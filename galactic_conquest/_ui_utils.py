"""Small shared UI helpers for the galactic_conquest map-screen panels."""

from collections import OrderedDict

import pygame


# Bounded LRU text-render cache shared across conquest screens.
# font.render() is expensive; most labels (faction names, button labels,
# resource counts) are stable across many frames.
_text_cache: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()
_TEXT_CACHE_MAX = 512


def render_text_cached(font, text, color):
    """Return a cached rendered text surface.

    Font must be a stable cached object (constructed once per screen, not
    per frame). Color is a 3-tuple or 4-tuple.
    """
    key = (id(font), text, color if len(color) == 3 else color[:3])
    surf = _text_cache.get(key)
    if surf is not None:
        _text_cache.move_to_end(key)
        return surf
    surf = font.render(text, True, color)
    _text_cache[key] = surf
    if len(_text_cache) > _TEXT_CACHE_MAX:
        # Evict the oldest 64 in one batch so this branch runs rarely.
        for _ in range(64):
            _text_cache.popitem(last=False)
    return surf


def clear_text_cache():
    """Clear the text cache. Call on resolution change or large state shift."""
    _text_cache.clear()


# --- Filled SRCALPHA rectangle cache (small static panels) ---
_alpha_rect_cache: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()
_ALPHA_RECT_CACHE_MAX = 64


def blit_alpha(screen, rgba, rect):
    """Blit a filled semi-transparent rectangle. Uses cached SRCALPHA surface."""
    key = (rect.width, rect.height, rgba)
    surf = _alpha_rect_cache.get(key)
    if surf is None:
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill(rgba)
        _alpha_rect_cache[key] = surf
        if len(_alpha_rect_cache) > _ALPHA_RECT_CACHE_MAX:
            _alpha_rect_cache.popitem(last=False)
    else:
        _alpha_rect_cache.move_to_end(key)
    screen.blit(surf, rect.topleft)
