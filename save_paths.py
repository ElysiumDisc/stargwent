"""
Save Paths Module for Stargwent
Implements XDG Base Directory Specification for Linux compatibility.
Works correctly with both .deb and AppImage builds.
"""
import os
import shutil

# Application name for XDG directories
APP_NAME = "stargwent"

# File names (without paths)
DECK_SAVE_FILENAME = "player_decks.json"
UNLOCK_SAVE_FILENAME = "player_unlocks.json"
SETTINGS_FILENAME = "game_settings.json"


def get_data_dir() -> str:
    """
    Get the XDG data directory for Stargwent.

    Uses $XDG_DATA_HOME if set, otherwise defaults to ~/.local/share/stargwent/
    This ensures saves work correctly regardless of how the game is launched
    (from terminal, .deb install, AppImage, etc.)

    Returns:
        Path to the data directory (created if it doesn't exist)
    """
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
