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
VSYNC_ENABLED = True  # VSync enabled by default for tear-free rendering
COMPETITIVE_MODE = False  # Uses tick_busy_loop for precise timing in LAN games
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
    global VSYNC_ENABLED, COMPETITIVE_MODE

    # GUARD: Only initialize once
    if _initialized:
        return
    _initialized = True

    # Load vsync and competitive mode settings
    try:
        from game_settings import get_settings
        settings = get_settings()
        VSYNC_ENABLED = settings.get_vsync_enabled()
        COMPETITIVE_MODE = settings.get_competitive_mode()
    except (ImportError, AttributeError):
        VSYNC_ENABLED = True
        COMPETITIVE_MODE = False

    # Check smoothscale SIMD acceleration backend
    try:
        backend = pygame.transform.get_smoothscale_backend()
        print(f"Smoothscale SIMD backend: {backend}")
    except AttributeError:
        print("Smoothscale backend check not available")

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

    # 2. Adaptive Resolution - render at desktop resolution if smaller than 1440p
    if DESKTOP_WIDTH < TARGET_WIDTH or DESKTOP_HEIGHT < TARGET_HEIGHT:
        # Desktop smaller than 1440p - render at native desktop resolution
        SCREEN_WIDTH = DESKTOP_WIDTH
        SCREEN_HEIGHT = DESKTOP_HEIGHT
        print(f"📐 Rendering at native resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    else:
        # Desktop 1440p or larger - render at 1440p, let hardware scale up
        SCREEN_WIDTH = TARGET_WIDTH
        SCREEN_HEIGHT = TARGET_HEIGHT
        print(f"📐 Rendering at 1440p: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    SCALE_FACTOR = SCREEN_HEIGHT / 1080.0
    print(f"   → Scale Factor: {SCALE_FACTOR:.3f}x")

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

def set_display_mode(fullscreen_enabled, *, reload_cards=False, vsync=None):
    """Hardware-accelerated scaling using 1440p internal resolution.

    Args:
        fullscreen_enabled: Whether to use fullscreen mode
        reload_cards: Whether to reload card images after mode change
        vsync: Override vsync setting (None uses global VSYNC_ENABLED)
    """
    global screen, SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_FACTOR, FULLSCREEN, VSYNC_ENABLED
    FULLSCREEN = fullscreen_enabled

    # Use global vsync setting if not overridden
    use_vsync = VSYNC_ENABLED if vsync is None else vsync
    vsync_value = 1 if use_vsync else 0

    # Don't override SCREEN_WIDTH/HEIGHT - they're already set by initialize_display()
    # with adaptive resolution logic (native res if < 1440p, else 1440p)

    if fullscreen_enabled:
        # Use SCALED + FULLSCREEN for hardware-accelerated 4K output with optional vsync
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.FULLSCREEN | pygame.SCALED,
            vsync=vsync_value
        )
        vsync_status = "VSync ON" if use_vsync else "VSync OFF"
        pygame.display.set_caption(f"Stargwent - 4K ({vsync_status})")
    else:
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.SCALED,
            vsync=vsync_value
        )
        vsync_status = "VSync ON" if use_vsync else "VSync OFF"
        pygame.display.set_caption(f"Stargwent - Windowed ({vsync_status})")
    
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
    print(f"Toggling fullscreen: {FULLSCREEN} -> {new_state}")
    set_display_mode(new_state, reload_cards=True)

    # Verify the change took effect
    surface = pygame.display.get_surface()
    if surface:
        actual_fullscreen = bool(surface.get_flags() & pygame.FULLSCREEN)
        print(f"Fullscreen toggle complete. Requested={new_state}, Actual SDL state={actual_fullscreen}")


def set_vsync_enabled(enabled):
    """Enable or disable VSync. Requires display mode reset to take effect."""
    global VSYNC_ENABLED
    VSYNC_ENABLED = enabled
    print(f"VSync {'enabled' if enabled else 'disabled'}")
    # Apply immediately by resetting display mode
    set_display_mode(FULLSCREEN, reload_cards=False, vsync=enabled)


def set_competitive_mode(enabled):
    """Enable competitive mode for precise timing in LAN games."""
    global COMPETITIVE_MODE
    COMPETITIVE_MODE = enabled
    print(f"Competitive mode {'enabled' if enabled else 'disabled'} (uses tick_busy_loop)")


def get_clock_tick_func():
    """Get the appropriate clock tick function based on competitive mode.

    Returns a function that takes fps as argument:
    - competitive mode: clock.tick_busy_loop (precise, more CPU)
    - normal mode: clock.tick (efficient, uses SDL_Delay)
    """
    if COMPETITIVE_MODE:
        return lambda clock, fps: clock.tick_busy_loop(fps)
    else:
        return lambda clock, fps: clock.tick(fps)
