"""
STARGWENT - GALACTIC CONQUEST - Map Renderer

Renders the galaxy map with planets, hyperspace lanes, territory colors,
side info panel, and HUD. Handles click detection for planet selection.
"""

import pygame
import math
import os

from . import leader_command
from . import relic_actives_panel
from .activity_sidebar import ActivitySidebar


# Planet visual sizes
PLANET_RADIUS_HOMEWORLD = 22
PLANET_RADIUS_TERRITORY = 16
PLANET_RADIUS_NEUTRAL = 12

# Colors
COLOR_LANE = (60, 80, 120)
COLOR_LANE_ATTACKABLE = (120, 200, 255)
COLOR_SELECTED = (255, 255, 100)
COLOR_COOLDOWN = (120, 60, 60)
COLOR_HUD_BG = (15, 20, 35)
COLOR_HUD_BG_ALPHA = 200
COLOR_HUD_TEXT = (220, 220, 220)
COLOR_NAQUADAH = (100, 200, 255)
COLOR_DECK = (200, 180, 100)
COLOR_TURN = (255, 200, 100)
COLOR_PANEL_BG = (12, 16, 30)
COLOR_PANEL_BORDER = (50, 70, 110)

# --- Dim overlay cache (non-SRCALPHA fast path) ---
_dim_overlay_cache = {}


def _get_dim_overlay(w, h, alpha):
    """Return a cached dim overlay using non-SRCALPHA + set_alpha (fast path)."""
    key = (w, h, alpha)
    surf = _dim_overlay_cache.get(key)
    if surf is None:
        surf = pygame.Surface((w, h))
        surf.fill((0, 0, 0))
        surf.set_alpha(alpha)
        _dim_overlay_cache[key] = surf
    return surf


# --- Per-planet glow / marker cache -----------------------------------------
# These get drawn once per planet per frame; the underlying shapes only
# depend on radius, so cache the filled surface and animate alpha via
# set_alpha() at blit time.
_planet_glow_cache = {}


