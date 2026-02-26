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
- **Web (Emscripten):** ModernGL unavailable → `webgl_renderer.py` (raw GL ES via PyOpenGL) → same API as `GPURenderer`

**Dual renderer (desktop + web):**
- `gpu_renderer.py` — ModernGL backend (desktop, GLSL 330)
- `webgl_renderer.py` — PyOpenGL/raw GL ES backend (web, GLSL 300 es)
- `display_manager.initialize_gpu()` tries ModernGL first, falls back to WebGL on Emscripten
- `shaders/__init__.py: glsl_version_header()` returns `#version 300 es\nprecision highp float;\n` on web, `#version 330\n` on desktop
- All 12 shader sources use `glsl_version_header()` instead of hardcoded version strings

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

#### Linux: .deb Package (`build_deb.sh`)

**Prerequisites:** `dpkg-deb`, `python3`, `python3-venv`

Bundles game files + Python venv (`pygame-ce`, `moderngl`, `Pillow`) into a `.deb`. Installs to `/usr/share/stargwent/` with launcher at `/usr/bin/stargwent` and `.desktop` file.

```bash
./build_deb.sh
sudo dpkg -i builds/releases/Stargwent-X.Y.Z-linux-amd64.deb
stargwent                          # run from anywhere
sudo dpkg -r stargwent             # uninstall
```

---

#### Linux: AppImage (`build_appimage.sh`)

**Prerequisites:** `wget`, `python3`, `fuse` or `libfuse2`

Downloads Python 3.13 runtime + `appimagetool`, bundles everything into a self-contained AppImage. No installation needed.

```bash
./build_appimage.sh
./builds/releases/Stargwent-X.Y.Z-linux-x86_64.AppImage
```

---

#### Windows: .exe (`build_exe.sh`)

**Prerequisites:** Python 3.8+, `pip install pyinstaller pygame-ce moderngl Pillow`

Uses PyInstaller `--onedir --windowed` mode. Run in Git Bash/MSYS2 on Windows, or via GitHub Actions CI.

```bash
./build_exe.sh
# Output: builds/releases/Stargwent-X.Y.Z-windows-x64.zip
# Extract and run Stargwent/Stargwent.exe
```

**Manual build (PowerShell):**
```powershell
pip install -r requirements.txt pyinstaller
pyinstaller --onedir --name Stargwent --windowed --icon=stargwent.ico ^
  --add-data "assets;assets" --add-data "shaders;shaders" ^
  --hidden-import moderngl --hidden-import glcontext main.py
```

---

#### macOS: .dmg (`build_dmg.sh`)

**Prerequisites:** Python 3.8+, `pip install pyinstaller pygame-ce moderngl Pillow`, Xcode CLI tools

Uses PyInstaller + `hdiutil` to create a compressed `.dmg`. Run on macOS or via GitHub Actions CI.

```bash
./build_dmg.sh
# Output: builds/releases/Stargwent-X.Y.Z-macos.dmg
```

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

#### GitHub Actions CI/CD

Workflow at `.github/workflows/build.yml` automatically builds all platform targets on version tag push. Can also be triggered manually from the Actions tab.

**Release workflow:**
```bash
# Update version badge in README.md, then:
git add README.md && git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z
```

This triggers 4 parallel jobs (linux .deb+AppImage, windows .exe, macos .dmg), creates a draft GitHub Release with all artifacts attached. Review and publish at `github.com/ElysiumDisc/stargwent/releases`.

**Free tier:** Public repos = unlimited. Private repos = 2,000 min/month (macOS uses 10x multiplier).

**Troubleshooting:**

| Issue | Fix |
|-------|-----|
| "Actions" tab not visible | Settings → Actions → General → enable "Allow all actions" |
| Tag push doesn't trigger | Make sure you pushed the tag: `git push origin vX.Y.Z` |
| "Resource not accessible by integration" | Settings → Actions → General → "Read and write" permissions |

---

### Web Browser (PWA via Pygbag)

