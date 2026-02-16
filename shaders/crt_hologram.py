"""
CRT/Hologram Post-Processing Effect for MALP Feed Panel

Region-specific effect applied only to the history panel area:
- Scanlines
- Static noise
- Subtle green tint (MALP footage aesthetic)
- Flicker

Panel rect passed as uniform from frame_renderer.py.
"""

from gpu_renderer import ShaderPass

CRT_HOLOGRAM_FRAG = """
#version 330
uniform sampler2D tex;
uniform float time;
uniform vec4 panel_rect;  // x, y, width, height in UV space (0-1)
uniform float scanline_intensity;
uniform float noise_intensity;
uniform float flicker_speed;
in vec2 uv;
out vec4 fragColor;

// Pseudo-random noise
float random(vec2 st) {
    return fract(sin(dot(st, vec2(12.9898, 78.233))) * 43758.5453123);
}

void main() {
    vec4 color = texture(tex, uv);

    // Check if pixel is within the panel region
    vec2 panel_min = panel_rect.xy;
    vec2 panel_max = panel_rect.xy + panel_rect.zw;

    if (uv.x >= panel_min.x && uv.x <= panel_max.x &&
        uv.y >= panel_min.y && uv.y <= panel_max.y) {

        // Local UV within panel
        vec2 local_uv = (uv - panel_min) / panel_rect.zw;

        // Scanlines
        float scanline = sin(local_uv.y * 800.0) * 0.5 + 0.5;
        scanline = mix(1.0, scanline, scanline_intensity);
        color.rgb *= scanline;

        // Static noise
        float noise = random(uv + vec2(time * 7.0, time * 3.0));
        color.rgb += vec3(noise * noise_intensity);

        // Subtle green tint (MALP footage)
        color.rgb = mix(color.rgb, color.rgb * vec3(0.8, 1.1, 0.85), 0.3);

        // Flicker
        float flicker = 0.95 + 0.05 * sin(time * flicker_speed);
        color.rgb *= flicker;

        // Slight chromatic aberration
        float ca_offset = 0.001;
        float r = texture(tex, uv + vec2(ca_offset, 0.0)).r;
        float b = texture(tex, uv - vec2(ca_offset, 0.0)).b;
        color.r = mix(color.r, r, 0.3);
        color.b = mix(color.b, b, 0.3);
    }

    fragColor = color;
}
"""


def create_crt_pass(ctx):
    """Create CRT/hologram shader pass."""
    sp = ShaderPass(ctx, CRT_HOLOGRAM_FRAG)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('panel_rect', (0.0, 0.0, 0.0, 0.0))  # Set by frame_renderer
    sp.set_uniform('scanline_intensity', 0.15)
    sp.set_uniform('noise_intensity', 0.03)
    sp.set_uniform('flicker_speed', 12.0)
    return sp
