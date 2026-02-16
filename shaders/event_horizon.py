"""
Stargate Event Horizon GPU Effect

Procedural rippling portal surface overlay:
- Noise-based animated distortion
- Blue-white gradient from center
- Glowing edge ring
- Driven by gate_center, gate_radius, intensity uniforms
"""

from gpu_renderer import ShaderPass

EVENT_HORIZON_FRAG = """
#version 330
uniform sampler2D tex;
uniform float time;
uniform vec2 gate_center;    // UV-space center of stargate
uniform float gate_radius;   // UV-space radius
uniform float intensity;     // 0.0 = inactive, 1.0 = full effect
uniform vec2 screen_size;
in vec2 uv;
out vec4 fragColor;

// Simplex-like noise
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
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 4; i++) {
        v += a * noise(p);
        p *= 2.0;
        a *= 0.5;
    }
    return v;
}

void main() {
    vec4 scene = texture(tex, uv);

    if (intensity <= 0.0 || gate_radius <= 0.0) {
        fragColor = scene;
        return;
    }

    // Aspect-corrected distance from gate center
    vec2 to_center = uv - gate_center;
    to_center.x *= screen_size.x / screen_size.y;
    float dist = length(to_center);
    float norm_dist = dist / gate_radius;

    if (norm_dist > 1.2) {
        fragColor = scene;
        return;
    }

    // Event horizon surface — inside the gate
    if (norm_dist < 1.0) {
        vec2 polar = vec2(atan(to_center.y, to_center.x), norm_dist);

        // Animated ripples
        float ripple = fbm(polar * 3.0 + vec2(time * 0.5, time * 0.3));
        ripple += 0.5 * sin(norm_dist * 12.0 - time * 2.0);

        // Blue-white gradient: white at center, blue at edges
        vec3 center_color = vec3(0.8, 0.9, 1.0);
        vec3 edge_color = vec3(0.2, 0.5, 1.0);
        vec3 horizon_color = mix(center_color, edge_color, norm_dist);
        horizon_color += vec3(ripple * 0.15);

        // Brightness peaks at center
        float brightness = (1.0 - norm_dist * 0.6) * intensity;
        vec3 result = mix(scene.rgb, horizon_color * brightness, intensity * (1.0 - norm_dist * 0.3));
        fragColor = vec4(result, 1.0);
    }
    // Glowing edge ring
    else {
        float edge_dist = norm_dist - 1.0;
        float edge_glow = exp(-edge_dist * 15.0) * intensity;
        vec3 glow_color = vec3(0.3, 0.6, 1.0) * edge_glow;
        fragColor = vec4(scene.rgb + glow_color, 1.0);
    }
}
"""


def create_event_horizon_pass(ctx):
    """Create event horizon shader pass."""
    sp = ShaderPass(ctx, EVENT_HORIZON_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('gate_center', (0.5, 0.5))
    sp.set_uniform('gate_radius', 0.0)
    sp.set_uniform('intensity', 0.0)
    sp.set_uniform('screen_size', (2560.0, 1440.0))
    return sp
