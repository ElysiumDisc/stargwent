"""User workflow: Custom faction creation wizard."""

import json
from pathlib import Path
from typing import Any, Dict

from ..config import USER_CONTENT_DIR
from ..ui import print_header, get_input, get_int, get_rgb, confirm, select_from_list
from ..code_parsing import get_existing_factions
from ..logging_ import log
from .create_leader import get_leader_ability_types


def get_faction_passive_types() -> Dict[str, Dict[str, Any]]:
    """Get available faction passive types from existing factions."""
    return {
        "EXTRA_DRAW": {
            "example": "Tau'ri Resourcefulness",
            "desc": "Draw extra cards at certain rounds",
            "params": {
                "count": {"type": "int", "min": 1, "max": 2, "default": 1},
                "rounds": {"type": "list", "default": [2, 3]}
            }
        },
        "HERO_POWER_BOOST": {
            "example": "Goa'uld System Lord's Command",
            "desc": "Bonus power when you control a hero",
            "params": {"boost": {"type": "int", "min": 1, "max": 3, "default": 1}}
        },
        "BROTHERHOOD": {
            "example": "Jaffa Brotherhood",
            "desc": "Units gain power per adjacent unit in same row",
            "params": {"max_bonus": {"type": "int", "min": 2, "max": 5, "default": 3}}
        },
        "SPY_DRAW_BONUS": {
            "example": "Lucian Alliance Piracy",
            "desc": "First spy each round draws extra cards",
            "params": {"extra_draw": {"type": "int", "min": 1, "max": 2, "default": 1}}
        },
        "WEATHER_IMMUNITY": {
            "example": "Asgard Superior Shielding",
            "desc": "Immune to first weather effect",
            "params": {"immune_count": {"type": "int", "min": 1, "max": 2, "default": 1}}
        },
    }


def get_faction_power_types() -> Dict[str, Dict[str, Any]]:
    """Get available faction power types from existing factions."""
    return {
        "SCORCH_ROWS": {
            "example": "Tau'ri Gate Shutdown",
            "desc": "Destroy highest unit in each enemy row",
            "params": {}
        },
        "REVIVE_UNITS": {
            "example": "Goa'uld Sarcophagus",
            "desc": "Revive units from discard pile",
            "params": {"count": {"type": "int", "min": 1, "max": 3, "default": 2}}
        },
        "DAMAGE_ALL": {
            "example": "Lucian Unstable Naquadah",
            "desc": "Deal damage to all non-hero units",
            "params": {"damage": {"type": "int", "min": 3, "max": 7, "default": 5}}
        },
        "DRAW_AND_DISCARD": {
            "example": "Jaffa Rebel Alliance Aid",
            "desc": "Draw cards then discard random cards",
            "params": {
                "draw": {"type": "int", "min": 2, "max": 4, "default": 3},
                "discard": {"type": "int", "min": 2, "max": 4, "default": 3}
            }
        },
        "SWAP_ROWS": {
            "example": "Asgard Holographic Decoy",
            "desc": "Swap opponent's close and ranged rows",
            "params": {}
        },
    }


