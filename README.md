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
![Version](https://img.shields.io/badge/version-6.0.0-blue)
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
- **MALP Feed History Panel** - Military monitor aesthetic with scan-lines, score delta badges, turn numbers, round separators, and latest-entry pulse
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

### 🚀 Space Shooter Easter Egg (Vampire Survivors-Style)
- **Unlocked at 8 Draft Wins** - Beat the gauntlet to unlock a full arcade mini-game
- **5 Playable Factions** - Each with unique ship, weapon type, and passive ability
- **Smooth Ship Rotation** - Ships rotate smoothly toward movement direction (12 deg/frame interpolation)
- **Wormhole Escape** - Press Q to vanish through a wormhole and reappear at a random location
- **20-Wave Campaign** - Boss fights with escorts, XP/level-up upgrades, power-ups, and asteroid hazards
- **21 Upgrades (3 Rarities)** - Common, Rare, and Epic upgrades including Chain Lightning, Scatter Shot, Gravity Well, Shield Bash, Critical Strike, Evasion Matrix, Berserker Protocol, and more
- **Multi-Directional Fire** - Multi-Targeting upgrade fires in all 4 quadrants at higher stacks (perpendicular at 2+, rear at 3+, diagonals at 4+)
- **Fast-Paced Combat** - High base fire rate, frequent power-up drops, and rapid level-ups for non-stop action
- **5 Enemy Types** - Regular, Fast, Tank, Elite, and Kamikaze with formation spawning (V, Line, Pincer)
- **Visual Juice** - Parallax starfield, damage numbers, screen shake, kill streak counter, mini-radar, popup notifications
- **Per-Session Leaderboard** - Scores accumulate across restarts, reset on exit

### 🌐 LAN Multiplayer
- **Full 2-Player Networked Gameplay** - Host/Join with deck selection and chat
- **Room Codes** - Share easy codes like "GATE-7K3M" instead of IP addresses
- **Tailscale Support** - Smart IP detection prioritizes VPN addresses for remote play
- **Rematch System** - Play again with new faction/leader or disconnect
- **Integrated Chat** - Press 'T' to chat, quick chat keys 1-0 (Stargate quotes!), message bubbles, opponent name display
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
- **Comprehensive Stats Menu** - Win rate bars, achievements, fun facts, top 3 leaders with hover preview
- **Persistent Saves** - All progress saved to JSON

### 💾 Persistent Progression
- **Automatic Deck Saving** - Your deck is saved every time you finish customizing
- **Per-Faction Customization** - Each faction remembers your leader and deck choices
- **Win Tracking** - Track your wins, losses, and win streaks
- **Stats Menu** - Visual win rate bars, earned achievements, fun facts, top 3 leaders, overall record, AI vs LAN breakdown, matchups, turn counts, and draft mode history
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

### Unlockable Content

#### **21 Unlockable Cards**
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
