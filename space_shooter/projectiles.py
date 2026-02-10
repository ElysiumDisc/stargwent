"""Projectile classes for the space shooter."""

import pygame
import math
import random


class Projectile:
    """Base class for all projectiles."""
    def __init__(self, x, y, direction, color, speed=15, damage=15):
        self.x = x
        self.y = y
        # Support both scalar (legacy AI) and tuple (4-dir) direction
        if isinstance(direction, (int, float)):
            self.direction = (direction, 0)
        else:
            self.direction = tuple(direction)
        self.color = color
        self.speed = speed
        self.damage = damage
        self.active = True
        self.is_player_proj = True  # Set False for AI projectiles

    def update(self):
        dx, dy = self.direction
        self.x += self.speed * dx
        self.y += self.speed * dy

    def get_rect(self):
        return pygame.Rect(int(self.x) - 15, int(self.y) - 15, 30, 30)

    def draw(self, surface):
        pass


class Laser(Projectile):
    """Standard laser projectile (Goa'uld style)."""
    def __init__(self, x, y, direction, color, speed=18):
        super().__init__(x, y, direction, color, speed, damage=12)
        dx, dy = self.direction
        self.is_vertical = (abs(dy) > abs(dx))
        if self.is_vertical:
            self.width = 6
            self.height = 35
        else:
            self.width = 35
            self.height = 6

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.width // 2, int(self.y) - self.height // 2,
                           self.width, self.height)

    def draw(self, surface):
        # Glowing laser effect
        glow_surf = pygame.Surface((self.width + 10, self.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*self.color[:3], 100), (5, 5, self.width, self.height))
        pygame.draw.rect(glow_surf, self.color, (5, 5, self.width, self.height))
        # Bright core
        if self.is_vertical:
            pygame.draw.rect(glow_surf, (255, 255, 255),
                             (5 + self.width // 4, 5, self.width // 2, self.height))
        else:
            pygame.draw.rect(glow_surf, (255, 255, 255),
                             (5, 5 + self.height // 4, self.width, self.height // 2))
        surface.blit(glow_surf, (int(self.x) - self.width // 2 - 5,
                                 int(self.y) - self.height // 2 - 5))


class Missile(Projectile):
    """Tau'ri missile - slower but high damage with trail."""
    def __init__(self, x, y, direction, color, speed=10):
        super().__init__(x, y, direction, color, speed, damage=25)
        dx, dy = self.direction
        self.is_vertical = (abs(dy) > abs(dx))
        if self.is_vertical:
            self.width = 8
            self.height = 20
        else:
            self.width = 20
            self.height = 8
        self.trail = []
        self.wobble = 0

    def update(self):
        # Add trail particle
        self.trail.append({'x': self.x, 'y': self.y, 'alpha': 200})
        if len(self.trail) > 15:
            self.trail.pop(0)

        # Update trail
        for t in self.trail:
            t['alpha'] -= 15
        self.trail = [t for t in self.trail if t['alpha'] > 0]

        # Slight wobble perpendicular to travel direction
        self.wobble += 0.3
        wobble_val = math.sin(self.wobble) * 0.5
        if self.is_vertical:
            self.x += wobble_val
        else:
            self.y += wobble_val

        super().update()

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.width // 2, int(self.y) - self.height // 2,
                          self.width, self.height)

    def draw(self, surface):
        # Draw trail (engine exhaust)
        for t in self.trail:
            alpha = max(0, t['alpha'])
            trail_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (255, 150, 50, alpha), (6, 6), 4)
            pygame.draw.circle(trail_surf, (255, 255, 100, alpha // 2), (6, 6), 2)
            surface.blit(trail_surf, (int(t['x']) - 6, int(t['y']) - 6))

        # Draw missile body
        missile_surf = pygame.Surface((self.width + 10, self.height + 10), pygame.SRCALPHA)
        pygame.draw.ellipse(missile_surf, self.color, (5, 5, self.width, self.height))
        # Nose cone points in travel direction
        dx, dy = self.direction
        cx = 5 + self.width // 2
        cy = 5 + self.height // 2
        if self.is_vertical:
            nose_y = 5 + self.height if dy == 1 else 0
            pygame.draw.polygon(missile_surf, (200, 200, 200), [
                (cx, nose_y),
                (5, nose_y - 5 * dy),
                (5 + self.width, nose_y - 5 * dy)
            ])
        else:
            nose_x = 5 + self.width if dx == 1 else 0
            pygame.draw.polygon(missile_surf, (200, 200, 200), [
                (nose_x, cy),
                (nose_x - 5 * dx, 5),
                (nose_x - 5 * dx, 5 + self.height)
            ])
        surface.blit(missile_surf, (int(self.x) - self.width // 2 - 5, int(self.y) - self.height // 2 - 5))


class ContinuousBeam:
    """Asgard continuous beam weapon - deals damage over time in any direction."""
    def __init__(self, ship, direction, color, screen_width, screen_height=1080):
        self.ship = ship
        # Support both scalar (legacy AI) and tuple direction
        if isinstance(direction, (int, float)):
            self.direction = (direction, 0)
        else:
            self.direction = tuple(direction)
        self.color = color
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.active = True
        self.damage_per_frame = 0.4
        self.pulse = 0
        # Default length: full screen
        dx, dy = self.direction
        self.current_length = screen_height if (abs(dy) > abs(dx)) else screen_width

    def update(self):
        self.pulse += 0.2

    def set_length(self, length):
        """Set the current beam length based on collision."""
        self.current_length = length

    def get_start_pos(self):
        dx, dy = self.direction
        if dx == 1:
            return (self.ship.x + self.ship.width, self.ship.y)
        elif dx == -1:
            return (self.ship.x, self.ship.y)
        elif dy == -1:
            return (self.ship.x + self.ship.width // 2, self.ship.y - self.ship.height // 2)
        else:  # dy == 1
            return (self.ship.x + self.ship.width // 2, self.ship.y + self.ship.height // 2)

    def get_end_pos(self):
        sx, sy = self.get_start_pos()
        dx, dy = self.direction
        return (sx + dx * self.current_length, sy + dy * self.current_length)

    def get_rect(self):
        start_x, start_y = self.get_start_pos()
        dx, dy = self.direction
        if abs(dx) > abs(dy):  # Horizontal
            if dx == 1:
                return pygame.Rect(int(start_x), int(start_y) - 10, self.current_length, 20)
            else:
                return pygame.Rect(int(start_x) - self.current_length, int(start_y) - 10, self.current_length, 20)
        else:  # Vertical
            if dy == 1:
                return pygame.Rect(int(start_x) - 10, int(start_y), 20, self.current_length)
            else:
                return pygame.Rect(int(start_x) - 10, int(start_y) - self.current_length, 20, self.current_length)

    def draw(self, surface):
        sx, sy = self.get_start_pos()
        ex, ey = self.get_end_pos()

        pulse_width = 8 + int(math.sin(self.pulse) * 4)

        # Draw wide faint line (simulated glow)
        glow_color = (max(0, self.color[0]-50), max(0, self.color[1]-50), max(0, self.color[2]-50))
        pygame.draw.line(surface, glow_color, (sx, sy), (ex, ey), pulse_width + 12)
        # Draw main color
        pygame.draw.line(surface, self.color, (sx, sy), (ex, ey), pulse_width)
        # Draw white core
        pygame.draw.line(surface, (255, 255, 255), (sx, sy), (ex, ey), max(1, pulse_width // 2))


class EnergyBall(Projectile):
    """Lucian Alliance energy ball - medium speed, splash potential."""
    def __init__(self, x, y, direction, color, speed=12):
        super().__init__(x, y, direction, color, speed, damage=18)
        self.radius = 18
        self.pulse = random.uniform(0, math.pi * 2)
        self.particles = []

    def update(self):
        super().update()
        self.pulse += 0.15

        # Spawn trailing particles
        if random.random() < 0.4:
            self.particles.append({
                'x': self.x + random.uniform(-5, 5),
                'y': self.y + random.uniform(-5, 5),
                'alpha': 150,
                'size': random.randint(3, 6)
            })

        # Update particles — trail opposite to travel direction
        dx, dy = self.direction
        for p in self.particles:
            p['alpha'] -= 10
            p['x'] -= dx * 2
            p['y'] -= dy * 2
        self.particles = [p for p in self.particles if p['alpha'] > 0]

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.radius, int(self.y) - self.radius,
                          self.radius * 2, self.radius * 2)

    def draw(self, surface):
        # Draw particles
        for p in self.particles:
            p_surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*self.color[:3], int(p['alpha'])),
                             (p['size'], p['size']), p['size'])
            surface.blit(p_surf, (int(p['x']) - p['size'], int(p['y']) - p['size']))

        # Pulsing size
        pulse_radius = self.radius + int(math.sin(self.pulse) * 4)

        # Outer glow
        ball_surf = pygame.Surface((pulse_radius * 3, pulse_radius * 3), pygame.SRCALPHA)
        center = pulse_radius * 3 // 2
        pygame.draw.circle(ball_surf, (*self.color[:3], 50), (center, center), pulse_radius + 8)
        pygame.draw.circle(ball_surf, (*self.color[:3], 100), (center, center), pulse_radius + 4)
        pygame.draw.circle(ball_surf, self.color, (center, center), pulse_radius)
        # Bright core
        pygame.draw.circle(ball_surf, (255, 200, 255), (center, center), pulse_radius // 2)

        surface.blit(ball_surf, (int(self.x) - center, int(self.y) - center))


class JaffaStaffBlast(Projectile):
    """Jaffa staff weapon blast - orange energy bolt."""
    def __init__(self, x, y, direction, color, speed=14):
        super().__init__(x, y, direction, color, speed, damage=13)
        self.width = 25
        self.height = 12
        self.glow_pulse = 0

    def update(self):
        super().update()
        self.glow_pulse += 0.25

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.width // 2, int(self.y) - self.height // 2,
                          self.width, self.height)

    def draw(self, surface):
        pulse = abs(math.sin(self.glow_pulse))
        glow_size = int(8 + pulse * 4)

        blast_surf = pygame.Surface((self.width + glow_size * 2, self.height + glow_size * 2), pygame.SRCALPHA)
        center_x = self.width // 2 + glow_size
        center_y = self.height // 2 + glow_size

        # Outer glow
        pygame.draw.ellipse(blast_surf, (*self.color[:3], 80),
                           (0, 0, self.width + glow_size * 2, self.height + glow_size * 2))
        # Main blast
        pygame.draw.ellipse(blast_surf, self.color,
                           (glow_size // 2, glow_size // 2, self.width + glow_size, self.height + glow_size))
        # Hot core
        pygame.draw.ellipse(blast_surf, (255, 255, 200),
                           (glow_size, glow_size, self.width, self.height))

        surface.blit(blast_surf, (int(self.x) - center_x, int(self.y) - center_y))


class ChainLightning:
    """Chain lightning projectile that jumps between enemies."""
    def __init__(self, x, y, targets, damage, max_chains=1):
        self.x = x
        self.y = y
        self.targets = targets  # List of (x, y) positions for chain points
        self.damage = damage
        self.max_chains = max_chains
        self.active = True
        self.timer = 0
        self.duration = 12  # frames visible
        self.is_player_proj = True
        # Generate jagged segments between chain points
        self.segments = []
        self._generate_segments()

    def _generate_segments(self):
        """Generate jagged lightning segments between chain points."""
        all_points = [(self.x, self.y)] + self.targets
        for i in range(len(all_points) - 1):
            sx, sy = all_points[i]
            ex, ey = all_points[i + 1]
            segment = [(sx, sy)]
            num_jags = random.randint(4, 8)
            for j in range(1, num_jags):
                t = j / num_jags
                mx = sx + (ex - sx) * t + random.uniform(-15, 15)
                my = sy + (ey - sy) * t + random.uniform(-15, 15)
                segment.append((mx, my))
            segment.append((ex, ey))
            self.segments.append(segment)

    def update(self):
        self.timer += 1
        if self.timer >= self.duration:
            self.active = False

    def draw(self, surface):
        if not self.active:
            return
        alpha = max(0, int(255 * (1 - self.timer / self.duration)))
        for segment in self.segments:
            for i in range(len(segment) - 1):
                # Outer glow
                pygame.draw.line(surface, (100, 150, 255),
                               (int(segment[i][0]), int(segment[i][1])),
                               (int(segment[i+1][0]), int(segment[i+1][1])), 4)
                # Bright core
                pygame.draw.line(surface, (200, 220, 255),
                               (int(segment[i][0]), int(segment[i][1])),
                               (int(segment[i+1][0]), int(segment[i+1][1])), 2)
                # White center
                pygame.draw.line(surface, (255, 255, 255),
                               (int(segment[i][0]), int(segment[i][1])),
                               (int(segment[i+1][0]), int(segment[i+1][1])), 1)
