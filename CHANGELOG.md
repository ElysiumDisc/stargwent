# Changelog

*Older versions: [v5.0-v8.8](CHANGELOG-v5-v8.md) | [v1.0-v4.9](CHANGELOG-v1-v4.md)*

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

