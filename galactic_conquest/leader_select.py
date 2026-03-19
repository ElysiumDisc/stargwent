"""
STARGWENT - GALACTIC CONQUEST - Per-Battle Leader Selection

Shows available leaders for the player's faction before a battle.
Player picks which leader to command their forces for this fight.
"""

import asyncio
import math
import os
import pygame
import display_manager

from content_registry import get_all_leaders_for_faction
from .map_renderer import FACTION_COLORS


# Colors (matches conquest CRT aesthetic)
COLOR_BG = (10, 12, 20)
COLOR_TITLE = (255, 200, 80)
COLOR_SELECTED_BORDER = (80, 255, 140)
COLOR_HOVER_BORDER = (100, 200, 180)
COLOR_CARD_BG = (18, 24, 35)
COLOR_CARD_BG_SELECTED = (25, 40, 50)
COLOR_CARD_BORDER = (50, 70, 110)
COLOR_ABILITY_NAME = (255, 220, 100)
COLOR_ABILITY_DESC = (160, 180, 200)
COLOR_HINT = (80, 100, 130)
COLOR_CONFIRM_BG = (30, 100, 50)
COLOR_CONFIRM_HOVER = (50, 140, 70)
COLOR_BACK_BG = (80, 40, 40)
COLOR_BACK_HOVER = (120, 60, 60)
COLOR_CAMPAIGN_BADGE = (200, 180, 100)


