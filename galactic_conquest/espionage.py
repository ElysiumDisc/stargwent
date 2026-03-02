"""
STARGWENT - GALACTIC CONQUEST - Espionage / Tok'ra Operatives

Covert operations layer with state-machine lifecycle, risk/reward missions,
and integration with Minor Worlds (coups) and Diplomacy (incidents).
"""

from dataclasses import dataclass, field

# Tok'ra operative names (canon)
TOK_RA_NAMES = [
    "Anise", "Malek", "Delek", "Garshaw", "Aldwin",
    "Kelmaa", "Martouf", "Thoran", "Per'sus", "Ren'al",
]

# Operative states
IDLE = "idle"
MOVING = "moving"         # 1 turn transit
ESTABLISHING = "establishing"  # 2 turns to establish cover
ACTIVE = "active"
DEAD = "dead"             # 3 turn revival

# Rank info
RANK_NAMES = {1: "Recruit", 2: "Agent", 3: "Special Agent"}
RANK_EFFECTIVENESS = {1: 0.50, 2: 0.65, 3: 0.80}
RANK_DEATH_REDUCTION = 0.05  # per rank level
RANK_UP_COST = 40

# Mission definitions
MISSIONS = {
    "infiltrate": {
        "name": "Infiltrate",
        "target": "enemy",    # enemy planet
        "turns": 1,
        "death_risk": 0.10,
        "desc": "Reveal defender deck details in pre-battle",
    },
    "sabotage": {
        "name": "Sabotage",
        "target": "enemy",
        "turns": 2,
        "death_risk": 0.20,
        "desc": "Remove 1 card from AI deck (next battle)",
    },
    "steal_intel": {
        "name": "Steal Intel",
        "target": "enemy",
        "turns": 2,
        "death_risk": 0.15,
        "desc": "Gain 30-50 naquadah",
    },
    "rig_influence": {
        "name": "Rig Influence",
        "target": "minor",    # minor world
        "turns": 2,
        "death_risk": 0.10,
        "desc": "+15 influence at target minor world",
    },
    "coup": {
        "name": "Coup",
        "target": "minor",
        "turns": 1,
        "death_risk": 0.40,
        "desc": "Flip minor world ally status to player",
    },
    "counter_intel": {
        "name": "Counter-Intel",
        "target": "own",      # own planet
        "turns": 0,           # persistent
        "death_risk": 0.0,
        "desc": "Block next enemy espionage on this planet",
    },
}

# Diplomatic incident chance (per turn, per operative on enemy faction planet)
INCIDENT_CHANCE = 0.10
REVIVAL_TURNS = 3


@dataclass
class Operative:
    """A Tok'ra operative."""
    id: int
    name: str
    rank: int = 1
    state: str = "idle"
    target_planet: str = None
    turns_remaining: int = 0
    mission: str = None
    death_countdown: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rank": self.rank,
            "state": self.state,
            "target_planet": self.target_planet,
            "turns_remaining": self.turns_remaining,
            "mission": self.mission,
            "death_countdown": self.death_countdown,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            name=data["name"],
            rank=data.get("rank", 1),
            state=data.get("state", "idle"),
            target_planet=data.get("target_planet"),
            turns_remaining=data.get("turns_remaining", 0),
            mission=data.get("mission"),
            death_countdown=data.get("death_countdown", 0),
        )


def _get_doctrine_effects(state):
    """Get espionage-relevant doctrine effects."""
    from .doctrines import get_active_effects
    return get_active_effects(state)


def _save_operatives(state, operatives):
    """Save operative list back to state."""
    state.operatives = [op.to_dict() for op in operatives]


def _load_operatives(state):
    """Load operative list from state."""
    return [Operative.from_dict(d) for d in state.operatives]


# --- Earning Operatives ---

def check_earn_operative(state, rng):
    """Check if a free operative should be earned this turn.

    Free operatives at turns 5, 10, 16 (+ Shadow Government policy).
    Returns message or None.
    """
    earned = []
    turn = state.turn_number

    # Standard free operatives
    if turn in state.operative_earn_turns:
        state.operative_earn_turns.remove(turn)
        op = _create_operative(state, rng)
        earned.append(op)

    # Shadow Government doctrine: free every 8 turns
    effects = _get_doctrine_effects(state)
    interval = effects.get("free_operative_interval", 0)
    if interval > 0 and turn > 0 and turn % interval == 0:
        op = _create_operative(state, rng)
        earned.append(op)

    if earned:
        names = ", ".join(op.name for op in earned)
        return f"New operative(s): {names}"
    return None


