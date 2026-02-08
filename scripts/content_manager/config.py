"""Configuration constants for the content manager."""

import sys
from pathlib import Path

# Root of the project - two levels up from this package
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

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

# User content directory
USER_CONTENT_DIR = ROOT / "user_content"
