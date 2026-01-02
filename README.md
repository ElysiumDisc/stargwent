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
![Version](https://img.shields.io/badge/version-3.9.5-blue)
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
- **100% Fully Implemented** - All mechanics + Powers + Animations + Persistence + LAN Multiplayer + Draft Mode!
- **⚡ NEW v3.9.4: UNLOCKABLE CARD VERIFICATION & FIXES** - Complete logic audit of all 20 unlockable cards! Fixed ZPM Power doubling (now preserves bonuses), Puddle Jumper Ring Transport for unit cards, and Replicator Swarm description. All abilities verified with correct animations!
- **⚡ NEW v3.9.2: WITCHER-STYLE DECK BUILDER UI** - Complete visual overhaul featuring bottom accordion card preview (2x size), right-side vertical deck list, holographic stats panel, and smooth drag-and-drop interactions!
- **⚡ NEW v3.9.1: STATS MENU OVERHAUL** - Comprehensive player statistics with faction win rates, round breakdown (2-0 vs 2-1), comeback tracking, unlock progress, and red DHD-styled reset button!
- **⚡ NEW v3.9.0: FACTION POWER CINEMATICS** - Faction powers now feature high-fidelity animations: Asgard de-materialization beams, Lucian EM interference glitches, and functional Goa'uld Sarcophagus lid animations!
- **⚡ NEW v3.9.0: REPLICATOR SWARM WEATHER** - A new weather hazard featuring swarms of grey metallic blocks that jitter and consume row space!
- **⚡ NEW v3.9.0: COMBAT TEXT POP-UPS** - Scores now feature "BUFFED!", "INSPIRED!", or "WIPED!" tags that float alongside the numbers for better readability!
- **⚡ NEW v3.7.0: PERSISTENT ROW WEATHER ANIMATIONS** - Each weather card now has distinct visual effects that persist on affected rows until cleared! Ice crystals for Ice Planet Hazard, fiery meteors for Asteroid Storm, purple nebula clouds, cyan EMP arcs, and more!
- **⚡ NEW v3.7.0: ENHANCED CARD PREVIEW** - Right-click preview now shows cards at 2x scale with smooth scaling, faction-colored glow borders, and improved description layout!
- **⚡ NEW v3.7.0: DRAFT MODE SYNERGY SYSTEM** - Draft mode now shows synergy scores for each card choice, highlighting cards that combo with your current deck! Press Z to undo picks!
- **⚡ NEW v3.6.0: ELITE AI OVERHAUL** - AI logic rebuilt for strategic depth: Hero preservation, Round 2 bleeding, and tactical Faction Power usage. Single "Hard" difficulty now plays like a veteran!
- **⚡ NEW v3.5.0: NARRATOR & INTEGRATED CHAT** - Game history now acts as a narrator, explaining score changes (e.g., "Scorch vaporized 3 units! (-15)") and card effects. Chat is fully integrated into the history panel—press 'T' to type without leaving the action!
- **⚡ NEW v3.5.0: PRECISE CARD PLACEMENT** - You can now drop cards *between* existing units on the board, allowing for precise tactical positioning!
- **⚡ NEW v3.0.0: DRAFT MODE (ARENA)** - Roguelike deck-building mode! Choose from 3 random leaders, draft 30 cards from ALL factions (1 of 3 choices each pick), review your deck stats, then battle AI with your creation! Card pool includes ALL unlocked cards regardless of faction!
- **35 Unique Leaders** (15 base + 20 unlockable) with special abilities
- **⚡ NEW v2.9.1: ADVANCED AI OVERHAUL** - Smart mulligan logic, strategic pass timing, intelligent power/iris usage, and advanced target selection for Hathor/Medic abilities!
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
- **⚡ NEWv1.7 - Witcher 3 Gwent Layout: Authentic board design with clear separation, proper lane spacing, weather separator, and fixed hand positioning!*
- **⚡ NEWv1.6 - Fullscreen UI fixes: All bottom elements now properly visible with safe margins + Round winner scoreboard announcement!*
- **⚡ NEWv1.5.1 - Naquadah Overload now shows targeted blue explosions only on rows with destroyed cards!*
- **⚡ NEWv1.5.0 - Apophis weather decree, dual-lane storms, horn slots, legendary lightning, and Yu intel overhaul! *Legendary commanders now crackle with lightning as they land — embrace the spectacle!*
### 🆕 Recent UI Updates
- **Witcher-Style Deck Builder** - Complete redesign inspired by The Witcher 3's Gwent interface:
  - **Bottom Accordion**: Horizontal scrolling card pool with 2x sized cards, hover lift animation, and card name tooltips
  - **Right Deck List**: Vertical list view showing power, name, quantity, and row-type color indicators
  - **Holographic Stats Panel**: Translucent top-left panel with deck validity, card counts, and total strength
  - **Chevron Back Button**: Stylized "« DEPARTURE" button with faction-colored border
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
- ✅ **Chevron Back Button** – Stylized "« BACK" / "« DEPARTURE" button in top-left
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
- ✅ **Persistent Fullscreen** – Toggling fullscreen via F11/Alt+Enter (or launching with `python main.py --fullscreen` / `STARGWENT_FULLSCREEN=1`) keeps the entire experience in the chosen mode—from menus, to deck builder, to battle.
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

#### UI Improvements
- ✅ **Fullscreen Bottom UI Fix** - Pass button, Faction Power UI, and all bottom elements now stay properly visible in fullscreen mode
- ✅ **Safe Margin System** - Implemented 3% bottom margin and 2% right margin to prevent UI cutoff
- ✅ **Dynamic Hand Area** - Hand area now reserves minimum 25% of screen height (250px minimum) to prevent card cropping
- ✅ **Improved Button Positioning** - DHD Pass button and Mulligan button repositioned with increased safe spacing

#### Round Winner System
- ✅ **Cinematic Round Winner Overlay** - Beautiful 3-second announcement showing who won each round
- ✅ **Detailed Scoreboard** - Displays all 3 rounds with highlights for wins/losses
- ✅ **Perfect Timing** - Announcement appears BEFORE hyperspace transition to next round



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
- ✅ Aegir - "Asgard Archives": Draw on siege play
- ✅ All other leader abilities fully functional!

#### **20/20 Card Abilities Working**
- Draw abilities (Prometheus, Mothership, Operative)
- Special destruction (Thor's Hammer removes Goa'uld)
- Power doubling (ZPM doubles siege)
- One-sided scorch (Merlin's Weapon)
- Hand reveal (Communication Device, Sodan)
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
   * `FACTION_COLORS`: You need to define what color the placeholder cards should be (e.g., silver/purple).
   * `FACTION_BACKGROUND_IDS`: You need to tell it what filename to use for the faction selection screen.
   * Imports: You will need to add the new FACTION_NAME constant to the import line at the top of the script.


  
  
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

- **Weather, Horn**: Weather and horn cues now hook to dedicated files; add these to `assets/audio/`:
  - `weather_clear.ogg`
  - `weather_ice_planet_hazard.ogg`
  - `weather_nebula_interference.ogg`
  - `weather_asteroid_storm.ogg`
  - `weather_electromagnetic_pulse.ogg`
  - `horn.ogg`
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
- **Chat System**: "Subspace Communications" overlay toggles with `T`/`ESC`; when active it captures keyboard focus, when closed a subtle "Press T to Chat" hint sits below history, and the history panel stays visible during LAN matches.
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
| Open LAN Chat | Press T (ESC to close; LAN matches only) |
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

*"You know, you blow up one sun and suddenly everyone expects you to walk on water."* - Col. Samantha Carter

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



> Stargwent is intentionally modular: every card, leader, soundtrack, and UI element lives in plain Python and editable assets so anyone can reskin the experience into their own fantasy Gwent variant—Lord of the Rings, Dragon Ball, or whatever universe you want to explore. Dive into the codebase, swap art/audio JSON entries, and the engine adapts.

