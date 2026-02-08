"""Developer workflow: Add a new card."""

from ..config import FILES, VALID_ROWS, VALID_RARITIES
from ..ui import print_header, get_input, get_int, confirm, select_from_list
from ..validation import (
    validate_card_id, validate_card_name_unique,
    validate_leader_id_prefix, validate_ability_string,
)
from ..formatting import format_card_entry, format_unlockable_entry
from ..code_insertion import insert_card_entry_safely, insert_unlockable_entry_safely
from ..code_parsing import get_existing_factions, get_existing_faction_constants, get_existing_abilities
from ..safety import safe_modify_file, safe_modify_json
from ..backup import restore_from_backup
from ..verification import verify_card_integration, print_verification_results
from ..logging_ import log


def generate_card_placeholder(card_id, name, faction, power, row, force=False):
    """Import and delegate to placeholders module."""
    from .placeholders import generate_card_placeholder as _gen
    return _gen(card_id, name, faction, power, row, force=force)


def add_card_workflow():
    """Interactive workflow to add a new card."""
    print_header("ADD NEW CARD")

    # Collect card information
    print("Enter card details:\n")

    card_id = get_input("Card ID (e.g., tauri_scientist)", validator=validate_card_id)

    # Validate card name is unique
    while True:
        card_name = get_input("Card Name (e.g., SGC Scientist)")
        name_error = validate_card_name_unique(card_name)
        if name_error:
            print(f"  Warning: {name_error}")
            if not confirm("Use this name anyway?", default=False):
                continue
        break

    factions = get_existing_factions()
    faction = select_from_list("Select Faction:", factions)

    # Validate card_id prefix matches faction convention
    prefix_warning = validate_leader_id_prefix(card_id, faction)
    if prefix_warning:
        expected_prefix = card_id.split("_")[0] + "_"
        faction_prefix = faction.lower().replace("'", "").replace(" ", "_")[:8]
        if not card_id.startswith(faction_prefix):
            print(f"  Note: Card ID doesn't start with faction prefix '{faction_prefix}_'")
            if not confirm("Continue anyway?", default=True):
                return

    power = get_int("Power (0-15)", min_val=0, max_val=15, default=5)

    row = select_from_list("Select Row:", VALID_ROWS[:4])

    abilities = get_existing_abilities()
    ability = select_from_list("Select Ability (or None):", ["None"] + abilities[:15], allow_custom=True)
    if ability == "None":
        ability = None

    if ability:
        ability_warning = validate_ability_string(ability)
        if ability_warning:
            print(f"  Warning: {ability_warning}")
            if not confirm("Use this ability anyway?", default=True):
                ability = None

    is_unlockable = confirm("Is this an unlockable card?", default=False)

    rarity = None
    description = None
    if is_unlockable:
        rarity = select_from_list("Rarity:", VALID_RARITIES)
        description = get_input("Description/flavor text")

    # Get faction constant
    faction_constants = get_existing_faction_constants()
    faction_const = None
    for const, val in faction_constants.items():
        if val == faction:
            faction_const = const
            break

    if not faction_const:
        clean_faction = faction.upper().replace(' ', '_').replace("'", '')
        faction_const = f"FACTION_{clean_faction}"

    # Show preview and get confirmation
    print("\n" + "=" * 50)
    print("PREVIEW: New Card Entry")
    print("=" * 50)

    card_code = format_card_entry(card_id, card_name, faction_const, power, row, ability)

    print(f"\ncards.py entry:")
    print(card_code)

    if is_unlockable:
        unlockable_code = format_unlockable_entry(
            card_id, card_name, faction, row, power, ability, description, rarity
        )
        print(f"\nunlocks.py entry:")
        print(unlockable_code)

    print()

    if not confirm("Add this card to the codebase?"):
        print("Cancelled.")
        return

    # === STEP 1: Modify cards.py ===
    print("\n=== STEP 1: cards.py ===")

    def modify_cards_py(content: str) -> str:
        return insert_card_entry_safely(content, faction, card_code)

    if not safe_modify_file(FILES["cards"], modify_cards_py, f"Added card {card_id}"):
        return

    # === STEP 2: Modify unlocks.py if unlockable ===
    if is_unlockable:
        print("\n=== STEP 2: unlocks.py ===")

        unlockable_code = format_unlockable_entry(
            card_id, card_name, faction, row, power, ability, description, rarity
        )

        def modify_unlocks_py(content: str) -> str:
            return insert_unlockable_entry_safely(content, unlockable_code)

        if not safe_modify_file(FILES["unlocks"], modify_unlocks_py, f"Added unlockable {card_id}"):
            restore_from_backup(FILES["cards"])
            return

    # === STEP 3: Update card_catalog.json ===
    print("\n=== STEP 3: card_catalog.json ===")

    def modify_catalog(data: dict) -> dict:
        if faction not in data:
            data[faction] = []

        data[faction].append({
            "card_id": card_id,
            "name": card_name,
            "faction": faction,
            "power": power,
            "row": row,
            "ability": ability
        })

        return data

    if not safe_modify_json(FILES["card_catalog"], modify_catalog, f"Added {card_id}"):
        print("  Warning: Failed to update card_catalog.json")

    # === STEP 4: Generate placeholder image ===
    print("\n=== STEP 4: Placeholder Image ===")
    if confirm("Generate placeholder image?"):
        generate_card_placeholder(card_id, card_name, faction, power, row, force=True)

    # === VERIFICATION ===
    checks = verify_card_integration(card_id, faction, is_unlockable)
    print_verification_results(checks)

    log(f"SESSION COMPLETE - Card '{card_name}' ({card_id}) added")
