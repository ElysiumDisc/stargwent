import pygame
import sys
import os
from cards import reload_card_images

# ctypes and tempfile may not be available on Emscripten/WASM
if sys.platform != "emscripten":
    import ctypes
    import tempfile

# Initialize Pygame
pygame.init()

# Enable keyboard repeat (delay_ms, interval_ms) for continuous navigation when holding keys
pygame.key.set_repeat(300, 50)

# Set high DPI awareness for Windows
if sys.platform != "emscripten":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Windows 8.1+
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Windows Vista+
        except:
            pass  # Not Windows or already set

screen = None
gpu_renderer = None  # GPURenderer instance (None if unavailable)


def is_gpu_available():
    """Check if GPU renderer is initialized and enabled."""
    return gpu_renderer is not None and gpu_renderer.enabled


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

# --- Mouse coordinate scaling for GPU fullscreen ---
# In GPU mode, the OpenGL display uses desktop resolution (e.g. 3840x2160) but
# game logic operates at internal resolution (e.g. 2560x1440).  pygame.SCALED
# handles this automatically for non-GPU mode, but OpenGL needs manual scaling.
_original_mouse_get_pos = pygame.mouse.get_pos
_original_event_get = pygame.event.get

# Cached scale factors — recalculated only on display mode changes
_cached_mouse_sx = 1.0
_cached_mouse_sy = 1.0

# Touch gesture recognizer — lazy-initialized on first touch platform use
_touch_recognizer = None


def _recalc_mouse_scale():
    """Recompute cached mouse scale factors. Call after display mode changes."""
    global _cached_mouse_sx, _cached_mouse_sy
    if gpu_renderer and gpu_renderer.enabled and FULLSCREEN:
        try:
            ww, wh = pygame.display.get_window_size()
            if ww != SCREEN_WIDTH or wh != SCREEN_HEIGHT:
                _cached_mouse_sx = SCREEN_WIDTH / ww
                _cached_mouse_sy = SCREEN_HEIGHT / wh
                return
        except Exception:
            pass
    _cached_mouse_sx = 1.0
    _cached_mouse_sy = 1.0


def _get_mouse_scale():
    """Scale factors from window coordinates to game coordinates."""
    return _cached_mouse_sx, _cached_mouse_sy


def _scaled_mouse_get_pos():
    """pygame.mouse.get_pos() returning game-space coordinates.

    On touch platforms, returns the last touch position instead.
    """
    if _touch_recognizer is not None:
        return _touch_recognizer.get_last_touch_pos()
    x, y = _original_mouse_get_pos()
    sx, sy = _get_mouse_scale()
    if sx != 1.0 or sy != 1.0:
        return (int(x * sx), int(y * sy))
    return (x, y)


def _scaled_event_get(*args, **kwargs):
    """pygame.event.get() with touch→mouse translation and coordinate scaling."""
    global _touch_recognizer
    events = _original_event_get(*args, **kwargs)

    # --- Touch gesture translation (lazy init) ---
    from touch_support import is_touch_platform
    if is_touch_platform():
        if _touch_recognizer is None:
            from touch_gestures import TouchGestureRecognizer
            _touch_recognizer = TouchGestureRecognizer(SCREEN_WIDTH or 1280, SCREEN_HEIGHT or 720)

        translated = []
        for event in events:
            if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
                translated.extend(_touch_recognizer.process_event(event))
            else:
                translated.append(event)
        # Check for long-press (time-based)
        translated.extend(_touch_recognizer.update())
        events = translated

    # --- Coordinate scaling for GPU fullscreen ---
    sx, sy = _get_mouse_scale()
    if sx != 1.0 or sy != 1.0:
        for event in events:
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                ox, oy = event.pos
                event.pos = (int(ox * sx), int(oy * sy))
            elif event.type == pygame.MOUSEMOTION:
                ox, oy = event.pos
                event.pos = (int(ox * sx), int(oy * sy))
                rx, ry = event.rel
                event.rel = (int(rx * sx), int(ry * sy))
    return events


