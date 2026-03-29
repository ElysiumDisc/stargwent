"""
STARGWENT - GALACTIC CONQUEST - Crisis Events

Galaxy-wide crisis events that trigger randomly after turn 5.
10% chance per turn (respects crisis_cooldown on CampaignState).
Each crisis affects ALL factions and creates dramatic turning points.
"""

import asyncio
import random
import pygame
import display_manager


# Crisis definitions: each has a title, description, and an apply function name
CRISIS_EVENTS = [
    {
        "id": "replicator_outbreak",
        "title": "Replicator Outbreak",
        "text": "Self-replicating machines swarm across the galaxy!\n"
                "All factions lose their weakest unit card.",
        "effect": "replicator_outbreak",
        "color": (180, 180, 200),
    },
    {
        "id": "ori_crusade",
        "title": "Ori Crusade",
        "text": "The Ori launch a devastating crusade across the galaxy!\n"
                "All players suffer -40 naquadah. AI factions lose a random planet.",
        "effect": "ori_crusade",
        "color": (255, 200, 100),
    },
    {
        "id": "galactic_plague",
        "title": "Galactic Plague",
        "text": "A virulent plague spreads through the Stargate network!\n"
                "All card upgrades are reduced by 1 (min 0). -20 naquadah.",
        "effect": "galactic_plague",
        "color": (100, 200, 80),
    },
    {
        "id": "ascension_wave",
        "title": "Ascension Wave",
        "text": "A wave of ascension energy sweeps the galaxy!\n"
                "Your 2 strongest cards gain +2 power. Cooldowns reset.",
        "effect": "ascension_wave",
        "color": (200, 220, 255),
    },
    {
        "id": "wraith_invasion",
        "title": "Wraith Invasion",
        "text": "The Wraith have come from the Pegasus galaxy!\n"
                "A random neutral planet becomes hostile. -30 naquadah.",
        "effect": "wraith_invasion",
        "color": (140, 80, 160),
    },
]

CRISIS_CHOICES = {
    "replicator_outbreak": {
        "a": {"label": "Sacrifice weakest card", "desc": "Lose your weakest card. Outbreak contained."},
        "b": {"label": "Risk containment", "desc": "40% chance enemy loses 2 cards. 60% you lose 2 cards."},
        "c": {"label": "Isolate & study", "desc": "Gain Replicator Nanites relic, no cards lost.",
               "requires": "sensor_array_2"},
    },
    "ori_crusade": {
        "a": {"label": "Pay for shields (-60 naq)", "desc": "Heavy cost but no other damage."},
        "b": {"label": "Endure the crusade", "desc": "-40 naq, but an AI faction loses a planet."},
        "c": {"label": "Allied defense", "desc": "Split cost with ally. Only -30 naq.",
               "requires": "has_ally"},
    },
    "galactic_plague": {
        "a": {"label": "Quarantine (-30 naq)", "desc": "Pay more but keep all card upgrades intact."},
        "b": {"label": "Endure the plague", "desc": "-20 naq, all card upgrades reduced by 1."},
        "c": {"label": "Ancient cure", "desc": "No losses. Upgrades intact. Free.",
               "requires": "ascension_complete"},
    },
    "ascension_wave": {
        "a": {"label": "Channel into power", "desc": "+2 power to 2 strongest cards. Reset cooldowns."},
        "b": {"label": "Store as wisdom", "desc": "+20 wisdom. Reset cooldowns."},
        "c": {"label": "Harmonic resonance", "desc": "+1 power to ALL cards. Reset cooldowns.",
               "requires": "3_ancient_planets"},
    },
    "wraith_invasion": {
        "a": {"label": "Stand and fight", "desc": "Keep the planet but lose 50 naquadah."},
        "b": {"label": "Evacuate", "desc": "Lose the planet but only -20 naquadah."},
        "c": {"label": "Covert counterattack", "desc": "60% keep planet. Only -10 naq.",
               "requires": "3_operatives"},
    },
}


def check_crisis_option_c(campaign_state, galaxy, crisis_effect):
    """Check if the conditional 3rd crisis option is available.

    Returns True if the player meets the requirements for option C.
    """
    choices = CRISIS_CHOICES.get(crisis_effect, {})
    option_c = choices.get("c")
    if not option_c:
        return False

    req = option_c.get("requires", "")

    if req == "sensor_array_2":
        # Need 2+ Sensor Arrays on player planets
        count = sum(1 for pid, bid in campaign_state.buildings.items()
                    if bid == "sensor_array"
                    and galaxy.planets.get(pid)
                    and galaxy.planets[pid].owner == "player")
        return count >= 2

    elif req == "has_ally":
        return any(rel == "allied" for rel in campaign_state.faction_relations.values())

    elif req == "ascension_complete":
        return "ascension" in campaign_state.completed_doctrines

    elif req == "3_ancient_planets":
        from .doctrines import ANCIENT_PLANETS
        count = sum(1 for pid, p in galaxy.planets.items()
                    if p.name in ANCIENT_PLANETS and p.owner == "player")
        return count >= 3

    elif req == "3_operatives":
        active_ops = sum(1 for op in campaign_state.operatives
                         if op.get("state") in ("active", "idle", "moving", "establishing"))
        return active_ops >= 3

    return False


