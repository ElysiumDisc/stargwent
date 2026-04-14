"""
STARGWENT - GALACTIC CONQUEST - Spy Report (12.0 Pillar 3d)

Per-faction intel screen.  Always shows the coarse strategic picture
(planet count, relation, favor, active treaties) so the diplomatic
state is legible at any time.  When ``conquest_ability_data
['ai_intel_turns'] > 0`` (set by the Quantum Mirror relic, Tok'ra-tier
operatives, or scripted events), the report also exposes adopted AI
doctrines and building counts.

Opened with the **S** key on the galaxy map.
"""

import asyncio
import pygame
import display_manager


BG = (10, 14, 26)
HEADER = (255, 220, 130)
TEXT = (220, 220, 235)
TEXT_SUB = (160, 170, 190)
TEXT_GOOD = (120, 220, 150)
TEXT_BAD = (240, 130, 130)
TEXT_TREATY = (220, 180, 100)
BORDER = (70, 110, 160)


RELATION_COLORS = {
    "allied": TEXT_GOOD,
    "trading": (140, 180, 230),
    "neutral": TEXT_SUB,
    "hostile": TEXT_BAD,
}


async def show_spy_report(screen, state, galaxy):
    """Render and run the Spy Report modal.  Closes on Esc or click.

    The report is a stable snapshot while open, so we build the entire
    composite surface (overlay + title + faction cards) once and blit it
    each frame.  No per-frame font/Surface allocation.
    """
    sw, sh = screen.get_size()
    font_title = pygame.font.SysFont("Impact, Arial", max(32, sh // 32), bold=True)
    font_header = pygame.font.SysFont("Arial", max(18, sh // 48), bold=True)
    font_body = pygame.font.SysFont("Arial", max(15, sh // 60))
    font_hint = pygame.font.SysFont("Arial", max(13, sh // 70))

    intel_turns = int(state.conquest_ability_data.get("ai_intel_turns", 0))
    intel_on = intel_turns > 0

    # Collect survivors
    factions = sorted({p.owner for p in galaxy.planets.values()
                        if p.owner not in ("player", "neutral", state.friendly_faction)})

    # --- Build the whole report once ---------------------------------
    composite = pygame.Surface((sw, sh), pygame.SRCALPHA)
    composite.fill((0, 0, 0, 220))

    title_text = ("SPY REPORT — ENHANCED INTEL"
                  if intel_on else "SPY REPORT — SURFACE-LEVEL INTEL")
    title = font_title.render(title_text, True, HEADER)
    tw, _ = title.get_size()
    composite.blit(title, ((sw - tw) // 2, int(sh * 0.06)))

    sub_text = (f"Enhanced intel expires in {intel_turns} turn(s)."
                if intel_on else
                "Activate Quantum Mirror or a Tok'ra operative for enhanced intel.")
    sub = font_hint.render(sub_text, True, TEXT_SUB)
    sw2, _ = sub.get_size()
    composite.blit(sub, ((sw - sw2) // 2, int(sh * 0.10)))

    if not factions:
        none_surf = font_body.render("No rival factions remain.", True, TEXT_SUB)
        nw, _ = none_surf.get_size()
        composite.blit(none_surf, ((sw - nw) // 2, sh // 2))
    else:
        top = int(sh * 0.16)
        card_w = int(sw * 0.26)
        card_h = int(sh * 0.52)
        gap = int(sw * 0.02)
        total_w = len(factions) * card_w + (len(factions) - 1) * gap
        left = (sw - total_w) // 2
        for i, f in enumerate(factions):
            card_rect = pygame.Rect(left + i * (card_w + gap),
                                      top, card_w, card_h)
            _draw_faction_card(composite, state, galaxy, f, card_rect,
                                font_header, font_body, font_hint, intel_on)

    hint = font_hint.render("Press S / Esc / click to close.", True, TEXT_SUB)
    hw, hh = hint.get_size()
    composite.blit(hint, ((sw - hw) // 2, sh - hh - 12))

    # --- Event loop: just blit + flip --------------------------------
    while True:
        await asyncio.sleep(0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_ESCAPE, pygame.K_s, pygame.K_RETURN):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                return

        screen.blit(composite, (0, 0))
        display_manager.gpu_flip()


def _draw_faction_card(screen, state, galaxy, faction, rect,
                        font_header, font_body, font_hint, intel_on):
    """Render one faction's intel panel."""
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((*BG, 230))
    pygame.draw.rect(panel, BORDER, panel.get_rect(), 2)

    # Header — faction name
    pad = 10
    y = pad
    hdr = font_header.render(faction, True, HEADER)
    panel.blit(hdr, (pad, y))
    y += hdr.get_height() + 6

    # Relation + favor
    rel = (state.faction_relations or {}).get(faction, "hostile")
    rel_color = RELATION_COLORS.get(rel, TEXT)
    favor = (state.diplomatic_favor or {}).get(faction, 0)
    rel_surf = font_body.render(f"Relation: {rel}", True, rel_color)
    panel.blit(rel_surf, (pad, y))
    y += rel_surf.get_height() + 2
    favor_surf = font_body.render(f"Favor: {favor:+d}", True, TEXT)
    panel.blit(favor_surf, (pad, y))
    y += favor_surf.get_height() + 2

    # Planet count + homeworld status
    planets = galaxy.get_faction_planet_count(faction)
    planets_surf = font_body.render(f"Planets held: {planets}", True, TEXT)
    panel.blit(planets_surf, (pad, y))
    y += planets_surf.get_height() + 2

    # Active treaties
    treaties = [t for t in (state.treaties or [])
                if t.get("faction") == faction
                and t.get("turns_remaining", 0) > 0]
    if treaties:
        treaty_line = ", ".join(
            f"{t['type'].upper()} {t.get('turns_remaining', 0)}t"
            for t in treaties)
        t_surf = font_body.render(f"Treaties: {treaty_line}",
                                    True, TEXT_TREATY)
        panel.blit(t_surf, (pad, y))
        y += t_surf.get_height() + 2

    # Coalition membership
    if state.coalition.get("active") and faction in (state.coalition.get("members") or []):
        c_surf = font_body.render("In anti-coalition", True, TEXT_BAD)
        panel.blit(c_surf, (pad, y))
        y += c_surf.get_height() + 2

    # Recent planet losses (always visible — factions notice each other too)
    losses = state.conquest_ability_data.get(
        f"_faction_planets_lost_{faction}", 0)
    if losses:
        l_surf = font_body.render(f"Recent losses: {losses}", True, TEXT_SUB)
        panel.blit(l_surf, (pad, y))
        y += l_surf.get_height() + 2

    # Divider before enhanced-intel block
    y += 4
    pygame.draw.line(panel, (60, 80, 120), (pad, y), (rect.width - pad, y), 1)
    y += 6

    if not intel_on:
        hint = font_hint.render("— Enhanced intel required —",
                                  True, TEXT_SUB)
        panel.blit(hint, (pad, y))
    else:
        doctrines = state.ai_doctrines.get(faction, []) or []
        d_surf = font_body.render(
            f"Doctrines ({len(doctrines)}): {', '.join(doctrines) or 'none'}",
            True, TEXT)
        panel.blit(d_surf, (pad, y))
        y += d_surf.get_height() + 2
        # Approximate building count: buildings dict entries on this faction's planets
        building_count = 0
        for pid, owner in state.planet_ownership.items():
            if owner == faction and pid in state.buildings:
                building_count += 1
        b_surf = font_body.render(f"Buildings: {building_count}",
                                    True, TEXT)
        panel.blit(b_surf, (pad, y))
        y += b_surf.get_height() + 2

        # Personality flavor
        try:
            from .campaign_controller import _get_personality
            pers = _get_personality(faction)
            pers_line = f"Personality: ×{pers.get('counterattack_mult', 1.0):.1f} CA"
            if pers.get("vengeful"):
                pers_line += ", vengeful"
            if pers.get("target_weakest"):
                pers_line += ", opportunist"
            p_surf = font_body.render(pers_line, True, TEXT_SUB)
            panel.blit(p_surf, (pad, y))
        except Exception:
            pass

    screen.blit(panel, rect.topleft)
