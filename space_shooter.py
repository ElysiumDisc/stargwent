"""
STARGWENT - SPACE SHOOTER EASTER EGG
A simple 1v1 arcade-style space shooter mini-game.
Unlocked after achieving 8 wins in Draft Mode.

Controls:
- W/S or UP/DOWN: Move ship
- SPACE: Fire laser
- ESC: Exit to main menu
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
        self.direction = direction  # 1 = right, -1 = left
        self.color = color
        self.speed = speed
        self.damage = damage
        self.active = True
    
    def update(self):
        self.x += self.speed * self.direction
    
    def get_rect(self):
        return pygame.Rect(int(self.x) - 15, int(self.y) - 15, 30, 30)
    
    def draw(self, surface):
        pass


class Laser(Projectile):
    """Standard laser projectile (Goa'uld style)."""
    def __init__(self, x, y, direction, color, speed=18):
        super().__init__(x, y, direction, color, speed, damage=12)
        self.width = 35
        self.height = 6
    
    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y - self.height // 2), self.width, self.height)
    
    def draw(self, surface):
        # Glowing laser effect
        glow_surf = pygame.Surface((self.width + 10, self.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*self.color[:3], 100), (5, 5, self.width, self.height))
        pygame.draw.rect(glow_surf, self.color, (5, 5, self.width, self.height))
        # Bright core
        pygame.draw.rect(glow_surf, (255, 255, 255), (5, 5 + self.height // 4, self.width, self.height // 2))
        surface.blit(glow_surf, (int(self.x) - 5, int(self.y) - self.height // 2 - 5))


class Missile(Projectile):
    """Tau'ri missile - slower but high damage with trail."""
    def __init__(self, x, y, direction, color, speed=10):
        super().__init__(x, y, direction, color, speed, damage=25)
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
        
        # Slight wobble for realism
        self.wobble += 0.3
        self.y += math.sin(self.wobble) * 0.5
        
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
        # Body
        pygame.draw.ellipse(missile_surf, self.color, (5, 5, self.width, self.height))
        # Nose cone
        nose_x = 5 + self.width if self.direction == 1 else 5 - 5
        pygame.draw.polygon(missile_surf, (200, 200, 200), [
            (nose_x, 5 + self.height // 2),
            (nose_x - 5 * self.direction, 5),
            (nose_x - 5 * self.direction, 5 + self.height)
        ])
        surface.blit(missile_surf, (int(self.x) - self.width // 2 - 5, int(self.y) - self.height // 2 - 5))


class ContinuousBeam:
    """Asgard continuous beam weapon - deals damage over time, reaches entire screen."""
    def __init__(self, ship, direction, color, screen_width):
        self.ship = ship
        self.direction = direction
        self.color = color
        self.screen_width = screen_width
        self.active = True
        self.damage_per_frame = 0.8
        self.pulse = 0
    
    def update(self):
        self.pulse += 0.2
    
    def get_start_pos(self):
        return (self.ship.x + (self.ship.width if self.direction == 1 else 0), self.ship.y)
    
    def get_rect(self):
        start_x, start_y = self.get_start_pos()
        if self.direction == 1:
            beam_length = self.screen_width - start_x
            return pygame.Rect(int(start_x), int(start_y) - 10, beam_length, 20)
        else:
            return pygame.Rect(0, int(start_y) - 10, int(start_x), 20)
    
    def draw(self, surface):
        start_x, start_y = self.get_start_pos()
        
        if self.direction == 1:
            end_x = self.screen_width
        else:
            end_x = 0
        
        beam_length = abs(end_x - start_x)
        
        # Pulsing beam effect
        pulse_width = 8 + int(math.sin(self.pulse) * 4)
        
        # Create beam surface
        beam_surf = pygame.Surface((beam_length + 20, 60), pygame.SRCALPHA)
        
        # Outer glow
        pygame.draw.line(beam_surf, (*self.color[:3], 40), (10, 30), (beam_length + 10, 30), pulse_width + 12)
        pygame.draw.line(beam_surf, (*self.color[:3], 80), (10, 30), (beam_length + 10, 30), pulse_width + 6)
        pygame.draw.line(beam_surf, self.color, (10, 30), (beam_length + 10, 30), pulse_width)
        # White hot core
        pygame.draw.line(beam_surf, (255, 255, 255), (10, 30), (beam_length + 10, 30), pulse_width // 2)
        
        blit_x = min(start_x, end_x) - 10
        surface.blit(beam_surf, (int(blit_x), int(start_y) - 30))


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
        
        # Update particles
        for p in self.particles:
            p['alpha'] -= 10
            p['x'] -= self.direction * 2
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
        super().__init__(x, y, direction, color, speed, damage=15)
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
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Start from right side, move left - SLOW speed
        self.x = screen_width + 150
        self.y = random.randint(150, screen_height - 150)
        self.speed = random.uniform(1.0, 2.0)  # Much slower
        self.size = random.randint(120, 200)  # Much bigger
        self.rotation = 0
        self.rotation_speed = random.uniform(-0.5, 0.5)  # Slower rotation
        self.health = self.size * 2  # More health for bigger asteroids
        self.active = True
        
        # Generate rocky shape (irregular polygon)
        self.points = []
        num_points = random.randint(8, 14)
        for i in range(num_points):
            angle = (i / num_points) * math.pi * 2
            dist = self.size // 2 + random.randint(-self.size // 5, self.size // 5)
            self.points.append((
                math.cos(angle) * dist,
                math.sin(angle) * dist
            ))
        
        self.color = random.choice([
            (100, 90, 80),
            (80, 70, 60),
            (90, 85, 75),
            (70, 65, 55)
        ])
    
    def update(self):
        self.x -= self.speed
        self.rotation += self.rotation_speed
        
        # Remove if off screen
        if self.x < -self.size:
            self.active = False
    
    def get_rect(self):
        return pygame.Rect(int(self.x) - self.size // 2, int(self.y) - self.size // 2,
                          self.size, self.size)
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.active = False
            return True  # Destroyed
        return False
    
    def draw(self, surface):
        # Create rotated asteroid surface
        asteroid_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        center = self.size
        
        # Rotate points
        rotated_points = []
        for px, py in self.points:
            angle = math.radians(self.rotation)
            rx = px * math.cos(angle) - py * math.sin(angle) + center
            ry = px * math.sin(angle) + py * math.cos(angle) + center
            rotated_points.append((rx, ry))
        
        # Draw asteroid
        pygame.draw.polygon(asteroid_surf, self.color, rotated_points)
        pygame.draw.polygon(asteroid_surf, (50, 45, 40), rotated_points, 3)
        
        # Add some crater details
        for i in range(3):
            crater_x = center + random.randint(-self.size // 3, self.size // 3)
            crater_y = center + random.randint(-self.size // 3, self.size // 3)
            crater_size = random.randint(3, 8)
            pygame.draw.circle(asteroid_surf, (60, 55, 50), (crater_x, crater_y), crater_size)
        
        surface.blit(asteroid_surf, (int(self.x) - center, int(self.y) - center))


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
            self.fire_rate = 180  # 3 second cooldown at 60 FPS
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
            self.fire_rate = 20  # Faster
        
        # For beam weapon
        self.beam_active = False
        self.current_beam = None
        self.beam_cooldown = 0  # Cooldown after beam stops
        self.beam_duration_timer = 0
        
        # Ship image
        self.image = None
        self.original_size = 120  # Original PNG size
        self.scale_factor = 2  # 2x size
        self.width = self.original_size * self.scale_factor  # 240
        self.height = self.original_size * self.scale_factor  # 240
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
        self.margin = 100
        
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
            
            # Scale to 2x size (maintain aspect ratio since they're square)
            self.image = pygame.transform.smoothscale(self.image, (self.width, self.height))
            
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
        
        if self.is_player and keys:
            # Player controls
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.y -= self.speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.y += self.speed
        
        # Keep in bounds
        self.y = max(self.margin, min(self.screen_height - self.margin, self.y))
        
        # Update beam if active
        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            if self.beam_duration_timer >= 180:  # 3 seconds at 60 FPS
                self.stop_beam()
    
    def update_ai(self, player_ship, asteroids):
        """Smart AI update - aims at player, dodges asteroids."""
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.beam_cooldown > 0:
            self.beam_cooldown -= 1
        
        # AI targeting - try to align with player's Y position
        target_y = player_ship.y
        
        # Check for incoming asteroids and dodge them
        dodge_direction = 0
        for asteroid in asteroids:
            # If asteroid is heading toward AI ship
            if asteroid.x < self.x + 400 and asteroid.x > self.x - 100:
                asteroid_dist_y = abs(asteroid.y - self.y)
                if asteroid_dist_y < asteroid.size + self.height // 2 + 50:
                    # Need to dodge!
                    if asteroid.y > self.y:
                        dodge_direction = -1  # Dodge up
                    else:
                        dodge_direction = 1   # Dodge down
                    break
        
        # Apply dodge or pursue player
        if dodge_direction != 0:
            # Dodging asteroid - move faster
            self.y += dodge_direction * self.speed * 1.2
        else:
            # Pursue player with some prediction
            y_diff = target_y - self.y
            
            # Add some smoothing and slight randomness for realism
            if abs(y_diff) > 10:
                move_speed = min(self.speed * 0.9, abs(y_diff) * 0.1)
                if y_diff > 0:
                    self.y += move_speed
                else:
                    self.y -= move_speed
        
        # Keep in bounds
        self.y = max(self.margin, min(self.screen_height - self.margin, self.y))
        
        # Update beam if active
        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            if self.beam_duration_timer >= 180:  # 3 seconds at 60 FPS
                self.stop_beam()
    
    def fire(self):
        """Fire weapon based on faction type."""
        direction = 1 if self.is_player else -1
        fire_x = self.x + (self.width if self.is_player else 0)
        
        # Beam weapon is special - it's continuous but has cooldown after use
        if self.weapon_type == "beam":
            if self.beam_cooldown <= 0 and not self.current_beam:
                self.current_beam = ContinuousBeam(self, direction, self.laser_color, self.screen_width)
                self.beam_duration_timer = 0
            return self.current_beam
        
        # Other weapons have cooldown
        if self.fire_cooldown <= 0:
            self.fire_cooldown = self.fire_rate
            
            if self.weapon_type == "missile":
                return Missile(fire_x, self.y, direction, self.laser_color)
            elif self.weapon_type == "energy_ball":
                return EnergyBall(fire_x, self.y, direction, self.laser_color)
            elif self.weapon_type == "staff":
                return JaffaStaffBlast(fire_x, self.y, direction, self.laser_color)
            else:  # laser (Goa'uld default)
                return Laser(fire_x, self.y, direction, self.laser_color)
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
        if is_asteroid:
            # Asteroids damage shields only and trigger shield bubble effect
            self.shields = max(0, self.shields - amount)
            self.shield_hit_timer = 60  # Show shield bubble for 60 frames (1 second)
            return False  # Asteroids never destroy the ship directly
        else:
            # Weapons damage health
            self.health -= amount
            return self.health <= 0
    
    def draw(self, surface, time_tick=0):
        """Draw the ship with shield bubble (only when hit by asteroid)."""
        # Decrement shield hit timer
        if self.shield_hit_timer > 0:
            self.shield_hit_timer -= 1
        
        # Draw shield bubble only when recently hit by asteroid
        if self.shield_hit_timer > 0 and self.shields > 0:
            shield_pct = self.shields / self.max_shields
            # Make bubble more visible based on timer (fades out)
            visibility = self.shield_hit_timer / 60.0
            bubble_radius = int(self.width * 0.7)
            bubble_center = (int(self.x + self.width // 2), int(self.y))
            
            # Animated bubble effect
            pulse = math.sin(time_tick * 0.15) * 0.15 + 1.0
            animated_radius = int(bubble_radius * pulse)
            
            # Create shield bubble surface
            bubble_surf = pygame.Surface((animated_radius * 2 + 20, animated_radius * 2 + 20), pygame.SRCALPHA)
            bubble_center_local = (animated_radius + 10, animated_radius + 10)
            
            # Outer glow (bright when just hit)
            alpha_outer = int(80 * shield_pct * visibility)
            pygame.draw.circle(bubble_surf, (100, 200, 255, alpha_outer), bubble_center_local, animated_radius + 10)
            
            # Main shield bubble
            alpha_main = int(120 * shield_pct * visibility)
            pygame.draw.circle(bubble_surf, (50, 150, 255, alpha_main), bubble_center_local, animated_radius)
            
            # Inner highlight (top-left for 3D effect)
            highlight_offset = int(animated_radius * 0.3)
            alpha_highlight = int(150 * shield_pct * visibility)
            pygame.draw.circle(bubble_surf, (150, 220, 255, alpha_highlight), 
                             (bubble_center_local[0] - highlight_offset, bubble_center_local[1] - highlight_offset), 
                             int(animated_radius * 0.4))
            
            # Shield ring (thicker and brighter)
            ring_alpha = int(200 * shield_pct * visibility)
            pygame.draw.circle(bubble_surf, (100, 220, 255, ring_alpha), bubble_center_local, animated_radius, 4)
            
            # Blit shield bubble
            surface.blit(bubble_surf, (bubble_center[0] - animated_radius - 10, bubble_center[1] - animated_radius - 10))
        
        # Draw ship
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y - self.height // 2)))
        else:
            # Fallback triangle ship
            if self.is_player:
                points = [
                    (self.x + self.width, self.y),
                    (self.x, self.y - self.height // 2),
                    (self.x, self.y + self.height // 2)
                ]
            else:
                points = [
                    (self.x, self.y),
                    (self.x + self.width, self.y - self.height // 2),
                    (self.x + self.width, self.y + self.height // 2)
                ]
            pygame.draw.polygon(surface, self.laser_color, points)
            pygame.draw.polygon(surface, (255, 255, 255), points, 2)
        
        # Draw health bar only (shield shown as bubble now)
        bar_width = self.width
        bar_height = 8
        bar_x = self.x
        health_bar_y = self.y - self.height // 2 - 15
        
        # Health background
        pygame.draw.rect(surface, (60, 60, 60), (bar_x, health_bar_y, bar_width, bar_height))
        # Health fill
        health_pct = self.health / self.max_health
        health_color = (0, 255, 0) if health_pct > 0.5 else (255, 255, 0) if health_pct > 0.25 else (255, 0, 0)
        pygame.draw.rect(surface, health_color, (bar_x, health_bar_y, int(bar_width * health_pct), bar_height))
        # Border
        pygame.draw.rect(surface, (255, 255, 255), (bar_x, health_bar_y, bar_width, bar_height), 1)
        
        # Small shield indicator text
        if self.shields > 0:
            shield_text = f"{int(self.shields)}%"
            font = pygame.font.SysFont("Arial", 14)
            text_surf = font.render(shield_text, True, (100, 200, 255))
            surface.blit(text_surf, (bar_x + bar_width + 5, health_bar_y - 2))


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


class SpaceShooterGame:
    """Main space shooter mini-game with waves of enemies."""
    def __init__(self, screen_width, screen_height, player_faction, ai_faction):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.player_faction = player_faction
        self.ai_faction = ai_faction
        
        # Game state
        self.running = True
        self.game_over = False
        self.winner = None
        self.exit_to_menu = False
        
        # Wave system
        self.current_wave = 1
        self.max_waves = 5
        self.wave_complete = False
        self.wave_transition_timer = 0
        self.enemies_defeated = 0
        
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
        
        # Asteroid spawning
        self.asteroid_spawn_timer = 0
        self.asteroid_spawn_rate = 300  # frames between spawns
        
        # Player beam state (for Asgard continuous beam)
        self.player_firing = False
        
        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.ui_font = pygame.font.SysFont("Arial", 32)
        self.small_font = pygame.font.SysFont("Arial", 24)
        
        # Hit flash effect
        self.player_hit_flash = 0
    
    def spawn_wave_enemies(self):
        """Spawn enemies for the current wave."""
        self.ai_ships = []
        num_enemies = self.current_wave  # Wave 1 = 1 enemy, Wave 5 = 5 enemies
        
        # Minimum vertical spacing between ships to avoid overlap
        min_spacing = 150
        margin = 150  # Keep away from top/bottom edges
        usable_height = self.screen_height - 2 * margin
        
        # Generate random Y positions with minimum separation
        y_positions = []
        for i in range(num_enemies):
            attempts = 0
            while attempts < 50:
                y_pos = random.randint(margin, self.screen_height - margin)
                # Check distance from all existing positions
                valid = True
                for existing_y in y_positions:
                    if abs(y_pos - existing_y) < min_spacing:
                        valid = False
                        break
                if valid:
                    y_positions.append(y_pos)
                    break
                attempts += 1
            else:
                # Fallback: use evenly spaced position if random placement fails
                spacing = usable_height // (num_enemies + 1)
                y_positions.append(margin + spacing * (i + 1))
        
        for i, y_pos in enumerate(y_positions):
            # Pick random faction for variety (but not player's faction)
            enemy_faction = random.choice([f for f in self.all_factions if f != self.player_faction])
            
            ship = Ship(
                self.screen_width - 340 - (i * 50),  # Stagger x positions slightly
                y_pos,
                enemy_faction, is_player=False,
                screen_width=self.screen_width, screen_height=self.screen_height
            )
            ship.ai_fire_timer = random.randint(0, 60)  # Randomize initial fire timing
            self.ai_ships.append(ship)
    
    def handle_event(self, event):
        """Handle pygame events."""
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
            elif event.key == pygame.K_r and self.game_over:
                # Restart game
                self.__init__(self.screen_width, self.screen_height, 
                            self.player_faction, self.ai_faction)
        
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                self.player_firing = False
                self.player_ship.stop_beam()
    
    def update(self):
        """Update game state."""
        # Handle wave transition
        if self.wave_complete:
            self.wave_transition_timer += 1
            if self.wave_transition_timer >= 120:  # 2 second delay
                self.current_wave += 1
                if self.current_wave > self.max_waves:
                    self.game_over = True
                    self.winner = "player"
                else:
                    self.spawn_wave_enemies()
                    self.wave_complete = False
                    self.wave_transition_timer = 0
            # Update explosions during transition
            self.explosions = [e for e in self.explosions if e.update()]
            self.starfield.update()
            return
        
        if self.game_over:
            self.explosions = [e for e in self.explosions if e.update()]
            return
        
        keys = pygame.key.get_pressed()
        
        # Update player ship
        self.player_ship.update(keys)
        
        # Update all AI ships with smart behavior
        for ai_ship in self.ai_ships:
            ai_ship.update_ai(self.player_ship, self.asteroids)
            
            # AI firing
            if not hasattr(ai_ship, 'ai_fire_timer'):
                ai_ship.ai_fire_timer = 0
            ai_ship.ai_fire_timer -= 1
            y_diff = abs(ai_ship.y - self.player_ship.y)
            
            # Handle beam weapons - continuous fire when aligned
            if ai_ship.weapon_type == "beam":
                if y_diff < 80:  # AI aims beam when close to player's Y
                    if not ai_ship.current_beam:
                        ai_ship.fire()
                else:
                    # Stop beam when not aligned
                    ai_ship.stop_beam()
            else:
                # Regular projectile weapons
                if ai_ship.ai_fire_timer <= 0 and y_diff < 100:
                    projectile = ai_ship.fire()
                    if projectile:
                        self.projectiles.append(projectile)
                    ai_ship.ai_fire_timer = random.randint(30, 80)
        
        # Player continuous firing
        if self.player_firing:
            if self.player_ship.weapon_type == "beam":
                if not self.player_ship.current_beam:
                    self.player_ship.fire()
            else:
                projectile = self.player_ship.fire()
                if projectile:
                    self.projectiles.append(projectile)
        
        # Spawn asteroids
        self.asteroid_spawn_timer += 1
        if self.asteroid_spawn_timer >= self.asteroid_spawn_rate:
            self.asteroid_spawn_timer = 0
            self.asteroids.append(Asteroid(self.screen_width, self.screen_height))
        
        # Update asteroids
        for asteroid in self.asteroids[:]:
            asteroid.update()
            if not asteroid.active:
                self.asteroids.remove(asteroid)
        
        # Update projectiles
        for proj in self.projectiles[:]:
            proj.update()
            
            if proj.x < -100 or proj.x > self.screen_width + 100:
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                continue
            
            proj_rect = proj.get_rect()
            
            if proj.direction == 1:  # Player projectile
                # Check collision with all AI ships
                for ai_ship in self.ai_ships[:]:
                    if proj_rect.colliderect(ai_ship.get_rect()):
                        if proj in self.projectiles:
                            self.projectiles.remove(proj)
                        ai_ship.hit_flash = 10
                        if ai_ship.take_damage(proj.damage):
                            self.explosions.append(Explosion(
                                ai_ship.x + ai_ship.width // 2, ai_ship.y))
                            self.ai_ships.remove(ai_ship)
                            self.enemies_defeated += 1
                            # Check if wave complete
                            if len(self.ai_ships) == 0:
                                self.wave_complete = True
                        break
            else:  # AI projectile hitting player
                if proj_rect.colliderect(self.player_ship.get_rect()):
                    if proj in self.projectiles:
                        self.projectiles.remove(proj)
                    self.player_hit_flash = 10
                    if self.player_ship.take_damage(proj.damage):
                        self.game_over = True
                        self.winner = "ai"
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
                    break
        
        # Check beam collision
        if self.player_ship.current_beam:
            beam = self.player_ship.current_beam
            beam_rect = beam.get_rect()
            
            for ai_ship in self.ai_ships[:]:
                if beam_rect.colliderect(ai_ship.get_rect()):
                    ai_ship.hit_flash = 3
                    if ai_ship.take_damage(beam.damage_per_frame):
                        self.explosions.append(Explosion(
                            ai_ship.x + ai_ship.width // 2, ai_ship.y))
                        self.ai_ships.remove(ai_ship)
                        self.enemies_defeated += 1
                        if len(self.ai_ships) == 0:
                            self.wave_complete = True
            
            for asteroid in self.asteroids[:]:
                if beam_rect.colliderect(asteroid.get_rect()):
                    if asteroid.take_damage(beam.damage_per_frame):
                        self.explosions.append(Explosion(asteroid.x, asteroid.y))
                        self.asteroids.remove(asteroid)
        
        # Check AI beam collision with player
        for ai_ship in self.ai_ships:
            if ai_ship.current_beam:
                beam = ai_ship.current_beam
                beam_rect = beam.get_rect()
                
                # AI beam vs player
                if beam_rect.colliderect(self.player_ship.get_rect()):
                    self.player_hit_flash = 3
                    if self.player_ship.take_damage(beam.damage_per_frame):
                        self.game_over = True
                        self.winner = "ai"
                        self.explosions.append(Explosion(
                            self.player_ship.x + self.player_ship.width // 2,
                            self.player_ship.y))
                
                # AI beam vs asteroids
                for asteroid in self.asteroids[:]:
                    if beam_rect.colliderect(asteroid.get_rect()):
                        if asteroid.take_damage(beam.damage_per_frame):
                            self.explosions.append(Explosion(asteroid.x, asteroid.y))
                            if asteroid in self.asteroids:
                                self.asteroids.remove(asteroid)
        
        # Ship collision with asteroids (damages shields)
        for asteroid in self.asteroids[:]:
            if asteroid.get_rect().colliderect(self.player_ship.get_rect()):
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
        
        # Update background
        self.starfield.update()
        
        # Update hit flashes
        if self.player_hit_flash > 0:
            self.player_hit_flash -= 1
        
        # Update explosions
        self.explosions = [e for e in self.explosions if e.update()]
        
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
        
        # Draw projectiles
        for proj in self.projectiles:
            proj.draw(surface)
        
        # Draw beam weapons if active
        if self.player_ship.current_beam:
            self.player_ship.current_beam.draw(surface)
        for ai_ship in self.ai_ships:
            if ai_ship.current_beam:
                ai_ship.current_beam.draw(surface)
        
        # Draw player ship
        if not self.game_over or self.winner != "ai":
            if self.player_hit_flash > 0:
                flash_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                self.player_ship.draw(flash_surf, time_tick)
                flash_overlay = pygame.Surface(flash_surf.get_size(), pygame.SRCALPHA)
                flash_overlay.fill((255, 0, 0, 100))
                flash_surf.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(flash_surf, (0, 0))
            else:
                self.player_ship.draw(surface, time_tick)
        
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
    
    def draw_ui(self, surface):
        """Draw game UI."""
        # Title
        title = self.title_font.render("STARGATE SPACE BATTLE", True, (255, 215, 0))
        surface.blit(title, (self.screen_width // 2 - title.get_width() // 2, 20))
        
        # Wave info
        wave_text = self.ui_font.render(f"WAVE {self.current_wave}/{self.max_waves}", True, (255, 200, 100))
        surface.blit(wave_text, (self.screen_width // 2 - wave_text.get_width() // 2, 80))
        
        # Enemies remaining
        enemies_text = self.small_font.render(f"Enemies: {len(self.ai_ships)}", True, (255, 100, 100))
        surface.blit(enemies_text, (self.screen_width // 2 - enemies_text.get_width() // 2, 115))
        
        # Player faction label
        player_label = self.ui_font.render(self.player_faction.upper(), True, self.player_ship.laser_color)
        surface.blit(player_label, (50, self.screen_height - 50))
        
        # Controls hint
        controls = self.small_font.render("W/S or ↑/↓: Move  |  SPACE: Fire  |  ESC: Exit", True, (150, 150, 150))
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
            restart_surf = self.ui_font.render("Press R to play again or ESC to exit", True, (150, 150, 150))
            
            surface.blit(result_surf, (self.screen_width // 2 - result_surf.get_width() // 2, 
                                       self.screen_height // 2 - 80))
            surface.blit(sub_surf, (self.screen_width // 2 - sub_surf.get_width() // 2,
                                    self.screen_height // 2))
            surface.blit(restart_surf, (self.screen_width // 2 - restart_surf.get_width() // 2,
                                        self.screen_height // 2 + 60))


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
    
    game = SpaceShooterGame(screen_width, screen_height, player_faction, ai_faction)
    
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
