"""
Co-op Space Shooter Game — Host-Authoritative

Subclasses SpaceShooterGame to add:
- Partner ship (player 2)
- Independent cameras (P1 follows host ship, P2 data sent to client)
- Revival mechanic (killing an enemy revives dead partner)
- Shared scoring / XP / upgrades
- State snapshot serialization for network sync (expanded for all entities)
"""

import math
import random
import pygame

from .game import SpaceShooterGame
from .ship import Ship
from .camera import Camera
from .spawner import ContinuousSpawner
from .entities import Explosion, DamageNumber, PopupNotification, XPOrb, PowerUp
from .virtual_keys import VirtualKeys
from .upgrades import ENEMY_TYPES


# Distance at which we warn players they're too far apart (very generous)
LEASH_WARNING_DIST = 5000


class CoopSpaceShooterGame(SpaceShooterGame):
    """Two-player co-op space shooter. Runs on the host."""

    def __init__(self, screen_width, screen_height,
                 p1_faction, p2_faction, session_scores=None,
                 p1_variant=0, p2_variant=0):
        # Initialize base game with P1 as the main player
        super().__init__(screen_width, screen_height,
                         p1_faction, p2_faction,
                         session_scores=session_scores, variant=p1_variant)

        self.is_coop = True
        self.p1_faction = p1_faction
        self.p2_faction = p2_faction

        # Create partner ship (P2) offset from P1
        self.partner_ship = Ship(
            150, 0,
            p2_faction, is_player=True,
            screen_width=screen_width, screen_height=screen_height,
            variant=p2_variant
        )
        self.partner_ship.max_health = 150
        self.partner_ship.health = 150
        self.partner_ship.max_shields = 150
        self.partner_ship.shields = 150

        # Partner input (VirtualKeys for network, real keys for local testing)
        self.partner_keys = VirtualKeys()

        # Revival state
        self.p1_alive = True
        self.p2_alive = True
        self.p1_ghost = False
        self.p2_ghost = False
        self.p1_invuln_timer = 0  # Per-player invulnerability (frames)
        self.p2_invuln_timer = 0
        self.revival_pulse_timer = 0
        self.revival_popup_timer = 0
        self.revival_target = None  # "p1" or "p2"

        # Leash warning
        self.leash_warning = False

        # Snapshot frame counter (send every 3 frames = 20 Hz)
        self._snapshot_frame = 0

        # Heartbeat tracking
        self._heartbeat_timer = 0
        self._last_partner_msg_frame = 0

        # Scale spawner for two players
        self.spawner = ContinuousSpawner(self.camera, p1_faction, self.all_factions,
                                          coop_scale=1.5)

    def update(self):
        """Override to handle two-player logic."""
        if self.showing_level_up:
            return

        self.survival_frames += 1
        self._snapshot_frame += 1
        self._heartbeat_timer += 1

        # Kill streak timer
        if self.kill_streak > 0:
            self.kill_streak_timer += 1
            if self.kill_streak_timer >= 180:
                self.kill_streak = 0
                self.kill_streak_timer = 0

        # Tick per-player invulnerability timers
        if self.p1_invuln_timer > 0:
            self.p1_invuln_timer -= 1
        if self.p2_invuln_timer > 0:
            self.p2_invuln_timer -= 1

        if self.game_over:
            self.explosions = [e for e in self.explosions if e.update()]
            self.damage_numbers = [d for d in self.damage_numbers if d.update()]
            return

        # --- Update P1 ---
        keys = pygame.key.get_pressed()
        if self.p1_alive and not self.wormhole_active:
            self.player_ship.update(keys)
            self._update_ship_facing(self.player_ship)

        # --- Update P2 ---
        if self.p2_alive:
            self.partner_ship.update(self.partner_keys)
            self._update_ship_facing(self.partner_ship)

        # --- Camera follows P1 (independent cameras — client follows P2) ---
        self._update_coop_camera()

        # --- Leash check ---
        dist = math.hypot(
            self.player_ship.x - self.partner_ship.x,
            self.player_ship.y - self.partner_ship.y
        )
        self.leash_warning = dist > LEASH_WARNING_DIST

        # --- Wormhole (P1 only for simplicity) ---
        if self.wormhole_cooldown > 0:
            self.wormhole_cooldown -= 1
        if self.wormhole_active:
            self._update_wormhole()
        self.wormhole_effects = [e for e in self.wormhole_effects if e.update()]

        # --- Spawner (scaled for 2 players) ---
        new_ships = self.spawner.update(self.ai_ships, self.screen_width, self.screen_height)
        self.ai_ships.extend(new_ships)

        # --- Despawn far entities based on NEAREST alive player ---
        despawn_dist = 2500
        p1x = self.player_ship.x + self.player_ship.width // 2
        p1y = self.player_ship.y
        p2x = self.partner_ship.x + self.partner_ship.width // 2
        p2y = self.partner_ship.y

        def dist_from_nearest_player(ex, ey):
            d1 = math.hypot(ex - p1x, ey - p1y) if self.p1_alive else float('inf')
            d2 = math.hypot(ex - p2x, ey - p2y) if self.p2_alive else float('inf')
            return min(d1, d2)

        self.ai_ships = [s for s in self.ai_ships
                         if dist_from_nearest_player(s.x, s.y) < despawn_dist]
        self.asteroids = [a for a in self.asteroids if a.active and
                          dist_from_nearest_player(a.x, a.y) < despawn_dist]
        self.xp_orbs = [o for o in self.xp_orbs if o.active and
                        dist_from_nearest_player(o.x, o.y) < despawn_dist]
        self.powerups = [p for p in self.powerups if p.active and
                         dist_from_nearest_player(p.x, p.y) < despawn_dist]
        self.area_bombs = [b for b in self.area_bombs
                           if dist_from_nearest_player(b.x, b.y) < despawn_dist]

        # --- Upgrade passive effects (apply to both ships) ---
        self._apply_passive_upgrades()

        # --- Update suns ---
        from .entities import Sun
        for sun in self.suns[:]:
            entities_dict = {
                "ships": ([self.player_ship] if self.p1_alive else []) +
                         ([self.partner_ship] if self.p2_alive else []),
                "enemies": self.ai_ships,
                "allies": self.ally_ships,
                "projectiles": self.projectiles,
                "asteroids": self.asteroids,
            }
            sun.update(entities_dict)
            if sun.phase == Sun.PHASE_EXPLODING and sun.timer == 1:
                self.screen_shake.trigger(8, 15)
            if not sun.active:
                self.suns.remove(sun)

        # Sun spawning
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

        # --- Update area bombs ---
        for bomb in self.area_bombs[:]:
            bomb.update()
            if bomb.detonated:
                self.explosions.append(Explosion(bomb.x, bomb.y, tier="normal"))
                self.screen_shake.trigger(4, 8)
                # Damage both players
                for ship, alive, tag in [(self.player_ship, self.p1_alive, "p1"),
                                         (self.partner_ship, self.p2_alive, "p2")]:
                    if not alive:
                        continue
                    if self._is_player_invulnerable(tag):
                        continue
                    sx = ship.x + ship.width // 2
                    sy = ship.y
                    d = math.hypot(sx - bomb.x, sy - bomb.y)
                    if d < bomb.blast_radius:
                        dmg = int(bomb.damage * (1.0 - d / bomb.blast_radius * 0.5))
                        ship.take_damage(dmg)
                        self.damage_numbers.append(DamageNumber(sx, sy, dmg, (255, 150, 50)))
                        if ship.health <= 0:
                            self._kill_player(tag)
                self.area_bombs.remove(bomb)

        # --- Update AI ships (target nearest alive player) ---
        for ai_ship in self.ai_ships:
            # Skip stunned enemies
            if getattr(ai_ship, '_stunned', 0) > 0:
                ai_ship._stunned -= 1
                ai_ship.vx = 0
                ai_ship.vy = 0
                ai_ship.stop_beam()
                continue

            target = self._nearest_alive_ship(ai_ship)
            ai_ship.update_ai(target, self.asteroids, self.ai_ships)

            if self.is_cloaked():
                ai_ship.stop_beam()
                continue

            ai_ship.ai_fire_timer -= 1
            y_diff = abs(ai_ship.y - target.y)
            dx_to_target = target.x - ai_ship.x
            facing_target = (ai_ship.facing[0] > 0 and dx_to_target > 0) or \
                            (ai_ship.facing[0] < 0 and dx_to_target < 0)

            if ai_ship.weapon_type == "beam":
                if y_diff < 80 and facing_target:
                    if not ai_ship.current_beam:
                        ai_ship.fire()
                else:
                    ai_ship.stop_beam()
            else:
                if ai_ship.ai_fire_timer <= 0 and y_diff < 150 and facing_target:
                    projectile = ai_ship.fire()
                    if projectile:
                        self.projectiles.append(projectile)
                    ai_ship.ai_fire_timer = random.randint(
                        max(240, ai_ship.fire_rate * 4),
                        max(420, ai_ship.fire_rate * 7)
                    )

            # Bomber behavior: fire area bombs
            behavior = getattr(ai_ship, '_behavior', None)
            if behavior == 'bomber':
                ai_ship._bomber_timer = getattr(ai_ship, '_bomber_timer', 0) + 1
                if ai_ship._bomber_timer >= 180:
                    ai_ship._bomber_timer = 0
                    from .projectiles import AreaBomb
                    self.area_bombs.append(AreaBomb(
                        ai_ship.x + ai_ship.width // 2, ai_ship.y,
                        target.x + target.width // 2, target.y))
            elif behavior == 'mini_boss_spawner':
                ai_ship._spawner_timer = getattr(ai_ship, '_spawner_timer', 0) + 1
                spawned = getattr(ai_ship, '_spawned_darts', [])
                spawned = [d for d in spawned if d in self.ai_ships]
                ai_ship._spawned_darts = spawned
                if ai_ship._spawner_timer >= 300 and len(spawned) < 4:
                    ai_ship._spawner_timer = 0
                    tier = self.spawner.get_current_tier()
                    dart = self.spawner._spawn_enemy(tier, self.screen_width, self.screen_height,
                                                     force_type="wraith_dart")
                    if dart:
                        dart.x = ai_ship.x + random.randint(-80, 80)
                        dart.y = ai_ship.y + random.randint(-80, 80)
                        self.ai_ships.append(dart)
                        spawned.append(dart)
                        ai_ship._spawned_darts = spawned

        # --- Auto-fire for both alive players ---
        if self.p1_alive:
            self._auto_fire_ship(self.player_ship, keys)
        if self.p2_alive:
            self._auto_fire_ship(self.partner_ship, self.partner_keys)

        # --- Update projectiles and collisions ---
        self._update_projectiles()
        self._update_collisions()

        # --- Update powerups, XP orbs, explosions ---
        self._update_entities()

        # --- Active powerup timer decrements ---
        expired = []
        for ptype, timer in list(self.active_powerups.items()):
            if timer > 0:
                self.active_powerups[ptype] = timer - 1
                if timer - 1 <= 0:
                    expired.append(ptype)
        for ptype in expired:
            self._expire_powerup(ptype)

        # --- Revival pulse decay ---
        if self.revival_pulse_timer > 0:
            self.revival_pulse_timer -= 1
        if self.revival_popup_timer > 0:
            self.revival_popup_timer -= 1

        # --- Both dead = game over ---
        if not self.p1_alive and not self.p2_alive:
            self.game_over = True
            self.winner = "enemies"

        # Asteroid spawning
        self.asteroid_spawn_timer += 1
        if self.asteroid_spawn_timer >= self.asteroid_spawn_rate:
            self.asteroid_spawn_timer = 0
            self._spawn_asteroid()

        # Periodic powerup spawns near a random alive player
        self.powerup_spawn_timer += 1
        if self.powerup_spawn_timer >= random.randint(240, 420):
            self.powerup_spawn_timer = 0
            alive_ships = []
            if self.p1_alive:
                alive_ships.append(self.player_ship)
            if self.p2_alive:
                alive_ships.append(self.partner_ship)
            if alive_ships:
                target = random.choice(alive_ships)
                angle = random.uniform(0, math.pi * 2)
                pdist = random.uniform(150, 350)
                px = target.x + math.cos(angle) * pdist
                py = target.y + math.sin(angle) * pdist
                self.powerups.append(PowerUp.spawn_at(px, py, faction=self.p1_faction))

        # Hit sound cooldown tick (frame-based)
        if self.hit_sound_cooldown > 0:
            self.hit_sound_cooldown -= 1

        # Supergate boss system (shared with base game)
        self._update_supergate_system()

        # Update miscellaneous effects
        self.screen_shake.update()
        self.damage_numbers = [d for d in self.damage_numbers if d.update()]
        self.popup_notifications = [p for p in self.popup_notifications if p.update()]
        self.explosions = [e for e in self.explosions if e.update()]

        # XP level-up check
        while self.xp >= self.xp_to_next and not self.showing_level_up:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(480 * 1.25 ** (self.level - 1))
            self.pending_level_ups += 1
        if self.pending_level_ups > 0 and not self.showing_level_up:
            self._show_level_up()

    def _update_ship_facing(self, ship):
        """Derive facing from velocity."""
        if abs(ship.vx) > 0.5 or abs(ship.vy) > 0.5:
            if abs(ship.vx) >= abs(ship.vy):
                ship.set_facing((1, 0) if ship.vx > 0 else (-1, 0))
            else:
                ship.set_facing((0, -1) if ship.vy < 0 else (0, 1))

    def _update_coop_camera(self):
        """Camera follows P1 (host). Client follows P2 independently."""
        if self.p1_alive:
            self.camera.follow(
                self.player_ship.x + self.player_ship.width // 2,
                self.player_ship.y)
        elif self.p2_alive:
            # P1 dead — host camera follows P2 until revival
            self.camera.follow(
                self.partner_ship.x + self.partner_ship.width // 2,
                self.partner_ship.y)

    def _beam_damage_players(self, beam):
        """Override: check beam collision against both player ships."""
        for ship, alive, tag in [(self.player_ship, self.p1_alive, "p1"),
                                  (self.partner_ship, self.p2_alive, "p2")]:
            if not alive:
                continue
            if self._is_player_invulnerable(tag):
                continue
            cx = ship.x + ship.width // 2
            cy = ship.y
            r = max(ship.width, ship.height) // 2
            if beam.line_circle_intersect(cx, cy, r):
                dmg = beam.damage_per_frame
                self.player_hit_flash = 3
                self.damage_numbers.append(DamageNumber(cx, cy, dmg, (255, 200, 50)))
                if ship.take_damage(dmg):
                    self._kill_player(tag)

    def _nearest_alive_ship(self, ai_ship):
        """Return the nearest alive player ship to an AI ship."""
        if self.p1_alive and self.p2_alive:
            d1 = math.hypot(ai_ship.x - self.player_ship.x,
                            ai_ship.y - self.player_ship.y)
            d2 = math.hypot(ai_ship.x - self.partner_ship.x,
                            ai_ship.y - self.partner_ship.y)
            return self.player_ship if d1 <= d2 else self.partner_ship
        elif self.p1_alive:
            return self.player_ship
        elif self.p2_alive:
            return self.partner_ship
        # Both dead — just return P1 as fallback
        return self.player_ship

    def _auto_fire_ship(self, ship, keys):
        """Handle auto-fire for a player ship."""
        if ship.fire_cooldown > 0:
            ship.fire_cooldown -= 1
            return

        # Auto-fire when moving
        moving = (keys[pygame.K_w] or keys[pygame.K_s] or
                  keys[pygame.K_a] or keys[pygame.K_d] or
                  keys[pygame.K_UP] or keys[pygame.K_DOWN] or
                  keys[pygame.K_LEFT] or keys[pygame.K_RIGHT])
        if not moving:
            return

        projectile = ship.fire()
        if projectile:
            projectile.is_player_proj = True
            # Apply damage multiplier from upgrades
            projectile.damage = int(projectile.damage * self.base_damage_mult)
            dmg_stacks = self.upgrades.get("naquadah_rounds", 0)
            if dmg_stacks:
                projectile.damage = int(projectile.damage * (1 + dmg_stacks * 0.15))
            self.projectiles.append(projectile)

    def _update_collisions(self):
        """Check collisions for both player ships."""
        for proj in self.projectiles[:]:
            if not proj.active:
                continue
            pr = proj.get_rect() if hasattr(proj, 'get_rect') else pygame.Rect(
                int(proj.x - 4), int(proj.y - 4), 8, 8)

            if getattr(proj, 'is_player_proj', False):
                # Player projectile → enemy
                for ai_ship in self.ai_ships[:]:
                    if pr.colliderect(ai_ship.get_rect()):
                        damage = getattr(proj, 'damage', 10)
                        ai_ship.hit_flash = 5
                        self.damage_numbers.append(DamageNumber(
                            ai_ship.x + ai_ship.width // 2, ai_ship.y,
                            damage, (255, 255, 100)))
                        if self._damage_enemy(ai_ship, damage):
                            self._on_enemy_killed(ai_ship)
                        if not getattr(proj, 'piercing', False):
                            proj.active = False
                        break

                # Player projectile → ally ships (skip — no friendly fire)
            else:
                # Enemy projectile → player ships
                if self.p1_alive:
                    if pr.colliderect(self.player_ship.get_rect()):
                        self._hit_player(self.player_ship, proj, "p1")
                        proj.active = False
                        continue
                if self.p2_alive:
                    if pr.colliderect(self.partner_ship.get_rect()):
                        self._hit_player(self.partner_ship, proj, "p2")
                        proj.active = False
                        continue

                # Enemy projectile → ally ships
                for ally in self.ally_ships[:]:
                    if pr.colliderect(ally.get_rect()):
                        ally.hit_flash = 5
                        ally.take_damage(getattr(proj, 'damage', 10))
                        proj.active = False
                        break

        # Remove inactive projectiles
        self.projectiles = [p for p in self.projectiles if p.active]

        # Ship collision with asteroids (both players)
        for asteroid in self.asteroids[:]:
            if not asteroid.active:
                continue
            for ship, alive, tag in [(self.player_ship, self.p1_alive, "p1"),
                                     (self.partner_ship, self.p2_alive, "p2")]:
                if alive and asteroid.get_rect().colliderect(ship.get_rect()):
                    ship.take_damage(25, is_asteroid=True)
                    self.explosions.append(Explosion(asteroid.x, asteroid.y, tier="small"))
                    asteroid.active = False
                    self.screen_shake.trigger(3, 5)
                    if ship.health <= 0:
                        self._kill_player(tag)
                    break
            if not asteroid.active:
                continue
            for ai_ship in self.ai_ships:
                if asteroid.get_rect().colliderect(ai_ship.get_rect()):
                    ai_ship.hit_flash = 5
                    ai_ship.take_damage(25, is_asteroid=True)
                    self.explosions.append(Explosion(asteroid.x, asteroid.y, tier="small"))
                    asteroid.active = False
                    break

        self.asteroids = [a for a in self.asteroids if a.active]

        # Contact damage: enemy ships touching players
        for ai_ship in self.ai_ships[:]:
            if ai_ship.contact_damage_cooldown > 0:
                continue
            for ship, alive, tag in [(self.player_ship, self.p1_alive, "p1"),
                                     (self.partner_ship, self.p2_alive, "p2")]:
                if alive and ai_ship.get_rect().colliderect(ship.get_rect()):
                    if self._is_player_invulnerable(tag):
                        ai_ship.contact_damage_cooldown = 30
                        self.damage_numbers.append(DamageNumber(
                            ship.x + ship.width // 2, ship.y, 0, (255, 215, 0)))
                        break
                    contact_dmg = 36 if getattr(ai_ship, 'is_boss', False) else 14
                    ship.take_damage(contact_dmg)
                    self.damage_numbers.append(DamageNumber(
                        ship.x + ship.width // 2, ship.y,
                        contact_dmg, (255, 80, 80)))
                    ai_ship.contact_damage_cooldown = 60
                    if ship.health <= 0:
                        self._kill_player(tag)
                    # Swarm lifesteal: heal on contact
                    if getattr(ai_ship, '_behavior', None) == 'swarm_lifesteal':
                        heal = min(contact_dmg, ai_ship.max_health - ai_ship.health)
                        ai_ship.health += heal
                    break

    def _is_player_invulnerable(self, player_tag):
        """Check if a player has invulnerability active (per-player or shared)."""
        if player_tag == "p1" and self.p1_invuln_timer > 0:
            return True
        if player_tag == "p2" and self.p2_invuln_timer > 0:
            return True
        return self.active_powerups.get("goauld_sarcophagus", 0) > 0

    def _hit_player(self, ship, proj, player_tag):
        """Apply damage to a player ship, handle death."""
        # Skip damage if invulnerable
        if self._is_player_invulnerable(player_tag):
            self.damage_numbers.append(DamageNumber(
                ship.x + ship.width // 2, ship.y, 0, (255, 215, 0)))
            return

        damage = getattr(proj, 'damage', 10)
        # Shields absorb first
        if ship.shields > 0:
            absorbed = min(ship.shields, damage)
            ship.shields -= absorbed
            damage -= absorbed
            ship.shield_hit_timer = 10
        if damage > 0:
            ship.health -= damage

        self.damage_numbers.append(DamageNumber(
            ship.x + ship.width // 2, ship.y,
            getattr(proj, 'damage', 10), (255, 80, 80)))
        self.screen_shake.trigger(4, 8)
        self.player_hit_flash = 8

        if ship.health <= 0:
            self._kill_player(player_tag)

    def _kill_player(self, player_tag):
        """Mark a player as dead (ghost mode)."""
        if player_tag == "p1":
            if not self.p1_alive:
                return  # Already dead
            self.p1_alive = False
            self.p1_ghost = True
            ship = self.player_ship
        else:
            if not self.p2_alive:
                return  # Already dead
            self.p2_alive = False
            self.p2_ghost = True
            ship = self.partner_ship

        # Death explosion
        self.explosions.append(Explosion(
            ship.x + ship.width // 2, ship.y, tier="large"))
        self.screen_shake.trigger(8, 15)
        self.popup_notifications.append(PopupNotification(
            ship.x + ship.width // 2, ship.y - 30,
            f"P{'1' if player_tag == 'p1' else '2'} DOWN!",
            (255, 80, 80), duration=120))

    def _on_enemy_killed(self, enemy):
        """Override: handle enemy kill with revival check and themed explosions."""
        from .upgrades import ENEMY_EXPLOSION_PALETTES

        # Special handling for supergate bosses
        if enemy in self.ori_bosses:
            self._ori_boss_killed(enemy)
            # Revival check after boss kill
            if self.p1_ghost and self.p2_alive:
                self._revive_player("p1")
            elif self.p2_ghost and self.p1_alive:
                self._revive_player("p2")
            return

        # Score
        score_val = self.SCORE_BOSS if getattr(enemy, 'is_boss', False) else self.SCORE_ENEMY
        self.score += score_val
        self.enemies_defeated += 1
        self.total_kills += 1

        # Kill streak
        self.kill_streak += 1
        self.kill_streak_timer = 0
        if self.kill_streak > 1:
            self.score += self.kill_streak * 25

        # XP orbs
        xp_val = getattr(enemy, 'xp_value', 20)
        num_orbs = max(1, xp_val // 10)
        for _ in range(min(num_orbs, 5)):
            self.xp_orbs.append(XPOrb(
                enemy.x + enemy.width // 2 + random.randint(-20, 20),
                enemy.y + random.randint(-20, 20),
                value=max(1, xp_val // num_orbs)))

        # Explosion with themed palette
        is_boss = getattr(enemy, 'is_boss', False)
        tier = "large" if is_boss else "normal"
        palette = ENEMY_EXPLOSION_PALETTES.get(getattr(enemy, 'enemy_type', ''))
        self.explosions.append(Explosion(
            enemy.x + enemy.width // 2, enemy.y, tier=tier,
            color_palette=palette))

        # Secondary explosion for bosses and wraith_hive
        if is_boss or getattr(enemy, 'enemy_type', '') == 'wraith_hive':
            ox = enemy.x + enemy.width // 2 + random.randint(-30, 30)
            oy = enemy.y + random.randint(-30, 30)
            self.explosions.append(Explosion(ox, oy, tier=tier,
                                             color_palette=palette, secondary=True))

        # Replicator split-on-death
        enemy_type = getattr(enemy, 'enemy_type', '')
        behavior = ENEMY_TYPES.get(enemy_type, {}).get('behavior')
        if behavior == 'split_on_death':
            split_gen = getattr(enemy, '_split_gen', 0)
            if split_gen < 2:
                for _ in range(2):
                    child = Ship(
                        enemy.x + random.randint(-30, 30),
                        enemy.y + random.randint(-30, 30),
                        enemy.faction, is_player=False,
                        screen_width=self.screen_width, screen_height=self.screen_height)
                    child.max_health = max(10, enemy.max_health // 2)
                    child.health = child.max_health
                    child.speed = enemy.speed
                    child.enemy_type = enemy_type
                    child._behavior = behavior
                    child._split_gen = split_gen + 1
                    child.xp_value = max(5, getattr(enemy, 'xp_value', 25) // 2)
                    # Scale down visually
                    if child.image:
                        new_w = int(child.width * 0.7)
                        new_h = int(child.height * 0.7)
                        child.image = pygame.transform.smoothscale(child.image, (new_w, new_h))
                        child.width = new_w
                        child.height = new_h
                        child.image_right = child.image.copy()
                        child.image_left = pygame.transform.flip(child.image, True, False)
                        child.image_up = pygame.transform.rotate(child.image_right, 90)
                        child.image_down = pygame.transform.rotate(child.image_right, -90)
                    self.ai_ships.append(child)

        # Power-up drop
        drop_chance = self.powerup_drop_chance
        if self.active_powerups.get("lucian_smugglers_luck", 0) > 0:
            drop_chance = min(1.0, drop_chance * 2.0)
        if random.random() < drop_chance:
            self.powerups.append(PowerUp.spawn_at(
                enemy.x + enemy.width // 2, enemy.y,
                faction=self.p1_faction))

        # Remove from ai_ships
        if enemy in self.ai_ships:
            self.ai_ships.remove(enemy)

        # --- Revival check ---
        if self.p1_ghost and self.p2_alive:
            self._revive_player("p1")
        elif self.p2_ghost and self.p1_alive:
            self._revive_player("p2")

    def _revive_player(self, player_tag):
        """Revive a dead player at partner's position with 50% stats."""
        if player_tag == "p1":
            self.p1_alive = True
            self.p1_ghost = False
            revived = self.player_ship
            partner = self.partner_ship
        else:
            self.p2_alive = True
            self.p2_ghost = False
            revived = self.partner_ship
            partner = self.player_ship

        # Respawn at partner position
        revived.x = partner.x + random.randint(-50, 50)
        revived.y = partner.y + random.randint(-50, 50)
        revived.health = revived.max_health // 2
        revived.shields = revived.max_shields // 2
        revived.vx = 0
        revived.vy = 0

        # Per-player invulnerability on revival (3 seconds)
        if player_tag == "p1":
            self.p1_invuln_timer = max(self.p1_invuln_timer, 180)
        else:
            self.p2_invuln_timer = max(self.p2_invuln_timer, 180)

        # Visual feedback
        self.revival_pulse_timer = 30
        self.revival_popup_timer = 90
        self.revival_target = player_tag
        self.popup_notifications.append(PopupNotification(
            revived.x + revived.width // 2, revived.y - 40,
            "REVIVED!", (100, 255, 100), duration=90))
        self.screen_shake.trigger(3, 6)

    def _apply_passive_upgrades(self):
        """Apply passive upgrade effects to both ships."""
        # Sarcophagus healing
        sarc = self.upgrades.get("sarcophagus", 0)
        if sarc > 0:
            rate = sarc * 5.0 / 60.0
            if self.p1_alive:
                self.player_ship.health = min(self.player_ship.max_health,
                                              self.player_ship.health + rate)
            if self.p2_alive:
                self.partner_ship.health = min(self.partner_ship.max_health,
                                               self.partner_ship.health + rate)

        # Shield Harmonics
        sh = self.upgrades.get("shield_harmonics", 0)
        if sh > 0:
            regen = sh * 0.1
            if self.p1_alive:
                self.player_ship.shields = min(self.player_ship.max_shields,
                                               self.player_ship.shields + regen)
            if self.p2_alive:
                self.partner_ship.shields = min(self.partner_ship.max_shields,
                                                self.partner_ship.shields + regen)

    def _update_entities(self):
        """Update powerups, XP orbs — collection by either player."""
        # XP orbs — collected by nearest alive player
        for orb in self.xp_orbs[:]:
            orb.update()
            if not orb.active:
                continue
            for ship, alive in [(self.player_ship, self.p1_alive),
                                (self.partner_ship, self.p2_alive)]:
                if not alive:
                    continue
                dx = (ship.x + ship.width // 2) - orb.x
                dy = ship.y - orb.y
                dist = math.hypot(dx, dy)
                # Magnetize pull
                if dist < 200:
                    if dist > 5:
                        orb.vx += (dx / dist) * 1.5
                        orb.vy += (dy / dist) * 1.5
                if dist < 30:
                    self.xp += orb.value
                    orb.active = False
                    break

        self.xp_orbs = [o for o in self.xp_orbs if o.active]

        # Powerups — collected by nearest alive player
        for pu in self.powerups[:]:
            pu.update()
            if not pu.active:
                continue
            for ship, alive in [(self.player_ship, self.p1_alive),
                                (self.partner_ship, self.p2_alive)]:
                if not alive:
                    continue
                dx = (ship.x + ship.width // 2) - pu.x
                dy = ship.y - pu.y
                if math.hypot(dx, dy) < 40:
                    self._apply_powerup(pu)
                    pu.active = False
                    break

        self.powerups = [p for p in self.powerups if p.active]

    def _collect_powerup(self, pu):
        """Collect a powerup — benefits both players."""
        pu_type = getattr(pu, 'type', 'shield')
        if pu_type == 'shield':
            for ship, alive in [(self.player_ship, self.p1_alive),
                                (self.partner_ship, self.p2_alive)]:
                if alive:
                    ship.shields = min(ship.max_shields, ship.shields + 30)
        elif pu_type == 'health':
            for ship, alive in [(self.player_ship, self.p1_alive),
                                (self.partner_ship, self.p2_alive)]:
                if alive:
                    ship.health = min(ship.max_health, ship.health + 25)
        else:
            # Other powerups go to shared pool
            duration = 600
            self.active_powerups[pu_type] = self.active_powerups.get(pu_type, 0) + duration

    def _update_projectiles(self):
        """Update all projectile positions."""
        p1x = self.player_ship.x + self.player_ship.width // 2
        p1y = self.player_ship.y
        p2x = self.partner_ship.x + self.partner_ship.width // 2
        p2y = self.partner_ship.y
        for proj in self.projectiles:
            proj.update()
        # Remove off-screen or inactive — despawn based on nearest player
        def near_player(p):
            d1 = math.hypot(p.x - p1x, p.y - p1y) if self.p1_alive else float('inf')
            d2 = math.hypot(p.x - p2x, p.y - p2y) if self.p2_alive else float('inf')
            return min(d1, d2) < 2500
        self.projectiles = [p for p in self.projectiles
                            if p.active and near_player(p)]

    def _spawn_asteroid(self):
        """Spawn an asteroid near the viewport edge."""
        from .entities import Asteroid
        wx, wy = self.camera.get_spawn_ring(300, 500)
        self.asteroids.append(Asteroid(wx, wy))

    def _update_wormhole(self):
        """Handle wormhole transit."""
        from .entities import WormholeEffect
        self.wormhole_transit_timer += 1
        halfway = self.wormhole_transit_duration // 2
        if self.wormhole_transit_timer == halfway:
            self.player_ship.x = self.wormhole_exit_x - self.player_ship.width // 2
            self.player_ship.y = self.wormhole_exit_y
            self.wormhole_effects.append(
                WormholeEffect(self.wormhole_exit_x, self.wormhole_exit_y, is_entry=False))
            self.camera.snap_to(self.wormhole_exit_x, self.wormhole_exit_y)
        if self.wormhole_transit_timer >= self.wormhole_transit_duration:
            self.wormhole_active = False
            self.wormhole_cooldown = self.wormhole_max_cooldown

    def fire_partner_secondary(self):
        """Fire P2's secondary weapon."""
        if not self.p2_alive:
            return
        result = self.partner_ship.fire_secondary()
        if result:
            result_type, result_data = result
            if result_type == "projectile":
                result_data.is_player_proj = True
                self.projectiles.append(result_data)
            elif result_type == "ion_pulse":
                radius, damage = result_data
                px = self.partner_ship.x + self.partner_ship.width // 2
                py = self.partner_ship.y
                self.screen_shake.trigger(5, 10)
                self.ion_pulse_effects.append({
                    "x": px, "y": py, "radius": 0,
                    "max_radius": radius, "timer": 0, "duration": 20,
                    "color": self.partner_ship.laser_color,
                })
                for enemy in self.ai_ships[:]:
                    dist = math.hypot(enemy.x + enemy.width // 2 - px, enemy.y - py)
                    if dist < radius:
                        dmg = int(damage * (1.0 - dist / radius * 0.5))
                        enemy.hit_flash = 5
                        self.damage_numbers.append(DamageNumber(
                            enemy.x + enemy.width // 2, enemy.y,
                            dmg, (100, 255, 255)))
                        if self._damage_enemy(enemy, dmg):
                            self._on_enemy_killed(enemy)
            elif result_type == "war_cry":
                self.screen_shake.trigger(4, 8)
                self.popup_notifications.append(PopupNotification(
                    self.partner_ship.x + self.partner_ship.width // 2,
                    self.partner_ship.y - 80,
                    "WAR CRY!", (255, 150, 50)))
            elif result_type == "mines":
                for mine in result_data:
                    mine.is_player_proj = True
                    self.mines.append(mine)

    def draw(self, surface):
        """Override to draw both ships and co-op UI."""
        super().draw(surface)

        # Draw partner ship (if alive or ghost)
        if self.p2_alive or self.p2_ghost:
            sx, sy = self.camera.world_to_screen(
                self.partner_ship.x + self.partner_ship.width // 2,
                self.partner_ship.y)
            if -100 < sx < self.screen_width + 100 and -100 < sy < self.screen_height + 100:
                img = self.partner_ship.get_image()
                if img:
                    draw_x = int(sx - img.get_width() // 2)
                    draw_y = int(sy - img.get_height() // 2)
                    if self.p2_ghost:
                        img = img.copy()
                        img.set_alpha(80)
                    surface.blit(img, (draw_x, draw_y))

        # Draw co-op UI overlay
        self._draw_coop_ui(surface)

    def _draw_coop_ui(self, surface):
        """Draw co-op specific UI: P2 health, partner arrow, revival status."""
        # P2 health bar (top-right)
        if self.p2_alive:
            self._draw_health_bar(surface, self.partner_ship,
                                  self.screen_width - 250, 10, "P2")
        elif self.p2_ghost:
            ghost_font = pygame.font.SysFont("Arial", 20, bold=True)
            text = ghost_font.render("P2 DOWN — Kill to revive!", True, (255, 80, 80))
            surface.blit(text, (self.screen_width - text.get_width() - 20, 10))

        # CO-OP label
        coop_font = pygame.font.SysFont("Arial", 16, bold=True)
        label = coop_font.render("CO-OP", True, (100, 255, 100))
        surface.blit(label, (self.screen_width // 2 - label.get_width() // 2, 5))

        # Partner arrow (when near screen edge)
        self._draw_partner_arrow(surface)

        # Leash warning
        if self.leash_warning:
            warn_font = pygame.font.SysFont("Arial", 24, bold=True)
            warn = warn_font.render("TOO FAR APART!", True, (255, 200, 50))
            surface.blit(warn, (self.screen_width // 2 - warn.get_width() // 2, 40))

        # Revival pulse
        if self.revival_pulse_timer > 0 and self.revival_target:
            ship = self.player_ship if self.revival_target == "p1" else self.partner_ship
            sx, sy = self.camera.world_to_screen(
                ship.x + ship.width // 2, ship.y)
            radius = int(40 + (30 - self.revival_pulse_timer) * 3)
            alpha = int(200 * self.revival_pulse_timer / 30)
            pulse_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(pulse_surf, (100, 255, 100, alpha),
                               (radius, radius), radius, 3)
            surface.blit(pulse_surf, (int(sx - radius), int(sy - radius)))

    def _draw_health_bar(self, surface, ship, x, y, label):
        """Draw a compact health/shield bar."""
        bar_w, bar_h = 220, 12
        font = pygame.font.SysFont("Arial", 14, bold=True)

        # Label
        lbl = font.render(label, True, (200, 200, 200))
        surface.blit(lbl, (x, y))

        # Health bar
        bar_y = y + 18
        hp_pct = max(0, ship.health / ship.max_health)
        pygame.draw.rect(surface, (40, 40, 40), (x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, (50, 200, 50), (x, bar_y, int(bar_w * hp_pct), bar_h))
        pygame.draw.rect(surface, (100, 100, 100), (x, bar_y, bar_w, bar_h), 1)

        # Shield bar
        bar_y += bar_h + 2
        sh_pct = max(0, ship.shields / ship.max_shields) if ship.max_shields > 0 else 0
        pygame.draw.rect(surface, (40, 40, 40), (x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, (50, 130, 255), (x, bar_y, int(bar_w * sh_pct), bar_h))
        pygame.draw.rect(surface, (100, 100, 100), (x, bar_y, bar_w, bar_h), 1)

    def _draw_partner_arrow(self, surface):
        """Draw an arrow pointing to partner when near screen edge."""
        if not self.p2_alive and not self.p2_ghost:
            return
        partner = self.partner_ship
        sx, sy = self.camera.world_to_screen(
            partner.x + partner.width // 2, partner.y)

        margin = 60
        on_screen = (margin < sx < self.screen_width - margin and
                     margin < sy < self.screen_height - margin)
        if on_screen:
            return

        # Clamp to screen edge
        cx, cy = self.screen_width // 2, self.screen_height // 2
        dx = sx - cx
        dy = sy - cy
        dist = max(1, math.hypot(dx, dy))
        edge_dist = min(
            (self.screen_width // 2 - 30) / max(1, abs(dx / dist)),
            (self.screen_height // 2 - 30) / max(1, abs(dy / dist))
        )
        ax = int(cx + dx / dist * edge_dist)
        ay = int(cy + dy / dist * edge_dist)

        color = (100, 200, 255) if self.p2_alive else (255, 100, 100)
        angle = math.atan2(dy, dx)
        size = 12
        pts = [
            (ax + int(math.cos(angle) * size),
             ay + int(math.sin(angle) * size)),
            (ax + int(math.cos(angle + 2.5) * size * 0.6),
             ay + int(math.sin(angle + 2.5) * size * 0.6)),
            (ax + int(math.cos(angle - 2.5) * size * 0.6),
             ay + int(math.sin(angle - 2.5) * size * 0.6)),
        ]
        pygame.draw.polygon(surface, color, pts)

    def get_state_snapshot(self):
        """Serialize game state for network transmission to client.

        Expanded to include all entity types for full client rendering.
        """
        def ship_data(ship, alive, ghost):
            return {
                'x': round(ship.x, 1), 'y': round(ship.y, 1),
                'vx': round(ship.vx, 1), 'vy': round(ship.vy, 1),
                'health': round(ship.health, 1),
                'shields': round(ship.shields, 1),
                'max_health': ship.max_health,
                'max_shields': ship.max_shields,
                'facing': ship.facing,
                'faction': ship.faction,
                'alive': alive, 'ghost': ghost,
            }

        def entity_data(ent):
            return {
                'x': round(ent.x, 1), 'y': round(ent.y, 1),
                'type': getattr(ent, 'enemy_type', 'regular'),
                'health': round(getattr(ent, 'health', 0), 1),
                'max_health': getattr(ent, 'max_health', 100),
                'faction': getattr(ent, 'faction', ''),
                'facing': getattr(ent, 'facing', (1, 0)),
                'is_boss': getattr(ent, 'is_boss', False),
            }

        def proj_data(p):
            return {
                'x': round(p.x, 1), 'y': round(p.y, 1),
                'player': getattr(p, 'is_player_proj', False),
                'color': getattr(p, 'color', (255, 255, 255)),
            }

        def powerup_data(pu):
            return {
                'x': round(pu.x, 1), 'y': round(pu.y, 1),
                'type': pu.type,
                'color': pu.props.get('color', (255, 255, 255)),
                'rarity': pu.props.get('rarity', 'common'),
            }

        def xp_data(orb):
            return {
                'x': round(orb.x, 1), 'y': round(orb.y, 1),
                'value': orb.value,
            }

        def explosion_data(exp):
            return {
                'x': round(exp.x, 1), 'y': round(exp.y, 1),
                'tier': exp.tier,
                'timer': exp.timer,
                'duration': exp.duration,
            }

        def sun_data(s):
            return {
                'x': round(s.x, 1), 'y': round(s.y, 1),
                'phase': s.phase,
                'timer': s.timer,
                'radius': getattr(s, 'radius', 80),
            }

        def ally_data(a):
            return {
                'x': round(a.x, 1), 'y': round(a.y, 1),
                'health': round(a.health, 1),
                'max_health': a.max_health,
                'facing': a.facing,
                'faction': a.faction,
            }

        return {
            'frame': self.survival_frames,
            'p1': ship_data(self.player_ship, self.p1_alive, self.p1_ghost),
            'p2': ship_data(self.partner_ship, self.p2_alive, self.p2_ghost),
            'enemies': [entity_data(e) for e in self.ai_ships[:60]],
            'projectiles': [proj_data(p) for p in self.projectiles[:100]],
            'powerups': [powerup_data(p) for p in self.powerups[:20]],
            'xp_orbs': [xp_data(o) for o in self.xp_orbs[:50]],
            'explosions': [explosion_data(e) for e in self.explosions[:20]],
            # Total counts so client can detect truncation
            'total_enemies': len(self.ai_ships),
            'total_projectiles': len(self.projectiles),
            'asteroids': [{'x': round(a.x, 1), 'y': round(a.y, 1),
                          'size': a.size} for a in self.asteroids[:30]],
            'suns': [sun_data(s) for s in self.suns],
            'allies': [ally_data(a) for a in self.ally_ships],
            'area_bombs': [{'x': round(b.x, 1), 'y': round(b.y, 1),
                           'fuse': b.fuse_timer, 'fuse_duration': b.fuse_duration}
                          for b in self.area_bombs],
            'mines': [{'x': round(m.x, 1), 'y': round(m.y, 1),
                       'radius': m.radius, 'armed': m.is_armed(),
                       'color': m.color[:3]} for m in self.mines[:20]],
            'ion_pulses': [{'x': round(e['x'], 1), 'y': round(e['y'], 1),
                           'radius': e.get('radius', 200),
                           'max_radius': e.get('max_radius', 200),
                           'timer': e.get('timer', 0),
                           'duration': e.get('duration', 30),
                           'color': e.get('color', (100, 180, 255))[:3]}
                          for e in self.ion_pulse_effects[:10]],
            'supergates': [{'x': round(sg.x, 1), 'y': round(sg.y, 1),
                           'phase': sg.phase, 'timer': sg.timer,
                           'ring_scale': round(sg.ring_scale, 2),
                           'health': round(sg.health, 1),
                           'max_health': sg.max_health}
                          for sg in self.supergates],
            'ori_beams': [{'x': round(ob.x, 1), 'y': round(ob.y, 1),
                          'angle': round(ob.current_angle, 3),
                          'length': ob.length, 'width': ob.width,
                          'active': ob.active}
                         for ob in self.ori_beams if ob.active],
            'score': self.score,
            'level': self.level,
            'xp': self.xp,
            'xp_to_next': self.xp_to_next,
            'survival_frames': self.survival_frames,
            'game_over': self.game_over,
            'showing_level_up': self.showing_level_up,
            'leash_warning': self.leash_warning,
            'difficulty': self.spawner.get_difficulty_label(),
            'active_powerups': {k: v for k, v in self.active_powerups.items() if v > 0},
            'revival_pulse': self.revival_pulse_timer,
            'revival_target': self.revival_target,
            'p1_invuln': self.p1_invuln_timer,
            'p2_invuln': self.p2_invuln_timer,
        }

    def apply_partner_input(self, input_dict):
        """Apply input from the network partner."""
        self.partner_keys.update(input_dict)
        self._last_partner_msg_frame = self.survival_frames

    def is_partner_connected(self):
        """Check if partner has sent input recently (within 5 seconds)."""
        return (self.survival_frames - self._last_partner_msg_frame) < 300
