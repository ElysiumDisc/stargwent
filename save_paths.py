"""
Save Paths Module for Stargwent
Implements XDG Base Directory Specification for Linux compatibility.
Works correctly with both .deb and AppImage builds.
On web (Pygbag/Emscripten), uses IDBFS virtual filesystem with IndexedDB sync.
"""
import json
import os
import shutil
import sys

# Application name for XDG directories
APP_NAME = "stargwent"

# File names (without paths)
DECK_SAVE_FILENAME = "player_decks.json"
UNLOCK_SAVE_FILENAME = "player_unlocks.json"
SETTINGS_FILENAME = "game_settings.json"


def get_data_dir() -> str:
    """
    Get the data directory for Stargwent.

    - Web (Emscripten): /home/web_user/.local/share/stargwent/ (Pygbag's IDBFS)
    - Desktop: $XDG_DATA_HOME/stargwent or ~/.local/share/stargwent/

    Returns:
        Path to the data directory (created if it doesn't exist)
    """
    if sys.platform == "emscripten":
        # Pygbag provides a virtual FS backed by IndexedDB
        data_dir = f"/home/web_user/.local/share/{APP_NAME}"
    else:
        # Check XDG_DATA_HOME environment variable
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            data_dir = os.path.join(xdg_data_home, APP_NAME)
        else:
            # Default XDG location: ~/.local/share/stargwent/
            home = os.path.expanduser("~")
            data_dir = os.path.join(home, ".local", "share", APP_NAME)

    # Create directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        print(f"[save_paths] Created data directory: {data_dir}")

    return data_dir


def get_deck_save_path() -> str:
    """Get the full path to player_decks.json"""
    return os.path.join(get_data_dir(), DECK_SAVE_FILENAME)


def get_unlock_save_path() -> str:
    """Get the full path to player_unlocks.json"""
    return os.path.join(get_data_dir(), UNLOCK_SAVE_FILENAME)


def get_settings_path() -> str:
    """Get the full path to game_settings.json"""
    return os.path.join(get_data_dir(), SETTINGS_FILENAME)


def migrate_legacy_saves():
    """
    Migrate save files from old relative locations to XDG directory.

    This function checks for save files in the current working directory
    (legacy behavior) and moves them to the proper XDG location if they
    don't already exist there.

    Called once on startup to ensure smooth transition for existing players.
    """
    data_dir = get_data_dir()
    migrated = []

    # List of files to potentially migrate
    files_to_migrate = [
        (DECK_SAVE_FILENAME, get_deck_save_path()),
        (UNLOCK_SAVE_FILENAME, get_unlock_save_path()),
        (SETTINGS_FILENAME, get_settings_path()),
    ]

    for old_name, new_path in files_to_migrate:
        old_path = old_name  # Relative path in current directory

        # Check if legacy file exists in current directory
        if os.path.exists(old_path) and os.path.isfile(old_path):
            # Only migrate if target doesn't already exist
            if not os.path.exists(new_path):
                try:
                    shutil.copy2(old_path, new_path)
                    migrated.append(old_name)
                    print(f"[save_paths] Migrated {old_name} -> {new_path}")
                except (IOError, OSError) as e:
                    print(f"[save_paths] Failed to migrate {old_name}: {e}")
            else:
                # Target exists - check if we should merge or skip
                # For now, prefer the XDG location (newer) over legacy
                print(f"[save_paths] Skipping {old_name} - already exists at {new_path}")

    if migrated:
        print(f"[save_paths] Migration complete: {len(migrated)} files migrated")
        print(f"[save_paths] You may delete the old files from the game directory")

    return migrated


def atomic_write_json(path: str, obj, *, indent: int = 2) -> bool:
    """Write JSON to *path* atomically: serialize to a sibling .tmp file
    then rename over the target. Prevents truncation/corruption when the
    process is killed mid-write (power loss, SIGKILL, OOM).

    On Emscripten the rename pattern is preserved so IDBFS sees a single
    coherent state, then sync_saves() flushes to IndexedDB.

    Returns True on success, False on any I/O / serialization error.
    """
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(obj, f, indent=indent)
        os.replace(tmp_path, path)
        sync_saves()
        return True
    except (OSError, TypeError, ValueError) as e:
        print(f"[save_paths] atomic_write_json({path}) failed: {e}")
        # Best-effort cleanup of the partial temp file
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


def sync_saves():
    """Flush virtual filesystem writes to IndexedDB on web platform.

    On desktop this is a no-op. On Emscripten/Pygbag, calls FS.syncfs()
    to persist IDBFS writes to the browser's IndexedDB.
    """
    if sys.platform != "emscripten":
        return
    try:
        from platform import window  # Pygbag JS interop
        window.FS.syncfs(False)
    except Exception as e:
        print(f"[save_paths] syncfs failed: {e}")


def get_all_save_paths() -> dict:
    """
    Get all save file paths as a dictionary.

    Returns:
        Dict with keys 'decks', 'unlocks', 'settings' and their full paths
    """
    return {
        "decks": get_deck_save_path(),
        "unlocks": get_unlock_save_path(),
        "settings": get_settings_path(),
        "data_dir": get_data_dir(),
    }


# Run migration on module import to ensure saves are in the right place
# This happens once when the game starts
_migration_done = False

def ensure_migration():
    """Ensure legacy save migration has been performed."""
    global _migration_done
    if not _migration_done:
        migrate_legacy_saves()
        _migration_done = True
