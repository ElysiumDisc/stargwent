"""Format helpers - generate code strings matching existing file formats."""

from typing import Optional


def format_card_entry(card_id: str, name: str, faction_const: str,
                      power: int, row: str, ability: Optional[str]) -> str:
    """
    Format card entry matching cards.py style (4-space indent, single line).

    Example output:
        "tauri_scientist": Card("tauri_scientist", "SGC Scientist", FACTION_TAURI, 3, "ranged", None),
    """
    ability_str = f'"{ability}"' if ability else "None"
    return f'    "{card_id}": Card("{card_id}", "{name}", {faction_const}, {power}, "{row}", {ability_str}),'


def format_unlockable_entry(card_id: str, name: str, faction: str, row: str,
                            power: int, ability: Optional[str], description: str, rarity: str) -> str:
    """
    Format unlockable entry matching unlocks.py style (4+8 space indent, multiline).
    """
    ability_str = ability if ability else ""
    return f'''    "{card_id}": {{
        "name": "{name}",
        "faction": "{faction}",
        "row": "{row}",
        "power": {power},
        "ability": "{ability_str}",
        "description": "{description or ''}",
        "rarity": "{rarity}"
    }},'''


def format_leader_entry(name: str, ability: str, ability_desc: str, card_id: str,
                        image_path: Optional[str] = None) -> str:
    """
    Format leader entry matching content_registry.py style.
    """
    if image_path:
        return f'{{"name": "{name}", "ability": "{ability}", "ability_desc": "{ability_desc}", "card_id": "{card_id}", "image_path": "{image_path}"}}'
    return f'{{"name": "{name}", "ability": "{ability}", "ability_desc": "{ability_desc}", "card_id": "{card_id}"}}'
