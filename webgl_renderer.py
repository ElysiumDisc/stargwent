"""
WebGL 2.0 GPU Renderer for Stargwent (Emscripten/Pygbag).

Provides the same public API as GPURenderer but uses raw OpenGL ES 3.0 calls
via ctypes, which Emscripten maps to WebGL 2.0 automatically.

This renderer is only used when running in the browser (sys.platform == "emscripten")
and moderngl is not available.
"""

import struct
import sys
import ctypes

import pygame

# OpenGL ES 3.0 constants
GL_TRUE = 1
GL_FALSE = 0
GL_FLOAT = 0x1406
GL_UNSIGNED_BYTE = 0x1401
GL_RGBA = 0x1908
GL_RGBA8 = 0x8058
GL_TEXTURE_2D = 0x0DE1
GL_TEXTURE0 = 0x84C0
GL_TEXTURE_MIN_FILTER = 0x2801
GL_TEXTURE_MAG_FILTER = 0x2800
GL_LINEAR = 0x2601
GL_FRAMEBUFFER = 0x8D40
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_TRIANGLE_STRIP = 0x0005
GL_VERTEX_SHADER = 0x8B31
GL_FRAGMENT_SHADER = 0x8B30
GL_COMPILE_STATUS = 0x8B81
GL_LINK_STATUS = 0x8B82
GL_ARRAY_BUFFER = 0x8889
GL_STATIC_DRAW = 0x88E4
GL_COLOR_BUFFER_BIT = 0x4000
GL_VIEWPORT = 0x0BA2

# Try to import GL functions from SDL2's GL loader
try:
    import OpenGL.GL as gl
    _HAS_PYOPENGL = True
except ImportError:
    _HAS_PYOPENGL = False
    gl = None


def _glsl_version():
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

QUAD_VERTICES = [
    -1.0, -1.0, 0.0, 0.0,
     1.0, -1.0, 1.0, 0.0,
    -1.0,  1.0, 0.0, 1.0,
     1.0,  1.0, 1.0, 1.0,
]
_QUAD_DATA = struct.pack(f'{len(QUAD_VERTICES)}f', *QUAD_VERTICES)


