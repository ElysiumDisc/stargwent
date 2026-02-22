"""
STARGWENT - GALACTIC CONQUEST - Campaign Controller

Main orchestrator: turn loop, planet attacks, card battles,
AI counterattacks, and campaign flow.
"""

import pygame
import random
import os
import display_manager

from .campaign_state import CampaignState
from .campaign_persistence import save_campaign, load_campaign
from .galaxy_map import GalaxyMap, ALL_FACTIONS
from .map_renderer import MapScreen
from .card_battle import run_card_battle
from .reward_screen import run_reward_screen
from .neutral_events import run_neutral_event


# AI counterattack chance per faction with adjacent border
AI_COUNTERATTACK_CHANCE = 0.30
# Cooldown turns after failed attack
ATTACK_COOLDOWN = 3

# Faction-specific bonuses when conquering a faction's planet
FACTION_CONQUEST_BONUSES = {
    "Tau'ri": {"type": "extra_card", "desc": "Intel: +1 random card"},
    "Goa'uld": {"type": "upgrade_card", "desc": "Domination: +2 power to a random card"},
    "Jaffa Rebellion": {"type": "remove_weak", "desc": "Training: removed weakest card"},
    "Lucian Alliance": {"type": "naquadah", "value": 50, "desc": "Trade: +50 naquadah"},
    "Asgard": {"type": "upgrade_multi", "desc": "Tech: +1 power to 2 random cards"},
}


