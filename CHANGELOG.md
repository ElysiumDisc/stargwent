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