class WebGLShaderPass:
    """A single shader pass using raw GL calls."""

    def __init__(self, fragment_source, vertex_source=None):
        if vertex_source is None:
            vertex_source = PASSTHROUGH_VERT
        self.enabled = True
        self.program = 0
        self.vao = 0
        self.vbo = 0
        self._uniform_cache = {}

        if not _HAS_PYOPENGL:
            return

        # Compile shaders
        vs = self._compile_shader(vertex_source, GL_VERTEX_SHADER)
        fs = self._compile_shader(fragment_source, GL_FRAGMENT_SHADER)
        if not vs or not fs:
            return

        self.program = gl.glCreateProgram()
        gl.glAttachShader(self.program, vs)
        gl.glAttachShader(self.program, fs)
        gl.glLinkProgram(self.program)

        status = gl.glGetProgramiv(self.program, GL_LINK_STATUS)
        if not status:
            log = gl.glGetProgramInfoLog(self.program)
            print(f"[WebGL] Shader link error: {log}")
            self.program = 0
            return

        gl.glDeleteShader(vs)
        gl.glDeleteShader(fs)

        # Create VAO + VBO
        self.vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao)

        self.vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(GL_ARRAY_BUFFER, len(_QUAD_DATA), _QUAD_DATA, GL_STATIC_DRAW)

        # in_position (location 0)
        pos_loc = gl.glGetAttribLocation(self.program, "in_position")
        if pos_loc >= 0:
            gl.glEnableVertexAttribArray(pos_loc)
            gl.glVertexAttribPointer(pos_loc, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))

        # in_texcoord (location 1)
        tc_loc = gl.glGetAttribLocation(self.program, "in_texcoord")
        if tc_loc >= 0:
            gl.glEnableVertexAttribArray(tc_loc)
            gl.glVertexAttribPointer(tc_loc, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))

        gl.glBindVertexArray(0)

    def _compile_shader(self, source, shader_type):
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, source)
        gl.glCompileShader(shader)
        status = gl.glGetShaderiv(shader, GL_COMPILE_STATUS)
        if not status:
            log = gl.glGetShaderInfoLog(shader)
            kind = "vertex" if shader_type == GL_VERTEX_SHADER else "fragment"
            print(f"[WebGL] {kind} shader compile error: {log}")
            gl.glDeleteShader(shader)
            return 0
        return shader

    def set_uniform(self, name, value):
        if not self.program:
            return
        loc = self._get_uniform_loc(name)
        if loc < 0:
            return
        gl.glUseProgram(self.program)
        if isinstance(value, float):
            gl.glUniform1f(loc, value)
        elif isinstance(value, int):
            gl.glUniform1i(loc, value)
        elif isinstance(value, (tuple, list)):
            if len(value) == 2:
                gl.glUniform2f(loc, *value)
            elif len(value) == 3:
                gl.glUniform3f(loc, *value)
            elif len(value) == 4:
                gl.glUniform4f(loc, *value)

    def _get_uniform_loc(self, name):
        if name not in self._uniform_cache:
            self._uniform_cache[name] = gl.glGetUniformLocation(self.program, name)
        return self._uniform_cache[name]

    def apply(self, input_tex_id, fbo_id, out_tex_id, width, height):
        """Render this pass: bind FBO, set input texture, draw quad."""
        if not self.program:
            return
        gl.glBindFramebuffer(GL_FRAMEBUFFER, fbo_id)
        gl.glViewport(0, 0, width, height)

        gl.glUseProgram(self.program)

        gl.glActiveTexture(GL_TEXTURE0)
        gl.glBindTexture(GL_TEXTURE_2D, input_tex_id)
        tex_loc = self._get_uniform_loc("tex")
        if tex_loc >= 0:
            gl.glUniform1i(tex_loc, 0)

        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        gl.glBindVertexArray(0)

    def cleanup(self):
        if not _HAS_PYOPENGL:
            return
        if self.vao:
            gl.glDeleteVertexArrays(1, [self.vao])
        if self.vbo:
            gl.glDeleteBuffers(1, [self.vbo])
        if self.program:
            gl.glDeleteProgram(self.program)


