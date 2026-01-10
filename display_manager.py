import pygame
import sys
import os
import ctypes
import tempfile
from cards import reload_card_images

# Initialize Pygame
pygame.init()

# Set high DPI awareness for Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Windows 8.1+
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Windows Vista+
    except:
        pass  # Not Windows or already set

# Global display state
screen = None
FULLSCREEN = False
SCREEN_WIDTH = 0
SCREEN_HEIGHT = 0
SCALE_FACTOR = 1.0
DESKTOP_WIDTH = 0
DESKTOP_HEIGHT = 0
TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160
WINDOWED_WIDTH = 0
WINDOWED_HEIGHT = 0
WINDOWED_SCALE_FACTOR = 1.0
WINDOWED_FLAGS = 0

def initialize_display():
    """Detects resolution and sets up the initial display state."""
    global SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_FACTOR, FULLSCREEN, screen
    global DESKTOP_WIDTH, DESKTOP_HEIGHT, WINDOWED_WIDTH, WINDOWED_HEIGHT
    global WINDOWED_SCALE_FACTOR, WINDOWED_FLAGS

    _desktop_cache_file = os.path.join(tempfile.gettempdir(), 'stargwent_desktop_cache.txt')

    # 1. Detect Desktop Resolution
    try:
        if os.path.exists(_desktop_cache_file):
            with open(_desktop_cache_file, 'r') as f:
                cached = f.read().strip().split('x')
                ORIGINAL_DESKTOP_WIDTH = int(cached[0])
                ORIGINAL_DESKTOP_HEIGHT = int(cached[1])
            print(f"🖥️  Using Cached Desktop Resolution: {ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")
        else:
            display_info = pygame.display.Info()
            ORIGINAL_DESKTOP_WIDTH = display_info.current_w
            ORIGINAL_DESKTOP_HEIGHT = display_info.current_h
            with open(_desktop_cache_file, 'w') as f:
                f.write(f"{ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")
            print(f"🖥️  Detected Original Desktop Resolution: {ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")
    except Exception as e:
        display_info = pygame.display.Info()
        ORIGINAL_DESKTOP_WIDTH = display_info.current_w
        ORIGINAL_DESKTOP_HEIGHT = display_info.current_h
        print(f"🖥️  Desktop Resolution (no cache): {ORIGINAL_DESKTOP_WIDTH}x{ORIGINAL_DESKTOP_HEIGHT}")

    DESKTOP_WIDTH = ORIGINAL_DESKTOP_WIDTH
    DESKTOP_HEIGHT = ORIGINAL_DESKTOP_HEIGHT

    # 2. Calculate Scaling
    SCALE_X = (DESKTOP_WIDTH * 0.95) / TARGET_WIDTH
    SCALE_Y = (DESKTOP_HEIGHT * 0.95) / TARGET_HEIGHT
    SCALE_FACTOR = min(SCALE_X, SCALE_Y, 1.0)

    # 3. Final Screen Size
    SCREEN_WIDTH = int(TARGET_WIDTH * SCALE_FACTOR)
    SCREEN_HEIGHT = int(TARGET_HEIGHT * SCALE_FACTOR)

    WINDOWED_WIDTH = SCREEN_WIDTH
    WINDOWED_HEIGHT = SCREEN_HEIGHT
    WINDOWED_SCALE_FACTOR = SCALE_FACTOR
    WINDOWED_FLAGS = pygame.SHOWN | pygame.SCALED if SCALE_FACTOR < 1.0 else pygame.SHOWN

    # 4. Check for Fullscreen Flag
    DEFAULT_FULLSCREEN = (
        "--fullscreen" in sys.argv or
        os.environ.get("STARGWENT_FULLSCREEN", "").lower() in {"1", "true", "yes"}
    )
    FULLSCREEN = DEFAULT_FULLSCREEN

    # 5. Set Mode
    set_display_mode(FULLSCREEN, reload_cards=False)
    
    # 6. Set Icon
    try:
        icon = pygame.image.load("assets/tauri_oneill.png")
        pygame.display.set_icon(icon)
        print("✓ Custom window icon set.")
    except pygame.error as e:
        print(f"⚠ Warning: Could not load window icon. {e}")

    # 7. Reload cards (happens in main usually, but good to do here if we own display)
    print("Loading card images...")
    reload_card_images()
    print("Card images loaded.")

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
