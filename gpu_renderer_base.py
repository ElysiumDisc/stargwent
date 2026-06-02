"""Shared core for the GPU post-processing renderers (v13.0.0 pipeline refresh).

`GPURenderer` (desktop, ModernGL) and `WebGLRenderer` (web, raw GL ES) used to
carry byte-for-byte copies of the effect-registry bookkeeping, the time uniform
advance, and — after the refresh — the zero-copy upload format guard. Those live
here so the two backends only implement what genuinely differs (the GL API:
ModernGL objects vs raw GL ids for upload, FBO pooling, and pass dispatch).

A subclass sets `_PASS_TYPE` to its ShaderPass class so `add_effect()` can wrap a
single pass in a list, and calls `super().__init__(width, height)`.
"""


class GpuRendererBase:
    """Backend-agnostic state + effect registry shared by both renderers."""

    # Subclasses override with their concrete shader-pass class.
    _PASS_TYPE = ()

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.enabled = False
        self.time = 0.0

        # Per-frame timing breakdown (ms) for the debug overlay; populated by
        # the subclass present(). perf_counter deltas are sub-microsecond so
        # this is always measured rather than gated behind a debug flag.
        self.last_timings = {"upload": 0.0, "chain": 0.0, "present": 0.0, "passes": 0}

        # Shader effect chain
        self._effects = {}        # name -> list of shader passes
        self._effect_order = []   # ordered names
        self._effect_enabled = {}  # name -> bool

    # --- Effect registry (identical across backends) ---

    def add_effect(self, name, shader_passes, order=None):
        """Register a named effect (single shader pass or list of passes)."""
        if isinstance(shader_passes, self._PASS_TYPE):
            shader_passes = [shader_passes]
        self._effects[name] = shader_passes
        self._effect_enabled[name] = True
        if order is not None:
            self._effect_order.insert(order, name)
        else:
            self._effect_order.append(name)

    def set_effect_enabled(self, name, enabled):
        if name in self._effect_enabled:
            self._effect_enabled[name] = enabled

    def is_effect_enabled(self, name):
        return self._effect_enabled.get(name, False)

    def get_effect(self, name):
        """Get the shader pass(es) for a named effect."""
        passes = self._effects.get(name)
        if passes and len(passes) == 1:
            return passes[0]
        return passes

    def update(self, dt_ms):
        """Advance the time uniform for animated shaders."""
        self.time += dt_ms / 1000.0

    # --- Upload helpers (shared) ---

    @staticmethod
    def is_fast_upload(pygame_surface):
        """True if the surface can be uploaded zero-copy as native BGRA bytes.

        The fast path skips pygame.image.tobytes()'s per-pixel RGBA conversion
        (~12.5ms/frame at 2560x1440). It requires a 32-bit surface whose memory
        layout is BGRA (the default for 32-bit surfaces on little-endian
        desktops); the GPU normalize pass then fixes channel order + V flip.
        Anything else falls back to the format-agnostic tobytes() conversion.
        """
        return (
            pygame_surface.get_bytesize() == 4
            and pygame_surface.get_masks()[:3] == (0xFF0000, 0xFF00, 0xFF)
        )
