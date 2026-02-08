"""User workflow: Content pack import/export."""

import json
import os
import shutil
import zipfile
from pathlib import Path

from ..config import ROOT, USER_CONTENT_DIR
from ..ui import print_header, get_input, confirm
from ..logging_ import log
from .create_card import get_valid_abilities_list


def user_import_content_pack():
    """Import a content pack from a .zip file."""
    print_header("IMPORT CONTENT PACK")

    zip_path = get_input("Path to .zip file")
    zip_path = Path(zip_path).expanduser()

    if not zip_path.exists():
        print(f"[ERROR] File not found: {zip_path}")
        return

    if not zipfile.is_zipfile(zip_path):
        print(f"[ERROR] Not a valid zip file: {zip_path}")
        return

    packs_dir = USER_CONTENT_DIR / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)

    # Extract and validate
    print("\nValidating pack...")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Check for manifest
            if 'manifest.json' not in zf.namelist():
                print("[ERROR] No manifest.json found in pack")
                return

            # Read manifest
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
            pack_name = manifest.get('name', zip_path.stem)
            pack_version = manifest.get('version', '1.0')
            pack_author = manifest.get('author', 'Unknown')

            # Count content
            card_count = len([n for n in zf.namelist() if '/cards/' in n and n.endswith('card.json')])
            leader_count = len([n for n in zf.namelist() if '/leaders/' in n and n.endswith('leader.json')])

            print(f"[OK] manifest.json found")
            print(f"[OK] {card_count} cards found")
            print(f"[OK] {leader_count} leaders found")

            # Validate abilities
            errors = []
            for name in zf.namelist():
                if name.endswith('card.json'):
                    try:
                        card_data = json.loads(zf.read(name).decode('utf-8'))
                        ability = card_data.get('ability')
                        if ability:
                            valid_abilities = get_valid_abilities_list()
                            for a in ability.split(','):
                                if a.strip() not in valid_abilities:
                                    errors.append(f"Invalid ability '{a.strip()}' in {name}")
                    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                        errors.append(f"Invalid JSON in {name}")

            if errors:
                print(f"\n[WARNING] {len(errors)} validation errors found:")
                for e in errors[:5]:
                    print(f"  - {e}")
                if len(errors) > 5:
                    print(f"  ... and {len(errors) - 5} more")

                if not confirm("Import anyway?", default=False):
                    print("Cancelled.")
                    return

            print(f"\nPack Contents:")
            print(f"  - {pack_name} v{pack_version} by {pack_author}")
            print(f"  - {card_count} cards, {leader_count} leaders")

            if not confirm("\nInstall this pack?"):
                print("Cancelled.")
                return

            # Extract to packs directory
            pack_dir = packs_dir / pack_name.lower().replace(" ", "_")
            if pack_dir.exists():
                if not confirm("Pack already exists. Overwrite?", default=False):
                    print("Cancelled.")
                    return
                shutil.rmtree(pack_dir)

            pack_dir.mkdir(parents=True, exist_ok=True)
            zf.extractall(pack_dir)

            log(f"Imported content pack: {pack_name}")
            print(f"\n[OK] Extracted to {pack_dir}")

            # Enable pack
            try:
                from user_content_loader import get_loader
                loader = get_loader()
                loader.enable_content("pack", pack_name)
                print("[OK] Pack enabled")
            except (ImportError, AttributeError):
                pass

    except Exception as e:
        print(f"[ERROR] Failed to import pack: {e}")


def user_export_content_pack():
    """Export user content as a shareable .zip pack."""
    print_header("EXPORT CONTENT PACK")

    # Get content to export
    try:
        from user_content_loader import get_loader
        loader = get_loader()
        content = loader.list_content()
    except (ImportError, AttributeError):
        content = {"cards": [], "leaders": [], "factions": [], "packs": []}
        # Manual scan
        cards_dir = USER_CONTENT_DIR / "cards"
        if cards_dir.exists():
            for card_dir in cards_dir.iterdir():
                if card_dir.is_dir():
                    content["cards"].append({"id": card_dir.name, "name": card_dir.name})
        leaders_dir = USER_CONTENT_DIR / "leaders"
        if leaders_dir.exists():
            for leader_dir in leaders_dir.iterdir():
                if leader_dir.is_dir():
                    content["leaders"].append({"id": leader_dir.name, "name": leader_dir.name})

    total_items = len(content["cards"]) + len(content["leaders"]) + len(content["factions"])
    if total_items == 0:
        print("No user content to export.")
        return

    print(f"Found {len(content['cards'])} cards, {len(content['leaders'])} leaders, {len(content['factions'])} factions\n")

    # Pack metadata
    pack_name = get_input("Pack Name", default="My Content Pack")
    pack_version = get_input("Version", default="1.0")
    pack_author = get_input("Author", default="Unknown")
    pack_desc = get_input("Description", default="User-created content pack")

    # Output path
    default_output = ROOT / f"{pack_name.lower().replace(' ', '_')}.zip"
    output_path = get_input("Output path", default=str(default_output))
    output_path = Path(output_path).expanduser()

    if output_path.exists():
        if not confirm("File exists. Overwrite?", default=False):
            print("Cancelled.")
            return

    print("\nCreating pack...")

    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            manifest = {
                "name": pack_name,
                "version": pack_version,
                "author": pack_author,
                "description": pack_desc,
                "cards": [c["id"] for c in content["cards"]],
                "leaders": [l["id"] for l in content["leaders"]],
                "factions": [f["id"] for f in content["factions"]]
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Add cards
            cards_dir = USER_CONTENT_DIR / "cards"
            if cards_dir.exists():
                for card_dir in cards_dir.iterdir():
                    if card_dir.is_dir():
                        for f in card_dir.iterdir():
                            arcname = f"cards/{card_dir.name}/{f.name}"
                            zf.write(f, arcname)
                            print(f"  Added: {arcname}")

            # Add leaders
            leaders_dir = USER_CONTENT_DIR / "leaders"
            if leaders_dir.exists():
                for leader_dir in leaders_dir.iterdir():
                    if leader_dir.is_dir():
                        for f in leader_dir.iterdir():
                            arcname = f"leaders/{leader_dir.name}/{f.name}"
                            zf.write(f, arcname)
                            print(f"  Added: {arcname}")

            # Add factions
            factions_dir = USER_CONTENT_DIR / "factions"
            if factions_dir.exists():
                for faction_dir in factions_dir.iterdir():
                    if faction_dir.is_dir():
                        for root_dir, dirs, files in os.walk(faction_dir):
                            for f in files:
                                fpath = Path(root_dir) / f
                                rel = fpath.relative_to(factions_dir)
                                arcname = f"factions/{rel}"
                                zf.write(fpath, arcname)

        log(f"Exported content pack: {pack_name}")
        print(f"\n[OK] Pack exported to: {output_path}")
        print("Share this file with other players!")

    except Exception as e:
        print(f"[ERROR] Failed to export pack: {e}")
