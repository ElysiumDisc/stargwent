"""
Replicator Swarm GPU Shader Effect

Metallic shimmer highlight + chromatic aberration + ripple distortion
centered on the swarm. Driven by ReplicatorCrawlEffect.get_gpu_params().
"""

from gpu_renderer import ShaderPass

REPLICATOR_SWARM_FRAG = """
#version 330
uniform sampler2D tex;
uniform float time;
uniform vec2 swarm_center;   // UV-space center of the swarm
uniform float intensity;     // 0.0 = off, 1.0 = full
uniform float density;       // 0.0-1.0 swarm density factor
uniform vec2 screen_size;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec2 to_center = uv - swarm_center;
    // Correct for aspect ratio
    to_center.x *= screen_size.x / screen_size.y;
    float dist = length(to_center);

    // -- Ripple distortion from swarm center --
    float ripple_freq = 30.0;
    float ripple_speed = 3.0;
    float ripple = sin(dist * ripple_freq - time * ripple_speed) * 0.5 + 0.5;
    float ripple_falloff = exp(-dist * 4.0) * intensity * 0.3;
    vec2 ripple_dir = normalize(to_center + vec2(0.0001));
    ripple_dir.x /= screen_size.x / screen_size.y;
    vec2 distorted_uv = uv + ripple_dir * ripple * ripple_falloff * 0.008;

    // -- Chromatic aberration near swarm center --
    float chroma_strength = exp(-dist * 3.5) * intensity * density * 0.004;
    vec2 chroma_dir = normalize(to_center + vec2(0.0001));
    chroma_dir.x /= screen_size.x / screen_size.y;

    float r = texture(tex, distorted_uv + chroma_dir * chroma_strength).r;
    float g = texture(tex, distorted_uv).g;
    float b = texture(tex, distorted_uv - chroma_dir * chroma_strength).b;
    float a = texture(tex, distorted_uv).a;

    vec3 color = vec3(r, g, b);

    // -- Metallic shimmer bloom overlay --
    // Pulsing highlight that sweeps across the swarm area
    float sweep = sin(time * 2.0 + dist * 8.0) * 0.5 + 0.5;
    float bloom_falloff = exp(-dist * 3.0) * intensity * 0.15;
    vec3 metallic = vec3(0.75, 0.75, 0.85);  // Silver/chrome tint
    color += metallic * sweep * bloom_falloff;

    fragColor = vec4(color, a);
}
"""


def create_replicator_swarm_pass(ctx):
    """Create the replicator swarm shader pass."""
    sp = ShaderPass(ctx, REPLICATOR_SWARM_FRAG)
    sp.set_uniform('swarm_center', (0.5, 0.5))
    sp.set_uniform('intensity', 0.0)
    sp.set_uniform('density', 0.0)
    sp.set_uniform('time', 0.0)
    sp.set_uniform('screen_size', (2560.0, 1440.0))
    return sp
