"""
STARGWENT - GALACTIC CONQUEST - Doctrine Trees

New resource "Wisdom" funds policy trees that force strategic identity per run.
5 trees, 4 sequential policies each + completion bonus.
Can complete 2-3 trees per campaign, creating distinct "builds."
"""


# --- Doctrine Tree Definitions ---

DOCTRINE_TREES = {
    "ascension": {
        "name": "Path of Ascension",
        "color": (200, 180, 255),
        "icon": "\u2605",  # star
        "policies": [
            {"id": "asc_1", "name": "Ancient Meditation", "base_cost": 10,
             "effect": {"wisdom_per_turn": 3},
             "desc": "+3 Wisdom/turn"},
            {"id": "asc_2", "name": "Repository Access", "base_cost": 20,
             "effect": {"extra_card_choices": 1},
             "desc": "+1 reward card choice"},
            {"id": "asc_3", "name": "Enlightened Warfare", "base_cost": 30,
             "effect": {"battle_power_bonus": 1},
             "desc": "+1 power to all cards in battle"},
            {"id": "asc_4", "name": "Near-Ascension", "base_cost": 40,
             "effect": {"wisdom_income_doubled": True},
             "desc": "Wisdom income doubled"},
        ],
        "completion_bonus": {
            "name": "Ascension Mastery",
            "desc": "Unlocks Ascension Victory",
            "effect": {"unlock_victory": "ascension"},
        },
    },
    "conquest": {
        "name": "Doctrine of Conquest",
        "color": (255, 100, 80),
        "icon": "\u2694",  # swords
        "policies": [
            {"id": "con_1", "name": "Blitzkrieg Tactics", "base_cost": 10,
             "effect": {"attack_cooldown_reduction": 1},
             "desc": "-1 turn attack cooldown"},
            {"id": "con_2", "name": "Veteran Troops", "base_cost": 20,
             "effect": {"attack_power_bonus": 1},
             "desc": "+1 power when attacking"},
            {"id": "con_3", "name": "War Logistics", "base_cost": 30,
             "effect": {"extra_attacks_per_turn": 1},
             "desc": "+1 attack per turn"},
            {"id": "con_4", "name": "Total Supremacy", "base_cost": 40,
             "effect": {"conquest_naq_bonus": 30},
             "desc": "+30 naq per conquered planet"},
        ],
        "completion_bonus": {
            "name": "Military Mastery",
            "desc": "First fortification free each turn",
            "effect": {"free_fortify": True},
        },
    },
    "alliance": {
        "name": "Alliance Doctrine",
        "color": (100, 220, 180),
        "icon": "\u2696",  # scales
        "policies": [
            {"id": "all_1", "name": "Diplomatic Mastery", "base_cost": 10,
             "effect": {"minor_world_influence_per_turn": 5},
             "desc": "+5 influence/turn to all minor worlds"},
            {"id": "all_2", "name": "Free Trade Zone", "base_cost": 20,
             "effect": {"trade_cost_discount": 20},
             "desc": "Trade agreements cost -20 naq"},
            {"id": "all_3", "name": "Deep Alliance", "base_cost": 30,
             "effect": {"alliance_upkeep_reduction": 5},
             "desc": "Alliance upkeep -5/turn"},
            {"id": "all_4", "name": "Galactic Federation", "base_cost": 40,
             "effect": {"passive_sharing_boost": True},
             "desc": "Allied passive sharing 50% -> 75%"},
        ],
        "completion_bonus": {
            "name": "Diplomacy Mastery",
            "desc": "Unlocks Alliance Victory",
            "effect": {"unlock_victory": "galactic_alliance"},
        },
    },
    "shadow": {
        "name": "Shadow Operations",
        "color": (180, 100, 200),
        "icon": "\u2623",  # biohazard
        "policies": [
            {"id": "shd_1", "name": "Tok'ra Training", "base_cost": 10,
             "effect": {"operative_death_risk_reduction": 0.10},
             "desc": "Operative death risk -10%"},
            {"id": "shd_2", "name": "Intelligence Networks", "base_cost": 20,
             "effect": {"mission_time_reduction": 1},
             "desc": "Mission times -1 turn (min 1)"},
            {"id": "shd_3", "name": "Advanced Sabotage", "base_cost": 30,
             "effect": {"sabotage_extra_cards": 1},
             "desc": "Sabotage removes 2 cards (was 1)"},
            {"id": "shd_4", "name": "Shadow Government", "base_cost": 40,
             "effect": {"free_operative_interval": 8},
             "desc": "Free operative every 8 turns"},
        ],
        "completion_bonus": {
            "name": "Shadow Mastery",
            "desc": "Coup success doubled, no diplomatic incidents",
            "effect": {"shadow_mastery": True},
        },
    },
    "innovation": {
        "name": "Technological Innovation",
        "color": (100, 200, 255),
        "icon": "\u2699",  # gear
        "policies": [
            {"id": "inn_1", "name": "Accelerated Research", "base_cost": 10,
             "effect": {"building_naq_bonus": 10},
             "desc": "+10 naq/turn from buildings"},
            {"id": "inn_2", "name": "Advanced Engineering", "base_cost": 20,
             "effect": {"building_cost_reduction": 25},
             "desc": "All buildings cost -25 naq"},
            {"id": "inn_3", "name": "Network Optimization", "base_cost": 30,
             "effect": {"network_tier_reduction": 1},
             "desc": "Network tier thresholds -1 planet each"},
            {"id": "inn_4", "name": "Supergate Project", "base_cost": 40,
             "effect": {"enable_supergate": True},
             "desc": "Enables Supergate wonder construction"},
        ],
        "completion_bonus": {
            "name": "Tech Mastery",
            "desc": "Unlocks Network Victory",
            "effect": {"unlock_victory": "stargate_supremacy"},
        },
    },
}

