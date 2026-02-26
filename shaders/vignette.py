"""
Vignette Post-Processing Effect

Single-pass radial edge darkening for cinematic depth.
Uses smoothstep falloff from screen center.
"""

from gpu_renderer import ShaderPass
from shaders import glsl_version_header

VIGNETTE_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform float strength;
uniform float radius;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec4 color = texture(tex, uv);
    vec2 center = uv - vec2(0.5);
    float dist = length(center);
    float vignette = smoothstep(radius, radius - 0.25, dist);
    color.rgb *= mix(1.0, vignette, strength);
    fragColor = color;
}
"""


def create_vignette_pass(ctx, strength=0.5, radius=0.75):
    """Create vignette shader pass."""
    sp = ShaderPass(ctx, VIGNETTE_FRAG)
    sp.set_uniform('strength', strength)
    sp.set_uniform('radius', radius)
    return sp
