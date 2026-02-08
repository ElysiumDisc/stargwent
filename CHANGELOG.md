### Version 5.7.0 (February 2026)
**Main Game Loop Refactor & Draft Mode Penalty Fix**

Refactored the 4150-line `main.py` monolith into a modular architecture with a centralized state dataclass, extracted event handling and rendering, and fixed a bug where draft mode decks were unfairly penalized.

#### Bug Fix: Draft Mode Penalties
- ✅ **Draft Penalty Exemption** -- Draft mode decks are cross-faction by design but were getting hit by Mercenary Tax (-25%) and Ori Corruption (-50%); now correctly exempted via `exempt_penalties` parameter
- ✅ **Player.__init__ `exempt_penalties`** -- New parameter to skip Mercenary Tax and Ori Corruption checks for designated players
- ✅ **Game.__init__ `player1_exempt_penalties`** -- Passed through to Player 1 creation, set `True` for draft mode in `game_setup.py`

#### Main Loop Architecture Refactor
- ✅ **GameLoopState Dataclass** -- New `game_loop_state.py` replaces ~100 local variables in `main()` with a single organized `GameLoopState` dataclass
- ✅ **Event Handler Extraction** -- New `event_handler.py` with `handle_events()` function (~1210 lines of keyboard, mouse, and UI event processing)
- ✅ **Rendering Extraction** -- New `frame_renderer.py` with `render_frame()` function (~1158 lines of board, card, overlay, and debug rendering)
- ✅ **Dead Code Removal** -- Removed duplicate `_draw_card_details` and `_draw_drag_trail` functions (already in `render_engine.py`) and dead `main()` stub
- ✅ **LAN Entry Point Fix** -- `run_game_with_context()` now properly delegates to `main()` instead of being a broken `pass` stub

#### Size Reduction
- `main.py`: 4150 → 1580 lines (62% reduction)
- New modules: `game_loop_state.py` (132), `event_handler.py` (1268), `frame_renderer.py` (1219)

---

### Version 5.6.0 (February 2026)
**Content Manager Modular Refactor & User Content System**

Refactored the 6000-line `content_manager.py` monolith into a clean modular package with role-based menus, CLI flags, colored output, dry-run mode, and a full user content creation system.

#### Content Manager Package Refactor
- ✅ **Modular Package** -- Split monolithic `scripts/content_manager.py` (6000 lines) into `scripts/content_manager/` package with 36 focused modules
- ✅ **Foundation Modules** (12) -- config, color, logging, backup, safety, cli, ui, validation, formatting, code_insertion, code_parsing, verification
- ✅ **Developer Modules** (12) -- add_card, add_leader, add_faction, ability_manager, placeholders, documentation, asset_checker, audio_manager, balance_analyzer, batch_import, leader_ability_gen, card_rename_delete
- ✅ **User Modules** (7) -- save_manager, deck_io, create_card, create_leader, create_faction, content_packs, manage_content
- ✅ **Sequential Dev Menu** -- Developer menu renumbered 1-12 (was 1-8, 11-14 with gaps)
- ✅ **Thin Shim Launcher** -- `scripts/content_manager.py` is now a 3-line launcher that imports from the package

#### CLI Flags
- ✅ **`--dev`** -- Jump directly to developer menu (skip role selection)
- ✅ **`--user`** -- Jump directly to user/player menu
- ✅ **`--dry-run`** -- Preview all file changes as unified diffs without writing
- ✅ **`--non-interactive`** -- Use defaults for all prompts (for scripting/CI)
- ✅ **`python -m` support** -- Run as `python -m scripts.content_manager`

#### Terminal Enhancements
- ✅ **Colored Output** -- Headers in cyan, [OK] in green, [ERROR] in red, [WARNING] in yellow (auto-detects tty)
- ✅ **Progress Bars** -- Batch import, placeholder generation, asset checking, and batch rename show progress
- ✅ **Dry-Run Diffs** -- `safe_modify_file` and `safe_modify_json` show colored unified diffs in dry-run mode

#### User Content System
- ✅ **Create Custom Cards** -- Wizard using only existing game abilities (stored in `user_content/cards/`)
- ✅ **Create Custom Leaders** -- 16 ability types from existing leaders (DRAW_ON_PASS, ROW_POWER_BOOST, etc.)
- ✅ **Create Custom Factions** -- Visual identity, passive, and power selection from existing mechanics
- ✅ **Content Packs** -- Import/export user content as .zip files with manifest.json validation
- ✅ **Manage User Content** -- Enable, disable, or delete any user-created content at any time
- ✅ **Validate User Content** -- Check all user content for errors with colored severity levels
- ✅ **Full Removability** -- All user content can always be toggled off or completely deleted without affecting the base game

#### Bug Fixes
- ✅ **XDG Save Paths** -- Save manager and deck I/O now use `save_paths.py` for XDG-compliant paths (was hardcoded to ROOT)
- ✅ **Stale Comment** -- Removed incorrect "Options 15-21" reference from user content section
- ✅ **Deduplication** -- `find_insertion_point_for_card()` merged into `find_faction_section_end()` in code_insertion.py
- ✅ **USER_CONTENT_DIR** -- Defined once in `config.py` instead of scattered across modules

---

### Version 5.5.0 (February 2026)
**AI Improvements, Bug Fixes, Expanded Lore & Deck Builder Enhancements**

#### AI Deck System
- ✅ **Curated AI Decks** – AI opponents now use pre-built, faction-appropriate decks from `docs/default_faction_decks.json`
- ✅ **Balanced Strategy** – Each faction deck (26 cards) follows optimal playstyle with proper Naquadah budget
- ✅ **AI Penalty Exemption** – AI players skip Mercenary Tax and Ori Corruption checks (they use curated decks)

#### Deck Builder Enhancements
- ✅ **Reset to Default Button** – New button in deck builder to reset your deck to the curated default deck for that faction
- ✅ **Available in Both Modes** – Reset button appears in standalone deck builder and when starting a new game

#### Bug Fixes
- ✅ **Quantum Mirror Fix** – Fixed bug where shuffling hand into deck drew one fewer card than expected (hand size was captured after card removal)

#### Animation Improvements
- ✅ **Quantum Mirror Card Shuffle** – New animation shows cards flying from hand to mirror and back, with staggered timing, arc motion, and sparkle effects

#### Rule Compendium Improvements
- ✅ **Better Margins** – Increased viewport margins (0.32 → 0.38) for cleaner text presentation inside the Stargate portal
- ✅ **Smoother Scrolling** – Reduced scroll step (35 → 25) for more precise navigation
- ✅ **Improved Spacing** – Increased paragraph spacing (20 → 28) and section spacing (30 → 36) for better readability

#### Expanded Lore Content
- ✅ **Faction Lore** – Detailed backstories for all 5 factions covering origins, motivations, and playstyle identity
- ✅ **Key Synergies** – Strategic tips highlighting powerful card combinations for each faction
- ✅ **Iconic Quotes** – Memorable quotes from the Stargate series for each faction
- ✅ **Leader Biographies** – Full bios for all 35 leaders (7 per faction) including backstory, notable achievements, and ability explanations

---

