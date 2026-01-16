import pygame
import display_manager
from cards import (
    FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
    FACTION_LUCIAN, FACTION_ASGARD
)

# ============================================================================
# ANIMATION DURATIONS (milliseconds)
# ============================================================================
ANIM_INSTANT = 300           # Quick movements, basic transitions
ANIM_SHORT = 400             # Short animations (fades, small effects)
ANIM_CARD_FLIP = 500         # Card flip/reveal
ANIM_MEDIUM = 600            # Score pops, card movements
ANIM_CARD_PLAY = 650         # Card being played animation
ANIM_STARGATE = 800          # Stargate activation effect
ANIM_CARD_REVEAL = 900       # Card reveal, row animations
ANIM_AMBIENT = 1000          # Ambient glows, loops
ANIM_AI_PLAY = 1200          # AI card play (slower for readability)
ANIM_MAJOR_EFFECT = 1500     # Major effects (explosions, big reveals)
ANIM_PERSISTENT = 2500       # Long-running persistent effects

# ============================================================================
# HAND CARD INTERACTION PARAMETERS
# ============================================================================
HAND_CARD_HOVER_LIFT = 35    # Pixels to lift card on hover (base, scaled)
DRAG_LIFT_MULTIPLIER = 0.35  # Multiplier for drag speed -> lift effect
INACTIVE_LANE_ALPHA = 40     # Alpha transparency for inactive lanes (0-255)
PASS_BUTTON_PULSE_RATE = 500 # Milliseconds for pass button glow pulse cycle

# ============================================================================
# PARTICLE & EFFECT DEFAULTS
# ============================================================================
PARTICLE_COUNT_DEFAULTS = {
    "stargate": 30,          # Stargate activation particles
    "ability_burst": 20,     # Ability trigger burst particles
    "card_reveal": 15,       # Card reveal sparkle particles
    "score_pop": 12,         # Score change celebration particles
}

# ============================================================================
# TIMING & DELAYS (milliseconds)
# ============================================================================
TYPING_TIMEOUT = 2000        # Chat typing indicator timeout
POPUP_DISPLAY_TIME = 5000    # Info popup display duration
MULLIGAN_TIMEOUT = 30000     # Mulligan phase timeout
KEY_REPEAT_DELAY = 300       # Keyboard repeat initial delay
KEY_REPEAT_INTERVAL = 50     # Keyboard repeat interval

# ============================================================================
# FONT SIZES (base sizes, scaled by SCALE_FACTOR)
# ============================================================================
FONT_SIZE_TINY = 14          # Small labels, timestamps
FONT_SIZE_SMALL = 16         # Body text, descriptions
FONT_SIZE_MEDIUM = 20        # Titles, headings
FONT_SIZE_CHAT = 22          # Chat messages
FONT_SIZE_UI = 24            # UI elements, card names
FONT_SIZE_TITLE = 28         # Section titles
FONT_SIZE_SUBTITLE = 30      # Large subtitles
FONT_SIZE_HEADER = 36        # Overlay headers
FONT_SIZE_LARGE = 48         # Score displays
FONT_SIZE_HUGE = 60          # Major announcements
FONT_SIZE_GIANT = 72         # Victory/defeat screens

# ============================================================================
# UI COLORS - Extended Palette
# ============================================================================
# Basic Colors
WHITE = (255, 255, 255)
PLAYER_HAND_BG = (40, 40, 50, 150)  # Semi-transparent
BLACK = (0, 0, 0)
GOLD = (255, 215, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 150, 255)

# Highlight Colors (for selection, hover states)
HIGHLIGHT_GREEN = (100, 255, 100)    # Medic selection, positive feedback
HIGHLIGHT_RED = (255, 100, 100)      # Opponent cards, negative feedback
HIGHLIGHT_BLUE = (100, 150, 255)     # Player cards, neutral selection
HIGHLIGHT_CYAN = (100, 200, 255)     # Info highlights
HIGHLIGHT_ORANGE = (255, 180, 50)    # Warnings, Goa'uld theme

# Text Colors
TEXT_LIGHT = (220, 220, 220)         # Primary text on dark backgrounds
TEXT_DIM = (200, 200, 200)           # Secondary text, instructions
TEXT_DIMMER = (180, 180, 180)        # Tertiary text, hints
TEXT_MUTED = (150, 150, 150)         # Disabled/inactive text
TEXT_TIMESTAMP = (100, 100, 120)     # Chat timestamps

