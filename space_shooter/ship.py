"""Ship class for player and AI ships."""

import pygame
import math
import random
import os

from .projectiles import (ContinuousBeam, Laser, Missile, EnergyBall,
                          JaffaStaffBlast, RailgunShot, ProximityMine)


# --- Ship variant definitions ---
# Each faction maps to a list of variant dicts. Index 0 = default ship.
# Fields: name, image_file, image_orientation ("left"=faces left, "up"=faces up, "down"=faces down, "right"),
#         weapon_type, fire_rate, secondary_type, secondary_fire_rate,
#         passive, passive_state, description
SHIP_VARIANTS = {
    "asgard": [
        {
            "name": "O'Neill-class",
            "image_file": "asgard_ship.png",
            "image_orientation": "left",
            "weapon_type": "beam",
            "fire_rate": 150,
            "secondary_type": "ion_pulse",
            "secondary_fire_rate": 300,
            "passive": "beam_pierce",
            "passive_state": {},
            "description": "Beam weapon pierces enemies",
        },
        {
            "name": "Valhalla-class",
            "image_file": "asgard_ship_alt_1.png",
            "image_orientation": "down",
            "weapon_type": "plasma_lance",
            "fire_rate": 40,
            "secondary_type": "ion_pulse",
            "secondary_fire_rate": 240,
            "passive": "heavy_armor",
            "passive_state": {},
            "description": "Slow heavy warship, 25% dmg reduction",
        },
        {
            "name": "Beliskner-class",
            "image_file": "asgard_ship_alt_2.png",
            "image_orientation": "down",
            "weapon_type": "beam",
            "fire_rate": 120,
            "secondary_type": "transporter_beam",
            "secondary_fire_rate": 360,
            "passive": "adaptive_shields",
            "passive_state": {"shield_hits": 0, "dmg_buff_timer": 0},
            "description": "Shield hits grant damage buff",
        },
        {
            "name": "Research Vessel",
            "image_file": "asgard_ship_alt_3.png",
            "image_orientation": "down",
            "weapon_type": "disruptor_pulse",
            "fire_rate": 15,
            "secondary_type": "sensor_sweep",
            "secondary_fire_rate": 480,
            "passive": "analyzer",
            "passive_state": {},
            "description": "Rapid fire, marked kills = double XP",
        },
    ],
    "goa'uld": [
        {
            "name": "Ha'tak",
            "image_file": "goa'uld_ship.png",
            "image_orientation": "right",
            "weapon_type": "laser",
            "fire_rate": 14,
            "secondary_type": "staff_barrage",
            "secondary_fire_rate": 240,
            "passive": "shield_regen",
            "passive_state": {"no_hit_timer": 0},
            "description": "Shield regen after 2s without damage",
        },
        {
            "name": "Apophis Flagship",
            "image_file": "goa'uld_ship_alt_1.png",
            "image_orientation": "down",
            "weapon_type": "dual_staff",
            "fire_rate": 10,
            "secondary_type": "ribbon_blast",
            "secondary_fire_rate": 180,
            "passive": "sarcophagus_regen",
            "passive_state": {},
            "description": "Twin staffs, heals below 50% HP",
        },
        {
            "name": "Anubis Mothership",
            "image_file": "goa'uld_ship_alt_2.png",
            "image_orientation": "down",
            "weapon_type": "laser",
            "fire_rate": 18,
            "secondary_type": "eye_of_ra",
            "secondary_fire_rate": 300,
            "passive": "anubis_shield",
            "passive_state": {"absorb_charges": 3},
            "description": "Eye of Ra beam, absorbs 3 hits",
        },
    ],
    "tau'ri": [
        {
            "name": "BC-304",
            "image_file": "tau'ri_ship.png",
            "image_orientation": "up",
            "weapon_type": "missile",
            "fire_rate": 28,
            "secondary_type": "railgun",
            "secondary_fire_rate": 180,
            "passive": "armor_plating",
            "passive_state": {},
            "description": "Armored fighter, -15% incoming damage",
        },
        {
            "name": "Aurora-class",
            "image_file": "tau'ri_ship_alt_1.png",
            "image_orientation": "up",
            "natural_size": True,
            "weapon_type": "drone_pulse",
            "fire_rate": 12,
            "secondary_type": "drone_salvo",
            "secondary_fire_rate": 360,
            "passive": "ancient_shields",
            "passive_state": {"regen_rate": 0.3},
            "description": "Ancient battleship, rapid drones, powerful shield regen",
        },
    ],
    "jaffa rebellion": [
        {
            "name": "Death Glider",
            "image_file": "jaffa_rebellion_ship.png",
            "image_orientation": "left",
            "weapon_type": "staff",
            "fire_rate": 16,
            "secondary_type": "war_cry",
            "secondary_fire_rate": 360,
            "passive": "warriors_fury",
            "passive_state": {"kills": 0},
            "description": "+2% damage per kill, max 40%",
        },
        {
            "name": "Ha'tak Refit",
            "image_file": "jaffa_rebellion_alt_1.png",
            "image_orientation": "down",
            "weapon_type": "dual_staff",
            "fire_rate": 12,
            "secondary_type": "jaffa_rally",
            "secondary_fire_rate": 420,
            "passive": "symbiote_resilience",
            "passive_state": {"invuln_cooldown": 0},
            "description": "Twin staffs, invuln burst when low HP",
        },
    ],
    "lucian alliance": [
        {
            "name": "Smuggler Ship",
            "image_file": "lucian_alliance_ship.png",
            "image_orientation": "up",
            "weapon_type": "energy_ball",
            "fire_rate": 20,
            "secondary_type": "scatter_mines",
            "secondary_fire_rate": 210,
            "passive": "splash_damage",
            "passive_state": {},
            "description": "Energy balls deal 40% AoE splash",
        },
    ],
}

# Build alias mappings for alternate faction name spellings
for _alias, _canon in [("tauri", "tau'ri"), ("goauld", "goa'uld"),
                        ("jaffa_rebellion", "jaffa rebellion"),
                        ("lucian_alliance", "lucian alliance")]:
    SHIP_VARIANTS[_alias] = SHIP_VARIANTS[_canon]

# Collect all alt ship image files for AI visual variety
_ALL_ALT_SHIP_IMAGES = []
_seen = set()
for _variants in SHIP_VARIANTS.values():
    for _v in _variants:
        f = _v["image_file"]
        if f not in _seen:
            _seen.add(f)
            _ALL_ALT_SHIP_IMAGES.append(f)


