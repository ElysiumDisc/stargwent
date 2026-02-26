"""
STARGWENT - GALACTIC CONQUEST - Neutral Planet Events

Text-based events with choices and roguelite rewards for neutral planets.
Every neutral event always offers the option to add a neutral card to the deck.
Features player's leader portrait alongside event text.
"""

import asyncio
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
    # === New events (v8.5) ===
    {
        "title": "Replicator Infestation",
        "text": "Replicators swarm across this planet's surface.\n"
                "You can fight them or salvage their technology.",
        "choices": [
            {"label": "Fight them (lose 2 random cards)",
             "effect": "lose_cards", "value": 2},
            {"label": "Salvage tech (gain 1 powerful card)",
             "effect": "powerful_card", "value": 1},
        ],
    },
    {
        "title": "Prior Conversion",
        "text": "An Ori Prior offers forbidden power.\n"
                "The price may be steeper than it seems.",
        "choices": [
            {"label": "Accept the Ori's gift (gain powerful Ori card, lose 2 cards)",
             "effect": "prior_conversion", "value": 1},
            {"label": "Reject and loot the shrine (+50 naquadah)",
             "effect": "naquadah", "value": 50},
        ],
    },
    {
        "title": "Time Dilation Field",
        "text": "An Asgard time dilation device is still active.\n"
                "Time moves differently here — use it wisely.",
        "choices": [
            {"label": "Exploit the field (double next naquadah reward: +100)",
             "effect": "naquadah", "value": 100},
            {"label": "Study the tech (upgrade 3 random cards +1)",
             "effect": "upgrade_cards_multi", "value": 3},
        ],
    },
    {
        "title": "Tok'ra Alliance",
        "text": "Tok'ra operatives offer their services.\n"
                "Their intelligence network or their soldiers could aid your cause.",
        "choices": [
            {"label": "Accept operatives (+2 faction cards)",
             "effect": "cards", "value": 2},
            {"label": "Take intelligence (+80 naquadah)",
             "effect": "naquadah", "value": 80},
        ],
    },
    {
        "title": "Furling Ruins",
        "text": "The legendary Furlings left behind a treasure vault.\n"
                "Ancient artifacts shimmer inside.",
        "choices": [
            {"label": "Claim an artifact (gain a random relic)",
             "effect": "gain_relic", "value": 1},
            {"label": "Sell everything (+100 naquadah)",
             "effect": "naquadah", "value": 100},
        ],
    },
    {
        "title": "Ba'al's Clone Lab",
        "text": "You've found one of Ba'al's cloning facilities.\n"
                "The technology could duplicate your strongest assets.",
        "choices": [
            {"label": "Clone your best card (duplicate strongest)",
             "effect": "duplicate_card", "value": 1},
            {"label": "Destroy the lab (+80 naquadah)",
             "effect": "naquadah", "value": 80},
        ],
    },
    {
        "title": "Wraith Culling Beam",
        "text": "A Wraith cruiser culls the planet's population.\n"
                "You must act fast — fight or hide.",
        "choices": [
            {"label": "Fight the Wraith (lose 1, gain 2 faction cards)",
             "effect": "wraith_fight", "value": 1},
            {"label": "Hide underground (-40 naquadah)",
             "effect": "naquadah", "value": -40},
        ],
    },
    {
        "title": "Ascension Trial",
        "text": "An ascended being offers to test your worthiness.\n"
                "The trial will transform your deck — for better or worse.",
        "choices": [
            {"label": "Accept the trial (remove 3 weakest, upgrade 2 strongest +2)",
             "effect": "ascension_trial", "value": 1},
            {"label": "Decline respectfully (+50 naquadah)",
             "effect": "naquadah", "value": 50},
        ],
    },
    # === New events (v8.9) ===
    {
        "title": "Nox Sanctuary",
        "text": "The peaceful Nox reveal themselves in a hidden grove.\n"
                "They offer healing wisdom or a gift of concealment.",
        "choices": [
            {"label": "Learn healing arts (upgrade 3 weakest cards +2)",
             "effect": "nox_healing", "value": 3},
            {"label": "Accept Nox cloak (remove 2 strongest enemy-faction cards, gain stealth card)",
             "effect": "nox_cloak", "value": 1},
        ],
    },
    {
        "title": "Tollan Ion Cannon",
        "text": "A derelict Tollan ion cannon sits atop this mountain.\n"
                "Its technology is incredibly advanced — and valuable.",
        "choices": [
            {"label": "Salvage the cannon (+150 naquadah)",
             "effect": "naquadah", "value": 150},
            {"label": "Reverse-engineer it (upgrade all cards with power >= 5 by +1)",
             "effect": "tollan_upgrade", "value": 5},
        ],
    },
    {
        "title": "Goa'uld Sarcophagus Chamber",
        "text": "A golden sarcophagus hums with regenerative energy.\n"
                "Its power is seductive, but the cost may be your humanity.",
        "choices": [
            {"label": "Use the sarcophagus (duplicate 2 strongest cards, lose 3 weakest)",
             "effect": "sarcophagus_gamble", "value": 2},
            {"label": "Destroy it (+80 naquadah, remove 1 weak card)",
             "effect": "destroy_and_purge", "value": 80},
        ],
    },
    {
        "title": "Ori Supergate",
        "text": "A dormant Ori Supergate looms in orbit.\n"
                "Activating it is a massive gamble — glory or ruin.",
        "choices": [
            {"label": "Activate the Supergate (50% chance: +200 naq OR lose 4 random cards)",
             "effect": "ori_supergate_gamble", "value": 200},
            {"label": "Scavenge components (+70 naquadah)",
             "effect": "naquadah", "value": 70},
        ],
    },
    {
        "title": "Pegasus Expedition",
        "text": "A wormhole to the Pegasus galaxy opens briefly.\n"
                "Wraith technology and Ancient relics await beyond.",
        "choices": [
            {"label": "Send an expedition (gain 3 powerful cards, -60 naquadah)",
             "effect": "pegasus_expedition", "value": 3},
            {"label": "Study the wormhole data (upgrade 2 random cards +2)",
             "effect": "upgrade_cards_big", "value": 2},
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


async def run_neutral_event(screen, campaign_state):
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
        await asyncio.sleep(0)

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

    elif effect == "powerful_card":
        from cards import ALL_CARDS
        # Add a high-power card from any faction
        powerful = [(cid, getattr(c, 'power', 0) or 0) for cid, c in ALL_CARDS.items()
                    if getattr(c, 'card_type', '') != "Legendary Commander"
                    and getattr(c, 'row', '') != "weather"
                    and (getattr(c, 'power', 0) or 0) >= 6]
        if powerful:
            cid, _ = rng.choice(powerful)
            campaign_state.add_card(cid)
            name = getattr(ALL_CARDS[cid], 'name', cid)
            return f"Salvaged: {name}"
        return "No powerful cards available."

    elif effect == "prior_conversion":
        from cards import ALL_CARDS
        # Gain a powerful card, lose 2 random
        powerful = [(cid, getattr(c, 'power', 0) or 0) for cid, c in ALL_CARDS.items()
                    if getattr(c, 'card_type', '') != "Legendary Commander"
                    and getattr(c, 'row', '') != "weather"
                    and (getattr(c, 'power', 0) or 0) >= 7]
        gained_name = "nothing"
        if powerful:
            cid, _ = rng.choice(powerful)
            campaign_state.add_card(cid)
            gained_name = getattr(ALL_CARDS[cid], 'name', cid)
        # Lose 2 cards
        lost_names = []
        if len(campaign_state.current_deck) > 2:
            removed = rng.sample(campaign_state.current_deck, 2)
            for rid in removed:
                campaign_state.remove_card(rid)
                lost_names.append(getattr(ALL_CARDS.get(rid), 'name', rid))
        return f"Gained: {gained_name} | Lost: {', '.join(lost_names) if lost_names else 'none'}"

    elif effect == "gain_relic":
        # Award a random relic not yet owned
        try:
            from .relics import RELICS
            owned = getattr(campaign_state, 'relics', [])
            available = [rid for rid in RELICS if rid not in owned]
            if available:
                relic_id = rng.choice(available)
                campaign_state.add_relic(relic_id)
                relic = RELICS[relic_id]
                return f"Found relic: {relic.name} — {relic.description}"
            return "No relics available (you have them all!)"
        except (ImportError, AttributeError):
            return "Relic system not available."

    elif effect == "duplicate_card":
        from cards import ALL_CARDS
        # Duplicate the strongest card in deck
        deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                      for cid in campaign_state.current_deck]
        deck_power.sort(key=lambda x: -x[1])
        if deck_power:
            best_cid = deck_power[0][0]
            campaign_state.add_card(best_cid)
            name = getattr(ALL_CARDS.get(best_cid), 'name', best_cid)
            return f"Cloned: {name}"
        return "No cards to clone."

    elif effect == "wraith_fight":
        from cards import ALL_CARDS
        # Lose 1 card, gain 2 from player's faction
        lost_name = "none"
        if campaign_state.current_deck:
            lost_cid = rng.choice(campaign_state.current_deck)
            campaign_state.remove_card(lost_cid)
            lost_name = getattr(ALL_CARDS.get(lost_cid), 'name', lost_cid)
        # Gain 2 faction cards
        faction = campaign_state.player_faction
        faction_pool = [cid for cid, c in ALL_CARDS.items()
                        if getattr(c, 'faction', None) == faction
                        and getattr(c, 'card_type', '') != "Legendary Commander"
                        and getattr(c, 'row', '') != "weather"]
        gained = []
        if faction_pool:
            picks = rng.sample(faction_pool, min(2, len(faction_pool)))
            for cid in picks:
                campaign_state.add_card(cid)
                gained.append(getattr(ALL_CARDS[cid], 'name', cid))
        return f"Lost: {lost_name} | Gained: {', '.join(gained) if gained else 'none'}"

    elif effect == "ascension_trial":
        from cards import ALL_CARDS
        # Remove 3 weakest, upgrade 2 strongest +2
        deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                      for cid in campaign_state.current_deck]
        deck_power.sort(key=lambda x: x[1])
        # Remove 3 weakest (if deck large enough)
        removed = []
        if len(deck_power) > 10:
            for cid, _ in deck_power[:3]:
                campaign_state.remove_card(cid)
                removed.append(getattr(ALL_CARDS.get(cid), 'name', cid))
        # Upgrade 2 strongest
        upgraded = []
        deck_power_desc = sorted(deck_power, key=lambda x: -x[1])
        for cid, pw in deck_power_desc[:2]:
            if pw > 0:
                campaign_state.upgrade_card(cid, 2)
                upgraded.append(getattr(ALL_CARDS.get(cid), 'name', cid))
        parts = []
        if removed:
            parts.append(f"Removed: {', '.join(removed)}")
        if upgraded:
            parts.append(f"Upgraded +2: {', '.join(upgraded)}")
        return " | ".join(parts) if parts else "Trial complete."

    elif effect == "destroy_and_purge":
        campaign_state.add_naquadah(value)
        from cards import ALL_CARDS
        deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                      for cid in campaign_state.current_deck]
        deck_power.sort(key=lambda x: x[1])
        if deck_power and len(campaign_state.current_deck) > 10:
            removed_cid = deck_power[0][0]
            campaign_state.remove_card(removed_cid)
            name = getattr(ALL_CARDS.get(removed_cid), 'name', removed_cid)
            return f"+{value} Naquadah, removed weak card: {name}"
        return f"+{value} Naquadah (Total: {campaign_state.naquadah})"

    elif effect == "nox_healing":
        from cards import ALL_CARDS
        # Upgrade the N weakest cards by +2
        deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                      for cid in campaign_state.current_deck]
        deck_power.sort(key=lambda x: x[1])
        upgradeable = [(cid, pw) for cid, pw in deck_power if pw > 0]
        targets = upgradeable[:value]
        names = []
        for cid, _ in targets:
            campaign_state.upgrade_card(cid, 2)
            names.append(getattr(ALL_CARDS.get(cid), 'name', cid))
        if names:
            return f"Nox healing: {', '.join(names)} (+2 each)"
        return "No cards to heal."

    elif effect == "nox_cloak":
        from cards import ALL_CARDS
        # Remove 2 enemy-faction cards from deck, add a powerful neutral card
        player_faction = campaign_state.player_faction
        enemy_in_deck = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                         for cid in campaign_state.current_deck
                         if ALL_CARDS.get(cid)
                         and getattr(ALL_CARDS[cid], 'faction', None) != player_faction
                         and getattr(ALL_CARDS[cid], 'faction', None) is not None]
        enemy_in_deck.sort(key=lambda x: -x[1])
        removed = []
        for cid, _ in enemy_in_deck[:2]:
            campaign_state.remove_card(cid)
            removed.append(getattr(ALL_CARDS.get(cid), 'name', cid))
        # Add a powerful card
        powerful = [(cid, getattr(c, 'power', 0) or 0) for cid, c in ALL_CARDS.items()
                    if getattr(c, 'card_type', '') != "Legendary Commander"
                    and getattr(c, 'row', '') != "weather"
                    and (getattr(c, 'power', 0) or 0) >= 6]
        gained_name = "none"
        if powerful:
            cid, _ = rng.choice(powerful)
            campaign_state.add_card(cid)
            gained_name = getattr(ALL_CARDS[cid], 'name', cid)
        parts = []
        if removed:
            parts.append(f"Removed: {', '.join(removed)}")
        parts.append(f"Gained: {gained_name}")
        return " | ".join(parts)

    elif effect == "tollan_upgrade":
        from cards import ALL_CARDS
        # Upgrade all cards with power >= threshold by +1
        threshold = value
        upgraded = []
        seen = set()
        for cid in campaign_state.current_deck:
            if cid in seen:
                continue
            card = ALL_CARDS.get(cid)
            if card and (getattr(card, 'power', 0) or 0) >= threshold:
                campaign_state.upgrade_card(cid, 1)
                upgraded.append(getattr(card, 'name', cid))
                seen.add(cid)
        if upgraded:
            return f"Tollan tech: {', '.join(upgraded)} (+1 each)"
        return "No cards powerful enough to upgrade."

    elif effect == "sarcophagus_gamble":
        from cards import ALL_CARDS
        deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                      for cid in campaign_state.current_deck]
        deck_power.sort(key=lambda x: -x[1])
        # Duplicate N strongest
        duped = []
        for cid, pw in deck_power[:value]:
            if pw > 0:
                campaign_state.add_card(cid)
                duped.append(getattr(ALL_CARDS.get(cid), 'name', cid))
        # Remove 3 weakest
        deck_power.sort(key=lambda x: x[1])
        removed = []
        for cid, pw in deck_power[:3]:
            if len(campaign_state.current_deck) > 10:
                campaign_state.remove_card(cid)
                removed.append(getattr(ALL_CARDS.get(cid), 'name', cid))
        parts = []
        if duped:
            parts.append(f"Duplicated: {', '.join(duped)}")
        if removed:
            parts.append(f"Lost: {', '.join(removed)}")
        return " | ".join(parts) if parts else "The sarcophagus had no effect."

    elif effect == "ori_supergate_gamble":
        # 50% chance: big reward or big loss
        if rng.random() < 0.5:
            campaign_state.add_naquadah(value)
            return f"The Supergate surges with power! +{value} Naquadah!"
        else:
            from cards import ALL_CARDS
            if len(campaign_state.current_deck) > 6:
                lost = rng.sample(campaign_state.current_deck, min(4, len(campaign_state.current_deck) - 5))
                for cid in lost:
                    campaign_state.remove_card(cid)
                names = [getattr(ALL_CARDS.get(cid), 'name', cid) for cid in lost]
                return f"Ori forces attack! Lost: {', '.join(names)}"
            return "The Supergate collapses harmlessly."

    elif effect == "pegasus_expedition":
        from cards import ALL_CARDS
        cost = 60
        if campaign_state.naquadah >= cost:
            campaign_state.add_naquadah(-cost)
            powerful = [(cid, getattr(c, 'power', 0) or 0) for cid, c in ALL_CARDS.items()
                        if getattr(c, 'card_type', '') != "Legendary Commander"
                        and getattr(c, 'row', '') != "weather"
                        and (getattr(c, 'power', 0) or 0) >= 5]
            if powerful:
                picks = rng.sample(powerful, min(value, len(powerful)))
                names = []
                for cid, _ in picks:
                    campaign_state.add_card(cid)
                    names.append(getattr(ALL_CARDS[cid], 'name', cid))
                return f"Expedition returns! Gained: {', '.join(names)} (-{cost} naq)"
            return f"Expedition found nothing. (-{cost} naq)"
        return "Not enough Naquadah for the expedition!"

    elif effect == "upgrade_cards_big":
        from cards import ALL_CARDS
        upgradeable = list(set(cid for cid in campaign_state.current_deck
                               if ALL_CARDS.get(cid) and getattr(ALL_CARDS[cid], 'power', 0)))
        if upgradeable:
            targets = rng.sample(upgradeable, min(value, len(upgradeable)))
            names = []
            for cid in targets:
                campaign_state.upgrade_card(cid, 2)
                names.append(getattr(ALL_CARDS[cid], 'name', cid))
            return f"Upgraded: {', '.join(names)} (+2 each)"
        return "No cards to upgrade."

    return "Nothing happened."
