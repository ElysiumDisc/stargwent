import pygame
import math
import random
import os
import game_config as cfg
import display_manager
from game_config import (
    UI_FONT,
    PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS,
    CARD_WIDTH, CARD_HEIGHT
)


def _get_gpu():
    """Get GPU renderer if available and enabled."""
    gpu = display_manager.gpu_renderer
    if gpu and gpu.enabled:
        return gpu
    return None


def _enable_effect(gpu, name):
    """Safely enable a GPU effect."""
    if gpu:
        gpu.set_effect_enabled(name, True)


def _disable_effect(gpu, name):
    """Safely disable a GPU effect."""
    if gpu:
        gpu.set_effect_enabled(name, False)


def _set_effect_uniform(gpu, name, uniform, value):
    """Safely set a uniform on a GPU effect."""
    if not gpu:
        return
    effect = gpu.get_effect(name)
    if effect:
        effect.set_uniform(uniform, value)

def create_card_sweep_animation(screen, game, screen_width, screen_height, direction="out"):
    """
    Animate all cards on board sweeping off screen.
    direction: "out" = cards fly outward, "up" = cards fly up into hyperspace
    """
    clock = pygame.time.Clock()
    gpu = _get_gpu()

    # Enable hyperspace shader for "up" direction (cards jumping to hyperspace)
    if direction == "up" and gpu:
        _enable_effect(gpu, "hyperspace")
        _set_effect_uniform(gpu, "hyperspace", "direction", 1.0)
        _set_effect_uniform(gpu, "hyperspace", "center", (0.5, 0.5))

    # Collect all card positions from both players' boards
    card_snapshots = []

    for player in [game.player1, game.player2]:
        for row_name in ["close", "ranged", "siege"]:
            row_cards = player.board.get(row_name, [])
            # Get approximate card positions based on row
            if player == game.player1:
                row_rect = cfg.PLAYER_ROW_RECTS.get(row_name)
            else:
                row_rect = cfg.OPPONENT_ROW_RECTS.get(row_name)

            if row_rect and row_cards:
                card_spacing = cfg.CARD_WIDTH + 5
                start_x = row_rect.x + 10
                for i, card in enumerate(row_cards):
                    card_x = start_x + i * card_spacing
                    card_y = row_rect.y + (row_rect.height - cfg.CARD_HEIGHT) // 2

                    # Calculate direction vector (outward from center or upward)
                    center_x, center_y = screen_width // 2, screen_height // 2
                    if direction == "out":
                        dx = card_x - center_x
                        dy = card_y - center_y
                        dist = math.sqrt(dx*dx + dy*dy) or 1
                        vx = (dx / dist) * random.uniform(15, 25)
                        vy = (dy / dist) * random.uniform(15, 25)
                    else:  # "up" - hyperspace jump
                        vx = random.uniform(-2, 2)
                        vy = random.uniform(-30, -20)

                    card_snapshots.append({
                        'image': card.image.copy() if card.image else None,
                        'x': float(card_x),
                        'y': float(card_y),
                        'vx': vx,
                        'vy': vy,
                        'rotation': 0,
                        'rot_speed': random.uniform(-8, 8),
                        'alpha': 255,
                        'scale': 1.0
                    })

    # Animate cards flying off (30 frames = 0.5 seconds)
    for frame in range(30):
        progress = frame / 30.0

        # Animate hyperspace warp ramp-up during card sweep
        if direction == "up" and gpu:
            warp = min(0.6, progress * 0.8)  # Ramp to 0.6 (transition takes it higher)
            _set_effect_uniform(gpu, "hyperspace", "warp_factor", warp)
            _set_effect_uniform(gpu, "hyperspace", "time", gpu.time)

        # Draw dark background
        screen.fill((5, 5, 15))

        # Update and draw each card
        for card_data in card_snapshots:
            if card_data['image'] is None:
                continue

            # Update physics
            card_data['x'] += card_data['vx']
            card_data['y'] += card_data['vy']
            card_data['rotation'] += card_data['rot_speed']
            card_data['alpha'] = max(0, 255 - int(progress * 300))
            card_data['scale'] = max(0.1, 1.0 - progress * 0.5)

            # Accelerate (hyperspace effect)
            if direction == "up":
                card_data['vy'] -= 2  # Accelerate upward

            # Draw card with rotation and alpha
            if card_data['alpha'] > 0:
                scaled_w = int(cfg.CARD_WIDTH * card_data['scale'])
                scaled_h = int(cfg.CARD_HEIGHT * card_data['scale'])
                if scaled_w > 0 and scaled_h > 0:
                    scaled_img = pygame.transform.scale(card_data['image'], (scaled_w, scaled_h))
                    rotated_img = pygame.transform.rotate(scaled_img, card_data['rotation'])
                    rotated_img.set_alpha(card_data['alpha'])
                    rect = rotated_img.get_rect(center=(int(card_data['x']), int(card_data['y'])))
                    screen.blit(rotated_img, rect)

        display_manager.gpu_flip()
        clock.tick(60)

    # Disable hyperspace after card sweep — the hyperspace transition will re-enable it
    if direction == "up" and gpu:
        _set_effect_uniform(gpu, "hyperspace", "warp_factor", 0.0)
        _disable_effect(gpu, "hyperspace")


