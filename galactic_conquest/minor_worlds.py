"""
STARGWENT - GALACTIC CONQUEST - Minor Worlds System

Transforms neutral planets into persistent diplomatic actors with influence,
quests, ally exclusivity, and type bonuses. Inspired by Civ V city-states.
"""

from dataclasses import dataclass, field


# Minor world type assignments for each neutral planet
MINOR_WORLD_TYPES = {
    "Abydos": "economic",
    "Vis Uban": "spiritual",
    "Atlantis": "scientific",
    "Heliopolis": "scientific",
    "Cimmeria": "militant",
    "Kheb": "spiritual",
    "Proclarush": "militant",
    "Vagonbrei": "diplomatic",
    "P3X-888": "economic",
}

# Type display info: color + bonuses at each tier
MINOR_WORLD_TYPE_INFO = {
    "scientific": {
        "color": (100, 200, 255),
        "icon": "\u2699",  # gear
        "friend_desc": "+1 reward card choice",
        "ally_desc": "+1 card upgrade per turn",
    },
    "militant": {
        "color": (255, 100, 80),
        "icon": "\u2694",  # swords
        "friend_desc": "+1 defense power",
        "ally_desc": "+1 attack power",
    },
    "diplomatic": {
        "color": (200, 180, 255),
        "icon": "\u2696",  # scales
        "friend_desc": "-15 naq trade cost",
        "ally_desc": "-8% counterattack chance",
    },
    "economic": {
        "color": (255, 220, 80),
        "icon": "\u26A1",  # lightning
        "friend_desc": "+8 naq/turn",
        "ally_desc": "+15 naq/turn",
    },
    "spiritual": {
        "color": (200, 150, 255),
        "icon": "\u2261",  # triple bar
        "friend_desc": "+3 Wisdom/turn",
        "ally_desc": "+6 Wisdom/turn",
    },
}

# Influence tier thresholds
NEUTRAL_THRESHOLD = 0
FRIEND_THRESHOLD = 30
ALLY_THRESHOLD = 60
INFLUENCE_MAX = 100
INFLUENCE_RESTING = 25
INFLUENCE_DECAY = 3

# Action costs
TRIBUTE_COST_MIN = 30
TRIBUTE_COST_MAX = 50
TRIBUTE_INFLUENCE = 15
BULLY_GAIN = 20
BULLY_PENALTY = 10

# Quest types
QUEST_TYPES = {
    "tribute": {
        "desc_template": "Pay {amount} naquadah",
        "reward_influence": 15,
    },
    "defend": {
        "desc_template": "Win your next defense battle",
        "reward_influence": 20,
    },
    "conquer": {
        "desc_template": "Conquer any enemy planet this turn",
        "reward_influence": 15,
    },
    "trade": {
        "desc_template": "Establish trade with any faction",
        "reward_influence": 10,
    },
    "build": {
        "desc_template": "Build on any owned planet",
        "reward_influence": 10,
    },
}

QUEST_COOLDOWN_TURNS = 2


@dataclass
class MinorWorldState:
    """Persistent state for a single minor world."""
    planet_id: str
    world_type: str
    influence: int = 0
    ally_faction: str = None  # "player" or faction name; exclusive
    active_quest: dict = None  # {quest_type, description, amount (optional), reward_influence}
    quest_cooldown: int = 0
    ai_influence: dict = field(default_factory=dict)  # faction_name -> influence

    def to_dict(self):
        return {
            "planet_id": self.planet_id,
            "world_type": self.world_type,
            "influence": self.influence,
            "ally_faction": self.ally_faction,
            "active_quest": self.active_quest,
            "quest_cooldown": self.quest_cooldown,
            "ai_influence": dict(self.ai_influence),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            planet_id=data["planet_id"],
            world_type=data["world_type"],
            influence=data.get("influence", 0),
            ally_faction=data.get("ally_faction"),
            active_quest=data.get("active_quest"),
            quest_cooldown=data.get("quest_cooldown", 0),
            ai_influence=data.get("ai_influence", {}),
        )


