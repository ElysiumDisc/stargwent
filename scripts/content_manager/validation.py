"""Validation helpers for cards, leaders, factions, and abilities."""

import re
from typing import Dict, List, Optional

from .config import VALID_ROWS


def validate_card_id(card_id: str) -> Optional[str]:
    """Validate a card ID."""
    if not card_id:
        return "Card ID cannot be empty"
    if not re.match(r'^[a-z][a-z0-9_]*$', card_id):
        return "Card ID must be lowercase letters, numbers, underscores, starting with letter"

    # Check for duplicates
    try:
        from cards import ALL_CARDS
        if card_id in ALL_CARDS:
            return f"Card ID '{card_id}' already exists"
    except ImportError:
        pass

    return None


def validate_faction_constant(constant: str) -> Optional[str]:
    """Validate a faction constant name."""
    if not constant:
        return "Constant cannot be empty"
    if not re.match(r'^FACTION_[A-Z][A-Z0-9_]*$', constant):
        return "Must be like FACTION_NAME (uppercase)"
    return None


def validate_row(row: str) -> Optional[str]:
    """Validate a row type."""
    if row not in VALID_ROWS:
        return f"Must be one of: {', '.join(VALID_ROWS)}"
    return None


def validate_power(power: int) -> Optional[str]:
    """Validate power value."""
    if not 0 <= power <= 20:
        return "Power must be 0-20"
    return None


def validate_card_name_unique(name: str) -> Optional[str]:
    """Ensure card name isn't already used by another card."""
    try:
        from cards import ALL_CARDS
        for card in ALL_CARDS.values():
            if card.name.lower() == name.lower():
                return f"Card name '{name}' already exists (on card '{card.id}')"
    except Exception:
        pass
    return None


def validate_leader_id_prefix(card_id: str, faction: str) -> Optional[str]:
    """Ensure leader card_id matches faction prefix convention."""
    faction_prefixes = {
        "Tau'ri": "tauri_",
        "Goa'uld": "goauld_",
        "Jaffa Rebellion": "jaffa_",
        "Lucian Alliance": "lucian_",
        "Asgard": "asgard_",
        "Neutral": "neutral_",
    }

    expected_prefix = faction_prefixes.get(faction)
    if expected_prefix and not card_id.startswith(expected_prefix):
        return f"Leader card_id should start with '{expected_prefix}' for {faction} faction"
    return None


def validate_ability_string(ability: str) -> Optional[str]:
    """Check ability string against known abilities in Ability enum."""
    if not ability:
        return None

    try:
        from abilities import Ability
        valid_abilities = {a.value for a in Ability}

        # Split by comma for multi-ability cards
        abilities = [a.strip() for a in ability.split(",")]
        unknown = [a for a in abilities if a not in valid_abilities]

        if unknown:
            return f"Unknown abilities: {', '.join(unknown)}. Consider adding them first."
    except Exception:
        pass
    return None


def validate_faction_complete(faction_data: dict) -> List[str]:
    """Check all required faction components are defined."""
    issues = []

    required_keys = ["name", "constant", "base_leaders", "cards"]
    for key in required_keys:
        if key not in faction_data or not faction_data[key]:
            issues.append(f"Missing required field: {key}")

    if "base_leaders" in faction_data:
        if len(faction_data["base_leaders"]) < 3:
            issues.append(f"Need at least 3 base leaders (have {len(faction_data['base_leaders'])})")

    if "cards" in faction_data:
        if len(faction_data["cards"]) < 15:
            issues.append(f"Need at least 15 starter cards (have {len(faction_data['cards'])})")

    return issues


def validate_batch_card(card: dict, index: int) -> List[str]:
    """Validate a single card entry in batch import."""
    errors = []
    prefix = f"Card[{index}]"

    required_fields = ["card_id", "name", "faction", "power", "row"]
    for field in required_fields:
        if field not in card:
            errors.append(f"{prefix}: missing required field '{field}'")

    if "card_id" in card:
        id_error = validate_card_id(card["card_id"])
        if id_error:
            errors.append(f"{prefix}: {id_error}")

    if "row" in card and card["row"] not in VALID_ROWS:
        errors.append(f"{prefix}: invalid row '{card['row']}' - must be one of {VALID_ROWS}")

    if "power" in card:
        try:
            power = int(card["power"])
            if not 0 <= power <= 20:
                errors.append(f"{prefix}: power must be 0-20")
        except (ValueError, TypeError):
            errors.append(f"{prefix}: power must be a number")

    if card.get("is_unlockable") and "rarity" not in card:
        errors.append(f"{prefix}: unlockable cards require 'rarity' field")

    return errors


def validate_batch_leader(leader: dict, index: int) -> List[str]:
    """Validate a single leader entry in batch import."""
    errors = []
    prefix = f"Leader[{index}]"

    required_fields = ["card_id", "name", "faction", "ability", "ability_desc"]
    for field in required_fields:
        if field not in leader:
            errors.append(f"{prefix}: missing required field '{field}'")

    if "card_id" in leader:
        id_error = validate_card_id(leader["card_id"])
        if id_error:
            errors.append(f"{prefix}: {id_error}")

    if "faction" in leader:
        from .code_parsing import get_existing_factions
        valid_factions = get_existing_factions()[:-1]  # Exclude Neutral
        if leader["faction"] not in valid_factions:
            errors.append(f"{prefix}: invalid faction '{leader['faction']}'")

    return errors


def validate_batch_json(data: dict) -> List[str]:
    """Validate JSON structure and content for batch import."""
    errors = []

    if not isinstance(data, dict):
        errors.append("Root must be a JSON object")
        return errors

    if "cards" in data:
        if not isinstance(data["cards"], list):
            errors.append("'cards' must be an array")
        else:
            for i, card in enumerate(data["cards"]):
                card_errors = validate_batch_card(card, i)
                errors.extend(card_errors)

    if "leaders" in data:
        if not isinstance(data["leaders"], list):
            errors.append("'leaders' must be an array")
        else:
            for i, leader in enumerate(data["leaders"]):
                leader_errors = validate_batch_leader(leader, i)
                errors.extend(leader_errors)

    if "cards" not in data and "leaders" not in data:
        errors.append("JSON must contain 'cards' and/or 'leaders' array")

    return errors
