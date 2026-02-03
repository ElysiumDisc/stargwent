"""
Iris Power System for StarGwent
Each faction has a unique, once-per-round, cinematic ability
"""
import pygame
import math
import random
from abilities import is_hero


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

        # Play iris sound effect
        from sound_manager import get_sound_manager
        sound_manager = get_sound_manager()
        sound_manager.play_iris_sound(volume=0.7)

        opponent = game.player2 if player == game.player1 else game.player1
        destroyed_cards = []

        # Find and destroy strongest non-Hero in each row
        for row_name in ["close", "ranged", "siege"]:
            row_cards = opponent.board.get(row_name, [])
            if not row_cards:
                continue

            # Find strongest non-Legendary Commander
            non_hero_cards = [c for c in row_cards if not is_hero(c)]
            if non_hero_cards:
                strongest = max(non_hero_cards, key=lambda c: c.displayed_power)
                opponent.board[row_name].remove(strongest)
                opponent.discard_pile.append(strongest)
                destroyed_cards.append(strongest)

        # Log each destroyed card to history
        owner_label = "player" if player == game.player1 else "opponent"
        for card in destroyed_cards:
            game.add_history_event(
                "destroy",
                f"Iris destroyed {card.name}",
                owner_label,
                card_ref=card,
                icon="🔥"
            )

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
                      if not is_hero(c) 
                      and c.row in ["close", "ranged", "siege", "agile"]]
        
        if not valid_cards:
            return False
        
        # Revive up to 2 random cards
        num_to_revive = min(2, len(valid_cards))
        rng = getattr(game, "rng", random)
        revived_cards = rng.sample(valid_cards, num_to_revive)
        
        for card in revived_cards:
            player.discard_pile.remove(card)
            # Place in appropriate row
            target_row = card.row if card.row != "agile" else rng.choice(["close", "ranged"])
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
                    if not is_hero(card):
                        # Reduce BASE power by 5 (so it persists through calculate_score)
                        old_power = card.power
                        card.power = max(0, card.power - 5)
                        card.displayed_power = card.power
                        damaged_count += 1
        
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

        # Log the draw
        owner_label = "player" if player == game.player1 else "opponent"
        game.add_history_event(
            "ability",
            f"{player.name} drew 3 cards (Rebel Alliance Aid)",
            owner_label,
            icon="🃏"
        )

        # Discard 3 random cards from hand
        discarded_cards = []
        if len(player.hand) >= 3:
            import random
            rng = getattr(game, "rng", random)
            cards_to_discard = rng.sample(player.hand, 3)
            for card in cards_to_discard:
                player.hand.remove(card)
                player.discard_pile.append(card)
                discarded_cards.append(card)
        else:
            # If fewer than 3 cards, discard all
            while player.hand:
                card = player.hand.pop()
                player.discard_pile.append(card)
                discarded_cards.append(card)

        # Log each discarded card to history
        for card in discarded_cards:
            game.add_history_event(
                "discard",
                f"{player.name} discarded {card.name}",
                owner_label,
                card_ref=card,
                icon="🗑️"
            )

        return True


