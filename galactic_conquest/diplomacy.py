"""
STARGWENT - GALACTIC CONQUEST - Diplomacy System

Faction relations: HOSTILE → NEUTRAL → TRADING → ALLIED
Diplomatic favor, trade, alliance, betrayal, NAP, tribute, gifts, military aid.
"""

import random

# Relation levels (ordered by friendliness)
HOSTILE = "hostile"
NEUTRAL_REL = "neutral"
TRADING = "trading"
ALLIED = "allied"

RELATION_ORDER = [HOSTILE, NEUTRAL_REL, TRADING, ALLIED]

RELATION_DISPLAY = {
    HOSTILE: {"name": "Hostile", "color": (255, 80, 80)},
    NEUTRAL_REL: {"name": "Neutral", "color": (180, 180, 180)},
    TRADING: {"name": "Trading", "color": (100, 220, 255)},
    ALLIED: {"name": "Allied", "color": (80, 255, 140)},
}

# Costs
TRADE_COST = 50
ALLIANCE_COST = 100
BETRAY_REWARD = 80
GIFT_COST = 30
NAP_COST = 20
MILITARY_AID_COST = 40
JOINT_ATTACK_COST = 15

# Favor constants
FAVOR_MIN = -100
FAVOR_MAX = 100
FAVOR_DECAY_PER_TURN = 3
FAVOR_HIGH_THRESHOLD = 50
FAVOR_LOW_THRESHOLD = -50
NAP_DURATION = 5

# --- Faction diplomacy personality defaults (overridden by FACTION_PERSONALITIES) ---
_DEFAULT_DIPLO_PERSONALITY = {
    "gift_favor_mult": 1.0,
    "nap_acceptance": 0.50,
    "demand_refusal_rate": 0.50,
    "trade_propose_mult": 1.0,
    "unique_proposal": None,
}


def _get_diplo_personality(faction):
    """Get diplomacy personality data for a faction.

    Tries to look up from FACTION_PERSONALITIES in campaign_controller,
    falls back to defaults.
    """
    try:
        from .campaign_controller import FACTION_PERSONALITIES
        p = FACTION_PERSONALITIES.get(faction, {})
        return {
            "gift_favor_mult": p.get("gift_favor_mult", 1.0),
            "nap_acceptance": p.get("nap_acceptance", 0.50),
            "demand_refusal_rate": p.get("demand_refusal_rate", 0.50),
            "trade_propose_mult": p.get("trade_propose_mult", 1.0),
            "unique_proposal": p.get("unique_proposal"),
        }
    except ImportError:
        return dict(_DEFAULT_DIPLO_PERSONALITY)


# =========================================================================
# Favor System
# =========================================================================

def get_favor(state, faction):
    """Get current diplomatic favor with a faction (-100 to +100)."""
    return state.diplomatic_favor.get(faction, 0)


def adjust_favor(state, faction, amount):
    """Adjust favor with a faction, clamped to [-100, +100]."""
    current = state.diplomatic_favor.get(faction, 0)
    state.diplomatic_favor[faction] = max(FAVOR_MIN, min(FAVOR_MAX, current + amount))


def adjust_favor_all(state, amount, exclude=None):
    """Adjust favor for all factions the player has relations with."""
    for faction in list(state.faction_relations):
        if faction == exclude:
            continue
        adjust_favor(state, faction, amount)


def tick_favor_decay(state):
    """Decay all favor 3 points toward 0 each turn."""
    for faction in list(state.diplomatic_favor):
        current = state.diplomatic_favor[faction]
        if current > 0:
            state.diplomatic_favor[faction] = max(0, current - FAVOR_DECAY_PER_TURN)
        elif current < 0:
            state.diplomatic_favor[faction] = min(0, current + FAVOR_DECAY_PER_TURN)


def get_favor_cost_modifier(state, faction):
    """Get cost multiplier based on favor. High favor = cheaper diplomacy.

    Returns float multiplier (e.g. 0.75 for 25% discount at 50+ favor).
    """
    favor = get_favor(state, faction)
    if favor >= FAVOR_HIGH_THRESHOLD:
        return 0.75
    return 1.0


def get_favor_counter_bonus(state, faction):
    """Get extra counterattack chance from very negative favor."""
    favor = get_favor(state, faction)
    if favor <= FAVOR_LOW_THRESHOLD:
        return 0.10
    return 0.0


def tick_trading_favor(state):
    """Every 3 turns of TRADING, gain +5 favor with that faction."""
    for faction, rel in state.faction_relations.items():
        if rel == TRADING:
            key = f"_trading_turns_{faction}"
            turns = state.conquest_ability_data.get(key, 0) + 1
            state.conquest_ability_data[key] = turns
            if turns % 3 == 0:
                adjust_favor(state, faction, 5)
        else:
            # Reset counter if not trading
            key = f"_trading_turns_{faction}"
            if key in state.conquest_ability_data:
                del state.conquest_ability_data[key]


# =========================================================================
# Core Relations
# =========================================================================

def get_relation(state, faction):
    """Get current relation with a faction."""
    return state.faction_relations.get(faction, HOSTILE)


def set_relation(state, faction, relation):
    """Set relation with a faction."""
    state.faction_relations[faction] = relation


def init_relations(state, friendly_faction=None):
    """Initialize faction relations for a new campaign."""
    from .galaxy_map import ALL_FACTIONS
    for faction in ALL_FACTIONS:
        if faction == state.player_faction:
            continue
        if faction == friendly_faction:
            state.faction_relations[faction] = ALLIED
            state.diplomatic_favor[faction] = 30
        else:
            state.faction_relations[faction] = HOSTILE
            state.diplomatic_favor[faction] = 0


def _get_effective_trade_cost(state, faction=None):
    """Get trade cost after doctrine/minor world/favor discounts."""
    cost = TRADE_COST
    # Doctrine: Free Trade Zone (-20 naq)
    from .doctrines import get_active_effects
    effects = get_active_effects(state)
    cost -= effects.get("trade_cost_discount", 0)
    # Minor world: diplomatic friend/ally (-15 naq)
    from .minor_worlds import get_minor_world_bonuses
    mw_bonuses = get_minor_world_bonuses(state, None)
    cost -= mw_bonuses.get("trade_cost_discount", 0)
    # Favor discount
    if faction:
        cost = int(cost * get_favor_cost_modifier(state, faction))
    return max(10, cost)


