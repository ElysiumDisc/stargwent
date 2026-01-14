import pygame
import sys
import os
import ctypes
import tempfile
from cards import reload_card_images

# Initialize Pygame
pygame.init()

# Enable keyboard repeat (delay_ms, interval_ms) for continuous navigation when holding keys
pygame.key.set_repeat(300, 50)

# Set high DPI awareness for Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Windows 8.1+
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Windows Vista+
    except:
        pass  # Not Windows or already set

screen = None
FULLSCREEN = False
SCREEN_WIDTH = 0
SCREEN_HEIGHT = 0
SCALE_FACTOR = 1.0
DESKTOP_WIDTH = 0
DESKTOP_HEIGHT = 0
TARGET_WIDTH = 2560
TARGET_HEIGHT = 1440
WINDOWED_WIDTH = 0
WINDOWED_HEIGHT = 0
WINDOWED_SCALE_FACTOR = 1.0
WINDOWED_FLAGS = 0
_initialized = False  # Guard to prevent re-initialization

def initialize_display():
    """Detects resolution and sets up the initial display state.

    NOTE: Only initializes once. Subsequent calls are skipped to preserve
    fullscreen state across game state transitions.
    """
    global SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_FACTOR, FULLSCREEN, screen
    global DESKTOP_WIDTH, DESKTOP_HEIGHT, WINDOWED_WIDTH, WINDOWED_HEIGHT
    global WINDOWED_SCALE_FACTOR, WINDOWED_FLAGS, _initialized

    # GUARD: Only initialize once
    if _initialized:
        return
    _initialized = True

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

    # 2. Hardware Scaling Setup
    # 1440p provides crisp detail while keeping blitting fast for 4K output
    SCREEN_WIDTH = TARGET_WIDTH
    SCREEN_HEIGHT = TARGET_HEIGHT
    SCALE_FACTOR = SCREEN_HEIGHT / 1080.0

    WINDOWED_WIDTH = SCREEN_WIDTH
    WINDOWED_HEIGHT = SCREEN_HEIGHT
    WINDOWED_SCALE_FACTOR = SCALE_FACTOR
    # Use SCALED flag for hardware upscaling
    WINDOWED_FLAGS = pygame.SHOWN | pygame.SCALED

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
    """Hardware-accelerated scaling using 1440p internal resolution."""
    global screen, SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_FACTOR, FULLSCREEN
    FULLSCREEN = fullscreen_enabled
    
    SCREEN_WIDTH = TARGET_WIDTH
    SCREEN_HEIGHT = TARGET_HEIGHT
    
    if fullscreen_enabled:
        # Use SCALED + FULLSCREEN for hardware-accelerated 4K output
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        pygame.display.set_caption("Stargwent - 4K (Hardware Scaled)")
    else:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED)
        pygame.display.set_caption("Stargwent - 1440p (Windowed)")
    
    # Adjust SCALE_FACTOR for our 1440p base
    SCALE_FACTOR = SCREEN_HEIGHT / 1080.0
    
    # Update layout dimensions for new resolution
    import game_config
    game_config.recalculate_dimensions()

    # Clear render caches on resolution change
    try:
        import render_engine
        render_engine.clear_render_caches()
    except ImportError:
        pass  # render_engine not yet imported

    try:
        import board_renderer
        board_renderer.clear_surface_cache()
    except ImportError:
        pass  # board_renderer not yet imported

    if reload_cards:
        reload_card_images()

def sync_fullscreen_from_surface():
    """Ensure FULLSCREEN flag matches current SDL state (handles menu toggles)."""
    surface = pygame.display.get_surface()
    if not surface:
        return
    is_fullscreen = bool(surface.get_flags() & pygame.FULLSCREEN)
    if is_fullscreen != FULLSCREEN:
        print(f"⚠️  Display state mismatch! SDL says fullscreen={is_fullscreen}, but FULLSCREEN={FULLSCREEN}")
        print(f"    Surface flags: {surface.get_flags()}, pygame.FULLSCREEN={pygame.FULLSCREEN}")
        print(f"    Syncing to SDL state...")
        set_display_mode(is_fullscreen, reload_cards=True)

def toggle_fullscreen_mode():
    """Flip fullscreen state respecting all UI/layout updates."""
    new_state = not FULLSCREEN
    print(f"🔄 Toggling fullscreen: {FULLSCREEN} → {new_state}")
    set_display_mode(new_state, reload_cards=True)

    # Verify the change took effect
    surface = pygame.display.get_surface()
    if surface:
        actual_fullscreen = bool(surface.get_flags() & pygame.FULLSCREEN)
        print(f"✓ Fullscreen toggle complete. Requested={new_state}, Actual SDL state={actual_fullscreen}")