def _create_operative(state, rng):
    """Create a new operative with a unique name."""
    ops = _load_operatives(state)
    used_names = {op.name for op in ops}
    available = [n for n in TOK_RA_NAMES if n not in used_names]
    name = rng.choice(available) if available else f"Tok'ra-{state.operative_next_id}"
    op = Operative(id=state.operative_next_id, name=name)
    state.operative_next_id += 1
    ops.append(op)
    _save_operatives(state, ops)
    return op


# --- Deployment & Missions ---

def deploy_operative(state, op_id, planet_id):
    """Deploy an idle operative to a planet. Returns message or None."""
    ops = _load_operatives(state)
    op = next((o for o in ops if o.id == op_id), None)
    if not op or op.state != IDLE:
        return None
    op.state = MOVING
    op.target_planet = planet_id
    op.turns_remaining = 1
    _save_operatives(state, ops)
    return f"{op.name} deploying to target..."


def assign_mission(state, op_id, mission_type):
    """Assign a mission to an active operative. Returns message or None."""
    if mission_type not in MISSIONS:
        return None
    ops = _load_operatives(state)
    op = next((o for o in ops if o.id == op_id), None)
    if not op or op.state != ACTIVE:
        return None
    mission = MISSIONS[mission_type]
    effects = _get_doctrine_effects(state)
    turns = mission["turns"]
    # Intelligence Networks: -1 turn (min 1)
    time_reduce = effects.get("mission_time_reduction", 0)
    if turns > 0:
        turns = max(1, turns - time_reduce)
    op.mission = mission_type
    op.turns_remaining = turns
    _save_operatives(state, ops)
    return f"{op.name} assigned: {mission['name']} ({turns} turn(s))"


def recall_operative(state, op_id):
    """Recall an operative back to idle. Returns message."""
    ops = _load_operatives(state)
    op = next((o for o in ops if o.id == op_id), None)
    if not op or op.state in (IDLE, DEAD):
        return None
    op.state = IDLE
    op.target_planet = None
    op.mission = None
    op.turns_remaining = 0
    _save_operatives(state, ops)
    return f"{op.name} recalled."


def rank_up_operative(state, op_id):
    """Upgrade an operative's rank. Returns message or None."""
    ops = _load_operatives(state)
    op = next((o for o in ops if o.id == op_id), None)
    if not op or op.state != IDLE or op.rank >= 3:
        return None
    if state.naquadah < RANK_UP_COST:
        return None
    state.add_naquadah(-RANK_UP_COST)
    op.rank += 1
    _save_operatives(state, ops)
    return f"{op.name} promoted to {RANK_NAMES[op.rank]}! (-{RANK_UP_COST} naq)"


# --- Turn Advance ---

def tick_operatives(state, galaxy, rng):
    """Advance all operatives by one turn. Returns list of message strings."""
    ops = _load_operatives(state)
    effects = _get_doctrine_effects(state)
    messages = []

    for op in ops:
        if op.state == DEAD:
            op.death_countdown -= 1
            if op.death_countdown <= 0:
                op.state = IDLE
                op.rank = 1  # Reset rank on death
                messages.append(f"{op.name} revived (Rank 1).")
            continue

        if op.state == MOVING:
            op.turns_remaining -= 1
            if op.turns_remaining <= 0:
                op.state = ESTABLISHING
                op.turns_remaining = 2
            continue

        if op.state == ESTABLISHING:
            op.turns_remaining -= 1
            if op.turns_remaining <= 0:
                op.state = ACTIVE
                messages.append(f"{op.name} established at target.")
            continue

        if op.state == ACTIVE and op.mission:
            if op.turns_remaining > 0:
                op.turns_remaining -= 1
            if op.turns_remaining <= 0:
                # Mission complete — resolve
                result = _resolve_mission(state, op, galaxy, rng, effects)
                messages.append(result)

        # Diplomatic incident check for operatives on enemy faction planets
        if op.state == ACTIVE and op.target_planet:
            incident = _check_diplomatic_incident(state, op, galaxy, rng, effects)
            if incident:
                messages.append(incident)

    _save_operatives(state, ops)
    return messages