def _get_effective_alliance_cost(state, faction=None):
    """Get alliance cost after favor discounts."""
    cost = ALLIANCE_COST
    if faction:
        cost = int(cost * get_favor_cost_modifier(state, faction))
    return max(20, cost)


# =========================================================================
# Original Player Actions (Trade, Alliance, Betray)
# =========================================================================

def can_trade(state, faction, galaxy):
    """Check if player can propose trade with a faction."""
    rel = get_relation(state, faction)
    if rel in (TRADING, ALLIED):
        return False
    # Low favor blocks trade proposals
    if get_favor(state, faction) <= FAVOR_LOW_THRESHOLD:
        return False
    cost = _get_effective_trade_cost(state, faction)
    if rel == HOSTILE:
        return _has_shared_border(state, faction, galaxy) and state.naquadah >= cost
    return state.naquadah >= cost


def can_ally(state, faction, galaxy):
    """Check if player can form alliance."""
    rel = get_relation(state, faction)
    if rel != TRADING:
        return False
    cost = _get_effective_alliance_cost(state, faction)
    return state.naquadah >= cost


def can_betray(state, faction):
    """Check if player can betray an ally."""
    return get_relation(state, faction) == ALLIED


def _track_conquest_stat(key, increment=1):
    """Increment a conquest stat counter."""
    from deck_persistence import get_persistence
    p = get_persistence()
    cs = p.unlock_data.setdefault("conquest_stats", {})
    cs[key] = cs.get(key, 0) + increment
    p.save_unlocks()


def propose_trade(state, faction, galaxy):
    """Propose trade agreement. Returns success message or None."""
    if not can_trade(state, faction, galaxy):
        return None
    cost = _get_effective_trade_cost(state, faction)
    state.add_naquadah(-cost)
    set_relation(state, faction, TRADING)
    adjust_favor(state, faction, 10)
    _track_conquest_stat("trades_made")
    from .minor_worlds import notify_quest_event
    notify_quest_event(state, "trade")
    return f"Trade agreement with {faction}! (-{cost} naq) They will not counterattack."


def form_alliance(state, faction, galaxy):
    """Form alliance. Returns success message or None."""
    if not can_ally(state, faction, galaxy):
        return None
    cost = _get_effective_alliance_cost(state, faction)
    state.add_naquadah(-cost)
    set_relation(state, faction, ALLIED)
    adjust_favor(state, faction, 15)
    _track_conquest_stat("alliances_forged")
    return f"Alliance formed with {faction}! (-{cost} naq) Their territory counts as yours."


def betray_alliance(state, faction, rng=None):
    """Break alliance for immediate reward. Returns message.

    Ripple effect: 40% chance each TRADING partner also turns HOSTILE.
    Massive favor loss.
    """
    if not can_betray(state, faction):
        return None
    state.add_naquadah(BETRAY_REWARD)
    set_relation(state, faction, HOSTILE)
    state.conquest_ability_data[f"betrayed_{faction}"] = True
    adjust_favor(state, faction, -40)
    adjust_favor_all(state, -15, exclude=faction)
    _track_conquest_stat("betrayals")
    msg = f"Betrayed {faction}! +{BETRAY_REWARD} naq. Permanently hostile (+15% counterattack)."

    if rng is None:
        rng = random.Random()
    for other, rel in list(state.faction_relations.items()):
        if other == faction:
            continue
        if rel == TRADING and rng.random() < 0.40:
            set_relation(state, other, HOSTILE)
            msg += f" {other} lost trust — now Hostile!"
    return msg


# =========================================================================
# New Player Actions
# =========================================================================

def can_send_gift(state, faction, galaxy):
    """Check if player can send a gift to a faction."""
    rel = get_relation(state, faction)
    if rel == ALLIED:
        return False  # Already max friendly
    if not _has_shared_border(state, faction, galaxy):
        return False
    # Once per faction per turn
    if state.conquest_ability_data.get(f"_gift_sent_{faction}"):
        return False
    return state.naquadah >= GIFT_COST


def send_gift(state, faction, galaxy):
    """Send a gift to improve favor. Returns message or None."""
    if not can_send_gift(state, faction, galaxy):
        return None
    state.add_naquadah(-GIFT_COST)
    personality = _get_diplo_personality(faction)
    favor_gain = int(15 * personality["gift_favor_mult"])
    adjust_favor(state, faction, favor_gain)
    state.conquest_ability_data[f"_gift_sent_{faction}"] = True
    _track_conquest_stat("gifts_sent")
    return f"Sent gift to {faction}! (-{GIFT_COST} naq, +{favor_gain} favor)"


def can_demand_tribute(state, faction, galaxy):
    """Check if player can demand tribute (requires 2x planet count)."""
    rel = get_relation(state, faction)
    if rel in (ALLIED, TRADING):
        return False  # Only from hostile/neutral
    player_planets = galaxy.get_player_planet_count()
    faction_planets = galaxy.get_faction_planet_count(faction)
    if faction_planets == 0:
        return False
    if player_planets < faction_planets * 2:
        return False
    # Cooldown check (5 turns)
    key = f"_demand_cooldown_{faction}"
    if state.conquest_ability_data.get(key, 0) > 0:
        return False
    return True


def demand_tribute(state, faction, galaxy, rng=None):
    """Demand tribute from a weaker faction. Returns message.

    AI acceptance based on favor + personality.
    """
    if not can_demand_tribute(state, faction, galaxy):
        return None
    if rng is None:
        rng = random.Random()

    personality = _get_diplo_personality(faction)
    favor = get_favor(state, faction)
    # Base 40% acceptance, +1% per positive favor, modified by personality
    acceptance = 0.40 + max(0, favor) * 0.01
    acceptance *= (1.0 - personality["demand_refusal_rate"] + 0.50)
    acceptance = max(0.05, min(0.90, acceptance))

    # Set cooldown
    state.conquest_ability_data[f"_demand_cooldown_{faction}"] = 5

    if rng.random() < acceptance:
        naq_gain = rng.randint(20, 40)
        state.add_naquadah(naq_gain)
        adjust_favor(state, faction, -5)
        _track_conquest_stat("tributes_collected")
        return f"{faction} submits! +{naq_gain} naquadah tribute."
    else:
        adjust_favor(state, faction, -10)
        # 20% chance they counterattack next turn
        if rng.random() < 0.20:
            state.conquest_ability_data[f"_demand_retaliation_{faction}"] = 1
            return f"{faction} refuses your demand and prepares for war! (-10 favor, retaliation incoming)"
        return f"{faction} refuses your tribute demand. (-10 favor)"