def get_influence_tier(influence):
    """Return tier string for an influence value."""
    if influence >= ALLY_THRESHOLD:
        return "ally"
    elif influence >= FRIEND_THRESHOLD:
        return "friend"
    return "neutral"


def get_tier_label(influence):
    """Human-readable tier label."""
    tier = get_influence_tier(influence)
    return {"neutral": "Neutral", "friend": "Friend", "ally": "Ally"}[tier]


# --- Initialization ---

def init_minor_worlds(state, galaxy):
    """Initialize minor world states for all neutral planets owned by player.

    Called when a neutral planet is first claimed (or on campaign load if missing).
    """
    for pid, planet in galaxy.planets.items():
        if planet.planet_type != "neutral":
            continue
        if pid in state.minor_world_states:
            continue
        world_type = MINOR_WORLD_TYPES.get(planet.name, "economic")
        mw = MinorWorldState(planet_id=pid, world_type=world_type)
        state.minor_world_states[pid] = mw.to_dict()


def ensure_minor_world(state, planet_id, galaxy):
    """Ensure a minor world state exists for a planet. Returns MinorWorldState or None."""
    if planet_id in state.minor_world_states:
        return MinorWorldState.from_dict(state.minor_world_states[planet_id])
    planet = galaxy.planets.get(planet_id)
    if not planet or planet.planet_type != "neutral":
        return None
    world_type = MINOR_WORLD_TYPES.get(planet.name, "economic")
    mw = MinorWorldState(planet_id=planet_id, world_type=world_type)
    state.minor_world_states[planet_id] = mw.to_dict()
    return mw


def _save_mw(state, mw):
    """Save a MinorWorldState back to campaign state."""
    state.minor_world_states[mw.planet_id] = mw.to_dict()


# --- Player Actions ---

def get_tribute_cost(state):
    """Get current tribute cost (scales slightly with turn)."""
    base = TRIBUTE_COST_MIN + min(20, state.turn_number)
    return min(TRIBUTE_COST_MAX, base)


def pay_tribute(state, planet_id, galaxy):
    """Pay naquadah tribute for influence. Returns message or None."""
    mw = ensure_minor_world(state, planet_id, galaxy)
    if not mw:
        return None
    cost = get_tribute_cost(state)
    if state.naquadah < cost:
        return None
    state.add_naquadah(-cost)
    mw.influence = min(INFLUENCE_MAX, mw.influence + TRIBUTE_INFLUENCE)
    _save_mw(state, mw)
    planet = galaxy.planets.get(planet_id)
    name = planet.name if planet else planet_id
    return f"Paid {cost} naq tribute to {name}. Influence: {mw.influence}"


def bully_world(state, planet_id, galaxy):
    """Bully a minor world: +20 here, -10 from all others. Returns message."""
    mw = ensure_minor_world(state, planet_id, galaxy)
    if not mw:
        return None
    mw.influence = min(INFLUENCE_MAX, mw.influence + BULLY_GAIN)
    _save_mw(state, mw)
    # Penalty to all other minor worlds
    for other_pid, other_data in state.minor_world_states.items():
        if other_pid == planet_id:
            continue
        other_mw = MinorWorldState.from_dict(other_data)
        other_mw.influence = max(0, other_mw.influence - BULLY_PENALTY)
        _save_mw(state, other_mw)
    planet = galaxy.planets.get(planet_id)
    name = planet.name if planet else planet_id
    return f"Bullied {name}! +{BULLY_GAIN} influence, -{BULLY_PENALTY} from others."


def attempt_ally(state, planet_id, galaxy):
    """Attempt to become ally of a minor world. Returns message or None."""
    mw = ensure_minor_world(state, planet_id, galaxy)
    if not mw:
        return None
    if mw.influence < ALLY_THRESHOLD:
        return None
    if mw.ally_faction is not None:
        return f"Already allied with {mw.ally_faction}!"
    mw.ally_faction = "player"
    _save_mw(state, mw)
    planet = galaxy.planets.get(planet_id)
    name = planet.name if planet else planet_id
    type_info = MINOR_WORLD_TYPE_INFO.get(mw.world_type, {})
    return f"Allied with {name}! Bonus: {type_info.get('ally_desc', '?')}"


