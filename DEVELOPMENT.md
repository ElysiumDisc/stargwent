### To change a card name (and its internal ID) you need to update the reference in four specific locations

  1. Update the Code Definition (cards.py)
  This is the "source of truth". You likely already did this.
   * Action: Change the dictionary key and the Card object parameters.
   * Example:
   1     # Change this:
   2     "old_id": Card("old_id", "Old Name", ...)
   3     # To this:
   4     "new_id": Card("new_id", "New Name", ...)

  2. Rename the Image Asset (assets/)
  The game automatically looks for an image with the exact same name as the card ID.
   * Action: Rename assets/old_id.png to assets/new_id.png.
   * Why: If you don't do this, the card will appear invisible or default to a missing texture.

  3. Update Save Data (player_decks.json & player_unlocks.json)
  This is what caused your crash. The save files still "remember" the old ID.
   * Action: Open these JSON files and do a Find & Replace.
   * Find: "old_id"
   * Replace with: "new_id"

  4. Update Documentation (Optional)
  To keep your project clean.
   * Action: Update docs/card_catalog.json and any Markdown specs (like docs/rules_menu_spec.md).

  Summary:
  If you rename jaffa_scout to jaffa_monk in the code, you must also rename the image file to jaffa_monk.png and replace text in player_decks.json.

  
  
