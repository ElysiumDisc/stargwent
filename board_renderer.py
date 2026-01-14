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
    draw_card, draw_weather_slots, draw_horn_slots, _compute_hand_positions
)

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


def draw_lane_labels(surface):
    """Lane labels intentionally suppressed for cleaner UI."""
    return


def draw_board(surface, game, selected_card, dragging_card=None, drag_hover_highlight=None,
               drag_row_highlights=None):
    """Draw the game board, including contextual drop highlights."""
    draw_weather_separator(surface, game)
    draw_lane_labels(surface)
    draw_weather_slots(surface, game, dragging_card=dragging_card)
    draw_horn_slots(surface, game, dragging_card=dragging_card)
    
    # Darken inactive lanes (Witcher 3 polish)
    if game.player1.has_passed or game.current_player != game.player1:
        for row_name, row_rect in cfg.PLAYER_ROW_RECTS.items():
            dark_surface = _get_cached_surface(row_rect.width, row_rect.height, (0, 0, 0, 40))
            surface.blit(dark_surface, row_rect.topleft)

    # Subtle glow on active player's lanes (Witcher 3 polish)
    if game.current_player == game.player1 and not game.player1.has_passed:
        for row_name, row_rect in cfg.PLAYER_ROW_RECTS.items():
            glow_surface = _get_cached_surface(row_rect.width, row_rect.height, (100, 150, 255, 30))
            surface.blit(glow_surface, row_rect.topleft)

    # Highlight valid target rows with semi-transparent fill and border
    if selected_card and selected_card.row not in ["special", "weather"]:
        valid_rows = []
        is_spy = "Deep Cover Agent" in (selected_card.ability or "")

        target_rects = cfg.OPPONENT_ROW_RECTS if is_spy else cfg.PLAYER_ROW_RECTS
        fill_color = (255, 100, 100, 40) if is_spy else (100, 255, 100, 40)

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
        fill_color = (180, 100, 100, 60)  # Reddish transparent fill for weather
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
        ability_text = dragging_card.ability or ""
        if "Command Network" not in ability_text:
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
            standard_spacing = int(cfg.CARD_WIDTH * 0.85) # 15% overlap
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
                        x += cfg.CARD_WIDTH * 0.4 # Shift right to open a gap
                    else:
                        x -= cfg.CARD_WIDTH * 0.4 # Shift left slightly

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
    p1_score_text = cfg.SCORE_FONT.render(f"Score: {game.player1.score}", True, p1_color)
    surface.blit(p1_score_text, (p1_score_x, p1_score_y))
    
    p2_color = (100, 255, 100) if game.player2.score > game.player1.score else cfg.WHITE
    p2_score_text = cfg.SCORE_FONT.render(f"Score: {game.player2.score}", True, p2_color)
    surface.blit(p2_score_text, (p2_score_x, p2_score_y))

    p1_rounds_text = cfg.UI_FONT.render(f"Rounds Won: {game.player1.rounds_won}", True, cfg.WHITE)
    p2_rounds_text = cfg.UI_FONT.render(f"Rounds Won: {game.player2.rounds_won}", True, cfg.WHITE)
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
        glow_time = pygame.time.get_ticks() / 500.0
        glow_pulse = abs(math.sin(glow_time))
        center_alpha = int(150 + glow_pulse * 105)
        
        # Outer glow
        glow_surf = pygame.Surface((inner_radius * 3, inner_radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 50, 50, 80), (inner_radius * 1.5, inner_radius * 1.5), inner_radius + int(10 * display_manager.SCALE_FACTOR))
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
    pass_text = cfg.UI_FONT.render("PASS", True, text_color)
    text_rect = pass_text.get_rect(center=(center_x, center_y + outer_radius + int(20 * display_manager.SCALE_FACTOR)))
    
    # Add shadow
    if can_pass:
        shadow = cfg.UI_FONT.render("PASS", True, (0, 0, 0, 100))
        surface.blit(shadow, (text_rect.x + int(2 * display_manager.SCALE_FACTOR), text_rect.y + int(2 * display_manager.SCALE_FACTOR)))
    
    surface.blit(pass_text, text_rect)


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
    mulligan_text = cfg.UI_FONT.render(text, True, cfg.WHITE)
    text_rect = mulligan_text.get_rect(center=cfg.MULLIGAN_BUTTON_RECT.center)
    surface.blit(mulligan_text, text_rect)

def draw_zpm_resource(surface, player, x, y):
    """Draw ZPM resource indicators."""
    zpm_spacing = int(display_manager.SCREEN_WIDTH * 0.018)  # ~35px spacing
    zpm_height = int(display_manager.SCREEN_HEIGHT * 0.028)  # ~30px height
    
    for i in range(player.zpm_resource.max_zpms):
        zpm_x = x + i * zpm_spacing
        if i < player.zpm_resource.current_zpms:
            color = (100, 200, 255)  # Active ZPM - cyan
        else:
            color = (50, 50, 70)  # Depleted ZPM - dark
        
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
        mission_text = cfg.UI_FONT.render("Mission:", True, (255, 255, 100))
        surface.blit(mission_text, (x, y))
        
        desc_text = cfg.UI_FONT.render(player.current_mission.description, True, cfg.WHITE)
        surface.blit(desc_text, (x, y + 20))
        
        reward_text = cfg.UI_FONT.render(f"Reward: {player.current_mission.reward_desc}", True, (100, 255, 100))
        surface.blit(reward_text, (x, y + 40))
    elif player.current_mission and player.current_mission.completed:
        completed_text = cfg.UI_FONT.render("Mission Completed!", True, (100, 255, 100))
        surface.blit(completed_text, (x, y))
