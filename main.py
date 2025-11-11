import pygame
import sys
import math
import random
from pygame.math import Vector2
from game import Game
from cards import ALL_CARDS, reload_card_images
from ai_opponent import AIController
from animations import AnimationManager, StargateActivationEffect, GlowAnimation, CardSlideAnimation, ScorchEffect, NaquadahExplosionEffect, AICardPlayAnimation, create_hero_animation, create_ability_animation, LegendaryLightningEffect
from deck_builder import run_deck_builder, build_faction_deck
from unlocks import CardUnlockSystem, show_card_reward_screen, show_leader_reward_screen, UNLOCKABLE_CARDS
from main_menu import run_main_menu, DeckManager, show_stargate_opening
from power import FACTION_POWERS, FactionPowerUI, FactionPowerEffect
from deck_persistence import record_victory, record_defeat, check_leader_unlock, get_persistence

# Initialize Pygame
pygame.init()

# Set high DPI awareness for Windows
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Windows 8.1+
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Windows Vista+
    except:
        pass  # Not Windows or already set

# Screen dimensions - Auto-detect and scale
# Get desktop resolution ONCE at very first run
# Store in a temp file to persist across module reloads
import os
import tempfile
_desktop_cache_file = os.path.join(tempfile.gettempdir(), 'stargwent_desktop_cache.txt')

try:
    # Try to load cached desktop resolution
    if os.path.exists(_desktop_cache_file):
        with open(_desktop_cache_file, 'r') as f:
            cached = f.read().strip().split('x')
            ORIGINAL_DESKTOP_WIDTH = int(cached[0])
            ORIGINAL_DESKTOP_HEIGHT = int(cached[1])
        print(f"🖥️  Using Cached Desktop Resolution: {ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")
    else:
        # First run - detect and cache
        display_info = pygame.display.Info()
        ORIGINAL_DESKTOP_WIDTH = display_info.current_w
        ORIGINAL_DESKTOP_HEIGHT = display_info.current_h
        # Save to cache file
        with open(_desktop_cache_file, 'w') as f:
            f.write(f"{ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")
        print(f"🖥️  Detected Original Desktop Resolution: {ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")
except Exception as e:
    # Fallback if caching fails
    display_info = pygame.display.Info()
    ORIGINAL_DESKTOP_WIDTH = display_info.current_w
    ORIGINAL_DESKTOP_HEIGHT = display_info.current_h
    print(f"🖥️  Desktop Resolution (no cache): {ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")

# Use cached desktop dimensions
DESKTOP_WIDTH = ORIGINAL_DESKTOP_WIDTH
DESKTOP_HEIGHT = ORIGINAL_DESKTOP_HEIGHT

# Target resolution (design is for 4K)
TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160

# Calculate scaling factor based on desktop size
# Use 95% of screen to leave room for OS taskbars
SCALE_X = (DESKTOP_WIDTH * 0.95) / TARGET_WIDTH
SCALE_Y = (DESKTOP_HEIGHT * 0.95) / TARGET_HEIGHT
SCALE_FACTOR = min(SCALE_X, SCALE_Y, 1.0)  # Don't scale up, only down

# Final screen size (scaled to fit)
SCREEN_WIDTH = int(TARGET_WIDTH * SCALE_FACTOR)
SCREEN_HEIGHT = int(TARGET_HEIGHT * SCALE_FACTOR)
FULLSCREEN = False

print(f"Display Detection:")
print(f"  Desktop: {DESKTOP_WIDTH}x{DESKTOP_HEIGHT}")
print(f"  Target: {TARGET_WIDTH}x{TARGET_HEIGHT}")
print(f"  Scale Factor: {SCALE_FACTOR:.2f}")
print(f"  Window Size: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

# Create the screen - Auto-scaled
if SCALE_FACTOR < 1.0:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SHOWN | pygame.SCALED)
    pygame.display.set_caption(f"Stargwent - Scaled to {SCREEN_WIDTH}x{SCREEN_HEIGHT} (from 4K)")
    print(f"✓ Using hardware scaling for better performance")
else:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SHOWN)
    pygame.display.set_caption("Stargwent - 4K (3840x2160)")

# Set custom window icon
try:
    icon = pygame.image.load("assets/tauri_oneill.png")
    pygame.display.set_icon(icon)
    print("✓ Custom window icon set.")
except pygame.error as e:
    print(f"⚠ Warning: Could not load window icon. {e}")

# Debug: Print actual screen size
actual_width = screen.get_width()
actual_height = screen.get_height()
print(f"✓ Screen initialized: {actual_width}x{actual_height}")

if actual_width != SCREEN_WIDTH or actual_height != SCREEN_HEIGHT:
    print(f"⚠ WARNING: Screen size mismatch!")
    print(f"   Actual: {actual_width}x{actual_height}")
    print(f"   Expected: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    print(f"   The OS may be applying additional scaling.")
else:
    print(f"✓ Window size is correct!")

# Reload card images now that screen is properly initialized
print("Loading card images...")
reload_card_images()
print("Card images loaded.")

# Colors
WHITE = (255, 255, 255)
PLAYER_HAND_BG = (40, 40, 50, 150) # Semi-transparent

# Fonts (scaled based on screen size)
SCORE_FONT = pygame.font.SysFont("Arial", int(48 * SCALE_FACTOR), bold=True)
UI_FONT = pygame.font.SysFont("Arial", int(28 * SCALE_FACTOR))
POWER_FONT = pygame.font.SysFont("Arial", int(32 * SCALE_FACTOR), bold=True)
ROW_FONT = pygame.font.SysFont("Arial", max(16, int(16 * SCALE_FACTOR)), bold=True)

# Card & Board dimensions (relative to screen height)
CARD_WIDTH = int(SCREEN_HEIGHT * 0.093)  # Target: ~100px at 1080p
CARD_HEIGHT = int(SCREEN_HEIGHT * 0.139)  # Target: ~150px at 1080p

# --- CORRECTED LAYOUT CALCULATION ---
# Base layout on card size to ensure everything fits properly

# 1. Define ROW_HEIGHT based on CARD_HEIGHT, adding minimal padding (5% instead of 10%)
ROW_HEIGHT = int(CARD_HEIGHT * 1.05)

# 2. Define heights for the UI areas
TOP_UI_MARGIN = int(SCREEN_HEIGHT * 0.06)   # Space for opponent's score, hand, etc.
DIVIDER_HEIGHT = int(SCREEN_HEIGHT * 0.015) # Thin divider between player/opponent boards

# 3. Calculate the total height required for the 6-row game board
TOTAL_BOARD_HEIGHT = (6 * ROW_HEIGHT) + DIVIDER_HEIGHT

# 4. The player's hand area dynamically uses the remaining vertical space
# Ensure it's large enough to accommodate cards + UI elements (faction power, leader, buttons)
# Reserve minimum 25% of screen height for hand area, but at least 250px
min_hand_height = max(250, int(SCREEN_HEIGHT * 0.25))
calculated_hand_height = SCREEN_HEIGHT - TOTAL_BOARD_HEIGHT - TOP_UI_MARGIN
HAND_Y_OFFSET = max(min_hand_height, calculated_hand_height)

# 5. Define the Y positions for the top of each row sequentially
opponent_siege_y = TOP_UI_MARGIN
opponent_ranged_y = opponent_siege_y + ROW_HEIGHT
opponent_close_y = opponent_ranged_y + ROW_HEIGHT

# Player rows start after the opponent's rows and the central divider
player_close_y = opponent_close_y + ROW_HEIGHT + DIVIDER_HEIGHT
player_ranged_y = player_close_y + ROW_HEIGHT
player_siege_y = player_ranged_y + ROW_HEIGHT

# The height is now ROW_HEIGHT, so the highlight box fills the entire lane
PLAYER_ROW_RECTS = {
    "close": pygame.Rect(0, player_close_y, SCREEN_WIDTH, ROW_HEIGHT),
    "ranged": pygame.Rect(0, player_ranged_y, SCREEN_WIDTH, ROW_HEIGHT),
    "siege": pygame.Rect(0, player_siege_y, SCREEN_WIDTH, ROW_HEIGHT),
}

OPPONENT_ROW_RECTS = {
    "close": pygame.Rect(0, opponent_close_y, SCREEN_WIDTH, ROW_HEIGHT),
    "ranged": pygame.Rect(0, opponent_ranged_y, SCREEN_WIDTH, ROW_HEIGHT),
    "siege": pygame.Rect(0, opponent_siege_y, SCREEN_WIDTH, ROW_HEIGHT),
}

ROW_CARD_OFFSET = (ROW_HEIGHT - CARD_HEIGHT) // 2

WEATHER_SLOT_X = int(SCREEN_WIDTH * 0.035)
HORN_SLOT_X = WEATHER_SLOT_X + CARD_WIDTH + int(CARD_WIDTH * 0.4)

WEATHER_SLOT_RECTS = {}
for shared_row in ["siege", "ranged", "close"]:
    top_rect = OPPONENT_ROW_RECTS[shared_row]
    bottom_rect = PLAYER_ROW_RECTS[shared_row]
    shared_center = (top_rect.centery + bottom_rect.centery) // 2
    WEATHER_SLOT_RECTS[shared_row] = pygame.Rect(
        WEATHER_SLOT_X,
        shared_center - CARD_HEIGHT // 2,
        CARD_WIDTH,
        CARD_HEIGHT
    )

PLAYER_HORN_SLOT_RECTS = {}
for row_name, row_rect in PLAYER_ROW_RECTS.items():
    PLAYER_HORN_SLOT_RECTS[row_name] = pygame.Rect(
        HORN_SLOT_X,
        row_rect.top + ROW_CARD_OFFSET,
        CARD_WIDTH,
        CARD_HEIGHT
    )

OPPONENT_HORN_SLOT_RECTS = {}
for row_name, row_rect in OPPONENT_ROW_RECTS.items():
    OPPONENT_HORN_SLOT_RECTS[row_name] = pygame.Rect(
        HORN_SLOT_X,
        row_rect.top + ROW_CARD_OFFSET,
        CARD_WIDTH,
        CARD_HEIGHT
    )

ROW_SYMBOLS = {
    "close": "⚔",      # Swords for close combat
    "ranged": "🏹",    # Bow for ranged
    "siege": "🎯",     # Target for siege
    "agile": "↕",      # Up-down for agile
    "special": "★",    # Star for special
    "weather": "☁",    # Cloud for weather
}

ROW_COLORS = {
    "close": (255, 100, 100),    # Red
    "ranged": (100, 100, 255),   # Blue
    "siege": (100, 255, 100),    # Green
    "agile": (255, 255, 100),    # Yellow
    "special": (255, 215, 0),    # Gold
    "weather": (150, 150, 255),  # Light blue
}


def get_row_color(row_name):
    """Return the theme color for a given row type."""
    return ROW_COLORS.get(row_name, (200, 200, 255))


def get_row_under_position(pos):
    """Return (row_name, rect) under the given screen position."""
    for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
        for row_name, row_rect in rects.items():
            if row_rect.collidepoint(pos):
                return row_name, row_rect
    return None, None


def get_weather_target_rows(card, hovered_row=None):
    """Determine which shared row(s) a weather card will affect."""
    ability = (card.ability or "").lower()
    if "ice planet hazard" in ability:
        return ["close"]
    if "nebula interference" in ability:
        return ["ranged"]
    if "asteroid storm" in ability:
        return ["siege"]
    if "electromagnetic pulse" in ability and hovered_row in ["close", "ranged", "siege"]:
        return [hovered_row]
    return []


def _draw_card_details(target_surface, card, rect):
    """Render card overlays (power pips and row icon)."""
    if card.row not in ["special", "weather"]:
        power_text = POWER_FONT.render(str(card.displayed_power), True, WHITE)
        power_rect = power_text.get_rect(
            center=(rect.x + rect.width / 2, rect.y + rect.height - 20)
        )
        pygame.draw.rect(
            target_surface,
            (0, 0, 0, 150),
            power_rect.inflate(4, 4)
        )
        target_surface.blit(power_text, power_rect)

    symbol = ROW_SYMBOLS.get(card.row, "?")
    color = get_row_color(card.row)
    symbol_x = rect.x + rect.width - 15
    symbol_y = rect.y + 15
    pygame.draw.circle(target_surface, (0, 0, 0, 180), (symbol_x, symbol_y), 12)
    pygame.draw.circle(
        target_surface,
        color,
        (symbol_x, symbol_y),
        12,
        width=2
    )
    symbol_text = ROW_FONT.render(symbol, True, color)
    symbol_rect = symbol_text.get_rect(center=(symbol_x, symbol_y))
    target_surface.blit(symbol_text, symbol_rect)


def _draw_drag_trail(surface, trail_entries):
    """Draw motion silhouettes that follow the dragged card."""
    if not trail_entries:
        return

    for blob in trail_entries:
        alpha = int(blob.get("alpha", 0))
        if alpha <= 0:
            continue

        width_scale = blob.get("width_scale", 1.0)
        height_scale = blob.get("height_scale", 1.0)
        width = max(4, int(CARD_WIDTH * width_scale))
        height = max(4, int(CARD_HEIGHT * height_scale))
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


def draw_card(surface, card, x, y, selected=False, hover_scale=1.0, tilt_angle=0.0,
              alpha=255, render_details=True, update_rect=True):
    """Draws a single card with optional scaling, tilt, and alpha adjustments."""
    if hover_scale != 1.0:
        scaled_width = int(CARD_WIDTH * hover_scale)
        scaled_height = int(CARD_HEIGHT * hover_scale)
        scaled_x = x - (scaled_width - CARD_WIDTH) // 2
        scaled_y = y - (scaled_height - CARD_HEIGHT) // 2
    else:
        scaled_width = CARD_WIDTH
        scaled_height = CARD_HEIGHT
        scaled_x = x
        scaled_y = y

    draw_rect = pygame.Rect(scaled_x, scaled_y, scaled_width, scaled_height)
    if update_rect:
        card.rect = draw_rect.copy()

    scaled_image = pygame.transform.smoothscale(card.image, (scaled_width, scaled_height))

    # Shadow for depth
    if hover_scale > 1.0 or selected:
        shadow_offset = 6 if selected else 4
        shadow_padding = shadow_offset * 2
        shadow_surf = pygame.Surface(
            (draw_rect.width + shadow_padding, draw_rect.height + shadow_padding),
            pygame.SRCALPHA
        )
        shadow_alpha = 120 if hover_scale > 1.0 else 80
        pygame.draw.rect(
            shadow_surf,
            (0, 0, 0, shadow_alpha),
            shadow_surf.get_rect(),
            border_radius=8
        )
        surface.blit(shadow_surf, (draw_rect.x + shadow_offset, draw_rect.y + shadow_offset))

    needs_rotation = abs(tilt_angle) > 0.05 or alpha != 255
    target_rect = draw_rect

    if needs_rotation:
        temp_surface = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
        temp_surface.blit(scaled_image, (0, 0))
        if render_details:
            detail_rect = pygame.Rect(0, 0, draw_rect.width, draw_rect.height)
            _draw_card_details(temp_surface, card, detail_rect)
        rotated_surface = pygame.transform.rotozoom(temp_surface, tilt_angle, 1.0)
        if alpha != 255:
            rotated_surface.set_alpha(alpha)
        target_rect = rotated_surface.get_rect(center=draw_rect.center)
        surface.blit(rotated_surface, target_rect)
    else:
        surface.blit(scaled_image, draw_rect)
        if render_details:
            _draw_card_details(surface, card, draw_rect)

    if selected:
        pygame.draw.rect(surface, (255, 255, 0), target_rect, width=3, border_radius=5)

def draw_hand(surface, player, selected_card, mulligan_selected=None, dragging_card=None,
              hovered_card=None, hover_scale=1.0, drag_visuals=None):
    """Draw the player's hand plus optional drag animations."""
    hand_bg_surface = pygame.Surface((SCREEN_WIDTH, HAND_Y_OFFSET), pygame.SRCALPHA)
    hand_bg_surface.fill(PLAYER_HAND_BG)
    surface.blit(hand_bg_surface, (0, SCREEN_HEIGHT - HAND_Y_OFFSET))

    if drag_visuals and drag_visuals.get("trail"):
        _draw_drag_trail(surface, drag_visuals.get("trail"))

    # Calculate spacing to center hand
    total_cards = len(player.hand)
    card_spacing = int(CARD_WIDTH * 0.125)  # Spacing between cards
    total_width = total_cards * CARD_WIDTH + (total_cards - 1) * card_spacing
    start_x = (SCREEN_WIDTH - total_width) // 2 if total_width < SCREEN_WIDTH else 20
    
    # Calculate vertical centering - ensure cards aren't cut off at bottom
    hand_area_top = SCREEN_HEIGHT - HAND_Y_OFFSET
    # Center cards vertically in the hand area, but if they're too tall, align to top with small margin
    if CARD_HEIGHT < HAND_Y_OFFSET - 20:  # Cards fit with margin
        card_y = hand_area_top + (HAND_Y_OFFSET - CARD_HEIGHT) // 2
    else:  # Cards are tall, use top alignment with small margin
        card_y = hand_area_top + 10
    
    for i, card in enumerate(player.hand):
        # Skip rendering dragging card in hand (it's rendered separately)
        if card == dragging_card:
            continue
            
        card_x = start_x + i * (CARD_WIDTH + card_spacing)
        is_selected = (card == selected_card)
        is_mulligan_selected = (mulligan_selected and card in mulligan_selected)
        is_hovered = (card == hovered_card)
        
        # Apply hover scale to hovered card
        card_scale = hover_scale if is_hovered else 1.0
        draw_card(surface, card, card_x, card_y, selected=is_selected, hover_scale=card_scale)
        
        # Draw blue border for mulligan selection
        if is_mulligan_selected:
            pygame.draw.rect(surface, (100, 100, 255), card.rect, width=4, border_radius=5)
        
        # Special/Weather cards - show "CLICK AGAIN TO PLAY" if selected
        if is_selected and card.row in ["special", "weather"]:
            hint_font = pygame.font.SysFont("Arial", 16, bold=True)
            hint_text = hint_font.render("CLICK AGAIN TO PLAY", True, (255, 255, 0))
            hint_rect = hint_text.get_rect(center=(card.rect.centerx, card.rect.top - 15))
            # Black background for readability
            bg_rect = hint_rect.inflate(10, 4)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect)
            surface.blit(hint_text, hint_rect)
    
    # Draw dragging card with juicy effects
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

        glow_size = (int(CARD_WIDTH * 1.2), int(CARD_HEIGHT * 0.8))
        shadow_surface = pygame.Surface((glow_size[0], int(glow_size[1])), pygame.SRCALPHA)
        shadow_alpha = min(210, 80 + speed * 10)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, shadow_alpha), shadow_surface.get_rect())
        shadow_pos = (
            int(dragging_card.rect.centerx - shadow_surface.get_width() // 2 + velocity.x * 0.8),
            int(dragging_card.rect.centery - shadow_surface.get_height() // 2 + 45 + abs(velocity.y) * 0.2)
        )
        surface.blit(shadow_surface, shadow_pos)

        if pickup_boost > 0.01:
            flash_surface = pygame.Surface((CARD_WIDTH + 40, CARD_HEIGHT + 40), pygame.SRCALPHA)
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
            update_rect=False
        )

def draw_opponent_hand(surface, opponent):
    """Draws the opponent's hand as card backs at the top of the screen."""
    from cards import get_card_back
    
    # Opponent hand area at top
    hand_y = 10
    total_cards = len(opponent.hand)
    
    if total_cards == 0:
        return
    
    card_spacing = int(CARD_WIDTH * 0.125)
    total_width = total_cards * CARD_WIDTH + (total_cards - 1) * card_spacing
    start_x = (SCREEN_WIDTH - total_width) // 2 if total_width < SCREEN_WIDTH else 20
    
    # Get card back image
    card_back_image = get_card_back(CARD_WIDTH, CARD_HEIGHT)
    
    for i, card in enumerate(opponent.hand):
        card_x = start_x + i * (CARD_WIDTH + card_spacing)
        if opponent.hand_revealed:
            draw_card(
                surface,
                card,
                card_x,
                hand_y,
                render_details=True,
                update_rect=False
            )
            pygame.draw.rect(surface, (255, 215, 0), 
                             (card_x, hand_y, CARD_WIDTH, CARD_HEIGHT), 
                             2, border_radius=8)
        else:
            surface.blit(card_back_image, (card_x, hand_y))
            pygame.draw.rect(surface, (100, 150, 200), 
                            (card_x, hand_y, CARD_WIDTH, CARD_HEIGHT), 
                            2, border_radius=8)


def draw_weather_slots(surface, game):
    """Render persistent weather card boxes on the left side."""
    for row_name, slot_rect in WEATHER_SLOT_RECTS.items():
        is_active = game.weather_active.get(row_name)
        slot_surface = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)
        fill_alpha = 210 if is_active else 150
        slot_surface.fill((25, 45, 70, fill_alpha))
        border_color = (120, 190, 255) if is_active else (80, 120, 170)
        pygame.draw.rect(slot_surface, border_color, slot_surface.get_rect(), width=3, border_radius=12)
        surface.blit(slot_surface, slot_rect.topleft)
        
        entry = game.weather_cards_on_board.get(row_name) if hasattr(game, "weather_cards_on_board") else None
        card = entry.get("card") if entry else None
        if card:
            draw_card(surface, card, slot_rect.x, slot_rect.y, render_details=False, update_rect=False)
        else:
            symbol = ROW_SYMBOLS.get(row_name, "?")
            symbol_text = ROW_FONT.render(symbol, True, border_color)
            symbol_rect = symbol_text.get_rect(center=slot_rect.center)
            surface.blit(symbol_text, symbol_rect)


