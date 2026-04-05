"""
User Content Loader for Stargwent.

This module loads user-created content (cards, leaders, factions) from the
user_content directory and registers them with the game's registries.

IMPORTANT: Users can ONLY use existing game abilities and mechanics.
No new abilities or powers can be created through this system.

Usage:
    from user_content_loader import UserContentLoader

    # Load all user content at game startup
    loader = UserContentLoader()
    loader.load_all()

    # Access loaded content
    user_cards = loader.user_cards
    user_leaders = loader.user_leaders
    user_factions = loader.user_factions
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
import datetime


# Root directory of the game
ROOT = Path(__file__).resolve().parent

# User content directory
USER_CONTENT_DIR = ROOT / "user_content"
ENABLED_FILE = USER_CONTENT_DIR / "enabled.json"


@dataclass
class ValidationError:
    """Represents a content validation error."""
    content_type: str  # 'card', 'leader', 'faction', 'pack'
    content_id: str
    field: str
    message: str


class UserContentLoader:
    """
    Loads and validates user-created content.

    All user content uses ONLY existing game abilities and mechanics.
    This loader validates content against the existing ability enum
    and other game constraints.
    """

    def __init__(self):
        self.user_cards: Dict[str, Any] = {}
        self.user_leaders: List[Dict[str, Any]] = []
        self.user_factions: Dict[str, Dict[str, Any]] = {}
        self.enabled_config: Dict[str, Any] = {}
        self.validation_errors: List[ValidationError] = []
        self._loaded = False

        # Cache of valid values from game code
        self._valid_abilities: Optional[Set[str]] = None
        self._valid_factions: Optional[Set[str]] = None
        self._existing_card_ids: Optional[Set[str]] = None

    # =========================================================================
    # LOADING
    # =========================================================================

    def load_all(self) -> bool:
        """
        Load all enabled user content.

        Called at game startup before main menu.

        Returns:
            True if loading succeeded (even with some validation errors),
            False if critical failure occurred.
        """
        if self._loaded:
            return True

        try:
            # Ensure user_content directory exists
            self._ensure_directories()

            # Load enabled configuration
            self.load_enabled_config()

            # Load content in order: factions first (may define new factions),
            # then leaders, then cards
            self.load_user_factions()
            self.load_user_leaders()
            self.load_user_cards()

            # Load content packs
            self.load_content_packs()

            self._loaded = True
            return True

        except Exception as e:
            print(f"[USER CONTENT] Critical error loading user content: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _ensure_directories(self):
        """Ensure user content directories exist."""
        dirs = [
            USER_CONTENT_DIR,
            USER_CONTENT_DIR / "cards",
            USER_CONTENT_DIR / "leaders",
            USER_CONTENT_DIR / "factions",
            USER_CONTENT_DIR / "packs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Ensure enabled.json exists
        if not ENABLED_FILE.exists():
            self._save_enabled_config({
                "version": "1.0",
                "enabled_cards": [],
                "enabled_leaders": [],
                "enabled_factions": [],
                "enabled_packs": [],
                "last_updated": None
            })

    def load_enabled_config(self):
        """Load the enabled.json configuration."""
        try:
            if ENABLED_FILE.exists():
                self.enabled_config = json.loads(ENABLED_FILE.read_text())
            else:
                self.enabled_config = {
                    "version": "1.0",
                    "enabled_cards": [],
                    "enabled_leaders": [],
                    "enabled_factions": [],
                    "enabled_packs": [],
                    "last_updated": None
                }
        except json.JSONDecodeError as e:
            print(f"[USER CONTENT] Error reading enabled.json: {e}")
            self.enabled_config = {
                "version": "1.0",
                "enabled_cards": [],
                "enabled_leaders": [],
                "enabled_factions": [],
                "enabled_packs": [],
            }

    def _save_enabled_config(self, config: Dict[str, Any] = None):
        """Save the enabled configuration."""
        if config is None:
            config = self.enabled_config
        config["last_updated"] = datetime.datetime.now().isoformat()
        ENABLED_FILE.write_text(json.dumps(config, indent=2))

    def load_user_cards(self):
        """Load all enabled user cards from user_content/cards/."""
        cards_dir = USER_CONTENT_DIR / "cards"
        if not cards_dir.exists():
            return

        enabled_cards = set(self.enabled_config.get("enabled_cards", []))

        for card_dir in cards_dir.iterdir():
            if not card_dir.is_dir():
                continue

            card_json = card_dir / "card.json"
            if not card_json.exists():
                continue

            try:
                card_data = json.loads(card_json.read_text())
                card_id = card_data.get("card_id", card_dir.name)

                # Skip if not enabled (unless no cards are configured = all enabled)
                if enabled_cards and card_id not in enabled_cards:
                    continue

                # Validate the card
                errors = self.validate_card(card_data, card_dir)
                if errors:
                    self.validation_errors.extend(errors)
                    # Still load the card even with errors - game can handle it
                    print(f"[USER CONTENT] Card '{card_id}' has validation errors")

                # Create card object and store
                card = self._create_card_from_data(card_data, card_dir)
                if card:
                    self.user_cards[card_id] = card
                    print(f"[USER CONTENT] Loaded card: {card_id}")

            except json.JSONDecodeError as e:
                print(f"[USER CONTENT] Invalid JSON in {card_json}: {e}")
            except Exception as e:
                print(f"[USER CONTENT] Error loading card from {card_dir}: {e}")

    def load_user_leaders(self):
        """Load all enabled user leaders from user_content/leaders/."""
        leaders_dir = USER_CONTENT_DIR / "leaders"
        if not leaders_dir.exists():
            return

        enabled_leaders = set(self.enabled_config.get("enabled_leaders", []))

        for leader_dir in leaders_dir.iterdir():
            if not leader_dir.is_dir():
                continue

            leader_json = leader_dir / "leader.json"
            if not leader_json.exists():
                continue

            try:
                leader_data = json.loads(leader_json.read_text())
                leader_id = leader_data.get("card_id", leader_dir.name)

                # Skip if not enabled (unless no leaders are configured = all enabled)
                if enabled_leaders and leader_id not in enabled_leaders:
                    continue

                # Validate the leader
                errors = self.validate_leader(leader_data, leader_dir)
                if errors:
                    self.validation_errors.extend(errors)
                    print(f"[USER CONTENT] Leader '{leader_id}' has validation errors")

                # Store leader data
                self.user_leaders.append(leader_data)
                print(f"[USER CONTENT] Loaded leader: {leader_id}")

            except json.JSONDecodeError as e:
                print(f"[USER CONTENT] Invalid JSON in {leader_json}: {e}")
            except Exception as e:
                print(f"[USER CONTENT] Error loading leader from {leader_dir}: {e}")

    def load_user_factions(self):
        """Load all enabled user factions from user_content/factions/."""
        factions_dir = USER_CONTENT_DIR / "factions"
        if not factions_dir.exists():
            return

        enabled_factions = set(self.enabled_config.get("enabled_factions", []))

        for faction_dir in factions_dir.iterdir():
            if not faction_dir.is_dir():
                continue

            faction_json = faction_dir / "faction.json"
            if not faction_json.exists():
                continue

            try:
                faction_data = json.loads(faction_json.read_text())
                faction_name = faction_data.get("name", faction_dir.name)

                # Skip if not enabled (unless no factions are configured = all enabled)
                if enabled_factions and faction_name not in enabled_factions:
                    continue

                # Validate the faction
                errors = self.validate_faction(faction_data, faction_dir)
                if errors:
                    self.validation_errors.extend(errors)
                    print(f"[USER CONTENT] Faction '{faction_name}' has validation errors")

                # Store faction data
                self.user_factions[faction_name] = faction_data
                print(f"[USER CONTENT] Loaded faction: {faction_name}")

                # Also load faction's cards and leaders
                self._load_faction_content(faction_data, faction_dir)

            except json.JSONDecodeError as e:
                print(f"[USER CONTENT] Invalid JSON in {faction_json}: {e}")
            except Exception as e:
                print(f"[USER CONTENT] Error loading faction from {faction_dir}: {e}")

    def _load_faction_content(self, faction_data: Dict, faction_dir: Path):
        """Load cards and leaders belonging to a user faction."""
        faction_name = faction_data.get("name")

        # Load faction's cards
        faction_cards_dir = faction_dir / "cards"
        if faction_cards_dir.exists():
            for card_dir in faction_cards_dir.iterdir():
                if not card_dir.is_dir():
                    continue

                card_json = card_dir / "card.json"
                if not card_json.exists():
                    continue

                try:
                    card_data = json.loads(card_json.read_text())
                    # Ensure faction is set to this faction
                    card_data["faction"] = faction_name
                    card_id = card_data.get("card_id", card_dir.name)

                    card = self._create_card_from_data(card_data, card_dir)
                    if card:
                        self.user_cards[card_id] = card
                        print(f"[USER CONTENT] Loaded faction card: {card_id}")

                except Exception as e:
                    print(f"[USER CONTENT] Error loading faction card {card_dir}: {e}")

        # Load faction's leaders
        faction_leaders_dir = faction_dir / "leaders"
        if faction_leaders_dir.exists():
            for leader_dir in faction_leaders_dir.iterdir():
                if not leader_dir.is_dir():
                    continue

                leader_json = leader_dir / "leader.json"
                if not leader_json.exists():
                    continue

                try:
                    leader_data = json.loads(leader_json.read_text())
                    # Ensure faction is set to this faction
                    leader_data["faction"] = faction_name
                    leader_id = leader_data.get("card_id", leader_dir.name)

                    self.user_leaders.append(leader_data)
                    print(f"[USER CONTENT] Loaded faction leader: {leader_id}")

                except Exception as e:
                    print(f"[USER CONTENT] Error loading faction leader {leader_dir}: {e}")

    def load_content_packs(self):
        """Load enabled content packs from user_content/packs/."""
        packs_dir = USER_CONTENT_DIR / "packs"
        if not packs_dir.exists():
            return

        enabled_packs = set(self.enabled_config.get("enabled_packs", []))

        for pack_dir in packs_dir.iterdir():
            if not pack_dir.is_dir():
                continue

            manifest_json = pack_dir / "manifest.json"
            if not manifest_json.exists():
                continue

            try:
                manifest = json.loads(manifest_json.read_text())
                pack_name = manifest.get("name", pack_dir.name)

                # Skip if not enabled
                if enabled_packs and pack_name not in enabled_packs:
                    continue

                print(f"[USER CONTENT] Loading pack: {pack_name}")

                # Load pack's cards
                pack_cards_dir = pack_dir / "cards"
                if pack_cards_dir.exists():
                    for card_dir in pack_cards_dir.iterdir():
                        if card_dir.is_dir():
                            card_json = card_dir / "card.json"
                            if card_json.exists():
                                card_data = json.loads(card_json.read_text())
                                card = self._create_card_from_data(card_data, card_dir)
                                if card:
                                    self.user_cards[card_data["card_id"]] = card

                # Load pack's leaders
                pack_leaders_dir = pack_dir / "leaders"
                if pack_leaders_dir.exists():
                    for leader_dir in pack_leaders_dir.iterdir():
                        if leader_dir.is_dir():
                            leader_json = leader_dir / "leader.json"
                            if leader_json.exists():
                                leader_data = json.loads(leader_json.read_text())
                                self.user_leaders.append(leader_data)

            except Exception as e:
                print(f"[USER CONTENT] Error loading pack {pack_dir}: {e}")

    # =========================================================================
    # CARD CREATION
    # =========================================================================

    def _create_card_from_data(self, data: Dict, content_dir: Path) -> Optional[Any]:
        """
        Create a Card object from user content data.

        Returns None if card cannot be created.
        """
        try:
            # Import Card class
            from cards import Card

            card_id = data.get("card_id")
            if not card_id:
                return None

            # Get faction constant or name
            faction = data.get("faction", "Neutral")

            # Try to resolve faction to constant
            faction_constant = self._resolve_faction(faction)

            # Get ability (must be valid or None)
            ability = data.get("ability")
            if ability and not self.validate_ability(ability):
                print(f"[USER CONTENT] Invalid ability '{ability}' for card {card_id}, setting to None")
                ability = None

            # Create the card
            card = Card(
                id=card_id,
                name=data.get("name", card_id),
                faction=faction_constant,
                power=data.get("power", 1),
                row=data.get("row", "close"),
                ability=ability,
            )

            # Set custom image path if exists
            card_image = content_dir / "card.png"
            if card_image.exists():
                card.image_path = str(card_image)

            return card

        except Exception as e:
            print(f"[USER CONTENT] Error creating card: {e}")
            return None

    def _resolve_faction(self, faction_name: str) -> str:
        """
        Resolve a faction name to its constant value.

        Returns the faction name as-is if it's a user faction or
        resolves standard factions to their constant values.
        """
        try:
            from cards import (
                FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
                FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL
            )

            faction_map = {
                "Tau'ri": FACTION_TAURI,
                "Tauri": FACTION_TAURI,
                "FACTION_TAURI": FACTION_TAURI,
                "Goa'uld": FACTION_GOAULD,
                "Goauld": FACTION_GOAULD,
                "FACTION_GOAULD": FACTION_GOAULD,
                "Jaffa Rebellion": FACTION_JAFFA,
                "Jaffa": FACTION_JAFFA,
                "FACTION_JAFFA": FACTION_JAFFA,
                "Lucian Alliance": FACTION_LUCIAN,
                "Lucian": FACTION_LUCIAN,
                "FACTION_LUCIAN": FACTION_LUCIAN,
                "Asgard": FACTION_ASGARD,
                "FACTION_ASGARD": FACTION_ASGARD,
                "Neutral": FACTION_NEUTRAL,
                "FACTION_NEUTRAL": FACTION_NEUTRAL,
            }

            return faction_map.get(faction_name, faction_name)

        except ImportError:
            return faction_name

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate_ability(self, ability: str) -> bool:
        """
        Ensure ability exists in the game's Ability enum.

        Returns True if ability is valid or None, False otherwise.
        """
        if not ability:
            return True

        # Cache valid abilities
        if self._valid_abilities is None:
            try:
                from abilities import Ability
                self._valid_abilities = {a.value for a in Ability}
            except ImportError:
                self._valid_abilities = set()
                return True  # Can't validate, assume valid

        # Handle multiple abilities (comma-separated)
        abilities = [a.strip() for a in ability.split(",")]
        for a in abilities:
            if a not in self._valid_abilities:
                return False
        return True

    def validate_card(self, data: Dict, content_dir: Path) -> List[ValidationError]:
        """Validate a card definition."""
        errors = []
        card_id = data.get("card_id", "unknown")

        # Required fields
        required = ["card_id", "name", "faction", "power", "row"]
        for field in required:
            if field not in data:
                errors.append(ValidationError(
                    "card", card_id, field,
                    f"Missing required field: {field}"
                ))

        # Validate row
        valid_rows = ["close", "ranged", "siege", "agile", "special", "weather"]
        row = data.get("row")
        if row and row not in valid_rows:
            errors.append(ValidationError(
                "card", card_id, "row",
                f"Invalid row '{row}'. Must be one of: {', '.join(valid_rows)}"
            ))

        # Validate power
        power = data.get("power", 0)
        if not isinstance(power, int) or power < 0 or power > 20:
            errors.append(ValidationError(
                "card", card_id, "power",
                f"Power must be an integer 0-20, got: {power}"
            ))

        # Validate ability
        ability = data.get("ability")
        if ability and not self.validate_ability(ability):
            errors.append(ValidationError(
                "card", card_id, "ability",
                f"Invalid ability '{ability}'. Must be from existing Ability enum."
            ))

        # Validate rarity if present
        valid_rarities = ["common", "rare", "epic", "legendary"]
        rarity = data.get("rarity")
        if rarity and rarity not in valid_rarities:
            errors.append(ValidationError(
                "card", card_id, "rarity",
                f"Invalid rarity '{rarity}'. Must be one of: {', '.join(valid_rarities)}"
            ))

        # Check for image (warning only)
        card_image = content_dir / "card.png"
        if not card_image.exists():
            errors.append(ValidationError(
                "card", card_id, "image",
                "Missing card.png image file (will use placeholder)"
            ))

        return errors

    def validate_leader(self, data: Dict, content_dir: Path) -> List[ValidationError]:
        """Validate a leader definition."""
        errors = []
        leader_id = data.get("card_id", "unknown")

        # Required fields
        required = ["card_id", "name", "faction", "ability", "ability_desc"]
        for field in required:
            if field not in data:
                errors.append(ValidationError(
                    "leader", leader_id, field,
                    f"Missing required field: {field}"
                ))

        # Validate ability_type if present
        valid_ability_types = [
            "DRAW_ON_PASS", "DRAW_ON_ROUND_START", "POWER_BOOST_ROW",
            "POWER_BOOST_UNIT_TYPE", "FIRST_UNIT_BOOST", "ON_SPY_PLAYED",
            "WEATHER_IMMUNITY", "CLONE_STRONGEST", "PEEK_CARDS",
            "STEAL_UNIT", "AUTO_SCORCH", "ROUND_POWER_BONUS",
            "CUSTOM"  # Allow custom but it uses existing mechanics
        ]
        ability_type = data.get("ability_type")
        if ability_type and ability_type not in valid_ability_types:
            errors.append(ValidationError(
                "leader", leader_id, "ability_type",
                f"Invalid ability_type '{ability_type}'. Must use existing leader mechanics."
            ))

        # Check for portrait
        portrait = content_dir / "portrait.png"
        leader_portrait = content_dir / f"{leader_id}_leader.png"
        if not portrait.exists() and not leader_portrait.exists():
            errors.append(ValidationError(
                "leader", leader_id, "portrait",
                "Missing portrait.png image file (will use placeholder)"
            ))

        return errors

    def validate_faction(self, data: Dict, content_dir: Path) -> List[ValidationError]:
        """Validate a faction definition."""
        errors = []
        faction_name = data.get("name", "unknown")

        # Required fields
        required = ["name", "constant", "passive_name", "passive_type",
                    "power_name", "power_type"]
        for field in required:
            if field not in data:
                errors.append(ValidationError(
                    "faction", faction_name, field,
                    f"Missing required field: {field}"
                ))

        # Validate passive_type
        valid_passive_types = [
            "EXTRA_DRAW", "SPY_DRAW_BONUS", "ROW_POWER_BOOST",
            "HERO_POWER_BOOST", "BROTHERHOOD", "WEATHER_IMMUNITY"
        ]
        passive_type = data.get("passive_type")
        if passive_type and passive_type not in valid_passive_types:
            errors.append(ValidationError(
                "faction", faction_name, "passive_type",
                f"Invalid passive_type '{passive_type}'. Must use existing faction mechanics."
            ))

        # Validate power_type
        valid_power_types = [
            "SCORCH_ROWS", "REVIVE_UNITS", "DAMAGE_ALL",
            "DRAW_AND_DISCARD", "SWAP_ROWS", "RETURN_UNITS"
        ]
        power_type = data.get("power_type")
        if power_type and power_type not in valid_power_types:
            errors.append(ValidationError(
                "faction", faction_name, "power_type",
                f"Invalid power_type '{power_type}'. Must use existing faction mechanics."
            ))

        # Validate colors
        for color_field in ["primary_color", "secondary_color", "glow_color"]:
            color = data.get(color_field)
            if color:
                if not isinstance(color, (list, tuple)) or len(color) != 3:
                    errors.append(ValidationError(
                        "faction", faction_name, color_field,
                        f"Color must be [R, G, B] array with 3 values"
                    ))
                elif not all(isinstance(c, int) and 0 <= c <= 255 for c in color):
                    errors.append(ValidationError(
                        "faction", faction_name, color_field,
                        f"Color values must be integers 0-255"
                    ))

        return errors

    def validate_all(self) -> List[ValidationError]:
        """
        Validate all user content and return list of errors.

        This can be called from content manager to check content.
        """
        errors = []

        # Validate cards
        cards_dir = USER_CONTENT_DIR / "cards"
        if cards_dir.exists():
            for card_dir in cards_dir.iterdir():
                if card_dir.is_dir():
                    card_json = card_dir / "card.json"
                    if card_json.exists():
                        try:
                            data = json.loads(card_json.read_text())
                            errors.extend(self.validate_card(data, card_dir))
                        except json.JSONDecodeError as e:
                            errors.append(ValidationError(
                                "card", card_dir.name, "json",
                                f"Invalid JSON: {e}"
                            ))

        # Validate leaders
        leaders_dir = USER_CONTENT_DIR / "leaders"
        if leaders_dir.exists():
            for leader_dir in leaders_dir.iterdir():
                if leader_dir.is_dir():
                    leader_json = leader_dir / "leader.json"
                    if leader_json.exists():
                        try:
                            data = json.loads(leader_json.read_text())
                            errors.extend(self.validate_leader(data, leader_dir))
                        except json.JSONDecodeError as e:
                            errors.append(ValidationError(
                                "leader", leader_dir.name, "json",
                                f"Invalid JSON: {e}"
                            ))

        # Validate factions
        factions_dir = USER_CONTENT_DIR / "factions"
        if factions_dir.exists():
            for faction_dir in factions_dir.iterdir():
                if faction_dir.is_dir():
                    faction_json = faction_dir / "faction.json"
                    if faction_json.exists():
                        try:
                            data = json.loads(faction_json.read_text())
                            errors.extend(self.validate_faction(data, faction_dir))
                        except json.JSONDecodeError as e:
                            errors.append(ValidationError(
                                "faction", faction_dir.name, "json",
                                f"Invalid JSON: {e}"
                            ))

        return errors

    # =========================================================================
    # CONTENT REGISTRATION
    # =========================================================================

    def register_content(self):
        """
        Register loaded user content with game registries.

        Called after load_all() to inject content into the game.
        """
        self._register_cards()
        self._register_leaders()
        self._register_factions()

    def _register_cards(self):
        """Register user cards with the game's ALL_CARDS registry."""
        if not self.user_cards:
            return

        try:
            from cards import ALL_CARDS

            for card_id, card in self.user_cards.items():
                if card_id not in ALL_CARDS:
                    ALL_CARDS[card_id] = card
                    print(f"[USER CONTENT] Registered card: {card_id}")
                else:
                    print(f"[USER CONTENT] Skipped duplicate card: {card_id}")

        except ImportError as e:
            print(f"[USER CONTENT] Cannot register cards: {e}")

    def _register_leaders(self):
        """Register user leaders with the game's leader registries."""
        if not self.user_leaders:
            return

        try:
            from content_registry import (
                BASE_FACTION_LEADERS,
                UNLOCKABLE_LEADERS,
                LEADER_NAME_BY_ID,
                ALL_LEADER_IDS_BY_FACTION,
                LEADER_REGISTRY,
                LEADER_BANNER_NAMES
            )

            for leader in self.user_leaders:
                card_id = leader.get("card_id")
                faction = leader.get("faction")
                name = leader.get("name")
                is_base = leader.get("is_base", True)

                if not card_id or not faction:
                    continue

                # Skip if already registered
                if card_id in LEADER_NAME_BY_ID:
                    print(f"[USER CONTENT] Skipped duplicate leader: {card_id}")
                    continue

                # Add to name mapping
                LEADER_NAME_BY_ID[card_id] = name

                # Add to faction leader IDs
                if faction not in ALL_LEADER_IDS_BY_FACTION:
                    ALL_LEADER_IDS_BY_FACTION[faction] = []
                ALL_LEADER_IDS_BY_FACTION[faction].append(card_id)

                # Add to banner names if provided
                banner_name = leader.get("banner_name", name)
                LEADER_BANNER_NAMES[card_id] = banner_name

                # Add to appropriate registry
                target_registry = BASE_FACTION_LEADERS if is_base else UNLOCKABLE_LEADERS
                if faction not in target_registry:
                    target_registry[faction] = []

                leader_entry = {
                    "name": name,
                    "ability": leader.get("ability", ""),
                    "ability_desc": leader.get("ability_desc", ""),
                    "card_id": card_id,
                    "faction": faction,
                }

                # Check for custom image path
                if leader.get("image_path"):
                    leader_entry["image_path"] = leader["image_path"]

                target_registry[faction].append(leader_entry)

                # Add to full registry
                LEADER_REGISTRY.append(leader_entry)

                print(f"[USER CONTENT] Registered leader: {card_id}")

        except ImportError as e:
            print(f"[USER CONTENT] Cannot register leaders: {e}")

    def _register_factions(self):
        """
        Register user factions.

        Note: Full faction registration requires more game code changes.
        For now, this registers faction colors and basic info.
        """
        if not self.user_factions:
            return

        # Faction registration is more complex and requires
        # changes to power.py, game_config.py, etc.
        # For now, just log that factions are loaded
        for faction_name in self.user_factions:
            print(f"[USER CONTENT] Faction '{faction_name}' loaded (limited support)")

    # =========================================================================
    # CONTENT MANAGEMENT
    # =========================================================================

    def enable_content(self, content_type: str, content_id: str):
        """Enable a specific piece of content."""
        key = f"enabled_{content_type}s"
        if key not in self.enabled_config:
            self.enabled_config[key] = []

        if content_id not in self.enabled_config[key]:
            self.enabled_config[key].append(content_id)
            self._save_enabled_config()

    def disable_content(self, content_type: str, content_id: str):
        """Disable a specific piece of content."""
        key = f"enabled_{content_type}s"
        if key in self.enabled_config and content_id in self.enabled_config[key]:
            self.enabled_config[key].remove(content_id)
            self._save_enabled_config()

    def list_content(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all available user content with their enabled status.

        Returns dict with 'cards', 'leaders', 'factions', 'packs' keys.
        """
        result = {
            "cards": [],
            "leaders": [],
            "factions": [],
            "packs": []
        }

        enabled_cards = set(self.enabled_config.get("enabled_cards", []))
        enabled_leaders = set(self.enabled_config.get("enabled_leaders", []))
        enabled_factions = set(self.enabled_config.get("enabled_factions", []))
        enabled_packs = set(self.enabled_config.get("enabled_packs", []))

        # List cards
        cards_dir = USER_CONTENT_DIR / "cards"
        if cards_dir.exists():
            for card_dir in cards_dir.iterdir():
                if card_dir.is_dir():
                    card_json = card_dir / "card.json"
                    if card_json.exists():
                        try:
                            data = json.loads(card_json.read_text())
                            card_id = data.get("card_id", card_dir.name)
                            result["cards"].append({
                                "id": card_id,
                                "name": data.get("name", card_id),
                                "faction": data.get("faction"),
                                "enabled": not enabled_cards or card_id in enabled_cards,
                                "author": data.get("author", "Unknown")
                            })
                        except Exception as e:
                            print(f"[user_content] Warning: skipped invalid card {card_dir.name}: {e}")

        # List leaders
        leaders_dir = USER_CONTENT_DIR / "leaders"
        if leaders_dir.exists():
            for leader_dir in leaders_dir.iterdir():
                if leader_dir.is_dir():
                    leader_json = leader_dir / "leader.json"
                    if leader_json.exists():
                        try:
                            data = json.loads(leader_json.read_text())
                            leader_id = data.get("card_id", leader_dir.name)
                            result["leaders"].append({
                                "id": leader_id,
                                "name": data.get("name", leader_id),
                                "faction": data.get("faction"),
                                "enabled": not enabled_leaders or leader_id in enabled_leaders,
                                "author": data.get("author", "Unknown")
                            })
                        except Exception as e:
                            print(f"[user_content] Warning: skipped invalid leader {leader_dir.name}: {e}")

        # List factions
        factions_dir = USER_CONTENT_DIR / "factions"
        if factions_dir.exists():
            for faction_dir in factions_dir.iterdir():
                if faction_dir.is_dir():
                    faction_json = faction_dir / "faction.json"
                    if faction_json.exists():
                        try:
                            data = json.loads(faction_json.read_text())
                            faction_name = data.get("name", faction_dir.name)
                            result["factions"].append({
                                "id": faction_name,
                                "name": faction_name,
                                "enabled": not enabled_factions or faction_name in enabled_factions,
                                "author": data.get("author", "Unknown")
                            })
                        except Exception as e:
                            print(f"[user_content] Warning: skipped invalid faction {faction_dir.name}: {e}")

        # List packs
        packs_dir = USER_CONTENT_DIR / "packs"
        if packs_dir.exists():
            for pack_dir in packs_dir.iterdir():
                if pack_dir.is_dir():
                    manifest_json = pack_dir / "manifest.json"
                    if manifest_json.exists():
                        try:
                            data = json.loads(manifest_json.read_text())
                            pack_name = data.get("name", pack_dir.name)
                            result["packs"].append({
                                "id": pack_name,
                                "name": pack_name,
                                "version": data.get("version", "1.0"),
                                "enabled": not enabled_packs or pack_name in enabled_packs,
                                "author": data.get("author", "Unknown")
                            })
                        except Exception as e:
                            print(f"[user_content] Warning: skipped invalid pack {pack_dir.name}: {e}")

        return result


# ============================================================================
# MODULE-LEVEL FUNCTIONS
# ============================================================================

# Global loader instance
_loader: Optional[UserContentLoader] = None


def get_loader() -> UserContentLoader:
    """Get the global user content loader instance."""
    global _loader
    if _loader is None:
        _loader = UserContentLoader()
    return _loader


def load_user_content() -> bool:
    """
    Load all user content. Call at game startup.

    Returns True if successful, False otherwise.
    """
    loader = get_loader()
    success = loader.load_all()
    if success:
        loader.register_content()
    return success


def get_user_cards() -> Dict[str, Any]:
    """Get all loaded user cards."""
    return get_loader().user_cards


def get_user_leaders() -> List[Dict[str, Any]]:
    """Get all loaded user leaders."""
    return get_loader().user_leaders


def get_user_factions() -> Dict[str, Dict[str, Any]]:
    """Get all loaded user factions."""
    return get_loader().user_factions


# ============================================================================
# MULTIPLAYER PROTECTION - CRITICAL
# ============================================================================
# User content is NEVER allowed in multiplayer/LAN games.
# These functions help filter out user content for fair play.
# ============================================================================

# Set of all user content IDs (populated when content loads)
_user_card_ids: Set[str] = set()
_user_leader_ids: Set[str] = set()
_user_faction_names: Set[str] = set()


def _update_user_content_ids():
    """Update the sets of user content IDs from the loader."""
    global _user_card_ids, _user_leader_ids, _user_faction_names
    loader = get_loader()
    _user_card_ids = set(loader.user_cards.keys())
    _user_leader_ids = {l.get("card_id") for l in loader.user_leaders if l.get("card_id")}
    _user_faction_names = set(loader.user_factions.keys())


def is_user_card(card_id: str) -> bool:
    """
    Check if a card ID is user-created content.

    CRITICAL: Used to filter cards for multiplayer.

    Args:
        card_id: The card ID to check

    Returns:
        True if card is user-created, False if it's base game content
    """
    if not _user_card_ids:
        _update_user_content_ids()

    # User cards always start with "user_" prefix
    if card_id.startswith("user_"):
        return True

    return card_id in _user_card_ids


def is_user_leader(leader_id: str) -> bool:
    """
    Check if a leader ID is user-created content.

    CRITICAL: Used to filter leaders for multiplayer.

    Args:
        leader_id: The leader card_id to check

    Returns:
        True if leader is user-created, False if it's base game content
    """
    if not _user_leader_ids:
        _update_user_content_ids()

    # User leaders always start with "user_" prefix
    if leader_id.startswith("user_"):
        return True

    return leader_id in _user_leader_ids


def is_user_faction(faction_name: str) -> bool:
    """
    Check if a faction is user-created content.

    CRITICAL: Used to filter factions for multiplayer.

    Args:
        faction_name: The faction name to check

    Returns:
        True if faction is user-created, False if it's base game content
    """
    if not _user_faction_names:
        _update_user_content_ids()

    return faction_name in _user_faction_names


def filter_out_user_cards(card_ids: List[str]) -> List[str]:
    """
    Filter out all user-created cards from a list of card IDs.

    CRITICAL: Use this for multiplayer deck building to ensure
    only base game cards are used.

    Args:
        card_ids: List of card IDs

    Returns:
        Filtered list with user cards removed
    """
    return [cid for cid in card_ids if not is_user_card(cid)]


def filter_out_user_leaders(leader_ids: List[str]) -> List[str]:
    """
    Filter out all user-created leaders from a list of leader IDs.

    CRITICAL: Use this for multiplayer to ensure only base game
    leaders are available.

    Args:
        leader_ids: List of leader card_ids

    Returns:
        Filtered list with user leaders removed
    """
    return [lid for lid in leader_ids if not is_user_leader(lid)]


def get_base_game_factions() -> List[str]:
    """
    Get list of base game factions only (no user factions).

    CRITICAL: Use this for multiplayer faction selection.

    Returns:
        List of base game faction names
    """
    try:
        from cards import (
            FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
            FACTION_LUCIAN, FACTION_ASGARD
        )
        return [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA,
                FACTION_LUCIAN, FACTION_ASGARD]
    except ImportError:
        # Fallback to hardcoded values if cards.py can't be imported
        return ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard"]


def validate_deck_for_multiplayer(deck_ids: List[str], leader_id: str, faction: str) -> Tuple[bool, str]:
    """
    Validate that a deck contains NO user content for multiplayer.

    CRITICAL: Call this before sending deck data in LAN/multiplayer.

    Args:
        deck_ids: List of card IDs in the deck
        leader_id: The selected leader's card_id
        faction: The selected faction name

    Returns:
        (is_valid, error_message) tuple
    """
    errors = []

    # Check faction
    if is_user_faction(faction):
        errors.append(f"User faction '{faction}' not allowed in multiplayer")

    # Check leader
    if is_user_leader(leader_id):
        errors.append(f"User leader '{leader_id}' not allowed in multiplayer")

    # Check all cards
    user_cards_in_deck = [cid for cid in deck_ids if is_user_card(cid)]
    if user_cards_in_deck:
        errors.append(f"User cards not allowed in multiplayer: {', '.join(user_cards_in_deck[:5])}")
        if len(user_cards_in_deck) > 5:
            errors.append(f"  ... and {len(user_cards_in_deck) - 5} more")

    if errors:
        return False, "\n".join(errors)

    return True, "Deck valid for multiplayer"


# ============================================================================
# STATS TRACKING FOR USER CONTENT
# ============================================================================

def get_user_content_stats() -> Dict[str, Any]:
    """
    Get statistics about user content usage.

    Returns dict with counts and usage info for the stats menu.
    """
    loader = get_loader()

    return {
        "total_user_cards": len(loader.user_cards),
        "total_user_leaders": len(loader.user_leaders),
        "total_user_factions": len(loader.user_factions),
        "user_card_ids": list(loader.user_cards.keys()),
        "user_leader_ids": [l.get("card_id") for l in loader.user_leaders],
        "user_faction_names": list(loader.user_factions.keys()),
        "validation_errors": len(loader.validation_errors),
    }
