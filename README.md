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
![Version](https://img.shields.io/badge/version-2.9-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Pygame CE](https://img.shields.io/badge/pygame--ce-2.5.6+-red)
![Resolution](https://img.shields.io/badge/resolution-4K%20(3840x2160)-purple)
![Status](https://img.shields.io/badge/status-Complete-brightgreen)

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
- [📝 License & Credits](#-license--credits)

---

### ✨ Key Features

### 🎮 Complete Card Game Experience
- **100% Fully Implemented** - All mechanics + Powers + Animations + Persistence + LAN Multiplayer!
- **35 Unique Leaders** (15 base + 20 unlockable) with special abilities
- **⚡ NEW v2.9: LAN MULTIPLAYER OVERHAUL** - Fixed game loop, added all animations for both players, robust disconnect handling!
- **⚡ NEW v2.9: TAILSCALE SUPPORT** - Smart IP detection prioritizes Tailscale VPN addresses for easy remote play!
- **⚡ NEW v2.8: LEGENDARY COMMANDER VOICE SNIPPETS** - Every legendary commander plays a character voice clip when deployed!
- **⚡ NEW v2.7: ALLIANCE COMBO TRACKING** - Alliance activations now show in history viewer with full visibility!
- **⚡ NEW v2.7: BALANCE CONFIG INTEGRATION** - All balance values now use centralized config for easy tuning!
- **⚡ NEW v2.7: 7 NEW LEADER ABILITIES** - Landry, Ba'al, Jonas Quinn, Vala, Kiva, Thor Commander, Aegir all implemented!
- **⚡ NEW v2.7: CRITICAL BUG FIXES** - Fixed Tactical Formation bonus stacking, Rya'c ability, and Asgard Beam artifact!
- **⚡ NEW v2.5: MASTER VOLUME SLIDER** - Interactive sound control with real-time adjustment, persistent settings, and beautiful gradient UI!
- **⚡ NEW v2.5: ENHANCED HISTORY PANEL** - Comprehensive event tracking: round results, leader abilities, weather, scorch, card draws, and more!
- **⚡ NEW v2.5: LAN WAITING LOBBY** - Ready system with live chat before deck selection!
- **⚡ NEW v2.2: LAN MULTIPLAYER** - Full 2-player networked gameplay with chat!
- **218 Cards** across 5 factions + Neutral cards
- **20+ Stargate-Themed Abilities** - Every ability matches the universe lore
- **25+ Hero Animations** - Unique entry effects for legendary commanders
- **⚡ NEW v1.9: Universal Leader Matchups** - One cinematic Stargate template replaces thousands of PNGs while preserving collision, Event Horizon effects, and lore quotes.
- **⚡ NEW v1.9: Retro Neon Nameplates** - Leader names now render in a retro cyberpunk font with faction-colored glow + scanlines for every matchup.
- **⚡ NEW v1.9: Seamless Fullscreen** - Toggle with F11/Alt+Enter or launch via `--fullscreen`; mode persists from menus through combat.
- **⚡ NEW v1.9: RULE MENU COMPENDIUM** - In-game `RULE MENU` button that opens the fully formatted rulebook generated from live card data.
- **Interactive Abilities** - Medical Evac and Ring Transport with full UI
- **DHD Pass Button** - Authentic Stargate Dial Home Device with glowing animation
- **⚡ NEW v1.7: WITCHER 3 GWENT LAYOUT** - Complete visual restructure matching authentic Gwent board design with clear separation, proper lane spacing, and fixed hand positioning!
- **⚡ NEW v1.6: FULLSCREEN UI FIX** - All bottom UI elements (Pass button, Faction Power) now properly visible in fullscreen mode with safe margins!
- **⚡ NEW v1.6: ROUND WINNER ANNOUNCEMENT** - Beautiful scoreboard overlay shows who won each round with blue highlights for victories before transitioning to next round!
- **⚡ NEW v1.6: IMPROVED HAND LAYOUT** - Hand area dynamically reserves 25% of screen height to prevent card cutoff in fullscreen!
- **⚡ NEW v1.5: APOPHIS WEATHER DECREE** - Once per game Apophis unleashes a random battlefield hazard that blankets both sides and honors weather immunities.
- **⚡ NEW v1.5: WEATHER & HORN PANELS** - Left-side slots display active weather cards and Commander Horns while doubling as drag-and-drop targets.
- **⚡ NEW v1.5: LEGENDARY LIGHTNING** - Every Legendary Commander arrival now gets a one-shot lightning outline (player + AI).
- **⚡ NEW v1.4: APOPHIS RAID** - If the opponent piles 4+ siege ships, Apophis teleports one to your board once per round.
- **⚡ NEW v1.4: REFINED DISCARD PANEL** - Dedicated UI panel with safe spacing replaces the old D-key shortcut.
- **⚡ NEW v1.2: GOA'ULD RING TRANSPORTATION** - Return close combat unit to hand EVERY ROUND!
- **⚡ NEW v1.2: 3-PHASE RING ANIMATION** - Golden rings descend → activate → ascend with card!
- **⚡ NEW v1.2: CLOSE COMBAT ONLY** - Rings can only retrieve close range fighters (once per round)!
- **⚡ NEW v1.3: TARGETED WEATHER DEPLOYMENT** - Drag weather cards directly onto opponent lanes (specials still go anywhere)!
- **⚡ NEW v1.3: EMP & NEBULA VFX** - Electromagnetic Pulse gets pulsing plasma motes; Nebula Fields add drifting pink clouds.
- **⚡ NEW v1.1.1: VISUAL DROP ZONES** - Blue highlights show all valid targets when dragging weather cards!
- **⚡ NEW v1.1: FLUID CARD FEEL** - Smooth dragging with easing, hover scale effects, enhanced shadows!
- **⚡ NEW v1.1: ANIMATED AI TURNS** - 4-phase AI animations: thinking particles → card selection → playing → resolving!
- **⚡ NEW v1.1: VISUAL FEEDBACK** - Cards feel weighted and responsive, every action is readable at 60 FPS!
- **⚡ NEW v1.0: UI OVERHAUL** - Streamlined controls: Right-click to preview cards, left-click drag & drop, removed keyboard shortcuts!
- **⚡ NEW v1.0: LEADER ABILITIES FIXED** - All leaders working correctly: Vulkar, Lord Yu, Rak'nor, Freyr verified!
- **⚡ DEV UPDATE: WEATHER BALANCE & SMARTER AI** - Persistent ability buffs, symmetrical weather shields, and retuned AI decision making.
- **⚡ NEW v1.0: FACTION POWERS RENAMED** - IrisPower → FactionPower (Tau'ri IrisDefense kept separate)!
- **⚡ NEW v1.0: MATCHUP BACKGROUNDS** - PNG backgrounds load for each leader combination!
- **⚡ NEW v0.9: ESC Pause Menu** - Pause anytime with Resume/Main Menu/Quit options
- **⚡ NEW v0.9: Round 3 Asteroids** - Animated asteroid field appears in final round!
- **⚡ NEW v0.9: Enhanced Jaffa Animation** - Tel'tak ship delivers 3 cards with title and effects
- **⚡ NEW v0.9: Minimum Deck Size** - Must have at least 20 cards to start a game!
- **⚡ NEW v0.9: Card Back System** - Opponent's hand shows card backs until revealed
- **⚡ NEW v0.9: Leader Backgrounds** - Each leader has unique background art during selection
- **⚡ v0.8.1: Code Cleanup** - Removed 100+ lines of dead code for cleaner codebase!
- **⚡ v0.8.1: Verified Abilities** - All 20 unlockable card abilities confirmed working (100%)!
- **⚡ v0.8: Deck Persistence** - Your deck choices are saved between games!
- **⚡ v0.8: Win Streak System** - Track your wins and unlock leaders every 3 victories!
- **⚡ v0.8: Automatic Saving** - Leaders and deck configurations saved automatically!
- **⚡ v0.7: Mulligan System** - Redraw 2-5 cards at game start!
- **⚡ v0.7: Random First Player** - Fair coin flip determines who goes first!
- **⚡ v0.7: Enhanced UI** - Left-click drag, right-click zoom everywhere!
- **⚡ v0.6: 4K Support** - Full 3840×2160 native resolution!
- **⚡ v0.6: Enhanced Animations** - Stargate KAWOOSH, hyperspace transitions, faction-specific effects!
- **⚡ Faction Power System** - Once-per-game cinematic abilities with unique visuals!
- **🖱️ Intuitive Controls** - Left-click to drag, right-click to inspect!

### 💾 Persistent Progression
- **Automatic Deck Saving** - Your deck is saved every time you finish customizing
- **Per-Faction Customization** - Each faction remembers your leader and deck choices
- **Win Tracking** - Track your wins, losses, and win streaks
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
- **Score Animations** - Dramatic pop effects with deltas
- **Weather Effects** - Row-specific highlights plus custom particle fields
- **EMP Plasma Field** - Floating green motes when Electromagnetic Pulse is active
- **Nebula Clouds** - Layered pink fog drifting through affected lanes
- **Black Hole Animation** - When clearing weather effects
- **Particle Systems** - Fire explosions, energy bursts, faction-specific effects
- **DHD Button** - Glowing red center button with chevron ring
- **Faction Power Effects** - Unique cinematic animations for each faction:
  - **Tau'ri**: Fiery explosions destroying units
  - **Goa'uld**: Golden sarcophagus revival beams
  - **Lucian Alliance**: Green naquadah shockwave
  - **Jaffa**: Stealth Tel'tak ship delivery
  - **Asgard**: Blue holographic lattice swaps

---

## 📝 Changelog

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
- ✅ **Connection Robustness** – Improved network reliability:
  - 10-second join timeout (was infinite)
  - 1-second recv timeout prevents hangs
  - 5-second keepalive heartbeat
  - 30-second connection timeout detection
  - TCP keepalive at OS level
- ✅ **Disconnect Detection** – Graceful handling of connection loss:
  - "CONNECTION LOST" overlay with red text
  - Automatic detection via keepalive failures
  - Clean return to main menu
  - Works in both lobby and game
- ✅ **Network Sync for Actions** – Faction power usage now syncs over network

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
- ✅ **Persistent Fullscreen** – Toggling fullscreen via F11/Alt+Enter (or launching with `python main.py --fullscreen` / `STARGWENT_FULLSCREEN=1`) keeps the entire experience in the chosen mode—from menus, to deck builder, to battle.
- ✅ **Card Reload Safety** – Switching display modes re-renders the board and reloads card assets so everything stays crisp in both windowed and fullscreen sessions.
- ✅ **Leader Background Alias Fix** – Master Bra'tac now reuses `leader_bg_jaffa_bratac.png`, preventing mismatched filenames and keeping the deck builder happy.

### Version 1.8 (September 2025)
**Preparations for Command Horn & HUD Overhaul**

- ✅ **Documentation Refresh** – README bumped to v1.8 to track the upcoming board/HUD rebuild work.
- ✅ **Spec Alignment** – Codex plan captured for the new percentage-based layout, accordion hands, right-HUD history column, and AI faction-power parity; implementation will land in the next tagged build.
- ℹ️ **Gameplay Code** – Currently identical to v1.7 so existing saves, decks, and ESC pause behavior remain untouched while we stage the next wave of UI fixes.

---

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

#### Layout Specifications
- ✅ **ROW_HEIGHT**: 9.5% screen height (perfectly fits cards with breathing room)
- ✅ **ROW_GAP**: 1.2% screen height (clean spacing between lanes)
- ✅ **DIVIDER_HEIGHT**: 5% screen height (prominent weather separator)
- ✅ **TOP_MARGIN**: 7% + card height + 2% (space for opponent hand)
- ✅ **HAND_Y_OFFSET**: 18% screen height (generous player hand area)
- ✅ **Opponent Rows**: Start after opponent hand with proper margin
- ✅ **Player Rows**: Start after weather separator with clean gaps

#### UI Improvements
- ✅ **Command Bar Positioning** - Faction Power and Pass button form right-side control zone
- ✅ **Player Faction Power** - Left of Pass button at `x=SCREEN_WIDTH-780`, `y=COMMAND_BAR_Y`
- ✅ **AI Faction Power** - Top-left at `x=140`, `y=TOP_MARGIN+10`
- ✅ **Pass Button (DHD)** - Bottom-right with safe margins (already positioned correctly)
- ✅ **Leader Portraits** - Player bottom-left, AI top-left (unchanged)

#### Visual Polish
- ✅ **Active Player Glow** - Subtle blue glow (alpha 30) on active player's lanes
- ✅ **Inactive Lane Darkening** - Vignette effect when player has passed
- ✅ **Weather Separator Visual** - Semi-transparent dark bar with subtle borders
- ✅ **Score Positioning** - Next to leader portraits with proper alignment

---

### Version 1.6 (September 2025)
**Fullscreen Polish & Round Winner Announcements**

#### UI Improvements
- ✅ **Fullscreen Bottom UI Fix** - Pass button, Faction Power UI, and all bottom elements now stay properly visible in fullscreen mode
- ✅ **Safe Margin System** - Implemented 3% bottom margin and 2% right margin to prevent UI cutoff
- ✅ **Dynamic Hand Area** - Hand area now reserves minimum 25% of screen height (250px minimum) to prevent card cropping
- ✅ **Improved Button Positioning** - DHD Pass button and Mulligan button repositioned with increased safe spacing

#### Round Winner System
- ✅ **Cinematic Round Winner Overlay** - Beautiful 3-second announcement showing who won each round
- ✅ **Detailed Scoreboard** - Displays all 3 rounds with:
  - **Blue highlights (100, 150, 255)** for won rounds
  - **Light grey (150, 150, 150)** for lost/draw rounds  
  - **Dark grey (80, 80, 80)** for future rounds
  - Total rounds won for each player
- ✅ **Round-by-Round Tracking** - Shows completed round number (e.g., "YOU WIN ROUND 2!")
- ✅ **Skip Option** - Press SPACE to continue immediately
- ✅ **Perfect Timing** - Announcement appears BEFORE hyperspace transition to next round

#### Technical Improvements
- ✅ **Scale Factor Adjustments** - All UI elements properly scale with fullscreen resolution changes
- ✅ **F11 Fullscreen Toggle** - Recalculates all margins when switching between windowed/fullscreen
- ✅ **Faction Power UI Positioning** - Moved up with safe margin calculation to stay visible
- ✅ **Hand Y Offset Calculation** - Improved formula ensures cards never get cut off at bottom

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

```bash
# 1. Navigate to game directory
cd stargwent

# 2. Create virtual environment
python -m venv venv

# 3. Activate venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Generate placeholder assets
python scripts/create_placeholders.py

# 6. Run the game!
python main.py

# Optional: start directly in fullscreen (persists for the whole session)
python main.py --fullscreen

# 7. Update pygame-ce
pip install --upgrade pygame-ce

Set `STARGWENT_FULLSCREEN=1` before running `python main.py` if you prefer forcing fullscreen without passing the CLI flag each time.

### First Launch
1. **Main Menu** - Select "NEW GAME"
2. **Select Faction** - Choose Tau'ri, Goa'uld, Jaffa, Lucian, or Asgard
3. **Select Leader** - Pick leader with unique ability
4. **Play!** - Start your first match

### Rule Menu & Docs
- **In-game reference:** From the Main Menu choose **RULE MENU** to browse the animated handbook (Basic Rules, Card Glossary, Lore, etc.) without leaving the game.
- **Regenerate the guide:** After editing cards, leaders, or abilities run `python scripts/generate_rules_spec.py` to rebuild `docs/rules_menu_spec.md`, which the viewer loads at runtime.

---

## 🎨 Animation & Visual Polish (v1.1)

### Fluid Card Interactions ✨
**Cards feel weighted and responsive!**

- **Smooth Dragging** - Cards follow mouse with easing (25% lerp factor), creating natural momentum instead of instant snap
- **Hover Scaling** - Cards in hand gently enlarge 8% when hovered with smooth interpolation (15% speed)
- **Dynamic Shadows** - Depth shadows intensify on hover (4px) and selection (6px) for physical card feel
- **Weighted Release** - Cards settle naturally when released, not teleported
- **Frame-Rate Independent** - All animations use delta time (dt) for consistent speed at any FPS (30-144Hz)

### AI Turn Animations 🤖
**No more instant AI skips! Every action is visually clear and cinematic:**

#### Phase 1: Thinking (1.0 second)
- **Text**: "AI is thinking..."
- **Effect**: 30 pulsing blue particles drift and bounce near top of screen
- **Formula**: `alpha = life * (128 + 127 * sin(pulse))`
- **Particles**: Continuously respawn for organic, living feel

#### Phase 2: Selecting (0.6 seconds)
- **Text**: "AI selects card..."
- **Effect**: Chosen card in opponent's hand gets pulsing glow highlight
- **Glow**: Expands/contracts with sine wave (80-160 alpha oscillation)
- **Visual**: Player can see which card AI chose before it's played

#### Phase 3: Playing (0.8 seconds)
- **Text**: "AI plays card..."
- **Effect**: Card travels from hand to board with ease-out cubic motion
- **Trigger**: Stargate activation effect at target row
- **Progress**: Smooth interpolation over 800ms

#### Phase 4: Resolving (0.4 seconds)
- **Text**: "Resolving..."
- **Effect**: Pulsing text shows card abilities activating
- **Scores**: Update with animated pop effects showing deltas
- **Turn End**: Smooth transition to player's turn

**Total AI turn duration: ~2.8 seconds** (readable, never rushed, maintains 60 FPS)

### Technical Improvements
- **No Blocking Waits** - Removed `pygame.time.wait()` calls that froze the screen
- **Async Animation Flow** - State machine drives AI actions frame-by-frame
- **Easing Functions** - `ease_out_cubic` for natural motion curves
- **Particle Systems** - Efficient spawning/despawning with life tracking
- **Z-Order Rendering** - Animations layer correctly (hand → board → AI overlay)

### Performance Metrics
- **CPU Impact**: ~1-2% increase for particle systems
- **GPU Impact**: Negligible (smoothscale cached)
- **Frame Rate**: Locked 60 FPS maintained throughout
- **Memory**: ~2KB for 50 active particles

---

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
- Press SPACEBAR to use Faction Power (ONCE per game!)

**5. Victory & Rewards**
- First to win 2 rounds wins the game
- **Win any game** → Unlock 1 of 3 cards (faction-specific + Neutral)
- **Win 3 in a row** → Unlock alternate leader for that faction
- All progress saved automatically!

### Card Types

#### Unit Cards
- **Close Combat** (Red) - Front-line melee fighters
- **Ranged** (Blue) - Archers and ranged attackers
- **Siege** (Green) - Heavy artillery and starships
- **Agile** (Purple) - Can be placed in Close or Ranged

#### Special Cards
- One-time effects that don't stay on board
- Includes Command Network, Naquadah Overload, Ring Transport

#### Weather Cards
- Target a specific opponent row (Close/Ranged/Siege) and leave your side untouched
- Reduces non-Legendary Commander units in that lane to 1 power (Survival Instinct units gain +2)
- **Ice Planet**, **Nebula**, **Asteroid Storm**, **Electromagnetic Pulse** (glowing green plasma)
- Clear any hazard with **Wormhole Stabilization** (cinematic black hole collapse)

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
**Activation:** Press **SPACEBAR** or click **ACTIVATE** button

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
- **Hotkey:** Press **SPACEBAR** to activate (when available)
- **Location:** Bottom-right for player, top-right for opponent
- **Cinematic:** 2-second full-screen effect with faction-specific visuals

---

## 🎬 Cinematic Leader Matchups

**NEW in v0.9!** Every game begins with an epic 5-second confrontation between leaders!

### Animation Sequence

**Phase 1 (0-1.5s): The Approach**
- Leader cards fly in from opposite sides of screen
- Smooth easing motion builds anticipation
- Stargate event horizon activates in background

**Phase 2 (1.5-2.5s): The Collision**
- Cards meet at center in explosive impact
- 8 lightning bolts radiate outward in all directions
- Energy burst with faction-colored effects
- Chevrons lock around the Stargate ring
- Screen shake effect
- Massive "VS" text appears

**Phase 3 (2.5-5.0s): The Declaration**
- Cards float to their battle positions
  - Player leader: Bottom left
  - Opponent leader: Top left
- Lore-based confrontation quote appears
- Historical context subtitle fades in
- Background continues animated event horizon

### Stargate Event Horizon Background

- **Animated Stargate Ring** with 9 chevrons
- **Rippling Water Effect** like the actual show
- **Vertical Distortion** mimicking energy flow
- **Floating Energy Particles** circling the gate
- **Chevron Lock Animation** during collision phase
- **Shimmering Blue/Cyan** authentic watery portal

### Lore-Based Quotes (40+ Specific Matchups)

Every leader combination has a unique quote based on Stargate SG-1 history:

**Examples:**
- **O'Neill vs Apophis:** "In the middle of my backswing?!"
- **Teal'c vs Apophis:** "I have pledged my life to destroy you."
- **Daniel vs Apophis:** "Your reign of terror ends today." (Sha're reference)
- **Vala vs Daniel:** "Oh, come on Daniel! Where's your sense of adventure?"
- **Thor vs Anubis:** "The Asgard will not allow your ascension."
- **Ba'al vs Yu:** "Age does not grant wisdom."
- **Bra'tac vs Apophis:** "This day of reckoning is long overdue, false god!"

**Dynamic System:**
- 40+ pre-defined specific matchups
- Auto-generates appropriate quotes for any combination
- Based on faction relationships (Tau'ri vs Goa'uld, Jaffa rebellion, etc.)
- Includes ALL 35 leaders (base + unlockable)

### Controls
- **SPACE or ESC:** Skip animation (if impatient)
- Otherwise: Enjoy the full 5-second cinematic!

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
- Removes ALL Goa'uld units from both boards
- Faction-specific destruction

#### **Zero Point Module (ZPM)** ⚡
- Doubles ALL your siege units' power
- Ancient power source

#### **Communication Device** 📡
- Reveals opponent's hand for rest of round
- Ancient stones allow you to see through enemy eyes
- Intelligence gathering

#### **Merlin's Anti-Ori Weapon** ⚡
- One-sided Naquadah Overload
- Destroys ONLY opponent's strongest units (yours are safe)
- Designed to destroy ascended beings

#### **Dakara Superweapon** 💥
- Stats: 12 power, Legendary Commander
- Immune to all effects (highest non-special power in game)
- Massive ancient superweapon

---

## 🏆 Progression System

### Card Unlocks ✅
- **Trigger**: Win any game
- **Reward**: Choose 1 of 3 random cards
- **Filter**: Only shows cards from your faction + Neutral
- **Total**: 20 unlockable cards
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
- **Features**:
  - Add/remove cards from your unlocked collection
  - Select leader from unlocked leaders
  - Save custom decks per faction (auto-saves when done)
  - Reset to default anytime
- **Persistence**: Saved to `player_decks.json`

### Unlockable Content

#### **20 Unlockable Cards**
1. **Ori Warship** (11) - Legendary Commander
2. **Atlantis City** (10) - Legendary + Inspiring Leadership
3. **Anubis Super Soldier** (7) - Survival Instinct
4. **Kull Warrior Elite** (8) - Legendary + Survival Instinct
5. **Asuran Warship** (10) - Deploy Clones + Tactical Formation
6. **Destiny Ship** (15, LEGENDARY) - Legendary Commander
7. **Replicator Swarm** (4) - Tactical Formation
8. **Wraith Hive** (9) - Gate Reinforcement (swarm tactics)
9. **Ancient Drone** (8) - Naquadah Overload
10. **Tok'ra Operative** (4) - Deep Cover Agent
11. **Puddle Jumper** (5) - Ring Transport
12. **Prometheus BC-303** (8) - Draw 1 when played
13. **Asgard Mothership** (10) - Draw 2 when played
14. **Thor's Hammer** (Special) - Remove all Goa'uld units
15. **Zero Point Module** (Special) - Double all siege units
16. **Merlin's Weapon** (Special) - One-sided Naquadah Overload (opponent only)
17. **Dakara Superweapon** (12) - Legendary Commander (highest normal power)
18. **Replicator Carter** (7) - Survival Instinct
19. **Communication Device** (Special) - Reveal opponent's hand
20. **Sodan Warrior** (6) - Reveal hand when played

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

---

## 🎨 Visual Features

### DHD Pass Button 🎮
**Authentic Stargate Dial Home Device!**
- Bronze metallic outer ring
- 7 symbol markers (chevrons) around edge
- Red glowing center button
- Pulsing animation when active
- Stargate activation burst on click
- Dark gray when inactive

### Background Effects (Always Active)
- Moving starfield with subtle twinkle
- Chevron glows on screen edges
- Blue energy waves across board
- Layers over static background

### In-Game Effects (Action-Based)
- **Score Animations** - Pop effects with deltas
- **Stargate Activation** - Blue portal when playing cards
- **Naquadah Overload** - Blue energy explosions with expanding shockwave rings (only on affected rows)
- **Weather Effects** - Animated hazards with row highlighting
- **EMP Plasma Field** - Floating green motes when Electromagnetic Pulse is active
- **Nebula Clouds** - Layered pink fog drifting through affected lanes
- **Black Hole** - Wormhole Stabilization animation
- **Particle Systems** - Fire, energy bursts
- **Glow Animations** - Pulsing highlights
- **Hero Animations** - 25+ unique entry effects
- **Ability Animations** - Visual feedback for special abilities

---

## ⌨️ Controls

### Deck Builder
- **LEFT CLICK + DRAG** - Drag cards between panels to add/remove from deck
- **RIGHT CLICK** - Inspect/zoom any card (full details)
- **Mouse Wheel** - Scroll through card collections
- **Arrow Keys / WASD** - Navigate menus
- **ENTER** - Confirm selections
- **ESC** - Back/Cancel

### In-Game Mouse Controls
- **LEFT CLICK cards** - Select cards in hand
- **LEFT CLICK + DRAG** - Drag card from hand to board row
- **RIGHT CLICK any card** - Preview/Zoom (hand, board, opponent, leaders)
- **LEFT CLICK row** - Place dragged card on board
- **LEFT CLICK DHD** - Pass turn (red glowing button!)
- **LEFT CLICK Faction Power** - Activate once-per-game faction ability
- **LEFT CLICK Iris Button** - Activate Iris Defense (Tau'ri only)
- **LEFT CLICK "Confirm Mulligan"** - Confirm 2-5 card redraw
- **Mouse Wheel** - Scroll discard pile viewer

### Deck Builder Controls
- **LEFT CLICK + DRAG** - Move cards between pool and deck
- **RIGHT CLICK** - Zoom/inspect any card
- **Mouse Wheel** - Scroll card pools
- **Card Type Tabs** - Filter by Units, Special, Weather, All

### In-Game Keyboard Hotkeys
- **F3** - Toggle debug overlay (shows all zone boundaries and alignments)
- **SPACEBAR** - Activate Faction Power OR preview selected card
- **D** - View discard pile (scroll with mouse wheel, ESC to close)
- **ESC** - Close overlays / Pause menu
- **F11 / Alt+Enter** - Toggle fullscreen (mode persists across menus/matchups; also selectable via `--fullscreen` or `STARGWENT_FULLSCREEN=1`)
- **R** - Restart (game over)
- **Arrow Keys / WASD** - Navigate menus
- **1/2/3** - Quick select rewards

### Pause Menu (ESC During Game)
- **Resume** - Continue playing
- **Main Menu** - Return to main menu (forfeit current game)
- **Quit** - Exit game entirely

### Card Inspection
- RIGHT CLICK any card (yours, opponent's, leaders, board) to zoom
- See full art, power, abilities, description
- Browse multiple cards with arrows/wheel
- RIGHT CLICK again or press TAB/ESC to close

---

## 📊 Implementation Status

### ✅ Fully Implemented (100%)

#### **NEW v1.0: UI & Leader Ability Fixes**
- **Right-Click Card Preview** - Preview any card (hand, board, opponent) with right-click
- **Streamlined Controls** - Removed manual ability hotkeys (V, B, T) - abilities auto-trigger
- **Leader Ability Fixes**:
  - **Vulkar** - Correctly draws 3 cards for Deep Cover Agents (verified working)
  - **Lord Yu** - Now reveals opponent's hand when you pass
  - **Rak'nor** - Can play 2 cards on first turn of each round
  - **Freyr** - Complete immunity to ALL weather effects (not just first)
- **Faction Powers Renamed** - IrisPower → FactionPower throughout codebase
- **Tau'ri Iris Defense** - Kept separate and working (click Iris button)
- **Unstable Naquadah Fixed** - Lucian faction power now properly damages units
- **Universal Leader Matchups** - Cinematic intro now renders from a single `universal_leader_matchup_bg.png` with faction-colored neon typography and dynamically scaled portraits.
- **Placeholder Generation** - Run `create_placeholders.py` to (re)create the universal template plus all cards/portraits (including Bra'tac alias cleanup).
- **Simplified Keyboard** - Only essential keys: D (discard), Space (preview/power), ESC (close/pause)

#### **NEW v0.9: Cinematic & Polish Updates**
- **Leader Matchup Animation** - 5-second cinematic confrontation with Stargate event horizon, lightning collision, and 40+ lore-based quotes for every leader combination
- **Pause Menu System** - ESC anytime to pause with Resume/Main Menu/Quit options
- **Round 3 Asteroids** - Animated asteroid field appears in background during final round
- **Enhanced Jaffa Animation** - "JAFFA REINFORCEMENTS" title with improved Tel'tak delivery effect
- **Minimum Deck Size** - Players must have at least 20 cards to start a game
- **Card Back System** - Opponent's hand displays card backs until revealed by abilities
- **Leader Selection Backgrounds** - Each of 35 leaders has unique background art during selection
- **Improved Jaffa Power** - Draw 3, discard 3 (prevents hand overflow issues)
- **Deck Builder Improvements** - Direct deck view access from deck building menu, auto-save functionality
- **F11 Fullscreen** - Works from main menu
- **Animation Polish** - Better visibility for faction powers, enhanced particle effects

#### **v0.8.1: Code Cleanup & Verification**
- **Dead Code Removed** - Eliminated 100+ lines of unused ZPM resource and mission systems
- **Ability Verification Complete** - All 20 unlockable card abilities confirmed working (100%)
- **Description Accuracy** - Updated card descriptions to match actual implementations
- **Streamlined Codebase** - Removed unused classes: ZPMResource, MissionObjective
- **Cleaner Game Logic** - Simplified Player initialization and round management

#### **v0.8: Deck Persistence & Progression**
- **Automatic Deck Saving** - Your deck is saved after every customization
- **Per-Faction Decks** - Each faction remembers your leader and card choices
- **Win/Loss Tracking** - Full statistics system with win streaks
- **Leader Unlocks** - Earn new leaders every 3 consecutive wins
- **Cross-Session Saves** - JSON-based persistence (`player_decks.json`, `player_unlocks.json`)
- **Seamless Integration** - Loads previous choices automatically on game start

#### **Visual & Animation System (v0.6-2.8)**
- **4K Native Support** - 3840×2160 resolution with perfect asset scaling
- **Stargate Opening** - Epic KAWOOSH vortex with outward particle burst
- **Hyperspace Transitions** - Star streak animations for rounds 2 & 3
- **Planet Emergence** - Round 3 planet appearance effect
- **Improved AI Pacing** - 1.2s think time + 0.8s pause after moves
- **Discard Pile Viewer** - Press D to view all discarded cards
- **Left-Click Drag & Right-Click Zoom** - Intuitive card interaction everywhere

#### **Game Flow & Balance (v0.7)**
- **Random First Player** - Fair coin flip at game start
- **Mulligan System** - 2-5 card redraw with enforced limits
- **AI Strategic Power Usage** - AI uses faction powers in rounds 1-2 based on board state
- **Faction Power Balance** - All powers are once-per-game (not per-round)

#### **Faction Power System**
- 5 unique faction powers with cinematic effects
- Full UI with availability indicators
- Once-per-game activation system
- Keyboard (SPACEBAR) and mouse activation
- Unique visual effects for each faction:
  - Tau'ri: Fire explosions with smoke debris
  - Goa'uld: Golden sarcophagus revival beam
  - Lucian: Green naquadah shockwave
  - Jaffa: Stealth Tel'tak delivery
  - Asgard: Blue holographic lattice swap

#### **35/35 Leader Abilities Working** (100% Complete!)
- ✅ Gen. Landry - "Homeworld Command": +1 to most populated row
- ✅ Ba'al - "System Lord's Cunning": Resurrect unit from discard
- ✅ Jonas Quinn - "Eidetic Memory": Copy opponent's drawn card
- ✅ Vala Mal Doran - "Thief's Luck": Steal card at round 2
- ✅ Kiva - "Brutal Tactics": First unit +4 power
- ✅ Thor Supreme Commander - "Fleet Command": Motherships +3
- ✅ Aegir - "Asgard Archives": Draw on siege play
- ✅ All other leader abilities fully functional!

#### **20/20 Card Abilities Working**
- Draw abilities (Prometheus, Mothership, Operative)
- Special destruction (Thor's Hammer removes Goa'uld)
- Power doubling (ZPM doubles siege)
- One-sided scorch (Merlin's Weapon)
- Hand reveal (Communication Device, Sodan)
- All core mechanics (Gate Reinforcement, Tactical Formation, etc.)

#### **Complete Systems**
- Deck persistence and auto-save
- Win streak tracking and leader unlocks
- Faction-specific unlock filtering
- Leader & card progression (JSON)
- DHD pass button with animations
- Round tracking & counters
- Hand reveal system
- Medical Evac selection UI
- Ring Transport selection UI
- Deck builder with drag-and-drop customization
- Win streak tracking
- Score animations
- Weather effects with highlighting
- Black hole animation
- Right-click card inspection
- Discard pile viewer with scrolling

### ⏳ Polish & Enhancement (1%)

#### **Future Enhancements**
- Sound effects & music (Sonic Pi integration ready)
- Advanced AI difficulty settings
- More faction-specific animations
- Tournament mode
- LAN reconnection support

**All core gameplay 100% complete! Ready for extensive playtesting and content expansion!**

---

## 🏗️ Project Structure

### Python Files (21 total)

#### **Core Game Files**
- `main.py` (2215 lines) - Main game loop, UI, event handling, Power system integration
- `game.py` (849 lines) - Game logic, rules, Player class
- `cards.py` (322 lines) - Card database and definitions
- `ai_opponent.py` (374 lines) - AI controller and strategy

#### **UI & Menu Files**
- `main_menu.py` (830 lines) - Main menu, faction selection, Stargate opening animation
- `leader_matchup.py` (450+ lines) - Cinematic leader confrontation system with 40+ lore quotes
- `deck_builder.py` (1025 lines) - Deck customization interface with drag-and-drop
- `unlocks.py` (791 lines) - Progression system
- `rules_menu.py` (1400+ lines) - **NEW v1.7!** Interactive rule compendium with search

#### **Persistence & Data Files**
- `deck_persistence.py` (260 lines) - Automatic deck/progress saving system
- `game_settings.py` (110 lines) - **NEW v2.5!** Sound settings with volume control
- `content_registry.py` (220 lines) - **NEW v2.2!** Centralized leader/card registry

#### **Visual & Effects Files**
- `animations.py` (1974 lines) - All animation and particle systems
- `power.py` (600 lines) - Faction Power system with cinematic effects

#### **LAN Multiplayer Files** - **NEW v2.2-2.5!**
- `lan_session.py` (84 lines) - TCP socket wrapper with JSON framing
- `lan_protocol.py` (82 lines) - Message types and protocol definitions
- `lan_game.py` (156 lines) - LAN setup flow and game initialization
- `lan_opponent.py` (296 lines) - NetworkController and NetworkPlayerProxy
- `lan_menu.py` (170 lines) - Host/Join connection interface
- `lan_lobby.py` (195 lines) - **NEW v2.5!** Waiting room with ready system
- `lan_chat.py` (66 lines) - Chat panel for multiplayer
- `lan_context.py` (25 lines) - Data structures for LAN state

#### **Utility Files**
- `create_placeholders.py` (530 lines) - Asset generation script (4K support)

### Asset Structure
```
assets/
├── audio/                           # Music and sound effects
│   ├── main_menu_music.ogg          # Main menu theme
│   ├── battle_round1.ogg            # Round 1 battle music
│   ├── battle_round2.ogg            # Round 2 music (more intense)
│   ├── battle_round3.ogg            # Round 3 music (most intense)
│   ├── tauri_theme.ogg              # Tau'ri faction preview (hover in menu)
│   ├── goauld_theme.ogg             # Goa'uld faction preview
│   ├── jaffa_theme.ogg              # Jaffa faction preview
│   ├── lucian_theme.ogg             # Lucian Alliance faction preview
│   ├── asgard_theme.ogg             # Asgard faction preview
│   ├── close.ogg                    # Close combat unit play sound
│   ├── ranged.ogg                   # Ranged unit play sound
│   ├── siege.ogg                    # Siege unit play sound
│   ├── ring.ogg                     # Ring Transport activation
│   ├── stargate_sequence.ogg        # Stargate opening SFX
│   └── commander_snippets/          # Voice clips for legendary commanders
│       ├── tauri_oneill.ogg         # "In the middle of my backswing!"
│       ├── tauri_hammond.ogg        # "SG-1, you have a go."
│       ├── jaffa_tealc.ogg          # "Indeed."
│       └── ... (27 total)           # One per legendary commander
├── board_background.png             # 4K main game board
├── menu_background.png              # 4K menu background
├── deck_building_background.png     # 4K deck builder background
├── card_back.png                    # Card back design (200x280)
├── [card_id].png                    # 218 card images (200x280)
├── [card_id]_leader.png             # 35 leader portraits
└── leader_bg_[faction]_[leader].png # 35 leader selection backgrounds

Save Files (auto-generated):
├── player_decks.json                # Custom deck configurations
├── player_unlocks.json              # Unlock progress and stats
└── game_settings.json               # Sound and game settings - NEW v2.5!
```

### 🎵 Complete Audio File Guide

All audio files are `.ogg` format (OGG Vorbis). Place them in `assets/audio/`.

---

#### Menu & Battle Music

| File | Location | When It Plays |
|------|----------|---------------|
| `main_menu_music.ogg` | `assets/audio/` | Main menu (loops infinitely) |
| `battle_round1.ogg` | `assets/audio/` | Round 1 battle (loops) |
| `battle_round2.ogg` | `assets/audio/` | Round 2 battle - more intense (loops) |
| `battle_round3.ogg` | `assets/audio/` | Round 3 battle - climactic finale (loops) |

---

#### Faction Preview Themes (Menu Hover)

Play when hovering over faction buttons in selection menu. Restart every 10 seconds while hovering.

| File | Location | Faction |
|------|----------|---------|
| `tauri_theme.ogg` | `assets/audio/` | Tau'ri |
| `goauld_theme.ogg` | `assets/audio/` | Goa'uld |
| `jaffa_theme.ogg` | `assets/audio/` | Jaffa Rebellion |
| `lucian_theme.ogg` | `assets/audio/` | Lucian Alliance |
| `asgard_theme.ogg` | `assets/audio/` | Asgard |

---

#### Unit Card Row Sounds

Play when a non-legendary unit card is placed on the board.

| File | Location | Row Type |
|------|----------|----------|
| `close.ogg` | `assets/audio/` | Close combat units |
| `ranged.ogg` | `assets/audio/` | Ranged units |
| `siege.ogg` | `assets/audio/` | Siege units |

---

#### Special Ability Sounds

| File | Location | When It Plays |
|------|----------|---------------|
| `ring.ogg` | `assets/audio/` | Ring Transport card used (Goa'uld) |
| `iris.ogg` | `assets/audio/` | Tau'ri Iris Defense OR Faction Power (The Gate Shutdown) |

---

#### Legendary Commander Voice Snippets (27 total)

Play when a legendary commander is deployed. Place all in `assets/audio/commander_snippets/`.

**Tau'ri (4):**
| File | Character |
|------|-----------|
| `tauri_oneill.ogg` | Col. Jack O'Neill |
| `tauri_hammond.ogg` | Gen. George Hammond |
| `tauri_jackson.ogg` | Dr. Daniel Jackson |
| `tauri_carter.ogg` | Dr. Samantha Carter |

**Goa'uld (5):**
| File | Character |
|------|-----------|
| `goauld_sokar.ogg` | Sokar |
| `goauld_yu.ogg` | Lord Yu |
| `goauld_hathor.ogg` | Hathor |
| `goauld_apophis.ogg` | Apophis |
| `goauld_isis.ogg` | Isis |

**Jaffa Rebellion (4):**
| File | Character |
|------|-----------|
| `jaffa_tealc.ogg` | Teal'c |
| `jaffa_bratac.ogg` | Bra'tac |
| `jaffa_raknor.ogg` | Rak'nor |
| `jaffa_master_bratac.ogg` | Master Bra'tac |

**Lucian Alliance (4):**
| File | Character |
|------|-----------|
| `lucian_vulkar.ogg` | Vulkar |
| `lucian_curtis.ogg` | Sg. Curtis |
| `lucian_sodan_master.ogg` | The Sodan Master |
| `lucian_baal_clone.ogg` | Ba'al Clone |

**Asgard (3):**
| File | Character |
|------|-----------|
| `asgard_freyr.ogg` | Freyr |
| `asgard_loki.ogg` | Loki |
| `asgard_heimdall.ogg` | Heimdall |

**Neutral (6):**
| File | Character |
|------|-----------|
| `neutral_ascended_daniel.ogg` | Ascended Daniel Jackson |
| `neutral_oma_desala.ogg` | Oma Desala |
| `neutral_mckay.ogg` | Dr. Rodney McKay |
| `neutral_teyla.ogg` | Teyla Emmagan |
| `neutral_ancient_drone.ogg` | Ancients Drone |
| `neutral_weir.ogg` | Dr. Elizabeth Weir |

---

#### Audio File Summary

**Total Files Needed: 41**
- Menu/Battle Music: 4
- Faction Themes: 5
- Row Sounds: 3
- Special Sounds: 2
- Commander Snippets: 26
- Stargate sequence: 1 (`stargate_sequence.ogg`)

All files are optional - missing files are silently skipped (no crashes).



### LAN Multiplayer (v2.2 - COMPLETE!)
- Choose **LAN MULTIPLAYER** in the main menu
- **Host**: Runs TCP listener on port 4765, displays local IP addresses, waits for opponent
- **Join**: Enter host's LAN IP to connect
- **Deck Selection**: Both players select faction, leader, and deck independently
- **Leader Matchup**: Full cinematic animation showing both leaders
- **Gameplay**: Complete networked game with:
  - All card plays synchronized in real-time
  - Pass turn synchronization
  - Faction power activation sync
  - NetworkController seamlessly replaces AI
- **Chat System**: Built-in chat replaces history panel during multiplayer - type to communicate!
- **Unlock Override**: All factions, leaders, and cards automatically unlocked in LAN mode (no grind)
- **Single-Player Unaffected**: Your progression system remains intact for solo games
- **Zero Dependencies**: Uses only Python's built-in `socket` module - no extra packages needed!

### Data Files (Auto-Generated)
```
player_decks.json         # Per-faction deck configurations (leader + cards)
player_unlocks.json       # Unlocked leaders/cards + win stats
```

**Example `player_decks.json`:**
```json
{
  "Tau'ri": {
    "leader": "tauri_oneill",
    "cards": ["tauri_sg1", "tauri_prometheus", ...]
  },
  "Goa'uld": {
    "leader": "goauld_apophis",
    "cards": []  // Empty = use default deck
  }
}
```

**Example `player_unlocks.json`:**
```json
{
  "unlocked_cards": ["tauri_mckay", "goauld_baal"],
  "unlocked_leaders": ["tauri_landry"],
  "consecutive_wins": 5,
  "total_wins": 12,
  "faction_wins": {"Tau'ri": 5, "Goa'uld": 7}
}
```

---

## 🔧 Technical Details

### Power Calculation Order
1. **Base Power** - Start with card's base
2. **Leader Abilities** - Apply power bonuses
3. **Weather Effects** - Reduce non-Legendary to 1
4. **Survival Instinct** - +2 if weather active
5. **Tactical Formation** - Multiply by copies
6. **Command Network** - Double all in row

### Example
- Card: Clone Warrior (4 power, Tactical Formation)
- 3 copies, Command Network active, no weather
- **Calculation**: 4 × 3 (formation) × 2 (horn) = 24 each
- **Total**: 72 power from 3 cards!

### Code Architecture

#### **Player Class Attributes**
```python
self.faction               # Faction name
self.leader                # Leader dict with ability
self.deck                  # List of Card objects
self.hand                  # Cards in hand
self.board                 # {row: [cards]}
self.discard_pile          # Discarded cards
self.current_round_number  # For round-based abilities
self.units_played_this_round  # For counters
self.hand_revealed         # For intel effects
```

#### **Card Class**
```python
self.name                  # Display name
self.faction               # Faction or "Neutral"
self.row                   # close/ranged/siege/agile/special/weather
self.power                 # Base power
self.ability               # Ability string (can have multiple)
self.displayed_power       # Calculated power (changes in game)
```

#### **Ability Hooks**
- `calculate_score()` - Power bonuses every turn
- `play_card()` - Per-card abilities trigger
- `end_round()` - Round start abilities
- `pass_turn()` - Pass-based abilities (McKay)
- `apply_special_effect()` - Special card logic

### Sound System Architecture

#### **Settings Persistence** (`game_settings.py`)
```python
# Global settings instance
from game_settings import get_settings

settings = get_settings()

# Volume ranges: 0.0 to 1.0 (0% to 100%)
master_volume = settings.get_master_volume()
music_volume = settings.get_music_volume()
sfx_volume = settings.get_sfx_volume()

# Effective volumes (master × specific)
effective_music = settings.get_effective_music_volume()
effective_sfx = settings.get_effective_sfx_volume()

# Set and auto-save
settings.set_master_volume(0.8)  # Saves to game_settings.json
settings.apply_volume()          # Apply to pygame.mixer
```

#### **Settings File** (`game_settings.json`)
```json
{
  "master_volume": 0.7,
  "music_volume": 0.7,
  "sfx_volume": 0.7
}
```

#### **Volume Application**
- **Menu Music**: `master × music` (default: 0.7 × 0.7 = 0.49)
- **Battle Music**: `master × music` (per faction theme)
- **SFX**: `master × sfx` (Stargate sequence, abilities)

#### **Sound Loading**
```python
# Music (streaming)
pygame.mixer.music.load(path)
pygame.mixer.music.set_volume(settings.get_effective_music_volume())
pygame.mixer.music.play()

# Sound effects (preloaded)
sound = pygame.mixer.Sound(path)
sound.set_volume(settings.get_effective_sfx_volume())
sound.play()
```

#### **Options Menu Slider**
- **Interactive Drag**: Smooth volume adjustment
- **Real-time Preview**: Hear changes immediately
- **Visual Feedback**: Blue gradient fill, percentage display
- **Persistent**: Auto-saves on change

### Code Quality & Verification

#### **Dead Code Removed (v0.8.1)**
The following unused systems were removed to streamline the codebase:

**Removed Classes:**
- `ZPMResource` - Unused resource spending system (~20 lines)
- `MissionObjective` - Unimplemented mission system (~60 lines)
- `create_random_objective()` - Mission generation function

**Removed Code:**
- ZPM configuration constants
- Mission reward logic
- Mission checking at round end
- Player attributes: `zpm_resource`, `current_mission`, `mission_bonus_cards`

**Result:** ~100+ lines of dead code removed, cleaner game logic

#### **Ability Implementation Verification (v0.8.1)**
All 20 unlockable card abilities verified and confirmed working:

✅ **17/20 Originally Implemented:**
- Draw abilities (Prometheus, Mothership)
- Combat abilities (Naquadah Overload, Tactical Formation)
- Defense abilities (Legendary Commander, Survival Instinct)
- Utility abilities (Ring Transport, Deep Cover Agent, Deploy Clones)
- Special abilities (Thor's Hammer, ZPM, Merlin's Weapon, Dakara)

✅ **3/20 Descriptions Updated to Match Implementation:**
- **Wraith Hive:** Changed from "Life Force Drain" → "Gate Reinforcement"
- **Replicator Carter:** Changed from "Copy opponent ability" → "Survival Instinct"
- **Communication Device:** Clarified as "Reveal opponent's hand" (was ambiguous)

**Status:** 100% of unlockable card abilities now verified and working correctly!

---

## 🔄 Recommended Code Consolidations

### Files That Could Be Merged

#### **Option 1: Merge stargate_mechanics.py into game.py**
**Why:** Both handle game mechanics
**Benefit:** Single source of truth for all game rules
**Consideration:** game.py would become ~1300 lines (manageable)

#### **Option 2: Merge ability_rename.py into tools/ folder**
**Why:** It's a one-time utility, not part of game
**Benefit:** Cleaner root directory
**Action:** Move to `tools/ability_rename.py` or delete if no longer needed

#### **Option 3: Merge stargate_opening.py into main_menu.py**
**Why:** Both are pre-game UI sequences
**Benefit:** Consolidates all menu/intro UI
**Result:** ~800 lines total (reasonable)

### Suggested Structure (After Consolidation)
```
stargwent/
├── main.py                    # Main game loop & UI
├── game.py                    # All game logic & mechanics (merged with stargate_mechanics)
├── cards.py                   # Card database
├── ai_opponent.py             # AI controller
├── menu.py                    # All menus (merged main_menu + stargate_opening)
├── deck_builder.py            # Deck customization
├── card_unlock_system.py      # Progression
├── animations.py              # Visual effects
├── create_placeholders.py     # Asset generator
└── tools/
    └── ability_rename.py      # Utility scripts
```

**This would reduce from 12 files to 9 core files + tools folder.**

---

## 🛠 Build & Packaging

### Debian Package (Linux)
We ship a helper script that assembles a `.deb` for Debian/Ubuntu style systems.

**Prerequisites**
- `python3` and `python3-pygame` runtime packages
- `dpkg-deb` (usually provided by the `dpkg` package)

**How to Build & Release a New Version**

1. **Edit the version badge** (line 7 of this README):
   ```markdown
   ![Version](https://img.shields.io/badge/version-X.Y.Z-blue)
   ```
   Replace `X.Y.Z` with your new version (e.g., `2.14.0`)

2. **Build the package** (automatically reads version from README badge):
   ```bash
   ./build_deb.sh
   ```
   The `.deb` will be created at `builds/releases/stargwent_X.Y.Z.deb`

3. **Commit and push**:
   ```bash
   git add -A
   git commit -m "Update to version X.Y.Z - [description]"
   git push origin main
   ```

**Note:** The version badge in this README is the **single source of truth**. The build script automatically reads it, so you only need to update one place.

**Advanced:** You can override the version by passing it directly: `./build_deb.sh 2.14.0`

The generated package installs to `/usr/share/stargwent` with a `stargwent` launcher in `/usr/bin`, desktop shortcut (`/usr/share/applications/stargwent.desktop`), and icon (`/usr/share/pixmaps/stargwent.png`).

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

### Development
- Built with **Python 3.8+** and **Pygame CE 2.5.6+**
- Inspired by The Witcher 3: Wild Hunt's Gwent
- Animation system designed for extensibility
- 90% complete, active development

### Legal
**This is a non-commercial fan project created purely for educational purposes and out of love for two incredible franchises.**

- **Gwent** is a trademark of CD Projekt Red - creators of The Witcher series and one of the best card games ever made
- **Stargate SG-1** is owned by MGM - the legendary sci-fi franchise that inspired this tribute
- This project is **NOT affiliated with or endorsed by** CD Projekt Red, MGM, or any related companies
- **No commercial use** - this is free, open-source, and will always remain so
- All trademarks, characters, and intellectual property belong to their respective owners
- This is fan service from fans who love both universes and wanted to combine them

*"You know, you blow up one sun and suddenly everyone expects you to walk on water."* - Col. Jack O'Neill

### Special Thanks
- CD Projekt Red for Gwent game design
- MGM for Stargate SG-1 universe
- [101 Soundboards - Stargate SG-1 Soundboard](https://www.101soundboards.com/boards/33269-stargate-sg1-soundboard) for character voice clips
- Pygame CE community for documentation
- Contributors and playtesters

---

## 🤝 Contributing

Suggestions and feedback welcome!

### Want to Help?
- **Card Designs** - Create new cards for factions
- **Visual Effects** - Design custom animations
- **AI Improvements** - Enhance decision-making
- **Documentation** - Improve guides
- **Bug Reports** - Report issues

---

## 💡 Quick Reference

| Action | Control |
|--------|---------|
| Select Card | Left click in hand |
| Play Card | Left drag to row |
| **Preview Card** | **Right click any card** |
| Pass Turn | Click DHD button (glowing red center) |
| **Activate Faction Power** | **Press SPACEBAR or click ACTIVATE** |
| **Debug Overlay** | **F3 (toggle zone boundaries)** |
| View Discard | Press D |
| Inspect Leader | Right click leader portrait |
| Drag Card (Deck Builder) | LEFT CLICK + DRAG |
| Zoom Card (Deck Builder) | RIGHT CLICK |
| Fullscreen | F11 |
| Restart | R (game over) |
| Quit | ESC |
| Mulligan | Click cards (2-5) + "Confirm" |
| Browse Cards | Arrow keys / Mouse wheel |
| Quick Select | 1/2/3 keys (rewards) |

---

## 🎯 Tips & Strategy

1. **Card Advantage** - Deep Cover Agents draw cards
2. **Weather Control** - Cripple opponent's strongest row
3. **Hero Timing** - Save Legendary Commanders for weathered rounds
4. **Passing Strategy** - Sometimes losing a round cheaply is smart
5. **Combos** - Build decks around Tactical Formation multipliers
6. **Round Management** - You only need 2 of 3 rounds to win

---

## 🐛 Known Issues

- **AI**: Basic-medium difficulty (improvements planned)
- **Sound**: Menu + Goa'uld + Asgard themes implemented; other factions' battle music & SFX still pending
- **LAN**: No automatic reconnect after disconnect; no state recovery from desync

---

## 🚀 Roadmap

### ✅ Completed
- Core Gwent gameplay
- All card abilities (20/20 fully working - 100% verified!)
- All leader abilities (35/35 fully working!)
- All unlockable card abilities (20/20 verified and working!)
- **⚡ v1.2: Goa'uld Ring Transportation - Return close combat unit to hand ONCE PER ROUND**
- **⚡ v1.2: 3-phase golden ring animation (descend → activate → ascend)**
- **⚡ v1.2: Visual selection with pulsing gold glow on close combat units only**
- **⚡ v1.1.1: Enhanced weather/special card dragging - drag to ANY row with visual feedback**
- **⚡ v1.1.1: Blue highlight shows all valid drop zones for weather/special cards**
- **⚡ v1.1: Fluid card interactions with smooth dragging, hover scaling, and dynamic shadows**
- **⚡ v1.1: AI turn animation system with 4 cinematic phases (thinking → selecting → playing → resolving)**
- **⚡ v1.1: Delta-time based animations for frame-rate independence (30-144 FPS)**
- **⚡ v1.1: Enhanced visual feedback - cards feel weighted and every AI action is readable**
- **⚡ v1.0: UI overhaul with right-click preview and streamlined controls**
- **⚡ v1.0: All leader abilities verified and fixed (Vulkar, Yu, Rak'nor, Freyr)**
- **⚡ v1.0: FactionPower system (renamed from IrisPower)**
- **⚡ v1.0: Leader matchup PNG background support**
- **⚡ v1.0: Unlock system verified (card every win, leader every 3 wins)**
- **⚡ v0.9: Cinematic leader matchups with 40+ lore-based quotes**
- **⚡ v0.9: ESC pause menu system**
- **⚡ v0.9: Round 3 asteroid field animation**
- **⚡ v0.9: Card back system for hidden hands**
- **⚡ v0.9: Leader selection backgrounds (35 total)**
- **⚡ v0.9: Minimum deck size enforcement (20 cards)**
- **⚡ v0.9: Enhanced faction power animations**
- **⚡ v0.8.1: Code cleanup - Removed 100+ lines of dead code**
- **⚡ v0.8.1: Ability verification - All abilities confirmed working**
- **⚡ v0.8: Deck persistence and progression system**
- **⚡ Faction Power system with unique cinematic effects**
- **🎨 4K resolution support (3840×2160)**
- **🌌 Enhanced animations (Stargate KAWOOSH, hyperspace, explosions)**
- **🖱️ Intuitive controls (left-click drag, right-click zoom)**
- Stargate theme integration
- Deck builder with drag-and-drop
- Progression system
- Visual effects & particle systems
- DHD pass button
- Faction-specific unlocks
- Discard pile viewer
- Improved AI pacing

### 🚧 Polish & Enhancement
- Sound effects & music
- Advanced AI difficulty levels
- Per-card custom animations (expand beyond current set)
- More hyperspace/wormhole effects
- LAN reconnection and state recovery

### 📋 Planned
- Tournament mode (best-of-3)
- Achievement system
- More factions (Wraith, Ori, Atlantis)
- Statistics tracking
- Custom card creation tools
- Internet matchmaking (beyond LAN/VPN)

---

## 🌐 LAN Multiplayer Architecture

### Overview

Stargwent features **peer-to-peer TCP-based LAN multiplayer** where two players can battle against each other in real-time. The system uses a deterministic game engine synchronized by exchanging only player actions, ensuring both clients see the same game state.

### Connection Flow

```
1. Main Menu → Select "LAN Multiplayer"
2. LAN Menu → Host (opens port 4765) OR Join (enter host IP)
3. Waiting Lobby ✨ → Chat while waiting, press READY when ready
4. Deck Selection → Both players choose faction/leader/deck independently
5. Seed Sync → Host generates seed, client receives it
6. Leader Matchup → Cinematic reveal animation
7. Game Start → Battle begins!
```

### Player Perspective

**Each player sees:**
- **YOU (Player 1)**: Hand face-up, full control
- **OPPONENT (Player 2)**: Hand as card backs (hidden), replays network actions
- **Board**: Shared view, all cards visible
- **Chat Panel**: Bottom-right corner during match
- **History Panel**: Left side shows game events (NOT chat)

### Key Components

#### LanSession (`lan_session.py`)
- TCP socket wrapper with JSON message framing
- Thread-safe inbox queue
- Newline-delimited JSON packets

#### Network Protocol (`lan_protocol.py`)
```python
Message Types:
  CHAT           # Live chat messages
  DECK_SELECTION # Faction, leader, 30 card IDs
  SEED           # Random seed for synchronization
  GAME_ACTION    # play_card, pass, faction_power
  MULLIGAN       # Card indices to redraw
  READY_CHECK    # Player ready status
```

#### NetworkController (`lan_opponent.py`)
Replaces AIController in LAN mode:
- Waits for network messages instead of computing moves
- Processes opponent actions and replays them locally
- Maintains turn synchronization

#### LanLobby (`lan_lobby.py`)
- Waiting room with live chat
- Ready/Not Ready toggle buttons
- "START MATCH" appears when both ready
- Shows connection status (Host/Client)

### Synchronization Strategy

**Deterministic Engine**: Both clients run the full game engine locally. Only player **actions** are sent over the network, not the entire game state.

**What Gets Synchronized:**
- ✅ Player actions (card plays, pass, faction power)
- ✅ Mulligan choices
- ✅ Random seed (ensures identical RNG)

**What Does NOT Get Synchronized:**
- ❌ Game state (calculated locally)
- ❌ Card positions (calculated locally)
- ❌ Scores (calculated locally)
- ❌ Animations (run locally)

### Message Flow Example

**Card Play:**
```
Player 1 (Local):
  1. Drags card to board
  2. NetworkPlayerProxy sends GAME_ACTION: play_card

Player 2 (Remote):
  1. NetworkController receives GAME_ACTION
  2. Finds card in hand by ID
  3. Replays card play on local board

Result: Both see identical board state
```

### Animations & Effects (v2.9)

All animations run **locally** on each client and are **fully synchronized**:
- ✅ Card play animations (Stargate activation, Naquadah Overload explosions)
- ✅ Faction power effects (Gate Shutdown with Iris closing, Sarcophagus Revival, etc.)
- ✅ Weather effects (Ice Planet, Nebula, Asteroid Storm, EMP)
- ✅ Special ability effects (Vampire, Inspiring Leadership, Deploy Clones, etc.)
- ✅ Legendary Commander entry effects with lightning
- ✅ Leader ability effects

**Both players see the same animations** when either player performs an action. The game synchronizes by:
1. Sending only player actions over the network
2. Each client runs the same game engine locally
3. Animation triggers fire based on game events

### Technical Details

- **Architecture**: Peer-to-peer TCP
- **Port**: 4765 (must be open on host)
- **Protocol**: JSON newline-delimited
- **Perspective**: Each player is Player 1 locally
- **Chat**: Available in lobby and during game
- **Disconnect**: Auto-detected, returns to menu

### Testing Checklist

#### Connection:
- Host can open port 4765
- Client can connect to host IP
- Both see "Connected" status
- Chat works in lobby

#### Gameplay:
- Both see same board state
- Card plays appear on both screens
- Pass turn syncs correctly
- Faction powers work
- Weather effects sync
- Leader abilities trigger
- Round end/start syncs

### Connection Robustness (v2.9)

The LAN system includes multiple reliability features:

| Feature | Description |
|---------|-------------|
| **Join Timeout** | 10 seconds to connect or fail |
| **Recv Timeout** | 1 second prevents blocking |
| **Keepalive** | 5-second heartbeat packets |
| **Connection Timeout** | 30 seconds without data = disconnect |
| **TCP Keepalive** | OS-level connection monitoring |
| **Disconnect Detection** | Visual overlay with "CONNECTION LOST" |

### IP Detection for Tailscale (v2.9)

The Host screen automatically detects all available IP addresses:

```
★ RECOMMENDED:  100.64.1.5      ← Tailscale VPN
  Alternative 1: 192.168.1.100   ← Local network
```

**Which IP to use:**
- **Tailscale (100.x.x.x)**: Both players on same Tailscale network
- **Local (192.168.x.x)**: Both players on same WiFi/LAN
- **Port forwarding**: Required for internet play without VPN

### Known Limitations

1. **LAN/VPN Only**: No internet matchmaking (use Tailscale for remote play)
2. **No Spectator Mode**: Only 2 players
3. **No Reconnect**: Disconnect = game over (detected within 30s)
4. **No Save/Resume**: Match must finish in one session
5. **Firewall**: Port 4765 must be open on host

---

**⚡ Chevron Seven Locked! ⚡**

Enjoy commanding the forces of the Stargate universe in this strategic card battle game!

Special thanks to the Sonic Pi team and community for providing the live-coding instrument that powers every custom soundtrack in Stargwent.

> Stargwent is intentionally modular: every card, leader, soundtrack, and UI element lives in plain Python and editable assets so anyone can reskin the experience into their own fantasy Gwent variant—Lord of the Rings, Dragon Ball, or whatever universe you want to explore. Dive into the codebase, swap art/audio JSON entries, and the engine adapts.

*v1.7 - Witcher 3 Gwent Layout: Authentic board design with clear separation, proper lane spacing, weather separator, and fixed hand positioning!*
*v1.6 - Fullscreen UI fixes: All bottom elements now properly visible with safe margins + Round winner scoreboard announcement!*
*v1.5.1 - Naquadah Overload now shows targeted blue explosions only on rows with destroyed cards!*
*v1.5.0 - Apophis weather decree, dual-lane storms, horn slots, legendary lightning, and Yu intel overhaul!*
*Legendary commanders now crackle with lightning as they land — embrace the spectacle!*
