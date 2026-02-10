"""Visual effects for the space shooter: starfield, screen shake, FX helpers."""

import pygame
import math
import random


class StarField:
    """Multi-layer parallax starfield with nebula clouds and space debris."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # 3 star layers: far (slow/dim/small), mid, near (fast/bright/large)
        self.layers = []
        layer_configs = [
            {"count": 60, "speed_range": (0.2, 0.8), "size_range": (1, 1), "bright_range": (60, 120)},
            {"count": 40, "speed_range": (0.8, 2.0), "size_range": (1, 2), "bright_range": (120, 200)},
            {"count": 30, "speed_range": (2.0, 4.0), "size_range": (2, 3), "bright_range": (180, 255)},
        ]
        for cfg in layer_configs:
            layer = []
            for _ in range(cfg["count"]):
                layer.append({
                    'x': random.randint(0, screen_width),
                    'y': random.randint(0, screen_height),
                    'base_speed': random.uniform(*cfg["speed_range"]),
                    'size': random.randint(*cfg["size_range"]),
                    'brightness': random.randint(*cfg["bright_range"]),
                })
            self.layers.append(layer)

        # Depth multipliers for parallax response to player movement
        self.depth_mults = [0.02, 0.05, 0.1]

        # Nebula clouds: pre-rendered semi-transparent colored blobs
        self.nebulae = []
        nebula_colors = [
            (80, 40, 120),   # Purple
            (30, 50, 120),   # Blue
            (120, 30, 50),   # Red
        ]
        for i in range(3):
            radius = random.randint(200, 400)
            alpha = random.randint(15, 30)
            color = nebula_colors[i % len(nebula_colors)]
            # Pre-render nebula surface once
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
                'x': random.randint(0, screen_width),
                'y': random.randint(0, screen_height),
                'radius': radius,
                'surface': neb_surf,
                'vx': random.uniform(-0.1, 0.1),
                'vy': random.uniform(-0.05, 0.05),
            })

        # Space debris: tiny polygon shapes floating through
        self.debris = []
        self.debris_spawn_counter = 0

        # Speed lines (populated dynamically when player moves fast)
        self.speed_lines = []

    def update(self, player_vx=0, player_vy=0):
        """Update all star layers, nebulae, debris, and speed lines."""
        # Update star layers with parallax
        for layer_idx, layer in enumerate(self.layers):
            depth = self.depth_mults[layer_idx]
            for star in layer:
                # Base scroll + parallax response to player movement
                star['x'] -= star['base_speed'] + player_vx * depth
                star['y'] -= player_vy * depth

                # Wrap around
                if star['x'] < 0:
                    star['x'] = self.screen_width
                    star['y'] = random.randint(0, self.screen_height)
                elif star['x'] > self.screen_width:
                    star['x'] = 0
                    star['y'] = random.randint(0, self.screen_height)
                if star['y'] < 0:
                    star['y'] = self.screen_height
                elif star['y'] > self.screen_height:
                    star['y'] = 0

        # Update nebulae (slow drift, wrap around)
        for neb in self.nebulae:
            neb['x'] += neb['vx'] - player_vx * 0.01
            neb['y'] += neb['vy'] - player_vy * 0.01
            if neb['x'] < -neb['radius']:
                neb['x'] = self.screen_width + neb['radius']
            elif neb['x'] > self.screen_width + neb['radius']:
                neb['x'] = -neb['radius']
            if neb['y'] < -neb['radius']:
                neb['y'] = self.screen_height + neb['radius']
            elif neb['y'] > self.screen_height + neb['radius']:
                neb['y'] = -neb['radius']

        # Space debris spawning (1 per ~400 frames)
        self.debris_spawn_counter += 1
        if self.debris_spawn_counter >= 400:
            self.debris_spawn_counter = 0
            edge = random.choice(["top", "bottom", "left", "right"])
            size = random.randint(5, 15)
            if edge == "right":
                dx, dy = -random.uniform(0.5, 1.5), random.uniform(-0.3, 0.3)
                x, y = self.screen_width + size, random.randint(0, self.screen_height)
            elif edge == "left":
                dx, dy = random.uniform(0.5, 1.5), random.uniform(-0.3, 0.3)
                x, y = -size, random.randint(0, self.screen_height)
            elif edge == "top":
                dx, dy = random.uniform(-0.3, 0.3), random.uniform(0.5, 1.5)
                x, y = random.randint(0, self.screen_width), -size
            else:
                dx, dy = random.uniform(-0.3, 0.3), -random.uniform(0.5, 1.5)
                x, y = random.randint(0, self.screen_width), self.screen_height + size
            # Generate polygon shape
            num_pts = random.randint(4, 6)
            pts = []
            for i in range(num_pts):
                angle = (i / num_pts) * math.pi * 2
                r = size // 2 + random.randint(-size // 4, size // 4)
                pts.append((math.cos(angle) * r, math.sin(angle) * r))
            self.debris.append({
                'x': x, 'y': y, 'vx': dx, 'vy': dy,
                'size': size, 'points': pts, 'rot': 0,
                'rot_speed': random.uniform(-1, 1),
                'color': random.choice([(70, 65, 55), (50, 50, 60), (80, 70, 60)])
            })

        # Update debris
        for d in self.debris[:]:
            d['x'] += d['vx']
            d['y'] += d['vy']
            d['rot'] += d['rot_speed']
            margin = d['size'] + 20
            if (d['x'] < -margin or d['x'] > self.screen_width + margin or
                    d['y'] < -margin or d['y'] > self.screen_height + margin):
                self.debris.remove(d)

        # Speed lines when player moves fast
        player_speed = abs(player_vx) + abs(player_vy)
        self.speed_lines = [sl for sl in self.speed_lines if sl['life'] > 0]
        for sl in self.speed_lines:
            sl['life'] -= 1
            sl['x'] -= player_vx * 0.3
            sl['y'] -= player_vy * 0.3

        if player_speed > 10:
            for _ in range(2):
                self.speed_lines.append({
                    'x': random.randint(0, self.screen_width),
                    'y': random.randint(0, self.screen_height),
                    'length': random.randint(20, 60),
                    'life': random.randint(5, 15),
                    'max_life': 15,
                    'angle': math.atan2(-player_vy, -player_vx),
                })

    def draw(self, surface):
        # Draw nebulae first (background) — uses pre-rendered surfaces
        for neb in self.nebulae:
            c = neb['radius']
            surface.blit(neb['surface'], (int(neb['x']) - c, int(neb['y']) - c))

        # Draw star layers
        for layer in self.layers:
            for star in layer:
                color = (star['brightness'],) * 3
                pygame.draw.circle(surface, color, (int(star['x']), int(star['y'])), star['size'])

        # Draw debris
        for d in self.debris:
            cos_r = math.cos(math.radians(d['rot']))
            sin_r = math.sin(math.radians(d['rot']))
            rotated = []
            for px, py in d['points']:
                rx = px * cos_r - py * sin_r + d['x']
                ry = px * sin_r + py * cos_r + d['y']
                rotated.append((int(rx), int(ry)))
            if len(rotated) >= 3:
                pygame.draw.polygon(surface, d['color'], rotated)
                pygame.draw.polygon(surface, (40, 40, 40), rotated, 1)

        # Draw speed lines — draw directly (opaque, fades via brightness)
        for sl in self.speed_lines:
            brightness = int(80 * (sl['life'] / sl['max_life']))
            ex = sl['x'] + math.cos(sl['angle']) * sl['length']
            ey = sl['y'] + math.sin(sl['angle']) * sl['length']
            pygame.draw.line(surface, (brightness, brightness, min(255, brightness + 40)),
                           (int(sl['x']), int(sl['y'])), (int(ex), int(ey)), 1)


class ScreenShake:
    """Screen shake effect manager."""
    def __init__(self):
        self.timer = 0
        self.intensity = 0

    def trigger(self, intensity, duration):
        """Start or override a screen shake."""
        # Only override if new shake is stronger
        if intensity >= self.intensity or self.timer <= 0:
            self.intensity = intensity
            self.timer = duration

    def update(self):
        """Update shake timer. Returns (offset_x, offset_y)."""
        if self.timer > 0:
            self.timer -= 1
            ox = random.randint(-self.intensity, self.intensity)
            oy = random.randint(-self.intensity, self.intensity)
            return ox, oy
        self.intensity = 0
        return 0, 0
