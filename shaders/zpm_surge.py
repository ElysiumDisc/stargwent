"""
ZPM Electric Arcs GPU Effect

GPU lightning arcs radiating from ZPM center:
- Procedural lightning via multi-octave sin
- Multiple arcs distributed radially
- Cyan-white color, fading with distance
"""

from gpu_renderer import ShaderPass
from shaders import glsl_version_header

ZPM_SURGE_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform float time;
uniform vec2 zpm_center;     // UV-space center
uniform float intensity;     // 0.0 = off, 1.0 = full
uniform float surge_radius;  // UV-space max reach of arcs
uniform int num_arcs;        // Number of lightning arcs (4-12)
in vec2 uv;
out vec4 fragColor;

float hash(float n) {
    return fract(sin(n) * 43758.5453);
}

void main() {
    vec4 scene = texture(tex, uv);

    if (intensity <= 0.0 || surge_radius <= 0.0) {
        fragColor = scene;
        return;
    }

    vec2 to_center = uv - zpm_center;
    float dist = length(to_center);
    float angle = atan(to_center.y, to_center.x);

    float arc_brightness = 0.0;

    for (int i = 0; i < num_arcs && i < 12; i++) {
        // Each arc has a base angle
        float arc_angle = float(i) * 6.283185 / float(num_arcs) + time * 0.5;
        float angle_diff = abs(mod(angle - arc_angle + 3.14159, 6.28318) - 3.14159);

        // Arc width narrows with distance
        float arc_width = 0.08 * (1.0 - dist / surge_radius);
        if (arc_width <= 0.0) continue;

        // Lightning jitter (multi-octave sin)
        float jitter = 0.0;
        float freq = 20.0;
        float amp = 0.03;
        for (int j = 0; j < 3; j++) {
            jitter += amp * sin(dist * freq + time * (5.0 + float(j) * 3.0) + hash(float(i)) * 100.0);
            freq *= 2.0;
            amp *= 0.5;
        }

        float arc_dist = abs(angle_diff + jitter);
        float arc = smoothstep(arc_width, 0.0, arc_dist);

        // Fade with distance
        float fade = 1.0 - smoothstep(0.0, surge_radius, dist);
        arc *= fade;

        arc_brightness += arc;
    }

    arc_brightness = min(arc_brightness, 1.0) * intensity;

    // Cyan-white ZPM energy color
    vec3 arc_color = mix(vec3(0.0, 0.8, 1.0), vec3(1.0), arc_brightness * 0.5);
    vec3 result = scene.rgb + arc_color * arc_brightness * 0.7;

    // Central glow
    float center_glow = exp(-dist * dist / (surge_radius * surge_radius * 0.1)) * intensity;
    result += vec3(0.4, 0.7, 1.0) * center_glow * 0.3;

    fragColor = vec4(result, 1.0);
}
"""


def create_zpm_surge_pass(ctx):
    """Create ZPM surge shader pass."""
    sp = ShaderPass(ctx, ZPM_SURGE_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('zpm_center', (0.5, 0.5))
    sp.set_uniform('intensity', 0.0)
    sp.set_uniform('surge_radius', 0.0)
    sp.set_uniform('num_arcs', 8)
    return sp
