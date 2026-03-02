import pygame
import math
import game_config as cfg
import display_manager
from game_config import (
    PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS,
    WEATHER_ZONE_HEIGHT, weather_y,
    CARD_WIDTH, CARD_HEIGHT,
    PLAYFIELD_WIDTH, PLAYFIELD_LEFT,
    HAND_REGION_LEFT
)
from render_engine import (
    draw_card, draw_weather_slots, draw_horn_slots, _compute_hand_positions,
    _render_text, _get_cached_font,
)
from abilities import Ability, has_ability, is_spy

_pass_btn_cache = {}


def draw_aa_circle(surface, color, center, radius, width=0):
    """Draw an anti-aliased circle using pygame-ce's aacircle if available.

    Falls back to standard circle if aacircle is not supported.

    Args:
        surface: Target surface to draw on
        color: RGB or RGBA color tuple
        center: (x, y) center position
        radius: Circle radius in pixels
        width: Border width (0 = filled)
    """
    try:
        # pygame-ce has draw.aacircle for anti-aliased circles
        if width == 0:
            # Filled anti-aliased circle
            pygame.draw.aacircle(surface, center[0], center[1], radius, color)
        else:
            # Anti-aliased circle outline
            pygame.draw.aacircle(surface, center[0], center[1], radius, color)
            if radius > width:
                # Draw inner circle to create ring effect
                inner_color = surface.get_at((int(center[0]), int(center[1]))) if width > 1 else (0, 0, 0, 0)
                pygame.draw.aacircle(surface, center[0], center[1], radius - width, inner_color)
    except (AttributeError, TypeError):
        # Fallback to standard circle
        pygame.draw.circle(surface, color, center, radius, width)

# Surface cache for frequently-used overlay surfaces
_surface_cache = {}


def _get_cached_surface(width, height, color):
    """Get a cached surface with the given size and fill color."""
    key = (width, height, color)
    if key not in _surface_cache:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        surf.fill(color)
        _surface_cache[key] = surf
    return _surface_cache[key]


def clear_surface_cache():
    """Clear the surface cache - call on resolution change."""
    _surface_cache.clear()

def draw_weather_separator(surface, game):
    """Draw the weather lane plus glowing turn divider strip."""
    zone_rect = pygame.Rect(0, weather_y, display_manager.SCREEN_WIDTH, WEATHER_ZONE_HEIGHT)
    zone_surface = _get_cached_surface(zone_rect.width, zone_rect.height, (18, 28, 48, 220))
    surface.blit(zone_surface, zone_rect.topleft)

    pygame.draw.line(surface, (70, 90, 140), zone_rect.topleft, (zone_rect.right, zone_rect.top), 2)
    pygame.draw.line(surface, (70, 90, 140), (zone_rect.left, zone_rect.bottom), (zone_rect.right, zone_rect.bottom), 2)

    divider_height = min(WEATHER_ZONE_HEIGHT, cfg.pct_y(0.03))
    divider_rect = pygame.Rect(
        zone_rect.left,
        zone_rect.bottom - divider_height,
        zone_rect.width,
        divider_height
    )
    divider_surface = _get_cached_surface(divider_rect.width, divider_rect.height, (255, 170, 60, 90))
    surface.blit(divider_surface, divider_rect.topleft)
    pygame.draw.rect(surface, (255, 210, 120, 200), divider_rect, width=3, border_radius=6)
    # Turn indicator moved to HUD - no duplicate text here


_iris_cache = {}

