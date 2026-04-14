"""
STARGWENT - GALACTIC CONQUEST - Relic Actives Panel (12.0 Pillar 4c UI)

Compact UI strip beneath the Leader Command panel showing each owned
relic whose active ability still has charges.  Click a button to fire
the ability — for target-requiring actives, the controller resolves
the target the same way it does for leader actions.

Action protocol: clicks emit ``"relic_active:<relic_id>"`` which the
controller's map-loop dispatch handles via ``_handle_relic_active``.
"""

import pygame

from . import relics
from ._ui_utils import blit_alpha as _blit_alpha


# Layout constants (mirror leader_command panel for visual symmetry)
PANEL_W = 180
BTN_H = 42
BTN_GAP = 5

BG_OK = (40, 60, 90)
BG_DISABLED = (40, 40, 50)
BORDER = (120, 160, 220)
BORDER_DISABLED = (70, 70, 90)
TEXT = (230, 230, 245)
TEXT_SUB = (180, 190, 210)
HEADER = (180, 220, 255)


def draw_panel(screen, state, galaxy, mapscreen) -> dict:
    """Render the Relic Actives strip; return {relic_id: Rect}.

    Positions directly below the Leader Command panel on the left
    edge.  No-op if the player has no owned relics with actives.
    """
    actives = relics.get_active_relics(state)
    if not actives:
        mapscreen._relic_action_rects = {}
        return {}

    # Anchor: beneath the leader_command panel's rough footprint.
    leader_action_count = len(
        getattr(mapscreen, "_leader_action_rects", {}) or {})
    leader_panel_h = 22 + (leader_action_count * (48 + 6))  # mirrors LC panel
    top = mapscreen.map_rect.y + 8 + leader_panel_h + 18
    left = mapscreen.map_rect.x + 4

    font_btn = mapscreen.font_btn
    font_info = mapscreen.font_info

    # Header
    header_rect = pygame.Rect(left, top, PANEL_W, 22)
    _blit_alpha(screen, (*BG_OK, 210), header_rect)
    pygame.draw.rect(screen, BORDER, header_rect, 1)
    txt = font_btn.render("RELIC ACTIVES", True, HEADER)
    screen.blit(txt, (header_rect.centerx - txt.get_width() // 2,
                      header_rect.centery - txt.get_height() // 2))

    y = top + 22 + BTN_GAP
    rects = {}
    for relic_id, ability in actives:
        rect = pygame.Rect(left, y, PANEL_W, BTN_H)
        rects[relic_id] = rect

        remaining = relics.get_active_charges_remaining(state, relic_id)
        usable = remaining > 0
        bg = BG_OK if usable else BG_DISABLED
        border = BORDER if usable else BORDER_DISABLED

        _blit_alpha(screen, (*bg, 210), rect)
        pygame.draw.rect(screen, border, rect, 1)

        name_surf = font_btn.render(ability.get("name", relic_id),
                                     True, TEXT if usable else TEXT_SUB)
        screen.blit(name_surf, (rect.x + 6, rect.y + 4))

        charges = font_info.render(f"x{remaining}", True, TEXT_SUB)
        screen.blit(charges, (rect.right - charges.get_width() - 6,
                               rect.y + 4))

        desc = ability.get("desc", "")
        desc_surf = font_info.render(desc, True, TEXT_SUB)
        if desc_surf.get_width() > rect.width - 12:
            while desc and font_info.size(desc + "…")[0] > rect.width - 12:
                desc = desc[:-1]
            desc_surf = font_info.render(desc + "…", True, TEXT_SUB)
        screen.blit(desc_surf, (rect.x + 6, rect.y + 22))

        y += BTN_H + BTN_GAP

    mapscreen._relic_action_rects = rects
    return rects


def hit_test(mapscreen, pos) -> str | None:
    """Return the relic_id at ``pos`` or ``None``."""
    rects = getattr(mapscreen, "_relic_action_rects", None) or {}
    for relic_id, rect in rects.items():
        if rect.collidepoint(pos):
            return relic_id
    return None


