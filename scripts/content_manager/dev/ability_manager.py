"""Developer workflow: Ability manager (add/edit/view abilities)."""

import re

from ..config import FILES
from ..ui import print_header, get_input, confirm, select_from_list
from ..code_parsing import get_existing_abilities
from ..safety import safe_modify_file
from ..logging_ import log


def ability_manager_workflow():
    """Manage abilities (card, leader, faction power)."""
    print_header("ABILITY MANAGER")

    print("  1. Add new Card Ability (to abilities.py enum)")
    print("  2. Edit Leader Ability (in content_registry.py)")
    print("  3. Assign ability to existing card")
    print("  4. View all abilities")
    print("  0. Back")
    print()

    choice = get_input("Choice", default="0")

    if choice == "1":
        add_card_ability()
    elif choice == "2":
        edit_leader_ability()
    elif choice == "3":
        assign_ability_to_card()
    elif choice == "4":
        view_all_abilities()


def add_card_ability():
    """Add a new ability to the Ability enum."""
    print_header("ADD NEW CARD ABILITY")

    ability_name = get_input("Ability Name (e.g., 'Quantum Tunneling')")
    enum_name = ability_name.upper().replace(" ", "_").replace("'", "")

    effect = get_input("Effect description")
    timing = get_input("Timing (when does it trigger?)")
    synergy = get_input("Synergy notes (what combos with it?)")

    print(f"\nAbility Enum Value: {enum_name} = \"{ability_name}\"")

    if not confirm("Add this ability?"):
        return

    def modify_abilities(content: str) -> str:
        class_start = content.find("class Ability(Enum):")
        if class_start == -1:
            raise ValueError("Could not find Ability enum class in abilities.py")

        func_start = content.find("\ndef ", class_start)
        if func_start == -1:
            func_start = len(content)

        enum_section = content[class_start:func_start]
        last_equals = enum_section.rfind(" = ")

        if last_equals == -1:
            raise ValueError("Could not find any enum values in Ability class")

        absolute_pos = class_start + last_equals
        line_end = content.find('\n', absolute_pos)

        new_line = f'\n    {enum_name} = "{ability_name}"'
        content = content[:line_end] + new_line + content[line_end:]

        return content

    if safe_modify_file(FILES["abilities"], modify_abilities, f"Added ability {ability_name}"):
        print(f"[OK] Added {ability_name} to abilities.py")

    def modify_rules(content: str) -> str:
        pattern = r'(def build_ability_info\(\):.*?return \{)'
        match = re.search(pattern, content, re.DOTALL)

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

            insert_pos = pos - 1

            new_entry = f'''        "{ability_name}": {{
            "effect": "{effect}",
            "timing": "{timing}",
            "synergy": "{synergy}",
        }},
'''
            content = content[:insert_pos] + new_entry + content[insert_pos:]

        return content

    if safe_modify_file(FILES["generate_rules_spec"], modify_rules, f"Added ability docs for {ability_name}"):
        print(f"[OK] Added documentation for {ability_name}")


def edit_leader_ability():
    """Edit an existing leader's ability."""
    print_header("EDIT LEADER ABILITY")

    card_id = get_input("Leader Card ID (e.g., tauri_oneill)")

    new_ability = get_input("New Ability (short)")
    new_desc = get_input("New Ability Description (full)")

    def modify(content: str) -> str:
        pattern = rf'"card_id":\s*"{card_id}"'
        match = re.search(pattern, content)

        if match:
            start = content.rfind("{", 0, match.start())
            end = content.find("}", match.end()) + 1

            old_entry = content[start:end]

            new_entry = re.sub(r'"ability":\s*"[^"]*"', f'"ability": "{new_ability}"', old_entry)
            new_entry = re.sub(r'"ability_desc":\s*"[^"]*"', f'"ability_desc": "{new_desc}"', new_entry)

            content = content[:start] + new_entry + content[end:]
        else:
            raise ValueError(f"Leader {card_id} not found in content_registry.py")

        return content

    if safe_modify_file(FILES["content_registry"], modify, f"Updated {card_id} ability"):
        print(f"[OK] Updated leader {card_id}")


def assign_ability_to_card():
    """Assign an ability to an existing card."""
    print_header("ASSIGN ABILITY TO CARD")

    card_id = get_input("Card ID")

    abilities = get_existing_abilities()
    ability = select_from_list("Select Ability:", abilities, allow_custom=True)

    def modify(content: str) -> str:
        pattern = rf'("{card_id}":\s*Card\([^)]+\))'
        match = re.search(pattern, content)

        if match:
            old_entry = match.group(1)
            new_entry = re.sub(r',\s*(?:None|"[^"]*")\s*\)', f', "{ability}")', old_entry)
            content = content.replace(old_entry, new_entry)
        else:
            raise ValueError(f"Card {card_id} not found")

        return content

    if safe_modify_file(FILES["cards"], modify, f"Assigned {ability} to {card_id}"):
        print(f"[OK] Assigned ability to {card_id}")


def view_all_abilities():
    """Display all existing abilities."""
    print_header("ALL ABILITIES")

    abilities = get_existing_abilities()

    print(f"Found {len(abilities)} abilities:\n")
    for i, ability in enumerate(abilities, 1):
        print(f"  {i:2}. {ability}")
