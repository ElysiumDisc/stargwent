"""
Ascension GPU Effect

Ethereal golden-white light column ascending skyward with radiant energy beams.
Used when Ascension ability cards are played — golden motes rise as the card
transcends to a higher plane of existence.
"""

from gpu_renderer import ShaderPass
from shaders import glsl_version_header

ASCENSION_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform float time;
uniform vec2 ascension_center;   // UV-space center of the ascending column
uniform float intensity;         // 0.0 = off, 1.0 = full
uniform float column_height;     // UV-space height of the light column (grows over time)
in vec2 uv;
out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void main() {
    vec4 scene = texture(tex, uv);

    if (intensity <= 0.0) {
        fragColor = scene;
        return;
    }

    vec2 to_center = uv - ascension_center;

    // --- Light Column ---
    // Vertical column above the card, narrowing toward the top
    float col_half_width = 0.04 * intensity;
    // Column extends upward (positive Y in UV = upward in GL coords)
    float col_top = ascension_center.y + column_height;
    float col_bottom = ascension_center.y - 0.02;

    float in_column = 0.0;
    if (uv.y > col_bottom && uv.y < col_top) {
        float height_frac = (uv.y - ascension_center.y) / max(column_height, 0.001);
        height_frac = clamp(height_frac, 0.0, 1.0);
        // Column narrows toward top
        float width_at_height = col_half_width * (1.0 - height_frac * 0.6);
        // Soft edges with shimmer
        float shimmer = noise(vec2(uv.y * 30.0, time * 2.0)) * 0.008;
        float edge_dist = abs(to_center.x) - width_at_height + shimmer;
        in_column = smoothstep(0.01, -0.005, edge_dist);
        // Fade at top
        in_column *= 1.0 - smoothstep(0.7, 1.0, height_frac);
        // Fade at bottom
        in_column *= smoothstep(-0.02, 0.02, uv.y - col_bottom);
    }

    // --- Radial Rays ---
    float angle = atan(to_center.y, to_center.x);
    float dist = length(to_center);
    float num_rays = 12.0;
    float ray_pattern = pow(abs(sin(angle * num_rays * 0.5 + time * 1.5)), 8.0);
    float ray_fade = exp(-dist * dist / (0.08 * intensity));
    float rays = ray_pattern * ray_fade * intensity * 0.4;

    // --- Central Glow ---
    float center_glow = exp(-dist * dist / (0.015 * intensity)) * intensity;

    // --- Rising energy wisps (procedural) ---
    float wisp = 0.0;
    for (int i = 0; i < 3; i++) {
        float fi = float(i);
        vec2 wisp_uv = uv - ascension_center;
        wisp_uv.x += sin(wisp_uv.y * 15.0 + time * (2.0 + fi) + fi * 2.1) * 0.02;
        float wisp_dist = abs(wisp_uv.x);
        float wisp_vert = smoothstep(0.0, column_height * 0.8, wisp_uv.y) *
                          (1.0 - smoothstep(column_height * 0.5, column_height, wisp_uv.y));
        wisp += smoothstep(0.02, 0.005, wisp_dist) * wisp_vert * 0.15;
    }

    // --- Combine ---
    float total = in_column + rays + center_glow * 0.6 + wisp;
    total = min(total, 1.0) * intensity;

    // Gold → white-gold color gradient
    vec3 gold = vec3(1.0, 0.85, 0.3);
    vec3 white_gold = vec3(1.0, 0.95, 0.75);
    vec3 ethereal = vec3(0.8, 0.85, 1.0);

    // Mix colors: center is white-gold, edges are gold, top is ethereal
    float height_mix = clamp((uv.y - ascension_center.y) / max(column_height, 0.001), 0.0, 1.0);
    vec3 col_color = mix(gold, white_gold, center_glow);
    col_color = mix(col_color, ethereal, height_mix * 0.4);

    vec3 result = scene.rgb + col_color * total * 0.8;

    fragColor = vec4(result, 1.0);
}
"""


def create_ascension_pass(ctx):
    """Create ascension shader pass."""
    sp = ShaderPass(ctx, ASCENSION_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('ascension_center', (0.5, 0.5))
    sp.set_uniform('intensity', 0.0)
    sp.set_uniform('column_height', 0.0)
    return sp
