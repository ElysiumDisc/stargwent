# Stargwent 🌌⚡

**A Gwent-style card game set in the Stargate SG-1 universe**

Battle with iconic characters and technology from the Tau'ri, Goa'uld, Jaffa, Lucian Alliance, and Asgard in this strategic card game featuring stunning visual effects, comprehensive progression system, and full deck customization!

---

## ⚠️ Fan Project Disclaimer

**This is a non-commercial fan project created purely out of love for two amazing franchises:**

- **Stargate SG-1** - The legendary sci-fi series by MGM that brought us the Stargate universe
- **Gwent** - The brilliant card game from CD Projekt Red's The Witcher 3: Wild Hunt

**No copyright infringement is intended.** This project is a tribute and fan service to both franchises. We do not claim ownership of any Stargate or Gwent intellectual property. This is an educational hobby project made by fans, for fans, with no commercial purpose whatsoever.

*Indeed.* - Teal'c

---

<!-- VERSION: Update this badge to change the version everywhere (README, .deb package, GitHub) -->
![Version](https://img.shields.io/badge/version-5.3.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Pygame CE](https://img.shields.io/badge/pygame--ce-2.5.6+-red)
![Resolution](https://img.shields.io/badge/resolution-2K%20(2560x1440)-purple)
![Status](https://img.shields.io/badge/status-Optimized-brightgreen)

---

## 📋 Table of Contents

- [✨ Key Features](#-key-features)
- [🚀 Quick Start](#-quick-start)
- [🎮 How to Play](#-how-to-play)
- [🎴 Factions & Leaders](#-factions--leaders)
- [⚡ Faction Powers](#-faction-powers)
- [🃏 Card Abilities](#-card-abilities)
- [🏆 Progression System](#-progression-system)
- [🎨 Visual Features](#-visual-features)
- [⌨️ Controls](#️-controls)
- [🌐 LAN Multiplayer Architecture](#-lan-multiplayer-architecture)
- [📊 Implementation Status](#-implementation-status)
- [🏗️ Project Structure](#️-project-structure)
- [🔧 Technical Details](#-technical-details)
- [🛠 Build & Packaging](#-build--packaging)
- [📜 Rules Spec Generator](#-rules-spec-generator-auto-detection)
- [🛠️ Content Manager](#️-content-manager-developer-tool)
- [📝 License & Credits](#-license--credits)

---

### ✨ Key Features

### 🎮 Complete Card Game Experience
- **100% Fully Implemented** - All mechanics, powers, animations, persistence, LAN multiplayer, and Draft Mode
- **219 Cards** across 5 factions + Neutral cards with 20+ Stargate-themed abilities
- **35 Unique Leaders** (15 base + 20 unlockable) each with special abilities
- **25+ Hero Animations** - Unique cinematic entry effects for legendary commanders
- **Legendary Commander Voice Clips** - Character quotes play when heroes are deployed

### 🎨 Stargate-Authentic UI
- **MALP Feed History Panel** - Military monitor aesthetic with scan-lines and terminal font
- **DHD Buttons** - Authentic Dial Home Device styling with glowing chevrons and cyan crystals
- **Iris Defense Overlay** - Metallic titanium shutter pattern when Tau'ri shield is active
- **Retro Neon Leader Nameplates** - Cyberpunk font with faction-colored glow and scanlines
- **Witcher 3 Gwent Layout** - Authentic board design with clear lane separation

### ⚔️ Deep Strategic Gameplay
- **Elite AI Opponent** - Hero preservation, Round 2 bleeding tactics, strategic faction power usage
- **Precise Card Placement** - Drop cards between existing units for tactical positioning
- **5 Unique Faction Powers** - Once-per-game abilities with cinematic animations
- **Interactive Abilities** - Medical Evac and Ring Transport with full selection UI

### 🏆 Draft Mode (Roguelike Gauntlet)
- **8-Win Challenge** - Survive increasingly difficult AI opponents
- **Cross-Faction Drafting** - Build decks from ALL factions (30 cards, pick 1 of 3)
- **Redraft Milestones** - At 3 wins: redraft 5 cards. At 5 wins: redraft your leader
- **Synergy Scoring** - Cards highlight when they combo with your current deck
- **Save & Continue** - Progress persists between sessions

### 🌐 LAN Multiplayer
- **Full 2-Player Networked Gameplay** - Host/Join with deck selection and chat
- **Room Codes** - Share easy codes like "GATE-7K3M" instead of IP addresses
- **Tailscale Support** - Smart IP detection prioritizes VPN addresses for remote play
- **Rematch System** - Play again with new faction/leader or disconnect
- **Integrated Chat** - Press 'T' to chat, quick chat keys 1-5, sound notifications
- **Connection Quality** - Real-time latency indicator (green/yellow/red) in HUD
- **Reliable Connections** - JSON error recovery, host timeout, graceful disconnect handling

### 🎨 Visual Polish
- **4K Native Resolution** (3840×2160) with perfect scaling
- **Persistent Weather Animations** - Ice crystals, fiery meteors, nebula clouds, EMP arcs
- **Faction Power Cinematics** - Asgard beams, Goa'uld sarcophagus, Lucian EM glitches
- **Combat Text Pop-ups** - "BUFFED!", "INSPIRED!", "WIPED!" float with score changes
- **Smooth Card Interactions** - Hover enlargement, drag shadows, glow borders

### ⌨️ Universal Controls
- **Full Keyboard Navigation** - Arrow keys, F to play, G for faction power, Tab to cycle
- **Row-Type Highlighting** - Cards glow red (close), blue (ranged), green (siege)
- **Mouse + Keyboard** - Drag-and-drop or keyboard-only gameplay

### 💾 Progression & Customization
- **Witcher-Style Deck Builder** - Accordion card pool, holographic stats, drag-and-drop
- **Card Unlock System** - Win games to unlock 20+ powerful cards
- **Leader Unlock System** - Win 3 in a row to unlock alternate faction leaders
- **Comprehensive Stats Menu** - Win rates, round breakdowns, matchup history
- **Persistent Saves** - All progress saved to JSON

### 🆕 Recent Updates

#### v5.1.0 - Code Quality & Bug Fixes
- **Clone Token Fix** - O'Neill clones now correctly live 4 turns (was 3 due to off-by-one error)
- **Horn + ZPM Stacking** - Fixed 4x multiplier bug when both effects applied to siege cards
- **Card Validation** - Deck builder now validates card IDs preventing crashes during drag-drop
- **Exception Handling** - Replaced 15+ bare `except:` clauses with specific exception types
- **Debug Cleanup** - Removed debug print statements from production code
- **AI Calculation Fix** - Fixed Tactical Formation double-counting in AI evaluation

#### v5.0.0 - Deck Builder UI
- **Witcher-Style Deck Builder** - Complete redesign inspired by The Witcher 3's Gwent interface:
  - **Bottom Accordion**: Horizontal scrolling card pool with 2x sized cards, hover lift animation, and card name tooltips
  - **Circular Icon Tabs**: New high-resolution circular buttons for filtering cards by type (Close, Ranged, Siege, Special, etc.).
  - **Right Deck List**: Vertical list view showing power, name, quantity, and row-type color indicators
  - **Holographic Stats Panel**: Translucent top-left panel with deck validity, card counts, and total strength
  - **DHD Back Button**: Circular Dial Home Device button with metallic ring, glowing chevrons, and cyan center crystal (top-left in all menus)
  - **Top-Center Faction Tabs**: Filter cards by type (All, Close, Ranged, Siege, etc.)
- **Elite AI Strategy** - The AI now uses Gwent-style "bleeding" and hero preservation tactics to challenge even experienced players.
- **Draft Mode Polish** - "Your Deck" list is now scrollable, groups duplicates (e.g. "3x Alpha Team"), and features a centered "Start Battle" layout.
- **Integrated Comms** - Chat and Game History are now unified. Press 'T' to open a non-intrusive input box directly below the history panel.
- **Options Menu Alignment** — All labels/status text are perfectly centered above/below their toggles with consistent spacing.
- **Deck Builder Layout** — Type headers removed; cards use a simple grid with unified positioning and click detection for hover, inspect, and drag/drop; compact stats now sit in a clean box at the top-right of **Your Deck**.
- **Smooth Dragging Everywhere** — Deck builder runs at 144 FPS with lerped card dragging, subtle shadows, and glow borders for a buttery feel; in-match rendering already uses the same smooth follow/hover easing.

### 💾 Persistent Progression
- **Automatic Deck Saving** - Your deck is saved every time you finish customizing
- **Per-Faction Customization** - Each faction remembers your leader and deck choices
- **Win Tracking** - Track your wins, losses, and win streaks
- **Stats Menu** - View comprehensive statistics: overall record, AI vs LAN breakdown, leader usage, matchups, turn counts, and draft mode history
- **Leader Unlocks** - Earn new leaders every 3 consecutive wins
- **Cross-Session Saves** - All progress saved in `player_decks.json` and `player_unlocks.json`

### 🌌 Stargate Universe Integration
All abilities renamed and themed around Stargate lore:
- **Tactical Formation** - Unit coordination (was Tight Bond)
- **Gate Reinforcement** - Bring backup through the Stargate (was Muster)
- **Deep Cover Agent** - Tok'ra spies (was Spy)
- **Medical Evac** - Rescue fallen soldiers (was Medic)
- **Naquadah Overload** - Explosive destruction (was Scorch)
- **Ring Transport** - Asgard beam technology (was Decoy)
- **Command Network** - Tactical comms (was Commander's Horn)
- **Space Hazards** - Ice planets, nebulas, asteroid storms (was Weather)
- **Wormhole Stabilization** - Clear hazards with black hole animation!

### 🏆 Progression & Customization
- **Card Unlock System** - Win games to unlock 20+ powerful cards
- **Leader Unlock System** - Win 3 in a row to unlock faction leaders
- **Full Deck Builder** - Customize decks (25-40 cards, faction-specific unlocks)
- **Persistent Progress** - All unlocks saved to JSON
- **Win Streak Tracking** - Stats tracked across sessions
- **Faction-Specific Unlocks** - Leaders and cards match your chosen faction

### 🎨 Stunning Visual Effects
- **4K Resolution** - Native 3840×2160 support with perfect scaling
- **Persistent Row Weather Effects** - Each weather type has unique animations that remain on affected rows:
  - **Ice Planet Hazard**: Falling ice crystals with sparkle effects
  - **Nebula Interference**: Drifting purple/pink cosmic clouds
  - **Asteroid Storm**: Fiery orange meteors with trail effects
  - **Electromagnetic Pulse**: Cyan particles with electric arcs
  - **Wormhole Stabilization**: Blue spiral vortex (black hole clearing)
- **Animated Weather Borders** - Pulsing faction-colored borders on weathered rows
- **Naquadah Overload Animation** - Blue energy explosions with shockwave rings appear on rows where highest power units are destroyed
- **Smooth Card Interactions** - NEW v1.1: Cards follow mouse with easing (not snappy), gentle hover enlargement (8%), dynamic shadows
- **Juicy Drag FX** - Inspired by John Scolaro's [pygame card experiments](https://johnscolaro.xyz/blog/pygame-cards) and [pygame-examples repo](https://github.com/JohnScolaro/pygame-examples): cards tilt with momentum, glow near drop zones, and leave energy trails while you drag them
- **AI Turn Animations** - NEW v1.1: 4-phase cinematic AI actions (thinking particles → selection glow → card travel → resolution)
- **Delta Time Animations** - Frame-rate independent smooth motion at any FPS (30-144Hz)
- **Stargate Opening** - Epic KAWOOSH vortex animation before game starts
- **Hyperspace Transitions** - Streaking stars when entering/exiting hyperspace (rounds 2 & 3)
- **Planet Emergence** - Beautiful planet appearance in round 3
- **Animated Background** - Moving starfield, chevron glows, energy waves
- **Stargate Activation** - Portal effect when playing cards
- **Retro Neon Leader HUD** - Universal matchup template overlays glowing faction-colored typography and scanlines across the Stargate event horizon for every confrontation.
- **Score Animations** - Dramatic pop effects with deltas and **Combat Text labels** ("BUFFED!", "INSPIRED!", etc.)
- **Weather Effects** - Row-specific highlights plus custom particle fields:
  - **Ice Planet Hazard** - Blue ice crystals with sparkles
  - **Nebula Interference** - Purple/pink drifting clouds
  - **Asteroid Storm** - Orange fiery meteors with trails
  - **Electromagnetic Pulse** - Cyan glowing particles with lightning arcs
  - **Replicator Swarm** - Jittering grey metallic blocks consuming the row
- **EMP Plasma Field** - Floating green motes when Electromagnetic Pulse is active
- **Nebula Clouds** - Layered pink fog drifting through affected lanes
- **Black Hole Animation** - When clearing weather effects (Wormhole Stabilization)
- **Particle Systems** - Fire, energy bursts, faction-specific effects
- **DHD Button** - Glowing red center button with chevron ring
- **Faction Power Effects** - Unique cinematic animations for each faction:
  - **Tau'ri**: Fiery explosions destroying units
  - **Goa'uld**: Sarcophagus lid animation with golden revival beams
  - **Lucian Alliance**: Green naquadah shockwave with scanline/EM glitch effect
  - **Jaffa**: Stealth Tel'tak ship delivery
  - **Asgard**: White light de-materialization/re-materialization transporter beams

---

## 📝 Changelog

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

#### New Audio Asset
- `assets/audio/chat_notification.ogg` – Chat message notification sound (optional, silent if missing)

See [Audio Assets](#audio-assets) section for full list of supported audio files.

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


## 🎮 How to Play

### Game Objective
**Win 2 out of 3 rounds** by having a higher total power than your opponent when both players pass.

### Game Flow

**1. Main Menu**
- **NEW GAME** - Start match with faction/leader selection
- **DECK BUILDING** - Customize decks for each faction
- **QUIT** - Exit game

**2. Faction & Leader Selection**
- Choose faction (each has unique playstyle)
- Select leader with special ability
- Review deck composition
- Start game

**3. Mulligan Phase (2-5 Cards)**
- Random coin flip determines who goes first
- LEFT CLICK to select 2-5 cards you want to redraw
- Click "CONFIRM MULLIGAN" button
- Must select at least 2 cards, maximum 5 cards
- AI automatically mulligans 2-4 cards

**4. Round Gameplay**
- Random player goes first (fair coin flip!)
- Each player starts with 10 cards
- Draw 2 cards at start of rounds 2 and 3
- Take turns playing one card at a time
- Pass when you want to stop (click DHD button!)
- Round ends when both players pass
- Player with highest power wins the round
- Press G or click Faction Power button (ONCE per game!)

**5. Victory & Rewards**
- First to win 2 rounds wins the game
- **Win any game** → Unlock 1 of 3 cards (faction-specific + Neutral)
- **Win 3 in a row** → Unlock alternate leader for that faction
- All progress saved automatically!

---

## 🎴 Factions & Leaders

### 5 Playable Factions

#### **Tau'ri** (Earth Forces) 🌎
*Human ingenuity and determination*
- **Style**: Balanced units, strong heroes
- **Leaders**: Col. O'Neill, Gen. Hammond, Dr. Carter, Dr. Jackson, Teal'c
- **Signature Twist**: Col. Jack O'Neill now summons a temporary 6-power clone at the start of every round—perfect disposable muscle that vaporizes after three of your turns.
- **Unlockable**: Jonas Quinn, Catherine Langford, Gen. Landry, Dr. McKay

#### **Goa'uld** (System Lords) 👑
*Ancient parasitic overlords*
- **Style**: Overwhelming numbers, powerful abilities
- **Leaders**: Apophis, Yu the Great, Sokar, Ba'al, Hathor
- **Apophis Ability**: If the enemy stacks 4+ ships in Siege, he beams one onto your board
- **Unlockable**: Ba'al (Clone), Cronus, Anubis, Kvasir

#### **Jaffa** (Free Jaffa Nation) ⚔️
*Warriors seeking freedom*
- **Style**: Tactical combat, unit synergy
- **Starter Leaders**: Teal'c, Bra'tac, Rak'nor
- **Unlockable**: Ka'lel, Gerak, Ishta, Rya'c (Teal'c's son)

#### **Lucian Alliance** (Pirates & Smugglers) 💀
*Cunning outlaws and mercenaries*
- **Leaders**: Netan, Anateo, Kiva, Vala Mal Doran, Vulkar
- **Unlockable**: Netan (Crime Lord), Anateo (Warlord)

#### **Asgard** (Ancient Allies) 👽
*Advanced technology and wisdom*
- **Leaders**: Thor, Freyr, Penegal, Aegir, Heimdall
- **Unlockable**: Thor (Supreme Commander), Hermiod, Loki

---

## ⚡ Faction Powers

**NEW in v0.6!** Each faction has a unique, **once-per-game** (not per-round!), cinematic ability called a **Faction Power** that doesn't consume your turn.

### 🌍 Tau'ri - "The Gate Shutdown"
**Effect:** Destroys the highest strength card on each of the opponent's rows.
**Visual:** Multiple fiery explosions on each row - white hot center → yellow → orange → red rings, followed by dark smoke debris particles.
**Strategy:** Surgical strike against opponent's strongest units. Best used when opponent has powerful cards spread across multiple rows. **Save for critical moment - only usable ONCE per game!**
**Activation:** Press **G** or click **ACTIVATE** button (Tab to select, SPACE to confirm)

### 🐍 Goa'uld - "Sarcophagus Revival"
**Effect:** Play two random non-Hero cards from your discard pile.
**Visual:** Golden energy stream radiating from the Goa'uld Leader card, sweeping over the discard pile. Two gold-tinged card sprites lift up and fly onto the battlefield.
**Strategy:** Massive card advantage and board recovery. Most effective when you have quality units in your discard pile. **Once per game - use wisely!**

### 🔫 Lucian Alliance - "Unstable Naquadah"
**Effect:** Deals 5 damage (strength reduction) to every non-Hero unit on the battlefield, friend or foe.
**Visual:** Sickly green pulse exploding outward from the center of the board with enhanced glowing particles and screen shake.
**Strategy:** Chaotic, high-risk ability. Use when you have fewer/weaker units than opponent, or when combined with Heroes (which are immune). **Once per game!**

### ⚔️ Jaffa Rebellion - "Rebel Alliance Aid"
**Effect:** Draw 3 cards from your deck, then discard 3 random cards to prevent hand overflow.
**Visual:** Enhanced Tel'tak ship with "JAFFA REINFORCEMENTS" title, stealth effects, and card delivery animation.
**Strategy:** Card cycling for tactical advantage. Useful when you need specific cards or want to refresh your hand options. **Once per game - timing is everything!**

### 👽 Asgard - "Holographic Row Swap"
**Effect:** Swap opponent's entire close combat row with their ranged row.
**Visual:** Blue transference lattice effect, screen vibrates, entire rows swap positions with holographic shimmer.
**Strategy:** Massive tactical disruption! Completely reverses opponent's row strategy. Units built for close combat are now in ranged (and vice versa). Destroys row-specific combos, horn placements, and weather strategies. **Once per game!**

### Power UI Features
- **Visibility:** Both players can see each other's power availability
- **Once Per Game:** Cannot be used again after activation - choose the perfect moment!
- **Visual Feedback:** Golden pulsing border when available, grey "USED" when exhausted
- **Hotkey:** Press **G** to activate directly, or **Tab** to select + **SPACE** to confirm
- **Location:** Bottom-right for player, top-right for opponent
- **Cinematic:** 2-second full-screen effect with faction-specific visuals

---


## 🃏 Card Abilities

### Core Abilities

#### **Legendary Commander** 🌟
- Immune to ALL special effects
- Not affected by weather/hazards
- Cannot be targeted by most abilities
- Cannot be boosted by Command Network

#### **Tactical Formation** 🤝
- Multiple copies multiply each other's power
- Example: 3 cards with power 4 = 4×3 = 12 each (36 total!)

#### **Gate Reinforcement** 📢
- Automatically plays all copies from hand and deck
- All must go to same row
- Variants:
  - **Life Force Drain** - Steals power from opponent
  - **System Lord's Curse** - Weakens opponent units

#### **Deep Cover Agent** 🕵️
- Played on opponent's side
- You draw 2 cards (or 3 with faction/leader bonus!)
- Great for card advantage

#### **Medical Evac** ⚕️
- **Interactive!** Choose any non-Legendary unit from discard pile
- Full UI overlay shows available cards
- Immediately played to board

#### **Ring Transport** 🛸
- **Interactive!** Choose any non-Legendary unit from either board
- Returns card to YOUR hand (even opponent's!)
- Full UI with colored borders (blue=yours, red=theirs)

#### **Naquadah Overload** 🔥
- Destroys highest power non-Legendary units on the board
- Affects both players if tied
- **Blue energy explosions appear ONLY on rows where cards are destroyed**
- **Merlin's Weapon** variant - Only hits opponent!

#### **Command Network** 📯
- Doubles power of all non-Legendary units in a row
- Choose which row when playing

#### **Inspiring Leadership** 💚
- Boosts adjacent units in same row by +1
- Green aura animation

#### **Deploy Clones** 🛡️
- Summons 2 Clone Warriors (2 power each)
- Asgard technology
- Blue portal animation

#### **Activate Combat Protocol** ⚔️
- Summons 1 Combat AI (5 power)
- Advanced systems activation

#### **Survival Instinct** 😤
- Gains +2 power when weather affects their row
- Thrives in harsh conditions!

#### **Genetic Enhancement** ⚗️
- Transforms weakest unit in EACH row → 8-power warrior
- Gold transformation animation

### Special Card Abilities

#### **Thor's Hammer** ⚡
- Removes ALL Goa'uld units from both boards (instant purge)
- Asgard anti-Goa'uld failsafe

#### **Zero Point Module (ZPM)** ⚡
- Doubles ALL your siege units' power for the rest of the round
- Ancient power source

#### **Communication Device** 📡
- Reveals opponent's hand for the rest of the round
- Ancient stones allow you to see through enemy eyes
- Intelligence gathering

#### **Merlin's Anti-Ori Weapon** ⚡
- One-sided Naquadah Overload
- Destroys ONLY opponent's strongest non-Hero units (yours are safe)
- Designed to destroy ascended beings

#### **Dakara Superweapon** 💥
- Stats: 12 power, Legendary Commander
- Immune to all effects (highest non-special power in game)
- Massive ancient superweapon

---

## 🏆 Progression System

## 🔮 Future Roadmap (Ideas)
- **Single-Player Campaign**: Story-driven runs for all four factions, blending comic-book style cutscenes, roguelite replayability, and branching scenarios.
- **Cinematic Comic Panels**: Hand-drawn panels and motion layouts between missions to deliver a gripping Stargate narrative.
- **Roguelite Progression**: Draft between battles, evolving decks, leader upgrades, and escalating anomalies to keep each run fresh.

### Card Unlocks ✅
- **Trigger**: Win any game
- **Reward**: Choose 1 of 3 random cards
- **Filter**: Only shows cards from your faction + Neutral
- **Total**: 20 unlockable cards (ALL abilities verified v3.9.4!)
- **Persistence**: Saved to `player_unlocks.json`
- **Usage**: Access via Deck Builder to customize decks
- **⚡ v3.9.4 Fixes**: ZPM now doubles total power (not base), Puddle Jumper Ring Transport works correctly, all animations verified

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
  - **Mercenary Tax**: If your deck contains more Neutral cards than Faction cards, your total score is reduced by 25% (power penalty).
- **Features**:
  - Add/remove cards from your unlocked collection
  - Select leader from unlocked leaders
  - Save custom decks per faction (auto-saves when done)
  - Reset to default anytime
- **Persistence**: Saved to `player_decks.json`

### Unlockable Content

#### **21 Unlockable Cards** (ALL VERIFIED v3.9.4 ✅)
1. **Ori Warship** (11) - Legendary Commander
2. **Atlantis City** (10) - Legendary + Inspiring Leadership
3. **Anubis Super Soldier** (7) - Survival Instinct
4. **Kull Warrior Elite** (8) - Legendary + Survival Instinct
5. **Asuran Aurora-class** (10) - Grant ZPM + Tactical Formation
6. **Destiny Ship** (15, LEGENDARY) - Legendary Commander
7. **Replicator Swarm** (4) - Tactical Formation *(v3.9.4: Fixed description)*
8. **Wraith Hive** (9) - Gate Reinforcement (summons all copies)
9. **Ancient Drone** (8) - Naquadah Overload (destroys LOWEST enemy unit)
10. **Tok'ra Operative** (4) - Deep Cover Agent (draws 2-3 cards)
11. **Puddle Jumper** (5) - Ring Transport *(v3.9.4: Fixed for unit cards!)*
12. **Prometheus BC-303** (8) - Draw 1 when played
13. **Asgard Mothership** (10) - Draw 2 when played
14. **Thor's Hammer** (Special) - Remove all Goa'uld units
15. **Zero Point Module** (Special) - Double all siege units *(v3.9.4: Now preserves bonuses!)*
16. **Merlin's Weapon** (Special) - One-sided Naquadah Overload (opponent only)
17. **Dakara Superweapon** (12) - Legendary Commander
18. **Replicator Carter** (7) - Survival Instinct
19. **Communication Device** (Special) - Reveal opponent's hand
20. **Sodan Warrior** (6) - Look at opponent's hand (reveal animation added!)
21. **Grant ZPM** - Adds a ZPM card to hand (Asuran Aurora-class)

#### **20 Unlockable Leaders**

**Tau'ri:**
- Jonas Quinn - See any cards drawn by opponent (not starting hand)
- Catherine Langford - Ancient Knowledge: Look at top 3 cards, play one immediately
- Gen. Landry - +1 power to units each round they survive
- Dr. McKay - Draw 2 cards when you pass

**Goa'uld:**
- Ba'al (Clone) - Clone highest power unit
- Cronus - Units get +1/+2/+3 per round
- Anubis - Auto-scorch rounds 2 & 3
- Kvasir - First weather affects opponent only

**Jaffa:**
- Ka'lel - First 3 units each round get +2 power
- Gerak - Draw 1 card for every 2 units played
- Ishta - Gate Reinforcement units get +2 power
- Rya'c - Hope for Tomorrow: Draw 2 extra cards at start of round 3

**Lucian:**
- Netan - Gain 1 extra card each round
- Anateo - Free Medical Evac per round
- Vala - Look at 3 cards, keep 1
- Kiva - Play 2 cards on first turn

**Asgard:**
- Thor (Supreme) - Move any unit once per round
- Hermiod - Weather only affects opponent
- Loki - Steal 1 power from opponent's strongest
- Aegir - Legendary Commanders get +2 power



#### **35/35 Leader Abilities Working** (100% Complete!)
- ✅ Gen. Landry - "Homeworld Command": +1 to most populated row
- ✅ Ba'al - "System Lord's Cunning": Resurrect unit from discard
- ✅ Jonas Quinn - "Eidetic Memory": Copy opponent's drawn card
- ✅ Vala Mal Doran - "Thief's Luck": Steal card at round 2
- ✅ Kiva - "Brutal Tactics": First unit +4 power
- ✅ Thor Supreme Commander - "Fleet Command": Motherships +3
- ✅ Aegir - "Asgard Archives": Draw 1 card when playing siege units
- ✅ All other leader abilities fully functional!

#### **20/20 Card Abilities Working**
- Draw abilities (Prometheus, Mothership, Operative)
- Special destruction (Thor's Hammer removes Goa'uld)
- Power doubling (ZPM doubles siege)
- One-sided scorch (Merlin's Weapon)
- Hand reveal (Communication Device, Sodan) - 30s timer
- All core mechanics (Gate Reinforcement, Tactical Formation, etc.)

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



## 🛠️ Content Manager (Developer Tool)


### Features

| Option | Description |
|--------|-------------|
| **1. Add Card** | Interactive wizard to add a new card with automatic file updates |
| **2. Add Leader** | Create new leader with registry, colors, and portrait generation |
| **3. Add Faction** | Complete faction creation (colors, powers, leaders, starter cards) |
| **4. Ability Manager** | Add/edit card abilities, leader abilities, or faction powers |
| **5. Placeholders** | Generate missing card images and leader portraits |
| **6. Regenerate Docs** | Rebuild card_catalog.json, leader_catalog.json, rules_menu_spec.md |
| **7. Asset Checker** | Find missing images, orphaned assets, size validation |
| **8. Balance Analyzer** | Power distribution, ability frequency, faction balance stats |
| **9. Save Manager** | Backup/restore player_unlocks.json, player_decks.json, player_stats.json |
| **10. Deck Import/Export** | Share decks via JSON or text format |
| **11. Batch Import** | Import multiple cards/leaders from a JSON file |

### Safety Features

The Content Manager includes robust safety features to prevent breaking the game:

1. **Timestamped Backups** - All files are backed up to `backup/YYYY-MM-DD_HHMMSS/` before modification
2. **Step-by-Step Approval** - You see exact code and confirm each file change
3. **Syntax Validation** - Python files are compiled and import-tested after changes
4. **Automatic Rollback** - Any error triggers immediate restore from backup
5. **Session Logging** - All changes logged to `scripts/content_manager.log`

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

## 💡 Quick Reference

### Mouse Controls
| Action | Control |
|--------|---------|
| Select Card | Left click in hand |
| Play Card | Left drag to row |
| Preview Card | Right click any card |
| Pass Turn | Click DHD button (glowing red center) |
| Activate Faction Power | Click Faction Power button |
| View Discard | Press D |
| Inspect Leader | Right click leader portrait |
| Drag Card (Deck Builder) | Left click + drag |
| Zoom Card (Deck Builder) | Right click |


### 📋 Planned
- Tournament mode (best-of-3)
- Achievement system
- More factions (Wraith, Ori, Atlantis)
- Custom card creation tools
- AI-generated content (card art, abilities, flavor text)
- Internet matchmaking (beyond LAN/VPN)


## 📝 License & Credits

### Game Design
- **Gwent mechanics** - Original by CD Projekt Red
- **Stargate SG-1 theme** - Adaptation by fan project
- **This project** - Educational fan project, not for profit

### Assets
- Placeholder art generated via pygame
- Color-coded by faction
- Custom particle systems
- Future: Replace with commissioned art or community art

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

### Development
- Built with **Python 3.8+** and **Pygame CE 2.5.6+**
- Inspired by The Witcher 3: Wild Hunt's Gwent
- Animation system designed for extensibility
- Active development

### Legal
**This is a non-commercial fan project created purely for educational purposes and out of love for two incredible franchises.**

- **Gwent** is a trademark of CD Projekt Red - creators of The Witcher series and one of the best card games ever made
- **Stargate SG-1** is owned by MGM - the legendary sci-fi franchise that inspired this tribute
- This project is **NOT affiliated with or endorsed by** CD Projekt Red, MGM, or any related companies
- **No commercial use** - this is free, open-source, and will always remain so
- All trademarks, characters, and intellectual property belong to their respective owners
- This is fan service from fans who love both universes and wanted to combine them

*"You know, you blow up one sun and suddenly everyone expects you to walk on water."* - Col. Samantha Carter

### Special Thanks
- CD Projekt Red for Gwent game design
- MGM for Stargate SG-1 universe
- [101 Soundboards - Stargate SG-1 Soundboard](https://www.101soundboards.com/boards/33269-stargate-sg1-soundboard) for character voice clips
- Pygame CE community for documentation
- Contributors and playtesters


## 🤝 Contributing

Suggestions and feedback welcome!

### Want to Help?
- **Card Designs** - Create new cards for factions
- **Visual Effects** - Design custom animations
- **AI Improvements** - Enhance decision-making
- **Documentation** - Improve guides
- **Bug Reports** - Report issues



> Stargwent is intentionally modular: every card, leader, soundtrack, and UI element lives in plain Python and editable assets so anyone can reskin the experience into their own fantasy Gwent variant—Lord of the Rings, Dragon Ball, or whatever universe you want to explore. Dive into the codebase, swap art/audio JSON entries, and the engine adapts.