def user_create_faction_wizard():
    """Interactive wizard to create a custom faction (using existing passive/power types)."""
    print_header("CREATE CUSTOM FACTION")
    print("This wizard helps you create a custom faction for Stargwent.")
    print("Faction passives and powers must be based on existing mechanics.")
    print("\nNOTE: Full faction support requires game code changes.")
    print("Created factions will have limited functionality.\n")

    # Ensure user_content directory exists
    factions_dir = USER_CONTENT_DIR / "factions"
    factions_dir.mkdir(parents=True, exist_ok=True)

    # Get faction name
    faction_name = get_input("Faction Name (e.g., Tok'ra)")

    # Check for duplicates
    if (factions_dir / faction_name.lower().replace("'", "").replace(" ", "_")).exists():
        print(f"[ERROR] Faction '{faction_name}' already exists")
        return

    # Generate constant name
    constant = f"FACTION_{faction_name.upper().replace(' ', '_').replace(chr(39), '')}"
    constant = get_input("Faction Constant", default=constant)

    # Visual identity
    print("\n=== VISUAL IDENTITY ===")
    primary_color = get_rgb("Primary Color", default=(100, 150, 200))
    secondary_color = get_rgb("Secondary Color", default=(80, 120, 160))
    glow_color = get_rgb("Glow Color", default=(120, 180, 240))

    # Select faction passive from existing types
    print("\n=== FACTION PASSIVE (from existing) ===")
    passive_types = get_faction_passive_types()
    passive_names = list(passive_types.keys())

    for i, (name, info) in enumerate(passive_types.items(), 1):
        print(f"  {i}. {info['desc']} - like {info['example']}")

    passive_choice = get_int("Select passive type", min_val=1, max_val=len(passive_names)) - 1
    passive_type = passive_names[passive_choice]
    passive_info = passive_types[passive_type]

    passive_name = get_input("Passive Name", default=f"{faction_name} {passive_info['desc'].split()[0]}")
    passive_desc = get_input("Passive Description", default=passive_info['desc'])

    # Configure passive parameters
    passive_params = {}
    for param_name, param_config in passive_info.get("params", {}).items():
        if param_config["type"] == "int":
            value = get_int(
                f"  {param_name}",
                min_val=param_config.get("min", 1),
                max_val=param_config.get("max", 5),
                default=param_config.get("default", 1)
            )
            passive_params[param_name] = value
        elif param_config["type"] == "list":
            passive_params[param_name] = param_config.get("default", [])

    # Select faction power from existing types
    print("\n=== FACTION POWER (from existing) ===")
    power_types = get_faction_power_types()
    power_names = list(power_types.keys())

    for i, (name, info) in enumerate(power_types.items(), 1):
        print(f"  {i}. {info['desc']} - like {info['example']}")

    power_choice = get_int("Select power type", min_val=1, max_val=len(power_names)) - 1
    power_type = power_names[power_choice]
    power_info = power_types[power_type]

    power_name = get_input("Power Name", default=f"{faction_name} {power_info['desc'].split()[0]}")
    power_desc = get_input("Power Description", default=power_info['desc'])

    # Configure power parameters
    power_params = {}
    for param_name, param_config in power_info.get("params", {}).items():
        if param_config["type"] == "int":
            value = get_int(
                f"  {param_name}",
                min_val=param_config.get("min", 1),
                max_val=param_config.get("max", 10),
                default=param_config.get("default", 2)
            )
            power_params[param_name] = value

    # Author
    author = get_input("Author", default="Unknown")

    # Preview
    print("\n" + "=" * 50)
    print("=== PREVIEW ===")
    print("=" * 50)
    print(f"  Faction: {faction_name} ({constant})")
    print(f"  Colors: {primary_color} / {secondary_color} / {glow_color}")
    print(f"  Passive: {passive_name} - {passive_type}")
    print(f"  Power: {power_name} - {power_type}")
    print("=" * 50)

    if not confirm("\nCreate this faction?"):
        print("Cancelled.")
        return

    # Create faction directory
    faction_dir_name = faction_name.lower().replace("'", "").replace(" ", "_")
    faction_dir = factions_dir / faction_dir_name
    faction_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (faction_dir / "cards").mkdir(exist_ok=True)
    (faction_dir / "leaders").mkdir(exist_ok=True)

    faction_data = {
        "name": faction_name,
        "constant": constant,
        "primary_color": list(primary_color),
        "secondary_color": list(secondary_color),
        "glow_color": list(glow_color),
        "passive_name": passive_name,
        "passive_type": passive_type,
        "passive_params": passive_params,
        "passive_desc": passive_desc,
        "power_name": power_name,
        "power_type": power_type,
        "power_params": power_params,
        "power_desc": power_desc,
        "author": author
    }

    # Save faction.json
    faction_json = faction_dir / "faction.json"
    faction_json.write_text(json.dumps(faction_data, indent=2))
    log(f"Created user faction: {faction_name}")

    print(f"\n[OK] Faction created in {faction_dir}/")
    print("\nNext steps:")
    print(f"  1. Add cards in {faction_dir}/cards/")
    print(f"  2. Add leaders in {faction_dir}/leaders/")
    print("  3. A minimum of 15 cards and 3 leaders recommended")

    # Offer to create starter content
    if confirm("Create starter leaders now?", default=True):
        ability_types = get_leader_ability_types()
        type_names = list(ability_types.keys())

        for i in range(3):
            print(f"\n--- Creating Base Leader {i+1}/3 ---")
            # Simplified leader creation for faction
            lid = get_input(f"Leader {i+1} ID (e.g., {faction_dir_name}_leader{i+1})")
            if not lid.startswith("user_"):
                lid = f"user_{lid}"
            lname = get_input(f"Leader {i+1} Name")

            # Quick ability type selection
            print("Ability types: " + ", ".join(f"{j+1}={n}" for j, n in enumerate(type_names[:5])))
            type_idx = get_int("Ability type (1-5)", min_val=1, max_val=5, default=1) - 1
            ability_type = type_names[type_idx]

            leader_data = {
                "card_id": lid,
                "name": lname,
                "faction": faction_name,
                "ability": f"{lname}'s Ability",
                "ability_desc": ability_types[ability_type]["desc"],
                "ability_type": ability_type,
                "ability_params": {},
                "is_base": True,
                "author": author
            }

            leader_subdir = faction_dir / "leaders" / lid.replace("user_", "")
            leader_subdir.mkdir(parents=True, exist_ok=True)
            (leader_subdir / "leader.json").write_text(json.dumps(leader_data, indent=2))
            print(f"[OK] Created leader: {lid}")

    # Auto-enable
    try:
        from user_content_loader import get_loader
        loader = get_loader()
        loader.enable_content("faction", faction_name)
        print(f"\n[OK] Faction enabled - will be available next game start")
    except (ImportError, AttributeError):
        print("\n[INFO] Faction created. Enable it in 'Manage User Content' menu.")
