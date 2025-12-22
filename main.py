import pygame
import sys
import math
import random
import os
from pygame.math import Vector2
from game import Game
from lan_protocol import LanMessageType, parse_message
from cards import (
    ALL_CARDS,
    reload_card_images,
    FACTION_TAURI,
    FACTION_GOAULD,
    FACTION_JAFFA,
    FACTION_LUCIAN,
    FACTION_ASGARD,
)
from ai_opponent import AIController
from enum import Enum, auto

class UIState(Enum):
    """Finite State Machine for UI interaction modes."""
    # Core Game Phases (synced with game.game_state)
    MULLIGAN = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    
    # Overlays & Special Modes
    LEADER_MATCHUP = auto()
    PAUSED = auto()
    DISCARD_VIEW = auto()
    MEDIC_SELECT = auto()
    DECOY_SELECT = auto()
    RING_TRANSPORT_SELECT = auto()
    JONAS_PEEK = auto()
    BAAL_CLONE_SELECT = auto()
    VALA_SELECT = auto()
    CATHERINE_SELECT = auto()
    LEADER_CHOICE_SELECT = auto()
    THOR_MOVE_SELECT = auto()
    LAN_CHAT = auto()

# LAN Mode globals - set by lan_game.py when running multiplayer
LAN_MODE = False
LAN_CONTEXT = None
from animations import (
    AnimationManager,
    StargateActivationEffect,
    GlowAnimation,
    CardSlideAnimation,
    ScorchEffect,
    NaquadahExplosionEffect,
    AICardPlayAnimation,
    create_hero_animation,
    create_ability_animation,
    LegendaryLightningEffect,
    ClearWeatherBlackHole,
    MeteorShowerImpactEffect,
    HathorStealAnimation,
    ThorsHammerPurgeEffect,
    ZPMSurgeEffect,
    CommunicationRevealEffect,
    MerlinAntiOriEffect,
    DakaraShockwaveEffect,
)
from deck_builder import run_deck_builder, build_faction_deck
from unlocks import CardUnlockSystem, show_card_reward_screen, show_leader_reward_screen, UNLOCKABLE_CARDS
from main_menu import run_main_menu, DeckManager, show_stargate_opening
from power import FACTION_POWERS, FactionPowerEffect
from deck_persistence import record_victory, record_defeat, check_leader_unlock, get_persistence

# Round-based battle music (increases intensity each round)
ROUND_BATTLE_MUSIC = {
    1: os.path.join("assets", "audio", "battle_round1.ogg"),
    2: os.path.join("assets", "audio", "battle_round2.ogg"),
    3: os.path.join("assets", "audio", "battle_round3.ogg"),
}
_current_battle_music = None
_current_music_round = None
_next_music_allowed_at = 0
_battle_music_cooldown_ms = 120000


def _ensure_mixer_ready():
    if pygame.mixer.get_init():
        return True
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        return True
    except pygame.error as exc:
        print(f"[audio] Unable to init mixer: {exc}")
        return False


def _play_battle_theme(round_number, *, force=False):
    """Internal helper that plays the round track once if cooldown allows."""
    global _current_battle_music, _next_music_allowed_at
    if round_number is None:
        return False
    music_path = ROUND_BATTLE_MUSIC.get(round_number)
    if not music_path:
        return False
    if not os.path.exists(music_path):
        print(f"[audio] Battle music missing for round {round_number}: {music_path}")
        return False
    now = pygame.time.get_ticks()
    if not force and now < _next_music_allowed_at:
        return False
    if not _ensure_mixer_ready():
        return False
    try:
        from game_settings import get_settings
        pygame.mixer.music.load(music_path)
        # Get volume from settings
        settings = get_settings()
        volume = settings.get_effective_music_volume()
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)  # Loop the battle music
        _current_battle_music = music_path
        _next_music_allowed_at = now + _battle_music_cooldown_ms
        print(f"[audio] Battle music playing for round {round_number}: {music_path} at volume {volume:.2f}")
        return True
    except pygame.error as exc:
        print(f"[audio] Unable to play battle music ({music_path}): {exc}")
        return False


def set_battle_music_round(round_number, *, immediate=False):
    """Select which round music should be considered for playback."""
    global _current_music_round, _next_music_allowed_at
    if round_number == _current_music_round:
        if immediate:
            _play_battle_theme(round_number, force=True)
        return
    stop_battle_music()
    _current_music_round = round_number
    _next_music_allowed_at = 0
    if round_number:
        _play_battle_theme(round_number, force=True)


def update_battle_music():
    """Call regularly to restart music respecting the cooldown."""
    if not _current_music_round:
        return
    if not pygame.mixer.get_init():
        return
    if pygame.mixer.music.get_busy():
        return
    _play_battle_theme(_current_music_round)


def stop_battle_music(fade_ms=800):
    """Stop any playing battle theme and clear the round."""
    global _current_battle_music, _current_music_round
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        try:
            pygame.mixer.music.fadeout(fade_ms)
        except pygame.error:
            pygame.mixer.music.stop()
    if _current_battle_music:
        print(f"[audio] Battle music stopped ({_current_battle_music})")
    _current_battle_music = None
    _current_music_round = None


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

WINDOWED_WIDTH = SCREEN_WIDTH
WINDOWED_HEIGHT = SCREEN_HEIGHT
WINDOWED_SCALE_FACTOR = SCALE_FACTOR
WINDOWED_FLAGS = pygame.SHOWN | pygame.SCALED if SCALE_FACTOR < 1.0 else pygame.SHOWN

# Allow forcing fullscreen via CLI/env for streamers/setups
DEFAULT_FULLSCREEN = (
    "--fullscreen" in sys.argv or
    os.environ.get("STARGWENT_FULLSCREEN", "").lower() in {"1", "true", "yes"}
)
FULLSCREEN = DEFAULT_FULLSCREEN
screen = None


def set_display_mode(fullscreen_enabled, *, reload_cards=False):
    """Centralized fullscreen toggling that keeps dimensions in sync."""
    global screen, SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_FACTOR, FULLSCREEN
    FULLSCREEN = fullscreen_enabled
    if fullscreen_enabled:
        SCREEN_WIDTH = DESKTOP_WIDTH
        SCREEN_HEIGHT = DESKTOP_HEIGHT
        SCALE_FACTOR = min(DESKTOP_WIDTH / TARGET_WIDTH, DESKTOP_HEIGHT / TARGET_HEIGHT, 1.0)
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Stargwent - Fullscreen")
    else:
        SCREEN_WIDTH = WINDOWED_WIDTH
        SCREEN_HEIGHT = WINDOWED_HEIGHT
        SCALE_FACTOR = WINDOWED_SCALE_FACTOR
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), WINDOWED_FLAGS)
        if WINDOWED_FLAGS & pygame.SCALED:
            pygame.display.set_caption(f"Stargwent - Scaled to {SCREEN_WIDTH}x{SCREEN_HEIGHT} (from 4K)")
        else:
            pygame.display.set_caption("Stargwent - 4K (3840x2160)")
    if reload_cards:
        reload_card_images()


def sync_fullscreen_from_surface():
    """Ensure FULLSCREEN flag matches current SDL state (handles menu toggles)."""
    surface = pygame.display.get_surface()
    if not surface:
        return
    is_fullscreen = bool(surface.get_flags() & pygame.FULLSCREEN)
    if is_fullscreen != FULLSCREEN:
        set_display_mode(is_fullscreen, reload_cards=True)


def toggle_fullscreen_mode():
    """Flip fullscreen state respecting all UI/layout updates."""
    set_display_mode(not FULLSCREEN, reload_cards=True)


def enforce_display_mode():
    """Ensure the active SDL surface matches our desired fullscreen flag."""
    surface = pygame.display.get_surface()
    if not surface:
        return
    actual_fullscreen = bool(surface.get_flags() & pygame.FULLSCREEN)
    if actual_fullscreen != FULLSCREEN:
        set_display_mode(FULLSCREEN, reload_cards=True)