async def run_leader_select(screen, player_faction, current_leader):
    """
    Show leader selection screen for a battle.

    Args:
        screen: Pygame display surface
        player_faction: Player's faction string
        current_leader: Player's current campaign leader dict

    Returns:
        Selected leader dict with 'faction' field set, or None if player backed out.
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    # Fonts
    title_font = pygame.font.SysFont("Impact, Arial", max(36, sh // 24), bold=True)
    name_font = pygame.font.SysFont("Impact, Arial", max(20, sh // 45), bold=True)
    ability_font = pygame.font.SysFont("Arial", max(14, sh // 65), bold=True)
    desc_font = pygame.font.SysFont("Arial", max(12, sh // 75))
    btn_font = pygame.font.SysFont("Impact, Arial", max(22, sh // 38), bold=True)
    hint_font = pygame.font.SysFont("Arial", max(13, sh // 70))
    badge_font = pygame.font.SysFont("Arial", max(11, sh // 80), bold=True)

    # Load background
    background = None
    bg_path = os.path.join("assets", "conquest.png")
    try:
        raw = pygame.image.load(bg_path).convert()
        background = pygame.transform.smoothscale(raw, (sw, sh))
    except (pygame.error, FileNotFoundError):
        background = pygame.Surface((sw, sh))
        background.fill(COLOR_BG)

    # Get all leaders for faction
    all_leaders = get_all_leaders_for_faction(player_faction)
    if not all_leaders:
        return current_leader  # No leaders available, use current

    # Find current leader index
    current_name = current_leader.get("name", "") if current_leader else ""
    selected_idx = 0
    for i, leader in enumerate(all_leaders):
        if leader.get("name") == current_name:
            selected_idx = i
            break

    hovered_idx = -1
    hovered_btn = None
    frame = 0

    # Calculate card layout
    num_leaders = len(all_leaders)
    max_per_row = min(5, num_leaders)
    rows = (num_leaders + max_per_row - 1) // max_per_row

    card_w = min(int(sw * 0.17), int((sw * 0.85) / max_per_row))
    card_h = int(sh * 0.52)
    card_gap = int(sw * 0.015)

    # Buttons
    btn_w = int(sw * 0.13)
    btn_h = int(sh * 0.055)
    confirm_rect = pygame.Rect(sw // 2 - btn_w - 15, int(sh * 0.88), btn_w, btn_h)
    back_rect = pygame.Rect(sw // 2 + 15, int(sh * 0.88), btn_w, btn_h)

    # Pre-compute card rects
    card_rects = []
    for row in range(rows):
        start = row * max_per_row
        end = min(start + max_per_row, num_leaders)
        count = end - start
        total_w = count * card_w + (count - 1) * card_gap
        start_x = sw // 2 - total_w // 2
        y = int(sh * 0.15) + row * (card_h + int(sh * 0.02))
        for col in range(count):
            idx = start + col
            x = start_x + col * (card_w + card_gap)
            card_rects.append((idx, pygame.Rect(x, y, card_w, card_h)))

    # Load leader portraits
    portraits = {}
    for leader in all_leaders:
        card_id = leader.get("card_id", "")
        # Try multiple image paths
        paths = [
            leader.get("image_path", ""),
            os.path.join("assets", f"{card_id}_leader.png"),
            os.path.join("assets", "leaders", f"{card_id}.png"),
        ]
        for p in paths:
            if p and os.path.exists(p):
                try:
                    img = pygame.image.load(p).convert_alpha()
                    portrait_h = int(card_h * 0.40)
                    portrait_w = int(card_w * 0.85)
                    portraits[card_id] = pygame.transform.smoothscale(img, (portrait_w, portrait_h))
                except (pygame.error, Exception):
                    pass
                break

    faction_color = FACTION_COLORS.get(player_faction, FACTION_COLORS.get("player", (80, 220, 120)))

    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame += 1

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            elif ev.type == pygame.MOUSEMOTION:
                mx, my = ev.pos
                hovered_idx = -1
                hovered_btn = None
                for idx, rect in card_rects:
                    if rect.collidepoint(mx, my):
                        hovered_idx = idx
                        break
                if confirm_rect.collidepoint(mx, my):
                    hovered_btn = "confirm"
                elif back_rect.collidepoint(mx, my):
                    hovered_btn = "back"
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                for idx, rect in card_rects:
                    if rect.collidepoint(mx, my):
                        selected_idx = idx
                        break
                if confirm_rect.collidepoint(mx, my):
                    leader = dict(all_leaders[selected_idx])
                    leader.setdefault("faction", player_faction)
                    return leader
                if back_rect.collidepoint(mx, my):
                    return None
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return None
                elif ev.key == pygame.K_RETURN or ev.key == pygame.K_SPACE:
                    leader = dict(all_leaders[selected_idx])
                    leader.setdefault("faction", player_faction)
                    return leader
                elif ev.key == pygame.K_LEFT:
                    selected_idx = (selected_idx - 1) % num_leaders
                elif ev.key == pygame.K_RIGHT:
                    selected_idx = (selected_idx + 1) % num_leaders

        # === Draw ===
        screen.blit(background, (0, 0))

        # Dark overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        # Title with pulse
        pulse = 0.85 + 0.15 * math.sin(frame * 0.04)
        t_color = tuple(int(c * pulse) for c in COLOR_TITLE)
        title = title_font.render("SELECT COMMANDER", True, t_color)
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.03)))

        # Subtitle
        sub = hint_font.render(f"Choose your leader for this battle  |  Faction: {player_faction}",
                               True, faction_color)
        screen.blit(sub, (sw // 2 - sub.get_width() // 2, int(sh * 0.09)))

        # Separator
        sep_w = int(sw * 0.6)
        pygame.draw.line(screen, (60, 80, 110),
                         (sw // 2 - sep_w // 2, int(sh * 0.125)),
                         (sw // 2 + sep_w // 2, int(sh * 0.125)), 1)

        # Draw leader cards
        for idx, rect in card_rects:
            leader = all_leaders[idx]
            is_selected = (idx == selected_idx)
            is_hovered = (idx == hovered_idx)
            is_campaign = (leader.get("name") == current_name)

            # Card background
            bg_color = COLOR_CARD_BG_SELECTED if is_selected else COLOR_CARD_BG
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            card_surf.fill((*bg_color, 230))
            screen.blit(card_surf, rect.topleft)

            # Selection glow
            if is_selected:
                glow_pulse = 0.7 + 0.3 * math.sin(frame * 0.06)
                glow_color = tuple(int(c * glow_pulse) for c in COLOR_SELECTED_BORDER)
                pygame.draw.rect(screen, glow_color, rect.inflate(6, 6), 3, border_radius=4)
            elif is_hovered:
                pygame.draw.rect(screen, COLOR_HOVER_BORDER, rect.inflate(4, 4), 2, border_radius=4)
            else:
                pygame.draw.rect(screen, COLOR_CARD_BORDER, rect, 1, border_radius=3)

            # Card content
            pad = int(rect.width * 0.08)
            cx = rect.x + pad
            cy = rect.y + pad
            inner_w = rect.width - 2 * pad

            # Portrait area
            card_id = leader.get("card_id", "")
            portrait_h = int(rect.height * 0.40)
            if card_id in portraits:
                portrait = portraits[card_id]
                px = rect.x + (rect.width - portrait.get_width()) // 2
                screen.blit(portrait, (px, cy))
            else:
                # Colored placeholder
                placeholder_rect = pygame.Rect(cx, cy, inner_w, portrait_h - 10)
                dim_color = tuple(max(30, c // 3) for c in faction_color)
                pygame.draw.rect(screen, dim_color, placeholder_rect, border_radius=3)
                # First letter
                initial = leader.get("name", "?")[0]
                initial_surf = title_font.render(initial, True, faction_color)
                screen.blit(initial_surf, (placeholder_rect.centerx - initial_surf.get_width() // 2,
                                           placeholder_rect.centery - initial_surf.get_height() // 2))
            cy += portrait_h

            # Campaign leader badge
            if is_campaign:
                badge = badge_font.render("CAMPAIGN LEADER", True, COLOR_CAMPAIGN_BADGE)
                badge_bg = pygame.Surface((badge.get_width() + 8, badge.get_height() + 4), pygame.SRCALPHA)
                badge_bg.fill((0, 0, 0, 150))
                screen.blit(badge_bg, (rect.x + (rect.width - badge_bg.get_width()) // 2, cy - 2))
                screen.blit(badge, (rect.x + (rect.width - badge.get_width()) // 2, cy))
                cy += badge.get_height() + 6
            else:
                cy += 4

            # Leader name
            name_text = leader.get("name", "?")
            name_surf = name_font.render(name_text, True, (255, 255, 255))
            # Truncate if too wide — try smaller font, then ellipsis
            if name_surf.get_width() > inner_w:
                name_surf = desc_font.render(name_text, True, (255, 255, 255))
                if name_surf.get_width() > inner_w:
                    while len(name_text) > 1 and desc_font.size(name_text + "...")[0] > inner_w:
                        name_text = name_text[:-1]
                    name_surf = desc_font.render(name_text + "...", True, (255, 255, 255))
            screen.blit(name_surf, (cx, cy))
            cy += name_surf.get_height() + 4

            # Ability name
            ability = leader.get("ability", "")
            ability_surf = ability_font.render(ability, True, COLOR_ABILITY_NAME)
            # Word wrap if needed
            if ability_surf.get_width() > inner_w:
                _draw_wrapped_text(screen, ability, ability_font, COLOR_ABILITY_NAME,
                                   cx, cy, inner_w)
                # Estimate wrapped height
                words = ability.split()
                lines_est = 1
                line = ""
                for w in words:
                    test = line + " " + w if line else w
                    if ability_font.size(test)[0] > inner_w:
                        lines_est += 1
                        line = w
                    else:
                        line = test
                cy += lines_est * (ability_font.get_height() + 2) + 4
            else:
                screen.blit(ability_surf, (cx, cy))
                cy += ability_surf.get_height() + 4

            # Ability description (dimmer, smaller)
            if cy < rect.bottom - 20:
                desc = leader.get("ability_desc", "")
                if desc:
                    remaining_h = rect.bottom - cy - pad
                    _draw_wrapped_text(screen, desc, desc_font, COLOR_ABILITY_DESC,
                                       cx, cy, inner_w, max_height=remaining_h)

        # Buttons
        for rect_btn, label, base_color, hover_color, key in [
            (confirm_rect, "CONFIRM", COLOR_CONFIRM_BG, COLOR_CONFIRM_HOVER, "confirm"),
            (back_rect, "BACK", COLOR_BACK_BG, COLOR_BACK_HOVER, "back"),
        ]:
            is_hover = (hovered_btn == key)
            color = hover_color if is_hover else base_color
            btn_surf = pygame.Surface((rect_btn.width, rect_btn.height), pygame.SRCALPHA)
            btn_surf.fill((*color, 230))
            screen.blit(btn_surf, rect_btn.topleft)
            border_c = (200, 200, 200) if is_hover else (120, 120, 120)
            pygame.draw.rect(screen, border_c, rect_btn, 2)
            lbl = btn_font.render(label, True, (255, 255, 255))
            screen.blit(lbl, (rect_btn.centerx - lbl.get_width() // 2,
                              rect_btn.centery - lbl.get_height() // 2))

        # Hint
        hint = hint_font.render("ENTER = Confirm  |  ESC = Back  |  LEFT/RIGHT = Navigate",
                                True, COLOR_HINT)
        screen.blit(hint, (sw // 2 - hint.get_width() // 2, int(sh * 0.95)))

        display_manager.gpu_flip()


def _draw_wrapped_text(screen, text, font, color, x, y, max_width, max_height=None):
    """Draw word-wrapped text within max_width. Returns final y position."""
    words = text.split()
    line = ""
    cy = y
    line_h = font.get_height() + 2

    for word in words:
        test = line + " " + word if line else word
        if font.size(test)[0] > max_width and line:
            surf = font.render(line, True, color)
            screen.blit(surf, (x, cy))
            cy += line_h
            line = word
            if max_height and cy - y + line_h > max_height:
                return cy
        else:
            line = test

    if line:
        surf = font.render(line, True, color)
        screen.blit(surf, (x, cy))
        cy += line_h

    return cy
