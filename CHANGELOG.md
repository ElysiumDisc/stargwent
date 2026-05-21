### Version 12.8.0 — "Ninth-Pass Audit + Living Galaxy II" (May 2026)
**Audit pass plus three larger improvements pulled in from the
deferred backlog: map-renderer label caching, AI-to-AI diplomatic
relations (resolves a long-standing TODO), and zlib-compressed co-op
snapshots.  ~90 candidate findings triaged, 5 verified-real fixes
shipped, ~20 confirmed already-fixed or false positives.**

Three Explore agents covered card-game core, rendering pipeline, the
Space Shooter, and Galactic Conquest. As in 12.7.0, every finding was
re-verified against current source before any code change — the
agent reports are a hint, not the diff.

**Core game — first-frame DT clamp**
- `main.py` — `state.clock.tick(...)` can return 100ms+ on the first
  frame after the user alt-tabs back in or returns from a debugger
  break. Unclamped, that single huge `dt` value would step shader
  time uniforms (kawoosh, hyperspace, replicator_swarm) by a full
  frame's worth at once and could expire multi-second hand-reveal
  timers in one tick. Clamped to 33 ms (a 30 FPS floor) at the
  single source before fan-out to subsystems.

**Frame renderer — Ring Transport target glow cache**
- `frame_renderer.py` — 12.7.0 had fixed the glow band along the
  Ring Transport beam by drawing two pygame lines directly, but the
  pulsing target circle at the destination was still
  `pygame.Surface(SRCALPHA)` allocated every frame during the drag.
  New module-level cache `_get_ring_glow_surf(radius, color)`
  mirrors the existing `_get_flash_surf` / `_get_halo_surf` /
  `_get_plague_surf` pattern from `space_shooter/game.py`: cache by
  (radius, color), animate alpha via `set_alpha()`. Bounded LRU at
  32 entries.

**Galactic Conquest map renderer — font label cache**
- `galactic_conquest/map_renderer.py` — the planet-loop in
  `draw()` called `self.font_name.render(planet.name, ...)` once per
  planet per frame. On a 60-planet galaxy that's 60 CPU font
  rasterisations every frame, plus more for fortification shields,
  operative diamonds, building icons, the rival arc glyph, the
  "GALACTIC CONQUEST" title, and the ESC hint. New per-instance
  `_label_cache` dict keyed on `(id(font), text, color)`; replaces 7
  font.render call sites. Cache lives with the MapScreen instance so
  it's discarded on resolution change.

**Galactic Conquest — AI-to-AI diplomatic relations (resolves TODO)**
- `galactic_conquest/diplomacy.py:1033` had carried an explicit TODO
  since pre-11.0: `on_faction_eliminated` gave every survivor the
  same -15 favor penalty because there was no way to know how the
  survivor felt about the eliminated party. 12.8.0 adds real AI-to-AI
  relation tracking:
  - `CampaignState.ai_to_ai_relations` — dict keyed on a sorted
    `"faction_a__faction_b"` pair string, value is favor in
    [-100, +100]. Schema bumped 12 → 13 with the seed-on-load
    migration pattern that already exists.
  - New helpers in `diplomacy.py`: `get_ai_relation`,
    `adjust_ai_relation`, `is_ai_hostile_to_ai`,
    `is_ai_friendly_to_ai`.
  - `on_faction_eliminated` now branches: -5 penalty if the survivor
    was hostile to the eliminated faction (relief), -15 default
    reaction, -25 if they were friendly (lost an ally, blamed on the
    player). Stale relation rows touching the dead faction are
    purged so saves stay clean.
  - Coalition formation now creates +25 AI-to-AI bonds between
    every pair of coalition members; if the player breaks the
    coalition with gifts, the bribed members take a -40 relation
    hit with the loyalists (finally backing the flavour line
    "they turn on each other" with state).
  - `tick_favor_decay` decays AI-to-AI relations at half the player
    rate so grudges and alliances between blocs outlast player-vs-AI
    swings.

**Space Shooter co-op — zlib-compressed state snapshots**
- `space_shooter/coop_game.py` `get_state_snapshot()` was emitting
  a full uncompressed dict every 3 frames (20 Hz host → client).
  Typical wire size: 2–5 KB per snapshot, 40–100 KB/s upstream.
- `space_shooter/coop_protocol.py` — new `pack_state_payload` /
  `unpack_state_payload` helpers. Snapshots ≥ 1 KB are
  `zlib.compress(..., level=1)` (host CPU-thread budget matters
  more than maximum size) and wrapped in a `{"_z": True, "data":
  "<base64>"}` envelope. Smaller snapshots pass through unchanged.
- `space_shooter/__init__.py` — host wraps via `pack_state_payload`
  before `session.send(CoopMsg.STATE, ...)`; client unwraps via
  `unpack_state_payload` on receive.
- `lan_protocol.py` — `PROTOCOL_VERSION` bumped 2 → 3 so older
  clients are rejected at the HELLO handshake instead of trying to
  parse the compressed envelope as a verbose-JSON snapshot.
- Wire reduction: JSON's redundant key strings compress to ~25% of
  their original size at level 1, so a 4 KB snapshot now flies as
  ~1 KB.

**Audit candidates checked but not shipped**

Re-verifying agent findings against current source caught these as
either already fixed, intentional design, or out of scope. Documented
for the next audit pass.

- *Space Shooter fire-rate not restored on powerup expiry* — already
  correct. `space_shooter/game.py:1354-1398` (`_expire_powerup`)
  restores `_saved_fire_rate` for rapid_fire, overcharge,
  lucian_kassa_stash, and ancient_ascension, with overlap-aware
  delete-on-last-expiry. Agent missed the function.
- *Weather floor clobbers Tactical Formation / horn / ZPM bonuses* —
  design intent. `docs/rules_menu_spec.md:55` explicitly states
  "Weather reduces non-Hero units to 1 power unless they have
  Survival Instinct". The 5-pass ordering in `game.py calculate_score`
  applies weather last on purpose.
- *Mulligan shuffle uses seeded `game.rng` but `game_setup.py:69,
  214` and `deck_builder.py:2716` use plain `random.shuffle`* — not a
  LAN-determinism bug. `lan_protocol.build_deck_message` transmits
  `deck_ids` as an explicit list; each side shuffles its own deck
  independently. Mulligan only needs determinism on a single side.
- *`CampaignState.from_dict` hard-codes `data["act"]` etc. without
  `.get()` defaults* — safe because `_migrate()` runs first and
  seeds every v11+ and v12+ field with `setdefault`. Verified by
  reading `_migrate_10_to_11` and `_migrate_11_to_12`. 12.8.0
  follows the same pattern for the new `ai_to_ai_relations` field.
- *`animations.py:2653` `pygame.image.load(...).convert_alpha()`
  in `ShipFlywayAnimation.draw()`* — false positive. Line 2653 lives
  inside `load_ship_image()` (defined at line 2631), which
  `BattleShip.__init__` calls exactly once at line 2629. The image
  is held on `self.raw_image`.
- *`AnimationPool` clears `on_complete` callbacks when returning to
  pool* — correct behaviour. Callbacks were already fired before the
  pool-return path runs; clearing the reference is cleanup, not a
  leak.
- *`FactionAbility._boost_tracker` double-initialised at lines 175
  and 180* — false positive. Line 175 is `__init__`, line 180 is
  `reset_round`. Both intentional.
- *AI difficulty hardcoded to `"hard"` (`ai_opponent.py:16`)* —
  acknowledged dead code (medium/easy branches at lines 759, 763
  exist but are unused). Out of scope for an audit release; the
  comment is self-documenting and players can't currently change
  it.
- *Activity sidebar font.render on every panel rebuild
  (`activity_sidebar.py`)* — already optimised. The panel cache
  rebuilds only when scroll/count changes, and each entry is
  rendered once per rebuild, not per frame.
- *`gpu_renderer.py:260` `pygame.image.tobytes()` per frame* — known
  bottleneck, but unavoidable without a complete render-pipeline
  redesign (Pygame surfaces have no zero-copy GL interop on most
  drivers). Documented for the future "render pipeline refresh"
  release.
- *AI passes/should_pass thresholds in `ai_opponent.py`* — tuning
  values, not bugs. Adjusting them without playtest data would
  change difficulty silently.

**File / version surface bumps**
- `game_config.py` `GAME_VERSION` 12.7.0 → 12.8.0
- `metadata.json` `version` 12.7.0 → 12.8.0
- `README.md` version badge → 12.8.0
- `DEVELOPMENT.md` build-instruction example version strings → 12.8.0
- `galactic_conquest/campaign_state.py` `SCHEMA_VERSION` 12 → 13
- `lan_protocol.py` `PROTOCOL_VERSION` 2 → 3

---

### Version 12.7.0 — "Eighth-Pass Audit" (May 2026)
**Full-stack bug hunt + perf audit. ~20 candidate findings triaged,
6 verified-real shipped, 11 confirmed already-fixed or false positives.**

Three Explore agents produced ~50 audit candidates across rendering,
core card battle, AI, Galactic Conquest, Space Shooter, networking,
sound, settings, and persistence. Every finding was re-checked against
current source before any code change — the established 12.5.x / 12.6.0
discipline. Verified-real items shipped here; everything else is
documented at the bottom of this entry so the agent reports can be
trusted (or skipped) by the next audit pass.

**Space Shooter — targeting + per-frame allocation fixes**
- `space_shooter/game.py` `_naquadria_cascade_chain` — chain lightning
  used `enemy.y` (top edge) for distance calculation while using
  `enemy.x + width//2` (center) for the x component. The result was a
  consistent half-height bias in target selection that preferred enemies
  *below* the player. Switched both x and y to enemy centers
  (`ecy = enemy.y + enemy.height // 2`) for the distance check and for
  the bounce origin so the chain visibly arcs from where it just hit.
- `space_shooter/game.py` `_naquadria_cascade_chain` — inner search
  now queries `self.spatial_grid.query_unique(current_x, current_y, 600)`
  instead of scanning every entry in `self.ai_ships`. Filters to `Ship`
  instances (asteroids are also in the grid). Reuses the existing grid
  populated each frame in `update()` — no new bookkeeping. With 50+
  enemies on screen at high waves, the 15-bounce inner loop drops from
  O(15·n) to O(15·k) where k is the count of enemies actually within the
  600px bounce radius.
