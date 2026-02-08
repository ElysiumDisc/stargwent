"""Developer workflow: Add a new faction (comprehensive)."""

import re
from typing import List, Optional

from ..config import FILES, VALID_ROWS
from ..ui import print_header, get_input, get_int, get_rgb, confirm, select_from_list
from ..validation import validate_faction_constant
from ..formatting import format_leader_entry
from ..code_parsing import get_existing_factions, get_existing_faction_constants, get_existing_abilities
from ..safety import safe_modify_file, safe_modify_json
from ..backup import restore_from_backup
from ..verification import verify_faction_integration, print_verification_results
from ..logging_ import log
from .add_leader import collect_leader_info


def collect_card_info(faction_name: str, faction_constant: str) -> Optional[dict]:
    """Collect information for a single card. Returns None if user enters 'done'."""
    card_id = input("Card ID (or 'done' to finish): ").strip()

    if card_id.lower() == 'done':
        return None

    name = get_input("Card Name")
    power = get_int("Power", min_val=0, max_val=15, default=5)
    row = select_from_list("Row:", VALID_ROWS[:4])

    abilities = get_existing_abilities()
    ability = select_from_list("Ability:", ["None"] + abilities[:10], allow_custom=True)
    if ability == "None":
        ability = None

    is_hero = confirm("Is this a hero (Legendary Commander)?", default=False)
    if is_hero and ability:
        ability = f"Legendary Commander, {ability}"
    elif is_hero:
        ability = "Legendary Commander"

    return {
        "card_id": card_id,
        "name": name,
        "power": power,
        "row": row,
        "ability": ability,
        "faction_constant": faction_constant
    }


def add_faction_to_cards_py(faction_name: str, faction_constant: str,
                             cards: List[dict]) -> bool:
    """Add faction constant and cards to cards.py."""

    def modify(content: str) -> str:
        constants_end = content.find("# Card Database")
        if constants_end == -1:
            constants_end = content.find("ALL_CARDS")

        new_constant = f'{faction_constant} = "{faction_name}"\n'
        content = content[:constants_end] + new_constant + content[constants_end:]

        all_cards_end = content.rfind("}")

        card_entries = [f'\n    # --- {faction_name} ---']
        for card in cards:
            ability_str = f'"{card["ability"]}"' if card["ability"] else "None"
            entry = f'    "{card["card_id"]}": Card("{card["card_id"]}", "{card["name"]}", {faction_constant}, {card["power"]}, "{card["row"]}", {ability_str}),'
            card_entries.append(entry)

        cards_section = "\n".join(card_entries) + "\n"
        content = content[:all_cards_end] + cards_section + content[all_cards_end:]

        return content

    return safe_modify_file(FILES["cards"], modify, f"Added faction {faction_name}")


def add_faction_to_content_registry(faction_name: str, faction_constant: str,
                                     base_leaders: List[dict],
                                     unlock_leaders: List[dict]) -> bool:
    """Add leaders to content_registry.py."""

    def modify(content: str) -> str:
        # Add import for new faction constant
        import_pattern = r'(from cards import \([^)]+)'
        match = re.search(import_pattern, content, re.DOTALL)
        if match:
            import_end = match.end()
            if faction_constant not in content[:import_end + 50]:
                comma_pos = content.rfind(",", match.start(), import_end)
                if comma_pos != -1:
                    content = content[:comma_pos + 1] + f"\n    {faction_constant}," + content[comma_pos + 1:]

        # Add to BASE_FACTION_LEADERS
        base_pattern = r'(BASE_FACTION_LEADERS\s*=\s*\{)'
        match = re.search(base_pattern, content)
        if match:
            start = match.end()
            brace_count = 1
            pos = start
            while brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1

            insert_pos = pos - 1

            base_entries = []
            for leader in base_leaders:
                entry = f'        {{"name": "{leader["name"]}", "ability": "{leader["ability"]}", "ability_desc": "{leader["ability_desc"]}", "card_id": "{leader["card_id"]}"}}'
                base_entries.append(entry)

            new_section = f'''    {faction_constant}: [
{",\n".join(base_entries)},
    ],
'''
            content = content[:insert_pos] + new_section + content[insert_pos:]

        # Add to UNLOCKABLE_LEADERS
        unlock_pattern = r'(UNLOCKABLE_LEADERS\s*=\s*\{)'
        match = re.search(unlock_pattern, content)
        if match:
            start = match.end()
            brace_count = 1
            pos = start
            while brace_count > 0:
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1

            insert_pos = pos - 1

            unlock_entries = []
            for leader in unlock_leaders:
                entry = f'        {{"name": "{leader["name"]}", "ability": "{leader["ability"]}", "ability_desc": "{leader["ability_desc"]}", "card_id": "{leader["card_id"]}"}}'
                unlock_entries.append(entry)

            new_section = f'''    {faction_constant}: [
{",\n".join(unlock_entries)},
    ],
'''
            content = content[:insert_pos] + new_section + content[insert_pos:]

        # Add color overrides
        for leader in base_leaders + unlock_leaders:
            if leader.get("color_override"):
                pattern = r'(LEADER_COLOR_OVERRIDES\s*=\s*\{)'
                match = re.search(pattern, content)
                if match:
                    end = content.find("}", match.end())
                    new_line = f'\n    "{leader["card_id"]}": {leader["color_override"]},'
                    content = content[:end] + new_line + content[end:]

        # Add banner names
        for leader in base_leaders + unlock_leaders:
            pattern = r'(LEADER_BANNER_NAMES\s*=\s*\{)'
            match = re.search(pattern, content)
            if match:
                end = content.find("}", match.end())
                short_name = leader["name"].split()[-1]
                new_line = f'\n    "{leader["card_id"]}": "{short_name}",'
                content = content[:end] + new_line + content[end:]

        return content

    return safe_modify_file(FILES["content_registry"], modify, f"Added {faction_name} leaders")


