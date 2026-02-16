"""Menu system and entry point for the content manager."""

import traceback

from .ui import clear_screen, get_input, print_header
from .color import cyan, bold, yellow, red
from .logging_ import start_session, save_session_log
from .cli import parse_args


def show_role_selection():
    """Show role selection menu (Developer or User)."""
    clear_screen()
    print()
    print("+" + "=" * 52 + "+")
    print("|" + bold("        STARGWENT CONTENT MANAGER").center(62) + "|")
    print("+" + "=" * 52 + "+")
    print("|                                                    |")
    print("|  Welcome! Please select your role:                 |")
    print("|                                                    |")
    print("|   1. " + bold("Developer") + "                                    |")
    print("|      (Modify game source code, add abilities,      |")
    print("|       create official content)                     |")
    print("|                                                    |")
    print("|   2. " + bold("User / Player") + "                                |")
    print("|      (Create custom content using existing         |")
    print("|       abilities, manage saves and decks)           |")
    print("|                                                    |")
    print("|   0. Exit                                          |")
    print("+" + "=" * 52 + "+")
    print()
    return get_input("Choice", default="0")


def show_developer_menu():
    """Show developer tools menu with sequential numbering 1-12."""
    clear_screen()
    print()
    print("+" + "=" * 52 + "+")
    print("|" + bold("        DEVELOPER TOOLS").center(62) + "|")
    print("+" + "=" * 52 + "+")
    print("|                                                    |")
    print("|  " + yellow("WARNING: These tools modify game source code!") + "     |")
    print("|                                                    |")
    print("|  " + cyan("=== CONTENT CREATION ===") + "                         |")
    print("|   1. Add a new CARD                                |")
    print("|   2. Add a new LEADER                              |")
    print("|   3. Add a new FACTION (comprehensive)             |")
    print("|   4. Add/Edit ABILITY                              |")
    print("|                                                    |")
    print("|  " + cyan("=== ASSET MANAGEMENT ===") + "                         |")
    print("|   5. Generate placeholder images                   |")
    print("|   6. Regenerate all documentation                  |")
    print("|   7. Asset Checker (find missing images)           |")
    print("|   8. Audio Manager                                 |")
    print("|   9. Card Assembler (portrait → finished card)     |")
    print("|                                                    |")
    print("|  " + cyan("=== ANALYSIS & TOOLS ===") + "                         |")
    print("|  10. Balance Analyzer (power stats)                |")
    print("|  11. Batch Import (from JSON)                      |")
    print("|  12. Leader Ability Generator                      |")
    print("|  13. Card Rename/Delete Tool                       |")
    print("|                                                    |")
    print("|   0. Back to role selection                        |")
    print("+" + "=" * 52 + "+")
    print()
    return get_input("Choice", default="0")


def show_user_menu():
    """Show user/player tools menu."""
    clear_screen()
    print()
    print("+" + "=" * 52 + "+")
    print("|" + bold("        USER / PLAYER TOOLS").center(62) + "|")
    print("+" + "=" * 52 + "+")
    print("|                                                    |")
    print("|  " + cyan("=== SAVE & DECK MANAGEMENT ===") + "                   |")
    print("|   1. Save Manager (backup/restore saves)           |")
    print("|   2. Deck Import/Export (share decks)              |")
    print("|                                                    |")
    print("|  " + cyan("=== CUSTOM CONTENT CREATION ===") + "                  |")
    print("|   (Uses ONLY existing game abilities)              |")
    print("|                                                    |")
    print("|   3. Create Custom Card (wizard)                   |")
    print("|   4. Create Custom Leader (wizard)                 |")
    print("|   5. Create Custom Faction (wizard)                |")
    print("|                                                    |")
    print("|  " + cyan("=== CONTENT PACK MANAGEMENT ===") + "                  |")
    print("|   6. Import Content Pack (.zip)                    |")
    print("|   7. Export Content Pack (.zip)                    |")
    print("|   8. Manage User Content (enable/disable)          |")
    print("|   9. Validate User Content                         |")
    print("|                                                    |")
    print("|   0. Back to role selection                        |")
    print("+" + "=" * 52 + "+")
    print()
    return get_input("Choice", default="0")


def _card_assembler_workflow():
    """Interactive wrapper for scripts/card_assembler.py."""
    import subprocess
    import sys
    from .config import ROOT

    assembler = ROOT / "scripts" / "card_assembler.py"
    python = sys.executable

    print_header("CARD ASSEMBLER")
    print()
    print("  Assemble finished card images from raw portrait art.")
    print(f"  Raw art folder: {ROOT / 'raw_art'}/")
    print()

    # Always show status first
    print(bold("Current status:"))
    subprocess.run([python, str(assembler), "--status"], cwd=str(ROOT))
    print()

    print("  1. Assemble ALL cards with raw art")
    print("  2. Assemble a specific faction")
    print("  3. Assemble specific card(s)")
    print("  4. Generate status report (card_status.txt)")
    print("  5. List cards needing art")
    print("  0. Back")
    print()
    choice = get_input("Choice", default="0")

    if choice == "0":
        return
    elif choice == "1":
        cmd = [python, str(assembler)]
        overwrite = get_input("Overwrite existing cards? [y/N]", default="n")
        if overwrite.lower() != "y":
            cmd.append("--no-overwrite")
        subprocess.run(cmd, cwd=str(ROOT))
    elif choice == "2":
        faction = get_input("Faction (tauri/goauld/jaffa/lucian/asgard/neutral)")
        if faction:
            subprocess.run([python, str(assembler), "--faction", faction], cwd=str(ROOT))
    elif choice == "3":
        card_ids = get_input("Card ID(s) (space-separated)")
        if card_ids:
            subprocess.run([python, str(assembler)] + card_ids.split(), cwd=str(ROOT))
    elif choice == "4":
        subprocess.run([python, str(assembler), "--report"], cwd=str(ROOT))
    elif choice == "5":
        subprocess.run([python, str(assembler), "--list-missing"], cwd=str(ROOT))


