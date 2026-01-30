"""
Input Manager Module (v4.3.1)

Centralized input handling for cleaner event loops and easier key rebinding.
Processes all pygame events in one place and provides a clean API for checking input states.

Enhanced Keyboard Controls (Gwent-style):
    E / Enter     - Confirm / Play selected card
    X             - Activate leader ability
    Q / Escape    - Close overlay / Surrender (in pause menu)
    Space         - Pass turn
    Arrow Keys    - Navigate cards in hand
    Tab           - Switch between rows
    1 / 2 / 3     - Select row (close / ranged / siege)
    F             - Toggle fullscreen
    P             - Pause game
"""

import pygame
from typing import Set, Tuple, Optional, Dict


# ============================================================================
# KEY BINDING CONFIGURATION
# ============================================================================
class KeyBindings:
    """Configurable key bindings for game actions.

    All bindings can be customized by modifying this class.
    Multiple keys can be assigned to the same action.
    """
    # Confirmation / Selection
    CONFIRM = [pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER]
    PLAY_CARD = [pygame.K_RETURN, pygame.K_KP_ENTER]

    # Navigation
    NAV_LEFT = [pygame.K_LEFT, pygame.K_a]
    NAV_RIGHT = [pygame.K_RIGHT, pygame.K_d]
    NAV_UP = [pygame.K_UP, pygame.K_w]
    NAV_DOWN = [pygame.K_DOWN, pygame.K_s]

    # Row selection (direct)
    SELECT_ROW_CLOSE = [pygame.K_1, pygame.K_KP1]
    SELECT_ROW_RANGED = [pygame.K_2, pygame.K_KP2]
    SELECT_ROW_SIEGE = [pygame.K_3, pygame.K_KP3]

    # Tab to cycle rows
    CYCLE_ROW = [pygame.K_TAB]

    # Game actions
    PASS_TURN = [pygame.K_SPACE]
    LEADER_ABILITY = [pygame.K_x]
    FACTION_POWER = [pygame.K_c]

    # Menu / System
    CANCEL = [pygame.K_ESCAPE, pygame.K_q]
    PAUSE = [pygame.K_p, pygame.K_ESCAPE]
    SURRENDER = [pygame.K_q]  # Only in pause menu
    FULLSCREEN = [pygame.K_f, pygame.K_F11]

    # Debug
    TOGGLE_FPS = [pygame.K_F3]
    DEBUG_INFO = [pygame.K_F1]


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

    # ========================================================================
    # GAME ACTION HELPERS (Using KeyBindings)
    # ========================================================================

    def confirm_pressed(self) -> bool:
        """Check if confirm action triggered (E, Enter)."""
        return self.any_key_pressed(*KeyBindings.CONFIRM)

    def play_card_pressed(self) -> bool:
        """Check if play card action triggered (Enter)."""
        return self.any_key_pressed(*KeyBindings.PLAY_CARD)

    def cancel_pressed(self) -> bool:
        """Check if cancel action triggered (Escape, Q)."""
        return self.any_key_pressed(*KeyBindings.CANCEL)

    def pass_turn_pressed(self) -> bool:
        """Check if pass turn action triggered (Space)."""
        return self.any_key_pressed(*KeyBindings.PASS_TURN)

    def leader_ability_pressed(self) -> bool:
        """Check if leader ability action triggered (X)."""
        return self.any_key_pressed(*KeyBindings.LEADER_ABILITY)

    def faction_power_pressed(self) -> bool:
        """Check if faction power action triggered (C)."""
        return self.any_key_pressed(*KeyBindings.FACTION_POWER)

    def pause_pressed(self) -> bool:
        """Check if pause action triggered (P, Escape)."""
        return self.any_key_pressed(*KeyBindings.PAUSE)

    def fullscreen_pressed(self) -> bool:
        """Check if fullscreen toggle triggered (F, F11)."""
        return self.any_key_pressed(*KeyBindings.FULLSCREEN)

    def surrender_pressed(self) -> bool:
        """Check if surrender action triggered (Q) - only valid in pause menu."""
        return self.any_key_pressed(*KeyBindings.SURRENDER)

    def toggle_fps_pressed(self) -> bool:
        """Check if FPS toggle triggered (F3)."""
        return self.any_key_pressed(*KeyBindings.TOGGLE_FPS)

    # Navigation helpers

    def nav_left_pressed(self) -> bool:
        """Check if navigate left triggered (Left, A)."""
        return self.any_key_pressed(*KeyBindings.NAV_LEFT)

    def nav_right_pressed(self) -> bool:
        """Check if navigate right triggered (Right, D)."""
        return self.any_key_pressed(*KeyBindings.NAV_RIGHT)

    def nav_up_pressed(self) -> bool:
        """Check if navigate up triggered (Up, W)."""
        return self.any_key_pressed(*KeyBindings.NAV_UP)

    def nav_down_pressed(self) -> bool:
        """Check if navigate down triggered (Down, S)."""
        return self.any_key_pressed(*KeyBindings.NAV_DOWN)

    def cycle_row_pressed(self) -> bool:
        """Check if row cycle triggered (Tab)."""
        return self.any_key_pressed(*KeyBindings.CYCLE_ROW)

    def select_row_close_pressed(self) -> bool:
        """Check if close row selected (1)."""
        return self.any_key_pressed(*KeyBindings.SELECT_ROW_CLOSE)

    def select_row_ranged_pressed(self) -> bool:
        """Check if ranged row selected (2)."""
        return self.any_key_pressed(*KeyBindings.SELECT_ROW_RANGED)

    def select_row_siege_pressed(self) -> bool:
        """Check if siege row selected (3)."""
        return self.any_key_pressed(*KeyBindings.SELECT_ROW_SIEGE)

    def get_selected_row(self) -> Optional[str]:
        """Get directly selected row if any number key pressed.

        Returns:
            "close", "ranged", "siege", or None
        """
        if self.select_row_close_pressed():
            return "close"
        if self.select_row_ranged_pressed():
            return "ranged"
        if self.select_row_siege_pressed():
            return "siege"
        return None

    def get_navigation_direction(self) -> Tuple[int, int]:
        """Get navigation direction as (dx, dy) tuple.

        Returns:
            (dx, dy) where:
            - dx: -1 (left), 0 (none), 1 (right)
            - dy: -1 (up), 0 (none), 1 (down)
        """
        dx = 0
        dy = 0

        if self.nav_left_pressed():
            dx = -1
        elif self.nav_right_pressed():
            dx = 1

        if self.nav_up_pressed():
            dy = -1
        elif self.nav_down_pressed():
            dy = 1

        return (dx, dy)


# Singleton instance for easy global access (optional)
_input_manager_instance: Optional[InputManager] = None


def get_input_manager() -> InputManager:
    """Get the singleton InputManager instance."""
    global _input_manager_instance
    if _input_manager_instance is None:
        _input_manager_instance = InputManager()
    return _input_manager_instance


def get_key_bindings() -> KeyBindings:
    """Get the key bindings configuration."""
    return KeyBindings
