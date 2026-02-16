"""
Asgard Beam Volumetric GPU Effect

Adds a light-scattering column overlay to existing AsgardBeamTransportEffect:
- Vertical column with Gaussian falloff from center-x
- Downward scan line
- Shimmer via high-frequency sin
"""

from gpu_renderer import ShaderPass

ASGARD_BEAM_FRAG = """
#version 330
uniform sampler2D tex;
uniform float time;
uniform float beam_x;        // UV-space x center of beam
uniform float beam_top;      // UV-space top of beam (0.0 = top of screen)
uniform float beam_bottom;   // UV-space bottom of beam
uniform float intensity;     // 0.0 = off, 1.0 = full
uniform float scan_progress; // 0.0 = top, 1.0 = bottom
in vec2 uv;
out vec4 fragColor;

void main() {
    vec4 scene = texture(tex, uv);

    if (intensity <= 0.0) {
        fragColor = scene;
        return;
    }

    // Check if within beam vertical range
    float in_beam_y = step(beam_top, uv.y) * step(uv.y, beam_bottom);

    // Gaussian falloff from beam center-x
    float dx = uv.x - beam_x;
    float beam_width = 0.04;  // Narrow beam
    float column = exp(-dx * dx / (2.0 * beam_width * beam_width));
    column *= in_beam_y;

    // Scan line (bright horizontal bar moving down)
    float scan_y = mix(beam_top, beam_bottom, scan_progress);
    float scan_dist = abs(uv.y - scan_y);
    float scan_line = exp(-scan_dist * scan_dist / 0.0005) * in_beam_y;

    // High-frequency shimmer
    float shimmer = 0.8 + 0.2 * sin(uv.y * 200.0 + time * 15.0);
    shimmer *= 0.9 + 0.1 * sin(uv.y * 80.0 - time * 8.0);

    // Asgard beam color: bright white-blue
    vec3 beam_color = vec3(0.7, 0.85, 1.0);
    vec3 glow = beam_color * column * shimmer * intensity * 0.6;
    vec3 scan_glow = vec3(0.9, 0.95, 1.0) * scan_line * intensity;

    fragColor = vec4(scene.rgb + glow + scan_glow, 1.0);
}
"""


def create_asgard_beam_pass(ctx):
    """Create Asgard beam volumetric shader pass."""
    sp = ShaderPass(ctx, ASGARD_BEAM_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('beam_x', 0.5)
    sp.set_uniform('beam_top', 0.0)
    sp.set_uniform('beam_bottom', 1.0)
    sp.set_uniform('intensity', 0.0)
    sp.set_uniform('scan_progress', 0.0)
    return sp
