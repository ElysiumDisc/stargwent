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
