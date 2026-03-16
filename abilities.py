"""
Ability system for Stargwent.

This module provides type-safe ability checking while maintaining backward
compatibility with string-based card definitions.

Usage:
    from abilities import Ability, has_ability

    # Check if a card has an ability
    if has_ability(card, Ability.LEGENDARY_COMMANDER):
        # card is a hero

    # Check multiple abilities
    if has_ability(card, Ability.TACTICAL_FORMATION, Ability.GATE_REINFORCEMENT):
        # card has at least one of these abilities
"""

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cards import Card


class Ability(Enum):
    """All card abilities in Stargwent."""

    # Unit Type Abilities
    LEGENDARY_COMMANDER = "Legendary Commander"

    # Synergy Abilities
    TACTICAL_FORMATION = "Tactical Formation"
    GATE_REINFORCEMENT = "Gate Reinforcement"
    INSPIRING_LEADERSHIP = "Inspiring Leadership"

    # Agent Abilities
    DEEP_COVER_AGENT = "Deep Cover Agent"
    MEDICAL_EVAC = "Medical Evac"

    # Combat Abilities
    LIFE_FORCE_DRAIN = "Life Force Drain"
    SYSTEM_LORDS_CURSE = "System Lord's Curse"
    SURVIVAL_INSTINCT = "Survival Instinct"
    NAQUADAH_OVERLOAD = "Naquadah Overload"

    # Special Card Abilities
    COMMAND_NETWORK = "Command Network"
    RING_TRANSPORT = "Ring Transport"
    DEPLOY_CLONES = "Deploy Clones"
    ACTIVATE_COMBAT_PROTOCOL = "Activate Combat Protocol"
    GENETIC_ENHANCEMENT = "Genetic Enhancement"
    GRANT_ZPM = "Grant ZPM"

    # Weather Abilities
    ICE_PLANET_HAZARD = "Ice Planet Hazard"
    NEBULA_INTERFERENCE = "Nebula Interference"
    ASTEROID_STORM = "Asteroid Storm"
    WORMHOLE_STABILIZATION = "Wormhole Stabilization"
    ELECTROMAGNETIC_PULSE = "Electromagnetic Pulse"

    # Rare/Special Abilities (from unlockable cards)
    VAMPIRE = "Vampire"
    CRONE = "Crone"

    # Alteran Faction Abilities
    PRIORS_PLAGUE = "Prior's Plague"
    ASCENSION = "Ascension"


def has_ability(card: "Card", *abilities: Ability) -> bool:
    """
    Check if a card has any of the specified abilities.

    This function provides type-safe ability checking while working with
    the existing string-based card.ability field.

    Args:
        card: The card to check
        *abilities: One or more Ability enum values to check for

    Returns:
        True if the card has at least one of the specified abilities

    Example:
        if has_ability(card, Ability.LEGENDARY_COMMANDER):
            # Handle hero card

        if has_ability(card, Ability.TACTICAL_FORMATION, Ability.GATE_REINFORCEMENT):
            # Handle synergy card
    """
    if not card or not card.ability:
        return False

    ability_str = card.ability
    for ability in abilities:
        if ability.value in ability_str:
            return True
    return False


def get_abilities(card: "Card") -> list[Ability]:
    """
    Get all abilities a card has as a list of Ability enums.

    Args:
        card: The card to get abilities from

    Returns:
        List of Ability enum values the card has
    """
    if not card or not card.ability:
        return []

    result = []
    ability_str = card.ability
    for ability in Ability:
        if ability.value in ability_str:
            result.append(ability)
    return result


def is_hero(card: "Card") -> bool:
    """Check if a card is a hero (Legendary Commander)."""
    return has_ability(card, Ability.LEGENDARY_COMMANDER)


def is_spy(card: "Card") -> bool:
    """Check if a card is a spy (Deep Cover Agent)."""
    return has_ability(card, Ability.DEEP_COVER_AGENT)


def is_medic(card: "Card") -> bool:
    """Check if a card has Medical Evac ability."""
    return has_ability(card, Ability.MEDICAL_EVAC)


def is_weather_card(card: "Card") -> bool:
    """Check if a card is a weather card."""
    return has_ability(
        card,
        Ability.ICE_PLANET_HAZARD,
        Ability.NEBULA_INTERFERENCE,
        Ability.ASTEROID_STORM,
        Ability.WORMHOLE_STABILIZATION,
        Ability.ELECTROMAGNETIC_PULSE
    )


def is_special_card(card: "Card") -> bool:
    """Check if a card is a special (non-unit) card."""
    return has_ability(
        card,
        Ability.COMMAND_NETWORK,
        Ability.RING_TRANSPORT,
        Ability.NAQUADAH_OVERLOAD
    ) or (card and card.row == "special")


def has_synergy(card: "Card") -> bool:
    """Check if a card has any synergy ability (Tactical Formation or Gate Reinforcement)."""
    return has_ability(card, Ability.TACTICAL_FORMATION, Ability.GATE_REINFORCEMENT)


def is_plague_card(card: "Card") -> bool:
    """Check if a card has Prior's Plague ability."""
    return has_ability(card, Ability.PRIORS_PLAGUE)


def is_ascension_card(card: "Card") -> bool:
    """Check if a card has Ascension ability."""
    return has_ability(card, Ability.ASCENSION)


def can_be_targeted(card: "Card") -> bool:
    """
    Check if a card can be targeted by effects like weather, scorch, etc.
    Heroes (Legendary Commanders) are typically immune to targeting.
    """
    if not card:
        return False
    if is_hero(card):
        return False
    if card.row in ["special", "weather"]:
        return False
    return True
