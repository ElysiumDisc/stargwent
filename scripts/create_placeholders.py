import pygame
import os
import sys
import math
import random

# Add parent directory to path so we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL
from unlocks import UNLOCKABLE_CARDS
from content_registry import (
    ALL_LEADER_IDS_BY_FACTION,
    get_leader_banner_name,
)

# Initialize Pygame and its font module
pygame.init()
pygame.font.init()

# --- CONFIGURATION ---
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "assets")
# Card dimensions: Match existing card assets (200x280)
CARD_WIDTH, CARD_HEIGHT = 200, 280  # Standard card size for all cards
BOARD_WIDTH, BOARD_HEIGHT = 3840, 2160  # 4K resolution

# Global settings
SKIP_EXISTING = False  # Will be set based on user input
OVERWRITE_ALL = False  # Will be set based on user input
ASKED_ONCE = False  # Track if we've asked the user yet

# Fonts (scaled for 4K)
TITLE_FONT = pygame.font.SysFont("Arial", 28, bold=True)  # Doubled from 14
POWER_FONT = pygame.font.SysFont("Arial", 40, bold=True)  # Doubled from 20

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FACTION_COLORS = {
    FACTION_TAURI: (50, 100, 180),
    FACTION_GOAULD: (200, 40, 60),  # Deeper red tint for Goa'uld assets
    FACTION_JAFFA: (215, 170, 60),  # Golden Jaffa palette
    FACTION_LUCIAN: (220, 80, 170),  # Pink Lucian Alliance hue
    FACTION_ASGARD: (150, 150, 200),
    FACTION_NEUTRAL: (120, 120, 120),
}

LEADER_BACKGROUND_ALIASES = {
}

FACTION_BACKGROUND_IDS = {
    FACTION_TAURI: "tauri",
    FACTION_GOAULD: "goauld",
    FACTION_JAFFA: "jaffa",
    FACTION_LUCIAN: "lucian",
    FACTION_ASGARD: "asgard",
}

# Allow loosely named factions (e.g., "Jaffa" vs "Jaffa Rebellion") to map to the proper palette
FACTION_NAME_ALIASES = {
    FACTION_TAURI: FACTION_TAURI,
    "Tauri": FACTION_TAURI,
    "Tau'ri Command": FACTION_TAURI,
    FACTION_GOAULD: FACTION_GOAULD,
    "Goauld": FACTION_GOAULD,
    "Goa'uld Empire": FACTION_GOAULD,
    FACTION_JAFFA: FACTION_JAFFA,
    "Jaffa": FACTION_JAFFA,
    "Jaffa Resistance": FACTION_JAFFA,
    FACTION_LUCIAN: FACTION_LUCIAN,
    "Lucian": FACTION_LUCIAN,
    "Lucian Cartel": FACTION_LUCIAN,
    FACTION_ASGARD: FACTION_ASGARD,
}


def resolve_faction_name(name):
    """Return the canonical faction key for palette lookups."""
    return FACTION_NAME_ALIASES.get(name, name)

# Some unlockable leaders intentionally reuse the same portrait art as their base counterparts.
LEADER_PORTRAIT_ALIASES = {
}