def should_trigger_crisis(campaign_state):
    """Check if a crisis should trigger this turn.

    Returns True if crisis should fire (10% chance after turn 5, if cooldown is 0).
    Ori Shield Matrix perk reduces chance to 5%.
    """
    if campaign_state.turn_number < 5:
        return False
    if campaign_state.crisis_cooldown > 0:
        return False
    from .meta_progression import has_perk
    chance = 0.05 if has_perk("crisis_resistance") else 0.10
    return random.random() < chance


def pick_crisis(campaign_state):
    """Pick a random crisis event. Returns crisis dict or None."""
    if not CRISIS_EVENTS:
        return None
    return random.choice(CRISIS_EVENTS)


def apply_crisis(campaign_state, galaxy, crisis, rng=None, choice="b"):
    """Apply a crisis event's effects.

    Args:
        campaign_state: CampaignState instance
        galaxy: GalaxyMap instance
        crisis: Crisis event dict
        rng: Optional Random instance
        choice: "a" (safe/costly), "b" (risky/cheap), or "c" (conditional)

    Returns:
        Result message string.
    """
    if rng is None:
        rng = random.Random()

    effect = crisis["effect"]

    if effect == "replicator_outbreak":
        from cards import ALL_CARDS
        if choice == "c":
            # Conditional: Sensor Arrays isolate and study — gain relic, no losses
            campaign_state.add_relic("replicator_nanites")
            return "Sensor Arrays isolated the Replicators! Gained Replicator Nanites relic."
        elif choice == "a":
            # Safe: remove weakest card (original behavior)
            deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                          for cid in campaign_state.current_deck]
            deck_power.sort(key=lambda x: x[1])
            removed_name = "none"
            if deck_power and len(campaign_state.current_deck) > 10:
                removed_cid = deck_power[0][0]
                campaign_state.remove_card(removed_cid)
                removed_name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
            return f"Replicators consumed your weakest card: {removed_name}. Outbreak contained."
        else:
            # Risky: 40% reward, 60% lose 2 cards
            if rng.random() < 0.40:
                campaign_state.add_naquadah(10)
                return "Containment gamble paid off! Replicators destroyed. +10 naq."
            else:
                deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                              for cid in campaign_state.current_deck]
                deck_power.sort(key=lambda x: x[1])
                removed = []
                for cid, _pw in deck_power:
                    if len(campaign_state.current_deck) > 10 and len(removed) < 2:
                        campaign_state.remove_card(cid)
                        removed.append(getattr(ALL_CARDS.get(cid), 'name', cid))
                names = ", ".join(removed) if removed else "none"
                return f"Containment failed! Replicators consumed 2 cards: {names}."

    elif effect == "ori_crusade":
        if choice == "c":
            # Conditional: Allied defense — split cost
            campaign_state.add_naquadah(-30)
            return "-30 Naquadah. Allied forces shared the burden — shields held!"
        elif choice == "a":
            # Safe: pay 60 naq, no planet damage
            campaign_state.add_naquadah(-60)
            return "-60 Naquadah. Shields held — no planetary damage."
        else:
            # Risky: original behavior
            campaign_state.add_naquadah(-40)
            ai_planets = [(pid, p) for pid, p in galaxy.planets.items()
                          if p.owner not in ("player", "neutral")]
            flipped_name = "none"
            if ai_planets:
                pid, planet = rng.choice(ai_planets)
                flipped_name = planet.name
                galaxy.transfer_ownership(pid, "neutral")
                campaign_state.planet_ownership[pid] = "neutral"
            return f"-40 Naquadah. Ori crusade destabilized {flipped_name}."

    elif effect == "galactic_plague":
        if choice == "c":
            # Conditional: Ancient cure — no losses at all
            return "Ancient knowledge neutralized the plague. No losses!"
        elif choice == "a":
            # Safe: pay 30 naq, keep upgrades
            campaign_state.add_naquadah(-30)
            return "-30 Naquadah. Quarantine successful — card upgrades intact."
        else:
            # Risky: original behavior
            campaign_state.add_naquadah(-20)
            downgraded = 0
            for cid in list(campaign_state.upgraded_cards):
                if campaign_state.upgraded_cards[cid] > 0:
                    campaign_state.upgraded_cards[cid] -= 1
                    downgraded += 1
                if campaign_state.upgraded_cards[cid] <= 0:
                    del campaign_state.upgraded_cards[cid]
            return f"-20 Naquadah. Plague weakened {downgraded} card upgrade(s)."

    elif effect == "ascension_wave":
        from cards import ALL_CARDS
        if choice == "c":
            # Conditional: Harmonic resonance — +1 power to ALL cards
            upgraded_count = 0
            for cid in campaign_state.current_deck:
                card = ALL_CARDS.get(cid)
                if card and getattr(card, 'power', 0) and getattr(card, 'power', 0) > 0:
                    campaign_state.upgrade_card(cid, 1)
                    upgraded_count += 1
            campaign_state.cooldowns.clear()
            return f"Harmonic resonance! {upgraded_count} cards gained +1 power. Cooldowns reset!"
        elif choice == "a":
            # Channel into power: +2 to 2 strongest + reset cooldowns (original)
            deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                          for cid in campaign_state.current_deck]
            deck_power.sort(key=lambda x: -x[1])
            upgraded = []
            seen = set()
            for cid, pw in deck_power:
                if cid in seen or pw <= 0:
                    continue
                campaign_state.upgrade_card(cid, 2)
                upgraded.append(getattr(ALL_CARDS.get(cid), 'name', cid))
                seen.add(cid)
                if len(upgraded) >= 2:
                    break
            campaign_state.cooldowns.clear()
            parts = []
            if upgraded:
                parts.append(f"Ascended: {', '.join(upgraded)} (+2)")
            parts.append("All cooldowns reset!")
            return " | ".join(parts)
        else:
            # Store as wisdom: +20 wisdom + reset cooldowns
            campaign_state.wisdom = getattr(campaign_state, 'wisdom', 0) + 20
            campaign_state.cooldowns.clear()
            return "+20 Wisdom. All cooldowns reset!"

    elif effect == "wraith_invasion":
        if choice == "c":
            # Conditional: Covert counterattack — 60% keep planet, only -10 naq
            campaign_state.add_naquadah(-10)
            if rng.random() < 0.60:
                return "-10 Naquadah. Operatives repelled the Wraith! All planets secure."
            else:
                player_non_hw = [(pid, p) for pid, p in galaxy.planets.items()
                                 if p.owner == "player" and p.planet_type != "homeworld"]
                lost_name = "none"
                if player_non_hw:
                    pid, planet = rng.choice(player_non_hw)
                    lost_name = planet.name
                    ai_factions = list(set(p.owner for p in galaxy.planets.values()
                                           if p.owner not in ("player", "neutral")))
                    new_owner = rng.choice(ai_factions) if ai_factions else "neutral"
                    galaxy.transfer_ownership(pid, new_owner)
                    campaign_state.planet_ownership[pid] = new_owner
                return f"-10 Naquadah. Counterattack failed — Wraith took {lost_name}."
        elif choice == "a":
            # Stand and fight: pay 50 naq, keep planet
            campaign_state.add_naquadah(-50)
            return "-50 Naquadah. Wraith repelled — all planets secure!"
        else:
            # Evacuate: lose planet but only -20 naq
            campaign_state.add_naquadah(-20)
            player_non_hw = [(pid, p) for pid, p in galaxy.planets.items()
                             if p.owner == "player" and p.planet_type != "homeworld"]
            lost_name = "none"
            if player_non_hw:
                pid, planet = rng.choice(player_non_hw)
                lost_name = planet.name
                ai_factions = list(set(p.owner for p in galaxy.planets.values()
                                       if p.owner not in ("player", "neutral")))
                new_owner = rng.choice(ai_factions) if ai_factions else "neutral"
                galaxy.transfer_ownership(pid, new_owner)
                campaign_state.planet_ownership[pid] = new_owner
            return f"-20 Naquadah. Evacuated {lost_name} — Wraith took control."

    return "The crisis passes without incident."


