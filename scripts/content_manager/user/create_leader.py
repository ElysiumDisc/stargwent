"""User workflow: Custom leader creation wizard."""

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import ROOT, USER_CONTENT_DIR
from ..ui import print_header, get_input, get_int, confirm, select_from_list
from ..code_parsing import get_existing_factions
from ..logging_ import log


def get_leader_ability_types() -> Dict[str, Dict[str, Any]]:
    """
    Get available leader ability types derived from existing leaders.

    Returns dict mapping ability type to example and parameters.
    """
    return {
        "DRAW_ON_PASS": {
            "example": "Dr. McKay",
            "desc": "Draw cards when you pass",
            "params": {"draw_count": {"type": "int", "min": 1, "max": 3, "default": 2}}
        },
        "DRAW_ON_ROUND_START": {
            "example": "Col. O'Neill",
            "desc": "Draw extra cards at round start",
            "params": {"draw_count": {"type": "int", "min": 1, "max": 2, "default": 1}}
        },
        "FIRST_UNIT_BOOST": {
            "example": "Gen. Hammond",
            "desc": "First unit played each round gets power boost",
            "params": {"boost": {"type": "int", "min": 1, "max": 5, "default": 3}}
        },
        "ROW_POWER_BOOST": {
            "example": "Dr. Carter (Siege), Bra'tac (Agile)",
            "desc": "All units in specific row get power boost",
            "params": {
                "row": {"type": "choice", "options": ["close", "ranged", "siege", "agile"]},
                "boost": {"type": "int", "min": 1, "max": 3, "default": 2}
            }
        },
        "UNIT_TYPE_BOOST": {
            "example": "Heimdall (heroes)",
            "desc": "Specific unit types get power boost",
            "params": {
                "unit_type": {"type": "choice", "options": ["heroes", "spies", "medics"]},
                "boost": {"type": "int", "min": 1, "max": 5, "default": 3}
            }
        },
        "SPY_DRAW_BONUS": {
            "example": "Vulkar",
            "desc": "Spy cards draw extra cards",
            "params": {"extra_draw": {"type": "int", "min": 1, "max": 2, "default": 1}}
        },
        "HIGHEST_UNIT_BOOST": {
            "example": "Sodan Master",
            "desc": "Highest unit in each row gets boost",
            "params": {"boost": {"type": "int", "min": 1, "max": 5, "default": 3}}
        },
        "WEATHER_IMMUNITY": {
            "example": "Freyr",
            "desc": "Immune to weather effects",
            "params": {}
        },
        "CLONE_STRONGEST": {
            "example": "Ba'al",
            "desc": "Copy highest power unit from discard",
            "params": {}
        },
        "PEEK_OPPONENT": {
            "example": "Lord Yu",
            "desc": "See opponent's hand when passing",
            "params": {}
        },
        "PEEK_DECK": {
            "example": "Catherine Langford",
            "desc": "Look at top cards of deck, play one",
            "params": {"peek_count": {"type": "int", "min": 2, "max": 5, "default": 3}}
        },
        "STEAL_LOWEST": {
            "example": "Hathor",
            "desc": "Steal lowest power enemy unit",
            "params": {}
        },
        "AUTO_SCORCH": {
            "example": "Anubis",
            "desc": "Automatically scorch at certain rounds",
            "params": {"rounds": {"type": "list", "default": [2, 3]}}
        },
        "ROUND_POWER_BONUS": {
            "example": "Cronus",
            "desc": "Units gain power based on round number",
            "params": {"per_round": {"type": "int", "min": 1, "max": 2, "default": 1}}
        },
        "WIN_ROUND_DRAW": {
            "example": "Teal'c",
            "desc": "Draw card when winning a round",
            "params": {"draw_count": {"type": "int", "min": 1, "max": 2, "default": 1}}
        },
        "DOUBLE_PLAY_FIRST_TURN": {
            "example": "Rak'nor",
            "desc": "Play 2 cards on first turn each round",
            "params": {}
        },
    }