def should_create_file(file_path):
    """Check if we should create/overwrite this file based on user preference."""
    global SKIP_EXISTING, OVERWRITE_ALL, ASKED_ONCE
    
    if not os.path.exists(file_path):
        return True  # File doesn't exist, create it
    
    # If user already chose to overwrite all or skip all
    if OVERWRITE_ALL:
        return True
    if SKIP_EXISTING:
        return False
    
    # Ask user on first existing file
    if not ASKED_ONCE:
        ASKED_ONCE = True
        print("\n" + "="*60)
        print("EXISTING FILES DETECTED")
        print("="*60)
        print("Some asset files already exist in the assets folder.")
        print("What would you like to do?")
        print()
        print("  [O] Overwrite ALL existing files (replace with placeholders)")
        print("  [S] Skip ALL existing files (keep your custom artwork)")
        print("  [A] Ask for each file individually")
        print()
        
        while True:
            choice = input("Your choice (O/S/A): ").strip().upper()
            if choice == 'O':
                OVERWRITE_ALL = True
                print("✓ Will overwrite all existing files\n")
                return True
            elif choice == 'S':
                SKIP_EXISTING = True
                print("✓ Will skip all existing files\n")
                return False
            elif choice == 'A':
                print("✓ Will ask for each file\n")
                break
            else:
                print("Invalid choice. Please enter O, S, or A.")
    
    # Ask for this specific file
    filename = os.path.basename(file_path)
    while True:
        choice = input(f"File exists: {filename} - Overwrite? (y/n): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print("Please enter 'y' or 'n'.")

def create_card_image(card):
    """Creates a placeholder image for a single card."""
    surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
    
    # Background color based on faction
    faction_key = resolve_faction_name(card.faction)
    faction_color = FACTION_COLORS.get(faction_key, (80, 80, 80))
    surface.fill(faction_color)
    
    # Border
    pygame.draw.rect(surface, WHITE, surface.get_rect(), width=2, border_radius=10)
    
    # Card Name
    title_text = TITLE_FONT.render(card.name, True, WHITE)
    title_rect = title_text.get_rect(center=(CARD_WIDTH / 2, 20))
    surface.blit(title_text, title_rect)
    
    # Card Power
    if card.row not in ["special", "weather"]:
        power_text = POWER_FONT.render(str(card.power), True, BLACK)
        power_circle = pygame.draw.circle(surface, WHITE, (30, 30), 20)
        power_rect = power_text.get_rect(center=power_circle.center)
        surface.blit(power_text, power_rect)

    # Save the image only if allowed
    image_path = os.path.join(ASSETS_DIR, f"{card.id}.png")
    if should_create_file(image_path):
        pygame.image.save(surface, image_path)
        return image_path
    return None

def create_leader_portrait(leader_id, faction):
    """Creates a placeholder leader portrait image."""
    # Leader portraits are larger and more prominent
    LEADER_WIDTH = 200
    LEADER_HEIGHT = 280
    
    surface = pygame.Surface((LEADER_WIDTH, LEADER_HEIGHT))
    
    # Get faction color
    faction_key = resolve_faction_name(faction)
    faction_color = FACTION_COLORS.get(faction_key, (120, 120, 120))
    
    # Gradient background
    for y in range(LEADER_HEIGHT):
        brightness = 1.0 - (y / LEADER_HEIGHT) * 0.3
        shade = tuple(int(c * brightness) for c in faction_color)
        pygame.draw.line(surface, shade, (0, y), (LEADER_WIDTH, y))
    
    # Golden border (leader = special)
    pygame.draw.rect(surface, (255, 215, 0), surface.get_rect(), width=4, border_radius=5)
    
    # "LEADER" text at top
    leader_font = pygame.font.SysFont("Arial", 18, bold=True)
    leader_text = leader_font.render("LEADER", True, (255, 215, 0))
    text_rect = leader_text.get_rect(center=(LEADER_WIDTH // 2, 20))
    surface.blit(leader_text, text_rect)
    
    # Character name (extract from ID)
    name = leader_id.split('_', 1)[1].replace('_', ' ').title()
    name_font = pygame.font.SysFont("Arial", 14, bold=True)
    name_text = name_font.render(name, True, WHITE)
    name_rect = name_text.get_rect(center=(LEADER_WIDTH // 2, LEADER_HEIGHT - 20))
    
    # Black background for name
    bg_rect = name_rect.inflate(10, 5)
    pygame.draw.rect(surface, BLACK, bg_rect)
    surface.blit(name_text, name_rect)
    
    # Large faction symbol in center (diamond)
    center_x = LEADER_WIDTH // 2
    center_y = LEADER_HEIGHT // 2
    diamond_size = 50
    diamond_points = [
        (center_x, center_y - diamond_size),
        (center_x + diamond_size, center_y),
        (center_x, center_y + diamond_size),
        (center_x - diamond_size, center_y),
    ]
    pygame.draw.polygon(surface, WHITE, diamond_points)
    pygame.draw.polygon(surface, (255, 215, 0), diamond_points, width=3)
    
    # Save the leader portrait only if allowed
    portrait_id = LEADER_PORTRAIT_ALIASES.get(leader_id, leader_id)
    image_path = os.path.join(ASSETS_DIR, f"{portrait_id}_leader.png")
    if should_create_file(image_path):
        pygame.image.save(surface, image_path)
        return image_path
    return None

def create_decoy_placeholder():
    """Create the shared decoy placeholder used by Ring Transport."""
    surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
    surface.fill((110, 110, 110))
    pygame.draw.rect(surface, WHITE, surface.get_rect(), width=3, border_radius=10)
    title_text = TITLE_FONT.render("Asgard Decoy", True, WHITE)
    title_rect = title_text.get_rect(center=(CARD_WIDTH / 2, 28))
    surface.blit(title_text, title_rect)
    label_font = pygame.font.SysFont("Arial", 22, bold=True)
    label_text = label_font.render("DECOY", True, WHITE)
    label_rect = label_text.get_rect(center=(CARD_WIDTH / 2, CARD_HEIGHT - 30))
    surface.blit(label_text, label_rect)

    image_path = os.path.join(ASSETS_DIR, "decoy.png")
    if should_create_file(image_path):
        pygame.image.save(surface, image_path)
        return image_path
    return None

def create_ship_placeholder(faction, ship_type="generic"):
    """Creates a placeholder ship image for background battles."""
    SHIP_SIZE = 120  # 120x120 for good detail
    
    surface = pygame.Surface((SHIP_SIZE, SHIP_SIZE), pygame.SRCALPHA)
    
    # Get faction color
    faction_key = resolve_faction_name(faction)
    faction_color = FACTION_COLORS.get(faction_key, (120, 120, 120))
    
    # Draw ship body (more detailed than triangle)
    center_x = SHIP_SIZE // 2
    center_y = SHIP_SIZE // 2
    
    # Main hull (elongated hexagon)
    hull_points = [
        (center_x, 20),  # Nose
        (center_x + 20, 35),
        (center_x + 25, 70),
        (center_x + 20, 95),
        (center_x, 105),  # Tail
        (center_x - 20, 95),
        (center_x - 25, 70),
        (center_x - 20, 35),
    ]
    pygame.draw.polygon(surface, faction_color, hull_points)
    pygame.draw.polygon(surface, WHITE, hull_points, 2)
    
    # Wings/nacelles
    # Left wing
    left_wing = [
        (center_x - 20, 45),
        (center_x - 45, 50),
        (center_x - 48, 75),
        (center_x - 25, 72),
    ]
    pygame.draw.polygon(surface, faction_color, left_wing)
    pygame.draw.polygon(surface, WHITE, left_wing, 2)
    
    # Right wing
    right_wing = [
        (center_x + 20, 45),
        (center_x + 45, 50),
        (center_x + 48, 75),
        (center_x + 25, 72),
    ]
    pygame.draw.polygon(surface, faction_color, right_wing)
    pygame.draw.polygon(surface, WHITE, right_wing, 2)
    
    # Cockpit/bridge (lighter color)
    cockpit_color = tuple(min(c + 50, 255) for c in faction_color)
    pygame.draw.ellipse(surface, cockpit_color, (center_x - 12, 30, 24, 30))
    pygame.draw.ellipse(surface, WHITE, (center_x - 12, 30, 24, 30), 1)
    
    # Engine glow (at tail)
    engine_color = (*faction_color, 200)
    engine_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
    pygame.draw.circle(engine_surf, engine_color, (15, 15), 12)
    pygame.draw.circle(engine_surf, (255, 255, 255, 150), (15, 15), 8)
    surface.blit(engine_surf, (center_x - 15, 95))
    
    # Detail lines
    detail_color = tuple(max(c - 30, 0) for c in faction_color)
    pygame.draw.line(surface, detail_color, (center_x, 25), (center_x, 100), 2)
    pygame.draw.line(surface, detail_color, (center_x - 15, 50), (center_x - 15, 85), 1)
    pygame.draw.line(surface, detail_color, (center_x + 15, 50), (center_x + 15, 85), 1)
    
    # Faction-specific details
    if "Tau'ri" in faction:
        # Earth insignia (simple star)
        star_points = []
        for i in range(5):
            angle = i * 144 - 90
            x = center_x + int(8 * math.cos(math.radians(angle)))
            y = 45 + int(8 * math.sin(math.radians(angle)))
            star_points.append((x, y))
        pygame.draw.polygon(surface, WHITE, star_points)
    
    elif "Goa'uld" in faction:
        # Egyptian eye symbol
        pygame.draw.ellipse(surface, WHITE, (center_x - 8, 42, 16, 8))
        pygame.draw.circle(surface, WHITE, (center_x, 46), 3)
    
    elif "Asgard" in faction:
        # Smooth curves (additional rounded sections)
        pygame.draw.circle(surface, cockpit_color, (center_x, 35), 8)
        pygame.draw.circle(surface, WHITE, (center_x, 35), 8, 1)
    
    # Ship type label for identification
    label_font = pygame.font.SysFont("Arial", 10)
    label_text = label_font.render(ship_type.upper(), True, WHITE)
    label_rect = label_text.get_rect(center=(center_x, 115))
    surface.blit(label_text, label_rect)
    
    return surface


def create_faction_background(asset_id, faction_name, base_color):
    """Create a 4K background for faction selection."""
    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

    top_color = tuple(min(255, int(c * 0.55) + 25) for c in base_color)
    bottom_color = tuple(max(0, int(c * 0.15)) for c in base_color)
    for y in range(BOARD_HEIGHT):
        t = y / BOARD_HEIGHT
        blend_color = (
            int(top_color[0] * (1 - t) + bottom_color[0] * t),
            int(top_color[1] * (1 - t) + bottom_color[1] * t),
            int(top_color[2] * (1 - t) + bottom_color[2] * t),
        )
        pygame.draw.line(surface, blend_color, (0, y), (BOARD_WIDTH, y))

    # Dense starfield
    for _ in range(900):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        brightness = random.randint(120, 255)
        size = random.choice([2, 2, 3, 4])
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)

    # Translucent Stargate motif
    center_x, center_y = BOARD_WIDTH // 2, BOARD_HEIGHT // 2
    motif_surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    radius = min(BOARD_WIDTH, BOARD_HEIGHT) // 2
    pygame.draw.circle(motif_surface, (*base_color, 80), (center_x, center_y), radius, 80)
    pygame.draw.circle(motif_surface, (255, 255, 255, 40), (center_x, center_y), radius - 60, 12)
    surface.blit(motif_surface, (0, 0))

    # Diamond insignia
    badge = pygame.Surface((900, 900), pygame.SRCALPHA)
    badge_color = tuple(min(255, c + 90) for c in base_color)
    pygame.draw.polygon(
        badge,
        badge_color,
        [(450, 40), (860, 450), (450, 860), (40, 450)],
    )
    pygame.draw.polygon(
        badge,
        (255, 255, 255, 220),
        [(450, 140), (720, 450), (450, 760), (180, 450)],
        width=8,
    )
    surface.blit(badge, (center_x - 450, center_y - 450), special_flags=pygame.BLEND_PREMULTIPLIED)

    # Title text
    title_font = pygame.font.SysFont("Eurostile, Arial", 140, bold=True)
    title_text = title_font.render(faction_name.upper(), True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(center_x, int(center_y * 0.35)))
    surface.blit(title_text, title_rect)

    motto_font = pygame.font.SysFont("Arial", 48, italic=True)
    motto_text = motto_font.render("Stargate Command", True, (220, 220, 220))
    motto_rect = motto_text.get_rect(center=(center_x, title_rect.bottom + 50))
    surface.blit(motto_text, motto_rect)

    path = os.path.join(ASSETS_DIR, f"faction_bg_{asset_id}.png")
    if should_create_file(path):
        pygame.image.save(surface, path)
        return path
    return None


def create_menu_background():
    """Creates a menu background image."""
    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    
    # Deep space background
    surface.fill((5, 10, 20))
    
    # Add stars (scaled for 4K - 4x as many)
    for _ in range(800):  # 200 * 4 for 4K
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        brightness = random.randint(150, 255)
        size = random.choice([2, 2, 2, 4, 4, 6])  # Doubled sizes for 4K
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)
    
    # Add nebula-like clouds (scaled for 4K)
    for _ in range(10):  # More nebulas for 4K
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(400, 800)  # Doubled for 4K
        nebula_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        color = random.choice([
            (50, 100, 150, 30),   # Blue
            (100, 50, 150, 30),   # Purple
            (150, 50, 100, 30)    # Pink
        ])
        pygame.draw.circle(nebula_surf, color, (size, size), size)
        surface.blit(nebula_surf, (x - size, y - size))
    
    # Add Stargate silhouette in background (subtle) - scaled for 4K
    center_x, center_y = BOARD_WIDTH // 2, BOARD_HEIGHT // 2
    gate_radius = 600  # Doubled for 4K
    gate_surf = pygame.Surface((gate_radius * 2, gate_radius * 2), pygame.SRCALPHA)
    
    # Outer ring (subtle)
    pygame.draw.circle(gate_surf, (40, 60, 80, 80), (gate_radius, gate_radius), gate_radius, 60)  # Doubled thickness
    pygame.draw.circle(gate_surf, (60, 80, 100, 100), (gate_radius, gate_radius), gate_radius, 6)  # Doubled thickness
    
    # Inner ring
    inner_radius = gate_radius - 80  # Doubled offset
    pygame.draw.circle(gate_surf, (30, 45, 65, 60), (gate_radius, gate_radius), inner_radius, 40)  # Doubled thickness
    
    # Chevrons (9 points)
    for i in range(9):
        angle = i * 40 - 90
        angle_rad = math.radians(angle)
        x = gate_radius + math.cos(angle_rad) * gate_radius
        y = gate_radius + math.sin(angle_rad) * gate_radius
        
        # Small triangles (scaled for 4K)
        size = 30  # Doubled for 4K
        points = [
            (x, y - size),
            (x - size // 2, y + size // 2),
            (x + size // 2, y + size // 2)
        ]
        pygame.draw.polygon(gate_surf, (80, 100, 120, 120), points)
    
    surface.blit(gate_surf, (center_x - gate_radius, center_y - gate_radius))
    
    # Save only if allowed
    path = os.path.join(ASSETS_DIR, "menu_background.png")
    if should_create_file(path):
        pygame.image.save(surface, path)
        print(f"Created menu background: {path}")
        return path
    return None


def create_rule_menu_background():
    """Creates a dedicated background for the in-game rule compendium."""
    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    
    # Deep gradient backdrop
    top_color = (10, 16, 32)
    bottom_color = (4, 4, 12)
    for y in range(BOARD_HEIGHT):
        t = y / BOARD_HEIGHT
        color = (
            int(top_color[0] * (1 - t) + bottom_color[0] * t),
            int(top_color[1] * (1 - t) + bottom_color[1] * t),
            int(top_color[2] * (1 - t) + bottom_color[2] * t),
        )
        pygame.draw.line(surface, color, (0, y), (BOARD_WIDTH, y))

    # Subtle starfield
    for _ in range(600):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        brightness = random.randint(120, 200)
        size = random.choice([1, 1, 2])
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)

    # Blueprint grid overlay
    grid_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    grid_color = (40, 80, 140, 30)
    grid_spacing = 100
    for x in range(0, BOARD_WIDTH, grid_spacing):
        pygame.draw.line(grid_surf, grid_color, (x, 0), (x, BOARD_HEIGHT), 1)
    for y in range(0, BOARD_HEIGHT, grid_spacing):
        pygame.draw.line(grid_surf, grid_color, (0, y), (BOARD_WIDTH, y), 1)
    surface.blit(grid_surf, (0, 0))

    # Center holographic panel
    panel_width = int(BOARD_WIDTH * 0.75)
    panel_height = int(BOARD_HEIGHT * 0.8)
    panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(panel_surf, (20, 40, 70, 200), panel_surf.get_rect(), border_radius=30)
    pygame.draw.rect(panel_surf, (120, 190, 255, 60), panel_surf.get_rect(), width=4, border_radius=30)
    surface.blit(panel_surf, ((BOARD_WIDTH - panel_width) // 2, (BOARD_HEIGHT - panel_height) // 2))

    # Corner chevrons
    chevron_color = (100, 160, 220, 180)
    chevron_surf = pygame.Surface((200, 200), pygame.SRCALPHA)
    pygame.draw.polygon(chevron_surf, chevron_color, [(0, 0), (60, 0), (0, 60)])
    surface.blit(chevron_surf, (40, 40))
    surface.blit(pygame.transform.flip(chevron_surf, True, False), (BOARD_WIDTH - 240, 40))
    surface.blit(pygame.transform.flip(chevron_surf, False, True), (40, BOARD_HEIGHT - 240))
    surface.blit(pygame.transform.flip(chevron_surf, True, True), (BOARD_WIDTH - 240, BOARD_HEIGHT - 240))

    path = os.path.join(ASSETS_DIR, "rule_menu_bg.png")
    if should_create_file(path):
        pygame.image.save(surface, path)
        print(f"Created rule menu background: {path}")
        return path
    return None


def create_custom_font():
    """Creates a placeholder custom font file."""
    # For now, just create a text file documenting what font to use
    font_path = os.path.join(ASSETS_DIR, "custom_font.txt")
    with open(font_path, 'w') as f:
        f.write("Custom Font Configuration\n")
        f.write("=========================\n\n")
        f.write("Primary Font: 'Stargate' or similar sci-fi font\n")
        f.write("Fallback: Arial Bold\n\n")
        f.write("Font Sizes:\n")
        f.write("  - Title: 72pt\n")
        f.write("  - Subtitle: 36pt\n")
        f.write("  - Card Name: 18pt\n")
        f.write("  - Card Power: 24pt bold\n")
        f.write("  - UI Text: 16pt\n")
        f.write("  - Small Text: 12pt\n\n")
        f.write("To customize: Replace system fonts in main.py with pygame.font.Font('assets/yourfont.ttf', size)\n")
    print(f"Created: {font_path}")
    return font_path

def create_deck_building_background():
    """Creates placeholder background for deck building screen."""
    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    
    # Dark space background
    surface.fill((10, 10, 20))
    
    # Add starfield
    for _ in range(200):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        brightness = random.randint(100, 255)
        size = random.choice([1, 1, 1, 2])
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)
    
    # Add nebula effect (blurred colored areas)
    for _ in range(5):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        radius = random.randint(100, 300)
        color_choice = random.choice([
            (50, 50, 150, 30),   # Blue nebula
            (150, 50, 150, 30),  # Purple nebula
            (50, 150, 150, 30),  # Cyan nebula
        ])
        nebula_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(nebula_surface, color_choice, (radius, radius), radius)
        surface.blit(nebula_surface, (x - radius, y - radius), special_flags=pygame.BLEND_ADD)
    
    # Add title area at top
    title_surface = pygame.Surface((BOARD_WIDTH, 120), pygame.SRCALPHA)
    title_surface.fill((20, 30, 50, 200))
    pygame.draw.line(title_surface, (100, 150, 200), (0, 115), (BOARD_WIDTH, 115), 3)
    surface.blit(title_surface, (0, 0))
    
    # Add title text
    title_font = pygame.font.SysFont("Arial", 56, bold=True)
    title_text = title_font.render("DECK BUILDING", True, (200, 220, 255))
    title_rect = title_text.get_rect(center=(BOARD_WIDTH // 2, 60))
    surface.blit(title_text, title_rect)
    
    # Save only if allowed
    path = os.path.join(ASSETS_DIR, "deck_building_bg.png")
    if should_create_file(path):
        pygame.image.save(surface, path)
        print(f"Created: {path}")
        return path
    return None

def create_leader_background(leader_name, faction, card_id):
    """Creates a unique background for each specific leader selection screen."""
    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    
    # Faction-specific color schemes
    faction_themes = {
        FACTION_TAURI: {
            "bg_color": (15, 25, 45),
            "accent": (100, 150, 220),
            "secondary": (60, 90, 130)
        },
        FACTION_GOAULD: {
            "bg_color": (45, 15, 20),
            "accent": (210, 60, 70),
            "secondary": (140, 35, 45)
        },
        FACTION_JAFFA: {
            "bg_color": (35, 25, 10),
            "accent": (230, 180, 70),
            "secondary": (150, 110, 45)
        },
        FACTION_LUCIAN: {
            "bg_color": (30, 10, 30),
            "accent": (235, 110, 190),
            "secondary": (150, 60, 140)
        },
        FACTION_ASGARD: {
            "bg_color": (10, 20, 25),
            "accent": (100, 180, 200),
            "secondary": (50, 90, 110)
        }
    }
    
    canonical_faction = resolve_faction_name(faction)
    theme = faction_themes.get(canonical_faction, faction_themes[FACTION_TAURI])
    
    # Base gradient background
    bg_color = theme["bg_color"]
    for y in range(BOARD_HEIGHT):
        progress = y / BOARD_HEIGHT
        color = tuple(int(c * (1 - progress * 0.3)) for c in bg_color)
        pygame.draw.line(surface, color, (0, y), (BOARD_WIDTH, y))
    
    # Add unique starfield for each leader (based on card_id seed)
    import random
    random.seed(hash(card_id))
    for _ in range(300):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(1, 3)
        brightness = random.randint(100, 255)
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)
    
    # Large decorative circle pattern in background (unique per leader)
    center_x, center_y = BOARD_WIDTH // 2, BOARD_HEIGHT // 2
    
    # Unique pattern based on leader
    num_circles = 3 + (hash(card_id) % 3)
    for i in range(num_circles, 0, -1):
        radius = 250 + i * 120
        alpha_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
        alpha = 25 - i * 5
        color_with_alpha = theme["accent"] + (alpha,)
        pygame.draw.circle(alpha_surf, color_with_alpha, (center_x, center_y), radius, 3)
        surface.blit(alpha_surf, (0, 0))
    
    # Diagonal accent lines (direction varies per leader)
    line_color = theme["secondary"] + (20,)
    alpha_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    direction = 1 if hash(card_id) % 2 == 0 else -1
    for i in range(0, BOARD_WIDTH + BOARD_HEIGHT, 100):
        if direction > 0:
            pygame.draw.line(alpha_surf, line_color, (i, 0), (i - BOARD_HEIGHT, BOARD_HEIGHT), 2)
        else:
            pygame.draw.line(alpha_surf, line_color, (0, i), (BOARD_WIDTH, i - BOARD_WIDTH), 2)
    surface.blit(alpha_surf, (0, 0))
    
    # Top/bottom accent bars
    pygame.draw.rect(surface, theme["accent"], (0, 0, BOARD_WIDTH, 10))
    pygame.draw.rect(surface, theme["secondary"], (0, 10, BOARD_WIDTH, 5))
    pygame.draw.rect(surface, theme["secondary"], (0, BOARD_HEIGHT - 15, BOARD_WIDTH, 5))
    pygame.draw.rect(surface, theme["accent"], (0, BOARD_HEIGHT - 10, BOARD_WIDTH, 10))
    
    # Corner decorations
    corner_size = 150
    corner_color = theme["accent"] + (60,)
    
    # Top-left
    alpha_surf = pygame.Surface((corner_size, corner_size), pygame.SRCALPHA)
    pygame.draw.arc(alpha_surf, corner_color, (0, 0, corner_size * 2, corner_size * 2), 
                   math.pi, math.pi * 1.5, 5)
    surface.blit(alpha_surf, (0, 0))
    
    # Top-right
    alpha_surf = pygame.Surface((corner_size, corner_size), pygame.SRCALPHA)
    pygame.draw.arc(alpha_surf, corner_color, (-corner_size, 0, corner_size * 2, corner_size * 2), 
                   math.pi * 1.5, math.pi * 2, 5)
    surface.blit(alpha_surf, (BOARD_WIDTH - corner_size, 0))
    
    # Bottom-left
    alpha_surf = pygame.Surface((corner_size, corner_size), pygame.SRCALPHA)
    pygame.draw.arc(alpha_surf, corner_color, (0, -corner_size, corner_size * 2, corner_size * 2), 
                   math.pi * 0.5, math.pi, 5)
    surface.blit(alpha_surf, (0, BOARD_HEIGHT - corner_size))
    
    # Bottom-right
    alpha_surf = pygame.Surface((corner_size, corner_size), pygame.SRCALPHA)
    pygame.draw.arc(alpha_surf, corner_color, (-corner_size, -corner_size, corner_size * 2, corner_size * 2), 
                   0, math.pi * 0.5, 5)
    surface.blit(alpha_surf, (BOARD_WIDTH - corner_size, BOARD_HEIGHT - corner_size))
    
    # Leader-specific details: add faction emblem suggestion in center
    emblem_font = pygame.font.Font(None, 80)
    leader_initial = leader_name[0].upper() if leader_name else "?"
    emblem_text = emblem_font.render(leader_initial, True, theme["accent"] + (40,))
    emblem_rect = emblem_text.get_rect(center=(center_x, center_y))
    surface.blit(emblem_text, emblem_rect)
    
    # Save with unique filename per leader only if allowed
    # Certain leaders share the same cinematic background (ex: Bra'tac vs Master Bra'tac)
    normalized_id = LEADER_BACKGROUND_ALIASES.get(card_id, card_id)
    filename = f"leader_bg_{normalized_id}.png"
    path = os.path.join(ASSETS_DIR, filename)
    
    # Ensure alias file is removed to prevent stale assets (e.g., leader_bg_jaffa_master_bratac.png)
    if normalized_id != card_id:
        alias_path = os.path.join(ASSETS_DIR, f"leader_bg_{card_id}.png")
        if os.path.exists(alias_path):
            os.remove(alias_path)
    
    if should_create_file(path):
        pygame.image.save(surface, path)
        return path
    return None

def create_board_image():
    """Creates a placeholder for the game board."""
    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    surface.fill((20, 40, 30))  # Dark green background
    pygame.draw.rect(surface, (10, 20, 15), (0, 0, BOARD_WIDTH, BOARD_HEIGHT), width=20)
    image_path = os.path.join(ASSETS_DIR, "board_background.png")
    if should_create_file(image_path):
        pygame.image.save(surface, image_path)
        print(f"Created board background: {image_path}")
        return image_path
    return None

def create_unlockable_card_image(card_id, card_data):
    """Creates a special placeholder image for unlockable cards."""
    surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
    
    # Rarity colors
    rarity_colors = {
        'common': (200, 200, 200),
        'rare': (100, 150, 255),
        'epic': (200, 100, 255),
        'legendary': (255, 200, 50)
    }
    
    # Background - darker with rarity accent
    bg_color = (40, 40, 50)
    surface.fill(bg_color)
    
    # Rarity border (thicker for higher rarity)
    rarity = card_data.get('rarity', 'common')
    border_color = rarity_colors.get(rarity, (200, 200, 200))
    border_width = 3 if rarity in ['epic', 'legendary'] else 2
    pygame.draw.rect(surface, border_color, surface.get_rect(), width=border_width, border_radius=10)
    
    # "NEW CARD" banner at top
    banner_font = pygame.font.SysFont("Arial", 16, bold=True)
    banner_text = banner_font.render("NEW CARD", True, (255, 215, 0))
    banner_rect = banner_text.get_rect(center=(CARD_WIDTH / 2, 20))
    # Black background for banner
    bg_rect = banner_rect.inflate(10, 4)
    pygame.draw.rect(surface, (0, 0, 0), bg_rect)
    surface.blit(banner_text, banner_rect)
    
    # Card Name (wrapped if needed)
    name_font = pygame.font.SysFont("Arial", 12, bold=True)
    name = card_data['name']
    name_text = name_font.render(name, True, WHITE)
    name_rect = name_text.get_rect(center=(CARD_WIDTH / 2, CARD_HEIGHT - 60))
    surface.blit(name_text, name_rect)
    
    # Rarity badge
    rarity_text = TITLE_FONT.render(rarity.upper(), True, border_color)
    rarity_rect = rarity_text.get_rect(center=(CARD_WIDTH / 2, CARD_HEIGHT - 40))
    surface.blit(rarity_text, rarity_rect)
    
    # Power (if applicable)
    if card_data['row'] not in ["special", "weather"]:
        power_text = POWER_FONT.render(str(card_data['power']), True, BLACK)
        power_circle = pygame.draw.circle(surface, border_color, (30, 50), 20)
        pygame.draw.circle(surface, BLACK, (30, 50), 20, width=2)
        power_rect = power_text.get_rect(center=power_circle.center)
        surface.blit(power_text, power_rect)
    
    # Large "?" or lock symbol in center
    lock_font = pygame.font.SysFont("Arial", 80, bold=True)
    lock_text = lock_font.render("?", True, border_color)
    lock_rect = lock_text.get_rect(center=(CARD_WIDTH / 2, CARD_HEIGHT / 2))
    surface.blit(lock_text, lock_rect)
    
    # Save the image only if allowed
    image_path = os.path.join(ASSETS_DIR, f"{card_id}.png")
    if should_create_file(image_path):
        pygame.image.save(surface, image_path)
        return image_path
    return None

def create_card_back_image():
    """Creates a high-quality card back placeholder for 4K."""
    surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
    
    # Base color - Dark blue/black space theme
    surface.fill((20, 30, 50))
    
    # Outer border - bright blue
    pygame.draw.rect(surface, (100, 150, 200), (0, 0, CARD_WIDTH, CARD_HEIGHT), 
                    6, border_radius=16)
    
    # Inner decorative border
    pygame.draw.rect(surface, (60, 90, 130), (16, 16, CARD_WIDTH-32, CARD_HEIGHT-32), 
                    4, border_radius=12)
    
    # Center Stargate symbol
    center_x = CARD_WIDTH // 2
    center_y = CARD_HEIGHT // 2
    
    # Outer ring (largest)
    ring_radius = min(CARD_WIDTH, CARD_HEIGHT) // 3
    pygame.draw.circle(surface, (100, 150, 200), (center_x, center_y), ring_radius, 6)
    
    # Middle ring
    pygame.draw.circle(surface, (80, 120, 170), (center_x, center_y), 
                      int(ring_radius * 0.8), 4)
    
    # Inner ring (smallest)
    pygame.draw.circle(surface, (60, 90, 130), (center_x, center_y), 
                      int(ring_radius * 0.6), 3)
    
    # 9 Chevron markers around the ring
    chevron_radius = ring_radius + 20
    for i in range(9):
        angle = (i / 9) * 2 * math.pi - math.pi / 2  # Start at top
        chevron_x = center_x + int(math.cos(angle) * chevron_radius)
        chevron_y = center_y + int(math.sin(angle) * chevron_radius)
        
        # Chevron wedge shape
        wedge_size = 16
        wedge_points = [
            (chevron_x, chevron_y - wedge_size),
            (chevron_x + wedge_size // 2, chevron_y + wedge_size // 2),
            (chevron_x - wedge_size // 2, chevron_y + wedge_size // 2)
        ]
        pygame.draw.polygon(surface, (150, 180, 220), wedge_points)
        pygame.draw.polygon(surface, (180, 210, 255), wedge_points, 2)
    
    # Center symbol (triangle - like Earth's point of origin)
    triangle_size = int(ring_radius * 0.3)
    triangle_points = [
        (center_x, center_y - triangle_size),
        (center_x - triangle_size, center_y + triangle_size),
        (center_x + triangle_size, center_y + triangle_size)
    ]
    pygame.draw.polygon(surface, (150, 180, 220), triangle_points, 6)
    
    # Add some decorative lines in corners
    corner_size = 40
    corner_color = (100, 150, 200)
    # Top-left corner
    pygame.draw.line(surface, corner_color, (20, 20), (20 + corner_size, 20), 4)
    pygame.draw.line(surface, corner_color, (20, 20), (20, 20 + corner_size), 4)
    # Top-right corner
    pygame.draw.line(surface, corner_color, (CARD_WIDTH - 20, 20), 
                    (CARD_WIDTH - 20 - corner_size, 20), 4)
    pygame.draw.line(surface, corner_color, (CARD_WIDTH - 20, 20), 
                    (CARD_WIDTH - 20, 20 + corner_size), 4)
    # Bottom-left corner
    pygame.draw.line(surface, corner_color, (20, CARD_HEIGHT - 20), 
                    (20 + corner_size, CARD_HEIGHT - 20), 4)
    pygame.draw.line(surface, corner_color, (20, CARD_HEIGHT - 20), 
                    (20, CARD_HEIGHT - 20 - corner_size), 4)
    # Bottom-right corner
    pygame.draw.line(surface, corner_color, (CARD_WIDTH - 20, CARD_HEIGHT - 20), 
                    (CARD_WIDTH - 20 - corner_size, CARD_HEIGHT - 20), 4)
    pygame.draw.line(surface, corner_color, (CARD_WIDTH - 20, CARD_HEIGHT - 20), 
                    (CARD_WIDTH - 20, CARD_HEIGHT - 20 - corner_size), 4)
    
    # Add "STARGATE" text at bottom
    title_font = pygame.font.SysFont("Arial", 32, bold=True)
    title_text = title_font.render("STARGATE", True, (150, 180, 220))
    title_rect = title_text.get_rect(center=(center_x, CARD_HEIGHT - 40))
    surface.blit(title_text, title_rect)
    
    # Save card back only if allowed
    path = os.path.join(ASSETS_DIR, "card_back.png")
    if should_create_file(path):
        pygame.image.save(surface, path)
        print(f"  - {path}")
        return path
    return None

def main():
    """Generates all placeholder assets."""
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
    
    # Create ships folder
    ships_dir = os.path.join(ASSETS_DIR, "ships")
    if not os.path.exists(ships_dir):
        os.makedirs(ships_dir)
    
    print("Generating card images...")
    for card_id, card in ALL_CARDS.items():
        path = create_card_image(card)
        if path:
            print(f"  ✓ {path}")
        else:
            print(f"  ⊗ Skipped: {card_id}.png (already exists)")
    
    print("\nGenerating UNLOCKABLE card images...")
    for card_id, card_data in UNLOCKABLE_CARDS.items():
        path = create_unlockable_card_image(card_id, card_data)
        if path:
            print(f"  ✓ {path} [{card_data['rarity'].upper()}]")
        else:
            print(f"  ⊗ Skipped: {card_id}.png (already exists)")

    print("\nGenerating DECOY placeholder...")
    decoy_path = create_decoy_placeholder()
    if decoy_path:
        print(f"  ✓ {decoy_path}")
    else:
        print("  ⊗ Skipped: decoy.png (already exists)")
    
    print("\nGenerating SHIP placeholders for background battles...")
    # Generate generic faction ships
    factions_for_ships = [
        (FACTION_TAURI, "Tau'ri"),
        (FACTION_GOAULD, "Goa'uld"),
        (FACTION_JAFFA, "Jaffa Rebellion"),
        (FACTION_LUCIAN, "Lucian Alliance"),
        (FACTION_ASGARD, "Asgard"),
    ]
    
    for faction_id, faction_name in factions_for_ships:
        # Create generic faction ship
        ship_surface = create_ship_placeholder(faction_name, "generic")
        ship_path = os.path.join(ships_dir, f"{faction_id.lower().replace(' ', '_')}_ship.png")
        if should_create_file(ship_path):
            pygame.image.save(ship_surface, ship_path)
            print(f"  - {ship_path}")
        
        # Skip creating light/heavy variants; only the base faction ship is generated
    
    print("\nGenerating leader portraits...")
    # Leader IDs for each faction (base + ALL unlockable)
    leaders = {faction: list(ids) for faction, ids in ALL_LEADER_IDS_BY_FACTION.items()}
    
    # Leader names for backgrounds
    leader_names = {card_id: get_leader_banner_name(card_id) for card_ids in leaders.values() for card_id in card_ids}
    
    for faction, leader_ids in leaders.items():
        for leader_id in leader_ids:
            path = create_leader_portrait(leader_id, faction)
            if path:
                print(f"  ✓ {path}")
            else:
                print(f"  ⊗ Skipped: {leader_id}_leader.png (already exists)")
    
    print("\nGenerating leader selection backgrounds...")
    for faction, leader_ids in leaders.items():
        for leader_id in leader_ids:
            leader_name = leader_names.get(leader_id, leader_id)
            path = create_leader_background(leader_name, faction, leader_id)
            if path:
                print(f"  ✓ {path}")
            else:
                alias_id = LEADER_BACKGROUND_ALIASES.get(leader_id, leader_id)
                print(f"  ⊗ Skipped: leader_bg_{alias_id}.png (already exists)")

    print("\nGenerating faction selection backgrounds...")
    for faction, asset_id in FACTION_BACKGROUND_IDS.items():
        canonical_faction = resolve_faction_name(faction)
        base_color = FACTION_COLORS.get(canonical_faction, (80, 80, 80))
        path = create_faction_background(asset_id, faction, base_color)
        if path:
            print(f"  ✓ faction_bg_{asset_id}.png")
        else:
            print(f"  ⊗ Skipped: faction_bg_{asset_id}.png (already exists)")
    
    print("\nGenerating other assets...")
    create_board_image()
    create_menu_background()
    create_rule_menu_background()
    create_deck_building_background()
    create_stats_menu_background()
    create_draft_mode_background()
    create_custom_font()
    create_card_back_image()
    create_universal_matchup_background()
    create_lobby_background()
    
    # Calculate totals
    base_cards = len(ALL_CARDS)
    unlockable_cards = len(UNLOCKABLE_CARDS)
    num_leaders = sum(len(l) for l in leaders.values())
    num_ships = len(factions_for_ships)  # One ship per faction
    num_faction_bgs = len(FACTION_BACKGROUND_IDS)
    num_other = 9  # board, menu, rule menu, deck bg, stats bg, draft bg, card back, universal matchup bg, lobby bg
    # Leader backgrounds match leaders count
    leader_backgrounds = num_leaders
    
    total_images = base_cards + unlockable_cards + num_leaders + leader_backgrounds + num_ships + num_faction_bgs + num_other
    
    print("\nAsset generation complete.")
    print(f"  Base Cards: {base_cards}")
    print(f"  Unlockable Cards: {unlockable_cards}")
    print(f"  Leader Portraits: {num_leaders}")
    print(f"  Leader Backgrounds: {leader_backgrounds}")
    print(f"  Universal Matchup Backgrounds: 1 (dynamic overlay handles text/names)")
    print(f"  Ships: {num_ships} (1 per faction)")
    print(f"  Faction Backgrounds: {num_faction_bgs}")
    print(f"  Other: {num_other} (board, menu, rule menu, deck bg, stats bg, draft bg, card back, universal matchup bg, lobby bg) + 1 font config")
    print(f"  Total Images: {total_images}")


def create_stats_menu_background():
    """Create background for stats menu with data visualization aesthetic."""
    path = os.path.join(ASSETS_DIR, "stats_menu_bg.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: stats_menu_bg.png (already exists)")
        return None

    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

    # Dark blue-grey gradient background (professional data look)
    for y in range(BOARD_HEIGHT):
        progress = y / BOARD_HEIGHT
        r = int(15 + progress * 15)
        g = int(20 + progress * 20)
        b = int(35 + progress * 30)
        pygame.draw.line(surface, (r, g, b), (0, y), (BOARD_WIDTH, y))

    # Subtle starfield (less dense for readability)
    for _ in range(300):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(1, 2)
        brightness = random.randint(80, 160)
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)

    # Data grid pattern (subtle)
    grid_color = (40, 60, 90)
    grid_spacing = 80
    for x in range(0, BOARD_WIDTH, grid_spacing):
        pygame.draw.line(surface, grid_color, (x, 0), (x, BOARD_HEIGHT), 1)
    for y in range(0, BOARD_HEIGHT, grid_spacing):
        pygame.draw.line(surface, grid_color, (0, y), (BOARD_WIDTH, y), 1)

    # Holographic data panels (corner accents)
    panel_color = (60, 100, 160, 100)
    corner_size = 400

    # Top-left data panel
    panel_surf = pygame.Surface((corner_size, corner_size), pygame.SRCALPHA)
    pygame.draw.rect(panel_surf, panel_color, (0, 0, corner_size, corner_size), border_radius=20)
    pygame.draw.rect(panel_surf, (100, 160, 220, 80), (0, 0, corner_size, corner_size), width=3, border_radius=20)
    surface.blit(panel_surf, (50, 50))

    # Bottom-right data panel
    panel_surf = pygame.Surface((corner_size, corner_size), pygame.SRCALPHA)
    pygame.draw.rect(panel_surf, panel_color, (0, 0, corner_size, corner_size), border_radius=20)
    pygame.draw.rect(panel_surf, (100, 160, 220, 80), (0, 0, corner_size, corner_size), width=3, border_radius=20)
    surface.blit(panel_surf, (BOARD_WIDTH - corner_size - 50, BOARD_HEIGHT - corner_size - 50))

    # Chart-like decorations (bar graph silhouette)
    chart_x = 150
    chart_y = BOARD_HEIGHT - 300
    bar_width = 40
    for i in range(10):
        bar_height = random.randint(50, 200)
        bar_color = (50, 120, 180, 60)
        pygame.draw.rect(surface, bar_color, (chart_x + i * (bar_width + 10), chart_y - bar_height, bar_width, bar_height), border_radius=5)

    # Circular stat wheels (top-right)
    wheel_center = (BOARD_WIDTH - 300, 300)
    for radius in range(150, 50, -30):
        alpha = 40 + (150 - radius) // 2
        pygame.draw.circle(surface, (60, 140, 200, alpha), wheel_center, radius, 3)

    # Line graph silhouette (center-right)
    graph_points = []
    graph_x_start = BOARD_WIDTH - 600
    graph_y_base = BOARD_HEIGHT // 2
    for i in range(8):
        x = graph_x_start + i * 70
        y = graph_y_base + random.randint(-100, 100)
        graph_points.append((x, y))

    if len(graph_points) > 1:
        pygame.draw.lines(surface, (80, 160, 220, 100), False, graph_points, 4)
        for point in graph_points:
            pygame.draw.circle(surface, (100, 180, 240), point, 8)
            pygame.draw.circle(surface, (60, 140, 200), point, 6)

    # "STATISTICS" title watermark (very faint)
    title_font = pygame.font.SysFont("Arial", 180, bold=True)
    title_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    title_text = title_font.render("STATISTICS", True, (60, 100, 160, 30))
    title_rect = title_text.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT // 2))
    title_surf.blit(title_text, title_rect)
    surface.blit(title_surf, (0, 0))

    pygame.image.save(surface, path)
    print(f"  ✓ {path}")
    return path


def create_draft_mode_background():
    """Create background for Draft Mode (Arena) with card-picking aesthetic."""
    path = os.path.join(ASSETS_DIR, "draft_mode_bg.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: draft_mode_bg.png (already exists)")
        return None

    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

    # Deep space with purple/blue nebula theme (mysterious, exciting)
    for y in range(BOARD_HEIGHT):
        progress = y / BOARD_HEIGHT
        r = int(25 + progress * 30)
        g = int(15 + progress * 25)
        b = int(45 + progress * 60)
        pygame.draw.line(surface, (r, g, b), (0, y), (BOARD_WIDTH, y))

    # Dense starfield for excitement
    for _ in range(800):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.choice([1, 1, 2, 3])
        brightness = random.randint(100, 255)
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)

    # Nebula clouds (purple and blue)
    for _ in range(15):
        x = random.randint(-400, BOARD_WIDTH + 400)
        y = random.randint(-400, BOARD_HEIGHT + 400)
        size = random.randint(300, 700)
        nebula_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)

        color_choice = random.choice([
            (150, 50, 200, 40),   # Purple nebula
            (50, 100, 200, 40),   # Blue nebula
            (200, 50, 150, 40),   # Pink nebula
        ])
        pygame.draw.circle(nebula_surf, color_choice, (size, size), size)
        surface.blit(nebula_surf, (x - size, y - size))

    # Card silhouettes floating in background (draft theme)
    card_silhouette_color = (80, 60, 140, 60)
    for i in range(12):
        x = random.randint(100, BOARD_WIDTH - 100)
        y = random.randint(100, BOARD_HEIGHT - 100)
        rotation = random.randint(-30, 30)

        # Create rotated card shape
        card_surf = pygame.Surface((250, 350), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, card_silhouette_color, (0, 0, 250, 350), border_radius=15)
        pygame.draw.rect(card_surf, (120, 100, 180, 80), (0, 0, 250, 350), width=3, border_radius=15)

        # Rotate and blit
        rotated = pygame.transform.rotate(card_surf, rotation)
        rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rect)

    # "DRAFT MODE" title watermark (center, very faint)
    title_font = pygame.font.SysFont("Arial", 200, bold=True)
    title_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    title_text = title_font.render("DRAFT MODE", True, (100, 80, 180, 25))
    title_rect = title_text.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT // 2))
    title_surf.blit(title_text, title_rect)
    surface.blit(title_surf, (0, 0))

    # Glowing particles (excitement effect)
    for _ in range(50):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(5, 15)

        # Multi-layer glow
        glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        for r in range(size * 2, 0, -3):
            alpha = int(100 * (r / (size * 2)))
            color = random.choice([
                (180, 100, 255, alpha),  # Purple glow
                (100, 180, 255, alpha),  # Blue glow
            ])
            pygame.draw.circle(glow_surf, color, (size * 2, size * 2), r)
        surface.blit(glow_surf, (x - size * 2, y - size * 2))

    # Spotlight effect from top (dramatic)
    spotlight = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    for i in range(600, 0, -20):
        alpha = max(0, 60 - (600 - i) // 10)
        pygame.draw.circle(spotlight, (100, 150, 255, alpha), (BOARD_WIDTH // 2, -200), i)
    surface.blit(spotlight, (0, 0))

    pygame.image.save(surface, path)
    print(f"  ✓ {path}")
    return path


def create_lobby_background():
    """Create LAN multiplayer lobby background with Stargate tech aesthetic."""
    path = os.path.join(ASSETS_DIR, "lobby_background.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: lobby_background.png (already exists)")
        return None

    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

    # Dark blue gradient background
    for y in range(BOARD_HEIGHT):
        progress = y / BOARD_HEIGHT
        r = int(10 + progress * 20)
        g = int(15 + progress * 30)
        b = int(40 + progress * 60)
        pygame.draw.line(surface, (r, g, b), (0, y), (BOARD_WIDTH, y))

    # Add starfield
    for _ in range(500):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(1, 3)
        brightness = random.randint(100, 255)
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)

    # Add larger glowing stars
    for _ in range(50):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(4, 12)
        brightness = random.randint(150, 255)
        # Glow effect (multiple circles with decreasing alpha)
        for radius in range(size, 0, -2):
            alpha_factor = radius / size
            r = min(255, int(brightness * alpha_factor))
            g = min(255, int(brightness * alpha_factor))
            b = min(255, int((brightness + 50) * alpha_factor))
            pygame.draw.circle(surface, (r, g, b), (x, y), radius)

    # Add tech grid pattern (subtle)
    grid_color_main = (30, 60, 120)
    grid_color_dim = (15, 30, 60)
    grid_spacing = 100

    # Vertical lines
    for x in range(0, BOARD_WIDTH, grid_spacing):
        if x % 300 == 0:
            pygame.draw.line(surface, grid_color_main, (x, 0), (x, BOARD_HEIGHT), 2)
        else:
            pygame.draw.line(surface, grid_color_dim, (x, 0), (x, BOARD_HEIGHT), 1)

    # Horizontal lines
    for y in range(0, BOARD_HEIGHT, grid_spacing):
        if y % 300 == 0:
            pygame.draw.line(surface, grid_color_main, (0, y), (BOARD_WIDTH, y), 2)
        else:
            pygame.draw.line(surface, grid_color_dim, (0, y), (BOARD_WIDTH, y), 1)

    # Add circuit-like connections
    for _ in range(30):
        x1 = random.randint(0, BOARD_WIDTH)
        y1 = random.randint(0, BOARD_HEIGHT)
        current_x, current_y = x1, y1

        # Draw a path with right angles (circuit-like)
        for _ in range(random.randint(2, 5)):
            prev_x, prev_y = current_x, current_y

            if random.random() > 0.5:
                # Horizontal
                current_x += random.randint(-300, 300)
                current_x = max(0, min(BOARD_WIDTH, current_x))
            else:
                # Vertical
                current_y += random.randint(-300, 300)
                current_y = max(0, min(BOARD_HEIGHT, current_y))

            # Draw line
            pygame.draw.line(surface, (40, 100, 150), (prev_x, prev_y), (current_x, current_y), 2)

            # Add node at connection
            pygame.draw.circle(surface, (60, 140, 200), (prev_x, prev_y), 4)
            pygame.draw.circle(surface, (100, 180, 240), (prev_x, prev_y), 6, 1)

    # Add Stargate chevron symbols (simplified circles with glyphs)
    num_chevrons = 7
    center_x = BOARD_WIDTH // 2
    center_y = BOARD_HEIGHT // 2
    radius = min(BOARD_WIDTH, BOARD_HEIGHT) // 3

    for i in range(num_chevrons):
        angle = (i * 2 * math.pi / num_chevrons) - math.pi / 2
        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))

        # Outer glow
        for r in range(50, 0, -5):
            alpha_factor = r / 50
            cr = min(255, int(140 * alpha_factor))
            cg = min(255, int(200 * alpha_factor))
            cb = min(255, int(230 * alpha_factor))
            pygame.draw.circle(surface, (cr, cg, cb), (x, y), r)

        # Main chevron circle
        pygame.draw.circle(surface, (60, 140, 220), (x, y), 30)
        pygame.draw.circle(surface, (20, 60, 100), (x, y), 25)
        pygame.draw.circle(surface, (80, 160, 240), (x, y), 20)

        # Inner detail
        pygame.draw.circle(surface, (40, 100, 180), (x, y), 15)
        pygame.draw.circle(surface, (100, 180, 255), (x, y), 8)

    # Add center Stargate ring (subtle)
    ring_radius = min(BOARD_WIDTH, BOARD_HEIGHT) // 4
    for thickness in range(20, 0, -2):
        alpha_factor = thickness / 20
        cr = min(255, int(30 + 80 * alpha_factor))
        cg = min(255, int(80 + 80 * alpha_factor))
        cb = min(255, int(150 + 80 * alpha_factor))
        pygame.draw.circle(surface, (cr, cg, cb), (center_x, center_y), ring_radius, 2)
        ring_radius -= 3

    pygame.image.save(surface, path)
    print(f"  ✓ {path}")
    return path

def create_universal_matchup_background():
    """Create a single cinematic Stargate matchup background used by all leader pairs."""
    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    
    # Deep space gradient
    for y in range(BOARD_HEIGHT):
        t = y / BOARD_HEIGHT
        color = (
            10 + int(15 * t),
            15 + int(35 * t),
            35 + int(85 * t),
        )
        pygame.draw.line(surface, color, (0, y), (BOARD_WIDTH, y))
    
    # Add subtle diagonal scanlines for retro vibe
    overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    for x in range(0, BOARD_WIDTH, 12):
        pygame.draw.line(overlay, (0, 255, 200, 18), (x, 0), (0, x), 1)
        pygame.draw.line(overlay, (0, 120, 255, 12), (BOARD_WIDTH - x, 0), (BOARD_WIDTH, x), 1)
    surface.blit(overlay, (0, 0))
    
    # Stargate ring impression in center
    gate_surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    center = (BOARD_WIDTH // 2, BOARD_HEIGHT // 2)
    gate_radius = min(BOARD_WIDTH, BOARD_HEIGHT) // 3
    pygame.draw.circle(gate_surface, (80, 120, 160, 160), center, gate_radius, 6)
    pygame.draw.circle(gate_surface, (40, 70, 110, 120), center, gate_radius - 20, 4)
    
    # Chevron markers
    for i in range(9):
        angle = (i / 9) * 2 * math.pi
        outer = (
            center[0] + int(math.cos(angle) * (gate_radius + 20)),
            center[1] + int(math.sin(angle) * (gate_radius + 20)),
        )
        inner = (
            center[0] + int(math.cos(angle) * (gate_radius - 40)),
            center[1] + int(math.sin(angle) * (gate_radius - 40)),
        )
        pygame.draw.line(gate_surface, (120, 200, 255, 180), inner, outer, 4)
    surface.blit(gate_surface, (0, 0))
    
    # Event horizon bloom
    horizon = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    for radius in range(gate_radius - 100, gate_radius + 40, 12):
        alpha = max(0, 180 - (gate_radius + 40 - radius) * 2)
        pygame.draw.circle(horizon, (30, 180, 255, alpha), center, radius, 2)
    surface.blit(horizon, (0, 0))
    
    # Focal glow at center for collision effect alignment
    glow = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow, (0, 200, 255, 60), center, 220)
    pygame.draw.circle(glow, (255, 255, 255, 80), center, 140)
    surface.blit(glow, (0, 0))
    
    # Save file if needed
    path = os.path.join(ASSETS_DIR, "universal_leader_matchup_bg.png")
    if should_create_file(path):
        pygame.image.save(surface, path)
        print(f"  Created universal matchup background: {path}")
        return path
    return None

if __name__ == "__main__":
    main()
