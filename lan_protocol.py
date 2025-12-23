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


class LanMessageType(str, Enum):
    CHAT = "chat"
    DECK_SELECTION = "deck_selection"
    SEED = "seed"
    GAME_ACTION = "game_action"
    MULLIGAN = "mulligan"
    LEADER_MATCHUP_READY = "leader_ready"
    READY_CHECK = "ready_check"
    STATUS = "status"
    TYPING = "typing"


def build_message(message_type: LanMessageType, payload: Optional[Dict[str, Any]] = None, turn_token: Optional[str] = None) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "type": message_type.value,
        "payload": payload or {},
    }
    if turn_token is not None:
        msg["turn_token"] = turn_token
    return msg


def build_chat_message(text: str) -> Dict[str, Any]:
    return build_message(LanMessageType.CHAT, {"text": text})


def build_deck_message(faction: str, leader_id: str, deck_ids: list[str]) -> Dict[str, Any]:
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
    return raw
