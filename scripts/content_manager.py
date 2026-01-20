#!/usr/bin/env python3
"""
Stargwent Content Manager - Developer Tool
===========================================

A powerful CLI tool to help add game content to the Stargwent codebase.
This script modifies source code files to add factions, leaders, cards, abilities,
and auto-generate placeholder assets.

Usage:
    python scripts/content_manager.py

Features:
    === DEVELOPER TOOLS ===
    1. Add a new CARD
    2. Add a new LEADER
    3. Add a new FACTION (comprehensive)
    4. Add/Edit ABILITY
    5. Generate placeholder images
    6. Regenerate all documentation
    7. Asset Checker (find missing images)
    8. Balance Analyzer (power stats)
    11. Batch Import (from JSON)
    12. Audio Manager (faction themes, voices, sound effects)
    13. Leader Ability Generator (code stub generation)
    14. Card Rename/Delete Tool (safe multi-file updates)

    === USER TOOLS ===
    9. Save Manager (backup/restore saves)
    10. Deck Import/Export (share decks)
"""

import os
import sys
import json
import shutil
import re
import ast
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# Add parent directory to path for imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ============================================================================
# CONFIGURATION
# ============================================================================

BACKUP_DIR = ROOT / "backup"
LOG_FILE = ROOT / "scripts" / "content_manager.log"

# File paths that this tool modifies
FILES = {
    "cards": ROOT / "cards.py",
    "content_registry": ROOT / "content_registry.py",
    "abilities": ROOT / "abilities.py",
    "unlocks": ROOT / "unlocks.py",
    "deck_persistence": ROOT / "deck_persistence.py",
    "game_config": ROOT / "game_config.py",
    "power": ROOT / "power.py",
    "create_placeholders": ROOT / "scripts" / "create_placeholders.py",
    "generate_rules_spec": ROOT / "scripts" / "generate_rules_spec.py",
    "card_catalog": ROOT / "docs" / "card_catalog.json",
    "leader_catalog": ROOT / "docs" / "leader_catalog.json",
}

# Valid values for validation
VALID_ROWS = ["close", "ranged", "siege", "agile", "special", "weather"]
VALID_RARITIES = ["common", "rare", "epic", "legendary"]

# ============================================================================
# LOGGING
# ============================================================================

_session_log = []
_session_start = None
_backup_folder = None


def log(message: str):
    """Log a message with timestamp."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    _session_log.append(entry)
    print(f"  {message}")


def start_session():
    """Start a new logging session."""
    global _session_start, _backup_folder, _session_log
    _session_start = datetime.datetime.now()
    _session_log = []
    _backup_folder = BACKUP_DIR / _session_start.strftime("%Y-%m-%d_%H%M%S")

    header = f"\n=== CONTENT MANAGER SESSION: {_session_start.strftime('%Y-%m-%d %H:%M:%S')} ==="
    _session_log.append(header)
    log(f"BACKUP FOLDER: {_backup_folder}")


def save_session_log():
    """Save session log to file."""
    if not _session_log:
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write("\n".join(_session_log) + "\n\n")

    print(f"\nSession log saved to: {LOG_FILE}")


# ============================================================================
# BACKUP SYSTEM
# ============================================================================

def create_backup(file_path: Path, force: bool = False) -> Path:
    """
    Create a backup of a file before modification.

    Args:
        file_path: The file to backup
        force: If True, overwrite existing backup. If False (default),
               skip if backup already exists in this session.

    Returns:
        Path to the backup file
    """
    if not _backup_folder:
        raise RuntimeError("Session not started - call start_session() first")

    _backup_folder.mkdir(parents=True, exist_ok=True)

    backup_path = _backup_folder / file_path.name

    # Skip if backup already exists (preserves original state for batch operations)
    if backup_path.exists() and not force:
        log(f"BACKUP EXISTS: {file_path.name} (keeping original)")
        return backup_path

    if file_path.exists():
        shutil.copy2(file_path, backup_path)
        log(f"BACKUP CREATED: {file_path.name} -> {backup_path}")

    return backup_path


def restore_from_backup(file_path: Path):
    """Restore a file from its backup."""
    if not _backup_folder:
        return False

    backup_path = _backup_folder / file_path.name
    if backup_path.exists():
        shutil.copy2(backup_path, file_path)
        log(f"RESTORED: {file_path.name} from backup")
        return True
    return False


# ============================================================================
# FILE MODIFICATION WITH SAFETY
# ============================================================================

def safe_modify_file(file_path: Path, modifier_fn, description: str) -> bool:
    """
    Safely modify a file with full validation.

    1. Creates backup before modification
    2. Applies modifier function
    3. Validates Python syntax (for .py files)
    4. Tests import works (for .py files)
    5. Rolls back on any failure
    """
    # Create backup
    create_backup(file_path)

    # Read original content
    original = file_path.read_text() if file_path.exists() else ""

    try:
        # Apply modification
        modified = modifier_fn(original)

        # Validate Python syntax
        if file_path.suffix == ".py":
            compile(modified, str(file_path), "exec")

        # Write changes
        file_path.write_text(modified)

        # Verify import works for Python files
        if file_path.suffix == ".py":
            module_name = file_path.stem
            # Don't test import for script files
            if file_path.parent == ROOT:
                try:
                    # Clear from sys.modules to force reimport
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    __import__(module_name)
                except Exception as e:
                    raise RuntimeError(f"Import test failed: {e}")

        log(f"MODIFIED: {file_path.name} - {description}")
        return True

    except Exception as e:
        # ROLLBACK
        file_path.write_text(original)
        log(f"ERROR: {e}")
        log(f"ROLLED BACK: {file_path.name}")
        print(f"\n  [ERROR] {e}")
        print(f"  Changes rolled back - game is safe!")
        return False


def safe_modify_json(file_path: Path, modifier_fn, description: str) -> bool:
    """Safely modify a JSON file."""
    create_backup(file_path)

    try:
        if file_path.exists():
            data = json.loads(file_path.read_text())
        else:
            data = {}

        modified_data = modifier_fn(data)

        file_path.write_text(json.dumps(modified_data, indent=2))
        log(f"MODIFIED: {file_path.name} - {description}")
        return True

    except Exception as e:
        restore_from_backup(file_path)
        log(f"ERROR: {e}")
        print(f"\n  [ERROR] {e}")
        return False


# ============================================================================
# USER INTERACTION HELPERS
# ============================================================================

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """Print a formatted header."""
    width = 50
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)
    print()


def print_box(lines: List[str], width: int = 48):
    """Print text in a box."""
    print("+" + "-" * width + "+")
    for line in lines:
        print(f"| {line:<{width-2}} |")
    print("+" + "-" * width + "+")


def confirm(prompt: str, default: bool = True) -> bool:
    """Ask for yes/no confirmation."""
    suffix = "[Y/n]" if default else "[y/N]"
    response = input(f"{prompt} {suffix}: ").strip().lower()

    if not response:
        return default
    return response in ("y", "yes")


def get_input(prompt: str, default: str = None, validator=None) -> str:
    """Get validated input from user."""
    while True:
        if default:
            response = input(f"{prompt} [{default}]: ").strip()
            if not response:
                response = default
        else:
            response = input(f"{prompt}: ").strip()

        if validator:
            error = validator(response)
            if error:
                print(f"  Invalid: {error}")
                continue

        return response


def get_int(prompt: str, min_val: int = None, max_val: int = None, default: int = None) -> int:
    """Get an integer from user."""
    while True:
        if default is not None:
            response = input(f"{prompt} [{default}]: ").strip()
            if not response:
                return default
        else:
            response = input(f"{prompt}: ").strip()

        try:
            value = int(response)
            if min_val is not None and value < min_val:
                print(f"  Must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"  Must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("  Please enter a number")


def get_rgb(prompt: str, default: Tuple[int, int, int] = None) -> Tuple[int, int, int]:
    """Get RGB color tuple from user."""
    while True:
        if default:
            default_str = f"{default[0]},{default[1]},{default[2]}"
            response = input(f"{prompt} (R,G,B) [{default_str}]: ").strip()
            if not response:
                return default
        else:
            response = input(f"{prompt} (R,G,B): ").strip()

        try:
            parts = [int(x.strip()) for x in response.split(",")]
            if len(parts) != 3:
                print("  Enter three values separated by commas (e.g., 100,150,200)")
                continue
            if not all(0 <= x <= 255 for x in parts):
                print("  Each value must be 0-255")
                continue
            return tuple(parts)
        except ValueError:
            print("  Enter three numbers separated by commas (e.g., 100,150,200)")


def select_from_list(prompt: str, options: List[str], allow_custom: bool = False) -> str:
    """Let user select from a list of options."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    if allow_custom:
        print(f"  {len(options) + 1}. (Other - enter custom)")

    while True:
        response = input("Choice: ").strip()
        try:
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return options[idx]
            if allow_custom and idx == len(options):
                return input("Enter custom value: ").strip()
        except ValueError:
            pass
        print("  Invalid choice")


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_card_id(card_id: str) -> Optional[str]:
    """Validate a card ID."""
    if not card_id:
        return "Card ID cannot be empty"
    if not re.match(r'^[a-z][a-z0-9_]*$', card_id):
        return "Card ID must be lowercase letters, numbers, underscores, starting with letter"

    # Check for duplicates
    try:
        from cards import ALL_CARDS
        if card_id in ALL_CARDS:
            return f"Card ID '{card_id}' already exists"
    except:
        pass

    return None


def validate_faction_constant(constant: str) -> Optional[str]:
    """Validate a faction constant name."""
    if not constant:
        return "Constant cannot be empty"
    if not re.match(r'^FACTION_[A-Z][A-Z0-9_]*$', constant):
        return "Must be like FACTION_NAME (uppercase)"
    return None


def validate_row(row: str) -> Optional[str]:
    """Validate a row type."""
    if row not in VALID_ROWS:
        return f"Must be one of: {', '.join(VALID_ROWS)}"
    return None


def validate_power(power: int) -> Optional[str]:
    """Validate power value."""
    if not 0 <= power <= 20:
        return "Power must be 0-20"
    return None


# ============================================================================
# FORMAT HELPERS - Generate code strings matching existing file formats
# ============================================================================

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

    Example output:
        "card_id": {
            "name": "Card Name",
            "faction": "Faction Name",
            "row": "row_type",
            "power": 5,
            "ability": "Ability String",
            "description": "Description text",
            "rarity": "rare"
        },
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

    Example output:
        {"name": "Leader Name", "ability": "Ability", "ability_desc": "Full desc", "card_id": "leader_id"},
    """
    if image_path:
        return f'{{"name": "{name}", "ability": "{ability}", "ability_desc": "{ability_desc}", "card_id": "{card_id}", "image_path": "{image_path}"}}'
    return f'{{"name": "{name}", "ability": "{ability}", "ability_desc": "{ability_desc}", "card_id": "{card_id}"}}'


# ============================================================================
# AST-AWARE CODE INSERTION
# ============================================================================

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
                            # Return positions from the dict value, not the assignment
                            return (node.value.col_offset, node.value.end_col_offset)
    except SyntaxError:
        pass
    return None


def find_faction_section_end(content: str, faction: str) -> int:
    """
    Find the position to insert a new card for a given faction in cards.py.

    Uses comment markers like "# --- Faction ---" and finds the last card entry
    before the next section or end of ALL_CARDS dict.
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
    """
    Insert card entry using AST-aware positioning, preserving format.

    Args:
        content: Current cards.py content
        faction: Faction name (e.g., "Tau'ri")
        card_entry: Pre-formatted card entry string

    Returns:
        Modified content with card inserted
    """
    insert_pos = find_faction_section_end(content, faction)
    return content[:insert_pos] + "\n" + card_entry + content[insert_pos:]


def insert_unlockable_entry_safely(content: str, entry: str) -> str:
    """
    Insert entry into UNLOCKABLE_CARDS dict in unlocks.py.

    Args:
        content: Current unlocks.py content
        entry: Pre-formatted unlockable entry string

    Returns:
        Modified content with entry inserted
    """
    # Find UNLOCKABLE_CARDS dict
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
    """
    Insert leader entry into BASE_FACTION_LEADERS or UNLOCKABLE_LEADERS.

    Args:
        content: Current content_registry.py content
        target_dict: "BASE_FACTION_LEADERS" or "UNLOCKABLE_LEADERS"
        faction_const: Faction constant (e.g., "FACTION_TAURI")
        leader_entry: Pre-formatted leader entry string

    Returns:
        Modified content with leader inserted
    """
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


# ============================================================================
# ENHANCED VALIDATION FUNCTIONS
# ============================================================================

def validate_card_name_unique(name: str) -> Optional[str]:
    """
    Ensure card name isn't already used by another card.

    Returns error message if duplicate found, None if unique.
    """
    try:
        from cards import ALL_CARDS
        for card in ALL_CARDS.values():
            if card.name.lower() == name.lower():
                return f"Card name '{name}' already exists (on card '{card.id}')"
    except Exception:
        pass
    return None


def validate_leader_id_prefix(card_id: str, faction: str) -> Optional[str]:
    """
    Ensure leader card_id matches faction prefix convention.

    Returns error message if mismatched, None if valid.
    """
    faction_prefixes = {
        "Tau'ri": "tauri_",
        "Goa'uld": "goauld_",
        "Jaffa Rebellion": "jaffa_",
        "Lucian Alliance": "lucian_",
        "Asgard": "asgard_",
        "Neutral": "neutral_",
    }

    expected_prefix = faction_prefixes.get(faction)
    if expected_prefix and not card_id.startswith(expected_prefix):
        return f"Leader card_id should start with '{expected_prefix}' for {faction} faction"
    return None


