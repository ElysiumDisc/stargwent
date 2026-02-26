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

### Version 8.8.0 (February 2026)
**Performance Caching, Shield-on-Hit, Level 20 Masteries, Boss Overhaul**

#### Performance Improvements
- **Cached `struct.pack` VBO data** (`gpu_renderer.py`): Pre-computed module-level `_QUAD_VBO_DATA` constant replaces 3 per-init `struct.pack()` calls
- **Cached panel surfaces** (`frame_renderer.py`): `_get_cached_panel()` and `_get_cached_overlay()` eliminate 4 per-frame `pygame.Surface()` allocations for UI panels and 3 full-screen dim overlays
- **Cached effect surfaces** (`space_shooter/game.py`): `_get_flash_surf()` cache for hit-flash surfaces, grow-only reusable `_ion_pulse_surf` and `_orbital_surf` for effect rendering
- **Cached mouse scale factors** (`display_manager.py`): `_cached_mouse_sx/sy` globals with `_recalc_mouse_scale()` called only on display mode changes instead of every frame
- **Cached streak font** (`space_shooter/ui.py`): `_get_cached_font()` helper avoids per-frame `pygame.font.SysFont()` allocations

#### Shield Visual — Hit-Only Flash
- **Removed always-on bubble aura** (`space_shooter/ship.py`): Deleted the 30-line block drawing 10 wobbling circles + rim + inner glow every frame when shields > 0
- **GPU shader hit-only** (`space_shooter/game.py`): Shield bubble shader now activates only when `shield_hit_timer > 0`, with intensity fading over ~1 second (`hit_fade = shield_hit_timer / 60.0`)
- Ship looks clean normally; on shield hit → faction-colored Pygame flash + GPU hex grid + refraction + rim glow that fades out

#### Level 20 Primary Fire Mastery (New)
- **9 unique weapon masteries** auto-applied at exactly level 20 — one per weapon type
- **Overcharged Beam**: 50% wider beam + burn DoT (5 dmg/sec, 3 seconds)
- **Plasma Detonation**: 120px AoE explosion on impact
- **Cascade Disruption**: Disruptor pulse fragments into 3 mini-pulses on hit
- **Focused Optics**: Laser shots pierce through all enemies
- **Staff Barrage**: Fires 4 staffs instead of 2
- **MIRV Warhead**: Missiles split into 3 homing sub-missiles on impact
- **Drone Swarm**: Each drone pulse shot spawns 2 extra tracking drones
- **Kree's Judgement**: Every 5th staff shot is supercharged (3x damage, 2x size)
- **Unstable Naquadah**: Energy balls deal trail damage to nearby enemies
- Mastery popup notification + screen shake on acquisition
- `PRIMARY_MASTERIES` dict added to `space_shooter/upgrades.py`

#### Boss Overhaul
- **Doubled boss HP**: Ori Mothership 10,000 → 20,000 HP + 5,000 → 10,000 shields; Wraith Hive 8,000 → 16,000 HP + 3,000 → 6,000 shields
- **Wraith boss full size**: Wraith ship image scaled 2x after loading (was using tiny natural PNG size)
- **Boss event lifecycle fix**: All supergates now stay open until EVERY boss from the wave is destroyed, then all gates show closing animation simultaneously
- **Destroyed gate behavior**: Destroying a supergate stops boss emergence but already-spawned bosses remain until killed
- **Flat supergate HP**: Supergates now have constant 40,000 HP (was 5x boss HP)

#### Audio
- **Secondary fire sounds**: New `_load_secondary_sound()` + `_play_secondary_sound()` system — supports per-faction + per-variant secondary fire audio (e.g. Beliskner transporter beam)
- **Asgard boost sound**: `asgard_boost_space_shooter.ogg` loaded via existing variant boost sound system
- **Galactic Conquest defense alert**: `conquest_defend.ogg` plays when an AI faction attacks the player's planet

#### Key Modified Files
| File | Changes |
|------|---------|
| `gpu_renderer.py` | Cached `_QUAD_VBO_DATA` module constant |
| `frame_renderer.py` | `_get_cached_panel()`, `_get_cached_overlay()` |
| `display_manager.py` | `_cached_mouse_sx/sy`, `_recalc_mouse_scale()` |
| `space_shooter/game.py` | Effect surface caches, shield hit-only shader, level 20 mastery system, secondary sound, doubled boss HP, wraith 2x scale, boss lifecycle fix |
| `space_shooter/ship.py` | Removed always-on shield aura, dual_staff mastery (4 staffs) |
| `space_shooter/projectiles.py` | `ContinuousBeam.width_mult` for beam mastery |
| `space_shooter/upgrades.py` | `PRIMARY_MASTERIES` dict (9 weapon masteries) |
| `space_shooter/ui.py` | `_get_cached_font()` cache |
| `space_shooter/entities.py` | Supergate flat 40k HP (removed `boss_hp` param) |
| `galactic_conquest/campaign_controller.py` | `conquest_defend.ogg` defense alert sound |

---

### Version 8.7.0 (February 2026)
**Faction Shield Tints, Asteroid Field Events, CI Fix**

#### Faction-Tinted Shields (GPU + Software)
- **GPU shader** (`shaders/shield_bubble.py`): New `shield_tint` vec3 uniform — hex grid, rim glow, and inner glow now derive colors from faction instead of hardcoded cyan-blue
- **`SHIELD_TINTS` dict** maps all 5 factions to normalised RGB tint values
- **Software renderer** (`space_shooter/ship.py`): New `SHIELD_COLORS` dict with per-faction (bubble, rim, inner) RGB tuples
- Shield aura bubbles, outer rim, inner glow ring, hit flare, crack lines, and shield bar all use faction-specific colors
- **Tau'ri / Asgard**: Blue shields (existing look preserved)
- **Goa'uld / Jaffa / Lucian Alliance**: Orange shields matching faction identity
- Game loop (`game.py`) passes player faction tint to GPU shader each frame via `update_shield()`

#### Asteroid Field Events (New)
- **Periodic dense asteroid waves** starting at 60 seconds of survival
- **3-second warning**: "ASTEROID FIELD INCOMING!" popup notification before each field arrives
- **Directional approach**: Asteroids stream from a random direction toward the player
- **Escalating difficulty**: Duration grows from 6s to 12s cap; spawn density increases every 3 waves (1→3 asteroids per burst)
- **Mixed sizes** (40-130px) with varied speeds (3.5-7.0) for visual variety
- **45-75 second cooldown** between fields
- Screen shake on field start, numbered wave announcements ("ASTEROID FIELD #1!")

#### GitHub Actions CI Fix
- **Deleted all 44 old build artifacts** (~7GB) that were filling the GitHub Actions storage quota
- **Added `retention-days: 1`** to all 4 `upload-artifact` steps — artifacts only need to survive until the release job downloads them
- Builds will no longer fail with "Artifact storage quota has been hit"

#### Key Modified Files
| File | Changes |
|------|---------|
| `shaders/shield_bubble.py` | `shield_tint` uniform, `SHIELD_TINTS` dict, faction-derived hex/rim/glow colors |
| `space_shooter/ship.py` | `SHIELD_COLORS` dict, faction-tinted aura/hit flare/shield bar |
| `space_shooter/game.py` | Faction tint passed to GPU shader, `_update_asteroid_field()`, `_start_asteroid_field()` |
| `.github/workflows/build.yml` | `retention-days: 1` on all artifact uploads |
| `README.md` | Version badge 8.6.0 → 8.7.0, asteroid field events, faction-tinted shields |
| `DEVELOPMENT.md` | Updated space shooter architecture to v8.7.0 |

---

### Version 8.6.0 (February 2026)
**Space Shooter Polish — Shield Bubble Shader, Boss Beam Fix, Audio Variants**

#### Shield Bubble GPU Shader (New)
- **New post-processing shader** `shaders/shield_bubble.py` — localized energy bubble around the player ship when shields are active
- Hexagonal energy grid pattern visible on the bubble shell, slowly rotating
- Subtle UV refraction/distortion inside the bubble area
- Pulsing energy rim at the bubble edge, faint inner glow
- Intensity scales with shield health percentage — fades as shields deplete
- Registered in shader chain (disabled by default, driven by space shooter game loop)
- Graceful fallback: effect is fully optional, never crashes the game if GPU unavailable

#### Enhanced Pygame Shield Aura
- Replaced static 6-segment arc circles with **10 dynamic drifting bubble circles** using golden angle spacing
- Each bubble wobbles independently in size and alpha over time
- Brighter 3px outer rim ring (bloom shader enhances this)
- Inner glow ring with subtle pulsing for depth

#### Boss Beam Origin Fix
- **Ori Mothership** and **Wraith Hive** beams now fire from the ship's **nose** (facing direction) instead of center
- Beam angle-to-player calculation also originates from the nose for accurate targeting
- Popup notifications ("ORI BEAM!" / "CULLING BEAM!") positioned at the nose

#### Enemy Visual Tuning
- Enemy tint overlay alpha reduced from 60 to 30 — subtler faction coloring, less overwhelming
- Hit flash (red overlay) alpha reduced from 80 to 50 on both player and enemy ships

#### Audio — New Sounds & Variant Support
- **Cloak activation sound**: `cloak_space_shooter.ogg` plays immediately when any ship picks up the cloak powerup
- **Variant-specific boost sounds**: Boost sound loader now supports per-variant audio (e.g. `tauri_boost_space_shooter_alt_1.ogg` for Aurora-class)
- Boost fallback chain: variant-specific → faction default → generic
- New audio files: `cloak_space_shooter.ogg`, `tauri_boost_space_shooter_alt_1.ogg`, `jaffa_boost_space_shooter.ogg`, `jaffa_space_shooter.ogg` (hit), `lucian_space_shooter.ogg` (hit)
- All 5 factions now have dedicated hit sounds; Jaffa and Goa'uld have dedicated boost sounds

#### New Files (1)
| File | Purpose |
|------|---------|
| `shaders/shield_bubble.py` | Hexagonal energy bubble post-processing shader |

#### Key Modified Files
| File | Changes |
|------|---------|
| `space_shooter/game.py` | Boss beam nose origin, hit flash alpha reduction, `_update_shield_shader()`, cloak sound, variant boost sound loader |
| `space_shooter/ship.py` | Dynamic bubbling shield aura (replaces static segments) |
| `space_shooter/spawner.py` | Enemy tint alpha 60 → 30 |
| `shaders/__init__.py` | Shield bubble effect registration |
| `README.md` | Version badge 8.5.0 → 8.6.0 |

---

### Version 8.5.0 (February 2026)
**Galactic Conquest Expansion + Space Shooter Overhaul — Alt Ships, Supergate Bosses, Relics, AI Wars**

#### Galactic Conquest — 8 New Systems

##### Planet Weather (Phase 1A)
- Planet `weather_preset` fields now wired into card battles — battles on Tartarus have ice, Othala has EMP, etc.
- 4 neutral planets gain weather: Abydos (ice), Atlantis (EMP), Cimmeria (nebula), Proclarush (asteroid)
- Weather type map for display names in battle UI

##### Planet Passives (Phase 1B — New)
- **18 planet passives** grant bonuses when owned: naquadah/turn, card choice bonus, counterattack reduction, upgrade chance, cooldown reduction, weaken enemy
- Key passives: Earth +15 naq/turn, Dakara +10 naq/turn, Atlantis +1 card choice, Tartarus enemies -1 card, Hasara -1 cooldown
- Passives listed in Run Info screen

##### Fortification System (Phase 2A — New)
- **FORTIFY button** on galaxy map: spend 60 naquadah to fortify a player-owned planet (max level 3)
- Shield diamond icons on fortified planets, fortification level shown in planet info HUD
- Fort count displayed in top HUD bar

##### Elite Homeworld Defenders (Phase 2B — New)
- Homeworld attacks trigger dramatic **"ELITE DEFENDER"** screen with leader name and faction color
- All AI cards get **+2 power** and **+2 extra faction cards** in homeworld battles
- Pulsing faction-colored glow ring on enemy homeworlds on galaxy map

