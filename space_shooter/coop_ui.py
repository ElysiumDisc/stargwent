"""
Co-op Space Shooter UI Elements

Dual health bars, partner indicator arrow, CO-OP label,
revival status overlay, and latency display for co-op mode.

Used by both CoopSpaceShooterGame (host) and CoopSpaceShooterClient.
"""

import math
import pygame


def draw_coop_label(surface, screen_width):
    """Draw 'CO-OP' label at top center."""
    font = pygame.font.SysFont("Arial", 18, bold=True)
    label = font.render("CO-OP", True, (100, 255, 100))
    surface.blit(label, (screen_width // 2 - label.get_width() // 2, 5))


def draw_dual_health_bars(surface, p1_data, p2_data, screen_width):
    """Draw P1 health top-left, P2 health top-right.

    p1_data / p2_data: dicts with health, max_health, shields, max_shields, alive, ghost
    """
    _draw_bar(surface, p1_data, 10, 10, "P1")
    _draw_bar(surface, p2_data, screen_width - 240, 10, "P2")


def _draw_bar(surface, data, x, y, label):
    """Draw a single health+shield bar set."""
    if not data:
        return
    bar_w, bar_h = 220, 12
    font = pygame.font.SysFont("Arial", 14, bold=True)

    if not data.get('alive') and not data.get('ghost'):
        return

    if data.get('ghost'):
        text = font.render(f"{label} DOWN — Kill to revive!", True, (255, 80, 80))
        surface.blit(text, (x, y))
        return

    lbl = font.render(label, True, (200, 200, 200))
    surface.blit(lbl, (x, y))

    hp = data.get('health', 0)
    max_hp = data.get('max_health', 100)
    sh = data.get('shields', 0)
    max_sh = data.get('max_shields', 100)

    # Health
    bar_y = y + 18
    hp_pct = max(0.0, hp / max_hp) if max_hp > 0 else 0
    pygame.draw.rect(surface, (40, 40, 40), (x, bar_y, bar_w, bar_h))
    pygame.draw.rect(surface, (50, 200, 50), (x, bar_y, int(bar_w * hp_pct), bar_h))
    pygame.draw.rect(surface, (100, 100, 100), (x, bar_y, bar_w, bar_h), 1)

    # Shields
    bar_y += bar_h + 2
    sh_pct = max(0.0, sh / max_sh) if max_sh > 0 else 0
    pygame.draw.rect(surface, (40, 40, 40), (x, bar_y, bar_w, bar_h))
    pygame.draw.rect(surface, (50, 130, 255), (x, bar_y, int(bar_w * sh_pct), bar_h))
    pygame.draw.rect(surface, (100, 100, 100), (x, bar_y, bar_w, bar_h), 1)


def draw_partner_arrow(surface, camera, partner_data, screen_width, screen_height):
    """Draw an arrow pointing toward partner when off-screen."""
    if not partner_data or (not partner_data.get('alive') and not partner_data.get('ghost')):
        return

    px = partner_data.get('x', 0)
    py = partner_data.get('y', 0)
    sx, sy = camera.world_to_screen(px, py)

    margin = 60
    if margin < sx < screen_width - margin and margin < sy < screen_height - margin:
        return  # On screen, no arrow needed

    cx, cy = screen_width // 2, screen_height // 2
    dx = sx - cx
    dy = sy - cy
    dist = max(1, math.hypot(dx, dy))
    edge_dist = min(
        (screen_width // 2 - 30) / max(1, abs(dx / dist)),
        (screen_height // 2 - 30) / max(1, abs(dy / dist))
    )
    ax = int(cx + dx / dist * edge_dist)
    ay = int(cy + dy / dist * edge_dist)

    color = (100, 200, 255) if partner_data.get('alive') else (255, 100, 100)
    angle = math.atan2(dy, dx)
    size = 12
    pts = [
        (ax + int(math.cos(angle) * size),
         ay + int(math.sin(angle) * size)),
        (ax + int(math.cos(angle + 2.5) * size * 0.6),
         ay + int(math.sin(angle + 2.5) * size * 0.6)),
        (ax + int(math.cos(angle - 2.5) * size * 0.6),
         ay + int(math.sin(angle - 2.5) * size * 0.6)),
    ]
    pygame.draw.polygon(surface, color, pts)


def draw_revival_pulse(surface, camera, ship_x, ship_y, timer, max_timer=30):
    """Draw expanding circle pulse at revival location."""
    if timer <= 0:
        return
    sx, sy = camera.world_to_screen(ship_x, ship_y)
    radius = int(40 + (max_timer - timer) * 3)
    alpha = int(200 * timer / max_timer)
    pulse_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(pulse_surf, (100, 255, 100, alpha),
                       (radius, radius), radius, 3)
    surface.blit(pulse_surf, (int(sx - radius), int(sy - radius)))


def draw_leash_warning(surface, screen_width):
    """Draw 'TOO FAR APART!' warning."""
    font = pygame.font.SysFont("Arial", 24, bold=True)
    warn = font.render("TOO FAR APART!", True, (255, 200, 50))
    surface.blit(warn, (screen_width // 2 - warn.get_width() // 2, 40))


def draw_latency(surface, session, screen_width, screen_height):
    """Draw latency display in bottom-right."""
    latency = session.get_latency() if hasattr(session, 'get_latency') else 0
    font = pygame.font.SysFont("Arial", 14, bold=True)
    color, _ = session.get_latency_status() if hasattr(session, 'get_latency_status') else ((150, 150, 150), "")
    text = font.render(f"{latency}ms", True, color)
    surface.blit(text, (screen_width - text.get_width() - 10, screen_height - 25))
