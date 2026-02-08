"""Developer workflow: Audio manager."""

import shutil
from pathlib import Path

from ..config import ROOT
from ..ui import print_header, get_input, get_int, confirm, select_from_list
from ..code_parsing import get_existing_factions
from ..logging_ import log


def audio_manager_workflow():
    """Manage faction themes, leader voices, and sound effects."""
    while True:
        print_header("AUDIO MANAGER")

        print("  1. Add New Faction Theme")
        print("  2. Add New Leader Voice")
        print("  3. Add New Sound Effect")
        print("  4. Add Commander Snippet")
        print("  5. Preview/Test Audio Files")
        print("  6. List All Audio Assets")
        print("  7. Find Missing Audio")
        print("  0. Back")
        print()

        choice = get_input("Choice", default="0")

        if choice == "0":
            break
        elif choice == "1":
            add_faction_theme_workflow()
        elif choice == "2":
            add_leader_voice_workflow()
        elif choice == "3":
            add_sound_effect_workflow()
        elif choice == "4":
            add_commander_snippet_workflow()
        elif choice == "5":
            preview_audio_workflow()
        elif choice == "6":
            list_all_audio_assets()
        elif choice == "7":
            find_missing_audio()

        input("\nPress Enter to continue...")


def add_faction_theme_workflow():
    """Copy a new faction theme to assets/audio/."""
    print_header("ADD FACTION THEME")

    audio_dir = ROOT / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    factions = get_existing_factions()
    print("Existing factions:", ", ".join(factions))
    print()

    source_path = get_input("Path to source audio file (.ogg or .mp3)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    faction = select_from_list("Select faction:", factions)
    faction_key = faction.lower().replace("'", "").replace(" ", "_")

    dest_name = f"{faction_key}_theme.ogg"
    dest_path = audio_dir / dest_name

    if dest_path.exists():
        if not confirm(f"Theme already exists at {dest_name}. Overwrite?", default=False):
            return

    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied faction theme to {dest_path}")
        print(f"\n[OK] Faction theme added: {dest_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def add_leader_voice_workflow():
    """Copy a new leader voice to assets/audio/leader_voices/."""
    print_header("ADD LEADER VOICE")

    voice_dir = ROOT / "assets" / "audio" / "leader_voices"
    voice_dir.mkdir(parents=True, exist_ok=True)

    source_path = get_input("Path to source audio file (.ogg)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    try:
        from content_registry import LEADER_NAME_BY_ID
        print("\nAvailable leader IDs:")
        for i, (lid, name) in enumerate(sorted(LEADER_NAME_BY_ID.items())[:20]):
            print(f"  {lid}: {name}")
        if len(LEADER_NAME_BY_ID) > 20:
            print(f"  ... and {len(LEADER_NAME_BY_ID) - 20} more")
    except ImportError:
        pass

    leader_id = get_input("\nLeader card_id (e.g., tauri_oneill)")

    dest_name = f"{leader_id}.ogg"
    dest_path = voice_dir / dest_name

    if dest_path.exists():
        if not confirm(f"Voice already exists at {dest_name}. Overwrite?", default=False):
            return

    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied leader voice to {dest_path}")
        print(f"\n[OK] Leader voice added: leader_voices/{dest_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def add_sound_effect_workflow():
    """Copy a new sound effect to assets/audio/."""
    print_header("ADD SOUND EFFECT")

    audio_dir = ROOT / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    existing_sfx = [f.name for f in audio_dir.glob("*.ogg")
                    if not f.name.endswith("_theme.ogg")
                    and "battle_round" not in f.name]
    print("Existing sound effects:")
    for sfx in sorted(existing_sfx)[:15]:
        print(f"  - {sfx}")
    print()

    source_path = get_input("Path to source audio file (.ogg)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    effect_name = get_input("Effect name (e.g., 'horn', 'ring', 'weather_storm')")
    if not effect_name.endswith(".ogg"):
        effect_name += ".ogg"

    dest_path = audio_dir / effect_name

    if dest_path.exists():
        if not confirm(f"Effect already exists at {effect_name}. Overwrite?", default=False):
            return

    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied sound effect to {dest_path}")
        print(f"\n[OK] Sound effect added: {effect_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def add_commander_snippet_workflow():
    """Copy a new commander snippet to assets/audio/commander_snippets/."""
    print_header("ADD COMMANDER SNIPPET")

    snippet_dir = ROOT / "assets" / "audio" / "commander_snippets"
    snippet_dir.mkdir(parents=True, exist_ok=True)

    source_path = get_input("Path to source audio file (.ogg)")
    source = Path(source_path)

    if not source.exists():
        print(f"[ERROR] File not found: {source}")
        return

    try:
        from cards import ALL_CARDS
        legendary = [cid for cid, c in ALL_CARDS.items()
                     if c.ability and "Legendary Commander" in c.ability]
        print("\nLegendary Commanders:")
        for cid in sorted(legendary)[:20]:
            card = ALL_CARDS[cid]
            print(f"  {cid}: {card.name}")
        if len(legendary) > 20:
            print(f"  ... and {len(legendary) - 20} more")
    except ImportError:
        pass

    card_id = get_input("\nCard ID (e.g., tauri_oneill)")

    dest_name = f"{card_id}.ogg"
    dest_path = snippet_dir / dest_name

    if dest_path.exists():
        if not confirm(f"Snippet already exists at {dest_name}. Overwrite?", default=False):
            return

    try:
        shutil.copy2(source, dest_path)
        log(f"AUDIO: Copied commander snippet to {dest_path}")
        print(f"\n[OK] Commander snippet added: commander_snippets/{dest_name}")
    except Exception as e:
        print(f"[ERROR] Failed to copy file: {e}")


def preview_audio_workflow():
    """Preview/test audio files using pygame.mixer."""
    print_header("PREVIEW AUDIO")

    audio_dir = ROOT / "assets" / "audio"
    if not audio_dir.exists():
        print("No audio directory found")
        return

    all_audio = []
    for ogg in audio_dir.glob("*.ogg"):
        all_audio.append(("root", ogg))
    for ogg in (audio_dir / "leader_voices").glob("*.ogg"):
        all_audio.append(("leader_voices", ogg))
    for ogg in (audio_dir / "commander_snippets").glob("*.ogg"):
        all_audio.append(("commander_snippets", ogg))

    if not all_audio:
        print("No audio files found")
        return

    print(f"Found {len(all_audio)} audio files\n")

    categories = {
        "1. Faction Themes": [f for cat, f in all_audio if f.name.endswith("_theme.ogg")],
        "2. Battle Music": [f for cat, f in all_audio if "battle_round" in f.name],
        "3. Sound Effects": [f for cat, f in all_audio if cat == "root"
                            and not f.name.endswith("_theme.ogg")
                            and "battle_round" not in f.name],
        "4. Leader Voices": [f for cat, f in all_audio if cat == "leader_voices"],
        "5. Commander Snippets": [f for cat, f in all_audio if cat == "commander_snippets"],
    }

    for cat_name, files in categories.items():
        if files:
            print(f"{cat_name}: {len(files)} files")

    print()
    category = select_from_list("Select category:", list(categories.keys()))
    files = categories[category]

    if not files:
        print("No files in this category")
        return

    print(f"\nFiles in {category}:")
    for i, f in enumerate(sorted(files)[:20], 1):
        print(f"  {i}. {f.name}")

    if len(files) > 20:
        print(f"  ... and {len(files) - 20} more")

    choice = get_int("\nSelect file to preview (0 to cancel)", min_val=0, max_val=min(20, len(files)))
    if choice == 0:
        return

    selected_file = sorted(files)[choice - 1]

    try:
        import pygame
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

        print(f"\nPlaying: {selected_file.name}")
        print("(Press Enter to stop)")

        sound = pygame.mixer.Sound(str(selected_file))
        sound.play()

        input()
        sound.stop()
        pygame.mixer.quit()

    except Exception as e:
        print(f"[ERROR] Could not play audio: {e}")
        print("Make sure pygame is installed and audio device is available")


def list_all_audio_assets():
    """List all audio files in assets/audio/."""
    print_header("ALL AUDIO ASSETS")

    audio_dir = ROOT / "assets" / "audio"
    if not audio_dir.exists():
        print("No audio directory found")
        return

    print("=== FACTION THEMES ===")
    themes = list(audio_dir.glob("*_theme.ogg"))
    for t in sorted(themes):
        size_kb = t.stat().st_size // 1024
        print(f"  {t.name} ({size_kb} KB)")
    print(f"  Total: {len(themes)} themes\n")

    print("=== BATTLE MUSIC ===")
    battle = list(audio_dir.glob("battle_round*.ogg"))
    for b in sorted(battle):
        size_kb = b.stat().st_size // 1024
        print(f"  {b.name} ({size_kb} KB)")
    print(f"  Total: {len(battle)} tracks\n")

    print("=== SOUND EFFECTS ===")
    sfx = [f for f in audio_dir.glob("*.ogg")
           if not f.name.endswith("_theme.ogg")
           and "battle_round" not in f.name]
    for s in sorted(sfx):
        size_kb = s.stat().st_size // 1024
        print(f"  {s.name} ({size_kb} KB)")
    print(f"  Total: {len(sfx)} effects\n")

    print("=== LEADER VOICES ===")
    voice_dir = audio_dir / "leader_voices"
    if voice_dir.exists():
        voices = list(voice_dir.glob("*.ogg"))
        for v in sorted(voices):
            size_kb = v.stat().st_size // 1024
            print(f"  {v.name} ({size_kb} KB)")
        print(f"  Total: {len(voices)} voices\n")
    else:
        print("  (directory not found)\n")

    print("=== COMMANDER SNIPPETS ===")
    snippet_dir = audio_dir / "commander_snippets"
    if snippet_dir.exists():
        snippets = list(snippet_dir.glob("*.ogg"))
        for s in sorted(snippets):
            size_kb = s.stat().st_size // 1024
            print(f"  {s.name} ({size_kb} KB)")
        print(f"  Total: {len(snippets)} snippets")
    else:
        print("  (directory not found)")


def find_missing_audio():
    """Cross-reference leaders/commanders with audio files."""
    print_header("FIND MISSING AUDIO")

    audio_dir = ROOT / "assets" / "audio"
    voice_dir = audio_dir / "leader_voices"
    snippet_dir = audio_dir / "commander_snippets"

    existing_voices = set()
    if voice_dir.exists():
        existing_voices = {f.stem for f in voice_dir.glob("*.ogg")}

    existing_snippets = set()
    if snippet_dir.exists():
        existing_snippets = {f.stem for f in snippet_dir.glob("*.ogg")}

    existing_themes = set()
    for f in audio_dir.glob("*_theme.ogg"):
        existing_themes.add(f.stem.replace("_theme", ""))

    missing_voices = []
    missing_snippets = []
    missing_themes = []

    try:
        from content_registry import LEADER_NAME_BY_ID
        for leader_id, name in LEADER_NAME_BY_ID.items():
            if leader_id not in existing_voices:
                if leader_id not in existing_snippets:
                    missing_voices.append((leader_id, name))
    except ImportError:
        print("[WARNING] Could not import content_registry")

    try:
        from cards import ALL_CARDS
        for card_id, card in ALL_CARDS.items():
            if card.ability and "Legendary Commander" in card.ability:
                if card_id not in existing_snippets:
                    missing_snippets.append((card_id, card.name))
    except ImportError:
        print("[WARNING] Could not import cards")

    factions = get_existing_factions()
    for faction in factions:
        if faction == "Neutral":
            continue
        faction_key = faction.lower().replace("'", "").replace(" ", "_")
        if faction_key not in existing_themes:
            missing_themes.append(faction)

    print("=== MISSING LEADER VOICES ===")
    if missing_voices:
        for lid, name in sorted(missing_voices)[:15]:
            print(f"  - {lid}: {name}")
        if len(missing_voices) > 15:
            print(f"  ... and {len(missing_voices) - 15} more")
        print(f"  Total missing: {len(missing_voices)}")
    else:
        print("  All leader voices present!")

    print("\n=== MISSING COMMANDER SNIPPETS ===")
    if missing_snippets:
        for cid, name in sorted(missing_snippets)[:15]:
            print(f"  - {cid}: {name}")
        if len(missing_snippets) > 15:
            print(f"  ... and {len(missing_snippets) - 15} more")
        print(f"  Total missing: {len(missing_snippets)}")
    else:
        print("  All commander snippets present!")

    print("\n=== MISSING FACTION THEMES ===")
    if missing_themes:
        for faction in missing_themes:
            faction_key = faction.lower().replace("'", "").replace(" ", "_")
            print(f"  - {faction_key}_theme.ogg ({faction})")
        print(f"  Total missing: {len(missing_themes)}")
    else:
        print("  All faction themes present!")
