"""
Virtual keyboard input from touch/network, merged with real keyboard.

Translates a dict of key states received over the network or touch overlay
into an object compatible with pygame.key.get_pressed() indexing.
Keyboard events are tracked separately so they work reliably on Emscripten.
"""

import pygame


class VirtualKeys:
    """Translates touch/network input dict to pygame key-like interface.

    Usage:
        vk = VirtualKeys()
        # In event loop: vk.key_event(event.key, True/False)
        # Each frame:
        vk.update({"up": True, "left": True, "shift": False, ...})
        vk.merge_keyboard()
        ship.update(vk)  # Ship.update() calls keys[pygame.K_w] etc.
    """

    # Map from network key names to pygame key constants
    _KEY_MAP = {
        "up": (pygame.K_w, pygame.K_UP),
        "down": (pygame.K_s, pygame.K_DOWN),
        "left": (pygame.K_a, pygame.K_LEFT),
        "right": (pygame.K_d, pygame.K_RIGHT),
        "shift": (pygame.K_LSHIFT, pygame.K_RSHIFT),
        "e": (pygame.K_e,),
        "q": (pygame.K_q,),
    }

    def __init__(self):
        # Combined state (touch + keyboard) — this is what __getitem__ reads
        self._state = [False] * 512
        # Keyboard state tracked from KEYDOWN/KEYUP events (reliable on web)
        self._kb_state = [False] * 512

    def key_event(self, key, pressed):
        """Track a KEYDOWN/KEYUP event (reliable on Emscripten)."""
        if 0 <= key < len(self._kb_state):
            self._kb_state[key] = pressed

    def update(self, input_dict):
        """Update from a network/touch input dict."""
        # Reset combined state
        for i in range(len(self._state)):
            self._state[i] = False
        # Apply touch/network state
        if input_dict:
            for name, pg_keys in self._KEY_MAP.items():
                pressed = input_dict.get(name, False)
                for k in pg_keys:
                    if k < len(self._state):
                        self._state[k] = pressed

    def merge_keyboard(self):
        """OR tracked keyboard state into combined state."""
        # Use event-tracked state (reliable on web)
        for i in range(len(self._state)):
            if self._kb_state[i]:
                self._state[i] = True
        # Also check pygame.key.get_pressed() as backup (works on desktop)
        try:
            real_keys = pygame.key.get_pressed()
            for i in range(min(len(self._state), len(real_keys))):
                if real_keys[i]:
                    self._state[i] = True
        except Exception:
            pass

    def __getitem__(self, key):
        """Allow keys[pygame.K_w] style access."""
        if 0 <= key < len(self._state):
            return self._state[key]
        return False
