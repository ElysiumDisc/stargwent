import pygame
import os
import game_config as cfg
import display_manager
from cards import ALL_CARDS
from game_config import UI_FONT
from abilities import is_hero
from render_engine import _get_cached_font


def _draw_overlay_background(surface, screen_width, screen_height, title=None, title_color=None):
    """Draw standard dark overlay background with optional title."""
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill(cfg.BG_OVERLAY_DARK)
    surface.blit(overlay, (0, 0))

    if title:
        title_font = _get_cached_font(cfg.OVERLAY_TITLE_FONT_SIZE)
        color = title_color or cfg.HIGHLIGHT_GREEN
        title_text = title_font.render(title, True, color)
        title_rect = title_text.get_rect(center=(screen_width // 2, 60))
        surface.blit(title_text, title_rect)

def draw_leader_ability_box(surface, player, x, y, width, height, is_opponent=False):
    """Draw clickable leader ability box with Stargate theme."""
    if not player.leader:
        return
    
    # Stargate-themed box (semi-transparent with border)
    box_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    box_surface.fill(cfg.BG_PANEL)  # Dark blue-ish with transparency
    
    # Golden border (Stargate style)
    pygame.draw.rect(box_surface, cfg.GOLD, box_surface.get_rect(), width=3, border_radius=8)
    
    # Leader name
    name_font = pygame.font.SysFont("Arial", 22, bold=True)
    name_text = name_font.render(player.leader['name'], True, cfg.GOLD)
    name_rect = name_text.get_rect(center=(width // 2, 20))
    box_surface.blit(name_text, name_rect)
    
    # Ability description (wrapped)
    ability_font = pygame.font.SysFont("Arial", 16)
    words = player.leader['ability'].split(' ')
    lines = []
    current_line = ""
    for word in words:
        if ability_font.size(current_line + " " + word)[0] < width - 20:
            current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    lines.append(current_line.strip())
    
    line_y = name_rect.bottom + 5
    for i, line in enumerate(lines):
        if line:
            ability_text = ability_font.render(line, True, (200, 255, 200))
            ability_rect = ability_text.get_rect(center=(width // 2, line_y + i * 15))
            box_surface.blit(ability_text, ability_rect)

    # Blit to main surface
    surface.blit(box_surface, (x, y))
    
    return pygame.Rect(x, y, width, height)  # Return rect for click detection

def draw_leader_inspection_overlay(surface, player, screen_width, screen_height):
    """Draw full-screen leader inspection overlay."""
    if not player.leader:
        return
    
    # Keep battlefield visible during leader inspection
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    surface.blit(overlay, (0, 0))
    
    # Large leader portrait display
    portrait_width = 400
    portrait_height = 600
    portrait_x = (screen_width - portrait_width) // 2
    portrait_y = 60
    
    # Try to load and display leader image
    leader_card_id = player.leader.get('card_id', None)
    if leader_card_id:
        leader_image_path = f"assets/{leader_card_id}_leader.png"
        import os
        try:
            if os.path.exists(leader_image_path):
                leader_img = pygame.image.load(leader_image_path).convert_alpha()
                scaled_image = pygame.transform.scale(leader_img, (portrait_width, portrait_height))
                surface.blit(scaled_image, (portrait_x, portrait_y))
            elif leader_card_id in ALL_CARDS:
                leader_card = ALL_CARDS[leader_card_id]
                scaled_image = pygame.transform.scale(leader_card.image, (portrait_width, portrait_height))
                surface.blit(scaled_image, (portrait_x, portrait_y))
            else:
                # Fallback rectangle
                pygame.draw.rect(surface, (60, 60, 80), pygame.Rect(portrait_x, portrait_y, portrait_width, portrait_height))
        except:
            # Fallback rectangle
            pygame.draw.rect(surface, (60, 60, 80), pygame.Rect(portrait_x, portrait_y, portrait_width, portrait_height))
    
    # Golden border
    pygame.draw.rect(surface, cfg.GOLD, pygame.Rect(portrait_x, portrait_y, portrait_width, portrait_height), width=5)
    
    # Leader name
    name_font = pygame.font.Font(None, 48)
    name_text = name_font.render(player.leader['name'], True, cfg.GOLD)
    name_rect = name_text.get_rect(center=(screen_width // 2, portrait_y + portrait_height + 40))
    surface.blit(name_text, name_rect)
    
    # Ability description box
    ability_box_y = portrait_y + portrait_height + 80
    ability_box_width = 600
    ability_box_height = 120
    ability_box_x = (screen_width - ability_box_width) // 2
    
    # Draw ability box
    pygame.draw.rect(surface, (40, 40, 50), pygame.Rect(ability_box_x, ability_box_y, ability_box_width, ability_box_height))
    pygame.draw.rect(surface, cfg.GOLD, pygame.Rect(ability_box_x, ability_box_y, ability_box_width, ability_box_height), width=3)
    
    # Ability title
    ability_title_font = pygame.font.Font(None, 32)
    ability_title = ability_title_font.render("LEADER ABILITY", True, cfg.GOLD)
    title_rect = ability_title.get_rect(center=(screen_width // 2, ability_box_y + 20))
    surface.blit(ability_title, title_rect)
    
    # Ability description (wrapped)
    ability_font = pygame.font.Font(None, 28)
    ability_desc = player.leader.get('ability_desc', 'Unknown ability')
    
    # Word wrap the description
    words = ability_desc.split()
    lines = []
    current_line = ""
    max_width = ability_box_width - 40
    
    for word in words:
        test_line = current_line + word + " "
        if ability_font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word + " "
    if current_line:
        lines.append(current_line)
    
    # Draw lines
    line_y = ability_box_y + 50
    for line in lines[:3]:  # Max 3 lines
        line_text = ability_font.render(line.strip(), True, cfg.TEXT_LIGHT)
        line_rect = line_text.get_rect(center=(screen_width // 2, line_y))
        surface.blit(line_text, line_rect)
        line_y += 30
    
    # Instructions
    instruction_font = pygame.font.Font(None, 28)
    instruction = instruction_font.render("Press SPACE or Click to close", True, cfg.TEXT_DIM)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 50))
    surface.blit(instruction, instruction_rect)

def draw_medic_selection_overlay(surface, game, screen_width, screen_height):
    """Draw overlay for selecting a card to revive with medic ability."""
    _draw_overlay_background(surface, screen_width, screen_height,
                             "MEDIC: Choose a card to revive", cfg.HIGHLIGHT_GREEN)

    # Get valid cards
    valid_cards = game.get_medic_valid_cards(game.player1)
    
    if not valid_cards:
        # No cards available
        no_cards_text = cfg.UI_FONT.render("No cards available to revive", True, cfg.HIGHLIGHT_RED)
        no_cards_rect = no_cards_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(no_cards_text, no_cards_rect)
        return []
    
    # Display cards in a grid
    card_display_width = 160
    card_display_height = 240
    cards_per_row = 5
    spacing = 20
    start_y = 140
    
    card_rects = []
    for i, card in enumerate(valid_cards):
        row = i // cards_per_row
        col = i % cards_per_row
        
        # Calculate position
        total_row_width = cards_per_row * card_display_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_display_width + spacing)
        y = start_y + row * (card_display_height + spacing + 40)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        
        # Highlight border
        card_rect = pygame.Rect(x, y, card_display_width, card_display_height)
        pygame.draw.rect(surface, cfg.HIGHLIGHT_GREEN, card_rect, width=3)
        
        # Card name below
        name_text = cfg.UI_FONT.render(card.name[:20], True, cfg.WHITE)
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 20))
        surface.blit(name_text, name_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    instruction = instruction_font.render("Click a card to revive it", True, cfg.TEXT_DIM)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def draw_decoy_selection_overlay(surface, game, screen_width, screen_height):
    """Draw overlay for selecting a card to return to hand with decoy ability."""
    _draw_overlay_background(surface, screen_width, screen_height,
                             "DECOY: Choose a card to return to your hand", (150, 200, 255))

    # Subtitle
    subtitle_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    subtitle_text = subtitle_font.render("(You can take your own card or an opponent's card)", True, cfg.TEXT_DIM)
    subtitle_rect = subtitle_text.get_rect(center=(screen_width // 2, 100))
    surface.blit(subtitle_text, subtitle_rect)

    # Get valid cards (all non-Legendary Commander units on both boards)
    valid_cards = game.get_decoy_valid_cards()
    
    if not valid_cards:
        # No cards available
        no_cards_text = cfg.UI_FONT.render("No cards available on the board", True, cfg.HIGHLIGHT_RED)
        no_cards_rect = no_cards_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(no_cards_text, no_cards_rect)
        return []
    
    # Display cards in a grid
    card_display_width = 140
    card_display_height = 210
    cards_per_row = 6
    spacing = 15
    start_y = 160
    
    card_rects = []
    for i, card in enumerate(valid_cards):
        row = i // cards_per_row
        col = i % cards_per_row
        
        # Calculate position
        total_row_width = cards_per_row * card_display_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_display_width + spacing)
        y = start_y + row * (card_display_height + spacing + 50)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        
        # Determine card owner
        is_player_card = card in [c for row in game.player1.board.values() for c in row]
        is_opponent_card = card in [c for row in game.player2.board.values() for c in row]
        
        # Highlight border - blue for own cards, red for opponent cards
        card_rect = pygame.Rect(x, y, card_display_width, card_display_height)
        if is_player_card:
            pygame.draw.rect(surface, cfg.HIGHLIGHT_BLUE, card_rect, width=3)
        elif is_opponent_card:
            pygame.draw.rect(surface, cfg.HIGHLIGHT_RED, card_rect, width=3)
        
        # Owner label
        owner_text = cfg.UI_FONT.render("YOUR CARD" if is_player_card else "OPP CARD", True, 
                                    cfg.HIGHLIGHT_BLUE if is_player_card else cfg.HIGHLIGHT_RED)
        owner_rect = owner_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 10))
        surface.blit(owner_text, owner_rect)
        
        # Card name below
        name_text = cfg.UI_FONT.render(card.name[:15], True, cfg.WHITE)
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 30))
        surface.blit(name_text, name_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    instruction = instruction_font.render("Click a card to return it to your hand", True, cfg.TEXT_DIM)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def draw_card_inspection_overlay(surface, card, screen_width, screen_height):
    """Draw full-screen card inspection overlay when spacebar/right-click is pressed."""
    # Semi-transparent dark overlay for focus
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill(cfg.BG_OVERLAY_MEDIUM)
    surface.blit(overlay, (0, 0))
    
    # Large card display - 2x scale for crisp preview
    # Base card is typically ~240x360, so 2x = 480x720
    card_display_width = min(560, int(screen_width * 0.35))  # Larger but responsive
    card_display_height = int(card_display_width * 1.5)  # Maintain aspect ratio
    card_x = (screen_width - card_display_width) // 2
    card_y = max(40, (screen_height - card_display_height - 180) // 2)  # Room for description
    
    # Draw card image (load original for better quality)
    try:
        # Load original image from file for crisp display
        if hasattr(card, 'image_path') and os.path.exists(card.image_path):
            original_image = pygame.image.load(card.image_path).convert_alpha()
            large_card_image = pygame.transform.smoothscale(original_image, (card_display_width, card_display_height))
        else:
            # Fallback to scaled existing image
            large_card_image = pygame.transform.smoothscale(card.image, (card_display_width, card_display_height))
        surface.blit(large_card_image, (card_x, card_y))
    except:
        pygame.draw.rect(surface, (80, 80, 90), pygame.Rect(card_x, card_y, card_display_width, card_display_height))
    
    # Faction-colored glow effect
    glow_color = cfg.get_faction_ui_color(card.faction)
    
    # Draw multiple borders for glow effect
    for i in range(4):
        border_rect = pygame.Rect(card_x - i * 2, card_y - i * 2, 
                                  card_display_width + i * 4, card_display_height + i * 4)
        alpha = 200 - i * 50
        border_color = (*glow_color, alpha)
        border_surf = pygame.Surface((border_rect.width, border_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, border_color, border_surf.get_rect(), width=3, border_radius=8)
        surface.blit(border_surf, border_rect.topleft)
    
    # Main golden border
    pygame.draw.rect(surface, cfg.GOLD, pygame.Rect(card_x, card_y, card_display_width, card_display_height), width=4, border_radius=6)
    
    # Description box UNDER the card art
    desc_box_y = card_y + card_display_height + 15
    desc_box_height = min(160, screen_height - desc_box_y - 50)
    desc_box_padding = 15
    desc_box_width = card_display_width + 100  # Wider for more text
    desc_box_x = (screen_width - desc_box_width) // 2
    
    # Ensure valid dimensions (at least 1x1)
    desc_box_width = max(1, desc_box_width)
    desc_box_height = max(1, desc_box_height)
    
    # Create semi-transparent description box
    desc_surface = pygame.Surface((desc_box_width, desc_box_height), pygame.SRCALPHA)
    desc_surface.fill((15, 25, 45, 240))
    
    # Border for description box
    pygame.draw.rect(desc_surface, glow_color, desc_surface.get_rect(), width=3, border_radius=12)
    
    # Draw description text
    desc_font = pygame.font.SysFont("Arial", max(20, int(24 * display_manager.SCALE_FACTOR)), bold=True)
    small_font = pygame.font.SysFont("Arial", max(16, int(18 * display_manager.SCALE_FACTOR)))
    
    # Card name at top
    name_text = desc_font.render(card.name, True, cfg.GOLD)
    name_rect = name_text.get_rect(center=(desc_box_width // 2, 22))
    desc_surface.blit(name_text, name_rect)
    
    # Stats line with icons
    power_str = f"Power: {card.power}"
    row_str = f"Row: {card.row.capitalize()}"
    faction_str = f"Faction: {card.faction}"
    stats_text = small_font.render(f"{power_str}  |  {row_str}  |  {faction_str}", True, (200, 200, 220))
    stats_rect = stats_text.get_rect(center=(desc_box_width // 2, 50))
    desc_surface.blit(stats_text, stats_rect)
    
    # Ability/Description
    if card.ability:
        ability_title = small_font.render("Ability:", True, (150, 255, 150))
        desc_surface.blit(ability_title, (desc_box_padding, 75))
        
        # Word wrap the ability text
        ability_words = card.ability.split()
        line = ""
        line_y = 98
        max_line_width = desc_box_width - (desc_box_padding * 2)
        
        for word in ability_words:
            test_line = line + word + " "
            if small_font.size(test_line)[0] < max_line_width:
                line = test_line
            else:
                if line:
                    ability_text = small_font.render(line.strip(), True, (220, 255, 220))
                    desc_surface.blit(ability_text, (desc_box_padding, line_y))
                    line_y += 22
                line = word + " "
        
        # Draw remaining text
        if line:
            ability_text = small_font.render(line.strip(), True, (220, 255, 220))
            desc_surface.blit(ability_text, (desc_box_padding, line_y))
    else:
        # No ability - show unit type
        no_ability_text = small_font.render("Standard unit - no special ability", True, cfg.TEXT_DIMMER)
        no_ability_rect = no_ability_text.get_rect(center=(desc_box_width // 2, 100))
        desc_surface.blit(no_ability_text, no_ability_rect)
    
    # Blit description box to screen
    surface.blit(desc_surface, (desc_box_x, desc_box_y))
    
    # Close instruction at bottom
    close_font = pygame.font.SysFont("Arial", max(14, int(16 * display_manager.SCALE_FACTOR)))
    close_text = close_font.render("Click anywhere or press SPACE to close", True, cfg.TEXT_DIMMER)
    close_rect = close_text.get_rect(center=(screen_width // 2, screen_height - 25))
    surface.blit(close_text, close_rect)

def draw_discard_viewer(surface, discard_pile, screen_width, screen_height, scroll_offset):
    """Draw discard pile viewer overlay."""
    # Semi-transparent background
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill(cfg.BG_OVERLAY_DARK)
    surface.blit(overlay, (0, 0))
    
    # Title
    title_font = _get_cached_font(64)
    title = title_font.render("DISCARD PILE", True, cfg.HIGHLIGHT_RED)
    title_rect = title.get_rect(center=(screen_width // 2, 60))
    surface.blit(title, title_rect)
    
    if not discard_pile:
        empty_text = cfg.UI_FONT.render("Discard pile is empty", True, cfg.TEXT_MUTED)
        empty_rect = empty_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(empty_text, empty_rect)
        return
    
    # Draw cards in grid
    card_width = 200
    card_height = 300
    cards_per_row = 6
    spacing = 20
    start_y = 140 + scroll_offset
    
    for i, card in enumerate(discard_pile):
        row = i // cards_per_row
        col = i % cards_per_row
        
        total_row_width = cards_per_row * card_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_width + spacing)
        y = start_y + row * (card_height + spacing + 40)
        
        # Only draw if on screen
        if y > 60 and y < screen_height:
            scaled_image = pygame.transform.scale(card.image, (card_width, card_height))
            surface.blit(scaled_image, (x, y))
            pygame.draw.rect(surface, cfg.HIGHLIGHT_RED, pygame.Rect(x, y, card_width, card_height), width=3)
            
            # Store rect for click detection
            card.rect = pygame.Rect(x, y, card_width, card_height)
            
            # Card name
            name_text = pygame.font.Font(None, 24).render(card.name[:25], True, cfg.WHITE)
            name_rect = name_text.get_rect(center=(x + card_width // 2, y + card_height + 20))
            surface.blit(name_text, name_rect)
    
    # Instructions
    inst_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    inst = inst_font.render("Scroll: Mouse Wheel | Right-Click: Inspect | Close: ESC or Click", True, cfg.TEXT_DIM)
    inst_rect = inst.get_rect(center=(screen_width // 2, screen_height - 40))
    surface.blit(inst, inst_rect)

def draw_jonas_peek_overlay(surface, game, screen_width, screen_height):
    """Jonas Quinn: Show cards drawn by opponent - click one to copy to hand."""
    card_rects = []

    if not game.opponent_drawn_cards:
        return card_rects

    _draw_overlay_background(surface, screen_width, screen_height,
                             "JONAS QUINN — Eidetic Memory", cfg.HIGHLIGHT_CYAN)

    # Subtitle
    cards_count = len(game.opponent_drawn_cards)
    subtitle_font = _get_cached_font(36)
    subtitle_text = subtitle_font.render(f"Opponent drew {cards_count} card{'s' if cards_count > 1 else ''} — Click one to copy to your hand!", True, cfg.TEXT_DIM)
    subtitle_rect = subtitle_text.get_rect(center=(screen_width // 2, 130))
    surface.blit(subtitle_text, subtitle_rect)

    # Show all drawn cards
    card_display_width = 250
    card_display_height = 375
    spacing = 20
    total_width = len(game.opponent_drawn_cards) * (card_display_width + spacing) - spacing
    start_x = (screen_width - total_width) // 2
    card_y = 200

    for i, card in enumerate(game.opponent_drawn_cards):
        card_x = start_x + i * (card_display_width + spacing)
        rect = pygame.Rect(card_x, card_y, card_display_width, card_display_height)

        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (card_x, card_y))
        pygame.draw.rect(surface, cfg.HIGHLIGHT_CYAN, rect, width=3)

        # Card name below
        detail_font = _get_cached_font(24)
        name_text = detail_font.render(card.name, True, cfg.TEXT_DIM)
        name_rect = name_text.get_rect(center=(card_x + card_display_width // 2, card_y + card_display_height + 20))
        surface.blit(name_text, name_rect)

        # Power and row
        info_text = detail_font.render(f"{card.power}  •  {card.row.capitalize()}", True, cfg.TEXT_MUTED)
        info_rect = info_text.get_rect(center=(card_x + card_display_width // 2, card_y + card_display_height + 45))
        surface.blit(info_text, info_rect)

        # Store rect for click detection
        card_rects.append((card, rect))

    # Instruction
    instruction_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    instruction = instruction_font.render("Click a card to copy it to your hand", True, cfg.TEXT_MUTED)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)

    return card_rects

def draw_baal_clone_overlay(surface, game, screen_width, screen_height):
    """Ba'al Clone: Select unit to clone."""
    _draw_overlay_background(surface, screen_width, screen_height,
                             "BA'AL CLONE: Choose Unit to Duplicate", (200, 50, 50))

    # Get all player units
    all_units = []
    for row_cards in game.player1.board.values():
        all_units.extend([c for c in row_cards if not is_hero(c)])
    
    if not all_units:
        no_units_text = cfg.UI_FONT.render("No units available to clone", True, cfg.HIGHLIGHT_RED)
        no_units_rect = no_units_text.get_rect(center=(screen_width // 2, screen_height // 2))
        surface.blit(no_units_text, no_units_rect)
        return []
    
    # Display units in grid
    card_display_width = 140
    card_display_height = 210
    cards_per_row = 6
    spacing = 15
    start_y = 140
    
    card_rects = []
    for i, card in enumerate(all_units):
        row = i // cards_per_row
        col = i % cards_per_row
        
        total_row_width = cards_per_row * card_display_width + (cards_per_row - 1) * spacing
        start_x = (screen_width - total_row_width) // 2
        x = start_x + col * (card_display_width + spacing)
        y = start_y + row * (card_display_height + spacing + 50)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        
        card_rect = pygame.Rect(x, y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (200, 50, 50), card_rect, width=3)
        
        # Power display
        power_text = cfg.UI_FONT.render(f"Power: {card.displayed_power}", True, cfg.GOLD)
        power_rect = power_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 20))
        surface.blit(power_text, power_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    instruction = instruction_font.render("Click a unit to clone it", True, cfg.TEXT_DIM)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 60))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def draw_vala_selection_overlay(surface, vala_cards, screen_width, screen_height):
    """Vala: Choose 1 of 3 cards."""
    _draw_overlay_background(surface, screen_width, screen_height,
                             "VALA MAL DORAN: Choose 1 Card to Keep", (150, 50, 150))
    
    # Display 3 cards
    card_display_width = 300
    card_display_height = 450
    spacing = 80
    total_width = 3 * card_display_width + 2 * spacing
    start_x = (screen_width - total_width) // 2
    card_y = 200
    
    card_rects = []
    for i, card in enumerate(vala_cards[:3]):
        x = start_x + i * (card_display_width + spacing)
        
        # Draw card
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, card_y))
        
        card_rect = pygame.Rect(x, card_y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (150, 50, 150), card_rect, width=3)
        
        # Card name
        name_text = cfg.UI_FONT.render(card.name[:20], True, cfg.WHITE)
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, card_y + card_display_height + 30))
        surface.blit(name_text, name_rect)
        
        card_rects.append((card, card_rect))
    
    # Instructions
    instruction_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    instruction = instruction_font.render("Click a card to add it to your hand", True, cfg.TEXT_DIM)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 80))
    surface.blit(instruction, instruction_rect)
    
    return card_rects

def draw_catherine_selection_overlay(surface, revealed_cards, screen_width, screen_height):
    """Catherine Langford: Reveal top cards and choose one to draw immediately."""
    _draw_overlay_background(surface, screen_width, screen_height,
                             "CATHERINE LANGFORD — Ancient Knowledge", (235, 200, 120))

    subtitle_font = _get_cached_font(34)
    subtitle_text = subtitle_font.render("Choose a card to draw immediately (others return to the deck bottom)", True, (230, 230, 230))
    subtitle_rect = subtitle_text.get_rect(center=(screen_width // 2, 140))
    surface.blit(subtitle_text, subtitle_rect)

    card_display_width = 280
    card_display_height = 420
    spacing = 70
    cards_to_show = revealed_cards[:3]
    count = max(1, len(cards_to_show))
    total_width = count * card_display_width + (count - 1) * spacing
    start_x = (screen_width - total_width) // 2
    card_y = 220

    card_rects = []
    for i, card in enumerate(cards_to_show):
        x = start_x + i * (card_display_width + spacing)
        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, card_y))
        rect = pygame.Rect(x, card_y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (235, 200, 120), rect, width=4)
        name_text = cfg.UI_FONT.render(card.name[:22], True, cfg.WHITE)
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, card_y + card_display_height + 28))
        surface.blit(name_text, name_rect)
        card_rects.append((card, rect))

    instruction_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    instruction = instruction_font.render("Click a card to draw it now (it will be added to your hand to play immediately)", True, cfg.TEXT_DIM)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 70))
    surface.blit(instruction, instruction_rect)

    return card_rects

def draw_leader_choice_overlay(surface, ability_result, screen_width, screen_height):
    """Generic leader ability card selection UI (Jonas Quinn, Ba'al, etc.)"""
    ability_name = ability_result.get("ability", "Leader Ability")
    revealed_cards = ability_result.get("revealed_cards", [])

    # Title mapping
    titles = {
        "Eidetic Memory": ("JONAS QUINN — Eidetic Memory", "Choose a card to copy to your hand"),
        "System Lord's Cunning": ("BA'AL — System Lord's Cunning", "Choose a card to resurrect from your discard pile")
    }

    title_str, subtitle_str = titles.get(ability_name, (ability_name, "Choose a card"))

    _draw_overlay_background(surface, screen_width, screen_height,
                             title_str, (235, 200, 120))

    subtitle_font = _get_cached_font(34)
    subtitle = subtitle_font.render(subtitle_str, True, (230, 230, 230))
    subtitle_rect = subtitle.get_rect(center=(screen_width // 2, 140))
    surface.blit(subtitle, subtitle_rect)

    card_display_width = 240
    card_display_height = 360
    spacing = 40
    max_per_row = 5

    card_rects = []
    for idx, card in enumerate(revealed_cards[:10]):  # Max 10 cards
        row = idx // max_per_row
        col = idx % max_per_row

        cards_in_row = min(max_per_row, len(revealed_cards) - row * max_per_row)
        total_width = cards_in_row * card_display_width + (cards_in_row - 1) * spacing
        start_x = (screen_width - total_width) // 2

        x = start_x + col * (card_display_width + spacing)
        y = 220 + row * (card_display_height + 80)

        scaled_image = pygame.transform.scale(card.image, (card_display_width, card_display_height))
        surface.blit(scaled_image, (x, y))
        rect = pygame.Rect(x, y, card_display_width, card_display_height)
        pygame.draw.rect(surface, (235, 200, 120), rect, width=4)

        name_text = cfg.UI_FONT.render(card.name[:20], True, cfg.WHITE)
        name_rect = name_text.get_rect(center=(x + card_display_width // 2, y + card_display_height + 20))
        surface.blit(name_text, name_rect)

        card_rects.append((card, rect))

    instruction_font = _get_cached_font(cfg.OVERLAY_INSTRUCTION_FONT_SIZE)
    instruction = instruction_font.render("Click a card to select it", True, cfg.TEXT_DIM)
    instruction_rect = instruction.get_rect(center=(screen_width // 2, screen_height - 70))
    surface.blit(instruction, instruction_rect)

    return card_rects