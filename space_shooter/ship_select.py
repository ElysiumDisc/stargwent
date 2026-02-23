"""Ship selection screen for the space shooter."""

import pygame

from .ship import Ship, SHIP_VARIANTS
from .effects import StarField


class ShipSelectScreen:
    """Ship selection screen before the game with variant support."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.factions = ["Tau'ri", "Goa'uld", "Asgard", "Jaffa Rebellion", "Lucian Alliance"]
        self.selected_index = 0
        self.variant_indices = {f: 0 for f in self.factions}  # Per-faction variant index
        self.starfield = StarField(screen_width, screen_height)

        # Fonts
        self.title_font = pygame.font.SysFont("Arial", 64, bold=True)
        self.faction_font = pygame.font.SysFont("Arial", 36, bold=True)
        self.variant_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.desc_font = pygame.font.SysFont("Arial", 18)
        self.hint_font = pygame.font.SysFont("Arial", 24)

        # Load all variant previews per faction
        self.faction_variants = {}  # faction -> list of {name, image, color, description}
        self.load_previews()

        # Selection rects for click detection
        self.ship_rects = []

    def load_previews(self):
        """Load preview images for all ships and variants."""
        for faction in self.factions:
            faction_lower = faction.lower()
            variants = SHIP_VARIANTS.get(faction_lower, [])
            variant_previews = []
            for vi, vdata in enumerate(variants):
                ship = Ship(0, 0, faction, is_player=True,
                           screen_width=self.screen_width, screen_height=self.screen_height,
                           variant=vi)
                variant_previews.append({
                    'name': vdata["name"],
                    'image': ship.image,
                    'color': ship.laser_color,
                    'description': vdata.get("description", ""),
                })
            if not variant_previews:
                # Fallback for factions without variants
                ship = Ship(0, 0, faction, is_player=True,
                           screen_width=self.screen_width, screen_height=self.screen_height)
                variant_previews.append({
                    'name': faction,
                    'image': ship.image,
                    'color': ship.laser_color,
                    'description': "",
                })
            self.faction_variants[faction] = variant_previews

    def _get_current_variant(self):
        """Get the current faction and variant index."""
        faction = self.factions[self.selected_index]
        vi = self.variant_indices.get(faction, 0)
        return faction, vi

    def _variant_count(self, faction):
        """Get number of variants for a faction."""
        return len(self.faction_variants.get(faction, []))

    def handle_event(self, event):
        """Handle input events. Returns (faction, variant_index) tuple or None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.selected_index = (self.selected_index - 1) % len(self.factions)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.selected_index = (self.selected_index + 1) % len(self.factions)
            elif event.key == pygame.K_UP or event.key == pygame.K_w:
                faction = self.factions[self.selected_index]
                count = self._variant_count(faction)
                if count > 1:
                    self.variant_indices[faction] = (self.variant_indices[faction] - 1) % count
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                faction = self.factions[self.selected_index]
                count = self._variant_count(faction)
                if count > 1:
                    self.variant_indices[faction] = (self.variant_indices[faction] + 1) % count
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                faction, vi = self._get_current_variant()
                return (faction, vi)
            elif event.key == pygame.K_ESCAPE:
                return "exit"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.ship_rects):
                if rect.collidepoint(event.pos):
                    if i == self.selected_index:
                        faction, vi = self._get_current_variant()
                        return (faction, vi)
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

        for i, faction in enumerate(self.factions):
            vi = self.variant_indices.get(faction, 0)
            variants = self.faction_variants.get(faction, [])
            if not variants:
                continue
            preview = variants[vi % len(variants)]

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
                # Scale to fit within box while preserving aspect ratio
                box = ship_size - 40
                iw = preview['image'].get_width()
                ih = preview['image'].get_height()
                if iw > 0 and ih > 0:
                    ratio = min(box / iw, box / ih)
                    sw = max(1, int(iw * ratio))
                    sh = max(1, int(ih * ratio))
                    img = pygame.transform.smoothscale(preview['image'], (sw, sh))
                else:
                    img = preview['image']
                    sw, sh = img.get_width(), img.get_height()
                # Center within the box
                img_x = x + (ship_size - sw) // 2
                img_y = ship_y - sh // 2
                surface.blit(img, (img_x, img_y))

            # Faction name
            name_text = self.faction_font.render(faction, True,
                                                  preview['color'] if is_selected else (180, 180, 180))
            name_x = x + ship_size // 2 - name_text.get_width() // 2
            name_y = ship_y + ship_size // 2 + 15
            surface.blit(name_text, (name_x, name_y))

            # Variant name
            variant_text = self.variant_font.render(preview['name'], True,
                                                     (220, 220, 255) if is_selected else (140, 140, 160))
            vx = x + ship_size // 2 - variant_text.get_width() // 2
            vy = name_y + 35
            surface.blit(variant_text, (vx, vy))

            # Variant dots (if multiple variants)
            num_variants = len(variants)
            if num_variants > 1:
                dot_y = vy + 28
                dot_total_w = num_variants * 12 + (num_variants - 1) * 6
                dot_start_x = x + ship_size // 2 - dot_total_w // 2
                for di in range(num_variants):
                    dx = dot_start_x + di * 18
                    if di == vi:
                        pygame.draw.circle(surface, preview['color'], (dx + 6, dot_y), 6)
                    else:
                        pygame.draw.circle(surface, (80, 80, 100), (dx + 6, dot_y), 4)
                        pygame.draw.circle(surface, (120, 120, 140), (dx + 6, dot_y), 4, 1)

            # Description (selected only)
            if is_selected and preview.get('description'):
                desc_text = self.desc_font.render(preview['description'], True, (160, 160, 180))
                desc_x = x + ship_size // 2 - desc_text.get_width() // 2
                desc_y = vy + (38 if num_variants > 1 else 28)
                surface.blit(desc_text, (desc_x, desc_y))

        # Controls hint
        controls = self.hint_font.render(
            "A/D: faction  |  W/S: variant  |  ENTER: confirm  |  ESC: exit",
            True, (120, 120, 140))
        surface.blit(controls, (self.screen_width // 2 - controls.get_width() // 2,
                               self.screen_height - 60))
