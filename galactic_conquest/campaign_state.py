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
    conquest_ability_data: dict = field(default_factory=dict)  # leader ability persistent state
    attacks_this_turn: int = 0                                 # attacks made this turn (for multi-attack abilities)
    difficulty: str = "normal"                                 # easy/normal/hard/insane
    faction_relations: dict = field(default_factory=dict)      # faction → "hostile"/"neutral"/"trading"/"allied"
    buildings: dict = field(default_factory=dict)               # planet_id → building_type string
    meta_points_earned: int = 0                                 # conquest points earned this run
    network_tier: int = 1                                       # current stargate network tier
    crisis_cooldown: int = 0                                    # turns until next crisis can fire
    minor_world_states: dict = field(default_factory=dict)       # planet_id -> MinorWorldState dict
    wisdom: int = 0                                               # doctrine currency
    adopted_policies: list = field(default_factory=list)          # policy_id strings
    completed_doctrines: list = field(default_factory=list)       # tree_id strings
    supergate_progress: dict = field(default_factory=lambda: {"built": False, "turns_held": 0})
    operatives: list = field(default_factory=list)                # Operative dicts
    operative_next_id: int = 0
    operative_earn_turns: list = field(default_factory=lambda: [5, 10, 16])
    building_levels: dict = field(default_factory=dict)                   # planet_id -> 1/2/3
    pending_crisis: dict = field(default_factory=dict)                    # crisis dict with choices (empty = none)
    wisdom_actions_this_turn: int = 0                                     # reset each turn
    turns_held: dict = field(default_factory=dict)                        # planet_id → turns owned (development track)

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
            "conquest_ability_data": dict(self.conquest_ability_data),
            "attacks_this_turn": self.attacks_this_turn,
            "difficulty": self.difficulty,
            "faction_relations": dict(self.faction_relations),
            "buildings": dict(self.buildings),
            "meta_points_earned": self.meta_points_earned,
            "network_tier": self.network_tier,
            "crisis_cooldown": self.crisis_cooldown,
            "minor_world_states": dict(self.minor_world_states),
            "wisdom": self.wisdom,
            "adopted_policies": list(self.adopted_policies),
            "completed_doctrines": list(self.completed_doctrines),
            "supergate_progress": dict(self.supergate_progress),
            "operatives": list(self.operatives),
            "operative_next_id": self.operative_next_id,
            "operative_earn_turns": list(self.operative_earn_turns),
            "building_levels": dict(self.building_levels),
            "pending_crisis": dict(self.pending_crisis),
            "wisdom_actions_this_turn": self.wisdom_actions_this_turn,
            "turns_held": dict(self.turns_held),
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
            conquest_ability_data=data.get("conquest_ability_data", {}),
            attacks_this_turn=data.get("attacks_this_turn", 0),
            difficulty=data.get("difficulty", "normal"),
            faction_relations=data.get("faction_relations", {}),
            buildings=data.get("buildings", {}),
            meta_points_earned=data.get("meta_points_earned", 0),
            network_tier=data.get("network_tier", 1),
            crisis_cooldown=data.get("crisis_cooldown", 0),
            minor_world_states=data.get("minor_world_states", {}),
            wisdom=data.get("wisdom", 0),
            adopted_policies=data.get("adopted_policies", []),
            completed_doctrines=data.get("completed_doctrines", []),
            supergate_progress=data.get("supergate_progress", {"built": False, "turns_held": 0}),
            operatives=data.get("operatives", []),
            operative_next_id=data.get("operative_next_id", 0),
            operative_earn_turns=data.get("operative_earn_turns", [5, 10, 16]),
            building_levels=data.get("building_levels", {}),
            pending_crisis=data.get("pending_crisis", {}),
            wisdom_actions_this_turn=data.get("wisdom_actions_this_turn", 0),
            turns_held=data.get("turns_held", {}),
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
