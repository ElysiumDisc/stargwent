"""AST-aware code insertion helpers."""

import re
import ast
from typing import Optional, Tuple


def find_dict_in_ast(content: str, dict_name: str) -> Optional[Tuple[int, int]]:
    """
    Find the start and end positions of a dictionary assignment in Python code.

    Returns (start, end) character positions or None if not found.
    """
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == dict_name:
                        if isinstance(node.value, ast.Dict):
                            return (node.value.col_offset, node.value.end_col_offset)
    except SyntaxError:
        pass
    return None


def find_faction_section_end(content: str, faction: str) -> int:
    """
    Find the position to insert a new card for a given faction in cards.py.

    Uses comment markers like "# --- Faction ---" and finds the last card entry
    before the next section or end of ALL_CARDS dict.

    This function also serves as the insertion point finder for cards
    (replaces the old find_insertion_point_for_card).
    """
    # Look for the faction section marker
    pattern = rf'#\s*---\s*{re.escape(faction)}\s*---'
    match = re.search(pattern, content, re.IGNORECASE)

    if match:
        start_pos = match.end()

        # Find the next section marker
        next_section = re.search(r'\n\s*#\s*---\s*\w', content[start_pos:])
        if next_section:
            end_pos = start_pos + next_section.start()
        else:
            # Find end of ALL_CARDS dict - look for final closing brace
            end_pos = content.rfind("}")

        # Find the last complete card entry ending with "),"
        section = content[start_pos:end_pos]

        # Find the last ")," which marks end of a Card() constructor
        last_entry = section.rfind("),")
        if last_entry != -1:
            return start_pos + last_entry + 2  # Position after "),"

    # Fallback: before the closing brace of ALL_CARDS
    # Find the last "}" that closes the dict
    all_cards_start = content.find("ALL_CARDS = {")
    if all_cards_start != -1:
        # Count braces to find matching close
        brace_count = 0
        pos = all_cards_start + len("ALL_CARDS = ")
        while pos < len(content):
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Find the last ")," before this closing brace
                    last_entry = content.rfind("),", all_cards_start, pos)
                    if last_entry != -1:
                        return last_entry + 2
                    return pos
            pos += 1

    return len(content)


def insert_card_entry_safely(content: str, faction: str, card_entry: str) -> str:
    """Insert card entry using AST-aware positioning, preserving format."""
    insert_pos = find_faction_section_end(content, faction)
    return content[:insert_pos] + "\n" + card_entry + content[insert_pos:]


def insert_unlockable_entry_safely(content: str, entry: str) -> str:
    """Insert entry into UNLOCKABLE_CARDS dict in unlocks.py."""
    pattern = r'UNLOCKABLE_CARDS\s*=\s*\{'
    match = re.search(pattern, content)

    if match:
        # Find matching closing brace
        start = match.end()
        brace_count = 1
        pos = start
        while brace_count > 0 and pos < len(content):
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1

        # Insert before the closing brace
        insert_pos = pos - 1

        # Find the last entry (ends with "},")
        last_entry = content.rfind("},", match.start(), insert_pos)
        if last_entry != -1:
            insert_pos = last_entry + 2  # After "},"

        return content[:insert_pos] + "\n" + entry + content[insert_pos:]

    return content


def insert_leader_entry_safely(content: str, target_dict: str,
                                faction_const: str, leader_entry: str) -> str:
    """Insert leader entry into BASE_FACTION_LEADERS or UNLOCKABLE_LEADERS."""
    # Find the faction's list within the target dict
    pattern = rf'({target_dict}\s*=\s*\{{[^}}]*{faction_const}\s*:\s*\[)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        # Find the closing bracket of this faction's list
        start = match.end()
        bracket_count = 1
        pos = start
        while bracket_count > 0 and pos < len(content):
            if content[pos] == '[':
                bracket_count += 1
            elif content[pos] == ']':
                bracket_count -= 1
            pos += 1

        # Insert before the closing bracket
        insert_pos = pos - 1

        # Find last entry (ends with "},")
        last_entry = content.rfind("},", match.end(), insert_pos)
        if last_entry != -1:
            insert_pos = last_entry + 2

        return content[:insert_pos] + "\n        " + leader_entry + "," + content[insert_pos:]

    return content