# Flat lookup: policy_id -> (tree_id, index)
_POLICY_LOOKUP = {}
for _tree_id, _tree in DOCTRINE_TREES.items():
    for _idx, _policy in enumerate(_tree["policies"]):
        _POLICY_LOOKUP[_policy["id"]] = (_tree_id, _idx)

# Escalation: each adopted policy adds this to all future costs
ESCALATION_PER_POLICY = 10


# --- Core Functions ---

def get_policy_cost(policy_id, state):
    """Get the effective cost of adopting a policy (base + escalation)."""
    tree_id, idx = _POLICY_LOOKUP.get(policy_id, (None, None))
    if tree_id is None:
        return 999
    policy = DOCTRINE_TREES[tree_id]["policies"][idx]
    base = policy["base_cost"]
    escalation = len(state.adopted_policies) * ESCALATION_PER_POLICY
    return base + escalation


def can_adopt(state, policy_id):
    """Check if a policy can be adopted (wisdom available, prerequisite met)."""
    if policy_id in state.adopted_policies:
        return False
    tree_id, idx = _POLICY_LOOKUP.get(policy_id, (None, None))
    if tree_id is None:
        return False
    # Check prerequisite: previous policy in tree must be adopted
    if idx > 0:
        prev_id = DOCTRINE_TREES[tree_id]["policies"][idx - 1]["id"]
        if prev_id not in state.adopted_policies:
            return False
    # Check wisdom
    cost = get_policy_cost(policy_id, state)
    return state.wisdom >= cost


def adopt_policy(state, policy_id):
    """Adopt a policy. Deducts wisdom. Returns message or None."""
    if not can_adopt(state, policy_id):
        return None
    cost = get_policy_cost(policy_id, state)
    state.wisdom -= cost
    state.adopted_policies.append(policy_id)

    tree_id, idx = _POLICY_LOOKUP[policy_id]
    tree = DOCTRINE_TREES[tree_id]
    policy = tree["policies"][idx]

    # Check if tree is now complete
    all_ids = [p["id"] for p in tree["policies"]]
    if all(pid in state.adopted_policies for pid in all_ids):
        if tree_id not in state.completed_doctrines:
            state.completed_doctrines.append(tree_id)
            bonus_name = tree["completion_bonus"]["name"]
            return f"Adopted {policy['name']}! (-{cost} Wisdom) TREE COMPLETE: {bonus_name}!"

    return f"Adopted {policy['name']}! (-{cost} Wisdom)"


def is_tree_complete(state, tree_id):
    """Check if all policies in a tree are adopted."""
    return tree_id in state.completed_doctrines


def get_next_policy(state, tree_id):
    """Get the next adoptable policy in a tree, or None if complete/all adopted."""
    tree = DOCTRINE_TREES.get(tree_id)
    if not tree:
        return None
    for policy in tree["policies"]:
        if policy["id"] not in state.adopted_policies:
            return policy
    return None


def get_active_effects(state):
    """Aggregate all effects from adopted policies + completed tree bonuses.

    Returns dict of effect_key -> value (aggregated).
    """
    effects = {}
    for pid in state.adopted_policies:
        tree_id, idx = _POLICY_LOOKUP.get(pid, (None, None))
        if tree_id is None:
            continue
        policy = DOCTRINE_TREES[tree_id]["policies"][idx]
        for key, val in policy["effect"].items():
            if isinstance(val, bool):
                effects[key] = True
            elif isinstance(val, (int, float)):
                effects[key] = effects.get(key, 0) + val
            else:
                effects[key] = val
    # Completion bonuses
    for tree_id in state.completed_doctrines:
        tree = DOCTRINE_TREES.get(tree_id)
        if tree:
            for key, val in tree["completion_bonus"]["effect"].items():
                if isinstance(val, bool):
                    effects[key] = True
                elif isinstance(val, (int, float)):
                    effects[key] = effects.get(key, 0) + val
                else:
                    effects[key] = val
    return effects


# --- Wisdom Economy ---

ANCIENT_PLANETS = ["Atlantis", "Heliopolis", "Vis Uban", "Kheb", "Proclarush"]


def get_wisdom_per_turn(state, galaxy):
    """Calculate total wisdom income per turn.

    Sources:
    - +8 per Ancient planet owned
    - Spiritual minor world bonuses (+3/+6 per turn from friend/ally)
    - Ascension doctrine policy 1: +3/turn
    - Ascension doctrine policy 4: double all wisdom income
    """
    wisdom = 0
    # Ancient planets
    for pid, planet in galaxy.planets.items():
        if planet.name in ANCIENT_PLANETS and planet.owner == "player":
            wisdom += 8

    # Spiritual minor worlds
    from .minor_worlds import get_minor_world_bonuses
    mw_bonuses = get_minor_world_bonuses(state, galaxy)
    wisdom += mw_bonuses.get("wisdom_per_turn", 0)

    # Doctrine effects
    effects = get_active_effects(state)
    wisdom += effects.get("wisdom_per_turn", 0)

    # Near-Ascension doubles total
    if effects.get("wisdom_income_doubled"):
        wisdom *= 2

    return wisdom


def apply_wisdom_income(state, galaxy):
    """Apply per-turn wisdom income. Returns amount gained."""
    amount = get_wisdom_per_turn(state, galaxy)
    state.wisdom += amount
    return amount
