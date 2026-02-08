"""User workflow: Custom card creation wizard."""

import json
import re
import shutil
from pathlib import Path
from typing import Optional

from ..config import ROOT, USER_CONTENT_DIR
from ..ui import print_header, get_input, get_int, confirm, select_from_list
from ..code_parsing import get_existing_factions
from ..logging_ import log


def get_valid_abilities_list():
    """Get list of valid ability names from the Ability enum."""
    try:
        from abilities import Ability
        return [a.value for a in Ability]
    except ImportError:
        return []


def user_create_card_wizard():
    """Interactive wizard to create a custom card (using existing abilities only)."""
    print_header("CREATE CUSTOM CARD")
    print("This wizard helps you create a custom card for Stargwent.")
    print("All abilities must be from the existing game - no new mechanics.\n")

    # Ensure user_content directory exists
    cards_dir = USER_CONTENT_DIR / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    # Get card ID
    def validate_user_card_id(card_id: str) -> Optional[str]:
        if not card_id:
            return "Card ID cannot be empty"
        if not re.match(r'^[a-z][a-z0-9_]*$', card_id):
            return "Card ID must be lowercase letters, numbers, underscores, starting with letter"
        # Check for duplicates in user content
        if (cards_dir / card_id).exists():
            return f"User card '{card_id}' already exists"
        # Check for duplicates in game
        try:
            from cards import ALL_CARDS
            # Add user_ prefix to avoid conflicts
            full_id = f"user_{card_id}" if not card_id.startswith("user_") else card_id
            if full_id in ALL_CARDS or card_id in ALL_CARDS:
                return "Card ID conflicts with existing game card"
        except ImportError:
            pass
        return None

    card_id = get_input("Card ID (e.g., tokra_spy)", validator=validate_user_card_id)
    # Ensure user_ prefix
    if not card_id.startswith("user_"):
        card_id = f"user_{card_id}"

    card_name = get_input("Card Name (e.g., Tok'ra Infiltrator)")

    # Select faction
    factions = get_existing_factions()
    # Also add any user factions
    user_factions_dir = USER_CONTENT_DIR / "factions"
    if user_factions_dir.exists():
        for f in user_factions_dir.iterdir():
            if f.is_dir():
                faction_json = f / "faction.json"
                if faction_json.exists():
                    try:
                        data = json.loads(faction_json.read_text())
                        fname = data.get("name")
                        if fname and fname not in factions:
                            factions.append(fname)
                    except (json.JSONDecodeError, OSError):
                        pass

    faction = select_from_list("Select Faction:", factions)

    # Get power
    power = get_int("Power (0-15)", min_val=0, max_val=15, default=5)

    # Select row
    rows = [
        "close (melee combat)",
        "ranged (archery/guns)",
        "siege (ships/heavy weapons)",
        "agile (can go in close or ranged)",
    ]
    row_choice = select_from_list("Select Row:", rows)
    row = row_choice.split(" ")[0]  # Extract just the row name

    # Select ability - ONLY from existing abilities
    abilities = get_valid_abilities_list()
    ability_options = ["None (no special ability)"] + abilities

    print("\nSelect Ability (ONLY from existing game abilities):")
    for i, opt in enumerate(ability_options, 1):
        if i <= 10:
            print(f"  {i:2}. {opt}")
    if len(ability_options) > 10:
        print(f"  ... ({len(ability_options) - 10} more abilities available)")
        print("  Enter a number or type to search")

    while True:
        response = input("Choice (number or search term): ").strip()
        try:
            idx = int(response) - 1
            if 0 <= idx < len(ability_options):
                if idx == 0:
                    ability = None
                else:
                    ability = ability_options[idx]
                break
        except ValueError:
            # Search for ability
            matches = [a for a in abilities if response.lower() in a.lower()]
            if matches:
                print("\nMatching abilities:")
                for i, m in enumerate(matches[:10], 1):
                    print(f"  {i}. {m}")
                choice = get_int("Select match", min_val=1, max_val=len(matches[:10]))
                ability = matches[choice - 1]
                break
            else:
                print("No matching abilities found. Enter a number or try another search.")

    # Is unlockable?
    is_unlockable = confirm("Is this card unlockable (earned through gameplay)?", default=False)

    # Rarity
    rarities = ["common", "rare", "epic", "legendary"]
    rarity = select_from_list("Select Rarity:", rarities)

    # Description
    description = get_input("Description (flavor text, no mechanics)", default="A custom card")

    # Author
    author = get_input("Author (your name)", default="Unknown")

    # Preview
    print("\n" + "=" * 50)
    print("=== PREVIEW ===")
    print("=" * 50)
    print(f"  Card: {card_name}")
    print(f"  ID: {card_id}")
    print(f"  Faction: {faction}")
    print(f"  Power: {power} | Row: {row}")
    print(f"  Ability: {ability if ability else 'None'}")
    print(f"  Rarity: {rarity}" + (" (unlockable)" if is_unlockable else ""))
    print("=" * 50)

    if not confirm("\nCreate this card?"):
        print("Cancelled.")
        return

    # Create card directory and files
    card_dir = cards_dir / card_id.replace("user_", "")  # Store without prefix in folder name
    card_dir.mkdir(parents=True, exist_ok=True)

    card_data = {
        "card_id": card_id,
        "name": card_name,
        "faction": faction,
        "power": power,
        "row": row,
        "ability": ability,
        "is_unlockable": is_unlockable,
        "rarity": rarity,
        "description": description,
        "author": author
    }

    # Save card.json
    card_json = card_dir / "card.json"
    card_json.write_text(json.dumps(card_data, indent=2))
    log(f"Created user card: {card_id}")

    print(f"\n[OK] Card created in {card_dir}/")

    # Offer to generate placeholder
    if confirm("Generate placeholder image?", default=True):
        try:
            from ..dev.placeholders import generate_card_placeholder
            generate_card_placeholder(card_id, card_name, faction, power, row, force=True)
            # Copy to user content dir
            src = ROOT / "assets" / f"{card_id}.png"
            dst = card_dir / "card.png"
            if src.exists():
                shutil.copy2(src, dst)
                print(f"[OK] Placeholder saved to {dst}")
        except ImportError:
            print("[INFO] Placeholder generation not available")

    # Auto-enable
    try:
        from user_content_loader import get_loader
        loader = get_loader()
        loader.enable_content("card", card_id)
        print("[OK] Card enabled - will be available next game start")
    except (ImportError, AttributeError):
        print("[INFO] Card created. Enable it in 'Manage User Content' menu.")
