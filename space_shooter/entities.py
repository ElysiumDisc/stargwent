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
        # --- NEW FACTION EPIC POWERUPS (2 per faction) ---
        "tauri_f302_squadron": {
            "name": "F-302 Squadron",
            "color": (80, 180, 255),
            "duration": 480,  # 8 seconds
            "spawn_weight": 0,
            "icon": "F",
            "icon_file": "siege.png",
            "rarity": "epic",
            "faction": "tau'ri",
        },
        "tauri_prometheus_shield": {
            "name": "Prometheus Shield",
            "color": (100, 200, 255),
            "duration": 600,  # 10 seconds
            "spawn_weight": 0,
            "icon": "P",
            "icon_file": "special.png",
            "rarity": "epic",
            "faction": "tau'ri",
        },
        "goauld_kull_warrior": {
            "name": "Kull Warrior",
            "color": (50, 50, 50),
            "duration": 240,  # 4 seconds
            "spawn_weight": 0,
            "icon": "K",
            "icon_file": "close.png",
            "rarity": "epic",
            "faction": "goa'uld",
        },
        "goauld_hand_device": {
            "name": "Hand Device",
            "color": (255, 200, 100),
            "duration": 0,  # Instant
            "spawn_weight": 0,
            "icon": "H",
            "icon_file": "close.png",
            "rarity": "epic",
            "faction": "goa'uld",
        },
        "asgard_time_dilation": {
            "name": "Time Dilation",
            "color": (100, 180, 255),
            "duration": 300,  # 5 seconds
            "spawn_weight": 0,
            "icon": "T",
            "icon_file": "all.png",
            "rarity": "epic",
            "faction": "asgard",
        },
        "asgard_matter_converter": {
            "name": "Matter Converter",
            "color": (200, 200, 255),
            "duration": 0,  # Instant
            "spawn_weight": 0,
            "icon": "C",
            "icon_file": "all.png",
            "rarity": "epic",
            "faction": "asgard",
        },
        "jaffa_tretonin": {
            "name": "Tretonin",
            "color": (100, 255, 100),
            "duration": 600,  # 10 seconds
            "spawn_weight": 0,
            "icon": "T",
            "icon_file": "weather.png",
            "rarity": "epic",
            "faction": "jaffa rebellion",
        },
        "jaffa_rite_sharran": {
            "name": "Rite of M'al Sharran",
            "color": (255, 180, 80),
            "duration": 0,  # Instant (conditional)
            "spawn_weight": 0,
            "icon": "R",
            "icon_file": "weather.png",
            "rarity": "epic",
            "faction": "jaffa rebellion",
        },
        "lucian_smugglers_luck": {
            "name": "Smuggler's Luck",
            "color": (200, 255, 100),
            "duration": 900,  # 15 seconds
            "spawn_weight": 0,
            "icon": "L",
            "icon_file": "agile.png",
            "rarity": "epic",
            "faction": "lucian alliance",
        },
        "lucian_black_market": {
            "name": "Black Market",
            "color": (180, 80, 200),
            "duration": 0,  # Instant
            "spawn_weight": 0,
            "icon": "B",
            "icon_file": "agile.png",
            "rarity": "epic",
            "faction": "lucian alliance",
        },
        # --- NEW FACTION LEGENDARY POWERUPS (1 per faction) ---
        "tauri_ancient_tech": {
            "name": "Ancient Tech",
            "color": (255, 220, 100),
            "duration": 480,  # 8 seconds
            "spawn_weight": 0,
            "icon": "A",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "tau'ri",
        },
        "goauld_ribbon_device": {
            "name": "Ribbon Device",
            "color": (255, 180, 50),
            "duration": 360,  # 6 seconds
            "spawn_weight": 0,
            "icon": "R",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "goa'uld",
        },
        "asgard_replicator_disruptor": {
            "name": "Replicator Disruptor",
            "color": (100, 220, 255),
            "duration": 0,  # Instant
            "spawn_weight": 0,
            "icon": "D",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "asgard",
        },
        "jaffa_free_jaffa_rally": {
            "name": "Free Jaffa Rally",
            "color": (255, 150, 50),
            "duration": 600,  # 10 seconds
            "spawn_weight": 0,
            "icon": "J",
            "icon_file": "Legendary commander.png",
            "rarity": "legendary",
            "faction": "jaffa rebellion",
        },
        "lucian_kassa_stash": {
            "name": "Kassa Stash",
            "color": (255, 80, 200),
            "duration": 240,  # 4 seconds
            "spawn_weight": 0,
            "icon": "K",
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
                # Calculate 2D direction toward nearest enemy
                dx = nearest.x - self.x
                dy = nearest.y - self.y
                direction = (dx / dist, dy / dist)
                return Laser(self.x, self.y, direction, (100, 255, 100), speed=20)
        return None

    def draw(self, surface, camera=None):
        """Draw the drone."""
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y
        if not hasattr(Drone, '_cached_surf'):
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.polygon(s, (100, 255, 100), [(10, 0), (20, 20), (0, 20)])
            pygame.draw.polygon(s, (255, 255, 255), [(10, 0), (20, 20), (0, 20)], 2)
            Drone._cached_surf = s
        surface.blit(Drone._cached_surf, (int(sx - 10), int(sy - 10)))


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
    """Explosion effect when a ship is destroyed. 3 tiers: small, normal, large.

    Supports custom color_palette for faction/enemy-themed explosions and
    an initial flash frame for visual punch.
    """

    # Default orange/yellow/red palette
    DEFAULT_PALETTE = [(255, 100, 0), (255, 200, 0), (255, 50, 0), (255, 255, 100)]

    def __init__(self, x, y, tier="normal", color_palette=None, secondary=False):
        self.x = x
        self.y = y
        self.tier = tier
        self.particles = []
        self.timer = 0
        palette = color_palette or self.DEFAULT_PALETTE

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
            num_particles = 40
            speed_range = (2, 10)
            size_range = (3, 12)

        # Secondary explosions are slightly offset and delayed-feeling
        if secondary:
            num_particles = num_particles // 2

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
                'color': random.choice(palette)
            })

        # Large explosions get a shockwave ring
        self.shockwave_radius = 0
        self.shockwave_max = 120 if tier == "large" else (60 if tier == "normal" else 0)

        # Flash frame: initial white pop
        self.flash_radius = {
            "small": 20, "normal": 35, "large": 60
        }.get(tier, 35)

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

        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

        # Flash frame: bright white circle on frames 0-2
        if self.timer <= 2:
            flash_alpha = int(255 * (1 - self.timer / 3))
            fr = self.flash_radius
            flash_surf = pygame.Surface((fr * 2, fr * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha),
                             (fr, fr), fr)
            surface.blit(flash_surf, (int(sx) - fr, int(sy) - fr))

        # Draw shockwave ring
        if self.shockwave_radius > 5:
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
        # Pre-render text surface once
        self._text_surf = self.font.render(str(self.amount), True, self.color)
        self._text_w = self._text_surf.get_width()
        self._text_h = self._text_surf.get_height()

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
        # Re-use pre-rendered text surface with alpha
        tmp = self._text_surf.copy()
        tmp.set_alpha(alpha)
        surface.blit(tmp, (int(sx) - self._text_w // 2,
                           int(sy) - self._text_h // 2))


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


class Sun:
    """Environmental hazard: Sun that collapses into a wormhole gravity well.

    Lifecycle phases (all in frames at 60fps):
    1. Growing (60f/1s): Orange circle expands from 0 to max_radius=80
    2. Stable (180f/3s): Full sun with pulsing corona glow, particle emission
    3. Exploding (30f/0.5s): White flash, expanding shockwave ring, screen shake
    4. Wormhole (300f/5s): Spinning blue-purple vortex, gravity pull 300px, 2 DPS core
    5. Closing (30f/0.5s): Shrinking vortex, flash, entity removed
    """

    PHASE_GROWING = 0
    PHASE_STABLE = 1
    PHASE_EXPLODING = 2
    PHASE_WORMHOLE = 3
    PHASE_CLOSING = 4

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.active = True
        self.phase = self.PHASE_GROWING
        self.timer = 0
        self.max_radius = 160
        self.current_radius = 0
        self.pulse = 0
        self.rotation = 0
        self.particles = []
        self.triggered_shake = False

        # Phase durations (frames)
        self.phase_durations = {
            self.PHASE_GROWING: 60,
            self.PHASE_STABLE: 180,
            self.PHASE_EXPLODING: 30,
            self.PHASE_WORMHOLE: 300,
            self.PHASE_CLOSING: 30,
        }

    def update(self, entities_dict=None):
        """Update sun state. entities_dict has 'ships', 'enemies', 'projectiles', 'asteroids'."""
        self.timer += 1
        self.pulse += 0.08
        self.rotation += 2

        dur = self.phase_durations[self.phase]
        progress = min(1.0, self.timer / dur)

        if self.phase == self.PHASE_GROWING:
            self.current_radius = int(self.max_radius * progress)
            if self.timer >= dur:
                self._next_phase()

        elif self.phase == self.PHASE_STABLE:
            self.current_radius = self.max_radius
            # Emit particles
            if random.random() < 0.3:
                angle = random.uniform(0, math.pi * 2)
                dist = self.max_radius + random.uniform(0, 20)
                self.particles.append({
                    'x': self.x + math.cos(angle) * dist,
                    'y': self.y + math.sin(angle) * dist,
                    'vx': math.cos(angle) * random.uniform(0.5, 1.5),
                    'vy': math.sin(angle) * random.uniform(0.5, 1.5),
                    'life': 1.0, 'size': random.randint(2, 5),
                })
            if self.timer >= dur:
                self._next_phase()

        elif self.phase == self.PHASE_EXPLODING:
            self.current_radius = int(self.max_radius * (1 - progress * 0.3))
            if not self.triggered_shake:
                self.triggered_shake = True
            if self.timer >= dur:
                self._next_phase()

        elif self.phase == self.PHASE_WORMHOLE:
            self.current_radius = int(self.max_radius * 0.7)
            # Apply gravity pull to all entities
            if entities_dict:
                self._apply_gravity(entities_dict)
            if self.timer >= dur:
                self._next_phase()

        elif self.phase == self.PHASE_CLOSING:
            self.current_radius = int(self.max_radius * 0.7 * (1 - progress))
            if self.timer >= dur:
                self.active = False

        # Update particles
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 0.03
        self.particles = [p for p in self.particles if p['life'] > 0]

    def _next_phase(self):
        self.phase += 1
        self.timer = 0
        self.triggered_shake = False

    def _apply_gravity(self, entities_dict):
        """Pull everything within 1000px toward center. 2 DPS at inner 160px."""
        pull_radius = 1000
        core_radius = 160
        max_accel = 5.5

        all_entities = []
        for ship in entities_dict.get('ships', []):
            all_entities.append(ship)
        for enemy in entities_dict.get('enemies', []):
            all_entities.append(enemy)
        for ally in entities_dict.get('allies', []):
            all_entities.append(ally)

        for ent in all_entities:
            ex = getattr(ent, 'x', 0) + getattr(ent, 'width', 0) // 2
            ey = getattr(ent, 'y', 0)
            dx = self.x - ex
            dy = self.y - ey
            dist = math.hypot(dx, dy)
            if dist < pull_radius and dist > 1:
                strength = max_accel * (1 - dist / pull_radius)
                ent.x += (dx / dist) * strength
                ent.y += (dy / dist) * strength
                # Core damage (2 DPS = 2/60 per frame)
                if dist < core_radius and hasattr(ent, 'take_damage'):
                    ent.take_damage(2.0 / 60.0)

        # Pull projectiles
        for proj in entities_dict.get('projectiles', []):
            dx = self.x - proj.x
            dy = self.y - proj.y
            dist = math.hypot(dx, dy)
            if dist < pull_radius and dist > 1:
                strength = max_accel * 0.5 * (1 - dist / pull_radius)
                proj.x += (dx / dist) * strength
                proj.y += (dy / dist) * strength

        # Pull asteroids
        for ast in entities_dict.get('asteroids', []):
            dx = self.x - ast.x
            dy = self.y - ast.y
            dist = math.hypot(dx, dy)
            if dist < pull_radius and dist > 1:
                strength = max_accel * 0.7 * (1 - dist / pull_radius)
                ast.vx += (dx / dist) * strength * 0.1
                ast.vy += (dy / dist) * strength * 0.1

    def draw(self, surface, camera=None):
        if not self.active or self.current_radius < 2:
            return
        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

        r = self.current_radius
        sz = r * 3 + 20
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        c = sz // 2

        if self.phase in (self.PHASE_GROWING, self.PHASE_STABLE):
            # Sun: orange/yellow with corona
            corona_pulse = int(math.sin(self.pulse) * 8)
            pygame.draw.circle(surf, (255, 150, 0, 40), (c, c), r + 15 + corona_pulse)
            pygame.draw.circle(surf, (255, 200, 50, 80), (c, c), r + 5)
            pygame.draw.circle(surf, (255, 200, 50), (c, c), r)
            pygame.draw.circle(surf, (255, 255, 200), (c, c), r // 2)

        elif self.phase == self.PHASE_EXPLODING:
            dur = self.phase_durations[self.phase]
            progress = min(1.0, self.timer / dur)
            flash_r = int(r * (1 + progress * 2))
            flash_alpha = int(255 * (1 - progress))
            pygame.draw.circle(surf, (255, 255, 255, flash_alpha), (c, c), flash_r)
            ring_r = int(r + progress * 150)
            ring_alpha = int(180 * (1 - progress))
            if ring_r > 0:
                pygame.draw.circle(surf, (200, 220, 255, ring_alpha), (c, c), ring_r, 3)

        elif self.phase in (self.PHASE_WORMHOLE, self.PHASE_CLOSING):
            num_rings = 5
            for i in range(num_rings):
                ring_r = int(r * (0.3 + i * 0.15))
                angle_off = math.radians(self.rotation + i * 72)
                a = max(0, int(150 - i * 25))
                blue = min(255, 100 + i * 30)
                pygame.draw.circle(surf, (100, blue, 255, a), (c, c), ring_r, 2)
                for j in range(3):
                    spot_angle = angle_off + j * (math.pi * 2 / 3)
                    spot_x = c + int(math.cos(spot_angle) * ring_r)
                    spot_y = c + int(math.sin(spot_angle) * ring_r)
                    pygame.draw.circle(surf, (180, 200, 255, a),
                                     (spot_x, spot_y), max(2, 4 - i))
            pygame.draw.circle(surf, (20, 0, 40, 200), (c, c), int(r * 0.25))
            core_a = int(120 + math.sin(self.pulse * 2) * 60)
            pygame.draw.circle(surf, (150, 100, 255, core_a), (c, c), int(r * 0.15))

        # Draw particles
        for p in self.particles:
            if camera:
                px, py = camera.world_to_screen(p['x'], p['y'])
            else:
                px, py = p['x'], p['y']
            pa = max(0, int(p['life'] * 200))
            ps = max(1, int(p['size'] * p['life']))
            if self.phase <= self.PHASE_STABLE:
                pc = (255, 200, 50, pa)
            else:
                pc = (150, 100, 255, pa)
            p_surf = pygame.Surface((ps * 2, ps * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, pc, (ps, ps), ps)
            surface.blit(p_surf, (int(px) - ps, int(py) - ps))

        surface.blit(surf, (int(sx) - c, int(sy) - c))



class Supergate:
    """Supergate portal that opens to spawn a boss ship.

    5 phases — full Stargate-style kawoosh sequence:
    1. APPEARING  (90f / 1.5s): Ring materialises, chevron pulses, energy crackle
    2. ACTIVATING (150f / 2.5s): Unstable vortex KAWOOSH explodes outward then
       retracts into a shimmering event horizon
    3. OPEN       (60f / 1s):   Stable wormhole, boss emerges from center
    4. CLOSING    (60f / 1s):   Horizon collapses, ring fades
    """

    PHASE_APPEARING = 0
    PHASE_ACTIVATING = 1
    PHASE_OPEN = 2
    PHASE_HOLDING = 3   # Stays open until boss is killed
    PHASE_CLOSING = 4

    def __init__(self, x, y, boss_hp=5000):
        self.x = x
        self.y = y
        self.active = True
        self.phase = self.PHASE_APPEARING
        self.timer = 0
        self.ring_scale = 0.0
        self.ring_radius = 150
        self.pulse = 0.0
        self.particles = []
        self.boss_spawned = False

        # Supergate is destroyable — 5x boss HP
        self.max_health = boss_hp * 5
        self.health = self.max_health
        self.hit_flash = 0

        # Kawoosh state
        self._kawoosh_burst_done = False
        self._tendrils = []          # lightning arcs around ring
        self._horizon_wobble = []    # per-frame wobble offsets (pre-calc)
        self._chevron_flash = 0.0

        # Try loading supergate image
        self._ring_image = None
        try:
            path = os.path.join("assets", "ships", "supergate.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                self._ring_image = pygame.transform.smoothscale(img, (300, 300))
        except (pygame.error, FileNotFoundError):
            pass

        self.phase_durations = {
            self.PHASE_APPEARING: 90,
            self.PHASE_ACTIVATING: 150,
            self.PHASE_OPEN: 60,
            self.PHASE_HOLDING: -1,  # Indefinite — closed externally via close()
            self.PHASE_CLOSING: 60,
        }
        self._linked_boss = None  # Set by game.py after boss spawns

    # ── update ──────────────────────────────────────────────────────

    def update(self):
        """Update supergate animation. Returns 'spawn_boss' when boss should emerge."""
        self.timer += 1
        self.pulse += 0.12
        if self.hit_flash > 0:
            self.hit_flash -= 1
        result = None

        dur = self.phase_durations[self.phase]
        progress = min(1.0, self.timer / dur) if dur > 0 else 0

        if self.phase == self.PHASE_APPEARING:
            self.ring_scale = progress ** 0.6          # ease-out: fast then slow
            self._chevron_flash = math.sin(self.timer * 0.4) * 0.5 + 0.5
            # Energy crackle sparks along ring edge
            if random.random() < 0.35:
                a = random.uniform(0, math.pi * 2)
                r = self.ring_radius * self.ring_scale
                self.particles.append(self._spark(
                    self.x + math.cos(a) * r,
                    self.y + math.sin(a) * r,
                    speed=random.uniform(0.5, 1.5), life=0.6,
                    size=random.randint(2, 4), kind='spark'))
            if self.timer >= dur:
                self._next_phase()

        elif self.phase == self.PHASE_ACTIVATING:
            self.ring_scale = 1.0
            self._chevron_flash = 1.0
            self._update_kawoosh(progress)
            if self.timer >= dur:
                self._next_phase()

        elif self.phase == self.PHASE_OPEN:
            self.ring_scale = 1.0
            if not self.boss_spawned:
                self.boss_spawned = True
                result = "spawn_boss"
            # Gentle shimmer particles from horizon
            if random.random() < 0.3:
                a = random.uniform(0, math.pi * 2)
                r = random.uniform(0, self.ring_radius * 0.5)
                self.particles.append(self._spark(
                    self.x + math.cos(a) * r,
                    self.y + math.sin(a) * r,
                    speed=0.3, life=0.8, size=random.randint(2, 5), kind='shimmer'))
            if self.timer >= dur:
                self._next_phase()

        elif self.phase == self.PHASE_HOLDING:
            # Stay open with shimmering event horizon until boss is killed
            self.ring_scale = 1.0
            if random.random() < 0.15:
                a = random.uniform(0, math.pi * 2)
                r = random.uniform(0, self.ring_radius * 0.5)
                self.particles.append(self._spark(
                    self.x + math.cos(a) * r,
                    self.y + math.sin(a) * r,
                    speed=0.2, life=0.6, size=random.randint(2, 4), kind='shimmer'))
            # Occasional tendril to show it's still active
            if random.random() < 0.02:
                self._add_tendril()

        elif self.phase == self.PHASE_CLOSING:
            self.ring_scale = max(0, 1.0 - progress)
            # Implosion: pull particles inward
            if random.random() < 0.4 and self.ring_scale > 0.1:
                a = random.uniform(0, math.pi * 2)
                r = self.ring_radius * self.ring_scale
                self.particles.append(self._spark(
                    self.x + math.cos(a) * r * 1.2,
                    self.y + math.sin(a) * r * 1.2,
                    speed=-1.5, life=0.5, size=random.randint(2, 5), kind='spark',
                    angle=a))
            if self.timer >= dur:
                self.active = False

        # Update tendrils (lightning arcs)
        for t in self._tendrils:
            t['life'] -= 0.06
        self._tendrils = [t for t in self._tendrils if t['life'] > 0]

        # Update particles
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= p.get('decay', 0.025)
        self.particles = [p for p in self.particles if p['life'] > 0]

        return result

    def _update_kawoosh(self, progress):
        """Kawoosh: explosive outward vortex burst → retract → stable horizon."""
        r = self.ring_radius

        if progress < 0.25:
            # === BURST PHASE: unstable vortex explodes outward ===
            burst_p = progress / 0.25
            # Massive particle explosion outward
            num = int(8 * (1 - burst_p) + 2)
            for _ in range(num):
                a = random.uniform(0, math.pi * 2)
                dist = r * 0.3 * burst_p
                spd = random.uniform(4, 10) * (1 - burst_p * 0.6)
                self.particles.append(self._spark(
                    self.x + math.cos(a) * dist,
                    self.y + math.sin(a) * dist,
                    speed=spd, life=0.9, size=random.randint(4, 12),
                    kind='kawoosh', angle=a))
            # Bright white flash particles at center
            if burst_p < 0.5:
                for _ in range(3):
                    a = random.uniform(0, math.pi * 2)
                    self.particles.append(self._spark(
                        self.x, self.y,
                        speed=random.uniform(6, 14), life=0.5,
                        size=random.randint(6, 14), kind='flash', angle=a))
            # Lightning tendrils from ring
            if random.random() < 0.6:
                self._add_tendril()

        elif progress < 0.5:
            # === RETRACT PHASE: vortex pulls back to center ===
            retract_p = (progress - 0.25) / 0.25
            if random.random() < 0.4:
                a = random.uniform(0, math.pi * 2)
                dist = r * (1.0 - retract_p) * 0.8
                self.particles.append(self._spark(
                    self.x + math.cos(a) * dist,
                    self.y + math.sin(a) * dist,
                    speed=-2.0 * retract_p, life=0.6,
                    size=random.randint(3, 8), kind='kawoosh', angle=a))
            if random.random() < 0.3:
                self._add_tendril()

        else:
            # === STABILIZE: event horizon forming, gentle shimmer ===
            if random.random() < 0.25:
                a = random.uniform(0, math.pi * 2)
                dist = random.uniform(0, r * 0.6)
                self.particles.append(self._spark(
                    self.x + math.cos(a) * dist,
                    self.y + math.sin(a) * dist,
                    speed=random.uniform(0.1, 0.5), life=0.8,
                    size=random.randint(2, 5), kind='shimmer'))
            # Occasional edge tendril
            if random.random() < 0.1:
                self._add_tendril()

    def _spark(self, x, y, speed=1, life=1.0, size=4, kind='spark', angle=None):
        """Create a particle dict."""
        if angle is None:
            angle = random.uniform(0, math.pi * 2)
        return {
            'x': x, 'y': y,
            'vx': math.cos(angle) * speed,
            'vy': math.sin(angle) * speed,
            'life': life,
            'size': size,
            'kind': kind,
            'decay': 0.02 if kind == 'shimmer' else 0.03,
        }

    def _add_tendril(self):
        """Add an electric tendril arc on the ring edge."""
        a = random.uniform(0, math.pi * 2)
        span = random.uniform(0.3, 0.8)  # radians of arc
        segs = random.randint(4, 8)
        points = []
        for i in range(segs + 1):
            t = i / segs
            seg_a = a + t * span
            jr = self.ring_radius + random.uniform(-15, 15)
            points.append((
                self.x + math.cos(seg_a) * jr,
                self.y + math.sin(seg_a) * jr))
        self._tendrils.append({'points': points, 'life': 1.0})

    def close(self):
        """Trigger closing animation (called when the linked boss is killed)."""
        if self.phase in (self.PHASE_HOLDING, self.PHASE_OPEN):
            self.phase = self.PHASE_CLOSING
            self.timer = 0

    def get_rect(self):
        """Collision rect for the supergate ring."""
        r = int(self.ring_radius * self.ring_scale)
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    def take_damage(self, amount):
        """Damage the supergate. Returns True if destroyed."""
        self.health -= amount
        self.hit_flash = 6
        if self.health <= 0:
            self.health = 0
            return True
        return False

    def _next_phase(self):
        self.phase += 1
        self.timer = 0

    # ── draw ────────────────────────────────────────────────────────

    def draw(self, surface, camera=None):
        if not self.active or self.ring_scale < 0.01:
            return

        if camera:
            sx, sy = camera.world_to_screen(self.x, self.y)
        else:
            sx, sy = self.x, self.y

        scaled_r = int(self.ring_radius * self.ring_scale)
        if scaled_r < 2:
            return

        margin = 80  # extra space for glow + particles
        sz = scaled_r * 2 + margin * 2
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        c = sz // 2

        # ── Outer glow ──
        glow_alpha = int(60 * self.ring_scale)
        if self.phase == self.PHASE_ACTIVATING:
            dur = self.phase_durations[self.phase]
            prog = min(1.0, self.timer / dur)
            glow_alpha = int((80 + 60 * math.sin(self.pulse * 3)) * min(1.0, prog * 3))
        for gr in range(3):
            r = scaled_r + 10 + gr * 12
            a = max(0, glow_alpha - gr * 18)
            if a > 0 and r > 0:
                pygame.draw.circle(surf, (60, 120, 255, a), (c, c), r, 3)

        # ── Ring image or fallback circles ──
        if self._ring_image and self.ring_scale > 0.05:
            img_size = int(300 * self.ring_scale)
            if img_size > 4:
                scaled_img = pygame.transform.smoothscale(self._ring_image, (img_size, img_size))
                alpha = 255 if self.phase != self.PHASE_CLOSING else int(255 * self.ring_scale)
                scaled_img.set_alpha(alpha)
                # Chevron pulse: brighten during appear phase
                if self.phase == self.PHASE_APPEARING and self._chevron_flash > 0.5:
                    bright = pygame.Surface((img_size, img_size), pygame.SRCALPHA)
                    bright.fill((255, 200, 80, int(40 * self._chevron_flash)))
                    scaled_img.blit(bright, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                img_rect = scaled_img.get_rect(center=(c, c))
                surf.blit(scaled_img, img_rect)
        else:
            alpha = int(220 * self.ring_scale)
            pygame.draw.circle(surf, (80, 140, 255, alpha), (c, c), scaled_r, 5)
            pygame.draw.circle(surf, (140, 200, 255, alpha // 2), (c, c), scaled_r - 6, 2)
            # Chevron dots
            for i in range(9):
                ca = i * (math.pi * 2 / 9)
                cx2 = c + int(math.cos(ca) * scaled_r)
                cy2 = c + int(math.sin(ca) * scaled_r)
                ch_a = int(200 * self._chevron_flash) if self.phase == self.PHASE_APPEARING else 200
                pygame.draw.circle(surf, (255, 180, 40, ch_a), (cx2, cy2), 5)

        # ── Event horizon ──
        if self.phase in (self.PHASE_ACTIVATING, self.PHASE_OPEN, self.PHASE_HOLDING):
            self._draw_event_horizon(surf, c, scaled_r)

        # ── Kawoosh flash (first 25% of activation) ──
        if self.phase == self.PHASE_ACTIVATING:
            dur = self.phase_durations[self.phase]
            kprog = min(1.0, self.timer / dur)
            if kprog < 0.25:
                flash_a = int(180 * (1.0 - kprog / 0.25))
                flash_r = int(scaled_r * (0.5 + kprog * 3))
                if flash_r > 0:
                    pygame.draw.circle(surf, (200, 230, 255, flash_a), (c, c), flash_r)

        # Blit main surface
        surface.blit(surf, (int(sx) - c, int(sy) - c))

        # ── Tendrils (drawn in world/screen space for accuracy) ──
        for t in self._tendrils:
            ta = max(0, int(t['life'] * 220))
            points_screen = []
            for px, py in t['points']:
                if camera:
                    spx, spy = camera.world_to_screen(px, py)
                else:
                    spx, spy = px, py
                points_screen.append((int(spx), int(spy)))
            if len(points_screen) >= 2:
                # Bright core
                pygame.draw.lines(surface, (180, 220, 255, ta), False, points_screen, 2)
                # Outer glow
                ga = max(0, ta // 2)
                pygame.draw.lines(surface, (80, 140, 255, ga), False, points_screen, 5)

        # ── Particles (drawn in world/screen space) ──
        for p in self.particles:
            if camera:
                px, py = camera.world_to_screen(p['x'], p['y'])
            else:
                px, py = p['x'], p['y']
            pa = max(0, int(p['life'] * 220))
            ps = max(1, int(p['size'] * p['life']))
            kind = p.get('kind', 'spark')

            if kind == 'flash':
                # Bright white-blue flash
                if ps > 0:
                    fs = pygame.Surface((ps * 4, ps * 4), pygame.SRCALPHA)
                    pygame.draw.circle(fs, (220, 240, 255, pa), (ps * 2, ps * 2), ps * 2)
                    pygame.draw.circle(fs, (255, 255, 255, min(255, pa + 40)), (ps * 2, ps * 2), ps)
                    surface.blit(fs, (int(px) - ps * 2, int(py) - ps * 2))
            elif kind == 'kawoosh':
                # Blue-white energy blobs
                if ps > 0:
                    fs = pygame.Surface((ps * 3, ps * 3), pygame.SRCALPHA)
                    pygame.draw.circle(fs, (60, 140, 255, pa), (ps * 3 // 2, ps * 3 // 2), ps * 3 // 2)
                    pygame.draw.circle(fs, (180, 220, 255, min(255, pa + 30)),
                                       (ps * 3 // 2, ps * 3 // 2), max(1, ps))
                    surface.blit(fs, (int(px) - ps * 3 // 2, int(py) - ps * 3 // 2))
            elif kind == 'shimmer':
                # Soft blue-cyan shimmer
                if ps > 0:
                    fs = pygame.Surface((ps * 2, ps * 2), pygame.SRCALPHA)
                    flicker = int(math.sin(self.pulse * 4 + px * 0.1) * 30)
                    col_b = min(255, 200 + flicker)
                    pygame.draw.circle(fs, (80, col_b, 255, pa // 2), (ps, ps), ps)
                    surface.blit(fs, (int(px) - ps, int(py) - ps))
            else:
                # Default spark
                if ps > 0:
                    fs = pygame.Surface((ps * 2, ps * 2), pygame.SRCALPHA)
                    pygame.draw.circle(fs, (120, 180, 255, pa), (ps, ps), ps)
                    surface.blit(fs, (int(px) - ps, int(py) - ps))

    def _draw_event_horizon(self, surf, c, scaled_r):
        """Draw the shimmering water-like event horizon disc."""
        dur = self.phase_durations[self.phase]
        progress = min(1.0, self.timer / dur)
        horizon_r = int(scaled_r * 0.78)

        if self.phase == self.PHASE_ACTIVATING:
            if progress < 0.25:
                # Kawoosh outburst — horizon not yet visible
                return
            elif progress < 0.5:
                # Retracting — horizon forming, grows from 0 to full
                form_p = (progress - 0.25) / 0.25
                horizon_r = int(horizon_r * form_p)
            horizon_alpha = int(200 * min(1.0, (progress - 0.25) * 3))
        else:
            horizon_alpha = 200

        if horizon_r < 3:
            return

        # Base disc: dark blue with radial gradient feel
        for layer in range(3):
            lr = horizon_r - layer * int(horizon_r * 0.15)
            if lr < 2:
                break
            la = horizon_alpha - layer * 30
            b_val = min(255, 160 + layer * 30)
            if la > 0:
                pygame.draw.circle(surf, (20 + layer * 15, 60 + layer * 20, b_val, la),
                                   (c, c), lr)

        # Concentric ripple rings (water-like)
        num_ripples = 5
        for i in range(num_ripples):
            phase_off = self.pulse * 2.5 + i * 1.2
            wobble = math.sin(phase_off) * 4
            rr = int(horizon_r * (0.2 + i * 0.16)) + int(wobble)
            rr = max(2, min(rr, horizon_r - 2))
            ra = max(0, int((100 - i * 15) * (horizon_alpha / 200)))
            gb = min(255, 180 + int(math.sin(phase_off * 0.7) * 40))
            pygame.draw.circle(surf, (80, gb, 255, ra), (c, c), rr, 2)

        # Bright center vortex glow
        core_r = max(3, int(horizon_r * 0.25))
        core_pulse = math.sin(self.pulse * 3) * 0.3 + 0.7
        core_a = int(180 * core_pulse * (horizon_alpha / 200))
        pygame.draw.circle(surf, (180, 220, 255, core_a), (c, c), core_r)
        # Inner white hot spot
        hot_r = max(2, int(core_r * 0.5))
        pygame.draw.circle(surf, (230, 245, 255, int(core_a * 0.8)), (c, c), hot_r)
