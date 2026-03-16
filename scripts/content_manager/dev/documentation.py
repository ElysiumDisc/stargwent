"""Developer workflow: Documentation regeneration."""

import sys
import json
from collections import defaultdict

from ..config import ROOT, FILES
from ..ui import print_header, confirm
from ..logging_ import log


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

    print("\n=== Rebuilding card_catalog.json ===")
    rebuild_card_catalog()

    print("\n=== Rebuilding leader_catalog.json ===")
    rebuild_leader_catalog()

    print("\n[OK] Documentation regenerated!")


def rebuild_card_catalog():
    """Rebuild card_catalog.json from cards.py."""
    try:
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

        for faction in catalog:
            catalog[faction].sort(key=lambda c: (-c["power"], c["name"]))

        FILES["card_catalog"].write_text(json.dumps(dict(catalog), indent=2))
        print(f"[OK] Rebuilt {FILES['card_catalog']}")

    except Exception as e:
        print(f"[ERROR] Could not rebuild card catalog: {e}")


def rebuild_leader_catalog():
    """Rebuild leader_catalog.json from content_registry.py."""
    try:
        if "content_registry" in sys.modules:
            del sys.modules["content_registry"]

        from content_registry import BASE_FACTION_LEADERS, UNLOCKABLE_LEADERS
        from cards import FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_ALTERAN

        faction_map = {
            FACTION_TAURI: "FACTION_TAURI",
            FACTION_GOAULD: "FACTION_GOAULD",
            FACTION_JAFFA: "FACTION_JAFFA",
            FACTION_LUCIAN: "FACTION_LUCIAN",
            FACTION_ASGARD: "FACTION_ASGARD",
            FACTION_ALTERAN: "FACTION_ALTERAN",
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
