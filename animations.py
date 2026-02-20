import pygame
import math
import random
import display_manager

# RESOLUTION SCALE FACTOR
# All hardcoded sizes should be multiplied by this for 4K
# Base: 1080p = 1.0, 4K (2160p) = 2.0
def get_scale_factor(screen_height):
    """Get resolution scale factor based on screen height."""
    return screen_height / 1080.0  # 1.0 for 1080p, 2.0 for 4K

# Particle system limits to prevent memory accumulation
MAX_TRAIL_PARTICLES = 50
MAX_HEARTS_PARTICLES = 30
MAX_GENERAL_PARTICLES = 100


# ============================================================================
# ANIMATION POOLING SYSTEM (v4.3.1)
# ============================================================================
class AnimationPool:
    """
    Object pool for animations to reduce GC pressure during particle-heavy effects.
    Reuses finished animations instead of creating new ones every time.
    """
    def __init__(self):
        self._pools = {}  # animation_type -> List[Animation]
        self._max_pool_size = 20  # Limit per animation type to prevent unbounded growth

    def get(self, animation_type, *args, **kwargs):
        """
        Get an animation from the pool or create a new one.

        Args:
            animation_type: The animation class to instantiate
            *args, **kwargs: Arguments to pass to the animation constructor

        Returns:
            Animation instance (reused or new)
        """
        type_name = animation_type.__name__

        # Try to reuse from pool
        if type_name in self._pools and self._pools[type_name]:
            anim = self._pools[type_name].pop()
            # Check if animation has a reset method
            if hasattr(anim, 'reset'):
                anim.reset(*args, **kwargs)
            else:
                # If no reset method, reinitialize basic properties
                anim.__init__(*args, **kwargs)
            return anim

        # No pooled instance available, create new
        return animation_type(*args, **kwargs)

    def return_animation(self, anim):
        """
        Return a finished animation to the pool for reuse.

        Args:
            anim: The animation to return to the pool
        """
        if anim is None:
            return

        type_name = type(anim).__name__

        # Initialize pool for this type if needed
        if type_name not in self._pools:
            self._pools[type_name] = []

        # Only add to pool if below max size
        if len(self._pools[type_name]) < self._max_pool_size:
            # Clear any references that might prevent cleanup
            if hasattr(anim, 'card_image'):
                anim.card_image = None
            if hasattr(anim, 'on_complete'):
                anim.on_complete = None

            self._pools[type_name].append(anim)

    def clear(self):
        """Clear all pooled animations (useful for testing or cleanup)."""
        self._pools.clear()

    def get_stats(self):
        """Get statistics about the pool (for debugging)."""
        return {type_name: len(pool) for type_name, pool in self._pools.items()}

