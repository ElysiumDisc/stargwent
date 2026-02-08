"""
STARGWENT - SPACE SHOOTER EASTER EGG
A simple 1v1 arcade-style space shooter mini-game.
Unlocked after achieving 8 wins in Draft Mode.

Controls:
- WASD or Arrow keys: Move ship (all directions)
- SPACE: Fire weapon
- ESC: Exit to main menu

Scoring:
- Enemy destroyed: 100 pts
- Boss defeated: 1000 pts (Wave 5 final enemy)
- Wave clear bonus: 500 pts
- No damage bonus: 200 pts (per wave, if took no damage)
- Asteroid destroyed: 50 pts
"""

import pygame
import math
import random
import os


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
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rotation += self.rotation_speed

        self.image = pygame.transform.rotate(self.original_image, self.rotation)
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

        # Icon letter
        font = pygame.font.SysFont("Arial", pulse_size, bold=True)
        icon_surf = font.render(self.props['icon'], True, (0, 0, 0))
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
        # Orbit around owner
        self.angle += 0.05
        self.x = self.owner.x + self.owner.width // 2 + math.cos(self.angle) * self.orbit_radius
        self.y = self.owner.y + math.sin(self.angle) * self.orbit_radius

        self.fire_cooldown = max(0, self.fire_cooldown - 1)

        # Auto-target nearest enemy
        if enemies and self.fire_cooldown <= 0:
            nearest = min(enemies, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            if math.hypot(nearest.x - self.x, nearest.y - self.y) < 500:
                self.fire_cooldown = self.fire_rate
                return Laser(self.x, self.y, 1, (100, 255, 100), speed=20)
        return None

    def draw(self, surface):
        """Draw the drone."""
        drone_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.polygon(drone_surf, (100, 255, 100), [(10, 0), (20, 20), (0, 20)])
        pygame.draw.polygon(drone_surf, (255, 255, 255), [(10, 0), (20, 20), (0, 20)], 2)
        surface.blit(drone_surf, (int(self.x - 10), int(self.y - 10)))


class Ship:
    """A spaceship (player or AI)."""
    def __init__(self, x, y, faction, is_player=True, screen_width=1920, screen_height=1080):
        self.x = x
        self.y = y
        self.faction = faction
        self.is_player = is_player
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Stats
        self.max_health = 100
        self.health = self.max_health
        self.max_shields = 100
        self.shields = self.max_shields
        self.shield_hit_timer = 0  # Timer for shield bubble visibility
        self.speed = 8
        self.fire_cooldown = 0
        self.fire_rate = 30  # frames between shots
        
        # Faction-specific weapon types and fire rates
        # Asgard: continuous beam (no cooldown, hold to fire)
        # Tau'ri: missiles (slow fire rate, high damage)
        # Goa'uld: yellow laser (medium)
        # Lucian: pink energy balls (medium)
        # Jaffa: staff blasts (fast fire rate)
        faction_lower = faction.lower()
        self.weapon_type = "laser"  # default
        if faction_lower in ["asgard"]:
            self.weapon_type = "beam"
            self.fire_rate = 240  # 4 second cooldown at 60 FPS
        elif faction_lower in ["tau'ri", "tauri"]:
            self.weapon_type = "missile"
            self.fire_rate = 50  # Slower
        elif faction_lower in ["goa'uld", "goauld"]:
            self.weapon_type = "laser"
            self.fire_rate = 25
        elif faction_lower in ["lucian alliance", "lucian_alliance"]:
            self.weapon_type = "energy_ball"
            self.fire_rate = 35
        elif faction_lower in ["jaffa rebellion", "jaffa_rebellion"]:
            self.weapon_type = "staff"
            self.fire_rate = 28  # Balanced (was 20)
        
        # Faction passive abilities
        self.passive = None
        self.passive_state = {}
        if faction_lower in ["tau'ri", "tauri"]:
            self.passive = "armor_plating"  # -15% incoming damage
        elif faction_lower in ["goa'uld", "goauld"]:
            self.passive = "shield_regen"  # Regen 0.3/frame after 120 frames no hit
            self.passive_state = {"no_hit_timer": 0}
        elif faction_lower in ["asgard"]:
            self.passive = "beam_pierce"  # Beam hits pierce through enemies
        elif faction_lower in ["jaffa rebellion", "jaffa_rebellion"]:
            self.passive = "warriors_fury"  # +2% damage per kill, cap 40%
            self.passive_state = {"kills": 0}
        elif faction_lower in ["lucian alliance", "lucian_alliance"]:
            self.passive = "splash_damage"  # Energy balls deal 40% AoE

        # For beam weapon
        self.beam_active = False
        self.current_beam = None
        self.beam_cooldown = 0  # Cooldown after beam stops
        self.beam_duration_timer = 0
        
        # Ship image
        self.image = None
        self.image_right = None  # Cached right-facing image
        self.image_left = None   # Cached left-facing image
        self.image_up = None     # Cached up-facing image
        self.image_down = None   # Cached down-facing image
        self.facing = (1, 0) if is_player else (-1, 0)  # (dx, dy) tuple
        self.original_size = 120  # Original PNG size
        self.scale_factor = 1.2  # Compact ships for more play area
        self.width = int(self.original_size * self.scale_factor)   # 144
        self.height = int(self.original_size * self.scale_factor)  # 144
        self.load_image()
        
        # Faction colors for lasers
        self.faction_colors = {
            "tau'ri": (0, 150, 255),
            "tauri": (0, 150, 255),
            "goa'uld": (255, 180, 0),
            "goauld": (255, 180, 0),
            "asgard": (0, 255, 255),
            "jaffa rebellion": (255, 100, 50),
            "jaffa_rebellion": (255, 100, 50),
            "lucian alliance": (255, 100, 200),
            "lucian_alliance": (255, 100, 200),
        }
        self.laser_color = self.faction_colors.get(faction.lower(), (255, 255, 255))
        
        # Movement bounds
        self.margin = 60
        
        # AI behavior
        self.ai_target_y = y
        self.ai_decision_timer = 0
    
    def load_image(self):
        """Load faction ship image."""
        # Map faction names to actual file names
        faction_to_file = {
            "tau'ri": "tau'ri_ship.png",
            "tauri": "tau'ri_ship.png",
            "goa'uld": "goa'uld_ship.png",
            "goauld": "goa'uld_ship.png",
            "asgard": "asgard_ship.png",
            "jaffa rebellion": "jaffa_rebellion_ship.png",
            "jaffa_rebellion": "jaffa_rebellion_ship.png",
            "lucian alliance": "lucian_alliance_ship.png",
            "lucian_alliance": "lucian_alliance_ship.png",
        }
        
        # Ship image orientations in the PNG files:
        # - tau'ri: faces UP
        # - goa'uld: no clear direction (symmetrical)
        # - asgard: faces LEFT
        # - jaffa_rebellion: faces LEFT
        # - lucian_alliance: faces UP
        
        faction_lower = self.faction.lower()
        ship_filename = faction_to_file.get(faction_lower)
        
        if not ship_filename:
            # Fallback: try to construct filename
            ship_filename = faction_lower.replace(" ", "_") + "_ship.png"
        
        ship_path = os.path.join("assets", "ships", ship_filename)
        
        try:
            self.image = pygame.image.load(ship_path).convert_alpha()
            
            # Apply rotation/flip based on original orientation and player/AI side
            # Player is on LEFT, needs to face RIGHT (shooting right)
            # AI is on RIGHT, needs to face LEFT (shooting left)
            
            if faction_lower in ["tau'ri", "tauri", "lucian alliance", "lucian_alliance"]:
                # These face UP - rotate to face horizontally
                if self.is_player:
                    # Rotate 90° clockwise (facing right)
                    self.image = pygame.transform.rotate(self.image, -90)
                else:
                    # Rotate 90° counter-clockwise (facing left)
                    self.image = pygame.transform.rotate(self.image, 90)
                    
            elif faction_lower in ["asgard", "jaffa rebellion", "jaffa_rebellion"]:
                # These face LEFT - flip for player only
                if self.is_player:
                    self.image = pygame.transform.flip(self.image, True, False)
                # AI keeps original (facing left)
                    
            elif faction_lower in ["goa'uld", "goauld"]:
                # Symmetrical/no direction - flip for AI to look different
                if not self.is_player:
                    self.image = pygame.transform.flip(self.image, True, False)
            
            # Scale image
            self.image = pygame.transform.smoothscale(self.image, (self.width, self.height))
            # Cache all 4 facing directions
            self.image_right = self.image.copy()
            self.image_left = pygame.transform.flip(self.image, True, False)
            self.image_up = pygame.transform.rotate(self.image_right, 90)
            self.image_down = pygame.transform.rotate(self.image_right, -90)
            # Set initial facing
            if self.facing == (-1, 0):
                self.image = self.image_left

        except (pygame.error, FileNotFoundError) as e:
            print(f"[space_shooter] Could not load ship: {ship_path} - {e}")
            # Fallback: draw a simple ship shape
            self.image = None
    
    def update(self, keys=None):
        """Update ship position and cooldowns."""
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.beam_cooldown > 0:
            self.beam_cooldown -= 1

        # Goa'uld passive: Shield Regeneration
        if self.passive == "shield_regen":
            self.passive_state["no_hit_timer"] = self.passive_state.get("no_hit_timer", 0) + 1
            if self.passive_state["no_hit_timer"] >= 120 and self.shields < self.max_shields:
                self.shields = min(self.max_shields, self.shields + 0.3)

        if self.is_player and keys:
            # Player controls — full WASD / arrow movement
            # Facing is set via set_facing() on KEYDOWN events, not here
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.y -= self.speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.y += self.speed
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.x -= self.speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.x += self.speed

        # Player wraps around screen edges; AI gets clamped normally
        if self.is_player:
            if self.x < -self.width:
                self.x = self.screen_width
            elif self.x > self.screen_width:
                self.x = -self.width
            if self.y < -self.height // 2:
                self.y = self.screen_height + self.height // 2
            elif self.y > self.screen_height + self.height // 2:
                self.y = -self.height // 2
        else:
            self.x = max(self.margin, min(self.screen_width - self.width - self.margin, self.x))
            self.y = max(self.margin, min(self.screen_height - self.margin, self.y))

        # Update beam if active
        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            if self.beam_duration_timer >= 90:  # 1.5 seconds at 60 FPS
                self.stop_beam()

    def set_facing(self, direction):
        """Set the ship facing direction and update sprite. Stops active beam on direction change."""
        if direction == self.facing:
            return
        self.facing = direction
        # Stop beam when changing direction — player must re-fire
        if self.current_beam:
            self.stop_beam()
        # Update sprite image
        img_map = {
            (1, 0): self.image_right,
            (-1, 0): self.image_left,
            (0, -1): self.image_up,
            (0, 1): self.image_down,
        }
        new_img = img_map.get(direction)
        if new_img:
            self.image = new_img

    def update_ai(self, player_ship, asteroids, other_ships=None):
        """Smart AI update - aims at player, dodges asteroids and other ships."""
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.beam_cooldown > 0:
            self.beam_cooldown -= 1

        # Goa'uld passive: Shield Regeneration (also works for AI)
        if self.passive == "shield_regen":
            self.passive_state["no_hit_timer"] = self.passive_state.get("no_hit_timer", 0) + 1
            if self.passive_state["no_hit_timer"] >= 120 and self.shields < self.max_shields:
                self.shields = min(self.max_shields, self.shields + 0.3)
        
        # AI targeting - try to align with player's Y position
        target_y = player_ship.y
        
        # Check for incoming asteroids from all directions and dodge closest threat
        dodge_direction = 0
        closest_threat_dist = float('inf')
        for asteroid in asteroids:
            dx = asteroid.x - self.x
            dy = asteroid.y - self.y
            dist = math.hypot(dx, dy)
            threat_radius = asteroid.size + self.height // 2 + 50

            if dist < 400 and dist < closest_threat_dist:
                # Check if asteroid is actually heading toward us
                # Project future position
                future_x = asteroid.x + asteroid.vx * 30
                future_y = asteroid.y + asteroid.vy * 30
                future_dist = math.hypot(future_x - self.x, future_y - self.y)

                if future_dist < dist and dist < threat_radius + 200:
                    closest_threat_dist = dist
                    # Dodge perpendicular to asteroid movement
                    if abs(asteroid.vx) > abs(asteroid.vy):
                        # Asteroid moving mostly horizontally - dodge vertically
                        dodge_direction = -1 if asteroid.y > self.y else 1
                    else:
                        # Asteroid moving mostly vertically - still dodge vertically
                        # (AI can only move up/down)
                        dodge_direction = -1 if asteroid.vy > 0 else 1
        
        # Separation logic (avoid stacking)
        separation_force = 0
        if other_ships:
            for other in other_ships:
                if other == self:
                    continue
                
                dist_y = self.y - other.y
                if abs(dist_y) < 100:  # Too close vertically
                    # Push away
                    if dist_y > 0:
                        separation_force += 3
                    else:
                        separation_force -= 3
                    
                    # If exactly on top, push randomly
                    if dist_y == 0:
                        separation_force += random.choice([-3, 3])

        # Apply dodge or pursue player
        if dodge_direction != 0:
            # Dodging asteroid - move faster
            self.y += dodge_direction * self.speed * 1.0
        elif separation_force != 0:
             # Avoiding collision with other ship
             self.y += separation_force
        else:
            # Lazy pursuit — drift toward player, not snap to them
            y_diff = target_y - self.y
            if abs(y_diff) > 30:
                # Slow, capped drift (max ~40% of ship speed)
                move_speed = min(self.speed * 0.35, abs(y_diff) * 0.03)
                self.y += move_speed if y_diff > 0 else -move_speed

            # Also drift on X toward preferred combat range
            preferred_x = self.screen_width * 0.7
            x_diff = preferred_x - self.x
            if abs(x_diff) > 20:
                self.x += min(self.speed * 0.2, abs(x_diff) * 0.02) * (1 if x_diff > 0 else -1)

        # Keep in bounds
        self.x = max(self.screen_width * 0.4, min(self.screen_width - self.margin, self.x))
        self.y = max(self.margin, min(self.screen_height - self.margin, self.y))
        
        # Update beam if active
        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            if self.beam_duration_timer >= 90:  # 1.5 seconds at 60 FPS
                self.stop_beam()

    def get_fury_multiplier(self):
        """Get Jaffa Warrior's Fury damage multiplier."""
        if self.passive == "warriors_fury":
            kills = self.passive_state.get("kills", 0)
            return 1.0 + min(kills * 0.02, 0.40)
        return 1.0

    def fire(self):
        """Fire weapon based on faction type."""
        direction = self.facing  # (dx, dy) tuple
        dx, dy = direction
        # Determine fire origin at the ship edge facing the direction
        if dx == 1:
            fire_x = self.x + self.width
            fire_y = self.y
        elif dx == -1:
            fire_x = self.x
            fire_y = self.y
        elif dy == -1:
            fire_x = self.x + self.width // 2
            fire_y = self.y - self.height // 2
        else:  # dy == 1
            fire_x = self.x + self.width // 2
            fire_y = self.y + self.height // 2

        # Beam weapon is special - it's continuous but has cooldown after use
        if self.weapon_type == "beam":
            if self.beam_cooldown <= 0 and not self.current_beam:
                self.current_beam = ContinuousBeam(self, direction, self.laser_color,
                                                   self.screen_width, self.screen_height)
                self.beam_duration_timer = 0
                # Apply fury multiplier to beam damage
                fury = self.get_fury_multiplier()
                if fury > 1.0:
                    self.current_beam.damage_per_frame *= fury
            return self.current_beam

        # Other weapons have cooldown
        if self.fire_cooldown <= 0:
            self.fire_cooldown = self.fire_rate

            proj = None
            if self.weapon_type == "missile":
                proj = Missile(fire_x, fire_y, direction, self.laser_color)
            elif self.weapon_type == "energy_ball":
                proj = EnergyBall(fire_x, fire_y, direction, self.laser_color)
            elif self.weapon_type == "staff":
                proj = JaffaStaffBlast(fire_x, fire_y, direction, self.laser_color)
            else:  # laser (Goa'uld default)
                proj = Laser(fire_x, fire_y, direction, self.laser_color)

            # Apply Jaffa Warrior's Fury damage bonus
            if proj:
                proj.is_player_proj = self.is_player
                fury = self.get_fury_multiplier()
                if fury > 1.0:
                    proj.damage = int(proj.damage * fury)
            return proj
        return None
    
    def stop_beam(self):
        """Stop the continuous beam weapon and start cooldown."""
        if self.current_beam:
            self.beam_cooldown = self.fire_rate  # Start cooldown (180 frames = 3 sec for Asgard)
        self.current_beam = None
    
    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y - self.height // 2), self.width, self.height)
    
    def take_damage(self, amount, is_asteroid=False):
        """Take damage - asteroids hit shields first, weapons hit health."""
        # Tau'ri passive: Armor Plating - 15% damage reduction
        if self.passive == "armor_plating":
            amount *= 0.85

        if is_asteroid:
            # Asteroids damage shields only and trigger shield bubble effect
            self.shields = max(0, self.shields - amount)
            self.shield_hit_timer = 60  # Show shield bubble for 60 frames (1 second)
            return False  # Asteroids never destroy the ship directly
        else:
            # Weapons damage health
            self.health -= amount
            # Reset Goa'uld shield regen timer on hit
            if self.passive == "shield_regen":
                self.passive_state["no_hit_timer"] = 0
            return self.health <= 0
    
    def draw(self, surface, time_tick=0):
        """Draw the ship with shield effects and health/shield bars."""
        # Decrement shield hit timer
        if self.shield_hit_timer > 0:
            self.shield_hit_timer -= 1

        shield_pct = self.shields / max(self.max_shields, 1)
        bubble_center = (int(self.x + self.width // 2), int(self.y))
        base_radius = int(self.width * 0.55)

        # --- Always-visible subtle shield aura when shields > 0 ---
        if self.shields > 0:
            pulse = math.sin(time_tick * 0.04) * 0.08 + 1.0
            r = int(base_radius * pulse)
            sz = r * 2 + 20
            aura = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = sz // 2

            # Soft rotating hex segments for sci-fi look
            num_segments = 6
            seg_angle_offset = time_tick * 0.02
            for i in range(num_segments):
                angle = seg_angle_offset + i * (math.pi * 2 / num_segments)
                arc_alpha = int(25 * shield_pct + 10)
                ax = c + int(math.cos(angle) * r * 0.9)
                ay = c + int(math.sin(angle) * r * 0.9)
                pygame.draw.circle(aura, (80, 180, 255, arc_alpha), (ax, ay), int(r * 0.35), 1)

            # Thin outer ring
            ring_alpha = int(40 * shield_pct + 15)
            pygame.draw.circle(aura, (100, 200, 255, ring_alpha), (c, c), r, 2)

            surface.blit(aura, (bubble_center[0] - c, bubble_center[1] - c))

        # --- Bright flare on shield hit ---
        if self.shield_hit_timer > 0 and self.shields >= 0:
            visibility = self.shield_hit_timer / 60.0
            flare_r = int(base_radius * (1.0 + visibility * 0.3))
            sz = flare_r * 2 + 30
            flare = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = sz // 2

            # Impact flash — bright expanding ring
            flash_alpha = int(180 * visibility)
            pygame.draw.circle(flare, (150, 220, 255, flash_alpha), (c, c), flare_r, 4)
            # Inner glow
            inner_alpha = int(100 * visibility)
            pygame.draw.circle(flare, (100, 200, 255, inner_alpha), (c, c), int(flare_r * 0.7))
            # Highlight spark (top)
            spark_alpha = int(220 * visibility)
            pygame.draw.circle(flare, (220, 240, 255, spark_alpha), (c, c - int(flare_r * 0.5)), int(flare_r * 0.15))

            # Hex-crack pattern radiating from impact point
            num_cracks = 8
            for i in range(num_cracks):
                angle = (time_tick * 0.01) + i * (math.pi * 2 / num_cracks)
                inner_pt = (c + int(math.cos(angle) * flare_r * 0.5),
                            c + int(math.sin(angle) * flare_r * 0.5))
                outer_pt = (c + int(math.cos(angle) * flare_r * 0.95),
                            c + int(math.sin(angle) * flare_r * 0.95))
                crack_alpha = int(120 * visibility)
                pygame.draw.line(flare, (180, 230, 255, crack_alpha), inner_pt, outer_pt, 2)

            surface.blit(flare, (bubble_center[0] - c, bubble_center[1] - c))

        # Draw ship
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y - self.height // 2)))
        else:
            # Fallback triangle ship pointing in facing direction
            dx, dy = self.facing
            cx = self.x + self.width // 2
            cy = self.y
            hw = self.width // 2
            hh = self.height // 2
            if dx == 1:  # Right
                points = [(cx + hw, cy), (cx - hw, cy - hh), (cx - hw, cy + hh)]
            elif dx == -1:  # Left
                points = [(cx - hw, cy), (cx + hw, cy - hh), (cx + hw, cy + hh)]
            elif dy == -1:  # Up
                points = [(cx, cy - hh), (cx - hw, cy + hh), (cx + hw, cy + hh)]
            else:  # Down
                points = [(cx, cy + hh), (cx - hw, cy - hh), (cx + hw, cy - hh)]
            pygame.draw.polygon(surface, self.laser_color, points)
            pygame.draw.polygon(surface, (255, 255, 255), points, 2)

        # Health bar
        bar_width = self.width
        bar_height = 6
        bar_x = self.x
        health_bar_y = self.y - self.height // 2 - 18

        pygame.draw.rect(surface, (40, 40, 40), (bar_x, health_bar_y, bar_width, bar_height))
        health_pct = self.health / max(self.max_health, 1)
        health_color = (0, 255, 0) if health_pct > 0.5 else (255, 255, 0) if health_pct > 0.25 else (255, 0, 0)
        pygame.draw.rect(surface, health_color, (bar_x, health_bar_y, int(bar_width * health_pct), bar_height))
        pygame.draw.rect(surface, (200, 200, 200), (bar_x, health_bar_y, bar_width, bar_height), 1)

        # Shield bar (below health bar)
        if self.max_shields > 0:
            shield_bar_y = health_bar_y + bar_height + 2
            shield_bar_h = 4
            pygame.draw.rect(surface, (20, 30, 50), (bar_x, shield_bar_y, bar_width, shield_bar_h))
            pygame.draw.rect(surface, (80, 170, 255), (bar_x, shield_bar_y, int(bar_width * shield_pct), shield_bar_h))
            pygame.draw.rect(surface, (100, 180, 255), (bar_x, shield_bar_y, bar_width, shield_bar_h), 1)


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


class StarField:
    """Scrolling starfield background."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.stars = []
        
        for _ in range(100):
            self.stars.append({
                'x': random.randint(0, screen_width),
                'y': random.randint(0, screen_height),
                'speed': random.uniform(0.5, 3),
                'size': random.randint(1, 3),
                'brightness': random.randint(100, 255)
            })
    
    def update(self):
        for star in self.stars:
            star['x'] -= star['speed']
            if star['x'] < 0:
                star['x'] = self.screen_width
                star['y'] = random.randint(0, self.screen_height)
    
    def draw(self, surface):
        for star in self.stars:
            color = (star['brightness'],) * 3
            pygame.draw.circle(surface, color, (int(star['x']), int(star['y'])), star['size'])


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


class SpaceShooterGame:
    """Main space shooter mini-game with waves of enemies."""

    # Scoring constants
    SCORE_ENEMY = 100
    SCORE_BOSS = 1000  # Final wave enemy bonus
    SCORE_WAVE_CLEAR = 500
    SCORE_NO_DAMAGE = 200  # Per wave, if took no damage during wave
    SCORE_ASTEROID = 50

    def __init__(self, screen_width, screen_height, player_faction, ai_faction, session_scores=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.player_faction = player_faction
        self.ai_faction = ai_faction
        # Per-session leaderboard (survives R restarts, resets on exit to menu)
        self.session_scores = session_scores if session_scores is not None else []

        # Game state
        self.running = True
        self.game_over = False
        self.winner = None
        self.exit_to_menu = False

        # Wave system
        self.current_wave = 1
        self.max_waves = 20
        self.wave_complete = False
        self.wave_transition_timer = 0
        self.enemies_defeated = 0

        # Scoring system
        self.score = 0
        self.wave_damage_taken = False  # Track if damage taken this wave
        self.asteroids_destroyed = 0

        # Power-up system
        self.powerups = []
        self.powerup_spawn_timer = 0
        self.powerup_spawn_rate = 400  # frames between spawn chances
        self.active_powerups = {}  # type -> remaining_frames
        self.drones = []  # Active drone swarm
        self.base_fire_rate = None  # Store original fire rate
        self.base_damage_mult = 1.0

        # XP and Level-up system
        self.xp = 0
        self.level = 1
        self.xp_to_next = 100
        self.upgrades = {}  # upgrade_name -> stack count
        self.xp_orbs = []
        self.pending_level_ups = 0
        self.level_up_choices = []  # 3 upgrade options during level-up screen
        self.showing_level_up = False
        self.total_kills = 0
        self.upgrade_drones = []  # Permanent drones from Orbital Defense upgrade
        self.rear_turret_timer = 0

        # Wormhole escape ability
        self.wormhole_cooldown = 0
        self.wormhole_max_cooldown = 480  # 8 seconds at 60 FPS
        self.wormhole_active = False  # True while player is "in transit"
        self.wormhole_transit_timer = 0
        self.wormhole_transit_duration = 30  # 0.5 sec invisible
        self.wormhole_effects = []  # Active WormholeEffect animations
        self.wormhole_exit_x = 0
        self.wormhole_exit_y = 0

        # All faction options for variety
        self.all_factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]
        
        # Create player ship
        self.player_ship = Ship(
            100, screen_height // 2,
            player_faction, is_player=True,
            screen_width=screen_width, screen_height=screen_height
        )
        
        # Create enemy ships (starts with 1, adds more each wave)
        self.ai_ships = []
        self.spawn_wave_enemies()
        
        # Projectiles and effects
        self.projectiles = []
        self.explosions = []
        self.asteroids = []
        self.starfield = StarField(screen_width, screen_height)
        
        # Asteroid spawning (scales with wave in update)
        self.asteroid_spawn_timer = 0
        self.asteroid_spawn_rate = 600  # starts slow, speeds up with waves
        
        # Player beam state (for Asgard continuous beam)
        self.player_firing = False
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.ui_font = pygame.font.SysFont("Arial", 32)
        self.small_font = pygame.font.SysFont("Arial", 24)
        self.tiny_font = pygame.font.SysFont("Arial", 14, bold=True)
        self.card_key_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.card_icon_font = pygame.font.SysFont("Arial", 40, bold=True)
        self.card_name_font = pygame.font.SysFont("Arial", 20, bold=True)
        self.card_desc_font = pygame.font.SysFont("Arial", 16)
        self.card_stack_font = pygame.font.SysFont("Arial", 18)
        self.count_font = pygame.font.SysFont("Arial", 11, bold=True)
        
        # Hit flash effect
        self.player_hit_flash = 0
    
    # Enemy type modifiers: (speed_mult, hp_mult, scale, xp_value, tint)
    ENEMY_TYPES = {
        "regular": {"speed": 1.0, "hp": 1.0, "scale": 1.0, "xp": 20, "tint": None},
        "fast":    {"speed": 1.5, "hp": 0.7, "scale": 0.9, "xp": 25, "tint": (100, 200, 255)},
        "tank":    {"speed": 0.6, "hp": 2.5, "scale": 1.3, "xp": 35, "tint": (150, 150, 150)},
        "elite":   {"speed": 1.2, "hp": 2.0, "scale": 1.1, "xp": 50, "tint": (255, 215, 0)},
    }

    def _get_wave_enemy_types(self):
        """Determine which enemy types to spawn based on current wave."""
        wave = self.current_wave
        types = ["regular"]
        weights = [60]
        if wave >= 4:
            types.append("fast")
            weights.append(25)
        if wave >= 8:
            types.append("tank")
            weights.append(20)
        if wave >= 13:
            types.append("elite")
            weights.append(15)
        return types, weights

    def spawn_wave_enemies(self):
        """Spawn enemies for the current wave with scaling difficulty.

        Difficulty scales with BOTH wave number and player level so the game
        starts easy and ramps up as the player gains power through upgrades.
        """
        self.ai_ships = []
        wave = self.current_wave

        # Boss waves at 5, 10, 15 and final boss at 20
        is_boss_wave = wave in (5, 10, 15, 20)

        # Power factor: blends wave progression with player level
        # Early waves are gentle; difficulty catches up as player levels
        power = (wave * 0.6 + self.level * 0.4)

        # Enemy count: starts at 1-2, grows with power
        num_enemies = max(1, int(1 + power * 0.8))

        if is_boss_wave:
            num_enemies = max(1, num_enemies // 2)  # Fewer mobs on boss waves

        # Scaling multipliers — gentle curve tied to power
        hp_mult = 1.0 + (power - 1) * 0.10
        speed_mult = 1.0 + (power - 1) * 0.03
        fire_rate_mult = max(0.5, 1.0 - (power - 1) * 0.02)

        # Get available enemy types for this wave
        types, weights = self._get_wave_enemy_types()

        # Generate positions with minimum separation
        min_spacing = 90
        margin = 100
        usable_height = self.screen_height - 2 * margin

        y_positions = []
        for i in range(num_enemies):
            attempts = 0
            while attempts < 50:
                y_pos = random.randint(margin, self.screen_height - margin)
                valid = all(abs(y_pos - ey) >= min_spacing for ey in y_positions)
                if valid:
                    y_positions.append(y_pos)
                    break
                attempts += 1
            else:
                spacing = usable_height // (num_enemies + 1)
                y_positions.append(margin + spacing * (i + 1))

        for i, y_pos in enumerate(y_positions):
            enemy_faction = random.choice([f for f in self.all_factions if f != self.player_faction])
            enemy_type = random.choices(types, weights=weights)[0]
            mods = self.ENEMY_TYPES[enemy_type]

            ship = Ship(
                self.screen_width - 250 - (i % 4) * 40,
                y_pos,
                enemy_faction, is_player=False,
                screen_width=self.screen_width, screen_height=self.screen_height
            )

            # Apply wave scaling
            ship.max_health = int(ship.max_health * hp_mult * mods["hp"])
            ship.health = ship.max_health
            ship.speed = int(ship.speed * speed_mult * mods["speed"])
            ship.fire_rate = max(5, int(ship.fire_rate * fire_rate_mult))

            # Scale ship visual for tanks
            if mods["scale"] != 1.0 and ship.image:
                new_w = int(ship.width * mods["scale"])
                new_h = int(ship.height * mods["scale"])
                ship.image = pygame.transform.smoothscale(ship.image, (new_w, new_h))
                ship.width = new_w
                ship.height = new_h

            # Apply gold tint for elites
            if mods["tint"] and ship.image:
                tint_surf = pygame.Surface(ship.image.get_size(), pygame.SRCALPHA)
                tint_surf.fill((*mods["tint"], 60))
                ship.image.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            ship.xp_value = mods["xp"]
            ship.enemy_type = enemy_type
            ship.ai_fire_timer = random.randint(0, 60)
            self.ai_ships.append(ship)

        # Spawn boss on boss waves
        if is_boss_wave:
            self._spawn_boss(wave)

    def _spawn_boss(self, wave):
        """Spawn a boss enemy for boss waves."""
        boss_faction = random.choice([f for f in self.all_factions if f != self.player_faction])
        boss = Ship(
            self.screen_width - 300,
            self.screen_height // 2,
            boss_faction, is_player=False,
            screen_width=self.screen_width, screen_height=self.screen_height
        )

        # Boss HP scales by wave — gentle early, tough late
        boss_hp_table = {5: 2.0, 10: 4.0, 15: 7.0, 20: 15.0}
        hp_scale = boss_hp_table.get(wave, 3.0)
        boss.max_health = int(100 * hp_scale)
        boss.health = boss.max_health
        boss.max_shields = int(100 * hp_scale * 0.5)
        boss.shields = boss.max_shields

        # Boss is bigger than normal enemies but not huge
        scale = 1.3 if wave < 20 else 1.6
        if boss.image:
            new_w = int(boss.width * scale)
            new_h = int(boss.height * scale)
            boss.image = pygame.transform.smoothscale(boss.image, (new_w, new_h))
            boss.width = new_w
            boss.height = new_h

        # Red tint for bosses
        if boss.image:
            tint = pygame.Surface(boss.image.get_size(), pygame.SRCALPHA)
            tint.fill((255, 50, 50, 40))
            boss.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        boss.fire_rate = max(10, boss.fire_rate // 2)  # Bosses fire faster
        boss.xp_value = 200
        boss.enemy_type = "boss"
        boss.is_boss = True
        boss.ai_fire_timer = 0

        # Wave 20 final boss: multi-phase (fires different patterns at HP thresholds)
        if wave == 20:
            boss.xp_value = 500

        self.ai_ships.append(boss)

    def handle_event(self, event):
        """Handle pygame events."""
        # Handle level-up selection input
        if self.showing_level_up and self.level_up_choices:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.exit_to_menu = True
                    self.running = False
                    return
                # Keys 1/2/3 to select
                key_map = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
                idx = key_map.get(event.key)
                if idx is not None and idx < len(self.level_up_choices):
                    self._select_upgrade(self.level_up_choices[idx])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check click on level-up cards
                if hasattr(self, '_level_up_card_rects'):
                    for i, rect in enumerate(self._level_up_card_rects):
                        if rect.collidepoint(event.pos) and i < len(self.level_up_choices):
                            self._select_upgrade(self.level_up_choices[i])
                            break
            return  # Don't process other input during level-up

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.exit_to_menu = True
                self.running = False
            elif event.key == pygame.K_SPACE and not self.game_over:
                self.player_firing = True
                # For non-beam weapons, fire immediately
                if self.player_ship.weapon_type != "beam":
                    projectile = self.player_ship.fire()
                    if projectile:
                        self.projectiles.append(projectile)
            elif event.key == pygame.K_q and not self.game_over:
                # Wormhole escape ability
                if self.wormhole_cooldown <= 0 and not self.wormhole_active:
                    self._activate_wormhole()
            elif event.key == pygame.K_r and self.game_over:
                # Restart game (keep session scores)
                self.__init__(self.screen_width, self.screen_height,
                            self.player_faction, self.ai_faction,
                            session_scores=self.session_scores)
            # Direction keys set facing (last pressed wins)
            elif event.key in (pygame.K_w, pygame.K_UP) and not self.game_over:
                self.player_ship.set_facing((0, -1))
            elif event.key in (pygame.K_s, pygame.K_DOWN) and not self.game_over:
                self.player_ship.set_facing((0, 1))
            elif event.key in (pygame.K_a, pygame.K_LEFT) and not self.game_over:
                self.player_ship.set_facing((-1, 0))
            elif event.key in (pygame.K_d, pygame.K_RIGHT) and not self.game_over:
                self.player_ship.set_facing((1, 0))

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                self.player_firing = False
                self.player_ship.stop_beam()

    def _activate_wormhole(self):
        """Activate the wormhole escape: player vanishes and reappears at a random location."""
        self.wormhole_active = True
        self.wormhole_transit_timer = 0

        # Spawn entry vortex at current player position
        entry_x = self.player_ship.x + self.player_ship.width // 2
        entry_y = self.player_ship.y
        self.wormhole_effects.append(WormholeEffect(entry_x, entry_y, is_entry=True))

        # Pick a random exit location (with margin so player doesn't land offscreen)
        margin = 100
        self.wormhole_exit_x = random.randint(margin, self.screen_width - margin)
        self.wormhole_exit_y = random.randint(margin, self.screen_height - margin)

    def _save_score(self):
        """Save the score to the per-session leaderboard (not persisted to disk)."""
        import time as time_module
        entry = {
            "score": self.score,
            "waves_cleared": self.current_wave if self.winner == "player" else self.current_wave - 1,
            "enemies_defeated": self.enemies_defeated,
            "won": self.winner == "player",
            "faction": self.player_faction,
            "timestamp": time_module.time(),
        }
        self.session_scores.append(entry)
        self.session_scores.sort(key=lambda x: x["score"], reverse=True)
        # Keep top 10
        if len(self.session_scores) > 10:
            self.session_scores[:] = self.session_scores[:10]
        # Determine rank in session
        self.final_rank = 0
        for i, e in enumerate(self.session_scores):
            if e["timestamp"] == entry["timestamp"] and e["score"] == entry["score"]:
                self.final_rank = i + 1
                break

    def _apply_powerup(self, powerup):
        """Apply the effect of a collected power-up."""
        ptype = powerup.type
        props = powerup.props
        # ZPM Reserves: power-ups last 50% longer per stack
        zpm_mult = 1.0 + self.upgrades.get("zpm_reserves", 0) * 0.5
        duration = int(props["duration"] * zpm_mult) if props["duration"] > 0 else 0

        if ptype == "shield":
            # Instant: +50 shields
            self.player_ship.shields = min(self.player_ship.max_shields,
                                          self.player_ship.shields + 50)
        elif ptype == "rapid_fire":
            # Store original fire rate if not already stored
            if self.base_fire_rate is None:
                self.base_fire_rate = self.player_ship.fire_rate
            self.player_ship.fire_rate = max(5, self.base_fire_rate // 2)
            self.active_powerups["rapid_fire"] = duration
        elif ptype == "drone":
            # Spawn 3 drones
            self.drones = []
            for i in range(3):
                angle = (i * 2 * math.pi / 3)
                self.drones.append(Drone(self.player_ship, angle))
            self.active_powerups["drone"] = duration
        elif ptype == "damage":
            # +25% damage
            self.base_damage_mult = 1.25
            self.active_powerups["damage"] = duration
        elif ptype == "cloak":
            # Player becomes invisible to enemies
            self.active_powerups["cloak"] = duration

    def _expire_powerup(self, ptype):
        """Handle expiration of a power-up effect."""
        if ptype == "rapid_fire":
            if self.base_fire_rate is not None:
                self.player_ship.fire_rate = self.base_fire_rate
        elif ptype == "drone":
            self.drones = []
        elif ptype == "damage":
            self.base_damage_mult = 1.0
        elif ptype == "cloak":
            pass  # Just expires, no special handling

    def is_cloaked(self):
        """Check if player is currently cloaked."""
        return self.active_powerups.get("cloak", 0) > 0

    def _on_enemy_killed(self, ai_ship):
        """Handle bookkeeping when an enemy is killed by the player."""
        self.explosions.append(Explosion(ai_ship.x + ai_ship.width // 2, ai_ship.y))
        if ai_ship in self.ai_ships:
            self.ai_ships.remove(ai_ship)
        self.enemies_defeated += 1
        self.total_kills += 1
        # Track kills for Jaffa Warrior's Fury passive
        if self.player_ship.passive == "warriors_fury":
            self.player_ship.passive_state["kills"] = self.player_ship.passive_state.get("kills", 0) + 1
        # Spawn XP orb at enemy position
        xp_value = getattr(ai_ship, 'xp_value', 20)
        self.xp_orbs.append(XPOrb(ai_ship.x + ai_ship.width // 2, ai_ship.y, xp_value))
        # Award score - bosses give bonus
        if getattr(ai_ship, 'is_boss', False):
            self.score += self.SCORE_BOSS
        else:
            self.score += self.SCORE_ENEMY
        # Check if wave complete
        if len(self.ai_ships) == 0:
            self.wave_complete = True
            self.score += self.SCORE_WAVE_CLEAR
            if not self.wave_damage_taken:
                self.score += self.SCORE_NO_DAMAGE
            self.wave_damage_taken = False

    def _gain_xp(self, amount):
        """Add XP and check for level-ups."""
        # Tractor Beam upgrade increases collection radius (handled in update)
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(100 * 1.3 ** (self.level - 1))
            self.pending_level_ups += 1

    # Upgrade definitions: name -> {display_name, description, max_stacks, icon}
    UPGRADES = {
        "naquadah_plating": {
            "name": "Naquadah Plating",
            "desc": "+20 max HP, heal 20",
            "max": 5, "icon": "+", "color": (200, 50, 50)
        },
        "weapons_power": {
            "name": "Weapons Power",
            "desc": "+15% projectile damage",
            "max": 5, "icon": "W", "color": (255, 100, 50)
        },
        "rapid_capacitors": {
            "name": "Rapid Capacitors",
            "desc": "-10% fire cooldown",
            "max": 5, "icon": ">>", "color": (255, 200, 50)
        },
        "sublight_engines": {
            "name": "Sublight Engines",
            "desc": "+1 ship speed",
            "max": 5, "icon": "^", "color": (50, 200, 255)
        },
        "multi_targeting": {
            "name": "Multi-Targeting",
            "desc": "+1 extra projectile",
            "max": 5, "icon": "|||", "color": (255, 150, 200)
        },
        "shield_harmonics": {
            "name": "Shield Harmonics",
            "desc": "+20 max shields\n+0.1 shield regen",
            "max": 5, "icon": "O", "color": (100, 150, 255)
        },
        "tractor_beam": {
            "name": "Tractor Beam",
            "desc": "+50% XP orb range",
            "max": 5, "icon": "@", "color": (100, 255, 100)
        },
        "orbital_defense": {
            "name": "Orbital Defense",
            "desc": "+1 orbiting drone\n(max 3)",
            "max": 3, "icon": "D", "color": (150, 255, 150)
        },
        "rear_turret": {
            "name": "Rear Turret",
            "desc": "Auto-fire backward",
            "max": 5, "icon": "<", "color": (255, 255, 100)
        },
        "zpm_reserves": {
            "name": "ZPM Reserves",
            "desc": "Power-ups last\n50% longer",
            "max": 5, "icon": "Z", "color": (200, 100, 255)
        },
        "sarcophagus": {
            "name": "Sarcophagus",
            "desc": "Heal 5 HP/sec",
            "max": 5, "icon": "H", "color": (255, 100, 100)
        },
        "targeting_computer": {
            "name": "Targeting Computer",
            "desc": "Projectiles gain\nslight homing",
            "max": 5, "icon": "T", "color": (200, 200, 255)
        },
    }

    def _prepare_level_up_choices(self):
        """Prepare 3 random upgrade choices for level-up selection."""
        available = [
            name for name, info in self.UPGRADES.items()
            if self.upgrades.get(name, 0) < info["max"]
        ]
        random.shuffle(available)
        self.level_up_choices = available[:3]

    def _select_upgrade(self, upgrade_name):
        """Apply the selected upgrade and resume gameplay."""
        self.upgrades[upgrade_name] = self.upgrades.get(upgrade_name, 0) + 1
        stacks = self.upgrades[upgrade_name]
        ship = self.player_ship

        if upgrade_name == "naquadah_plating":
            ship.max_health += 20
            ship.health = min(ship.max_health, ship.health + 20)
        elif upgrade_name == "weapons_power":
            pass  # Applied dynamically in projectile creation
        elif upgrade_name == "rapid_capacitors":
            ship.fire_rate = max(5, int(ship.fire_rate * 0.9))
        elif upgrade_name == "sublight_engines":
            ship.speed += 1
        elif upgrade_name == "multi_targeting":
            pass  # Applied dynamically in fire logic
        elif upgrade_name == "shield_harmonics":
            ship.max_shields += 20
            ship.shields = min(ship.max_shields, ship.shields + 20)
        elif upgrade_name == "tractor_beam":
            pass  # Applied dynamically in XP orb collection
        elif upgrade_name == "orbital_defense":
            # Spawn a new drone
            angle = len(self.upgrade_drones) * (2 * math.pi / 3)
            self.upgrade_drones.append(Drone(ship, angle))
        elif upgrade_name == "rear_turret":
            pass  # Applied dynamically in update
        elif upgrade_name == "zpm_reserves":
            pass  # Applied when power-ups are collected
        elif upgrade_name == "sarcophagus":
            pass  # Applied in update
        elif upgrade_name == "targeting_computer":
            pass  # Applied in projectile update

        self.pending_level_ups -= 1
        if self.pending_level_ups > 0:
            self._prepare_level_up_choices()
        else:
            self.showing_level_up = False
            self.level_up_choices = []

    def _apply_splash_damage(self, x, y, damage, source_ship):
        """Apply Lucian Alliance splash damage to nearby enemies."""
        splash_radius = 60
        splash_damage = damage * 0.4
        for ai_ship in self.ai_ships[:]:
            dist = math.hypot(ai_ship.x + ai_ship.width // 2 - x, ai_ship.y - y)
            if dist < splash_radius:
                ai_ship.hit_flash = 5
                if ai_ship.take_damage(splash_damage):
                    self._on_enemy_killed(ai_ship)

    def update(self):
        """Update game state."""
        # Pause game during level-up selection
        if self.showing_level_up:
            return

        # Handle wave transition
        if self.wave_complete:
            self.wave_transition_timer += 1
            if self.wave_transition_timer >= 180:  # 3 second rest between waves
                self.current_wave += 1
                if self.current_wave > self.max_waves:
                    self.game_over = True
                    self.winner = "player"
                    self._save_score()
                else:
                    self.spawn_wave_enemies()
                    self.wave_complete = False
                    self.wave_transition_timer = 0
            # Update explosions and XP orbs during transition
            self.explosions = [e for e in self.explosions if e.update()]
            collection_radius = 30 + self.upgrades.get("tractor_beam", 0) * 15
            player_cx = self.player_ship.x + self.player_ship.width // 2
            player_cy = self.player_ship.y
            for orb in self.xp_orbs[:]:
                xp_gained = orb.update(player_cx, player_cy, collection_radius)
                if xp_gained > 0:
                    self._gain_xp(xp_gained)
                if not orb.active:
                    self.xp_orbs.remove(orb)
            self.starfield.update()
            return
        
        if self.game_over:
            self.explosions = [e for e in self.explosions if e.update()]
            return
        
        keys = pygame.key.get_pressed()
        
        # Update player ship
        if not self.wormhole_active:
            self.player_ship.update(keys)

        # Wormhole cooldown tick
        if self.wormhole_cooldown > 0:
            self.wormhole_cooldown -= 1

        # Wormhole transit logic
        if self.wormhole_active:
            self.wormhole_transit_timer += 1
            halfway = self.wormhole_transit_duration // 2

            if self.wormhole_transit_timer == halfway:
                # Teleport player to exit location mid-transit
                self.player_ship.x = self.wormhole_exit_x - self.player_ship.width // 2
                self.player_ship.y = self.wormhole_exit_y
                # Spawn exit vortex
                self.wormhole_effects.append(
                    WormholeEffect(self.wormhole_exit_x, self.wormhole_exit_y, is_entry=False))

            if self.wormhole_transit_timer >= self.wormhole_transit_duration:
                # Transit complete — player reappears
                self.wormhole_active = False
                self.wormhole_cooldown = self.wormhole_max_cooldown

        # Update wormhole vortex animations
        self.wormhole_effects = [e for e in self.wormhole_effects if e.update()]

        # Upgrade effects: Sarcophagus passive healing (5 HP/sec = 5/60 per frame)
        sarc_stacks = self.upgrades.get("sarcophagus", 0)
        if sarc_stacks > 0:
            heal_rate = sarc_stacks * 5.0 / 60.0
            self.player_ship.health = min(self.player_ship.max_health,
                                          self.player_ship.health + heal_rate)

        # Upgrade effects: Shield Harmonics passive regen
        shield_stacks = self.upgrades.get("shield_harmonics", 0)
        if shield_stacks > 0:
            regen = shield_stacks * 0.1
            self.player_ship.shields = min(self.player_ship.max_shields,
                                           self.player_ship.shields + regen)

        # Upgrade effects: Rear Turret auto-fire
        rear_stacks = self.upgrades.get("rear_turret", 0)
        if rear_stacks > 0:
            self.rear_turret_timer += 1
            if self.rear_turret_timer >= max(20, 40 - rear_stacks * 5):
                self.rear_turret_timer = 0
                fdx, fdy = self.player_ship.facing
                rear_dir = (-fdx, -fdy)  # Opposite of facing
                rdx, rdy = rear_dir
                if rdx == -1:
                    rear_x, rear_y = self.player_ship.x, self.player_ship.y
                elif rdx == 1:
                    rear_x, rear_y = self.player_ship.x + self.player_ship.width, self.player_ship.y
                elif rdy == -1:
                    rear_x = self.player_ship.x + self.player_ship.width // 2
                    rear_y = self.player_ship.y - self.player_ship.height // 2
                else:
                    rear_x = self.player_ship.x + self.player_ship.width // 2
                    rear_y = self.player_ship.y + self.player_ship.height // 2
                rear_proj = Laser(rear_x, rear_y, rear_dir,
                                  self.player_ship.laser_color, speed=12)
                rear_proj.damage = 8
                self.projectiles.append(rear_proj)

        # Upgrade effects: Orbital Defense drones
        for drone in self.upgrade_drones:
            proj = drone.update(self.ai_ships)
            if proj:
                self.projectiles.append(proj)

        # Update all AI ships with smart behavior
        for ai_ship in self.ai_ships:
            ai_ship.update_ai(self.player_ship, self.asteroids, self.ai_ships)

            # AI firing - but not if player is cloaked!
            if self.is_cloaked():
                # Stop any active beams when player cloaks
                ai_ship.stop_beam()
                continue  # Skip firing logic

            if not hasattr(ai_ship, 'ai_fire_timer'):
                ai_ship.ai_fire_timer = 0
            ai_ship.ai_fire_timer -= 1
            y_diff = abs(ai_ship.y - self.player_ship.y)

            # Handle beam weapons - continuous fire when aligned
            if ai_ship.weapon_type == "beam":
                if y_diff < 80:
                    if not ai_ship.current_beam:
                        ai_ship.fire()
                else:
                    ai_ship.stop_beam()
            else:
                # Regular projectile weapons
                if ai_ship.ai_fire_timer <= 0 and y_diff < 150:
                    projectile = ai_ship.fire()
                    if projectile:
                        self.projectiles.append(projectile)
                    # Boss multi-phase: fire more aggressively at low HP
                    if getattr(ai_ship, 'is_boss', False):
                        hp_pct = ai_ship.health / ai_ship.max_health
                        if hp_pct < 0.25:
                            # Desperate phase: burst fire + spread
                            ai_ship.ai_fire_timer = random.randint(5, 15)
                            for offset in [-40, 40]:
                                extra = ai_ship.fire()
                                if extra is None:
                                    fire_x = ai_ship.x
                                    extra = Laser(fire_x, ai_ship.y + offset, -1,
                                                  ai_ship.laser_color, speed=16)
                                    extra.damage = 10
                                extra.is_player_proj = False
                                self.projectiles.append(extra)
                        elif hp_pct < 0.50:
                            ai_ship.ai_fire_timer = random.randint(10, 25)
                        elif hp_pct < 0.75:
                            ai_ship.ai_fire_timer = random.randint(15, 40)
                        else:
                            ai_ship.ai_fire_timer = random.randint(20, 50)
                    else:
                        # Normal enemies: fire slower early, faster late
                        base_min = max(30, 80 - self.current_wave * 3)
                        base_max = max(60, 140 - self.current_wave * 4)
                        ai_ship.ai_fire_timer = random.randint(base_min, base_max)
        
        # Player continuous firing
        if self.player_firing:
            if self.player_ship.weapon_type == "beam":
                if not self.player_ship.current_beam:
                    beam = self.player_ship.fire()
                    # Apply Weapons Power upgrade to beam
                    if beam:
                        wp_stacks = self.upgrades.get("weapons_power", 0)
                        if wp_stacks > 0:
                            beam.damage_per_frame *= (1.0 + wp_stacks * 0.15)
            else:
                projectile = self.player_ship.fire()
                if projectile:
                    # Apply damage multiplier from power-ups and Weapons Power upgrade
                    wp_mult = 1.0 + self.upgrades.get("weapons_power", 0) * 0.15
                    projectile.damage = int(projectile.damage * self.base_damage_mult * wp_mult)
                    self.projectiles.append(projectile)
                    # Multi-Targeting: fire extra projectiles at spread angles
                    mt_stacks = self.upgrades.get("multi_targeting", 0)
                    if mt_stacks > 0 and not isinstance(projectile, ContinuousBeam):
                        fdx, fdy = self.player_ship.facing
                        for i in range(1, mt_stacks + 1):
                            for angle_sign in [1, -1]:
                                spread = angle_sign * i * 8  # 8 degree spread per extra
                                extra = self.player_ship.fire()
                                if extra is None:
                                    # Force create a copy-like projectile
                                    d = self.player_ship.facing
                                    # Fire from ship edge in facing direction
                                    if fdx == 1:
                                        fx = self.player_ship.x + self.player_ship.width
                                        fy = self.player_ship.y
                                    elif fdx == -1:
                                        fx = self.player_ship.x
                                        fy = self.player_ship.y
                                    elif fdy == -1:
                                        fx = self.player_ship.x + self.player_ship.width // 2
                                        fy = self.player_ship.y - self.player_ship.height // 2
                                    else:
                                        fx = self.player_ship.x + self.player_ship.width // 2
                                        fy = self.player_ship.y + self.player_ship.height // 2
                                    extra = type(projectile)(fx, fy, d,
                                                             self.player_ship.laser_color)
                                extra.is_player_proj = True
                                extra.damage = int(extra.damage * self.base_damage_mult * wp_mult)
                                # Offset perpendicular to facing direction
                                offset = math.tan(math.radians(spread)) * 50
                                if abs(fdx) > 0:  # Horizontal facing: spread on Y
                                    extra.y += offset
                                else:  # Vertical facing: spread on X
                                    extra.x += offset
                                self.projectiles.append(extra)
        
        # Spawn asteroids — spawn rate increases with wave (600 → ~200 by wave 20)
        effective_asteroid_rate = max(200, 600 - self.current_wave * 20)
        self.asteroid_spawn_timer += 1
        if self.asteroid_spawn_timer >= effective_asteroid_rate:
            self.asteroid_spawn_timer = 0
            # Weighted random direction: 35% right, 25% left, 20% top, 20% bottom
            direction = random.choices(
                ["right", "left", "top", "bottom"],
                weights=[35, 25, 20, 20]
            )[0]
            self.asteroids.append(Asteroid(self.screen_width, self.screen_height, direction))

        # Update asteroids
        for asteroid in self.asteroids[:]:
            asteroid.update()
            if not asteroid.active:
                self.asteroids.remove(asteroid)

        # Spawn power-ups
        self.powerup_spawn_timer += 1
        if self.powerup_spawn_timer >= self.powerup_spawn_rate:
            self.powerup_spawn_timer = 0
            # Random chance to spawn (50% total, distributed by weight)
            if random.random() < 0.5:
                self.powerups.append(PowerUp.spawn_random(self.screen_width, self.screen_height))

        # Update power-ups
        for powerup in self.powerups[:]:
            powerup.update()
            if not powerup.active:
                self.powerups.remove(powerup)
                continue

            # Check collision with player
            if powerup.get_rect().colliderect(self.player_ship.get_rect()):
                self._apply_powerup(powerup)
                self.powerups.remove(powerup)

        # Update active power-up timers
        expired = []
        for ptype, remaining in self.active_powerups.items():
            if remaining > 0:
                self.active_powerups[ptype] = remaining - 1
                if self.active_powerups[ptype] <= 0:
                    expired.append(ptype)

        for ptype in expired:
            self._expire_powerup(ptype)
            del self.active_powerups[ptype]

        # Update drones
        for drone in self.drones:
            proj = drone.update(self.ai_ships)
            if proj:
                self.projectiles.append(proj)
        
        # Update projectiles
        tc_stacks = self.upgrades.get("targeting_computer", 0)
        for proj in self.projectiles[:]:
            proj.update()

            # Targeting Computer: player projectiles home toward nearest enemy
            if tc_stacks > 0 and proj.is_player_proj and self.ai_ships:
                nearest = min(self.ai_ships,
                              key=lambda e: math.hypot(e.x - proj.x, e.y - proj.y))
                max_adjust = tc_stacks * 2.0
                # Adjust perpendicular to travel direction
                pdx, pdy = proj.direction
                if abs(pdx) > abs(pdy):  # Horizontal projectile: home on Y
                    diff = nearest.y - proj.y
                    if abs(diff) > 1:
                        proj.y += max(-max_adjust, min(max_adjust, diff * 0.05))
                else:  # Vertical projectile: home on X
                    diff = nearest.x - proj.x
                    if abs(diff) > 1:
                        proj.x += max(-max_adjust, min(max_adjust, diff * 0.05))

            if proj.x < -100 or proj.x > self.screen_width + 100 or proj.y < -100 or proj.y > self.screen_height + 100:
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                continue
            
            proj_rect = proj.get_rect()
            
            if proj.is_player_proj:  # Player projectile
                # Check collision with all AI ships
                for ai_ship in self.ai_ships[:]:
                    if proj_rect.colliderect(ai_ship.get_rect()):
                        if proj in self.projectiles:
                            self.projectiles.remove(proj)
                        ai_ship.hit_flash = 10
                        hit_x = ai_ship.x + ai_ship.width // 2
                        hit_y = ai_ship.y
                        if ai_ship.take_damage(proj.damage):
                            self._on_enemy_killed(ai_ship)
                        # Lucian Alliance splash damage
                        if self.player_ship.passive == "splash_damage" and isinstance(proj, EnergyBall):
                            self._apply_splash_damage(hit_x, hit_y, proj.damage, self.player_ship)
                        break
            else:  # AI projectile hitting player
                if not self.wormhole_active and proj_rect.colliderect(self.player_ship.get_rect()):
                    if proj in self.projectiles:
                        self.projectiles.remove(proj)
                    self.player_hit_flash = 10
                    self.wave_damage_taken = True  # Track damage for no-damage bonus
                    if self.player_ship.take_damage(proj.damage):
                        self.game_over = True
                        self.winner = "ai"
                        self._save_score()
                        self.explosions.append(Explosion(
                            self.player_ship.x + self.player_ship.width // 2,
                            self.player_ship.y))
                    continue
            
            # Projectile vs asteroids
            for asteroid in self.asteroids[:]:
                if proj_rect.colliderect(asteroid.get_rect()):
                    if proj in self.projectiles:
                        self.projectiles.remove(proj)
                    if asteroid.take_damage(proj.damage):
                        self.explosions.append(Explosion(asteroid.x, asteroid.y))
                        if asteroid in self.asteroids:
                            self.asteroids.remove(asteroid)
                        # Award points for asteroid destruction (player projectiles only)
                        if proj.is_player_proj:
                            self.score += self.SCORE_ASTEROID
                            self.asteroids_destroyed += 1
                            self.xp_orbs.append(XPOrb(asteroid.x, asteroid.y, 10))
                    break
        
        # Check beam collision (supports 4-directional beams)
        if self.player_ship.current_beam:
            beam = self.player_ship.current_beam
            beam_sx, beam_sy = beam.get_start_pos()
            bdx, bdy = beam.direction
            piercing = self.player_ship.passive == "beam_pierce"
            is_horizontal = abs(bdx) > abs(bdy)

            # Collect all targets in beam path with distances
            targets = []
            for ai_ship in self.ai_ships:
                ship_cx = ai_ship.x + ai_ship.width // 2
                ship_cy = ai_ship.y
                if is_horizontal:
                    if abs(ship_cy - beam_sy) < (ai_ship.height // 2 + 10):
                        dist = (ship_cx - beam_sx) * bdx
                        if dist > 0:
                            targets.append((dist, ai_ship, False))
                else:
                    if abs(ship_cx - beam_sx) < (ai_ship.width // 2 + 10):
                        dist = (ship_cy - beam_sy) * bdy
                        if dist > 0:
                            targets.append((dist, ai_ship, False))
            for asteroid in self.asteroids:
                half_s = asteroid.size // 2 + 10
                if is_horizontal:
                    if abs(asteroid.y - beam_sy) < half_s:
                        dist = (asteroid.x - beam_sx) * bdx
                        if dist > 0:
                            targets.append((dist, asteroid, True))
                else:
                    if abs(asteroid.x - beam_sx) < half_s:
                        dist = (asteroid.y - beam_sy) * bdy
                        if dist > 0:
                            targets.append((dist, asteroid, True))

            targets.sort(key=lambda t: t[0])

            # If piercing, hit all targets (50% damage after first); otherwise just closest
            beam_end_dist = self.screen_width if is_horizontal else self.screen_height
            hit_first = False
            for dist, target, is_ast in targets:
                if not piercing and dist > beam_end_dist:
                    break
                # Pierce penalty: targets after the first take half damage
                dmg = beam.damage_per_frame * (0.5 if (piercing and hit_first) else 1.0)
                hit_first = True
                if is_ast:
                    if target.take_damage(dmg):
                        self.explosions.append(Explosion(target.x, target.y))
                        if target in self.asteroids:
                            self.asteroids.remove(target)
                        self.score += self.SCORE_ASTEROID
                        self.asteroids_destroyed += 1
                        self.xp_orbs.append(XPOrb(target.x, target.y, 10))
                    if not piercing:
                        beam_end_dist = dist
                else:
                    target.hit_flash = 3
                    if target.take_damage(dmg):
                        self._on_enemy_killed(target)
                    if not piercing:
                        beam_end_dist = dist

            beam.set_length(beam_end_dist)
        
        # Check AI beam collision with player
        for ai_ship in self.ai_ships:
            if ai_ship.current_beam:
                beam = ai_ship.current_beam
                beam_start_x, _ = beam.get_start_pos()
                
                closest_hit_dist = self.screen_width
                hit_target = None
                is_asteroid = False
                
                # Check player (AI shoots Left, so dist is Start - Target)
                beam_y = ai_ship.y
                if not self.wormhole_active and abs(self.player_ship.y - beam_y) < (self.player_ship.height // 2 + 10):
                    dist = beam_start_x - (self.player_ship.x + self.player_ship.width)
                    if 0 < dist < closest_hit_dist:
                        closest_hit_dist = dist
                        hit_target = self.player_ship
                        is_asteroid = False
                
                # Check asteroids
                for asteroid in self.asteroids:
                    if abs(asteroid.y - beam_y) < (asteroid.size // 2 + 10):
                        dist = beam_start_x - (asteroid.x + asteroid.size//2)
                        if 0 < dist < closest_hit_dist:
                            closest_hit_dist = dist
                            hit_target = asteroid
                            is_asteroid = True
                
                beam.set_length(closest_hit_dist)
                
                if hit_target:
                    if is_asteroid:
                        if hit_target.take_damage(beam.damage_per_frame):
                            self.explosions.append(Explosion(hit_target.x, hit_target.y))
                            if hit_target in self.asteroids:
                                self.asteroids.remove(hit_target)
                    else:
                        self.player_hit_flash = 3
                        self.wave_damage_taken = True  # Track damage
                        if self.player_ship.take_damage(beam.damage_per_frame):
                            self.game_over = True
                            self.winner = "ai"
                            self._save_score()
                            self.explosions.append(Explosion(
                                self.player_ship.x + self.player_ship.width // 2,
                                self.player_ship.y))
        
        # Ship collision with asteroids (damages shields)
        for asteroid in self.asteroids[:]:
            if not self.wormhole_active and asteroid.get_rect().colliderect(self.player_ship.get_rect()):
                self.player_hit_flash = 5
                self.player_ship.take_damage(25, is_asteroid=True)
                self.explosions.append(Explosion(asteroid.x, asteroid.y))
                self.asteroids.remove(asteroid)
                continue
            for ai_ship in self.ai_ships:
                if asteroid.get_rect().colliderect(ai_ship.get_rect()):
                    ai_ship.hit_flash = 5
                    ai_ship.take_damage(25, is_asteroid=True)
                    self.explosions.append(Explosion(asteroid.x, asteroid.y))
                    if asteroid in self.asteroids:
                        self.asteroids.remove(asteroid)
                    break
        
        # Update XP orbs
        collection_radius = 30 + self.upgrades.get("tractor_beam", 0) * 15
        player_cx = self.player_ship.x + self.player_ship.width // 2
        player_cy = self.player_ship.y
        for orb in self.xp_orbs[:]:
            xp_gained = orb.update(player_cx, player_cy, collection_radius)
            if xp_gained > 0:
                self._gain_xp(xp_gained)
            if not orb.active:
                self.xp_orbs.remove(orb)

        # Trigger level-up screen if pending
        if self.pending_level_ups > 0 and not self.showing_level_up:
            self._prepare_level_up_choices()
            self.showing_level_up = True

        # Update background
        self.starfield.update()

        # Update hit flashes
        if self.player_hit_flash > 0:
            self.player_hit_flash -= 1

        # Update explosions
        self.explosions = [e for e in self.explosions if e.update()]
    
    def draw(self, surface):
        """Draw the game."""
        time_tick = pygame.time.get_ticks()
        
        # Background
        surface.fill((5, 5, 20))
        self.starfield.draw(surface)
        
        # Draw asteroids
        for asteroid in self.asteroids:
            asteroid.draw(surface)

        # Draw XP orbs
        for orb in self.xp_orbs:
            orb.draw(surface)

        # Draw power-ups
        for powerup in self.powerups:
            powerup.draw(surface)

        # Draw projectiles
        for proj in self.projectiles:
            proj.draw(surface)
        
        # Draw beam weapons if active
        if self.player_ship.current_beam:
            self.player_ship.current_beam.draw(surface)
        for ai_ship in self.ai_ships:
            if ai_ship.current_beam:
                ai_ship.current_beam.draw(surface)
        
        # Draw player ship (hidden during wormhole transit)
        if not self.game_over or self.winner != "ai":
            if self.wormhole_active:
                pass  # Player is inside the wormhole — invisible
            elif self.player_hit_flash > 0:
                flash_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                self.player_ship.draw(flash_surf, time_tick)
                flash_overlay = pygame.Surface(flash_surf.get_size(), pygame.SRCALPHA)
                flash_overlay.fill((255, 0, 0, 100))
                flash_surf.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(flash_surf, (0, 0))
            else:
                # Apply cloak effect if active
                if self.is_cloaked():
                    cloak_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                    self.player_ship.draw(cloak_surf, time_tick)
                    cloak_surf.set_alpha(100)  # Semi-transparent
                    surface.blit(cloak_surf, (0, 0))
                else:
                    self.player_ship.draw(surface, time_tick)

        # Draw wormhole vortex effects
        for effect in self.wormhole_effects:
            effect.draw(surface)

        # Draw drones (power-up and upgrade)
        for drone in self.drones:
            drone.draw(surface)
        for drone in self.upgrade_drones:
            drone.draw(surface)

        # Draw all AI ships
        for ai_ship in self.ai_ships:
            hit_flash = getattr(ai_ship, 'hit_flash', 0)
            if hit_flash > 0:
                flash_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                ai_ship.draw(flash_surf, time_tick)
                flash_overlay = pygame.Surface(flash_surf.get_size(), pygame.SRCALPHA)
                flash_overlay.fill((255, 0, 0, 100))
                flash_surf.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(flash_surf, (0, 0))
                ai_ship.hit_flash = hit_flash - 1
            else:
                ai_ship.draw(surface, time_tick)
        
        # Draw explosions
        for explosion in self.explosions:
            explosion.draw(surface)
        
        # Draw UI
        self.draw_ui(surface)

        # Draw level-up screen on top of everything
        if self.showing_level_up and self.level_up_choices:
            self._draw_level_up_screen(surface)

    def _draw_level_up_screen(self, surface):
        """Draw the level-up upgrade selection overlay."""
        time_tick = pygame.time.get_ticks()

        # Dark overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        # "LEVEL UP!" text with pulse
        pulse = 1.0 + math.sin(time_tick * 0.005) * 0.1
        title_size = int(64 * pulse)
        title_font = pygame.font.SysFont("Arial", title_size, bold=True)
        title = title_font.render("LEVEL UP!", True, (255, 215, 0))
        surface.blit(title, (self.screen_width // 2 - title.get_width() // 2, 80))

        subtitle = self.ui_font.render(f"Level {self.level} - Choose an upgrade:", True, (200, 200, 200))
        surface.blit(subtitle, (self.screen_width // 2 - subtitle.get_width() // 2, 150))

        # Draw 3 upgrade cards
        card_w, card_h = 200, 280
        spacing = 40
        total_w = len(self.level_up_choices) * card_w + (len(self.level_up_choices) - 1) * spacing
        start_x = (self.screen_width - total_w) // 2
        card_y = (self.screen_height - card_h) // 2

        self._level_up_card_rects = []
        mouse_pos = pygame.mouse.get_pos()

        for i, upgrade_name in enumerate(self.level_up_choices):
            info = self.UPGRADES[upgrade_name]
            x = start_x + i * (card_w + spacing)
            rect = pygame.Rect(x, card_y, card_w, card_h)
            self._level_up_card_rects.append(rect)

            hovered = rect.collidepoint(mouse_pos)
            current_stacks = self.upgrades.get(upgrade_name, 0)

            # Card background
            bg_color = (50, 50, 70) if not hovered else (70, 70, 100)
            pygame.draw.rect(surface, bg_color, rect, border_radius=12)

            # Border with upgrade color
            border_color = info["color"] if hovered else tuple(c // 2 for c in info["color"])
            border_w = 3 if hovered else 2
            pygame.draw.rect(surface, border_color, rect, border_w, border_radius=12)

            # Glow on hover
            if hovered:
                glow = pygame.Surface((card_w + 20, card_h + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*info["color"], 40), (0, 0, card_w + 20, card_h + 20), border_radius=15)
                surface.blit(glow, (x - 10, card_y - 10))

            # Key shortcut indicator
            key_text = self.card_key_font.render(f"[{i + 1}]", True, (180, 180, 180))
            surface.blit(key_text, (x + card_w // 2 - key_text.get_width() // 2, card_y + 8))

            # Icon
            icon_surf = self.card_icon_font.render(info["icon"], True, info["color"])
            surface.blit(icon_surf, (x + card_w // 2 - icon_surf.get_width() // 2, card_y + 35))

            # Name
            name_surf = self.card_name_font.render(info["name"], True, (255, 255, 255))
            surface.blit(name_surf, (x + card_w // 2 - name_surf.get_width() // 2, card_y + 90))

            # Description (multi-line)
            desc_lines = info["desc"].split("\n")
            for j, line in enumerate(desc_lines):
                desc_surf = self.card_desc_font.render(line, True, (180, 180, 180))
                surface.blit(desc_surf, (x + card_w // 2 - desc_surf.get_width() // 2, card_y + 120 + j * 20))

            # Stack indicator
            stack_y = card_y + card_h - 50
            stack_text = f"{current_stacks}/{info['max']}"
            stack_surf = self.card_stack_font.render(stack_text, True, (150, 150, 150))
            surface.blit(stack_surf, (x + card_w // 2 - stack_surf.get_width() // 2, stack_y))

            # Stack pips
            pip_y = stack_y + 25
            pip_total = info["max"]
            pip_w = min(16, (card_w - 40) // pip_total)
            pip_start = x + (card_w - pip_total * pip_w) // 2
            for p in range(pip_total):
                pip_color = info["color"] if p < current_stacks else (60, 60, 80)
                if p == current_stacks:
                    pip_color = (255, 255, 255)  # Next pip highlight
                pygame.draw.rect(surface, pip_color,
                                (pip_start + p * pip_w + 1, pip_y, pip_w - 2, 8), border_radius=2)

    def draw_ui(self, surface):
        """Draw game UI."""
        # Title
        title = self.title_font.render("STARGATE SPACE BATTLE", True, (255, 215, 0))
        surface.blit(title, (self.screen_width // 2 - title.get_width() // 2, 20))

        # Wave info
        wave_text = self.ui_font.render(f"Wave {self.current_wave}/20", True, (255, 200, 100))
        surface.blit(wave_text, (self.screen_width // 2 - wave_text.get_width() // 2, 80))

        # Enemies remaining
        enemies_text = self.small_font.render(f"Enemies: {len(self.ai_ships)}", True, (255, 100, 100))
        surface.blit(enemies_text, (self.screen_width // 2 - enemies_text.get_width() // 2, 115))

        # Score display (top-left)
        score_text = self.ui_font.render(f"SCORE: {self.score:,}", True, (255, 215, 0))
        surface.blit(score_text, (20, 20))

        # Score breakdown hint
        score_hint = self.small_font.render(f"Enemies: {self.enemies_defeated} | Asteroids: {self.asteroids_destroyed}", True, (180, 180, 180))
        surface.blit(score_hint, (20, 55))

        # Kill counter (top-right area)
        kill_text = self.small_font.render(f"Kills: {self.total_kills}", True, (255, 200, 100))
        surface.blit(kill_text, (self.screen_width - kill_text.get_width() - 20, 80))

        # XP bar (below health/shield bars area, left side)
        xp_bar_x = 20
        xp_bar_y = 80
        xp_bar_w = 200
        xp_bar_h = 12
        # Level text
        level_text = self.small_font.render(f"Lv.{self.level}", True, (100, 255, 100))
        surface.blit(level_text, (xp_bar_x, xp_bar_y))
        # XP bar background
        bar_x = xp_bar_x + level_text.get_width() + 8
        pygame.draw.rect(surface, (40, 40, 40), (bar_x, xp_bar_y + 2, xp_bar_w, xp_bar_h))
        # XP bar fill
        xp_pct = self.xp / max(self.xp_to_next, 1)
        pygame.draw.rect(surface, (100, 255, 100), (bar_x, xp_bar_y + 2, int(xp_bar_w * xp_pct), xp_bar_h))
        pygame.draw.rect(surface, (150, 255, 150), (bar_x, xp_bar_y + 2, xp_bar_w, xp_bar_h), 1)

        # Active power-ups indicator (top-right)
        if self.active_powerups:
            powerup_y = 110
            for ptype, remaining in self.active_powerups.items():
                if remaining > 0:
                    props = PowerUp.TYPES.get(ptype, {})
                    name = props.get("name", ptype)
                    duration = props.get("duration", 1)
                    pct = remaining / max(duration, 1)

                    box_width = 150
                    box_height = 30
                    box_x = self.screen_width - box_width - 20

                    pygame.draw.rect(surface, (30, 30, 50),
                                   (box_x, powerup_y, box_width, box_height), border_radius=5)
                    bar_width = int((box_width - 10) * pct)
                    color = props.get("color", (100, 200, 255))
                    pygame.draw.rect(surface, color,
                                   (box_x + 5, powerup_y + 5, bar_width, box_height - 10), border_radius=3)
                    text = self.small_font.render(name, True, (255, 255, 255))
                    surface.blit(text, (box_x + 10, powerup_y + 5))

                    powerup_y += box_height + 5

        # Active upgrades display (bottom of screen, horizontal strip)
        if self.upgrades:
            icon_size = 24
            icon_spacing = 30
            active_upgrades = [(name, count) for name, count in self.upgrades.items() if count > 0]
            total_icons_w = len(active_upgrades) * icon_spacing
            icon_x = (self.screen_width - total_icons_w) // 2
            icon_y = self.screen_height - 65

            # Semi-transparent background strip
            if active_upgrades:
                strip_rect = pygame.Rect(icon_x - 5, icon_y - 3, total_icons_w + 10, icon_size + 14)
                strip_surf = pygame.Surface((strip_rect.width, strip_rect.height), pygame.SRCALPHA)
                strip_surf.fill((0, 0, 0, 80))
                surface.blit(strip_surf, strip_rect.topleft)

            for name, count in active_upgrades:
                info = self.UPGRADES.get(name, {})
                color = info.get("color", (200, 200, 200))
                icon_text = info.get("icon", "?")
                # Draw icon
                icon_surf = self.tiny_font.render(icon_text, True, color)
                surface.blit(icon_surf, (icon_x, icon_y))
                # Stack count
                count_surf = self.count_font.render(str(count), True, (255, 255, 255))
                surface.blit(count_surf, (icon_x + icon_size - 4, icon_y + icon_size - 6))
                icon_x += icon_spacing

        # Player faction label
        player_label = self.ui_font.render(self.player_faction.upper(), True, self.player_ship.laser_color)
        surface.blit(player_label, (50, self.screen_height - 90))

        # Wormhole cooldown indicator (bottom-left, above faction label)
        wh_x = 50
        wh_y = self.screen_height - 130
        if self.wormhole_active:
            wh_label = self.small_font.render("[Q] WORMHOLE  IN TRANSIT", True, (100, 180, 255))
            surface.blit(wh_label, (wh_x, wh_y))
        elif self.wormhole_cooldown > 0:
            cd_pct = self.wormhole_cooldown / self.wormhole_max_cooldown
            bar_w = 140
            bar_h = 10
            # Label
            cd_secs = self.wormhole_cooldown / 60.0
            wh_label = self.small_font.render(f"[Q] WORMHOLE  {cd_secs:.1f}s", True, (120, 120, 150))
            surface.blit(wh_label, (wh_x, wh_y))
            # Cooldown bar
            pygame.draw.rect(surface, (40, 40, 60), (wh_x, wh_y + 25, bar_w, bar_h))
            fill_w = int(bar_w * (1.0 - cd_pct))
            pygame.draw.rect(surface, (80, 140, 255), (wh_x, wh_y + 25, fill_w, bar_h))
            pygame.draw.rect(surface, (100, 160, 255), (wh_x, wh_y + 25, bar_w, bar_h), 1)
        else:
            wh_label = self.small_font.render("[Q] WORMHOLE  READY", True, (100, 200, 255))
            surface.blit(wh_label, (wh_x, wh_y))

        # Controls hint
        controls = self.small_font.render("WASD / Arrows: Move  |  SPACE: Fire  |  Q: Wormhole  |  ESC: Exit", True, (150, 150, 150))
        surface.blit(controls, (self.screen_width // 2 - controls.get_width() // 2, self.screen_height - 30))
        
        # Wave transition message
        if self.wave_complete and not self.game_over:
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            surface.blit(overlay, (0, 0))
            
            if self.current_wave < self.max_waves:
                wave_msg = self.title_font.render(f"WAVE {self.current_wave} COMPLETE!", True, (100, 255, 100))
                next_msg = self.ui_font.render(f"Next wave: {self.current_wave + 1} enemies incoming...", True, (200, 200, 200))
            else:
                wave_msg = self.title_font.render("ALL WAVES COMPLETE!", True, (255, 215, 0))
                next_msg = self.ui_font.render("Preparing victory...", True, (200, 200, 200))
            
            surface.blit(wave_msg, (self.screen_width // 2 - wave_msg.get_width() // 2, self.screen_height // 2 - 50))
            surface.blit(next_msg, (self.screen_width // 2 - next_msg.get_width() // 2, self.screen_height // 2 + 20))
        
        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            surface.blit(overlay, (0, 0))

            if self.winner == "player":
                result_text = "VICTORY!"
                result_color = (255, 215, 0)
                sub_text = f"All {self.max_waves} waves defeated! {self.enemies_defeated} enemies destroyed!"
            else:
                result_text = "DEFEAT"
                result_color = (255, 50, 50)
                sub_text = f"Destroyed on wave {self.current_wave}. {self.enemies_defeated} enemies defeated."

            result_surf = self.title_font.render(result_text, True, result_color)
            sub_surf = self.ui_font.render(sub_text, True, (200, 200, 200))

            # Score display
            score_surf = self.title_font.render(f"SCORE: {self.score:,}", True, (255, 215, 0))

            # Show session rank
            rank_text = ""
            if hasattr(self, 'final_rank') and self.final_rank > 0:
                if self.final_rank == 1:
                    rank_text = "SESSION BEST!"
                else:
                    rank_text = f"Session Rank #{self.final_rank}"
                games_played = len(self.session_scores)
                if games_played > 1:
                    rank_text += f"  ({games_played} games this session)"
            rank_surf = self.ui_font.render(rank_text, True, (100, 255, 100)) if rank_text else None

            restart_surf = self.ui_font.render("Press R to play again or ESC to exit", True, (150, 150, 150))

            y_offset = self.screen_height // 2 - 120
            surface.blit(result_surf, (self.screen_width // 2 - result_surf.get_width() // 2, y_offset))
            y_offset += 70
            surface.blit(score_surf, (self.screen_width // 2 - score_surf.get_width() // 2, y_offset))
            y_offset += 60
            if rank_surf:
                surface.blit(rank_surf, (self.screen_width // 2 - rank_surf.get_width() // 2, y_offset))
                y_offset += 40
            surface.blit(sub_surf, (self.screen_width // 2 - sub_surf.get_width() // 2, y_offset))
            y_offset += 50
            surface.blit(restart_surf, (self.screen_width // 2 - restart_surf.get_width() // 2, y_offset))


class ShipSelectScreen:
    """Ship selection screen before the game."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]
        self.selected_index = 0
        self.ship_previews = []
        self.starfield = StarField(screen_width, screen_height)
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.faction_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.hint_font = pygame.font.SysFont("Arial", 24)
        
        # Load ship previews
        self.load_previews()
        
        # Selection rects for click detection
        self.ship_rects = []
    
    def load_previews(self):
        """Load preview images for all ships."""
        for faction in self.factions:
            ship = Ship(0, 0, faction, is_player=True, 
                       screen_width=self.screen_width, screen_height=self.screen_height)
            self.ship_previews.append({
                'faction': faction,
                'image': ship.image,
                'color': ship.laser_color
            })
    
    def handle_event(self, event):
        """Handle input events. Returns selected faction or None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.selected_index = (self.selected_index - 1) % len(self.factions)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.selected_index = (self.selected_index + 1) % len(self.factions)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                return self.factions[self.selected_index]
            elif event.key == pygame.K_ESCAPE:
                return "exit"
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.ship_rects):
                if rect.collidepoint(event.pos):
                    if i == self.selected_index:
                        # Double click or click on selected - confirm
                        return self.factions[self.selected_index]
                    else:
                        self.selected_index = i
        
        return None
    
    def draw(self, surface):
        """Draw the ship selection screen."""
        # Background
        surface.fill((5, 5, 20))
        self.starfield.update()
        self.starfield.draw(surface)
        
        # Title
        title = self.title_font.render("SELECT YOUR SHIP", True, (255, 215, 0))
        surface.blit(title, (self.screen_width // 2 - title.get_width() // 2, 50))
        
        # Subtitle
        subtitle = self.hint_font.render("Each faction has unique weapons (coming soon!)", True, (150, 150, 180))
        surface.blit(subtitle, (self.screen_width // 2 - subtitle.get_width() // 2, 120))
        
        # Draw ship options
        self.ship_rects = []
        ship_size = 200
        spacing = 50
        total_width = len(self.factions) * ship_size + (len(self.factions) - 1) * spacing
        start_x = (self.screen_width - total_width) // 2
        ship_y = self.screen_height // 2 - 50
        
        for i, preview in enumerate(self.ship_previews):
            x = start_x + i * (ship_size + spacing)
            rect = pygame.Rect(x, ship_y - ship_size // 2, ship_size, ship_size)
            self.ship_rects.append(rect)
            
            # Selection highlight
            is_selected = (i == self.selected_index)
            is_hovered = rect.collidepoint(pygame.mouse.get_pos())
            
            if is_selected:
                # Glowing border for selected
                glow_rect = rect.inflate(20, 20)
                pygame.draw.rect(surface, (*preview['color'], 150), glow_rect, border_radius=15)
                pygame.draw.rect(surface, preview['color'], rect, 4, border_radius=10)
            elif is_hovered:
                pygame.draw.rect(surface, (80, 80, 100), rect, 2, border_radius=10)
            
            # Background panel
            panel_color = (40, 40, 60) if is_selected else (25, 25, 40)
            pygame.draw.rect(surface, panel_color, rect, border_radius=10)
            
            # Ship image
            if preview['image']:
                img = pygame.transform.smoothscale(preview['image'], (ship_size - 40, ship_size - 40))
                img_x = x + 20
                img_y = ship_y - (ship_size - 40) // 2
                surface.blit(img, (img_x, img_y))
            
            # Faction name below
            name_text = self.faction_font.render(preview['faction'], True, 
                                                  preview['color'] if is_selected else (180, 180, 180))
            name_x = x + ship_size // 2 - name_text.get_width() // 2
            name_y = ship_y + ship_size // 2 + 15
            surface.blit(name_text, (name_x, name_y))
        
        # Controls hint
        controls = self.hint_font.render("← → or A/D to select  |  ENTER or CLICK to confirm  |  ESC to exit", 
                                         True, (120, 120, 140))
        surface.blit(controls, (self.screen_width // 2 - controls.get_width() // 2, 
                               self.screen_height - 60))


def run_space_shooter(screen, player_faction=None, ai_faction=None):
    """
    Run the space shooter mini-game.
    
    Args:
        screen: Pygame display surface
        player_faction: Player's faction name (if None, show selection screen)
        ai_faction: AI's faction name (if None, pick random)
    
    Returns:
        True if player won, False if AI won, None if exited early
    """
    clock = pygame.time.Clock()
    screen_width = screen.get_width()
    screen_height = screen.get_height()
    
    # Show ship selection if no faction provided
    if player_faction is None:
        select_screen = ShipSelectScreen(screen_width, screen_height)
        selecting = True
        
        while selecting:
            clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                
                result = select_screen.handle_event(event)
                if result == "exit":
                    return None
                elif result:
                    player_faction = result
                    selecting = False
            
            select_screen.draw(screen)
            pygame.display.flip()
    
    # Pick random AI faction (different from player)
    if ai_faction is None:
        factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]
        ai_faction = random.choice([f for f in factions if f != player_faction])
    
    session_scores = []  # Per-session leaderboard, shared across R restarts
    game = SpaceShooterGame(screen_width, screen_height, player_faction, ai_faction,
                            session_scores=session_scores)
    
    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.exit_to_menu = True
                game.running = False
            else:
                game.handle_event(event)
        
        game.update()
        game.draw(screen)
        
        pygame.display.flip()
        clock.tick(60)
    
    if game.exit_to_menu:
        return None
    
    return game.winner == "player"
