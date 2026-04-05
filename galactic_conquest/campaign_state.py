"""
STARGWENT - GALACTIC CONQUEST - Campaign State

Dataclass and serialization for the persistent campaign state.

Save schema is versioned via SCHEMA_VERSION. `from_dict` runs all saves
through `_migrate` first, which seeds new fields for older saves in one
centralized place so we never scatter `.get(key, default)` guards.
"""

from dataclasses import dataclass, field


# Bump whenever we add fields to CampaignState. Paired with a
# _migrate_{prev}_to_{new} function below.
SCHEMA_VERSION = 11


def _migrate_10_to_11(data: dict) -> dict:
    """Seed all 11.0 fields on a pre-11 save in one place.

    Covers every new field added by the 11.0 release so downstream code
    can assume they exist. Also converts legacy NAP keys in
    `conquest_ability_data` into the new `treaties` list.

    Does NOT mutate the input dict — returns a new dict with updates.
    """
    data = dict(data)
    # Any nested dict/list we'll mutate needs its own copy.
    data["conquest_ability_data"] = dict(data.get("conquest_ability_data", {}))
    data["treaties"] = list(data.get("treaties", []))

    # --- New 11.0 state fields (G2a, G2b, G3, G4, G5, G6, G7, G8) ---
    data.setdefault("act", 1)
    data.setdefault("consecutive_high_income_turns", 0)
    data.setdefault("ai_doctrines", {})
    data.setdefault("broken_treaty_counts", {})
    data.setdefault("coalition", {
        "active": False,
        "members": [],
        "turns_remaining": 0,
        "trust": {},
    })
    data.setdefault("quest_chain_progress", {})
    data.setdefault("minor_world_rival", {})
    data.setdefault("relic_active_charges", {})
    data.setdefault("espionage_blocks", {})

    # --- Legacy NAP key migration (G8) ---
    # Old format stored NAPs as "_nap_timer_{faction}" keys in
    # conquest_ability_data. Convert each to a Treaty dict so the new
    # diplomacy layer has a single source of truth.  Only the timer
    # keys migrate — "_nap_broken_*" flags stay put because they're
    # still read by the counterattack bonus logic.
    ability_data = data["conquest_ability_data"]
    turn_number = data.get("turn_number", 1)
    treaties = data["treaties"]
    nap_prefix = "_nap_timer_"
    for key in list(ability_data.keys()):
        if not key.startswith(nap_prefix):
            continue
        value = ability_data[key]
        if not (isinstance(value, int) and value > 0):
            continue
        faction = key[len(nap_prefix):]
        if not any(t.get("type") == "nap" and t.get("faction") == faction
                   for t in treaties):
            treaties.append({
                "type": "nap",
                "faction": faction,
                "turns_remaining": value,
                "signed_on_turn": max(1, turn_number - 1),
                "penalty_if_broken": 30,
            })
        del ability_data[key]

    return data


def _migrate(data: dict) -> dict:
    """Run all migrations needed to bring *data* up to SCHEMA_VERSION.

    Returns a new dict. The input is not mutated, so callers can safely
    pass dicts they want to reuse.
    """
    version = data.get("schema_version", 10)
    if version < 11:
        data = _migrate_10_to_11(data)
    else:
        data = dict(data)
    data["schema_version"] = SCHEMA_VERSION
    return data


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
    diplomatic_favor: dict = field(default_factory=dict)                  # faction → int (-100 to +100)

    # --- 11.0 fields ---
    act: int = 1                                                           # G4: 1=Expansion, 2=Tension, 3=Endgame
    consecutive_high_income_turns: int = 0                                 # G5: for Economic Victory
    ai_doctrines: dict = field(default_factory=dict)                       # G2a: faction → list[policy_id]
    treaties: list = field(default_factory=list)                           # G8: list of Treaty dicts
    broken_treaty_counts: dict = field(default_factory=dict)               # G8: faction → int (vengeful memory)
    coalition: dict = field(default_factory=lambda: {
        "active": False, "members": [], "turns_remaining": 0, "trust": {}
    })                                                                      # G3: coalition-against-player state
    quest_chain_progress: dict = field(default_factory=dict)               # G6: planet_id → {chain_id, step}
    minor_world_rival: dict = field(default_factory=dict)                  # G6: planet_id → {faction, influence}
    relic_active_charges: dict = field(default_factory=dict)               # G7: relic_id → remaining charges
    espionage_blocks: dict = field(default_factory=dict)                   # G2b: {doctrine_blocked_turns: int}

    def to_dict(self) -> dict:
        """Serialize campaign state to a JSON-friendly dictionary."""
        return {
            "schema_version": SCHEMA_VERSION,
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
            "diplomatic_favor": dict(self.diplomatic_favor),
            # --- 11.0 ---
            "act": self.act,
            "consecutive_high_income_turns": self.consecutive_high_income_turns,
            "ai_doctrines": {k: list(v) for k, v in self.ai_doctrines.items()},
            "treaties": list(self.treaties),
            "broken_treaty_counts": dict(self.broken_treaty_counts),
            "coalition": dict(self.coalition),
            "quest_chain_progress": dict(self.quest_chain_progress),
            "minor_world_rival": dict(self.minor_world_rival),
            "relic_active_charges": dict(self.relic_active_charges),
            "espionage_blocks": dict(self.espionage_blocks),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CampaignState":
        """Deserialize campaign state from a dictionary.

        Runs `_migrate` first so pre-11.0 saves are brought forward with
        all new fields seeded and legacy keys converted.
        """
        data = _migrate(data)
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
            diplomatic_favor=data.get("diplomatic_favor", {}),
            # --- 11.0 (migration already seeded these) ---
            act=data["act"],
            consecutive_high_income_turns=data["consecutive_high_income_turns"],
            ai_doctrines=data["ai_doctrines"],
            treaties=data["treaties"],
            broken_treaty_counts=data["broken_treaty_counts"],
            coalition=data["coalition"],
            quest_chain_progress=data["quest_chain_progress"],
            minor_world_rival=data["minor_world_rival"],
            relic_active_charges=data["relic_active_charges"],
            espionage_blocks=data["espionage_blocks"],
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