def can_propose_nap(state, faction, galaxy):
    """Check if player can propose a Non-Aggression Pact."""
    rel = get_relation(state, faction)
    if rel != HOSTILE:
        return False
    if not _has_shared_border(state, faction, galaxy):
        return False
    # Already have active NAP?
    if state.conquest_ability_data.get(f"_nap_timer_{faction}", 0) > 0:
        return False
    return state.naquadah >= NAP_COST


def propose_nap(state, faction, galaxy, rng=None):
    """Propose a Non-Aggression Pact. Returns message.

    AI acceptance based on personality + favor.
    """
    if not can_propose_nap(state, faction, galaxy):
        return None
    if rng is None:
        rng = random.Random()

    personality = _get_diplo_personality(faction)
    favor = get_favor(state, faction)
    acceptance = personality["nap_acceptance"] + favor * 0.005
    acceptance = max(0.10, min(0.95, acceptance))

    state.add_naquadah(-NAP_COST)

    if rng.random() < acceptance:
        set_relation(state, faction, NEUTRAL_REL)
        state.conquest_ability_data[f"_nap_timer_{faction}"] = NAP_DURATION
        adjust_favor(state, faction, 10)
        _track_conquest_stat("naps_formed")
        return f"NAP with {faction}! (-{NAP_COST} naq) No attacks for {NAP_DURATION} turns."
    else:
        adjust_favor(state, faction, -5)
        return f"{faction} rejects your NAP offer. (-{NAP_COST} naq, -5 favor)"


def can_request_military_aid(state, faction, galaxy):
    """Check if player can request military aid from an ally."""
    if get_relation(state, faction) != ALLIED:
        return False
    # Cooldown: once per 3 turns
    key = f"_aid_cooldown_{faction}"
    if state.conquest_ability_data.get(key, 0) > 0:
        return False
    if state.naquadah < MILITARY_AID_COST:
        return False
    # Must have a valid target (hostile faction with shared border to allied faction)
    targets = _get_aid_targets(state, faction, galaxy)
    return len(targets) > 0


def _get_aid_targets(state, allied_faction, galaxy):
    """Get valid targets for military aid (hostile factions adjacent to allied territory)."""
    targets = []
    for pid, planet in galaxy.planets.items():
        if planet.owner == allied_faction:
            for neighbor_id in planet.connections:
                neighbor = galaxy.planets.get(neighbor_id)
                if neighbor and neighbor.owner not in ("player", allied_faction, "neutral"):
                    rel = get_relation(state, neighbor.owner)
                    if rel == HOSTILE and neighbor.owner not in targets:
                        targets.append(neighbor.owner)
    return targets


def request_military_aid(state, faction, target_faction, galaxy, rng=None):
    """Request allied faction to attack a hostile neighbor. Returns message."""
    if not can_request_military_aid(state, faction, galaxy):
        return None
    if rng is None:
        rng = random.Random()

    state.add_naquadah(-MILITARY_AID_COST)
    state.conquest_ability_data[f"_aid_cooldown_{faction}"] = 3
    adjust_favor(state, faction, -5)

    # Success chance: same as AI faction wars logic
    allied_planets = galaxy.get_faction_planet_count(faction)
    target_planets = galaxy.get_faction_planet_count(target_faction)
    total = max(1, allied_planets + target_planets)
    success = 0.25 + 0.30 * (allied_planets / total)
    success = max(0.20, min(0.60, success))

    if rng.random() < success:
        # Find a target planet to capture
        target_planet = None
        for pid, planet in galaxy.planets.items():
            if planet.owner == target_faction:
                for nid in planet.connections:
                    neighbor = galaxy.planets.get(nid)
                    if neighbor and neighbor.owner == faction:
                        target_planet = planet
                        break
            if target_planet:
                break
        if target_planet:
            galaxy.transfer_ownership(target_planet.id, faction)
            _track_conquest_stat("military_aid_successes")
            return (f"{faction} attacks {target_faction}! "
                    f"Captured {target_planet.name}! (-{MILITARY_AID_COST} naq)")
        return f"{faction} attempted attack on {target_faction} but found no target."
    else:
        _track_conquest_stat("military_aid_failures")
        return f"{faction}'s attack on {target_faction} failed. (-{MILITARY_AID_COST} naq)"


def can_propose_joint_attack(state, faction, galaxy):
    """Check if player can propose a joint attack with a trading partner."""
    rel = get_relation(state, faction)
    if rel != TRADING:
        return False
    if state.naquadah < JOINT_ATTACK_COST:
        return False
    # Need a mutual hostile enemy adjacent to both
    targets = _get_joint_attack_targets(state, faction, galaxy)
    return len(targets) > 0


def _get_joint_attack_targets(state, trading_faction, galaxy):
    """Find mutual hostile enemies for joint attack."""
    targets = []
    for other_faction in galaxy.get_active_factions():
        if other_faction == state.player_faction or other_faction == trading_faction:
            continue
        if get_relation(state, other_faction) != HOSTILE:
            continue
        if _has_shared_border(state, other_faction, galaxy):
            targets.append(other_faction)
    return targets


