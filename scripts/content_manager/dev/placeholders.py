"""Developer workflow: Placeholder image generation."""

import sys
from pathlib import Path
from typing import List

from ..config import ROOT, FILES
from ..ui import print_header, get_input, get_int, confirm, select_from_list, progress_bar
from ..code_parsing import get_existing_factions
from ..logging_ import log

# Global settings for placeholder generation
_placeholder_skip_existing = False
_placeholder_overwrite_all = False
_placeholder_asked_once = False


def reset_placeholder_settings():
    """Reset placeholder generation settings for a new session."""
    global _placeholder_skip_existing, _placeholder_overwrite_all, _placeholder_asked_once
    _placeholder_skip_existing = False
    _placeholder_overwrite_all = False
    _placeholder_asked_once = False


def should_create_placeholder(file_path: Path) -> bool:
    """Check if we should create/overwrite this placeholder file."""
    global _placeholder_skip_existing, _placeholder_overwrite_all, _placeholder_asked_once

    if not file_path.exists():
        return True

    if _placeholder_overwrite_all:
        return True
    if _placeholder_skip_existing:
        return False

    if not _placeholder_asked_once:
        _placeholder_asked_once = True
        print("\n" + "=" * 60)
        print("EXISTING FILES DETECTED")
        print("=" * 60)
        print("Some asset files already exist in the assets folder.")
        print("What would you like to do?")
        print()
        print("  [O] Overwrite ALL existing files (replace with placeholders)")
        print("  [S] Skip ALL existing files (keep your custom artwork)")
        print("  [A] Ask for each file individually")
        print()

        while True:
            choice = input("Your choice (O/S/A): ").strip().upper()
            if choice == 'O':
                _placeholder_overwrite_all = True
                print("  Will overwrite all existing files\n")
                return True
            elif choice == 'S':
                _placeholder_skip_existing = True
                print("  Will skip all existing files\n")
                return False
            elif choice == 'A':
                print("  Will ask for each file\n")
                break
            else:
                print("Invalid choice. Please enter O, S, or A.")

    filename = file_path.name
    while True:
        choice = input(f"File exists: {filename} - Overwrite? (y/n): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print("Please enter 'y' or 'n'.")


def placeholder_generation_workflow():
    """Generate placeholder images."""
    print_header("PLACEHOLDER GENERATION")

    print("  1. Generate ALL placeholders (run create_placeholders.py)")
    print("  2. Generate for specific card")
    print("  3. Generate for specific leader")
    print("  4. Generate for specific faction")
    print("  0. Back")
    print()

    choice = get_input("Choice", default="0")

    reset_placeholder_settings()

    if choice == "1":
        run_create_placeholders_script()
    elif choice == "2":
        card_id = get_input("Card ID")
        try:
            from cards import ALL_CARDS
            if card_id in ALL_CARDS:
                card = ALL_CARDS[card_id]
                generate_card_placeholder(card_id, card.name, card.faction,
                                          card.power, card.row)
            else:
                print(f"Card {card_id} not found")
        except Exception as e:
            print(f"Error: {e}")
    elif choice == "3":
        card_id = get_input("Leader Card ID")
        name = get_input("Leader Name")
        faction = select_from_list("Faction:", get_existing_factions()[:-1])
        generate_leader_placeholders(card_id, name, faction)
    elif choice == "4":
        faction = select_from_list("Faction:", get_existing_factions())
        generate_all_faction_placeholders(faction)


def run_create_placeholders_script():
    """Run the create_placeholders.py script."""
    import subprocess

    print("\nRunning create_placeholders.py...")
    print("(The original script has its own skip/overwrite options)")
    print()

    result = subprocess.run(
        [sys.executable, str(FILES["create_placeholders"])],
        cwd=str(ROOT)
    )

    if result.returncode == 0:
        print("\n[OK] Placeholders generated successfully")
    else:
        print(f"\n[ERROR] Script exited with code {result.returncode}")


def generate_card_placeholder(card_id: str, name: str, faction: str,
                              power: int, row: str, force: bool = False):
    """Generate a single card placeholder."""
    try:
        import pygame
        pygame.init()

        assets_dir = ROOT / "assets"
        assets_dir.mkdir(exist_ok=True)
        path = assets_dir / f"{card_id}.png"

        if not force and not should_create_placeholder(path):
            print(f"  Skipped: {card_id}.png (already exists)")
            return False

        CARD_WIDTH, CARD_HEIGHT = 200, 280

        faction_colors = {
            "Tau'ri": (50, 100, 180),
            "Goa'uld": (200, 40, 60),
            "Jaffa Rebellion": (215, 170, 60),
            "Lucian Alliance": (220, 80, 170),
            "Asgard": (150, 150, 200),
            "Neutral": (120, 120, 120),
        }

        surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
        color = faction_colors.get(faction, (100, 100, 100))
        surface.fill(color)

        pygame.draw.rect(surface, (255, 255, 255), surface.get_rect(), width=2, border_radius=10)

        font = pygame.font.SysFont("Arial", 28, bold=True)
        title = font.render(name[:20], True, (255, 255, 255))
        title_rect = title.get_rect(center=(CARD_WIDTH / 2, 20))
        surface.blit(title, title_rect)

        if row not in ["special", "weather"]:
            power_font = pygame.font.SysFont("Arial", 40, bold=True)
            power_text = power_font.render(str(power), True, (0, 0, 0))
            pygame.draw.circle(surface, (255, 255, 255), (30, 50), 20)
            power_rect = power_text.get_rect(center=(30, 50))
            surface.blit(power_text, power_rect)

        pygame.image.save(surface, str(path))

        log(f"ASSET CREATED: {path}")
        print(f"[OK] Created {path}")
        return True

    except Exception as e:
        print(f"[ERROR] Could not generate placeholder: {e}")
        return False


def generate_leader_placeholders(card_id: str, name: str, faction: str, force: bool = False):
    """Generate leader portrait and background placeholders."""
    try:
        import pygame
        pygame.init()

        faction_colors = {
            "Tau'ri": (50, 100, 180),
            "Goa'uld": (200, 40, 60),
            "Jaffa Rebellion": (215, 170, 60),
            "Lucian Alliance": (220, 80, 170),
            "Asgard": (150, 150, 200),
        }

        color = faction_colors.get(faction, (100, 100, 100))
        assets_dir = ROOT / "assets"
        assets_dir.mkdir(exist_ok=True)

        # Leader portrait
        portrait_path = assets_dir / f"{card_id}_leader.png"

        if force or should_create_placeholder(portrait_path):
            LEADER_WIDTH, LEADER_HEIGHT = 200, 280
            surface = pygame.Surface((LEADER_WIDTH, LEADER_HEIGHT))

            for y in range(LEADER_HEIGHT):
                brightness = 1.0 - (y / LEADER_HEIGHT) * 0.3
                shade = tuple(int(c * brightness) for c in color)
                pygame.draw.line(surface, shade, (0, y), (LEADER_WIDTH, y))

            pygame.draw.rect(surface, (255, 215, 0), surface.get_rect(), width=4, border_radius=5)

            font = pygame.font.SysFont("Arial", 18, bold=True)
            leader_text = font.render("LEADER", True, (255, 215, 0))
            text_rect = leader_text.get_rect(center=(LEADER_WIDTH // 2, 20))
            surface.blit(leader_text, text_rect)

            name_font = pygame.font.SysFont("Arial", 14, bold=True)
            name_text = name_font.render(name[:20], True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(LEADER_WIDTH // 2, LEADER_HEIGHT - 20))
            pygame.draw.rect(surface, (0, 0, 0), name_rect.inflate(10, 5))
            surface.blit(name_text, name_rect)

            pygame.image.save(surface, str(portrait_path))
            log(f"ASSET CREATED: {portrait_path}")
            print(f"[OK] Created {portrait_path}")
        else:
            print(f"  Skipped: {card_id}_leader.png (already exists)")

        # Leader background
        bg_path = assets_dir / f"leader_bg_{card_id}.png"

        if force or should_create_placeholder(bg_path):
            BOARD_WIDTH, BOARD_HEIGHT = 3840, 2160
            bg_surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

            for y in range(BOARD_HEIGHT):
                progress = y / BOARD_HEIGHT
                bg_color = tuple(int(c * (1 - progress * 0.3)) for c in color)
                pygame.draw.line(bg_surface, bg_color, (0, y), (BOARD_WIDTH, y))

            pygame.image.save(bg_surface, str(bg_path))
            log(f"ASSET CREATED: {bg_path}")
            print(f"[OK] Created {bg_path}")
        else:
            print(f"  Skipped: leader_bg_{card_id}.png (already exists)")

    except Exception as e:
        print(f"[ERROR] Could not generate placeholders: {e}")


def generate_all_faction_placeholders(faction: str):
    """Generate placeholders for all content of a faction."""
    print(f"\nGenerating all placeholders for {faction}...")

    try:
        from cards import ALL_CARDS

        faction_cards = [(cid, c) for cid, c in ALL_CARDS.items() if c.faction == faction]
        total = len(faction_cards)
        for i, (card_id, card) in enumerate(faction_cards, 1):
            generate_card_placeholder(card_id, card.name, card.faction,
                                      card.power, card.row)
            progress_bar(i, total, "Cards")

        print(f"\n[OK] Generated {total} card placeholders for {faction}")

    except Exception as e:
        print(f"[ERROR] {e}")


def generate_faction_placeholders(faction_name: str, faction_constant: str,
                                   cards: List[dict], leaders: List[dict]):
    """Generate all placeholders for a new faction (force=True for new content)."""
    print("\nGenerating card placeholders...")
    total = len(cards)
    for i, card in enumerate(cards, 1):
        generate_card_placeholder(card["card_id"], card["name"], faction_name,
                                  card["power"], card["row"], force=True)
        progress_bar(i, total, "Cards")

    print("\nGenerating leader placeholders...")
    total = len(leaders)
    for i, leader in enumerate(leaders, 1):
        generate_leader_placeholders(leader["card_id"], leader["name"], faction_name, force=True)
        progress_bar(i, total, "Leaders")
