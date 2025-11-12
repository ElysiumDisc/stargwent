"""
Iris Power System for StarGwent
Each faction has a unique, once-per-round, cinematic ability
"""
import pygame
import math
import random
import random
import math


class FactionPower:
    """Base class for faction-specific powers."""
    def __init__(self, name, description, faction):
        self.name = name
        self.description = description
        self.faction = faction
        self.available = True
        self.used_this_game = False  # Once per game for all factions
    
    def is_available(self):
        """Check if the power can be used."""
        return self.available and not self.used_this_game
    
    def activate(self, game, player):
        """Execute the Faction Power. Override in subclasses."""
        if not self.is_available():
            return False
        
        self.available = False
        self.used_this_game = True  # Can never be used again this game
        return True
    
    def reset_round(self):
        """Powers are once per game, so round reset does nothing."""
        pass  # Do NOT reset - once per game only!


class TauriFactionPower(FactionPower):
    """The Gate Shutdown - Destroys the highest strength card on each of the opponent's rows."""
    def __init__(self):
        super().__init__(
            "The Gate Shutdown",
            "Destroy the strongest enemy unit in each row",
            "Tau'ri"
        )
    
    def activate(self, game, player):
        if not super().activate(game, player):
            return False
        
        opponent = game.player2 if player == game.player1 else game.player1
        destroyed_cards = []
        
        # Find and destroy strongest non-Hero in each row
        for row_name in ["close", "ranged", "siege"]:
            row_cards = opponent.board.get(row_name, [])
            if not row_cards:
                continue
            
            # Find strongest non-Legendary Commander
            non_hero_cards = [c for c in row_cards if "Legendary Commander" not in (c.ability or "")]
            if non_hero_cards:
                strongest = max(non_hero_cards, key=lambda c: c.displayed_power)
                opponent.board[row_name].remove(strongest)
                opponent.discard_pile.append(strongest)
                destroyed_cards.append(strongest)
        
        return True


class GoauldFactionPower(FactionPower):
    """Sarcophagus Revival - Play two random non-Hero cards from your discard pile."""
    def __init__(self):
        super().__init__(
            "Sarcophagus Revival",
            "Revive 2 random units from your discard pile",
            "Goa'uld"
        )
    
    def activate(self, game, player):
        if not super().activate(game, player):
            return False
        
        # Get valid cards from discard (non-Hero units)
        valid_cards = [c for c in player.discard_pile 
                      if "Legendary Commander" not in (c.ability or "") 
                      and c.row in ["close", "ranged", "siege", "agile"]]
        
        if not valid_cards:
            return False
        
        # Revive up to 2 random cards
        num_to_revive = min(2, len(valid_cards))
        revived_cards = random.sample(valid_cards, num_to_revive)
        
        for card in revived_cards:
            player.discard_pile.remove(card)
            # Place in appropriate row
            target_row = card.row if card.row != "agile" else random.choice(["close", "ranged"])
            player.board[target_row].append(card)
        
        return True


class LucianFactionPower(FactionPower):
    """Unstable Naquadah - Deals 5 damage to every non-Hero unit on the battlefield."""
    def __init__(self):
        super().__init__(
            "Unstable Naquadah",
            "Deal 5 damage to all non-Hero units on both sides",
            "Lucian Alliance"
        )
    
    def activate(self, game, player):
        if not super().activate(game, player):
            return False
        
        # Damage all non-Hero units on both boards (affects BASE power, minimum 0)
        damaged_count = 0
        for game_player in [game.player1, game.player2]:
            for row_name in ["close", "ranged", "siege"]:
                row_cards = list(game_player.board[row_name])  # Copy list to avoid modification issues
                for card in row_cards:
                    if "Legendary Commander" not in (card.ability or ""):
                        # Reduce BASE power by 5 (so it persists through calculate_score)
                        old_power = card.power
                        card.power = max(0, card.power - 5)
                        card.displayed_power = card.power
                        damaged_count += 1
                        print(f"Unstable Naquadah: {card.name} power {old_power} -> {card.power}")
        
        print(f"Unstable Naquadah activated! Damaged {damaged_count} units")
        
        # Recalculate scores to apply all effects
        game.player1.calculate_score()
        game.player2.calculate_score()
        
        return True