pygame.mouse.get_pos = _scaled_mouse_get_pos
pygame.event.get = _scaled_event_get


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

    _is_web = sys.platform == "emscripten"

    # Web/Emscripten: simplified display setup — Pygbag manages the canvas.
    # pygame.SCALED, vsync, fullscreen, and temp-file caching don't work on WASM.
    if _is_web:
        SCREEN_WIDTH = 1920
        SCREEN_HEIGHT = 1080
        DESKTOP_WIDTH = 1920
        DESKTOP_HEIGHT = 1080
        SCALE_FACTOR = SCREEN_HEIGHT / 1080.0
        WINDOWED_WIDTH = SCREEN_WIDTH
        WINDOWED_HEIGHT = SCREEN_HEIGHT
        WINDOWED_SCALE_FACTOR = SCALE_FACTOR
        WINDOWED_FLAGS = 0
        FULLSCREEN = False
        VSYNC_ENABLED = False
        COMPETITIVE_MODE = False
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Stargwent")
        print(f"[Web] Display: {SCREEN_WIDTH}x{SCREEN_HEIGHT}, scale={SCALE_FACTOR:.3f}x")
        # Load card images
        print("Loading card images...")
        reload_card_images()
        print("Card images loaded.")
        return

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
    except (pygame.error, FileNotFoundError, OSError) as e:
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

    if gpu_renderer and gpu_renderer.enabled:
        # GPU mode — recreate OPENGL display and reinitialize context
        _recreate_gpu_display(fullscreen_enabled, vsync_value)
    elif fullscreen_enabled:
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

    # Recalculate mouse scale for GPU fullscreen
    _recalc_mouse_scale()

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


def _set_gl_attributes():
    """Set OpenGL context attributes for ModernGL compatibility."""
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK,
                                     pygame.GL_CONTEXT_PROFILE_CORE)


def _revert_to_scaled():
    """Revert from OPENGL display to SCALED after GPU failure."""
    global screen
    print("[GPU] Reverting to Pygame SCALED rendering")
    use_vsync = VSYNC_ENABLED
    vsync_value = 1 if use_vsync else 0
    flags = pygame.SCALED
    if FULLSCREEN:
        flags |= pygame.FULLSCREEN
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT), flags, vsync=vsync_value
    )
    vsync_status = "VSync ON" if use_vsync else "VSync OFF"
    mode = "Fullscreen" if FULLSCREEN else "Windowed"
    pygame.display.set_caption(f"Stargwent - {mode} ({vsync_status})")


def _recreate_gpu_display(fullscreen_enabled, vsync_value):
    """Recreate OPENGL display and GPU context for mode change (e.g. fullscreen toggle)."""
    global screen, gpu_renderer

    # Cleanup old GPU resources (context will be invalidated by display recreation)
    if gpu_renderer:
        try:
            gpu_renderer.cleanup()
        except Exception as e:
            print(f"[GPU] Cleanup error: {e}")
        gpu_renderer = None

    _set_gl_attributes()

    flags = pygame.OPENGL | pygame.DOUBLEBUF
    if fullscreen_enabled:
        flags |= pygame.FULLSCREEN
        # Use desktop resolution for fullscreen — GPU renderer upscales
        # the offscreen surface via fullscreen quad
        display_w, display_h = DESKTOP_WIDTH, DESKTOP_HEIGHT
    else:
        display_w, display_h = SCREEN_WIDTH, SCREEN_HEIGHT

    try:
        pygame.display.set_mode(
            (display_w, display_h), flags, vsync=vsync_value
        )
    except pygame.error as e:
        print(f"[GPU] Failed to recreate OpenGL display: {e}")
        _revert_to_scaled()
        return

    # Offscreen surface stays at internal render resolution
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    from gpu_renderer import GPURenderer
    renderer = GPURenderer(SCREEN_WIDTH, SCREEN_HEIGHT)
    if renderer.initialize():
        gpu_renderer = renderer
        try:
            from shaders import register_all_effects
            register_all_effects(gpu_renderer)
        except Exception as e:
            print(f"[GPU] Effect re-registration failed: {e}")
        _apply_gpu_settings()
        _recalc_mouse_scale()

        use_vsync = vsync_value == 1
        vsync_status = "VSync ON" if use_vsync else "VSync OFF"
        mode = "Fullscreen" if fullscreen_enabled else "Windowed"
        pygame.display.set_caption(f"Stargwent - {mode} GPU ({vsync_status})")
    else:
        print("[GPU] Failed to reinitialize — reverting to Pygame rendering")
        _revert_to_scaled()


