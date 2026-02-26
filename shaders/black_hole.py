"""
Black Hole Post-Processing Effect

Gravitational lensing distortion, swirling accretion disk, dark event horizon,
and bright rim glow.  Driven by the space shooter when a Sun enters its
WORMHOLE or CLOSING phase.

Uniforms (set from game code):
  tex          – sampler2D scene texture
  time         – float (seconds)
  screen_size  – vec2 (pixels)
  hole_center  – vec2 in UV space (0-1)
  hole_radius  – float in UV space (event horizon radius)
  intensity    – float 0-1 (fade in/out during phase transitions)
"""

from gpu_renderer import ShaderPass
from shaders import glsl_version_header

BLACK_HOLE_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform float time;
uniform vec2  screen_size;
uniform vec2  hole_center;
uniform float hole_radius;
uniform float intensity;

in  vec2 uv;
out vec4 fragColor;

// ---- simple hash / noise helpers ----
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
        p *= 2.1;
        a *= 0.5;
    }
    return v;
}

void main() {
    if (intensity < 0.001) {
        fragColor = texture(tex, uv);
        return;
    }

    // Aspect-corrected delta from black hole center
    vec2 delta = uv - hole_center;
    float aspect = screen_size.x / screen_size.y;
    delta.x *= aspect;
    float dist = length(delta);

    // Normalised distance (1.0 = event horizon edge)
    float hr = max(hole_radius * aspect, 0.001);
    float norm = dist / hr;

    // Beyond influence range — passthrough
    if (norm > 6.0) {
        fragColor = texture(tex, uv);
        return;
    }

    // ---- Gravitational lensing (UV displacement) ----
    vec2 dir = (dist > 0.0001) ? normalize(delta) : vec2(0.0);
    // Displacement strength: inverse-square falloff, capped near center
    float lensing_strength = intensity * hr * 0.8 / max(norm * norm, 0.15);
    // Pull UVs toward the black hole center
    vec2 displaced_uv = uv + dir * lensing_strength * 0.15;
    // Spiral twist: rotate displacement slightly for swirl feel
    float twist = intensity * 0.3 / max(norm, 0.3);
    float ca = cos(twist);
    float sa = sin(twist);
    vec2 twist_delta = displaced_uv - hole_center;
    displaced_uv = hole_center + vec2(
        twist_delta.x * ca - twist_delta.y * sa,
        twist_delta.x * sa + twist_delta.y * ca
    );
    displaced_uv = clamp(displaced_uv, vec2(0.0), vec2(1.0));

    vec4 color = texture(tex, displaced_uv);

    // ---- Event horizon (dark void at center) ----
    float core_edge = smoothstep(1.1, 0.7, norm);
    color.rgb *= 1.0 - core_edge * intensity;

    // ---- Accretion disk (swirling ring around event horizon) ----
    float disk_inner = 0.9;
    float disk_outer = 3.0;
    if (norm > disk_inner && norm < disk_outer) {
        // Polar angle for rotation
        float angle = atan(delta.y, delta.x);
        // Animated rotation
        float rot_angle = angle + time * 1.5 - norm * 2.0;

        // Noise-based turbulence on the disk
        vec2 disk_p = vec2(rot_angle * 2.0, norm * 4.0);
        float turb = fbm(disk_p + time * 0.3);

        // Disk brightness: peaks near event horizon, fades outward
        float disk_profile = smoothstep(disk_inner, 1.2, norm)
                           * smoothstep(disk_outer, 1.8, norm);
        disk_profile *= (0.6 + 0.4 * turb);

        // Swirling arm pattern
        float arms = sin(rot_angle * 3.0 + turb * 4.0) * 0.5 + 0.5;
        disk_profile *= (0.5 + 0.5 * arms);

        // Color: blue-purple with bright white-blue inner edge
        vec3 disk_inner_color = vec3(0.7, 0.8, 1.0);   // white-blue
        vec3 disk_outer_color = vec3(0.4, 0.2, 0.8);   // purple
        float color_t = smoothstep(disk_inner, disk_outer, norm);
        vec3 disk_color = mix(disk_inner_color, disk_outer_color, color_t);

        // Bright hotspots
        float hotspot = pow(turb, 3.0) * 2.0;
        disk_color += vec3(0.3, 0.3, 0.5) * hotspot;

        color.rgb += disk_color * disk_profile * intensity * 0.7;
    }

    // ---- Glow rim around event horizon boundary ----
    float rim_dist = abs(norm - 1.0);
    float rim = exp(-rim_dist * 8.0) * intensity;
    // Pulsing rim
    float rim_pulse = 0.85 + 0.15 * sin(time * 3.0);
    vec3 rim_color = vec3(0.5, 0.6, 1.0);  // blue-white
    color.rgb += rim_color * rim * rim_pulse * 0.9;

    // ---- Subtle outer glow (very faint blue haze) ----
    float outer_glow = exp(-norm * 1.5) * intensity * 0.15;
    color.rgb += vec3(0.3, 0.3, 0.8) * outer_glow;

    fragColor = color;
}
"""


class BlackHolePass(ShaderPass):
    """Black hole gravitational lensing and accretion disk effect."""

    def __init__(self, ctx):
        super().__init__(ctx, BLACK_HOLE_FRAG)
        # Safe defaults (effect invisible until driven)
        self.set_uniform('hole_center', (0.5, 0.5))
        self.set_uniform('hole_radius', 0.0)
        self.set_uniform('intensity', 0.0)
        self.set_uniform('time', 0.0)
        self.set_uniform('screen_size', (1920.0, 1080.0))

    def update_black_hole(self, center_uv, radius_uv, intensity, t,
                          screen_size=None):
        """Convenience setter called each frame from game code."""
        self.set_uniform('hole_center', center_uv)
        self.set_uniform('hole_radius', radius_uv)
        self.set_uniform('intensity', float(intensity))
        self.set_uniform('time', float(t))
        if screen_size:
            self.set_uniform('screen_size',
                             (float(screen_size[0]), float(screen_size[1])))


def create_black_hole_pass(ctx):
    """Create the black hole shader pass."""
    return BlackHolePass(ctx)
