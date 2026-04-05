"""
STARGWENT - GALACTIC CONQUEST - Doctrine Screen

CRT-styled screen with 5 vertical columns (one per tree).
Each column shows tree name, 4 policies, costs, and completion bonus.
"""

import asyncio
import pygame
import math
import os
import display_manager

from .conquest_menu import (_get_scanline_overlay, CRT_AMBER, CRT_CYAN,
                             CRT_GREEN, CRT_BORDER, CRT_TEXT, CRT_TEXT_DIM,
                             CRT_BTN_BG, CRT_BTN_HOVER, CRT_BTN_BORDER,
                             CRT_BTN_BORDER_HOVER)
from .doctrines import (DOCTRINE_TREES, get_policy_cost, can_adopt,
                          adopt_policy, is_tree_complete, get_next_policy,
                          get_active_effects, get_wisdom_per_turn)
from .wisdom_actions import get_available_actions, use_wisdom_action


async def run_doctrine_screen(screen, state, galaxy):
    """Run the doctrine tree screen.

    Returns: None (always returns to map)
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()
    frame_count = 0

    title_font = pygame.font.SysFont("Impact, Arial", max(36, sh // 24), bold=True)
    tree_font = pygame.font.SysFont("Impact, Arial", max(18, sh // 50), bold=True)
    policy_font = pygame.font.SysFont("Arial", max(14, sh // 65))
    small_font = pygame.font.SysFont("Arial", max(12, sh // 75))
    btn_font = pygame.font.SysFont("Arial", max(13, sh // 70), bold=True)

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

    tree_ids = list(DOCTRINE_TREES.keys())

    # Close button
    close_w = int(sw * 0.10)
    close_h = int(sh * 0.045)
    close_rect = pygame.Rect(sw // 2 - close_w // 2, int(sh * 0.92), close_w, close_h)

    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame_count += 1

        # Build adopt button rects
        adopt_rects = []  # (rect, policy_id, can_adopt_flag)
        col_w = int(sw * 0.17)
        col_gap = int(sw * 0.015)
        total_w = len(tree_ids) * col_w + (len(tree_ids) - 1) * col_gap
        start_x = sw // 2 - total_w // 2
        col_top = int(sh * 0.20)

        # Each tree may have a different policy count now that tier 3
        # branches out into 3 mutually-exclusive options. Derive the
        # slot height from the longest tree so every column lines up.
        max_policies = max(len(t["policies"]) for t in DOCTRINE_TREES.values())
        # Available vertical space inside a column (after header + bonus)
        col_body_h = int(sh * 0.58)
        slot_h = col_body_h // max_policies
        # Box height leaves a small gap between slots
        box_h = int(slot_h * 0.88)

        for i, tree_id in enumerate(tree_ids):
            tree = DOCTRINE_TREES[tree_id]
            col_x = start_x + i * (col_w + col_gap)
            for j, policy in enumerate(tree["policies"]):
                policy_y = col_top + int(sh * 0.08) + j * slot_h
                is_adopted = policy["id"] in state.adopted_policies
                is_available = can_adopt(state, policy["id"])
                if not is_adopted and is_available:
                    btn_rect = pygame.Rect(col_x + 5,
                                           policy_y + box_h - int(sh * 0.03) - 2,
                                           col_w - 10, int(sh * 0.025))
                    adopt_rects.append((btn_rect, policy["id"], True))

        # Build wisdom action rects
        wisdom_rects = []  # (rect, action_id, can_afford)
        wa_actions = get_available_actions(state)
        if wa_actions:
            wa_count = len(wa_actions)
            wa_btn_w = int(sw * 0.18)
            wa_btn_h = int(sh * 0.055)
            wa_gap = int(sw * 0.015)
            wa_total_w = wa_count * wa_btn_w + (wa_count - 1) * wa_gap
            wa_start_x = sw // 2 - wa_total_w // 2
            wa_y = int(sh * 0.82)
            for idx, (action_id, info, can_afford) in enumerate(wa_actions):
                wa_x = wa_start_x + idx * (wa_btn_w + wa_gap)
                wa_rect = pygame.Rect(wa_x, wa_y, wa_btn_w, wa_btn_h)
                wisdom_rects.append((wa_rect, action_id, can_afford))

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
                for rect, pid, adoptable in adopt_rects:
                    if rect.collidepoint(mx, my) and adoptable:
                        msg = adopt_policy(state, pid)
                        if msg:
                            message = msg
                            message_timer = 150
                for rect, action_id, can_afford in wisdom_rects:
                    if rect.collidepoint(mx, my) and can_afford:
                        msg = use_wisdom_action(state, action_id, galaxy)
                        if msg:
                            message = msg
                            message_timer = 150

        if message_timer > 0:
            message_timer -= 1
            if message_timer <= 0:
                message = None

        # ===== RENDER =====
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(190)
        screen.blit(overlay, (0, 0))

        # Title
        pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title = title_font.render("DOCTRINE TREES", True, title_color)
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.03)))

        # Wisdom display
        wisdom_income = get_wisdom_per_turn(state, galaxy)
        wisdom_str = f"Wisdom: {state.wisdom}"
        if wisdom_income > 0:
            wisdom_str += f"  (+{wisdom_income}/turn)"
        wisdom_surf = tree_font.render(wisdom_str, True, (200, 150, 255))
        screen.blit(wisdom_surf, (sw // 2 - wisdom_surf.get_width() // 2, int(sh * 0.08)))

        # Policies adopted count
        adopted_str = f"Policies Adopted: {len(state.adopted_policies)}"
        adopted_surf = policy_font.render(adopted_str, True, CRT_TEXT_DIM)
        screen.blit(adopted_surf, (sw // 2 - adopted_surf.get_width() // 2, int(sh * 0.12)))

        # Decorative line
        line_y = int(sh * 0.155)
        line_w = int(sw * 0.50)
        pygame.draw.line(screen, tuple(int(c * pulse) for c in CRT_BORDER),
                         (sw // 2 - line_w // 2, line_y),
                         (sw // 2 + line_w // 2, line_y), 2)

        mx, my = pygame.mouse.get_pos()

        # Rebuild adopt rects for rendering (same logic as event phase)
        adopt_rects_render = []
        for i, tree_id in enumerate(tree_ids):
            tree = DOCTRINE_TREES[tree_id]
            col_x = start_x + i * (col_w + col_gap)
            tree_color = tree["color"]
            complete = is_tree_complete(state, tree_id)

            # Column background
            col_bg = pygame.Surface((col_w, int(sh * 0.70)), pygame.SRCALPHA)
            col_bg.fill((10, 15, 12, 180))
            if complete:
                pygame.draw.rect(col_bg, tree_color + (40,), col_bg.get_rect(), 0)
            pygame.draw.rect(col_bg, tree_color, col_bg.get_rect(), 2)
            screen.blit(col_bg, (col_x, col_top))

            # Tree name + icon
            tree_label = f"{tree['icon']} {tree['name']}"
            name_surf = tree_font.render(tree_label, True, tree_color)
            # Truncate if too wide
            if name_surf.get_width() > col_w - 10:
                name_surf = tree_font.render(tree['name'][:15], True, tree_color)
            screen.blit(name_surf, (col_x + col_w // 2 - name_surf.get_width() // 2,
                                     col_top + 5))

            # Policies
            prev_tier = 0
            for j, policy in enumerate(tree["policies"]):
                policy_y = col_top + int(sh * 0.08) + j * slot_h
                is_adopted = policy["id"] in state.adopted_policies
                is_available = can_adopt(state, policy["id"])
                cost = get_policy_cost(policy["id"], state)
                current_tier = policy.get("tier", j + 1)
                # "OR" divider between consecutive sibling tier-3 options
                if current_tier == prev_tier and current_tier == 3:
                    or_surf = small_font.render("─ OR ─", True, CRT_TEXT_DIM)
                    screen.blit(or_surf,
                                (col_x + col_w // 2 - or_surf.get_width() // 2,
                                 policy_y - or_surf.get_height() - 1))
                prev_tier = current_tier

                # Policy box
                box_rect = pygame.Rect(col_x + 4, policy_y, col_w - 8, box_h)

                # Sibling policies become visually muted once the player has
                # locked in one branch at this tier — makes the mutual
                # exclusion obvious at a glance.
                locked_out = False
                if not is_adopted:
                    for conflict_id in policy.get("conflicts_with", []):
                        if conflict_id in state.adopted_policies:
                            locked_out = True
                            break

                if is_adopted:
                    pygame.draw.rect(screen, (20, 50, 25), box_rect)
                    pygame.draw.rect(screen, CRT_GREEN, box_rect, 1)
                    status = "\u2713 "  # checkmark
                    name_color = CRT_GREEN
                elif locked_out:
                    pygame.draw.rect(screen, (25, 15, 15), box_rect)
                    pygame.draw.rect(screen, (80, 40, 40), box_rect, 1)
                    status = "\u2715 "  # x mark
                    name_color = (120, 70, 70)
                elif is_available:
                    pygame.draw.rect(screen, (25, 35, 20), box_rect)
                    pygame.draw.rect(screen, tree_color, box_rect, 1)
                    status = ""
                    name_color = (255, 255, 255)
                else:
                    pygame.draw.rect(screen, (12, 15, 12), box_rect)
                    pygame.draw.rect(screen, (40, 50, 40), box_rect, 1)
                    status = ""
                    name_color = CRT_TEXT_DIM

                # Policy name
                pname = policy_font.render(f"{status}{policy['name']}", True, name_color)
                screen.blit(pname, (col_x + 8, policy_y + 2))

                # Description
                desc_surf = small_font.render(policy["desc"], True,
                                               CRT_TEXT if is_adopted or is_available else CRT_TEXT_DIM)
                screen.blit(desc_surf, (col_x + 8, policy_y + 2 + pname.get_height()))

                # Cost (if not adopted and not locked out)
                if not is_adopted and not locked_out:
                    cost_color = CRT_CYAN if is_available else CRT_TEXT_DIM
                    cost_surf = small_font.render(f"Cost: {cost}W", True, cost_color)
                    screen.blit(cost_surf, (col_x + 8,
                                            policy_y + 2 + pname.get_height() + desc_surf.get_height()))

                # Adopt button
                if not is_adopted and is_available:
                    btn_rect = pygame.Rect(col_x + 5,
                                           policy_y + box_h - int(sh * 0.03) - 2,
                                           col_w - 10, int(sh * 0.025))
                    hovered = btn_rect.collidepoint(mx, my)
                    bg = CRT_BTN_HOVER if hovered else CRT_BTN_BG
                    border = CRT_BTN_BORDER_HOVER if hovered else CRT_BTN_BORDER
                    pygame.draw.rect(screen, bg, btn_rect)
                    pygame.draw.rect(screen, border, btn_rect, 1)
                    btn_label = btn_font.render("ADOPT", True,
                                                (255, 255, 255) if hovered else CRT_TEXT)
                    screen.blit(btn_label, (btn_rect.centerx - btn_label.get_width() // 2,
                                            btn_rect.centery - btn_label.get_height() // 2))
                    adopt_rects_render.append((btn_rect, policy["id"], True))

            # Completion bonus at bottom — positioned below the policy
            # area which now sizes to fit the longest tree.
            bonus_y = col_top + int(sh * 0.08) + col_body_h + 4
            bonus = tree["completion_bonus"]
            if complete:
                b_color = tree_color
                b_prefix = "\u2605 "
            else:
                b_color = CRT_TEXT_DIM
                b_prefix = ""
            b_name = small_font.render(f"{b_prefix}{bonus['name']}", True, b_color)
            screen.blit(b_name, (col_x + col_w // 2 - b_name.get_width() // 2, bonus_y))
            b_desc = small_font.render(bonus["desc"], True, b_color)
            screen.blit(b_desc, (col_x + col_w // 2 - b_desc.get_width() // 2,
                                  bonus_y + b_name.get_height() + 2))

        # Wisdom Powers section (below doctrine trees, above close button)
        if wa_actions:
            wp_label_y = int(sh * 0.775)
            wp_label = tree_font.render("WISDOM POWERS", True,
                                         tuple(int(c * pulse) for c in (200, 150, 255)))
            screen.blit(wp_label, (sw // 2 - wp_label.get_width() // 2, wp_label_y))

            for wa_rect, action_id, can_afford in wisdom_rects:
                info = None
                for aid, ainf, _ in wa_actions:
                    if aid == action_id:
                        info = ainf
                        break
                if not info:
                    continue

                hovered = wa_rect.collidepoint(mx, my)
                if can_afford:
                    bg = CRT_BTN_HOVER if hovered else CRT_BTN_BG
                    border = CRT_BTN_BORDER_HOVER if hovered else CRT_BTN_BORDER
                    text_color = (255, 255, 255) if hovered else CRT_TEXT
                else:
                    bg = (20, 20, 20)
                    border = (50, 50, 50)
                    text_color = CRT_TEXT_DIM

                pygame.draw.rect(screen, bg, wa_rect)
                pygame.draw.rect(screen, border, wa_rect, 1)

                # Icon + name line
                line1 = f"{info['icon']} {info['name']} ({info['cost']}W)"
                line1_surf = btn_font.render(line1, True, text_color)
                screen.blit(line1_surf, (wa_rect.x + wa_rect.w // 2 - line1_surf.get_width() // 2,
                                          wa_rect.y + 3))
                # Description line
                line2_surf = small_font.render(info["desc"], True,
                                                text_color if can_afford else CRT_TEXT_DIM)
                screen.blit(line2_surf, (wa_rect.x + wa_rect.w // 2 - line2_surf.get_width() // 2,
                                          wa_rect.y + 3 + line1_surf.get_height()))

        # Close button
        close_hovered = close_rect.collidepoint(mx, my)
        close_bg = CRT_BTN_HOVER if close_hovered else CRT_BTN_BG
        close_border = CRT_BTN_BORDER_HOVER if close_hovered else CRT_BTN_BORDER
        pygame.draw.rect(screen, close_bg, close_rect)
        pygame.draw.rect(screen, close_border, close_rect, 2)
        close_label = tree_font.render("CLOSE", True,
                                        (255, 255, 255) if close_hovered else CRT_TEXT)
        screen.blit(close_label, (close_rect.centerx - close_label.get_width() // 2,
                                   close_rect.centery - close_label.get_height() // 2))

        # Status message
        if message:
            msg_surf = policy_font.render(message, True, CRT_GREEN)
            screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, int(sh * 0.88)))

        # CRT scanlines
        scanlines = _get_scanline_overlay(sw, sh, alpha=25)
        screen.blit(scanlines, (0, 0))

        display_manager.gpu_flip()
