"""Centralized game loop state container.

Houses all mutable state for the main game loop, replacing ~100 local
variables in main() with a single organized object.  Functions extracted
from main() accept ``state: GameLoopState`` instead of long parameter lists.
"""

from __future__ import annotations

import pygame
from dataclasses import dataclass, field
from typing import Any, Optional
from pygame.math import Vector2

# UIState is defined in main.py; import at runtime to avoid circular deps.
# We store it as a generic attribute and let callers pass the correct enum.


def _default_weather() -> dict:
    return {"close": False, "ranged": False, "siege": False}


@dataclass
class GameLoopState:
    """All mutable state for the main game loop."""

    # -- Core game objects (set during initialization, not optional) ---------
    game: Any = None                       # Game instance
    ai_controller: Any = None              # AIController | NetworkController | None
    network_proxy: Any = None              # NetworkPlayerProxy | None
    menu_action: str = ""                  # 'new_game' | 'draft_mode' | 'lan_game'
    unlock_system: Any = None              # CardUnlockSystem
    anim_manager: Any = None               # AnimationManager
    ambient_effects: Any = None            # AmbientBackgroundEffects
    assets: dict = field(default_factory=dict)
    clock: Any = None                      # pygame.time.Clock

    # -- Score tracking ------------------------------------------------------
    prev_p1_score: int = 0
    prev_p2_score: int = 0

    # -- Drag state ----------------------------------------------------------
    selected_card: Any = None
    dragging_card: Any = None
    drag_offset: tuple = (0, 0)
    drag_target_x: int = 0
    drag_target_y: int = 0
    drag_velocity: Vector2 = field(default_factory=Vector2)
    drag_trail: list = field(default_factory=list)
    drag_trail_emit_ms: int = 0
    drag_pickup_flash: float = 0.0
    drag_pulse: float = 0.0
    drag_hover_highlight: Any = None

    # -- Selection / hover ---------------------------------------------------
    hovered_card: Any = None
    card_hover_scale: float = 1.0
    target_hover_scale: float = 1.0
    inspected_card: Any = None
    inspected_leader: Any = None
    keyboard_hand_cursor: int = -1
    keyboard_row_cursor: int = 0
    keyboard_mode_active: bool = False
    keyboard_button_cursor: int = -1

    # -- UI state machine ----------------------------------------------------
    ui_state: Any = None                   # UIState enum, set after init
    button_info_popup: Any = None

    # -- Ability / action state ----------------------------------------------
    medic_card_played: Any = None
    decoy_card_played: Any = None
    ring_transport_animation: Any = None
    ring_transport_selection: bool = False
    ring_transport_button_rect: Optional[pygame.Rect] = None
    decoy_drag_target: Any = None
    decoy_valid_targets: list = field(default_factory=list)
    iris_button_rect: Optional[pygame.Rect] = None
    faction_power_effect: Any = None
    ai_ability_tried: bool = False

    # -- Leader ability state ------------------------------------------------
    vala_cards_to_choose: list = field(default_factory=list)
    catherine_cards_to_choose: list = field(default_factory=list)
    thor_selected_unit: Any = None
    pending_leader_choice: Any = None
    leader_choice_rects: list = field(default_factory=list)
    player_ability_ready: bool = False
    ai_ability_ready: bool = False

    # -- UI button rects (set during rendering, read during events) ----------
    player_leader_rect: Optional[pygame.Rect] = None
    ai_leader_rect: Optional[pygame.Rect] = None
    player_ability_rect: Optional[pygame.Rect] = None
    ai_ability_rect: Optional[pygame.Rect] = None
    player_faction_button_rect: Optional[pygame.Rect] = None
    ai_faction_button_rect: Optional[pygame.Rect] = None
    player_special_button_rect: Optional[pygame.Rect] = None
    player_special_button_kind: Optional[str] = None
    ai_special_button_rect: Optional[pygame.Rect] = None
    ai_special_button_kind: Optional[str] = None
    hud_pass_button_rect: Optional[pygame.Rect] = None
    game_over_buttons: dict = field(default_factory=dict)   # name -> Rect
    pause_menu_buttons: dict = field(default_factory=dict)  # name -> Rect
    overlay_card_rects: list = field(default_factory=list)  # [(card, Rect)] from selection overlays

    # -- History / column state ----------------------------------------------
    history_scroll_offset: int = 0
    history_scroll_limit: int = 0
    history_manual_scroll: bool = False
    history_entry_hitboxes: list = field(default_factory=list)
    history_panel_rect: Optional[pygame.Rect] = None
    discard_scroll: int = 0
    discard_rect: Optional[pygame.Rect] = None
    previous_round: int = 1
    previous_weather: dict = field(default_factory=_default_weather)

    # -- AI turn state -------------------------------------------------------
    ai_turn_anim: Any = None               # AITurnAnimation
    ai_turn_in_progress: bool = False
    ai_card_to_play: Any = None
    ai_row_to_play: Optional[str] = None
    ai_selected_card_index: Optional[int] = None

    # -- LAN state -----------------------------------------------------------
    lan_chat_panel: Any = None
    mulligan_selected: list = field(default_factory=list)
    mulligan_local_done: bool = False
    mulligan_remote_done: bool = False
    waiting_for_opponent: bool = False

    # -- Misc flags ----------------------------------------------------------
    running: bool = True
    fullscreen: bool = False
    debug_overlay_enabled: bool = False
    restart_requested: bool = False
