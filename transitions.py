import pygame
import math
import random
import game_config as cfg
from game_config import (
    UI_FONT, 
    PLAYER_ROW_RECTS, OPPONENT_ROW_RECTS, 
    CARD_WIDTH, CARD_HEIGHT
)

def create_card_sweep_animation(screen, game, screen_width, screen_height, direction="out"):
    """
    Animate all cards on board sweeping off screen.
    direction: "out" = cards fly outward, "up" = cards fly up into hyperspace
    """
    clock = pygame.time.Clock()
    
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
        
        pygame.display.flip()
        clock.tick(60)


def create_hyperspace_transition(screen, screen_width, screen_height, round_number, transition_text):
    """
    Improved hyperspace transition with persistent star streaks and radial blur effect.
    """
    clock = pygame.time.Clock()
    transition_font = pygame.font.SysFont("Arial", 80, bold=True)
    
    # Pre-generate persistent star positions (not random each frame!)
    num_stars = 120
    stars = []
    for _ in range(num_stars):
        # Stars originate from center and streak outward (or vice versa)
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
            'color_tint': random.choice([(150, 150, 255), (180, 180, 255), (200, 200, 255), (255, 255, 255)])
        })
    
    center_x, center_y = screen_width // 2, screen_height // 2
    
    # Animation duration: 90 frames (1.5 seconds)
    total_frames = 90
    
    for frame in range(total_frames):
        progress = frame / total_frames
        
        # Dark space background with slight blue tint
        screen.fill((2, 2, 12))
        
        # Draw radial blur / whoosh effect (concentric rings expanding from center)
        if round_number == 2:
            # Entering hyperspace - rings expand outward
            for ring_idx in range(5):
                ring_progress = (progress + ring_idx * 0.15) % 1.0
                ring_radius = int(ring_progress * max(screen_width, screen_height))
                ring_alpha = int((1 - ring_progress) * 80)
                if ring_alpha > 0 and ring_radius > 0:
                    ring_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    pygame.draw.circle(ring_surf, (100, 150, 255, ring_alpha), 
                                      (center_x, center_y), ring_radius, width=3)
                    screen.blit(ring_surf, (0, 0))
        
        elif round_number == 3:
            # Emerging from hyperspace - rings contract inward
            for ring_idx in range(5):
                ring_progress = (1 - progress + ring_idx * 0.15) % 1.0
                ring_radius = int(ring_progress * max(screen_width, screen_height))
                ring_alpha = int(ring_progress * 60)
                if ring_alpha > 0 and ring_radius > 0:
                    ring_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    pygame.draw.circle(ring_surf, (100, 150, 255, ring_alpha),
                                      (center_x, center_y), ring_radius, width=3)
                    screen.blit(ring_surf, (0, 0))
        
        # Draw persistent star streaks
        for star in stars:
            if round_number == 2:
                # Entering hyperspace - stars streak FROM center OUTWARD
                # Streak length increases over time
                streak_length = 20 + progress * 400
                
                # Star moves outward from center
                current_dist = star['base_dist'] * (0.3 + progress * 1.5)
                
                # Calculate streak start and end points
                start_dist = max(0, current_dist - streak_length * 0.3)
                end_dist = current_dist + streak_length * 0.7
                
                start_x = center_x + math.cos(star['angle']) * start_dist
                start_y = center_y + math.sin(star['angle']) * start_dist
                end_x = center_x + math.cos(star['angle']) * end_dist
                end_y = center_y + math.sin(star['angle']) * end_dist
                
            else:  # round_number == 3
                # Emerging - stars streak FROM outside INWARD (decelerating)
                streak_length = 400 * (1 - progress) + 20
                
                # Star moves inward toward center
                current_dist = star['base_dist'] * (1.5 - progress * 1.2)
                
                start_dist = current_dist + streak_length * 0.7
                end_dist = max(0, current_dist - streak_length * 0.3)
                
                start_x = center_x + math.cos(star['angle']) * start_dist
                start_y = center_y + math.sin(star['angle']) * start_dist
                end_x = center_x + math.cos(star['angle']) * end_dist
                end_y = center_y + math.sin(star['angle']) * end_dist
            
            # Draw the star streak with gradient (brighter at head)
            color = star['color_tint']
            alpha = int(star['brightness'] * (0.5 + 0.5 * math.sin(progress * math.pi)))
            
            # Main streak
            pygame.draw.line(screen, color, (int(start_x), int(start_y)), 
                           (int(end_x), int(end_y)), star['thickness'])
            
            # Bright head of streak
            if round_number == 2:
                head_x, head_y = end_x, end_y
            else:
                head_x, head_y = start_x, start_y
            pygame.draw.circle(screen, (255, 255, 255), (int(head_x), int(head_y)), star['thickness'] + 1)
        
        # Planet appearing (round 3 only, in second half)
        if round_number == 3 and progress > 0.5:
            planet_progress = (progress - 0.5) * 2
            planet_alpha = int(planet_progress * 200)
            planet_radius = int(screen_height * 0.18)
            
            planet_surf = pygame.Surface((planet_radius * 2 + 40, planet_radius * 2 + 40), pygame.SRCALPHA)
            # Atmosphere glow
            pygame.draw.circle(planet_surf, (60, 100, 180, planet_alpha // 3), 
                             (planet_radius + 20, planet_radius + 20), planet_radius + 15)
            # Planet body
            pygame.draw.circle(planet_surf, (40, 80, 160, planet_alpha), 
                             (planet_radius + 20, planet_radius + 20), planet_radius)
            # Highlight
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
        
        pygame.display.flip()
        clock.tick(60)


def show_round_winner_announcement(screen, game, screen_width, screen_height):
    """Show cinematic announcement of who won the round with detailed scoreboard and screen shake."""
    # Get the round that just completed
    completed_round = game.round_number - 1
    
    # Determine winner text
    if game.round_winner == game.player1:
        winner_text = f"YOU WIN ROUND {completed_round}!"
        winner_color = (100, 255, 100)
    elif game.round_winner == game.player2:
        winner_text = f"OPPONENT WINS ROUND {completed_round}!"
        winner_color = (255, 100, 100)
    else:
        winner_text = f"ROUND {completed_round} DRAW!"
        winner_color = (255, 255, 100)
    
    # Get round history (who won each round so far)
    # We need to track this - for now infer from rounds_won
    round_results = []  # Will store who won each round
    
    # Reconstruct round results from current state
    # This is a simplified version - ideally game.py should track round_history
    p1_rounds = game.player1.rounds_won
    p2_rounds = game.player2.rounds_won
    total_rounds_played = completed_round
    
    # Build round results (this is an approximation)
    for i in range(total_rounds_played):
        if i == completed_round - 1:  # Current round just completed
            if game.round_winner == game.player1:
                round_results.append("p1")
            elif game.round_winner == game.player2:
                round_results.append("p2")
            else:
                round_results.append("draw")
        else:
            # For previous rounds, we have to guess based on total wins
            # This is imperfect but works for display
            round_results.append("unknown")
    
    # Fonts
    title_font = pygame.font.SysFont("Arial", 72, bold=True)
    score_font = pygame.font.SysFont("Arial", 48, bold=True)
    round_font = pygame.font.SysFont("Arial", 36, bold=True)
    label_font = pygame.font.SysFont("Arial", 32)
    
    clock = pygame.time.Clock()
    duration = 3000  # 3 seconds
    start_time = pygame.time.get_ticks()
    
    # Screen shake parameters
    shake_intensity = 15  # Initial shake intensity
    shake_decay = 0.92  # How fast shake decays
    current_shake = shake_intensity
    
    # Create a render surface for shake effect
    render_surface = pygame.Surface((screen_width, screen_height))
    
    while pygame.time.get_ticks() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    return  # Skip animation
        
        elapsed = pygame.time.get_ticks() - start_time
        progress = elapsed / duration
        
        # Calculate screen shake offset (strongest at start, decays over time)
        if progress < 0.3:
            shake_offset_x = random.uniform(-current_shake, current_shake)
            shake_offset_y = random.uniform(-current_shake, current_shake)
            current_shake *= shake_decay
        else:
            shake_offset_x = 0
            shake_offset_y = 0
        
        # Render to intermediate surface
        render_surface.fill((0, 0, 0))
        
        # Dark overlay
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        render_surface.blit(overlay, (0, 0))
        
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Impact flash effect (at very start)
        if progress < 0.1:
            flash_alpha = int((1 - progress / 0.1) * 150)
            flash_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            flash_surf.fill((*winner_color[:3], flash_alpha))
            render_surface.blit(flash_surf, (0, 0))
        
        # Main winner text - slide in from top with slam effect
        if progress < 0.15:
            # Fast slam down
            slam_progress = progress / 0.15
            text_y_offset = int((1 - slam_progress) * -200)
            text_scale = 1.0 + (1 - slam_progress) * 0.3  # Starts bigger, slams to normal
        else:
            text_y_offset = 0
            text_scale = 1.0
        
        text_alpha = min(255, int(255 * progress * 3))
        
        # Render winner text with optional scale
        if text_scale != 1.0:
            scaled_font = pygame.font.SysFont("Arial", int(72 * text_scale), bold=True)
            winner_surface = scaled_font.render(winner_text, True, winner_color)
        else:
            winner_surface = title_font.render(winner_text, True, winner_color)
        
        winner_surface.set_alpha(text_alpha)
        winner_rect = winner_surface.get_rect(center=(center_x, 120 + text_y_offset))
        render_surface.blit(winner_surface, winner_rect)
        
        # Scoreboard - fade in after title
        if progress > 0.3:
            board_alpha = min(255, int(255 * (progress - 0.3) * 2.5))
            
            # Scoreboard box
            board_width = 700
            board_height = 350
            board_x = center_x - board_width // 2
            board_y = center_y - 50
            
            board_surf = pygame.Surface((board_width, board_height), pygame.SRCALPHA)
            board_surf.fill((20, 30, 50, 240))
            pygame.draw.rect(board_surf, (255, 215, 0), board_surf.get_rect(), width=4, border_radius=15)
            board_surf.set_alpha(board_alpha)
            render_surface.blit(board_surf, (board_x, board_y))
            
            # Draw scoreboard content
            y_offset = board_y + 30
            
            # Title
            scoreboard_title = label_font.render("SCOREBOARD", True, (255, 215, 0))
            scoreboard_title.set_alpha(board_alpha)
            title_rect = scoreboard_title.get_rect(center=(center_x, y_offset))
            render_surface.blit(scoreboard_title, title_rect)
            
            y_offset += 60
            
            # Column headers
            col_header_font = pygame.font.SysFont("Arial", 28, bold=True)
            player_label = col_header_font.render("PLAYER", True, (200, 200, 200))
            round1_label = col_header_font.render("R1", True, (200, 200, 200))
            round2_label = col_header_font.render("R2", True, (200, 200, 200))
            round3_label = col_header_font.render("R3", True, (200, 200, 200))
            total_label = col_header_font.render("TOTAL", True, (200, 200, 200))
            
            player_label.set_alpha(board_alpha)
            round1_label.set_alpha(board_alpha)
            round2_label.set_alpha(board_alpha)
            round3_label.set_alpha(board_alpha)
            total_label.set_alpha(board_alpha)
            
            render_surface.blit(player_label, (board_x + 50, y_offset))
            render_surface.blit(round1_label, (board_x + 280, y_offset))
            render_surface.blit(round2_label, (board_x + 380, y_offset))
            render_surface.blit(round3_label, (board_x + 480, y_offset))
            render_surface.blit(total_label, (board_x + 580, y_offset))
            
            y_offset += 50
            
            # Draw separator line
            line_surf = pygame.Surface((board_width - 40, 3), pygame.SRCALPHA)
            line_surf.fill((255, 215, 0, board_alpha))
            render_surface.blit(line_surf, (board_x + 20, y_offset))
            
            y_offset += 20
            
            # Player 1 row
            p1_name = score_font.render("YOU", True, (100, 255, 100))
            p1_name.set_alpha(board_alpha)
            render_surface.blit(p1_name, (board_x + 50, y_offset))
            
            # Round scores for Player 1
            for round_num in range(1, 4):
                round_x = board_x + 280 + (round_num - 1) * 100
                
                if round_num <= completed_round:
                    # Check if player won this round
                    won_round = False
                    if round_num == completed_round and game.round_winner == game.player1:
                        won_round = True
                    elif round_num < completed_round:
                        # For previous rounds, check if they contributed to rounds_won
                        # This is approximate - ideally we'd track full history
                        won_round = (round_num <= p1_rounds)
                    
                    if won_round:
                        round_color = (100, 150, 255)  # Blue for won round
                        round_score = score_font.render("1", True, round_color)
                    else:
                        round_color = (150, 150, 150)  # Light grey for lost/draw
                        round_score = score_font.render("0", True, round_color)
                else:
                    # Future round
                    round_color = (80, 80, 80)
                    round_score = score_font.render("-", True, round_color)
                
                round_score.set_alpha(board_alpha)
                score_rect = round_score.get_rect(center=(round_x + 20, y_offset + 25))
                render_surface.blit(round_score, score_rect)
            
            # Total for Player 1
            p1_total = score_font.render(str(game.player1.rounds_won), True, (255, 215, 0))
            p1_total.set_alpha(board_alpha)
            total_rect = p1_total.get_rect(center=(board_x + 600, y_offset + 25))
            render_surface.blit(p1_total, total_rect)
            
            y_offset += 70
            
            # Player 2 row
            p2_name = score_font.render("OPP", True, (255, 100, 100))
            p2_name.set_alpha(board_alpha)
            render_surface.blit(p2_name, (board_x + 50, y_offset))
            
            # Round scores for Player 2
            for round_num in range(1, 4):
                round_x = board_x + 280 + (round_num - 1) * 100
                
                if round_num <= completed_round:
                    won_round = False
                    if round_num == completed_round and game.round_winner == game.player2:
                        won_round = True
                    elif round_num < completed_round:
                        won_round = (round_num <= p2_rounds)
                    
                    if won_round:
                        round_color = (100, 150, 255)  # Blue for won round
                        round_score = score_font.render("1", True, round_color)
                    else:
                        round_color = (150, 150, 150)  # Light grey for lost/draw
                        round_score = score_font.render("0", True, round_color)
                else:
                    round_color = (80, 80, 80)
                    round_score = score_font.render("-", True, round_color)
                
                round_score.set_alpha(board_alpha)
                score_rect = round_score.get_rect(center=(round_x + 20, y_offset + 25))
                render_surface.blit(round_score, score_rect)
            
            # Total for Player 2
            p2_total = score_font.render(str(game.player2.rounds_won), True, (255, 215, 0))
            p2_total.set_alpha(board_alpha)
            total_rect = p2_total.get_rect(center=(board_x + 600, y_offset + 25))
            render_surface.blit(p2_total, total_rect)
        
        # Skip instruction
        if progress > 0.4:
            skip_font = pygame.font.SysFont("Arial", 28)
            skip_text = skip_font.render("Press SPACE to continue", True, (180, 180, 180))
            skip_text.set_alpha(text_alpha)
            skip_rect = skip_text.get_rect(center=(center_x, screen_height - 80))
            render_surface.blit(skip_text, skip_rect)
        
        # Apply screen shake by blitting render_surface with offset
        screen.blit(render_surface, (int(shake_offset_x), int(shake_offset_y)))
        
        pygame.display.flip()
        clock.tick(60)

def show_game_start_animation(screen, game, screen_width, screen_height):
    """Show Stargate activation animation announcing who goes first."""
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
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    return  # Skip animation
        
        elapsed = pygame.time.get_ticks() - start_time
        progress = elapsed / duration
        
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
        
        pygame.display.flip()
        clock.tick(60)
