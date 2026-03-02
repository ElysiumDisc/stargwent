"""
STARGWENT - GALACTIC CONQUEST - Espionage Screen

CRT-styled screen for managing Tok'ra operatives: deploy, recall,
assign missions, rank up, and view status.
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
from .espionage import (get_operative_summary, deploy_operative, recall_operative,
                          assign_mission, rank_up_operative, MISSIONS, RANK_NAMES,
                          RANK_EFFECTIVENESS, RANK_UP_COST,
                          IDLE, MOVING, ESTABLISHING, ACTIVE, DEAD)

# State colors
STATE_COLORS = {
    IDLE: CRT_GREEN,
    MOVING: CRT_CYAN,
    ESTABLISHING: CRT_CYAN,
    ACTIVE: (80, 255, 140),
    DEAD: (255, 80, 80),
}


def _get_valid_missions(op_state, op_target, galaxy, campaign_state):
    """Get missions available for an operative based on target planet type."""
    if op_state != ACTIVE or not op_target:
        return []
    planet = galaxy.planets.get(op_target)
    if not planet:
        return []
    valid = []
    for mid, minfo in MISSIONS.items():
        target_type = minfo["target"]
        if target_type == "enemy" and planet.owner not in ("player", "neutral"):
            valid.append(mid)
        elif target_type == "minor" and planet.planet_type == "neutral":
            valid.append(mid)
        elif target_type == "own" and planet.owner == "player":
            valid.append(mid)
    return valid


def _get_deployable_planets(galaxy, campaign_state):
    """Get list of (planet_id, name, type_hint) for operative deployment."""
    targets = []
    for pid, planet in galaxy.planets.items():
        if planet.owner == "player":
            targets.append((pid, planet.name, "own"))
        elif planet.planet_type == "neutral":
            targets.append((pid, planet.name, "minor"))
        elif planet.owner not in ("player", "neutral"):
            targets.append((pid, planet.name, "enemy"))
    return targets


async def run_espionage_screen(screen, state, galaxy):
    """Run the espionage management screen.

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

    # UI state
    selected_op_idx = 0
    deploy_mode = False  # True when picking a planet for deployment
    mission_mode = False  # True when picking a mission

    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame_count += 1

        # Fresh operative data each frame
        ops = get_operative_summary(state)
        # ops: list of (name, rank_name, state, target_planet, mission, turns_remaining, death_countdown, op_id)

        if selected_op_idx >= len(ops):
            selected_op_idx = max(0, len(ops) - 1)

        # Layout
        panel_w = int(sw * 0.70)
        panel_x = sw // 2 - panel_w // 2
        list_y = int(sh * 0.22)
        row_h = int(sh * 0.08)

        # Build operative row rects
        op_rects = []
        for i in range(len(ops)):
            rect = pygame.Rect(panel_x, list_y + i * row_h, panel_w, row_h - 4)
            op_rects.append(rect)

        # Action button area (right side, below list)
        action_y = list_y + len(ops) * row_h + int(sh * 0.02)
        btn_w = int(sw * 0.13)
        btn_h = int(sh * 0.045)
        btn_gap = int(sw * 0.01)

        # Build action buttons based on selected operative
        action_btns = []  # (rect, label, action_key, enabled)
        if ops and 0 <= selected_op_idx < len(ops):
            sel = ops[selected_op_idx]
            sel_name, sel_rank, sel_state, sel_target, sel_mission, sel_turns, sel_death, sel_id = sel
            bx = panel_x

            if sel_state == IDLE:
                # Deploy button
                r = pygame.Rect(bx, action_y, btn_w, btn_h)
                action_btns.append((r, "DEPLOY", "deploy", True))
                bx += btn_w + btn_gap
                # Rank up button
                can_rank = sel_rank != "Special Agent" and state.naquadah >= RANK_UP_COST
                rank_label = f"RANK UP ({RANK_UP_COST})"
                r = pygame.Rect(bx, action_y, btn_w + 20, btn_h)
                action_btns.append((r, rank_label, "rank_up", can_rank))

            elif sel_state == ACTIVE:
                if not sel_mission:
                    # Mission button
                    r = pygame.Rect(bx, action_y, btn_w, btn_h)
                    action_btns.append((r, "MISSION", "mission", True))
                    bx += btn_w + btn_gap
                # Recall button
                r = pygame.Rect(bx, action_y, btn_w, btn_h)
                action_btns.append((r, "RECALL", "recall", True))

            elif sel_state in (MOVING, ESTABLISHING):
                # Recall button
                r = pygame.Rect(bx, action_y, btn_w, btn_h)
                action_btns.append((r, "RECALL", "recall", True))

        # Deploy target list (when in deploy mode)
        deploy_targets = []
        deploy_rects = []
        if deploy_mode:
            deploy_targets = _get_deployable_planets(galaxy, state)
            dy = action_y + btn_h + int(sh * 0.02)
            for i, (pid, pname, ptype) in enumerate(deploy_targets):
                r = pygame.Rect(panel_x, dy + i * int(sh * 0.035), panel_w, int(sh * 0.032))
                deploy_rects.append((r, pid, pname, ptype))

        # Mission list (when in mission mode)
        mission_rects = []
        if mission_mode and ops and 0 <= selected_op_idx < len(ops):
            sel = ops[selected_op_idx]
            valid_missions = _get_valid_missions(sel[2], sel[3], galaxy, state)
            my = action_y + btn_h + int(sh * 0.02)
            for i, mid in enumerate(valid_missions):
                minfo = MISSIONS[mid]
                r = pygame.Rect(panel_x, my + i * int(sh * 0.04), panel_w, int(sh * 0.037))
                mission_rects.append((r, mid, minfo))

        # Close button
        close_w = int(sw * 0.12)
        close_h = int(sh * 0.05)
        close_rect = pygame.Rect(sw // 2 - close_w // 2, int(sh * 0.92), close_w, close_h)

        # === EVENT HANDLING ===
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if deploy_mode:
                        deploy_mode = False
                    elif mission_mode:
                        mission_mode = False
                    else:
                        return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my_pos = event.pos
                if close_rect.collidepoint(mx, my_pos):
                    return

                # Deploy target selection
                if deploy_mode:
                    for r, pid, pname, ptype in deploy_rects:
                        if r.collidepoint(mx, my_pos):
                            sel = ops[selected_op_idx]
                            msg = deploy_operative(state, sel[7], pid)
                            if msg:
                                message = msg
                                message_timer = 120
                            deploy_mode = False
                            break
                    else:
                        # Click outside — cancel
                        deploy_mode = False
                    continue

                # Mission selection
                if mission_mode:
                    for r, mid, minfo in mission_rects:
                        if r.collidepoint(mx, my_pos):
                            sel = ops[selected_op_idx]
                            msg = assign_mission(state, sel[7], mid)
                            if msg:
                                message = msg
                                message_timer = 120
                            mission_mode = False
                            break
                    else:
                        mission_mode = False
                    continue

                # Operative row selection
                for i, rect in enumerate(op_rects):
                    if rect.collidepoint(mx, my_pos):
                        selected_op_idx = i
                        deploy_mode = False
                        mission_mode = False
                        break

                # Action buttons
                for r, label, action_key, enabled in action_btns:
                    if r.collidepoint(mx, my_pos) and enabled:
                        sel = ops[selected_op_idx]
                        if action_key == "deploy":
                            deploy_mode = True
                            mission_mode = False
                        elif action_key == "mission":
                            mission_mode = True
                            deploy_mode = False
                        elif action_key == "recall":
                            msg = recall_operative(state, sel[7])
                            if msg:
                                message = msg
                                message_timer = 120
                        elif action_key == "rank_up":
                            msg = rank_up_operative(state, sel[7])
                            if msg:
                                message = msg
                                message_timer = 120
                        break

        # Tick message timer
        if message_timer > 0:
            message_timer -= 1
            if message_timer <= 0:
                message = None

        # === RENDER ===
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        screen.blit(overlay, (0, 0))

        # Title
        pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title = title_font.render("TOK'RA OPERATIVES", True, title_color)
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.05)))

        # Decorative line
        line_y = int(sh * 0.05) + title.get_height() + 8
        line_w = int(sw * 0.30)
        pygame.draw.line(screen, tuple(int(c * pulse) for c in CRT_BORDER),
                         (sw // 2 - line_w // 2, line_y),
                         (sw // 2 + line_w // 2, line_y), 2)

        # Naquadah display
        naq_text = info_font.render(f"Naquadah: {state.naquadah}", True, CRT_CYAN)
        screen.blit(naq_text, (sw // 2 - naq_text.get_width() // 2, int(sh * 0.14)))

        # Operative count
        active_count = sum(1 for o in ops if o[2] not in (DEAD,))
        count_text = small_font.render(
            f"Operatives: {len(ops)}  |  Active: {active_count}", True, CRT_TEXT_DIM)
        screen.blit(count_text, (sw // 2 - count_text.get_width() // 2, int(sh * 0.17)))

        # === OPERATIVE LIST ===
        if not ops:
            no_ops = info_font.render("No operatives yet. Earn them at turns 5, 10, 16.",
                                       True, CRT_TEXT_DIM)
            screen.blit(no_ops, (sw // 2 - no_ops.get_width() // 2, list_y + 20))
        else:
            for i, (name, rank_name, op_state, target, mission_id, turns_rem, death_cd, op_id) in enumerate(ops):
                rect = op_rects[i]
                is_selected = (i == selected_op_idx)

                # Background
                if is_selected:
                    pygame.draw.rect(screen, (25, 35, 50), rect)
                    pygame.draw.rect(screen, CRT_AMBER, rect, 2)
                else:
                    pygame.draw.rect(screen, (12, 18, 25), rect)
                    pygame.draw.rect(screen, (40, 50, 60), rect, 1)

                # Name + Rank
                state_color = STATE_COLORS.get(op_state, CRT_TEXT)
                name_surf = section_font.render(f"{name}", True, state_color)
                screen.blit(name_surf, (rect.x + 10, rect.y + 4))

                rank_surf = small_font.render(f"[{rank_name}]", True, CRT_TEXT_DIM)
                screen.blit(rank_surf, (rect.x + 10 + name_surf.get_width() + 8, rect.y + 8))

                # State + info line
                if op_state == DEAD:
                    status = f"KIA — Revival in {death_cd} turn(s)"
                    status_color = (255, 80, 80)
                elif op_state == IDLE:
                    status = "Idle — Ready for deployment"
                    status_color = CRT_GREEN
                elif op_state == MOVING:
                    pname = _planet_name(galaxy, target)
                    status = f"Moving to {pname} ({turns_rem}T)"
                    status_color = CRT_CYAN
                elif op_state == ESTABLISHING:
                    pname = _planet_name(galaxy, target)
                    status = f"Establishing cover at {pname} ({turns_rem}T)"
                    status_color = CRT_CYAN
                elif op_state == ACTIVE:
                    pname = _planet_name(galaxy, target)
                    if mission_id:
                        minfo = MISSIONS.get(mission_id, {})
                        mname = minfo.get("name", mission_id)
                        status = f"Active at {pname} — {mname} ({turns_rem}T)"
                        status_color = (255, 200, 80)
                    else:
                        status = f"Active at {pname} — Awaiting orders"
                        status_color = (80, 255, 140)
                else:
                    status = op_state
                    status_color = CRT_TEXT

                status_surf = small_font.render(status, True, status_color)
                screen.blit(status_surf, (rect.x + 10, rect.y + rect.height - status_surf.get_height() - 4))

                # Effectiveness indicator (right side)
                rank_num = list(RANK_NAMES.values()).index(rank_name) + 1 if rank_name in RANK_NAMES.values() else 1
                eff = RANK_EFFECTIVENESS.get(rank_num, 0.5)
                eff_text = small_font.render(f"Eff: {int(eff*100)}%", True, CRT_TEXT_DIM)
                screen.blit(eff_text, (rect.right - eff_text.get_width() - 10, rect.y + 8))

        # === ACTION BUTTONS ===
        mx, my_pos = pygame.mouse.get_pos()
        for r, label, action_key, enabled in action_btns:
            hovered = r.collidepoint(mx, my_pos)
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
            pygame.draw.rect(screen, bg_color, r)
            pygame.draw.rect(screen, border_color, r, 2)
            lbl = btn_font.render(label, True, text_color)
            screen.blit(lbl, (r.centerx - lbl.get_width() // 2,
                              r.centery - lbl.get_height() // 2))

        # === DEPLOY TARGET LIST ===
        if deploy_mode and deploy_rects:
            header = info_font.render("Select deployment target:", True, CRT_AMBER)
            screen.blit(header, (panel_x, action_y + btn_h + 4))
            for r, pid, pname, ptype in deploy_rects:
                hovered = r.collidepoint(mx, my_pos)
                type_color = {"own": CRT_GREEN, "minor": (200, 180, 255),
                              "enemy": (255, 100, 100)}.get(ptype, CRT_TEXT)
                bg = CRT_BTN_HOVER if hovered else (15, 20, 28)
                pygame.draw.rect(screen, bg, r)
                pygame.draw.rect(screen, (50, 60, 70), r, 1)
                txt = small_font.render(f"{pname} ({ptype})", True,
                                         (255, 255, 255) if hovered else type_color)
                screen.blit(txt, (r.x + 8, r.y + 3))

        # === MISSION LIST ===
        if mission_mode and mission_rects:
            header = info_font.render("Select mission:", True, CRT_AMBER)
            screen.blit(header, (panel_x, action_y + btn_h + 4))
            for r, mid, minfo in mission_rects:
                hovered = r.collidepoint(mx, my_pos)
                bg = CRT_BTN_HOVER if hovered else (15, 20, 28)
                pygame.draw.rect(screen, bg, r)
                pygame.draw.rect(screen, (50, 60, 70), r, 1)
                risk_pct = int(minfo["death_risk"] * 100)
                risk_color = (255, 80, 80) if risk_pct >= 30 else (255, 200, 80) if risk_pct >= 15 else CRT_GREEN
                line1 = f"{minfo['name']} ({minfo['turns']}T)"
                line2 = f"{minfo['desc']} | Risk: {risk_pct}%"
                l1 = small_font.render(line1, True, (255, 255, 255) if hovered else CRT_TEXT)
                l2 = small_font.render(line2, True, risk_color if not hovered else (255, 220, 180))
                screen.blit(l1, (r.x + 8, r.y + 2))
                screen.blit(l2, (r.x + 8, r.y + 2 + l1.get_height()))

        # Close button
        close_hovered = close_rect.collidepoint(mx, my_pos)
        close_bg = CRT_BTN_HOVER if close_hovered else CRT_BTN_BG
        close_border = CRT_BTN_BORDER_HOVER if close_hovered else CRT_BTN_BORDER
        pygame.draw.rect(screen, close_bg, close_rect)
        pygame.draw.rect(screen, close_border, close_rect, 2)
        close_label = section_font.render("CLOSE", True,
                                           (255, 255, 255) if close_hovered else CRT_TEXT)
        screen.blit(close_label, (close_rect.centerx - close_label.get_width() // 2,
                                   close_rect.centery - close_label.get_height() // 2))

        # Status message
        if message:
            msg_surf = info_font.render(message, True, CRT_GREEN)
            screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, int(sh * 0.88)))

        # CRT scanlines
        scanlines = _get_scanline_overlay(sw, sh, alpha=25)
        screen.blit(scanlines, (0, 0))

        display_manager.gpu_flip()


def _planet_name(galaxy, planet_id):
    """Get planet name from ID."""
    if not planet_id:
        return "?"
    planet = galaxy.planets.get(planet_id)
    return planet.name if planet else planet_id
