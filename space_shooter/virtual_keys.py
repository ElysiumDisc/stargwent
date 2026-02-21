"""
Virtual keyboard input from network messages.

Translates a dict of key states received over the network into
an object compatible with pygame.key.get_pressed() indexing.
"""

import pygame


class VirtualKeys:
    """Translates network input dict to pygame key-like interface.

    Usage:
        vk = VirtualKeys()
        vk.update({"up": True, "left": True, "shift": False, ...})
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
        # Internal state array sized to cover all pygame keys
        self._state = [False] * 512

    def update(self, input_dict):
        """Update from a network input dict."""
        # Reset all
        for i in range(len(self._state)):
            self._state[i] = False
        # Apply network state
        if input_dict:
            for name, pg_keys in self._KEY_MAP.items():
                pressed = input_dict.get(name, False)
                for k in pg_keys:
                    if k < len(self._state):
                        self._state[k] = pressed

    def __getitem__(self, key):
        """Allow keys[pygame.K_w] style access."""
        if 0 <= key < len(self._state):
            return self._state[key]
        return False