- `space_shooter/game.py` halo + plague visuals — `pygame.Surface(...,
  SRCALPHA)` was allocated **every frame** for both the player Ascension
  halo ring (~one alloc/frame whenever ascension is active) and the
  Prior's Plague enemy tint (one alloc/frame per plagued enemy). Both
  now use module-level surface caches keyed on size, drawn once at full
  alpha, and animated with `set_alpha()` per frame. New helpers:
  `_get_halo_surf(halo_r)` and `_get_plague_surf(w, h)`, modelled on the
  existing `_get_flash_surf` pattern with a 20/30-entry cap to keep the
  caches bounded.

**Deck persistence — Alteran completeness**
- `deck_persistence.py` `_get_default_unlock_data` — `faction_wins` and
  `faction_games` seed dicts now include `"Alteran": 0`. Pre-12.7 saves
  were not broken (the `record_faction_*` helpers use `setdefault` at
  runtime), but stats UI on a fresh install would show 5 factions
  instead of 6 until the first Alteran game.
- `deck_persistence.py` `_migrate_unlocks` v1→v2 — seed dict gains the
  Alteran entry, plus a forward-looking backfill loop that
  `setdefault`s `"Alteran"` into `faction_games` and `faction_wins` on
  every load. Older 5-faction saves now self-heal to 6 factions on
  first run after 12.7.
- `deck_persistence.py` `_get_default_deck_data` — added an Alteran
  entry with `alteran_adria` as the default leader (matches the
  pattern used for every other faction). Lets the deck builder open
  the Alteran tab on first unlock without a special-case branch.

**Settings / circular import hygiene**
- `game_settings.py` — moved `import board_renderer` from the top of
  the module into `draw_back_button()` (the only function that uses
  it). The top-level import created the cycle
  `game_settings → board_renderer → display_manager → game_settings`,
  which CLAUDE.md and the existing display_manager-side lazy imports
  already worked around — game_settings was the one remaining piece.

**Galactic Conquest — silent failure visibility**
- `galactic_conquest/campaign_controller.py` — added a module-level
  `logger`. The `from transitions import …` block inside
  `_run_warp_transition` previously had a bare `except Exception: pass`
  that silently disabled every GC battle hyperspace transition if the
  shaders package failed to import (minimal builds, broken web build).
  Now logs a warning so the missing visual isn't a complete mystery.
  Other bare `except`s in the file (sound-load fallbacks, optional
  effect-disable cleanup) were verified as appropriate silent
  fallbacks and left alone.

**Documentation**
- `README.md` badge bumped to 12.7.0.
- `metadata.json` version bumped to 12.7.0.
- `game_config.py` `GAME_VERSION` bumped to 12.7.0.
- `CHANGELOG.md` — this entry.
- `DEVELOPMENT.md` — version-bump procedure example AppImage filename
  and git tag example updated to 12.7.0.

**Skipped (verified non-issues / already fixed in 12.5.x or 12.6.0)**
- `FACTION_ABILITIES` singleton dict shared-instance footgun — already
  removed in 12.6.0 (replaced with `FACTION_ABILITY_CLASSES` and
  per-player instances).
- `switch_turn()` infinite recursion on both-passed edge — already
  fixed in 12.6.0 (recursion replaced with in-line swap).
- Ring Transport drag-laser per-frame full-screen `SRCALPHA` surface
  alloc — already fixed in 12.6.0 (two `pygame.draw.line` calls).
- DHD radial gradient ellipse aspect ratio — already fixed in 12.6.0.
- Sarcophagus relic bypassing seeded `Game.rng` — already fixed in
  12.5.2.
- `render_engine.py:832` "per-frame leader portrait `pygame.image.load`"
  — false positive. Cache lookup at L823-824 hits first; load only
  runs on cold cache, then the result is stored back into
  `_leader_portrait_cache`. Steady-state hit rate is 100 %.
- `frame_renderer.py:1030+` "_surface_cache key collision between
  card_glow and ring_glow" — false positive. Keys are explicitly
  namespaced (`("card_glow", w, h)` vs `("ring_glow", w, h)`) and the
  color per namespace is constant, so no two effects share a cache slot.
- `game.py:795-810` "Tactical Formation multiplier over-inflates
  Hammond bonus" — false positive. Worked example: base 3 + Hammond
  +3 → displayed_power 6; TF (2 copies) → bonuses_applied = 6 − 3 = 3;
  displayed_power = (3 × 2) + 3 = 9. Not 18. The formula correctly
  preserves additive bonuses across the multiplier and matches the
  v12.5.1 "TF re-derivation" documentation.
- `game.py:1576` "Prior's Plague mutates `card.power` permanently
  across rounds" — verified intentional, matches the Life Force Drain
  pattern documented in `docs/rules_menu_spec.md` ("steals base
  power"). Plague is a permanent debuff by design; the rules entry
  is "On play: inflicts -1 power to all enemy units in the same row"
  with no per-round reset clause.
- `game.py:2755` "Ascension only fires on red-variant discards (scorch),
  not medic/decoy" — verified intentional. Ascension reads as
  "trigger on **destroyed** units"; medic moves a card *out* of the
  destroyed pool, decoy returns a card to hand (also not destroyed),
  so neither should refire Ascension. Mirrors the rules_menu_spec
  description ("on destroy: +1 to all remaining friendly units").
- `ai_opponent.py:899-904` "AI medic crashes on empty discard" — false
  positive. `select_best_medic_target` at L649-657 has explicit
  `if not revivable: return None`, and the caller at L879-886 checks
  for None before scoring.
- `space_shooter/spatial_grid.py` "grid never inserted with enemy
  positions" — false positive. Grid is populated each frame in
  `SpaceShooterGame.update()` (`spatial_grid.clear()` then
  `spatial_grid.insert(ai_ship, ...)` and asteroid insertions) and
  queried by every hostile-all projectile collision pass. Chain
  lightning was the one outlier that bypassed it — now fixed (above).
- `sound_manager.py:46-73` "reserved channels can be empty → IndexError
  in `get_critical_channel`" — false positive.
  `get_critical_channel(index)` guards with
  `if 0 <= index < len(self._reserved_channels): return …; return None`,
  and every caller (`play_critical_sound`, etc.) checks for `None`
  before using the channel.
- `galactic_conquest/campaign_state.py:301-309` "`tick_cooldowns`
  mutates dict during iteration" — false positive. Updating values
  of *existing* keys during iteration is safe in Python; the separate
  `expired` list defers actual key removal. The pattern is fine; a
  dict comprehension would be equivalent.
- `main_menu.py:240-252, 358-361, 600-603` "per-frame `pygame.font.SysFont`
  allocations" — false positive. L240-252 is `__init__`-time (once per
  MainMenu instance), L358-361 is `run_settings_menu` init (once per
  settings open), L600-603 is the post-fullscreen-toggle geometry
  refresh block (one-shot when window mode changes), not the draw loop.
- `animations.py:78-83` "12 animation classes lack `reset()` so pool
  reuse falls back to `__init__`" — verified all 66 classes lack
  `reset()` by design. `__init__` reinitialises a small fixed number
  of attributes; a hypothetical `reset()` would do the same work. The
  pool's `return_animation` already clears retained references
  (`card_image`, `trail`, `hearts`, `on_complete`, `_cached_scaled_*`)
  to prevent leaks.
- `gpu_renderer.py:260, 274` "per-frame full-surface CPU→GPU upload
  via `pygame.image.tobytes`" — verified architectural cost, not a
  bug. The Pygame surface is the canvas; gameplay touches arbitrary
  pixels every frame, so dirty-rect tracking would require deep
  integration with every renderer that touches the surface. At
  2560×1440 RGBA the upload is ~14.7 MB/frame (~880 MB/s at 60 FPS),
  ~0.5 ms on a modern PCIe 3.0+ system. Acceptable for now. Worth
  revisiting if profiling on lower-end hardware shows it as the
  primary frame-time consumer.
- LAN keepalive heartbeat (PROTOCOL_VERSION bump 2→3) — deferred. The
  v3 bump would silently break compatibility with v12.6.0 clients
  even with backward-compat code, because v12.6.0 peers don't yet
  know to ignore unknown opcodes. Will reconsider in a release that
  also ships a version negotiation mechanism.

- Bumped to 12.7.0 in `metadata.json`, `game_config.py`, and the
  README badge.

### Version 12.6.0 — "Resolute Raccoon" (May 2026)
**Ubuntu 26.04 compat + full-stack audit pass**

The headline fix is AppImage support on Ubuntu 26.04. Alongside that, an
end-to-end audit of LAN networking, core card battle, rendering, side
modes, build system, and documentation landed real fixes where issues
were verified and skipped a meaningful pile of agent-flagged "bugs" that
turned out to be either already-correct code or intentional game
mechanics.

**Packaging — Ubuntu 26.04 AppImage support**
- `build_appimage.sh` switched from the old `AppImageKit` appimagetool
  (FUSE2-only, March 2023 binary) to the new `AppImage/appimagetool`
  release. The produced AppImage now uses the **type2-runtime static
  FUSE3 runtime** via `--runtime-file`, so it launches on Ubuntu 26.04
  without manual `libfuse2t64` install.
- Added `build/appimage.excludelist`: keeps host-bundled libc, libssl,
  libstdc++, libGL, libX11/wayland, FUSE, audio libs out of the AppImage
  so they resolve against the user's host (matched to host glibc).
- `appimagetool` itself now runs via `--appimage-extract-and-run`, so
  the build host doesn't need FUSE installed either.
- `requirements.txt` + `requirements-build.txt` introduced; both
  `build_appimage.sh` and `build_deb.sh` install from pinned requirements
  for reproducible builds.

**CI — `.github/workflows/build.yml` overhaul**
- Linux job runs on a matrix `[ubuntu-22.04, ubuntu-24.04]`; canonical
  release artifacts upload from the 24.04 leg, 22.04 is a regression
  sentinel.
- 22.04 leg installs `libfuse2`, 24.04 leg installs `libfuse2t64`
  (t64 rename). Both include `desktop-file-utils` + `file` for
  appimagetool validation.
- New `lint` job runs an import smoke test on Python 3.11 / 3.12 / 3.13
  so the README's "3.11+" support claim is actually tested.
- macOS pinned to `macos-14`, Windows pinned to `windows-2022` (no more
  `*-latest` surprises).
- All jobs use pip cache via `actions/setup-python@v6` keyed on
  `requirements*.txt`.
- Release job extracts the matching `### Version X.Y.Z` section out of
  CHANGELOG.md and injects it into the GitHub Release body. Pre-build
  step warns when no changelog entry exists for the target version.

**LAN networking (real desync / security fixes)**
- `lan_game.py`: host shared-RNG seed now generated with
  `secrets.randbits(32)` instead of unseeded `random.randint`, so a
  rapid-restart of the host can't produce near-identical seeds and
  undermine the deterministic-shuffle contract both peers rely on.