def propose_joint_attack(state, faction, target_faction, galaxy, rng=None):
    """Propose joint attack with trading partner vs mutual enemy. Returns message."""
    if not can_propose_joint_attack(state, faction, galaxy):
        return None
    if rng is None:
        rng = random.Random()

    personality = _get_diplo_personality(faction)
    favor = get_favor(state, faction)
    acceptance = 0.60 + favor * 0.005
    acceptance *= personality.get("trade_propose_mult", 1.0)
    acceptance = max(0.20, min(0.90, acceptance))

    state.add_naquadah(-JOINT_ATTACK_COST)

    if rng.random() < acceptance:
        # -1 cooldown on next attack vs target
        key = f"joint_attack_cooldown_{target_faction}"
        state.conquest_ability_data[key] = 1
        # Trading partner also attacks (30% success)
        partner_msg = ""
        if rng.random() < 0.30:
            for pid, planet in galaxy.planets.items():
                if planet.owner == target_faction:
                    for nid in planet.connections:
                        neighbor = galaxy.planets.get(nid)
                        if neighbor and neighbor.owner == faction:
                            galaxy.transfer_ownership(pid, faction)
                            partner_msg = f" {faction} captured {planet.name}!"
                            break
                if partner_msg:
                    break
        adjust_favor(state, faction, 5)
        _track_conquest_stat("joint_attacks_proposed")
        return (f"Joint offensive with {faction} against {target_faction}! "
                f"-1 cooldown on next attack.{partner_msg}")
    else:
        adjust_favor(state, faction, -3)
        return f"{faction} declines the joint attack against {target_faction}. (-{JOINT_ATTACK_COST} naq)"


# =========================================================================
# NAP Management
# =========================================================================

def tick_nap_timers(state):
    """Tick down NAP timers. Expires NAPs and awards favor for honoring them."""
    keys_to_remove = []
    for key in list(state.conquest_ability_data):
        if key.startswith("_nap_timer_"):
            faction = key[len("_nap_timer_"):]
            state.conquest_ability_data[key] -= 1
            if state.conquest_ability_data[key] <= 0:
                keys_to_remove.append(key)
                # NAP honored: +10 favor
                adjust_favor(state, faction, 10)
    for key in keys_to_remove:
        del state.conquest_ability_data[key]


def has_active_nap(state, faction):
    """Check if there's an active NAP with a faction."""
    return state.conquest_ability_data.get(f"_nap_timer_{faction}", 0) > 0


def get_nap_turns_remaining(state, faction):
    """Get turns remaining on NAP. Returns 0 if no active NAP."""
    return state.conquest_ability_data.get(f"_nap_timer_{faction}", 0)


def break_nap(state, faction):
    """Break a NAP early. Heavy favor penalty."""
    key = f"_nap_timer_{faction}"
    if state.conquest_ability_data.get(key, 0) > 0:
        del state.conquest_ability_data[key]
        set_relation(state, faction, HOSTILE)
        adjust_favor(state, faction, -30)
        adjust_favor_all(state, -10, exclude=faction)
        state.conquest_ability_data[f"_nap_broken_{faction}"] = True
        _track_conquest_stat("naps_broken")


# =========================================================================
# Per-Turn Cooldown Ticking
# =========================================================================

def tick_diplomacy_cooldowns(state):
    """Tick all diplomacy-related cooldowns (demand, aid, gift, retaliation)."""
    prefixes = ("_demand_cooldown_", "_aid_cooldown_", "_demand_retaliation_")
    keys_to_remove = []
    for key in list(state.conquest_ability_data):
        for prefix in prefixes:
            if key.startswith(prefix):
                state.conquest_ability_data[key] -= 1
                if state.conquest_ability_data[key] <= 0:
                    keys_to_remove.append(key)
                break
    for key in keys_to_remove:
        del state.conquest_ability_data[key]
    # Reset per-turn gift flags
    for key in list(state.conquest_ability_data):
        if key.startswith("_gift_sent_"):
            del state.conquest_ability_data[key]


def get_demand_retaliation_bonus(state, faction):
    """Get extra counterattack chance from refused tribute demand."""
    if state.conquest_ability_data.get(f"_demand_retaliation_{faction}", 0) > 0:
        return 0.15
    return 0.0


# =========================================================================
# Faction Elimination Consequences
# =========================================================================

def on_faction_eliminated(state, eliminated_faction):
    """Apply diplomatic consequences when a faction is eliminated.

    All survivors lose -15 favor (galactic fear).
    Factions that were hostile to the eliminated faction gain +10 (relief).
    """
    for faction, rel in list(state.faction_relations.items()):
        if faction == eliminated_faction:
            continue
        adjust_favor(state, faction, -15)
        # TODO: We don't track AI-to-AI relations, so approximate:
        # Factions from the same "personality cluster" as eliminated get less penalty
        # For now, all get the same -15


# =========================================================================
# Existing Helper Functions
# =========================================================================

def get_betrayal_counter_bonus(state, faction):
    """Get extra counterattack chance from betrayal."""
    if state.conquest_ability_data.get(f"betrayed_{faction}"):
        return 0.15
    if state.conquest_ability_data.get(f"_nap_broken_{faction}"):
        return 0.10
    return 0.0


def check_ai_trade_proposals(state, galaxy, rng):
    """Check if weakened AI factions propose trades.

    Returns list of (faction, message) proposals.
    """
    proposals = []
    for faction in galaxy.get_active_factions():
        if faction == state.player_faction:
            continue
        rel = get_relation(state, faction)
        if rel != HOSTILE:
            continue
        planet_count = galaxy.get_faction_planet_count(faction)
        if planet_count <= 2 and rng.random() < 0.30:
            proposals.append((faction, f"{faction} offers a trade agreement (they're weakened)."))
    return proposals


