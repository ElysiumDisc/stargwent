"""
DHD (Dial Home Device) Button System
Provides enhanced button rendering with Stargate-inspired visual effects:
- Glowing pulsing inner radial gradients
- Edge lighting with 3D etched look
- Active state depression with kawoosh flash
- Screen shake effect on activation
"""

import pygame
import math
import random


class DHDButton:
    """Enhanced button with Ancient DHD (Dial Home Device) styling."""
    
    def __init__(self, rect, text, font):
        self.rect = rect
        self.text = text
        self.font = font
        self.is_hovered = False
        self.is_pressed = False
        self.glow_phase = random.random() * math.tau
        self.activation_time = 0
        self.activation_duration = 500  # ms
        
        # Colors
        self.base_color = (40, 60, 100)
        self.hover_color = (60, 90, 150)
        self.selected_color = (80, 120, 180)
        self.glow_color = (0, 255, 255)  # Cyan
        self.edge_light_color = (150, 230, 255)
        
    def update(self, dt, is_hovered, is_selected):
        """Update button animation state."""
        self.is_hovered = is_hovered or is_selected
        self.glow_phase = (self.glow_phase + dt * 0.003) % math.tau
        
        if self.activation_time > 0:
            self.activation_time = max(0, self.activation_time - dt)
    
    def activate(self):
        """Trigger activation animation (kawoosh effect)."""
        self.activation_time = self.activation_duration
        self.is_pressed = True
    
    def draw(self, surface, is_selected=False):
        """Draw the DHD button with all effects."""
        rect = self.rect.copy()
        
        # Active state depression
        if self.activation_time > 0:
            progress = 1.0 - (self.activation_time / self.activation_duration)
            if progress < 0.2:  # First 20% - depress
                offset = int(5 * (progress / 0.2))
                rect.y += offset
            else:  # Rest - return to normal
                offset = int(5 * (1.0 - (progress - 0.2) / 0.8))
                rect.y += offset
        
        # Determine base color
        if is_selected:
            base_color = self.selected_color
        elif self.is_hovered:
            base_color = self.hover_color
        else:
            base_color = self.base_color
        
        # Create button surface with alpha for layering effects
        button_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        # Inner glow (radial gradient pulse)
        if self.is_hovered:
            pulse = 0.6 + 0.4 * math.sin(self.glow_phase * 2)
            self._draw_radial_gradient(button_surf, rect.size, base_color, pulse)
        else:
            button_surf.fill((*base_color, 255))
        
        # Draw to main surface
        pygame.draw.rect(surface, base_color, rect, border_radius=10)
        surface.blit(button_surf, rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)
        
        # Edge lighting (1px cyan highlight top-left)
        if self.is_hovered or is_selected:
            edge_intensity = int(255 * (0.7 + 0.3 * math.sin(self.glow_phase)))
            edge_color = (*self.edge_light_color[:3], edge_intensity)
            
            # Top edge
            pygame.draw.line(surface, edge_color,
                           (rect.left + 10, rect.top + 1),
                           (rect.right - 10, rect.top + 1), 2)
            # Left edge
            pygame.draw.line(surface, edge_color,
                           (rect.left + 1, rect.top + 10),
                           (rect.left + 1, rect.bottom - 10), 2)
        
        # Border
        if is_selected:
            border_color = (100, 200, 255)
            border_width = 4
        else:
            border_color = (100, 100, 120)
            border_width = 2
        pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=10)
        
        # Kawoosh flash effect during activation
        if self.activation_time > 0:
            flash_progress = 1.0 - (self.activation_time / self.activation_duration)
            if flash_progress < 0.3:  # Flash during first 30%
                flash_alpha = int(200 * (1.0 - flash_progress / 0.3))
                flash_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
                flash_surf.fill((200, 230, 255, flash_alpha))
                surface.blit(flash_surf, rect.topleft, special_flags=pygame.BLEND_ADD)
        
        # Motion blur on text during kawoosh peak
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        
        if self.activation_time > 0:
            progress = 1.0 - (self.activation_time / self.activation_duration)
            if 0.15 < progress < 0.35:  # Peak kawoosh
                # Create motion blur by drawing text multiple times with slight offset
                blur_alpha = int(80 * math.sin((progress - 0.15) / 0.2 * math.pi))
                for offset in range(-3, 4, 1):
                    blur_surf = self.font.render(self.text, True, (255, 255, 255))
                    blur_surf.set_alpha(blur_alpha // 2)
                    blur_rect = text_rect.copy()
                    blur_rect.x += offset
                    surface.blit(blur_surf, blur_rect)
        
        surface.blit(text_surf, text_rect)
    
    def _draw_radial_gradient(self, surface, size, base_color, pulse):
        """Draw a radial gradient with pulsing effect."""
        center = (size[0] // 2, size[1] // 2)
        max_radius = max(size[0], size[1]) // 2
        
        for i in range(max_radius, 0, -3):
            progress = i / max_radius
            alpha = int(255 * progress * pulse * 0.3)
            r = min(255, int(base_color[0] * (1 + 0.3 * (1 - progress))))
            g = min(255, int(base_color[1] * (1 + 0.3 * (1 - progress))))
            b = min(255, int(base_color[2] * (1 + 0.5 * (1 - progress))))
            
            pygame.draw.ellipse(surface, (r, g, b, alpha),
                              pygame.Rect(center[0] - i, center[1] - i // 2,
                                        i * 2, i))


class DHDButtonManager:
    """Manages DHD buttons and screen shake effects."""
    
    def __init__(self):
        self.buttons = {}
        self.shake_duration = 0
        self.shake_intensity = 0
        self.shake_offset = (0, 0)
    
    def add_button(self, key, rect, text, font):
        """Add a new DHD button."""
        self.buttons[key] = DHDButton(rect, text, font)
        return self.buttons[key]
    
    def update(self, dt, mouse_pos, selected_index=None):
        """Update all buttons."""
        for i, (key, button) in enumerate(self.buttons.items()):
            is_hovered = button.rect.collidepoint(mouse_pos)
            is_selected = (selected_index is not None and i == selected_index)
            button.update(dt, is_hovered, is_selected)
        
        # Update screen shake
        if self.shake_duration > 0:
            self.shake_duration = max(0, self.shake_duration - dt)
            progress = self.shake_duration / 500.0
            intensity = self.shake_intensity * progress
            self.shake_offset = (
                random.uniform(-intensity, intensity),
                random.uniform(-intensity, intensity)
            )
        else:
            self.shake_offset = (0, 0)
    
    def activate_button(self, key):
        """Activate a button and trigger screen shake."""
        if key in self.buttons:
            self.buttons[key].activate()
            self.trigger_shake(intensity=5, duration=500)
    
    def trigger_shake(self, intensity=5, duration=500):
        """Trigger screen shake effect."""
        self.shake_duration = duration
        self.shake_intensity = intensity
    
    def draw(self, surface, selected_index=None):
        """Draw all buttons."""
        for i, button in enumerate(self.buttons.values()):
            is_selected = (selected_index is not None and i == selected_index)
            button.draw(surface, is_selected)
    
    def get_shake_offset(self):
        """Get current screen shake offset."""
        return self.shake_offset
    
    def handle_click(self, pos):
        """Handle mouse click and return clicked button key."""
        for key, button in self.buttons.items():
            if button.rect.collidepoint(pos):
                self.activate_button(key)
                return key
        return None
