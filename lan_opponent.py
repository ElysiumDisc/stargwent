"""
NetworkOpponent - Replaces AI opponent for LAN multiplayer.

Instead of AI logic, this class waits for network messages from the remote player
and relays local player actions to the remote player.
"""
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
    it waits for network messages from the remote player.
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
        return self.session and self.session.running

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

        # Poll for network message
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

        if msg_type == LanMessageType.GAME_ACTION.value:
            action_type = payload.get("action")
            data = payload.get("data", {})
            target_id = payload.get("target_id")

            if action_type == "play_card":
                # Find the card in hand
                card_id = data.get("card_id")
                row = data.get("row")

                # Find card object in hand
                for card in self.network_player.hand:
                    if card.id == card_id:
                        return (card, row)

                # Card not found in hand
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

    def __init__(self, session: LanSession, role: str):
        """
        Initialize proxy.

        Args:
            session: LAN session for sending actions
            role: "host" or "client"
        """
        self.session = session
        self.role = role
        self.turn_token_counter = 0

    def next_turn_token(self) -> str:
        """Generate next turn token."""
        self.turn_token_counter += 1
        return f"{self.role}-{self.turn_token_counter}"

    def _send_action(self, action_type: str, data: Dict[str, Any], target_id: Optional[str] = None):
        turn_token = self.next_turn_token()
        msg = build_action_message(action_type, data, turn_token=turn_token, target_id=target_id)
        self.session.send(msg["type"], msg["payload"])

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
