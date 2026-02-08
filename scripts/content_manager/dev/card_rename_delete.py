"""Developer workflow: Card rename/delete tool."""

import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from ..config import ROOT, FILES
from ..ui import print_header, get_input, get_int, confirm, progress_bar
from ..validation import validate_card_id
from ..backup import create_backup, restore_from_backup
from ..logging_ import get_backup_folder, log


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
    """Find all references to a card_id across all relevant files."""
    references = {}

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

    success = execute_card_rename(old_id, new_id, refs)

    if success:
        log(f"RENAMED: {old_id} -> {new_id}")
        print(f"\n[OK] Card renamed successfully: {old_id} -> {new_id}")
    else:
        print("\n[ERROR] Rename failed - check logs for details")


def execute_card_rename(old_id: str, new_id: str, refs: Dict) -> bool:
    """Execute the card rename across all files."""
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
        for py_file in ["cards", "unlocks", "content_registry"]:
            path = FILES.get(py_file)
            if path and path.exists() and py_file + ".py" in refs:
                content = path.read_text()
                new_content = re.sub(
                    rf'\b{re.escape(old_id)}\b',
                    new_id,
                    content
                )
                compile(new_content, str(path), "exec")
                path.write_text(new_content)
                log(f"  Updated {py_file}.py")

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

        from content_registry import LEADER_NAME_BY_ID
        if card_id in LEADER_NAME_BY_ID:
            is_leader = True
            print(f"  [!] This is also a LEADER: {LEADER_NAME_BY_ID[card_id]}")
    except ImportError:
        pass

    print(f"\nSearching for references to '{card_id}'...\n")
    refs = find_all_card_references(card_id)

    if not refs:
        print(f"No references found for '{card_id}'")
        return

    total_refs = sum(len(m) for m in refs.values())
    print(f"Found {total_refs} references in {len(refs)} files:")
    for filename, matches in refs.items():
        print(f"  - {filename}: {len(matches)} references")

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

    print()
    confirmation = get_input(f"Type 'DELETE {card_id}' to confirm")
    if confirmation != f"DELETE {card_id}":
        print("Confirmation failed. Cancelled.")
        return

    success = execute_card_delete(card_id, refs, is_leader)

    if success:
        log(f"DELETED: {card_id}")
        print(f"\n[OK] Card deleted successfully: {card_id}")
    else:
        print("\n[ERROR] Delete failed - check logs for details")


def execute_card_delete(card_id: str, refs: Dict, is_leader: bool) -> bool:
    """Execute the card deletion across all files."""
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
        if "cards.py" in refs:
            content = FILES["cards"].read_text()
            pattern = rf'^\s*"{card_id}":\s*Card\([^)]+\),?\s*$'
            new_content = re.sub(pattern, '', content, flags=re.MULTILINE)
            compile(new_content, str(FILES["cards"]), "exec")
            FILES["cards"].write_text(new_content)
            log(f"  Removed from cards.py")

        if "unlocks.py" in refs:
            content = FILES["unlocks"].read_text()
            pattern = rf'^\s*"{card_id}":\s*\{{[^}}]+\}},?\s*$'
            new_content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
            compile(new_content, str(FILES["unlocks"]), "exec")
            FILES["unlocks"].write_text(new_content)
            log(f"  Removed from unlocks.py")

        if is_leader and "content_registry.py" in refs:
            content = FILES["content_registry"].read_text()
            pattern = rf'\{{"name":[^}}]*"card_id":\s*"{card_id}"[^}}]*\}},?\s*'
            new_content = re.sub(pattern, '', content)
            pattern2 = rf'^\s*"{card_id}":\s*\([^)]+\),?\s*$'
            new_content = re.sub(pattern2, '', new_content, flags=re.MULTILINE)
            pattern3 = rf'^\s*"{card_id}":\s*"[^"]+",?\s*$'
            new_content = re.sub(pattern3, '', new_content, flags=re.MULTILINE)
            compile(new_content, str(FILES["content_registry"]), "exec")
            FILES["content_registry"].write_text(new_content)
            log(f"  Removed from content_registry.py")

        if "card_catalog.json" in refs:
            _remove_card_from_json_file(FILES["card_catalog"], card_id)
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

        if "asset_files" in refs:
            backup_folder = get_backup_folder()
            for _, asset_path in refs["asset_files"]:
                full_path = ROOT / asset_path
                if full_path.exists() and backup_folder:
                    backup_path = backup_folder / Path(asset_path).name
                    shutil.move(str(full_path), str(backup_path))
                    log(f"  Moved asset to backup: {asset_path}")

        return True

    except Exception as e:
        log(f"ERROR during delete: {e}")
        print(f"[ERROR] {e}")
        print("Attempting rollback...")

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


def _remove_card_from_json_file(path: Path, card_id: str):
    """Remove card from a JSON file (card_catalog.json format)."""
    if not path.exists():
        return

    data = json.loads(path.read_text())

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

    total = len(renames)
    for idx, rename in enumerate(renames, 1):
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

        progress_bar(idx, total, "Renames")

    print(f"\n=== BATCH COMPLETE ===")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {error_count}")