def generate_ai_proposals(state, galaxy, rng):
    """Generate AI diplomatic proposals at turn start.

    Returns list of proposal dicts:
    {type, faction, description, accept_label, reject_label, ...}
    """
    proposals = []
    for faction in galaxy.get_active_factions():
        if faction == state.player_faction:
            continue
        rel = get_relation(state, faction)
        planet_count = galaxy.get_faction_planet_count(faction)
        favor = get_favor(state, faction)
        personality = _get_diplo_personality(faction)
        player_planets = galaxy.get_player_planet_count()

        if rel == HOSTILE:
            # Trade offer from weakened faction
            trade_chance = 0.25 * personality["trade_propose_mult"]
            if planet_count <= 3 and rng.random() < trade_chance:
                proposals.append({
                    "type": "trade_offer",
                    "faction": faction,
                    "description": f"{faction} offers a trade agreement and a 20 naquadah signing bonus.",
                    "accept_label": "Accept Trade",
                    "reject_label": "Decline",
                })
                continue  # Only one proposal per faction

            # Ceasefire from very weak faction
            if planet_count <= 2 and rng.random() < 0.20:
                proposals.append({
                    "type": "ceasefire",
                    "faction": faction,
                    "description": f"{faction} requests a ceasefire. They will stop counterattacking.",
                    "accept_label": "Accept Ceasefire",
                    "reject_label": "Refuse",
                })
                continue

            # Tribute demand from strong faction
            if planet_count >= 6 and rng.random() < 0.15:
                proposals.append({
                    "type": "tribute_demand",
                    "faction": faction,
                    "description": f"{faction} demands 40 naquadah tribute — or face increased aggression.",
                    "accept_label": "Pay Tribute (-40 naq)",
                    "reject_label": "Refuse",
                })
                continue

            # Peace offering: hostile faction lost 2+ planets recently and has positive favor
            lost_key = f"_faction_planets_lost_{faction}"
            planets_lost = state.conquest_ability_data.get(lost_key, 0)
            if planets_lost >= 2 and favor > -20 and rng.random() < 0.25:
                proposals.append({
                    "type": "peace_offering",
                    "faction": faction,
                    "description": f"{faction} sends 25 naquadah as a peace offering and requests a ceasefire.",
                    "accept_label": "Accept Peace (+25 naq)",
                    "reject_label": "Refuse",
                })
                continue

            # Ultimatum from strong faction with negative favor
            if planet_count >= 6 and favor < -20 and rng.random() < 0.12:
                # Find an alliance target
                allied_factions = [f for f, r in state.faction_relations.items() if r == ALLIED]
                if allied_factions:
                    target_ally = rng.choice(allied_factions)
                    proposals.append({
                        "type": "ultimatum",
                        "faction": faction,
                        "target": target_ally,
                        "description": (f"{faction} demands you break your alliance with {target_ally} "
                                        f"— or face total war!"),
                        "accept_label": f"Break Alliance with {target_ally}",
                        "reject_label": "Refuse Ultimatum",
                    })
                    continue

            # --- Faction-unique proposals (HOSTILE) ---
            unique = personality.get("unique_proposal")

            # Goa'uld Subjugation Demand
            if unique == "subjugation" and planet_count >= 5 and rng.random() < 0.12:
                # Find a player border planet
                border_planet = _find_player_border_planet(state, faction, galaxy)
                if border_planet:
                    proposals.append({
                        "type": "goauld_subjugation",
                        "faction": faction,
                        "target_planet": border_planet.id,
                        "description": (f"The Goa'uld demand you surrender {border_planet.name} "
                                        f"— or face a full-scale assault!"),
                        "accept_label": f"Surrender {border_planet.name}",
                        "reject_label": "Defy the Goa'uld",
                    })
                    continue

            # Jaffa Revenge Pact (vs Goa'uld specifically)
            if unique == "revenge_pact" and rng.random() < 0.18:
                goauld_active = galaxy.get_faction_planet_count("Goa'uld") > 0
                if goauld_active and _has_shared_border(state, "Goa'uld", galaxy):
                    proposals.append({
                        "type": "jaffa_revenge_pact",
                        "faction": faction,
                        "description": ("The Jaffa Rebellion proposes a Revenge Pact — "
                                        "mutual -1 cooldown vs Goa'uld planets and a trade agreement."),
                        "accept_label": "Honor the Pact",
                        "reject_label": "Decline",
                    })
                    continue

        elif rel == TRADING:
            # Joint attack proposal
            mutual_enemies = []
            for other_faction in galaxy.get_active_factions():
                if other_faction == state.player_faction or other_faction == faction:
                    continue
                if get_relation(state, other_faction) == HOSTILE:
                    if _has_shared_border(state, other_faction, galaxy):
                        mutual_enemies.append(other_faction)
            if mutual_enemies and rng.random() < 0.15:
                target = rng.choice(mutual_enemies)
                proposals.append({
                    "type": "joint_attack",
                    "faction": faction,
                    "target": target,
                    "description": (f"{faction} proposes a joint offensive against {target}. "
                                    f"Accept for -1 attack cooldown vs {target}."),
                    "accept_label": "Coordinate Attack",
                    "reject_label": "Decline",
                })
                continue

            # Alliance offer from faction with high favor
            if favor >= 30 and rng.random() < 0.20:
                proposals.append({
                    "type": "alliance_offer",
                    "faction": faction,
                    "description": (f"{faction} is impressed by your diplomacy and offers "
                                    f"a full alliance at no cost!"),
                    "accept_label": "Accept Alliance",
                    "reject_label": "Decline",
                })
                continue

            # --- Faction-unique proposals (TRADING) ---
            unique = personality.get("unique_proposal")

            # Asgard Technology Exchange
            if unique == "tech_exchange" and rng.random() < 0.15:
                proposals.append({
                    "type": "asgard_tech_exchange",
                    "faction": faction,
                    "description": ("The Asgard offer advanced technology — trade 50 naquadah "
                                    "for +1 extra card draw in your next 5 battles."),
                    "accept_label": "Accept (-50 naq)",
                    "reject_label": "Decline",
                })
                continue

            # Lucian Protection Racket
            if unique == "protection_racket" and planet_count >= 4 and rng.random() < 0.15:
                proposals.append({
                    "type": "lucian_protection_racket",
                    "faction": faction,
                    "description": ("The Lucian Alliance 'suggests' you pay 15 naquadah per turn "
                                    "for protection — or they'll sabotage your operations."),
                    "accept_label": "Pay Protection (-15/turn)",
                    "reject_label": "Refuse",
                })
                continue

            # Tau'ri Mutual Defense
            if unique == "mutual_defense" and rng.random() < 0.15:
                proposals.append({
                    "type": "tauri_mutual_defense",
                    "faction": faction,
                    "description": ("The Tau'ri propose a Mutual Defense Treaty — "
                                    "both sides get +1 defense power for 5 turns."),
                    "accept_label": "Sign Treaty",
                    "reject_label": "Decline",
                })
                continue

        elif rel == ALLIED:
            # --- Faction-unique proposals (ALLIED) ---
            unique = personality.get("unique_proposal")

            # Alteran Knowledge Sharing (after turn 15)
            if unique == "knowledge_sharing" and state.turn_number >= 15 and rng.random() < 0.15:
                proposals.append({
                    "type": "alteran_knowledge_sharing",
                    "faction": faction,
                    "description": ("The Alteran share fragments of Ancient knowledge — "
                                    "trade 30 naquadah for +10 Wisdom."),
                    "accept_label": "Accept (-30 naq)",
                    "reject_label": "Decline",
                })
                continue

    return proposals