class JaffaFactionPower(FactionPower):
    """Rebel Alliance Aid - Draw 3 cards, then discard 3 random cards."""
    def __init__(self):
        super().__init__(
            "Rebel Alliance Aid",
            "Draw 3 cards, then discard 3 random cards",
            "Jaffa Rebellion"
        )
    
    def activate(self, game, player):
        if not super().activate(game, player):
            return False
        
        # Draw 3 cards
        player.draw_cards(3)
        print(f"{player.name} drew 3 cards from Rebel Alliance Aid")
        
        # Discard 3 random cards from hand
        if len(player.hand) >= 3:
            import random
            cards_to_discard = random.sample(player.hand, 3)
            for card in cards_to_discard:
                player.hand.remove(card)
                player.discard_pile.append(card)
                print(f"  Discarded: {card.name}")
        else:
            # If fewer than 3 cards, discard all
            while player.hand:
                card = player.hand.pop()
                player.discard_pile.append(card)
                print(f"  Discarded: {card.name}")
        
        return True


class AsgardFactionPower(FactionPower):
    """Holographic Decoy - Swap opponent's close combat and ranged rows."""
    def __init__(self):
        super().__init__(
            "Holographic Decoy",
            "Swap opponent's entire close combat and ranged rows",
            "Asgard"
        )
        self.pending_selection = False
        self.selected_cards = []
    
    def activate(self, game, player):
        if not super().activate(game, player):
            return False
        
        # Simply swap opponent's close combat row with their ranged row
        opponent = game.player2 if player == game.player1 else game.player1
        
        # Swap the entire rows
        opponent.board["close"], opponent.board["ranged"] = opponent.board["ranged"], opponent.board["close"]
        
        print(f"Asgard Holographic Decoy: Swapped opponent's close combat and ranged rows!")
        print(f"  Close row now has {len(opponent.board['close'])} units")
        print(f"  Ranged row now has {len(opponent.board['ranged'])} units")
        
        # Recalculate scores after swap (row-specific bonuses might have changed)
        opponent.calculate_score()
        player.calculate_score()
        
        return True
    
    def select_card(self, card):
        """Select a card to swap."""
        if len(self.selected_cards) < 2:
            self.selected_cards.append(card)
            return True
        return False
    
    def can_execute_swap(self):
        """Check if we have 2 cards selected."""
        return len(self.selected_cards) == 2
    
    def execute_swap(self, game, player):
        """Swap the two selected cards."""
        if not self.can_execute_swap():
            return False
        
        card1, card2 = self.selected_cards
        opponent = game.player2 if player == game.player1 else game.player1
        
        # Find which rows the cards are in
        row1, row2 = None, None
        idx1, idx2 = None, None
        
        for row_name, row_cards in opponent.board.items():
            if card1 in row_cards:
                row1 = row_name
                idx1 = row_cards.index(card1)
            if card2 in row_cards:
                row2 = row_name
                idx2 = row_cards.index(card2)
        
        if row1 and row2:
            # Swap cards
            opponent.board[row1][idx1], opponent.board[row2][idx2] = opponent.board[row2][idx2], opponent.board[row1][idx1]
            
            # Disable abilities (mark with temporary flag)
            card1.abilities_disabled = True
            card2.abilities_disabled = True
        
        self.pending_selection = False
        self.selected_cards = []
        return True


# Faction Power mapping by faction
FACTION_POWERS = {
    "Tau'ri": TauriFactionPower(),
    "Goa'uld": GoauldFactionPower(),
    "Lucian Alliance": LucianFactionPower(),
    "Jaffa Rebellion": JaffaFactionPower(),
    "Asgard": AsgardFactionPower(),
}


