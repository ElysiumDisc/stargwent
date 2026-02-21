"""
Co-op Space Shooter Game — Host-Authoritative

Subclasses SpaceShooterGame to add:
- Partner ship (player 2)
- Shared camera (midpoint between both ships)
- Revival mechanic (killing an enemy revives dead partner)
- Shared scoring / XP / upgrades
- State snapshot serialization for network sync
"""

import math
import random
import pygame

from .game import SpaceShooterGame
from .ship import Ship
from .camera import Camera
from .spawner import ContinuousSpawner
from .entities import Explosion, DamageNumber, PopupNotification
from .virtual_keys import VirtualKeys


# Distance at which we warn players they're too far apart
LEASH_WARNING_DIST = 800


class CoopSpaceShooterGame(SpaceShooterGame):
    """Two-player co-op space shooter. Runs on the host."""

    def __init__(self, screen_width, screen_height,
                 p1_faction, p2_faction, session_scores=None):
        # Initialize base game with P1 as the main player
        super().__init__(screen_width, screen_height,
                         p1_faction, p2_faction,
                         session_scores=session_scores)

        self.is_coop = True
        self.p1_faction = p1_faction
        self.p2_faction = p2_faction

        # Create partner ship (P2) offset from P1
        self.partner_ship = Ship(
            150, 0,
            p2_faction, is_player=True,
            screen_width=screen_width, screen_height=screen_height
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
        self.revival_pulse_timer = 0
        self.revival_popup_timer = 0
        self.revival_target = None  # "p1" or "p2"

        # Leash warning
        self.leash_warning = False

        # Snapshot frame counter (send every 3 frames = 20 Hz)
        self._snapshot_frame = 0

        # Scale spawner for two players
        self.spawner = ContinuousSpawner(self.camera, p1_faction, self.all_factions,
                                          coop_scale=1.5)

    def update(self):
        """Override to handle two-player logic."""
        if self.showing_level_up:
            return

        self.survival_frames += 1
        self._snapshot_frame += 1

        # Kill streak timer
        if self.kill_streak > 0:
            self.kill_streak_timer += 1
            if self.kill_streak_timer >= 180:
                self.kill_streak = 0
                self.kill_streak_timer = 0

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

        # --- Camera follows midpoint of alive ships ---
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
        # Temporarily increase max_alive for co-op
        new_ships = self.spawner.update(self.ai_ships, self.screen_width, self.screen_height)
        self.ai_ships.extend(new_ships)

        # --- Despawn far entities ---
        despawn_dist = 2500
        self.ai_ships = [s for s in self.ai_ships
                         if math.hypot(s.x - self.camera.x, s.y - self.camera.y) < despawn_dist]
        self.asteroids = [a for a in self.asteroids if a.active and
                          math.hypot(a.x - self.camera.x, a.y - self.camera.y) < despawn_dist]
        self.xp_orbs = [o for o in self.xp_orbs if o.active and
                        math.hypot(o.x - self.camera.x, o.y - self.camera.y) < despawn_dist]
        self.powerups = [p for p in self.powerups if p.active and
                         math.hypot(p.x - self.camera.x, p.y - self.camera.y) < despawn_dist]

        # --- Upgrade passive effects (apply to both ships) ---
        self._apply_passive_upgrades()

        # --- Update AI ships (target nearest alive player) ---
        for ai_ship in self.ai_ships:
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

        # Update miscellaneous effects
        self.screen_shake.update()
        self.damage_numbers = [d for d in self.damage_numbers if d.update()]
        self.popup_notifications = [p for p in self.popup_notifications if p.update()]
        self.explosions = [e for e in self.explosions if e.update()]

        # XP level-up check
        while self.xp >= self.xp_to_next and not self.showing_level_up:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.15)
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
        """Camera follows midpoint of alive ships."""
        if self.p1_alive and self.p2_alive:
            p1_cx = self.player_ship.x + self.player_ship.width // 2
            p1_cy = self.player_ship.y
            p2_cx = self.partner_ship.x + self.partner_ship.width // 2
            p2_cy = self.partner_ship.y
            self.camera.follow_midpoint(p1_cx, p1_cy, p2_cx, p2_cy)
        elif self.p1_alive:
            self.camera.follow(
                self.player_ship.x + self.player_ship.width // 2,
                self.player_ship.y)
        elif self.p2_alive:
            self.camera.follow(
                self.partner_ship.x + self.partner_ship.width // 2,
                self.partner_ship.y)

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
                        if ai_ship.take_damage(damage):
                            self._on_enemy_killed(ai_ship)
                        if not getattr(proj, 'piercing', False):
                            proj.active = False
                        break
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

        # Remove inactive projectiles
        self.projectiles = [p for p in self.projectiles if p.active]

    def _hit_player(self, ship, proj, player_tag):
        """Apply damage to a player ship, handle death."""
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
            self.p1_alive = False
            self.p1_ghost = True
            ship = self.player_ship
        else:
            self.p2_alive = False
            self.p2_ghost = True
            ship = self.partner_ship

        # Death explosion
        self.explosions.append(Explosion(
            ship.x + ship.width // 2, ship.y, tier=2))
        self.screen_shake.trigger(8, 15)
        self.popup_notifications.append(PopupNotification(
            ship.x + ship.width // 2, ship.y - 30,
            f"P{'1' if player_tag == 'p1' else '2'} DOWN!",
            (255, 80, 80), duration=120))

    def _on_enemy_killed(self, enemy):
        """Override: handle enemy kill with revival check."""
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
        from .entities import XPOrb
        xp_val = getattr(enemy, 'xp_value', 20)
        num_orbs = max(1, xp_val // 10)
        for _ in range(min(num_orbs, 5)):
            self.xp_orbs.append(XPOrb(
                enemy.x + enemy.width // 2 + random.randint(-20, 20),
                enemy.y + random.randint(-20, 20),
                value=max(1, xp_val // num_orbs)))

        # Explosion
        tier = 2 if getattr(enemy, 'is_boss', False) else 0
        self.explosions.append(Explosion(
            enemy.x + enemy.width // 2, enemy.y, tier=tier))

        # Power-up drop
        if random.random() < self.powerup_drop_chance:
            from .entities import PowerUp
            self.powerups.append(PowerUp(
                enemy.x + enemy.width // 2, enemy.y))

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
                    self._collect_powerup(pu)
                    pu.active = False
                    break

        self.powerups = [p for p in self.powerups if p.active]

    def _collect_powerup(self, pu):
        """Collect a powerup — benefits both players."""
        pu_type = getattr(pu, 'powerup_type', 'shield')
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
        for proj in self.projectiles:
            proj.update()
        # Remove off-screen or inactive
        self.projectiles = [p for p in self.projectiles
                            if p.active and
                            math.hypot(p.x - self.camera.x, p.y - self.camera.y) < 2500]

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
        # Check if P1 is the local view — draw arrow to partner
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

        # Draw arrow
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
        """Serialize game state for network transmission to client."""
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
            }

        return {
            'frame': self.survival_frames,
            'p1': ship_data(self.player_ship, self.p1_alive, self.p1_ghost),
            'p2': ship_data(self.partner_ship, self.p2_alive, self.p2_ghost),
            'enemies': [entity_data(e) for e in self.ai_ships[:30]],  # Cap at 30
            'score': self.score,
            'level': self.level,
            'xp': self.xp,
            'xp_to_next': self.xp_to_next,
            'survival_frames': self.survival_frames,
            'game_over': self.game_over,
            'showing_level_up': self.showing_level_up,
            'leash_warning': self.leash_warning,
            'difficulty': self.spawner.get_difficulty_label(),
        }

    def apply_partner_input(self, input_dict):
        """Apply input from the network partner."""
        self.partner_keys.update(input_dict)