### Version 5.4.0 (February 2026)
**Major Content Update: Alliance Combos, Space Shooter, Naquadah System & Draft Enhancements**

#### New Alliance Combos
- ✅ **Asgard High Council** – 3+ Asgard heroes on board grants +2 power to all Asgard units
- ✅ **Jaffa Uprising** – 5+ Jaffa units on board grants +1 power to ALL units (both players benefit from the uprising!)
- ✅ **Lucian Network** – Play 2+ spies in a single round to draw 1 card (spy tracking resets each round)

#### Space Shooter Power-ups
- ✅ **Shield Boost** (15% spawn) – Instant +50 shields
- ✅ **Rapid Fire** (10% spawn) – 2x fire rate for 10 seconds
- ✅ **Drone Swarm** (8% spawn) – Auto-targeting drones for 8 seconds
- ✅ **Naquadah Core** (12% spawn) – +25% damage for 12 seconds
- ✅ **Cloak** (5% spawn) – Invisibility (enemies can't target) for 5 seconds
- ✅ **Power-up UI** – Active power-up indicator with duration timer

#### Space Shooter High Score System
- ✅ **Scoring** – Enemy: 100pts, Boss: 1000pts, Wave clear: 500pts, No damage bonus: 200pts, Asteroid: 50pts
- ✅ **Leaderboard** – Top 10 scores per faction, saved to player_unlocks.json
- ✅ **Stats Tracking** – Enemies defeated, waves cleared, win/loss tracking

#### Naquadah Budget System
- ✅ **Deck Budget** – 150 Naquadah limit for deck building
- ✅ **Cost Formula** – Base 4 + (power - 1), heroes get +3 bonus
- ✅ **Visual Display** – Crystalline mineral bar in deck builder stats panel
- ✅ **Soft Warning** – "Unstable - Over by X!" message for over-budget decks
- ✅ **Ori Corruption Penalty** – Over-budget decks suffer 50% score reduction in-game

#### Draft Mode Enhancements
- ✅ **Rare Events** (5% chance per pick):
  - "Stargate Anomaly" – Pick from 5 cards instead of 3
  - "Ancient Cache" – One guaranteed Epic/Legendary card
- ✅ **Scaled Rewards** based on wins:
  - 3 wins: 1 random card unlock
  - 5 wins: Choice of 2 cards
  - 8 wins: Legendary card + leader unlock chance
- ✅ **Synergy Tier Display** – Visual indicators for card synergy quality

#### New Animations
- ✅ **Dakara Pulse** – Golden expanding shockwave rings for Dakara Superweapon
- ✅ **Atlantis Shield** – Blue hexagonal dome effect for City of Atlantis card
- ✅ **Hyperspace Jump** – Starfield stretch effect for round transitions
- ✅ **Wraith Culling Beam** – Blue beam from top of screen (future Wraith cards)
- ✅ **Ori Prior Flame** – Holy fire eruption effect (future Ori cards)

#### Balance Changes
- ✅ **Naquadah** prevents power-stacking in deckbuilding (budget constraint)
- ✅ **Mercenary Tax** still applies in-game (-25% for neutral-heavy decks)
- ✅ **Ori Corruption** adds severe penalty (-50%) for ignoring Naquadah budget

### Version 5.3.0 (January 2026)
**Movie-Accurate Stargate Animation & Rule Compendium Polish**

#### New Stargate Opening Animation
- ✅ **Cinematic Stargate Sequence** – Complete visual overhaul of the Stargate opening animation with movie-accurate effects:
  - **Rotating Inner Ring** – The inner symbol ring rotates and stops at randomized glyphs, alternating clockwise/counter-clockwise for each chevron
  - **9-Chevron Locking Sequence** – Each chevron lights up, engages with a visual "clunk" bump, and locks in sequence
  - **Enhanced Kawoosh Effect** – Directional particle cone with 300 layered particles that burst outward, extend, retract, then stabilize
  - **Event Horizon Particles** – 100 swirling particles create the iconic blue ripple effect inside the gate
  - **16-Second Duration** – Timed to match the audio cue for full immersion
  - **State Machine Control** – Kawoosh progresses through dormant → burst → extend → retract → stable phases

#### Rule Compendium Improvements
- ✅ **Scaling Fix** – Rule Compendium UI now scales properly across all resolutions (4K, 1440p, 1080p)
- ✅ **Enhanced Layout** – Improved text rendering and section organization in the rules menu

### Version 5.2.0 (January 2026)
**LAN Multiplayer Reliability & Chat Overhaul**

#### Connection Reliability
- ✅ **JSON Error Recovery** – No longer disconnects on first malformed packet:
  - 3-strike system before disconnect (tolerates network corruption)
  - Logs corrupted data preview for debugging
  - Resets error counter on successful parse
- ✅ **Host Timeout & Cancel** – Hosting no longer blocks forever:
  - 120-second timeout with elapsed time display ("Waiting... 45s / 120s")
  - ESC key cancels hosting gracefully
  - Proper socket cleanup on cancel
- ✅ **Improved Disconnect UX** – Better feedback when connection lost:
  - Styled overlay box with specific reason ("Opponent disconnected" vs "Connection lost")
  - 10-second countdown before auto-return to menu
  - "Return Now" button for immediate exit

#### Connection Quality
- ✅ **Ping/Latency Display** – Real-time connection quality indicator in HUD:
  - PING/PONG protocol measures round-trip time every 5 seconds
  - Colored dot indicator: Green (<50ms), Yellow (50-150ms), Red (>150ms)
  - Shows exact latency in milliseconds
- ✅ **Room Codes** – Human-readable codes for easier LAN connections:
  - Host displays room code (e.g., "GATE-7K3M") prominently
  - Join screen accepts room codes OR IP addresses
  - Excludes confusing characters (0/O, 1/I/L)
  - Auto-detects network prefix for decoding

#### Chat System Overhaul
- ✅ **Sound Notifications** – Audio feedback for incoming messages
- ✅ **Chat Scrolling** – Full history navigation with PageUp/PageDown, Home/End, mouse wheel
- ✅ **Quick Chat** – Pre-defined messages via number keys (1-5)
- ✅ **Unread Message Indicator** – Badge shows unread count when chat minimized
- ✅ **Message Delivery Confirmation** – Checkmark appears next to confirmed messages

### Version 5.1.0 (February 2026)
**Code Quality, XDG Save Paths & Bug Fix Update**

Major code quality improvements addressing 25+ issues across game logic, deck building, and AI systems. Plus proper XDG save paths for Linux compatibility.

#### XDG Base Directory Support
- ✅ **Centralized Save Paths** – New `save_paths.py` module implements XDG Base Directory Specification:
  - Save data now stored in `~/.local/share/stargwent/` (or `$XDG_DATA_HOME/stargwent/`)
  - Works correctly with both .deb and AppImage builds
  - Automatic migration of legacy saves from game directory to XDG location
  - Affected files: `player_decks.json`, `player_unlocks.json`, `game_settings.json`
- ✅ **Updated Modules** – `deck_persistence.py`, `unlocks.py`, `game_settings.py`, `main_menu.py` now use centralized paths

#### Draft Mode Fixes
- ✅ **Duplicate Card Prevention** – Fixed weighted draft pool that could show the same card multiple times in choices
- ✅ **Better Card ID Matching** – Save/restore now matches cards by name, faction, power, AND row to avoid variant mismatches
- ✅ **Exception Handling** – Replaced broad `except Exception:` with specific types in draft UI

#### Critical Bug Fixes
- ✅ **Clone Token Lifetime Fix** – O'Neill clones now correctly live for 4 turns instead of 3 (off-by-one error in `decrement_clone_tokens`)
- ✅ **Horn + ZPM Stacking Fix** – Siege cards no longer get 4x multiplier when both Horn and ZPM are active; each effect applies independently (2x max from either)
- ✅ **Card ID Validation** – Deck builder now validates card IDs before accessing `ALL_CARDS`, preventing crashes during drag-drop and keyboard navigation
- ✅ **Weather State Fix** – Wormhole Stabilization now correctly clears weather types to `None` instead of contradictory state

#### High Severity Fixes
- ✅ **AI Tactical Formation Fix** – Fixed double-counting of Tactical Formation synergy in AI steal evaluation (was inflating card values)
- ✅ **Card Migration Validation** – Deck persistence now validates migration target IDs exist before migrating old card IDs
- ✅ **Neutral Penalty Rounding** – Changed from truncation (`int()`) to proper rounding (`round()`) for fair score calculation

#### Code Quality Improvements
- ✅ **Bare Except Removal** – Replaced 15 bare `except:` clauses with specific exception types across `content_manager.py`, `unlocks.py`, and `deck_builder.py`:
  - `ImportError` for module imports
  - `json.JSONDecodeError` for JSON parsing
  - `OSError` for file operations
  - `pygame.error` for rendering issues
- ✅ **Debug Print Cleanup** – Removed 8 debug print statements from production code in `game.py` and `power.py`
- ✅ **Dead Code Removal** – Removed unused `elif False:` block and orphaned methods (`select_card`, `can_execute_swap`, `execute_swap`) from Asgard faction power
- ✅ **Indentation Fix** – Fixed 5-space indentation to 4-space in `trigger_muster` history event
- ✅ **Null Safety** – Changed `deck_preview_ids` initialization from `None` to `[]` to avoid null checks throughout deck builder

#### Files Modified
- `game.py` – 8 fixes (clone tokens, horn/ZPM stacking, weather state, debug prints, dead code, indentation, neutral penalty)
- `deck_builder.py` – 5 fixes (card ID validation, null initialization, bare excepts)
- `scripts/content_manager.py` – 15 bare except clauses replaced
- `ai_opponent.py` – 1 fix (tactical formation double-count)
- `power.py` – 4 fixes (debug prints, dead code)
- `unlocks.py` – 2 bare except clauses replaced
- `deck_persistence.py` – 1 fix (migration validation)

### Version 5.0.0 (January 2026)
**Content Manager Reliability & Batch Import**

- ✅ **JSON Batch Import (Option 11)** – Import multiple cards and leaders from a single JSON file:
  - Define cards with: `card_id`, `name`, `faction`, `power`, `row`, `ability`, `is_unlockable`, `rarity`, `description`
  - Define leaders with: `card_id`, `name`, `faction`, `ability`, `ability_desc`, `is_unlockable`, `banner_name`, `color_override`
  - Full JSON validation with detailed error messages before import
  - Export JSON template with example entries to get started
  - Optional placeholder image generation for all imported content
- ✅ **Robust Code Insertion** – AST-aware parsing replaces fragile regex:
  - `format_card_entry()` - generates cards.py format (4-space indent, single line)
  - `format_unlockable_entry()` - generates unlocks.py format (multiline with proper indentation)
  - `format_leader_entry()` - generates content_registry.py leader format
  - `find_faction_section_end()` - finds correct insertion point by faction section
  - Preserves exact formatting patterns from existing files
- ✅ **Enhanced Validation** – Catch errors before they break the game:
  - `validate_card_name_unique()` - warns if card name already exists
  - `validate_leader_id_prefix()` - ensures leader IDs match faction convention (e.g., `tauri_` for Tau'ri)
  - `validate_ability_string()` - checks abilities against the Ability enum
  - `validate_faction_complete()` - verifies all required faction components
- ✅ **Integration Verification** – Automatic checks after adding content:
  - `verify_card_integration()` - checks cards.py, card_catalog.json, unlocks.py, assets
  - `verify_leader_integration()` - checks content_registry.py, leader_catalog.json, portraits
  - `verify_faction_integration()` - comprehensive check across all faction-related files
  - Clear [OK]/[!!] status output for each verification check
- ✅ **Faction Workflow Fixes** – Complete integration for new factions:
  - Now adds `FACTION_NAME_ALIASES` entries in create_placeholders.py
  - Generates common aliases (full name, short name, clean name)
  - Verification step at end of faction creation

### Version 4.9.0 (January 2026)
**Content Manager Developer Tool**

- ✅ **Content Manager Script** – New comprehensive developer tool (`scripts/content_manager.py`) for adding game content:
  - **Add Cards**: Interactive wizard to add new cards with automatic updates to `cards.py`, `unlocks.py`, docs, and placeholder image generation
  - **Add Leaders**: Full leader creation with registry updates, color overrides, banner names, and portrait generation
  - **Add Factions**: Complete faction wizard collecting all required data (colors, powers, leaders, cards) and updating 6+ files
  - **Ability Manager**: Add/edit card abilities, leader abilities, and faction powers with proper enum updates
  - **Placeholder Generation**: Generate missing card images and leader portraits with skip/overwrite options
  - **Documentation Regeneration**: Rebuild card_catalog.json, leader_catalog.json, and rules_menu_spec.md
  - **Asset Checker**: Scan for missing card images, leader portraits, and orphaned assets
  - **Balance Analyzer**: Analyze power distribution, ability frequency, and faction balance
  - **Save Manager**: Backup/restore player saves (unlocks, decks, stats) with timestamped folders
  - **Deck Import/Export**: Share decks via JSON or text format with validation
- ✅ **Safety Features** – Robust protection against breaking the game:
  - Timestamped backup folders created before any modification
  - Step-by-step approval prompts showing exact code to be added
  - Python syntax validation and import testing after changes
  - Automatic rollback on any error
  - Session logging to `scripts/content_manager.log`
- ✅ **Integration** – Works with existing scripts:
  - Calls `create_placeholders.py` for image generation
  - Calls `generate_rules_spec.py` for documentation
  - Validates against `abilities.py` enum values

### Version 4.8.3 (January 2026)
**New Card: Quantum Mirror**

- ✅ **Quantum Mirror** – New Neutral special card that counters hand reveal abilities:
  - Shuffles your entire hand into your deck, then draws the same number of cards
  - Clears any active hand reveal effect (Lord Yu, Communication Device, Sodan Warrior)
  - Hand reveal is cleared BEFORE drawing, so new cards remain hidden from opponent
  - Strategic uses: counter intel gathering, mid-game mulligan for bad hands, deck cycling
- ✅ **Quantum Mirror Animation** – Authentic rectangular mirror portal inspired by the show:
  - Dark metallic Naquadah frame with silvery-blue reflective surface
  - Shimmering gradient bands and horizontal/vertical light waves
  - Elliptical reality distortion ripples emanating from center
  - Central singularity glow (the quantum core) with bright flash on activation
- ✅ **Documentation** – Added Quantum Mirror to rules specification with effect, timing, and synergy info

### Version 4.8.2 (January 2026)
**Jonas Quinn "Eidetic Memory" Bug Fix**

- ✅ **Jonas Quinn Card Selection Fixed** – Clicking on cards in the Jonas Quinn overlay now properly copies the selected card to your hand:
  - Fixed `draw_jonas_peek_overlay` to return card rects for click detection
  - Changed overlay from view-only to interactive selection (click card to copy)
  - Updated instruction text from "Click to close" to "Click a card to copy it to your hand"
- ✅ **AI Ability Spam Prevention** – Fixed AI leader ability checks running every frame:
  - Added `ai_ability_tried` flag to limit ability checks to once per AI turn
  - Flag resets when player's turn begins
- ✅ **AI Jonas Quinn Support** – AI opponents with Jonas Quinn leader now properly use the Eidetic Memory ability:
  - Tracks player's drawn cards (`player1_drawn_cards`) when AI has Jonas Quinn
  - AI auto-selects highest power card from player's draws

### Version 4.8.0 (January 2026)
**Stargate UI Polish & Visual Effects**

- ✅ **MALP Feed History Panel** – Re-skinned the game history panel as a MALP (Mobile Analytic Laboratory Probe) tactical feed:
  - Scan-line grid overlay with subtle cyan tint for that military monitor aesthetic
  - Monospaced "Courier New" terminal font for authentic SGC feel
  - Blinking red "MALP FEED" indicator in the top-right corner
- ✅ **Iris Defense Visual Overlay** – When the Tau'ri Iris is activated, opponent rows now show:
  - Metallic titanium shutter pattern with 6 interlocking blades
  - "GATE SHIELD ACTIVE" text in amber across the ranged row
  - Overlay persists until the Iris blocks an incoming card
- ✅ **Red Hover Effects for DHD Buttons** – All DHD-style buttons now glow red on mouse hover:
  - Main menu options: hover color, glow, and edge highlights turn red
  - DHD back buttons: outer ring, chevron symbols, and center button turn red on hover
- ✅ **Mulligan Phase Ring Sound** – The ring transport sound (ring.ogg) now plays when entering the mulligan phase, providing audio feedback for the "wormhole opening" moment

### Version 4.7.1 (January 2026)
**Code Architecture & Bug Fixes**

- ✅ **Ability System Refactor (String → Enum)** – Replaced fragile string-based ability checks with a type-safe enum system:
  - New `abilities.py` module with `Ability` enum containing all 22 abilities
  - Helper functions: `has_ability()`, `is_hero()`, `is_spy()`, `is_medic()`, `can_be_targeted()`
  - Updated all ability checks across 9 files (game.py, main.py, ai_opponent.py, power.py, board_renderer.py, selection_overlays.py, deck_builder.py, render_engine.py, draft_mode.py)
  - Eliminates typo bugs and enables IDE autocomplete for ability names
- ✅ **Centralized Hardcoded Values** – Moved 50+ magic numbers into `game_config.py`:
  - Animation durations: `ANIM_INSTANT` (300ms) → `ANIM_PERSISTENT` (2500ms)
  - Timing constants: `TYPING_TIMEOUT`, `POPUP_DISPLAY_TIME`, `MULLIGAN_TIMEOUT`
  - Font sizes: `FONT_SIZE_TINY` (14) → `FONT_SIZE_GIANT` (72)
  - Extended UI colors: Highlight colors, text colors, background overlays
  - Helper functions: `scaled_font()`, `get_faction_ui_color()`
  - Updated selection_overlays.py, main.py, lan_chat.py to use centralized constants
- ✅ **Rule Compendium Fix** – Fixed missing "Unlockable Collection" sections for Jaffa Rebellion and Lucian Alliance factions in Tab 9 (Full Card Glossary):
  - Root cause: Faction names in `unlocks.py` didn't match full names used elsewhere ("Jaffa" vs "Jaffa Rebellion", "Lucian" vs "Lucian Alliance")
  - Fixed faction names in UNLOCKABLE_CARDS dictionary
  - Regenerated `rules_menu_spec.md` - all 6 factions now show their unlockable cards

### Version 4.6.0 (January 2026)
**DHD Back Buttons & Navigation Polish**

- ✅ **DHD-Style Back Buttons** – Replaced all "Departure" and "Back" buttons with circular DHD (Dial Home Device) buttons across the game:
  - Metallic ring with 7 glowing orange chevron symbols
  - Cyan glowing center button (like the Stargate's DHD activation crystal)
  - Consistent top-left positioning across all menus
  - Applied to: Deck Builder, Options, Settings, Stats Menu, Draft Mode UI
- ✅ **Continuous Keyboard Navigation** – Holding arrow keys now continuously browses cards/menus instead of requiring repeated key presses (300ms delay, 50ms repeat interval)
- ✅ **Spacebar Preview Fix** – SPACE now correctly previews the selected card instead of playing it (F key plays cards)
- ✅ **Wider Chat/History Panel** – Narrowed row score boxes (220px → 150px) to give more space to the history panel (220px → 300px)
- ✅ **LAN Chat UI** – Added visible chat input box and "Press T to chat" hint in LAN mode, plus "Peer is typing..." indicator
- ✅ **Mulligan Phase Cleanup** – Removed descriptive text overlay during mulligan for cleaner visuals
- ✅ **Deck Builder Keyboard Fix** – Fixed critical bug where arrow keys and other keyboard navigation wasn't working in the deck builder (events weren't being passed to handler)
- ✅ **Consistent Tab Navigation** – Added correct filter tabs for deck builder keyboard navigation (all, close, ranged, siege, agile, legendary, special, weather, neutral)

### Version 4.5.0 (January 2026)
**Universal Keyboard Controls & Row-Type Highlighting**

- ✅ **Universal Keyboard Navigation** – The entire game is now fully playable with keyboard:
  - **In-Game Combat**: LEFT/RIGHT to select cards in hand, UP/DOWN for row selection, F to play card, SPACE to preview card, G for faction power, Tab to cycle Pass/Faction Power buttons, SPACE to activate selected button
  - **Deck Builder**: Tab to switch focus between card pool and deck list, LEFT/RIGHT to navigate card pool with auto-scroll, UP/DOWN to navigate deck or switch filter tabs, F/ENTER to add card, DELETE/BACKSPACE to remove, SPACE to preview
  - **Stats Menu**: UP/DOWN arrows, PAGE UP/DOWN, HOME/END for scrolling
  - **Draft Mode**: LEFT/RIGHT between choices, UP/DOWN for menu navigation, ENTER/SPACE to select
  - **Mulligan Phase**: LEFT/RIGHT to select cards, SPACE to toggle selection, ENTER to confirm
- ✅ **Row-Type Color Highlighting** – Cards now show their row type when hovered or keyboard-selected:
  - **Close Combat**: Red border
  - **Ranged**: Blue border
  - **Siege**: Green border
  - **Agile**: Yellow border
  - **Weather/Special**: Light blue/gold border
- ✅ **Enhanced Pause Menu** – ESC now shows consistent pause menu with Back, Options, Main Menu, and Quit buttons with hover effects
- ✅ **Settings Menu Integration** – Options button in pause menu opens settings with Master, Music, and SFX volume sliders
- ✅ **Standardized Fullscreen** – F11 is now the only fullscreen toggle (removed Alt+Enter for consistency)
- ✅ **Keyboard Hints** – Visual hints show available keyboard controls during gameplay
- ✅ **Button Selection Glow** – Pass and Faction Power buttons show cyan glow when keyboard-selected

### Version 4.4.0 (January 2026)
**Post-Game Menu, Draft Mode Save, Performance & Bug Fixes**

- ✅ **Stargwent-Styled Post-Game Menu** – Game over screen now features polished Stargwent-style buttons with hover effects, glowing borders, and proper scaling. Buttons include REMATCH, MAIN MENU, and QUIT with distinct color schemes.
- ✅ **Draft Mode Save & Continue** – When winning a draft match, players now see three options: CONTINUE DRAFT (proceed to next battle), SAVE & EXIT (save progress and return to menu), or ABANDON DRAFT (end the run early). Draft progress is automatically saved!
- ✅ **Critical Card Bug Fix** – Fixed a major bug where cards were not being deep-copied when building decks. This caused shared state issues where playing a card (like Oma Desala) on one side would make the same card unplayable on the other side.
- ✅ **Taller Game Rows** – Increased combat row heights from 10% to 11% of screen height for better card visibility. Card aspect ratio adjusted to 1:1.4 for slightly wider cards.
- ✅ **Performance Optimizations** – Added font caching to avoid expensive font creation each frame. Added surface caching for common overlay surfaces. Switched from smoothscale to scale for faster image resizing. These changes improve FPS significantly.
- ✅ **Weather Card Drag Highlighting** – Verified that weather cards properly highlight affected rows when dragged (already implemented in board_renderer.py).

### Version 4.3.1 (January 2026)
**Architecture Refactoring & Code Health**

- ✅ **Modular Architecture** – Split monolithic 6,000+ line `main.py` into logical, maintainable modules:
  - `display_manager.py` (138 lines) – Centralized display mode, resolution, and fullscreen handling
  - `game_config.py` (213 lines) – All layout calculations, fonts, colors, and configuration constants
  - `render_engine.py` (794 lines) – Complete drawing system (cards, hands, UI elements, leader portraits)
  - `main.py` (5,033 lines) – Core game loop now focused on game logic without rendering clutter
- ✅ **Improved Maintainability** – Changes to display, config, or rendering no longer risk breaking unrelated systems
- ✅ **Centralized Configuration** – Single source of truth for all layout percentages, colors, fonts, and dimensions
- ✅ **Better Testability** – Each module can now be tested independently
- ✅ **Code Deduplication** – Removed ~80 lines of redundant layout calculations
- ✅ **Cleaner Imports** – All display, config, and render functions properly imported from their respective modules
- ✅ **No Regressions** – Full backward compatibility maintained; all features work exactly as before

### Version 4.2.0 (January 2026)
**Deck Builder Visual & Functional Polish**

- ✅ **Circular Icon Tabs** – Replaced rectangular text tabs with high-quality circular buttons featuring distinct icons for each card category (Close, Ranged, Siege, etc.).
- ✅ **New Card Categories** – Added dedicated "Special" and "Neutral" tabs to better organize non-unit cards and cross-faction assets.
- ✅ **Icon Quality Upgrade** – Tab icons now scale smoothly to 75% of the button diameter, ensuring crisp visuals even at 4K resolution.
- ✅ **Asset Reorganization** – Migrated all UI icons to a dedicated `assets/icons/` directory for cleaner project structure.
- ✅ **UI Cleanup** – Removed redundant instruction text from the deck builder for a cleaner, more immersive look.

### Version 4.0.1 (January 2026)
**Goa'uld Symbiote Animation & LAN Improvements**

- ✅ **Goa'uld Symbiote Animation** – When played, the Goa'uld Symbiote card triggers a creepy larva animation:
  - Snake-like symbiote with 18 body segments that coil, leap, and seek a host
  - Three animation phases: Coil (prepare), Leap (arc through air), Land (wrap around target)
  - Glowing red eyes, fangs visible during attack, greenish slime trail
  - "SEEKING HOST..." text floats during the leap phase
- ✅ **LAN Chat Timestamps** – All chat messages now display `[HH:MM]` timestamps in a dim gray color for better conversation tracking
- ✅ **LAN Rematch System** – After a LAN game ends, players can:
  - Press **P** to **Play Again** – Stay connected and choose new faction/leader
  - Press **ESC** to **Disconnect** – Close the connection and return to menu
  - Both players must confirm rematch before proceeding to deck selection
  - Ready status shown for both players in the rematch lobby

### Version 4.0.0 (January 2026)
**Draft Mode Gauntlet & Unified Faction Visuals**

- ✅ **Expanded Draft Mode Gauntlet** – Draft Mode is now a multi-stage roguelike challenge!
  - Survive up to 8 wins to become the Draft Champion.
  - **Milestone (3 Wins)**: Redraft 5 cards of your choice to refine your synergies.
  - **Milestone (5 Wins)**: Option to redraft your Leader to adapt your endgame strategy.
  - **Victory (8 Wins)**: Unlock a special Easter Egg hint for future content!
  - **Persistence**: Draft runs are now saved and can be resumed from the main menu.
- ✅ **Unified Faction Colors** – Standardized the visual identity of all factions across the entire game:
  - **Lucian Alliance**: Now consistently Pink `(200, 100, 255)` in UI, text, and glow effects.
  - **Asgard**: Now a bright, high-tech Cyan `(100, 255, 255)`.
  - Applied to Draft Mode UI, Stats Menu, Deck Builder, and in-game combat effects.
- ✅ **XP System Removal** – Removed the redundant XP calculation and tracking to focus on the more direct Card and Leader unlock progression system.
- ✅ **Stability Fixes** – Fixed a bug where resuming a Draft Mode run at the `leader_select` phase would result in an empty screen.

### Version 3.9.4 (December 2025)
**Unlockable Card Logic Verification & Bug Fixes**

- ✅ **Complete Logic Audit** – Deep verification of all 20 unlockable card abilities:
  - Verified draw mechanics (Mothership, Prometheus, Tok'ra Operative)
  - Confirmed destruction logic (Ancient Drone destroys LOWEST unit)
  - Validated summoning (Gate Reinforcement, Deploy Clones)
  - Tested combat calculations (Survival Instinct, Tactical Formation)
  - Verified Legendary Commander immunity (weather, horns, scorch)
  - Confirmed special effects (Thor's Hammer, Merlin Device, Communication Stones)
- ✅ **ZPM Power Fix** – Critical bugs fixed:
  - **Logic Fix**: Now applies doubling during score calculation (not when played)
  - Preserves leader bonuses and other effects
  - **Persistence Fix**: Effect now lasts the entire round (was being reset immediately)
  - Example: 8-power siege with Carter +2 = 10 → ZPM makes it 20 ✅
- ✅ **Animation Fix** – Fixed crash when playing special effect cards:
  - Removed invalid `easing` parameter from Animation base class calls
  - Fixed ZPM, Thor's Hammer, Merlin Device, Communication Stones, Dakara animations
- ✅ **Puddle Jumper Fix** – Ring Transport now works for unit cards:
  - Added selection UI when picking up unit cards with Ring Transport
  - Drag onto unit → triggers Ring Transport with golden ring animation
  - Drag to empty row → plays as 5-power agile unit
  - Versatile gameplay: use as unit OR as Ring Transport
- ✅ **Replicator Swarm Description** – Fixed misleading ability text:
  - Changed from "Gain +2 per unit" to just "Tactical Formation"
  - Clarifies that it multiplies base power by copy count (not adds +2)
- ✅ **Sodan Warrior Animation** – Added CommunicationRevealEffect when played
- ✅ **All 20 Cards Verified** – Every unlockable card has correct logic and animations

### Version 3.9.2 (December 2025)
**Witcher-Style Deck Builder UI Overhaul**

- ✅ **Bottom Accordion Card Pool** – Cards now displayed in a horizontal scrolling strip at the bottom of the screen:
  - 2x sized cards (160×240) for better visibility
  - Smooth lift animation on hover (25px rise with shadow)
  - Card names appear below on hover
  - Power badges with faction-colored borders
  - Scroll indicators (◀ ▶) when content overflows
  - Pool count indicator showing filtered card total
- ✅ **Right-Side Vertical Deck List** – Your deck displayed as a sleek list panel:
  - Row-type color indicators (red=close, blue=ranged, gold=siege, etc.)
  - Power circles with values for unit cards
  - Truncated names with quantity badges (x2, x3)
  - Quick remove button (×) on hover
  - Scrollable with mouse wheel
- ✅ **Holographic Stats Panel** – Translucent top-left panel with:
  - Total cards / max (40)
  - Unit count with minimum indicator (15 required)
  - Special and Weather card counts
  - Total deck strength
  - Deck validity status with icon
- ✅ **Back Button** – Stylized back button in top-left (now upgraded to DHD style in v4.6.0)
- ✅ **Top-Center Faction Tabs** – Card type filters maintained from previous version
- ✅ **Improved Drag & Drop** – Drag from accordion to deck list to add, drag out to remove
- ✅ **Right-Click Preview** – Works on both accordion cards and deck list items
- ✅ **Horizontal Scroll** – Mouse wheel scrolls accordion horizontally when hovering bottom area

### Version 3.9.1 (December 2025)
**Stats Menu Overhaul & Bug Fixes**

- ✅ **Comprehensive Stats Menu** – Full player statistics tracking:
  - **Overall**: Games played, win rate, current/best streaks
  - **Unlock Progress**: Leaders and cards unlocked (X/20)
  - **Faction Win Rates**: Per-faction win/loss records with percentages
  - **By Mode**: Separate AI and LAN game tracking (fixed!)
  - **Round Breakdown**: Perfect games (2-0), close wins (2-1), comebacks, sweeps
  - **Leaders**: Most played leader with win rate percentage
  - **Matchups**: Best AND worst faction matchups
  - **Recent Form**: Last 10 games W/L history
  - **Game Length**: Average, fastest, and longest games
  - **Mulligans**: Average cards mulliganed per game
  - **Abilities Used**: Medical Evac, Ring Transport, Faction Power, Iris usage counts
  - **Top Cards**: Most played cards with win rates
  - **LAN Reliability**: Completed games and disconnects
  - **Draft Mode**: Full arena stats (existing)
- ✅ **Red DHD Reset Button** – Stargate-themed circular button with glowing red center, 9 chevrons, and pulsing animation
- ✅ **LAN Mode Tracking Fix** – Fixed critical bug where AI games were incorrectly counted as LAN games after playing a LAN match
- ✅ **Card/Leader Hover Preview** – Hover over top cards or leaders to see 4x scale preview with faction glow

### Version 3.9.0 (December 2025)
**Faction Power Overhaul & Replicator Swarm**

- ✅ **Asgard Transporter FX** – Replaced Holographic Decoy's lattice with a lore-accurate Asgard beaming effect. Units now de-materialize into white light and re-materialize in their new rows.
- ✅ **Lucian Alliance EM Glitch** – The Naquadah Assault now features a screen-wide scanline/glitch effect, simulating the electromagnetic pulse of a massive naquadah explosion.
- ✅ **Goa'uld Sarcophagus Animation** – Sarcophagus Revival now features a physical sarcophagus with a lid that slides open to release golden energy before sealing shut again.
- ✅ **Combat Text Labels** – Score pop-ups now support "Combat Text" tags. See "BUFFED!", "INSPIRED!", or "WIPED!" float alongside score changes in different colors.
- ✅ **Replicator Swarm Weather** – Added a new weather type. Small, grey, geometric blocks jitter erratically across affected rows, simulating a swarm of Replicators consuming the battlefield.

### Version 3.7.0 (December 2025)
**Weather Animations, Card Preview & Draft Synergies**

- ✅ **Persistent Row Weather Animations** – Each weather card now has unique visual effects that remain on affected rows until cleared:
  - **Ice Planet Hazard** (Close): Blue ice crystals/snowflakes falling with sparkle effects and pulsing blue border
  - **Nebula Interference** (Ranged): Purple/pink cosmic clouds drifting with layered fog particles
  - **Asteroid Storm** (Siege): Orange fiery meteors streaking down with trail effects and bright heads
  - **Electromagnetic Pulse** (Any): Cyan glowing particles with electric arc/lightning effects
  - **Wormhole Stabilization** (Clear): Blue spiral vortex that expands then collapses like a black hole
- ✅ **Animated Weather Borders** – Affected rows now have pulsing faction-colored borders that animate continuously
- ✅ **Enhanced Card Preview (Right-Click)** – Cards now display at 2x scale with:
  - Smooth scaling for crisp images at larger sizes
  - Faction-colored glow effect around card border
  - Semi-transparent dark overlay for better focus
  - Wider description box with better typography
  - Responsive sizing that adapts to screen
- ✅ **Draft Mode Synergy System** – Card choices now show synergy scores:
  - Green border highlights high-synergy cards (+3 or more)
  - Synergy reasons shown on hover (e.g., "+3 Tight Bond (2 copies)")
  - Evaluates: Tactical Formation, Gate Reinforcement, row balance, hero/spy/medic value
  - **Undo Feature**: Press Z or Backspace to undo last pick
- ✅ **Draft Stats Enhancement** – Review phase now shows hero/spy/medic counts
- ✅ **Ability Button Labels** – Faction power and leader ability buttons now show ability names and READY/USED status

### Version 3.6.0 (December 2025)
**Grand AI Overhaul & Tactical Precision**

- ✅ **Elite AI Opponent** – AI logic rebuilt for strategic depth:
  - **Hero Preservation**: AI now saves Legendary Commanders for Round 3 or critical weather turns.
  - **Bleeding Strategy**: AI will "bleed" the opponent in Round 2 if it wins Round 1.
  - **Smarter Powers**: Faction Powers reserved for high-value targets (e.g., Scorch hits 12+ power units).
- ✅ **Iris Defense Fix** – Fixed a critical bug where non-Tau'ri factions could use Iris Defense.
- ✅ **O'Neill Clone Token** – Jack O'Neill's ability spawns a dedicated `tauri_oneill_clone` token card.
- ✅ **Icon Rendering Fix** – Fixed missing icons in the history log (🔥, 🤝, 🚪 now display correctly).

### Version 3.5.0 (December 2025)
**Narrator, Chat Integration & Precision Gameplay**

- ✅ **Integrated "Narrator" History** – The history log is now a storytelling tool! Instead of just "Card Played", it explains *why* things happen:
  - *"Scorch vaporized 3 units! (-15)"* - Shows exact score impact.
  - *"Rak'nor inspires adjacent units!"* - Narrates passive triggers.
  - *"Iris blocked Wraith Hive!"* - Confirms defensive moves.
- ✅ **Seamless Chat Integration** – Chat messages are now injected directly into the History Panel with color coding:
  - **Gold**: System/Narrator messages
  - **Green**: Your messages
  - **Blue**: Opponent messages
  - **Red**: Destruction events
- ✅ **Non-Intrusive Input** – Removed the full-screen chat modal. Press 'T' or 'Enter' to toggle a sleek input line below the history panel.
- ✅ **Precision Card Placement** – You can now drop cards **between** existing units on the board! The game calculates the insertion index based on your mouse position, giving you full control over adjacency bonuses (vital for Inspiring Leadership!).
- ✅ **Draft Mode UI Polish** – "Your Deck" sidebar is now scrollable and groups duplicate cards (e.g., "2x Jaffa Guard") for cleaner reading. "Start Battle" button is centered and prominent.

### Version 3.0.0 (December 2025)
**Draft Mode (Arena)**

- ✅ **Roguelike Deck Building** – New game mode! Build a deck from scratch by picking 1 of 3 cards at a time until you have 30.
- ✅ **Cross-Faction Chaos** – Draft pool includes ALL unlocked cards from ALL factions. Combine Asgard tech with Goa'uld numbers!
- ✅ **Risk/Reward** – Choose your leader wisely at the start—their ability defines your run.
- ✅ **Multi-Stage Progression** – The fight doesn't end at one battle!
  - **1 Win**: Earn standard Card & Leader unlocks.
  - **3 Wins**: Milestone reached! **Redraft 5 cards** to refine your synergy.
  - **5 Wins**: Milestone reached! **Redraft your Leader** to adapt for the endgame.
  - **8 Wins**: **DRAFT CHAMPION!** Complete the run and discover a hidden Easter Egg... 🚀

### Version 2.9 (November 2025)
**LAN Multiplayer Overhaul & Robustness**

- ✅ **LAN Game Loop Fixed** – Critical fix: game loop now actually runs after deck selection (was broken since v2.2)
- ✅ **LAN Opponent Animations** – All animations now display for both players:
  - Card play effects (Stargate activation, weather, Naquadah explosions)
  - Special ability animations (Vampire, Inspiring Leadership, Deploy Clones, etc.)
  - Faction power animations (Gate Shutdown with Iris closing, Sarcophagus Revival, etc.)
  - Legendary Commander entry effects
- ✅ **AI Animation Parity** – AI opponent now triggers same animations as player:
  - Faction power effects with full visuals
  - Card ability animations (previously missing)
  - Iris Defense activation with animation
- ✅ **Improved LAN Menu UI** – Completely redesigned Host/Join interface:
  - 400×70px buttons (was 260×40) with 36px font
  - Hover effects and color-coded buttons (green=Host, blue=Join)
  - Gradient backgrounds and rounded corners
  - Tailscale IP prioritization (100.x.x.x shown first with ★ RECOMMENDED)
- ✅ **Enhanced IP Detection** – Multi-method IP detection for Tailscale support:
  - Parses `ip addr` output for all interfaces
  - Connects to Tailscale coordination server (100.100.100.100)
  - Falls back to standard socket methods
  - No sudo required, no network traffic sent
- ✅ **LAN Chat Overlay in Main Loop** – Chat now lives in the core game loop: toggle with `T` or `ESC`, modal "Subspace Communications" window, "Press T to Chat" hint when closed, "Dialing..." typing indicator, and the history panel stays visible during LAN matches.
- ✅ **LAN State Sync Fixes** – Mulligans and Hathor’s steal now stay in lockstep: both players see the heart-kiss animation and the stolen card lands in the correct row before turns switch.

### Version 2.8 (November 2025)
**Complete Audio System Overhaul**

- ✅ **Round-Based Battle Music** – Music intensity increases each round:
  - `battle_round1.ogg` - Opening battle theme
  - `battle_round2.ogg` - More intense mid-game music
  - `battle_round3.ogg` - Climactic final round music
- ✅ **Faction Theme Preview** – Hover over factions in selection menu to hear their theme
  - Music plays while hovering, stops when you move away
  - Each faction has unique audio identity before you commit
- ✅ **Voice Snippets for All 27 Legendary Commanders** – Character voice clips play when deployed:
  - **Tau'ri (4)**: O'Neill, Hammond, Jackson, Carter
  - **Goa'uld (5)**: Sokar, Yu, Hathor, Apophis, Isis
  - **Jaffa (4)**: Teal'c, Bra'tac, Rak'nor, Master Bra'tac
  - **Lucian (4)**: Vulkar, Curtis, Sodan Master, Ba'al Clone
  - **Asgard (3)**: Freyr, Loki, Heimdall
  - **Neutral (6)**: Ascended Daniel, Oma Desala, McKay, Teyla, Ancient Drone, Weir
- ✅ **Unit Card Sounds** – Row-type sounds for non-legendary cards (every 4th card):
  - `close.ogg`, `ranged.ogg`, `siege.ogg`
- ✅ **Ring Transport Sound** – `ring.ogg` plays on every Ring Transport use
- ✅ **New Sound Manager System** – `sound_manager.py` handles loading, caching, and playback
- ✅ **Graceful Fallback** – Missing audio files are silently skipped (no crashes)

### Version 2.7 (November 2025)
**Complete Leader Abilities, Alliance Tracking & UI Polish**

- ✅ **7 New Leader Abilities Implemented** – All 35 leaders now fully functional:
  - **Gen. Landry** - "Homeworld Command": +1 power to units in most populated row
  - **Ba'al** - "System Lord's Cunning": Once per game resurrect unit from discard
  - **Jonas Quinn** - "Eidetic Memory": Copy a card opponent has drawn
  - **Vala Mal Doran** - "Thief's Luck": Steal random card from opponent at round 2
  - **Kiva** - "Brutal Tactics": First unit each round gets +4 power
  - **Thor Supreme Commander** - "Fleet Command": All Mothership/O'Neill ships +3
  - **Aegir** - "Asgard Archives": Draw 1 card when playing siege units
- ✅ **Alliance Combo History Tracking** – All alliance activations now visible in history:
  - SG-1 United (+5 to O'Neill, Carter, Jackson, Teal'c)
  - Tok'ra Alliance (+3 to Carter + Tok'ra Operative)
  - System Lords Summit (+4 to Apophis, Yu, Sokar)
- ✅ **Balance Configuration System** – Centralized BALANCE_CONFIG for easy tuning:
  - Jaffa Brotherhood max, Goa'uld Command bonus, Ancient Control Chair bonus
  - Asgard Beam threshold all configurable
- ✅ **Stargate-Themed UI Buttons** – Beautiful new button designs:
  - Leader ability button: Stargate ring with 9 chevrons and dot pattern
  - Faction power button: Full Stargate with faction-specific event horizon colors
  - Tau'ri: Blue horizon, silver ring | Goa'uld: Red/orange, gold ring
  - Jaffa: Golden horizon, bronze ring | Lucian: Purple horizon
  - Asgard: Cyan horizon, white ring
- ✅ **Critical Bug Fixes**:
  - Tactical Formation now correctly preserves leader bonuses (was wiping them)
  - Rya'c ability fixed (was crashing the game)
  - Asgard Beam artifact now destroys all 8+ power units (was doing nothing)
- ✅ **LAN Multiplayer Polish**:
  - Removed AI "thinking/resolving" messages when playing humans
  - Improved lobby UI with better alignment and styling
  - Enhanced chat panel display

### Version 2.5 (October 2025)
**Enhanced History, Sound Control & Multiplayer Polish**

- ✅ **Enhanced Game History** – Comprehensive event tracking for single-player matches:
  - Round start/end announcements with scores
  - Leader ability activations (O'Neill clones, Penegal revival, Anateo medic, etc.)
  - Card draw bonuses tracked (Teal'c wins, O'Neill resourcefulness)
  - Weather effects logged (Ice Planet, Nebula, EMP, Wormhole clear)
  - Scorch/special abilities with destroyed card details
  - Thor's Hammer, ZPM, Communication Device events
  - McKay/Yu pass abilities
- ✅ **Master Volume Slider** – Interactive sound control in Options menu:
  - Drag-to-adjust volume slider (0-100%)
  - Real-time volume changes (hear adjustments immediately)
  - Persistent settings saved to `game_settings.json`
  - Applies to menu music, battle music, and SFX
  - Clean blue gradient UI design
- ✅ **LAN Waiting Lobby** – Enhanced multiplayer pre-game experience:
  - Ready/Not Ready system (both players must confirm)
  - Live chat while waiting in lobby
  - Visual status indicators (Host/Client roles)
  - "START MATCH" button appears when both ready
- ✅ **Jonas Quinn Ability Fixed** – Now shows only cards drawn AFTER mulligan (not starting hand):
  - Tracks opponent draws during rounds
  - Shows all drawn cards in horizontal layout
  - Clear overlay with card count
  - Excludes starting hand from visibility
- ✅ **Ryac Leader Matchup** – Added character quotes for unlockable Jaffa leader:
  - vs Apophis: "I am Jaffa. I will not be your slave!"
  - vs Teal'c: "I will make you proud, Father."
  - vs Bra'tac: "Master Bra'tac taught me the ways of freedom."
- ✅ **Ring Transport Rework** – Neutral decoy cards now behave like true Stargate recalls:
  - Drag Ring Transport onto any non-Hero unit (ally or enemy) to beam it directly into your hand
  - Board slots stay empty (no placeholder Decoy), so row totals update instantly
  - History log records each transport and AI logic shares the same streamlined flow
- ✅ **Hathor Seduction Rework** – Click Hathor's leader badge to abduct the enemy's weakest non-Hero unit:
  - Automatically targets the opponent's lowest-power combat unit (skips Legendary Commanders and specials)
  - Plays a bespoke heart-kiss animation before slotting the stolen card into your matching row
  - Round history logs the theft, both scoreboards recalc immediately, and the AI uses the same timing logic when piloting Hathor

### Version 2.2 (October 2025)
**LAN Multiplayer & Leader Refinements**

- ✅ **LAN Multiplayer COMPLETE** – Host/Join system with deck selection, leader matchup animation, and full 2-player networked gameplay!
  - NetworkController replaces AI for remote opponents
  - All actions sync over LAN (card plays, pass, faction powers)
  - Chat system replaces history panel during multiplayer
  - Unlock override for balanced LAN play
- ✅ **Catherine Langford Redesign** – New ability "Ancient Knowledge": Look at top 3 cards of deck, play one immediately (rest to bottom)
- ✅ **Rya'c Unlockable Leader** – Replaces Master Bra'tac with "Hope for Tomorrow": Draw 2 extra cards at start of round 3
- ✅ **Master Bra'tac Removed** – Consolidated duplicate Bra'tac leaders; regular Bra'tac remains as starter
- ✅ **Options Menu Polish** – "Unlock All" button redesigned with clean layout, status indicators, and faction-colored DHD button
- ✅ **Script Organization** – Moved `create_placeholders.py` to `scripts/` folder for cleaner project structure
- ✅ **Content Registry** – All leaders now centralized in `content_registry.py` for easier maintenance

### Version 1.9 (October 2025)
**Universal Matchups & Fullscreen Persistence**

- ✅ **Retro Neon Matchup HUD** – Leader names now use a retro cyberpunk font with faction-colored glow, scanlines, and proper portrait scaling for every confrontation.
- ✅ **Single Template Background** – `universal_leader_matchup_bg.png` replaces thousands of matchup PNGs; create_placeholders now generates the shared template and cleans up aliases automatically.
- ✅ **Persistent Fullscreen** – Toggling fullscreen via F11 (or launching with `python main.py --fullscreen` / `STARGWENT_FULLSCREEN=1`) keeps the entire experience in the chosen mode—from menus, to deck builder, to battle.
- ✅ **Card Reload Safety** – Switching display modes re-renders the board and reloads card assets so everything stays crisp in both windowed and fullscreen sessions.
- ✅ **Leader Background Alias Fix** – Master Bra'tac now reuses `leader_bg_jaffa_bratac.png`, preventing mismatched filenames and keeping the deck builder happy.

### Version 1.8 (September 2025)
**Preparations for Command Horn & HUD Overhaul**

- ✅ **Documentation Refresh** – README bumped to v1.8 to track the upcoming board/HUD rebuild work.
- ✅ **Spec Alignment** – Codex plan captured for the new percentage-based layout, accordion hands, right-HUD history column, and AI faction-power parity; implementation will land in the next tagged build.
- ℹ️ **Gameplay Code** – Currently identical to v1.7 so existing saves, decks, and ESC pause behavior remain untouched while we stage the next wave of UI fixes.

### Version 1.7 (September 2025)
**Stargwent Gwent-Style Balanced Layout**

#### Visual Layout Overhaul
- ✅ **Balanced Board Design** - Gwent-inspired layout with proper spacing for all elements
- ✅ **Clear Separation** - Opponent hand, rows, weather separator, player rows, and player hand all clearly separated
- ✅ **Dynamic Scaling** - All layout elements scale with screen height for perfect 4K/windowed support
- ✅ **No Overlap** - Opponent hand floats above their siege row, player hand detached from player siege row
- ✅ **Weather Separator** - Visible 5% screen height divider between factions (dark backdrop with borders)
- ✅ **Lane Labels** - Faded row labels (⚔ CLOSE, 🏹 RANGED, ⚙ SIEGE) on right side
- ✅ **Unified Command Bar** - Bottom-right "command zone" with Faction Power and Pass button aligned

### Version 1.6 (September 2025)
**Fullscreen Polish & Round Winner Announcements**

