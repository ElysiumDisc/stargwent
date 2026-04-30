"""Ship class for player and AI ships."""

import pygame
import math
import random
import os

from .projectiles import (ContinuousBeam, Laser, Missile, EnergyBall,
                          JaffaStaffBlast, RailgunShot, ProximityMine,
                          AncientDrone)


# --- Ship variant definitions ---
# Each faction maps to a list of variant dicts. Index 0 = default ship.
# Fields: name, image_file, image_orientation ("left"=faces left, "up"=faces up, "down"=faces down, "right"),
#         weapon_type, fire_rate, secondary_type, secondary_fire_rate,
#         passive, passive_state, description
# Faction → shield bubble RGB colors (bubble, rim, inner glow)
SHIELD_COLORS = {
    "tau'ri":          ((80, 190, 255), (120, 210, 255), (90, 200, 255)),
    "tauri":           ((80, 190, 255), (120, 210, 255), (90, 200, 255)),
    "asgard":          ((80, 190, 255), (120, 210, 255), (90, 200, 255)),
    "goa'uld":         ((255, 160, 50), (255, 190, 80), (255, 140, 40)),
    "goauld":          ((255, 160, 50), (255, 190, 80), (255, 140, 40)),
    "jaffa rebellion": ((255, 140, 50), (255, 170, 70), (255, 120, 40)),
    "jaffa_rebellion": ((255, 140, 50), (255, 170, 70), (255, 120, 40)),
    "lucian alliance": ((255, 140, 70), (255, 170, 90), (255, 120, 50)),
    "lucian_alliance": ((255, 140, 70), (255, 170, 90), (255, 120, 50)),
}
_DEFAULT_SHIELD_COLOR = ((80, 190, 255), (120, 210, 255), (90, 200, 255))

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
        {
            "name": "Loki's Lab Ship",
            "image_file": "asgard_ship_alt_3.png",
            "image_orientation": "down",
            "weapon_type": "nanite_swarm",
            "fire_rate": 25,
            "secondary_type": "sensor_sweep",
            "secondary_fire_rate": 420,
            "passive": "analyzer",
            "passive_state": {},
            "description": "Nanite swarm replicates on kill",
        },
    ],
    "goa'uld": [
        {
            "name": "Ha'tak",
            "image_file": "goa'uld_ship.png",
            "image_orientation": "right",
            "weapon_type": "laser",
            "fire_rate": 14,
            "secondary_type": "alkesh_deploy",
            "secondary_fire_rate": 300,
            "passive": "shield_regen",
            "passive_state": {"no_hit_timer": 0},
            "description": "Deploy Al'kesh bombers, shield regen",
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
        {
            "name": "Tok'ra Tunneler",
            "image_file": "jaffa_rebellion_ship.png",
            "image_orientation": "left",
            "weapon_type": "tunnel_crystal",
            "fire_rate": 35,
            "secondary_type": "railgun",
            "secondary_fire_rate": 180,
            "passive": "ancient_shields",
            "passive_state": {"regen_rate": 0.2},
            "description": "Gravity trap crystals, pulls enemies in",
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
    "wraith": [
        {
            "name": "Wraith Hive Cruiser",
            "image_file": "wraith_ship.png",
            "image_orientation": "down",
            "weapon_type": "wraith_culling",
            "fire_rate": 120,
            "secondary_type": "ribbon_blast",
            "secondary_fire_rate": 240,
            "passive": "sarcophagus_regen",
            "passive_state": {},
            "description": "Life-steal beam, heals 25% damage dealt",
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
        self._aim_override = None  # Set by game.py auto-aim system
        self.original_size = 120
        self.scale_factor = 1.2
        self.width = int(self.original_size * self.scale_factor)
        self.height = int(self.original_size * self.scale_factor)
        # Smooth rotation state
        self._current_angle = 0.0 if is_player else 180.0  # Degrees, 0=right
        self._target_angle = self._current_angle
        self._rotation_speed = 18.0  # Degrees per frame
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
            "wraith": (160, 40, 255),
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
        self._strafe_sign = 1 if random.random() > 0.5 else -1
        self._strafe_flip_timer = random.randint(120, 180)

        # Ally ship attributes
        self.is_friendly = False
        self.ally_owner = None
        self.ally_lifetime = 0
        self.is_miniship = False

        # Smooth velocity-based movement (player only)
        self.vx = 0.0
        self.vy = 0.0
        self.acceleration = 1.5  # How fast we reach top speed
        self.friction = 0.82  # Deceleration when no input (0.0 = instant stop, 1.0 = no friction)

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
                "wraith": ("wraith_ship.png", "down"),
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
            # NOTE: self.image stays as the right-facing base so that
            # spawner/game re-cache code (which copies from self.image)
            # always derives correct directional images.
            # _update_rotation() sets the display image on the first tick.

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
            if abs(self.vx) < 0.05:
                self.vx = 0
            if abs(self.vy) < 0.05:
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
            # Wraith: Sickly green-purple organic bio-engines
            "wraith": {
                "colors": [(160, 40, 255), (100, 200, 80), (80, 255, 120)],
                "emit_rate": 1, "spread": 5.0, "speed": (1.5, 3.0),
                "size": (3, 6), "life_decay": 0.05, "shrink": 0.93,
                "particle_count": 2, "shape": "circle",
            },
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

        # Budget cap (higher when boosting, lower for AI ships)
        if self.is_player:
            max_particles = 80 if boosting else 50
        else:
            max_particles = 40
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
            (1, -1): 45,
            (1, 1): -45,
            (-1, -1): 135,
            (-1, 1): -135,
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

    def update_miniship_ai(self, owner, enemies, formation_angle=0, overdrive=False):
        """SC2 Carrier-style interceptor AI: launch, orbit, attack-run, return.

        Interceptors launch from the carrier ship, orbit in formation when
        idle, dive toward enemies for burst-fire attack runs, then pull out
        and return to orbit.  Faction-specific weapons.

        Args:
            owner: The player Ship this miniship escorts.
            enemies: List of enemy Ships to engage.
            formation_angle: Radians offset for formation orbit position.
            overdrive: If True, halve fire cooldown for doubled fire rate.

        Returns:
            A projectile if fired, else None.
        """
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # Smooth velocity tracking (init once)
        if not hasattr(self, '_mini_vx'):
            self._mini_vx = 0.0
            self._mini_vy = 0.0
            self._strafe_dir = 1
            self._strafe_timer = 0

        # Attack run state machine (init once)
        if not hasattr(self, '_attack_state'):
            self._attack_state = "approach"
            self._attack_burst_count = 0
            self._pullout_timer = 0

        # --- Compute orbit anchor around owner ---
        orbit_radius = 120
        ox = owner.x + owner.width // 2 + math.cos(formation_angle) * orbit_radius
        oy = owner.y + math.sin(formation_angle) * orbit_radius

        # --- Launch phase: fly out from carrier before engaging ---
        if getattr(self, '_launch_phase', False):
            self._launch_timer = getattr(self, '_launch_timer', 30) - 1
            dx = ox - (self.x + self.width // 2)
            dy = oy - self.y
            dist = math.hypot(dx, dy)
            if dist > 15 and self._launch_timer > 0:
                speed_mult = 2.0
                self._mini_vx = (dx / max(dist, 1)) * self.speed * speed_mult
                self._mini_vy = (dy / max(dist, 1)) * self.speed * speed_mult
                self.x += self._mini_vx
                self.y += self._mini_vy
                self._ai_face_target(dx, dy) if hasattr(self, '_ai_face_target') else None
                self._update_rotation()
                self._update_engine_trail()
                return None
            self._launch_phase = False

        # --- Find best target: prioritize low-HP enemies for finishing blows ---
        leash = 500
        nearest = None
        nearest_score = float('inf')
        owner_cx = owner.x + owner.width // 2
        owner_cy = owner.y
        for e in enemies:
            ed = math.hypot(e.x - owner_cx, e.y - owner_cy)
            if ed < leash:
                md = math.hypot(e.x - self.x, e.y - self.y)
                hp_ratio = e.health / max(e.max_health, 1)
                score = md * (0.3 + hp_ratio * 0.7)
                if score < nearest_score:
                    nearest = e
                    nearest_score = score

        target_vx = 0.0
        target_vy = 0.0
        proj = None

        if nearest:
            ex = nearest.x + nearest.width // 2
            ey = nearest.y
            edx = ex - (self.x + self.width // 2)
            edy = ey - self.y
            edist = math.hypot(edx, edy)

            if edist > 1:
                nx, ny = edx / edist, edy / edist

                # SC2-style attack run state machine
                if self._attack_state == "approach":
                    # Close to engagement range
                    target_vx = nx * self.speed * 0.9
                    target_vy = ny * self.speed * 0.9
                    if edist < 150:
                        self._attack_state = "strafe"
                        self._attack_burst_count = 0
                        self._strafe_timer = 0

                elif self._attack_state == "strafe":
                    # Fire burst of 3 shots while strafing
                    self._strafe_timer += 1
                    if self._strafe_timer >= 45:
                        self._strafe_dir *= -1
                        self._strafe_timer = 0
                    target_vx = -ny * self.speed * 0.6 * self._strafe_dir
                    target_vy = nx * self.speed * 0.6 * self._strafe_dir
                    if edist < 80:
                        target_vx -= nx * self.speed * 0.3
                        target_vy -= ny * self.speed * 0.3
                    # After 3 shots, pull out
                    if self._attack_burst_count >= 3:
                        self._attack_state = "pullout"
                        self._pullout_timer = 40

                elif self._attack_state == "pullout":
                    # Retreat back toward orbit anchor
                    self._pullout_timer -= 1
                    pull_dx = ox - (self.x + self.width // 2)
                    pull_dy = oy - self.y
                    pull_dist = math.hypot(pull_dx, pull_dy)
                    if pull_dist > 1:
                        target_vx = (pull_dx / pull_dist) * self.speed * 1.2
                        target_vy = (pull_dy / pull_dist) * self.speed * 1.2
                    if self._pullout_timer <= 0:
                        self._attack_state = "approach"
                        self._attack_burst_count = 0

            # Face direction: during pullout, face movement dir; otherwise face enemy
            if self._attack_state == "pullout":
                # Face movement direction during retreat (not backwards at enemy)
                mvx, mvy = self._mini_vx, self._mini_vy
                mspd = math.hypot(mvx, mvy)
                if mspd > 0.5:
                    avx, avy = abs(mvx), abs(mvy)
                    sx = 1 if mvx > 0 else -1
                    sy = -1 if mvy < 0 else 1
                    if avx > 0.35 and avy > 0.35 and min(avx, avy) / max(avx, avy) > 0.4:
                        self.set_facing((sx, sy))
                    elif avx >= avy:
                        self.set_facing((sx, 0))
                    else:
                        self.set_facing((0, sy))
            elif edist > 1:
                # Face enemy (8-direction aware)
                avx, avy = abs(edx), abs(edy)
                sx = 1 if edx > 0 else -1
                sy = -1 if edy < 0 else 1
                if avx > 0.35 and avy > 0.35 and min(avx, avy) / max(avx, avy) > 0.4:
                    self.set_facing((sx, sy))
                elif avx >= avy:
                    self.set_facing((sx, 0))
                else:
                    self.set_facing((0, sy))

            # Fire at enemy — faction-specific weapons
            effective_rate = max(3, self.fire_rate // 2) if overdrive else self.fire_rate
            # Burst fire: use tighter cooldown during strafe phase
            if self._attack_state == "strafe":
                effective_rate = max(3, effective_rate // 3)
            if self.fire_cooldown <= 0 and edist < 400 and self._attack_state != "pullout":
                self.fire_cooldown = effective_rate
                direction = (edx / edist, edy / edist) if edist > 1 else self.facing
                self._attack_burst_count += 1
                proj = self._create_miniship_projectile(direction)
        else:
            # --- Return to orbit anchor with visible idle orbit ---
            self._attack_state = "approach"
            self._attack_burst_count = 0
            dx = ox - (self.x + self.width // 2)
            dy = oy - self.y
            dist = math.hypot(dx, dy)
            if dist > 15:
                self._mini_vx = dx * 0.08
                self._mini_vy = dy * 0.08
                self.x += self._mini_vx
                self.y += self._mini_vy
            else:
                # Visible idle orbit: small circle around formation anchor
                self._orbit_phase = getattr(self, '_orbit_phase', formation_angle) + 0.04
                orbit_r = 30
                target_x = ox + math.cos(self._orbit_phase) * orbit_r
                target_y = oy + math.sin(self._orbit_phase) * orbit_r
                self._mini_vx = (target_x - (self.x + self.width // 2)) * 0.12
                self._mini_vy = (target_y - self.y) * 0.12
                self.x += self._mini_vx
                self.y += self._mini_vy
            # Mirror owner's facing direction when idle
            if dist > 15:
                # Returning to orbit: face movement direction
                mvx, mvy = self._mini_vx, self._mini_vy
                mspd = math.hypot(mvx, mvy)
                if mspd > 0.5:
                    avx, avy = abs(mvx), abs(mvy)
                    sx = 1 if mvx > 0 else -1
                    sy = -1 if mvy < 0 else 1
                    if avx > 0.35 and avy > 0.35 and min(avx, avy) / max(avx, avy) > 0.4:
                        self.set_facing((sx, sy))
                    elif avx >= avy:
                        self.set_facing((sx, 0))
                    else:
                        self.set_facing((0, sy))
            else:
                # At orbit anchor: match owner's facing direction
                self.set_facing(owner.facing)
            self._update_rotation()
            self._update_engine_trail()
            return proj

        # Smooth velocity blending for attack movement
        smooth = 0.15
        self._mini_vx += (target_vx - self._mini_vx) * smooth
        self._mini_vy += (target_vy - self._mini_vy) * smooth
        self.x += self._mini_vx
        self.y += self._mini_vy

        self._update_rotation()
        self._update_engine_trail()
        return proj

    def _create_miniship_projectile(self, direction):
        """Create faction-specific projectile for miniship interceptors."""
        faction = self.faction.lower() if hasattr(self, 'faction') else ""
        cx = self.x + self.width // 2
        cy = self.y

        if "tau" in faction:
            proj = Missile(cx, cy, direction, self.laser_color, speed=16)
            proj.damage = 10
        elif "goa" in faction:
            proj = Laser(cx, cy, direction, (255, 180, 0), speed=18)
            proj.damage = 8
        else:
            proj = Laser(cx, cy, direction, self.laser_color, speed=20)
            proj.damage = 8

        proj.is_player_proj = True
        return proj

    def update_ai(self, target_ship, asteroids, other_ships=None, spatial_grid=None):
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
        elif self._behavior == "hostile_all":
            self._ai_hostile_all(dx, dy, dist_to_player, player_ship, other_ships)
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
            strafe_sign = self._strafe_sign
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

        # --- Asteroid dodge (use spatial grid if available) ---
        dodge_x, dodge_y = 0.0, 0.0
        closest_threat_dist = float('inf')
        nearby_asteroids = spatial_grid.query_unique(self.x, self.y, 400) if spatial_grid else asteroids
        for asteroid in nearby_asteroids:
            if not hasattr(asteroid, 'size'):
                continue
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

        # --- Separation (use spatial grid if available) ---
        sep_x, sep_y = 0.0, 0.0
        nearby_ships = spatial_grid.query_unique(self.x, self.y, 180) if spatial_grid else (other_ships or [])
        if nearby_ships:
            for other in nearby_ships:
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

        # --- Facing (4/8-direction) ---
        self._ai_face_target(dx, dy)

        # Strafe timer flip
        self._strafe_flip_timer -= 1
        if self._strafe_flip_timer <= 0:
            self._strafe_sign *= -1
            self._strafe_flip_timer = random.randint(120, 180)

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
        direction = self._aim_override if self._aim_override else self.facing
        dx, dy = direction
        cx = self.x + self.width // 2
        cy = self.y
        if dx == 1 and dy == 0:
            fire_x = self.x + self.width
            fire_y = cy
        elif dx == -1 and dy == 0:
            fire_x = self.x
            fire_y = cy
        elif dx == 0 and dy == -1:
            fire_x = cx
            fire_y = self.y - self.height // 2
        elif dx == 0 and dy == 1:
            fire_x = cx
            fire_y = self.y + self.height // 2
        else:
            # Diagonal or arbitrary aim direction
            fire_x = cx + int(dx * self.width * 0.5)
            fire_y = cy + int(dy * self.height * 0.5)

        if self.weapon_type in ("beam", "wraith_culling"):
            if self.beam_cooldown <= 0 and not self.current_beam:
                if self.weapon_type == "wraith_culling":
                    from .projectiles import WraithCullingBeam
                    self.current_beam = WraithCullingBeam(self, direction, (160, 40, 255),
                                                          self.screen_width, self.screen_height)
                else:
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
                # Ancient drone weapon: golden squid-shaped homing projectiles
                proj = AncientDrone(fire_x, fire_y, direction)
            elif self.weapon_type == "nanite_swarm":
                from .projectiles import NaniteProjectile
                base_angle = math.atan2(dy, dx)
                count = random.randint(3, 5)
                projs = []
                for i in range(count):
                    spread = (i - count / 2) * 0.15 + random.uniform(-0.05, 0.05)
                    angle = base_angle + spread
                    ndx, ndy = math.cos(angle), math.sin(angle)
                    p = NaniteProjectile(fire_x, fire_y, (ndx, ndy))
                    p.is_player_proj = self.is_player
                    fury = self.get_fury_multiplier()
                    if fury > 1.0:
                        p.damage = int(p.damage * fury)
                    projs.append(p)
                return projs
            elif self.weapon_type == "tunnel_crystal":
                from .projectiles import TunnelCrystal
                proj = TunnelCrystal(fire_x, fire_y, direction)
            elif self.weapon_type == "dual_staff":
                # Two or four parallel staff blasts (mastery: Staff Barrage)
                mastery_active = getattr(self, '_mastery_active', False)
                if mastery_active:
                    offsets = [1.5, 0.5, -0.5, -1.5]
                else:
                    offsets = [1, -1]
                projs = []
                for off in offsets:
                    px = -direction[1] * 12 * off
                    py = direction[0] * 12 * off
                    p = JaffaStaffBlast(fire_x + px, fire_y + py, direction, self.laser_color)
                    p.damage = 10
                    p.is_player_proj = self.is_player
                    fury = self.get_fury_multiplier()
                    if fury > 1.0:
                        p.damage = int(p.damage * fury)
                    projs.append(p)
                return projs
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
                proj = AncientDrone(cx + dx * 30, cy + dy * 30, (sdx, sdy),
                                    speed=14)
                proj.damage = 15
                proj.homing_strength = 0.05
                proj.is_player_proj = self.is_player
                results.append(("projectile", proj))

        elif self.secondary_type == "alkesh_deploy":
            # Goa'uld Ha'tak: deploy 3 Al'kesh bombers targeting nearest enemies
            results.append(("alkesh_deploy", {"x": cx, "y": cy, "count": 3,
                                              "damage": 35, "blast_radius": 130}))

        elif self.secondary_type == "eye_of_ra":
            # Anubis Eye of Ra: devastating focused golden beam (5s cooldown)
            # Fires a concentrated beam that deals massive damage to everything in a line
            results.append(("eye_of_ra", {"x": cx, "y": cy, "direction": self.facing,
                                          "damage": 100, "range": 800}))

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

        # --- Bright flare on shield hit (no always-on bubble — clean ship look) ---
        if self.shield_hit_timer > 0 and self.shields >= 0:
            sc_bubble, sc_rim, sc_inner = SHIELD_COLORS.get(
                self.faction.lower(), _DEFAULT_SHIELD_COLOR)
            # Brighten toward white for flash effect
            flash_col = tuple(min(255, c + 70) for c in sc_rim)
            mid_col = tuple(min(255, c + 20) for c in sc_inner)
            spark_col = tuple(min(255, c + 100) for c in sc_rim)
            crack_col = tuple(min(255, c + 60) for c in sc_rim)

            visibility = self.shield_hit_timer / 60.0
            flare_r = int(base_radius * (1.0 + visibility * 0.3))
            sz = flare_r * 2 + 30
            flare = pygame.Surface((sz, sz), pygame.SRCALPHA)
            c = sz // 2

            flash_alpha = int(180 * visibility)
            pygame.draw.circle(flare, (*flash_col, flash_alpha), (c, c), flare_r, 4)
            inner_alpha = int(100 * visibility)
            pygame.draw.circle(flare, (*mid_col, inner_alpha), (c, c), int(flare_r * 0.7))
            spark_alpha = int(220 * visibility)
            pygame.draw.circle(flare, (*spark_col, spark_alpha), (c, c - int(flare_r * 0.5)), int(flare_r * 0.15))

            num_cracks = 8
            for i in range(num_cracks):
                angle = (time_tick * 0.01) + i * (math.pi * 2 / num_cracks)
                inner_pt = (c + int(math.cos(angle) * flare_r * 0.5),
                            c + int(math.sin(angle) * flare_r * 0.5))
                outer_pt = (c + int(math.cos(angle) * flare_r * 0.95),
                            c + int(math.sin(angle) * flare_r * 0.95))
                crack_alpha = int(120 * visibility)
                pygame.draw.line(flare, (*crack_col, crack_alpha), inner_pt, outer_pt, 2)

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

        # Shield bar (faction-tinted)
        if self.max_shields > 0:
            sc_bubble, sc_rim, _ = SHIELD_COLORS.get(
                self.faction.lower(), _DEFAULT_SHIELD_COLOR)
            # Dim background from faction color
            bar_bg = tuple(max(0, c // 4) for c in sc_bubble)
            shield_bar_y = health_bar_y + bar_height + 2
            shield_bar_h = 4
            pygame.draw.rect(surface, bar_bg, (bar_x, shield_bar_y, bar_width, shield_bar_h))
            pygame.draw.rect(surface, sc_bubble, (bar_x, shield_bar_y, int(bar_width * shield_pct), shield_bar_h))
            pygame.draw.rect(surface, sc_rim, (bar_x, shield_bar_y, bar_width, shield_bar_h), 1)

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
        self._ai_face_target(dx, dy)
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
        self._ai_face_target(math.cos(self._homing_angle), math.sin(self._homing_angle))
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
            self._ai_face_target(dx, dy)
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
        """Ori mothership: slowly drifts toward action, fires sweeping beam + regular lasers.

        Phase transitions based on HP:
        - Normal (>50%): slow drift, fire every 60 frames
        - Aggressive (25-50%): 30% faster, fire every 40 frames
        - Enrage (<=25%): spread lasers every 30 frames, beam charges 2x faster
        """
        hp_pct = self.health / max(self.max_health, 1)

        # Determine movement speed based on phase
        move_speed = self.speed * 1.3 if hp_pct <= 0.5 else self.speed

        # Slow drift toward target
        if dist > 1:
            ux = dx / dist
            uy = dy / dist
            self.x += ux * move_speed
            self.y += uy * move_speed

        # Face target (4/8-direction)
        self._ai_face_target(dx, dy)

        # Ori boss beam timer (tracked by game.py via _ori_beam_timer)
        beam_advance = 2 if hp_pct <= 0.25 else 1
        self._ori_beam_timer = getattr(self, '_ori_beam_timer', 0) + beam_advance

        # Determine fire rate based on phase
        if hp_pct <= 0.25:
            fire_interval = 30
        elif hp_pct <= 0.5:
            fire_interval = 40
        else:
            fire_interval = 60

        # Fire regular golden lasers between beam charges
        self.ai_fire_timer = getattr(self, 'ai_fire_timer', 0)
        if self.ai_fire_timer <= 0 and dist < 800:
            self.ai_fire_timer = fire_interval
            if dist > 1:
                if not hasattr(self, '_pending_projectiles'):
                    self._pending_projectiles = []
                if hp_pct <= 0.25:
                    # Enrage: fire 3 spread lasers (-15, 0, +15 degrees)
                    base_angle = math.atan2(dy, dx)
                    for spread in [-math.radians(15), 0, math.radians(15)]:
                        angle = base_angle + spread
                        direction = (math.cos(angle), math.sin(angle))
                        proj = Laser(self.x + self.width // 2, self.y, direction,
                                    (255, 220, 80), speed=12)
                        proj.damage = 15
                        proj.is_player_proj = False
                        self._pending_projectiles.append(proj)
                else:
                    direction = (dx / dist, dy / dist)
                    proj = Laser(self.x + self.width // 2, self.y, direction,
                                (255, 220, 80), speed=12)
                    proj.damage = 15
                    proj.is_player_proj = False
                    self._pending_projectiles.append(proj)

        self._update_rotation()
        self._update_engine_trail()

    def _ai_wraith_boss(self, dx, dy, dist, target, asteroids, other_ships):
        """Wraith Hive boss: drifts toward action, fires purple beam + spawns darts via _pending.

        Phase transitions based on HP:
        - Normal (>50%): fire every 45 frames, spawn darts every 240 frames (max 3)
        - Aggressive (25-50%): fire every 35 frames, spawn darts every 180 frames (max 3)
        - Desperate (<=25%): fire every 25 frames with stronger lifesteal, spawn every 120 frames (max 5)
        """
        hp_pct = self.health / max(self.max_health, 1)

        # Slow drift toward target
        if dist > 1:
            ux = dx / dist
            uy = dy / dist
            self.x += ux * self.speed
            self.y += uy * self.speed

        # Face target (4/8-direction)
        self._ai_face_target(dx, dy)

        # Wraith beam timer (tracked by game.py)
        self._ori_beam_timer = getattr(self, '_ori_beam_timer', 0) + 1

        # Determine fire rate based on phase
        if hp_pct <= 0.25:
            fire_interval = 25
        elif hp_pct <= 0.5:
            fire_interval = 35
        else:
            fire_interval = 45

        # Fire purple life-drain bolts between beam charges
        self.ai_fire_timer = getattr(self, 'ai_fire_timer', 0)
        if self.ai_fire_timer <= 0 and dist < 700:
            self.ai_fire_timer = fire_interval
            if dist > 1:
                direction = (dx / dist, dy / dist)
                proj = Laser(self.x + self.width // 2, self.y, direction,
                            (160, 40, 255), speed=10)
                proj.damage = 12
                proj.is_player_proj = False
                proj._wraith_lifesteal = True  # game.py uses this for heal-on-hit
                if hp_pct <= 0.25:
                    proj._wraith_lifesteal_pct = 0.3  # Stronger heal in desperate phase
                if not hasattr(self, '_pending_projectiles'):
                    self._pending_projectiles = []
                self._pending_projectiles.append(proj)

        # Determine spawn rate and max darts based on phase
        if hp_pct <= 0.25:
            spawn_interval = 120
            max_darts = 5
        elif hp_pct <= 0.5:
            spawn_interval = 180
            max_darts = 3
        else:
            spawn_interval = 240
            max_darts = 3

        # Spawn wraith darts periodically
        self._wraith_spawn_timer = getattr(self, '_wraith_spawn_timer', 0) + 1
        if not hasattr(self, '_spawned_darts'):
            self._spawned_darts = []
        if self._wraith_spawn_timer >= spawn_interval and len(self._spawned_darts) < max_darts:
            self._wraith_spawn_timer = 0
            # game.py handles actual spawn via _pending_spawns
            if not hasattr(self, '_pending_spawns'):
                self._pending_spawns = []
            self._pending_spawns.append("wraith_dart")

        self._update_rotation()
        self._update_engine_trail()

    def _ai_hostile_all(self, dx, dy, dist_to_player, target, other_ships):
        """Wraith miniship: hostile to everyone — targets nearest entity (player OR other enemy)."""
        # Build combined target list: player + other AI ships (excluding self)
        candidates = [(target.x + target.width // 2, target.y, dist_to_player, target)]
        if other_ships:
            for o in other_ships:
                if o is self:
                    continue
                od = math.hypot(o.x - self.x, o.y - self.y)
                candidates.append((o.x + o.width // 2, o.y, od, o))

        # Pick nearest
        candidates.sort(key=lambda c: c[2])
        tx, ty, tdist, _ = candidates[0]

        # Standard approach/strafe against chosen target
        if tdist > 1:
            ux = (tx - (self.x + self.width // 2)) / tdist
            uy = (ty - self.y) / tdist
            strafe_sign = self._strafe_sign
            perp_x = -uy * strafe_sign
            perp_y = ux * strafe_sign

            preferred_range = 200
            if tdist > preferred_range + 75:
                self.x += ux * self.speed * 0.8
                self.y += uy * self.speed * 0.8
            elif tdist < preferred_range - 75:
                self.x += -ux * self.speed * 0.3 + perp_x * self.speed * 0.5
                self.y += -uy * self.speed * 0.3 + perp_y * self.speed * 0.5
            else:
                self.x += perp_x * self.speed * 0.5
                self.y += perp_y * self.speed * 0.5

        # Facing (4/8-direction)
        self._ai_face_target(tx - (self.x + self.width // 2), ty - self.y)

        # Fire at target — mark projectiles as hostile_all
        if self.fire_cooldown <= 0 and tdist < 450:
            self.fire_cooldown = self.fire_rate
            if tdist > 1:
                direction = ((tx - (self.x + self.width // 2)) / tdist,
                             (ty - self.y) / tdist)
            else:
                direction = self.facing
            proj = Laser(self.x + self.width // 2, self.y, direction,
                         (160, 40, 255), speed=14)
            proj.damage = 10
            proj.is_player_proj = False
            proj.is_hostile_all = True
            proj._source_ship = self
            if not hasattr(self, '_pending_projectiles'):
                self._pending_projectiles = []
            self._pending_projectiles.append(proj)

        self._update_rotation()
        self._update_engine_trail()

    def _ai_face_target(self, dx, dy):
        """Set facing toward target using 4/8-direction logic."""
        adx, ady = abs(dx), abs(dy)
        if adx > ady * 1.5:
            self.set_facing((1, 0) if dx > 0 else (-1, 0))
        elif ady > adx * 1.5:
            self.set_facing((0, 1) if dy > 0 else (0, -1))
        else:
            sx = 1 if dx > 0 else -1
            sy = 1 if dy > 0 else -1
            self.set_facing((sx, sy))

    def _ai_standard_strafe(self, dx, dy, dist, target, asteroids, other_ships, preferred_range=275):
        """Common strafe AI reused by multiple behaviors."""
        range_tolerance = 75
        move_x, move_y = 0.0, 0.0

        if dist > 1:
            ux = dx / dist
            uy = dy / dist

            # Flanking: some enemies approach from an angle
            if other_ships and len(other_ships) >= 3 and id(self) % 3 == 0:
                angle_off = math.pi / 3  # 60 degrees
                cos_o = math.cos(angle_off)
                sin_o = math.sin(angle_off)
                ux2 = ux * cos_o - uy * sin_o
                uy2 = ux * sin_o + uy * cos_o
                ux, uy = ux2, uy2

            strafe_sign = self._strafe_sign
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

        self._ai_face_target(dx, dy)

        if self.current_beam:
            self.current_beam.update()
            self.beam_duration_timer += 1
            if self.beam_duration_timer >= 90:
                self.stop_beam()

        self._strafe_flip_timer -= 1
        if self._strafe_flip_timer <= 0:
            self._strafe_sign *= -1
            self._strafe_flip_timer = random.randint(120, 180)

        self._update_rotation()
        self._update_engine_trail()
