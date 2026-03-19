# Stargwent Development Guide

## Content Changes

### Renaming a Card
1. **`cards.py`** — Change the dict key + Card object params (`"old_id"` → `"new_id"`)
2. **`assets/`** — Rename `old_id.png` → `new_id.png`
3. **Save files** — Find & replace in `player_decks.json` and `player_unlocks.json`
4. **Docs** (optional) — Update `docs/card_catalog.json`, `docs/rules_menu_spec.md`

### Adding a Card
1. **`cards.py`** — Add to `ALL_CARDS`: `"new_id": Card("new_id", "Name", FACTION, power, "row", "Ability")`
2. **`assets/`** — Place `new_id.png`
3. **`unlocks.py`** — Add to `UNLOCKABLE_CARDS` if unlockable
4. **`docs/card_catalog.json`** — Add entry for Rule Compendium

### Adding a Leader
1. **`content_registry.py`** — Add to `UNLOCKABLE_LEADERS` or `BASE_FACTION_LEADERS`
2. **`cards.py`** — Add Card object: `"faction_name": Card("faction_name", "Name", FACTION, 10, "close", "Ability")`
3. **`assets/`** — Add `faction_name_leader.png`
4. **`leader_matchup.py` / `game.py`** — Implement ability logic
5. **`docs/leader_catalog.json`** — Add entry

