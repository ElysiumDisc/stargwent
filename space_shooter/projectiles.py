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

    def draw(self, surface, camera=None):
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

    def draw(self, surface, camera=None):
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y
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
        surface.blit(glow_surf, (int(sx) - self.width // 2 - 5,
                                 int(sy) - self.height // 2 - 5))


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

    def draw(self, surface, camera=None):
        # Draw trail (engine exhaust)
        for t in self.trail:
            if camera:
                tx, ty = camera.world_to_screen(t['x'], t['y'])
            else:
                tx, ty = t['x'], t['y']
            alpha = max(0, t['alpha'])
            trail_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (255, 150, 50, alpha), (6, 6), 4)
            pygame.draw.circle(trail_surf, (255, 255, 100, alpha // 2), (6, 6), 2)
            surface.blit(trail_surf, (int(tx) - 6, int(ty) - 6))

        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

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
        surface.blit(missile_surf, (int(sx) - self.width // 2 - 5, int(sy) - self.height // 2 - 5))


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
        self.damage_per_frame = 0.55
        self.pulse = 0
        # Max beam range (infinite world — don't go to screen edge)
        self.max_range = 2000
        self.current_length = self.max_range
        self.width_mult = 1.0  # Mastery: Overcharged Beam sets to 1.5

    def update(self):
        self.pulse += 0.2

    def set_length(self, length):
        """Set the current beam length based on collision."""
        self.current_length = min(length, self.max_range)

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

    def draw(self, surface, camera=None):
        sx, sy = self.get_start_pos()
        ex, ey = self.get_end_pos()

        if camera:
            sx, sy = camera.world_to_screen(sx, sy)
            ex, ey = camera.world_to_screen(ex, ey)

        base_pw = 8 + int(math.sin(self.pulse) * 4)
        pulse_width = int(base_pw * self.width_mult)

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

    def draw(self, surface, camera=None):
        # Draw particles
        for p in self.particles:
            if camera:
                px, py = camera.world_to_screen(p['x'], p['y'])
            else:
                px, py = p['x'], p['y']
            p_surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*self.color[:3], int(p['alpha'])),
                             (p['size'], p['size']), p['size'])
            surface.blit(p_surf, (int(px) - p['size'], int(py) - p['size']))

        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

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

        surface.blit(ball_surf, (int(sx) - center, int(sy) - center))


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

    def draw(self, surface, camera=None):
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

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

        surface.blit(blast_surf, (int(sx) - center_x, int(sy) - center_y))


class RailgunShot(Projectile):
    """Tau'ri railgun — fast piercing shot that passes through enemies."""
    def __init__(self, x, y, direction, color, speed=28):
        super().__init__(x, y, direction, color, speed, damage=50)
        dx, dy = self.direction
        self.is_vertical = (abs(dy) > abs(dx))
        if self.is_vertical:
            self.width = 4
            self.height = 60
        else:
            self.width = 60
            self.height = 4
        self.trail = []
        self.piercing = True  # Flag for collision system to not remove on hit

    def update(self):
        self.trail.append({'x': self.x, 'y': self.y, 'alpha': 255})
        if len(self.trail) > 25:
            self.trail.pop(0)
        for t in self.trail:
            t['alpha'] -= 12
        self.trail = [t for t in self.trail if t['alpha'] > 0]
        super().update()

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.width // 2, int(self.y) - self.height // 2,
                          self.width, self.height)

    def draw(self, surface, camera=None):
        # Draw trail
        for t in self.trail:
            if camera:
                tx, ty = camera.world_to_screen(t['x'], t['y'])
            else:
                tx, ty = t['x'], t['y']
            alpha = max(0, t['alpha'])
            trail_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (100, 200, 255, alpha), (4, 4), 3)
            surface.blit(trail_surf, (int(tx) - 4, int(ty) - 4))

        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

        # Bright blue-white bolt
        bolt_surf = pygame.Surface((self.width + 12, self.height + 12), pygame.SRCALPHA)
        cx = self.width // 2 + 6
        cy = self.height // 2 + 6
        # Outer glow
        pygame.draw.rect(bolt_surf, (80, 160, 255, 100),
                        (6 - 3, 6 - 3, self.width + 6, self.height + 6))
        # Core
        pygame.draw.rect(bolt_surf, (150, 220, 255), (6, 6, self.width, self.height))
        # White center
        if self.is_vertical:
            pygame.draw.rect(bolt_surf, (255, 255, 255),
                           (6 + self.width // 4, 6, self.width // 2, self.height))
        else:
            pygame.draw.rect(bolt_surf, (255, 255, 255),
                           (6, 6 + self.height // 4, self.width, self.height // 2))
        surface.blit(bolt_surf, (int(sx) - cx, int(sy) - cy))


class ProximityMine:
    """Lucian Alliance proximity mine — sits in world, explodes near enemies."""
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.radius = 12
        self.detection_radius = 100
        self.damage = 40
        self.active = True
        self.is_player_proj = True
        self.pulse = random.uniform(0, math.pi * 2)
        self.lifetime = 600  # 10 seconds
        self.armed_timer = 30  # Arm after 0.5s

    def update(self):
        self.pulse += 0.1
        self.lifetime -= 1
        if self.armed_timer > 0:
            self.armed_timer -= 1
        if self.lifetime <= 0:
            self.active = False

    def is_armed(self):
        return self.armed_timer <= 0

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.radius, int(self.y) - self.radius,
                          self.radius * 2, self.radius * 2)

    def draw(self, surface, camera=None):
        if not self.active:
            return
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

        pulse_r = self.radius + int(math.sin(self.pulse) * 3)
        mine_surf = pygame.Surface((pulse_r * 4, pulse_r * 4), pygame.SRCALPHA)
        c = pulse_r * 2

        # Detection ring (faint, pulsing)
        if self.is_armed():
            ring_alpha = int(30 + abs(math.sin(self.pulse * 2)) * 30)
            pygame.draw.circle(mine_surf, (*self.color[:3], ring_alpha), (c, c),
                             int(self.detection_radius * 0.3), 1)

        # Mine body
        armed_color = self.color if self.is_armed() else (100, 100, 100)
        pygame.draw.circle(mine_surf, (*armed_color[:3], 180), (c, c), pulse_r)
        # Blinking core
        if self.is_armed() and int(self.pulse * 3) % 2 == 0:
            pygame.draw.circle(mine_surf, (255, 50, 50), (c, c), pulse_r // 3)
        else:
            pygame.draw.circle(mine_surf, (200, 200, 200), (c, c), pulse_r // 3)

        surface.blit(mine_surf, (int(sx) - c, int(sy) - c))


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

    def draw(self, surface, camera=None):
        if not self.active:
            return
        for segment in self.segments:
            for i in range(len(segment) - 1):
                if camera:
                    p1x, p1y = camera.world_to_screen(segment[i][0], segment[i][1])
                    p2x, p2y = camera.world_to_screen(segment[i+1][0], segment[i+1][1])
                else:
                    p1x, p1y = segment[i]
                    p2x, p2y = segment[i+1]
                # Outer glow
                pygame.draw.line(surface, (100, 150, 255),
                               (int(p1x), int(p1y)),
                               (int(p2x), int(p2y)), 4)
                # Bright core
                pygame.draw.line(surface, (200, 220, 255),
                               (int(p1x), int(p1y)),
                               (int(p2x), int(p2y)), 2)
                # White center
                pygame.draw.line(surface, (255, 255, 255),
                               (int(p1x), int(p1y)),
                               (int(p2x), int(p2y)), 1)


class AreaBomb:
    """Al'kesh bomber projectile — slow-falling bomb that detonates on a fuse.

    Moves slowly toward a target area, then explodes after a fuse timer
    dealing AoE damage within its blast radius.
    """
    def __init__(self, x, y, target_x, target_y, damage=30, blast_radius=120):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.damage = damage
        self.blast_radius = blast_radius
        self.active = True
        self.is_player_proj = False
        self.fuse_timer = 0
        self.fuse_duration = 120  # 2 seconds at 60fps
        self.detonated = False
        self.radius = 10
        self.pulse = 0
        # Slow drift toward target
        dx = target_x - x
        dy = target_y - y
        dist = max(1, math.hypot(dx, dy))
        speed = 2.0
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed

    def update(self):
        self.fuse_timer += 1
        self.pulse += 0.15
        if not self.detonated:
            self.x += self.vx
            self.y += self.vy
        if self.fuse_timer >= self.fuse_duration:
            self.detonated = True
            self.active = False

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.radius, int(self.y) - self.radius,
                          self.radius * 2, self.radius * 2)

    def draw(self, surface, camera=None):
        if not self.active:
            return
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

        # Pulsing warning glow that intensifies as fuse burns down
        progress = self.fuse_timer / self.fuse_duration
        pulse_r = self.radius + int(math.sin(self.pulse) * 3)
        warn_alpha = int(80 + 175 * progress)

        bomb_surf = pygame.Surface((pulse_r * 4, pulse_r * 4), pygame.SRCALPHA)
        c = pulse_r * 2
        # Warning radius ring (grows as detonation nears)
        if progress > 0.3:
            warn_r = int(self.blast_radius * progress * 0.3)
            pygame.draw.circle(bomb_surf, (255, 100, 0, int(30 * progress)),
                             (c, c), warn_r, 1)
        # Bomb body
        pygame.draw.circle(bomb_surf, (200, 100, 0, warn_alpha), (c, c), pulse_r)
        # Blinking core (faster as fuse runs out)
        blink_rate = max(2, int(8 * (1 - progress)))
        if int(self.pulse * 3) % blink_rate < blink_rate // 2:
            pygame.draw.circle(bomb_surf, (255, 50, 0), (c, c), pulse_r // 2)
        else:
            pygame.draw.circle(bomb_surf, (255, 200, 50), (c, c), pulse_r // 2)
        surface.blit(bomb_surf, (int(sx) - c, int(sy) - c))



class PlasmaLance(Projectile):
    """Asgard plasma lance — slow thick cyan bolt, high damage, pierces 1 enemy."""
    def __init__(self, x, y, direction, color=(0, 255, 255), speed=8):
        super().__init__(x, y, direction, color, speed, damage=35)
        self.width = 50
        self.height = 14
        self.piercing = True
        self._pierce_count = 0
        self._max_pierce = 1
        self.trail = []
        self.pulse = 0

    def update(self):
        self.pulse += 0.2
        self.trail.append({"x": self.x, "y": self.y, "alpha": 180})
        if len(self.trail) > 12:
            self.trail.pop(0)
        for t in self.trail:
            t["alpha"] -= 18
        self.trail = [t for t in self.trail if t["alpha"] > 0]
        super().update()

    def on_hit(self):
        """Called by game.py on hit. Returns True if projectile should deactivate."""
        self._pierce_count += 1
        return self._pierce_count > self._max_pierce

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.width // 2, int(self.y) - self.height // 2,
                          self.width, self.height)

    def draw(self, surface, camera=None):
        for t in self.trail:
            if camera:
                tx, ty = camera.world_to_screen(t["x"], t["y"])
            else:
                tx, ty = t["x"], t["y"]
            alpha = max(0, t["alpha"])
            trail_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (0, 200, 255, alpha), (8, 8), 6)
            surface.blit(trail_surf, (int(tx) - 8, int(ty) - 8))

        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

        pulse_w = self.width + int(math.sin(self.pulse) * 4)
        bolt_surf = pygame.Surface((pulse_w + 16, self.height + 16), pygame.SRCALPHA)
        cx = pulse_w // 2 + 8
        cy = self.height // 2 + 8
        # Outer glow
        pygame.draw.ellipse(bolt_surf, (0, 200, 255, 80),
                           (0, 0, pulse_w + 16, self.height + 16))
        # Core
        pygame.draw.ellipse(bolt_surf, self.color,
                           (4, 4, pulse_w + 8, self.height + 8))
        # White center
        pygame.draw.ellipse(bolt_surf, (255, 255, 255),
                           (8, 6, pulse_w, self.height + 4))
        surface.blit(bolt_surf, (int(sx) - cx, int(sy) - cy))


class DisruptorPulse(Projectile):
    """Asgard disruptor pulse — rapid small blue-white flickering shot."""
    def __init__(self, x, y, direction, color=(100, 180, 255), speed=20):
        super().__init__(x, y, direction, color, speed, damage=8)
        self.radius = 8
        self.flicker = 0

    def update(self):
        super().update()
        self.flicker += 0.4

    def get_rect(self):
        return pygame.Rect(int(self.x) - self.radius, int(self.y) - self.radius,
                          self.radius * 2, self.radius * 2)

    def draw(self, surface, camera=None):
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y
        flicker_r = self.radius + int(math.sin(self.flicker) * 3)
        surf = pygame.Surface((flicker_r * 4, flicker_r * 4), pygame.SRCALPHA)
        c = flicker_r * 2
        # Outer glow
        pygame.draw.circle(surf, (100, 180, 255, 60), (c, c), flicker_r + 4)
        # Main body
        pygame.draw.circle(surf, self.color, (c, c), flicker_r)
        # White-hot core
        pygame.draw.circle(surf, (220, 240, 255), (c, c), max(2, flicker_r // 2))
        surface.blit(surf, (int(sx) - c, int(sy) - c))


class OriBossBeam:
    """Ori mothership sweeping beam — long golden-yellow beam that rotates.

    1500px length, 30px width, sweeps 90 degrees over 120 frames.
    Deals 1.5 damage/frame to anything it touches.
    """
    def __init__(self, x, y, start_angle):
        self.x = x
        self.y = y
        self.start_angle = start_angle
        self.current_angle = start_angle
        self.sweep_range = math.pi / 2  # 90 degrees
        self.length = 1500
        self.width = 20
        self.timer = 0
        self.charge_duration = 60   # 1s charge-up telegraph before beam fires
        self.duration = 180  # 3 seconds sweep (slower = more dodgeable)
        self.damage_per_frame = 1.875  # 1.5 * 1.25
        self.active = True
        self.charging = True  # True during charge-up phase (no damage)
        self.pulse = 0

    def update(self):
        self.timer += 1
        self.pulse += 0.3
        if self.charging:
            if self.timer >= self.charge_duration:
                self.charging = False
                self.timer = 0  # Reset timer for sweep phase
        else:
            progress = self.timer / self.duration
            self.current_angle = self.start_angle + self.sweep_range * progress
            if self.timer >= self.duration:
                self.active = False

    def get_end_pos(self):
        ex = self.x + math.cos(self.current_angle) * self.length
        ey = self.y + math.sin(self.current_angle) * self.length
        return ex, ey

    def line_circle_intersect(self, cx, cy, radius):
        """Check if a circle at (cx, cy) with given radius intersects this beam line."""
        ex, ey = self.get_end_pos()
        # Vector from start to end
        dx = ex - self.x
        dy = ey - self.y
        # Vector from start to circle center
        fx = self.x - cx
        fy = self.y - cy
        a = dx * dx + dy * dy
        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - (radius + self.width / 2) ** 2
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return False
        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2 * a)
        t2 = (-b + discriminant) / (2 * a)
        return (0 <= t1 <= 1) or (0 <= t2 <= 1) or (t1 < 0 and t2 > 1)

    def draw(self, surface, camera=None):
        if not self.active:
            return
        ex, ey = self.get_end_pos()
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
            draw_ex, draw_ey = camera.world_to_screen(ex, ey)
        else:
            sx, sy = self.x, self.y
            draw_ex, draw_ey = ex, ey

        if self.charging:
            # Charge-up telegraph: pulsing warning line + growing origin glow
            charge_progress = self.timer / self.charge_duration
            flicker = int(128 + 127 * math.sin(self.timer * 0.5))
            # Thin flickering warning line showing where beam will fire
            pygame.draw.line(surface, (255, 200, 50, flicker),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), 2)
            # Growing glow at origin
            glow_r = int(10 + 30 * charge_progress)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            alpha = int(100 + 155 * charge_progress)
            pygame.draw.circle(glow_surf, (255, 220, 80, alpha), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (int(sx) - glow_r, int(sy) - glow_r))
        else:
            pulse_w = int(self.width + math.sin(self.pulse) * 6)
            # Outer glow
            pygame.draw.line(surface, (255, 200, 50, 100),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), pulse_w + 12)
            # Main beam
            pygame.draw.line(surface, (255, 220, 80),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), pulse_w)
            # Core
            pygame.draw.line(surface, (255, 255, 200),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), max(2, pulse_w // 3))


class WraithBossBeam(OriBossBeam):
    """Wraith Hive sweeping beam — purple life-draining beam that rotates.

    1200px length, 25px width, sweeps 90 degrees over 120 frames.
    Deals 1.2 damage/frame + heals the Wraith boss for 50% of damage dealt.
    """
    def __init__(self, x, y, start_angle):
        super().__init__(x, y, start_angle)
        self.length = 1200
        self.width = 18
        self.damage_per_frame = 1.5  # 1.2 * 1.25
        self.life_steal_pct = 0.5  # Heal boss for 50% of damage dealt

    def draw(self, surface, camera=None):
        if not self.active:
            return
        ex, ey = self.get_end_pos()
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
            draw_ex, draw_ey = camera.world_to_screen(ex, ey)
        else:
            sx, sy = self.x, self.y
            draw_ex, draw_ey = ex, ey

        if self.charging:
            # Charge-up telegraph: pulsing purple warning line + growing glow
            charge_progress = self.timer / self.charge_duration
            flicker = int(128 + 127 * math.sin(self.timer * 0.5))
            pygame.draw.line(surface, (160, 40, 255, flicker),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), 2)
            glow_r = int(10 + 30 * charge_progress)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            alpha = int(100 + 155 * charge_progress)
            pygame.draw.circle(glow_surf, (160, 40, 255, alpha), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (int(sx) - glow_r, int(sy) - glow_r))
        else:
            pulse_w = int(self.width + math.sin(self.pulse) * 5)
            # Outer glow — deep purple
            pygame.draw.line(surface, (120, 0, 200),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), pulse_w + 14)
            # Main beam — bright purple
            pygame.draw.line(surface, (160, 40, 255),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), pulse_w)
            # Core — pale violet
            pygame.draw.line(surface, (220, 180, 255),
                            (int(sx), int(sy)), (int(draw_ex), int(draw_ey)), max(2, pulse_w // 3))
