"""
Co-op Space Shooter Client

Receives state snapshots from the host and renders them locally.
Sends local input to the host each frame.
The client does NOT run game simulation — it's a pure renderer.
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

    def __init__(self, screen_width, screen_height, session, local_faction, remote_faction):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.session = session
        self.local_faction = local_faction
        self.remote_faction = remote_faction

        self.running = True
        self.exit_to_menu = False

        # Camera for rendering
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
        self.interp_t = 0.0  # Interpolation progress between snapshots

        # Create ship sprites for rendering (faction-specific visuals)
        self._p1_ship = Ship(0, 0, remote_faction, is_player=True,
                             screen_width=screen_width, screen_height=screen_height)
        self._p2_ship = Ship(0, 0, local_faction, is_player=True,
                             screen_width=screen_width, screen_height=screen_height)

        # Enemy ship cache (faction → Ship template for sprite)
        self._enemy_cache = {}

        # Game over state
        self.game_over = False

    def apply_state(self, snapshot):
        """Apply a new state snapshot from the host."""
        self.prev_state = self.state
        self.state = snapshot
        self.interp_t = 0.0
        self.game_over = snapshot.get('game_over', False)

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
        # Smooth interpolation toward latest snapshot (3 frames between snapshots)
        self.interp_t = min(1.0, self.interp_t + 1.0 / 3.0)

        # Update camera based on P2 (local player) position
        if self.state:
            p2 = self.state.get('p2', {})
            p1 = self.state.get('p1', {})
            p2_x = p2.get('x', 0)
            p2_y = p2.get('y', 0)
            p1_x = p1.get('x', 0)
            p1_y = p1.get('y', 0)
            # Camera follows midpoint like host
            if p1.get('alive') and p2.get('alive'):
                self.camera.follow_midpoint(p1_x, p1_y, p2_x, p2_y)
            elif p2.get('alive'):
                self.camera.follow(p2_x, p2_y)
            elif p1.get('alive'):
                self.camera.follow(p1_x, p1_y)

        self.screen_shake.update()

    def draw(self, surface):
        """Render the game state."""
        if not self.state:
            # Waiting for first snapshot
            surface.fill((5, 5, 20))
            text = self.title_font.render("Waiting for host...", True, (150, 150, 200))
            surface.blit(text, text.get_rect(center=(self.screen_width // 2,
                                                      self.screen_height // 2)))
            return

        # Background
        surface.fill((5, 5, 20))
        self.starfield.draw(surface, self.camera)

        state = self.state

        # Draw enemies
        for enemy in state.get('enemies', []):
            ex, ey = enemy['x'], enemy['y']
            sx, sy = self.camera.world_to_screen(ex, ey)
            if -100 < sx < self.screen_width + 100 and -100 < sy < self.screen_height + 100:
                # Get or create enemy sprite
                faction = enemy.get('faction', 'Goa\'uld')
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

        # Draw P1 (host)
        p1 = state.get('p1', {})
        self._draw_player_ship(surface, p1, self._p1_ship, "P1")

        # Draw P2 (client / local player)
        p2 = state.get('p2', {})
        self._draw_player_ship(surface, p2, self._p2_ship, "P2")

        # --- UI ---
        self._draw_ui(surface, state)

        # Game over overlay
        if state.get('game_over'):
            self._draw_game_over(surface, state)

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
            text = self.tiny_font.render("P1 DOWN", True, (255, 80, 80))
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

        # Leash warning
        if state.get('leash_warning'):
            warn = self.small_font.render("TOO FAR APART!", True, (255, 200, 50))
            surface.blit(warn, (self.screen_width // 2 - warn.get_width() // 2, 100))

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