### Adding a Faction
Major change across many files (see Alteran faction added in v10.0 for a complete example):
1. `cards.py` — Add `FACTION_NEW` constant + card definitions
2. `abilities.py` — Add new ability enums if needed (e.g., `PRIORS_PLAGUE`, `ASCENSION`)
3. `content_registry.py` — Add to leader dicts + `LEADER_COLOR_OVERRIDES` + `LEADER_BANNER_NAMES`
4. `game.py` — Implement faction passive class + register in `FACTION_ABILITIES` + leader ability handlers
5. `power.py` — Implement faction power class + register in `FACTION_POWERS`
6. `game_config.py` — Add to `FACTION_GLOW_COLORS`
7. `deck_builder.py` — Add to `AVAILABLE_FACTIONS`, colors, descriptions, theme music
8. `game_setup.py` — Add to AI opponent faction pool (gated by `is_faction_unlocked()` if unlockable)
9. `draft_mode.py` — Add faction-specific synergy scoring in `get_synergy_score()` (e.g., Alteran Presence, Prior's Plague, Ascension)
10. `draft_controller.py` — Leaders auto-included via `BASE_FACTION_LEADERS` + `is_faction_unlocked()` gate
11. `unlocks.py` — Add unlock conditions if faction is unlockable
12. `assets/data/default_faction_decks.json` — Add default AI deck (used by both standard and draft AI opponents)
13. `scripts/create_placeholders.py` — Add `FACTION_COLORS`, `FACTION_BACKGROUND_IDS`, imports
14. `scripts/card_quotes.json` — Add character quotes

Current factions (6): Tau'ri, Goa'uld, Jaffa Rebellion, Lucian Alliance, Asgard, **Alteran** (unlockable — win 1 game with each base faction). All 6 factions are playable in both standard card game and Galactic Conquest mode.

---

## Content Manager

Modular CLI tool with **Developer** and **User/Player** modes.

```bash
python scripts/content_manager.py              # Interactive role selection
python scripts/content_manager.py --dev        # Developer menu
python scripts/content_manager.py --user       # User/player menu
python scripts/content_manager.py --dry-run    # Preview changes without writing
python scripts/content_manager.py --non-interactive  # CI/scripting defaults
```

### Developer Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | Add Card | Interactive wizard, auto-updates all files |
| 2 | Add Leader | Create leader with registry, colors, portrait |
| 3 | Add Faction | Complete faction creation |
| 4 | Ability Manager | Add/edit card, leader, or faction abilities |
| 5 | Placeholders | Generate missing card images/portraits |
| 6 | Regenerate Docs | Rebuild catalog JSONs + rules spec |
| 7 | Asset Checker | Find missing/orphaned assets, size validation |
| 8 | Audio Manager | Manage SFX, music, voice clips |
| 9 | Balance Analyzer | Power distribution, ability frequency stats |
| 10 | Batch Import | Import cards/leaders from JSON |
| 11 | Leader Ability Gen | Generate code stubs for leader abilities |
| 12 | Card Rename/Delete | Rename, delete, preview, batch rename |

### User/Player Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | Save Manager | Backup/restore player saves |
| 2 | Deck Import/Export | Share decks via JSON or text |
| 3-5 | Create Custom Card/Leader/Faction | Using existing abilities |
| 6-7 | Content Packs | Import/export shareable .zip packs |
| 8 | Manage User Content | Enable/disable/delete user content |
| 9 | Validate | Check user content for errors |

All user content lives in `user_content/` — never touches game source code.

### Safety Features
- Timestamped backups to `backup/YYYY-MM-DD_HHMMSS/` before modification
- Step-by-step approval, syntax validation, automatic rollback on errors
- Dry-run mode, colored output, session logging to `scripts/content_manager.log`

---

## Miniship Escort System (v9.4.0)

Carrier-style interceptors (StarCraft Carrier inspired). Permanent escorts orbit the player, sortie to attack, return to formation.

| File | Role |
|------|------|
| `space_shooter/game.py` | State, spawn, update loop, rendering, collision, powerup apply |
| `space_shooter/ship.py` | `update_miniship_ai()` orbit/sortie/return; `_ai_hostile_all()` wraith enemy AI |
| `space_shooter/entities.py` | 4 miniship powerup types |
| `space_shooter/upgrades.py` | `wraith_miniship` enemy type + explosion palette |
| `space_shooter/spawner.py` | Wraith miniship in tiers 5+, paired spawning |
| `space_shooter/coop_game.py` | Miniship snapshot sync + co-op collision |
| `space_shooter/coop_client.py` | Client-side rendering + entity interpolation |

### Adding a New Miniship Faction
1. Create `assets/ships/<faction>_miniship.png` (120x120, used at native x1 scale)
2. `game.py:_load_miniship_sprites()` — add faction entry with rotation to face-right
3. `spawner.py:_spawn_enemy()` — add sprite loading for enemy miniship types

### Hostile-All Behavior
`ship.py:_ai_hostile_all()` targets nearest entity (player + AI ships). Projectiles marked `is_hostile_all=True` + `_source_ship=self`. Collision loop in `game.py` checks against `ai_ships` (skipping source).

---

## Audio Assets

All in `assets/audio/`. Missing files silently skipped.

| Category | Files |
|----------|-------|
| **Music** | `main_menu_music.ogg`, `deck_building.ogg`, `battle_round{1,2,3}.ogg`, `{faction}_theme.ogg` |
| **Card SFX** | `close.ogg`, `ranged.ogg`, `siege.ogg`, `ring.ogg`, `horn.ogg`, `iris.ogg`, `symbiote.ogg` |
| **Menu SFX** | `menu_select.ogg`, `menu_enter.ogg`, `rule_chevron.ogg`, `conquest_menu_select.ogg`, `stats_menu_tab.ogg` |
| **Weather** | `weather_ice.ogg`, `weather_nebula.ogg`, `weather_asteroid.ogg`, `weather_emp.ogg` |
| **Chat** | `chat_notification.ogg` |
| **Voices** | `assets/audio/commander_snippets/{card_id}.ogg`, `assets/audio/leader_voices/{leader_id}.ogg` |
| **Space Shooter** | `assets/audio/space_shooter/` — shield_hit, supergate, ori/wraith beam, per-faction boost/secondary SFX |

### Volume Mapping (4 sliders in game_settings.py)
- **Master** — multiplier for all sliders
- **Music** — battle music, menu music
- **Voice** — commander snippets (`play_commander_snippet`), leader voices (`play_leader_voice`)
- **Effects** — card animations, row/weather/horn/iris sounds, UI hover, chat notifications

---

## Art Assembler

Automated pipeline using Pillow for card images, leader portraits, and backgrounds.

```bash
python scripts/card_assembler.py                    # Assemble all
python scripts/card_assembler.py tauri_oneill       # Specific cards
python scripts/card_assembler.py --faction tauri    # Entire faction
python scripts/card_assembler.py --status           # Per-faction progress
python scripts/card_assembler.py --list-missing     # Cards without raw art
python scripts/card_assembler.py --dry-run          # Preview only
```

**Pipeline:** Raw art (`raw_art/{card_id}.png`) → stretch to border cutout → composite faction border → overlay row/ability icons → render power number → rarity nameplate → card name → flavor text (`scripts/card_quotes.json`) → save to `assets/{card_id}.png`

**Raw art naming:**

| Pattern | Output |
|---------|--------|
| `raw_art/{id}.png` | Card with border/icons/text |
| `raw_art/{id}_leader.png` | Leader portrait (200x280) |
| `raw_art/leader_bg_{id}.png` | Leader background (3840x2160) |
| `raw_art/faction_bg_{faction}.png` | Faction background (3840x2160) |

Layout constants at top of `card_assembler.py`. `--status` classifies cards as done (>15KB), ready (has raw art), or needs art.

---

## GPU Post-Processing Architecture

Hybrid rendering: Pygame draws to offscreen surface → uploaded to ModernGL for GLSL shader post-processing → rendered to screen via fullscreen quad.

| File | Purpose |
|------|---------|
| `gpu_renderer.py` | `GPURenderer`, `ShaderPass`, `FBOPool` — ModernGL backend (GLSL 330) |
| `webgl_renderer.py` | PyOpenGL/raw GL ES backend for web (GLSL 300 es) |
| `shaders/__init__.py` | Effect registry, `glsl_version_header()` for desktop/web |
| `shaders/*.py` | 14 effects: bloom, vignette, CRT, distortion, event_horizon, kawoosh, hyperspace, shockwave, asgard_beam, zpm_surge, shield_bubble, black_hole, ascension, priors_plague |

**Rendering flow:** Game → `display_manager.screen` → `gpu_flip()` → `tobytes()` → texture upload → shader chain → `ctx.screen` → `pygame.display.flip()`

**Adding a shader:** Create `shaders/my_effect.py` with `ShaderPass` → register in `register_all_effects()` → if animation-driven, add `get_gpu_params()` to animation class + handle in `frame_renderer._apply_gpu_params()`. Use `display_manager.is_gpu_available()` for consistent GPU null checks.

**Fallback chain:** `moderngl` missing → pure Pygame | OpenGL creation fails → `pygame.SCALED` | shader compile fails → effect skipped | runtime GPU error → auto-revert | `gpu_enabled: false` → skip init | Web → `webgl_renderer.py`

**Settings:** `gpu_enabled`, `bloom_enabled`, `bloom_intensity`, `bloom_threshold`, `vignette_enabled`, `shader_quality` (low/medium/high)

**Circular import:** `game_settings.py` ↔ `display_manager.py` — always use local import in `game_settings.py` functions.

---

## Building & Packaging

### Desktop Builds

Version is read from the README.md badge.

| Script | Target | Platform |
|--------|--------|----------|
| `build_deb.sh` | `.deb` installer | Linux (Debian/Ubuntu) |
| `build_appimage.sh` | `.AppImage` portable | Linux (any) |
| `build_exe.sh` | `.exe` zip | Windows |
| `build_dmg.sh` | `.dmg` disk image | macOS |
| `build_release.sh` | Orchestrator | Auto-detects platform |

```bash
./build_release.sh                  # Auto-detect, build all
./build_release.sh "" deb           # .deb only
./build_release.sh "" appimage      # AppImage only
./build_release.sh "" exe           # Windows .exe only
./build_release.sh "" dmg           # macOS .dmg only
./build_release.sh "" linux         # .deb + AppImage
./build_release.sh 10.0.0            # Override version
```

Output: `builds/releases/`. Staging: `builds/staging/` (auto-cleaned).

### Web Build (PWA via Pygbag)

The game runs in-browser via [Pygbag](https://github.com/nicegui-community/pygbag) (Pygame → WASM/Emscripten). Single-player parity: card game, space shooter, deck builder, galactic conquest — all with touch controls and WebGL shaders.

**Local dev:**
```bash
pip install pygbag
pygbag main.py              # Dev server at localhost:8000
pygbag --build main.py      # Production build → build/web/
```

**CI/CD:** Push to `main` → `.github/workflows/web-deploy.yml` builds automatically:
1. Install Pygbag, preserve PWA assets (`manifest.json`, `sw.js`, icons)
2. `pygbag --build main.py`
3. Inject PWA tags (manifest, service worker, viewport meta) into `index.html`
4. Upload `build/web/` as artifact (30-day retention)

**`pygbag.ini` config:** Excludes `/builds`, `/raw_art`, `/scripts`, `/docs`, `/backup`, `/.git`, `/.github`, `/.claude`, `/user_content` directories and build/doc files from the WASM bundle.

**Web architecture:**

| Layer | Module | Description |
|-------|--------|-------------|
| Platform detection | `touch_support.py` | `is_web_platform()`, `is_touch_platform()` |
| Async loops | All game loops | `async def` + `await asyncio.sleep(0)` after `clock.tick()` |
| Touch → Mouse | `touch_gestures.py` | FINGER events → synthetic mouse (tap, long-press, drag, scroll) |
| Touch → Keys | `space_shooter/touch_controls.py` | Virtual joystick + action buttons |
| WebGL | `webgl_renderer.py` | Raw GL ES, same API as `GPURenderer` |
| GLSL | `shaders/__init__.py` | `glsl_version_header()` — `#version 300 es` on web |
| Saves | `save_paths.py` | IndexedDB via `sync_saves()` after every write |
| Audio | `main.py` | "Tap to Start" splash to unlock browser audio context |
| Networking | `lan_session.py` | Threading/sockets guarded, multiplayer hidden on web |
| PWA | `build/web/` | manifest.json, sw.js, icons for installable offline app |

**Default faction decks:** `docs/` excluded from Pygbag build. Copy defaults to `assets/data/` for web. `deck_builder.py:load_default_faction_deck()` tries both paths.

**LAN on web:** Not supported (no TCP sockets in WASM). Future: WebSocket relay or WebRTC.

---

## Web (Emscripten) Performance Notes

### Critical Rules
- **NEVER** create full-screen SRCALPHA surface blits (8MB per-pixel alpha blend per frame)
- **NEVER** call `pygame.font.SysFont()` per-frame — use `_get_cached_font()` or `cfg.get_font()`
- **NEVER** use `pygame.mixer.music.fadeout()` on web — crashes Emscripten audio. Use `stop()`
- Blocking animation loops freeze the browser — skip via `if sys.platform != "emscripten":` guard

### Render Caching

| Cache | File | Avoids |
|-------|------|--------|
| `_render_text()` | `render_engine.py` | ~60-100 `font.render()` calls/frame |
| `_score_box_cache` | `render_engine.py` | 6 SRCALPHA allocations/frame |
| `_history_panel_bg_cache` | `render_engine.py` | Scanline grid (dozens of draw.line) |
| Row separator surface | `frame_renderer.py` | 30 draw.line → 1 blit |
| Panel/slider gradients | `main_menu.py` | Per-pixel gradient renders |
| `_dim_overlay_cache` | `map_renderer.py` | Full-screen SRCALPHA overlay (8MB/frame) |
| `_tooltip_cache` | `map_renderer.py` | 15+ `font.render()` calls/frame on hover |
| `_get_circle_sprite()` | `animations.py` | Per-particle SRCALPHA in steal/trail effects |
| `_cached_scaled_card` | `animations.py` | Per-frame `smoothscale` in CardStealAnimation |
| `_get_network_cached()` | `campaign_controller.py` | BFS traversal called 4+ times/turn |
| `_flash_surf_cache` (bounded) | `space_shooter/game.py` | Unbounded cache growth (capped at 50) |

Call `clear_render_caches()` on resolution change.

### Web Audio
- `battle_music.py` uses `music.stop()` on web (not `fadeout()`), loads next track lazily
- Gated via `sys.platform == "emscripten"`

---

## Galactic Conquest Architecture (v10.0.0)

Roguelite card-battle campaign. Package: `galactic_conquest/` (~30 modules, ~11,470 lines)

| File | Description |
|------|-------------|
| `__init__.py` | Entry point, campaign routing |
| `conquest_menu.py` | CRT submenu + CustomizeRunScreen + unlocks |
| `campaign_state.py` | CampaignState dataclass (~45 fields) |
| `campaign_persistence.py` | Save/load JSON via XDG paths |
| `campaign_controller.py` | Turn loop, attacks, AI, diplomacy, buildings, crisis, scoring, minor world/doctrine/espionage hooks |
| `galaxy_map.py` | Planets, adjacency, supply lines, Ring Platform 2-hop |
| `map_renderer.py` | Side info panel, pulsing lanes, building/fort icons, simplified HUD, 8-button bar, non-SRCALPHA surfaces |
| `wisdom_actions.py` | 4 repeatable wisdom actions (Ascended Insight, Temporal Shift, Ancient Knowledge, Enlightened Trade) |
| `faction_setup.py` | Faction/leader/deck selection (6 factions including Alteran) |
| `leader_select.py` | Per-battle leader selection screen with portraits and ability descriptions |
| `card_battle.py` | Weather injection, elite params, relic modifiers, doctrine power bonuses, sabotage effects |
| `reward_screen.py` | Post-victory card picks with tier scaling |
| `neutral_events.py` | 20 events with choices |
| `planet_passives.py` | 21 planet passives (6 factions + neutrals) |
| `relics.py` | 19 relics (combat/economy/exploration) |
| `relic_screen.py` | CRT acquisition screen |
| `narrative_arcs.py` | 7 story chains (including The Ori Crusade) |
| `difficulty.py` | 4 levels (Easy/Normal/Hard/Insane) |
| `stargate_network.py` | Network tiers (Outpost→Galactic) based on BFS connectivity |
| `conquest_abilities.py` | 40 leader abilities (6 factions), L1-L4 scaling with network tier |
| `diplomacy.py` + `diplomacy_screen.py` | Faction relations, trade/alliance/betray, AI proposals (4 types), strain warnings, incident handling |
| `buildings.py` | 5 building types with Lv 1-3 upgrades, level-scaled effects, doctrine cost reduction |
| `crisis_events.py` | 5 galaxy-wide events with 2-choice player agency (10%/turn after turn 5) |
| `meta_progression.py` | Conquest Points, 5 perks, high scores, victory type multipliers |
| `minor_worlds.py` | 9 minor worlds: influence, quests, type bonuses, AI competition |
| `minor_world_screen.py` | CRT-styled minor world interaction panel |
| `doctrines.py` | 5 doctrine trees (20 policies), Wisdom economy, `get_active_effects()` |
| `doctrine_screen.py` | CRT-styled doctrine tree selection UI |
| `espionage.py` | Operative lifecycle, 6 missions, rank system, AI espionage events, incident choices |
| `espionage_screen.py` | CRT-styled operative management UI |
| `victory_conditions.py` | 4 victory paths + score fallback, progress tracking |

### Key Systems
- **Network Tiers**: Connected planet count → tier → scaling naq/cooldown/range/ability bonuses
- **Supply Lines**: Disconnected planets = -50% income, +20% counterattack, no fortification
- **Pre-Battle Preview**: ENGAGE/RETREAT screen with forces, weather, modifiers
- **Post-Battle Refresh**: `_refresh_after_battle()` — rebuild screen + `pygame.event.clear()`
- **Minor Worlds**: 9 neutral planets with influence (0-100), quests, ally exclusivity, 5 world types with Friend/Ally bonuses
- **Doctrine Trees**: Wisdom resource → 5 trees × 4 policies + completion bonus; escalating cross-tree cost forces 2-3 tree completions per campaign
- **Wisdom Actions**: After completing any doctrine tree, 4 repeatable wisdom sinks (card upgrade, cooldown reset, deck reveal, naq conversion)
- **Building Upgrades**: Lv 1→2→3 with `BUILDING_LEVEL_EFFECTS` lookup and `UPGRADE_COST_MULTIPLIERS` (1.5x/2.0x)
- **Espionage**: Tok'ra operatives with IDLE→MOVING→ESTABLISHING→ACTIVE lifecycle, 6 mission types, rank 1-3; AI espionage against player (3 mission types); diplomatic incident choices (deny/recall/double-down)
- **AI Diplomacy**: `generate_ai_proposals()` creates trade offers, joint attacks, ceasefires, tribute demands; `check_potential_strain()` warns before attacking near allies
- **Crisis Choices**: `CRISIS_CHOICES` dict provides 2 options per crisis; `apply_crisis(choice=)` branches on player decision
- **Victory Conditions**: Domination (always), Ascension/Alliance/Supremacy (require doctrine completion), Score (turn 30 fallback)
- **Side Panel UI**: `_draw_side_panel()` replaces tooltips — planet details with build/upgrade buttons when selected, victory/faction overview when not
- **Cross-system integration**: `get_active_effects(state)` is the central doctrine query — called by card_battle, buildings, diplomacy, espionage, minor_worlds, campaign_controller

---

## Space Shooter Architecture (v9.4.0)

Vampire Survivors-style infinite survival. Package: `space_shooter/`

| File | ~Lines | Description |
|------|--------|-------------|
| `__init__.py` | 330 | `run_space_shooter()`, `run_coop_space_shooter()`, disconnect handling |
| `game.py` | 3700 | SpaceShooterGame — update, draw, collisions, upgrades, bosses, miniships |
| `ship.py` | 1500 | Ship class, SHIP_VARIANTS, player + 9 AI behaviors + miniship AI |
| `projectiles.py` | 800 | 13 projectile types |
| `entities.py` | 1670 | Asteroid, PowerUp (33 types), XPOrb, Sun (5 phases), Supergate, Explosion |
| `effects.py` | 270 | StarField, ScreenShake, ParticleTrail |
| `upgrades.py` | 300 | 27 upgrades, 5 evolutions, 9 masteries, 15 enemy types |
| `ui.py` | 500 | HUD, timer, radar, level-up cards, game over |
| `camera.py` | 140 | Smooth follow, culling, co-op spawn ring |
| `spawner.py` | 280 | 10 tiers, paired/swarm spawning |
| `ship_select.py` | 200 | Ship + variant selection |
| `coop_game.py` | 1100 | Host-authoritative co-op, snapshots, revival |
| `coop_client.py` | 610 | Client renderer, independent camera, entity interpolation |
| `coop_protocol.py` | 75 | Message types + variant in READY |
| `coop_ui.py` | 130 | Dual health bars, partner arrow, revival |
| `virtual_keys.py` | 55 | Network input translation |

### Key Systems
- **Ship Variants**: Data-driven `SHIP_VARIANTS` dict per faction with weapon, secondary, passive configs
- **Supergate Bosses**: At 3 min, single Supergate (40k HP) spawns → bosses emerge one at a time (Ori Mothership / Wraith Hive). Song plays when gate opens. Gate stays until all bosses spawned AND killed. Damageable by projectiles, asteroids (500), wormhole (2000) — immune to touch contact. Boss events never stack
- **Common Threat**: Enemies retarget boss within 500px, boss beam damages everything, boss ↔ enemy touch damage (50/10)
- **Miniship Escorts**: Tau'ri/Goa'uld/Wraith get permanent interceptors (2 at level 3 → 5 at level 15), native 120x120 sprites, lerp-smoothed movement
- **Enemy Behaviors**: swarm_lifesteal, split_on_death, shielded_charge, homing, paired, bomber, mini_boss_spawner, hostile_all, ori_boss, wraith_boss
- **Secondary Fire**: Per-faction + per-variant E-key abilities (Railgun, Staff Barrage, Ion Pulse, etc.)
- **Passives**: heavy_armor, adaptive_shields, analyzer, sarcophagus_regen, point_defense, symbiote_resilience, anubis_shield
- **Level 20 Masteries**: 9 weapon evolutions (Overcharged Beam, Plasma Detonation, Cascade Disruption, etc.)
- **Co-op**: Independent cameras, P2 secondary fire, revival with 3s invuln, 20Hz snapshots with entity interpolation

---

## Chat System

- **Sound**: `chat_notification.ogg` on incoming messages, respects SFX volume
- **Scrolling**: PageUp/Down, Home/End, mouse wheel, 100 message buffer
- **Quick Chat**: Keys 1-5 ("Good game!", "Nice play!", etc.)
- **Unread Badge**: Count badge when chat minimized
- **Delivery Confirmation**: Unique message IDs + ACK protocol, checkmark on confirmed
- **Thread Safety**: Socket lock, duplicate disconnect prevention, parse error tolerance (5 consecutive), `deque(maxlen=1000)` inbox (atomic under CPython GIL), `time.monotonic()` for all timing, game action ACKs with single-retry

---

## Progression

### Card Unlocks
- **Trigger**: Win any game → choose 1 of 3 (faction + Neutral)
- **Total**: 21 unlockable cards, saved to `player_unlocks.json`

### Leader Unlocks
- **Trigger**: Win 3 in a row → choose 1 of 3 faction leaders
- **Total**: 20 unlockable leaders (4 per faction)

### Deck Customization
- 20-40 cards, ≥15 units, faction + Neutral only
- **Naquadah Budget**: 150 limit (cost = 4 + power - 1, heroes +3)
- **Mercenary Tax**: More Neutral than Faction cards → -25% score
- **Ori Corruption**: Over 150 Naquadah → -50% score
- Saved to `player_decks.json`

---

## Build Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: moderngl` | Add `--hidden-import moderngl --hidden-import glcontext` to PyInstaller |
| Assets not found | Verify `--add-data` paths (`:` on Linux/macOS, `;` on Windows) |
| OpenGL errors in AppImage | `sudo apt install mesa-utils` |
| AppImage won't run | `sudo apt install fuse libfuse2` or `--appimage-extract` |
| macOS "app is damaged" | `xattr -cr Stargwent.app` |
| Save data location | `~/.local/share/stargwent/` (XDG) |

### GitHub Actions CI/CD

The `Build Releases` workflow (`.github/workflows/build.yml`) builds `.deb`, `.AppImage`, `.exe`, and `.dmg` in parallel. Two trigger methods:

#### Method 1: Tag Push (creates draft GitHub Release)
```bash
# Tag the current commit and push both code + tag:
git tag v10.0.0
git push origin main
git push origin v10.0.0
```
This creates a **draft** GitHub Release with all 4 platform artifacts attached. Go to Releases to review and publish.

#### Method 2: Manual Dispatch (downloads as artifacts)
1. Go to the repository on GitHub
2. Click **Actions** tab → **Build Releases** workflow (left sidebar)
3. Click **Run workflow** (top-right dropdown)
4. Optionally enter a version override (leave empty to read from README.md badge)
5. Click **Run workflow**

Artifacts are uploaded with 1-day retention. Download from the workflow run summary page.

#### Version Detection
The workflow reads the version from the README.md badge (`![Version](https://img.shields.io/badge/version-X.Y.Z-blue)`). Priority: manual input > git tag > README badge.

#### Web Build
Web build (Pygbag → WASM) triggers on any push to `main` that touches `.py`, `assets/`, `shaders/`, or `build/web/` files.

### Development Prerequisites
- **Python 3.8+**, **Pygame CE 2.5.6+**
- **ModernGL** — optional GPU post-processing (`pip install moderngl`)
- **Pillow** — card assembler (`pip install Pillow`)
- **Pygbag** — web builds (`pip install pygbag`)