def apply_proposal(state, proposal, accepted, galaxy, rng):
    """Apply the result of an AI diplomatic proposal.

    Returns result message string.
    """
    p_type = proposal["type"]
    faction = proposal["faction"]

    if p_type == "trade_offer":
        if accepted:
            set_relation(state, faction, TRADING)
            state.add_naquadah(20)
            adjust_favor(state, faction, 5)
            _track_conquest_stat("ai_trades_accepted")
            return f"Trade with {faction}! +20 naq signing bonus."
        adjust_favor(state, faction, -5)
        return f"Declined {faction}'s trade offer."

    elif p_type == "ceasefire":
        if accepted:
            set_relation(state, faction, NEUTRAL_REL)
            adjust_favor(state, faction, 5)
            _track_conquest_stat("ceasefires_accepted")
            return f"Ceasefire with {faction}. They won't counterattack."
        return f"Refused {faction}'s ceasefire."

    elif p_type == "tribute_demand":
        if accepted:
            state.add_naquadah(-40)
            adjust_favor(state, faction, 5)
            return f"Paid 40 naquadah tribute to {faction}."
        else:
            key = f"tribute_rejected_{faction}"
            state.conquest_ability_data[key] = 3
            adjust_favor(state, faction, -10)
            return f"Refused {faction}'s demand! They're +10% more aggressive for 3 turns."

    elif p_type == "joint_attack":
        if accepted:
            target = proposal.get("target", "unknown")
            key = f"joint_attack_cooldown_{target}"
            state.conquest_ability_data[key] = 1
            adjust_favor(state, faction, 5)
            return f"Joint offensive with {faction} against {target}! -1 cooldown on next attack."
        else:
            if rng.random() < 0.10:
                set_relation(state, faction, HOSTILE)
                adjust_favor(state, faction, -10)
                return f"Declined {faction}'s joint attack. They feel slighted — now Hostile!"
            return f"Declined {faction}'s joint attack proposal."

    elif p_type == "peace_offering":
        if accepted:
            state.add_naquadah(25)
            set_relation(state, faction, NEUTRAL_REL)
            adjust_favor(state, faction, 10)
            _track_conquest_stat("peace_offerings_accepted")
            return f"Accepted {faction}'s peace offering! +25 naq, ceasefire in effect."
        adjust_favor(state, faction, -10)
        return f"Rejected {faction}'s peace offering."

    elif p_type == "alliance_offer":
        if accepted:
            set_relation(state, faction, ALLIED)
            adjust_favor(state, faction, 10)
            _track_conquest_stat("alliances_forged")
            return f"Alliance with {faction} — at their expense! Territory bridge activated."
        adjust_favor(state, faction, -10)
        return f"Declined {faction}'s alliance offer."

    elif p_type == "ultimatum":
        target_ally = proposal.get("target", "unknown")
        if accepted:
            # Break the alliance
            for f, rel in list(state.faction_relations.items()):
                if f == target_ally:
                    set_relation(state, f, HOSTILE)
                    adjust_favor(state, f, -20)
            adjust_favor(state, faction, 10)
            return f"Broke alliance with {target_ally} under {faction}'s pressure."
        else:
            # Full aggression: 100% counterattack for 2 turns
            state.conquest_ability_data[f"_ultimatum_aggro_{faction}"] = 2
            adjust_favor(state, faction, -15)
            return f"Defied {faction}'s ultimatum! They're enraged — 100% counterattack for 2 turns."

    elif p_type == "goauld_subjugation":
        target_pid = proposal.get("target_planet")
        if accepted:
            planet = galaxy.planets.get(target_pid)
            if planet:
                galaxy.transfer_ownership(target_pid, faction)
                adjust_favor(state, faction, 15)
                return f"Surrendered {planet.name} to the Goa'uld to avoid war."
            return f"Surrendered territory to the Goa'uld."
        else:
            state.conquest_ability_data[f"_ultimatum_aggro_{faction}"] = 2
            adjust_favor(state, faction, -15)
            return f"Defied the Goa'uld! They launch a full-scale assault — 100% counterattack for 2 turns."

    elif p_type == "jaffa_revenge_pact":
        if accepted:
            set_relation(state, faction, TRADING)
            state.conquest_ability_data["_jaffa_revenge_pact"] = True
            # -1 cooldown vs Goa'uld
            state.conquest_ability_data["joint_attack_cooldown_Goa'uld"] = 1
            adjust_favor(state, faction, 15)
            _track_conquest_stat("ai_trades_accepted")
            return "Revenge Pact with the Jaffa! Trade established + mutual -1 cooldown vs Goa'uld."
        adjust_favor(state, faction, -5)
        return "Declined the Jaffa's Revenge Pact."

    elif p_type == "asgard_tech_exchange":
        if accepted:
            if state.naquadah >= 50:
                state.add_naquadah(-50)
                state.conquest_ability_data["_asgard_tech_draws"] = 5
                adjust_favor(state, faction, 10)
                return "Asgard technology acquired! +1 card draw for next 5 battles. (-50 naq)"
            return "Insufficient naquadah for Asgard technology exchange."
        return "Declined Asgard technology exchange."

    elif p_type == "lucian_protection_racket":
        if accepted:
            state.conquest_ability_data["_lucian_racket_active"] = True
            adjust_favor(state, faction, 5)
            return "Paying Lucian Alliance protection money. (-15 naq/turn)"
        else:
            # Sabotage: random building damage
            adjust_favor(state, faction, -10)
            state.conquest_ability_data[f"_lucian_sabotage"] = 3
            return ("Refused the Lucian Alliance! They'll sabotage your income "
                    "(-5 naq/turn for 3 turns).")

    elif p_type == "tauri_mutual_defense":
        if accepted:
            state.conquest_ability_data["_mutual_defense_turns"] = 5
            adjust_favor(state, faction, 10)
            _track_conquest_stat("defense_treaties")
            return "Mutual Defense Treaty signed with the Tau'ri! +1 defense power for 5 turns."
        return "Declined Tau'ri Mutual Defense Treaty."

    elif p_type == "alteran_knowledge_sharing":
        if accepted:
            if state.naquadah >= 30:
                state.add_naquadah(-30)
                state.wisdom += 10
                adjust_favor(state, faction, 10)
                return "The Alteran share their knowledge! +10 Wisdom. (-30 naq)"
            return "Insufficient naquadah for Alteran knowledge exchange."
        return "Declined Alteran knowledge sharing."

    return ""