def _draw_iris_overlay(surface, row_rects):
    """Draw metallic shutter overlay over opponent's play area when Iris is active."""
    for row_name, rect in row_rects.items():
        cache_key = (row_name, rect.width, rect.height)
        overlay = _iris_cache.get(cache_key)
        if overlay is None:
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            blade_color = cfg.IRIS_BLADE_COLOR
            highlight = (140, 145, 155, 100)
            num_blades = 6
            blade_height = rect.height // num_blades
            for i in range(num_blades):
                y = i * blade_height
                pygame.draw.rect(overlay, blade_color, (0, y, rect.width, blade_height - 2))
                pygame.draw.line(overlay, highlight, (0, y), (rect.width, y), 2)
            if row_name == "ranged":
                font = _get_cached_font(max(14, int(16 * display_manager.SCALE_FACTOR)), bold=True)
                text = _render_text(font, "GATE SHIELD ACTIVE", cfg.IRIS_TEXT_COLOR)
                text_rect = text.get_rect(center=(rect.width // 2, rect.height // 2))
                overlay.blit(text, text_rect)
            _iris_cache[cache_key] = overlay
        surface.blit(overlay, rect.topleft)


def draw_board(surface, game, selected_card, dragging_card=None, drag_hover_highlight=None,
               drag_row_highlights=None):
    """Draw the game board, including contextual drop highlights."""
    draw_weather_separator(surface, game)
    draw_weather_slots(surface, game, dragging_card=dragging_card)
    draw_horn_slots(surface, game, dragging_card=dragging_card)
    
    # Darken inactive lanes (Witcher 3 polish)
    if game.player1.has_passed or game.current_player != game.player1:
        for row_name, row_rect in cfg.PLAYER_ROW_RECTS.items():
            dark_surface = _get_cached_surface(row_rect.width, row_rect.height, (0, 0, 0, cfg.INACTIVE_LANE_ALPHA))
            surface.blit(dark_surface, row_rect.topleft)

    # Subtle glow on active player's lanes (Witcher 3 polish)
    if game.current_player == game.player1 and not game.player1.has_passed:
        for row_name, row_rect in cfg.PLAYER_ROW_RECTS.items():
            glow_surface = _get_cached_surface(row_rect.width, row_rect.height, (100, 150, 255, 30))
            surface.blit(glow_surface, row_rect.topleft)

    # Highlight valid target rows with semi-transparent fill and border
    if selected_card and selected_card.row not in ["special", "weather"]:
        valid_rows = []
        card_is_spy = is_spy(selected_card)

        target_rects = cfg.OPPONENT_ROW_RECTS if card_is_spy else cfg.PLAYER_ROW_RECTS
        fill_color = cfg.SPY_TARGET_FILL if card_is_spy else (100, 255, 100, 40)

        if selected_card.row == "agile":
            valid_rows = ["close", "ranged"]
        elif selected_card.row in ["close", "ranged", "siege"]:
            valid_rows = [selected_card.row]

        for r_name in valid_rows:
            if r_name in target_rects:
                rect = target_rects[r_name]
                highlight_surface = _get_cached_surface(rect.width, rect.height, fill_color)
                surface.blit(highlight_surface, (rect.x, rect.y))
    
    # Highlight weather rows when dragging weather cards
    if dragging_card and dragging_card.row == "weather":
        ability_text = dragging_card.ability or ""
        ability_lower = ability_text.lower() if ability_text else ""

        # Determine which rows this weather card affects
        affected_rows = []
        if "all" in ability_lower or "any" in ability_lower:
            affected_rows = ["close", "ranged", "siege"]
        else:
            # Check for specific row types in the ability text
            if "close" in ability_lower:
                affected_rows.append("close")
            if "ranged" in ability_lower:
                affected_rows.append("ranged")
            if "siege" in ability_lower:
                affected_rows.append("siege")
            # If no specific row is mentioned, assume it affects all rows
            if not affected_rows:
                affected_rows = ["close", "ranged", "siege"]

        # Highlight affected rows for both players
        fill_color = cfg.WEATHER_HIGHLIGHT
        for row_name in affected_rows:
            if row_name in cfg.PLAYER_ROW_RECTS:
                rect = cfg.PLAYER_ROW_RECTS[row_name]
                highlight_surface = _get_cached_surface(rect.width, rect.height, fill_color)
                surface.blit(highlight_surface, rect.topleft)
            if row_name in cfg.OPPONENT_ROW_RECTS:
                rect = cfg.OPPONENT_ROW_RECTS[row_name]
                highlight_surface = _get_cached_surface(rect.width, rect.height, fill_color)
                surface.blit(highlight_surface, rect.topleft)

    # Highlight general special targets (non-horn placement)
    if dragging_card and dragging_card.row == "special":
        if not has_ability(dragging_card, Ability.COMMAND_NETWORK):
            fill_color = (255, 255, 255, 30)
            for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                for rect in rects.values():
                    highlight_surface = _get_cached_surface(rect.width, rect.height, fill_color)
                    surface.blit(highlight_surface, rect.topleft)

    if drag_row_highlights:
        for highlight in drag_row_highlights:
            rect = highlight["rect"]
            color = highlight.get("color", (255, 255, 255))
            alpha = highlight.get("alpha", 80)
            highlight_surface = _get_cached_surface(rect.width, rect.height, (color[0], color[1], color[2], alpha))
            surface.blit(highlight_surface, rect.topleft)
            inflate_y = int(display_manager.SCREEN_HEIGHT*0.006)
            pygame.draw.rect(surface, color, rect.inflate(0, inflate_y), width=3, border_radius=6)

    if drag_hover_highlight:
        rect = drag_hover_highlight["rect"]
        color = drag_hover_highlight["color"]
        alpha = drag_hover_highlight.get("alpha", 80)
        hover_surface = _get_cached_surface(rect.width, rect.height, (color[0], color[1], color[2], alpha))
        surface.blit(hover_surface, rect.topleft)
        inflate_y = int(display_manager.SCREEN_HEIGHT*0.006)
        pygame.draw.rect(surface, color, rect.inflate(0, inflate_y), width=4, border_radius=6)

    # --- Draw Iris Defense overlay if active ---
    if hasattr(game.player1, 'iris_defense') and game.player1.iris_defense.is_active():
        _draw_iris_overlay(surface, cfg.OPPONENT_ROW_RECTS)

    # --- Draw subtle row type labels in empty rows ---
    _ROW_LABELS = {"close": "CLOSE COMBAT", "ranged": "RANGED", "siege": "SIEGE"}
    _label_font = _get_cached_font(max(11, int(13 * display_manager.SCALE_FACTOR)), bold=True)
    for player, rects in [(game.player1, cfg.PLAYER_ROW_RECTS),
                          (game.player2, cfg.OPPONENT_ROW_RECTS)]:
        for row_name, row_rect in rects.items():
            if player.board[row_name]:
                continue
            label = _ROW_LABELS.get(row_name)
            if not label:
                continue
            dim_color = (60, 70, 90)
            text_surf = _render_text(_label_font, label, dim_color)
            surface.blit(text_surf, text_surf.get_rect(center=row_rect.center))

    # --- Draw cards on board (Dynamic Fan Layout with Gap) ---
    row_map = {
        game.player2: cfg.OPPONENT_ROW_RECTS,
        game.player1: cfg.PLAYER_ROW_RECTS,
    }

    mouse_pos = pygame.mouse.get_pos()

    for player, rects in row_map.items():
        for row_name, row_rect in rects.items():
            cards_in_row = player.board[row_name]
            if not cards_in_row:
                continue
            
            total_cards = len(cards_in_row)
            available_width = cfg.PLAYFIELD_WIDTH
            
            # Fan Logic: Spread cards evenly
            standard_spacing = int(cfg.CARD_WIDTH * cfg.CARD_OVERLAP_RATIO)
            needed_width = (total_cards - 1) * standard_spacing + cfg.CARD_WIDTH
            
            if needed_width <= available_width:
                start_x = cfg.PLAYFIELD_LEFT + (available_width - needed_width) // 2
                spacing = standard_spacing
            else:
                start_x = cfg.PLAYFIELD_LEFT
                spacing = (available_width - cfg.CARD_WIDTH) / (total_cards - 1)

            # Check for insertion gap if dragging a card over this lane
            insertion_index = -1
            if dragging_card and row_rect.collidepoint(mouse_pos):
                if dragging_card.row == row_name or (dragging_card.row == "agile" and row_name in ["close", "ranged"]):
                    insertion_index = total_cards # Default to end
                    for i, card in enumerate(cards_in_row):
                        if mouse_pos[0] < card.rect.centerx:
                            insertion_index = i
                            break

            for i, card in enumerate(cards_in_row):
                # Calculate base position
                x = start_x + i * spacing
                
                # Apply visual parting shift
                if insertion_index != -1:
                    if i >= insertion_index:
                        x += cfg.CARD_WIDTH * cfg.CARD_GAP_SHIFT_SCALE  # Shift right to open a gap
                    else:
                        x -= cfg.CARD_WIDTH * cfg.CARD_GAP_SHIFT_SCALE  # Shift left slightly

                y = row_rect.centery - cfg.CARD_HEIGHT // 2
                
                # Update collision rect
                card.rect.topleft = (int(x), int(y))
                card.rect.width = cfg.CARD_WIDTH
                card.rect.height = cfg.CARD_HEIGHT
                
                if getattr(card, "in_transit", False):
                    continue
                draw_card(surface, card, int(x), int(y), render_details=True)
    
def draw_scores(surface, game, anim_manager=None, p1_score_x=0, p1_score_y=0, p2_score_x=0, p2_score_y=0, render_static=True):
    """Draws the player scores and rounds won next to leader portraits."""
    if anim_manager and anim_manager.score_animations:
        anim_manager.draw_score_animations(surface, cfg.SCORE_FONT)
        if not render_static:
            return
    elif not render_static:
        return

    p1_color = (100, 255, 100) if game.player1.score > game.player2.score else cfg.WHITE
    p1_score_text = _render_text(cfg.SCORE_FONT, f"Score: {game.player1.score}", p1_color)
    surface.blit(p1_score_text, (p1_score_x, p1_score_y))

    p2_color = (100, 255, 100) if game.player2.score > game.player1.score else cfg.WHITE
    p2_score_text = _render_text(cfg.SCORE_FONT, f"Score: {game.player2.score}", p2_color)
    surface.blit(p2_score_text, (p2_score_x, p2_score_y))

    p1_rounds_text = _render_text(cfg.UI_FONT, f"Rounds Won: {game.player1.rounds_won}", cfg.WHITE)
    p2_rounds_text = _render_text(cfg.UI_FONT, f"Rounds Won: {game.player2.rounds_won}", cfg.WHITE)
    surface.blit(p1_rounds_text, (p1_score_x, p1_score_y + 55))
    surface.blit(p2_rounds_text, (p2_score_x, p2_score_y + 55))

def draw_pass_button(surface, game, button_rect=None):
    """Draws the DHD-style pass button."""
    if not button_rect:
        return
    target_rect = button_rect
    center_x = target_rect.centerx
    center_y = target_rect.centery
    
    # Base state
    can_pass = game.current_player == game.player1 and not game.player1.has_passed
    
    # Outer DHD ring (scaled)
    outer_radius = max(20, min(target_rect.width, target_rect.height) // 2)
    inner_radius = max(10, int(outer_radius * 0.7))
    
    # Outer ring color (bronze/metallic)
    outer_color = (120, 100, 80)
    pygame.draw.circle(surface, outer_color, (center_x, center_y), outer_radius)
    pygame.draw.circle(surface, (80, 70, 60), (center_x, center_y), outer_radius, width=max(1, int(3 * display_manager.SCALE_FACTOR)))
    
    # DHD symbols around the ring (simplified chevrons) - scaled
    num_symbols = 7
    for i in range(num_symbols):
        angle = (i * 360 / num_symbols) - 90  # Start from top
        rad = math.radians(angle)
        symbol_x = center_x + math.cos(rad) * (42 * display_manager.SCALE_FACTOR)
        symbol_y = center_y + math.sin(rad) * (42 * display_manager.SCALE_FACTOR)
        
        # Small chevron-like triangle
        symbol_color = (150, 130, 100) if can_pass else (80, 70, 60)
        symbol_size = max(2, int(5 * display_manager.SCALE_FACTOR))
        pygame.draw.circle(surface, symbol_color, (int(symbol_x), int(symbol_y)), symbol_size)
    
    # Center button (home/dial button)
    if can_pass:
        # Glowing red when active
        glow_time = pygame.time.get_ticks() / cfg.PASS_BUTTON_PULSE_RATE
        glow_pulse = abs(math.sin(glow_time))
        center_alpha = int(150 + glow_pulse * 105)
        
        # Outer glow — cached
        glow_key = ("pass_glow", inner_radius)
        glow_surf = _pass_btn_cache.get(glow_key)
        if glow_surf is None:
            glow_surf = pygame.Surface((inner_radius * 3, inner_radius * 3), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 50, 50, 80), (inner_radius * 1.5, inner_radius * 1.5), inner_radius + int(10 * display_manager.SCALE_FACTOR))
            _pass_btn_cache[glow_key] = glow_surf
        surface.blit(glow_surf, (center_x - inner_radius * 1.5, center_y - inner_radius * 1.5))
        
        # Main button - glowing red
        pygame.draw.circle(surface, (200, 40, 40), (center_x, center_y), inner_radius)
        pygame.draw.circle(surface, (255, 100, 100), (center_x, center_y), max(1, inner_radius - int(5 * display_manager.SCALE_FACTOR)))
        pygame.draw.circle(surface, (255, 50, 50, center_alpha), (center_x, center_y), max(1, inner_radius - int(10 * display_manager.SCALE_FACTOR)))
        
        # Center dot (button press point)
        pygame.draw.circle(surface, (255, 200, 200), (center_x, center_y), max(2, int(8 * display_manager.SCALE_FACTOR)))
        pygame.draw.circle(surface, (255, 255, 255, 200), (center_x, center_y), max(1, int(4 * display_manager.SCALE_FACTOR)))
    else:
        # Inactive - dark gray
        pygame.draw.circle(surface, (60, 60, 70), (center_x, center_y), inner_radius)
        pygame.draw.circle(surface, (80, 80, 90), (center_x, center_y), max(1, inner_radius - int(5 * display_manager.SCALE_FACTOR)))
        pygame.draw.circle(surface, (50, 50, 60), (center_x, center_y), max(1, inner_radius - int(10 * display_manager.SCALE_FACTOR)))
        pygame.draw.circle(surface, (70, 70, 80), (center_x, center_y), max(2, int(8 * display_manager.SCALE_FACTOR)))
    
    # "PASS" text below DHD
    text_color = (255, 200, 200) if can_pass else (120, 120, 120)
    pass_text = _render_text(cfg.UI_FONT, "PASS", text_color)
    text_rect = pass_text.get_rect(center=(center_x, center_y + outer_radius + int(20 * display_manager.SCALE_FACTOR)))

    # Add shadow
    if can_pass:
        shadow = _render_text(cfg.UI_FONT, "PASS", (0, 0, 0))
        surface.blit(shadow, (text_rect.x + int(2 * display_manager.SCALE_FACTOR), text_rect.y + int(2 * display_manager.SCALE_FACTOR)))
    
    surface.blit(pass_text, text_rect)


def draw_dhd_back_button(surface, x=30, y=30, size=80, label=None):
    """Draws a DHD-style back button. Returns the button rect for click detection."""
    center_x = x + size // 2
    center_y = y + size // 2
    button_rect = pygame.Rect(x, y, size, size)

    # Check if mouse is hovering over the button
    mouse_pos = pygame.mouse.get_pos()
    is_hovered = button_rect.collidepoint(mouse_pos)

    # Outer DHD ring (scaled)
    outer_radius = size // 2
    inner_radius = int(outer_radius * 0.65)

    # Outer ring color (bronze/metallic, redder on hover)
    if is_hovered:
        outer_color = (140, 80, 80)
        ring_border = (110, 50, 50)
    else:
        outer_color = (100, 120, 140)
        ring_border = (70, 90, 110)
    pygame.draw.circle(surface, outer_color, (center_x, center_y), outer_radius)
    pygame.draw.circle(surface, ring_border, (center_x, center_y), outer_radius, width=max(1, int(3 * display_manager.SCALE_FACTOR)))

    # DHD symbols around the ring (simplified chevrons)
    num_symbols = 7
    for i in range(num_symbols):
        angle = (i * 360 / num_symbols) - 90  # Start from top
        rad = math.radians(angle)
        symbol_dist = outer_radius * 0.75
        symbol_x = center_x + math.cos(rad) * symbol_dist
        symbol_y = center_y + math.sin(rad) * symbol_dist

        # Small chevron-like dots - red on hover, cyan/blue otherwise
        symbol_color = (255, 120, 120) if is_hovered else (100, 180, 220)
        symbol_size = max(2, int(size * 0.06))
        pygame.draw.circle(surface, symbol_color, (int(symbol_x), int(symbol_y)), symbol_size)

    # Center button - glowing red on hover, cyan/blue otherwise
    glow_time = pygame.time.get_ticks() / 600.0
    glow_pulse = abs(math.sin(glow_time))

    # Outer glow — cached by state, alpha modulated
    glow_alpha = int(60 + glow_pulse * 40)
    dhd_glow_color = (255, 80, 80) if is_hovered else (50, 150, 255)
    dhd_glow_key = ("dhd_glow", inner_radius, dhd_glow_color)
    glow_surf = _pass_btn_cache.get(dhd_glow_key)
    if glow_surf is None:
        glow_surf = pygame.Surface((inner_radius * 3, inner_radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*dhd_glow_color, 100), (inner_radius * 1.5, inner_radius * 1.5), inner_radius + 8)
        _pass_btn_cache[dhd_glow_key] = glow_surf
    glow_surf.set_alpha(glow_alpha)
    surface.blit(glow_surf, (center_x - inner_radius * 1.5, center_y - inner_radius * 1.5))

    # Main button - glowing red on hover, cyan/blue otherwise
    if is_hovered:
        pygame.draw.circle(surface, (160, 40, 40), (center_x, center_y), inner_radius)
        pygame.draw.circle(surface, (200, 60, 60), (center_x, center_y), max(1, inner_radius - 4))
        pygame.draw.circle(surface, (240, 80, 80), (center_x, center_y), max(1, inner_radius - 8))
        # Center dot
        pygame.draw.circle(surface, (255, 150, 150), (center_x, center_y), max(2, int(size * 0.08)))
        pygame.draw.circle(surface, (255, 200, 200), (center_x, center_y), max(1, int(size * 0.04)))
    else:
        pygame.draw.circle(surface, (40, 100, 160), (center_x, center_y), inner_radius)
        pygame.draw.circle(surface, (60, 140, 200), (center_x, center_y), max(1, inner_radius - 4))
        pygame.draw.circle(surface, (80, 180, 240), (center_x, center_y), max(1, inner_radius - 8))
        # Center dot
        pygame.draw.circle(surface, (150, 220, 255), (center_x, center_y), max(2, int(size * 0.08)))
        pygame.draw.circle(surface, (200, 240, 255), (center_x, center_y), max(1, int(size * 0.04)))

    # Return clickable rect (just the circle, no label)
    return button_rect


def draw_mulligan_button(surface, mulligan_selected):
    """Draws the mulligan confirm button."""
    num_selected = len(mulligan_selected)
    
    # Color based on validity (2-5 cards)
    if num_selected >= 2 and num_selected <= 5:
        color = (50, 200, 100)  # Green - valid
    elif num_selected > 5:
        color = (200, 50, 50)  # Red - too many
    else:
        color = (100, 100, 100)  # Gray - not enough
    
    pygame.draw.rect(surface, color, cfg.MULLIGAN_BUTTON_RECT, border_radius=5)
    text = f"Redraw ({num_selected}/2-5)"
    mulligan_text = _render_text(cfg.UI_FONT, text, cfg.WHITE)
    text_rect = mulligan_text.get_rect(center=cfg.MULLIGAN_BUTTON_RECT.center)
    surface.blit(mulligan_text, text_rect)

def draw_zpm_resource(surface, player, x, y):
    """Draw ZPM resource indicators."""
    zpm_spacing = int(display_manager.SCREEN_WIDTH * 0.018)  # ~35px spacing
    zpm_height = int(display_manager.SCREEN_HEIGHT * 0.028)  # ~30px height
    
    for i in range(player.zpm_resource.max_zpms):
        zpm_x = x + i * zpm_spacing
        if i < player.zpm_resource.current_zpms:
            color = cfg.ZPM_ACTIVE_COLOR
        else:
            color = cfg.ZPM_DEPLETED_COLOR
        
        # Draw crystal shape
        pygame.draw.polygon(surface, color, [
            (zpm_x + 15, y),
            (zpm_x + 25, y + 10),
            (zpm_x + 20, y + zpm_height),
            (zpm_x + 10, y + zpm_height),
            (zpm_x + 5, y + 10),
        ])
        pygame.draw.polygon(surface, cfg.WHITE, [
            (zpm_x + 15, y),
            (zpm_x + 25, y + 10),
            (zpm_x + 20, y + zpm_height),
            (zpm_x + 10, y + zpm_height),
            (zpm_x + 5, y + 10),
        ], width=2)

def draw_mission_objective(surface, player, x, y):
    """Draw current mission objective."""
    if player.current_mission and not player.current_mission.completed:
        mission_text = _render_text(cfg.UI_FONT, "Mission:", (255, 255, 100))
        surface.blit(mission_text, (x, y))

        desc_text = _render_text(cfg.UI_FONT, player.current_mission.description, cfg.WHITE)
        surface.blit(desc_text, (x, y + 20))

        reward_text = _render_text(cfg.UI_FONT, f"Reward: {player.current_mission.reward_desc}", (100, 255, 100))
        surface.blit(reward_text, (x, y + 40))
    elif player.current_mission and player.current_mission.completed:
        completed_text = _render_text(cfg.UI_FONT, "Mission Completed!", (100, 255, 100))
        surface.blit(completed_text, (x, y))