def _get_attackable_glow(radius):
    """Cached bluish glow disk for attackable planets (size = radius*6)."""
    key = ("attackable", radius)
    surf = _planet_glow_cache.get(key)
    if surf is None:
        side = radius * 6
        surf = pygame.Surface((side, side), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*COLOR_LANE_ATTACKABLE, 40),
                           (side // 2, side // 2), side // 2)
        _planet_glow_cache[key] = surf
    return surf


def _get_homeworld_ring(radius, color):
    """Cached hollow faction-coloured ring for enemy homeworlds."""
    key = ("hw_ring", radius, color)
    surf = _planet_glow_cache.get(key)
    if surf is None:
        side = radius * 8
        surf = pygame.Surface((side, side), pygame.SRCALPHA)
        # Draw at full alpha; caller animates via set_alpha().
        pygame.draw.circle(surf, (*color, 255),
                           (side // 2, side // 2), side // 2, 3)
        _planet_glow_cache[key] = surf
    return surf


def _get_star_sprite(color):
    """Cached 16x16 star sprite drawn at full alpha.  Animate via set_alpha()."""
    key = ("star", color)
    surf = _planet_glow_cache.get(key)
    if surf is None:
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        _draw_star(surf, 8, 8, 6, (*color, 255))
        _planet_glow_cache[key] = surf
    return surf


# --- Side-panel scratch surface caches --------------------------------------
# These are fully deterministic for their key — the redraw path used to allocate
# fresh SRCALPHA surfaces every frame the panel/tooltip was visible.
_panel_surf_cache = {}
_PANEL_CACHE_MAX = 64


def _get_toggle_button_surf(w, h):
    key = ("toggle", w, h)
    surf = _panel_surf_cache.get(key)
    if surf is None:
        if len(_panel_surf_cache) >= _PANEL_CACHE_MAX:
            _panel_surf_cache.pop(next(iter(_panel_surf_cache)))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((40, 60, 90, 180))
        _panel_surf_cache[key] = surf
    return surf


def _get_row_bg_surf(w, h, faction_color):
    """Cached translucent faction-tinted row background."""
    key = ("row_bg", w, h, faction_color)
    surf = _panel_surf_cache.get(key)
    if surf is None:
        if len(_panel_surf_cache) >= _PANEL_CACHE_MAX:
            _panel_surf_cache.pop(next(iter(_panel_surf_cache)))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((faction_color[0] // 10, faction_color[1] // 10,
                   faction_color[2] // 10, 60))
        _panel_surf_cache[key] = surf
    return surf


def _get_tooltip_surf(w, h):
    """Cached tooltip background (dark fill + light border).
    The text is blitted on top of a fresh copy each frame so the cache is safe."""
    key = ("tooltip", w, h)
    surf = _panel_surf_cache.get(key)
    if surf is None:
        if len(_panel_surf_cache) >= _PANEL_CACHE_MAX:
            _panel_surf_cache.pop(next(iter(_panel_surf_cache)))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((15, 20, 35, 230))
        pygame.draw.rect(surf, (120, 160, 220), surf.get_rect(), 1)
        _panel_surf_cache[key] = surf
    return surf


def _draw_star(surf, cx, cy, r, color):
    """Draw a 5-point star centered at (cx, cy).  Alpha-aware."""
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rr, cy - math.sin(ang) * rr))
    pygame.draw.polygon(surf, color, pts)


FACTION_COLORS = {
    "Tau'ri": (50, 120, 200),
    "Goa'uld": (200, 50, 50),
    "Jaffa Rebellion": (200, 180, 50),
    "Lucian Alliance": (200, 80, 180),
    "Asgard": (100, 180, 220),
    "neutral": (150, 150, 150),
    "player": (80, 220, 120),
}


class MapScreen:
    """Renders and handles interaction for the galaxy map."""

    def __init__(self, screen_width, screen_height, panel_visible=True):
        self.sw = screen_width
        self.sh = screen_height

        # Load background
        self.background = None
        bg_path = os.path.join("assets", "conquest.png")
        try:
            raw = pygame.image.load(bg_path).convert()
            self.background = pygame.transform.smoothscale(raw, (self.sw, self.sh))
        except (pygame.error, FileNotFoundError):
            self.background = pygame.Surface((self.sw, self.sh))
            self.background.fill((10, 12, 25))

        # Fonts
        self.font_name = pygame.font.SysFont("Arial", max(14, screen_height // 80))
        self.font_hud = pygame.font.SysFont("Arial", max(18, screen_height // 55), bold=True)
        self.font_btn = pygame.font.SysFont("Arial", max(13, screen_height // 70), bold=True)
        self.font_title = pygame.font.SysFont("Impact, Arial", max(28, screen_height // 35), bold=True)
        self.font_info = pygame.font.SysFont("Arial", max(13, screen_height // 90))
        self.font_panel = pygame.font.SysFont("Arial", max(15, screen_height // 72))
        self.font_panel_title = pygame.font.SysFont("Arial", max(17, screen_height // 60), bold=True)
        self.font_section = pygame.font.SysFont("Arial", max(14, screen_height // 68), bold=True)

        # Panel toggle state
        self.panel_visible = panel_visible
        self.panel_toggle_btn_rect = None

        # State
        self.hovered_planet = None
        self.selected_planet = None
        self.planet_rects = {}

        # Side panel button rects (populated during draw, read during handle_event)
        self.build_button_rects = []     # list of (rect, building_id)
        self.upgrade_button_rect = None  # rect or None

        # Side panel cache
        self._panel_cache = None  # (cache_key, surface)

        # 12.0: Activity log sidebar (right-edge slide-out, L to toggle)
        self.activity_sidebar = ActivitySidebar()

        # Calculate layout
        self._recalculate_layout()

    def _recalculate_layout(self):
        """Recalculate all layout rects based on panel visibility."""
        margin_x = int(self.sw * 0.04)

        if self.panel_visible:
            self.panel_w = int(self.sw * 0.20)
            self.panel_x = self.sw - self.panel_w
        else:
            self.panel_w = 0
            self.panel_x = self.sw

        # Bottom HUD
        self.bottom_hud_h = int(self.sh * 0.07)
        self.btn_row_y = self.sh - int(self.sh * 0.055)

        # Map area
        margin_top = int(self.sh * 0.07)
        self.map_rect = pygame.Rect(margin_x, margin_top,
                                     self.panel_x - 2 * margin_x,
                                     self.sh - margin_top - self.bottom_hud_h)

        # Buttons — 8 buttons evenly spaced along bottom row
        btn_count = 8
        btn_h = int(self.sh * 0.045)
        available_w = self.panel_x - 2 * margin_x
        btn_gap = max(4, int(self.sw * 0.006))
        btn_w = (available_w - (btn_count - 1) * btn_gap) // btn_count

        def _btn(i):
            return pygame.Rect(margin_x + i * (btn_w + btn_gap), self.btn_row_y, btn_w, btn_h)

        self.diplomacy_button_rect = _btn(0)
        self.minor_world_button_rect = _btn(1)
        self.operatives_button_rect = _btn(2)
        self.doctrines_button_rect = _btn(3)
        self.view_deck_button_rect = _btn(4)
        self.end_turn_button_rect = _btn(5)
        self.fortify_button_rect = _btn(6)
        self.attack_button_rect = _btn(7)

    def _world_to_screen(self, pos):
        """Convert normalized (0-1) position to screen pixel coordinates."""
        return (
            int(self.map_rect.x + pos[0] * self.map_rect.width),
            int(self.map_rect.y + pos[1] * self.map_rect.height),
        )

    def _get_planet_color(self, planet):
        return FACTION_COLORS.get(planet.owner, (150, 150, 150))

    # ------------------------------------------------------------------
    # 12.0 lookups: rival arc hideouts and narrative arc planet status
    # ------------------------------------------------------------------
    def _rival_arc_for_planet(self, campaign_state, planet_id):
        """Return the active rival arc dict whose hideout is this planet,
        or ``None``.  Cheap linear scan — ``rival_arcs`` stays small."""
        for arc in getattr(campaign_state, "rival_arcs", []) or []:
            if arc.get("phase") == "resolved":
                continue
            if arc.get("hideout_planet_id") == planet_id:
                return arc
        return None

    def _lane_diplo_color(self, state, a, b):
        """Return a diplomatic tint for the lane between planets *a* and *b*,
        or ``None`` if this lane has no relation colour to show.

        Only lanes that touch a player-owned planet get a relation
        colour — lanes between two AI factions would be noisy to paint
        across the whole map.  Colours::

            allied    → green
            trading   → soft blue
            nap       → amber
            coalition → pulsing red
            hostile   → dull red
        """
        if a.owner == "player" and b.owner == "player":
            return None
        # Decide which side is the "other" faction.
        if a.owner == "player":
            other = b.owner
        elif b.owner == "player":
            other = a.owner
        else:
            return None
        if other in ("player", "neutral"):
            return None

        # Coalition membership wins — pulse attention-red.
        coalition = getattr(state, "coalition", {}) or {}
        if coalition.get("active") and other in (coalition.get("members") or []):
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
            return (200 + int(40 * pulse), 40, 40)

        rel = (state.faction_relations or {}).get(other, "neutral")
        if rel == "allied":
            return (60, 180, 90)
        if rel == "trading":
            return (90, 150, 220)

        # NAP treaty?
        for t in getattr(state, "treaties", []) or []:
            if t.get("faction") == other and t.get("type") == "nap" \
                    and t.get("turns_remaining", 0) > 0:
                return (220, 180, 60)

        if rel == "hostile":
            return (150, 60, 60)
        return None

    def _narrative_arc_state(self, campaign_state, planet_name):
        """Return ``"active"`` / ``"complete"`` / ``None`` for a planet.

        - ``"active"``   — planet is on an unfinished arc's required list.
        - ``"complete"`` — planet belongs to a fully-progressed arc.
        - ``None``       — no arc involvement.
        """
        from .narrative_arcs import NARRATIVE_ARCS
        progress = getattr(campaign_state, "narrative_progress", {}) or {}
        any_active = False
        for arc_id, arc in NARRATIVE_ARCS.items():
            if planet_name not in getattr(arc, "required_planets", []):
                continue
            conquered = set(progress.get(arc_id, []))
            if len(conquered) >= len(arc.required_planets):
                return "complete"
            any_active = True
        return "active" if any_active else None

    def _get_planet_radius(self, planet):
        if planet.planet_type == "homeworld":
            return PLANET_RADIUS_HOMEWORLD
        elif planet.planet_type == "territory":
            return PLANET_RADIUS_TERRITORY
        return PLANET_RADIUS_NEUTRAL

    def draw(self, screen, galaxy_map, campaign_state, attackable_ids, message=None):
        """Render the full galaxy map view."""
        # Background
        screen.blit(self.background, (0, 0))

        # Dim overlay (cached non-SRCALPHA fast path)
        screen.blit(_get_dim_overlay(self.sw, self.sh, 100), (0, 0))

        self.planet_rects.clear()

        # Draw hyperspace lanes with pulsing effect for player-owned connections
        tick = pygame.time.get_ticks()
        lane_pulse = 0.6 + 0.4 * math.sin(tick * 0.002)
        for pid, planet in galaxy_map.planets.items():
            sx, sy = self._world_to_screen(planet.position)
            for conn_id in planet.connections:
                if conn_id > pid:
                    conn = galaxy_map.planets[conn_id]
                    cx, cy = self._world_to_screen(conn.position)
                    is_attackable = (pid in attackable_ids or conn_id in attackable_ids)
                    both_player = (planet.owner == "player" and conn.owner == "player")
                    # 12.0: lanes touching the player's territory carry a
                    # diplomatic tint so coalition / trade / NAP / hostile
                    # relations are legible at a glance.
                    diplo_color = self._lane_diplo_color(campaign_state, planet, conn)
                    if is_attackable:
                        color = COLOR_LANE_ATTACKABLE
                        width = 2
                    elif both_player:
                        pulse_val = int(80 + 60 * lane_pulse)
                        color = (pulse_val, int(pulse_val * 1.5), pulse_val)
                        width = 2
                    elif diplo_color is not None:
                        color = diplo_color
                        width = 2
                    else:
                        color = COLOR_LANE
                        width = 1
                    pygame.draw.line(screen, color, (sx, sy), (cx, cy), width)

        # Compute supply lines — unsupplied player planets (allied planets bridge gaps)
        from .stargate_network import get_disconnected_planets
        from .diplomacy import get_adjacency_bonus_factions
        allied_factions = get_adjacency_bonus_factions(campaign_state)
        unsupplied = get_disconnected_planets(galaxy_map, campaign_state.player_faction, allied_factions)

        # Pre-compute operative counts per planet once per frame; the old
        # code called get_operative_summary() inside the per-planet loop.
        from .espionage import get_operative_summary
        _ops_by_pid = {}
        for _o in get_operative_summary(campaign_state):
            _o_pid = _o[3]
            if _o_pid and _o[2] not in ("idle", "dead"):
                _ops_by_pid[_o_pid] = _ops_by_pid.get(_o_pid, 0) + 1

        # Pre-compute narrative-arc state per planet once per frame.
        # Old code ran the full NARRATIVE_ARCS scan inside the draw loop.
        from .narrative_arcs import NARRATIVE_ARCS
        _progress = getattr(campaign_state, "narrative_progress", {}) or {}
        _arc_state_by_name: dict[str, str] = {}
        for _arc_id, _arc in NARRATIVE_ARCS.items():
            _req = getattr(_arc, "required_planets", []) or []
            if not _req:
                continue
            _conquered = len(set(_progress.get(_arc_id, [])))
            _state = "complete" if _conquered >= len(_req) else "active"
            for _pname in _req:
                prev = _arc_state_by_name.get(_pname)
                # "complete" wins over "active" if any arc containing this
                # planet is finished (mirrors original method's early return).
                if prev != "complete":
                    _arc_state_by_name[_pname] = _state

        # Draw planets
        for pid, planet in galaxy_map.planets.items():
            sx, sy = self._world_to_screen(planet.position)
            radius = self._get_planet_radius(planet)
            color = self._get_planet_color(planet)

            is_cooldown = pid in campaign_state.cooldowns
            if is_cooldown:
                color = COLOR_COOLDOWN

            is_attackable = pid in attackable_ids and not is_cooldown
            if is_attackable:
                glow_surf = _get_attackable_glow(radius)
                screen.blit(glow_surf, (sx - radius * 3, sy - radius * 3))

            pygame.draw.circle(screen, color, (sx, sy), radius)

            # Minor world type ring for player-owned neutral planets
            if planet.planet_type == "neutral" and planet.owner == "player":
                from .minor_worlds import MINOR_WORLD_TYPES, MINOR_WORLD_TYPE_INFO
                _mw_type = MINOR_WORLD_TYPES.get(planet.name)
                if _mw_type:
                    _mw_color = MINOR_WORLD_TYPE_INFO.get(_mw_type, {}).get("color", (150, 150, 150))
                    pygame.draw.circle(screen, _mw_color, (sx, sy), radius + 3, 2)

            if planet.planet_type == "homeworld":
                pygame.draw.circle(screen, (255, 255, 255), (sx, sy), radius + 3, 2)

            if pid == self.selected_planet:
                pygame.draw.circle(screen, COLOR_SELECTED, (sx, sy), radius + 5, 3)

            if pid == self.hovered_planet and pid != self.selected_planet:
                pygame.draw.circle(screen, (200, 200, 200), (sx, sy), radius + 4, 2)

            label = self.font_name.render(planet.name, True, (220, 220, 220))
            screen.blit(label, (sx - label.get_width() // 2, sy + radius + 4))

            if is_cooldown:
                cd_text = self.font_info.render(
                    f"{campaign_state.cooldowns[pid]}T", True, (255, 100, 100))
                screen.blit(cd_text, (sx - cd_text.get_width() // 2, sy - radius - 16))

            # Unsupplied indicator (dashed red outline)
            if pid in unsupplied and planet.owner == "player":
                for angle_deg in range(0, 360, 30):
                    rad = math.radians(angle_deg)
                    end_rad = math.radians(angle_deg + 15)
                    x1 = sx + int(math.cos(rad) * (radius + 6))
                    y1 = sy + int(math.sin(rad) * (radius + 6))
                    x2 = sx + int(math.cos(end_rad) * (radius + 6))
                    y2 = sy + int(math.sin(end_rad) * (radius + 6))
                    pygame.draw.line(screen, (255, 100, 60), (x1, y1), (x2, y2), 2)

            # Building indicator
            from .buildings import get_planet_building_display
            building_info = get_planet_building_display(campaign_state, pid)
            if building_info and planet.owner == "player":
                bname, bicon, bdesc = building_info
                bld_text = self.font_info.render(bicon, True, (200, 180, 100))
                screen.blit(bld_text, (sx + radius + 3, sy - 8))

            # Fortification shields
            fort_level = getattr(campaign_state, 'fortification_levels', {}).get(pid, 0)
            if fort_level > 0 and planet.owner == "player":
                shield_text = self.font_info.render(
                    "\u2666" * fort_level, True, (100, 200, 255))
                screen.blit(shield_text, (sx - shield_text.get_width() // 2, sy - radius - 14))

            # Operative indicator (small diamond) — count pre-aggregated above
            _op_here = _ops_by_pid.get(pid, 0)
            if _op_here > 0:
                op_text = self.font_info.render(
                    "\u25C6" * _op_here, True, (200, 150, 255))
                screen.blit(op_text, (sx - op_text.get_width() // 2, sy + radius + 16))

            # Enemy homeworld glow ring (cached shape, animated alpha)
            if planet.planet_type == "homeworld" and planet.owner not in ("player", "neutral"):
                hw_color = FACTION_COLORS.get(planet.owner, (200, 50, 50))
                glow_surf = _get_homeworld_ring(radius, hw_color)
                glow_alpha = int(120 + 60 * math.sin(pygame.time.get_ticks() * 0.003))
                glow_surf.set_alpha(min(255, glow_alpha))
                screen.blit(glow_surf, (sx - radius * 4, sy - radius * 4))

            # 12.0: Rival arc hideout marker (blood-red ghost glyph)
            rival_here = self._rival_arc_for_planet(campaign_state, pid)
            if rival_here is not None:
                ghost_text = self.font_info.render("\u2620", True, (220, 80, 80))
                screen.blit(ghost_text,
                            (sx + radius - 2, sy - radius - ghost_text.get_height()))

            # 12.0: Narrative arc marker (golden star) on planets tied to
            # an arc that has not yet completed.  Shape cached, alpha animated.
            arc_state = _arc_state_by_name.get(planet.name)
            if arc_state == "active":
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.004)
                star_alpha = int(120 + 100 * pulse)
                star_surf = _get_star_sprite((255, 210, 80))
                star_surf.set_alpha(star_alpha)
                screen.blit(star_surf, (sx - radius - 10, sy - radius - 10))
            elif arc_state == "complete":
                star_surf = _get_star_sprite((255, 220, 150))
                star_surf.set_alpha(220)
                screen.blit(star_surf, (sx - radius - 10, sy - radius - 10))

            self.planet_rects[pid] = pygame.Rect(sx - radius, sy - radius,
                                                  radius * 2, radius * 2)

        # ===== TOP HUD (simplified) =====
        hud_h = int(self.sh * 0.06)
        hud_bg = _get_dim_overlay(self.panel_x, hud_h, COLOR_HUD_BG_ALPHA)
        screen.blit(hud_bg, (0, 0))

        title = self.font_title.render("GALACTIC CONQUEST", True, (200, 220, 255))
        screen.blit(title, (int(self.sw * 0.03), int(self.sh * 0.012)))

        # Key stats — Turn, Naquadah, Wisdom (left side), Network + Planets (right)
        from .stargate_network import get_network_bonuses
        from .diplomacy import get_adjacency_bonus_factions as _get_allied
        network = get_network_bonuses(galaxy_map, campaign_state.player_faction,
                                       _get_allied(campaign_state))
        tier_colors = {1: (150, 150, 150), 2: (100, 200, 255), 3: (255, 200, 80),
                       4: (255, 140, 60), 5: (200, 100, 255)}
        tier_color = tier_colors.get(network["tier"], (200, 200, 200))

        x_off = int(self.sw * 0.30)
        y_center = int(self.sh * 0.02)
        left_stats = [
            (f"Turn {campaign_state.turn_number}", COLOR_TURN),
            (f"Naquadah: {campaign_state.naquadah}", COLOR_NAQUADAH),
            (f"Wisdom: {campaign_state.wisdom}", (200, 150, 255)),
        ]
        for text, color in left_stats:
            surf = self.font_hud.render(text, True, color)
            screen.blit(surf, (x_off, y_center))
            x_off += surf.get_width() + int(self.sw * 0.025)

        # Right-aligned: network tier + planets
        right_stats = [
            (f"T{network['tier']} {network['name']}", tier_color),
            (f"{galaxy_map.get_player_planet_count()}/{len(galaxy_map.planets)}", (200, 200, 200)),
        ]
        rx = self.panel_x - int(self.sw * 0.02)
        for text, color in reversed(right_stats):
            surf = self.font_hud.render(text, True, color)
            rx -= surf.get_width()
            screen.blit(surf, (rx, y_center))
            rx -= int(self.sw * 0.02)

        # ===== PANEL TOGGLE BUTTON =====
        toggle_text = "\u25C0" if self.panel_visible else "\u25B6"
        toggle_w, toggle_h = 32, 24
        toggle_x = self.panel_x - toggle_w - 8 if self.panel_visible else self.sw - toggle_w - 8
        toggle_y = int(self.sh * 0.015)
        self.panel_toggle_btn_rect = pygame.Rect(toggle_x, toggle_y, toggle_w, toggle_h)
        screen.blit(_get_toggle_button_surf(toggle_w, toggle_h), (toggle_x, toggle_y))
        pygame.draw.rect(screen, (80, 110, 150), self.panel_toggle_btn_rect, 1)
        toggle_label = self.font_info.render(toggle_text, True, (180, 200, 220))
        screen.blit(toggle_label, (toggle_x + toggle_w // 2 - toggle_label.get_width() // 2,
                                   toggle_y + toggle_h // 2 - toggle_label.get_height() // 2))

        # ===== SIDE PANEL =====
        if self.panel_visible:
            self._draw_side_panel(screen, galaxy_map, campaign_state, attackable_ids, network)

        # ===== BOTTOM HUD =====
        hud_w = self.panel_x if self.panel_visible else self.sw
        bottom_bg = _get_dim_overlay(hud_w, self.bottom_hud_h, COLOR_HUD_BG_ALPHA)
        screen.blit(bottom_bg, (0, self.sh - self.bottom_hud_h))

        # ===== BUTTONS (8 buttons) =====
        can_attack = (self.selected_planet in attackable_ids
                      and self.selected_planet not in campaign_state.cooldowns)

        fort_levels = getattr(campaign_state, 'fortification_levels', {})
        fort_cost = network["fortify_cost"]
        can_fortify = False
        if self.selected_planet and self.selected_planet in galaxy_map.planets:
            sp = galaxy_map.planets[self.selected_planet]
            cur_fort = fort_levels.get(self.selected_planet, 0)
            can_fortify = (sp.owner == "player" and cur_fort < 3
                           and campaign_state.naquadah >= fort_cost)

        self._draw_button(screen, self.diplomacy_button_rect, "DIPLOMACY",
                          (120, 80, 160), enabled=True)
        can_minor_world = False
        if self.selected_planet and self.selected_planet in galaxy_map.planets:
            _mw_planet = galaxy_map.planets[self.selected_planet]
            can_minor_world = (_mw_planet.planet_type == "neutral"
                               and _mw_planet.owner == "player")
        self._draw_button(screen, self.minor_world_button_rect, "MINOR WORLD",
                          (100, 80, 160) if can_minor_world else (60, 60, 60),
                          enabled=can_minor_world)
        has_operatives = len(getattr(campaign_state, 'operatives', [])) > 0
        self._draw_button(screen, self.operatives_button_rect, "OPERATIVES",
                          (120, 80, 180) if has_operatives else (60, 60, 60),
                          enabled=has_operatives)
        self._draw_button(screen, self.doctrines_button_rect, "DOCTRINES",
                          (100, 80, 140), enabled=True)
        self._draw_button(screen, self.view_deck_button_rect, "VIEW DECK",
                          (120, 100, 60), enabled=True)
        self._draw_button(screen, self.end_turn_button_rect, "END TURN",
                          (80, 120, 180), enabled=True)
        fort_label = f"FORTIFY ({fort_cost})" if can_fortify else "FORTIFY"
        self._draw_button(screen, self.fortify_button_rect, fort_label,
                          (60, 120, 180) if can_fortify else (60, 60, 60),
                          enabled=can_fortify)
        self._draw_button(screen, self.attack_button_rect, "ATTACK",
                          (60, 180, 80) if can_attack else (60, 60, 60),
                          enabled=can_attack)

        # ESC hint (bottom-left corner)
        hint = self.font_info.render("ESC = Save & Quit  |  D = Deck  |  I = Info  |  TAB = Panel",
                                     True, (80, 90, 120))
        screen.blit(hint, (int(self.sw * 0.03),
                           self.sh - self.bottom_hud_h + int(self.sh * 0.005)))

        # 12.0: Leader Command panel (top-left of map area)
        leader_command.draw_panel(screen, campaign_state, galaxy_map, self)
        # 12.0: Relic Actives panel (directly below leader command)
        relic_actives_panel.draw_panel(screen, campaign_state, galaxy_map, self)

        # 12.0: hover tooltip for whichever planet the cursor is on
        if self.hovered_planet and self.hovered_planet in galaxy_map.planets:
            self._draw_hover_tooltip(screen, galaxy_map, campaign_state,
                                     self.hovered_planet)

        # 12.0: activity log sidebar (above everything — it's modal-ish)
        self.activity_sidebar.draw(screen, self, campaign_state)

        # Status message (above bottom HUD)
        if message:
            msg_center = self.panel_x // 2 if self.panel_visible else self.sw // 2
            msg_surf = self.font_hud.render(message, True, (255, 220, 100))
            screen.blit(msg_surf, (msg_center - msg_surf.get_width() // 2,
                                    self.sh - self.bottom_hud_h - int(self.sh * 0.03)))

    def _draw_side_panel(self, screen, galaxy_map, campaign_state, attackable_ids, network):
        """Draw the right-side info panel. Stores button rects for event handler."""
        panel_top = int(self.sh * 0.06)
        panel_h = self.sh - panel_top - self.bottom_hud_h
        pad = int(self.panel_w * 0.08)
        inner_w = self.panel_w - 2 * pad

        # Panel background
        panel_bg = _get_dim_overlay(self.panel_w, panel_h, 220)
        screen.blit(panel_bg, (self.panel_x, panel_top))
        pygame.draw.line(screen, COLOR_PANEL_BORDER,
                         (self.panel_x, panel_top), (self.panel_x, panel_top + panel_h), 1)

        # Reset button rects
        self.build_button_rects = []
        self.upgrade_button_rect = None

        x = self.panel_x + pad
        y = panel_top + pad
        line_h = self.font_panel.get_height() + 4
        small_h = self.font_info.get_height() + 3

        if self.selected_planet and self.selected_planet in galaxy_map.planets:
            self._draw_panel_planet(screen, galaxy_map, campaign_state, attackable_ids,
                                    x, y, inner_w, line_h, small_h, panel_top + panel_h)
        else:
            self._draw_panel_overview(screen, galaxy_map, campaign_state, network,
                                       x, y, inner_w, line_h, small_h, panel_top + panel_h)

    def _draw_section_header(self, screen, text, x, y, inner_w, color=(200, 220, 255)):
        """Draw a section header with separator line. Returns new y position."""
        y += 4
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (x, y), (x + inner_w, y), 1)
        y += 6
        header = self.font_section.render(text, True, color)
        screen.blit(header, (x, y))
        y += header.get_height() + 4
        return y

    def _draw_panel_planet(self, screen, galaxy_map, campaign_state, attackable_ids,
                           x, y, inner_w, line_h, small_h, panel_bottom):
        """Draw planet details in side panel."""
        sp = galaxy_map.planets[self.selected_planet]
        owner_color = self._get_planet_color(sp)
        is_enemy = sp.owner not in ("player", "neutral")
        is_player = sp.owner == "player"

        # ===== PLANET IDENTITY =====
        # Planet name
        type_icon = "\u2605" if sp.planet_type == "homeworld" else (
            "\u25C6" if sp.planet_type == "territory" else "\u25CB")
        name_surf = self.font_panel_title.render(f"{type_icon} {sp.name}", True, owner_color)
        screen.blit(name_surf, (x, y))
        y += line_h + 2

        # Owner with colored dot
        pygame.draw.circle(screen, owner_color, (x + 6, y + self.font_panel.get_height() // 2), 4)
        owner_label = sp.owner.title() if sp.owner != "player" else "You"
        owner_surf = self.font_panel.render(f"  {owner_label}", True, owner_color)
        screen.blit(owner_surf, (x + 12, y))
        y += line_h

        # Type
        type_surf = self.font_info.render(f"{sp.planet_type.title()}", True, (160, 170, 190))
        screen.blit(type_surf, (x, y))
        y += small_h

        # Weather
        if sp.weather_preset:
            wname = sp.weather_preset.get('type', 'none').replace('_', ' ').title()
            w_color = (255, 200, 100)
            w_surf = self.font_info.render(f"\u26A0 Weather: {wname}", True, w_color)
            screen.blit(w_surf, (x, y))
            y += small_h

        # Cooldown
        if self.selected_planet in campaign_state.cooldowns:
            cd = campaign_state.cooldowns[self.selected_planet]
            cd_surf = self.font_info.render(f"\u23F1 Cooldown: {cd} turns", True, (255, 100, 100))
            screen.blit(cd_surf, (x, y))
            y += small_h

        # ===== ENEMY INTELLIGENCE (for enemy planets) =====
        if is_enemy and y < panel_bottom - 80:
            y = self._draw_section_header(screen, "ENEMY INTELLIGENCE", x, y, inner_w,
                                          color=(255, 200, 140))

            if sp.defender_leader:
                leader_name = sp.defender_leader.get('name', '?')
                dl_surf = self.font_panel.render(f"Cmdr: {leader_name}", True, (220, 180, 140))
                screen.blit(dl_surf, (x, y))
                y += line_h

                # Leader ability
                ability = sp.defender_leader.get('ability', '')
                if ability and y < panel_bottom - 60:
                    # Word-wrap ability text
                    y = self._draw_wrapped_panel_text(screen, ability, self.font_info,
                                                      (200, 180, 140), x, y, inner_w)

                # Leader ability description (detailed)
                ability_desc = sp.defender_leader.get('ability_desc', '')
                if ability_desc and ability_desc != ability and y < panel_bottom - 40:
                    y = self._draw_wrapped_panel_text(screen, ability_desc, self.font_info,
                                                      (160, 150, 130), x, y, inner_w)

            # Faction info
            faction_color = FACTION_COLORS.get(sp.faction, (150, 150, 150))
            f_surf = self.font_info.render(f"Faction: {sp.faction}", True, faction_color)
            screen.blit(f_surf, (x, y))
            y += small_h

            if sp.planet_type == "homeworld":
                elite_surf = self.font_info.render("\u26A0 ELITE DEFENDERS", True, (255, 100, 80))
                screen.blit(elite_surf, (x, y))
                y += small_h

        # ===== YOUR FORCES (shown for attackable enemy planets) =====
        if is_enemy and y < panel_bottom - 60:
            y = self._draw_section_header(screen, "YOUR FORCES", x, y, inner_w,
                                          color=(140, 255, 180))

            if campaign_state.player_leader and isinstance(campaign_state.player_leader, dict):
                pl_name = campaign_state.player_leader.get('name', '?')
                pl_surf = self.font_panel.render(f"Cmdr: {pl_name}", True, (140, 220, 160))
                screen.blit(pl_surf, (x, y))
                y += line_h

                pl_ability = campaign_state.player_leader.get('ability', '')
                if pl_ability and y < panel_bottom - 40:
                    y = self._draw_wrapped_panel_text(screen, pl_ability, self.font_info,
                                                      (130, 200, 150), x, y, inner_w)
            else:
                pl_surf = self.font_info.render("Cmdr: Chosen per battle", True, (130, 200, 150))
                screen.blit(pl_surf, (x, y))
                y += small_h

            deck_surf = self.font_info.render(
                f"Deck: {len(campaign_state.current_deck)} cards", True, COLOR_DECK)
            screen.blit(deck_surf, (x, y))
            y += small_h

            upgraded = sum(1 for v in campaign_state.upgraded_cards.values() if v > 0)
            if upgraded:
                upg_surf = self.font_info.render(f"Upgrades: {upgraded}", True, (100, 255, 150))
                screen.blit(upg_surf, (x, y))
                y += small_h

        # ===== INFRASTRUCTURE (player-owned planets) =====
        if is_player and y < panel_bottom - 40:
            y = self._draw_section_header(screen, "INFRASTRUCTURE", x, y, inner_w,
                                          color=(200, 200, 255))

            # Building
            from .buildings import get_planet_building_display, get_upgrade_cost, can_upgrade, BUILDINGS
            binfo = get_planet_building_display(campaign_state, self.selected_planet)
            if binfo:
                bname, bicon, bdesc = binfo
                b_surf = self.font_panel.render(f"{bicon} {bname}", True, (200, 180, 100))
                screen.blit(b_surf, (x, y))
                y += line_h
                desc_surf = self.font_info.render(bdesc, True, (160, 160, 170))
                screen.blit(desc_surf, (x, y))
                y += small_h

                # Upgrade button
                upg_cost = get_upgrade_cost(campaign_state, self.selected_planet)
                if upg_cost is not None:
                    can_upg = can_upgrade(campaign_state, self.selected_planet, type('G', (), {'planets': galaxy_map.planets})())
                    btn_h = int(self.sh * 0.035)
                    btn_w = min(inner_w, int(self.panel_w * 0.85))
                    btn_rect = pygame.Rect(x, y + 2, btn_w, btn_h)
                    self.upgrade_button_rect = btn_rect
                    self._draw_button(screen, btn_rect, f"UPGRADE (-{upg_cost} naq)",
                                      (80, 120, 60) if can_upg else (50, 50, 50),
                                      enabled=can_upg)
                    y += btn_h + 6
            else:
                # No building — show build options
                b_label = self.font_panel.render("No Building", True, (120, 120, 130))
                screen.blit(b_label, (x, y))
                y += line_h
                btn_h = int(self.sh * 0.030)
                btn_w = min(inner_w, int(self.panel_w * 0.85))
                from .buildings import _get_building_cost, can_build
                for bid, building in BUILDINGS.items():
                    if y + btn_h > panel_bottom - 10:
                        break
                    cost = _get_building_cost(building, campaign_state)
                    can_b = can_build(campaign_state, self.selected_planet, bid, type('G', (), {'planets': galaxy_map.planets})())
                    btn_rect = pygame.Rect(x, y, btn_w, btn_h)
                    self.build_button_rects.append((btn_rect, bid))
                    label = f"{building.icon_char} {building.name} (-{cost})"
                    self._draw_button(screen, btn_rect, label,
                                      (60, 80, 100) if can_b else (40, 40, 40),
                                      enabled=can_b)
                    y += btn_h + 3

            # Fortification — visual bars
            fort_level = campaign_state.fortification_levels.get(self.selected_planet, 0)
            y += 4
            fort_label = self.font_info.render("Fort:", True,
                                               (100, 200, 255) if fort_level > 0 else (120, 120, 130))
            screen.blit(fort_label, (x, y))
            bar_x = x + fort_label.get_width() + 6
            bar_w_each = int(inner_w * 0.12)
            bar_h = 10
            for i in range(3):
                bx = bar_x + i * (bar_w_each + 3)
                if i < fort_level:
                    pygame.draw.rect(screen, (80, 180, 255), (bx, y + 2, bar_w_each, bar_h))
                else:
                    pygame.draw.rect(screen, (40, 50, 60), (bx, y + 2, bar_w_each, bar_h))
                pygame.draw.rect(screen, (70, 90, 120), (bx, y + 2, bar_w_each, bar_h), 1)
            y += line_h

        # Planet passive
        from .planet_passives import get_planet_passive
        passive = get_planet_passive(self.selected_planet, galaxy_map)
        if passive and is_player and y < panel_bottom - 20:
            p_surf = self.font_info.render(f"Passive: {passive['desc']}", True, (150, 200, 150))
            screen.blit(p_surf, (x, y))
            y += small_h

        # Operatives here
        from .espionage import get_operative_summary
        ops = get_operative_summary(campaign_state)
        ops_here = [o for o in ops if o[3] == self.selected_planet and o[2] not in ("idle", "dead")]
        if ops_here and y < panel_bottom - 20:
            op_surf = self.font_info.render(f"Operatives: {len(ops_here)}", True, (200, 150, 255))
            screen.blit(op_surf, (x, y))
            y += small_h

        # Minor world info
        if sp.planet_type == "neutral" and y < panel_bottom - 40:
            from .minor_worlds import ensure_minor_world, MINOR_WORLD_TYPE_INFO, get_tier_label
            _mw = ensure_minor_world(campaign_state, self.selected_planet, galaxy_map)
            if _mw:
                _mw_info = MINOR_WORLD_TYPE_INFO.get(_mw.world_type, {})
                mw_icon = _mw_info.get('icon', '')
                mw_color = _mw_info.get('color', (150, 150, 150))
                y = self._draw_section_header(screen, f"{mw_icon} {_mw.world_type.title()} World",
                                               x, y, inner_w, color=mw_color)

                # Influence bar
                tier_label = get_tier_label(_mw.influence)
                inf_surf = self.font_info.render(
                    f"Influence: {_mw.influence} [{tier_label}]", True, COLOR_HUD_TEXT)
                screen.blit(inf_surf, (x, y))
                y += small_h
                bar_w = min(inner_w, int(self.panel_w * 0.80))
                bar_h = 8
                pygame.draw.rect(screen, (40, 40, 50), (x, y, bar_w, bar_h))
                fill_w = int(bar_w * min(1.0, _mw.influence / 100.0))
                bar_color = (80, 220, 120) if _mw.influence >= 60 else (
                    (200, 200, 80) if _mw.influence >= 30 else (120, 120, 130))
                if fill_w > 0:
                    pygame.draw.rect(screen, bar_color, (x, y, fill_w, bar_h))
                y += bar_h + 4

                if _mw.active_quest and y < panel_bottom - 20:
                    q_surf = self.font_info.render(
                        f"Quest: {_mw.active_quest.get('description', '?')}", True, (200, 200, 150))
                    screen.blit(q_surf, (x, y))
                    y += small_h

    def _draw_wrapped_panel_text(self, screen, text, font, color, x, y, max_width):
        """Draw word-wrapped text in the side panel. Returns new y position."""
        words = text.split()
        line = ""
        line_h = font.get_height() + 2
        for word in words:
            test = line + " " + word if line else word
            if font.size(test)[0] > max_width and line:
                surf = font.render(line, True, color)
                screen.blit(surf, (x, y))
                y += line_h
                line = word
            else:
                line = test
        if line:
            surf = font.render(line, True, color)
            screen.blit(surf, (x, y))
            y += line_h
        return y

    def _draw_panel_overview(self, screen, galaxy_map, campaign_state, network,
                             x, y, inner_w, line_h, small_h, panel_bottom):
        """Draw overview info in side panel (no planet selected)."""
        # Victory progress
        header = self.font_panel_title.render("Victory Progress", True, (200, 220, 255))
        screen.blit(header, (x, y))
        y += line_h + 4

        from .victory_conditions import get_victory_progress, VICTORY_INFO
        v_progress = get_victory_progress(campaign_state, galaxy_map)
        bar_w = min(inner_w, int(self.panel_w * 0.80))
        bar_h = 10
        if v_progress:
            for v_id, v_name, v_desc, v_pct in v_progress:
                v_info = VICTORY_INFO.get(v_id, {})
                v_color = v_info.get("color", (150, 150, 150))
                pct_int = int(v_pct * 100)
                name_surf = self.font_info.render(f"{v_name} ({pct_int}%)", True, v_color)
                screen.blit(name_surf, (x, y))
                y += small_h
                # Progress bar
                pygame.draw.rect(screen, (30, 30, 40), (x, y, bar_w, bar_h))
                fill_w = int(bar_w * min(1.0, v_pct))
                if fill_w > 0:
                    pygame.draw.rect(screen, v_color, (x, y, fill_w, bar_h))
                y += bar_h + 4
                if y > panel_bottom - 100:
                    break

        # Separator
        y += 4
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (x, y), (x + inner_w, y), 1)
        y += 8

        # Faction overview
        header2 = self.font_panel_title.render("Factions", True, (200, 220, 255))
        screen.blit(header2, (x, y))
        y += line_h + 2

        from .galaxy_map import ALL_FACTIONS
        from .diplomacy import get_relation, RELATION_DISPLAY
        row_h = small_h + 4
        for faction in ALL_FACTIONS:
            if faction == campaign_state.player_faction:
                continue
            if y > panel_bottom - 40:
                break
            pcount = galaxy_map.get_faction_planet_count(faction)
            if pcount == 0:
                continue
            rel = get_relation(campaign_state, faction)
            rel_info = RELATION_DISPLAY.get(rel, {})
            rel_color = rel_info.get("color", (150, 150, 150))
            faction_color = FACTION_COLORS.get(faction, (150, 150, 150))

            # Subtle background box for each faction row (cached by faction color)
            screen.blit(_get_row_bg_surf(inner_w, row_h, faction_color), (x, y))

            # Faction name + planet count
            f_surf = self.font_info.render(f"{faction} ({pcount})", True, faction_color)
            screen.blit(f_surf, (x + 4, y + 2))
            # Relation tag
            rel_tag = self.font_info.render(rel_info.get("name", rel), True, rel_color)
            screen.blit(rel_tag, (x + inner_w - rel_tag.get_width() - 4, y + 2))
            y += row_h

        # Separator
        y += 6
        pygame.draw.line(screen, COLOR_PANEL_BORDER, (x, y), (x + inner_w, y), 1)
        y += 8

        # Quick stats
        if y < panel_bottom - 80:
            header3 = self.font_panel_title.render("Stats", True, (200, 220, 255))
            screen.blit(header3, (x, y))
            y += line_h + 2

            deck_surf = self.font_info.render(
                f"Deck: {len(campaign_state.current_deck)} cards", True, COLOR_DECK)
            screen.blit(deck_surf, (x, y))
            y += small_h

            upgraded_count = sum(1 for v in campaign_state.upgraded_cards.values() if v > 0)
            if upgraded_count:
                upg_surf = self.font_info.render(
                    f"Upgrades: {upgraded_count}", True, (100, 255, 150))
                screen.blit(upg_surf, (x, y))
                y += small_h

            relic_count = len(campaign_state.relics)
            if relic_count:
                rel_surf = self.font_info.render(
                    f"Relics: {relic_count}", True, (255, 176, 0))
                screen.blit(rel_surf, (x, y))
                y += small_h

            fort_count = sum(1 for v in campaign_state.fortification_levels.values() if v > 0)
            if fort_count:
                fort_surf = self.font_info.render(
                    f"Fortified: {fort_count} planets", True, (100, 200, 255))
                screen.blit(fort_surf, (x, y))
                y += small_h

            op_count = len(campaign_state.operatives)
            if op_count:
                op_surf = self.font_info.render(
                    f"Operatives: {op_count}", True, (200, 150, 255))
                screen.blit(op_surf, (x, y))
                y += small_h

    def _draw_button(self, screen, rect, text, color, enabled=True):
        """Draw a button with text, auto-fitting to button width."""
        alpha = 255 if enabled else 120
        btn_surf = pygame.Surface((rect.width, rect.height))
        btn_surf.fill(color)
        if not enabled:
            btn_surf.set_alpha(alpha)
        screen.blit(btn_surf, rect.topleft)
        border_color = (200, 200, 200) if enabled else (100, 100, 100)
        pygame.draw.rect(screen, border_color, rect, 2)
        text_color = (255, 255, 255) if enabled else (120, 120, 120)
        label = self.font_btn.render(text, True, text_color)
        if label.get_width() > rect.width - 6:
            label = self.font_info.render(text, True, text_color)
        screen.blit(label, (rect.centerx - label.get_width() // 2,
                            rect.centery - label.get_height() // 2))

    def _draw_hover_tooltip(self, screen, galaxy_map, state, pid):
        """Compose and render a floating info card for the hovered planet.

        Aggregates data that used to require clicking the planet and
        reading the side panel.  Positioned next to the planet but
        clamped to the map area so it never overflows the HUD.
        """
        planet = galaxy_map.planets[pid]
        lines: list[tuple[str, tuple]] = []

        # Header
        owner_txt = planet.owner if planet.owner else "neutral"
        lines.append((f"{planet.name}", (255, 220, 150)))
        lines.append((f"Owner: {owner_txt}", (200, 200, 230)))
        if planet.planet_type == "homeworld":
            lines.append(("Homeworld", (255, 180, 120)))

        # Fort + cooldown
        fort = (state.fortification_levels or {}).get(pid, 0)
        if fort > 0:
            lines.append((f"Fortification: {fort}/3", (120, 200, 255)))
        cd = (state.cooldowns or {}).get(pid, 0)
        if cd > 0:
            lines.append((f"Cooldown: {cd}t", (255, 140, 140)))

        # Building
        bld = (state.buildings or {}).get(pid)
        if bld:
            lvl = (state.building_levels or {}).get(pid, 1)
            lines.append((f"Building: {bld} L{lvl}", (220, 200, 120)))

        # Weather
        if getattr(planet, "weather_preset", None):
            lines.append((f"Weather: {planet.weather_preset}", (180, 220, 220)))

        # Operatives here
        try:
            from .espionage import get_operative_summary
            ops_here = [o for o in get_operative_summary(state)
                        if o[3] == pid and o[2] not in ("idle", "dead")]
            if ops_here:
                lines.append((f"Operatives: {len(ops_here)}", (200, 150, 255)))
        except Exception:
            pass

        # Rival arc hideout
        rival = self._rival_arc_for_planet(state, pid)
        if rival:
            lines.append(
                (f"Rival: {rival.get('rival_name', '?')} ({rival.get('phase', '?')})",
                 (230, 110, 110)))

        # Narrative arc progress
        arc_state = self._narrative_arc_state(state, planet.name)
        if arc_state == "active":
            lines.append(("Narrative arc in progress", (255, 220, 120)))
        elif arc_state == "complete":
            lines.append(("Arc complete", (200, 230, 150)))

        # Passives (brief — show first 2 only)
        try:
            from .planet_passives import PLANET_PASSIVES
            passives = PLANET_PASSIVES.get(planet.name, {})
            shown = 0
            for key, val in passives.items():
                if shown >= 2:
                    break
                lines.append((f"  {key}: {val}", (180, 200, 180)))
                shown += 1
        except Exception:
            pass

        # Layout
        pad = 8
        font = self.font_info
        surfaces = [font.render(t, True, c) for t, c in lines]
        w = max(s.get_width() for s in surfaces) + pad * 2
        h = sum(s.get_height() for s in surfaces) + pad * 2 + 2 * (len(surfaces) - 1)

        # Place next to planet but keep inside map_rect
        sx, sy = self._world_to_screen(planet.position)
        radius = self._get_planet_radius(planet)
        tx = sx + radius + 12
        ty = sy - h // 2
        if tx + w > self.map_rect.right:
            tx = sx - radius - 12 - w
        ty = max(self.map_rect.y + 4, min(ty, self.map_rect.bottom - h - 4))

        # Tooltip background (cached) + per-frame text on a copy
        tip = _get_tooltip_surf(w, h).copy()
        y = pad
        for s in surfaces:
            tip.blit(s, (pad, y))
            y += s.get_height() + 2
        screen.blit(tip, (tx, ty))

    def handle_event(self, event, galaxy_map, campaign_state, attackable_ids):
        """Handle mouse events. Returns action string or None."""
        # 12.0: activity log sidebar gets first dibs — it consumes key L,
        # clicks on its tab/panel, and scroll wheel events inside it.
        if self.activity_sidebar.handle_event(event, self):
            return None

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_planet = None
            for pid, rect in self.planet_rects.items():
                if rect.collidepoint(mx, my):
                    self.hovered_planet = pid
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # 12.0: Leader Command button hit-test (takes priority over
            # planet clicks so the strip stays usable when planets are dense)
            _lc_action = leader_command.hit_test(self, (mx, my))
            if _lc_action:
                return f"leader_action:{_lc_action}"

            # 12.0: Relic actives panel sits beneath the leader command
            # strip; same priority principle.
            _relic_action = relic_actives_panel.hit_test(self, (mx, my))
            if _relic_action:
                return f"relic_active:{_relic_action}"

            # Check panel toggle button
            if self.panel_toggle_btn_rect and self.panel_toggle_btn_rect.collidepoint(mx, my):
                self.panel_visible = not self.panel_visible
                self._recalculate_layout()
                self._panel_cache = None
                return None

            # Check side panel build buttons
            for btn_rect, building_id in self.build_button_rects:
                if btn_rect.collidepoint(mx, my):
                    return f"build_{building_id}"

            # Check side panel upgrade button
            if self.upgrade_button_rect and self.upgrade_button_rect.collidepoint(mx, my):
                if self.selected_planet:
                    return f"upgrade_{self.selected_planet}"

            # Check planet clicks
            for pid, rect in self.planet_rects.items():
                if rect.collidepoint(mx, my):
                    self.selected_planet = pid
                    return None

            # Check buttons
            if self.attack_button_rect.collidepoint(mx, my):
                if (self.selected_planet in attackable_ids
                        and self.selected_planet not in campaign_state.cooldowns):
                    return "attack"

            if self.fortify_button_rect.collidepoint(mx, my):
                return "fortify"

            if self.end_turn_button_rect.collidepoint(mx, my):
                return "end_turn"

            if self.view_deck_button_rect.collidepoint(mx, my):
                return "view_deck"

            if self.doctrines_button_rect.collidepoint(mx, my):
                return "doctrines"

            if self.diplomacy_button_rect.collidepoint(mx, my):
                return "diplomacy"

            if self.minor_world_button_rect.collidepoint(mx, my):
                if self.selected_planet and self.selected_planet in galaxy_map.planets:
                    _p = galaxy_map.planets[self.selected_planet]
                    if _p.planet_type == "neutral" and _p.owner == "player":
                        return "minor_world"

            if self.operatives_button_rect.collidepoint(mx, my):
                if len(getattr(campaign_state, 'operatives', [])) > 0:
                    return "operatives"

            # Click empty space (not in panel) — deselect
            if mx < self.panel_x:
                self.selected_planet = None

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "save_quit"
            elif event.key == pygame.K_d:
                return "view_deck"
            elif event.key == pygame.K_i:
                return "run_info"
            elif event.key == pygame.K_s:
                return "spy_report"
            elif event.key == pygame.K_TAB:
                self.panel_visible = not self.panel_visible
                self._recalculate_layout()
                self._panel_cache = None
                return None

        return None
