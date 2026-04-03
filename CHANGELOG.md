# Changelog

*Older versions: [v5.0-v8.8](CHANGELOG-v5-v8.md) | [v1.0-v4.9](CHANGELOG-v1-v4.md)*

---

### Version 10.3.1 (April 2026)
**Space Shooter — Bug Fixes & Polish**

#### Bug Fixes
- **Asteroid collision crash** — fixed `AttributeError: 'Asteroid' object has no attribute 'width'` when player projectiles hit asteroids via spatial grid query. Asteroids are now properly skipped in the ship collision loop (handled in dedicated asteroid loop)
- **Settings save spam** — fixed settings being saved to disk on every frame during slider drags (100+ writes/sec). Added skip-if-unchanged guards on all setters and batch mode for slider interactions (single write on mouse-up)
- **Miniship escort facing** — interceptor escorts now properly follow the player's facing direction. When idle they mirror the owner's facing; when returning to orbit they face their movement direction; during combat pullout they face retreat direction instead of flying backwards

---

### Version 10.3.0 (March 2026)
**Space Shooter — Combat Overhaul & Carrier Rework**

#### Ship Fixes
- **Tok'ra Tunneler image** — now uses the correct `jaffa_rebellion_ship.png` design instead of `alteran_ship.png`
- **Wraith faction removed from player selection** — Wraith Hive is now exclusively a supergate boss encounter (like Ori Mothership). SHIP_VARIANTS entry retained for boss spawn code

#### Performance
- **Spatial grid collision detection** — new `SpatialGrid` class replaces O(n*m) brute-force projectile-vs-enemy checks with cell-based spatial partitioning (200px cells). Reduces ~21,000 collision checks/frame to ~2,000 at peak density
- **AI neighbor queries optimized** — asteroid dodge and ship separation in `_ai_standard_strafe` now use spatial grid queries instead of iterating all entities
- **Global projectile particle budget** — module-level cap of 800 trail particles prevents unbounded particle accumulation during intense combat. AI engine trails reduced from 80 to 40 max particles
- **Hostile-all and asteroid collisions** also routed through spatial grid

#### AI Improvements
- **Strafe direction switching** — AI enemies now periodically flip their strafe direction every 2-3 seconds (random timer) instead of using a fixed pattern based on object ID. Makes enemy movement much less predictable
- **Boss phase transitions** — Ori Mothership and Wraith Hive bosses now have 3 combat phases:
  - Ori: Normal → Aggressive (50% HP: faster movement, 40f fire rate) → Enrage (25% HP: 3 spread lasers, halved beam cooldown)
  - Wraith: Normal → Aggressive (50% HP: 180f dart spawn, 35f fire) → Desperate (25% HP: 120f dart spawn, max 5 darts, 25f fire, stronger lifesteal)
- **4-direction facing for all AI** — enemies now face up/down/diagonal toward targets instead of only left/right. Applied to all 7 AI behavior methods via shared `_ai_face_target()` helper
- **Flanking behavior** — when 3+ enemies are alive, ~33% of them approach the player from a 60-degree offset angle, creating natural flanking patterns

#### Controls & Game Feel
- **Tighter acceleration** — ship acceleration increased from 1.2 to 1.5, friction decreased from 0.88 to 0.82. Faster ramp-up and snappier stops
- **Velocity dead zone reduced** — from 0.1 to 0.05 for more responsive micro-adjustments
- **Auto-aim smoothing** — aim direction now lerps at 15% per frame toward new targets instead of snapping instantly. Target hysteresis keeps current target if within 1.5x best distance, preventing jerky transitions between crossing enemies

#### Weapon Animation Enhancements
Faction-themed visual effects for every projectile type:
- **Asgard (cyan)**: ContinuousBeam gets pulsing energy nodes every 40px + crackle sparks. PlasmaLance gets electric arc particles. DisruptorPulse gets impact ring
- **Goa'uld (golden)**: Laser gets golden afterglow trail (8-frame fade) + ember particles. Dual staff muzzle flash
- **Tau'ri (blue)**: Missile gets smoke trail layer + variable thrust sizing. AncientDrone gets spiral golden helix trail. TunnelCrystal gets crystalline shard fragments
- **Jaffa (orange-red)**: StaffBlast gets heat shimmer + ember scatter
- **Lucian Alliance (magenta)**: EnergyBall gets 3 orbiting spark particles. ProximityMine gets dual concentric pulsing rings
- **Wraith (purple, boss only)**: CullingBeam gets sinusoidal soul-drain wisps. OriBossBeam gets golden energy nodes

#### Carrier Miniship Overhaul (SC2 Carrier Reference)
Complete rework of the interceptor escort system modeled after StarCraft II Carriers:
- **Start with 4 interceptors** at level 1 (was 0 until level 3). Max increased to 8 at level 20 (was 5 at level 15)
- **Launch animation** — interceptors now fly out FROM the player ship instead of spawning in place. 30-frame launch phase where they accelerate to orbit position before engaging
- **Attack run pattern** — SC2-style dive-fire-pullout cycle: approach target → fire burst of 3 shots rapidly → retreat at 1.2x speed back to orbit for 40 frames → re-engage
- **Faction-specific weapons** — Tau'ri interceptors fire small missiles, Goa'uld fire golden lasers (unchanged). No longer all firing generic white lasers
- **Visible idle orbit** — interceptors orbit in a small 30px circle around their formation anchor when no enemies nearby, instead of sitting on a static point
- **HP scaling** — interceptor health now scales with level: 40 + 3×level (100 HP at level 20, was flat 40)
- **Faster respawn** — auto-build time reduced from 5s to 3s, matching SC2's auto-cast build rate
- Only factions with dedicated miniship sprites (Tau'ri, Goa'uld) get interceptors. Asgard/Jaffa/Lucian remain without escorts

---

### Version 10.2.0 (March 2026)
**Space Shooter Easter Egg — Deep Survival Update**

#### Controls & Game Feel
- **Auto-aim system** — projectiles now fire toward the nearest enemy within 800px while ship sprite still faces movement direction. Beams smoothly track targets each frame. The #1 Vampire Survivors-style improvement
- **8-direction facing** — ship now faces diagonals (NE/NW/SE/SW) when moving diagonally, not just 4 cardinals. All firing positions and beam collision updated for arbitrary angles
- **Snappier camera** — lerp speed increased from 0.08 to 0.12, cutting follow lag by ~33%
- **Faster rotation** — ship visual rotation 12°/frame → 18°/frame (90° turn in 5 frames instead of 7.5)
- **Input buffering** — Q (wormhole) and E (secondary) now buffer for 10 frames. Press slightly before cooldown ends and the ability fires the instant it's ready
- **Touch joystick dead band fix** — movement threshold lowered from 0.3 to 0.15 to match dead zone, eliminating the unresponsive band between 15-30% input

#### Kill Streak Combo System
- **Escalating damage multiplier** — sustained kill streaks now grant bonus damage:
  - 5 kills: 1.1x | 10 kills: 1.2x | 20 kills: 1.5x | 50 kills: 2.0x
- **Tier-colored UI** — streak display changes color with tier (orange → white → blue → purple → gold) with glow ring at tier 3+
- **Screen pulse** on each tier-up with popup notification (COMBO x5!, MEGA COMBO!, ULTRA COMBO!)
- Multiplier resets after 3 seconds of no kills

#### New Weapons (3 Lore-Accurate Types)
- **Replicator Nanite Swarm** (Asgard — "Loki's Lab Ship" variant) — fires 3-5 grey metallic nanites that self-replicate on kill: 1-2 children per kill, max 20 active, 3 generation limit. Mastery "Replicator Horde" raises cap to 30 with 3 children per kill
- **Wraith Culling Beam** (Goa'uld — "Wraith Alliance Cruiser" variant) — purple continuous beam that heals player 25% of damage dealt. Shorter range (1200px) but sustain advantage. Green life-steal wisps flow toward ship. Mastery "Feeding Frenzy" increases to 40% life steal
- **Tok'ra Tunnel Crystal** (Tau'ri — "Tok'ra Scout" variant) — slow crystal projectile (speed 6) creates gravity vortex on impact. 200px pull radius, 5 dmg/frame inner zone, 4s duration, max 2 active. Swirling purple visual with spiral arms. Mastery "Crystal Labyrinth" allows 4 vortices with doubled duration

