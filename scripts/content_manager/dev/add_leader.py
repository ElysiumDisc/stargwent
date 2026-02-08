"""Developer workflow: Add a new leader."""

import re

from ..config import FILES
from ..ui import print_header, get_input, get_rgb, confirm, select_from_list
from ..validation import validate_card_id, validate_leader_id_prefix
from ..code_parsing import get_existing_factions, get_existing_faction_constants
from ..safety import safe_modify_file, safe_modify_json
from ..verification import verify_leader_integration, print_verification_results
from ..logging_ import log


def generate_leader_placeholders(card_id, name, faction, force=False):
    """Import and delegate to placeholders module."""
    from .placeholders import generate_leader_placeholders as _gen
    return _gen(card_id, name, faction, force=force)


def collect_leader_info(faction_name: str, is_base: bool) -> dict:
    """Collect information for a single leader."""
    name = get_input("Leader Name")

    prefix = faction_name.lower().replace(" ", "_").replace("'", "")[:8]
    id_suffix = name.lower().replace(" ", "_").replace("'", "").replace(".", "")
    suggested_id = f"{prefix}_{id_suffix}"

    card_id = get_input("Card ID", default=suggested_id)
    ability = get_input("Ability (short)")
    ability_desc = get_input("Ability Description (full)")

    color_override = None
    if confirm("Set custom color?", default=False):
        color_override = get_rgb("Color RGB")

    return {
        "name": name,
        "card_id": card_id,
        "ability": ability,
        "ability_desc": ability_desc,
        "color_override": color_override,
        "is_base": is_base
    }


def add_leader_workflow():
    """Interactive workflow to add a new leader."""
    print_header("ADD NEW LEADER")

    print("Enter leader details:\n")

    card_id = get_input("Card ID (e.g., tauri_newleader)", validator=validate_card_id)
    name = get_input("Leader Name (e.g., Dr. New Character)")

    factions = get_existing_factions()[:-1]  # Exclude Neutral
    faction = select_from_list("Select Faction:", factions)

    prefix_warning = validate_leader_id_prefix(card_id, faction)
    if prefix_warning:
        print(f"  Warning: {prefix_warning}")
        if not confirm("Continue anyway?", default=False):
            return

    ability_short = get_input("Ability (short description, e.g., 'Draw 2 cards when passing')")
    ability_desc = get_input("Ability Description (full explanation)")

    is_unlockable = confirm("Is this leader unlockable (vs base)?", default=True)

    color_override = None
    if confirm("Set custom color override?", default=False):
        color_override = get_rgb("Color override RGB", default=(50, 50, 80))

    banner_name = get_input("Banner name (short display name)", default=name.split()[-1])

    # Preview
    print("\n" + "=" * 50)
    print("PREVIEW: New Leader Entry")
    print("=" * 50)

    leader_entry = f'''        {{"name": "{name}", "ability": "{ability_short}", "ability_desc": "{ability_desc}", "card_id": "{card_id}"}},'''

    print(f"\ncontent_registry.py entry:")
    print(leader_entry)

    if color_override:
        print(f"\nLEADER_COLOR_OVERRIDES entry:")
        print(f'    "{card_id}": {color_override},')

    print(f"\nLEADER_BANNER_NAMES entry:")
    print(f'    "{card_id}": "{banner_name}",')

    if not confirm("\nAdd this leader to the codebase?"):
        print("Cancelled.")
        return

    # === STEP 1: Modify content_registry.py ===
    print("\n=== STEP 1: content_registry.py ===")

    def modify_registry(content: str) -> str:
        faction_const = None
        for const, val in get_existing_faction_constants().items():
            if val == faction:
                faction_const = const
                break

        if not faction_const:
            raise ValueError(f"Could not find faction constant for {faction}")

        target_dict = "UNLOCKABLE_LEADERS" if is_unlockable else "BASE_FACTION_LEADERS"

        pattern = rf'({target_dict}\s*=\s*\{{[^}}]*{faction_const}\s*:\s*\[)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            start = match.end()
            bracket_count = 1
            pos = start
            while bracket_count > 0 and pos < len(content):
                if content[pos] == '[':
                    bracket_count += 1
                elif content[pos] == ']':
                    bracket_count -= 1
                pos += 1

            insert_pos = pos - 1
            last_entry = content.rfind("},", match.end(), insert_pos)
            if last_entry != -1:
                insert_pos = last_entry + 2

            new_entry = f'\n{leader_entry}'
            content = content[:insert_pos] + new_entry + content[insert_pos:]

        # Add color override
        if color_override:
            pattern = r'(LEADER_COLOR_OVERRIDES\s*=\s*\{)'
            match = re.search(pattern, content)
            if match:
                end = content.find("}", match.end())
                insert_pos = end
                new_line = f'\n    "{card_id}": {color_override},'
                content = content[:insert_pos] + new_line + content[insert_pos:]

        # Add banner name
        pattern = r'(LEADER_BANNER_NAMES\s*=\s*\{)'
        match = re.search(pattern, content)
        if match:
            end = content.find("}", match.end())
            insert_pos = end
            new_line = f'\n    "{card_id}": "{banner_name}",'
            content = content[:insert_pos] + new_line + content[insert_pos:]

        return content

    if not safe_modify_file(FILES["content_registry"], modify_registry, f"Added leader {card_id}"):
        return

    # === STEP 2: Update leader_catalog.json ===
    print("\n=== STEP 2: leader_catalog.json ===")

    faction_const = None
    for const, val in get_existing_faction_constants().items():
        if val == faction:
            faction_const = const
            break

    def modify_leader_catalog(data: dict) -> dict:
        key = faction_const or f"FACTION_{faction.upper().replace(' ', '_')}"

        if key not in data:
            data[key] = {"base": [], "unlockable": []}

        target = "unlockable" if is_unlockable else "base"
        data[key][target].append({
            "name": name,
            "ability": ability_short,
            "ability_desc": ability_desc,
            "card_id": card_id
        })

        return data

    if not safe_modify_json(FILES["leader_catalog"], modify_leader_catalog, f"Added leader {card_id}"):
        print("  Warning: Failed to update leader_catalog.json")

    # === STEP 3: Generate placeholder images ===
    print("\n=== STEP 3: Placeholder Images ===")
    if confirm("Generate placeholder portrait and background?"):
        generate_leader_placeholders(card_id, name, faction, force=True)

    # === VERIFICATION ===
    checks = verify_leader_integration(card_id, faction)
    print_verification_results(checks)

    print(f"\n     Type: {'Unlockable' if is_unlockable else 'Base'}")
    print(f"     Faction: {faction}")

    log(f"SESSION COMPLETE - Leader '{name}' ({card_id}) added")
