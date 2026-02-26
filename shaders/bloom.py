"""
Bloom/Glow Post-Processing Effect

3-pass effect:
1. Bright extraction — threshold pixels by luminance
2. Separable Gaussian blur (horizontal + vertical) at half resolution
3. Composite — blend blurred bright pixels back with original

Automatically enhances all existing bright-colored effects:
stargate chevrons, energy waves, explosions, score pops, faction glows.
"""

from gpu_renderer import ShaderPass, PASSTHROUGH_VERT
from shaders import glsl_version_header

# Pass 1: Extract bright pixels
BRIGHT_EXTRACT_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform float threshold;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec4 color = texture(tex, uv);
    float luminance = dot(color.rgb, vec3(0.2126, 0.7152, 0.0722));
    float brightness = max(0.0, luminance - threshold) / max(luminance, 0.001);
    fragColor = vec4(color.rgb * brightness, 1.0);
}
"""

# Pass 2a: Horizontal Gaussian blur
BLUR_H_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform vec2 tex_size;
in vec2 uv;
out vec4 fragColor;

void main() {
    float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    vec2 texel = 1.0 / tex_size;
    vec3 result = texture(tex, uv).rgb * weights[0];
    for (int i = 1; i < 5; i++) {
        float offset = float(i) * texel.x;
        result += texture(tex, uv + vec2(offset, 0.0)).rgb * weights[i];
        result += texture(tex, uv - vec2(offset, 0.0)).rgb * weights[i];
    }
    fragColor = vec4(result, 1.0);
}
"""

# Pass 2b: Vertical Gaussian blur
BLUR_V_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform vec2 tex_size;
in vec2 uv;
out vec4 fragColor;

void main() {
    float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    vec2 texel = 1.0 / tex_size;
    vec3 result = texture(tex, uv).rgb * weights[0];
    for (int i = 1; i < 5; i++) {
        float offset = float(i) * texel.y;
        result += texture(tex, uv + vec2(0.0, offset)).rgb * weights[i];
        result += texture(tex, uv - vec2(0.0, offset)).rgb * weights[i];
    }
    fragColor = vec4(result, 1.0);
}
"""

# Pass 3: Composite original + bloom
COMPOSITE_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform sampler2D bloom_tex;
uniform float intensity;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec3 original = texture(tex, uv).rgb;
    vec3 bloom = texture(bloom_tex, uv).rgb;
    vec3 result = original + bloom * intensity;
    fragColor = vec4(min(result, vec3(1.0)), 1.0);
}
"""


class BloomExtractPass(ShaderPass):
    """Extract bright pixels above luminance threshold."""

    def __init__(self, ctx, threshold=0.65):
        super().__init__(ctx, BRIGHT_EXTRACT_FRAG)
        self.threshold = threshold
        self.set_uniform('threshold', threshold)

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        self.set_uniform('threshold', self.threshold)
        # Extract at half resolution for performance
        hw, hh = width // 2, height // 2
        return super().apply(input_tex, fbo_pool, quad_vao, hw, hh)


class BloomBlurHPass(ShaderPass):
    """Horizontal Gaussian blur pass."""

    def __init__(self, ctx):
        super().__init__(ctx, BLUR_H_FRAG)

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        hw, hh = width // 2, height // 2
        self.set_uniform('tex_size', (float(hw), float(hh)))
        return super().apply(input_tex, fbo_pool, quad_vao, hw, hh)


class BloomBlurVPass(ShaderPass):
    """Vertical Gaussian blur pass."""

    def __init__(self, ctx):
        super().__init__(ctx, BLUR_V_FRAG)

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        hw, hh = width // 2, height // 2
        self.set_uniform('tex_size', (float(hw), float(hh)))
        return super().apply(input_tex, fbo_pool, quad_vao, hw, hh)


