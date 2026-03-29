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
    # --- Deep Cover Missions (v10.1) ---
    "forge_alliance": {
        "name": "Forge Alliance",
        "target": "enemy",
        "turns": 3,
        "death_risk": 0.15,
        "desc": "Shift faction relation one level toward friendly",
    },
    "relic_hunt": {
        "name": "Relic Hunt",
        "target": "neutral",  # neutral planet
        "turns": 3,
        "death_risk": 0.25,
        "desc": "Chance to discover a relic from ancient ruins",
    },
    "doctrine_theft": {
        "name": "Doctrine Theft",
        "target": "enemy",
        "turns": 2,
        "death_risk": 0.30,
        "desc": "Steal knowledge: gain 15 Wisdom",
    },
    "sleeper_agent": {
        "name": "Sleeper Agent",
        "target": "enemy",
        "turns": 0,           # persistent
        "death_risk": 0.05,
        "desc": "Enemy counterattacks from this planet start -1 card",
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

        # NOTE: Diplomatic incidents are now generated separately via
        # generate_incident_choices() and resolved interactively in the
        # campaign controller.  The old auto-resolve is kept as a fallback
        # only when called directly (not the normal path).

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

    elif mission_type == "forge_alliance":
        from .diplomacy import get_relation, set_relation, HOSTILE, NEUTRAL_REL, TRADING, ALLIED
        faction = galaxy.planets[op.target_planet].owner if op.target_planet else None
        if faction and faction not in ("player", "neutral"):
            rel = get_relation(state, faction)
            if rel == HOSTILE:
                set_relation(state, faction, NEUTRAL_REL)
                msg += f" {faction} relations improved to Neutral!"
            elif rel == NEUTRAL:
                set_relation(state, faction, TRADING)
                msg += f" {faction} relations improved to Trading!"
            elif rel == TRADING:
                set_relation(state, faction, ALLIED)
                msg += f" {faction} relations improved to Allied!"
            else:
                msg += " Relations already at maximum."
        else:
            msg += " No valid faction to influence."

    elif mission_type == "relic_hunt":
        from .relics import RELICS
        # 50% chance to find a relic the player doesn't own
        owned = set(state.relics)
        available = [rid for rid in RELICS if rid not in owned]
        if available and rng.random() < 0.50:
            found_id = rng.choice(available)
            state.add_relic(found_id)
            found_name = RELICS[found_id].name
            msg += f" Discovered {found_name}!"
        elif available:
            naq = rng.randint(15, 30)
            state.add_naquadah(naq)
            msg += f" No relic found, but recovered +{naq} naquadah."
        else:
            msg += " All relics already discovered."

    elif mission_type == "doctrine_theft":
        state.wisdom += 15
        msg += " +15 Wisdom stolen from enemy archives."

    elif mission_type == "sleeper_agent":
        state.conquest_ability_data[f"sleeper_{op.target_planet}"] = True
        msg += " Sleeper agent embedded. Enemy attacks from here start -1 card."
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


# ─── AI Espionage Against Player ────────────────────────────────

AI_ESPIONAGE_MISSIONS = {
    "steal_naq": {"name": "Resource Theft", "desc": "Steal 20-40 naquadah", "chance": 0.70},
    "sabotage": {"name": "Sabotage", "desc": "Remove 1 card from your next battle", "chance": 0.60},
    "rig_minor": {"name": "Rig Influence", "desc": "Reduce your minor world influence", "chance": 0.70},
}


def generate_ai_espionage_events(state, galaxy, rng):
    """Generate AI espionage events targeting player planets.

    Hostile factions with 4+ planets have 15% chance/turn.
    Returns list of event dicts.
    """
    events = []
    for faction in galaxy.get_active_factions():
        if faction == state.player_faction:
            continue
        from .diplomacy import get_relation, HOSTILE
        if get_relation(state, faction) != HOSTILE:
            continue
        if galaxy.get_faction_planet_count(faction) < 4:
            continue
        if rng.random() >= 0.15:
            continue
        # Pick a random player planet as target
        player_planets = [pid for pid, p in galaxy.planets.items() if p.owner == "player"]
        if not player_planets:
            continue
        target_pid = rng.choice(player_planets)
        target_planet = galaxy.planets[target_pid]
        mission_type = rng.choice(list(AI_ESPIONAGE_MISSIONS.keys()))
        mission = AI_ESPIONAGE_MISSIONS[mission_type]

        # Check if player has counter-intel operative here
        has_counter = any(
            op.get("target_planet") == target_pid
            and op.get("current_mission") == "counter_intel"
            and op.get("state") == "active"
            for op in state.operatives
        )

        events.append({
            "faction": faction,
            "planet_id": target_pid,
            "planet_name": target_planet.name,
            "mission_type": mission_type,
            "mission_name": mission["name"],
            "mission_desc": mission["desc"],
            "success_chance": mission["chance"],
            "has_counter_intel": has_counter,
        })
    return events


def resolve_ai_espionage(state, galaxy, event, choice, rng):
    """Resolve an AI espionage event based on player choice.

    choice: "ignore", "capture", or "counter"
    Returns result message string.
    """
    faction = event["faction"]
    planet_name = event["planet_name"]
    mission_type = event["mission_type"]

    if choice == "counter":
        return f"Counter-intel operative blocked {faction}'s {event['mission_name']} on {planet_name}!"

    if choice == "capture":
        state.add_naquadah(-20)
        if rng.random() < 0.60:
            return f"Captured {faction} operative on {planet_name}! (-20 naq)"
        else:
            # Capture failed, mission proceeds
            pass  # Fall through to mission resolution

    # Ignore or failed capture — mission may succeed
    if rng.random() < event["success_chance"]:
        # Mission succeeds
        if mission_type == "steal_naq":
            stolen = rng.randint(20, 40)
            state.add_naquadah(-stolen)
            return f"{faction} stole {stolen} naquadah from {planet_name}!"
        elif mission_type == "sabotage":
            state.conquest_ability_data["ai_sabotage_active"] = True
            return f"{faction} sabotaged {planet_name}! -1 card in your next battle."
        elif mission_type == "rig_minor":
            # Reduce influence on a random minor world
            from .minor_worlds import MinorWorldState
            for pid, mw_data in list(state.minor_world_states.items()):
                mw = MinorWorldState.from_dict(mw_data)
                if mw.influence > 10:
                    mw.influence = max(0, mw.influence - 15)
                    state.minor_world_states[pid] = mw.to_dict()
                    return f"{faction} rigged influence on a minor world! -15 influence."
            return f"{faction}'s influence operation found no viable targets."
    else:
        if choice == "ignore":
            return f"{faction}'s espionage on {planet_name} failed."
        return f"Failed to capture {faction} operative, but their mission also failed. (-20 naq)"


# ─── Diplomatic Incident Choices ────────────────────────────────

def generate_incident_choices(state, galaxy, rng):
    """Check for diplomatic incidents and generate choice events.

    Returns list of incident choice dicts instead of auto-resolving.
    """
    incidents = []
    for op in state.operatives:
        if op.get("state") != "active":
            continue
        target_pid = op.get("target_planet")
        if not target_pid:
            continue
        target = galaxy.planets.get(target_pid)
        if not target or target.owner in ("player", "neutral"):
            continue
        # 10% chance of detection
        if rng.random() >= 0.10:
            continue
        # Shadow Mastery eliminates incidents
        from .doctrines import get_active_effects
        effects = get_active_effects(state)
        if effects.get("shadow_mastery"):
            continue
        incidents.append({
            "operative_id": op.get("id"),
            "operative_name": op.get("name", "Operative"),
            "planet_name": target.name,
            "faction": target.owner,
        })
    return incidents


def resolve_incident_choice(state, incident, choice, rng):
    """Resolve a diplomatic incident choice.

    choice: "deny", "recall", or "double_down"
    Returns result message string.
    """
    faction = incident["faction"]
    op_name = incident["operative_name"]
    planet_name = incident["planet_name"]

    if choice == "deny":
        if rng.random() < 0.50:
            return f"Denied involvement — {faction} bought it. {op_name} is safe on {planet_name}."
        else:
            from .diplomacy import get_relation, set_relation, TRADING, HOSTILE, ALLIED
            rel = get_relation(state, faction)
            if rel == ALLIED:
                set_relation(state, faction, TRADING)
                return f"Cover blown! {faction} caught {op_name}. Alliance downgraded to Trading."
            elif rel == TRADING:
                set_relation(state, faction, HOSTILE)
                return f"Cover blown! {faction} caught {op_name}. Now Hostile!"
            return f"Cover blown! {faction} caught {op_name} on {planet_name}."

    elif choice == "recall":
        # Find and recall the operative
        for op in state.operatives:
            if op.get("id") == incident["operative_id"]:
                op["state"] = "idle"
                op["target_planet"] = None
                op["current_mission"] = None
                break
        return f"Recalled {op_name} from {planet_name}. No diplomatic damage."

    elif choice == "double_down":
        # Guaranteed incident but operative gets mission bonus
        from .diplomacy import get_relation, set_relation, TRADING, HOSTILE, ALLIED
        rel = get_relation(state, faction)
        if rel == ALLIED:
            set_relation(state, faction, TRADING)
        elif rel == TRADING:
            set_relation(state, faction, HOSTILE)
        # Give operative bonus
        for op in state.operatives:
            if op.get("id") == incident["operative_id"]:
                op["mission_bonus"] = op.get("mission_bonus", 0) + 20
                break
        return f"Doubled down! {op_name} gets +20% next mission, but {faction} relations damaged."

    return ""