class Animation:
    """Base class for all animations."""
    def __init__(self, duration):
        self.duration = duration  # in milliseconds
        self.elapsed = 0
        self.finished = False
    
    def update(self, dt):
        """Update animation state."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            self.elapsed = self.duration
        return not self.finished
    
    def get_progress(self):
        """Returns progress from 0.0 to 1.0."""
        return min(1.0, self.elapsed / self.duration)
    
    def apply(self, surface, x, y):
        """Override this to apply the animation effect."""
        pass


class CardSlideAnimation(Animation):
    """Slides a card from start position to end position."""
    def __init__(self, start_pos, end_pos, duration=300):
        super().__init__(duration)
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.current_x = self.start_x
        self.current_y = self.start_y
    
    def update(self, dt):
        super().update(dt)
        progress = self.ease_out_cubic(self.get_progress())
        self.current_x = self.start_x + (self.end_x - self.start_x) * progress
        self.current_y = self.start_y + (self.end_y - self.start_y) * progress
        return not self.finished
    
    def ease_out_cubic(self, t):
        """Easing function for smooth motion."""
        return 1 - pow(1 - t, 3)
    
    def get_position(self):
        return (self.current_x, self.current_y)


class CardStealAnimation(Animation):
    """Animates a stolen card flying from opponent to player."""
    def __init__(self, card_image, start_pos, end_pos, duration=650, on_complete=None):
        super().__init__(duration)
        self.card_image = card_image.copy() if card_image else None
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.current_x = self.start_x
        self.current_y = self.start_y
        self.scale = 1.0
        self.alpha = 255
        self.on_complete = on_complete
        self.trail = []
    
    def update(self, dt):
        if not self.card_image:
            if self.on_complete:
                self.on_complete()
                self.on_complete = None
            return False
        
        active = super().update(dt)
        progress = self.get_progress()
        eased = 1 - math.pow(1 - progress, 3)
        
        arc = math.sin(progress * math.pi) * -60
        self.current_x = self.start_x + (self.end_x - self.start_x) * eased
        self.current_y = self.start_y + (self.end_y - self.start_y) * eased + arc
        self.scale = 1.05
        self.alpha = int(255 * (1 - progress * 0.2))

        self.trail.append({
            'x': self.current_x,
            'y': self.current_y,
            'alpha': self.alpha,
            'age': 0
        })

        # Enforce max trail particles limit
        if len(self.trail) > MAX_TRAIL_PARTICLES:
            self.trail = self.trail[-MAX_TRAIL_PARTICLES:]

        for particle in self.trail[:]:
            particle['age'] += dt
            particle['alpha'] = max(0, particle['alpha'] - dt * 0.4)
            if particle['alpha'] <= 0:
                self.trail.remove(particle)
        
        if self.finished and self.on_complete:
            self.on_complete()
            self.on_complete = None
        return active
    
    def draw(self, surface):
        if not self.card_image or self.finished:
            return
        
        for particle in self.trail:
            size = int(40 + particle['age'] * 0.02)
            trail_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (80, 200, 255, int(particle['alpha'] * 0.4)), (size//2, size//2), size//2)
            surface.blit(trail_surf, (int(particle['x'] - size//2), int(particle['y'] - size//2)))
        
        width, height = self.card_image.get_size()
        scaled_size = (
            max(1, int(width * self.scale)),
            max(1, int(height * self.scale))
        )
        scaled_card = pygame.transform.smoothscale(self.card_image, scaled_size)
        scaled_card.set_alpha(self.alpha)
        rect = scaled_card.get_rect(center=(int(self.current_x), int(self.current_y)))
        surface.blit(scaled_card, rect)


class HathorStealAnimation(Animation):
    """Animation for Hathor stealing a card with heart kisses."""
    def __init__(self, card, start_pos, end_pos, duration=1200, on_finish=None):
        super().__init__(duration)
        self.card = card
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.current_x = self.start_x
        self.current_y = self.start_y
        self.hearts = []
        self.scale = 1.0
        self.alpha = 255
        self.rotation = 0
        self.on_finish = on_finish
        
        # Create heart particles
        for _ in range(15):
            self.hearts.append({
                'x': start_pos[0],
                'y': start_pos[1],
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-3, -1),
                'size': random.randint(8, 15),
                'life': 1.0,
                'color': (255, random.randint(100, 200), random.randint(150, 200))
            })
    
    def update(self, dt):
        if not self.card:
            if self.on_finish:
                self.on_finish()
                self.on_finish = None
            return False
        
        active = super().update(dt)
        progress = self.get_progress()
        
        # Update card position with easing
        eased = self.ease_in_out_cubic(progress)
        self.current_x = self.start_x + (self.end_x - self.start_x) * eased
        self.current_y = self.start_y + (self.end_y - self.start_y) * eased
        
        # Add a floating effect
        float_offset = math.sin(progress * math.pi * 2) * 10
        self.current_y += float_offset
        
        # Slight rotation effect
        self.rotation = math.sin(progress * math.pi * 4) * 5
        
        # Update hearts
        for heart in self.hearts:
            heart['x'] += heart['vx']
            heart['y'] += heart['vy']
            heart['vy'] += 0.1  # Gravity
            heart['life'] -= dt / 1000.0
            
            # Make hearts float toward the card
            dx = self.current_x - heart['x']
            dy = self.current_y - heart['y']
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                heart['x'] += dx * 0.02
                heart['y'] += dy * 0.02
        
        # Remove dead hearts
        self.hearts = [h for h in self.hearts if h['life'] > 0]

        # Add new hearts during the animation (with max limit)
        if progress < 0.7 and random.random() < 0.2 and len(self.hearts) < MAX_HEARTS_PARTICLES:
            self.hearts.append({
                'x': self.current_x + random.uniform(-20, 20),
                'y': self.current_y + random.uniform(-20, 20),
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(-2, -0.5),
                'size': random.randint(8, 15),
                'life': 1.0,
                'color': (255, random.randint(100, 200), random.randint(150, 200))
            })

        # Enforce max hearts limit (safety check)
        if len(self.hearts) > MAX_HEARTS_PARTICLES:
            self.hearts = self.hearts[-MAX_HEARTS_PARTICLES:]
            
        if self.finished and self.on_finish:
            self.on_finish()
            self.on_finish = None
            
        return active
    
    def ease_in_out_cubic(self, t):
        """Easing function for smooth motion."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    def draw(self, surface):
        if not self.card or self.finished:
            return
        
        # Draw hearts
        for heart in self.hearts:
            alpha = int(255 * heart['life'])
            self.draw_heart(surface, heart['x'], heart['y'], heart['size'], (*heart['color'], alpha))
        
        # Draw the card with rotation
        if self.card.image:
            # Create a rotated surface
            card_surface = pygame.transform.rotate(self.card.image, self.rotation)
            
            # Apply alpha
            card_surface.set_alpha(self.alpha)
            
            # Get the rect and center it
            card_rect = card_surface.get_rect(center=(int(self.current_x), int(self.current_y)))
            
            # Draw the card
            surface.blit(card_surface, card_rect)
    
    def draw_heart(self, surface, x, y, size, color):
        """Draw a heart shape at the given position."""
        # Create a surface for the heart
        heart_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        
        # Draw a simple heart shape
        # Using two circles and a triangle
        pygame.draw.circle(heart_surface, color, (size // 2, size // 2), size // 2)
        pygame.draw.circle(heart_surface, color, (size + size // 2, size // 2), size // 2)
        points = [
            (size, size),
            (size * 2, size),
            (size, size * 2)
        ]
        pygame.draw.polygon(heart_surface, color, points)
        
        # Blit the heart to the surface
        surface.blit(heart_surface, (x - size, y - size))


class CardFlipAnimation(Animation):
    """Flips a card (scale effect)."""
    def __init__(self, duration=400):
        super().__init__(duration)
        self.scale = 1.0
    
    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()
        # Scale down then up for flip effect
        if progress < 0.5:
            self.scale = 1.0 - (progress * 2) * 0.3  # Scale to 0.7
        else:
            self.scale = 0.7 + ((progress - 0.5) * 2) * 0.3  # Scale back to 1.0
        return not self.finished
    
    def apply_to_image(self, image):
        """Returns scaled image for flip effect."""
        width = int(image.get_width() * self.scale)
        height = image.get_height()
        if width <= 0:
            width = 1
        return pygame.transform.scale(image, (width, height))


class CardRevealAnimation(Animation):
    """Card reveal animation with flip effect and sparkle particles for drawn cards."""
    def __init__(self, card, start_pos, end_pos, duration=500, on_complete=None):
        super().__init__(duration)
        self.card = card
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.current_x = self.start_x
        self.current_y = self.start_y
        self.scale_x = 0.0  # Start flipped (showing back)
        self.scale_y = 1.0
        self.alpha = 255
        self.on_complete = on_complete
        self.sparkles = []
        self.revealed = False  # Track when card face is shown

        # Create sparkle particles
        for _ in range(15):
            self.sparkles.append({
                'x': start_pos[0],
                'y': start_pos[1],
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-4, -1),
                'size': random.randint(2, 5),
                'life': 1.0,
                'color': (200, 220, 255),
                'delay': random.uniform(0, 0.3)  # Stagger sparkle appearance
            })

    def update(self, dt):
        if not self.card:
            if self.on_complete:
                self.on_complete()
                self.on_complete = None
            return False

        active = super().update(dt)
        progress = self.get_progress()

        # Eased movement toward hand position
        eased = self.ease_out_cubic(progress)
        self.current_x = self.start_x + (self.end_x - self.start_x) * eased
        self.current_y = self.start_y + (self.end_y - self.start_y) * eased

        # Flip animation: scale from 0 to 1 (card rotates in)
        if progress < 0.5:
            # First half: show card back, scale shrinking
            self.scale_x = 1.0 - (progress * 2)
            self.revealed = False
        else:
            # Second half: show card face, scale growing
            self.scale_x = (progress - 0.5) * 2
            self.revealed = True

        # Slight bounce in Y scale during flip
        self.scale_y = 1.0 + math.sin(progress * math.pi) * 0.1

        # Update sparkles
        for sparkle in self.sparkles:
            if progress > sparkle['delay']:
                sparkle['x'] += sparkle['vx']
                sparkle['y'] += sparkle['vy']
                sparkle['vy'] += 0.15  # Gravity
                sparkle['life'] -= dt / 400.0

        # Remove dead sparkles
        self.sparkles = [s for s in self.sparkles if s['life'] > 0]

        if self.finished and self.on_complete:
            self.on_complete()
            self.on_complete = None

        return active

    def ease_out_cubic(self, t):
        return 1 - pow(1 - t, 3)

    def draw(self, surface):
        if not self.card or self.finished:
            return

        # Draw sparkles
        for sparkle in self.sparkles:
            if sparkle['life'] > 0:
                alpha = int(255 * sparkle['life'])
                size = max(1, int(sparkle['size'] * sparkle['life']))
                sparkle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(sparkle_surf, (*sparkle['color'], alpha), (size, size), size)
                surface.blit(sparkle_surf, (int(sparkle['x'] - size), int(sparkle['y'] - size)))

        # Draw the card with flip effect
        if self.card.image and self.scale_x > 0.05:
            width = int(self.card.image.get_width() * self.scale_x)
            height = int(self.card.image.get_height() * self.scale_y)
            if width > 0 and height > 0:
                # Use card back image for first half, card face for second half
                if self.revealed and self.card.image:
                    scaled_card = pygame.transform.scale(self.card.image, (width, height))
                else:
                    # Create a simple card back
                    scaled_card = pygame.Surface((width, height), pygame.SRCALPHA)
                    scaled_card.fill((40, 60, 100))
                    pygame.draw.rect(scaled_card, (80, 120, 180), scaled_card.get_rect(), width=3)

                scaled_card.set_alpha(self.alpha)
                rect = scaled_card.get_rect(center=(int(self.current_x), int(self.current_y)))
                surface.blit(scaled_card, rect)


class AbilityBurstEffect:
    """Visual burst/glow effect when card abilities trigger."""
    def __init__(self, x, y, color=(100, 200, 255), duration=600, ability_name=""):
        self.x = x
        self.y = y
        self.color = color
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.ability_name = ability_name
        self.particles = []
        self.ring_radius = 0
        self.max_ring_radius = 80

        # Determine color based on ability type
        ability_lower = ability_name.lower() if ability_name else ""
        if "medic" in ability_lower or "evac" in ability_lower or "heal" in ability_lower:
            self.color = (100, 255, 150)  # Green for healing
        elif "spy" in ability_lower or "ring" in ability_lower or "transport" in ability_lower:
            self.color = (255, 180, 80)   # Orange for transport
        elif "decoy" in ability_lower or "recall" in ability_lower:
            self.color = (180, 100, 255)  # Purple for recall
        elif "bond" in ability_lower or "muster" in ability_lower:
            self.color = (255, 220, 100)  # Gold for bond/muster
        elif "scorch" in ability_lower or "naquadah" in ability_lower:
            self.color = (255, 80, 80)    # Red for damage

        # Create burst particles
        for _ in range(20):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(2, 6)
            self.particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': random.randint(3, 7),
                'life': 1.0,
                'color': self.color
            })

    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False

        progress = self.elapsed / self.duration

        # Expand ring
        self.ring_radius = self.max_ring_radius * self.ease_out_cubic(min(progress * 1.5, 1.0))

        # Update particles
        for particle in self.particles[:]:
            particle['x'] += particle['vx'] * (dt / 16.0)
            particle['y'] += particle['vy'] * (dt / 16.0)
            particle['vx'] *= 0.96
            particle['vy'] *= 0.96
            particle['life'] -= dt / self.duration
            if particle['life'] <= 0:
                self.particles.remove(particle)

        return True

    def ease_out_cubic(self, t):
        return 1 - pow(1 - t, 3)

    def draw(self, surface):
        if self.finished:
            return

        progress = self.elapsed / self.duration
        alpha = int((1 - progress) * 200)

        # Draw expanding ring
        if self.ring_radius > 0 and alpha > 0:
            ring_surf = pygame.Surface((self.max_ring_radius * 2 + 20, self.max_ring_radius * 2 + 20), pygame.SRCALPHA)
            center = self.max_ring_radius + 10

            # Outer glow ring
            glow_color = (*self.color, alpha // 3)
            pygame.draw.circle(ring_surf, glow_color, (center, center), int(self.ring_radius + 5), width=8)

            # Inner bright ring
            ring_color = (*self.color, alpha)
            pygame.draw.circle(ring_surf, ring_color, (center, center), int(self.ring_radius), width=3)

            surface.blit(ring_surf, (self.x - center, self.y - center))

        # Draw central flash (bright at start, fades quickly)
        if progress < 0.2:
            flash_alpha = int((1 - progress / 0.2) * 255)
            flash_size = int(30 + progress * 40)
            flash_surf = pygame.Surface((flash_size * 2, flash_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha), (flash_size, flash_size), flash_size)
            surface.blit(flash_surf, (self.x - flash_size, self.y - flash_size))

        # Draw particles
        for particle in self.particles:
            if particle['life'] > 0:
                p_alpha = int(255 * particle['life'])
                size = max(1, int(particle['size'] * particle['life']))

                particle_surf = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
                # Glow
                glow_color = (*particle['color'], p_alpha // 2)
                pygame.draw.circle(particle_surf, glow_color, (size * 1.5, size * 1.5), int(size * 1.5))
                # Core
                core_color = (*particle['color'], p_alpha)
                pygame.draw.circle(particle_surf, core_color, (size * 1.5, size * 1.5), size)

                surface.blit(particle_surf, (int(particle['x'] - size * 1.5), int(particle['y'] - size * 1.5)))

        # Draw ability-specific flourish on top
        self._draw_ability_flourish(surface, progress)

    def _draw_ability_flourish(self, surface, progress):
        """Draw ability-type-specific visual flourish layered on top of ring+particles."""
        ability_lower = self.ability_name.lower() if self.ability_name else ""
        if not ability_lower:
            return

        if "medic" in ability_lower or "evac" in ability_lower or "heal" in ability_lower:
            # Glowing + cross shape at center, fades 0.1–0.5
            if 0.1 < progress < 0.5:
                t = (progress - 0.1) / 0.4
                cross_alpha = int(200 * (1 - t))
                cross_size = int(20 + 10 * t)
                cross_w = max(4, int(6 * (1 - t)))
                cross_surf = pygame.Surface((cross_size * 2, cross_size * 2), pygame.SRCALPHA)
                c = cross_size
                color = (*self.color, cross_alpha)
                pygame.draw.rect(cross_surf, color, (c - cross_w // 2, c - cross_size + 4, cross_w, cross_size * 2 - 8))
                pygame.draw.rect(cross_surf, color, (c - cross_size + 4, c - cross_w // 2, cross_size * 2 - 8, cross_w))
                surface.blit(cross_surf, (self.x - cross_size, self.y - cross_size))

        elif "spy" in ability_lower or "ring" in ability_lower or "transport" in ability_lower:
            # 3 horizontal ring-transport ellipses expanding vertically
            if progress < 0.7:
                t = progress / 0.7
                ring_alpha = int(180 * (1 - t))
                for i in range(3):
                    offset_y = int((i - 1) * 30 * t)
                    rx = int(25 + 15 * t)
                    ry = int(8 + 20 * t)
                    ellipse_surf = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
                    color = (*self.color, ring_alpha)
                    pygame.draw.ellipse(ellipse_surf, color, (2, 2, rx * 2, ry * 2), width=2)
                    surface.blit(ellipse_surf, (self.x - rx - 2, self.y + offset_y - ry - 2))

        elif "decoy" in ability_lower or "recall" in ability_lower:
            # << chevron arrows shrinking toward center
            if progress < 0.6:
                t = progress / 0.6
                chev_alpha = int(200 * (1 - t))
                chev_surf = pygame.Surface((120, 80), pygame.SRCALPHA)
                cx, cy = 60, 40
                color = (*self.color, chev_alpha)
                for j in range(2):
                    offset = int(40 * (1 - t) + j * 20)
                    # Left chevron <<
                    pygame.draw.line(chev_surf, color, (cx - offset, cy - 15), (cx - offset - 12, cy), 3)
                    pygame.draw.line(chev_surf, color, (cx - offset - 12, cy), (cx - offset, cy + 15), 3)
                    # Right chevron >>
                    pygame.draw.line(chev_surf, color, (cx + offset, cy - 15), (cx + offset + 12, cy), 3)
                    pygame.draw.line(chev_surf, color, (cx + offset + 12, cy), (cx + offset, cy + 15), 3)
                surface.blit(chev_surf, (self.x - 60, self.y - 40))

        elif "bond" in ability_lower or "muster" in ability_lower:
            # Connecting lines from center to each particle
            if progress < 0.6:
                t = progress / 0.6
                line_alpha = int(150 * (1 - t))
                line_surf = pygame.Surface((self.max_ring_radius * 3, self.max_ring_radius * 3), pygame.SRCALPHA)
                lc = self.max_ring_radius * 3 // 2
                color = (*self.color, line_alpha)
                for p in self.particles:
                    if p['life'] > 0:
                        px = int(p['x'] - self.x + lc)
                        py = int(p['y'] - self.y + lc)
                        pygame.draw.line(line_surf, color, (lc, lc), (px, py), 1)
                surface.blit(line_surf, (self.x - lc, self.y - lc))

        elif "scorch" in ability_lower or "naquadah" in ability_lower:
            # Pulsing concentric danger circles with sin oscillation
            if progress < 0.7:
                t = progress / 0.7
                pulse = math.sin(progress * math.pi * 6) * 0.3 + 0.7
                circle_alpha = int(160 * (1 - t) * pulse)
                for r_mult in (0.5, 0.8):
                    r = int(self.max_ring_radius * r_mult * (0.3 + 0.7 * t))
                    if r > 0:
                        circ_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                        color = (*self.color, circle_alpha)
                        pygame.draw.circle(circ_surf, color, (r + 2, r + 2), r, width=2)
                        surface.blit(circ_surf, (self.x - r - 2, self.y - r - 2))


class RowScoreAnimation(Animation):
    """Animated score counter for row score changes."""
    def __init__(self, old_value, new_value, x, y, duration=400, color=None):
        super().__init__(duration)
        self.old_value = old_value
        self.new_value = new_value
        self.current_value = old_value
        self.x = x
        self.y = y
        self.scale = 1.0
        self.offset_y = 0

        # Determine color based on change direction
        if color:
            self.color = color
        elif new_value > old_value:
            self.color = (100, 255, 100)  # Green for increase
        elif new_value < old_value:
            self.color = (255, 100, 100)  # Red for decrease
        else:
            self.color = (255, 255, 255)  # White for no change

    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()

        # Smooth counting animation
        self.current_value = int(self.old_value + (self.new_value - self.old_value) * self.ease_out_cubic(progress))

        # Pop effect
        if progress < 0.3:
            self.scale = 1.0 + (progress / 0.3) * 0.3
        else:
            self.scale = 1.3 - ((progress - 0.3) / 0.7) * 0.3

        # Slight bounce
        self.offset_y = -math.sin(progress * math.pi) * 8

        return not self.finished

    def ease_out_cubic(self, t):
        return 1 - pow(1 - t, 3)

    def get_display_value(self):
        return self.current_value


class GlowAnimation(Animation):
    """Pulsing glow effect."""
    def __init__(self, color=(100, 200, 255), duration=1000, loop=True):
        super().__init__(duration)
        self.color = color
        self.loop = loop
        self.intensity = 0
    
    def update(self, dt):
        super().update(dt)
        if self.loop and self.finished:
            self.elapsed = 0
            self.finished = False
        
        progress = self.get_progress()
        # Sine wave for smooth pulse
        self.intensity = math.sin(progress * math.pi * 2) * 0.5 + 0.5
        return not self.finished or self.loop
    
    def apply(self, surface, rect):
        """Draws glow around rectangle."""
        glow_surface = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
        alpha = int(self.intensity * 100)
        glow_color = (*self.color, alpha)
        pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), width=10, border_radius=10)
        return glow_surface


class ParticleEffect:
    """Particle system for effects like Stargate event horizon."""
    def __init__(self, x, y, color=(100, 150, 255), count=20):
        self.particles = []
        # Enforce max particle limit
        count = min(count, MAX_GENERAL_PARTICLES)
        for _ in range(count):
            angle = math.radians(pygame.time.get_ticks() % 360 + _ * (360 / count))
            speed = pygame.math.Vector2(math.cos(angle) * 2, math.sin(angle) * 2)
            self.particles.append({
                'pos': pygame.math.Vector2(x, y),
                'vel': speed,
                'life': 1.0,
                'color': color
            })
    
    def update(self, dt):
        """Update all particles."""
        for particle in self.particles[:]:
            particle['pos'] += particle['vel'] * (dt / 16.0)  # Normalize to 60fps
            particle['life'] -= dt / 1000.0
            particle['vel'] *= 0.98  # Slow down
            if particle['life'] <= 0:
                self.particles.remove(particle)
        return len(self.particles) > 0
    
    def draw(self, surface):
        """Draw all particles."""
        for particle in self.particles:
            alpha = int(particle['life'] * 255)
            color = (*particle['color'], alpha)
            pos = (int(particle['pos'].x), int(particle['pos'].y))
            size = max(1, int(particle['life'] * 5))
            # Draw particle as small circle
            particle_surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, color, (size, size), size)
            surface.blit(particle_surf, (pos[0]-size, pos[1]-size))


class StargateActivationEffect:
    """Stargate-themed effect when cards are played, colored by faction."""

    # Faction color map for rings and particles
    FACTION_COLORS = {
        "Tau'ri":           (100, 150, 255),   # blue
        "Goa'uld":          (255, 200, 60),    # gold
        "Jaffa Rebellion":  (200, 150, 100),   # bronze
        "Lucian Alliance":  (180, 100, 220),   # purple
        "Asgard":           (100, 240, 255),   # cyan
    }
    DEFAULT_COLOR = (100, 180, 255)  # blue fallback

    def __init__(self, x, y, duration=1000, faction=None):
        self.x = x
        self.y = y
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.radius = 0
        self.max_radius = 100
        self.faction = faction
        # Pick faction color or default blue
        self.color = self.FACTION_COLORS.get(faction, self.DEFAULT_COLOR)
        self.particles = ParticleEffect(x, y, color=self.color, count=30)
        # Pre-compute shimmer angles for event horizon
        self._shimmer_angles = [i * (math.tau / 12) for i in range(12)]

    def update(self, dt):
        """Update effect."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False

        progress = min(1.0, self.elapsed / self.duration)
        # Expand ring
        self.radius = self.max_radius * progress
        # Update particles
        self.particles.update(dt)
        return True

    def draw(self, surface):
        """Draw the stargate activation effect."""
        if self.finished:
            return

        progress = min(1.0, self.elapsed / self.duration)
        alpha = int((1.0 - progress) * 200)
        ring_surface = pygame.Surface((self.max_radius*2 + 20, self.max_radius*2 + 20), pygame.SRCALPHA)
        cx, cy = self.max_radius + 10, self.max_radius + 10

        # Draw multiple rings for depth (faction-colored)
        r, g, b = self.color
        for i in range(3):
            ring_color = (min(255, r + i*30), min(255, g + i*20), min(255, b), alpha // (i+1))
            radius = int(self.radius - i*5)
            if radius > 0:
                pygame.draw.circle(ring_surface, ring_color, (cx, cy), radius, width=3)

        # Event horizon shimmer: 12 rotating radial lines during first 50%
        if progress < 0.5:
            shimmer_t = progress / 0.5
            shimmer_alpha = int(140 * (1 - shimmer_t))
            rotation = progress * math.pi * 3  # rotate during animation
            for angle in self._shimmer_angles:
                a = angle + rotation
                length = self.radius * 0.8
                if length > 5:
                    ex = cx + math.cos(a) * length
                    ey = cy + math.sin(a) * length
                    line_color = (*self.color, shimmer_alpha)
                    pygame.draw.line(ring_surface, line_color, (cx, cy), (int(ex), int(ey)), 1)

        surface.blit(ring_surface, (self.x - self.max_radius - 10, self.y - self.max_radius - 10))

        # Draw particles
        self.particles.draw(surface)

    def get_gpu_params(self):
        """Return mild distortion for GPU rendering during first 40%."""
        if self.finished:
            return None
        progress = min(1.0, self.elapsed / self.duration)
        if progress > 0.4:
            return None
        strength = 0.15 * (1 - progress / 0.4)
        return {
            'type': 'distortion',
            'center': (self.x, self.y),
            'strength': strength,
            'radius': int(self.max_radius * progress * 2),
        }


class LegendaryLightningEffect(Animation):
    """Electric outline that races around a Legendary Commander card once."""
    def __init__(self, card, duration=900):
        super().__init__(duration)
        self.card = card
        self.points = []
        self.trail_ratio = 0.35  # Portion of the perimeter to illuminate
        self.jitter = 6
    
    def _get_rect(self):
        rect = getattr(self.card, "rect", None)
        if rect:
            return rect.copy()
        return None
    
    def _point_at_distance(self, rect, dist):
        width = rect.width
        height = rect.height
        perimeter = max(1.0, 2 * (width + height))
        d = max(0.0, min(dist, perimeter))
        left, top = rect.left, rect.top
        right = left + width
        bottom = top + height
        
        if d <= width:
            return (left + d, top, "top")
        d -= width
        if d <= height:
            return (right, top + d, "right")
        d -= height
        if d <= width:
            return (right - d, bottom, "bottom")
        d -= width
        return (left, bottom - d, "left")
    
    def _build_path(self):
        rect = self._get_rect()
        if not rect:
            self.points = []
            return
        perimeter = max(1.0, 2 * (rect.width + rect.height))
        head = perimeter * self.get_progress()
        tail = max(0.0, head - perimeter * self.trail_ratio)
        if head <= tail:
            head = tail + 0.001
        steps = max(4, int((head - tail) / 8))
        points = []
        for i in range(steps):
            t = tail + (head - tail) * (i / (steps - 1))
            x, y, edge = self._point_at_distance(rect, t)
            jitter = random.uniform(-self.jitter, self.jitter)
            if edge in ("top", "bottom"):
                y += jitter
            else:
                x += jitter
            points.append((x, y))
        self.points = points
    
    def update(self, dt):
        active = super().update(dt)
        self._build_path()
        return active
    
    def draw(self, surface):
        if not self.points:
            return
        rect = self._get_rect()
        if not rect:
            return
        alpha = int(220 * (1.0 - self.get_progress() * 0.4))
        if alpha <= 0:
            return
        lightning_surface = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
        offset_points = [(p[0] - rect.left + 10, p[1] - rect.top + 10) for p in self.points]
        color = (200, 240, 255, alpha)
        pygame.draw.lines(lightning_surface, color, False, offset_points, 3)
        
        glow_alpha = max(40, alpha // 3)
        glow_color = (120, 200, 255, glow_alpha)
        pygame.draw.rect(
            lightning_surface,
            glow_color,
            pygame.Rect(4, 4, rect.width + 12, rect.height + 12),
            width=2,
            border_radius=12
        )
        surface.blit(lightning_surface, (rect.left - 10, rect.top - 10))


class AICardPlayAnimation(Animation):
    """Floating AI card animation that moves from hand to target row."""
    def __init__(self, card_image, start_pos, end_pos, duration=600):
        super().__init__(duration)
        self.card_image = card_image.copy() if card_image else None
        self.start_x, self.start_y = start_pos
        self.end_x, self.end_y = end_pos
        self.current_x = self.start_x
        self.current_y = self.start_y
        self.scale = 1.0
        self.alpha = 255
    
    def ease_out_cubic(self, t):
        return 1 - pow(1 - t, 3)
    
    def update(self, dt):
        if not self.card_image:
            return False
        active = super().update(dt)
        progress = self.get_progress()
        eased = self.ease_out_cubic(progress)
        
        # Smooth travel with slight arc dip
        arc_offset = math.sin(eased * math.pi) * -30  # Gentle float-down arc
        self.current_x = self.start_x + (self.end_x - self.start_x) * eased
        self.current_y = self.start_y + (self.end_y - self.start_y) * eased + arc_offset
        
        # Gentle scale/alpha pulses
        self.scale = 0.95 + 0.1 * math.sin(progress * math.pi)
        self.alpha = int(255 * (0.9 + 0.1 * (1 - progress)))
        return active
    
    def draw(self, surface):
        if not self.card_image or self.finished:
            return
        width, height = self.card_image.get_size()
        scaled_size = (
            max(1, int(width * self.scale)),
            max(1, int(height * self.scale))
        )
        scaled_card = pygame.transform.smoothscale(self.card_image, scaled_size)
        scaled_card.set_alpha(self.alpha)
        rect = scaled_card.get_rect(center=(int(self.current_x), int(self.current_y)))
        surface.blit(scaled_card, rect)


class NaquadahExplosionEffect:
    """Dense blue naquadah energy explosion effect for Naquadah Overload ability."""
    def __init__(self, x, y, duration=1500):
        self.x = x
        self.y = y
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.particles = []
        self.lightning_arcs = []
        self.shockwave_radius = 0
        self.max_shockwave_radius = 200
        self.shake_intensity = 0

        # Create DENSE blue energy particles radiating outward (3x more particles)
        for i in range(150):
            angle = random.uniform(0, 360)
            speed = random.uniform(1.5, 8)
            # Varied particle types for depth
            particle_type = random.choice(['fast', 'slow', 'sparkle'])
            size = random.randint(2, 10) if particle_type == 'fast' else random.randint(4, 14)

            self.particles.append({
                'pos': pygame.math.Vector2(x, y),
                'vel': pygame.math.Vector2(
                    math.cos(math.radians(angle)) * speed,
                    math.sin(math.radians(angle)) * speed
                ),
                'life': 1.0,
                'size': size,
                'type': particle_type,
                'color': (80 + random.randint(-30, 60), 150 + random.randint(-40, 80), 255)
            })

        # Create electric arc/lightning effects
        for i in range(8):
            angle = random.uniform(0, 360)
            length = random.randint(80, 150)
            self.lightning_arcs.append({
                'start': pygame.math.Vector2(x, y),
                'angle': angle,
                'length': length,
                'life': 1.0,
                'segments': self._generate_lightning_segments(x, y, angle, length)
            })

    def _generate_lightning_segments(self, x, y, angle, length):
        """Generate jagged lightning bolt segments."""
        segments = [pygame.math.Vector2(x, y)]
        current = pygame.math.Vector2(x, y)
        target = pygame.math.Vector2(
            x + math.cos(math.radians(angle)) * length,
            y + math.sin(math.radians(angle)) * length
        )

        # Create 5-8 segments with random offsets
        num_segments = random.randint(5, 8)
        for i in range(1, num_segments):
            progress = i / num_segments
            # Interpolate toward target with random perpendicular offset
            next_point = current.lerp(target, 1.0 / (num_segments - i + 1))
            offset = random.uniform(-15, 15)
            perp_angle = angle + 90
            next_point.x += math.cos(math.radians(perp_angle)) * offset
            next_point.y += math.sin(math.radians(perp_angle)) * offset
            segments.append(next_point)
            current = next_point

        segments.append(target)
        return segments

    def update(self, dt):
        """Update explosion effect."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False

        progress = self.elapsed / self.duration
        self.shockwave_radius = self.max_shockwave_radius * min(progress * 1.8, 1.0)

        # Screen shake intensity (peaks early, fades out)
        if progress < 0.3:
            self.shake_intensity = 8 * (1 - progress / 0.3)
        else:
            self.shake_intensity = 0

        # Update particles
        for particle in self.particles[:]:
            speed_mult = 1.5 if particle['type'] == 'fast' else 0.8
            particle['pos'] += particle['vel'] * (dt / 16.0) * speed_mult
            particle['life'] -= (dt / self.duration) * (1.2 if particle['type'] == 'fast' else 0.9)
            particle['vel'] *= 0.97  # Slow down over time
            if particle['life'] <= 0:
                self.particles.remove(particle)

        # Update lightning arcs (fade out quickly)
        for arc in self.lightning_arcs[:]:
            arc['life'] -= dt / (self.duration * 0.4)  # Lightning fades in first 40%
            if arc['life'] <= 0:
                self.lightning_arcs.remove(arc)

        return True

    def draw(self, surface):
        """Draw dense explosion with multiple shockwaves, particles, and lightning."""
        progress = self.elapsed / self.duration

        # Apply screen shake offset
        shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
        shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)

        # Draw bright blue core flash (fades quickly)
        if progress < 0.15:
            core_alpha = int((1 - progress / 0.15) * 255)
            core_size = int(40 + progress * 100)
            core_surf = pygame.Surface((core_size * 2, core_size * 2), pygame.SRCALPHA)
            # Bright white-blue core
            pygame.draw.circle(core_surf, (200, 230, 255, core_alpha), (core_size, core_size), core_size)
            pygame.draw.circle(core_surf, (150, 200, 255, core_alpha // 2), (core_size, core_size), int(core_size * 1.5))
            surface.blit(core_surf, (int(self.x - core_size + shake_x), int(self.y - core_size + shake_y)))

        # Draw multiple concentric shockwave rings
        if progress < 0.7:
            max_surf_size = int(self.shockwave_radius * 2 + 100)
            shockwave_surf = pygame.Surface((max_surf_size, max_surf_size), pygame.SRCALPHA)
            center = max_surf_size // 2

            # 5 shockwave rings at different speeds
            for i in range(5):
                ring_progress = min((progress + i * 0.05) / 0.7, 1.0)
                ring_radius = int(self.shockwave_radius * ring_progress)
                ring_alpha = int((1 - ring_progress) * (180 - i * 20))

                if ring_alpha > 0 and ring_radius > 0:
                    # Bright electric blue colors
                    color = (60 + i*15, 120 + i*25, 255, ring_alpha)
                    pygame.draw.circle(shockwave_surf, color, (center, center), ring_radius, width=5 - i)

            surface.blit(shockwave_surf,
                        (int(self.x - max_surf_size // 2 + shake_x),
                         int(self.y - max_surf_size // 2 + shake_y)))

        # Draw lightning arcs
        for arc in self.lightning_arcs:
            alpha = int(arc['life'] * 255)
            if alpha > 0 and len(arc['segments']) > 1:
                # Draw electric arc with glow
                for i in range(len(arc['segments']) - 1):
                    start = arc['segments'][i]
                    end = arc['segments'][i + 1]

                    # Outer glow
                    pygame.draw.line(surface, (100, 180, 255, alpha // 3),
                                   (int(start.x + shake_x), int(start.y + shake_y)),
                                   (int(end.x + shake_x), int(end.y + shake_y)), width=5)
                    # Bright core
                    pygame.draw.line(surface, (200, 230, 255, alpha),
                                   (int(start.x + shake_x), int(start.y + shake_y)),
                                   (int(end.x + shake_x), int(end.y + shake_y)), width=2)

        # Draw dense energy particles
        for particle in self.particles:
            alpha = int(particle['life'] * 255)
            if alpha <= 0:
                continue

            color = (*particle['color'][:3], alpha)
            pos = (int(particle['pos'].x + shake_x), int(particle['pos'].y + shake_y))
            size = max(1, int(particle['size'] * particle['life']))

            # Draw particle with glow
            particle_surf = pygame.Surface((size*4, size*4), pygame.SRCALPHA)

            # Sparkle particles get extra bright glow
            if particle['type'] == 'sparkle':
                # Bright outer glow
                glow_color = (*particle['color'][:3], alpha // 3)
                pygame.draw.circle(particle_surf, glow_color, (size*2, size*2), size*3)

            # Medium glow
            glow_color = (*particle['color'][:3], alpha // 2)
            pygame.draw.circle(particle_surf, glow_color, (size*2, size*2), size*2)
            # Bright inner core
            pygame.draw.circle(particle_surf, color, (size*2, size*2), size)

            surface.blit(particle_surf, (pos[0]-size*2, pos[1]-size*2))

    def get_gpu_params(self):
        """Return GPU distortion parameters for shockwave effect."""
        if self.finished or self.elapsed >= self.duration:
            return None
        progress = self.elapsed / self.duration
        strength = max(0.0, 1.0 - progress * 1.5) * 0.8
        if strength <= 0.0:
            return None
        return {
            'type': 'distortion',
            'center': (self.x, self.y),
            'strength': strength,
            'radius': self.shockwave_radius / 200.0,
        }


class ScorchEffect:
    """Fire effect for Naquadah Overload ability."""
    def __init__(self, x, y, duration=800):
        self.x = x
        self.y = y
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.particles = []
        # Create fire particles
        for i in range(40):
            self.particles.append({
                'pos': pygame.math.Vector2(x + pygame.math.Vector2(0, 0).rotate(i * 9).x * 30,
                                          y + pygame.math.Vector2(0, 0).rotate(i * 9).y * 30),
                'vel': pygame.math.Vector2(0, -2 - i * 0.1),
                'life': 1.0,
                'color': (255, 100 + i*2, 0)
            })
    
    def update(self, dt):
        """Update fire effect."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        
        for particle in self.particles[:]:
            particle['pos'] += particle['vel'] * (dt / 16.0)
            particle['life'] -= dt / self.duration
            if particle['life'] <= 0:
                self.particles.remove(particle)
        
        return True
    
    def draw(self, surface):
        """Draw fire particles."""
        for particle in self.particles:
            alpha = int(particle['life'] * 255)
            color = (*particle['color'][:3], alpha)
            pos = (int(particle['pos'].x), int(particle['pos'].y))
            size = max(1, int(particle['life'] * 8))
            particle_surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, color, (size, size), size)
            surface.blit(particle_surf, (pos[0]-size, pos[1]-size))


class CardDisintegrationEffect:
    """Stargate ring-transport dematerialization: card breaks into pixel chunks
    that stream upward with blue-white energy tint."""

    # Color presets (r, g, b) for the energy tint
    COLORS = {
        'default': (180, 220, 255),   # Blue-white (ring transport)
        'red':     (255, 100,  80),   # Scorch / iris
        'gold':    (255, 215, 100),   # Sacrifice
    }

    def __init__(self, card_image, x, y, duration=1000, color_variant='default'):
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.x = x
        self.y = y

        tint = self.COLORS.get(color_variant, self.COLORS['default'])

        # Break card image into rectangular chunks
        self.chunks = []
        if card_image is None:
            self.finished = True
            return

        cw, ch = card_image.get_size()
        chunk_w = max(4, cw // 8)   # ~6-8 px wide
        chunk_h = max(4, ch // 8)   # ~6-8 px tall
        cx, cy = cw / 2.0, ch / 2.0  # card center (local coords)
        max_dist = math.hypot(cx, cy) or 1.0

        count = 0
        for gx in range(0, cw, chunk_w):
            for gy in range(0, ch, chunk_h):
                if count >= 400:
                    break
                w = min(chunk_w, cw - gx)
                h = min(chunk_h, ch - gy)
                surf = card_image.subsurface(pygame.Rect(gx, gy, w, h)).copy()

                # Distance from center → delay: edges first, center last
                dx = (gx + w / 2.0) - cx
                dy = (gy + h / 2.0) - cy
                dist_norm = math.hypot(dx, dy) / max_dist  # 0 (center) .. 1 (edge)
                delay = (1.0 - dist_norm) * 0.45  # edges start at t=0, center at ~0.45

                self.chunks.append({
                    'surf': surf,
                    'ox': gx, 'oy': gy,             # original offset in card
                    'vx': random.uniform(-0.8, 0.8), # wander
                    'vy': random.uniform(-3.0, -1.0), # upward drift
                    'delay': delay,
                    'alpha': 255,
                    'scale': 1.0,
                    'tint': tint,
                })
                count += 1

        # Edge glow rect (original card position)
        self.glow_w = cw
        self.glow_h = ch

    def update(self, dt):
        if self.finished:
            return False
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False

        progress = self.elapsed / self.duration
        dt_factor = dt / 16.0  # normalise to ~60 fps

        for c in self.chunks:
            local_progress = max(0.0, (progress - c['delay']) / max(0.01, 1.0 - c['delay']))
            if local_progress <= 0:
                continue
            # Move
            c['ox'] += c['vx'] * dt_factor
            c['oy'] += c['vy'] * dt_factor
            c['vy'] -= 0.02 * dt_factor  # slight acceleration upward
            # Fade & shrink
            c['alpha'] = max(0, int(255 * (1.0 - local_progress)))
            c['scale'] = max(0.1, 1.0 - local_progress * 0.6)

        return True

    def draw(self, surface):
        if self.finished:
            return
        progress = self.elapsed / self.duration

        # Edge glow (first half only)
        if progress < 0.5:
            glow_alpha = int(120 * (1.0 - progress * 2))
            glow_surf = pygame.Surface((self.glow_w + 16, self.glow_h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (180, 220, 255, glow_alpha),
                             (0, 0, self.glow_w + 16, self.glow_h + 16),
                             width=3, border_radius=6)
            surface.blit(glow_surf, (self.x - 8, self.y - 8))

        for c in self.chunks:
            if c['alpha'] <= 0:
                continue
            local_progress = max(0.0,
                (progress - c['delay']) / max(0.01, 1.0 - c['delay']))
            if local_progress <= 0:
                # Still intact — draw at original position
                surface.blit(c['surf'], (self.x + c['ox'], self.y + c['oy']))
                continue

            w0, h0 = c['surf'].get_size()
            sw = max(1, int(w0 * c['scale']))
            sh = max(1, int(h0 * c['scale']))
            chunk_surf = pygame.transform.scale(c['surf'], (sw, sh))
            # Tint towards energy color
            tint_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            tint_a = int(min(200, local_progress * 255))
            tint_surf.fill((*c['tint'], tint_a))
            chunk_surf.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            chunk_surf.set_alpha(c['alpha'])
            surface.blit(chunk_surf, (self.x + c['ox'], self.y + c['oy']))

    def get_gpu_params(self):
        """Return distortion ring params (reuses existing DistortionPass shader)."""
        if self.finished:
            return None
        progress = self.elapsed / self.duration
        if progress > 0.6:
            return None
        strength = max(0.0, (0.6 - progress) / 0.6) * 0.3
        return {
            'type': 'distortion',
            'center': (self.x + self.glow_w / 2, self.y + self.glow_h / 2),
            'strength': strength,
            'radius': 0.15 + progress * 0.3,
        }


class CardMaterializationEffect:
    """Reverse disintegration: scattered particles converge into card shape
    with Stargate energy tint that fades to original colors."""

    def __init__(self, card_image, x, y, duration=800):
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.x = x
        self.y = y

        self.chunks = []
        if card_image is None:
            self.finished = True
            return

        cw, ch = card_image.get_size()
        chunk_w = max(4, cw // 8)
        chunk_h = max(4, ch // 8)
        cx, cy = cw / 2.0, ch / 2.0
        max_dist = math.hypot(cx, cy) or 1.0

        count = 0
        for gx in range(0, cw, chunk_w):
            for gy in range(0, ch, chunk_h):
                if count >= 400:
                    break
                w = min(chunk_w, cw - gx)
                h = min(chunk_h, ch - gy)
                surf = card_image.subsurface(pygame.Rect(gx, gy, w, h)).copy()

                # Scatter start positions (above and around)
                sx = gx + random.uniform(-cw * 0.8, cw * 0.8)
                sy = gy + random.uniform(-ch * 1.5, -ch * 0.3)

                # Edge chunks arrive first, center last (like disintegration reverse)
                dx = (gx + w / 2.0) - cx
                dy = (gy + h / 2.0) - cy
                dist_norm = math.hypot(dx, dy) / max_dist
                delay = (1.0 - dist_norm) * 0.3  # edges arrive first

                self.chunks.append({
                    'surf': surf,
                    'tx': gx, 'ty': gy,  # target (final) position
                    'sx': sx, 'sy': sy,  # scatter (start) position
                    'delay': delay,
                })
                count += 1

        self.card_w = cw
        self.card_h = ch
        self.card_image = card_image

    def _ease_out_cubic(self, t):
        return 1.0 - (1.0 - t) ** 3

    def update(self, dt):
        if self.finished:
            return False
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        return True

    def draw(self, surface):
        if self.finished:
            return
        progress = self.elapsed / self.duration

        for c in self.chunks:
            local_t = max(0.0, min(1.0,
                (progress - c['delay'] * 0.5) / max(0.01, 1.0 - c['delay'] * 0.5)))
            eased = self._ease_out_cubic(local_t)

            cx = c['sx'] + (c['tx'] - c['sx']) * eased
            cy = c['sy'] + (c['ty'] - c['sy']) * eased
            alpha = int(255 * min(1.0, local_t * 2.0))  # fade in quickly

            chunk_surf = c['surf'].copy()
            # Energy tint that fades as chunks lock in
            tint_amount = max(0, int(180 * (1.0 - eased)))
            if tint_amount > 0:
                tint_surf = pygame.Surface(chunk_surf.get_size(), pygame.SRCALPHA)
                tint_surf.fill((180, 220, 255, tint_amount))
                chunk_surf.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            chunk_surf.set_alpha(alpha)
            surface.blit(chunk_surf, (self.x + cx, self.y + cy))

        # Glow pulse at formation complete (last 20%)
        if progress > 0.8:
            pulse_t = (progress - 0.8) / 0.2
            glow_alpha = int(100 * math.sin(pulse_t * math.pi))
            if glow_alpha > 0:
                glow_surf = pygame.Surface((self.card_w + 20, self.card_h + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (180, 220, 255, glow_alpha),
                                 (0, 0, self.card_w + 20, self.card_h + 20),
                                 width=4, border_radius=8)
                surface.blit(glow_surf, (self.x - 10, self.y - 10))

    def get_gpu_params(self):
        """Mild distortion during convergence phase."""
        if self.finished:
            return None
        progress = self.elapsed / self.duration
        if progress > 0.5:
            return None
        strength = max(0.0, (0.5 - progress) / 0.5) * 0.2
        return {
            'type': 'distortion',
            'center': (self.x + self.card_w / 2, self.y + self.card_h / 2),
            'strength': strength,
            'radius': 0.2,
        }


class RowPowerSurgeEffect:
    """Horizontal energy wave sweeps along a row when power changes significantly.
    Blue-cyan for gain, red-orange for loss."""

    def __init__(self, row_rect, power_delta, duration=600):
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.row_rect = row_rect
        self.power_delta = power_delta
        self.is_gain = power_delta > 0

        # Wave direction: left→right for gain, right→left for loss
        self.start_x = row_rect.left if self.is_gain else row_rect.right
        self.end_x = row_rect.right if self.is_gain else row_rect.left

        # Colors
        if self.is_gain:
            self.wave_color = (100, 200, 255)  # Blue-cyan
            self.particle_color = (150, 230, 255)
        else:
            self.wave_color = (255, 120, 60)   # Red-orange
            self.particle_color = (255, 180, 100)

        # Trailing particles
        self.particles = []

    def update(self, dt):
        if self.finished:
            return False
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False

        progress = self.elapsed / self.duration
        wave_x = self.start_x + (self.end_x - self.start_x) * progress
        dt_factor = dt / 16.0

        # Spawn particles at wave front
        if random.random() < 0.6:
            self.particles.append({
                'x': wave_x + random.uniform(-5, 5),
                'y': self.row_rect.centery + random.uniform(-self.row_rect.height * 0.4,
                                                             self.row_rect.height * 0.4),
                'vx': random.uniform(-0.5, 0.5),
                'vy': random.uniform(-1.5, 1.5),
                'life': 1.0,
                'size': random.randint(2, 5),
            })

        # Update particles
        for p in self.particles[:]:
            p['x'] += p['vx'] * dt_factor
            p['y'] += p['vy'] * dt_factor
            p['life'] -= dt / (self.duration * 0.6)
            if p['life'] <= 0:
                self.particles.remove(p)

        # Cap particles
        if len(self.particles) > MAX_GENERAL_PARTICLES:
            self.particles = self.particles[-MAX_GENERAL_PARTICLES:]

        return True

    def draw(self, surface):
        if self.finished:
            return
        progress = self.elapsed / self.duration
        wave_x = self.start_x + (self.end_x - self.start_x) * progress
        fade = 1.0 - progress * 0.5  # gentle fade out

        # Glow line at wave front
        line_alpha = int(200 * fade)
        glow_surf = pygame.Surface((12, self.row_rect.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*self.wave_color, line_alpha),
                         (0, 0, 12, self.row_rect.height + 16), border_radius=4)
        # Wider glow behind
        wide_surf = pygame.Surface((30, self.row_rect.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(wide_surf, (*self.wave_color, line_alpha // 3),
                         (0, 0, 30, self.row_rect.height + 16), border_radius=8)
        surface.blit(wide_surf, (int(wave_x) - 15, self.row_rect.top - 8))
        surface.blit(glow_surf, (int(wave_x) - 6, self.row_rect.top - 8))

        # Particles
        for p in self.particles:
            alpha = int(p['life'] * 200 * fade)
            if alpha <= 0:
                continue
            size = max(1, int(p['size'] * p['life']))
            ps = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*self.particle_color, alpha), (size, size), size)
            surface.blit(ps, (int(p['x']) - size, int(p['y']) - size))


class RowWeatherEffect:
    """Weather effect that only affects specific row areas."""
    def __init__(self, weather_type, row_rect, screen_width):
        self.weather_type = weather_type
        self.row_rect = row_rect  # pygame.Rect of the affected row
        self.screen_width = screen_width
        self.particles = []
        self.duration = -1  # -1 = infinite (until cleared)
        self.active = True
        self.highlight_color = self.get_highlight_color()
        self.border_pulse = 0  # For pulsing border effect
        self.initialize_particles()
    
    def get_highlight_color(self):
        """Get the highlight color based on weather type."""
        wt = self.weather_type.lower()
        if 'ice' in wt or 'frost' in wt or 'hazard' in wt:
            return (100, 180, 255, 60)  # Light blue for ice/frost
        elif 'asteroid' in wt or 'meteor' in wt or 'storm' in wt:
            return (255, 150, 80, 55)  # Orange for asteroid/meteor
        elif 'nebula' in wt or 'fog' in wt or 'interference' in wt:
            return (200, 100, 220, 65)  # Purple for nebula
        elif 'solar' in wt:
            return (255, 200, 100, 70)  # Orange/yellow for solar
        elif 'electromagnetic' in wt or 'pulse' in wt or 'emp' in wt or 'asgard' in wt:
            return (80, 255, 200, 55)  # Cyan for EMP
        elif 'wormhole' in wt or 'stabilization' in wt or 'clear' in wt:
            return (50, 100, 200, 70)  # Deep blue for wormhole
        else:
            return (150, 150, 150, 50)  # Default grey
    
    def get_border_color(self):
        """Get animated border color for weather type."""
        wt = self.weather_type.lower()
        pulse = 0.5 + 0.5 * math.sin(self.border_pulse)
        
        if 'ice' in wt or 'frost' in wt or 'hazard' in wt:
            return (int(150 + 105 * pulse), int(200 + 55 * pulse), 255)
        elif 'asteroid' in wt or 'meteor' in wt or 'storm' in wt:
            return (255, int(120 + 80 * pulse), int(50 + 50 * pulse))
        elif 'nebula' in wt or 'fog' in wt or 'interference' in wt:
            return (int(180 + 75 * pulse), int(80 + 80 * pulse), 255)
        elif 'electromagnetic' in wt or 'pulse' in wt or 'emp' in wt:
            return (int(80 + 80 * pulse), 255, int(180 + 75 * pulse))
        elif 'wormhole' in wt or 'stabilization' in wt:
            return (int(100 + 100 * pulse), int(150 + 100 * pulse), 255)
        else:
            return (180, 180, 200)
    
    def initialize_particles(self):
        """Create weather particles constrained to row area."""
        row_x = self.row_rect.x
        row_y = self.row_rect.y
        row_width = self.row_rect.width
        row_height = self.row_rect.height
        wt = self.weather_type.lower()
        
        if 'ice' in wt or 'frost' in wt or 'hazard' in wt:
            # Ice Planet Hazard - Snowflakes/ice crystals falling
            for i in range(50):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        row_x + (i * (row_width / 50)),
                        row_y + (i * 7) % row_height
                    ),
                    'vel': pygame.math.Vector2(random.uniform(-0.5, 0.5), random.uniform(0.8, 1.8)),
                    'size': random.randint(2, 5),
                    'color': (180, 220, 255),
                    'alpha': random.randint(150, 230),
                    'rotation': random.uniform(0, 360),
                    'rot_speed': random.uniform(-2, 2)
                })
        
        elif 'asteroid' in wt or 'meteor' in wt or 'storm' in wt:
            # Asteroid Storm - Fiery meteors streaking down
            for i in range(45):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        row_x + random.randint(0, row_width),
                        row_y + random.randint(-20, row_height)
                    ),
                    'vel': pygame.math.Vector2(random.uniform(-2, -0.5), random.uniform(5, 9)),
                    'size': random.randint(2, 4),
                    'color': (255, random.randint(150, 200), random.randint(50, 100)),
                    'alpha': random.randint(180, 255),
                    'trail_length': random.randint(10, 25)
                })
        
        elif 'nebula' in wt or 'fog' in wt or 'interference' in wt:
            # Nebula Interference - Purple/pink cosmic clouds
            cloud_count = max(35, row_width // 45)
            for i in range(cloud_count):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        row_x + random.uniform(0, row_width),
                        row_y + random.uniform(0, row_height)
                    ),
                    'vel': pygame.math.Vector2(random.uniform(-0.3, 0.5), random.uniform(-0.1, 0.1)),
                    'size': random.randint(20, 45),
                    'color': (220, random.randint(100, 160), 230),
                    'alpha': random.randint(30, 60),
                    'wobble': random.uniform(0, math.pi * 2),
                    'wobble_speed': random.uniform(0.015, 0.04),
                    'layer': random.uniform(0.4, 1.0)
                })
        
        elif 'electromagnetic' in wt or 'pulse' in wt or 'emp' in wt or 'asgard' in wt:
            # Electromagnetic Pulse - Electric arcs and charged particles
            particle_count = max(50, row_width // 50)
            for i in range(particle_count):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        row_x + random.uniform(0, row_width),
                        row_y + random.uniform(0, row_height)
                    ),
                    'vel': pygame.math.Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.3, 0.3)),
                    'size': random.randint(2, 5),
                    'color': (100, 255, 200),
                    'base_alpha': random.randint(100, 180),
                    'pulse_speed': random.uniform(0.08, 0.15),
                    'pulse_phase': random.uniform(0, math.pi * 2)
                })
            # Add some arc/lightning elements
            for i in range(8):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        row_x + random.uniform(0, row_width),
                        row_y + row_height // 2
                    ),
                    'is_arc': True,
                    'arc_length': random.randint(30, 80),
                    'arc_phase': random.uniform(0, math.pi * 2),
                    'alpha': random.randint(150, 255)
                })
        
        elif 'wormhole' in wt or 'stabilization' in wt or 'clear' in wt:
            # Wormhole Stabilization - Vortex/black hole clearing effect
            center_x = self.screen_width // 2
            center_y = row_y + row_height // 2
            
            for i in range(70):
                angle = i * 5.15
                distance = i * 6
                rad = math.radians(angle)
                
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        center_x + math.cos(rad) * distance,
                        center_y + math.sin(rad) * distance
                    ),
                    'vel': pygame.math.Vector2(0, 0),
                    'size': random.randint(3, 7),
                    'color': (80, 150, 255),
                    'alpha': 255,
                    'fade_rate': random.uniform(2, 4),
                    'spiral_speed': random.uniform(0.1, 0.25),
                    'spiral_angle': angle,
                    'spiral_distance': distance,
                    'center': (center_x, center_y),
                    'max_distance': distance + 180
                })
            self.duration = 2500
            self.lifetime = 0
            
        elif 'replicator' in wt or 'swarm' in wt:
            # Replicator Swarm - Small grey blocks jittering
            for i in range(80):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        row_x + random.uniform(0, row_width),
                        row_y + random.uniform(0, row_height)
                    ),
                    'vel': pygame.math.Vector2(random.uniform(-2, 2), random.uniform(-2, 2)),
                    'size': random.randint(3, 6),
                    'color': (180, 180, 190),  # Grey metallic
                    'target_pos': pygame.math.Vector2(
                        row_x + random.uniform(0, row_width),
                        row_y + random.uniform(0, row_height)
                    ),
                    'jitter_timer': 0,
                    'block_type': True  # Mark as block for draw
                })
        
        else:
            # Default generic weather particles
            for i in range(30):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        row_x + random.uniform(0, row_width),
                        row_y + random.uniform(0, row_height)
                    ),
                    'vel': pygame.math.Vector2(random.uniform(-0.3, 0.3), random.uniform(0.5, 1.5)),
                    'size': random.randint(2, 4),
                    'color': (180, 180, 200),
                    'alpha': random.randint(120, 200)
                })
    
    def update(self, dt):
        """Update particles within row bounds."""
        if not self.active:
            return False
        
        # Update border pulse animation
        self.border_pulse += 0.08 * (dt / 16.0)
        
        # Track lifetime for timed effects
        if self.duration > 0:
            self.lifetime = getattr(self, 'lifetime', 0) + dt
            if self.lifetime >= self.duration:
                self.active = False
                return False
        
        row_x = self.row_rect.x
        row_y = self.row_rect.y
        row_width = self.row_rect.width
        row_height = self.row_rect.height
        wt = self.weather_type.lower()
        
        for particle in self.particles:
            # Skip arc particles (handled separately in draw)
            if particle.get('is_arc'):
                particle['arc_phase'] = particle.get('arc_phase', 0) + 0.15 * (dt / 16.0)
                continue

            # Handle Replicator Swarm
            if particle.get('block_type'):
                # Jitter movement toward target
                particle['jitter_timer'] += dt
                if particle['jitter_timer'] > 100:  # New target every 0.1s
                    particle['jitter_timer'] = 0
                    particle['target_pos'] = pygame.math.Vector2(
                        particle['pos'].x + random.uniform(-20, 20),
                        particle['pos'].y + random.uniform(-20, 20)
                    )
                
                # Move towards target rapidly
                diff = particle['target_pos'] - particle['pos']
                if diff.length() > 1:
                    particle['pos'] += diff.normalize() * 3 * (dt / 16.0)
                
                # Wrap
                if particle['pos'].x < row_x: particle['pos'].x = row_x + row_width
                if particle['pos'].x > row_x + row_width: particle['pos'].x = row_x
                if particle['pos'].y < row_y: particle['pos'].y = row_y + row_height
                if particle['pos'].y > row_y + row_height: particle['pos'].y = row_y
                continue
            
            particle['pos'] += particle['vel'] * (dt / 16.0)
            
            # Handle rotation for ice crystals
            if 'rotation' in particle:
                particle['rotation'] += particle.get('rot_speed', 0) * (dt / 16.0)
            
            # Handle pulse effects
            if 'pulse' in particle:
                particle['pulse'] += 0.1 * (dt / 16.0)
            
            if 'fade_rate' in particle:
                particle['alpha'] = max(0, particle['alpha'] - particle['fade_rate'] * (dt / 16.0))
            
            if 'pulse_speed' in particle:
                particle['pulse_phase'] = particle.get('pulse_phase', 0) + particle['pulse_speed'] * (dt / 16.0)
                base_alpha = particle.get('base_alpha', 120)
                intensity = 0.5 + 0.5 * math.sin(particle['pulse_phase'])
                particle['alpha'] = int(base_alpha * (0.6 + 0.4 * intensity))
            
            if 'wobble_speed' in particle:
                particle['wobble'] = particle.get('wobble', 0) + particle['wobble_speed'] * (dt / 16.0)
                particle['pos'].x += math.sin(particle['wobble']) * 0.5
                particle['alpha'] = max(20, min(120, particle.get('alpha', 60) + math.sin(particle['wobble'] * 0.8) * 5))

            # Handle spiral/vortex for clear weather
            if 'spiral_speed' in particle:
                progress = self.lifetime / self.duration if self.duration > 0 else 0
                
                if progress < 0.3:
                    expand_factor = progress / 0.3
                    particle['spiral_distance'] = particle.get('initial_distance', particle['spiral_distance']) + \
                                                 (particle.get('max_distance', 200) - particle.get('initial_distance', 100)) * expand_factor
                else:
                    particle['spiral_distance'] = max(0, particle['spiral_distance'] - 1.5 * (dt / 16.0))
                
                if 'initial_distance' not in particle:
                    particle['initial_distance'] = particle['spiral_distance']
                
                particle['spiral_angle'] += particle['spiral_speed'] * (dt / 16.0) * 15
                
                rad = math.radians(particle['spiral_angle'])
                center = particle['center']
                particle['pos'].x = center[0] + math.cos(rad) * particle['spiral_distance']
                particle['pos'].y = center[1] + math.sin(rad) * particle['spiral_distance']
                continue
            
            # Wrap particles within row bounds
            if particle['pos'].y > row_y + row_height:
                particle['pos'].y = row_y - 10
                if 'asteroid' in wt or 'meteor' in wt:
                    particle['pos'].x = row_x + random.randint(0, row_width)
            elif particle['pos'].y < row_y - 20:
                particle['pos'].y = row_y + row_height
            
            if particle['pos'].x > row_x + row_width:
                particle['pos'].x = row_x
            elif particle['pos'].x < row_x:
                particle['pos'].x = row_x + row_width
        
        return True
    
    def draw(self, surface):
        """Draw weather particles on the row."""
        if not self.active:
            return
        
        wt = self.weather_type.lower()
        
        # Draw highlighted row background first
        highlight_surf = pygame.Surface((self.row_rect.width, self.row_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(highlight_surf, self.highlight_color, highlight_surf.get_rect(), border_radius=8)
        surface.blit(highlight_surf, (self.row_rect.x, self.row_rect.y))
        
        # Draw animated pulsing border
        border_color = self.get_border_color()
        pygame.draw.rect(surface, border_color, self.row_rect, width=3, border_radius=8)
        
        for particle in self.particles:
            # Handle arc/lightning particles
            if particle.get('is_arc'):
                arc_x = int(particle['pos'].x)
                arc_y = int(particle['pos'].y)
                arc_len = particle['arc_length']
                phase = particle['arc_phase']
                
                # Draw zigzag lightning
                points = [(arc_x, arc_y)]
                for i in range(5):
                    offset_x = math.sin(phase + i * 1.5) * 15
                    offset_y = (i + 1) * (self.row_rect.height // 6)
                    points.append((arc_x + int(offset_x), arc_y + offset_y))
                
                if len(points) >= 2:
                    pygame.draw.lines(surface, (100, 255, 220, particle['alpha']), False, points, 2)
                continue

            # Handle Replicator Blocks
            if particle.get('block_type'):
                pos = (int(particle['pos'].x), int(particle['pos'].y))
                size = particle['size']
                # Draw geometric block (rectangle)
                pygame.draw.rect(surface, particle['color'], (pos[0], pos[1], size*2, size))
                pygame.draw.rect(surface, (100, 100, 110), (pos[0], pos[1], size*2, size), width=1)
                continue
            
            pos = (int(particle['pos'].x), int(particle['pos'].y))
            alpha = particle.get('alpha', 255)
            
            # Handle pulse effects for solar
            if 'pulse' in particle:
                pulse_alpha = int(alpha * (0.7 + 0.3 * math.sin(particle['pulse'])))
                alpha = pulse_alpha
            
            # EMP particles with glow
            if 'pulse_speed' in particle:
                glow_radius = particle['size'] + 4
                glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
                inner_color = (*particle['color'], alpha)
                outer_color = (particle['color'][0], particle['color'][1], particle['color'][2], alpha // 2)
                pygame.draw.circle(glow_surf, outer_color, (glow_radius, glow_radius), glow_radius, width=0)
                pygame.draw.circle(glow_surf, inner_color, (glow_radius, glow_radius), particle['size'])
                surface.blit(glow_surf, (pos[0]-glow_radius, pos[1]-glow_radius))
                continue
            
            # Nebula/fog particles
            if 'nebula' in wt or 'fog' in wt or 'interference' in wt or particle['size'] > 10:
                fog_surf = pygame.Surface((particle['size']*2, particle['size']*2), pygame.SRCALPHA)
                color = (*particle['color'], alpha)
                pygame.draw.circle(fog_surf, color, (particle['size'], particle['size']), particle['size'])
                if 'wobble_speed' in particle:
                    inner_radius = max(4, int(particle['size'] * 0.6))
                    inner_color = (
                        min(255, particle['color'][0] + 30),
                        min(255, particle['color'][1] + 20),
                        min(255, particle['color'][2] + 30),
                        alpha // 2
                    )
                    pygame.draw.circle(fog_surf, inner_color, (particle['size'], particle['size']), inner_radius)
                surface.blit(fog_surf, (pos[0]-particle['size'], pos[1]-particle['size']))
            
            # Asteroid/meteor particles - draw as fiery streaks
            elif 'asteroid' in wt or 'meteor' in wt or 'storm' in wt:
                trail_len = particle.get('trail_length', 15)
                end_pos = (int(pos[0] - particle['vel'].x * trail_len / 5), 
                          int(pos[1] - particle['vel'].y * trail_len / 5))
                
                # Draw trail (gradient effect)
                for i in range(3):
                    trail_alpha = max(50, alpha - i * 60)
                    trail_color = (*particle['color'][:3], trail_alpha) if len(particle['color']) == 3 else particle['color']
                    intermediate = (
                        int(pos[0] - particle['vel'].x * trail_len / 5 * (i / 3)),
                        int(pos[1] - particle['vel'].y * trail_len / 5 * (i / 3))
                    )
                    pygame.draw.line(surface, particle['color'], pos, intermediate, max(1, particle['size'] - i))
                
                # Draw bright head
                pygame.draw.circle(surface, (255, 255, 200), pos, particle['size'])
            
            # Ice particles - draw as small crystals
            elif 'ice' in wt or 'hazard' in wt or 'frost' in wt:
                if alpha < 255:
                    crystal_surf = pygame.Surface((particle['size']*2+2, particle['size']*2+2), pygame.SRCALPHA)
                    color = (*particle['color'], alpha)
                    center = (particle['size']+1, particle['size']+1)
                    # Draw simple crystal shape
                    pygame.draw.circle(crystal_surf, color, center, particle['size'])
                    # Add a sparkle
                    sparkle_color = (255, 255, 255, alpha // 2)
                    pygame.draw.circle(crystal_surf, sparkle_color, (center[0]-1, center[1]-1), max(1, particle['size']//2))
                    surface.blit(crystal_surf, (pos[0]-particle['size']-1, pos[1]-particle['size']-1))
                else:
                    pygame.draw.circle(surface, particle['color'], pos, particle['size'])
            
            # Default particles
            else:
                if alpha < 255:
                    circle_surf = pygame.Surface((particle['size']*2, particle['size']*2), pygame.SRCALPHA)
                    color = (*particle['color'], alpha)
                    pygame.draw.circle(circle_surf, color, (particle['size'], particle['size']), particle['size'])
                    surface.blit(circle_surf, (pos[0]-particle['size'], pos[1]-particle['size']))
                else:
                    pygame.draw.circle(surface, particle['color'], pos, particle['size'])


class MeteorShowerImpactEffect:
    """Short-lived burst of micrometeorite streaks across a single row."""
    def __init__(self, row_rect, duration=900):
        self.rect = row_rect.copy()
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.streaks = []
        self._spawn_initial_streaks()
    
    def _spawn_initial_streaks(self):
        for _ in range(30):
            self._spawn_streak()
    
    def _spawn_streak(self):
        start_x = self.rect.x + random.uniform(0, self.rect.width)
        start_y = self.rect.y - random.uniform(0, self.rect.height * 0.4)
        direction = pygame.math.Vector2(random.uniform(-0.6, -0.2), 1.0)
        direction = direction.normalize() if direction.length() else pygame.math.Vector2(0, 1)
        speed = random.uniform(450, 750)  # pixels per second
        self.streaks.append({
            "pos": pygame.math.Vector2(start_x, start_y),
            "dir": direction,
            "speed": speed,
            "length": random.uniform(35, 70),
            "alpha": random.randint(180, 255),
        })
    
    def update(self, dt):
        if self.finished:
            return False
        self.elapsed += dt
        dt_seconds = dt / 1000.0
        for streak in self.streaks:
            streak["pos"] += streak["dir"] * streak["speed"] * dt_seconds
            if streak["pos"].y > self.rect.bottom + 40:
                streak["pos"].x = self.rect.x + random.uniform(0, self.rect.width)
                streak["pos"].y = self.rect.y - random.uniform(0, self.rect.height * 0.4)
                streak["dir"] = pygame.math.Vector2(random.uniform(-0.6, -0.2), 1.0)
                if streak["dir"].length():
                    streak["dir"].scale_to_length(1)
                streak["speed"] = random.uniform(450, 750)
                streak["length"] = random.uniform(35, 70)
                streak["alpha"] = random.randint(180, 255)
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        return True
    
    def draw(self, surface):
        if self.finished:
            return
        for streak in self.streaks:
            start = (int(streak["pos"].x), int(streak["pos"].y))
            direction = pygame.math.Vector2(streak["dir"].x, streak["dir"].y)
            if direction.length() == 0:
                continue
            end_vec = streak["pos"] - direction * streak["length"]
            end = (int(end_vec.x), int(end_vec.y))
            color = (255, 220, 140, streak["alpha"])
            pygame.draw.line(surface, color, start, end, width=3)
    
    def is_finished(self):
        return self.finished


class WeatherEffect:
    """Weather overlay effect (snow, rain, fog)."""
    def __init__(self, weather_type, screen_width, screen_height):
        self.weather_type = weather_type  # 'frost', 'rain', 'fog'
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.particles = []
        self.initialize_particles()
    
    def initialize_particles(self):
        """Create weather particles."""
        if self.weather_type == 'frost':
            # Snowflakes
            for _ in range(50):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        pygame.math.Vector2(0, 0).rotate(_ * 7.2).x % self.screen_width,
                        pygame.math.Vector2(0, 0).rotate(_ * 7.2).y % self.screen_height
                    ),
                    'vel': pygame.math.Vector2(0.5, 1.5),
                    'size': 2 + (_ % 3),
                    'color': (200, 230, 255)
                })
        elif self.weather_type == 'rain':
            # Rain drops
            for _ in range(100):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        _ * (self.screen_width / 100),
                        (_ * 13) % self.screen_height
                    ),
                    'vel': pygame.math.Vector2(1, 8),
                    'size': 2,
                    'color': (100, 150, 200)
                })
        elif self.weather_type == 'fog':
            # Fog patches (larger, slower particles)
            for _ in range(30):
                self.particles.append({
                    'pos': pygame.math.Vector2(
                        (_ * 50) % self.screen_width,
                        (_ * 30) % self.screen_height
                    ),
                    'vel': pygame.math.Vector2(0.5, 0.2),
                    'size': 20 + (_ % 10),
                    'color': (150, 150, 150)
                })
    
    def update(self, dt):
        """Update weather particles."""
        for particle in self.particles:
            particle['pos'] += particle['vel'] * (dt / 16.0)
            
            # Wrap around screen
            if particle['pos'].y > self.screen_height:
                particle['pos'].y = -10
            if particle['pos'].x > self.screen_width:
                particle['pos'].x = 0
            elif particle['pos'].x < 0:
                particle['pos'].x = self.screen_width
    
    def draw(self, surface):
        """Draw weather effect."""
        for particle in self.particles:
            pos = (int(particle['pos'].x), int(particle['pos'].y))
            
            if self.weather_type == 'fog':
                # Draw semi-transparent circles for fog
                fog_surf = pygame.Surface((particle['size']*2, particle['size']*2), pygame.SRCALPHA)
                color = (*particle['color'], 40)
                pygame.draw.circle(fog_surf, color, (particle['size'], particle['size']), particle['size'])
                surface.blit(fog_surf, (pos[0]-particle['size'], pos[1]-particle['size']))
            else:
                # Draw simple particles for snow/rain
                pygame.draw.circle(surface, particle['color'], pos, particle['size'])


class ScorePopAnimation(Animation):
    """Dramatic score change animation with pop effect and optional combat text."""
    def __init__(self, old_value, new_value, x, y, duration=600, lead_burst=False, label_text=None, label_color=(255, 255, 255)):
        super().__init__(duration)
        self.old_value = old_value
        self.new_value = new_value
        self.current_value = old_value
        self.x = x
        self.y = y
        self.scale = 1.0
        self.alpha = 255
        self.offset_y = 0
        self.shake_seed = random.uniform(0, math.pi * 2)
        self.shake_strength = 0.0
        self.shake_freq = random.uniform(4.0, 6.5)
        self.lead_burst = lead_burst
        self.label_text = label_text
        self.label_color = label_color
        self.burst_particles = []
        if lead_burst:
            for _ in range(24):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(140, 260)
                size = random.randint(3, 6)
                self.burst_particles.append({
                    "angle": angle,
                    "speed": speed,
                    "dist": 0.0,
                    "alpha": 1.0,
                    "size": size
                })
    
    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()
        
        # Interpolate value
        self.current_value = int(self.old_value + (self.new_value - self.old_value) * progress)
        
        # Scale effect - pop out then settle
        if progress < 0.3:
            self.scale = 1.0 + (progress / 0.3) * 0.5  # Scale up to 1.5
        else:
            self.scale = 1.5 - ((progress - 0.3) / 0.7) * 0.5  # Scale down to 1.0
        
        # Float up slightly
        self.offset_y = -math.sin(progress * math.pi) * 20
        # Shake strongest near the start, fade out by the end
        self.shake_strength = max(0.0, (1.0 - progress) * 4.0)
        
        # Fade in at start
        if progress < 0.1:
            self.alpha = int((progress / 0.1) * 255)
        else:
            self.alpha = 255
        
        if self.lead_burst:
            for particle in self.burst_particles:
                particle["dist"] += particle["speed"] * (dt / 1000.0)
                particle["alpha"] = max(0.0, particle["alpha"] - dt / 500.0)
            self.burst_particles = [p for p in self.burst_particles if p["alpha"] > 0]
        
        return not self.finished
    
    def draw(self, surface, font):
        """Draw the animated score."""
        # Get current progress
        progress = self.get_progress()
        
        # Determine color based on change
        if self.new_value > self.old_value:
            color = (100, 255, 100)  # Green for increase
        elif self.new_value < self.old_value:
            color = (255, 100, 100)  # Red for decrease
        else:
            color = (255, 255, 255)  # White for no change
        
        # Render score with current scale
        base_text = font.render(str(self.current_value), True, color)
        
        # Scale the text
        if self.scale != 1.0:
            new_width = max(1, int(base_text.get_width() * self.scale))
            new_height = max(1, int(base_text.get_height() * self.scale))
            base_text = pygame.transform.smoothscale(base_text, (new_width, new_height))
        
        # Apply alpha
        base_text.set_alpha(self.alpha)
        
        # Compute shake offsets
        elapsed_sec = self.elapsed / 1000.0
        shake_phase = self.shake_seed + elapsed_sec * self.shake_freq * 2.5
        shake_x = math.sin(shake_phase) * self.shake_strength
        shake_y = math.cos(shake_phase * 0.85) * (self.shake_strength * 0.6)
        
        # Draw with offset
        final_y = self.y + self.offset_y + shake_y
        text_rect = base_text.get_rect(right=int(self.x + shake_x), centery=int(final_y))
        
        # Add glow effect
        if self.scale > 1.2:
            glow_surf = pygame.Surface((base_text.get_width() + 20, base_text.get_height() + 20), pygame.SRCALPHA)
            glow_color = (*color, int(self.alpha * 0.3))
            pygame.draw.ellipse(glow_surf, glow_color, glow_surf.get_rect())
            surface.blit(glow_surf, (text_rect.x - 10, text_rect.y - 10))
        
        if self.lead_burst and self.burst_particles:
            center = (int(self.x), int(final_y))
            for particle in self.burst_particles:
                px = center[0] + math.cos(particle["angle"]) * particle["dist"]
                py = center[1] + math.sin(particle["angle"]) * particle["dist"]
                alpha = int(200 * particle["alpha"])
                color = (120, 190, 255, alpha)
                burst_surf = pygame.Surface((particle["size"]*2, particle["size"]*2), pygame.SRCALPHA)
                pygame.draw.circle(burst_surf, color, (particle["size"], particle["size"]), particle["size"])
                surface.blit(burst_surf, (int(px - particle["size"]), int(py - particle["size"])))
        
        surface.blit(base_text, text_rect)
        
        # Show delta if significantly changed
        if abs(self.new_value - self.old_value) > 0 and progress < 0.8:
            delta = self.new_value - self.old_value
            delta_text = font.render(f"{'+' if delta > 0 else ''}{delta}", True, color)
            delta_text.set_alpha(int(self.alpha * (1.0 - progress / 0.8)))
            delta_y = final_y - 40 - progress * 30
            surface.blit(delta_text, (self.x - 100, int(delta_y)))

        # Show combat text label (e.g. "BUFFED!")
        if self.label_text:
            # Use smaller font for label
            label_font = pygame.font.SysFont("Arial", 16, bold=True)
            label_surf = label_font.render(self.label_text, True, self.label_color)
            
            # Fade in/out
            label_alpha = self.alpha
            if progress > 0.7:
                label_alpha = int(255 * (1.0 - (progress - 0.7) / 0.3))
            label_surf.set_alpha(label_alpha)
            
            # Position above score
            label_rect = label_surf.get_rect(bottom=text_rect.top - 5, centerx=text_rect.centerx)
            surface.blit(label_surf, label_rect)


class AmbientStarfield:
    """Moving starfield optimized with static caching for 4K performance."""
    def __init__(self, screen_width, screen_height, num_stars=150):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.stars = []
        
        # We use a smaller number of dynamic stars for "movement"
        # and pre-render a dense static field for "depth"
        self.static_stars_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        for _ in range(num_stars * 10):
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            brightness = random.randint(40, 150)
            color = (brightness, brightness, brightness, random.randint(50, 200))
            pygame.draw.circle(self.static_stars_surf, color, (x, y), random.choice([1, 1, 2]))

        # Dynamic moving stars
        for _ in range(num_stars):
            self.stars.append({
                'x': random.randint(0, screen_width),
                'y': random.randint(0, screen_height),
                'size': random.choice([1, 1, 2, 2, 3]),
                'speed': random.uniform(0.05, 0.25),
                'brightness': random.randint(150, 255),
                'twinkle_phase': random.uniform(0, 6.28)
            })
    
    def update(self, dt):
        for star in self.stars:
            star['y'] += star['speed'] * (dt / 16.0)
            if star['y'] > self.screen_height:
                star['y'] = 0
                star['x'] = random.randint(0, self.screen_width)
            star['twinkle_phase'] += 0.02 * (dt / 16.0)
    
    def draw(self, surface):
        # 1. Blit the entire static field in ONE call
        surface.blit(self.static_stars_surf, (0, 0))
        
        # 2. Draw only the few moving stars
        for star in self.stars:
            twinkle = math.sin(star['twinkle_phase']) * 0.3 + 0.7
            brightness = int(star['brightness'] * twinkle)
            color = (brightness, brightness, brightness)
            pos = (int(star['x']), int(star['y']))
            if star['size'] == 1:
                surface.set_at(pos, color)
            else:
                pygame.draw.circle(surface, color, pos, star['size'])


class ChevronGlow:
    """Subtle chevron lock glows appearing randomly on edges."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.glows = []
        self.spawn_timer = 0
        self.spawn_interval = 3000  # 3 seconds between spawns
    
    def update(self, dt):
        """Update chevron glows."""
        self.spawn_timer += dt
        
        # Spawn new glow occasionally
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.spawn_glow()
        
        # Update existing glows
        for glow in self.glows[:]:
            glow['life'] -= dt / glow['duration']
            if glow['life'] <= 0:
                self.glows.remove(glow)
    
    def spawn_glow(self):
        """Spawn a new chevron glow on screen edge."""
        edge = random.choice(['left', 'right', 'top', 'bottom'])
        
        if edge == 'left':
            x, y = 50, random.randint(100, self.screen_height - 100)
        elif edge == 'right':
            x, y = self.screen_width - 50, random.randint(100, self.screen_height - 100)
        elif edge == 'top':
            x, y = random.randint(100, self.screen_width - 100), 50
        else:  # bottom
            x, y = random.randint(100, self.screen_width - 100), self.screen_height - 50
        
        self.glows.append({
            'x': x,
            'y': y,
            'life': 1.0,
            'duration': 2000,  # 2 seconds
            'color': (255, 140, 0)  # Orange chevron color
        })
    
    def draw(self, surface):
        """Draw chevron glows."""
        for glow in self.glows:
            alpha = int(glow['life'] * 150)  # Fade in and out
            size = int(20 + (1.0 - glow['life']) * 10)  # Expand slightly
            
            # Create glow surface
            glow_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color = (*glow['color'], alpha)
            
            # Draw multiple circles for glow effect
            for i in range(3):
                radius = size - i * 5
                if radius > 0:
                    a = alpha // (i + 1)
                    pygame.draw.circle(glow_surf, (*glow['color'], a), (size, size), radius)
            
            surface.blit(glow_surf, (glow['x'] - size, glow['y'] - size))


class EnergyWave:
    """Subtle energy waves across the background."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.waves = []
        self.spawn_timer = 0
        self.spawn_interval = 5000  # 5 seconds
    
    def update(self, dt):
        """Update energy waves."""
        self.spawn_timer += dt
        
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.spawn_wave()
        
        # Update waves
        for wave in self.waves[:]:
            wave['progress'] += dt / wave['duration']
            if wave['progress'] >= 1.0:
                self.waves.remove(wave)
    
    def spawn_wave(self):
        """Spawn a new energy wave."""
        self.waves.append({
            'start_x': random.randint(0, self.screen_width),
            'start_y': random.randint(0, self.screen_height),
            'progress': 0.0,
            'duration': 3000,
            'color': (100, 150, 255),  # Blue energy
            'direction': random.choice(['horizontal', 'vertical'])
        })
    
    def draw(self, surface):
        """Draw energy waves."""
        for wave in self.waves:
            alpha = int((1.0 - wave['progress']) * 80)  # Fade out
            
            if wave['direction'] == 'horizontal':
                # Horizontal wave
                y = wave['start_y']
                x_offset = int(wave['progress'] * self.screen_width)
                
                for i in range(-50, 50, 10):
                    x = (wave['start_x'] + x_offset + i) % self.screen_width
                    fade = 1.0 - abs(i) / 50.0
                    color = (*wave['color'], int(alpha * fade))
                    pygame.draw.circle(surface, color, (x, y), 3)
            else:
                # Vertical wave
                x = wave['start_x']
                y_offset = int(wave['progress'] * self.screen_height)
                
                for i in range(-50, 50, 10):
                    y = (wave['start_y'] + y_offset + i) % self.screen_height
                    fade = 1.0 - abs(i) / 50.0
                    color = (*wave['color'], int(alpha * fade))
                    pygame.draw.circle(surface, color, (x, y), 3)


class BattleShip:
    """Animated ship in space battle."""
    def __init__(self, x, y, faction, ship_name, is_player, screen_height=1080):
        self.x = x
        self.y = y
        self.faction = faction
        self.ship_name = ship_name
        self.is_player = is_player  # True for player ships, False for enemy
        self.scale = get_scale_factor(screen_height)
        self.size = int(120 * self.scale)  # Ship art size scaled for resolution
        self.velocity_x = random.uniform(-0.3, 0.3)
        self.velocity_y = random.uniform(-0.2, 0.2)
        self.fire_cooldown = 0
        self.fire_interval = random.randint(2000, 4000)  # 2-4 seconds between shots
        self.shield_active = False
        self.shield_timer = 0
        self.rotation = 90 if is_player else 270  # Player ships point up (90°), enemy down (270°)
        self.raw_image = None
        
        # Faction colors (for fallback and effects)
        self.colors = {
            "Tau'ri": (100, 150, 255),
            "Goa'uld": (200, 50, 50),
            "Jaffa Rebellion": (200, 140, 50),
            "Lucian Alliance": (150, 50, 150),
            "Asgard": (50, 200, 150),
        }
        self.color = self.colors.get(faction, (150, 150, 150))
        
        # Try to load ship art
        self.image = None
        self.load_ship_image()
    
    def load_ship_image(self):
        """Try to load custom ship art from assets/ships/ folder."""
        import os
        
        # Create safe filename from ship name
        safe_name = self.ship_name.lower().replace(" ", "_").replace("'", "")
        
        # Try multiple paths
        possible_paths = [
            f"assets/ships/{self.faction.lower().replace(' ', '_')}_{safe_name}.png",
            f"assets/ships/{safe_name}.png",
            f"assets/ships/{self.faction.lower().replace(' ', '_')}_ship.png",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    loaded_img = pygame.image.load(path).convert_alpha()
                    scaled_image = pygame.transform.scale(loaded_img, (self.size, self.size))
                    self.raw_image = scaled_image
                    self.image = pygame.transform.rotate(self.raw_image, self.rotation)
                    return
                except:
                    continue
    
        # No image found - will use placeholder triangle
        self.raw_image = None
        self.image = None

    def set_side(self, is_player):
        """Switch ship to player/enemy side with correct orientation."""
        if self.is_player == is_player:
            return
        self.is_player = is_player
        self.rotation = 90 if is_player else 270
        if self.raw_image:
            self.image = pygame.transform.rotate(self.raw_image, self.rotation)
    
    def update(self, dt, screen_width, screen_height):
        """Update ship position and state."""
        # Drift slowly
        self.x += self.velocity_x * (dt / 16.0)
        self.y += self.velocity_y * (dt / 16.0)
        
        # Bounce off edges
        if self.x < 50 or self.x > screen_width - 50:
            self.velocity_x *= -1
        if self.y < 50 or self.y > screen_height - 50:
            self.velocity_y *= -1
        
        # Keep in bounds
        self.x = max(50, min(screen_width - 50, self.x))
        self.y = max(50, min(screen_height - 50, self.y))
        
        # Update fire cooldown
        self.fire_cooldown += dt
        
        # Update shield
        if self.shield_active:
            self.shield_timer += dt
            if self.shield_timer > 500:  # Shield lasts 0.5 seconds
                self.shield_active = False
                self.shield_timer = 0
    
    def can_fire(self):
        """Check if ship can fire."""
        return self.fire_cooldown >= self.fire_interval
    
    def fire(self):
        """Fire a laser and reset cooldown."""
        self.fire_cooldown = 0
        self.fire_interval = random.randint(2000, 4000)
    
    def activate_shield(self):
        """Activate shield when hit by laser."""
        self.shield_active = True
        self.shield_timer = 0
    
    def draw(self, surface):
        """Draw the ship."""
        size = self.size
        
        if self.image:
            # Draw custom ship image
            img_rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(self.image, img_rect)
            
            # Engine glow overlay (optional, adds nice effect)
            engine_surf = pygame.Surface((size // 2, size // 2), pygame.SRCALPHA)
            engine_color = (*self.color, 120)
            if self.is_player:
                glow_pos = (int(self.x), int(self.y + size // 3))
            else:
                glow_pos = (int(self.x), int(self.y - size // 3))
            pygame.draw.circle(engine_surf, engine_color, (size // 4, size // 4), size // 6)
            surface.blit(engine_surf, (glow_pos[0] - size // 4, glow_pos[1] - size // 4))
        else:
            # Fallback: Draw triangle placeholder
            if self.is_player:
                # Point up for player ships
                points = [
                    (self.x, self.y - size // 2),
                    (self.x - size // 3, self.y + size // 2),
                    (self.x + size // 3, self.y + size // 2)
                ]
            else:
                # Point down for enemy ships
                points = [
                    (self.x, self.y + size // 2),
                    (self.x - size // 3, self.y - size // 2),
                    (self.x + size // 3, self.y - size // 2)
                ]
            
            # Draw ship with faction color
            pygame.draw.polygon(surface, self.color, points)
            pygame.draw.polygon(surface, (255, 255, 255), points, 2)  # White outline
            
            # Engine glow
            engine_color = (*self.color, 150)
            engine_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            if self.is_player:
                pygame.draw.circle(engine_surf, engine_color, (size // 2, size - 5), 5)
            else:
                pygame.draw.circle(engine_surf, engine_color, (size // 2, 5), 5)
            surface.blit(engine_surf, (int(self.x - size // 2), int(self.y - size // 2)))
        
        # Shield effect (always drawn regardless of ship type)
        if self.shield_active:
            # Shield should bubble the entire ship (120x120)
            shield_progress = self.shield_timer / 500  # 0 to 1
            shield_alpha = int((1.0 - shield_progress) * 220)  # Fade out
            
            # Shield bubble size - starts slightly larger, shrinks as fades
            shield_radius = int(size * 0.75 * (1.0 + shield_progress * 0.1))  # 90px to 99px
            
            # Create shield surface large enough for the bubble
            shield_surf_size = shield_radius * 3
            shield_surf = pygame.Surface((shield_surf_size, shield_surf_size), pygame.SRCALPHA)
            center = shield_surf_size // 2
            
            # Draw multiple shield layers for depth
            # Outer glow
            outer_alpha = shield_alpha // 3
            pygame.draw.circle(shield_surf, (80, 180, 255, outer_alpha), 
                             (center, center), shield_radius + 8)
            
            # Main shield bubble
            pygame.draw.circle(shield_surf, (100, 200, 255, shield_alpha), 
                             (center, center), shield_radius)
            
            # Inner bright ring
            inner_alpha = min(255, int(shield_alpha * 1.3))
            pygame.draw.circle(shield_surf, (150, 220, 255, inner_alpha), 
                             (center, center), shield_radius, 4)
            
            # Highlight shimmer (top-left)
            shimmer_alpha = int(shield_alpha * 0.6)
            shimmer_x = center - shield_radius // 3
            shimmer_y = center - shield_radius // 3
            pygame.draw.circle(shield_surf, (200, 240, 255, shimmer_alpha), 
                             (shimmer_x, shimmer_y), shield_radius // 4)
            
            # Blit shield centered on ship
            shield_x = int(self.x - center)
            shield_y = int(self.y - center)
            surface.blit(shield_surf, (shield_x, shield_y))


class Laser:
    """Laser beam fired between ships."""
    def __init__(self, start_x, start_y, target_x, target_y, color):
        self.start_x = start_x
        self.start_y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.color = color
        self.progress = 0.0
        self.speed = 0.05  # Travel speed
        self.hit = False
    
    def update(self, dt):
        """Update laser travel."""
        self.progress += self.speed * (dt / 16.0)
        return self.progress < 1.0
    
    def get_current_position(self):
        """Get current laser position."""
        current_x = self.start_x + (self.target_x - self.start_x) * self.progress
        current_y = self.start_y + (self.target_y - self.start_y) * self.progress
        return (current_x, current_y)
    
    def draw(self, surface):
        """Draw the laser."""
        if self.progress < 1.0:
            current_x, current_y = self.get_current_position()
            
            # Draw laser beam
            pygame.draw.line(surface, self.color, 
                           (self.start_x, self.start_y), 
                           (int(current_x), int(current_y)), 3)
            
            # Laser head glow
            glow_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
            glow_color = (*self.color, 200)
            pygame.draw.circle(glow_surf, glow_color, (10, 10), 8)
            surface.blit(glow_surf, (int(current_x - 10), int(current_y - 10)))


class SpaceBattle:
    """Manages space battle with ships and lasers."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.player_ships = []
        self.enemy_ships = []
        self.lasers = []
        self.round_active = False
    
    def add_ship(self, faction, ship_name, is_player):
        """Add a ship to the battle."""
        if not self.round_active:
            return
        
        # Position ships on their side
        if is_player:
            x = random.randint(100, self.screen_width - 100)
            y = random.randint(self.screen_height // 2 + 100, self.screen_height - 150)
            ship = BattleShip(x, y, faction, ship_name, True, self.screen_height)
            self.player_ships.append(ship)
        else:
            x = random.randint(100, self.screen_width - 100)
            y = random.randint(100, self.screen_height // 2 - 100)
            ship = BattleShip(x, y, faction, ship_name, False, self.screen_height)
            self.enemy_ships.append(ship)
    
    def start_round(self):
        """Start a new round of battle."""
        self.round_active = True
        self.player_ships = []
        self.enemy_ships = []
        self.lasers = []
    
    def end_round(self):
        """End the current round."""
        self.round_active = False
        self.player_ships = []
        self.enemy_ships = []
        self.lasers = []
    
    def update(self, dt):
        """Update all ships and lasers."""
        if not self.round_active:
            return
        
        # Update player ships
        for ship in self.player_ships:
            ship.update(dt, self.screen_width, self.screen_height)
            
            # Try to fire at enemy ships
            if ship.can_fire() and self.enemy_ships:
                target = random.choice(self.enemy_ships)
                laser = Laser(ship.x, ship.y, target.x, target.y, ship.color)
                self.lasers.append((laser, target))
                ship.fire()
        
        # Update enemy ships
        for ship in self.enemy_ships:
            ship.update(dt, self.screen_width, self.screen_height)
            
            # Try to fire at player ships
            if ship.can_fire() and self.player_ships:
                target = random.choice(self.player_ships)
                laser = Laser(ship.x, ship.y, target.x, target.y, ship.color)
                self.lasers.append((laser, target))
                ship.fire()
        
        # Update lasers
        for laser, target in self.lasers[:]:
            if not laser.update(dt):
                # Laser reached target - activate shield
                target.activate_shield()
                self.lasers.remove((laser, target))
    
    def draw(self, surface):
        """Draw all battle elements."""
        if not self.round_active:
            return
        
        # Draw lasers first (behind ships)
        for laser, target in self.lasers:
            laser.draw(surface)
        
        # Draw ships
        for ship in self.player_ships:
            ship.draw(surface)
        for ship in self.enemy_ships:
            ship.draw(surface)

    def transfer_ship_to_player(self, ship_name):
        """Move a ship from enemy fleet to player fleet (used by Apophis ability)."""
        if not self.round_active:
            return False
        for ship in self.enemy_ships:
            if ship.ship_name == ship_name:
                self.enemy_ships.remove(ship)
                ship.set_side(True)
                ship.y = random.randint(self.screen_height // 2 + 80, self.screen_height - 120)
                ship.velocity_y = abs(ship.velocity_y)
                self.player_ships.append(ship)
                self.lasers = [(laser, target) for laser, target in self.lasers if target != ship]
                return True
        return False


class AsteroidField:
    """Animated asteroids for round 3 - makes the battle feel more dangerous."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.asteroids = []
        self.active = False
    
    def activate(self):
        """Activate asteroid field for round 3."""
        if not self.active:
            self.active = True
            self.spawn_initial_asteroids()
    
    def deactivate(self):
        """Deactivate asteroid field."""
        self.active = False
        self.asteroids = []
    
    def spawn_initial_asteroids(self):
        """Spawn initial set of asteroids."""
        # Create mix of small and big asteroids
        num_small = random.randint(8, 12)
        num_big = random.randint(3, 5)
        
        for _ in range(num_small):
            self.spawn_asteroid(size='small')
        for _ in range(num_big):
            self.spawn_asteroid(size='big')
    
    def spawn_asteroid(self, size='small'):
        """Spawn a single asteroid."""
        if size == 'small':
            radius = random.randint(3, 8)
            speed = random.uniform(0.3, 0.8)
        else:  # big
            radius = random.randint(12, 20)
            speed = random.uniform(0.15, 0.4)
        
        asteroid = {
            'x': random.randint(0, self.screen_width),
            'y': random.randint(0, self.screen_height),
            'radius': radius,
            'speed_x': random.uniform(-speed, speed),
            'speed_y': random.uniform(0.2, speed),
            'rotation': random.uniform(0, 360),
            'rotation_speed': random.uniform(-2, 2),
            'color': random.choice([
                (90, 85, 80),   # Gray
                (100, 95, 85),  # Light gray  
                (80, 75, 70),   # Dark gray
                (95, 85, 75),   # Brown-gray
            ]),
            'size': size
        }
        self.asteroids.append(asteroid)
    
    def update(self, dt):
        """Update asteroid positions and rotation."""
        if not self.active:
            return
        
        for asteroid in self.asteroids:
            # Move asteroid
            asteroid['x'] += asteroid['speed_x'] * (dt / 16.0)
            asteroid['y'] += asteroid['speed_y'] * (dt / 16.0)
            asteroid['rotation'] += asteroid['rotation_speed'] * (dt / 16.0)
            
            # Wrap around screen edges
            if asteroid['x'] < -asteroid['radius']:
                asteroid['x'] = self.screen_width + asteroid['radius']
            elif asteroid['x'] > self.screen_width + asteroid['radius']:
                asteroid['x'] = -asteroid['radius']
            
            if asteroid['y'] > self.screen_height + asteroid['radius']:
                asteroid['y'] = -asteroid['radius']
                asteroid['x'] = random.randint(0, self.screen_width)
    
    def draw(self, surface):
        """Draw asteroids."""
        if not self.active:
            return
        
        for asteroid in self.asteroids:
            pos = (int(asteroid['x']), int(asteroid['y']))
            radius = asteroid['radius']
            
            # Draw asteroid as irregular circle (multiple overlapping circles for rough texture)
            # Main body
            pygame.draw.circle(surface, asteroid['color'], pos, radius)
            
            # Add some darker spots for craters/texture
            if radius > 5:
                num_spots = 2 if asteroid['size'] == 'small' else 4
                for i in range(num_spots):
                    angle = asteroid['rotation'] + (i * 360 / num_spots)
                    offset_x = int(math.cos(math.radians(angle)) * radius * 0.4)
                    offset_y = int(math.sin(math.radians(angle)) * radius * 0.4)
                    spot_pos = (pos[0] + offset_x, pos[1] + offset_y)
                    spot_radius = max(1, radius // 4)
                    darker_color = tuple(max(0, c - 15) for c in asteroid['color'])
                    pygame.draw.circle(surface, darker_color, spot_pos, spot_radius)


class AmbientBackgroundEffects:
    """Manager for all ambient background effects."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.starfield = AmbientStarfield(screen_width, screen_height, num_stars=150)
        self.chevrons = ChevronGlow(screen_width, screen_height)
        self.energy_waves = EnergyWave(screen_width, screen_height)
        self.space_battle = SpaceBattle(screen_width, screen_height)
        self.asteroids = AsteroidField(screen_width, screen_height)
        self.current_round = 1
        
    def update(self, dt):
        """Update all ambient effects."""
        self.starfield.update(dt)
        self.chevrons.update(dt)
        self.energy_waves.update(dt)
        self.space_battle.update(dt)
        self.asteroids.update(dt)
    
    def draw(self, surface):
        """Draw all ambient effects (call after drawing board background)."""
        self.starfield.draw(surface)
        self.asteroids.draw(surface)  # Draw asteroids over stars
        self.energy_waves.draw(surface)
        self.space_battle.draw(surface)  # Draw battle OVER stars and waves
        self.chevrons.draw(surface)
    
    def add_ship(self, faction, ship_name, is_player):
        """Add a ship to the space battle."""
        self.space_battle.add_ship(faction, ship_name, is_player)
    
    def transfer_ship_to_player(self, ship_name):
        """Transfer a ship from enemy fleet to player fleet."""
        self.space_battle.transfer_ship_to_player(ship_name)
    
    def start_round(self, round_number=None):
        """Start a new round of space battle."""
        if round_number is not None:
            self.current_round = round_number
            # Activate asteroids only in round 3
            if round_number == 3:
                self.asteroids.activate()
            else:
                self.asteroids.deactivate()
        self.space_battle.start_round()
    
    def end_round(self):
        """End the current round."""
        self.space_battle.end_round()


class HeroEntryAnimation:
    """Base class for hero entry animations."""
    def __init__(self, x, y, duration=1500):
        self.x = x
        self.y = y
        self.duration = duration
        self.elapsed = 0
        self.finished = False
    
    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return False
        return True
    
    def get_progress(self):
        return min(1.0, self.elapsed / self.duration)
    
    def draw(self, surface):
        pass


class ONeillWormholeEntry(HeroEntryAnimation):
    """O'Neill arrives through unstable vortex (wormhole establishment)."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1800)
        self.particles = []
        # Create wormhole particles
        for i in range(50):
            angle = random.uniform(0, 360)
            distance = random.uniform(50, 200)
            self.particles.append({
                'angle': angle,
                'distance': distance,
                'speed': random.uniform(3, 8),
                'size': random.randint(2, 5),
                'color': (100, 180, 255)
            })
    
    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()
        # Pull particles inward
        for p in self.particles:
            p['distance'] = max(0, p['distance'] - p['speed'] * (dt / 16.0))
        return not self.finished
    
    def draw(self, surface):
        progress = self.get_progress()
        # Draw event horizon ring
        alpha = int((1.0 - progress) * 180)
        for i in range(3):
            radius = int(100 * (1 - progress * 0.7)) + i * 10
            ring_surf = pygame.Surface((radius*2 + 20, radius*2 + 20), pygame.SRCALPHA)
            color = (100 + i*30, 150 + i*30, 255, alpha // (i+1))
            pygame.draw.circle(ring_surf, color, (radius + 10, radius + 10), radius, width=4)
            surface.blit(ring_surf, (int(self.x - radius - 10), int(self.y - radius - 10)))
        
        # Draw particles
        for p in self.particles:
            rad = math.radians(p['angle'])
            px = self.x + math.cos(rad) * p['distance']
            py = self.y + math.sin(rad) * p['distance']
            pygame.draw.circle(surface, p['color'], (int(px), int(py)), p['size'])


class CarterTechExplosion(HeroEntryAnimation):
    """Carter appears with naquadah reactor energy burst."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1500)
        self.rings = []
        for i in range(5):
            self.rings.append({'delay': i * 150, 'started': False})
    
    def draw(self, surface):
        progress = self.get_progress()
        for i, ring in enumerate(self.rings):
            if self.elapsed >= ring['delay'] and not ring['started']:
                ring['started'] = True
            
            if ring['started']:
                ring_progress = min(1.0, (self.elapsed - ring['delay']) / (self.duration - ring['delay']))
                radius = int(30 + ring_progress * 120)
                alpha = int((1 - ring_progress) * 200)
                
                ring_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                color = (100, 200, 255, alpha)
                pygame.draw.circle(ring_surf, color, (radius, radius), radius, width=3)
                surface.blit(ring_surf, (int(self.x - radius), int(self.y - radius)))


class JacksonAscensionGlow(HeroEntryAnimation):
    """Daniel Jackson materializes with ascension energy."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=2000)
        self.particles = []
        for _ in range(80):
            self.particles.append({
                'x': x + random.uniform(-100, 100),
                'y': y + random.uniform(100, 200),
                'vy': random.uniform(-2, -4),
                'size': random.randint(2, 6),
                'alpha': random.randint(150, 255)
            })
    
    def update(self, dt):
        super().update(dt)
        for p in self.particles:
            p['y'] += p['vy'] * (dt / 16.0)
        return not self.finished
    
    def draw(self, surface):
        progress = self.get_progress()
        # Draw glowing particles rising
        for p in self.particles:
            alpha = int(p['alpha'] * (1 - progress))
            color = (255, 255, 200, alpha)
            surf = pygame.Surface((p['size']*2, p['size']*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (p['size'], p['size']), p['size'])
            surface.blit(surf, (int(p['x'] - p['size']), int(p['y'] - p['size'])))


class TealcStaffBlast(HeroEntryAnimation):
    """Teal'c arrives with staff weapon energy blast."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1200)
    
    def draw(self, surface):
        progress = self.get_progress()
        if progress < 0.3:
            # Charging phase
            charge = progress / 0.3
            radius = int(20 * charge)
            alpha = int(255 * charge)
            surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 150, 50, alpha), (radius, radius), radius)
            surface.blit(surf, (int(self.x - radius), int(self.y - radius)))
        else:
            # Blast expansion
            blast_progress = (progress - 0.3) / 0.7
            radius = int(20 + blast_progress * 100)
            alpha = int(200 * (1 - blast_progress))
            surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 180, 80, alpha), (radius, radius), radius, width=5)
            surface.blit(surf, (int(self.x - radius), int(self.y - radius)))


class ApophisSnakeEyes(HeroEntryAnimation):
    """Apophis appears with glowing Goa'uld eyes effect."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1600)
    
    def draw(self, surface):
        progress = self.get_progress()
        # Eye glow effect - two glowing orbs
        alpha = int(math.sin(progress * math.pi) * 255)
        
        # Left eye
        eye_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(eye_surf, (255, 200, 50, alpha), (15, 15), 12)
        pygame.draw.circle(eye_surf, (255, 150, 0, alpha), (15, 15), 8)
        surface.blit(eye_surf, (int(self.x - 30), int(self.y - 40)))
        
        # Right eye
        surface.blit(eye_surf, (int(self.x + 10), int(self.y - 40)))
        
        # Energy waves
        if progress > 0.3:
            wave_progress = (progress - 0.3) / 0.7
            radius = int(50 + wave_progress * 80)
            wave_alpha = int((1 - wave_progress) * 150)
            wave_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(wave_surf, (255, 180, 50, wave_alpha), (radius, radius), radius, width=3)
            surface.blit(wave_surf, (int(self.x - radius), int(self.y - radius)))


class AsgardBeamIn(HeroEntryAnimation):
    """Asgard heroes beam in with transport beam."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1400)
        self.beam_particles = []
        for i in range(30):
            self.beam_particles.append({
                'x': x + random.uniform(-15, 15),
                'y': y + 200,
                'target_y': y + random.uniform(-30, 30),
                'speed': random.uniform(4, 8)
            })
    
    def update(self, dt):
        super().update(dt)
        for p in self.beam_particles:
            if p['y'] > p['target_y']:
                p['y'] -= p['speed'] * (dt / 16.0)
        return not self.finished
    
    def draw(self, surface):
        progress = self.get_progress()
        # Draw beam column
        beam_alpha = int((1 - abs(progress - 0.5) * 2) * 180)
        beam_surf = pygame.Surface((60, 250), pygame.SRCALPHA)
        pygame.draw.rect(beam_surf, (200, 230, 255, beam_alpha), beam_surf.get_rect())
        surface.blit(beam_surf, (int(self.x - 30), int(self.y - 200)))
        
        # Draw particles
        for p in self.beam_particles:
            alpha = int(beam_alpha * 1.2)
            pygame.draw.circle(surface, (220, 240, 255, min(255, alpha)), (int(p['x']), int(p['y'])), 3)


class SokarFireLord(HeroEntryAnimation):
    """Sokar emerges from flames."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1700)
        self.flames = []
        for i in range(50):
            self.flames.append({
                'x': x + random.uniform(-60, 60),
                'y': y + random.uniform(-20, 60),
                'vy': random.uniform(-3, -1),
                'size': random.randint(4, 10),
                'life': random.uniform(0.5, 1.0)
            })
    
    def update(self, dt):
        super().update(dt)
        for f in self.flames:
            f['y'] += f['vy'] * (dt / 16.0)
            f['life'] -= dt / 2000
        return not self.finished
    
    def draw(self, surface):
        for f in self.flames:
            if f['life'] > 0:
                alpha = int(f['life'] * 255)
                # Gradient from yellow to red
                color = (255, int(150 * f['life']), 0, min(255, alpha))
                surf = pygame.Surface((f['size']*2, f['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (f['size'], f['size']), f['size'])
                surface.blit(surf, (int(f['x'] - f['size']), int(f['y'] - f['size'])))


class AscendedBeingEntry(HeroEntryAnimation):
    """Ascended beings (Daniel, Oma) materialize with divine light."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=2200)
        self.rays = []
        for i in range(12):
            angle = i * 30
            self.rays.append({'angle': angle, 'length': 0})
    
    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()
        for ray in self.rays:
            ray['length'] = progress * 150
        return not self.finished
    
    def draw(self, surface):
        progress = self.get_progress()
        alpha = int(math.sin(progress * math.pi) * 200)
        
        # Draw rays of light
        for ray in self.rays:
            rad = math.radians(ray['angle'])
            end_x = self.x + math.cos(rad) * ray['length']
            end_y = self.y + math.sin(rad) * ray['length']
            
            # Draw multiple lines for glow effect
            for width in [8, 5, 2]:
                line_alpha = alpha // (9 - width)
                pygame.draw.line(surface, (255, 255, 220, line_alpha), 
                               (int(self.x), int(self.y)), 
                               (int(end_x), int(end_y)), width)
        
        # Central glow
        glow_radius = int(30 + progress * 40)
        glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 255, 200, alpha), (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surf, (int(self.x - glow_radius), int(self.y - glow_radius)))


def create_hero_animation(hero_name, x, y):
    """Factory function to create the appropriate hero animation."""
    hero_animations = {
        "Col. Jack O'Neill": ONeillWormholeEntry,
        "Dr. Samantha Carter": CarterTechExplosion,
        "Dr. Daniel Jackson": JacksonAscensionGlow,
        "Teal'c": TealcStaffBlast,
        "Apophis": ApophisSnakeEyes,
        "Sokar": SokarFireLord,
        "Lord Yu": ApophisSnakeEyes,  # Similar Goa'uld effect
        "Hathor": ApophisSnakeEyes,  # Similar Goa'uld effect
        "Isis": ApophisSnakeEyes,  # Similar Goa'uld effect
        "Bra'tac": TealcStaffBlast,  # Similar Jaffa warrior effect
        "Master Bra'tac": TealcStaffBlast,
        "Rak'nor": TealcStaffBlast,
        "Freyr": AsgardBeamIn,
        "Loki": AsgardBeamIn,
        "Heimdall": AsgardBeamIn,
        "Ascended Daniel Jackson": AscendedBeingEntry,
        "Oma Desala": AscendedBeingEntry,
        "Dr. Rodney McKay": CarterTechExplosion,  # Tech genius like Carter
        "Teyla Emmagan": TealcStaffBlast,  # Warrior entry
        "Dr. Elizabeth Weir": CarterTechExplosion,  # Diplomatic/tech leader
        "Vulkar": ApophisSnakeEyes,  # Villain effect
        "The Sodan Master": TealcStaffBlast,  # Warrior
        "Ba'al Clone": ApophisSnakeEyes,  # Goa'uld
        "Gen. George Hammond": ONeillWormholeEntry,  # Tau'ri command
        "Jonas Quinn": JacksonAscensionGlow,  # Similar to Daniel
        "Sg. Curtis": TealcStaffBlast,  # Military
        # NEW UNLOCKABLE LEADERS with unique animations
        "Catherine Langford": AscendedBeingEntry,  # Ancient wisdom
        "Ba'al": ApophisSnakeEyes,  # Goa'uld clone master
        "Anubis": SokarFireLord,  # Dark ascended being
        "Cronus": ApophisSnakeEyes,  # Ancient System Lord
        "Ka'lel": TealcStaffBlast,  # Jaffa warrior
        "Gerak": TealcStaffBlast,  # Jaffa leader
        "Ishta": TealcStaffBlast,  # Hak'tyl leader
        "Netan": ApophisSnakeEyes,  # Crime lord energy
        "Vala Mal Doran": CarterTechExplosion,  # Flashy entrance
        "Anateo": ApophisSnakeEyes,  # Lucian Alliance
        "Kiva": TealcStaffBlast,  # Combat specialist
        "Thor Supreme Commander": AsgardBeamIn,  # Supreme commander beam
        "Hermiod": AsgardBeamIn,  # Asgard engineer
        "Penegal": AsgardBeamIn,  # Asgard high council
        "Aegir": AsgardBeamIn,  # Asgard high council
        "Gen. Landry": ONeillWormholeEntry,  # SGC commander
        "Dr. McKay": CarterTechExplosion,  # Genius scientist
        "Hathor (Unlockable)": ApophisSnakeEyes,  # Goa'uld seductress
    }
    
    animation_class = hero_animations.get(hero_name, StargateActivationEffect)
    if animation_class in [ONeillWormholeEntry, CarterTechExplosion, JacksonAscensionGlow, 
                           TealcStaffBlast, ApophisSnakeEyes, AsgardBeamIn, SokarFireLord, 
                           AscendedBeingEntry]:
        return animation_class(x, y)
    else:
        return animation_class(x, y, duration=1000)


class MoraleBoostEffect(HeroEntryAnimation):
    """Green inspiring aura that radiates outward."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1200)
        self.pulses = []
        for i in range(3):
            self.pulses.append({'delay': i * 300, 'started': False})
    
    def draw(self, surface):
        progress = self.get_progress()
        
        for i, pulse in enumerate(self.pulses):
            if self.elapsed >= pulse['delay'] and not pulse['started']:
                pulse['started'] = True
            
            if pulse['started']:
                pulse_progress = min(1.0, (self.elapsed - pulse['delay']) / (self.duration - pulse['delay']))
                radius = int(20 + pulse_progress * 80)
                alpha = int((1 - pulse_progress) * 150)
                
                # Green inspiring aura
                ring_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (100, 255, 100, alpha), (radius, radius), radius, width=3)
                surface.blit(ring_surf, (int(self.x - radius), int(self.y - radius)))


class VampireEffect(HeroEntryAnimation):
    """Red draining energy that flows from opponent to player."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1000)
        self.particles = []
        for _ in range(15):
            self.particles.append({
                'x': x,
                'y': y - random.uniform(30, 50),
                'vy': random.uniform(2, 4),
                'alpha': 255
            })
    
    def update(self, dt):
        super().update(dt)
        for p in self.particles:
            p['y'] += p['vy'] * (dt / 16.0)
            p['alpha'] = max(0, p['alpha'] - 3 * (dt / 16.0))
        return not self.finished
    
    def draw(self, surface):
        for p in self.particles:
            if p['alpha'] > 0:
                color = (255, 50, 50, int(p['alpha']))
                surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (4, 4), 4)
                surface.blit(surf, (int(p['x'] - 4), int(p['y'] - 4)))


class CroneEffect(HeroEntryAnimation):
    """Purple curse effect that spreads across row."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1400)
    
    def draw(self, surface):
        progress = self.get_progress()
        
        # Purple curse waves
        wave_width = int(progress * 800)
        alpha = int(math.sin(progress * math.pi) * 180)
        
        # Draw curse wave expanding left and right
        for offset in range(-wave_width, wave_width, 20):
            x_pos = self.x + offset
            y_offset = math.sin((progress * 10 + offset * 0.02)) * 15
            
            curse_surf = pygame.Surface((25, 25), pygame.SRCALPHA)
            pygame.draw.circle(curse_surf, (150, 50, 200, alpha), (12, 12), 10)
            surface.blit(curse_surf, (int(x_pos - 12), int(self.y + y_offset - 12)))


class SummonEffect(HeroEntryAnimation):
    """Blue portal effect for summoning tokens."""
    def __init__(self, x, y, num_summons=2):
        super().__init__(x, y, duration=1600)
        self.num_summons = num_summons
        self.rings = []
        for i in range(num_summons):
            self.rings.append({
                'x': x + (i - num_summons/2 + 0.5) * 100,
                'progress': 0
            })
    
    def draw(self, surface):
        progress = self.get_progress()
        
        for ring in self.rings:
            ring['progress'] = progress
            
            # Portal ring
            radius = int(30 + progress * 40)
            alpha = int((1 - progress) * 200)
            
            portal_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(portal_surf, (100, 180, 255, alpha), (radius, radius), radius, width=4)
            pygame.draw.circle(portal_surf, (150, 200, 255, alpha//2), (radius, radius), radius//2)
            surface.blit(portal_surf, (int(ring['x'] - radius), int(self.y - radius)))


class BerserkerRageEffect(HeroEntryAnimation):
    """Red rage effect when berserker activates."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=800)
    
    def draw(self, surface):
        progress = self.get_progress()
        
        # Expanding red aura
        radius = int(40 + progress * 60)
        alpha = int((1 - progress) * 200)
        
        # Multiple rage pulses
        for i in range(3):
            r = radius - i * 15
            if r > 0:
                rage_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                a = alpha // (i + 1)
                pygame.draw.circle(rage_surf, (255, 100, 80, a), (r, r), r, width=5)
                surface.blit(rage_surf, (int(self.x - r), int(self.y - r)))


class MardroemeEffect(HeroEntryAnimation):
    """Gold transformation effect for Genetic Enhancement ability."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=2000)
        self.particles = []
        for _ in range(50):
            angle = random.uniform(0, 360)
            dist = random.uniform(10, 60)
            self.particles.append({
                'angle': angle,
                'dist': dist,
                'size': random.randint(2, 5)
            })
    
    def update(self, dt):
        super().update(dt)
        for p in self.particles:
            p['angle'] += 0.5 * (dt / 16.0)
        return not self.finished
    
    def draw(self, surface):
        progress = self.get_progress()
        
        # Gold swirling particles
        alpha = int(math.sin(progress * math.pi) * 255)
        
        for p in self.particles:
            rad = math.radians(p['angle'])
            px = self.x + math.cos(rad) * p['dist'] * (1 + progress)
            py = self.y + math.sin(rad) * p['dist'] * (1 + progress)
            
            color = (255, 215, 0, alpha)
            surf = pygame.Surface((p['size']*2, p['size']*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (p['size'], p['size']), p['size'])
            surface.blit(surf, (int(px - p['size']), int(py - p['size'])))


class StargateOpeningEffect:
    """
    High-fidelity Stargate Kawoosh opening sequence.
    Duration: Fixed to 16,000ms to match audio.
    
    Layered rendering order:
    1. Deep space void + starfield (depth)
    2. Gate structure (metallic rings + symbols)
    3. Event horizon (puddle inside inner ring)
    4. Kawoosh surge (additive particles expanding outward)
    """
    def __init__(self, screen_width, screen_height):
        self.duration = 16000  # STRICTLY MAINTAINED FOR AUDIO SYNC
        self.elapsed = 0
        self.finished = False
        self.show_stabilized_text = False  # Narrator trigger at 13.5s
        
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        # Scale gate based on screen height (responsive)
        self.radius = min(350, int(screen_height * 0.35))
        
        # --- Animation State ---
        self.inner_ring_angle = 0
        self.inner_ring_radius = int(self.radius * 0.85)
        
        # --- Color Palette (Synced with UI) ---
        # Asgard Blue for UI matching
        self.ASGARD_BLUE = (50, 150, 255)
        # Ancient Amber for chevrons
        self.ANCIENT_AMBER = (255, 191, 0)
        # Active chevron color (White-Yellow)
        self.CHEVRON_ACTIVE = (255, 255, 220)
        
        # --- Chevrons (The "Buttons") ---
        # We simulate 9 chevrons with position, active state, and glow intensity
        self.chevrons = []
        for i in range(9):
            angle = (i * (360 / 9)) - 90  # Start at top
            rad = math.radians(angle)
            cx = self.center_x + math.cos(rad) * self.radius
            cy = self.center_y + math.sin(rad) * self.radius
            self.chevrons.append({
                'pos': (cx, cy),
                'angle': angle,
                'active': False,
                'glow': 0.0,  # Used for the "pop" effect when locking
            })
            
        # Timing for chevron locking (milliseconds) - approximated for dramatic effect
        # Matches typical SG-1 opening tempo
        self.lock_times = [
            2000, 3800, 5600, 7200, 8800, 10500, 12000, 13500, 14500
        ]
        
        # --- Particle System for Kawoosh ---
        self.particles = [] 
        
        # --- Background Starfield (Layer 1: The Void) ---
        self.stars = []
        for _ in range(200):
            x = random.randint(0, screen_width)
            y = random.randint(0, screen_height)
            size = random.uniform(0.5, 2)
            brightness = random.randint(100, 255)
            self.stars.append({'x': x, 'y': y, 'size': size, 'b': brightness})
            
    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            self.elapsed = self.duration
            return

        progress = self.elapsed / self.duration
        
        # 1. Rotate Inner Ring
        # Spin fast during dialing, slows down as it locks
        spin_speed = 3.0 if self.elapsed < 12000 else 0.5
        self.inner_ring_angle += spin_speed
        
        # 2. Activate Chevrons (The "Button" Logic)
        for i, time in enumerate(self.lock_times):
            if self.elapsed >= time and not self.chevrons[i]['active']:
                self.chevrons[i]['active'] = True
                self.chevrons[i]['glow'] = 1.0 # Max glow pop on activation
        
        # Decay chevron glow slowly
        for chev in self.chevrons:
            if chev['active']:
                chev['glow'] *= 0.94
        
        # Narrator trigger: "Wormhole Established" at 13.5s
        if self.elapsed >= 13500 and not self.show_stabilized_text:
            self.show_stabilized_text = True
                
        # 3. Handle Horizon & Kawoosh Logic
        
        # Stage A: The Puddle Forms (11s - 12s)
        if 11000 <= self.elapsed <= 12500:
            # Spawn slow drifting blue mist
            for _ in range(3):
                angle = random.uniform(0, 6.28)
                r = random.uniform(0, self.radius * 0.8)
                self.particles.append({
                    'type': 'horizon_mist',
                    'x': self.center_x + math.cos(angle) * r,
                    'y': self.center_y + math.sin(angle) * r,
                    'vx': random.uniform(-0.5, 0.5),
                    'vy': random.uniform(-0.5, 0.5),
                    'life': 1.0,
                    'size': random.randint(5, 10)
                })

        # Stage B: THE KAWOOSH (12.5s - 13.5s) - The massive energy burst
        if 12500 <= self.elapsed <= 13500:
            # Spawn particles representing the 3D wave coming out
            for _ in range(15): # Heavy density per frame
                angle = random.uniform(0, 6.28)
                # Z-simulation: faster particles are "larger/brighter"
                z = random.uniform(0.2, 1.0) 
                speed = (25 * z) * (self.center_x / 960) # Responsive speed
                
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                
                self.particles.append({
                    'type': 'kawoosh',
                    'x': self.center_x,
                    'y': self.center_y,
                    'vx': vx,
                    'vy': vy,
                    'life': 1.0,
                    'decay': random.uniform(0.08, 0.20),
                    'size': random.randint(8, 30) * z,
                })

        # Stage C: Stabilization (After 13.5s)
        # Gentle ripples handled in draw

        # Update Particles
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= p.get('decay', 0.02)
            
            # Remove dead or off-screen
            if p['life'] <= 0 or \
               p['x'] < 0 or p['x'] > self.center_x * 2 or \
               p['y'] < 0 or p['y'] > self.center_y * 2:
                self.particles.remove(p)

    def draw(self, surface):
        """
        Layered rendering order:
        LAYER 1: Deep space void + starfield (background depth)
        LAYER 2: Gate structure (metallic rings + symbols)
        LAYER 3: Event horizon (puddle inside inner ring)
        LAYER 4: Kawoosh surge (additive particles expanding outward)
        """
        
        # === LAYER 1: The Void + Starfield ===
        surface.fill((0, 0, 5))  # Deep space black
        for star in self.stars:
            color = (star['b'], star['b'], star['b'])
            pygame.draw.circle(surface, color, (star['x'], star['y']), int(star['size']))

        # Create effect surface for layered composition
        effect_surf = pygame.Surface((self.center_x * 2, self.center_y * 2), pygame.SRCALPHA)
        
        # === LAYER 2: Gate Structure (Static/Rotating) ===
        
        # Outer Ring (Metallic with depth shading)
        ring_color = (40, 50, 65)
        pygame.draw.circle(effect_surf, ring_color, (self.center_x, self.center_y), self.radius, width=12)
        pygame.draw.circle(effect_surf, (30, 40, 55), (self.center_x, self.center_y), self.radius + 6, width=2)
        
        # Inner Rotating Ring (Symbol-etched)
        num_symbols = 39
        for i in range(num_symbols):
            theta = math.radians(self.inner_ring_angle + (i * (360/num_symbols)))
            sx = self.center_x + math.cos(theta) * self.inner_ring_radius
            sy = self.center_y + math.sin(theta) * self.inner_ring_radius
            # Ancient glyphs in UI-matching color
            glyph_color = (80, 90, 100)
            pygame.draw.circle(effect_surf, glyph_color, (int(sx), int(sy)), 4)

        # Chevrons (UI-synced colors)
        for chev in self.chevrons:
            cx, cy = chev['pos']
            base_color = (160, 80, 30)  # Inactive Dark Orange
            
            if chev['active']:
                # Dynamic Glow Halo (Ancient Amber aura)
                if chev['glow'] > 0.1:
                    glow_alpha = int(chev['glow'] * 200)
                    halo_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
                    # Radial gradient with Ancient Amber tones
                    pygame.draw.circle(halo_surf, (*self.ANCIENT_AMBER, glow_alpha), (20, 20), 16)
                    pygame.draw.circle(halo_surf, (255, 150, 50, glow_alpha), (20, 20), 12)
                    effect_surf.blit(halo_surf, (int(cx - 20), int(cy - 20)))
                
                # Active Chevron Shape (Triangle) - UI-matching White-Yellow
                pygame.draw.polygon(effect_surf, self.CHEVRON_ACTIVE, [
                    (int(cx), int(cy) - 10), 
                    (int(cx) - 8, int(cy) + 6), 
                    (int(cx) + 8, int(cy) + 6)
                ])
                # Center LED (Bright white core)
                pygame.draw.circle(effect_surf, (255, 255, 255), (int(cx), int(cy)), 3)
            else:
                # Inactive Chevron Shape (Embedded in stone)
                pygame.draw.polygon(effect_surf, base_color, [
                    (int(cx), int(cy) - 8), 
                    (int(cx) - 6, int(cy) + 4), 
                    (int(cx) + 6, int(cy) + 4)
                ])

        # === LAYER 3: Event Horizon (Inside inner ring) ===
        if self.elapsed > 11000:
            # Draw stabilized pool first (behind particles)
            if self.elapsed > 13500:
                pool_radius = self.inner_ring_radius * 0.92
                # Animated Ripple (Sine wave distortion)
                ripple_offset = math.sin(pygame.time.get_ticks() / 150) * 5
                
                # Deep blue pool with Asgard Blue tint
                pygame.draw.circle(effect_surf, (10, 60, 140), 
                                 (self.center_x, self.center_y), 
                                 int(pool_radius + ripple_offset))
                
                # Lighter "water" edge (Asgard Blue highlight)
                pygame.draw.circle(effect_surf, self.ASGARD_BLUE, 
                                 (self.center_x, self.center_y), 
                                 int(pool_radius - 12 + ripple_offset))
        
        # === LAYER 4: Kawoosh Surge (Additive particles expanding AROUND gate) ===
        if self.elapsed > 11000:
            # Create dedicated glow surface for additive blending
            glow_surf = pygame.Surface((self.center_x * 2, self.center_y * 2), pygame.SRCALPHA)
            
            for p in self.particles:
                alpha = int(p['life'] * 255)
                
                # KAWOOSH: Fast, White/Blue core with Asgard Blue halo
                if p['type'] == 'kawoosh':
                    # Outer Asgard Blue Halo (expanding around gate)
                    size = p['size'] * 2.5
                    color = (*self.ASGARD_BLUE, alpha // 2)
                    pygame.draw.circle(glow_surf, color, (int(p['x']), int(p['y'])), int(size))
                    
                    # Inner White/Blue Core (The energy burst)
                    size = p['size']
                    color = (200, 240, 255, alpha)
                    pygame.draw.circle(glow_surf, color, (int(p['x']), int(p['y'])), int(size))
                
                # HORIZON MIST: Slow, Deep Blue fog (inside ring)
                elif p['type'] == 'horizon_mist':
                    size = p['size']
                    color = (*self.ASGARD_BLUE, alpha)
                    pygame.draw.circle(glow_surf, color, (int(p['x']), int(p['y'])), int(size))

            # Apply Additive Blending for volumetric glow effect
            effect_surf.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        # Composite all layers onto main screen
        surface.blit(effect_surf, (0, 0))
        
        # Narrator text: "WORMHOLE ESTABLISHED" (appears at 13.5s)
        if self.show_stabilized_text:
            # Fade in over 0.5s
            fade_progress = min(1.0, (self.elapsed - 13500) / 500)
            text_alpha = int(fade_progress * 255)
            
            font = pygame.font.Font(None, 72)
            text = font.render("WORMHOLE ESTABLISHED", True, self.ASGARD_BLUE)
            text.set_alpha(text_alpha)
            text_rect = text.get_rect(center=(self.center_x, self.center_y + self.radius + 80))
            
            # Shadow for depth
            shadow = font.render("WORMHOLE ESTABLISHED", True, (0, 0, 0))
            shadow.set_alpha(text_alpha // 2)
            surface.blit(shadow, (text_rect.x + 3, text_rect.y + 3))
            surface.blit(text, text_rect)

    def get_gpu_params(self):
        """Return GPU parameters for event horizon and kawoosh effects."""
        if self.finished:
            return None
        progress = self.elapsed / self.duration
        params = {
            'type': 'stargate',
            'center': (self.center_x, self.center_y),
            'radius': self.radius,
        }
        # Event horizon phase (after 11s puddle formation)
        if self.elapsed > 11000:
            horizon_progress = min(1.0, (self.elapsed - 11000) / 1500)
            params['event_horizon'] = {
                'intensity': horizon_progress,
                'gate_radius': self.inner_ring_radius,
            }
        # Kawoosh phase (12.5s - 13.5s)
        if 12500 <= self.elapsed <= 13500:
            kawoosh_progress = (self.elapsed - 12500) / 1000.0
            params['kawoosh'] = {
                'progress': kawoosh_progress,
                'strength': 1.0 - kawoosh_progress,
            }
        return params


class IrisClosingEffect(HeroEntryAnimation):
    """Stargate Iris closing animation - metal segments closing from edges."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=1500)
        self.num_segments = 12
        self.max_radius = 250
        self.segments = []
        
        # Create iris blade segments
        for i in range(self.num_segments):
            angle = i * (360 / self.num_segments)
            self.segments.append({
                'angle': angle,
                'start_radius': self.max_radius,
                'current_radius': self.max_radius,
                'color': (120, 120, 140)  # Metal grey
            })
    
    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()
        
        # Ease-in-out closing
        eased_progress = progress * progress * (3 - 2 * progress)
        
        # Close segments from outer to center
        for segment in self.segments:
            segment['current_radius'] = self.max_radius * (1 - eased_progress)
        
        return not self.finished
    
    def draw(self, surface):
        progress = self.get_progress()
        
        # Draw circular outer ring (iris housing)
        housing_alpha = int(200 * (1 - progress * 0.5))
        housing_surf = pygame.Surface((self.max_radius * 2 + 20, self.max_radius * 2 + 20), pygame.SRCALPHA)
        pygame.draw.circle(housing_surf, (80, 80, 100, housing_alpha), 
                          (self.max_radius + 10, self.max_radius + 10), self.max_radius + 10, width=8)
        surface.blit(housing_surf, (int(self.x - self.max_radius - 10), int(self.y - self.max_radius - 10)))
        
        # Draw iris blade segments
        for i, segment in enumerate(self.segments):
            if segment['current_radius'] > 5:
                angle_rad = math.radians(segment['angle'])
                
                # Calculate blade shape (trapezoid pointing to center)
                blade_width = 30
                blade_points = []
                
                # Outer edge points
                outer_angle1 = angle_rad - math.radians(blade_width / 2)
                outer_angle2 = angle_rad + math.radians(blade_width / 2)
                
                outer_x1 = self.x + math.cos(outer_angle1) * segment['current_radius']
                outer_y1 = self.y + math.sin(outer_angle1) * segment['current_radius']
                outer_x2 = self.x + math.cos(outer_angle2) * segment['current_radius']
                outer_y2 = self.y + math.sin(outer_angle2) * segment['current_radius']
                
                # Inner edge points (narrower, towards center)
                inner_radius = max(5, segment['current_radius'] * 0.3)
                inner_angle1 = angle_rad - math.radians(blade_width / 4)
                inner_angle2 = angle_rad + math.radians(blade_width / 4)
                
                inner_x1 = self.x + math.cos(inner_angle1) * inner_radius
                inner_y1 = self.y + math.sin(inner_angle1) * inner_radius
                inner_x2 = self.x + math.cos(inner_angle2) * inner_radius
                inner_y2 = self.y + math.sin(inner_angle2) * inner_radius
                
                blade_points = [
                    (outer_x1, outer_y1),
                    (outer_x2, outer_y2),
                    (inner_x2, inner_y2),
                    (inner_x1, inner_y1)
                ]
                
                # Draw blade with gradient effect
                blade_surf = pygame.Surface((self.max_radius * 2, self.max_radius * 2), pygame.SRCALPHA)
                
                # Main blade
                pygame.draw.polygon(blade_surf, segment['color'], 
                                  [(p[0] - self.x + self.max_radius, p[1] - self.y + self.max_radius) 
                                   for p in blade_points])
                
                # Metallic highlight
                highlight_color = (160, 160, 180)
                pygame.draw.polygon(blade_surf, highlight_color, 
                                  [(p[0] - self.x + self.max_radius, p[1] - self.y + self.max_radius) 
                                   for p in blade_points], width=2)
                
                surface.blit(blade_surf, (int(self.x - self.max_radius), int(self.y - self.max_radius)))
        
        # Draw center locking mechanism when nearly closed
        if progress > 0.7:
            center_alpha = int((progress - 0.7) / 0.3 * 255)
            center_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(center_surf, (100, 100, 120, center_alpha), (20, 20), 18)
            pygame.draw.circle(center_surf, (140, 140, 160, center_alpha), (20, 20), 15)
            pygame.draw.circle(center_surf, (80, 80, 100, center_alpha), (20, 20), 10)
            surface.blit(center_surf, (int(self.x - 20), int(self.y - 20)))
        
        # Draw "IRIS CLOSED" text when fully closed
        if progress > 0.95:
            text_alpha = int((progress - 0.95) / 0.05 * 255)
            font = pygame.font.Font(None, 48)
            text = font.render("IRIS CLOSED", True, (255, 0, 0, text_alpha))
            text_rect = text.get_rect(center=(self.x, self.y + self.max_radius + 50))
            
            # Add text with shadow
            shadow = font.render("IRIS CLOSED", True, (0, 0, 0, text_alpha // 2))
            surface.blit(shadow, (text_rect.x + 2, text_rect.y + 2))
            surface.blit(text, text_rect)


class ClearWeatherBlackHole(HeroEntryAnimation):
    """Dramatic black hole vortex for Wormhole Stabilization (Clear Weather)."""
    def __init__(self, x, y):
        super().__init__(x, y, duration=2800)
        self.particles = []
        self.max_radius = 400
        
        # Create spiral of particles expanding from center
        for i in range(80):
            angle = i * 4.5  # Tighter spiral
            distance = i * 4
            self.particles.append({
                'angle': angle,
                'distance': distance,
                'initial_distance': distance,
                'size': random.randint(4, 9),
                'color': (50 + i, 150 + random.randint(-30, 30), 255),
                'alpha': 255,
                'rotation_speed': random.uniform(0.5, 1.5)
            })
    
    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()
        
        # Rotate and move particles
        for p in self.particles:
            p['angle'] += p['rotation_speed'] * (dt / 16.0)
            
            # First 30%: expand outward
            if progress < 0.3:
                expand_factor = progress / 0.3
                p['distance'] = p['initial_distance'] + (self.max_radius - p['initial_distance']) * expand_factor
            # Remaining 70%: spiral inward (black hole effect)
            else:
                p['distance'] = max(0, p['distance'] - 3.0 * (dt / 16.0))
            
            # Fade when getting close to center
            if p['distance'] < 50:
                p['alpha'] = max(0, p['alpha'] - 8 * (dt / 16.0))
        
        return not self.finished


def create_black_hole_defeat_transition(screen, screen_width, screen_height, duration=4000):
    """
    Full-screen black hole transition for when player is about to lose (0-2 deficit).
    Shows a menacing black hole consuming the screen with ominous text.
    """
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()
    center_x = screen_width // 2
    center_y = screen_height // 2
    
    # Create debris particles being sucked into black hole
    debris = []
    for _ in range(150):
        angle = random.uniform(0, 360)
        distance = random.uniform(300, max(screen_width, screen_height))
        debris.append({
            'angle': angle,
            'distance': distance,
            'size': random.randint(2, 8),
            'color': random.choice([
                (255, 100, 50),   # Orange/fire
                (200, 80, 40),    # Dark orange
                (150, 60, 30),    # Brown
                (100, 100, 120),  # Grey debris
                (80, 80, 100),    # Dark grey
            ]),
            'rotation_speed': random.uniform(1.5, 4.0),
            'pull_speed': random.uniform(0.5, 2.0),
            'alpha': 255
        })
    
    # Accretion disk particles (glowing ring around black hole)
    accretion = []
    for i in range(60):
        angle = i * 6
        accretion.append({
            'angle': angle,
            'base_distance': random.uniform(80, 150),
            'size': random.randint(3, 7),
            'color': (255, 150 + random.randint(-50, 50), 50),
            'speed': random.uniform(3, 6)
        })
    
    # Stars being stretched (spaghettification effect)
    stretched_stars = []
    for _ in range(30):
        stretched_stars.append({
            'x': random.randint(0, screen_width),
            'y': random.randint(0, screen_height),
            'length': random.randint(20, 100),
            'alpha': random.randint(100, 200)
        })
    
    while pygame.time.get_ticks() - start_time < duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    return
        
        elapsed = pygame.time.get_ticks() - start_time
        progress = elapsed / duration
        dt = clock.tick(60)
        
        # Fill with deep space black
        screen.fill((0, 0, 5))
        
        # Draw stretched stars (spaghettification toward center)
        for star in stretched_stars:
            dx = center_x - star['x']
            dy = center_y - star['y']
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                # Calculate stretch direction toward black hole
                stretch_x = dx / dist
                stretch_y = dy / dist
                
                # Stretch increases as we get closer to black hole and as time progresses
                stretch_factor = star['length'] * (1 + progress * 3) * (1 - min(dist / 800, 1))
                
                end_x = star['x'] + stretch_x * stretch_factor
                end_y = star['y'] + stretch_y * stretch_factor
                
                alpha = int(star['alpha'] * (1 - progress * 0.5))
                if alpha > 0:
                    line_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                    pygame.draw.line(line_surf, (255, 255, 255, alpha), 
                                   (int(star['x']), int(star['y'])), 
                                   (int(end_x), int(end_y)), 1)
                    screen.blit(line_surf, (0, 0))
        
        # Update and draw debris being pulled in
        for d in debris:
            # Spiral inward
            d['angle'] += d['rotation_speed'] * (dt / 16.0)
            d['distance'] -= d['pull_speed'] * (1 + progress * 3) * (dt / 16.0)
            
            # Fade as it gets close
            if d['distance'] < 100:
                d['alpha'] = max(0, d['alpha'] - 5 * (dt / 16.0))
            
            if d['distance'] > 0 and d['alpha'] > 0:
                rad = math.radians(d['angle'])
                dx = center_x + math.cos(rad) * d['distance']
                dy = center_y + math.sin(rad) * d['distance']
                
                # Draw debris with trail
                trail_length = min(30, d['distance'] * 0.1)
                trail_x = dx - math.cos(rad) * trail_length
                trail_y = dy - math.sin(rad) * trail_length
                
                debris_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                pygame.draw.line(debris_surf, (*d['color'], int(d['alpha'] * 0.5)), 
                               (int(trail_x), int(trail_y)), (int(dx), int(dy)), max(1, d['size'] // 2))
                pygame.draw.circle(debris_surf, (*d['color'], int(d['alpha'])), 
                                 (int(dx), int(dy)), d['size'])
                screen.blit(debris_surf, (0, 0))
        
        # Draw accretion disk (glowing ring)
        accretion_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        for a in accretion:
            a['angle'] += a['speed'] * (dt / 16.0)
            rad = math.radians(a['angle'])
            
            # Elliptical orbit for 3D effect
            disk_x = center_x + math.cos(rad) * a['base_distance'] * 1.5
            disk_y = center_y + math.sin(rad) * a['base_distance'] * 0.4
            
            # Glow intensity based on position (brighter in front)
            glow = 150 + int(50 * math.sin(rad))
            color = (255, glow, 50, 200)
            
            pygame.draw.circle(accretion_surf, color, (int(disk_x), int(disk_y)), a['size'])
        screen.blit(accretion_surf, (0, 0))
        
        # Draw black hole center (grows over time)
        hole_radius = int(30 + progress * 70)
        
        # Event horizon glow
        for r in range(hole_radius + 40, hole_radius, -5):
            glow_alpha = int(100 * (1 - (r - hole_radius) / 40))
            glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (100, 50, 150, glow_alpha), (r, r), r)
            screen.blit(glow_surf, (center_x - r, center_y - r))
        
        # Pure black center
        pygame.draw.circle(screen, (0, 0, 0), (center_x, center_y), hole_radius)
        
        # Gravitational lensing ring (bright edge)
        pygame.draw.circle(screen, (200, 100, 255), (center_x, center_y), hole_radius + 3, 2)
        pygame.draw.circle(screen, (255, 200, 100), (center_x, center_y), hole_radius + 1, 1)
        
        # Ominous text
        text_alpha = int(255 * min(1.0, progress * 2))
        
        title_font = pygame.font.SysFont("Arial", 64, bold=True)
        sub_font = pygame.font.SysFont("Arial", 32)
        
        # Main text
        title_text = "GRAVITATIONAL COLLAPSE"
        title_surf = title_font.render(title_text, True, (255, 50, 50))
        title_surf.set_alpha(text_alpha)
        title_rect = title_surf.get_rect(center=(center_x, 80))
        screen.blit(title_surf, title_rect)
        
        # Sub text (appears later)
        if progress > 0.3:
            sub_alpha = int(255 * min(1.0, (progress - 0.3) * 2))
            sub_text = "Your forces are being consumed..."
            sub_surf = sub_font.render(sub_text, True, (200, 150, 150))
            sub_surf.set_alpha(sub_alpha)
            sub_rect = sub_surf.get_rect(center=(center_x, screen_height - 100))
            screen.blit(sub_surf, sub_rect)
        
        # Screen darkening at the end
        if progress > 0.8:
            dark_alpha = int(255 * (progress - 0.8) / 0.2)
            dark_surf = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            dark_surf.fill((0, 0, 0, dark_alpha))
            screen.blit(dark_surf, (0, 0))
        
        display_manager.gpu_flip()
    
    # Final flash to black
    screen.fill((0, 0, 0))
    display_manager.gpu_flip()


class GoauldSymbioteAnimation(Animation):
    """Goa'uld larva symbiote jumping animation - seeks a host on opponent's side."""
    def __init__(self, start_x, start_y, target_x, target_y, duration=1400):
        super().__init__(duration)
        self.start_x = start_x
        self.start_y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.current_x = start_x
        self.current_y = start_y
        
        # Symbiote body segments (snake-like) - longer body
        self.segments = []
        self.num_segments = 18  # More segments for longer body
        for i in range(self.num_segments):
            self.segments.append({
                'x': start_x,
                'y': start_y,
                'size': max(3, 10 - i * 0.35),  # Larger head, tapers toward tail
                'delay': i * 0.025  # Tighter trail delay
            })
        
        # Slime trail particles
        self.slime_trail = []
        
        # Animation phases: coil (0-20%), leap (20-70%), land (70-100%)
        self.phase = "coil"
        self.coil_offset = 0
        self.wiggle_phase = 0
        
        # Symbiote colors (sickly yellowish-tan Goa'uld larva)
        self.body_color = (180, 160, 100)  # Pale tan
        self.highlight_color = (220, 200, 140)  # Lighter highlights
        self.eye_color = (255, 80, 80)  # Glowing red eyes
    
    def update(self, dt):
        active = super().update(dt)
        progress = self.get_progress()
        self.wiggle_phase += 0.25 * (dt / 16.0)
        
        # Phase transitions
        if progress < 0.2:
            self.phase = "coil"
        elif progress < 0.7:
            self.phase = "leap"
        else:
            self.phase = "land"
        
        # Calculate head position based on phase
        if self.phase == "coil":
            # Coiling up, preparing to jump
            coil_progress = progress / 0.2
            self.coil_offset = math.sin(coil_progress * math.pi * 3) * 15
            self.current_x = self.start_x + self.coil_offset
            self.current_y = self.start_y - coil_progress * 20  # Rises slightly
            
        elif self.phase == "leap":
            # Leaping through the air in an arc
            leap_progress = (progress - 0.2) / 0.5
            eased = self.ease_out_cubic(leap_progress)
            
            # Parabolic arc (high jump)
            arc_height = -180 * math.sin(leap_progress * math.pi)
            
            self.current_x = self.start_x + (self.target_x - self.start_x) * eased
            self.current_y = self.start_y + (self.target_y - self.start_y) * eased + arc_height
            
            # Add wiggle during flight
            wiggle = math.sin(self.wiggle_phase * 8) * 8
            self.current_x += wiggle
            
        else:  # land
            # Landing and wrapping around target
            land_progress = (progress - 0.7) / 0.3
            self.current_x = self.target_x + math.sin(land_progress * math.pi * 2) * 10 * (1 - land_progress)
            self.current_y = self.target_y + math.cos(land_progress * math.pi) * 5
        
        # Update body segments (follow the head with delay)
        for i, seg in enumerate(self.segments):
            delay = seg['delay']
            delayed_progress = max(0, progress - delay)
            
            if delayed_progress < 0.2:
                # Still at start
                seg['x'] = self.start_x + math.sin(self.wiggle_phase + i * 0.5) * 5
                seg['y'] = self.start_y + i * 2
            elif delayed_progress < 0.7:
                # Following head through arc
                t = (delayed_progress - 0.2) / 0.5
                eased_t = self.ease_out_cubic(t)
                arc = -180 * math.sin(t * math.pi)
                seg['x'] = self.start_x + (self.target_x - self.start_x) * eased_t
                seg['y'] = self.start_y + (self.target_y - self.start_y) * eased_t + arc
                # Wiggle
                seg['x'] += math.sin(self.wiggle_phase * 8 + i * 0.8) * (8 - i * 0.5)
            else:
                # At target
                wrap_angle = (self.wiggle_phase * 2 + i * 0.6) * (1 - (delayed_progress - 0.7) / 0.3)
                radius = 15 + i * 2
                seg['x'] = self.target_x + math.cos(wrap_angle) * radius * (1 - (delayed_progress - 0.7) / 0.3 * 0.5)
                seg['y'] = self.target_y + math.sin(wrap_angle) * radius * 0.5
        
        # Add slime trail particles during leap
        if self.phase == "leap" and random.random() < 0.4:
            self.slime_trail.append({
                'x': self.current_x + random.uniform(-5, 5),
                'y': self.current_y + random.uniform(-3, 3),
                'size': random.randint(2, 5),
                'alpha': 180,
                'life': 1.0
            })
        
        # Limit slime trail
        if len(self.slime_trail) > 40:
            self.slime_trail = self.slime_trail[-40:]
        
        # Fade slime trail
        for slime in self.slime_trail[:]:
            slime['life'] -= dt / 800.0
            slime['alpha'] = int(180 * slime['life'])
            if slime['life'] <= 0:
                self.slime_trail.remove(slime)
        
        return active
    
    def ease_out_cubic(self, t):
        return 1 - pow(1 - t, 3)
    
    def draw(self, surface):
        if self.finished:
            return
        
        progress = self.get_progress()
        
        # Draw slime trail first (behind symbiote)
        for slime in self.slime_trail:
            if slime['alpha'] > 0:
                slime_surf = pygame.Surface((slime['size'] * 2, slime['size'] * 2), pygame.SRCALPHA)
                slime_color = (120, 140, 80, slime['alpha'])  # Greenish slime
                pygame.draw.circle(slime_surf, slime_color, (slime['size'], slime['size']), slime['size'])
                surface.blit(slime_surf, (int(slime['x'] - slime['size']), int(slime['y'] - slime['size'])))
        
        # Draw body segments (tail to head)
        for i in range(len(self.segments) - 1, -1, -1):
            seg = self.segments[i]
            size = int(seg['size'])
            
            # Segment surface with glow
            seg_size = size * 3
            seg_surf = pygame.Surface((seg_size, seg_size), pygame.SRCALPHA)
            
            # Outer glow
            glow_alpha = 60 if self.phase == "leap" else 30
            pygame.draw.circle(seg_surf, (*self.body_color, glow_alpha), (seg_size // 2, seg_size // 2), size + 2)
            
            # Main body segment
            pygame.draw.circle(seg_surf, self.body_color, (seg_size // 2, seg_size // 2), size)
            
            # Highlight on top
            highlight_offset = -size // 3
            pygame.draw.circle(seg_surf, self.highlight_color, (seg_size // 2 + highlight_offset, seg_size // 2 + highlight_offset), max(1, size // 2))
            
            surface.blit(seg_surf, (int(seg['x'] - seg_size // 2), int(seg['y'] - seg_size // 2)))
        
        # Draw head (larger, with eyes)
        head_size = 12
        head_surf = pygame.Surface((head_size * 4, head_size * 4), pygame.SRCALPHA)
        center = head_size * 2
        
        # Head glow (menacing)
        if self.phase == "leap":
            pygame.draw.circle(head_surf, (200, 180, 100, 80), (center, center), head_size + 4)
        
        # Head body
        pygame.draw.ellipse(head_surf, self.body_color, (center - head_size, center - head_size // 2, head_size * 2, head_size))
        
        # Eyes (glowing red, menacing)
        eye_offset_x = 4
        eye_offset_y = -2
        eye_size = 3
        
        # Eye glow
        pygame.draw.circle(head_surf, (255, 100, 100, 150), (center - eye_offset_x, center + eye_offset_y), eye_size + 2)
        pygame.draw.circle(head_surf, (255, 100, 100, 150), (center + eye_offset_x, center + eye_offset_y), eye_size + 2)
        
        # Eye cores
        pygame.draw.circle(head_surf, self.eye_color, (center - eye_offset_x, center + eye_offset_y), eye_size)
        pygame.draw.circle(head_surf, self.eye_color, (center + eye_offset_x, center + eye_offset_y), eye_size)
        
        # Eye pupils (tiny black dots)
        pygame.draw.circle(head_surf, (0, 0, 0), (center - eye_offset_x, center + eye_offset_y), 1)
        pygame.draw.circle(head_surf, (0, 0, 0), (center + eye_offset_x, center + eye_offset_y), 1)
        
        # Mandibles/fangs when attacking
        if self.phase == "leap" or (self.phase == "land" and progress < 0.85):
            fang_color = (220, 200, 160)
            # Left fang
            pygame.draw.line(head_surf, fang_color, (center - 6, center + 4), (center - 8, center + 10), 2)
            # Right fang
            pygame.draw.line(head_surf, fang_color, (center + 6, center + 4), (center + 8, center + 10), 2)
        
        surface.blit(head_surf, (int(self.current_x - center), int(self.current_y - center)))
        
        # Draw "SEEKING HOST" text during leap
        if self.phase == "leap":
            text_alpha = int(200 * math.sin(progress * math.pi))
            if text_alpha > 20:
                font = pygame.font.Font(None, 32)
                text = font.render("SEEKING HOST...", True, (200, 180, 100))
                text.set_alpha(text_alpha)
                text_rect = text.get_rect(center=(self.current_x, self.current_y - 50))
                surface.blit(text, text_rect)
        
        # Draw impact burst when landing
        if self.phase == "land" and progress < 0.8:
            land_progress = (progress - 0.7) / 0.1
            if land_progress < 1.0:
                burst_radius = int(20 + land_progress * 30)
                burst_alpha = int((1 - land_progress) * 150)
                burst_surf = pygame.Surface((burst_radius * 2, burst_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(burst_surf, (200, 180, 100, burst_alpha), (burst_radius, burst_radius), burst_radius, width=3)
                surface.blit(burst_surf, (int(self.target_x - burst_radius), int(self.target_y - burst_radius)))


# === Special Card Effects ===

class ThorsHammerPurgeEffect(Animation):
    """Blue-white vertical purge beam for Thor's Hammer."""
    def __init__(self, x, y, width, height, duration=1100):
        super().__init__(duration=duration)
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def draw(self, surface):
        if self.finished:
            return
        progress = self.get_progress()
        alpha = int(255 * (1 - abs(progress - 0.5) * 2))
        beam_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        core_color = (120, 200, 255, max(60, alpha))
        glow_color = (80, 160, 255, max(30, alpha // 2))

        beam_rect = pygame.Rect(self.x - 6, 0, 12, self.height)
        pygame.draw.rect(beam_surface, core_color, beam_rect)
        pygame.draw.rect(beam_surface, glow_color, beam_rect.inflate(30, 0))

        max_radius = int(180 + 220 * progress)
        for r in range(0, max_radius, 30):
            ring_alpha = max(0, int(150 * (1 - r / max_radius)))
            pygame.draw.circle(
                beam_surface,
                (120, 200, 255, ring_alpha),
                (self.x, self.y),
                r,
                width=3
            )

        surface.blit(beam_surface, (0, 0))


class ZPMSurgeEffect(Animation):
    """Massive ZPM energy discharge with particles, lightning, and screen flash."""
    def __init__(self, x, y, duration=1500):
        super().__init__(duration=duration)
        self.x = x
        self.y = y

        # Burst particles (gold/cyan/white-gold radial)
        self.particles = []
        particle_colors = [
            (255, 200, 60),   # gold
            (100, 240, 255),  # cyan
            (255, 240, 180),  # white-gold
        ]
        for _ in range(min(60, MAX_GENERAL_PARTICLES)):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(3, 10)
            self.particles.append({
                'x': float(x),
                'y': float(y),
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': random.randint(3, 8),
                'life': 1.0,
                'color': random.choice(particle_colors),
            })

        # Lightning arcs (4 arcs with jagged segments)
        self.lightning_arcs = []
        for i in range(4):
            arc_angle = i * 90 + random.uniform(-20, 20)
            arc_length = random.uniform(120, 200)
            self.lightning_arcs.append({
                'segments': self._generate_lightning_segments(x, y, arc_angle, arc_length),
                'life': 1.0,
                'color': random.choice([(100, 240, 255), (200, 230, 255), (255, 220, 100)]),
            })

    def _generate_lightning_segments(self, x, y, angle, length):
        """Generate jagged lightning bolt segments."""
        segments = [pygame.math.Vector2(x, y)]
        current = pygame.math.Vector2(x, y)
        target = pygame.math.Vector2(
            x + math.cos(math.radians(angle)) * length,
            y + math.sin(math.radians(angle)) * length
        )
        num_segments = random.randint(5, 8)
        for i in range(1, num_segments):
            next_point = current.lerp(target, 1.0 / (num_segments - i + 1))
            offset = random.uniform(-15, 15)
            perp_angle = angle + 90
            next_point.x += math.cos(math.radians(perp_angle)) * offset
            next_point.y += math.sin(math.radians(perp_angle)) * offset
            segments.append(next_point)
            current = next_point
        segments.append(target)
        return segments

    def update(self, dt):
        """Update particles and lightning."""
        super().update(dt)
        progress = self.get_progress()
        dt_factor = dt / 16.0

        # Update particles
        for p in self.particles:
            p['x'] += p['vx'] * dt_factor
            p['y'] += p['vy'] * dt_factor
            p['vx'] *= 0.95
            p['vy'] *= 0.95
            p['life'] = max(0, 1.0 - progress * 1.3)

        # Fade lightning
        for arc in self.lightning_arcs:
            arc['life'] = max(0, 1.0 - progress * 2.0)

    def draw(self, surface):
        if self.finished:
            return
        progress = self.get_progress()

        # Screen flash (white overlay during first 120ms, ~8% of 1500ms)
        if progress < 0.08:
            flash_alpha = int(120 * (1 - progress / 0.08))
            flash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, flash_alpha))
            surface.blit(flash_surf, (0, 0))

        # Create a canvas large enough for the effect
        size = 800
        canvas = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (size // 2, size // 2)

        # Ease out
        ease = 1 - pow(1 - progress, 4)

        # Central ZPM Glow (Orange/Gold)
        alpha_core = int(255 * (1 - progress))
        pygame.draw.circle(canvas, (255, 180, 50, alpha_core), center, 40)
        pygame.draw.circle(canvas, (255, 255, 200, alpha_core), center, 20)

        # Expanding Rings (Ancient Blue/Cyan)
        for i in range(3):
            sub_prog = (progress * 1.5 - i * 0.2)
            if 0 < sub_prog < 1:
                r = int(300 * sub_prog)
                a = int(200 * (1 - sub_prog))
                pygame.draw.circle(canvas, (100, 240, 255, a), center, r, width=10)

        # Energy Spikes
        if progress < 0.8:
            for i in range(8):
                angle = i * (360/8) + progress * 90
                rad = math.radians(angle)
                length = 50 + 250 * ease
                end_x = center[0] + math.cos(rad) * length
                end_y = center[1] + math.sin(rad) * length
                pygame.draw.line(canvas, (255, 220, 100, int(180 * (1-progress))), center, (end_x, end_y), 4)

        # Draw lightning arcs
        for arc in self.lightning_arcs:
            if arc['life'] > 0:
                a = int(220 * arc['life'])
                color = (*arc['color'], a)
                segs = arc['segments']
                # Offset segments to canvas-local coords
                for j in range(len(segs) - 1):
                    s = segs[j]
                    e = segs[j + 1]
                    sx = int(s.x - self.x + center[0])
                    sy = int(s.y - self.y + center[1])
                    ex = int(e.x - self.x + center[0])
                    ey = int(e.y - self.y + center[1])
                    # Glow line (wider, dimmer)
                    pygame.draw.line(canvas, (*arc['color'][:3], a // 3), (sx, sy), (ex, ey), 5)
                    # Core line
                    pygame.draw.line(canvas, color, (sx, sy), (ex, ey), 2)

        # Draw particles as glowing circles
        for p in self.particles:
            if p['life'] > 0:
                pa = int(255 * p['life'])
                ps = max(1, int(p['size'] * p['life']))
                px = int(p['x'] - self.x + center[0])
                py = int(p['y'] - self.y + center[1])
                # Glow
                pygame.draw.circle(canvas, (*p['color'], pa // 2), (px, py), ps + 2)
                # Core
                pygame.draw.circle(canvas, (*p['color'], pa), (px, py), ps)

        # Blit to screen centered at self.x, self.y
        surface.blit(canvas, (self.x - size // 2, self.y - size // 2))

    def get_gpu_params(self):
        """Return GPU parameters for ZPM electric arc overlay."""
        if self.finished:
            return None
        progress = self.get_progress()
        intensity = 1.0 - progress
        if intensity <= 0.0:
            return None
        return {
            'type': 'zpm_surge',
            'center': (self.x, self.y),
            'intensity': intensity,
            'surge_radius': 300 * (1 - pow(1 - progress, 4)),
        }


class CommunicationRevealEffect(Animation):
    """Eye sweep revealing opponent hand."""
    def __init__(self, x, y, screen_width, screen_height, duration=1200):
        super().__init__(duration=duration)
        self.x = x
        self.y = y
        self.screen_width = screen_width
        self.screen_height = screen_height

    def draw(self, surface):
        if self.finished:
            return
        progress = self.get_progress()
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        sweep_x = int(self.screen_width * progress)
        sweep_width = 240
        sweep_rect = pygame.Rect(sweep_x - sweep_width // 2, 0, sweep_width, self.screen_height)
        pygame.draw.rect(overlay, (120, 200, 255, 90), sweep_rect)

        eye_radius = 42
        pygame.draw.circle(overlay, (180, 220, 255, 200), (self.x, self.y), eye_radius)
        pygame.draw.circle(overlay, (40, 80, 140, 230), (self.x, self.y), max(12, eye_radius // 2))
        pygame.draw.line(overlay, (200, 240, 255, 200), (self.x - 50, self.y), (self.x + 50, self.y), 3)

        surface.blit(overlay, (0, 0))


class MerlinAntiOriEffect(Animation):
    """Golden-white anti-Ori blast that only hits the opponent."""
    def __init__(self, x, y, screen_width, screen_height, duration=1100):
        super().__init__(duration=duration)
        self.x = x
        self.y = y
        self.screen_width = screen_width
        self.screen_height = screen_height

    def draw(self, surface):
        if self.finished:
            return
        progress = self.get_progress()
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        blast_radius = int(120 + 260 * progress)
        center = (self.x, self.y)
        pygame.draw.circle(overlay, (255, 230, 180, 150), center, blast_radius, width=6)
        pygame.draw.circle(overlay, (255, 255, 200, 120), center, max(10, blast_radius // 3))
        pygame.draw.circle(overlay, (255, 255, 255, 90), center, max(8, blast_radius // 6))

        beam_height = self.screen_height // 2
        beam_rect = pygame.Rect(self.x - 12, 0, 24, beam_height)
        pygame.draw.rect(overlay, (255, 230, 180, 140), beam_rect)
        pygame.draw.rect(overlay, (255, 255, 200, 90), beam_rect.inflate(30, 0))

        surface.blit(overlay, (0, 0))


class DakaraShockwaveEffect(Animation):
    """Massive radial shockwave for Dakara Superweapon."""
    def __init__(self, x, y, screen_width, screen_height, duration=1300):
        super().__init__(duration=duration)
        self.x = x
        self.y = y
        self.screen_width = screen_width
        self.screen_height = screen_height

    def draw(self, surface):
        if self.finished:
            return
        progress = self.get_progress()
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        radius = int(progress * max(self.screen_width, self.screen_height))
        ring_alpha = max(0, int(180 * (1 - progress)))
        pygame.draw.circle(overlay, (255, 140, 80, ring_alpha), (self.x, self.y), radius, width=10)

        core_radius = int(120 + 120 * progress)
        pygame.draw.circle(overlay, (255, 200, 120, ring_alpha), (self.x, self.y), core_radius)

        surface.blit(overlay, (0, 0))
    
    def draw(self, surface):
        progress = self.get_progress()
        
        # Draw black hole center
        if progress > 0.3:
            center_alpha = min(255, int((progress - 0.3) * 365))
            center_radius = int(20 + (progress - 0.3) * 80)
            
            # Outer dark ring
            center_surf = pygame.Surface((center_radius * 2, center_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(center_surf, (0, 0, 0, center_alpha // 2), (center_radius, center_radius), center_radius)
            # Inner black hole
            pygame.draw.circle(center_surf, (10, 10, 30, center_alpha), (center_radius, center_radius), center_radius // 2)
            surface.blit(center_surf, (int(self.x - center_radius), int(self.y - center_radius)))
        
        # Draw spiral particles
        for p in self.particles:
            if p['alpha'] > 0 and p['distance'] > 0:
                rad = math.radians(p['angle'])
                px = self.x + math.cos(rad) * p['distance']
                py = self.y + math.sin(rad) * p['distance']
                
                color = (*p['color'], int(p['alpha']))
                surf = pygame.Surface((p['size']*2, p['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (p['size'], p['size']), p['size'])
                
                # Add glow
                glow_color = (*p['color'][:3], int(p['alpha'] // 2))
                pygame.draw.circle(surf, glow_color, (p['size'], p['size']), p['size'] + 2, width=1)
                
                surface.blit(surf, (int(px - p['size']), int(py - p['size'])))
        
        # Draw "WORMHOLE STABILIZED" text when particles are collapsing
        if progress > 0.5:
            text_alpha = min(255, int((progress - 0.5) * 510))
            font = pygame.font.Font(None, 56)
            text = font.render("WORMHOLE STABILIZED", True, (100, 200, 255, text_alpha))
            text_rect = text.get_rect(center=(self.x, self.y - 200))
            
            # Shadow
            shadow = font.render("WORMHOLE STABILIZED", True, (0, 0, 0, text_alpha // 3))
            surface.blit(shadow, (text_rect.x + 3, text_rect.y + 3))
            surface.blit(text, text_rect)


class QuantumMirrorEffect(Animation):
    """Quantum Mirror portal effect with card shuffle animation.

    Phase 1 (0-0.35): Cards fly from hand to mirror
    Phase 2 (0.35-0.65): Mirror effect with reality distortion
    Phase 3 (0.65-1.0): Cards fly from mirror back to hand
    """
    def __init__(self, x, y, screen_width, screen_height, duration=2200, num_cards=8):
        super().__init__(duration=duration)
        self.x = x
        self.y = y
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.mirror_width = 280
        self.mirror_height = 400

        # Card shuffle animation properties
        self.card_width = 60
        self.card_height = 85
        self.num_cards = max(1, min(num_cards, 25))  # Clamp to reasonable range

        # Hand position (bottom center of screen)
        self.hand_y = screen_height - 120
        self.hand_center_x = screen_width // 2

        # Calculate spacing based on number of cards
        max_spread = min(screen_width * 0.6, self.num_cards * 50)
        card_spacing = max_spread / max(1, self.num_cards - 1) if self.num_cards > 1 else 0

        # Generate random card start positions (spread across hand area)
        self.card_offsets = []
        for i in range(self.num_cards):
            # Center the cards and spread them out
            offset_x = (i - (self.num_cards - 1) / 2) * card_spacing + random.randint(-10, 10)
            delay = random.uniform(0, 0.2) * (i / max(1, self.num_cards))  # Staggered timing
            rotation = random.randint(-15, 15)
            self.card_offsets.append((offset_x, delay, rotation))

    def _draw_card_silhouette(self, surface, x, y, alpha, rotation=0, scale=1.0):
        """Draw a glowing card silhouette."""
        w = int(self.card_width * scale)
        h = int(self.card_height * scale)

        # Create card surface
        card_surf = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
        card_rect = pygame.Rect(10, 10, w, h)

        # Outer glow
        glow_color = (180, 200, 255, alpha // 3)
        pygame.draw.rect(card_surf, glow_color, card_rect.inflate(8, 8), border_radius=6)

        # Card body
        body_color = (220, 230, 255, alpha)
        pygame.draw.rect(card_surf, body_color, card_rect, border_radius=4)

        # Card border
        border_color = (255, 255, 255, min(255, alpha + 30))
        pygame.draw.rect(card_surf, border_color, card_rect, width=2, border_radius=4)

        # Inner detail lines (card face suggestion)
        if alpha > 100:
            line_alpha = alpha // 2
            pygame.draw.line(card_surf, (200, 210, 230, line_alpha),
                           (15, 20), (w + 5, 20), 1)
            pygame.draw.line(card_surf, (200, 210, 230, line_alpha),
                           (15, h - 5), (w + 5, h - 5), 1)

        # Rotate if needed
        if rotation != 0:
            card_surf = pygame.transform.rotate(card_surf, rotation)

        # Center the card at position
        rect = card_surf.get_rect(center=(x, y))
        surface.blit(card_surf, rect)

    def draw(self, surface):
        if self.finished:
            return
        progress = self.get_progress()
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        center_x, center_y = self.x, self.y

        # === PHASE 1: Cards fly from hand to mirror (0 - 0.35) ===
        if progress < 0.35:
            phase_progress = progress / 0.35
            for i, (offset_x, delay, rotation) in enumerate(self.card_offsets):
                # Staggered card animation
                card_progress = max(0, min(1, (phase_progress - delay) / (1 - delay)))
                if card_progress <= 0:
                    continue

                # Ease out cubic
                eased = 1 - pow(1 - card_progress, 3)

                # Start position (hand)
                start_x = self.hand_center_x + offset_x
                start_y = self.hand_y

                # End position (mirror center with slight spread)
                end_x = center_x + (i - self.num_cards // 2) * 15
                end_y = center_y

                # Interpolate position
                card_x = start_x + (end_x - start_x) * eased
                card_y = start_y + (end_y - start_y) * eased

                # Arc motion
                arc = math.sin(card_progress * math.pi) * -80
                card_y += arc

                # Rotation animation
                current_rotation = rotation * (1 - eased) + random.randint(-5, 5) * (1 - card_progress)

                # Alpha (fade in at start, stay visible)
                alpha = int(200 * min(1, card_progress * 3))

                # Scale (slightly smaller as they approach mirror)
                scale = 1.0 - 0.2 * eased

                self._draw_card_silhouette(overlay, int(card_x), int(card_y), alpha, current_rotation, scale)

        # === PHASE 2: Mirror effect (0.2 - 0.8) ===
        if 0.2 < progress < 0.8:
            mirror_progress = (progress - 0.2) / 0.6

            # Mirror rectangle centered at effect position
            mx = self.x - self.mirror_width // 2
            my = self.y - self.mirror_height // 2

            # Outer frame (dark metallic border)
            frame_alpha = int(220 * (1 - mirror_progress * 0.3))
            frame_rect = pygame.Rect(mx - 12, my - 12, self.mirror_width + 24, self.mirror_height + 24)
            pygame.draw.rect(overlay, (60, 65, 75, frame_alpha), frame_rect, border_radius=6)
            pygame.draw.rect(overlay, (100, 110, 130, frame_alpha), frame_rect, width=4, border_radius=6)

            # Inner reflective surface
            mirror_alpha = int(180 * (1 - mirror_progress * 0.4))
            mirror_surf = pygame.Surface((self.mirror_width, self.mirror_height), pygame.SRCALPHA)

            # Gradient bands
            for i in range(self.mirror_height):
                wave = math.sin((i / 30.0) + mirror_progress * 12) * 0.3 + 0.7
                r = int(180 * wave)
                g = int(190 * wave)
                b = int(210 * wave + 30)
                pygame.draw.line(mirror_surf, (r, g, b, mirror_alpha), (0, i), (self.mirror_width, i))

            # Shimmer waves
            for i in range(5):
                wave_y = int((mirror_progress * 3 + i * 0.2) % 1.0 * self.mirror_height)
                wave_alpha = int(100 * (1 - abs(wave_y / self.mirror_height - 0.5) * 2))
                if wave_alpha > 0:
                    pygame.draw.line(mirror_surf, (255, 255, 255, wave_alpha),
                                   (0, wave_y), (self.mirror_width, wave_y), 3)

            overlay.blit(mirror_surf, (mx, my))

            # Ripple effect
            for i in range(4):
                ripple_progress = (mirror_progress * 2 + i * 0.25) % 1.0
                ripple_size = int(ripple_progress * 250)
                ripple_alpha = max(0, int(120 * (1 - ripple_progress)))
                if ripple_size > 10:
                    ripple_rect = pygame.Rect(center_x - ripple_size // 2,
                                             center_y - int(ripple_size * 0.7),
                                             ripple_size, int(ripple_size * 1.4))
                    pygame.draw.ellipse(overlay, (200, 210, 230, ripple_alpha), ripple_rect, width=2)

            # Central glow
            glow_alpha = int(150 * (1 - mirror_progress * 0.5))
            glow_radius = int(30 + 20 * math.sin(mirror_progress * 15))
            pygame.draw.circle(overlay, (230, 240, 255, glow_alpha), (center_x, center_y), glow_radius)

            # Flash at midpoint
            if 0.4 < mirror_progress < 0.6:
                flash_intensity = 1 - abs(mirror_progress - 0.5) * 5
                flash_alpha = int(200 * flash_intensity)
                flash_surf = pygame.Surface((self.mirror_width + 40, self.mirror_height + 40), pygame.SRCALPHA)
                flash_surf.fill((255, 255, 255, flash_alpha))
                overlay.blit(flash_surf, (mx - 20, my - 20))

        # === PHASE 3: Cards fly from mirror back to hand (0.65 - 1.0) ===
        if progress > 0.65:
            phase_progress = (progress - 0.65) / 0.35
            for i, (offset_x, delay, rotation) in enumerate(self.card_offsets):
                # Staggered card animation (reverse order for visual interest)
                adjusted_delay = delay * 0.5
                card_progress = max(0, min(1, (phase_progress - adjusted_delay) / (1 - adjusted_delay)))
                if card_progress <= 0:
                    continue

                # Ease out cubic
                eased = 1 - pow(1 - card_progress, 3)

                # Start position (mirror center)
                start_x = center_x + (i - self.num_cards // 2) * 15
                start_y = center_y

                # End position (hand) - slightly different positions for "new" cards
                new_offset = (i - self.num_cards // 2) * 70 + random.randint(-10, 10)
                end_x = self.hand_center_x + new_offset
                end_y = self.hand_y

                # Interpolate position
                card_x = start_x + (end_x - start_x) * eased
                card_y = start_y + (end_y - start_y) * eased

                # Arc motion (opposite direction)
                arc = math.sin(card_progress * math.pi) * 80
                card_y += arc

                # Rotation
                current_rotation = -rotation * (1 - eased)

                # Alpha (visible, fade out at end)
                alpha = int(220 * (1 - max(0, card_progress - 0.7) * 3.33))

                # Scale (grow slightly as they return)
                scale = 0.8 + 0.2 * eased

                # Glow effect on returning cards (they're "new")
                self._draw_card_silhouette(overlay, int(card_x), int(card_y), alpha, current_rotation, scale)

                # Extra sparkle on returning cards
                if card_progress > 0.3:
                    sparkle_alpha = int(100 * (1 - card_progress))
                    pygame.draw.circle(overlay, (255, 255, 200, sparkle_alpha),
                                      (int(card_x), int(card_y - 20)), 4)

        surface.blit(overlay, (0, 0))


def create_ability_animation(ability_name, x, y):
    """Factory function to create ability-specific animations."""
    if "Inspiring Leadership" in ability_name:
        return MoraleBoostEffect(x, y)
    elif "Vampire" in ability_name:
        return VampireEffect(x, y)
    elif "Crone" in ability_name:
        return CroneEffect(x, y)
    elif "Deploy Clones" in ability_name:
        return SummonEffect(x, y, num_summons=2)
    elif "Activate Combat Protocol" in ability_name:
        return SummonEffect(x, y, num_summons=1)
    elif "Survival Instinct" in ability_name:
        return BerserkerRageEffect(x, y)
    elif "Genetic Enhancement" in ability_name:
        return MardroemeEffect(x, y)
    elif "Look at opponent's hand" in ability_name:
        return CommunicationRevealEffect(x, y, 1920, 1080)  # Use default screen size
    else:
        return StargateActivationEffect(x, y, duration=1000)


class AITurnAnimation:
    """Manages smooth AI turn animations - thinking, selecting, playing."""
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.phase = "idle"  # idle, thinking, selecting, playing, resolving
        self.timer = 0
        self.selected_card_index = None
        self.target_row = None
        self.thinking_particles = []
        self.card_travel_progress = 0.0
        
    def start_thinking(self):
        """Start AI thinking animation."""
        self.phase = "thinking"
        self.timer = 0
        self.thinking_particles = []
        for _ in range(30):
            self.thinking_particles.append({
                'x': self.screen_width // 2 + random.uniform(-80, 80),
                'y': 60 + random.uniform(-30, 30),
                'vx': random.uniform(-0.8, 0.8),
                'vy': random.uniform(-0.8, 0.8),
                'size': random.randint(2, 5),
                'life': 1.0,
                'pulse': random.uniform(0, 6.28)
            })
    
    def start_selecting(self, card_index):
        """Start card selection animation."""
        self.phase = "selecting"
        self.timer = 0
        self.selected_card_index = card_index
    
    def start_playing(self, target_row):
        """Start card playing animation."""
        self.phase = "playing"
        self.timer = 0
        self.target_row = target_row
        self.card_travel_progress = 0.0
    
    def start_resolving(self):
        """Start effect resolution animation."""
        self.phase = "resolving"
        self.timer = 0
    
    def finish(self):
        """Finish animation."""
        self.phase = "idle"
        self.timer = 0
    
    def update(self, dt):
        """Update AI animation state."""
        if self.phase == "idle":
            return None
            
        self.timer += dt
        
        if self.phase == "thinking":
            # Update thinking particles
            for p in self.thinking_particles:
                p['x'] += p['vx'] * (dt / 16.0)
                p['y'] += p['vy'] * (dt / 16.0)
                p['pulse'] += 0.05 * (dt / 16.0)
                p['life'] = max(0, p['life'] - 0.002 * (dt / 16.0))
                
                # Bounce off edges
                if p['x'] < self.screen_width // 2 - 100 or p['x'] > self.screen_width // 2 + 100:
                    p['vx'] *= -1
                if p['y'] < 30 or p['y'] > 90:
                    p['vy'] *= -1
            
            # Respawn particles
            if len(self.thinking_particles) < 30:
                self.thinking_particles.append({
                    'x': self.screen_width // 2 + random.uniform(-80, 80),
                    'y': 60 + random.uniform(-30, 30),
                    'vx': random.uniform(-0.8, 0.8),
                    'vy': random.uniform(-0.8, 0.8),
                    'size': random.randint(2, 5),
                    'life': 1.0,
                    'pulse': random.uniform(0, 6.28)
                })
            
            if self.timer >= 1000:  # 1 second thinking
                return "thinking_done"
        
        elif self.phase == "selecting":
            if self.timer >= 600:  # 0.6 second selection highlight
                return "selecting_done"
        
        elif self.phase == "playing":
            # Smooth card travel
            self.card_travel_progress = min(1.0, self.timer / 800.0)  # 0.8 second travel
            if self.timer >= 800:
                return "playing_done"
        
        elif self.phase == "resolving":
            if self.timer >= 400:  # 0.4 second resolution
                return "resolving_done"
        
        return None
    
    def draw(self, surface, font, opponent_hand_rect):
        """Draw AI turn animation."""
        if self.phase == "thinking":
            # Draw thinking text
            text = font.render("AI is thinking...", True, (180, 200, 255))
            text_rect = text.get_rect(center=(self.screen_width // 2, 60))
            surface.blit(text, text_rect)
            
            # Draw thinking particles
            for p in self.thinking_particles:
                if p['life'] > 0:
                    alpha = int(p['life'] * (128 + 127 * math.sin(p['pulse'])))
                    size = p['size']
                    color = (120, 180, 255, min(255, alpha))
                    particle_surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.circle(particle_surf, color, (size, size), size)
                    surface.blit(particle_surf, (int(p['x']-size), int(p['y']-size)))
        
        elif self.phase == "selecting" and self.selected_card_index is not None:
            # Highlight selected card in opponent's hand
            text = font.render("AI selects card...", True, (255, 200, 180))
            text_rect = text.get_rect(center=(self.screen_width // 2, 60))
            surface.blit(text, text_rect)
            
            # Calculate card position and draw glow
            from main import CARD_WIDTH, CARD_HEIGHT
            card_spacing = int(CARD_WIDTH * 0.125)
            card_x = opponent_hand_rect.x + self.selected_card_index * (CARD_WIDTH + card_spacing)
            
            # Pulsing glow
            pulse = (math.sin(self.timer / 100.0) + 1) / 2  # 0 to 1
            glow_alpha = int(80 + pulse * 80)
            glow_size = int(10 + pulse * 8)
            glow_surf = pygame.Surface((CARD_WIDTH + glow_size*2, CARD_HEIGHT + glow_size*2), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 150, 100, glow_alpha), glow_surf.get_rect(), border_radius=10)
            surface.blit(glow_surf, (card_x - glow_size, opponent_hand_rect.y - glow_size))
        
        elif self.phase == "playing":
            # Draw card traveling to board
            text = font.render("AI plays card...", True, (255, 220, 180))
            text_rect = text.get_rect(center=(self.screen_width // 2, 60))
            surface.blit(text, text_rect)
        
        elif self.phase == "resolving":
            # Draw resolution effect
            pulse = math.sin(self.timer / 80.0)
            alpha = int(128 + 127 * pulse)
            text = font.render("Resolving...", True, (180, 255, 180, alpha))
            text_rect = text.get_rect(center=(self.screen_width // 2, 60))
            surface.blit(text, text_rect)


class ReplicatorCrawlEffect(Animation):
    """Swarming replicator spiders crawling across the screen."""
    def __init__(self, screen_width, screen_height, duration=10000):
        super().__init__(duration=duration)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.spiders = []
        
        # Create spider-like replicators
        for _ in range(60):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 4)
            self.spiders.append({
                'x': random.randint(-100, screen_width + 100),
                'y': random.randint(-100, screen_height + 100),
                'angle': angle,
                'speed': speed,
                'size': random.randint(8, 16),
                'leg_phase': random.uniform(0, math.pi * 2),
                'leg_speed': random.uniform(0.15, 0.25),
                'rotation': random.uniform(0, 360),
                'rotation_speed': random.uniform(-2, 2)
            })
    
    def draw(self, surface):
        if self.finished:
            return
        
        progress = self.get_progress()
        alpha = int(255 * (1 - progress))
        
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        
        for spider in self.spiders:
            # Update spider position - crawling movement
            spider['x'] += math.cos(spider['angle']) * spider['speed']
            spider['y'] += math.sin(spider['angle']) * spider['speed']
            spider['leg_phase'] += spider['leg_speed']
            spider['rotation'] += spider['rotation_speed']
            
            # Random direction changes for organic movement
            if random.random() < 0.02:
                spider['angle'] += random.uniform(-0.5, 0.5)
            
            # Wrap around screen
            if spider['x'] < -100:
                spider['x'] = self.screen_width + 100
            elif spider['x'] > self.screen_width + 100:
                spider['x'] = -100
            if spider['y'] < -100:
                spider['y'] = self.screen_height + 100
            elif spider['y'] > self.screen_height + 100:
                spider['y'] = -100
            
            # Calculate pulsing alpha
            pulse = abs(math.sin(spider['leg_phase']))
            spider_alpha = int(alpha * (0.7 + 0.3 * pulse))
            
            # Draw spider body (metallic block)
            body_size = spider['size']
            body_color = (140, 140, 160, spider_alpha)
            
            # Main body (tilted square)
            body_rect = pygame.Rect(
                int(spider['x'] - body_size // 2),
                int(spider['y'] - body_size // 2),
                body_size,
                body_size
            )
            
            # Create rotated body surface
            body_surf = pygame.Surface((body_size * 2, body_size * 2), pygame.SRCALPHA)
            pygame.draw.rect(body_surf, body_color, 
                           (body_size // 2, body_size // 2, body_size, body_size))
            
            # Add core glow
            core_color = (180, 180, 200, spider_alpha // 2)
            pygame.draw.rect(body_surf, core_color,
                           (body_size // 2 + 2, body_size // 2 + 2, body_size - 4, body_size - 4))
            
            # Rotate body
            rotated_body = pygame.transform.rotate(body_surf, spider['rotation'])
            body_pos = (
                int(spider['x'] - rotated_body.get_width() // 2),
                int(spider['y'] - rotated_body.get_height() // 2)
            )
            overlay.blit(rotated_body, body_pos)
            
            # Draw 8 spider legs (4 on each side)
            leg_color = (120, 120, 140, spider_alpha)
            leg_length = body_size * 1.2
            
            for i in range(8):
                # Leg angle around the body
                base_angle = (i * math.pi / 4) + math.radians(spider['rotation'])
                
                # Animate leg movement (walking motion)
                leg_bend = math.sin(spider['leg_phase'] + i * math.pi / 4) * 0.3
                
                # Leg segments
                mid_x = spider['x'] + math.cos(base_angle) * (leg_length * 0.5)
                mid_y = spider['y'] + math.sin(base_angle) * (leg_length * 0.5)
                
                end_angle = base_angle + leg_bend
                end_x = spider['x'] + math.cos(end_angle) * leg_length
                end_y = spider['y'] + math.sin(end_angle) * leg_length
                
                # Draw leg (two segments for articulation)
                pygame.draw.line(overlay, leg_color, 
                               (int(spider['x']), int(spider['y'])),
                               (int(mid_x), int(mid_y)), 2)
                pygame.draw.line(overlay, leg_color,
                               (int(mid_x), int(mid_y)),
                               (int(end_x), int(end_y)), 2)
        
        surface.blit(overlay, (0, 0))

        surface.blit(overlay, (0, 0))


# ============================================================================
# NEW STARGATE-THEMED ANIMATIONS (v5.4.0)
# ============================================================================

class DakaraPulseAnimation(Animation):
    """
    Dakara Superweapon pulse effect.
    Expanding golden shockwave rings emanating from the card's position.
    Triggered when playing the Dakara Superweapon card.
    """
    def __init__(self, x, y, duration=1500):
        super().__init__(duration)
        self.x = x
        self.y = y
        self.rings = []  # List of active rings
        self.ring_spawn_timer = 0
        self.max_rings = 4
        self.max_radius = 400

    def update(self, dt):
        active = super().update(dt)
        progress = self.get_progress()

        # Spawn new rings periodically
        self.ring_spawn_timer += dt
        if self.ring_spawn_timer > 200 and len(self.rings) < self.max_rings:
            self.ring_spawn_timer = 0
            self.rings.append({
                'radius': 0,
                'alpha': 255,
                'width': 6
            })

        # Update existing rings
        for ring in self.rings:
            ring['radius'] += dt * 0.4  # Expand outward
            ring['alpha'] = max(0, ring['alpha'] - dt * 0.15)
            ring['width'] = max(1, int(6 - ring['radius'] / 100))

        # Remove faded rings
        self.rings = [r for r in self.rings if r['alpha'] > 0]

        return active

    def draw(self, surface):
        if self.finished:
            return

        for ring in self.rings:
            if ring['radius'] <= 0 or ring['alpha'] <= 0:
                continue

            # Create ring surface
            size = int(ring['radius'] * 2) + 20
            if size < 10:
                continue

            ring_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            center = size // 2

            # Golden shockwave color with gradient
            inner_color = (255, 215, 100, int(ring['alpha']))
            outer_color = (255, 180, 50, int(ring['alpha'] * 0.5))

            # Draw multiple rings for depth
            if ring['radius'] > 5:
                pygame.draw.circle(ring_surf, outer_color, (center, center),
                                 int(ring['radius']), int(ring['width'] + 2))
                pygame.draw.circle(ring_surf, inner_color, (center, center),
                                 int(ring['radius']), int(ring['width']))
                # Bright core
                pygame.draw.circle(ring_surf, (255, 255, 200, int(ring['alpha'] * 0.8)),
                                 (center, center), int(ring['radius']), max(1, ring['width'] // 2))

            surface.blit(ring_surf, (int(self.x - center), int(self.y - center)))


class AtlantisShieldAnimation(Animation):
    """
    Atlantis city shield dome effect.
    Blue hexagonal shield bubble that expands and pulses.
    Triggered when playing the City of Atlantis card.
    """
    def __init__(self, x, y, duration=2000):
        super().__init__(duration)
        self.x = x
        self.y = y
        self.dome_radius = 0
        self.max_radius = 150
        self.pulse = 0
        self.hexagons = []  # Hexagonal pattern points

        # Pre-calculate hexagon pattern
        for ring in range(3):
            radius = 30 + ring * 35
            hex_count = 6 + ring * 6
            for i in range(hex_count):
                angle = (i / hex_count) * math.pi * 2
                self.hexagons.append({
                    'angle': angle,
                    'radius': radius,
                    'phase': random.uniform(0, math.pi * 2)
                })

    def update(self, dt):
        active = super().update(dt)
        progress = self.get_progress()

        # Expand dome
        if progress < 0.3:
            self.dome_radius = self.max_radius * (progress / 0.3)
        else:
            self.dome_radius = self.max_radius

        # Pulse effect
        self.pulse += dt * 0.01

        return active

    def draw(self, surface):
        if self.finished or self.dome_radius < 5:
            return

        progress = self.get_progress()
        alpha = int(200 * (1 - progress * 0.5))

        # Create dome surface
        size = int(self.dome_radius * 2) + 40
        dome_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2

        # Outer glow
        pygame.draw.circle(dome_surf, (50, 150, 255, alpha // 4),
                          (center, center), int(self.dome_radius + 10))

        # Main dome (semi-transparent)
        pygame.draw.circle(dome_surf, (100, 180, 255, alpha // 2),
                          (center, center), int(self.dome_radius))

        # Hexagonal pattern overlay
        for hex_info in self.hexagons:
            if hex_info['radius'] > self.dome_radius:
                continue

            angle = hex_info['angle'] + math.sin(self.pulse + hex_info['phase']) * 0.1
            hx = center + math.cos(angle) * hex_info['radius']
            hy = center + math.sin(angle) * hex_info['radius'] * 0.6  # Flatten for 3D effect

            # Draw hexagon
            hex_size = 12 + math.sin(self.pulse * 2 + hex_info['phase']) * 3
            hex_alpha = int(alpha * 0.7)

            # Simple hexagon points
            hex_points = []
            for i in range(6):
                pa = (i / 6) * math.pi * 2
                px = hx + math.cos(pa) * hex_size
                py = hy + math.sin(pa) * hex_size * 0.6
                hex_points.append((px, py))

            if len(hex_points) >= 3:
                pygame.draw.polygon(dome_surf, (150, 220, 255, hex_alpha), hex_points, 1)

        # Dome edge highlight
        pygame.draw.circle(dome_surf, (200, 240, 255, alpha),
                          (center, center), int(self.dome_radius), 2)

        surface.blit(dome_surf, (int(self.x - center), int(self.y - center)))


class HyperspaceJumpAnimation(Animation):
    """
    Hyperspace jump effect for round transitions.
    Stars stretch into lines as the view accelerates to hyperspace.
    """
    def __init__(self, screen_width, screen_height, duration=1000):
        super().__init__(duration)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        self.stars = []

        # Create stars distributed around center
        for _ in range(150):
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(50, max(screen_width, screen_height) // 2)
            self.stars.append({
                'angle': angle,
                'base_dist': dist,
                'dist': dist,
                'brightness': random.randint(150, 255),
                'size': random.randint(1, 3)
            })

    def update(self, dt):
        active = super().update(dt)
        progress = self.get_progress()

        # Accelerate stars outward
        stretch_factor = 1 + progress * 8  # Stars stretch 8x by end

        for star in self.stars:
            star['dist'] = star['base_dist'] * stretch_factor

        return active

    def draw(self, surface):
        progress = self.get_progress()
        if progress >= 1.0:
            return

        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        # Fade to white at end
        flash_alpha = 0
        if progress > 0.8:
            flash_alpha = int(255 * ((progress - 0.8) / 0.2))
            overlay.fill((255, 255, 255, flash_alpha))

        for star in self.stars:
            # Calculate stretched star position
            end_x = self.center_x + math.cos(star['angle']) * star['dist']
            end_y = self.center_y + math.sin(star['angle']) * star['dist']

            # Starting point (closer to center for stretch effect)
            stretch = progress * 50
            start_x = self.center_x + math.cos(star['angle']) * (star['base_dist'] - stretch)
            start_y = self.center_y + math.sin(star['angle']) * (star['base_dist'] - stretch)

            # Skip if off screen
            if (end_x < -50 or end_x > self.screen_width + 50 or
                end_y < -50 or end_y > self.screen_height + 50):
                continue

            # Draw star as line (stretched)
            alpha = int(star['brightness'] * (1 - progress * 0.3))
            color = (star['brightness'], star['brightness'], 255, alpha)

            if progress < 0.2:
                # Just dots at start
                pygame.draw.circle(overlay, color, (int(end_x), int(end_y)), star['size'])
            else:
                # Stretched lines
                line_width = max(1, int(star['size'] * (1 + progress * 2)))
                pygame.draw.line(overlay, color,
                               (int(start_x), int(start_y)),
                               (int(end_x), int(end_y)), line_width)

        surface.blit(overlay, (0, 0))


class WraithCullingBeamAnimation(Animation):
    """
    Wraith culling beam effect (for future Wraith faction).
    Blue energy beam descending from the top of the screen.
    """
    def __init__(self, x, y, duration=1200):
        super().__init__(duration)
        self.target_x = x
        self.target_y = y
        self.beam_width = 0
        self.max_width = 60
        self.particles = []

    def update(self, dt):
        active = super().update(dt)
        progress = self.get_progress()

        # Beam expands then contracts
        if progress < 0.3:
            self.beam_width = self.max_width * (progress / 0.3)
        elif progress > 0.7:
            self.beam_width = self.max_width * (1 - (progress - 0.7) / 0.3)
        else:
            self.beam_width = self.max_width

        # Spawn particles
        if random.random() < 0.3 and progress < 0.8:
            self.particles.append({
                'x': self.target_x + random.uniform(-self.beam_width / 2, self.beam_width / 2),
                'y': random.uniform(0, self.target_y),
                'vy': random.uniform(3, 8),
                'alpha': 200,
                'size': random.randint(2, 5)
            })

        # Update particles
        for p in self.particles[:]:
            p['y'] += p['vy']
            p['alpha'] -= 3
            if p['alpha'] <= 0 or p['y'] > self.target_y + 50:
                self.particles.remove(p)

        return active

    def draw(self, surface):
        if self.finished or self.beam_width < 1:
            return

        progress = self.get_progress()
        alpha = int(180 * (1 - progress * 0.3))

        # Draw particles first
        for p in self.particles:
            p_surf = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (100, 180, 255, int(p['alpha'])),
                             (p['size'], p['size']), p['size'])
            surface.blit(p_surf, (int(p['x'] - p['size']), int(p['y'] - p['size'])))

        # Main beam
        beam_surf = pygame.Surface((int(self.beam_width) + 40, int(self.target_y) + 40), pygame.SRCALPHA)
        center_x = beam_surf.get_width() // 2

        # Outer glow
        pygame.draw.rect(beam_surf, (50, 100, 200, alpha // 3),
                        (center_x - self.beam_width // 2 - 10, 0,
                         self.beam_width + 20, self.target_y))

        # Main beam
        pygame.draw.rect(beam_surf, (100, 180, 255, alpha),
                        (center_x - self.beam_width // 2, 0,
                         self.beam_width, self.target_y))

        # Bright core
        core_width = max(2, self.beam_width // 3)
        pygame.draw.rect(beam_surf, (200, 240, 255, alpha),
                        (center_x - core_width // 2, 0,
                         core_width, self.target_y))

        surface.blit(beam_surf, (int(self.target_x - center_x), 0))


class OriPriorFlameAnimation(Animation):
    """
    Ori Prior flame effect (for future Ori faction).
    Holy fire eruption effect with rising flames.
    """
    def __init__(self, x, y, duration=1500):
        super().__init__(duration)
        self.x = x
        self.y = y
        self.flames = []
        self.max_flames = 30

    def update(self, dt):
        active = super().update(dt)
        progress = self.get_progress()

        # Spawn flames
        if progress < 0.7 and random.random() < 0.4 and len(self.flames) < self.max_flames:
            self.flames.append({
                'x': self.x + random.uniform(-40, 40),
                'y': self.y,
                'vy': random.uniform(-3, -8),
                'vx': random.uniform(-1, 1),
                'size': random.randint(10, 25),
                'life': 1.0,
                'color_shift': random.uniform(0, 1)
            })

        # Update flames
        for flame in self.flames[:]:
            flame['y'] += flame['vy']
            flame['x'] += flame['vx']
            flame['vy'] *= 0.98  # Slow down
            flame['life'] -= 0.02
            flame['size'] = max(2, flame['size'] - 0.3)

            if flame['life'] <= 0:
                self.flames.remove(flame)

        return active

    def draw(self, surface):
        if self.finished:
            return

        for flame in self.flames:
            if flame['life'] <= 0:
                continue

            alpha = int(255 * flame['life'])
            size = int(flame['size'])

            flame_surf = pygame.Surface((size * 2, size * 3), pygame.SRCALPHA)

            # Gradient from yellow to orange to red
            t = flame['color_shift']
            r = int(255)
            g = int(200 * (1 - t) + 100 * t)
            b = int(50 * (1 - t))

            # Draw flame shape (teardrop)
            pygame.draw.ellipse(flame_surf, (r, g, b, alpha),
                              (0, size, size * 2, size * 2))
            pygame.draw.polygon(flame_surf, (r, g, b, alpha),
                              [(size, 0), (0, size), (size * 2, size)])

            # Bright core
            core_alpha = int(alpha * 0.8)
            pygame.draw.ellipse(flame_surf, (255, 255, 200, core_alpha),
                              (size // 2, size + size // 2, size, size))

            surface.blit(flame_surf, (int(flame['x'] - size), int(flame['y'] - size)))


class AsgardBeamTransportEffect(Animation):
    """Asgard transporter beam — bright white column of light with flash.

    Inspired by the show's iconic beam-in effect: a vertical column of
    brilliant white-blue light engulfs the target, peaks with a blinding
    flash, then fades with shimmering particles rising upward.

    Phases:
      0.0–0.25: Beam column materializes from top, widening
      0.25–0.50: Full intensity flash, expanding glow halo
      0.50–0.80: Beam narrows and fades, particles scatter upward
      0.80–1.00: Residual shimmer particles drift away
    """
    def __init__(self, x, y, screen_height, duration=1000):
        super().__init__(duration=duration)
        self.x = x
        self.y = y
        self.screen_height = screen_height
        self.particles = []
        for _ in range(40):
            self.particles.append({
                'x': x + random.uniform(-20, 20),
                'y': y + random.uniform(-40, 40),
                'vx': random.uniform(-1.5, 1.5),
                'vy': random.uniform(-4, -1),
                'size': random.uniform(2, 5),
                'alpha': random.randint(150, 255),
                'phase': random.uniform(0, math.pi * 2),
            })

    def update(self, dt):
        super().update(dt)
        progress = self.get_progress()
        if progress > 0.4:
            for p in self.particles:
                p['x'] += p['vx'] * (dt / 16.0)
                p['y'] += p['vy'] * (dt / 16.0)
                p['alpha'] = max(0, p['alpha'] - dt * 0.15)
        return not self.finished

    def draw(self, surface):
        if self.finished:
            return
        progress = self.get_progress()

        # Beam column dimensions
        beam_top = max(0, self.y - 300)
        beam_bottom = self.y + 40
        beam_height = beam_bottom - beam_top

        if progress < 0.25:
            # Phase 1: beam materializes from above
            phase = progress / 0.25
            draw_height = int(beam_height * phase)
            beam_width = int(12 + 28 * phase)
            alpha = int(200 * phase)
        elif progress < 0.50:
            # Phase 2: full flash
            phase = (progress - 0.25) / 0.25
            draw_height = beam_height
            beam_width = int(40 + 20 * math.sin(phase * math.pi))
            alpha = 255
        elif progress < 0.80:
            # Phase 3: beam fades and narrows
            phase = (progress - 0.50) / 0.30
            draw_height = beam_height
            beam_width = int(40 * (1 - phase))
            alpha = int(255 * (1 - phase))
        else:
            # Phase 4: just particles
            draw_height = 0
            beam_width = 0
            alpha = 0

        if draw_height > 0 and alpha > 0:
            # Outer glow (wide, soft)
            glow_w = beam_width + 50
            glow_surf = pygame.Surface((glow_w, draw_height), pygame.SRCALPHA)
            glow_alpha = max(0, alpha // 3)
            pygame.draw.rect(glow_surf, (180, 210, 255, glow_alpha),
                             (0, 0, glow_w, draw_height))
            surface.blit(glow_surf, (int(self.x - glow_w // 2),
                                     beam_bottom - draw_height))

            # Core beam (bright white-blue)
            core_surf = pygame.Surface((beam_width, draw_height), pygame.SRCALPHA)
            core_alpha = min(255, alpha)
            pygame.draw.rect(core_surf, (230, 240, 255, core_alpha),
                             (0, 0, beam_width, draw_height))
            surface.blit(core_surf, (int(self.x - beam_width // 2),
                                     beam_bottom - draw_height))

            # Hot center line
            center_w = max(2, beam_width // 4)
            center_surf = pygame.Surface((center_w, draw_height), pygame.SRCALPHA)
            pygame.draw.rect(center_surf, (255, 255, 255, core_alpha),
                             (0, 0, center_w, draw_height))
            surface.blit(center_surf, (int(self.x - center_w // 2),
                                       beam_bottom - draw_height))

        # Flash burst at peak (0.25–0.50)
        if 0.20 < progress < 0.55:
            flash_phase = (progress - 0.20) / 0.35
            flash_alpha = int(180 * math.sin(flash_phase * math.pi))
            flash_radius = int(60 + 80 * flash_phase)
            flash_surf = pygame.Surface((flash_radius * 2, flash_radius * 2),
                                        pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha),
                               (flash_radius, flash_radius), flash_radius)
            surface.blit(flash_surf, (int(self.x - flash_radius),
                                      int(self.y - flash_radius)))

        # Shimmer particles (after 0.4)
        if progress > 0.3:
            particle_alpha_scale = min(1.0, (progress - 0.3) / 0.2)
            for p in self.particles:
                pa = int(p['alpha'] * particle_alpha_scale)
                if pa <= 0:
                    continue
                # Shimmer with phase offset
                shimmer = 0.5 + 0.5 * math.sin(progress * 12 + p['phase'])
                size = max(1, int(p['size'] * shimmer))
                color = (220, 235, 255, min(255, pa))
                pygame.draw.circle(surface, color,
                                   (int(p['x']), int(p['y'])), size)

    def get_gpu_params(self):
        """Return GPU parameters for Asgard beam volumetric light column."""
        if self.finished:
            return None
        progress = self.get_progress()
        if progress > 0.8:
            return None
        # Beam visible during first 80% of effect
        beam_bottom = self.y
        beam_top = beam_bottom - self.screen_height * 0.5
        intensity = 1.0 if progress < 0.5 else max(0.0, 1.0 - (progress - 0.5) / 0.3)
        scan_progress = min(1.0, progress / 0.5)
        return {
            'type': 'asgard_beam',
            'beam_x': self.x,
            'beam_top': beam_top,
            'beam_bottom': beam_bottom,
            'intensity': intensity,
            'scan_progress': scan_progress,
            'screen_height': self.screen_height,
        }


class AnimationManager:
    """Manages all active animations with object pooling (v4.3.1)."""
    def __init__(self):
        self.animations = []
        self.effects = []
        self.weather_effect = None
        self.row_weather_effects = []  # NEW: Row-specific weather
        self.clock = pygame.time.Clock()
        self.score_animations = {}  # Track score animations per player
        self.pool = AnimationPool()  # NEW: Animation pooling system
    
    def add_animation(self, animation):
        """Add an animation to the manager."""
        self.animations.append(animation)
    
    def add_effect(self, effect):
        """Add a visual effect."""
        self.effects.append(effect)
    
    def add_score_animation(self, player_id, old_score, new_score, x, y, lead_burst=False):
        """Add a score change animation."""
        anim = ScorePopAnimation(old_score, new_score, x, y, lead_burst=lead_burst)
        self.score_animations[player_id] = anim
    
    def add_row_weather(self, weather_type, row_rect, screen_width):
        """Add weather effect to a specific row."""
        row_weather = RowWeatherEffect(weather_type, row_rect, screen_width)
        self.row_weather_effects.append(row_weather)
    
    def clear_row_weather(self):
        """Clear all row weather effects."""
        self.row_weather_effects = []
    
    def set_weather_effect(self, weather_type, screen_width, screen_height):
        """Set the weather effect."""
        if weather_type:
            self.weather_effect = WeatherEffect(weather_type, screen_width, screen_height)
        else:
            self.weather_effect = None
    
    def update(self, dt):
        """Update all animations and effects with pooling (v4.3.1)."""
        # Update animations and return finished ones to pool
        active_animations = []
        for anim in self.animations:
            if anim.update(dt):
                active_animations.append(anim)
            else:
                # Animation finished, return to pool
                self.pool.return_animation(anim)
        self.animations = active_animations

        # Update effects and return finished ones to pool
        active_effects = []
        for effect in self.effects:
            if effect.update(dt):
                active_effects.append(effect)
            else:
                # Effect finished, return to pool
                self.pool.return_animation(effect)
        self.effects = active_effects

        # Update score animations
        for player_id in list(self.score_animations.keys()):
            if not self.score_animations[player_id].update(dt):
                # Return to pool before deleting
                self.pool.return_animation(self.score_animations[player_id])
                del self.score_animations[player_id]

        # Update weather
        if self.weather_effect:
            self.weather_effect.update(dt)

        # Update row weather effects
        active_row_weather = []
        for effect in self.row_weather_effects:
            if effect.update(dt):
                active_row_weather.append(effect)
            else:
                # Return to pool
                self.pool.return_animation(effect)
        self.row_weather_effects = active_row_weather
    
    def collect_gpu_params(self):
        """Collect GPU shader parameters from all active effects and animations."""
        params = []
        for effect in self.effects:
            if hasattr(effect, 'get_gpu_params'):
                p = effect.get_gpu_params()
                if p:
                    params.append(p)
        for anim in self.animations:
            if hasattr(anim, 'get_gpu_params'):
                p = anim.get_gpu_params()
                if p:
                    params.append(p)
        return params

    def draw_effects(self, surface):
        """Draw all visual effects."""
        # Draw effects
        for effect in self.effects:
            effect.draw(surface)
    
    def draw_weather(self, surface):
        """Draw weather effect."""
        if self.weather_effect:
            self.weather_effect.draw(surface)
        
        # Draw row-specific weather
        for effect in self.row_weather_effects:
            effect.draw(surface)
    
    def draw_score_animations(self, surface, font):
        """Draw score animations."""
        for anim in self.score_animations.values():
            anim.draw(surface, font)
    
    def has_active_animations(self):
        """Check if any animations are active."""
        return len(self.animations) > 0 or len(self.effects) > 0 or len(self.score_animations) > 0

    # --- Row power surge tracking ---
    _row_power_cache = None  # {(player_id, row_name): total_power}

    def snapshot_row_powers(self, game):
        """Cache current row power totals for later comparison."""
        cache = {}
        for player in [game.player1, game.player2]:
            pid = id(player)
            for row_name, row_cards in player.board.items():
                total = sum(getattr(c, 'displayed_power', 0) for c in row_cards)
                cache[(pid, row_name)] = total
        self._row_power_cache = cache

    def check_power_surge(self, game, row_rects):
        """Compare current row powers against cache; spawn surge effects for big deltas.

        Args:
            game: Game instance
            row_rects: dict mapping (player_index, row_name) → pygame.Rect
                       e.g. {(0, 'close'): Rect, (1, 'ranged'): Rect, ...}
        """
        if self._row_power_cache is None:
            return
        for idx, player in enumerate([game.player1, game.player2]):
            pid = id(player)
            for row_name, row_cards in player.board.items():
                total = sum(getattr(c, 'displayed_power', 0) for c in row_cards)
                prev = self._row_power_cache.get((pid, row_name), total)
                delta = total - prev
                if abs(delta) >= 5:
                    rect = row_rects.get((idx, row_name))
                    if rect:
                        self.add_effect(RowPowerSurgeEffect(rect, delta))
        self._row_power_cache = None