async def show_crisis_screen(screen, crisis, choices=None, has_option_c=False):
    """Show a dramatic crisis event screen with choice buttons.

    Args:
        screen: Pygame display surface
        crisis: Crisis event dict
        choices: Optional dict with "a" and "b" keys (and optionally "c"),
                 each having "label" and "desc".  If None, falls back to legacy
                 "press any key" behavior and returns "b".
        has_option_c: If True and choices has "c", show the third button.

    Returns:
        "a", "b", or "c" depending on which button the player clicks.
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("Impact, Arial", max(48, sh // 18), bold=True)
    text_font = pygame.font.SysFont("Arial", max(22, sh // 40))
    btn_font = pygame.font.SysFont("Arial", max(18, sh // 50), bold=True)
    desc_font = pygame.font.SysFont("Arial", max(14, sh // 65))
    hint_font = pygame.font.SysFont("Arial", max(16, sh // 60))

    crisis_color = tuple(crisis.get("color", (255, 200, 100)))

    # Button layout — adapts to 2 or 3 buttons
    show_c = has_option_c and choices and "c" in choices
    if show_c:
        btn_w = int(sw * 0.26)
        btn_h = int(sh * 0.10)
        gap = int(sw * 0.02)
        total_w = btn_w * 3 + gap * 2
        btn_y = int(sh * 0.65)
        start_x = sw // 2 - total_w // 2
        btn_a_rect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        btn_b_rect = pygame.Rect(start_x + btn_w + gap, btn_y, btn_w, btn_h)
        btn_c_rect = pygame.Rect(start_x + 2 * (btn_w + gap), btn_y, btn_w, btn_h)
    else:
        btn_w = int(sw * 0.30)
        btn_h = int(sh * 0.10)
        gap = int(sw * 0.04)
        btn_y = int(sh * 0.68)
        btn_a_rect = pygame.Rect(sw // 2 - btn_w - gap // 2, btn_y, btn_w, btn_h)
        btn_b_rect = pygame.Rect(sw // 2 + gap // 2, btn_y, btn_w, btn_h)
        btn_c_rect = None

    frame = 0
    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame += 1

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "b"
            if choices is None:
                # Legacy: press any key to dismiss
                if (ev.type == pygame.KEYDOWN or ev.type == pygame.MOUSEBUTTONDOWN) and frame > 30:
                    return "b"
            else:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and frame > 30:
                    if btn_a_rect.collidepoint(ev.pos):
                        return "a"
                    if btn_b_rect.collidepoint(ev.pos):
                        return "b"
                    if btn_c_rect and btn_c_rect.collidepoint(ev.pos):
                        return "c"

        # Dark background with crisis-colored vignette
        screen.fill((10, 10, 15))
        overlay = pygame.Surface((sw, sh))
        overlay.fill(crisis_color)
        overlay.set_alpha(30)
        screen.blit(overlay, (0, 0))

        # Warning flash effect (first second)
        if frame < 60 and frame % 20 < 10:
            flash = pygame.Surface((sw, sh))
            flash.fill(crisis_color)
            flash.set_alpha(40)
            screen.blit(flash, (0, 0))

        # Crisis warning header
        import math
        pulse = 0.7 + 0.3 * math.sin(frame * 0.05)
        warn_color = tuple(int(c * pulse) for c in (255, 80, 80))
        warn_text = title_font.render("CRISIS EVENT", True, warn_color)
        screen.blit(warn_text, (sw // 2 - warn_text.get_width() // 2, int(sh * 0.12)))

        # Crisis title
        title_surf = title_font.render(crisis["title"], True, crisis_color)
        screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, int(sh * 0.25)))

        # Crisis text (multi-line)
        lines = crisis["text"].split("\n")
        for i, line in enumerate(lines):
            line_surf = text_font.render(line.strip(), True, (220, 220, 220))
            screen.blit(line_surf, (sw // 2 - line_surf.get_width() // 2,
                                    int(sh * 0.42) + i * int(sh * 0.05)))

        if choices is not None and frame > 30:
            # Draw choice buttons
            mx, my = pygame.mouse.get_pos()
            buttons = [
                (btn_a_rect, "a", (40, 100, 60)),
                (btn_b_rect, "b", (100, 60, 40)),
            ]
            if show_c:
                buttons.append((btn_c_rect, "c", (60, 60, 120)))
            for rect, key, base_color in buttons:
                choice_data = choices[key]
                hovered = rect.collidepoint(mx, my)
                color = tuple(min(255, c + 40) for c in base_color) if hovered else base_color
                pygame.draw.rect(screen, color, rect)
                border_color = (255, 220, 100) if key == "c" else ((200, 200, 200) if hovered else (120, 120, 120))
                pygame.draw.rect(screen, border_color, rect, 2)
                # Label
                lbl = btn_font.render(choice_data["label"], True, (255, 255, 255))
                screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                  rect.y + int(btn_h * 0.20)))
                # Description
                dsc = desc_font.render(choice_data["desc"], True, (200, 200, 200))
                screen.blit(dsc, (rect.centerx - dsc.get_width() // 2,
                                  rect.y + int(btn_h * 0.60)))
        elif choices is None and frame > 30:
            # Legacy hint
            hint = hint_font.render("Press any key to continue", True, (150, 150, 150))
            screen.blit(hint, (sw // 2 - hint.get_width() // 2, int(sh * 0.82)))

        display_manager.gpu_flip()