### Adding a New Unlockable Card (Unit/Special)

   1. Define the Card (`cards.py`):
       * Add a new entry to the ALL_CARDS dictionary.
       * Ensure the card_id is unique.
   1     "new_card_id": Card("new_card_id", "Card Name", FACTION_CONSTANT, power, "row", "Ability"),

   2. Add the Asset (`assets/`):
       * Place the card image as assets/new_card_id.png.

   3. Register as Unlockable (`unlocks.py`):
       * Add the card to the UNLOCKABLE_CARDS list.
       * Define its unlock condition logic in CardUnlockSystem.check_unlocks if it's not a standard random unlock.

   4. Update Documentation (`docs/card_catalog.json`):
       * Add the card entry to the relevant faction list so it appears in the Rule Compendium (Tab 9).
       * Note: You may need to run `scripts/generate_rules_spec.py` if you use it, or edit the JSON manually.

  ---

  2. Adding a New Leader

   1. Define the Leader (`content_registry.py`):
       * Add the leader entry to UNLOCKABLE_LEADERS (or BASE_FACTION_LEADERS if it's a starter).
       * Crucial: Ensure card_id matches the filename prefix you intend to use.
   1     {"name": "New Leader", "ability": "...", "ability_desc": "...", "card_id": "faction_leadername"},

   2. Define the Card Object (`cards.py`):
       * Even though it's a leader, it needs a Card object for internal logic.
       * Use card_id from step 1.

   1     "faction_leadername": Card("faction_leadername", "New Leader", FACTION_CONSTANT, 10, "close", "Leader Ability"),

   3. Add the Asset (`assets/`):
       * Filename: assets/faction_leadername_leader.png (Recommended convention).
       * Note: The system now prioritizes `_leader.png` for leader portraits in the Rules Menu.

   4. Register Logic (`leader_matchup.py` / `game.py`):
       * Implement the actual ability logic.
       * In game.py or leader_matchup.py, look for where leader abilities are triggered (e.g., apply_leader_ability) and add a case for your new leader's name or ID.

   5. Update Documentation (`docs/leader_catalog.json`):
       * Add the leader to the relevant section so it appears in the Rule Compendium (Tab 5).

  ---

  3. Adding a New Faction

  This is a major change involving many files.

   1. Define Constants (`cards.py`):
       * Add FACTION_NEW = "New Faction" to the constants.
       * Import and use this constant everywhere.

   2. Add Assets (`assets/`):
       * faction_bg_new.png (Background for stats/rules).
       * card_back_new.png (Optional, if specific backs exist).
       * deck_shield_new.png (For deck builder).

   3. Register Faction (`content_registry.py`):
       * Add a new key to BASE_FACTION_LEADERS and UNLOCKABLE_LEADERS.
       * Add it to LEADER_COLOR_OVERRIDES.

   4. Update Deck Persistence (`deck_persistence.py`):
       * Update _get_default_deck_data() to include the new faction key.
       * Update _get_default_unlock_data() to track wins for the new faction.

   5. Update UI Menus:
       * `deck_builder.py`: Ensure it iterates over the new faction constant.
       * `stats_menu.py`: Add the new faction to the Factions tab builder and ensure faction_bar_colors includes it.
       * `rules_menu.py`: Add it to FACTION_DISPLAY and _pretty_faction_name.

   6. Update Game Logic (`game.py`):
       * If the faction has a passive ability (e.g., "Always goes first"), implement it in Game class methods.

   7. Update Documentation:
       * Add new sections to docs/card_catalog.json and docs/leader_catalog.json.

       create_placeholders.py:

### New Factions
  The script has hardcoded visual settings for factions that won't automatically update. If you add a brand new faction (e.g., "Replicators"), you will need to edit scripts/create_placeholders.py to add:
   * `FACTION_COLORS`: You need to tell it what color the placeholder cards should be (e.g., silver/purple).
   * `FACTION_BACKGROUND_IDS`: You need to tell it what filename to use for the faction selection screen.
   * Imports: You will need to add the new FACTION_NAME constant to the import line at the top of the script.



## 🛠️ Content Manager

A modular CLI tool with separate **Developer** and **User/Player** modes. The tool prevents accidental source code modifications by separating workflows by role.

```bash
python scripts/content_manager.py              # Interactive role selection
python scripts/content_manager.py --dev        # Jump to developer menu
python scripts/content_manager.py --user       # Jump to user/player menu
python scripts/content_manager.py --dry-run    # Preview changes without writing
python scripts/content_manager.py --non-interactive  # Use defaults (CI/scripting)
```

### Developer Tools (modifies game source code)

| # | Option | Description |
|---|--------|-------------|
| 1 | **Add Card** | Interactive wizard to add a new card with automatic file updates |
| 2 | **Add Leader** | Create new leader with registry, colors, and portrait generation |
| 3 | **Add Faction** | Complete faction creation (colors, powers, leaders, starter cards) |
| 4 | **Ability Manager** | Add/edit card abilities, leader abilities, or faction powers |
| 5 | **Placeholders** | Generate missing card images and leader portraits |
| 6 | **Regenerate Docs** | Rebuild card_catalog.json, leader_catalog.json, rules_menu_spec.md |
| 7 | **Asset Checker** | Find missing images, orphaned assets, size validation |
| 8 | **Audio Manager** | Manage sound effects, music, and voice clips |
| 9 | **Balance Analyzer** | Power distribution, ability frequency, faction balance stats |
| 10 | **Batch Import** | Import multiple cards/leaders from a JSON file |
| 11 | **Leader Ability Gen** | Generate code stubs for new leader abilities |
| 12 | **Card Rename/Delete** | Rename, delete, preview, or batch rename cards |

### User/Player Tools (safe - uses only existing abilities)

| # | Option | Description |
|---|--------|-------------|
| 1 | **Save Manager** | Backup/restore player saves with timestamped folders |
| 2 | **Deck Import/Export** | Share decks via JSON or text format |
| 3 | **Create Custom Card** | Wizard to create cards using existing abilities |
| 4 | **Create Custom Leader** | Wizard to create leaders using existing ability types |
| 5 | **Create Custom Faction** | Create a faction with existing passive/power types |
| 6 | **Import Content Pack** | Install a .zip content pack from another player |
| 7 | **Export Content Pack** | Package your user content as a shareable .zip |
| 8 | **Manage User Content** | Enable, disable, or delete any user-created content |
| 9 | **Validate User Content** | Check all user content for errors |

All user content lives in `user_content/` and can always be enabled, disabled, or fully deleted without affecting the base game. Nothing a user creates touches game source code.

### Safety Features

The Content Manager includes robust safety features to prevent breaking the game:

1. **Timestamped Backups** - All files are backed up to `backup/YYYY-MM-DD_HHMMSS/` before modification
2. **Step-by-Step Approval** - You see exact code and confirm each file change
3. **Syntax Validation** - Python files are compiled and import-tested after changes
4. **Automatic Rollback** - Any error triggers immediate restore from backup
5. **Dry-Run Mode** - `--dry-run` shows unified diffs without writing any files
6. **Colored Output** - Headers, errors, warnings, and success messages are color-coded
7. **Session Logging** - All changes logged to `scripts/content_manager.log`

### Example: Adding a Card

```
Choice: 1

=== ADD NEW CARD ===
Card ID: tauri_scientist
Card Name: SGC Scientist
Faction: Tau'ri
Power: 3
Row: ranged
Ability: Deep Cover Agent
Is unlockable? [y/N]: n

=== STEP 1: cards.py ===
Creating backup: backup/2026-01-16_143205/cards.py

The following code will be added:

    "tauri_scientist": Card("tauri_scientist", "SGC Scientist", FACTION_TAURI, 3, "ranged", "Deep Cover Agent"),

Add this entry? [Y/n]: y
[OK] cards.py updated

=== VERIFICATION ===
Testing imports... OK

Done! Card "SGC Scientist" ready to use.
```

### Example: Batch Import from JSON

Create a JSON file with cards and/or leaders:

```json
{
  "cards": [
    {
      "card_id": "tauri_scientist",
      "name": "SGC Scientist",
      "faction": "Tau'ri",
      "power": 3,
      "row": "ranged",
      "ability": null,
      "is_unlockable": false
    },
    {
      "card_id": "goauld_elite",
      "name": "Elite Jaffa Guard",
      "faction": "Goa'uld",
      "power": 7,
      "row": "close",
      "ability": "Survival Instinct",
      "is_unlockable": true,
      "rarity": "rare",
      "description": "A battle-hardened warrior"
    }
  ],
  "leaders": [
    {
      "card_id": "tauri_newleader",
      "name": "New Leader Name",
      "faction": "Tau'ri",
      "ability": "Draw 1 card when passing",
      "ability_desc": "When you pass your turn, draw 1 card from your deck",
      "is_unlockable": true,
      "banner_name": "NewLeader"
    }
  ]
}
```

Then import:

```
Choice: 11

=== BATCH IMPORT FROM JSON ===
  1. Import from JSON file
  2. Export JSON template
  3. View example JSON format
  0. Back

Choice: 1
Path to JSON file: my_cards.json

=== VALIDATING JSON ===
[OK] JSON validation passed

=== IMPORT SUMMARY ===
  Cards to import: 2
  Leaders to import: 1

Proceed with import? [Y/n]: y

=== IMPORTING CARDS ===
  [OK] Added card: SGC Scientist (tauri_scientist)
  [OK] Added card: Elite Jaffa Guard (goauld_elite)

=== IMPORTING LEADERS ===
  [OK] Added leader: New Leader Name (tauri_newleader)

=== IMPORT COMPLETE ===
  Cards:   2 added, 0 failed
  Leaders: 1 added, 0 failed
```

### Restoring From Backup

If something goes wrong, restore from the backup folder:

```bash
# Find your session folder
ls backup/

# Restore all files from that session
cp backup/2026-01-16_143205/* ./
```

---




### Audio Assets

All audio files are located in `assets/audio/`. Missing files are silently skipped (no crashes).

#### Music Files
| File | Purpose |
|------|---------|
| `main_menu_music.ogg` | Main menu background music |
| `deck_building.ogg` | Deck builder background music (loops continuously) |
| `battle_round1.ogg` | Battle music - Round 1 |
| `battle_round2.ogg` | Battle music - Round 2 (more intense) |
| `battle_round3.ogg` | Battle music - Round 3 (climactic) |
| `tauri_theme.ogg` | Tau'ri faction theme (hover preview) |
| `goauld_theme.ogg` | Goa'uld faction theme (hover preview) |
| `jaffa_theme.ogg` | Jaffa faction theme (hover preview) |
| `lucian_theme.ogg` | Lucian Alliance faction theme (hover preview) |
| `asgard_theme.ogg` | Asgard faction theme (hover preview) |

#### Sound Effects
| File | Purpose |
|------|---------|
| `close.ogg` | Close combat unit played |
| `ranged.ogg` | Ranged unit played |
| `siege.ogg` | Siege unit played |
| `ring.ogg` | Ring Transport / Mulligan phase |
| `horn.ogg` | Commander's Horn effect |
| `iris.ogg` | Tau'ri Iris Defense activation |
| `symbiote.ogg` | Goa'uld Symbiote animation |
| `chat_notification.ogg` | LAN chat message received |

#### Menu UI Sounds
| File | Purpose |
|------|---------|
| `menu_select.ogg` | Hover over main menu option / back button click |
| `menu_enter.ogg` | Click/enter a menu option / post-Stargate transition |
| `rule_chevron.ogg` | Chevron tab click in Rule Compendium |

#### Weather Sound Effects (Optional)
| File | Purpose |
|------|---------|
| `weather_ice.ogg` | Ice Planet Hazard |
| `weather_nebula.ogg` | Nebula Interference |
| `weather_asteroid.ogg` | Asteroid Storm |
| `weather_emp.ogg` | Electromagnetic Pulse |

#### Commander Voice Snippets
Located in `assets/audio/commander_snippets/`. Each legendary commander can have a voice clip that plays when deployed.

| Pattern | Example |
|---------|---------|
| `{card_id}.ogg` | `tauri_oneill.ogg`, `goauld_apophis.ogg` |

#### Leader Voice Snippets
Located in `assets/audio/leader_voices/`. Leader quotes for draft mode and selection screens.

| Pattern | Example |
|---------|---------|
| `{leader_id}.ogg` | `tauri_oneill.ogg`, `jaffa_tealc.ogg` |


#### New Audio Asset
- `assets/audio/chat_notification.ogg` – Chat message notification sound (optional, silent if missing)

See [Audio Assets](#audio-assets) section for full list of supported audio files.

### Art Assembler

Automated pipeline for assembling finished card images, leader portraits, leader backgrounds, and faction/lobby backgrounds from raw art. Uses Pillow (PIL).

```bash
python scripts/card_assembler.py                    # Assemble all cards with raw art
python scripts/card_assembler.py tauri_oneill       # Specific cards
python scripts/card_assembler.py --faction tauri    # Entire faction
python scripts/card_assembler.py --no-overwrite     # Skip existing finished assets
python scripts/card_assembler.py --status           # Per-faction progress report
python scripts/card_assembler.py --list-missing     # Cards without raw art
python scripts/card_assembler.py --dry-run          # Preview without writing files
```

**Card assembly pipeline:**
1. Load raw portrait art from `raw_art/{card_id}.png`
2. Stretch portrait to fit border's portrait cutout
3. Alpha-composite faction border on top
4. Scale & paste row icon (close/ranged/siege/agile)
5. Scale & paste ability icons (stacked vertically if multiple)
6. Render power number (size 24, black)
7. Draw rarity-colored name plate overlay (blue=rare, purple=epic, gold=legendary; only for cards with explicit rarity in `unlocks.py`)
8. Render card name (auto-sized 13-7px, black)
9. Render flavor text from `scripts/card_quotes.json` (size 13, black, word-wrapped)
10. Save to `assets/{card_id}.png`

**Leader & background assembly (each has its own separate raw art):**
- `raw_art/{card_id}_leader.png` → `assets/{card_id}_leader.png` (200x280 leader portrait)
- `raw_art/leader_bg_{card_id}.png` → `assets/leader_bg_{card_id}.png` (3840x2160 leader background)
- `raw_art/faction_bg_{faction}.png` → `assets/faction_bg_{faction}.png` (3840x2160)
- `raw_art/lobby_background.png` → `assets/lobby_background.png` (3840x2160)

**Raw art naming — each asset type has its own unique image:**
| Raw art filename | Output asset |
|---|---|
| `raw_art/asgard_loki.png` | `asgard_loki.png` (assembled card with border/icons/text) |
| `raw_art/asgard_loki_leader.png` | `asgard_loki_leader.png` (leader portrait, stretched) |
| `raw_art/leader_bg_asgard_loki.png` | `leader_bg_asgard_loki.png` (leader background, stretched) |
| `raw_art/faction_bg_asgard.png` | `faction_bg_asgard.png` (faction background, stretched) |
| `raw_art/lobby_background.png` | `lobby_background.png` (lobby background, stretched) |

**Asset structure:**
```
assets/card_assembler/
    borders/              # Faction border PNGs (200x280 RGBA, transparent portrait cutout)
    row_icons/            # Row type icons (close, ranged, siege, agile)
    ability_icons/        # Ability icons (12 abilities with icons)
raw_art/                  # Drop raw art PNGs here (each output has its own source):
    {card_id}.png         #   Card art → assembled with border/icons/text
    {card_id}_leader.png  #   Leader portrait → stretched to 200x280
    leader_bg_{card_id}.png  # Leader background → stretched to 3840x2160
    faction_bg_{id}.png   #   Faction background → stretched to 3840x2160
    lobby_background.png  #   Lobby background → stretched to 3840x2160
scripts/card_quotes.json  # Optional flavor text mapping (card_id -> quote string)
```

**Layout constants** (top of `card_assembler.py`) control pixel positions for all overlays. Tweak after visual inspection with your border PNGs.

**Status detection:** `--status` classifies cards as "done" (real art >15KB), "ready" (has raw art), or "needs art" (placeholder only) by comparing file sizes against the placeholder threshold.

### Assets
- Card art assembled via Card Assembler pipeline (Pillow)
- Placeholder art generated via pygame (`scripts/create_placeholders.py`)
- Color-coded by faction
- AI-generated portrait art using [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) and [Disco Elysium](https://civitai.com/models/1433982/disco-elysium) style model


### GPU Post-Processing Architecture

The game uses a **hybrid rendering approach**: all drawing is done via Pygame to an offscreen surface, then the frame is uploaded to a ModernGL shared OpenGL context for GLSL shader post-processing. The final result is rendered directly to the default framebuffer (screen) via a fullscreen quad — no CPU readback needed. The display is created with `pygame.OPENGL | pygame.DOUBLEBUF` and ModernGL shares the context via `moderngl.create_context()`.

**Key files:**
| File | Purpose |
|------|---------|
| `gpu_renderer.py` | `GPURenderer`, `ShaderPass`, `FBOPool` — core bridge |
| `shaders/__init__.py` | Effect registry, `register_all_effects()` |
| `shaders/bloom.py` | 3-pass bloom (extract → blur H/V → composite) |
| `shaders/vignette.py` | Radial edge darkening |
| `shaders/crt_hologram.py` | MALP panel CRT scanlines/noise |
| `shaders/distortion.py` | Screen-space shockwave distortion (8 points) |
| `shaders/event_horizon.py` | Procedural stargate portal surface |
| `shaders/kawoosh.py` | Vortex pixel displacement |
| `shaders/hyperspace.py` | Radial motion blur warp with speed lines, chromatic aberration, tunnel vignette |
| `shaders/shockwave.py` | Expanding ring distortion with flash (round winner, game start) |
| `shaders/asgard_beam.py` | Volumetric light column |
| `shaders/zpm_surge.py` | Procedural electric arcs |
| `shaders/shield_bubble.py` | Localized shield energy bubble (hex grid + refraction + rim glow + faction tint) |

**Rendering flow:**
1. Game draws to offscreen `display_manager.screen` (a `pygame.Surface`)
2. `display_manager.gpu_flip()` calls `gpu_renderer.present(surface)`
3. Frame uploaded to GPU via `pygame.image.tobytes()` → `texture.write()`
4. Shader chain runs: each enabled effect reads input texture, renders to FBO, outputs texture
5. Final result rendered to `ctx.screen` (default framebuffer) via passthrough fullscreen quad
6. `pygame.display.flip()` swaps OpenGL double buffers

**Adding a new shader effect:**
1. Create `shaders/my_effect.py` with a `ShaderPass` subclass or factory function
2. Write GLSL fragment shader (vertex shader is shared fullscreen quad passthrough)
3. Register in `shaders/__init__.py` `register_all_effects()`
4. If animation-driven: add `get_gpu_params()` to the animation class, handle in `frame_renderer._apply_gpu_params()`

**Animation → GPU bridge:**
- Animation classes expose `get_gpu_params() -> dict | None`
- `AnimationManager.collect_gpu_params()` aggregates from all active effects
- `frame_renderer._apply_gpu_params()` converts pixel coordinates to UV space and sets shader uniforms

**Fallback chain:**
- `moderngl` not installed → `MODERNGL_AVAILABLE = False` → pure Pygame
- OpenGL display creation fails → reverts to `pygame.SCALED` → pure Pygame
- `create_context()` fails → reverts to `pygame.SCALED` → pure Pygame
- Shader compilation fails → that effect skipped, others continue
- Runtime GPU error → `self.enabled = False` → auto-reverts to `pygame.SCALED`
- Settings `gpu_enabled: false` → skips initialization

**Settings** (in `game_settings.py`):
- `voice_volume` — voice clips volume (leader/commander voices)
- `gpu_enabled` — master GPU toggle
- `bloom_enabled`, `bloom_intensity` (0.0-1.0), `bloom_threshold` (0.0-1.0)
- `vignette_enabled`
- `shader_quality` — "low" / "medium" / "high"

**Circular import note:** `game_settings.py` ↔ `display_manager.py` have a circular dependency. Always use local `import display_manager` inside functions in `game_settings.py`.

### Development
- Built with **Python 3.8+** and **Pygame CE 2.5.6+**
- GPU post-processing requires **ModernGL** (`pip install moderngl`) — optional, graceful fallback
- Card assembler requires **Pillow** (`pip install Pillow`)
- Inspired by The Witcher 3: Wild Hunt's Gwent
- Animation system designed for extensibility
- Active development

---

### Building Distributable Packages

Five build scripts automate the entire packaging process. Version is read automatically from the README.md badge.

| Script | Target | Platform | Method |
|--------|--------|----------|--------|
| `build_deb.sh` | `.deb` installer | Linux (Debian/Ubuntu) | Bundled Python venv |
| `build_appimage.sh` | `.AppImage` portable | Linux (any distro) | Bundled Python runtime |
| `build_exe.sh` | `.exe` (zipped folder) | Windows | PyInstaller |
| `build_dmg.sh` | `.dmg` disk image | macOS | PyInstaller + hdiutil |
| `build_release.sh` | Orchestrator | Auto-detects platform | Calls the right script |

All output goes to `builds/releases/`. Staging area is `builds/staging/` (auto-cleaned each build).

#### Quick Start

```bash
# Build all targets for your current platform
./build_release.sh

# Build a specific target
./build_release.sh "" deb           # .deb only
./build_release.sh "" appimage      # AppImage only
./build_release.sh "" exe           # Windows .exe only
./build_release.sh "" dmg           # macOS .dmg only
./build_release.sh "" linux         # .deb + AppImage

# Override version (instead of reading from README.md badge)
./build_release.sh 6.9.0

# Run individual scripts directly
./build_deb.sh
./build_appimage.sh
./build_exe.sh
./build_dmg.sh
```

---

#### Linux: .deb Package (Debian/Ubuntu)

**Script:** `build_deb.sh`

**Prerequisites:** `dpkg-deb` (pre-installed on Debian/Ubuntu), `python3`, `python3-venv`

**Step by step — what the script does:**

1. Reads version from README.md badge (or accepts `./build_deb.sh 6.9.0`)
2. Creates staging directory `builds/staging/stargwent_VERSION/`
3. Copies all game files (Python sources, assets, shaders, docs) — skips dev artifacts (`.git`, `venv`, `builds`, `raw_art`, all `build_*.sh`)
4. Creates a bundled Python virtual environment at `/usr/share/stargwent/.venv/`
5. Installs all pip dependencies into the venv: `pygame-ce`, `moderngl`, `Pillow`
6. Creates a launcher script at `/usr/bin/stargwent` that `cd`s to the game dir and runs `main.py` via the bundled venv's Python
7. Writes `DEBIAN/control` with system library dependencies (`python3`, `libgl1`, `libsdl2-*`)
8. Installs icon to `/usr/share/pixmaps/` and `.desktop` file to `/usr/share/applications/`
9. Builds the `.deb` with `dpkg-deb --build --root-owner-group`

**Build and install:**

```bash
./build_deb.sh
sudo dpkg -i builds/releases/Stargwent-6.9.0-linux-amd64.deb
stargwent                          # run from anywhere
sudo dpkg -r stargwent             # uninstall
```

**File layout inside the .deb:**

```
/usr/bin/stargwent                     # launcher script
/usr/share/stargwent/                  # game files
/usr/share/stargwent/.venv/            # bundled Python venv (pygame-ce, moderngl, Pillow)
/usr/share/stargwent/main.py           # entry point
/usr/share/stargwent/assets/           # game assets
/usr/share/stargwent/shaders/          # GLSL shaders
/usr/share/applications/stargwent.desktop
/usr/share/pixmaps/stargwent.png
```

---

#### Linux: AppImage (Universal)

**Script:** `build_appimage.sh`

**Prerequisites:** `wget`, `python3` (for the file copy step), `fuse` or `libfuse2` (to run the AppImage)

**Step by step — what the script does:**

1. Reads version from README.md badge (or accepts `./build_appimage.sh 6.9.0`)
2. Downloads `appimagetool` if not already cached in `builds/`
3. Creates AppDir at `builds/staging/stargwent.AppDir/`
4. Copies all game files — skips dev artifacts (`.git`, `venv`, `builds`, `raw_art`, all `build_*.sh`)
5. Downloads Python 3.13 AppImage from the `python-appimage` project (cached in `builds/`)
6. Extracts the Python runtime and copies it into the AppDir at `opt/python3.13/`
7. Installs all pip dependencies into `usr/lib/python3/site-packages/`: `pygame-ce`, `moderngl`, `Pillow`
8. Creates `AppRun` launcher that sets `PYTHONPATH`, `PYTHONHOME`, `LD_LIBRARY_PATH`, then runs `main.py`
9. Copies icon and creates `.desktop` file in the AppDir root
10. Builds the final `.AppImage` with `appimagetool`

**Build and run:**

```bash
./build_appimage.sh
chmod +x builds/releases/Stargwent-6.9.0-linux-x86_64.AppImage
./builds/releases/Stargwent-6.9.0-linux-x86_64.AppImage
```

No installation needed — the AppImage is fully self-contained with its own Python runtime and all dependencies.

---

#### Windows: .exe (PyInstaller)

**Script:** `build_exe.sh` (run in Git Bash / MSYS2 on Windows, or via GitHub Actions CI)

**Prerequisites:** Python 3.8+, `pip install pyinstaller pygame-ce moderngl Pillow`

**Step by step — what the script does:**

1. Reads version from README.md badge (or accepts `./build_exe.sh 6.9.0`)
2. Generates a `.ico` icon from `assets/tauri_oneill.png` using Pillow (multi-size: 256 down to 16px)
3. Ensures all pip dependencies are installed (`pygame-ce`, `moderngl`, `Pillow`)
4. Runs PyInstaller in `--onedir --windowed` mode with:
   - `--add-data "assets;assets"` (note: `;` separator on Windows)
   - `--add-data "shaders;shaders"`, `"docs;docs"`, `"user_content;user_content"`
   - `--hidden-import moderngl --hidden-import glcontext --hidden-import PIL`
5. Packages the `dist/Stargwent/` folder into a `.zip` file

**Build and run (Git Bash on Windows):**

```bash
./build_exe.sh
# Output: builds/releases/Stargwent-6.9.0-windows-x64.zip
# Extract and run Stargwent/Stargwent.exe
```

**Manual build (PowerShell/CMD):**

```powershell
pip install -r requirements.txt
pip install pyinstaller
python -c "from PIL import Image; Image.open('assets/tauri_oneill.png').save('stargwent.ico', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"
pyinstaller --onedir --name Stargwent --windowed --icon=stargwent.ico ^
  --add-data "assets;assets" --add-data "shaders;shaders" ^
  --add-data "docs;docs" --add-data "user_content;user_content" ^
  --hidden-import moderngl --hidden-import glcontext main.py
dist\Stargwent\Stargwent.exe
```

**CI build:** See `.github/workflows/build.yml` for automated Windows builds via GitHub Actions.

---

#### macOS: .dmg (PyInstaller + hdiutil)

**Script:** `build_dmg.sh` (run on macOS, or via GitHub Actions CI with `macos-latest`)

**Prerequisites:** Python 3.8+, `pip install pyinstaller pygame-ce moderngl Pillow`, Xcode command-line tools

**Step by step — what the script does:**

1. Reads version from README.md badge (or accepts `./build_dmg.sh 6.9.0`)
2. Generates a `.icns` icon from `assets/tauri_oneill.png` using `sips` + `iconutil` (macOS built-in) or Pillow fallback
3. Ensures all pip dependencies are installed (`pygame-ce`, `moderngl`, `Pillow`)
4. Runs PyInstaller in `--onedir --windowed` mode with:
   - `--add-data "assets:assets"` (note: `:` separator on macOS/Linux)
   - `--add-data "shaders:shaders"`, `"docs:docs"`, `"user_content:user_content"`
   - `--hidden-import moderngl --hidden-import glcontext --hidden-import PIL`
5. Verifies the `.app` bundle was created
6. Creates a `.dmg` disk image with `hdiutil create -format UDZO` (compressed)

**Build and install:**

```bash
./build_dmg.sh
# Output: builds/releases/Stargwent-6.9.0-macos.dmg
# Open the .dmg → drag Stargwent to Applications
```

**CI build:** See `.github/workflows/build.yml` for automated macOS builds via GitHub Actions.

---

#### Orchestrator: build_release.sh

**Script:** `build_release.sh`

Auto-detects the current platform and builds the appropriate targets.

```bash
./build_release.sh                     # auto-detect platform, build all
./build_release.sh "" deb              # .deb only (Linux)
./build_release.sh "" appimage         # AppImage only (Linux)
./build_release.sh "" exe              # .exe only (Windows)
./build_release.sh "" dmg              # .dmg only (macOS)
./build_release.sh "" linux            # both .deb and AppImage
./build_release.sh 6.9.0 all          # explicit version, all platform targets
```

Platform detection:
- **Linux** → builds `.deb` + `.AppImage`
- **Windows** (Git Bash/MSYS2) → builds `.exe` zip
- **macOS** → builds `.dmg`

---

#### Build Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: moderngl` at runtime | Add `--hidden-import moderngl --hidden-import glcontext` to PyInstaller |
| Assets not found | Verify `--add-data` paths — use `:` on Linux/macOS, `;` on Windows |
| OpenGL errors in AppImage | Ensure `libGL.so` is available on the host (`sudo apt install mesa-utils`) |
| `.deb` missing SDL2 libs | The `Depends:` field handles this — user needs `libsdl2-*` installed |
| AppImage won't run | Install FUSE: `sudo apt install fuse libfuse2` or extract with `--appimage-extract` |
| PyInstaller `--onefile` slow startup | Scripts use `--onedir` — faster launch, slightly larger folder |
| Windows `--add-data` wrong separator | Must use `;` on Windows, `:` on Linux/macOS |
| macOS "app is damaged" Gatekeeper | Run `xattr -cr Stargwent.app` or sign with `codesign` |
| Save data location | Game saves to `~/.local/share/stargwent/` (XDG) — works from any install path |

---

#### GitHub Actions CI/CD — Step-by-Step Setup

GitHub Actions automatically builds your .deb, AppImage, Windows .exe, and macOS .dmg every time you push a version tag. No need to own a Windows or Mac machine.

**Is it free?**

| Repo type | Free minutes/month | Notes |
|-----------|-------------------|-------|
| **Public** repo | Unlimited | Completely free, no limits |
| **Private** repo | 2,000 minutes/month | Linux = 1x, Windows = 2x, macOS = 10x multiplier |

Your repo is currently **private**. A full build (Linux + Windows + macOS) takes ~10-15 min and costs roughly 25 minutes of quota (because macOS has a 10x multiplier). That gives you ~80 full builds/month for free. If you make the repo public, it's unlimited.

**Step 1: Commit and push the workflow file**

The workflow file is already created at `.github/workflows/build.yml`. Push it to GitHub:

```bash
git add .github/workflows/build.yml
git commit -m "Add GitHub Actions CI/CD for all platform builds"
git push origin main
```

**Step 2: Verify the workflow appears on GitHub**

1. Open your repo in a browser: https://github.com/ElysiumDisc/stargwent
2. Click the **"Actions"** tab at the top (between "Pull requests" and "Projects")
3. You should see **"Build Releases"** listed as a workflow on the left sidebar
4. If you see a yellow banner saying "Workflows aren't being run on this repository" → click **"I understand my workflows, go ahead and enable them"**

**Step 3: Run your first build (manual trigger)**

You don't need to create a tag for your first test — you can trigger it manually:

1. Go to **Actions** tab → click **"Build Releases"** on the left
2. Click the **"Run workflow"** dropdown button (top right, blue)
3. Leave the version field empty (it reads from your README.md badge automatically)
4. Click the green **"Run workflow"** button
5. A new run appears — click on it to watch the progress

You'll see 4 jobs:
- **version** — reads the version number (fast, ~10 seconds)
- **linux** — builds .deb + AppImage (~3-5 min)
- **windows** — builds .exe zip (~3-5 min)
- **macos** — builds .dmg (~5-8 min)

**Step 4: Download the built artifacts**

1. Once all jobs show green checkmarks, click on any completed job
2. Scroll to the bottom — you'll see an **"Artifacts"** section
3. Download each one:
   - `Stargwent-X.Y.Z-linux-deb` — the .deb file
   - `Stargwent-X.Y.Z-linux-appimage` — the AppImage
   - `Stargwent-X.Y.Z-windows-x64` — the .exe zip
   - `Stargwent-X.Y.Z-macos` — the .dmg

**Step 5: Automated releases with version tags (recommended workflow)**

Once you've verified the manual build works, use tags for proper releases:

```bash
# 1. Update version in README.md badge (single source of truth)
#    Edit the badge line: ![Version](https://img.shields.io/badge/version-6.9.0-blue)

# 2. Commit the version bump
git add README.md
git commit -m "Bump version to 6.9.0"

# 3. Create a version tag
git tag v6.9.0

# 4. Push both the commit and the tag
git push origin main
git push origin v6.9.0
```

This automatically:
- Triggers all 4 builds (Linux, Windows, macOS)
- Creates a **draft GitHub Release** at https://github.com/ElysiumDisc/stargwent/releases
- Attaches all 4 artifacts (.deb, .AppImage, .zip, .dmg) to the release
- You review the draft → click **"Publish release"** to make it public

**Step 6: Share your game**

After publishing a release, anyone can download the right build for their platform from:
`https://github.com/ElysiumDisc/stargwent/releases/latest`

**Troubleshooting GitHub Actions:**

| Issue | Fix |
|-------|-----|
| "Actions" tab not visible | Go to repo Settings → Actions → General → enable "Allow all actions" |
| Workflow not triggering on tag push | Make sure you pushed the tag: `git push origin v6.9.0` |
| Build fails on Windows/macOS | Click the failed job → read the red error log → usually a missing dependency |
| "Resource not accessible by integration" | Go to Settings → Actions → General → set "Workflow permissions" to "Read and write" |
| Artifacts expire after 90 days | Published releases are permanent; only workflow artifacts expire |

---

### Roadmap: Future Targets

#### Web Browser (WebGL / WASM)

Play Stargwent in any modern web browser — no install needed.

**Approach: Pygbag (most realistic path)**

[Pygbag](https://github.com/nicegui-community/pygbag) compiles Pygame games to WebAssembly (WASM) via Emscripten. Since Stargwent is already Pygame-based, this is the lowest-friction route to a browser build.

**How it would work:**
1. `pip install pygbag`
2. `pygbag main.py` — builds a WASM bundle and serves it locally
3. Deploy the `build/web/` folder to any static host (GitHub Pages, Netlify, itch.io)

**What works out of the box:**
- Core game loop and rendering (Pygame surface drawing)
- All card art, animations, particle effects
- Menu navigation, deck builder, rules compendium
- Single-player vs AI gameplay

**What needs adaptation:**
| Feature | Issue | Solution |
|---------|-------|----------|
| GPU shaders (ModernGL) | ModernGL uses desktop OpenGL 3.3 — browsers only support WebGL (GLSL ES) | Detect WASM environment → disable GPU effects or port shaders to WebGL-compatible GLSL ES 3.0 |
| LAN multiplayer | Raw TCP sockets don't exist in browsers | Replace with WebSocket transport layer; host a lightweight relay server (or use WebRTC for peer-to-peer) |
| File I/O (saves, decks) | No filesystem access in browser sandbox | Use browser `localStorage` or `IndexedDB` via Pygbag's async storage API |
| Threading | No `threading` module in WASM/Emscripten | Refactor any threaded code to use `asyncio` (Pygbag requires `async` main loop) |
| Audio | Pygame mixer works but browser may require user interaction first | Add a "Click to Start" splash to unlock audio context |

**Alternative: Pyodide + Pygbag combo**

Pyodide runs CPython in the browser via Emscripten/WASM. Combined with Pygbag's Pygame-to-canvas bridge, this gives full Python stdlib support. Heavier download (~15MB WASM runtime) but more compatible.

**Shader porting notes:**

The existing GLSL 3.3 core shaders (bloom, vignette, distortion, etc.) would need to be ported to GLSL ES 3.0 for WebGL 2.0:
- `#version 330 core` → `#version 300 es`
- Add `precision mediump float;` declarations
- Replace `texture()` calls if using legacy `texture2D()`
- FBO handling changes (WebGL framebuffer API differs from ModernGL)

A `shaders/webgl/` directory with ES 3.0 variants + runtime detection (`if PLATFORM == "web": use_webgl_shaders()`) would keep both paths working.

**Web Multiplayer Architecture:**

The current LAN multiplayer uses raw TCP sockets (`socket.AF_INET, SOCK_STREAM`), which browsers cannot access. The web build needs a different transport layer while keeping the same game protocol.

**Option A: WebSocket relay server (recommended)**
```
Browser Player A  ←WebSocket→  Relay Server  ←WebSocket→  Browser Player B
                                    ↕ (also accepts TCP)
                              Desktop Player C (LAN)
```
- A lightweight relay server (Python `websockets` or Node.js `ws`) bridges connections
- Browser clients connect via `wss://` (secure WebSocket)
- Desktop clients can also connect via WebSocket OR keep using raw TCP
- The relay translates between WebSocket frames and the existing JSON+newline protocol
- Cross-play between browser and desktop players works through the relay
- Server can be hosted on any VPS, Heroku, Railway, or Fly.io (~$0-5/month)

**Implementation plan:**
1. Create `network_transport.py` — abstract transport layer with `TCPTransport` and `WebSocketTransport` implementations
2. Refactor `lan_session.py` to use the transport abstraction instead of raw sockets
3. Create `relay_server.py` — standalone WebSocket relay that rooms/matchmakes players
4. Browser build auto-detects WASM environment → uses WebSocket transport
5. Desktop build defaults to TCP (LAN) but can optionally connect to the relay for internet play

**Option B: WebRTC peer-to-peer (advanced)**
- No relay server needed — browsers connect directly via WebRTC data channels
- Requires a signaling server (lightweight, only for initial handshake)
- Lower latency than relay, but more complex NAT traversal
- Libraries: `aiortc` (Python), or JavaScript WebRTC API via Pygbag's JS interop

**Option C: Hybrid (best of both)**
- LAN play: raw TCP sockets (desktop only, existing code)
- Online play: WebSocket relay server (browser + desktop)
- Same-network browser play: WebRTC peer-to-peer (no server needed)
- Transport layer auto-selects based on platform and network conditions

**Matchmaking for web:**
- Relay server provides a simple lobby: create room → share room code → opponent joins
- No account system needed — ephemeral room codes (e.g., `STARGATE-7X2K`)
- Optional: public lobby listing for open matches

**Hosting options:**
- **GitHub Pages** — free, static hosting for the game client, deploy from CI
- **itch.io** — game-focused platform, supports HTML5 games natively, built-in audience
- **Relay server** — Python `websockets` on Fly.io / Railway / any VPS for multiplayer support
- **All-in-one** — single server hosts both the static game files and the WebSocket relay

---

## 🌌 Galactic Conquest Architecture (v8.3.0)

Roguelite card-battle campaign mode. Conquer a galaxy of planets through card battles with deck progression.

### Package Structure: `galactic_conquest/`

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | ~110 | Entry point `run_galactic_conquest()`, new campaign + resume + customize run routing |
| `conquest_menu.py` | ~380 | CRT-themed submenu (New/Resume/Customize Run/Back) + CustomizeRunScreen with per-faction leader picker |
| `campaign_state.py` | ~85 | CampaignState dataclass — faction, leader, deck, naquadah, planets, cooldowns, upgrades, friendly faction, enemy leaders |
| `campaign_persistence.py` | ~100 | Save/load campaign JSON + conquest_settings.json via XDG paths |
| `campaign_controller.py` | ~510 | Main orchestrator — turn loop, attacks, AI counterattacks, faction bonuses, defense bonuses, deck viewer, run info, defense alert sound |
| `galaxy_map.py` | ~440 | Planet dataclass, GalaxyMap — procedural generation, adjacency graph, 9 neutral + 15 faction planets |
| `map_renderer.py` | ~450 | Galaxy map renderer — planet clicks, two-row HUD, keyboard shortcuts (D/I/ESC) |
| `faction_setup.py` | ~70 | Faction + leader selection, reuses deck_builder |
| `card_battle.py` | ~60 | Card battle wrapper — builds Game + AIController, calls `main.main(lan_game_data=...)` |
| `reward_screen.py` | ~290 | Post-victory card picks with planet control tier scaling + faction bonus display |
| `neutral_events.py` | ~370 | 7 text events with choices + leader portrait display |

### Key Systems

- **Customize Run**: Friendly faction, neutral event count (3-9), per-faction enemy leader selection; persisted in `conquest_settings.json`
- **Faction Conquest Bonuses**: Tau'ri=intel card, Goa'uld=upgrade+2, Jaffa=remove weak, Lucian=+50 naquadah, Asgard=upgrade×2
- **Defense Bonuses**: +1 card from attacker + 30% upgrade chance on successful counterattack defense
- **Planet Control Scaling**: 3-5 planets=Standard (3 choices), 6-9=Enhanced (4 choices, +25% naq), 10+=Supreme (5 choices, +50% naq)
- **Card Battle Integration**: Passes pre-built `Game` object to `main.main(lan_game_data={'game': game, 'ai_controller': ai_ctrl})`
- **CRT Menu**: Pre-cached scanline overlay, pulsing amber title, CRT-green UI, faction-colored displays
- **Leader Portrait**: Neutral event screens display player's leader card art alongside event text
- **Post-Battle Refresh**: `_refresh_after_battle()` — `self.screen = display_manager.screen` + rebuild MapScreen + `pygame.event.clear()`

---

## 🚀 Space Shooter Architecture (v8.8.0)

The space shooter easter egg is a Vampire Survivors-style infinite survival mini-game unlocked after 8 Draft Mode wins. It lives in the `space_shooter/` package.

### Package Structure

| File | Lines | Description |
|------|-------|-------------|
| `__init__.py` | ~330 | Public API `run_space_shooter()`, `run_coop_space_shooter()`, game loops, variant propagation, disconnect handling |
| `game.py` | ~3100 | SpaceShooterGame — update, draw, collisions, upgrades, 15+ powerup handlers, supergate boss system, common threat, sun/ally/bomb management, level 20 mastery system, secondary fire sound |
| `ship.py` | ~1500 | Ship class — SHIP_VARIANTS config, player + AI + 9 behavior AIs (swarm, homing, charge, bomber, mini_boss, strafe, ori_boss, wraith_boss, ally) + new secondaries/passives |
| `projectiles.py` | ~800 | Projectile types: Laser, Missile, Beam, EnergyBall, StaffBlast, Railgun, ProximityMine, ChainLightning, AreaBomb, PlasmaLance, DisruptorPulse, OriBossBeam, WraithBossBeam |
| `entities.py` | ~1670 | Asteroid, PowerUp (33 types), Drone, XPOrb, Explosion (themed palettes), Sun (5 phases), Supergate (5-phase kawoosh animation), DamageNumber, GravityWell |
| `effects.py` | ~270 | StarField (infinite tiling), ScreenShake, ParticleTrail |
| `upgrades.py` | ~300 | UPGRADES (27), EVOLUTIONS (5), PRIMARY_MASTERIES (9), ENEMY_TYPES (14 incl. ori_mothership, wraith_supergate), ENEMY_EXPLOSION_PALETTES, RARITY_COLORS |
| `ui.py` | ~500 | HUD, survival timer, mini-radar, level-up cards, game over screen |
| `camera.py` | ~140 | Camera with smooth follow, world_to_screen, culling, spawn ring, `get_spawn_ring_for_coop()` |
| `spawner.py` | ~280 | ContinuousSpawner with 10 tiers, paired/swarm spawning, random alt variant sprites |
| `ship_select.py` | ~200 | Ship selection screen with Up/Down variant picking, variant dots, description |
| `coop_game.py` | ~1100 | CoopSpaceShooterGame — host-authoritative co-op, independent P1 camera, supergate/beam snapshot, revival |
| `coop_client.py` | ~540 | Client renderer — independent P2 camera, full entity + supergate + beam rendering, disconnect overlay |
| `coop_protocol.py` | ~75 | Message types: INPUT, STATE, ACTION, LEVEL_UP, GAME_OVER, HEARTBEAT, DISCONNECT + variant in READY |
| `coop_ui.py` | ~130 | Dual health bars, partner arrow, revival pulse, leash warning |
| `virtual_keys.py` | ~55 | Network input translation for co-op |

### Key Systems

- **Ship Variants**: Data-driven `SHIP_VARIANTS` dict maps each faction to a list of variant configs (weapon_type, fire_rate, secondary_type, passive, image_file, etc.). Ship.__init__ looks up variant by index, replacing hardcoded if/elif chains
- **Supergate Boss Events**: At 3 min survival, a Supergate (40k HP) spawns 800-1200px from player. 5-phase animation (APPEARING → ACTIVATING kawoosh → OPEN → HOLDING → CLOSING) with explosive particle burst, lightning tendrils, shimmering event horizon. Randomly spawns Ori Mothership (20k HP + 10k shields, golden sweeping beam) or Wraith Hive (16k HP + 6k shields, full-size purple life-drain beam + dart spawns). All gates stay open until every boss is killed, then close simultaneously
- **Common Threat**: When a supergate boss is alive, all enemies within 500px retarget it, enemy projectiles damage it, boss beam damages everything. Boss death = massive rewards + stun shockwave
- **Camera**: Smooth lerp follow, world-to-screen conversion, `is_visible()` for draw culling. Co-op: independent cameras per player
- **Spawner**: Time-based difficulty tiers interpolate spawn rate, enemy types, HP/speed multipliers. Paired (death gliders) and swarm (wraith darts) spawning. Random variant sprites for visual variety
- **Enemy Behaviors**: 9 unique AI behaviors dispatched via `_behavior` attribute — swarm_lifesteal, split_on_death, shielded_charge, homing, paired, bomber, mini_boss_spawner, ori_boss, wraith_boss
- **Secondary Fire**: Each faction + variant has a unique E-key ability with its own cooldown (Railgun, Staff Barrage, Ion Pulse, War Cry, Scatter Mines + Transporter Beam, Sensor Sweep, Ribbon Blast, Asgard Beam, Eye of Ra, Jaffa Rally). Works in co-op for P2
- **Passives**: Per-variant passives — heavy_armor (25% dmg reduction), adaptive_shields, analyzer (double XP on marks), sarcophagus_regen, point_defense, symbiote_resilience (invuln burst), anubis_shield (absorb charges)
- **Thrusters**: Faction-specific particle configs (color, shape, emit rate, spread), SHIFT to boost
- **Movement**: Velocity-based with acceleration/friction for smooth feel
- **Evolutions**: When both prerequisite upgrades are maxed, a legendary evolution is offered
- **Audio**: Background music loop, per-faction hit SFX + per-variant boost SFX + per-variant secondary fire SFX + shield hit SFX + cloak activation SFX, Ori beam sound + Wraith beam sound via `pygame.mixer.Sound` channels (`assets/audio/space_shooter/`)
- **Faction Power-Ups**: 33 total (8 generic + 15 epic + 10 legendary) with unique effects per faction, rarity glow rendering (purple/gold)
- **Faction-Tinted Shields**: GPU shader + software renderer use per-faction colors — Tau'ri/Asgard blue, Goa'uld/Jaffa/Lucian orange. Shield bar, hit flare all match faction. Ship looks clean normally; shield visual only appears on hit and fades over ~1 second
- **Level 20 Masteries**: At level 20, `_apply_primary_mastery()` grants a unique weapon evolution (9 types in `PRIMARY_MASTERIES` dict). Effects hook into collision, fire, and projectile update loops
- **Asteroid Field Events**: Periodic dense asteroid waves (first at 60s, every 45-75s after) with 3s "INCOMING!" warning, escalating density (1-3 per burst) and duration (6-12s), directional approach
- **Environmental Hazards**: Sun/wormhole with 5 lifecycle phases, gravity pull (550px range), core damage
- **Ally Ships**: Summoned via upgrades/powerups/Jaffa Rally secondary, follow owner, engage enemies, auto-fire
- **Co-op Revival**: Ghost mode on death, revive by killing any enemy, 3s per-player invulnerability on respawn (blocks projectiles, beams, contact, bombs — uses dedicated `p1_invuln_timer`/`p2_invuln_timer` instead of shared powerup)
- **Co-op Networking**: 20 Hz state snapshots with expanded entity serialization (incl. supergates + beams + per-player invuln timers), heartbeat/disconnect handling, variant in READY payload
- **Audio Cleanup**: `_stop_space_music()` stops both music and all SFX channels (`pygame.mixer.stop()`) — no lingering sounds on exit
