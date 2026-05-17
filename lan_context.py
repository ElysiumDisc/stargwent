import threading
from dataclasses import dataclass, field
from typing import List, Optional
from lan_session import LanSession


@dataclass
class LanDeckSelection:
    faction: str
    leader_id: str
    deck_ids: List[str]


@dataclass
class LanContext:
    session: LanSession
    role: str  # "host" or "client"
    local: LanDeckSelection
    remote: LanDeckSelection
    seed: int
    turn_token: int = 0
    # Lock protecting turn_token increments. Without it the UI thread,
    # network reader, and game loop can collide and hand out duplicate
    # tokens — the very thing the lan_opponent gap detector treats as
    # fatal desync.
    _token_lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    def next_turn_token(self) -> str:
        with self._token_lock:
            self.turn_token += 1
            token = self.turn_token
        return f"{self.role}-{token}"
