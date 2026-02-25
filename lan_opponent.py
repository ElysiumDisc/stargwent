"""
NetworkOpponent - Replaces AI opponent for LAN multiplayer.

Instead of AI logic, this class waits for network messages from the remote player
and relays local player actions to the remote player.
"""
import time
import pygame
from typing import Optional, Dict, Any
from lan_session import LanSession
from lan_protocol import (
    LanMessageType,
    build_action_message,
    build_mulligan_message,
    parse_message,
)


class NetworkOpponent:
    """
    Network-based opponent that replaces AIOpponent for LAN games.

    This class mirrors the AIOpponent interface but instead of computing moves,
    it waits for the remote player to send their action.
    """

    def __init__(self, session: LanSession, role: str):
        """
        Initialize network opponent.

        Args:
            session: Active LAN session for communication
            role: "host" or "client" - determines turn order
        """
        self.session = session
        self.role = role
        self.turn_token_counter = 0
        self.waiting_for_action = False
        self.last_received_action = None

    def next_turn_token(self) -> str:
        """Generate next turn token for action validation."""
        self.turn_token_counter += 1
        return f"{self.role}-{self.turn_token_counter}"

    def make_move(self, player, opponent, board_state):
        """
        Wait for network action from remote player.

        This replaces AIOpponent.make_move(). Instead of computing a move,
        it waits for the remote player to send their action.

        Args:
            player: The network player (remote)
            opponent: The local player
            board_state: Current game state

        Returns:
            Dict with action details, or None if waiting
        """
        # Poll for messages from remote player
        msg = self.session.receive()
        if not msg:
            # No message yet - still waiting
            return None

        try:
            parsed = parse_message(msg)
        except ValueError:
            print(f"[NetworkOpponent] Invalid message received: {msg}")
            return None

        msg_type = parsed.get("type")
        payload = parsed.get("payload", {})

        # Handle different action types
        if msg_type == LanMessageType.GAME_ACTION.value:
            action_type = payload.get("action")
            data = payload.get("data", {})
            target_id = payload.get("target_id")

            # Return action in format expected by game loop
            return {
                "type": action_type,
                "data": data,
                "target_id": target_id
            }

        elif msg_type == LanMessageType.MULLIGAN.value:
            # Mulligan action
            indices = payload.get("indices", [])
            return {
                "type": "mulligan",
                "indices": indices
            }

        elif msg_type == "disconnect":
            print("[NetworkOpponent] Remote player disconnected!")
            return {
                "type": "disconnect"
            }

        # Unknown message type - ignore
        return None

    def send_action(self, action_type: str, data: Dict[str, Any], target_id: Optional[str] = None):
        """
        Send local player's action to remote player.

        Args:
            action_type: Type of action (e.g., "play_card", "pass", "faction_power")
            data: Action-specific data
        """
        turn_token = self.next_turn_token()
        msg = build_action_message(action_type, data, turn_token=turn_token, target_id=target_id)
        self.session.send(msg["type"], msg["payload"])

    def send_mulligan(self, indices: list):
        """
        Send mulligan selection to remote player.

        Args:
            indices: List of card indices to mulligan
        """
        turn_token = self.next_turn_token()
        msg = build_mulligan_message(indices, turn_token=turn_token)
        self.session.send(msg["type"], msg["payload"])

    def is_connected(self) -> bool:
        """Check if session is still active."""
        return self.session and self.session.is_connected()

    def close(self):
        """Close the network session."""
        if self.session:
            self.session.close()