#### New Power-Ups (3 Stargate-Themed)
- **Prior Plague** (epic, Goa'uld) — infects nearest 3 enemies with plague that spreads to nearby enemies within 100px (max 3 generations). Infected enemies take 30% more damage and show purple tint overlay
- **Ancient Ascension** (legendary, universal) — 10 seconds of transcendence: 2x damage, 2x speed, full invulnerability, all projectiles pierce, screen-wide XP magnet. Ship rendered with white energy glow and halo ring
- **Naquadria Cascade** (legendary, Lucian Alliance) — instant chain explosion bouncing between up to 15 enemies. 80 base damage with -10% per bounce. Uses ChainLightning + Explosion visuals for satisfying cascading detonation

#### Ancient Drone Weapon Overhaul
- **New `AncientDrone` projectile class** replaces generic Laser for Aurora-class drone_pulse weapon. Now renders as golden squid-shaped projectiles with:
  - Elongated golden oval body with bright yellow-white core
  - 3 trailing energy tentacles (randomized per frame)
  - Fading golden energy wisp trail
  - Organic wobble flight pattern true to the show
  - Rotates to face direction of travel
- Updated drone_salvo secondary and Drone Swarm mastery to use proper AncientDrone visuals
- Fixed Laser class SRCALPHA color rendering bug (3-tuple RGB on SRCALPHA surface)

#### Miniship Escort Improvements
- **Target prioritization** — escorts now favor low-HP enemies for finishing blows (weighted distance × HP ratio scoring)
- **Weaving strafe** — alternates strafe direction every 0.75s for dynamic attack patterns instead of one-directional circling
- **Retreat when close** — escorts drift backward when within 80px of target while strafing
- **8-direction facing** — escorts now use diagonal-aware facing toward their target

#### Beam Collision Rewrite
- Player beam collision detection rewritten from cardinal-only axis checks to proper beam-line projection math, supporting arbitrary aim directions from the auto-aim system

---

### Version 10.1.5 (March 2026)
**Balance Patch — Faction & Leader Tuning**

#### Bug Fix
- **Fixed Alteran faction passive not applying** — `AlteranAbility` was defined but missing from the per-player ability dict in `Player.__init__`. Alteran players now correctly receive "Flames of Enlightenment" (+1 per Alteran on board to first 3 non-heroes/round, max +3)

#### Balance Changes
- **Asgard default deck**: Removed Heimdall (8p hero) from starter deck, replaced with Asgard Mothership (10p non-hero, Draw 2). Reduces untouchable hero power from 40 to 32, making the deck less resilient to weather and scorch
- **Freyr leader nerfed**: Changed from total weather immunity to blocking the first 2 weather effects per game. After both blocks are consumed, weather affects Freyr's side normally. Prevents Freyr + Superior Shielding from completely nullifying weather as a game mechanic

---

### Version 10.1.0 (March 2026)
**Galactic Conquest Overhaul — Deep Strategy Update**

#### In-Game Version & License Display
- **Options menu** now shows `v10.1.0 • CC BY-NC 4.0` at the bottom (both main menu and pause menu)
- Central `GAME_VERSION` and `GAME_LICENSE` constants in `game_config.py`

#### AI Faction Personalities (Conquest)
- **6 distinct AI behaviors** shape counterattack, expansion, and faction wars:
  - **Goa'uld** — Aggressive: 1.5x counterattack, 1.4x expansion
  - **Asgard** — Diplomatic: 0.5x counterattack, prefers trade
  - **Jaffa Rebellion** — Vengeful: 2x counterattack if lost a planet last turn
  - **Lucian Alliance** — Opportunistic: targets weakest faction, +10% battle success
  - **Alteran** — Ascendant: passive early, 2.5x multiplier after turn 15
  - **Tau'ri** — Balanced: standard behavior

#### Crisis Third Options (Conquest)
- **Conditional 3rd choices** unlock based on campaign investments:
  - Replicator Outbreak + 2 Sensor Arrays → "Isolate & study" (gain relic)
  - Ori Crusade + any Allied faction → "Allied defense" (-30 naq instead of -60)
  - Galactic Plague + completed Ascension tree → "Ancient cure" (no losses)
  - Ascension Wave + 3 Ancient planets → "Harmonic resonance" (+1 power to ALL cards)
  - Wraith Invasion + 3 operatives → "Covert counterattack" (60% success, -10 naq)
- Third option button highlighted with gold border

#### Relic Combos (Conquest)
- **6 relic pair combos** trigger bonus effects:
  - Staff of Ra + Thor's Hammer → "Weapon of the Ancients": Hero +1 power
  - Ancient ZPM + Naquadah Reactor → "Unlimited Power": +2 starting cards
  - Ring Platform + Replicator Nanites → "Self-Replicating Network": remote fortify
  - Iris Shield + Kull Armor → "Impenetrable Defense": enhanced -2 enemy power
  - Flames of Celestis + Ori Prior Staff → "Ascended Arsenal": +15 naq per victory
  - Asgard Time Machine + Alteran Database → "Temporal Archives": +2 card choices

#### Building Synergies (Conquest)
- **4 connected-planet building combos**:
  - Shipyard + Training Ground → "Prometheus Protocol": +1 attack power
  - 2x Sensor Array → "Deep Space Telemetry": full enemy deck reveal
  - Naquadah Refinery + Shield Generator → "Naquadria Cascade": +50% refinery income
  - Shield Generator + Training Ground → "Integrated Defense Grid": +1 fortification

#### Contextual Card Rewards (Conquest)
- **Faction-weighted rewards** — homeworld conquests offer more faction-specific cards
- **Narrative arc themed cards** — planets in story arcs add thematic faction cards to pool
- **Conquest streak bonus** — 3+ consecutive victories add a hero card to reward pool

#### Deep Cover Espionage Missions (Conquest)
- **4 new Tok'ra operative mission types**:
  - **Forge Alliance** — shift faction relation one level toward friendly (3 turns, 15% death risk)
  - **Relic Hunt** — 50% chance to discover a relic at neutral planet (3 turns, 25% death risk)
  - **Doctrine Theft** — steal 15 Wisdom from enemy archives (2 turns, 30% death risk)
  - **Sleeper Agent** — persistent: enemy counterattacks from that planet start -1 card (5% death risk/turn)

#### Planet Development Track (Conquest)
- **Planets evolve** the longer you hold them:
  - **Unstable** (turns 1-2): +10% counterattack risk, 50% passive bonus
  - **Stabilized** (turns 3-4): normal behavior, full passive
  - **Developed** (turns 5-7): 150% passive bonus
  - **Integrated** (turn 8+): -5% counterattack, 200% passive bonus
- Tracked per-planet via `turns_held` in campaign state

#### Doctrine Trade-offs (Conquest)
- **Policies now have meaningful penalties** alongside buffs:
  - Ancient Meditation: +3 Wisdom/turn BUT -5 naq/turn
  - Blitzkrieg Tactics: -1 cooldown BUT -1 defense power
  - Enlightened Warfare: +1 battle power BUT +5% counterattack chance
  - War Logistics: +1 attack/turn BUT +5 alliance upkeep
  - Diplomatic Mastery: +5 influence/turn BUT +5% counterattack chance
  - Intelligence Networks: -1 mission turn BUT +5% incident chance
  - Shadow Government: free operative every 8 turns BUT -8 naq/turn
  - Advanced Engineering: buildings -25 naq BUT -2 Wisdom/turn
  - Supergate Project: enables Supergate BUT +8% counterattack chance

---

### Version 10.0.0 (March 2026)
**Alteran Faction — Ori & Ancients Unite**

#### New Faction: Alteran (Unlockable)
- **40 cards** spanning both Ori crusaders and Ancient scientists
- **5 heroes**: Adria (The Orici), The Doci, Merlin (Moros), Morgan Le Fay, Oma Desala
- **5 leaders** with unique abilities: Crusade (+3 power), Voice of the Ori (spy conversion), Sangraal Protocol (destroy hero), Eternal Watch (auto-revive), Path to Ascension (sacrifice for mass buff)
- **Faction passive**: "Flames of Enlightenment" — first 3 non-hero units each round gain +1 per Alteran card on board (max +3)
- **Faction power**: "Flames of Celestis" — set all non-hero units on opponent's weakest row to power 1
- **Unlock condition**: Win at least one game with each of the 5 base factions
- **Seafoam green** visual theme (#64C8AA)

#### New Abilities
- **Prior's Plague** — When played, -1 power to all enemy non-heroes in same row (min 1)
- **Ascension** — When destroyed, +1 power to all remaining friendly units on board

#### Turn Mechanic Fix
- **All manually-activated leader abilities AND faction powers now consume the player's turn** — no more free ability + card play
- Passive leader bonuses (Carter +2 siege, Bra'tac +1 agile, etc.) remain free
- Applies to all factions, adding strategic depth to ability timing

#### Draft Mode — Alteran Integration
- **Alteran leaders selectable in Draft** — all 5 Alteran leaders (Adria, Doci, Merlin, Morgan Le Fay, Oma Desala) appear in the leader selection pool when the faction is unlocked
- **Alteran AI opponents in Draft** — AI can play as Alteran with the curated default deck (Priors, Warships, Ascended units) when the faction is unlocked
- **Fixed draft leader pool filtering** — `DraftModeController` now correctly builds a flat list of unlocked leader card IDs instead of passing faction names (old bug caused silent fallback to all leaders regardless of unlock state)
- **Alteran synergy scoring** — draft deck-building advisor now evaluates Alteran-specific strategies:
  - **Alteran Presence**: +1/+2 synergy when drafting Alteran cards as an Alteran leader (rewards building into the faction passive "Flames of Enlightenment")
  - **Prior's Plague**: First plague card +2, 2nd-3rd +1 for multi-row debuff spread, 4th+ penalized
  - **Ascension**: Up to 3 Ascension cards valued at +2 (death buff synergy), bonus if deck has expendable low-power units
- **Unlock-gated everywhere** — Alteran only appears as leader choice or AI opponent when unlocked (win with all 5 base factions or unlock override toggle)

#### Deck Builder — Faction Filter
- **Faction filter tab** — new circular tab with Stargate icon filters card pool to show only faction-specific cards (excludes neutrals), complementing the existing Neutral tab

#### GPU Card Ability Animations — Dedicated Shaders
- **Ascension** — NEW dedicated `ascension` GLSL shader: ethereal golden-white light column ascending skyward with radial energy rays, rising wisps, shimmer noise, and gold→ethereal color gradient. Replaces reused `zpm_surge` shader with a thematic ascending light effect
- **Prior's Plague** — NEW dedicated `priors_plague` GLSL shader: toxic green miasma spreading horizontally with fbm noise turbulence, dripping tendrils, corruption veins, and scene desaturation in the plague area. Replaces reused `distortion` shader with a thematic pestilence effect
- Both abilities retain their full particle animation systems (motes, rings, clouds, tendrils) alongside the new GPU post-processing shaders
- GPU shader count: 12 → 14 (added `shaders/ascension.py`, `shaders/priors_plague.py`)

#### Faction Selection Scrolling Fix
- **Fixed Alteran faction unreachable on small screens** — faction selection now supports mouse wheel scrolling, legacy scroll, and keyboard auto-scroll-into-view, matching leader selection behavior
- On 768p screens, faction buttons overflow below the screen edge; scroll indicator ("Scroll for more") appears when content overflows
- Clipping viewport prevents buttons from drawing outside the scroll area

#### Galactic Conquest — Alteran Faction Integration
- **Alteran fully playable in Galactic Conquest** — select Alteran as your faction for a new campaign with lore-accurate Ori/Ancient planets
- **Fixed crash** when selecting Alteran in conquest (`galaxy_map.py` — `ALL_FACTIONS` and `FACTION_PLANETS` now include Alteran; fixed hardcoded 5-faction angle calculation to be dynamic)
- **3 lore-accurate planets**: Celestis (Ori holy capital, homeworld), Ver Eger (first contact village), Ortus Mallum (ruined Alteran settlement where the Ark of Truth was hidden)
- **Planet passives**: Celestis +15 naq/turn (Flames of Enlightenment), Ver Eger 35% auto-upgrade (Conversion), Ortus Mallum +1 card choice (Ark of Truth knowledge)
- **5 conquest leader abilities** (L1-L4 scaling with network tier):
  - **Adria — Orici's Crusade**: Bonus naquadah on victory, card upgrades at higher levels (worship generates power)
  - **Doci — Flames of Enlightenment**: Passive naquadah per owned planet/turn (faith energy from followers)
  - **Merlin — Sangraal Protocol**: Weaken enemy heroes in battle, buff your heroes (anti-ascended weapon)
  - **Morgan — Eternal Vigil**: Preserve cards on defeat, auto-replace lost cards (eternal guardian)
  - **Oma — Path to Ascension**: Sacrifice weakest card, upgrade strongest (ascension through sacrifice)
- **Narrative arc**: "The Ori Crusade" — conquer Celestis + Ver Eger + Ortus Mallum → Prior Staff relic + 120 Naquadah
- **New relic**: "Flames of Celestis" — +2 power to first card played each round (Alteran homeworld reward)
- **Conquest bonus**: Conquering Alteran planets grants "Ascension: +1 power to 2 random cards"
- **Alteran AI opponent**: Alteran appears as enemy faction on the galaxy map with seafoam green territory

#### Rule Compendium — Alteran & UI Fixes
- **Alteran faction added to Rule Compendium** — "Alteran" now appears in Leader Faction (Tab 5), Card Faction (Tab 9), and Faction Selection/Lore (Tab 10) filter panels; faction name mapping added for leader catalog display
- **Larger card art preview** — card preview panel merges two right-side slots for ~2x taller card image display, metadata text moved to dedicated slot below (`rules_menu.py`)
- **Larger leader portraits** — leader thumbnail panel merges slot pairs for taller display areas with bigger, more readable portraits; pagination arrows support scrolling through rosters (`rules_menu.py`)

#### AI Improvements
- Alteran-specific strategy: prioritizes cheap units first for snowball passive
- Prior's Plague and Ascension evaluation in card scoring
- Strategic leader ability timing consideration

#### Galactic Conquest — Strategic Depth & UI Overhaul

##### Building Upgrades
- **Lv 1→2→3 building upgrades** — all 5 building types now upgradeable with escalating costs (1.5x/2.0x base) and scaling effects
- Naquadah Refinery: +10/+18/+25 naq/turn | Training Ground: +1/+2/+3 defense | Shipyard: +1/+1/+2 extra cards | Shield Generator: -20/-30/-40 fortify cost
- Upgrade button appears in the new side panel when a player-owned building planet is selected

##### Wisdom Sink
- **4 repeatable wisdom actions** unlocked after completing any doctrine tree — solves the late-game dead-resource problem
- Ascended Insight (15 wisdom): +1 power to random card permanently
- Temporal Shift (20 wisdom): Reset 1 planet cooldown immediately
- Ancient Knowledge (25 wisdom): Reveal full enemy deck for next battle
- Enlightened Trade (10 wisdom): Convert to +30 naquadah
- Actions appear as "WISDOM POWERS" section at the bottom of the Doctrine screen

##### AI Diplomatic Proposals
- **4 AI-initiated proposal types** make the galaxy feel alive — AI factions now propose deals at turn end
- Trade Offer: Weakened factions (≤3 planets) offer trade + 20 naq signing bonus
- Joint Attack: Trading partners propose coordinated offensives against shared enemies (-1 attack cooldown)
- Ceasefire: Very weak factions (≤2 planets) request neutral status
- Tribute Demand: Strong factions (6+ planets) demand 40 naq — refuse and face +10% counterattack for 3 turns
- **Conquest strain warnings** — pre-attack popup warns when attacking adjacent to allied territory (30% alliance downgrade risk)

##### AI Espionage & Incident Choices
- **AI espionage events** — hostile factions with 4+ planets can target player planets (15%/turn) with resource theft, sabotage, or influence rigging
- Player choices: IGNORE (free, 70% enemy success), CAPTURE (-20 naq, 60% success), or auto-blocked by Counter-Intel operative
- **Diplomatic incident choices** — when operatives are discovered, choose: DENY (50/50 bluff), RECALL (safe retreat), or DOUBLE DOWN (guaranteed relations hit but +20% next mission success)

##### Crisis Event Choices
- **All 5 crisis events now present 2 strategic options** instead of auto-resolving:
  - Replicator Outbreak: sacrifice weakest card (safe) vs. gamble for enemy losing 2 cards (risky)
  - Ori Crusade: pay 60 naq for shields (costly safe) vs. endure -40 naq but AI loses planet
  - Galactic Plague: quarantine -30 naq (keep upgrades) vs. endure -20 naq (lose upgrades)
  - Ascension Wave: channel +2 power to strongest cards vs. store +20 wisdom
  - Wraith Invasion: stand and fight -50 naq (keep planet) vs. evacuate -20 naq (lose planet)

##### Map UI Overhaul
- **Right-side info panel** (~20% screen width) replaces cramped hover tooltips
  - Planet selected: name, owner, type, weather, building with level + UPGRADE button, BUILD buttons, fortification, passive, operatives, minor world influence bar, cooldown
  - No planet selected: victory progress bars, faction overview with relations, deck/relic/upgrade/operative stats
- **Simplified top HUD** — Turn, Naquadah, Wisdom (left) | Network tier, Planet count (right) — secondary stats moved to panel
- **8 bottom buttons** (from 10) — removed SAVE & QUIT (ESC) and RUN INFO (merged into panel); wider buttons
- **Non-SRCALPHA HUD/panel surfaces** — performance improvement for web builds (uses `set_alpha()` fast path)

##### New File
| File | Description |
|------|-------------|
| `galactic_conquest/wisdom_actions.py` | 4 repeatable wisdom actions, gated behind doctrine completion |

##### Key Modified Files
| File | Changes |
|------|---------|
| `galactic_conquest/campaign_state.py` | +3 fields: building_levels, pending_crisis, wisdom_actions_this_turn |
| `galactic_conquest/buildings.py` | Level-scaled effects, upgrade cost/can/do functions |
| `galactic_conquest/diplomacy.py` | AI proposals (4 types), strain warning, tribute rejection tracking |
| `galactic_conquest/espionage.py` | AI espionage events, incident choices, resolve functions |
| `galactic_conquest/crisis_events.py` | CRISIS_CHOICES data, choice parameter in apply/show |
| `galactic_conquest/campaign_controller.py` | All new popup flows, action handlers, turn-phase hooks |
| `galactic_conquest/map_renderer.py` | Side panel, HUD cleanup, 8 buttons, non-SRCALPHA surfaces |
| `galactic_conquest/doctrine_screen.py` | Wisdom powers button section |

#### Pre-Release Audit — Bug Fixes, Performance, LAN Hardening

##### Critical Game Logic Fixes
- **Fixed draw games treated as defeats** — card battle draws now return neutral outcome (no cooldown, no naquadah penalty, no "battles_lost" stat). Previously the `else` block caught both `"player_loss"` and `"draw"`, unfairly penalizing tied battles (`campaign_controller.py`)
- **Fixed empty deck crash in card battles** — added MIN_DECK_SIZE (10) validation before creating Game object. Returns `"draw"` for broken player deck, `"player_win"` for broken AI deck, preventing undefined behavior when all card IDs are invalid (`card_battle.py`)
- **Added defensive guard for empty card pool in neutral events** — `"cards"` effect now returns early message when `all_ids` list is empty instead of passing empty list to `rng.sample()` (`neutral_events.py`)
- **Changed loss handler to explicit `elif`** — `else:` → `elif card_result == "player_loss":` prevents future result types from silently falling into the loss path (`campaign_controller.py`)

##### Animation Performance
- **Fixed O(n²) particle removal** — replaced `list.remove(particle)` inside iteration (O(n) per removal) with single-pass list comprehension filter in `CardStealAnimation.update()` (`animations.py`)
- **Switched particle lists to `deque(maxlen=N)`** — trail and hearts lists now use `collections.deque` with `maxlen`, auto-dropping oldest elements on append. Eliminates per-frame list slicing (`self.trail = self.trail[-MAX:]`) that allocated new list objects every frame (`animations.py`)
- **Cached `smoothscale` in `CardStealAnimation.draw()`** — scale factor is constant (1.05), so the scaled card surface is now cached and reused instead of re-scaling every frame (`animations.py`)
- **Fixed animation pool memory leak** — `return_animation()` now clears `trail`, `hearts`, `on_finish`, and `_cached_scaled_card` fields in addition to `card_image` and `on_complete`, preventing stale particle/surface references from accumulating in pooled instances (`animations.py`)

##### LAN Networking Hardening
- **Fixed race condition in inbox queue drop** — replaced `queue.Queue(maxsize=1000)` with `collections.deque(maxlen=1000)` for game message inbox. The old get-then-put overflow pattern had a window where another thread could steal the freed slot, silently dropping the message. `deque.append()` is atomic under CPython's GIL (`lan_session.py`)
- **Lowered parse error threshold** — `max_parse_errors` reduced from 20 to 5. 20 consecutive JSON parse errors was far too lenient; 5 consecutive failures is sufficient to detect a corrupt connection while tolerating transient TCP fragmentation (`lan_session.py`)
- **Switched to monotonic clock for all network timing** — all `time.time()` calls in `lan_session.py` and `lan_opponent.py` replaced with `time.monotonic()`. Wall clock jumps from NTP sync could corrupt RTT calculations and trigger false connection timeouts (`lan_session.py`, `lan_opponent.py`)
- **Added single-retry for unacked game actions** — previously, actions unacknowledged after 3 seconds were silently deleted. Now retries once (re-sends the original message) before giving up, with stored `_pending_messages` for re-transmission (`lan_opponent.py`)
- **Added turn token gap tracking** — token sequence gaps now accumulate in `_token_gap_count` and display a HUD warning when 3+ actions have been lost, instead of silently resyncing (`lan_opponent.py`)
- **Added `desync_warning` handler on receive side** — the `desync_warning` message (sent after 3 consecutive card-not-found auto-passes) is now handled by the remote player with a HUD flash and game history entry, instead of being silently ignored (`lan_opponent.py`)

##### UI Polish
- **Fixed mouse coordinate truncation** — replaced `int(x * sx)` with `round(x * sx)` at all mouse scaling points (`_scaled_mouse_get_pos`, `_scaled_event_get`). Eliminates 1-pixel offset that could cause missed clicks on card edges in GPU fullscreen mode (`display_manager.py`)
- **Added ellipsis truncation for long leader names** — leader selection cards now truncate overflowing names with "..." after trying a smaller font, preventing text from clipping outside the card boundary (`leader_select.py`)

##### New File
| File | Description |
|------|-------------|
| `galactic_conquest/leader_select.py` | Per-battle leader selection screen for Galactic Conquest |

#### LAN Security & Bug Fixes
- **Fixed buffer overflow vulnerability** — `LanSession` reader now enforces 1 MB buffer limit; peers sending data without newline delimiters are disconnected instead of causing OOM (`lan_session.py`)
- **Fixed reader thread deadlock** — `inbox.put()` replaced with non-blocking `put_nowait()` with overflow eviction; prevents the reader thread from blocking indefinitely when the game loop falls behind on message consumption (`lan_session.py`)
- **Fixed async-blocking `wait_for_message`** — replaced `pygame.time.wait(50)` (blocks entire thread) with `await asyncio.sleep(0.05)` for proper async cooperation (`lan_game.py`)
- **Fixed async-blocking disconnect overlay** — `_show_disconnect_message` converted to async with `await asyncio.sleep` in its wait loop; no longer freezes the browser event loop on web (`lan_lobby.py`)
- **Fixed SRCALPHA disconnect overlay** — replaced full-screen SRCALPHA surface with non-SRCALPHA + `set_alpha()` fast path (`lan_lobby.py`)
- **Fixed "Connection lost!" spam in rematch** — status message now only added once instead of every frame when connection drops (`lan_menu.py`)
- **Fixed bare `except:` in lobby background loader** — narrowed to `except Exception:` to avoid swallowing `SystemExit`/`KeyboardInterrupt` (`lan_lobby.py`)
- **Added join IP input length limit** — capped at 45 characters to prevent unbounded string growth (`lan_menu.py`)

#### LAN Performance
- **Cached gradient backgrounds** — lobby, LAN menu, and rematch screens now pre-build gradient surfaces once instead of drawing 1080 lines per frame (`lan_lobby.py`, `lan_menu.py`)
- **Cached lobby panel surface** — SRCALPHA panel background replaced with non-SRCALPHA + `set_alpha()`, built once in constructor (`lan_lobby.py`)
- **Fixed per-frame font allocation in chat badge** — `draw_unread_badge()` now uses cached `font_small` instead of creating `SysFont("Arial", 14)` every frame (`lan_chat.py`)

#### Build System Fixes
- **Fixed dev files leaking into packages** — `.github/`, `.claude/`, `scripts/`, `build_web.sh`, `metadata.json` excluded from deb/AppImage builds (`build_deb.sh`, `build_appimage.sh`)
- **Fixed AppImage env var security** — `LD_LIBRARY_PATH` and `PYTHONPATH` no longer get trailing colon when unset (which adds `.` to search path) (`build_appimage.sh`)
- **Fixed hidden import mismatch** — local `build_exe.sh` and `build_dmg.sh` now include `PIL._imaging` and `PIL.ImageDraw` matching CI config
- **Fixed empty version crash in CI** — version detection job now fails with clear error instead of producing broken filenames (`build.yml`)
- **Fixed release body race condition** — release description moved to dedicated job that runs after all platform builds complete (`build.yml`)
- **Fixed deb missing SDL2_ttf dependency** — added `libsdl2-ttf-2.0-0` to `Depends` (`build_deb.sh`)
- **Fixed metadata.json channel paths** — deb and Windows glob patterns now match actual build output filenames
- **Added `raw_art/` and `backup/` to .gitignore**

#### Performance Improvements
- **LRU cache eviction for text render cache** — evicts oldest 50 entries when full instead of clearing all 400, preventing cache thrashing during gameplay (`render_engine.py`)
- **LRU cache eviction for scaled image cache** — evicts oldest 30 entries instead of clearing half, with move-to-end on access for proper LRU ordering (`render_engine.py`)
- **LRU cache eviction for particle sprite cache** — evicts oldest 60 entries instead of clearing all 300 (`animations.py`)
- **Animation list filter-in-place** — `AnimationManager.update()` uses swap-and-pop instead of creating new lists every frame, eliminating per-frame list allocation for animations, effects, and row weather (`animations.py`)
- **FBO pool bounded per resolution** — GPU framebuffer pool capped at 3 FBOs per resolution key; excess released immediately to prevent GPU memory leak on fullscreen toggle (`gpu_renderer.py`)
- **Drag trail bounded** — card drag trail capped at 50 entries to prevent unbounded list growth during long drag sessions (`main.py`)

#### Bug Fixes & Polish
- **Fixed silent game summary recording failures** — bare `except Exception: pass` replaced with warning log so stats persistence issues are diagnosable (`frame_renderer.py`)
- **Fixed weather state tracking** — `previous_weather` now uses `dict()` copy instead of `.copy()` to prevent stale reference when dict values mutate (`main.py`)
- **Added `is_gpu_available()` helper** — centralized GPU renderer null+enabled check in `display_manager.py` for consistent GPU availability checks across modules
- Fixed 3 debug print statements in `game.py` (now use proper logging)
- Deck builder shows locked factions with progress indicator

---

### Version 9.7.0 (March 2026)
**Galactic Conquest Strategic Depth — Minor Worlds, Doctrine Trees, Espionage, Victory Conditions**

#### Minor Worlds (Phase A)
- **9 minor worlds** — Neutral planets become persistent diplomatic actors: Abydos (Economic), Vis Uban (Spiritual), Atlantis (Scientific), Heliopolis (Scientific), Cimmeria (Militant), Kheb (Spiritual), Proclarush (Militant), Vagonbrei (Diplomatic), P3X-888 (Economic)
- **Influence system** (0-100) — Tiers: Neutral (0-29), Friend (30-59), Ally (60+) with passive decay toward resting point (25)
- **Ally exclusivity** — Only one faction can be ally per minor world; AI factions compete for influence
- **Type bonuses** — Friend/Ally tiers grant scaling bonuses: Scientific (+1 card choice / +1 card upgrade), Militant (+1 defense / +1 attack), Diplomatic (-15 naq trade / -8% counterattack), Economic (+8 / +15 naq/turn), Spiritual (+3 / +6 Wisdom/turn)
- **4 actions** — TRIBUTE (pay naq for influence), REQUEST QUEST, ATTEMPT ALLY, BULLY (+20 influence here, -10 from all others)
- **Quest system** — 5 quest types (Tribute, Defend, Conquer, Trade, Build) with dynamic generation and 2-turn cooldown
- **AI competition** — AI factions gain 5-10 influence on adjacent minor worlds (25%/turn), may claim ally status
- **Minor world screen** — CRT-styled panel showing influence bar, tier, active bonuses, quest progress, action buttons, AI competition info
- **Map integration** — Colored type rings on neutral planets, tooltip shows world type, influence, active quest

#### Doctrine Trees (Phase C)
- **Wisdom resource** — New currency: +5 per battle victory, +3 per neutral event, +8/turn per Ancient planet owned, spiritual minor world bonuses
- **5 doctrine trees** with 4 sequential policies + completion bonus each:
  - **Path of Ascension** (purple): Wisdom income → reward choices → battle power → wisdom doubled → Ascension Victory
  - **Doctrine of Conquest** (red): Cooldown reduction → attack power → extra attacks → conquest naq → free fortification
  - **Alliance Doctrine** (teal): Minor world influence → trade discount → alliance upkeep → passive sharing → Alliance Victory
  - **Shadow Operations** (dark purple): Operative risk reduction → faster missions → stronger sabotage → free operatives → coup mastery
  - **Technological Innovation** (blue): Building income → building discount → network thresholds → Supergate wonder → Network Victory
- **Escalating costs** — Each policy adopted (across ALL trees) increases the next policy's cost by 10 Wisdom, forcing meaningful choice between going wide vs deep
- **Doctrine screen** — CRT-styled 5-column layout showing tree progress, costs, and completion bonuses
- **Wisdom HUD** — Wisdom counter alongside Naquadah on map, DOCTRINES button on right-side

#### Tok'ra Operatives / Espionage (Phase B)
- **Operative lifecycle** — IDLE → MOVING (1 turn) → ESTABLISHING (2 turns) → ACTIVE → mission or death → IDLE/DEAD (3-turn revival)
- **3 free operatives** earned at turns 5, 10, and 16, named from Tok'ra canon (Anise, Malek, Delek, Garshaw, Aldwin, Kelmaa, Martouf, Thoran, Per'sus, Ren'al)
- **Rank system** (1-3) — Higher rank = better effectiveness, -5% death risk per rank; costs 40 naq to upgrade; reset on death
- **6 mission types** — Infiltrate (reveal deck, 10% risk), Sabotage (remove AI cards, 20%), Steal Intel (gain naq, 15%), Rig Influence (boost minor world, 10%), Coup (flip minor world ally, 40%), Counter-Intel (block enemy espionage, 0%)
- **Diplomatic incidents** — 10%/turn chance of detection on enemy faction planets; can downgrade relations from TRADING/ALLIED
- **Shadow Operations doctrine synergy** — -10% death risk, -1 turn mission times, +1 sabotage cards, free operative every 8 turns, Shadow Mastery doubles coup success + no incidents
- **Espionage screen** — CRT-styled operative roster with deploy, mission, recall, rank up actions
- **Map indicators** — Eye icon on planets with operatives, OPERATIVES button next to DIPLOMACY

#### Multiple Victory Conditions (Phase D)
- **Domination** (always available) — Capture all enemy homeworlds, 1.0x score multiplier
- **Ascension** (requires Path of Ascension doctrine) — 100+ Wisdom, control 3/5 Ancient planets, 1.2x multiplier
- **Galactic Alliance** (requires Alliance Doctrine) — 3+ allied minor worlds, 2+ major faction trade/alliance, 1.1x multiplier
- **Stargate Supremacy** (requires Tech Innovation doctrine) — Tier 5 network, Supergate wonder built, hold homeworld 3 turns, 1.3x multiplier
- **Score Victory** (always available, fallback) — Survive to turn 30, 0.8x multiplier
- **Victory progress UI** — Run info screen shows all 5 conditions with checkmark/X per requirement, locked conditions show required doctrine
- **End screen** — Victory type name, flavor text, and score multiplier displayed

#### Cross-Feature Integration
- Espionage `rig_influence` and `coup` missions target minor worlds
- Alliance doctrine gives +5 influence/turn to all minor worlds
- Shadow Operations doctrine improves operative effectiveness
- Non-default victories require completing specific doctrine trees
- Alliance Victory requires 3+ allied minor worlds
- Spiritual minor worlds provide Wisdom/turn for doctrine adoption
- Caught operatives cause diplomatic incidents with major factions
- Alliance doctrine reduces trade/alliance costs in diplomacy
- Tech Innovation doctrine reduces building costs
- Stargate Supremacy victory uses existing network tier system

#### UI Fixes
- **Fixed overlapping map buttons** — 10 bottom-bar buttons (SAVE & QUIT, DIPLOMACY, MINOR WORLD, OPERATIVES, DOCTRINES, RUN INFO, VIEW DECK, END TURN, FORTIFY, ATTACK) now evenly distributed across the full screen width with auto-sized widths and auto-fitting text labels

#### New Files (7)
| File | Description |
|------|-------------|
| `galactic_conquest/minor_worlds.py` | Minor world state, influence, quests, type bonuses |
| `galactic_conquest/minor_world_screen.py` | CRT-styled minor world interaction panel |
| `galactic_conquest/doctrines.py` | 5 doctrine trees, Wisdom economy, policy effects |
| `galactic_conquest/doctrine_screen.py` | CRT-styled doctrine tree selection UI |
| `galactic_conquest/espionage.py` | Operative lifecycle, missions, rank, diplomatic incidents |
| `galactic_conquest/espionage_screen.py` | CRT-styled espionage management UI |
| `galactic_conquest/victory_conditions.py` | 4 victory paths + score fallback, progress tracking |

#### Key Modified Files
| File | Changes |
|------|---------|
| `galactic_conquest/campaign_state.py` | Minor world states, wisdom, doctrines, operatives, supergate progress |
| `galactic_conquest/campaign_controller.py` | Turn hooks for all 4 systems, victory check replacement, quest progress, operative ticks |
| `galactic_conquest/map_renderer.py` | Type rings, wisdom HUD, doctrine/operative buttons, eye icons, victory progress |
| `galactic_conquest/card_battle.py` | Doctrine power bonuses, sabotage effects |
| `galactic_conquest/buildings.py` | Doctrine cost reduction |
| `galactic_conquest/diplomacy.py` | Doctrine trade discount, espionage incident handling |
| `galactic_conquest/meta_progression.py` | Victory type in scoring + multiplier |

#### Bug Fixes & Performance
- **Galaxy map: eliminated 8MB/frame SRCALPHA overlay** — Replaced per-frame full-screen SRCALPHA surface allocation with cached non-SRCALPHA + `set_alpha()` fast path (`map_renderer.py`)
- **Card steal animation: eliminated per-particle SRCALPHA allocation** — Replaced per-trail-particle `pygame.Surface(SRCALPHA)` creation (~3000 allocs/sec) with existing `_get_circle_sprite()` cache (`animations.py`)
- **Galaxy map: cached planet tooltip rendering** — Tooltip surface only rebuilds when content changes instead of 15+ `font.render()` calls every frame (`map_renderer.py`)
- **Galactic Conquest: cached BFS network bonuses per turn** — `get_network_bonuses()` BFS traversal was called 4+ times per turn; now cached and invalidated on ownership change (`campaign_controller.py`)
- **History panel: eliminated per-frame surface copy for pulse effect** — Last-entry pulse now uses a reusable overlay instead of `.copy()` every frame (`render_engine.py`)
- **Fixed bare `except:` swallowing SystemExit/KeyboardInterrupt** — Narrowed to `except Exception:` in leader portrait loading (`render_engine.py`)
- **Fixed LAN session crash on web platform** — `LanSession.__init__()` now raises `RuntimeError` when threading/queue unavailable instead of crashing on `None.Queue()` (`lan_session.py`)
- **Fixed LAN thread resource leak on disconnect** — `close()` now joins reader and keepalive threads with timeout to prevent zombie threads (`lan_session.py`)
- **Fixed supergate_progress default initialization** — Changed from empty `{}` to `{"built": False, "turns_held": 0}` for correct initial state (`campaign_state.py`)
- **Narrowed overly broad exception handling** — `except Exception` in deck load/save replaced with specific `(json.JSONDecodeError, OSError, KeyError, TypeError)` (`deck_persistence.py`)
- **Added logging to silent audio error catches** — 5 `except pygame.error: pass` blocks now print diagnostic messages (`sound_manager.py`)
- **Bounded space shooter flash surface cache** — `_flash_surf_cache` now clears at 50 entries to prevent unbounded memory growth (`space_shooter/game.py`)
- **Removed dead code** — Deleted unreachable `elif pass` block in LAN chat toggle (`event_handler.py`)

---

### Version 9.5.0 (February 2026)
**Supergate Boss Overhaul, Eye of Ra Buff, Miniship Visual & Movement Polish**

#### Supergate Boss Event Overhaul
- **Single supergate per wave** — One supergate spawns per boss wave; all bosses emerge through it sequentially (was: one supergate per boss)
- **Sound timing fixed** — Supergate song now plays when the opening animation finishes (kawoosh complete → gate open), not at the start of activation. Music ducks during kawoosh buildup for dramatic tension
- **Staggered boss spawns** — First boss emerges immediately when gate opens, then 2-second delay between each additional boss coming through
- **Supergate destroyed = bosses prevented** — Destroying the supergate cancels unspawned bosses with notification ("SUPERGATE DESTROYED! (2 BOSSES PREVENTED)"). Already-spawned bosses stay alive
- **Supergate stays until wave resolved** — Gate only closes when ALL bosses have spawned AND all are killed, preventing premature closing
- **Boss events never stack** — No new supergate event can trigger while any supergate or boss from the current wave exists
- **Environmental damage** — Supergates can be damaged by projectiles, asteroids (500 damage), and wormhole exit vortex (2000 damage). No touch/contact damage from ships
- **Boss ↔ enemy touch damage** — Ori/Wraith bosses deal 50 contact damage to regular enemies on collision, enemies deal 10 back to boss (30-frame cooldown)

#### Eye of Ra Buff
- **Anubis Eye of Ra beam** — Damage increased from 60 → 100, range from 600 → 800px

#### Miniship Visual & Movement Polish
- **Native resolution sprites** — Miniship images used at full 120x120 (x1 scale) instead of crushed 28x28, preserving all art detail
- **No color tint** — Removed faction color tint overlay that was creating visible colored squares around miniship sprites via BLEND_RGBA_ADD on transparent pixels
- **Wraith faction miniship support** — Wraith players now get miniship escorts using `wraith_miniship.png` with purple tint
- **Smooth lerp movement** — Miniship AI uses velocity blending for fluid motion: orbit return via lerp (natural deceleration), attack runs via smoothed velocity (responsive but no jerk)
- **No health bar clutter** — Miniship health bars removed for cleaner UI

---

### Version 9.4.0 (February 2026)
**Miniship Escort System, Wraith Cruiser Enemies, LAN Performance & Reliability**

#### Miniship Escort System (Carrier-Style Interceptors)
- **Carrier-style miniship escorts** — Tau'ri and Goa'uld players unlock autonomous interceptor miniships that orbit the player, sortie to attack enemies, and return to formation (inspired by Protoss Carrier interceptors from StarCraft)
- **Level-based scaling** — 2 escorts at level 3, growing to 3/4/5 at levels 6/10/15
- **Faction-specific sprites** — Tau'ri bee-ships, Goa'uld Al'kesh miniships, loaded from dedicated miniship assets at native resolution
- **Permanent with respawn** — Escorts persist until destroyed, then respawn after 5-second cooldown
- **Formation orbit** — Miniships orbit the player in evenly spaced formation when no enemies are nearby, with smooth rotation
- **Interceptor AI** — Engage enemies within 500px leash of owner, approach to 150px strafing range, fire Laser projectiles (8 damage, speed 20)
- **Escort Overdrive powerup** — Doubles escort fire rate + spawns 2 temporary extra escorts for 12 seconds
- **Escort Shields powerup** — Full heal all escorts for 8 seconds (Tau'ri and Goa'uld variants)
- **Other factions** (Asgard, Jaffa, Lucian) gracefully skip miniships — no assets yet

#### Wraith Miniship Enemy Type
- **Wraith Cruiser enemies** — New `wraith_miniship` enemy type with `hostile_all` behavior: attacks both the player AND other enemies
- **Hostile-all projectiles** — Purple bolts that damage any entity except the source ship, with XP/score awarded on kills
- **Spawns in pairs** from tier 5+ (Contested, 150s onward) with ±60px offset
- **Custom sprite** — Loaded from `wraith_miniship.png`, purple explosion palette

#### LAN Mode Audit & Fixes
- **TCP_NODELAY** — Eliminates 40ms Nagle buffering delay on all LAN packets, critical for smooth 20Hz co-op snapshots
- **Removed recv() lock** — TCP supports concurrent send+recv on separate threads; the lock was blocking send() for up to 1s on each recv timeout
- **Merged keepalive into ping** — Removed redundant keepalive packet; ping/pong already serves as connection keepalive, halving idle network overhead
- **Bounded chat queue** — `chat_inbox` now capped at 100 messages with `put_nowait()` overflow protection
- **Chat retry on ACK failure** — Messages retry once before marking as failed (prevents false failures on transient packet loss)
- **Snapshot int rounding** — Entity positions rounded to int instead of 1 decimal, saving ~15% bandwidth with client interpolation compensating

#### Co-op Miniship Support
- **Miniship sync** — Escort positions, health, and facing synced in state snapshots
- **Client-side rendering** — Miniships rendered with "ESCORT" label and health bars on client
- **Entity interpolation** — Client linearly interpolates all entity positions between 20Hz snapshots for smooth rendering (enemies, allies, miniships, projectiles, powerups, XP orbs)

---

### Version 9.3.0 (February 2026)
**Web Performance & Polish — Render Caching, Battle Music Fix, Conquest Menu SFX**

#### Web Stability
- **Fixed Round 2 crash on web** — `battle_music.set_battle_music_round()` now uses instant `stop()` instead of `fadeout()` on Emscripten, preventing audio backend crash when switching tracks
- **Skip blocking transition animations on web** — Round winner announcement, card sweep, and hyperspace transitions are bypassed on Emscripten to avoid freezing the browser event loop
- **Web FPS cap** — Lowered from 144 to 60 FPS on Emscripten for smoother frame pacing

#### Render Performance Caching (1080p Web)
- **Text render cache** — New `_render_text()` function in `render_engine.py` caches all `font.render()` calls (60-100 per frame) keyed on `(font, text, color)`, eliminating redundant text rasterization
- **Row separator cache** — 30 `draw.line` calls per frame pre-rendered into a single cached surface
- **History panel background cache** — MALP feed scanline grid (dozens of `draw.line` calls + SRCALPHA allocation) built once and reused
- **Score box background cache** — 6 per-frame SRCALPHA surface allocations replaced with cached styled backgrounds
- **Font object caching** — History panel fonts (`Courier New`) now use `_get_cached_font()` instead of creating new `SysFont` objects every frame
- **Hand background surface cache** — Player hand area SRCALPHA surface (1920xN) created once
- **Options menu caching** — Panel gradient and slider gradient fills cached instead of per-pixel rendering each frame

#### UI Sound Effects
- **Conquest menu hover sound** — `conquest_menu_select.ogg` plays when hovering over conquest menu buttons, respects Effects volume slider
- **Stats menu tab sound** — `stats_menu_tab.ogg` plays when switching tabs (click, TAB key, or number keys), respects Effects volume slider

#### Audio Control Clarity
- **Card effect animation sounds** (Replicator Swarm, Symbiote, Asgard Beam, etc.) — controlled by **Effects** volume slider
- **Commander voice snippets** (hero deployment quotes) — controlled by **Voice** volume slider
- **Leader voices** (draft mode hover) — controlled by **Voice** volume slider

#### CI/CD
- **Web build workflow** — Switched from GitHub Pages deployment to artifact-only build (private repo support)

---

### Version 9.2.0 (February 2026)
**PWA Web Deployment — Browser Play, Touch Controls, WebGL Shaders, Offline Support**

#### Web Platform (Pygbag WASM)
- **Full browser deployment** via Pygbag — compiles Pygame to WASM/Emscripten, playable at any URL
- **Async game loops** — all ~30 game loops across 22 files converted to `async/await` with `await asyncio.sleep(0)` for browser event loop compatibility
- **Platform detection** — `touch_support.py` module with `is_web_platform()`, `is_touch_platform()`, `force_touch_mode()` used by all subsystems
- **Conditional imports** — `threading`, `socket`, `subprocess` guarded behind `is_web_platform()` checks; MULTIPLAYER button hidden on web
- **"Tap to Start" splash** — unlocks browser audio context before game starts (required by all browsers)

#### Touch Controls
- **Touch gesture recognition** — `touch_gestures.py` translates FINGER events to synthetic mouse events: tap→click, long-press→right-click, drag→mouse drag, two-finger scroll→mousewheel
- **Zero downstream changes** — all existing menus, card game, deck builder work with touch via transparent event translation in `display_manager.py`
- **Space shooter virtual joystick** — `space_shooter/touch_controls.py` with `VirtualJoystick` (bottom-left) + `TouchActionButton` cluster (fire/wormhole/boost, bottom-right)
- **Multi-touch orchestrator** — finger IDs tracked per control, simultaneous move+fire supported

#### WebGL 2.0 Renderer
- **Dual renderer architecture** — `webgl_renderer.py` (PyOpenGL/raw GL ES) implements same API as `GPURenderer` (ModernGL)
- **Automatic backend selection** — tries ModernGL first, falls back to WebGL renderer on Emscripten
- **GLSL ES 3.0 shader porting** — all 12 shaders (bloom, vignette, CRT, distortion, event_horizon, kawoosh, hyperspace, asgard_beam, zpm_surge, shockwave, replicator_swarm, shield_bubble) use dynamic `glsl_version_header()` — `#version 300 es` + `precision highp float;` on web, `#version 330` on desktop

#### File I/O & Persistence
- **IndexedDB-backed saves** — `save_paths.py` routes to `/home/web_user/.local/share/stargwent/` on Emscripten
- **`sync_saves()` helper** — calls `platform.window.FS.syncfs()` after every JSON write to persist to IndexedDB
- **5 persistence files updated** — `deck_persistence.py`, `game_settings.py`, `unlocks.py`, `campaign_persistence.py`, `meta_progression.py`

#### PWA & Deployment
- **PWA manifest** — `build/web/manifest.json` with fullscreen display, landscape orientation, app icons
- **Service worker** — `build/web/sw.js` with cache-first strategy for offline play
- **GitHub Actions CI/CD** — `.github/workflows/web-deploy.yml` builds with Pygbag, injects PWA tags, deploys to GitHub Pages
- **Placeholder PWA icons** — `build/web/icons/icon-192.png` and `icon-512.png`

#### Desktop Compatibility
- **Zero behavior change on desktop** — all web-specific code gated behind `is_web_platform()` guards
- **All 45 modified/new files** pass Python syntax validation

#### Files Added
| File | Description |
|------|-------------|
| `touch_support.py` | Platform detection (web, touch, force override) |
| `touch_gestures.py` | FINGER event → mouse event gesture recognizer |
| `webgl_renderer.py` | WebGL 2.0 / PyOpenGL renderer backend |
| `space_shooter/touch_controls.py` | Virtual joystick + action buttons overlay |
| `build/web/manifest.json` | PWA manifest |
| `build/web/sw.js` | Service worker for offline caching |
| `build/web/icons/icon-192.png` | PWA icon (192x192) |
| `build/web/icons/icon-512.png` | PWA icon (512x512) |
| `.github/workflows/web-deploy.yml` | GitHub Actions web deploy pipeline |

#### Files Modified
| File | Changes |
|------|---------|
| `main.py` | Async entry point, tap-to-start splash, `await` all sub-loops |
| `main_menu.py` | Async loops, hide MULTIPLAYER on web |
| `game_setup.py` | Async `initialize_game()` |
| `event_handler.py` | Async `handle_events()` |
| `display_manager.py` | Touch gesture integration, WebGL backend selection |
| `gpu_renderer.py` | Dynamic GLSL version headers |
| `shaders/__init__.py` | `glsl_version_header()` function |
| `shaders/*.py` (12 files) | Dynamic GLSL version instead of hardcoded `#version 330` |
| `save_paths.py` | Web-aware save paths + `sync_saves()` |
| `deck_builder.py` | Async loop |
| `lan_session.py` | Guarded threading/socket imports |
| `lan_menu.py` | Guarded imports, async loops |
| `lan_game.py` | Async loops |
| `lan_coop_arcade.py` | Async loops |
| `lan_lobby.py` | Async loop |
| `draft_controller.py` | Async loops |
| `stats_menu.py` | Async loops |
| `rules_menu.py` | Async loop |
| `deck_persistence.py` | `sync_saves()` after writes |
| `game_settings.py` | `sync_saves()` after writes |
| `unlocks.py` | `sync_saves()` after writes |
| `space_shooter/__init__.py` | Async loops, touch overlay wiring |
| `space_shooter/game.py` | `update(touch_keys=None)` parameter |
| `space_shooter/ui.py` | Hide keyboard hints on touch |
| `galactic_conquest/*.py` (8 files) | Async loops throughout |
| `galactic_conquest/campaign_persistence.py` | `sync_saves()` after writes |
| `galactic_conquest/meta_progression.py` | `sync_saves()` after writes |

---

### Version 9.1.0 (February 2026)
**LAN Networking Robustness — Thread Safety, Co-op Sync, Chat Fixes, Game Action ACKs**

#### Thread Safety (lan_session.py)
- **Socket lock** for all send/recv/close operations — prevents crashes when reader, keepalive, and main threads touch the socket concurrently
- **Duplicate disconnect prevention** — only one disconnect message sent to queues regardless of which thread detects the failure
- **Parse error tolerance** raised from 3 to 10 consecutive errors — TCP fragmentation under high throughput no longer kills the connection prematurely
- **Double-close protection** — `close()` now grabs a local socket reference under lock and nulls the field atomically

#### Co-op Snapshot Completeness (space_shooter)
- **Proximity mines** now synced to P2 — Lucian Alliance mines were invisible to the client, causing damage from unseen hazards
- **Ion pulse effects** now synced to P2 — Asgard secondary fire visual rings now render on the client
- Client renders mines as pulsing colored circles with armed/unarmed state and blinking cores
- Client renders ion pulses as expanding translucent rings matching host visuals

#### Chat Fixes (lan_chat.py)
- **Fixed bare exception catch** — `except Exception` replaced with `except queue.Empty` to avoid swallowing real bugs
- **Typing indicator throttled** — now sends at most 1 typing=True message per 500ms instead of one per keystroke
- **Queue fully drained per frame** — all queued chat messages processed each frame instead of just one

#### Game Action ACKs (lan_opponent.py)
- **ACK system for game actions** — each action includes a `msg_id`; receiver sends `action_ack` back to confirm receipt
- **Stale ACK warnings** — unacknowledged actions after 3 seconds log a warning (informational, doesn't disconnect)
- **Card-not-found user feedback** — desync flash message and game history log entry when opponent's card can't be found in hand, so players know something went wrong instead of a silent auto-pass

#### Co-op Timing & Reliability (space_shooter)
- **Keepalive resets disconnect timer** — client tracks `_frames_since_last_msg` (any message) separately from `_frames_since_last_state` (snapshots only), preventing false disconnects during heavy host frames
- **Game-over message sent twice** with 100ms gap for cheap LAN reliability insurance
- **Connection lost screen** shows last known score and survival time instead of a bare "Host Disconnected" message

#### Files Modified
| File | Changes |
|------|---------|
| `lan_session.py` | Socket lock, disconnect dedup, parse error tolerance, close() safety |
| `lan_chat.py` | Fix exception type, throttle typing, drain queue fully |
| `lan_opponent.py` | Game action ACKs, card-not-found user feedback |
| `space_shooter/coop_game.py` | Add mines + ion_pulses to snapshot |
| `space_shooter/coop_client.py` | Render mines/ion_pulses, fix timeout, game-over fallback |
| `space_shooter/__init__.py` | Retry game-over send, wire `on_any_message()` |

---

### Version 9.0.0 (February 2026)
**Galactic Conquest Major Expansion — Stargate Network, 35 Leader Abilities, Diplomacy, Buildings, Crisis Events, Meta-Progression**

#### Stargate Network System (New)
- **Network tier system** based on connected planet count (BFS from homeworld through owned territory)
- 5 tiers: Outpost (1-3 planets), Regional (4-6), Sector (7-10), Quadrant (11-14), Galactic (15+)
- Tier bonuses stack: naquadah/turn, cooldown reduction, counterattack reduction, attack range, card choice bonus
- Leader conquest abilities scale L1-L4 with network tier
- Network tier displayed in map HUD

#### 35 Conquest Leader Abilities (New)
- **Ability registry** (`conquest_abilities.py`): 35 unique abilities (7 per faction) triggered at campaign hook points
- **Hook points**: on_victory, on_defeat, on_defense, pre_battle, on_turn_end, on_counterattack, on_neutral_event, on_fortify
- **Tau'ri**: O'Neill MacGyver Protocol (comeback power), Hammond Homeworld Command (defense bonus), Carter Naquadah Generator (bonus naq), Landry SGC Logistics (cooldown reduction), McKay Brilliant Improvisation (auto-upgrade), Quinn Kelownan Intelligence (pre-battle intel), Langford Archaeological Discovery (event bonuses)
- **Goa'uld**: Apophis System Lord's Dominion (permanent power), Lord Yu Ancient Wisdom (reveal cards), Sokar Netu's Torment (counterattack reduction), Ba'al Clone Network (loss negation), Anubis Ascended Wrath (elite defense bypass), Hathor Seductive Diplomacy (skip counterattacks), Cronus Imperial Expansion (scaling income)
- **Jaffa**: Teal'c Shol'va's Resolve (defense power), Bra'tac Warrior's Training (periodic upgrades), Rak'nor Rebel Recruitment (free conquest cards), Ka'lel Hak'tyl Warriors (cheaper fortify), Gerak Political Maneuvering (starting bonus), Ishta Guerrilla Resistance (multi-attack), Rya'c Next Generation (upgrade boost)
- **Lucian**: Varro Black Market Contacts (battle naq), Sodan Master Sodan Cloak (counterattack immunity), Ba'al Clone Infiltration (adjacent flip), Netan Smuggler's Network (event naq), Vala Treasure Hunter (extra relics), Anateo Hostage Tactics (planet retention), Kiva Shock Assault (first attack power)
- **Asgard**: Freyr Protected Planets Treaty (counterattack reduction), Loki Genetic Manipulation (card steal), Heimdall Research Archives (reward choices), Thor Asgard Fleet (ship power), Hermiod Beaming Technology (extended range), Penegal Asgard Preservation (card protection), Aegir Asgard Science Council (free upgrades)
- Ability name + level displayed in map HUD and Run Info screen

#### Diplomacy & Faction Relations (New)
- **Faction relations**: HOSTILE → NEUTRAL → TRADING → ALLIED
- **Trade** (50 naq): Faction stops counterattacking, mutual trade bonuses
- **Alliance** (100 naq + adjacent planet): Their territory counts for adjacency, mutual non-aggression
- **Betray**: Break alliance for +80 naq, faction becomes permanently hostile (+15% counterattack)
- AI factions can propose trades when weakened (< 2 planets)
- **DIPLOMACY button** on map HUD, CRT-styled diplomacy screen
- Replaces `friendly_faction: str` with `faction_relations: dict` in campaign state

#### Difficulty System (New)
- 4 difficulty levels: Easy, Normal, Hard, Insane
- Scales counterattack chance (15-50%), starting naquadah (60-150), AI power bonus (+0 to +2), loss penalty (-20 to -50)
- Difficulty selector in Customize Run screen
- Stored in campaign state, affects scoring multiplier

#### Planet Buildings (New)
- 5 building types: Naquadah Refinery (+10 naq/turn, 80 cost), Training Ground (+1 power defending, 60), Shipyard (+1 card attacking from here, 100), Sensor Array (reveal enemy deck size, 40), Shield Generator (-20 fortify cost, 50)
- 1 building per planet (plus fortification)
- BUILD button on map HUD with building selection popup
- Building income included in turn summary

#### Supply Lines (New)
- BFS check: planets disconnected from homeworld through owned territory are "unsupplied"
- Unsupplied penalties: -50% passive income, +20% counterattack chance, no fortification allowed
- Visual: dashed/dim outline on unsupplied planets in map renderer

#### Crisis Events (New)
- 5 galaxy-wide crisis events: Replicator Outbreak, Ori Crusade, Galactic Plague, Ascension Wave, Wraith Invasion
- 10% chance per turn after turn 5, with cooldown between crises
- Dramatic full-screen display with warning flash effect
- Effects range from naquadah loss to planet flips to card destruction

#### Meta-Progression (New)
- **Conquest Points (CP)**: Earned per run — 50 victory, 20 defeat, 10 per homeworld, 5 per arc, 3 per relic
- **Difficulty multiplier**: Easy 0.5x, Normal 1.0x, Hard 1.5x, Insane 2.0x
- **5 unlockable perks** (10 CP each): Extra Starting Card, Naquadah Boost (+20), Veteran Recruits (+1 all), Diplomatic Immunity (first counter auto-fails), Ancient Knowledge (start with relic)
- **Scoring system**: Base + planets + arcs + relics - turns, difficulty multiplier
- **High scores** saved to `conquest_high_scores.json`
- **UNLOCKS button** on conquest menu with CRT-styled perk/high scores screen

#### 5 New Neutral Events (15 → 20 total)
- **Nox Sanctuary**: Healing or cloaking choices
- **Tollan Ion Cannon**: Upgrade cards or gain naquadah
- **Goa'uld Sarcophagus Chamber**: Gamble — risk cards for power or destroy for naquadah
- **Ori Supergate**: High-risk gamble — gain/lose significant naquadah and cards
- **Pegasus Expedition**: Explore for cards and upgrades or play it safe

#### 3 New Narrative Arcs (3 → 6 total)
- **Asgard Exodus**: Othala + Orilla + Hala → Thor's Hammer relic
- **Lucian Underworld**: P4C-452 + Lucia + Langara → 200 naq + purge 5 weak cards
- **Alliance of Four Races**: Earth + Atlantis + Othala + 2 neutral → Quantum Mirror relic + 150 naq

#### 4 New Relics (14 → 18 total)
- `tel'tak_transport`: See defender power before attacking (wired into pre-battle preview)
- `jaffa_tretonin`: Weather can't reduce cards below 3 power
- `ancient_repository`: +30 naq/turn if you control Atlantis
- `asgard_time_machine`: Auto-reverses first planet loss per turn

#### 6 Previously Unwired Relics — Now Functional
- `iris_shield`: Block first Spy card played against player in battle
- `ancient_zpm`: +1 starting card in player hand
- `ori_prior_staff`: Weather sets non-heroes to 3 instead of 1
- `sarcophagus`: After each round, return 1 random card from discard to hand
- `quantum_mirror`: Show enemy hand size in battle HUD
- `replicator_nanites`: Already wired (verified)

#### 2 Previously Unwired Passives — Now Functional
- `extra_defense_card`: Extra player cards drawn in defense battles
- `weaken_enemy`: Remove cards from AI deck before battle

#### Fortification Now Affects Defense Battles
- Fort level passed to `run_card_battle()` — all player cards get +1 power per fort level when defending

#### Visual & UX Polish
- **Pulsing hyperspace lanes**: Connected player territory lanes pulse bright green on the galaxy map
- **Planet tooltips**: Hover planets for details — owner, type, weather, defender, fort level, building, cooldown, passive
- **Pre-battle preview**: ENGAGE/RETREAT screen showing player forces, enemy forces, weather, modifiers (replaces old elite defender screen)
- **Turn summary animation**: Animated income breakdown showing passive, reactor, network, and building income before AI phase
- **End screen scoring**: Victory/defeat screens now display run score and CP earned

#### New Files (8)
| File | Purpose |
|------|---------|
| `galactic_conquest/difficulty.py` | 4 difficulty levels with scaling parameters |
| `galactic_conquest/stargate_network.py` | Network tier system (5 tiers) based on connected territory |
| `galactic_conquest/conquest_abilities.py` | 35 leader abilities with L1-L4 scaling and trigger routing |
| `galactic_conquest/diplomacy.py` | Faction relations, trade, alliance, betray mechanics |
| `galactic_conquest/diplomacy_screen.py` | CRT-styled diplomacy interface |
| `galactic_conquest/buildings.py` | 5 planet building types with costs and effects |
| `galactic_conquest/crisis_events.py` | 5 galaxy-wide crisis events with dramatic display |
| `galactic_conquest/meta_progression.py` | CP awards, perks, scoring, high scores |

#### Key Modified Files
| File | Changes |
|------|---------|
| `galactic_conquest/campaign_controller.py` | Stargate network, conquest abilities, diplomacy, buildings, supply lines, crisis events, pre-battle preview, turn summary, scoring, meta-progression, fortification defense bonus, relic/passive wiring |
| `galactic_conquest/campaign_state.py` | ~20 fields: conquest_ability_data, difficulty, faction_relations, buildings, network_tier, crisis_cooldown, meta_points_earned |
| `galactic_conquest/map_renderer.py` | Pulsing hyperspace lanes, planet tooltips, building icons, network tier HUD, supply line visuals |
| `galactic_conquest/conquest_menu.py` | UNLOCKS button (5th), CP/campaigns/perks display, run_unlocks_screen() |
| `galactic_conquest/__init__.py` | Unlocks routing, meta perk application on new campaign |
| `galactic_conquest/galaxy_map.py` | Supply line BFS, building support |
| `galactic_conquest/neutral_events.py` | 5 new events + 8 new effect handlers |
| `galactic_conquest/narrative_arcs.py` | 3 new story chains |
| `galactic_conquest/relics.py` | 4 new relics (18 total) |
| `galactic_conquest/card_battle.py` | Fortification defense power, extra_defense_card, weaken_enemy passives |
| `galactic_conquest/planet_passives.py` | get_planet_passive() helper for tooltips |
| `game.py` | jaffa_tretonin relic weather floor modifier |
| `README.md` | Version 8.8.0 → 9.0.0, expanded Galactic Conquest features |
| `DEVELOPMENT.md` | Updated Galactic Conquest architecture to v9.0.0 (20+ modules), trimmed/organized |

---

