"""Integration verification functions."""

import sys
import json
from typing import List, Tuple

from .config import ROOT, FILES
from .color import green, red


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
        status = green("[OK]") if passed else red("[!!]")
        print(f"  {status} {check_name}: {details}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n  {green('All checks passed!')}")
    else:
        print(f"\n  {red('Some checks failed - manual review may be needed')}")

    return all_passed
