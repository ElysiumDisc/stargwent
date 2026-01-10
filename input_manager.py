"""
Input Manager Module (v4.3.1)

Centralized input handling for cleaner event loops and easier key rebinding.
Processes all pygame events in one place and provides a clean API for checking input states.
"""

import pygame
from typing import Set, Tuple, Optional, Dict


class InputManager:
    """
    Centralized input manager for mouse and keyboard events.

    Benefits:
    - Cleaner event loop in main.py
    - Single source of truth for input state
    - Easier to add key rebinding in the future
    - Better preparation for controller support
    """

    def __init__(self):
        # Mouse state
        self.mouse_pos: Tuple[int, int] = (0, 0)
        self.mouse_buttons: Dict[int, bool] = {1: False, 2: False, 3: False}  # left, middle, right
        self.mouse_button_pressed: Dict[int, bool] = {1: False, 2: False, 3: False}
        self.mouse_button_released: Dict[int, bool] = {1: False, 2: False, 3: False}
        self.mouse_wheel_y = 0

        # Keyboard state
        self.keys_held: Set[int] = set()
        self.keys_pressed: Set[int] = set()  # Keys pressed this frame
        self.keys_released: Set[int] = set()  # Keys released this frame

        # Text input for chat/input fields
        self.text_input: str = ""

        # Window events
        self.quit_requested: bool = False
        self.window_resized: bool = False
        self.window_size: Tuple[int, int] = (0, 0)

    def update(self, events):
        """
        Process all pygame events for this frame.
        Call this once per frame at the beginning of the game loop.

        Args:
            events: List of pygame events from pygame.event.get()
        """
        # Reset frame-specific states
        self.keys_pressed.clear()
        self.keys_released.clear()
        self.mouse_button_pressed = {1: False, 2: False, 3: False}
        self.mouse_button_released = {1: False, 2: False, 3: False}
        self.mouse_wheel_y = 0
        self.text_input = ""
        self.quit_requested = False
        self.window_resized = False

        # Update mouse position (always track even if no events)
        self.mouse_pos = pygame.mouse.get_pos()

        # Process events
        for event in events:
            if event.type == pygame.QUIT:
                self.quit_requested = True

            elif event.type == pygame.KEYDOWN:
                self.keys_held.add(event.key)
                self.keys_pressed.add(event.key)

            elif event.type == pygame.KEYUP:
                self.keys_held.discard(event.key)
                self.keys_released.add(event.key)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button <= 3:
                    self.mouse_buttons[event.button] = True
                    self.mouse_button_pressed[event.button] = True

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button <= 3:
                    self.mouse_buttons[event.button] = False
                    self.mouse_button_released[event.button] = True

            elif event.type == pygame.MOUSEWHEEL:
                self.mouse_wheel_y = event.y

            elif event.type == pygame.TEXTINPUT:
                self.text_input = event.text

            elif event.type == pygame.VIDEORESIZE:
                self.window_resized = True
                self.window_size = (event.w, event.h)

    # Convenience methods for common checks

    def left_click_pressed(self) -> bool:
        """Check if left mouse button was just pressed this frame."""
        return self.mouse_button_pressed[1]

    def left_click_released(self) -> bool:
        """Check if left mouse button was just released this frame."""
        return self.mouse_button_released[1]

    def left_click_held(self) -> bool:
        """Check if left mouse button is currently held down."""
        return self.mouse_buttons[1]

    def right_click_pressed(self) -> bool:
        """Check if right mouse button was just pressed this frame."""
        return self.mouse_button_pressed[3]

    def right_click_released(self) -> bool:
        """Check if right mouse button was just released this frame."""
        return self.mouse_button_released[3]

    def key_pressed(self, key: int) -> bool:
        """Check if a key was just pressed this frame."""
        return key in self.keys_pressed

    def key_released(self, key: int) -> bool:
        """Check if a key was just released this frame."""
        return key in self.keys_released

    def key_held(self, key: int) -> bool:
        """Check if a key is currently held down."""
        return key in self.keys_held

    def any_key_pressed(self, *keys: int) -> bool:
        """Check if any of the given keys were pressed this frame."""
        return any(k in self.keys_pressed for k in keys)

    def all_keys_held(self, *keys: int) -> bool:
        """Check if all of the given keys are currently held."""
        return all(k in self.keys_held for k in keys)

    def get_mouse_pos(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return self.mouse_pos

    def is_mouse_over(self, rect: pygame.Rect) -> bool:
        """Check if mouse is over a given rectangle."""
        return rect.collidepoint(self.mouse_pos)

    def clear(self):
        """Clear all input state (useful for state transitions)."""
        self.keys_held.clear()
        self.keys_pressed.clear()
        self.keys_released.clear()
        self.mouse_buttons = {1: False, 2: False, 3: False}
        self.mouse_button_pressed = {1: False, 2: False, 3: False}
        self.mouse_button_released = {1: False, 2: False, 3: False}
        self.mouse_wheel_y = 0
        self.text_input = ""


# Singleton instance for easy global access (optional)
_input_manager_instance: Optional[InputManager] = None

def get_input_manager() -> InputManager:
    """Get the singleton InputManager instance."""
    global _input_manager_instance
    if _input_manager_instance is None:
        _input_manager_instance = InputManager()
    return _input_manager_instance