def draw_horn_slots(surface, game):
    """Render Commander Horn drop slots for each row."""
    def render_slot(slot_rect, active, card, is_player_side):
        slot_surface = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)
        base_color = (60, 40, 20, 200) if is_player_side else (35, 45, 65, 190)
        glow_color = (255, 215, 0) if active else (150, 120, 80)
        slot_surface.fill(base_color)
        pygame.draw.rect(slot_surface, glow_color, slot_surface.get_rect(), width=3 if active else 2, border_radius=12)
        surface.blit(slot_surface, slot_rect.topleft)
        if card:
            draw_card(surface, card, slot_rect.x, slot_rect.y, render_details=False, update_rect=False)
        else:
            horn_text = ROW_FONT.render("H", True, glow_color)
            horn_rect = horn_text.get_rect(center=slot_rect.center)
            surface.blit(horn_text, horn_rect)
    
    if hasattr(game.player1, "horn_slots"):
        for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
            render_slot(slot_rect,
                        game.player1.horn_effects.get(row_name, False),
                        game.player1.horn_slots.get(row_name),
                        True)
    if hasattr(game.player2, "horn_slots"):
        for row_name, slot_rect in OPPONENT_HORN_SLOT_RECTS.items():
            render_slot(slot_rect,
                        game.player2.horn_effects.get(row_name, False),
                        game.player2.horn_slots.get(row_name),
                        False)

