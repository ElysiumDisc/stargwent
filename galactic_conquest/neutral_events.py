"""
STARGWENT - GALACTIC CONQUEST - Neutral Planet Events

Text-based events with choices and roguelite rewards for neutral planets.
Every neutral event always offers the option to add a neutral card to the deck.
Features player's leader portrait alongside event text.
"""

import pygame
import random
import os
import display_manager


# Event definitions: each event has text, and 2 choice options with effects
# A 3rd "neutral card" choice is always added automatically
NEUTRAL_EVENTS = [
    {
        "title": "Abandoned Tok'ra Base",
        "text": "You discover a hidden Tok'ra outpost. Their intelligence files are intact,\n"
                "and the naquadah stores are untouched.",
        "choices": [
            {"label": "Take the intelligence (2 random cards)",
             "effect": "cards", "value": 2},
            {"label": "Salvage the naquadah (+80)",
             "effect": "naquadah", "value": 80},
        ],
    },
    {
        "title": "Naquadah Mine",
        "text": "A rich naquadah vein stretches deep underground.\n"
                "Mining it will take time, but there's also an Ancient device nearby.",
        "choices": [
            {"label": "Mine the naquadah (+120)",
             "effect": "naquadah", "value": 120},
            {"label": "Remove 2 weak cards from your deck",
             "effect": "remove_cards", "value": 2},
        ],
    },
    {
        "title": "Ancient Outpost",
        "text": "An Ancient outpost hums with residual power.\n"
                "Its database contains tactical schematics and card upgrade data.",
        "choices": [
            {"label": "Upgrade a random card's power (+2)",
             "effect": "upgrade_card", "value": 2},
            {"label": "Download tactical data (3 random cards)",
             "effect": "cards", "value": 3},
        ],
    },
    {
        "title": "Trader Caravan",
        "text": "A nomadic trader offers rare goods.\n"
                "Their prices are steep, but the merchandise is genuine.",
        "choices": [
            {"label": "Buy a card (-40 naquadah, +1 card)",
             "effect": "buy_card", "value": 40},
            {"label": "Sell surplus (+60 naquadah)",
             "effect": "naquadah", "value": 60},
        ],
    },
    {
        "title": "Ori Plague",
        "text": "An Ori plague ravages this world. Exposure is unavoidable.\n"
                "You must choose what to sacrifice.",
        "choices": [
            {"label": "Quarantine and lose naquadah (-50)",
             "effect": "naquadah", "value": -50},
            {"label": "Jettison contaminated cargo (-3 random cards)",
             "effect": "lose_cards", "value": 3},
        ],
    },
    {
        "title": "Asgard Archive",
        "text": "A dormant Asgard data core contains technology blueprints.\n"
                "It could revolutionize your deck or fill your coffers.",
        "choices": [
            {"label": "Upgrade 2 random cards (+1 each)",
             "effect": "upgrade_cards_multi", "value": 2},
            {"label": "Sell the tech (+100 naquadah)",
             "effect": "naquadah", "value": 100},
        ],
    },
    {
        "title": "Stargate Malfunction",
        "text": "The Stargate on this world is unstable. You can attempt\n"
                "to repair it for future strategic advantage.",
        "choices": [
            {"label": "Repair the gate (-30 naquadah, remove 1 weak card)",
             "effect": "repair_gate", "value": 30},
            {"label": "Scavenge parts (+50 naquadah)",
             "effect": "naquadah", "value": 50},
        ],
    },
]

# Leader portrait dimensions
PORTRAIT_W = 180
PORTRAIT_H = 250


def _load_leader_portrait(campaign_state, sh):
    """Load the player's leader portrait image. Returns surface or None."""
    leader = campaign_state.player_leader
    if not leader:
        return None
    card_id = leader.get("card_id")
    if not card_id:
        return None
    img_path = os.path.join("assets", f"{card_id}.png")
    try:
        img = pygame.image.load(img_path).convert_alpha()
        # Scale to portrait size, maintaining aspect ratio
        pw = min(PORTRAIT_W, int(sh * 0.18))
        ph = min(PORTRAIT_H, int(sh * 0.25))
        return pygame.transform.smoothscale(img, (pw, ph))
    except (pygame.error, FileNotFoundError):
        return None