The game runs in the browser via [Pygbag](https://github.com/nicegui-community/pygbag) (Pygame→WASM/Emscripten). Single-player parity: card game, space shooter, deck builder, galactic conquest — all playable with touch controls and full GPU shader effects.

**Build & test locally:**
```bash
pip install pygbag
pygbag main.py          # Dev server at localhost:8000
pygbag --build main.py  # Production build → build/web/
```

**Deploy:** Push to `main` → GitHub Actions builds + deploys to GitHub Pages automatically (`.github/workflows/web-deploy.yml`).

**Architecture:**

| Layer | Module | Description |
|-------|--------|-------------|
| Platform detection | `touch_support.py` | `is_web_platform()`, `is_touch_platform()`, `force_touch_mode()` |
| Async loops | All game loop files | `async def` + `await asyncio.sleep(0)` after every `clock.tick()` |
| Touch → Mouse | `touch_gestures.py` | Translates FINGER events → synthetic mouse events (tap, long-press, drag, scroll) |
| Touch → Keys | `space_shooter/touch_controls.py` | Virtual joystick + action buttons for space shooter |
| WebGL renderer | `webgl_renderer.py` | Raw GL ES backend, same API as `GPURenderer` |
| GLSL porting | `shaders/__init__.py` | `glsl_version_header()` — `#version 300 es` on web, `#version 330` on desktop |
| File I/O | `save_paths.py` | IndexedDB-backed via `sync_saves()` after every write |
| Audio unlock | `main.py` | "Tap to Start" splash before game start |
| Conditional imports | `lan_session.py`, `lan_menu.py` | Threading/sockets guarded, multiplayer hidden on web |
| PWA | `build/web/` | manifest.json, sw.js, icons for installable offline app |
| CI/CD | `.github/workflows/web-deploy.yml` | Pygbag build → inject PWA tags → deploy to GitHub Pages |

**Desktop compatibility:** All web code gated behind `is_web_platform()` — zero behavior change on desktop.

**LAN multiplayer on web:** Not supported in v1 (no TCP sockets in WASM). Future: WebSocket relay server or WebRTC.

---

## 🌌 Galactic Conquest Architecture (v9.0.0)

Roguelite card-battle campaign mode. Conquer a galaxy of planets through card battles with deck progression, diplomacy, and meta-progression.

### Package Structure: `galactic_conquest/`

| File | Description |
|------|-------------|
| `__init__.py` | Entry point `run_galactic_conquest()`, new campaign + resume + customize + unlocks routing |
| `conquest_menu.py` | CRT-themed submenu (New/Resume/Customize/Unlocks/Back) + CustomizeRunScreen + unlocks screen |
| `campaign_state.py` | CampaignState dataclass — ~20 fields (faction, leader, deck, naquadah, planets, cooldowns, upgrades, relics, buildings, network tier, diplomacy, crisis, difficulty, etc.) |
| `campaign_persistence.py` | Save/load campaign JSON + conquest_settings.json via XDG paths |
| `campaign_controller.py` | Main orchestrator — turn loop, attacks, AI counterattacks, defense, fortify, buildings, diplomacy, pre-battle preview, turn summary, crisis events, scoring |
| `galaxy_map.py` | Planet dataclass, GalaxyMap — procedural generation, adjacency graph, supply lines, Ring Platform 2-hop |
| `map_renderer.py` | Galaxy map renderer — pulsing hyperspace lanes, planet tooltips, shield/building icons, network tier HUD |
| `faction_setup.py` | Faction + leader selection, reuses deck_builder |
| `card_battle.py` | Card battle wrapper — weather injection, elite params, relic combat modifiers |
| `reward_screen.py` | Post-victory card picks with tier scaling + passive/relic card choice bonuses |
| `neutral_events.py` | 20 text events with choices + leader portrait display |
| `planet_passives.py` | 18 planet passives (naq/turn, card choices, counterattack reduction, upgrade chance, cooldown reduction) |
| `relics.py` | 18 relics (combat/economy/exploration) with homeworld relic mapping |
| `relic_screen.py` | CRT acquisition screen + multi-choice mode |
| `narrative_arcs.py` | 6 story chains (Ancients, System Lords, Jaffa Liberation, Asgard Exodus, Lucian Underworld, Alliance of Four Races) |
| `difficulty.py` | 4 difficulty levels (Easy/Normal/Hard/Insane) scaling AI power, counterattack, naquadah |
| `stargate_network.py` | Network tier system (Outpost→Regional→Sector→Quadrant→Galactic) based on connected territory |
| `conquest_abilities.py` | 35 conquest-unique leader abilities with L1-L4 scaling tied to network tier |
| `diplomacy.py` | Faction relations (Hostile→Neutral→Trading→Allied), trade/alliance/betray mechanics |
| `diplomacy_screen.py` | CRT-styled diplomacy interface |
| `buildings.py` | 5 planet building types (Refinery, Training Ground, Shipyard, Sensor Array, Shield Generator) |
| `crisis_events.py` | 5 galaxy-wide crisis events (Replicator Outbreak, Ori Crusade, Plague, Ascension Wave, Wraith Invasion) |
| `meta_progression.py` | Conquest Points, 5 unlockable perks, scoring system, high scores |

### Key Systems

- **Stargate Network**: Connected planet count determines tier (1-3=Outpost, 4-6=Regional, ..., 15+=Galactic). Bonuses: naq/turn, cooldown reduction, attack range, leader ability level
- **Conquest Abilities**: 35 leader abilities (7 per faction) scale L1-L4 with network tier. Triggered at hook points (on_victory, pre_battle, on_defense, on_turn_end, etc.)
- **Diplomacy**: Faction relations from HOSTILE to ALLIED. Trade (50 naq), Alliance (100 naq + adjacency), Betray (+80 naq, permanent hostility)
- **Difficulty System**: Easy/Normal/Hard/Insane scaling counterattack chance, starting naquadah, AI power bonus, loss penalty
- **Buildings**: 5 types, 1 per planet. Refinery (+10 naq/turn), Training Ground (+1 defense power), Shipyard (+1 attack card), Sensor Array (reveal enemy), Shield Generator (cheaper fortify)
- **Supply Lines**: Planets disconnected from homeworld are "unsupplied" (-50% income, +20% counterattack, no fortification)
- **Crisis Events**: 10% chance/turn after turn 5 — galaxy-wide disruptions with dramatic screen display
- **Meta-Progression**: Earn Conquest Points (CP) per run → unlock persistent perks (extra card, naq boost, veteran recruits, diplomatic immunity, ancient knowledge)
- **Pre-Battle Preview**: ENGAGE/RETREAT screen showing player forces, enemy forces, weather, modifiers
- **18 Relics**: Combat (Staff of Ra, Kull Armor), Economy (Asgard Core, Naquadah Reactor), Exploration (Ring Platform, Alteran Database)
- **18 Planet Passives**: Owned planets grant bonuses (Earth +15 naq/turn, Atlantis +1 card choice, Antarctica -8% counterattack, etc.)
- **6 Narrative Arcs**: Story chains tracking planet conquest sequences → relic/naquadah rewards
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
| `coop_client.py` | ~610 | Client renderer — independent P2 camera, full entity + supergate + beam + mine + ion pulse rendering, disconnect overlay with last-known score |
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
- **Co-op Networking**: 20 Hz state snapshots with expanded entity serialization (incl. supergates + beams + per-player invuln timers + proximity mines + ion pulses), heartbeat/disconnect handling, variant in READY payload, keepalive-aware disconnect detection, game-over retry
- **Audio Cleanup**: `_stop_space_music()` stops both music and all SFX channels (`pygame.mixer.stop()`) — no lingering sounds on exit

#### Chat System Overhaul
- ✅ **Sound Notifications** – Audio feedback for incoming messages:
  - Plays `assets/audio/chat_notification.ogg` on peer messages
  - Respects game sound settings (silent if file missing)
- ✅ **Chat Scrolling** – Full history navigation:
  - PageUp/PageDown, Home/End keys for scrolling
  - Mouse wheel support
  - Keeps 100 messages in memory (was 20)
  - "New messages below" indicator when scrolled up
- ✅ **Quick Chat** – Pre-defined messages via number keys:
  - `1`: "Good game!"
  - `2`: "Nice play!"
  - `3`: "Good luck!"
  - `4`: "One moment..."
  - `5`: "Well played!"
  - Hints displayed below chat input
- ✅ **Unread Message Indicator** – Track messages when chat minimized:
  - Badge shows unread count
  - Clears when chat is opened
  - `draw_unread_badge()` method for custom UI placement
- ✅ **Message Delivery Confirmation** – Know your messages arrived:
  - Unique message IDs with ACK protocol
  - Checkmark (v) appears next to confirmed messages
  - Unconfirmed messages shown dimmed
  - Auto-confirms after 5-second timeout
- ✅ **Thread-Safe Session** – All LAN operations protected:
  - Socket lock for concurrent send/recv/close across threads
  - Duplicate disconnect prevention (reader + keepalive dedup)
  - Parse error tolerance raised to 10 consecutive
  - Game action ACKs with msg_id tracking and stale warnings
- ✅ **Chat Robustness** – Reliable message handling:
  - Typing indicator throttled (1 per 500ms instead of per-keystroke)
  - All queued messages drained per frame (not just one)
  - Proper `queue.Empty` exception handling
### Card Unlocks ✅
- **Trigger**: Win any game
- **Reward**: Choose 1 of 3 random cards
- **Filter**: Only shows cards from your faction + Neutral
- **Total**: 20 unlockable cards (ALL abilities verified v3.9.4!)
- **Persistence**: Saved to `player_unlocks.json`
- **Usage**: Access via Deck Builder to customize decks

### Leader Unlocks 🎖️
- **Trigger**: Win 3 games in a row
- **Reward**: Choose 1 of 3 faction leaders
- **Filter**: Only shows leaders from your current faction
- **Total**: 20 unlockable leaders (4 per faction)
- **Effect**: Replaces current leader (can switch anytime)
- **Persistence**: Saved to `player_unlocks.json` per faction

### Deck Customization 🃏
- **Access**: Main Menu → "DECK BUILDING"
- **Rules**:
  - **MINIMUM 20 cards** to start a game
  - Maximum 40 cards
  - At least 15 unit cards
  - Only your faction + Neutral cards
  - **Naquadah Budget**: 150 Naquadah limit (cost = 4 + power - 1, heroes +3 bonus)
  - **Mercenary Tax**: If your deck contains more Neutral cards than Faction cards, your total score is reduced by 25%.
  - **Ori Corruption**: Decks exceeding 150 Naquadah suffer 50% score reduction in-game!
- **Features**:
  - Add/remove cards from your unlocked collection
  - Select leader from unlocked leaders
  - Save custom decks per faction (auto-saves when done)
  - Reset to default anytime
- **Persistence**: Saved to `player_decks.json`
