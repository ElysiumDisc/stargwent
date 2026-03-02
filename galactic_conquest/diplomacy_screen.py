"""
STARGWENT - GALACTIC CONQUEST - Diplomacy Screen

CRT-styled screen for managing faction relations: trade, alliance, betray.
Shows active benefits per faction and faction strength indicators.
"""

import asyncio
import pygame
import math
import os
import random
import display_manager

from .conquest_menu import (_get_scanline_overlay, CRT_AMBER, CRT_CYAN,
                             CRT_GREEN, CRT_BORDER, CRT_TEXT, CRT_TEXT_DIM,
                             CRT_BTN_BG, CRT_BTN_HOVER, CRT_BTN_BORDER,
                             CRT_BTN_BORDER_HOVER, FACTION_DISPLAY_COLORS)
from .diplomacy import (get_diplomacy_options, propose_trade, form_alliance,
                          betray_alliance, RELATION_DISPLAY, get_relation,
                          get_trade_income, get_alliance_upkeep,
                          HOSTILE, TRADING, ALLIED)

# Benefit text per relation level
_RELATION_BENEFITS = {
    HOSTILE: [("Counterattacks active", (255, 100, 100))],
    "neutral": [("No active benefits", CRT_TEXT_DIM)],
    TRADING: [
        ("+5 naq/turn", CRT_CYAN),
        ("Card pool access", CRT_CYAN),
        ("No counterattacks", (100, 220, 140)),
    ],
    ALLIED: [
        ("Network bridge", (80, 255, 140)),
        ("50% passive sharing", (80, 255, 140)),
        ("-10 naq/turn upkeep", (255, 180, 80)),
        ("No counterattacks", (100, 220, 140)),
    ],
}


