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


def apply_crisis(campaign_state, galaxy, crisis, rng=None):
    """Apply a crisis event's effects.

    Args:
        campaign_state: CampaignState instance
        galaxy: GalaxyMap instance
        crisis: Crisis event dict
        rng: Optional Random instance

    Returns:
        Result message string.
    """
    if rng is None:
        rng = random.Random()

    effect = crisis["effect"]

    if effect == "replicator_outbreak":
        from cards import ALL_CARDS
        # Remove weakest card from player deck
        deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                      for cid in campaign_state.current_deck]
        deck_power.sort(key=lambda x: x[1])
        removed_name = "none"
        if deck_power and len(campaign_state.current_deck) > 10:
            removed_cid = deck_power[0][0]
            campaign_state.remove_card(removed_cid)
            removed_name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
        return f"Replicators consumed your weakest card: {removed_name}"

    elif effect == "ori_crusade":
        campaign_state.add_naquadah(-40)
        # A random AI faction loses a planet to neutral
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
        campaign_state.add_naquadah(-20)
        # Reduce all upgrades by 1
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
        # Upgrade 2 strongest cards by +2
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
        # Reset all cooldowns
        campaign_state.cooldowns.clear()
        parts = []
        if upgraded:
            parts.append(f"Ascended: {', '.join(upgraded)} (+2)")
        parts.append("All cooldowns reset!")
        return " | ".join(parts)

    elif effect == "wraith_invasion":
        campaign_state.add_naquadah(-30)
        # Convert a random player non-homeworld planet to hostile
        player_non_hw = [(pid, p) for pid, p in galaxy.planets.items()
                         if p.owner == "player" and p.planet_type != "homeworld"]
        lost_name = "none"
        if player_non_hw:
            pid, planet = rng.choice(player_non_hw)
            lost_name = planet.name
            # Give to a random existing AI faction
            ai_factions = list(set(p.owner for p in galaxy.planets.values()
                                   if p.owner not in ("player", "neutral")))
            new_owner = rng.choice(ai_factions) if ai_factions else "neutral"
            galaxy.transfer_ownership(pid, new_owner)
            campaign_state.planet_ownership[pid] = new_owner
        return f"-30 Naquadah. Wraith overran {lost_name}!"

    return "The crisis passes without incident."


async def show_crisis_screen(screen, crisis, result_text):
    """Show a dramatic crisis event screen.

    Args:
        screen: Pygame display surface
        crisis: Crisis event dict
        result_text: Result message from apply_crisis()
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("Impact, Arial", max(48, sh // 18), bold=True)
    text_font = pygame.font.SysFont("Arial", max(22, sh // 40))
    result_font = pygame.font.SysFont("Arial", max(20, sh // 45), bold=True)
    hint_font = pygame.font.SysFont("Arial", max(16, sh // 60))

    crisis_color = tuple(crisis.get("color", (255, 200, 100)))

    running = True
    frame = 0
    while running:
        clock.tick(60)
        await asyncio.sleep(0)
        frame += 1

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            elif ev.type == pygame.KEYDOWN or ev.type == pygame.MOUSEBUTTONDOWN:
                if frame > 30:  # Require at least 0.5s before dismissing
                    running = False

        # Dark background with crisis-colored vignette
        screen.fill((10, 10, 15))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((*crisis_color, 30))
        screen.blit(overlay, (0, 0))

        # Warning flash effect (first second)
        if frame < 60 and frame % 20 < 10:
            flash = pygame.Surface((sw, sh), pygame.SRCALPHA)
            flash.fill((*crisis_color, 40))
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

        # Result
        res_surf = result_font.render(result_text, True, (255, 220, 100))
        screen.blit(res_surf, (sw // 2 - res_surf.get_width() // 2, int(sh * 0.65)))

        # Continue hint
        if frame > 30:
            hint = hint_font.render("Press any key to continue", True, (150, 150, 150))
            screen.blit(hint, (sw // 2 - hint.get_width() // 2, int(sh * 0.82)))

        display_manager.gpu_flip()