class CampaignController:
    """Orchestrates the Galactic Conquest campaign turn loop."""

    def __init__(self, screen, campaign_state: CampaignState):
        self.screen = screen
        self.state = campaign_state
        self.galaxy = GalaxyMap.from_dict(campaign_state.galaxy)
        self.map_screen = MapScreen(screen.get_width(), screen.get_height())
        self.message = None
        self.rng = random.Random(campaign_state.seed + campaign_state.turn_number)

    @staticmethod
    def _music_start():
        from . import start_conquest_music
        start_conquest_music()

    @staticmethod
    def _music_stop():
        from . import stop_conquest_music
        stop_conquest_music()

    def run(self):
        """Main campaign loop. Returns 'victory', 'defeat', 'quit', or 'save_quit'."""
        clock = pygame.time.Clock()
        self._music_start()

        while True:
            # Refresh screen reference (may have changed after card battle)
            self.screen = display_manager.screen

            # Sync planet ownership from state to galaxy
            for pid, owner in self.state.planet_ownership.items():
                if pid in self.galaxy.planets:
                    self.galaxy.planets[pid].owner = owner

            # Check win/loss
            if self.galaxy.check_win():
                self._music_stop()
                self._show_end_screen("VICTORY", "You have conquered the galaxy!")
                return "victory"
            if self.galaxy.check_loss(self.state.player_faction):
                self._music_stop()
                self._show_end_screen("DEFEAT", "Your homeworld has fallen!")
                return "defeat"

            attackable = self.galaxy.get_attackable_planets()
            # Remove cooldown planets
            attackable = [p for p in attackable if p not in self.state.cooldowns]

            # Map screen loop (player turn)
            action = self._run_map_screen(clock, attackable)

            if action == "save_quit":
                self._save()
                self._music_stop()
                return "save_quit"
            elif action == "quit":
                self._music_stop()
                return "quit"
            elif action == "view_deck":
                self._show_deck_viewer()
            elif action == "run_info":
                self._show_run_info()
            elif action == "attack":
                planet_id = self.map_screen.selected_planet
                if planet_id:
                    result = self._attack_planet(planet_id)
                    if result == "quit":
                        return "quit"
            elif action == "end_turn":
                # AI counterattack phase
                ai_result = self._ai_counterattack_phase()
                if ai_result == "quit":
                    self._music_stop()
                    return "quit"
                if ai_result == "defeat":
                    self._music_stop()
                    self._show_end_screen("DEFEAT", "Your homeworld has fallen!")
                    return "defeat"

                # Advance turn
                self.state.turn_number += 1
                self.state.tick_cooldowns()
                self.rng = random.Random(self.state.seed + self.state.turn_number)
                self.message = f"Turn {self.state.turn_number}"

                # Auto-save
                self._save()

    def _run_map_screen(self, clock, attackable):
        """Run the galaxy map until player takes an action."""
        while True:
            clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"

                action = self.map_screen.handle_event(
                    event, self.galaxy, self.state, attackable)
                if action:
                    return action

            self.map_screen.draw(
                self.screen, self.galaxy, self.state, attackable, self.message)
            display_manager.gpu_flip()

    def _attack_planet(self, planet_id):
        """Execute an attack on a planet. Returns 'done' or 'quit'."""
        planet = self.galaxy.planets[planet_id]

        # Neutral planet — text event, no combat
        if planet.owner == "neutral":
            self._music_stop()
            result = run_neutral_event(self.screen, self.state)
            self._refresh_after_battle()
            if result == "quit":
                return "quit"
            planet.visited = True
            self.galaxy.transfer_ownership(planet_id, "player")
            self.state.planet_ownership[planet_id] = "player"
            self.message = f"Claimed {planet.name}!"
            return "done"

        # Enemy faction planet — card battle
        self._music_stop()
        card_result = self._run_card_battle(planet)
        self._refresh_after_battle()
        if card_result == "quit":
            return "quit"

        if card_result == "player_win":
            # Victory! Claim planet
            self.galaxy.transfer_ownership(planet_id, "player")
            self.state.planet_ownership[planet_id] = "player"
            self.message = f"Conquered {planet.name}!"

            # Apply faction-specific conquest bonus
            bonus_msg = self._apply_faction_bonus(planet.faction)

            # Reward screen — quality scales with planets controlled
            reward_result = run_reward_screen(
                self.screen, self.state, planet.faction,
                planet_type=planet.planet_type,
                galaxy_map=self.galaxy,
                bonus_message=bonus_msg)
            self._refresh_after_battle()
            if reward_result == "quit":
                return "quit"
        else:
            # Lost card battle — cooldown
            self.state.cooldowns[planet_id] = ATTACK_COOLDOWN
            self.state.add_naquadah(-30)
            self.message = f"Card battle lost at {planet.name}! Cooldown: {ATTACK_COOLDOWN} turns"

        return "done"

    def _run_card_battle(self, planet):
        """Run a card battle against a planet's defender. Returns battle outcome."""
        ai_faction = planet.faction
        ai_leader = planet.defender_leader

        result = run_card_battle(
            self.screen,
            player_faction=self.state.player_faction,
            player_leader=self.state.player_leader,
            player_deck_ids=list(self.state.current_deck),
            ai_faction=ai_faction,
            ai_leader=ai_leader,
            exempt_penalties=True,
            upgraded_cards=self.state.upgraded_cards,
        )
        return result

    def _refresh_after_battle(self):
        """Refresh screen and clear events after returning from a battle/event screen."""
        self.screen = display_manager.screen
        self.map_screen = MapScreen(self.screen.get_width(), self.screen.get_height())
        pygame.event.clear()
        self._music_start()

    def _ai_counterattack_phase(self):
        """Process AI counterattacks. Returns 'done', 'defeat', or 'quit'."""
        enemy_factions = set()
        for planet in self.galaxy.planets.values():
            if planet.owner not in ("player", "neutral"):
                enemy_factions.add(planet.owner)

        for faction in enemy_factions:
            # Skip friendly faction — they don't counterattack
            if faction == self.state.friendly_faction:
                continue
            targets = self.galaxy.get_ai_attack_targets(faction)
            if not targets:
                continue

            if self.rng.random() > AI_COUNTERATTACK_CHANCE:
                continue

            # AI attacks a random player planet
            target_id = self.rng.choice(targets)
            target = self.galaxy.planets[target_id]

            self.message = f"{faction} attacks {target.name}!"
            # Brief message display
            self._flash_message(f"{faction} is attacking {target.name}!", 2000)

            # Card battle defense
            # Pick a random leader from the attacking faction
            from content_registry import get_all_leaders_for_faction
            leaders = get_all_leaders_for_faction(faction)
            ai_leader = dict(self.rng.choice(leaders)) if leaders else None
            if ai_leader:
                ai_leader.setdefault("faction", faction)

            self._music_stop()
            result = run_card_battle(
                self.screen,
                player_faction=self.state.player_faction,
                player_leader=self.state.player_leader,
                player_deck_ids=list(self.state.current_deck),
                ai_faction=faction,
                ai_leader=ai_leader,
                exempt_penalties=True,
                upgraded_cards=self.state.upgraded_cards,
            )
            self._refresh_after_battle()

            if result == "quit":
                return "quit"

            if result == "player_win":
                self.state.add_naquadah(40)
                # Defense bonus: random card from attacking faction
                defense_bonus = self._apply_defense_bonus(faction)
                self.message = f"Defended {target.name}! +40 Naquadah{defense_bonus}"
            else:
                # Lost defense — enemy takes the planet
                self.galaxy.transfer_ownership(target_id, faction)
                self.state.planet_ownership[target_id] = faction
                self.state.add_naquadah(-30)
                self.message = f"{target.name} lost to {faction}!"

                # Check if homeworld was lost
                if self.galaxy.check_loss(self.state.player_faction):
                    return "defeat"

        return "done"

    def _show_deck_viewer(self):
        """Show the player's current conquest deck using the full deck builder UI."""
        from deck_builder import run_deck_builder

        def _conquest_save(card_ids):
            """Callback: save deck changes back to campaign state."""
            self.state.current_deck = list(card_ids)
            from .campaign_persistence import save_campaign
            self.state.galaxy = self.galaxy.to_dict()
            for pid, planet in self.galaxy.planets.items():
                self.state.planet_ownership[pid] = planet.owner
            save_campaign(self.state)

        self._music_stop()
        run_deck_builder(
            self.screen,
            for_new_game=False,
            conquest_save_callback=_conquest_save,
            preset_faction=self.state.player_faction,
            preset_leader=self.state.player_leader,
            preset_deck_ids=list(self.state.current_deck),
        )
        self._refresh_after_battle()

    def _show_run_info(self):
        """Show a summary of the current campaign run with CRT terminal aesthetic."""
        import math
        from .conquest_menu import (_get_scanline_overlay, CRT_AMBER, CRT_CYAN,
                                    CRT_GREEN, CRT_BORDER, CRT_TEXT, CRT_TEXT_DIM,
                                    CRT_BTN_BG, CRT_BTN_BORDER, FACTION_DISPLAY_COLORS)

        sw, sh = self.screen.get_width(), self.screen.get_height()
        clock = pygame.time.Clock()

        title_font = pygame.font.SysFont("Impact, Arial", max(40, sh // 22), bold=True)
        section_font = pygame.font.SysFont("Impact, Arial", max(22, sh // 42), bold=True)
        info_font = pygame.font.SysFont("Arial", max(17, sh // 55))

        # Load background (same as conquest menu)
        background = None
        bg_path = os.path.join("assets", "conquest_menu_bg.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join("assets", "conquest.png")
        try:
            raw = pygame.image.load(bg_path).convert()
            background = pygame.transform.smoothscale(raw, (sw, sh))
        except (pygame.error, FileNotFoundError):
            background = pygame.Surface((sw, sh))
            background.fill((8, 12, 10))

        scroll_offset = 0
        frame_count = 0
        running = True

        while running:
            clock.tick(60)
            frame_count += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_RETURN):
                        running = False
                    elif event.key == pygame.K_UP:
                        scroll_offset = max(0, scroll_offset - 40)
                    elif event.key == pygame.K_DOWN:
                        scroll_offset += 40
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        running = False
                    elif event.button == 4:
                        scroll_offset = max(0, scroll_offset - 40)
                    elif event.button == 5:
                        scroll_offset += 40

            # Background + dark overlay
            self.screen.blit(background, (0, 0))
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            self.screen.blit(overlay, (0, 0))

            # Panel with CRT border
            panel_w = int(sw * 0.6)
            panel_h = int(sh * 0.8)
            panel_x = sw // 2 - panel_w // 2
            panel_y = int(sh * 0.1)
            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel_surf.fill((*CRT_BTN_BG, 230))
            pygame.draw.rect(panel_surf, CRT_BORDER, panel_surf.get_rect(), 2)

            # Content lines
            content_lines = []

            # Title (pulsing amber)
            content_lines.append(("title", "RUN INFORMATION"))
            content_lines.append(("spacer", ""))

            # General stats
            content_lines.append(("section", "Campaign Status"))
            faction_color = FACTION_DISPLAY_COLORS.get(self.state.player_faction, CRT_TEXT)
            content_lines.append(("info", f"Faction: {self.state.player_faction}", faction_color))
            leader_name = self.state.player_leader.get("name", "Unknown") if self.state.player_leader else "Unknown"
            content_lines.append(("info", f"Leader: {leader_name}", CRT_TEXT))
            content_lines.append(("info", f"Turn: {self.state.turn_number}", CRT_AMBER))
            content_lines.append(("info", f"Naquadah: {self.state.naquadah}", CRT_CYAN))
            content_lines.append(("info", f"Deck Size: {len(self.state.current_deck)} cards", CRT_AMBER))
            content_lines.append(("spacer", ""))

            # Territory
            content_lines.append(("section", "Territory"))
            player_planets = []
            enemy_planets = []
            neutral_planets = []
            for pid, planet in self.galaxy.planets.items():
                if planet.owner == "player":
                    player_planets.append(planet)
                elif planet.owner == "neutral":
                    neutral_planets.append(planet)
                else:
                    enemy_planets.append(planet)
            total = len(self.galaxy.planets)
            content_lines.append(("info", f"Controlled: {len(player_planets)}/{total} planets", CRT_GREEN))
            content_lines.append(("info", f"Enemy: {len(enemy_planets)} | Neutral: {len(neutral_planets)}", CRT_TEXT))

            # Reward tier
            player_count = len(player_planets)
            if player_count >= 10:
                tier_text = "Supreme (5 card choices, +50% naquadah)"
                tier_color = CRT_AMBER
            elif player_count >= 6:
                tier_text = "Enhanced (4 card choices, +25% naquadah)"
                tier_color = CRT_CYAN
            else:
                tier_text = "Standard (3 card choices)"
                tier_color = CRT_TEXT
            content_lines.append(("info", f"Reward Tier: {tier_text}", tier_color))
            content_lines.append(("spacer", ""))

            # Your planets
            if player_planets:
                content_lines.append(("section", "Your Planets"))
                for p in player_planets:
                    tag = " (Homeworld)" if p.planet_type == "homeworld" else ""
                    content_lines.append(("info", f"  {p.name}{tag}", CRT_GREEN))

            # Cooldowns
            if self.state.cooldowns:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Active Cooldowns"))
                for pid, turns in self.state.cooldowns.items():
                    pname = self.galaxy.planets[pid].name if pid in self.galaxy.planets else pid
                    content_lines.append(("info", f"  {pname}: {turns} turn(s) remaining", (255, 100, 100)))

            # Upgraded cards
            if self.state.upgraded_cards:
                content_lines.append(("spacer", ""))
                content_lines.append(("section", "Upgraded Cards"))
                from cards import ALL_CARDS
                for cid, bonus in sorted(self.state.upgraded_cards.items()):
                    if bonus <= 0:
                        continue
                    card = ALL_CARDS.get(cid)
                    cname = card.name if card else cid
                    content_lines.append(("info", f"  {cname}: +{bonus} power", CRT_GREEN))
            content_lines.append(("spacer", ""))

            # Enemy homeworld status
            content_lines.append(("section", "Enemy Homeworlds"))
            for pid, planet in self.galaxy.planets.items():
                if planet.planet_type == "homeworld" and planet.owner != "player":
                    hw_color = FACTION_DISPLAY_COLORS.get(planet.owner, (255, 100, 100))
                    content_lines.append(("info", f"  {planet.name} ({planet.owner})", hw_color))
            for pid, planet in self.galaxy.planets.items():
                if planet.planet_type == "homeworld" and planet.owner == "player" and planet.faction != self.state.player_faction:
                    content_lines.append(("info", f"  {planet.name} (CAPTURED)", CRT_GREEN))

            content_lines.append(("spacer", ""))
            content_lines.append(("info", "Press ESC / I / Click to close", CRT_TEXT_DIM))

            # Render content
            pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
            y = 20 - scroll_offset
            for kind, text, *extra in content_lines:
                if kind == "title":
                    title_color = tuple(int(c * pulse) for c in CRT_AMBER)
                    surf = title_font.render(text, True, title_color)
                    panel_surf.blit(surf, (panel_w // 2 - surf.get_width() // 2, y))
                    y += surf.get_height() + 4
                    # Decorative line under title
                    line_w = int(panel_w * 0.6)
                    line_color = tuple(int(c * pulse) for c in CRT_BORDER)
                    pygame.draw.line(panel_surf, line_color,
                                     (panel_w // 2 - line_w // 2, y),
                                     (panel_w // 2 + line_w // 2, y), 2)
                    y += 8
                elif kind == "section":
                    surf = section_font.render(text, True, CRT_AMBER)
                    panel_surf.blit(surf, (30, y))
                    y += surf.get_height() + 6
                elif kind == "info":
                    color = extra[0] if extra else CRT_TEXT
                    surf = info_font.render(text, True, color)
                    panel_surf.blit(surf, (40, y))
                    y += surf.get_height() + 3
                elif kind == "spacer":
                    y += 12

            self.screen.blit(panel_surf, (panel_x, panel_y))

            # CRT scanlines over entire screen
            scanlines = _get_scanline_overlay(sw, sh, alpha=25)
            self.screen.blit(scanlines, (0, 0))

            # Bottom bar
            bar_h = int(sh * 0.035)
            bar_rect = pygame.Rect(0, sh - bar_h, sw, bar_h)
            bar_surf = pygame.Surface((bar_rect.width, bar_rect.height), pygame.SRCALPHA)
            bar_surf.fill((0, 0, 0, 180))
            self.screen.blit(bar_surf, bar_rect.topleft)
            hint = info_font.render("ESC / I / Click to close", True, CRT_TEXT_DIM)
            self.screen.blit(hint, (int(sw * 0.04), bar_rect.centery - hint.get_height() // 2))

            display_manager.gpu_flip()

    def _apply_faction_bonus(self, faction):
        """Apply faction-specific bonus after conquering a planet. Returns bonus message."""
        bonus = FACTION_CONQUEST_BONUSES.get(faction)
        if not bonus:
            return ""
        from cards import ALL_CARDS
        btype = bonus["type"]

        if btype == "extra_card":
            all_ids = [cid for cid, c in ALL_CARDS.items()
                       if getattr(c, 'card_type', '') != "Legendary Commander"
                       and getattr(c, 'row', '') != "weather"]
            if all_ids:
                cid = self.rng.choice(all_ids)
                self.state.add_card(cid)
                name = getattr(ALL_CARDS[cid], 'name', cid)
                return f" | {bonus['desc']}: {name}"

        elif btype == "upgrade_card":
            upgradeable = [cid for cid in self.state.current_deck
                           if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)]
            if upgradeable:
                target = self.rng.choice(upgradeable)
                self.state.upgrade_card(target, 2)
                name = getattr(ALL_CARDS[target], 'name', target)
                return f" | {bonus['desc']}: {name}"

        elif btype == "remove_weak":
            deck_with_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                               for cid in self.state.current_deck]
            deck_with_power.sort(key=lambda x: x[1])
            if len(deck_with_power) > 15:  # don't remove if deck too small
                removed_cid = deck_with_power[0][0]
                self.state.remove_card(removed_cid)
                name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
                return f" | {bonus['desc']}: {name}"

        elif btype == "naquadah":
            amount = bonus.get("value", 50)
            self.state.add_naquadah(amount)
            return f" | {bonus['desc']}"

        elif btype == "upgrade_multi":
            upgradeable = list(set(cid for cid in self.state.current_deck
                                   if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)))
            if upgradeable:
                targets = self.rng.sample(upgradeable, min(2, len(upgradeable)))
                names = []
                for cid in targets:
                    self.state.upgrade_card(cid, 1)
                    names.append(getattr(ALL_CARDS[cid], 'name', cid))
                return f" | {bonus['desc']}: {', '.join(names)}"

        return ""

    def _apply_defense_bonus(self, attacking_faction):
        """Apply bonus for successfully defending a counterattack. Returns bonus string."""
        from cards import ALL_CARDS
        # Award a random card from attacking faction
        faction_cards = [cid for cid, c in ALL_CARDS.items()
                         if getattr(c, 'faction', None) == attacking_faction
                         and getattr(c, 'card_type', '') != "Legendary Commander"
                         and getattr(c, 'row', '') != "weather"]
        bonus_parts = []
        if faction_cards:
            cid = self.rng.choice(faction_cards)
            self.state.add_card(cid)
            name = getattr(ALL_CARDS[cid], 'name', cid)
            bonus_parts.append(f"+1 {attacking_faction} card: {name}")

        # 30% chance to upgrade a random card
        if self.rng.random() < 0.30:
            upgradeable = [cid for cid in self.state.current_deck
                           if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)]
            if upgradeable:
                target = self.rng.choice(upgradeable)
                self.state.upgrade_card(target, 1)
                name = getattr(ALL_CARDS[target], 'name', target)
                bonus_parts.append(f"Upgrade: {name} +1")

        if bonus_parts:
            return " | " + " | ".join(bonus_parts)
        return ""

    def _flash_message(self, text, duration_ms=2000):
        """Show a message overlay for a brief duration."""
        sw, sh = self.screen.get_width(), self.screen.get_height()
        font = pygame.font.SysFont("Impact, Arial", max(36, sh // 25), bold=True)
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        msg_surf = font.render(text, True, (255, 200, 100))
        self.screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2,
                                     sh // 2 - msg_surf.get_height() // 2))
        display_manager.gpu_flip()
        pygame.time.wait(duration_ms)

    def _show_end_screen(self, title, subtitle):
        """Show a victory/defeat screen."""
        self.screen = display_manager.screen
        sw, sh = self.screen.get_width(), self.screen.get_height()
        clock = pygame.time.Clock()

        title_font = pygame.font.SysFont("Impact, Arial", max(72, sh // 12), bold=True)
        sub_font = pygame.font.SysFont("Arial", max(28, sh // 30))
        info_font = pygame.font.SysFont("Arial", max(20, sh // 45))

        title_color = (255, 220, 100) if title == "VICTORY" else (255, 80, 80)

        running = True
        while running:
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    running = False

            self.screen.fill((10, 15, 25))
            t_surf = title_font.render(title, True, title_color)
            self.screen.blit(t_surf, (sw // 2 - t_surf.get_width() // 2, int(sh * 0.25)))
            s_surf = sub_font.render(subtitle, True, (220, 220, 220))
            self.screen.blit(s_surf, (sw // 2 - s_surf.get_width() // 2, int(sh * 0.42)))

            # Stats
            stats_y = int(sh * 0.55)
            stats = [
                f"Turns: {self.state.turn_number}",
                f"Planets: {self.galaxy.get_player_planet_count()}/{len(self.galaxy.planets)}",
                f"Naquadah: {self.state.naquadah}",
                f"Deck size: {len(self.state.current_deck)}",
            ]
            for stat in stats:
                stat_surf = info_font.render(stat, True, (180, 180, 200))
                self.screen.blit(stat_surf, (sw // 2 - stat_surf.get_width() // 2, stats_y))
                stats_y += int(sh * 0.04)

            cont = info_font.render("Press any key to continue", True, (150, 150, 150))
            self.screen.blit(cont, (sw // 2 - cont.get_width() // 2, int(sh * 0.82)))
            display_manager.gpu_flip()

    def _save(self):
        """Save current campaign state."""
        # Sync galaxy data back to state
        self.state.galaxy = self.galaxy.to_dict()
        # Sync ownership
        for pid, planet in self.galaxy.planets.items():
            self.state.planet_ownership[pid] = planet.owner
        save_campaign(self.state)