- `lan_protocol.py`: `parse_message()` extended with schema validation
  for `GAME_ACTION` (whitelisted action names, integer score bounds,
  target_id length cap), `SEED` (uint32 range check), and `MULLIGAN`
  (index range check). A malicious peer can no longer feed negative
  scores, path-traversal target IDs, or unknown action types through.
- `lan_context.py`: `next_turn_token()` now wraps its increment in a
  `threading.Lock`. Without it the UI thread, network reader, and game
  loop could collide and hand out duplicate tokens — the very thing the
  desync detector treats as fatal.
- `lan_session.py`: chat queue maxsize raised from 100 to 500 (aligned
  with the game inbox at 500), with a rate-limited dropped-count log
  and a `get_chat_drop_count()` accessor so the UI can surface
  saturation.

**Core card battle**
- `game.py` `_cleanup_round`: per-round leader-boost flags
  (`hammond_boosted`, `kalel_boosted`, `kiva_boosted`, `adria_boosted`)
  now cleared across discard + hand zones in addition to the board. A
  Hammond-boosted card that died mid-round and was later revived by
  Medic no longer carries undeserved +3 into the next round.
- `game.py` `switch_turn`: when the next player has already passed, the
  function now swaps in-line instead of tail-calling itself. The
  recursion would never have unwound on a "both passed" edge case.
- `FACTION_ABILITIES` (singleton dict, dead code) replaced with
  `FACTION_ABILITY_CLASSES` (class registry). `Player.__init__` was
  already creating fresh per-player instances; this removes the parallel
  inline class table and the shared-instance footgun for good.
- `dhd_button.py`: radial gradient now scales its ellipses to the
  button's actual aspect ratio. Previously fixed at 2:1 regardless of
  size, producing visibly squashed gradients on near-square buttons.
- `deck_persistence.py`: card-id migration now refuses to run if
  `cards.ALL_CARDS` failed to import, instead of silently accepting
  every migration with no validation.
- `draft_mode.py`: new `_build_balanced_fallback_pool()` ensures each
  faction has at least 6 cheap-common cards in the pool when player
  unlocks are sparse. Stops the early-account draft from collapsing
  into a Neutral-heavy single-faction soup.
- `cards.py`: hero-cost check now uses `abilities.is_hero()` instead of
  a hand-rolled `"Legendary Commander" in self.ability` string scan.

**Rendering / GPU**
- `gpu_renderer.py` `present()`: before releasing the old input texture
  on a resize, calls `ctx.finish()` to drain in-flight GPU work (avoids
  texture leaks on some Intel/AMD drivers) and invalidates stale FBO
  pool buckets via `fbo_pool.cleanup_stale()`.
- `gpu_renderer.py` `resize()`: same `ctx.finish()` + `cleanup_stale()`
  treatment, plus the method now actually wires `cleanup_stale()` in
  (the method existed but was never called).
- `gpu_renderer.py` `present()`: clears the screen FBO with `ctx.clear`
  before the final composite blit — prevents uncleared garbage in
  margin areas on the first frame after a window resize.
- `frame_renderer.py`: Ring Transport drag laser glow replaced with two
  `pygame.draw.line` calls direct to screen. Previously allocated a
  full bounding-box SRCALPHA surface every frame during drag — up to
  ~10MB/frame at 2560×1440 with cards on opposite sides of the board.

**Side modes**
- `space_shooter/projectiles.py`: `OriBossBeam.line_circle_intersect`
  now guards against zero-length beams before dividing by `2*a`
  (would have crashed or produced inf on a degenerate beam).
- `space_shooter/game.py`: Prior Plague spreads to up to 3 nearby
  enemies per 4-second cycle instead of just 1. The old single-target
  `break` made the visual outbreak barely noticeable on dense waves.

**Documentation**
- README card count corrected: 288 → 287 (actual `ALL_CARDS` entries).
- README Python badge corrected: 3.8+ → 3.11+ (matches what CI tests).
- DEVELOPMENT.md shader count corrected: 14 → 15 (added
  `replicator_swarm` to the list).
- DEVELOPMENT.md: new "Ubuntu 26.04 support" subsection explains the
  static FUSE3 runtime change and the `--appimage-extract-and-run`
  fallback for AppArmor-restricted hosts.
- DEVELOPMENT.md: new "Version bump procedure" subsection enumerates
  the four files that hold the version string and the grep command to
  audit for stale references.
- AppImage install troubleshooting updated for the libfuse2/libfuse2t64
  rename and the new no-FUSE-needed v12.6.0 builds.
- `build_deb.sh` package description card count corrected: 247 → 287.

**Skipped (verified to be non-issues during the audit)**
- Newline-delimited LAN framing: safe because `json.dumps` escapes
  embedded `\n` as `\\n` text — the actual newline byte never appears
  in the encoded output.
- Weather + Survival Instinct power overwrite: behaviour matches
  Gwent's canonical weather rule (weather obliterates buffs) — both
  the survival and non-survival branches behave consistently.
- LAN handshake message race: HELLO is already special-cased in the
  reader and never enters the regular inbox.
- LAN session close ordering: `close()` already sets `stop_event`
  before `join()` and uses `sock.shutdown` to break blocking recv.
- Galactic Conquest battle state contamination: each card battle
  constructs a fresh `Game()` instance, so leftover state from a
  previous battle is structurally impossible.
- LanLobby state reset between matches: lobby is re-instantiated on
  each `run_lan_lobby` call, so flags start fresh every time.
- Several other agent findings (faction ability shared singletons via
  dead `FACTION_ABILITIES` dict reads, `_refresh_after_battle` clearing
  space-shooter properties on a card-battle controller, etc.) turned
  out to reference code paths that don't actually run.

### Version 12.5.2 — "Seventh-Pass Audit" (May 2026)
**Audit verification + 11 fixes shipped, 12 false positives rejected**

A seventh-pass audit covering ~30 reported issues across `game.py`,
`galactic_conquest/card_battle.py`, `galactic_conquest/campaign_controller.py`,
`space_shooter/game.py`, and the `lan_*.py` networking files. Each finding
was verified against current source before any code change: **16 held up,
4 were partially accurate, and 12 were false positives** where the cited
"bug" was either correct logic the reporter misread or code that never
executes. The 11 highest-value fixes were applied; the remaining real-but-
minor items are documented below for future passes.

#### Multiplayer determinism (RNG correctness)
- **`game.py:237` DHD fell through to global `random` when no rng arg
  was passed.** `DHDMechanic.use(self, player, rng=None)` had
  `rand = rng or random`, so any caller that forgot to thread the game
  rng would silently desync LAN matches. Switched the fallback to
  `getattr(player, "_rng", random)` — `Player._rng` is already wired to
  `Game.rng` at construction (line 673), so seeded matches now stay
  deterministic even when the call site is sloppy. Note: no production
  call site invokes `.use()` today (the DHD button is a UI back-button,
  unrelated), so this is a defensive fix against future wiring.
- **`game.py:3066-3068` Sarcophagus relic bypassed `Game.rng` entirely.**
  The Conquest Sarcophagus revive block did
  `import random as _rng; _rng.choice(self.player1.discard_pile)`,
  reaching for the module-global RNG instead of the seeded
  `self.rng.choice` used everywhere else on the round-advance path.
  Replaced with `self.rng.choice(...)` and dropped the local import.

#### Networking hardening (LAN multiplayer attack surface)
- **`lan_protocol.py` had no payload size caps.** Added
  `MAX_DECK_IDS = 40` (matches `deck_builder.MAX_DECK_SIZE`),
  `MAX_CHAT_LEN = 512`, and `MAX_PAYLOAD_BYTES = 65536`. Builders
  reject/truncate before send (`build_deck_message` raises
  `ValueError` on oversized lists; `build_chat_message` truncates).
  `parse_message` re-validates on the receive side so a hostile peer
  using their own builder can't bypass the check.
- **`lan_session.py:175` second-pass buffer scan + no per-frame size
  cap.** The recv loop did `while b"\n" in buffer:` followed by
  `buffer.split(b"\n", 1)`, scanning the buffer twice per iteration.
  Replaced with a single `buffer.find(b"\n")` then slice. Also added a
  pre-JSON `len(line) > MAX_PAYLOAD_BYTES` check so a peer streaming a
  single huge line just under the 1 MB session ceiling gets dropped
  instead of feeding `json.loads`.
- **`lan_session.py:228` log injection via corrupted data.** The JSON
  parse-error branch logged `line[:100].decode("utf-8", errors="replace")`
  directly to stdout, letting a peer inject ANSI escape sequences,
  carriage returns, or terminal control codes into the host's terminal
  / log file. Switched to `repr(line[:100])` so non-printable bytes are
  rendered as `\x1b` rather than executed by the terminal.
- **`lan_game.py:112` seed taken from peer with zero validation.**
  `seed = payload.get("seed", 0)` was fed straight to `random.seed()`,
  so a malicious peer could send `seed: "haha"` (TypeError mid-match)
  or `seed: <huge bigint>`. Wrapped in `int()` with bounds check
  `0 <= seed < 2**32`; falls back to 0 with a warning on bad input.

#### Game features
- **`space_shooter/game.py:386-388` mission restart silently dropped
  mission config.** Pressing R after death called
  `self.__init__(...)` without forwarding `mission_type` or
  `mission_target`, so any restart from a campaign mission dumped the
  player into the default infinite-survival scenario. Threaded both
  arguments through the re-init call.

#### Performance
- **`game.py:744` `Player.build_deck` deep-copied through every
  `ALL_CARDS.values()` filter on every Player construction.** Two
  Players are built per match plus mid-match Sarcophagus/clone paths
  that may re-instantiate. Added a module-level `_FACTION_CARD_POOL`
  built once at import (faction → list of card refs); `build_deck`
  now deepcopies from the cached list. Filter scan cost amortises to
  zero; deepcopy cost (the dominant term) is unchanged because card
  state still has to be per-player.
- **`game.py:964, 1040-1042` `self.history.pop(0)` was O(n).** History
  was a plain list with a `if len > 200: pop(0)` ring-buffer hack —
  every overflow shifted up to 200 entries. Switched to
  `collections.deque(maxlen=200)`; appends now evict the oldest entry
  in O(1) and the manual length check disappears. Verified all
  consumers (render_engine.py iteration + `entries[-1]` slice) work
  unchanged on `deque`.