def add_faction_to_deck_persistence(faction_name: str, default_leader_id: str) -> bool:
    """Add default deck entry to deck_persistence.py."""

    def modify(content: str) -> str:
        pattern = r'(def _get_default_deck_data.*?return \{[^}]+)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            end = match.end()
            closing = content.find("}", end)

            new_entry = f'''            "{faction_name}": {{
                "leader": "{default_leader_id}",
                "cards": []
            }},
'''
            content = content[:closing] + new_entry + content[closing:]

        return content

    return safe_modify_file(FILES["deck_persistence"], modify, f"Added {faction_name} default deck")


def add_faction_to_game_config(faction_name: str, faction_constant: str,
                                primary_color: tuple, glow_color: tuple) -> bool:
    """Add faction colors to game_config.py."""

    def modify(content: str) -> str:
        pattern = r'(FACTION_UI_COLORS\s*=\s*\{[^}]+)'
        match = re.search(pattern, content)
        if match:
            end = match.end()
            closing = content.find("}", end)
            new_line = f'\n    "{faction_name}": {primary_color},'
            content = content[:closing] + new_line + content[closing:]

        pattern = r'(FACTION_GLOW_COLORS\s*=\s*\{[^}]+)'
        match = re.search(pattern, content)
        if match:
            end = match.end()
            closing = content.find("}", end)
            glow_hex = f"(0x{glow_color[0]:02X}, 0x{glow_color[1]:02X}, 0x{glow_color[2]:02X})"
            new_line = f'\n    {faction_constant}: {glow_hex},'
            content = content[:closing] + new_line + content[closing:]

        return content

    return safe_modify_file(FILES["game_config"], modify, f"Added {faction_name} colors")


def add_faction_power_stub(faction_name: str, power_name: str, power_desc: str) -> bool:
    """Add faction power stub to power.py."""

    class_name = faction_name.replace(" ", "").replace("'", "") + "FactionPower"

    def modify(content: str) -> str:
        pattern = r'(FACTION_POWERS\s*=\s*\{)'
        match = re.search(pattern, content)

        if match:
            insert_pos = match.start()

            new_class = f'''
class {class_name}(FactionPower):
    """{power_name} - {power_desc}"""
    def __init__(self):
        super().__init__(
            "{power_name}",
            "{power_desc}",
            "{faction_name}"
        )

    def activate(self, game, player):
        if not super().activate(game, player):
            return False

        # TODO: Implement {power_name} logic here
        print(f"{{player.name}} activated {power_name}!")

        return True


'''
            content = content[:insert_pos] + new_class + content[insert_pos:]

            pattern = r'(FACTION_POWERS\s*=\s*\{[^}]+)'
            match = re.search(pattern, content)
            if match:
                end = match.end()
                closing = content.find("}", end)
                new_line = f'\n    "{faction_name}": {class_name}(),'
                content = content[:closing] + new_line + content[closing:]

        return content

    return safe_modify_file(FILES["power"], modify, f"Added {faction_name} power stub")