# UI Background Colors (RGBA)
BG_OVERLAY_DARK = (0, 0, 0, 200)     # Dark overlays
BG_OVERLAY_MEDIUM = (0, 0, 0, 180)   # Medium overlays
BG_PANEL = (20, 40, 60, 200)         # Panel backgrounds
BG_DESC_BOX = (15, 25, 45, 240)      # Description box backgrounds
BG_BORDER = (80, 120, 160)           # Panel borders

# Chevron/Stargate Colors
CHEVRON_ACTIVE = (255, 160, 50)      # Active chevron amber

# Iris Defense Colors
IRIS_BLADE_COLOR = (100, 105, 115, 180)   # Metallic grey
IRIS_TEXT_COLOR = (255, 200, 100)          # Amber text

# Card Targeting Highlight Colors
SPY_TARGET_FILL = (255, 100, 100, 40)      # Red tint for spy targets
WEATHER_HIGHLIGHT = (180, 100, 100, 60)    # Reddish for weather effect

# ZPM Indicator Colors
ZPM_ACTIVE_COLOR = (100, 200, 255)         # Active ZPM - cyan
ZPM_DEPLETED_COLOR = (50, 50, 70)          # Depleted ZPM - dark

# Faction Theme Colors (for UI, not glow)
FACTION_UI_COLORS = {
    "Tau'ri": (100, 150, 255),
    "Goa'uld": (255, 180, 50),
    "Jaffa": (200, 150, 100),
    "Lucian Alliance": (200, 80, 200),
    "Asgard": (100, 255, 255),
    "Neutral": (180, 180, 180),
}

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

# Card Layout Constants
CARD_OVERLAP_RATIO = 0.85              # 15% overlap between cards in rows
CARD_GAP_SHIFT_SCALE = 0.4             # How much cards shift when making room for insertion

# Overlay Font Sizes (base sizes, scaled by SCALE_FACTOR)
OVERLAY_TITLE_FONT_SIZE = 56           # Large titles in selection overlays
OVERLAY_INSTRUCTION_FONT_SIZE = 32     # Instructions at bottom of overlays

def get_row_color(row_name):
    """Return the theme color for a given row type."""
    return ROW_COLORS.get(row_name, (200, 200, 255))

def get_faction_ui_color(faction_name):
    """Return the UI theme color for a faction."""
    return FACTION_UI_COLORS.get(faction_name, GOLD)

def scaled_font(base_size, bold=False, font_name="Arial"):
    """Create a font scaled to current display resolution."""
    sf = display_manager.SCALE_FACTOR
    size = max(base_size, int(base_size * sf))
    return pygame.font.SysFont(font_name, size, bold=bold)

# Layout System
COLUMN_RANGES = {
    "leader": (0.00, 0.09),      # Far left - leader portraits
    "horn": (0.09, 0.14),        # Horn slots between leader and playfield
    "playfield": (0.14, 0.80),   # Main game board
    "hud": (0.80, 1.00),         # Right sidebar
}