- **`galactic_conquest/card_battle.py:113-152` three identical
  `ALL_CARDS.items()` filter comprehensions.** The Elite-defenders,
  Ancient-ZPM, and Extra-defense paths each rebuilt the same
  faction-filtered list (excluding Legendary Commanders + weather).
  Extracted a `_faction_pool(faction)` helper with a
  `_FACTION_POOL_CACHE` dict so each faction's pool is computed once
  per process. Also collapses the three `getattr(c, …)` ladders.

#### Code robustness
- **`abilities.py:92-98` substring matching was permissive.**
  `has_ability` did `if ability.value in ability_str:`, which works
  today only because no two ability names are substrings of each
  other — a fragile invariant. Added `_ability_tokens()` that splits
  the comma-separated ability field, strips
  `"Name: descriptive text"` suffixes (e.g. `"Ring Transport: Return
  to hand"` → `"Ring Transport"`), and returns a set; `has_ability`
  and `get_abilities` now do exact membership. All 41 distinct
  ability strings in `cards.py` round-trip through the new tokeniser
  to the same enum members as before. Future-proofs against any
  ability name that's a substring of another.

#### Audit findings verified false (no code change)
- **`game.py:1350-1351` "Doci Spy conversion loses +5 power after
  scoring."** False. The conversion sets both `card.power = 5` and
  `card.displayed_power = 5`; `calculate_score` Pass 1 resets
  `displayed_power` to `power` (preserving the 5), and Pass 2
  bonuses are additive on top.
- **`game.py:1221` "Hathor ability infinite-loops when both players
  pass."** False. Line 1189 short-circuits with an early `return`
  when `player1.has_passed and player2.has_passed`, so the recursive
  `switch_turn()` at 1221 can never fire in the both-passed state.
- **`game.py:906, 3449` "Clone token discards go to wrong player's
  pile."** False. `Player.decrement_clone_tokens` appends to
  `self.discard_pile` (correct owner — it's a method on `Player`).
  `Game.decrement_all_clone_tokens` calls
  `self.discard_card(player, card, …)` with an explicit player
  argument, so routing is correct.
- **`game.py:798-802` "Tactical Formation Pass 3 breaks additive
  bonuses."** False. The pass computes
  `bonuses_applied = displayed_power - power`, applies the
  multiplier to base `power`, then re-adds `bonuses_applied`.
  Additive bonuses survive the multiplier exactly as the comment at
  line 759 documents.
- **"Faction powers missing `game=self` parameter — artifact bonuses
  don't apply after row swaps."** False. `apply_to_score(player)`
  doesn't reference game state; artifacts (which do) already receive
  `game` via `artifact.apply_effect(game, self)` at line 826.
- **`galactic_conquest/card_battle.py:142-145` "Weaken enemy hits
  Legendary Commanders."** False. Leaders aren't in `current_deck` —
  they're stored as a separate `Player.leader` attribute, so
  `ai_deck.pop(random.randrange(len(ai_deck)))` can't touch them.
- **`galactic_conquest/card_battle.py:123-130` "Kull Armor ordering
  inconsistent."** False. The ordering — apply elite bonus first,
  then `_apply_relic_combat_modifiers` (which subtracts Kull Armor)
  — is intentional. Boost-then-weaken matches the documented
  intent.
- **`galactic_conquest/campaign_controller.py:367 + 390-395`
  "Duplicate cooldown processing."** False. Line 367's
  `tick_cooldowns()` is the standard per-turn decrement; lines
  390-395 apply an additional cooldown-reduction *passive* on top.
  Two distinct effects, sequenced correctly.
- **"Network cache staleness on same-turn ownership changes."**
  False. No such cache exists in `campaign_controller.py`; territory
  ownership and faction relations are read live from `self.state`.
- **"`campaign_controller.py` repeats ALL_CARDS iteration in
  multiple functions."** Two iterations, not three; serve different
  purposes (faction bonus at 1963, defense bonus at 2013). Not
  redundant.
- **"`campaign_controller.py` multiple `faction_relations`
  iterations per turn."** Two iterations, both necessary (income
  phase at 446, reward selection at 864). Not redundant.
- **`space_shooter/game.py:1972` "Supergate projectile damage
  capped at 1/frame."** False. The hit applies full `proj.damage`;
  the 1-per-frame is a per-supergate-projectile cap, not a global
  damage rate.
- **`space_shooter/game.py:1867-1869` "Time unit mismatch (frames
  vs seconds)."** False. Every comparison in the block uses
  `survival_seconds` consistently.
- **`lan_game.py:38-47` "Busy-wait polling in `wait_for_message`."**
  False. The loop already includes `await asyncio.sleep(0.05)`.

#### Deferred (real but low-value)
Documented for a future audit pass; no urgency:
- `card_battle.py:140` AI deck never shuffled after passive-card
  insertions. Player deck is shuffled at 89; impact on randomness is
  small because draws are still random.
- `card_battle.py:192` weather-row validation only checks dict-key
  presence — silent no-op on a typo, but no user-facing path can
  trigger it today.
- `deck_builder.FACTION_LEADERS` access via `.get(faction, [])`
  silently returns empty on bad faction; only fails on dev typo.
- `card_battle.run_card_battle` returns outcome strings only; no
  battle statistics export. Feature work, not a bug.
- `lan_session.py` has no peer authentication. Design decision
  pending — only relevant if anyone plays on hostile networks.
- `lan_game.py:113-114` direct `remote_payload["faction"]` /
  `["leader_id"]` access without try/except. Some upstream
  validation at 99-104 narrows the risk.
- `lan_game.py:156-157` mutates `game_main.LAN_MODE` /
  `LAN_CONTEXT` module globals. Cleaner state-management pending.

#### Manual test plan
1. **RNG determinism**: host + join a LAN match with a fixed peer
   seed; trigger Sarcophagus revive at round-advance and confirm
   both peers select the same revived card.
2. **LAN size cap**: have a peer (or test harness) emit a deck
   message with 100 deck_ids; receiver should disconnect cleanly
   with "Oversized frame" log, no OOM.
3. **Seed validation**: emit `{"type":"seed","payload":{"seed":"x"}}`
   from peer; client should warn and fall back to seed 0 without
   crashing.
4. **Mission restart**: enter Galactic Conquest mission, die, press
   R — same mission should reload (kill counter resets, mission
   target preserved).
5. **History scroll**: play a long match (>200 events) and scroll
   the history panel — oldest entries should evict cleanly with no
   visual hitch.
6. **Card abilities**: play any Lucian Alliance Medical Evac and
   confirm the medic UI opens (verifies tokeniser preserves
   `"Medical Evac"` matching). Play Puddle Jumper and confirm Ring
   Transport prompt appears (`"Ring Transport: Return to hand"`
   → token `"Ring Transport"`).

#### Version
- Bumped to 12.5.2 in `metadata.json`, `game_config.py`, and the
  `README.md` badge.

---

### Version 12.5.1 — "Sixth-Pass Audit" (May 2026)



#### Crash / logic
- **`game.py:1467-1472` Mothership/Prometheus name-substring matching
  drew cards for the wrong cards.** The played-card draw trigger used
  `"Prometheus" in card.name` and `"Mothership" in card.name` (with an
  unguarded fallback), so playing **Ha'tak Mothership** (Goa'uld,
  power 6, ability `Gate Reinforcement`), **Alliance Mothership**
  (Lucian, power 10, no draw ability), or **O'Neill-Class Mothership**
  (Asgard, power 8, ability `Command Network`) all silently triggered
  `draw_cards(2)` despite none of them having a draw ability. The basic
  `tauri_prometheus_1/2` ("X-303 Prometheus", power 6, ability `None`)
  were similarly drawing 1 despite having no ability text — only
  `prometheus_x303` (power 8, "Draw 1 card when played") was supposed
  to. Replaced both substring matches with an explicit `card.id` →
  `draw_count` dict containing only `prometheus_x303` (1) and
  `asgard_mothership` (2). A `card.ability` substring approach was
  considered and rejected — `"Draw 1"` and `"Draw 2"` would both match
  any `"Draw"` enum, putting us right back where we started.

#### Audit findings verified false (no code change)
- **`draft_mode.py:260` "syntax error in min() call"** — code is valid
  Python; the reporter's "broken" and "fixed" snippets were identical
  strings.
- **`ai_opponent.py:17` "power_used never reset between rounds"** —
  faction power is **once per game** by design (see comment at
  `game.py:738`: `# Track faction power usage (once per game)`). Both
  player and AI follow this rule; `AIStrategy.power_used` mirrors
  `Player.power_used` correctly.
- **`game.py:2555-2559` "Sodan trigger inconsistent"** — works
  correctly. Only `sodan_warrior` carries the matched ability string,
  so the dual `name AND ability` check resolves to exactly one card.
- **`cards.py:381` "Puddle Jumper colon syntax fragile"** — the
  ability `"Ring Transport: Return to hand to replay"` matches
  `Ability.RING_TRANSPORT` ("Ring Transport") via the existing
  substring search. The colon-suffix pattern is the established
  convention for descriptive abilities.
- **"`abilities.py:96-98` is O(26) per call"** — misread.
  `has_ability(card, *abilities)` iterates the **variadic args**
  (typically 1–5), not the 26-member `Ability` enum. Only
  `get_abilities()` (line 117) iterates the full enum, and it is not
  on a hot path.
- **"`game.py:788-802` 5-pass score calculation is slow"** — the pass
  ordering (reset → additive → Tactical Formation → Horn/ZPM →
  Weather + sum) is required for correctness. Collapsing passes would
  break the `bonuses_applied = displayed_power - power` invariant that
  Tactical Formation relies on. Already optimised in v12.5.0 from ~10
  passes to 5.

#### Manual test plan
1. Goa'uld vs. Asgard skirmish: play Ha'tak Mothership — hand size
   must **not** increase. Play Asgard Mothership — hand size must
   increase by 2 (subject to deck/cap limits).
2. Lucian skirmish: play Alliance Mothership — hand size must **not**
   increase.
3. Tau'ri skirmish: play `tauri_prometheus_1` (basic X-303 Prometheus,
   power 6) — hand size must **not** increase. Play `prometheus_x303`
   (Prometheus X-303, power 8) — hand size must increase by 1.
4. Asgard skirmish: play O'Neill-Class Mothership — hand size must
   **not** increase.

#### Version
- Bumped to 12.5.1 in `metadata.json`, `game_config.py`, and the
  `README.md` badge.

---

### Version 12.5.0 — "Fifth-Pass Audit" (May 2026)
**Audit verification + 13 of 18 backlog items shipped**

A re-audit pass over the v12.4 backlog. Each of the 18 reported issues
was verified against current source before any code change: 10 were
accurate, 3 partially accurate, and **5 were false positives where the
"bug" was either intended behaviour or already correct in the existing
code**. The 13 verified fixes were then implemented under the prioritised
order critical → performance → balance → low. No save schema changes;
all 12.x saves load cleanly.

