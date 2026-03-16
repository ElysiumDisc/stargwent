"""Developer workflow: Batch import from JSON."""

import json
from pathlib import Path
from typing import List, Tuple

from ..config import ROOT, FILES
from ..ui import print_header, get_input, confirm, progress_bar
from ..validation import validate_batch_json
from ..formatting import format_card_entry, format_unlockable_entry, format_leader_entry
from ..code_insertion import insert_card_entry_safely, insert_unlockable_entry_safely, insert_leader_entry_safely
from ..code_parsing import get_existing_faction_constants
from ..safety import safe_modify_file, safe_modify_json
from ..logging_ import log
from .placeholders import generate_card_placeholder, generate_leader_placeholders

import re


def batch_import_workflow():
    """Import multiple cards/leaders from JSON file."""
    print_header("BATCH IMPORT FROM JSON")

    print("This feature allows you to import multiple cards and/or leaders")
    print("from a single JSON file.\n")

    print("  1. Import from JSON file")
    print("  2. Export JSON template")
    print("  3. View example JSON format")
    print("  0. Back")
    print()

    choice = get_input("Choice", default="0")

    if choice == "1":
        import_from_json_file()
    elif choice == "2":
        export_json_template()
    elif choice == "3":
        show_json_format_example()


def process_batch_cards(cards: List[dict]) -> Tuple[int, int]:
    """Process batch cards. Returns (success_count, error_count)."""
    success = 0
    errors = 0

    total = len(cards)
    for idx, card in enumerate(cards, 1):
        try:
            card_id = card["card_id"]
            name = card["name"]
            faction = card["faction"]
            power = int(card["power"])
            row = card["row"]
            ability = card.get("ability")
            is_unlockable = card.get("is_unlockable", False)
            rarity = card.get("rarity", "common")
            description = card.get("description", "")

            faction_constants = get_existing_faction_constants()
            faction_const = None
            for const, val in faction_constants.items():
                if val == faction:
                    faction_const = const
                    break

            if not faction_const:
                clean_faction = faction.upper().replace(' ', '_').replace("'", '')
                faction_const = f"FACTION_{clean_faction}"

            card_code = format_card_entry(card_id, name, faction_const, power, row, ability)

            def modify_cards(content: str) -> str:
                return insert_card_entry_safely(content, faction, card_code)

            if not safe_modify_file(FILES["cards"], modify_cards, f"Added card {card_id}"):
                errors += 1
                continue

            if is_unlockable:
                unlock_code = format_unlockable_entry(
                    card_id, name, faction, row, power, ability, description, rarity
                )

                def modify_unlocks(content: str) -> str:
                    return insert_unlockable_entry_safely(content, unlock_code)

                if not safe_modify_file(FILES["unlocks"], modify_unlocks, f"Added unlockable {card_id}"):
                    errors += 1
                    continue

            def modify_catalog(data: dict) -> dict:
                if faction not in data:
                    data[faction] = []
                data[faction].append({
                    "card_id": card_id,
                    "name": name,
                    "faction": faction,
                    "power": power,
                    "row": row,
                    "ability": ability
                })
                return data

            safe_modify_json(FILES["card_catalog"], modify_catalog, f"Added {card_id} to catalog")

            success += 1
            print(f"  [OK] Added card: {name} ({card_id})")

        except Exception as e:
            errors += 1
            print(f"  [ERROR] Failed to add card {card.get('card_id', '?')}: {e}")

        progress_bar(idx, total, "Cards")

    return success, errors


def process_batch_leaders(leaders: List[dict]) -> Tuple[int, int]:
    """Process batch leaders. Returns (success_count, error_count)."""
    success = 0
    errors = 0

    total = len(leaders)
    for idx, leader in enumerate(leaders, 1):
        try:
            card_id = leader["card_id"]
            name = leader["name"]
            faction = leader["faction"]
            ability = leader["ability"]
            ability_desc = leader["ability_desc"]
            is_unlockable = leader.get("is_unlockable", True)
            color_override = leader.get("color_override")
            banner_name = leader.get("banner_name", name.split()[-1])

            faction_constants = get_existing_faction_constants()
            faction_const = None
            for const, val in faction_constants.items():
                if val == faction:
                    faction_const = const
                    break

            if not faction_const:
                print(f"  [ERROR] Unknown faction: {faction}")
                errors += 1
                continue

            leader_entry = format_leader_entry(name, ability, ability_desc, card_id)

            def modify_registry(content: str) -> str:
                target_dict = "UNLOCKABLE_LEADERS" if is_unlockable else "BASE_FACTION_LEADERS"
                content = insert_leader_entry_safely(content, target_dict, faction_const, leader_entry)

                if color_override:
                    pattern = r'(LEADER_COLOR_OVERRIDES\s*=\s*\{)'
                    match = re.search(pattern, content)
                    if match:
                        end = content.find("}", match.end())
                        new_line = f'\n    "{card_id}": {tuple(color_override)},'
                        content = content[:end] + new_line + content[end:]

                pattern = r'(LEADER_BANNER_NAMES\s*=\s*\{)'
                match = re.search(pattern, content)
                if match:
                    end = content.find("}", match.end())
                    new_line = f'\n    "{card_id}": "{banner_name}",'
                    content = content[:end] + new_line + content[end:]

                return content

            if not safe_modify_file(FILES["content_registry"], modify_registry, f"Added leader {card_id}"):
                errors += 1
                continue

            def modify_leader_catalog(data: dict) -> dict:
                key = faction_const
                if key not in data:
                    data[key] = {"base": [], "unlockable": []}

                target = "unlockable" if is_unlockable else "base"
                data[key][target].append({
                    "name": name,
                    "ability": ability,
                    "ability_desc": ability_desc,
                    "card_id": card_id
                })
                return data

            safe_modify_json(FILES["leader_catalog"], modify_leader_catalog, f"Added leader {card_id}")

            success += 1
            print(f"  [OK] Added leader: {name} ({card_id})")

        except Exception as e:
            errors += 1
            print(f"  [ERROR] Failed to add leader {leader.get('card_id', '?')}: {e}")

        progress_bar(idx, total, "Leaders")

    return success, errors


