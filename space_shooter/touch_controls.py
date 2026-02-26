"""
Touch controls for the space shooter — virtual joystick and action buttons.

- VirtualJoystick: bottom-left circular pad, outputs dx/dy [-1,1]
- TouchActionButton: individual action buttons (fire, wormhole, boost)
- SpaceShooterTouchOverlay: multi-touch orchestrator that assigns finger IDs
"""

import math
import pygame
from .virtual_keys import VirtualKeys


class VirtualJoystick:
    """Circular touch joystick returning (dx, dy) in [-1, 1]."""

    def __init__(self, center_x, center_y, radius):
        self.cx = center_x
        self.cy = center_y
        self.radius = radius
        self.dead_zone = 0.15  # fraction of radius
        self.finger_id = None
        self.dx = 0.0
        self.dy = 0.0

    def handle_down(self, finger_id, x, y):
        dist = math.hypot(x - self.cx, y - self.cy)
        if dist <= self.radius * 1.5:  # generous touch area
            self.finger_id = finger_id
            self._update_axis(x, y)
            return True
        return False

    def handle_move(self, finger_id, x, y):
        if finger_id == self.finger_id:
            self._update_axis(x, y)
            return True
        return False

    def handle_up(self, finger_id):
        if finger_id == self.finger_id:
            self.finger_id = None
            self.dx = 0.0
            self.dy = 0.0
            return True
        return False

    def _update_axis(self, x, y):
        ox = (x - self.cx) / self.radius
        oy = (y - self.cy) / self.radius
        mag = math.hypot(ox, oy)
        if mag < self.dead_zone:
            self.dx = 0.0
            self.dy = 0.0
        else:
            # Clamp to unit circle
            if mag > 1.0:
                ox /= mag
                oy /= mag
            self.dx = ox
            self.dy = oy

    def draw(self, surface):
        # Outer ring
        pygame.draw.circle(surface, (255, 255, 255, 60),
                          (int(self.cx), int(self.cy)), int(self.radius), 2)
        # Inner knob
        knob_x = int(self.cx + self.dx * self.radius * 0.6)
        knob_y = int(self.cy + self.dy * self.radius * 0.6)
        knob_r = max(8, int(self.radius * 0.25))
        pygame.draw.circle(surface, (200, 200, 255, 100),
                          (knob_x, knob_y), knob_r)


class TouchActionButton:
    """A circular touch button for an action (fire, wormhole, boost)."""

    def __init__(self, center_x, center_y, radius, label, key_name):
        self.cx = center_x
        self.cy = center_y
        self.radius = radius
        self.label = label
        self.key_name = key_name  # "e", "q", or "shift"
        self.finger_id = None
        self.pressed = False

    def handle_down(self, finger_id, x, y):
        dist = math.hypot(x - self.cx, y - self.cy)
        if dist <= self.radius * 1.3:
            self.finger_id = finger_id
            self.pressed = True
            return True
        return False

    def handle_up(self, finger_id):
        if finger_id == self.finger_id:
            self.finger_id = None
            self.pressed = False
            return True
        return False

    def draw(self, surface):
        color = (100, 200, 100, 120) if self.pressed else (80, 80, 120, 80)
        pygame.draw.circle(surface, color,
                          (int(self.cx), int(self.cy)), int(self.radius))
        pygame.draw.circle(surface, (200, 200, 255, 100),
                          (int(self.cx), int(self.cy)), int(self.radius), 2)
        font = pygame.font.SysFont("Arial", max(12, int(self.radius * 0.6)), bold=True)
        text = font.render(self.label, True, (220, 220, 255))
        surface.blit(text, (int(self.cx - text.get_width() // 2),
                           int(self.cy - text.get_height() // 2)))


class SpaceShooterTouchOverlay:
    """Multi-touch orchestrator for the space shooter.

    Assigns each finger to either the joystick or an action button.
    Produces a keys dict compatible with VirtualKeys.update().
    """

    def __init__(self, screen_width, screen_height):
        sw, sh = screen_width, screen_height
        pad = int(sw * 0.08)
        joy_r = int(min(sw, sh) * 0.10)
        btn_r = int(min(sw, sh) * 0.055)

        # Joystick bottom-left
        self.joystick = VirtualJoystick(
            pad + joy_r, sh - pad - joy_r, joy_r
        )

        # Action buttons bottom-right cluster
        btn_base_x = sw - pad - btn_r
        btn_base_y = sh - pad - btn_r
        spacing = int(btn_r * 2.6)

        self.buttons = [
            TouchActionButton(btn_base_x, btn_base_y - spacing, btn_r, "FIRE", "e"),
            TouchActionButton(btn_base_x - spacing, btn_base_y, btn_r, "WARP", "q"),
            TouchActionButton(btn_base_x, btn_base_y, btn_r, "BOOST", "shift"),
        ]

        self._overlay_surface = None

    def handle_event(self, event):
        """Process a FINGER* event. Returns True if consumed."""
        if event.type == pygame.FINGERDOWN:
            # Convert normalized coords to pixels
            x, y = self._to_px(event.x, event.y)
            fid = event.finger_id
            if self.joystick.handle_down(fid, x, y):
                return True
            for btn in self.buttons:
                if btn.handle_down(fid, x, y):
                    return True
            return False

        elif event.type == pygame.FINGERMOTION:
            x, y = self._to_px(event.x, event.y)
            fid = event.finger_id
            if self.joystick.handle_move(fid, x, y):
                return True
            return False

        elif event.type == pygame.FINGERUP:
            fid = event.finger_id
            if self.joystick.handle_up(fid):
                return True
            for btn in self.buttons:
                if btn.handle_up(fid):
                    return True
            return False

        return False

    def _to_px(self, fx, fy):
        """Normalized finger coords -> screen pixels."""
        import display_manager
        sw = display_manager.SCREEN_WIDTH or 1280
        sh = display_manager.SCREEN_HEIGHT or 720
        return int(fx * sw), int(fy * sh)

    def get_virtual_keys_dict(self):
        """Return a dict matching VirtualKeys.update() format."""
        dx = self.joystick.dx
        dy = self.joystick.dy
        keys = {
            "up": dy < -0.3,
            "down": dy > 0.3,
            "left": dx < -0.3,
            "right": dx > 0.3,
            "shift": False,
            "e": False,
            "q": False,
        }
        for btn in self.buttons:
            if btn.pressed:
                keys[btn.key_name] = True
        return keys

    def draw(self, surface):
        """Draw semi-transparent overlay controls."""
        # Create transparent overlay
        if (self._overlay_surface is None or
                self._overlay_surface.get_size() != surface.get_size()):
            self._overlay_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        self._overlay_surface.fill((0, 0, 0, 0))
        self.joystick.draw(self._overlay_surface)
        for btn in self.buttons:
            btn.draw(self._overlay_surface)
        surface.blit(self._overlay_surface, (0, 0))
