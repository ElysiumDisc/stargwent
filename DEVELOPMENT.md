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
       * `stats_menu.py`: Add the new faction to the list of factions for win rate display and ensure faction_colors includes it.
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
| `menu_theme.ogg` | Main menu background music |
| `battle_round1.ogg` | Battle music - Round 1 |
| `battle_round2.ogg` | Battle music - Round 2 (more intense) |
| `battle_round3.ogg` | Battle music - Round 3 (climactic) |
| `faction_tauri.ogg` | Tau'ri faction theme (hover preview) |
| `faction_goauld.ogg` | Goa'uld faction theme (hover preview) |
| `faction_jaffa.ogg` | Jaffa faction theme (hover preview) |
| `faction_lucian.ogg` | Lucian Alliance faction theme (hover preview) |
| `faction_asgard.ogg` | Asgard faction theme (hover preview) |

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


### Development
- Built with **Python 3.8+** and **Pygame CE 2.5.6+**
- Card assembler requires **Pillow** (`pip install Pillow`)
- Inspired by The Witcher 3: Wild Hunt's Gwent
- Animation system designed for extensibility
- Active development
