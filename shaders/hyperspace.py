"""
Hyperspace Warp GPU Effect

Enhances hyperspace transitions with:
- Radial motion blur (multi-sample along direction from center)
- Warp factor uniform drives stretch intensity
- Blue-white streak color overlay
"""

from gpu_renderer import ShaderPass

HYPERSPACE_FRAG = """
#version 330
uniform sampler2D tex;
uniform float warp_factor;   // 0.0 = none, 1.0 = full warp
uniform vec2 center;         // UV-space center of warp
uniform int num_samples;     // Blur quality (4-12)
in vec2 uv;
out vec4 fragColor;

void main() {
    if (warp_factor <= 0.001) {
        fragColor = texture(tex, uv);
        return;
    }

    vec2 dir = uv - center;
    float dist = length(dir);

    // Radial blur: sample along direction from center
    float blur_strength = warp_factor * dist * 0.1;
    vec2 step_dir = normalize(dir + vec2(0.0001)) * blur_strength / float(num_samples);

    vec3 color = vec3(0.0);
    float total_weight = 0.0;
    for (int i = 0; i < num_samples; i++) {
        float t = float(i) / float(num_samples);
        vec2 sample_uv = uv + step_dir * (t - 0.5) * 2.0;
        sample_uv = clamp(sample_uv, vec2(0.0), vec2(1.0));
        float weight = 1.0 - abs(t - 0.5) * 2.0;  // Tent filter
        color += texture(tex, sample_uv).rgb * weight;
        total_weight += weight;
    }
    color /= total_weight;

    // Blue-white streak overlay at high warp
    float streak = smoothstep(0.3, 0.8, warp_factor) * dist * 0.5;
    vec3 streak_color = vec3(0.5, 0.7, 1.0) * streak;

    fragColor = vec4(color + streak_color, 1.0);
}
"""


def create_hyperspace_pass(ctx):
    """Create hyperspace warp shader pass."""
    sp = ShaderPass(ctx, HYPERSPACE_FRAG)
    sp.set_uniform('warp_factor', 0.0)
    sp.set_uniform('center', (0.5, 0.5))
    sp.set_uniform('num_samples', 8)
    return sp
