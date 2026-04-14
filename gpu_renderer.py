"""
GPU Post-Processing Renderer for Stargwent

Uses ModernGL with Pygame's shared OpenGL context to apply GLSL shader
effects (bloom, vignette, distortion, etc.) on top of the Pygame-rendered
frame.  The final result is rendered directly to the default framebuffer
(screen) — no CPU readback needed.

Graceful fallback: if moderngl is unavailable or GPU init fails,
the game runs with pure Pygame rendering unchanged.
"""

import struct
import sys

import pygame

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


class ShaderPass:
    """Base class for a single GPU post-processing pass."""

    def __init__(self, ctx, fragment_source, vertex_source=PASSTHROUGH_VERT):
        self.ctx = ctx
        self.enabled = True
        self.program = ctx.program(
            vertex_shader=vertex_source,
            fragment_shader=fragment_source,
        )
        self._uniforms = {}
        # Each pass gets its own VAO (program-specific attribute binding)
        vbo = ctx.buffer(_QUAD_VBO_DATA)
        self._vao = ctx.vertex_array(
            self.program,
            [(vbo, '2f 2f', 'in_position', 'in_texcoord')],
        )

    def set_uniform(self, name, value):
        self._uniforms[name] = value

    def _write_uniforms(self):
        for name, value in self._uniforms.items():
            if name in self.program:
                self.program[name].value = value

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        """Apply this shader pass. Returns (fbo, output_texture)."""
        fbo, out_tex = fbo_pool.acquire(width, height)
        fbo.use()
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
        self.program.release()


class GPURenderer:
    """Core GPU rendering bridge using ModernGL shared context."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ctx = None
        self.enabled = False
        self.time = 0.0

        # Shader effect chain
        self._effects = {}  # name -> ShaderPass or list of ShaderPass
        self._effect_order = []  # ordered names
        self._effect_enabled = {}  # name -> bool

        # GPU resources
        self.quad_vao = None
        self.fbo_pool = None
        self.input_texture = None
        self._passthrough = None

    def initialize(self):
        """Create ModernGL context sharing Pygame's OpenGL display."""
        try:
            self.ctx = moderngl.create_context()

            # Fullscreen quad
            vbo = self.ctx.buffer(_QUAD_VBO_DATA)

            # Passthrough shader (used when no effects active, and for final output)
            self._passthrough = ShaderPass(self.ctx, PASSTHROUGH_FRAG)
            self.quad_vao = self.ctx.vertex_array(
                self._passthrough.program,
                [(vbo, '2f 2f', 'in_position', 'in_texcoord')],
            )

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

    def _make_vao_for(self, program):
        """Create a VAO for a given shader program using the quad VBO."""
        vbo = self.ctx.buffer(_QUAD_VBO_DATA)
        return self.ctx.vertex_array(
            program,
            [(vbo, '2f 2f', 'in_position', 'in_texcoord')],
        )

    def add_effect(self, name, shader_passes, order=None):
        """Register a named effect (single ShaderPass or list of passes)."""
        if isinstance(shader_passes, ShaderPass):
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
        """Advance time uniform for animated shaders."""
        self.time += dt_ms / 1000.0

    def present(self, pygame_surface):
        """Upload Pygame frame to GPU, run shader chain, render to screen.

        The final result is rendered directly to the default framebuffer
        (OpenGL screen) via a fullscreen quad — no CPU readback needed.
        """
        try:
            w, h = pygame_surface.get_size()

            # Upload frame to GPU texture
            raw = pygame.image.tobytes(pygame_surface, "RGBA", True)
            if (w, h) != (self.input_texture.width, self.input_texture.height):
                self.input_texture.release()
                self.input_texture = self.ctx.texture((w, h), 4)
                self.input_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.input_texture.write(raw)

            # Reset blend state so previous Pygame/effect state can't leak in
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

            # Run shader chain — early-out if every effect is disabled
            current_tex = self.input_texture
            temp_resources = []

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

            # Render final result to default framebuffer (the display)
            self.ctx.screen.use()
            # Use get_window_size() — for OpenGL windows, get_surface().get_size()
            # may report the internal render resolution instead of the actual
            # display size (e.g. 2560x1440 instead of 3840x2160 in fullscreen)
            try:
                dw, dh = pygame.display.get_window_size()
            except Exception:
                dw, dh = w, h
            self.ctx.screen.viewport = (0, 0, dw, dh)

            current_tex.use(location=0)
            if 'tex' in self._passthrough.program:
                self._passthrough.program['tex'].value = 0
            self.quad_vao.render(moderngl.TRIANGLE_STRIP)

            pygame.display.flip()

            # Release temp FBOs back to pool
            for fbo, tex in temp_resources:
                self.fbo_pool.release(fbo, tex)

        except Exception as e:
            print(f"[GPU] Runtime error, disabling GPU: {e}")
            self.enabled = False
            pygame.display.flip()

    def resize(self, width, height):
        """Rebuild resources on resolution change."""
        self.width = width
        self.height = height
        if self.input_texture:
            self.input_texture.release()
            self.input_texture = self.ctx.texture((width, height), 4)
            self.input_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

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
