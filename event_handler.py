"""Event handling for the main game loop.

Extracted from main.py to reduce its size. All event processing
(keyboard, mouse, UI interactions) is handled here.
"""

import sys
import pygame
from pygame.math import Vector2
import game_config as cfg
import display_manager
import battle_music
import board_renderer
import transitions
import selection_overlays
from game_settings import get_settings
from abilities import Ability, has_ability, is_hero, is_spy, is_medic
from animations import (
    StargateActivationEffect,
    NaquadahExplosionEffect,
    LegendaryLightningEffect,
    ClearWeatherBlackHole,
    MeteorShowerImpactEffect,
    HathorStealAnimation,
    IrisClosingEffect,
    create_hero_animation,
    create_ability_animation,
)
from power import FactionPowerEffect
from deck_persistence import get_persistence
from draft_mode import DraftRun


def handle_events(state, game, screen, dt):
    """Process all pygame events for the current frame.

    Args:
        state: GameLoopState containing all mutable game loop state.
        game: The Game instance (alias for state.game).
        screen: The pygame display surface.
        dt: Delta time in milliseconds since last frame.
    """
    # Import main module for globals/functions that live there
    import main as _main

    # Convenience aliases for frequently used values
    SCREEN_WIDTH = display_manager.SCREEN_WIDTH
    SCREEN_HEIGHT = display_manager.SCREEN_HEIGHT
    SCALE_FACTOR = display_manager.SCALE_FACTOR
    HUD_LEFT = cfg.HUD_LEFT
    HUD_WIDTH = cfg.HUD_WIDTH
    HAND_Y_OFFSET = SCREEN_HEIGHT - cfg.player_hand_area_y
    WEATHER_SLOT_RECTS = cfg.WEATHER_SLOT_RECTS
    PLAYER_HORN_SLOT_RECTS = cfg.PLAYER_HORN_SLOT_RECTS
    UIState = _main.UIState
    LAN_MODE = _main.LAN_MODE
    LAN_CONTEXT = _main.LAN_CONTEXT
    pct_y = cfg.pct_y
    add_special_card_effect = _main.add_special_card_effect
    toggle_fullscreen_mode = _main.toggle_fullscreen_mode
    build_button_info_popup = _main.build_button_info_popup

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            state.running = False
        elif event.type == pygame.KEYDOWN:
            # Handle chat input in LAN mode FIRST (takes priority except for ESC and F11)
            if state.lan_chat_panel and state.lan_chat_panel.active and event.key not in (pygame.K_ESCAPE, pygame.K_F11, pygame.K_F3):
                state.lan_chat_panel.handle_event(event)
                continue  # Skip other key handlers when typing in chat

            # F3 - Toggle debug overlay (zone boundaries + FPS counter)
            if event.key == pygame.K_F3:
                # Toggle debug/FPS
                DEBUG_MODE = not DEBUG_MODE
                get_settings().set_show_fps(DEBUG_MODE)

            # ESC to toggle pause menu or close overlays
            if event.key == pygame.K_ESCAPE:
                if state.inspected_card or state.inspected_leader:
                    state.inspected_card = None
                    state.inspected_leader = None
                elif state.ui_state == UIState.DISCARD_VIEW:
                    state.ui_state = UIState.PLAYING
                    state.discard_scroll = 0
                elif state.ui_state == UIState.JONAS_PEEK:
                    state.ui_state = UIState.PLAYING
                    # Clear the tracked cards after viewing
                    game.opponent_drawn_cards = []
                elif state.ui_state == UIState.LAN_CHAT:
                    state.ui_state = UIState.PLAYING
                elif game.game_state == "playing":
                    if state.ui_state == UIState.PAUSED:
                        state.ui_state = UIState.PLAYING
                    else:
                        state.ui_state = UIState.PAUSED

            # Q to surrender in pause menu
            elif event.key == pygame.K_q:
                if state.ui_state == UIState.PAUSED and game.game_state == "playing":
                    game.surrender(game.player1)
                    state.ui_state = UIState.GAME_OVER

            # Toggle fullscreen with F11
            elif event.key == pygame.K_F11:
                toggle_fullscreen_mode()
                state.fullscreen = display_manager.FULLSCREEN

                # Recalculate UI button positions for new resolution
                hud_pass_button_size = max(80, int(SCREEN_HEIGHT * 0.04))
                state.hud_pass_button_rect = pygame.Rect(
                    HUD_LEFT + (HUD_WIDTH - hud_pass_button_size) // 2,
                    pct_y(0.94) - hud_pass_button_size // 2,
                    hud_pass_button_size,
                    hud_pass_button_size
                )
                cfg.MULLIGAN_BUTTON_RECT = pygame.Rect(
                    SCREEN_WIDTH - int(300 * SCALE_FACTOR),
                    SCREEN_HEIGHT - int(160 * SCALE_FACTOR),
                    int(200 * SCALE_FACTOR),
                    int(50 * SCALE_FACTOR)
                )

            # F key = Play keyboard-selected or hovered card to its default row
            elif event.key == pygame.K_f:
                if game.game_state == "playing" and game.current_player == game.player1 and state.ui_state == UIState.PLAYING:
                    # Get card to play: keyboard-selected or hovered
                    card_to_play = None
                    if state.keyboard_mode_active and state.keyboard_hand_cursor >= 0 and state.keyboard_hand_cursor < len(game.player1.hand):
                        card_to_play = game.player1.hand[state.keyboard_hand_cursor]
                    elif state.hovered_card and state.hovered_card in game.player1.hand:
                        card_to_play = state.hovered_card

                    if card_to_play:
                        # Determine default row
                        if card_to_play.row in ("close", "ranged", "siege"):
                            target_row = card_to_play.row
                        elif card_to_play.row == "agile":
                            target_row = "close"  # Default agile to close
                        elif card_to_play.row == "weather":
                            target_row = "close"  # Default weather to close row
                        elif card_to_play.row == "special":
                            # Special cards need specific handling
                            if has_ability(card_to_play, Ability.RING_TRANSPORT):
                                target_row = None  # Skip - needs drag
                            elif has_ability(card_to_play, Ability.WORMHOLE_STABILIZATION):
                                target_row = "weather"
                            elif has_ability(card_to_play, Ability.COMMAND_NETWORK):
                                target_row = "close"  # Default horn to close
                            else:
                                target_row = "special"
                        else:
                            target_row = card_to_play.row

                        if target_row:
                            game.play_card(card_to_play, target_row)
                            row_rect = cfg.PLAYER_ROW_RECTS.get(target_row)
                            if row_rect:
                                state.anim_manager.add_effect(StargateActivationEffect(row_rect.centerx, row_rect.centery, duration=cfg.ANIM_STARGATE))
                            if state.network_proxy:
                                state.network_proxy.send_play_card(card_to_play.id, target_row)
                            # Reset keyboard cursor
                            state.keyboard_hand_cursor = min(state.keyboard_hand_cursor, len(game.player1.hand) - 1)
                            if len(game.player1.hand) == 0:
                                state.keyboard_hand_cursor = -1
                                state.keyboard_mode_active = False
                            state.hovered_card = None

            # G key = Activate Faction Power
            elif event.key == pygame.K_g:
                if game.game_state == "playing" and game.current_player == game.player1:
                    if game.player1.faction_power and game.player1.faction_power.is_available():
                        if game.player1.faction_power.activate(game, game.player1):
                            state.faction_power_effect = FactionPowerEffect(
                                game.player1.faction,
                                SCREEN_WIDTH // 2,
                                SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT
                            )
                            game.add_history_event(
                                "faction_power",
                                f"{game.player1.name} used {game.player1.faction_power.name}",
                                "player"
                            )
                            if state.network_proxy:
                                state.network_proxy.send_faction_power(game.player1.faction_power.name)
                            game.player1.calculate_score()
                            game.player2.calculate_score()

            # T key = Toggle LAN Chat Input
            elif event.key == pygame.K_t:
                if state.lan_chat_panel and not state.lan_chat_panel.active:
                    state.lan_chat_panel.active = True
                    continue
                elif state.lan_chat_panel and state.lan_chat_panel.active:
                     pass

            # Arrow keys for keyboard card navigation
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and game.game_state == "playing" and game.current_player == game.player1 and state.ui_state == UIState.PLAYING:
                hand_size = len(game.player1.hand)
                if hand_size > 0:
                    state.keyboard_mode_active = True
                    state.keyboard_button_cursor = -1  # Reset button cursor when selecting cards
                    if state.keyboard_hand_cursor < 0:
                        state.keyboard_hand_cursor = 0
                    elif event.key == pygame.K_LEFT:
                        state.keyboard_hand_cursor = (state.keyboard_hand_cursor - 1) % hand_size
                    else:
                        state.keyboard_hand_cursor = (state.keyboard_hand_cursor + 1) % hand_size
                    # Update hovered_card to show the keyboard-selected card
                    if 0 <= state.keyboard_hand_cursor < hand_size:
                        state.hovered_card = game.player1.hand[state.keyboard_hand_cursor]

            # Tab key = Cycle through action buttons (Pass, Faction Power)
            elif event.key == pygame.K_TAB and game.game_state == "playing" and game.current_player == game.player1 and state.ui_state == UIState.PLAYING:
                # Deactivate card selection mode, switch to button mode
                state.keyboard_mode_active = False
                state.keyboard_hand_cursor = -1
                state.hovered_card = None
                # Cycle: -1 -> 0 (pass) -> 1 (faction power) -> -1
                state.keyboard_button_cursor = (state.keyboard_button_cursor + 1) % 3 - 1  # -1, 0, 1, -1...
                if state.keyboard_button_cursor == -1:
                    state.keyboard_button_cursor = 0  # Start at pass button

            # UP/DOWN to select target row when a card is selected via keyboard
            elif event.key in (pygame.K_UP, pygame.K_DOWN) and game.game_state == "playing" and game.current_player == game.player1 and state.ui_state == UIState.PLAYING:
                if state.keyboard_mode_active and state.keyboard_hand_cursor >= 0 and state.keyboard_hand_cursor < len(game.player1.hand):
                    card = game.player1.hand[state.keyboard_hand_cursor]
                    # Determine valid rows for this card
                    if card.row == "close":
                        valid_rows = ["close"]
                    elif card.row == "ranged":
                        valid_rows = ["ranged"]
                    elif card.row == "siege":
                        valid_rows = ["siege"]
                    elif card.row == "agile":
                        valid_rows = ["close", "ranged"]
                    elif card.row == "weather":
                        valid_rows = ["close", "ranged", "siege"]
                    elif card.row == "special":
                        valid_rows = ["close", "ranged", "siege"]  # For horn effects
                    else:
                        valid_rows = ["close", "ranged", "siege"]

                    if len(valid_rows) > 1:
                        if event.key == pygame.K_UP:
                            state.keyboard_row_cursor = (state.keyboard_row_cursor - 1) % len(valid_rows)
                        else:
                            state.keyboard_row_cursor = (state.keyboard_row_cursor + 1) % len(valid_rows)
                elif state.keyboard_button_cursor >= 0:
                    # Cycle between pass (0) and faction power (1)
                    state.keyboard_button_cursor = 1 - state.keyboard_button_cursor

            # SPACEBAR = Preview card or close overlays
            elif event.key == pygame.K_SPACE:
                if state.inspected_card or state.inspected_leader:
                    # Close preview
                    state.inspected_card = None
                    state.inspected_leader = None
                elif state.ui_state in (UIState.DISCARD_VIEW, UIState.JONAS_PEEK):
                    # Close overlays
                    if state.ui_state == UIState.JONAS_PEEK:
                        game.opponent_drawn_cards = []
                    state.ui_state = UIState.PLAYING
                    state.discard_scroll = 0
                elif state.keyboard_button_cursor >= 0 and game.game_state == "playing" and game.current_player == game.player1:
                    # Activate keyboard-selected button
                    if state.keyboard_button_cursor == 0:
                        # Pass button
                        game.pass_turn()
                        if state.network_proxy:
                            state.network_proxy.send_pass()
                        state.keyboard_button_cursor = -1
                    elif state.keyboard_button_cursor == 1:
                        # Faction power button
                        if game.player1.faction_power and game.player1.faction_power.is_available():
                            if game.player1.faction_power.activate(game, game.player1):
                                state.faction_power_effect = FactionPowerEffect(
                                    game.player1.faction,
                                    SCREEN_WIDTH // 2,
                                    SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH,
                                    SCREEN_HEIGHT
                                )
                                game.add_history_event(
                                    "faction_power",
                                    f"{game.player1.name} used {game.player1.faction_power.name}",
                                    "player"
                                )
                                if state.network_proxy:
                                    state.network_proxy.send_faction_power(game.player1.faction_power.name)
                                game.player1.calculate_score()
                                game.player2.calculate_score()
                        state.keyboard_button_cursor = -1
                elif state.keyboard_mode_active and state.keyboard_hand_cursor >= 0 and game.current_player == game.player1:
                    # Preview the keyboard-selected card
                    if state.keyboard_hand_cursor < len(game.player1.hand):
                        state.inspected_card = game.player1.hand[state.keyboard_hand_cursor]

            # ENTER = Close overlays or open chat (F key plays cards)
            elif event.key == pygame.K_RETURN:
                # Skip if chat is active (RETURN opens chat)
                if state.lan_chat_panel and not state.lan_chat_panel.active:
                    state.lan_chat_panel.active = True
                    continue

                if state.inspected_card or state.inspected_leader:
                    # Close preview
                    state.inspected_card = None
                    state.inspected_leader = None
                elif state.ui_state in (UIState.DISCARD_VIEW, UIState.JONAS_PEEK):
                    # Close overlays
                    if state.ui_state == UIState.JONAS_PEEK:
                        game.opponent_drawn_cards = []
                    state.ui_state = UIState.PLAYING
                    state.discard_scroll = 0
                elif state.keyboard_button_cursor >= 0 and game.game_state == "playing" and game.current_player == game.player1:
                    # Activate keyboard-selected button
                    if state.keyboard_button_cursor == 0:
                        # Pass button
                        game.pass_turn()
                        if state.network_proxy:
                            state.network_proxy.send_pass()
                        state.keyboard_button_cursor = -1
                    elif state.keyboard_button_cursor == 1:
                        # Faction power button
                        if game.player1.faction_power and game.player1.faction_power.is_available():
                            if game.player1.faction_power.activate(game, game.player1):
                                state.faction_power_effect = FactionPowerEffect(
                                    game.player1.faction,
                                    SCREEN_WIDTH // 2,
                                    SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH,
                                    SCREEN_HEIGHT
                                )
                                game.add_history_event(
                                    "faction_power",
                                    f"{game.player1.name} used {game.player1.faction_power.name}",
                                    "player"
                                )
                                if state.network_proxy:
                                    state.network_proxy.send_faction_power(game.player1.faction_power.name)
                                game.player1.calculate_score()
                                game.player2.calculate_score()
                        state.keyboard_button_cursor = -1

            # Keyboard navigation for mulligan phase
            if game.game_state == "mulligan" and not state.mulligan_local_done:
                hand_size = len(game.player1.hand)
                if hand_size > 0:
                    # LEFT/RIGHT to navigate cards
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        state.keyboard_mode_active = True
                        if state.keyboard_hand_cursor < 0:
                            state.keyboard_hand_cursor = 0
                        elif event.key == pygame.K_LEFT:
                            state.keyboard_hand_cursor = (state.keyboard_hand_cursor - 1) % hand_size
                        else:
                            state.keyboard_hand_cursor = (state.keyboard_hand_cursor + 1) % hand_size
                        if 0 <= state.keyboard_hand_cursor < hand_size:
                            state.hovered_card = game.player1.hand[state.keyboard_hand_cursor]

                    # SPACE to toggle selection
                    elif event.key == pygame.K_SPACE and state.keyboard_hand_cursor >= 0 and state.keyboard_hand_cursor < hand_size:
                        card = game.player1.hand[state.keyboard_hand_cursor]
                        if card in state.mulligan_selected:
                            state.mulligan_selected.remove(card)
                        elif len(state.mulligan_selected) < 5:
                            state.mulligan_selected.append(card)

                    # ENTER to confirm mulligan
                    elif event.key == pygame.K_RETURN:
                        if 2 <= len(state.mulligan_selected) <= 5:
                            selected_indices = [i for i, card in enumerate(game.player1.hand) if card in state.mulligan_selected]
                            game.mulligan(game.player1, state.mulligan_selected)
                            game.player_mulligan_count = len(selected_indices)
                            state.mulligan_local_done = True
                            state.mulligan_selected = []
                            state.keyboard_hand_cursor = -1
                            state.keyboard_mode_active = False

                            if state.network_proxy:
                                state.network_proxy.send_mulligan(selected_indices)
                            else:
                                from ai_opponent import AIStrategy
                                ai_strategy = AIStrategy(game, game.player2)
                                ai_cards = ai_strategy.decide_mulligan()
                                game.mulligan(game.player2, ai_cards)

            # Game over screen - R to restart
            if game.game_state == "game_over":
                if event.key == pygame.K_r and not LAN_MODE:
                    battle_music.stop_battle_music()
                    _main.main()
                    return
                elif event.key == pygame.K_p and LAN_MODE:
                    # Play again in LAN mode - go back to deck selection while staying connected
                    if state.network_proxy and state.network_proxy.session.is_connected():
                        # Send play again message to peer
                        state.network_proxy.session.send("play_again", {"request": True})
                        battle_music.stop_battle_music()
                        # Return to LAN menu with existing session for rematch
                        from lan_menu import run_lan_rematch
                        result = run_lan_rematch(screen, state.network_proxy.session, state.network_proxy.role)
                        if result:
                            # Both players ready - run deck selection and start new game
                            from lan_game import run_lan_setup
                            from unlocks import CardUnlockSystem
                            import main as main_module
                            state.unlock_system = CardUnlockSystem()
                            new_context = run_lan_setup(screen, state.unlock_system, result["session"], result["role"])
                            if new_context:
                                # Set global LAN context via module and restart game
                                main_module.LAN_MODE = True
                                main_module.LAN_CONTEXT = new_context
                                _main.main()
                        return
                elif event.key == pygame.K_ESCAPE:
                    if LAN_MODE and state.network_proxy:
                        state.network_proxy.session.close()
                    state.running = False
                elif event.key == pygame.K_RETURN and getattr(game, 'draft_victory', False):
                    # Launch space shooter easter egg with ship selection!
                    from space_shooter import run_space_shooter
                    run_space_shooter(screen)  # Shows ship selection screen
        elif event.type == pygame.MOUSEWHEEL:
            if state.history_panel_rect and state.history_panel_rect.collidepoint(pygame.mouse.get_pos()):
                # Scroll down (event.y < 0) = see older entries = increase offset
                state.history_scroll_offset = max(0, min(state.history_scroll_limit, state.history_scroll_offset - event.y * cfg.HISTORY_ENTRY_HEIGHT))
                state.history_manual_scroll = state.history_scroll_offset > 0
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # LAN: Block game interactions if waiting for opponent
            # Allow Right Click (3) for inspection and UI clicks if paused/chatting
            # Allow clicks during leader ability selection overlays (Jonas Quinn, Ba'al, etc.)
            if state.waiting_for_opponent and state.ui_state not in (UIState.PAUSED, UIState.LAN_CHAT, UIState.LEADER_CHOICE_SELECT) and event.button != 3:
                continue

            if event.button in (4, 5):
                if state.history_panel_rect and state.history_panel_rect.collidepoint(event.pos):
                    # Button 4 = scroll up (newer) = decrease offset, Button 5 = scroll down (older) = increase offset
                    delta = -cfg.HISTORY_ENTRY_HEIGHT if event.button == 4 else cfg.HISTORY_ENTRY_HEIGHT
                    state.history_scroll_offset = max(0, min(state.history_scroll_limit, state.history_scroll_offset + delta))
                    state.history_manual_scroll = state.history_scroll_offset > 0
                continue
            if event.button == 1:
                state.button_info_popup = None

                # Game over screen button clicks
                if game.game_state == "game_over" and state.game_over_buttons:
                    btns = state.game_over_buttons
                    if "continue_draft" in btns and btns["continue_draft"].collidepoint(event.pos):
                        battle_music.stop_battle_music()
                        _main.main()
                        return
                    elif "save_exit" in btns and btns["save_exit"].collidepoint(event.pos):
                        battle_music.stop_battle_music()
                        game.main_menu_requested = True
                    elif "quit_draft" in btns and btns["quit_draft"].collidepoint(event.pos):
                        persistence = get_persistence()
                        persistence.clear_active_draft_run()
                        battle_music.stop_battle_music()
                        game.main_menu_requested = True
                    elif "new_draft" in btns and btns["new_draft"].collidepoint(event.pos):
                        game.main_menu_requested = True
                    elif "rematch" in btns and btns["rematch"].collidepoint(event.pos):
                        game.restart_requested = True
                    elif "main_menu" in btns and btns["main_menu"].collidepoint(event.pos):
                        game.main_menu_requested = True
                    elif "quit" in btns and btns["quit"].collidepoint(event.pos):
                        pygame.quit()
                        sys.exit()
                    continue

                # Pause menu button clicks
                if state.ui_state == UIState.PAUSED and state.pause_menu_buttons:
                    btns = state.pause_menu_buttons
                    if "resume" in btns and btns["resume"].collidepoint(event.pos):
                        state.ui_state = UIState.PLAYING
                    elif "options" in btns and btns["options"].collidepoint(event.pos):
                        from game_settings import run_settings_menu
                        run_settings_menu(screen)
                    elif "surrender" in btns and btns["surrender"].collidepoint(event.pos):
                        game.surrender(game.player1)
                        state.ui_state = UIState.GAME_OVER
                    elif "main_menu" in btns and btns["main_menu"].collidepoint(event.pos):
                        battle_music.stop_battle_music()
                        _main.main()
                        return
                    elif "quit" in btns and btns["quit"].collidepoint(event.pos):
                        battle_music.stop_battle_music()
                        pygame.quit()
                        sys.exit()
                    continue

                # Leader choice selection (Jonas Quinn, Ba'al)
                if state.ui_state == UIState.LEADER_CHOICE_SELECT and state.pending_leader_choice and state.leader_choice_rects:
                    for card, rect in state.leader_choice_rects:
                        if rect.collidepoint(event.pos):
                            ability_name = state.pending_leader_choice.get("ability", "")
                            if ability_name == "Eidetic Memory":
                                game.jonas_memorize_card(game.player1, card)
                                if state.network_proxy:
                                    state.network_proxy.send_leader_ability("Eidetic Memory", {"card_id": card.id})
                            elif ability_name == "System Lord's Cunning":
                                game.baal_resurrect_card(game.player1, card)
                                if state.network_proxy:
                                    state.network_proxy.send_leader_ability("System Lord's Cunning", {"choice_id": card.id})
                            state.pending_leader_choice = None
                            state.leader_choice_rects = []
                            state.ui_state = UIState.PLAYING
                            break
                    continue  # Don't process other clicks when in leader choice mode
            if game.current_player == game.player1:
                # Handle leader ability click
                if state.player_ability_rect and state.player_ability_rect.collidepoint(event.pos):
                    # If the leader is Hathor, handle her ability specifically
                    if game.player1.leader and "Hathor" in game.player1.leader.get('name', ''):
                        if game.trigger_hathor_ability(game.player1):
                            # Start the animation
                            steal_info = game.hathor_steal_info
                            if steal_info:
                                # Calculate start and end positions
                                start_pos = (
                                    steal_info['card'].rect.centerx,
                                    steal_info['card'].rect.centery
                                )

                                # Find the target row position
                                target_row = steal_info['to_player'].hathor_ability_pending['target_row']
                                target_row_rect = cfg.PLAYER_ROW_RECTS[target_row]
                                end_pos = (
                                    target_row_rect.centerx,
                                    target_row_rect.centery
                                )

                                # Create and start the animation
                                animation = HathorStealAnimation(
                                    steal_info['card'],
                                    start_pos,
                                    end_pos,
                                    on_finish=lambda: game.switch_turn()
                                )
                                state.anim_manager.add_animation(animation)
                                steal_info["animation_started"] = True
                                if state.network_proxy:
                                    state.network_proxy.send_leader_ability(
                                        "Hathor Steal",
                                        {
                                            "from_row": steal_info.get("from_row"),
                                            "from_index": steal_info.get("from_index"),
                                            "target_row": steal_info.get("target_row"),
                                            "card_id": steal_info.get("card_id"),
                                        }
                                    )
                        # After attempting Hathor's ability, don't process any other click logic for this event
                        continue
                    else:
                        # For any other leader, use the generic activation
                        result = game.activate_leader_ability(game.player1)
                        if result:
                            if result.get("requires_ui"):
                                ability_name = result.get("ability", "")
                                if ability_name == "Ancient Knowledge":
                                    # Catherine Langford
                                    state.ui_state = UIState.CATHERINE_SELECT
                                    state.catherine_cards_to_choose = result.get("revealed_cards", [])
                                elif ability_name in ["Eidetic Memory", "System Lord's Cunning"]:
                                    # Jonas Quinn or Ba'al
                                    state.pending_leader_choice = result
                                    state.ui_state = UIState.LEADER_CHOICE_SELECT
                            elif result.get("rows"):
                                # Weather ability (Apophis) - show weather visual effects
                                ability_name = result.get("ability", "Weather Decree")
                                if state.network_proxy:
                                    state.network_proxy.send_leader_ability(
                                        ability_name,
                                        {"rows": result.get("rows", [])}
                                    )
                                state.anim_manager.add_effect(create_ability_animation(
                                    ability_name,
                                    SCREEN_WIDTH // 2,
                                    SCREEN_HEIGHT // 3
                                ))
                                for row_name in result.get("rows", []):
                                    weather_target = game.weather_row_targets.get(row_name, "both")
                                    weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                                    if weather_target in ("player1", "both"):
                                        rect = cfg.PLAYER_ROW_RECTS.get(row_name)
                                        if rect:
                                            state.anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=cfg.ANIM_STARGATE))
                                            state.anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                                    if weather_target in ("player2", "both"):
                                        rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                                        if rect:
                                            state.anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=cfg.ANIM_STARGATE))
                                            state.anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                            else:
                                if state.network_proxy:
                                    ability_name = result.get("ability", game.player1.leader.get("name", "leader_ability"))
                                    state.network_proxy.send_leader_ability(ability_name, {})
            # RIGHT CLICK = Card Preview/Zoom or Discard Pile View
            if event.button == 3:  # Right click
                state.button_info_popup = None
                popup_targets = []
                if state.player_ability_rect:
                    popup_targets.append(("ability", game.player1, state.player_ability_rect, None))
                if state.ai_ability_rect:
                    popup_targets.append(("ability", game.player2, state.ai_ability_rect, None))
                if state.player_faction_button_rect:
                    popup_targets.append(("faction", game.player1, state.player_faction_button_rect, None))
                if state.ai_faction_button_rect:
                    popup_targets.append(("faction", game.player2, state.ai_faction_button_rect, None))
                if state.player_special_button_rect and state.player_special_button_kind:
                    popup_targets.append(("special", game.player1, state.player_special_button_rect, state.player_special_button_kind))
                if state.ai_special_button_rect and state.ai_special_button_kind:
                    popup_targets.append(("special", game.player2, state.ai_special_button_rect, state.ai_special_button_kind))

                popup_triggered = False
                for kind, owner, rect, special_kind in popup_targets:
                    if rect and rect.collidepoint(event.pos):
                        new_popup = build_button_info_popup(kind, owner, rect, special_kind)
                        if new_popup:
                            state.button_info_popup = new_popup
                        popup_triggered = True
                        break
                if popup_triggered:
                    continue

                history_clicked = False
                for entry, rect in state.history_entry_hitboxes:
                    if rect.collidepoint(event.pos):
                        history_clicked = True
                        if getattr(entry, "card_ref", None):
                            state.inspected_card = entry.card_ref
                            state.selected_card = None
                        break
                if history_clicked:
                    continue
                # Check if right-clicking discard pile to view it
                if state.discard_rect and state.discard_rect.collidepoint(event.pos) and state.ui_state != UIState.DISCARD_VIEW:
                    state.ui_state = UIState.DISCARD_VIEW
                    state.discard_scroll = 0
                    continue

                # Check if right-clicking a card in the discard viewer to inspect it
                if state.ui_state == UIState.DISCARD_VIEW:
                    card_clicked = False
                    for card in game.player1.discard_pile:
                        if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                            state.inspected_card = card
                            state.selected_card = None
                            card_clicked = True
                            break

                    # If clicked on a card, don't close the viewer
                    if card_clicked:
                        continue

                    # Otherwise close the discard viewer
                    state.ui_state = UIState.PLAYING
                    state.discard_scroll = 0
                    continue

                # Close any existing previews
                if state.inspected_card or state.inspected_leader:
                    state.inspected_card = None
                    state.inspected_leader = None
                else:
                    # Check if clicking on a card in hand
                    for card in game.player1.hand:
                        if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                            state.inspected_card = card
                            state.selected_card = None
                            break

                    # Check if clicking on board cards (both player and opponent)
                    if not state.inspected_card:
                        for player_obj in [game.player1, game.player2]:
                            for row_name, cards in player_obj.board.items():
                                for card in cards:
                                    if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                        state.inspected_card = card
                                        state.selected_card = None
                                        break
                                if state.inspected_card:
                                    break
                            if state.inspected_card:
                                break

                    # Check if clicking on leader portraits
                    if not state.inspected_card:
                        if state.player_leader_rect and state.player_leader_rect.collidepoint(event.pos):
                            state.inspected_leader = game.player1
                        elif state.ai_leader_rect and state.ai_leader_rect.collidepoint(event.pos):
                            state.inspected_leader = game.player2
                continue

            # LEFT CLICK = Select/Activate
            if event.button != 1:  # Only handle left click below
                continue

            # Click discard pile to view it
            if state.discard_rect and state.discard_rect.collidepoint(event.pos) and state.ui_state != UIState.DISCARD_VIEW:
                state.ui_state = UIState.DISCARD_VIEW
                state.discard_scroll = 0

            # Close discard viewer with click
            if state.ui_state == UIState.DISCARD_VIEW and event.button == 1:
                state.ui_state = UIState.PLAYING

            # Handle discard scroll with mouse wheel
            if state.ui_state == UIState.DISCARD_VIEW and event.button in [4, 5]:
                if event.button == 4:  # Scroll up
                    state.discard_scroll = min(0, state.discard_scroll + 50)
                else:  # Scroll down
                    state.discard_scroll -= 50

            # Handle medic selection mode
            if state.ui_state == UIState.MEDIC_SELECT:
                # Check if clicking on a card in the medic selection overlay
                # This will be handled after drawing
                pass

            # Check if clicking Faction Power button (player only)
            if (game.game_state == "playing"
                    and game.current_player == game.player1
                    and state.player_faction_button_rect
                    and state.player_faction_button_rect.collidepoint(event.pos)):
                if game.player1.faction_power and game.player1.faction_power.is_available():
                    if game.player1.faction_power.activate(game, game.player1):
                        state.faction_power_effect = FactionPowerEffect(
                            game.player1.faction,
                            SCREEN_WIDTH // 2,
                            SCREEN_HEIGHT // 2,
                            SCREEN_WIDTH,
                            SCREEN_HEIGHT
                        )
                        game.add_history_event(
                            "faction_power",
                            f"{game.player1.name} used {game.player1.faction_power.name}",
                            "player"
                        )
                        # Send over network in LAN mode
                        if state.network_proxy:
                            state.network_proxy.send_faction_power(game.player1.faction_power.name)
                        # Track ability usage
                        game.ability_usage["faction_power"] = game.ability_usage.get("faction_power", 0) + 1
                        game.player1.calculate_score()
                        game.player2.calculate_score()
                continue

            # Check if clicking on leader portraits (for inspection)
            if state.player_leader_rect and state.player_leader_rect.collidepoint(event.pos):
                state.inspected_leader = game.player1
                state.inspected_card = None
                state.selected_card = None
                continue
            elif state.ai_leader_rect and state.ai_leader_rect.collidepoint(event.pos):
                state.inspected_leader = game.player2
                state.inspected_card = None
                state.selected_card = None
                continue

            # Check if clicking on opponent cards (for inspection)
            if not state.inspected_card and not state.inspected_leader:
                for row_name, cards in game.player2.board.items():
                    for card in cards:
                        if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                            state.inspected_card = card
                            state.selected_card = None
                            break
                    if state.inspected_card:
                        break

            # Close inspection overlays if clicking
            if state.inspected_card or state.inspected_leader:
                state.inspected_card = None
                state.inspected_leader = None
                continue

            # Mulligan phase
            if game.game_state == "mulligan":
                if state.mulligan_local_done:
                    continue

                # Select cards to mulligan (max 2)
                for card in game.player1.hand:
                    if card.rect.collidepoint(event.pos):
                        if card in state.mulligan_selected:
                            state.mulligan_selected.remove(card)
                        elif len(state.mulligan_selected) < 5:  # Max 5 cards
                            state.mulligan_selected.append(card)
                        break

                # Confirm mulligan
                if cfg.MULLIGAN_BUTTON_RECT.collidepoint(event.pos):
                    # Enforce 2-5 card limit
                    if len(state.mulligan_selected) < 2:
                        # Show error message
                        print("Must select at least 2 cards for mulligan!")
                        continue
                    elif len(state.mulligan_selected) > 5:
                        # Show error message
                        print("Cannot mulligan more than 5 cards!")
                        continue

                    selected_indices = [i for i, card in enumerate(game.player1.hand) if card in state.mulligan_selected]
                    game.mulligan(game.player1, state.mulligan_selected)
                    game.player_mulligan_count = len(selected_indices)
                    state.mulligan_local_done = True
                    state.mulligan_selected = []

                    if state.network_proxy:
                        state.network_proxy.send_mulligan(selected_indices)
                    else:
                        # Single-player: Use AI strategy for mulligan
                        from ai_opponent import AIStrategy
                        ai_strategy = AIStrategy(game, game.player2)
                        ai_cards = ai_strategy.decide_mulligan()
                        game.mulligan(game.player2, ai_cards)
                        state.mulligan_remote_done = True
                        # Don't end mulligan here - let the main loop handle it

            # Playing phase - START DRAG
            elif game.game_state == "playing":
                if game.current_player == game.player1 and not game.player1.has_passed:
                    # Check if clicking on pass buttons
                    pass_clicked = False
                    if state.hud_pass_button_rect and state.hud_pass_button_rect.collidepoint(event.pos):
                        state.selected_card = None
                        state.dragging_card = None
                        state.drag_velocity = Vector2()
                        state.drag_pickup_flash = 0.0
                        state.anim_manager.add_effect(StargateActivationEffect(state.hud_pass_button_rect.centerx,
                                                                         state.hud_pass_button_rect.centery,
                                                                         duration=cfg.ANIM_STARGATE))
                        game.pass_turn()

                        # Send network action if in LAN mode
                        if state.network_proxy:
                            state.network_proxy.send_pass()

                        pass_clicked = True
                    if pass_clicked:
                        continue
                    # Iris button click (Tau'ri only)
                    elif state.iris_button_rect and state.iris_button_rect.collidepoint(event.pos):
                        if game.player1.iris_defense.is_available():
                            game.player1.iris_defense.activate()
                            # Trigger Iris closing animation at center of screen
                            from animations import IrisClosingEffect
                            iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                            state.anim_manager.add_effect(iris_anim)
                    # Ring Transportation button click (Goa'uld only)
                    elif state.ring_transport_button_rect and state.ring_transport_button_rect.collidepoint(event.pos):
                        if game.player1.ring_transportation and game.player1.ring_transportation.can_use():
                            # Enter card selection mode - next card clicked will be transported
                            state.ui_state = UIState.RING_TRANSPORT_SELECT
                    else:
                        # Ring Transport selection mode - clicking a card on player's board
                        if state.ui_state == UIState.RING_TRANSPORT_SELECT:
                            # Check if clicking on player's CLOSE COMBAT cards only
                            card_clicked = False
                            row_cards = game.player1.board.get("close", [])
                            for card in row_cards:
                                if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                    # Start ring transportation animation
                                    from power import RingTransportAnimation

                                    start_pos = (card.rect.centerx, card.rect.centery)
                                    # End position = center of hand area
                                    end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - HAND_Y_OFFSET // 2)

                                    state.ring_transport_animation = RingTransportAnimation(
                                        card, start_pos, end_pos, SCREEN_WIDTH, SCREEN_HEIGHT
                                    )

                                    # Remove card from board and add to hand
                                    game.player1.board["close"].remove(card)
                                    game.player1.hand.append(card)

                                    # Mark ability as used
                                    game.player1.ring_transportation.use(card)

                                    # Recalculate scores
                                    game.player1.calculate_score()
                                    game.player2.calculate_score()

                                    state.ui_state = UIState.PLAYING
                                    card_clicked = True
                                    break

                            if card_clicked:
                                continue

                        # Check if clicking on a card in hand
                        for card in game.player1.hand:
                            if card.rect.collidepoint(event.pos):
                                # Check if clicking the same special card again (confirmation)
                                if card.row == "special" and state.selected_card == card:
                                    # Second click = confirm and play
                                    # Check if this is a decoy card
                                    if has_ability(card, Ability.RING_TRANSPORT):
                                        # This card is played by dragging and dropping, so do nothing on a double-click.
                                        pass
                                    else:
                                        # Check if this is Wormhole Stabilization (Clear Weather)
                                        if has_ability(card, Ability.WORMHOLE_STABILIZATION):
                                            black_hole_anim = ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                                            state.anim_manager.add_effect(black_hole_anim)
                                        game.play_card(card, card.row)
                                    state.selected_card = None
                                    state.dragging_card = None
                                    state.drag_velocity = Vector2()
                                    state.drag_pickup_flash = 0.0
                                    break

                                # First click or different card - Select it
                                state.selected_card = card

                                if card.row == "special":
                                    # All Special cards can now be dragged
                                    state.dragging_card = card
                                    state.drag_offset = (card.rect.x - event.pos[0], card.rect.y - event.pos[1])
                                    state.drag_velocity = Vector2()
                                    state.drag_trail.clear()
                                    state.drag_trail_emit_ms = 0
                                    state.drag_pickup_flash = 1.0
                                    state.drag_pulse = 0.0
                                    # Get valid decoy targets for Ring Transport
                                    if has_ability(card, Ability.RING_TRANSPORT):
                                        state.decoy_valid_targets = []
                                        valid_cards = game.get_decoy_valid_cards()
                                        for valid_card in valid_cards:
                                            if hasattr(valid_card, 'rect'):
                                                state.decoy_valid_targets.append((valid_card, valid_card.rect.copy()))
                                else:
                                    # Start dragging unit cards
                                    state.dragging_card = card
                                    state.drag_offset = (card.rect.x - event.pos[0], card.rect.y - event.pos[1])
                                    state.drag_velocity = Vector2()
                                    state.drag_trail.clear()
                                    state.drag_trail_emit_ms = 0
                                    state.drag_pickup_flash = 1.0
                                    state.drag_pulse = 0.0
                                    # Get valid decoy targets for Ring Transport on unit cards (e.g., Puddle Jumper)
                                    if has_ability(card, Ability.RING_TRANSPORT):
                                        state.decoy_valid_targets = []
                                        valid_cards = game.get_decoy_valid_cards()
                                        for valid_card in valid_cards:
                                            if hasattr(valid_card, 'rect'):
                                                state.decoy_valid_targets.append((valid_card, valid_card.rect.copy()))

                                break

        elif event.type == pygame.MOUSEBUTTONUP:
            # Drop card
            if state.dragging_card and game.game_state == "playing":
                played = False
                card_is_spy = is_spy(state.dragging_card)
                ability_text = state.dragging_card.ability or ""
                ability_lower = ability_text.lower()

                # Weather and special cards can target any row
                if state.dragging_card.row in ["weather", "special"]:
                    if state.dragging_card.row == "weather":
                        target_row = None
                        drop_rect = None
                        # First, allow dropping onto dedicated weather slots
                        for row_name, slot_rect in WEATHER_SLOT_RECTS.items():
                            if slot_rect.collidepoint(event.pos):
                                target_row = row_name
                                drop_rect = slot_rect
                                break
                        # Fallback to full row targets if player drags over the battlefield
                        if target_row is None:
                            for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                for row_name, rect in rects.items():
                                    if rect.collidepoint(event.pos):
                                        target_row = row_name
                                        drop_rect = rect
                                        break
                                if target_row:
                                    break
                        if target_row:
                            played = True
                            if "wormhole stabilization" in ability_lower:
                                state.anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                            else:
                                effect_x = drop_rect.centerx
                                effect_y = drop_rect.centery
                                state.anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_STARGATE))
                                if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                                    for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                        row_rect = rects.get(target_row)
                                        if row_rect:
                                            state.anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))
                            game.play_card(state.dragging_card, target_row)

                            # Send network action if in LAN mode
                            if state.network_proxy:
                                state.network_proxy.send_play_card(state.dragging_card.id, target_row)
                    else:
                        if has_ability(state.dragging_card, Ability.COMMAND_NETWORK):
                            for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
                                if slot_rect.collidepoint(event.pos):
                                    game.play_card(state.dragging_card, row_name)
                                    played = True
                                    effect_x = slot_rect.centerx
                                    effect_y = slot_rect.centery
                                    state.anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_STARGATE))
                                    break
                        elif has_ability(state.dragging_card, Ability.RING_TRANSPORT):
                            # Ring Transport - check if dropped on a valid card
                            if state.decoy_drag_target:
                                if game.play_ring_transport(state.dragging_card, state.decoy_drag_target):
                                    # Show ring transport animation with golden rings
                                    from power import RingTransportAnimation
                                    start_pos = (state.decoy_drag_target.rect.centerx, state.decoy_drag_target.rect.centery)
                                    # End position is player's hand area
                                    end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
                                    state.ring_transport_animation = RingTransportAnimation(
                                        state.decoy_drag_target, start_pos, end_pos,
                                        SCREEN_WIDTH, SCREEN_HEIGHT
                                    )
                                    game.player1.calculate_score()
                                    game.player2.calculate_score()
                                    game.switch_turn()
                                    played = True
                                state.decoy_valid_targets = []
                                state.decoy_drag_target = None
                        else:
                            for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                for row_name, rect in rects.items():
                                    if rect.collidepoint(event.pos):
                                        game.play_card(state.dragging_card, row_name)
                                        played = True

                                        effect_x = rect.centerx
                                        effect_y = rect.centery

                                        # Check for Naquadah Overload explosions
                                        if has_ability(state.dragging_card, Ability.NAQUADAH_OVERLOAD):
                                            # Create blue explosions ONLY on rows where cards were destroyed
                                            for player, destroyed_row in game.last_scorch_positions:
                                                # Determine which row rect to use
                                                if player == game.player1:
                                                    row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                                                else:
                                                    row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)

                                                if row_rect:
                                                    state.anim_manager.add_effect(NaquadahExplosionEffect(
                                                        SCREEN_WIDTH // 2,
                                                        row_rect.centery,
                                                        duration=cfg.ANIM_MAJOR_EFFECT
                                                    ))
                                            game.last_scorch_positions = []

                                        # Trigger other special visuals
                                        if not add_special_card_effect(state.dragging_card, effect_x, effect_y, state.anim_manager, SCREEN_WIDTH, SCREEN_HEIGHT, game=game):
                                            stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_STARGATE)
                                            state.anim_manager.add_effect(stargate_effect)
                                        break
                                if played:
                                    break
                else:
                    # Regular unit cards
                    target_rows = cfg.OPPONENT_ROW_RECTS if card_is_spy else cfg.PLAYER_ROW_RECTS

                    # Check which row the card was dropped on
                    for row_name, rect in target_rows.items():
                        if rect.collidepoint(event.pos):
                            if state.dragging_card.row == row_name or (state.dragging_card.row == "agile" and row_name in ["close", "ranged"]):

                                # Check if this is a Ring Transport unit (e.g., Puddle Jumper) dropped on a valid target
                                if has_ability(state.dragging_card, Ability.RING_TRANSPORT) and state.decoy_drag_target:
                                    if game.play_ring_transport(state.dragging_card, state.decoy_drag_target):
                                        # Show ring transport animation with golden rings
                                        from power import RingTransportAnimation
                                        start_pos = (state.decoy_drag_target.rect.centerx, state.decoy_drag_target.rect.centery)
                                        # End position is player's hand area
                                        end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
                                        state.ring_transport_animation = RingTransportAnimation(
                                            state.decoy_drag_target, start_pos, end_pos,
                                            SCREEN_WIDTH, SCREEN_HEIGHT
                                        )
                                        game.player1.calculate_score()
                                        game.player2.calculate_score()
                                        game.switch_turn()
                                        played = True
                                    state.decoy_valid_targets = []
                                    state.decoy_drag_target = None
                                    break

                                # Calculate insertion index (Mid-Card Insertion)
                                target_player = game.player2 if card_is_spy else game.player1
                                row_cards = target_player.board[row_name]
                                insert_index = len(row_cards)

                                # Find drop position relative to existing cards (Dynamic Slot Logic)
                                if row_cards:
                                    mouse_x = event.pos[0]
                                    for i, card in enumerate(row_cards):
                                        if hasattr(card, 'rect'):
                                            # Use center of card as threshold for insertion
                                            if mouse_x < card.rect.centerx:
                                                insert_index = i
                                                break

                                # --- NEW: Check card for specific animations ---
                                if has_ability(state.dragging_card, Ability.NAQUADAH_OVERLOAD):
                                    # Naquadah Overload: Play card first, then show explosions on affected rows
                                    game.play_card(state.dragging_card, row_name, index=insert_index)

                                    # Create blue explosions ONLY on rows where cards were destroyed
                                    for player, destroyed_row in game.last_scorch_positions:
                                        # Determine which row rect to use
                                        if player == game.player1:
                                            row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                                        else:
                                            row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)

                                        if row_rect:
                                            state.anim_manager.add_effect(NaquadahExplosionEffect(
                                                SCREEN_WIDTH // 2,
                                                row_rect.centery,
                                                duration=cfg.ANIM_MAJOR_EFFECT
                                            ))

                                    # Clear the positions for next time
                                    game.last_scorch_positions = []
                                    played = True
                                elif is_hero(state.dragging_card):
                                    # Legendary Commander card - use unique hero animation
                                    effect_x = rect.centerx
                                    effect_y = rect.centery
                                    hero_anim = create_hero_animation(state.dragging_card.name, effect_x, effect_y)
                                    state.anim_manager.add_effect(hero_anim)
                                    state.anim_manager.add_effect(LegendaryLightningEffect(state.dragging_card))
                                else:
                                    # Check for special abilities
                                    effect_x = rect.centerx
                                    effect_y = rect.centery

                                    ability = state.dragging_card.ability or ""
                                    ability_triggered = False

                                    # Check for special ability animations
                                    for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones", 
                                                           "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement",
                                                           "Look at opponent's hand"]:
                                        if special_ability in ability:
                                            ability_anim = create_ability_animation(ability, effect_x, effect_y)
                                            state.anim_manager.add_effect(ability_anim)
                                            ability_triggered = True
                                            break

                                    # Default stargate effect if no special ability
                                    if not ability_triggered:
                                        state.anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y))

                                # Special card unique visuals
                                if state.dragging_card.row == "special":
                                    add_special_card_effect(
                                        state.dragging_card,
                                        effect_x,
                                        effect_y,
                                        state.anim_manager,
                                        SCREEN_WIDTH,
                                        SCREEN_HEIGHT,
                                        game=game
                                    )

                                # Add ship to space battle if siege card is PLAYED
                                if state.dragging_card.row == "siege":
                                    state.ambient_effects.add_ship(game.player1.faction, state.dragging_card.name, is_player=True)

                                # Check if this is a medic card
                                if is_medic(state.dragging_card):
                                    valid_medic_cards = game.get_medic_valid_cards(game.player1)
                                    if valid_medic_cards:
                                        # Enter medic selection mode
                                        state.ui_state = UIState.MEDIC_SELECT
                                        state.medic_card_played = state.dragging_card
                                        game.play_card(state.dragging_card, row_name, index=insert_index)
                                    else:
                                        # No cards to revive, play normally
                                        game.play_card(state.dragging_card, row_name, index=insert_index)
                                else:
                                    game.play_card(state.dragging_card, row_name, index=insert_index)

                                # Add special card effects for unit cards too
                                effect_x = rect.centerx
                                effect_y = rect.centery
                                if not add_special_card_effect(state.dragging_card, effect_x, effect_y, state.anim_manager, SCREEN_WIDTH, SCREEN_HEIGHT, game=game):
                                    # Default stargate effect if no special effect
                                    state.anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_STARGATE))

                                played = True
                                break

                # Reset drag state
                if not played:
                    state.selected_card = None
                state.dragging_card = None
                state.drag_velocity = Vector2()
                state.drag_pickup_flash = 0.0
                state.decoy_valid_targets = []
                state.decoy_drag_target = None

        elif event.type == pygame.MOUSEMOTION:
            # Reset keyboard mode when mouse is used significantly
            rel_x, rel_y = getattr(event, "rel", (0, 0))
            if abs(rel_x) > 5 or abs(rel_y) > 5:
                if state.keyboard_mode_active:
                    state.keyboard_mode_active = False
                    state.keyboard_hand_cursor = -1

            # Update dragging position with smooth easing
            if state.dragging_card:
                state.drag_target_x = event.pos[0] + state.drag_offset[0]
                state.drag_target_y = event.pos[1] + state.drag_offset[1]
                # Apply easing for smooth follow
                easing_factor = 0.25  # Lower = smoother but more lag
                state.dragging_card.rect.x += (state.drag_target_x - state.dragging_card.rect.x) * easing_factor
                state.dragging_card.rect.y += (state.drag_target_y - state.dragging_card.rect.y) * easing_factor
                rel_x, rel_y = getattr(event, "rel", (0, 0))
                state.drag_velocity.x = state.drag_velocity.x * 0.7 + rel_x * 0.3
                state.drag_velocity.y = state.drag_velocity.y * 0.7 + rel_y * 0.3

                # Update Ring Transport decoy target detection
                if has_ability(state.dragging_card, Ability.RING_TRANSPORT):
                    state.decoy_drag_target = None
                    mouse_pos = event.pos
                    for card, rect in state.decoy_valid_targets:
                        if rect.collidepoint(mouse_pos):
                            state.decoy_drag_target = card
                            break
            else:
                state.drag_velocity *= 0.85
                state.decoy_drag_target = None

            # Check for card hover in hand (for scale effect)
            if not state.dragging_card and game.game_state in ("playing", "mulligan"):
                mouse_pos = event.pos
                new_hovered = None
                for card in game.player1.hand:
                    if hasattr(card, 'rect') and card.rect.collidepoint(mouse_pos):
                        new_hovered = card
                        break
                if new_hovered != state.hovered_card:
                    state.hovered_card = new_hovered
                    state.target_hover_scale = 1.08 if state.hovered_card else 1.0

