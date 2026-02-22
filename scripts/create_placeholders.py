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

def create_oneill_clone_token():
    """Creates the specific token for Jack O'Neill's clone ability."""
    from cards import Card
    # Temporary card object for generation
    clone_card = Card(
        "tauri_oneill_clone", 
        "Jack O'Neill Clone", 
        FACTION_TAURI, 
        6, 
        "close", 
        "Temporary Clone"
    )
    
    # Use standard card generation
    path = create_card_image(clone_card)
    if path:
        print(f"  ✓ {path} [TOKEN]")
    else:
        print(f"  ⊗ Skipped: tauri_oneill_clone.png (already exists)")

def create_tab_icon(filename, label, color):
    """Creates a placeholder icon for deck builder tabs."""
    size = 256
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    
    # Background circle
    pygame.draw.circle(surface, color, (size // 2, size // 2), size // 2 - 10)
    pygame.draw.circle(surface, WHITE, (size // 2, size // 2), size // 2 - 10, width=5)
    
    # Text label (first 1-3 letters)
    font = pygame.font.SysFont("Arial", 80, bold=True)
    text = font.render(label[:3].upper(), True, WHITE)
    rect = text.get_rect(center=(size // 2, size // 2))
    surface.blit(text, rect)
    
    icon_path = os.path.join(ASSETS_DIR, "icons", filename)
    if should_create_file(icon_path):
        pygame.image.save(surface, icon_path)
        return icon_path
    return None

def main():
    """Generates all placeholder assets."""
    if not os.path.exists(ASSETS_DIR):
        os.makedirs(ASSETS_DIR)
    
    # Create icons folder
    icons_dir = os.path.join(ASSETS_DIR, "icons")
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
    
    # Create ships folder
    ships_dir = os.path.join(ASSETS_DIR, "ships")
    if not os.path.exists(ships_dir):
        os.makedirs(ships_dir)
    
    print("Generating tab icons...")
    tab_icons = [
        ("all.png", "ALL", (100, 100, 100)),
        ("close.png", "CLS", (200, 50, 50)),
        ("ranged.png", "RNG", (50, 150, 200)),
        ("siege.png", "SGE", (200, 150, 50)),
        ("agile.png", "AGL", (100, 200, 100)),
        ("weather.png", "WTH", (100, 100, 150)),
        ("Legendary commander.png", "LEG", (255, 215, 0)),
        ("neutral.png", "NTR", (150, 150, 150)),
        ("special.png", "SPC", (180, 100, 200)),
    ]
    for filename, label, color in tab_icons:
        path = create_tab_icon(filename, label, color)
        if path:
            print(f"  ✓ {path}")
        else:
            print(f"  ⊗ Skipped: icons/{filename} (already exists)")

    print("\nGenerating card images...")
    for card_id, card in ALL_CARDS.items():
        path = create_card_image(card)
        if path:
            print(f"  ✓ {path}")
        else:
            print(f"  ⊗ Skipped: {card_id}.png (already exists)")
            
    # Generate O'Neill Clone Token
    create_oneill_clone_token()
    
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
    create_options_menu_background()
    create_draft_mode_background()
    create_mulligan_background()
    create_custom_font()
    create_card_back_image()
    create_universal_matchup_background()
    create_lobby_background()
    create_conquest_background()
    create_conquest_menu_background()
    create_conquest_deck_building_background()

    # Calculate totals
    base_cards = len(ALL_CARDS)
    unlockable_cards = len(UNLOCKABLE_CARDS)
    num_leaders = sum(len(l) for l in leaders.values())
    num_ships = len(factions_for_ships)  # One ship per faction
    num_faction_bgs = len(FACTION_BACKGROUND_IDS)
    num_other = 12  # board, menu, rule menu, deck bg, stats bg, options bg, draft bg, mulligan bg, card back, universal matchup bg, lobby bg, conquest bg
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
    print(f"  Other: {num_other} (board, menu, rule menu, deck bg, stats bg, options bg, draft bg, mulligan bg, card back, universal matchup bg, lobby bg, conquest bg) + 1 font config")
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


def create_options_menu_background():
    """Create background for Options menu with Stargate control room aesthetic."""
    path = os.path.join(ASSETS_DIR, "options_menu_bg.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: options_menu_bg.png (already exists)")
        return None

    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

    # Dark blue-grey gradient (control room lighting)
    for y in range(BOARD_HEIGHT):
        progress = y / BOARD_HEIGHT
        r = int(10 + progress * 15)
        g = int(15 + progress * 25)
        b = int(30 + progress * 40)
        pygame.draw.line(surface, (r, g, b), (0, y), (BOARD_WIDTH, y))

    # Subtle starfield through windows
    for _ in range(400):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(1, 2)
        brightness = random.randint(60, 140)
        pygame.draw.circle(surface, (brightness, brightness, brightness + 20), (x, y), size)

    # Central Stargate (large, prominent)
    gate_center = (BOARD_WIDTH // 2, BOARD_HEIGHT // 2)
    gate_radius = 450
    
    # Outer ring (dark metal)
    pygame.draw.circle(surface, (50, 55, 65), gate_center, gate_radius, 40)
    pygame.draw.circle(surface, (70, 80, 95), gate_center, gate_radius - 5, 3)
    pygame.draw.circle(surface, (40, 45, 55), gate_center, gate_radius - 35, 3)
    
    # Chevrons (9 chevrons around the gate)
    for i in range(9):
        angle = (i / 9) * 2 * math.pi - math.pi / 2  # Start from top
        chev_x = gate_center[0] + int(math.cos(angle) * (gate_radius - 20))
        chev_y = gate_center[1] + int(math.sin(angle) * (gate_radius - 20))
        
        # Orange lit chevron
        pygame.draw.circle(surface, (200, 100, 30), (chev_x, chev_y), 25)
        pygame.draw.circle(surface, (255, 150, 50), (chev_x, chev_y), 18)
        pygame.draw.circle(surface, (255, 200, 100), (chev_x, chev_y), 10)
    
    # Event horizon (blue watery effect)
    horizon_radius = gate_radius - 50
    horizon_surf = pygame.Surface((horizon_radius * 2, horizon_radius * 2), pygame.SRCALPHA)
    
    # Layered circles for depth
    for r in range(horizon_radius, 0, -30):
        alpha = int(60 + (horizon_radius - r) * 0.3)
        blue_val = min(255, 150 + (horizon_radius - r) // 3)
        pygame.draw.circle(horizon_surf, (30, 80, blue_val, alpha), 
                          (horizon_radius, horizon_radius), r)
    
    # Ripple rings
    for r in range(50, horizon_radius, 60):
        pygame.draw.circle(horizon_surf, (100, 180, 255, 40), 
                          (horizon_radius, horizon_radius), r, 3)
    
    surface.blit(horizon_surf, (gate_center[0] - horizon_radius, gate_center[1] - horizon_radius))
    
    # Control panels on sides (left and right)
    panel_width = 300
    panel_height = 600
    panel_color = (30, 40, 55, 180)
    
    # Left control panel
    left_panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(left_panel, panel_color, (0, 0, panel_width, panel_height), border_radius=15)
    pygame.draw.rect(left_panel, (60, 100, 150, 150), (0, 0, panel_width, panel_height), width=3, border_radius=15)
    
    # Add indicator lights
    for i in range(5):
        light_y = 80 + i * 100
        light_color = random.choice([(80, 200, 100), (200, 150, 50), (100, 150, 220)])
        pygame.draw.circle(left_panel, light_color, (panel_width - 40, light_y), 12)
        pygame.draw.circle(left_panel, (255, 255, 255), (panel_width - 40, light_y), 6)
        # Label bar
        pygame.draw.rect(left_panel, (40, 60, 80), (30, light_y - 8, 180, 16), border_radius=4)
    
    surface.blit(left_panel, (80, BOARD_HEIGHT // 2 - panel_height // 2))
    
    # Right control panel
    right_panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    pygame.draw.rect(right_panel, panel_color, (0, 0, panel_width, panel_height), border_radius=15)
    pygame.draw.rect(right_panel, (60, 100, 150, 150), (0, 0, panel_width, panel_height), width=3, border_radius=15)
    
    # Add slider tracks (representing settings)
    for i in range(4):
        slider_y = 100 + i * 120
        # Track
        pygame.draw.rect(right_panel, (50, 70, 90), (40, slider_y, 220, 12), border_radius=6)
        # Filled portion
        fill_width = random.randint(80, 200)
        pygame.draw.rect(right_panel, (80, 160, 220), (40, slider_y, fill_width, 12), border_radius=6)
        # Handle
        pygame.draw.circle(right_panel, (200, 220, 255), (40 + fill_width, slider_y + 6), 14)
        pygame.draw.circle(right_panel, (100, 180, 255), (40 + fill_width, slider_y + 6), 10)
    
    surface.blit(right_panel, (BOARD_WIDTH - panel_width - 80, BOARD_HEIGHT // 2 - panel_height // 2))
    
    # "OPTIONS" title watermark (very faint)
    title_font = pygame.font.SysFont("Arial", 200, bold=True)
    title_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    title_text = title_font.render("OPTIONS", True, (60, 100, 160, 25))
    title_rect = title_text.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT - 200))
    title_surf.blit(title_text, title_rect)
    surface.blit(title_surf, (0, 0))
    
    # Top decorative bar (like SGC control room)
    top_bar = pygame.Surface((BOARD_WIDTH, 80), pygame.SRCALPHA)
    pygame.draw.rect(top_bar, (25, 35, 50, 200), (0, 0, BOARD_WIDTH, 80))
    pygame.draw.line(top_bar, (80, 140, 200, 150), (0, 79), (BOARD_WIDTH, 79), 2)
    surface.blit(top_bar, (0, 0))
    
    # Bottom decorative bar
    bottom_bar = pygame.Surface((BOARD_WIDTH, 60), pygame.SRCALPHA)
    pygame.draw.rect(bottom_bar, (25, 35, 50, 200), (0, 0, BOARD_WIDTH, 60))
    pygame.draw.line(bottom_bar, (80, 140, 200, 150), (0, 0), (BOARD_WIDTH, 0), 2)
    surface.blit(bottom_bar, (0, BOARD_HEIGHT - 60))

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

def create_mulligan_background():
    """Create background for the mulligan (card redraw) phase."""
    path = os.path.join(ASSETS_DIR, "mulligan_bg.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: mulligan_bg.png (already exists)")
        return None

    surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))

    # Deep blue-purple gradient (mysterious, transitional feel)
    for y in range(BOARD_HEIGHT):
        progress = y / BOARD_HEIGHT
        r = int(15 + progress * 20)
        g = int(20 + progress * 25)
        b = int(50 + progress * 40)
        pygame.draw.line(surface, (r, g, b), (0, y), (BOARD_WIDTH, y))

    # Starfield background
    for _ in range(600):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        size = random.randint(1, 3)
        brightness = random.randint(80, 200)
        pygame.draw.circle(surface, (brightness, brightness, brightness), (x, y), size)

    # Subtle nebula clouds
    for _ in range(8):
        x = random.randint(-200, BOARD_WIDTH + 200)
        y = random.randint(-200, BOARD_HEIGHT + 200)
        size = random.randint(300, 600)
        nebula_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        color_choice = random.choice([
            (80, 60, 150, 35),   # Purple nebula
            (60, 100, 180, 35),  # Blue nebula
            (100, 80, 160, 35),  # Violet nebula
        ])
        pygame.draw.circle(nebula_surf, color_choice, (size, size), size)
        surface.blit(nebula_surf, (x - size, y - size))

    # Central focus area (where cards will be shown)
    center_x, center_y = BOARD_WIDTH // 2, BOARD_HEIGHT // 2

    # Glowing ring effect around center area
    ring_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    for radius in range(500, 300, -20):
        alpha = max(0, 50 - (500 - radius) // 5)
        pygame.draw.circle(ring_surf, (100, 150, 220, alpha), (center_x, center_y), radius, 3)
    surface.blit(ring_surf, (0, 0))

    # Horizontal divider line (subtle)
    pygame.draw.line(surface, (60, 100, 160, 100), (200, center_y - 200), (BOARD_WIDTH - 200, center_y - 200), 2)

    # Corner decorations (tech/ancient feel)
    corner_size = 150
    corner_color = (80, 130, 200)

    # Top-left
    pygame.draw.line(surface, corner_color, (50, 50), (50 + corner_size, 50), 3)
    pygame.draw.line(surface, corner_color, (50, 50), (50, 50 + corner_size), 3)
    pygame.draw.circle(surface, corner_color, (50, 50), 8)

    # Top-right
    pygame.draw.line(surface, corner_color, (BOARD_WIDTH - 50, 50), (BOARD_WIDTH - 50 - corner_size, 50), 3)
    pygame.draw.line(surface, corner_color, (BOARD_WIDTH - 50, 50), (BOARD_WIDTH - 50, 50 + corner_size), 3)
    pygame.draw.circle(surface, corner_color, (BOARD_WIDTH - 50, 50), 8)

    # Bottom-left
    pygame.draw.line(surface, corner_color, (50, BOARD_HEIGHT - 50), (50 + corner_size, BOARD_HEIGHT - 50), 3)
    pygame.draw.line(surface, corner_color, (50, BOARD_HEIGHT - 50), (50, BOARD_HEIGHT - 50 - corner_size), 3)
    pygame.draw.circle(surface, corner_color, (50, BOARD_HEIGHT - 50), 8)

    # Bottom-right
    pygame.draw.line(surface, corner_color, (BOARD_WIDTH - 50, BOARD_HEIGHT - 50), (BOARD_WIDTH - 50 - corner_size, BOARD_HEIGHT - 50), 3)
    pygame.draw.line(surface, corner_color, (BOARD_WIDTH - 50, BOARD_HEIGHT - 50), (BOARD_WIDTH - 50, BOARD_HEIGHT - 50 - corner_size), 3)
    pygame.draw.circle(surface, corner_color, (BOARD_WIDTH - 50, BOARD_HEIGHT - 50), 8)

    # "MULLIGAN" watermark (very faint)
    title_font = pygame.font.SysFont("Arial", 180, bold=True)
    title_surf = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    title_text = title_font.render("REDRAW PHASE", True, (80, 120, 180, 20))
    title_rect = title_text.get_rect(center=(center_x, center_y - 350))
    title_surf.blit(title_text, title_rect)
    surface.blit(title_surf, (0, 0))

    # Floating card silhouettes in background
    card_color = (60, 90, 140, 40)
    for i in range(6):
        x = random.randint(100, BOARD_WIDTH - 100)
        y = random.randint(BOARD_HEIGHT // 2 + 100, BOARD_HEIGHT - 200)
        rotation = random.randint(-15, 15)

        card_surf = pygame.Surface((180, 260), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, card_color, (0, 0, 180, 260), border_radius=12)
        pygame.draw.rect(card_surf, (100, 140, 200, 60), (0, 0, 180, 260), width=2, border_radius=12)

        rotated = pygame.transform.rotate(card_surf, rotation)
        rect = rotated.get_rect(center=(x, y))
        surface.blit(rotated, rect)

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

def create_conquest_background():
    """Create a 4K Milky Way galaxy background for Galactic Conquest mode.

    Matches the Stargate galaxy map reference: spiral galaxy with cyan diamond
    planet markers for every canon Stargate world, faction territory boundaries,
    territory labels, and subtle navigation grid.
    """
    path = os.path.join(ASSETS_DIR, "conquest.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: conquest.png (already exists)")
        return None

    W, H = BOARD_WIDTH, BOARD_HEIGHT
    surface = pygame.Surface((W, H))
    cx, cy = W // 2, H // 2
    max_r = math.sqrt(cx**2 + cy**2)

    # --- Deep space base with radial gradient (golden core → dark edges) ---
    for y in range(0, H, 2):
        for x in range(0, W, 4):
            dx, dy = x - cx, y - cy
            t = min(1.0, math.sqrt(dx*dx + dy*dy) / max_r)
            r = int(45 * (1 - t) + 4 * t)
            g = int(38 * (1 - t) + 6 * t)
            b = int(22 * (1 - t) + 18 * t)
            pygame.draw.rect(surface, (r, g, b), (x, y, 4, 2))

    # --- Spiral arms (2 main arms: blue + red/pink nebulae) ---
    arm_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    arm_configs = [
        (0,        (50, 70, 180, 30)),   # Blue arm
        (math.pi,  (160, 45, 55, 25)),   # Red arm
        (math.pi/2, (80, 40, 120, 15)),  # Faint purple arm
        (3*math.pi/2, (40, 80, 130, 15)), # Faint blue-green arm
    ]
    for base_angle, arm_color in arm_configs:
        for i in range(800):
            t = i / 800.0
            radius = 80 + t * (min(W, H) * 0.45)
            angle = base_angle + t * 5.0
            spread = 50 + t * 150
            for _ in range(4):
                offset = random.gauss(0, spread)
                a_off = offset / max(radius, 1)
                ax = cx + int(math.cos(angle + a_off) * radius)
                ay = cy + int(math.sin(angle + a_off) * radius)
                if 0 <= ax < W and 0 <= ay < H:
                    size = random.randint(2, 9)
                    pygame.draw.circle(arm_surf, arm_color, (ax, ay), size)
    surface.blit(arm_surf, (0, 0))

    # --- Galactic core glow (warm golden/white) ---
    core_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for r in range(280, 0, -4):
        frac = 1 - r / 280
        alpha = max(0, min(255, int(180 * frac)))
        warmth = min(255, 160 + int(95 * frac))
        pygame.draw.circle(core_surf, (warmth, max(0, warmth - 50), max(0, warmth - 110), alpha),
                           (cx, cy), r)
    surface.blit(core_surf, (0, 0))

    # --- Dense starfield (2000 stars, brighter near core) ---
    for _ in range(2000):
        sx, sy = random.randint(0, W), random.randint(0, H)
        dist = math.sqrt((sx - cx)**2 + (sy - cy)**2)
        core_f = max(0.25, 1 - dist / max_r)
        bright = random.randint(int(60 * core_f), int(255 * core_f))
        size = random.choice([1, 1, 1, 2, 2, 3])
        pygame.draw.circle(surface, (bright, bright, min(255, bright + 15)), (sx, sy), size)

    # Larger glowing stars
    for _ in range(80):
        sx, sy = random.randint(0, W), random.randint(0, H)
        size = random.randint(3, 8)
        bright = random.randint(160, 255)
        for r in range(size, 0, -1):
            a = int(bright * r / size)
            pygame.draw.circle(surface, (a, a, min(255, a + 25)), (sx, sy), r)

    # ===================================================================
    # STARGATE CANON PLANET MARKERS
    # Each planet: (name, x_fraction, y_fraction, faction_color)
    # Positions match the Stargate galaxy map reference layout.
    # ===================================================================
    CYAN = (100, 220, 255)
    TAURI_COL  = (50, 130, 220)    # Blue — Tau'ri
    GOAULD_COL = (210, 55, 55)     # Red — Goa'uld
    JAFFA_COL  = (210, 190, 55)    # Gold — Jaffa Rebellion
    LUCIAN_COL = (210, 85, 185)    # Magenta — Lucian Alliance
    ASGARD_COL = (100, 190, 230)   # Light blue — Asgard
    NEUTRAL_COL = (150, 150, 160)  # Grey — Neutral / Uncharted

    PLANETS = [
        # --- TAU'RI TERRITORY (bottom/south) ---
        ("EARTH",           0.48, 0.76, TAURI_COL),
        ("ABYDOS",          0.48, 0.71, TAURI_COL),
        ("ANTARCTICA",      0.42, 0.78, TAURI_COL),
        ("TOLLANA",         0.85, 0.08, TAURI_COL),
        ("ALPHA SITE",      0.40, 0.72, TAURI_COL),
        ("CAMELOT",         0.38, 0.67, TAURI_COL),
        ("MADRONA",         0.47, 0.66, TAURI_COL),
        ("LAND OF LIGHT",   0.48, 0.53, TAURI_COL),
        ("LATONA",          0.52, 0.60, TAURI_COL),
        ("KATANA",          0.56, 0.53, TAURI_COL),
        # --- GOA'ULD TERRITORY (center/center-right) ---
        ("TARTARUS",        0.58, 0.38, GOAULD_COL),
        ("NETU",            0.55, 0.42, GOAULD_COL),
        ("HASARA",          0.34, 0.36, GOAULD_COL),
        ("DELMAK",          0.60, 0.34, GOAULD_COL),
        ("EREBUS",          0.44, 0.38, GOAULD_COL),
        ("HADANTE",         0.60, 0.42, GOAULD_COL),
        ("JEBANI",          0.54, 0.35, GOAULD_COL),
        ("SOKAR'S DOMAIN",  0.52, 0.40, GOAULD_COL),
        ("AMON SHEK",       0.50, 0.28, GOAULD_COL),
        ("CERADOR",         0.50, 0.32, GOAULD_COL),
        # --- JAFFA REBELLION (center-left) ---
        ("CHULAK",          0.43, 0.43, JAFFA_COL),
        ("DAKARA",          0.38, 0.40, JAFFA_COL),
        ("HAK'TYL",         0.35, 0.44, JAFFA_COL),
        ("GORONAK",         0.42, 0.30, JAFFA_COL),
        ("K'TAU",           0.28, 0.31, JAFFA_COL),
        ("ORBANA",          0.37, 0.49, JAFFA_COL),
        ("GALAR",           0.27, 0.29, JAFFA_COL),
        ("CAL MAH",         0.32, 0.38, JAFFA_COL),
        # --- LUCIAN ALLIANCE (right side / east) ---
        ("P4C-452",         0.82, 0.28, LUCIAN_COL),
        ("LUCIA",           0.78, 0.35, LUCIAN_COL),
        ("LANGARA",         0.75, 0.47, LUCIAN_COL),
        ("MARLOON",         0.82, 0.35, LUCIAN_COL),
        ("HANKA",           0.84, 0.36, LUCIAN_COL),
        ("VELONA",          0.86, 0.39, LUCIAN_COL),
        ("GARO",            0.92, 0.28, LUCIAN_COL),
        ("REVANNA",         0.91, 0.38, LUCIAN_COL),
        ("VYUS",            0.90, 0.47, LUCIAN_COL),
        ("MARLOON",         0.93, 0.44, LUCIAN_COL),
        # --- ASGARD TERRITORY (upper-left / north) ---
        ("OTHALA",          0.30, 0.14, ASGARD_COL),
        ("ORILLA",          0.22, 0.18, ASGARD_COL),
        ("HALA",            0.36, 0.18, ASGARD_COL),
        ("AMRA",            0.28, 0.17, ASGARD_COL),
        ("NOX",             0.12, 0.20, ASGARD_COL),
        ("CIMMERIA",        0.30, 0.23, ASGARD_COL),
        ("ARDENA",          0.57, 0.06, ASGARD_COL),
        # --- NEUTRAL / CONTESTED / UNCHARTED ---
        ("ABYDOS",          0.48, 0.71, NEUTRAL_COL),   # contested
        ("VIS UBAN",        0.58, 0.57, NEUTRAL_COL),
        ("ATLANTIS",        0.45, 0.50, NEUTRAL_COL),
        ("HELIOPOLIS",      0.52, 0.48, NEUTRAL_COL),
        ("EURONDA",         0.46, 0.20, NEUTRAL_COL),
        ("HASSYA",          0.58, 0.18, NEUTRAL_COL),
        ("KALLANA",         0.63, 0.21, NEUTRAL_COL),
        ("JADE",            0.48, 0.24, NEUTRAL_COL),
        ("KRESH'TA",        0.63, 0.25, NEUTRAL_COL),
        ("IX CHEL",         0.75, 0.24, NEUTRAL_COL),
        ("TUNA",            0.74, 0.20, NEUTRAL_COL),
        ("IR'TIN",          0.83, 0.21, NEUTRAL_COL),
        ("MALKSHOR",        0.81, 0.25, NEUTRAL_COL),
        ("ARGOS",           0.88, 0.25, NEUTRAL_COL),
        ("BELOTE",          0.60, 0.28, NEUTRAL_COL),
        ("ALTAIR",          0.74, 0.31, NEUTRAL_COL),
        ("TOBIN",           0.68, 0.36, NEUTRAL_COL),
        ("ENTAK",           0.68, 0.40, NEUTRAL_COL),
        ("ATHENEIN",        0.80, 0.41, NEUTRAL_COL),
        ("VOLIA",           0.83, 0.43, NEUTRAL_COL),
        ("BURROCK",         0.72, 0.44, NEUTRAL_COL),
        ("BEDROSIA",        0.65, 0.47, NEUTRAL_COL),
        ("EDORA",           0.78, 0.48, NEUTRAL_COL),
        ("CARTEGO",         0.64, 0.51, NEUTRAL_COL),
        ("PROCLARUSH",      0.52, 0.49, NEUTRAL_COL),
        ("BP6-3Q1",         0.68, 0.57, NEUTRAL_COL),
        ("HEBRIDAN",        0.77, 0.57, NEUTRAL_COL),
        ("TAGREA",          0.82, 0.54, NEUTRAL_COL),
        ("TEGALUS",         0.89, 0.56, NEUTRAL_COL),
        ("ORAN",            0.30, 0.55, NEUTRAL_COL),
        ("ARKHANA",         0.73, 0.73, NEUTRAL_COL),
        ("KHEB",            0.63, 0.79, NEUTRAL_COL),
        ("GADMEER NOVA",    0.30, 0.89, NEUTRAL_COL),
        ("TOLLAN",          0.74, 0.08, NEUTRAL_COL),
        ("OANESS",          0.68, 0.10, NEUTRAL_COL),
        ("GALAR",           0.47, 0.11, NEUTRAL_COL),
        ("ORAN",            0.37, 0.15, NEUTRAL_COL),
    ]

    # Deduplicate by position (some planets appear twice — keep first)
    seen_pos = set()
    unique_planets = []
    for name, px, py, col in PLANETS:
        key = (round(px, 2), round(py, 2))
        if key not in seen_pos:
            seen_pos.add(key)
            unique_planets.append((name, px, py, col))
    PLANETS = unique_planets

    # --- Territory boundary lines (semi-transparent grey, like reference) ---
    boundary_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    # Asgard boundary (upper-left arc)
    boundary_pts_asgard = [
        (0.08, 0.12), (0.20, 0.10), (0.38, 0.12), (0.45, 0.16),
        (0.48, 0.22), (0.42, 0.28), (0.30, 0.28), (0.18, 0.25), (0.08, 0.22),
    ]
    _draw_boundary(boundary_surf, boundary_pts_asgard, W, H)

    # Goa'uld boundary (center)
    boundary_pts_goauld = [
        (0.42, 0.28), (0.48, 0.22), (0.58, 0.22), (0.65, 0.28),
        (0.66, 0.38), (0.62, 0.44), (0.52, 0.44), (0.42, 0.42),
        (0.38, 0.35), (0.42, 0.28),
    ]
    _draw_boundary(boundary_surf, boundary_pts_goauld, W, H)

    # Jaffa boundary (center-left)
    boundary_pts_jaffa = [
        (0.22, 0.28), (0.30, 0.28), (0.38, 0.35), (0.42, 0.42),
        (0.40, 0.50), (0.32, 0.50), (0.24, 0.46), (0.20, 0.36),
        (0.22, 0.28),
    ]
    _draw_boundary(boundary_surf, boundary_pts_jaffa, W, H)

    # Lucian boundary (right)
    boundary_pts_lucian = [
        (0.72, 0.22), (0.88, 0.20), (0.96, 0.28), (0.96, 0.50),
        (0.88, 0.52), (0.75, 0.50), (0.70, 0.42), (0.66, 0.30),
        (0.72, 0.22),
    ]
    _draw_boundary(boundary_surf, boundary_pts_lucian, W, H)

    # Tau'ri boundary (bottom)
    boundary_pts_tauri = [
        (0.32, 0.58), (0.42, 0.52), (0.52, 0.50), (0.62, 0.52),
        (0.66, 0.60), (0.62, 0.72), (0.55, 0.80), (0.42, 0.82),
        (0.34, 0.76), (0.30, 0.66), (0.32, 0.58),
    ]
    _draw_boundary(boundary_surf, boundary_pts_tauri, W, H)
    surface.blit(boundary_surf, (0, 0))

    # --- Territory labels (faction names + annotations) ---
    label_font = pygame.font.SysFont("Arial", 30, bold=True)
    small_font = pygame.font.SysFont("Arial", 22, italic=True)

    territory_labels = [
        # (text, x_frac, y_frac, color, is_small)
        ("Tau'ri",               0.46, 0.74, TAURI_COL, False),
        ("-Earth's domain-",     0.46, 0.77, (120, 140, 180), True),
        ("Goa'uld",             0.52, 0.36, GOAULD_COL, False),
        ("-System Lords-",       0.52, 0.39, (180, 100, 100), True),
        ("Jaffa",               0.34, 0.42, JAFFA_COL, False),
        ("-Rebellion-",          0.34, 0.45, (180, 170, 100), True),
        ("Lucian Alliance",     0.82, 0.32, LUCIAN_COL, False),
        ("-Eastern territories-",0.82, 0.35, (180, 120, 160), True),
        ("Asgard",              0.26, 0.15, ASGARD_COL, False),
        ("-Protected planets-",  0.26, 0.18, (120, 170, 200), True),
        ("-Northern uncharted-", 0.60, 0.03, NEUTRAL_COL, True),
        ("-Eastern uncharted territory-", 0.92, 0.30, NEUTRAL_COL, True),
        ("-Wildspace-",          0.18, 0.53, NEUTRAL_COL, True),
        ("-Southern arm territory-", 0.30, 0.91, NEUTRAL_COL, True),
        ("-Former Ra's territory-", 0.78, 0.50, NEUTRAL_COL, True),
        ("-Aschen Conf.-",       0.78, 0.40, NEUTRAL_COL, True),
    ]

    for text, lx, ly, color, is_small in territory_labels:
        font = small_font if is_small else label_font
        rendered = font.render(text, True, color)
        rendered.set_alpha(160 if is_small else 200)
        surface.blit(rendered, (int(lx * W) - rendered.get_width() // 2,
                                int(ly * H) - rendered.get_height() // 2))

    # --- Planet markers (cyan diamonds with faction halos + labels) ---
    marker_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    name_font = pygame.font.SysFont("Arial", 20, bold=True)

    for name, px, py, color in PLANETS:
        mx, my = int(px * W), int(py * H)

        # Faction-colored halo glow
        pygame.draw.circle(marker_surf, (*color, 40), (mx, my), 18)

        # Cyan diamond marker
        ds = 7
        diamond = [(mx, my - ds), (mx + ds, my), (mx, my + ds), (mx - ds, my)]
        pygame.draw.polygon(marker_surf, (100, 220, 255, 210), diamond)
        pygame.draw.polygon(marker_surf, (180, 240, 255, 255), diamond, 2)

        # Planet name label (cyan)
        label = name_font.render(name, True, (100, 220, 255))
        label.set_alpha(220)
        # Position label to the right unless near right edge
        label_x = mx + 12
        if px > 0.85:
            label_x = mx - label.get_width() - 12
        label_y = my - label.get_height() // 2
        marker_surf.blit(label, (label_x, label_y))

    surface.blit(marker_surf, (0, 0))

    # --- Subtle navigation grid overlay ---
    grid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    grid_spacing = 200
    grid_color = (50, 60, 80, 18)
    for x in range(0, W, grid_spacing):
        pygame.draw.line(grid_surf, grid_color, (x, 0), (x, H), 1)
    for y in range(0, H, grid_spacing):
        pygame.draw.line(grid_surf, grid_color, (0, y), (W, y), 1)
    surface.blit(grid_surf, (0, 0))

    pygame.image.save(surface, path)
    print(f"  Created conquest background: {path}")
    return path


def _draw_boundary(surface, points, w, h):
    """Draw a territory boundary polyline on a surface."""
    color = (120, 120, 140, 55)
    pixel_pts = [(int(x * w), int(y * h)) for x, y in points]
    if len(pixel_pts) >= 2:
        pygame.draw.lines(surface, color, False, pixel_pts, 2)


def create_conquest_menu_background():
    """Create a separate 4K background for the Galactic Conquest submenu.

    StarCraft-meets-Stargate cinematic UI: darker, more dramatic, focused on
    the galaxy vista with no planet markers (those are for the gameplay map).
    """
    path = os.path.join(ASSETS_DIR, "conquest_menu_bg.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: conquest_menu_bg.png (already exists)")
        return None

    W, H = BOARD_WIDTH, BOARD_HEIGHT
    surface = pygame.Surface((W, H))
    cx, cy = W // 2, int(H * 0.45)  # Galaxy shifted slightly up for menu layout
    max_r = math.sqrt(cx**2 + cy**2)

    # --- Deep space base (darker than galaxy map) ---
    for y in range(0, H, 2):
        for x in range(0, W, 4):
            dx, dy = x - cx, y - cy
            t = min(1.0, math.sqrt(dx*dx + dy*dy) / max_r)
            r = int(30 * (1 - t) + 3 * t)
            g = int(25 * (1 - t) + 4 * t)
            b = int(18 * (1 - t) + 15 * t)
            pygame.draw.rect(surface, (r, g, b), (x, y, 4, 2))

    # --- Spiral arms (more dramatic, brighter nebulae) ---
    arm_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for arm_idx, arm_color in enumerate([
        (60, 80, 200, 40), (180, 50, 60, 35),
        (90, 50, 140, 20), (50, 90, 150, 20),
    ]):
        base_a = arm_idx * math.pi / 2
        for i in range(900):
            t = i / 900.0
            radius = 60 + t * (min(W, H) * 0.48)
            angle = base_a + t * 5.2
            spread = 40 + t * 160
            for _ in range(5):
                off = random.gauss(0, spread)
                a_off = off / max(radius, 1)
                ax = cx + int(math.cos(angle + a_off) * radius)
                ay = cy + int(math.sin(angle + a_off) * radius)
                if 0 <= ax < W and 0 <= ay < H:
                    size = random.randint(3, 12)
                    pygame.draw.circle(arm_surf, arm_color, (ax, ay), size)
    surface.blit(arm_surf, (0, 0))

    # --- Galactic core (larger, brighter) ---
    core_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for r in range(350, 0, -4):
        frac = 1 - r / 350
        alpha = max(0, min(255, int(200 * frac)))
        w_val = min(255, 150 + int(105 * frac))
        pygame.draw.circle(core_surf, (w_val, max(0, w_val - 45), max(0, w_val - 100), alpha),
                           (cx, cy), r)
    surface.blit(core_surf, (0, 0))

    # --- Starfield ---
    for _ in range(2500):
        sx, sy = random.randint(0, W), random.randint(0, H)
        dist = math.sqrt((sx - cx)**2 + (sy - cy)**2)
        core_f = max(0.2, 1 - dist / max_r)
        bright = random.randint(int(50 * core_f), int(255 * core_f))
        size = random.choice([1, 1, 1, 2, 2])
        pygame.draw.circle(surface, (bright, bright, min(255, bright + 10)), (sx, sy), size)

    for _ in range(50):
        sx, sy = random.randint(0, W), random.randint(0, H)
        size = random.randint(3, 7)
        bright = random.randint(180, 255)
        for r in range(size, 0, -1):
            a = int(bright * r / size)
            pygame.draw.circle(surface, (a, a, min(255, a + 20)), (sx, sy), r)

    # --- Subtle StarCraft-style border frame ---
    frame_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    # Top/bottom thick bars with gradient
    for i in range(60):
        alpha = int(200 * (1 - i / 60))
        pygame.draw.line(frame_surf, (20, 30, 60, alpha), (0, i), (W, i))
        pygame.draw.line(frame_surf, (20, 30, 60, alpha), (0, H - 1 - i), (W, H - 1 - i))
    # Side bars
    for i in range(30):
        alpha = int(150 * (1 - i / 30))
        pygame.draw.line(frame_surf, (15, 25, 50, alpha), (i, 0), (i, H))
        pygame.draw.line(frame_surf, (15, 25, 50, alpha), (W - 1 - i, 0), (W - 1 - i, H))
    # Corner accents
    corner_size = 120
    for corner_x, corner_y, dx_sign, dy_sign in [
        (0, 0, 1, 1), (W, 0, -1, 1), (0, H, 1, -1), (W, H, -1, -1)
    ]:
        for i in range(corner_size):
            alpha = int(100 * (1 - i / corner_size))
            pygame.draw.line(frame_surf, (80, 120, 200, alpha),
                             (corner_x, corner_y + dy_sign * i),
                             (corner_x + dx_sign * int(corner_size * (1 - i/corner_size)),
                              corner_y + dy_sign * i))
    surface.blit(frame_surf, (0, 0))

    # --- Grid (more subtle than galaxy map) ---
    grid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for x in range(0, W, 240):
        pygame.draw.line(grid_surf, (30, 40, 60, 12), (x, 0), (x, H), 1)
    for y in range(0, H, 240):
        pygame.draw.line(grid_surf, (30, 40, 60, 12), (0, y), (W, y), 1)
    surface.blit(grid_surf, (0, 0))

    pygame.image.save(surface, path)
    print(f"  Created conquest menu background: {path}")
    return path


def create_conquest_deck_building_background():
    """Create a 4K background for the conquest mode deck builder.

    Inspired by a Stargate energy beam interior – deep purple/blue space
    with a central vertical energy column, ornate golden Goa'uld-style
    framing, and swirling energy tendrils.  Serves as the backdrop when
    the player edits their conquest deck.
    """
    path = os.path.join(ASSETS_DIR, "deck_building_conquest_bg.png")
    if not should_create_file(path):
        print(f"  ⊗ Skipped: deck_building_conquest_bg.png (already exists)")
        return None

    W, H = BOARD_WIDTH, BOARD_HEIGHT
    surface = pygame.Surface((W, H))
    cx = W // 2

    # --- Deep space base with purple tint ---
    for y in range(0, H, 2):
        t = y / H
        r = int(8 + 12 * t)
        g = int(5 + 8 * t)
        b = int(20 + 30 * (1 - abs(t - 0.5) * 2))
        pygame.draw.rect(surface, (r, g, b), (0, y, W, 2))

    # --- Central energy beam (vertical pillar of light) ---
    beam_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    beam_w_base = 120
    for layer in range(6):
        w = beam_w_base + layer * 80
        alpha = max(5, 60 - layer * 10)
        color = (180 - layer * 20, 140 - layer * 15, 255, alpha)
        pygame.draw.rect(beam_surf, color, (cx - w // 2, 0, w, H))
    # Core bright line
    pygame.draw.rect(beam_surf, (220, 200, 255, 100), (cx - 30, 0, 60, H))
    pygame.draw.rect(beam_surf, (255, 255, 255, 60), (cx - 8, 0, 16, H))
    surface.blit(beam_surf, (0, 0))

    # --- Swirling energy tendrils ---
    tendril_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for arm_idx in range(8):
        base_angle = arm_idx * math.pi / 4
        side = 1 if arm_idx % 2 == 0 else -1
        for i in range(300):
            t = i / 300.0
            y_pos = int(t * H)
            radius = 80 + t * 350
            angle = base_angle + t * 3.5 * side
            x_pos = cx + int(math.cos(angle) * radius)
            if 0 <= x_pos < W and 0 <= y_pos < H:
                # Purple/blue tendrils
                r_c = min(255, 120 + int(60 * math.sin(t * 5)))
                b_c = min(255, 180 + int(40 * math.cos(t * 3)))
                size = random.randint(3, 10)
                alpha = max(10, int(35 * (1 - t)))
                pygame.draw.circle(tendril_surf, (r_c, 60, b_c, alpha), (x_pos, y_pos), size)
    surface.blit(tendril_surf, (0, 0))

    # --- Golden ornate frame elements (Goa'uld style) ---
    frame_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    gold = (200, 160, 60)
    gold_dim = (140, 110, 40)

    # Top and bottom ornate bars
    bar_h = 80
    for i in range(bar_h):
        alpha = int(180 * (1 - i / bar_h))
        pygame.draw.line(frame_surf, (*gold_dim, alpha), (0, i), (W, i))
        pygame.draw.line(frame_surf, (*gold_dim, alpha), (0, H - 1 - i), (W, H - 1 - i))

    # Side pillars
    pillar_w = 60
    for i in range(pillar_w):
        alpha = int(120 * (1 - i / pillar_w))
        pygame.draw.line(frame_surf, (*gold_dim, alpha), (i, 0), (i, H))
        pygame.draw.line(frame_surf, (*gold_dim, alpha), (W - 1 - i, 0), (W - 1 - i, H))

    # Corner accents (golden triangular shapes)
    corner_size = 200
    for corner_x, corner_y, dx_s, dy_s in [
        (0, 0, 1, 1), (W, 0, -1, 1), (0, H, 1, -1), (W, H, -1, -1)
    ]:
        for i in range(corner_size):
            alpha = int(80 * (1 - i / corner_size))
            end_x = corner_x + dx_s * int(corner_size * (1 - i / corner_size))
            pygame.draw.line(frame_surf, (*gold, alpha),
                             (corner_x, corner_y + dy_s * i),
                             (end_x, corner_y + dy_s * i))

    # Decorative horizontal accent lines
    for y_frac in [0.12, 0.88]:
        y_pos = int(H * y_frac)
        pygame.draw.line(frame_surf, (*gold, 60), (pillar_w, y_pos), (W - pillar_w, y_pos), 2)
        # Small diamond markers along the line
        for x_frac in [0.2, 0.4, 0.6, 0.8]:
            dx = int(W * x_frac)
            pts = [(dx, y_pos - 6), (dx + 6, y_pos), (dx, y_pos + 6), (dx - 6, y_pos)]
            pygame.draw.polygon(frame_surf, (*gold, 80), pts)

    surface.blit(frame_surf, (0, 0))

    # --- Starfield (fewer, subtle) ---
    for _ in range(400):
        sx = random.randint(0, W)
        sy = random.randint(0, H)
        dist_from_center = abs(sx - cx)
        if dist_from_center < 200:
            continue  # Keep the beam area clean
        brightness = random.randint(80, 200)
        size = random.choice([1, 1, 2])
        pygame.draw.circle(surface, (brightness, brightness, min(255, brightness + 30)), (sx, sy), size)

    # --- Title watermark ---
    try:
        title_font = pygame.font.SysFont("Impact, Arial", 72, bold=True)
        title_text = title_font.render("CONQUEST DECK", True, (200, 180, 120))
        title_text.set_alpha(40)
        surface.blit(title_text, (cx - title_text.get_width() // 2, 20))
    except Exception:
        pass

    pygame.image.save(surface, path)
    print(f"  Created conquest deck building background: {path}")
    return path


if __name__ == "__main__":
    main()