print(f"Display Detection:")
print(f"  Desktop: {DESKTOP_WIDTH}x{DESKTOP_HEIGHT}")
print(f"  Target: {TARGET_WIDTH}x{TARGET_HEIGHT}")
print(f"  Scale Factor: {SCALE_FACTOR:.2f}")
print(f"  Window Size: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

set_display_mode(FULLSCREEN)

if FULLSCREEN:
    print("✓ Fullscreen mode enabled on launch")
elif WINDOWED_FLAGS & pygame.SCALED:
    print("✓ Using hardware scaling for better performance")
else:
    print("✓ Running at native 4K resolution")

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
CARD_WIDTH = int(SCREEN_HEIGHT * 0.08)  # Made cards slightly smaller
CARD_HEIGHT = int(SCREEN_HEIGHT * 0.11)
HISTORY_ENTRY_HEIGHT = max(36, int(CARD_HEIGHT * 0.3))

# Mulligan card scaling (to prevent cropping)
MULLIGAN_CARD_SCALE = 0.8
MULLIGAN_CARD_WIDTH  = int(CARD_WIDTH * MULLIGAN_CARD_SCALE)
MULLIGAN_CARD_HEIGHT = int(CARD_HEIGHT * MULLIGAN_CARD_SCALE)

# ═══════════════════════════════════════════════════════════════
# LAYOUT SYSTEM - Percentage-based 4K blueprint
# ═══════════════════════════════════════════════════════════════

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
    return int(SCREEN_WIDTH * value)

def pct_y(value: float) -> int:
    return int(SCREEN_HEIGHT * value)

def rect_from_percent(x_range, y_range):
    return pygame.Rect(
        pct_x(x_range[0]),
        pct_y(y_range[0]),
        max(1, pct_x(x_range[1] - x_range[0])),
        max(1, pct_y(y_range[1] - y_range[0])),
    )

PLAYFIELD_RANGE = COLUMN_RANGES["playfield"]
opponent_hand_area_y = pct_y(ROW_RANGES["opponent_hand"][0])
player_hand_area_y = pct_y(ROW_RANGES["player_hand"][0])
OPPONENT_HAND_HEIGHT = pct_y(ROW_RANGES["opponent_hand"][1] - ROW_RANGES["opponent_hand"][0])
PLAYER_HAND_HEIGHT = pct_y(ROW_RANGES["player_hand"][1] - ROW_RANGES["player_hand"][0])
COMMAND_BAR_Y = pct_y(ROW_RANGES["command_bar"][0])
COMMAND_BAR_HEIGHT = max(1, pct_y(ROW_RANGES["command_bar"][1] - ROW_RANGES["command_bar"][0]))
weather_y = pct_y(ROW_RANGES["weather"][0])
WEATHER_ZONE_HEIGHT = max(1, pct_y(ROW_RANGES["weather"][1] - ROW_RANGES["weather"][0]))
ROW_HEIGHT = max(1, pct_y(ROW_RANGES["player_close"][1] - ROW_RANGES["player_close"][0]))
HAND_Y_OFFSET = SCREEN_HEIGHT - player_hand_area_y

# Build rectangles for hitboxes and rendering (restricted to playfield)
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
LEADER_COLUMN_HEIGHT = SCREEN_HEIGHT
LEADER_SECTION_HEIGHT = LEADER_COLUMN_HEIGHT // 2
LEADER_TOP_RECT = pygame.Rect(
    LEADER_COLUMN_X,
    0,
    LEADER_COLUMN_WIDTH,
    LEADER_SECTION_HEIGHT
)
LEADER_BOTTOM_RECT = pygame.Rect(
    LEADER_COLUMN_X,
    SCREEN_HEIGHT - LEADER_SECTION_HEIGHT,
    LEADER_COLUMN_WIDTH,
    LEADER_SECTION_HEIGHT
)
HORN_COLUMN_X = pct_x(COLUMN_RANGES["horn"][0])
HORN_COLUMN_WIDTH = max(1, pct_x(COLUMN_RANGES["horn"][1] - COLUMN_RANGES["horn"][0]))
HAND_REGION_LEFT = pct_x(0.15)
HAND_REGION_WIDTH = max(1, pct_x(0.70))

# Compute weather & horn slots relative to rows
WEATHER_SLOT_X = pct_x(0.02)
HORN_SLOT_WIDTH = min(max(1, int(CARD_WIDTH * 1.1)), HORN_COLUMN_WIDTH)
HORN_SLOT_X = HORN_COLUMN_X + (HORN_COLUMN_WIDTH - HORN_SLOT_WIDTH) // 2

WEATHER_SLOT_RECTS, PLAYER_HORN_SLOT_RECTS, OPPONENT_HORN_SLOT_RECTS = {}, {}, {}
for idx, shared_row in enumerate(["siege", "ranged", "close"]):
    slot_center_y = weather_y + int(((idx + 0.5) / 3.0) * WEATHER_ZONE_HEIGHT)
    WEATHER_SLOT_RECTS[shared_row] = pygame.Rect(
        WEATHER_SLOT_X,
        slot_center_y - CARD_HEIGHT // 2,
        CARD_WIDTH,
        CARD_HEIGHT
    )

for rname, rect in PLAYER_ROW_RECTS.items():
    PLAYER_HORN_SLOT_RECTS[rname] = pygame.Rect(
        HORN_SLOT_X,
        rect.y,
        HORN_SLOT_WIDTH,
        rect.height
    )

for rname, rect in OPPONENT_ROW_RECTS.items():
    OPPONENT_HORN_SLOT_RECTS[rname] = pygame.Rect(
        HORN_SLOT_X,
        rect.y,
        HORN_SLOT_WIDTH,
        rect.height
    )

HUD_PASS_BUTTON_RECT = None

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
    FACTION_LUCIAN: (0x6E, 0x37, 0xAA),
    FACTION_ASGARD: (0x7D, 0xC8, 0xFF),
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


def add_special_card_effect(card, effect_x, effect_y, anim_manager, screen_width, screen_height):
    """Trigger unique animations for special cards matching lore/logic."""
    name_lower = (card.name or "").lower()
    ability_lower = (card.ability or "").lower()

    if "thor" in name_lower or "remove all goa'uld" in ability_lower:
        anim_manager.add_effect(ThorsHammerPurgeEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "zero point module" in name_lower or "zpm" in name_lower or "double all your siege" in ability_lower:
        anim_manager.add_effect(ZPMSurgeEffect(effect_x, effect_y))
        return True
    if "communication device" in name_lower or "reveal opponent's hand" in ability_lower:
        anim_manager.add_effect(CommunicationRevealEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "merlin" in name_lower or "anti-ori" in name_lower:
        anim_manager.add_effect(MerlinAntiOriEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "dakara" in name_lower:
        anim_manager.add_effect(DakaraShockwaveEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    return False


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

def _compute_hand_positions(card_count, card_width, card_gap):
    """Return evenly spaced or accordion-style hand positions."""
    if card_count <= 0:
        return [], False

    card_full = card_width + card_gap
    total_width = card_count * card_width + (card_count - 1) * card_gap
    region_left = HAND_REGION_LEFT
    region_width = HAND_REGION_WIDTH

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
    """Draw the player's hand plus optional drag animations."""
    hand_area_height = COMMAND_BAR_Y - player_hand_area_y
    if hand_area_height > 0:
        hand_bg_surface = pygame.Surface((SCREEN_WIDTH, hand_area_height), pygame.SRCALPHA)
        hand_bg_surface.fill(PLAYER_HAND_BG)
        surface.blit(hand_bg_surface, (0, player_hand_area_y))

    if drag_visuals and drag_visuals.get("trail"):
        _draw_drag_trail(surface, drag_visuals.get("trail"))

    is_mulligan_mode = mulligan_selected is not None
    card_w = MULLIGAN_CARD_WIDTH if is_mulligan_mode else CARD_WIDTH
    card_h = MULLIGAN_CARD_HEIGHT if is_mulligan_mode else CARD_HEIGHT
    total_cards = len(player.hand)
    card_spacing = int(card_w * 0.125)

    if is_mulligan_mode:
        total_width = total_cards * card_w + (total_cards - 1) * card_spacing
        start_x = (SCREEN_WIDTH - total_width) // 2 if total_width < SCREEN_WIDTH else HAND_REGION_LEFT
        card_positions = [start_x + i * (card_w + card_spacing) for i in range(total_cards)]
        accordion_active = False
    else:
        card_positions, accordion_active = _compute_hand_positions(total_cards, card_w, card_spacing)

    if is_mulligan_mode:
        card_y = SCREEN_HEIGHT // 2 - card_h // 2
    else:
        card_y = COMMAND_BAR_Y + (COMMAND_BAR_HEIGHT - card_h) // 2
    
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
            card_scale = MULLIGAN_CARD_SCALE * (hover_scale if is_hovered else 1.0)
        else:
            base_scale = 0.95 if accordion_active else 1.0
            card_scale = base_scale * (hover_scale if is_hovered else 1.0)
        edge_alpha = 205 if (accordion_active and (i == 0 or i == len(player.hand) - 1)) else 255
        draw_y = card_y - (int(25 * SCALE_FACTOR) if (is_hovered and not is_mulligan_mode) else 0)
        draw_card(surface, card, card_x, draw_y, selected=is_selected, hover_scale=card_scale, alpha=edge_alpha)
        
        if is_mulligan_selected:
            pygame.draw.rect(surface, (100, 100, 255), card.rect, width=4, border_radius=5)
        
        if is_selected and card.row in ["special", "weather"]:
            hint_font = pygame.font.SysFont("Arial", 16, bold=True)
            hint_text = hint_font.render("CLICK AGAIN TO PLAY", True, (255, 255, 0))
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
    
    hand_area_height = OPPONENT_HAND_HEIGHT
    hand_y = opponent_hand_area_y + (hand_area_height - CARD_HEIGHT) // 2
    total_cards = len(opponent.hand)
    
    if total_cards == 0:
        return
    
    card_spacing = int(CARD_WIDTH * 0.125)
    card_positions, accordion_active = _compute_hand_positions(total_cards, CARD_WIDTH, card_spacing)
    
    # Get card back image
    card_back_image = get_card_back(CARD_WIDTH, CARD_HEIGHT)
    
    for i, card in enumerate(opponent.hand):
        if i >= len(card_positions):
            continue
        card_x = card_positions[i]
        alpha = 205 if accordion_active and (i == 0 or i == total_cards - 1) else 255
        if opponent.hand_revealed:
            draw_card(
                surface,
                card,
                card_x,
                hand_y,
                render_details=True,
                update_rect=False,
                alpha=alpha
            )
            pygame.draw.rect(surface, (255, 215, 0), 
                             (card_x, hand_y, CARD_WIDTH, CARD_HEIGHT), 
                             2, border_radius=8)
        else:
            temp_surface = card_back_image.copy()
            if alpha < 255:
                temp_surface.set_alpha(alpha)
            surface.blit(temp_surface, (card_x, hand_y))
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


def draw_horn_slots(surface, game):
    """Render Commander Horn drop slots for each row."""
    def render_slot(slot_rect, active, card, faction_color):
        slot_surface = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)
        slot_surface.fill((30, 30, 40, 120))
        pygame.draw.rect(slot_surface, (15, 15, 20, 200), slot_surface.get_rect().inflate(-6, -6), border_radius=10)
        surface.blit(slot_surface, slot_rect.topleft)

        pulse = (math.sin(pygame.time.get_ticks() / 250.0) + 1) * 0.5
        outline_color = faction_color if active else tuple(int(c * 0.7) for c in faction_color)
        outline_alpha = 220 if active else int(130 + 80 * pulse)
        outline_surface = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(outline_surface, (*outline_color, outline_alpha), outline_surface.get_rect(), width=3, border_radius=14)
        surface.blit(outline_surface, slot_rect.topleft)

        if card:
            draw_card(
                surface,
                card,
                slot_rect.x + (slot_rect.width - CARD_WIDTH) // 2,
                slot_rect.centery - CARD_HEIGHT // 2,
                render_details=False,
                update_rect=False
            )
        else:
            horn_text = ROW_FONT.render("H", True, outline_color)
            horn_rect = horn_text.get_rect(center=slot_rect.center)
            surface.blit(horn_text, horn_rect)
    
    player_color = FACTION_GLOW_COLORS.get(game.player1.faction, (255, 215, 0))
    opponent_color = FACTION_GLOW_COLORS.get(game.player2.faction, (255, 215, 0))

    if hasattr(game.player1, "horn_slots"):
        for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
            render_slot(slot_rect,
                        game.player1.horn_effects.get(row_name, False),
                        game.player1.horn_slots.get(row_name),
                        player_color)
    if hasattr(game.player2, "horn_slots"):
        for row_name, slot_rect in OPPONENT_HORN_SLOT_RECTS.items():
            render_slot(slot_rect,
                        game.player2.horn_effects.get(row_name, False),
                        game.player2.horn_slots.get(row_name),
                        opponent_color)

def _render_sg1_score_box(tint, row_box, score, surface, is_player):
    """Draw Stargate-inspired border/panel for per-row scores."""
    score_font = pygame.font.SysFont("Arial", max(24, int(28 * SCALE_FACTOR)), bold=True)
    box_surface = pygame.Surface((row_box.width, row_box.height), pygame.SRCALPHA)
    fill_alpha = 215 if is_player else 170
    box_surface.fill((*tint, fill_alpha))
    border_rect = box_surface.get_rect()
    pygame.draw.rect(box_surface, (255, 255, 255, 45), border_rect, border_radius=18)
    pygame.draw.rect(box_surface, (20, 30, 45, 180), border_rect.inflate(-4, -4), width=3, border_radius=14)
    notch_color = (180, 220, 255, 160)
    notch = 18
    pygame.draw.line(box_surface, notch_color, (notch, 4), (border_rect.width - notch, 4), 3)
    pygame.draw.line(box_surface, notch_color, (4, border_rect.height - 4), (border_rect.width - 4, border_rect.height - 4), 3)
    pygame.draw.line(box_surface, notch_color, (4, border_rect.height - 4), (4, border_rect.height - 20), 3)
    pygame.draw.line(box_surface, notch_color, (border_rect.width - 4, border_rect.height - 4), (border_rect.width - 4, 20), 3)
    surface.blit(box_surface, row_box.topleft)
    score_color = WHITE if score > 0 else (200, 200, 200)
    score_text = score_font.render(str(score), True, score_color)
    score_rect = score_text.get_rect(center=row_box.center)
    surface.blit(score_text, score_rect)


def draw_row_score_boxes(surface, game):
    """Render per-row score boxes inside the HUD column."""
    box_width = int(HUD_WIDTH * 0.32)
    box_height = max(30, int(ROW_HEIGHT * 0.35))
    box_x = HUD_LEFT + int(HUD_WIDTH * 0.03)

    for player, rects in [(game.player2, OPPONENT_ROW_RECTS), (game.player1, PLAYER_ROW_RECTS)]:
        for row_name, row_rect in rects.items():
            score = sum(c.displayed_power for c in player.board.get(row_name, []))
            center_y = row_rect.centery
            row_box = pygame.Rect(box_x, center_y - box_height // 2, box_width, box_height)
            tint = get_row_color(row_name)
            _render_sg1_score_box(tint, row_box, score, surface, player == game.player1)

def draw_history_panel(surface, game, panel_rect, scroll_offset, hover_pos=None):
    """Draw the scrollable history feed in the HUD column."""
    history_font = pygame.font.SysFont("Arial", max(14, int(16 * SCALE_FACTOR)))
    panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    panel_surface.fill((10, 18, 32, 200))
    pygame.draw.rect(panel_surface, (80, 120, 180, 220), panel_surface.get_rect(), width=2, border_radius=12)
    surface.blit(panel_surface, panel_rect.topleft)

    padding = 10
    entries = game.history
    icon_width = 12
    line_height = history_font.get_linesize()
    entry_base_height = HISTORY_ENTRY_HEIGHT
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
    player_color = FACTION_GLOW_COLORS.get(game.player1.faction, (100, 200, 255))
    ai_color = FACTION_GLOW_COLORS.get(game.player2.faction, (255, 120, 120))

    for entry, entry_height, wrapped_lines in reversed(formatted_entries):
        y_cursor -= entry_height
        entry_rect = pygame.Rect(panel_rect.x + padding, y_cursor,
                                 panel_rect.width - 2 * padding, entry_height - 4)
        if entry_rect.bottom < panel_rect.top + padding:
            continue
        if entry_rect.top > panel_rect.bottom:
            continue

        owner_color = player_color if entry.owner == "player" else ai_color
        
        # Override color for Chat/System events
        if entry.event_type == "chat":
            if "System" in entry.description:
                owner_color = (255, 215, 0) # Gold
            elif "You" in entry.description:
                owner_color = (100, 255, 100) # Green
            else:
                owner_color = (200, 200, 255) # Blue
        elif entry.event_type == "scorch" or entry.event_type == "destroy":
             owner_color = (255, 80, 80) # Red
        
        hovered = hover_pos and entry_rect.collidepoint(hover_pos)
        entry_surface = pygame.Surface((entry_rect.width, entry_rect.height), pygame.SRCALPHA)
        entry_surface.fill((owner_color[0], owner_color[1], owner_color[2], 160 if hovered else 120))
        pygame.draw.rect(entry_surface, owner_color, entry_surface.get_rect(), width=2, border_radius=8)

        # Draw icon (or chat bubble)
        icon_rect = pygame.Rect(8, 6, icon_width, entry_rect.height - 12)
        pygame.draw.rect(entry_surface, (255, 255, 255, 90), icon_rect, border_radius=4)
        
        # Render the icon character/emoji
        if entry.icon:
            # Use smaller font for icon to fit in box
            icon_surf = history_font.render(entry.icon, True, (255, 255, 255))
            # Center in the icon box
            icon_dest = icon_surf.get_rect(center=icon_rect.center)
            entry_surface.blit(icon_surf, icon_dest)

        for idx, line in enumerate(wrapped_lines):
            text_surface = history_font.render(line, True, WHITE)
            text_rect = text_surface.get_rect()
            text_rect.topleft = (icon_rect.right + 8, 6 + idx * line_height)
            entry_surface.blit(text_surface, text_rect)

        surface.blit(entry_surface, entry_rect.topleft)
        hitboxes.append((entry, entry_rect.copy()))

    surface.set_clip(None)
    return hitboxes, max_scroll

def draw_leader_column(surface, player, area_rect, ability_ready=True, faction_power_ready=False, hover_pos=None):
    """Render the left column stack (ability/faction/special buttons + leader portrait)."""
    faction_color = FACTION_GLOW_COLORS.get(player.faction, (200, 200, 200))
    padding = max(12, int(area_rect.width * 0.05))
    column_left = area_rect.x + padding
    column_right = area_rect.right - padding
    column_width = max(1, column_right - column_left)
    column_center_x = column_left + column_width // 2
    spacing = max(10, min(15, int(12 * SCALE_FACTOR)))

    # Keep leader portrait locked to the same dimensions as battlefield cards.
    leader_width = CARD_WIDTH
    leader_height = CARD_HEIGHT

    # Ability strip shares space with counters on the right.
    ability_height = max(int(CARD_HEIGHT * 0.22), 56)
    min_ability_width = max(int(CARD_WIDTH * 0.9), 140)
    counter_gap = spacing
    base_counter_width = int(column_width * 0.32)
    max_counter_width = max(0, column_width - min_ability_width - counter_gap)
    counter_width = min(base_counter_width, max_counter_width)
    if counter_width <= 0:
        counter_width = 0
        counter_gap = 0
    ability_area_width = column_width - counter_width - counter_gap
    ability_width = min(ability_area_width, max(min_ability_width, ability_area_width))
    ability_x = column_left + max(0, (ability_area_width - ability_width) // 2)

    faction_size = max(int(CARD_WIDTH * 0.65), 72)
    special_size = max(int(CARD_WIDTH * 0.5), 60)

    # Determine if this player has a special faction button (Iris, Rings, etc.).
    special_info = None
    if player.faction == FACTION_TAURI:
        special_info = {
            "kind": "iris",
            "ready": player.iris_defense.is_available(),
            "active": player.iris_defense.is_active()
        }
    elif getattr(player, "ring_transportation", None):
        special_info = {
            "kind": "rings",
            "ready": player.ring_transportation.can_use(),
            "active": player.ring_transportation.animation_in_progress
        }

    element_heights = [ability_height, faction_size]
    if special_info:
        element_heights.append(special_size)
    element_heights.append(leader_height)
    stack_height = sum(element_heights) + spacing * (len(element_heights) - 1)
    available_top = area_rect.top + padding
    available_bottom = area_rect.bottom - padding
    max_top = max(available_top, available_bottom - stack_height)
    y_cursor = area_rect.centery - stack_height // 2
    y_cursor = max(available_top, min(y_cursor, max_top))

    ability_rect = pygame.Rect(ability_x, y_cursor, ability_width, ability_height)
    counter_rect = None
    if counter_width > 0:
        counter_rect = pygame.Rect(column_right - counter_width, ability_rect.y, counter_width, ability_height)

    # Ability button with Stargate ring design
    ability_surface = pygame.Surface((ability_rect.width, ability_rect.height), pygame.SRCALPHA)
    ability_surface.fill((15, 20, 35, 240))

    # Colors based on ability state
    if ability_ready:
        ring_color = faction_color
        chevron_color = tuple(min(255, c + 40) for c in faction_color)
        dot_color = faction_color
        glow_color = tuple(min(255, c + 60) for c in faction_color)
    else:
        ring_color = (80, 80, 90)
        chevron_color = (100, 100, 110)
        dot_color = (70, 70, 80)
        glow_color = (90, 90, 100)

    # Hover effect
    if hover_pos and ability_rect.collidepoint(hover_pos):
        ring_color = tuple(min(255, c + 50) for c in ring_color)
        chevron_color = tuple(min(255, c + 50) for c in chevron_color)
        glow_color = tuple(min(255, c + 70) for c in glow_color)

    icon_rect = ability_surface.get_rect()
    cx, cy = icon_rect.center

    # Calculate sizes based on button dimensions
    outer_radius = min(icon_rect.width, icon_rect.height) // 2 - 6
    inner_radius = int(outer_radius * 0.65)
    chevron_radius = int(outer_radius * 0.85)

    # Draw outer glow ring
    for i in range(3):
        r = outer_radius + 3 - i
        alpha = 60 - i * 20
        glow = (*glow_color[:3], alpha) if len(glow_color) == 3 else glow_color
        pygame.draw.circle(ability_surface, glow, (cx, cy), r, 2)

    # Draw main outer ring
    pygame.draw.circle(ability_surface, ring_color, (cx, cy), outer_radius, 4)

    # Draw inner ring
    pygame.draw.circle(ability_surface, ring_color, (cx, cy), inner_radius, 3)

    # Draw 9 chevrons around the ring (like a Stargate)
    num_chevrons = 9
    chevron_size = max(6, outer_radius // 5)
    for i in range(num_chevrons):
        angle = (i * 2 * 3.14159 / num_chevrons) - 3.14159 / 2

        # Chevron position on the ring
        chev_x = cx + int(chevron_radius * math.cos(angle))
        chev_y = cy + int(chevron_radius * math.sin(angle))

        # Draw chevron as triangle pointing outward
        # Calculate direction vector
        dx = math.cos(angle)
        dy = math.sin(angle)

        # Perpendicular vector for chevron width
        px = -dy
        py = dx

        # Chevron points
        tip_x = chev_x + int(dx * chevron_size * 0.8)
        tip_y = chev_y + int(dy * chevron_size * 0.8)

        base1_x = chev_x + int(px * chevron_size * 0.5) - int(dx * chevron_size * 0.3)
        base1_y = chev_y + int(py * chevron_size * 0.5) - int(dy * chevron_size * 0.3)

        base2_x = chev_x - int(px * chevron_size * 0.5) - int(dx * chevron_size * 0.3)
        base2_y = chev_y - int(py * chevron_size * 0.5) - int(dy * chevron_size * 0.3)

        pygame.draw.polygon(ability_surface, chevron_color, [
            (tip_x, tip_y),
            (base1_x, base1_y),
            (base2_x, base2_y)
        ])

    # Draw center dot pattern (like the event horizon)
    dot_radius = max(2, inner_radius // 8)
    dot_spacing = max(6, inner_radius // 3)

    # Draw grid of dots in center
    for row in range(-2, 3):
        for col in range(-2, 3):
            # Skip corners to make circular pattern
            if abs(row) == 2 and abs(col) == 2:
                continue

            dot_x = cx + col * dot_spacing
            dot_y = cy + row * dot_spacing

            # Check if dot is within inner circle
            dist = math.sqrt((dot_x - cx) ** 2 + (dot_y - cy) ** 2)
            if dist < inner_radius - dot_radius - 2:
                pygame.draw.circle(ability_surface, dot_color, (dot_x, dot_y), dot_radius)

    # Draw rounded border
    pygame.draw.rect(ability_surface, ring_color, ability_surface.get_rect(), width=3, border_radius=12)

    surface.blit(ability_surface, ability_rect.topleft)

    # Card/Deck counters stay compact on the right.
    discard_hit_rect = None
    if counter_rect:
        counter_items = [
            ("HAND", len(player.hand)),
            ("DRAW", len(player.deck)),
            ("DISC", len(player.discard_pile)),
        ]
        counter_font = pygame.font.SysFont("Arial", max(12, int(14 * SCALE_FACTOR)), bold=True)
        slot_height = counter_rect.height // len(counter_items)
        for idx, (label, value) in enumerate(counter_items):
            slot = pygame.Rect(counter_rect.x,
                               counter_rect.y + idx * slot_height,
                               counter_rect.width,
                               slot_height - max(2, spacing // 3))
            slot_surface = pygame.Surface((slot.width, slot.height), pygame.SRCALPHA)
            slot_surface.fill((16, 24, 40, 210))
            pygame.draw.rect(slot_surface, (70, 110, 180), slot_surface.get_rect(), width=2, border_radius=6)
            text = counter_font.render(f"{label}: {value}", True, WHITE)
            slot_surface.blit(text, text.get_rect(center=slot_surface.get_rect().center))
            surface.blit(slot_surface, slot.topleft)
            if label == "DISC":
                discard_hit_rect = slot.copy()

    y_cursor = ability_rect.bottom + spacing

    # Faction power button - Stargate design with faction-specific event horizon
    faction_rect = pygame.Rect(0, y_cursor, faction_size, faction_size)
    faction_rect.centerx = column_center_x
    faction_surface = pygame.Surface((faction_rect.width, faction_rect.height), pygame.SRCALPHA)

    cx, cy = faction_surface.get_rect().center
    outer_radius = faction_rect.width // 2 - 2
    inner_radius = int(outer_radius * 0.7)
    chevron_radius = int(outer_radius * 0.88)

    # Faction-specific color schemes for Stargate
    faction_name = player.faction if hasattr(player, 'faction') else "Tau'ri"

    # Define faction-specific colors (ring, event horizon primary, event horizon secondary, chevron)
    faction_gate_colors = {
        "Tau'ri": {
            "ring": (120, 130, 140),      # Silver/gray ring
            "horizon1": (30, 100, 200),    # Blue event horizon
            "horizon2": (80, 160, 255),    # Light blue swirl
            "horizon3": (200, 230, 255),   # White center glow
            "chevron": (255, 180, 50),     # Gold chevrons
        },
        "Goa'uld": {
            "ring": (180, 150, 80),        # Gold ring
            "horizon1": (180, 50, 30),     # Red/orange event horizon
            "horizon2": (255, 120, 60),    # Orange swirl
            "horizon3": (255, 200, 150),   # Bright center
            "chevron": (255, 80, 40),      # Red chevrons
        },
        "Jaffa": {
            "ring": (160, 140, 100),       # Bronze ring
            "horizon1": (180, 140, 40),    # Golden event horizon
            "horizon2": (220, 180, 80),    # Light gold swirl
            "horizon3": (255, 240, 180),   # Bright gold center
            "chevron": (255, 200, 100),    # Gold chevrons
        },
        "Lucian Alliance": {
            "ring": (100, 80, 120),        # Dark purple ring
            "horizon1": (120, 50, 150),    # Purple event horizon
            "horizon2": (180, 100, 200),   # Pink swirl
            "horizon3": (240, 180, 255),   # Bright purple center
            "chevron": (255, 100, 200),    # Pink chevrons
        },
        "Asgard": {
            "ring": (180, 200, 220),       # White/silver ring
            "horizon1": (40, 150, 180),    # Cyan event horizon
            "horizon2": (100, 200, 220),   # Light cyan swirl
            "horizon3": (220, 255, 255),   # White center
            "chevron": (150, 255, 255),    # Cyan chevrons
        },
    }

    colors = faction_gate_colors.get(faction_name, faction_gate_colors["Tau'ri"])

    # Adjust brightness based on ready state and hover
    brightness_mult = 1.0 if faction_power_ready else 0.5
    if hover_pos and faction_rect.collidepoint(hover_pos):
        brightness_mult = min(1.3, brightness_mult + 0.3)

    def adjust_color(color, mult):
        return tuple(min(255, int(c * mult)) for c in color)

    ring_color = adjust_color(colors["ring"], brightness_mult)
    horizon1 = adjust_color(colors["horizon1"], brightness_mult)
    horizon2 = adjust_color(colors["horizon2"], brightness_mult)
    horizon3 = adjust_color(colors["horizon3"], brightness_mult)
    chevron_color = adjust_color(colors["chevron"], brightness_mult)

    # Draw dark background circle
    pygame.draw.circle(faction_surface, (20, 25, 35), (cx, cy), outer_radius)

    # Draw event horizon (swirling effect with concentric circles)
    # Outer horizon ring
    pygame.draw.circle(faction_surface, horizon1, (cx, cy), inner_radius)

    # Swirl effect - multiple offset circles
    swirl_radius = int(inner_radius * 0.85)
    for i in range(6):
        angle = i * 60 * 3.14159 / 180
        offset_x = int(math.cos(angle) * inner_radius * 0.15)
        offset_y = int(math.sin(angle) * inner_radius * 0.15)
        pygame.draw.circle(faction_surface, horizon2, (cx + offset_x, cy + offset_y), swirl_radius, 3)

    # Inner swirl layers
    for radius_mult in [0.7, 0.5, 0.3]:
        r = int(inner_radius * radius_mult)
        pygame.draw.circle(faction_surface, horizon2, (cx, cy), r, 2)

    # Center glow
    center_radius = int(inner_radius * 0.25)
    pygame.draw.circle(faction_surface, horizon3, (cx, cy), center_radius)
    pygame.draw.circle(faction_surface, (255, 255, 255), (cx, cy), center_radius // 2)

    # Draw outer ring (the Stargate frame)
    ring_width = max(4, int(outer_radius * 0.12))
    pygame.draw.circle(faction_surface, ring_color, (cx, cy), outer_radius, ring_width)

    # Draw chevrons around the ring
    num_chevrons = 9
    chevron_size = max(4, int(outer_radius * 0.15))

    for i in range(num_chevrons):
        angle = (i * 2 * 3.14159 / num_chevrons) - 3.14159 / 2

        chev_x = cx + int(chevron_radius * math.cos(angle))
        chev_y = cy + int(chevron_radius * math.sin(angle))

        # Direction vectors
        dx = math.cos(angle)
        dy = math.sin(angle)
        px = -dy
        py = dx

        # Chevron triangle points (pointing outward)
        tip_x = chev_x + int(dx * chevron_size)
        tip_y = chev_y + int(dy * chevron_size)

        base1_x = chev_x + int(px * chevron_size * 0.6) - int(dx * chevron_size * 0.3)
        base1_y = chev_y + int(py * chevron_size * 0.6) - int(dy * chevron_size * 0.3)

        base2_x = chev_x - int(px * chevron_size * 0.6) - int(dx * chevron_size * 0.3)
        base2_y = chev_y - int(py * chevron_size * 0.6) - int(dy * chevron_size * 0.3)

        pygame.draw.polygon(faction_surface, chevron_color, [
            (tip_x, tip_y),
            (base1_x, base1_y),
            (base2_x, base2_y)
        ])

        # Inner chevron detail
        inner_tip_x = chev_x + int(dx * chevron_size * 0.5)
        inner_tip_y = chev_y + int(dy * chevron_size * 0.5)
        pygame.draw.circle(faction_surface, ring_color, (int(inner_tip_x), int(inner_tip_y)), max(2, chevron_size // 4))

    # Add glow effect around the gate when ready
    if faction_power_ready:
        for i in range(3):
            glow_r = outer_radius + 2 + i
            glow_alpha = 80 - i * 25
            pygame.draw.circle(faction_surface, (*chevron_color, glow_alpha), (cx, cy), glow_r, 2)

    surface.blit(faction_surface, faction_rect.topleft)

    # Total score box lives to the right of the faction power circle.
    score_rect_width = max(0, column_right - (faction_rect.right + spacing))
    score_rect = pygame.Rect(faction_rect.right + spacing,
                             faction_rect.y,
                             score_rect_width,
                             faction_rect.height)
    if score_rect.width > 0:
        score_surface = pygame.Surface((score_rect.width, score_rect.height), pygame.SRCALPHA)
        score_surface.fill((20, 30, 50, 210))
        pygame.draw.rect(score_surface, faction_color, score_surface.get_rect(), width=4, border_radius=12)
        score_font = pygame.font.SysFont("Arial", max(24, int(26 * SCALE_FACTOR)), bold=True)
        score_text = score_font.render(str(player.score), True, WHITE)
        score_surface.blit(score_text, score_text.get_rect(center=score_surface.get_rect().center))
        surface.blit(score_surface, score_rect.topleft)
    else:
        score_rect = None

    y_cursor = faction_rect.bottom + spacing

    # Special faction button (Iris, Rings, etc.) appears above the leader portrait.
    special_rect = None
    special_kind = None
    if special_info:
        special_rect = pygame.Rect(0, y_cursor, special_size, special_size)
        special_rect.centerx = column_center_x
        special_surface = pygame.Surface((special_rect.width, special_rect.height), pygame.SRCALPHA)
        base_color = (28, 36, 50)
        ready_color = faction_color if special_info["ready"] else (90, 90, 100)
        if special_info["active"]:
            ready_color = (255, 120, 100)
        pygame.draw.circle(special_surface, base_color,
                           special_surface.get_rect().center, special_rect.width // 2)
        pygame.draw.circle(
            special_surface,
            ready_color,
            special_surface.get_rect().center,
            special_rect.width // 2,
            width=4
        )

        # Iconography per special kind.
        center = special_surface.get_rect().center
        if special_info["kind"] == "iris":
            blade_radius = int(special_rect.width * 0.35)
            for angle in range(0, 360, 45):
                radians = math.radians(angle)
                dx = int(math.cos(radians) * blade_radius)
                dy = int(math.sin(radians) * blade_radius)
                pygame.draw.line(
                    special_surface,
                    ready_color,
                    (center[0], center[1]),
                    (center[0] + dx, center[1] + dy),
                    width=3
                )
        else:
            inner_radius = int(special_rect.width * 0.18)
            for i in range(3):
                pygame.draw.circle(
                    special_surface,
                    ready_color,
                    center,
                    inner_radius + i * 6,
                    width=2
                )

        if hover_pos and special_rect.collidepoint(hover_pos):
            hover_color = tuple(min(255, c + 40) for c in ready_color[:3])
            pygame.draw.circle(
                special_surface,
                hover_color,
                special_surface.get_rect().center,
                special_rect.width // 2,
                width=2
            )
        surface.blit(special_surface, special_rect.topleft)
        special_kind = special_info["kind"]
        y_cursor = special_rect.bottom + spacing

    # Leader portrait occupies full card dimensions (no forced squishing).
    portrait_rect = pygame.Rect(
        column_center_x - leader_width // 2,
        y_cursor,
        leader_width,
        leader_height
    )
    leader_rect = draw_leader_portrait(
        surface,
        player,
        portrait_rect.x,
        portrait_rect.y,
        portrait_rect.width,
        portrait_rect.height,
        show_label=False
    )

    return {
        "leader_rect": leader_rect or portrait_rect,
        "ability_rect": ability_rect,
        "faction_rect": faction_rect,
        "score_rect": score_rect,
        "discard_rect": discard_hit_rect,
        "special_rect": special_rect,
        "special_kind": special_kind,
    }


def build_button_info_popup(kind, owner, anchor_rect, special_kind=None):
    """Create metadata describing the info popup for leader column buttons."""
    if not owner or not anchor_rect:
        return None

    color = FACTION_GLOW_COLORS.get(owner.faction, (255, 215, 0))
    title = "Info"
    lines = []

    if kind == "ability":
        leader_data = owner.leader or {}
        leader_name = leader_data.get("name", "Leader")
        ability_name = leader_data.get("ability", "Leader Ability")
        ability_desc = leader_data.get("ability_desc", ability_name)
        title = f"{leader_name} — Ability"
        lines = [ability_name, ability_desc]
    elif kind == "faction":
        power = getattr(owner, "faction_power", None)
        if power:
            title = f"{power.name}"
            lines = [power.description]
        else:
            title = f"{owner.faction} Power"
            lines = ["This faction has no special power assigned."]
    elif kind == "special":
        if special_kind == "iris" and hasattr(owner, "iris_defense"):
            status = "Active" if owner.iris_defense.is_active() else ("Ready" if owner.iris_defense.is_available() else "Spent")
            title = "Tau'ri Iris Defense"
            lines = [
                "Blocks the next enemy card as it emerges from the wormhole.",
                f"Status: {status}"
            ]
        elif special_kind == "rings" and getattr(owner, "ring_transportation", None):
            rt = owner.ring_transportation
            if rt.animation_in_progress:
                status = "Transferring..."
            elif rt.can_use():
                status = "Ready this round"
            else:
                status = "Used this round"
            title = "Goa'uld Ring Transportation"
            lines = [
                "Return one of your close-combat units to hand once per round.",
                f"Status: {status}"
            ]
        else:
            return None
    else:
        return None

    clean_lines = [line for line in lines if line]
    if not clean_lines:
        clean_lines = ["No additional details available."]

    return {
        "title": title,
        "lines": clean_lines,
        "anchor": anchor_rect.copy(),
        "color": color,
        "kind": kind,
        "special_kind": special_kind,
        "owner": owner,
        "expires_at": pygame.time.get_ticks() + 5000,
    }


def draw_button_info_popup(surface, popup):
    """Render the compact info popup near a leader column button."""
    if not popup:
        return

    anchor_rect = popup.get("anchor")
    if not anchor_rect:
        return

    padding = 14
    title_font = pygame.font.SysFont("Arial", max(20, int(20 * SCALE_FACTOR)), bold=True)
    body_font = pygame.font.SysFont("Arial", max(14, int(16 * SCALE_FACTOR)))
    max_text_width = max(int(320 * SCALE_FACTOR), 240)

    def wrap_line(text):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if body_font.size(candidate)[0] <= max_text_width - padding * 2:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if not lines:
            lines.append("")
        return lines

    wrapped_lines = []
    for entry in popup.get("lines", []):
        wrapped_lines.extend(wrap_line(entry))

    title_surface = title_font.render(popup.get("title", "Info"), True, popup.get("color", (255, 215, 0)))
    widest_line = title_surface.get_width()
    for line in wrapped_lines:
        line_width = body_font.size(line)[0]
        widest_line = max(widest_line, line_width)

    popup_width = min(max_text_width, max(widest_line + padding * 2, int(260 * SCALE_FACTOR)))
    body_line_height = body_font.get_linesize()
    popup_height = padding * 2 + title_surface.get_height()
    if wrapped_lines:
        popup_height += 8 + len(wrapped_lines) * body_line_height

    popup_rect = pygame.Rect(0, 0, popup_width, popup_height)
    place_right = anchor_rect.right + popup_width + 20 <= SCREEN_WIDTH
    if place_right:
        popup_rect.left = anchor_rect.right + 18
    else:
        popup_rect.right = anchor_rect.left - 18
    popup_rect.top = max(20, min(anchor_rect.centery - popup_height // 2, SCREEN_HEIGHT - popup_height - 20))

    popup_surface = pygame.Surface((popup_width, popup_height), pygame.SRCALPHA)
    popup_surface.fill((12, 20, 34, 235))
    pygame.draw.rect(popup_surface, popup.get("color", (255, 215, 0)),
                     popup_surface.get_rect(), width=3, border_radius=12)

    y_cursor = padding
    popup_surface.blit(title_surface, (padding, y_cursor))
    y_cursor += title_surface.get_height() + 8

    for line in wrapped_lines:
        text_surface = body_font.render(line, True, (225, 230, 240))
        popup_surface.blit(text_surface, (padding, y_cursor))
        y_cursor += body_line_height

    surface.blit(popup_surface, popup_rect.topleft)

def get_opponent_hand_card_center(total_cards, index):
    """Return the screen center position of an opponent hand slot by index."""
    hand_area_height = OPPONENT_HAND_HEIGHT
    hand_y = opponent_hand_area_y + (hand_area_height - CARD_HEIGHT) // 2
    card_spacing = int(CARD_WIDTH * 0.125)
    positions, _ = _compute_hand_positions(total_cards, CARD_WIDTH, card_spacing)
    if not positions:
        return (HAND_REGION_LEFT, hand_y + CARD_HEIGHT // 2)
    safe_index = max(0, min(index if index is not None else 0, len(positions) - 1))
    card_x = positions[safe_index]
    return (card_x + CARD_WIDTH // 2, hand_y + CARD_HEIGHT // 2)

def draw_weather_separator(surface, game):
    """Draw the weather lane plus glowing turn divider strip."""
    zone_rect = pygame.Rect(0, weather_y, SCREEN_WIDTH, WEATHER_ZONE_HEIGHT)
    zone_surface = pygame.Surface(zone_rect.size, pygame.SRCALPHA)
    zone_surface.fill((18, 28, 48, 220))
    surface.blit(zone_surface, zone_rect.topleft)

    pygame.draw.line(surface, (70, 90, 140), zone_rect.topleft, (zone_rect.right, zone_rect.top), 2)
    pygame.draw.line(surface, (70, 90, 140), (zone_rect.left, zone_rect.bottom), (zone_rect.right, zone_rect.bottom), 2)

    divider_height = min(WEATHER_ZONE_HEIGHT, pct_y(0.03))
    divider_rect = pygame.Rect(
        zone_rect.left,
        zone_rect.bottom - divider_height,
        zone_rect.width,
        divider_height
    )
    divider_surface = pygame.Surface(divider_rect.size, pygame.SRCALPHA)
    divider_surface.fill((255, 170, 60, 90))
    pygame.draw.rect(divider_surface, (255, 210, 120, 200), divider_surface.get_rect(), width=3, border_radius=6)
    surface.blit(divider_surface, divider_rect.topleft)

    turn_text = "YOUR TURN" if game.current_player == game.player1 else "ENEMY TURN"
    turn_color = (120, 255, 160) if game.current_player == game.player1 else (255, 140, 140)
    turn_font = pygame.font.SysFont("Arial", max(26, int(30 * SCALE_FACTOR)), bold=True)
    turn_surface = turn_font.render(turn_text, True, turn_color)
    turn_rect = turn_surface.get_rect(center=divider_rect.center)
    surface.blit(turn_surface, turn_rect)


def draw_lane_labels(surface):
    """Lane labels intentionally suppressed for cleaner UI."""
    return


def draw_board(surface, game, selected_card, dragging_card=None, drag_hover_highlight=None,
               drag_row_highlights=None):
    """Draw the game board, including contextual drop highlights."""
    draw_weather_separator(surface, game)
    draw_lane_labels(surface)
    draw_weather_slots(surface, game)
    draw_horn_slots(surface, game)
    
    # Darken inactive lanes (Witcher 3 polish)
    if game.player1.has_passed or game.current_player != game.player1:
        for row_name, row_rect in PLAYER_ROW_RECTS.items():
            dark_surface = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
            dark_surface.fill((0, 0, 0, 40))
            surface.blit(dark_surface, row_rect.topleft)
    
    # Subtle glow on active player's lanes (Witcher 3 polish)
    if game.current_player == game.player1 and not game.player1.has_passed:
        glow_alpha = 30
        for row_name, row_rect in PLAYER_ROW_RECTS.items():
            glow_surface = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
            glow_surface.fill((100, 150, 255, glow_alpha))
            surface.blit(glow_surface, row_rect.topleft)
    
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
            inflate_y = int(SCREEN_HEIGHT*0.006)
            pygame.draw.rect(surface, color, rect.inflate(0, inflate_y), width=3, border_radius=6)

    if drag_hover_highlight:
        rect = drag_hover_highlight["rect"]
        color = drag_hover_highlight["color"]
        alpha = drag_hover_highlight.get("alpha", 80)
        hover_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        hover_surface.fill((color[0], color[1], color[2], alpha))
        surface.blit(hover_surface, rect.topleft)
        inflate_y = int(SCREEN_HEIGHT*0.006)
        pygame.draw.rect(surface, color, rect.inflate(0, inflate_y), width=4, border_radius=6)

    # --- Draw cards on board (centered in their rows) ---
    row_map = {
        game.player2: OPPONENT_ROW_RECTS,
        game.player1: PLAYER_ROW_RECTS,
    }

    card_spacing = int(CARD_WIDTH * 0.125)  # Spacing between cards on board
    for player, rects in row_map.items():
        for row_name, row_rect in rects.items():
            cards_in_row = player.board[row_name]
            if not cards_in_row:
                continue
            
            # Calculate total width and center cards
            total_width = len(cards_in_row) * CARD_WIDTH + (len(cards_in_row) - 1) * card_spacing
            available_width = PLAYFIELD_WIDTH
            if total_width <= available_width:
                start_x = PLAYFIELD_LEFT + (available_width - total_width) // 2
            else:
                start_x = PLAYFIELD_LEFT

            for i, card in enumerate(cards_in_row):
                x = start_x + i * (CARD_WIDTH + card_spacing)

                # Center cards vertically within the row
                card_draw_y = row_rect.centery - CARD_HEIGHT // 2
                card.rect.topleft = (x, card_draw_y)
                if getattr(card, "in_transit", False):
                    continue
                draw_card(surface, card, x, card_draw_y)
    
def draw_scores(surface, game, anim_manager=None, p1_score_x=0, p1_score_y=0, p2_score_x=0, p2_score_y=0, render_static=True):
    """Draws the player scores and rounds won next to leader portraits."""
    if anim_manager and anim_manager.score_animations:
        anim_manager.draw_score_animations(surface, SCORE_FONT)
        if not render_static:
            return
    elif not render_static:
        return

    p1_color = (100, 255, 100) if game.player1.score > game.player2.score else WHITE
    p1_score_text = SCORE_FONT.render(f"Score: {game.player1.score}", True, p1_color)
    surface.blit(p1_score_text, (p1_score_x, p1_score_y))
    
    p2_color = (100, 255, 100) if game.player2.score > game.player1.score else WHITE
    p2_score_text = SCORE_FONT.render(f"Score: {game.player2.score}", True, p2_color)
    surface.blit(p2_score_text, (p2_score_x, p2_score_y))

    p1_rounds_text = UI_FONT.render(f"Rounds Won: {game.player1.rounds_won}", True, WHITE)
    p2_rounds_text = UI_FONT.render(f"Rounds Won: {game.player2.rounds_won}", True, WHITE)
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
    
    # Ability description (wrapped)
    ability_font = pygame.font.SysFont("Arial", 16)
    words = player.leader['ability'].split(' ')
    lines = []
    current_line = ""
    for word in words:
        if ability_font.size(current_line + " " + word)[0] < width - 20:
            current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    lines.append(current_line.strip())
    
    line_y = name_rect.bottom + 5
    for i, line in enumerate(lines):
        if line:
            ability_text = ability_font.render(line, True, (200, 255, 200))
            ability_rect = ability_text.get_rect(center=(width // 2, line_y + i * 15))
            box_surface.blit(ability_text, ability_rect)

    # Blit to main surface
    surface.blit(box_surface, (x, y))
    
    return pygame.Rect(x, y, width, height)  # Return rect for click detection

def draw_leader_portrait(surface, player, x, y, width=100, height=150, show_label=True):
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
    
    if show_label:
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
    """Jonas Quinn: Show cards drawn by opponent (not starting hand)."""
    if not game.opponent_drawn_cards:
        return

    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    # Title
    title_font = pygame.font.Font(None, 56)
    cards_count = len(game.opponent_drawn_cards)
    title_text = title_font.render(f"JONAS QUINN: Opponent Drew {cards_count} Card{'s' if cards_count > 1 else ''}", True, (100, 200, 255))
    title_rect = title_text.get_rect(center=(screen_width // 2, 80))
    surface.blit(title_text, title_rect)

    # Show all drawn cards
    card_display_width = 250
    card_display_height = 375
    spacing = 20
    total_width = len(game.opponent_drawn_cards) * (card_display_width + spacing) - spacing
    start_x = (screen_width - total_width) // 2
    card_y = 200

    for i, card in enumerate(game.opponent_drawn_cards):
        card_x = start_x + i * (card_display_width + spacing)

        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (card_x, card_y))
        pygame.draw.rect(surface, (100, 200, 255), pygame.Rect(card_x, card_y, card_display_width, card_display_height), width=3)

        # Card name below
        detail_font = pygame.font.Font(None, 24)
        name_text = detail_font.render(card.name, True, (200, 200, 200))
        name_rect = name_text.get_rect(center=(card_x + card_display_width // 2, card_y + card_display_height + 20))
        surface.blit(name_text, name_rect)

        # Power and row
        info_text = detail_font.render(f"{card.power}  •  {card.row.capitalize()}", True, (150, 150, 150))
        info_rect = info_text.get_rect(center=(card_x + card_display_width // 2, card_y + card_display_height + 45))
        surface.blit(info_text, info_rect)

    # Close instruction
    instruction_font = pygame.font.Font(None, 32)
    instruction = instruction_font.render("Click or Press SPACE to close", True, (150, 150, 150))
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

def draw_catherine_selection_overlay(surface, revealed_cards, screen_width, screen_height):
    """Catherine Langford: Reveal top cards and choose one to draw immediately."""
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((10, 10, 30, 220))
    surface.blit(overlay, (0, 0))

    title_font = pygame.font.Font(None, 58)
    title_text = title_font.render("CATHERINE LANGFORD — Ancient Knowledge", True, (235, 200, 120))
    title_rect = title_text.get_rect(center=(screen_width // 2, 90))
    surface.blit(title_text, title_rect)

    subtitle_font = pygame.font.Font(None, 34)
    subtitle_text = subtitle_font.render("Choose a card to draw immediately (others return to the deck bottom)", True, (230, 230, 230))
    subtitle_rect = subtitle_text.get_rect(center=(screen_width // 2, 140))
    surface.blit(subtitle_text, subtitle_rect)

    card_display_width = 280
    card_display_height = 420
    spacing = 70
    cards_to_show = revealed_cards[:3]
    count = max(1, len(cards_to_show))
    total_width = count * card_display_width + (count - 1) * spacing
    start_x = (screen_width - total_width) // 2
    card_y = 220

    card_rects = []
    for i, card in enumerate(cards_to_show):
        x = start_x + i * (card_display_width + spacing)
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, card_y))
        rect = pygame.Rect(x, card_y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (235, 200, 120), rect, width=4)
        name_text = UI_FONT.render(card.name[:22], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, card_y + card_display_height + 28))
        surface.blit(name_text, name_rect)
        card_rects.append((card, rect))

    instruction_font = pygame.font.Font(None, 32)
    instruction = instruction_font.render("Click a card to draw it now (it will be added to your hand to play immediately)", True, (200, 200, 200))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 70))
    surface.blit(instruction, instruction_rect)

    return card_rects

def draw_leader_choice_overlay(surface, ability_result, screen_width, screen_height):
    """Generic leader ability card selection UI (Jonas Quinn, Ba'al, etc.)"""
    ability_name = ability_result.get("ability", "Leader Ability")
    revealed_cards = ability_result.get("revealed_cards", [])

    # Title mapping
    titles = {
        "Eidetic Memory": ("JONAS QUINN — Eidetic Memory", "Choose a card to copy to your hand"),
        "System Lord's Cunning": ("BA'AL — System Lord's Cunning", "Choose a card to resurrect from your discard pile")
    }

    title_text, subtitle_text = titles.get(ability_name, (ability_name, "Choose a card"))

    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((10, 10, 30, 220))
    surface.blit(overlay, (0, 0))

    title_font = pygame.font.Font(None, 58)
    title = title_font.render(title_text, True, (235, 200, 120))
    title_rect = title.get_rect(center=(screen_width // 2, 90))
    surface.blit(title, title_rect)

    subtitle_font = pygame.font.Font(None, 34)
    subtitle = subtitle_font.render(subtitle_text, True, (230, 230, 230))
    subtitle_rect = subtitle.get_rect(center=(screen_width // 2, 140))
    surface.blit(subtitle, subtitle_rect)

    card_display_width = 240
    card_display_height = 360
    spacing = 40
    max_per_row = 5

    card_rects = []
    for idx, card in enumerate(revealed_cards[:10]):  # Max 10 cards
        row = idx // max_per_row
        col = idx % max_per_row

        cards_in_row = min(max_per_row, len(revealed_cards) - row * max_per_row)
        total_width = cards_in_row * card_display_width + (cards_in_row - 1) * spacing
        start_x = (screen_width - total_width) // 2

        x = start_x + col * (card_display_width + spacing)
        y = 220 + row * (card_display_height + 80)

        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        rect = pygame.Rect(x, y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (235, 200, 120), rect, width=4)

        name_text = UI_FONT.render(card.name[:20], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 20))
        surface.blit(name_text, name_rect)

        card_rects.append((card, rect))

    instruction_font = pygame.font.Font(None, 32)
    instruction = instruction_font.render("Click a card to select it", True, (200, 200, 200))
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 70))
    surface.blit(instruction, instruction_rect)

    return card_rects

def run_game_with_context(screen, context):
    """
    Main game loop, but initialized with a specific LAN context.
    """
    # Set global LAN context
    global LAN_MODE, LAN_CONTEXT
    LAN_MODE = True
    LAN_CONTEXT = context
    
    # Initialize unlock system (needed for DeckManager)
    from unlocks import CardUnlockSystem
    unlock_system = CardUnlockSystem()
    
    # Initialize game with LAN context decks/leaders
    # Local player is player1, Remote player is player2
    player1_deck = [ALL_CARDS[cid] for cid in context.local.deck_ids if cid in ALL_CARDS]
    player2_deck = [ALL_CARDS[cid] for cid in context.remote.deck_ids if cid in ALL_CARDS]
    
    # Find leader cards
    from deck_builder import FACTION_LEADERS
    def find_leader(faction, leader_id):
        # Check base leaders
        for leader in FACTION_LEADERS.get(faction, []):
            if leader.get("card_id") == leader_id:
                return leader
        # Check unlockable leaders
        from content_registry import UNLOCKABLE_LEADERS
        if faction in UNLOCKABLE_LEADERS:
            for leader in UNLOCKABLE_LEADERS[faction]:
                if leader.get("card_id") == leader_id:
                    return leader
        # Fallback
        return FACTION_LEADERS.get(faction, [{}])[0]

    player1_leader = find_leader(context.local.faction, context.local.leader_id)
    player2_leader = find_leader(context.remote.faction, context.remote.leader_id)
    
    game = Game(
        player1_faction=context.local.faction,
        player1_deck=player1_deck,
        player1_leader=player1_leader,
        player2_faction=context.remote.faction,
        player2_deck=player2_deck,
        player2_leader=player2_leader,
        seed=context.seed
    )
    
    # Initialize Network Controller for player 2
    from lan_opponent import NetworkController, NetworkPlayerProxy
    network_controller = NetworkController(game, game.player2, context.session, context.role)
    network_proxy = NetworkPlayerProxy(context.session, context.role)
    
    # Assign controller to game logic variables used in main loop
    # We need to inject this into the main game loop scope
    # Ideally main() should be refactored to accept these, but for now we'll hijack the globals/locals
    # Actually, run_game_loop() is what we want to call, passing these.
    
    # Since main.py is a script, we'll reuse the logic by calling a shared loop function
    # But main() is currently monolithic.
    # We will run a modified version of the game loop here.
    
    # ... ACTUALLY, main() is huge. duplicating it is bad.
    # Refactoring main() into run_game_loop() is the right way, but risky for this task.
    # Instead, I will call the internal loop logic if I can expose it.
    
    # Let's look at how I can inject this.
    # The easiest way without huge refactor is to set global variables that main() checks?
    # No, main() creates its own Game object.
    
    # I will rename `main()` to `run_game_loop(game_instance=None, network_ctrl=None)` 
    # and have `main` call `run_game_loop()`.
    
    # But wait, I can't easily rename main() in one go if it's 5000 lines.
    # I will define run_game_with_context to essentially COPY the necessary setup and then run the loop.
    # OR, I can implement `run_game_loop` by extracting the while loop from `main`.
    
    # Given the constraints, I will assume `main.py` has a `main()` function that does everything.
    # I will implement `run_game_with_context` by modifying `main` to accept arguments.
    pass

def main(external_game=None, external_network=None):
    # ... existing main code ...
    # When creating game:
    if external_game:
        game = external_game
        ai_controller = external_network # This will be the network controller
    else:
        # ... existing game creation ...
        pass


def main(lan_game_data=None):
    """Main game loop.

    Args:
        lan_game_data: Optional dict with LAN game info to skip menu/deck builder.
                      Keys: 'game', 'player_faction', 'player_leader', 'ai_faction', 'ai_leader'
    """
    global MULLIGAN_BUTTON_RECT, screen, SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_FACTOR

    # If LAN game data provided, skip menu and deck builder
    if lan_game_data:
        game = lan_game_data['game']
        player_faction = lan_game_data['player_faction']
        player_leader = lan_game_data['player_leader']
        ai_faction = lan_game_data['ai_faction']
        ai_leader = lan_game_data['ai_leader']
        # Player deck is already in game.player1.hand/deck
        # AI deck is already in game.player2.hand/deck
    else:
        # Normal flow - show menu and deck builder

        # Initialize card unlock system
        unlock_system = CardUnlockSystem()
        deck_manager = DeckManager(unlock_system)

        # --- SHOW MAIN MENU FIRST ---
        menu_result = run_main_menu(screen, unlock_system, toggle_fullscreen_mode)

        if isinstance(menu_result, dict) and 'session' in menu_result:
            from lan_game import run_lan_setup, run_lan_match
            lan_context = run_lan_setup(
                screen,
                unlock_system,
                menu_result['session'],
                menu_result.get('role', 'host'),
                toggle_fullscreen_callback=toggle_fullscreen_mode
            )
            if lan_context:
                run_lan_match(screen, lan_context)
            main()
            return

        is_draft_mode = False  # Track if this is a draft mode game

        if menu_result == 'draft_mode':
            # Launch Draft Mode
            from draft_controller import launch_draft_mode
            drafted_deck = launch_draft_mode(screen, unlock_system)

            if drafted_deck is None:
                # User exited draft mode - return to main menu
                main()
                return

            # Use the drafted deck for the game
            is_draft_mode = True
            player_leader = drafted_deck['leader']
            player_deck = drafted_deck['cards']
            player_faction = player_leader.get('faction', 'Neutral')

        elif menu_result == 'new_game':
            # --- SHOW STARGATE OPENING ANIMATION ---
            if not show_stargate_opening(screen):
                # User closed window during animation
                pygame.quit()
                sys.exit()

            # Sync display mode in case menu/rules toggled fullscreen
            sync_fullscreen_from_surface()

            # --- RUN DECK BUILDER FOR FACTION/LEADER SELECTION ---
            deck_selection = run_deck_builder(
                screen,
                unlock_override=unlock_system.is_unlock_override_enabled(),
                unlock_system=unlock_system,
                toggle_fullscreen_callback=toggle_fullscreen_mode
            )

            if deck_selection is None:
                # User cancelled - go back to main menu
                main()
                return

            # Build player deck based on selection
            player_faction = deck_selection['faction']
            player_leader = dict(deck_selection['leader'])
            player_leader.setdefault('faction', player_faction)
            player_deck_ids = deck_selection['deck_ids']

            # Check if player has a custom deck for this faction
            deck_manager.load_decks()  # Reload in case the player saved new changes in the deck builder
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
        else:
            pygame.quit()
            sys.exit()

        # AI gets a random faction (different from player) and random leader
        from cards import FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD
        from deck_builder import FACTION_LEADERS
        available_ai_factions = [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD]
        available_ai_factions.remove(player_faction)
        import random
        ai_faction = random.choice(available_ai_factions)
        ai_leader = dict(random.choice(FACTION_LEADERS[ai_faction]))  # AI gets random leader
        ai_leader.setdefault('faction', ai_faction)
        ai_deck_ids = build_faction_deck(ai_faction, ai_leader)
        ai_deck = [ALL_CARDS[id] for id in ai_deck_ids]
    
    # Initialize Mulligan button near bottom-right (stays above player hand zone)
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

    # Create game with player's selections (skip if LAN - game already created)
    if not lan_game_data:
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

    # Show leader matchup animation (skip if LAN - already shown in lan_setup)
    if not lan_game_data:
        from leader_matchup import LeaderMatchupAnimation
        matchup_anim = LeaderMatchupAnimation(player_leader, ai_leader, SCREEN_WIDTH, SCREEN_HEIGHT)
        clock_matchup = pygame.time.Clock()
        while not matchup_anim.finished:
            dt = clock_matchup.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEWHEEL:
                    if history_panel_rect and history_panel_rect.collidepoint(pygame.mouse.get_pos()):
                        history_scroll_offset = max(0, min(history_scroll_limit, history_scroll_offset - event.y * HISTORY_ENTRY_HEIGHT))
                        history_manual_scroll = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_SPACE:
                        matchup_anim.finished = True  # Allow skipping

            matchup_anim.update(dt)
            matchup_anim.draw(screen)
            pygame.display.flip()

        # Show game start animation
        show_game_start_animation(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)

    # Start round-based battle music (round 1)
    set_battle_music_round(1, immediate=True)
    
    # Initialize controller (AI or Network depending on mode)
    if LAN_MODE and LAN_CONTEXT:
        # LAN multiplayer mode - use NetworkController
        from lan_opponent import NetworkController, NetworkPlayerProxy
        ai_controller = NetworkController(game, game.player2, LAN_CONTEXT.session, LAN_CONTEXT.role)
        network_proxy = NetworkPlayerProxy(LAN_CONTEXT.session, LAN_CONTEXT.role)
        print(f"[LAN] Running in {LAN_CONTEXT.role} mode with NetworkController")
    else:
        # Single player mode - use AIController (always hardest)
        ai_controller = AIController(game, game.player2, difficulty="hard")
        network_proxy = None

    # Initialize chat panel for LAN mode
    lan_chat_panel = None
    if LAN_MODE and LAN_CONTEXT:
        from lan_chat import LanChatPanel
        
        # Callback: When chat message arrives/sent, push to Game History
        def push_chat_to_history(prefix, text, color):
            # Only add to history if it's actual chat (avoid duplicates if we re-enabled system loop)
            # But since we removed the system->chat loop, this is safe.
            owner = "player" if prefix == "You" else "ai"
            game.add_history_event("chat", f"{prefix}: {text}", owner, icon='"')

        lan_chat_panel = LanChatPanel(
            LAN_CONTEXT.session, 
            LAN_CONTEXT.role, 
            max_lines=12, 
            on_message=push_chat_to_history
        )
        
        lan_chat_panel.add_message("System", f"Connected as {LAN_CONTEXT.role}. Type 'T' to chat!")
        print("[LAN] Chat panel initialized")

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
    mulligan_local_done = False
    mulligan_remote_done = not LAN_MODE
    inspected_card = None  # Card being inspected with spacebar
    inspected_leader = None  # Leader being inspected
    player_leader_rect = None
    ai_leader_rect = None
    player_ability_rect = None
    ai_ability_rect = None
    
    # UI State Machine Initialization
    ui_state = UIState.PLAYING
    
    # State Data Holders
    medic_card_played = None  # The medic card that was just played
    decoy_card_played = None  # The decoy card that was just played
    ring_transport_animation = None  # Active ring transportation animation
    ring_transport_selection = False  # Flag for Ring Transport (Decoy) selection mode
    ring_transport_button_rect = None  # Ring button for click detection
    decoy_drag_target = None  # Card being hovered over when dragging Ring Transport
    decoy_valid_targets = []  # List of (card, rect) for valid decoy targets
    iris_button_rect = None  # Iris button for click detection
    previous_round = game.round_number  # Track round changes
    previous_weather = {"close": False, "ranged": False, "siege": False}  # Track weather changes
    
    # Discard pile viewer data
    discard_scroll = 0  # Scroll offset for discard viewer
    discard_rect = None  # Assigned during draw phase
    
    # Leader ability selection data
    vala_cards_to_choose = []  # The 3 cards Vala can choose from
    catherine_cards_to_choose = []  # Cached revealed cards for Catherine
    thor_selected_unit = None  # The unit Thor is moving
    pending_leader_choice = None  # Generic leader ability card selection (Jonas Quinn, Ba'al, etc.)
    
    # History/column state
    history_scroll_offset = 0
    history_scroll_limit = 0
    history_manual_scroll = False
    history_entry_hitboxes = []
    history_panel_rect = None
    player_faction_button_rect = None
    player_ability_ready = False
    ai_ability_ready = False
    ai_faction_button_rect = None
    player_special_button_rect = None
    player_special_button_kind = None
    ai_special_button_rect = None
    ai_special_button_kind = None
    button_info_popup = None

    # Pass buttons (command bar + HUD)
    hud_pass_button_size = max(80, int(SCREEN_HEIGHT * 0.04))
    HUD_PASS_BUTTON_RECT = pygame.Rect(
        HUD_LEFT + (HUD_WIDTH - hud_pass_button_size) // 2,
        pct_y(0.94) - hud_pass_button_size // 2,
        hud_pass_button_size,
        hud_pass_button_size
    )
    
    faction_power_effect = None  # Active Iris Power visual effect
    
    # Debug overlay toggle (F3 key)
    debug_overlay_enabled = False
    
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
        enforce_display_mode()
        dt = clock.tick(144)  # 144 FPS for buttery smooth animations and card movement
        update_battle_music()

        # Poll chat messages in LAN mode
        if lan_chat_panel:
            lan_chat_panel.poll_session()

        # Check for LAN disconnect
        if LAN_MODE and LAN_CONTEXT:
            if not LAN_CONTEXT.session.is_connected():
                # Show disconnect message
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                screen.blit(overlay, (0, 0))

                font_large = pygame.font.SysFont("Arial", 60, bold=True)
                font_small = pygame.font.SysFont("Arial", 30)

                # Disconnect message
                text1 = font_large.render("CONNECTION LOST", True, (255, 100, 100))
                text2 = font_small.render("Your opponent has disconnected", True, (200, 200, 200))
                text3 = font_small.render("Press any key to return to menu", True, (150, 150, 150))

                screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, SCREEN_HEIGHT // 2 - 80))
                screen.blit(text2, (SCREEN_WIDTH // 2 - text2.get_width() // 2, SCREEN_HEIGHT // 2))
                screen.blit(text3, (SCREEN_WIDTH // 2 - text3.get_width() // 2, SCREEN_HEIGHT // 2 + 60))

                pygame.display.flip()

                # Wait for key press
                waiting = True
                while waiting:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                            waiting = False

                # Clean up and return to menu
                LAN_CONTEXT.session.close()
                stop_battle_music()
                main()
                return

        # Handle remote mulligan selections in LAN mode
        if LAN_MODE and LAN_CONTEXT and game.game_state == "mulligan" and not mulligan_remote_done:
            # Timeout after 30 seconds to prevent infinite loops
            mulligan_timeout = 30000  # 30 seconds in milliseconds
            mulligan_start_time = pygame.time.get_ticks()
            max_iterations = 1000  # Safety limit on iterations
            iteration_count = 0

            while iteration_count < max_iterations:
                # Check timeout
                if pygame.time.get_ticks() - mulligan_start_time > mulligan_timeout:
                    print("WARNING: Mulligan timeout reached, proceeding without remote mulligan")
                    mulligan_remote_done = True
                    break

                iteration_count += 1
                msg = LAN_CONTEXT.session.receive()
                if not msg:
                    break
                try:
                    parsed = parse_message(msg)
                except ValueError:
                    continue

                msg_type = parsed.get("type")
                if msg_type == LanMessageType.MULLIGAN.value:
                    payload = parsed.get("payload", {})
                    indices = payload.get("indices", [])
                    remote_cards = []
                    for idx in indices:
                        if isinstance(idx, int) and 0 <= idx < len(game.player2.hand):
                            remote_cards.append(game.player2.hand[idx])
                    if remote_cards:
                        game.mulligan(game.player2, remote_cards)
                    mulligan_remote_done = True
                    continue

                # Not a mulligan message - put it back for game logic
                LAN_CONTEXT.session.inbox.put(parsed)
                break

        if game.game_state == "mulligan" and mulligan_local_done and mulligan_remote_done:
            game.end_mulligan_phase()

        if getattr(game, "history_dirty", False):
            if not history_manual_scroll:
                history_scroll_offset = 0
            game.history_dirty = False
        history_entry_hitboxes = []
        player_ability_ready = not game.leader_ability_used.get(game.player1, False)
        ai_ability_ready = not game.leader_ability_used.get(game.player2, False)
        
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

            # Update battle music for new round (more intense each round)
            set_battle_music_round(game.round_number, immediate=True)
        
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
                if ability_result.get("requires_ui") and ability_name == "Ancient Knowledge":
                    revealed = ability_result.get("revealed_cards") or []
                    if revealed:
                        chosen_card = max(revealed, key=lambda c: getattr(c, "power", 0))
                        game.catherine_play_chosen_card(game.player2, chosen_card)
                anim_manager.add_effect(create_ability_animation(
                    ability_name,
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 3
                ))
                for row_name in ability_result.get("rows", []):
                    weather_target = game.weather_row_targets.get(row_name, "both")
                    weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                    if weather_target in ("player1", "both"):
                        rect = PLAYER_ROW_RECTS.get(row_name)
                        if rect:
                            anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                            # Add row weather visual effect (meteorites, nebula, etc.)
                            anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                    if weather_target in ("player2", "both"):
                        rect = OPPONENT_ROW_RECTS.get(row_name)
                        if rect:
                            anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                            # Add row weather visual effect (meteorites, nebula, etc.)
                            anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)

        # Update animations
        anim_manager.update(dt)

        # Check if Hathor's ability animation is complete
        if hasattr(game, 'hathor_steal_info') and game.hathor_steal_info:
            # Check if the animation is complete
            animation_complete = True
            for animation in anim_manager.animations:
                if isinstance(animation, HathorStealAnimation) and not animation.finished:
                    animation_complete = False
                    break
            
            if animation_complete:
                # Clear the steal info
                game.hathor_steal_info = None
        
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
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Handle chat input in LAN mode FIRST (takes priority except for ESC and F11)
                if lan_chat_panel and lan_chat_panel.active and event.key not in (pygame.K_ESCAPE, pygame.K_F11, pygame.K_F3):
                    lan_chat_panel.handle_event(event)
                    continue  # Skip other key handlers when typing in chat

                # F3 - Toggle debug overlay
                if event.key == pygame.K_F3:
                    debug_overlay_enabled = not debug_overlay_enabled
                    print(f"🔍 Debug Overlay: {'ENABLED' if debug_overlay_enabled else 'DISABLED'}")
                
                # Debug: Print all key presses
                elif event.key == pygame.K_F11:
                    print(f"🔑 DEBUG: F11 key detected (keycode: {event.key})")
                
                # ESC to toggle pause menu or close overlays
                if event.key == pygame.K_ESCAPE:
                    if inspected_card or inspected_leader:
                        inspected_card = None
                        inspected_leader = None
                    elif ui_state == UIState.DISCARD_VIEW:
                        ui_state = UIState.PLAYING
                        discard_scroll = 0
                    elif ui_state == UIState.JONAS_PEEK:
                        ui_state = UIState.PLAYING
                        # Clear the tracked cards after viewing
                        game.opponent_drawn_cards = []
                    elif ui_state == UIState.LAN_CHAT:
                        ui_state = UIState.PLAYING
                    elif game.game_state == "playing":
                        if ui_state == UIState.PAUSED:
                            ui_state = UIState.PLAYING
                        else:
                            ui_state = UIState.PAUSED
                
                # Toggle fullscreen with F11 or Alt+Enter
                elif event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                    print(f"🔑 Fullscreen toggle requested. Current state: {FULLSCREEN}")
                    toggle_fullscreen_mode()
                    fullscreen = FULLSCREEN
                    
                    # Recalculate UI button positions for new resolution
                    hud_pass_button_size = max(80, int(SCREEN_HEIGHT * 0.04))
                    HUD_PASS_BUTTON_RECT = pygame.Rect(
                        HUD_LEFT + (HUD_WIDTH - hud_pass_button_size) // 2,
                        pct_y(0.94) - hud_pass_button_size // 2,
                        hud_pass_button_size,
                        hud_pass_button_size
                    )
                    MULLIGAN_BUTTON_RECT = pygame.Rect(
                        SCREEN_WIDTH - int(300 * SCALE_FACTOR),
                        SCREEN_HEIGHT - int(160 * SCALE_FACTOR),
                        int(200 * SCALE_FACTOR),
                        int(50 * SCALE_FACTOR)
                    )
                    
                    mode_label = "ON" if fullscreen else "OFF"
                    print(f"✓ Fullscreen: {mode_label} - Resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
                    print(f"  Scale Factor: {SCALE_FACTOR:.2f}")
                
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
                                game.add_history_event(
                                    "faction_power",
                                    f"{game.player1.name} used {game.player1.faction_power.name}",
                                    "player"
                                )
                                # Send over network in LAN mode
                                if network_proxy:
                                    network_proxy.send_faction_power(game.player1.faction_power.name)
                                # Recalculate scores
                                game.player1.calculate_score()
                                game.player2.calculate_score()
                                print(f"✓ Faction Power activated with F key: {game.player1.faction_power.name}")
                
                # T key = Toggle LAN Chat Input
                elif event.key == pygame.K_t or event.key == pygame.K_RETURN:
                    if lan_chat_panel and not lan_chat_panel.active:
                        lan_chat_panel.active = True
                        # Consume the key press so it doesn't type 't' into the box immediately
                        continue
                    elif lan_chat_panel and lan_chat_panel.active and event.key == pygame.K_t:
                         # Allow closing with T if empty? No, T is a letter. ESC closes.
                         pass
                
                # SPACEBAR = Alternative preview (same as right-click)
                elif event.key == pygame.K_SPACE:
                    if inspected_card or inspected_leader:
                        # Close preview
                        inspected_card = None
                        inspected_leader = None
                    elif ui_state in (UIState.DISCARD_VIEW, UIState.JONAS_PEEK):
                        # Close overlays
                        if ui_state == UIState.JONAS_PEEK:
                            # Clear the tracked cards after viewing
                            game.opponent_drawn_cards = []
                        ui_state = UIState.PLAYING
                        discard_scroll = 0
                    elif selected_card and game.game_state == "playing":
                        # Preview selected card
                        inspected_card = selected_card
                
                # Game over screen - R to restart
                if game.game_state == "game_over":
                    if event.key == pygame.K_r:
                        stop_battle_music()
                        main()
                        return
                    elif event.key == pygame.K_ESCAPE:
                        running = False
            elif event.type == pygame.MOUSEWHEEL:
                if history_panel_rect and history_panel_rect.collidepoint(pygame.mouse.get_pos()):
                    history_scroll_offset = max(0, min(history_scroll_limit, history_scroll_offset - event.y * HISTORY_ENTRY_HEIGHT))
                    history_manual_scroll = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (4, 5):
                    if history_panel_rect and history_panel_rect.collidepoint(event.pos):
                        delta = HISTORY_ENTRY_HEIGHT if event.button == 4 else -HISTORY_ENTRY_HEIGHT
                        history_scroll_offset = max(0, min(history_scroll_limit, history_scroll_offset - delta))
                        history_manual_scroll = True
                    continue
                if event.button == 1:
                    button_info_popup = None
                if game.current_player == game.player1:
                    # Handle leader ability click
                    if player_ability_rect and player_ability_rect.collidepoint(event.pos):
                        # If the leader is Hathor, handle her ability specifically
                        if game.player1.leader and "Hathor" in game.player1.leader.get('name', ''):
                            if game.trigger_hathor_ability(game.player1):
                                # Start the animation
                                steal_info = game.hathor_steal_info
                                if steal_info:
                                    # Calculate start and end positions
                                    start_pos = (
                                        steal_info['card'].rect.centerx,
                                        steal_info['card'].rect.centery
                                    )
                                    
                                    # Find the target row position
                                    target_row = steal_info['to_player'].hathor_ability_pending['target_row']
                                    target_row_rect = PLAYER_ROW_RECTS[target_row]
                                    end_pos = (
                                        target_row_rect.centerx,
                                        target_row_rect.centery
                                    )
                                    
                                    # Create and start the animation
                                    animation = HathorStealAnimation(
                                        steal_info['card'],
                                        start_pos,
                                        end_pos,
                                        on_finish=lambda: game.switch_turn()
                                    )
                                    anim_manager.add_animation(animation)
                                    steal_info["animation_started"] = True
                                    if network_proxy:
                                        network_proxy.send_leader_ability(
                                            "Hathor Steal",
                                            {
                                                "from_row": steal_info.get("from_row"),
                                                "from_index": steal_info.get("from_index"),
                                                "target_row": steal_info.get("target_row"),
                                                "card_id": steal_info.get("card_id"),
                                            }
                                        )
                            # After attempting Hathor's ability, don't process any other click logic for this event
                            continue
                        else:
                            # For any other leader, use the generic activation
                            result = game.activate_leader_ability(game.player1)
                            if result:
                                if result.get("requires_ui"):
                                    ability_name = result.get("ability", "")
                                    if ability_name == "Ancient Knowledge":
                                        # Catherine Langford
                                        ui_state = UIState.CATHERINE_SELECT
                                        catherine_cards_to_choose = result.get("revealed_cards", [])
                                    elif ability_name in ["Eidetic Memory", "System Lord's Cunning"]:
                                        # Jonas Quinn or Ba'al
                                        pending_leader_choice = result
                                        ui_state = UIState.LEADER_CHOICE_SELECT
                                elif result.get("rows"):
                                    # Weather ability (Apophis) - show weather visual effects
                                    ability_name = result.get("ability", "Weather Decree")
                                    if network_proxy:
                                        network_proxy.send_leader_ability(
                                            ability_name,
                                            {"rows": result.get("rows", [])}
                                        )
                                    anim_manager.add_effect(create_ability_animation(
                                        ability_name,
                                        SCREEN_WIDTH // 2,
                                        SCREEN_HEIGHT // 3
                                    ))
                                    for row_name in result.get("rows", []):
                                        weather_target = game.weather_row_targets.get(row_name, "both")
                                        weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                                        if weather_target in ("player1", "both"):
                                            rect = PLAYER_ROW_RECTS.get(row_name)
                                            if rect:
                                                anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                                                anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                                        if weather_target in ("player2", "both"):
                                            rect = OPPONENT_ROW_RECTS.get(row_name)
                                            if rect:
                                                anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                                                anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                                else:
                                    if network_proxy:
                                        ability_name = result.get("ability", game.player1.leader.get("name", "leader_ability"))
                                        network_proxy.send_leader_ability(ability_name, {})
                # RIGHT CLICK = Card Preview/Zoom or Discard Pile View
                if event.button == 3:  # Right click
                    button_info_popup = None
                    popup_targets = []
                    if player_ability_rect:
                        popup_targets.append(("ability", game.player1, player_ability_rect, None))
                    if ai_ability_rect:
                        popup_targets.append(("ability", game.player2, ai_ability_rect, None))
                    if player_faction_button_rect:
                        popup_targets.append(("faction", game.player1, player_faction_button_rect, None))
                    if ai_faction_button_rect:
                        popup_targets.append(("faction", game.player2, ai_faction_button_rect, None))
                    if player_special_button_rect and player_special_button_kind:
                        popup_targets.append(("special", game.player1, player_special_button_rect, player_special_button_kind))
                    if ai_special_button_rect and ai_special_button_kind:
                        popup_targets.append(("special", game.player2, ai_special_button_rect, ai_special_button_kind))

                    popup_triggered = False
                    for kind, owner, rect, special_kind in popup_targets:
                        if rect and rect.collidepoint(event.pos):
                            new_popup = build_button_info_popup(kind, owner, rect, special_kind)
                            if new_popup:
                                button_info_popup = new_popup
                            popup_triggered = True
                            break
                    if popup_triggered:
                        continue

                    history_clicked = False
                    for entry, rect in history_entry_hitboxes:
                        if rect.collidepoint(event.pos):
                            history_clicked = True
                            if getattr(entry, "card_ref", None):
                                inspected_card = entry.card_ref
                                selected_card = None
                            break
                    if history_clicked:
                        continue
                    # Check if right-clicking discard pile to view it
                    if discard_rect and discard_rect.collidepoint(event.pos) and ui_state != UIState.DISCARD_VIEW:
                        ui_state = UIState.DISCARD_VIEW
                        discard_scroll = 0
                        continue
                    
                    # Check if right-clicking a card in the discard viewer to inspect it
                    if ui_state == UIState.DISCARD_VIEW:
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
                        ui_state = UIState.PLAYING
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
                if discard_rect and discard_rect.collidepoint(event.pos) and ui_state != UIState.DISCARD_VIEW:
                    ui_state = UIState.DISCARD_VIEW
                    discard_scroll = 0
                
                # Close discard viewer with click
                if ui_state == UIState.DISCARD_VIEW and event.button == 1:
                    ui_state = UIState.PLAYING
                
                # Handle discard scroll with mouse wheel
                if ui_state == UIState.DISCARD_VIEW and event.button in [4, 5]:
                    if event.button == 4:  # Scroll up
                        discard_scroll = min(0, discard_scroll + 50)
                    else:  # Scroll down
                        discard_scroll -= 50
                
                # Handle medic selection mode
                if ui_state == UIState.MEDIC_SELECT:
                    # Check if clicking on a card in the medic selection overlay
                    # This will be handled after drawing
                    pass
                
                # Check if clicking Faction Power button (player only)
                if (game.game_state == "playing"
                        and game.current_player == game.player1
                        and player_faction_button_rect
                        and player_faction_button_rect.collidepoint(event.pos)):
                    if game.player1.faction_power and game.player1.faction_power.is_available():
                        if game.player1.faction_power.activate(game, game.player1):
                            faction_power_effect = FactionPowerEffect(
                                game.player1.faction,
                                SCREEN_WIDTH // 2,
                                SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT
                            )
                            game.add_history_event(
                                "faction_power",
                                f"{game.player1.name} used {game.player1.faction_power.name}",
                                "player"
                            )
                            # Send over network in LAN mode
                            if network_proxy:
                                network_proxy.send_faction_power(game.player1.faction_power.name)
                            # Track ability usage
                            game.ability_usage["faction_power"] = game.ability_usage.get("faction_power", 0) + 1
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
                    if mulligan_local_done:
                        continue

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
                        selected_indices = [i for i, card in enumerate(game.player1.hand) if card in mulligan_selected]
                        game.mulligan(game.player1, mulligan_selected)
                        game.player_mulligan_count = len(selected_indices)
                        mulligan_local_done = True
                        mulligan_selected = []

                        if network_proxy:
                            network_proxy.send_mulligan(selected_indices)
                        else:
                            # Single-player: Use AI strategy for mulligan
                            from ai_opponent import AIStrategy
                            ai_strategy = AIStrategy(game, game.player2)
                            ai_cards = ai_strategy.decide_mulligan()
                            game.mulligan(game.player2, ai_cards)
                            mulligan_remote_done = True
                            game.end_mulligan_phase()
                
                # Playing phase - START DRAG
                elif game.game_state == "playing":
                    if game.current_player == game.player1 and not game.player1.has_passed:
                        # Check if clicking on pass buttons
                        pass_clicked = False
                        if HUD_PASS_BUTTON_RECT and HUD_PASS_BUTTON_RECT.collidepoint(event.pos):
                            selected_card = None
                            dragging_card = None
                            drag_velocity = Vector2()
                            drag_pickup_flash = 0.0
                            anim_manager.add_effect(StargateActivationEffect(HUD_PASS_BUTTON_RECT.centerx,
                                                                             HUD_PASS_BUTTON_RECT.centery,
                                                                             duration=800))
                            game.pass_turn()

                            # Send network action if in LAN mode
                            if network_proxy:
                                network_proxy.send_pass()

                            pass_clicked = True
                        if pass_clicked:
                            continue
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
                                ui_state = UIState.RING_TRANSPORT_SELECT
                        else:
                            # Ring Transport selection mode - clicking a card on player's board
                            if ui_state == UIState.RING_TRANSPORT_SELECT:
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
                                        
                                        ui_state = UIState.PLAYING
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
                                            # This card is played by dragging and dropping, so do nothing on a double-click.
                                            pass
                                        else:
                                            # Check if this is Wormhole Stabilization (Clear Weather)
                                            if "Wormhole Stabilization" in (card.ability or ""):
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
                    ability_lower = ability_text.lower()
                    
                    # Weather and special cards can target any row
                    if dragging_card.row in ["weather", "special"]:
                        if dragging_card.row == "weather":
                            target_row = None
                            drop_rect = None
                            # First, allow dropping onto dedicated weather slots
                            for row_name, slot_rect in WEATHER_SLOT_RECTS.items():
                                if slot_rect.collidepoint(event.pos):
                                    target_row = row_name
                                    drop_rect = slot_rect
                                    break
                            # Fallback to full row targets if player drags over the battlefield
                            if target_row is None:
                                for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                                    for row_name, rect in rects.items():
                                        if rect.collidepoint(event.pos):
                                            target_row = row_name
                                            drop_rect = rect
                                            break
                                    if target_row:
                                        break
                            if target_row:
                                played = True
                                if "wormhole stabilization" in ability_lower:
                                    anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                                else:
                                    effect_x = drop_rect.centerx
                                    effect_y = drop_rect.centery
                                    anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=800))
                                    if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                                        for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                                            row_rect = rects.get(target_row)
                                            if row_rect:
                                                anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))
                                game.play_card(dragging_card, target_row)

                                # Send network action if in LAN mode
                                if network_proxy:
                                    network_proxy.send_play_card(dragging_card.id, target_row)
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
                                    if game.play_ring_transport(dragging_card, decoy_drag_target):
                                        # Show ring transport animation with golden rings
                                        from power import RingTransportAnimation
                                        start_pos = (decoy_drag_target.rect.centerx, decoy_drag_target.rect.centery)
                                        # End position is player's hand area
                                        end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
                                        ring_transport_animation = RingTransportAnimation(
                                            decoy_drag_target, start_pos, end_pos,
                                            SCREEN_WIDTH, SCREEN_HEIGHT
                                        )
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
                                    
                                    # Calculate insertion index
                                    target_player = game.player2 if is_spy else game.player1
                                    row_cards = target_player.board[row_name]
                                    insert_index = len(row_cards)
                                    
                                    # Find drop position relative to existing cards
                                    if row_cards:
                                        mouse_x = event.pos[0]
                                        for i, card in enumerate(row_cards):
                                            if hasattr(card, 'rect'):
                                                # If dropping to the left of a card's center, insert before it
                                                if mouse_x < card.rect.centerx:
                                                    insert_index = i
                                                    break
                                    
                                    # --- NEW: Check card for specific animations ---
                                    if "Naquadah Overload" in (dragging_card.ability or ""):
                                        # Naquadah Overload: Play card first, then show explosions on affected rows
                                        game.play_card(dragging_card, row_name, index=insert_index)
                                        
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
                                                    duration=1500
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

                                    # Special card unique visuals
                                    if dragging_card.row == "special":
                                        add_special_card_effect(
                                            dragging_card,
                                            effect_x,
                                            effect_y,
                                            anim_manager,
                                            SCREEN_WIDTH,
                                            SCREEN_HEIGHT
                                        )
                                    
                                    # Add ship to space battle if siege card is PLAYED
                                    if dragging_card.row == "siege":
                                        ambient_effects.add_ship(game.player1.faction, dragging_card.name, is_player=True)
                                    
                                    # Check if this is a medic card
                                    if "Medical Evac" in (dragging_card.ability or ""):
                                        valid_medic_cards = game.get_medic_valid_cards(game.player1)
                                        if valid_medic_cards:
                                            # Enter medic selection mode
                                            ui_state = UIState.MEDIC_SELECT
                                            medic_card_played = dragging_card
                                            game.play_card(dragging_card, row_name, index=insert_index)
                                        else:
                                            # No cards to revive, play normally
                                            game.play_card(dragging_card, row_name, index=insert_index)
                                    else:
                                        game.play_card(dragging_card, row_name, index=insert_index)
                                    
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
            # Jonas Quinn: See cards drawn by opponent (auto-trigger when opponent draws)
            if game.player1.leader and "Jonas" in game.player1.leader.get('name', ''):
                # Show overlay if opponent has drawn cards (not starting hand)
                if game.opponent_drawn_cards:
                    ui_state = UIState.JONAS_PEEK
            
            # Vala: Look at 3 cards, keep 1 (once per round, manual trigger with V key)
            # Ba'al Clone: Clone highest unit (once per round, manual trigger with B key)
            # Thor: Move unit (once per round, manual trigger with T key)
        
        # Simple AI for Player 2 - WITH SMOOTH ANIMATIONS
        # Skip AI animations in LAN mode - opponent is a real human
        if game.current_player == game.player2 and game.game_state == "playing" and not LAN_MODE:
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

                # Check if faction power was available before AI decision
                ai_power_available_before = (game.player2.faction_power and
                                             game.player2.faction_power.is_available())

                # Get AI decision without executing it yet
                card_to_play, row_to_play = ai_controller.choose_move()

                # Check if AI used faction power
                ai_power_available_after = (game.player2.faction_power and
                                            game.player2.faction_power.is_available())
                ai_used_faction_power = ai_power_available_before and not ai_power_available_after

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

                    # Check if AI used faction power - trigger animation!
                    if ai_used_faction_power:
                        # Create faction power effect animation
                        faction_power_effect = FactionPowerEffect(
                            game.player2.faction,
                            SCREEN_WIDTH // 2,
                            SCREEN_HEIGHT // 2,
                            SCREEN_WIDTH,
                            SCREEN_HEIGHT
                        )
                        anim_manager.add_effect(faction_power_effect)

                        # Add history event for AI faction power use
                        game.add_history_event(
                            "faction_power",
                            f"{game.player2.name} used {game.player2.faction_power.name}",
                            "ai"
                        )

                        # Add Iris closing animation for Tau'ri Gate Shutdown
                        if game.player2.faction == FACTION_TAURI:
                            from animations import IrisClosingEffect
                            iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                            anim_manager.add_effect(iris_anim)

                    # AI passes or uses power
                    ai_turn_anim.finish()
                    game.last_turn_actor = game.player2
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

                    weather_visual_applied = False
                    if ai_card_to_play.row == "weather":
                        weather_visual_applied = True
                        ability_lower = ability.lower()
                        if "wormhole stabilization" in ability_lower:
                            anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                        else:
                            anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=500))
                            if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                                for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                                    row_rect = rects.get(ai_row_to_play)
                                    if row_rect:
                                        anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))

                    # Check for Naquadah Overload
                    if not weather_visual_applied and "Naquadah Overload" in ability:
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
                                    duration=1500
                                ))
                        game.last_scorch_positions = []
                    elif not weather_visual_applied and "Legendary Commander" in ability:
                        hero_anim = create_hero_animation(ai_card_to_play.name, effect_x, effect_y)
                        anim_manager.add_effect(hero_anim)
                        anim_manager.add_effect(LegendaryLightningEffect(ai_card_to_play))
                    elif not weather_visual_applied:
                        # Check for special ability animations (same as player)
                        ability_triggered = False
                        for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones",
                                               "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement"]:
                            if special_ability in ability:
                                ability_anim = create_ability_animation(ability, effect_x, effect_y)
                                anim_manager.add_effect(ability_anim)
                                ability_triggered = True
                                break

                        # Default stargate effect if no special ability
                        if not ability_triggered:
                            stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=500)
                            anim_manager.add_effect(stargate_effect)

                        # Special card unique visuals
                        if ai_card_to_play.row == "special":
                            add_special_card_effect(
                                ai_card_to_play,
                                effect_x,
                                effect_y,
                                anim_manager,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT
                            )
                
                ai_turn_anim.start_resolving()
            
            elif ai_result == "resolving_done":
                # Recalculate scores
                game.player1.calculate_score()
                game.player2.calculate_score()

                # Check if AI should use Iris Defense (before switching turn)
                if (hasattr(ai_controller, 'strategy') and
                    ai_controller.strategy.should_use_iris_defense()):
                    # AI activates Iris Defense
                    game.player2.iris_defense.activate()
                    # Trigger Iris closing animation
                    from animations import IrisClosingEffect
                    iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    anim_manager.add_effect(iris_anim)
                    # Add history event
                    game.add_history_event(
                        "special",
                        f"{game.player2.name} activated Iris Defense!",
                        "ai",
                        icon="[#]"
                    )

                # Finish turn
                ai_turn_anim.finish()
                game.switch_turn()
                ai_turn_in_progress = False
                ai_selected_card_index = None

        # LAN opponent turn handling
        elif game.current_player == game.player2 and game.game_state == "playing" and LAN_MODE:
            # Check if faction power was available before polling
            lan_power_available_before = (game.player2.faction_power and
                                          game.player2.faction_power.is_available())

            # Poll for network message from opponent
            card_to_play, row_to_play = ai_controller.choose_move()

            # Check if opponent used faction power
            lan_power_available_after = (game.player2.faction_power and
                                         game.player2.faction_power.is_available())
            if lan_power_available_before and not lan_power_available_after:
                # Opponent used faction power - trigger animation!
                faction_power_effect = FactionPowerEffect(
                    game.player2.faction,
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 2,
                    SCREEN_WIDTH,
                    SCREEN_HEIGHT
                )
                anim_manager.add_effect(faction_power_effect)

                # Add Iris closing animation for Tau'ri Gate Shutdown
                if game.player2.faction == FACTION_TAURI:
                    from animations import IrisClosingEffect
                    iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    anim_manager.add_effect(iris_anim)

            if card_to_play and row_to_play:
                # Opponent played a card - process it with animations
                ability = card_to_play.ability or ""

                # Play the card
                game.play_card(card_to_play, row_to_play)

                # Check if opponent played a siege card for space battle
                if row_to_play == 'siege':
                    ambient_effects.add_ship(game.player2.faction, card_to_play.name, is_player=False)

                # Trigger visual effect for the play
                target_rect = OPPONENT_ROW_RECTS.get(row_to_play)
                if "Deep Cover Agent" in ability or card_to_play.row == "weather":
                    target_rect = PLAYER_ROW_RECTS.get(row_to_play) or target_rect
                effect_x = target_rect.centerx if target_rect else SCREEN_WIDTH // 2
                effect_y = target_rect.centery if target_rect else SCREEN_HEIGHT // 4
                if card_to_play.row == "special":
                    add_special_card_effect(
                        card_to_play,
                        effect_x,
                        effect_y,
                        anim_manager,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT
                    )

                weather_visual_applied = False
                if card_to_play.row == "weather":
                    weather_visual_applied = True
                    ability_lower = ability.lower()
                    if "wormhole stabilization" in ability_lower:
                        anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                    else:
                        anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=500))
                        if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                            for rects in (PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS):
                                row_rect = rects.get(row_to_play)
                                if row_rect:
                                    anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))

                # Check for Naquadah Overload
                if not weather_visual_applied and "Naquadah Overload" in ability:
                    for player, destroyed_row in game.last_scorch_positions:
                        if player == game.player1:
                            row_rect = PLAYER_ROW_RECTS.get(destroyed_row)
                        else:
                            row_rect = OPPONENT_ROW_RECTS.get(destroyed_row)
                        if row_rect:
                            anim_manager.add_effect(NaquadahExplosionEffect(
                                SCREEN_WIDTH // 2,
                                row_rect.centery,
                                duration=1500
                            ))
                    game.last_scorch_positions = []
                elif not weather_visual_applied and "Legendary Commander" in ability:
                    hero_anim = create_hero_animation(card_to_play.name, effect_x, effect_y)
                    anim_manager.add_effect(hero_anim)
                    anim_manager.add_effect(LegendaryLightningEffect(card_to_play))
                elif not weather_visual_applied:
                    # Check for special ability animations (same as player)
                    ability_triggered = False
                    for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones",
                                           "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement"]:
                        if special_ability in ability:
                            ability_anim = create_ability_animation(ability, effect_x, effect_y)
                            anim_manager.add_effect(ability_anim)
                            ability_triggered = True
                            break

                    # Default stargate effect if no special ability
                    if not ability_triggered:
                        stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=500)
                        anim_manager.add_effect(stargate_effect)

                # Recalculate scores
                game.player1.calculate_score()
                game.player2.calculate_score()

            # Note: If (None, None) returned, either opponent passed/used power (already handled),
            # or no message yet (keep polling next frame)

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
                slot_hover = False
                for row_name, slot_rect in WEATHER_SLOT_RECTS.items():
                    slot_color = get_row_color(row_name)
                    drag_row_highlights.append({"rect": slot_rect, "color": slot_color, "alpha": 55})
                    if slot_rect.collidepoint(mouse_pos):
                        drag_hover_highlight = {"rect": slot_rect, "color": slot_color, "alpha": 150}
                        slot_hover = True
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
                if not slot_hover and hovered_rect:
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
        
        separator_color = (100, 150, 200, 150)
        separator_width = 3
        glow_color = (150, 200, 255, 80)
        x_start = PLAYFIELD_LEFT
        x_end = PLAYFIELD_LEFT + PLAYFIELD_WIDTH

        for row_rect in list(OPPONENT_ROW_RECTS.values()) + list(PLAYER_ROW_RECTS.values()):
            y_pos = row_rect.bottom
            if row_rect in OPPONENT_ROW_RECTS.values():
                y_pos += 8

            pygame.draw.line(screen, glow_color, (x_start, y_pos - 2), (x_end, y_pos - 2), 1)
            pygame.draw.line(screen, glow_color, (x_start, y_pos - 1), (x_end, y_pos - 1), 1)
            pygame.draw.line(screen, separator_color, (x_start, y_pos), (x_end, y_pos), separator_width)
            pygame.draw.line(screen, glow_color, (x_start, y_pos + separator_width), (x_end, y_pos + separator_width), 1)
            pygame.draw.line(screen, glow_color, (x_start, y_pos + separator_width + 1), (x_end, y_pos + separator_width + 1), 1)
        
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
            history_panel_rect = None
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

                    # Record draft mode completion if this was a draft game
                    if is_draft_mode:
                        persistence = get_persistence()
                        leader_name = player_leader.get('name', 'Unknown')
                        leader_id = player_leader.get('card_id', '')
                        deck_power = sum(card.power for card in player_deck)
                        persistence.record_draft_completion(
                            leader_id=leader_id,
                            leader_name=leader_name,
                            faction=player_faction,
                            cards=player_deck,
                            deck_power=deck_power,
                            won=player_won
                        )

                    mode_label = "lan" if LAN_MODE else "ai"
                    if player_won:
                        record_victory(player_faction, mode_label)

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
                        record_defeat(player_faction, mode_label)
                        unlock_system.record_game_result(False)

                    # Record rich stats summary once per game
                    try:
                        leader_name = (game.player1.leader or {}).get('name', 'Unknown') if isinstance(game.player1.leader, dict) else str(game.player1.leader)
                        opponent_leader = (game.player2.leader or {}).get('name', 'Unknown') if isinstance(game.player2.leader, dict) else str(game.player2.leader)
                        summary = {
                            "won": player_won,
                            "player_faction": player_faction,
                            "opponent_faction": game.player2.faction,
                            "leader": leader_name,
                            "opponent_leader": opponent_leader,
                            "turns": getattr(game, "turn_count", 0),
                            "mulligans": getattr(game, "player_mulligan_count", 0),
                            "abilities": getattr(game, "ability_usage", {}),
                            "cards_played": getattr(game, "cards_played_ids", []),
                            "mode": mode_label,
                            "lan_completed": LAN_MODE,
                            "lan_disconnect": False,
                            "ai_difficulty": "hard" if not LAN_MODE else None,
                        }
                        get_persistence().record_game_summary(summary)
                    except Exception as exc:
                        print(f"[stats] Unable to record summary: {exc}")
            
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
            history_panel_rect = None
        else:
            draw_board(screen, game, selected_card, dragging_card=dragging_card,
                       drag_hover_highlight=drag_hover_highlight, drag_row_highlights=drag_row_highlights)
            draw_scores(screen, game, anim_manager, render_static=False)

            # Auto-start Hathor steal animation (LAN/AI) if pending and not started yet
            steal_info = getattr(game, "hathor_steal_info", None)
            if steal_info and not steal_info.get("animation_started"):
                card = steal_info.get("card")
                target_row = steal_info.get("target_row", "close")
                if card and hasattr(card, "rect"):
                    start_pos = (card.rect.centerx, card.rect.centery)
                    target_rect = PLAYER_ROW_RECTS.get(target_row) or OPPONENT_ROW_RECTS.get(target_row)
                    end_pos = (target_rect.centerx, target_rect.centery) if target_rect else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    h_anim = HathorStealAnimation(
                        card,
                        start_pos,
                        end_pos,
                        on_finish=lambda: game.switch_turn()
                    )
                    anim_manager.add_animation(h_anim)
                    steal_info["animation_started"] = True

            history_rect = pygame.Rect(
                HUD_LEFT + int(HUD_WIDTH * 0.42),
                pct_y(0.12),
                max(50, int(HUD_WIDTH * 0.55)),
                pct_y(0.80) - pct_y(0.12)
            )
            history_panel_rect = history_rect

            # Always show game history in the HUD panel
            history_entry_hitboxes, history_scroll_limit = draw_history_panel(
                screen,
                game,
                history_rect,
                history_scroll_offset,
                pygame.mouse.get_pos()
            )
            
            # LAN Chat Input (Integrated)
            if lan_chat_panel:
                if lan_chat_panel.active:
                    # Draw input box below history panel
                    input_height = 40
                    input_rect = pygame.Rect(
                        history_rect.x, 
                        history_rect.bottom + 5, 
                        history_rect.width, 
                        input_height
                    )
                    
                    # Draw background
                    pygame.draw.rect(screen, (30, 35, 60), input_rect, border_radius=5)
                    pygame.draw.rect(screen, (100, 200, 255), input_rect, 2, border_radius=5)
                    
                    # Draw text
                    font_input = pygame.font.SysFont("Consolas", 18)
                    input_text = lan_chat_panel.input_text
                    
                    # Cursor blink
                    if (pygame.time.get_ticks() // 500) % 2 == 0:
                        input_text += "|"
                        
                    surf = font_input.render(input_text, True, (255, 255, 255))
                    
                    # Clip if too long
                    area_rect = pygame.Rect(input_rect.x + 5, input_rect.y + 10, input_rect.width - 10, input_rect.height - 20)
                    screen.set_clip(area_rect)
                    screen.blit(surf, (input_rect.x + 5, input_rect.y + 10))
                    screen.set_clip(None)
                    
                    # Typing indicator if peer is typing
                    if lan_chat_panel.peer_is_typing:
                        # Draw indicator slightly above input (overlapping bottom of history)
                        lan_chat_panel._draw_typing_indicator(screen, input_rect)

                else:
                    # Draw small hint
                    hint_font = pygame.font.SysFont("Arial", 14)
                    hint_text = hint_font.render("Press T or Enter to Chat", True, (150, 200, 255))
                    screen.blit(hint_text, (history_rect.x, history_rect.bottom + 5))
                    
                    # Show typing indicator even if closed (as a notification)
                    if lan_chat_panel.peer_is_typing:
                        typing_rect = pygame.Rect(history_rect.x, history_rect.bottom + 25, history_rect.width, 40)
                        lan_chat_panel._draw_typing_indicator(screen, typing_rect)

            history_scroll_offset = max(0, min(history_scroll_offset, history_scroll_limit))
            if history_manual_scroll and history_scroll_offset <= 0:
                history_manual_scroll = False

            draw_row_score_boxes(screen, game)

            round_font = pygame.font.SysFont("Arial", max(28, int(30 * SCALE_FACTOR)), bold=True)
            round_text = round_font.render(f"Round {game.round_number}", True, WHITE)
            screen.blit(round_text, (HUD_LEFT + int(HUD_WIDTH * 0.1), pct_y(0.05)))
            turn_color = (120, 255, 160) if game.current_player == game.player1 else (255, 140, 140)
            turn_text = UI_FONT.render("YOUR TURN" if game.current_player == game.player1 else "ENEMY TURN", True, turn_color)
            screen.blit(turn_text, (HUD_LEFT + int(HUD_WIDTH * 0.1), pct_y(0.05) + round_text.get_height() + 6))

            command_bar_surface = pygame.Surface((SCREEN_WIDTH, COMMAND_BAR_HEIGHT), pygame.SRCALPHA)
            command_bar_surface.fill((10, 20, 35, 200))
            pygame.draw.line(command_bar_surface, (80, 120, 180), (0, 0), (SCREEN_WIDTH, 0), 2)
            screen.blit(command_bar_surface, (0, COMMAND_BAR_Y))

            draw_pass_button(screen, game, HUD_PASS_BUTTON_RECT)

            draw_hand(
                screen,
                game.player1,
                selected_card,
                dragging_card=dragging_card,
                hovered_card=hovered_card,
                hover_scale=card_hover_scale,
                drag_visuals=drag_visual_state
            )
            draw_opponent_hand(screen, game.player2)

            mouse_pos = pygame.mouse.get_pos()
            ai_area = LEADER_TOP_RECT.copy()
            player_area = LEADER_BOTTOM_RECT.copy()
            ai_stack = draw_leader_column(
                screen,
                game.player2,
                ai_area,
                ability_ready=ai_ability_ready,
                faction_power_ready=bool(game.player2.faction_power and game.player2.faction_power.is_available()),
                hover_pos=mouse_pos
            )
            player_stack = draw_leader_column(
                screen,
                game.player1,
                player_area,
                ability_ready=player_ability_ready,
                faction_power_ready=bool(game.player1.faction_power and game.player1.faction_power.is_available()),
                hover_pos=mouse_pos
            )

            ai_leader_rect = ai_stack["leader_rect"]
            ai_ability_rect = ai_stack["ability_rect"]
            ai_faction_button_rect = ai_stack["faction_rect"]
            ai_special_button_rect = ai_stack.get("special_rect")
            ai_special_button_kind = ai_stack.get("special_kind")
            player_leader_rect = player_stack["leader_rect"]
            player_ability_rect = player_stack["ability_rect"]
            player_faction_button_rect = player_stack["faction_rect"]
            player_special_button_rect = player_stack.get("special_rect")
            player_special_button_kind = player_stack.get("special_kind")
            discard_rect = player_stack.get("discard_rect") or discard_rect

            iris_button_rect = player_special_button_rect if player_special_button_kind == "iris" else None
            ring_transport_button_rect = player_special_button_rect if player_special_button_kind == "rings" else None

            if ai_turn_in_progress:
                total_cards = len(game.player2.hand)
                if total_cards > 0:
                    card_spacing = int(CARD_WIDTH * 0.125)
                    positions, _ = _compute_hand_positions(total_cards, CARD_WIDTH, card_spacing)
                    left_edge = positions[0]
                    right_edge = positions[-1] + CARD_WIDTH
                    opponent_hand_area = pygame.Rect(left_edge, opponent_hand_area_y,
                                                     right_edge - left_edge, CARD_HEIGHT)
                    ai_turn_anim.draw(screen, UI_FONT, opponent_hand_area)
        
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
        if ui_state == UIState.MEDIC_SELECT:
            medic_valid_cards = game.get_medic_valid_cards(game.player1)
            if not medic_valid_cards:
                # No valid targets (discard pile empty) — exit selection and end turn cleanly
                ui_state = UIState.PLAYING
                medic_card_played = None
                game.add_history_event(
                    "ability",
                    f"{game.player1.name}'s medic had no targets to revive",
                    "player",
                    icon="+"
                )
                game.player1.calculate_score()
                game.player2.calculate_score()
                game.last_turn_actor = game.player1
                game.switch_turn()
            else:
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
                            game.last_turn_actor = game.player1
                            game.switch_turn()
                            if network_proxy:
                                network_proxy.send_medic_choice(card.id)
                            ui_state = UIState.PLAYING
                            medic_card_played = None
                            pygame.time.wait(200)  # Small delay to prevent double-click
                            break
        
        # Ring Transport selection overlay
        decoy_card_rects = []
        if ui_state == UIState.DECOY_SELECT:
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
                            game.last_turn_actor = game.player1
                            game.switch_turn()
                            if network_proxy:
                                network_proxy.send_decoy_choice(card.id)
                            ui_state = UIState.PLAYING
                            decoy_card_played = None
                            pygame.time.wait(200)  # Small delay to prevent double-click
                        break
        
        # Jonas Quinn peek overlay
        if ui_state == UIState.JONAS_PEEK:
            draw_jonas_peek_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)

            # Handle click to close
            if pygame.mouse.get_pressed()[0]:
                ui_state = UIState.PLAYING
                # Clear the tracked cards after viewing
                game.opponent_drawn_cards = []
                pygame.time.wait(200)
        
        # Ba'al Clone selection overlay
        baal_card_rects = []
        if ui_state == UIState.BAAL_CLONE_SELECT:
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
                        ui_state = UIState.PLAYING
                        pygame.time.wait(200)
                        break
        
        # Vala selection overlay
        vala_card_rects = []
        if ui_state == UIState.VALA_SELECT:
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
                        game.rng.shuffle(game.player1.deck)
                        ui_state = UIState.PLAYING
                        vala_cards_to_choose = []
                        pygame.time.wait(200)
                        break

        # Catherine Langford selection overlay
        catherine_card_rects = []
        if ui_state == UIState.CATHERINE_SELECT:
            catherine_card_rects = draw_catherine_selection_overlay(screen, catherine_cards_to_choose, SCREEN_WIDTH, SCREEN_HEIGHT)
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in catherine_card_rects:
                    if rect.collidepoint(mouse_pos):
                        revealed_ids = [c.id for c in catherine_cards_to_choose]
                        game.catherine_play_chosen_card(game.player1, card)
                        if network_proxy:
                            network_proxy.send_leader_ability(
                                "Ancient Knowledge",
                                {"choice_id": card.id, "revealed_ids": revealed_ids}
                            )
                        ui_state = UIState.PLAYING
                        catherine_cards_to_choose = []
                        pygame.time.wait(200)
                        break

        # Generic leader choice overlay (Jonas Quinn, Ba'al, etc.)
        leader_choice_rects = []
        if pending_leader_choice:
            # Sync state if needed
            if ui_state != UIState.LEADER_CHOICE_SELECT:
                ui_state = UIState.LEADER_CHOICE_SELECT
                
            leader_choice_rects = draw_leader_choice_overlay(screen, pending_leader_choice, SCREEN_WIDTH, SCREEN_HEIGHT)
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in leader_choice_rects:
                    if rect.collidepoint(mouse_pos):
                        ability_name = pending_leader_choice.get("ability", "")
                        if ability_name == "Eidetic Memory":
                            game.jonas_memorize_card(game.player1, card)
                            if network_proxy:
                                network_proxy.send_leader_ability(
                                    "Eidetic Memory",
                                    {"card_id": card.id}
                                )
                        elif ability_name == "System Lord's Cunning":
                            game.baal_resurrect_card(game.player1, card)
                            if network_proxy:
                                network_proxy.send_leader_ability(
                                    "System Lord's Cunning",
                                    {"choice_id": card.id}
                                )
                        pending_leader_choice = None
                        ui_state = UIState.PLAYING
                        pygame.time.wait(200)
                        break

        # Thor move mode - simple visual indicator
        if ui_state == UIState.THOR_MOVE_SELECT:
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
                                    ui_state = UIState.PLAYING
                                    thor_selected_unit = None
                                    pygame.time.wait(200)
                                    break
                            break
        
        # Discard pile viewer overlay
        if ui_state == UIState.DISCARD_VIEW:
            draw_discard_viewer(screen, game.player1.discard_pile, SCREEN_WIDTH, SCREEN_HEIGHT, discard_scroll)

        # Context popup for leader column buttons
        if button_info_popup and ui_state != UIState.PAUSED and not inspected_card and not inspected_leader:
            expires_at = button_info_popup.get("expires_at")
            if expires_at and pygame.time.get_ticks() > expires_at:
                button_info_popup = None
            else:
                draw_button_info_popup(screen, button_info_popup)
        
        # Pause menu overlay
        if ui_state == UIState.PAUSED:
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
                    ui_state = UIState.PLAYING
                elif main_menu_button.collidepoint(mouse_pos):
                    # Return to main menu
                    stop_battle_music()
                    main()
                    return
                elif quit_button.collidepoint(mouse_pos):
                    stop_battle_music()
                    pygame.quit()
                    sys.exit()

        pygame.display.flip()

    stop_battle_music()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
