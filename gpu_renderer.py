"""
GPU Post-Processing Renderer for Stargwent

Uses ModernGL with Pygame's shared OpenGL context to apply GLSL shader
effects (bloom, vignette, distortion, etc.) on top of the Pygame-rendered
frame.  The final result is rendered directly to the default framebuffer
(screen) — no CPU readback needed.

Graceful fallback: if moderngl is unavailable or GPU init fails,
the game runs with pure Pygame rendering unchanged.
"""

import logging
import struct
import sys
import time

import pygame

from gpu_renderer_base import GpuRendererBase

logger = logging.getLogger(__name__)

try:
    import moderngl
    MODERNGL_AVAILABLE = True
except ImportError:
    MODERNGL_AVAILABLE = False


# Fullscreen quad vertices (position + texcoord)
QUAD_VERTICES = [
    # x,    y,   u,   v
    -1.0, -1.0, 0.0, 0.0,
     1.0, -1.0, 1.0, 0.0,
    -1.0,  1.0, 0.0, 1.0,
     1.0,  1.0, 1.0, 1.0,
]

# Pre-packed VBO data — avoids struct.pack() on every ShaderPass / VAO creation
_QUAD_VBO_DATA = struct.pack(f'{len(QUAD_VERTICES)}f', *QUAD_VERTICES)

# Sentinel for the uniform write-cache (distinct from any real uniform value).
_UNSET = object()

def _glsl_version():
    """Return the GLSL version header for the current platform."""
    if sys.platform == "emscripten":
        return "#version 300 es\nprecision highp float;\n"
    return "#version 330\n"

PASSTHROUGH_VERT = _glsl_version() + """
in vec2 in_position;
in vec2 in_texcoord;
out vec2 uv;
void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    uv = in_texcoord;
}
"""

PASSTHROUGH_FRAG = _glsl_version() + """
uniform sampler2D tex;
in vec2 uv;
out vec4 fragColor;
void main() {
    fragColor = texture(tex, uv);
}
"""

# Input-normalize pass (v13.0.0 pipeline refresh). The raw Pygame frame is
# uploaded zero-copy as the surface's native bytes, which are:
#   - BGRA in memory (32-bit surface masks R=0xFF0000 G=0xFF00 B=0xFF), and
#   - stored top-row-first (Pygame origin), i.e. vertically inverted vs GL.
# This pass flips V and swizzles BGR->RGB with a forced opaque alpha, producing
# a texture identical to the old `tobytes(surface, "RGBA", True)` result so the
# rest of the effect chain (and directional effects) behave pixel-identically.
NORMALIZE_FRAG = _glsl_version() + """
uniform sampler2D tex;
in vec2 uv;
out vec4 fragColor;
void main() {
    fragColor = vec4(texture(tex, vec2(uv.x, 1.0 - uv.y)).bgr, 1.0);
}
"""


class FBOPool:
    """Reusable framebuffer pool by resolution."""

    def __init__(self, ctx):
        self.ctx = ctx
        self._pool = {}  # (width, height) -> list of (fbo, texture)

    def acquire(self, width, height):
        key = (width, height)
        if key in self._pool and self._pool[key]:
            return self._pool[key].pop()
        tex = self.ctx.texture((width, height), 4)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        fbo = self.ctx.framebuffer(color_attachments=[tex])
        return fbo, tex

    def release(self, fbo, tex):
        key = (tex.width, tex.height)
        if key not in self._pool:
            self._pool[key] = []
        if len(self._pool[key]) < 3:
            self._pool[key].append((fbo, tex))
        else:
            # Pool full for this resolution — release immediately to prevent GPU memory leak
            fbo.release()
            tex.release()

    def cleanup(self):
        for key, items in self._pool.items():
            for fbo, tex in items:
                fbo.release()
                tex.release()
        self._pool.clear()

    def cleanup_stale(self, current_width, current_height):
        """Release pooled FBOs that don't match the current resolution.

        Called after a resolution change (e.g. fullscreen toggle, window
        resize) to prevent GPU memory leaks from stale buckets.
        """
        active = (current_width, current_height)
        stale_keys = [k for k in self._pool if k != active]
        for k in stale_keys:
            for fbo, tex in self._pool[k]:
                fbo.release()
                tex.release()
            del self._pool[k]