def handle_developer_choice(choice: str) -> bool:
    """Handle developer menu choice. Returns True to continue, False to go back."""
    if choice == "0":
        return False

    start_session()

    try:
        if choice == "1":
            from .dev.add_card import add_card_workflow
            add_card_workflow()
        elif choice == "2":
            from .dev.add_leader import add_leader_workflow
            add_leader_workflow()
        elif choice == "3":
            from .dev.add_faction import add_faction_workflow
            add_faction_workflow()
        elif choice == "4":
            from .dev.ability_manager import ability_manager_workflow
            ability_manager_workflow()
        elif choice == "5":
            from .dev.placeholders import placeholder_generation_workflow
            placeholder_generation_workflow()
        elif choice == "6":
            from .dev.documentation import regenerate_documentation
            regenerate_documentation()
        elif choice == "7":
            from .dev.asset_checker import asset_checker_workflow
            asset_checker_workflow()
        elif choice == "8":
            from .dev.audio_manager import audio_manager_workflow
            audio_manager_workflow()
        elif choice == "9":
            _card_assembler_workflow()
        elif choice == "10":
            from .dev.balance_analyzer import balance_analyzer_workflow
            balance_analyzer_workflow()
        elif choice == "11":
            from .dev.batch_import import batch_import_workflow
            batch_import_workflow()
        elif choice == "12":
            from .dev.leader_ability_gen import leader_ability_generator_workflow
            leader_ability_generator_workflow()
        elif choice == "13":
            from .dev.card_rename_delete import card_rename_delete_workflow
            card_rename_delete_workflow()
        else:
            print("Invalid choice")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
    except Exception as e:
        print(f"\n{red('[ERROR]')} {e}")
        traceback.print_exc()

    save_session_log()
    input("\nPress Enter to continue...")
    return True


def handle_user_choice(choice: str) -> bool:
    """Handle user menu choice. Returns True to continue, False to go back."""
    if choice == "0":
        return False

    start_session()

    try:
        if choice == "1":
            from .user.save_manager import save_manager_workflow
            save_manager_workflow()
        elif choice == "2":
            from .user.deck_io import deck_import_export_workflow
            deck_import_export_workflow()
        elif choice == "3":
            from .user.create_card import user_create_card_wizard
            user_create_card_wizard()
        elif choice == "4":
            from .user.create_leader import user_create_leader_wizard
            user_create_leader_wizard()
        elif choice == "5":
            from .user.create_faction import user_create_faction_wizard
            user_create_faction_wizard()
        elif choice == "6":
            from .user.content_packs import user_import_content_pack
            user_import_content_pack()
        elif choice == "7":
            from .user.content_packs import user_export_content_pack
            user_export_content_pack()
        elif choice == "8":
            from .user.manage_content import user_manage_content
            user_manage_content()
        elif choice == "9":
            from .user.manage_content import user_validate_content
            user_validate_content()
        else:
            print("Invalid choice")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
    except Exception as e:
        print(f"\n{red('[ERROR]')} {e}")
        traceback.print_exc()

    save_session_log()
    input("\nPress Enter to continue...")
    return True


def main_menu():
    """Display and handle main menu with role-based separation."""
    while True:
        role_choice = show_role_selection()

        if role_choice == "0":
            save_session_log()
            print("\nGoodbye!")
            break
        elif role_choice == "1":
            # Developer mode
            while True:
                dev_choice = show_developer_menu()
                if not handle_developer_choice(dev_choice):
                    break
        elif role_choice == "2":
            # User mode
            while True:
                user_choice = show_user_menu()
                if not handle_user_choice(user_choice):
                    break
        else:
            print("Invalid choice")


def main():
    """Entry point with CLI argument support."""
    args = parse_args()

    # Apply global flags
    if args.non_interactive:
        from . import ui
        ui.NON_INTERACTIVE = True

    if args.dry_run:
        from . import safety
        safety.DRY_RUN = True

    try:
        if args.dev:
            # Jump directly to developer menu
            while True:
                dev_choice = show_developer_menu()
                if not handle_developer_choice(dev_choice):
                    break
            save_session_log()
            print("\nGoodbye!")
        elif args.user:
            # Jump directly to user menu
            while True:
                user_choice = show_user_menu()
                if not handle_user_choice(user_choice):
                    break
            save_session_log()
            print("\nGoodbye!")
        else:
            main_menu()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        save_session_log()
