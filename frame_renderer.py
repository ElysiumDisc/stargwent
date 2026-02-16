"""Frame rendering for the main game loop.

Extracted from main.py to reduce its size. All rendering logic
(board, cards, UI overlays, debug info) is handled here.
"""

import sys
import pygame
import math
import game_config as cfg
import display_manager
import board_renderer
import transitions
import selection_overlays
import render_engine as re_mod
from render_engine import (
    draw_hand,
    draw_opponent_hand,
    draw_row_score_boxes,
    draw_history_panel,
    draw_leader_column,
    _compute_hand_positions,
)
from animations import RowScoreAnimation, HathorStealAnimation, AbilityBurstEffect
from abilities import Ability, has_ability
from draft_mode import DraftRun
from unlocks import UNLOCKABLE_CARDS, show_card_reward_screen, show_leader_reward_screen
from deck_persistence import record_victory, record_defeat, get_persistence
import battle_music


def render_frame(state, game, screen, dt, drag_visual_state):
    """Render a complete frame of the game.

    Args:
        state: GameLoopState containing all mutable game loop state.
        game: The Game instance (alias for state.game).
        screen: The pygame display surface.
        dt: Delta time in milliseconds since last frame.
        drag_visual_state: Dict with drag trail/velocity/pulse data.
    """
    # Import main module for globals/functions that live there
    import main as _main

    # Convenience aliases
    SCREEN_WIDTH = display_manager.SCREEN_WIDTH
    SCREEN_HEIGHT = display_manager.SCREEN_HEIGHT
    SCALE_FACTOR = display_manager.SCALE_FACTOR
    HUD_LEFT = cfg.HUD_LEFT
    HUD_WIDTH = cfg.HUD_WIDTH
    CARD_WIDTH = cfg.CARD_WIDTH
    CARD_HEIGHT = cfg.CARD_HEIGHT
    PLAYFIELD_LEFT = cfg.PLAYFIELD_LEFT
    PLAYFIELD_WIDTH = cfg.PLAYFIELD_WIDTH
    COMMAND_BAR_Y = cfg.COMMAND_BAR_Y
    COMMAND_BAR_HEIGHT = cfg.COMMAND_BAR_HEIGHT
    LEADER_TOP_RECT = cfg.LEADER_TOP_RECT
    LEADER_BOTTOM_RECT = cfg.LEADER_BOTTOM_RECT
    UIState = _main.UIState
    LAN_MODE = _main.LAN_MODE
    LAN_CONTEXT = _main.LAN_CONTEXT
    DEBUG_MODE = _main.DEBUG_MODE
    draw_stargwent_button = _main.draw_stargwent_button
    draw_button_info_popup = _main.draw_button_info_popup
    GOLD = cfg.GOLD
    pct_y = cfg.pct_y
    opponent_hand_area_y = cfg.opponent_hand_area_y

    # Cache mouse position once per frame
    mouse_pos = pygame.mouse.get_pos()

    # --- Drawing ---
    # Use mulligan background during mulligan phase, otherwise board background
    if game.game_state == "mulligan":
        screen.blit(state.assets["mulligan_bg"], (0, 0))
    else:
        screen.blit(state.assets["board"], (0, 0))

    separator_color = (100, 150, 200, 150)
    separator_width = 3
    glow_color = (150, 200, 255, 80)
    x_start = PLAYFIELD_LEFT
    x_end = PLAYFIELD_LEFT + PLAYFIELD_WIDTH

    for row_rect in list(cfg.OPPONENT_ROW_RECTS.values()) + list(cfg.PLAYER_ROW_RECTS.values()):
        y_pos = row_rect.bottom
        if row_rect in cfg.OPPONENT_ROW_RECTS.values():
            y_pos += 8

        pygame.draw.line(screen, glow_color, (x_start, y_pos - 2), (x_end, y_pos - 2), 1)
        pygame.draw.line(screen, glow_color, (x_start, y_pos - 1), (x_end, y_pos - 1), 1)
        pygame.draw.line(screen, separator_color, (x_start, y_pos), (x_end, y_pos), separator_width)
        pygame.draw.line(screen, glow_color, (x_start, y_pos + separator_width), (x_end, y_pos + separator_width), 1)
        pygame.draw.line(screen, glow_color, (x_start, y_pos + separator_width + 1), (x_end, y_pos + separator_width + 1), 1)

    # Draw ambient background effects
    state.ambient_effects.draw(screen)

    if game.game_state == "mulligan":
        # Draw mulligan UI (hand and button only, no text)
        draw_hand(
            screen,
            game.player1,
            None,
            state.mulligan_selected,
            dragging_card=None,
            hovered_card=state.hovered_card,
            hover_scale=state.card_hover_scale
        )
        board_renderer.draw_mulligan_button(screen, state.mulligan_selected)
        state.history_panel_rect = None
    elif game.game_state == "game_over":
        # Initialize game over animation if not already created
        if not hasattr(game, 'game_over_animation'):
            game.game_over_animation = transitions.GameOverAnimation(game, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Update and draw the animation
        anim = game.game_over_animation
        if anim:
            anim.update()
            anim.draw(screen)

        # Calculate position below the leader cards for messages/score
        # (VICTOR/DEFEATED labels in animation already communicate the result)
        if anim:
            card_bottom_y = int(SCREEN_HEIGHT * 0.42) + anim.card_height // 2
            content_start_y = card_bottom_y + int(30 * anim.scale)
        else:
            content_start_y = SCREEN_HEIGHT // 2 + int(100 * SCALE_FACTOR)

        if game.winner:
            # Record game result and show rewards
            if not hasattr(game, 'reward_shown'):
                game.reward_shown = True

                # Record win/loss using persistence system
                player_won = (game.winner == game.player1)

                # Derive player_leader and player_deck from game state
                player_leader = game.player1.leader if game.player1.leader else {}
                if isinstance(player_leader, str):
                    player_leader = {'name': player_leader, 'card_id': ''}
                player_deck = list(game.player1.hand) + [c for row in game.player1.board.values() for c in row] + list(game.player1.discard_pile)

                # Update Draft Run Progress
                if hasattr(game, 'is_draft_match') and game.is_draft_match:
                    persistence = get_persistence()
                    # Update the active run
                    active_run_data = persistence.get_active_draft_run()
                    if active_run_data:
                        current_wins = active_run_data.get('wins', 0)

                        if player_won:
                            current_wins += 1
                            active_run_data['wins'] = current_wins

                            # Check milestones
                            msg_list = []

                            if current_wins >= DraftRun.MAX_WINS: # 8 Wins
                                msg_list.append("DRAFT CHAMPION! 8 WINS!")
                                msg_list.append("You have conquered the galaxy!")
                                game.draft_victory = True
                                persistence.clear_active_draft_run()
                                # Record stats for completed run
                                leader_name = player_leader.get('name', 'Unknown')
                                leader_id = player_leader.get('card_id', '')
                                deck_power = sum(card.power for card in player_deck)
                                persistence.record_draft_completion(
                                    leader_id=leader_id,
                                    leader_name=leader_name,
                                    faction=game.player1_faction,
                                    cards=player_deck,
                                    deck_power=deck_power,
                                    won=True,
                                    final_wins=current_wins
                                )
                            else:
                                # Continue Run
                                if current_wins == DraftRun.MILESTONE_REDRAFT_LEADER: # 5 Wins
                                    active_run_data['phase'] = "redraft_leader"
                                    msg_list.append("Milestone Reached: Leader Redraft Available!")
                                elif current_wins == DraftRun.MILESTONE_REDRAFT_CARDS: # 3 Wins
                                    active_run_data['phase'] = "redraft_cards_select"
                                    msg_list.append("Milestone Reached: Card Redraft Available!")
                                else:
                                    # Ensure we go back to review/battle ready
                                    active_run_data['phase'] = "review"

                                persistence.save_active_draft_run(active_run_data)
                                msg_list.append(f"Draft Run Progress: {current_wins}/{DraftRun.MAX_WINS} Wins")

                            game.draft_messages = msg_list

                        else:
                            # Defeat - End Run
                            persistence.clear_active_draft_run()
                            game.draft_messages = ["Draft Run Ended", f"Final Result: {current_wins} Wins"]
                            # Record stats
                            leader_name = player_leader.get('name', 'Unknown')
                            leader_id = player_leader.get('card_id', '')
                            deck_power = sum(card.power for card in player_deck)
                            persistence.record_draft_completion(
                                leader_id=leader_id,
                                leader_name=leader_name,
                                faction=game.player1_faction,
                                cards=player_deck,
                                deck_power=deck_power,
                                won=False,
                                final_wins=current_wins
                            )
                    else:
                         # Fallback if no run data found (legacy/error)
                        persistence.record_draft_completion(
                            leader_id=player_leader.get('card_id', ''),
                            leader_name=player_leader.get('name', 'Unknown'),
                            faction=game.player1_faction,
                            cards=player_deck,
                            deck_power=sum(c.power for c in player_deck),
                            won=player_won
                        )

                mode_label = "lan" if LAN_MODE else "ai"

                # Record rich stats summary once per game (BEFORE blocking UI)
                try:
                    # Extract leader names robustly
                    leader_obj = game.player1.leader
                    if isinstance(leader_obj, dict):
                        leader_name = leader_obj.get('name', 'Unknown')
                    elif isinstance(leader_obj, str):
                        leader_name = leader_obj # Use ID if name unavailable
                    else:
                        leader_name = str(leader_obj) if leader_obj else 'Unknown'

                    opp_leader_obj = game.player2.leader
                    if isinstance(opp_leader_obj, dict):
                        opponent_leader = opp_leader_obj.get('name', 'Unknown')
                    else:
                        opponent_leader = str(opp_leader_obj) if opp_leader_obj else 'Unknown'

                    # Check if player lost round 1 (for comeback tracking)
                    round_history = getattr(game, "round_history", [])
                    lost_round_1 = len(round_history) > 0 and round_history[0].get("winner") == "player2"
                    # Check who went first
                    went_first = getattr(game, "player_went_first", None)

                    summary = {
                        "won": player_won,
                        "player_faction": game.player1_faction,
                        "opponent_faction": game.player2_faction,
                        "leader": leader_name,
                        "opponent_leader": opponent_leader,
                        "turns": getattr(game, "turn_count", 0),
                        "mulligans": getattr(game, "player_mulligan_count", 0),
                        "abilities": getattr(game, "ability_usage", {}),
                        "cards_played": getattr(game, "cards_played_ids", []),
                        "mode": mode_label,
                        "lan_completed": LAN_MODE,
                        "lan_disconnect": False,
                        "ai_difficulty": "hard" if not LAN_MODE else None,
                        "player_rounds_won": game.player1.rounds_won,
                        "opponent_rounds_won": game.player2.rounds_won,
                        "lost_round_1": lost_round_1,
                        "went_first": went_first,
                    }
                    get_persistence().record_game_summary(summary)
                except Exception:
                    pass  # Silently handle stats recording failures

                if player_won:
                    record_victory(game.player1_faction, mode_label)

                    # FIRST: Check for leader unlock (every 3 consecutive wins)
                    persistence = get_persistence()
                    consecutive_wins = persistence.get_consecutive_wins()

                    if consecutive_wins > 0 and consecutive_wins % 3 == 0:
                        # Show leader reward screen - unless unlock all is enabled
                        if not state.unlock_system.is_unlock_override_enabled():
                            unlocked_leader = show_leader_reward_screen(screen, state.unlock_system, game.player1_faction)
                            if unlocked_leader:
                                leader_name = unlocked_leader.get('name', 'Unknown Leader')
                                game.unlock_message = cfg.UI_FONT.render(f"NEW LEADER UNLOCKED: {leader_name}!", True, cfg.GOLD)
                                game.streak_message = cfg.UI_FONT.render(f"3 Win Streak! Leader unlocked!", True, cfg.HIGHLIGHT_ORANGE)

                    # SECOND: Show card reward screen (every win) - unless unlock all is enabled
                    state.unlock_system.record_game_result(True)
                    # Only show reward screen if unlock all is not enabled
                    if not state.unlock_system.is_unlock_override_enabled():
                        unlocked_card = show_card_reward_screen(screen, state.unlock_system, faction=game.player1_faction)
                        if unlocked_card:
                            # Add unlocked card to player's deck
                            persistence = get_persistence()
                            persistence.unlock_card(unlocked_card)
                            current_deck = persistence.get_deck(game.player1_faction)
                            current_cards = current_deck.get("cards", [])
                            if unlocked_card not in current_cards:
                                current_cards.append(unlocked_card)
                                persistence.set_deck(game.player1_faction, current_deck.get("leader", ""), current_cards)

                            card_msg = cfg.UI_FONT.render(f"Unlocked: {UNLOCKABLE_CARDS[unlocked_card]['name']}!", True, cfg.GOLD)
                            if hasattr(game, 'unlock_message'):
                                game.unlock_message2 = card_msg
                            else:
                                game.unlock_message = card_msg

                    # Show win streak progress
                    if not hasattr(game, 'streak_message'):
                        persistence = get_persistence()
                        streak = persistence.get_consecutive_wins()
                        if streak > 0:
                            remaining = 3 - (streak % 3)
                            if remaining == 3:
                                remaining = 0  # Just got a leader unlock
                            game.streak_message = cfg.UI_FONT.render(f"Win Streak: {streak}! ({remaining} more for leader unlock)", True, cfg.HIGHLIGHT_GREEN)
                else:
                    record_defeat(game.player1_faction, mode_label)
                    state.unlock_system.record_game_result(False)

        # Position score and messages directly below the animation (tighter spacing)
        messages_base_y = content_start_y + int(20 * SCALE_FACTOR)
        score_font = cfg.get_font("Arial", max(20, int(24 * SCALE_FACTOR)), bold=True)
        score_text = score_font.render(f"Final Score: {game.player1.name} {game.player1.rounds_won} - {game.player2.rounds_won} {game.player2.name}", True, cfg.WHITE)
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, messages_base_y))

        # Show unlock messages if exist (tighter spacing)
        line_spacing = int(28 * SCALE_FACTOR)
        y_offset = line_spacing
        if hasattr(game, 'unlock_message'):
            screen.blit(game.unlock_message, (SCREEN_WIDTH // 2 - game.unlock_message.get_width() // 2, messages_base_y + y_offset))
            y_offset += line_spacing
        if hasattr(game, 'unlock_message2'):
            screen.blit(game.unlock_message2, (SCREEN_WIDTH // 2 - game.unlock_message2.get_width() // 2, messages_base_y + y_offset))
            y_offset += line_spacing
        if hasattr(game, 'streak_message'):
            screen.blit(game.streak_message, (SCREEN_WIDTH // 2 - game.streak_message.get_width() // 2, messages_base_y + y_offset))
            y_offset += line_spacing

        if hasattr(game, 'draft_messages'):
            for msg in game.draft_messages:
                if isinstance(msg, str):
                    msg_surf = cfg.UI_FONT.render(msg, True, cfg.HIGHLIGHT_ORANGE)
                else:
                    msg_surf = msg
                screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, messages_base_y + y_offset))
                y_offset += line_spacing

        if getattr(game, 'draft_victory', False):
            egg_font = cfg.get_font("Arial", max(36, int(48 * SCALE_FACTOR)), bold=True)
            egg_text = egg_font.render("EASTER EGG UNLOCKED!", True, (255, 0, 255))
            sub_font = cfg.get_font("Arial", max(16, int(20 * SCALE_FACTOR)))
            sub_text = sub_font.render("Press ENTER to play STARGATE SPACE BATTLE!", True, (200, 100, 255))

            screen.blit(egg_text, (SCREEN_WIDTH // 2 - egg_text.get_width() // 2, messages_base_y + y_offset + int(20 * SCALE_FACTOR)))
            screen.blit(sub_text, (SCREEN_WIDTH // 2 - sub_text.get_width() // 2, messages_base_y + y_offset + int(70 * SCALE_FACTOR)))
            y_offset += int(100 * SCALE_FACTOR)

        # Show different options based on game mode
        if hasattr(game, 'is_draft_match') and game.is_draft_match:
            # In draft mode, check if we should continue automatically
            persistence = get_persistence()
            active_run_data = persistence.get_active_draft_run()

            # Check if player won
            player_won = (game.winner == game.player1)

            if active_run_data:
                current_wins = active_run_data.get('wins', 0)
                if player_won and current_wins < DraftRun.MAX_WINS:  # Player won and still in draft run
                    # Show draft progress and options
                    scale = display_manager.SCALE_FACTOR
                    button_width = int(250 * scale)
                    button_height = int(55 * scale)
                    button_spacing = int(15 * scale)
                    start_y = messages_base_y + y_offset + int(30 * scale)
                    # mouse_pos already cached at frame start

                    # Progress message (positioned above button panel)
                    progress_text = cfg.UI_FONT.render(f"Draft Progress: {current_wins}/{DraftRun.MAX_WINS} Wins", True, cfg.HIGHLIGHT_GREEN)
                    screen.blit(progress_text, (SCREEN_WIDTH // 2 - progress_text.get_width() // 2, start_y - int(35 * scale)))

                    # Define buttons
                    continue_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                    save_exit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                    quit_draft_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                    # Draw semi-transparent panel behind buttons
                    panel_padding = int(20 * scale)
                    panel_rect = pygame.Rect(
                        continue_button.left - panel_padding,
                        continue_button.top - panel_padding,
                        button_width + panel_padding * 2,
                        quit_draft_button.bottom - continue_button.top + panel_padding * 2
                    )
                    panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
                    panel_surface.fill((0, 0, 0, 140))
                    pygame.draw.rect(panel_surface, (60, 60, 80, 200), panel_surface.get_rect(), 2, border_radius=8)
                    screen.blit(panel_surface, panel_rect.topleft)

                    # Draw Stargwent-styled buttons
                    draw_stargwent_button(screen, continue_button, "CONTINUE DRAFT", mouse_pos,
                                          base_color=(40, 60, 40), hover_color=(60, 90, 60),
                                          border_color=(80, 180, 80), hover_border=(100, 255, 100))
                    draw_stargwent_button(screen, save_exit_button, "SAVE & EXIT", mouse_pos,
                                          base_color=(50, 50, 70), hover_color=(70, 70, 100),
                                          border_color=(100, 100, 180), hover_border=(150, 150, 255))
                    draw_stargwent_button(screen, quit_draft_button, "ABANDON DRAFT", mouse_pos,
                                          base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                          border_color=(180, 80, 80), hover_border=(255, 100, 100))

                    # Store button rects for event handler
                    state.game_over_buttons = {
                        "continue_draft": continue_button,
                        "save_exit": save_exit_button,
                        "quit_draft": quit_draft_button,
                    }
                else:
                    # Draft completed (either won all rounds or lost) - show game over options
                    scale = display_manager.SCALE_FACTOR
                    button_width = int(250 * scale)
                    button_height = int(55 * scale)
                    button_spacing = int(20 * scale)
                    start_y = messages_base_y + y_offset + int(30 * scale)
                    # mouse_pos already cached at frame start

                    # Define buttons - different for draft mode end
                    new_draft_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                    main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                    quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                    # Draw semi-transparent panel behind buttons
                    panel_padding = int(20 * scale)
                    panel_rect = pygame.Rect(
                        new_draft_button.left - panel_padding,
                        new_draft_button.top - panel_padding,
                        button_width + panel_padding * 2,
                        quit_button.bottom - new_draft_button.top + panel_padding * 2
                    )
                    panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
                    panel_surface.fill((0, 0, 0, 140))
                    pygame.draw.rect(panel_surface, (60, 60, 80, 200), panel_surface.get_rect(), 2, border_radius=8)
                    screen.blit(panel_surface, panel_rect.topleft)

                    # Draw Stargwent-styled buttons
                    draw_stargwent_button(screen, new_draft_button, "NEW DRAFT", mouse_pos,
                                          base_color=(40, 60, 40), hover_color=(60, 90, 60),
                                          border_color=(80, 180, 80), hover_border=(100, 255, 100))
                    draw_stargwent_button(screen, main_menu_button, "MAIN MENU", mouse_pos)
                    draw_stargwent_button(screen, quit_button, "QUIT", mouse_pos,
                                          base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                          border_color=(180, 80, 80), hover_border=(255, 100, 100))

                    # Store button rects for event handler
                    state.game_over_buttons = {
                        "new_draft": new_draft_button,
                        "main_menu": main_menu_button,
                        "quit": quit_button,
                    }
            else:
                # No active draft run - show regular game over options
                scale = display_manager.SCALE_FACTOR
                button_width = int(250 * scale)
                button_height = int(55 * scale)
                button_spacing = int(20 * scale)
                start_y = messages_base_y + y_offset + int(30 * scale)
                # mouse_pos already cached at frame start

                # Define buttons
                rematch_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                # Draw semi-transparent panel behind buttons
                panel_padding = int(20 * scale)
                panel_rect = pygame.Rect(
                    rematch_button.left - panel_padding,
                    rematch_button.top - panel_padding,
                    button_width + panel_padding * 2,
                    quit_button.bottom - rematch_button.top + panel_padding * 2
                )
                panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
                panel_surface.fill((0, 0, 0, 140))
                pygame.draw.rect(panel_surface, (60, 60, 80, 200), panel_surface.get_rect(), 2, border_radius=8)
                screen.blit(panel_surface, panel_rect.topleft)

                # Draw Stargwent-styled buttons
                draw_stargwent_button(screen, rematch_button, "REMATCH", mouse_pos)
                draw_stargwent_button(screen, main_menu_button, "MAIN MENU", mouse_pos)
                draw_stargwent_button(screen, quit_button, "QUIT", mouse_pos,
                                      base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                      border_color=(180, 80, 80), hover_border=(255, 100, 100))

                # Store button rects for event handler
                state.game_over_buttons = {
                    "rematch": rematch_button,
                    "main_menu": main_menu_button,
                    "quit": quit_button,
                }

        else:
            # Regular game - show game over options with Stargwent styling
            scale = display_manager.SCALE_FACTOR
            button_width = int(250 * scale)
            button_height = int(55 * scale)
            button_spacing = int(20 * scale)
            start_y = messages_base_y + y_offset + int(30 * scale)
            # mouse_pos already cached at frame start

            # Define buttons
            rematch_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
            main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
            quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

            # Draw semi-transparent panel behind buttons
            panel_padding = int(20 * scale)
            panel_rect = pygame.Rect(
                rematch_button.left - panel_padding,
                rematch_button.top - panel_padding,
                button_width + panel_padding * 2,
                quit_button.bottom - rematch_button.top + panel_padding * 2
            )
            panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
            panel_surface.fill((0, 0, 0, 140))
            pygame.draw.rect(panel_surface, (60, 60, 80, 200), panel_surface.get_rect(), 2, border_radius=8)
            screen.blit(panel_surface, panel_rect.topleft)

            # Draw Stargwent-styled buttons
            draw_stargwent_button(screen, rematch_button, "REMATCH", mouse_pos)
            draw_stargwent_button(screen, main_menu_button, "MAIN MENU", mouse_pos)
            draw_stargwent_button(screen, quit_button, "QUIT", mouse_pos,
                                  base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                  border_color=(180, 80, 80), hover_border=(255, 100, 100))

            # Store button rects for event handler
            state.game_over_buttons = {
                "rematch": rematch_button,
                "main_menu": main_menu_button,
                "quit": quit_button,
            }

        # Draw history panel on game over screen (right side)
        panel_width = 300
        history_rect = pygame.Rect(
            cfg.SIDEBAR_X + 175,
            pct_y(0.12),
            panel_width,
            pct_y(0.80) - pct_y(0.12)
        )
        state.history_panel_rect = history_rect
        state.history_entry_hitboxes, state.history_scroll_limit = draw_history_panel(
            screen,
            game,
            history_rect,
            state.history_scroll_offset,
            mouse_pos
        )

    if state.ui_state != UIState.LEADER_MATCHUP and game.game_state != "game_over":
        board_renderer.draw_board(screen, game, state.selected_card, dragging_card=state.dragging_card,
                   drag_hover_highlight=state.drag_hover_highlight,
                   drag_row_highlights=None)  # Add logic for drag row highlights if needed
        board_renderer.draw_scores(screen, game, state.anim_manager, render_static=False)

        # Draw row scores using render_engine (special specialized boxes)

        # Auto-start Hathor steal animation (LAN/AI) if pending and not started yet
        steal_info = getattr(game, "hathor_steal_info", None)
        if steal_info and not steal_info.get("animation_started"):
            card = steal_info.get("card")
            target_row = steal_info.get("target_row", "close")
            if card and hasattr(card, "rect"):
                start_pos = (card.rect.centerx, card.rect.centery)
                target_rect = cfg.PLAYER_ROW_RECTS.get(target_row) or cfg.OPPONENT_ROW_RECTS.get(target_row)
                end_pos = (target_rect.centerx, target_rect.centery) if target_rect else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                h_anim = HathorStealAnimation(
                    card,
                    start_pos,
                    end_pos,
                    on_finish=lambda: game.switch_turn()
                )
                state.anim_manager.add_animation(h_anim)
                steal_info["animation_started"] = True

        # 1. Sidebar Positioning (No More Percentages)
        panel_width = 300 # Wider panel for chat/history (score boxes are now narrower)
        history_rect = pygame.Rect(
            cfg.SIDEBAR_X + 175,
            pct_y(0.12),
            panel_width,
            pct_y(0.80) - pct_y(0.12)
        )
        state.history_panel_rect = history_rect

        # 2. Draw Score Boxes (Anchored to Sidebar start + padding)
        draw_row_score_boxes(screen, game)

        # Always show game history in the HUD panel
        state.history_entry_hitboxes, state.history_scroll_limit = draw_history_panel(
            screen,
            game,
            history_rect,
            state.history_scroll_offset,
            mouse_pos
        )

        # LAN Chat UI - show input box when active, hint when inactive
        if LAN_MODE and state.lan_chat_panel:
            chat_font = cfg.get_font("Consolas", max(18, int(20 * SCALE_FACTOR)))
            if state.lan_chat_panel.active:
                # Draw chat input box below history panel
                input_rect = pygame.Rect(
                    history_rect.x,
                    history_rect.bottom + 8,
                    history_rect.width,
                    36
                )
                pygame.draw.rect(screen, (25, 35, 55), input_rect, border_radius=6)
                pygame.draw.rect(screen, (80, 140, 200), input_rect, width=2, border_radius=6)

                # Draw input text or placeholder
                input_text = state.lan_chat_panel.input_text if state.lan_chat_panel.input_text else "Type message... (Enter to send)"
                text_color = (220, 220, 220) if state.lan_chat_panel.input_text else (120, 140, 160)
                input_surf = chat_font.render(input_text, True, text_color)
                screen.blit(input_surf, (input_rect.x + 10, input_rect.y + 8))

                # Draw typing indicator if peer is typing
                if state.lan_chat_panel.peer_is_typing:
                    typing_text = chat_font.render("Peer is typing...", True, cfg.HIGHLIGHT_CYAN)
                    screen.blit(typing_text, (input_rect.x, input_rect.y - 22))
            else:
                # Show hint to open chat
                hint_text = chat_font.render("Press T to chat", True, (100, 140, 180))
                screen.blit(hint_text, (history_rect.x, history_rect.bottom + 12))

        # Round and Turn indicator in HUD (horizontal layout)
        round_font = cfg.get_font("Arial", max(24, int(26 * SCALE_FACTOR)), bold=True)
        round_text = round_font.render(f"Round {game.round_number}", True, cfg.WHITE)
        turn_color = (120, 255, 160) if game.current_player == game.player1 else (255, 140, 140)
        turn_text = round_font.render("YOUR TURN" if game.current_player == game.player1 else "ENEMY TURN", True, turn_color)
        # Draw on same line: "Round X - YOUR TURN"
        hud_text_x = HUD_LEFT + int(HUD_WIDTH * 0.05)
        hud_text_y = pct_y(0.04)
        screen.blit(round_text, (hud_text_x, hud_text_y))
        screen.blit(turn_text, (hud_text_x, hud_text_y + round_text.get_height() + 4))

        # LAN Mode: Draw latency indicator
        if LAN_MODE and LAN_CONTEXT and LAN_CONTEXT.session.is_connected():
            latency_font = cfg.get_font("Arial", max(16, int(18 * SCALE_FACTOR)))
            rtt = LAN_CONTEXT.session.get_latency()
            latency_color, latency_label = LAN_CONTEXT.session.get_latency_status()

            # Draw latency dot and text
            latency_y = hud_text_y + round_text.get_height() + turn_text.get_height() + 12
            dot_radius = 6
            pygame.draw.circle(screen, latency_color, (hud_text_x + dot_radius, latency_y + dot_radius), dot_radius)
            latency_text = latency_font.render(f"{rtt}ms ({latency_label})", True, latency_color)
            screen.blit(latency_text, (hud_text_x + dot_radius * 3, latency_y))

        command_bar_surface = pygame.Surface((SCREEN_WIDTH, COMMAND_BAR_HEIGHT), pygame.SRCALPHA)
        command_bar_surface.fill((10, 20, 35, 200))
        pygame.draw.line(command_bar_surface, (80, 120, 180), (0, 0), (SCREEN_WIDTH, 0), 2)
        screen.blit(command_bar_surface, (0, COMMAND_BAR_Y))

        board_renderer.draw_pass_button(screen, game, state.hud_pass_button_rect)

        # Draw keyboard highlight for Pass button
        if state.keyboard_button_cursor == 0 and game.current_player == game.player1:
            highlight_rect = state.hud_pass_button_rect.inflate(12, 12)
            pygame.draw.rect(screen, (255, 255, 100), highlight_rect, width=3, border_radius=highlight_rect.width // 2)

        draw_hand(
            screen,
            game.player1,
            state.selected_card,
            dragging_card=state.dragging_card,
            hovered_card=state.hovered_card,
            hover_scale=state.card_hover_scale,
            drag_visuals=drag_visual_state
        )
        draw_opponent_hand(screen, game.player2)

        # Draw keyboard navigation hint when active
        if game.current_player == game.player1 and state.ui_state == UIState.PLAYING:
            hint_font = cfg.get_font("Arial", max(18, int(20 * SCALE_FACTOR)))
            hint_text = None

            if state.keyboard_mode_active and state.keyboard_hand_cursor >= 0:
                if state.keyboard_hand_cursor < len(game.player1.hand):
                    card = game.player1.hand[state.keyboard_hand_cursor]
                    if card.row in ("agile", "weather", "special"):
                        hint_text = "←/→: Card | ↑/↓: Row | F: Play | TAB: Buttons"
                    else:
                        hint_text = "←/→: Card | F: Play | SPACE: Preview | TAB: Buttons"
            elif state.keyboard_button_cursor >= 0:
                btn_name = "PASS" if state.keyboard_button_cursor == 0 else "FACTION POWER"
                hint_text = f"↑/↓: Switch | SPACE: {btn_name} | ←/→: Cards"

            if hint_text:
                hint_surf = hint_font.render(hint_text, True, (180, 200, 220))
                hint_x = (SCREEN_WIDTH - hint_surf.get_width()) // 2
                hint_y = COMMAND_BAR_Y - hint_surf.get_height() - 8
                hint_bg = pygame.Surface((hint_surf.get_width() + 16, hint_surf.get_height() + 8), pygame.SRCALPHA)
                hint_bg.fill((20, 30, 50, 180))
                screen.blit(hint_bg, (hint_x - 8, hint_y - 4))
                screen.blit(hint_surf, (hint_x, hint_y))

        # mouse_pos already cached at frame start
        ai_area = LEADER_TOP_RECT.copy()
        player_area = LEADER_BOTTOM_RECT.copy()
        ai_stack = draw_leader_column(
            screen,
            game.player2,
            ai_area,
            ability_ready=state.ai_ability_ready,
            faction_power_ready=bool(game.player2.faction_power and game.player2.faction_power.is_available()),
            hover_pos=mouse_pos
        )
        player_stack = draw_leader_column(
            screen,
            game.player1,
            player_area,
            ability_ready=state.player_ability_ready,
            faction_power_ready=bool(game.player1.faction_power and game.player1.faction_power.is_available()),
            hover_pos=mouse_pos
        )

        state.ai_leader_rect = ai_stack["leader_rect"]
        state.ai_ability_rect = ai_stack["ability_rect"]
        state.ai_faction_button_rect = ai_stack["faction_rect"]
        state.ai_special_button_rect = ai_stack.get("special_rect")
        state.ai_special_button_kind = ai_stack.get("special_kind")
        state.player_leader_rect = player_stack["leader_rect"]
        state.player_ability_rect = player_stack["ability_rect"]
        state.player_faction_button_rect = player_stack["faction_rect"]
        state.player_special_button_rect = player_stack.get("special_rect")
        state.player_special_button_kind = player_stack.get("special_kind")
        state.discard_rect = player_stack.get("discard_rect") or state.discard_rect

        state.iris_button_rect = state.player_special_button_rect if state.player_special_button_kind == "iris" else None
        state.ring_transport_button_rect = state.player_special_button_rect if state.player_special_button_kind == "rings" else None

        # Draw keyboard highlight for Faction Power button
        if state.keyboard_button_cursor == 1 and game.current_player == game.player1 and state.player_faction_button_rect:
            highlight_rect = state.player_faction_button_rect.inflate(8, 8)
            pygame.draw.rect(screen, (255, 255, 100), highlight_rect, width=3, border_radius=8)

        if state.ai_turn_in_progress:
            total_cards = len(game.player2.hand)
            if total_cards > 0:
                card_spacing = int(CARD_WIDTH * 0.125)
                positions, _ = _compute_hand_positions(total_cards, CARD_WIDTH, card_spacing)
                left_edge = positions[0]
                right_edge = positions[-1] + CARD_WIDTH
                opponent_hand_area = pygame.Rect(left_edge, opponent_hand_area_y,
                                                 right_edge - left_edge, CARD_HEIGHT)
                state.ai_turn_anim.draw(screen, cfg.UI_FONT, opponent_hand_area)

    # Draw animations and effects on top of everything (but not during game_over)
    if game.game_state != "game_over":
        state.anim_manager.draw_effects(screen)
        state.anim_manager.draw_weather(screen)

    # Draw Iris Power effect (full-screen cinematic) - not during game_over
    if state.faction_power_effect and game.game_state != "game_over":
        state.faction_power_effect.draw(screen)

    # Draw Ring Transportation animation - not during game_over
    if state.ring_transport_animation and game.game_state != "game_over":
        state.ring_transport_animation.draw(screen)

    # Draw visual feedback for ring transport selection mode (not during game_over)
    if state.ui_state == UIState.RING_TRANSPORT_SELECT and game.game_state != "game_over":
        # Dim the screen slightly
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        # Draw instruction text
        hint_font = cfg.get_font(None, 48)
        hint_text = hint_font.render("Click a CLOSE COMBAT unit to return to hand", True, cfg.HIGHLIGHT_ORANGE)
        hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, 100))

        # Draw text shadow
        shadow_text = hint_font.render("Click a CLOSE COMBAT unit to return to hand", True, (0, 0, 0))
        screen.blit(shadow_text, (hint_rect.x + 3, hint_rect.y + 3))
        screen.blit(hint_text, hint_rect)

        # Highlight ONLY close combat cards on board with golden glow
        row_cards = game.player1.board.get("close", [])
        for card in row_cards:
            if hasattr(card, 'rect'):
                # Golden glow around selectable cards
                glow_surf = pygame.Surface((card.rect.width + 20, card.rect.height + 20), pygame.SRCALPHA)
                glow_alpha = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.005))
                pygame.draw.rect(glow_surf, (255, 200, 100, glow_alpha), glow_surf.get_rect(), border_radius=10)
                screen.blit(glow_surf, (card.rect.x - 10, card.rect.y - 10))

    # Draw visual feedback when dragging Ring Transport over valid targets
    if state.dragging_card and has_ability(state.dragging_card, Ability.RING_TRANSPORT):
        # Highlight valid targets
        for card, rect in state.decoy_valid_targets:
            # Golden glow around valid cards
            glow_surf = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
            glow_alpha = int(100 + 80 * math.sin(pygame.time.get_ticks() * 0.008))
            pygame.draw.rect(glow_surf, (100, 200, 255, glow_alpha), glow_surf.get_rect(), border_radius=8)
            screen.blit(glow_surf, (rect.x - 10, rect.y - 10))

        # Draw laser beam to hovered target
        if state.decoy_drag_target and hasattr(state.decoy_drag_target, 'rect'):
            # Animated laser beam from dragged card to target
            beam_start = (state.dragging_card.rect.centerx, state.dragging_card.rect.centery)
            beam_end = (state.decoy_drag_target.rect.centerx, state.decoy_drag_target.rect.centery)

            # Pulsing beam effect
            pulse = math.sin(pygame.time.get_ticks() * 0.01) * 0.3 + 0.7
            beam_color = (int(150 * pulse), int(220 * pulse), int(255 * pulse))
            beam_width = int(4 + 2 * math.sin(pygame.time.get_ticks() * 0.01))

            # Draw main beam
            pygame.draw.line(screen, beam_color, beam_start, beam_end, beam_width)

            # Draw glow along the beam
            glow_surf = pygame.Surface((abs(beam_end[0] - beam_start[0]) + 40, 
                                       abs(beam_end[1] - beam_start[1]) + 40), pygame.SRCALPHA)
            glow_start = (20, 20) if beam_start[0] < beam_end[0] else (glow_surf.get_width() - 20, 20)
            glow_end = (glow_surf.get_width() - 20, glow_surf.get_height() - 20) if beam_start[0] < beam_end[0] else (20, glow_surf.get_height() - 20)
            pygame.draw.line(glow_surf, (*beam_color, int(100 * pulse)), glow_start, glow_end, beam_width + 6)
            screen.blit(glow_surf, (min(beam_start[0], beam_end[0]) - 20, min(beam_start[1], beam_end[1]) - 20))

            # Draw glowing circle at target
            target_glow_size = int(20 + 10 * math.sin(pygame.time.get_ticks() * 0.015))
            target_glow = pygame.Surface((target_glow_size * 2, target_glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(target_glow, (*beam_color, int(150 * pulse)), 
                             (target_glow_size, target_glow_size), target_glow_size)
            screen.blit(target_glow, (state.decoy_drag_target.rect.centerx - target_glow_size, 
                                     state.decoy_drag_target.rect.centery - target_glow_size))

    # Draw card inspection overlay (on top of EVERYTHING)
    if state.inspected_card:
        selection_overlays.draw_card_inspection_overlay(screen, state.inspected_card, SCREEN_WIDTH, SCREEN_HEIGHT)

    if state.inspected_leader:
        selection_overlays.draw_leader_inspection_overlay(screen, state.inspected_leader, SCREEN_WIDTH, SCREEN_HEIGHT)

    # Medical Evac selection overlay - draw only, clicks handled in event_handler
    if state.ui_state == UIState.MEDIC_SELECT:
        medic_valid_cards = game.get_medic_valid_cards(game.player1)
        if not medic_valid_cards:
            state.ui_state = UIState.PLAYING
            state.medic_card_played = None
            game.add_history_event(
                "ability",
                f"{game.player1.name}'s medic had no targets to revive",
                "player",
                icon="+"
            )
            game.player1.calculate_score()
            game.player2.calculate_score()
            game.last_turn_actor = game.player1
            game.switch_turn()
            state.overlay_card_rects = []
        else:
            state.overlay_card_rects = selection_overlays.draw_medic_selection_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
    elif state.ui_state == UIState.DECOY_SELECT:
        state.overlay_card_rects = selection_overlays.draw_decoy_selection_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
    elif state.ui_state == UIState.JONAS_PEEK:
        state.overlay_card_rects = selection_overlays.draw_jonas_peek_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
    elif state.ui_state == UIState.BAAL_CLONE_SELECT:
        state.overlay_card_rects = selection_overlays.draw_baal_clone_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
    elif state.ui_state == UIState.VALA_SELECT:
        state.overlay_card_rects = selection_overlays.draw_vala_selection_overlay(screen, state.vala_cards_to_choose, SCREEN_WIDTH, SCREEN_HEIGHT)
    elif state.ui_state == UIState.CATHERINE_SELECT:
        state.overlay_card_rects = selection_overlays.draw_catherine_selection_overlay(screen, state.catherine_cards_to_choose, SCREEN_WIDTH, SCREEN_HEIGHT)
    else:
        state.overlay_card_rects = []

    # Generic leader choice overlay (Jonas Quinn, Ba'al, etc.)
    if state.pending_leader_choice:
        if state.ui_state != UIState.LEADER_CHOICE_SELECT:
            state.ui_state = UIState.LEADER_CHOICE_SELECT
        state.leader_choice_rects = selection_overlays.draw_leader_choice_overlay(screen, state.pending_leader_choice, SCREEN_WIDTH, SCREEN_HEIGHT)
    else:
        state.leader_choice_rects = []

    # Thor move mode - visual indicator only, clicks handled in event_handler
    if state.ui_state == UIState.THOR_MOVE_SELECT:
        indicator_font = cfg.get_font(None, 48)
        indicator_text = indicator_font.render("THOR: Click a unit to move, then click destination row", True, (50, 200, 150))
        indicator_rect = indicator_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        bg_surf = pygame.Surface((indicator_rect.width + 40, indicator_rect.height + 20), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 180))
        screen.blit(bg_surf, (indicator_rect.x - 20, indicator_rect.y - 10))
        screen.blit(indicator_text, indicator_rect)

    # Discard pile viewer overlay
    if state.ui_state == UIState.DISCARD_VIEW:
        selection_overlays.draw_discard_viewer(screen, game.player1.discard_pile, SCREEN_WIDTH, SCREEN_HEIGHT, state.discard_scroll)

    # Context popup for leader column buttons
    if state.button_info_popup and state.ui_state != UIState.PAUSED and not state.inspected_card and not state.inspected_leader:
        expires_at = state.button_info_popup.get("expires_at")
        if expires_at and pygame.time.get_ticks() > expires_at:
            state.button_info_popup = None
        else:
            draw_button_info_popup(screen, state.button_info_popup)

    # Pause menu overlay
    if state.ui_state == UIState.PAUSED:
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Pause menu
        menu_width = 500
        menu_height = 550  # Increased to fit surrender button
        menu_x = (SCREEN_WIDTH - menu_width) // 2
        menu_y = (SCREEN_HEIGHT - menu_height) // 2

        # Menu background
        pygame.draw.rect(screen, (30, 30, 40), (menu_x, menu_y, menu_width, menu_height), border_radius=15)
        pygame.draw.rect(screen, (100, 150, 200), (menu_x, menu_y, menu_width, menu_height), 5, border_radius=15)

        # Title
        pause_font = cfg.get_font("Arial", 56, bold=True)
        title_text = pause_font.render("PAUSED", True, cfg.TEXT_DIM)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, menu_y + 70))
        screen.blit(title_text, title_rect)

        # Buttons
        button_font = cfg.get_font("Arial", 32, bold=True)
        button_width = 350
        button_height = 55
        button_x = (SCREEN_WIDTH - button_width) // 2
        button_spacing = 70
        # mouse_pos already cached at frame start

        # Resume button
        resume_button = pygame.Rect(button_x, menu_y + 140, button_width, button_height)
        resume_hover = resume_button.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (70, 200, 70) if resume_hover else (50, 160, 50), resume_button, border_radius=10)
        pygame.draw.rect(screen, (100, 255, 100) if resume_hover else (80, 180, 80), resume_button, 2, border_radius=10)
        resume_text = button_font.render("RESUME", True, (255, 255, 255))
        resume_rect = resume_text.get_rect(center=resume_button.center)
        screen.blit(resume_text, resume_rect)

        # Options button
        options_button = pygame.Rect(button_x, menu_y + 140 + button_spacing, button_width, button_height)
        options_hover = options_button.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (80, 140, 200) if options_hover else (60, 100, 160), options_button, border_radius=10)
        pygame.draw.rect(screen, (120, 180, 255) if options_hover else (80, 140, 200), options_button, 2, border_radius=10)
        options_text = button_font.render("OPTIONS", True, (255, 255, 255))
        options_rect = options_text.get_rect(center=options_button.center)
        screen.blit(options_text, options_rect)

        # Surrender button (only show if game is still in progress)
        surrender_button = None
        if game.game_state == "playing":
            surrender_button = pygame.Rect(button_x, menu_y + 140 + button_spacing * 2, button_width, button_height)
            surrender_hover = surrender_button.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (180, 100, 50) if surrender_hover else (140, 70, 30), surrender_button, border_radius=10)
            pygame.draw.rect(screen, (220, 140, 80) if surrender_hover else (160, 90, 50), surrender_button, 2, border_radius=10)
            surrender_text = button_font.render("SURRENDER", True, (255, 255, 255))
            surrender_rect = surrender_text.get_rect(center=surrender_button.center)
            screen.blit(surrender_text, surrender_rect)

        # Main Menu button (shifted down if surrender is shown)
        main_menu_offset = 3 if game.game_state == "playing" else 2
        main_menu_button = pygame.Rect(button_x, menu_y + 140 + button_spacing * main_menu_offset, button_width, button_height)
        main_menu_hover = main_menu_button.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (200, 160, 60) if main_menu_hover else (160, 120, 40), main_menu_button, border_radius=10)
        pygame.draw.rect(screen, (255, 200, 100) if main_menu_hover else (180, 140, 60), main_menu_button, 2, border_radius=10)
        menu_text = button_font.render("MAIN MENU", True, (255, 255, 255))
        menu_rect = menu_text.get_rect(center=main_menu_button.center)
        screen.blit(menu_text, menu_rect)

        # Quit button
        quit_offset = 4 if game.game_state == "playing" else 3
        quit_button = pygame.Rect(button_x, menu_y + 140 + button_spacing * quit_offset, button_width, button_height)
        quit_hover = quit_button.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (200, 70, 70) if quit_hover else (160, 50, 50), quit_button, border_radius=10)
        pygame.draw.rect(screen, (255, 100, 100) if quit_hover else (180, 70, 70), quit_button, 2, border_radius=10)
        quit_text = button_font.render("QUIT GAME", True, (255, 255, 255))
        quit_rect = quit_text.get_rect(center=quit_button.center)
        screen.blit(quit_text, quit_rect)

        # Hint text
        hint_font = cfg.get_font("Arial", 18)
        hint_text = hint_font.render("Press ESC to resume | Q to surrender | F11 fullscreen", True, (140, 140, 160))
        hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, menu_y + menu_height - 25))
        screen.blit(hint_text, hint_rect)

        # Store button rects for event handler
        state.pause_menu_buttons = {
            "resume": resume_button,
            "options": options_button,
            "main_menu": main_menu_button,
            "quit": quit_button,
        }
        if surrender_button:
            state.pause_menu_buttons["surrender"] = surrender_button

    # LAN: Waiting for Opponent Overlay
    if LAN_MODE and game.current_player != game.player1 and game.game_state != "game_over" and state.ui_state == UIState.PLAYING:
        # Draw transparent overlay
        wait_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        wait_overlay.fill((0, 0, 0, 100)) # Darken slightly
        screen.blit(wait_overlay, (0, 0))

        # Draw Text
        wait_font = cfg.get_font("Arial", 48, bold=True)
        wait_text = wait_font.render("WAITING FOR OPPONENT...", True, (255, 255, 255))
        wait_rect = wait_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

        # Draw text background
        pygame.draw.rect(screen, (0, 0, 0, 150), wait_rect.inflate(40, 20), border_radius=10)
        screen.blit(wait_text, wait_rect)

    # Debug overlay: FPS counter and performance stats (v4.3.1)
    if DEBUG_MODE:
        current_fps = state.clock.get_fps()
        # FPS counter (top-left corner)
        fps_text = cfg.UI_FONT.render(f"FPS: {current_fps:.1f}", True, (0, 255, 0))
        fps_bg = pygame.Surface((fps_text.get_width() + 10, fps_text.get_height() + 6), pygame.SRCALPHA)
        fps_bg.fill((0, 0, 0, 180))
        screen.blit(fps_bg, (8, 8))
        screen.blit(fps_text, (13, 11))

    pygame.display.flip()
