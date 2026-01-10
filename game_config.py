import pygame
import display_manager
from cards import (
    FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
    FACTION_LUCIAN, FACTION_ASGARD
)

# Colors
WHITE = (255, 255, 255)
PLAYER_HAND_BG = (40, 40, 50, 150) # Semi-transparent
BLACK = (0, 0, 0)
GOLD = (255, 215, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 150, 255)

ROW_COLORS = {
    "close": (255, 100, 100),    # Red
    "ranged": (100, 100, 255),   # Blue
    "siege": (100, 255, 100),    # Green
    "agile": (255, 255, 100),    # Yellow
    "special": (255, 215, 0),    # Gold
    "weather": (150, 150, 255),  # Light blue
}

FACTION_GLOW_COLORS = {
    FACTION_TAURI: (0x2D, 0x50, 0xAA),
    FACTION_GOAULD: (0xA0, 0x19, 0x1E),
    FACTION_JAFFA: (0xC8, 0xA0, 0x28),
    FACTION_LUCIAN: (0xC8, 0x64, 0xFF),
    FACTION_ASGARD: (0x64, 0xFF, 0xFF),
}

def get_row_color(row_name):
    """Return the theme color for a given row type."""
    return ROW_COLORS.get(row_name, (200, 200, 255))

# Layout System
COLUMN_RANGES = {
    "leader": (0.00, 0.12),
    "horn": (0.12, 0.20),
    "playfield": (0.20, 0.85),
    "hud": (0.85, 1.00),
}

ROW_RANGES = {
    "opponent_hand": (0.03, 0.11),
    "opponent_siege": (0.12, 0.215),
    "opponent_ranged": (0.23, 0.325),
    "opponent_close": (0.34, 0.435),
    "weather": (0.435, 0.505),
    "player_close": (0.515, 0.61),
    "player_ranged": (0.625, 0.72),
    "player_siege": (0.735, 0.83),
    "player_hand": (0.84, 0.91),
    "command_bar": (0.91, 0.97),
}

def pct_x(value: float) -> int:
    return int(display_manager.SCREEN_WIDTH * value)

def pct_y(value: float) -> int:
    return int(display_manager.SCREEN_HEIGHT * value)

def rect_from_percent(x_range, y_range):
    return pygame.Rect(
        pct_x(x_range[0]),
        pct_y(y_range[0]),
        max(1, pct_x(x_range[1] - x_range[0])),
        max(1, pct_y(y_range[1] - y_range[0])),
    )

# Calculated Dimensions (Initialized to default)
SCORE_FONT = None
UI_FONT = None
POWER_FONT = None
ROW_FONT = None

CARD_WIDTH = 0
CARD_HEIGHT = 0
HISTORY_ENTRY_HEIGHT = 0

MULLIGAN_CARD_SCALE = 0.8
MULLIGAN_CARD_WIDTH = 0
MULLIGAN_CARD_HEIGHT = 0

PLAYFIELD_RANGE = None
opponent_hand_area_y = 0
player_hand_area_y = 0
OPPONENT_HAND_HEIGHT = 0
PLAYER_HAND_HEIGHT = 0
COMMAND_BAR_Y = 0
COMMAND_BAR_HEIGHT = 0
weather_y = 0
WEATHER_ZONE_HEIGHT = 0

PLAYER_ROW_RECTS = {}
OPPONENT_ROW_RECTS = {}
WEATHER_SLOT_RECTS = {}
PLAYER_HORN_SLOT_RECTS = {}
OPPONENT_HORN_SLOT_RECTS = {}

PLAYFIELD_LEFT = 0
PLAYFIELD_WIDTH = 0
HUD_LEFT = 0
HUD_WIDTH = 0
LEADER_COLUMN_X = 0
LEADER_COLUMN_WIDTH = 0
LEADER_COLUMN_HEIGHT = 0
LEADER_SECTION_HEIGHT = 0
LEADER_TOP_RECT = None
LEADER_BOTTOM_RECT = None
HORN_COLUMN_X = 0
HORN_COLUMN_WIDTH = 0
HAND_REGION_LEFT = 0
HAND_REGION_WIDTH = 0
HUD_PASS_BUTTON_RECT = None

