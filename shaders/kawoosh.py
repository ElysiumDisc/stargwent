"""
Kawoosh Vortex GPU Effect

Displacement-based vortex during the kawoosh phase of stargate opening:
- Pixels displaced radially from gate center in surge direction
- Blue-white energy color additively blended
- Progress-based retraction
"""

from gpu_renderer import ShaderPass

KAWOOSH_FRAG = """
#version 330
uniform sampler2D tex;
uniform float time;
uniform vec2 gate_center;    // UV-space center
uniform float progress;      // 0.0 = start, 1.0 = retracted
uniform float strength;      // Displacement strength
uniform vec2 screen_size;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec4 scene = texture(tex, uv);

    if (strength <= 0.0) {
        fragColor = scene;
        return;
    }

    vec2 to_center = uv - gate_center;
    to_center.x *= screen_size.x / screen_size.y;
    float dist = length(to_center);

    // Kawoosh extends forward (downward in screen space) then retracts
    float surge_reach = (1.0 - progress) * 0.4;  // Max reach at start
    float surge_width = 0.15;

    // Cone-shaped displacement: strongest along forward direction
    vec2 surge_dir = vec2(0.0, 1.0);  // Downward
    float forward_dot = dot(normalize(to_center + vec2(0.0001)), surge_dir);
    float cone_factor = max(0.0, forward_dot);

    // Displacement falloff
    float falloff = smoothstep(surge_reach, 0.0, dist) * cone_factor;

    // Radial displacement (push pixels outward from gate center)
    vec2 dir = normalize(to_center + vec2(0.0001));
    dir.x /= screen_size.x / screen_size.y;
    vec2 displaced_uv = uv + dir * falloff * strength * 0.08;
    displaced_uv = clamp(displaced_uv, vec2(0.0), vec2(1.0));

    vec4 displaced_color = texture(tex, displaced_uv);

    // Additive blue-white energy at the wavefront
    float energy = falloff * (1.0 - progress) * 0.6;
    vec3 energy_color = vec3(0.4, 0.7, 1.0) * energy;

    fragColor = vec4(displaced_color.rgb + energy_color, 1.0);
}
"""


def create_kawoosh_pass(ctx):
    """Create kawoosh vortex shader pass."""
    sp = ShaderPass(ctx, KAWOOSH_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('gate_center', (0.5, 0.5))
    sp.set_uniform('progress', 0.0)
    sp.set_uniform('strength', 0.0)
    sp.set_uniform('screen_size', (2560.0, 1440.0))
    return sp
