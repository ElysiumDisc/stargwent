"""
STARGWENT - GALACTIC CONQUEST - Map Renderer

Renders the galaxy map with planets, hyperspace lanes, territory colors, and HUD.
Handles click detection for planet selection.
"""

import pygame
import math
import os


# Planet visual sizes
PLANET_RADIUS_HOMEWORLD = 22
PLANET_RADIUS_TERRITORY = 16
PLANET_RADIUS_NEUTRAL = 12

# Colors
COLOR_LANE = (60, 80, 120)
COLOR_LANE_ATTACKABLE = (120, 200, 255)
COLOR_SELECTED = (255, 255, 100)
COLOR_COOLDOWN = (120, 60, 60)
COLOR_HUD_BG = (15, 20, 35, 200)
COLOR_HUD_TEXT = (220, 220, 220)
COLOR_NAQUADAH = (100, 200, 255)
COLOR_DECK = (200, 180, 100)
COLOR_TURN = (255, 200, 100)

# --- Dim overlay cache (non-SRCALPHA fast path) ---
_dim_overlay_cache = {}


def _get_dim_overlay(w, h, alpha):
    """Return a cached dim overlay using non-SRCALPHA + set_alpha (fast path)."""
    key = (w, h, alpha)
    surf = _dim_overlay_cache.get(key)
    if surf is None:
        surf = pygame.Surface((w, h))
        surf.fill((0, 0, 0))
        surf.set_alpha(alpha)
        _dim_overlay_cache[key] = surf
    return surf


FACTION_COLORS = {
    "Tau'ri": (50, 120, 200),
    "Goa'uld": (200, 50, 50),
    "Jaffa Rebellion": (200, 180, 50),
    "Lucian Alliance": (200, 80, 180),
    "Asgard": (100, 180, 220),
    "neutral": (150, 150, 150),
    "player": (80, 220, 120),
}