def get_opponent_hand_card_center(total_cards, index):
    """Return the screen center position of an opponent hand slot by index."""
    hand_y = 10
    if total_cards <= 0:
        return (SCREEN_WIDTH // 2, hand_y + CARD_HEIGHT // 2)
    card_spacing = int(CARD_WIDTH * 0.125)
    total_width = total_cards * CARD_WIDTH + (total_cards - 1) * card_spacing
    start_x = (SCREEN_WIDTH - total_width) // 2 if total_width < SCREEN_WIDTH else 20
    safe_index = max(0, min(index if index is not None else 0, total_cards - 1))
    card_x = start_x + safe_index * (CARD_WIDTH + card_spacing)
    return (card_x + CARD_WIDTH // 2, hand_y + CARD_HEIGHT // 2)

def draw_board(surface, game, selected_card, dragging_card=None, drag_hover_highlight=None,
               drag_row_highlights=None):
    """Draw the game board, including contextual drop highlights."""
    draw_weather_slots(surface, game)
    draw_horn_slots(surface, game)
    # Highlight valid target rows with semi-transparent fill and border
    if selected_card and selected_card.row not in ["special", "weather"]:
        valid_rows = []
        is_spy = "Deep Cover Agent" in (selected_card.ability or "")
        
        target_rects = OPPONENT_ROW_RECTS if is_spy else PLAYER_ROW_RECTS
        highlight_color = (255, 100, 100) if is_spy else (100, 255, 100)
        fill_color = (255, 100, 100, 40) if is_spy else (100, 255, 100, 40)  # Semi-transparent fill

        if selected_card.row == "agile":
            valid_rows = ["close", "ranged"]
        elif selected_card.row in ["close", "ranged", "siege"]:
            valid_rows = [selected_card.row]

        for r_name in valid_rows:
            if r_name in target_rects:
                # Draw semi-transparent fill
                highlight_surface = pygame.Surface((target_rects[r_name].width, target_rects[r_name].height), pygame.SRCALPHA)
                highlight_surface.fill(fill_color)
                surface.blit(highlight_surface, (target_rects[r_name].x, target_rects[r_name].y))
    
    # Highlight general special targets (non-horn placement)
    if dragging_card and dragging_card.row == "special":
        ability_text = dragging_card.ability or ""
        if "Command Network" not in ability_text:
            fill_color = (255, 255, 255, 30)
            for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                for rect in rects.values():
                    highlight_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    highlight_surface.fill(fill_color)
                    surface.blit(highlight_surface, rect.topleft)

    if drag_row_highlights:
        for highlight in drag_row_highlights:
            rect = highlight["rect"]
            color = highlight.get("color", (255, 255, 255))
            alpha = highlight.get("alpha", 80)
            highlight_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            highlight_surface.fill((color[0], color[1], color[2], alpha))
            surface.blit(highlight_surface, rect.topleft)
            pygame.draw.rect(surface, color, rect, width=3, border_radius=12)

    if drag_hover_highlight:
        rect = drag_hover_highlight["rect"]
        color = drag_hover_highlight["color"]
        alpha = drag_hover_highlight.get("alpha", 80)
        hover_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        hover_surface.fill((color[0], color[1], color[2], alpha))
        surface.blit(hover_surface, rect.topleft)
        pygame.draw.rect(surface, color, rect, width=4, border_radius=12)

    # --- Draw cards on board (centered in their rows) ---
    row_map = {
        game.player2: OPPONENT_ROW_RECTS,
        game.player1: PLAYER_ROW_RECTS,
    }

    # This offset will center the TALLER cards within their SHORTER row space
    card_y_offset = (ROW_HEIGHT - CARD_HEIGHT) // 2

    card_spacing = int(CARD_WIDTH * 0.125)  # Spacing between cards on board
    for player, rects in row_map.items():
        for row_name, row_rect in rects.items():
            cards_in_row = player.board[row_name]
            if not cards_in_row:
                continue
            
            # Calculate total width and center cards
            total_width = len(cards_in_row) * CARD_WIDTH + (len(cards_in_row) - 1) * card_spacing
            start_x = (SCREEN_WIDTH - total_width) // 2
            
            for i, card in enumerate(cards_in_row):
                x = start_x + i * (CARD_WIDTH + card_spacing)

                # Use the offset to center the card vertically in its lane
                card_draw_y = row_rect.top + card_y_offset
                card.rect.topleft = (x, card_draw_y)
                if getattr(card, "in_transit", False):
                    continue
                draw_card(surface, card, x, card_draw_y)
    
def draw_scores(surface, game, anim_manager=None):
    """Draws the player scores and rounds won next to leader portraits."""
    
    # Leader portraits are at:
    # AI: x=20, y=20, width=100, height=140
    # Player: x=20, y=SCREEN_HEIGHT - HAND_Y_OFFSET + 20, width=100, height=140
    
    # Position scores next to leader portraits (to the right)
    score_x_offset = 130  # Right after the 100px wide leader portrait + 30px margin
    
    # Player 2 (AI/Opponent) - Top
    p2_score_x = 20 + score_x_offset
    p2_score_y = 40
    
    # Player 1 (Human) - Bottom
    p1_score_x = 20 + score_x_offset
    p1_score_y = SCREEN_HEIGHT - HAND_Y_OFFSET + 40
    
    # If we have active score animations, draw them instead
    if anim_manager and anim_manager.score_animations:
        anim_manager.draw_score_animations(surface, SCORE_FONT)
    else:
        # Player 1 Total Score (next to leader, bottom)
        p1_color = (100, 255, 100) if game.player1.score > game.player2.score else WHITE
        p1_score_text = SCORE_FONT.render(f"Score: {game.player1.score}", True, p1_color)
        surface.blit(p1_score_text, (p1_score_x, p1_score_y))
        
        # Player 2 Total Score (next to leader, top)
        p2_color = (100, 255, 100) if game.player2.score > game.player1.score else WHITE
        p2_score_text = SCORE_FONT.render(f"Score: {game.player2.score}", True, p2_color)
        surface.blit(p2_score_text, (p2_score_x, p2_score_y))

    # Rounds Won (below scores, next to leaders)
    p1_rounds_text = UI_FONT.render(f"Rounds Won: {game.player1.rounds_won}", True, WHITE)
    p2_rounds_text = UI_FONT.render(f"Rounds Won: {game.player2.rounds_won}", True, WHITE)
    surface.blit(p1_rounds_text, (p1_score_x, p1_score_y + 55))
    surface.blit(p2_rounds_text, (p2_score_x, p2_score_y + 55))
    
    # Row Scores (still show for reference, but more compact)
    # Player row scores at bottom-center
    row_score_y = SCREEN_HEIGHT - 50
    center_x = SCREEN_WIDTH // 2
    
    # Calculate row totals
    p1_siege_total = sum(c.displayed_power for c in game.player1.board.get("siege", []))
    p1_ranged_total = sum(c.displayed_power for c in game.player1.board.get("ranged", []))
    p1_close_total = sum(c.displayed_power for c in game.player1.board.get("close", []))
    
    # Draw row score boxes (small, compact)
    row_font = pygame.font.SysFont("Arial", 20, bold=True)
    
    # Siege
    siege_x = center_x - 150
    siege_text = row_font.render(f"🎯: {p1_siege_total}", True, (100, 255, 100))
    surface.blit(siege_text, (siege_x, row_score_y))
    
    # Ranged
    ranged_x = center_x - 50
    ranged_text = row_font.render(f"🏹: {p1_ranged_total}", True, (100, 100, 255))
    surface.blit(ranged_text, (ranged_x, row_score_y))
    
    # Close
    close_x = center_x + 50
    close_text = row_font.render(f"⚔: {p1_close_total}", True, (255, 100, 100))
    surface.blit(close_text, (close_x, row_score_y))

def draw_pass_button(surface, game):
    """Draws the DHD-style pass button."""
    center_x = PASS_BUTTON_RECT.centerx
    center_y = PASS_BUTTON_RECT.centery
    
    # Base state
    can_pass = game.current_player == game.player1 and not game.player1.has_passed
    
    # Outer DHD ring (scaled)
    outer_radius = int(50 * SCALE_FACTOR)
    inner_radius = int(35 * SCALE_FACTOR)
    
    # Outer ring color (bronze/metallic)
    outer_color = (120, 100, 80)
    pygame.draw.circle(surface, outer_color, (center_x, center_y), outer_radius)
    pygame.draw.circle(surface, (80, 70, 60), (center_x, center_y), outer_radius, width=max(1, int(3 * SCALE_FACTOR)))
    
    # DHD symbols around the ring (simplified chevrons) - scaled
    num_symbols = 7
    for i in range(num_symbols):
        angle = (i * 360 / num_symbols) - 90  # Start from top
        rad = math.radians(angle)
        symbol_x = center_x + math.cos(rad) * (42 * SCALE_FACTOR)
        symbol_y = center_y + math.sin(rad) * (42 * SCALE_FACTOR)
        
        # Small chevron-like triangle
        symbol_color = (150, 130, 100) if can_pass else (80, 70, 60)
        symbol_size = max(2, int(5 * SCALE_FACTOR))
        pygame.draw.circle(surface, symbol_color, (int(symbol_x), int(symbol_y)), symbol_size)
    
    # Center button (home/dial button)
    if can_pass:
        # Glowing red when active
        glow_time = pygame.time.get_ticks() / 500.0
        glow_pulse = abs(math.sin(glow_time))
        center_alpha = int(150 + glow_pulse * 105)
        
        # Outer glow
        glow_surf = pygame.Surface((inner_radius * 3, inner_radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 50, 50, 80), (inner_radius * 1.5, inner_radius * 1.5), inner_radius + int(10 * SCALE_FACTOR))
        surface.blit(glow_surf, (center_x - inner_radius * 1.5, center_y - inner_radius * 1.5))
        
        # Main button - glowing red
        pygame.draw.circle(surface, (200, 40, 40), (center_x, center_y), inner_radius)
        pygame.draw.circle(surface, (255, 100, 100), (center_x, center_y), max(1, inner_radius - int(5 * SCALE_FACTOR)))
        pygame.draw.circle(surface, (255, 50, 50, center_alpha), (center_x, center_y), max(1, inner_radius - int(10 * SCALE_FACTOR)))
        
        # Center dot (button press point)
        pygame.draw.circle(surface, (255, 200, 200), (center_x, center_y), max(2, int(8 * SCALE_FACTOR)))
        pygame.draw.circle(surface, (255, 255, 255, 200), (center_x, center_y), max(1, int(4 * SCALE_FACTOR)))
    else:
        # Inactive - dark gray
        pygame.draw.circle(surface, (60, 60, 70), (center_x, center_y), inner_radius)
        pygame.draw.circle(surface, (80, 80, 90), (center_x, center_y), max(1, inner_radius - int(5 * SCALE_FACTOR)))
        pygame.draw.circle(surface, (50, 50, 60), (center_x, center_y), max(1, inner_radius - int(10 * SCALE_FACTOR)))
        pygame.draw.circle(surface, (70, 70, 80), (center_x, center_y), max(2, int(8 * SCALE_FACTOR)))
    
    # "PASS" text below DHD
    text_color = (255, 200, 200) if can_pass else (120, 120, 120)
    pass_text = UI_FONT.render("PASS", True, text_color)
    text_rect = pass_text.get_rect(center=(center_x, center_y + outer_radius + int(20 * SCALE_FACTOR)))
    
    # Add shadow
    if can_pass:
        shadow = UI_FONT.render("PASS", True, (0, 0, 0, 100))
        surface.blit(shadow, (text_rect.x + int(2 * SCALE_FACTOR), text_rect.y + int(2 * SCALE_FACTOR)))
    
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
    
    pygame.draw.rect(surface, color, MULLIGAN_BUTTON_RECT, border_radius=5)
    text = f"Redraw ({num_selected}/2-5)"
    mulligan_text = UI_FONT.render(text, True, WHITE)
    text_rect = mulligan_text.get_rect(center=MULLIGAN_BUTTON_RECT.center)
    surface.blit(mulligan_text, text_rect)

def draw_zpm_resource(surface, player, x, y):
    """Draw ZPM resource indicators."""
    zpm_spacing = int(SCREEN_WIDTH * 0.018)  # ~35px spacing
    zpm_height = int(SCREEN_HEIGHT * 0.028)  # ~30px height
    
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
        pygame.draw.polygon(surface, WHITE, [
            (zpm_x + 15, y),
            (zpm_x + 25, y + 10),
            (zpm_x + 20, y + zpm_height),
            (zpm_x + 10, y + zpm_height),
            (zpm_x + 5, y + 10),
        ], width=2)

def draw_mission_objective(surface, player, x, y):
    """Draw current mission objective."""
    if player.current_mission and not player.current_mission.completed:
        mission_text = UI_FONT.render("Mission:", True, (255, 255, 100))
        surface.blit(mission_text, (x, y))
        
        desc_text = UI_FONT.render(player.current_mission.description, True, WHITE)
        surface.blit(desc_text, (x, y + 20))
        
        reward_text = UI_FONT.render(f"Reward: {player.current_mission.reward_desc}", True, (100, 255, 100))
        surface.blit(reward_text, (x, y + 40))
    elif player.current_mission and player.current_mission.completed:
        completed_text = UI_FONT.render("Mission Completed!", True, (100, 255, 100))
        surface.blit(completed_text, (x, y))

def show_round_winner_announcement(screen, game, screen_width, screen_height):
    """Show cinematic announcement of who won the round with detailed scoreboard."""
    # Get the round that just completed
    completed_round = game.round_number - 1
    
    # Determine winner text
    if game.round_winner == game.player1:
        winner_text = f"YOU WIN ROUND {completed_round}!"
        winner_color = (100, 255, 100)
    elif game.round_winner == game.player2:
        winner_text = f"OPPONENT WINS ROUND {completed_round}!"
        winner_color = (255, 100, 100)
    else:
        winner_text = f"ROUND {completed_round} DRAW!"
        winner_color = (255, 255, 100)
    
    # Get round history (who won each round so far)
    # We need to track this - for now infer from rounds_won
    round_results = []  # Will store who won each round
    
    # Reconstruct round results from current state
    # This is a simplified version - ideally game.py should track round_history
    p1_rounds = game.player1.rounds_won
    p2_rounds = game.player2.rounds_won
    total_rounds_played = completed_round
    
    # Build round results (this is an approximation)
    for i in range(total_rounds_played):
        if i == completed_round - 1:  # Current round just completed
            if game.round_winner == game.player1:
                round_results.append("p1")
            elif game.round_winner == game.player2:
                round_results.append("p2")
            else:
                round_results.append("draw")
        else:
            # For previous rounds, we have to guess based on total wins
            # This is imperfect but works for display
            round_results.append("unknown")
    
    # Fonts
    title_font = pygame.font.SysFont("Arial", 72, bold=True)
    score_font = pygame.font.SysFont("Arial", 48, bold=True)
    round_font = pygame.font.SysFont("Arial", 36, bold=True)
    label_font = pygame.font.SysFont("Arial", 32)
    
    clock = pygame.time.Clock()
    duration = 3000  # 3 seconds
    start_time = pygame.time.get_ticks()
    
    while pygame.time.get_ticks() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    return  # Skip animation
        
        elapsed = pygame.time.get_ticks() - start_time
        progress = elapsed / duration
        
        # Dark overlay
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        screen.blit(overlay, (0, 0))
        
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Main winner text - slide in from top
        text_alpha = min(255, int(255 * progress * 2))
        text_y_offset = int((1 - min(1, progress * 1.5)) * -100)
        
        winner_surface = title_font.render(winner_text, True, winner_color)
        winner_surface.set_alpha(text_alpha)
        winner_rect = winner_surface.get_rect(center=(center_x, 120 + text_y_offset))
        screen.blit(winner_surface, winner_rect)
        
        # Scoreboard - fade in after title
        if progress > 0.3:
            board_alpha = min(255, int(255 * (progress - 0.3) * 2.5))
            
            # Scoreboard box
            board_width = 700
            board_height = 350
            board_x = center_x - board_width // 2
            board_y = center_y - 50
            
            board_surf = pygame.Surface((board_width, board_height), pygame.SRCALPHA)
            board_surf.fill((20, 30, 50, 240))
            pygame.draw.rect(board_surf, (255, 215, 0), board_surf.get_rect(), width=4, border_radius=15)
            board_surf.set_alpha(board_alpha)
            screen.blit(board_surf, (board_x, board_y))
            
            # Draw scoreboard content
            y_offset = board_y + 30
            
            # Title
            scoreboard_title = label_font.render("SCOREBOARD", True, (255, 215, 0))
            scoreboard_title.set_alpha(board_alpha)
            title_rect = scoreboard_title.get_rect(center=(center_x, y_offset))
            screen.blit(scoreboard_title, title_rect)
            
            y_offset += 60
            
            # Column headers
            col_header_font = pygame.font.SysFont("Arial", 28, bold=True)
            player_label = col_header_font.render("PLAYER", True, (200, 200, 200))
            round1_label = col_header_font.render("R1", True, (200, 200, 200))
            round2_label = col_header_font.render("R2", True, (200, 200, 200))
            round3_label = col_header_font.render("R3", True, (200, 200, 200))
            total_label = col_header_font.render("TOTAL", True, (200, 200, 200))
            
            player_label.set_alpha(board_alpha)
            round1_label.set_alpha(board_alpha)
            round2_label.set_alpha(board_alpha)
            round3_label.set_alpha(board_alpha)
            total_label.set_alpha(board_alpha)
            
            screen.blit(player_label, (board_x + 50, y_offset))
            screen.blit(round1_label, (board_x + 280, y_offset))
            screen.blit(round2_label, (board_x + 380, y_offset))
            screen.blit(round3_label, (board_x + 480, y_offset))
            screen.blit(total_label, (board_x + 580, y_offset))
            
            y_offset += 50
            
            # Draw separator line
            line_surf = pygame.Surface((board_width - 40, 3), pygame.SRCALPHA)
            line_surf.fill((255, 215, 0, board_alpha))
            screen.blit(line_surf, (board_x + 20, y_offset))
            
            y_offset += 20
            
            # Player 1 row
            p1_name = score_font.render("YOU", True, (100, 255, 100))
            p1_name.set_alpha(board_alpha)
            screen.blit(p1_name, (board_x + 50, y_offset))
            
            # Round scores for Player 1
            for round_num in range(1, 4):
                round_x = board_x + 280 + (round_num - 1) * 100
                
                if round_num <= completed_round:
                    # Check if player won this round
                    won_round = False
                    if round_num == completed_round and game.round_winner == game.player1:
                        won_round = True
                    elif round_num < completed_round:
                        # For previous rounds, check if they contributed to rounds_won
                        # This is approximate - ideally we'd track full history
                        won_round = (round_num <= p1_rounds)
                    
                    if won_round:
                        round_color = (100, 150, 255)  # Blue for won round
                        round_score = score_font.render("1", True, round_color)
                    else:
                        round_color = (150, 150, 150)  # Light grey for lost/draw
                        round_score = score_font.render("0", True, round_color)
                else:
                    # Future round
                    round_color = (80, 80, 80)
                    round_score = score_font.render("-", True, round_color)
                
                round_score.set_alpha(board_alpha)
                score_rect = round_score.get_rect(center=(round_x + 20, y_offset + 25))
                screen.blit(round_score, score_rect)
            
            # Total for Player 1
            p1_total = score_font.render(str(game.player1.rounds_won), True, (255, 215, 0))
            p1_total.set_alpha(board_alpha)
            total_rect = p1_total.get_rect(center=(board_x + 600, y_offset + 25))
            screen.blit(p1_total, total_rect)
            
            y_offset += 70
            
            # Player 2 row
            p2_name = score_font.render("OPP", True, (255, 100, 100))
            p2_name.set_alpha(board_alpha)
            screen.blit(p2_name, (board_x + 50, y_offset))
            
            # Round scores for Player 2
            for round_num in range(1, 4):
                round_x = board_x + 280 + (round_num - 1) * 100
                
                if round_num <= completed_round:
                    won_round = False
                    if round_num == completed_round and game.round_winner == game.player2:
                        won_round = True
                    elif round_num < completed_round:
                        won_round = (round_num <= p2_rounds)
                    
                    if won_round:
                        round_color = (100, 150, 255)  # Blue for won round
                        round_score = score_font.render("1", True, round_color)
                    else:
                        round_color = (150, 150, 150)  # Light grey for lost/draw
                        round_score = score_font.render("0", True, round_color)
                else:
                    round_color = (80, 80, 80)
                    round_score = score_font.render("-", True, round_color)
                
                round_score.set_alpha(board_alpha)
                score_rect = round_score.get_rect(center=(round_x + 20, y_offset + 25))
                screen.blit(round_score, score_rect)
            
            # Total for Player 2
            p2_total = score_font.render(str(game.player2.rounds_won), True, (255, 215, 0))
            p2_total.set_alpha(board_alpha)
            total_rect = p2_total.get_rect(center=(board_x + 600, y_offset + 25))
            screen.blit(p2_total, total_rect)
        
        # Skip instruction
        if progress > 0.4:
            skip_font = pygame.font.SysFont("Arial", 28)
            skip_text = skip_font.render("Press SPACE to continue", True, (180, 180, 180))
            skip_text.set_alpha(text_alpha)
            skip_rect = skip_text.get_rect(center=(center_x, screen_height - 80))
            screen.blit(skip_text, skip_rect)
        
        pygame.display.flip()
        clock.tick(60)

def show_game_start_animation(screen, game, screen_width, screen_height):
    """Show Stargate activation animation announcing who goes first."""
    # Determine who goes first
    if game.current_player == game.player1:
        first_player_text = "YOU GO FIRST"
        color = (100, 255, 100)
    else:
        first_player_text = "OPPONENT GOES FIRST"
        color = (255, 100, 100)
    
    # Font
    title_font = pygame.font.SysFont("Arial", 72, bold=True)
    subtitle_font = pygame.font.SysFont("Arial", 36)
    
    clock = pygame.time.Clock()
    
    # Animation phases
    duration = 2500  # 2.5 seconds
    start_time = pygame.time.get_ticks()
    
    while pygame.time.get_ticks() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    return  # Skip animation
        
        elapsed = pygame.time.get_ticks() - start_time
        progress = elapsed / duration
        
        # Dark semi-transparent overlay
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        
        # Pulsing circle effect (Stargate-like)
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Multiple expanding circles
        for i in range(3):
            phase_offset = i * 0.3
            circle_progress = (progress + phase_offset) % 1.0
            radius = int(50 + circle_progress * 200)
            alpha = int(255 * (1 - circle_progress))
            
            if alpha > 0:
                circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(circle_surface, (100, 150, 255, alpha), (radius, radius), radius, width=3)
                screen.blit(circle_surface, (center_x - radius, center_y - radius))
        
        # Central glow
        glow_alpha = int(128 + 127 * abs(0.5 - progress))
        pygame.draw.circle(screen, (100, 150, 255), (center_x, center_y), 40)
        
        # Text fade in
        text_alpha = min(255, int(255 * progress * 2))
        
        # Main text
        text_surface = title_font.render(first_player_text, True, color)
        text_surface.set_alpha(text_alpha)
        text_rect = text_surface.get_rect(center=(center_x, center_y - 100))
        screen.blit(text_surface, text_rect)
        
        # Subtitle
        if progress > 0.3:
            subtitle = subtitle_font.render("Prepare your strategy...", True, (200, 200, 200))
            subtitle.set_alpha(text_alpha)
            subtitle_rect = subtitle.get_rect(center=(center_x, center_y + 100))
            screen.blit(subtitle, subtitle_rect)
        
        # Skip instruction
        if progress > 0.5:
            skip_font = pygame.font.SysFont("Arial", 20)
            skip_text = skip_font.render("Press SPACE to skip", True, (150, 150, 150))
            skip_text.set_alpha(text_alpha)
            skip_rect = skip_text.get_rect(center=(center_x, screen_height - 50))
            screen.blit(skip_text, skip_rect)
        
        pygame.display.flip()
        clock.tick(60)
    
    # Brief pause before game starts
    pygame.time.wait(300)

def draw_iris_button(surface, player, x, y):
    """Draw Iris defense button (Tau'ri only)."""
    if player.faction != "Tau'ri":
        return None
    
    button_width = 100
    button_height = 50
    button_rect = pygame.Rect(x, y, button_width, button_height)
    
    # Button color based on state
    if player.iris_defense.is_active():
        color = (255, 100, 100)  # Red - active/blocking
        text = "IRIS ON"
    elif player.iris_defense.is_available():
        color = (100, 200, 255)  # Blue - available
        text = "IRIS"
    else:
        color = (80, 80, 80)  # Gray - used
        text = "IRIS USED"
    
    # Draw button
    pygame.draw.rect(surface, color, button_rect, border_radius=5)
    pygame.draw.rect(surface, (255, 215, 0), button_rect, width=2, border_radius=5)
    
    # Text
    font = pygame.font.SysFont("Arial", 18, bold=True)
    button_text = font.render(text, True, (255, 255, 255))
    text_rect = button_text.get_rect(center=button_rect.center)
    surface.blit(button_text, text_rect)
    
    # Removed "(Press I)" hint text during gameplay for cleaner UI
    
    return button_rect

def draw_ring_transport_button(surface, player, x, y):
    """Draw Ring Transportation button (Goa'uld only)."""
    if player.faction != "Goa'uld" or not player.ring_transportation:
        return None
    
    button_width = 120
    button_height = 50
    button_rect = pygame.Rect(x, y, button_width, button_height)
    
    # Button color based on state
    if player.ring_transportation.animation_in_progress:
        color = (255, 200, 100)  # Gold - animating
        text = "RINGS..."
    elif player.ring_transportation.can_use():
        color = (200, 100, 50)  # Orange - available
        text = "RINGS"
    else:
        color = (80, 80, 80)  # Gray - used
        text = "USED"
    
    # Draw button with Goa'uld theme
    pygame.draw.rect(surface, color, button_rect, border_radius=5)
    pygame.draw.rect(surface, (255, 200, 100), button_rect, width=2, border_radius=5)
    
    # Draw three small ring symbols on button
    if player.ring_transportation.can_use() or player.ring_transportation.animation_in_progress:
        for i in range(3):
            ring_x = x + 20 + i * 30
            ring_y = y + button_height // 2
            pygame.draw.circle(surface, (255, 220, 150), (ring_x, ring_y), 8, width=2)
    
    # Text
    font = pygame.font.SysFont("Arial", 16, bold=True)
    button_text = font.render(text, True, (255, 255, 255))
    text_rect = button_text.get_rect(center=button_rect.center)
    surface.blit(button_text, text_rect)
    
    return button_rect

def draw_leader_ability_box(surface, player, x, y, width, height, is_opponent=False):
    """Draw clickable leader ability box with Stargate theme."""
    if not player.leader:
        return
    
    # Stargate-themed box (semi-transparent with border)
    box_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    box_surface.fill((20, 40, 60, 200))  # Dark blue-ish with transparency
    
    # Golden border (Stargate style)
    pygame.draw.rect(box_surface, (255, 215, 0), box_surface.get_rect(), width=3, border_radius=8)
    
    # Leader name
    name_font = pygame.font.SysFont("Arial", 22, bold=True)
    name_text = name_font.render(player.leader['name'], True, (255, 215, 0))
    name_rect = name_text.get_rect(center=(width // 2, 20))
    box_surface.blit(name_text, name_rect)
    
    # Ability description
    ability_font = pygame.font.SysFont("Arial", 18)
    ability_text = ability_font.render(player.leader['ability'], True, (200, 255, 200))
    ability_rect = ability_text.get_rect(center=(width // 2, height - 20))
    box_surface.blit(ability_text, ability_rect)
    
    # Blit to main surface
    surface.blit(box_surface, (x, y))
    
    return pygame.Rect(x, y, width, height)  # Return rect for click detection

def draw_card_counters(surface, player, x, y, is_player=True):
    """Draw deck/hand/discard pile counters on the right side."""
    small_font = pygame.font.SysFont("Arial", 20)

    panel_width = 170
    panel_height = 100
    panel_rect = pygame.Rect(x, y, panel_width, panel_height)
    pygame.draw.rect(surface, (15, 25, 45), panel_rect, border_radius=10)
    pygame.draw.rect(surface, (60, 90, 140), panel_rect, width=2, border_radius=10)

    hand_text = small_font.render(f"Hand: {len(player.hand)}", True, (255, 255, 255))
    deck_text = small_font.render(f"Draw: {len(player.deck)}", True, (255, 255, 255))
    discard_text = small_font.render(f"Discard: {len(player.discard_pile)}", True, (230, 255, 255))

    surface.blit(hand_text, (x + 12, y + 12))
    surface.blit(deck_text, (x + 12, y + 36))

    discard_rect = pygame.Rect(x + 10, y + 62, panel_width - 20, 26)
    pygame.draw.rect(surface, (30, 60, 100), discard_rect, border_radius=6)
    pygame.draw.rect(surface, (90, 130, 185), discard_rect, width=2, border_radius=6)
    surface.blit(discard_text, (discard_rect.x + 8, discard_rect.y + 4))

    return discard_rect if is_player else None

def draw_leader_portrait(surface, player, x, y, width=100, height=150):
    """Draw leader portrait card and return its rect for click detection."""
    if not player.leader:
        return None
    
    leader_rect = pygame.Rect(x, y, width, height)
    
    # Try to load leader portrait (separate from card image)
    leader_card_id = player.leader.get('card_id', None)
    if leader_card_id:
        leader_image_path = f"assets/{leader_card_id}_leader.png"
        import os
        try:
            if os.path.exists(leader_image_path):
                # Load leader-specific portrait
                leader_img = pygame.image.load(leader_image_path).convert_alpha()
                scaled_image = pygame.transform.scale(leader_img, (width, height))
                surface.blit(scaled_image, (x, y))
                pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
            elif leader_card_id in ALL_CARDS:
                # Fallback to regular card image
                leader_card = ALL_CARDS[leader_card_id]
                scaled_image = pygame.transform.scale(leader_card.image, (width, height))
                surface.blit(scaled_image, (x, y))
                pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
            else:
                # Final fallback
                pygame.draw.rect(surface, (60, 60, 80), leader_rect)
                pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
        except:
            # Final fallback
            pygame.draw.rect(surface, (60, 60, 80), leader_rect)
            pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
    else:
        # Fallback
        pygame.draw.rect(surface, (60, 60, 80), leader_rect)
        pygame.draw.rect(surface, (255, 215, 0), leader_rect, width=3)
    
    # Leader label below
    name_text = UI_FONT.render("LEADER", True, (255, 215, 0))
    name_rect = name_text.get_rect(center=(x + width // 2, y + height + 15))
    surface.blit(name_text, name_rect)
    
    return leader_rect

def draw_leader_inspection_overlay(surface, player, screen_width, screen_height):
    """Draw full-screen leader inspection overlay."""
    if not player.leader:
        return
    
    # Keep battlefield visible during leader inspection
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    surface.blit(overlay, (0, 0))
    
    # Large leader portrait display
    portrait_width = 400
    portrait_height = 600
    portrait_x = (screen_width - portrait_width) // 2
    portrait_y = 60
    
    # Try to load and display leader image
    leader_card_id = player.leader.get('card_id', None)
    if leader_card_id:
        leader_image_path = f"assets/{leader_card_id}_leader.png"
        import os
        try:
            if os.path.exists(leader_image_path):
                leader_img = pygame.image.load(leader_image_path).convert_alpha()
                scaled_image = pygame.transform.scale(leader_img, (portrait_width, portrait_height))
                surface.blit(scaled_image, (portrait_x, portrait_y))
            elif leader_card_id in ALL_CARDS:
                leader_card = ALL_CARDS[leader_card_id]
                scaled_image = pygame.transform.scale(leader_card.image, (portrait_width, portrait_height))
                surface.blit(scaled_image, (portrait_x, portrait_y))
            else:
                # Fallback rectangle
                pygame.draw.rect(surface, (60, 60, 80), pygame.Rect(portrait_x, portrait_y, portrait_width, portrait_height))
        except:
            # Fallback rectangle
            pygame.draw.rect(surface, (60, 60, 80), pygame.Rect(portrait_x, portrait_y, portrait_width, portrait_height))
    
    # Golden border
    pygame.draw.rect(surface, (255, 215, 0), pygame.Rect(portrait_x, portrait_y, portrait_width, portrait_height), width=5)
    
    # Leader name
    name_font = pygame.font.Font(None, 48)
    name_text = name_font.render(player.leader['name'], True, (255, 215, 0))
    name_rect = name_text.get_rect(center=(screen_width // 2, portrait_y + portrait_height + 40))
    surface.blit(name_text, name_rect)
    
    # Ability description box
    ability_box_y = portrait_y + portrait_height + 80
    ability_box_width = 600
    ability_box_height = 120
    ability_box_x = (screen_width - ability_box_width) // 2
    
    # Draw ability box
    pygame.draw.rect(surface, (40, 40, 50), pygame.Rect(ability_box_x, ability_box_y, ability_box_width, ability_box_height))
    pygame.draw.rect(surface, (255, 215, 0), pygame.Rect(ability_box_x, ability_box_y, ability_box_width, ability_box_height), width=3)
    
    # Ability title
    ability_title_font = pygame.font.Font(None, 32)
    ability_title = ability_title_font.render("LEADER ABILITY", True, (255, 215, 0))
    title_rect = ability_title.get_rect(center=(screen_width // 2, ability_box_y + 20))
    surface.blit(ability_title, title_rect)
    
    # Ability description (wrapped)
    ability_font = pygame.font.Font(None, 28)
    ability_desc = player.leader.get('ability_desc', 'Unknown ability')
    
    # Word wrap the description
    words = ability_desc.split()
    lines = []
    current_line = ""
    max_width = ability_box_width - 40
    
    for word in words:
        test_line = current_line + word + " "
        if ability_font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word + " "
    if current_line:
        lines.append(current_line)
    
    # Draw lines
    line_y = ability_box_y + 50
    for line in lines[:3]:  # Max 3 lines
        line_text = ability_font.render(line.strip(), True, (220, 220, 220))
        line_rect = line_text.get_rect(center=(screen_width // 2, line_y))
        surface.blit(line_text, line_rect)
        line_y += 30
    
    # Instructions
    instruction_font = pygame.font.Font(None, 28)
    instruction = instruction_font.render("Press SPACE or Click to close", True, (200, 200, 200))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 50))
    surface.blit(instruction, instruction_rect)

def draw_medic_selection_overlay(surface, game, screen_width, screen_height):
    """Draw overlay for selecting a card to revive with medic ability."""
    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    # Title
    title_font = pygame.font.Font(None, 56)
    title_text = title_font.render("MEDIC: Choose a card to revive", True, (100, 255, 100))
    title_rect = title_text.get_rect(center=(screen_width // 2, 60))
    surface.blit(title_text, title_rect)
    
    # Get valid cards
    valid_cards = game.get_medic_valid_cards(game.player1)
    
    if not valid_cards:
        # No cards available
        no_cards_text = UI_FONT.render("No cards available to revive", True, (255, 100, 100))
        no_cards_rect = no_cards_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(no_cards_text, no_cards_rect)
        return []
    
    # Display cards in a grid
    card_display_width = 160
    card_display_height = 240
    cards_per_row = 5
    spacing = 20
    start_y = 140
    
    card_rects = []
    for i, card in enumerate(valid_cards):
        row = i // cards_per_row
        col = i % cards_per_row
        
        # Calculate position
        total_row_width = cards_per_row * card_display_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_display_width + spacing)
        y = start_y + row * (card_display_height + spacing + 40)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        
        # Highlight border
        card_rect = pygame.Rect(x, y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (100, 255, 100), card_rect, width=3)
        
        # Card name below
        name_text = UI_FONT.render(card.name[:20], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 20))
        surface.blit(name_text, name_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = pygame.font.Font(None, 32)
    instruction = instruction_font.render("Click a card to revive it", True, (200, 200, 200))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def draw_decoy_selection_overlay(surface, game, screen_width, screen_height):
    """Draw overlay for selecting a card to return to hand with decoy ability."""
    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    # Title
    title_font = pygame.font.Font(None, 56)
    title_text = title_font.render("DECOY: Choose a card to return to your hand", True, (150, 200, 255))
    title_rect = title_text.get_rect(center=(screen_width // 2, 60))
    surface.blit(title_text, title_rect)
    
    # Subtitle
    subtitle_font = pygame.font.Font(None, 32)
    subtitle_text = subtitle_font.render("(You can take your own card or an opponent's card)", True, (200, 200, 200))
    subtitle_rect = subtitle_text.get_rect(center=(screen_width // 2, 100))
    surface.blit(subtitle_text, subtitle_rect)
    
    # Get valid cards (all non-Legendary Commander units on both boards)
    valid_cards = game.get_decoy_valid_cards()
    
    if not valid_cards:
        # No cards available
        no_cards_text = UI_FONT.render("No cards available on the board", True, (255, 100, 100))
        no_cards_rect = no_cards_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(no_cards_text, no_cards_rect)
        return []
    
    # Display cards in a grid
    card_display_width = 140
    card_display_height = 210
    cards_per_row = 6
    spacing = 15
    start_y = 160
    
    card_rects = []
    for i, card in enumerate(valid_cards):
        row = i // cards_per_row
        col = i % cards_per_row
        
        # Calculate position
        total_row_width = cards_per_row * card_display_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_display_width + spacing)
        y = start_y + row * (card_display_height + spacing + 50)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        
        # Determine card owner
        is_player_card = card in [c for row in game.player1.board.values() for c in row]
        is_opponent_card = card in [c for row in game.player2.board.values() for c in row]
        
        # Highlight border - blue for own cards, red for opponent cards
        card_rect = pygame.Rect(x, y, card_display_width, card_display_height)
        if is_player_card:
            pygame.draw.rect(surface, (100, 150, 255), card_rect, width=3)
        elif is_opponent_card:
            pygame.draw.rect(surface, (255, 100, 100), card_rect, width=3)
        
        # Owner label
        owner_text = UI_FONT.render("YOUR CARD" if is_player_card else "OPP CARD", True, 
                                    (100, 150, 255) if is_player_card else (255, 100, 100))
        owner_rect = owner_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 10))
        surface.blit(owner_text, owner_rect)
        
        # Card name below
        name_text = UI_FONT.render(card.name[:15], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 30))
        surface.blit(name_text, name_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = pygame.font.Font(None, 32)
    instruction = instruction_font.render("Click a card to return it to your hand", True, (200, 200, 200))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def draw_card_inspection_overlay(surface, card, screen_width, screen_height):
    """Draw full-screen card inspection overlay when spacebar/right-click is pressed."""
    # Keep gameplay view visible while inspecting a card
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    surface.blit(overlay, (0, 0))
    
    # Large card display
    card_display_width = 480
    card_display_height = 720
    card_x = (screen_width - card_display_width) // 2
    card_y = (screen_height - card_display_height) // 2 - 80  # Moved up to make room for description
    
    # Draw card image (scaled up)
    try:
        large_card_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(large_card_image, (card_x, card_y))
    except:
        pygame.draw.rect(surface, (80, 80, 90), pygame.Rect(card_x, card_y, card_display_width, card_display_height))
    
    # Golden border around card
    pygame.draw.rect(surface, (255, 215, 0), pygame.Rect(card_x, card_y, card_display_width, card_display_height), width=6)
    
    # Description box UNDER the card art
    desc_box_y = card_y + card_display_height + 20
    desc_box_height = 150
    desc_box_padding = 20
    
    # Create semi-transparent description box
    desc_surface = pygame.Surface((card_display_width, desc_box_height), pygame.SRCALPHA)
    desc_surface.fill((20, 30, 50, 230))  # Dark blue-gray with transparency
    
    # Border for description box
    pygame.draw.rect(desc_surface, (100, 150, 200, 200), desc_surface.get_rect(), width=3, border_radius=10)
    
    # Draw description text
    desc_font = pygame.font.SysFont("Arial", 24)
    small_font = pygame.font.SysFont("Arial", 20)
    
    # Card name at top
    name_text = desc_font.render(card.name, True, (255, 215, 0))
    name_rect = name_text.get_rect(center=(card_display_width // 2, 25))
    desc_surface.blit(name_text, name_rect)
    
    # Stats line
    stats_line = f"Power: {card.power}  •  Row: {card.row.capitalize()}  •  Faction: {card.faction}"
    stats_text = small_font.render(stats_line, True, (200, 200, 200))
    stats_rect = stats_text.get_rect(center=(card_display_width // 2, 55))
    desc_surface.blit(stats_text, stats_rect)
    
    # Ability/Description
    if card.ability:
        ability_title = small_font.render("Ability:", True, (150, 255, 150))
        desc_surface.blit(ability_title, (desc_box_padding, 80))
        
        # Word wrap the ability text
        ability_words = card.ability.split()
        line = ""
        line_y = 105
        max_line_width = card_display_width - (desc_box_padding * 2)
        
        for word in ability_words:
            test_line = line + word + " "
            if small_font.size(test_line)[0] < max_line_width:
                line = test_line
            else:
                if line:
                    ability_text = small_font.render(line.strip(), True, (220, 255, 220))
                    desc_surface.blit(ability_text, (desc_box_padding, line_y))
                    line_y += 25
                line = word + " "
        
        # Draw remaining text
        if line:
            ability_text = small_font.render(line.strip(), True, (220, 255, 220))
            desc_surface.blit(ability_text, (desc_box_padding, line_y))
    else:
        # No ability - show unit type
        no_ability_text = small_font.render("Standard unit card", True, (180, 180, 180))
        no_ability_rect = no_ability_text.get_rect(center=(card_display_width // 2, 105))
        desc_surface.blit(no_ability_text, no_ability_rect)
    
    # Blit description box to screen
    surface.blit(desc_surface, (card_x, desc_box_y))
    
    # Close instruction at bottom
    close_text = UI_FONT.render("Press SPACE or Click to close", True, (200, 200, 200))
    close_rect = close_text.get_rect(center=(screen_width // 2, screen_height - 30))
    surface.blit(close_text, close_rect)

def draw_discard_viewer(surface, discard_pile, screen_width, screen_height, scroll_offset):
    """Draw discard pile viewer overlay."""
    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    # Title
    title_font = pygame.font.Font(None, 64)
    title = title_font.render("DISCARD PILE", True, (255, 100, 100))
    title_rect = title.get_rect(center=(screen_width // 2, 60))
    surface.blit(title, title_rect)
    
    if not discard_pile:
        empty_text = UI_FONT.render("Discard pile is empty", True, (150, 150, 150))
        empty_rect = empty_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(empty_text, empty_rect)
        return
    
    # Draw cards in grid
    card_width = 200
    card_height = 300
    cards_per_row = 6
    spacing = 20
    start_y = 140 + scroll_offset
    
    for i, card in enumerate(discard_pile):
        row = i // cards_per_row
        col = i % cards_per_row
        
        total_row_width = cards_per_row * card_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_width + spacing)
        y = start_y + row * (card_height + spacing + 40)
        
        # Only draw if on screen
        if y > 60 and y < screen_height:
            scaled_image = pygame.transform.scale(card.image, (card_width, card_height))
            surface.blit(scaled_image, (x, y))
            pygame.draw.rect(surface, (255, 100, 100), pygame.Rect(x, y, card_width, card_height), width=3)
            
            # Store rect for click detection
            card.rect = pygame.Rect(x, y, card_width, card_height)
            
            # Card name
            name_text = pygame.font.Font(None, 24).render(card.name[:25], True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(x + card_width // 2, y + card_height + 20))
            surface.blit(name_text, name_rect)
    
    # Instructions
    inst_font = pygame.font.Font(None, 32)
    inst = inst_font.render("Scroll: Mouse Wheel | Right-Click: Inspect | Close: ESC or Click", True, (200, 200, 200))
    inst_rect = inst.get_rect(center=(screen_width // 2, screen_height - 40))
    surface.blit(inst, inst_rect)

def draw_jonas_peek_overlay(surface, game, screen_width, screen_height):
    """Jonas Quinn: Show opponent's next card."""
    if not game.player2.deck:
        return
    
    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))
    
    # Title
    title_font = pygame.font.Font(None, 56)
    title_text = title_font.render("JONAS QUINN: Opponent's Next Card", True, (100, 200, 255))
    title_rect = title_text.get_rect(center=(screen_width // 2, 80))
    surface.blit(title_text, title_rect)
    
    # Show next card
    next_card = game.player2.deck[-1]  # Top of deck
    card_display_width = 300
    card_display_height = 450
    card_x = (screen_width - card_display_width) // 2
    card_y = 200
    
    # Draw card
    scaled_image = pygame.transform.scale(next_card.image, (card_display_width, card_display_height))
    surface.blit(scaled_image, (card_x, card_y))
    pygame.draw.rect(surface, (100, 200, 255), pygame.Rect(card_x, card_y, card_display_width, card_display_height), width=3)
    
    # Card details
    detail_font = pygame.font.Font(None, 32)
    detail_y = card_y + card_display_height + 30
    
    details = [
        f"Power: {next_card.power}",
        f"Row: {next_card.row.capitalize()}",
        f"Ability: {next_card.ability if next_card.ability else 'None'}"
    ]
    
    for detail in details:
        detail_text = detail_font.render(detail, True, (200, 200, 200))
        detail_rect = detail_text.get_rect(center=(screen_width // 2, detail_y))
        surface.blit(detail_text, detail_rect)
        detail_y += 40
    
    # Close instruction
    instruction = detail_font.render("Click or Press SPACE to close", True, (150, 150, 150))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)

def draw_baal_clone_overlay(surface, game, screen_width, screen_height):
    """Ba'al Clone: Select unit to clone."""
    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    # Title
    title_font = pygame.font.Font(None, 56)
    title_text = title_font.render("BA'AL CLONE: Choose Unit to Duplicate", True, (200, 50, 50))
    title_rect = title_text.get_rect(center=(screen_width // 2, 60))
    surface.blit(title_text, title_rect)
    
    # Get all player units
    all_units = []
    for row_cards in game.player1.board.values():
        all_units.extend([c for c in row_cards if "Legendary Commander" not in (c.ability or "")])
    
    if not all_units:
        no_units_text = UI_FONT.render("No units available to clone", True, (255, 100, 100))
        no_units_rect = no_units_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(no_units_text, no_units_rect)
        return []
    
    # Display units in grid
    card_display_width = 140
    card_display_height = 210
    cards_per_row = 6
    spacing = 15
    start_y = 140
    
    card_rects = []
    for i, card in enumerate(all_units):
        row = i // cards_per_row
        col = i % cards_per_row
        
        total_row_width = cards_per_row * card_display_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_display_width + spacing)
        y = start_y + row * (card_display_height + spacing + 50)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        
        card_rect = pygame.Rect(x, y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (200, 50, 50), card_rect, width=3)
        
        # Power display
        power_text = UI_FONT.render(f"Power: {card.displayed_power}", True, (255, 215, 0))
        power_rect = power_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 20))
        surface.blit(power_text, power_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = pygame.font.Font(None, 32)
    instruction = instruction_font.render("Click a unit to clone it", True, (200, 200, 200))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def draw_vala_selection_overlay(surface, vala_cards, screen_width, screen_height):
    """Vala: Choose 1 of 3 cards."""
    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    
    # Title
    title_font = pygame.font.Font(None, 56)
    title_text = title_font.render("VALA MAL DORAN: Choose 1 Card to Keep", True, (150, 50, 150))
    title_rect = title_text.get_rect(center=(screen_width // 2, 80))
    surface.blit(title_text, title_rect)
    
    # Display 3 cards
    card_display_width = 300
    card_display_height = 450
    spacing = 80
    total_width = 3 * card_display_width + 2 * spacing
    start_x = (screen_width - total_width) // 2
    card_y = 200
    
    card_rects = []
    for i, card in enumerate(vala_cards[:3]):
        x = start_x + i * (card_display_width + spacing)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, card_y))
        
        card_rect = pygame.Rect(x, card_y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (150, 50, 150), card_rect, width=3)
        
        # Card name
        name_text = UI_FONT.render(card.name[:20], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, card_y + card_display_height + 30))
        surface.blit(name_text, name_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = pygame.font.Font(None, 32)
    instruction = instruction_font.render("Click a card to add it to your hand", True, (200, 200, 200))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 80))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def main():
    """Main game loop."""
    global PASS_BUTTON_RECT, MULLIGAN_BUTTON_RECT, screen, SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_FACTOR
    
    # Initialize card unlock system
    unlock_system = CardUnlockSystem()
    deck_manager = DeckManager(unlock_system)
    
    # --- SHOW MAIN MENU FIRST ---
    menu_result = run_main_menu(screen, unlock_system)
    
    if menu_result != 'new_game':
        # User quit or closed window
        pygame.quit()
        sys.exit()
    
    # --- SHOW STARGATE OPENING ANIMATION ---
    if not show_stargate_opening(screen):
        # User closed window during animation
        pygame.quit()
        sys.exit()
    
    # --- RUN DECK BUILDER FOR FACTION/LEADER SELECTION ---
    deck_selection = run_deck_builder(screen)
    
    if deck_selection is None:
        # User cancelled - go back to main menu
        main()
        return
    
    # Build player deck based on selection
    player_faction = deck_selection['faction']
    player_leader = deck_selection['leader']
    player_deck_ids = deck_selection['deck_ids']

    # Check if player has a custom deck for this faction
    custom_deck_data = deck_manager.get_deck(player_faction)
    if custom_deck_data and custom_deck_data.get("cards"):
        # Use custom deck
        custom_card_ids = custom_deck_data["cards"]
        # Filter out 'leader' key and invalid cards
        player_deck = [ALL_CARDS[id] for id in custom_card_ids if id != 'leader' and id in ALL_CARDS]
        # Shuffle custom deck
        import random
        random.shuffle(player_deck)
    else:
        # Use default faction deck
        player_deck = [ALL_CARDS[id] for id in player_deck_ids]
    
    # AI gets a random faction (different from player) and random leader
    from cards import FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD
    from deck_builder import FACTION_LEADERS
    available_ai_factions = [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD]
    available_ai_factions.remove(player_faction)
    import random
    ai_faction = random.choice(available_ai_factions)
    ai_leader = random.choice(FACTION_LEADERS[ai_faction])  # AI gets random leader
    ai_deck_ids = build_faction_deck(ai_faction, ai_leader)
    ai_deck = [ALL_CARDS[id] for id in ai_deck_ids]
    
    # Initialize UI button positions (NEW LAYOUT - Bottom aligned, scaled)
    # DHD Pass Button - position in bottom-right, ensuring it stays visible
    DHD_SIZE = int(100 * SCALE_FACTOR)  # DHD is circular, scaled
    button_margin = int(30 * SCALE_FACTOR)
    
    # Ensure buttons fit in bottom-right corner with proper spacing from edge
    # Use larger margins to ensure visibility in fullscreen
    safe_bottom_margin = max(button_margin, int(SCREEN_HEIGHT * 0.03))  # 3% of screen height
    safe_right_margin = max(button_margin, int(SCREEN_WIDTH * 0.02))    # 2% of screen width
    
    PASS_BUTTON_RECT = pygame.Rect(
        SCREEN_WIDTH - DHD_SIZE - safe_right_margin,
        SCREEN_HEIGHT - DHD_SIZE - safe_bottom_margin,
        DHD_SIZE,
        DHD_SIZE
    )
    
    MULLIGAN_BUTTON_RECT = pygame.Rect(
        SCREEN_WIDTH - int(300 * SCALE_FACTOR),
        SCREEN_HEIGHT - int(160 * SCALE_FACTOR),  # Increased from 140
        int(200 * SCALE_FACTOR),
        int(50 * SCALE_FACTOR)
    )
    
    # --- Animation Manager ---
    from animations import AmbientBackgroundEffects
    anim_manager = AnimationManager()
    ambient_effects = AmbientBackgroundEffects(SCREEN_WIDTH, SCREEN_HEIGHT)
    
    # Track previous scores for animation
    prev_p1_score = 0
    prev_p2_score = 0
    
    # --- Asset Loading ---
    assets = {}
    try:
        assets["board"] = pygame.image.load("assets/board_background.png").convert()
    except pygame.error as e:
        print(f"Warning: Could not load board background. Using solid color. ({e})")
        assets["board"] = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        assets["board"].fill((20, 20, 30))

    # Create game with player's selections
    game = Game(
        player1_faction=player_faction,
        player1_deck=player_deck,
        player1_leader=player_leader,
        player2_faction=ai_faction,
        player2_deck=ai_deck,
        player2_leader=ai_leader  # AI now has a leader
    )
    game.start_game()
    
    # Initialize Faction Powers for both players
    from power import FACTION_POWERS as FACTION_POWERS_FACTORY
    if player_faction in FACTION_POWERS_FACTORY:
        game.player1.faction_power = FACTION_POWERS_FACTORY[player_faction]
    
    if ai_faction in FACTION_POWERS_FACTORY:
        # Create separate instance for AI
        game.player2.faction_power = type(FACTION_POWERS_FACTORY[ai_faction])()
    
    # Iris Defense is ONLY for Tau'ri faction - it blocks next card
    # The iris_defense is the actual Iris mechanic, faction_power is the big ability
    # All players already have iris_defense initialized in Player.__init__
    # but only Tau'ri should be able to activate it
    
    
    # Start space battle for first round
    ambient_effects.start_round(round_number=1)
    
    # Show leader matchup animation
    from leader_matchup import LeaderMatchupAnimation
    matchup_anim = LeaderMatchupAnimation(player_leader, ai_leader, SCREEN_WIDTH, SCREEN_HEIGHT)
    clock_matchup = pygame.time.Clock()
    while not matchup_anim.finished:
        dt = clock_matchup.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_SPACE:
                    matchup_anim.finished = True  # Allow skipping
        
        matchup_anim.update(dt)
        matchup_anim.draw(screen)
        pygame.display.flip()
    
    # Show game start animation
    show_game_start_animation(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
    
    ai_controller = AIController(game, game.player2, difficulty="medium")
    selected_card = None
    dragging_card = None
    drag_offset = (0, 0)
    drag_target_x = 0
    drag_target_y = 0
    drag_velocity = Vector2()
    drag_trail = []
    drag_trail_emit_ms = 0
    drag_pickup_flash = 0.0
    drag_pulse = 0.0
    drag_hover_highlight = None
    card_hover_scale = 1.0
    target_hover_scale = 1.0
    hovered_card = None
    mulligan_selected = []
    inspected_card = None  # Card being inspected with spacebar
    inspected_leader = None  # Leader being inspected
    player_leader_rect = None
    ai_leader_rect = None
    player_ability_rect = None
    ai_ability_rect = None
    medic_selection_mode = False  # When player needs to choose card from discard
    medic_card_played = None  # The medic card that was just played
    decoy_selection_mode = False  # When player needs to choose card to return to hand
    decoy_card_played = None  # The decoy card that was just played
    ring_transport_selection = False  # When Goa'uld player is choosing card for ring transport
    ring_transport_animation = None  # Active ring transportation animation
    ring_transport_button_rect = None  # Ring button for click detection
    decoy_drag_target = None  # Card being hovered over when dragging Ring Transport
    decoy_valid_targets = []  # List of (card, rect) for valid decoy targets
    iris_button_rect = None  # Iris button for click detection
    previous_round = game.round_number  # Track round changes
    previous_weather = {"close": False, "ranged": False, "siege": False}  # Track weather changes
    paused = False  # Pause menu state
    
    # Discard pile viewer
    viewing_discard = False  # True when viewing discard pile
    discard_scroll = 0  # Scroll offset for discard viewer
    discard_rect = None  # Assigned during draw phase
    
    # Leader ability selection modes
    jonas_peek_active = False  # Jonas Quinn: Showing opponent's next card
    baal_clone_selection = False  # Ba'al: Choosing unit to clone
    vala_selection_mode = False  # Vala: Choosing 1 of 3 cards
    vala_cards_to_choose = []  # The 3 cards Vala can choose from
    thor_move_mode = False  # Thor: Selecting unit to move
    thor_selected_unit = None  # The unit Thor is moving
    
    # Iris Power UI elements
    # Player faction power - position to stay visible above hand area with safe margin
    faction_ui_height = 120
    # Ensure faction power UI is well above the bottom edge
    safe_margin_from_bottom = int(SCREEN_HEIGHT * 0.03)  # 3% margin from bottom
    
    player_faction_ui = FactionPowerUI(
        x=150,  # To the right of player leader (which is at x=20, width=100)
        y=SCREEN_HEIGHT - HAND_Y_OFFSET - faction_ui_height - safe_margin_from_bottom,
        width=300,
        height=faction_ui_height
    )
    ai_faction_ui = FactionPowerUI(
        x=150,  # To the right of AI leader (which is at x=20, width=100)
        y=180,  # Below AI leader (leader is at y=20, height=140, plus "LEADER" text ~15px + margin)
        width=300,
        height=faction_ui_height
    )
    faction_power_effect = None  # Active Iris Power visual effect
    
    clock = pygame.time.Clock()
    
    # AI Turn Animation System
    from animations import AITurnAnimation
    ai_turn_anim = AITurnAnimation(SCREEN_WIDTH, SCREEN_HEIGHT)
    ai_turn_in_progress = False
    ai_card_to_play = None
    ai_row_to_play = None
    ai_selected_card_index = None

    running = True
    fullscreen = FULLSCREEN
    
    while running:
        dt = clock.tick(60)  # 60 FPS, returns milliseconds since last frame
        
        # Check for round changes and reset space battle WITH COOL TRANSITION
        if game.round_number != previous_round:
            # Show round winner announcement FIRST
            if hasattr(game, 'round_winner'):
                show_round_winner_announcement(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Show transition message
            transition_font = pygame.font.SysFont("Arial", 80, bold=True)
            if game.round_number == 2:
                transition_text = "ENTERING HYPERSPACE..."
            elif game.round_number == 3:
                transition_text = "EMERGING NEAR PLANET..."
            else:
                transition_text = f"ROUND {game.round_number}"
            
            # Display transition with HYPERSPACE ANIMATION
            for frame in range(120):  # 2 seconds at 60fps
                screen.fill((5, 5, 15))
                
                # Hyperspace star streaks
                if game.round_number == 2:
                    # Stars stretching into lines (entering hyperspace)
                    for i in range(50):
                        start_x = random.randint(0, SCREEN_WIDTH)
                        y = random.randint(0, SCREEN_HEIGHT)
                        streak_length = int(frame * 10 + random.randint(0, 50))
                        end_x = start_x + streak_length
                        pygame.draw.line(screen, (150, 150, 255), (start_x, y), (end_x, y), 2)
                
                elif game.round_number == 3:
                    # Stars condensing back (emerging from hyperspace)
                    for i in range(50):
                        start_x = random.randint(0, SCREEN_WIDTH)
                        y = random.randint(0, SCREEN_HEIGHT)
                        streak_length = int((120 - frame) * 8 + random.randint(0, 40))
                        end_x = start_x + streak_length
                        pygame.draw.line(screen, (150, 150, 255), (start_x, y), (end_x, y), 2)
                    
                    # Planet appearing
                    if frame > 60:
                        planet_alpha = (frame - 60) * 4
                        planet_radius = int(SCREEN_HEIGHT * 0.15)
                        planet_surf = pygame.Surface((planet_radius * 2, planet_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(planet_surf, (80, 120, 200, planet_alpha), (planet_radius, planet_radius), planet_radius)
                        screen.blit(planet_surf, (SCREEN_WIDTH // 2 - planet_radius, 100))
                
                text_surf = transition_font.render(transition_text, True, (100, 150, 255))
                text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                screen.blit(text_surf, text_rect)
                pygame.display.flip()
                clock.tick(60)
            
            ambient_effects.end_round()
            ambient_effects.start_round(round_number=game.round_number)
            previous_round = game.round_number
        
        # Check for weather changes and add row effects
        if game.weather_active != previous_weather:
            # Clear old weather effects
            anim_manager.clear_row_weather()
            
            # Add new weather effects for affected rows
            for row_name, is_active in game.weather_active.items():
                if is_active:
                    target_flag = game.weather_row_targets.get(row_name)
                    weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                    
                    if target_flag in ("player1", "both"):
                        player_row_rect = PLAYER_ROW_RECTS.get(row_name)
                        if player_row_rect:
                            anim_manager.add_row_weather(weather_type, player_row_rect, SCREEN_WIDTH)
                    if target_flag in ("player2", "both"):
                        opponent_row_rect = OPPONENT_ROW_RECTS.get(row_name)
                        if opponent_row_rect:
                            anim_manager.add_row_weather(weather_type, opponent_row_rect, SCREEN_WIDTH)
            
            # Handle Clear Weather - show it on all rows for the black hole effect
            if any(game.current_weather_types.get(row) == "Wormhole Stabilization" for row in ["close", "ranged", "siege"]):
                # Show clear weather effect on middle row for dramatic center effect
                middle_row_rect = PLAYER_ROW_RECTS.get("ranged")  # Use ranged as middle
                if middle_row_rect:
                    anim_manager.add_row_weather("Wormhole Stabilization", middle_row_rect, SCREEN_WIDTH)
            
            previous_weather = game.weather_active.copy()

        # AI leader ability - auto-activate when appropriate (e.g., Apophis weather strike)
        if (game.game_state == "playing"
                and game.current_player == game.player2
                and not game.player2.has_passed):
            ability_result = game.activate_leader_ability(game.player2)
            if ability_result:
                ability_name = ability_result.get("ability", game.player2.leader.get('ability', 'Leader Ability'))
                anim_manager.add_effect(create_ability_animation(
                    ability_name,
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 3
                ))
                for row_name in ability_result.get("rows", []):
                    weather_target = game.weather_row_targets.get(row_name, "both")
                    if weather_target in ("player1", "both"):
                        rect = PLAYER_ROW_RECTS.get(row_name)
                        if rect:
                            anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                    if weather_target in ("player2", "both"):
                        rect = OPPONENT_ROW_RECTS.get(row_name)
                        if rect:
                            anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))

        # Update animations
        anim_manager.update(dt)
        ambient_effects.update(dt)
        drag_pulse += dt * 0.005
        if dragging_card:
            drag_pickup_flash = max(0.0, drag_pickup_flash - dt / 500.0)
        else:
            drag_pickup_flash = max(0.0, drag_pickup_flash - dt / 350.0)
            drag_velocity *= 0.9
        drag_trail_emit_ms = max(0, drag_trail_emit_ms - dt)
        for blob in drag_trail[:]:
            blob["alpha"] -= dt * 0.35
            blob["width_scale"] += dt * 0.0008
            blob["height_scale"] += dt * 0.0006
            if blob["alpha"] <= 0:
                drag_trail.remove(blob)
        if dragging_card:
            if drag_trail_emit_ms <= 0:
                drag_trail.append({
                    "pos": dragging_card.rect.center,
                    "alpha": 130,
                    "width_scale": 1.0 + min(0.25, abs(drag_velocity.x) * 0.04),
                    "height_scale": 1.0 + min(0.2, abs(drag_velocity.y) * 0.03),
                    "color": get_row_color(dragging_card.row)
                })
                drag_trail_emit_ms = 45

        # Update card hover scale smoothly
        if abs(card_hover_scale - target_hover_scale) > 0.01:
            card_hover_scale += (target_hover_scale - card_hover_scale) * 0.15
        
        # Update Iris Power effect
        if faction_power_effect:
            if not faction_power_effect.update(dt):
                faction_power_effect = None
        
        # Update Ring Transportation animation
        if ring_transport_animation:
            if not ring_transport_animation.update(dt):
                # Animation complete
                ring_transport_animation = None
                if game.player1.ring_transportation:
                    game.player1.ring_transportation.complete_animation()
        
        # Update Iris Power UI hover states
        mouse_pos = pygame.mouse.get_pos()
        player_faction_ui.update(mouse_pos)
        ai_faction_ui.update(mouse_pos)
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Debug: Print all key presses
                if event.key == pygame.K_F11:
                    print(f"🔑 DEBUG: F11 key detected (keycode: {event.key})")
                
                # ESC to toggle pause menu or close overlays
                if event.key == pygame.K_ESCAPE:
                    if inspected_card or inspected_leader:
                        inspected_card = None
                        inspected_leader = None
                    elif viewing_discard:
                        viewing_discard = False
                        discard_scroll = 0
                    elif jonas_peek_active:
                        jonas_peek_active = False
                    elif game.game_state == "playing":
                        paused = not paused
                
                # Toggle fullscreen with F11 or Alt+Enter
                elif event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                    print(f"🔑 Fullscreen toggle! Current state: {fullscreen}")
                    fullscreen = not fullscreen
                    if fullscreen:
                        # Go fullscreen using native desktop resolution
                        screen = pygame.display.set_mode((DESKTOP_WIDTH, DESKTOP_HEIGHT), pygame.FULLSCREEN)
                        # Update screen dimensions for UI rendering
                        SCREEN_WIDTH = DESKTOP_WIDTH
                        SCREEN_HEIGHT = DESKTOP_HEIGHT
                        # Recalculate scale factor for fullscreen
                        SCALE_FACTOR = min(DESKTOP_WIDTH / TARGET_WIDTH, DESKTOP_HEIGHT / TARGET_HEIGHT, 1.0)
                        
                        # Recalculate UI button positions for new resolution
                        DHD_SIZE = int(100 * SCALE_FACTOR)
                        button_margin = int(30 * SCALE_FACTOR)
                        safe_bottom_margin = max(button_margin, int(SCREEN_HEIGHT * 0.03))  # 3% margin
                        safe_right_margin = max(button_margin, int(SCREEN_WIDTH * 0.02))    # 2% margin
                        
                        PASS_BUTTON_RECT = pygame.Rect(
                            SCREEN_WIDTH - DHD_SIZE - safe_right_margin,
                            SCREEN_HEIGHT - DHD_SIZE - safe_bottom_margin,
                            DHD_SIZE,
                            DHD_SIZE
                        )
                        MULLIGAN_BUTTON_RECT = pygame.Rect(
                            SCREEN_WIDTH - int(300 * SCALE_FACTOR),
                            SCREEN_HEIGHT - int(160 * SCALE_FACTOR),
                            int(200 * SCALE_FACTOR),
                            int(50 * SCALE_FACTOR)
                        )
                        
                        print(f"✓ Fullscreen: ON - Resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
                        print(f"  Scale Factor: {SCALE_FACTOR:.2f}")
                    else:
                        # Restore to windowed mode with original calculated size
                        original_scale_x = (DESKTOP_WIDTH * 0.95) / TARGET_WIDTH
                        original_scale_y = (DESKTOP_HEIGHT * 0.95) / TARGET_HEIGHT
                        SCALE_FACTOR = min(original_scale_x, original_scale_y, 1.0)
                        SCREEN_WIDTH = int(TARGET_WIDTH * SCALE_FACTOR)
                        SCREEN_HEIGHT = int(TARGET_HEIGHT * SCALE_FACTOR)
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SHOWN | pygame.SCALED)
                        
                        # Recalculate UI button positions for windowed mode
                        DHD_SIZE = int(100 * SCALE_FACTOR)
                        button_margin = int(30 * SCALE_FACTOR)
                        safe_bottom_margin = max(button_margin, int(SCREEN_HEIGHT * 0.03))  # 3% margin
                        safe_right_margin = max(button_margin, int(SCREEN_WIDTH * 0.02))    # 2% margin
                        
                        PASS_BUTTON_RECT = pygame.Rect(
                            SCREEN_WIDTH - DHD_SIZE - safe_right_margin,
                            SCREEN_HEIGHT - DHD_SIZE - safe_bottom_margin,
                            DHD_SIZE,
                            DHD_SIZE
                        )
                        MULLIGAN_BUTTON_RECT = pygame.Rect(
                            SCREEN_WIDTH - int(300 * SCALE_FACTOR),
                            SCREEN_HEIGHT - int(160 * SCALE_FACTOR),
                            int(200 * SCALE_FACTOR),
                            int(50 * SCALE_FACTOR)
                        )
                        
                        print(f"✓ Fullscreen: OFF - Window: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
                
                # F key = Activate Faction Power
                elif event.key == pygame.K_f:
                    if game.game_state == "playing" and game.current_player == game.player1:
                        if game.player1.faction_power and game.player1.faction_power.is_available():
                            if game.player1.faction_power.activate(game, game.player1):
                                # Trigger visual effect
                                faction_power_effect = FactionPowerEffect(
                                    game.player1.faction,
                                    SCREEN_WIDTH // 2,
                                    SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH,
                                    SCREEN_HEIGHT
                                )
                                # Recalculate scores
                                game.player1.calculate_score()
                                game.player2.calculate_score()
                                print(f"✓ Faction Power activated with F key: {game.player1.faction_power.name}")
                
                # SPACEBAR = Alternative preview (same as right-click)
                elif event.key == pygame.K_SPACE:
                    if inspected_card or inspected_leader:
                        # Close preview
                        inspected_card = None
                        inspected_leader = None
                    elif viewing_discard or jonas_peek_active:
                        # Close overlays
                        viewing_discard = False
                        jonas_peek_active = False
                        discard_scroll = 0
                    elif selected_card and game.game_state == "playing":
                        # Preview selected card
                        inspected_card = selected_card
                
                # Game over screen - R to restart
                if game.game_state == "game_over":
                    if event.key == pygame.K_r:
                        main()
                        return
                    elif event.key == pygame.K_ESCAPE:
                        running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if (player_ability_rect and player_ability_rect.collidepoint(event.pos)
                            and game.game_state == "playing"
                            and game.current_player == game.player1
                            and not game.player1.has_passed):
                        ability_result = game.activate_leader_ability(game.player1)
                        if ability_result:
                            ability_name = ability_result.get("ability", game.player1.leader.get('ability', 'Leader Ability'))
                            anim_manager.add_effect(create_ability_animation(
                                ability_name,
                                SCREEN_WIDTH // 2,
                                SCREEN_HEIGHT // 2
                            ))
                            for row_name in ability_result.get("rows", []):
                                weather_target = game.weather_row_targets.get(row_name, "both")
                                if weather_target in ("player1", "both"):
                                    rect = PLAYER_ROW_RECTS.get(row_name)
                                    if rect:
                                        anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                                if weather_target in ("player2", "both"):
                                    rect = OPPONENT_ROW_RECTS.get(row_name)
                                    if rect:
                                        anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                        continue
                # RIGHT CLICK = Card Preview/Zoom or Discard Pile View
                if event.button == 3:  # Right click
                    # Check if right-clicking discard pile to view it
                    if discard_rect and discard_rect.collidepoint(event.pos) and not viewing_discard:
                        viewing_discard = True
                        discard_scroll = 0
                        continue
                    
                    # Check if right-clicking a card in the discard viewer to inspect it
                    if viewing_discard:
                        card_clicked = False
                        for card in game.player1.discard_pile:
                            if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                inspected_card = card
                                selected_card = None
                                card_clicked = True
                                break
                        
                        # If clicked on a card, don't close the viewer
                        if card_clicked:
                            continue
                        
                        # Otherwise close the discard viewer
                        viewing_discard = False
                        discard_scroll = 0
                        continue
                    
                    # Close any existing previews
                    if inspected_card or inspected_leader:
                        inspected_card = None
                        inspected_leader = None
                    else:
                        # Check if clicking on a card in hand
                        for card in game.player1.hand:
                            if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                inspected_card = card
                                selected_card = None
                                break
                        
                        # Check if clicking on board cards (both player and opponent)
                        if not inspected_card:
                            for player_obj in [game.player1, game.player2]:
                                for row_name, cards in player_obj.board.items():
                                    for card in cards:
                                        if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                            inspected_card = card
                                            selected_card = None
                                            break
                                    if inspected_card:
                                        break
                                if inspected_card:
                                    break
                        
                        # Check if clicking on leader portraits
                        if not inspected_card:
                            if player_leader_rect and player_leader_rect.collidepoint(event.pos):
                                inspected_leader = game.player1
                            elif ai_leader_rect and ai_leader_rect.collidepoint(event.pos):
                                inspected_leader = game.player2
                    continue
                
                # LEFT CLICK = Select/Activate
                if event.button != 1:  # Only handle left click below
                    continue
                
                # Click discard pile to view it
                if discard_rect and discard_rect.collidepoint(event.pos) and not viewing_discard:
                    viewing_discard = True
                    discard_scroll = 0
                
                # Close discard viewer with click
                if viewing_discard and event.button == 1:
                    viewing_discard = False
                
                # Handle discard scroll with mouse wheel
                if viewing_discard and event.button in [4, 5]:
                    if event.button == 4:  # Scroll up
                        discard_scroll = min(0, discard_scroll + 50)
                    else:  # Scroll down
                        discard_scroll -= 50
                
                # Handle medic selection mode
                if medic_selection_mode:
                    # Check if clicking on a card in the medic selection overlay
                    # This will be handled after drawing
                    pass
                
                # Check if clicking Faction Power button (player only)
                if game.game_state == "playing" and game.current_player == game.player1:
                    if game.player1.faction_power and player_faction_ui.handle_click(event.pos):
                        if game.player1.faction_power.is_available():
                            # Activate Faction Power
                            if game.player1.faction_power.activate(game, game.player1):
                                # Trigger visual effect
                                faction_power_effect = FactionPowerEffect(
                                    game.player1.faction,
                                    SCREEN_WIDTH // 2,
                                    SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH,
                                    SCREEN_HEIGHT
                                )
                                # Recalculate scores
                                game.player1.calculate_score()
                                game.player2.calculate_score()
                                continue
                
                # Check if clicking on leader portraits (for inspection)
                if player_leader_rect and player_leader_rect.collidepoint(event.pos):
                    inspected_leader = game.player1
                    inspected_card = None
                    selected_card = None
                    continue
                elif ai_leader_rect and ai_leader_rect.collidepoint(event.pos):
                    inspected_leader = game.player2
                    inspected_card = None
                    selected_card = None
                    continue
                
                # Check if clicking on opponent cards (for inspection)
                if not inspected_card and not inspected_leader:
                    for row_name, cards in game.player2.board.items():
                        for card in cards:
                            if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                inspected_card = card
                                selected_card = None
                                break
                        if inspected_card:
                            break
                
                # Close inspection overlays if clicking
                if inspected_card or inspected_leader:
                    inspected_card = None
                    inspected_leader = None
                    continue
                
                # Mulligan phase
                if game.game_state == "mulligan":
                    # Select cards to mulligan (max 2)
                    for card in game.player1.hand:
                        if card.rect.collidepoint(event.pos):
                            if card in mulligan_selected:
                                mulligan_selected.remove(card)
                            elif len(mulligan_selected) < 5:  # Max 5 cards
                                mulligan_selected.append(card)
                            break
                    
                    # Confirm mulligan
                    if MULLIGAN_BUTTON_RECT.collidepoint(event.pos):
                        # Enforce 2-5 card limit
                        if len(mulligan_selected) < 2:
                            # Show error message
                            print("Must select at least 2 cards for mulligan!")
                            continue
                        elif len(mulligan_selected) > 5:
                            # Show error message
                            print("Cannot mulligan more than 5 cards!")
                            continue
                        
                        game.mulligan(game.player1, mulligan_selected)
                        mulligan_selected = []
                        # AI does simple mulligan (redraw 2-4 cards randomly)
                        ai_mulligan_count = random.randint(2, 4)
                        ai_cards = random.sample(game.player2.hand, min(ai_mulligan_count, len(game.player2.hand)))
                        game.mulligan(game.player2, ai_cards)
                        game.end_mulligan_phase()
                
                # Playing phase - START DRAG
                elif game.game_state == "playing":
                    if game.current_player == game.player1 and not game.player1.has_passed:
                        # Check if clicking on pass button (DHD)
                        if PASS_BUTTON_RECT.collidepoint(event.pos):
                            selected_card = None
                            dragging_card = None
                            drag_velocity = Vector2()
                            drag_pickup_flash = 0.0
                            
                            # Add DHD button press animation
                            dhd_anim = StargateActivationEffect(PASS_BUTTON_RECT.centerx, PASS_BUTTON_RECT.centery, duration=800)
                            anim_manager.add_effect(dhd_anim)
                            
                            game.pass_turn()
                        # Iris button click (Tau'ri only)
                        elif iris_button_rect and iris_button_rect.collidepoint(event.pos):
                            if game.player1.iris_defense.is_available():
                                game.player1.iris_defense.activate()
                                # Trigger Iris closing animation at center of screen
                                from animations import IrisClosingEffect
                                iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                                anim_manager.add_effect(iris_anim)
                        # Ring Transportation button click (Goa'uld only)
                        elif ring_transport_button_rect and ring_transport_button_rect.collidepoint(event.pos):
                            if game.player1.ring_transportation and game.player1.ring_transportation.can_use():
                                # Enter card selection mode - next card clicked will be transported
                                ring_transport_selection = True
                        else:
                            # Ring Transport selection mode - clicking a card on player's board
                            if ring_transport_selection:
                                # Check if clicking on player's CLOSE COMBAT cards only
                                card_clicked = False
                                row_cards = game.player1.board.get("close", [])
                                for card in row_cards:
                                    if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                        # Start ring transportation animation
                                        from power import RingTransportAnimation
                                        
                                        start_pos = (card.rect.centerx, card.rect.centery)
                                        # End position = center of hand area
                                        end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - HAND_Y_OFFSET // 2)
                                        
                                        ring_transport_animation = RingTransportAnimation(
                                            card, start_pos, end_pos, SCREEN_WIDTH, SCREEN_HEIGHT
                                        )
                                        
                                        # Remove card from board and add to hand
                                        game.player1.board["close"].remove(card)
                                        game.player1.hand.append(card)
                                        
                                        # Mark ability as used
                                        game.player1.ring_transportation.use(card)
                                        
                                        # Recalculate scores
                                        game.player1.calculate_score()
                                        game.player2.calculate_score()
                                        
                                        ring_transport_selection = False
                                        card_clicked = True
                                        break
                                
                                if card_clicked:
                                    continue
                            
                            # Check if clicking on a card in hand
                            for card in game.player1.hand:
                                if card.rect.collidepoint(event.pos):
                                    # Check if clicking the same special card again (confirmation)
                                    if card.row == "special" and selected_card == card:
                                        # Second click = confirm and play
                                        # Check if this is a decoy card
                                        if "Ring Transport" in (card.ability or ""):
                                            valid_decoy_cards = game.get_decoy_valid_cards()
                                            if valid_decoy_cards:
                                                # Enter decoy selection mode
                                                decoy_selection_mode = True
                                                decoy_card_played = card
                                                game.play_card(card, card.row)
                                            else:
                                                # No cards to decoy, play normally
                                                game.play_card(card, card.row)
                                        else:
                                            # Check if this is Wormhole Stabilization (Clear Weather)
                                            if "Wormhole Stabilization" in (card.ability or ""):
                                                from animations import ClearWeatherBlackHole
                                                black_hole_anim = ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                                                anim_manager.add_effect(black_hole_anim)
                                            game.play_card(card, card.row)
                                        selected_card = None
                                        dragging_card = None
                                        drag_velocity = Vector2()
                                        drag_pickup_flash = 0.0
                                        break
                                    
                                    # First click or different card - Select it
                                    selected_card = card
                                    
                                    if card.row == "special":
                                        # Special cards - Ring Transport and Command Network can be dragged
                                        if "Ring Transport" in (card.ability or "") or "Command Network" in (card.ability or ""):
                                            # Allow dragging these special cards
                                            dragging_card = card
                                            drag_offset = (card.rect.x - event.pos[0], card.rect.y - event.pos[1])
                                            drag_velocity = Vector2()
                                            drag_trail.clear()
                                            drag_trail_emit_ms = 0
                                            drag_pickup_flash = 1.0
                                            drag_pulse = 0.0
                                            # Get valid decoy targets for Ring Transport
                                            if "Ring Transport" in (card.ability or ""):
                                                decoy_valid_targets = []
                                                valid_cards = game.get_decoy_valid_cards()
                                                for valid_card in valid_cards:
                                                    if hasattr(valid_card, 'rect'):
                                                        decoy_valid_targets.append((valid_card, valid_card.rect.copy()))
                                        else:
                                            # Other special cards: click AGAIN to play, or press SPACE to inspect
                                            dragging_card = None
                                            drag_velocity = Vector2()
                                            drag_pickup_flash = 0.0
                                    else:
                                        # Start dragging unit cards
                                        dragging_card = card
                                        drag_offset = (card.rect.x - event.pos[0], card.rect.y - event.pos[1])
                                        drag_velocity = Vector2()
                                        drag_trail.clear()
                                        drag_trail_emit_ms = 0
                                        drag_pickup_flash = 1.0
                                        drag_pulse = 0.0
                                    
                                    break
            
            elif event.type == pygame.MOUSEBUTTONUP:
                # Drop card
                if dragging_card and game.game_state == "playing":
                    played = False
                    is_spy = "Deep Cover Agent" in (dragging_card.ability or "")
                    ability_text = dragging_card.ability or ""
                    
                    # Weather and special cards can target any row
                    if dragging_card.row in ["weather", "special"]:
                        if dragging_card.row == "weather":
                            for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                                for row_name, rect in rects.items():
                                    if rect.collidepoint(event.pos):
                                        game.play_card(dragging_card, row_name)
                                        played = True
                                        
                                        effect_x = rect.centerx
                                        effect_y = rect.centery
                                        stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=800)
                                        anim_manager.add_effect(stargate_effect)
                                        break
                                if played:
                                    break
                        else:
                            if "Command Network" in ability_text:
                                for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
                                    if slot_rect.collidepoint(event.pos):
                                        game.play_card(dragging_card, row_name)
                                        played = True
                                        effect_x = slot_rect.centerx
                                        effect_y = slot_rect.centery
                                        anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=800))
                                        break
                            elif "Ring Transport" in ability_text:
                                # Ring Transport - check if dropped on a valid card
                                if decoy_drag_target:
                                    # Play the decoy card first
                                    game.play_card(dragging_card, "special")
                                    # Apply decoy effect
                                    if game.apply_decoy(decoy_drag_target):
                                        # Show ring transport animation
                                        effect_x = decoy_drag_target.rect.centerx
                                        effect_y = decoy_drag_target.rect.centery
                                        anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=800))
                                        game.player1.calculate_score()
                                        game.player2.calculate_score()
                                        game.switch_turn()
                                        played = True
                                    decoy_valid_targets = []
                                    decoy_drag_target = None
                            else:
                                for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                                    for row_name, rect in rects.items():
                                        if rect.collidepoint(event.pos):
                                            game.play_card(dragging_card, row_name)
                                            played = True
                                            
                                            effect_x = rect.centerx
                                            effect_y = rect.centery
                                            stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=800)
                                            anim_manager.add_effect(stargate_effect)
                                            break
                                    if played:
                                        break
                    else:
                        # Regular unit cards
                        target_rows = OPPONENT_ROW_RECTS if is_spy else PLAYER_ROW_RECTS
                        
                        # Check which row the card was dropped on
                        for row_name, rect in target_rows.items():
                            if rect.collidepoint(event.pos):
                                if dragging_card.row == row_name or (dragging_card.row == "agile" and row_name in ["close", "ranged"]):
                                    
                                    # --- NEW: Check card for specific animations ---
                                    if "Naquadah Overload" in (dragging_card.ability or ""):
                                        # Naquadah Overload: Play card first, then show explosions on affected rows
                                        game.play_card(dragging_card, row_name)
                                        
                                        # Create blue explosions ONLY on rows where cards were destroyed
                                        for player, destroyed_row in game.last_scorch_positions:
                                            # Determine which row rect to use
                                            if player == game.player1:
                                                row_rect = PLAYER_ROW_RECTS.get(destroyed_row)
                                            else:
                                                row_rect = OPPONENT_ROW_RECTS.get(destroyed_row)
                                            
                                            if row_rect:
                                                anim_manager.add_effect(NaquadahExplosionEffect(
                                                    SCREEN_WIDTH // 2, 
                                                    row_rect.centery, 
                                                    duration=1200
                                                ))
                                        
                                        # Clear the positions for next time
                                        game.last_scorch_positions = []
                                        played = True
                                    elif "Legendary Commander" in (dragging_card.ability or ""):
                                        # Legendary Commander card - use unique hero animation
                                        effect_x = rect.centerx
                                        effect_y = rect.centery
                                        hero_anim = create_hero_animation(dragging_card.name, effect_x, effect_y)
                                        anim_manager.add_effect(hero_anim)
                                        anim_manager.add_effect(LegendaryLightningEffect(dragging_card))
                                    else:
                                        # Check for special abilities
                                        effect_x = rect.centerx
                                        effect_y = rect.centery
                                        
                                        ability = dragging_card.ability or ""
                                        ability_triggered = False
                                        
                                        # Check for special ability animations
                                        for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones", 
                                                               "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement"]:
                                            if special_ability in ability:
                                                ability_anim = create_ability_animation(ability, effect_x, effect_y)
                                                anim_manager.add_effect(ability_anim)
                                                ability_triggered = True
                                                break
                                        
                                        # Default stargate effect if no special ability
                                        if not ability_triggered:
                                            anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y))
                                    
                                    # Add ship to space battle if siege card is PLAYED
                                    if dragging_card.row == "siege":
                                        ambient_effects.add_ship(game.player1.faction, dragging_card.name, is_player=True)
                                    
                                    # Check if this is a medic card
                                    if "Medical Evac" in (dragging_card.ability or ""):
                                        valid_medic_cards = game.get_medic_valid_cards(game.player1)
                                        if valid_medic_cards:
                                            # Enter medic selection mode
                                            medic_selection_mode = True
                                            medic_card_played = dragging_card
                                            game.play_card(dragging_card, row_name)
                                        else:
                                            # No cards to revive, play normally
                                            game.play_card(dragging_card, row_name)
                                    else:
                                        game.play_card(dragging_card, row_name)
                                    
                                    played = True
                                    break
                    
                    # Reset drag state
                    if not played:
                        selected_card = None
                    dragging_card = None
                    drag_velocity = Vector2()
                    drag_pickup_flash = 0.0
                    decoy_valid_targets = []
                    decoy_drag_target = None
            
            elif event.type == pygame.MOUSEMOTION:
                # Update dragging position with smooth easing
                if dragging_card:
                    drag_target_x = event.pos[0] + drag_offset[0]
                    drag_target_y = event.pos[1] + drag_offset[1]
                    # Apply easing for smooth follow
                    easing_factor = 0.25  # Lower = smoother but more lag
                    dragging_card.rect.x += (drag_target_x - dragging_card.rect.x) * easing_factor
                    dragging_card.rect.y += (drag_target_y - dragging_card.rect.y) * easing_factor
                    rel_x, rel_y = getattr(event, "rel", (0, 0))
                    drag_velocity.x = drag_velocity.x * 0.7 + rel_x * 0.3
                    drag_velocity.y = drag_velocity.y * 0.7 + rel_y * 0.3
                    
                    # Update Ring Transport decoy target detection
                    if "Ring Transport" in (dragging_card.ability or ""):
                        decoy_drag_target = None
                        mouse_pos = event.pos
                        for card, rect in decoy_valid_targets:
                            if rect.collidepoint(mouse_pos):
                                decoy_drag_target = card
                                break
                else:
                    drag_velocity *= 0.85
                    decoy_drag_target = None
                
                # Check for card hover in hand (for scale effect)
                if not dragging_card and game.game_state in ("playing", "mulligan"):
                    mouse_pos = event.pos
                    new_hovered = None
                    for card in game.player1.hand:
                        if hasattr(card, 'rect') and card.rect.collidepoint(mouse_pos):
                            new_hovered = card
                            break
                    if new_hovered != hovered_card:
                        hovered_card = new_hovered
                        target_hover_scale = 1.08 if hovered_card else 1.0
        
        # Leader ability triggers (at start of player's turn)
        if game.current_player == game.player1 and game.game_state == "playing" and not game.player1.has_passed:
            # Jonas Quinn: See opponent's next card (auto-trigger once per turn)
            if game.player1.leader and "Jonas" in game.player1.leader.get('name', ''):
                if not hasattr(game, 'jonas_used_this_turn'):
                    game.jonas_used_this_turn = {}
                if game.round_number not in game.jonas_used_this_turn and game.player2.deck:
                    jonas_peek_active = True
                    game.jonas_used_this_turn[game.round_number] = True
            
            # Vala: Look at 3 cards, keep 1 (once per round, manual trigger with V key)
            # Ba'al Clone: Clone highest unit (once per round, manual trigger with B key)
            # Thor: Move unit (once per round, manual trigger with T key)
        
        # Simple AI for Player 2 - WITH SMOOTH ANIMATIONS
        if game.current_player == game.player2 and game.game_state == "playing":
            if not ai_turn_in_progress:
                # Start AI turn animation
                ai_turn_anim.start_thinking()
                ai_turn_in_progress = True
                ai_card_to_play = None
                ai_row_to_play = None
            
            # Update AI animation
            ai_result = ai_turn_anim.update(dt)
            
            if ai_result == "thinking_done":
                # AI has finished thinking, get the decision
                ai_board_before = {row: len(cards) for row, cards in game.player2.board.items()}
                
                # Get AI decision without executing it yet
                card_to_play, row_to_play = ai_controller.choose_move()
                
                if card_to_play:
                    # Store the decision
                    ai_card_to_play = card_to_play
                    ai_row_to_play = row_to_play
                    # Find card index in hand for animation
                    try:
                        card_index = game.player2.hand.index(card_to_play)
                        ai_selected_card_index = card_index
                        ai_turn_anim.start_selecting(card_index)
                    except ValueError:
                        # Card not in hand, skip animation
                        ai_selected_card_index = None
                        ai_turn_anim.finish()
                        ai_turn_in_progress = False
                else:
                    ai_selected_card_index = None
                    # AI passes or uses power
                    ai_turn_anim.finish()
                    game.switch_turn()
                    ai_turn_in_progress = False
            
            elif ai_result == "selecting_done":
                # Start playing animation
                if ai_card_to_play and ai_row_to_play:
                    total_cards = len(game.player2.hand)
                    start_center = get_opponent_hand_card_center(total_cards, ai_selected_card_index)
                    ability = ai_card_to_play.ability or ""
                    target_rects = PLAYER_ROW_RECTS if ("Deep Cover Agent" in ability or ai_card_to_play.row == "weather") else OPPONENT_ROW_RECTS
                    target_rect = target_rects.get(ai_row_to_play)
                    if not target_rect:
                        # Fallback to any matching row rect
                        target_rect = PLAYER_ROW_RECTS.get(ai_row_to_play) or OPPONENT_ROW_RECTS.get(ai_row_to_play)
                    end_center = (target_rect.centerx, target_rect.centery) if target_rect else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    if ai_card_to_play.image:
                        anim_manager.add_effect(AICardPlayAnimation(ai_card_to_play.image, start_center, end_center))
                ai_turn_anim.start_playing(ai_row_to_play)
            
            elif ai_result == "playing_done":
                # Actually play the card
                if ai_card_to_play and ai_row_to_play:
                    ability = ai_card_to_play.ability or ""
                    
                    # Play the card
                    game.play_card(ai_card_to_play, ai_row_to_play)
                    ai_selected_card_index = None
                    
                    # Check if AI played a siege card for space battle
                    if ai_row_to_play == 'siege':
                        ambient_effects.add_ship(game.player2.faction, ai_card_to_play.name, is_player=False)
                    
                    # Trigger visual effect for the play
                    target_rect = OPPONENT_ROW_RECTS.get(ai_row_to_play)
                    effect_x = target_rect.centerx if target_rect else SCREEN_WIDTH // 2
                    effect_y = target_rect.centery if target_rect else SCREEN_HEIGHT // 4
                    
                    # Check for Naquadah Overload
                    if "Naquadah Overload" in ability:
                        # Create blue explosions ONLY on rows where cards were destroyed
                        for player, destroyed_row in game.last_scorch_positions:
                            if player == game.player1:
                                row_rect = PLAYER_ROW_RECTS.get(destroyed_row)
                            else:
                                row_rect = OPPONENT_ROW_RECTS.get(destroyed_row)
                            
                            if row_rect:
                                anim_manager.add_effect(NaquadahExplosionEffect(
                                    SCREEN_WIDTH // 2, 
                                    row_rect.centery, 
                                    duration=1200
                                ))
                        game.last_scorch_positions = []
                    elif "Legendary Commander" in ability:
                        hero_anim = create_hero_animation(ai_card_to_play.name, effect_x, effect_y)
                        anim_manager.add_effect(hero_anim)
                        anim_manager.add_effect(LegendaryLightningEffect(ai_card_to_play))
                    else:
                        stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=500)
                        anim_manager.add_effect(stargate_effect)
                
                ai_turn_anim.start_resolving()
            
            elif ai_result == "resolving_done":
                # Recalculate scores
                game.player1.calculate_score()
                game.player2.calculate_score()
                
                # Finish turn
                ai_turn_anim.finish()
                game.switch_turn()
                ai_turn_in_progress = False
                ai_selected_card_index = None
        
        # Check for score changes and trigger animations
        prev_p1_before = prev_p1_score
        prev_p2_before = prev_p2_score

        if game.player1.score != prev_p1_score:
            score_x = SCREEN_WIDTH - int(SCREEN_WIDTH * 0.052)
            p1_lead_gain = (prev_p1_before <= prev_p2_before) and (game.player1.score > game.player2.score)
            anim_manager.add_score_animation('p1', prev_p1_score, game.player1.score, 
                                            score_x, SCREEN_HEIGHT // 2 + 50, lead_burst=p1_lead_gain)
            prev_p1_score = game.player1.score
        
        if game.player2.score != prev_p2_score:
            score_x = SCREEN_WIDTH - int(SCREEN_WIDTH * 0.052)
            p2_lead_gain = (prev_p2_before <= prev_p1_before) and (game.player2.score > game.player1.score)
            anim_manager.add_score_animation('p2', prev_p2_score, game.player2.score,
                                            score_x, SCREEN_HEIGHT // 2 - 50, lead_burst=p2_lead_gain)
            prev_p2_score = game.player2.score

        drag_hover_highlight = None
        drag_row_highlights = []
        if dragging_card and game.game_state == "playing":
            mouse_pos = pygame.mouse.get_pos()
            hover_alpha = 80
            ability = dragging_card.ability or ""
            if dragging_card.row == "weather":
                hovered_row_name, hovered_rect = get_row_under_position(mouse_pos)
                target_rows = get_weather_target_rows(dragging_card, hovered_row_name)
                for row_name in target_rows:
                    color = get_row_color(row_name)
                    player_rect = PLAYER_ROW_RECTS.get(row_name)
                    opponent_rect = OPPONENT_ROW_RECTS.get(row_name)
                    if player_rect:
                        drag_row_highlights.append({"rect": player_rect, "color": color, "alpha": 70})
                    if opponent_rect:
                        drag_row_highlights.append({"rect": opponent_rect, "color": color, "alpha": 70})
                if hovered_rect:
                    drag_hover_highlight = {"rect": hovered_rect, "color": get_row_color(hovered_row_name or "weather"), "alpha": 120}
            elif dragging_card.row == "special" and "Command Network" in ability:
                for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
                    drag_row_highlights.append({"rect": slot_rect, "color": (255, 215, 0), "alpha": 80})
                    if slot_rect.collidepoint(mouse_pos):
                        drag_hover_highlight = {"rect": slot_rect, "color": (255, 215, 0), "alpha": 140}
            elif dragging_card.row == "special":
                for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                    for row_name, rect in rects.items():
                        if rect.collidepoint(mouse_pos):
                            drag_hover_highlight = {"rect": rect, "color": get_row_color(row_name), "alpha": 100}
                            break
                    if drag_hover_highlight:
                        break
            else:
                is_spy = "Deep Cover Agent" in ability
                target_rects = OPPONENT_ROW_RECTS if is_spy else PLAYER_ROW_RECTS
                for row_name, rect in target_rects.items():
                    if rect.collidepoint(mouse_pos):
                        color = (255, 120, 120) if is_spy else get_row_color(row_name)
                        drag_hover_highlight = {"rect": rect, "color": color, "alpha": hover_alpha}
                        break

        drag_visual_state = {
            "trail": drag_trail,
            "velocity": drag_velocity,
            "pickup_boost": drag_pickup_flash,
            "pulse": drag_pulse
        }

        # --- Drawing ---
        screen.blit(assets["board"], (0, 0))
        
        # Draw lane separators (horizontal lines between rows)
        # These lines match the actual row rectangles used for card placement
        separator_color = (100, 150, 200, 150)  # Semi-transparent blue
        separator_width = 3
        glow_color = (150, 200, 255, 80)
        
        # Draw separator at the bottom of each row rect
        all_row_rects = list(OPPONENT_ROW_RECTS.values()) + list(PLAYER_ROW_RECTS.values())
        
        for row_rect in all_row_rects:
            y_pos = row_rect.bottom  # Bottom edge of each row rectangle
            
            # Shift opponent's lines down for better visibility
            if row_rect in OPPONENT_ROW_RECTS.values():
                y_pos += 8  # Adds a small gap below opponent cards
            
            # Glow effect (slightly above the main line)
            pygame.draw.line(screen, glow_color, (0, y_pos - 2), (SCREEN_WIDTH, y_pos - 2), 1)
            pygame.draw.line(screen, glow_color, (0, y_pos - 1), (SCREEN_WIDTH, y_pos - 1), 1)
            
            # Main separator line
            pygame.draw.line(screen, separator_color, (0, y_pos), (SCREEN_WIDTH, y_pos), separator_width)
            
            # Glow effect (slightly below the main line)
            pygame.draw.line(screen, glow_color, (0, y_pos + separator_width), (SCREEN_WIDTH, y_pos + separator_width), 1)
            pygame.draw.line(screen, glow_color, (0, y_pos + separator_width + 1), (SCREEN_WIDTH, y_pos + separator_width + 1), 1)
        
        # Draw ambient background effects
        ambient_effects.draw(screen)
        
        if game.game_state == "mulligan":
            # Draw mulligan UI
            mulligan_title = SCORE_FONT.render("Select up to 2 cards to redraw", True, WHITE)
            screen.blit(mulligan_title, (SCREEN_WIDTH // 2 - mulligan_title.get_width() // 2, int(SCREEN_HEIGHT * 0.019)))
            mulligan_subtitle = UI_FONT.render("Click cards to select/deselect, then click Redraw button", True, WHITE)
            screen.blit(mulligan_subtitle, (SCREEN_WIDTH // 2 - mulligan_subtitle.get_width() // 2, int(SCREEN_HEIGHT * 0.046)))
            draw_hand(
                screen,
                game.player1,
                None,
                mulligan_selected,
                dragging_card=None,
                hovered_card=hovered_card,
                hover_scale=card_hover_scale
            )
            draw_mulligan_button(screen, mulligan_selected)
        elif game.game_state == "game_over":
            # Draw game over screen
            game_over_text = SCORE_FONT.render("GAME OVER", True, WHITE)
            screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
            
            if game.winner:
                winner_text = SCORE_FONT.render(f"{game.winner.name} WINS!", True, (100, 255, 100))
                screen.blit(winner_text, (SCREEN_WIDTH // 2 - winner_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
                
                # Record game result and show rewards
                if not hasattr(game, 'reward_shown'):
                    game.reward_shown = True
                    
                    # Record win/loss using persistence system
                    player_won = (game.winner == game.player1)
                    
                    if player_won:
                        record_victory(player_faction)
                        
                        # FIRST: Check for leader unlock (every 3 consecutive wins)
                        persistence = get_persistence()
                        consecutive_wins = persistence.get_consecutive_wins()
                        
                        if consecutive_wins > 0 and consecutive_wins % 3 == 0:
                            # Show leader reward screen
                            unlocked_leader = show_leader_reward_screen(screen, unlock_system, player_faction)
                            if unlocked_leader:
                                leader_name = unlocked_leader.get('name', 'Unknown Leader')
                                game.unlock_message = UI_FONT.render(f"NEW LEADER UNLOCKED: {leader_name}!", True, (255, 215, 0))
                                game.streak_message = UI_FONT.render(f"3 Win Streak! Leader unlocked!", True, (255, 150, 50))
                        
                        # SECOND: Always show card reward screen (every win)
                        unlock_system.record_game_result(True)
                        unlocked_card = show_card_reward_screen(screen, unlock_system, faction=player_faction)
                        if unlocked_card:
                            # Add unlocked card to player's deck
                            persistence = get_persistence()
                            persistence.unlock_card(unlocked_card)
                            current_deck = persistence.get_deck(player_faction)
                            current_cards = current_deck.get("cards", [])
                            if unlocked_card not in current_cards:
                                current_cards.append(unlocked_card)
                                persistence.set_deck(player_faction, current_deck.get("leader", ""), current_cards)
                                print(f"✓ Card {unlocked_card} added to {player_faction} deck")
                            
                            card_msg = UI_FONT.render(f"Unlocked: {UNLOCKABLE_CARDS[unlocked_card]['name']}!", True, (255, 215, 0))
                            if hasattr(game, 'unlock_message'):
                                game.unlock_message2 = card_msg
                            else:
                                game.unlock_message = card_msg
                        
                        # Show win streak progress
                        if not hasattr(game, 'streak_message'):
                            persistence = get_persistence()
                            streak = persistence.get_consecutive_wins()
                            if streak > 0:
                                remaining = 3 - (streak % 3)
                                if remaining == 3:
                                    remaining = 0  # Just got a leader unlock
                                game.streak_message = UI_FONT.render(f"Win Streak: {streak}! ({remaining} more for leader unlock)", True, (100, 255, 100))
                    else:
                        record_defeat(player_faction)
                        unlock_system.record_game_result(False)
            
            score_text = UI_FONT.render(f"Final Score: {game.player1.name} {game.player1.rounds_won} - {game.player2.rounds_won} {game.player2.name}", True, WHITE)
            screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2))
            
            # Show unlock messages if exist
            y_offset = 30
            if hasattr(game, 'unlock_message'):
                screen.blit(game.unlock_message, (SCREEN_WIDTH // 2 - game.unlock_message.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset))
                y_offset += 35
            if hasattr(game, 'unlock_message2'):
                screen.blit(game.unlock_message2, (SCREEN_WIDTH // 2 - game.unlock_message2.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset))
                y_offset += 35
            if hasattr(game, 'streak_message'):
                screen.blit(game.streak_message, (SCREEN_WIDTH // 2 - game.streak_message.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset))
                y_offset += 35
            
            restart_text = UI_FONT.render("Press R to restart or ESC to quit", True, WHITE)
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset + 15))
        else:
            # Draw normal game UI
            draw_board(screen, game, selected_card, dragging_card=dragging_card,
                       drag_hover_highlight=drag_hover_highlight, drag_row_highlights=drag_row_highlights)
            draw_scores(screen, game, anim_manager)
            draw_pass_button(screen, game)
            draw_hand(
                screen,
                game.player1,
                selected_card,
                dragging_card=dragging_card,
                hovered_card=hovered_card,
                hover_scale=card_hover_scale,
                drag_visuals=drag_visual_state
            )
            draw_opponent_hand(screen, game.player2)  # Show opponent's hand as card backs
            
            # Draw AI turn animation on top of opponent hand
            if ai_turn_in_progress:
                # Get opponent hand area for animation
                total_cards = len(game.player2.hand)
                if total_cards > 0:
                    card_spacing = int(CARD_WIDTH * 0.125)
                    total_width = total_cards * CARD_WIDTH + (total_cards - 1) * card_spacing
                    start_x = (SCREEN_WIDTH - total_width) // 2 if total_width < SCREEN_WIDTH else 20
                    opponent_hand_area = pygame.Rect(start_x, 10, total_width, CARD_HEIGHT)
                    ai_turn_anim.draw(screen, UI_FONT, opponent_hand_area)
            
            # Show current turn indicator (top center)
            if game.current_player == game.player1:
                turn_text = UI_FONT.render("YOUR TURN", True, (100, 255, 100))
            else:
                turn_text = UI_FONT.render("OPPONENT'S TURN", True, (255, 100, 100))
            turn_rect = turn_text.get_rect(center=(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.03))) # Increased from 0.019
            screen.blit(turn_text, turn_rect)
            
            # Show round number (next to turn indicator)
            round_text = UI_FONT.render(f"Round {game.round_number}", True, WHITE)
            round_rect = round_text.get_rect(center=(SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.06))) # Increased from 0.046
            screen.blit(round_text, round_rect)
            
            # Leader portraits - AI top-left, Player bottom-left
            ai_leader_x = 20
            ai_leader_y = 20
            ai_leader_rect = draw_leader_portrait(screen, game.player2, ai_leader_x, ai_leader_y, 100, 140)
            
            player_leader_x = 20
            player_leader_y = SCREEN_HEIGHT - HAND_Y_OFFSET + 20 # Position inside the hand area
            player_leader_rect = draw_leader_portrait(screen, game.player1, player_leader_x, player_leader_y, 100, 140)
            
            # Iris button (Tau'ri only, below "LEADER" text)
            # LEADER text is at player_leader_rect.bottom + 15, so button goes below that
            iris_button_rect = draw_iris_button(screen, game.player1, player_leader_rect.centerx - 50, player_leader_rect.bottom + 40)
            
            # Ring Transportation button (Goa'uld only, same position as Iris)
            ring_transport_button_rect = draw_ring_transport_button(screen, game.player1, player_leader_rect.centerx - 60, player_leader_rect.bottom + 40)
            
            # Faction Power UI - Player (bottom right area)
            if game.player1.faction_power:
                player_faction_ui.draw(screen, game.player1.faction_power, is_player=True)
            
            # Faction Power UI - AI (top right area) - show but don't allow interaction
            if game.player2.faction_power:
                ai_faction_ui.draw(screen, game.player2.faction_power, is_player=False)
            
            # Leader ability boxes - centered, AI top, Player bottom
            ability_box_width = 400
            ability_box_height = 60
            
            # AI leader ability (top center)
            ai_ability_x = (SCREEN_WIDTH - ability_box_width) // 2
            ai_ability_y = 20
            ai_ability_rect = draw_leader_ability_box(screen, game.player2, ai_ability_x, ai_ability_y, 
                                   ability_box_width, ability_box_height, is_opponent=True)
            
            # Player leader ability (bottom center, above hand)
            player_ability_x = (SCREEN_WIDTH - ability_box_width) // 2
            player_ability_y = SCREEN_HEIGHT - HAND_Y_OFFSET - 80
            player_ability_rect = draw_leader_ability_box(screen, game.player1, player_ability_x, player_ability_y, 
                                   ability_box_width, ability_box_height, is_opponent=False)
            
            # Card counters - right side, vertical
            counter_x = SCREEN_WIDTH - 260
            counter_y_player = SCREEN_HEIGHT - HAND_Y_OFFSET - 190
            counter_y_opponent = 70
            discard_rect = draw_card_counters(screen, game.player1, counter_x, counter_y_player, is_player=True)
            draw_card_counters(screen, game.player2, counter_x, counter_y_opponent, is_player=False)
        
        # Draw animations and effects on top of everything
        anim_manager.draw_effects(screen)
        anim_manager.draw_weather(screen)
        
        # Draw Iris Power effect (full-screen cinematic)
        if faction_power_effect:
            faction_power_effect.draw(screen)
        
        # Draw Ring Transportation animation
        if ring_transport_animation:
            ring_transport_animation.draw(screen)
        
        # Draw visual feedback for ring transport selection mode
        if ring_transport_selection:
            # Dim the screen slightly
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))
            
            # Draw instruction text
            hint_font = pygame.font.Font(None, 48)
            hint_text = hint_font.render("Click a CLOSE COMBAT unit to return to hand", True, (255, 200, 100))
            hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
            
            # Draw text shadow
            shadow_text = hint_font.render("Click a CLOSE COMBAT unit to return to hand", True, (0, 0, 0))
            screen.blit(shadow_text, (hint_rect.x + 3, hint_rect.y + 3))
            screen.blit(hint_text, hint_rect)
            
            # Highlight ONLY close combat cards on board with golden glow
            row_cards = game.player1.board.get("close", [])
            for card in row_cards:
                if hasattr(card, 'rect'):
                    # Golden glow around selectable cards
                    glow_surf = pygame.Surface((card.rect.width + 20, card.rect.height + 20), pygame.SRCALPHA)
                    glow_alpha = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.005))
                    pygame.draw.rect(glow_surf, (255, 200, 100, glow_alpha), glow_surf.get_rect(), border_radius=10)
                    screen.blit(glow_surf, (card.rect.x - 10, card.rect.y - 10))
        
        # Draw visual feedback when dragging Ring Transport over valid targets
        if dragging_card and "Ring Transport" in (dragging_card.ability or ""):
            # Highlight valid targets
            for card, rect in decoy_valid_targets:
                # Golden glow around valid cards
                glow_surf = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
                glow_alpha = int(100 + 80 * math.sin(pygame.time.get_ticks() * 0.008))
                pygame.draw.rect(glow_surf, (100, 200, 255, glow_alpha), glow_surf.get_rect(), border_radius=8)
                screen.blit(glow_surf, (rect.x - 10, rect.y - 10))
            
            # Draw laser beam to hovered target
            if decoy_drag_target and hasattr(decoy_drag_target, 'rect'):
                # Animated laser beam from dragged card to target
                beam_start = (dragging_card.rect.centerx, dragging_card.rect.centery)
                beam_end = (decoy_drag_target.rect.centerx, decoy_drag_target.rect.centery)
                
                # Pulsing beam effect
                pulse = math.sin(pygame.time.get_ticks() * 0.01) * 0.3 + 0.7
                beam_color = (int(150 * pulse), int(220 * pulse), int(255 * pulse))
                beam_width = int(4 + 2 * math.sin(pygame.time.get_ticks() * 0.01))
                
                # Draw main beam
                pygame.draw.line(screen, beam_color, beam_start, beam_end, beam_width)
                
                # Draw glow along the beam
                glow_surf = pygame.Surface((abs(beam_end[0] - beam_start[0]) + 40, 
                                           abs(beam_end[1] - beam_start[1]) + 40), pygame.SRCALPHA)
                glow_start = (20, 20) if beam_start[0] < beam_end[0] else (glow_surf.get_width() - 20, 20)
                glow_end = (glow_surf.get_width() - 20, glow_surf.get_height() - 20) if beam_start[0] < beam_end[0] else (20, glow_surf.get_height() - 20)
                pygame.draw.line(glow_surf, (*beam_color, int(100 * pulse)), glow_start, glow_end, beam_width + 6)
                screen.blit(glow_surf, (min(beam_start[0], beam_end[0]) - 20, min(beam_start[1], beam_end[1]) - 20))
                
                # Draw glowing circle at target
                target_glow_size = int(20 + 10 * math.sin(pygame.time.get_ticks() * 0.015))
                target_glow = pygame.Surface((target_glow_size * 2, target_glow_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(target_glow, (*beam_color, int(150 * pulse)), 
                                 (target_glow_size, target_glow_size), target_glow_size)
                screen.blit(target_glow, (decoy_drag_target.rect.centerx - target_glow_size, 
                                         decoy_drag_target.rect.centery - target_glow_size))
        
        # Draw card inspection overlay (on top of EVERYTHING)
        if inspected_card:
            draw_card_inspection_overlay(screen, inspected_card, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        if inspected_leader:
            draw_leader_inspection_overlay(screen, inspected_leader, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Medical Evac selection overlay
        medic_card_rects = []
        if medic_selection_mode:
            medic_card_rects = draw_medic_selection_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Handle clicks on medic cards
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = pygame.mouse.get_pressed()[0]
            
            if mouse_clicked:
                for card, rect in medic_card_rects:
                    if rect.collidepoint(mouse_pos):
                        # Player selected this card to revive
                        game.trigger_medic(game.player1, card)
                        game.player1.calculate_score()
                        game.player2.calculate_score()
                        game.switch_turn()
                        medic_selection_mode = False
                        medic_card_played = None
                        pygame.time.wait(200)  # Small delay to prevent double-click
                        break
        
        # Ring Transport selection overlay
        decoy_card_rects = []
        if decoy_selection_mode:
            decoy_card_rects = draw_decoy_selection_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Handle clicks on decoy cards
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = pygame.mouse.get_pressed()[0]
            
            if mouse_clicked:
                for card, rect in decoy_card_rects:
                    if rect.collidepoint(mouse_pos):
                        # Player selected this card to return to hand
                        if game.apply_decoy(card):
                            game.player1.calculate_score()
                            game.player2.calculate_score()
                            game.switch_turn()
                            decoy_selection_mode = False
                            decoy_card_played = None
                            pygame.time.wait(200)  # Small delay to prevent double-click
                        break
        
        # Jonas Quinn peek overlay
        if jonas_peek_active:
            draw_jonas_peek_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Handle click to close
            if pygame.mouse.get_pressed()[0]:
                jonas_peek_active = False
                pygame.time.wait(200)
        
        # Ba'al Clone selection overlay
        baal_card_rects = []
        if baal_clone_selection:
            baal_card_rects = draw_baal_clone_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in baal_card_rects:
                    if rect.collidepoint(mouse_pos):
                        # Clone this card
                        import copy
                        cloned_card = copy.deepcopy(card)
                        # Find which row the original is in
                        for row_name, row_cards in game.player1.board.items():
                            if card in row_cards:
                                game.player1.board[row_name].append(cloned_card)
                                break
                        game.player1.calculate_score()
                        baal_clone_selection = False
                        pygame.time.wait(200)
                        break
        
        # Vala selection overlay
        vala_card_rects = []
        if vala_selection_mode:
            vala_card_rects = draw_vala_selection_overlay(screen, vala_cards_to_choose, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in vala_card_rects:
                    if rect.collidepoint(mouse_pos):
                        # Add chosen card to hand
                        game.player1.hand.append(card)
                        # Return unchosen cards to deck
                        for c in vala_cards_to_choose:
                            if c != card:
                                game.player1.deck.append(c)
                        random.shuffle(game.player1.deck)
                        vala_selection_mode = False
                        vala_cards_to_choose = []
                        pygame.time.wait(200)
                        break
        
        # Thor move mode - simple visual indicator
        if thor_move_mode:
            # Draw indicator
            indicator_font = pygame.font.Font(None, 48)
            indicator_text = indicator_font.render("THOR: Click a unit to move, then click destination row", True, (50, 200, 150))
            indicator_rect = indicator_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
            
            # Semi-transparent background
            bg_surf = pygame.Surface((indicator_rect.width + 40, indicator_rect.height + 20), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 180))
            screen.blit(bg_surf, (indicator_rect.x - 20, indicator_rect.y - 10))
            screen.blit(indicator_text, indicator_rect)
            
            # Handle clicks
            if pygame.mouse.get_pressed()[0]:
                mouse_pos = pygame.mouse.get_pos()
                
                if not thor_selected_unit:
                    # First click: select unit
                    for row_cards in game.player1.board.values():
                        for card in row_cards:
                            if hasattr(card, 'rect') and card.rect.collidepoint(mouse_pos):
                                thor_selected_unit = card
                                pygame.time.wait(200)
                                break
                        if thor_selected_unit:
                            break
                else:
                    # Second click: select destination row
                    for row_name, rect in PLAYER_ROW_RECTS.items():
                        if rect.collidepoint(mouse_pos):
                            # Move the unit
                            for source_row, row_cards in game.player1.board.items():
                                if thor_selected_unit in row_cards:
                                    row_cards.remove(thor_selected_unit)
                                    game.player1.board[row_name].append(thor_selected_unit)
                                    game.player1.calculate_score()
                                    thor_move_mode = False
                                    thor_selected_unit = None
                                    pygame.time.wait(200)
                                    break
                            break
        
        # Discard pile viewer overlay
        if viewing_discard:
            draw_discard_viewer(screen, game.player1.discard_pile, SCREEN_WIDTH, SCREEN_HEIGHT, discard_scroll)
        
        # Pause menu overlay
        if paused:
            # Semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            
            # Pause menu
            menu_width = 500
            menu_height = 400
            menu_x = (SCREEN_WIDTH - menu_width) // 2
            menu_y = (SCREEN_HEIGHT - menu_height) // 2
            
            # Menu background
            pygame.draw.rect(screen, (30, 30, 40), (menu_x, menu_y, menu_width, menu_height), border_radius=15)
            pygame.draw.rect(screen, (100, 150, 200), (menu_x, menu_y, menu_width, menu_height), 5, border_radius=15)
            
            # Title
            pause_font = pygame.font.SysFont("Arial", 56, bold=True)
            title_text = pause_font.render("PAUSED", True, (200, 200, 200))
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, menu_y + 80))
            screen.blit(title_text, title_rect)
            
            # Buttons
            button_font = pygame.font.SysFont("Arial", 32, bold=True)
            button_width = 350
            button_height = 60
            button_x = (SCREEN_WIDTH - button_width) // 2
            
            # Resume button
            resume_button = pygame.Rect(button_x, menu_y + 160, button_width, button_height)
            pygame.draw.rect(screen, (50, 180, 50), resume_button, border_radius=10)
            resume_text = button_font.render("RESUME (ESC)", True, (255, 255, 255))
            resume_rect = resume_text.get_rect(center=resume_button.center)
            screen.blit(resume_text, resume_rect)
            
            # Main Menu button
            main_menu_button = pygame.Rect(button_x, menu_y + 240, button_width, button_height)
            pygame.draw.rect(screen, (180, 140, 50), main_menu_button, border_radius=10)
            menu_text = button_font.render("MAIN MENU", True, (255, 255, 255))
            menu_rect = menu_text.get_rect(center=main_menu_button.center)
            screen.blit(menu_text, menu_rect)
            
            # Quit button
            quit_button = pygame.Rect(button_x, menu_y + 320, button_width, button_height)
            pygame.draw.rect(screen, (180, 50, 50), quit_button, border_radius=10)
            quit_text = button_font.render("QUIT GAME", True, (255, 255, 255))
            quit_rect = quit_text.get_rect(center=quit_button.center)
            screen.blit(quit_text, quit_rect)
            
            # Handle pause menu clicks
            if event and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if resume_button.collidepoint(mouse_pos):
                    paused = False
                elif main_menu_button.collidepoint(mouse_pos):
                    # Return to main menu
                    main()
                    return
                elif quit_button.collidepoint(mouse_pos):
                    pygame.quit()
                    sys.exit()

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
