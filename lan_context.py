from dataclasses import dataclass
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

    def next_turn_token(self) -> str:
        self.turn_token += 1
        return f"{self.role}-{self.turn_token}"
