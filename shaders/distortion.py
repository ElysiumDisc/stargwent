"""
Screen-Space Distortion Post-Processing Effect

UV displacement shader supporting up to 8 concurrent distortion points.
Each point creates a ring-shaped shockwave distortion pattern.
Driven by animation classes via get_gpu_distortion_params().
"""

from gpu_renderer import ShaderPass

DISTORTION_FRAG = """
#version 330
uniform sampler2D tex;
uniform int num_points;
uniform vec2 centers[8];      // UV-space center of each distortion
uniform float strengths[8];   // Distortion strength per point
uniform float radii[8];       // Distortion radius per point
uniform vec2 screen_size;
in vec2 uv;
out vec4 fragColor;

void main() {
    vec2 displaced_uv = uv;

    for (int i = 0; i < num_points && i < 8; i++) {
        vec2 to_center = uv - centers[i];
        // Correct aspect ratio
        to_center.x *= screen_size.x / screen_size.y;
        float dist = length(to_center);
        float radius = radii[i];

        // Ring-shaped shockwave: peak distortion at the wavefront
        float ring_dist = abs(dist - radius);
        float ring_width = radius * 0.15;
        float ring_factor = 1.0 - smoothstep(0.0, ring_width, ring_dist);

        // Displacement direction (radial, away from center)
        vec2 dir = normalize(to_center + vec2(0.0001));
        dir.x /= screen_size.x / screen_size.y;  // Undo aspect correction

        displaced_uv += dir * ring_factor * strengths[i] * 0.05;
    }

    // Clamp UV to prevent sampling outside texture
    displaced_uv = clamp(displaced_uv, vec2(0.0), vec2(1.0));
    fragColor = texture(tex, displaced_uv);
}
"""


class DistortionPass(ShaderPass):
    """Screen-space distortion with multiple shockwave points."""

    def __init__(self, ctx):
        super().__init__(ctx, DISTORTION_FRAG)
        self._points = []  # list of (center_uv, strength, radius)
        self.set_uniform('num_points', 0)
        self.set_uniform('screen_size', (2560.0, 1440.0))

    def set_distortion_points(self, points, screen_size=None):
        """Set active distortion points.

        Args:
            points: list of dicts with 'center' (x,y in UV 0-1), 'strength', 'radius'
            screen_size: (width, height) tuple
        """
        self._points = points[:8]
        self.set_uniform('num_points', len(self._points))
        if screen_size:
            self.set_uniform('screen_size', (float(screen_size[0]), float(screen_size[1])))

        # Pack arrays
        centers = [(0.0, 0.0)] * 8
        strengths = [0.0] * 8
        radii = [0.0] * 8
        for i, pt in enumerate(self._points):
            centers[i] = pt['center']
            strengths[i] = pt['strength']
            radii[i] = pt['radius']

        # Set array uniforms individually
        for i in range(8):
            self.set_uniform(f'centers[{i}]', centers[i])
            self.set_uniform(f'strengths[{i}]', strengths[i])
            self.set_uniform(f'radii[{i}]', radii[i])

    def clear_points(self):
        self._points = []
        self.set_uniform('num_points', 0)


def create_distortion_pass(ctx):
    """Create distortion shader pass."""
    return DistortionPass(ctx)
