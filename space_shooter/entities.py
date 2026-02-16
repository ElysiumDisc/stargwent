"""Entity classes for the space shooter (non-projectile, non-ship)."""

import pygame
import math
import random


class Asteroid:
    """Floating asteroid obstacle - big, slow, easily avoidable."""
    def __init__(self, screen_width, screen_height, direction="right"):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.direction = direction

        self.size = random.randint(60, 110)
        speed = random.uniform(3.0, 6.0)

        # Spawn position and velocity based on direction
        if direction == "right":
            self.x = screen_width + self.size
            self.y = random.randint(150, screen_height - 150)
            self.vx = -speed
            self.vy = random.uniform(-0.5, 0.5)
        elif direction == "left":
            self.x = -self.size
            self.y = random.randint(150, screen_height - 150)
            self.vx = speed
            self.vy = random.uniform(-0.5, 0.5)
        elif direction == "top":
            self.x = random.randint(150, screen_width - 150)
            self.y = -self.size
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = speed
        else:  # bottom
            self.x = random.randint(150, screen_width - 150)
            self.y = screen_height + self.size
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = -speed

        self.rotation = 0
        self.rotation_speed = random.uniform(-1.0, 1.0)
        self.health = self.size * 0.4
        self.active = True

        self.color = random.choice([
            (100, 90, 80),
            (80, 70, 60),
            (90, 85, 75),
            (70, 65, 55)
        ])

        # Pre-render asteroid surface
        self.original_image = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        center = self.size

        # Generate rocky shape points
        points = []
        num_points = random.randint(8, 14)
        for i in range(num_points):
            angle = (i / num_points) * math.pi * 2
            dist = self.size // 2 + random.randint(-self.size // 5, self.size // 5)
            points.append((
                center + math.cos(angle) * dist,
                center + math.sin(angle) * dist
            ))

        # Draw to original image
        pygame.draw.polygon(self.original_image, self.color, points)
        pygame.draw.polygon(self.original_image, (50, 45, 40), points, 3)

        # Add craters
        for i in range(3):
            crater_x = center + random.randint(-self.size // 3, self.size // 3)
            crater_y = center + random.randint(-self.size // 3, self.size // 3)
            crater_size = random.randint(3, 8)
            pygame.draw.circle(self.original_image, (60, 55, 50), (crater_x, crater_y), crater_size)

        self.image = self.original_image
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        self._cached_angle = 0  # Track cached rotation angle

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rotation += self.rotation_speed

        # Only re-rotate when angle changes by >2 degrees (avoids Surface alloc every frame)
        if abs(self.rotation - self._cached_angle) > 2:
            self.image = pygame.transform.rotate(self.original_image, self.rotation)
            self._cached_angle = self.rotation
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

        # Remove if fully off any edge
        margin = self.size + 50
        if (self.x < -margin or self.x > self.screen_width + margin or
                self.y < -margin or self.y > self.screen_height + margin):
            self.active = False

    def get_rect(self):
        # Return smaller hitbox for forgiveness
        hitbox_size = self.size * 0.8
        return pygame.Rect(int(self.x) - hitbox_size // 2, int(self.y) - hitbox_size // 2,
                          hitbox_size, hitbox_size)

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.active = False
            return True  # Destroyed
        return False

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class PowerUp:
    """Collectible power-up that grants temporary or instant effects."""

    # Power-up types with their properties
    TYPES = {
        "shield": {
            "name": "Shield Boost",
            "color": (100, 200, 255),
            "duration": 0,  # Instant
            "spawn_weight": 15,
            "icon": "S"
        },
        "rapid_fire": {
            "name": "Rapid Fire",
            "color": (255, 150, 50),
            "duration": 600,  # 10 seconds at 60 FPS
            "spawn_weight": 10,
            "icon": "R"
        },
        "drone": {
            "name": "Drone Swarm",
            "color": (150, 255, 150),
            "duration": 480,  # 8 seconds
            "spawn_weight": 8,
            "icon": "D"
        },
        "damage": {
            "name": "Naquadah Core",
            "color": (255, 200, 100),
            "duration": 720,  # 12 seconds
            "spawn_weight": 12,
            "icon": "N"
        },
        "cloak": {
            "name": "Cloak",
            "color": (180, 100, 255),
            "duration": 300,  # 5 seconds
            "spawn_weight": 5,
            "icon": "C"
        }
    }

    def __init__(self, x, y, powerup_type):
        self.x = x
        self.y = y
        self.type = powerup_type
        self.props = self.TYPES[powerup_type]
        self.active = True
        self.size = 30
        self.pulse = 0
        self.bob_offset = random.uniform(0, math.pi * 2)
        self.particles = []
        self._icon_font = pygame.font.SysFont("Arial", self.size, bold=True)

    def update(self):
        """Update power-up animation and position."""
        self.pulse += 0.1
        # Slow horizontal drift
        self.x -= 1.5

        # Spawn glow particles occasionally
        if random.random() < 0.15:
            self.particles.append({
                'x': self.x + random.uniform(-10, 10),
                'y': self.y + random.uniform(-10, 10),
                'vx': random.uniform(-0.5, 0.5),
                'vy': random.uniform(-1, 0),
                'life': 1.0,
                'size': random.randint(2, 4)
            })

        # Update particles
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 0.03
            if p['life'] <= 0:
                self.particles.remove(p)

        # Remove if off screen
        if self.x < -50:
            self.active = False

    def get_rect(self):
        """Get collision rectangle."""
        return pygame.Rect(int(self.x - self.size), int(self.y - self.size),
                          self.size * 2, self.size * 2)

    def draw(self, surface):
        """Draw power-up with glow effect."""
        if not self.active:
            return

        # Draw particles
        for p in self.particles:
            alpha = int(p['life'] * 150)
            p_surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*self.props['color'], alpha),
                             (p['size'], p['size']), p['size'])
            surface.blit(p_surf, (int(p['x'] - p['size']), int(p['y'] - p['size'])))

        # Pulsing glow effect
        pulse_size = self.size + int(math.sin(self.pulse) * 5)
        bob_y = self.y + math.sin(self.pulse * 0.5 + self.bob_offset) * 8

        # Create glow surface
        glow_size = pulse_size + 15
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        center = glow_size

        # Outer glow
        pygame.draw.circle(glow_surf, (*self.props['color'], 60), (center, center), glow_size)
        pygame.draw.circle(glow_surf, (*self.props['color'], 100), (center, center), pulse_size + 5)

        # Main circle
        pygame.draw.circle(glow_surf, self.props['color'], (center, center), pulse_size)

        # White core
        pygame.draw.circle(glow_surf, (255, 255, 255), (center, center), pulse_size // 2)

        # Icon letter (reuse cached font)
        icon_surf = self._icon_font.render(self.props['icon'], True, (0, 0, 0))
        icon_rect = icon_surf.get_rect(center=(center, center))
        glow_surf.blit(icon_surf, icon_rect)

        surface.blit(glow_surf, (int(self.x - glow_size), int(bob_y - glow_size)))

    @classmethod
    def spawn_random(cls, screen_width, screen_height):
        """Spawn a random power-up based on spawn weights."""
        # Calculate total weight
        total_weight = sum(t['spawn_weight'] for t in cls.TYPES.values())
        roll = random.uniform(0, total_weight)

        cumulative = 0
        chosen_type = "shield"  # Default
        for ptype, props in cls.TYPES.items():
            cumulative += props['spawn_weight']
            if roll <= cumulative:
                chosen_type = ptype
                break

        # Spawn on right side, random Y
        x = screen_width + 30
        y = random.randint(100, screen_height - 100)
        return cls(x, y, chosen_type)


class Drone:
    """Auto-targeting drone that orbits the player and shoots enemies."""

    def __init__(self, owner, angle_offset):
        self.owner = owner
        self.angle = angle_offset
        self.orbit_radius = 80
        self.x = owner.x
        self.y = owner.y
        self.fire_cooldown = 0
        self.fire_rate = 30  # frames between shots

    def update(self, enemies):
        """Update drone position and firing."""
        from .projectiles import Laser
        # Orbit around owner
        self.angle += 0.05
        self.x = self.owner.x + self.owner.width // 2 + math.cos(self.angle) * self.orbit_radius
        self.y = self.owner.y + math.sin(self.angle) * self.orbit_radius

        self.fire_cooldown = max(0, self.fire_cooldown - 1)

        # Auto-target nearest enemy
        if enemies and self.fire_cooldown <= 0:
            nearest = min(enemies, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            dist = math.hypot(nearest.x - self.x, nearest.y - self.y)
            if dist < 500:
                self.fire_cooldown = self.fire_rate
                # Calculate direction toward nearest enemy
                direction = 1 if nearest.x > self.x else -1
                return Laser(self.x, self.y, direction, (100, 255, 100), speed=20)
        return None

    def draw(self, surface):
        """Draw the drone."""
        drone_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.polygon(drone_surf, (100, 255, 100), [(10, 0), (20, 20), (0, 20)])
        pygame.draw.polygon(drone_surf, (255, 255, 255), [(10, 0), (20, 20), (0, 20)], 2)
        surface.blit(drone_surf, (int(self.x - 10), int(self.y - 10)))


class XPOrb:
    """XP orb dropped by enemies on death, drifts toward player."""
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value
        self.radius = 8
        self.active = True
        self.pulse = random.uniform(0, math.pi * 2)
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)

    def update(self, player_x, player_y, collection_radius=30):
        """Update orb: drift toward player, check collection."""
        self.pulse += 0.15
        # Gentle acceleration toward player (tractor beam feel)
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            accel = min(0.3, 8.0 / max(dist, 1))
            self.vx += (dx / dist) * accel
            self.vy += (dy / dist) * accel
        # Cap speed
        speed = math.hypot(self.vx, self.vy)
        if speed > 10:
            self.vx = self.vx / speed * 10
            self.vy = self.vy / speed * 10
        self.x += self.vx
        self.y += self.vy
        # Check collection
        if dist < collection_radius:
            self.active = False
            return self.value
        return 0

    def draw(self, surface):
        if not self.active:
            return
        pulse_r = self.radius + int(math.sin(self.pulse) * 3)
        orb_surf = pygame.Surface((pulse_r * 4, pulse_r * 4), pygame.SRCALPHA)
        center = pulse_r * 2
        # Outer glow
        pygame.draw.circle(orb_surf, (50, 255, 50, 60), (center, center), pulse_r + 6)
        # Main orb
        pygame.draw.circle(orb_surf, (100, 255, 100), (center, center), pulse_r)
        # Bright core
        pygame.draw.circle(orb_surf, (200, 255, 200), (center, center), pulse_r // 2)
        surface.blit(orb_surf, (int(self.x) - center, int(self.y) - center))


class WormholeEffect:
    """Animated wormhole vortex for the player escape ability."""
    def __init__(self, x, y, is_entry=True):
        self.x = x
        self.y = y
        self.is_entry = is_entry  # Entry shrinks, exit expands
        self.timer = 0
        self.duration = 45  # frames (~0.75 sec)
        self.active = True

    def update(self):
        self.timer += 1
        if self.timer >= self.duration:
            self.active = False
        return self.active

    def draw(self, surface):
        if not self.active:
            return
        progress = self.timer / self.duration
        if self.is_entry:
            # Entry: starts big, collapses to a point
            radius = int(80 * (1.0 - progress))
            ring_alpha = int(200 * (1.0 - progress))
        else:
            # Exit: starts as a point, expands out
            radius = int(80 * progress)
            ring_alpha = int(200 * (1.0 - progress * 0.5))

        if radius < 2:
            return
        sz = radius * 2 + 40
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        c = sz // 2

        # Spinning rings — blue/white vortex
        num_rings = 4
        for i in range(num_rings):
            angle_off = self.timer * 0.15 + i * (math.pi / 2)
            r = int(radius * (0.4 + i * 0.2))
            a = max(0, min(255, ring_alpha - i * 40))
            # Ring color shifts from blue center to cyan edge
            blue = min(255, 150 + i * 30)
            pygame.draw.circle(surf, (100, blue, 255, a), (c, c), r, 3)
            # Rotating bright spots on each ring
            for j in range(3):
                spot_angle = angle_off + j * (math.pi * 2 / 3)
                sx = c + int(math.cos(spot_angle) * r)
                sy = c + int(math.sin(spot_angle) * r)
                pygame.draw.circle(surf, (200, 230, 255, a), (sx, sy), max(2, 5 - i))

        # Bright center core
        core_r = max(2, int(radius * 0.25))
        core_a = min(255, ring_alpha + 50)
        pygame.draw.circle(surf, (220, 240, 255, core_a), (c, c), core_r)

        surface.blit(surf, (int(self.x) - c, int(self.y) - c))


class Explosion:
    """Explosion effect when a ship is destroyed."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.particles = []
        self.timer = 0
        self.duration = 60

        # Create explosion particles
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 10)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': random.randint(3, 12),
                'color': random.choice([
                    (255, 100, 0),
                    (255, 200, 0),
                    (255, 50, 0),
                    (255, 255, 100)
                ])
            })

    def update(self):
        self.timer += 1
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vx'] *= 0.95
            p['vy'] *= 0.95
        return self.timer < self.duration

    def draw(self, surface):
        alpha = int(255 * (1 - self.timer / self.duration))
        for p in self.particles:
            color = (*p['color'], alpha)
            size = int(p['size'] * (1 - self.timer / self.duration))
            if size > 0:
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (size, size), size)
                surface.blit(surf, (int(p['x'] - size), int(p['y'] - size)))


class DamageNumber:
    """Floating damage number that rises and fades."""
    def __init__(self, x, y, amount, color=(255, 255, 255)):
        self.x = x + random.uniform(-10, 10)
        self.y = y
        self.amount = int(amount) if amount == int(amount) else round(amount, 1)
        self.color = color
        self.timer = 0
        self.duration = 45  # 0.75s at 60fps
        self.active = True
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = -2.0
        self.font = pygame.font.SysFont("Arial", 20, bold=True)

    def update(self):
        self.timer += 1
        self.x += self.vx
        self.y += self.vy
        self.vy *= 0.97  # Decelerate
        if self.timer >= self.duration:
            self.active = False
        return self.active

    def draw(self, surface):
        if not self.active:
            return
        alpha = max(0, int(255 * (1 - self.timer / self.duration)))
        text = str(self.amount)
        text_surf = self.font.render(text, True, self.color)
        # Create alpha surface
        alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        alpha_surf.blit(text_surf, (0, 0))
        alpha_surf.set_alpha(alpha)
        surface.blit(alpha_surf, (int(self.x) - text_surf.get_width() // 2,
                                  int(self.y) - text_surf.get_height() // 2))


class PopupNotification:
    """Large text notification that rises and fades near the player."""
    def __init__(self, x, y, text, color=(255, 215, 0)):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.timer = 0
        self.duration = 90  # 1.5s at 60fps
        self.active = True
        self.font = pygame.font.SysFont("Arial", 32, bold=True)

    def update(self):
        self.timer += 1
        self.y -= 1.0  # Rise slowly
        if self.timer >= self.duration:
            self.active = False
        return self.active

    def draw(self, surface):
        if not self.active:
            return
        alpha = max(0, int(255 * (1 - self.timer / self.duration)))
        # Use cached font (no per-frame scaling — too expensive)
        text_surf = self.font.render(self.text, True, self.color)
        alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        alpha_surf.blit(text_surf, (0, 0))
        alpha_surf.set_alpha(alpha)
        surface.blit(alpha_surf, (int(self.x) - text_surf.get_width() // 2,
                                  int(self.y) - text_surf.get_height() // 2))


class GravityWell:
    """Deployable area that pulls and damages enemies."""
    def __init__(self, x, y, stacks=1):
        self.x = x
        self.y = y
        self.radius = 120
        self.pull_strength = 2.0
        self.tick_damage = 0.3 * stacks
        self.timer = 0
        self.duration = 300  # 5s at 60fps
        self.active = True
        self.rotation = 0

    def update(self, enemies):
        """Pull and damage enemies within radius. Returns list of killed enemy refs."""
        self.timer += 1
        self.rotation += 3
        if self.timer >= self.duration:
            self.active = False
            return []

        killed = []
        for enemy in enemies[:]:
            ex = enemy.x + getattr(enemy, 'width', 0) // 2
            ey = enemy.y
            dx = self.x - ex
            dy = self.y - ey
            dist = math.hypot(dx, dy)
            if dist < self.radius and dist > 1:
                # Pull toward center
                pull = self.pull_strength * (1 - dist / self.radius)
                enemy.x += (dx / dist) * pull
                enemy.y += (dy / dist) * pull
                # Tick damage
                if enemy.take_damage(self.tick_damage):
                    killed.append(enemy)
        return killed

    def draw(self, surface):
        if not self.active:
            return
        progress = self.timer / self.duration
        alpha_mult = 1.0 if progress < 0.8 else (1.0 - progress) / 0.2

        sz = self.radius * 2 + 20
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        c = sz // 2

        # Swirling concentric circles
        for i in range(4):
            r = int(self.radius * (0.3 + i * 0.2))
            angle = math.radians(self.rotation + i * 90)
            a = int(40 * alpha_mult)
            # Draw arc segments
            for j in range(6):
                arc_angle = angle + j * (math.pi / 3)
                ax = c + int(math.cos(arc_angle) * r)
                ay = c + int(math.sin(arc_angle) * r)
                pygame.draw.circle(surf, (150, 80, 255, a), (ax, ay), max(2, 6 - i))

        # Outer ring
        ring_a = int(60 * alpha_mult)
        pygame.draw.circle(surf, (120, 60, 200, ring_a), (c, c), self.radius, 2)
        # Inner glow
        inner_a = int(30 * alpha_mult)
        pygame.draw.circle(surf, (180, 100, 255, inner_a), (c, c), self.radius // 2)
        # Core
        core_a = int(100 * alpha_mult)
        pygame.draw.circle(surf, (200, 150, 255, core_a), (c, c), 8)

        surface.blit(surf, (int(self.x) - c, int(self.y) - c))
