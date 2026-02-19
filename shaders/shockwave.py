"""
Shockwave / Impact Pulse GPU Effect

Used during round winner announcements:
- Expanding ring of screen distortion
- Flash at impact moment
- Radial displacement pushes pixels outward from ring center
"""

from gpu_renderer import ShaderPass

SHOCKWAVE_FRAG = """
#version 330
uniform sampler2D tex;
uniform float time;
uniform vec2 center;          // UV-space center of shockwave
uniform float ring_radius;    // Current radius of the ring (0-1.5)
uniform float ring_width;     // Width of the distortion band
uniform float distort_strength; // How much pixels get pushed
uniform float flash_intensity;  // Bright flash overlay (0-1)
in vec2 uv;
out vec4 fragColor;

void main() {
    vec2 dir = uv - center;
    float dist = length(dir);
    vec2 norm_dir = normalize(dir + vec2(0.0001));

    // Distance from the expanding ring edge
    float ring_dist = abs(dist - ring_radius);

    // Distortion: push pixels outward at the ring boundary
    float distortion = smoothstep(ring_width, 0.0, ring_dist) * distort_strength;

    // Displace UV along radial direction (outward from ring)
    vec2 displaced_uv = uv + norm_dir * distortion;
    displaced_uv = clamp(displaced_uv, vec2(0.0), vec2(1.0));

    vec4 color = texture(tex, displaced_uv);

    // Ring glow — bright line at the wavefront
    float ring_glow = smoothstep(ring_width, 0.0, ring_dist) * 0.25;
    // Color the ring with winner-appropriate tint (white-blue by default)
    vec3 ring_color = vec3(0.6, 0.8, 1.0);
    color.rgb += ring_color * ring_glow;

    // Flash overlay (fades out quickly)
    color.rgb += vec3(flash_intensity);

    // Slight chromatic aberration at ring edge
    if (distortion > 0.001) {
        float ca = distortion * 0.5;
        float r = texture(tex, clamp(uv + norm_dir * (distortion + ca), vec2(0.0), vec2(1.0))).r;
        float b = texture(tex, clamp(uv + norm_dir * (distortion - ca), vec2(0.0), vec2(1.0))).b;
        color.r = mix(color.r, r, 0.4);
        color.b = mix(color.b, b, 0.4);
    }

    fragColor = color;
}
"""


def create_shockwave_pass(ctx):
    """Create shockwave/impact pulse shader pass."""
    sp = ShaderPass(ctx, SHOCKWAVE_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('center', (0.5, 0.5))
    sp.set_uniform('ring_radius', 0.0)
    sp.set_uniform('ring_width', 0.12)
    sp.set_uniform('distort_strength', 0.0)
    sp.set_uniform('flash_intensity', 0.0)
    return sp