def user_create_leader_wizard():
    """Interactive wizard to create a custom leader (using existing ability types)."""
    print_header("CREATE CUSTOM LEADER")
    print("This wizard helps you create a custom leader for Stargwent.")
    print("All abilities must be based on existing leader mechanics.\n")

    # Ensure user_content directory exists
    leaders_dir = USER_CONTENT_DIR / "leaders"
    leaders_dir.mkdir(parents=True, exist_ok=True)

    # Get leader ID
    def validate_user_leader_id(leader_id: str) -> Optional[str]:
        if not leader_id:
            return "Leader ID cannot be empty"
        if not re.match(r'^[a-z][a-z0-9_]*$', leader_id):
            return "Leader ID must be lowercase letters, numbers, underscores"
        if (leaders_dir / leader_id).exists():
            return f"User leader '{leader_id}' already exists"
        return None

    leader_id = get_input("Leader ID (e.g., jacob_carter)", validator=validate_user_leader_id)
    if not leader_id.startswith("user_"):
        leader_id = f"user_{leader_id}"

    leader_name = get_input("Leader Name (e.g., Jacob Carter/Selmak)")

    # Select faction
    factions = get_existing_factions()[:-1]  # Exclude Neutral
    faction = select_from_list("Select Faction:", factions)

    # Select ability type from existing leader mechanics
    ability_types = get_leader_ability_types()
    type_names = list(ability_types.keys())
    type_descriptions = [f"{k} - {v['desc']} (like {v['example']})" for k, v in ability_types.items()]

    print("\nSelect Leader Ability Type (from existing leaders):")
    for i, desc in enumerate(type_descriptions, 1):
        print(f"  {i:2}. {desc}")

    type_choice = get_int("Choice", min_val=1, max_val=len(type_names)) - 1
    ability_type = type_names[type_choice]
    ability_info = ability_types[ability_type]

    # Configure ability parameters
    ability_params = {}
    if ability_info["params"]:
        print("\nConfigure ability values (within bounds):")
        for param_name, param_config in ability_info["params"].items():
            if param_config["type"] == "int":
                value = get_int(
                    f"  {param_name}",
                    min_val=param_config.get("min", 1),
                    max_val=param_config.get("max", 10),
                    default=param_config.get("default", 1)
                )
                ability_params[param_name] = value
            elif param_config["type"] == "choice":
                value = select_from_list(f"  {param_name}:", param_config["options"])
                ability_params[param_name] = value
            elif param_config["type"] == "list":
                ability_params[param_name] = param_config.get("default", [])

    # Generate ability name and description based on type
    ability_name = get_input("Ability Name (short)", default=ability_info["desc"].split()[0].title() + " Ability")
    ability_desc = get_input("Ability Description (full)", default=ability_info["desc"])

    # Is base or unlockable?
    is_base = confirm("Is this a BASE leader (available from start)?", default=True)

    # Banner name (short display name)
    banner_name = get_input("Banner Name (short display)", default=leader_name.split()[0])

    # Author
    author = get_input("Author", default="Unknown")

    # Preview
    print("\n" + "=" * 50)
    print("=== PREVIEW ===")
    print("=" * 50)
    print(f"  Leader: {leader_name}")
    print(f"  ID: {leader_id}")
    print(f"  Faction: {faction}")
    print(f"  Ability: {ability_name}")
    print(f"  Description: {ability_desc}")
    print(f"  Type: {ability_type} (uses existing {ability_info['example']} mechanic)")
    if ability_params:
        print(f"  Parameters: {ability_params}")
    print(f"  Status: {'Base' if is_base else 'Unlockable'}")
    print("=" * 50)

    if not confirm("\nCreate this leader?"):
        print("Cancelled.")
        return

    # Create leader directory and files
    leader_dir = leaders_dir / leader_id.replace("user_", "")
    leader_dir.mkdir(parents=True, exist_ok=True)

    leader_data = {
        "card_id": leader_id,
        "name": leader_name,
        "faction": faction,
        "ability": ability_name,
        "ability_desc": ability_desc,
        "ability_type": ability_type,
        "ability_params": ability_params,
        "is_base": is_base,
        "banner_name": banner_name,
        "author": author
    }

    # Save leader.json
    leader_json = leader_dir / "leader.json"
    leader_json.write_text(json.dumps(leader_data, indent=2))
    log(f"Created user leader: {leader_id}")

    print(f"\n[OK] Leader created in {leader_dir}/")

    # Offer to generate placeholder
    if confirm("Generate placeholder portrait?", default=True):
        try:
            from ..dev.placeholders import generate_leader_placeholders
            generate_leader_placeholders(leader_id, leader_name, faction, force=True)
            # Copy to user content dir
            src = ROOT / "assets" / f"{leader_id}_leader.png"
            dst = leader_dir / "portrait.png"
            if src.exists():
                shutil.copy2(src, dst)
                print(f"[OK] Portrait saved to {dst}")
        except ImportError:
            print("[INFO] Placeholder generation not available")

    # Auto-enable
    try:
        from user_content_loader import get_loader
        loader = get_loader()
        loader.enable_content("leader", leader_id)
        print("[OK] Leader enabled - will be available next game start")
    except (ImportError, AttributeError):
        print("[INFO] Leader created. Enable it in 'Manage User Content' menu.")