def request_quest(state, planet_id, galaxy, rng):
    """Generate a new quest for a minor world. Returns message or None."""
    mw = ensure_minor_world(state, planet_id, galaxy)
    if not mw:
        return None
    if mw.active_quest:
        return "Already has an active quest!"
    if mw.quest_cooldown > 0:
        return f"Quest available in {mw.quest_cooldown} turn(s)."

    # Pick a random quest type
    quest_type = rng.choice(list(QUEST_TYPES.keys()))
    quest_info = QUEST_TYPES[quest_type]
    amount = None
    if quest_type == "tribute":
        amount = rng.randint(30, 60)
        desc = quest_info["desc_template"].format(amount=amount)
    else:
        desc = quest_info["desc_template"]

    mw.active_quest = {
        "quest_type": quest_type,
        "description": desc,
        "amount": amount,
        "reward_influence": quest_info["reward_influence"],
        "completed": False,
    }
    _save_mw(state, mw)
    planet = galaxy.planets.get(planet_id)
    name = planet.name if planet else planet_id
    return f"{name} quest: {desc} (+{quest_info['reward_influence']} influence)"


def complete_quest_tribute(state, planet_id, galaxy):
    """Complete a tribute quest by paying naquadah. Returns message or None."""
    mw = ensure_minor_world(state, planet_id, galaxy)
    if not mw or not mw.active_quest:
        return None
    if mw.active_quest["quest_type"] != "tribute":
        return None
    amount = mw.active_quest.get("amount", 40)
    if state.naquadah < amount:
        return None
    state.add_naquadah(-amount)
    reward = mw.active_quest["reward_influence"]
    mw.influence = min(INFLUENCE_MAX, mw.influence + reward)
    mw.active_quest = None
    mw.quest_cooldown = QUEST_COOLDOWN_TURNS
    _save_mw(state, mw)
    return f"Quest complete! +{reward} influence"


# --- Quest Progress Hooks ---

def notify_quest_event(state, event_type):
    """Check all minor worlds for quest completion on an event.

    event_type: "defend" | "conquer" | "trade" | "build"
    Returns list of (planet_id, message) for completed quests.
    """
    completed = []
    for pid, data in list(state.minor_world_states.items()):
        mw = MinorWorldState.from_dict(data)
        if not mw.active_quest or mw.active_quest.get("completed"):
            continue
        if mw.active_quest["quest_type"] == event_type:
            reward = mw.active_quest["reward_influence"]
            mw.influence = min(INFLUENCE_MAX, mw.influence + reward)
            mw.active_quest = None
            mw.quest_cooldown = QUEST_COOLDOWN_TURNS
            _save_mw(state, mw)
            completed.append((pid, f"Quest complete! +{reward} influence"))
    return completed


# --- Turn Advance ---

def decay_minor_world_influence(state):
    """Decay all minor world influence toward resting point."""
    for pid, data in list(state.minor_world_states.items()):
        mw = MinorWorldState.from_dict(data)
        if mw.influence > INFLUENCE_RESTING:
            mw.influence = max(INFLUENCE_RESTING, mw.influence - INFLUENCE_DECAY)
        elif mw.influence < INFLUENCE_RESTING:
            mw.influence = min(INFLUENCE_RESTING, mw.influence + 1)
        # Decay AI influence too
        for faction in list(mw.ai_influence.keys()):
            ai_inf = mw.ai_influence[faction]
            if ai_inf > INFLUENCE_RESTING:
                mw.ai_influence[faction] = max(INFLUENCE_RESTING, ai_inf - INFLUENCE_DECAY)
            elif ai_inf < INFLUENCE_RESTING:
                mw.ai_influence[faction] = min(INFLUENCE_RESTING, ai_inf + 1)
        # Tick quest cooldown
        if mw.quest_cooldown > 0:
            mw.quest_cooldown -= 1
        _save_mw(state, mw)


