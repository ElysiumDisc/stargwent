"""
STARGWENT - GALACTIC CONQUEST - Doctrine Trees

New resource "Wisdom" funds policy trees that force strategic identity per run.
5 trees, 4 tiers of policies each + completion bonus. At tier 3, each tree
offers THREE mutually-exclusive options: the original "spine" policy and
two new specialized branches introduced in v11.0. Players pick ONE tier-3
option and the capstone (tier 4) unlocks after any of them.

Save-compat note (v11.0): existing save files with the old linear tier-3
policy IDs (`con_3`, `asc_3`, …) still load unchanged — those IDs are
still present as the "balanced" option. New branches (`con_3a`, `con_3b`,
…) are ADDITIVE and only reachable in new runs.

Each policy dict supports:
    id, name, base_cost, effect, penalty, desc, tier        (all existing)
    requires: [policy_id, ...]   — at least one must be adopted (OR)
    conflicts_with: [policy_id, ...] — none may be adopted
    capstone: True               — adopting this completes the tree
"""


# --- Doctrine Tree Definitions ---

DOCTRINE_TREES = {
    "ascension": {
        "name": "Path of Ascension",
        "color": (200, 180, 255),
        "icon": "\u2605",  # star
        "policies": [
            {"id": "asc_1", "name": "Ancient Meditation", "base_cost": 10,
             "tier": 1,
             "effect": {"wisdom_per_turn": 3},
             "penalty": {"naquadah_per_turn_penalty": 5},
             "desc": "+3 Wisdom/turn | -5 naq/turn"},
            {"id": "asc_2", "name": "Repository Access", "base_cost": 20,
             "tier": 2, "requires": ["asc_1"],
             "effect": {"extra_card_choices": 1},
             "penalty": {},
             "desc": "+1 reward card choice"},
            # --- Tier 3: pick one ---
            {"id": "asc_3", "name": "Enlightened Warfare", "base_cost": 30,
             "tier": 3, "requires": ["asc_2"],
             "conflicts_with": ["asc_3a", "asc_3b"],
             "effect": {"battle_power_bonus": 1},
             "penalty": {"counterattack_chance_increase": 0.05},
             "desc": "+1 power to all cards | +5% counterattack"},
            {"id": "asc_3a", "name": "Inner Peace", "base_cost": 30,
             "tier": 3, "requires": ["asc_2"],
             "conflicts_with": ["asc_3", "asc_3b"],
             "effect": {"global_counter_reduction": 0.05},
             "penalty": {"battle_power_penalty": 1},
             "desc": "-5% all counterattacks | -1 card power"},
            {"id": "asc_3b", "name": "Ascended Fury", "base_cost": 30,
             "tier": 3, "requires": ["asc_2"],
             "conflicts_with": ["asc_3", "asc_3a"],
             "effect": {"battle_power_bonus": 2},
             "penalty": {"counterattack_chance_increase": 0.10},
             "desc": "+2 power to all cards | +10% counterattack"},
            {"id": "asc_4", "name": "Near-Ascension", "base_cost": 40,
             "tier": 4, "capstone": True,
             "requires": ["asc_3", "asc_3a", "asc_3b"],
             "effect": {"wisdom_income_doubled": True},
             "penalty": {"naquadah_per_turn_penalty": 10},
             "desc": "Wisdom income doubled | -10 naq/turn"},
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
             "tier": 1,
             "effect": {"attack_cooldown_reduction": 1},
             "penalty": {"defense_power_penalty": 1},
             "desc": "-1 turn cooldown | -1 defense power"},
            {"id": "con_2", "name": "Veteran Troops", "base_cost": 20,
             "tier": 2, "requires": ["con_1"],
             "effect": {"attack_power_bonus": 1},
             "penalty": {},
             "desc": "+1 power when attacking"},
            # --- Tier 3: pick one ---
            {"id": "con_3", "name": "War Logistics", "base_cost": 30,
             "tier": 3, "requires": ["con_2"],
             "conflicts_with": ["con_3a", "con_3b"],
             "effect": {"extra_attacks_per_turn": 1},
             "penalty": {"alliance_upkeep_increase": 5},
             "desc": "+1 attack per turn | +5 upkeep"},
            {"id": "con_3a", "name": "Scorched Earth", "base_cost": 30,
             "tier": 3, "requires": ["con_2"],
             "conflicts_with": ["con_3", "con_3b"],
             "effect": {"attack_cooldown_reduction": 1},
             "penalty": {"conquest_naq_penalty": 10},
             "desc": "-1 additional cooldown | -10 naq per conquest"},
            {"id": "con_3b", "name": "Siege Engineers", "base_cost": 30,
             "tier": 3, "requires": ["con_2"],
             "conflicts_with": ["con_3", "con_3a"],
             "effect": {"homeworld_attack_bonus": 2},
             "penalty": {"defense_power_penalty": 1},
             "desc": "+2 power vs homeworlds | -1 defense"},
            {"id": "con_4", "name": "Total Supremacy", "base_cost": 40,
             "tier": 4, "capstone": True,
             "requires": ["con_3", "con_3a", "con_3b"],
             "effect": {"conquest_naq_bonus": 30},
             "penalty": {"trade_income_penalty": 5},
             "desc": "+30 naq per conquest | -5 trade income"},
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
             "tier": 1,
             "effect": {"minor_world_influence_per_turn": 5},
             "penalty": {"counterattack_chance_increase": 0.05},
             "desc": "+5 influence/turn | +5% counterattack"},
            {"id": "all_2", "name": "Free Trade Zone", "base_cost": 20,
             "tier": 2, "requires": ["all_1"],
             "effect": {"trade_cost_discount": 20},
             "penalty": {},
             "desc": "Trade agreements cost -20 naq"},
            # --- Tier 3: pick one ---
            {"id": "all_3", "name": "Deep Alliance", "base_cost": 30,
             "tier": 3, "requires": ["all_2"],
             "conflicts_with": ["all_3a", "all_3b"],
             "effect": {"alliance_upkeep_reduction": 5},
             "penalty": {},
             "desc": "Alliance upkeep -5/turn"},
            {"id": "all_3a", "name": "Trade Federation", "base_cost": 30,
             "tier": 3, "requires": ["all_2"],
             "conflicts_with": ["all_3", "all_3b"],
             "effect": {"trading_naq_bonus": 5},
             "penalty": {"alliance_upkeep_increase": 5},
             "desc": "+5 naq/turn per trade | +5 upkeep"},
            {"id": "all_3b", "name": "Brotherhood", "base_cost": 30,
             "tier": 3, "requires": ["all_2"],
             "conflicts_with": ["all_3", "all_3a"],
             "effect": {"allied_passive_boost": True},
             "penalty": {"trade_income_penalty": 3},
             "desc": "Allied sharing 75% (was 50%) | -3 trade"},
            {"id": "all_4", "name": "Galactic Federation", "base_cost": 40,
             "tier": 4, "capstone": True,
             "requires": ["all_3", "all_3a", "all_3b"],
             "effect": {"passive_sharing_boost": True},
             "penalty": {"conquest_naq_penalty": 15},
             "desc": "Allied sharing 75% | -15 naq per conquest"},
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
             "tier": 1,
             "effect": {"operative_death_risk_reduction": 0.10},
             "penalty": {},
             "desc": "Operative death risk -10%"},
            {"id": "shd_2", "name": "Intelligence Networks", "base_cost": 20,
             "tier": 2, "requires": ["shd_1"],
             "effect": {"mission_time_reduction": 1},
             "penalty": {"incident_chance_increase": 0.05},
             "desc": "Mission times -1 turn | +5% incidents"},
            # --- Tier 3: pick one ---
            {"id": "shd_3", "name": "Advanced Sabotage", "base_cost": 30,
             "tier": 3, "requires": ["shd_2"],
             "conflicts_with": ["shd_3a", "shd_3b"],
             "effect": {"sabotage_extra_cards": 1},
             "penalty": {},
             "desc": "Sabotage removes 2 cards (was 1)"},
            {"id": "shd_3a", "name": "Assassins Guild", "base_cost": 30,
             "tier": 3, "requires": ["shd_2"],
             "conflicts_with": ["shd_3", "shd_3b"],
             "effect": {"mission_time_reduction": 1},
             "penalty": {"operative_death_risk_increase": 0.15},
             "desc": "-1 mission time | +15% death risk"},
            {"id": "shd_3b", "name": "Intelligence Web", "base_cost": 30,
             "tier": 3, "requires": ["shd_2"],
             "conflicts_with": ["shd_3", "shd_3a"],
             "effect": {"counter_intel_double": True},
             "penalty": {"naquadah_per_turn_penalty": 5},
             "desc": "Counter-Intel blocks 2 ops | -5 naq/turn"},
            {"id": "shd_4", "name": "Shadow Government", "base_cost": 40,
             "tier": 4, "capstone": True,
             "requires": ["shd_3", "shd_3a", "shd_3b"],
             "effect": {"free_operative_interval": 8},
             "penalty": {"naquadah_per_turn_penalty": 8},
             "desc": "Free operative every 8 turns | -8 naq/turn"},
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
             "tier": 1,
             "effect": {"building_naq_bonus": 10},
             "penalty": {},
             "desc": "+10 naq/turn from buildings"},
            {"id": "inn_2", "name": "Advanced Engineering", "base_cost": 20,
             "tier": 2, "requires": ["inn_1"],
             "effect": {"building_cost_reduction": 25},
             "penalty": {"wisdom_per_turn_penalty": 2},
             "desc": "Buildings -25 naq | -2 Wisdom/turn"},
            # --- Tier 3: pick one ---
            {"id": "inn_3", "name": "Network Optimization", "base_cost": 30,
             "tier": 3, "requires": ["inn_2"],
             "conflicts_with": ["inn_3a", "inn_3b"],
             "effect": {"network_tier_reduction": 1},
             "penalty": {},
             "desc": "Network tier thresholds -1 planet"},
            {"id": "inn_3a", "name": "Rapid Prototype", "base_cost": 30,
             "tier": 3, "requires": ["inn_2"],
             "conflicts_with": ["inn_3", "inn_3b"],
             "effect": {"upgrade_cost_reduction": 50},
             "penalty": {"wisdom_per_turn_penalty": 2},
             "desc": "Building upgrades -50 naq | -2 Wisdom/turn"},
            {"id": "inn_3b", "name": "Quantum Computing", "base_cost": 30,
             "tier": 3, "requires": ["inn_2"],
             "conflicts_with": ["inn_3", "inn_3a"],
             "effect": {"wisdom_per_turn": 5},
             "penalty": {"building_cost_penalty": 20},
             "desc": "+5 Wisdom/turn | +20 building cost"},
            {"id": "inn_4", "name": "Supergate Project", "base_cost": 40,
             "tier": 4, "capstone": True,
             "requires": ["inn_3", "inn_3a", "inn_3b"],
             "effect": {"enable_supergate": True},
             "penalty": {"counterattack_chance_increase": 0.08},
             "desc": "Enables Supergate | +8% counterattack"},
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
    """Check if a policy can be adopted.

    Rules:
    - Not already adopted.
    - Every id listed in `requires` must have at least one entry in
      state.adopted_policies (OR semantics — capstones can list all
      three tier-3 siblings).
    - No id listed in `conflicts_with` may be adopted already (mutual
      exclusion for tier-3 branches).
    - Player has enough wisdom for the escalating cost.
    """
    if policy_id in state.adopted_policies:
        return False
    tree_id, idx = _POLICY_LOOKUP.get(policy_id, (None, None))
    if tree_id is None:
        return False
    policy = DOCTRINE_TREES[tree_id]["policies"][idx]

    # G2b: espionage block from enemy "steal_doctrine" mission
    blocked = getattr(state, "espionage_blocks", {}).get("doctrine_blocked_turns", 0)
    if blocked > 0:
        return False

    # Prerequisites (OR semantics): at least one required policy must be adopted.
    requires = policy.get("requires", [])
    if requires and not any(r in state.adopted_policies for r in requires):
        return False

    # Conflicts: none of the listed policies may be adopted already.
    for conflict_id in policy.get("conflicts_with", []):
        if conflict_id in state.adopted_policies:
            return False

    cost = get_policy_cost(policy_id, state)
    return state.wisdom >= cost


def _is_tree_complete_by_capstone(state, tree_id):
    """Tree is complete when the capstone policy (flagged `capstone: True`) is adopted."""
    tree = DOCTRINE_TREES.get(tree_id)
    if not tree:
        return False
    for policy in tree["policies"]:
        if policy.get("capstone") and policy["id"] in state.adopted_policies:
            return True
    return False


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

    # Tree completion now keys off the capstone flag rather than "all
    # policies adopted" — branches are mutually exclusive so no run can
    # ever own every policy in a tree.
    if policy.get("capstone") and tree_id not in state.completed_doctrines:
        state.completed_doctrines.append(tree_id)
        bonus_name = tree["completion_bonus"]["name"]
        return f"Adopted {policy['name']}! (-{cost} Wisdom) TREE COMPLETE: {bonus_name}!"

    return f"Adopted {policy['name']}! (-{cost} Wisdom)"


def is_tree_complete(state, tree_id):
    """Check if a tree's capstone has been adopted."""
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
    Penalties are included with their own keys (e.g. defense_power_penalty).
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
        # Aggregate penalties alongside effects
        for key, val in policy.get("penalty", {}).items():
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