class WebGLRenderer:
    """WebGL 2.0 renderer implementing the same interface as GPURenderer."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.enabled = False
        self.time = 0.0

        self._effects = {}
        self._effect_order = []
        self._effect_enabled = {}

        self._passthrough = None
        self._input_tex = 0
        self._fbos = {}  # (w,h) -> list of (fbo_id, tex_id)

    def initialize(self):
        """Initialize using raw GL calls (Emscripten maps to WebGL 2.0)."""
        if not _HAS_PYOPENGL:
            print("[WebGL] PyOpenGL not available")
            return False

        try:
            self._passthrough = WebGLShaderPass(PASSTHROUGH_FRAG)
            if not self._passthrough.program:
                print("[WebGL] Failed to compile passthrough shader")
                return False

            # Create input texture
            self._input_tex = gl.glGenTextures(1)
            gl.glBindTexture(GL_TEXTURE_2D, self._input_tex)
            gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            gl.glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self.width, self.height,
                           0, GL_RGBA, GL_UNSIGNED_BYTE, None)

            renderer_info = gl.glGetString(gl.GL_RENDERER)
            if isinstance(renderer_info, bytes):
                renderer_info = renderer_info.decode()
            print(f"[WebGL] Initialized: {renderer_info}")
            self.enabled = True
            return True

        except Exception as e:
            print(f"[WebGL] Initialization failed: {e}")
            self.enabled = False
            return False

    def add_effect(self, name, shader_passes, order=None):
        if isinstance(shader_passes, WebGLShaderPass):
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
        passes = self._effects.get(name)
        if passes and len(passes) == 1:
            return passes[0]
        return passes

    def update(self, dt_ms):
        self.time += dt_ms / 1000.0

    def _acquire_fbo(self, width, height):
        """Get or create an FBO + texture pair."""
        key = (width, height)
        if key in self._fbos and self._fbos[key]:
            return self._fbos[key].pop()

        tex = gl.glGenTextures(1)
        gl.glBindTexture(GL_TEXTURE_2D, tex)
        gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        gl.glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height,
                       0, GL_RGBA, GL_UNSIGNED_BYTE, None)

        fbo = gl.glGenFramebuffers(1)
        gl.glBindFramebuffer(GL_FRAMEBUFFER, fbo)
        gl.glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0)
        gl.glBindFramebuffer(GL_FRAMEBUFFER, 0)

        return fbo, tex

    def _release_fbo(self, fbo, tex, width, height):
        key = (width, height)
        if key not in self._fbos:
            self._fbos[key] = []
        self._fbos[key].append((fbo, tex))

    def present(self, pygame_surface):
        """Upload Pygame frame to GPU, run shader chain, render to screen."""
        try:
            w, h = pygame_surface.get_size()

            # Upload frame to input texture
            raw = pygame.image.tobytes(pygame_surface, "RGBA", True)
            gl.glBindTexture(GL_TEXTURE_2D, self._input_tex)
            gl.glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h,
                           0, GL_RGBA, GL_UNSIGNED_BYTE, raw)

            # Run shader chain
            current_tex = self._input_tex
            temp_resources = []

            for name in self._effect_order:
                if not self._effect_enabled.get(name, False):
                    continue
                passes = self._effects.get(name, [])
                for sp in passes:
                    if not sp.enabled or not sp.program:
                        continue
                    fbo, out_tex = self._acquire_fbo(w, h)
                    sp.apply(current_tex, fbo, out_tex, w, h)
                    temp_resources.append((fbo, out_tex, w, h))
                    current_tex = out_tex

            # Render to default framebuffer (screen)
            gl.glBindFramebuffer(GL_FRAMEBUFFER, 0)
            try:
                dw, dh = pygame.display.get_window_size()
            except Exception:
                dw, dh = w, h
            gl.glViewport(0, 0, dw, dh)

            gl.glActiveTexture(GL_TEXTURE0)
            gl.glBindTexture(GL_TEXTURE_2D, current_tex)
            self._passthrough.set_uniform("tex", 0)
            gl.glUseProgram(self._passthrough.program)
            gl.glBindVertexArray(self._passthrough.vao)
            gl.glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
            gl.glBindVertexArray(0)

            pygame.display.flip()

            # Release temp FBOs
            for fbo, tex, tw, th in temp_resources:
                self._release_fbo(fbo, tex, tw, th)

        except Exception as e:
            print(f"[WebGL] Runtime error, disabling: {e}")
            self.enabled = False
            pygame.display.flip()

    def resize(self, width, height):
        self.width = width
        self.height = height
        if self._input_tex:
            gl.glBindTexture(GL_TEXTURE_2D, self._input_tex)
            gl.glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height,
                           0, GL_RGBA, GL_UNSIGNED_BYTE, None)

    def cleanup(self):
        if not _HAS_PYOPENGL:
            return
        try:
            for name, passes in self._effects.items():
                for sp in passes:
                    sp.cleanup()
            self._effects.clear()
            if self._passthrough:
                self._passthrough.cleanup()
            if self._input_tex:
                gl.glDeleteTextures(1, [self._input_tex])
            for key, items in self._fbos.items():
                for fbo, tex in items:
                    gl.glDeleteFramebuffers(1, [fbo])
                    gl.glDeleteTextures(1, [tex])
            self._fbos.clear()
            print("[WebGL] Resources cleaned up")
        except Exception as e:
            print(f"[WebGL] Cleanup error: {e}")
        self.enabled = False
