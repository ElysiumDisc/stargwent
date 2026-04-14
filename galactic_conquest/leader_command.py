"""
STARGWENT - GALACTIC CONQUEST - Leader Command Panel (12.0 Pillar 1 UI)

Compact UI strip on the left edge of the galaxy map displaying the
current leader's 2-3 toolkit actions as clickable buttons.

The panel is stateless — ``draw_panel`` paints the current frame and
stores a ``dict[action_id → pygame.Rect]`` in the ``MapScreen``
instance for ``hit_test`` to consult on click.  No hover state,
animation, or internal cursor — keep it boring and legible so Sprint 3
can add the polish.

Action string protocol with ``map_renderer.handle_event``:

    returns "leader_action:<action_id>"

The controller decides target resolution (``_handle_leader_action``):
- ``target_kind == "none"``     → execute immediately
- ``target_kind == "own_planet"`` / ``"enemy_planet"`` / ``"any_planet"``
                               → use ``selected_planet`` if valid,
                                 else flash "select a planet first"
- ``target_kind == "faction"``  → open a simple faction chooser dialog
"""

import pygame

from . import leader_toolkits
from ._ui_utils import blit_alpha as _blit_alpha


# --- Layout constants -----------------------------------------------------
PANEL_W = 180
BTN_H = 48
BTN_GAP = 6
PANEL_TOP_OFFSET = 8  # gap below the top HUD

# --- Colors ---------------------------------------------------------------
BG = (12, 16, 30, 200)
BG_OK = (30, 60, 110)
BG_DISABLED = (40, 40, 50)
BORDER = (80, 120, 180)
BORDER_DISABLED = (70, 70, 90)
TEXT = (230, 230, 245)
TEXT_SUB = (180, 190, 210)
TEXT_COST = (250, 210, 120)
TEXT_COOL = (255, 150, 150)
HEADER = (255, 220, 140)


def draw_panel(screen, state, galaxy, mapscreen) -> dict:
    """Draw the Leader Command strip and return {action_id: Rect}.

    Anchored to the left edge of ``mapscreen.map_rect``.  No-op if the
    player's leader has no registered toolkit.
    """
    actions = leader_toolkits.list_actions(state)
    if not actions:
        mapscreen._leader_action_rects = {}
        return {}

    # Fonts lifted from mapscreen so we don't re-allocate.
    font_btn = mapscreen.font_btn
    font_info = mapscreen.font_info

    top = mapscreen.map_rect.y + PANEL_TOP_OFFSET
    left = mapscreen.map_rect.x + 4
    rects = {}

    # Header band.
    header_rect = pygame.Rect(left, top, PANEL_W, 22)
    _blit_alpha(screen, BG, header_rect)
    pygame.draw.rect(screen, BORDER, header_rect, 1)
    txt = font_btn.render("LEADER COMMAND", True, HEADER)
    screen.blit(txt, (header_rect.centerx - txt.get_width() // 2,
                      header_rect.centery - txt.get_height() // 2))

    y = top + 22 + BTN_GAP
    for action in actions:
        rect = pygame.Rect(left, y, PANEL_W, BTN_H)
        rects[action.id] = rect

        ok, reason = leader_toolkits.can_use(state, galaxy, action.id)
        bg = BG_OK if ok else BG_DISABLED
        border = BORDER if ok else BORDER_DISABLED

        _blit_alpha(screen, (*bg, 210), rect)
        pygame.draw.rect(screen, border, rect, 1)

        name = font_btn.render(action.name, True, TEXT if ok else TEXT_SUB)
        screen.blit(name, (rect.x + 6, rect.y + 4))

        # Second line: cost / cooldown / charges
        astate = state.leader_action_state.get(action.id, {})
        bits = []
        if action.cost_naq:
            bits.append(("cost", f"{action.cost_naq} naq", TEXT_COST))
        if astate.get("cooldown", 0) > 0:
            bits.append(("cd", f"CD {astate['cooldown']}t", TEXT_COOL))
        elif action.cooldown_turns:
            bits.append(("cd", f"{action.cooldown_turns}t", TEXT_SUB))
        if action.charges is not None:
            remaining = max(0, action.charges - astate.get("charges_used", 0))
            bits.append(("chg", f"x{remaining}", TEXT_COOL if remaining <= 0 else TEXT_SUB))
        if not bits and not action.cooldown_turns:
            bits.append(("", "Free", TEXT_SUB))

        xoff = rect.x + 6
        for _kind, text, color in bits:
            surf = font_info.render(text, True, color)
            if xoff + surf.get_width() > rect.right - 4:
                break
            screen.blit(surf, (xoff, rect.y + 26))
            xoff += surf.get_width() + 8

        # Inline "reason" when disabled — small right-justified hint.
        if not ok and reason:
            r_surf = font_info.render(reason, True, TEXT_COOL)
            if r_surf.get_width() < PANEL_W - 8:
                screen.blit(r_surf, (rect.right - r_surf.get_width() - 6,
                                      rect.y + 26))

        y += BTN_H + BTN_GAP

    mapscreen._leader_action_rects = rects
    return rects


def hit_test(mapscreen, pos) -> str | None:
    """Return the action_id at ``pos`` or ``None``."""
    rects = getattr(mapscreen, "_leader_action_rects", None) or {}
    for action_id, rect in rects.items():
        if rect.collidepoint(pos):
            return action_id
    return None