def create_hyperspace_transition(screen, screen_width, screen_height, round_number, transition_text):
    """
    GPU-enhanced hyperspace transition with persistent star streaks,
    radial motion blur, chromatic aberration, and procedural speed lines.
    """
    clock = pygame.time.Clock()
    transition_font = pygame.font.SysFont("Arial", 80, bold=True)
    gpu = _get_gpu()

    # Configure hyperspace shader direction
    if gpu:
        _enable_effect(gpu, "hyperspace")
        if round_number == 2:
            _set_effect_uniform(gpu, "hyperspace", "direction", 1.0)   # Outward
        else:
            _set_effect_uniform(gpu, "hyperspace", "direction", -1.0)  # Inward
        _set_effect_uniform(gpu, "hyperspace", "center", (0.5, 0.5))

    # Pre-generate persistent star positions (not random each frame!)
    num_stars = 150
    stars = []
    for _ in range(num_stars):
        angle = random.uniform(0, 2 * math.pi)
        base_distance = random.uniform(50, max(screen_width, screen_height) * 0.8)
        speed = random.uniform(8, 20)
        brightness = random.randint(150, 255)
        thickness = random.choice([1, 1, 2, 2, 3])

        stars.append({
            'angle': angle,
            'base_dist': base_distance,
            'speed': speed,
            'brightness': brightness,
            'thickness': thickness,
            'color_tint': random.choice([
                (150, 170, 255), (180, 190, 255), (200, 210, 255),
                (220, 230, 255), (255, 255, 255)
            ])
        })

    center_x, center_y = screen_width // 2, screen_height // 2

    # Animation duration: 90 frames (1.5 seconds)
    total_frames = 90

    # Pre-allocate per-frame scratch surfaces — these were being created fresh
    # each iteration of the inner ring loop (5 rings × 90 frames = 450 allocs/transition).
    ring_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    if round_number == 3:
        _planet_radius = int(screen_height * 0.18)
        planet_surf = pygame.Surface(
            (_planet_radius * 2 + 40, _planet_radius * 2 + 40),
            pygame.SRCALPHA,
        )
    else:
        planet_surf = None
        _planet_radius = 0

    for frame in range(total_frames):
        progress = frame / total_frames

        # --- Animate GPU hyperspace shader ---
        if gpu:
            if round_number == 2:
                # Entering hyperspace: ramp up fast, sustain, then slight ease at end
                if progress < 0.3:
                    warp = progress / 0.3  # 0→1 over first 30%
                else:
                    warp = 1.0  # Sustain full warp
            else:
                # Emerging from hyperspace: start full, decelerate to stop
                if progress < 0.7:
                    warp = 1.0 - (progress / 0.7) * 0.7  # 1.0→0.3 over 70%
                else:
                    warp = 0.3 * (1.0 - (progress - 0.7) / 0.3)  # 0.3→0 final 30%
            _set_effect_uniform(gpu, "hyperspace", "warp_factor", max(0.0, warp))
            _set_effect_uniform(gpu, "hyperspace", "time", gpu.time)

        # Dark space background with slight blue tint
        screen.fill((2, 2, 12))

        # Draw radial blur / whoosh rings (CPU, enhanced by GPU shader).
        # All rings share one scratch surface — fill once, draw, blit once.
        if round_number == 2 or round_number == 3:
            ring_surf.fill((0, 0, 0, 0))
            ring_drawn = False
            for ring_idx in range(5):
                if round_number == 2:
                    ring_progress = (progress + ring_idx * 0.15) % 1.0
                    ring_alpha = int((1 - ring_progress) * 80)
                else:  # round_number == 3
                    ring_progress = (1 - progress + ring_idx * 0.15) % 1.0
                    ring_alpha = int(ring_progress * 60)
                ring_radius = int(ring_progress * max(screen_width, screen_height))
                if ring_alpha > 0 and ring_radius > 0:
                    pygame.draw.circle(ring_surf, (100, 150, 255, ring_alpha),
                                       (center_x, center_y), ring_radius, width=3)
                    ring_drawn = True
            if ring_drawn:
                screen.blit(ring_surf, (0, 0))

        # Draw persistent star streaks
        for star in stars:
            if round_number == 2:
                streak_length = 20 + progress * 400
                current_dist = star['base_dist'] * (0.3 + progress * 1.5)
                start_dist = max(0, current_dist - streak_length * 0.3)
                end_dist = current_dist + streak_length * 0.7

                start_x = center_x + math.cos(star['angle']) * start_dist
                start_y = center_y + math.sin(star['angle']) * start_dist
                end_x = center_x + math.cos(star['angle']) * end_dist
                end_y = center_y + math.sin(star['angle']) * end_dist

            else:  # round_number == 3
                streak_length = 400 * (1 - progress) + 20
                current_dist = star['base_dist'] * (1.5 - progress * 1.2)
                start_dist = current_dist + streak_length * 0.7
                end_dist = max(0, current_dist - streak_length * 0.3)

                start_x = center_x + math.cos(star['angle']) * start_dist
                start_y = center_y + math.sin(star['angle']) * start_dist
                end_x = center_x + math.cos(star['angle']) * end_dist
                end_y = center_y + math.sin(star['angle']) * end_dist

            # Draw the star streak
            color = star['color_tint']

            # Main streak
            pygame.draw.line(screen, color, (int(start_x), int(start_y)),
                           (int(end_x), int(end_y)), star['thickness'])

            # Bright head of streak
            if round_number == 2:
                head_x, head_y = end_x, end_y
            else:
                head_x, head_y = start_x, start_y
            pygame.draw.circle(screen, (255, 255, 255), (int(head_x), int(head_y)), star['thickness'] + 1)

        # Planet appearing (round 3 only, in second half) — reuses the
        # pre-allocated planet_surf from above; cleared each frame.
        if round_number == 3 and progress > 0.5 and planet_surf is not None:
            planet_progress = (progress - 0.5) * 2
            planet_alpha = int(planet_progress * 200)
            planet_radius = _planet_radius

            planet_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(planet_surf, (60, 100, 180, planet_alpha // 3),
                             (planet_radius + 20, planet_radius + 20), planet_radius + 15)
            pygame.draw.circle(planet_surf, (40, 80, 160, planet_alpha),
                             (planet_radius + 20, planet_radius + 20), planet_radius)
            pygame.draw.circle(planet_surf, (80, 120, 200, planet_alpha),
                             (planet_radius + 10, planet_radius + 10), planet_radius // 2)

            screen.blit(planet_surf, (center_x - planet_radius - 20, 80))

        # Transition text with glow effect
        text_alpha = int(255 * min(1, progress * 3) * min(1, (1 - progress) * 3))

        # Text glow
        glow_surf = transition_font.render(transition_text, True, (50, 100, 200))
        glow_surf.set_alpha(text_alpha // 2)
        for offset in [(-3, -3), (3, -3), (-3, 3), (3, 3)]:
            glow_rect = glow_surf.get_rect(center=(center_x + offset[0], center_y + offset[1]))
            screen.blit(glow_surf, glow_rect)

        # Main text
        text_surf = transition_font.render(transition_text, True, (150, 200, 255))
        text_surf.set_alpha(text_alpha)
        text_rect = text_surf.get_rect(center=(center_x, center_y))
        screen.blit(text_surf, text_rect)

        display_manager.gpu_flip()
        clock.tick(60)

    # Clean up: disable hyperspace shader and reset warp
    if gpu:
        _set_effect_uniform(gpu, "hyperspace", "warp_factor", 0.0)
        _disable_effect(gpu, "hyperspace")


def _draw_stargate_chevrons(surface, rect, color, alpha, num_chevrons=9):
    """Draw Stargate-style chevron decorations around a rectangle."""
    chevron_surf = pygame.Surface((rect.width + 40, rect.height + 40), pygame.SRCALPHA)

    # Chevron positions (top, sides)
    chevron_size = 12

    # Top chevrons
    top_positions = [rect.width * 0.2, rect.width * 0.5, rect.width * 0.8]
    for x_pos in top_positions:
        cx = int(x_pos) + 20
        cy = 8
        # Draw chevron shape (inverted V with glow)
        points = [(cx - chevron_size, cy + chevron_size),
                  (cx, cy),
                  (cx + chevron_size, cy + chevron_size)]
        pygame.draw.polygon(chevron_surf, (*color, alpha), points)
        pygame.draw.polygon(chevron_surf, (255, 255, 255, alpha // 2), points, 2)

    # Bottom chevrons
    for x_pos in top_positions:
        cx = int(x_pos) + 20
        cy = rect.height + 32
        points = [(cx - chevron_size, cy - chevron_size),
                  (cx, cy),
                  (cx + chevron_size, cy - chevron_size)]
        pygame.draw.polygon(chevron_surf, (*color, alpha), points)
        pygame.draw.polygon(chevron_surf, (255, 255, 255, alpha // 2), points, 2)

    # Side chevrons (left and right)
    side_y_positions = [rect.height * 0.3, rect.height * 0.7]
    for y_pos in side_y_positions:
        # Left side
        cy = int(y_pos) + 20
        cx = 8
        points = [(cx + chevron_size, cy - chevron_size),
                  (cx, cy),
                  (cx + chevron_size, cy + chevron_size)]
        pygame.draw.polygon(chevron_surf, (*color, alpha), points)

        # Right side
        cx = rect.width + 32
        points = [(cx - chevron_size, cy - chevron_size),
                  (cx, cy),
                  (cx - chevron_size, cy + chevron_size)]
        pygame.draw.polygon(chevron_surf, (*color, alpha), points)

    surface.blit(chevron_surf, (rect.x - 20, rect.y - 20))


def show_round_winner_announcement(screen, game, screen_width, screen_height):
    """Show cinematic announcement of who won the round with detailed scoreboard,
    screen shake, and GPU shockwave effect."""
    scale = display_manager.SCALE_FACTOR
    gpu = _get_gpu()

    # Enable shockwave GPU effect for the impact moment
    if gpu:
        _enable_effect(gpu, "shockwave")
        _set_effect_uniform(gpu, "shockwave", "center", (0.5, 0.5))

    # Get the round that just completed
    completed_round = game.round_number - 1

    # Determine winner text and shockwave ring color
    if game.round_winner == game.player1:
        winner_text = f"{game.player1.name.upper()} WINS ROUND {completed_round}!"
        winner_color = (100, 255, 100)
        accent_color = (50, 200, 50)
        if gpu:
            _set_effect_uniform(gpu, "shockwave", "ring_color", (0.3, 1.0, 0.4))  # Green
    elif game.round_winner == game.player2:
        winner_text = f"{game.player2.name.upper()} WINS ROUND {completed_round}!"
        winner_color = (255, 100, 100)
        accent_color = (200, 50, 50)
        if gpu:
            _set_effect_uniform(gpu, "shockwave", "ring_color", (1.0, 0.3, 0.3))  # Red
    else:
        winner_text = f"ROUND {completed_round} DRAW!"
        winner_color = (255, 255, 100)
        accent_color = (200, 200, 50)
        if gpu:
            _set_effect_uniform(gpu, "shockwave", "ring_color", (1.0, 1.0, 0.4))  # Yellow

    # Get round history (who won each round so far)
    p1_rounds = game.player1.rounds_won
    p2_rounds = game.player2.rounds_won
    total_rounds_played = completed_round

    # Scaled font sizes
    title_size = max(48, int(72 * scale))
    name_size = max(28, int(36 * scale))
    header_size = max(22, int(26 * scale))
    score_size = max(32, int(40 * scale))
    label_size = max(24, int(28 * scale))

    # Fonts
    title_font = pygame.font.SysFont("Arial", title_size, bold=True)
    name_font = pygame.font.SysFont("Arial", name_size, bold=True)
    header_font = pygame.font.SysFont("Arial", header_size, bold=True)
    score_font = pygame.font.SysFont("Arial", score_size, bold=True)
    label_font = pygame.font.SysFont("Arial", label_size)

    clock = pygame.time.Clock()
    duration = 3000  # 3 seconds
    start_time = pygame.time.get_ticks()

    # Screen shake parameters
    shake_intensity = 15  # Initial shake intensity
    shake_decay = 0.92  # How fast shake decays
    current_shake = shake_intensity

    # Create a render surface for shake effect
    render_surface = pygame.Surface((screen_width, screen_height))

    # Calculate dynamic scoreboard dimensions
    board_width = min(800, int(screen_width * 0.6))
    board_height = min(380, int(screen_height * 0.4))

    # Pre-allocate per-frame scratch surfaces (sizes are stable for the
    # whole transition). Avoids ~3-4 SRCALPHA allocations per frame at 60fps.
    _overlay_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    _overlay_surf.fill((0, 0, 0, 200))  # static fill — never re-filled
    _flash_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    _board_surf = pygame.Surface((board_width, board_height), pygame.SRCALPHA)
    _line_w = max(1, board_width - int(40 * scale))
    _line_surf = pygame.Surface((_line_w, 2), pygame.SRCALPHA)

    # Column positions as percentages of board width
    name_col_width = int(board_width * 0.35)  # 35% for names
    round_col_width = int(board_width * 0.12)  # 12% each for R1, R2, R3
    total_col_width = int(board_width * 0.16)  # 16% for total

    def _cleanup_shockwave():
        if gpu:
            _set_effect_uniform(gpu, "shockwave", "distort_strength", 0.0)
            _set_effect_uniform(gpu, "shockwave", "flash_intensity", 0.0)
            _disable_effect(gpu, "shockwave")

    while pygame.time.get_ticks() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _cleanup_shockwave()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    _cleanup_shockwave()
                    return  # Skip animation

        elapsed = pygame.time.get_ticks() - start_time
        progress = elapsed / duration

        # Animate GPU shockwave effect — expands during first 40% of animation
        if gpu:
            if progress < 0.4:
                shock_progress = progress / 0.4  # 0→1 over first 40%
                ring_r = shock_progress * 1.2  # Ring expands past screen edges
                distort = max(0.0, 0.04 * (1.0 - shock_progress))  # Strong then fades
                flash = max(0.0, 0.3 * (1.0 - shock_progress * 3))  # Quick flash
                _set_effect_uniform(gpu, "shockwave", "ring_radius", ring_r)
                _set_effect_uniform(gpu, "shockwave", "distort_strength", distort)
                _set_effect_uniform(gpu, "shockwave", "flash_intensity", flash)
                _set_effect_uniform(gpu, "shockwave", "time", gpu.time)
            else:
                # Shockwave done — zero out
                _set_effect_uniform(gpu, "shockwave", "distort_strength", 0.0)
                _set_effect_uniform(gpu, "shockwave", "flash_intensity", 0.0)

        # Calculate screen shake offset (strongest at start, decays over time)
        if progress < 0.3:
            shake_offset_x = random.uniform(-current_shake, current_shake)
            shake_offset_y = random.uniform(-current_shake, current_shake)
            current_shake *= shake_decay
        else:
            shake_offset_x = 0
            shake_offset_y = 0

        # Render to intermediate surface
        render_surface.fill((5, 5, 20))  # Dark space blue

        # Dark overlay with gradient (reuse pre-allocated surface)
        render_surface.blit(_overlay_surf, (0, 0))

        center_x = screen_width // 2
        center_y = screen_height // 2

        # Impact flash effect (at very start) — reuse _flash_surf
        if progress < 0.1:
            flash_alpha = int((1 - progress / 0.1) * 150)
            _flash_surf.fill((*winner_color[:3], flash_alpha))
            render_surface.blit(_flash_surf, (0, 0))

        # Main winner text - slide in from top with slam effect
        if progress < 0.15:
            slam_progress = progress / 0.15
            text_y_offset = int((1 - slam_progress) * -200)
            text_scale = 1.0 + (1 - slam_progress) * 0.3
        else:
            text_y_offset = 0
            text_scale = 1.0

        text_alpha = min(255, int(255 * progress * 3))

        # Render winner text with glow effect
        if text_scale != 1.0:
            scaled_font = pygame.font.SysFont("Arial", int(title_size * text_scale), bold=True)
            winner_surface = scaled_font.render(winner_text, True, winner_color)
        else:
            winner_surface = title_font.render(winner_text, True, winner_color)

        # Glow behind text
        glow_surf = title_font.render(winner_text, True, accent_color)
        glow_surf.set_alpha(text_alpha // 3)
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, -4), (0, 4)]:
            glow_rect = glow_surf.get_rect(center=(center_x + dx, int(100 * scale) + text_y_offset + dy))
            render_surface.blit(glow_surf, glow_rect)

        winner_surface.set_alpha(text_alpha)
        winner_rect = winner_surface.get_rect(center=(center_x, int(100 * scale) + text_y_offset))
        render_surface.blit(winner_surface, winner_rect)

        # Stargate-themed decorative line under title
        if progress > 0.2:
            line_alpha = min(255, int(255 * (progress - 0.2) * 3))
            line_width = int(400 * scale)
            line_y = int(140 * scale) + text_y_offset

            # Main line
            pygame.draw.line(render_surface, (*accent_color, line_alpha),
                           (center_x - line_width // 2, line_y),
                           (center_x + line_width // 2, line_y), 3)

            # End decorations (diamond shapes)
            for side in [-1, 1]:
                dx = side * (line_width // 2 + 10)
                diamond_points = [
                    (center_x + dx, line_y - 8),
                    (center_x + dx + 8 * side, line_y),
                    (center_x + dx, line_y + 8),
                    (center_x + dx - 8 * side, line_y)
                ]
                pygame.draw.polygon(render_surface, winner_color, diamond_points)

        # Scoreboard - fade in after title
        if progress > 0.3:
            board_alpha = min(255, int(255 * (progress - 0.3) * 2.5))

            board_x = center_x - board_width // 2
            board_y = center_y - int(30 * scale)

            # Create scoreboard with styled border (reuse _board_surf,
            # clear before redrawing as set_alpha persists across frames).
            board_surf = _board_surf
            board_surf.fill((0, 0, 0, 0))

            # Background gradient
            for y in range(board_height):
                ratio = y / board_height
                r = int(15 + 15 * ratio)
                g = int(25 + 15 * ratio)
                b = int(45 + 20 * ratio)
                pygame.draw.line(board_surf, (r, g, b, 240), (0, y), (board_width, y))

            # Border with corner accents
            pygame.draw.rect(board_surf, (100, 150, 200), board_surf.get_rect(), width=3, border_radius=12)

            # Inner glow line
            inner_rect = pygame.Rect(4, 4, board_width - 8, board_height - 8)
            pygame.draw.rect(board_surf, (50, 80, 120, 150), inner_rect, width=1, border_radius=10)

            board_surf.set_alpha(board_alpha)
            render_surface.blit(board_surf, (board_x, board_y))

            # Draw chevron decorations
            board_rect = pygame.Rect(board_x, board_y, board_width, board_height)
            _draw_stargate_chevrons(render_surface, board_rect, accent_color, board_alpha)

            # Draw scoreboard content
            y_offset = board_y + int(25 * scale)

            # Title with Stargate styling
            title_text = "- BATTLE STATUS -"
            scoreboard_title = label_font.render(title_text, True, (150, 200, 255))
            scoreboard_title.set_alpha(board_alpha)
            title_rect = scoreboard_title.get_rect(center=(center_x, y_offset))
            render_surface.blit(scoreboard_title, title_rect)

            y_offset += int(50 * scale)

            # Column headers - properly spaced
            col_x_start = board_x + int(20 * scale)
            round_start_x = col_x_start + name_col_width

            headers = [("COMMANDER", col_x_start),
                      ("R1", round_start_x),
                      ("R2", round_start_x + round_col_width),
                      ("R3", round_start_x + round_col_width * 2),
                      ("WINS", round_start_x + round_col_width * 3)]

            for header_text, x_pos in headers:
                header_surf = header_font.render(header_text, True, (180, 200, 220))
                header_surf.set_alpha(board_alpha)
                if header_text == "COMMANDER":
                    render_surface.blit(header_surf, (x_pos, y_offset))
                else:
                    # Center round headers
                    header_rect = header_surf.get_rect(center=(x_pos + round_col_width // 2, y_offset + header_surf.get_height() // 2))
                    render_surface.blit(header_surf, header_rect)

            y_offset += int(40 * scale)

            # Draw separator line with glow (reuse pre-allocated _line_surf)
            _line_surf.fill((100, 150, 200, board_alpha))
            render_surface.blit(_line_surf, (board_x + int(20 * scale), y_offset))

            y_offset += int(20 * scale)

            # Player 1 row
            p1_display = game.player1.name[:15] if len(game.player1.name) > 15 else game.player1.name
            p1_name = name_font.render(p1_display.upper(), True, (100, 255, 100))
            p1_name.set_alpha(board_alpha)
            render_surface.blit(p1_name, (col_x_start, y_offset))

            # Round scores for Player 1
            row_center_y = y_offset + int(20 * scale)
            for round_num in range(1, 4):
                round_x = round_start_x + (round_num - 1) * round_col_width + round_col_width // 2

                if round_num <= completed_round:
                    won_round = False
                    if round_num == completed_round and game.round_winner == game.player1:
                        won_round = True
                    elif round_num < completed_round:
                        won_round = (round_num <= p1_rounds)

                    if won_round:
                        # Glowing win indicator
                        pygame.draw.circle(render_surface, (50, 100, 200, board_alpha // 2),
                                         (round_x, row_center_y), int(18 * scale))
                        round_color = (100, 200, 255)
                        round_text = "W"
                    else:
                        round_color = (120, 120, 120)
                        round_text = "-"
                else:
                    round_color = (60, 60, 60)
                    round_text = "."

                round_score = score_font.render(round_text, True, round_color)
                round_score.set_alpha(board_alpha)
                score_rect = round_score.get_rect(center=(round_x, row_center_y))
                render_surface.blit(round_score, score_rect)

            # Total for Player 1
            total_x = round_start_x + round_col_width * 3 + round_col_width // 2
            p1_total = score_font.render(str(game.player1.rounds_won), True, (255, 215, 0))
            p1_total.set_alpha(board_alpha)
            total_rect = p1_total.get_rect(center=(total_x, row_center_y))
            render_surface.blit(p1_total, total_rect)

            y_offset += int(60 * scale)

            # Player 2 row
            p2_display = game.player2.name[:15] if len(game.player2.name) > 15 else game.player2.name
            p2_name = name_font.render(p2_display.upper(), True, (255, 100, 100))
            p2_name.set_alpha(board_alpha)
            render_surface.blit(p2_name, (col_x_start, y_offset))

            # Round scores for Player 2
            row_center_y = y_offset + int(20 * scale)
            for round_num in range(1, 4):
                round_x = round_start_x + (round_num - 1) * round_col_width + round_col_width // 2

                if round_num <= completed_round:
                    won_round = False
                    if round_num == completed_round and game.round_winner == game.player2:
                        won_round = True
                    elif round_num < completed_round:
                        won_round = (round_num <= p2_rounds)

                    if won_round:
                        pygame.draw.circle(render_surface, (50, 100, 200, board_alpha // 2),
                                         (round_x, row_center_y), int(18 * scale))
                        round_color = (100, 200, 255)
                        round_text = "W"
                    else:
                        round_color = (120, 120, 120)
                        round_text = "-"
                else:
                    round_color = (60, 60, 60)
                    round_text = "."

                round_score = score_font.render(round_text, True, round_color)
                round_score.set_alpha(board_alpha)
                score_rect = round_score.get_rect(center=(round_x, row_center_y))
                render_surface.blit(round_score, score_rect)

            # Total for Player 2
            p2_total = score_font.render(str(game.player2.rounds_won), True, (255, 215, 0))
            p2_total.set_alpha(board_alpha)
            total_rect = p2_total.get_rect(center=(total_x, row_center_y))
            render_surface.blit(p2_total, total_rect)

        # Skip instruction with pulsing effect
        if progress > 0.4:
            pulse = 0.7 + 0.3 * math.sin(elapsed * 0.005)
            skip_alpha = int(text_alpha * pulse)
            skip_font = pygame.font.SysFont("Arial", max(20, int(24 * scale)))
            skip_text = skip_font.render("[ PRESS SPACE TO CONTINUE ]", True, (150, 180, 200))
            skip_text.set_alpha(skip_alpha)
            skip_rect = skip_text.get_rect(center=(center_x, screen_height - int(60 * scale)))
            render_surface.blit(skip_text, skip_rect)

        # Apply screen shake by blitting render_surface with offset
        screen.blit(render_surface, (int(shake_offset_x), int(shake_offset_y)))

        display_manager.gpu_flip()
        clock.tick(60)

    # Clean up: disable shockwave effect
    _cleanup_shockwave()

def show_game_start_animation(screen, game, screen_width, screen_height):
    """Show Stargate activation animation announcing who goes first,
    with GPU shockwave pulse effect."""
    gpu = _get_gpu()

    # Enable shockwave for a subtle pulse at game start
    if gpu:
        _enable_effect(gpu, "shockwave")
        _set_effect_uniform(gpu, "shockwave", "center", (0.5, 0.5))

    # Determine who goes first
    if game.current_player == game.player1:
        first_player_text = "YOU GO FIRST"
        color = (100, 255, 100)
    else:
        first_player_text = "OPPONENT GOES FIRST"
        color = (255, 100, 100)

    # Font
    title_font = pygame.font.SysFont("Arial", 72, bold=True)
    subtitle_font = pygame.font.SysFont("Arial", 36)

    clock = pygame.time.Clock()

    # Animation phases
    duration = 2500  # 2.5 seconds
    start_time = pygame.time.get_ticks()

    while pygame.time.get_ticks() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                _disable_effect(gpu, "shockwave") if gpu else None
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    _disable_effect(gpu, "shockwave") if gpu else None
                    return  # Skip animation

        elapsed = pygame.time.get_ticks() - start_time
        progress = elapsed / duration

        # Animate shockwave — single expanding pulse in first 30%
        if gpu:
            if progress < 0.3:
                sp = progress / 0.3
                _set_effect_uniform(gpu, "shockwave", "ring_radius", sp * 1.0)
                _set_effect_uniform(gpu, "shockwave", "distort_strength",
                                    max(0.0, 0.025 * (1.0 - sp)))
                _set_effect_uniform(gpu, "shockwave", "flash_intensity",
                                    max(0.0, 0.15 * (1.0 - sp * 2)))
            else:
                _set_effect_uniform(gpu, "shockwave", "distort_strength", 0.0)
                _set_effect_uniform(gpu, "shockwave", "flash_intensity", 0.0)
        
        # Dark semi-transparent overlay
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        
        # Pulsing circle effect (Stargate-like)
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Multiple expanding circles
        for i in range(3):
            phase_offset = i * 0.3
            circle_progress = (progress + phase_offset) % 1.0
            radius = int(50 + circle_progress * 200)
            alpha = int(255 * (1 - circle_progress))
            
            if alpha > 0:
                circle_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(circle_surface, (100, 150, 255, alpha), (radius, radius), radius, width=3)
                screen.blit(circle_surface, (center_x - radius, center_y - radius))
        
        # Central glow
        glow_alpha = int(128 + 127 * abs(0.5 - progress))
        pygame.draw.circle(screen, (100, 150, 255), (center_x, center_y), 40)
        
        # Text fade in
        text_alpha = min(255, int(255 * progress * 2))
        
        # Main text
        text_surface = title_font.render(first_player_text, True, color)
        text_surface.set_alpha(text_alpha)
        text_rect = text_surface.get_rect(center=(center_x, center_y - 100))
        screen.blit(text_surface, text_rect)
        
        # Subtitle
        if progress > 0.3:
            subtitle = subtitle_font.render("Prepare your strategy...", True, (200, 200, 200))
            subtitle.set_alpha(text_alpha)
            subtitle_rect = subtitle.get_rect(center=(center_x, center_y + 100))
            screen.blit(subtitle, subtitle_rect)
        
        # Skip instruction
        if progress > 0.5:
            skip_font = pygame.font.SysFont("Arial", 20)
            skip_text = skip_font.render("Press SPACE to skip", True, (150, 150, 150))
            skip_text.set_alpha(text_alpha)
            skip_rect = skip_text.get_rect(center=(center_x, screen_height - 50))
            screen.blit(skip_text, skip_rect)

        display_manager.gpu_flip()
        clock.tick(60)

    # Clean up shockwave
    if gpu:
        _set_effect_uniform(gpu, "shockwave", "distort_strength", 0.0)
        _set_effect_uniform(gpu, "shockwave", "flash_intensity", 0.0)
        _disable_effect(gpu, "shockwave")


class GameOverAnimation:
    """
    Displays game over animation with winner and loser leader cards.
    Winner stands upright with golden glow, loser topples over.
    High-quality rendering with proper scaling support and Stargate theming.
    """

    # Base dimensions at 2560x1440 (will be scaled)
    BASE_CARD_WIDTH = 180
    BASE_CARD_HEIGHT = 270
    DURATION = 4.0  # 4 seconds total
    TOPPLE_START = 0.3  # Topple starts at 30% progress
    TOPPLE_END = 0.8    # Topple completes at 80%

    def __init__(self, game, screen_width, screen_height):
        self.game = game
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.start_time = None
        self.finished = False

        # Get scale factor for proper sizing
        self.scale = display_manager.SCALE_FACTOR

        # Calculate scaled dimensions
        self.card_width = int(self.BASE_CARD_WIDTH * self.scale)
        self.card_height = int(self.BASE_CARD_HEIGHT * self.scale)

        # Determine winner and loser
        self.winner = game.winner
        self.loser = game.player2 if game.winner == game.player1 else game.player1

        # Determine if player won (for "MISSION COMPLETE" vs "MISSION FAILED")
        self.player_won = game.winner == game.player1

        # Load leader images at high resolution then scale down for quality
        self.winner_image = self._load_leader_image(self.winner)
        self.loser_image = self._load_leader_image(self.loser)
        # Keep a pristine copy for rotation (avoids cumulative quality loss)
        self.loser_image_original = self.loser_image.copy() if self.loser_image else None

        # Card positions (winner left, loser right) - centered vertically with offset
        center_y = int(screen_height * 0.45)  # Centered better
        spacing = int(220 * self.scale)  # More spacing between cards
        self.winner_pos = (screen_width // 2 - spacing - self.card_width // 2, center_y - self.card_height // 2)
        self.loser_pos = (screen_width // 2 + spacing - self.card_width // 2, center_y - self.card_height // 2)

        # Scaled fonts with minimum sizes for readability
        self.title_font = pygame.font.SysFont("Arial", max(36, int(56 * self.scale)), bold=True)
        self.name_font = pygame.font.SysFont("Arial", max(18, int(24 * self.scale)), bold=True)
        self.label_font = pygame.font.SysFont("Arial", max(16, int(20 * self.scale)), bold=True)
        self.hint_font = pygame.font.SysFont("Arial", max(14, int(18 * self.scale)))

        # Pre-calculate scaled values for drawing
        self.border_width = max(3, int(5 * self.scale))
        self.glow_base_radius = int(25 * self.scale)
        self.border_radius = max(6, int(10 * self.scale))
        self.name_offset_y = int(40 * self.scale)  # More space below cards
        self.label_offset_y = int(35 * self.scale)  # More space above cards
        self.drift_max = int(40 * self.scale)

        # Panel dimensions for background
        self.panel_width = int(self.card_width * 2 + spacing * 2 + 100 * self.scale)
        self.panel_height = int(self.card_height + 180 * self.scale)

    def _load_leader_image(self, player):
        """Load leader image for a player at high quality, with fallbacks."""
        if not player or not player.leader:
            return self._create_fallback_image(player)

        leader_card_id = player.leader.get('card_id')

        if leader_card_id:
            # Try loading the _leader.png variant first (higher quality portrait)
            leader_image_path = os.path.join("assets", f"{leader_card_id}_leader.png")
            if os.path.exists(leader_image_path):
                try:
                    # Load at full resolution
                    original = pygame.image.load(leader_image_path).convert_alpha()
                    # Use smoothscale for high-quality downscaling
                    return pygame.transform.smoothscale(original, (self.card_width, self.card_height))
                except Exception:
                    pass

            # Fallback to regular card image
            from cards import ALL_CARDS
            if leader_card_id in ALL_CARDS:
                leader_card = ALL_CARDS[leader_card_id]
                if hasattr(leader_card, 'image_path') and os.path.exists(leader_card.image_path):
                    try:
                        original = pygame.image.load(leader_card.image_path).convert_alpha()
                        return pygame.transform.smoothscale(original, (self.card_width, self.card_height))
                    except Exception:
                        pass
                if leader_card.image:
                    return pygame.transform.smoothscale(leader_card.image, (self.card_width, self.card_height))

        return self._create_fallback_image(player)

    def _create_fallback_image(self, player):
        """Create a fallback colored rectangle with gradient if no image available."""
        surface = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)

        # Determine color based on faction
        if player and player.faction == "Tau'ri":
            base_color = (40, 80, 120)
            highlight = (60, 120, 180)
        elif player and player.faction == "Goa'uld":
            base_color = (120, 80, 40)
            highlight = (180, 120, 60)
        else:
            base_color = (80, 80, 80)
            highlight = (120, 120, 120)

        # Draw gradient background
        for y in range(self.card_height):
            ratio = y / self.card_height
            r = int(base_color[0] + (highlight[0] - base_color[0]) * ratio * 0.5)
            g = int(base_color[1] + (highlight[1] - base_color[1]) * ratio * 0.5)
            b = int(base_color[2] + (highlight[2] - base_color[2]) * ratio * 0.5)
            pygame.draw.line(surface, (r, g, b, 255), (0, y), (self.card_width, y))

        # Draw border
        pygame.draw.rect(surface, (180, 180, 180), surface.get_rect(), max(2, int(3 * self.scale)), border_radius=self.border_radius)
        return surface

    def _ease_in_cubic(self, t):
        """Ease-in cubic function for acceleration."""
        return t * t * t

    def update(self):
        """Update animation state. Returns True if animation is complete."""
        if self.start_time is None:
            self.start_time = pygame.time.get_ticks()

        elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0
        if elapsed >= self.DURATION:
            self.finished = True

        return self.finished

    def _draw_panel_background(self, screen, progress):
        """Draw Stargate-themed panel background."""
        panel_x = (self.screen_width - self.panel_width) // 2
        panel_y = (self.screen_height - self.panel_height) // 2 - int(30 * self.scale)

        # Fade in panel
        panel_alpha = min(220, int(220 * progress * 2))

        # Create panel surface
        panel = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)

        # Gradient background (dark blue to darker)
        for y in range(self.panel_height):
            ratio = y / self.panel_height
            r = int(10 + 10 * (1 - ratio))
            g = int(20 + 15 * (1 - ratio))
            b = int(40 + 25 * (1 - ratio))
            pygame.draw.line(panel, (r, g, b, panel_alpha), (0, y), (self.panel_width, y))

        # Main border
        border_color = (100, 180, 255) if self.player_won else (255, 100, 100)
        pygame.draw.rect(panel, (*border_color, panel_alpha), panel.get_rect(), width=4, border_radius=15)

        # Inner border glow
        inner_rect = pygame.Rect(6, 6, self.panel_width - 12, self.panel_height - 12)
        pygame.draw.rect(panel, (*border_color, panel_alpha // 3), inner_rect, width=2, border_radius=12)

        # Corner decorations (Stargate-like)
        corner_size = int(25 * self.scale)
        corners = [
            (0, 0),  # Top-left
            (self.panel_width - corner_size, 0),  # Top-right
            (0, self.panel_height - corner_size),  # Bottom-left
            (self.panel_width - corner_size, self.panel_height - corner_size)  # Bottom-right
        ]

        for cx, cy in corners:
            # L-shaped corner accent
            pygame.draw.line(panel, (*border_color, panel_alpha),
                           (cx + (corner_size if cx == 0 else 0), cy + 8),
                           (cx + (0 if cx == 0 else corner_size), cy + 8), 3)
            pygame.draw.line(panel, (*border_color, panel_alpha),
                           (cx + 8, cy + (corner_size if cy == 0 else 0)),
                           (cx + 8, cy + (0 if cy == 0 else corner_size)), 3)

        screen.blit(panel, (panel_x, panel_y))
        return panel_x, panel_y

    def draw(self, screen):
        """Draw the game over animation with high-quality rendering and Stargate theming."""
        if self.start_time is None:
            self.start_time = pygame.time.get_ticks()
            print(f"[DEBUG GameOverAnimation] Started: winner={self.winner.name if self.winner else 'None'}, loser={self.loser.name if self.loser else 'None'}")
            print(f"[DEBUG GameOverAnimation] winner_image={self.winner_image is not None}, loser_image={self.loser_image_original is not None}")

        elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0
        progress = min(1.0, elapsed / self.DURATION)

        # Calculate topple progress (0 to 1 within the topple window)
        if progress < self.TOPPLE_START:
            topple_progress = 0.0
        elif progress > self.TOPPLE_END:
            topple_progress = 1.0
        else:
            raw_progress = (progress - self.TOPPLE_START) / (self.TOPPLE_END - self.TOPPLE_START)
            topple_progress = self._ease_in_cubic(raw_progress)

        # Draw themed panel background
        panel_x, panel_y = self._draw_panel_background(screen, progress)

        # --- Draw Title at top of panel ---
        title_y = panel_y + int(25 * self.scale)

        if self.player_won:
            title_text = "MISSION COMPLETE"
            title_color = (100, 255, 150)
            glow_color = (50, 200, 100)
        else:
            title_text = "MISSION FAILED"
            title_color = (255, 100, 100)
            glow_color = (200, 50, 50)

        # Title with glow effect
        title_alpha = min(255, int(255 * progress * 2))

        # Glow
        glow_surf = self.title_font.render(title_text, True, glow_color)
        glow_surf.set_alpha(title_alpha // 3)
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            glow_rect = glow_surf.get_rect(center=(self.screen_width // 2 + dx, title_y + dy))
            screen.blit(glow_surf, glow_rect)

        # Main title
        title_surf = self.title_font.render(title_text, True, title_color)
        title_surf.set_alpha(title_alpha)
        title_rect = title_surf.get_rect(center=(self.screen_width // 2, title_y))
        screen.blit(title_surf, title_rect)

        # Decorative line under title
        if progress > 0.1:
            line_alpha = min(200, int(200 * (progress - 0.1) * 3))
            line_width = int(300 * self.scale)
            line_y = title_y + int(35 * self.scale)

            pygame.draw.line(screen, (*glow_color, line_alpha),
                           (self.screen_width // 2 - line_width // 2, line_y),
                           (self.screen_width // 2 + line_width // 2, line_y), 2)

        # --- Draw Winner Card (left side, upright with golden glow) ---
        winner_x, winner_y = self.winner_pos

        # Golden glow effect (pulsing) - multi-layered for smooth appearance
        glow_intensity = 0.7 + 0.3 * math.sin(elapsed * 3)
        for i in range(3):
            layer_radius = int(self.glow_base_radius * glow_intensity * (1 + i * 0.5))
            glow_surface = pygame.Surface(
                (self.card_width + layer_radius * 2, self.card_height + layer_radius * 2),
                pygame.SRCALPHA
            )
            glow_alpha = int(60 * glow_intensity / (i + 1))
            pygame.draw.rect(
                glow_surface,
                (255, 215, 0, glow_alpha),
                (layer_radius // 2, layer_radius // 2, self.card_width + layer_radius, self.card_height + layer_radius),
                border_radius=self.border_radius + i * 2
            )
            screen.blit(glow_surface, (winner_x - layer_radius, winner_y - layer_radius))

        # Winner card
        if self.winner_image:
            screen.blit(self.winner_image, (winner_x, winner_y))

        # Golden border for winner (crisp)
        pygame.draw.rect(
            screen,
            (255, 215, 0),
            (winner_x - self.border_width, winner_y - self.border_width,
             self.card_width + self.border_width * 2, self.card_height + self.border_width * 2),
            self.border_width,
            border_radius=self.border_radius
        )

        # "VICTOR" label above card with background for visibility
        victor_y = winner_y - self.label_offset_y
        victor_surf = self.label_font.render("VICTOR", True, (100, 255, 100))

        # Small background behind label
        label_bg = pygame.Surface((victor_surf.get_width() + 16, victor_surf.get_height() + 8), pygame.SRCALPHA)
        label_bg.fill((0, 0, 0, 150))
        pygame.draw.rect(label_bg, (100, 255, 100, 200), label_bg.get_rect(), width=1, border_radius=4)
        label_bg_rect = label_bg.get_rect(center=(winner_x + self.card_width // 2, victor_y))
        screen.blit(label_bg, label_bg_rect)

        victor_rect = victor_surf.get_rect(center=(winner_x + self.card_width // 2, victor_y))
        screen.blit(victor_surf, victor_rect)

        # Winner name below card with truncation
        winner_name = self.winner.name if self.winner else "Winner"
        if len(winner_name) > 14:
            winner_name = winner_name[:13] + "..."
        winner_name_surf = self.name_font.render(winner_name, True, (255, 215, 0))
        winner_name_rect = winner_name_surf.get_rect(
            center=(winner_x + self.card_width // 2, winner_y + self.card_height + self.name_offset_y)
        )
        screen.blit(winner_name_surf, winner_name_rect)

        # --- Draw Loser Card (right side, topples over) ---
        loser_x, loser_y = self.loser_pos

        # Calculate rotation and position offset for toppling
        rotation_angle = 90 * topple_progress  # Rotate 90 degrees clockwise
        y_drift = self.drift_max * topple_progress  # Drift down slightly
        alpha = int(255 - 128 * topple_progress)  # Fade to ~50% alpha

        if self.loser_image_original:
            # Start from original image to avoid quality degradation
            loser_display = self.loser_image_original.copy()

            # Apply red tint overlay to loser
            red_overlay = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
            red_overlay.fill((255, 0, 0, int(60 * topple_progress)))
            loser_display.blit(red_overlay, (0, 0))

            # Use rotozoom for smoother rotation (anti-aliased)
            if rotation_angle > 0.5:
                loser_display = pygame.transform.rotozoom(loser_display, -rotation_angle, 1.0)

            # Apply alpha
            loser_display.set_alpha(alpha)

            # Calculate position for rotation around bottom-center pivot
            if rotation_angle > 0.5:
                rotated_rect = loser_display.get_rect()
                # Pivot at bottom center of original card position
                pivot_x = loser_x + self.card_width // 2
                pivot_y = loser_y + self.card_height

                angle_rad = math.radians(rotation_angle)
                # Offset to simulate falling to the right
                offset_x = (self.card_height / 2) * math.sin(angle_rad)
                offset_y = (self.card_height / 2) * (1 - math.cos(angle_rad))
                final_x = pivot_x - rotated_rect.width // 2 + offset_x
                final_y = pivot_y - rotated_rect.height + offset_y + y_drift
            else:
                final_x = loser_x
                final_y = loser_y + y_drift

            screen.blit(loser_display, (final_x, final_y))

        # Red border for loser (fades as card falls)
        if topple_progress < 0.85:
            border_alpha = int(255 * (1 - topple_progress * 1.1))
            border_surf = pygame.Surface(
                (self.card_width + self.border_width * 2, self.card_height + self.border_width * 2),
                pygame.SRCALPHA
            )
            pygame.draw.rect(
                border_surf,
                (255, 80, 80, max(0, border_alpha)),
                border_surf.get_rect(),
                self.border_width,
                border_radius=self.border_radius
            )
            screen.blit(border_surf, (loser_x - self.border_width, loser_y - self.border_width + y_drift))

        # "DEFEATED" label above card with background
        defeated_y = loser_y - self.label_offset_y
        defeated_surf = self.label_font.render("DEFEATED", True, (255, 80, 80))
        defeated_surf.set_alpha(alpha)

        # Small background behind label
        label_bg2 = pygame.Surface((defeated_surf.get_width() + 16, defeated_surf.get_height() + 8), pygame.SRCALPHA)
        label_bg2.fill((0, 0, 0, int(150 * (alpha / 255))))
        pygame.draw.rect(label_bg2, (255, 80, 80, int(200 * (alpha / 255))), label_bg2.get_rect(), width=1, border_radius=4)
        label_bg2_rect = label_bg2.get_rect(center=(loser_x + self.card_width // 2, defeated_y))
        screen.blit(label_bg2, label_bg2_rect)

        defeated_rect = defeated_surf.get_rect(
            center=(loser_x + self.card_width // 2, defeated_y)
        )
        screen.blit(defeated_surf, defeated_rect)

        # Loser name below card (fades with card, truncated)
        loser_name = self.loser.name if self.loser else "Defeated"
        if len(loser_name) > 14:
            loser_name = loser_name[:13] + "..."
        loser_name_surf = self.name_font.render(loser_name, True, (255, 100, 100))
        loser_name_surf.set_alpha(alpha)
        loser_name_rect = loser_name_surf.get_rect(
            center=(loser_x + self.card_width // 2, loser_y + self.card_height + self.name_offset_y + y_drift)
        )
        screen.blit(loser_name_surf, loser_name_rect)

        # --- Skip hint at bottom ---
        if progress > 0.5:
            hint_alpha = min(180, int(180 * (progress - 0.5) * 3))
            pulse = 0.7 + 0.3 * math.sin(elapsed * 4)
            hint_surf = self.hint_font.render("[ PRESS SPACE TO CONTINUE ]", True, (150, 180, 200))
            hint_surf.set_alpha(int(hint_alpha * pulse))
            hint_rect = hint_surf.get_rect(center=(self.screen_width // 2, panel_y + self.panel_height - int(20 * self.scale)))
            screen.blit(hint_surf, hint_rect)
