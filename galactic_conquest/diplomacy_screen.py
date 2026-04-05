"""
STARGWENT - GALACTIC CONQUEST - Diplomacy Screen

CRT-styled screen for managing faction relations: trade, alliance, betray,
gift, NAP, demand tribute, military aid, joint attack.
Shows favor bars, active benefits per faction, and faction strength indicators.
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
                          betray_alliance, send_gift, demand_tribute,
                          propose_nap, request_military_aid,
                          propose_joint_attack, get_favor,
                          get_nap_turns_remaining, has_active_nap,
                          renew_alliance, get_active_treaty,
                          request_tech_exchange, request_knowledge,
                          propose_revenge_pact,
                          _get_aid_targets, _get_joint_attack_targets,
                          RELATION_DISPLAY, get_relation,
                          get_trade_income, get_alliance_upkeep,
                          get_neutral_income, get_diplomacy_net_income,
                          HOSTILE, NEUTRAL_REL, TRADING, ALLIED,
                          FAVOR_MAX, FAVOR_MIN)

# Benefit text per relation level (enriched tiers)
_RELATION_BENEFITS = {
    HOSTILE: [("Counterattacks active", (255, 100, 100))],
    NEUTRAL_REL: [
        ("+2 naq/turn", (180, 180, 180)),
        ("NAP eligible", (180, 180, 180)),
    ],
    TRADING: [
        ("+8 naq/turn", CRT_CYAN),
        ("-10% building cost (border)", CRT_CYAN),
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

# Favor bar colors by value range
_FAVOR_COLOR_NEGATIVE = (255, 80, 80)
_FAVOR_COLOR_NEUTRAL = (180, 180, 180)
_FAVOR_COLOR_POSITIVE = (80, 255, 140)

# Action button label overrides for compact display
_ACTION_LABELS = {
    "trade": "TRADE",
    "alliance": "ALLIANCE",
    "betray": "BETRAY",
    "gift": "GIFT",
    "nap": "NAP",
    "demand": "DEMAND",
    "aid": "AID",
    "joint": "JOINT ATK",
    "nap_info": "NAP",
    "renew": "RENEW",
    "tech_exchange": "TECH",
    "knowledge": "KNOWLEDGE",
    "revenge_pact": "REVENGE",
}


def _draw_favor_bar(screen, x, y, w, h, favor):
    """Draw a favor bar from -100 to +100 with color gradient."""
    # Background
    pygame.draw.rect(screen, (20, 25, 20), (x, y, w, h))

    # Center line (zero point)
    center_x = x + w // 2
    pygame.draw.line(screen, (60, 60, 60), (center_x, y), (center_x, y + h), 1)

    # Fill bar from center
    if favor > 0:
        fill_w = int((favor / FAVOR_MAX) * (w // 2))
        color = _FAVOR_COLOR_POSITIVE
        pygame.draw.rect(screen, color, (center_x, y, fill_w, h))
    elif favor < 0:
        fill_w = int((abs(favor) / abs(FAVOR_MIN)) * (w // 2))
        color = _FAVOR_COLOR_NEGATIVE
        pygame.draw.rect(screen, color, (center_x - fill_w, y, fill_w, h))

    # Border
    pygame.draw.rect(screen, (80, 80, 80), (x, y, w, h), 1)


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
    favor_font = pygame.font.SysFont("Arial", max(12, sh // 72))

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

    # Scroll state for many factions
    scroll_y = 0

    # Total planet count for strength bars
    total_planets = max(1, len(galaxy.planets))

    # Target selection state for aid/joint attack
    selecting_target = None  # ("aid", faction, targets) or ("joint", faction, targets)
    target_rects = []

    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame_count += 1

        # Build fresh options each frame (state may have changed)
        options = get_diplomacy_options(state, galaxy)

        # Row height — increased to fit favor bar + benefits + buttons
        row_height = int(sh * 0.15)

        # Build button rects
        btn_rects = []  # [(rect, faction, action_name, enabled, desc)]
        panel_w = int(sw * 0.75)
        panel_x = sw // 2 - panel_w // 2
        base_y = int(sh * 0.24) + scroll_y

        for i, (faction, rel, actions) in enumerate(options):
            row_y = base_y + i * row_height
            btn_w = int(sw * 0.10)
            btn_h = int(sh * 0.035)
            # Place buttons in a row at the right side
            for j, (action, cost, enabled, desc) in enumerate(actions):
                btn_x = panel_x + panel_w - (len(actions) - j) * (btn_w + 6)
                rect = pygame.Rect(btn_x, row_y + int(sh * 0.065), btn_w, btn_h)
                btn_rects.append((rect, faction, action, enabled, desc))

        # Close button
        close_w = int(sw * 0.12)
        close_h = int(sh * 0.05)
        close_rect = pygame.Rect(sw // 2 - close_w // 2, int(sh * 0.92), close_w, close_h)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if selecting_target:
                        selecting_target = None
                    else:
                        return
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y += event.y * 30
                scroll_y = min(0, scroll_y)  # Don't scroll above top
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # Handle target selection overlay
                if selecting_target:
                    for trect, target_faction in target_rects:
                        if trect.collidepoint(mx, my):
                            sel_type, sel_faction, _ = selecting_target
                            rng = random.Random()
                            if sel_type == "aid":
                                msg = request_military_aid(
                                    state, sel_faction, target_faction, galaxy, rng)
                            elif sel_type == "joint":
                                msg = propose_joint_attack(
                                    state, sel_faction, target_faction, galaxy, rng)
                            else:
                                msg = None
                            if msg:
                                message = msg
                                message_timer = 180
                            selecting_target = None
                            break
                    else:
                        selecting_target = None
                    continue

                if close_rect.collidepoint(mx, my):
                    return
                for rect, faction, action, enabled, desc in btn_rects:
                    if rect.collidepoint(mx, my) and enabled:
                        rng = random.Random()
                        if action == "trade":
                            msg = propose_trade(state, faction, galaxy)
                        elif action == "alliance":
                            msg = form_alliance(state, faction, galaxy)
                        elif action == "betray":
                            msg = betray_alliance(state, faction, rng)
                        elif action == "gift":
                            msg = send_gift(state, faction, galaxy)
                        elif action == "nap":
                            msg = propose_nap(state, faction, galaxy, rng)
                        elif action == "demand":
                            msg = demand_tribute(state, faction, galaxy, rng)
                        elif action == "renew":
                            msg = renew_alliance(state, faction)
                        elif action == "tech_exchange":
                            msg = request_tech_exchange(state, faction)
                        elif action == "knowledge":
                            msg = request_knowledge(state, faction)
                        elif action == "revenge_pact":
                            msg = propose_revenge_pact(state, faction)
                        elif action == "aid":
                            # Need target selection
                            targets = _get_aid_targets(state, faction, galaxy)
                            if len(targets) == 1:
                                msg = request_military_aid(
                                    state, faction, targets[0], galaxy, rng)
                            elif targets:
                                selecting_target = ("aid", faction, targets)
                                msg = None
                            else:
                                msg = None
                        elif action == "joint":
                            targets = _get_joint_attack_targets(state, faction, galaxy)
                            if len(targets) == 1:
                                msg = propose_joint_attack(
                                    state, faction, targets[0], galaxy, rng)
                            elif targets:
                                selecting_target = ("joint", faction, targets)
                                msg = None
                            else:
                                msg = None
                        else:
                            msg = None
                        if msg:
                            message = msg
                            message_timer = 180  # ~3 seconds
                        break

        # Tick message timer
        if message_timer > 0:
            message_timer -= 1
            if message_timer <= 0:
                message = None

        # ===== RENDER =====
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        screen.blit(overlay, (0, 0))

        # Title
        pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title = title_font.render("DIPLOMACY", True, title_color)
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.05)))

        # Decorative line
        line_y = int(sh * 0.05) + title.get_height() + 8
        line_w = int(sw * 0.25)
        pygame.draw.line(screen, tuple(int(c * pulse) for c in CRT_BORDER),
                         (sw // 2 - line_w // 2, line_y),
                         (sw // 2 + line_w // 2, line_y), 2)

        # Naquadah + diplomacy income display
        net_diplo = get_diplomacy_net_income(state)
        naq_str = f"Naquadah: {state.naquadah}"
        if net_diplo > 0:
            naq_str += f"  |  Diplomacy: +{net_diplo}/turn"
        elif net_diplo < 0:
            naq_str += f"  |  Diplomacy: {net_diplo}/turn"
        # Breakdown
        neutral_inc = get_neutral_income(state)
        trade_inc = get_trade_income(state)
        ally_upkeep = get_alliance_upkeep(state)
        parts = []
        if neutral_inc > 0:
            parts.append(f"Neutral: +{neutral_inc}")
        if trade_inc > 0:
            parts.append(f"Trade: +{trade_inc}")
        if ally_upkeep > 0:
            parts.append(f"Upkeep: -{ally_upkeep}")
        if parts:
            naq_str += f"  ({', '.join(parts)})"
        naq_text = info_font.render(naq_str, True, CRT_CYAN)
        screen.blit(naq_text, (sw // 2 - naq_text.get_width() // 2, int(sh * 0.14)))

        # G3: Coalition banner
        if state.coalition.get("active"):
            members = ", ".join(state.coalition.get("members", []))
            turns_left = state.coalition.get("turns_remaining", 0)
            coalition_msg = f"!! COALITION AGAINST YOU: {members} ({turns_left}t) !!"
            coalition_color = (255, 100, 100) if (frame_count // 30) % 2 == 0 else (255, 200, 100)
            coalition_surf = info_font.render(coalition_msg, True, coalition_color)
            screen.blit(coalition_surf,
                        (sw // 2 - coalition_surf.get_width() // 2, int(sh * 0.17)))

        # Faction rows
        for i, (faction, rel, actions) in enumerate(options):
            row_y = base_y + i * row_height

            # Skip if off-screen
            if row_y + row_height < int(sh * 0.20) or row_y > int(sh * 0.88):
                continue

            # Faction name
            faction_color = FACTION_DISPLAY_COLORS.get(faction, CRT_TEXT)
            fname = section_font.render(faction, True, faction_color)
            screen.blit(fname, (panel_x + 20, row_y))

            # Relation status
            rel_info = RELATION_DISPLAY.get(rel, {"name": rel, "color": CRT_TEXT})
            rel_surf = info_font.render(f"[{rel_info['name']}]", True, rel_info["color"])
            screen.blit(rel_surf, (panel_x + 20 + fname.get_width() + 12, row_y + 5))

            # G2a: AI adopted doctrines — small caption below faction name
            ai_doctrines = state.ai_doctrines.get(faction, [])
            if ai_doctrines:
                from .doctrines import DOCTRINE_TREES, _POLICY_LOOKUP
                # Pick the most recent (highest tier) adopted policy to display
                latest = ai_doctrines[-1]
                pair = _POLICY_LOOKUP.get(latest)
                if pair:
                    _tree_id, _idx = pair
                    policy_name = DOCTRINE_TREES[_tree_id]["policies"][_idx]["name"]
                    tree_color = DOCTRINE_TREES[_tree_id]["color"]
                    doctrine_surf = small_font.render(
                        f"Doctrine: {policy_name}", True, tree_color)
                    screen.blit(doctrine_surf,
                                (panel_x + 20, row_y + int(sh * 0.045)))

            # NAP indicator / Alliance treaty timer
            indicator_x = panel_x + 20 + fname.get_width() + 12 + rel_surf.get_width() + 10
            nap_turns = get_nap_turns_remaining(state, faction)
            if nap_turns > 0:
                nap_surf = small_font.render(f"NAP: {nap_turns}t", True, (100, 220, 180))
                screen.blit(nap_surf, (indicator_x, row_y + 7))
            else:
                alliance_treaty = get_active_treaty(state, "alliance", faction)
                if alliance_treaty is not None:
                    tr = alliance_treaty["turns_remaining"]
                    if tr > 0:
                        treaty_color = (140, 220, 255) if tr > 5 else (255, 200, 80)
                        treaty_surf = small_font.render(f"Treaty: {tr}t", True, treaty_color)
                        screen.blit(treaty_surf, (indicator_x, row_y + 7))
                    else:
                        # Needs renewal
                        treaty_surf = small_font.render("Treaty: renew!", True, (255, 180, 80))
                        screen.blit(treaty_surf, (indicator_x, row_y + 7))

            # Planet count + strength bar
            planet_count = galaxy.get_faction_planet_count(faction)
            pc_surf = small_font.render(f"{planet_count} planets", True, CRT_TEXT_DIM)
            pc_x = panel_x + 20
            screen.blit(pc_surf, (pc_x, row_y + int(sh * 0.025)))

            # Strength bar
            bar_x = pc_x + pc_surf.get_width() + 8
            bar_y = row_y + int(sh * 0.030)
            bar_w = int(sw * 0.06)
            bar_h = max(5, sh // 130)
            strength_ratio = planet_count / total_planets
            pygame.draw.rect(screen, (30, 40, 30), (bar_x, bar_y, bar_w, bar_h))
            fill_w = max(1, int(bar_w * strength_ratio))
            bar_color = faction_color if faction_color != CRT_TEXT else (100, 150, 200)
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h), 1)

            # Favor bar (next to strength bar)
            favor = get_favor(state, faction)
            favor_label = favor_font.render(f"Favor: {favor:+d}", True,
                                            _FAVOR_COLOR_POSITIVE if favor > 0
                                            else _FAVOR_COLOR_NEGATIVE if favor < 0
                                            else _FAVOR_COLOR_NEUTRAL)
            favor_lx = bar_x + bar_w + 15
            screen.blit(favor_label, (favor_lx, row_y + int(sh * 0.025)))
            favor_bar_x = favor_lx + favor_label.get_width() + 6
            favor_bar_w = int(sw * 0.08)
            favor_bar_h = max(5, sh // 130)
            _draw_favor_bar(screen, favor_bar_x, bar_y, favor_bar_w, favor_bar_h, favor)

            # Benefits sub-row
            benefits = _RELATION_BENEFITS.get(rel, [])
            # NAP active indicator
            if nap_turns > 0 and rel == NEUTRAL_REL:
                benefits = list(benefits) + [("No counterattacks (NAP)", (100, 220, 140))]
            # Betrayal indicator
            if state.conquest_ability_data.get(f"betrayed_{faction}"):
                benefits = list(benefits) + [("+15% counter (betrayed)", (255, 80, 80))]
            if state.conquest_ability_data.get(f"_nap_broken_{faction}"):
                benefits = list(benefits) + [("+10% counter (NAP broken)", (255, 80, 80))]

            benefit_x = panel_x + 20
            benefit_y = row_y + int(sh * 0.045)
            for b_text, b_color in benefits:
                b_surf = small_font.render(b_text, True, b_color)
                screen.blit(b_surf, (benefit_x, benefit_y))
                benefit_x += b_surf.get_width() + 12

            # Action buttons
            for rect, btn_faction, action, enabled, desc in btn_rects:
                if btn_faction != faction:
                    continue
                mx, my = pygame.mouse.get_pos()
                hovered = rect.collidepoint(mx, my) and not selecting_target

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

                label_text = _ACTION_LABELS.get(action, action.upper())
                label = btn_font.render(label_text, True, text_color)
                screen.blit(label, (rect.centerx - label.get_width() // 2,
                                    rect.centery - label.get_height() // 2))

                # Tooltip on hover
                if hovered and enabled:
                    from .tooltip import draw_tooltip
                    draw_tooltip(screen, desc, rect, small_font)

        # Close button
        mx, my = pygame.mouse.get_pos()
        close_hovered = close_rect.collidepoint(mx, my) and not selecting_target
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
            screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, int(sh * 0.88)))

        # Target selection overlay
        if selecting_target:
            sel_type, sel_faction, targets = selecting_target
            # Dark overlay
            sel_overlay = pygame.Surface((sw, sh))
            sel_overlay.fill((0, 0, 0))
            sel_overlay.set_alpha(160)
            screen.blit(sel_overlay, (0, 0))

            action_name = "Military Aid" if sel_type == "aid" else "Joint Attack"
            sel_title = section_font.render(
                f"Select target for {action_name} with {sel_faction}:", True, CRT_AMBER)
            screen.blit(sel_title, (sw // 2 - sel_title.get_width() // 2, int(sh * 0.35)))

            target_rects = []
            for ti, tfaction in enumerate(targets):
                t_btn_w = int(sw * 0.20)
                t_btn_h = int(sh * 0.05)
                t_btn_x = sw // 2 - t_btn_w // 2
                t_btn_y = int(sh * 0.42) + ti * (t_btn_h + 10)
                t_rect = pygame.Rect(t_btn_x, t_btn_y, t_btn_w, t_btn_h)
                t_hovered = t_rect.collidepoint(mx, my)
                t_bg = CRT_BTN_HOVER if t_hovered else CRT_BTN_BG
                t_border = CRT_BTN_BORDER_HOVER if t_hovered else CRT_BTN_BORDER
                pygame.draw.rect(screen, t_bg, t_rect)
                pygame.draw.rect(screen, t_border, t_rect, 2)
                t_label = info_font.render(tfaction, True,
                                           (255, 255, 255) if t_hovered else CRT_TEXT)
                screen.blit(t_label, (t_rect.centerx - t_label.get_width() // 2,
                                       t_rect.centery - t_label.get_height() // 2))
                target_rects.append((t_rect, tfaction))

            cancel_text = small_font.render("Press ESC to cancel", True, CRT_TEXT_DIM)
            screen.blit(cancel_text, (sw // 2 - cancel_text.get_width() // 2,
                                       int(sh * 0.42) + len(targets) * (int(sh * 0.05) + 10) + 10))

        # CRT scanlines
        scanlines = _get_scanline_overlay(sw, sh, alpha=25)
        screen.blit(scanlines, (0, 0))

        display_manager.gpu_flip()