#### Crash / logic
- **`espionage.py:399` undefined `NEUTRAL` constant.** The
  `forge_alliance` mission only imported `NEUTRAL_REL` from `diplomacy.py`
  but compared against bare `NEUTRAL`, so the Hostile→Neutral→Trading
  upgrade path raised `NameError` mid-mission for any player who actually
  reached the Neutral tier. Replaced with `NEUTRAL_REL`.
- **Counter-intel detection silently broken.** Operatives serialise via
  `Operative.to_dict()` with key `"mission"`, but
  `galactic_conquest/espionage.py:537,695` was reading and writing key
  `"current_mission"`, which never existed in the dict. `op.get(...)`
  always returned `None`, so AI espionage events never registered the
  player's counter-intel operative as a threat. Fixed both call sites to
  the canonical `"mission"` key. Symptom was invisible (operatives
  appeared deployed and the player saw no error), so this had been live
  for several versions.
- **AI hardcoded to Player 2.** `ai_opponent.py:15` set
  `self.opponent = game.player1` with a comment "Assume AI is always
  player2", blocking any AI-controls-player1 mode (AI-vs-AI demos, swap-
  sides debug, future spectator mode). Replaced with a parameterised
  lookup: opponent is the *other* player relative to `ai_player`.
- **`card_battle.py` returned `"draw"` on validation failure.** When a
  player deck was below the 10-card minimum the function returned
  `"draw"`, but the AI-deck-too-small branch on the very next line
  returned `"player_win"`. The asymmetry meant a player who somehow
  shipped a busted deck got a free draw instead of a proper loss. Now
  returns `"player_loss"` (already a handled case in
  `campaign_controller._run_card_battle`).
- **Defensive `rng.choice` guards in Apophis weather.**
  `_activate_apophis_weather` calls `self.rng.choice(weather_rows)` and
  `self.rng.choice(options)` on hardcoded lists. The current lists are
  always non-empty so no real crash today, but a future refactor that
  drove either list empty would crash on a leader power activation.
  Added `if not weather_rows or not options: return None` belt-and-
  suspenders. The other 7 `rng.choice` sites flagged in the audit
  (`game.py:238, 1122, 1720, 1757, 2258, 3087, 3136`) were already
  guarded — verified and left alone.

#### Performance
- **`Player.calculate_score` board sweeps reduced from ~10 → ~5.** This
  is the inner loop of every `play_card` and `end_round`, and was doing
  separate full-board iterations for: reset, Hammond +3, Ka'lel +2,
  Tactical Formation, Inspiring Leadership, Horn ×2, ZPM ×2, weather,
  and final sum. Merged:
    - **reset + Hammond + Ka'lel + Inspiring Leadership** into one
      additive sweep (IL moved before TF — semantically equivalent
      because TF preserves additive bonuses via
      `bonuses_applied = displayed - power`);
    - **Horn + ZPM** into one multiplicative sweep guarded by the
      existing `horn_multiplied` set so no card 4×-stacks;
    - **weather + final sum** into one terminal sweep.
  TF, leader-ability dispatch, alliance combos, and artifacts remain
  separate — they have ordering dependencies on the additive bonuses
  being fully applied first. Output identical for all tested boards
  (Hammond + TF, Horn + ZPM siege, Weather + Survival Instinct).
- **`select_hathor_target` row-power hoisted out of the candidate loop.**
  `ai_opponent.py:605` was recomputing `sum(c.power for c in
  self.opponent.board.get(card.row, []))` once per candidate inside the
  scoring loop — O(n²) in board size. Pre-built a `row_power_by_row`
  dict before the loop; per-candidate evaluation now O(1). Trivial impact
  in absolute terms (boards top out around 30 cards) but meaningful for
  Hathor turns at higher difficulties.
- **`PowerUp.draw` glow surface cached.** `space_shooter/entities.py:601`
  allocated a fresh `pygame.Surface(SRCALPHA)` every frame, every powerup.
  Now cached on a class-level `_glow_cache` dict keyed by `glow_size`
  (small integer domain from the pulse animation, ~10 distinct values),
  cleared with `fill((0,0,0,0))` on reuse. Eliminates ~60 SRCALPHA allocs
  per powerup per second under load.
- **`XPOrb.draw` orb surface cached.** Same pattern, keyed by `pulse_r`.
  Matters during boss kills and other XP-orb shower moments where the
  on-screen orb count spikes.

#### Balance (user-confirmed numbers)
- **Fire-rate scaling switched from compounding to stack-additive.**
  `space_shooter/game.py:1581` used `ship.fire_rate = max(5, int(
  ship.fire_rate * 0.9))` — multiplicative 10%-per-stack on the live
  field meant `rapid_capacitors` stacked extremely steeply (≈47 % faster
  at 6 stacks, ≈77 % at 14). Wired up the previously-unused
  `self.base_fire_rate` field (initialised at ship creation) and replaced
  the formula with `max(5, int(base_fire_rate / (1 + 0.07 * stacks)))`.
  Asymptotes toward zero — early stacks still feel impactful, late stacks
  add diminishing returns instead of breaking the game.
- **XP curve growth rate halved.**
  `self.xp_to_next = int(480 * 1.25 ** (self.level - 1))` →
  `int(480 * 1.15 ** (self.level - 1))`. Level 30 needs ~31 K XP instead
  of ~388 K; the late-game grind is now reachable in a normal session.
  Existing players' `xp_to_next` only recomputes on level-up, so live
  saves transition smoothly.

#### Co-op
- **Player 2 wormhole escape ability.**
  `space_shooter/coop_game.py` previously had a `# Wormhole (P1 only for
  simplicity)` comment marking the asymmetry. P2 now has its own
  independent wormhole on the same cooldown / transit-duration
  constants:
    - new `partner_wormhole_*` state on `CoopSpaceShooterGame.__init__`;
    - `activate_partner_wormhole()` mirrors `_activate_wormhole()` but
      teleports the partner ship instead of the host;
    - `_update_partner_wormhole()` mirrors `_update_wormhole()` and
      crucially does *not* snap the host camera (P2 has its own camera);
    - new `"wormhole"` `CoopMsg.ACTION` dispatch in `space_shooter/
      __init__.py` mirroring the existing `"secondary"` action;
    - client side sends edge-triggered Q-presses (paired with the
      existing `_e_was_pressed` pattern via a new `_q_was_pressed`).
  P2 is now functionally symmetric with P1 for evasion.

#### Robustness
- **`touch_controls.py:205` import wrapped in try/except.** The
  `_to_px(fx, fy)` helper does `import display_manager` inline; on
  platforms where the module path differs (web build, embedded mobile),
  an `ImportError` would crash the touch coordinate path. Now falls back
  to `1280×720` if the import fails, mirroring the existing fallback for
  `display_manager.SCREEN_WIDTH or 1280`.

#### Verified false-positives (no code change)
- **Space-shooter projectile collision claimed to use N×M loops.**
  `space_shooter/game.py:3496` already uses
  `self.spatial_grid.query_unique(proj.x, proj.y, 60)`; the
  `SpatialGrid` is instantiated and rebuilt each frame. No N×M loop.
- **Sensor-sweep marks claimed to "overwrite instead of extend."**
  `enemy._sensor_marked = 480` resets the frame counter on every fresh
  sweep — that is the intended refresh-on-resweep behaviour, not a bug.
- **Co-op miniship targeting claimed to ignore the nearest player.**
  Miniships are intentionally owner-bound (leashed to their summoner,
  scoring by miniship-relative distance). Splitting aggro 50/50 would
  be a design change, not a bug fix.
- **Goa'uld bonus order claimed to apply before tactical formation.**
  Already correct: the leader-ability dispatch (`LEADER_SCORE_ABILITIES`
  at `game.py:779`) runs *before* the Tactical Formation sweep, and TF
  preserves additive bonuses via `bonuses_applied`.
- **`Planet.name` access claimed to need `getattr` safety.** `Planet`
  is a `@dataclass` with `name: str` declared as a required attribute;
  `to_dict()` always emits it. No `AttributeError` is reachable.

#### Code cleanup byproducts
- `_glow_cache` and `_orb_cache` are class-level dicts so they're shared
  across all PowerUp / XPOrb instances; the integer keys (pulse-derived
  ints) come from a small bounded domain so the cache cannot grow
  unbounded.
- The previously unused `self.base_fire_rate = None` field on
  `SpaceShooterGame` (sitting at game.py:113 since v10) is now actually
  populated and read.

#### Verification
1. Card battle full match (3 rounds), AI vs player. Specifically watch:
   Tactical Formation cards combined with Hammond bonus on the same
   card, Horn + ZPM stacking on siege, Weather + Survival Instinct.
   Scores must match pre-refactor expectations — `calculate_score` is
   the riskiest change.
2. Galactic Conquest `forge_alliance` mission against each starting
   relation tier (HOSTILE → NEUTRAL → TRADING → ALLIED). NEUTRAL tier
   must no longer raise `NameError`.
3. AI espionage event triggered while a counter-intel operative is on
   the targeted planet — counter-intel detection should now fire.
4. AI-as-player1 smoke test (debug toggle if available, otherwise
   temporary swap in `Game.__init__`) — no `AttributeError`.
5. Card battle with a forced sub-10 player deck — result string is
   `"player_loss"`, not `"draw"`.
6. Apophis leader power triggers without crash (sanity check on the
   added guards).
7. Space-shooter session, ≥5 minutes mid-game: observe FPS during
   high-powerup-density and high-XP-orb-density moments. Profiler
   should no longer flag PowerUp/XPOrb surface allocation as a hot path.
8. Level 5/10/15 in space shooter: XP requirements feel reasonable;
   `rapid_capacitors` at 6+ stacks still feels strong but not instant.
9. Co-op session: P2 presses Q to wormhole-escape a swarm; the
   partner ship teleports without affecting P1's camera.
10. Touch-controls test (mobile/web): force `display_manager` import
    failure; `_to_px` should fall back to 1280×720 instead of crashing.

#### Version
- Bumped to 12.5.0 in `metadata.json`, `game_config.py`, and the
  `README.md` badge.

---

### Version 12.4.0 — "Fourth-Pass Audit" (May 2026)
**Comprehensive audit + 16 of 18 backlog items shipped**

