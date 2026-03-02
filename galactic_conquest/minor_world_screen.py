"""
STARGWENT - GALACTIC CONQUEST - Minor World Screen

CRT-styled panel for interacting with a minor world:
influence bar, quests, action buttons, AI competition display.
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
from .minor_worlds import (
    ensure_minor_world, MinorWorldState, MINOR_WORLD_TYPE_INFO,
    get_influence_tier, get_tier_label, get_tribute_cost,
    pay_tribute, bully_world, attempt_ally, request_quest,
    complete_quest_tribute, ALLY_THRESHOLD, FRIEND_THRESHOLD,
    INFLUENCE_MAX,
)


async def run_minor_world_screen(screen, state, galaxy, planet_id):
    """Run the minor world interaction screen.

    Returns: None (always returns to map)
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()
    frame_count = 0
    rng = random.Random(state.seed + state.turn_number + hash(planet_id))

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

    planet = galaxy.planets.get(planet_id)
    planet_name = planet.name if planet else planet_id

    message = None
    message_timer = 0

    while True:
        clock.tick(60)
        await asyncio.sleep(0)
        frame_count += 1

        mw = ensure_minor_world(state, planet_id, galaxy)
        if not mw:
            return

        type_info = MINOR_WORLD_TYPE_INFO.get(mw.world_type, {})
        type_color = type_info.get("color", CRT_TEXT)
        tier = get_influence_tier(mw.influence)
        tier_label = get_tier_label(mw.influence)
        is_ally = mw.ally_faction == "player"

        # Layout
        panel_w = int(sw * 0.55)
        panel_x = sw // 2 - panel_w // 2
        base_y = int(sh * 0.18)

        # Button rects
        btn_w = int(sw * 0.14)
        btn_h = int(sh * 0.045)
        btn_gap = int(sw * 0.02)
        buttons_y = int(sh * 0.62)

        tribute_cost = get_tribute_cost(state)
        can_tribute = state.naquadah >= tribute_cost
        can_quest = not mw.active_quest and mw.quest_cooldown <= 0
        can_ally_btn = mw.influence >= ALLY_THRESHOLD and mw.ally_faction is None
        has_tribute_quest = (mw.active_quest and mw.active_quest.get("quest_type") == "tribute"
                             and state.naquadah >= mw.active_quest.get("amount", 40))

        tribute_rect = pygame.Rect(panel_x + 20, buttons_y, btn_w, btn_h)
        quest_rect = pygame.Rect(panel_x + 20 + btn_w + btn_gap, buttons_y, btn_w, btn_h)
        ally_rect = pygame.Rect(panel_x + 20 + 2 * (btn_w + btn_gap), buttons_y, btn_w, btn_h)
        bully_rect = pygame.Rect(panel_x + panel_w - btn_w - 20, buttons_y, btn_w, btn_h)

        # Pay tribute quest button (shown when tribute quest is active)
        pay_quest_rect = pygame.Rect(panel_x + 20, buttons_y + btn_h + 8, btn_w * 2 + btn_gap, btn_h)

        # Close button
        close_w = int(sw * 0.12)
        close_h = int(sh * 0.05)
        close_rect = pygame.Rect(sw // 2 - close_w // 2, int(sh * 0.88), close_w, close_h)

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
                if tribute_rect.collidepoint(mx, my) and can_tribute:
                    msg = pay_tribute(state, planet_id, galaxy)
                    if msg:
                        message = msg
                        message_timer = 120
                elif quest_rect.collidepoint(mx, my) and can_quest:
                    msg = request_quest(state, planet_id, galaxy, rng)
                    if msg:
                        message = msg
                        message_timer = 120
                elif ally_rect.collidepoint(mx, my) and can_ally_btn:
                    msg = attempt_ally(state, planet_id, galaxy)
                    if msg:
                        message = msg
                        message_timer = 120
                elif bully_rect.collidepoint(mx, my):
                    msg = bully_world(state, planet_id, galaxy)
                    if msg:
                        message = msg
                        message_timer = 120
                elif pay_quest_rect.collidepoint(mx, my) and has_tribute_quest:
                    msg = complete_quest_tribute(state, planet_id, galaxy)
                    if msg:
                        message = msg
                        message_timer = 120

        # Tick message timer
        if message_timer > 0:
            message_timer -= 1
            if message_timer <= 0:
                message = None

        # Re-read after possible changes
        mw = ensure_minor_world(state, planet_id, galaxy)
        if not mw:
            return
        tier = get_influence_tier(mw.influence)
        tier_label = get_tier_label(mw.influence)
        is_ally = mw.ally_faction == "player"

        # ===== RENDER =====
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((sw, sh))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        screen.blit(overlay, (0, 0))

        # Title
        pulse = 0.85 + 0.15 * math.sin(frame_count * 0.03)
        title_text = f"{type_info.get('icon', '')} {planet_name} — {mw.world_type.title()} World"
        title_color = tuple(int(c * pulse) for c in type_color)
        title = title_font.render(title_text, True, title_color)
        screen.blit(title, (sw // 2 - title.get_width() // 2, int(sh * 0.06)))

        # Decorative line
        line_y = int(sh * 0.06) + title.get_height() + 8
        line_w = int(sw * 0.30)
        pygame.draw.line(screen, tuple(int(c * pulse) for c in CRT_BORDER),
                         (sw // 2 - line_w // 2, line_y),
                         (sw // 2 + line_w // 2, line_y), 2)

        # --- Influence Bar ---
        bar_y = base_y
        bar_label = section_font.render("Influence", True, CRT_TEXT)
        screen.blit(bar_label, (panel_x + 20, bar_y))

        # Tier label
        tier_colors = {"neutral": CRT_TEXT_DIM, "friend": CRT_CYAN, "ally": CRT_GREEN}
        tier_surf = section_font.render(f"[{tier_label}]", True, tier_colors.get(tier, CRT_TEXT))
        screen.blit(tier_surf, (panel_x + 20 + bar_label.get_width() + 15, bar_y))

        # Bar
        bar_x = panel_x + 20
        bar_top = bar_y + bar_label.get_height() + 5
        bar_w = panel_w - 40
        bar_h = max(16, sh // 50)
        pygame.draw.rect(screen, (20, 30, 20), (bar_x, bar_top, bar_w, bar_h))
        fill_w = max(0, int(bar_w * mw.influence / INFLUENCE_MAX))
        # Color gradient based on influence
        if mw.influence >= ALLY_THRESHOLD:
            fill_color = CRT_GREEN
        elif mw.influence >= FRIEND_THRESHOLD:
            fill_color = CRT_CYAN
        else:
            fill_color = CRT_TEXT_DIM
        pygame.draw.rect(screen, fill_color, (bar_x, bar_top, fill_w, bar_h))
        pygame.draw.rect(screen, CRT_BORDER, (bar_x, bar_top, bar_w, bar_h), 1)
        # Threshold markers
        for threshold, label in [(FRIEND_THRESHOLD, "Friend"), (ALLY_THRESHOLD, "Ally")]:
            tx = bar_x + int(bar_w * threshold / INFLUENCE_MAX)
            pygame.draw.line(screen, (200, 200, 200), (tx, bar_top), (tx, bar_top + bar_h), 1)
            t_surf = small_font.render(label, True, (160, 160, 160))
            screen.blit(t_surf, (tx - t_surf.get_width() // 2, bar_top + bar_h + 2))
        # Value
        val_surf = info_font.render(f"{mw.influence}/{INFLUENCE_MAX}", True, (255, 255, 255))
        screen.blit(val_surf, (bar_x + bar_w + 8, bar_top))

        # --- Ally Status ---
        ally_y = bar_top + bar_h + 25
        if mw.ally_faction:
            ally_label = f"Allied with: {mw.ally_faction}"
            ally_color = CRT_GREEN if mw.ally_faction == "player" else (255, 100, 80)
        else:
            ally_label = "No ally (requires 60+ influence)"
            ally_color = CRT_TEXT_DIM
        ally_surf = info_font.render(ally_label, True, ally_color)
        screen.blit(ally_surf, (panel_x + 20, ally_y))

        # --- Active Bonuses ---
        bonus_y = ally_y + 30
        bonus_header = section_font.render("Active Bonuses", True, CRT_AMBER)
        screen.blit(bonus_header, (panel_x + 20, bonus_y))
        bonus_y += bonus_header.get_height() + 5

        bonuses_shown = False
        if tier == "friend" or tier == "ally":
            friend_desc = type_info.get("friend_desc", "")
            if friend_desc:
                b_surf = info_font.render(f"Friend: {friend_desc}", True, CRT_CYAN)
                screen.blit(b_surf, (panel_x + 30, bonus_y))
                bonus_y += b_surf.get_height() + 3
                bonuses_shown = True
        if is_ally and tier == "ally":
            ally_desc = type_info.get("ally_desc", "")
            if ally_desc:
                b_surf = info_font.render(f"Ally: {ally_desc}", True, CRT_GREEN)
                screen.blit(b_surf, (panel_x + 30, bonus_y))
                bonus_y += b_surf.get_height() + 3
                bonuses_shown = True
        if not bonuses_shown:
            no_bonus = info_font.render("None (reach Friend tier for bonuses)", True, CRT_TEXT_DIM)
            screen.blit(no_bonus, (panel_x + 30, bonus_y))
            bonus_y += no_bonus.get_height() + 3

        # --- Active Quest ---
        quest_y = bonus_y + 15
        quest_header = section_font.render("Quest", True, CRT_AMBER)
        screen.blit(quest_header, (panel_x + 20, quest_y))
        quest_y += quest_header.get_height() + 5

        if mw.active_quest:
            q_desc = mw.active_quest.get("description", "?")
            q_reward = mw.active_quest.get("reward_influence", 0)
            q_surf = info_font.render(f"{q_desc} (+{q_reward} influence)", True, CRT_CYAN)
            screen.blit(q_surf, (panel_x + 30, quest_y))
        elif mw.quest_cooldown > 0:
            cd_surf = info_font.render(f"Quest available in {mw.quest_cooldown} turn(s)", True, CRT_TEXT_DIM)
            screen.blit(cd_surf, (panel_x + 30, quest_y))
        else:
            no_quest = info_font.render("No active quest — request one below", True, CRT_TEXT_DIM)
            screen.blit(no_quest, (panel_x + 30, quest_y))

        # --- AI Competition ---
        ai_y = quest_y + 30
        ai_header = section_font.render("AI Competition", True, (255, 150, 100))
        screen.blit(ai_header, (panel_x + 20, ai_y))
        ai_y += ai_header.get_height() + 5

        has_ai = False
        for faction, inf in sorted(mw.ai_influence.items(), key=lambda x: -x[1]):
            if inf > 0:
                f_color = FACTION_DISPLAY_COLORS.get(faction, CRT_TEXT)
                ai_surf = info_font.render(f"{faction}: {inf}", True, f_color)
                screen.blit(ai_surf, (panel_x + 30, ai_y))
                ai_y += ai_surf.get_height() + 2
                has_ai = True
        if not has_ai:
            no_ai = info_font.render("No AI influence yet", True, CRT_TEXT_DIM)
            screen.blit(no_ai, (panel_x + 30, ai_y))

        # --- Action Buttons ---
        mx, my = pygame.mouse.get_pos()

        # Tribute
        _draw_action_btn(screen, tribute_rect, f"TRIBUTE ({tribute_cost})",
                         btn_font, can_tribute, mx, my)
        # Request Quest
        _draw_action_btn(screen, quest_rect, "REQUEST QUEST",
                         btn_font, can_quest, mx, my)
        # Attempt Ally
        _draw_action_btn(screen, ally_rect, "ATTEMPT ALLY",
                         btn_font, can_ally_btn, mx, my)
        # Bully
        _draw_action_btn(screen, bully_rect, "BULLY",
                         btn_font, True, mx, my, color_base=(80, 40, 30))

        # Pay tribute quest button
        if has_tribute_quest:
            amount = mw.active_quest.get("amount", 40)
            _draw_action_btn(screen, pay_quest_rect, f"PAY QUEST ({amount} naq)",
                             btn_font, True, mx, my, color_base=(40, 60, 30))

        # Close button
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
            screen.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, int(sh * 0.83)))

        # CRT scanlines
        scanlines = _get_scanline_overlay(sw, sh, alpha=25)
        screen.blit(scanlines, (0, 0))

        display_manager.gpu_flip()


def _draw_action_btn(screen, rect, text, font, enabled, mx, my, color_base=None):
    """Draw a CRT-styled action button."""
    hovered = rect.collidepoint(mx, my)
    if not enabled:
        bg_color = (10, 12, 10)
        border_color = (30, 40, 30)
        text_color = CRT_TEXT_DIM
    elif hovered:
        bg_color = CRT_BTN_HOVER if not color_base else tuple(min(255, c + 20) for c in color_base)
        border_color = CRT_BTN_BORDER_HOVER
        text_color = (255, 255, 255)
    else:
        bg_color = CRT_BTN_BG if not color_base else color_base
        border_color = CRT_BTN_BORDER
        text_color = CRT_TEXT
    pygame.draw.rect(screen, bg_color, rect)
    pygame.draw.rect(screen, border_color, rect, 2)
    label = font.render(text, True, text_color)
    screen.blit(label, (rect.centerx - label.get_width() // 2,
                        rect.centery - label.get_height() // 2))
