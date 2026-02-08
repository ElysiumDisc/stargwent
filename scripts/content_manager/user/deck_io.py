"""User workflow: Deck import/export - uses XDG-compliant save_paths."""

import json
from pathlib import Path

from ..config import ROOT
from ..ui import print_header, get_input, confirm, select_from_list
from ..code_parsing import get_existing_factions


def _get_decks_path() -> Path:
    """Get the decks save path using XDG-compliant save_paths."""
    try:
        from save_paths import get_deck_save_path
        return Path(get_deck_save_path())
    except ImportError:
        return ROOT / "player_decks.json"


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
    decks_file = _get_decks_path()

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
    decks_file = _get_decks_path()

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

    try:
        from cards import ALL_CARDS

        invalid = [c for c in cards if c not in ALL_CARDS]
        if invalid:
            print(f"\n[WARNING] Unknown card IDs: {', '.join(invalid[:5])}")
            if not confirm("Import anyway?"):
                return
    except ImportError:
        pass

    faction = select_from_list("Select faction for this deck:", get_existing_factions()[:-1])

    decks_file = _get_decks_path()
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

        decks_file = _get_decks_path()
        if decks_file.exists():
            decks = json.loads(decks_file.read_text())
        else:
            decks = {}

        decks[faction] = {"leader": leader, "cards": cards}

        decks_file.write_text(json.dumps(decks, indent=2))
        print(f"\n[OK] Imported deck for {faction} ({len(cards)} cards)")

    except Exception as e:
        print(f"[ERROR] Could not import deck: {e}")