class ShaderPass:
    """Base class for a single GPU post-processing pass."""

    def __init__(self, ctx, fragment_source, vertex_source=PASSTHROUGH_VERT):
        self.ctx = ctx
        self.enabled = True
        # Whether to clear the target FBO before drawing. A pass that draws a
        # fullscreen quad with opaque alpha (a=1.0) fully replaces the target,
        # so the clear is redundant — set clears=False on such passes to skip
        # it (v13.0.0). Defaults True so unverified passes keep old behaviour.
        self.clears = True
        self.program = ctx.program(
            vertex_shader=vertex_source,
            fragment_shader=fragment_source,
        )
        self._uniforms = {}
        self._written = {}  # last value pushed per uniform, to skip redundant sets
        # Each pass gets its own VAO (program-specific attribute binding).
        # Keep a reference to the VBO so cleanup() can release it (previously
        # this was a local and leaked one buffer per pass on teardown).
        self._vbo = ctx.buffer(_QUAD_VBO_DATA)
        self._vao = ctx.vertex_array(
            self.program,
            [(self._vbo, '2f 2f', 'in_position', 'in_texcoord')],
        )

    def set_uniform(self, name, value):
        self._uniforms[name] = value

    def _write_uniforms(self):
        # Skip uniforms whose value is unchanged since the last push — static
        # uniforms (thresholds, intensities) are then set once, not every frame.
        for name, value in self._uniforms.items():
            if self._written.get(name, _UNSET) == value:
                continue
            if name in self.program:
                self.program[name].value = value
                self._written[name] = value

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        """Apply this shader pass. Returns (fbo, output_texture)."""
        fbo, out_tex = fbo_pool.acquire(width, height)
        fbo.use()
        if self.clears:
            fbo.clear(0.0, 0.0, 0.0, 1.0)
        input_tex.use(location=0)
        if 'tex' in self.program:
            self.program['tex'].value = 0
        self._write_uniforms()
        quad_vao.render(moderngl.TRIANGLE_STRIP)
        return fbo, out_tex

    def cleanup(self):
        if self._vao:
            self._vao.release()
        if self._vbo:
            self._vbo.release()
        self.program.release()


