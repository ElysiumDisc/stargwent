"""Developer workflow: Asset checker (find missing/orphaned images)."""

from ..config import ROOT
from ..ui import print_header, progress_bar


def asset_checker_workflow():
    """Check for missing or orphaned assets."""
    print_header("ASSET CHECKER")

    assets_dir = ROOT / "assets"

    if not assets_dir.exists():
        print(f"Assets directory not found: {assets_dir}")
        return

    try:
        from cards import ALL_CARDS
    except ImportError:
        print("Could not import cards.py")
        return

    existing_images = {f.stem for f in assets_dir.glob("*.png")}
    expected_cards = set(ALL_CARDS.keys())
    missing_cards = expected_cards - existing_images

    known_non_cards = {
        "board_background", "menu_background", "card_back", "decoy",
        "deck_building_bg", "stats_menu_bg", "options_menu_bg",
        "draft_mode_bg", "mulligan_bg", "rule_menu_bg",
        "universal_leader_matchup_bg", "lobby_background"
    }

    leader_images = {f.stem for f in assets_dir.glob("*_leader.png")}
    leader_bgs = {f.stem for f in assets_dir.glob("leader_bg_*.png")}
    faction_bgs = {f.stem for f in assets_dir.glob("faction_bg_*.png")}

    non_card_images = known_non_cards | {f.replace("_leader", "") for f in leader_images}
    non_card_images |= {f.replace("leader_bg_", "") for f in leader_bgs}
    non_card_images |= faction_bgs

    orphaned = existing_images - expected_cards - non_card_images - leader_images - leader_bgs - faction_bgs

    print(f"\n=== ASSET CHECK REPORT ===\n")
    print(f"Total cards in code: {len(expected_cards)}")
    print(f"Total images in assets/: {len(existing_images)}")

    if missing_cards:
        print(f"\n[!] MISSING CARD IMAGES ({len(missing_cards)}):")
        for card_id in sorted(missing_cards)[:20]:
            print(f"    - {card_id}.png")
        if len(missing_cards) > 20:
            print(f"    ... and {len(missing_cards) - 20} more")
    else:
        print(f"\n[OK] All card images present")

    if orphaned:
        print(f"\n[?] POSSIBLY ORPHANED IMAGES ({len(orphaned)}):")
        for img in sorted(orphaned)[:10]:
            print(f"    - {img}.png")
        if len(orphaned) > 10:
            print(f"    ... and {len(orphaned) - 10} more")

    print(f"\n=== IMAGE SIZE CHECK ===")
    standard_card_size = (200, 280)
    wrong_size = []

    try:
        import pygame
        pygame.init()

        check_cards = list(expected_cards)[:50]
        for i, card_id in enumerate(check_cards, 1):
            path = assets_dir / f"{card_id}.png"
            if path.exists():
                img = pygame.image.load(str(path))
                if img.get_size() != standard_card_size:
                    wrong_size.append((card_id, img.get_size()))
            progress_bar(i, len(check_cards), "Checking")

        if wrong_size:
            print(f"\n[!] NON-STANDARD SIZE CARDS:")
            for card_id, size in wrong_size[:10]:
                print(f"    - {card_id}: {size} (expected {standard_card_size})")
        else:
            print(f"[OK] All checked cards have standard size")

    except Exception as e:
        print(f"Could not check image sizes: {e}")
