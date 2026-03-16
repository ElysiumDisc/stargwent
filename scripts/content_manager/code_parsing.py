"""Code parsing helpers - extract information from game source files."""

import re
from typing import Any, Dict, List

from .config import FILES


def get_existing_factions() -> List[str]:
    """Get list of existing faction names."""
    try:
        from cards import (
            FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
            FACTION_LUCIAN, FACTION_ASGARD, FACTION_ALTERAN, FACTION_NEUTRAL
        )
        return [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
                FACTION_LUCIAN, FACTION_ASGARD, FACTION_ALTERAN, FACTION_NEUTRAL]
    except ImportError:
        return ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard", "Alteran", "Neutral"]


def get_existing_faction_constants() -> Dict[str, str]:
    """Get mapping of faction constant names to values."""
    content = FILES["cards"].read_text()

    constants = {}
    pattern = r'^(FACTION_\w+)\s*=\s*["\']([^"\']+)["\']'
    for match in re.finditer(pattern, content, re.MULTILINE):
        constants[match.group(1)] = match.group(2)

    return constants


def get_existing_abilities() -> List[str]:
    """Get list of existing ability names from Ability enum."""
    try:
        from abilities import Ability
        return [a.value for a in Ability]
    except ImportError:
        return []


def get_all_cards() -> Dict[str, Any]:
    """Get all cards from cards.py."""
    try:
        from cards import ALL_CARDS
        return ALL_CARDS
    except ImportError:
        return {}