def validate_ability_string(ability: str) -> Optional[str]:
    """
    Check ability string against known abilities in Ability enum.

    Returns error message if ability not found, None if valid.
    """
    if not ability:
        return None

    try:
        from abilities import Ability
        valid_abilities = {a.value for a in Ability}

        # Split by comma for multi-ability cards
        abilities = [a.strip() for a in ability.split(",")]
        unknown = [a for a in abilities if a not in valid_abilities]

        if unknown:
            return f"Unknown abilities: {', '.join(unknown)}. Consider adding them first."
    except Exception:
        pass
    return None


def validate_faction_complete(faction_data: dict) -> List[str]:
    """
    Check all required faction components are defined.

    Returns list of missing/incomplete items.
    """
    issues = []

    required_keys = ["name", "constant", "base_leaders", "cards"]
    for key in required_keys:
        if key not in faction_data or not faction_data[key]:
            issues.append(f"Missing required field: {key}")

    if "base_leaders" in faction_data:
        if len(faction_data["base_leaders"]) < 3:
            issues.append(f"Need at least 3 base leaders (have {len(faction_data['base_leaders'])})")

    if "cards" in faction_data:
        if len(faction_data["cards"]) < 15:
            issues.append(f"Need at least 15 starter cards (have {len(faction_data['cards'])})")

    return issues


# ============================================================================
# INTEGRATION VERIFICATION
# ============================================================================

def verify_card_integration(card_id: str, faction: str, is_unlockable: bool) -> List[Tuple[str, bool, str]]:
    """
    Verify card is properly integrated across all systems.

    Returns list of (check_name, passed, details) tuples.
    """
    checks = []

    # Check cards.py
    try:
        if "cards" in sys.modules:
            del sys.modules["cards"]
        from cards import ALL_CARDS
        in_cards = card_id in ALL_CARDS
        checks.append(("cards.py", in_cards, f"Card {'found' if in_cards else 'NOT FOUND'} in ALL_CARDS"))
    except Exception as e:
        checks.append(("cards.py", False, f"Import error: {e}"))

    # Check card_catalog.json
    try:
        catalog_path = FILES["card_catalog"]
        if catalog_path.exists():
            catalog = json.loads(catalog_path.read_text())
            found = any(
                c["card_id"] == card_id
                for cards in catalog.values()
                for c in cards
            )
            checks.append(("card_catalog.json", found, f"Card {'found' if found else 'NOT FOUND'} in catalog"))
        else:
            checks.append(("card_catalog.json", False, "Catalog file doesn't exist"))
    except Exception as e:
        checks.append(("card_catalog.json", False, f"Error: {e}"))

    # Check asset exists
    asset_path = ROOT / "assets" / f"{card_id}.png"
    checks.append(("Asset file", asset_path.exists(), f"{asset_path.name}"))

    # Check unlocks.py if unlockable
    if is_unlockable:
        try:
            if "unlocks" in sys.modules:
                del sys.modules["unlocks"]
            from unlocks import UNLOCKABLE_CARDS
            in_unlocks = card_id in UNLOCKABLE_CARDS
            checks.append(("unlocks.py", in_unlocks, f"Card {'found' if in_unlocks else 'NOT FOUND'} in UNLOCKABLE_CARDS"))
        except Exception as e:
            checks.append(("unlocks.py", False, f"Import error: {e}"))

    return checks


def verify_leader_integration(card_id: str, faction: str) -> List[Tuple[str, bool, str]]:
    """
    Verify leader is properly integrated across all systems.

    Returns list of (check_name, passed, details) tuples.
    """
    checks = []

    # Check content_registry.py
    try:
        if "content_registry" in sys.modules:
            del sys.modules["content_registry"]
        from content_registry import LEADER_REGISTRY, LEADER_NAME_BY_ID
        in_registry = card_id in LEADER_NAME_BY_ID
        checks.append(("content_registry.py", in_registry,
                      f"Leader {'found' if in_registry else 'NOT FOUND'} in LEADER_REGISTRY"))
    except Exception as e:
        checks.append(("content_registry.py", False, f"Import error: {e}"))

    # Check leader_catalog.json
    try:
        catalog_path = FILES["leader_catalog"]
        if catalog_path.exists():
            catalog = json.loads(catalog_path.read_text())
            found = any(
                leader["card_id"] == card_id
                for faction_data in catalog.values()
                for leader_list in [faction_data.get("base", []), faction_data.get("unlockable", [])]
                for leader in leader_list
            )
            checks.append(("leader_catalog.json", found, f"Leader {'found' if found else 'NOT FOUND'} in catalog"))
        else:
            checks.append(("leader_catalog.json", False, "Catalog file doesn't exist"))
    except Exception as e:
        checks.append(("leader_catalog.json", False, f"Error: {e}"))

    # Check portrait asset
    portrait_path = ROOT / "assets" / f"{card_id}_leader.png"
    checks.append(("Portrait", portrait_path.exists(), f"{card_id}_leader.png"))

    # Check background asset
    bg_path = ROOT / "assets" / f"leader_bg_{card_id}.png"
    checks.append(("Background", bg_path.exists(), f"leader_bg_{card_id}.png"))

    return checks


def verify_faction_integration(faction_name: str, faction_const: str) -> List[Tuple[str, bool, str]]:
    """
    Comprehensive faction integration check.

    Returns list of (check_name, passed, details) tuples.
    """
    checks = []

    # Check cards.py for faction constant
    try:
        cards_content = FILES["cards"].read_text()
        has_constant = f'{faction_const} = "{faction_name}"' in cards_content
        checks.append(("Faction constant", has_constant, f"{faction_const} in cards.py"))

        # Check for faction section in ALL_CARDS
        has_section = f"# --- {faction_name} ---" in cards_content
        checks.append(("Faction section", has_section, f"Section marker in cards.py"))
    except Exception as e:
        checks.append(("cards.py", False, f"Error: {e}"))

    # Check content_registry.py
    try:
        registry_content = FILES["content_registry"].read_text()
        has_base_leaders = faction_const in registry_content and "BASE_FACTION_LEADERS" in registry_content
        checks.append(("Base leaders", has_base_leaders, f"{faction_const} in BASE_FACTION_LEADERS"))
    except Exception as e:
        checks.append(("content_registry.py", False, f"Error: {e}"))

    # Check game_config.py
    try:
        config_content = FILES["game_config"].read_text()
        has_ui_color = f'"{faction_name}"' in config_content
        checks.append(("UI colors", has_ui_color, f"Faction in FACTION_UI_COLORS"))
    except Exception as e:
        checks.append(("game_config.py", False, f"Error: {e}"))

    # Check create_placeholders.py
    try:
        placeholders_content = FILES["create_placeholders"].read_text()
        has_colors = faction_const in placeholders_content
        checks.append(("Placeholder colors", has_colors, f"{faction_const} in create_placeholders.py"))
    except Exception as e:
        checks.append(("create_placeholders.py", False, f"Error: {e}"))

    return checks


def print_verification_results(checks: List[Tuple[str, bool, str]]):
    """Print verification results in a formatted table."""
    print("\n=== INTEGRATION VERIFICATION ===")
    all_passed = True
    for check_name, passed, details in checks:
        status = "[OK]" if passed else "[!!]"
        print(f"  {status} {check_name}: {details}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  All checks passed!")
    else:
        print("\n  Some checks failed - manual review may be needed")

    return all_passed


# ============================================================================
# CODE PARSING HELPERS
# ============================================================================

def get_existing_factions() -> List[str]:
    """Get list of existing faction names."""
    try:
        from cards import (
            FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
            FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL
        )
        return [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
                FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL]
    except:
        return ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard", "Neutral"]


def get_existing_faction_constants() -> Dict[str, str]:
    """Get mapping of faction constant names to values."""
    content = FILES["cards"].read_text()

    constants = {}
    pattern = r'^(FACTION_\w+)\s*=\s*["\']([^"\']+)["\']'
    for match in re.finditer(pattern, content, re.MULTILINE):
        constants[match.group(1)] = match.group(2)

    return constants


def get_existing_abilities() -> List[str]:
    """Get list of existing ability names from Ability enum."""
    try:
        from abilities import Ability
        return [a.value for a in Ability]
    except:
        return []


def get_all_cards() -> Dict[str, Any]:
    """Get all cards from cards.py."""
    try:
        from cards import ALL_CARDS
        return ALL_CARDS
    except:
        return {}


def find_insertion_point_for_card(content: str, faction: str) -> int:
    """Find the position to insert a new card in cards.py."""
    # Look for the faction section marker (e.g., "# --- Tau'ri ---")
    pattern = rf'#\s*---\s*{re.escape(faction)}\s*---'
    match = re.search(pattern, content, re.IGNORECASE)

    if match:
        # Find the last card entry for this faction before the next section
        start_pos = match.end()
        next_section = re.search(r'\n\s*#\s*---', content[start_pos:])

        if next_section:
            end_pos = start_pos + next_section.start()
        else:
            # Find end of ALL_CARDS dict
            end_pos = content.rfind("}")

        # Find the last complete card entry
        section = content[start_pos:end_pos]
        last_entry = section.rfind("),")
        if last_entry != -1:
            return start_pos + last_entry + 2

    # Fallback: before the closing brace of ALL_CARDS
    close_brace = content.rfind("}")
    if close_brace != -1:
        # Find the line before the closing brace
        newline_before = content.rfind("\n", 0, close_brace)
        return newline_before if newline_before != -1 else close_brace

    return len(content)


# ============================================================================
# MENU OPTION 1: ADD NEW CARD
# ============================================================================

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
        # Use same prefix validation for cards
        expected_prefix = card_id.split("_")[0] + "_"
        faction_prefix = faction.lower().replace("'", "").replace(" ", "_")[:8]
        if not card_id.startswith(faction_prefix):
            print(f"  Note: Card ID doesn't start with faction prefix '{faction_prefix}_'")
            if not confirm("Continue anyway?", default=True):
                return

    power = get_int("Power (0-15)", min_val=0, max_val=15, default=5)

    row = select_from_list("Select Row:", VALID_ROWS[:4])  # close, ranged, siege, agile

    abilities = get_existing_abilities()
    ability = select_from_list("Select Ability (or None):", ["None"] + abilities[:15], allow_custom=True)
    if ability == "None":
        ability = None

    # Validate ability string if provided
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

    # Use format helpers to generate properly formatted code
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
        # Use AST-aware insertion
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
            # Use safe insertion helper
            return insert_unlockable_entry_safely(content, unlockable_code)

        if not safe_modify_file(FILES["unlocks"], modify_unlocks_py, f"Added unlockable {card_id}"):
            # Rollback cards.py
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
        # force=True since this is a newly created card
        generate_card_placeholder(card_id, card_name, faction, power, row, force=True)

    # === VERIFICATION ===
    checks = verify_card_integration(card_id, faction, is_unlockable)
    print_verification_results(checks)

    log(f"SESSION COMPLETE - Card '{card_name}' ({card_id}) added")


# ============================================================================
# MENU OPTION 2: ADD NEW LEADER
# ============================================================================

def add_leader_workflow():
    """Interactive workflow to add a new leader."""
    print_header("ADD NEW LEADER")

    # Collect leader information
    print("Enter leader details:\n")

    card_id = get_input("Card ID (e.g., tauri_newleader)", validator=validate_card_id)
    name = get_input("Leader Name (e.g., Dr. New Character)")

    factions = get_existing_factions()[:-1]  # Exclude Neutral
    faction = select_from_list("Select Faction:", factions)

    # Validate leader card_id matches faction prefix
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
        # Find the faction constant
        faction_const = None
        for const, val in get_existing_faction_constants().items():
            if val == faction:
                faction_const = const
                break

        if not faction_const:
            raise ValueError(f"Could not find faction constant for {faction}")

        # Find the right dict to insert into
        target_dict = "UNLOCKABLE_LEADERS" if is_unlockable else "BASE_FACTION_LEADERS"

        # Find the faction's list in the target dict
        pattern = rf'({target_dict}\s*=\s*\{{[^}}]*{faction_const}\s*:\s*\[)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            # Find the closing bracket of this list
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
            # Find last entry
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
                # Find end of dict
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
        # force=True since this is a newly created leader
        generate_leader_placeholders(card_id, name, faction, force=True)

    # === VERIFICATION ===
    checks = verify_leader_integration(card_id, faction)
    print_verification_results(checks)

    print(f"\n     Type: {'Unlockable' if is_unlockable else 'Base'}")
    print(f"     Faction: {faction}")

    log(f"SESSION COMPLETE - Leader '{name}' ({card_id}) added")


