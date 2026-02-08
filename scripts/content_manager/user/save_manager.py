"""User workflow: Save manager (backup/restore saves) - uses XDG-compliant save_paths."""

import json
import shutil
import datetime
from pathlib import Path

from ..config import ROOT, BACKUP_DIR
from ..ui import print_header, get_input, get_int, confirm


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


def _get_save_paths():
    """Get save file paths using XDG-compliant save_paths module."""
    try:
        from save_paths import get_deck_save_path, get_unlock_save_path, get_settings_path
        return [
            Path(get_unlock_save_path()),
            Path(get_deck_save_path()),
            Path(get_settings_path()),
        ]
    except ImportError:
        # Fallback to ROOT-relative paths
        return [
            ROOT / "player_unlocks.json",
            ROOT / "player_decks.json",
            ROOT / "player_stats.json",
        ]


def backup_saves():
    """Backup player save files."""
    save_files = _get_save_paths()

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

    # Determine restore target directory using save_paths
    try:
        from save_paths import get_data_dir
        restore_dir = Path(get_data_dir())
    except ImportError:
        restore_dir = ROOT

    for save_file in selected.iterdir():
        if save_file.suffix == ".json":
            shutil.copy2(save_file, restore_dir / save_file.name)
            print(f"  Restored: {save_file.name} -> {restore_dir}")

    print("\n[OK] Saves restored")


def view_save_progress():
    """Display current unlock progress."""
    try:
        from save_paths import get_unlock_save_path
        unlocks_file = Path(get_unlock_save_path())
    except ImportError:
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
    save_files = _get_save_paths()

    for save_file in save_files:
        if save_file.exists():
            save_file.unlink()
            print(f"  Deleted: {save_file.name}")

    print("\n[OK] Save data reset. A backup was created first.")
