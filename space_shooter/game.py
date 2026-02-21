"""Main SpaceShooterGame class — infinite survival mode with camera system."""

import pygame
import math
import random
import os

from .projectiles import (Projectile, Laser, ContinuousBeam, EnergyBall,
                          ChainLightning, RailgunShot, ProximityMine, AreaBomb)
from .entities import (
    Asteroid, PowerUp, Drone, XPOrb, WormholeEffect, Explosion,
    DamageNumber, PopupNotification, GravityWell, Sun,
)
from .effects import StarField, ScreenShake
from .ship import Ship
from .upgrades import UPGRADES, EVOLUTIONS, ENEMY_TYPES, ENEMY_EXPLOSION_PALETTES
from .camera import Camera
from .spawner import ContinuousSpawner
from . import ui as _ui


class SpaceShooterGame:
    """Infinite survival space shooter — Vampire Survivors style."""

    # Scoring constants
    SCORE_ENEMY = 100
    SCORE_BOSS = 1000
    SCORE_ASTEROID = 50

    def __init__(self, screen_width, screen_height, player_faction, ai_faction, session_scores=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.player_faction = player_faction
        self.ai_faction = ai_faction
        self.session_scores = session_scores if session_scores is not None else []

        # Game state
        self.running = True
        self.game_over = False
        self.winner = None
        self.exit_to_menu = False

        # Survival timer (frames)
        self.survival_frames = 0

        # Scoring system
        self.score = 0
        self.enemies_defeated = 0
        self.asteroids_destroyed = 0

        # Kill streak
        self.kill_streak = 0
        self.kill_streak_timer = 0

        # Power-up system
        self.powerups = []
        self.powerup_drop_chance = 0.50  # 50% chance on enemy kill
        self.powerup_spawn_timer = 0  # periodic powerup spawn near player
        self.active_powerups = {}
        self.drones = []
        self.mines = []  # Lucian Alliance proximity mines
        self.ion_pulse_effects = []  # Asgard ion pulse visual effects
        self.base_fire_rate = None
        self.base_damage_mult = 1.15  # Slight base damage bonus — player should feel powerful

        # XP and Level-up system
        self.xp = 0
        self.level = 1
        self.xp_to_next = 80
        self.upgrades = {}
        self.evolutions = {}  # Completed evolutions
        self.xp_orbs = []
        self.pending_level_ups = 0
        self.level_up_choices = []
        self.showing_level_up = False
        self.total_kills = 0
        self.upgrade_drones = []
        self.rear_turret_timer = 0

        # Wormhole escape ability
        self.wormhole_cooldown = 0
        self.wormhole_max_cooldown = 480
        self.wormhole_active = False
        self.wormhole_transit_timer = 0
        self.wormhole_transit_duration = 18  # Snappy: 0.3s (was 0.5s)
        self.wormhole_effects = []
        self.wormhole_exit_x = 0.0
        self.wormhole_exit_y = 0.0

        # Wormhole sound effect
        self.wormhole_sound = None
        try:
            sound_path = os.path.join("assets", "audio", "siege.ogg")
            if os.path.exists(sound_path):
                self.wormhole_sound = pygame.mixer.Sound(sound_path)
                self.wormhole_sound.set_volume(0.5)
        except Exception:
            pass

        # Faction hit sound effects — plays on enemy hit with short cooldown
        self.hit_sound = None
        self.hit_sound_cooldown = 0
        self._load_hit_sound()

        # Boost sound effect — plays once when SHIFT boost activates
        self.boost_sound = None
        self._was_boosting = False
        self._load_boost_sound()

        # Shield bash (dash) state
        self.dash_active = False
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_afterimages = []

        # Gravity well state
        self.gravity_wells = []
        self.gravity_well_timer = 0

        # Sun/wormhole environmental hazards
        self.suns = []
        self.sun_spawn_timer = 0
        self.sun_first_spawn_done = False

        # Ally ships (summoned by upgrades/powerups)
        self.ally_ships = []

        # Area bombs (from Al'kesh bombers)
        self.area_bombs = []

        # New upgrade timers
        self.nova_burst_timer = 0
        self.orbital_laser_timer = 0
        self.orbital_laser_effects = []  # List of active orbital strike visuals
        self.temporal_field_active = False

        # Chain lightning visual effects
        self.chain_lightning_effects = []

        # Visual feedback
        self.damage_numbers = []
        self.popup_notifications = []
        self.screen_shake = ScreenShake()

        # All faction options for variety
        self.all_factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]

        # --- Camera system ---
        self.camera = Camera(screen_width, screen_height)

        # Create player ship at world origin
        self.player_ship = Ship(
            0, 0,
            player_faction, is_player=True,
            screen_width=screen_width, screen_height=screen_height
        )
        # Boost player base stats — feel powerful from the start
        self.player_ship.max_health = 150
        self.player_ship.health = 150
        self.player_ship.max_shields = 150
        self.player_ship.shields = 150

        # Snap camera to player start
        self.camera.snap_to(self.player_ship.x + self.player_ship.width // 2,
                            self.player_ship.y)

        # --- Continuous spawner (replaces wave system) ---
        self.spawner = ContinuousSpawner(self.camera, player_faction, self.all_factions,
                                          enemy_faction=ai_faction)

        # Projectiles and effects
        self.ai_ships = []
        self.projectiles = []
        self.explosions = []
        self.asteroids = []
        self.starfield = StarField(screen_width, screen_height)

        # Asteroid spawning
        self.asteroid_spawn_timer = 0
        self.asteroid_spawn_rate = 300

        # Player beam state
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

    @property
    def survival_seconds(self):
        return self.survival_frames / 60.0

    def handle_event(self, event):
        """Handle pygame events."""
        if self.showing_level_up and self.level_up_choices:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.exit_to_menu = True
                    self.running = False
                    return
                key_map = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}
                idx = key_map.get(event.key)
                if idx is not None and idx < len(self.level_up_choices):
                    self._select_upgrade(self.level_up_choices[idx])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hasattr(self, '_level_up_card_rects'):
                    for i, rect in enumerate(self._level_up_card_rects):
                        if rect.collidepoint(event.pos) and i < len(self.level_up_choices):
                            self._select_upgrade(self.level_up_choices[i])
                            break
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.exit_to_menu = True
                self.running = False
            elif event.key == pygame.K_q and not self.game_over:
                if self.wormhole_cooldown <= 0 and not self.wormhole_active:
                    self._activate_wormhole()
            elif event.key == pygame.K_e and not self.game_over:
                self._fire_secondary()
            elif event.key == pygame.K_r and self.game_over:
                self.__init__(self.screen_width, self.screen_height,
                            self.player_faction, self.ai_faction,
                            session_scores=self.session_scores)
            # Facing is now derived from velocity in update() for smooth movement

    def _activate_wormhole(self):
        """Activate the wormhole escape — snappy teleport with sound."""
        self.wormhole_active = True
        self.wormhole_transit_timer = 0

        # Play siege.ogg sound
        if self.wormhole_sound:
            self.wormhole_sound.play()

        entry_x = self.player_ship.x + self.player_ship.width // 2
        entry_y = self.player_ship.y
        self.wormhole_effects.append(WormholeEffect(entry_x, entry_y, is_entry=True))

        # Teleport to a random spot ~400px away
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(300, 500)
        self.wormhole_exit_x = self.player_ship.x + math.cos(angle) * dist
        self.wormhole_exit_y = self.player_ship.y + math.sin(angle) * dist

        # Screen shake for impact
        self.screen_shake.trigger(6, 10)

    def _load_hit_sound(self):
        """Load hit sound effect for the player's faction."""
        faction_sounds = {
            "Asgard": "asgard_space_shooter.ogg",
            "Tau'ri": "tauri_space_shooter.ogg",
            "Goa'uld": "goauld_space_shooter.ogg",
            "Jaffa Rebellion": "jaffa_space_shooter.ogg",
            "Lucian Alliance": "lucian_space_shooter.ogg",
        }
        filename = faction_sounds.get(self.player_faction)
        if not filename:
            return
        sound_path = os.path.join("assets", "audio", "space_shooter", filename)
        try:
            if os.path.exists(sound_path):
                self.hit_sound = pygame.mixer.Sound(sound_path)
                self.hit_sound.set_volume(0.4)
        except Exception:
            pass

    def _play_hit_sound(self):
        """Play hit SFX when enemy is struck (0.5s cooldown to avoid spam)."""
        if self.hit_sound is None:
            return
        if self.hit_sound_cooldown > 0:
            self.hit_sound_cooldown -= 1
            return
        try:
            ch = self.hit_sound.play()
            if ch:
                ch.set_volume(0.4)
            # 30 frames = 0.5s cooldown at 60fps
            self.hit_sound_cooldown = 30
        except Exception:
            pass

    def _load_boost_sound(self):
        """Load the thruster boost activation sound."""
        sound_path = os.path.join("assets", "audio", "space_shooter", "boost_space_shooter.ogg")
        try:
            if os.path.exists(sound_path):
                self.boost_sound = pygame.mixer.Sound(sound_path)
                self.boost_sound.set_volume(0.45)
        except Exception:
            pass

    def _fire_secondary(self):
        """Fire the player's faction-specific secondary weapon."""
        results = self.player_ship.secondary_fire()
        for result_type, data in results:
            if result_type == "projectile":
                self.projectiles.append(data)
            elif result_type == "mine":
                self.mines.append(data)
            elif result_type == "ion_pulse":
                # Asgard Ion Pulse: instant AoE damage + visual
                px, py = data["x"], data["y"]
                radius = data["radius"]
                damage = data["damage"]
                self.screen_shake.trigger(5, 10)
                self.ion_pulse_effects.append({
                    "x": px, "y": py, "radius": 0,
                    "max_radius": radius, "timer": 0, "duration": 20,
                    "color": self.player_ship.laser_color,
                })
                for enemy in self.ai_ships[:]:
                    dist = math.hypot(enemy.x + enemy.width // 2 - px, enemy.y - py)
                    if dist < radius:
                        # Damage falls off with distance
                        dmg = int(damage * (1.0 - dist / radius * 0.5))
                        enemy.hit_flash = 5
                        self.damage_numbers.append(DamageNumber(
                            enemy.x + enemy.width // 2, enemy.y,
                            dmg, (100, 255, 255)))
                        if self._damage_enemy(enemy, dmg):
                            self._on_enemy_killed(enemy)
                        else:
                            # Push enemies away
                            if dist > 1:
                                push = 80 / max(dist, 1)
                                enemy.x += (enemy.x - px) / dist * push
                                enemy.y += (enemy.y - py) / dist * push
            elif result_type == "war_cry":
                # Jaffa War Cry: buff notification + screen shake
                self.screen_shake.trigger(4, 8)
                self.popup_notifications.append(PopupNotification(
                    self.player_ship.x + self.player_ship.width // 2,
                    self.player_ship.y - 80,
                    "WAR CRY!", (255, 150, 50)
                ))

    def _spawn_sun(self):
        """Spawn a sun hazard 600-1000px from the player."""
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(600, 1000)
        sx = self.player_ship.x + math.cos(angle) * dist
        sy = self.player_ship.y + math.sin(angle) * dist
        self.suns.append(Sun(sx, sy))

    def _spawn_ally_ship(self, duration=600):
        """Spawn a friendly ally ship near the player."""
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(80, 150)
        ax = self.player_ship.x + math.cos(angle) * dist
        ay = self.player_ship.y + math.sin(angle) * dist
        ally = Ship(ax, ay, self.player_faction, is_player=False,
                   screen_width=self.screen_width, screen_height=self.screen_height)
        ally.is_friendly = True
        ally.ally_owner = self.player_ship
        ally.ally_lifetime = duration
        ally.max_health = 80
        ally.health = 80
        ally.speed = 6
        ally.fire_rate = 25
        # Green tint
        if ally.image:
            tint = pygame.Surface(ally.image.get_size(), pygame.SRCALPHA)
            tint.fill((0, 100, 0, 40))
            ally.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            ally.image_right = ally.image.copy()
            ally.image_left = pygame.transform.flip(ally.image, True, False)
            ally.image_up = pygame.transform.rotate(ally.image_right, 90)
            ally.image_down = pygame.transform.rotate(ally.image_right, -90)
        self.ally_ships.append(ally)

    def _save_score(self):
        """Save the score to the per-session leaderboard."""
        import time as time_module
        entry = {
            "score": self.score,
            "survival_time": round(self.survival_seconds, 1),
            "enemies_defeated": self.enemies_defeated,
            "won": False,  # Survival — always ends in death
            "faction": self.player_faction,
            "timestamp": time_module.time(),
        }
        self.session_scores.append(entry)
        self.session_scores.sort(key=lambda x: x["score"], reverse=True)
        if len(self.session_scores) > 10:
            self.session_scores[:] = self.session_scores[:10]
        self.final_rank = 0
        for i, e in enumerate(self.session_scores):
            if e["timestamp"] == entry["timestamp"] and e["score"] == entry["score"]:
                self.final_rank = i + 1
                break

    def _apply_powerup(self, powerup):
        """Apply the effect of a collected power-up."""
        ptype = powerup.type
        props = powerup.props
        zpm_mult = 1.0 + self.upgrades.get("zpm_reserves", 0) * 0.5
        duration = int(props["duration"] * zpm_mult) if props["duration"] > 0 else 0

        # Popup notification
        self.popup_notifications.append(PopupNotification(
            self.player_ship.x + self.player_ship.width // 2,
            self.player_ship.y - 60,
            props["name"].upper() + "!",
            props["color"]
        ))

        if ptype == "shield":
            self.player_ship.shields = min(self.player_ship.max_shields,
                                          self.player_ship.shields + 50)
        elif ptype == "rapid_fire":
            if not hasattr(self, '_saved_fire_rate'):
                self._saved_fire_rate = self.player_ship.fire_rate
            self.player_ship.fire_rate = max(5, self.player_ship.fire_rate // 2)
            self.active_powerups["rapid_fire"] = duration
        elif ptype == "drone":
            self.drones = []
            for i in range(3):
                angle = (i * 2 * math.pi / 3)
                self.drones.append(Drone(self.player_ship, angle))
            self.active_powerups["drone"] = duration
        elif ptype == "damage":
            self.base_damage_mult = 1.25
            self.active_powerups["damage"] = duration
        elif ptype == "cloak":
            self.active_powerups["cloak"] = duration
        elif ptype == "overcharge":
            # Massive fire rate boost + extra projectiles
            if not hasattr(self, '_saved_fire_rate'):
                self._saved_fire_rate = self.player_ship.fire_rate
            self.player_ship.fire_rate = max(3, self.player_ship.fire_rate // 3)
            self.active_powerups["overcharge"] = duration
            # Visual feedback — screen shake burst
            self.screen_shake.trigger(4, 8)
        elif ptype == "time_warp":
            self.active_powerups["time_warp"] = duration
            # Visual feedback — brief shake
            self.screen_shake.trigger(3, 6)
        elif ptype == "magnetize":
            self.active_powerups["magnetize"] = duration

        # --- FACTION EPIC POWERUPS ---
        elif ptype == "asgard_beam_array":
            # Asgard: Fires beams in all 4 directions for 6 seconds
            self.active_powerups["asgard_beam_array"] = duration
            self.screen_shake.trigger(6, 12)
        elif ptype == "tauri_railgun_barrage":
            # Tau'ri: Auto-fire railgun shots every 0.5s for 7 seconds
            self.active_powerups["tauri_railgun_barrage"] = duration
            self._railgun_barrage_timer = 0
            self.screen_shake.trigger(5, 10)
        elif ptype == "goauld_sarcophagus":
            # Goa'uld: Full HP + shield restore + 3s invulnerability
            self.player_ship.health = self.player_ship.max_health
            self.player_ship.shields = self.player_ship.max_shields
            self.active_powerups["goauld_sarcophagus"] = 180  # 3s invuln
            self.screen_shake.trigger(4, 8)
        elif ptype == "jaffa_blood_rage":
            # Jaffa: Triple damage + double speed + life steal for 6 seconds
            self.active_powerups["jaffa_blood_rage"] = duration
            self.screen_shake.trigger(5, 10)
        elif ptype == "lucian_kassa":
            # Lucian: Enemies in range attack each other for 7 seconds
            self.active_powerups["lucian_kassa"] = duration
            self.screen_shake.trigger(3, 6)

        # --- FACTION LEGENDARY POWERUPS ---
        elif ptype == "asgard_mjolnir":
            # Asgard Mjolnir: Lightning strikes ALL visible enemies for massive damage
            self.screen_shake.trigger(12, 20)
            for enemy in self.ai_ships[:]:
                if self.camera.is_visible(enemy.x, enemy.y, margin=100):
                    enemy.hit_flash = 15
                    dmg = 80
                    self.damage_numbers.append(DamageNumber(
                        enemy.x + enemy.width // 2, enemy.y,
                        dmg, (150, 220, 255)))
                    if self._damage_enemy(enemy, dmg):
                        self._on_enemy_killed(enemy)
                    # Chain lightning visual to each
                    targets = [(enemy.x + enemy.width // 2, enemy.y)]
                    px = self.player_ship.x + self.player_ship.width // 2
                    py = self.player_ship.y
                    self.chain_lightning_effects.append(
                        ChainLightning(px, py, targets, dmg, max_chains=1))
        elif ptype == "tauri_ancient_drones":
            # Ancient Drone Swarm: 8 super-drones for 10 seconds
            self.drones = []
            for i in range(8):
                angle = i * 2 * math.pi / 8
                d = Drone(self.player_ship, angle)
                d.fire_rate = 15  # Much faster than normal drones
                self.drones.append(d)
            self.active_powerups["tauri_ancient_drones"] = duration
            self.screen_shake.trigger(6, 10)
        elif ptype == "goauld_hatak_strike":
            # Ha'tak Bombardment: Rain orbital strikes on all visible enemies
            self.screen_shake.trigger(10, 20)
            for enemy in self.ai_ships[:]:
                if self.camera.is_visible(enemy.x, enemy.y, margin=100):
                    ex = enemy.x + enemy.width // 2
                    ey = enemy.y
                    self.orbital_laser_effects.append({
                        'x': ex, 'y': ey, 'timer': 0, 'duration': 30,
                    })
                    enemy.hit_flash = 10
                    dmg = 60
                    self.damage_numbers.append(DamageNumber(ex, ey, dmg, (255, 200, 50)))
                    if self._damage_enemy(enemy, dmg):
                        self._on_enemy_killed(enemy)
                    self.explosions.append(Explosion(ex, ey, tier="normal"))
        elif ptype == "jaffa_freedom":
            # JAFFA KREE: Invulnerable + 3x damage + double speed for 5 seconds
            self.active_powerups["jaffa_freedom"] = duration
            self.active_powerups["goauld_sarcophagus"] = duration  # Reuse invuln
            self.screen_shake.trigger(8, 15)
        elif ptype == "lucian_nuke":
            # Naquadria Bomb: Massive AoE explosion centered on player, damages everything
            self.screen_shake.trigger(15, 25)
            px = self.player_ship.x + self.player_ship.width // 2
            py = self.player_ship.y
            self.explosions.append(Explosion(px, py, tier="large"))
            for enemy in self.ai_ships[:]:
                dist = math.hypot(enemy.x + enemy.width // 2 - px, enemy.y - py)
                if dist < 600:
                    dmg = int(120 * (1.0 - dist / 600 * 0.6))
                    enemy.hit_flash = 10
                    self.damage_numbers.append(DamageNumber(
                        enemy.x + enemy.width // 2, enemy.y,
                        dmg, (255, 100, 255)))
                    if self._damage_enemy(enemy, dmg):
                        self._on_enemy_killed(enemy)
                        self.explosions.append(Explosion(
                            enemy.x + enemy.width // 2, enemy.y, tier="normal"))

        # --- NEW FACTION EPIC POWERUPS ---
        elif ptype == "tauri_f302_squadron":
            # Spawn 3 ally F-302 ships for 8s
            for _ in range(3):
                self._spawn_ally_ship(duration=duration if duration > 0 else 480)
            self.screen_shake.trigger(4, 8)
        elif ptype == "tauri_prometheus_shield":
            # Absorb next 200 damage, reflect 50% back at attacker
            self.active_powerups["tauri_prometheus_shield"] = duration
            self._prometheus_shield_hp = 200
            self.screen_shake.trigger(5, 10)
        elif ptype == "goauld_kull_warrior":
            # Invulnerable + double damage for 4s
            self.active_powerups["goauld_kull_warrior"] = duration
            self.active_powerups["goauld_sarcophagus"] = duration  # Reuse invuln
            self.base_damage_mult *= 2.0
            self.screen_shake.trigger(6, 12)
        elif ptype == "goauld_hand_device":
            # Stun all enemies in 300px for 3s
            px = self.player_ship.x + self.player_ship.width // 2
            py = self.player_ship.y
            self.screen_shake.trigger(5, 10)
            for enemy in self.ai_ships:
                dist = math.hypot(enemy.x + enemy.width // 2 - px, enemy.y - py)
                if dist < 300:
                    enemy._stunned = 180  # 3s stun
                    enemy.hit_flash = 10
                    self.damage_numbers.append(DamageNumber(
                        enemy.x + enemy.width // 2, enemy.y, 0, (255, 255, 100)))
        elif ptype == "asgard_time_dilation":
            # All enemies slowed to 25% speed for 5s
            self.active_powerups["asgard_time_dilation"] = duration
            self.screen_shake.trigger(4, 8)
        elif ptype == "asgard_matter_converter":
            # Convert nearest 5 enemies to large XP orbs
            px = self.player_ship.x + self.player_ship.width // 2
            py = self.player_ship.y
            sorted_enemies = sorted(self.ai_ships,
                                    key=lambda e: math.hypot(e.x - px, e.y - py))
            for enemy in sorted_enemies[:5]:
                xp_val = getattr(enemy, 'xp_value', 30) * 3
                self.xp_orbs.append(XPOrb(enemy.x + enemy.width // 2, enemy.y, xp_val))
                self.explosions.append(Explosion(
                    enemy.x + enemy.width // 2, enemy.y, tier="normal",
                    color_palette=[(200, 200, 255), (150, 150, 220), (255, 255, 255)]))
                self.ai_ships.remove(enemy)
            self.screen_shake.trigger(6, 12)
        elif ptype == "jaffa_tretonin":
            # Double HP regen for 10s
            self.active_powerups["jaffa_tretonin"] = duration
        elif ptype == "jaffa_rite_sharran":
            # If HP < 30%, full heal + 50% max HP as temp HP
            hp_pct = self.player_ship.health / self.player_ship.max_health
            if hp_pct < 0.30:
                self.player_ship.health = self.player_ship.max_health
                bonus_hp = int(self.player_ship.max_health * 0.5)
                self.player_ship.health += bonus_hp
                self.screen_shake.trigger(8, 15)
                self.popup_notifications.append(PopupNotification(
                    self.player_ship.x + self.player_ship.width // 2,
                    self.player_ship.y - 80,
                    "REBORN!", (255, 200, 50)))
            else:
                # Still heals to full if above 30%
                self.player_ship.health = self.player_ship.max_health
                self.screen_shake.trigger(4, 8)
        elif ptype == "lucian_smugglers_luck":
            # Double powerup drop rate for 15s
            self.active_powerups["lucian_smugglers_luck"] = duration
        elif ptype == "lucian_black_market":
            # Gain 2 random upgrade stacks
            available = [u for u in UPGRADES if self.upgrades.get(u, 0) < UPGRADES[u]["max"]]
            for _ in range(min(2, len(available))):
                if not available:
                    break
                chosen = random.choice(available)
                self.upgrades[chosen] = self.upgrades.get(chosen, 0) + 1
                available.remove(chosen)
                self.popup_notifications.append(PopupNotification(
                    self.player_ship.x + self.player_ship.width // 2,
                    self.player_ship.y - 60,
                    f"+{UPGRADES[chosen]['name']}", (180, 80, 200)))
            self.screen_shake.trigger(4, 8)

        # --- NEW FACTION LEGENDARY POWERUPS ---
        elif ptype == "tauri_ancient_tech":
            # All weapons gain piercing + slight homing for 8s
            self.active_powerups["tauri_ancient_tech"] = duration
            self.screen_shake.trigger(8, 15)
        elif ptype == "goauld_ribbon_device":
            # Continuous beam drains nearest enemy HP to heal player for 6s
            self.active_powerups["goauld_ribbon_device"] = duration
            self.screen_shake.trigger(6, 12)
        elif ptype == "asgard_replicator_disruptor":
            # Chain-kill all enemies of same type as nearest
            px = self.player_ship.x + self.player_ship.width // 2
            py = self.player_ship.y
            if self.ai_ships:
                nearest = min(self.ai_ships,
                              key=lambda e: math.hypot(e.x - px, e.y - py))
                target_type = getattr(nearest, 'enemy_type', 'regular')
                same_type = [e for e in self.ai_ships
                             if getattr(e, 'enemy_type', 'regular') == target_type]
                for enemy in same_type:
                    enemy.health = 0
                    self._on_enemy_killed(enemy)
                self.screen_shake.trigger(10, 20)
                self.popup_notifications.append(PopupNotification(
                    px, py - 80,
                    f"DISRUPTOR: {len(same_type)} {target_type}s!", (100, 220, 255)))
        elif ptype == "jaffa_free_jaffa_rally":
            # Spawn 5 allied Jaffa ships for 10s
            for _ in range(5):
                self._spawn_ally_ship(duration=duration if duration > 0 else 600)
            self.screen_shake.trigger(6, 12)
        elif ptype == "lucian_kassa_stash":
            # Triple fire rate + 50% speed + invuln for 4s
            self.active_powerups["lucian_kassa_stash"] = duration
            self.active_powerups["goauld_sarcophagus"] = duration
            if not hasattr(self, '_saved_fire_rate'):
                self._saved_fire_rate = self.player_ship.fire_rate
            self.player_ship.fire_rate = max(2, self.player_ship.fire_rate // 3)
            self.screen_shake.trigger(8, 15)

    def _expire_powerup(self, ptype):
        """Handle expiration of a power-up effect."""
        if ptype == "rapid_fire":
            if hasattr(self, '_saved_fire_rate'):
                self.player_ship.fire_rate = self._saved_fire_rate
                # Only delete saved rate if overcharge isn't also active
                if self.active_powerups.get("overcharge", 0) <= 0:
                    del self._saved_fire_rate
            else:
                self.player_ship.fire_rate = min(self.player_ship.fire_rate * 2, 60)
        elif ptype == "drone":
            self.drones = []
        elif ptype == "damage":
            self.base_damage_mult = 1.15  # Reset to base (not 1.0 — player gets innate bonus)
        elif ptype == "overcharge":
            if hasattr(self, '_saved_fire_rate'):
                self.player_ship.fire_rate = self._saved_fire_rate
                # Only delete saved rate if rapid_fire isn't also active
                if self.active_powerups.get("rapid_fire", 0) <= 0:
                    del self._saved_fire_rate
            else:
                self.player_ship.fire_rate = min(self.player_ship.fire_rate * 3, 60)
        elif ptype == "tauri_ancient_drones":
            self.drones = []
        elif ptype == "goauld_kull_warrior":
            self.base_damage_mult = max(1.15, self.base_damage_mult / 2.0)
        elif ptype == "lucian_kassa_stash":
            if hasattr(self, '_saved_fire_rate'):
                self.player_ship.fire_rate = self._saved_fire_rate
                if (self.active_powerups.get("rapid_fire", 0) <= 0 and
                        self.active_powerups.get("overcharge", 0) <= 0):
                    del self._saved_fire_rate
            else:
                self.player_ship.fire_rate = min(self.player_ship.fire_rate * 3, 60)

    def is_cloaked(self):
        """Check if player is currently cloaked."""
        return self.active_powerups.get("cloak", 0) > 0

    def is_invulnerable(self):
        """Check if player has invulnerability active."""
        return self.active_powerups.get("goauld_sarcophagus", 0) > 0

    def _on_enemy_killed(self, ai_ship):
        """Handle bookkeeping when an enemy is killed by the player."""
        is_boss = getattr(ai_ship, 'is_boss', False)
        tier = "large" if is_boss else "normal"
        # Use themed explosion palette based on enemy type
        palette = ENEMY_EXPLOSION_PALETTES.get(getattr(ai_ship, 'enemy_type', ''))
        self.explosions.append(Explosion(
            ai_ship.x + ai_ship.width // 2, ai_ship.y, tier=tier,
            color_palette=palette))
        # Secondary explosion for bosses and wraith_hive (chain-explosion feel)
        if is_boss or getattr(ai_ship, 'enemy_type', '') == 'wraith_hive':
            ox = ai_ship.x + ai_ship.width // 2 + random.randint(-30, 30)
            oy = ai_ship.y + random.randint(-30, 30)
            self.explosions.append(Explosion(ox, oy, tier="normal",
                                            color_palette=palette, secondary=True))
        if ai_ship in self.ai_ships:
            self.ai_ships.remove(ai_ship)

        # --- Replicator split_on_death ---
        behavior = getattr(ai_ship, '_behavior', None)
        if behavior == "split_on_death" and getattr(ai_ship, '_split_gen', 0) < 2:
            for _ in range(2):
                child = Ship(
                    ai_ship.x + random.randint(-20, 20),
                    ai_ship.y + random.randint(-20, 20),
                    ai_ship.faction, is_player=False,
                    screen_width=self.screen_width, screen_height=self.screen_height)
                child.enemy_type = "replicator"
                child._behavior = "split_on_death"
                child._split_gen = ai_ship._split_gen + 1
                # Half HP, 0.7x scale of parent
                child.max_health = max(10, ai_ship.max_health // 2)
                child.health = child.max_health
                child.speed = ai_ship.speed
                child.xp_value = max(5, ai_ship.xp_value // 2)
                scale = 0.7
                if child.image:
                    import pygame
                    new_w = max(20, int(child.width * scale))
                    new_h = max(20, int(child.height * scale))
                    child.image = pygame.transform.smoothscale(child.image, (new_w, new_h))
                    child.width = new_w
                    child.height = new_h
                    # Apply replicator tint
                    tint_surf = pygame.Surface(child.image.get_size(), pygame.SRCALPHA)
                    tint_surf.fill((180, 180, 200, 60))
                    child.image.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                    child.image_right = child.image.copy()
                    child.image_left = pygame.transform.flip(child.image, True, False)
                    child.image_up = pygame.transform.rotate(child.image_right, 90)
                    child.image_down = pygame.transform.rotate(child.image_right, -90)
                child.ai_fire_timer = random.randint(0, 60)
                self.ai_ships.append(child)
        self.enemies_defeated += 1
        self.total_kills += 1

        # Kill streak
        self.kill_streak += 1
        self.kill_streak_timer = 0
        if self.kill_streak >= 3:
            self.score += self.kill_streak * 25

        # Screen shake on kill
        if is_boss:
            self.screen_shake.trigger(10, 20)
        else:
            self.screen_shake.trigger(2, 3)

        # Jaffa Warrior's Fury passive
        if self.player_ship.passive == "warriors_fury":
            self.player_ship.passive_state["kills"] = self.player_ship.passive_state.get("kills", 0) + 1

        # Jaffa Blood Rage: life steal on kill
        if self.active_powerups.get("jaffa_blood_rage", 0) > 0:
            heal = 10
            self.player_ship.health = min(self.player_ship.max_health,
                                          self.player_ship.health + heal)

        # Spawn XP orb
        xp_value = getattr(ai_ship, 'xp_value', 20)
        # Ancient Knowledge bonus
        ak_stacks = self.upgrades.get("ancient_knowledge", 0)
        if ak_stacks > 0:
            xp_value = int(xp_value * (1.0 + ak_stacks * 0.30))
        self.xp_orbs.append(XPOrb(ai_ship.x + ai_ship.width // 2, ai_ship.y, xp_value))

        # Score
        if is_boss:
            self.score += self.SCORE_BOSS
        else:
            self.score += self.SCORE_ENEMY

        # Power-up drop chance (doubled by Smuggler's Luck)
        drop_chance = self.powerup_drop_chance
        if self.active_powerups.get("lucian_smugglers_luck", 0) > 0:
            drop_chance = min(1.0, drop_chance * 2.0)
        if random.random() < drop_chance:
            self.powerups.append(PowerUp.spawn_at(
                ai_ship.x + ai_ship.width // 2, ai_ship.y,
                faction=self.player_faction))

        # Naquadah Bomb on-kill effect
        bomb_stacks = self.upgrades.get("naquadah_bomb", 0)
        if bomb_stacks > 0 and random.random() < 0.10 * bomb_stacks:
            self.explosions.append(Explosion(
                ai_ship.x + ai_ship.width // 2, ai_ship.y, tier="large"))
            self.screen_shake.trigger(6, 12)
            # Damage nearby enemies
            bomb_damage = 40 + bomb_stacks * 15
            for other in self.ai_ships[:]:
                dist = math.hypot(other.x - ai_ship.x, other.y - ai_ship.y)
                if dist < 150:
                    other.hit_flash = 5
                    self.damage_numbers.append(DamageNumber(
                        other.x + other.width // 2, other.y,
                        bomb_damage, (255, 200, 50)))
                    if self._damage_enemy(other, bomb_damage):
                        self._on_enemy_killed(other)

    def _gain_xp(self, amount):
        """Add XP and check for level-ups."""
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(80 * 1.12 ** (self.level - 1))
            self.pending_level_ups += 1

    def _prepare_level_up_choices(self):
        """Prepare 3 random upgrade choices for level-up selection."""
        # Check for available evolutions first
        evolution_available = self._check_evolutions()

        available = [
            name for name, info in UPGRADES.items()
            if self.upgrades.get(name, 0) < info["max"]
        ]

        # Add evolution as a choice if available
        if evolution_available:
            available.append(evolution_available)

        random.shuffle(available)
        self.level_up_choices = available[:3]

    def _check_evolutions(self):
        """Check if any evolution combo is ready. Returns evolution key or None."""
        for evo_name, evo_info in EVOLUTIONS.items():
            if evo_name in self.evolutions:
                continue  # Already evolved
            prereqs = evo_info["prereqs"]
            all_maxed = True
            for prereq in prereqs:
                prereq_info = UPGRADES.get(prereq, {})
                if self.upgrades.get(prereq, 0) < prereq_info.get("max", 999):
                    all_maxed = False
                    break
            if all_maxed:
                return evo_name
        return None

    def _select_upgrade(self, upgrade_name):
        """Apply the selected upgrade and resume gameplay."""
        ship = self.player_ship

        # Check if it's an evolution
        if upgrade_name in EVOLUTIONS:
            evo_info = EVOLUTIONS[upgrade_name]
            self.evolutions[upgrade_name] = True
            self.popup_notifications.append(PopupNotification(
                ship.x + ship.width // 2, ship.y - 60,
                f"EVOLUTION: {evo_info['name']}!",
                (255, 215, 0)
            ))
            self.screen_shake.trigger(8, 15)
            self.pending_level_ups -= 1
            if self.pending_level_ups > 0:
                self._prepare_level_up_choices()
            else:
                self.showing_level_up = False
                self.level_up_choices = []
            return

        self.upgrades[upgrade_name] = self.upgrades.get(upgrade_name, 0) + 1
        stacks = self.upgrades[upgrade_name]

        if upgrade_name == "naquadah_plating":
            ship.max_health += 20
            ship.health = min(ship.max_health, ship.health + 20)
        elif upgrade_name == "rapid_capacitors":
            ship.fire_rate = max(5, int(ship.fire_rate * 0.9))
        elif upgrade_name == "sublight_engines":
            ship.speed += 1
        elif upgrade_name == "shield_harmonics":
            ship.max_shields += 20
            ship.shields = min(ship.max_shields, ship.shields + 20)
        elif upgrade_name == "orbital_defense":
            angle = len(self.upgrade_drones) * (2 * math.pi / 3)
            self.upgrade_drones.append(Drone(ship, angle))
        elif upgrade_name == "hyperspace_jump":
            self.wormhole_max_cooldown = int(480 * (1.0 - stacks * 0.15))
        elif upgrade_name == "summon_ally":
            duration = 600 + (stacks - 1) * 300  # 10s base + 5s per extra stack
            self._spawn_ally_ship(duration)

        # Popup notification for the upgrade
        info = UPGRADES.get(upgrade_name, {})
        self.popup_notifications.append(PopupNotification(
            ship.x + ship.width // 2, ship.y - 60,
            info.get("name", upgrade_name),
            info.get("color", (255, 255, 255))
        ))

        self.pending_level_ups -= 1
        if self.pending_level_ups > 0:
            self._prepare_level_up_choices()
        else:
            self.showing_level_up = False
            self.level_up_choices = []

    def _damage_enemy(self, enemy, amount):
        """Damage an enemy, handling behavior-specific shields (Ori). Returns True if killed."""
        if getattr(enemy, '_behavior', None) == "shielded_charge" and enemy._shield_hp > 0:
            absorbed = min(enemy._shield_hp, amount)
            enemy._shield_hp -= absorbed
            amount -= absorbed
            if enemy._shield_hp <= 0:
                # Shields broken — trigger charge mode
                self.popup_notifications.append(PopupNotification(
                    enemy.x + enemy.width // 2, enemy.y - 40,
                    "SHIELDS DOWN!", (255, 255, 200)))
            if amount <= 0:
                return False
        return enemy.take_damage(amount)

    def _apply_splash_damage(self, x, y, damage, source_ship, already_killed=None):
        """Apply Lucian Alliance splash damage to nearby enemies."""
        splash_radius = 60
        splash_damage = damage * 0.4
        killed_set = already_killed or set()
        for ai_ship in self.ai_ships[:]:
            if ai_ship in killed_set:
                continue
            dist = math.hypot(ai_ship.x + ai_ship.width // 2 - x, ai_ship.y - y)
            if dist < splash_radius:
                ai_ship.hit_flash = 5
                self.damage_numbers.append(DamageNumber(
                    ai_ship.x + ai_ship.width // 2, ai_ship.y,
                    splash_damage, (255, 200, 100)))
                if self._damage_enemy(ai_ship, splash_damage):
                    killed_set.add(ai_ship)
                    self._on_enemy_killed(ai_ship)

    def _try_chain_lightning(self, hit_x, hit_y, damage, hit_enemy):
        """Try to chain lightning from a hit enemy to nearby enemies."""
        cl_stacks = self.upgrades.get("chain_lightning", 0)
        if cl_stacks <= 0:
            return

        # Thor's Hammer evolution: chain to ALL nearby enemies
        thors_hammer = "thors_hammer" in self.evolutions
        max_chains = 50 if thors_hammer else cl_stacks
        chain_range = 250 if thors_hammer else 150
        chain_targets = []
        hit_set = {id(hit_enemy)} if hit_enemy else set()

        current_x, current_y = hit_x, hit_y
        chain_damage = damage * (0.8 if thors_hammer else 0.6)

        for _ in range(max_chains):
            best = None
            best_dist = chain_range
            for enemy in self.ai_ships:
                if id(enemy) in hit_set:
                    continue
                ex = enemy.x + enemy.width // 2
                ey = enemy.y
                dist = math.hypot(ex - current_x, ey - current_y)
                if dist < best_dist:
                    best = enemy
                    best_dist = dist

            if best is None:
                break

            hit_set.add(id(best))
            target_x = best.x + best.width // 2
            target_y = best.y
            chain_targets.append((target_x, target_y))

            best.hit_flash = 5
            self.damage_numbers.append(DamageNumber(target_x, target_y, chain_damage, (100, 150, 255)))
            if self._damage_enemy(best, chain_damage):
                self._on_enemy_killed(best)

            current_x, current_y = target_x, target_y

        if chain_targets:
            self.chain_lightning_effects.append(
                ChainLightning(hit_x, hit_y, chain_targets, chain_damage))

    def _apply_critical(self, damage):
        """Apply critical strike chance. Returns (final_damage, is_crit)."""
        crit_stacks = self.upgrades.get("critical_strike", 0)
        if crit_stacks > 0 and random.random() < crit_stacks * 0.10:
            return damage * 2, True
        return damage, False

    def _check_evasion(self):
        """Check if player dodges an attack. Returns True if dodged."""
        evasion_stacks = self.upgrades.get("evasion_matrix", 0)
        if evasion_stacks > 0 and random.random() < evasion_stacks * 0.08:
            self.popup_notifications.append(PopupNotification(
                self.player_ship.x + self.player_ship.width // 2,
                self.player_ship.y - 40,
                "DODGE!", (200, 200, 255)
            ))
            return True
        return False

    def _get_berserker_mult(self):
        """Get berserker protocol damage multiplier."""
        bsk_stacks = self.upgrades.get("berserker_protocol", 0)
        if bsk_stacks > 0 and self.player_ship.health < self.player_ship.max_health * 0.5:
            return 1.0 + bsk_stacks * 0.05
        return 1.0

    def _update_new_upgrades(self):
        """Update timers and effects for new upgrade abilities."""
        # Nova Burst: AoE pulse around player
        nova_stacks = self.upgrades.get("nova_burst", 0)
        if nova_stacks > 0:
            # Check for Black Hole evolution
            black_hole = "black_hole" in self.evolutions
            self.nova_burst_timer += 1
            interval = 360 if black_hole else 480  # 6s or 8s
            if self.nova_burst_timer >= interval:
                self.nova_burst_timer = 0
                radius = 250 if black_hole else 180
                damage = 25 + nova_stacks * 15
                if black_hole:
                    damage *= 1.5
                # Damage all nearby enemies
                px = self.player_ship.x + self.player_ship.width // 2
                py = self.player_ship.y
                for enemy in self.ai_ships[:]:
                    dist = math.hypot(enemy.x + enemy.width // 2 - px, enemy.y - py)
                    if dist < radius:
                        enemy.hit_flash = 5
                        self.damage_numbers.append(DamageNumber(
                            enemy.x + enemy.width // 2, enemy.y,
                            damage, (255, 100, 200)))
                        if self._damage_enemy(enemy, damage):
                            self._on_enemy_killed(enemy)
                        # Black hole pulls enemies
                        if black_hole and dist > 10:
                            pull = 5.0 * (1 - dist / radius)
                            dx = px - enemy.x
                            dy = py - enemy.y
                            enemy.x += (dx / dist) * pull
                            enemy.y += (dy / dist) * pull
                # Visual pulse
                self.explosions.append(Explosion(px, py, tier="normal"))
                self.screen_shake.trigger(4, 8)

        # Orbital Laser: periodic beam from above
        laser_stacks = self.upgrades.get("orbital_laser", 0)
        if laser_stacks > 0 and self.ai_ships:
            self.orbital_laser_timer += 1
            if self.orbital_laser_timer >= 600:  # 10s
                self.orbital_laser_timer = 0
                # Find densest enemy cluster
                best_target = None
                best_count = 0
                for enemy in self.ai_ships:
                    count = sum(1 for e in self.ai_ships
                                if math.hypot(e.x - enemy.x, e.y - enemy.y) < 200)
                    if count > best_count:
                        best_count = count
                        best_target = enemy
                if best_target:
                    tx = best_target.x + best_target.width // 2
                    ty = best_target.y
                    damage = 50 + laser_stacks * 25
                    for enemy in self.ai_ships[:]:
                        dist = math.hypot(enemy.x + enemy.width // 2 - tx, enemy.y - ty)
                        if dist < 120:
                            enemy.hit_flash = 8
                            self.damage_numbers.append(DamageNumber(
                                enemy.x + enemy.width // 2, enemy.y,
                                damage, (0, 200, 255)))
                            if self._damage_enemy(enemy, damage):
                                self._on_enemy_killed(enemy)
                    self.explosions.append(Explosion(tx, ty, tier="large"))
                    self.screen_shake.trigger(6, 12)
                    # Store orbital strike visual
                    self.orbital_laser_effects.append({
                        'x': tx, 'y': ty, 'timer': 0, 'duration': 30
                    })

        # Update orbital laser visuals
        for strike in self.orbital_laser_effects:
            strike['timer'] += 1
        self.orbital_laser_effects = [
            e for e in self.orbital_laser_effects if e['timer'] < e['duration']
        ]

        # Temporal Field: slow nearby enemies
        tf_stacks = self.upgrades.get("temporal_field", 0)
        # Time Warp powerup stacks on top of temporal field
        time_warp_active = self.active_powerups.get("time_warp", 0) > 0
        if tf_stacks > 0 or time_warp_active:
            slow_factor = 1.0 - tf_stacks * 0.15  # 15% slow per stack
            if time_warp_active:
                slow_factor *= 0.35  # Time Warp: massive 65% additional slow
            slow_factor = max(0.15, slow_factor)
            px = self.player_ship.x + self.player_ship.width // 2
            py = self.player_ship.y
            slow_range = 600 if time_warp_active else 300
            for enemy in self.ai_ships:
                dist = math.hypot(enemy.x + enemy.width // 2 - px, enemy.y - py)
                if dist < slow_range:
                    if not hasattr(enemy, '_base_speed'):
                        enemy._base_speed = enemy.speed
                    enemy.speed = max(1, int(enemy._base_speed * slow_factor))
                else:
                    if hasattr(enemy, '_base_speed'):
                        enemy.speed = enemy._base_speed
        else:
            # No temporal field or time warp — restore all slowed enemies
            for enemy in self.ai_ships:
                if hasattr(enemy, '_base_speed'):
                    enemy.speed = enemy._base_speed
                    del enemy._base_speed

        # Magnetize powerup: pull all orbs and powerups toward player
        if self.active_powerups.get("magnetize", 0) > 0:
            px = self.player_ship.x + self.player_ship.width // 2
            py = self.player_ship.y
            for orb in self.xp_orbs:
                dx = px - orb.x
                dy = py - orb.y
                dist = math.hypot(dx, dy)
                if dist > 5:
                    orb.vx += (dx / dist) * 2.0
                    orb.vy += (dy / dist) * 2.0
            for pu in self.powerups:
                dist = math.hypot(pu.x - px, pu.y - py)
                if dist < 800 and dist > 5:
                    pull = 4.0 / dist
                    pu.x += (px - pu.x) * pull
                    pu.y += (py - pu.y) * pull

    def update(self):
        """Update game state."""
        if self.showing_level_up:
            return

        self.survival_frames += 1

        # Kill streak timer
        if self.kill_streak > 0:
            self.kill_streak_timer += 1
            if self.kill_streak_timer >= 180:  # 3 seconds
                self.kill_streak = 0
                self.kill_streak_timer = 0

        if self.game_over:
            self.explosions = [e for e in self.explosions if e.update()]
            self.damage_numbers = [d for d in self.damage_numbers if d.update()]
            return

        keys = pygame.key.get_pressed()

        # Update player ship
        if not self.wormhole_active:
            self.player_ship.update(keys)

            # Boost sound — play once on activation
            boosting_now = self.player_ship.thruster_boost_active
            if boosting_now and not self._was_boosting and self.boost_sound:
                try:
                    self.boost_sound.play()
                except Exception:
                    pass
            self._was_boosting = boosting_now

            # Derive facing from velocity (smooth — only change when moving)
            ship = self.player_ship
            if abs(ship.vx) > 0.5 or abs(ship.vy) > 0.5:
                # Pick dominant axis for facing
                if abs(ship.vx) >= abs(ship.vy):
                    ship.set_facing((1, 0) if ship.vx > 0 else (-1, 0))
                else:
                    ship.set_facing((0, -1) if ship.vy < 0 else (0, 1))

        # Update camera (smooth follow player center)
        player_cx = self.player_ship.x + self.player_ship.width // 2
        player_cy = self.player_ship.y
        self.camera.follow(player_cx, player_cy)

        # Wormhole cooldown tick
        if self.wormhole_cooldown > 0:
            self.wormhole_cooldown -= 1

        # Wormhole transit logic
        if self.wormhole_active:
            self.wormhole_transit_timer += 1
            halfway = self.wormhole_transit_duration // 2

            if self.wormhole_transit_timer == halfway:
                self.player_ship.x = self.wormhole_exit_x - self.player_ship.width // 2
                self.player_ship.y = self.wormhole_exit_y
                self.wormhole_effects.append(
                    WormholeEffect(self.wormhole_exit_x, self.wormhole_exit_y, is_entry=False))
                # Snap camera to new position for snappy feel
                self.camera.snap_to(self.wormhole_exit_x, self.wormhole_exit_y)

            if self.wormhole_transit_timer >= self.wormhole_transit_duration:
                self.wormhole_active = False
                self.wormhole_cooldown = self.wormhole_max_cooldown

        self.wormhole_effects = [e for e in self.wormhole_effects if e.update()]

        # --- Continuous spawner ---
        new_ships = self.spawner.update(self.ai_ships, self.screen_width, self.screen_height)
        self.ai_ships.extend(new_ships)

        # --- Despawn far-away entities ---
        despawn_dist = 2500
        self.ai_ships = [s for s in self.ai_ships
                         if math.hypot(s.x - self.camera.x, s.y - self.camera.y) < despawn_dist]
        self.asteroids = [a for a in self.asteroids if a.active and
                          math.hypot(a.x - self.camera.x, a.y - self.camera.y) < despawn_dist]
        self.xp_orbs = [o for o in self.xp_orbs if o.active and
                        math.hypot(o.x - self.camera.x, o.y - self.camera.y) < despawn_dist]
        self.powerups = [p for p in self.powerups if p.active and
                         math.hypot(p.x - self.camera.x, p.y - self.camera.y) < despawn_dist]
        self.area_bombs = [b for b in self.area_bombs if b.active and
                           math.hypot(b.x - self.camera.x, b.y - self.camera.y) < despawn_dist]

        # Shield Bash (dash) logic
        bash_stacks = self.upgrades.get("shield_bash", 0)
        if bash_stacks > 0:
            if self.dash_cooldown > 0:
                self.dash_cooldown -= 1

            player_vx = self.player_ship.x - (self.camera.x - self.camera.vx / self.camera.lerp_speed * self.camera.lerp_speed if hasattr(self.camera, 'vx') else 0)
            player_moving = abs(self.camera.vx) > 0.5 or abs(self.camera.vy) > 0.5

            if player_moving and not self.dash_active and self.dash_cooldown <= 0:
                self.dash_active = True
                self.dash_timer = 30
                self.dash_afterimages = []

            if self.dash_active:
                self.dash_timer -= 1
                if self.dash_timer % 3 == 0:
                    self.dash_afterimages.append({
                        'x': self.player_ship.x,
                        'y': self.player_ship.y,
                        'alpha': 150,
                    })

                player_rect = self.player_ship.get_rect()
                dash_damage = 30 + bash_stacks * 10
                for ai_ship in self.ai_ships[:]:
                    if ai_ship.get_rect().colliderect(player_rect):
                        ai_ship.hit_flash = 5
                        self.damage_numbers.append(DamageNumber(
                            ai_ship.x + ai_ship.width // 2, ai_ship.y,
                            dash_damage, (255, 200, 50)))
                        if self._damage_enemy(ai_ship, dash_damage):
                            self._on_enemy_killed(ai_ship)

                if self.dash_timer <= 0:
                    self.dash_active = False
                    self.dash_cooldown = 180

            for ai in self.dash_afterimages[:]:
                ai['alpha'] -= 10
            self.dash_afterimages = [a for a in self.dash_afterimages if a['alpha'] > 0]

        # Sarcophagus passive healing
        sarc_stacks = self.upgrades.get("sarcophagus", 0)
        if sarc_stacks > 0:
            heal_rate = sarc_stacks * 5.0 / 60.0
            self.player_ship.health = min(self.player_ship.max_health,
                                          self.player_ship.health + heal_rate)

        # Shield Harmonics passive regen
        shield_stacks = self.upgrades.get("shield_harmonics", 0)
        if shield_stacks > 0:
            regen = shield_stacks * 0.1
            self.player_ship.shields = min(self.player_ship.max_shields,
                                           self.player_ship.shields + regen)

        # Rear Turret auto-fire
        rear_stacks = self.upgrades.get("rear_turret", 0)
        if rear_stacks > 0:
            self.rear_turret_timer += 1
            if self.rear_turret_timer >= max(20, 40 - rear_stacks * 5):
                self.rear_turret_timer = 0
                fdx, fdy = self.player_ship.facing
                rear_dir = (-fdx, -fdy)
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

        # Gravity Well auto-deploy
        gw_stacks = self.upgrades.get("gravity_well", 0)
        if gw_stacks > 0:
            self.gravity_well_timer += 1
            if self.gravity_well_timer >= 600 and self.ai_ships:
                self.gravity_well_timer = 0
                cx = sum(s.x + s.width // 2 for s in self.ai_ships) / len(self.ai_ships)
                cy = sum(s.y for s in self.ai_ships) / len(self.ai_ships)
                self.gravity_wells.append(GravityWell(cx, cy, gw_stacks))

        # Update gravity wells
        for gw in self.gravity_wells[:]:
            killed = gw.update(self.ai_ships)
            for enemy in killed:
                self._on_enemy_killed(enemy)
            if not gw.active:
                self.gravity_wells.remove(gw)

        # New upgrade effects
        self._update_new_upgrades()

        # --- Faction powerup ongoing effects ---
        # Asgard Beam Array: auto-fire beams in all directions
        if self.active_powerups.get("asgard_beam_array", 0) > 0:
            if self.survival_frames % 10 == 0:  # Every 10 frames
                px = self.player_ship.x + self.player_ship.width // 2
                py = self.player_ship.y
                for direction in [(1, 0), (-1, 0), (0, -1), (0, 1)]:
                    proj = Laser(px, py, direction, (0, 255, 255), speed=22)
                    proj.damage = 20
                    proj.is_player_proj = True
                    self.projectiles.append(proj)

        # Tau'ri Railgun Barrage: auto-fire railgun toward nearest enemy
        if self.active_powerups.get("tauri_railgun_barrage", 0) > 0:
            if not hasattr(self, '_railgun_barrage_timer'):
                self._railgun_barrage_timer = 0
            self._railgun_barrage_timer += 1
            if self._railgun_barrage_timer >= 30 and self.ai_ships:  # Every 0.5s
                self._railgun_barrage_timer = 0
                nearest = min(self.ai_ships,
                              key=lambda e: math.hypot(e.x - self.player_ship.x,
                                                        e.y - self.player_ship.y))
                dx = nearest.x - self.player_ship.x
                dy = nearest.y - self.player_ship.y
                dist = math.hypot(dx, dy)
                if dist > 1:
                    direction = (dx / dist, dy / dist)
                    px = self.player_ship.x + self.player_ship.width // 2
                    py = self.player_ship.y
                    proj = RailgunShot(px, py, direction, (80, 180, 255))
                    proj.is_player_proj = True
                    proj.damage = 40
                    self.projectiles.append(proj)

        # Jaffa Blood Rage: triple damage + life steal on kill
        # (damage mult handled in auto-fire section, life steal in _on_enemy_killed)

        # Lucian Kassa: enemies damage each other
        if self.active_powerups.get("lucian_kassa", 0) > 0:
            if self.survival_frames % 30 == 0:  # Every 0.5s
                px = self.player_ship.x + self.player_ship.width // 2
                py = self.player_ship.y
                for enemy in self.ai_ships[:]:
                    dist = math.hypot(enemy.x + enemy.width // 2 - px, enemy.y - py)
                    if dist < 500:
                        # Confused enemies hurt each other
                        dmg = 8
                        enemy.hit_flash = 3
                        self.damage_numbers.append(DamageNumber(
                            enemy.x + enemy.width // 2, enemy.y,
                            dmg, (200, 80, 255)))
                        if self._damage_enemy(enemy, dmg):
                            self._on_enemy_killed(enemy)

        # Jaffa Freedom (KREE): 3x damage handled in auto-fire, invuln via sarcophagus

        # Asgard Time Dilation: slow all enemies to 25%
        if self.active_powerups.get("asgard_time_dilation", 0) > 0:
            for enemy in self.ai_ships:
                enemy.speed = max(1, int(enemy.speed * 0.25))

        # Jaffa Tretonin: double HP regen
        if self.active_powerups.get("jaffa_tretonin", 0) > 0:
            heal_rate = 10.0 / 60.0  # 10 HP/s
            self.player_ship.health = min(self.player_ship.max_health,
                                          self.player_ship.health + heal_rate)

        # Goa'uld Ribbon Device: drain nearest enemy HP to heal player
        if self.active_powerups.get("goauld_ribbon_device", 0) > 0:
            if self.ai_ships:
                px = self.player_ship.x + self.player_ship.width // 2
                py = self.player_ship.y
                nearest = min(self.ai_ships,
                              key=lambda e: math.hypot(e.x - px, e.y - py))
                dist = math.hypot(nearest.x + nearest.width // 2 - px, nearest.y - py)
                if dist < 400:
                    drain = 2  # 2 DPS (per frame at 60fps = 120 DPS total... actually 2 per frame)
                    nearest.hit_flash = 3
                    if self._damage_enemy(nearest, drain):
                        self._on_enemy_killed(nearest)
                    else:
                        self.player_ship.health = min(self.player_ship.max_health,
                                                      self.player_ship.health + drain)

        # Lucian Smuggler's Luck: double powerup drop rate (checked in _on_enemy_killed)

        # Lucian Kassa Stash: speed boost while active
        if self.active_powerups.get("lucian_kassa_stash", 0) > 0:
            self.player_ship.speed = int(self.player_ship.speed * 1.5)

        # Tau'ri Ancient Tech: piercing + homing handled in projectile loop

        # Enemy stun handling (from Hand Device)
        for enemy in self.ai_ships:
            if getattr(enemy, '_stunned', 0) > 0:
                enemy._stunned -= 1
                enemy.vx = 0
                enemy.vy = 0

        # Orbital Defense drones
        for drone in self.upgrade_drones:
            proj = drone.update(self.ai_ships)
            if proj:
                self.projectiles.append(proj)

        # Update all AI ships
        for ai_ship in self.ai_ships:
            # Skip AI update if stunned
            if getattr(ai_ship, '_stunned', 0) > 0:
                ai_ship.stop_beam()
                continue

            ai_ship.update_ai(self.player_ship, self.asteroids, self.ai_ships)

            # AI firing
            if self.is_cloaked():
                ai_ship.stop_beam()
                continue

            ai_ship.ai_fire_timer -= 1
            y_diff = abs(ai_ship.y - self.player_ship.y)
            dx_to_player = self.player_ship.x - ai_ship.x
            facing_player = (ai_ship.facing[0] > 0 and dx_to_player > 0) or \
                            (ai_ship.facing[0] < 0 and dx_to_player < 0)

            if ai_ship.weapon_type == "beam":
                if y_diff < 80 and facing_player:
                    if not ai_ship.current_beam:
                        ai_ship.fire()
                else:
                    ai_ship.stop_beam()
            else:
                if ai_ship.ai_fire_timer <= 0 and y_diff < 150 and facing_player:
                    projectile = ai_ship.fire()
                    if projectile:
                        self.projectiles.append(projectile)
                    # Boss multi-phase
                    if getattr(ai_ship, 'is_boss', False):
                        hp_pct = ai_ship.health / ai_ship.max_health
                        if hp_pct < 0.25:
                            ai_ship.ai_fire_timer = random.randint(60, 110)
                            extra = ai_ship.fire()
                            if extra is None:
                                fire_x = ai_ship.x
                                extra = Laser(fire_x, ai_ship.y,
                                              ai_ship.facing,
                                              ai_ship.laser_color, speed=14)
                                extra.damage = 8
                            extra.is_player_proj = False
                            self.projectiles.append(extra)
                        elif hp_pct < 0.50:
                            ai_ship.ai_fire_timer = random.randint(90, 160)
                        elif hp_pct < 0.75:
                            ai_ship.ai_fire_timer = random.randint(120, 200)
                        else:
                            ai_ship.ai_fire_timer = random.randint(150, 250)
                    else:
                        # Enemy fire rate scales with difficulty tier
                        tier_label = self.spawner.get_difficulty_label()
                        if tier_label in ("Beyond", "Apocalypse"):
                            ai_ship.ai_fire_timer = random.randint(120, 240)
                        elif tier_label in ("Overwhelming", "Dangerous"):
                            ai_ship.ai_fire_timer = random.randint(180, 330)
                        elif tier_label in ("Intense", "Contested"):
                            ai_ship.ai_fire_timer = random.randint(240, 420)
                        else:
                            ai_ship.ai_fire_timer = random.randint(300, 540)

        # --- Behavior-specific updates (bomber, hive, ori shields) ---
        for ai_ship in self.ai_ships[:]:
            behavior = getattr(ai_ship, '_behavior', None)
            if behavior == "bomber":
                ai_ship._bomber_timer += 1
                if ai_ship._bomber_timer >= 180:
                    ai_ship._bomber_timer = 0
                    # Drop area bomb toward player
                    px = self.player_ship.x + self.player_ship.width // 2
                    py = self.player_ship.y
                    bomb = AreaBomb(ai_ship.x + ai_ship.width // 2, ai_ship.y,
                                   px, py, damage=30, blast_radius=120)
                    self.area_bombs.append(bomb)
            elif behavior == "mini_boss_spawner":
                ai_ship._spawner_timer += 1
                # Clean dead dart refs
                ai_ship._spawned_darts = [d for d in ai_ship._spawned_darts
                                          if d in self.ai_ships]
                if ai_ship._spawner_timer >= 300 and len(ai_ship._spawned_darts) < 4:
                    ai_ship._spawner_timer = 0
                    dart = Ship(
                        ai_ship.x + random.randint(-60, 60),
                        ai_ship.y + random.randint(-60, 60),
                        ai_ship.faction, is_player=False,
                        screen_width=self.screen_width, screen_height=self.screen_height)
                    dart.enemy_type = "wraith_dart"
                    dart._behavior = "swarm_lifesteal"
                    dart.max_health = int(50 * self.spawner.get_current_tier().get("hp_mult", 1.0))
                    dart.health = dart.max_health
                    dart.speed = max(1, int(dart.speed * 1.1))
                    dart.xp_value = 25
                    # Tint purple
                    if dart.image:
                        tint = pygame.Surface(dart.image.get_size(), pygame.SRCALPHA)
                        tint.fill((80, 0, 160, 60))
                        dart.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                        dart.image_right = dart.image.copy()
                        dart.image_left = pygame.transform.flip(dart.image, True, False)
                        dart.image_up = pygame.transform.rotate(dart.image_right, 90)
                        dart.image_down = pygame.transform.rotate(dart.image_right, -90)
                    dart.ai_fire_timer = random.randint(0, 60)
                    self.ai_ships.append(dart)
                    ai_ship._spawned_darts.append(dart)

        # --- Update area bombs ---
        for bomb in self.area_bombs[:]:
            bomb.update()
            if not bomb.active:
                # Detonated — deal AoE damage to player (and enemies near blast)
                px = self.player_ship.x + self.player_ship.width // 2
                py = self.player_ship.y
                dist = math.hypot(px - bomb.x, py - bomb.y)
                if dist < bomb.blast_radius:
                    dmg = int(bomb.damage * (1.0 - dist / bomb.blast_radius * 0.5))
                    if not self._check_evasion() and not self.is_invulnerable():
                        self.player_hit_flash = 8
                        self.screen_shake.trigger(5, 10)
                        self.damage_numbers.append(DamageNumber(px, py, dmg, (255, 100, 0)))
                        if self.player_ship.take_damage(dmg):
                            self.game_over = True
                            self.winner = "ai"
                            self._save_score()
                            self.explosions.append(Explosion(px, py, tier="large"))
                self.explosions.append(Explosion(bomb.x, bomb.y, tier="normal",
                                                color_palette=[(255, 150, 0), (200, 100, 0), (255, 200, 50)]))
                self.screen_shake.trigger(4, 8)
                self.area_bombs.remove(bomb)

        # --- Update suns ---
        for sun in self.suns[:]:
            entities_dict = {
                'ships': [self.player_ship],
                'enemies': self.ai_ships,
                'projectiles': self.projectiles,
                'asteroids': self.asteroids,
                'allies': self.ally_ships,
            }
            sun.update(entities_dict)
            # Screen shake on explosion phase start
            if sun.phase == Sun.PHASE_EXPLODING and sun.timer == 1:
                self.screen_shake.trigger(8, 15)
            if not sun.active:
                self.suns.remove(sun)

        # Sun spawning: first at 30s, then every 40-60s
        if self.survival_seconds >= 30:
            if not self.sun_first_spawn_done:
                self.sun_first_spawn_done = True
                self.sun_spawn_timer = 0
                self._sun_next_interval = random.randint(2400, 3600)
                self._spawn_sun()
            else:
                self.sun_spawn_timer += 1
                if not hasattr(self, '_sun_next_interval'):
                    self._sun_next_interval = random.randint(2400, 3600)
                if self.sun_spawn_timer >= self._sun_next_interval:
                    self.sun_spawn_timer = 0
                    self._sun_next_interval = random.randint(2400, 3600)
                    self._spawn_sun()

        # --- Update ally ships ---
        for ally in self.ally_ships[:]:
            proj = ally.update_ally_ai(self.player_ship, self.ai_ships)
            if proj:
                self.projectiles.append(proj)
            ally.ally_lifetime -= 1
            if ally.ally_lifetime <= 0 or ally.health <= 0:
                self.explosions.append(Explosion(
                    ally.x + ally.width // 2, ally.y, tier="small"))
                self.ally_ships.remove(ally)

        # Player auto-fire
        if not self.game_over:
            berserker_mult = self._get_berserker_mult()

            # Bullet Hell evolution: fire in ALL directions
            bullet_hell = "bullet_hell" in self.evolutions

            if self.player_ship.weapon_type == "beam":
                if not self.player_ship.current_beam:
                    beam = self.player_ship.fire()
                    if beam:
                        wp_stacks = self.upgrades.get("weapons_power", 0)
                        if wp_stacks > 0:
                            beam.damage_per_frame *= (1.0 + wp_stacks * 0.15)
                        beam.damage_per_frame *= berserker_mult
            else:
                projectile = self.player_ship.fire()
                if projectile:
                    wp_mult = 1.0 + self.upgrades.get("weapons_power", 0) * 0.15
                    war_cry_mult = 1.5 if self.player_ship.secondary_buff_timer > 0 else 1.0
                    # Faction powerup damage bonuses
                    faction_dmg_mult = 1.0
                    if self.active_powerups.get("jaffa_blood_rage", 0) > 0:
                        faction_dmg_mult = 3.0
                    elif self.active_powerups.get("jaffa_freedom", 0) > 0:
                        faction_dmg_mult = 3.0
                    base_dmg = projectile.damage * self.base_damage_mult * wp_mult * berserker_mult * war_cry_mult * faction_dmg_mult
                    base_dmg, is_crit = self._apply_critical(base_dmg)
                    projectile.damage = int(base_dmg)
                    projectile._is_crit = is_crit
                    self.projectiles.append(projectile)

                    # Multi-Targeting extra projectiles
                    mt_stacks = self.upgrades.get("multi_targeting", 0)
                    if bullet_hell:
                        mt_stacks = max(mt_stacks, 5)  # Force max spread

                    if mt_stacks > 0 and not isinstance(projectile, ContinuousBeam):
                        fdx, fdy = self.player_ship.facing
                        ship = self.player_ship
                        cx = ship.x + ship.width // 2
                        cy = ship.y

                        extra_dirs = []
                        for i in range(1, min(mt_stacks + 1, 4)):
                            for angle_sign in [1, -1]:
                                extra_dirs.append(('spread', angle_sign * i * 8))

                        if mt_stacks >= 2 or bullet_hell:
                            if abs(fdx) > 0:
                                extra_dirs.append(('dir', (0, -1)))
                                extra_dirs.append(('dir', (0, 1)))
                            else:
                                extra_dirs.append(('dir', (-1, 0)))
                                extra_dirs.append(('dir', (1, 0)))

                        if mt_stacks >= 3 or bullet_hell:
                            extra_dirs.append(('dir', (-fdx, -fdy)))

                        if mt_stacks >= 4 or bullet_hell:
                            for ddx in [-1, 1]:
                                for ddy in [-1, 1]:
                                    if (ddx, ddy) != (fdx, fdy):
                                        extra_dirs.append(('dir', (ddx, ddy)))

                        for entry in extra_dirs:
                            if len(self.projectiles) > 300:
                                break
                            if entry[0] == 'spread':
                                spread = entry[1]
                                d = self.player_ship.facing
                                if fdx == 1:
                                    fx = ship.x + ship.width
                                    fy = cy
                                elif fdx == -1:
                                    fx = ship.x
                                    fy = cy
                                elif fdy == -1:
                                    fx = cx
                                    fy = ship.y - ship.height // 2
                                else:
                                    fx = cx
                                    fy = ship.y + ship.height // 2
                                extra = type(projectile)(fx, fy, d, ship.laser_color)
                                extra.is_player_proj = True
                                extra_dmg = extra.damage * self.base_damage_mult * wp_mult * berserker_mult
                                extra_dmg, _ = self._apply_critical(extra_dmg)
                                extra.damage = int(extra_dmg)
                                offset = math.tan(math.radians(spread)) * 50
                                if abs(fdx) > 0:
                                    extra.y += offset
                                else:
                                    extra.x += offset
                                self.projectiles.append(extra)
                            else:
                                d = entry[1]
                                extra = type(projectile)(cx, cy, d, ship.laser_color)
                                extra.is_player_proj = True
                                extra_dmg = extra.damage * self.base_damage_mult * wp_mult * berserker_mult * 0.7
                                extra_dmg, _ = self._apply_critical(extra_dmg)
                                extra.damage = int(extra_dmg)
                                self.projectiles.append(extra)

                    # Scatter Shot
                    scatter_stacks = self.upgrades.get("scatter_shot", 0)
                    # Cluster Bomb evolution boosts scatter
                    cluster_bomb = "cluster_bomb" in self.evolutions
                    if cluster_bomb:
                        scatter_stacks = max(scatter_stacks, 3)
                    if scatter_stacks > 0 and len(self.projectiles) <= 300:
                        fdx, fdy = self.player_ship.facing
                        num_pellets = scatter_stacks * 3
                        for p_idx in range(num_pellets):
                            spread_angle = random.uniform(-25, 25)
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
                            pellet = Laser(fx, fy, self.player_ship.facing,
                                          self.player_ship.laser_color, speed=22)
                            pellet.damage = int(projectile.damage * 0.4)
                            pellet.is_player_proj = True
                            offset = math.tan(math.radians(spread_angle)) * 40
                            if abs(fdx) > 0:
                                pellet.y += offset
                            else:
                                pellet.x += offset
                            pellet.width = max(2, pellet.width // 2)
                            pellet.height = max(2, pellet.height // 2)
                            self.projectiles.append(pellet)

        # Spawn asteroids around viewport
        self.asteroid_spawn_timer += 1
        if self.asteroid_spawn_timer >= self.asteroid_spawn_rate:
            self.asteroid_spawn_timer = 0
            ax, ay = self.camera.get_spawn_ring(400, 600)
            # Give asteroid velocity toward viewport center roughly
            angle_to_center = math.atan2(self.camera.y - ay, self.camera.x - ax)
            speed = random.uniform(2.0, 5.0)
            self.asteroids.append(Asteroid(
                ax, ay,
                vx=math.cos(angle_to_center) * speed + random.uniform(-0.5, 0.5),
                vy=math.sin(angle_to_center) * speed + random.uniform(-0.5, 0.5)
            ))

        # Update asteroids
        for asteroid in self.asteroids:
            asteroid.update()

        # Periodic powerup spawns near player (every 4-7 seconds)
        self.powerup_spawn_timer += 1
        if self.powerup_spawn_timer >= random.randint(240, 420):
            self.powerup_spawn_timer = 0
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(150, 350)
            px = self.player_ship.x + math.cos(angle) * dist
            py = self.player_ship.y + math.sin(angle) * dist
            self.powerups.append(PowerUp.spawn_at(px, py, faction=self.player_faction))

        # Update power-ups
        for powerup in self.powerups[:]:
            powerup.update()
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

        # Update proximity mines
        for mine in self.mines[:]:
            mine.update()
            if not mine.active:
                self.mines.remove(mine)
                continue
            if mine.is_armed():
                for enemy in self.ai_ships[:]:
                    dist = math.hypot(enemy.x + enemy.width // 2 - mine.x,
                                      enemy.y - mine.y)
                    if dist < mine.detection_radius:
                        # Mine explodes!
                        self.explosions.append(Explosion(mine.x, mine.y, tier="normal"))
                        self.screen_shake.trigger(3, 6)
                        # Damage all nearby enemies
                        for target in self.ai_ships[:]:
                            tdist = math.hypot(target.x + target.width // 2 - mine.x,
                                              target.y - mine.y)
                            if tdist < 120:
                                dmg = int(mine.damage * (1.0 - tdist / 120 * 0.5))
                                target.hit_flash = 5
                                self.damage_numbers.append(DamageNumber(
                                    target.x + target.width // 2, target.y,
                                    dmg, (255, 100, 200)))
                                if self._damage_enemy(target, dmg):
                                    self._on_enemy_killed(target)
                        mine.active = False
                        self.mines.remove(mine)
                        break

        # Update ion pulse effects
        for pulse in self.ion_pulse_effects:
            pulse["timer"] += 1
            pulse["radius"] = int(pulse["max_radius"] * (pulse["timer"] / pulse["duration"]))
        self.ion_pulse_effects = [p for p in self.ion_pulse_effects
                                   if p["timer"] < p["duration"]]

        # War Cry buff: boost fire rate while active
        if self.player_ship.secondary_buff_timer > 0:
            # Halve fire cooldown each frame it's active
            if self.player_ship.fire_cooldown > 1:
                self.player_ship.fire_cooldown = max(1, self.player_ship.fire_cooldown - 1)

        # Update projectiles
        tc_stacks = self.upgrades.get("targeting_computer", 0)
        to_remove_projs = []
        for proj_idx, proj in enumerate(self.projectiles):
            proj.update()

            # Targeting Computer homing (also from Ancient Tech powerup)
            ancient_tech_homing = self.active_powerups.get("tauri_ancient_tech", 0) > 0
            if (tc_stacks > 0 or ancient_tech_homing) and proj.is_player_proj and self.ai_ships:
                nearest = min(self.ai_ships,
                              key=lambda e: math.hypot(e.x - proj.x, e.y - proj.y))
                max_adjust = max(tc_stacks * 2.0, 3.0 if ancient_tech_homing else 0)
                pdx, pdy = proj.direction
                if abs(pdx) > abs(pdy):
                    diff = nearest.y - proj.y
                    if abs(diff) > 1:
                        proj.y += max(-max_adjust, min(max_adjust, diff * 0.05))
                else:
                    diff = nearest.x - proj.x
                    if abs(diff) > 1:
                        proj.x += max(-max_adjust, min(max_adjust, diff * 0.05))

            # Remove if too far from camera
            if not self.camera.is_visible(proj.x, proj.y, margin=400):
                to_remove_projs.append(proj_idx)
                continue

            proj_rect = proj.get_rect()

            if proj.is_player_proj:
                hit = False
                for ai_ship in self.ai_ships[:]:
                    if proj_rect.colliderect(ai_ship.get_rect()):
                        hit = True
                        ai_ship.hit_flash = 10
                        self._play_hit_sound()
                        hit_x = ai_ship.x + ai_ship.width // 2
                        hit_y = ai_ship.y

                        is_crit = getattr(proj, '_is_crit', False)
                        dmg_color = (255, 255, 0) if is_crit else (255, 255, 255)
                        self.damage_numbers.append(DamageNumber(hit_x, hit_y, proj.damage, dmg_color))

                        _killed_this_hit = set()
                        if self._damage_enemy(ai_ship, proj.damage):
                            _killed_this_hit.add(ai_ship)
                            self._on_enemy_killed(ai_ship)

                        self._try_chain_lightning(hit_x, hit_y, proj.damage, ai_ship)

                        if self.player_ship.passive == "splash_damage" and isinstance(proj, EnergyBall):
                            self._apply_splash_damage(hit_x, hit_y, proj.damage, self.player_ship, already_killed=_killed_this_hit)
                        break
                # Ancient Tech: all player projectiles pierce
                has_piercing = getattr(proj, 'piercing', False)
                if self.active_powerups.get("tauri_ancient_tech", 0) > 0:
                    has_piercing = True
                if hit and not has_piercing:
                    to_remove_projs.append(proj_idx)
                    continue
            else:
                if not self.wormhole_active and proj_rect.colliderect(self.player_ship.get_rect()):
                    if self._check_evasion() or self.is_invulnerable():
                        to_remove_projs.append(proj_idx)
                        if self.is_invulnerable():
                            self.damage_numbers.append(DamageNumber(
                                self.player_ship.x + self.player_ship.width // 2,
                                self.player_ship.y, 0, (255, 215, 0)))
                        continue

                    to_remove_projs.append(proj_idx)
                    self.player_hit_flash = 10
                    self.screen_shake.trigger(5, 8)

                    actual_damage = proj.damage
                    # Prometheus Shield: absorb damage and reflect 50%
                    if (self.active_powerups.get("tauri_prometheus_shield", 0) > 0
                            and getattr(self, '_prometheus_shield_hp', 0) > 0):
                        absorbed = min(self._prometheus_shield_hp, actual_damage)
                        self._prometheus_shield_hp -= absorbed
                        actual_damage -= absorbed
                        # Reflect 50% of absorbed back at nearest enemy
                        if self.ai_ships:
                            px = self.player_ship.x + self.player_ship.width // 2
                            py = self.player_ship.y
                            nearest = min(self.ai_ships,
                                          key=lambda e: math.hypot(e.x - px, e.y - py))
                            reflect_dmg = int(absorbed * 0.5)
                            if reflect_dmg > 0:
                                nearest.hit_flash = 5
                                self.damage_numbers.append(DamageNumber(
                                    nearest.x + nearest.width // 2, nearest.y,
                                    reflect_dmg, (100, 200, 255)))
                                if self._damage_enemy(nearest, reflect_dmg):
                                    self._on_enemy_killed(nearest)
                        if self._prometheus_shield_hp <= 0:
                            self.active_powerups["tauri_prometheus_shield"] = 0
                            self.popup_notifications.append(PopupNotification(
                                self.player_ship.x + self.player_ship.width // 2,
                                self.player_ship.y - 60,
                                "SHIELD DEPLETED", (255, 100, 100)))
                        self.damage_numbers.append(DamageNumber(
                            self.player_ship.x + self.player_ship.width // 2,
                            self.player_ship.y, absorbed, (100, 200, 255)))
                        if actual_damage <= 0:
                            continue

                    self.damage_numbers.append(DamageNumber(
                        self.player_ship.x + self.player_ship.width // 2,
                        self.player_ship.y, actual_damage, (255, 80, 80)))

                    if self.player_ship.take_damage(actual_damage):
                        self.game_over = True
                        self.winner = "ai"
                        self._save_score()
                        self.explosions.append(Explosion(
                            self.player_ship.x + self.player_ship.width // 2,
                            self.player_ship.y, tier="large"))
                    continue

                # Enemy projectile vs ally ships
                ally_hit = False
                for ally in self.ally_ships[:]:
                    if proj_rect.colliderect(ally.get_rect()):
                        ally.hit_flash = 5
                        ally.take_damage(proj.damage)
                        to_remove_projs.append(proj_idx)
                        ally_hit = True
                        break
                if ally_hit:
                    continue

            # Projectile vs asteroids
            for asteroid in self.asteroids[:]:
                if proj_rect.colliderect(asteroid.get_rect()):
                    to_remove_projs.append(proj_idx)
                    if asteroid.take_damage(proj.damage):
                        self.explosions.append(Explosion(asteroid.x, asteroid.y, tier="small"))
                        asteroid.active = False
                        if proj.is_player_proj:
                            self.score += self.SCORE_ASTEROID
                            self.asteroids_destroyed += 1
                            self.xp_orbs.append(XPOrb(asteroid.x, asteroid.y, 10))
                    break

        # Remove projectiles (reverse order to preserve indices)
        for idx in sorted(set(to_remove_projs), reverse=True):
            if idx < len(self.projectiles):
                self.projectiles.pop(idx)

        # Check beam collision (player)
        if self.player_ship.current_beam:
            beam = self.player_ship.current_beam
            beam_sx, beam_sy = beam.get_start_pos()
            bdx, bdy = beam.direction
            piercing = self.player_ship.passive == "beam_pierce"
            is_horizontal = abs(bdx) > abs(bdy)

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

            beam_end_dist = beam.max_range
            hit_first = False
            for dist, target, is_ast in targets:
                if not piercing and dist > beam_end_dist:
                    break
                dmg = beam.damage_per_frame * (0.5 if (piercing and hit_first) else 1.0)
                dmg *= self._get_berserker_mult()
                hit_first = True
                if is_ast:
                    if target.take_damage(dmg):
                        self.explosions.append(Explosion(target.x, target.y, tier="small"))
                        target.active = False
                        self.score += self.SCORE_ASTEROID
                        self.asteroids_destroyed += 1
                        self.xp_orbs.append(XPOrb(target.x, target.y, 10))
                    if not piercing:
                        beam_end_dist = dist
                else:
                    target.hit_flash = 3
                    if self._damage_enemy(target, dmg):
                        self._on_enemy_killed(target)
                    if not piercing:
                        beam_end_dist = dist

            beam.set_length(beam_end_dist)

        # Check AI beam collision with player
        for ai_ship in self.ai_ships:
            if ai_ship.current_beam:
                beam = ai_ship.current_beam
                beam_start_x, _ = beam.get_start_pos()
                beam_dir = ai_ship.facing[0]

                closest_hit_dist = beam.max_range
                hit_target = None
                is_asteroid = False

                beam_y = ai_ship.y
                if not self.wormhole_active and abs(self.player_ship.y - beam_y) < (self.player_ship.height // 2 + 10):
                    if beam_dir < 0:
                        dist = beam_start_x - (self.player_ship.x + self.player_ship.width)
                    else:
                        dist = self.player_ship.x - beam_start_x
                    if 0 < dist < closest_hit_dist:
                        closest_hit_dist = dist
                        hit_target = self.player_ship
                        is_asteroid = False

                for asteroid in self.asteroids:
                    if abs(asteroid.y - beam_y) < (asteroid.size // 2 + 10):
                        if beam_dir < 0:
                            dist = beam_start_x - (asteroid.x + asteroid.size // 2)
                        else:
                            dist = (asteroid.x - asteroid.size // 2) - beam_start_x
                        if 0 < dist < closest_hit_dist:
                            closest_hit_dist = dist
                            hit_target = asteroid
                            is_asteroid = True

                beam.set_length(closest_hit_dist)

                if hit_target:
                    if is_asteroid:
                        if hit_target.take_damage(beam.damage_per_frame):
                            self.explosions.append(Explosion(hit_target.x, hit_target.y, tier="small"))
                            hit_target.active = False
                    else:
                        if not self._check_evasion():
                            self.player_hit_flash = 3
                            self.damage_numbers.append(DamageNumber(
                                self.player_ship.x + self.player_ship.width // 2,
                                self.player_ship.y, beam.damage_per_frame, (255, 80, 80)))
                            if self.player_ship.take_damage(beam.damage_per_frame):
                                self.game_over = True
                                self.winner = "ai"
                                self._save_score()
                                self.explosions.append(Explosion(
                                    self.player_ship.x + self.player_ship.width // 2,
                                    self.player_ship.y, tier="large"))

        # Ship collision with asteroids
        for asteroid in self.asteroids[:]:
            if not asteroid.active:
                continue
            if not self.wormhole_active and asteroid.get_rect().colliderect(self.player_ship.get_rect()):
                self.player_hit_flash = 5
                self.player_ship.take_damage(25, is_asteroid=True)
                self.explosions.append(Explosion(asteroid.x, asteroid.y, tier="small"))
                asteroid.active = False
                self.screen_shake.trigger(3, 5)
                continue
            for ai_ship in self.ai_ships:
                if asteroid.get_rect().colliderect(ai_ship.get_rect()):
                    ai_ship.hit_flash = 5
                    ai_ship.take_damage(25, is_asteroid=True)
                    self.explosions.append(Explosion(asteroid.x, asteroid.y, tier="small"))
                    asteroid.active = False
                    break

        # Remove dead asteroids
        self.asteroids = [a for a in self.asteroids if a.active]

        # Contact damage: enemy ships touching the player
        if not self.wormhole_active and not self.game_over:
            player_rect = self.player_ship.get_rect()
            for ai_ship in self.ai_ships[:]:
                if ai_ship.contact_damage_cooldown > 0:
                    continue
                if ai_ship.get_rect().colliderect(player_rect):
                    if self._check_evasion():
                        ai_ship.contact_damage_cooldown = 30
                        continue

                    contact_dmg = 25 if getattr(ai_ship, 'is_boss', False) else 10
                    self.player_hit_flash = 5
                    self.screen_shake.trigger(5, 8)
                    self.damage_numbers.append(DamageNumber(
                        self.player_ship.x + self.player_ship.width // 2,
                        self.player_ship.y, contact_dmg, (255, 80, 80)))
                    if self.player_ship.take_damage(contact_dmg):
                        self.game_over = True
                        self.winner = "ai"
                        self._save_score()
                        self.explosions.append(Explosion(
                            self.player_ship.x + self.player_ship.width // 2,
                            self.player_ship.y, tier="large"))
                    ai_ship.hit_flash = 3
                    if ai_ship.take_damage(5):
                        self._on_enemy_killed(ai_ship)
                    ai_ship.contact_damage_cooldown = 30

        # Update XP orbs
        collection_radius = (30 + self.upgrades.get("tractor_beam", 0) * 15
                             + self.upgrades.get("magnet_field", 0) * 40)
        player_cx = self.player_ship.x + self.player_ship.width // 2
        player_cy = self.player_ship.y
        for orb in self.xp_orbs[:]:
            xp_gained = orb.update(player_cx, player_cy, collection_radius)
            if xp_gained > 0:
                self._gain_xp(xp_gained)
        self.xp_orbs = [o for o in self.xp_orbs if o.active]

        # Trigger level-up screen
        if self.pending_level_ups > 0 and not self.showing_level_up:
            self._prepare_level_up_choices()
            self.showing_level_up = True

        # Update background (pass camera velocity for speed lines)
        self.starfield.update(self.camera.vx, self.camera.vy)

        # Update visual feedback
        if self.player_hit_flash > 0:
            self.player_hit_flash -= 1
        self.explosions = [e for e in self.explosions if e.update()]
        self.damage_numbers = [d for d in self.damage_numbers if d.update()]
        self.popup_notifications = [p for p in self.popup_notifications if p.update()]
        self.chain_lightning_effects = [c for c in self.chain_lightning_effects if c.active]
        for cl in self.chain_lightning_effects:
            cl.update()

        # Add time-based score (1 point per second survived)
        if self.survival_frames % 60 == 0:
            self.score += 10

    def draw(self, surface):
        """Draw the game."""
        time_tick = pygame.time.get_ticks()
        cam = self.camera

        # Apply screen shake
        shake_x, shake_y = self.screen_shake.update()

        # Create draw surface (offset by shake)
        if shake_x != 0 or shake_y != 0:
            if not hasattr(self, '_shake_surface') or self._shake_surface.get_size() != (self.screen_width, self.screen_height):
                self._shake_surface = pygame.Surface((self.screen_width, self.screen_height))
            draw_surface = self._shake_surface
        else:
            draw_surface = surface

        # Background
        draw_surface.fill((5, 5, 20))
        self.starfield.draw(draw_surface, camera=cam)

        # Draw asteroids (culled)
        for asteroid in self.asteroids:
            if cam.is_visible(asteroid.x, asteroid.y, margin=asteroid.size + 50):
                asteroid.draw(draw_surface, camera=cam)

        # Draw gravity wells
        for gw in self.gravity_wells:
            if cam.is_visible(gw.x, gw.y, margin=gw.radius + 20):
                gw.draw(draw_surface, camera=cam)

        # Draw XP orbs (culled)
        for orb in self.xp_orbs:
            if cam.is_visible(orb.x, orb.y, margin=20):
                orb.draw(draw_surface, camera=cam)

        # Draw power-ups
        for powerup in self.powerups:
            if cam.is_visible(powerup.x, powerup.y, margin=50):
                powerup.draw(draw_surface, camera=cam)

        # Draw suns/wormhole hazards
        for sun in self.suns:
            if cam.is_visible(sun.x, sun.y, margin=sun.max_radius + 100):
                sun.draw(draw_surface, camera=cam)

        # Draw area bombs (from Al'kesh bombers)
        for bomb in self.area_bombs:
            if cam.is_visible(bomb.x, bomb.y, margin=bomb.blast_radius):
                bomb.draw(draw_surface, camera=cam)

        # Draw proximity mines
        for mine in self.mines:
            if cam.is_visible(mine.x, mine.y, margin=50):
                mine.draw(draw_surface, camera=cam)

        # Draw ion pulse effects
        for pulse in self.ion_pulse_effects:
            if cam.is_visible(pulse['x'], pulse['y'], margin=pulse['max_radius']):
                sx, sy = cam.world_to_screen(pulse['x'], pulse['y'])
                progress = pulse['timer'] / pulse['duration']
                r = pulse['radius']
                alpha = int(180 * (1 - progress))
                if r > 0:
                    pulse_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                    c = r + 2
                    pygame.draw.circle(pulse_surf, (*pulse['color'][:3], alpha // 3), (c, c), r)
                    pygame.draw.circle(pulse_surf, (*pulse['color'][:3], alpha), (c, c), r, 3)
                    pygame.draw.circle(pulse_surf, (255, 255, 255, alpha // 2), (c, c), max(1, r - 5), 2)
                    draw_surface.blit(pulse_surf, (int(sx) - c, int(sy) - c))

        # Draw projectiles (culled)
        for proj in self.projectiles:
            if cam.is_visible(proj.x, proj.y, margin=50):
                proj.draw(draw_surface, camera=cam)

        # Draw chain lightning effects
        for cl in self.chain_lightning_effects:
            cl.draw(draw_surface, camera=cam)

        # Draw beam weapons if active
        if self.player_ship.current_beam:
            self.player_ship.current_beam.draw(draw_surface, camera=cam)
        for ai_ship in self.ai_ships:
            if ai_ship.current_beam:
                ai_ship.current_beam.draw(draw_surface, camera=cam)

        # Draw orbital laser strike visuals
        for strike in self.orbital_laser_effects:
            if cam.is_visible(strike['x'], strike['y'], margin=100):
                sx, sy = cam.world_to_screen(strike['x'], strike['y'])
                progress = strike['timer'] / strike['duration']
                alpha = int(255 * (1 - progress))
                # Beam from top of screen to target
                beam_w = int(20 * (1 - progress))
                beam_h = max(1, int(sy) + 10)
                if beam_w > 0 and beam_h > 0:
                    beam_surf = pygame.Surface((beam_w * 2, beam_h), pygame.SRCALPHA)
                    pygame.draw.rect(beam_surf, (0, 200, 255, alpha),
                                     (0, 0, beam_w * 2, beam_h))
                    pygame.draw.rect(beam_surf, (200, 240, 255, alpha // 2),
                                     (beam_w // 2, 0, beam_w, beam_h))
                    draw_surface.blit(beam_surf, (int(sx) - beam_w, 0))

        # Draw dash afterimages
        for ai_data in self.dash_afterimages:
            if self.player_ship.image:
                ghost = self.player_ship.image.copy()
                ghost.set_alpha(ai_data['alpha'])
                gx, gy = cam.world_to_screen(ai_data['x'], ai_data['y'])
                draw_surface.blit(ghost, (int(gx), int(gy - self.player_ship.height // 2)))

        # Draw player ship
        if not self.game_over or self.winner != "ai":
            if self.wormhole_active:
                pass
            elif self.player_hit_flash > 0:
                self.player_ship.draw(draw_surface, time_tick, camera=cam)
                sx, sy = cam.world_to_screen(self.player_ship.x, self.player_ship.y)
                ship_rect = pygame.Rect(int(sx), int(sy - self.player_ship.height // 2),
                                        self.player_ship.width, self.player_ship.height)
                flash_surf = pygame.Surface((ship_rect.width, ship_rect.height), pygame.SRCALPHA)
                flash_surf.fill((255, 0, 0, 80))
                draw_surface.blit(flash_surf, ship_rect.topleft)
            else:
                if self.is_cloaked():
                    if self.player_ship.image:
                        ghost = self.player_ship.image.copy()
                        ghost.set_alpha(100)
                        sx, sy = cam.world_to_screen(self.player_ship.x, self.player_ship.y)
                        draw_surface.blit(ghost, (int(sx),
                                                  int(sy - self.player_ship.height // 2)))
                    else:
                        self.player_ship.draw(draw_surface, time_tick, camera=cam)
                else:
                    self.player_ship.draw(draw_surface, time_tick, camera=cam)

        # Draw wormhole vortex effects
        for effect in self.wormhole_effects:
            effect.draw(draw_surface, camera=cam)

        # Draw drones
        for drone in self.drones:
            drone.draw(draw_surface, camera=cam)
        for drone in self.upgrade_drones:
            drone.draw(draw_surface, camera=cam)

        # Draw ally ships with "ALLY" label
        for ally in self.ally_ships:
            if cam.is_visible(ally.x, ally.y, margin=ally.width):
                ally.draw(draw_surface, time_tick, camera=cam)
                ax, ay = cam.world_to_screen(ally.x + ally.width // 2, ally.y)
                ally_label = self.tiny_font.render("ALLY", True, (100, 255, 100))
                draw_surface.blit(ally_label,
                                 (int(ax) - ally_label.get_width() // 2,
                                  int(ay) - ally.height // 2 - 22))

        # Draw all AI ships (culled)
        for ai_ship in self.ai_ships:
            if cam.is_visible(ai_ship.x, ai_ship.y, margin=ai_ship.width):
                ai_ship.draw(draw_surface, time_tick, camera=cam)
                hit_flash = getattr(ai_ship, 'hit_flash', 0)
                if hit_flash > 0:
                    sx, sy = cam.world_to_screen(ai_ship.x, ai_ship.y)
                    ship_rect = pygame.Rect(int(sx), int(sy - ai_ship.height // 2),
                                            ai_ship.width, ai_ship.height)
                    flash_surf = pygame.Surface((ship_rect.width, ship_rect.height), pygame.SRCALPHA)
                    flash_surf.fill((255, 0, 0, 80))
                    draw_surface.blit(flash_surf, ship_rect.topleft)
                    ai_ship.hit_flash = hit_flash - 1

        # Draw explosions
        for explosion in self.explosions:
            explosion.draw(draw_surface, camera=cam)

        # Draw damage numbers
        for dn in self.damage_numbers:
            dn.draw(draw_surface, camera=cam)

        # Draw popup notifications
        for pn in self.popup_notifications:
            pn.draw(draw_surface, camera=cam)

        # Draw UI (screen-space, no camera)
        _ui.draw_ui(self, draw_surface)

        # Draw level-up screen on top
        if self.showing_level_up and self.level_up_choices:
            _ui.draw_level_up_screen(self, draw_surface)

        # Blit with shake offset
        if shake_x != 0 or shake_y != 0:
            surface.blit(draw_surface, (shake_x, shake_y))
