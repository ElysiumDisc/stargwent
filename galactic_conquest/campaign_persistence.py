"""
STARGWENT - GALACTIC CONQUEST - Campaign Persistence

Save/load/clear campaign state to/from JSON on disk.
"""

import json
import os
import shutil

from save_paths import get_data_dir, sync_saves

CAMPAIGN_SAVE_FILENAME = "galactic_conquest_save.json"
CAMPAIGN_V10_BACKUP_FILENAME = "galactic_conquest_save.json.v10.bak"
CONQUEST_SETTINGS_FILENAME = "conquest_settings.json"


def get_campaign_save_path() -> str:
    """Get the full path to the campaign save file."""
    return os.path.join(get_data_dir(), CAMPAIGN_SAVE_FILENAME)


def _backup_pre_11_save_if_needed(path: str) -> None:
    """Copy an existing pre-11 save to a .v10.bak file once.

    Runs before the first 11.0 overwrite so users can recover their old
    save if a migration bug surfaces. No-op if the backup already exists
    or if the current file is already at schema 11.
    """
    if not os.path.exists(path):
        return
    backup_path = os.path.join(get_data_dir(), CAMPAIGN_V10_BACKUP_FILENAME)
    if os.path.exists(backup_path):
        return
    try:
        with open(path, "r") as f:
            existing = json.load(f)
        if existing.get("schema_version", 10) >= 11:
            return  # Already on the new schema; nothing to back up.
        shutil.copy2(path, backup_path)
        print(f"[conquest] Backed up pre-11 save to {backup_path}")
    except (IOError, OSError, json.JSONDecodeError) as e:
        print(f"[conquest] Pre-11 backup skipped: {e}")


def save_campaign(state) -> bool:
    """Save campaign state to disk. Returns True on success."""
    path = get_campaign_save_path()
    try:
        _backup_pre_11_save_if_needed(path)
        data = state.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        sync_saves()
        print(f"[conquest] Campaign saved to {path}")
        return True
    except (IOError, OSError, TypeError) as e:
        print(f"[conquest] Failed to save campaign: {e}")
        return False


def load_campaign():
    """Load campaign state from disk. Returns CampaignState or None."""
    from .campaign_state import CampaignState
    path = get_campaign_save_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        state = CampaignState.from_dict(data)
        print(f"[conquest] Campaign loaded from {path}")
        return state
    except (IOError, OSError, json.JSONDecodeError, KeyError) as e:
        print(f"[conquest] Failed to load campaign: {e}")
        return None


def clear_campaign() -> bool:
    """Delete the campaign save file. Returns True on success."""
    path = get_campaign_save_path()
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"[conquest] Campaign save deleted: {path}")
            return True
        except OSError as e:
            print(f"[conquest] Failed to delete campaign save: {e}")
            return False
    return True


def has_campaign_save() -> bool:
    """Check if a campaign save file exists."""
    return os.path.exists(get_campaign_save_path())


# --- Conquest Run Settings (persist between sessions) ---

def get_conquest_settings_path() -> str:
    """Get path to conquest settings file."""
    return os.path.join(get_data_dir(), CONQUEST_SETTINGS_FILENAME)


def load_conquest_settings() -> dict:
    """Load conquest run settings. Returns defaults if no file exists."""
    defaults = {
        "friendly_faction": None,
        "neutral_count": 5,
        "enemy_leaders": {},  # faction → leader name
        # G3: coalition-against-player feature flag (11.0). Defaults on;
        # flip to false in conquest_settings.json if emergent behavior
        # locks players out of a run.
        "coalition_enabled": True,
    }
    path = get_conquest_settings_path()
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r") as f:
            data = json.load(f)
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    except (IOError, json.JSONDecodeError):
        return defaults


def save_conquest_settings(settings: dict) -> bool:
    """Save conquest run settings to disk."""
    path = get_conquest_settings_path()
    try:
        with open(path, "w") as f:
            json.dump(settings, f, indent=2)
        sync_saves()
        return True
    except (IOError, OSError):
        return False