def initialize_gpu():
    """Attempt to create GPURenderer with shared OpenGL context.

    On desktop: uses ModernGL with Pygame's shared GL context.
    On web (Emscripten): tries ModernGL first, falls back to WebGL renderer.
    On failure, reverts to SCALED Pygame rendering.
    """
    global gpu_renderer, screen

    import sys as _sys
    _is_web = _sys.platform == "emscripten"

    # Web/Emscripten: skip GPU — Pygbag manages its own canvas and GL context.
    # OPENGL|DOUBLEBUF display flags conflict with Pygbag's rendering pipeline.
    if _is_web:
        print("[GPU] Web platform — using Pygame rendering (Pygbag canvas)")
        return

    from gpu_renderer import MODERNGL_AVAILABLE
    if not MODERNGL_AVAILABLE:
        print("[GPU] moderngl not installed — using Pygame rendering")
        return

    # Check if GPU is enabled in settings
    try:
        from game_settings import get_settings
        settings = get_settings()
        if not settings.get_gpu_enabled():
            print("[GPU] Disabled in settings — using Pygame rendering")
            return
    except (ImportError, AttributeError):
        pass

    # --- Switch display to OpenGL mode ---
    _set_gl_attributes()

    flags = pygame.OPENGL | pygame.DOUBLEBUF
    if FULLSCREEN:
        flags |= pygame.FULLSCREEN
        # Use desktop resolution for fullscreen — GPU renderer upscales
        display_w, display_h = DESKTOP_WIDTH, DESKTOP_HEIGHT
    else:
        display_w, display_h = SCREEN_WIDTH, SCREEN_HEIGHT

    use_vsync = VSYNC_ENABLED
    vsync_value = 1 if use_vsync else 0

    try:
        pygame.display.set_mode(
            (display_w, display_h), flags, vsync=vsync_value
        )
    except pygame.error as e:
        print(f"[GPU] Failed to create OpenGL display: {e}")
        print("[GPU] Reverting to Pygame rendering")
        _revert_to_scaled()
        return

    # Offscreen surface — all game drawing targets this
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # --- Create GPU renderer ---
    renderer = None

    if MODERNGL_AVAILABLE:
        # Try ModernGL first (works on both desktop and some Emscripten builds)
        from gpu_renderer import GPURenderer
        renderer = GPURenderer(SCREEN_WIDTH, SCREEN_HEIGHT)
        if not renderer.initialize():
            renderer = None

        # Validate with FBO render test (desktop only — skip on web)
        if renderer and not _is_web:
            try:
                import moderngl
                ctx = renderer.ctx
                test_tex = ctx.texture((16, 16), 4)
                test_fbo = ctx.framebuffer(color_attachments=[test_tex])
                from gpu_renderer import _glsl_version
                _ver = _glsl_version()
                test_prog = ctx.program(
                    vertex_shader=_ver + """
                    in vec2 in_position;
                    void main() { gl_Position = vec4(in_position, 0.0, 1.0); }
                    """,
                    fragment_shader=_ver + """
                    out vec4 fragColor;
                    void main() { fragColor = vec4(1.0, 0.0, 0.0, 1.0); }
                    """,
                )
                import struct
                vbo_data = struct.pack('8f', -1, -1, 1, -1, -1, 1, 1, 1)
                test_vbo = ctx.buffer(vbo_data)
                test_vao = ctx.vertex_array(test_prog, [(test_vbo, '2f', 'in_position')])
                test_fbo.use()
                test_fbo.clear(0.0, 0.0, 0.0, 1.0)
                test_vao.render(moderngl.TRIANGLE_STRIP)
                ctx.finish()
                result = test_tex.read()
                r, g, b, a = result[0], result[1], result[2], result[3]
                test_vao.release()
                test_vbo.release()
                test_prog.release()
                test_fbo.release()
                test_tex.release()
                if r < 200:
                    print(f"[GPU] Render test failed: expected red, got RGBA=({r},{g},{b},{a})")
                    renderer.cleanup()
                    renderer = None
                else:
                    print(f"[GPU] Render test passed: RGBA=({r},{g},{b},{a})")
            except Exception as e:
                print(f"[GPU] Render test failed: {e}")
                renderer.cleanup()
                renderer = None

    # Fallback to WebGL renderer on Emscripten if ModernGL failed
    if renderer is None and _is_web:
        try:
            from webgl_renderer import WebGLRenderer
            renderer = WebGLRenderer(SCREEN_WIDTH, SCREEN_HEIGHT)
            if not renderer.initialize():
                renderer = None
        except Exception as e:
            print(f"[WebGL] Fallback failed: {e}")
            renderer = None

    if renderer is None:
        print("[GPU] Failed to initialize — reverting to Pygame rendering")
        _revert_to_scaled()
        return

    gpu_renderer = renderer

    # Set window caption
    vsync_status = "VSync ON" if use_vsync else "VSync OFF"
    mode = "Fullscreen" if FULLSCREEN else "Windowed"
    pygame.display.set_caption(f"Stargwent - {mode} GPU ({vsync_status})")

    # Register shader effects
    try:
        from shaders import register_all_effects
        register_all_effects(gpu_renderer)
    except Exception as e:
        print(f"[GPU] Effect registration failed: {e}")

    # Apply settings to effects
    _apply_gpu_settings()
    _recalc_mouse_scale()
    print("[GPU] Ready")