class MapScreen:
    """Renders and handles interaction for the galaxy map."""

    def __init__(self, screen_width, screen_height):
        self.sw = screen_width
        self.sh = screen_height

        # Load background
        self.background = None
        bg_path = os.path.join("assets", "conquest.png")
        try:
            raw = pygame.image.load(bg_path).convert()
            self.background = pygame.transform.smoothscale(raw, (self.sw, self.sh))
        except (pygame.error, FileNotFoundError):
            self.background = pygame.Surface((self.sw, self.sh))
            self.background.fill((10, 12, 25))

        # Fonts
        self.font_name = pygame.font.SysFont("Arial", max(14, screen_height // 80))
        self.font_hud = pygame.font.SysFont("Arial", max(18, screen_height // 55), bold=True)
        self.font_btn = pygame.font.SysFont("Arial", max(13, screen_height // 70), bold=True)
        self.font_title = pygame.font.SysFont("Impact, Arial", max(28, screen_height // 35), bold=True)
        self.font_info = pygame.font.SysFont("Arial", max(13, screen_height // 90))

        margin_x = int(self.sw * 0.04)

        # Bottom HUD dimensions — two rows: info row + button row
        self.bottom_hud_h = int(self.sh * 0.13)
        self.btn_row_y = self.sh - int(self.sh * 0.055)  # button row at very bottom
        self.info_row_y = self.sh - self.bottom_hud_h + int(self.sh * 0.01)  # info row above buttons

        # Map area
        margin_top = int(self.sh * 0.08)
        self.map_rect = pygame.Rect(margin_x, margin_top,
                                     self.sw - 2 * margin_x,
                                     self.sh - margin_top - self.bottom_hud_h)

        # State
        self.hovered_planet = None
        self.selected_planet = None
        self.planet_rects = {}
        self._tooltip_cache = None  # (planet_id, tooltip_surf, lines_key)

        # Buttons — 10 buttons evenly spaced along bottom row
        btn_count = 10
        btn_h = int(self.sh * 0.045)
        available_w = self.sw - 2 * margin_x
        btn_gap = max(4, int(self.sw * 0.006))
        btn_w = (available_w - (btn_count - 1) * btn_gap) // btn_count

        # All buttons left-to-right in logical order
        def _btn(i):
            return pygame.Rect(margin_x + i * (btn_w + btn_gap), self.btn_row_y, btn_w, btn_h)

        self.save_quit_button_rect = _btn(0)
        self.diplomacy_button_rect = _btn(1)
        self.minor_world_button_rect = _btn(2)
        self.operatives_button_rect = _btn(3)
        self.doctrines_button_rect = _btn(4)
        self.run_info_button_rect = _btn(5)
        self.view_deck_button_rect = _btn(6)
        self.end_turn_button_rect = _btn(7)
        self.fortify_button_rect = _btn(8)
        self.attack_button_rect = _btn(9)

    def _world_to_screen(self, pos):
        """Convert normalized (0-1) position to screen pixel coordinates."""
        return (
            int(self.map_rect.x + pos[0] * self.map_rect.width),
            int(self.map_rect.y + pos[1] * self.map_rect.height),
        )

    def _get_planet_color(self, planet):
        return FACTION_COLORS.get(planet.owner, (150, 150, 150))

    def _get_planet_radius(self, planet):
        if planet.planet_type == "homeworld":
            return PLANET_RADIUS_HOMEWORLD
        elif planet.planet_type == "territory":
            return PLANET_RADIUS_TERRITORY
        return PLANET_RADIUS_NEUTRAL

    def draw(self, screen, galaxy_map, campaign_state, attackable_ids, message=None):
        """Render the full galaxy map view."""
        # Background
        screen.blit(self.background, (0, 0))

        # Dim overlay (cached non-SRCALPHA fast path)
        screen.blit(_get_dim_overlay(self.sw, self.sh, 100), (0, 0))

        self.planet_rects.clear()

        # Draw hyperspace lanes with pulsing effect for player-owned connections
        tick = pygame.time.get_ticks()
        lane_pulse = 0.6 + 0.4 * math.sin(tick * 0.002)
        for pid, planet in galaxy_map.planets.items():
            sx, sy = self._world_to_screen(planet.position)
            for conn_id in planet.connections:
                if conn_id > pid:
                    conn = galaxy_map.planets[conn_id]
                    cx, cy = self._world_to_screen(conn.position)
                    is_attackable = (pid in attackable_ids or conn_id in attackable_ids)
                    both_player = (planet.owner == "player" and conn.owner == "player")
                    if is_attackable:
                        color = COLOR_LANE_ATTACKABLE
                        width = 2
                    elif both_player:
                        # Pulsing bright lane for connected player territory
                        pulse_val = int(80 + 60 * lane_pulse)
                        color = (pulse_val, int(pulse_val * 1.5), pulse_val)
                        width = 2
                    else:
                        color = COLOR_LANE
                        width = 1
                    pygame.draw.line(screen, color, (sx, sy), (cx, cy), width)

        # Compute supply lines — unsupplied player planets (allied planets bridge gaps)
        from .stargate_network import get_disconnected_planets
        from .diplomacy import get_adjacency_bonus_factions
        allied_factions = get_adjacency_bonus_factions(campaign_state)
        unsupplied = get_disconnected_planets(galaxy_map, campaign_state.player_faction, allied_factions)

        # Draw planets
        for pid, planet in galaxy_map.planets.items():
            sx, sy = self._world_to_screen(planet.position)
            radius = self._get_planet_radius(planet)
            color = self._get_planet_color(planet)

            is_cooldown = pid in campaign_state.cooldowns
            if is_cooldown:
                color = COLOR_COOLDOWN

            is_attackable = pid in attackable_ids and not is_cooldown
            if is_attackable:
                glow_surf = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*COLOR_LANE_ATTACKABLE, 40),
                                   (radius * 3, radius * 3), radius * 3)
                screen.blit(glow_surf, (sx - radius * 3, sy - radius * 3))

            pygame.draw.circle(screen, color, (sx, sy), radius)

            # Minor world type ring for player-owned neutral planets
            if planet.planet_type == "neutral" and planet.owner == "player":
                from .minor_worlds import MINOR_WORLD_TYPES, MINOR_WORLD_TYPE_INFO
                _mw_type = MINOR_WORLD_TYPES.get(planet.name)
                if _mw_type:
                    _mw_color = MINOR_WORLD_TYPE_INFO.get(_mw_type, {}).get("color", (150, 150, 150))
                    pygame.draw.circle(screen, _mw_color, (sx, sy), radius + 3, 2)

            if planet.planet_type == "homeworld":
                pygame.draw.circle(screen, (255, 255, 255), (sx, sy), radius + 3, 2)

            if pid == self.selected_planet:
                pygame.draw.circle(screen, COLOR_SELECTED, (sx, sy), radius + 5, 3)

            if pid == self.hovered_planet and pid != self.selected_planet:
                pygame.draw.circle(screen, (200, 200, 200), (sx, sy), radius + 4, 2)

            label = self.font_name.render(planet.name, True, (220, 220, 220))
            screen.blit(label, (sx - label.get_width() // 2, sy + radius + 4))

            if is_cooldown:
                cd_text = self.font_info.render(
                    f"{campaign_state.cooldowns[pid]}T", True, (255, 100, 100))
                screen.blit(cd_text, (sx - cd_text.get_width() // 2, sy - radius - 16))

            # Unsupplied indicator (dashed red outline)
            if pid in unsupplied and planet.owner == "player":
                for angle_deg in range(0, 360, 30):
                    rad = math.radians(angle_deg)
                    end_rad = math.radians(angle_deg + 15)
                    x1 = sx + int(math.cos(rad) * (radius + 6))
                    y1 = sy + int(math.sin(rad) * (radius + 6))
                    x2 = sx + int(math.cos(end_rad) * (radius + 6))
                    y2 = sy + int(math.sin(end_rad) * (radius + 6))
                    pygame.draw.line(screen, (255, 100, 60), (x1, y1), (x2, y2), 2)

            # Building indicator
            building_info = None
            from .buildings import get_planet_building_display
            building_info = get_planet_building_display(campaign_state, pid)
            if building_info and planet.owner == "player":
                bname, bicon, bdesc = building_info
                bld_text = self.font_info.render(bicon, True, (200, 180, 100))
                screen.blit(bld_text, (sx + radius + 3, sy - 8))

            # Fortification shields
            fort_level = getattr(campaign_state, 'fortification_levels', {}).get(pid, 0)
            if fort_level > 0 and planet.owner == "player":
                shield_text = self.font_info.render(
                    "\u2666" * fort_level, True, (100, 200, 255))
                screen.blit(shield_text, (sx - shield_text.get_width() // 2, sy - radius - 14))

            # Operative indicator (small diamond)
            from .espionage import get_operative_summary
            _ops = get_operative_summary(campaign_state)
            _op_here = sum(1 for o in _ops if o[3] == pid and o[2] not in ("idle", "dead"))
            if _op_here > 0:
                op_text = self.font_info.render(
                    "\u25C6" * _op_here, True, (200, 150, 255))
                screen.blit(op_text, (sx - op_text.get_width() // 2, sy + radius + 16))

            # Enemy homeworld glow ring
            if planet.planet_type == "homeworld" and planet.owner not in ("player", "neutral"):
                hw_color = FACTION_COLORS.get(planet.owner, (200, 50, 50))
                glow_alpha = int(120 + 60 * math.sin(pygame.time.get_ticks() * 0.003))
                glow_surf = pygame.Surface((radius * 8, radius * 8), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*hw_color, min(255, glow_alpha)),
                                   (radius * 4, radius * 4), radius * 4, 3)
                screen.blit(glow_surf, (sx - radius * 4, sy - radius * 4))

            self.planet_rects[pid] = pygame.Rect(sx - radius, sy - radius,
                                                  radius * 2, radius * 2)

        # ===== PLANET TOOLTIP (hover) =====
        if self.hovered_planet and self.hovered_planet in galaxy_map.planets:
            hp = galaxy_map.planets[self.hovered_planet]
            hp_rect = self.planet_rects.get(self.hovered_planet)
            if hp_rect:
                tooltip_lines = [hp.name]
                tooltip_lines.append(f"Owner: {hp.owner}")
                tooltip_lines.append(f"Type: {hp.planet_type.title()}")
                if hp.weather_preset:
                    wname = hp.weather_preset.get('type', 'none').replace('_', ' ').title()
                    tooltip_lines.append(f"Weather: {wname}")
                if hp.defender_leader and hp.owner not in ("player", "neutral"):
                    tooltip_lines.append(f"Defender: {hp.defender_leader.get('name', '?')}")
                fort_lv = getattr(campaign_state, 'fortification_levels', {}).get(self.hovered_planet, 0)
                if fort_lv > 0 and hp.owner == "player":
                    tooltip_lines.append(f"Fortification: Lv{fort_lv}/3")
                from .buildings import get_planet_building_display
                binfo = get_planet_building_display(campaign_state, self.hovered_planet)
                if binfo and hp.owner == "player":
                    tooltip_lines.append(f"Building: {binfo[0]}")
                if self.hovered_planet in campaign_state.cooldowns:
                    tooltip_lines.append(f"Cooldown: {campaign_state.cooldowns[self.hovered_planet]}T")
                from .planet_passives import get_planet_passive
                passive = get_planet_passive(self.hovered_planet, galaxy_map)
                if passive and hp.owner == "player":
                    tooltip_lines.append(f"Passive: {passive['desc']}")
                # Minor world info
                if hp.planet_type == "neutral" and hp.owner == "player":
                    from .minor_worlds import (ensure_minor_world, MINOR_WORLD_TYPE_INFO,
                                                get_tier_label)
                    _mw = ensure_minor_world(campaign_state, self.hovered_planet, galaxy_map)
                    if _mw:
                        _mw_info = MINOR_WORLD_TYPE_INFO.get(_mw.world_type, {})
                        tooltip_lines.append(f"World: {_mw.world_type.title()} {_mw_info.get('icon', '')}")
                        tooltip_lines.append(f"Influence: {_mw.influence} [{get_tier_label(_mw.influence)}]")
                        if _mw.active_quest:
                            tooltip_lines.append(f"Quest: {_mw.active_quest.get('description', '?')}")

                # Render tooltip (cached — only rebuild when content changes)
                tt_font = self.font_info
                lines_key = tuple(tooltip_lines)
                if (self._tooltip_cache is None or
                        self._tooltip_cache[0] != self.hovered_planet or
                        self._tooltip_cache[2] != lines_key):
                    tt_w = max(tt_font.size(line)[0] for line in tooltip_lines) + 16
                    tt_h = len(tooltip_lines) * (tt_font.get_height() + 2) + 10
                    tt_surf = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
                    tt_surf.fill((10, 15, 25, 220))
                    pygame.draw.rect(tt_surf, (80, 140, 160), tt_surf.get_rect(), 1)
                    y_off = 5
                    for j, line in enumerate(tooltip_lines):
                        color = (255, 220, 150) if j == 0 else (200, 200, 210)
                        ls = tt_font.render(line, True, color)
                        tt_surf.blit(ls, (8, y_off))
                        y_off += tt_font.get_height() + 2
                    self._tooltip_cache = (self.hovered_planet, tt_surf, lines_key)
                else:
                    tt_surf = self._tooltip_cache[1]
                tt_w = tt_surf.get_width()
                tt_h = tt_surf.get_height()
                tt_x = min(hp_rect.right + 10, self.sw - tt_w - 5)
                tt_y = max(5, hp_rect.centery - tt_h // 2)
                screen.blit(tt_surf, (tt_x, tt_y))

        # ===== TOP HUD =====
        hud_surf = pygame.Surface((self.sw, int(self.sh * 0.07)), pygame.SRCALPHA)
        hud_surf.fill(COLOR_HUD_BG)
        screen.blit(hud_surf, (0, 0))

        title = self.font_title.render("GALACTIC CONQUEST", True, (200, 220, 255))
        screen.blit(title, (int(self.sw * 0.04), int(self.sh * 0.015)))

        x_offset = int(self.sw * 0.35)
        y_center = int(self.sh * 0.03)
        upgraded_count = sum(1 for v in campaign_state.upgraded_cards.values() if v > 0)
        # Network tier display (allied planets bridge gaps for higher tiers)
        from .stargate_network import get_network_bonuses
        from .diplomacy import get_adjacency_bonus_factions as _get_allied
        network = get_network_bonuses(galaxy_map, campaign_state.player_faction,
                                       _get_allied(campaign_state))
        tier_colors = {1: (150, 150, 150), 2: (100, 200, 255), 3: (255, 200, 80),
                       4: (255, 140, 60), 5: (200, 100, 255)}
        tier_color = tier_colors.get(network["tier"], (200, 200, 200))

        stats = [
            (f"Turn {campaign_state.turn_number}", COLOR_TURN),
            (f"Naquadah: {campaign_state.naquadah}", COLOR_NAQUADAH),
            (f"Wisdom: {campaign_state.wisdom}", (200, 150, 255)),
            (f"Deck: {len(campaign_state.current_deck)}", COLOR_DECK),
            (f"Planets: {galaxy_map.get_player_planet_count()}/{len(galaxy_map.planets)}", (200, 200, 200)),
            (f"Net: T{network['tier']} {network['name']}", tier_color),
        ]
        if upgraded_count:
            stats.append((f"Upgrades: {upgraded_count}", (100, 255, 150)))
        relic_count = len(getattr(campaign_state, 'relics', []))
        if relic_count:
            stats.append((f"Relics: {relic_count}", (255, 176, 0)))
        fort_count = sum(1 for v in getattr(campaign_state, 'fortification_levels', {}).values() if v > 0)
        if fort_count:
            stats.append((f"Forts: {fort_count}", (100, 200, 255)))
        op_count = len(getattr(campaign_state, 'operatives', []))
        if op_count:
            stats.append((f"Ops: {op_count}", (200, 150, 255)))
        for text, color in stats:
            surf = self.font_hud.render(text, True, color)
            screen.blit(surf, (x_offset, y_center))
            x_offset += surf.get_width() + int(self.sw * 0.03)

        # Victory progress (compact, below stats row)
        from .victory_conditions import get_victory_progress
        v_progress = get_victory_progress(campaign_state, galaxy_map)
        if v_progress:
            best = max(v_progress, key=lambda x: x[3])
            from .victory_conditions import VICTORY_INFO
            v_info = VICTORY_INFO.get(best[0], {})
            v_color = v_info.get("color", (200, 200, 200))
            pct = int(best[3] * 100)
            v_text = self.font_info.render(
                f"Best path: {best[1]} ({pct}%) — {best[2]}", True, v_color)
            screen.blit(v_text, (int(self.sw * 0.35), y_center + int(self.sh * 0.025)))

        # ===== BOTTOM HUD =====
        bottom_surf = pygame.Surface((self.sw, self.bottom_hud_h), pygame.SRCALPHA)
        bottom_surf.fill(COLOR_HUD_BG)
        screen.blit(bottom_surf, (0, self.sh - self.bottom_hud_h))

        # Separator line between info and buttons
        sep_y = self.btn_row_y - int(self.sh * 0.01)
        pygame.draw.line(screen, (60, 80, 120), (int(self.sw * 0.02), sep_y),
                         (int(self.sw * 0.98), sep_y), 1)

        # Selected planet info — info row (above button row)
        if self.selected_planet and self.selected_planet in galaxy_map.planets:
            sp = galaxy_map.planets[self.selected_planet]
            info_x = int(self.sw * 0.05)
            info_y = self.info_row_y

            # Name + type
            name_text = self.font_hud.render(
                f"{sp.name} ({sp.planet_type.title()})", True, (255, 255, 255))
            screen.blit(name_text, (info_x, info_y))

            # Owner + faction color
            owner_color = self._get_planet_color(sp)
            owner_text = self.font_hud.render(f"Owner: {sp.owner}", True, owner_color)
            screen.blit(owner_text, (info_x + name_text.get_width() + int(self.sw * 0.03), info_y))

            # Weather (if any)
            if sp.weather_preset:
                weather_name = sp.weather_preset.get('type', 'none').replace('_', ' ').title()
                w_text = self.font_info.render(f"Weather: {weather_name}", True, (180, 180, 220))
                screen.blit(w_text, (info_x, info_y + int(self.sh * 0.028)))

            # Defender leader (if enemy planet)
            if sp.defender_leader and sp.owner not in ("player", "neutral"):
                leader_name = sp.defender_leader.get('name', '?')
                dl_text = self.font_info.render(f"Defender: {leader_name}", True, (220, 180, 140))
                screen.blit(dl_text, (info_x + int(self.sw * 0.15), info_y + int(self.sh * 0.028)))

            # Fortification level
            fort_level = getattr(campaign_state, 'fortification_levels', {}).get(self.selected_planet, 0)
            if fort_level > 0 and sp.owner == "player":
                fort_text = self.font_info.render(f"Fort: Lv{fort_level}/3", True, (100, 200, 255))
                screen.blit(fort_text, (info_x + int(self.sw * 0.30), info_y + int(self.sh * 0.028)))

            # Cooldown
            if self.selected_planet in campaign_state.cooldowns:
                cd_turns = campaign_state.cooldowns[self.selected_planet]
                cd_text = self.font_hud.render(f"Cooldown: {cd_turns} turns", True, (255, 100, 100))
                screen.blit(cd_text, (info_x + int(self.sw * 0.40), info_y + int(self.sh * 0.028)))
        else:
            # No planet selected — show hint
            hint = self.font_info.render(
                "Click a planet to see details  |  D = View Deck  |  ESC = Save & Quit",
                True, (100, 110, 140))
            screen.blit(hint, (int(self.sw * 0.05), self.info_row_y + int(self.sh * 0.01)))

        # ===== BUTTONS (bottom row) =====
        can_attack = (self.selected_planet in attackable_ids
                      and self.selected_planet not in campaign_state.cooldowns)

        # Fortify: selected planet must be player-owned, level < 3, enough naquadah
        fort_levels = getattr(campaign_state, 'fortification_levels', {})
        fort_cost = network["fortify_cost"]
        can_fortify = False
        if self.selected_planet and self.selected_planet in galaxy_map.planets:
            sp = galaxy_map.planets[self.selected_planet]
            cur_fort = fort_levels.get(self.selected_planet, 0)
            can_fortify = (sp.owner == "player" and cur_fort < 3
                           and campaign_state.naquadah >= fort_cost)

        self._draw_button(screen, self.save_quit_button_rect, "SAVE & QUIT",
                          (140, 80, 80), enabled=True)
        self._draw_button(screen, self.diplomacy_button_rect, "DIPLOMACY",
                          (120, 80, 160), enabled=True)
        # Minor World button: active when owned neutral planet selected
        can_minor_world = False
        if self.selected_planet and self.selected_planet in galaxy_map.planets:
            _mw_planet = galaxy_map.planets[self.selected_planet]
            can_minor_world = (_mw_planet.planet_type == "neutral"
                               and _mw_planet.owner == "player")
        self._draw_button(screen, self.minor_world_button_rect, "MINOR WORLD",
                          (100, 80, 160) if can_minor_world else (60, 60, 60),
                          enabled=can_minor_world)
        # Operatives button: always enabled when player has operatives
        has_operatives = len(getattr(campaign_state, 'operatives', [])) > 0
        self._draw_button(screen, self.operatives_button_rect, "OPERATIVES",
                          (120, 80, 180) if has_operatives else (60, 60, 60),
                          enabled=has_operatives)
        self._draw_button(screen, self.run_info_button_rect, "RUN INFO",
                          (80, 100, 130), enabled=True)
        self._draw_button(screen, self.doctrines_button_rect, "DOCTRINES",
                          (100, 80, 140), enabled=True)
        self._draw_button(screen, self.view_deck_button_rect, "VIEW DECK",
                          (120, 100, 60), enabled=True)
        self._draw_button(screen, self.end_turn_button_rect, "END TURN",
                          (80, 120, 180), enabled=True)
        fort_label = f"FORTIFY ({fort_cost})" if can_fortify else "FORTIFY"
        self._draw_button(screen, self.fortify_button_rect, fort_label,
                          (60, 120, 180) if can_fortify else (60, 60, 60),
                          enabled=can_fortify)
        self._draw_button(screen, self.attack_button_rect, "ATTACK",
                          (60, 180, 80) if can_attack else (60, 60, 60),
                          enabled=can_attack)

        # Status message (above bottom HUD)
        if message:
            msg_surf = self.font_hud.render(message, True, (255, 220, 100))
            screen.blit(msg_surf, (self.sw // 2 - msg_surf.get_width() // 2,
                                    self.sh - self.bottom_hud_h - int(self.sh * 0.03)))

    def _draw_button(self, screen, rect, text, color, enabled=True):
        """Draw a button with text, auto-fitting to button width."""
        alpha = 255 if enabled else 120
        btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        btn_surf.fill((*color, alpha))
        screen.blit(btn_surf, rect.topleft)
        pygame.draw.rect(screen, (200, 200, 200, alpha), rect, 2)
        # Use smaller font for buttons; fall back to font_info if still too wide
        text_color = (255, 255, 255) if enabled else (120, 120, 120)
        label = self.font_btn.render(text, True, text_color)
        if label.get_width() > rect.width - 6:
            label = self.font_info.render(text, True, text_color)
        screen.blit(label, (rect.centerx - label.get_width() // 2,
                            rect.centery - label.get_height() // 2))

    def handle_event(self, event, galaxy_map, campaign_state, attackable_ids):
        """Handle mouse events. Returns action string or None."""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_planet = None
            for pid, rect in self.planet_rects.items():
                if rect.collidepoint(mx, my):
                    self.hovered_planet = pid
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Check planet clicks
            for pid, rect in self.planet_rects.items():
                if rect.collidepoint(mx, my):
                    self.selected_planet = pid
                    return None

            # Check buttons
            if self.attack_button_rect.collidepoint(mx, my):
                if (self.selected_planet in attackable_ids
                        and self.selected_planet not in campaign_state.cooldowns):
                    return "attack"

            if self.fortify_button_rect.collidepoint(mx, my):
                return "fortify"

            if self.end_turn_button_rect.collidepoint(mx, my):
                return "end_turn"

            if self.view_deck_button_rect.collidepoint(mx, my):
                return "view_deck"

            if self.run_info_button_rect.collidepoint(mx, my):
                return "run_info"

            if self.doctrines_button_rect.collidepoint(mx, my):
                return "doctrines"

            if self.save_quit_button_rect.collidepoint(mx, my):
                return "save_quit"

            if self.diplomacy_button_rect.collidepoint(mx, my):
                return "diplomacy"

            if self.minor_world_button_rect.collidepoint(mx, my):
                if self.selected_planet and self.selected_planet in galaxy_map.planets:
                    _p = galaxy_map.planets[self.selected_planet]
                    if _p.planet_type == "neutral" and _p.owner == "player":
                        return "minor_world"

            if self.operatives_button_rect.collidepoint(mx, my):
                if len(getattr(campaign_state, 'operatives', [])) > 0:
                    return "operatives"

            # Click empty space — deselect
            self.selected_planet = None

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "save_quit"
            elif event.key == pygame.K_d:
                return "view_deck"
            elif event.key == pygame.K_i:
                return "run_info"

        return None