def _resolve_mission(state, op, galaxy, rng, effects):
    """Resolve a completed mission. Returns message string."""
    mission_type = op.mission
    mission = MISSIONS.get(mission_type)
    if not mission:
        op.mission = None
        return f"{op.name}: mission invalid."

    # Death risk
    death_risk = mission["death_risk"]
    death_risk -= op.rank * RANK_DEATH_REDUCTION
    death_risk -= effects.get("operative_death_risk_reduction", 0)
    death_risk = max(0.0, death_risk)

    if rng.random() < death_risk:
        op.state = DEAD
        op.death_countdown = REVIVAL_TURNS
        op.mission = None
        op.target_planet = None
        return f"{op.name} KIA during {mission['name']}! Revival in {REVIVAL_TURNS} turns."

    # Success — apply effect
    msg = f"{op.name} completed {mission['name']}!"

    if mission_type == "infiltrate":
        # Store intel for pre-battle display
        state.conquest_ability_data[f"intel_{op.target_planet}"] = True
        msg += " Enemy deck revealed."

    elif mission_type == "sabotage":
        extra = effects.get("sabotage_extra_cards", 0)
        cards_to_remove = 1 + extra
        state.conquest_ability_data[f"sabotage_{op.target_planet}"] = cards_to_remove
        msg += f" {cards_to_remove} card(s) will be removed from AI deck."

    elif mission_type == "steal_intel":
        naq = rng.randint(30, 50)
        state.add_naquadah(naq)
        msg += f" +{naq} naquadah."

    elif mission_type == "rig_influence":
        from .minor_worlds import ensure_minor_world, INFLUENCE_MAX
        mw = ensure_minor_world(state, op.target_planet, galaxy)
        if mw:
            mw.influence = min(INFLUENCE_MAX, mw.influence + 15)
            state.minor_world_states[mw.planet_id] = mw.to_dict()
            msg += " +15 influence."

    elif mission_type == "coup":
        from .minor_worlds import ensure_minor_world
        mw = ensure_minor_world(state, op.target_planet, galaxy)
        if mw:
            # Success chance = 50% + rank*15% - influence_gap/4
            influence_gap = max(0, 60 - mw.influence)
            success = 0.50 + op.rank * 0.15 - influence_gap / 400.0
            # Shadow Mastery doubles success
            if effects.get("shadow_mastery"):
                success *= 2.0
            success = min(0.95, max(0.10, success))
            if rng.random() < success:
                mw.ally_faction = "player"
                state.minor_world_states[mw.planet_id] = mw.to_dict()
                msg += " Coup successful! Allied with player."
            else:
                msg += " Coup failed."

    elif mission_type == "counter_intel":
        state.conquest_ability_data[f"counter_intel_{op.target_planet}"] = True
        msg += " Counter-intelligence active."
        # Don't reset mission — persistent
        return msg

    op.mission = None
    return msg


def _check_diplomatic_incident(state, op, galaxy, rng, effects):
    """Check if an operative causes a diplomatic incident."""
    if effects.get("shadow_mastery"):
        return None  # No incidents with Shadow Mastery

    planet = galaxy.planets.get(op.target_planet)
    if not planet or planet.owner in ("player", "neutral"):
        return None

    enemy_faction = planet.owner
    if rng.random() >= INCIDENT_CHANCE:
        return None

    # Check if we have a relation to damage
    from .diplomacy import get_relation, set_relation, TRADING, ALLIED
    rel = get_relation(state, enemy_faction)
    if rel == ALLIED and rng.random() < 0.20:
        set_relation(state, enemy_faction, TRADING)
        return f"Operative {op.name} detected! {enemy_faction} alliance downgraded to Trading!"
    elif rel == TRADING and rng.random() < 0.30:
        from .diplomacy import HOSTILE
        set_relation(state, enemy_faction, HOSTILE)
        return f"Operative {op.name} detected! {enemy_faction} now Hostile!"
    return None


# --- Query Functions (for battle integration) ---

def get_planet_intel(state, planet_id):
    """Check if player has intel on a planet (from Infiltrate mission)."""
    return state.conquest_ability_data.get(f"intel_{planet_id}", False)


def get_sabotage_effect(state, planet_id):
    """Get number of cards to remove from AI deck (from Sabotage mission)."""
    key = f"sabotage_{planet_id}"
    count = state.conquest_ability_data.get(key, 0)
    if count > 0:
        # Consume the sabotage
        del state.conquest_ability_data[key]
    return count


def get_operative_summary(state):
    """Get summary of all operatives for display."""
    ops = _load_operatives(state)
    return [(op.name, RANK_NAMES.get(op.rank, "?"), op.state,
             op.target_planet, op.mission, op.turns_remaining,
             op.death_countdown, op.id) for op in ops]