class FactionPowerUI:
    """UI component for displaying and activating Iris Powers."""
    def __init__(self, x, y, width=300, height=120):
        self.rect = pygame.Rect(x, y, width, height)
        self.button_rect = pygame.Rect(x + width - 110, y + height - 45, 100, 35)
        self.hovered = False
        self.button_hovered = False
    
    def update(self, mouse_pos):
        """Update hover states."""
        self.hovered = self.rect.collidepoint(mouse_pos)
        self.button_hovered = self.button_rect.collidepoint(mouse_pos)
    
    def draw(self, surface, faction_power, is_player=True):
        """Draw the Iris Power UI element."""
        # Main box - Stargate themed
        box_color = (30, 50, 80, 220) if is_player else (50, 30, 30, 220)
        border_color = (255, 215, 0) if faction_power.is_available() else (100, 100, 100)
        
        # Semi-transparent background
        box_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        box_surface.fill(box_color)
        
        # Animated border if available
        if faction_power.is_available():
            # Pulsing glow
            time = pygame.time.get_ticks() / 1000.0
            glow_alpha = int(100 + 50 * math.sin(time * 3))
            glow_color = (*border_color[:3], glow_alpha)
            
            # Draw glow
            for i in range(3):
                glow_rect = self.rect.inflate(i * 4, i * 4)
                pygame.draw.rect(surface, glow_color, glow_rect, width=2, border_radius=10)
        
        # Main border
        pygame.draw.rect(box_surface, border_color, box_surface.get_rect(), width=3, border_radius=10)
        surface.blit(box_surface, self.rect.topleft)
        
        # Iris Power icon (chevron-like symbol)
        icon_x = self.rect.x + 20
        icon_y = self.rect.y + self.rect.height // 2
        self.draw_iris_icon(surface, icon_x, icon_y, faction_power.is_available())
        
        # Text - Power name
        name_font = pygame.font.SysFont("Arial", 20, bold=True)
        name_color = (255, 215, 0) if faction_power.is_available() else (150, 150, 150)
        name_text = name_font.render(faction_power.name, True, name_color)
        surface.blit(name_text, (self.rect.x + 70, self.rect.y + 15))
        
        # Description
        desc_font = pygame.font.SysFont("Arial", 14)
        desc_color = (200, 200, 200) if faction_power.is_available() else (120, 120, 120)
        
        # Word wrap description
        words = faction_power.description.split()
        lines = []
        current_line = ""
        max_width = self.rect.width - 80
        
        for word in words:
            test_line = current_line + word + " "
            if desc_font.size(test_line)[0] < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)
        
        # Draw description lines
        y_offset = self.rect.y + 45
        for line in lines[:2]:  # Max 2 lines
            line_text = desc_font.render(line.strip(), True, desc_color)
            surface.blit(line_text, (self.rect.x + 70, y_offset))
            y_offset += 18
        
        # Activate button (if available)
        if is_player:
            if faction_power.is_available():
                button_color = (200, 50, 50) if self.button_hovered else (150, 30, 30)
                pygame.draw.rect(surface, button_color, self.button_rect, border_radius=5)
                pygame.draw.rect(surface, (255, 100, 100), self.button_rect, width=2, border_radius=5)
                
                button_font = pygame.font.SysFont("Arial", 16, bold=True)
                button_text = button_font.render("ACTIVATE", True, (255, 255, 255))
                text_rect = button_text.get_rect(center=self.button_rect.center)
                surface.blit(button_text, text_rect)
                
                # Hotkey hint
                hint_font = pygame.font.SysFont("Arial", 11)
                hint_text = hint_font.render("(Press F)", True, (200, 200, 200))
                hint_rect = hint_text.get_rect(center=(self.button_rect.centerx, self.button_rect.bottom + 10))
                surface.blit(hint_text, hint_rect)
            else:
                # Used indicator - ONCE PER GAME
                used_color = (80, 80, 80)
                pygame.draw.rect(surface, used_color, self.button_rect, border_radius=5)
                
                used_font = pygame.font.SysFont("Arial", 12, bold=True)
                used_text = used_font.render("USED", True, (150, 150, 150))
                text_rect = used_text.get_rect(center=self.button_rect.center)
                surface.blit(used_text, text_rect)
        else: # is not player (is AI)
            # Just show status, no button
            status_font = pygame.font.SysFont("Arial", 16, bold=True)
            if faction_power.is_available():
                status_text = status_font.render("READY", True, (100, 255, 100))
            else:
                status_text = status_font.render("USED", True, (150, 150, 150))
            
            status_rect = status_text.get_rect(center=self.button_rect.center)
            surface.blit(status_text, status_rect)
    
    def draw_iris_icon(self, surface, x, y, is_active):
        """Draw a stylized iris/chevron icon."""
        radius = 25
        color = (255, 215, 0) if is_active else (100, 100, 100)
        
        # Outer ring
        pygame.draw.circle(surface, color, (x, y), radius, width=3)
        
        # Inner chevron pattern (7 chevrons)
        for i in range(7):
            angle = (i * 360 / 7) - 90
            rad = math.radians(angle)
            cx = x + math.cos(rad) * (radius - 8)
            cy = y + math.sin(rad) * (radius - 8)
            
            # Small triangle (chevron)
            if is_active:
                # Animated glow
                time = pygame.time.get_ticks() / 200.0
                glow = int(200 + 55 * math.sin(time + i))
                chevron_color = (glow, glow // 2, 0)
            else:
                chevron_color = (80, 80, 80)
            
            pygame.draw.circle(surface, chevron_color, (int(cx), int(cy)), 4)
        
        # Center symbol (gate address)
        if is_active:
            pygame.draw.circle(surface, (255, 100, 100), (x, y), 8)
            pygame.draw.circle(surface, (255, 200, 200), (x, y), 4)
        else:
            pygame.draw.circle(surface, (60, 60, 60), (x, y), 6)
    
    def handle_click(self, mouse_pos):
        """Check if button was clicked."""
        return self.button_rect.collidepoint(mouse_pos)


class FactionPowerEffect:
    """Visual effect for Iris Power activation."""
    def __init__(self, faction, center_x, center_y, screen_width, screen_height):
        self.faction = faction
        self.center_x = center_x
        self.center_y = center_y
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.elapsed = 0
        self.duration = 2000  # 2 seconds
        self.finished = False
    
    def update(self, dt):
        """Update effect animation."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
        return not self.finished
    
    def get_progress(self):
        """Get animation progress (0.0 to 1.0)."""
        return min(1.0, self.elapsed / self.duration)
    
    def draw(self, surface):
        """Draw the effect. Override for faction-specific visuals."""
        progress = self.get_progress()
        
        if self.faction == "Tau'ri":
            self.draw_iris_deployment(surface, progress)
        elif self.faction == "Goa'uld":
            self.draw_sarcophagus_revival(surface, progress)
        elif self.faction == "Lucian Alliance":
            self.draw_naquadah_explosion(surface, progress)
        elif self.faction == "Jaffa Rebellion":
            self.draw_teltak_delivery(surface, progress)
        elif self.faction == "Asgard":
            self.draw_hologram_swap(surface, progress)
    
    def draw_iris_deployment(self, surface, progress):
        """Tau'ri - GATE SHUTDOWN - Fire explosions destroying strongest units!"""
        # Multiple fiery explosions (one for each row)
        explosion_positions = [
            (self.screen_width // 4, self.screen_height // 3),      # Left row
            (self.screen_width // 2, self.screen_height // 3),      # Center row
            (3 * self.screen_width // 4, self.screen_height // 3),  # Right row
        ]
        
        for pos_x, pos_y in explosion_positions:
            # Expanding fireball
            if progress < 0.7:
                explosion_radius = int(150 * progress * 1.5)
                
                # Multiple rings for depth
                for ring in range(5):
                    radius = explosion_radius - ring * 20
                    if radius > 0:
                        alpha = int(200 * (1 - progress))
                        
                        # Fire colors: white center -> yellow -> orange -> red
                        if ring == 0:
                            color = (255, 255, 255, alpha)  # White hot center
                        elif ring == 1:
                            color = (255, 255, 100, alpha)  # Yellow
                        elif ring == 2:
                            color = (255, 180, 50, alpha)   # Orange
                        else:
                            color = (255, 100, 50, alpha)   # Red
                        
                        explosion_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(explosion_surf, color, (radius, radius), radius)
                        surface.blit(explosion_surf, (pos_x - radius, pos_y - radius))
            
            # Smoke/debris particles
            if progress > 0.4:
                for _ in range(10):
                    particle_progress = (progress - 0.4) / 0.6
                    offset_x = random.randint(-100, 100) * particle_progress
                    offset_y = random.randint(-50, 50) * particle_progress - 100 * particle_progress
                    particle_size = random.randint(3, 8)
                    alpha = int(150 * (1 - particle_progress))
                    
                    particle_surf = pygame.Surface((particle_size * 2, particle_size * 2), pygame.SRCALPHA)
                    color = (100, 100, 100, alpha)  # Dark smoke
                    pygame.draw.circle(particle_surf, color, (particle_size, particle_size), particle_size)
                    surface.blit(particle_surf, (int(pos_x + offset_x - particle_size), 
                                                int(pos_y + offset_y - particle_size)))
    
    def draw_sarcophagus_revival(self, surface, progress):
        """Goa'uld - Golden energy stream from leader to discard pile."""
        # Golden beam
        beam_alpha = int(200 * math.sin(progress * math.pi))
        if beam_alpha > 0:
            # Draw beam from top center (leader area) to multiple points on board
            start_x = self.center_x
            start_y = 100
            
            for i in range(2):
                end_x = self.center_x - 200 + (i * 400)
                end_y = self.center_y
                
                # Multiple beam layers for glow effect
                for width in range(10, 0, -2):
                    alpha = beam_alpha * (width / 10)
                    beam_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                    pygame.draw.line(beam_surface, (255, 215, 0, int(alpha)), 
                                   (start_x, start_y), (end_x, end_y), width)
                    surface.blit(beam_surface, (0, 0))
                
                # Energy particle at end
                particle_radius = int(20 + 10 * math.sin(progress * math.pi * 4))
                particle_surface = pygame.Surface((particle_radius * 2, particle_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(particle_surface, (255, 215, 0, beam_alpha), 
                                 (particle_radius, particle_radius), particle_radius)
                surface.blit(particle_surface, (end_x - particle_radius, end_y - particle_radius))
    
    def draw_naquadah_explosion(self, surface, progress):
        """Lucian Alliance - Green energy wave expanding from center."""
        # Expanding shockwave
        wave_radius = int(50 + progress * 600)
        wave_alpha = int(200 * (1 - progress))
        
        if wave_alpha > 0:
            # Green shockwave rings
            for i in range(3):
                offset = i * 50
                radius = wave_radius - offset
                if radius > 0:
                    wave_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(wave_surface, (50, 255, 50, wave_alpha // (i + 1)), 
                                     (radius, radius), radius, width=5)
                    surface.blit(wave_surface, (self.center_x - radius, self.center_y - radius))
            
            # Distortion effect (visual glitch)
            if progress < 0.5:
                glitch_alpha = int(100 * (0.5 - progress) * 2)
                glitch_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                glitch_surface.fill((50, 255, 50, glitch_alpha))
                surface.blit(glitch_surface, (0, 0))
    
    def draw_teltak_delivery(self, surface, progress):
        """Jaffa Rebellion - Tel'tak ship delivers 3 cards from above."""
        # Ship enters from top and descends
        ship_start_y = -200
        ship_end_y = self.center_y - 100
        ship_y = int(ship_start_y + progress * (ship_end_y - ship_start_y))
        ship_x = self.center_x
        
        # Draw large Tel'tak ship (pyramid-ish shape)
        ship_width = 200
        ship_height = 120
        
        # Ship becomes fully visible as it descends
        ship_alpha = int(255 * min(1.0, progress * 2))
        if ship_alpha > 0:
            ship_surface = pygame.Surface((ship_width, ship_height), pygame.SRCALPHA)
            
            # Main ship body (wide triangle/pyramid)
            ship_points = [
                (ship_width // 2, 0),           # Top
                (ship_width, ship_height // 2),  # Right
                (ship_width // 2, ship_height), # Bottom  
                (0, ship_height // 2)            # Left
            ]
            # Dark brown/grey ship
            pygame.draw.polygon(ship_surface, (80, 70, 60, ship_alpha), ship_points)
            pygame.draw.polygon(ship_surface, (100, 90, 70, ship_alpha), ship_points, 3)
            
            # Cloaking shimmer effect
            shimmer_alpha = int(80 * abs(math.sin(progress * math.pi * 4)))
            if shimmer_alpha > 0:
                shimmer_surface = pygame.Surface((ship_width, ship_height), pygame.SRCALPHA)
                pygame.draw.polygon(shimmer_surface, (150, 200, 255, shimmer_alpha), ship_points)
                ship_surface.blit(shimmer_surface, (0, 0))
            
            surface.blit(ship_surface, (ship_x - ship_width // 2, ship_y))
        
        # Big "REBEL ALLIANCE AID" text at top
        if progress > 0.2:
            text_alpha = int(255 * min(1.0, (progress - 0.2) * 2))
            title_font = pygame.font.SysFont("Arial", 64, bold=True)
            title_text = title_font.render("REBEL ALLIANCE AID", True, (200, 140, 50))
            title_text.set_alpha(text_alpha)
            title_rect = title_text.get_rect(center=(self.center_x, 100))
            surface.blit(title_text, title_rect)
        
        # Draw 3 cards being delivered
        if progress > 0.5:
            card_progress = (progress - 0.5) / 0.5  # 0 to 1 over last half
            card_width = 80
            card_height = 120
            
            # Cards drop down from ship
            card_start_y = ship_y + ship_height
            card_end_y = self.screen_height - 400
            card_y = int(card_start_y + card_progress * (card_end_y - card_start_y))
            
            # Draw 3 cards spread out
            for i in range(3):
                card_x = self.center_x - 150 + i * 150
                
                # Card back (glowing)
                card_rect = pygame.Rect(card_x - card_width // 2, card_y, card_width, card_height)
                
                # Glow around card
                glow_size = card_width + 20
                glow_alpha = int(150 * math.sin(card_progress * math.pi))
                if glow_alpha > 0:
                    glow_surface = pygame.Surface((glow_size, card_height + 20), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surface, (255, 215, 0, glow_alpha), 
                                   (0, 0, glow_size, card_height + 20), border_radius=10)
                    surface.blit(glow_surface, (card_x - glow_size // 2, card_y - 10))
                
                # Card itself
                pygame.draw.rect(surface, (50, 70, 100), card_rect, border_radius=8)
                pygame.draw.rect(surface, (200, 140, 50), card_rect, 4, border_radius=8)
                
                # Card number
                card_font = pygame.font.SysFont("Arial", 48, bold=True)
                card_num = card_font.render(str(i + 1), True, (255, 215, 0))
                card_num_rect = card_num.get_rect(center=card_rect.center)
                surface.blit(card_num, card_num_rect)
        
        # Subtitle at bottom
        if progress > 0.4:
            subtitle_alpha = int(255 * min(1.0, (progress - 0.4) * 2))
            subtitle_font = pygame.font.SysFont("Arial", 32)
            subtitle_text = subtitle_font.render("Draw 3 cards, discard 3 random cards", True, (180, 180, 180))
            subtitle_text.set_alpha(subtitle_alpha)
            subtitle_rect = subtitle_text.get_rect(center=(self.center_x, self.screen_height - 100))
            surface.blit(subtitle_text, subtitle_rect)
    
    def draw_hologram_swap(self, surface, progress):
        """Asgard - Blue transference lattice effect."""
        # Two target locations (enemy units being swapped)
        target1_x = self.screen_width // 3
        target1_y = self.center_y
        target2_x = 2 * self.screen_width // 3
        target2_y = self.center_y
        
        lattice_alpha = int(200 * math.sin(progress * math.pi))
        
        if lattice_alpha > 0:
            # Blue lattice boxes around targets
            for tx, ty in [(target1_x, target1_y), (target2_x, target2_y)]:
                lattice_size = 120
                lattice_surface = pygame.Surface((lattice_size, lattice_size), pygame.SRCALPHA)
                
                # Draw grid pattern
                grid_spacing = 15
                for i in range(0, lattice_size, grid_spacing):
                    pygame.draw.line(lattice_surface, (100, 200, 255, lattice_alpha), 
                                   (i, 0), (i, lattice_size), 1)
                    pygame.draw.line(lattice_surface, (100, 200, 255, lattice_alpha), 
                                   (0, i), (lattice_size, i), 1)
                
                # Border
                pygame.draw.rect(lattice_surface, (150, 220, 255, lattice_alpha), 
                               lattice_surface.get_rect(), width=3)
                
                surface.blit(lattice_surface, (tx - lattice_size // 2, ty - lattice_size // 2))
            
            # Beam connecting the two targets (swap visualization)
            if progress > 0.3:
                beam_alpha = int(lattice_alpha * (progress - 0.3) / 0.7)
                beam_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                pygame.draw.line(beam_surface, (150, 220, 255, beam_alpha), 
                               (target1_x, target1_y), (target2_x, target2_y), 8)
                surface.blit(beam_surface, (0, 0))
                
                # Particles moving along beam
                for i in range(5):
                    particle_progress = (progress + i * 0.2) % 1.0
                    px = int(target1_x + (target2_x - target1_x) * particle_progress)
                    py = int(target1_y + (target2_y - target1_y) * particle_progress)
                    pygame.draw.circle(surface, (200, 230, 255, beam_alpha), (px, py), 5)


# === SPECIAL FACTION-SPECIFIC ABILITIES ===
# These are separate from Faction Powers (once-per-game abilities)

class RingTransportation:
    """Goa'uld Ring Transportation - Return a close combat unit from board to hand once per round.
    Features authentic Stargate-style 5-ring animation (4 seconds total)."""
    def __init__(self):
        self.available = True
        self.used_this_round = False
        self.animation_in_progress = False
        self.selected_card = None
        self.target_card = None
    
    def can_use(self):
        """Check if rings can be used."""
        return self.available and not self.used_this_round and not self.animation_in_progress
    
    def use(self, card_to_return):
        """Use ring transportation to return a card to hand."""
        if not self.can_use():
            return False
        
        self.target_card = card_to_return
        self.used_this_round = True
        self.animation_in_progress = True
        return True
    
    def complete_animation(self):
        """Called when animation completes."""
        self.animation_in_progress = False
        self.target_card = None
    
    def reset_round(self):
        """Reset for new round - can use again each round."""
        self.available = True
        self.used_this_round = False
        self.animation_in_progress = False
        self.selected_card = None
        self.target_card = None


class RingTransportAnimation:
    """Animation for Goa'uld Ring Transportation - authentic Stargate-style rings."""
    def __init__(self, card, start_pos, end_pos, screen_width, screen_height):
        self.card = card
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        self.elapsed = 0
        self.duration = 4000  # 4 seconds total for dramatic effect
        self.phase = "descending"  # descending, activating, ascending
        self.phase_timer = 0
        
        # Ring properties - larger and more dramatic
        self.ring_radius = 80  # Increased from 60
        self.ring_thickness = 6  # Thicker rings
        self.ring_positions = []
        self.ring_opacities = [0, 0, 0, 0, 0]  # FIVE rings like the show!
        self.finished = False
        
        # Initialize ring positions (start above card) - 5 rings stacked
        center_x = self.start_x
        for i in range(5):
            y_offset = -300 - i * 60  # Tighter spacing
            self.ring_positions.append([center_x, self.start_y + y_offset])
    
    def update(self, dt):
        """Update ring animation."""
        self.elapsed += dt
        self.phase_timer += dt
        
        if self.phase == "descending":
            # Rings descend from above - SLOWER for dramatic effect
            if self.phase_timer < 1500:  # 1.5 seconds descent
                for i in range(5):
                    start_y = self.start_y - 300 - i * 60
                    target_y = self.start_y - 80 + i * 20  # Stack tighter
                    t = min(1.0, self.phase_timer / 1500.0)
                    
                    # Smooth descent with ease-out
                    current_y = start_y + (target_y - start_y) * self.ease_out_cubic(t)
                    self.ring_positions[i][1] = current_y
                    
                    # Fade in rings sequentially for cascade effect
                    ring_delay = i * 0.15  # Each ring starts fading 0.15s after previous
                    if t > ring_delay:
                        fade_progress = min(1.0, (t - ring_delay) / (1.0 - ring_delay))
                        self.ring_opacities[i] = min(255, int(255 * fade_progress))
            else:
                self.phase = "activating"
                self.phase_timer = 0
        
        elif self.phase == "activating":
            # Rings glow and pulse - LONGER activation
            if self.phase_timer < 1200:  # 1.2 seconds activation
                # Pulse effect with multiple harmonics for energy feel
                pulse1 = math.sin(self.phase_timer * 0.008) * 0.5 + 0.5
                pulse2 = math.sin(self.phase_timer * 0.015) * 0.3
                combined_pulse = pulse1 + pulse2
                
                for i in range(5):
                    # Different phase offset per ring for wave effect
                    ring_phase = (self.phase_timer + i * 150) * 0.008
                    ring_pulse = math.sin(ring_phase) * 0.5 + 0.5
                    self.ring_opacities[i] = int(180 + 75 * ring_pulse)
            else:
                self.phase = "ascending"
                self.phase_timer = 0
        
        elif self.phase == "ascending":
            # Rings ascend with card - SLOWER for impact
            if self.phase_timer < 1300:  # 1.3 seconds ascent
                # Move rings upward
                for i in range(5):
                    start_y = self.start_y - 80 + i * 20
                    target_y = self.end_y - 300 - i * 60
                    t = min(1.0, self.phase_timer / 1300.0)
                    
                    current_y = start_y + (target_y - start_y) * self.ease_in_cubic(t)
                    self.ring_positions[i][1] = current_y
                    
                    # Fade out rings sequentially (reverse order)
                    ring_delay = (4 - i) * 0.15  # Last ring fades first
                    if t > ring_delay:
                        fade_progress = min(1.0, (t - ring_delay) / (1.0 - ring_delay))
                        self.ring_opacities[i] = int(255 * (1.0 - fade_progress))
                
                # Move card with rings - smooth interpolation
                card_progress = min(1.0, self.phase_timer / 1300.0)
                self.card.rect.x = int(self.start_x + (self.end_x - self.start_x) * card_progress)
                self.card.rect.y = int(self.start_y + (self.end_y - self.start_y) * card_progress)
            else:
                self.finished = True
                return False
        
        return not self.finished
    
    def draw(self, surface):
        """Draw ring transportation animation."""
        if self.finished:
            return
        
        # Draw rings with Stargate-style appearance
        for i, (x, y) in enumerate(self.ring_positions):
            if self.ring_opacities[i] > 0:
                # Create ring surface
                ring_surf = pygame.Surface((self.ring_radius * 2 + 40, self.ring_radius * 2 + 40), pygame.SRCALPHA)
                
                # Goa'uld golden color with slight variation per ring
                hue_shift = i * 10
                ring_color = (min(255, 255 - hue_shift), min(255, 200 - hue_shift), 100, self.ring_opacities[i])
                center = self.ring_radius + 20
                
                # Outer glow (energy field)
                if self.phase == "activating":
                    glow_radius = self.ring_radius + 8
                    for glow_step in range(3):
                        glow_alpha = self.ring_opacities[i] // (3 + glow_step)
                        glow_color = (255, 220, 150, glow_alpha)
                        pygame.draw.circle(ring_surf, glow_color, (center, center), 
                                         glow_radius - glow_step * 2, width=2)
                
                # Main ring - thicker and more solid
                pygame.draw.circle(ring_surf, ring_color, (center, center), 
                                 self.ring_radius, width=self.ring_thickness)
                
                # Inner ring for depth
                inner_ring_color = (255, 230, 180, self.ring_opacities[i] // 2)
                pygame.draw.circle(ring_surf, inner_ring_color, (center, center), 
                                 self.ring_radius - 12, width=3)
                
                # Segmented appearance - 12 segments like Stargate rings
                if self.phase != "ascending":
                    self.draw_ring_segments(ring_surf, center, center, i)
                
                surface.blit(ring_surf, (int(x - self.ring_radius - 20), int(y - self.ring_radius - 20)))
        
        # Draw card during animation (except late ascending phase)
        if self.phase != "ascending" or self.phase_timer < 1000:
            # Add glow around card during activation
            if self.phase == "activating":
                glow_alpha = int(100 + 100 * math.sin(self.elapsed * 0.008))
                glow_surf = pygame.Surface((self.card.rect.width + 40, self.card.rect.height + 40), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (255, 220, 150, glow_alpha), glow_surf.get_rect(), border_radius=15)
                surface.blit(glow_surf, (self.card.rect.x - 20, self.card.rect.y - 20))
            
            surface.blit(self.card.image, self.card.rect)
    
    def draw_ring_segments(self, surface, cx, cy, ring_index):
        """Draw segmented ring appearance like Stargate."""
        num_segments = 12  # 12 segments around the ring
        segment_gap = 8  # Gap between segments in degrees
        
        for i in range(num_segments):
            # Calculate segment arc
            start_angle = (i * 360 / num_segments) + (self.elapsed * 0.03 * (ring_index + 1))
            end_angle = start_angle + (360 / num_segments) - segment_gap
            
            # Draw segment as short arc
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)
            
            # Draw small chevron-like marker at each segment
            marker_angle = math.radians(start_angle + (360 / num_segments / 2))
            marker_x = cx + math.cos(marker_angle) * self.ring_radius
            marker_y = cy + math.sin(marker_angle) * self.ring_radius
            
            # Small rectangular segment marker
            marker_size = 6
            marker_color = (255, 240, 180, self.ring_opacities[ring_index])
            marker_rect = pygame.Rect(marker_x - marker_size//2, marker_y - marker_size//2, 
                                     marker_size, marker_size * 2)
            pygame.draw.rect(surface, marker_color, marker_rect, border_radius=2)
    
    def ease_out_cubic(self, t):
        """Easing function for smooth descent."""
        return 1 - pow(1 - t, 3)
    
    def ease_in_cubic(self, t):
        """Easing function for smooth ascent."""
        return t * t * t