async def run_diplomacy_screen(screen, state, galaxy):
    """Run the diplomacy management screen.

    Returns: None (always returns to map)
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()
    frame_count = 0

    title_font = pygame.font.SysFont("Impact, Arial", max(40, sh // 22), bold=True)
    section_font = pygame.font.SysFont("Impact, Arial", max(22, sh // 42), bold=True)
    info_font = pygame.font.SysFont("Arial", max(17, sh // 55))
    small_font = pygame.font.SysFont("Arial", max(14, sh // 65))
    btn_font = pygame.font.SysFont("Arial", max(15, sh // 60), bold=True)

    # Background
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

    message = None
    message_timer = 0

    # Total planet count for strength bars
    total_planets = max(1, len(galaxy.planets))

    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame_count += 1

        # Build fresh options each frame (state may have changed)
        options = get_diplomacy_options(state, galaxy)

        # Row height includes benefits sub-row
        row_height = int(sh * 0.14)

        # Build button rects
        btn_rects = []  # [(rect, faction, action_name)]
        panel_w = int(sw * 0.65)
        panel_x = sw // 2 - panel_w // 2
        base_y = int(sh * 0.24)

        for i, (faction, rel, actions) in enumerate(options):
            row_y = base_y + i * row_height
            for j, (action, cost, enabled, desc) in enumerate(actions):
                btn_w = int(sw * 0.14)
                btn_h = int(sh * 0.04)
                btn_x = panel_x + panel_w - btn_w - 30 - j * (btn_w + 10)
                rect = pygame.Rect(btn_x, row_y + int(sh * 0.02), btn_w, btn_h)
                btn_rects.append((rect, faction, action, enabled, desc))

        # Close button
        close_w = int(sw * 0.12)
        close_h = int(sh * 0.05)
        close_rect = pygame.Rect(sw // 2 - close_w // 2, int(sh * 0.90), close_w, close_h)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if close_rect.collidepoint(mx, my):
                    return
                for rect, faction, action, enabled, desc in btn_rects:
                    if rect.collidepoint(mx, my) and enabled:
                        if action == "trade":
                            msg = propose_trade(state, faction, galaxy)
                        elif action == "alliance":
                            msg = form_alliance(state, faction, galaxy)
                        elif action == "betray":
                            msg = betray_alliance(state, faction, random.Random())
                        else:
                            msg = None
                        if msg:
                            message = msg
                            message_timer = 150  # ~2.5 seconds

        # Tick message timer
        if message_timer > 0:
            message_timer -= 1
            if message_timer <= 0:
                message = None

        # ===== RENDER =====
        screen.blit(background, (0, 0))
        # Non-SRCALPHA overlay for web performance
        overlay = pygame.Surface((sw, sh))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        screen.blit(overlay, (0, 0))

        # Title
        pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title = title_font.render("DIPLOMACY", True, title_color)
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.06)))

        # Decorative line
        line_y = int(sh * 0.06) + title.get_height() + 8
        line_w = int(sw * 0.25)
        pygame.draw.line(screen, tuple(int(c * pulse) for c in CRT_BORDER),
                         (sw // 2 - line_w // 2, line_y),
                         (sw // 2 + line_w // 2, line_y), 2)

        # Naquadah + diplomacy income display
        trade_inc = get_trade_income(state)
        ally_upkeep = get_alliance_upkeep(state)
        net_diplo = trade_inc - ally_upkeep
        naq_str = f"Naquadah: {state.naquadah}"
        if net_diplo > 0:
            naq_str += f"  |  Diplomacy: +{net_diplo}/turn"
        elif net_diplo < 0:
            naq_str += f"  |  Diplomacy: {net_diplo}/turn"
        naq_text = info_font.render(naq_str, True, CRT_CYAN)
        screen.blit(naq_text, (sw // 2 - naq_text.get_width() // 2, int(sh * 0.15)))

        # Faction rows
        for i, (faction, rel, actions) in enumerate(options):
            row_y = base_y + i * row_height

            # Faction name
            faction_color = FACTION_DISPLAY_COLORS.get(faction, CRT_TEXT)
            fname = section_font.render(faction, True, faction_color)
            screen.blit(fname, (panel_x + 30, row_y))

            # Relation status
            rel_info = RELATION_DISPLAY.get(rel, {"name": rel, "color": CRT_TEXT})
            rel_surf = info_font.render(f"[{rel_info['name']}]", True, rel_info["color"])
            screen.blit(rel_surf, (panel_x + 30 + fname.get_width() + 15, row_y + 5))

            # Planet count + strength bar
            planet_count = galaxy.get_faction_planet_count(faction)
            pc_surf = info_font.render(f"{planet_count} planets", True, CRT_TEXT_DIM)
            pc_x = panel_x + 30
            screen.blit(pc_surf, (pc_x, row_y + int(sh * 0.025)))

            # Strength bar (small horizontal bar after planet count)
            bar_x = pc_x + pc_surf.get_width() + 10
            bar_y = row_y + int(sh * 0.030)
            bar_w = int(sw * 0.08)
            bar_h = max(6, sh // 120)
            strength_ratio = planet_count / total_planets
            pygame.draw.rect(screen, (30, 40, 30), (bar_x, bar_y, bar_w, bar_h))
            fill_w = max(1, int(bar_w * strength_ratio))
            bar_color = faction_color if faction_color != CRT_TEXT else (100, 150, 200)
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h), 1)

            # Benefits sub-row
            benefits = _RELATION_BENEFITS.get(rel, [])
            # Betrayal indicator
            if state.conquest_ability_data.get(f"betrayed_{faction}"):
                benefits = list(benefits) + [("+15% counterattack (betrayed)", (255, 80, 80))]
            benefit_x = panel_x + 30
            benefit_y = row_y + int(sh * 0.05)
            for b_text, b_color in benefits:
                b_surf = small_font.render(b_text, True, b_color)
                screen.blit(b_surf, (benefit_x, benefit_y))
                benefit_x += b_surf.get_width() + 15

            # Action buttons
            for rect, btn_faction, action, enabled, desc in btn_rects:
                if btn_faction != faction:
                    continue
                mx, my = pygame.mouse.get_pos()
                hovered = rect.collidepoint(mx, my)

                if not enabled:
                    bg_color = (10, 12, 10)
                    border_color = (30, 40, 30)
                    text_color = CRT_TEXT_DIM
                elif hovered:
                    bg_color = CRT_BTN_HOVER
                    border_color = CRT_BTN_BORDER_HOVER
                    text_color = (255, 255, 255)
                else:
                    bg_color = CRT_BTN_BG
                    border_color = CRT_BTN_BORDER
                    text_color = CRT_TEXT

                pygame.draw.rect(screen, bg_color, rect)
                pygame.draw.rect(screen, border_color, rect, 2)

                label = btn_font.render(action.upper(), True, text_color)
                screen.blit(label, (rect.centerx - label.get_width() // 2,
                                    rect.centery - label.get_height() // 2))

                # Tooltip on hover
                if hovered and enabled:
                    tip = info_font.render(desc, True, CRT_TEXT)
                    screen.blit(tip, (rect.x, rect.bottom + 4))

        # Close button
        mx, my = pygame.mouse.get_pos()
        close_hovered = close_rect.collidepoint(mx, my)
        close_bg = CRT_BTN_HOVER if close_hovered else CRT_BTN_BG
        close_border = CRT_BTN_BORDER_HOVER if close_hovered else CRT_BTN_BORDER
        pygame.draw.rect(screen, close_bg, close_rect)
        pygame.draw.rect(screen, close_border, close_rect, 2)
        close_label = section_font.render("CLOSE", True, (255, 255, 255) if close_hovered else CRT_TEXT)
        screen.blit(close_label, (close_rect.centerx - close_label.get_width() // 2,
                                   close_rect.centery - close_label.get_height() // 2))

        # Status message
        if message:
            msg_surf = info_font.render(message, True, CRT_GREEN)
            screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, int(sh * 0.85)))

        # CRT scanlines
        scanlines = _get_scanline_overlay(sw, sh, alpha=25)
        screen.blit(scanlines, (0, 0))

        display_manager.gpu_flip()