A four-area audit (core engine, rules/AI/LAN, space shooter, galactic
conquest) across ~44k LOC, followed by direct implementation of the
prioritised fix list. 16 items landed code changes; the remaining 2 were
verified as false positives — the underlying issue was already fixed in
prior versions. No save schema breakage; one schema-version migration
(`schema_version: 2`) added to `player_unlocks.json` for the new
`faction_games` counter. One real bug found and fixed during the cleanup
that wasn't in the audit (`adria_boosted` missing from round-end reset).

#### Performance
- **Deck-builder filter memoised.** `get_cards_by_type_and_strength()` is
  called from 7+ sites in `deck_builder.py` including the accordion draw
  path; previously every scroll/hover frame did an O(n) filter + O(n log n)
  sort over ~500 cards. Now keyed on `(id(card_id_list), len, tab, keyword)`
  with an LRU-bounded cache (16 entries). Eliminates accordion scroll lag.
- **Transition ring/planet/board/flash surfaces pre-allocated.** Round 2/3
  hyperspace transition was allocating 5 full-screen `SRCALPHA` surfaces
  per frame in the inner ring loop (450 allocs/transition); the round-
  winner announcement was allocating 4 more (overlay, flash, board, line)
  per frame at 60fps. Both are now scratch surfaces filled once and reused.
- **AncientDrone body sprite cached + 16-bin rotation cache.** Drones were
  building a fresh `pygame.Surface` and calling `pygame.transform.rotate()`
  every frame (~600 allocs/sec under load). Now a deterministic seeded
  body sprite is built once per radius and rotated into a 16-bucket
  angle-quantised cache. Tail wisps no longer wiggle frame-to-frame, but
  the visual change is invisible at game speeds.
- **Missile trail composite cached** (`(radius, alpha)` key, 64-entry LRU)
  in `space_shooter/projectiles.py` — replaces a per-particle two-circle
  surface allocation.
- **Galactic-map toggle button + per-row faction backgrounds + tooltip
  background** are now cached in `galactic_conquest/map_renderer.py`
  (`_panel_surf_cache`). The map panel was producing ~600 SRCALPHA allocs/
  sec when open.
- **Command-bar surface** moved from an ad-hoc `hasattr` cache to the
  shared `_panel_cache` LRU via a new `_get_cached_top_line_panel` helper
  in `frame_renderer.py`.
- **Card slide / reveal** uses `pygame.transform.scale` instead of
  `smoothscale` (`animations.py`). For these animations the scaling factors
  are near 1.0 or step in 4-px buckets, so the visual diff is invisible
  but the per-frame cycle cost is measurably lower.
- **Stargate toggle (options menu)** caches the fully-static inactive form
  by size and the static base (outer ring + ripple rings) for the active
  form. The animated chevron glow + event-horizon disc are still drawn per
  frame on a copy of the cached base. Was 3× full reconstruction per frame.

#### Logic / correctness
- **Card boost flags initialised in `Card.__init__`.** `hammond_boosted`,
  `kalel_boosted`, `kiva_boosted`, and `adria_boosted` are now declared
  `False` on every Card so the `calculate_score()` reads can drop their
  defensive `hasattr()` guards. Bonus catch: **`adria_boosted` was missing
  from the round-end reset path**, meaning an Adria-boosted card that
  survived a round via medic revive would carry +3 into the next round.
  Fixed by clearing all four flags together in `Game._end_round`.
- **Leader scoring dispatch.** The `if "Carter" in name elif "Sokar" in
  name elif …` chain in `Player.calculate_score` is now a
  `LEADER_SCORE_ABILITIES` list mapping name-substring to handler
  function. Same first-match semantics, easier to extend.
- **HathorStealAnimation / CardRevealAnimation snapshot `card.image`** at
  `__init__` (matches the existing `CardStealAnimation` pattern) so a
  mid-animation card image swap (e.g. `reload_card_images()` triggering
  during a transition) can't yank the surface out from under the
  in-flight animation.
- **LAN turn-token gap escalates to a clean disconnect** when a single
  jump exceeds 20 tokens or cumulative gap-count hits 10. Previously the
  receiver only logged + warned + resynced, regardless of severity, so
  catastrophic desyncs would let two diverged boards continue silently.
  Now closes the session so the existing `is_connected()` polling ends
  the match. Below the threshold, behaviour is unchanged.
- **AI evaluation runs in a worker thread** via `asyncio.to_thread` at the
  one synchronous-blocking call site in `main.py`. Late-game `choose_move`
  can take 50-200 ms; that no longer drops the main render loop. Pygbag
  shims the threading layer, so the web build degrades gracefully to the
  prior synchronous behaviour.

#### Stats / persistence
- **`faction_games` is now persisted directly** in `player_unlocks.json`
  alongside `faction_wins`. The old `wins * 2` (50%-win-rate guess)
  fallback in `statistics.py` is gone — for skilled players that was
  producing wildly wrong rates. Migration: `_migrate_unlocks()` adds the
  empty dict to v1 saves and stamps `schema_version: 2`. v1 saves still
  load fine and degrade to "games == max(wins, matchups_total)" until
  enough new games accrue.
- **Unlock save schema versioning.** Added `UNLOCK_SCHEMA_VERSION = 2` and
  `_migrate_unlocks()` to `deck_persistence.py`. Forward-only; older
  saves are upgraded transparently on first load.

#### Tooling / observability
- **GPU error paths route through the standard logger.** `gpu_renderer.py`
  runtime errors and `display_manager.py` effect-registration failures use
  `logger.exception(...)` instead of `print(...)`, so the existing
  `STARGWENT_DEBUG=1` environment toggle and CI log capture work uniformly.

#### Verified false-positives (no code change)
- **HELLO handshake timeout.** The audit flagged `_peer_hello_event.wait()`
  as having no timeout. In fact `lan_session.handshake()` has had a
  default 5-second deadline with bounded 250 ms polls and proper
  `TimeoutError` propagation since well before this version. Caller in
  `lan_menu._perform_handshake` already closes the socket on failure. No
  change needed.
- **`estimate_faction_power_value` caching.** The audit suggested per-round
  caching, claiming the function was hit multiple times per AI turn. Trace
  shows it has exactly one call site (`ai_opponent.py:282`, inside
  `should_use_power`) and runs once per AI decision over a O(discard pile)
  ≈ 30-element loop — sub-millisecond. Adding speculative caching would
  be code without a measurable win.

#### Code cleanup byproducts
- Module-level constants for the new caches all carry size limits and
  FIFO/LRU eviction so no cache can grow unbounded.
- The leader-dispatch refactor exposes `LEADER_SCORE_ABILITIES` as the
  authoritative list of leaders with passive scoring bonuses; adding a
  new leader ability requires one entry instead of finding the right
  spot in a 90-line `elif` chain.

#### Verification
1. `cProfile` 60 s of mid-game with deck-builder open + transition active;
   compare per-function ms vs 12.3.2. Target: deck-builder scroll <2 ms/
   frame, transitions <16 ms/frame.
2. GPU smoke test: fullscreen toggle ×2, force a shader-init failure to
   exercise the fallback path, watch the new `logger.exception` lines.
3. LAN sync test: `SIGSTOP` one client briefly to force a token jump;
   verify either the new resync warning fires or (above threshold) a
   clean disconnect occurs.
4. AI responsiveness: capture per-frame durations across 5 hard-difficulty
   late-game AI turns. Worst frame should be <20 ms with the to_thread
   wrap (was 50-200 ms in audit traces).
5. Save/load round-trip: 5 turns of Galactic Conquest, save, kill the
   process, reload — campaign state byte-identical (unchanged from 12.3.2).
6. Manual smoke of all factions, draft mode, and the space-shooter easter
   egg (no automated tests). Specifically watch the AncientDrone weapon
   under heavy fire to confirm the cached rotation looks correct.

#### Version
- Bumped to 12.4.0 in `metadata.json`, `game_config.py`, and the
  `README.md` badge.

---

### Version 12.3.2 (May 2026)
**Audit pass — Windows CI, Rak'nor leader fix, rendering regression revert**

#### CI / build
- **Windows build now succeeds.** `python -m pip install …` is used in place of bare
  `pip install …` for both the upgrade step and the dependency install on
  Windows and macOS runners, sidestepping pip's "To modify pip, please run …"
  refusal when the in-flight `pip.exe` shim is being upgraded.

#### Gameplay
- **Rak'nor's bonus play actually works now.** Previously the leader's
  "play two cards on your first turn each round" ability silently rejected
  the second card because `play_card`'s per-turn gate was never satisfied
  after the turn switched back. Replaced with a flag-guarded switch-back in
  `Game.switch_turn()` that resets `plays_this_turn` on the bonus and is
  consumed only once per round (`Player.raknor_bonus_used`). Behaves
  correctly through medic/spy/weather plays, mirror Rak'nor matchups, and
  the round reset path.

#### Rendering
- **Reverted laser-beam glow caching.** The 12.3.1 attempt keyed the surface
  cache on time-varying values (`beam_color`, `pulse`-derived alpha,
  cursor-relative `bw/bh`), so `_surface_cache` (which has no eviction
  policy outside resolution change) would grow unboundedly while a Ring
  Transport drag was active. The Ring Transport beam now allocates the glow
  surface per frame as before — a known acceptable cost during a transient
  interaction.

#### Logging cleanup
- **Removed duplicate `import logging` and unused `setup_logging` import** in
  `game.py` left over from the 12.3.1 migration.
- **Migrated the surrender log line** in `Game.surrender()` from `print()` to
  `logger.info()` to match the rest of the file. (Wider `print` → `logger`
  migration across other modules is still pending; the previous CHANGELOG
  entry overstated the scope.)

#### Version
- Bumped to 12.3.2 in `README.md` badge.

---

### Version 12.3.1 (May 2026)
**Withdrawn.** Shipped a non-functional Rak'nor ability and a memory-leaking
beam-glow cache; both are corrected in 12.3.2.

---

### Version 12.3.0 (May 2026)

### Version 12.2.4 — "Third-Pass Audit" (May 2026)
**Bug-hunt, performance pass, and code quality sweep**

A full three-agent audit covering all major subsystems. Fixes two confirmed
logic bugs, eliminates the largest per-frame surface-allocation hot spots in
the space shooter, and removes dead code. No gameplay changes; no save schema
changes; all 12.x saves load cleanly.

#### Bug fixes
- **AI mulligan hero adjustment never triggered.** `analyze_hand_composition()`
  stored `too_many_heroes` as a boolean (`hero_count > 3`). The check at
  `decide_mulligan()` compared the boolean against `> 3`, which is always
  `False` (True == 1). Now stores the raw count so the adjustment correctly
  fires when the AI holds 4+ hero cards.