# =========================================================================
# Tribute Rejection / Ultimatum Timers
# =========================================================================

def get_tribute_reject_bonus(state, faction):
    """Get extra counterattack chance from tribute rejection (0.10 if active, else 0.0)."""
    key = f"tribute_rejected_{faction}"
    if state.conquest_ability_data.get(key, 0) > 0:
        return 0.10
    return 0.0


def get_ultimatum_aggro(state, faction):
    """Get counterattack override from ultimatum refusal. Returns 1.0 or 0."""
    key = f"_ultimatum_aggro_{faction}"
    if state.conquest_ability_data.get(key, 0) > 0:
        return 1.0
    return 0.0


def tick_tribute_rejections(state):
    """Decrement tribute rejection and ultimatum timers each turn."""
    keys_to_remove = []
    for key in list(state.conquest_ability_data):
        if key.startswith("tribute_rejected_") or key.startswith("_ultimatum_aggro_"):
            state.conquest_ability_data[key] -= 1
            if state.conquest_ability_data[key] <= 0:
                keys_to_remove.append(key)
    for key in keys_to_remove:
        del state.conquest_ability_data[key]


def tick_special_effects(state):
    """Tick faction-unique timed effects (mutual defense, lucian sabotage, etc.)."""
    # Mutual defense countdown
    key = "_mutual_defense_turns"
    if state.conquest_ability_data.get(key, 0) > 0:
        state.conquest_ability_data[key] -= 1
        if state.conquest_ability_data[key] <= 0:
            del state.conquest_ability_data[key]

    # Lucian sabotage countdown
    key = "_lucian_sabotage"
    if state.conquest_ability_data.get(key, 0) > 0:
        state.conquest_ability_data[key] -= 1
        if state.conquest_ability_data[key] <= 0:
            del state.conquest_ability_data[key]

    # Lucian racket: deduct 15/turn
    if state.conquest_ability_data.get("_lucian_racket_active"):
        rel = state.faction_relations.get("Lucian Alliance", HOSTILE)
        if rel in (TRADING, ALLIED):
            state.add_naquadah(-15)
        else:
            # Racket ends if relation breaks
            del state.conquest_ability_data["_lucian_racket_active"]

    # Asgard tech draws: just a counter, decremented per battle in card_battle


def get_mutual_defense_bonus(state):
    """Get defense power bonus from Tau'ri Mutual Defense Treaty."""
    if state.conquest_ability_data.get("_mutual_defense_turns", 0) > 0:
        return 1
    return 0


def get_lucian_sabotage_penalty(state):
    """Get income penalty from Lucian sabotage."""
    if state.conquest_ability_data.get("_lucian_sabotage", 0) > 0:
        return 5
    return 0


def get_asgard_tech_bonus(state):
    """Get extra card draw from Asgard tech exchange. Returns int."""
    return 1 if state.conquest_ability_data.get("_asgard_tech_draws", 0) > 0 else 0


def consume_asgard_tech_draw(state):
    """Decrement Asgard tech draw counter after a battle."""
    key = "_asgard_tech_draws"
    if state.conquest_ability_data.get(key, 0) > 0:
        state.conquest_ability_data[key] -= 1
        if state.conquest_ability_data[key] <= 0:
            del state.conquest_ability_data[key]


# =========================================================================
# Alliance Strain & Border Checks
# =========================================================================

def check_potential_strain(state, planet_id, galaxy):
    """Check if attacking a planet might strain an alliance.

    Returns warning string or None.
    """
    planet = galaxy.planets.get(planet_id)
    if not planet:
        return None
    allied_factions = get_adjacency_bonus_factions(state)
    if not allied_factions:
        return None
    for neighbor_id in planet.connections:
        neighbor = galaxy.planets.get(neighbor_id)
        if neighbor and neighbor.owner in allied_factions:
            return (f"Attacking {planet.name} may strain your alliance "
                    f"with {neighbor.owner} (30% chance of downgrade).")
    # Also check NAP
    if planet.owner != "neutral":
        nap_faction = planet.owner
        if has_active_nap(state, nap_faction):
            return (f"Attacking {planet.name} will BREAK your NAP "
                    f"with {nap_faction}! (-30 favor, permanent trust penalty)")
    return None


def is_faction_friendly(state, faction):
    """Check if a faction is trading or allied (won't counterattack)."""
    rel = get_relation(state, faction)
    if rel in (TRADING, ALLIED):
        return True
    # NEUTRAL with active NAP also won't counterattack
    if rel == NEUTRAL_REL and has_active_nap(state, faction):
        return True
    return False


def get_adjacency_bonus_factions(state):
    """Get factions whose territory counts as player's for adjacency (allied)."""
    return [f for f, rel in state.faction_relations.items() if rel == ALLIED]


# =========================================================================
# Income (Enriched Tiers)
# =========================================================================

def get_neutral_income(state):
    """Get naquadah income per turn from neutral relations (+2 per neutral partner)."""
    count = sum(1 for f, rel in state.faction_relations.items()
                if rel == NEUTRAL_REL)
    return 2 * count


def get_trade_income(state):
    """Get naquadah income per turn from trading partners (+8 per partner)."""
    count = sum(1 for rel in state.faction_relations.values() if rel == TRADING)
    return 8 * count


def get_alliance_upkeep(state):
    """Get naquadah upkeep per turn from alliances (-10 per ally)."""
    count = sum(1 for rel in state.faction_relations.values() if rel == ALLIED)
    return 10 * count


def get_diplomacy_net_income(state):
    """Get total net diplomacy income/cost."""
    income = get_neutral_income(state) + get_trade_income(state)
    upkeep = get_alliance_upkeep(state) + get_lucian_sabotage_penalty(state)
    if state.conquest_ability_data.get("_lucian_racket_active"):
        rel = state.faction_relations.get("Lucian Alliance", HOSTILE)
        if rel in (TRADING, ALLIED):
            upkeep += 15
    return income - upkeep


