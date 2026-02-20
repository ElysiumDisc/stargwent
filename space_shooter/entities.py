"""Entity classes for the space shooter (non-projectile, non-ship)."""

import pygame
import math
import random
import os


class Asteroid:
    """Floating asteroid obstacle — spawned by the game/spawner in world-space."""
    def __init__(self, x, y, vx=None, vy=None, size=None):
        self.x = x
        self.y = y
        self.size = size or random.randint(60, 110)
        speed = random.uniform(3.0, 6.0)

        if vx is not None:
            self.vx = vx
            self.vy = vy
        else:
            angle = random.uniform(0, math.pi * 2)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed

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

    def draw(self, surface, camera=None):
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y
        draw_rect = self.image.get_rect(center=(int(sx), int(sy)))
        surface.blit(self.image, draw_rect)


# Cache loaded icon images at module level
_icon_cache = {}


def _load_icon(icon_name, size=40):
    """Load and cache an icon image from assets/icons/."""
    key = (icon_name, size)
    if key not in _icon_cache:
        path = os.path.join("assets", "icons", icon_name)
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (size, size))
            _icon_cache[key] = img
        except (pygame.error, FileNotFoundError):
            _icon_cache[key] = None
    return _icon_cache[key]


class PowerUp:
    """Collectible power-up that grants temporary or instant effects."""

    # Power-up types with their properties
    TYPES = {
        "shield": {
            "name": "Shield Boost",
            "color": (100, 200, 255),
            "duration": 0,  # Instant
            "spawn_weight": 15,
            "icon": "S",
            "icon_file": "special.png",
        },
        "rapid_fire": {
            "name": "Rapid Fire",
            "color": (255, 150, 50),
            "duration": 600,  # 10 seconds at 60 FPS
            "spawn_weight": 10,
            "icon": "R",
            "icon_file": "siege.png",
        },
        "drone": {
            "name": "Drone Swarm",
            "color": (150, 255, 150),
            "duration": 480,  # 8 seconds
            "spawn_weight": 8,
            "icon": "D",
            "icon_file": "ranged.png",
        },
        "damage": {
            "name": "Naquadah Core",
            "color": (255, 200, 100),
            "duration": 720,  # 12 seconds
            "spawn_weight": 12,
            "icon": "N",
            "icon_file": "close.png",
        },
        "cloak": {
            "name": "Cloak",
            "color": (180, 100, 255),
            "duration": 300,  # 5 seconds
            "spawn_weight": 5,
            "icon": "C",
            "icon_file": "agile.png",
        },
        "overcharge": {
            "name": "OVERCHARGE",
            "color": (255, 255, 100),
            "duration": 480,  # 8 seconds
            "spawn_weight": 6,
            "icon": "!",
            "icon_file": "weather.png",
        },
        "time_warp": {
            "name": "Time Warp",
            "color": (100, 180, 255),
            "duration": 420,  # 7 seconds
            "spawn_weight": 5,
            "icon": "T",
            "icon_file": "all.png",
        },
        "magnetize": {
            "name": "Magnetize",
            "color": (50, 255, 200),
            "duration": 360,  # 6 seconds
            "spawn_weight": 7,
            "icon": "M",
            "icon_file": "neutral.png",
        },
        # --- FACTION EPIC POWERUPS (faction-specific, one per faction) ---
        "asgard_beam_array": {
            "name": "Asgard Beam Array",
            "color": (0, 255, 255),
            "duration": 360,  # 6 seconds
            "spawn_weight": 0,  # Only spawned via faction pool
            "icon": "A",
            "icon_file": "all.png",
            "rarity": "epic",
            "faction": "asgard",
        },
        "tauri_railgun_barrage": {
            "name": "Railgun Barrage",
            "color": (80, 180, 255),
            "duration": 420,  # 7 seconds
            "spawn_weight": 0,
            "icon": "R",
            "icon_file": "siege.png",
            "rarity": "epic",
            "faction": "tau'ri",
        },
        "goauld_sarcophagus": {
            "name": "Sarcophagus",
            "color": (255, 215, 0),
            "duration": 0,  # Instant
            "spawn_weight": 0,
            "icon": "S",
            "icon_file": "close.png",
            "rarity": "epic",
            "faction": "goa'uld",
        },
        "jaffa_blood_rage": {
            "name": "Blood of Sokar",
            "color": (255, 80, 30),
            "duration": 360,  # 6 seconds
            "spawn_weight": 0,
            "icon": "B",
            "icon_file": "weather.png",
            "rarity": "epic",
            "faction": "jaffa rebellion",
        },
        "lucian_kassa": {
            "name": "Kassa Overdose",
            "color": (200, 80, 255),
            "duration": 420,  # 7 seconds
            "spawn_weight": 0,
            "icon": "K",
            "icon_file": "agile.png",
            "rarity": "epic",
            "faction": "lucian alliance",
        },
        # --- FACTION LEGENDARY POWERUPS (super rare, massive effects) ---
        "asgard_mjolnir": {
            "name": "Mjolnir Strike",
            "color": (150, 220, 255),
            "duration": 0,  # Instant nuke
            "spawn_weight": 0,
            "icon": "M",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "asgard",
        },
        "tauri_ancient_drones": {
            "name": "Ancient Drone Swarm",
            "color": (255, 200, 50),
            "duration": 600,  # 10 seconds
            "spawn_weight": 0,
            "icon": "D",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "tau'ri",
        },
        "goauld_hatak_strike": {
            "name": "Ha'tak Bombardment",
            "color": (255, 180, 0),
            "duration": 0,  # Instant
            "spawn_weight": 0,
            "icon": "H",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "goa'uld",
        },
        "jaffa_freedom": {
            "name": "Jaffa, KREE!",
            "color": (255, 150, 50),
            "duration": 300,  # 5 seconds
            "spawn_weight": 0,
            "icon": "K",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "jaffa rebellion",
        },
        "lucian_nuke": {
            "name": "Naquadria Bomb",
            "color": (255, 100, 255),
            "duration": 0,  # Instant
            "spawn_weight": 0,
            "icon": "N",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "lucian alliance",
        },
    }

    # Rarity colors for powerup border glow
    RARITY_GLOW = {
        "common": None,
        "epic": (180, 80, 255),
        "legendary": (255, 200, 50),
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
        # Try loading icon image
        self._icon_image = _load_icon(self.props.get("icon_file", ""), 32)

    def update(self):
        """Update power-up animation (no drift — stays in place in world)."""
        self.pulse += 0.1

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
        to_remove = []
        for i, p in enumerate(self.particles):
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 0.03
            if p['life'] <= 0:
                to_remove.append(i)
        for i in reversed(to_remove):
            self.particles.pop(i)

        # Lifetime: despawn after 30 seconds
        # (tracked externally or via pulse counter)

    def get_rect(self):
        """Get collision rectangle."""
        return pygame.Rect(int(self.x - self.size), int(self.y - self.size),
                          self.size * 2, self.size * 2)

    def draw(self, surface, camera=None):
        """Draw power-up with glow effect."""
        if not self.active:
            return

        if camera:
            draw_x, draw_y = camera.world_to_screen(self.x, self.y)
        else:
            draw_x, draw_y = self.x, self.y

        # Draw particles
        for p in self.particles:
            if camera:
                px, py = camera.world_to_screen(p['x'], p['y'])
            else:
                px, py = p['x'], p['y']
            alpha = int(p['life'] * 150)
            p_surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*self.props['color'], alpha),
                             (p['size'], p['size']), p['size'])
            surface.blit(p_surf, (int(px - p['size']), int(py - p['size'])))

        # Pulsing glow effect
        rarity = self.props.get('rarity', 'common')
        size_bonus = 8 if rarity == 'legendary' else (4 if rarity == 'epic' else 0)
        pulse_size = self.size + size_bonus + int(math.sin(self.pulse) * 5)
        bob_y = draw_y + math.sin(self.pulse * 0.5 + self.bob_offset) * 8

        # Create glow surface
        glow_size = pulse_size + 15 + size_bonus
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        center = glow_size

        # Rarity outer ring (epic = purple pulsing, legendary = golden rotating)
        rarity_glow = self.RARITY_GLOW.get(rarity)
        if rarity_glow:
            ring_alpha = int(80 + abs(math.sin(self.pulse * 1.5)) * 100)
            pygame.draw.circle(glow_surf, (*rarity_glow, ring_alpha),
                             (center, center), glow_size, 3)
            if rarity == 'legendary':
                # Extra golden starburst for legendary
                for i in range(6):
                    angle = self.pulse * 0.8 + i * math.pi / 3
                    ex = center + int(math.cos(angle) * (glow_size - 2))
                    ey = center + int(math.sin(angle) * (glow_size - 2))
                    pygame.draw.circle(glow_surf, (255, 255, 200, ring_alpha),
                                     (ex, ey), 4)

        # Outer glow
        pygame.draw.circle(glow_surf, (*self.props['color'], 60), (center, center), glow_size - 3)
        pygame.draw.circle(glow_surf, (*self.props['color'], 100), (center, center), pulse_size + 5)

        # Main circle
        pygame.draw.circle(glow_surf, self.props['color'], (center, center), pulse_size)

        # White core
        pygame.draw.circle(glow_surf, (255, 255, 255), (center, center), pulse_size // 2)

        # Icon — prefer image, fallback to text
        if self._icon_image:
            icon_rect = self._icon_image.get_rect(center=(center, center))
            glow_surf.blit(self._icon_image, icon_rect)
        else:
            icon_surf = self._icon_font.render(self.props['icon'], True, (0, 0, 0))
            icon_rect = icon_surf.get_rect(center=(center, center))
            glow_surf.blit(icon_surf, icon_rect)

        surface.blit(glow_surf, (int(draw_x - glow_size), int(bob_y - glow_size)))

    @classmethod
    def spawn_at(cls, x, y, faction=None):
        """Spawn a random power-up at a given world position.

        If faction is provided, includes faction-specific epic/legendary powerups
        with a chance to drop.
        """
        # Build weighted pool: base types + faction-specific
        pool = {}
        for ptype, props in cls.TYPES.items():
            w = props['spawn_weight']
            if w > 0:
                pool[ptype] = w
            elif faction and props.get('faction'):
                # Include faction-specific powerups if faction matches
                pfaction = props['faction'].lower()
                player_f = faction.lower()
                if pfaction == player_f or pfaction in player_f or player_f in pfaction:
                    rarity = props.get('rarity', 'common')
                    if rarity == 'epic':
                        pool[ptype] = 4  # ~8% of total weight
                    elif rarity == 'legendary':
                        pool[ptype] = 1.5  # ~3% of total weight

        total_weight = sum(pool.values())
        roll = random.uniform(0, total_weight)
        cumulative = 0
        chosen_type = "shield"
        for ptype, weight in pool.items():
            cumulative += weight
            if roll <= cumulative:
                chosen_type = ptype
                break
        return cls(x, y, chosen_type)

    @classmethod
    def spawn_random(cls, screen_width, screen_height):
        """Legacy spawn method (not used in infinite mode)."""
        x = screen_width + 30
        y = random.randint(100, screen_height - 100)
        return cls.spawn_at(x, y)


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

    def draw(self, surface, camera=None):
        """Draw the drone."""
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y
        drone_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.polygon(drone_surf, (100, 255, 100), [(10, 0), (20, 20), (0, 20)])
        pygame.draw.polygon(drone_surf, (255, 255, 255), [(10, 0), (20, 20), (0, 20)], 2)
        surface.blit(drone_surf, (int(sx - 10), int(sy - 10)))


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

    def draw(self, surface, camera=None):
        if not self.active:
            return
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y
        pulse_r = self.radius + int(math.sin(self.pulse) * 3)
        orb_surf = pygame.Surface((pulse_r * 4, pulse_r * 4), pygame.SRCALPHA)
        center = pulse_r * 2
        # Outer glow
        pygame.draw.circle(orb_surf, (50, 255, 50, 60), (center, center), pulse_r + 6)
        # Main orb
        pygame.draw.circle(orb_surf, (100, 255, 100), (center, center), pulse_r)
        # Bright core
        pygame.draw.circle(orb_surf, (200, 255, 200), (center, center), pulse_r // 2)
        surface.blit(orb_surf, (int(sx) - center, int(sy) - center))


class WormholeEffect:
    """Animated wormhole vortex for the player escape ability."""
    def __init__(self, x, y, is_entry=True):
        self.x = x
        self.y = y
        self.is_entry = is_entry  # Entry shrinks, exit expands
        self.timer = 0
        self.duration = 30  # Snappier: 0.5 sec (was 0.75)
        self.active = True

    def update(self):
        self.timer += 1
        if self.timer >= self.duration:
            self.active = False
        return self.active

    def draw(self, surface, camera=None):
        if not self.active:
            return

        if camera:
            draw_x, draw_y = camera.world_to_screen(self.x, self.y)
        else:
            draw_x, draw_y = self.x, self.y

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
            angle_off = self.timer * 0.25 + i * (math.pi / 2)  # Faster spin
            r = int(radius * (0.4 + i * 0.2))
            a = max(0, min(255, ring_alpha - i * 40))
            # Ring color shifts from blue center to cyan edge
            blue = min(255, 150 + i * 30)
            pygame.draw.circle(surf, (100, blue, 255, a), (c, c), r, 3)
            # Rotating bright spots on each ring
            for j in range(3):
                spot_angle = angle_off + j * (math.pi * 2 / 3)
                spot_x = c + int(math.cos(spot_angle) * r)
                spot_y = c + int(math.sin(spot_angle) * r)
                pygame.draw.circle(surf, (200, 230, 255, a), (spot_x, spot_y), max(2, 5 - i))

        # Bright center core
        core_r = max(2, int(radius * 0.25))
        core_a = min(255, ring_alpha + 50)
        pygame.draw.circle(surf, (220, 240, 255, core_a), (c, c), core_r)

        surface.blit(surf, (int(draw_x) - c, int(draw_y) - c))


class Explosion:
    """Explosion effect when a ship is destroyed. 3 tiers: small, normal, large."""
    def __init__(self, x, y, tier="normal"):
        self.x = x
        self.y = y
        self.tier = tier
        self.particles = []
        self.timer = 0

        if tier == "small":
            self.duration = 30
            num_particles = 15
            speed_range = (2, 6)
            size_range = (2, 8)
        elif tier == "large":
            self.duration = 90
            num_particles = 60
            speed_range = (3, 14)
            size_range = (4, 18)
        else:  # normal
            self.duration = 60
            num_particles = 30
            speed_range = (2, 10)
            size_range = (3, 12)

        # Create explosion particles
        for _ in range(num_particles):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(*speed_range)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': random.randint(*size_range),
                'color': random.choice([
                    (255, 100, 0),
                    (255, 200, 0),
                    (255, 50, 0),
                    (255, 255, 100)
                ])
            })

        # Large explosions get a shockwave ring
        self.shockwave_radius = 0
        self.shockwave_max = 120 if tier == "large" else (60 if tier == "normal" else 0)

    def update(self):
        self.timer += 1
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vx'] *= 0.95
            p['vy'] *= 0.95
        # Expand shockwave
        if self.shockwave_max > 0:
            self.shockwave_radius = int(self.shockwave_max * (self.timer / self.duration))
        return self.timer < self.duration

    def draw(self, surface, camera=None):
        alpha = int(255 * (1 - self.timer / self.duration))

        # Draw shockwave ring
        if self.shockwave_radius > 5:
            if camera:
                sx, sy = camera.world_to_screen(self.x, self.y)
            else:
                sx, sy = self.x, self.y
            ring_alpha = max(0, int(alpha * 0.6))
            sz = self.shockwave_radius * 2 + 10
            ring_surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = sz // 2
            pygame.draw.circle(ring_surf, (255, 200, 100, ring_alpha), (c, c), self.shockwave_radius, 3)
            pygame.draw.circle(ring_surf, (255, 255, 200, ring_alpha // 2), (c, c), self.shockwave_radius, 1)
            surface.blit(ring_surf, (int(sx) - c, int(sy) - c))

        for p in self.particles:
            if camera:
                px, py = camera.world_to_screen(p['x'], p['y'])
            else:
                px, py = p['x'], p['y']
            color = (*p['color'], alpha)
            size = int(p['size'] * (1 - self.timer / self.duration))
            if size > 0:
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (size, size), size)
                surface.blit(surf, (int(px - size), int(py - size)))


class DamageNumber:
    """Floating damage number that rises and fades. Screen-space (doesn't scroll)."""
    def __init__(self, x, y, amount, color=(255, 255, 255)):
        # Store the screen-space position at creation time
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
        # These are world-space coords — we'll convert at draw time
        self._world_x = self.x
        self._world_y = self.y

    def update(self):
        self.timer += 1
        self._world_x += self.vx
        self._world_y += self.vy
        self.vy *= 0.97  # Decelerate
        if self.timer >= self.duration:
            self.active = False
        return self.active

    def draw(self, surface, camera=None):
        if not self.active:
            return
        if camera:
            sx, sy = camera.world_to_screen(self._world_x, self._world_y)
        else:
            sx, sy = self._world_x, self._world_y
        alpha = max(0, int(255 * (1 - self.timer / self.duration)))
        text = str(self.amount)
        text_surf = self.font.render(text, True, self.color)
        # Create alpha surface
        alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        alpha_surf.blit(text_surf, (0, 0))
        alpha_surf.set_alpha(alpha)
        surface.blit(alpha_surf, (int(sx) - text_surf.get_width() // 2,
                                  int(sy) - text_surf.get_height() // 2))


class PopupNotification:
    """Large text notification that rises and fades near the player."""
    def __init__(self, x, y, text, color=(255, 215, 0)):
        self._world_x = x
        self._world_y = y
        self.text = text
        self.color = color
        self.timer = 0
        self.duration = 90  # 1.5s at 60fps
        self.active = True
        self.font = pygame.font.SysFont("Arial", 32, bold=True)

    def update(self):
        self.timer += 1
        self._world_y -= 1.0  # Rise slowly
        if self.timer >= self.duration:
            self.active = False
        return self.active

    def draw(self, surface, camera=None):
        if not self.active:
            return
        if camera:
            sx, sy = camera.world_to_screen(self._world_x, self._world_y)
        else:
            sx, sy = self._world_x, self._world_y
        alpha = max(0, int(255 * (1 - self.timer / self.duration)))
        text_surf = self.font.render(self.text, True, self.color)
        alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        alpha_surf.blit(text_surf, (0, 0))
        alpha_surf.set_alpha(alpha)
        surface.blit(alpha_surf, (int(sx) - text_surf.get_width() // 2,
                                  int(sy) - text_surf.get_height() // 2))


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

    def draw(self, surface, camera=None):
        if not self.active:
            return
        if camera:
            draw_x, draw_y = camera.world_to_screen(self.x, self.y)
        else:
            draw_x, draw_y = self.x, self.y

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

        surface.blit(surf, (int(draw_x) - c, int(draw_y) - c))
