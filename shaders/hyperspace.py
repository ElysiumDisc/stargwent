"""
Hyperspace Warp GPU Effect

Enhances hyperspace transitions with:
- Radial motion blur (multi-sample along direction from center)
- Procedural speed lines (star streaks generated in shader)
- Chromatic aberration that increases with warp
- Tunnel vignette darkening at edges
- Blue-white streak color overlay with energy pulse
"""

from gpu_renderer import ShaderPass
from shaders import glsl_version_header

HYPERSPACE_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform float warp_factor;   // 0.0 = none, 1.0 = full warp
uniform vec2 center;         // UV-space center of warp
uniform int num_samples;     // Blur quality (4-16)
uniform float time;          // Animation time
uniform float direction;     // 1.0 = outward (entering), -1.0 = inward (emerging)
in vec2 uv;
out vec4 fragColor;

// Pseudo-random noise
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

void main() {
    if (warp_factor <= 0.001) {
        fragColor = texture(tex, uv);
        return;
    }

    vec2 dir = uv - center;
    float dist = length(dir);
    vec2 norm_dir = normalize(dir + vec2(0.0001));

    // --- Radial Motion Blur ---
    float blur_strength = warp_factor * dist * 0.15;
    vec2 step_dir = norm_dir * blur_strength / float(num_samples);

    vec3 color = vec3(0.0);
    float total_weight = 0.0;
    for (int i = 0; i < num_samples && i < 16; i++) {
        float t = float(i) / float(num_samples);
        vec2 offset = step_dir * (t - 0.5) * 2.0 * direction;
        vec2 sample_uv = clamp(uv + offset, vec2(0.0), vec2(1.0));
        float weight = 1.0 - abs(t - 0.5) * 2.0;  // Tent filter
        color += texture(tex, sample_uv).rgb * weight;
        total_weight += weight;
    }
    color /= total_weight;

    // --- Chromatic Aberration (radial) ---
    float ca_amount = warp_factor * dist * 0.012;
    vec2 ca_offset = norm_dir * ca_amount;
    float r = texture(tex, clamp(uv + ca_offset, vec2(0.0), vec2(1.0))).r;
    float b = texture(tex, clamp(uv - ca_offset, vec2(0.0), vec2(1.0))).b;
    // Blend chromatic aberration into the blurred result
    color.r = mix(color.r, r, warp_factor * 0.5);
    color.b = mix(color.b, b, warp_factor * 0.5);

    // --- Procedural Speed Lines ---
    // Angular hash creates distinct "lanes" of star streaks
    float angle = atan(dir.y, dir.x);
    float lane = floor(angle * 40.0 / 3.14159);  // ~80 lanes around circle
    float lane_hash = hash(vec2(lane, 1.0));

    // Only some lanes have visible streaks
    float streak_visible = step(0.55, lane_hash);

    // Streak brightness varies with distance and time — moves outward or inward
    float streak_phase = fract(dist * 3.0 - time * 2.0 * direction + lane_hash * 6.28);
    float streak_bright = smoothstep(0.0, 0.15, streak_phase) *
                          smoothstep(0.4, 0.15, streak_phase);
    // Streaks are more visible at higher warp and further from center
    float streak_intensity = streak_visible * streak_bright *
                             warp_factor * smoothstep(0.05, 0.3, dist) * 0.6;

    // Streak color: blue-white with slight variation
    vec3 streak_color = mix(vec3(0.5, 0.7, 1.0), vec3(0.9, 0.95, 1.0), lane_hash);
    color += streak_color * streak_intensity;

    // --- Blue-White Energy Overlay ---
    float energy = smoothstep(0.3, 0.9, warp_factor) * dist * 0.3;
    vec3 energy_color = vec3(0.4, 0.6, 1.0) * energy;
    color += energy_color;

    // --- Tunnel Vignette ---
    // Darken edges more at high warp (tunnel vision effect)
    float vignette = 1.0 - smoothstep(0.2, 0.9, dist) * warp_factor * 0.5;
    color *= vignette;

    // --- Center Glow ---
    // Bright core at high warp
    float core_glow = smoothstep(0.15, 0.0, dist) * warp_factor * 0.3;
    color += vec3(0.6, 0.8, 1.0) * core_glow;

    fragColor = vec4(color, 1.0);
}
"""


def create_hyperspace_pass(ctx):
    """Create hyperspace warp shader pass."""
    sp = ShaderPass(ctx, HYPERSPACE_FRAG)
    sp.set_uniform('warp_factor', 0.0)
    sp.set_uniform('center', (0.5, 0.5))
    sp.set_uniform('num_samples', 12)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('direction', 1.0)
    return sp
