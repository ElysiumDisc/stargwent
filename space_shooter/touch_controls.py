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
        # Pre-render the static ring
        size = int(radius * 2 + 4)
        self._ring_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self._ring_surf, (255, 255, 255, 60),
                          (size // 2, size // 2), int(radius), 2)
        self._knob_r = max(8, int(radius * 0.25))
        knob_d = self._knob_r * 2 + 2
        self._knob_surf = pygame.Surface((knob_d, knob_d), pygame.SRCALPHA)
        pygame.draw.circle(self._knob_surf, (200, 200, 255, 100),
                          (knob_d // 2, knob_d // 2), self._knob_r)

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
        # Blit pre-rendered ring
        rs = self._ring_surf
        surface.blit(rs, (int(self.cx - rs.get_width() // 2),
                         int(self.cy - rs.get_height() // 2)))
        # Blit knob at current position
        knob_x = int(self.cx + self.dx * self.radius * 0.6)
        knob_y = int(self.cy + self.dy * self.radius * 0.6)
        ks = self._knob_surf
        surface.blit(ks, (knob_x - ks.get_width() // 2,
                         knob_y - ks.get_height() // 2))


_button_font_cache = {}


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
        # Pre-render both states (pressed and unpressed)
        self._surfs = {}
        for pressed_state in (False, True):
            self._surfs[pressed_state] = self._render_button(radius, label, pressed_state)

    def _render_button(self, radius, label, pressed):
        size = int(radius * 2 + 4)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        fill = (100, 200, 100, 120) if pressed else (80, 80, 120, 80)
        pygame.draw.circle(surf, fill, (center, center), int(radius))
        pygame.draw.circle(surf, (200, 200, 255, 100),
                          (center, center), int(radius), 2)
        font_size = max(12, int(radius * 0.6))
        if font_size not in _button_font_cache:
            _button_font_cache[font_size] = pygame.font.SysFont("Arial", font_size, bold=True)
        font = _button_font_cache[font_size]
        text = font.render(label, True, (220, 220, 255))
        surf.blit(text, (center - text.get_width() // 2,
                        center - text.get_height() // 2))
        return surf

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
        surf = self._surfs[self.pressed]
        surface.blit(surf, (int(self.cx - surf.get_width() // 2),
                           int(self.cy - surf.get_height() // 2)))


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
            "up": dy < -0.15,
            "down": dy > 0.15,
            "left": dx < -0.15,
            "right": dx > 0.15,
            "shift": False,
            "e": False,
            "q": False,
        }
        for btn in self.buttons:
            if btn.pressed:
                keys[btn.key_name] = True
        return keys

    def draw(self, surface):
        """Draw pre-cached touch controls (small SRCALPHA blits, not full-screen)."""
        self.joystick.draw(surface)
        for btn in self.buttons:
            btn.draw(surface)