def has_trading_neighbor(state, planet_id, galaxy):
    """Check if a planet is adjacent to a trading partner's territory."""
    planet = galaxy.planets.get(planet_id)
    if not planet:
        return False
    for nid in planet.connections:
        neighbor = galaxy.planets.get(nid)
        if neighbor and neighbor.owner != "player" and neighbor.owner != "neutral":
            rel = get_relation(state, neighbor.owner)
            if rel == TRADING:
                return True
    return False


def get_trading_building_discount(state, planet_id, galaxy):
    """Get building cost discount for planets adjacent to trading partners.

    Returns discount amount (0 or 10% of base cost approximated as flat 10).
    """
    if has_trading_neighbor(state, planet_id, galaxy):
        return 10
    return 0


# =========================================================================
# Conquest Strain
# =========================================================================

def check_conquest_strain(state, conquered_planet, galaxy, rng):
    """Check if conquering near an ally causes diplomatic strain.

    30% chance to downgrade alliance to trading if conquered planet
    is adjacent to allied faction territory.

    Returns: warning message string if strain occurred, else None.
    """
    allied_factions = get_adjacency_bonus_factions(state)
    if not allied_factions:
        return None

    for neighbor_id in conquered_planet.connections:
        neighbor = galaxy.planets.get(neighbor_id)
        if not neighbor:
            continue
        if neighbor.owner in allied_factions:
            strained_faction = neighbor.owner
            adjust_favor(state, strained_faction, -10)
            if rng.random() < 0.30:
                set_relation(state, strained_faction, TRADING)
                _track_conquest_stat("alliances_strained")
                return (f"{strained_faction} feels threatened by your expansion! "
                        f"Alliance downgraded to Trading. (-10 favor)")
            return None  # favor loss but no downgrade
    return None


# =========================================================================
# NAP break on attack
# =========================================================================

def check_nap_break(state, planet_id, galaxy):
    """Check if attacking a planet breaks a NAP. Returns faction name or None."""
    planet = galaxy.planets.get(planet_id)
    if not planet or planet.owner == "neutral":
        return None
    faction = planet.owner
    if has_active_nap(state, faction):
        return faction
    return None


# =========================================================================
# Diplomacy Options (for UI)
# =========================================================================

def _has_shared_border(state, faction, galaxy):
    """Check if player and faction share a border."""
    for pid, planet in galaxy.planets.items():
        if planet.owner == "player":
            for neighbor_id in planet.connections:
                neighbor = galaxy.planets.get(neighbor_id)
                if neighbor and neighbor.owner == faction:
                    return True
    return False


def _find_player_border_planet(state, faction, galaxy):
    """Find a player planet adjacent to a faction's territory."""
    for pid, planet in galaxy.planets.items():
        if planet.owner == "player":
            for neighbor_id in planet.connections:
                neighbor = galaxy.planets.get(neighbor_id)
                if neighbor and neighbor.owner == faction:
                    return planet
    return None


def get_diplomacy_options(state, galaxy):
    """Get available diplomatic actions for each faction.

    Returns: list of (faction, rel, actions) where actions is list of
    (action_name, cost_or_reward, enabled, description)
    """
    options = []
    from .galaxy_map import ALL_FACTIONS
    for faction in ALL_FACTIONS:
        if faction == state.player_faction:
            continue
        if galaxy.get_faction_planet_count(faction) == 0:
            continue
        rel = get_relation(state, faction)
        favor = get_favor(state, faction)
        actions = []

        if rel == HOSTILE:
            eff_cost = _get_effective_trade_cost(state, faction)
            actions.append(("trade", eff_cost, can_trade(state, faction, galaxy),
                            f"Propose trade (-{eff_cost} naq): +8 naq/turn, card pool access"))
            actions.append(("gift", GIFT_COST, can_send_gift(state, faction, galaxy),
                            f"Send gift (-{GIFT_COST} naq): improve favor"))
            actions.append(("nap", NAP_COST, can_propose_nap(state, faction, galaxy),
                            f"Non-Aggression Pact (-{NAP_COST} naq): {NAP_DURATION}-turn ceasefire"))
            if can_demand_tribute(state, faction, galaxy):
                actions.append(("demand", 0, True,
                                "Demand tribute: gain 20-40 naq if accepted"))

        elif rel == NEUTRAL_REL:
            eff_cost = _get_effective_trade_cost(state, faction)
            actions.append(("trade", eff_cost, can_trade(state, faction, galaxy),
                            f"Propose trade (-{eff_cost} naq): +8 naq/turn, card pool access"))
            actions.append(("gift", GIFT_COST, can_send_gift(state, faction, galaxy),
                            f"Send gift (-{GIFT_COST} naq): improve favor"))
            nap_remaining = get_nap_turns_remaining(state, faction)
            if nap_remaining > 0:
                actions.append(("nap_info", 0, False,
                                f"NAP active: {nap_remaining} turns remaining"))

        elif rel == TRADING:
            eff_cost = _get_effective_alliance_cost(state, faction)
            actions.append(("alliance", eff_cost, can_ally(state, faction, galaxy),
                            f"Form alliance (-{eff_cost} naq): network bridge, 50% passives"))
            actions.append(("gift", GIFT_COST, can_send_gift(state, faction, galaxy),
                            f"Send gift (-{GIFT_COST} naq): improve favor"))
            if can_propose_joint_attack(state, faction, galaxy):
                targets = _get_joint_attack_targets(state, faction, galaxy)
                target_str = ", ".join(targets[:2])
                actions.append(("joint", JOINT_ATTACK_COST, True,
                                f"Propose joint attack (-{JOINT_ATTACK_COST} naq) vs {target_str}"))

        elif rel == ALLIED:
            actions.append(("betray", -BETRAY_REWARD, True,
                            f"Betray (+{BETRAY_REWARD} naq): permanently hostile, trust ripple"))
            if can_request_military_aid(state, faction, galaxy):
                targets = _get_aid_targets(state, faction, galaxy)
                target_str = ", ".join(targets[:2])
                actions.append(("aid", MILITARY_AID_COST, True,
                                f"Request military aid (-{MILITARY_AID_COST} naq) vs {target_str}"))

        options.append((faction, rel, actions))
    return options
