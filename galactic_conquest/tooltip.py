"""
STARGWENT - GALACTIC CONQUEST - Tooltip Helper

Shared tooltip rendering for conquest screens. Previously each screen
re-invented hover-text drawing; this consolidates the pattern with
multi-line wrapping, screen-edge clamping, and a CRT-styled box.

Callers just provide a pygame surface, text, anchor rect (or point),
and font. The helper picks a placement below/above/beside the anchor
to keep the tooltip on-screen.
"""

import pygame

from .conquest_menu import CRT_TEXT, CRT_BTN_BG, CRT_BTN_BORDER


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list:
    """Word-wrap *text* into a list of lines that each fit in *max_width*.

    Handles explicit newlines as hard line breaks and splits on spaces
    for soft wrapping. Very long unbreakable tokens are kept as-is on
    their own line (may visually overflow — callers choose max_width).
    """
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def draw_tooltip(screen: pygame.Surface,
                 text: str,
                 anchor,
                 font: pygame.font.Font,
                 *,
                 max_width: int = 340,
                 padding: int = 6,
                 text_color=CRT_TEXT,
                 bg_color=CRT_BTN_BG,
                 border_color=CRT_BTN_BORDER):
    """Render a tooltip box near *anchor* with wrapped *text*.

    Args:
        screen: Target surface.
        text: Tooltip body (supports `\\n` for hard line breaks).
        anchor: Either a pygame.Rect (tooltip attaches to it) or an
                (x, y) tuple (tooltip draws at that point).
        font: Font for the body text.
        max_width: Soft cap before wrapping.
        padding: Inner padding around text.
        text_color/bg_color/border_color: Override the default CRT look.

    Returns:
        The pygame.Rect of the drawn tooltip (useful for hit-testing).
    """
    if not text:
        return None

    sw, sh = screen.get_size()
    lines = wrap_text(text, font, max_width)
    if not lines:
        return None

    # Measure
    line_surfaces = [font.render(line, True, text_color) for line in lines]
    text_w = max(ls.get_width() for ls in line_surfaces)
    line_h = font.get_linesize()
    text_h = line_h * len(lines)

    box_w = text_w + padding * 2
    box_h = text_h + padding * 2

    # Determine anchor placement
    if isinstance(anchor, pygame.Rect):
        # Prefer below the anchor; flip above if it would clip
        x = anchor.x
        y = anchor.bottom + 3
        if y + box_h > sh - 4:
            y = anchor.top - box_h - 3
    else:
        x, y = anchor
        y += 3

    # Clamp horizontally
    x = max(4, min(x, sw - box_w - 4))
    # Clamp vertically (last resort — may overlap anchor)
    y = max(4, min(y, sh - box_h - 4))

    box_rect = pygame.Rect(x, y, box_w, box_h)
    pygame.draw.rect(screen, bg_color, box_rect)
    pygame.draw.rect(screen, border_color, box_rect, 1)

    for i, ls in enumerate(line_surfaces):
        screen.blit(ls, (x + padding, y + padding + i * line_h))

    return box_rect
