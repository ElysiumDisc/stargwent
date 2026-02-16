"""Main SpaceShooterGame class — game loop, update, draw, collision."""

import pygame
import math
import random

from .projectiles import Projectile, Laser, ContinuousBeam, EnergyBall, ChainLightning
from .entities import (
    Asteroid, PowerUp, Drone, XPOrb, WormholeEffect, Explosion,
    DamageNumber, PopupNotification, GravityWell,
)
from .effects import StarField, ScreenShake
from .ship import Ship
from .upgrades import UPGRADES, ENEMY_TYPES
from . import ui as _ui


class SpaceShooterGame:
    """Main space shooter mini-game with waves of enemies."""

    # Scoring constants
    SCORE_ENEMY = 100
    SCORE_BOSS = 1000
    SCORE_WAVE_CLEAR = 500
    SCORE_NO_DAMAGE = 200
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

        # Wave system
        self.current_wave = 1
        self.max_waves = 20
        self.wave_complete = False
        self.wave_transition_timer = 0
        self.enemies_defeated = 0
        self.next_spawn_positions = []  # For enemy warning indicators

        # Scoring system
        self.score = 0
        self.wave_damage_taken = False
        self.asteroids_destroyed = 0

        # Kill streak
        self.kill_streak = 0
        self.kill_streak_timer = 0  # Frames since last kill (resets streak after 180 = 3s)

        # Power-up system
        self.powerups = []
        self.powerup_spawn_timer = 0
        self.powerup_spawn_rate = 200
        self.active_powerups = {}
        self.drones = []
        self.base_fire_rate = None
        self.base_damage_mult = 1.0

        # XP and Level-up system
        self.xp = 0
        self.level = 1
        self.xp_to_next = 80
        self.upgrades = {}
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
        self.wormhole_transit_duration = 30
        self.wormhole_effects = []
        self.wormhole_exit_x = 0
        self.wormhole_exit_y = 0

        # Shield bash (dash) state
        self.dash_active = False
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_afterimages = []  # List of (x, y, alpha) for afterimage trail

        # Gravity well state
        self.gravity_wells = []
        self.gravity_well_timer = 0

        # Chain lightning visual effects
        self.chain_lightning_effects = []

        # Visual feedback
        self.damage_numbers = []
        self.popup_notifications = []
        self.screen_shake = ScreenShake()

        # All faction options for variety
        self.all_factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]

        # Create player ship
        self.player_ship = Ship(
            100, screen_height // 2,
            player_faction, is_player=True,
            screen_width=screen_width, screen_height=screen_height
        )

        # Track player velocity for parallax
        self.prev_player_x = self.player_ship.x
        self.prev_player_y = self.player_ship.y

        # Create enemy ships
        self.ai_ships = []
        self.spawn_wave_enemies()

        # Projectiles and effects
        self.projectiles = []
        self.explosions = []
        self.asteroids = []
        self.starfield = StarField(screen_width, screen_height)

        # Asteroid spawning
        self.asteroid_spawn_timer = 0
        self.asteroid_spawn_rate = 600

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

    def _get_wave_enemy_types(self):
        """Determine which enemy types to spawn based on current wave."""
        wave = self.current_wave
        types = ["regular"]
        weights = [60]
        if wave >= 4:
            types.append("fast")
            weights.append(25)
        if wave >= 6:
            types.append("kamikaze")
            weights.append(15)
        if wave >= 8:
            types.append("tank")
            weights.append(20)
        if wave >= 13:
            types.append("elite")
            weights.append(15)
        return types, weights

    def _get_formation(self, num_enemies):
        """Generate formation spawn positions. Returns list of (x, y) or None for scattered."""
        if self.current_wave < 8 or random.random() > 0.5:
            return None  # Scattered spawn

        formation = random.choice(["v", "line", "pincer"])
        positions = []
        margin = 80

        if formation == "v":
            edge = random.choice(["left", "right", "top", "bottom"])
            count = min(num_enemies, 5)
            if edge == "right":
                base_x = self.screen_width + margin
                base_y = self.screen_height // 2
                for i in range(count):
                    offset = (i - count // 2)
                    positions.append((base_x + abs(offset) * 40, base_y + offset * 60))
            elif edge == "left":
                base_x = -margin
                base_y = self.screen_height // 2
                for i in range(count):
                    offset = (i - count // 2)
                    positions.append((base_x - abs(offset) * 40, base_y + offset * 60))
            elif edge == "top":
                base_x = self.screen_width // 2
                base_y = -margin
                for i in range(count):
                    offset = (i - count // 2)
                    positions.append((base_x + offset * 60, base_y - abs(offset) * 40))
            else:
                base_x = self.screen_width // 2
                base_y = self.screen_height + margin
                for i in range(count):
                    offset = (i - count // 2)
                    positions.append((base_x + offset * 60, base_y + abs(offset) * 40))

        elif formation == "line":
            edge = random.choice(["left", "right", "top", "bottom"])
            count = min(num_enemies, 5)
            if edge in ("left", "right"):
                base_x = -margin if edge == "left" else self.screen_width + margin
                spacing = self.screen_height // (count + 1)
                for i in range(count):
                    positions.append((base_x, spacing * (i + 1)))
            else:
                base_y = -margin if edge == "top" else self.screen_height + margin
                spacing = self.screen_width // (count + 1)
                for i in range(count):
                    positions.append((spacing * (i + 1), base_y))

        elif formation == "pincer":
            count = min(num_enemies, 6)
            half = count // 2
            # Group 1 from left
            for i in range(half):
                positions.append((-margin, self.screen_height // 3 + i * 80))
            # Group 2 from right
            for i in range(count - half):
                positions.append((self.screen_width + margin, self.screen_height * 2 // 3 - i * 80))

        # Pad remaining enemies with scattered positions
        while len(positions) < num_enemies:
            edge = random.choice(["top", "bottom", "left", "right"])
            if edge == "top":
                positions.append((random.randint(0, self.screen_width), -margin))
            elif edge == "bottom":
                positions.append((random.randint(0, self.screen_width), self.screen_height + margin))
            elif edge == "left":
                positions.append((-margin, random.randint(0, self.screen_height)))
            else:
                positions.append((self.screen_width + margin, random.randint(0, self.screen_height)))

        return positions

    def spawn_wave_enemies(self):
        """Spawn enemies for the current wave with scaling difficulty."""
        self.ai_ships = []
        wave = self.current_wave

        is_boss_wave = wave in (5, 10, 15, 20)

        power = (wave * 0.6 + self.level * 0.4)
        num_enemies = max(1, int(1 + power * 0.8))

        if is_boss_wave:
            num_enemies = max(1, num_enemies // 2)

        hp_mult = 1.0 + (power - 1) * 0.10
        speed_mult = 1.0 + (power - 1) * 0.008
        fire_rate_mult = max(0.5, 1.0 - (power - 1) * 0.02)

        types, weights = self._get_wave_enemy_types()

        # Try formation spawn
        formation_positions = self._get_formation(num_enemies)

        # Pre-calculate spawn positions for enemy warning indicators
        self.next_spawn_positions = []

        for i in range(num_enemies):
            enemy_faction = random.choice([f for f in self.all_factions if f != self.player_faction])
            enemy_type = random.choices(types, weights=weights)[0]
            mods = ENEMY_TYPES[enemy_type]

            if formation_positions and i < len(formation_positions):
                sx, sy = formation_positions[i]
            else:
                edge = random.choice(["top", "bottom", "left", "right"])
                margin = 60
                if edge == "top":
                    sx = random.randint(0, self.screen_width)
                    sy = -margin
                elif edge == "bottom":
                    sx = random.randint(0, self.screen_width)
                    sy = self.screen_height + margin
                elif edge == "left":
                    sx = -margin
                    sy = random.randint(0, self.screen_height)
                else:
                    sx = self.screen_width + margin
                    sy = random.randint(0, self.screen_height)

            self.next_spawn_positions.append((sx, sy))

            ship = Ship(
                sx, sy,
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

            # Apply tint
            if mods["tint"] and ship.image:
                tint_surf = pygame.Surface(ship.image.get_size(), pygame.SRCALPHA)
                tint_surf.fill((*mods["tint"], 60))
                ship.image.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # Re-cache 4-dir images after scale/tint changes
            if ship.image:
                ship.image_right = ship.image.copy()
                ship.image_left = pygame.transform.flip(ship.image, True, False)
                ship.image_up = pygame.transform.rotate(ship.image_right, 90)
                ship.image_down = pygame.transform.rotate(ship.image_right, -90)

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
        edge = random.choice(["top", "bottom", "left", "right"])
        margin = 80
        if edge == "top":
            bx = random.randint(margin, self.screen_width - margin)
            by = -margin
        elif edge == "bottom":
            bx = random.randint(margin, self.screen_width - margin)
            by = self.screen_height + margin
        elif edge == "left":
            bx = -margin
            by = random.randint(margin, self.screen_height - margin)
        else:
            bx = self.screen_width + margin
            by = random.randint(margin, self.screen_height - margin)
        boss = Ship(
            bx, by,
            boss_faction, is_player=False,
            screen_width=self.screen_width, screen_height=self.screen_height
        )

        boss_hp_table = {5: 2.0, 10: 4.0, 15: 7.0, 20: 15.0}
        hp_scale = boss_hp_table.get(wave, 3.0)
        boss.max_health = int(100 * hp_scale)
        boss.health = boss.max_health
        boss.max_shields = int(100 * hp_scale * 0.5)
        boss.shields = boss.max_shields

        scale = 1.3 if wave < 20 else 1.6
        if boss.image:
            new_w = int(boss.width * scale)
            new_h = int(boss.height * scale)
            boss.image = pygame.transform.smoothscale(boss.image, (new_w, new_h))
            boss.width = new_w
            boss.height = new_h

        if boss.image:
            tint = pygame.Surface(boss.image.get_size(), pygame.SRCALPHA)
            tint.fill((255, 50, 50, 40))
            boss.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if boss.image:
            boss.image_right = boss.image.copy()
            boss.image_left = pygame.transform.flip(boss.image, True, False)
            boss.image_up = pygame.transform.rotate(boss.image_right, 90)
            boss.image_down = pygame.transform.rotate(boss.image_right, -90)

        boss.fire_rate = max(10, boss.fire_rate // 2)
        boss.xp_value = 200
        boss.enemy_type = "boss"
        boss.is_boss = True
        boss.ai_fire_timer = 0

        if wave == 20:
            boss.xp_value = 500

        self.ai_ships.append(boss)

        # Boss escorts (2-3 elite ships that orbit the boss)
        num_escorts = random.randint(2, 3)
        for i in range(num_escorts):
            escort_faction = random.choice([f for f in self.all_factions if f != self.player_faction])
            angle = i * (2 * math.pi / num_escorts)
            escort = Ship(
                bx + math.cos(angle) * 100, by + math.sin(angle) * 100,
                escort_faction, is_player=False,
                screen_width=self.screen_width, screen_height=self.screen_height
            )
            escort_mods = ENEMY_TYPES["elite"]
            escort.max_health = int(escort.max_health * escort_mods["hp"])
            escort.health = escort.max_health
            escort.speed = int(escort.speed * escort_mods["speed"])
            if escort_mods["tint"] and escort.image:
                tint_surf = pygame.Surface(escort.image.get_size(), pygame.SRCALPHA)
                tint_surf.fill((*escort_mods["tint"], 60))
                escort.image.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            if escort.image:
                escort.image_right = escort.image.copy()
                escort.image_left = pygame.transform.flip(escort.image, True, False)
                escort.image_up = pygame.transform.rotate(escort.image_right, 90)
                escort.image_down = pygame.transform.rotate(escort.image_right, -90)
            escort.xp_value = escort_mods["xp"]
            escort.enemy_type = "elite"
            escort.ai_fire_timer = random.randint(0, 60)
            self.ai_ships.append(escort)

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
            elif event.key == pygame.K_r and self.game_over:
                self.__init__(self.screen_width, self.screen_height,
                            self.player_faction, self.ai_faction,
                            session_scores=self.session_scores)
            elif event.key in (pygame.K_w, pygame.K_UP) and not self.game_over:
                self.player_ship.set_facing((0, -1))
            elif event.key in (pygame.K_s, pygame.K_DOWN) and not self.game_over:
                self.player_ship.set_facing((0, 1))
            elif event.key in (pygame.K_a, pygame.K_LEFT) and not self.game_over:
                self.player_ship.set_facing((-1, 0))
            elif event.key in (pygame.K_d, pygame.K_RIGHT) and not self.game_over:
                self.player_ship.set_facing((1, 0))

    def _activate_wormhole(self):
        """Activate the wormhole escape."""
        self.wormhole_active = True
        self.wormhole_transit_timer = 0

        entry_x = self.player_ship.x + self.player_ship.width // 2
        entry_y = self.player_ship.y
        self.wormhole_effects.append(WormholeEffect(entry_x, entry_y, is_entry=True))

        margin = 100
        self.wormhole_exit_x = random.randint(margin, self.screen_width - margin)
        self.wormhole_exit_y = random.randint(margin, self.screen_height - margin)

    def _save_score(self):
        """Save the score to the per-session leaderboard."""
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
            # Use multiplier: halve fire rate, restore by doubling on expiry
            self.player_ship.fire_rate = max(5, self.player_ship.fire_rate // 2)
            self.active_powerups["rapid_fire"] = duration
        elif ptype == "drone":
            self.drones = []
            for i in range(3):
                angle = (i * 2 * math.pi / 3)
                self.drones.append(Drone(self.player_ship, angle))
            self.active_powerups["drone"] = duration
        elif ptype == "damage":
            # Intentionally does not stack: picking up another refreshes the timer
            self.base_damage_mult = 1.25
            self.active_powerups["damage"] = duration
        elif ptype == "cloak":
            self.active_powerups["cloak"] = duration

    def _expire_powerup(self, ptype):
        """Handle expiration of a power-up effect."""
        if ptype == "rapid_fire":
            # Reverse the halving by doubling (preserves upgrades taken during power-up)
            self.player_ship.fire_rate = min(self.player_ship.fire_rate * 2, 60)
        elif ptype == "drone":
            self.drones = []
        elif ptype == "damage":
            self.base_damage_mult = 1.0

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

        # Kill streak
        self.kill_streak += 1
        self.kill_streak_timer = 0
        # Streak bonus score
        if self.kill_streak >= 3:
            self.score += self.kill_streak * 25

        # Screen shake on kill
        if getattr(ai_ship, 'is_boss', False):
            self.screen_shake.trigger(8, 15)
        else:
            self.screen_shake.trigger(2, 3)

        # Jaffa Warrior's Fury passive
        if self.player_ship.passive == "warriors_fury":
            self.player_ship.passive_state["kills"] = self.player_ship.passive_state.get("kills", 0) + 1

        # Spawn XP orb
        xp_value = getattr(ai_ship, 'xp_value', 20)
        self.xp_orbs.append(XPOrb(ai_ship.x + ai_ship.width // 2, ai_ship.y, xp_value))

        # Score
        if getattr(ai_ship, 'is_boss', False):
            self.score += self.SCORE_BOSS
        else:
            self.score += self.SCORE_ENEMY

        # Check wave complete
        if len(self.ai_ships) == 0:
            self.wave_complete = True
            self.score += self.SCORE_WAVE_CLEAR
            if not self.wave_damage_taken:
                self.score += self.SCORE_NO_DAMAGE
            self.wave_damage_taken = False

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
        available = [
            name for name, info in UPGRADES.items()
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
                if ai_ship.take_damage(splash_damage):
                    killed_set.add(ai_ship)
                    self._on_enemy_killed(ai_ship)

    def _try_chain_lightning(self, hit_x, hit_y, damage, hit_enemy):
        """Try to chain lightning from a hit enemy to nearby enemies."""
        cl_stacks = self.upgrades.get("chain_lightning", 0)
        if cl_stacks <= 0:
            return

        max_chains = cl_stacks
        chain_range = 150
        chain_targets = []
        hit_set = {id(hit_enemy)} if hit_enemy else set()

        current_x, current_y = hit_x, hit_y
        chain_damage = damage * 0.6

        for _ in range(max_chains):
            # Find nearest un-hit enemy within range
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

            # Deal damage
            best.hit_flash = 5
            self.damage_numbers.append(DamageNumber(target_x, target_y, chain_damage, (100, 150, 255)))
            if best.take_damage(chain_damage):
                self._on_enemy_killed(best)

            current_x, current_y = target_x, target_y

        # Spawn visual effect
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

    def update(self):
        """Update game state."""
        if self.showing_level_up:
            return

        # Kill streak timer
        if self.kill_streak > 0:
            self.kill_streak_timer += 1
            if self.kill_streak_timer >= 180:  # 3 seconds
                self.kill_streak = 0
                self.kill_streak_timer = 0

        # Handle wave transition
        if self.wave_complete:
            self.wave_transition_timer += 1
            if self.wave_transition_timer >= 180:
                self.current_wave += 1
                if self.current_wave > self.max_waves:
                    self.game_over = True
                    self.winner = "player"
                    self._save_score()
                else:
                    self.spawn_wave_enemies()
                    self.wave_complete = False
                    self.wave_transition_timer = 0
            # Update during transition
            self.explosions = [e for e in self.explosions if e.update()]
            self.damage_numbers = [d for d in self.damage_numbers if d.update()]
            self.popup_notifications = [p for p in self.popup_notifications if p.update()]
            collection_radius = (30 + self.upgrades.get("tractor_beam", 0) * 15
                                 + self.upgrades.get("magnet_field", 0) * 40)
            player_cx = self.player_ship.x + self.player_ship.width // 2
            player_cy = self.player_ship.y
            for orb in self.xp_orbs[:]:
                xp_gained = orb.update(player_cx, player_cy, collection_radius)
                if xp_gained > 0:
                    self._gain_xp(xp_gained)
                if not orb.active:
                    self.xp_orbs.remove(orb)
            # Compute player velocity for parallax
            player_vx = self.player_ship.x - self.prev_player_x
            player_vy = self.player_ship.y - self.prev_player_y
            self.prev_player_x = self.player_ship.x
            self.prev_player_y = self.player_ship.y
            self.starfield.update(player_vx, player_vy)
            return

        if self.game_over:
            self.explosions = [e for e in self.explosions if e.update()]
            self.damage_numbers = [d for d in self.damage_numbers if d.update()]
            return

        keys = pygame.key.get_pressed()

        # Update player ship
        if not self.wormhole_active:
            self.player_ship.update(keys)

        # Compute player velocity for parallax
        player_vx = self.player_ship.x - self.prev_player_x
        player_vy = self.player_ship.y - self.prev_player_y
        self.prev_player_x = self.player_ship.x
        self.prev_player_y = self.player_ship.y

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

            if self.wormhole_transit_timer >= self.wormhole_transit_duration:
                self.wormhole_active = False
                self.wormhole_cooldown = self.wormhole_max_cooldown

        self.wormhole_effects = [e for e in self.wormhole_effects if e.update()]

        # Shield Bash (dash) logic
        bash_stacks = self.upgrades.get("shield_bash", 0)
        if bash_stacks > 0:
            if self.dash_cooldown > 0:
                self.dash_cooldown -= 1

            player_moving = (abs(player_vx) > 2 or abs(player_vy) > 2)

            if player_moving and not self.dash_active and self.dash_cooldown <= 0:
                self.dash_active = True
                self.dash_timer = 30  # 0.5s
                self.dash_afterimages = []

            if self.dash_active:
                self.dash_timer -= 1
                # Afterimage trail
                if self.dash_timer % 3 == 0:
                    self.dash_afterimages.append({
                        'x': self.player_ship.x,
                        'y': self.player_ship.y,
                        'alpha': 150,
                    })

                # Contact damage during dash
                player_rect = self.player_ship.get_rect()
                dash_damage = 30 + bash_stacks * 10
                for ai_ship in self.ai_ships[:]:
                    if ai_ship.get_rect().colliderect(player_rect):
                        ai_ship.hit_flash = 5
                        self.damage_numbers.append(DamageNumber(
                            ai_ship.x + ai_ship.width // 2, ai_ship.y,
                            dash_damage, (255, 200, 50)))
                        if ai_ship.take_damage(dash_damage):
                            self._on_enemy_killed(ai_ship)

                if self.dash_timer <= 0:
                    self.dash_active = False
                    self.dash_cooldown = 180  # 3s

            # Update afterimages
            for ai in self.dash_afterimages[:]:
                ai['alpha'] -= 10
                if ai['alpha'] <= 0:
                    self.dash_afterimages.remove(ai)

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
            if self.gravity_well_timer >= 600 and self.ai_ships:  # 10s
                self.gravity_well_timer = 0
                # Deploy at centroid of visible enemies
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

        # Orbital Defense drones
        for drone in self.upgrade_drones:
            proj = drone.update(self.ai_ships)
            if proj:
                self.projectiles.append(proj)

        # Update all AI ships
        for ai_ship in self.ai_ships:
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
                            ai_ship.ai_fire_timer = random.randint(5, 15)
                            for offset in [-40, 40]:
                                extra = ai_ship.fire()
                                if extra is None:
                                    fire_x = ai_ship.x
                                    extra = Laser(fire_x, ai_ship.y + offset,
                                                  ai_ship.facing,
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
                        base_min = max(30, 80 - self.current_wave * 3)
                        base_max = max(60, 140 - self.current_wave * 4)
                        ai_ship.ai_fire_timer = random.randint(base_min, base_max)

        # Player auto-fire
        if not self.game_over:
            berserker_mult = self._get_berserker_mult()
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
                    base_dmg = projectile.damage * self.base_damage_mult * wp_mult * berserker_mult
                    base_dmg, is_crit = self._apply_critical(base_dmg)
                    projectile.damage = int(base_dmg)
                    projectile._is_crit = is_crit
                    self.projectiles.append(projectile)

                    # Multi-Targeting: fires extra projectiles in all directions
                    mt_stacks = self.upgrades.get("multi_targeting", 0)
                    if mt_stacks > 0 and not isinstance(projectile, ContinuousBeam):
                        fdx, fdy = self.player_ship.facing
                        ship = self.player_ship
                        cx = ship.x + ship.width // 2
                        cy = ship.y

                        # Build list of extra fire directions
                        extra_dirs = []
                        # Forward spread shots (always)
                        for i in range(1, min(mt_stacks + 1, 4)):
                            for angle_sign in [1, -1]:
                                extra_dirs.append(('spread', angle_sign * i * 8))

                        # Perpendicular shots at 2+ stacks
                        if mt_stacks >= 2:
                            if abs(fdx) > 0:
                                extra_dirs.append(('dir', (0, -1)))  # Up
                                extra_dirs.append(('dir', (0, 1)))   # Down
                            else:
                                extra_dirs.append(('dir', (-1, 0)))  # Left
                                extra_dirs.append(('dir', (1, 0)))   # Right

                        # Rear shots at 3+ stacks
                        if mt_stacks >= 3:
                            extra_dirs.append(('dir', (-fdx, -fdy)))

                        # Diagonal shots at 4+ stacks
                        if mt_stacks >= 4:
                            for ddx in [-1, 1]:
                                for ddy in [-1, 1]:
                                    if (ddx, ddy) != (fdx, fdy):
                                        extra_dirs.append(('dir', (ddx, ddy)))

                        for entry in extra_dirs:
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
                                extra = type(projectile)(fx, fy, d,
                                                         ship.laser_color)
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
                                extra = type(projectile)(cx, cy, d,
                                                         ship.laser_color)
                                extra.is_player_proj = True
                                extra_dmg = extra.damage * self.base_damage_mult * wp_mult * berserker_mult * 0.7
                                extra_dmg, _ = self._apply_critical(extra_dmg)
                                extra.damage = int(extra_dmg)
                                self.projectiles.append(extra)

                    # Scatter Shot
                    scatter_stacks = self.upgrades.get("scatter_shot", 0)
                    if scatter_stacks > 0:
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
                            # Apply spread perpendicular to facing
                            offset = math.tan(math.radians(spread_angle)) * 40
                            if abs(fdx) > 0:
                                pellet.y += offset
                            else:
                                pellet.x += offset
                            # Reduce pellet size
                            pellet.width = max(2, pellet.width // 2)
                            pellet.height = max(2, pellet.height // 2)
                            self.projectiles.append(pellet)

        # Spawn asteroids
        effective_asteroid_rate = max(200, 600 - self.current_wave * 20)
        self.asteroid_spawn_timer += 1
        if self.asteroid_spawn_timer >= effective_asteroid_rate:
            self.asteroid_spawn_timer = 0
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
            if random.random() < 0.75:
                self.powerups.append(PowerUp.spawn_random(self.screen_width, self.screen_height))

        # Update power-ups
        for powerup in self.powerups[:]:
            powerup.update()
            if not powerup.active:
                self.powerups.remove(powerup)
                continue
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

            # Targeting Computer homing
            if tc_stacks > 0 and proj.is_player_proj and self.ai_ships:
                nearest = min(self.ai_ships,
                              key=lambda e: math.hypot(e.x - proj.x, e.y - proj.y))
                max_adjust = tc_stacks * 2.0
                pdx, pdy = proj.direction
                if abs(pdx) > abs(pdy):
                    diff = nearest.y - proj.y
                    if abs(diff) > 1:
                        proj.y += max(-max_adjust, min(max_adjust, diff * 0.05))
                else:
                    diff = nearest.x - proj.x
                    if abs(diff) > 1:
                        proj.x += max(-max_adjust, min(max_adjust, diff * 0.05))

            if proj.x < -100 or proj.x > self.screen_width + 100 or proj.y < -100 or proj.y > self.screen_height + 100:
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                continue

            proj_rect = proj.get_rect()

            if proj.is_player_proj:
                for ai_ship in self.ai_ships[:]:
                    if proj_rect.colliderect(ai_ship.get_rect()):
                        if proj in self.projectiles:
                            self.projectiles.remove(proj)
                        ai_ship.hit_flash = 10
                        hit_x = ai_ship.x + ai_ship.width // 2
                        hit_y = ai_ship.y

                        # Damage number
                        is_crit = getattr(proj, '_is_crit', False)
                        dmg_color = (255, 255, 0) if is_crit else (255, 255, 255)
                        self.damage_numbers.append(DamageNumber(hit_x, hit_y, proj.damage, dmg_color))

                        _killed_this_hit = set()
                        if ai_ship.take_damage(proj.damage):
                            _killed_this_hit.add(ai_ship)
                            self._on_enemy_killed(ai_ship)

                        # Chain lightning
                        self._try_chain_lightning(hit_x, hit_y, proj.damage, ai_ship)

                        # Lucian Alliance splash damage
                        if self.player_ship.passive == "splash_damage" and isinstance(proj, EnergyBall):
                            self._apply_splash_damage(hit_x, hit_y, proj.damage, self.player_ship, already_killed=_killed_this_hit)
                        break
            else:
                if not self.wormhole_active and proj_rect.colliderect(self.player_ship.get_rect()):
                    # Evasion check
                    if self._check_evasion():
                        if proj in self.projectiles:
                            self.projectiles.remove(proj)
                        continue

                    if proj in self.projectiles:
                        self.projectiles.remove(proj)
                    self.player_hit_flash = 10
                    self.wave_damage_taken = True
                    self.screen_shake.trigger(5, 8)

                    # Damage number (red for player damage)
                    self.damage_numbers.append(DamageNumber(
                        self.player_ship.x + self.player_ship.width // 2,
                        self.player_ship.y, proj.damage, (255, 80, 80)))

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
                        if proj.is_player_proj:
                            self.score += self.SCORE_ASTEROID
                            self.asteroids_destroyed += 1
                            self.xp_orbs.append(XPOrb(asteroid.x, asteroid.y, 10))
                    break

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

            beam_end_dist = self.screen_width if is_horizontal else self.screen_height
            hit_first = False
            for dist, target, is_ast in targets:
                if not piercing and dist > beam_end_dist:
                    break
                dmg = beam.damage_per_frame * (0.5 if (piercing and hit_first) else 1.0)
                dmg *= self._get_berserker_mult()
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
                beam_dir = ai_ship.facing[0]

                closest_hit_dist = self.screen_width
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
                            self.explosions.append(Explosion(hit_target.x, hit_target.y))
                            if hit_target in self.asteroids:
                                self.asteroids.remove(hit_target)
                    else:
                        # Evasion check for beam
                        if not self._check_evasion():
                            self.player_hit_flash = 3
                            self.wave_damage_taken = True
                            self.damage_numbers.append(DamageNumber(
                                self.player_ship.x + self.player_ship.width // 2,
                                self.player_ship.y, beam.damage_per_frame, (255, 80, 80)))
                            if self.player_ship.take_damage(beam.damage_per_frame):
                                self.game_over = True
                                self.winner = "ai"
                                self._save_score()
                                self.explosions.append(Explosion(
                                    self.player_ship.x + self.player_ship.width // 2,
                                    self.player_ship.y))

        # Ship collision with asteroids
        for asteroid in self.asteroids[:]:
            if not self.wormhole_active and asteroid.get_rect().colliderect(self.player_ship.get_rect()):
                self.player_hit_flash = 5
                self.player_ship.take_damage(25, is_asteroid=True)
                self.explosions.append(Explosion(asteroid.x, asteroid.y))
                self.asteroids.remove(asteroid)
                self.screen_shake.trigger(3, 5)
                continue
            for ai_ship in self.ai_ships:
                if asteroid.get_rect().colliderect(ai_ship.get_rect()):
                    ai_ship.hit_flash = 5
                    ai_ship.take_damage(25, is_asteroid=True)
                    self.explosions.append(Explosion(asteroid.x, asteroid.y))
                    if asteroid in self.asteroids:
                        self.asteroids.remove(asteroid)
                    break

        # Contact damage: enemy ships touching the player
        if not self.wormhole_active and not self.game_over:
            player_rect = self.player_ship.get_rect()
            for ai_ship in self.ai_ships[:]:
                if ai_ship.contact_damage_cooldown > 0:
                    continue
                if ai_ship.get_rect().colliderect(player_rect):
                    # Evasion check
                    if self._check_evasion():
                        ai_ship.contact_damage_cooldown = 30
                        continue

                    contact_dmg = 25 if getattr(ai_ship, 'is_boss', False) else 10
                    self.player_hit_flash = 5
                    self.wave_damage_taken = True
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
                            self.player_ship.y))
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
            if not orb.active:
                self.xp_orbs.remove(orb)

        # Trigger level-up screen
        if self.pending_level_ups > 0 and not self.showing_level_up:
            self._prepare_level_up_choices()
            self.showing_level_up = True

        # Update background
        self.starfield.update(player_vx, player_vy)

        # Update visual feedback
        if self.player_hit_flash > 0:
            self.player_hit_flash -= 1
        self.explosions = [e for e in self.explosions if e.update()]
        self.damage_numbers = [d for d in self.damage_numbers if d.update()]
        self.popup_notifications = [p for p in self.popup_notifications if p.update()]
        self.chain_lightning_effects = [c for c in self.chain_lightning_effects if c.active]
        for cl in self.chain_lightning_effects:
            cl.update()

    def draw(self, surface):
        """Draw the game."""
        time_tick = pygame.time.get_ticks()

        # Apply screen shake
        shake_x, shake_y = self.screen_shake.update()

        # Create draw surface (offset by shake)
        if shake_x != 0 or shake_y != 0:
            draw_surface = pygame.Surface((self.screen_width, self.screen_height))
        else:
            draw_surface = surface

        # Background
        draw_surface.fill((5, 5, 20))
        self.starfield.draw(draw_surface)

        # Draw asteroids
        for asteroid in self.asteroids:
            asteroid.draw(draw_surface)

        # Draw gravity wells
        for gw in self.gravity_wells:
            gw.draw(draw_surface)

        # Draw XP orbs
        for orb in self.xp_orbs:
            orb.draw(draw_surface)

        # Draw power-ups
        for powerup in self.powerups:
            powerup.draw(draw_surface)

        # Draw projectiles
        for proj in self.projectiles:
            proj.draw(draw_surface)

        # Draw chain lightning effects
        for cl in self.chain_lightning_effects:
            cl.draw(draw_surface)

        # Draw beam weapons if active
        if self.player_ship.current_beam:
            self.player_ship.current_beam.draw(draw_surface)
        for ai_ship in self.ai_ships:
            if ai_ship.current_beam:
                ai_ship.current_beam.draw(draw_surface)

        # Draw dash afterimages
        for ai_data in self.dash_afterimages:
            if self.player_ship.image:
                ghost = self.player_ship.image.copy()
                ghost.set_alpha(ai_data['alpha'])
                draw_surface.blit(ghost, (int(ai_data['x']), int(ai_data['y'] - self.player_ship.height // 2)))

        # Draw player ship
        if not self.game_over or self.winner != "ai":
            if self.wormhole_active:
                pass
            elif self.player_hit_flash > 0:
                self.player_ship.draw(draw_surface, time_tick)
                # Red flash overlay on ship bounds only
                ship_rect = self.player_ship.get_rect()
                flash_surf = pygame.Surface((ship_rect.width, ship_rect.height), pygame.SRCALPHA)
                flash_surf.fill((255, 0, 0, 80))
                draw_surface.blit(flash_surf, ship_rect.topleft)
            else:
                if self.is_cloaked():
                    # Draw ship with reduced alpha via image
                    if self.player_ship.image:
                        ghost = self.player_ship.image.copy()
                        ghost.set_alpha(100)
                        draw_surface.blit(ghost, (int(self.player_ship.x),
                                                  int(self.player_ship.y - self.player_ship.height // 2)))
                    else:
                        self.player_ship.draw(draw_surface, time_tick)
                else:
                    self.player_ship.draw(draw_surface, time_tick)

        # Draw wormhole vortex effects
        for effect in self.wormhole_effects:
            effect.draw(draw_surface)

        # Draw drones
        for drone in self.drones:
            drone.draw(draw_surface)
        for drone in self.upgrade_drones:
            drone.draw(draw_surface)

        # Draw all AI ships
        for ai_ship in self.ai_ships:
            ai_ship.draw(draw_surface, time_tick)
            hit_flash = getattr(ai_ship, 'hit_flash', 0)
            if hit_flash > 0:
                # Red flash overlay on ship bounds only
                ship_rect = ai_ship.get_rect()
                flash_surf = pygame.Surface((ship_rect.width, ship_rect.height), pygame.SRCALPHA)
                flash_surf.fill((255, 0, 0, 80))
                draw_surface.blit(flash_surf, ship_rect.topleft)
                ai_ship.hit_flash = hit_flash - 1

        # Draw explosions
        for explosion in self.explosions:
            explosion.draw(draw_surface)

        # Draw damage numbers
        for dn in self.damage_numbers:
            dn.draw(draw_surface)

        # Draw popup notifications
        for pn in self.popup_notifications:
            pn.draw(draw_surface)

        # Draw UI
        _ui.draw_ui(self, draw_surface)

        # Draw level-up screen on top
        if self.showing_level_up and self.level_up_choices:
            _ui.draw_level_up_screen(self, draw_surface)

        # Blit with shake offset
        if shake_x != 0 or shake_y != 0:
            surface.blit(draw_surface, (shake_x, shake_y))
