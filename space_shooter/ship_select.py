"""Ship selection screen for the space shooter."""

import pygame

from .ship import Ship
from .effects import StarField


class ShipSelectScreen:
    """Ship selection screen before the game."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]
        self.selected_index = 0
        self.ship_previews = []
        self.starfield = StarField(screen_width, screen_height)

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.faction_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.hint_font = pygame.font.SysFont("Arial", 24)

        # Load ship previews
        self.load_previews()

        # Selection rects for click detection
        self.ship_rects = []

    def load_previews(self):
        """Load preview images for all ships."""
        for faction in self.factions:
            ship = Ship(0, 0, faction, is_player=True,
                       screen_width=self.screen_width, screen_height=self.screen_height)
            self.ship_previews.append({
                'faction': faction,
                'image': ship.image,
                'color': ship.laser_color
            })

    def handle_event(self, event):
        """Handle input events. Returns selected faction or None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.selected_index = (self.selected_index - 1) % len(self.factions)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.selected_index = (self.selected_index + 1) % len(self.factions)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                return self.factions[self.selected_index]
            elif event.key == pygame.K_ESCAPE:
                return "exit"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.ship_rects):
                if rect.collidepoint(event.pos):
                    if i == self.selected_index:
                        return self.factions[self.selected_index]
                    else:
                        self.selected_index = i

        return None

    def draw(self, surface):
        """Draw the ship selection screen."""
        # Background
        surface.fill((5, 5, 20))
        self.starfield.update()
        self.starfield.draw(surface)

        # Title
        title = self.title_font.render("SELECT YOUR SHIP", True, (255, 215, 0))
        surface.blit(title, (self.screen_width // 2 - title.get_width() // 2, 50))

        # Subtitle
        subtitle = self.hint_font.render("Each faction has unique weapons, passives & secondary fire", True, (150, 150, 180))
        surface.blit(subtitle, (self.screen_width // 2 - subtitle.get_width() // 2, 120))

        # Draw ship options
        self.ship_rects = []
        ship_size = 200
        spacing = 50
        total_width = len(self.factions) * ship_size + (len(self.factions) - 1) * spacing
        start_x = (self.screen_width - total_width) // 2
        ship_y = self.screen_height // 2 - 50

        for i, preview in enumerate(self.ship_previews):
            x = start_x + i * (ship_size + spacing)
            rect = pygame.Rect(x, ship_y - ship_size // 2, ship_size, ship_size)
            self.ship_rects.append(rect)

            is_selected = (i == self.selected_index)
            is_hovered = rect.collidepoint(pygame.mouse.get_pos())

            if is_selected:
                glow_rect = rect.inflate(20, 20)
                pygame.draw.rect(surface, (*preview['color'], 150), glow_rect, border_radius=15)
                pygame.draw.rect(surface, preview['color'], rect, 4, border_radius=10)
            elif is_hovered:
                pygame.draw.rect(surface, (80, 80, 100), rect, 2, border_radius=10)

            panel_color = (40, 40, 60) if is_selected else (25, 25, 40)
            pygame.draw.rect(surface, panel_color, rect, border_radius=10)

            if preview['image']:
                img = pygame.transform.smoothscale(preview['image'], (ship_size - 40, ship_size - 40))
                img_x = x + 20
                img_y = ship_y - (ship_size - 40) // 2
                surface.blit(img, (img_x, img_y))

            name_text = self.faction_font.render(preview['faction'], True,
                                                  preview['color'] if is_selected else (180, 180, 180))
            name_x = x + ship_size // 2 - name_text.get_width() // 2
            name_y = ship_y + ship_size // 2 + 15
            surface.blit(name_text, (name_x, name_y))

        # Controls hint
        controls = self.hint_font.render(
            "< > or A/D to select  |  ENTER or CLICK to confirm  |  ESC to exit",
            True, (120, 120, 140))
        surface.blit(controls, (self.screen_width // 2 - controls.get_width() // 2,
                               self.screen_height - 60))