##### Relic/Artifact System (Phase 3 — New)
- **14 Stargate-themed relics** in 3 categories: Combat (Staff of Ra, Thor's Hammer, Kull Armor, Iris Shield, Ancient ZPM, Ori Prior Staff, Sarcophagus), Economy (Asgard Core, Naquadah Reactor), Exploration (Ring Platform, Replicator Nanites, Alteran Database, Quantum Mirror)
- **Homeworld relics**: each conquered homeworld awards a guaranteed faction relic (e.g. Goa'uld → Sarcophagus, Asgard → Asgard Core)
- **CRT-styled relic acquisition screen** with icon, name, category, and description
- **Multi-choice relic screen** for events (Furling Ruins)
- Combat relics modify decks pre-battle: Staff of Ra +1 Goa'uld, Thor's Hammer +2 Heroes, Kull Armor -1 enemy
- Economy relics: Asgard Core +20 naq/victory, Naquadah Reactor +10 naq/turn
- Ring Platform enables attacking 2-hop planets, Alteran Database +1 card choice, Replicator Nanites 20% duplicate
- Relic count in map HUD, full relic list in Run Info

##### AI Faction Wars (Phase 4 — New)
- AI factions attack each other's adjacent territory each turn
- Attack chance: 15% + 5% per planet owned (max 40%), success weighted by relative strength (25-55%)
- Flash messages: "Goa'uld captured Dakara from Jaffa!" / "Jaffa Rebellion has been ELIMINATED!"
- Creates dynamic galaxy where territory shifts without player intervention

##### 8 New Neutral Events (Phase 5 — 7→15 total)
- **Replicator Infestation**: Lose 2 cards OR gain 1 powerful card
- **Prior Conversion**: Gain powerful card + lose 2 OR +50 naquadah
- **Time Dilation Field**: +100 naquadah OR upgrade 3 cards
- **Tok'ra Alliance**: +2 faction cards OR +80 naquadah
- **Furling Ruins**: Gain random relic OR +100 naquadah
- **Ba'al's Clone Lab**: Duplicate strongest card OR +80 naquadah
- **Wraith Culling Beam**: Lose 1 + gain 2 faction cards OR -40 naquadah
- **Ascension Trial**: Remove 3 weakest + upgrade 2 strongest +2 OR +50 naquadah

##### Narrative Arcs / Story Chains (Phase 6 — New)
- **3 story chains** tracking planet conquest sequences with relic/naquadah rewards:
  - **Path of the Ancients**: Heliopolis → Kheb → Atlantis = Ancient ZPM relic
  - **Fall of the System Lords**: Tartarus → Netu → Hasara = 150 naq + remove 3 weak cards
  - **Jaffa Liberation**: Dakara → Hak'tyl → Chulak = Staff of Ra relic + 100 naq
- Progress flash messages ("Path of the Ancients: 2/3"), dramatic completion flash
- Arc progress displayed in Run Info screen

##### Run Info & HUD Polish (Phase 7)
- Run Info screen: new sections for Relics, Planet Passives, Fortifications, Story Arcs
- Map HUD: relic count, fort count in top bar; fortification level in planet info panel
- Homeworld glow ring pulsing with faction color on galaxy map

#### Campaign State Expansion
- 3 new fields: `fortification_levels`, `relics`, `narrative_progress`
- Backwards-compatible serialization via `.get()` defaults
- `add_relic()` / `has_relic()` helper methods

#### Space Shooter — Alt Ships, Supergate Bosses, New Weapons

##### Alternate Ship Variants (6 New Playable Ships)
- **Data-driven variant system**: `SHIP_VARIANTS` dict in ship.py replaces hardcoded faction if/elif chains
- **Ship select UI**: Up/Down (W/S) cycles variants within a faction, variant dots + name + description shown below ship
- **Asgard Valhalla-class** (heavy warship): Plasma Lance primary (piercing cyan bolt), Ion Pulse secondary, Heavy Armor passive (25% dmg reduction, 20% slower)
- **Asgard Beliskner-class** (cruiser): Fast beam primary, Transporter Beam secondary (teleport nearest enemy 300px away), Adaptive Shields passive (5 shield hits = +10% dmg for 5s)
- **Asgard Research Vessel**: Disruptor Pulse primary (rapid small shots), Sensor Sweep secondary (mark enemies for +30% dmg taken), Analyzer passive (marked kills = double XP + better drops)
- **Goa'uld Apophis Flagship**: Dual Staff primary (two parallel blasts), Ribbon Blast secondary (cone shockwave + knockback), Sarcophagus Regen passive (heal when <50% HP)
- **Tau'ri Aurora-class**: Ancient battleship with elongated hull — Drone Pulse primary (rapid golden homing shots), Drone Salvo secondary (6-drone burst), Ancient Shields passive (steady shield regen)
- **Jaffa Ha'tak Refit**: Dual Staff primary, Jaffa Rally secondary (spawn 2 temp ally ships), Symbiote Resilience passive (3s invuln when below 30% HP, 60s cooldown)
- **Goa'uld Anubis Mothership**: Dual Staff primary, Eye of Ra secondary (devastating line-damage beam, 600px range, 60 dmg), Anubis Shield passive (absorbs 3 hits completely)
- AI enemies now spawn with random ship variant sprites for visual variety

##### New Projectile Types
- **PlasmaLance**: Slow thick cyan-white bolt, 35 dmg, pierces 1 enemy, glow trail
- **DisruptorPulse**: Rapid small blue-white flickering shots, 8 dmg, fast fire rate
- **OriBossBeam**: 1500px golden sweeping beam, rotates 90 degrees over 2s, line-circle collision
- **WraithBossBeam**: 1200px purple beam, 1.2 dmg/frame, 50% life-steal heals the Wraith Hive

##### Supergate Boss Event System
- **Supergate animation**: Full Stargate-style 5-phase sequence — ring materializes with chevron pulses, explosive kawoosh vortex burst outward, retraction into shimmering event horizon with ripple rings and lightning tendrils, boss emerges, gate stays open
- **Destroyable supergates**: Supergates have 5x boss HP (Ori: 50000, Wraith: 40000) — destroy the gate to stop it, or kill the boss. Health bar shown when damaged
- **Supergate persists**: Gate stays open with shimmering horizon until boss is killed or gate is destroyed
- **Ori Mothership boss**: 10000 HP / 5000 shields, 2.5x scale, subtle blue center glow (matching PNG orb), fires golden sweeping beam + regular lasers, `ori_space_shooter.ogg` beam sound
- **Wraith Hive boss**: 8000 HP / 3000 shields, 2.0x scale, fires purple culling beam with life-steal, spawns wraith darts, `wraith_space_shooter.ogg` beam sound
- **Beam telegraph**: 1-second charge-up warning (flickering line + growing glow) before beam fires, slower 3s sweep — avoidable with good movement
- **Random boss type**: Each supergate randomly spawns Ori or Wraith boss
- **Player-only targets**: Supergate bosses must be killed by the player — regular enemies ignore them, boss beam still damages everything
- **Wave escalation**: Wave 1 = 1 boss, wave 2 = 2 bosses, wave 3+ = 3 bosses (capped), spread at equal angles around player
- **Boss death rewards**: Massive explosion + screen shake, 3-5 powerup drops, 500 XP, 5000 score, all enemies stunned 60 frames
- First supergate at 3 minutes survival, subsequent every 180-300s after previous boss defeated

##### Bigger Wormhole Gravity
- Pull radius 300→1000, core radius 50→160, max acceleration 3.0→5.5, visual radius 80→160 — massive wormhole gravity well

##### Audio & Balance Fixes
- **All space shooter SFX now respect volume sliders**: Hit sounds, boost sounds, wormhole, supergate activation, Ori beam, and Wraith beam all route through Master × Effects volume (were hardcoded, ignored settings)
- **Supergate activation sound**: `supergate.ogg` plays when the supergate enters its kawoosh activation phase
- **Variant-specific hit sounds**: Each ship variant can have its own hit sound (e.g. Aurora-class uses `tauri_space_shooter_alt_1.ogg`), falls back to faction default
- **Faction-specific boost sounds**: Goa'uld uses `goa'uld_boost_space_shooter.ogg`, others use generic boost sound
- **Fixed**: Goa'uld hit sound filename corrected (was missing apostrophe, never loaded)
- **Fixed**: Hit sound cooldown now frame-based (0.2s) instead of per-hit (was skipping ~30 hits on rapid-fire ships)
- **Fixed**: Ship rotation uses nearest cardinal cached image — fixes left-facing ships appearing vertically flipped
- **Base Tau'ri ship renamed**: F-302 → BC-304 (Daedalus-class battlecruiser)
- **Regen balance**: Ancient Shields 0.8→0.3/frame, Sarcophagus Regen 0.2→0.1/frame
- **Contact damage +44%**: Boss touch 25→36, regular touch 10→14
- **XP scaling adjusted**: Base 80 × 1.12^n → 480 × 1.25^n (upgrades come significantly less frequently)

##### LAN Co-op Parity Fixes
- **Fixed**: Ship variant selection now properly transmitted in co-op — both players see correct alt ship sprites, weapons, and abilities (was always defaulting to variant 0)
- **Fixed**: Supergate boss events now run in co-op — Ori Mothership and Wraith Hive boss fights appear for both players with beam damage hitting P1 and P2
- **Fixed**: Hit sound cooldown now ticks in co-op (was never decremented — sound played once then broke)
- **Fixed**: Asteroids now visible to co-op client (were simulated on host but missing from network snapshot)
- **Fixed**: Supergate health bar synced to co-op client (shows damage state on both screens)
- **Fixed**: XP scaling formula aligned between solo (120 × 1.18^n) and co-op (was using 1.15 multiplier)
- **Fixed**: Boss kill rewards trigger correctly in co-op (massive explosion, powerup drops, enemy stun, revival check)
- **Fixed**: Co-op revival invulnerability now uses **per-player timers** — revived player gets 3s invuln without affecting partner (was shared powerup — both players got invuln or neither did)
- **Fixed**: Invulnerability checks added to ALL co-op damage paths: projectile hits, beam damage, contact damage, and area bomb splash (revived players were taking damage immediately)
- **Fixed**: All space shooter audio (music + SFX channels) now cut off immediately on exit — no lingering sounds when returning to draft mode

#### Replicator Swarm Animation + Sound Fix
- **Fixed**: Replicator Swarm cards (close row) now trigger `ReplicatorCrawlEffect` animation (120 spider-bots + GPU metallic shimmer shader)
- **Fixed**: `add_special_card_effect()` now called for ALL unit cards (not just special row), so any card with a named animation fires correctly
- **New sound**: `replicator.ogg` now plays when any Replicator Swarm card is played (player or AI)
- Added `play_replicator_sound()` to `SoundEffectManager`
- Wired into all 3 card-play paths: player regular units, AI turn 1 animation, AI LAN/remote play

#### New Files (4)
| File | Purpose |
|------|---------|
| `galactic_conquest/planet_passives.py` | 18 planet passive bonuses + helper functions |
| `galactic_conquest/relics.py` | 14 relics, Relic dataclass, homeworld relic mapping |
| `galactic_conquest/relic_screen.py` | CRT acquisition screen + multi-choice mode |
| `galactic_conquest/narrative_arcs.py` | 3 story chains with progress tracking |

#### Key Modified Files
| File | Changes |
|------|---------|
| `space_shooter/game.py` | Supergate boss system, common threat, beam collisions, new secondary handlers, passive abilities, variant propagation |
| `space_shooter/ship.py` | SHIP_VARIANTS data, 7 alt ship configs, new AI behaviors (ori_boss, wraith_boss), new secondaries, new passives |
| `space_shooter/projectiles.py` | PlasmaLance, DisruptorPulse, OriBossBeam, WraithBossBeam |
| `space_shooter/entities.py` | Supergate class with 5-phase kawoosh animation |
| `space_shooter/upgrades.py` | ori_mothership + wraith_supergate enemy types, explosion palettes |
| `space_shooter/ship_select.py` | Up/Down variant selection, variant dots, description display |
| `space_shooter/spawner.py` | Random alt variant sprites for AI enemies |
| `space_shooter/__init__.py` | Variant tuple return, variant propagation to game |
| `space_shooter/coop_game.py` | p1/p2 variant params, supergate/beam snapshot serialization |
| `space_shooter/coop_client.py` | Supergate + beam rendering |
| `space_shooter/coop_protocol.py` | Variant field in READY message |
| `campaign_controller.py` | Passives, fortify, AI wars, elite screen, relic hooks, arc checks, Run Info |
| `neutral_events.py` | 8 new events + 7 new effect handlers |
| `card_battle.py` | Weather injection, elite params, relic combat modifiers |
| `galaxy_map.py` | Neutral weather, AI-vs-AI methods, Ring Platform 2-hop |
| `map_renderer.py` | FORTIFY button, shield icons, homeworld glow, relic/fort HUD |
| `campaign_state.py` | 3 new fields + relic helpers |
| `reward_screen.py` | Card choice bonuses from passives + relics, Replicator Nanites |
| `main.py` | `add_special_card_effect` called for regular unit cards (AI paths) |
| `event_handler.py` | `add_special_card_effect` called for regular unit cards (player path) |
| `sound_manager.py` | `play_replicator_sound()` method |

---

### Version 8.4.0 (February 2026)
**Stargate Menu Border, Button Scaling, Performance Optimizations**

#### Main Menu — Stargate-Themed Border & Larger Buttons
- **Stargate ring border**: New pre-rendered translucent border around the menu button area featuring Ancient blue outer glow, gold naquadah inner accent, and 6 amber chevron markers (top/bottom center + corners)
- **Dark panel fill**: Semi-transparent dark background behind buttons so they stand out against any background image
- **Dynamic button width**: Buttons now measure the widest text label (e.g. "GALACTIC CONQUEST") and auto-size with padding — no more text overflow at any resolution
- **Minimum width 500px at 1080p** (was 400px) — all labels fit comfortably with room for the border

#### DHD Button Performance Overhaul
- **Cached radial gradient**: The ~20-ellipse radial gradient for hovered buttons is now rendered once per button size/color and cached — eliminates expensive per-frame re-draw
- **Cached text rendering**: Button text is pre-rendered at init with auto-scaling — if text is wider than the button, the font size shrinks automatically until it fits
- **Cached title surface**: The multi-layer STARGWENT title (6 shadow passes + glow + highlight) is pre-rendered once instead of re-drawn every frame

#### Files Modified
- `main_menu.py` — Stargate border, dynamic button width, cached title rendering
- `dhd_button.py` — Gradient caching, text auto-fit, cached text surfaces

---

### Version 8.3.0 (February 2026)
**Galactic Conquest — Customize Run, Faction Bonuses, Defense Rewards, CRT Menu**

#### Conquest Menu Overhaul — CRT Terminal UI
- **CRT scanline effect**: Semi-transparent scanline overlay on the conquest menu for retro Stargate terminal aesthetic
- **Minimal layout**: Removed large description panel — clean title + 4 buttons: NEW CAMPAIGN, RESUME, CUSTOMIZE RUN, BACK
- **Pulsing amber title**: Animated "GALACTIC CONQUEST" with subtle brightness pulse
- **Pre-cached scanlines**: Scanline overlay surface rendered once and reused for performance at 4K

#### Customize Run Screen (New)
- **Friendly Faction**: Choose an allied faction whose territory starts as yours (None by default); they don't counterattack
- **Neutral Events**: Set the number of neutral planet events (3, 5, 7, or 9); 4 additional Stargate-canon planets added (Kheb, Proclarush, Vagonbrei, P3X-888)
- **Enemy Leader Selection**: Per-faction leader picker for homeworld defenders — cycle through each faction's leaders or leave as Random
- **Persistent settings**: Saved to `conquest_settings.json` via XDG data paths; applied when starting new campaigns
- **CRT-themed UI**: Arrow selectors for each option, faction-colored labels, allied faction tags

#### Faction-Specific Conquest Bonuses (New)
- **Tau'ri** (Intel): +1 random card from any faction on conquest
- **Goa'uld** (Domination): +2 power upgrade to a random card on conquest
- **Jaffa Rebellion** (Training): Remove weakest card from deck on conquest (if deck > 15 cards)
- **Lucian Alliance** (Trade): +50 bonus naquadah on conquest
- **Asgard** (Technology): +1 power upgrade to 2 random cards on conquest
- Faction bonuses displayed on reward screen after card pick

#### Counterattack Defense Bonuses (New)
- **Card reward**: Successful defense now awards +1 random card from the attacking faction
- **Upgrade chance**: 30% chance to upgrade a random card +1 power on successful defense
- Defense bonus details appended to the flash message

#### Leader Portrait in Neutral Events (New)
- Player's leader portrait displayed alongside event text using card art asset (`assets/{card_id}.png`)
- Portrait with border glow and leader name label below
- Event text layout shifts right when portrait is present for clean side-by-side arrangement

#### Campaign State Expansion
- Added `friendly_faction`, `neutral_count`, and `enemy_leaders` fields to CampaignState
- Full serialization support in save/load for all new settings
- Galaxy map `generate()` accepts friendly faction, neutral count, and enemy leader parameters
- Friendly faction planets start as player-owned in galaxy generation

#### Files Modified
- `galactic_conquest/conquest_menu.py` — Complete rewrite: CRT theme, 4 buttons, CustomizeRunScreen class
- `galactic_conquest/__init__.py` — Wire customize_run action, pass settings to new campaign
- `galactic_conquest/campaign_state.py` — Added friendly_faction, neutral_count, enemy_leaders fields
- `galactic_conquest/campaign_persistence.py` — Added conquest settings save/load functions
- `galactic_conquest/campaign_controller.py` — Faction bonuses, defense bonuses, skip friendly faction counterattacks
- `galactic_conquest/galaxy_map.py` — 9 neutral planets, friendly faction support, enemy leader assignment
- `galactic_conquest/neutral_events.py` — Leader portrait display alongside event text
- `galactic_conquest/reward_screen.py` — Faction bonus message display

---

### Version 8.2.0 (February 2026)
**Galactic Conquest — Roguelite Card-Battle Campaign Mode**

#### Galactic Conquest Mode (New)
- **Full roguelite campaign**: Conquer a galaxy of 20 planets through card battles
- **Galaxy map**: Stargate-themed star map with 5 faction homeworlds, 10 territory planets, and 5 neutral planets connected by hyperspace lanes
- **Strategic territory**: Only attack planets adjacent to your territory; enemy factions can counterattack your borders
- **Roguelite deck progression**: Win battles to draft cards from defeated factions; deck evolves throughout the campaign
- **Neutral planet events**: 7 text events with choices — bonus cards, naquadah, card upgrades, deck trimming, and more; every event offers an optional neutral card recruit
- **Planet control scaling**: More planets = better rewards (Standard → Enhanced → Supreme tiers with increasing card choices and naquadah multipliers)
- **Card upgrade system**: Permanently boost card power via naquadah or event rewards for the current run
- **AI counterattacks**: Each enemy faction with border territory has a 30% chance per turn to attack one of your planets
- **Win condition**: Capture all 4 enemy homeworlds; Lose condition: your homeworld falls
- **Conquest deck builder**: Full deck builder UI with separate conquest deck save; immune to Mercenary Tax and Naquadah budget penalties (like Draft Mode)
- **Conquest deck background**: Dedicated `deck_building_conquest_bg.png` background for the deck builder in conquest mode
- **Campaign persistence**: Auto-saves after every turn; resume from exact state
- **Run Info screen**: View territory, reward tier, upgraded cards, cooldowns, and enemy homeworld status mid-campaign

#### Conquest Submenu (StarCraft-meets-Stargate UI)
- **Cinematic panel UI**: Framed center panel with animated pulsing corner accents, split "GALACTIC / CONQUEST" gold title
- **Buttons with hover glow**: New Campaign, Resume (shows save info: turn, faction, deck size, naquadah), Back
- **Separate backgrounds**: `conquest_menu_bg.png` for submenu, `conquest.png` for galaxy map — both with Stargate-themed Milky Way galaxy art

#### Galaxy Map HUD
- **Two-row bottom HUD**: Info row (planet details, defender, weather) above button row (Save & Quit, Run Info, View Deck, End Turn, Attack)
- **Top HUD**: Turn number, naquadah, deck size, planet control count, upgrade count
- **Planet interaction**: Click planets to see details; glow effects on attackable planets; cooldown timers displayed
- **Keyboard shortcuts**: D = View Deck, I = Run Info, ESC = Save & Quit

#### Stats Menu — Conquest Tab
- **New "Conquest" tab** (6th tab): Campaigns started/won/lost, battle record, planets conquered, defenses, fastest victory, cards drafted/upgraded, naquadah earned
- **Conquest achievements**: Galaxy Conqueror, Galactic Emperor, Blitzkrieg, Planet Hoarder

#### Rules Menu — Conquest Info
- **Game Modes section** added to Basic Rules tab with full Galactic Conquest description

#### New Placeholder Assets
- `conquest.png` — 4K Stargate galaxy map with 70+ named canon planets, faction territories, cyan diamond markers
- `conquest_menu_bg.png` — Darker cinematic version with StarCraft-style border frame
- `deck_building_conquest_bg.png` — Purple energy beam interior with golden Goa'uld ornate framing

#### New Package: `galactic_conquest/`
- `__init__.py` — Entry point: `run_galactic_conquest(screen, unlock_system)`
- `campaign_state.py` — CampaignState dataclass with serialization
- `campaign_persistence.py` — Save/load/clear campaign JSON via XDG data paths
- `campaign_controller.py` — Main orchestrator: turn loop, attacks, AI counterattacks, deck viewer, run info
- `galaxy_map.py` — GalaxyMap with procedural generation, Planet dataclass, adjacency graph
- `map_renderer.py` — Galaxy map renderer with planet clicks, HUD, button interactions
- `conquest_menu.py` — StarCraft-style submenu: New Run / Resume / Back
- `faction_setup.py` — Faction + leader selection for campaign start
- `reward_screen.py` — Post-victory card picks with planet control tier scaling
- `neutral_events.py` — 7 text events with roguelite choices
- `card_battle.py` — Card battle wrapper using existing game loop

#### Files Modified
- `deck_builder.py` — Conquest mode integration: `conquest_save_callback`, `preset_faction/leader/deck_ids`, conquest-specific background loading, penalty exemption display
- `scripts/create_placeholders.py` — Three new background generators
- `stats_menu.py` — Added Conquest tab (6th tab) with campaign statistics and achievements
- `docs/rules_menu_spec.md` — Added Game Modes and Galactic Conquest descriptions
- `main_menu.py` — Added "GALACTIC CONQUEST" menu option
- `game_setup.py` — Added routing for galactic_conquest action
- `save_paths.py` — Added campaign save path

---

### Version 8.0.0 (February 2026)
**Major Content & Co-op Overhaul — New Enemies, Environmental Hazards, Ally Ships, Faction Powerups, LAN Independent Cameras**

#### 7 New Stargate-Themed Enemies with Unique AI Behaviors
- **Wraith Dart** (swarm_lifesteal): weaving approach in groups of 3-5, heals on contact damage
- **Replicator** (split_on_death): splits into 2 smaller copies on death, max 2 generations deep
- **Ori Fighter** (shielded_charge): extra golden shield bar; when shields break, enters zealous charge at 1.5x speed
- **Ancient Drone** (homing): smooth angular pursuit with 5 deg/frame turn rate, orbits target
- **Death Glider** (paired): always spawns in pairs, tries to stay near its partner
- **Al'kesh Bomber** (bomber): stays at 400px range, drops AreaBomb projectiles (2s fuse, 120px AoE, 30 dmg)
- **Wraith Hive** (mini_boss_spawner): mini-boss that orbits at 500px and spawns wraith darts (max 4 active)
- Themed explosion palettes: wraith purple, replicator silver sparks, ori holy gold, ancient golden sparkle
- Flash frame effect on all explosions (white pop on frames 0-2)
- Secondary chain-explosions for bosses and wraith hive kills

#### Sun/Wormhole Environmental Hazard
- **Sun entity** with 5 lifecycle phases: Growing (1s) → Stable (3s) → Exploding (0.5s) → Wormhole (5s) → Closing (0.5s)
- **Gravity pull** during wormhole phase affects ships, enemies, allies, projectiles, asteroids within 300px
- 2 DPS damage at inner 50px core
- First sun spawns at 30s, then every 40-60s at random 600-1000px from player
- Screen shake on explosion phase

#### Summon Ally Ship System
- New **summon_ally** upgrade (epic rarity, max 3 stacks, +5s duration per stack)
- Ally ships follow owner within 250px, engage nearest enemy within 400px, auto-fire lasers
- Green "ALLY" label above allied ships
- Enemy projectiles can hit allies (no friendly fire from player)

#### 15 New Faction Power-ups
- **Tau'ri**: F-302 Squadron (epic, 3 ally ships), Prometheus Shield (epic, absorb 200 dmg + 50% reflect), Ancient Tech (legendary, piercing + homing)
- **Goa'uld**: Kull Warrior (epic, invuln + 2x dmg), Hand Device (epic, stun 300px/3s), Ribbon Device (legendary, drain HP beam)
- **Asgard**: Time Dilation (epic, 25% enemy speed), Matter Converter (epic, convert 5 enemies to XP), Replicator Disruptor (legendary, chain-kill all same-type)
- **Jaffa**: Tretonin (epic, double HP regen), Rite of M'al Sharran (epic, full heal if <30% HP), Free Jaffa Rally (legendary, 5 ally ships)
- **Lucian**: Smuggler's Luck (epic, 2x drop rate), Black Market (epic, 2 random upgrade stacks), Kassa Stash (legendary, 3x fire + speed + invuln)

#### LAN Co-op Overhaul
- **Independent cameras**: host follows P1, client follows P2 (no more forced midpoint)
- **Leash distance** increased from 800 to 5000px for true roaming freedom
- **Despawn** based on nearest alive player, not camera center
- **Expanded state snapshot**: enemies 30→60, plus projectiles (100), powerups (20), XP orbs (50), explosions (20), suns, allies, area bombs, active powerup timers
- **Client renders all entities**: projectiles, powerups, XP orbs, explosions, suns, ally ships, area bombs
- **Partner arrow** with distance indicator on client
- **Partner secondary fire** (E key) now works — replaces TODO stub
- **Graceful disconnection**: heartbeat + disconnect message types, host continues solo on client drop, client shows "Host Disconnected" overlay
- **Revival invulnerability**: 3s invuln on revive to prevent instant re-death
- **Improved _on_enemy_killed**: themed explosions, replicator split, powerup drop with faction, smuggler's luck bonus

#### Arcade Button Visual Upgrade
- Draft mode ARCADE button now uses `assets/icons/siege.png` image instead of procedural drawing
- Hover brightening effect on the icon

#### Bug Fixes
- Fixed `_damage_enemy()` not wired into projectile collision loop (Ori fighter shields never worked)
- Fixed sun spawn timer using random-every-frame instead of fixed threshold
- Fixed co-op explosion tiers using integers (2, 0) instead of strings ("large", "normal")
- Fixed co-op `_on_enemy_killed` creating PowerUp without faction (no faction-specific drops)
- Fixed co-op `_kill_player` not guarding against double-death
- Wired `_damage_enemy()` into all 15+ enemy damage call sites for consistent Ori shield handling

#### Files Modified/Created
- `space_shooter/upgrades.py` — 7 new enemy types with behaviors + ENEMY_EXPLOSION_PALETTES + summon_ally upgrade
- `space_shooter/ship.py` — 6 behavior AI methods + ally AI + behavior attributes + Ori shield bar
- `space_shooter/spawner.py` — New enemies in difficulty tiers + paired/swarm spawning
- `space_shooter/projectiles.py` — AreaBomb class for Al'kesh bomber
- `space_shooter/entities.py` — Sun class (5 phases) + 15 new PowerUp.TYPES + enhanced Explosion (palettes, flash, secondary)
- `space_shooter/game.py` — All new entity loops, _damage_enemy integration, sun/ally/bomb management, 15 powerup handlers
- `space_shooter/coop_game.py` — Independent P1 camera, expanded snapshot, fire_partner_secondary, nearest-player despawn, improved revival
- `space_shooter/coop_client.py` — Independent P2 camera, full entity rendering, partner arrow with distance, disconnect overlay
- `space_shooter/coop_protocol.py` — HEARTBEAT + DISCONNECT message types
- `space_shooter/__init__.py` — Partner secondary fire wired, disconnect handling
- `space_shooter/camera.py` — get_spawn_ring_for_coop() for dual viewports
- `draft_controller.py` — Arcade button uses siege.png icon image

---

### Version 7.5.0 (February 2026)
**LAN Co-op Arcade + Replicator Animation + Leader Quotes**

#### LAN Co-op Space Shooter (Part A)
- **Two-player co-op arcade** over LAN — host-authoritative with state snapshots at 20 Hz
- **Shared camera** follows midpoint between both players, with soft leash warning at 800px
- **Revival mechanic** — when one player dies they become a ghost; surviving player revives them by killing any enemy (respawn at 50% HP/shields)
- **Shared scoring** — combined score, XP pool, and upgrades benefit both ships equally
- **Host picks upgrades** on level-up; client sees "Host choosing upgrade..." notification
- **Partner indicator arrow** when co-op partner is off-screen
- **Dual health bars** — P1 top-left, P2 top-right with health + shield display
- **CO-OP ARCADE button** in LAN menu chat screen for quick access
- New files: `coop_game.py`, `coop_client.py`, `coop_protocol.py`, `coop_ui.py`, `virtual_keys.py`, `lan_coop_arcade.py`

#### Arcade Menu Entry in Draft Mode (Part B)
- **Prominent ARCADE button** in draft mode, no longer just a tiny 60x60 icon
- **Unlock condition**: visible when unlock override is enabled OR player has achieved a draft victory
- LAN mode launches co-op flow; solo launches single-player space shooter

#### Replicator Swarm Animation Overhaul (Part C)
- **120 swarming spider-bots** (up from 60) with clustered group spawning and swarm AI
- **Hexagonal body** with metallic variation per spider and glowing red/orange eyes
- **3-segment leg articulation** with proper joint bending and walking animation
- **Spark particle trails** behind each spider
- **Swarm AI**: spiders cluster into groups, spread, and reform for organic movement
- **GPU shader**: metallic shimmer bloom, chromatic aberration near swarm center, ripple distortion
- Fixed double `surface.blit(overlay)` bug

#### Leader Matchup Battle Quotes (Part D)
- **14 new specific matchup quotes**: Daniel vs Ba'al, Carter vs Anubis, Carter vs Thor, Teal'c vs Ba'al, Teal'c vs Anubis, O'Neill vs Sokar, O'Neill vs Hathor, Daniel vs Vala, Hammond vs Anubis, Bra'tac vs Ba'al, Bra'tac vs Gerak, Thor vs Ba'al, Vala vs Ba'al, O'Neill vs Gerak
- **7 new faction fallbacks**: Tau'ri vs Jaffa, Tau'ri vs Asgard, Jaffa vs Asgard, Lucian vs Goa'uld, Lucian vs Jaffa, Lucian vs Asgard, Lucian vs Tau'ri
- **Fixed** Lucian Alliance leaders not being detected by `get_faction()`
- **Removed** duplicate Bra'tac vs Apophis entry

#### Files Modified/Created
- `space_shooter/coop_game.py` — CoopSpaceShooterGame subclass (~500 lines)
- `space_shooter/coop_client.py` — Client-side renderer (~250 lines)
- `space_shooter/coop_protocol.py` — Co-op message types (~65 lines)
- `space_shooter/coop_ui.py` — Dual health bars, partner arrow, revival UI (~150 lines)
- `space_shooter/virtual_keys.py` — Network input translation (~55 lines)
- `space_shooter/__init__.py` — Added `run_coop_space_shooter()` entry point
- `space_shooter/camera.py` — Added `follow_midpoint()` method
- `space_shooter/spawner.py` — Added `coop_scale` factor
- `space_shooter/ship.py` — Renamed `player_ship` → `target_ship` in `update_ai()`
- `lan_coop_arcade.py` — Top-level co-op lobby flow (~120 lines)
- `lan_menu.py` — Added CO-OP ARCADE button in chat state
- `draft_controller.py` — Prominent ARCADE button, broader unlock check, LAN co-op support
- `animations.py` — Rewrote ReplicatorCrawlEffect with swarm AI, hexagonal bodies, GPU params
- `shaders/replicator_swarm.py` — New GLSL shader for metallic shimmer + chromatic aberration
- `shaders/__init__.py` — Registered replicator_swarm shader
- `frame_renderer.py` — Added replicator_swarm handler in `_apply_gpu_params()`
- `leader_matchup.py` — 14 new matchup quotes, 7 faction fallbacks, Lucian detection fix

---

### Version 7.4.0 (February 2026)
**Bug Hunt & Performance — Gameplay Fixes, Per-Frame Allocation Cleanup, Safety Hardening**

#### Gameplay Bug Fixes

- **Fire rate powerup restoration** — `rapid_fire` and `overcharge` powerups now save the original fire rate before modifying it. On expiration, the saved value is restored instead of reversing the math (which could give wrong values when the `max()` clamp activated or both powerups were stacked)
- **Drone 2D aiming** — Drones now calculate a proper 2D direction vector `(dx/dist, dy/dist)` toward the nearest enemy instead of only firing horizontally (left/right)
- **Mulligan card.rect crash guard** — Added `hasattr(card, 'rect')` check before `collidepoint()` in the mulligan click handler, preventing crashes if a card hasn't been rendered yet
- **Temporal field speed restoration** — When temporal field upgrades are at 0 stacks and time warp is inactive, all slowed enemies now have their `_base_speed` properly restored and the attribute cleaned up
- **Projectile budget cap** — Multi-targeting and scatter shot spawning now stops when total projectiles exceed 300, preventing frame drops with bullet_hell evolution + scatter_shot at fast fire rates

#### Performance (Per-Frame Allocation Cleanup)

- **Command bar surface cached** — The command bar `pygame.Surface` is now created once and reused every frame instead of being allocated fresh each render pass
- **Screen shake surface cached** — The shake draw surface is created once as `_shake_surface` and reused during any screen shake
- **Damage number text cached** — `DamageNumber` now pre-renders its text surface in `__init__()` and reuses it in `draw()` with `set_alpha()`, eliminating per-frame font rendering
- **Drone surface cached** — Drone polygon surface is rendered once as a class-level `_cached_surf` instead of being redrawn every frame
- **Level-up font cached** — "LEVEL UP!" text uses a fixed-size font rendered once, with the pulse effect applied via `pygame.transform.smoothscale` instead of recreating the font every frame
- **Drag trail O(N) removal fixed** — Replaced `list.remove()` inside a loop (O(N) per removal) with a single list comprehension filter

#### Safety & Robustness

- **LAN host socket leak fixed** — `bind()`/`listen()`/`accept()` wrapped in try/except so the listener socket is always closed on failure
- **LAN join socket leak fixed** — `connect()`/`_start()` wrapped in try/except so the connection socket is always closed on failure
- **Deck save error propagated** — `save_decks()` now returns `True`/`False` so callers can detect save failures
- **Mulligan iteration limit removed** — Removed the arbitrary 1000-iteration cap; the time-based timeout is sufficient and correct

#### Files Modified
- `space_shooter/game.py` — Fire rate save/restore, temporal field cleanup, projectile budget cap, shake surface cache
- `space_shooter/entities.py` — Drone 2D direction fix, drone surface cache, damage number text cache
- `space_shooter/ui.py` — Level-up font cache
- `event_handler.py` — hasattr guard on card.rect in mulligan
- `frame_renderer.py` — Command bar surface cache
- `main.py` — Drag trail list comprehension, mulligan iteration limit cleanup
- `lan_session.py` — Socket leak fixes for host and join
- `deck_persistence.py` — save_decks() returns bool

---

### Version 7.3.0 (February 2026)
**Audio & UI Polish — Chevron SFX, Back Button Feedback, Options Layout Fix & Volume Defaults**

#### Rule Compendium Chevron Sound
- **`rule_chevron.ogg`** plays when clicking any red chevron tab in the Rule Compendium
- Lazy-loaded with class-level caching, respects Effects volume setting

#### Back Button Click Sound
- **`menu_select.ogg`** now plays on back button click across all menus:
  - Options menu, Settings menu, Stats menu, Deck Builder (all 3 states: faction select, leader select, deck review)
- Provides tactile audio feedback for navigation

#### Post-Stargate Transition Sound
- **`menu_enter.ogg`** plays after the Stargate opening animation finishes, right before the faction selection screen appears

#### Options Menu Layout Fix
- Fixed volume sliders overlapping with Fullscreen Mode toggle
- Increased spacing between slider section and toggle section (+60px at 1080p)
- Slightly reduced Stargate toggle size for tighter fit
- Increased panel height to accommodate the improved layout
- Geometry refresh on fullscreen toggle now matches the corrected layout

#### Updated Volume Defaults
- **Master**: 100% (was 70%) — full volume by default, users scale sub-channels
- **Music**: 50% (was 70%) — background music at comfortable level
- **Voice**: 60% (was 70%) — leader/commander voices clearly audible
- **Effects**: 40% (was 70%) — SFX less intrusive out of the box

#### Files Added
- `assets/audio/rule_chevron.ogg` — Rule Compendium chevron click sound

#### Files Modified
- `rules_menu.py` — Added `_play_chevron_sound()` with lazy-loaded class-level cache, called from `_activate_chevron()`
- `main_menu.py` — Options panel height increased (950→1040), slider-to-toggle gap widened (40→100), toggle radius reduced (50→45), back button plays menu_select.ogg
- `game_setup.py` — Play menu_enter.ogg after Stargate opening animation, before faction selection
- `game_settings.py` — Updated default volumes (master 1.0, music 0.5, sfx 0.4, voice 0.6), back button plays menu_select.ogg
- `deck_builder.py` — Added `_play_menu_select_sound()` helper, back button click sound on all 3 states
- `stats_menu.py` — Back button plays menu_select.ogg

---

### Version 7.2.0 (February 2026)
**Audio Overhaul — Granular Volume Controls, Deck Builder Music & Menu UI Sounds**

#### Granular Volume Sliders
- **4 independent volume sliders** in Options menu — Master, Music, Voice, and Effects, each with unique color-coded gradient (blue, teal, amber, purple)
- **Voice volume** controls leader voice clips and commander snippets separately from sound effects
- **Effects volume** controls gameplay SFX (card placement, abilities, weather, etc.)
- **Master volume** still scales all audio globally
- Both the main menu Options panel and the in-game Settings menu support all 4 sliders
- Settings persist to `game_settings.json` with backwards-compatible migration

#### Deck Builder Background Music
- **`deck_building.ogg`** plays as a continuous loop when entering the deck builder
- Faction theme previews temporarily replace the deck building music when hovering factions
- Music automatically resumes when un-hovering — seamless transitions
- Cleanly stops when leaving the deck builder; main menu music resumes

#### Menu UI Sound Effects
- **`menu_select.ogg`** plays when hovering over a new main menu option (mouse or keyboard navigation)
- **`menu_enter.ogg`** plays when clicking or pressing Enter on a menu option
- Hover sound only triggers on **transitions** (not every frame) for clean audio
- Both sounds respect the Effects volume setting

#### Space Shooter: Shield Hit Sound
- **`shield_hit.ogg`** plays when the player's shield absorbs damage
- Lazy-loaded with class-level caching for performance
- Only triggers for the player ship (not enemies)

#### Files Added
- `assets/audio/deck_building.ogg` — Deck builder background music
- `assets/audio/menu_select.ogg` — Menu hover sound effect
- `assets/audio/menu_enter.ogg` — Menu enter/click sound effect
- `assets/audio/space_shooter/shield_hit.ogg` — Shield hit sound effect

#### Files Modified
- `game_settings.py` — Added `voice_volume` setting (default 0.7), getter/setter, `get_effective_voice_volume()`, updated legacy settings menu to 4 sliders
- `sound_manager.py` — Added `_get_effective_voice_volume()`, commander snippets and leader voices now use voice volume instead of SFX volume
- `main_menu.py` — Options menu rewritten with 4 color-coded volume sliders (Master/Music/Voice/Effects), menu hover + enter sound effects, taller panel layout
- `deck_builder.py` — Added `start_deck_building_music()`, `_resume_deck_building_music()`, `stop_deck_building_music()`, faction theme un-hover resumes deck music
- `space_shooter/ship.py` — Added `_play_shield_hit_sound()` with lazy-loaded class-level sound cache, called on shield damage absorption

---

### Version 7.1.0 (February 2026)
**Space Shooter Overhaul — Vampire Survivors-Style Infinite Survival**

#### Infinite World & Camera System
- **Camera system** — Smooth-following camera that tracks the player through an infinite world (no screen boundaries)
- **Continuous spawner** — Replaces 20-wave system with time-based difficulty scaling across 10 tiers (Calm → Warming Up → Skirmish → Engaged → Intense → Overwhelming → Onslaught → Apocalypse → Extinction → Beyond)
- **Infinite tiling starfield** — 3-layer parallax stars, nebulae, and speed lines tile seamlessly in all directions
- **Entity lifecycle** — Distance-based despawning (2500px from camera center), visibility culling for draw optimization

#### Secondary Fire System (E Key)
- **Tau'ri — Railgun**: Fast piercing shot that passes through multiple enemies (3s cooldown)
- **Goa'uld — Staff Barrage**: 3-shot fan spread of lasers (4s cooldown)
- **Asgard — Ion Pulse**: AoE damage burst + knockback around ship (5s cooldown)
- **Jaffa Rebellion — War Cry**: 4-second buff: +50% damage + doubled fire speed (6s cooldown)
- **Lucian Alliance — Scatter Mines**: Drops 4 proximity mines behind ship that explode near enemies (3.5s cooldown)

#### Faction-Styled Thrusters
- **Tau'ri**: Clean blue-white chemical exhaust (F-302 style)
- **Goa'uld**: Fiery gold/orange plasma (Ha'tak engines)
- **Asgard**: Cool cyan energy diamonds (sleek, minimal)
- **Jaffa Rebellion**: Hot orange/red staff-weapon exhaust
- **Lucian Alliance**: Purple/pink smuggler engines (flashy, unstable)
- **Thruster boost**: Hold SHIFT for 60% speed boost with enhanced particle effects (drains energy bar, recharges when not boosting)

#### Buttery Smooth Movement
- **Velocity-based movement** — Acceleration (1.2/frame) + friction (0.88 decay) replaces instant position changes
- **Diagonal normalization** — No speed advantage moving diagonally
- **Velocity-based facing** — Ship facing smoothly follows movement direction
- **Dead zone** — Sub-0.1 velocities zeroed to prevent infinite drifting

#### Enhanced Power-Up System
- **Drop rate increased** to 50% (was 15%) on enemy kill
- **Periodic spawns** — Random power-up appears near player every 4-7 seconds
- **3 new generic power-ups**: Overcharge (triple fire rate for 8s), Time Warp (65% enemy slow for 7s), Magnetize (pull all orbs + pickups for 6s)
- **10 faction-specific power-ups** — 1 Epic + 1 Legendary per faction, each with unique effects:
  - Asgard: Beam Array (Epic — beams in 4 directions), Mjolnir Strike (Legendary — lightning all enemies)
  - Tau'ri: Railgun Barrage (Epic — auto-fire railguns), Ancient Drone Swarm (Legendary — 8 super drones)
  - Goa'uld: Sarcophagus (Epic — full heal + invulnerability), Ha'tak Bombardment (Legendary — orbital strikes)
  - Jaffa: Blood of Sokar (Epic — 3x damage + life steal), Jaffa KREE! (Legendary — invulnerable + 3x damage)
  - Lucian: Kassa Overdose (Epic — enemies damage each other), Naquadria Bomb (Legendary — massive AoE)
- **Rarity glow effects** — Epic power-ups have purple glow rings, Legendary have golden starburst
- **Icon-based visuals** — Power-ups display faction icon images from assets/icons/

#### Evolution Upgrade System
- **5 new upgrades**: Orbital Laser (Epic), Nova Burst (Epic), Naquadah Bomb (Epic), Temporal Field (Rare), Ancient Knowledge (Common)
- **Legendary rarity** — New gold tier for evolution upgrades
- **5 Evolution combos**: Thor's Hammer (Chain Lightning + Weapons Power), Bullet Hell (Multi-Targeting + Rapid Capacitors), Black Hole (Gravity Well + Nova Burst), Ancient Outpost (Orbital Defense + Shield Harmonics), Cluster Bomb (Naquadah Bomb + Scatter Shot)

#### Balanced Combat
- **Enemy fire rate dramatically reduced** — Regular enemies fire every 6-11 seconds (was 1.3-2.3s), bosses 2-3x slower across all phases
- **Player stat boost** — Base HP/Shields raised to 150 (was 100), +15% base damage multiplier
- **Player empowerment** — Fast level-ups, frequent power-ups, and powerful upgrades make the player feel like a force of nature

#### Audio
- **Background music loop** — `space_shooter.ogg` plays on infinite loop during gameplay, respects music volume setting, fades in/out on game start/exit
- **Per-faction hit SFX** — Faction-specific sound plays on enemy hit with 0.5s cooldown (Asgard, Tau'ri; Goa'uld/Jaffa/Lucian ready for drop-in)
- **Thruster boost SFX** — `boost_space_shooter.ogg` plays once on SHIFT boost activation

#### UI Updates
- **Survival timer** (MM:SS) replaces wave counter
- **Difficulty tier label** with color coding
- **Secondary fire cooldown bar** with ready/active/cooldown states
- **Thruster boost energy bar** with SHIFT label
- **Wider mini-radar** showing 3000x2200 world area with camera viewport outlined

#### Files Added
- `space_shooter/camera.py` — Camera class with smooth follow, world_to_screen, culling, spawn ring
- `space_shooter/spawner.py` — ContinuousSpawner with 10 difficulty tiers and time-based scaling
- `assets/audio/space_shooter/` — New audio directory: background music loop, per-faction hit SFX, boost SFX

#### Files Modified
- `space_shooter/game.py` — Major rewrite: camera integration, spawner, wave removal, secondary fire, new upgrades, mine/ion_pulse systems, war cry buff, piercing projectiles
- `space_shooter/ship.py` — Velocity-based movement, secondary fire system, faction thruster configs, thruster boost, smooth facing
- `space_shooter/projectiles.py` — Added RailgunShot (piercing) and ProximityMine classes, camera support on all draw methods
- `space_shooter/entities.py` — 13 power-up types (3 generic + 10 faction-specific), rarity glow effects, icon-based PowerUp, camera support, tiered Explosion, world-space spawning
- `space_shooter/effects.py` — Infinite tiling StarField, ParticleTrail class, directional ScreenShake
- `space_shooter/upgrades.py` — 5 new upgrades, EVOLUTIONS dict, Legendary rarity
- `space_shooter/ui.py` — Survival timer, difficulty tier, secondary cooldown bar, boost bar, updated controls
- `space_shooter/__init__.py` — Background music lifecycle (start/stop/fade), updated docstring and return logic for survival mode
- `space_shooter/game.py` — Hit SFX on enemy collision, boost SFX on activation, player stat boosts, invulnerability system, faction powerup effects

---

### Version 7.0.0 (February 2026)
**Card Animation Polish + Tabbed Stats Menu Revamp**

#### Animation Polish

- **StargateActivationEffect — Faction Colors** — Portal rings and particles now match the playing faction's color (Tau'ri blue, Goa'uld gold, Jaffa bronze, Lucian purple, Asgard cyan) instead of hardcoded blue. Added event horizon shimmer (12 rotating radial lines during first 50%) and mild GPU distortion during first 40%
- **ZPMSurgeEffect — Particles, Lightning & Screen Flash** — Added 60 gold/cyan/white-gold burst particles, 4 jagged lightning arcs with glow+core rendering, white screen flash during first 120ms, and increased GPU surge radius from 250→300
- **AbilityBurstEffect — Per-Type Flourishes** — Each ability type now has a unique visual layered on top of the existing ring+particles:
  - Medic/Heal: Glowing green cross shape
  - Spy/Transport: 3 expanding ring-transport ellipses
  - Decoy/Recall: Chevron arrows shrinking toward center
  - Bond/Muster: Connecting lines from center to each particle
  - Scorch/Naquadah: Pulsing concentric danger circles

#### Tabbed Stats Menu

- **5-Tab Layout** — Stats menu restructured from single scroll into tabs: Overview, Factions, Leaders, Records, Draft
- **Independent Scroll Per Tab** — Each tab remembers its scroll position when switching
- **Keyboard Navigation** — Tab key cycles through tabs, 1-5 jump to specific tabs
- **New Score Records** — Tracks highest score, lowest score, biggest victory margin, closest game, and average score — each with the leader used
- **Section Reorganization** — Round Breakdown and LAN Reliability moved to Records tab; Faction Win Rates and Matchups in dedicated Factions tab; Top Leaders expanded to top 5 (was 3)

#### Score Tracking

- **Game summary** now includes `player_score` and `opponent_score` for end-of-game power totals
- **Persistent score records** in `deck_persistence.py` — all fields use `setdefault()` for safe migration of existing saves

#### Bug Fix

- **card_assembler.py** — Fixed crash when running outside pygame environment. Added mock `pygame.mouse` and `pygame.event` submodules to match `display_manager.py`'s module-level monkey-patching of mouse coordinate scaling

#### Files Modified
- `animations.py` — Polished StargateActivationEffect (faction colors, shimmer, GPU params), ZPMSurgeEffect (particles, lightning, flash), AbilityBurstEffect (per-type flourishes)
- `event_handler.py` — Pass `faction=game.player1_faction` at 8 StargateActivationEffect call sites
- `main.py` — Pass `faction=game.player2_faction` at 6 StargateActivationEffect call sites
- `frame_renderer.py` — Added player_score/opponent_score to game summary dict
- `deck_persistence.py` — Score records in record_game_summary(), get_stats(), reset_stats()
- `stats_menu.py` — Full tabbed layout restructure with 5 tabs, independent scroll, keyboard nav, new Records tab
- `scripts/card_assembler.py` — Added mock pygame.mouse and pygame.event for headless operation

---

### Version 6.9.0 (February 2026)
**GPU-Enhanced Transitions — Hyperspace Warp, Shockwave Impacts & Procedural Speed Lines**

#### Hyperspace Transition Overhaul
- **Hyperspace GPU shader now active during transitions** — The previously-registered-but-disabled hyperspace shader is now enabled and animated during round transitions, producing real-time radial motion blur, chromatic aberration, and tunnel vignette on top of the CPU-drawn star streaks
- **Procedural speed lines** — New shader-generated star streak lanes (~80 angular lanes) that move outward (entering) or inward (emerging), driven by time and warp factor, complementing the existing CPU star streaks
- **Directional warp** — Shader supports `direction` uniform: `1.0` for outward (entering hyperspace) and `-1.0` for inward (emerging), so blur and speed lines move in the correct direction
- **Card sweep integration** — When cards fly off the board ("up" direction), the hyperspace shader ramps from 0→0.6 warp, creating an accelerating radial blur as cards disappear, then cleanly hands off to the hyperspace transition
- **Smooth warp curves** — Entering hyperspace ramps 0→1 over 30% then sustains full warp; emerging decelerates 1→0.3→0 with an ease-out for a natural deceleration feel

#### Shockwave Impact Effect (New Shader)
- **New `shaders/shockwave.py`** — Expanding ring distortion with screen flash and chromatic aberration at the wavefront, used for dramatic impact moments
- **Round winner announcement** — Shockwave pulse expands over the first 40% of the animation (synchronized with the existing screen shake), with ring distortion fading as it reaches the screen edges
- **Game start animation** — Subtle shockwave pulse when "YOU GO FIRST" / "OPPONENT GOES FIRST" text appears, adding weight to the game start moment

#### Hyperspace Shader Improvements
- **Chromatic aberration** — Red/blue channel separation increases radially with warp factor, creating a color-fringing effect at high speeds
- **Tunnel vignette** — Screen edges darken at high warp, creating a tunnel vision effect that intensifies the feeling of speed
- **Center glow** — Bright blue-white core at the center during full warp
- **Blue-white energy overlay** — Additive energy wash that increases with warp factor and distance from center
- **12-sample radial blur** — Increased from 8 to 12 samples with tent-weighted filtering for smoother blur quality

#### Technical Details
- All GPU effects are safely enabled/disabled per-transition with proper cleanup on early exit (skip/quit)
- Graceful fallback: all transitions work identically without GPU — shader effects are purely additive
- New helper functions `_get_gpu()`, `_enable_effect()`, `_disable_effect()`, `_set_effect_uniform()` centralize safe GPU interaction in transitions.py

#### Files Modified
- `shaders/hyperspace.py` — Complete rewrite: added `time`, `direction` uniforms, procedural speed lines, chromatic aberration, tunnel vignette, center glow, loop bounds safety
- `shaders/shockwave.py` — New file: expanding ring distortion, flash, chromatic aberration at wavefront
- `shaders/__init__.py` — Registered shockwave effect (disabled by default, driven by transitions)
- `transitions.py` — GPU helper functions, hyperspace shader integration in card sweep + hyperspace transition, shockwave in round winner + game start animations, proper cleanup on all exit paths

---

### Version 6.8.0 (February 2026)
**GPU Fullscreen Overhaul, MALP Feed CRT Scanlines & Stability Fixes**

#### GPU Fullscreen Mode
- **Fixed fullscreen resolution** — GPU mode now creates the OpenGL display at desktop resolution (e.g. 3840x2160) instead of internal render resolution (2560x1440), with the GPU renderer upscaling via fullscreen quad
- **Fixed fullscreen viewport** — `gpu_renderer.present()` now uses `pygame.display.get_window_size()` instead of `get_surface().get_size()` which reported incorrect dimensions for OpenGL windows
- **Fixed mouse coordinate scaling** — Monkey-patched `pygame.mouse.get_pos()` and `pygame.event.get()` in `display_manager.py` to automatically scale mouse coordinates from window space to game space in GPU fullscreen mode (non-GPU mode uses `pygame.SCALED` which handles this natively)
- **Fixed fullscreen toggle exit** — Added `pygame.event.clear()` + `break` after every fullscreen toggle path (F11 and mouse click) across all 6 event loops to prevent spurious QUIT events from Linux window manager display recreation
- **Fixed stale screen references** — After fullscreen toggle, `display_manager.screen` is a new surface but local `screen` variables in callers still pointed to the old one. Added `screen = display_manager.screen` refresh in `game_setup.py` (after menu, after deck builder), `main.py` (after init), and `main_menu.py` (after deck builder, after rules menu)

#### MALP Feed CRT Scanlines
- **Enabled CRT/Hologram GPU shader** on MALP Feed panel — scanlines, static noise, green tint, flicker, and chromatic aberration now render in real-time via the GPU pipeline
- **Fixed panel_rect uniform** — The CRT shader's `panel_rect` was never being set from frame_renderer (stayed at 0,0,0,0), so the effect region was empty. Now correctly passes the MALP feed panel rect in UV space every frame

#### Bug Fixes
- **Fixed GPU cleanup double-release** — `gpu_renderer.cleanup()` was releasing each shader pass VAO twice (once explicitly, then again inside `ShaderPass.cleanup()`), causing `'NoneType' object has no attribute 'release'` error on fullscreen toggle and game exit
- **Fixed options menu recursion** — Fullscreen toggle in options menu used recursive `return self.run_options_menu()` which could propagate stale return values. Replaced with in-place geometry refresh using `needs_geometry_refresh` flag

#### Files Modified
- `display_manager.py` — Mouse coordinate scaling monkey-patches, desktop resolution for GPU fullscreen, event clearing in `toggle_fullscreen_mode()`
- `gpu_renderer.py` — `present()` viewport fix with `get_window_size()`, cleanup double-release fix
- `frame_renderer.py` — CRT panel_rect uniform update moved before early return, runs every frame
- `shaders/__init__.py` — CRT/Hologram effect enabled by default
- `main_menu.py` — Options menu geometry refresh, screen refresh after sub-menus, event clearing on all toggle paths
- `event_handler.py` — Event clearing after F11 toggle
- `deck_builder.py` — Event clearing after F11 toggle
- `rules_menu.py` — Event clearing after F11 toggle
- `game_setup.py` — Screen refresh after menu and deck builder returns
- `main.py` — Screen refresh after `initialize_game()` returns

---

### Version 6.5.1 (February 2026)
**Lucian Alliance Card Rework, Border Fix & Art Credits**

#### Lucian Alliance Card Rework
- **Hero renames** — Vulkar → Varro (`lucian_varro`), Sg. Curtis → Netan (`lucian_netan`)
- **Card renames** — Ch'ulak Loyalist → Bounty Hunter (`lucian_bounty`), Agent Tyrus → Simeon (`lucian_simeon`), Vannesa → Kiva (`lucian_kiva`)
- **Row changes** — Sodan Master: ranged → agile; Alliance Mercenary: close → ranged; Sodan Warrior: ranged → agile
- **Balance changes** — Alliance Mercenary 3→8, Kiva (was Vannesa) 7→2, Odyssey Spy 9→1, Sodan Warrior 6→8, Medics 5→3, Ship Mechanic 0→2
- **New card art** — AI-generated portraits for all 37 Lucian Alliance cards assembled via card_assembler pipeline

#### Bug Fixes
- **Fixed Lucian Alliance & Goa'uld card borders** — Both faction border PNGs were missing the outer metallic frame (~3-4px thick around all edges), causing assembled cards to have visible gaps at the edges. Restored the missing frame pixels (1,939 for Lucian, 2,411 for Goa'uld) by copying the faction-neutral dark gray frame from a working border
- **Fixed card_assembler.py pygame mock** — The mock pygame module used to avoid needing a real display was missing `pygame.init` and `pygame.key.set_repeat` stubs, causing `AttributeError` when `display_manager.py` was imported through the `unlocks` → `display_manager` chain

#### Art Credits
- Card portrait art generated with [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) by Tongyi-MAI and [Disco Elysium](https://civitai.com/models/1433982/disco-elysium) style model

#### Files Modified
- `cards.py` — Lucian Alliance hero renames, card renames, row changes, balance changes
- `assets/lucian_*.png` — Reassembled all 37 Lucian Alliance card images with new art
- `assets/card_assembler/borders/lucian-border.png` — Restored outer metallic frame
- `assets/card_assembler/borders/goauld-border.png` — Restored outer metallic frame
- `scripts/card_assembler.py` — Added `mock_pg.init` and `mock_key.set_repeat` no-op stubs to pygame mock

---

### Version 6.5.0 (February 2026)
**GPU Post-Processing with ModernGL**

#### GPU Rendering Pipeline (`gpu_renderer.py`)
- **Shared OpenGL context** -- Display created with `pygame.OPENGL | pygame.DOUBLEBUF`, game draws to offscreen surface, GPU renders final result directly to default framebuffer via fullscreen quad (no CPU readback)
- **ShaderPass / FBOPool architecture** -- Reusable framebuffer pool, per-pass VAOs, automatic resource management
- **Graceful fallback chain** -- moderngl not installed → pure Pygame; context fails → reverts to `pygame.SCALED`; shader fails → effect disabled; runtime error → auto-reverts to Pygame for session; user setting → toggle off

#### 9 Shader Effects (`shaders/` package)
- **Bloom** (`shaders/bloom.py`) -- 3-pass bright extract → separable Gaussian blur (half-res) → additive composite with clamp. Auto-enhances all bright elements
- **Vignette** (`shaders/vignette.py`) -- Radial smoothstep edge darkening for cinematic depth
- **CRT/Hologram** (`shaders/crt_hologram.py`) -- Region-specific MALP panel effect: scanlines, static noise, green tint, flicker, chromatic aberration
- **Distortion** (`shaders/distortion.py`) -- Up to 8 concurrent ring-shaped shockwave distortion points driven by animations
- **Event Horizon** (`shaders/event_horizon.py`) -- Procedural rippling portal with fbm noise, blue-white gradient, glowing edge ring
- **Kawoosh** (`shaders/kawoosh.py`) -- Cone-shaped vortex displacement with additive blue-white energy
- **Hyperspace** (`shaders/hyperspace.py`) -- Radial motion blur with blue-white streak overlay
- **Asgard Beam** (`shaders/asgard_beam.py`) -- Vertical volumetric light column with downward scan line and shimmer
- **ZPM Surge** (`shaders/zpm_surge.py`) -- Procedural multi-octave lightning arcs with cyan-white energy

#### Animation→GPU Bridge
- **`get_gpu_params()`** on StargateOpeningEffect, NaquadahExplosionEffect, AsgardBeamTransportEffect, ZPMSurgeEffect
- **`AnimationManager.collect_gpu_params()`** -- Aggregates GPU parameters from all active effects
- **`frame_renderer._apply_gpu_params()`** -- Maps animation state to shader uniforms each frame

#### GPU Settings (`game_settings.py`)
- `gpu_enabled`, `bloom_enabled`, `bloom_intensity`, `bloom_threshold`, `vignette_enabled`, `shader_quality` (low/medium/high)

#### Display Pipeline (`display_manager.py`)
- **`gpu_flip()`** -- Routes all 30 flip calls across 15 files through GPU post-processing or plain Pygame
- **`initialize_gpu()`** -- Sets OpenGL attributes, recreates display with `pygame.OPENGL`, creates offscreen surface, shared context creation, validation, effect registration
- **Runtime fallback** -- If GPU fails mid-session, auto-reverts to `pygame.SCALED` rendering
- **Fullscreen toggle** -- Destroys/recreates entire GL context and re-registers all effects seamlessly

#### Files Created
- `gpu_renderer.py` -- GPURenderer, ShaderPass, FBOPool core
- `shaders/__init__.py` -- Package init with `register_all_effects()`
- `shaders/bloom.py`, `shaders/vignette.py`, `shaders/crt_hologram.py`, `shaders/distortion.py`
- `shaders/event_horizon.py`, `shaders/kawoosh.py`, `shaders/hyperspace.py`, `shaders/asgard_beam.py`, `shaders/zpm_surge.py`

#### Files Modified
- `display_manager.py` -- Added `gpu_renderer` global, `initialize_gpu()`, `gpu_flip()`
- `game_settings.py` -- Added 6 GPU settings with getters/setters
- `main.py` -- GPU init, update(dt) in game loop, cleanup on exit
- `frame_renderer.py` -- `_apply_gpu_params()`, replaced flip call
- `animations.py` -- `get_gpu_params()` on 4 effects, `collect_gpu_params()` on AnimationManager
- `transitions.py`, `main_menu.py`, `stats_menu.py`, `rules_menu.py`, `deck_builder.py`, `unlocks.py`, `lan_game.py`, `lan_lobby.py`, `lan_menu.py`, `draft_controller.py`, `space_shooter/__init__.py` -- Replaced `pygame.display.flip()` with `display_manager.gpu_flip()`
- `requirements.txt` -- Added `moderngl`

---

### Version 6.4.0 (February 2026)
**Art Assembly Pipeline, Rarity Name Plates & Avenger Token Art**

#### Art Assembler — Full Asset Pipeline (`scripts/card_assembler.py`)
- **Leader portraits** -- `raw_art/{card_id}_leader.png` → `assets/{card_id}_leader.png` (200x280, stretched)
- **Leader backgrounds** -- `raw_art/leader_bg_{card_id}.png` → `assets/leader_bg_{card_id}.png` (3840x2160, stretched)
- **Faction backgrounds** -- `raw_art/faction_bg_{faction}.png` → `assets/faction_bg_{faction}.png` (3840x2160, stretched)
- **Lobby background** -- `raw_art/lobby_background.png` → `assets/lobby_background.png` (3840x2160, stretched)
- **Each asset has its own raw art** -- Card art, leader portrait, leader background, faction background, and lobby background are all separate source images with unique filenames
- **Stretch-to-fit** -- Raw art is always stretched (not cropped) to exactly fit the target dimensions
- **Rarity name plate overlay** -- Name plate bar reflects card rarity from `unlocks.py` explicit rarity fields: blue (rare), purple (epic), gold (legendary). Cards without explicit rarity keep the original faction border color
- **Loads leader data** -- Imports `BASE_FACTION_LEADERS` and `UNLOCKABLE_LEADERS` from `content_registry.py` to identify which card_ids are leaders

#### Avenger Token Art
- **Clone Incubator art for Avenger tokens** -- The Asgard Avenger token spawned by Clone Incubator's "Activate Combat Protocol" now displays Clone Incubator card art instead of a blank grey rectangle

#### Files Modified
- `scripts/card_assembler.py` -- Art assembly pipeline: leader portraits, leader backgrounds, faction/lobby backgrounds, rarity name plates, stretch-to-fit
- `game.py` -- Set `avenger.image_path` in `trigger_summon_avenger()` to reuse Clone Incubator art

---

### Version 6.3.0 (February 2026)
**Card Assembler Pipeline — Automated Card Image Compositing**

New developer tool that automatically assembles finished card images from raw ComfyUI portrait art, eliminating manual per-card compositing in an image editor.

#### Card Assembler Script (`scripts/card_assembler.py`)
- **Automated compositing pipeline** -- Takes raw portrait art + card data from `cards.py` and layers: portrait, faction border, row icon, ability icons, power number, card name, and flavor text into finished 200x280 card PNGs
- **CLI interface** -- Assemble all cards, specific cards by ID, entire factions (`--faction tauri`), with `--no-overwrite`, `--dry-run`, and custom `--input`/`--output` directories
- **`--status` flag** -- Per-faction progress report classifying all 247 cards as "done" (real art >15KB), "ready" (has raw art in `raw_art/`), or "needs art" (placeholder only)
- **`--list-missing` flag** -- Lists all cards that still need raw portrait art
- **Smart portrait fitting** -- Auto-detects transparent cutout in border PNGs for portrait placement; center-crops raw art to match aspect ratio
- **Ability icon stacking** -- Parses comma-separated abilities, scales each icon to ~22px, stacks vertically on left bar
- **Auto-sized card names** -- Font shrinks automatically (13-7px) for long names to fit the name plate; black text
- **Word-wrapped flavor text** -- Optional quotes from `scripts/card_quotes.json` rendered in 13px black text in the parchment text box
- **Black text styling** -- Power number (24px), card name, and flavor text all render in black to match hand-crafted reference cards
- **Pygame-independent** -- Uses Pillow (PIL) with a lightweight pygame mock to import card data without requiring a display

#### New Asset Structure
- `assets/card_assembler/borders/` -- 6 faction border PNGs (copied from Dropbox)
- `assets/card_assembler/row_icons/` -- 4 high-res row icons (close, ranged, siege, agile)
- `assets/card_assembler/ability_icons/` -- 12 ability icons (Legendary Commander through Survival Instinct)
- `raw_art/` -- Input directory for ComfyUI portrait PNGs (named by card_id)
- `scripts/card_quotes.json` -- 18 starter Stargate quotes for flavor text

#### Files Created
- `scripts/card_assembler.py` -- Main assembler script (~350 lines)
- `scripts/card_quotes.json` -- Flavor text quotes mapping
- `assets/card_assembler/` -- Complete asset directory with borders, row icons, and ability icons
- `raw_art/` -- Empty input directory for user's ComfyUI art

#### Dependencies
- Added `Pillow` to `requirements.txt`

---

### Version 6.2.0 (February 2026)
**Bug Hunt, Performance & Code Quality Overhaul**

Deep audit and fix of 50+ issues across the entire codebase — crash-level bugs, broken features, game logic errors, space shooter fixes, performance optimizations, and code cleanliness improvements.

#### Critical Bug Fixes (Crashes & Broken Core Systems)
- **Double `end_round()` fixed** — AI passing triggered `switch_turn()` twice (once inside `pass_turn()`, once in main loop), awarding the opponent an extra round win; same issue fixed for LAN opponent path
- **Iris Defense visual fix** — When Iris blocked an AI card, the card-play animations still ran (stargate effect, hero fanfare) making it look like the card was successfully played; now shows Iris closing animation instead and skips all card-play visuals
- **Artifact system fixed** — `apply_effect()` was defined on the wrong class (`GameHistoryEntry` instead of `Artifact`); artifacts like Communication Stones crashed on use
- **Round winner no longer overridden** — `decrement_all_clone_tokens()` was resetting `current_player` to player1 every round, ignoring round-winner logic
- **Shared mutable singletons eliminated** — Both players of the same faction now get fresh faction ability/power instances instead of sharing a single mutable singleton
- **Draft game-over no longer crashes** — Fixed `NameError` for undefined `player_leader`/`player_deck` variables in the draft game-over renderer
- **LAN weather crash fixed** — Removed invalid `acting_player=` keyword argument from `apply_weather_effect()` call
- **Discard viewer no longer opens and closes on same click** — Changed sequential `if` blocks to `elif` with proper guard

#### Broken Feature Fixes
- **F3 debug toggle works** — Was creating a local variable instead of modifying `_main.DEBUG_MODE`
- **Tab key cycles correctly** — Fixed modular arithmetic that locked cursor at button 0 (could never reach faction power)
- **Mulligan timeout fires** — Timer was resetting every frame; now set once when mulligan phase begins
- **Ring transport overlay appears** — Was checking dead `state.ring_transport_selection` instead of `UIState.RING_TRANSPORT_SELECT`
- **Discard rect updates correctly** — Fixed wrong dict key `"state.discard_rect"` → `"discard_rect"`
- **Thor move ability is single-use** — Added `leader_ability_used` flag after Thor's move completes
- **No double stargate animation** — Removed duplicate `StargateActivationEffect` on normal unit cards

#### Game Logic Fixes
- **Quantum Mirror LAN-safe** — Changed `random.shuffle` to seeded `self.rng.shuffle` preventing LAN desync
- **Penegal revives units only** — Filtered out weather/special cards that would vanish when revived; agile cards now placed correctly
- **Loki drain is temporary** — Changed from modifying permanent `.power` to `.displayed_power`
- **Goa'uld power checks targets first** — No longer marked as used when there are no valid targets
- **Faction power activation deduplicated** — Extracted `_try_activate_faction_power()` helper replacing 4 inconsistent call sites
- **Selection overlays moved to event handler** — 7 overlays (Medic, Decoy, Jonas, Ba'al, Vala, Catherine, Thor) no longer handle clicks in the renderer via `get_pressed()`; uses proper `MOUSEBUTTONDOWN` events now
- **Anubis auto-scorch fires before winner** — Moved scorch application before round winner determination so it actually has an effect
- **Game-over check consistent** — Unified `game.game_over` vs `game.game_state == "game_over"` across all files

#### Space Shooter Fixes
- **Shields absorb all damage** — Shields now absorb weapon/beam/contact damage (was only blocking asteroids)
- **Drones aim at enemies** — Drones calculate direction toward nearest enemy instead of always firing right
- **GravityWell safe iteration** — Uses slice copy to avoid modifying enemy list during iteration
- **No splash double-kills** — Tracks already-killed enemies in a set to prevent double XP/score/streak
- **Rapid fire preserves upgrades** — Changed from base rate capture/restore to multiplier approach so upgrades taken during power-up aren't lost on expiry

#### Performance Optimizations
- **Font caching** — Added `get_font()` cache in `game_config.py`, replacing 13+ per-frame `pygame.font.SysFont()` OS lookups in the renderer
- **Mouse position cached** — `pygame.mouse.get_pos()` called once per frame instead of 14+ times
- **Rotation caching** — Ships and asteroids cache rotated sprites, only re-rotating when angle changes by >1-2 degrees
- **Surface allocation reduction** — Pre-allocated reusable surfaces for common overlays

#### Code Quality
- **No more recursive `main()` calls** — Replaced stack-overflow-prone recursive restarts with a loop-based `run_game()` wrapper
- **`_cleanup_round()` helper** — Extracted ~246 lines of duplicated cleanup logic from `end_round()` and `surrender()`
- **Mulligan comment fixed** — Changed incorrect "max 2" to "max 5"
- **Bare except removed** — Changed `except:` to `except Exception:` in card image loading
- **AI difficulty documented** — Added clarifying comment about always-hard difficulty setting

#### Files Modified
- `game.py` — Artifact system, clone tokens, shared singletons, weather crash, Quantum Mirror, Penegal, Loki, Anubis scorch, cleanup dedup
- `event_handler.py` — F3 toggle, Tab cycling, discard viewer, double stargate, faction power dedup, overlay click handling, recursive main
- `frame_renderer.py` — Draft game-over, ring transport, discard key, Thor ability, overlay refactor, font cache, mouse cache
- `main.py` — Faction powers singletons, mulligan timeout, game-over consistency, restart loop
- `game_loop_state.py` — Added `overlay_card_rects` and `restart_requested` fields
- `game_config.py` — Added `get_font()` font cache
- `power.py` — Goa'uld valid target check
- `space_shooter/ship.py` — Shield damage absorption, rotation caching
- `space_shooter/entities.py` — Drone aiming, GravityWell iteration, asteroid rotation cache
- `space_shooter/game.py` — Splash double-kill fix, rapid fire multiplier
- `cards.py` — Bare except fix

---

### Version 6.1.0 (February 2026)
**Asgard Faction Overhaul — Card Rework, Beam Animation & Audio**

Reworked the Asgard faction roster with renamed/rebalanced cards, a new Asgard Beam Tech unit with transporter beam animation and sound effect, and Thor promoted to Legendary Commander.

#### Asgard Card Changes
- **Thor** -- New hero card (Power 12, Siege) replacing Fifth (Asgard Android); has Legendary Commander + Inspiring Leadership
- **Asgard Beam Tech** (x3) -- Replaces Asgard Transport Ship (x2); ranged Gate Reinforcement unit with new beam-in animation
- **Asgard Healing Pod** -- Replaces Medical Bay Drone (renamed, same ability)
- **Asgard Elite** -- Replaces Asgard Elite Warrior (shortened name)
- **Energy Drone** -- Replaces Energy Pistol Drone; moved from ranged to siege row
- **Asgard Scientist** -- Moved from close to ranged row
- **Freyr** -- Ability changed to Legendary Commander (lost Deploy Clones)
- **Loki** -- Gained Deploy Clones ability
- **Asgard Defense Platform** -- Power buffed from 4 to 7
- **Daedalus-Class Ship** (x2) -- Power buffed from 6 to 8
- **Total card count**: 247 (up from 246, net +1 from 3rd Beam Tech)

#### New Animation: Asgard Transporter Beam
- **AsgardBeamTransportEffect** -- Bright white-blue column of light materializes from above, peaks with a blinding flash, then fades with shimmering particles rising upward
- **4-phase animation** -- Beam materializes (0–25%), full flash (25–50%), fade (50–80%), particle shimmer (80–100%)
- Triggered when any Asgard Beam Tech card is played

#### Audio
- **asgard_beamup.ogg** -- Transporter beam sound effect plays alongside the beam animation
- **asgard_thor.ogg** -- Commander voice snippet for Thor (added to commander snippets roster)

#### Bug Fixes
- **Fixed Thor's Hammer false trigger** -- Playing the hero card "Thor" no longer triggers the Thor's Hammer purge animation; now correctly requires "Thor's Hammer" in card name
- **Saved deck migration** -- Added migration mappings for all renamed card IDs (asgard_fifth → asgard_thor, asgard_elite_warrior → asgard_elite, asgard_medic_drone → asgard_medic, asgard_transport → asgard_beam)

#### Documentation
- Updated card_catalog.json, default_faction_decks.json, rules_menu_spec.md with all Asgard changes
- Updated README card count from 219 to 247

---

### Version 6.0.0 (February 2026)
**Space Shooter: Complete Overhaul — Vampire Survivors-Style Combat**

Major rewrite of the space shooter mini-game: split the 3000-line monolith into a modular package, added 9 new upgrades with a rarity system, 4 new weapon types, visual juice (parallax, damage numbers, screen shake), enemy variety (kamikaze, formations, boss escorts), and rebalanced combat for fast-paced action.

#### Package Architecture
- **Modular Package** -- Split `space_shooter.py` (3029 lines) into `space_shooter/` package with 9 focused modules (4100+ lines total)
- **Modules**: `__init__.py`, `projectiles.py`, `entities.py`, `ship.py`, `effects.py`, `upgrades.py`, `ui.py`, `game.py`, `ship_select.py`
- **Backward Compatible** -- Old `space_shooter.py` kept as 2-line shim; all imports work unchanged

#### New Weapons (Upgrade-Acquired)
- **Chain Lightning** (Epic) -- Projectiles chain to nearby enemies; +1 chain target per stack (max 3)
- **Scatter Shot** (Rare) -- +3 spread pellets per stack in a cone (40% damage each)
- **Gravity Well** (Epic) -- Auto-deploys a vortex that pulls and damages enemies every 10s
- **Shield Bash** (Rare) -- Dash damages enemies on contact with afterimage trail

#### New Passive Upgrades
- **Magnet Field** -- +40 XP orb collection range per stack
- **Critical Strike** -- +10% chance for double damage per stack
- **Evasion Matrix** -- +8% dodge chance per stack (with "DODGE!" popup)
- **Berserker Protocol** -- +5% damage per stack when below 50% HP
- **Hyperspace Jump** -- -15% wormhole cooldown per stack

#### Rarity System
- **3 Tiers** -- Common (white), Rare (blue), Epic (purple)
- **Level-Up Cards** -- Gradient backgrounds, pulsing rarity-colored borders, stats preview on hover

#### Visual Enhancements
- **3-Layer Parallax Starfield** -- Stars respond to player movement, scaled by depth
- **Nebula Clouds** -- Pre-rendered semi-transparent colored blobs drifting slowly
- **Space Debris** -- Tiny polygon shapes floating through as visual flair
- **Speed Lines** -- Translucent streaks when player moves fast
- **Damage Numbers** -- Float upward from hits, color-coded (white=normal, yellow=crit, red=player damage)
- **Screen Shake** -- Triggers on player hit (intensity 5), enemy kill (2), boss kill (8)
- **Popup Notifications** -- "RAPID FIRE!", "SHIELD BOOST!" etc. near player on power-up pickup
- **Kill Streak Counter** -- Tracks consecutive kills within 3s; bonus score at 3+ streak

#### Enemy Variety
- **Kamikaze Type** -- Fast red-tinted ships that charge straight at player (wave 6+)
- **Formation Spawning** -- V-Formation, Line, and Pincer patterns (wave 8+, 50% chance)
- **Enemy Warning Indicators** -- Pulsing arrows at screen edges during wave transition
- **Boss Escorts** -- 2-3 elite ships orbit bosses on boss waves

#### UI Improvements
- **Mini-Radar** -- 120x90 semi-transparent overlay showing player (green), enemies (red), asteroids (orange), power-ups (blue)
- **Upgrade Bar with Tooltips** -- Colored icon squares with hover tooltip showing name/stacks/description
- **Enhanced Level-Up Screen** -- Gradient card backgrounds, click or key selection, rarity glow

#### Combat Rebalance
- **Faster Player Fire Rate** -- All faction fire rates increased ~40% (e.g., laser 25 -> 14, missile 50 -> 28)
- **More Frequent Power-Ups** -- Spawn rate doubled (400 -> 200 frames), 75% spawn chance (was 50%)
- **Faster Level-Ups** -- XP requirement reduced (100 -> 80 base, 1.12x scaling instead of 1.3x)
- **Increased XP Drops** -- All enemy XP values boosted ~50% (regular 20 -> 30, elite 50 -> 75)
- **Multi-Directional Fire** -- Multi-Targeting now fires perpendicular at 2+ stacks, backward at 3+, diagonals at 4+
- **Smooth Ship Rotation** -- Ships interpolate rotation at 12 deg/frame instead of snapping between 4 cached images
- **Better Enemy Separation** -- 180px range with inverse-distance force (up to 8px push) prevents enemy overlap
- **Slower Enemies** -- Base enemy speed 4 (half of player's 8), wave speed scaling 0.008 per power level

#### Performance Optimizations
- **Eliminated SRCALPHA Surfaces** -- Nebulae pre-rendered once, speed lines draw directly, hit flash uses small ship-bounds overlay, cloak uses set_alpha()
- **Cached Fonts** -- PowerUp and PopupNotification cache fonts in __init__ instead of creating SysFont per frame
- **Enemy Warnings** -- Direct draw.polygon() instead of full-screen SRCALPHA per arrow

---

### Version 5.9.0 (February 2026)
**Space Shooter: 4-Directional Combat, Wormhole Escape & Session Leaderboard**

Major upgrade to the space shooter easter egg with full 4-directional ship facing, a wormhole teleport ability, and per-session score tracking that resets on exit.

#### 4-Directional Ship Facing
- **Ship Rotates to Face Movement Direction** -- Pressing WASD/Arrows rotates the ship sprite to face up, down, left, or right
- **Weapons Fire in Faced Direction** -- All weapon types (lasers, missiles, energy balls, staff blasts, beams) now fire in the direction the ship is facing
- **Beam Support** -- Asgard continuous beam works in all 4 directions with correct collision detection
- **Upgrade Compatibility** -- Rear turret fires opposite to facing, multi-targeting spreads perpendicular, targeting computer homes on the correct axis

#### Wormhole Escape Ability
- **Press Q to Activate** -- Player vanishes into a swirling blue vortex and reappears at a random screen location
- **Entry/Exit Vortex Animation** -- Spinning concentric rings with rotating bright spots and a collapsing/expanding effect
- **Invulnerability During Transit** -- Player is immune to projectiles, beams, and asteroids while in the wormhole
- **8-Second Cooldown** -- Cooldown bar and status indicator shown in the HUD
- **Ship Freezes in Transit** -- No movement input during the 0.5s teleport for balanced gameplay

#### Per-Session Leaderboard
- **Scores No Longer Persist to Disk** -- High scores are session-only, not saved to player_unlocks.json
- **Survives Restarts** -- Pressing R to restart keeps the session leaderboard intact
- **Resets on Exit** -- Returning to menu (ESC) clears all scores for a fresh start next time
- **Session Rank Display** -- Game over screen shows "SESSION BEST!" or "Session Rank #N" with games-played count

---

### Version 5.8.0 (February 2026)
**LAN Chat, Game History & Stats UI Improvements**

UX polish across three systems: enhanced LAN chat with message bubbles and opponent names, richer game history tracking with score deltas and visual separators, and an upgraded stats screen with win rate bars, achievements, and fun facts.

#### LAN Chat Improvements
- ✅ **Message Length Limit** -- 200-character cap with live counter that changes color (dim -> gold -> red)
- ✅ **Expanded Quick Chats** -- 10 quick chat messages (keys 1-0) including Stargate quotes like "Indeed.", "Kree!", and "Undomesticated equines could not drag me away"
- ✅ **Opponent Name Display** -- Chat shows actual opponent name instead of "Peer"; typing indicator reads "{Name} is dialing..."
- ✅ **Message Bubbles** -- Right-aligned dark blue bubbles for your messages, left-aligned dark purple for opponent, centered gold for system messages with colored borders and sender labels

#### Game History Enhancements
- ✅ **Turn & Score Tracking** -- Every history entry now records turn number and current scores at time of event
- ✅ **Score Delta Badges** -- Card plays show "+5" green badges, scorch/destroy events show "-10" red badges at entry edge
- ✅ **Turn Number Labels** -- Small "T3" badge in bottom-right of each entry
- ✅ **Running Score Display** -- Tiny "45|32" score indicator in top-right corner of entries
- ✅ **Round Separators** -- Round start/end entries render as gold horizontal dividers with centered text and score display
- ✅ **Latest Entry Pulse** -- Most recent entry has a subtle white sine-wave pulse overlay

#### Stats UI Improvements
- ✅ **Win Rate Bars** -- Faction win rates, game modes, and leader stats now show colored progress bars below text
- ✅ **Highlights/Achievements** -- Earned badges at top of stats: Recruit/Veteran/Centurion, On Fire/Unstoppable, Dominator, Faction Master, Perfect Draft, Comeback King
- ✅ **Section Visual Hierarchy** -- Glowing gradient underlines on section headers, alternating row backgrounds for better readability
- ✅ **Top 3 Leaders** -- Shows top 3 most-played leaders with win rate bars and hover preview (was top 1)
- ✅ **Fun Facts Section** -- Total cards played, cards per game, most used ability, avg mulligans, draft battles per run

---

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

#### Post-Refactor Fixes
- ✅ **Renderer/Event Split** -- Moved event-handling code (button clicks) out of `frame_renderer.py` into `event_handler.py`; renderer stores button rects on `state.game_over_buttons` / `state.pause_menu_buttons` and the event handler reads them
- ✅ **Pause Menu Clicks** -- Pause menu buttons (Resume, Options, Surrender, Main Menu, Quit) and Q-to-surrender now properly handled in event handler
- ✅ **Dead Code Cleanup** -- Removed 70 lines of unreachable game-over button code from KEYDOWN handler, removed redundant `LAN_MODE = True` assignment, fixed duplicate `pygame.display.flip()`

#### Size Reduction
- `main.py`: 4150 → 1575 lines (62% reduction)
- New modules: `game_loop_state.py` (135), `event_handler.py` (1268), `frame_renderer.py` (1195)

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