class GPURenderer(GpuRendererBase):
    """Core GPU rendering bridge using ModernGL shared context."""

    _PASS_TYPE = ShaderPass

    def __init__(self, width, height):
        super().__init__(width, height)
        self.ctx = None

        # GPU resources
        self.quad_vao = None
        self.fbo_pool = None
        self.input_texture = None
        self._passthrough = None
        self._normalize = None
        self._slow_upload_warned = False  # one-time guard for the tobytes warning

    def initialize(self):
        """Create ModernGL context sharing Pygame's OpenGL display."""
        try:
            self.ctx = moderngl.create_context()

            # Fullscreen quad
            vbo = self.ctx.buffer(_QUAD_VBO_DATA)

            # Passthrough shader (used when no effects active, and for final output)
            self._passthrough = ShaderPass(self.ctx, PASSTHROUGH_FRAG)
            # 'tex' always samples unit 0; bind the sampler once at init rather
            # than re-setting the uniform every present().
            if 'tex' in self._passthrough.program:
                self._passthrough.program['tex'].value = 0
            self.quad_vao = self.ctx.vertex_array(
                self._passthrough.program,
                [(vbo, '2f 2f', 'in_position', 'in_texcoord')],
            )

            # Input-normalize pass: turns the zero-copy raw upload (BGRA,
            # top-row-first) into a GL-oriented RGBA texture the chain expects.
            # It writes a fullscreen opaque quad, so the target clear is
            # redundant — skip it.
            self._normalize = ShaderPass(self.ctx, NORMALIZE_FRAG)
            self._normalize.clears = False

            # FBO pool
            self.fbo_pool = FBOPool(self.ctx)

            # Input texture (frame from Pygame)
            self.input_texture = self.ctx.texture(
                (self.width, self.height), 4
            )
            self.input_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

            self.enabled = True
            print(f"[GPU] ModernGL initialized: {self.ctx.info['GL_RENDERER']}")
            return True

        except Exception as e:
            print(f"[GPU] Initialization failed: {e}")
            self.enabled = False
            return False

    # Effect registry (add_effect/set_effect_enabled/is_effect_enabled/
    # get_effect) and update() are inherited from GpuRendererBase.

    def present(self, pygame_surface):
        """Upload Pygame frame to GPU, run shader chain, render to screen.

        The final result is rendered directly to the default framebuffer
        (OpenGL screen) via a fullscreen quad — no CPU readback needed.
        """
        try:
            w, h = pygame_surface.get_size()

            _t0 = time.perf_counter()

            # Fast path: zero-copy upload of the surface's native byte buffer,
            # skipping pygame.image.tobytes()'s per-pixel RGBA conversion
            # (~12.5ms/frame at 2560x1440 — the dominant cost of the old
            # pipeline). Valid only for a 32-bit BGRA surface; the bytes are
            # BGRA + top-row-first and the normalize pass fixes channel order
            # and orientation on the GPU. Any other format falls back to the
            # old format-agnostic conversion (and skips normalize, since
            # tobytes already yields RGBA + flipped).
            fast_upload = self.is_fast_upload(pygame_surface)
            if fast_upload:
                raw = pygame_surface.get_buffer()
            else:
                if not self._slow_upload_warned:
                    print("[GPU] WARNING: frame surface is not 32-bit BGRA; "
                          "falling back to slow tobytes() upload (~12.5ms/frame "
                          "at 1440p). Check display_manager.screen depth/masks.")
                    self._slow_upload_warned = True
                raw = pygame.image.tobytes(pygame_surface, "RGBA", True)
            if (w, h) != (self.input_texture.width, self.input_texture.height):
                # Wait for any in-flight GPU work referencing the old
                # texture to drain before release. Without this, some
                # Intel/AMD drivers can leak the texture or briefly
                # display garbage when the pipeline is still using it.
                self.ctx.finish()
                self.input_texture.release()
                self.input_texture = self.ctx.texture((w, h), 4)
                self.input_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
                # Resize invalidates the FBO pool buckets sized to the
                # old resolution; reclaim them now.
                if self.fbo_pool:
                    self.fbo_pool.cleanup_stale(w, h)
            self.input_texture.write(raw)

            # Reset blend state so previous Pygame/effect state can't leak in
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

            _t_upload = time.perf_counter()

            # Run shader chain — early-out if every effect is disabled
            temp_resources = []
            pass_count = 0

            # Normalize the raw upload (flip V + BGR->RGB, force opaque) into the
            # orientation/channel order the effect chain expects, so downstream
            # behaviour matches the old tobytes(..., "RGBA", True) path exactly.
            # Only needed on the fast path; the tobytes fallback is already
            # RGBA + flipped.
            if fast_upload:
                norm_fbo, norm_tex = self._normalize.apply(
                    self.input_texture, self.fbo_pool, self._normalize._vao, w, h
                )
                temp_resources.append((norm_fbo, norm_tex))
                current_tex = norm_tex
            else:
                current_tex = self.input_texture

            any_enabled = any(
                self._effect_enabled.get(name, False)
                and any(sp.enabled for sp in self._effects.get(name, []))
                for name in self._effect_order
            )
            if any_enabled:
                for name in self._effect_order:
                    if not self._effect_enabled.get(name, False):
                        continue
                    passes = self._effects.get(name, [])
                    for sp in passes:
                        if not sp.enabled:
                            continue
                        fbo, out_tex = sp.apply(
                            current_tex, self.fbo_pool, sp._vao, w, h
                        )
                        temp_resources.append((fbo, out_tex))
                        current_tex = out_tex
                        pass_count += 1

            _t_chain = time.perf_counter()

            # Render final result to default framebuffer (the display)
            self.ctx.screen.use()
            # Clear the screen FBO before final composite — without this,
            # the first frame after a window resize can show uncleared
            # garbage in margin areas not covered by the fullscreen quad.
            self.ctx.clear(0.0, 0.0, 0.0, 1.0)
            # Use get_window_size() — for OpenGL windows, get_surface().get_size()
            # may report the internal render resolution instead of the actual
            # display size (e.g. 2560x1440 instead of 3840x2160 in fullscreen)
            try:
                dw, dh = pygame.display.get_window_size()
            except Exception:
                dw, dh = w, h
            self.ctx.screen.viewport = (0, 0, dw, dh)

            current_tex.use(location=0)
            # 'tex' sampler bound to unit 0 once at init (see initialize()).
            self.quad_vao.render(moderngl.TRIANGLE_STRIP)

            pygame.display.flip()

            _t_present = time.perf_counter()
            self.last_timings = {
                "upload": (_t_upload - _t0) * 1000.0,
                "chain": (_t_chain - _t_upload) * 1000.0,
                "present": (_t_present - _t_chain) * 1000.0,
                "passes": pass_count,
                "fast_upload": fast_upload,
            }

            # Release temp FBOs back to pool
            for fbo, tex in temp_resources:
                self.fbo_pool.release(fbo, tex)

        except Exception as e:
            logger.exception("[GPU] Runtime error, disabling GPU: %s", e)
            self.enabled = False
            pygame.display.flip()

    def resize(self, width, height):
        """Rebuild resources on resolution change."""
        self.width = width
        self.height = height
        if self.input_texture:
            # Drain any in-flight GPU work before destroying the old
            # texture (see present()'s resize branch for the same fix).
            self.ctx.finish()
            self.input_texture.release()
            self.input_texture = self.ctx.texture((width, height), 4)
            self.input_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        if self.fbo_pool:
            # Stale FBOs from the previous resolution would leak GPU
            # memory if left in the pool — cleanup_stale() reclaims them.
            self.fbo_pool.cleanup_stale(width, height)

    def cleanup(self):
        """Release all GPU resources."""
        if not self.ctx:
            return
        try:
            for name, passes in self._effects.items():
                for sp in passes:
                    sp.cleanup()
            self._effects.clear()
            if self._passthrough:
                self._passthrough.cleanup()
            if self._normalize:
                self._normalize.cleanup()
            if self.input_texture:
                self.input_texture.release()
            if self.fbo_pool:
                self.fbo_pool.cleanup()
            if self.quad_vao:
                self.quad_vao.release()
            self.ctx.release()
            print("[GPU] Resources cleaned up")
        except Exception as e:
            print(f"[GPU] Cleanup error: {e}")
        self.enabled = False