- **`set_alpha()` mutated cached card surface.** `CardStealAnimation.draw()`
  and a second animation class called `set_alpha()` directly on the
  instance-cached scaled surface, so the cached copy's alpha was permanently
  updated. Any frame that reused the cache before the next rescale would blit
  at the wrong alpha. Fixed by copying the cached surface before setting alpha.

#### Performance — Space Shooter
- **Eliminated ~10 per-frame `pygame.Surface` allocations per projectile.**
  Added a module-level `_get_circle_surf(radius, color, alpha)` cache
  (alpha quantized to 32 levels) and two pre-built ember constants
  (`_EMBER_GOLD`, `_EMBER_ORANGE`). Replaced inline `pygame.Surface()`
  calls in: `Laser`, `AncientDrone`, `Missile`, `BlastProjectile`,
  `RailgunShot`, and `TunnelBolt` draw methods.
- **Cached per-instance static body surfaces.** `Laser` glow surface,
  `Missile` body+nosecone, and `RailgunShot` bolt are now built once on
  first draw and reused every subsequent frame (shapes are deterministic).

#### Code quality
- **Removed dead `CardFlipAnimation` class** (`animations.py`) — defined but
  never instantiated anywhere in the codebase.

#### Save-compat
- Save schema unchanged. All 12.x saves load cleanly.

---

### Version 12.2.3 — "Audit Follow-up" (April 2026)
**Targeted correctness fixes from second-pass audit verification**

A focused follow-up to 12.2.2 addressing confirmed bugs surfaced during
the deep audit that required source verification before fixing. No new
features; no schema changes; all 12.x saves load cleanly.

#### Bug fixes — Galactic Conquest
- **`turn_msg` crash on rival events.** `turn_msg` was first concatenated
  at the rival-courtship loop but not initialised until ~30 lines later,
  causing an unconditional `NameError` any time a rival event fired
  during a turn advance. Moved the `"Turn N"` initialisation to before
  the loop; removed the overwriting re-assignment that would also have
  silently discarded rival messages even if the `NameError` were somehow
  bypassed.
- **`construct_building` double-build guard.** Added an explicit
  `state.buildings.get(planet_id)` existence check at the top of
  `construct_building()`. The 12.2.2 fix added a defensive funds
  re-check; this adds the matching slot check so a stale UI click on an
  already-built planet cannot overwrite the existing building.
- **`get_building_level` unclamped.** Return value is now clamped to
  `[1, 3]`. A corrupted or out-of-range level stored in a save would
  previously cause a `KeyError` in the effects-table lookup.
- **Attack-animation `flash_alpha` overflow.** `flash_alpha` was
  unbounded when `progress` slightly exceeds 1.0 — passing a value above
  255 to pygame's draw call raises a `ValueError`. Added `min(255, …)`.

#### Bug fixes — LAN multiplayer
- **`LanSession.close()` potential stall.** `stop_event.set()` was
  called *inside* `_sock_lock`. The keepalive thread acquires the same
  lock for `sendall()`, so if keepalive was mid-send when `close()` was
  called, the `join(timeout=3)` could expire with threads still running.
  `stop_event` is now set *before* acquiring the lock, so the keepalive
  thread sees the signal and exits its loop without waiting for the lock.
- **`_send_ack` hardcoded message type.** `"chat_ack"` string literal
  replaced with `LanMessageType.CHAT_ACK.value` for protocol
  consistency.

#### Bug fix — Space Shooter
- **`Supergate.close()` ignores `PHASE_ACTIVATING`.** If the linked boss
  was killed while the supergate was still in its activation animation
  (before reaching `PHASE_OPEN`), `close()` was a no-op and the gate
  froze permanently — blocking enemy spawning in co-op indefinitely.
  `PHASE_ACTIVATING` is now included in the close condition.

#### Save-compat
- Save schema unchanged. All 12.x saves load cleanly.

---

### Version 12.2.2 — "Deep Audit" (April 2026)
**Whole-project audit: bug-hunt, performance, and structural pass**

A second, deeper sweep across every subsystem — card game core, GPU
pipeline, animations, LAN multiplayer & chat, Galactic Conquest, and the
Space Shooter arcade. No new features; no breaking changes; same save
schema. Three exploration passes surfaced ~70 candidate items, the
critical and high-impact ones were verified against source and fixed
below. Many additional agent-flagged items turned out to be false
positives (intentional design or already correctly handled) and were
deliberately left untouched.

#### Performance — rendering hot paths
- **`FireParticleEffect` particle draw.** Per-particle `pygame.Surface
  (SRCALPHA)` allocation removed; now routes through the existing
  `_get_circle_sprite` LRU cache with quantised alpha (16-step buckets)
  to keep the cache bounded. Frees the dominant per-frame allocator
  during Naquadah Overload / scorch effects.
- **`AICardPlayAnimation` smoothscale per frame.** Scaled-card surface
  is now cached and only regenerated when the bucketised target size
  (4-px quantum) actually changes. `pygame.transform.smoothscale` —
  ~10× slower than `transform.scale` — now runs ~10 times per
  animation instead of every frame.
- **`CardDisintegrationEffect` upfront stall.** Chunk size doubled
  (`cw // 8` → `cw // 6`, min 4 → 8) and the per-effect chunk cap
  dropped from 400 to 150. Eliminates the visible 50-100 ms hitch on
  scorch / Iris / sacrifice triggers while keeping the visual effect
  identical.
- **`ScorePopAnimation` font.render churn.** Now caches rendered text
  by `(int(current_value), color)` per instance, so the font render
  only runs once per integer step instead of every frame.
- **`LegendaryLightningEffect` per-frame surface.** Hoisted the
  SRCALPHA path-draw surface to an instance attribute and reuses it
  with `.fill((0,0,0,0))` between frames. Saves ~70 KB malloc per
  frame per active strike on legendary commanders.
- **Game-over UI panel.** Switched the rematch/menu/quit panel from a
  fresh per-frame `pygame.Surface(SRCALPHA)` + draw to the existing
  `_get_cached_panel` helper.
- **Space Shooter `ParticleTrail` + `PowerUp` particles.** Added a
  shared `_get_cached_circle` LRU in `space_shooter/effects.py` and
  routed `ParticleTrail.draw` and `PowerUp.draw` through it.
  `ParticleTrail.update` also gained an optional `dt` parameter and
  switched from a two-pass mark-then-pop pattern to a single-pass
  in-place compaction.
- **Player auto-aim.** `_get_aim_direction` rewritten to compare
  squared distances (no `math.hypot` per enemy) and to compute the
  unit vector exactly once for the chosen target. Hysteresis logic
  preserved.
- **GPU FBO pool.** Added `FBOPool.cleanup_stale(width, height)` so a
  resolution change can release framebuffers that no longer match the
  active resolution (defensive — current code only swaps on full
  context teardown, but the helper is available for future window
  resize support).
- **Conquest UI helpers.** New `render_text_cached` + cached
  `blit_alpha` in `galactic_conquest/_ui_utils.py` so screens that
  opt-in skip per-frame `font.render` and `pygame.Surface(SRCALPHA)`
  allocations on stable text/panels.

#### Bug fixes — Space Shooter correctness
- **Spatial-grid duplicate hits.** Five collision / proximity sites
  (`game.py:3103, 3492, 3693`, `ship.py:1179, 1201`) were calling
  `spatial_grid.query()` which can return the same entity once per
  cell it spans. Switched to `query_unique()`. Prevents double-tick
  effects on large entities (cap-ship asteroids, area-spanning
  enemies) where a projectile happens to sit on a cell boundary.
- **AncientDrone wobble.** `self.wobble += 0.4` now wraps modulo 2π
  so very long-lived projectiles can't accumulate a giant float
  argument to `math.sin` (cleanliness — no observable bug, but
  bounded is bounded).

#### Bug fixes — LAN co-op
- **Co-op snapshot truncation prioritised by distance.** When
  `enemies > 60` or `projectiles > 100`, the host previously truncated
  by insertion order — distant entities a client could never see kept
  the slots while the actual close-quarters threats were dropped.
  Truncation now ranks entities by squared distance to the *nearer*
  player, so the slots go to whatever each client most needs to see.

#### Bug fixes — Galactic Conquest
- **`_migrate_11_to_12` None-safety.** Migration switched from
  `setdefault` to `or {}` / `or []` so a partial pre-12 save with an
  explicit `None` field gets a usable empty container instead of
  crashing downstream code that expects a dict / list.
- **Naquadah upper bound.** `add_naquadah` now clamps to `[0,
  10_000_000]`. Long campaigns with stacked relic / income-double /
  passive bonuses can no longer push the value into UI-overflow
  territory.
- **`construct_building` defensive funds re-check.** Even though
  callers gate on `can_build()` first, the constructor now re-checks
  `state.naquadah >= cost` so a stale UI hover can't cost the player
  partial-naquadah on a click that should have been refused.

#### Polish & cleanup
- **Trail-particle counter reset on game start.** New
  `reset_trail_particle_count()` in `space_shooter/projectiles.py`,
  invoked from `Game.__init__`, so a previous run's leftover counter
  (e.g. from a crashed session that didn't tear down particles
  cleanly) doesn't starve the new run of its 800-particle budget.
- **Co-op spawn-ring fallback now logs.** `Camera.get_spawn_ring_for_coop`
  falls back to single-camera spawn after 10 failed attempts when
  players are spread far apart; that branch now prints a one-line
  warning so it surfaces in profiling instead of being silent.

#### Notes for reviewers
- `lan_session.py:93` `bind("", port)` is intentional (LAN peers must
  reach the listener on a routable address) and was *not* changed
  despite an audit flag — binding to localhost would break the
  feature.
- The draw-round scoring at `game.py:3006-3008` (both players +1 on a
  drawn round) is the correct Gwent rule and is paired with the
  mutual-2-2 game-over check at line 3021.
- Powerups `ancient_ascension` / `naquadria_cascade` / `prior_plague`
  are fully integrated in `space_shooter/game.py:1241-1268, 2719,
  2752, 4101` — verified, not skeleton stubs.

#### Save-compat
- Save schema unchanged. v12.0 / v12.1 saves load cleanly. Pre-12
  saves continue to migrate via the hardened `_migrate_11_to_12` path.

---

### Version 12.1.0 — "Audit Pass" (April 2026)
**Bug-hunt, performance, and cohesion pass on 12.0**

A focused maintenance release following a thorough audit of the v12.0
galactic-conquest rollout. No new features — just fixes, faster UI, and
a bit of cleanup so the new systems hold up under long sessions.