class NetworkController:
    """
    Network controller that matches AIController interface.

    This replaces AIController for LAN games. Instead of AI logic,
    it waits for network messages from the remote player.
    """

    def __init__(self, game, network_player, session: LanSession, role: str):
        """
        Initialize network controller.

        Args:
            game: Game instance
            network_player: The network-controlled player (player2 typically)
            session: LAN session for communication
            role: "host" or "client"
        """
        self.game = game
        self.network_player = network_player
        self.session = session
        self.role = role
        self.turn_token_counter = 0
        self.pending_verification = None  # Stores (p1_score, p2_score) from last action to verify
        self.desync_detected = False
        self.desync_message = None  # (text, expire_tick) for HUD flash
        self.card_not_found_count = 0  # Track consecutive card-not-found errors

    def _find_card_in_discard(self, player, card_id):
        if not card_id:
            return None
        for card in player.discard_pile:
            if card.id == card_id:
                return card
        return None

    def _find_card_on_board(self, card_id):
        if not card_id:
            return None
        for player in [self.game.player1, self.game.player2]:
            for row_cards in player.board.values():
                for card in row_cards:
                    if card.id == card_id:
                        return card
        return None

    def choose_move(self):
        """
        Wait for network action and return (card, row) tuple.

        This matches AIController.choose_move() interface.
        Returns: (card, row) tuple where card is Card object or None
        """
        if self.network_player.has_passed:
            return (None, None)

        # 1. State Verification (Post-Move Check)
        if self.pending_verification:
            expected_p1, expected_p2 = self.pending_verification
            current_p1 = self.game.player1.score
            current_p2 = self.game.player2.score
            
            # Allow for small timing differences, but scores should match after move is fully processed
            if current_p1 != expected_p1 or current_p2 != expected_p2:
                print(f"[Network] DESYNC DETECTED! Expected ({expected_p1}-{expected_p2}), Got ({current_p1}-{current_p2})")
                self.desync_detected = True
                # Store flash message for HUD display (expires after 5 seconds)
                import pygame
                self.desync_message = (
                    f"Score desync: expected {expected_p1}-{expected_p2}, got {current_p1}-{current_p2}",
                    pygame.time.get_ticks() + 5000
                )
                # Also push to game history so it's logged
                self.game.add_history_event(
                    "system",
                    f"Score desync detected ({expected_p1}-{expected_p2} vs {current_p1}-{current_p2})",
                    "ai",
                    icon="!"
                )
            
            self.pending_verification = None

        # 2. Poll for network message
        msg = self.session.receive()
        if not msg:
            # No message yet - return None to indicate waiting
            return (None, None)

        try:
            parsed = parse_message(msg)
        except ValueError:
            return (None, None)

        msg_type = parsed.get("type")
        payload = parsed.get("payload", {})

        # Extract scores for verification on NEXT tick (after action is applied)
        p1_score = payload.get("p1_score")
        p2_score = payload.get("p2_score")
        if p1_score is not None and p2_score is not None:
            self.pending_verification = (p1_score, p2_score)

        if msg_type == LanMessageType.GAME_ACTION.value:
            action_type = payload.get("action")
            data = payload.get("data", {})
            target_id = payload.get("target_id")

            # Send ACK for this action so sender knows it arrived
            msg_id = payload.get("msg_id")
            if msg_id:
                self.session.send("action_ack", {"msg_id": msg_id})

            if action_type == "play_card":
                # Find the card in hand
                card_id = data.get("card_id")
                row = data.get("row")

                # Find card object in hand
                for card in self.network_player.hand:
                    if card.id == card_id:
                        self.card_not_found_count = 0  # Reset on success
                        return (card, row)

                # Card not found in hand — log details and track failures
                hand_ids = [c.id for c in self.network_player.hand]
                print(f"[Network] Error: Card {card_id} not found in hand! Hand: {hand_ids}")
                self.card_not_found_count += 1
                # Flash desync warning so the player knows something went wrong
                self.desync_message = (
                    f"Card desync: opponent's card not found (#{self.card_not_found_count})",
                    pygame.time.get_ticks() + 4000
                )
                self.game.add_history_event(
                    "system",
                    f"Card sync error — opponent card {card_id[:8]} not in hand ({self.card_not_found_count}/3)",
                    "ai",
                    icon="!"
                )
                if self.card_not_found_count >= 3:
                    print(f"[Network] Card not found {self.card_not_found_count} times — forcing pass to prevent hang")
                    self.game.add_history_event(
                        "system",
                        "Too many card sync errors — auto-passing opponent turn",
                        "ai",
                        icon="!"
                    )
                    self.card_not_found_count = 0
                    self.game.pass_turn()
                return (None, None)

            elif action_type == "pass":
                # Pass turn
                self.game.pass_turn()
                return (None, None)

            elif action_type == "faction_power":
                # Use faction power
                if not self.network_player.power_used:
                    self.network_player.power_used = True
                    if self.network_player.faction_power:
                        if self.network_player.faction_power.activate(self.game, self.network_player):
                            self.game.add_history_event(
                                "faction_power",
                                f"{self.network_player.name} used {self.network_player.faction_power.name}",
                                "network"
                            )
                return (None, None)
            elif action_type == "leader_ability":
                self.game.apply_remote_leader_ability(self.network_player, data)
                return (None, None)
            elif action_type == "medic_choice":
                card = self._find_card_in_discard(self.network_player, target_id)
                if card:
                    self.game.trigger_medic(self.network_player, card)
                    self.game.player1.calculate_score()
                    self.game.player2.calculate_score()
                    self.game.last_turn_actor = self.network_player
                    self.game.switch_turn()
                return (None, None)
            elif action_type == "decoy_choice":
                card = self._find_card_on_board(target_id)
                if card and self.game.apply_decoy(card):
                    self.game.player1.calculate_score()
                    self.game.player2.calculate_score()
                    self.game.last_turn_actor = self.network_player
                    self.game.switch_turn()
                return (None, None)

        elif msg_type == "action_ack":
            # ACK for an action we sent — no game logic needed, just informational
            return (None, None)

        elif msg_type == "disconnect":
            print("[NetworkController] Remote player disconnected!")
            return (None, None)

        # Unknown or unhandled message
        return (None, None)