def import_from_json_file():
    """Import cards and leaders from a JSON file."""
    print_header("IMPORT FROM JSON FILE")

    file_path = get_input("Path to JSON file")
    path = Path(file_path)

    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        return

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        return

    print("\n=== VALIDATING JSON ===")
    validation_errors = validate_batch_json(data)

    if validation_errors:
        print(f"\n[ERROR] Found {len(validation_errors)} validation errors:")
        for error in validation_errors[:10]:
            print(f"  - {error}")
        if len(validation_errors) > 10:
            print(f"  ... and {len(validation_errors) - 10} more errors")
        return

    print("[OK] JSON validation passed")

    cards = data.get("cards", [])
    leaders = data.get("leaders", [])

    print(f"\n=== IMPORT SUMMARY ===")
    print(f"  Cards to import: {len(cards)}")
    print(f"  Leaders to import: {len(leaders)}")

    if not confirm("\nProceed with import?"):
        print("Cancelled.")
        return

    card_success = 0
    card_errors = 0
    if cards:
        print("\n=== IMPORTING CARDS ===")
        card_success, card_errors = process_batch_cards(cards)

    leader_success = 0
    leader_errors = 0
    if leaders:
        print("\n=== IMPORTING LEADERS ===")
        leader_success, leader_errors = process_batch_leaders(leaders)

    print("\n=== IMPORT COMPLETE ===")
    print(f"  Cards:   {card_success} added, {card_errors} failed")
    print(f"  Leaders: {leader_success} added, {leader_errors} failed")

    if card_errors + leader_errors > 0:
        print("\n  Some imports failed - check the log for details")

    if card_success + leader_success > 0:
        if confirm("\nGenerate placeholder images for imported content?"):
            print("\n=== GENERATING PLACEHOLDERS ===")
            for card in cards:
                try:
                    generate_card_placeholder(
                        card["card_id"], card["name"], card["faction"],
                        int(card["power"]), card["row"], force=True
                    )
                except Exception:
                    pass
            for leader in leaders:
                try:
                    generate_leader_placeholders(
                        leader["card_id"], leader["name"], leader["faction"], force=True
                    )
                except Exception:
                    pass


def export_json_template():
    """Generate JSON template for batch import with examples."""
    print_header("EXPORT JSON TEMPLATE")

    template = {
        "cards": [
            {
                "card_id": "tauri_example",
                "name": "Example Card",
                "faction": "Tau'ri",
                "power": 5,
                "row": "ranged",
                "ability": None,
                "is_unlockable": False
            },
            {
                "card_id": "goauld_example",
                "name": "Example Unlockable",
                "faction": "Goa'uld",
                "power": 7,
                "row": "close",
                "ability": "Survival Instinct",
                "is_unlockable": True,
                "rarity": "rare",
                "description": "An example unlockable card"
            }
        ],
        "leaders": [
            {
                "card_id": "tauri_example_leader",
                "name": "Example Leader",
                "faction": "Tau'ri",
                "ability": "Draw 1 card when passing",
                "ability_desc": "When you pass your turn, draw 1 card from your deck",
                "is_unlockable": True,
                "banner_name": "Example"
            }
        ]
    }

    output_path = ROOT / "batch_import_template.json"
    output_path.write_text(json.dumps(template, indent=2))

    print(f"[OK] Template exported to: {output_path}")
    print("\nEdit this file with your content, then use option 1 to import.")


def show_json_format_example():
    """Display example JSON format for batch import."""
    print_header("JSON FORMAT EXAMPLE")

    print("""
The JSON file should have the following structure:

{
  "cards": [
    {
      "card_id": "faction_cardname",      // Required: lowercase, underscores
      "name": "Card Display Name",        // Required: the name shown in-game
      "faction": "Tau'ri",                // Required: exact faction name
      "power": 5,                         // Required: 0-20
      "row": "ranged",                    // Required: close/ranged/siege/agile
      "ability": "Tactical Formation",    // Optional: null or ability string
      "is_unlockable": false,             // Optional: default false
      "rarity": "rare",                   // Required if unlockable
      "description": "Flavor text"        // Optional for unlockables
    }
  ],
  "leaders": [
    {
      "card_id": "faction_leadername",    // Required: must match faction prefix
      "name": "Leader Name",              // Required: display name
      "faction": "Tau'ri",                // Required: exact faction name
      "ability": "Short ability text",    // Required: brief description
      "ability_desc": "Full description", // Required: detailed explanation
      "is_unlockable": true,              // Optional: default true
      "banner_name": "ShortName",         // Optional: short display name
      "color_override": [50, 100, 150]    // Optional: RGB color array
    }
  ]
}

Valid factions: Tau'ri, Goa'uld, Jaffa Rebellion, Lucian Alliance, Asgard, Alteran
Valid rows: close, ranged, siege, agile, special, weather
Valid rarities: common, rare, epic, legendary
""")

    input("\nPress Enter to continue...")