def run_neutral_event(screen, campaign_state):
    """
    Show a random neutral planet text event with 2 choices + always a neutral card option.
    Shows player's leader portrait alongside the event.

    Args:
        screen: Pygame display surface
        campaign_state: CampaignState to modify based on choice

    Returns:
        "done" or "quit"
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()
    rng = random.Random()

    # Pick a random event
    event = rng.choice(NEUTRAL_EVENTS)

    # Always add neutral card option as 3rd choice
    all_choices = list(event["choices"]) + [
        {"label": "Recruit a neutral ally (add 1 neutral card)",
         "effect": "neutral_card", "value": 1},
    ]

    # Load background
    try:
        bg = pygame.image.load(os.path.join("assets", "conquest.png")).convert()
        bg = pygame.transform.smoothscale(bg, (sw, sh))
    except (pygame.error, FileNotFoundError):
        bg = pygame.Surface((sw, sh))
        bg.fill((10, 15, 25))

    # Load leader portrait
    portrait = _load_leader_portrait(campaign_state, sh)

    # Fonts
    title_font = pygame.font.SysFont("Impact, Arial", max(36, sh // 25), bold=True)
    text_font = pygame.font.SysFont("Arial", max(20, sh // 45))
    choice_font = pygame.font.SysFont("Arial", max(16, sh // 55), bold=True)
    result_font = pygame.font.SysFont("Arial", max(22, sh // 40), bold=True)
    leader_font = pygame.font.SysFont("Arial", max(14, sh // 70), italic=True)

    # Layout — text area shifts right if portrait present
    text_area_x = int(sw * 0.1)
    if portrait:
        portrait_x = int(sw * 0.06)
        portrait_y = int(sh * 0.18)
        text_area_x = portrait_x + portrait.get_width() + int(sw * 0.04)

    # Choice button rects — 3 buttons stacked vertically
    btn_w = int(sw * 0.50)
    btn_h = int(sh * 0.065)
    btn_x = sw // 2 - btn_w // 2
    btn_y_start = int(sh * 0.50)
    btn_spacing = int(sh * 0.08)

    choice_rects = []
    for i in range(len(all_choices)):
        choice_rects.append(pygame.Rect(btn_x, btn_y_start + i * btn_spacing, btn_w, btn_h))

    chosen = None
    result_text = ""
    hovered = -1

    running = True
    while running:
        clock.tick(60)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "quit"

            elif ev.type == pygame.MOUSEMOTION:
                mx, my = ev.pos
                hovered = -1
                if chosen is None:
                    for i, rect in enumerate(choice_rects):
                        if rect.collidepoint(mx, my):
                            hovered = i
                            break

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                if chosen is None:
                    for i, rect in enumerate(choice_rects):
                        if rect.collidepoint(mx, my) and i < len(all_choices):
                            chosen = i
                            result_text = _apply_choice(campaign_state, all_choices[i], rng)
                            break
                else:
                    # Click after choosing -> continue
                    return "done"

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if chosen is not None:
                        return "done"

        # Draw
        screen.blit(bg, (0, 0))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Leader portrait
        if portrait:
            # Portrait border glow
            border_rect = pygame.Rect(portrait_x - 3, portrait_y - 3,
                                      portrait.get_width() + 6, portrait.get_height() + 6)
            pygame.draw.rect(screen, (80, 140, 100), border_rect, 2)
            screen.blit(portrait, (portrait_x, portrait_y))

            # Leader name below portrait
            leader_name = campaign_state.player_leader.get("name", "")
            if leader_name:
                name_surf = leader_font.render(leader_name, True, (180, 255, 200))
                screen.blit(name_surf, (portrait_x + portrait.get_width() // 2 - name_surf.get_width() // 2,
                                        portrait_y + portrait.get_height() + 6))

        # Event title
        title = title_font.render(event["title"], True, (255, 220, 150))
        title_x = text_area_x if portrait else sw // 2 - title.get_width() // 2
        screen.blit(title, (title_x, int(sh * 0.08)))

        # Event text (multi-line)
        lines = event["text"].split("\n")
        for i, line in enumerate(lines):
            line_surf = text_font.render(line.strip(), True, (220, 220, 220))
            line_x = text_area_x if portrait else sw // 2 - line_surf.get_width() // 2
            screen.blit(line_surf, (line_x, int(sh * 0.22) + i * int(sh * 0.04)))

        # Naquadah display
        naq_text = text_font.render(f"Naquadah: {campaign_state.naquadah}", True, (100, 200, 255))
        screen.blit(naq_text, (sw // 2 - naq_text.get_width() // 2, int(sh * 0.40)))

        # Choice buttons
        for i, choice in enumerate(all_choices):
            if i >= len(choice_rects):
                break
            rect = choice_rects[i]

            if chosen == i:
                color = (60, 140, 80)
            elif chosen is not None:
                color = (40, 40, 40)
            elif i == hovered:
                color = (70, 100, 150)
            elif i == len(all_choices) - 1:
                # Neutral card option gets a distinct color
                color = (70, 70, 50)
            else:
                color = (50, 70, 110)

            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            btn_surf.fill((*color, 220))
            screen.blit(btn_surf, rect.topleft)
            pygame.draw.rect(screen, (180, 180, 180), rect, 2)

            label = choice_font.render(choice["label"], True, (255, 255, 255))
            screen.blit(label, (rect.centerx - label.get_width() // 2,
                                rect.centery - label.get_height() // 2))

        # Result text
        if result_text:
            res = result_font.render(result_text, True, (100, 255, 150))
            screen.blit(res, (sw // 2 - res.get_width() // 2, int(sh * 0.80)))
            cont = text_font.render("Click to continue", True, (180, 180, 180))
            screen.blit(cont, (sw // 2 - cont.get_width() // 2, int(sh * 0.87)))

        display_manager.gpu_flip()

    return "done"


def _apply_choice(campaign_state, choice, rng):
    """Apply the effect of a neutral event choice. Returns result description string."""
    effect = choice["effect"]
    value = choice["value"]

    if effect == "naquadah":
        campaign_state.add_naquadah(value)
        if value >= 0:
            return f"+{value} Naquadah (Total: {campaign_state.naquadah})"
        else:
            return f"{value} Naquadah (Total: {campaign_state.naquadah})"

    elif effect == "cards":
        from cards import ALL_CARDS
        # Add random cards from any faction
        all_ids = [cid for cid, c in ALL_CARDS.items()
                   if getattr(c, 'card_type', '') != "Legendary Commander"
                   and getattr(c, 'row', '') != "weather"]
        picked = rng.sample(all_ids, min(value, len(all_ids)))
        for cid in picked:
            campaign_state.add_card(cid)
        names = [getattr(ALL_CARDS[cid], 'name', cid) for cid in picked]
        return f"Added: {', '.join(names)}"

    elif effect == "neutral_card":
        from cards import ALL_CARDS, FACTION_NEUTRAL
        # Add a random neutral faction card
        neutral_ids = [cid for cid, c in ALL_CARDS.items()
                       if getattr(c, 'faction', None) == FACTION_NEUTRAL
                       and getattr(c, 'card_type', '') != "Legendary Commander"
                       and getattr(c, 'row', '') != "weather"]
        if not neutral_ids:
            # Fallback to any non-legendary card
            neutral_ids = [cid for cid, c in ALL_CARDS.items()
                           if getattr(c, 'card_type', '') != "Legendary Commander"
                           and getattr(c, 'row', '') != "weather"]
        if neutral_ids:
            picked = rng.sample(neutral_ids, min(value, len(neutral_ids)))
            for cid in picked:
                campaign_state.add_card(cid)
            names = [getattr(ALL_CARDS[cid], 'name', cid) for cid in picked]
            return f"Recruited: {', '.join(names)}"
        return "No neutral allies available."

    elif effect == "remove_cards":
        from cards import ALL_CARDS
        deck_with_power = []
        for cid in campaign_state.current_deck:
            card = ALL_CARDS.get(cid)
            power = getattr(card, 'power', 0) if card else 0
            deck_with_power.append((cid, power))
        deck_with_power.sort(key=lambda x: x[1])
        removed = []
        for cid, power in deck_with_power[:value]:
            campaign_state.remove_card(cid)
            removed.append(cid)
        if removed:
            names = [getattr(ALL_CARDS.get(cid), 'name', cid) for cid in removed]
            return f"Removed: {', '.join(names)}"
        return "No cards to remove."

    elif effect == "upgrade_card":
        from cards import ALL_CARDS
        # Upgrade a random card in deck with power
        upgradeable = [cid for cid in campaign_state.current_deck
                       if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)]
        if upgradeable:
            target = rng.choice(upgradeable)
            campaign_state.upgrade_card(target, value)
            name = getattr(ALL_CARDS[target], 'name', target)
            return f"Upgraded: {name} (+{value} power)"
        return "No cards to upgrade."

    elif effect == "upgrade_cards_multi":
        from cards import ALL_CARDS
        upgradeable = list(set(cid for cid in campaign_state.current_deck
                               if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)))
        if upgradeable:
            targets = rng.sample(upgradeable, min(value, len(upgradeable)))
            names = []
            for cid in targets:
                campaign_state.upgrade_card(cid, 1)
                names.append(getattr(ALL_CARDS[cid], 'name', cid))
            return f"Upgraded: {', '.join(names)} (+1 each)"
        return "No cards to upgrade."

    elif effect == "buy_card":
        if campaign_state.naquadah >= value:
            campaign_state.add_naquadah(-value)
            from cards import ALL_CARDS
            all_ids = [cid for cid, c in ALL_CARDS.items()
                       if getattr(c, 'card_type', '') != "Legendary Commander"
                       and getattr(c, 'row', '') != "weather"]
            if all_ids:
                cid = rng.choice(all_ids)
                campaign_state.add_card(cid)
                name = getattr(ALL_CARDS[cid], 'name', cid)
                return f"Bought: {name} (-{value} Naquadah)"
        return "Not enough Naquadah!"

    elif effect == "repair_gate":
        if campaign_state.naquadah >= value:
            campaign_state.add_naquadah(-value)
            # Also remove weakest card
            from cards import ALL_CARDS
            deck_with_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                               for cid in campaign_state.current_deck]
            deck_with_power.sort(key=lambda x: x[1])
            if deck_with_power:
                removed_cid = deck_with_power[0][0]
                campaign_state.remove_card(removed_cid)
                name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
                return f"Gate repaired! Removed weak card: {name} (-{value} Naquadah)"
            return f"Gate repaired! (-{value} Naquadah)"
        return "Not enough Naquadah!"

    elif effect == "lose_cards":
        if len(campaign_state.current_deck) > value:
            removed = rng.sample(campaign_state.current_deck, value)
            for cid in removed:
                campaign_state.remove_card(cid)
            from cards import ALL_CARDS
            names = [getattr(ALL_CARDS.get(cid), 'name', cid) for cid in removed]
            return f"Lost: {', '.join(names)}"
        return "Deck too small to lose cards."

    return "Nothing happened."