class NetworkPlayerProxy:
    """
    Captures local player actions and sends them over network.

    This wraps around player actions to automatically send them to
    the remote opponent for replay.
    """

    def __init__(self, session: LanSession, role: str, game=None):
        """
        Initialize proxy.

        Args:
            session: LAN session for sending actions
            role: "host" or "client"
            game: Game instance (for score validation)
        """
        self.session = session
        self.role = role
        self.game = game
        self.turn_token_counter = 0
        self._msg_id_counter = 0
        self._pending_acks = {}  # msg_id -> send_time

    def next_turn_token(self) -> str:
        """Generate next turn token."""
        self.turn_token_counter += 1
        return f"{self.role}-{self.turn_token_counter}"

    def _send_action(self, action_type: str, data: Dict[str, Any], target_id: Optional[str] = None):
        turn_token = self.next_turn_token()

        # Attach msg_id for ACK tracking
        self._msg_id_counter += 1
        msg_id = f"{self.role}-{self._msg_id_counter}"

        # Capture scores for validation
        p1_score = None
        p2_score = None
        if self.game:
            p1_score = self.game.player1.score
            p2_score = self.game.player2.score

        msg = build_action_message(
            action_type,
            data,
            turn_token=turn_token,
            target_id=target_id,
            p1_score=p1_score,
            p2_score=p2_score
        )
        # Inject msg_id into payload for ACK tracking
        msg["payload"]["msg_id"] = msg_id
        self._pending_acks[msg_id] = time.time()
        self.session.send(msg["type"], msg["payload"])

        # Check for stale unacked messages (>3s) — log warning but don't disconnect
        stale = [mid for mid, t in self._pending_acks.items() if time.time() - t > 3.0]
        for mid in stale:
            print(f"[NetworkProxy] Warning: action {mid} unacked after 3s")
            del self._pending_acks[mid]

    def send_play_card(self, card_id: str, row: str):
        """
        Send card play action to remote player.

        Args:
            card_id: ID of card being played
            row: Row where card is being played
        """
        self._send_action("play_card", {"card_id": card_id, "row": row})

    def send_pass(self):
        """Send pass action to remote player."""
        self._send_action("pass", {})

    def send_faction_power(self, power_type: str = ""):
        """
        Send faction power activation to remote player.

        Args:
            power_type: Type of faction power (for logging)
        """
        self._send_action("faction_power", {"power_type": power_type})

    def send_leader_ability(self, ability_name: str, data: Optional[Dict[str, Any]] = None):
        """Send leader ability activation/result to remote player."""
        payload = {"ability": ability_name}
        if data:
            payload.update(data)
        self._send_action("leader_ability", payload)

    def send_mulligan(self, indices: list):
        """
        Send mulligan selection to remote player.

        Args:
            indices: List of card indices to mulligan
        """
        turn_token = self.next_turn_token()
        msg = build_mulligan_message(indices, turn_token=turn_token)
        self.session.send(msg["type"], msg["payload"])

    def send_medic_choice(self, target_card_id: str):
        """Send medic revive selection."""
        self._send_action("medic_choice", {}, target_id=target_card_id)

    def send_decoy_choice(self, target_card_id: str):
        """Send decoy target selection."""
        self._send_action("decoy_choice", {}, target_id=target_card_id)

    def process_ack(self, msg_id: str):
        """Remove an acknowledged action from pending tracking."""
        self._pending_acks.pop(msg_id, None)