#### Bug fixes
- **Operative status field mismatch (espionage).** Operatives created by
  relics / leader toolkits / crisis events wrote `"status"` while the
  espionage code read `"state"`, so every state-check silently failed.
  Counter-intel detection, assassination targeting, diplomatic incident
  resolution, and the 3-operative crisis-event gate were all affected.
  The `Operative` dataclass now uses `status` as its canonical field
  and `from_dict()` falls back to the old `"state"` key when loading
  older saves, so existing runs keep working.
- **Crisis event operative count.** The 3-operatives crisis gate now
  reads the correct field.

#### Performance
- **Activity Sidebar caching.** The sidebar panel and edge tab surfaces
  are now cached and only rebuilt when the entry list, scroll position,
  or screen size actually changes — no more per-frame `Surface` +
  font renders while the log is open.
- **Spy Report one-shot render.** The modal now composites its entire
  report (overlay + faction cards) once at open time and blits that
  cached surface each frame, eliminating 4 per-frame `SysFont` calls
  plus a full-screen alpha surface allocation.
- **Galaxy map per-planet allocations.** The map draw loop was creating
  a fresh SRCALPHA surface for every attackable glow, enemy-homeworld
  ring, and narrative-arc star, every frame, for every planet. All
  three shapes are now cached by radius/colour and animated via
  `set_alpha()` — the per-frame work on a 10-planet galaxy drops from
  ~30 surface allocations to zero.
- **Hoisted per-planet scans.** `get_operative_summary()` and the full
  `NARRATIVE_ARCS` table walk are now computed once at the top of the
  draw call into `{planet_id: count}` / `{planet_name: state}` dicts,
  instead of re-running inside the per-planet loop (O(planets × ops)
  and O(planets × arcs) → O(planets + ops + arcs)).
- **Frame renderer hint + Ring-Transport glow caching.** The keyboard
  hint bar background and the golden Ring-Transport target glow now go
  through `_get_cached_panel` and `_surface_cache` respectively — both
  were previously rebuilding a fresh SRCALPHA surface every frame.
- **Particle sprite cache hardened.** `_particle_sprite_cache` is now
  a true LRU (`OrderedDict` with `move_to_end` on hit) and tightened
  to 150 entries with 30-entry eviction. Previous implementation
  pretended to be LRU but actually evicted insertion-order entries.
- **Particle mark-and-sweep.** Six hot animation update loops
  (`AnimationWaveEffect`, starburst / shock / plasma / fire / stargate /
  card-drain particle systems) used the `for p in list[:]: list.remove(p)`
  anti-pattern. Replaced with a single-pass mark-and-sweep that avoids
  O(N) removals and the subsequent slice hack.

#### Cohesion
- **Shared `_ui_utils.blit_alpha`.** Deduplicated the translucent-rect
  helper that was copy-pasted into `leader_command.py` and
  `relic_actives_panel.py`. Removed a no-op `_hex_rgb` identity helper.
- **Dropped per-frame font fallback.** The galactic-conquest map
  panels (`activity_sidebar`, `leader_command`, `relic_actives_panel`)
  now trust `MapScreen` to supply `font_btn` / `font_info` instead of
  falling back to a fresh `SysFont()` each draw. Any caller that
  bypasses `MapScreen.__init__` will now surface an `AttributeError`
  up front rather than silently leaking font objects.

#### Save-compat
- Save schema is unchanged. Old 12.0 saves load cleanly — the operative
  `state` → `status` rename is handled transparently by `Operative.from_dict`.

---

### Version 12.0.0 — "Living Galaxy" (April 2026)
**Flagship Galactic Conquest overhaul**

12.0 reshapes Galactic Conquest into a living, narrative-driven campaign.
Every leader now has a unique faction toolkit. Defeated rivals haunt your
run with multi-phase arcs. The map reacts and breathes with animated
wars, persistent icons, diplomatic borders, and a scrollable activity
log. Crises tied to faction state replace generic RNG. Most relics are
now active spells. Save state bumped to schema v12 with clean migration.

#### Pillar 1 — Leader Toolkits (unique per-leader actions)
- **40 leaders × 2-3 actions = 92 new map-layer abilities.** Every
  faction leader now has a unique *Leader Command* panel with
  player-initiated actions: O'Neill's SG-1 Strike, Apophis's System
  Lord Decree, Vala's Grand Theft, Thor's Asgard Beam, Merlin's
  Sangraal Protocol, and on through every base + unlockable leader.
- **Faction flavor motifs.** Tau'ri actions skew tactical, Goa'uld
  coercive, Jaffa honour/uprising, Lucian economic/deceptive, Asgard
  surgical/technological, Alteran escalating/metaphysical.
- **~25 reusable action templates** parameterised per leader (naq
  grants, cooldown clears, favor shifts, card upgrades, sabotage,
  two-hop attacks, NAP forces, coalition dispels, etc.) so content
  stays coherent and extensible.
- **Compact `leader_command.draw_panel` UI** renders each leader's
  actions on the left edge of the galaxy map with cost / cooldown /
  charges plus disabled-state reasons inline.
- Targeting handled by the controller: `none` fires immediately,
  planet targets use the current selection, faction targets pop a
  modal picker.

#### Pillar 2 — Rival Leader Arcs (haunting the run)
- **Rivals don't disappear.** Capture a faction homeworld and the
  defeated leader flees to a hideout planet, triggering a persistent
  multi-phase arc: EXILE → GUERRILLA → RESURGENCE → SHOWDOWN → RESOLVED.
- **Curated scripted pairs** reuse existing `LEADER_MATCHUPS` dialogue:
  O'Neill vs Apophis, Teal'c vs Ba'al, Catherine Langford vs Anubis,
  Merlin vs Adria. Any other pairing falls back to a procedural arc.
- **Showdown battle flow.** When an arc hits SHOWDOWN, the player gets
  an Engage/Defer modal; engaging runs a scaled card battle against
  the rival leader + their faction deck. Wins grant a faction-themed
  trophy relic + naquadah; losses rearm with `difficulty_tier += 1`
  and a fresh hideout so the rival comes back stronger.

#### Pillar 3 — Living Map
- **Animated AI-vs-AI wars.** Faction wars now draw a colored
  travelling-pulse attack arc between planets with an impact flash,
  instead of silent text-only resolution.
- **Persistent planet icons.** Rival arc ghost markers (☠), pulsing
  narrative arc stars, building glyphs, fort shields, cooldown labels,
  operative diamonds, and enemy homeworld glows all live on the planet
  nodes — no more clicking to read state.
- **Diplomatic borders on hyperspace lanes** color-code relations at a
  glance: allied green, trading blue, NAP amber, hostile dull red,
  coalition members pulsing red.
- **Hover tooltips** aggregate owner, fort, buildings, cooldown,
  weather, operatives, rival presence, arc state, and planet passives
  into a floating card next to the cursor.
- **Activity Log sidebar** (toggle with **L** or the right-edge tab)
  surfaces the full narrative of a run: your battles, AI counter-
  attacks, AI-vs-AI wars, diplomatic shifts, crisis outcomes, leader
  actions, rival arc beats. Categorised, colour-coded, mouse-wheel
  scrollable, capped at 400 entries.
- **Spy Report screen** (**S** key) — per-faction intel modal showing
  relation, favor, planet count, treaties, coalition membership, and
  recent losses. Enhanced intel (doctrines, buildings, personality)
  unlocks when `ai_intel_turns > 0` (from Quantum Mirror, Tok'ra-tier
  operatives, or scripted events).

#### Pillar 4 — Progression Depth & Drama
- **Scripted faction crises** preempt generic RNG when their
  predicates fire: Apophis's Declaration (Goa'uld dominance),
  Replicator Signal (Asgard network apex), Ori Crusade (Alteran
  doctrine mastery), Jaffa Rebellion Rising, Lucian Cartel Open,
  Stargate Lockdown (Supergate built), Ancient Awakening (3+ ancient
  planets held). Each fires once per run.
- **Active relic expansion (4c).** 13 relics gained active abilities
  on top of the 2 legacy ones, so nearly every owned relic is a
  spellbook entry: Ra's Wrath, Hammer of Judgment, Impenetrable Guard,
  Iris Lockdown, Power Surge, Prior's Judgment, Core Reroute, Reactor
  Overload, Extended Ring, Nanite Storm, Archive Query, Strategic
  Glance, Cloaked Run, Field Triage, Knowledge Infusion, Pyre of the
  Ori. Unified `activate_relic` dispatcher; a dedicated **Relic
  Actives** panel sits beneath the Leader Command strip on the map.
- **Victory rebalance (4d).**
  - Ascension now requires all 5 Ancient planets (was 3).
  - Economic now needs 700+ naq/turn sustained 5 turns (was 500/3).
  - Cultural now needs 5 ally minor worlds + 3 relics (was 4 + 2).
  - Alliance now requires 50+ favor with every ally, not just the
    "allied" relation state — flip-flop rushes no longer win runs.
  - Score fallback pushed from turn 30 → 35.
- **Emergency anti-coalition.** When the player is one step from any
  victory (domination / ascension / supremacy / economic / cultural),
  every surviving faction's coalition trust is forced to formation
  threshold; a flash and log entry make it explicit.

#### Pillar 5 — UX Flow
- **Hyperspace transition** now wraps map → battle and battle → map
  moves, reusing the existing `hyperspace` shader (~550 ms out, 450 ms
  back). Sells the spatial coherence of "we jumped somewhere".
- **Interruptible flash messages.** Map flash overlays no longer block
  on `pygame.time.wait()`; Space / click / Esc skips instantly with a
  visible skip hint.
- **Multi-save slots (5d).** Schema v12 seeds a `save_slot` field;
  `campaign_persistence` routes through 3 slot files
  (`galactic_conquest_save.json` remains slot 0 for backward compat).
  A new picker modal appears on NEW CAMPAIGN / RESUME when more than
  one slot is relevant.

#### Schema / Save
- **Schema v12 migration** seeds `leader_action_state`, `rival_arcs`,
  `activity_log`, and `save_slot` on any pre-12 save. Legacy saves
  load transparently; no manual intervention needed.
- **Activity log is persisted** (capped at 400 entries) so the
  sidebar history survives quit/resume.
- **Turn-counted flags** (`ai_intel_turns`, `network_surge_turns`,
  `income_double_turns`, `apophis_declaration_turns`,
  `stargate_lockdown_turns`, `fake_identity_turns`,
  `operatives_visible_turns`) tick automatically at end-of-turn.

#### Known limitations
- Leader voice barks / mid-conquest taunts deferred per "text-first"
  constraint — all new flavor lands as text/UI for 12.0. Voice-line
  expansion pencilled for 12.1.

---