def add_faction_to_placeholders_script(faction_name: str, faction_constant: str,
                                        primary_color: tuple) -> bool:
    """Add faction to create_placeholders.py including FACTION_NAME_ALIASES."""

    def modify(content: str) -> str:
        pattern = r'(FACTION_COLORS\s*=\s*\{[^}]+)'
        match = re.search(pattern, content)
        if match:
            end = match.end()
            closing = content.find("}", end)
            new_line = f'\n    {faction_constant}: {primary_color},'
            content = content[:closing] + new_line + content[closing:]

        pattern = r'(FACTION_BACKGROUND_IDS\s*=\s*\{[^}]+)'
        match = re.search(pattern, content)
        if match:
            end = match.end()
            closing = content.find("}", end)
            bg_id = faction_name.lower().replace(" ", "_").replace("'", "")
            new_line = f'\n    {faction_constant}: "{bg_id}",'
            content = content[:closing] + new_line + content[closing:]

        pattern = r'(FACTION_NAME_ALIASES\s*=\s*\{)'
        match = re.search(pattern, content)
        if match:
            start = match.end()
            brace_count = 1
            pos = start
            while brace_count > 0 and pos < len(content):
                if content[pos] == '{':
                    brace_count += 1
                elif content[pos] == '}':
                    brace_count -= 1
                pos += 1
            closing = pos - 1

            clean_name = faction_name.replace("'", "").replace(" ", "")
            short_name = faction_name.split()[0] if " " in faction_name else faction_name

            aliases = [
                f'    {faction_constant}: {faction_constant},',
                f'    "{faction_name}": {faction_constant},',
            ]
            if short_name != faction_name:
                aliases.append(f'    "{short_name}": {faction_constant},')
            if clean_name != faction_name and clean_name != short_name:
                aliases.append(f'    "{clean_name}": {faction_constant},')

            new_lines = '\n'.join(aliases)
            content = content[:closing] + new_lines + '\n' + content[closing:]

        return content

    return safe_modify_file(FILES["create_placeholders"], modify, f"Added {faction_name} to placeholders")


def update_catalogs_for_faction(faction_name: str, faction_constant: str,
                                 cards: List[dict], base_leaders: List[dict],
                                 unlock_leaders: List[dict]):
    """Update JSON catalog files for new faction."""

    def modify_cards(data: dict) -> dict:
        data[faction_name] = [
            {
                "card_id": c["card_id"],
                "name": c["name"],
                "faction": faction_name,
                "power": c["power"],
                "row": c["row"],
                "ability": c["ability"]
            }
            for c in cards
        ]
        return data

    safe_modify_json(FILES["card_catalog"], modify_cards, f"Added {faction_name} cards")

    def modify_leaders(data: dict) -> dict:
        data[faction_constant] = {
            "base": [
                {
                    "name": l["name"],
                    "ability": l["ability"],
                    "ability_desc": l["ability_desc"],
                    "card_id": l["card_id"]
                }
                for l in base_leaders
            ],
            "unlockable": [
                {
                    "name": l["name"],
                    "ability": l["ability"],
                    "ability_desc": l["ability_desc"],
                    "card_id": l["card_id"]
                }
                for l in unlock_leaders
            ]
        }
        return data

    safe_modify_json(FILES["leader_catalog"], modify_leaders, f"Added {faction_name} leaders")


