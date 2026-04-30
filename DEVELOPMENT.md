# Stargwent Development Guide

This document is the contributor reference: how to add content, how the
engine subsystems fit together, and how to ship builds. End-user docs
live in [README.md](README.md); per-version notes live in
[CHANGELOG.md](CHANGELOG.md).

## Table of Contents

- [Content Changes](#content-changes) — adding/renaming cards, leaders, factions
- [Content Manager](#content-manager) — the dev/user CLI tool
- [Save Persistence](#save-persistence) — XDG paths and atomic writes
- [Miniship Escort System](#miniship-escort-system) — Carrier-style interceptors
- [Audio Assets](#audio-assets) — file layout and volume mapping
- [Art Assembler](#art-assembler) — automated card art pipeline
- [GPU Post-Processing Architecture](#gpu-post-processing-architecture)
- [Building & Packaging](#building--packaging) — desktop + web + CI/CD
- [Web (Emscripten) Performance Notes](#web-emscripten-performance-notes)
- [Galactic Conquest Architecture](#galactic-conquest-architecture)
- [Space Shooter Architecture](#space-shooter-architecture)
- [Chat System](#chat-system)
- [Progression](#progression)

---

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

## Save Persistence

All player-facing JSON saves go through XDG-compliant paths defined in
`save_paths.py`:

| File | Path |
|------|------|
| Decks | `$XDG_DATA_HOME/stargwent/player_decks.json` |
| Unlocks | `$XDG_DATA_HOME/stargwent/player_unlocks.json` |
| Settings | `$XDG_DATA_HOME/stargwent/game_settings.json` |
| Custom decks | `$XDG_DATA_HOME/stargwent/custom_decks.json` |
| Galactic Conquest (slot 0 / legacy) | `$XDG_DATA_HOME/stargwent/galactic_conquest_save.json` |
| Galactic Conquest (slot 1, v12+) | `$XDG_DATA_HOME/stargwent/galactic_conquest_save_slot2.json` |
| Galactic Conquest (slot 2, v12+) | `$XDG_DATA_HOME/stargwent/galactic_conquest_save_slot3.json` |
| Conquest run settings | `$XDG_DATA_HOME/stargwent/conquest_settings.json` |

On web (Pygbag/Emscripten) these paths resolve to
`/home/web_user/.local/share/stargwent/` backed by IDBFS. Every write
should be followed by `sync_saves()` (no-op on desktop) so the
in-browser IndexedDB layer flushes.

### Atomic Writes (v11.1+)

Use `save_paths.atomic_write_json(path, obj)` for every JSON save. It
serialises to a sibling `.tmp` file, then `os.replace()`s it over the
target — a `kill -9`, power loss, or OOM mid-write leaves the prior
good save intact instead of producing a half-written JSON file. The
helper handles `OSError` / `TypeError` / `ValueError` and cleans up
the temp file on failure. Already wired through:

- `deck_persistence.py` (decks + unlocks)
- `unlocks.py` (`save_unlocks`)
- `game_settings.py` (`_force_save`)
- `main_menu.py` (custom decks)
- `galactic_conquest/campaign_persistence.py` (campaign + conquest settings)

Do **not** call `json.dump(...)` to a final path directly in new code.

### Migration

`migrate_legacy_saves()` runs once per process via `ensure_migration()`
and copies pre-XDG saves from the working directory into the data dir.
Call sites at the top of `deck_persistence.py` and `game_settings.py`.

---

## Miniship Escort System (added v9.4.0)

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

### Prerequisites
- **Python 3.8+**, **Pygame CE 2.5.6+**
- **ModernGL** — optional GPU post-processing (`pip install moderngl`)
- **Pillow** — card assembler (`pip install Pillow`)
- **Pygbag** — web builds (`pip install pygbag`)

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
./build_release.sh 10.1.5            # Override version
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

### GitHub Actions CI/CD

The `Build Releases` workflow (`.github/workflows/build.yml`) builds
`.deb`, `.AppImage`, `.exe`, and `.dmg` in parallel. Two trigger
methods:

**Method 1 — Tag push (creates draft GitHub Release):**
```bash
git tag v11.1.0
git push origin main
git push origin v11.1.0
```
Creates a **draft** GitHub Release with all 4 platform artifacts
attached. Go to Releases to review and publish.

**Method 2 — Manual dispatch (downloads as artifacts):** Actions tab
→ **Build Releases** → **Run workflow** (top-right). Optional version
override; leave empty to read from the README badge. Artifacts have
1-day retention.

**Version detection:** the workflow reads
`![Version](https://img.shields.io/badge/version-X.Y.Z-blue)` from the
README. Priority is *manual input > git tag > README badge*.

**Web build:** `.github/workflows/web-deploy.yml` triggers on any push
to `main` that touches `.py`, `assets/`, `shaders/`, or `build/web/`.

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: moderngl` | Add `--hidden-import moderngl --hidden-import glcontext` to PyInstaller |
| Assets not found | Verify `--add-data` paths (`:` on Linux/macOS, `;` on Windows) |
| OpenGL errors in AppImage | `sudo apt install mesa-utils` |
| AppImage won't run | `sudo apt install fuse libfuse2` or `--appimage-extract` |
| macOS "app is damaged" | `xattr -cr Stargwent.app` |
| Save data location | `~/.local/share/stargwent/` (XDG) |

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

## Galactic Conquest Architecture

Roguelite card-battle campaign. Package: `galactic_conquest/` (~35 modules).
v10.0 was the original release; v11.0 deepened the strategic layer
(branching doctrines, AI doctrine adoption, expanded AI espionage,
coalition-against-player, 3-act crisis escalation, Economic + Cultural
victory paths, minor-world quest chains + rival courtship, active relic
abilities, unified Treaty system). v11.1 made the campaign save
atomic. **v12.0 ("Living Galaxy")** reshaped the mode around narrative
coherence: per-leader toolkits (92 actions across 40 leaders), rival
leader arcs with multi-phase comebacks + showdown battles, animated
AI-vs-AI wars, persistent map icons, diplomatic lane colors, hover
tooltips, activity log sidebar, scripted faction crises, hyperspace
transitions, multi-save slots. **v12.1** is an audit pass on top of
that rollout: the operative `state`/`status` field schism is fixed
(espionage code now reads the same key the writers use), the activity
sidebar + spy report cache their render surfaces, and six particle
update loops switched to mark-and-sweep. **v12.2** is a deeper,
whole-project audit covering every subsystem (card core, GPU pipeline,
animations, LAN, conquest, arcade): `spatial_grid` collision sites
deduplicated, particle/lightning/score-pop allocations cached, AI auto-aim
rewritten on squared distances, conquest save migration hardened,
naquadah upper-bound clamped, co-op snapshot truncation prioritised by
distance to the nearer player. **v12.2.3** is a targeted follow-up
patch: fixes a `NameError` crash in Galactic Conquest turn-advance when
rival events fire, hardens `construct_building` against double-build,
clamps `get_building_level` to a valid range, prevents a `LanSession`
close stall under concurrent keepalive sends, and closes a `Supergate`
freeze when a boss dies during gate activation. Per-version detail in
[CHANGELOG.md](CHANGELOG.md).

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
| `diplomacy.py` + `diplomacy_screen.py` | Faction relations, trade/alliance/betray, 13 AI proposal types, 3 player-initiated faction-unique actions, Treaty system (NAP + Alliance duration + Renew), coalition-against-player, strain warnings, incident handling |
| `buildings.py` | 5 building types with Lv 1-3 upgrades, level-scaled effects, doctrine cost reduction |
| `crisis_events.py` | 10 galaxy-wide events with 3-choice player agency (a/b/c with conditional Option C); chance scales with campaign act (5%/10%/15%) |
| `meta_progression.py` | Conquest Points, 5 perks, high scores, victory type multipliers |
| `minor_worlds.py` | 9 minor worlds: influence, quest chains (3-step), type bonuses, rival-suitor courtship + lockouts |
| `minor_world_screen.py` | CRT-styled minor world interaction panel with rival progress bar |
| `doctrines.py` | 5 doctrine trees (30 policies — 20 spine + 10 branches at tier 3), Wisdom economy, `get_active_effects()` |
| `doctrine_screen.py` | CRT-styled doctrine tree selection UI with "OR" divider at branch tiers |
| `espionage.py` | Operative lifecycle, 10 player missions, rank system, 6 AI espionage mission types, incident choices |
| `espionage_screen.py` | CRT-styled operative management UI |
| `victory_conditions.py` | 6 victory paths + score fallback (Domination/Ascension/Alliance/Supremacy/Economic/Cultural), progress tracking |
| `tooltip.py` | **NEW in 11.0**: shared tooltip renderer with wrap + clamp |
| `leader_toolkits.py` | **NEW in 12.0**: 40 leaders × 2-3 player-initiated map actions (92 total); templates + dispatcher |
| `leader_command.py` | **NEW in 12.0**: left-edge Leader Command panel UI |
| `rival_arcs.py` | **NEW in 12.0**: 5-phase rival arcs (EXILE → GUERRILLA → RESURGENCE → SHOWDOWN → RESOLVED) + showdown battle flow |
| `activity_log.py` + `activity_sidebar.py` | **NEW in 12.0**: persistent categorised log + right-edge slide-out sidebar |
| `relic_actives_panel.py` | **NEW in 12.0**: on-map spellbook of owned relic actives (15 of them now active) |
| `_ui_utils.py` | **NEW in 12.1**: shared `blit_alpha` helper for on-map panels |
| `spy_report.py` | **NEW in 12.0**: per-faction intel modal (S key) |
| `slot_picker.py` | **NEW in 12.0**: 3-slot save picker for New Campaign / Resume |

### Key Systems
- **Network Tiers**: Connected planet count → tier → scaling naq/cooldown/range/ability bonuses
- **Supply Lines**: Disconnected planets = -50% income, +20% counterattack, no fortification
- **Pre-Battle Preview**: ENGAGE/RETREAT screen with forces, weather, modifiers
- **Post-Battle Refresh**: `_refresh_after_battle()` — rebuild screen + `pygame.event.clear()`
- **Minor Worlds**: 9 neutral planets with influence (0-100), quests, ally exclusivity, 5 world types with Friend/Ally bonuses
- **Doctrine Trees (v11)**: Wisdom resource → 5 trees, each with a 4-tier spine plus two additive branches at tier 3 (mutually-exclusive via `conflicts_with` / `requires` fields). Tree completion keys off a `capstone: True` flag on tier 4. AI factions adopt doctrines every 8 turns up to tier 2 based on their personality's `preferred_tree`.
- **Treaty System (v11)**: `state.treaties` is the single source of truth for NAP and Alliance. NAP ticks to honored expiry (+10 favor), Alliance ticks to a "needs renewal" state (never auto-severs) with a `renew_alliance` action. `break_treaty` applies a -2 reputation-web trickle to all non-target factions and increments `broken_treaty_counts`, which vengeful personalities compound into future penalties.
- **Coalition Against Player (v11)**: `update_coalition_trust` accumulates trust toward each AI faction while the player holds ≥40% territory. At 80 trust with 2+ eligible weak factions, a 5-turn coalition forms (forced HOSTILE + `+50%` counterattack). Breaks on territory drop below 30%, 60+ naq in gifts to 2+ members inside a 3-turn window, or timer expiry. Gated behind `coalition_enabled` in `conquest_settings.json`.
- **Wisdom Actions**: After completing any doctrine tree, 4 repeatable wisdom sinks (card upgrade, cooldown reset, deck reveal, naq conversion)
- **Building Upgrades**: Lv 1→2→3 with `BUILDING_LEVEL_EFFECTS` lookup and `UPGRADE_COST_MULTIPLIERS` (1.5x/2.0x)
- **Espionage**: Tok'ra operatives with IDLE→MOVING→ESTABLISHING→ACTIVE lifecycle, 10 player mission types, rank 1-3. AI espionage (v11): 6 mission types — steal_naq, sabotage, rig_minor, sabotage_building, steal_doctrine (blocks next doctrine adoption for 2 turns), assassinate_operative. Diplomatic incident choices (deny/recall/double-down).
- **AI Diplomacy (v10.5)**: `generate_ai_proposals()` generates 13 proposal types (trade, ceasefire, peace, ultimatum, tribute demand, alliance offer, plus 7 faction-unique variants). Personality-driven favor + acceptance rates. v11 adds 3 player-initiated versions (Asgard Tech Exchange, Alteran Knowledge Sharing, Jaffa Revenge Pact).
- **Crisis Choices (v11)**: `CRISIS_CHOICES` dict provides 3 options (a/b/c) per crisis, with conditional Option C gated on requirements (relic, building, ally, doctrine, operative count). Crisis chance scales with campaign act: 5% (Act 1 / turns 1-10), 10% (Act 2 / 11-20), 15% (Act 3 / 21+). `get_current_act(turn_number)` is the source of truth for the act.
- **Active Relic Abilities (v11)**: Relics can expose an `active_ability` dict with charges tracked on `state.relic_active_charges`. v11 ships two out-of-battle actives: Asgard Time Machine (Shift+T, manual planet-loss rewind) and Sarcophagus (Shift+S, reset cooldowns + clear upgrade penalties). Mid-battle actives are intentionally deferred to avoid touching `card_battle.py`.
- **Quest Chains + Rivals (v11)**: 50% of new minor-world quests roll a 3-step chain (Defense Pact / Trade Route / Military Contract) tracked via `state.quest_chain_progress`. Each minor world also has one AI rival suitor ticking at +2 influence/turn — if they reach Ally tier first, trading with that minor world is locked out for 5 turns via `_mw_locked_*` keys.
- **Victory Conditions (v11)**: Six paths — Domination, Ascension, Galactic Alliance, Stargate Supremacy, Economic Hegemony (40%+ territory + 500 naq/turn for 3 consecutive turns, tracked in `state.consecutive_high_income_turns`), Cultural Ascendancy (4+ Ally minor worlds + 2+ relics), plus Score Victory as the turn 30 fallback.
- **Save Migration**: `SCHEMA_VERSION` constant in `campaign_state.py` with a non-mutating `_migrate` dispatcher. 11.0 adds 10 new state fields seeded in `_migrate_10_to_11`; legacy `_nap_timer_*` keys transparently migrate to `state.treaties`. **12.0 bumps schema to v12** via `_migrate_11_to_12`, seeding `leader_action_state`, `rival_arcs`, `activity_log`, and `save_slot` on pre-12 saves. Legacy single-save filename is treated as slot 0 for zero-friction upgrades; slots 1-2 use suffixed filenames.
- **Leader Toolkits (v12)**: `leader_toolkits.LEADER_ACTIONS` maps every `card_id` → `list[LeaderAction]`. Actions resolve via `can_use` → `execute` dispatch; cooldowns tick in the turn-end block. UI: `leader_command.draw_panel` emits `"leader_action:<id>"` on click; the controller's `_handle_leader_action` resolves targets (planet from selection, faction via modal picker).
- **Rival Arcs (v12)**: `rival_arcs.spawn_on_homeworld_capture` fires after the player takes a homeworld, choosing a hideout (preferring neutrals). `advance_all` ticks phase dwell time; `pending_showdowns` surfaces arcs that just hit SHOWDOWN for the controller's `_run_rival_showdown` modal. Four scripted pairs reuse `LEADER_MATCHUPS` dialogue; everyone else gets a generic arc.
- **Scripted Crises (v12)**: `SCRIPTED_CRISIS_EVENTS` in `crisis_events.py` — each has a predicate gated on faction state (Goa'uld planet count, Asgard network tier, Alteran doctrine mastery, etc.). `pick_crisis(state, galaxy)` prefers eligible scripted ones over random; one-shot per run via `conquest_ability_data["scripted_crisis_fired"]`.
- **Active Relics (v12, 4c)**: 13 relics gained `active_ability` entries on top of the 2 legacy ones. Unified `activate_relic` dispatcher handles all 15 effect types; `relic_actives_panel` renders the owned-relic spellbook beneath the Leader Command strip.
- **Emergency Anti-Coalition (v12)**: `victory_conditions.is_player_near_victory` returns `(bool, path)` for 5 of the 6 victory paths; the turn-end block in `campaign_controller` force-seeds every surviving faction's coalition trust to the formation threshold.
- **Living Map (v12)**: `map_renderer.draw` now overlays rival ghost icons, narrative arc stars, and diplomatic lane colors (via `_lane_diplo_color`) — coalition members pulse, allies green, trading blue, NAP amber, hostile red. `_draw_hover_tooltip` aggregates per-planet intel. AI-vs-AI wars animate via `_animate_ai_war_arc` on the controller side.
- **Activity Log (v12)**: `activity_log.log(state, category, text, ...)` appends a capped list (400 max) stored on `state.activity_log`. `activity_sidebar.ActivitySidebar` renders a right-edge slide-out toggled with `L`.
- **Hyperspace Transition (v12)**: `_map_to_battle_transition(direction, duration_ms)` drives the existing `shaders/hyperspace.py` shader's `warp_factor` uniform on both entry and return of every attack.
- **Side Panel UI**: `_draw_side_panel()` replaces tooltips — planet details with build/upgrade buttons when selected, victory/faction overview when not
- **Cross-system integration**: `get_active_effects(state)` is the central doctrine query — called by card_battle, buildings, diplomacy, espionage, minor_worlds, campaign_controller

---

## Space Shooter Architecture

Vampire Survivors-style infinite survival. Package: `space_shooter/`
(baseline v9.4.0; expanded through v10.x — see [CHANGELOG.md](CHANGELOG.md)).

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
- **Quick Chat**: Keys 1-0 (Stargate quotes — "Indeed.", "Kree!", etc.)
- **Unread Badge**: Count badge when chat minimized
- **Delivery Confirmation**: Unique message IDs + ACK protocol, checkmark on confirmed.
  In v11.1, `pending_acks` is only populated *after* the underlying
  `session.send()` succeeds, so a failed send no longer registers a
  ghost message that "times out".
- **Retry safety (v11.1)**: history entries store an explicit
  `raw_text` field; retries resend that instead of parsing the
  display-formatted string, so messages containing `": "` survive
  a retry intact.
- **Thread Safety**: Socket lock, duplicate disconnect prevention, parse error tolerance (5 consecutive), `deque(maxlen=1000)` inbox (atomic under CPython GIL), `time.monotonic()` for all timing, game action ACKs with single-retry. The disconnect sentinel uses `chat_inbox.put_nowait()` with overflow eviction (v11.1) so the reader thread can never wedge on a full chat queue.

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
- Saved to `player_decks.json` (atomic write — see [Save Persistence](#save-persistence))
