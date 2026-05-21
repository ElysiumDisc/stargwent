"""
Shared message helpers for Stargwent LAN multiplayer.

Each packet we send through LanSession is a small JSON document with:
{
    "type": "<message_type>",
    "payload": {...},
    "turn_token": optional str/int added to every in-game action
}

This module centralises the allowed message types + helper builders so both
the UI layer and the upcoming networked game loop speak the same language.
"""

from enum import Enum
from typing import Any, Dict, Optional


# Wire-protocol version. Bumped whenever we change message shapes or add
# new required message types. Peers exchange this on the initial HELLO
# handshake and disconnect with a clear error if they don't match. This
# prevents silent cross-version desyncs — the scariest LAN failure mode.
#
# v3 (12.8.0): co-op space shooter STATE snapshots above ~1 KB are now
# transmitted as zlib+base64 envelopes (see coop_protocol.pack_state_payload).
PROTOCOL_VERSION = 3

# Caps to reject malicious or malformed payloads before they hit game logic.
# MAX_DECK_IDS matches deck_builder.MAX_DECK_SIZE; MAX_PAYLOAD_BYTES sized for
# the largest legitimate message (a full deck selection ≈ 2KB) with headroom.
MAX_DECK_IDS = 40
MAX_CHAT_LEN = 512
MAX_PAYLOAD_BYTES = 65536


class LanMessageType(str, Enum):
    HELLO = "hello"  # First message after connect: protocol/game version exchange
    CHAT = "chat"
    CHAT_ACK = "chat_ack"  # Message delivery confirmation
    DECK_SELECTION = "deck_selection"
    SEED = "seed"
    GAME_ACTION = "game_action"
    MULLIGAN = "mulligan"
    LEADER_MATCHUP_READY = "leader_ready"
    READY_CHECK = "ready_check"
    STATUS = "status"
    TYPING = "typing"
    DISCONNECT = "disconnect"
    CONCEDE = "concede"  # L3: graceful surrender in PvP
    PLAY_AGAIN = "play_again"
    KEEPALIVE = "keepalive"
    PING = "ping"  # Latency measurement request
    PONG = "pong"  # Latency measurement response


def build_message(message_type: LanMessageType, payload: Optional[Dict[str, Any]] = None, turn_token: Optional[str] = None) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "type": message_type.value,
        "payload": payload or {},
    }
    if turn_token is not None:
        msg["turn_token"] = turn_token
    return msg


def build_hello_message(game_version: str, role: str, player_name: Optional[str] = None) -> Dict[str, Any]:
    """Build the initial HELLO handshake packet.

    Sent immediately after TCP connect so both peers can verify they
    speak the same protocol before any game state is exchanged.
    """
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "game_version": game_version,
        "role": role,
    }
    if player_name:
        payload["player_name"] = player_name
    return build_message(LanMessageType.HELLO, payload)


def build_chat_message(text: str) -> Dict[str, Any]:
    if len(text) > MAX_CHAT_LEN:
        text = text[:MAX_CHAT_LEN]
    return build_message(LanMessageType.CHAT, {"text": text})


def build_deck_message(faction: str, leader_id: str, deck_ids: list[str]) -> Dict[str, Any]:
    if len(deck_ids) > MAX_DECK_IDS:
        raise ValueError(f"deck_ids too long: {len(deck_ids)} > {MAX_DECK_IDS}")
    return build_message(
        LanMessageType.DECK_SELECTION,
        {
            "faction": faction,
            "leader_id": leader_id,
            "deck_ids": deck_ids,
        },
    )


def build_seed_message(seed: int) -> Dict[str, Any]:
    return build_message(LanMessageType.SEED, {"seed": seed})


def build_action_message(action_type: str, data: Dict[str, Any], *, turn_token: str, target_id: Optional[str] = None, p1_score: Optional[int] = None, p2_score: Optional[int] = None) -> Dict[str, Any]:
    payload = {"action": action_type, "data": data}
    if target_id is not None:
        payload["target_id"] = target_id
    if p1_score is not None:
        payload["p1_score"] = p1_score
    if p2_score is not None:
        payload["p2_score"] = p2_score
    return build_message(LanMessageType.GAME_ACTION, payload, turn_token=turn_token)