class Ship:
    """A spaceship (player or AI). All positions are in world-space."""

    _shield_hit_sound = None
    _shield_hit_sound_loaded = False

    def __init__(self, x, y, faction, is_player=True, screen_width=1920, screen_height=1080,
                 variant=0):
        self.x = x
        self.y = y
        self.faction = faction
        self.is_player = is_player
        self.variant = variant
        # Store screen dims for spawner compatibility (not used for clamping)
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Stats
        self.max_health = 100
        self.health = self.max_health
        self.max_shields = 100
        self.shields = self.max_shields
        self.shield_hit_timer = 0  # Timer for shield bubble visibility
        self.speed = 8 if is_player else 4
        self.fire_cooldown = 0
        self.fire_rate = 30  # frames between shots

        # Look up variant config (data-driven)
        faction_lower = faction.lower()
        variants = SHIP_VARIANTS.get(faction_lower, [])
        if variants and 0 <= variant < len(variants):
            vdata = variants[variant]
        elif variants:
            vdata = variants[0]
        else:
            vdata = None

        if vdata:
            self.weapon_type = vdata["weapon_type"]
            self.fire_rate = vdata["fire_rate"]
            self.passive = vdata["passive"]
            self.passive_state = dict(vdata.get("passive_state", {}))
            self.secondary_type = vdata["secondary_type"]
            self.secondary_fire_rate = vdata["secondary_fire_rate"]
            self._variant_image_file = vdata["image_file"]
            self._variant_image_orientation = vdata["image_orientation"]
            self._variant_natural_size = vdata.get("natural_size", False)
            self.variant_name = vdata["name"]
        else:
            # Fallback for unknown factions
            self.weapon_type = "laser"
            self.passive = None
            self.passive_state = {}
            self.secondary_type = None
            self.secondary_fire_rate = 300
            self._variant_image_file = None
            self._variant_image_orientation = None
            self._variant_natural_size = False
            self.variant_name = faction

        # Secondary fire system
        self.secondary_cooldown = 0
        self.secondary_buff_timer = 0  # For buff-type secondaries

        # Heavy armor passive: 20% slower
        if self.passive == "heavy_armor" and is_player:
            self.speed = int(self.speed * 0.8)

        # For beam weapon
        self.beam_active = False
        self.current_beam = None
        self.beam_cooldown = 0  # Cooldown after beam stops
        self.beam_duration_timer = 0

        # Ship image
        self.image = None
        self.image_right = None  # Base right-facing image for rotation
        self.image_left = None
        self.image_up = None
        self.image_down = None
        self.facing = (1, 0) if is_player else (-1, 0)
        self.original_size = 120
        self.scale_factor = 1.2
        self.width = int(self.original_size * self.scale_factor)
        self.height = int(self.original_size * self.scale_factor)
        # Smooth rotation state
        self._current_angle = 0.0 if is_player else 180.0  # Degrees, 0=right
        self._target_angle = self._current_angle
        self._rotation_speed = 12.0  # Degrees per frame
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

        # Movement bounds (unused for player in infinite mode, kept for AI margin)
        self.margin = 60

        # AI behavior
        self.ai_target_y = y
        self.ai_decision_timer = 0
        self.contact_damage_cooldown = 0

        # Enemy type metadata (set by spawner)
        self.enemy_type = "regular"
        self.xp_value = 20
        self.is_boss = False
        self.ai_fire_timer = 0
        self.hit_flash = 0

        # Behavior system (set by spawner from ENEMY_TYPES)
        self._behavior = None
        self._split_gen = 0  # Replicator split generation (max 2 deep)
        self._shield_hp = 0  # Ori fighter extra shield bar
        self._shield_max = 0
        self._charge_timer = 0  # Ori zealous charge countdown
        self._charging = False
        self._homing_angle = random.uniform(0, math.pi * 2)  # Ancient drone turn angle
        self._bomber_timer = 0  # Al'kesh bomb timer
        self._spawner_timer = 0  # Wraith hive dart spawn timer
        self._spawned_darts = []  # Track spawned darts (refs)
        self._swarm_weave = random.uniform(0, math.pi * 2)  # Wraith dart weave offset

        # Ally ship attributes
        self.is_friendly = False
        self.ally_owner = None
        self.ally_lifetime = 0

        # Smooth velocity-based movement (player only)
        self.vx = 0.0
        self.vy = 0.0
        self.acceleration = 1.2  # How fast we reach top speed
        self.friction = 0.88  # Deceleration when no input (0.0 = instant stop, 1.0 = no friction)

        # Thruster speed boost (hold SHIFT)
        self.thruster_boost_active = False
        self.thruster_boost_mult = 1.6  # 60% speed boost
        self.thruster_boost_energy = 100.0  # Boost fuel
        self.thruster_boost_max = 100.0
        self.thruster_boost_drain = 1.2  # Per frame drain
        self.thruster_boost_regen = 0.4  # Per frame regen when not boosting

        # Faction-specific thruster config
        self.thruster_config = self._get_thruster_config(faction_lower)

        # Engine trail particles
        self.engine_particles = []
        self._engine_emit_timer = 0

    def load_image(self):
        """Load ship image using variant data or fallback to faction defaults."""
        # Use variant image file if available, else fallback to faction default
        if self._variant_image_file:
            ship_filename = self._variant_image_file
            orientation = self._variant_image_orientation or "left"
        else:
            faction_to_file = {
                "tau'ri": ("tau'ri_ship.png", "up"),
                "tauri": ("tau'ri_ship.png", "up"),
                "goa'uld": ("goa'uld_ship.png", "right"),
                "goauld": ("goa'uld_ship.png", "right"),
                "asgard": ("asgard_ship.png", "left"),
                "jaffa rebellion": ("jaffa_rebellion_ship.png", "left"),
                "jaffa_rebellion": ("jaffa_rebellion_ship.png", "left"),
                "lucian alliance": ("lucian_alliance_ship.png", "up"),
                "lucian_alliance": ("lucian_alliance_ship.png", "up"),
            }
            faction_lower = self.faction.lower()
            entry = faction_to_file.get(faction_lower, (faction_lower.replace(" ", "_") + "_ship.png", "left"))
            ship_filename = entry[0]
            orientation = entry[1]

        ship_path = os.path.join("assets", "ships", ship_filename)

        try:
            self.image = pygame.image.load(ship_path).convert_alpha()

            # Normalize to right-facing base image based on source orientation
            if orientation == "up":
                # PNG faces up → rotate -90 to face right
                self.image = pygame.transform.rotate(self.image, -90)
            elif orientation == "down":
                # PNG faces down → rotate +90 to face right
                self.image = pygame.transform.rotate(self.image, 90)
            elif orientation == "left":
                # PNG faces left → flip horizontally to face right
                self.image = pygame.transform.flip(self.image, True, False)
            # orientation == "right" → already right-facing, no transform needed

            # Scale image proportionally based on PNG's actual dimensions
            # PNG size determines in-game size — larger PNGs = larger ships
            raw_w = self.image.get_width()
            raw_h = self.image.get_height()
            scaled_w = int(raw_w * self.scale_factor)
            scaled_h = int(raw_h * self.scale_factor)
            self.image = pygame.transform.smoothscale(self.image, (scaled_w, scaled_h))
            self.width = scaled_w
            self.height = scaled_h
            # Cache all 4 facing directions from right-facing base
            self.image_right = self.image.copy()
            self.image_left = pygame.transform.flip(self.image, True, False)
            self.image_up = pygame.transform.rotate(self.image_right, 90)
            self.image_down = pygame.transform.rotate(self.image_right, -90)
            # Set initial facing
            if self.facing == (-1, 0):
                self.image = self.image_left

        except (pygame.error, FileNotFoundError) as e:
            print(f"[space_shooter] Could not load ship: {ship_path} - {e}")
            self.image = None

    def update(self, keys=None):
        """Update ship position and cooldowns. No screen clamping — infinite world."""
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.beam_cooldown > 0:
            self.beam_cooldown -= 1
        if self.secondary_cooldown > 0:
            self.secondary_cooldown -= 1
        if self.secondary_buff_timer > 0:
            self.secondary_buff_timer -= 1

        # Goa'uld passive: Shield Regeneration
        if self.passive == "shield_regen":
            self.passive_state["no_hit_timer"] = self.passive_state.get("no_hit_timer", 0) + 1
            if self.passive_state["no_hit_timer"] >= 120 and self.shields < self.max_shields:
                self.shields = min(self.max_shields, self.shields + 0.3)

        # Sarcophagus regen passive: heal 0.1/frame when below 50% HP
        if self.passive == "sarcophagus_regen":
            if self.health < self.max_health * 0.5:
                self.health = min(self.max_health, self.health + 0.1)

        # Adaptive shields: tick down buff timer
        if self.passive == "adaptive_shields":
            if self.passive_state.get("dmg_buff_timer", 0) > 0:
                self.passive_state["dmg_buff_timer"] -= 1

        # Ancient shields passive: steady shield regen always
        if self.passive == "ancient_shields":
            regen = self.passive_state.get("regen_rate", 0.3)
            if self.shields < self.max_shields:
                self.shields = min(self.max_shields, self.shields + regen)

        # Point defense passive: timer
        if self.passive == "point_defense":
            self.passive_state["pd_timer"] = self.passive_state.get("pd_timer", 0) + 1

        # Symbiote resilience: cooldown tick
        if self.passive == "symbiote_resilience":
            if self.passive_state.get("invuln_cooldown", 0) > 0:
                self.passive_state["invuln_cooldown"] -= 1

        if self.is_player and keys:
            # Thruster boost (SHIFT key)
            want_boost = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            if want_boost and self.thruster_boost_energy > 0:
                self.thruster_boost_active = True
                self.thruster_boost_energy = max(0, self.thruster_boost_energy - self.thruster_boost_drain)
            else:
                self.thruster_boost_active = False
                self.thruster_boost_energy = min(self.thruster_boost_max,
                                                  self.thruster_boost_energy + self.thruster_boost_regen)

            boost = self.thruster_boost_mult if self.thruster_boost_active else 1.0

            # Acceleration-based input — buttery smooth movement
            ax, ay = 0.0, 0.0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                ay -= self.acceleration
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                ay += self.acceleration
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                ax -= self.acceleration
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                ax += self.acceleration

            # Normalize diagonal input so diagonal speed matches cardinal
            if ax != 0 and ay != 0:
                inv_sqrt2 = 0.7071
                ax *= inv_sqrt2
                ay *= inv_sqrt2

            self.vx += ax
            self.vy += ay

            # Apply friction (deceleration when no input on that axis)
            if ax == 0:
                self.vx *= self.friction
            if ay == 0:
                self.vy *= self.friction

            # Clamp velocity to max speed (boosted if shift held)
            max_speed = self.speed * boost
            vel = math.hypot(self.vx, self.vy)
            if vel > max_speed:
                self.vx = self.vx / vel * max_speed
                self.vy = self.vy / vel * max_speed

            # Kill tiny velocities to avoid drifting forever
            if abs(self.vx) < 0.1:
                self.vx = 0
            if abs(self.vy) < 0.1:
                self.vy = 0

            self.x += self.vx
            self.y += self.vy

        # Update beam if active
        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            beam_max = getattr(self, '_asgard_beam_override', 90)
            if self.beam_duration_timer >= beam_max:
                self.stop_beam()
                if hasattr(self, '_asgard_beam_override'):
                    del self._asgard_beam_override

        # Smooth visual rotation
        self._update_rotation()

        # Engine trail particles
        self._update_engine_trail()

    def _get_thruster_config(self, faction_lower):
        """Return faction-specific thruster particle style."""
        configs = {
            # Tau'ri: Clean blue-white chemical thrusters (F-302/Daedalus style)
            "tau'ri": {
                "colors": [(100, 180, 255), (150, 220, 255), (255, 255, 255)],
                "emit_rate": 1, "spread": 3.0, "speed": (2.0, 4.0),
                "size": (2, 5), "life_decay": 0.07, "shrink": 0.95,
                "particle_count": 2, "shape": "circle",
            },
            "tauri": None,  # Filled below
            # Goa'uld: Fiery gold/orange plasma (Ha'tak engines)
            "goa'uld": {
                "colors": [(255, 200, 50), (255, 150, 0), (255, 100, 0)],
                "emit_rate": 1, "spread": 5.0, "speed": (1.5, 3.5),
                "size": (3, 7), "life_decay": 0.05, "shrink": 0.94,
                "particle_count": 3, "shape": "circle",
            },
            "goauld": None,
            # Asgard: Cool cyan energy field (sleek, minimal)
            "asgard": {
                "colors": [(0, 255, 255), (100, 255, 255), (200, 255, 255)],
                "emit_rate": 2, "spread": 2.0, "speed": (2.5, 4.5),
                "size": (2, 4), "life_decay": 0.08, "shrink": 0.97,
                "particle_count": 1, "shape": "diamond",
            },
            # Jaffa: Hot orange/red staff weapon-style exhaust
            "jaffa rebellion": {
                "colors": [(255, 120, 30), (255, 80, 20), (200, 50, 10)],
                "emit_rate": 1, "spread": 4.0, "speed": (1.8, 3.5),
                "size": (3, 6), "life_decay": 0.06, "shrink": 0.95,
                "particle_count": 2, "shape": "circle",
            },
            "jaffa_rebellion": None,
            # Lucian Alliance: Purple/pink smuggler engines (flashy, unstable)
            "lucian alliance": {
                "colors": [(255, 100, 200), (200, 80, 255), (150, 50, 200)],
                "emit_rate": 1, "spread": 6.0, "speed": (1.5, 3.0),
                "size": (2, 6), "life_decay": 0.055, "shrink": 0.93,
                "particle_count": 3, "shape": "circle",
            },
            "lucian_alliance": None,
        }
        # Alias fallbacks
        aliases = {"tauri": "tau'ri", "goauld": "goa'uld",
                   "jaffa_rebellion": "jaffa rebellion",
                   "lucian_alliance": "lucian alliance"}
        cfg = configs.get(faction_lower)
        if cfg is None and faction_lower in aliases:
            cfg = configs.get(aliases[faction_lower])
        if cfg is None:
            # Fallback: white generic
            cfg = {
                "colors": [(200, 200, 200), (255, 255, 255), (150, 150, 150)],
                "emit_rate": 1, "spread": 4.0, "speed": (2.0, 3.5),
                "size": (2, 5), "life_decay": 0.06, "shrink": 0.95,
                "particle_count": 2, "shape": "circle",
            }
        return cfg

    def _update_engine_trail(self):
        """Emit and update faction-styled engine exhaust particles."""
        cfg = self.thruster_config
        self._engine_emit_timer += 1
        boosting = self.thruster_boost_active

        emit_rate = max(1, cfg["emit_rate"] - (1 if boosting else 0))
        if self._engine_emit_timer >= emit_rate:
            self._engine_emit_timer = 0
            fdx, fdy = self.facing
            # Emit from behind the ship
            cx = self.x + self.width // 2 - fdx * (self.width // 2 + 5)
            cy = self.y - fdy * (self.height // 2 + 5)

            count = cfg["particle_count"] + (2 if boosting else 0)
            for _ in range(count):
                color = random.choice(cfg["colors"])
                speed_min, speed_max = cfg["speed"]
                spd = random.uniform(speed_min, speed_max)
                if boosting:
                    spd *= 1.5
                self.engine_particles.append({
                    'x': cx + random.uniform(-cfg["spread"], cfg["spread"]),
                    'y': cy + random.uniform(-cfg["spread"], cfg["spread"]),
                    'vx': -fdx * spd + random.uniform(-0.5, 0.5),
                    'vy': -fdy * spd + random.uniform(-0.5, 0.5),
                    'life': 1.0,
                    'size': random.uniform(*cfg["size"]) * (1.3 if boosting else 1.0),
                    'color': color,
                    'shape': cfg["shape"],
                })

        # Update particles
        to_remove = []
        for i, p in enumerate(self.engine_particles):
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= cfg["life_decay"]
            p['size'] *= cfg["shrink"]
            if p['life'] <= 0:
                to_remove.append(i)
        for i in reversed(to_remove):
            self.engine_particles.pop(i)

        # Budget cap (higher when boosting)
        max_particles = 80 if boosting else 50
        if len(self.engine_particles) > max_particles:
            self.engine_particles = self.engine_particles[-max_particles:]

    def set_facing(self, direction):
        """Set the ship facing direction and start smooth rotation."""
        if direction == self.facing:
            return
        self.facing = direction
        if self.current_beam:
            self.stop_beam()
        # Map direction to target angle (degrees, 0=right, CCW positive)
        angle_map = {
            (1, 0): 0,
            (-1, 0): 180,
            (0, -1): 90,
            (0, 1): -90,
        }
        self._target_angle = angle_map.get(direction, self._target_angle)

    def _update_rotation(self):
        """Smoothly interpolate visual rotation toward target angle.

        Uses pre-cached cardinal images as rotation bases to avoid the 180°
        artifact (vertical flip) that occurs when rotating image_right by 180°.
        pygame.transform.rotate positive angle = CCW on screen.
        """
        if self.image_right is None:
            return
        diff = self._target_angle - self._current_angle
        # Normalize to [-180, 180]
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        if abs(diff) < self._rotation_speed:
            self._current_angle = self._target_angle
        else:
            self._current_angle += self._rotation_speed if diff > 0 else -self._rotation_speed
        # Normalize current angle
        while self._current_angle > 180:
            self._current_angle -= 360
        while self._current_angle < -180:
            self._current_angle += 360
        # Only re-render when angle actually changed (avoids Surface alloc every frame)
        if not hasattr(self, '_cached_draw_angle') or abs(self._current_angle - self._cached_draw_angle) > 1:
            angle = self._current_angle
            # Pick nearest cardinal image as rotation base (max ±45° rotation).
            # This avoids the 180° rotation artifact where left-facing ships
            # appear vertically flipped (image_left uses correct horizontal flip).
            if -45 <= angle <= 45:
                base_img = self.image_right
                rot = angle
            elif 45 < angle < 135:
                base_img = self.image_up
                rot = angle - 90
            elif -135 < angle < -45:
                base_img = self.image_down
                rot = angle + 90
            else:  # abs(angle) >= 135 — left-facing
                base_img = self.image_left
                rot = angle - 180 if angle > 0 else angle + 180
            if abs(rot) < 1:
                self.image = base_img
            else:
                self.image = pygame.transform.rotate(base_img, rot)
            self._cached_draw_angle = self._current_angle

    def update_ally_ai(self, owner, enemies):
        """AI for friendly ally ships. Follow owner, engage enemies, return projectile."""
        if self.ally_lifetime > 0:
            self.ally_lifetime -= 1
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # Follow owner loosely (keep within 250px)
        ox = owner.x + owner.width // 2
        oy = owner.y
        dx = ox - (self.x + self.width // 2)
        dy = oy - self.y
        dist = math.hypot(dx, dy)

        if dist > 250:
            # Move toward owner
            if dist > 1:
                self.x += (dx / dist) * self.speed * 0.8
                self.y += (dy / dist) * self.speed * 0.8
        elif enemies:
            # Engage nearest enemy within 400px
            nearest = None
            nearest_dist = 400
            for e in enemies:
                ed = math.hypot(e.x - self.x, e.y - self.y)
                if ed < nearest_dist:
                    nearest = e
                    nearest_dist = ed
            if nearest:
                ex = nearest.x + nearest.width // 2
                ey = nearest.y
                edx = ex - (self.x + self.width // 2)
                edy = ey - self.y
                edist = math.hypot(edx, edy)
                # Approach to 200px range
                if edist > 200 and edist > 1:
                    self.x += (edx / edist) * self.speed * 0.6
                    self.y += (edy / edist) * self.speed * 0.6
                elif edist > 1:
                    # Strafe
                    perp_x = -edy / edist
                    perp_y = edx / edist
                    self.x += perp_x * self.speed * 0.4
                    self.y += perp_y * self.speed * 0.4

                # Face enemy
                if edx > 0:
                    self.set_facing((1, 0))
                else:
                    self.set_facing((-1, 0))

                # Fire at enemy
                if self.fire_cooldown <= 0 and edist < 400:
                    self.fire_cooldown = self.fire_rate
                    direction = (edx / edist, edy / edist) if edist > 1 else self.facing
                    from .projectiles import Laser
                    proj = Laser(self.x + self.width // 2, self.y, direction,
                               self.laser_color, speed=18)
                    proj.damage = 10
                    proj.is_player_proj = True
                    self._update_rotation()
                    self._update_engine_trail()
                    return proj

        # Face owner direction if idle
        if dx > 0:
            self.set_facing((1, 0))
        elif dx < 0:
            self.set_facing((-1, 0))

        self._update_rotation()
        self._update_engine_trail()
        return None

    def update_ai(self, target_ship, asteroids, other_ships=None):
        """Space-battle AI: approach to combat range, then strafe/orbit the target."""
        player_ship = target_ship  # local alias for backwards compat
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.beam_cooldown > 0:
            self.beam_cooldown -= 1
        if self.contact_damage_cooldown > 0:
            self.contact_damage_cooldown -= 1

        # Goa'uld passive: Shield Regeneration (also works for AI)
        if self.passive == "shield_regen":
            self.passive_state["no_hit_timer"] = self.passive_state.get("no_hit_timer", 0) + 1
            if self.passive_state["no_hit_timer"] >= 120 and self.shields < self.max_shields:
                self.shields = min(self.max_shields, self.shields + 0.3)

        # --- Vector to player ---
        player_cx = player_ship.x + player_ship.width // 2
        player_cy = player_ship.y
        dx = player_cx - (self.x + self.width // 2)
        dy = player_cy - self.y
        dist_to_player = math.hypot(dx, dy)

        # --- Behavior-specific AI dispatch ---
        if self._behavior == "swarm_lifesteal":
            self._ai_swarm_lifesteal(dx, dy, dist_to_player, player_ship)
            return
        elif self._behavior == "homing":
            self._ai_homing(dx, dy, dist_to_player, player_ship)
            return
        elif self._behavior == "shielded_charge":
            self._ai_shielded_charge(dx, dy, dist_to_player, player_ship, asteroids, other_ships)
            return
        elif self._behavior == "bomber":
            self._ai_bomber(dx, dy, dist_to_player, player_ship, asteroids, other_ships)
            return
        elif self._behavior == "mini_boss_spawner":
            self._ai_mini_boss(dx, dy, dist_to_player, player_ship, asteroids, other_ships)
            return
        elif self._behavior == "ori_boss":
            self._ai_ori_boss(dx, dy, dist_to_player, player_ship, asteroids, other_ships)
            return
        elif self._behavior == "wraith_boss":
            self._ai_wraith_boss(dx, dy, dist_to_player, player_ship, asteroids, other_ships)
            return
        # "paired" and "split_on_death" use standard strafe AI (handled by spawner/game.py)

        # --- Kamikaze behavior: charge straight at player ---
        if self.enemy_type == "kamikaze":
            if dist_to_player > 1:
                ux = dx / dist_to_player
                uy = dy / dist_to_player
                self.x += ux * self.speed
                self.y += uy * self.speed
            # Face player
            if dx > 0:
                self.set_facing((1, 0))
            elif dx < 0:
                self.set_facing((-1, 0))
            if self.current_beam:
                self.current_beam.update()
                self.beam_duration_timer += 1
                if self.beam_duration_timer >= 90:
                    self.stop_beam()
            self._update_rotation()
            self._update_engine_trail()
            return

        # --- Engage-at-range + strafe behaviour ---
        preferred_range = 275
        range_tolerance = 75
        move_x, move_y = 0.0, 0.0

        if dist_to_player > 1:
            ux = dx / dist_to_player
            uy = dy / dist_to_player
            strafe_sign = 1 if id(self) % 2 == 0 else -1
            perp_x = -uy * strafe_sign
            perp_y = ux * strafe_sign

            if dist_to_player > preferred_range + range_tolerance:
                move_x = ux * self.speed * 0.8
                move_y = uy * self.speed * 0.8
            elif dist_to_player < preferred_range - range_tolerance:
                move_x = -ux * self.speed * 0.4 + perp_x * self.speed * 0.5
                move_y = -uy * self.speed * 0.4 + perp_y * self.speed * 0.5
            else:
                drift = (dist_to_player - preferred_range) / range_tolerance
                move_x = ux * self.speed * 0.15 * drift + perp_x * self.speed * 0.5
                move_y = uy * self.speed * 0.15 * drift + perp_y * self.speed * 0.5

        # --- Asteroid dodge ---
        dodge_x, dodge_y = 0.0, 0.0
        closest_threat_dist = float('inf')
        for asteroid in asteroids:
            ax = asteroid.x - self.x
            ay = asteroid.y - self.y
            dist = math.hypot(ax, ay)
            threat_radius = asteroid.size + max(self.width, self.height) // 2 + 50

            if dist < 400 and dist < closest_threat_dist:
                future_x = asteroid.x + asteroid.vx * 30
                future_y = asteroid.y + asteroid.vy * 30
                future_dist = math.hypot(future_x - self.x, future_y - self.y)

                if future_dist < dist and dist < threat_radius + 200:
                    closest_threat_dist = dist
                    if dist > 1:
                        dodge_x = -(ax / dist) * self.speed * 1.0
                        dodge_y = -(ay / dist) * self.speed * 1.0

        # --- Separation (strong push to prevent overlap) ---
        sep_x, sep_y = 0.0, 0.0
        if other_ships:
            for other in other_ships:
                if other is self:
                    continue
                sx = self.x - other.x
                sy = self.y - other.y
                sdist = math.hypot(sx, sy)
                if sdist < 180:
                    if sdist > 1:
                        # Stronger push the closer they are (inverse distance)
                        force = min(8.0, 120.0 / max(sdist, 10))
                        sep_x += (sx / sdist) * force
                        sep_y += (sy / sdist) * force
                    else:
                        sep_x += random.choice([-5, 5])
                        sep_y += random.choice([-5, 5])

        # --- Combine: separation always applies, dodge overrides movement ---
        if dodge_x != 0 or dodge_y != 0:
            self.x += dodge_x + sep_x
            self.y += dodge_y + sep_y
        else:
            self.x += move_x + sep_x
            self.y += move_y + sep_y

        # --- Facing ---
        if dx > 0:
            self.set_facing((1, 0))
        elif dx < 0:
            self.set_facing((-1, 0))

        # No screen clamping for AI — despawn handled by game.py

        # Update beam if active
        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            if self.beam_duration_timer >= 90:
                self.stop_beam()

        # Smooth visual rotation
        self._update_rotation()
        # Engine trail
        self._update_engine_trail()

    def get_fury_multiplier(self):
        """Get Jaffa Warrior's Fury damage multiplier."""
        if self.passive == "warriors_fury":
            kills = self.passive_state.get("kills", 0)
            return 1.0 + min(kills * 0.02, 0.40)
        return 1.0

    def fire(self):
        """Fire weapon based on faction type."""
        direction = self.facing
        dx, dy = direction
        if dx == 1:
            fire_x = self.x + self.width
            fire_y = self.y
        elif dx == -1:
            fire_x = self.x
            fire_y = self.y
        elif dy == -1:
            fire_x = self.x + self.width // 2
            fire_y = self.y - self.height // 2
        else:
            fire_x = self.x + self.width // 2
            fire_y = self.y + self.height // 2

        if self.weapon_type == "beam":
            if self.beam_cooldown <= 0 and not self.current_beam:
                self.current_beam = ContinuousBeam(self, direction, self.laser_color,
                                                   self.screen_width, self.screen_height)
                self.beam_duration_timer = 0
                fury = self.get_fury_multiplier()
                if fury > 1.0:
                    self.current_beam.damage_per_frame *= fury
            return self.current_beam

        if self.fire_cooldown <= 0:
            self.fire_cooldown = self.fire_rate

            proj = None
            if self.weapon_type == "missile":
                proj = Missile(fire_x, fire_y, direction, self.laser_color)
            elif self.weapon_type == "energy_ball":
                proj = EnergyBall(fire_x, fire_y, direction, self.laser_color)
            elif self.weapon_type == "staff":
                proj = JaffaStaffBlast(fire_x, fire_y, direction, self.laser_color)
            elif self.weapon_type == "plasma_lance":
                from .projectiles import PlasmaLance
                proj = PlasmaLance(fire_x, fire_y, direction, self.laser_color)
            elif self.weapon_type == "disruptor_pulse":
                from .projectiles import DisruptorPulse
                proj = DisruptorPulse(fire_x, fire_y, direction, self.laser_color)
            elif self.weapon_type == "drone_pulse":
                # Ancient drone: rapid golden homing shots
                proj = Laser(fire_x, fire_y, direction, (255, 200, 50), speed=16)
                proj.damage = 12
                proj.homing_strength = 0.03  # slight tracking
            elif self.weapon_type == "dual_staff":
                # Two parallel staff blasts
                perp_x = -direction[1] * 12
                perp_y = direction[0] * 12
                proj1 = JaffaStaffBlast(fire_x + perp_x, fire_y + perp_y, direction, self.laser_color)
                proj2 = JaffaStaffBlast(fire_x - perp_x, fire_y - perp_y, direction, self.laser_color)
                proj1.damage = 10
                proj2.damage = 10
                proj1.is_player_proj = self.is_player
                proj2.is_player_proj = self.is_player
                fury = self.get_fury_multiplier()
                if fury > 1.0:
                    proj1.damage = int(proj1.damage * fury)
                    proj2.damage = int(proj2.damage * fury)
                return [proj1, proj2]
            else:
                proj = Laser(fire_x, fire_y, direction, self.laser_color)

            if proj:
                proj.is_player_proj = self.is_player
                fury = self.get_fury_multiplier()
                if fury > 1.0:
                    proj.damage = int(proj.damage * fury)
            return proj
        return None

    def secondary_fire(self):
        """Fire secondary weapon based on faction. Returns list of projectiles/effects."""
        if self.secondary_cooldown > 0 or not self.secondary_type:
            return []
        self.secondary_cooldown = self.secondary_fire_rate

        dx, dy = self.facing
        cx = self.x + self.width // 2
        cy = self.y
        results = []

        if self.secondary_type == "railgun":
            # Tau'ri Railgun: single piercing high-damage shot
            proj = RailgunShot(cx + dx * 40, cy + dy * 40, self.facing, self.laser_color)
            proj.is_player_proj = self.is_player
            results.append(("projectile", proj))

        elif self.secondary_type == "staff_barrage":
            # Goa'uld Staff Barrage: 3-shot fan spread
            base_angle = math.atan2(dy, dx)
            for spread in [-0.25, 0, 0.25]:  # ~14 degree spread
                angle = base_angle + spread
                sdx = math.cos(angle)
                sdy = math.sin(angle)
                # Normalize to unit-ish direction
                proj = Laser(cx + dx * 30, cy + dy * 30, (sdx, sdy),
                           self.laser_color, speed=20)
                proj.damage = 18
                proj.is_player_proj = self.is_player
                results.append(("projectile", proj))

        elif self.secondary_type == "ion_pulse":
            # Asgard Ion Pulse: AoE burst around ship
            results.append(("ion_pulse", {"x": cx, "y": cy, "damage": 35, "radius": 200}))

        elif self.secondary_type == "war_cry":
            # Jaffa War Cry: 4-second attack speed + damage buff
            self.secondary_buff_timer = 240  # 4 seconds
            results.append(("war_cry", {"duration": 240}))

        elif self.secondary_type == "scatter_mines":
            # Lucian Alliance Scatter Mines: drop 4 mines behind ship
            for i in range(4):
                offset_angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(30, 80)
                mine_x = cx - dx * 60 + math.cos(offset_angle) * dist
                mine_y = cy - dy * 60 + math.sin(offset_angle) * dist
                mine = ProximityMine(mine_x, mine_y, self.laser_color)
                mine.is_player_proj = self.is_player
                results.append(("mine", mine))

        elif self.secondary_type == "transporter_beam":
            # Asgard Beliskner: teleport nearest enemy 300px away
            results.append(("transporter_beam", {"x": cx, "y": cy, "range": 400, "teleport_dist": 300}))

        elif self.secondary_type == "sensor_sweep":
            # Asgard Research: mark enemies in 400px for 8s, +30% dmg taken
            results.append(("sensor_sweep", {"x": cx, "y": cy, "radius": 400, "duration": 480}))

        elif self.secondary_type == "ribbon_blast":
            # Goa'uld Apophis: 150px cone, 40 dmg + knockback
            results.append(("ribbon_blast", {"x": cx, "y": cy, "damage": 40,
                                              "radius": 150, "direction": self.facing}))

        elif self.secondary_type == "asgard_beam":
            # Tau'ri Daedalus: short ContinuousBeam burst (45 frames)
            if not self.current_beam:
                beam = ContinuousBeam(self, self.facing, (0, 255, 255),
                                       self.screen_width, self.screen_height)
                beam.damage_per_frame = 0.8
                self.current_beam = beam
                self.beam_duration_timer = 0
                # Override beam stop time to 45 frames
                self._asgard_beam_override = 45
                results.append(("beam", beam))

        elif self.secondary_type == "jaffa_rally":
            # Jaffa Ha'tak Refit: spawn 2 temp ally ships for 10s
            results.append(("jaffa_rally", {"x": cx, "y": cy, "count": 2, "duration": 600}))

        elif self.secondary_type == "drone_salvo":
            # Aurora-class: burst of 6 homing Ancient drones in a spread
            base_angle = math.atan2(dy, dx)
            for i in range(6):
                spread = (i - 2.5) * 0.2  # fan of ~1 radian total
                angle = base_angle + spread
                sdx = math.cos(angle)
                sdy = math.sin(angle)
                proj = Laser(cx + dx * 30, cy + dy * 30, (sdx, sdy),
                           (255, 200, 50), speed=14)
                proj.damage = 15
                proj.homing_strength = 0.05
                proj.is_player_proj = self.is_player
                results.append(("projectile", proj))

        elif self.secondary_type == "eye_of_ra":
            # Anubis Eye of Ra: devastating focused golden beam (5s cooldown)
            # Fires a concentrated beam that deals massive damage to everything in a line
            results.append(("eye_of_ra", {"x": cx, "y": cy, "direction": self.facing,
                                          "damage": 60, "range": 600}))

        return results

    def stop_beam(self):
        """Stop the continuous beam weapon and start cooldown."""
        if self.current_beam:
            self.beam_cooldown = self.fire_rate
        self.current_beam = None

    def get_rect(self):
        # Use actual image dimensions for collision (handles non-square rotated ships)
        if self.image:
            iw = self.image.get_width()
            ih = self.image.get_height()
            cx = self.x + self.width // 2
            cy = self.y
            return pygame.Rect(int(cx - iw // 2), int(cy - ih // 2), iw, ih)
        return pygame.Rect(int(self.x), int(self.y - self.height // 2), self.width, self.height)

    def get_image(self):
        """Return the current facing image."""
        return self.image

    def _play_shield_hit_sound(self):
        """Play shield hit sound effect (lazy-loaded, class-level cache)."""
        if not Ship._shield_hit_sound_loaded:
            Ship._shield_hit_sound_loaded = True
            path = os.path.join(os.path.dirname(__file__), "..", "assets", "audio", "space_shooter", "shield_hit.ogg")
            if os.path.exists(path):
                try:
                    Ship._shield_hit_sound = pygame.mixer.Sound(path)
                except pygame.error:
                    pass
        if Ship._shield_hit_sound:
            try:
                from game_settings import get_settings
                vol = get_settings().get_effective_sfx_volume()
                Ship._shield_hit_sound.set_volume(vol)
                Ship._shield_hit_sound.play()
            except (pygame.error, Exception):
                pass

    def take_damage(self, amount, is_asteroid=False):
        """Take damage - all damage hits shields first, overflow goes to health."""
        # Tau'ri passive: Armor Plating - 15% damage reduction
        if self.passive == "armor_plating":
            amount *= 0.85

        # Heavy armor passive: 25% damage reduction
        if self.passive == "heavy_armor":
            amount *= 0.75

        # Anubis Shield passive: absorb hits completely (limited charges)
        if self.passive == "anubis_shield":
            charges = self.passive_state.get("absorb_charges", 0)
            if charges > 0 and amount > 0:
                self.passive_state["absorb_charges"] = charges - 1
                return False  # Hit fully absorbed

        # Shields absorb damage first (both asteroid and weapon damage)
        if self.shields > 0:
            absorbed = min(self.shields, amount)
            self.shields -= absorbed
            amount -= absorbed
            self.shield_hit_timer = 60
            # Play shield hit sound for player
            if self.is_player:
                self._play_shield_hit_sound()
            # Adaptive shields passive: count shield hits
            if self.passive == "adaptive_shields":
                self.passive_state["shield_hits"] = self.passive_state.get("shield_hits", 0) + 1
                if self.passive_state["shield_hits"] >= 5:
                    self.passive_state["shield_hits"] = 0
                    self.passive_state["dmg_buff_timer"] = 300  # 5s of +10% dmg

        if amount > 0:
            self.health -= amount
            if self.passive == "shield_regen":
                self.passive_state["no_hit_timer"] = 0

        return self.health <= 0

    def draw(self, surface, time_tick=0, camera=None):
        """Draw the ship with shield effects and health/shield bars.

        If camera is provided, converts world-space to screen-space.
        """
        if camera:
            draw_x, draw_y = camera.world_to_screen(self.x, self.y)
        else:
            draw_x, draw_y = self.x, self.y

        if self.shield_hit_timer > 0:
            self.shield_hit_timer -= 1

        shield_pct = self.shields / max(self.max_shields, 1)
        bubble_center = (int(draw_x + self.width // 2), int(draw_y))
        ship_extent = max(self.width, self.height)
        base_radius = int(ship_extent * 0.55)

        # --- Draw engine trail particles (faction-styled) ---
        for p in self.engine_particles:
            if camera:
                px, py = camera.world_to_screen(p['x'], p['y'])
            else:
                px, py = p['x'], p['y']
            alpha = max(0, int(p['life'] * 200))
            size = max(1, int(p['size']))
            base_color = p.get('color', self.laser_color)
            # Brighten toward white as life is fresh
            r = min(255, base_color[0] + int(100 * p['life']))
            g = min(255, base_color[1] + int(80 * p['life']))
            b = min(255, base_color[2] + int(50 * p['life']))
            shape = p.get('shape', 'circle')
            p_surf = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
            c = size + 2
            if shape == 'diamond':
                points = [(c, c - size), (c + size, c), (c, c + size), (c - size, c)]
                pygame.draw.polygon(p_surf, (r, g, b, alpha), points)
            else:
                # Outer glow
                if size > 2:
                    pygame.draw.circle(p_surf, (r, g, b, alpha // 3), (c, c), size + 1)
                pygame.draw.circle(p_surf, (r, g, b, alpha), (c, c), size)
            surface.blit(p_surf, (int(px) - c, int(py) - c))

        # --- Always-visible subtle shield aura when shields > 0 ---
        if self.shields > 0:
            pulse = math.sin(time_tick * 0.04) * 0.08 + 1.0
            r = int(base_radius * pulse)
            sz = r * 2 + 20
            aura = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = sz // 2

            num_segments = 6
            seg_angle_offset = time_tick * 0.02
            for i in range(num_segments):
                angle = seg_angle_offset + i * (math.pi * 2 / num_segments)
                arc_alpha = int(25 * shield_pct + 10)
                ax = c + int(math.cos(angle) * r * 0.9)
                ay = c + int(math.sin(angle) * r * 0.9)
                pygame.draw.circle(aura, (80, 180, 255, arc_alpha), (ax, ay), int(r * 0.35), 1)

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

            flash_alpha = int(180 * visibility)
            pygame.draw.circle(flare, (150, 220, 255, flash_alpha), (c, c), flare_r, 4)
            inner_alpha = int(100 * visibility)
            pygame.draw.circle(flare, (100, 200, 255, inner_alpha), (c, c), int(flare_r * 0.7))
            spark_alpha = int(220 * visibility)
            pygame.draw.circle(flare, (220, 240, 255, spark_alpha), (c, c - int(flare_r * 0.5)), int(flare_r * 0.15))

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

        # Draw ship — center image on ship position (handles non-square rotated images)
        if self.image:
            iw = self.image.get_width()
            ih = self.image.get_height()
            cx = draw_x + self.width // 2
            cy = draw_y
            surface.blit(self.image, (int(cx - iw // 2), int(cy - ih // 2)))
        else:
            fdx, fdy = self.facing
            cx = draw_x + self.width // 2
            cy = draw_y
            hw = self.width // 2
            hh = self.height // 2
            if fdx == 1:
                points = [(cx + hw, cy), (cx - hw, cy - hh), (cx - hw, cy + hh)]
            elif fdx == -1:
                points = [(cx - hw, cy), (cx + hw, cy - hh), (cx + hw, cy + hh)]
            elif fdy == -1:
                points = [(cx, cy - hh), (cx - hw, cy + hh), (cx + hw, cy + hh)]
            else:
                points = [(cx, cy + hh), (cx - hw, cy - hh), (cx + hw, cy - hh)]
            pygame.draw.polygon(surface, self.laser_color, points)
            pygame.draw.polygon(surface, (255, 255, 255), points, 2)

        # Health bar
        bar_width = self.width
        bar_height = 6
        bar_x = draw_x
        health_bar_y = draw_y - self.height // 2 - 18

        pygame.draw.rect(surface, (40, 40, 40), (bar_x, health_bar_y, bar_width, bar_height))
        health_pct = self.health / max(self.max_health, 1)
        health_color = (0, 255, 0) if health_pct > 0.5 else (255, 255, 0) if health_pct > 0.25 else (255, 0, 0)
        pygame.draw.rect(surface, health_color, (bar_x, health_bar_y, int(bar_width * health_pct), bar_height))
        pygame.draw.rect(surface, (200, 200, 200), (bar_x, health_bar_y, bar_width, bar_height), 1)

        # Shield bar
        if self.max_shields > 0:
            shield_bar_y = health_bar_y + bar_height + 2
            shield_bar_h = 4
            pygame.draw.rect(surface, (20, 30, 50), (bar_x, shield_bar_y, bar_width, shield_bar_h))
            pygame.draw.rect(surface, (80, 170, 255), (bar_x, shield_bar_y, int(bar_width * shield_pct), shield_bar_h))
            pygame.draw.rect(surface, (100, 180, 255), (bar_x, shield_bar_y, bar_width, shield_bar_h), 1)

        # Ori fighter extra shield bar (golden)
        if self._shield_max > 0:
            ori_bar_y = (shield_bar_y + shield_bar_h + 2) if self.max_shields > 0 else (health_bar_y + bar_height + 2)
            ori_bar_h = 3
            ori_pct = self._shield_hp / max(self._shield_max, 1)
            pygame.draw.rect(surface, (40, 30, 10), (bar_x, ori_bar_y, bar_width, ori_bar_h))
            pygame.draw.rect(surface, (255, 215, 100), (bar_x, ori_bar_y, int(bar_width * ori_pct), ori_bar_h))
            pygame.draw.rect(surface, (200, 180, 80), (bar_x, ori_bar_y, bar_width, ori_bar_h), 1)

    # --- Behavior AI methods ---

    def _ai_swarm_lifesteal(self, dx, dy, dist, target):
        """Wraith dart: weaving approach, heals on contact."""
        self._swarm_weave += 0.08
        if dist > 1:
            ux = dx / dist
            uy = dy / dist
            # Weave perpendicular
            weave = math.sin(self._swarm_weave) * 3.0
            perp_x = -uy
            perp_y = ux
            self.x += ux * self.speed * 0.7 + perp_x * weave
            self.y += uy * self.speed * 0.7 + perp_y * weave
        # Face player
        if dx > 0:
            self.set_facing((1, 0))
        else:
            self.set_facing((-1, 0))
        self._update_rotation()
        self._update_engine_trail()

    def _ai_homing(self, dx, dy, dist, target):
        """Ancient drone: smooth pursuit curves, orbits if close."""
        # Angular turn toward target
        target_angle = math.atan2(dy, dx)
        angle_diff = target_angle - self._homing_angle
        # Normalize
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        # Turn at max 5 degrees/frame
        max_turn = math.radians(5)
        if abs(angle_diff) > max_turn:
            self._homing_angle += max_turn if angle_diff > 0 else -max_turn
        else:
            self._homing_angle = target_angle

        # Always move forward along current heading
        self.x += math.cos(self._homing_angle) * self.speed
        self.y += math.sin(self._homing_angle) * self.speed

        # Face movement direction
        if math.cos(self._homing_angle) > 0:
            self.set_facing((1, 0))
        else:
            self.set_facing((-1, 0))
        self._update_rotation()
        self._update_engine_trail()

    def _ai_shielded_charge(self, dx, dy, dist, target, asteroids, other_ships):
        """Ori fighter: ranged while shields up, zealous charge when shields break."""
        # Check if extra shields are broken
        if self._shield_hp > 0:
            # Standard ranged behavior (reuse normal strafe logic)
            self._ai_standard_strafe(dx, dy, dist, target, asteroids, other_ships, preferred_range=350)
        else:
            # Zealous charge!
            if not self._charging:
                self._charging = True
                self._charge_timer = 180  # 3 seconds of charging
                self.speed = int(self.speed * 1.5)

            self._charge_timer -= 1
            if dist > 1:
                ux = dx / dist
                uy = dy / dist
                self.x += ux * self.speed
                self.y += uy * self.speed
            if dx > 0:
                self.set_facing((1, 0))
            else:
                self.set_facing((-1, 0))
            self._update_rotation()
            self._update_engine_trail()

    def _ai_bomber(self, dx, dy, dist, target, asteroids, other_ships):
        """Al'kesh bomber: stays at 400px range, drops area bombs."""
        self._bomber_timer += 1
        self._ai_standard_strafe(dx, dy, dist, target, asteroids, other_ships, preferred_range=400)

    def _ai_mini_boss(self, dx, dy, dist, target, asteroids, other_ships):
        """Wraith hive: orbits at 500px, spawns darts."""
        self._spawner_timer += 1
        self._ai_standard_strafe(dx, dy, dist, target, asteroids, other_ships, preferred_range=500)

    def _ai_ori_boss(self, dx, dy, dist, target, asteroids, other_ships):
        """Ori mothership: slowly drifts toward action, fires sweeping beam + regular lasers."""
        # Slow drift toward target
        if dist > 1:
            ux = dx / dist
            uy = dy / dist
            self.x += ux * self.speed
            self.y += uy * self.speed

        # Face target
        if dx > 0:
            self.set_facing((1, 0))
        else:
            self.set_facing((-1, 0))

        # Ori boss beam timer (tracked by game.py via _ori_beam_timer)
        self._ori_beam_timer = getattr(self, '_ori_beam_timer', 0) + 1

        # Fire regular golden lasers between beam charges (every 60 frames)
        self.ai_fire_timer = getattr(self, 'ai_fire_timer', 0)
        if self.ai_fire_timer <= 0 and dist < 800:
            self.ai_fire_timer = 60
            if dist > 1:
                direction = (dx / dist, dy / dist)
                proj = Laser(self.x + self.width // 2, self.y, direction,
                            (255, 220, 80), speed=12)
                proj.damage = 15
                proj.is_player_proj = False
                # Store for game.py to collect (game.py checks this in AI loop)
                if not hasattr(self, '_pending_projectiles'):
                    self._pending_projectiles = []
                self._pending_projectiles.append(proj)

        self._update_rotation()
        self._update_engine_trail()

    def _ai_wraith_boss(self, dx, dy, dist, target, asteroids, other_ships):
        """Wraith Hive boss: drifts toward action, fires purple beam + spawns darts via _pending."""
        # Slow drift toward target
        if dist > 1:
            ux = dx / dist
            uy = dy / dist
            self.x += ux * self.speed
            self.y += uy * self.speed

        # Face target
        if dx > 0:
            self.set_facing((1, 0))
        else:
            self.set_facing((-1, 0))

        # Wraith beam timer (tracked by game.py)
        self._ori_beam_timer = getattr(self, '_ori_beam_timer', 0) + 1

        # Fire purple life-drain bolts between beam charges (every 45 frames, faster than Ori)
        self.ai_fire_timer = getattr(self, 'ai_fire_timer', 0)
        if self.ai_fire_timer <= 0 and dist < 700:
            self.ai_fire_timer = 45
            if dist > 1:
                direction = (dx / dist, dy / dist)
                proj = Laser(self.x + self.width // 2, self.y, direction,
                            (160, 40, 255), speed=10)
                proj.damage = 12
                proj.is_player_proj = False
                proj._wraith_lifesteal = True  # game.py uses this for heal-on-hit
                if not hasattr(self, '_pending_projectiles'):
                    self._pending_projectiles = []
                self._pending_projectiles.append(proj)

        # Spawn wraith darts periodically (every 240 frames = 4s, max 3 alive)
        self._wraith_spawn_timer = getattr(self, '_wraith_spawn_timer', 0) + 1
        if not hasattr(self, '_spawned_darts'):
            self._spawned_darts = []
        if self._wraith_spawn_timer >= 240 and len(self._spawned_darts) < 3:
            self._wraith_spawn_timer = 0
            # game.py handles actual spawn via _pending_spawns
            if not hasattr(self, '_pending_spawns'):
                self._pending_spawns = []
            self._pending_spawns.append("wraith_dart")

        self._update_rotation()
        self._update_engine_trail()

    def _ai_standard_strafe(self, dx, dy, dist, target, asteroids, other_ships, preferred_range=275):
        """Common strafe AI reused by multiple behaviors."""
        range_tolerance = 75
        move_x, move_y = 0.0, 0.0

        if dist > 1:
            ux = dx / dist
            uy = dy / dist
            strafe_sign = 1 if id(self) % 2 == 0 else -1
            perp_x = -uy * strafe_sign
            perp_y = ux * strafe_sign

            if dist > preferred_range + range_tolerance:
                move_x = ux * self.speed * 0.8
                move_y = uy * self.speed * 0.8
            elif dist < preferred_range - range_tolerance:
                move_x = -ux * self.speed * 0.4 + perp_x * self.speed * 0.5
                move_y = -uy * self.speed * 0.4 + perp_y * self.speed * 0.5
            else:
                drift = (dist - preferred_range) / range_tolerance
                move_x = ux * self.speed * 0.15 * drift + perp_x * self.speed * 0.5
                move_y = uy * self.speed * 0.15 * drift + perp_y * self.speed * 0.5

        # Asteroid dodge
        dodge_x, dodge_y = 0.0, 0.0
        if asteroids:
            closest_threat_dist = float('inf')
            for asteroid in asteroids:
                ax = asteroid.x - self.x
                ay = asteroid.y - self.y
                ad = math.hypot(ax, ay)
                if ad < 400 and ad < closest_threat_dist:
                    threat_radius = asteroid.size + max(self.width, self.height) // 2 + 50
                    if ad < threat_radius + 200 and ad > 1:
                        closest_threat_dist = ad
                        dodge_x = -(ax / ad) * self.speed * 1.0
                        dodge_y = -(ay / ad) * self.speed * 1.0

        # Separation
        sep_x, sep_y = 0.0, 0.0
        if other_ships:
            for other in other_ships:
                if other is self:
                    continue
                sx = self.x - other.x
                sy = self.y - other.y
                sdist = math.hypot(sx, sy)
                if sdist < 180:
                    if sdist > 1:
                        force = min(8.0, 120.0 / max(sdist, 10))
                        sep_x += (sx / sdist) * force
                        sep_y += (sy / sdist) * force

        if dodge_x != 0 or dodge_y != 0:
            self.x += dodge_x + sep_x
            self.y += dodge_y + sep_y
        else:
            self.x += move_x + sep_x
            self.y += move_y + sep_y

        if dx > 0:
            self.set_facing((1, 0))
        elif dx < 0:
            self.set_facing((-1, 0))

        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            if self.beam_duration_timer >= 90:
                self.stop_beam()
        self._update_rotation()
        self._update_engine_trail()