class BloomCompositePass(ShaderPass):
    """Composite original scene with blurred bloom texture."""

    def __init__(self, ctx, intensity=0.6):
        super().__init__(ctx, COMPOSITE_FRAG)
        self.intensity = intensity
        self._original_tex = None
        self._bloom_tex = None

    def set_textures(self, original_tex, bloom_tex):
        self._original_tex = original_tex
        self._bloom_tex = bloom_tex

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        """Composite pass uses the bloom (blurred) texture and original."""
        fbo, out_tex = fbo_pool.acquire(width, height)
        fbo.use()
        fbo.clear(0.0, 0.0, 0.0, 1.0)

        # Bind original scene to unit 0
        if self._original_tex:
            self._original_tex.use(location=0)
        else:
            input_tex.use(location=0)
        if 'tex' in self.program:
            self.program['tex'].value = 0

        # Bind bloom texture to unit 1
        if self._bloom_tex:
            self._bloom_tex.use(location=1)
        else:
            input_tex.use(location=1)
        if 'bloom_tex' in self.program:
            self.program['bloom_tex'].value = 1

        self.set_uniform('intensity', self.intensity)
        self._write_uniforms()
        import moderngl
        quad_vao.render(moderngl.TRIANGLE_STRIP)
        return fbo, out_tex


class BloomEffect:
    """Multi-pass bloom effect that wraps extract, blur, and composite passes."""

    def __init__(self, ctx, threshold=0.65, intensity=0.6):
        self.extract = BloomExtractPass(ctx, threshold)
        self.blur_h = BloomBlurHPass(ctx)
        self.blur_v = BloomBlurVPass(ctx)
        self.composite = BloomCompositePass(ctx, intensity)
        self.enabled = True
        self.threshold = threshold
        self.intensity = intensity

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        """Run full bloom pipeline: extract → blur_h → blur_v → composite."""
        temp_resources = []

        # Pass 1: Extract bright pixels (at half res)
        fbo1, bright_tex = self.extract.apply(
            input_tex, fbo_pool, self.extract._vao, width, height
        )
        temp_resources.append((fbo1, bright_tex))

        # Pass 2a: Horizontal blur
        fbo2, blur_h_tex = self.blur_h.apply(
            bright_tex, fbo_pool, self.blur_h._vao, width, height
        )
        temp_resources.append((fbo2, blur_h_tex))

        # Pass 2b: Vertical blur
        fbo3, blur_v_tex = self.blur_v.apply(
            blur_h_tex, fbo_pool, self.blur_v._vao, width, height
        )
        temp_resources.append((fbo3, blur_v_tex))

        # Pass 3: Composite original + bloom
        self.composite.set_textures(input_tex, blur_v_tex)
        fbo4, result_tex = self.composite.apply(
            input_tex, fbo_pool, self.composite._vao, width, height
        )

        # Release intermediate FBOs
        for fbo, tex in temp_resources:
            fbo_pool.release(fbo, tex)

        return fbo4, result_tex

    def cleanup(self):
        self.extract.cleanup()
        self.blur_h.cleanup()
        self.blur_v.cleanup()
        self.composite.cleanup()


class BloomPassAdapter:
    """Adapter to make BloomEffect work as a single entry in the effect chain."""

    def __init__(self, bloom_effect):
        self.bloom = bloom_effect
        self.enabled = True
        self.program = bloom_effect.extract.program  # for VAO creation
        self._vao = None  # Set by GPURenderer.add_effect

    def apply(self, input_tex, fbo_pool, quad_vao, width, height):
        return self.bloom.apply(input_tex, fbo_pool, quad_vao, width, height)

    def cleanup(self):
        self.bloom.cleanup()


def create_bloom_passes(ctx, threshold=0.65, intensity=0.6):
    """Factory: create bloom effect and return as list with adapter."""
    bloom = BloomEffect(ctx, threshold, intensity)
    adapter = BloomPassAdapter(bloom)
    return [adapter]