ROW_RANGES = {
    "opponent_hand": (0.01, 0.09),       # 8% height
    "opponent_siege": (0.10, 0.21),      # 11% height - taller rows
    "opponent_ranged": (0.22, 0.33),     # 11% height
    "opponent_close": (0.34, 0.44),      # 10% height
    "weather": (0.44, 0.50),             # 6% height - compact weather
    "player_close": (0.51, 0.61),        # 10% height
    "player_ranged": (0.62, 0.73),       # 11% height
    "player_siege": (0.74, 0.84),        # 10% height
    "player_hand": (0.85, 0.92),         # 7% height
    "command_bar": (0.93, 0.98),         # 5% height
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

ROW_HEIGHT = 0
CARD_WIDTH = 0
CARD_HEIGHT = 0
HAND_CARD_WIDTH = 0
HAND_CARD_HEIGHT = 0
HISTORY_ENTRY_HEIGHT = 0

MULLIGAN_CARD_SCALE = 1.3
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

HORN_LEFT = 0
HORN_WIDTH = 0
LEADER_LEFT = 0
LEADER_WIDTH = 0
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
MULLIGAN_BUTTON_RECT = None

def recalculate_dimensions():
    """Call this after display initialization to set up fonts and dimensions."""
    global SCORE_FONT, UI_FONT, POWER_FONT, ROW_FONT
    global ROW_HEIGHT, CARD_WIDTH, CARD_HEIGHT, HAND_CARD_WIDTH, HAND_CARD_HEIGHT, HISTORY_ENTRY_HEIGHT
    global MULLIGAN_CARD_SCALE, MULLIGAN_CARD_WIDTH, MULLIGAN_CARD_HEIGHT
    global PLAYFIELD_RANGE, opponent_hand_area_y, player_hand_area_y
    global OPPONENT_HAND_HEIGHT, PLAYER_HAND_HEIGHT, COMMAND_BAR_Y, COMMAND_BAR_HEIGHT
    global weather_y, WEATHER_ZONE_HEIGHT
    global PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS, WEATHER_SLOT_RECTS
    global PLAYER_HORN_SLOT_RECTS, OPPONENT_HORN_SLOT_RECTS
    global PLAYFIELD_LEFT, PLAYFIELD_WIDTH, HUD_LEFT, HUD_WIDTH
    global LEADER_COLUMN_X, LEADER_COLUMN_WIDTH, LEADER_COLUMN_HEIGHT, LEADER_SECTION_HEIGHT
    global LEADER_TOP_RECT, LEADER_BOTTOM_RECT, HORN_COLUMN_X, HORN_COLUMN_WIDTH
    global HAND_REGION_LEFT, HAND_REGION_WIDTH, HUD_PASS_BUTTON_RECT, MULLIGAN_BUTTON_RECT
    global HORN_LEFT, HORN_WIDTH, LEADER_LEFT, LEADER_WIDTH

    sf = display_manager.SCALE_FACTOR
    sh = display_manager.SCREEN_HEIGHT
    sw = display_manager.SCREEN_WIDTH

    # Fonts
    SCORE_FONT = pygame.font.SysFont("Arial", int(48 * sf), bold=True)
    UI_FONT = pygame.font.SysFont("Arial", int(28 * sf))
    POWER_FONT = pygame.font.SysFont("Arial", int(32 * sf), bold=True)
    ROW_FONT = pygame.font.SysFont("Arial", max(16, int(16 * sf)), bold=True)

    # Card & Board dimensions
    # Board cards: must fit within rows (11% screen height for taller rows)
    ROW_HEIGHT = int(sh * 0.11)  # ~158px at 1440p - taller rows
    CARD_HEIGHT = int(ROW_HEIGHT * 0.94)  # ~149px at 1440p - cards fill 94% of row
    CARD_WIDTH = int(CARD_HEIGHT / 1.4)  # Slightly wider aspect ratio = ~106px

    # Hand cards: BIGGER for better visibility and fanning effect
    HAND_CARD_HEIGHT = int(sh * 0.14)  # ~202px at 1440p - taller hand cards
    HAND_CARD_WIDTH = int(HAND_CARD_HEIGHT / 1.4)  # ~144px at 1440p

    HISTORY_ENTRY_HEIGHT = max(36, int(CARD_HEIGHT * 0.3))

    # Mulligan card scaling
    MULLIGAN_CARD_SCALE = 1.3
    MULLIGAN_CARD_WIDTH  = int(CARD_WIDTH * MULLIGAN_CARD_SCALE)
    MULLIGAN_CARD_HEIGHT = int(CARD_HEIGHT * MULLIGAN_CARD_SCALE)

    # Layout Zones (using COLUMN_RANGES for consistency)
    HORN_LEFT = pct_x(COLUMN_RANGES["horn"][0])
    HORN_WIDTH = pct_x(COLUMN_RANGES["horn"][1] - COLUMN_RANGES["horn"][0])

    LEADER_LEFT = pct_x(COLUMN_RANGES["leader"][0])
    LEADER_WIDTH = pct_x(COLUMN_RANGES["leader"][1] - COLUMN_RANGES["leader"][0])

    PLAYFIELD_RANGE = COLUMN_RANGES["playfield"]
    PLAYFIELD_LEFT = pct_x(PLAYFIELD_RANGE[0])
    PLAYFIELD_WIDTH = pct_x(PLAYFIELD_RANGE[1] - PLAYFIELD_RANGE[0])

    HUD_LEFT = pct_x(COLUMN_RANGES["hud"][0])
    HUD_WIDTH = pct_x(COLUMN_RANGES["hud"][1] - COLUMN_RANGES["hud"][0])

    # SIDEBAR_X for backwards compatibility with render_engine.py
    global SIDEBAR_X
    SIDEBAR_X = HUD_LEFT
    
    opponent_hand_area_y = pct_y(ROW_RANGES["opponent_hand"][0])
    player_hand_area_y = pct_y(ROW_RANGES["player_hand"][0])
    OPPONENT_HAND_HEIGHT = pct_y(ROW_RANGES["opponent_hand"][1] - ROW_RANGES["opponent_hand"][0])
    PLAYER_HAND_HEIGHT = pct_y(ROW_RANGES["player_hand"][1] - ROW_RANGES["player_hand"][0])
    COMMAND_BAR_Y = pct_y(ROW_RANGES["command_bar"][0])
    COMMAND_BAR_HEIGHT = max(1, pct_y(ROW_RANGES["command_bar"][1] - ROW_RANGES["command_bar"][0]))
    weather_y = pct_y(ROW_RANGES["weather"][0])
    WEATHER_ZONE_HEIGHT = max(1, pct_y(ROW_RANGES["weather"][1] - ROW_RANGES["weather"][0]))

    # Update ROW_RECTS to respect PLAYFIELD_WIDTH
    for row_name in ["close", "ranged", "siege"]:
        y_range = ROW_RANGES["player_" + row_name]
        PLAYER_ROW_RECTS[row_name] = pygame.Rect(
            PLAYFIELD_LEFT, pct_y(y_range[0]),
            PLAYFIELD_WIDTH, pct_y(y_range[1] - y_range[0])
        )
        
        y_range_opp = ROW_RANGES["opponent_" + row_name]
        OPPONENT_ROW_RECTS[row_name] = pygame.Rect(
            PLAYFIELD_LEFT, pct_y(y_range_opp[0]),
            PLAYFIELD_WIDTH, pct_y(y_range_opp[1] - y_range_opp[0])
        )

    # Leader Column (uses COLUMN_RANGES["leader"])
    LEADER_COLUMN_X = LEADER_LEFT
    LEADER_COLUMN_WIDTH = LEADER_WIDTH
    LEADER_COLUMN_HEIGHT = sh
    LEADER_SECTION_HEIGHT = LEADER_COLUMN_HEIGHT // 2
    LEADER_TOP_RECT = pygame.Rect(LEADER_COLUMN_X, 0, LEADER_COLUMN_WIDTH, LEADER_SECTION_HEIGHT)
    LEADER_BOTTOM_RECT = pygame.Rect(LEADER_COLUMN_X, sh - LEADER_SECTION_HEIGHT, LEADER_COLUMN_WIDTH, LEADER_SECTION_HEIGHT)

    # Horn Column (uses COLUMN_RANGES["horn"] - far left!)
    HORN_COLUMN_X = HORN_LEFT
    HORN_COLUMN_WIDTH = HORN_WIDTH
    HAND_REGION_LEFT = PLAYFIELD_LEFT
    HAND_REGION_WIDTH = PLAYFIELD_WIDTH

    # Horn slots: inside horn column, centered
    HORN_SLOT_WIDTH = CARD_WIDTH
    HORN_SLOT_X = HORN_LEFT + (HORN_WIDTH - CARD_WIDTH) // 2  # Center in horn column

    # Weather slots: inside horn column (same X as horn slots)
    WEATHER_SLOT_X = HORN_SLOT_X
    WEATHER_SLOT_RECTS = {}
    for idx, shared_row in enumerate(["siege", "ranged", "close"]):
        slot_center_y = weather_y + int(((idx + 0.5) / 3.0) * WEATHER_ZONE_HEIGHT)
        WEATHER_SLOT_RECTS[shared_row] = pygame.Rect(
            WEATHER_SLOT_X, slot_center_y - CARD_HEIGHT // 2, CARD_WIDTH, CARD_HEIGHT
        )

    PLAYER_HORN_SLOT_RECTS = {}
    for rname, rect in PLAYER_ROW_RECTS.items():
        # Horn slot: flush left of playfield row, same height as row
        PLAYER_HORN_SLOT_RECTS[rname] = pygame.Rect(HORN_SLOT_X, rect.y, HORN_SLOT_WIDTH, rect.height)

    OPPONENT_HORN_SLOT_RECTS = {}
    for rname, rect in OPPONENT_ROW_RECTS.items():
        # Horn slot: flush left of playfield row, same height as row
        OPPONENT_HORN_SLOT_RECTS[rname] = pygame.Rect(HORN_SLOT_X, rect.y, HORN_SLOT_WIDTH, rect.height)
    
    # HUD Pass Button (calculated dynamically later in main usually, but better to define here if possible)
    # In main.py it was not explicitly assigned to global constant immediately, but HUD_WIDTH is used.
    # We'll leave HUD_PASS_BUTTON_RECT as None for main to set or logic to use HUD coordinates.
    
    MULLIGAN_BUTTON_RECT = pygame.Rect(
        sw // 2 - int(100 * sf),
        sh // 2 + int(150 * sf),
        int(200 * sf),
        int(60 * sf)
    )