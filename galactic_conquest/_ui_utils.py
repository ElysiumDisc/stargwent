"""Small shared UI helpers for the galactic_conquest map-screen panels."""

import pygame


def blit_alpha(screen, rgba, rect):
    """Blit a filled semi-transparent rectangle. Cache-free and cheap."""
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    surf.fill(rgba)
    screen.blit(surf, rect.topleft)