def recalculate_dimensions():
    """Call this after display initialization to set up fonts and dimensions."""
    global SCORE_FONT, UI_FONT, POWER_FONT, ROW_FONT
    global CARD_WIDTH, CARD_HEIGHT, HISTORY_ENTRY_HEIGHT
    global MULLIGAN_CARD_SCALE, MULLIGAN_CARD_WIDTH, MULLIGAN_CARD_HEIGHT
    global PLAYFIELD_RANGE, opponent_hand_area_y, player_hand_area_y
    global OPPONENT_HAND_HEIGHT, PLAYER_HAND_HEIGHT, COMMAND_BAR_Y, COMMAND_BAR_HEIGHT
    global weather_y, WEATHER_ZONE_HEIGHT
    global PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS, WEATHER_SLOT_RECTS
    global PLAYER_HORN_SLOT_RECTS, OPPONENT_HORN_SLOT_RECTS
    global PLAYFIELD_LEFT, PLAYFIELD_WIDTH, HUD_LEFT, HUD_WIDTH
    global LEADER_COLUMN_X, LEADER_COLUMN_WIDTH, LEADER_COLUMN_HEIGHT, LEADER_SECTION_HEIGHT
    global LEADER_TOP_RECT, LEADER_BOTTOM_RECT, HORN_COLUMN_X, HORN_COLUMN_WIDTH
    global HAND_REGION_LEFT, HAND_REGION_WIDTH, HUD_PASS_BUTTON_RECT

    sf = display_manager.SCALE_FACTOR
    sh = display_manager.SCREEN_HEIGHT
    sw = display_manager.SCREEN_WIDTH

    # Fonts
    SCORE_FONT = pygame.font.SysFont("Arial", int(48 * sf), bold=True)
    UI_FONT = pygame.font.SysFont("Arial", int(28 * sf))
    POWER_FONT = pygame.font.SysFont("Arial", int(32 * sf), bold=True)
    ROW_FONT = pygame.font.SysFont("Arial", max(16, int(16 * sf)), bold=True)

    # Card & Board dimensions
    CARD_WIDTH = int(sh * 0.08)
    CARD_HEIGHT = int(sh * 0.11)
    HISTORY_ENTRY_HEIGHT = max(36, int(CARD_HEIGHT * 0.3))

    # Mulligan card scaling
    MULLIGAN_CARD_SCALE = 0.8
    MULLIGAN_CARD_WIDTH  = int(CARD_WIDTH * MULLIGAN_CARD_SCALE)
    MULLIGAN_CARD_HEIGHT = int(CARD_HEIGHT * MULLIGAN_CARD_SCALE)

    # Layout Zones
    PLAYFIELD_RANGE = COLUMN_RANGES["playfield"]
    opponent_hand_area_y = pct_y(ROW_RANGES["opponent_hand"][0])
    player_hand_area_y = pct_y(ROW_RANGES["player_hand"][0])
    OPPONENT_HAND_HEIGHT = pct_y(ROW_RANGES["opponent_hand"][1] - ROW_RANGES["opponent_hand"][0])
    PLAYER_HAND_HEIGHT = pct_y(ROW_RANGES["player_hand"][1] - ROW_RANGES["player_hand"][0])
    COMMAND_BAR_Y = pct_y(ROW_RANGES["command_bar"][0])
    COMMAND_BAR_HEIGHT = max(1, pct_y(ROW_RANGES["command_bar"][1] - ROW_RANGES["command_bar"][0]))
    weather_y = pct_y(ROW_RANGES["weather"][0])
    WEATHER_ZONE_HEIGHT = max(1, pct_y(ROW_RANGES["weather"][1] - ROW_RANGES["weather"][0]))

    # Rects
    PLAYER_ROW_RECTS = {
        "close":  rect_from_percent(PLAYFIELD_RANGE, ROW_RANGES["player_close"]),
        "ranged": rect_from_percent(PLAYFIELD_RANGE, ROW_RANGES["player_ranged"]),
        "siege":  rect_from_percent(PLAYFIELD_RANGE, ROW_RANGES["player_siege"]),
    }
    OPPONENT_ROW_RECTS = {
        "close":  rect_from_percent(PLAYFIELD_RANGE, ROW_RANGES["opponent_close"]),
        "ranged": rect_from_percent(PLAYFIELD_RANGE, ROW_RANGES["opponent_ranged"]),
        "siege":  rect_from_percent(PLAYFIELD_RANGE, ROW_RANGES["opponent_siege"]),
    }

    PLAYFIELD_LEFT = PLAYER_ROW_RECTS["close"].x
    PLAYFIELD_WIDTH = PLAYER_ROW_RECTS["close"].width
    HUD_LEFT = pct_x(COLUMN_RANGES["hud"][0])
    HUD_WIDTH = max(1, pct_x(COLUMN_RANGES["hud"][1] - COLUMN_RANGES["hud"][0]))
    LEADER_COLUMN_X = pct_x(COLUMN_RANGES["leader"][0])
    LEADER_COLUMN_WIDTH = max(1, pct_x(COLUMN_RANGES["leader"][1] - COLUMN_RANGES["leader"][0]))
    LEADER_COLUMN_HEIGHT = sh
    LEADER_SECTION_HEIGHT = LEADER_COLUMN_HEIGHT // 2
    LEADER_TOP_RECT = pygame.Rect(LEADER_COLUMN_X, 0, LEADER_COLUMN_WIDTH, LEADER_SECTION_HEIGHT)
    LEADER_BOTTOM_RECT = pygame.Rect(LEADER_COLUMN_X, sh - LEADER_SECTION_HEIGHT, LEADER_COLUMN_WIDTH, LEADER_SECTION_HEIGHT)
    HORN_COLUMN_X = pct_x(COLUMN_RANGES["horn"][0])
    HORN_COLUMN_WIDTH = max(1, pct_x(COLUMN_RANGES["horn"][1] - COLUMN_RANGES["horn"][0]))
    HAND_REGION_LEFT = pct_x(0.15)
    HAND_REGION_WIDTH = max(1, pct_x(0.70))

    # Slots
    WEATHER_SLOT_X = pct_x(0.02)
    HORN_SLOT_WIDTH = min(max(1, int(CARD_WIDTH * 1.1)), HORN_COLUMN_WIDTH)
    HORN_SLOT_X = HORN_COLUMN_X + (HORN_COLUMN_WIDTH - HORN_SLOT_WIDTH) // 2

    WEATHER_SLOT_RECTS = {}
    for idx, shared_row in enumerate(["siege", "ranged", "close"]):
        slot_center_y = weather_y + int(((idx + 0.5) / 3.0) * WEATHER_ZONE_HEIGHT)
        WEATHER_SLOT_RECTS[shared_row] = pygame.Rect(
            WEATHER_SLOT_X, slot_center_y - CARD_HEIGHT // 2, CARD_WIDTH, CARD_HEIGHT
        )

    PLAYER_HORN_SLOT_RECTS = {}
    for rname, rect in PLAYER_ROW_RECTS.items():
        PLAYER_HORN_SLOT_RECTS[rname] = pygame.Rect(HORN_SLOT_X, rect.y, HORN_SLOT_WIDTH, rect.height)

    OPPONENT_HORN_SLOT_RECTS = {}
    for rname, rect in OPPONENT_ROW_RECTS.items():
        OPPONENT_HORN_SLOT_RECTS[rname] = pygame.Rect(HORN_SLOT_X, rect.y, HORN_SLOT_WIDTH, rect.height)
    
    # HUD Pass Button (calculated dynamically later in main usually, but better to define here if possible)
    # In main.py it was not explicitly assigned to global constant immediately, but HUD_WIDTH is used.
    # We'll leave HUD_PASS_BUTTON_RECT as None for main to set or logic to use HUD coordinates.