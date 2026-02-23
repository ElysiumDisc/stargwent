"""
Co-op Space Shooter Client

Receives state snapshots from the host and renders them locally.
Sends local input to the host each frame.
The client does NOT run game simulation — it's a pure renderer.

Each player has an independent camera following their own ship.
"""

import math
import pygame

from .camera import Camera
from .effects import StarField, ScreenShake
from .ship import Ship


class CoopSpaceShooterClient:
    """Client-side renderer for co-op space shooter.

    Receives state snapshots from the host, interpolates positions,
    and renders the game. Sends local input each frame.
    """

    def __init__(self, screen_width, screen_height, session, local_faction, remote_faction,
                 local_variant=0, remote_variant=0):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.session = session
        self.local_faction = local_faction
        self.remote_faction = remote_faction

        self.running = True
        self.exit_to_menu = False

        # Camera for rendering — follows LOCAL (P2) ship independently
        self.camera = Camera(screen_width, screen_height)

        # Visual effects
        self.starfield = StarField(screen_width, screen_height)
        self.screen_shake = ScreenShake()

        # Fonts
        self.ui_font = pygame.font.SysFont("Arial", 32)
        self.small_font = pygame.font.SysFont("Arial", 24)
        self.tiny_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)

        # Latest state from host
        self.state = None
        self.prev_state = None
        self.interp_t = 0.0

        # Create ship sprites for rendering (faction + variant specific visuals)
        self._p1_ship = Ship(0, 0, remote_faction, is_player=True,
                             screen_width=screen_width, screen_height=screen_height,
                             variant=remote_variant)
        self._p2_ship = Ship(0, 0, local_faction, is_player=True,
                             screen_width=screen_width, screen_height=screen_height,
                             variant=local_variant)

        # Enemy ship cache (faction → Ship template for sprite)
        self._enemy_cache = {}

        # Game over state
        self.game_over = False

        # Host disconnect detection
        self._frames_since_last_state = 0
        self.host_disconnected = False

    def apply_state(self, snapshot):
        """Apply a new state snapshot from the host."""
        self.prev_state = self.state
        self.state = snapshot
        self.interp_t = 0.0
        self.game_over = snapshot.get('game_over', False)
        self._frames_since_last_state = 0

    def get_input_state(self):
        """Capture local keyboard input as a dict for transmission."""
        keys = pygame.key.get_pressed()
        return {
            'up': keys[pygame.K_w] or keys[pygame.K_UP],
            'down': keys[pygame.K_s] or keys[pygame.K_DOWN],
            'left': keys[pygame.K_a] or keys[pygame.K_LEFT],
            'right': keys[pygame.K_d] or keys[pygame.K_RIGHT],
            'shift': keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
            'e': keys[pygame.K_e],
            'q': keys[pygame.K_q],
        }

    def update(self):
        """Advance interpolation between snapshots."""
        self.interp_t = min(1.0, self.interp_t + 1.0 / 3.0)
        self._frames_since_last_state += 1

        # Detect host disconnect (no state for 5 seconds)
        if self._frames_since_last_state > 300 and not self.game_over:
            self.host_disconnected = True

        # Camera follows P2 (local player) independently
        if self.state:
            p2 = self.state.get('p2', {})
            p2_x = p2.get('x', 0)
            p2_y = p2.get('y', 0)
            if p2.get('alive') or p2.get('ghost'):
                self.camera.follow(p2_x, p2_y)
            else:
                # P2 dead and not ghost — follow P1
                p1 = self.state.get('p1', {})
                self.camera.follow(p1.get('x', 0), p1.get('y', 0))

        self.screen_shake.update()

    def draw(self, surface):
        """Render the game state."""
        if self.host_disconnected:
            surface.fill((5, 5, 20))
            text = self.title_font.render("Host Disconnected", True, (255, 80, 80))
            surface.blit(text, text.get_rect(center=(self.screen_width // 2,
                                                      self.screen_height // 2 - 30)))
            hint = self.small_font.render("Press ESC to return to menu", True, (150, 150, 150))
            surface.blit(hint, hint.get_rect(center=(self.screen_width // 2,
                                                      self.screen_height // 2 + 30)))
            return

        if not self.state:
            surface.fill((5, 5, 20))
            text = self.title_font.render("Waiting for host...", True, (150, 150, 200))
            surface.blit(text, text.get_rect(center=(self.screen_width // 2,
                                                      self.screen_height // 2)))
            return

        # Background
        surface.fill((5, 5, 20))
        self.starfield.draw(surface, self.camera)

        state = self.state

        # --- Draw suns ---
        for sun in state.get('suns', []):
            self._draw_sun(surface, sun)

        # --- Draw XP orbs ---
        for orb in state.get('xp_orbs', []):
            sx, sy = self.camera.world_to_screen(orb['x'], orb['y'])
            if -20 < sx < self.screen_width + 20 and -20 < sy < self.screen_height + 20:
                glow_size = 4 + min(orb.get('value', 10) // 5, 6)
                pygame.draw.circle(surface, (200, 200, 255), (int(sx), int(sy)), glow_size)
                pygame.draw.circle(surface, (255, 255, 255), (int(sx), int(sy)), glow_size - 2)

        # --- Draw powerups ---
        for pu in state.get('powerups', []):
            sx, sy = self.camera.world_to_screen(pu['x'], pu['y'])
            if -30 < sx < self.screen_width + 30 and -30 < sy < self.screen_height + 30:
                color = tuple(pu.get('color', (255, 255, 255)))
                rarity = pu.get('rarity', 'common')
                size = 12
                # Draw glow
                glow_color = color + (60,) if len(color) == 3 else color
                glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*color[:3], 60), (size * 2, size * 2), size * 2)
                surface.blit(glow_surf, (int(sx - size * 2), int(sy - size * 2)))
                # Draw core
                pygame.draw.circle(surface, color[:3], (int(sx), int(sy)), size)
                # Rarity border
                if rarity == 'epic':
                    pygame.draw.circle(surface, (180, 80, 255), (int(sx), int(sy)), size + 2, 2)
                elif rarity == 'legendary':
                    pygame.draw.circle(surface, (255, 200, 50), (int(sx), int(sy)), size + 2, 2)

        # --- Draw supergates ---
        for sg in state.get('supergates', []):
            sx, sy = self.camera.world_to_screen(sg['x'], sg['y'])
            if -200 < sx < self.screen_width + 200 and -200 < sy < self.screen_height + 200:
                ring_scale = sg.get('ring_scale', 0)
                if ring_scale > 0.01:
                    r = int(150 * ring_scale)
                    alpha = int(200 * ring_scale)
                    pygame.draw.circle(surface, (100, 150, 255), (int(sx), int(sy)), r, 4)
                    if sg.get('phase', 0) >= 1:  # ACTIVATING or later
                        horizon_r = int(r * 0.75)
                        if horizon_r > 2:
                            horizon_surf = pygame.Surface((horizon_r * 2 + 4, horizon_r * 2 + 4), pygame.SRCALPHA)
                            hc = horizon_r + 2
                            pygame.draw.circle(horizon_surf, (30, 80, 200, 140), (hc, hc), horizon_r)
                            surface.blit(horizon_surf, (int(sx) - hc, int(sy) - hc))
                    # Health bar if damaged
                    sg_hp = sg.get('health', 0)
                    sg_max = sg.get('max_health', 1)
                    if sg_hp < sg_max and sg_max > 0:
                        bar_w = int(r * 1.5)
                        pct = max(0, sg_hp / sg_max)
                        bx = int(sx - bar_w // 2)
                        by = int(sy + r + 8)
                        pygame.draw.rect(surface, (40, 40, 40), (bx, by, bar_w, 6))
                        pygame.draw.rect(surface, (100, 180, 255), (bx, by, int(bar_w * pct), 6))
                        pygame.draw.rect(surface, (80, 80, 80), (bx, by, bar_w, 6), 1)

        # --- Draw Ori beams ---
        for ob in state.get('ori_beams', []):
            if ob.get('active', True):
                bx, by = self.camera.world_to_screen(ob['x'], ob['y'])
                angle = ob.get('angle', 0)
                length = ob.get('length', 1500)
                ex = bx + math.cos(angle) * length
                ey = by + math.sin(angle) * length
                width = ob.get('width', 30)
                pygame.draw.line(surface, (255, 200, 50),
                                (int(bx), int(by)), (int(ex), int(ey)), width + 12)
                pygame.draw.line(surface, (255, 220, 80),
                                (int(bx), int(by)), (int(ex), int(ey)), width)
                pygame.draw.line(surface, (255, 255, 200),
                                (int(bx), int(by)), (int(ex), int(ey)), max(2, width // 3))

        # --- Draw area bombs ---
        for bomb in state.get('area_bombs', []):
            sx, sy = self.camera.world_to_screen(bomb['x'], bomb['y'])
            if -60 < sx < self.screen_width + 60 and -60 < sy < self.screen_height + 60:
                fuse_pct = bomb.get('fuse', 0) / max(1, bomb.get('fuse_duration', 120))
                pulse = 6 + int(fuse_pct * 8)
                pygame.draw.circle(surface, (255, 150, 50), (int(sx), int(sy)), pulse)
                # Warning ring
                warn_r = int(120 * fuse_pct)
                if warn_r > 10:
                    pygame.draw.circle(surface, (255, 100, 50, 100), (int(sx), int(sy)), warn_r, 1)

        # --- Draw asteroids ---
        for ast in state.get('asteroids', []):
            sx, sy = self.camera.world_to_screen(ast['x'], ast['y'])
            if -60 < sx < self.screen_width + 60 and -60 < sy < self.screen_height + 60:
                size = ast.get('size', 30)
                r = size // 2
                pygame.draw.circle(surface, (120, 100, 80), (int(sx), int(sy)), r)
                pygame.draw.circle(surface, (80, 70, 55), (int(sx), int(sy)), r, 2)

        # --- Draw enemies ---
        for enemy in state.get('enemies', []):
            ex, ey = enemy['x'], enemy['y']
            sx, sy = self.camera.world_to_screen(ex, ey)
            if -100 < sx < self.screen_width + 100 and -100 < sy < self.screen_height + 100:
                faction = enemy.get('faction', "Goa'uld")
                if faction not in self._enemy_cache:
                    self._enemy_cache[faction] = Ship(
                        0, 0, faction, is_player=False,
                        screen_width=self.screen_width, screen_height=self.screen_height)
                template = self._enemy_cache[faction]
                img = template.get_image()
                if img:
                    draw_x = int(sx - img.get_width() // 2)
                    draw_y = int(sy - img.get_height() // 2)
                    surface.blit(img, (draw_x, draw_y))
                else:
                    pygame.draw.circle(surface, (255, 80, 80), (int(sx), int(sy)), 10)

                # Health bar above enemy
                hp = enemy.get('health', 0)
                max_hp = enemy.get('max_health', 100)
                if hp < max_hp:
                    bar_w = 30
                    pct = max(0, hp / max_hp)
                    pygame.draw.rect(surface, (40, 40, 40),
                                     (int(sx - bar_w // 2), int(sy - 25), bar_w, 4))
                    pygame.draw.rect(surface, (255, 50, 50),
                                     (int(sx - bar_w // 2), int(sy - 25), int(bar_w * pct), 4))

                # Boss indicator
                if enemy.get('is_boss'):
                    boss_lbl = self.tiny_font.render("BOSS", True, (255, 80, 80))
                    surface.blit(boss_lbl, (int(sx - boss_lbl.get_width() // 2), int(sy - 35)))

        # --- Draw ally ships ---
        for ally in state.get('allies', []):
            sx, sy = self.camera.world_to_screen(ally['x'], ally['y'])
            if -60 < sx < self.screen_width + 60 and -60 < sy < self.screen_height + 60:
                faction = ally.get('faction', "Tau'ri")
                cache_key = f"ally_{faction}"
                if cache_key not in self._enemy_cache:
                    self._enemy_cache[cache_key] = Ship(
                        0, 0, faction, is_player=True,
                        screen_width=self.screen_width, screen_height=self.screen_height)
                template = self._enemy_cache[cache_key]
                img = template.get_image()
                if img:
                    draw_x = int(sx - img.get_width() // 2)
                    draw_y = int(sy - img.get_height() // 2)
                    surface.blit(img, (draw_x, draw_y))
                # ALLY label
                ally_lbl = self.tiny_font.render("ALLY", True, (100, 255, 100))
                surface.blit(ally_lbl, (int(sx - ally_lbl.get_width() // 2), int(sy - 30)))

        # --- Draw projectiles ---
        for proj in state.get('projectiles', []):
            sx, sy = self.camera.world_to_screen(proj['x'], proj['y'])
            if -10 < sx < self.screen_width + 10 and -10 < sy < self.screen_height + 10:
                color = tuple(proj.get('color', (255, 255, 255)))
                if len(color) < 3:
                    color = (255, 255, 255)
                is_player = proj.get('player', False)
                size = 3 if is_player else 2
                pygame.draw.circle(surface, color[:3], (int(sx), int(sy)), size)

        # --- Draw explosions ---
        for exp in state.get('explosions', []):
            sx, sy = self.camera.world_to_screen(exp['x'], exp['y'])
            if -100 < sx < self.screen_width + 100 and -100 < sy < self.screen_height + 100:
                tier = exp.get('tier', 'normal')
                timer = exp.get('timer', 0)
                duration = exp.get('duration', 60)
                progress = min(1.0, timer / max(1, duration))
                base_r = {'small': 15, 'normal': 30, 'large': 50}.get(tier, 30)
                radius = int(base_r * (1.0 - progress * 0.5))
                alpha = int(200 * (1.0 - progress))
                if radius > 0 and alpha > 0:
                    exp_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(exp_surf, (255, 150, 50, alpha),
                                       (radius, radius), radius)
                    surface.blit(exp_surf, (int(sx - radius), int(sy - radius)))

        # --- Draw P1 (host) ---
        p1 = state.get('p1', {})
        self._draw_player_ship(surface, p1, self._p1_ship, "P1")

        # --- Draw P2 (client / local player) ---
        p2 = state.get('p2', {})
        self._draw_player_ship(surface, p2, self._p2_ship, "P2")

        # --- Partner arrow (pointing to P1 when off-screen) ---
        if p1.get('alive') or p1.get('ghost'):
            self._draw_partner_arrow(surface, p1)

        # --- UI ---
        self._draw_ui(surface, state)

        # --- Revival pulse ---
        if state.get('revival_pulse', 0) > 0:
            target = state.get('revival_target')
            if target:
                rship = p1 if target == 'p1' else p2
                sx, sy = self.camera.world_to_screen(rship.get('x', 0), rship.get('y', 0))
                timer = state['revival_pulse']
                radius = int(40 + (30 - timer) * 3)
                alpha = int(200 * timer / 30)
                pulse_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(pulse_surf, (100, 255, 100, alpha),
                                   (radius, radius), radius, 3)
                surface.blit(pulse_surf, (int(sx - radius), int(sy - radius)))

        # Game over overlay
        if state.get('game_over'):
            self._draw_game_over(surface, state)

    def _draw_sun(self, surface, sun_info):
        """Draw a sun/wormhole hazard from snapshot data."""
        sx, sy = self.camera.world_to_screen(sun_info['x'], sun_info['y'])
        if -200 < sx < self.screen_width + 200 and -200 < sy < self.screen_height + 200:
            phase = sun_info.get('phase', 0)
            timer = sun_info.get('timer', 0)
            radius = sun_info.get('radius', 80)

            if phase <= 1:  # GROWING or STABLE
                # Orange sun
                glow_size = min(radius, int(radius * (timer / 60.0))) if phase == 0 else radius
                if glow_size > 0:
                    glow = pygame.Surface((glow_size * 4, glow_size * 4), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (255, 180, 50, 40), (glow_size * 2, glow_size * 2), glow_size * 2)
                    pygame.draw.circle(glow, (255, 200, 80, 80), (glow_size * 2, glow_size * 2), glow_size)
                    surface.blit(glow, (int(sx - glow_size * 2), int(sy - glow_size * 2)))
            elif phase == 2:  # EXPLODING
                flash_size = radius + timer * 5
                flash = pygame.Surface((flash_size * 2, flash_size * 2), pygame.SRCALPHA)
                alpha = max(0, 200 - timer * 6)
                pygame.draw.circle(flash, (255, 255, 255, alpha), (flash_size, flash_size), flash_size)
                surface.blit(flash, (int(sx - flash_size), int(sy - flash_size)))
            elif phase == 3:  # WORMHOLE
                wh_size = radius
                wh = pygame.Surface((wh_size * 4, wh_size * 4), pygame.SRCALPHA)
                pygame.draw.circle(wh, (80, 50, 200, 60), (wh_size * 2, wh_size * 2), wh_size * 2)
                pygame.draw.circle(wh, (100, 80, 255, 100), (wh_size * 2, wh_size * 2), wh_size)
                pygame.draw.circle(wh, (150, 120, 255, 150), (wh_size * 2, wh_size * 2), wh_size // 2)
                surface.blit(wh, (int(sx - wh_size * 2), int(sy - wh_size * 2)))

    def _draw_partner_arrow(self, surface, partner_data):
        """Draw an arrow pointing toward P1 (partner) when off-screen."""
        px, py = partner_data.get('x', 0), partner_data.get('y', 0)
        sx, sy = self.camera.world_to_screen(px, py)

        margin = 60
        if margin < sx < self.screen_width - margin and margin < sy < self.screen_height - margin:
            return

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

        color = (100, 200, 255) if partner_data.get('alive') else (255, 100, 100)
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

        # Distance text
        world_dist = math.hypot(
            partner_data.get('x', 0) - (self.state or {}).get('p2', {}).get('x', 0),
            partner_data.get('y', 0) - (self.state or {}).get('p2', {}).get('y', 0))
        dist_text = self.tiny_font.render(f"{int(world_dist)}px", True, color)
        surface.blit(dist_text, (ax - dist_text.get_width() // 2, ay + 15))

    def _draw_player_ship(self, surface, data, ship_template, label):
        """Draw a player ship from state data."""
        if not data:
            return
        x, y = data.get('x', 0), data.get('y', 0)
        sx, sy = self.camera.world_to_screen(x, y)

        if -100 < sx < self.screen_width + 100 and -100 < sy < self.screen_height + 100:
            facing = tuple(data.get('facing', (1, 0)))
            ship_template.set_facing(facing)
            img = ship_template.get_image()

            if img:
                draw_x = int(sx - img.get_width() // 2)
                draw_y = int(sy - img.get_height() // 2)
                if data.get('ghost'):
                    img = img.copy()
                    img.set_alpha(80)
                elif not data.get('alive'):
                    return  # Don't draw dead (non-ghost) ships
                surface.blit(img, (draw_x, draw_y))

            # Player label
            lbl = self.tiny_font.render(label, True, (200, 200, 200))
            surface.blit(lbl, (int(sx - lbl.get_width() // 2), int(sy - 35)))

    def _draw_ui(self, surface, state):
        """Draw HUD overlay."""
        # CO-OP label
        label = self.tiny_font.render("CO-OP", True, (100, 255, 100))
        surface.blit(label, (self.screen_width // 2 - label.get_width() // 2, 5))

        # P1 health (top-left)
        p1 = state.get('p1', {})
        if p1.get('alive'):
            self._draw_health_bar(surface, p1, 10, 10, "P1")
        elif p1.get('ghost'):
            text = self.tiny_font.render("P1 DOWN — Kill to revive!", True, (255, 80, 80))
            surface.blit(text, (10, 10))

        # P2 health (top-right)
        p2 = state.get('p2', {})
        if p2.get('alive'):
            self._draw_health_bar(surface, p2, self.screen_width - 240, 10, "P2")
        elif p2.get('ghost'):
            text = self.tiny_font.render("P2 DOWN — Kill to revive!", True, (255, 80, 80))
            surface.blit(text, (self.screen_width - text.get_width() - 10, 10))

        # Score / survival
        score_text = self.small_font.render(f"Score: {state.get('score', 0)}", True, (255, 215, 0))
        surface.blit(score_text, (self.screen_width // 2 - score_text.get_width() // 2, 30))

        secs = state.get('survival_frames', 0) / 60.0
        mins = int(secs // 60)
        sec = int(secs % 60)
        time_text = self.tiny_font.render(f"{mins:02d}:{sec:02d}", True, (200, 200, 200))
        surface.blit(time_text, (self.screen_width // 2 - time_text.get_width() // 2, 60))

        # Difficulty
        diff = state.get('difficulty', 'Calm')
        diff_text = self.tiny_font.render(diff, True, (200, 180, 100))
        surface.blit(diff_text, (self.screen_width // 2 - diff_text.get_width() // 2, 80))

        # Level-up waiting
        if state.get('showing_level_up'):
            wait_text = self.small_font.render("Host choosing upgrade...", True, (255, 220, 100))
            surface.blit(wait_text, wait_text.get_rect(
                center=(self.screen_width // 2, self.screen_height // 2)))

        # Active powerups display
        active = state.get('active_powerups', {})
        if active:
            y_offset = 105
            for ptype, timer in list(active.items())[:5]:
                secs_left = timer / 60.0
                pu_text = self.tiny_font.render(f"{ptype}: {secs_left:.0f}s", True, (200, 200, 100))
                surface.blit(pu_text, (self.screen_width // 2 - pu_text.get_width() // 2, y_offset))
                y_offset += 18

        # Latency
        latency = self.session.get_latency() if hasattr(self.session, 'get_latency') else 0
        lat_text = self.tiny_font.render(f"{latency}ms", True, (150, 150, 150))
        surface.blit(lat_text, (self.screen_width - lat_text.get_width() - 10,
                                self.screen_height - 25))

    def _draw_health_bar(self, surface, data, x, y, label):
        """Draw a health/shield bar from state data."""
        bar_w, bar_h = 220, 12

        lbl = self.tiny_font.render(label, True, (200, 200, 200))
        surface.blit(lbl, (x, y))

        hp = data.get('health', 0)
        max_hp = data.get('max_health', 100)
        sh = data.get('shields', 0)
        max_sh = data.get('max_shields', 100)

        # Health
        bar_y = y + 18
        hp_pct = max(0.0, hp / max_hp) if max_hp > 0 else 0
        pygame.draw.rect(surface, (40, 40, 40), (x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, (50, 200, 50), (x, bar_y, int(bar_w * hp_pct), bar_h))
        pygame.draw.rect(surface, (100, 100, 100), (x, bar_y, bar_w, bar_h), 1)

        # Shields
        bar_y += bar_h + 2
        sh_pct = max(0.0, sh / max_sh) if max_sh > 0 else 0
        pygame.draw.rect(surface, (40, 40, 40), (x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, (50, 130, 255), (x, bar_y, int(bar_w * sh_pct), bar_h))
        pygame.draw.rect(surface, (100, 100, 100), (x, bar_y, bar_w, bar_h), 1)

    def _draw_game_over(self, surface, state):
        """Draw game over overlay."""
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        title = self.title_font.render("GAME OVER", True, (255, 80, 80))
        surface.blit(title, title.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2 - 60)))

        score = state.get('score', 0)
        score_text = self.ui_font.render(f"Combined Score: {score}", True, (255, 215, 0))
        surface.blit(score_text, score_text.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2 + 10)))

        secs = state.get('survival_frames', 0) / 60.0
        mins = int(secs // 60)
        sec = int(secs % 60)
        time_text = self.small_font.render(f"Survived: {mins:02d}:{sec:02d}", True, (200, 200, 200))
        surface.blit(time_text, time_text.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2 + 50)))

        hint = self.small_font.render("Press ESC to exit", True, (150, 150, 150))
        surface.blit(hint, hint.get_rect(
            center=(self.screen_width // 2, self.screen_height // 2 + 100)))
