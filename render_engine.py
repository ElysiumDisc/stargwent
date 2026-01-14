import pygame
import math
import game_config as cfg
import display_manager
from pygame.math import Vector2
from cards import get_card_back, ALL_CARDS, FACTION_TAURI

# Performance caches to avoid recreating objects every frame
_font_cache = {}
_scaled_image_cache = {}
_MAX_SCALED_CACHE_SIZE = 150  # Limit cache size to prevent memory issues


def _get_cached_font(size, bold=False):
    """Get or create a cached font to avoid expensive font creation each frame."""
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("Arial", size, bold=bold)
    return _font_cache[key]


def _get_cached_scaled_image(base_img, target_size, card_id=None):
    """Get or create a cached scaled image to avoid expensive scaling each frame."""
    img_id = id(base_img) if card_id is None else card_id
    key = (img_id, target_size[0], target_size[1])

    if key not in _scaled_image_cache:
        if len(_scaled_image_cache) >= _MAX_SCALED_CACHE_SIZE:
            # Clear half the cache when full
            keys_to_remove = list(_scaled_image_cache.keys())[:_MAX_SCALED_CACHE_SIZE // 2]
            for k in keys_to_remove:
                del _scaled_image_cache[k]
        _scaled_image_cache[key] = pygame.transform.scale(base_img, target_size)
    return _scaled_image_cache[key]


def clear_render_caches():
    """Clear render caches - call on resolution change."""
    global _font_cache, _scaled_image_cache
    _font_cache.clear()
    _scaled_image_cache.clear()

def _draw_card_details(target_surface, card, rect):
    """Render card overlays (power pips and row icon)."""
    if card.row not in ["special", "weather"]:
        if card.displayed_power > card.power:
            text_color = (100, 255, 100)
        elif card.displayed_power < card.power:
            text_color = (255, 100, 100)
        else:
            text_color = cfg.WHITE

        # Scale font based on card size (smaller for board cards) - use cached font
        font_size = max(10, int(rect.height * 0.12))
        power_font = _get_cached_font(font_size, bold=True)
        power_text = power_font.render(str(card.displayed_power), True, text_color)
        power_rect = power_text.get_rect(
            center=(rect.x + rect.width // 2, rect.y + rect.height - int(rect.height * 0.12))
        )
        pygame.draw.rect(
            target_surface,
            (0, 0, 0, 180),
            power_rect.inflate(3, 2),
            border_radius=3
        )
        target_surface.blit(power_text, power_rect)

def draw_card(surface, card, x, y, selected=False, hover_scale=1.0, tilt_angle=0.0,
              alpha=255, render_details=True, update_rect=True,
              target_width=None, target_height=None):
    """Blits card surfaces, optionally scaling to target size."""

    # Target dimensions (default to board card size)
    w = target_width if target_width else cfg.CARD_WIDTH
    h = target_height if target_height else cfg.CARD_HEIGHT

    # Get base image
    if hover_scale > 1.05 and hasattr(card, 'hover_image'):
        base_img = card.hover_image
        # Apply hover scale to target dimensions
        w = int(w * hover_scale)
        h = int(h * hover_scale)
    else:
        base_img = card.image

    # Scale image to target size if needed - use cached scaling for performance
    img_size = base_img.get_size()
    if img_size[0] != w or img_size[1] != h:
        img = _get_cached_scaled_image(base_img, (w, h), getattr(card, 'id', None))
    else:
        img = base_img

    # Center hover offset
    if hover_scale > 1.05:
        base_w = target_width if target_width else cfg.CARD_WIDTH
        base_h = target_height if target_height else cfg.CARD_HEIGHT
        draw_x = x - (w - base_w) // 2
        draw_y = y - (h - base_h) // 2
    else:
        draw_x, draw_y = x, y

    draw_rect = pygame.Rect(draw_x, draw_y, w, h)
    if update_rect:
        card.rect = draw_rect.copy()

    # Fast path: No rotation or transparency
    if abs(tilt_angle) < 0.01 and alpha == 255:
        surface.blit(img, draw_rect)
        if render_details:
            _draw_card_details(surface, card, draw_rect)
    else:
        # Slow path: Only used for specific animations
        # Ensure we use high-quality base image
        temp_surface = img.copy()
        if render_details:
            detail_rect = pygame.Rect(0, 0, w, h)
            _draw_card_details(temp_surface, card, detail_rect)
        
        # rotozoom is okay for a few cards, but avoid bulk usage
        rotated_surface = pygame.transform.rotozoom(temp_surface, tilt_angle, 1.0)
        if alpha != 255:
            rotated_surface.set_alpha(alpha)
        
        final_rect = rotated_surface.get_rect(center=draw_rect.center)
        surface.blit(rotated_surface, final_rect)

    if selected:
        pygame.draw.rect(surface, (255, 255, 0), draw_rect, width=3, border_radius=5)

def _draw_drag_trail(surface, trail_entries):
    if not trail_entries:
        return

    for blob in trail_entries:
        alpha = int(blob.get("alpha", 0))
        if alpha <= 0:
            continue

        width_scale = blob.get("width_scale", 1.0)
        height_scale = blob.get("height_scale", 1.0)
        width = max(4, int(cfg.CARD_WIDTH * width_scale))
        height = max(4, int(cfg.CARD_HEIGHT * height_scale))
        tint = blob.get("color", (180, 200, 255))
        trail_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        pygame.draw.rect(
            trail_surface,
            (tint[0], tint[1], tint[2], alpha),
            trail_surface.get_rect(),
            border_radius=18
        )
        pygame.draw.rect(
            trail_surface,
            (255, 255, 255, min(alpha, 140)),
            trail_surface.get_rect().inflate(-12, -12),
            border_radius=14
        )

        pos = blob.get("pos", (0, 0))
        surface.blit(
            trail_surface,
            (int(pos[0] - width // 2), int(pos[1] - height // 2))
        )

def _compute_hand_positions(card_count, card_width, card_gap):
    if card_count <= 0:
        return [], False

    card_full = card_width + card_gap
    total_width = card_count * card_width + (card_count - 1) * card_gap
    region_left = cfg.HAND_REGION_LEFT
    region_width = cfg.HAND_REGION_WIDTH

    if total_width <= region_width:
        start_x = region_left + (region_width - total_width) // 2
        spacing = card_full
        accordion = False
    else:
        overlap = (total_width - region_width) / max(1, card_count - 1)
        spacing = card_full - overlap
        min_spacing = max(8, int(card_width * 0.35))
        if spacing < min_spacing:
            spacing = min_spacing
        render_width = (card_count - 1) * spacing + card_width
        start_x = region_left if render_width >= region_width else region_left + (region_width - render_width) // 2
        accordion = True

    positions = [start_x + i * spacing for i in range(card_count)]
    return positions, accordion

def draw_hand(surface, player, selected_card, mulligan_selected=None, dragging_card=None,
              hovered_card=None, hover_scale=1.0, drag_visuals=None):
    hand_area_height = cfg.COMMAND_BAR_Y - cfg.player_hand_area_y
    if hand_area_height > 0:
        hand_bg_surface = pygame.Surface((display_manager.SCREEN_WIDTH, hand_area_height), pygame.SRCALPHA)
        hand_bg_surface.fill(cfg.PLAYER_HAND_BG)
        surface.blit(hand_bg_surface, (0, cfg.player_hand_area_y))

    if drag_visuals and drag_visuals.get("trail"):
        _draw_drag_trail(surface, drag_visuals.get("trail"))

    is_mulligan_mode = mulligan_selected is not None
    # Use larger hand card dimensions for better visibility
    card_w = cfg.MULLIGAN_CARD_WIDTH if is_mulligan_mode else cfg.HAND_CARD_WIDTH
    card_h = cfg.MULLIGAN_CARD_HEIGHT if is_mulligan_mode else cfg.HAND_CARD_HEIGHT
    total_cards = len(player.hand)
    card_spacing = int(card_w * 0.125)

    if is_mulligan_mode:
        total_width = total_cards * card_w + (total_cards - 1) * card_spacing
        start_x = (display_manager.SCREEN_WIDTH - total_width) // 2 if total_width < display_manager.SCREEN_WIDTH else cfg.HAND_REGION_LEFT
        card_positions = [start_x + i * (card_w + card_spacing) for i in range(total_cards)]
        accordion_active = False
    else:
        card_positions, accordion_active = _compute_hand_positions(total_cards, card_w, card_spacing)

    if is_mulligan_mode:
        card_y = display_manager.SCREEN_HEIGHT // 2 - card_h // 2
    else:
        card_y = cfg.COMMAND_BAR_Y + (cfg.COMMAND_BAR_HEIGHT - card_h) // 2
    
    idle_time = pygame.time.get_ticks() / 1000.0
    
    for i, card in enumerate(player.hand):
        if card == dragging_card:
            continue
        if i >= len(card_positions):
            continue
        card_x = card_positions[i]
        is_selected = (card == selected_card)
        is_mulligan_selected = (mulligan_selected and card in mulligan_selected)
        is_hovered = (card == hovered_card)
        
        if is_mulligan_mode:
            card_scale = cfg.MULLIGAN_CARD_SCALE * (hover_scale if is_hovered else 1.0)
        else:
            base_scale = 0.95 if accordion_active else 1.0
            card_scale = base_scale * (hover_scale if is_hovered else 1.0)
        edge_alpha = 205 if (accordion_active and (i == 0 or i == len(player.hand) - 1)) else 255

        # Idle animation disabled for 1440p performance (was causing flickering)
        idle_float = 0
        idle_tilt = 0

        draw_y = card_y - (int(35 * display_manager.SCALE_FACTOR) if (is_hovered and not is_mulligan_mode) else 0) + idle_float
        draw_card(surface, card, card_x, draw_y, selected=is_selected, hover_scale=card_scale, alpha=edge_alpha, tilt_angle=idle_tilt,
                  target_width=card_w, target_height=card_h)
        
        if is_mulligan_selected:
            pygame.draw.rect(surface, (100, 100, 255), card.rect, width=4, border_radius=5)

        # Row-type color highlighting for hovered/selected cards
        if is_hovered or is_selected:
            row_colors = {
                "close": (220, 60, 60),      # Red
                "ranged": (80, 140, 220),    # Blue
                "siege": (60, 200, 60),      # Green
                "agile": (220, 200, 60),     # Yellow (can go close or ranged)
                "weather": (100, 180, 255),  # Light blue (Stargate theme)
                "special": (255, 200, 80),   # Gold/yellow (Command/Horn)
            }
            border_color = row_colors.get(card.row, (150, 150, 150))
            border_width = 4 if is_selected else 3
            pygame.draw.rect(surface, border_color, card.rect.inflate(4, 4), width=border_width, border_radius=8)

        if is_selected and card.row in ["special", "weather"]:
            hint_font = _get_cached_font(16, bold=True)
            hint_text = hint_font.render("DRAG TO PLAY", True, (255, 255, 0))
            hint_rect = hint_text.get_rect(center=(card.rect.centerx, card.rect.top - 15))
            bg_rect = hint_rect.inflate(10, 4)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect)
            surface.blit(hint_text, hint_rect)
    
    if dragging_card and dragging_card in player.hand:
        velocity = drag_visuals.get("velocity", Vector2()) if drag_visuals else Vector2()
        pickup_boost = drag_visuals.get("pickup_boost", 0.0) if drag_visuals else 0.0
        pulse = drag_visuals.get("pulse", 0.0) if drag_visuals else 0.0
        speed = velocity.length()
        lift = min(18, 6 + speed * 0.35 + pickup_boost * 18)
        wobble = math.sin(pulse * 1.2) * 2
        tilt = max(-12, min(12, -velocity.x * 1.2))
        tilt += math.sin(pulse * 1.5) * 1.5
        dynamic_scale = 1.05 + min(0.05, speed * 0.015) + pickup_boost * 0.08

        glow_size = (int(cfg.CARD_WIDTH * 1.2), int(cfg.CARD_HEIGHT * 0.8))
        shadow_surface = pygame.Surface((glow_size[0], int(glow_size[1])), pygame.SRCALPHA)
        shadow_alpha = min(210, 80 + speed * 10)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, shadow_alpha), shadow_surface.get_rect())
        shadow_pos = (
            int(dragging_card.rect.centerx - shadow_surface.get_width() // 2 + velocity.x * 0.8),
            int(dragging_card.rect.centery - shadow_surface.get_height() // 2 + 45 + abs(velocity.y) * 0.2)
        )
        surface.blit(shadow_surface, shadow_pos)

        if pickup_boost > 0.01:
            flash_surface = pygame.Surface((cfg.CARD_WIDTH + 40, cfg.CARD_HEIGHT + 40), pygame.SRCALPHA)
            pygame.draw.rect(
                flash_surface,
                (255, 255, 255, int(180 * pickup_boost)),
                flash_surface.get_rect(),
                border_radius=30
            )
            flash_pos = (
                int(dragging_card.rect.centerx - flash_surface.get_width() // 2),
                int(dragging_card.rect.centery - flash_surface.get_height() // 2)
            )
            surface.blit(flash_surface, flash_pos)

        draw_card(
            surface,
            dragging_card,
            dragging_card.rect.x,
            dragging_card.rect.y - lift + wobble,
            selected=False,
            hover_scale=dynamic_scale,
            tilt_angle=tilt,
            render_details=True,
            update_rect=False,
            target_width=card_w,
            target_height=card_h
        )

def draw_opponent_hand(surface, opponent):
    hand_area_height = cfg.OPPONENT_HAND_HEIGHT
    hand_y = cfg.opponent_hand_area_y + (hand_area_height - cfg.CARD_HEIGHT) // 2
    total_cards = len(opponent.hand)
    
    if total_cards == 0:
        return
    
    card_spacing = int(cfg.CARD_WIDTH * 0.125)
    card_positions, accordion_active = _compute_hand_positions(total_cards, cfg.CARD_WIDTH, card_spacing)
    
    card_back_image = get_card_back(cfg.CARD_WIDTH, cfg.CARD_HEIGHT)
    idle_time = pygame.time.get_ticks() / 1000.0
    
    for i, card in enumerate(opponent.hand):
        if i >= len(card_positions):
            continue
        card_x = card_positions[i]
        alpha = 205 if accordion_active and (i == 0 or i == total_cards - 1) else 255

        # Idle animation disabled for 1440p performance
        idle_float = 0
        idle_tilt = 0

        draw_y = hand_y + idle_float

        if opponent.hand_revealed:
            draw_card(surface, card, card_x, draw_y, render_details=True, update_rect=False, alpha=alpha, tilt_angle=idle_tilt)
            pygame.draw.rect(surface, (255, 215, 0), (card_x, int(draw_y), cfg.CARD_WIDTH, cfg.CARD_HEIGHT), 2, border_radius=8)
        else:
            # No rotation needed since idle_tilt is 0
            temp_surface = card_back_image.copy()
            if alpha < 255:
                temp_surface.set_alpha(alpha)
            surface.blit(temp_surface, (card_x, int(draw_y)))
            pygame.draw.rect(surface, (100, 150, 200), (card_x, int(draw_y), cfg.CARD_WIDTH, cfg.CARD_HEIGHT), 2, border_radius=8)
    
    if opponent.hand_revealed and opponent.hand_reveal_timer > 0:
        timer_text = f"HAND REVEALED: {int(opponent.hand_reveal_timer)}s"
        timer_surf = cfg.UI_FONT.render(timer_text, True, (255, 215, 0))
        # Position between player and opponent close rows
        # Opponent close row ends around 0.43, player close row starts around 0.51
        # Middle between them is around 0.47 of screen height
        y_position = int(display_manager.SCREEN_HEIGHT * 0.47)
        timer_rect = timer_surf.get_rect(center=(display_manager.SCREEN_WIDTH // 2, y_position))
        bg_rect = timer_rect.inflate(20, 10)
        pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect, border_radius=5)
        surface.blit(timer_surf, timer_rect)

def draw_weather_slots(surface, game, dragging_card=None):
    """Draw weather slots with highlighting when dragging weather cards."""
    for row_name, slot_rect in cfg.WEATHER_SLOT_RECTS.items():
        is_active = game.weather_active.get(row_name)

        # Check if we're dragging a weather card that affects this row
        is_drag_target = False
        if dragging_card and dragging_card.row == "weather":
            ability = dragging_card.ability or ""
            # Check if this weather affects this row
            ability_lower = ability.lower()
            row_lower = row_name.lower()

            # More comprehensive check for weather effects
            if ("all" in ability_lower or
                row_lower in ability_lower or
                ("close" in row_lower and "close" in ability_lower) or
                ("ranged" in row_lower and "ranged" in ability_lower) or
                ("siege" in row_lower and "siege" in ability_lower) or
                ("any" in ability_lower) or
                ("target" in ability_lower)):
                is_drag_target = True

        slot_surface = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)
        if is_drag_target:
            # Highlight when dragging weather card
            fill_alpha = 240
            slot_surface.fill((60, 100, 180, fill_alpha))
            border_color = (150, 220, 255)
            border_width = 4
        elif is_active:
            fill_alpha = 210
            slot_surface.fill((25, 45, 70, fill_alpha))
            border_color = (120, 190, 255)
            border_width = 3
        else:
            fill_alpha = 150
            slot_surface.fill((25, 45, 70, fill_alpha))
            border_color = (80, 120, 170)
            border_width = 2

        pygame.draw.rect(slot_surface, border_color, slot_surface.get_rect(), width=border_width, border_radius=12)
        surface.blit(slot_surface, slot_rect.topleft)

        # Draw the weather card if present
        entry = game.weather_cards_on_board.get(row_name) if hasattr(game, "weather_cards_on_board") else None
        card = entry.get("card") if entry else None
        if card:
            # Center card in slot
            card_x = slot_rect.x + (slot_rect.width - cfg.CARD_WIDTH) // 2
            card_y = slot_rect.y + (slot_rect.height - cfg.CARD_HEIGHT) // 2
            draw_card(surface, card, card_x, card_y, render_details=False, update_rect=False)

def draw_horn_slots(surface, game, dragging_card=None):
    def render_slot(slot_rect, active, card, faction_color, is_drag_target=False):
        slot_surface = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)

        # Determine fill color based on drag state
        if is_drag_target:
            fill_alpha = 240
            slot_surface.fill((60, 100, 180, fill_alpha))  # Highlight color when dragging horn card
        else:
            fill_alpha = 120
            slot_surface.fill((30, 30, 40, fill_alpha))

        pygame.draw.rect(slot_surface, (15, 15, 20, 200), slot_surface.get_rect().inflate(-6, -6), border_radius=10)
        surface.blit(slot_surface, slot_rect.topleft)

        pulse = (math.sin(pygame.time.get_ticks() / 250.0) + 1) * 0.5
        outline_color = faction_color if active else tuple(int(c * 0.7) for c in faction_color)
        outline_alpha = 220 if active else int(130 + 80 * pulse)

        # Enhance outline if this is a drag target
        if is_drag_target:
            outline_alpha = 255
            outline_color = (150, 220, 255)  # Bright blue for drag target

        outline_surface = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(outline_surface, (*outline_color, outline_alpha), outline_surface.get_rect(), width=3, border_radius=14)
        surface.blit(outline_surface, slot_rect.topleft)

        if card:
            draw_card(surface, card, slot_rect.x + (slot_rect.width - cfg.CARD_WIDTH) // 2,
                      slot_rect.centery - cfg.CARD_HEIGHT // 2, render_details=False, update_rect=False)
        # No "H" text - slot is visually clear without it

    player_color = cfg.FACTION_GLOW_COLORS.get(game.player1.faction, (255, 215, 0))
    opponent_color = cfg.FACTION_GLOW_COLORS.get(game.player2.faction, (255, 215, 0))

    # Check if we're dragging a Command Network card
    is_horn_card_drag = dragging_card and dragging_card.row == "special" and "Command Network" in (dragging_card.ability or "")

    if hasattr(game.player1, "horn_slots"):
        for row_name, slot_rect in cfg.PLAYER_HORN_SLOT_RECTS.items():
            # Check if this is a valid target for the dragged horn card
            is_drag_target = is_horn_card_drag and game.player1.horn_slots.get(row_name) is None
            render_slot(slot_rect, game.player1.horn_effects.get(row_name, False),
                        game.player1.horn_slots.get(row_name), player_color, is_drag_target)
    if hasattr(game.player2, "horn_slots"):
        for row_name, slot_rect in cfg.OPPONENT_HORN_SLOT_RECTS.items():
            # Check if this is a valid target for the dragged horn card
            is_drag_target = is_horn_card_drag and game.player2.horn_slots.get(row_name) is None
            render_slot(slot_rect, game.player2.horn_effects.get(row_name, False),
                        game.player2.horn_slots.get(row_name), opponent_color, is_drag_target)

def _render_sg1_score_box(tint, row_box, score, surface, is_player):
    # Scale font to fit the box height
    font_size = max(18, int(row_box.height * 0.75))
    score_font = _get_cached_font(font_size, bold=True)
    
    box_surface = pygame.Surface((row_box.width, row_box.height), pygame.SRCALPHA)
    fill_alpha = 215 if is_player else 170
    box_surface.fill((*tint, fill_alpha))
    border_rect = box_surface.get_rect()
    
    # Scale corner radius based on size
    radius = max(4, int(row_box.height * 0.3))
    pygame.draw.rect(box_surface, (255, 255, 255, 45), border_rect, border_radius=radius)
    pygame.draw.rect(box_surface, (20, 30, 45, 180), border_rect.inflate(-4, -4), width=2, border_radius=max(2, radius-2))
    
    notch_color = (180, 220, 255, 160)
    # Scaled notches
    nh = max(2, int(row_box.height * 0.15))
    nw = max(5, int(row_box.width * 0.15))
    
    pygame.draw.line(box_surface, notch_color, (nw, 2), (border_rect.width - nw, 2), 2)
    pygame.draw.line(box_surface, notch_color, (2, border_rect.height - 2), (border_rect.width - 2, border_rect.height - 2), 2)
    
    surface.blit(box_surface, row_box.topleft)
    score_color = cfg.WHITE if score > 0 else (200, 200, 200)
    score_text = score_font.render(str(score), True, score_color)
    score_rect = score_text.get_rect(center=row_box.center)
    surface.blit(score_text, score_rect)

def draw_row_score_boxes(surface, game, anchor_x_right=None):
    # Sidebar anchoring logic
    # Box scores are aligned to SIDEBAR_X + 20
    box_x = cfg.SIDEBAR_X + 15
    box_width = 150 # Narrower score boxes to give more space to chat/history

    row_height = cfg.PLAYER_ROW_RECTS["close"].height
    box_height = max(24, int(row_height * 0.40))

    for player, rects in [(game.player2, cfg.OPPONENT_ROW_RECTS), (game.player1, cfg.PLAYER_ROW_RECTS)]:
        for row_name, row_rect in rects.items():
            score = sum(c.displayed_power for c in player.board.get(row_name, []))
            center_y = row_rect.centery
            row_box = pygame.Rect(box_x, center_y - box_height // 2, box_width, box_height)
            tint = cfg.get_row_color(row_name)
            _render_sg1_score_box(tint, row_box, score, surface, player == game.player1)

def draw_history_panel(surface, game, panel_rect, scroll_offset, hover_pos=None):
    history_font = _get_cached_font(max(14, int(16 * display_manager.SCALE_FACTOR)))
    panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    panel_surface.fill((10, 18, 32, 200))
    pygame.draw.rect(panel_surface, (80, 120, 180, 220), panel_surface.get_rect(), width=2, border_radius=12)
    surface.blit(panel_surface, panel_rect.topleft)

    padding = 10
    entries = game.history
    icon_width = 12
    line_height = history_font.get_linesize()
    entry_base_height = cfg.HISTORY_ENTRY_HEIGHT
    text_block_width = max(40, panel_rect.width - 2 * padding - icon_width - 18)

    def wrap_text(text):
        words = text.split()
        if not words:
            return [""]
        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if history_font.size(candidate)[0] <= text_block_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    formatted_entries = []
    content_height = 0
    for entry in entries:
        wrapped_lines = wrap_text(entry.description)
        text_block_height = len(wrapped_lines) * line_height + 12
        entry_height = max(entry_base_height, text_block_height)
        formatted_entries.append((entry, entry_height, wrapped_lines))
        content_height += entry_height

    max_scroll = max(0, content_height + padding - panel_rect.height)
    scroll = max(0, min(scroll_offset, max_scroll))

    hitboxes = []
    surface.set_clip(panel_rect)
    y_cursor = panel_rect.bottom - padding - scroll
    player_color = cfg.FACTION_GLOW_COLORS.get(game.player1.faction, (100, 200, 255))
    ai_color = cfg.FACTION_GLOW_COLORS.get(game.player2.faction, (255, 120, 120))

    for entry, entry_height, wrapped_lines in reversed(formatted_entries):
        y_cursor -= entry_height
        entry_rect = pygame.Rect(panel_rect.x + padding, y_cursor, panel_rect.width - 2 * padding, entry_height - 4)
        if entry_rect.bottom < panel_rect.top + padding:
            continue
        if entry_rect.top > panel_rect.bottom:
            continue

        owner_color = player_color if entry.owner == "player" else ai_color
        if entry.event_type == "system":
            owner_color = (255, 215, 0)
        elif entry.event_type == "chat":
            if "System" in entry.description: owner_color = (255, 215, 0)
            elif "You" in entry.description: owner_color = (100, 255, 100)
            else: owner_color = (200, 200, 255)
        elif entry.event_type in ["scorch", "destroy"]:
             owner_color = (255, 80, 80)
        
        hovered = hover_pos and entry_rect.collidepoint(hover_pos)
        entry_surface = pygame.Surface((entry_rect.width, entry_rect.height), pygame.SRCALPHA)
        entry_surface.fill((owner_color[0], owner_color[1], owner_color[2], 160 if hovered else 120))
        pygame.draw.rect(entry_surface, owner_color, entry_surface.get_rect(), width=2, border_radius=8)

        icon_rect = pygame.Rect(8, 6, icon_width, entry_rect.height - 12)
        pygame.draw.rect(entry_surface, (255, 255, 255, 90), icon_rect, border_radius=4)
        
        if entry.icon:
            icon_surf = history_font.render(entry.icon, True, (255, 255, 255))
            icon_dest = icon_surf.get_rect(center=icon_rect.center)
            entry_surface.blit(icon_surf, icon_dest)

        for idx, line in enumerate(wrapped_lines):
            text_surface = history_font.render(line, True, cfg.WHITE)
            text_rect = text_surface.get_rect()
            text_rect.topleft = (icon_rect.right + 8, 6 + idx * line_height)
            entry_surface.blit(text_surface, text_rect)

        surface.blit(entry_surface, entry_rect.topleft)
        hitboxes.append((entry, entry_rect.copy()))

    surface.set_clip(None)
    return hitboxes, max_scroll

def draw_leader_portrait(surface, player, x, y, width=100, height=150, show_label=True):
    if not player.leader:
        return None
    
    leader_rect = pygame.Rect(x, y, width, height)
    leader_card_id = player.leader.get('card_id', None)
    
    if leader_card_id:
        leader_image_path = f"assets/{leader_card_id}_leader.png"
        import os
        try:
            if os.path.exists(leader_image_path):
                leader_img = pygame.image.load(leader_image_path).convert_alpha()
                scaled_image = pygame.transform.scale(leader_img, (width, height))
                surface.blit(scaled_image, (x, y))
                pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
            elif leader_card_id in ALL_CARDS:
                leader_card = ALL_CARDS[leader_card_id]
                scaled_image = pygame.transform.scale(leader_card.image, (width, height))
                surface.blit(scaled_image, (x, y))
                pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
            else:
                pygame.draw.rect(surface, (60, 60, 80), leader_rect)
                pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
        except:
            pygame.draw.rect(surface, (60, 60, 80), leader_rect)
            pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
    else:
        pygame.draw.rect(surface, (60, 60, 80), leader_rect)
        pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
    
    if show_label:
        name_text = cfg.UI_FONT.render("LEADER", True, (255, 215, 0))
        name_rect = name_text.get_rect(center=(x + width // 2, y + height + 15))
        surface.blit(name_text, name_rect)
    
    return leader_rect

def draw_leader_column(surface, player, area_rect, ability_ready=True, faction_power_ready=False, hover_pos=None):
    faction_color = cfg.FACTION_GLOW_COLORS.get(player.faction, (200, 200, 200))
    padding = max(12, int(area_rect.width * 0.05))
    column_left = area_rect.x + padding
    column_right = area_rect.right - padding
    column_width = max(1, column_right - column_left)
    column_center_x = column_left + column_width // 2
    spacing = max(8, min(12, int(10 * display_manager.SCALE_FACTOR)))

    # Leader portraits should be bigger for visibility (1.8x card size)
    leader_width = int(cfg.CARD_WIDTH * 1.8)
    leader_height = int(cfg.CARD_HEIGHT * 1.8)

    button_width = min(column_width - 4, max(int(cfg.CARD_WIDTH * 1.2), 120))
    button_height = max(int(cfg.CARD_HEIGHT * 0.28), 50)
    
    faction_size = max(int(cfg.CARD_WIDTH * 0.6), 65)
    special_size = max(int(cfg.CARD_WIDTH * 0.45), 55)
    stats_height = max(36, int(42 * display_manager.SCALE_FACTOR))

    special_info = None
    if player.faction == FACTION_TAURI:
        special_info = {
            "kind": "iris",
            "ready": player.iris_defense.is_available(),
            "active": player.iris_defense.is_active(),
            "label": "IRIS"
        }
    elif getattr(player, "ring_transportation", None):
        special_info = {
            "kind": "rings",
            "ready": player.ring_transportation.can_use(),
            "active": player.ring_transportation.animation_in_progress,
            "label": "RINGS"
        }

    element_heights = [button_height + 4 + stats_height, faction_size]
    if special_info:
        element_heights.append(special_size)
    element_heights.append(leader_height)
    stack_height = sum(element_heights) + spacing * (len(element_heights) - 1)
    available_top = area_rect.top + padding
    available_bottom = area_rect.bottom - padding
    max_top = max(available_top, available_bottom - stack_height)
    y_cursor = area_rect.centery - stack_height // 2
    y_cursor = max(available_top, min(y_cursor, max_top))

    # ABILITY BUTTON
    ability_rect = pygame.Rect(column_center_x - button_width // 2, y_cursor, button_width, button_height)
    ability_surface = pygame.Surface((ability_rect.width, ability_rect.height), pygame.SRCALPHA)
    
    leader_ability_name = "ABILITY"
    if player.leader:
        leader_ability_name = player.leader.get('ability_name', player.leader.get('name', 'ABILITY'))
        if len(leader_ability_name) > 12:
            leader_ability_name = leader_ability_name[:10] + ".."
    
    is_hovered = hover_pos and ability_rect.collidepoint(hover_pos)
    
    if ability_ready:
        bg_color = (25, 45, 70, 240)
        border_color = faction_color
        text_color = cfg.WHITE
        status_text = "READY"
        status_color = (100, 255, 100)
    else:
        bg_color = (30, 30, 35, 200)
        border_color = (80, 80, 90)
        text_color = (150, 150, 150)
        status_text = "USED"
        status_color = (150, 80, 80)
    
    if is_hovered and ability_ready:
        bg_color = (35, 60, 95, 250)
        border_color = tuple(min(255, c + 40) for c in faction_color)
    
    ability_surface.fill(bg_color)
    pygame.draw.rect(ability_surface, border_color, ability_surface.get_rect(), width=3, border_radius=8)
    
    name_font = _get_cached_font(max(12, int(14 * display_manager.SCALE_FACTOR)), bold=True)
    name_text = name_font.render(leader_ability_name.upper(), True, text_color)
    name_rect = name_text.get_rect(centerx=ability_rect.width // 2, top=6)
    ability_surface.blit(name_text, name_rect)

    status_font = _get_cached_font(max(10, int(11 * display_manager.SCALE_FACTOR)), bold=True)
    status_surf = status_font.render(status_text, True, status_color)
    status_rect = status_surf.get_rect(centerx=ability_rect.width // 2, bottom=ability_rect.height - 5)
    ability_surface.blit(status_surf, status_rect)
    
    icon_y = ability_rect.height // 2
    icon_radius = min(12, (ability_rect.height - 24) // 2)
    if icon_radius > 4:
        pygame.draw.circle(ability_surface, border_color, (ability_rect.width // 2, icon_y), icon_radius, 2)
        pygame.draw.circle(ability_surface, border_color, (ability_rect.width // 2, icon_y), icon_radius - 4, 1)
    
    surface.blit(ability_surface, ability_rect.topleft)

    # STATS ROW
    stats_rect = pygame.Rect(ability_rect.x, ability_rect.bottom + 4, ability_rect.width, stats_height)
    stat_val_font = _get_cached_font(max(14, int(16 * display_manager.SCALE_FACTOR)), bold=True)
    stat_lbl_font = _get_cached_font(max(8, int(9 * display_manager.SCALE_FACTOR)), bold=True)
    
    section_width = stats_rect.width / 3
    stats_data = [
        ("HAND", len(player.hand), (120, 220, 255)),
        ("DECK", len(player.deck), (220, 220, 120)),
        ("DISC", len(player.discard_pile), (255, 120, 120))
    ]

    for i, (label, value, color) in enumerate(stats_data):
        sx = stats_rect.x + (i * section_width)
        s_rect = pygame.Rect(sx, stats_rect.y, section_width, stats_height)
        panel_rect = s_rect.inflate(-4, 0)
        s_bg = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s_bg.fill((20, 25, 35, 230))
        surface.blit(s_bg, panel_rect.topleft)
        border_col = tuple(max(0, c - 40) for c in faction_color)
        pygame.draw.rect(surface, border_col, panel_rect, width=1, border_radius=5)
        lbl_surf = stat_lbl_font.render(label, True, (160, 160, 170))
        lbl_rect = lbl_surf.get_rect(centerx=panel_rect.centerx, top=panel_rect.top + 4)
        surface.blit(lbl_surf, lbl_rect)
        val_surf = stat_val_font.render(str(value), True, color)
        val_rect = val_surf.get_rect(centerx=panel_rect.centerx, bottom=panel_rect.bottom - 2)
        surface.blit(val_surf, val_rect)

    discard_hit_rect = stats_rect.copy()
    y_cursor = stats_rect.bottom + spacing

    # FACTION POWER BUTTON
    faction_rect = pygame.Rect(0, y_cursor, faction_size, faction_size)
    faction_rect.centerx = column_center_x
    faction_surface = pygame.Surface((faction_rect.width, faction_rect.height), pygame.SRCALPHA)

    cx, cy = faction_surface.get_rect().center
    outer_radius = faction_rect.width // 2 - 2
    inner_radius = int(outer_radius * 0.65)

    faction_name = player.faction if hasattr(player, 'faction') else "Tau'ri"
    faction_gate_colors = {
        "Tau'ri": {"ring": (120, 130, 140), "horizon": (30, 100, 200), "chevron": (255, 180, 50)},
        "Goa'uld": {"ring": (180, 150, 80), "horizon": (180, 50, 30), "chevron": (255, 80, 40)},
        "Jaffa": {"ring": (160, 140, 100), "horizon": (180, 140, 40), "chevron": (255, 200, 100)},
        "Lucian Alliance": {"ring": (100, 80, 120), "horizon": (120, 50, 150), "chevron": (255, 100, 200)},
        "Asgard": {"ring": (180, 200, 220), "horizon": (40, 150, 180), "chevron": (150, 255, 255)},
    }
    colors = faction_gate_colors.get(faction_name, faction_gate_colors["Tau'ri"])

    brightness = 1.0 if faction_power_ready else 0.4
    is_faction_hovered = hover_pos and faction_rect.collidepoint(hover_pos)
    if is_faction_hovered and faction_power_ready:
        brightness = 1.3

    def adj(c, m):
        return tuple(min(255, int(x * m)) for x in c)

    ring_c = adj(colors["ring"], brightness)
    horizon_c = adj(colors["horizon"], brightness)
    chevron_c = adj(colors["chevron"], brightness)

    pygame.draw.circle(faction_surface, (20, 25, 35), (cx, cy), outer_radius)
    pygame.draw.circle(faction_surface, horizon_c, (cx, cy), inner_radius)
    
    for i in range(4):
        r = int(inner_radius * (0.8 - i * 0.15))
        pygame.draw.circle(faction_surface, adj(colors["horizon"], brightness * 1.2), (cx, cy), r, 2)
    
    pygame.draw.circle(faction_surface, adj((255, 255, 255), brightness * 0.8), (cx, cy), inner_radius // 4)
    pygame.draw.circle(faction_surface, ring_c, (cx, cy), outer_radius, max(3, outer_radius // 8))
    
    chevron_radius = int(outer_radius * 0.85)
    chevron_size = max(3, outer_radius // 6)
    for i in range(9):
        angle = (i * 2 * 3.14159 / 9) - 3.14159 / 2
        chev_x = cx + int(chevron_radius * math.cos(angle))
        chev_y = cy + int(chevron_radius * math.sin(angle))
        pygame.draw.circle(faction_surface, chevron_c, (chev_x, chev_y), chevron_size)

    if faction_power_ready:
        for i in range(2):
            pygame.draw.circle(faction_surface, (*chevron_c, 60 - i * 30), (cx, cy), outer_radius + 2 + i, 2)

    surface.blit(faction_surface, faction_rect.topleft)

    power_label_rect = pygame.Rect(faction_rect.x - 10, faction_rect.bottom + 2, faction_rect.width + 20, 16)
    power_label_font = _get_cached_font(max(9, int(10 * display_manager.SCALE_FACTOR)), bold=True)
    
    power_name = "FACTION"
    if player.faction_power:
        power_name = getattr(player.faction_power, 'name', 'POWER')
        if len(power_name) > 10:
            power_name = power_name[:8] + ".."
    
    label_surf = power_label_font.render(f"{power_name}", True, (200, 200, 220) if faction_power_ready else (120, 120, 130))
    label_rect = label_surf.get_rect(centerx=faction_rect.centerx, top=faction_rect.bottom + 1)
    surface.blit(label_surf, label_rect)

    score_rect_width = max(0, column_right - (faction_rect.right + spacing))
    score_rect = pygame.Rect(faction_rect.right + spacing, faction_rect.y, score_rect_width, faction_rect.height)
    if score_rect.width > 20:
        score_surface = pygame.Surface((score_rect.width, score_rect.height), pygame.SRCALPHA)
        score_surface.fill((20, 30, 50, 210))
        pygame.draw.rect(score_surface, faction_color, score_surface.get_rect(), width=3, border_radius=10)
        score_font = _get_cached_font(max(20, int(24 * display_manager.SCALE_FACTOR)), bold=True)
        score_text = score_font.render(str(player.score), True, cfg.WHITE)
        score_surface.blit(score_text, score_text.get_rect(center=score_surface.get_rect().center))
        surface.blit(score_surface, score_rect.topleft)
    else:
        score_rect = None

    y_cursor = max(faction_rect.bottom, label_rect.bottom) + spacing

    # SPECIAL BUTTON
    special_rect = None
    special_kind = None
    if special_info:
        special_rect = pygame.Rect(0, y_cursor, special_size, special_size)
        special_rect.centerx = column_center_x
        special_surface = pygame.Surface((special_rect.width, special_rect.height), pygame.SRCALPHA)
        
        base_color = (28, 36, 50)
        if special_info["active"]:
            ready_color = (255, 120, 100)
        elif special_info["ready"]:
            ready_color = faction_color
        else:
            ready_color = (70, 70, 80)
        
        is_special_hovered = hover_pos and special_rect.collidepoint(hover_pos)
        if is_special_hovered and special_info["ready"]:
            ready_color = tuple(min(255, c + 40) for c in ready_color[:3])
        
        center = special_surface.get_rect().center
        pygame.draw.circle(special_surface, base_color, center, special_rect.width // 2)
        pygame.draw.circle(special_surface, ready_color, center, special_rect.width // 2, width=3)

        if special_info["kind"] == "iris":
            blade_radius = int(special_rect.width * 0.32)
            for angle in range(0, 360, 45):
                radians = math.radians(angle)
                dx = int(math.cos(radians) * blade_radius)
                dy = int(math.sin(radians) * blade_radius)
                pygame.draw.line(special_surface, ready_color, center, (center[0] + dx, center[1] + dy), width=2)
        else:
            for i in range(3):
                pygame.draw.circle(special_surface, ready_color, center, int(special_rect.width * 0.15) + i * 5, width=2)

        surface.blit(special_surface, special_rect.topleft)
        
        special_label = special_info.get("label", "SPECIAL")
        special_font = _get_cached_font(max(8, int(9 * display_manager.SCALE_FACTOR)), bold=True)
        special_surf = special_font.render(special_label, True, ready_color)
        surface.blit(special_surf, special_surf.get_rect(centerx=special_rect.centerx, top=special_rect.bottom + 1))
        
        special_kind = special_info["kind"]
        y_cursor = special_rect.bottom + 14 + spacing

    portrait_rect = pygame.Rect(column_center_x - leader_width // 2, y_cursor, leader_width, leader_height)
    leader_rect = draw_leader_portrait(surface, player, portrait_rect.x, portrait_rect.y, portrait_rect.width, portrait_rect.height, show_label=False)

    return {
        "leader_rect": leader_rect or portrait_rect,
        "ability_rect": ability_rect,
        "faction_rect": faction_rect,
        "score_rect": score_rect,
        "discard_rect": discard_hit_rect,
        "special_rect": special_rect,
        "special_kind": special_kind,
    }