# ============================================================================
# MENU OPTION 3: ADD NEW FACTION
# ============================================================================

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

        if card is None:  # User entered 'done'
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

    # Step 1: cards.py - Add faction constant and cards
    print("\n=== Modifying cards.py ===")
    if not add_faction_to_cards_py(faction_name, faction_constant, cards):
        return

    # Step 2: content_registry.py - Add leaders
    print("\n=== Modifying content_registry.py ===")
    if not add_faction_to_content_registry(faction_name, faction_constant,
                                            base_leaders, unlock_leaders):
        restore_from_backup(FILES["cards"])
        return

    # Step 3: deck_persistence.py - Add default deck
    print("\n=== Modifying deck_persistence.py ===")
    if not add_faction_to_deck_persistence(faction_name, base_leaders[0]["card_id"]):
        restore_from_backup(FILES["cards"])
        restore_from_backup(FILES["content_registry"])
        return

    # Step 4: game_config.py - Add colors
    print("\n=== Modifying game_config.py ===")
    if not add_faction_to_game_config(faction_name, faction_constant,
                                       primary_color, glow_color):
        print("  Warning: Could not update game_config.py")

    # Step 5: power.py - Add faction power stub
    print("\n=== Modifying power.py ===")
    if not add_faction_power_stub(faction_name, power_name, power_desc):
        print("  Warning: Could not update power.py - manual implementation needed")

    # Step 6: create_placeholders.py - Add colors
    print("\n=== Modifying create_placeholders.py ===")
    if not add_faction_to_placeholders_script(faction_name, faction_constant, primary_color):
        print("  Warning: Could not update create_placeholders.py")

    # Step 7: Update JSON catalogs
    print("\n=== Updating documentation ===")
    update_catalogs_for_faction(faction_name, faction_constant, cards,
                                base_leaders, unlock_leaders)

    # Step 8: Generate placeholders
    print("\n=== Generating placeholder assets ===")
    if confirm("Generate all placeholder images for this faction?"):
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


def collect_leader_info(faction_name: str, is_base: bool) -> dict:
    """Collect information for a single leader."""
    name = get_input("Leader Name")

    # Generate card ID suggestion
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
        # Add faction constant after other constants
        constants_end = content.find("# Card Database")
        if constants_end == -1:
            constants_end = content.find("ALL_CARDS")

        new_constant = f'{faction_constant} = "{faction_name}"\n'
        content = content[:constants_end] + new_constant + content[constants_end:]

        # Add cards section
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
            # Add new constant to imports
            import_end = match.end()
            if faction_constant not in content[:import_end + 50]:
                comma_pos = content.rfind(",", match.start(), import_end)
                if comma_pos != -1:
                    content = content[:comma_pos + 1] + f"\n    {faction_constant}," + content[comma_pos + 1:]

        # Add to BASE_FACTION_LEADERS
        base_pattern = r'(BASE_FACTION_LEADERS\s*=\s*\{)'
        match = re.search(base_pattern, content)
        if match:
            # Find end of dict
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
        # Find _get_default_deck_data method
        pattern = r'(def _get_default_deck_data.*?return \{[^}]+)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            end = match.end()
            # Find position before the closing brace
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
        # Add to FACTION_UI_COLORS
        pattern = r'(FACTION_UI_COLORS\s*=\s*\{[^}]+)'
        match = re.search(pattern, content)
        if match:
            end = match.end()
            closing = content.find("}", end)
            new_line = f'\n    "{faction_name}": {primary_color},'
            content = content[:closing] + new_line + content[closing:]

        # Add to FACTION_GLOW_COLORS
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
        # Find FACTION_POWERS dict
        pattern = r'(FACTION_POWERS\s*=\s*\{)'
        match = re.search(pattern, content)

        if match:
            # Insert class before the dict
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

            # Add to FACTION_POWERS dict
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
        # Add to FACTION_COLORS
        pattern = r'(FACTION_COLORS\s*=\s*\{[^}]+)'
        match = re.search(pattern, content)
        if match:
            end = match.end()
            closing = content.find("}", end)
            new_line = f'\n    {faction_constant}: {primary_color},'
            content = content[:closing] + new_line + content[closing:]

        # Add to FACTION_BACKGROUND_IDS
        pattern = r'(FACTION_BACKGROUND_IDS\s*=\s*\{[^}]+)'
        match = re.search(pattern, content)
        if match:
            end = match.end()
            closing = content.find("}", end)
            bg_id = faction_name.lower().replace(" ", "_").replace("'", "")
            new_line = f'\n    {faction_constant}: "{bg_id}",'
            content = content[:closing] + new_line + content[closing:]

        # Add to FACTION_NAME_ALIASES for common variations
        pattern = r'(FACTION_NAME_ALIASES\s*=\s*\{)'
        match = re.search(pattern, content)
        if match:
            # Find the closing brace of the dict
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

            # Generate common aliases
            clean_name = faction_name.replace("'", "").replace(" ", "")
            short_name = faction_name.split()[0] if " " in faction_name else faction_name

            aliases = [
                f'    {faction_constant}: {faction_constant},',
                f'    "{faction_name}": {faction_constant},',
            ]
            # Add short name alias if different
            if short_name != faction_name:
                aliases.append(f'    "{short_name}": {faction_constant},')
            # Add clean name alias if different
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

    # Update card_catalog.json
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

    # Update leader_catalog.json
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


# ============================================================================
# MENU OPTION 4: ABILITY MANAGER
# ============================================================================

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

    # Add to abilities.py
    def modify_abilities(content: str) -> str:
        # Find the Ability enum class and the first function after it
        # The pattern finds where 'def ' starts after the enum (marking end of enum values)
        class_start = content.find("class Ability(Enum):")
        if class_start == -1:
            raise ValueError("Could not find Ability enum class in abilities.py")

        # Find the first function definition after the class
        func_start = content.find("\ndef ", class_start)
        if func_start == -1:
            func_start = len(content)

        # Find the last enum value assignment before the function
        enum_section = content[class_start:func_start]
        last_equals = enum_section.rfind(" = ")

        if last_equals == -1:
            raise ValueError("Could not find any enum values in Ability class")

        # Find end of that line
        absolute_pos = class_start + last_equals
        line_end = content.find('\n', absolute_pos)

        # Insert new enum value after the last one
        new_line = f'\n    {enum_name} = "{ability_name}"'
        content = content[:line_end] + new_line + content[line_end:]

        return content

    if safe_modify_file(FILES["abilities"], modify_abilities, f"Added ability {ability_name}"):
        print(f"[OK] Added {ability_name} to abilities.py")

    # Add to generate_rules_spec.py
    def modify_rules(content: str) -> str:
        pattern = r'(def build_ability_info\(\):.*?return \{)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            # Find the closing brace of the return dict
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
        # Find the leader entry
        pattern = rf'"card_id":\s*"{card_id}"'
        match = re.search(pattern, content)

        if match:
            # Find the containing dict
            start = content.rfind("{", 0, match.start())
            end = content.find("}", match.end()) + 1

            old_entry = content[start:end]

            # Replace ability and ability_desc
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
        # Find the card entry
        pattern = rf'("{card_id}":\s*Card\([^)]+\))'
        match = re.search(pattern, content)

        if match:
            old_entry = match.group(1)

            # Parse the existing entry and update ability
            # Simple regex replacement for the ability parameter
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


# ============================================================================
# MENU OPTION 5: PLACEHOLDER GENERATION
# ============================================================================

# Global settings for placeholder generation
_placeholder_skip_existing = False
_placeholder_overwrite_all = False
_placeholder_asked_once = False


def reset_placeholder_settings():
    """Reset placeholder generation settings for a new session."""
    global _placeholder_skip_existing, _placeholder_overwrite_all, _placeholder_asked_once
    _placeholder_skip_existing = False
    _placeholder_overwrite_all = False
    _placeholder_asked_once = False


