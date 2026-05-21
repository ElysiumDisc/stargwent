"""
Co-op Space Shooter Network Protocol

Message types and builders for LAN co-op arcade mode.
Reuses the existing LanSession transport layer (TCP JSON).
"""

import base64
import json
import zlib


# Snapshots small enough to fit comfortably in a single TCP packet aren't
# worth compressing — the per-message zlib + base64 overhead outweighs the
# savings.  Anything larger benefits substantially (JSON's verbose dict
# keys compress to ~25% of the wire size at level 1).
_COMPRESS_THRESHOLD_BYTES = 1024


def pack_state_payload(snapshot: dict) -> dict:
    """Wrap a host state snapshot for transmission.

    Returns the snapshot dict unchanged if it's small; otherwise returns
    a compressed envelope ``{"_z": True, "data": "<base64>"}`` that
    ``unpack_state_payload`` decodes back into the original dict.

    Level 1 compression is intentional — this runs on the host's main
    thread every 50 ms and we'd rather spend bandwidth than frame time.
    """
    raw = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
    if len(raw) < _COMPRESS_THRESHOLD_BYTES:
        return snapshot
    compressed = zlib.compress(raw, 1)
    return {
        "_z": True,
        "data": base64.b64encode(compressed).decode("ascii"),
    }


def unpack_state_payload(payload):
    """Reverse of ``pack_state_payload``.

    If *payload* is a compressed envelope, return the decoded snapshot
    dict.  Otherwise return *payload* unchanged so old (pre-12.8) host
    snapshots still flow through.
    """
    if isinstance(payload, dict) and payload.get("_z"):
        try:
            raw = zlib.decompress(base64.b64decode(payload["data"]))
            return json.loads(raw.decode("utf-8"))
        except (ValueError, zlib.error):
            # Corrupt envelope — return an empty snapshot so the client
            # falls back to its last interpolated state instead of
            # crashing on a missing field.
            return {}
    return payload


class CoopMsg:
    """Message type constants for co-op space shooter."""
    # Lobby / handshake
    READY = "ss_ready"          # Player ready with faction choice
    # In-game
    INPUT = "ss_input"          # Client → Host: input state each frame
    STATE = "ss_state"          # Host → Client: world snapshot (20 Hz)
    ACTION = "ss_action"        # Discrete one-shot actions (secondary fire, wormhole)
    LEVEL_UP = "ss_level_up"    # Host → Client: level-up choice notification
    GAME_OVER = "ss_game_over"  # Host → Client: game ended
    HEARTBEAT = "ss_heartbeat"  # Bidirectional keep-alive
    DISCONNECT = "ss_disconnect"  # Graceful disconnect notification


def build_ready(faction, variant=0):
    """Build a ready message with chosen faction and variant."""
    return {"type": CoopMsg.READY, "payload": {"faction": faction, "variant": variant}}


def build_input(keys_state):
    """Build an input message from a dict of pressed keys.

    keys_state: dict with bool values for 'up', 'down', 'left', 'right',
                'shift', 'e', 'q'
    """
    return {"type": CoopMsg.INPUT, "payload": keys_state}


def build_state(snapshot):
    """Build a state snapshot message.

    snapshot: dict with serialized game state (ships, enemies, projectiles, etc.)
    """
    return {"type": CoopMsg.STATE, "payload": snapshot}


def build_action(action_type, data=None):
    """Build a discrete action message (e.g. secondary fire, wormhole)."""
    return {"type": CoopMsg.ACTION, "payload": {"action": action_type, "data": data or {}}}


def build_level_up(choices=None, selected=None):
    """Build a level-up notification.

    choices: list of upgrade names offered (host → client info)
    selected: name of chosen upgrade (host → client confirmation)
    """
    return {
        "type": CoopMsg.LEVEL_UP,
        "payload": {"choices": choices, "selected": selected},
    }


def build_game_over(stats):
    """Build a game-over message with combined stats."""
    return {"type": CoopMsg.GAME_OVER, "payload": stats}


def build_heartbeat():
    """Build a heartbeat keep-alive message."""
    return {"type": CoopMsg.HEARTBEAT, "payload": {}}


def build_disconnect(reason=""):
    """Build a graceful disconnect notification."""
    return {"type": CoopMsg.DISCONNECT, "payload": {"reason": reason}}
