"""
STARGWENT - GALACTIC CONQUEST - Wisdom Actions

Repeatable wisdom-powered actions available after completing any doctrine tree.
Solves the late-game dead-resource problem for wisdom.
"""

import random


WISDOM_ACTIONS = {
    "ascended_insight": {
        "name": "Ascended Insight",
        "cost": 15,
        "desc": "+1 power to random card permanently",
        "icon": "\u2605",  # star
    },
    "temporal_shift": {
        "name": "Temporal Shift",
        "cost": 20,
        "desc": "Reset 1 planet cooldown",
        "icon": "\u231B",  # hourglass
    },
    "ancient_knowledge": {
        "name": "Ancient Knowledge",
        "cost": 25,
        "desc": "Reveal full enemy deck next battle",
        "icon": "\u2302",  # house/knowledge
    },
    "enlightened_trade": {
        "name": "Enlightened Trade",
        "cost": 10,
        "desc": "Convert wisdom to +30 naquadah",
        "icon": "\u26A1",  # lightning
    },
}


def get_available_actions(state):
    """Get list of (action_id, action_info, can_afford) tuples.

    Only available when at least one doctrine tree is complete.
    """
    if not state.completed_doctrines:
        return []
    result = []
    for action_id, info in WISDOM_ACTIONS.items():
        can_afford = state.wisdom >= info["cost"]
        result.append((action_id, info, can_afford))
    return result


def can_use_wisdom_action(state, action_id):
    """Check if a wisdom action can be used."""
    if not state.completed_doctrines:
        return False
    info = WISDOM_ACTIONS.get(action_id)
    if not info:
        return False
    return state.wisdom >= info["cost"]


def use_wisdom_action(state, action_id, galaxy, rng=None):
    """Apply a wisdom action. Returns result message or None."""
    if not can_use_wisdom_action(state, action_id):
        return None
    if rng is None:
        rng = random.Random()

    info = WISDOM_ACTIONS[action_id]
    state.wisdom = max(0, state.wisdom - info["cost"])
    state.wisdom_actions_this_turn += 1

    if action_id == "ascended_insight":
        # +1 power to random card
        if state.current_deck:
            card_id = rng.choice(state.current_deck)
            state.upgrade_card(card_id, 1)
            from cards import ALL_CARDS
            card_name = getattr(ALL_CARDS.get(card_id), 'name', card_id)
            return f"Ascended Insight: {card_name} gained +1 power! (-{info['cost']} wisdom)"
        return f"Ascended Insight: No cards to upgrade. (-{info['cost']} wisdom)"

    elif action_id == "temporal_shift":
        # Reset highest cooldown
        if state.cooldowns:
            highest_pid = max(state.cooldowns, key=state.cooldowns.get)
            planet = galaxy.planets.get(highest_pid)
            planet_name = planet.name if planet else highest_pid
            del state.cooldowns[highest_pid]
            return f"Temporal Shift: {planet_name} cooldown reset! (-{info['cost']} wisdom)"
        return f"Temporal Shift: No active cooldowns. (-{info['cost']} wisdom)"

    elif action_id == "ancient_knowledge":
        # Flag for next battle to reveal enemy deck
        state.conquest_ability_data["wisdom_reveal_next_battle"] = True
        return f"Ancient Knowledge: Enemy deck will be revealed next battle! (-{info['cost']} wisdom)"

    elif action_id == "enlightened_trade":
        # Convert to naquadah
        state.add_naquadah(30)
        return f"Enlightened Trade: +30 naquadah! (-{info['cost']} wisdom)"

    return None