def _apply_gpu_settings():
    """Apply game settings to GPU effect enable/disable state."""
    if not gpu_renderer:
        return
    try:
        from game_settings import get_settings
        settings = get_settings()
        gpu_renderer.set_effect_enabled("bloom", settings.get_bloom_enabled())
        gpu_renderer.set_effect_enabled("vignette", settings.get_vignette_enabled())

        # Set bloom parameters
        bloom_adapter = gpu_renderer.get_effect("bloom")
        if bloom_adapter and hasattr(bloom_adapter, 'bloom'):
            bloom_adapter.bloom.extract.threshold = settings.get_bloom_threshold()
            bloom_adapter.bloom.composite.intensity = settings.get_bloom_intensity()
    except (ImportError, AttributeError):
        pass


def gpu_flip(surface=None):
    """Present frame via GPU post-processing or plain Pygame flip.

    Args:
        surface: Pygame surface to present. If None, uses display_manager.screen.
    """
    global gpu_renderer
    if gpu_renderer and gpu_renderer.enabled:
        target = surface or screen
        if target:
            gpu_renderer.present(target)
        else:
            pygame.display.flip()
    else:
        if gpu_renderer and not gpu_renderer.enabled:
            # GPU failed at runtime — revert to SCALED display
            print("[GPU] Runtime failure — reverting to Pygame rendering")
            try:
                gpu_renderer.cleanup()
            except Exception:
                pass
            gpu_renderer = None
            _revert_to_scaled()
        pygame.display.flip()


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
