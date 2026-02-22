"""
STARGWENT - GALACTIC CONQUEST - Reward Screen

Post-victory screen: pick 1+ cards from defeated faction + naquadah display.
Card reward quality and quantity scale with planets controlled.
"""

import pygame
import random
import os
import copy
import display_manager
from cards import ALL_CARDS


# Card visual constants
CARD_W = 200
CARD_H = 280


def get_faction_card_pool(faction: str, include_powerful=False) -> list[str]:
    """Get card IDs belonging to a faction.

    Args:
        faction: Faction name
        include_powerful: If True, include higher-tier cards (Legendary Commanders excluded always)
    """
    pool = []
    for card_id, card in ALL_CARDS.items():
        if getattr(card, 'faction', None) == faction:
            # Always exclude legendary commanders and weather cards
            if getattr(card, 'card_type', '') == "Legendary Commander":
                continue
            if getattr(card, 'row', '') == "weather":
                continue
            pool.append(card_id)
    return pool


def _get_reward_tier(player_planet_count, total_planets):
    """Determine reward tier based on territory control.

    More planets = better rewards:
    - Tier 1 (3-5 planets): 3 choices, base naquadah
    - Tier 2 (6-9 planets): 4 choices, +25% naquadah, access to stronger cards
    - Tier 3 (10+ planets): 5 choices, +50% naquadah, best cards available
    """
    if player_planet_count >= 10:
        return 3
    elif player_planet_count >= 6:
        return 2
    return 1


