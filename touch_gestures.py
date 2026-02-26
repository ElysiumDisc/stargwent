"""
Touch gesture recognition — translates FINGER* events to mouse events.

Recognizes:
  - Tap (< 300ms, < 15px move) -> MOUSEBUTTONDOWN/UP button=1 (left click)
  - Long-press (> 400ms held) -> MOUSEBUTTONDOWN button=3 (right click = card inspect)
  - Drag (> 15px move) -> MOUSEBUTTONDOWN(1) on threshold, MOUSEMOTION, MOUSEBUTTONUP(1) on lift
  - Two-finger scroll -> MOUSEWHEEL from vertical delta

All coordinates are converted from normalized FINGER coords (0.0-1.0) to game-space pixels.
"""

import pygame

# Tuning constants
TAP_MAX_DURATION_MS = 300
TAP_MAX_DISTANCE_PX = 15
LONG_PRESS_THRESHOLD_MS = 400
DRAG_THRESHOLD_PX = 15


class _TouchPoint:
    """Tracks a single finger from FINGERDOWN to FINGERUP."""
    __slots__ = ('finger_id', 'start_x', 'start_y', 'cur_x', 'cur_y',
                 'start_time', 'is_drag', 'long_press_fired')

    def __init__(self, finger_id, x, y, time_ms):
        self.finger_id = finger_id
        self.start_x = x
        self.start_y = y
        self.cur_x = x
        self.cur_y = y
        self.start_time = time_ms
        self.is_drag = False
        self.long_press_fired = False


class TouchGestureRecognizer:
    """Consumes FINGER* events and produces synthetic mouse events."""

    def __init__(self, screen_width, screen_height):
        self.sw = screen_width
        self.sh = screen_height
        self._touches = {}  # finger_id -> _TouchPoint
        self._last_touch_pos = (0, 0)  # for get_pos() on mobile
        # Two-finger scroll tracking
        self._prev_two_finger_y = None

    def resize(self, screen_width, screen_height):
        self.sw = screen_width
        self.sh = screen_height

    def get_last_touch_pos(self):
        return self._last_touch_pos

    def _to_pixels(self, fx, fy):
        """Convert normalized finger coords (0-1) to pixel coords."""
        return int(fx * self.sw), int(fy * self.sh)

    def process_event(self, event):
        """Process a single FINGER* event. Returns list of synthetic pygame events."""
        now = pygame.time.get_ticks()
        synthetic = []

        if event.type == pygame.FINGERDOWN:
            px, py = self._to_pixels(event.x, event.y)
            self._touches[event.finger_id] = _TouchPoint(event.finger_id, px, py, now)
            self._last_touch_pos = (px, py)

            # Two-finger scroll: reset baseline when second finger arrives
            if len(self._touches) == 2:
                self._prev_two_finger_y = self._avg_y()

        elif event.type == pygame.FINGERUP:
            tp = self._touches.pop(event.finger_id, None)
            if tp is None:
                return synthetic

            px, py = self._to_pixels(event.x, event.y)
            self._last_touch_pos = (px, py)
            elapsed = now - tp.start_time
            dist = ((px - tp.start_x) ** 2 + (py - tp.start_y) ** 2) ** 0.5

            if tp.is_drag:
                # End drag
                synthetic.append(self._mouse_event(pygame.MOUSEBUTTONUP, px, py, button=1))
            elif tp.long_press_fired:
                # Long press already sent button=3 down; send up
                synthetic.append(self._mouse_event(pygame.MOUSEBUTTONUP, px, py, button=3))
            elif elapsed < TAP_MAX_DURATION_MS and dist < TAP_MAX_DISTANCE_PX:
                # Tap -> click
                synthetic.append(self._mouse_event(pygame.MOUSEBUTTONDOWN, px, py, button=1))
                synthetic.append(self._mouse_event(pygame.MOUSEBUTTONUP, px, py, button=1))

            if len(self._touches) < 2:
                self._prev_two_finger_y = None

        elif event.type == pygame.FINGERMOTION:
            tp = self._touches.get(event.finger_id)
            if tp is None:
                return synthetic

            px, py = self._to_pixels(event.x, event.y)
            tp.cur_x = px
            tp.cur_y = py
            self._last_touch_pos = (px, py)

            # Two-finger scroll
            if len(self._touches) == 2:
                avg_y = self._avg_y()
                if self._prev_two_finger_y is not None:
                    delta = self._prev_two_finger_y - avg_y
                    if abs(delta) > 2:
                        # Convert pixel delta to scroll units
                        scroll_y = 1 if delta > 0 else -1
                        scroll_ev = pygame.event.Event(
                            pygame.MOUSEWHEEL, x=0, y=scroll_y, flipped=False
                        )
                        synthetic.append(scroll_ev)
                self._prev_two_finger_y = avg_y
                return synthetic  # Don't process drag when two fingers down

            dist = ((px - tp.start_x) ** 2 + (py - tp.start_y) ** 2) ** 0.5

            if not tp.is_drag and dist > DRAG_THRESHOLD_PX:
                tp.is_drag = True
                # Start drag
                synthetic.append(self._mouse_event(pygame.MOUSEBUTTONDOWN, px, py, button=1))

            if tp.is_drag:
                # Continue drag
                rel_x = int(event.dx * self.sw)
                rel_y = int(event.dy * self.sh)
                motion_ev = pygame.event.Event(
                    pygame.MOUSEMOTION,
                    pos=(px, py), rel=(rel_x, rel_y), buttons=(1, 0, 0)
                )
                synthetic.append(motion_ev)

        return synthetic

    def update(self):
        """Call each frame to detect long-press (time-based gesture)."""
        now = pygame.time.get_ticks()
        synthetic = []

        for tp in self._touches.values():
            if tp.long_press_fired or tp.is_drag:
                continue
            elapsed = now - tp.start_time
            dist = ((tp.cur_x - tp.start_x) ** 2 + (tp.cur_y - tp.start_y) ** 2) ** 0.5
            if elapsed >= LONG_PRESS_THRESHOLD_MS and dist < TAP_MAX_DISTANCE_PX:
                tp.long_press_fired = True
                synthetic.append(self._mouse_event(
                    pygame.MOUSEBUTTONDOWN, tp.cur_x, tp.cur_y, button=3
                ))

        return synthetic

    def _avg_y(self):
        """Average Y of all active touches (for two-finger scroll)."""
        if not self._touches:
            return 0
        return sum(tp.cur_y for tp in self._touches.values()) / len(self._touches)

    @staticmethod
    def _mouse_event(event_type, x, y, button=1):
        if event_type == pygame.MOUSEMOTION:
            return pygame.event.Event(event_type, pos=(x, y), rel=(0, 0), buttons=(1, 0, 0))
        return pygame.event.Event(event_type, pos=(x, y), button=button)
