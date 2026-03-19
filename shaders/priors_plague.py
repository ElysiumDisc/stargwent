"""
Prior's Plague GPU Effect

Toxic green miasma spreading horizontally across a row with corruption/decay.
Used when Prior's Plague ability cards are played — sickly green fog
spreads from the card, weakening enemies in the row.
"""

from gpu_renderer import ShaderPass
from shaders import glsl_version_header

PRIORS_PLAGUE_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform float time;
uniform vec2 plague_center;    // UV-space center of the plague origin
uniform float intensity;       // 0.0 = off, 1.0 = full
uniform float spread;          // 0.0 = none, 1.0 = full row coverage
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

float fbm(vec2 p) {
    float value = 0.0;
    float amp = 0.5;
    for (int i = 0; i < 4; i++) {
        value += amp * noise(p);
        p *= 2.1;
        amp *= 0.5;
    }
    return value;
}

void main() {
    vec4 scene = texture(tex, uv);

    if (intensity <= 0.0 || spread <= 0.0) {
        fragColor = scene;
        return;
    }

    vec2 to_center = uv - plague_center;

    // --- Horizontal Miasma Spread ---
    // Plague spreads wide horizontally, narrow vertically
    float horiz_range = spread * 0.5;  // How far left/right the plague reaches
    float vert_range = 0.06 * spread;   // Narrow vertical band (row height)

    float horiz_dist = abs(to_center.x) / max(horiz_range, 0.001);
    float vert_dist = abs(to_center.y) / max(vert_range, 0.001);

    // Soft falloff for the plague cloud shape
    float cloud_shape = 1.0 - smoothstep(0.0, 1.0, horiz_dist);
    cloud_shape *= 1.0 - smoothstep(0.0, 1.0, vert_dist);

    // --- Turbulent Noise (roiling plague fog) ---
    vec2 noise_uv = uv * 8.0 + vec2(time * 0.3, time * 0.15);
    float turb = fbm(noise_uv);
    float turb2 = fbm(noise_uv * 1.5 + vec2(3.7, 1.2));

    // Warp the cloud edges with turbulence
    cloud_shape *= mix(0.6, 1.0, turb);
    cloud_shape = clamp(cloud_shape, 0.0, 1.0);

    // --- Dripping Tendrils ---
    float tendrils = 0.0;
    for (int i = 0; i < 5; i++) {
        float fi = float(i);
        float tendril_x = plague_center.x + (fi - 2.0) * 0.08 * spread;
        float tx_dist = abs(uv.x - tendril_x);
        // Tendrils drip downward from the plague band
        float below = plague_center.y - uv.y;
        if (below > 0.0 && below < 0.08 * spread) {
            float tendril_shape = smoothstep(0.008, 0.002, tx_dist);
            // Wavy tendrils
            float wave = sin(uv.y * 40.0 + time * 3.0 + fi * 1.7) * 0.003;
            tendril_shape *= smoothstep(0.008 + wave, 0.002, tx_dist);
            tendril_shape *= 1.0 - smoothstep(0.0, 0.08 * spread, below);
            tendrils += tendril_shape * 0.4;
        }
    }

    // --- Corruption Veins (branching pattern) ---
    float veins = 0.0;
    float vein_noise = noise(uv * 20.0 + time * 0.5);
    float vein_pattern = smoothstep(0.48, 0.5, vein_noise) * cloud_shape;
    veins = vein_pattern * 0.3;

    // --- Color Mixing ---
    float total = (cloud_shape + tendrils + veins) * intensity;
    total = clamp(total, 0.0, 1.0);

    // Sickly green plague colors
    vec3 plague_dark = vec3(0.1, 0.3, 0.05);     // murky dark green
    vec3 plague_mid = vec3(0.2, 0.55, 0.12);      // sickly green
    vec3 plague_bright = vec3(0.35, 0.75, 0.2);   // toxic bright green

    // Color varies with turbulence
    vec3 plague_color = mix(plague_dark, plague_mid, turb);
    plague_color = mix(plague_color, plague_bright, turb2 * 0.5);

    // --- Scene Desaturation in plague area (corruption effect) ---
    float desat_amount = total * 0.3;
    float gray = dot(scene.rgb, vec3(0.299, 0.587, 0.114));
    vec3 desaturated = mix(scene.rgb, vec3(gray), desat_amount);

    // Slight green tint to the desaturated scene
    desaturated = mix(desaturated, desaturated * vec3(0.85, 1.1, 0.85), total * 0.4);

    // Additive plague fog on top
    vec3 result = desaturated + plague_color * total * 0.45;

    fragColor = vec4(result, 1.0);
}
"""


def create_priors_plague_pass(ctx):
    """Create Prior's Plague shader pass."""
    sp = ShaderPass(ctx, PRIORS_PLAGUE_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('plague_center', (0.5, 0.5))
    sp.set_uniform('intensity', 0.0)
    sp.set_uniform('spread', 0.0)
    return sp
