"""
STARGWENT - GALACTIC CONQUEST - Campaign State

Dataclass and serialization for the persistent campaign state.
"""

from dataclasses import dataclass, field


@dataclass
class CampaignState:
    """Persistent state for a Galactic Conquest campaign run."""
    player_faction: str
    player_leader: dict                     # {name, ability, ability_desc, card_id, faction}
    current_deck: list                      # list of card ID strings — evolves via roguelite rewards
    naquadah: int = 100                     # starting currency
    turn_number: int = 1
    planet_ownership: dict = field(default_factory=dict)  # planet_id → faction/"player"
    cooldowns: dict = field(default_factory=dict)          # planet_id → turns remaining
    galaxy: dict = field(default_factory=dict)             # serialized GalaxyMap
    seed: int = 0
    upgraded_cards: dict = field(default_factory=dict)     # card_id → power bonus
    friendly_faction: str = None                            # allied faction (their territory = yours)
    neutral_count: int = 5                                  # number of neutral planets
    enemy_leaders: dict = field(default_factory=dict)       # faction → leader name (homeworld defenders)
    fortification_levels: dict = field(default_factory=dict)  # planet_id → 0-3
    relics: list = field(default_factory=list)               # relic ID strings
    narrative_progress: dict = field(default_factory=dict)   # arc_id → [planet_names conquered]

    def to_dict(self) -> dict:
        """Serialize campaign state to a JSON-friendly dictionary."""
        return {
            "player_faction": self.player_faction,
            "player_leader": self.player_leader,
            "current_deck": list(self.current_deck),
            "naquadah": self.naquadah,
            "turn_number": self.turn_number,
            "planet_ownership": dict(self.planet_ownership),
            "cooldowns": dict(self.cooldowns),
            "galaxy": self.galaxy,
            "seed": self.seed,
            "upgraded_cards": dict(self.upgraded_cards),
            "friendly_faction": self.friendly_faction,
            "neutral_count": self.neutral_count,
            "enemy_leaders": dict(self.enemy_leaders),
            "fortification_levels": dict(self.fortification_levels),
            "relics": list(self.relics),
            "narrative_progress": {k: list(v) for k, v in self.narrative_progress.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CampaignState":
        """Deserialize campaign state from a dictionary."""
        return cls(
            player_faction=data["player_faction"],
            player_leader=data["player_leader"],
            current_deck=data.get("current_deck", []),
            naquadah=data.get("naquadah", 100),
            turn_number=data.get("turn_number", 1),
            planet_ownership=data.get("planet_ownership", {}),
            cooldowns=data.get("cooldowns", {}),
            galaxy=data.get("galaxy", {}),
            seed=data.get("seed", 0),
            upgraded_cards=data.get("upgraded_cards", {}),
            friendly_faction=data.get("friendly_faction"),
            neutral_count=data.get("neutral_count", 5),
            enemy_leaders=data.get("enemy_leaders", {}),
            fortification_levels=data.get("fortification_levels", {}),
            relics=data.get("relics", []),
            narrative_progress=data.get("narrative_progress", {}),
        )

    def tick_cooldowns(self):
        """Decrement all cooldowns by 1 and remove expired ones."""
        expired = []
        for planet_id, turns in self.cooldowns.items():
            self.cooldowns[planet_id] = turns - 1
            if self.cooldowns[planet_id] <= 0:
                expired.append(planet_id)
        for pid in expired:
            del self.cooldowns[pid]

    def add_naquadah(self, amount: int):
        """Add (or subtract) naquadah, clamped to 0."""
        self.naquadah = max(0, self.naquadah + amount)

    def upgrade_card(self, card_id: str, bonus: int = 1):
        """Permanently upgrade a card's power for this run."""
        self.upgraded_cards[card_id] = self.upgraded_cards.get(card_id, 0) + bonus

    def add_card(self, card_id: str):
        """Add a card to the deck."""
        self.current_deck.append(card_id)

    def remove_card(self, card_id: str):
        """Remove one copy of a card from the deck."""
        if card_id in self.current_deck:
            self.current_deck.remove(card_id)

    def add_relic(self, relic_id: str):
        """Add a relic if not already owned."""
        if relic_id not in self.relics:
            self.relics.append(relic_id)

    def has_relic(self, relic_id: str) -> bool:
        """Check if player owns a relic."""
        return relic_id in self.relics
