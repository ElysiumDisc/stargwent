"""
STARGWENT - GALACTIC CONQUEST - Relic Acquisition Screen

CRT-styled screen shown when the player acquires a new relic.
Supports single-relic "Acquired!" mode and multi-choice mode (events).
"""

import pygame
import math
import display_manager


def show_relic_acquired(screen, relic, source_text=""):
    """Show a dramatic relic acquisition screen.

    Args:
        screen: Pygame display surface
        relic: Relic dataclass instance
        source_text: Optional context string (e.g. "Conquered Goa'uld Homeworld")
    """
    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    # CRT colors
    CRT_AMBER = (255, 176, 0)
    CRT_GREEN = (0, 200, 80)
    CRT_BG = (8, 12, 10)

    title_font = pygame.font.SysFont("Impact, Arial", max(48, sh // 18), bold=True)
    name_font = pygame.font.SysFont("Impact, Arial", max(36, sh // 22), bold=True)
    icon_font = pygame.font.SysFont("Arial", max(72, sh // 10))
    desc_font = pygame.font.SysFont("Arial", max(20, sh // 45))
    info_font = pygame.font.SysFont("Arial", max(16, sh // 55))

    frame = 0
    running = True
    while running:
        clock.tick(60)
        frame += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if frame > 30:  # min display time
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if frame > 30:
                    running = False

        screen.fill(CRT_BG)

        # Dark overlay with slight amber tint
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((20, 15, 0, 180))
        screen.blit(overlay, (0, 0))

        pulse = 0.8 + 0.2 * math.sin(frame * 0.05)

        # "RELIC ACQUIRED" title
        title_color = tuple(int(c * pulse) for c in CRT_AMBER)
        title_surf = title_font.render("RELIC ACQUIRED", True, title_color)
        screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, int(sh * 0.12)))

        # Source text
        if source_text:
            src_surf = info_font.render(source_text, True, (150, 150, 150))
            screen.blit(src_surf, (sw // 2 - src_surf.get_width() // 2, int(sh * 0.20)))

        # Relic icon (large)
        icon_surf = icon_font.render(relic.icon_char, True, CRT_AMBER)
        screen.blit(icon_surf, (sw // 2 - icon_surf.get_width() // 2, int(sh * 0.30)))

        # Relic name
        name_surf = name_font.render(relic.name, True, (255, 255, 255))
        screen.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, int(sh * 0.48)))

        # Category tag
        cat_colors = {"combat": (255, 100, 100), "economy": (100, 200, 255), "exploration": (100, 255, 150)}
        cat_color = cat_colors.get(relic.category, (200, 200, 200))
        cat_surf = info_font.render(f"[{relic.category.upper()}]", True, cat_color)
        screen.blit(cat_surf, (sw // 2 - cat_surf.get_width() // 2, int(sh * 0.55)))

        # Description
        desc_surf = desc_font.render(relic.description, True, CRT_GREEN)
        screen.blit(desc_surf, (sw // 2 - desc_surf.get_width() // 2, int(sh * 0.63)))

        # Continue hint
        if frame > 30:
            hint_surf = info_font.render("Click or press any key to continue", True, (120, 120, 120))
            screen.blit(hint_surf, (sw // 2 - hint_surf.get_width() // 2, int(sh * 0.82)))

        display_manager.gpu_flip()


def show_relic_choice(screen, relic_ids):
    """Show a choice between multiple relics (for events).

    Args:
        screen: Pygame display surface
        relic_ids: List of relic ID strings to choose from

    Returns:
        Chosen relic ID string, or None if no valid relics.
    """
    from .relics import RELICS

    valid = [(rid, RELICS[rid]) for rid in relic_ids if rid in RELICS]
    if not valid:
        return None
    if len(valid) == 1:
        show_relic_acquired(screen, valid[0][1])
        return valid[0][0]

    sw, sh = screen.get_width(), screen.get_height()
    clock = pygame.time.Clock()

    CRT_AMBER = (255, 176, 0)
    CRT_GREEN = (0, 200, 80)

    title_font = pygame.font.SysFont("Impact, Arial", max(36, sh // 22), bold=True)
    name_font = pygame.font.SysFont("Impact, Arial", max(24, sh // 35), bold=True)
    icon_font = pygame.font.SysFont("Arial", max(48, sh // 16))
    desc_font = pygame.font.SysFont("Arial", max(16, sh // 60))
    info_font = pygame.font.SysFont("Arial", max(14, sh // 70))

    # Layout: horizontal cards
    card_w = int(sw * 0.22)
    card_h = int(sh * 0.45)
    spacing = int(sw * 0.03)
    total_w = len(valid) * card_w + (len(valid) - 1) * spacing
    start_x = (sw - total_w) // 2
    card_y = int(sh * 0.30)

    rects = []
    for i in range(len(valid)):
        x = start_x + i * (card_w + spacing)
        rects.append(pygame.Rect(x, card_y, card_w, card_h))

    hovered = -1
    chosen = None

    while chosen is None:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return valid[0][0]  # fallback
            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                hovered = -1
                for i, rect in enumerate(rects):
                    if rect.collidepoint(mx, my):
                        hovered = i
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, rect in enumerate(rects):
                    if rect.collidepoint(mx, my):
                        chosen = valid[i][0]
                        break

        screen.fill((8, 12, 10))
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((20, 15, 0, 160))
        screen.blit(overlay, (0, 0))

        title_surf = title_font.render("CHOOSE A RELIC", True, CRT_AMBER)
        screen.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, int(sh * 0.08)))

        for i, (rid, relic) in enumerate(valid):
            rect = rects[i]
            bg_color = (40, 50, 35) if i == hovered else (25, 30, 25)
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_surf.fill((*bg_color, 220))
            screen.blit(card_surf, rect.topleft)

            border_color = CRT_AMBER if i == hovered else (80, 80, 80)
            pygame.draw.rect(screen, border_color, rect, 2)

            # Icon
            icon_surf = icon_font.render(relic.icon_char, True, CRT_AMBER)
            screen.blit(icon_surf, (rect.centerx - icon_surf.get_width() // 2,
                                    rect.y + int(card_h * 0.08)))

            # Name
            name_surf = name_font.render(relic.name, True, (255, 255, 255))
            screen.blit(name_surf, (rect.centerx - name_surf.get_width() // 2,
                                    rect.y + int(card_h * 0.40)))

            # Category
            cat_colors = {"combat": (255, 100, 100), "economy": (100, 200, 255),
                          "exploration": (100, 255, 150)}
            cat_surf = info_font.render(f"[{relic.category.upper()}]", True,
                                        cat_colors.get(relic.category, (200, 200, 200)))
            screen.blit(cat_surf, (rect.centerx - cat_surf.get_width() // 2,
                                   rect.y + int(card_h * 0.52)))

            # Description (word wrap)
            words = relic.description.split()
            lines = []
            current = ""
            for word in words:
                test = f"{current} {word}".strip()
                if desc_font.size(test)[0] < card_w - 20:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)

            desc_y = rect.y + int(card_h * 0.62)
            for line in lines:
                line_surf = desc_font.render(line, True, CRT_GREEN)
                screen.blit(line_surf, (rect.centerx - line_surf.get_width() // 2, desc_y))
                desc_y += line_surf.get_height() + 2

        display_manager.gpu_flip()

    return chosen