def ai_court_minor_worlds(state, galaxy, rng):
    """AI factions gain influence on adjacent minor worlds.

    25% chance per turn per adjacent faction to gain 5-10 influence.
    30% chance to claim ally if influence >= 60 and no current ally.
    """
    for pid, data in list(state.minor_world_states.items()):
        mw = MinorWorldState.from_dict(data)
        planet = galaxy.planets.get(pid)
        if not planet:
            continue
        # Find adjacent AI factions
        adjacent_factions = set()
        for neighbor_id in planet.connections:
            neighbor = galaxy.planets.get(neighbor_id)
            if neighbor and neighbor.owner not in ("player", "neutral"):
                adjacent_factions.add(neighbor.owner)
        for faction in adjacent_factions:
            if rng.random() < 0.25:
                gain = rng.randint(5, 10)
                current = mw.ai_influence.get(faction, 0)
                mw.ai_influence[faction] = min(INFLUENCE_MAX, current + gain)
                # Try to claim ally
                if (mw.ai_influence[faction] >= ALLY_THRESHOLD
                        and mw.ally_faction is None
                        and rng.random() < 0.30):
                    mw.ally_faction = faction
        _save_mw(state, mw)


def apply_minor_world_income(state, galaxy):
    """Apply per-turn income from Economic friend/ally minor worlds.

    Returns total naquadah bonus.
    """
    total_naq = 0
    for pid, data in state.minor_world_states.items():
        mw = MinorWorldState.from_dict(data)
        planet = galaxy.planets.get(pid)
        if not planet or planet.owner != "player":
            continue
        if mw.world_type != "economic":
            continue
        tier = get_influence_tier(mw.influence)
        if mw.ally_faction == "player" and tier == "ally":
            total_naq += 15
        elif tier == "friend":
            total_naq += 8
    return total_naq


# --- Bonus Queries (for other systems) ---

def get_minor_world_bonuses(state, galaxy=None):
    """Aggregate all active minor world bonuses for the player.

    Args:
        state: CampaignState
        galaxy: GalaxyMap (optional — if None, skips ownership check)

    Returns dict of bonus values:
    - extra_card_choices: int (scientific friend/ally)
    - card_upgrades_per_turn: int (scientific ally)
    - defense_power_bonus: int (militant friend/ally)
    - attack_power_bonus: int (militant ally)
    - trade_cost_discount: int (diplomatic friend/ally)
    - counterattack_reduction: float (diplomatic ally)
    - naq_per_turn: int (economic, handled by apply_minor_world_income)
    - wisdom_per_turn: int (spiritual friend/ally)
    """
    bonuses = {
        "extra_card_choices": 0,
        "card_upgrades_per_turn": 0,
        "defense_power_bonus": 0,
        "attack_power_bonus": 0,
        "trade_cost_discount": 0,
        "counterattack_reduction": 0.0,
        "wisdom_per_turn": 0,
    }
    for pid, data in state.minor_world_states.items():
        mw = MinorWorldState.from_dict(data)
        if galaxy is not None:
            planet = galaxy.planets.get(pid)
            if not planet or planet.owner != "player":
                continue
        tier = get_influence_tier(mw.influence)
        is_ally = mw.ally_faction == "player" and tier == "ally"
        is_friend = tier == "friend"

        if mw.world_type == "scientific":
            if is_friend or is_ally:
                bonuses["extra_card_choices"] += 1
            if is_ally:
                bonuses["card_upgrades_per_turn"] += 1
        elif mw.world_type == "militant":
            if is_friend or is_ally:
                bonuses["defense_power_bonus"] += 1
            if is_ally:
                bonuses["attack_power_bonus"] += 1
        elif mw.world_type == "diplomatic":
            if is_friend or is_ally:
                bonuses["trade_cost_discount"] += 15
            if is_ally:
                bonuses["counterattack_reduction"] += 0.08
        elif mw.world_type == "spiritual":
            if is_friend and not is_ally:
                bonuses["wisdom_per_turn"] += 3
            if is_ally:
                bonuses["wisdom_per_turn"] += 6
    return bonuses


def get_player_ally_count(state):
    """Count minor worlds where player is the ally."""
    count = 0
    for data in state.minor_world_states.values():
        mw = MinorWorldState.from_dict(data)
        if mw.ally_faction == "player":
            count += 1
    return count
