"""Visual effects for the space shooter: starfield, screen shake, particle trails."""

import pygame
import math
import random
from collections import OrderedDict


# Cached circle sprites — avoids per-frame SRCALPHA allocation in particle draws.
_circle_cache: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()
_CIRCLE_CACHE_MAX = 192


def _get_cached_circle(size, rgb, alpha):
    """Return a cached SRCALPHA circle. Quantizes alpha to bound cache size."""
    alpha_q = (alpha >> 4) << 4
    key = (size, rgb, alpha_q)
    s = _circle_cache.get(key)
    if s is not None:
        _circle_cache.move_to_end(key)
        return s
    if len(_circle_cache) >= _CIRCLE_CACHE_MAX:
        for _ in range(32):
            _circle_cache.popitem(last=False)
    s = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*rgb, alpha_q), (size + 1, size + 1), size)
    _circle_cache[key] = s
    return s


class StarField:
    """Multi-layer parallax starfield that tiles infinitely with the camera.

    Stars are defined within a tile. The tile is drawn in a 3x3 grid offset
    by (camera.pos * depth_mult) modulo tile_size, creating seamless infinite
    scrolling in all directions.
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        # Tile size slightly larger than screen for overlap
        self.tile_w = screen_width + 200
        self.tile_h = screen_height + 200

        # 3 star layers: far (slow/dim/small), mid, near (fast/bright/large)
        self.layers = []
        layer_configs = [
            {"count": 80, "size_range": (1, 1), "bright_range": (60, 120)},
            {"count": 50, "size_range": (1, 2), "bright_range": (120, 200)},
            {"count": 35, "size_range": (2, 3), "bright_range": (180, 255)},
        ]
        for cfg in layer_configs:
            layer = []
            for _ in range(cfg["count"]):
                layer.append({
                    'tx': random.randint(0, self.tile_w),
                    'ty': random.randint(0, self.tile_h),
                    'size': random.randint(*cfg["size_range"]),
                    'brightness': random.randint(*cfg["bright_range"]),
                })
            self.layers.append(layer)

        # Depth multipliers for parallax (how much camera movement affects each layer)
        self.depth_mults = [0.1, 0.3, 0.6]

        # Nebula clouds: pre-rendered, tile at larger intervals
        self.nebulae = []
        nebula_colors = [
            (80, 40, 120),   # Purple
            (30, 50, 120),   # Blue
            (120, 30, 50),   # Red
        ]
        self.nebula_tile_w = screen_width * 2
        self.nebula_tile_h = screen_height * 2
        for i in range(4):
            radius = random.randint(200, 400)
            alpha = random.randint(15, 30)
            color = nebula_colors[i % len(nebula_colors)]
            sz = radius * 2
            neb_surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = sz // 2
            for j in range(3):
                r = radius - j * (radius // 4)
                if r <= 0:
                    continue
                a = alpha - j * 5
                if a <= 0:
                    continue
                pygame.draw.circle(neb_surf, (*color, a), (c, c), r)
            self.nebulae.append({
                'tx': random.randint(0, self.nebula_tile_w),
                'ty': random.randint(0, self.nebula_tile_h),
                'radius': radius,
                'surface': neb_surf,
            })

        # Speed lines (screen-space, respond to camera velocity)
        self.speed_lines = []

        # Camera velocity for speed line generation
        self._cam_vx = 0.0
        self._cam_vy = 0.0

    def update(self, cam_vx=0, cam_vy=0):
        """Update speed lines based on camera velocity."""
        self._cam_vx = cam_vx
        self._cam_vy = cam_vy

        # Speed lines when camera moves fast
        cam_speed = abs(cam_vx) + abs(cam_vy)
        self.speed_lines = [sl for sl in self.speed_lines if sl['life'] > 0]
        for sl in self.speed_lines:
            sl['life'] -= 1

        if cam_speed > 3:
            for _ in range(int(cam_speed * 0.3)):
                self.speed_lines.append({
                    'x': random.randint(0, self.screen_width),
                    'y': random.randint(0, self.screen_height),
                    'length': random.randint(20, int(20 + cam_speed * 5)),
                    'life': random.randint(5, 15),
                    'max_life': 15,
                    'angle': math.atan2(-cam_vy, -cam_vx),
                })

    def draw(self, surface, camera=None):
        """Draw the infinite tiling starfield."""
        cam_x = camera.x if camera else 0
        cam_y = camera.y if camera else 0

        # Draw nebulae (background, larger tile)
        for neb in self.nebulae:
            neb_depth = 0.05
            ox = -(cam_x * neb_depth) % self.nebula_tile_w
            oy = -(cam_y * neb_depth) % self.nebula_tile_h
            c = neb['radius']
            # Draw in 2x2 grid for coverage
            for gx in range(-1, 2):
                for gy in range(-1, 2):
                    nx = ox + neb['tx'] + gx * self.nebula_tile_w - c
                    ny = oy + neb['ty'] + gy * self.nebula_tile_h - c
                    # Cull if fully off screen
                    if (-c * 2 < nx < self.screen_width + c and
                            -c * 2 < ny < self.screen_height + c):
                        surface.blit(neb['surface'], (int(nx), int(ny)))

        # Draw star layers with tiling
        for layer_idx, layer in enumerate(self.layers):
            depth = self.depth_mults[layer_idx]
            # Offset based on camera position
            ox = -(cam_x * depth) % self.tile_w
            oy = -(cam_y * depth) % self.tile_h

            for star in layer:
                # Draw the star in the 3x3 tile grid
                for gx in range(-1, 2):
                    for gy in range(-1, 2):
                        sx = ox + star['tx'] + gx * self.tile_w
                        sy = oy + star['ty'] + gy * self.tile_h
                        # Only draw if on screen
                        if -3 < sx < self.screen_width + 3 and -3 < sy < self.screen_height + 3:
                            color = (star['brightness'],) * 3
                            pygame.draw.circle(surface, color, (int(sx), int(sy)), star['size'])
                            break  # Only need to draw once per star

        # Draw speed lines (screen-space)
        for sl in self.speed_lines:
            brightness = int(80 * (sl['life'] / sl['max_life']))
            ex = sl['x'] + math.cos(sl['angle']) * sl['length']
            ey = sl['y'] + math.sin(sl['angle']) * sl['length']
            pygame.draw.line(surface, (brightness, brightness, min(255, brightness + 40)),
                           (int(sl['x']), int(sl['y'])), (int(ex), int(ey)), 1)


class ScreenShake:
    """Screen shake effect manager with directional bias."""
    def __init__(self):
        self.timer = 0
        self.intensity = 0
        self.bias_x = 0.0
        self.bias_y = 0.0

    def trigger(self, intensity, duration, bias_x=0.0, bias_y=0.0):
        """Start or override a screen shake.

        bias_x/bias_y add directional emphasis (e.g. from an explosion direction).
        """
        # Only override if new shake is stronger
        if intensity >= self.intensity or self.timer <= 0:
            self.intensity = intensity
            self.timer = duration
            self.bias_x = bias_x
            self.bias_y = bias_y

    def update(self):
        """Update shake timer. Returns (offset_x, offset_y)."""
        if self.timer > 0:
            self.timer -= 1
            # Smooth decay curve
            decay = self.timer / max(self.timer + 1, 1)
            current_intensity = int(self.intensity * decay)
            if current_intensity < 1:
                current_intensity = 1
            ox = random.randint(-current_intensity, current_intensity) + int(self.bias_x * decay)
            oy = random.randint(-current_intensity, current_intensity) + int(self.bias_y * decay)
            return ox, oy
        self.intensity = 0
        self.bias_x = 0.0
        self.bias_y = 0.0
        return 0, 0


class ParticleTrail:
    """Reusable particle trail system for engine exhaust, weapon trails, etc."""

    # Global particle budget across all trails
    _global_count = 0
    _global_budget = 500

    def __init__(self, color, emit_rate=2, spread=4.0, particle_life=0.8,
                 speed=2.0, size_range=(2, 5)):
        self.color = color
        self.emit_rate = emit_rate  # Frames between emits
        self.spread = spread
        self.particle_life = particle_life
        self.speed = speed
        self.size_range = size_range
        self.particles = []
        self._emit_timer = 0

    def emit(self, x, y, direction_x=0, direction_y=0):
        """Emit particles from position, moving opposite to direction."""
        self._emit_timer += 1
        if self._emit_timer < self.emit_rate:
            return
        self._emit_timer = 0

        if ParticleTrail._global_count >= ParticleTrail._global_budget:
            return

        self.particles.append({
            'x': x + random.uniform(-self.spread, self.spread),
            'y': y + random.uniform(-self.spread, self.spread),
            'vx': -direction_x * self.speed + random.uniform(-0.5, 0.5),
            'vy': -direction_y * self.speed + random.uniform(-0.5, 0.5),
            'life': self.particle_life,
            'max_life': self.particle_life,
            'size': random.uniform(*self.size_range),
        })
        ParticleTrail._global_count += 1

    def update(self, dt=None):
        """Update all particles. dt is in seconds; defaults to 1/60 for back-compat."""
        # Default to 60 FPS step if caller hasn't been migrated yet.
        if dt is None:
            decay = 1.0 / 60.0
        else:
            decay = dt
        # In-place filter to avoid double-pass (build to_remove + reverse pop).
        write = 0
        particles = self.particles
        for read in range(len(particles)):
            p = particles[read]
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= decay
            p['size'] *= 0.97
            if p['life'] > 0:
                if write != read:
                    particles[write] = p
                write += 1
            else:
                ParticleTrail._global_count -= 1
        if write != len(particles):
            del particles[write:]

    def draw(self, surface, camera=None):
        """Draw all particles using cached circle sprites."""
        # Quantize size to limit cache pressure. Size buckets at integer steps
        # are already coarse (size = max(1, int(p['size']))), nothing extra to do.
        for p in self.particles:
            if camera:
                sx, sy = camera.world_to_screen(p['x'], p['y'])
            else:
                sx, sy = p['x'], p['y']
            # Skip if off screen
            if sx < -10 or sx > 2600 or sy < -10 or sy > 1500:
                continue
            progress = p['life'] / p['max_life']
            alpha = max(0, int(progress * 200))
            if alpha <= 0:
                continue
            size = max(1, int(p['size']))
            # Quantize r/g/b deltas to coarse buckets so cache hits often.
            r = min(255, self.color[0] + ((int(80 * progress) >> 4) << 4))
            g = min(255, self.color[1] + ((int(60 * progress) >> 4) << 4))
            b = min(255, self.color[2] + ((int(40 * progress) >> 4) << 4))
            sprite = _get_cached_circle(size, (r, g, b), alpha)
            surface.blit(sprite, (int(sx) - size - 1, int(sy) - size - 1))