def run_reward_screen(screen, campaign_state, defeated_faction, planet_type="territory",
                      galaxy_map=None, bonus_message=""):
    """
    Show post-victory rewards: naquadah + pick 1 of N cards (scales with territory).

    Args:
        screen: Pygame display surface
        campaign_state: CampaignState to modify
        defeated_faction: Faction whose cards are offered
        planet_type: "territory" or "homeworld" (affects naquadah reward)
        galaxy_map: GalaxyMap instance for planet-count scaling

    Returns:
        "done" when player has picked, or "quit" if they exit.
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    # Determine territory control tier
    player_planets = 3  # default
    total_planets = 20
    if galaxy_map:
        player_planets = galaxy_map.get_player_planet_count()
        total_planets = len(galaxy_map.planets)

    tier = _get_reward_tier(player_planets, total_planets)

    # Scale naquadah reward with tier
    base_naq = 150 if planet_type == "homeworld" else 80
    naquadah_multiplier = {1: 1.0, 2: 1.25, 3: 1.5}
    naquadah_reward = int(base_naq * naquadah_multiplier[tier])

    # Number of card choices scales with tier
    num_choices = {1: 3, 2: 4, 3: 5}[tier]

    # Generate card choices from defeated faction
    pool = get_faction_card_pool(defeated_faction, include_powerful=(tier >= 2))
    rng = random.Random()

    # Sort pool by power for tier-based filtering
    if tier >= 2:
        # Higher tiers: bias toward stronger cards
        pool_with_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0) for cid in pool]
        pool_with_power.sort(key=lambda x: -x[1])
        # Tier 2: top 75%, Tier 3: top 100% but guaranteed at least one strong card
        if tier == 2:
            cutoff = max(3, int(len(pool_with_power) * 0.75))
            pool = [cid for cid, _ in pool_with_power[:cutoff]]
        # Tier 3 uses full pool but we'll ensure variety

    choices = []
    if len(pool) >= num_choices:
        choices = rng.sample(pool, num_choices)
    elif pool:
        choices = list(pool)
        while len(choices) < num_choices:
            choices.append(rng.choice(pool))

    # Load card images
    card_surfaces = []
    for card_id in choices:
        card = ALL_CARDS.get(card_id)
        if not card:
            continue
        img_path = os.path.join("assets", f"{card_id}.png")
        try:
            img = pygame.image.load(img_path).convert_alpha()
            img = pygame.transform.smoothscale(img, (CARD_W, CARD_H))
        except (pygame.error, FileNotFoundError):
            # Fallback card surface
            img = pygame.Surface((CARD_W, CARD_H))
            img.fill((40, 50, 70))
            font = pygame.font.SysFont("Arial", 16)
            name_surf = font.render(getattr(card, 'name', card_id), True, (255, 255, 255))
            img.blit(name_surf, (10, 10))
            power = getattr(card, 'power', 0)
            if power:
                pw_surf = font.render(f"Power: {power}", True, (100, 200, 255))
                img.blit(pw_surf, (10, 35))
        card_surfaces.append((card_id, img))

    # Load background
    try:
        bg = pygame.image.load(os.path.join("assets", "conquest.png")).convert()
        bg = pygame.transform.smoothscale(bg, (sw, sh))
    except (pygame.error, FileNotFoundError):
        bg = pygame.Surface((sw, sh))
        bg.fill((10, 15, 25))

    # Fonts
    title_font = pygame.font.SysFont("Impact, Arial", max(36, sh // 25), bold=True)
    info_font = pygame.font.SysFont("Arial", max(20, sh // 45), bold=True)
    card_font = pygame.font.SysFont("Arial", max(14, sh // 70))
    tier_font = pygame.font.SysFont("Arial", max(16, sh // 55), italic=True)

    # Card layout — adaptive spacing based on number of cards
    card_spacing = max(int(sw * 0.02), int(sw * 0.05) - num_choices * 6)
    total_cards_w = len(card_surfaces) * CARD_W + (len(card_surfaces) - 1) * card_spacing
    start_x = (sw - total_cards_w) // 2
    card_y = int(sh * 0.32)

    card_rects = []
    for i in range(len(card_surfaces)):
        x = start_x + i * (CARD_W + card_spacing)
        card_rects.append(pygame.Rect(x, card_y, CARD_W, CARD_H))

    # Skip button (if no cards to pick)
    skip_rect = pygame.Rect(sw // 2 - 100, int(sh * 0.85), 200, 50)

    selected = None
    hovered = -1
    picked = False
    naquadah_applied = False

    running = True
    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                hovered = -1
                for i, rect in enumerate(card_rects):
                    if rect.collidepoint(mx, my):
                        hovered = i
                        break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if not picked:
                    for i, rect in enumerate(card_rects):
                        if rect.collidepoint(mx, my) and i < len(choices):
                            selected = i
                            picked = True
                            # Add card to deck
                            campaign_state.add_card(choices[i])
                            break

                    if not card_surfaces and skip_rect.collidepoint(mx, my):
                        picked = True

                # After picking, click anywhere to continue
                if picked and not naquadah_applied:
                    pass  # wait one more frame
                elif picked:
                    return "done"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if picked:
                        return "done"
                    # Allow escape without picking (forfeit card choice)
                    picked = True

        # Apply naquadah once after picking
        if picked and not naquadah_applied:
            campaign_state.add_naquadah(naquadah_reward)
            naquadah_applied = True

        # Draw
        screen.blit(bg, (0, 0))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # Title
        title = title_font.render("VICTORY — CHOOSE YOUR REWARD", True, (255, 220, 100))
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.04)))

        # Naquadah reward
        naq_text = info_font.render(f"+{naquadah_reward} Naquadah", True, (100, 200, 255))
        screen.blit(naq_text, (sw // 2 - naq_text.get_width() // 2, int(sh * 0.11)))

        # Faction bonus message
        if bonus_message:
            bonus_surf = info_font.render(f"Faction Bonus{bonus_message}", True, (180, 255, 150))
            screen.blit(bonus_surf, (sw // 2 - bonus_surf.get_width() // 2, int(sh * 0.14)))

        # Tier info
        tier_labels = {
            1: "Standard Rewards",
            2: "Enhanced Rewards (6+ planets)",
            3: "Supreme Rewards (10+ planets)",
        }
        tier_colors = {1: (160, 160, 160), 2: (100, 200, 255), 3: (255, 220, 100)}
        tier_text = tier_font.render(tier_labels[tier], True, tier_colors[tier])
        screen.blit(tier_text, (sw // 2 - tier_text.get_width() // 2, int(sh * 0.16)))

        # Instruction
        if not picked:
            inst = info_font.render(f"Pick 1 card from the defeated {defeated_faction}:", True, (200, 200, 200))
        else:
            inst = info_font.render("Card added to your deck! Click to continue.", True, (100, 255, 100))
        screen.blit(inst, (sw // 2 - inst.get_width() // 2, int(sh * 0.22)))

        # Draw cards
        for i, (card_id, surf) in enumerate(card_surfaces):
            rect = card_rects[i]
            draw_y = rect.y
            if i == hovered and not picked:
                draw_y -= 15

            # Selected glow
            if i == selected:
                glow = pygame.Surface((CARD_W + 20, CARD_H + 20), pygame.SRCALPHA)
                glow.fill((255, 220, 100, 60))
                screen.blit(glow, (rect.x - 10, draw_y - 10))

            screen.blit(surf, (rect.x, draw_y))

            # Card name below
            card = ALL_CARDS.get(card_id)
            if card:
                name = card_font.render(getattr(card, 'name', card_id), True, (220, 220, 220))
                screen.blit(name, (rect.centerx - name.get_width() // 2, draw_y + CARD_H + 8))
                power = getattr(card, 'power', 0)
                if power:
                    pw = card_font.render(f"Power: {power}", True, (180, 220, 255))
                    screen.blit(pw, (rect.centerx - pw.get_width() // 2, draw_y + CARD_H + 26))

            # Dim unselected after pick
            if picked and i != selected:
                dim = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 140))
                screen.blit(dim, (rect.x, draw_y))

        # Skip button (only if no cards)
        if not card_surfaces and not picked:
            pygame.draw.rect(screen, (80, 120, 80), skip_rect)
            pygame.draw.rect(screen, (200, 200, 200), skip_rect, 2)
            skip_text = info_font.render("CONTINUE", True, (255, 255, 255))
            screen.blit(skip_text, (skip_rect.centerx - skip_text.get_width() // 2,
                                    skip_rect.centery - skip_text.get_height() // 2))

        display_manager.gpu_flip()

    return "done"