def should_create_placeholder(file_path: Path) -> bool:
    """
    Check if we should create/overwrite this placeholder file.

    Similar to the logic in create_placeholders.py:
    - If file doesn't exist, always create
    - If overwrite_all is set, always create
    - If skip_existing is set, never create
    - Otherwise, ask user preference
    """
    global _placeholder_skip_existing, _placeholder_overwrite_all, _placeholder_asked_once

    if not file_path.exists():
        return True  # File doesn't exist, create it

    # If user already chose to overwrite all or skip all
    if _placeholder_overwrite_all:
        return True
    if _placeholder_skip_existing:
        return False

    # Ask user on first existing file
    if not _placeholder_asked_once:
        _placeholder_asked_once = True
        print("\n" + "=" * 60)
        print("EXISTING FILES DETECTED")
        print("=" * 60)
        print("Some asset files already exist in the assets folder.")
        print("What would you like to do?")
        print()
        print("  [O] Overwrite ALL existing files (replace with placeholders)")
        print("  [S] Skip ALL existing files (keep your custom artwork)")
        print("  [A] Ask for each file individually")
        print()

        while True:
            choice = input("Your choice (O/S/A): ").strip().upper()
            if choice == 'O':
                _placeholder_overwrite_all = True
                print("  Will overwrite all existing files\n")
                return True
            elif choice == 'S':
                _placeholder_skip_existing = True
                print("  Will skip all existing files\n")
                return False
            elif choice == 'A':
                print("  Will ask for each file\n")
                break
            else:
                print("Invalid choice. Please enter O, S, or A.")

    # Ask for this specific file
    filename = file_path.name
    while True:
        choice = input(f"File exists: {filename} - Overwrite? (y/n): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print("Please enter 'y' or 'n'.")


def placeholder_generation_workflow():
    """Generate placeholder images."""
    print_header("PLACEHOLDER GENERATION")

    print("  1. Generate ALL placeholders (run create_placeholders.py)")
    print("  2. Generate for specific card")
    print("  3. Generate for specific leader")
    print("  4. Generate for specific faction")
    print("  0. Back")
    print()

    choice = get_input("Choice", default="0")

    # Reset settings for fresh session
    reset_placeholder_settings()

    if choice == "1":
        run_create_placeholders_script()
    elif choice == "2":
        card_id = get_input("Card ID")
        try:
            from cards import ALL_CARDS
            if card_id in ALL_CARDS:
                card = ALL_CARDS[card_id]
                generate_card_placeholder(card_id, card.name, card.faction,
                                          card.power, card.row)
            else:
                print(f"Card {card_id} not found")
        except Exception as e:
            print(f"Error: {e}")
    elif choice == "3":
        card_id = get_input("Leader Card ID")
        name = get_input("Leader Name")
        faction = select_from_list("Faction:", get_existing_factions()[:-1])
        generate_leader_placeholders(card_id, name, faction)
    elif choice == "4":
        faction = select_from_list("Faction:", get_existing_factions())
        generate_all_faction_placeholders(faction)


def run_create_placeholders_script():
    """Run the create_placeholders.py script."""
    import subprocess

    print("\nRunning create_placeholders.py...")
    print("(The original script has its own skip/overwrite options)")
    print()

    result = subprocess.run(
        [sys.executable, str(FILES["create_placeholders"])],
        cwd=str(ROOT)
    )

    if result.returncode == 0:
        print("\n[OK] Placeholders generated successfully")
    else:
        print(f"\n[ERROR] Script exited with code {result.returncode}")


def generate_card_placeholder(card_id: str, name: str, faction: str,
                              power: int, row: str, force: bool = False):
    """
    Generate a single card placeholder.

    Args:
        card_id: The card identifier
        name: Card display name
        faction: Faction name
        power: Card power value
        row: Card row type
        force: If True, skip the overwrite check (for new cards)
    """
    try:
        import pygame
        pygame.init()

        assets_dir = ROOT / "assets"
        assets_dir.mkdir(exist_ok=True)
        path = assets_dir / f"{card_id}.png"

        # Check if we should create this file (unless forced)
        if not force and not should_create_placeholder(path):
            print(f"  Skipped: {card_id}.png (already exists)")
            return False

        CARD_WIDTH, CARD_HEIGHT = 200, 280

        # Faction colors
        faction_colors = {
            "Tau'ri": (50, 100, 180),
            "Goa'uld": (200, 40, 60),
            "Jaffa Rebellion": (215, 170, 60),
            "Lucian Alliance": (220, 80, 170),
            "Asgard": (150, 150, 200),
            "Neutral": (120, 120, 120),
        }

        surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
        color = faction_colors.get(faction, (100, 100, 100))
        surface.fill(color)

        pygame.draw.rect(surface, (255, 255, 255), surface.get_rect(), width=2, border_radius=10)

        font = pygame.font.SysFont("Arial", 28, bold=True)
        title = font.render(name[:20], True, (255, 255, 255))
        title_rect = title.get_rect(center=(CARD_WIDTH / 2, 20))
        surface.blit(title, title_rect)

        if row not in ["special", "weather"]:
            power_font = pygame.font.SysFont("Arial", 40, bold=True)
            power_text = power_font.render(str(power), True, (0, 0, 0))
            pygame.draw.circle(surface, (255, 255, 255), (30, 50), 20)
            power_rect = power_text.get_rect(center=(30, 50))
            surface.blit(power_text, power_rect)

        pygame.image.save(surface, str(path))

        log(f"ASSET CREATED: {path}")
        print(f"[OK] Created {path}")
        return True

    except Exception as e:
        print(f"[ERROR] Could not generate placeholder: {e}")
        return False


def generate_leader_placeholders(card_id: str, name: str, faction: str, force: bool = False):
    """
    Generate leader portrait and background placeholders.

    Args:
        card_id: The leader card identifier
        name: Leader display name
        faction: Faction name
        force: If True, skip the overwrite check (for new leaders)
    """
    try:
        import pygame
        pygame.init()

        faction_colors = {
            "Tau'ri": (50, 100, 180),
            "Goa'uld": (200, 40, 60),
            "Jaffa Rebellion": (215, 170, 60),
            "Lucian Alliance": (220, 80, 170),
            "Asgard": (150, 150, 200),
        }

        color = faction_colors.get(faction, (100, 100, 100))
        assets_dir = ROOT / "assets"
        assets_dir.mkdir(exist_ok=True)

        # Leader portrait
        portrait_path = assets_dir / f"{card_id}_leader.png"

        if force or should_create_placeholder(portrait_path):
            LEADER_WIDTH, LEADER_HEIGHT = 200, 280
            surface = pygame.Surface((LEADER_WIDTH, LEADER_HEIGHT))

            for y in range(LEADER_HEIGHT):
                brightness = 1.0 - (y / LEADER_HEIGHT) * 0.3
                shade = tuple(int(c * brightness) for c in color)
                pygame.draw.line(surface, shade, (0, y), (LEADER_WIDTH, y))

            pygame.draw.rect(surface, (255, 215, 0), surface.get_rect(), width=4, border_radius=5)

            font = pygame.font.SysFont("Arial", 18, bold=True)
            leader_text = font.render("LEADER", True, (255, 215, 0))
            text_rect = leader_text.get_rect(center=(LEADER_WIDTH // 2, 20))
            surface.blit(leader_text, text_rect)

            name_font = pygame.font.SysFont("Arial", 14, bold=True)
            name_text = name_font.render(name[:20], True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(LEADER_WIDTH // 2, LEADER_HEIGHT - 20))
            pygame.draw.rect(surface, (0, 0, 0), name_rect.inflate(10, 5))
            surface.blit(name_text, name_rect)

            pygame.image.save(surface, str(portrait_path))
            log(f"ASSET CREATED: {portrait_path}")
            print(f"[OK] Created {portrait_path}")
        else:
            print(f"  Skipped: {card_id}_leader.png (already exists)")

        # Leader background
        bg_path = assets_dir / f"leader_bg_{card_id}.png"

        if force or should_create_placeholder(bg_path):
            BOARD_WIDTH, BOARD_HEIGHT = 3840, 2160
            bg_surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

            for y in range(BOARD_HEIGHT):
                progress = y / BOARD_HEIGHT
                bg_color = tuple(int(c * (1 - progress * 0.3)) for c in color)
                pygame.draw.line(bg_surface, bg_color, (0, y), (BOARD_WIDTH, y))

            pygame.image.save(bg_surface, str(bg_path))
            log(f"ASSET CREATED: {bg_path}")
            print(f"[OK] Created {bg_path}")
        else:
            print(f"  Skipped: leader_bg_{card_id}.png (already exists)")

    except Exception as e:
        print(f"[ERROR] Could not generate placeholders: {e}")


def generate_all_faction_placeholders(faction: str):
    """Generate placeholders for all content of a faction."""
    print(f"\nGenerating all placeholders for {faction}...")

    try:
        from cards import ALL_CARDS

        count = 0
        for card_id, card in ALL_CARDS.items():
            if card.faction == faction:
                generate_card_placeholder(card_id, card.name, card.faction,
                                          card.power, card.row)
                count += 1

        print(f"\n[OK] Generated {count} card placeholders for {faction}")

    except Exception as e:
        print(f"[ERROR] {e}")


def generate_faction_placeholders(faction_name: str, faction_constant: str,
                                   cards: List[dict], leaders: List[dict]):
    """
    Generate all placeholders for a new faction.

    Note: Uses force=True because these are newly created content items
    that should always be generated (no need to ask about overwriting).
    """
    print("\nGenerating card placeholders...")
    for card in cards:
        generate_card_placeholder(card["card_id"], card["name"], faction_name,
                                  card["power"], card["row"], force=True)

    print("\nGenerating leader placeholders...")
    for leader in leaders:
        generate_leader_placeholders(leader["card_id"], leader["name"], faction_name, force=True)


# ============================================================================
# MENU OPTION 6: DOCUMENTATION REGENERATION
# ============================================================================

def regenerate_documentation():
    """Regenerate all documentation files."""
    print_header("REGENERATE DOCUMENTATION")

    print("This will:")
    print("  1. Run generate_rules_spec.py")
    print("  2. Rebuild card_catalog.json from cards.py")
    print("  3. Rebuild leader_catalog.json from content_registry.py")
    print()

    if not confirm("Proceed?"):
        return

    # Run generate_rules_spec.py
    print("\n=== Running generate_rules_spec.py ===")
    import subprocess
    result = subprocess.run(
        [sys.executable, str(FILES["generate_rules_spec"])],
        cwd=str(ROOT)
    )

    if result.returncode == 0:
        print("[OK] Rules spec regenerated")
    else:
        print(f"[WARNING] generate_rules_spec.py returned {result.returncode}")

    # Rebuild card_catalog.json
    print("\n=== Rebuilding card_catalog.json ===")
    rebuild_card_catalog()

    # Rebuild leader_catalog.json
    print("\n=== Rebuilding leader_catalog.json ===")
    rebuild_leader_catalog()

    print("\n[OK] Documentation regenerated!")


def rebuild_card_catalog():
    """Rebuild card_catalog.json from cards.py."""
    try:
        # Force reimport
        if "cards" in sys.modules:
            del sys.modules["cards"]

        from cards import ALL_CARDS

        catalog = defaultdict(list)

        for card_id, card in ALL_CARDS.items():
            catalog[card.faction].append({
                "card_id": card_id,
                "name": card.name,
                "faction": card.faction,
                "power": card.power,
                "row": card.row,
                "ability": card.ability
            })

        # Sort by power within each faction
        for faction in catalog:
            catalog[faction].sort(key=lambda c: (-c["power"], c["name"]))

        FILES["card_catalog"].write_text(json.dumps(dict(catalog), indent=2))
        print(f"[OK] Rebuilt {FILES['card_catalog']}")

    except Exception as e:
        print(f"[ERROR] Could not rebuild card catalog: {e}")


def rebuild_leader_catalog():
    """Rebuild leader_catalog.json from content_registry.py."""
    try:
        # Force reimport
        if "content_registry" in sys.modules:
            del sys.modules["content_registry"]

        from content_registry import BASE_FACTION_LEADERS, UNLOCKABLE_LEADERS
        from cards import FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD

        faction_map = {
            FACTION_TAURI: "FACTION_TAURI",
            FACTION_GOAULD: "FACTION_GOAULD",
            FACTION_JAFFA: "FACTION_JAFFA",
            FACTION_LUCIAN: "FACTION_LUCIAN",
            FACTION_ASGARD: "FACTION_ASGARD",
        }

        catalog = {}

        for faction, const in faction_map.items():
            catalog[const] = {
                "base": BASE_FACTION_LEADERS.get(faction, []),
                "unlockable": UNLOCKABLE_LEADERS.get(faction, [])
            }

        FILES["leader_catalog"].write_text(json.dumps(catalog, indent=2))
        print(f"[OK] Rebuilt {FILES['leader_catalog']}")

    except Exception as e:
        print(f"[ERROR] Could not rebuild leader catalog: {e}")


# ============================================================================
# MENU OPTION 7: ASSET CHECKER
# ============================================================================

def asset_checker_workflow():
    """Check for missing or orphaned assets."""
    print_header("ASSET CHECKER")

    assets_dir = ROOT / "assets"

    if not assets_dir.exists():
        print(f"Assets directory not found: {assets_dir}")
        return

    # Get all expected card images
    try:
        from cards import ALL_CARDS
    except:
        print("Could not import cards.py")
        return

    # Get all existing image files
    existing_images = {f.stem for f in assets_dir.glob("*.png")}

    # Expected card images
    expected_cards = set(ALL_CARDS.keys())

    # Check for missing card images
    missing_cards = expected_cards - existing_images

    # Check for orphaned images (images without matching cards)
    # Exclude known non-card images
    known_non_cards = {
        "board_background", "menu_background", "card_back", "decoy",
        "deck_building_bg", "stats_menu_bg", "options_menu_bg",
        "draft_mode_bg", "mulligan_bg", "rule_menu_bg",
        "universal_leader_matchup_bg", "lobby_background"
    }

    # Leader images and backgrounds
    leader_images = {f.stem for f in assets_dir.glob("*_leader.png")}
    leader_bgs = {f.stem for f in assets_dir.glob("leader_bg_*.png")}
    faction_bgs = {f.stem for f in assets_dir.glob("faction_bg_*.png")}

    non_card_images = known_non_cards | {f.replace("_leader", "") for f in leader_images}
    non_card_images |= {f.replace("leader_bg_", "") for f in leader_bgs}
    non_card_images |= faction_bgs

    orphaned = existing_images - expected_cards - non_card_images - leader_images - leader_bgs - faction_bgs

    # Report
    print(f"\n=== ASSET CHECK REPORT ===\n")
    print(f"Total cards in code: {len(expected_cards)}")
    print(f"Total images in assets/: {len(existing_images)}")

    if missing_cards:
        print(f"\n[!] MISSING CARD IMAGES ({len(missing_cards)}):")
        for card_id in sorted(missing_cards)[:20]:
            print(f"    - {card_id}.png")
        if len(missing_cards) > 20:
            print(f"    ... and {len(missing_cards) - 20} more")
    else:
        print(f"\n[OK] All card images present")

    if orphaned:
        print(f"\n[?] POSSIBLY ORPHANED IMAGES ({len(orphaned)}):")
        for img in sorted(orphaned)[:10]:
            print(f"    - {img}.png")
        if len(orphaned) > 10:
            print(f"    ... and {len(orphaned) - 10} more")

    # Check image sizes
    print(f"\n=== IMAGE SIZE CHECK ===")
    standard_card_size = (200, 280)
    wrong_size = []

    try:
        import pygame
        pygame.init()

        for card_id in list(expected_cards)[:50]:  # Check first 50
            path = assets_dir / f"{card_id}.png"
            if path.exists():
                img = pygame.image.load(str(path))
                if img.get_size() != standard_card_size:
                    wrong_size.append((card_id, img.get_size()))

        if wrong_size:
            print(f"\n[!] NON-STANDARD SIZE CARDS:")
            for card_id, size in wrong_size[:10]:
                print(f"    - {card_id}: {size} (expected {standard_card_size})")
        else:
            print(f"[OK] All checked cards have standard size")

    except Exception as e:
        print(f"Could not check image sizes: {e}")


# ============================================================================
# MENU OPTION 8: BALANCE ANALYZER
# ============================================================================

def balance_analyzer_workflow():
    """Analyze game balance statistics."""
    print_header("BALANCE ANALYZER")

    try:
        from cards import ALL_CARDS
    except:
        print("Could not import cards.py")
        return

    # Collect statistics
    faction_stats = defaultdict(lambda: {"count": 0, "total_power": 0, "powers": []})
    row_stats = defaultdict(lambda: {"count": 0, "total_power": 0, "powers": []})
    ability_counts = defaultdict(int)

    for card_id, card in ALL_CARDS.items():
        if card.row in ["special", "weather"]:
            continue

        faction_stats[card.faction]["count"] += 1
        faction_stats[card.faction]["total_power"] += card.power
        faction_stats[card.faction]["powers"].append(card.power)

        row_stats[card.row]["count"] += 1
        row_stats[card.row]["total_power"] += card.power
        row_stats[card.row]["powers"].append(card.power)

        if card.ability:
            for ability in card.ability.split(", "):
                ability_counts[ability.strip()] += 1

    # Display faction stats
    print("\n=== FACTION POWER DISTRIBUTION ===\n")
    print(f"{'Faction':<20} {'Cards':>6} {'Total':>7} {'Avg':>6} {'Min':>5} {'Max':>5}")
    print("-" * 55)

    for faction, stats in sorted(faction_stats.items()):
        if stats["count"] > 0:
            avg = stats["total_power"] / stats["count"]
            min_p = min(stats["powers"])
            max_p = max(stats["powers"])
            print(f"{faction:<20} {stats['count']:>6} {stats['total_power']:>7} {avg:>6.1f} {min_p:>5} {max_p:>5}")

    # Display row stats
    print("\n=== ROW POWER DISTRIBUTION ===\n")
    print(f"{'Row':<12} {'Cards':>6} {'Total':>7} {'Avg':>6}")
    print("-" * 35)

    for row, stats in sorted(row_stats.items()):
        if stats["count"] > 0:
            avg = stats["total_power"] / stats["count"]
            print(f"{row:<12} {stats['count']:>6} {stats['total_power']:>7} {avg:>6.1f}")

    # Display ability frequency
    print("\n=== ABILITY FREQUENCY ===\n")
    print(f"{'Ability':<35} {'Count':>6}")
    print("-" * 45)

    for ability, count in sorted(ability_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"{ability:<35} {count:>6}")

    # Identify outliers
    print("\n=== POTENTIAL OUTLIERS ===\n")

    all_powers = [c.power for c in ALL_CARDS.values() if c.row not in ["special", "weather"]]
    avg_power = sum(all_powers) / len(all_powers) if all_powers else 0

    high_power = [(cid, c) for cid, c in ALL_CARDS.items()
                  if c.power > avg_power + 5 and c.row not in ["special", "weather"]]

    if high_power:
        print("High power cards (5+ above average):")
        for card_id, card in sorted(high_power, key=lambda x: -x[1].power)[:10]:
            print(f"  - {card.name} ({card.faction}): {card.power} power")


# ============================================================================
# MENU OPTION 9: SAVE MANAGER
# ============================================================================

def save_manager_workflow():
    """Backup and restore player saves."""
    print_header("SAVE MANAGER")

    print("  1. Backup current saves")
    print("  2. Restore from backup")
    print("  3. View current progress")
    print("  4. Reset to fresh start")
    print("  0. Back")
    print()

    choice = get_input("Choice", default="0")

    if choice == "1":
        backup_saves()
    elif choice == "2":
        restore_saves()
    elif choice == "3":
        view_save_progress()
    elif choice == "4":
        reset_saves()


def backup_saves():
    """Backup player save files."""
    save_files = [
        ROOT / "player_unlocks.json",
        ROOT / "player_decks.json",
        ROOT / "player_stats.json"
    ]

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_DIR / f"saves_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backed_up = 0
    for save_file in save_files:
        if save_file.exists():
            shutil.copy2(save_file, backup_dir / save_file.name)
            backed_up += 1
            print(f"  Backed up: {save_file.name}")

    print(f"\n[OK] Backed up {backed_up} files to {backup_dir}")


def restore_saves():
    """Restore saves from a backup."""
    if not BACKUP_DIR.exists():
        print("No backup directory found")
        return

    # Find save backups
    save_backups = sorted([d for d in BACKUP_DIR.iterdir()
                          if d.is_dir() and d.name.startswith("saves_")])

    if not save_backups:
        print("No save backups found")
        return

    print("\nAvailable backups:")
    for i, backup in enumerate(save_backups[-10:], 1):
        print(f"  {i}. {backup.name}")

    choice = get_int("Select backup", min_val=1, max_val=len(save_backups[-10:]))
    selected = save_backups[-10:][choice - 1]

    if not confirm(f"Restore from {selected.name}? This will overwrite current saves."):
        return

    for save_file in selected.iterdir():
        if save_file.suffix == ".json":
            shutil.copy2(save_file, ROOT / save_file.name)
            print(f"  Restored: {save_file.name}")

    print("\n[OK] Saves restored")


def view_save_progress():
    """Display current unlock progress."""
    unlocks_file = ROOT / "player_unlocks.json"

    if not unlocks_file.exists():
        print("No unlock data found")
        return

    data = json.loads(unlocks_file.read_text())

    print("\n=== PLAYER PROGRESS ===\n")
    print(f"Total Games: {data.get('total_games', 0)}")
    print(f"Total Wins: {data.get('total_wins', 0)}")
    print(f"Current Win Streak: {data.get('consecutive_wins', 0)}")
    print(f"Max Win Streak: {data.get('max_streak', 0)}")

    unlocked_cards = data.get('unlocked', [])
    print(f"\nUnlocked Cards: {len(unlocked_cards)}")

    unlocked_leaders = data.get('unlocked_leaders', {})
    total_leaders = sum(len(v) for v in unlocked_leaders.values())
    print(f"Unlocked Leaders: {total_leaders}")


def reset_saves():
    """Reset all save data."""
    if not confirm("This will DELETE all player progress. Are you sure?", default=False):
        return

    if not confirm("This cannot be undone. Really delete?", default=False):
        return

    # Backup first
    backup_saves()

    # Delete save files
    save_files = [
        ROOT / "player_unlocks.json",
        ROOT / "player_decks.json",
        ROOT / "player_stats.json"
    ]

    for save_file in save_files:
        if save_file.exists():
            save_file.unlink()
            print(f"  Deleted: {save_file.name}")

    print("\n[OK] Save data reset. A backup was created first.")


# ============================================================================
# MENU OPTION 10: DECK IMPORT/EXPORT
# ============================================================================

def deck_import_export_workflow():
    """Import and export deck configurations."""
    print_header("DECK IMPORT/EXPORT")

    print("  1. Export deck to text")
    print("  2. Export deck to JSON file")
    print("  3. Import deck from text")
    print("  4. Import deck from JSON file")
    print("  0. Back")
    print()

    choice = get_input("Choice", default="0")

    if choice == "1":
        export_deck_text()
    elif choice == "2":
        export_deck_json()
    elif choice == "3":
        import_deck_text()
    elif choice == "4":
        import_deck_json()


def export_deck_text():
    """Export a deck to shareable text format."""
    decks_file = ROOT / "player_decks.json"

    if not decks_file.exists():
        print("No deck data found")
        return

    decks = json.loads(decks_file.read_text())

    faction = select_from_list("Select faction:", list(decks.keys()))
    deck = decks[faction]

    print("\n=== DECK EXPORT ===")
    print(f"# {faction} Deck")
    print(f"# Leader: {deck.get('leader', 'None')}")
    print(f"# Cards: {len(deck.get('cards', []))}")
    print()

    for card_id in deck.get('cards', []):
        print(card_id)

    print("\n(Copy the above text to share)")


def export_deck_json():
    """Export a deck to JSON file."""
    decks_file = ROOT / "player_decks.json"

    if not decks_file.exists():
        print("No deck data found")
        return

    decks = json.loads(decks_file.read_text())

    faction = select_from_list("Select faction:", list(decks.keys()))
    deck = decks[faction]

    export_path = ROOT / f"exported_deck_{faction.lower().replace(' ', '_')}.json"

    export_data = {
        "faction": faction,
        "leader": deck.get("leader"),
        "cards": deck.get("cards", [])
    }

    export_path.write_text(json.dumps(export_data, indent=2))
    print(f"\n[OK] Deck exported to {export_path}")


def import_deck_text():
    """Import a deck from text format."""
    print("\nPaste deck list (one card ID per line, empty line to finish):")

    cards = []
    while True:
        line = input().strip()
        if not line:
            break
        if not line.startswith("#"):
            cards.append(line)

    if not cards:
        print("No cards entered")
        return

    # Validate cards exist
    try:
        from cards import ALL_CARDS

        invalid = [c for c in cards if c not in ALL_CARDS]
        if invalid:
            print(f"\n[WARNING] Unknown card IDs: {', '.join(invalid[:5])}")
            if not confirm("Import anyway?"):
                return
    except:
        pass

    faction = select_from_list("Select faction for this deck:", get_existing_factions()[:-1])

    # Load and update decks
    decks_file = ROOT / "player_decks.json"
    if decks_file.exists():
        decks = json.loads(decks_file.read_text())
    else:
        decks = {}

    if faction not in decks:
        decks[faction] = {"leader": "", "cards": []}

    decks[faction]["cards"] = cards

    decks_file.write_text(json.dumps(decks, indent=2))
    print(f"\n[OK] Imported {len(cards)} cards to {faction} deck")


def import_deck_json():
    """Import a deck from JSON file."""
    import_path = get_input("Path to JSON file")
    path = Path(import_path)

    if not path.exists():
        print(f"File not found: {path}")
        return

    try:
        data = json.loads(path.read_text())

        faction = data.get("faction")
        leader = data.get("leader")
        cards = data.get("cards", [])

        if not faction:
            print("Invalid deck file: missing 'faction' field")
            return

        # Load and update decks
        decks_file = ROOT / "player_decks.json"
        if decks_file.exists():
            decks = json.loads(decks_file.read_text())
        else:
            decks = {}

        decks[faction] = {"leader": leader, "cards": cards}

        decks_file.write_text(json.dumps(decks, indent=2))
        print(f"\n[OK] Imported deck for {faction} ({len(cards)} cards)")

    except Exception as e:
        print(f"[ERROR] Could not import deck: {e}")


# ============================================================================
# MENU OPTION 11: BATCH IMPORT FROM JSON
# ============================================================================

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


def validate_batch_json(data: dict) -> List[str]:
    """
    Validate JSON structure and content for batch import.

    Returns list of error messages (empty if valid).
    """
    errors = []

    if not isinstance(data, dict):
        errors.append("Root must be a JSON object")
        return errors

    # Validate cards
    if "cards" in data:
        if not isinstance(data["cards"], list):
            errors.append("'cards' must be an array")
        else:
            for i, card in enumerate(data["cards"]):
                card_errors = validate_batch_card(card, i)
                errors.extend(card_errors)

    # Validate leaders
    if "leaders" in data:
        if not isinstance(data["leaders"], list):
            errors.append("'leaders' must be an array")
        else:
            for i, leader in enumerate(data["leaders"]):
                leader_errors = validate_batch_leader(leader, i)
                errors.extend(leader_errors)

    if "cards" not in data and "leaders" not in data:
        errors.append("JSON must contain 'cards' and/or 'leaders' array")

    return errors


def validate_batch_card(card: dict, index: int) -> List[str]:
    """Validate a single card entry in batch import."""
    errors = []
    prefix = f"Card[{index}]"

    required_fields = ["card_id", "name", "faction", "power", "row"]
    for field in required_fields:
        if field not in card:
            errors.append(f"{prefix}: missing required field '{field}'")

    if "card_id" in card:
        id_error = validate_card_id(card["card_id"])
        if id_error:
            errors.append(f"{prefix}: {id_error}")

    if "row" in card and card["row"] not in VALID_ROWS:
        errors.append(f"{prefix}: invalid row '{card['row']}' - must be one of {VALID_ROWS}")

    if "power" in card:
        try:
            power = int(card["power"])
            if not 0 <= power <= 20:
                errors.append(f"{prefix}: power must be 0-20")
        except (ValueError, TypeError):
            errors.append(f"{prefix}: power must be a number")

    if card.get("is_unlockable") and "rarity" not in card:
        errors.append(f"{prefix}: unlockable cards require 'rarity' field")

    return errors


def validate_batch_leader(leader: dict, index: int) -> List[str]:
    """Validate a single leader entry in batch import."""
    errors = []
    prefix = f"Leader[{index}]"

    required_fields = ["card_id", "name", "faction", "ability", "ability_desc"]
    for field in required_fields:
        if field not in leader:
            errors.append(f"{prefix}: missing required field '{field}'")

    if "card_id" in leader:
        id_error = validate_card_id(leader["card_id"])
        if id_error:
            errors.append(f"{prefix}: {id_error}")

    if "faction" in leader:
        valid_factions = get_existing_factions()[:-1]  # Exclude Neutral
        if leader["faction"] not in valid_factions:
            errors.append(f"{prefix}: invalid faction '{leader['faction']}'")

    return errors


def process_batch_cards(cards: List[dict]) -> Tuple[int, int]:
    """
    Process batch cards.

    Returns (success_count, error_count).
    """
    success = 0
    errors = 0

    for card in cards:
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

            # Generate formatted code
            card_code = format_card_entry(card_id, name, faction_const, power, row, ability)

            # Modify cards.py
            def modify_cards(content: str) -> str:
                return insert_card_entry_safely(content, faction, card_code)

            if not safe_modify_file(FILES["cards"], modify_cards, f"Added card {card_id}"):
                errors += 1
                continue

            # Modify unlocks.py if unlockable
            if is_unlockable:
                unlock_code = format_unlockable_entry(
                    card_id, name, faction, row, power, ability, description, rarity
                )

                def modify_unlocks(content: str) -> str:
                    return insert_unlockable_entry_safely(content, unlock_code)

                if not safe_modify_file(FILES["unlocks"], modify_unlocks, f"Added unlockable {card_id}"):
                    errors += 1
                    continue

            # Update card_catalog.json
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

    return success, errors


def process_batch_leaders(leaders: List[dict]) -> Tuple[int, int]:
    """
    Process batch leaders.

    Returns (success_count, error_count).
    """
    success = 0
    errors = 0

    for leader in leaders:
        try:
            card_id = leader["card_id"]
            name = leader["name"]
            faction = leader["faction"]
            ability = leader["ability"]
            ability_desc = leader["ability_desc"]
            is_unlockable = leader.get("is_unlockable", True)
            color_override = leader.get("color_override")
            banner_name = leader.get("banner_name", name.split()[-1])

            # Get faction constant
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

            # Format leader entry
            leader_entry = format_leader_entry(name, ability, ability_desc, card_id)

            # Modify content_registry.py
            def modify_registry(content: str) -> str:
                target_dict = "UNLOCKABLE_LEADERS" if is_unlockable else "BASE_FACTION_LEADERS"
                content = insert_leader_entry_safely(content, target_dict, faction_const, leader_entry)

                # Add color override if provided
                if color_override:
                    pattern = r'(LEADER_COLOR_OVERRIDES\s*=\s*\{)'
                    match = re.search(pattern, content)
                    if match:
                        end = content.find("}", match.end())
                        new_line = f'\n    "{card_id}": {tuple(color_override)},'
                        content = content[:end] + new_line + content[end:]

                # Add banner name
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

            # Update leader_catalog.json
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

    # Validate
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

    # Summary
    cards = data.get("cards", [])
    leaders = data.get("leaders", [])

    print(f"\n=== IMPORT SUMMARY ===")
    print(f"  Cards to import: {len(cards)}")
    print(f"  Leaders to import: {len(leaders)}")

    if not confirm("\nProceed with import?"):
        print("Cancelled.")
        return

    # Process cards
    card_success = 0
    card_errors = 0
    if cards:
        print("\n=== IMPORTING CARDS ===")
        card_success, card_errors = process_batch_cards(cards)

    # Process leaders
    leader_success = 0
    leader_errors = 0
    if leaders:
        print("\n=== IMPORTING LEADERS ===")
        leader_success, leader_errors = process_batch_leaders(leaders)

    # Final summary
    print("\n=== IMPORT COMPLETE ===")
    print(f"  Cards:   {card_success} added, {card_errors} failed")
    print(f"  Leaders: {leader_success} added, {leader_errors} failed")

    if card_errors + leader_errors > 0:
        print("\n  Some imports failed - check the log for details")

    # Generate placeholders
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

Valid factions: Tau'ri, Goa'uld, Jaffa Rebellion, Lucian Alliance, Asgard
Valid rows: close, ranged, siege, agile, special, weather
Valid rarities: common, rare, epic, legendary
""")

    input("\nPress Enter to continue...")


# ============================================================================
# MENU OPTION 12: AUDIO MANAGER
# ============================================================================

def audio_manager_workflow():
    """Manage faction themes, leader voices, and sound effects."""
    while True:
        print_header("AUDIO MANAGER")

        print("  1. Add New Faction Theme")
        print("  2. Add New Leader Voice")
        print("  3. Add New Sound Effect")
        print("  4. Add Commander Snippet")
        print("  5. Preview/Test Audio Files")
        print("  6. List All Audio Assets")
        print("  7. Find Missing Audio")
        print("  0. Back")
        print()

        choice = get_input("Choice", default="0")

        if choice == "0":
            break
        elif choice == "1":
            add_faction_theme_workflow()
        elif choice == "2":
            add_leader_voice_workflow()
        elif choice == "3":
            add_sound_effect_workflow()
        elif choice == "4":
            add_commander_snippet_workflow()
        elif choice == "5":
            preview_audio_workflow()
        elif choice == "6":
            list_all_audio_assets()
        elif choice == "7":
            find_missing_audio()

        input("\nPress Enter to continue...")


def add_faction_theme_workflow():
    """Copy a new faction theme to assets/audio/."""
    print_header("ADD FACTION THEME")

    audio_dir = ROOT / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Get existing factions
    factions = get_existing_factions()
    print("Existing factions:", ", ".join(factions))
    print()

    # Get source file
    source_path = get_input("Path to source audio file (.ogg or .mp3)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    # Get faction name
    faction = select_from_list("Select faction:", factions)
    faction_key = faction.lower().replace("'", "").replace(" ", "_")

    # Determine destination
    dest_name = f"{faction_key}_theme.ogg"
    dest_path = audio_dir / dest_name

    if dest_path.exists():
        if not confirm(f"Theme already exists at {dest_name}. Overwrite?", default=False):
            return

    # Copy file
    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied faction theme to {dest_path}")
        print(f"\n[OK] Faction theme added: {dest_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def add_leader_voice_workflow():
    """Copy a new leader voice to assets/audio/leader_voices/."""
    print_header("ADD LEADER VOICE")

    voice_dir = ROOT / "assets" / "audio" / "leader_voices"
    voice_dir.mkdir(parents=True, exist_ok=True)

    # Get source file
    source_path = get_input("Path to source audio file (.ogg)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    # Get leader info
    try:
        from content_registry import LEADER_NAME_BY_ID
        print("\nAvailable leader IDs:")
        for i, (lid, name) in enumerate(sorted(LEADER_NAME_BY_ID.items())[:20]):
            print(f"  {lid}: {name}")
        if len(LEADER_NAME_BY_ID) > 20:
            print(f"  ... and {len(LEADER_NAME_BY_ID) - 20} more")
    except ImportError:
        pass

    leader_id = get_input("\nLeader card_id (e.g., tauri_oneill)")

    # Determine destination
    dest_name = f"{leader_id}.ogg"
    dest_path = voice_dir / dest_name

    if dest_path.exists():
        if not confirm(f"Voice already exists at {dest_name}. Overwrite?", default=False):
            return

    # Copy file
    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied leader voice to {dest_path}")
        print(f"\n[OK] Leader voice added: leader_voices/{dest_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def add_sound_effect_workflow():
    """Copy a new sound effect to assets/audio/."""
    print_header("ADD SOUND EFFECT")

    audio_dir = ROOT / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Show existing sound effects
    existing_sfx = [f.name for f in audio_dir.glob("*.ogg")
                    if not f.name.endswith("_theme.ogg")
                    and "battle_round" not in f.name]
    print("Existing sound effects:")
    for sfx in sorted(existing_sfx)[:15]:
        print(f"  - {sfx}")
    print()

    # Get source file
    source_path = get_input("Path to source audio file (.ogg)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    # Get effect name
    effect_name = get_input("Effect name (e.g., 'horn', 'ring', 'weather_storm')")
    if not effect_name.endswith(".ogg"):
        effect_name += ".ogg"

    dest_path = audio_dir / effect_name

    if dest_path.exists():
        if not confirm(f"Effect already exists at {effect_name}. Overwrite?", default=False):
            return

    # Copy file
    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied sound effect to {dest_path}")
        print(f"\n[OK] Sound effect added: {effect_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def add_commander_snippet_workflow():
    """Copy a new commander snippet to assets/audio/commander_snippets/."""
    print_header("ADD COMMANDER SNIPPET")

    snippet_dir = ROOT / "assets" / "audio" / "commander_snippets"
    snippet_dir.mkdir(parents=True, exist_ok=True)

    # Get source file
    source_path = get_input("Path to source audio file (.ogg)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    # Show legendary commanders
    try:
        from cards import ALL_CARDS
        legendary = [cid for cid, c in ALL_CARDS.items()
                     if c.ability and "Legendary Commander" in c.ability]
        print("\nLegendary Commanders:")
        for cid in sorted(legendary)[:20]:
            card = ALL_CARDS[cid]
            print(f"  {cid}: {card.name}")
        if len(legendary) > 20:
            print(f"  ... and {len(legendary) - 20} more")
    except ImportError:
        pass

    card_id = get_input("\nCard ID (e.g., tauri_oneill)")

    # Determine destination
    dest_name = f"{card_id}.ogg"
    dest_path = snippet_dir / dest_name

    if dest_path.exists():
        if not confirm(f"Snippet already exists at {dest_name}. Overwrite?", default=False):
            return

    # Copy file
    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied commander snippet to {dest_path}")
        print(f"\n[OK] Commander snippet added: commander_snippets/{dest_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def preview_audio_workflow():
    """Preview/test audio files using pygame.mixer."""
    print_header("PREVIEW AUDIO")

    audio_dir = ROOT / "assets" / "audio"
    if not audio_dir.exists():
        print("No audio directory found")
        return

    # Collect all audio files
    all_audio = []
    for ogg in audio_dir.glob("*.ogg"):
        all_audio.append(("root", ogg))
    for ogg in (audio_dir / "leader_voices").glob("*.ogg"):
        all_audio.append(("leader_voices", ogg))
    for ogg in (audio_dir / "commander_snippets").glob("*.ogg"):
        all_audio.append(("commander_snippets", ogg))

    if not all_audio:
        print("No audio files found")
        return

    print(f"Found {len(all_audio)} audio files\n")

    # Group by category
    categories = {
        "1. Faction Themes": [f for cat, f in all_audio if f.name.endswith("_theme.ogg")],
        "2. Battle Music": [f for cat, f in all_audio if "battle_round" in f.name],
        "3. Sound Effects": [f for cat, f in all_audio if cat == "root"
                            and not f.name.endswith("_theme.ogg")
                            and "battle_round" not in f.name],
        "4. Leader Voices": [f for cat, f in all_audio if cat == "leader_voices"],
        "5. Commander Snippets": [f for cat, f in all_audio if cat == "commander_snippets"],
    }

    for cat_name, files in categories.items():
        if files:
            print(f"{cat_name}: {len(files)} files")

    print()
    category = select_from_list("Select category:", list(categories.keys()))
    files = categories[category]

    if not files:
        print("No files in this category")
        return

    print(f"\nFiles in {category}:")
    for i, f in enumerate(sorted(files)[:20], 1):
        print(f"  {i}. {f.name}")

    if len(files) > 20:
        print(f"  ... and {len(files) - 20} more")

    choice = get_int("\nSelect file to preview (0 to cancel)", min_val=0, max_val=min(20, len(files)))
    if choice == 0:
        return

    selected_file = sorted(files)[choice - 1]

    # Try to play with pygame
    try:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

        print(f"\nPlaying: {selected_file.name}")
        print("(Press Enter to stop)")

        sound = pygame.mixer.Sound(str(selected_file))
        sound.play()

        input()
        sound.stop()
        pygame.mixer.quit()

    except Exception as e:
        print(f"[ERROR] Could not play audio: {e}")
        print("Make sure pygame is installed and audio device is available")


def list_all_audio_assets():
    """List all audio files in assets/audio/."""
    print_header("ALL AUDIO ASSETS")

    audio_dir = ROOT / "assets" / "audio"
    if not audio_dir.exists():
        print("No audio directory found")
        return

    print("=== FACTION THEMES ===")
    themes = list(audio_dir.glob("*_theme.ogg"))
    for t in sorted(themes):
        size_kb = t.stat().st_size // 1024
        print(f"  {t.name} ({size_kb} KB)")
    print(f"  Total: {len(themes)} themes\n")

    print("=== BATTLE MUSIC ===")
    battle = list(audio_dir.glob("battle_round*.ogg"))
    for b in sorted(battle):
        size_kb = b.stat().st_size // 1024
        print(f"  {b.name} ({size_kb} KB)")
    print(f"  Total: {len(battle)} tracks\n")

    print("=== SOUND EFFECTS ===")
    sfx = [f for f in audio_dir.glob("*.ogg")
           if not f.name.endswith("_theme.ogg")
           and "battle_round" not in f.name]
    for s in sorted(sfx):
        size_kb = s.stat().st_size // 1024
        print(f"  {s.name} ({size_kb} KB)")
    print(f"  Total: {len(sfx)} effects\n")

    print("=== LEADER VOICES ===")
    voice_dir = audio_dir / "leader_voices"
    if voice_dir.exists():
        voices = list(voice_dir.glob("*.ogg"))
        for v in sorted(voices):
            size_kb = v.stat().st_size // 1024
            print(f"  {v.name} ({size_kb} KB)")
        print(f"  Total: {len(voices)} voices\n")
    else:
        print("  (directory not found)\n")

    print("=== COMMANDER SNIPPETS ===")
    snippet_dir = audio_dir / "commander_snippets"
    if snippet_dir.exists():
        snippets = list(snippet_dir.glob("*.ogg"))
        for s in sorted(snippets):
            size_kb = s.stat().st_size // 1024
            print(f"  {s.name} ({size_kb} KB)")
        print(f"  Total: {len(snippets)} snippets")
    else:
        print("  (directory not found)")


def find_missing_audio():
    """Cross-reference leaders/commanders with audio files."""
    print_header("FIND MISSING AUDIO")

    audio_dir = ROOT / "assets" / "audio"
    voice_dir = audio_dir / "leader_voices"
    snippet_dir = audio_dir / "commander_snippets"

    # Get existing audio files
    existing_voices = set()
    if voice_dir.exists():
        existing_voices = {f.stem for f in voice_dir.glob("*.ogg")}

    existing_snippets = set()
    if snippet_dir.exists():
        existing_snippets = {f.stem for f in snippet_dir.glob("*.ogg")}

    existing_themes = set()
    for f in audio_dir.glob("*_theme.ogg"):
        existing_themes.add(f.stem.replace("_theme", ""))

    # Get expected items
    missing_voices = []
    missing_snippets = []
    missing_themes = []

    # Check leader voices
    try:
        from content_registry import LEADER_NAME_BY_ID
        for leader_id, name in LEADER_NAME_BY_ID.items():
            if leader_id not in existing_voices:
                # Also check commander snippets as fallback
                if leader_id not in existing_snippets:
                    missing_voices.append((leader_id, name))
    except ImportError:
        print("[WARNING] Could not import content_registry")

    # Check commander snippets
    try:
        from cards import ALL_CARDS
        for card_id, card in ALL_CARDS.items():
            if card.ability and "Legendary Commander" in card.ability:
                if card_id not in existing_snippets:
                    missing_snippets.append((card_id, card.name))
    except ImportError:
        print("[WARNING] Could not import cards")

    # Check faction themes
    factions = get_existing_factions()
    for faction in factions:
        if faction == "Neutral":
            continue
        faction_key = faction.lower().replace("'", "").replace(" ", "_")
        if faction_key not in existing_themes:
            missing_themes.append(faction)

    # Report
    print("=== MISSING LEADER VOICES ===")
    if missing_voices:
        for lid, name in sorted(missing_voices)[:15]:
            print(f"  - {lid}: {name}")
        if len(missing_voices) > 15:
            print(f"  ... and {len(missing_voices) - 15} more")
        print(f"  Total missing: {len(missing_voices)}")
    else:
        print("  All leader voices present!")

    print("\n=== MISSING COMMANDER SNIPPETS ===")
    if missing_snippets:
        for cid, name in sorted(missing_snippets)[:15]:
            print(f"  - {cid}: {name}")
        if len(missing_snippets) > 15:
            print(f"  ... and {len(missing_snippets) - 15} more")
        print(f"  Total missing: {len(missing_snippets)}")
    else:
        print("  All commander snippets present!")

    print("\n=== MISSING FACTION THEMES ===")
    if missing_themes:
        for faction in missing_themes:
            faction_key = faction.lower().replace("'", "").replace(" ", "_")
            print(f"  - {faction_key}_theme.ogg ({faction})")
        print(f"  Total missing: {len(missing_themes)}")
    else:
        print("  All faction themes present!")


# ============================================================================
# MENU OPTION 13: LEADER ABILITY GENERATOR
# ============================================================================

def leader_ability_generator_workflow():
    """Generate code stubs for new leader abilities."""
    print_header("LEADER ABILITY GENERATOR")

    print("This tool generates code stubs for new leader abilities.")
    print("You'll need to manually add the generated code to game.py\n")

    print("Ability Types:")
    print("  1. Passive Power Bonus (applied during score calculation)")
    print("  2. Once-Per-Game Manual Activation (player clicks button)")
    print("  3. Automatic Trigger (event-based like round start/end)")
    print("  4. Continuous Effect (always active)")
    print("  0. Back")
    print()

    choice = get_input("Select ability type", default="0")

    if choice == "0":
        return

    # Collect common info
    print()
    leader_name = get_input("Leader Name (e.g., 'Dr. McKay')")
    leader_id = get_input("Leader card_id (e.g., 'tauri_mckay')")
    ability_desc = get_input("Ability Description (what it does)")

    print()

    if choice == "1":
        generate_passive_bonus_stub(leader_name, leader_id, ability_desc)
    elif choice == "2":
        generate_manual_activation_stub(leader_name, leader_id, ability_desc)
    elif choice == "3":
        generate_auto_trigger_stub(leader_name, leader_id, ability_desc)
    elif choice == "4":
        generate_continuous_effect_stub(leader_name, leader_id, ability_desc)

    log(f"Generated leader ability stub for {leader_name} ({leader_id})")


def generate_passive_bonus_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for passive power bonus ability."""
    print_header("PASSIVE POWER BONUS STUB")

    # Get specifics
    target_row = select_from_list("Which row to buff?", ["close", "ranged", "siege", "all rows"])
    bonus = get_int("Power bonus amount", min_val=1, max_val=5, default=2)
    hero_included = confirm("Does the bonus apply to heroes too?", default=False)

    hero_check = "# Note: Applies to heroes too" if hero_included else "if not is_hero(card):"
    indent = "" if hero_included else "    "

    if target_row == "all rows":
        row_code = '''for row_name in ["close", "ranged", "siege"]:
            for card in player.board.get(row_name, []):'''
    else:
        row_code = f'''for card in player.board.get("{target_row}", []):'''

    stub = f'''
# =============================================================================
# ADD TO game.py - In calculate_scores_and_log() method (~line 485)
# Find the section where leader abilities modify power
# =============================================================================

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    {row_code}
        {hero_check}
        {indent}card.displayed_power = getattr(card, 'displayed_power', card.power) + {bonus}
'''

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print("1. Open game.py")
    print("2. Find the calculate_scores_and_log() method (around line 485)")
    print("3. Look for other leader ability checks (search for 'player.leader')")
    print("4. Add this code in the same section")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")


def generate_manual_activation_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for once-per-game manual activation ability."""
    print_header("MANUAL ACTIVATION STUB")

    stub = f'''
# =============================================================================
# ADD TO game.py - In activate_leader_ability() method (~line 1694)
# =============================================================================

# In the activate_leader_ability method, add this elif clause:

elif "{leader_name}" in leader_name:
    result = self._activate_{leader_id.split('_')[1]}_ability(player)

# =============================================================================
# ADD TO game.py - New method (add after other _activate_* methods ~line 2000)
# =============================================================================

def _activate_{leader_id.split('_')[1]}_ability(self, player):
    """
    {leader_name}: {desc}
    """
    # TODO: Implement ability logic here

    # Example: If ability needs UI selection, return requires_ui
    # return {{
    #     "ability": "{leader_name} Ability",
    #     "revealed_cards": eligible_cards,
    #     "requires_ui": True
    # }}

    # Example: If ability is immediate effect
    self.add_history_event(
        "ability",
        f"{{player.name}} ({leader_name}) activated their ability!",
        self._owner_label(player),
        icon="⚡"
    )

    return {{"ability": "{leader_name} Ability"}}

# =============================================================================
# If ability needs UI interaction, also add a completion method:
# =============================================================================

def {leader_id.split('_')[1]}_complete_ability(self, player, chosen_card):
    """Complete {leader_name}'s ability after UI selection."""
    # TODO: Implement completion logic

    # Mark leader ability as used after successful completion
    self.leader_ability_used[player] = True
    self.calculate_scores_and_log()
    return True
'''

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print("1. Open game.py")
    print("2. Add the elif clause to activate_leader_ability() method (~line 1694)")
    print("3. Add the _activate_*_ability method after similar methods (~line 2000)")
    print("4. If UI interaction needed, add the completion method too")
    print("5. Add UI handling in main.py if requires_ui is True")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")


def generate_auto_trigger_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for automatic trigger ability."""
    print_header("AUTOMATIC TRIGGER STUB")

    trigger = select_from_list("When does this trigger?", [
        "round_start",
        "round_end",
        "turn_start",
        "turn_end",
        "card_played",
        "card_destroyed",
        "pass_turn"
    ])

    stub = f'''
# =============================================================================
# ADD TO game.py - Find the appropriate trigger location
# =============================================================================
'''

    if trigger == "round_start":
        stub += f'''
# In start_round() method (~line 200), add:

# {leader_name} Leader Ability: {desc}
for player in [self.player1, self.player2]:
    if player.leader and "{leader_name}" in player.leader.get('name', ''):
        # TODO: Implement round start effect
        self.add_history_event(
            "ability",
            f"{{player.name}} ({leader_name})'s ability triggered!",
            self._owner_label(player),
            icon="⚡"
        )
'''
    elif trigger == "round_end":
        stub += f'''
# In end_round() method (~line 350), add:

# {leader_name} Leader Ability: {desc}
for player in [self.player1, self.player2]:
    if player.leader and "{leader_name}" in player.leader.get('name', ''):
        # TODO: Implement round end effect
        self.add_history_event(
            "ability",
            f"{{player.name}} ({leader_name})'s ability triggered!",
            self._owner_label(player),
            icon="⚡"
        )
'''
    elif trigger == "card_played":
        stub += f'''
# In play_card() method (~line 500), after card is placed, add:

# {leader_name} Leader Ability: {desc}
if self.current_player.leader and "{leader_name}" in self.current_player.leader.get('name', ''):
    # TODO: Implement card played effect
    # card variable contains the card that was just played
    self.add_history_event(
        "ability",
        f"{{self.current_player.name}} ({leader_name})'s ability triggered!",
        self._owner_label(self.current_player),
        icon="⚡"
    )
'''
    elif trigger == "pass_turn":
        stub += f'''
# In pass_turn() method, add:

# {leader_name} Leader Ability: {desc}
if self.current_player.leader and "{leader_name}" in self.current_player.leader.get('name', ''):
    # TODO: Implement pass turn effect
    self.add_history_event(
        "ability",
        f"{{self.current_player.name}} ({leader_name})'s ability triggered on pass!",
        self._owner_label(self.current_player),
        icon="⚡"
    )
'''
    else:
        stub += f'''
# Find the appropriate trigger point for: {trigger}
# {leader_name} Leader Ability: {desc}

if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # TODO: Implement {trigger} effect
    self.add_history_event(
        "ability",
        f"{{player.name}} ({leader_name})'s ability triggered!",
        self._owner_label(player),
        icon="⚡"
    )
'''

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print(f"1. Open game.py")
    print(f"2. Find the {trigger} trigger location")
    print("3. Add the code at the appropriate point")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")


def generate_continuous_effect_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for continuous effect ability."""
    print_header("CONTINUOUS EFFECT STUB")

    effect_type = select_from_list("What type of continuous effect?", [
        "weather_immunity",
        "power_modifier",
        "draw_modifier",
        "custom"
    ])

    stub = f'''
# =============================================================================
# CONTINUOUS EFFECT: {leader_name} - {desc}
# =============================================================================
'''

    if effect_type == "weather_immunity":
        stub += f'''
# In apply_weather_effect() method, add check at the start:

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # Skip weather effect for this player
    return []  # Or modify the effect as needed
'''
    elif effect_type == "power_modifier":
        stub += f'''
# In calculate_scores_and_log() method (~line 485), add:

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    for row_name in ["close", "ranged", "siege"]:
        for card in player.board.get(row_name, []):
            # TODO: Apply continuous power modifier
            # Example: card.displayed_power += 1
            pass
'''
    elif effect_type == "draw_modifier":
        stub += f'''
# In draw_card() method, add:

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # TODO: Modify draw behavior
    # Example: Draw extra card
    # self._draw_single_card(player)
    pass
'''
    else:
        stub += f'''
# {leader_name} Leader Ability: {desc}
#
# IMPLEMENTATION NOTES:
# - Continuous effects should be checked wherever they apply
# - Common locations:
#   - calculate_scores_and_log() for power modifiers
#   - apply_weather_effect() for weather immunity
#   - draw_card() for draw modifiers
#   - play_card() for card play effects
#
# Add checks like:
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # TODO: Implement continuous effect
    pass
'''

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print("1. Open game.py")
    print("2. Find the appropriate method(s) based on effect type")
    print("3. Add the check wherever the effect should apply")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")


# ============================================================================
# MENU OPTION 14: CARD RENAME/DELETE TOOL
# ============================================================================

def card_rename_delete_workflow():
    """Safely rename or delete cards across all files."""
    while True:
        print_header("CARD RENAME/DELETE TOOL")

        print("  1. Rename Card ID")
        print("  2. Delete Card Completely")
        print("  3. Preview References (dry run)")
        print("  4. Batch Rename (from JSON)")
        print("  0. Back")
        print()

        choice = get_input("Choice", default="0")

        if choice == "0":
            break
        elif choice == "1":
            rename_card_workflow()
        elif choice == "2":
            delete_card_workflow()
        elif choice == "3":
            preview_references_workflow()
        elif choice == "4":
            batch_rename_workflow()

        input("\nPress Enter to continue...")


def find_all_card_references(card_id: str) -> Dict[str, List[Tuple[int, str]]]:
    """
    Find all references to a card_id across all relevant files.

    Returns dict mapping filename to list of (line_number, line_content) tuples.
    """
    references = {}

    # Files to search
    search_files = [
        ("cards.py", FILES["cards"]),
        ("unlocks.py", FILES["unlocks"]),
        ("content_registry.py", FILES["content_registry"]),
        ("card_catalog.json", FILES["card_catalog"]),
        ("player_decks.json", ROOT / "player_decks.json"),
        ("player_unlocks.json", ROOT / "player_unlocks.json"),
    ]

    for name, path in search_files:
        if not path.exists():
            continue

        content = path.read_text()
        lines = content.split('\n')

        matches = []
        for i, line in enumerate(lines, 1):
            if card_id in line:
                matches.append((i, line.strip()[:80]))

        if matches:
            references[name] = matches

    # Check asset files
    asset_files = []
    card_asset = ROOT / "assets" / f"{card_id}.png"
    if card_asset.exists():
        asset_files.append((0, f"assets/{card_id}.png"))

    snippet = ROOT / "assets" / "audio" / "commander_snippets" / f"{card_id}.ogg"
    if snippet.exists():
        asset_files.append((0, f"assets/audio/commander_snippets/{card_id}.ogg"))

    voice = ROOT / "assets" / "audio" / "leader_voices" / f"{card_id}.ogg"
    if voice.exists():
        asset_files.append((0, f"assets/audio/leader_voices/{card_id}.ogg"))

    if asset_files:
        references["asset_files"] = asset_files

    return references


def preview_references_workflow():
    """Preview all references to a card (dry run)."""
    print_header("PREVIEW CARD REFERENCES")

    card_id = get_input("Enter card_id to search for")

    print(f"\nSearching for references to '{card_id}'...\n")

    refs = find_all_card_references(card_id)

    if not refs:
        print(f"No references found for '{card_id}'")
        return

    total_refs = 0
    for filename, matches in refs.items():
        print(f"\n=== {filename} ({len(matches)} references) ===")
        for line_num, line_content in matches[:10]:
            if line_num > 0:
                print(f"  Line {line_num}: {line_content}")
            else:
                print(f"  File: {line_content}")
        if len(matches) > 10:
            print(f"  ... and {len(matches) - 10} more")
        total_refs += len(matches)

    print(f"\n=== TOTAL: {total_refs} references in {len(refs)} files ===")


def rename_card_workflow():
    """Interactive card rename with preview."""
    print_header("RENAME CARD")

    old_id = get_input("Current card_id")

    # Check card exists
    try:
        from cards import ALL_CARDS
        if old_id not in ALL_CARDS:
            print(f"\n[WARNING] Card '{old_id}' not found in ALL_CARDS")
            if not confirm("Continue anyway?", default=False):
                return
        else:
            card = ALL_CARDS[old_id]
            print(f"\n  Found: {card.name} ({card.faction})")
    except ImportError:
        print("[WARNING] Could not verify card exists")

    new_id = get_input("New card_id", validator=validate_card_id)

    # Preview references
    print(f"\nSearching for references to '{old_id}'...\n")
    refs = find_all_card_references(old_id)

    if not refs:
        print(f"No references found for '{old_id}'")
        return

    total_refs = sum(len(m) for m in refs.values())
    print(f"Found {total_refs} references in {len(refs)} files:")
    for filename in refs.keys():
        print(f"  - {filename}")

    print()
    if not confirm(f"Rename '{old_id}' to '{new_id}' in all these files?"):
        print("Cancelled.")
        return

    # Create backups and execute rename
    success = execute_card_rename(old_id, new_id, refs)

    if success:
        log(f"RENAMED: {old_id} -> {new_id}")
        print(f"\n[OK] Card renamed successfully: {old_id} -> {new_id}")
    else:
        print("\n[ERROR] Rename failed - check logs for details")


def execute_card_rename(old_id: str, new_id: str, refs: Dict) -> bool:
    """Execute the card rename across all files."""
    # Backup all files first
    for filename, _ in refs.items():
        if filename == "asset_files":
            continue
        if filename == "cards.py":
            create_backup(FILES["cards"])
        elif filename == "unlocks.py":
            create_backup(FILES["unlocks"])
        elif filename == "content_registry.py":
            create_backup(FILES["content_registry"])
        elif filename == "card_catalog.json":
            create_backup(FILES["card_catalog"])
        elif filename == "player_decks.json":
            create_backup(ROOT / "player_decks.json")
        elif filename == "player_unlocks.json":
            create_backup(ROOT / "player_unlocks.json")

    try:
        # Rename in Python files
        for py_file in ["cards", "unlocks", "content_registry"]:
            path = FILES.get(py_file)
            if path and path.exists() and py_file + ".py" in refs:
                content = path.read_text()
                # Use word boundary replacement to avoid partial matches
                new_content = re.sub(
                    rf'\b{re.escape(old_id)}\b',
                    new_id,
                    content
                )
                # Validate Python syntax
                compile(new_content, str(path), "exec")
                path.write_text(new_content)
                log(f"  Updated {py_file}.py")

        # Rename in JSON files
        for json_file in ["card_catalog.json", "player_decks.json", "player_unlocks.json"]:
            if json_file in refs:
                if json_file == "card_catalog.json":
                    path = FILES["card_catalog"]
                else:
                    path = ROOT / json_file

                if path.exists():
                    content = path.read_text()
                    new_content = content.replace(f'"{old_id}"', f'"{new_id}"')
                    path.write_text(new_content)
                    log(f"  Updated {json_file}")

        # Rename asset files
        if "asset_files" in refs:
            for _, asset_path in refs["asset_files"]:
                old_asset = ROOT / asset_path
                new_asset_path = asset_path.replace(old_id, new_id)
                new_asset = ROOT / new_asset_path
                if old_asset.exists():
                    old_asset.rename(new_asset)
                    log(f"  Renamed asset: {asset_path} -> {new_asset_path}")

        return True

    except Exception as e:
        log(f"ERROR during rename: {e}")
        print(f"[ERROR] {e}")
        print("Attempting rollback...")

        # Restore backups
        for filename in refs.keys():
            if filename == "asset_files":
                continue
            if filename == "cards.py":
                restore_from_backup(FILES["cards"])
            elif filename == "unlocks.py":
                restore_from_backup(FILES["unlocks"])
            elif filename == "content_registry.py":
                restore_from_backup(FILES["content_registry"])

        return False


def delete_card_workflow():
    """Delete a card with double confirmation."""
    print_header("DELETE CARD")

    card_id = get_input("Card ID to delete")

    # Check if card exists and get info
    card_info = None
    is_leader = False
    try:
        from cards import ALL_CARDS
        if card_id in ALL_CARDS:
            card = ALL_CARDS[card_id]
            card_info = f"{card.name} ({card.faction}, {card.power} power)"
            print(f"\n  Found: {card_info}")
        else:
            print(f"\n[WARNING] Card '{card_id}' not found in ALL_CARDS")

        # Check if it's a leader
        from content_registry import LEADER_NAME_BY_ID
        if card_id in LEADER_NAME_BY_ID:
            is_leader = True
            print(f"  [!] This is also a LEADER: {LEADER_NAME_BY_ID[card_id]}")
    except ImportError:
        pass

    # Preview references
    print(f"\nSearching for references to '{card_id}'...\n")
    refs = find_all_card_references(card_id)

    if not refs:
        print(f"No references found for '{card_id}'")
        return

    total_refs = sum(len(m) for m in refs.values())
    print(f"Found {total_refs} references in {len(refs)} files:")
    for filename, matches in refs.items():
        print(f"  - {filename}: {len(matches)} references")

    # First confirmation
    print()
    print("[!] WARNING: This will permanently delete the card from:")
    print("    - cards.py (card definition)")
    if "unlocks.py" in refs:
        print("    - unlocks.py (unlock entry)")
    if is_leader:
        print("    - content_registry.py (leader entry)")
    if "asset_files" in refs:
        print("    - Asset files (images, audio)")
    if "player_decks.json" in refs:
        print("    - Player deck saves")
    if "player_unlocks.json" in refs:
        print("    - Player unlock progress")

    if not confirm("\nAre you sure you want to delete this card?", default=False):
        print("Cancelled.")
        return

    # Second confirmation - type DELETE card_id
    print()
    confirmation = get_input(f"Type 'DELETE {card_id}' to confirm")
    if confirmation != f"DELETE {card_id}":
        print("Confirmation failed. Cancelled.")
        return

    # Execute deletion
    success = execute_card_delete(card_id, refs, is_leader)

    if success:
        log(f"DELETED: {card_id}")
        print(f"\n[OK] Card deleted successfully: {card_id}")
    else:
        print("\n[ERROR] Delete failed - check logs for details")


def execute_card_delete(card_id: str, refs: Dict, is_leader: bool) -> bool:
    """Execute the card deletion across all files."""
    # Backup all files first
    for filename in refs.keys():
        if filename == "asset_files":
            continue
        if filename == "cards.py":
            create_backup(FILES["cards"])
        elif filename == "unlocks.py":
            create_backup(FILES["unlocks"])
        elif filename == "content_registry.py":
            create_backup(FILES["content_registry"])
        elif filename == "card_catalog.json":
            create_backup(FILES["card_catalog"])
        elif filename == "player_decks.json":
            create_backup(ROOT / "player_decks.json")
        elif filename == "player_unlocks.json":
            create_backup(ROOT / "player_unlocks.json")

    try:
        # Delete from cards.py
        if "cards.py" in refs:
            content = FILES["cards"].read_text()
            # Remove the card entry line
            pattern = rf'^\s*"{card_id}":\s*Card\([^)]+\),?\s*$'
            new_content = re.sub(pattern, '', content, flags=re.MULTILINE)
            compile(new_content, str(FILES["cards"]), "exec")
            FILES["cards"].write_text(new_content)
            log(f"  Removed from cards.py")

        # Delete from unlocks.py
        if "unlocks.py" in refs:
            content = FILES["unlocks"].read_text()
            # Remove the unlockable entry block
            pattern = rf'^\s*"{card_id}":\s*\{{[^}}]+\}},?\s*$'
            new_content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
            compile(new_content, str(FILES["unlocks"]), "exec")
            FILES["unlocks"].write_text(new_content)
            log(f"  Removed from unlocks.py")

        # Delete from content_registry.py (if leader)
        if is_leader and "content_registry.py" in refs:
            content = FILES["content_registry"].read_text()
            # Remove leader entry
            pattern = rf'\{{"name":[^}}]*"card_id":\s*"{card_id}"[^}}]*\}},?\s*'
            new_content = re.sub(pattern, '', content)
            # Remove from LEADER_COLOR_OVERRIDES
            pattern2 = rf'^\s*"{card_id}":\s*\([^)]+\),?\s*$'
            new_content = re.sub(pattern2, '', new_content, flags=re.MULTILINE)
            # Remove from LEADER_BANNER_NAMES
            pattern3 = rf'^\s*"{card_id}":\s*"[^"]+",?\s*$'
            new_content = re.sub(pattern3, '', new_content, flags=re.MULTILINE)
            compile(new_content, str(FILES["content_registry"]), "exec")
            FILES["content_registry"].write_text(new_content)
            log(f"  Removed from content_registry.py")

        # Clean up JSON files
        if "card_catalog.json" in refs:
            remove_card_from_json_file(FILES["card_catalog"], card_id)
            log(f"  Removed from card_catalog.json")

        if "player_decks.json" in refs:
            path = ROOT / "player_decks.json"
            if path.exists():
                data = json.loads(path.read_text())
                for faction, deck in data.items():
                    if "cards" in deck and card_id in deck["cards"]:
                        deck["cards"] = [c for c in deck["cards"] if c != card_id]
                    if deck.get("leader") == card_id:
                        deck["leader"] = ""
                path.write_text(json.dumps(data, indent=2))
                log(f"  Cleaned player_decks.json")

        if "player_unlocks.json" in refs:
            path = ROOT / "player_unlocks.json"
            if path.exists():
                data = json.loads(path.read_text())
                if "unlocked" in data and card_id in data["unlocked"]:
                    data["unlocked"] = [c for c in data["unlocked"] if c != card_id]
                for faction, leaders in data.get("unlocked_leaders", {}).items():
                    if card_id in leaders:
                        data["unlocked_leaders"][faction] = [l for l in leaders if l != card_id]
                path.write_text(json.dumps(data, indent=2))
                log(f"  Cleaned player_unlocks.json")

        # Delete asset files
        if "asset_files" in refs:
            for _, asset_path in refs["asset_files"]:
                full_path = ROOT / asset_path
                if full_path.exists():
                    # Move to backup folder instead of deleting
                    backup_path = _backup_folder / Path(asset_path).name
                    shutil.move(str(full_path), str(backup_path))
                    log(f"  Moved asset to backup: {asset_path}")

        return True

    except Exception as e:
        log(f"ERROR during delete: {e}")
        print(f"[ERROR] {e}")
        print("Attempting rollback...")

        # Restore backups
        for filename in refs.keys():
            if filename == "asset_files":
                continue
            if filename == "cards.py":
                restore_from_backup(FILES["cards"])
            elif filename == "unlocks.py":
                restore_from_backup(FILES["unlocks"])
            elif filename == "content_registry.py":
                restore_from_backup(FILES["content_registry"])

        return False


def remove_card_from_json_file(path: Path, card_id: str):
    """Remove card from a JSON file (card_catalog.json format)."""
    if not path.exists():
        return

    data = json.loads(path.read_text())

    # Handle card_catalog.json format
    for faction, cards in list(data.items()):
        if isinstance(cards, list):
            data[faction] = [c for c in cards if c.get("card_id") != card_id]

    path.write_text(json.dumps(data, indent=2))


def batch_rename_workflow():
    """Batch rename cards from a JSON file."""
    print_header("BATCH RENAME FROM JSON")

    print("JSON format expected:")
    print('''
{
  "renames": [
    {"old_id": "old_card_id_1", "new_id": "new_card_id_1"},
    {"old_id": "old_card_id_2", "new_id": "new_card_id_2"}
  ]
}
''')

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

    renames = data.get("renames", [])
    if not renames:
        print("[ERROR] No renames found in JSON")
        return

    print(f"\nFound {len(renames)} rename operations:")
    for r in renames[:10]:
        print(f"  - {r['old_id']} -> {r['new_id']}")
    if len(renames) > 10:
        print(f"  ... and {len(renames) - 10} more")

    if not confirm("\nProceed with batch rename?"):
        print("Cancelled.")
        return

    success_count = 0
    error_count = 0

    for rename in renames:
        old_id = rename.get("old_id")
        new_id = rename.get("new_id")

        if not old_id or not new_id:
            print(f"  [SKIP] Invalid entry: {rename}")
            error_count += 1
            continue

        print(f"\n  Renaming: {old_id} -> {new_id}")
        refs = find_all_card_references(old_id)

        if not refs:
            print(f"    [SKIP] No references found")
            continue

        if execute_card_rename(old_id, new_id, refs):
            success_count += 1
            print(f"    [OK] Renamed successfully")
        else:
            error_count += 1
            print(f"    [ERROR] Rename failed")

    print(f"\n=== BATCH COMPLETE ===")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {error_count}")


# ============================================================================
# MAIN MENU
# ============================================================================

def main_menu():
    """Display and handle main menu."""
    while True:
        clear_screen()

        print()
        print("+" + "=" * 50 + "+")
        print("|        STARGWENT CONTENT MANAGER                  |")
        print("+" + "=" * 50 + "+")
        print("|                                                   |")
        print("|  === DEVELOPER TOOLS ===                          |")
        print("|   1. Add a new CARD                               |")
        print("|   2. Add a new LEADER                             |")
        print("|   3. Add a new FACTION (comprehensive)            |")
        print("|   4. Add/Edit ABILITY                             |")
        print("|   5. Generate placeholder images                  |")
        print("|   6. Regenerate all documentation                 |")
        print("|   7. Asset Checker (find missing images)          |")
        print("|   8. Balance Analyzer (power stats)               |")
        print("|  11. Batch Import (from JSON)                     |")
        print("|  12. Audio Manager                          [NEW] |")
        print("|  13. Leader Ability Generator               [NEW] |")
        print("|  14. Card Rename/Delete Tool                [NEW] |")
        print("|                                                   |")
        print("|  === USER TOOLS ===                               |")
        print("|   9. Save Manager (backup/restore saves)          |")
        print("|  10. Deck Import/Export (share decks)             |")
        print("|                                                   |")
        print("|   0. Exit                                         |")
        print("+" + "=" * 50 + "+")
        print()

        choice = get_input("Choice", default="0")

        if choice == "0":
            save_session_log()
            print("\nGoodbye!")
            break

        start_session()

        try:
            if choice == "1":
                add_card_workflow()
            elif choice == "2":
                add_leader_workflow()
            elif choice == "3":
                add_faction_workflow()
            elif choice == "4":
                ability_manager_workflow()
            elif choice == "5":
                placeholder_generation_workflow()
            elif choice == "6":
                regenerate_documentation()
            elif choice == "7":
                asset_checker_workflow()
            elif choice == "8":
                balance_analyzer_workflow()
            elif choice == "9":
                save_manager_workflow()
            elif choice == "10":
                deck_import_export_workflow()
            elif choice == "11":
                batch_import_workflow()
            elif choice == "12":
                audio_manager_workflow()
            elif choice == "13":
                leader_ability_generator_workflow()
            elif choice == "14":
                card_rename_delete_workflow()
            else:
                print("Invalid choice")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()

        save_session_log()

        input("\nPress Enter to continue...")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        save_session_log()