class AsgardFactionPower(FactionPower):
    """Holographic Decoy - Swap opponent's close combat and ranged rows."""
    def __init__(self):
        super().__init__(
            "Holographic Decoy",
            "Swap opponent's entire close combat and ranged rows",
            "Asgard"
        )
    
    def activate(self, game, player):
        if not super().activate(game, player):
            return False
        
        # Simply swap opponent's close combat row with their ranged row
        opponent = game.player2 if player == game.player1 else game.player1
        
        # Swap the entire rows
        opponent.board["close"], opponent.board["ranged"] = opponent.board["ranged"], opponent.board["close"]

        # Recalculate scores after swap (row-specific bonuses might have changed)
        opponent.calculate_score()
        player.calculate_score()

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
        """Tau'ri - GATE SHUTDOWN - Iris closing animation over Stargate!"""
        # Big iris closing in center of screen
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2

        # Iris parameters
        num_blades = 20  # Number of iris segments
        max_radius = min(self.screen_width, self.screen_height) // 2 + 100

        # Iris closes from open to shut
        # progress 0.0 = open, progress 0.5 = closed, progress 1.0 = opens slightly then fades
        if progress < 0.5:
            # Closing phase
            close_progress = progress * 2  # 0 to 1
            inner_radius = int(max_radius * (1 - close_progress))
        elif progress < 0.8:
            # Stay closed
            inner_radius = 0
        else:
            # Slight fade out
            inner_radius = 0

        # Draw outer ring (Stargate rim)
        rim_alpha = int(255 * min(1.0, progress * 4) * (1 - max(0, (progress - 0.8) * 5)))
        if rim_alpha > 0:
            rim_surf = pygame.Surface((max_radius * 2 + 40, max_radius * 2 + 40), pygame.SRCALPHA)
            # Outer rim glow
            pygame.draw.circle(rim_surf, (100, 150, 200, rim_alpha // 3),
                             (max_radius + 20, max_radius + 20), max_radius + 15, width=15)
            # Main rim
            pygame.draw.circle(rim_surf, (60, 80, 120, rim_alpha),
                             (max_radius + 20, max_radius + 20), max_radius, width=20)
            surface.blit(rim_surf, (center_x - max_radius - 20, center_y - max_radius - 20))

        # Draw iris blades
        blade_alpha = int(255 * min(1.0, progress * 3) * (1 - max(0, (progress - 0.8) * 5)))
        if blade_alpha > 0:
            iris_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

            for i in range(num_blades):
                angle = (i / num_blades) * 2 * math.pi
                next_angle = ((i + 1) / num_blades) * 2 * math.pi

                # Calculate blade shape (triangular segments)
                # Outer points
                outer_x1 = center_x + int(max_radius * math.cos(angle))
                outer_y1 = center_y + int(max_radius * math.sin(angle))
                outer_x2 = center_x + int(max_radius * math.cos(next_angle))
                outer_y2 = center_y + int(max_radius * math.sin(next_angle))

                # Inner points (where iris closes to)
                mid_angle = (angle + next_angle) / 2
                inner_x = center_x + int(inner_radius * math.cos(mid_angle))
                inner_y = center_y + int(inner_radius * math.sin(mid_angle))

                # Blade color - titanium gray with slight variation
                shade = 140 + (i % 3) * 15
                blade_color = (shade, shade, shade + 10, blade_alpha)

                # Draw blade
                points = [(outer_x1, outer_y1), (outer_x2, outer_y2), (inner_x, inner_y)]
                pygame.draw.polygon(iris_surf, blade_color, points)

                # Edge highlight
                edge_color = (180, 180, 190, blade_alpha // 2)
                pygame.draw.line(iris_surf, edge_color, (outer_x1, outer_y1), (inner_x, inner_y), 2)

            surface.blit(iris_surf, (0, 0))

        # Central flash when fully closed
        if 0.45 < progress < 0.6:
            flash_progress = (progress - 0.45) / 0.15
            flash_alpha = int(200 * math.sin(flash_progress * math.pi))
            flash_radius = int(50 + 30 * math.sin(flash_progress * math.pi))

            flash_surf = pygame.Surface((flash_radius * 2, flash_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (200, 220, 255, flash_alpha),
                             (flash_radius, flash_radius), flash_radius)
            surface.blit(flash_surf, (center_x - flash_radius, center_y - flash_radius))

        # Text overlay
        if 0.3 < progress < 0.9:
            text_alpha = int(255 * min(1.0, (progress - 0.3) * 5) * (1 - max(0, (progress - 0.7) * 5)))
            font = pygame.font.SysFont("Arial", 60, bold=True)
            text = font.render("IRIS ENGAGED", True, (200, 220, 255))
            text_surf = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_surf.fill((0, 0, 0, 0))
            text_surf.blit(text, (0, 0))
            text_surf.set_alpha(text_alpha)
            text_rect = text.get_rect(center=(center_x, center_y + max_radius + 80))
            surface.blit(text_surf, text_rect)
    
    def draw_sarcophagus_revival(self, surface, progress):
        """Goa'uld - Sarcophagus opens and golden energy stream flows."""
        # Draw Sarcophagus
        sarc_width = 160
        sarc_height = 240
        sarc_x = self.center_x - sarc_width // 2
        sarc_y = self.center_y - 100
        
        # Calculate lid opening state
        # 0.0-0.3: Closed
        # 0.3-0.5: Opens
        # 0.5-0.8: Open (Energy flows)
        # 0.8-1.0: Closes
        
        lid_offset = 0
        if 0.3 <= progress < 0.5:
            lid_offset = (progress - 0.3) / 0.2 * 60  # Move 60px to side
        elif 0.5 <= progress < 0.8:
            lid_offset = 60
        elif 0.8 <= progress:
            lid_offset = 60 - (progress - 0.8) / 0.2 * 60
            
        # Draw Sarcophagus Base (Dark gold/bronze)
        pygame.draw.rect(surface, (100, 80, 20), (sarc_x, sarc_y, sarc_width, sarc_height), border_radius=20)
        pygame.draw.rect(surface, (160, 140, 40), (sarc_x, sarc_y, sarc_width, sarc_height), width=5, border_radius=20)
        
        # Draw Inner Glow (when open)
        if lid_offset > 5:
            inner_rect = pygame.Rect(sarc_x + 10, sarc_y + 10, sarc_width - 20, sarc_height - 20)
            glow_intensity = min(255, int(abs(math.sin(progress * 10)) * 255))
            pygame.draw.rect(surface, (255, 255, 200), inner_rect, border_radius=15)
            
            # White hot center
            center_rect = inner_rect.inflate(-40, -40)
            pygame.draw.rect(surface, (255, 255, 255), center_rect, border_radius=10)
        
        # Draw Lid (Split in two or slide off - let's do slide right)
        lid_rect = pygame.Rect(sarc_x + lid_offset, sarc_y, sarc_width, sarc_height)
        # Detailed Lid
        pygame.draw.rect(surface, (180, 150, 50), lid_rect, border_radius=20)
        # Ornaments
        pygame.draw.rect(surface, (120, 100, 30), lid_rect.inflate(-20, -20), width=3, border_radius=10)
        # Pharaoh face shape (abstract)
        pygame.draw.circle(surface, (200, 180, 60), (lid_rect.centerx, lid_rect.y + 60), 30) # Head
        pygame.draw.rect(surface, (50, 100, 200), (lid_rect.centerx - 25, lid_rect.y + 60, 50, 40)) # Headdress stripes
        
        # Golden beam (only when open)
        if lid_offset > 30:
            beam_alpha = int(200 * math.sin(progress * math.pi))
            if beam_alpha > 0:
                # Draw beam from sarcophagus to discard pile area (or just up)
                start_x = sarc_x + sarc_width // 2
                start_y = sarc_y + 40
                
                # Beam flowing out
                for i in range(2):
                    end_x = self.center_x - 200 + (i * 400)
                    end_y = self.screen_height - 100
                    
                    # Energy curve
                    points = []
                    for t in range(11):
                        ft = t / 10.0
                        px = start_x + (end_x - start_x) * ft
                        py = start_y + (end_y - start_y) * ft + math.sin(ft * math.pi) * -100
                        points.append((px, py))
                    
                    if len(points) > 1:
                        pygame.draw.lines(surface, (255, 215, 0, beam_alpha), False, points, 5)

        # Text overlay
        if 0.3 < progress < 0.9:
            text_alpha = int(255 * min(1.0, (progress - 0.3) * 5) * (1 - max(0, (progress - 0.7) * 5)))
            font = pygame.font.SysFont("Arial", 60, bold=True)
            text = font.render("SARCOPHAGUS REVIVAL", True, (255, 215, 0))
            text_surf = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_surf.fill((0, 0, 0, 0))
            text_surf.blit(text, (0, 0))
            text_surf.set_alpha(text_alpha)
            text_rect = text.get_rect(center=(self.center_x, self.center_y + 150))
            surface.blit(text_surf, text_rect)
    
    def draw_naquadah_explosion(self, surface, progress):
        """Lucian Alliance - Green energy wave expanding from center with EM interference."""
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

            # Scanline / Glitch effect simulating EM interference
            num_scanlines = 20
            for i in range(num_scanlines):
                # Random horizontal lines
                line_y = random.randint(0, self.screen_height)
                line_h = random.randint(2, 10)
                # Random horizontal offset
                x_offset = random.randint(-20, 20)
                
                # Draw a semi-transparent colored strip
                line_surf = pygame.Surface((self.screen_width, line_h), pygame.SRCALPHA)
                line_color = random.choice([(50, 255, 50), (100, 255, 100), (200, 255, 200)])
                line_surf.fill((*line_color, random.randint(50, 150)))
                
                surface.blit(line_surf, (x_offset, line_y))
                
        # Text overlay
        if 0.2 < progress < 0.9:
            text_alpha = int(255 * min(1.0, (progress - 0.2) * 5) * (1 - max(0, (progress - 0.7) * 5)))
            font = pygame.font.SysFont("Arial", 60, bold=True)
            text = font.render("NAQUADAH ASSAULT", True, (50, 255, 50))
            text_surf = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_surf.fill((0, 0, 0, 0))
            text_surf.blit(text, (0, 0))
            text_surf.set_alpha(text_alpha)
            # Jitter text position
            jitter_x = random.randint(-5, 5)
            jitter_y = random.randint(-5, 5)
            text_rect = text.get_rect(center=(self.center_x + jitter_x, self.center_y + jitter_y))
            surface.blit(text_surf, text_rect)
    
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
        """Asgard - De-materialize and re-materialize cards with white light."""
        # Two target locations (center of rows essentially)
        target1_x = self.screen_width // 2
        target1_y = self.center_y - 100 # Ranged row approx
        target2_x = self.screen_width // 2
        target2_y = self.center_y + 100 # Close row approx
        
        # Phase 1: Beam Up (0.0 to 0.4)
        # Phase 2: Transfer/Swap (0.4 to 0.6)
        # Phase 3: Beam Down (0.6 to 1.0)
        
        if progress < 0.4:
            # Beam intensity ramps up
            beam_alpha = int((progress / 0.4) * 255)
            beam_width = int(100 + progress * 50)
        elif progress < 0.6:
            # Full whiteout transition
            beam_alpha = 255
            beam_width = 120
        else:
            # Beam intensity ramps down
            beam_alpha = int(((1.0 - progress) / 0.4) * 255)
            beam_width = int(120 - (progress - 0.6) * 50)
            
        if beam_alpha > 0:
            # Draw intense white beams at both locations
            for tx, ty in [(target1_x, target1_y), (target2_x, target2_y)]:
                # Main beam column
                beam_rect = pygame.Rect(tx - beam_width // 2, 0, beam_width, self.screen_height)
                
                # Create beam surface with gradient alpha for soft edges
                beam_surf = pygame.Surface((beam_width, self.screen_height), pygame.SRCALPHA)
                
                # Core white beam
                pygame.draw.rect(beam_surf, (255, 255, 255, min(255, beam_alpha)), 
                               beam_surf.get_rect())
                
                # Add outer glow
                glow_rect = beam_surf.get_rect().inflate(40, 0)
                # (Simple rect fill for core is fast, glow handled by alpha blend)
                
                surface.blit(beam_surf, (tx - beam_width // 2, 0))
                
                # Sparkles/Data particles floating up
                if progress < 0.5:
                    # Dematerializing
                    for _ in range(10):
                        px = tx + random.randint(-beam_width//2, beam_width//2)
                        py = ty + random.randint(-100, 100) - (progress * 500)
                        pygame.draw.circle(surface, (200, 230, 255, beam_alpha), (px, int(py)), random.randint(2, 5))
                else:
                    # Rematerializing
                    for _ in range(10):
                        px = tx + random.randint(-beam_width//2, beam_width//2)
                        py = ty - 400 + ((progress - 0.5) * 800) + random.randint(-100, 100)
                        pygame.draw.circle(surface, (200, 230, 255, beam_alpha), (px, int(py)), random.randint(2, 5))

        # Flash screen white at swap moment (0.5)
        if 0.45 < progress < 0.55:
            flash_alpha = int(200 * (1.0 - abs(progress - 0.5) * 20)) # Peak at 0.5
            flash_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, flash_alpha))
            surface.blit(flash_surf, (0, 0))

        # Text overlay
        if 0.2 < progress < 0.9:
            text_alpha = int(255 * min(1.0, (progress - 0.2) * 5) * (1 - max(0, (progress - 0.7) * 5)))
            font = pygame.font.SysFont("Arial", 60, bold=True)
            text = font.render("ASGARD TRANSPORTER", True, (200, 230, 255))
            text_surf = pygame.Surface(text.get_size(), pygame.SRCALPHA)
            text_surf.fill((0, 0, 0, 0))
            text_surf.blit(text, (0, 0))
            text_surf.set_alpha(text_alpha)
            text_rect = text.get_rect(center=(self.center_x, self.center_y))
            surface.blit(text_surf, text_rect)


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
