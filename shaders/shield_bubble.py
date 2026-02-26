"""
Shield Bubble Post-Processing Effect

Localized energy bubble with hexagonal grid pattern, subtle refraction,
and pulsing rim glow.  Driven by the space shooter when the player has
shields > 0.  Faction-tinted via the shield_tint uniform.

Uniforms (set from game code):
  shield_center  – vec2 in UV space (0-1)
  shield_radius  – float in UV space
  shield_pct     – float 0-1 (shield health fraction)
  time           – float (seconds)
  screen_size    – vec2 (pixels)
  shield_tint    – vec3 (faction color, 0-1 range)
"""

from gpu_renderer import ShaderPass
from shaders import glsl_version_header

# Faction → shield tint (0-1 normalised RGB)
SHIELD_TINTS = {
    "tau'ri":          (0.31, 0.75, 1.0),    # Blue
    "tauri":           (0.31, 0.75, 1.0),
    "asgard":          (0.31, 0.75, 1.0),    # Blue (same family)
    "goa'uld":         (1.0, 0.63, 0.2),     # Orange
    "goauld":          (1.0, 0.63, 0.2),
    "jaffa rebellion": (1.0, 0.55, 0.2),     # Orange
    "jaffa_rebellion": (1.0, 0.55, 0.2),
    "lucian alliance": (1.0, 0.55, 0.28),    # Orange
    "lucian_alliance": (1.0, 0.55, 0.28),
}

# Default blue tint (fallback)
DEFAULT_SHIELD_TINT = (0.31, 0.75, 1.0)

SHIELD_BUBBLE_FRAG = glsl_version_header() + """
uniform sampler2D tex;
uniform vec2  shield_center;   // UV-space center of the bubble
uniform float shield_radius;   // UV-space radius
uniform float shield_pct;      // 0-1 shield health
uniform float time;
uniform vec2  screen_size;
uniform vec3  shield_tint;     // Faction color tint (0-1 RGB)
in  vec2 uv;
out vec4 fragColor;

// ---------- hex grid helper ----------
// Returns distance to nearest hex edge (0 = on edge, ~0.5 = cell center)
float hex_dist(vec2 p) {
    p = abs(p);
    return max(dot(p, vec2(1.0, 1.732) * 0.5), p.x);
}

vec2 hex_uv(vec2 p, float scale) {
    vec2 a = mod(p, vec2(1.0, 1.732)) - vec2(0.5, 0.866);
    vec2 b = mod(p + vec2(0.5, 0.866), vec2(1.0, 1.732)) - vec2(0.5, 0.866);
    return (length(a) < length(b)) ? a : b;
}

void main() {
    // Aspect-corrected distance from bubble center
    vec2 delta = uv - shield_center;
    delta.x *= screen_size.x / screen_size.y;
    float dist = length(delta);

    // Normalised 0-1 inside the bubble
    float norm = dist / max(shield_radius * (screen_size.x / screen_size.y), 0.001);

    if (norm > 1.3) {
        // Outside influence range — passthrough
        fragColor = texture(tex, uv);
        return;
    }

    // Derive bright/dim variants from the faction tint
    vec3 tint_dim  = shield_tint * 0.65;
    vec3 tint_bright = min(shield_tint * 1.3, vec3(1.0));

    // ---- Subtle refraction inside the bubble ----
    vec2 refract_uv = uv;
    if (norm < 1.0) {
        vec2 dir = normalize(delta + vec2(0.0001));
        float refract_strength = 0.003 * shield_pct * (1.0 - norm);
        float wobble = sin(time * 3.0 + norm * 12.0) * 0.4 + 0.6;
        refract_uv += dir * refract_strength * wobble;
        refract_uv = clamp(refract_uv, vec2(0.0), vec2(1.0));
    }

    vec4 color = texture(tex, refract_uv);

    // ---- Hexagonal energy grid on the bubble surface ----
    if (norm < 1.05 && norm > 0.55) {
        // Map to hex grid coordinates — scale & rotate slowly
        float hex_scale = 28.0;
        float angle = time * 0.15;
        vec2 rot_delta = vec2(
            delta.x * cos(angle) - delta.y * sin(angle),
            delta.x * sin(angle) + delta.y * cos(angle)
        );
        vec2 hp = rot_delta * hex_scale;
        vec2 hc = hex_uv(hp, 1.0);
        float edge = smoothstep(0.38, 0.42, hex_dist(hc));

        // Hex grid visible only near the shell (fade toward center)
        float shell = smoothstep(0.55, 0.75, norm) * smoothstep(1.05, 0.9, norm);
        float grid_alpha = (1.0 - edge) * shell * shield_pct * 0.35;

        // Hex color — faction-tinted energy
        vec3 hex_color = mix(tint_dim, tint_bright,
                             sin(time * 2.0 + norm * 6.0) * 0.5 + 0.5);
        color.rgb = mix(color.rgb, hex_color, grid_alpha);
    }

    // ---- Pulsing energy rim at the bubble edge ----
    float rim_dist = abs(norm - 1.0);
    float pulse = sin(time * 4.0) * 0.15 + 0.85;
    float rim = smoothstep(0.12, 0.0, rim_dist) * shield_pct * pulse;
    vec3 rim_color = mix(shield_tint * 0.85, tint_bright, pulse);
    color.rgb += rim_color * rim * 0.45;

    // ---- Faint inner glow ----
    if (norm < 1.0) {
        float inner = (1.0 - norm) * shield_pct * 0.06;
        color.rgb += shield_tint * 0.7 * inner;
    }

    fragColor = color;
}
"""


class ShieldBubblePass(ShaderPass):
    """Localized shield bubble energy effect."""

    def __init__(self, ctx):
        super().__init__(ctx, SHIELD_BUBBLE_FRAG)
        # Safe defaults (effect invisible until driven)
        self.set_uniform('shield_center', (0.5, 0.5))
        self.set_uniform('shield_radius', 0.0)
        self.set_uniform('shield_pct', 0.0)
        self.set_uniform('time', 0.0)
        self.set_uniform('screen_size', (2560.0, 1440.0))
        self.set_uniform('shield_tint', DEFAULT_SHIELD_TINT)

    def update_shield(self, center_uv, radius_uv, pct, t,
                      screen_size=None, tint=None):
        """Convenience setter called each frame from game code."""
        self.set_uniform('shield_center', center_uv)
        self.set_uniform('shield_radius', radius_uv)
        self.set_uniform('shield_pct', pct)
        self.set_uniform('time', t)
        if screen_size:
            self.set_uniform('screen_size',
                             (float(screen_size[0]), float(screen_size[1])))
        if tint:
            self.set_uniform('shield_tint', tint)


def create_shield_bubble_pass(ctx):
    """Create the shield bubble shader pass."""
    return ShieldBubblePass(ctx)
