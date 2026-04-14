"""
STARGWENT - GALACTIC CONQUEST - Save Slot Picker (12.0 Pillar 5d UI)

Modal shown when the player clicks NEW CAMPAIGN or RESUME and more
than one slot is relevant:

- NEW CAMPAIGN: display all 3 slots; empty slots start a fresh run,
  filled slots warn before overwriting.
- RESUME: display only slots with saves; the legacy single-save flow
  auto-picks slot 0 when that's the only option.

Returns the chosen slot (0-2) or ``None`` if the player cancels.
"""

import asyncio
import pygame
import display_manager

from .campaign_persistence import NUM_SAVE_SLOTS, list_save_slots


BG = (10, 14, 26)
HEADER = (255, 220, 130)
TEXT = (220, 220, 235)
TEXT_SUB = (160, 170, 190)
TEXT_EMPTY = (140, 160, 200)
TEXT_WARN = (240, 160, 100)
BORDER = (80, 120, 180)
BORDER_HOVER = (140, 200, 255)


async def pick_slot(screen, mode: str) -> int | None:
    """Show the slot picker.  *mode* is ``"new"`` or ``"resume"``.

    Resume mode skips empty slots and auto-returns slot 0 when that's
    the only populated one — keeps the single-save flow frictionless
    for 11.x users.
    """
    slots = list_save_slots()

    if mode == "resume":
        populated = [s for s in slots if s["exists"]]
        if not populated:
            return None
        if len(populated) == 1:
            return populated[0]["slot"]
        slots = populated  # show only the populated ones

    sw, sh = screen.get_width(), screen.get_height()
    font_title = pygame.font.SysFont("Impact, Arial", max(40, sh // 24), bold=True)
    font_slot = pygame.font.SysFont("Arial", max(22, sh // 42), bold=True)
    font_body = pygame.font.SysFont("Arial", max(16, sh // 58))
    font_hint = pygame.font.SysFont("Arial", max(14, sh // 64))

    slot_w = int(sw * 0.24)
    slot_h = int(sh * 0.36)
    gap = int(sw * 0.03)
    total_w = len(slots) * slot_w + (len(slots) - 1) * gap
    left = (sw - total_w) // 2
    top = int(sh * 0.26)

    def rect_for(i):
        return pygame.Rect(left + i * (slot_w + gap), top, slot_w, slot_h)

    cancel_rect = pygame.Rect((sw - int(sw * 0.14)) // 2,
                                top + slot_h + int(sh * 0.05),
                                int(sw * 0.14), int(sh * 0.05))

    while True:
        await asyncio.sleep(0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, info in enumerate(slots):
                    if rect_for(i).collidepoint(event.pos):
                        if mode == "resume" and not info["exists"]:
                            continue  # can't resume empty slot
                        return info["slot"]
                if cancel_rect.collidepoint(event.pos):
                    return None

        overlay = pygame.Surface((sw, sh))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(220)
        screen.blit(overlay, (0, 0))

        title = font_title.render(
            "CHOOSE SAVE SLOT" if mode == "new" else "RESUME WHICH SLOT?",
            True, HEADER)
        screen.blit(title, ((sw - title.get_width()) // 2,
                             int(sh * 0.10)))
        sub = font_hint.render(
            "Empty slots start a fresh campaign. Filled slots overwrite — click carefully."
            if mode == "new" else "Pick the save you want to resume.",
            True, TEXT_SUB)
        screen.blit(sub, ((sw - sub.get_width()) // 2, int(sh * 0.16)))

        mx, my = pygame.mouse.get_pos()
        for i, info in enumerate(slots):
            rect = rect_for(i)
            hovered = rect.collidepoint(mx, my)
            _draw_slot(screen, rect, info, font_slot, font_body,
                        hovered, mode)

        # Cancel button
        hovered_cancel = cancel_rect.collidepoint(mx, my)
        pygame.draw.rect(screen, (70, 40, 40) if not hovered_cancel
                           else (110, 60, 60), cancel_rect)
        pygame.draw.rect(screen, (190, 130, 130), cancel_rect, 2)
        c_lbl = font_slot.render("Cancel", True, TEXT)
        screen.blit(c_lbl, (cancel_rect.centerx - c_lbl.get_width() // 2,
                              cancel_rect.centery - c_lbl.get_height() // 2))

        display_manager.gpu_flip()


def _draw_slot(screen, rect, info, font_slot, font_body, hovered, mode):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((*BG, 230))
    pygame.draw.rect(panel, BORDER_HOVER if hovered else BORDER,
                      panel.get_rect(), 2)

    pad = 12
    y = pad
    title = font_slot.render(f"Slot {info['slot'] + 1}", True, HEADER)
    panel.blit(title, (pad, y))
    y += title.get_height() + 10

    if not info["exists"]:
        empty = font_body.render("— empty —" if mode == "new"
                                  else "(no save)", True, TEXT_EMPTY)
        panel.blit(empty, (pad, y))
        y += empty.get_height() + 6
        if mode == "new":
            hint = font_body.render("Click to start a fresh campaign here.",
                                     True, TEXT_SUB)
            panel.blit(hint, (pad, y))
    else:
        if mode == "new":
            warn = font_body.render("Will OVERWRITE.", True, TEXT_WARN)
            panel.blit(warn, (pad, y))
            y += warn.get_height() + 6
        for line in (
            f"Faction: {info.get('faction') or '?'}",
            f"Leader: {info.get('player_name') or '?'}",
            f"Turn: {info.get('turn', 0)}",
            f"Planets: {info.get('planets', 0)}",
        ):
            surf = font_body.render(line, True, TEXT)
            panel.blit(surf, (pad, y))
            y += surf.get_height() + 4

    screen.blit(panel, rect.topleft)