def add_faction_workflow():
    """Comprehensive workflow to add a new faction."""
    print_header("ADD NEW FACTION (COMPREHENSIVE)")

    print("This wizard will guide you through creating a complete new faction.")
    print("You'll need to provide:")
    print("  - Basic faction info (name, colors)")
    print("  - 3 base leaders with abilities")
    print("  - At least 15 starter deck cards")
    print("  - 4 unlockable leaders")
    print("  - Faction power ability")
    print()

    if not confirm("Ready to begin?"):
        return

    # === BASIC INFO ===
    print_header("STEP 1: Basic Faction Info")

    faction_name = get_input("Faction Name (e.g., Replicators)")
    clean_name = faction_name.upper().replace(' ', '_').replace("'", '')
    constant_suggestion = f"FACTION_{clean_name}"
    faction_constant = get_input("Faction Constant", default=constant_suggestion,
                                  validator=validate_faction_constant)
    faction_lore = get_input("Faction Lore/Description (for docs)")

    # === VISUAL IDENTITY ===
    print_header("STEP 2: Visual Identity")

    primary_color = get_rgb("Primary Color (for cards, UI)", default=(150, 150, 150))
    secondary_color = get_rgb("Secondary Color (for accents)", default=(100, 100, 100))
    glow_color = get_rgb("Glow Color (for card effects)", default=(128, 128, 200))

    # === FACTION POWER ===
    print_header("STEP 3: Faction Power (Once-per-game ability)")

    power_name = get_input("Power Name (e.g., Assimilation Swarm)")
    power_desc = get_input("Power Description (what it does)")

    # === BASE LEADERS (3) ===
    print_header("STEP 4: Base Leaders (3 required)")

    base_leaders = []
    for i in range(3):
        print(f"\n--- Base Leader {i+1} ---")
        leader = collect_leader_info(faction_name, is_base=True)
        base_leaders.append(leader)

    # === STARTER DECK CARDS ===
    print_header("STEP 5: Starter Deck Cards (minimum 15)")

    print("Enter cards for the starter deck. Minimum 15 cards.")
    print("Enter 'done' when finished (after at least 15 cards).\n")

    cards = []
    while True:
        print(f"\n--- Card {len(cards) + 1} ---")
        card = collect_card_info(faction_name, faction_constant)

        if card is None:
            if len(cards) >= 15:
                break
            else:
                print(f"  Need at least 15 cards. Currently have {len(cards)}.")
                continue

        cards.append(card)

    # === UNLOCKABLE LEADERS (4) ===
    print_header("STEP 6: Unlockable Leaders (4 required)")

    unlock_leaders = []
    for i in range(4):
        print(f"\n--- Unlockable Leader {i+1} ---")
        leader = collect_leader_info(faction_name, is_base=False)
        unlock_leaders.append(leader)

    # === SUMMARY AND CONFIRMATION ===
    print_header("FACTION SUMMARY")

    print(f"Faction: {faction_name} ({faction_constant})")
    print(f"Colors: Primary {primary_color}, Secondary {secondary_color}, Glow {glow_color}")
    print(f"Faction Power: {power_name}")
    print(f"Base Leaders: {', '.join(l['name'] for l in base_leaders)}")
    print(f"Unlockable Leaders: {', '.join(l['name'] for l in unlock_leaders)}")
    print(f"Starter Cards: {len(cards)}")

    print()
    if not confirm("Create this faction? (This will modify multiple files)"):
        print("Cancelled.")
        return

    # === BEGIN FILE MODIFICATIONS ===
    print_header("CREATING FACTION...")

    print("\n=== Modifying cards.py ===")
    if not add_faction_to_cards_py(faction_name, faction_constant, cards):
        return

    print("\n=== Modifying content_registry.py ===")
    if not add_faction_to_content_registry(faction_name, faction_constant,
                                            base_leaders, unlock_leaders):
        restore_from_backup(FILES["cards"])
        return

    print("\n=== Modifying deck_persistence.py ===")
    if not add_faction_to_deck_persistence(faction_name, base_leaders[0]["card_id"]):
        restore_from_backup(FILES["cards"])
        restore_from_backup(FILES["content_registry"])
        return

    print("\n=== Modifying game_config.py ===")
    if not add_faction_to_game_config(faction_name, faction_constant,
                                       primary_color, glow_color):
        print("  Warning: Could not update game_config.py")

    print("\n=== Modifying power.py ===")
    if not add_faction_power_stub(faction_name, power_name, power_desc):
        print("  Warning: Could not update power.py - manual implementation needed")

    print("\n=== Modifying create_placeholders.py ===")
    if not add_faction_to_placeholders_script(faction_name, faction_constant, primary_color):
        print("  Warning: Could not update create_placeholders.py")

    print("\n=== Updating documentation ===")
    update_catalogs_for_faction(faction_name, faction_constant, cards,
                                base_leaders, unlock_leaders)

    print("\n=== Generating placeholder assets ===")
    if confirm("Generate all placeholder images for this faction?"):
        from .placeholders import generate_faction_placeholders
        generate_faction_placeholders(faction_name, faction_constant, cards,
                                      base_leaders + unlock_leaders)

    # === VERIFICATION ===
    print("\n=== INTEGRATION VERIFICATION ===")
    checks = verify_faction_integration(faction_name, faction_constant)
    print_verification_results(checks)

    print_header("FACTION CREATED!")
    print(f"'{faction_name}' has been added to the game.")
    print()
    print("IMPORTANT: You still need to implement:")
    print(f"  1. Faction power logic in power.py ({power_name})")
    print(f"  2. Leader ability implementations in game.py")
    print(f"  3. Any custom card abilities in game.py")

    log(f"SESSION COMPLETE - Faction '{faction_name}' created with {len(cards)} cards and {len(base_leaders) + len(unlock_leaders)} leaders")