def build_mulligan_message(indices: list[int], *, turn_token: str) -> Dict[str, Any]:
    payload = {"indices": indices}
    return build_message(LanMessageType.MULLIGAN, payload, turn_token=turn_token)


def build_concede_message() -> Dict[str, Any]:
    """L3: graceful surrender in PvP. Remote peer ends with a victory flash."""
    return build_message(LanMessageType.CONCEDE, {})


# Reasonable bounds for game-state-bearing fields. Anything outside is
# either malicious or a bug — reject before it reaches game logic.
MAX_SCORE = 500
MAX_TARGET_ID_LEN = 64
MAX_HAND_SIZE = 30
# Whitelist of GAME_ACTION sub-actions. Mirrors the actions sent by
# NetworkPlayerProxy._send_action() in lan_opponent.py. Keep narrow; if
# a new action is added there, add it here too or it'll be rejected.
ALLOWED_GAME_ACTIONS = {
    "play_card",
    "pass",
    "faction_power",
    "leader_ability",
    "medic_choice",
    "decoy_choice",
}


def parse_message(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basic validation: ensure a known type and expected payload structure.
    Returns the message if valid, otherwise raises ValueError.
    """
    if "type" not in raw:
        raise ValueError("Missing message type")
    msg_type = raw["type"]
    if msg_type not in {mt.value for mt in LanMessageType}:
        raise ValueError(f"Unknown LAN message type: {msg_type}")
    if "payload" not in raw:
        raw["payload"] = {}
    payload = raw["payload"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    # Reject obviously malicious payloads before they reach game state.
    if msg_type == LanMessageType.DECK_SELECTION.value:
        deck_ids = payload.get("deck_ids", [])
        if not isinstance(deck_ids, list) or len(deck_ids) > MAX_DECK_IDS:
            raise ValueError(f"deck_ids invalid or too long ({len(deck_ids) if isinstance(deck_ids, list) else 'not-list'})")
        # Each deck entry must be a short non-empty string (card id).
        for cid in deck_ids:
            if not isinstance(cid, str) or not cid or len(cid) > MAX_TARGET_ID_LEN:
                raise ValueError(f"invalid deck_id entry: {cid!r}")

    elif msg_type == LanMessageType.CHAT.value:
        text = payload.get("text", "")
        if isinstance(text, str) and len(text) > MAX_CHAT_LEN:
            payload["text"] = text[:MAX_CHAT_LEN]

    elif msg_type == LanMessageType.SEED.value:
        seed = payload.get("seed")
        if not isinstance(seed, int) or not (0 <= seed < 2**32):
            raise ValueError(f"seed must be uint32, got {seed!r}")

    elif msg_type == LanMessageType.GAME_ACTION.value:
        action = payload.get("action")
        if action not in ALLOWED_GAME_ACTIONS:
            raise ValueError(f"unknown game action: {action!r}")
        if "data" in payload and not isinstance(payload["data"], dict):
            raise ValueError("game_action.data must be an object")
        target_id = payload.get("target_id")
        if target_id is not None:
            if not isinstance(target_id, str) or len(target_id) > MAX_TARGET_ID_LEN:
                raise ValueError(f"invalid target_id: {target_id!r}")
        for score_field in ("p1_score", "p2_score"):
            val = payload.get(score_field)
            if val is None:
                continue
            if not isinstance(val, int) or not (0 <= val <= MAX_SCORE):
                raise ValueError(f"{score_field} out of range: {val!r}")

    elif msg_type == LanMessageType.MULLIGAN.value:
        indices = payload.get("indices", [])
        if not isinstance(indices, list) or len(indices) > MAX_HAND_SIZE:
            raise ValueError(f"mulligan indices invalid or too long: {indices!r}")
        for i in indices:
            if not isinstance(i, int) or not (0 <= i < MAX_HAND_SIZE):
                raise ValueError(f"mulligan index out of range: {i!r}")

    return raw
