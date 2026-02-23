import pygame
import sys
import math
import random
import os
from pygame.math import Vector2
from game import Game
from lan_protocol import LanMessageType, parse_message
from cards import (
    ALL_CARDS,
    reload_card_images,
    FACTION_TAURI,
    FACTION_GOAULD,
    FACTION_JAFFA,
    FACTION_LUCIAN,
    FACTION_ASGARD,
)
from ai_opponent import AIController
from enum import Enum, auto
from draft_mode import DraftRun
from abilities import Ability, has_ability, is_hero, is_spy, is_medic
from game_loop_state import GameLoopState
from event_handler import handle_events
from frame_renderer import render_frame

# ============================================================================
# DEBUG MODE (v4.3.1)
# ============================================================================
# Set to True to enable FPS counter and performance profiling
from game_settings import get_settings
DEBUG_MODE = os.environ.get('STARGWENT_DEBUG', '').lower() in ('1', 'true', 'yes') or get_settings().get_show_fps()
# Toggle with F3 key during gameplay

class UIState(Enum):
    """Finite State Machine for UI interaction modes."""
    # Core Game Phases (synced with game.game_state)
    MULLIGAN = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    
    # Overlays & Special Modes
    LEADER_MATCHUP = auto()
    PAUSED = auto()
    DISCARD_VIEW = auto()
    MEDIC_SELECT = auto()
    DECOY_SELECT = auto()
    RING_TRANSPORT_SELECT = auto()
    JONAS_PEEK = auto()
    BAAL_CLONE_SELECT = auto()
    VALA_SELECT = auto()
    CATHERINE_SELECT = auto()
    LEADER_CHOICE_SELECT = auto()
    THOR_MOVE_SELECT = auto()
    LAN_CHAT = auto()

# LAN Mode globals - set by lan_game.py when running multiplayer
LAN_MODE = False
LAN_CONTEXT = None
from animations import (
    AnimationManager,
    StargateActivationEffect,
    GlowAnimation,
    CardSlideAnimation,
    ScorchEffect,
    NaquadahExplosionEffect,
    AICardPlayAnimation,
    create_hero_animation,
    create_ability_animation,
    LegendaryLightningEffect,
    ClearWeatherBlackHole,
    MeteorShowerImpactEffect,
    HathorStealAnimation,
    ThorsHammerPurgeEffect,
    ZPMSurgeEffect,
    CommunicationRevealEffect,
    MerlinAntiOriEffect,
    DakaraShockwaveEffect,
    QuantumMirrorEffect,
    ReplicatorCrawlEffect,
    GoauldSymbioteAnimation,
    AsgardBeamTransportEffect,
    CardRevealAnimation,
    AbilityBurstEffect,
    RowScoreAnimation,
    CardDisintegrationEffect,
    CardMaterializationEffect,
)
from deck_builder import run_deck_builder, build_faction_deck
from unlocks import CardUnlockSystem, show_card_reward_screen, show_leader_reward_screen, UNLOCKABLE_CARDS
from main_menu import run_main_menu, DeckManager, show_stargate_opening
from power import FACTION_POWERS, FactionPowerEffect
from deck_persistence import record_victory, record_defeat, check_leader_unlock, get_persistence
import battle_music
import selection_overlays
import transitions
import board_renderer
import game_setup

# ============================================================================
# MODULE IMPORTS & INITIALIZATION
# ============================================================================
import display_manager
import game_config as cfg
import render_engine as re

# Initialize display via the new manager
display_manager.initialize_display()

# Initialize GPU post-processing (graceful fallback if unavailable)
display_manager.initialize_gpu()

# Load user-created content (cards, leaders, factions)
# This must happen early, before card images are loaded
try:
    from user_content_loader import load_user_content
    load_user_content()
    print("[INIT] User content loaded")
except ImportError:
    pass  # user_content_loader not available
except Exception as e:
    print(f"[INIT] Warning: Could not load user content: {e}")

# Calculate layout dimensions and fonts based on initialized display
cfg.recalculate_dimensions()

# Pull commonly used values into module scope for convenience
# NOTE: screen reference is updated in game loop after mode changes
screen = display_manager.screen  # Initial reference
SCREEN_WIDTH = display_manager.SCREEN_WIDTH
SCREEN_HEIGHT = display_manager.SCREEN_HEIGHT
SCALE_FACTOR = display_manager.SCALE_FACTOR
# Display functions
toggle_fullscreen_mode = display_manager.toggle_fullscreen_mode
sync_fullscreen_from_surface = display_manager.sync_fullscreen_from_surface
# Render engine functions
draw_card = re.draw_card
draw_hand = re.draw_hand
draw_opponent_hand = re.draw_opponent_hand
draw_weather_slots = re.draw_weather_slots
draw_horn_slots = re.draw_horn_slots
draw_row_score_boxes = re.draw_row_score_boxes
draw_history_panel = re.draw_history_panel
draw_leader_portrait = re.draw_leader_portrait
draw_leader_column = re.draw_leader_column
_compute_hand_positions = re._compute_hand_positions
CARD_WIDTH = cfg.CARD_WIDTH
CARD_HEIGHT = cfg.CARD_HEIGHT
ROW_RANGES = cfg.ROW_RANGES
COLUMN_RANGES = cfg.COLUMN_RANGES
pct_x = cfg.pct_x
pct_y = cfg.pct_y
rect_from_percent = cfg.rect_from_percent
# Fonts
ROW_FONT = cfg.ROW_FONT
# Colors (all accessed via cfg module now)
BLACK = cfg.BLACK
GOLD = cfg.GOLD
RED = cfg.RED
GREEN = cfg.GREEN
BLUE = cfg.BLUE

# ═══════════════════════════════════════════════════════════════
# LAYOUT SYSTEM - Percentage-based 4K blueprint
# (Managed in game_config.py)
# ═══════════════════════════════════════════════════════════════

PLAYFIELD_RANGE = cfg.COLUMN_RANGES["playfield"]
opponent_hand_area_y = cfg.opponent_hand_area_y
player_hand_area_y = cfg.player_hand_area_y
OPPONENT_HAND_HEIGHT = cfg.OPPONENT_HAND_HEIGHT
PLAYER_HAND_HEIGHT = cfg.PLAYER_HAND_HEIGHT
COMMAND_BAR_Y = cfg.COMMAND_BAR_Y
COMMAND_BAR_HEIGHT = cfg.COMMAND_BAR_HEIGHT
weather_y = cfg.weather_y
WEATHER_ZONE_HEIGHT = cfg.WEATHER_ZONE_HEIGHT
ROW_HEIGHT = max(1, pct_y(ROW_RANGES["player_close"][1] - ROW_RANGES["player_close"][0]))
HAND_Y_OFFSET = SCREEN_HEIGHT - player_hand_area_y

# Use pre-calculated rectangles from game_config
# Use cfg versions directly to ensure resolution sync
# cfg.PLAYER_ROW_RECTS = cfg.cfg.PLAYER_ROW_RECTS
# cfg.OPPONENT_ROW_RECTS = cfg.cfg.OPPONENT_ROW_RECTS
WEATHER_SLOT_RECTS = cfg.WEATHER_SLOT_RECTS
PLAYER_HORN_SLOT_RECTS = cfg.PLAYER_HORN_SLOT_RECTS
OPPONENT_HORN_SLOT_RECTS = cfg.OPPONENT_HORN_SLOT_RECTS

PLAYFIELD_LEFT = cfg.PLAYFIELD_LEFT
PLAYFIELD_WIDTH = cfg.PLAYFIELD_WIDTH
HUD_LEFT = cfg.HUD_LEFT
HUD_WIDTH = cfg.HUD_WIDTH
LEADER_COLUMN_X = cfg.LEADER_COLUMN_X
LEADER_COLUMN_WIDTH = cfg.LEADER_COLUMN_WIDTH
LEADER_COLUMN_HEIGHT = cfg.LEADER_COLUMN_HEIGHT
LEADER_SECTION_HEIGHT = cfg.LEADER_SECTION_HEIGHT
LEADER_TOP_RECT = cfg.LEADER_TOP_RECT
LEADER_BOTTOM_RECT = cfg.LEADER_BOTTOM_RECT
HORN_COLUMN_X = cfg.HORN_COLUMN_X
HORN_COLUMN_WIDTH = cfg.HORN_COLUMN_WIDTH
HAND_REGION_LEFT = cfg.HAND_REGION_LEFT
HAND_REGION_WIDTH = cfg.HAND_REGION_WIDTH

HUD_PASS_BUTTON_RECT = None

# Use colors from game_config
ROW_COLORS = cfg.ROW_COLORS
FACTION_GLOW_COLORS = cfg.FACTION_GLOW_COLORS


def get_row_color(row_name):
    """Return the theme color for a given row type."""
    return cfg.get_row_color(row_name)


def get_row_under_position(pos):
    """Return (row_name, rect) under the given screen position."""
    for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
        for row_name, row_rect in rects.items():
            if row_rect.collidepoint(pos):
                return row_name, row_rect
    return None, None


def get_weather_target_rows(card, hovered_row=None):
    """Determine which shared row(s) a weather card will affect."""
    ability = (card.ability or "").lower()
    if "ice planet hazard" in ability:
        return ["close"]
    if "nebula interference" in ability:
        return ["ranged"]
    if "asteroid storm" in ability:
        return ["siege"]
    if "electromagnetic pulse" in ability and hovered_row in ["close", "ranged", "siege"]:
        return [hovered_row]
    return []


def draw_stargwent_button(surface, rect, text, mouse_pos, font=None,
                          base_color=(30, 45, 70), hover_color=(45, 70, 110),
                          border_color=(70, 130, 200), hover_border=(100, 180, 255),
                          text_color=(210, 230, 255)):
    """Draw a Stargwent-styled button with hover effect.

    Args:
        surface: Pygame surface to draw on
        rect: pygame.Rect for button position and size
        text: Button text string
        mouse_pos: Current mouse position tuple
        font: Font to use (defaults to cfg.UI_FONT)
        base_color: Button background color
        hover_color: Button background color on hover
        border_color: Border color
        hover_border: Border color on hover
        text_color: Text color

    Returns:
        bool: True if button is currently hovered
    """
    is_hovered = rect.collidepoint(mouse_pos)

    # Draw button background with gradient effect
    bg_color = hover_color if is_hovered else base_color
    pygame.draw.rect(surface, bg_color, rect, border_radius=12)

    # Draw inner glow on hover
    if is_hovered:
        inner_rect = rect.inflate(-4, -4)
        glow_surface = pygame.Surface(inner_rect.size, pygame.SRCALPHA)
        glow_surface.fill((100, 180, 255, 30))
        surface.blit(glow_surface, inner_rect.topleft)

    # Draw border
    bd_color = hover_border if is_hovered else border_color
    pygame.draw.rect(surface, bd_color, rect, width=2, border_radius=12)

    # Draw text with optional shadow
    use_font = font or cfg.UI_FONT
    if is_hovered:
        # Shadow for hover state
        shadow = use_font.render(text, True, (0, 0, 0))
        shadow_rect = shadow.get_rect(center=(rect.centerx + 2, rect.centery + 2))
        surface.blit(shadow, shadow_rect)

    btn_text = use_font.render(text, True, text_color if not is_hovered else (255, 255, 255))
    text_rect = btn_text.get_rect(center=rect.center)
    surface.blit(btn_text, text_rect)

    return is_hovered


def add_special_card_effect(card, effect_x, effect_y, anim_manager, screen_width, screen_height, game=None):
    """Trigger unique animations for special cards matching lore/logic."""
    name_lower = (card.name or "").lower()
    ability_lower = (card.ability or "").lower()
    card_id = getattr(card, 'card_id', '') or ''

    if "thor's hammer" in name_lower or "remove all goa'uld" in ability_lower:
        anim_manager.add_effect(ThorsHammerPurgeEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    # Asgard Beam Tech — white transporter beam flash with sound
    if "beam tech" in name_lower:
        anim_manager.add_effect(AsgardBeamTransportEffect(effect_x, effect_y, screen_height))
        from sound_manager import get_sound_manager
        get_sound_manager().play_asgard_beam_sound()
        return True
    if "zero point module" in name_lower or "zpm" in name_lower or "double all your siege" in ability_lower:
        anim_manager.add_effect(ZPMSurgeEffect(effect_x, effect_y))
        return True
    if "communication device" in name_lower or "reveal opponent's hand" in ability_lower:
        anim_manager.add_effect(CommunicationRevealEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "quantum mirror" in name_lower or "shuffle your hand into deck" in ability_lower:
        # Get actual hand size from game state (card is already removed, so +1)
        num_cards = 8  # Default fallback
        if game and hasattr(game, 'current_player'):
            num_cards = len(game.current_player.hand) + 1  # +1 for the card being played
        anim_manager.add_effect(QuantumMirrorEffect(effect_x, effect_y, screen_width, screen_height, num_cards=num_cards))
        return True
    if "merlin" in name_lower or "anti-ori" in name_lower:
        anim_manager.add_effect(MerlinAntiOriEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "dakara" in name_lower:
        anim_manager.add_effect(DakaraShockwaveEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "naquadah" in name_lower or "overload" in ability_lower:
        anim_manager.add_effect(NaquadahExplosionEffect(effect_x, effect_y, duration=cfg.ANIM_MAJOR_EFFECT))
        return True
    if "replicator swarm" in name_lower:
        anim_manager.add_effect(ReplicatorCrawlEffect(screen_width, screen_height))
        from sound_manager import get_sound_manager
        get_sound_manager().play_replicator_sound()
        return True
    # Goa'uld Symbiote - larva seeking host animation
    if card_id == "goauld_symbiote" or "symbiote" in name_lower:
        # Target a random point in opponent's board area (top third of screen)
        import random
        target_x = random.randint(screen_width // 4, screen_width * 3 // 4)
        target_y = random.randint(screen_height // 6, screen_height // 3)
        anim_manager.add_effect(GoauldSymbioteAnimation(effect_x, effect_y, target_x, target_y))
        # Play symbiote sound effect
        from sound_manager import get_sound_manager
        get_sound_manager().play_symbiote_sound()
        return True
    return False


# draw_card moved to render_engine.py

# draw_hand moved to render_engine.py

# draw_opponent_hand moved to render_engine.py
# draw_weather_slots moved to render_engine.py
# draw_horn_slots moved to render_engine.py

# _render_sg1_score_box moved to render_engine.py
# draw_row_score_boxes moved to render_engine.py
# draw_history_panel moved to render_engine.py

# draw_leader_column moved to render_engine.py


def _show_disconnect_overlay(screen, screen_width, screen_height, reason="connection_lost", countdown_seconds=10):
    """Show a disconnect overlay with countdown and return options.

    Args:
        screen: Pygame surface to draw on
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        reason: "opponent_disconnected" or "connection_lost"
        countdown_seconds: Seconds before auto-return to menu

    Returns:
        None (blocks until user clicks or countdown expires)
    """
    font_large = pygame.font.SysFont("Arial", 60, bold=True)
    font_medium = pygame.font.SysFont("Arial", 36)
    font_small = pygame.font.SysFont("Arial", 24)

    # Reason-specific messages
    if reason == "opponent_disconnected":
        title = "OPPONENT DISCONNECTED"
        subtitle = "Your opponent has left the game"
        title_color = cfg.HIGHLIGHT_ORANGE
    else:
        title = "CONNECTION LOST"
        subtitle = "The connection to your opponent was interrupted"
        title_color = cfg.HIGHLIGHT_RED

    # Button rect
    button_width = 280
    button_height = 50
    button_rect = pygame.Rect(
        screen_width // 2 - button_width // 2,
        screen_height // 2 + 100,
        button_width, button_height
    )

    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()

    while True:
        elapsed_ms = pygame.time.get_ticks() - start_time
        remaining = max(0, countdown_seconds - elapsed_ms // 1000)

        # Check for timeout
        if remaining <= 0:
            return

        # Event handling
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                    return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if button_rect.collidepoint(mouse_pos):
                    return

        # Draw overlay
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        screen.blit(overlay, (0, 0))

        # Draw border box
        box_width = 600
        box_height = 300
        box_rect = pygame.Rect(
            screen_width // 2 - box_width // 2,
            screen_height // 2 - box_height // 2,
            box_width, box_height
        )
        pygame.draw.rect(screen, (30, 40, 55), box_rect, border_radius=12)
        pygame.draw.rect(screen, title_color, box_rect, 3, border_radius=12)

        # Draw title
        text1 = font_large.render(title, True, title_color)
        screen.blit(text1, (screen_width // 2 - text1.get_width() // 2, box_rect.y + 30))

        # Draw subtitle
        text2 = font_medium.render(subtitle, True, cfg.TEXT_DIM)
        screen.blit(text2, (screen_width // 2 - text2.get_width() // 2, box_rect.y + 100))

        # Draw countdown
        countdown_text = f"Returning to menu in {remaining} seconds..."
        text3 = font_small.render(countdown_text, True, cfg.TEXT_MUTED)
        screen.blit(text3, (screen_width // 2 - text3.get_width() // 2, box_rect.y + 150))

        # Draw return button
        button_hover = button_rect.collidepoint(mouse_pos)
        button_color = (70, 130, 220) if button_hover else (50, 100, 180)
        pygame.draw.rect(screen, button_color, button_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 150, 230), button_rect, 2, border_radius=8)

        btn_text = font_small.render("Return Now (Enter)", True, cfg.TEXT_LIGHT)
        screen.blit(btn_text, (button_rect.centerx - btn_text.get_width() // 2,
                               button_rect.centery - btn_text.get_height() // 2))

        display_manager.gpu_flip()
        clock.tick(30)


def build_button_info_popup(kind, owner, anchor_rect, special_kind=None):
    """Create metadata describing the info popup for leader column buttons."""
    if not owner or not anchor_rect:
        return None

    color = FACTION_GLOW_COLORS.get(owner.faction, (255, 215, 0))
    title = "Info"
    lines = []

    if kind == "ability":
        leader_data = owner.leader or {}
        leader_name = leader_data.get("name", "Leader")
        ability_name = leader_data.get("ability", "Leader Ability")
        ability_desc = leader_data.get("ability_desc", ability_name)
        title = f"{leader_name} — Ability"
        lines = [ability_name, ability_desc]
    elif kind == "faction":
        power = getattr(owner, "faction_power", None)
        if power:
            title = f"{power.name}"
            lines = [power.description]
        else:
            title = f"{owner.faction} Power"
            lines = ["This faction has no special power assigned."]
    elif kind == "special":
        if special_kind == "iris" and hasattr(owner, "iris_defense"):
            status = "Active" if owner.iris_defense.is_active() else ("Ready" if owner.iris_defense.is_available() else "Spent")
            title = "Tau'ri Iris Defense"
            lines = [
                "Blocks the next enemy card as it emerges from the wormhole.",
                f"Status: {status}"
            ]
        elif special_kind == "rings" and getattr(owner, "ring_transportation", None):
            rt = owner.ring_transportation
            if rt.animation_in_progress:
                status = "Transferring..."
            elif rt.can_use():
                status = "Ready this round"
            else:
                status = "Used this round"
            title = "Goa'uld Ring Transportation"
            lines = [
                "Return one of your close-combat units to hand once per round.",
                f"Status: {status}"
            ]
        else:
            return None
    else:
        return None

    clean_lines = [line for line in lines if line]
    if not clean_lines:
        clean_lines = ["No additional details available."]

    return {
        "title": title,
        "lines": clean_lines,
        "anchor": anchor_rect.copy(),
        "color": color,
        "kind": kind,
        "special_kind": special_kind,
        "owner": owner,
        "expires_at": pygame.time.get_ticks() + cfg.POPUP_DISPLAY_TIME,
    }


def draw_button_info_popup(surface, popup):
    """Render the compact info popup near a leader column button."""
    if not popup:
        return

    anchor_rect = popup.get("anchor")
    if not anchor_rect:
        return

    padding = 14
    title_font = pygame.font.SysFont("Arial", max(20, int(20 * SCALE_FACTOR)), bold=True)
    body_font = pygame.font.SysFont("Arial", max(14, int(16 * SCALE_FACTOR)))
    max_text_width = max(int(320 * SCALE_FACTOR), 240)

    def wrap_line(text):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if body_font.size(candidate)[0] <= max_text_width - padding * 2:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if not lines:
            lines.append("")
        return lines

    wrapped_lines = []
    for entry in popup.get("lines", []):
        wrapped_lines.extend(wrap_line(entry))

    title_surface = title_font.render(popup.get("title", "Info"), True, popup.get("color", (255, 215, 0)))
    widest_line = title_surface.get_width()
    for line in wrapped_lines:
        line_width = body_font.size(line)[0]
        widest_line = max(widest_line, line_width)

    popup_width = min(max_text_width, max(widest_line + padding * 2, int(260 * SCALE_FACTOR)))
    body_line_height = body_font.get_linesize()
    popup_height = padding * 2 + title_surface.get_height()
    if wrapped_lines:
        popup_height += 8 + len(wrapped_lines) * body_line_height

    popup_rect = pygame.Rect(0, 0, popup_width, popup_height)
    place_right = anchor_rect.right + popup_width + 20 <= SCREEN_WIDTH
    if place_right:
        popup_rect.left = anchor_rect.right + 18
    else:
        popup_rect.right = anchor_rect.left - 18
    popup_rect.top = max(20, min(anchor_rect.centery - popup_height // 2, SCREEN_HEIGHT - popup_height - 20))

    popup_surface = pygame.Surface((popup_width, popup_height), pygame.SRCALPHA)
    popup_surface.fill((12, 20, 34, 235))
    pygame.draw.rect(popup_surface, popup.get("color", (255, 215, 0)),
                     popup_surface.get_rect(), width=3, border_radius=12)

    y_cursor = padding
    popup_surface.blit(title_surface, (padding, y_cursor))
    y_cursor += title_surface.get_height() + 8

    for line in wrapped_lines:
        text_surface = body_font.render(line, True, (225, 230, 240))
        popup_surface.blit(text_surface, (padding, y_cursor))
        y_cursor += body_line_height

    surface.blit(popup_surface, popup_rect.topleft)

def get_opponent_hand_card_center(total_cards, index):
    """Return the screen center position of an opponent hand slot by index."""
    hand_area_height = OPPONENT_HAND_HEIGHT
    hand_y = opponent_hand_area_y + (hand_area_height - CARD_HEIGHT) // 2
    card_spacing = int(CARD_WIDTH * 0.125)
    positions, _ = _compute_hand_positions(total_cards, CARD_WIDTH, card_spacing)
    if not positions:
        return (HAND_REGION_LEFT, hand_y + CARD_HEIGHT // 2)
    safe_index = max(0, min(index if index is not None else 0, len(positions) - 1))
    card_x = positions[safe_index]
    return (card_x + CARD_WIDTH // 2, hand_y + CARD_HEIGHT // 2)

# ============================================================================
# TRANSITIONS
# ============================================================================










    
    # Brief pause before game starts
    pygame.time.wait(300)

# draw_leader_portrait moved to render_engine.py





















def run_game_with_context(screen, context):
    """Run the main game loop initialized with a LAN context.

    Delegates to run_game(). The caller (lan_game.py) sets LAN_MODE and
    LAN_CONTEXT globals before calling us, which main() passes through
    to game_setup.initialize_game() via lan_mode/lan_context params.
    """
    run_game()


def main(lan_game_data=None):
    """Main game loop.

    Args:
        lan_game_data: Optional dict with LAN game info to skip menu/deck builder.
                      Keys: 'game', 'player_faction', 'player_leader', 'ai_faction', 'ai_leader'
    """
    global screen, LAN_MODE, LAN_CONTEXT, DEBUG_MODE  # Update screen ref on fullscreen toggle

    # Update layout for current resolution
    import game_config as cfg
    cfg.recalculate_dimensions()

    # Initialize unlock system
    from unlocks import CardUnlockSystem
    unlock_system = CardUnlockSystem()

    # Initialize game using new setup module
    init_result = game_setup.initialize_game(
        screen,
        unlock_system=unlock_system, # Pass the initialized system
        lan_mode=LAN_MODE,
        lan_context=LAN_CONTEXT,
        toggle_fullscreen_callback=toggle_fullscreen_mode,
        lan_game_data=lan_game_data
    )
    
    if not init_result:
        pygame.quit()
        sys.exit()
        
    game, ai_controller, network_proxy, menu_action = init_result

    # Refresh screen — fullscreen may have been toggled during menu/deck builder
    screen = display_manager.screen

    # --- Animation Manager ---
    from animations import AmbientBackgroundEffects
    anim_manager = AnimationManager()
    ambient_effects = AmbientBackgroundEffects(SCREEN_WIDTH, SCREEN_HEIGHT)
    
    # Track previous scores for animation
    prev_p1_score = 0
    prev_p2_score = 0
    
    # --- Asset Loading ---
    assets = {}
    try:
        assets["board"] = pygame.image.load("assets/board_background.png").convert()
    except pygame.error as e:
        print(f"Warning: Could not load board background. Using solid color. ({e})")
        assets["board"] = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        assets["board"].fill((20, 20, 30))

    # Load mulligan background
    try:
        assets["mulligan_bg"] = pygame.image.load("assets/mulligan_bg.png").convert()
        assets["mulligan_bg"] = pygame.transform.smoothscale(assets["mulligan_bg"], (SCREEN_WIDTH, SCREEN_HEIGHT))
    except pygame.error as e:
        print(f"Warning: Could not load mulligan background. Using solid color. ({e})")
        assets["mulligan_bg"] = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        assets["mulligan_bg"].fill((10, 15, 25))

    # Initialize Faction Powers for both players (if not already done by game_setup/game class)
    # The Game class __init__ doesn't set faction_power instances, so we do it here
    from power import FACTION_POWERS as FACTION_POWERS_FACTORY
    # Create fresh instances for both players (avoid shared mutable state across games)
    if game.player1.faction in FACTION_POWERS_FACTORY and not game.player1.faction_power:
        game.player1.faction_power = type(FACTION_POWERS_FACTORY[game.player1.faction])()

    if game.player2.faction in FACTION_POWERS_FACTORY and not game.player2.faction_power:
        game.player2.faction_power = type(FACTION_POWERS_FACTORY[game.player2.faction])()

    game.start_game()

    # === MULLIGAN PHASE (Separate screen before main game) ===
    mulligan_selected = []
    mulligan_clock = pygame.time.Clock()

    # Play ring transport sound when entering mulligan phase
    from sound_manager import get_sound_manager
    get_sound_manager().play_ring_transport_sound(volume=0.7)

    while game.game_state == "mulligan":
        dt = mulligan_clock.tick(60)

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check mulligan button click
                if cfg.MULLIGAN_BUTTON_RECT.collidepoint(event.pos):
                    num_selected = len(mulligan_selected)
                    if num_selected >= 2 and num_selected <= 5:
                        # Player mulligan
                        game.mulligan(game.player1, mulligan_selected)
                        mulligan_selected = []

                        # AI mulligan
                        if not LAN_MODE:
                            from ai_opponent import AIStrategy
                            ai_strategy = AIStrategy(game, game.player2)
                            ai_cards = ai_strategy.decide_mulligan()
                            game.mulligan(game.player2, ai_cards)

                        # End mulligan phase
                        game.end_mulligan_phase()
                    else:
                        print("Must select at least 2 cards for mulligan!")
                else:
                    # Check card clicks
                    total_cards = len(game.player1.hand)
                    card_w = cfg.MULLIGAN_CARD_WIDTH
                    card_h = cfg.MULLIGAN_CARD_HEIGHT
                    card_spacing = int(card_w * 0.125)
                    total_width = total_cards * card_w + (total_cards - 1) * card_spacing
                    start_x = (SCREEN_WIDTH - total_width) // 2 if total_width < SCREEN_WIDTH else cfg.HAND_REGION_LEFT
                    card_y = SCREEN_HEIGHT // 2 - card_h // 2

                    for i, card in enumerate(game.player1.hand):
                        card_x = start_x + i * (card_w + card_spacing)
                        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
                        if card_rect.collidepoint(event.pos):
                            if card in mulligan_selected:
                                mulligan_selected.remove(card)
                            else:
                                mulligan_selected.append(card)
                            break

        # Draw mulligan screen with background
        screen.blit(assets["mulligan_bg"], (0, 0))

        # Title
        title_text = cfg.SCORE_FONT.render("Mulligan Phase", True, cfg.WHITE)
        screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, int(SCREEN_HEIGHT * 0.1)))

        subtitle_text = cfg.UI_FONT.render("Select 2-5 cards to redraw, then click Redraw", True, cfg.WHITE)
        screen.blit(subtitle_text, (SCREEN_WIDTH // 2 - subtitle_text.get_width() // 2, int(SCREEN_HEIGHT * 0.15)))

        # Draw hand
        from render_engine import draw_hand
        draw_hand(screen, game.player1, None, mulligan_selected)

        # Draw mulligan button
        board_renderer.draw_mulligan_button(screen, mulligan_selected)

        display_manager.gpu_flip()

    # === END MULLIGAN PHASE ===

    # Start space battle for first round
    ambient_effects.start_round(round_number=1)

    # Show leader matchup animation after mulligan
    if not LAN_MODE:
        from leader_matchup import LeaderMatchupAnimation
        matchup_anim = LeaderMatchupAnimation(game.player1.leader, game.player2.leader, SCREEN_WIDTH, SCREEN_HEIGHT)
        clock_matchup = pygame.time.Clock()
        while not matchup_anim.finished:
            dt_matchup = clock_matchup.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_SPACE:
                        matchup_anim.finished = True

            matchup_anim.update(dt_matchup)
            matchup_anim.draw(screen)
            display_manager.gpu_flip()

        # Show game start animation
        transitions.show_game_start_animation(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)

    # Start battle music for Round 1
    battle_music.set_battle_music_round(1, immediate=True)

    # Initialize chat panel for LAN mode
    lan_chat_panel = None
    if LAN_MODE and LAN_CONTEXT:
        from lan_chat import LanChatPanel
        
        # Callback: When chat message arrives/sent, push to Game History
        def push_chat_to_history(prefix, text, color):
            owner = "player" if prefix == "You" else "ai"
            game.add_history_event("chat", f"{prefix}: {text}", owner, icon='"')

        lan_chat_panel = LanChatPanel(
            LAN_CONTEXT.session,
            LAN_CONTEXT.role,
            max_lines=12,
            on_message=push_chat_to_history,
            peer_name=game.player2.name,
        )
        
        lan_chat_panel.add_message("System", f"Connected as {LAN_CONTEXT.role}. Type 'T' to chat!")

    # --- Build centralized game loop state ---
    from animations import AITurnAnimation
    hud_pass_button_size = max(80, int(SCREEN_HEIGHT * 0.04))

    state = GameLoopState(
        game=game,
        ai_controller=ai_controller,
        network_proxy=network_proxy,
        menu_action=menu_action,
        unlock_system=unlock_system,
        anim_manager=anim_manager,
        ambient_effects=ambient_effects,
        assets=assets,
        clock=pygame.time.Clock(),
        lan_chat_panel=lan_chat_panel,
        ui_state=UIState.PLAYING,
        previous_round=game.round_number,
        mulligan_remote_done=not LAN_MODE,
        hud_pass_button_rect=pygame.Rect(
            HUD_LEFT + (HUD_WIDTH - hud_pass_button_size) // 2,
            cfg.pct_y(0.94) - hud_pass_button_size // 2,
            hud_pass_button_size,
            hud_pass_button_size
        ),
        ai_turn_anim=AITurnAnimation(SCREEN_WIDTH, SCREEN_HEIGHT),
        fullscreen=display_manager.FULLSCREEN,
    )

    # Wire discard → disintegration effect callback
    def _discard_callback(card, color_variant='default'):
        """Spawn CardDisintegrationEffect at card's last rendered position."""
        card_img = getattr(card, 'image', None)
        card_rect = getattr(card, 'rect', None)
        if card_img and card_rect:
            anim_manager.add_effect(
                CardDisintegrationEffect(card_img, card_rect.x, card_rect.y,
                                         color_variant=color_variant)
            )
    game._on_discard = _discard_callback

    # Wire card-play → materialization effect callback
    def _card_played_callback(card, row_name, target_player):
        """Spawn CardMaterializationEffect at the row where card was placed."""
        card_img = getattr(card, 'image', None)
        if not card_img:
            return
        # Determine row rect based on which player's board it landed on
        if target_player == game.player1:
            row_rect = cfg.PLAYER_ROW_RECTS.get(row_name)
        else:
            row_rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
        if row_rect:
            # Position at right edge of row (where new card appears)
            card_w, card_h = card_img.get_size()
            x = row_rect.right - card_w - 5
            y = row_rect.centery - card_h // 2
            anim_manager.add_effect(
                CardMaterializationEffect(card_img, x, y)
            )
    game._on_card_played = _card_played_callback

    while state.running:
        # Check for game restart or main menu request
        if getattr(game, 'restart_requested', False):
            battle_music.stop_battle_music()
            # Rematch: restart with same faction/leader setup
            rematch_data = {
                'player_faction': game.player1.faction,
                'player_leader': game.player1.leader,
                'ai_faction': game.player2.faction,
                'ai_leader': game.player2.leader,
            }
            state.restart_requested = True
            state.running = False
            continue
        if getattr(game, 'main_menu_requested', False):
            battle_music.stop_battle_music()
            state.restart_requested = True
            state.running = False
            continue

        sync_fullscreen_from_surface()
        # CRITICAL: Update screen reference every frame (gets recreated on fullscreen toggle)
        screen = display_manager.screen
        dt = state.clock.tick(144)
        if display_manager.gpu_renderer:
            display_manager.gpu_renderer.update(dt)
        battle_music.update_battle_music()

        # Update hand reveal timers
        for p in [game.player1, game.player2]:
            if p.hand_revealed and p.hand_reveal_timer > 0:
                p.hand_reveal_timer -= dt / 1000.0
                if p.hand_reveal_timer <= 0:
                    p.hand_revealed = False
                    p.hand_reveal_timer = 0
                    game.add_history_event("system", f"{p.name}'s hand is no longer revealed", "ai", icon="👁️")

        # Poll chat messages in LAN mode
        if state.lan_chat_panel:
            state.lan_chat_panel.poll_session()

        # Check for LAN disconnect
        if LAN_MODE and LAN_CONTEXT:
            if not LAN_CONTEXT.session.is_connected():
                # Show disconnect overlay with countdown
                _show_disconnect_overlay(
                    screen, SCREEN_WIDTH, SCREEN_HEIGHT,
                    reason="opponent_disconnected",
                    countdown_seconds=10
                )
                LAN_CONTEXT.session.close()
                battle_music.stop_battle_music()
                state.restart_requested = True
                state.running = False
                continue

        # Handle remote mulligan selections in LAN mode (non-blocking per-frame poll)
        if LAN_MODE and LAN_CONTEXT and game.game_state == "mulligan" and not state.mulligan_remote_done:
            if not hasattr(state, '_mulligan_start_time'):
                state._mulligan_start_time = pygame.time.get_ticks()

            # Check timeout
            if pygame.time.get_ticks() - state._mulligan_start_time > cfg.MULLIGAN_TIMEOUT:
                print("WARNING: Mulligan timeout reached, proceeding without remote mulligan")
                state.mulligan_remote_done = True
            else:
                # Non-blocking: check one message per frame
                msg = LAN_CONTEXT.session.receive()
                if msg:
                    try:
                        parsed = parse_message(msg)
                        msg_type = parsed.get("type")
                        if msg_type == LanMessageType.MULLIGAN.value:
                            payload = parsed.get("payload", {})
                            indices = payload.get("indices", [])
                            remote_cards = []
                            for idx in indices:
                                if isinstance(idx, int) and 0 <= idx < len(game.player2.hand):
                                    remote_cards.append(game.player2.hand[idx])
                            if remote_cards:
                                game.mulligan(game.player2, remote_cards)
                            state.mulligan_remote_done = True
                        else:
                            # Not a mulligan message — put back for game logic
                            LAN_CONTEXT.session.inbox.put(parsed)
                    except ValueError:
                        pass  # Skip malformed messages


        if getattr(game, "history_dirty", False):
            if not state.history_manual_scroll:
                state.history_scroll_offset = 0
            game.history_dirty = False
        state.history_entry_hitboxes = []
        state.player_ability_ready = not game.leader_ability_used.get(game.player1, False)
        state.ai_ability_ready = not game.leader_ability_used.get(game.player2, False)
        
        # Check for round changes and reset space battle WITH COOL TRANSITION
        if game.round_number != state.previous_round:
            # Hide CRT scanlines during transitions so they don't bleed through
            gpu = display_manager.gpu_renderer
            if gpu and gpu.enabled:
                crt = gpu.get_effect("crt_hologram")
                if crt:
                    crt.set_uniform('panel_rect', (0.0, 0.0, 0.0, 0.0))

            # Step 1: Cards sweep off the board (before showing winner)
            if state.previous_round >= 1:
                transitions.create_card_sweep_animation(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT, direction="up")
            
            # Step 2: Show round winner announcement with screen shake
            if hasattr(game, 'round_winner'):
                transitions.show_round_winner_announcement(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Step 3: Hyperspace transition
            player_lost_both = (game.player1.rounds_won == 0 and game.player2.rounds_won == 2)
            
            if game.round_number == 2:
                transition_text = "ENTERING HYPERSPACE..."
                transitions.create_hyperspace_transition(screen, SCREEN_WIDTH, SCREEN_HEIGHT, game.round_number, transition_text)
            elif game.round_number == 3:
                if player_lost_both:
                    from animations import create_black_hole_defeat_transition
                    create_black_hole_defeat_transition(screen, SCREEN_WIDTH, SCREEN_HEIGHT)
                else:
                    transition_text = "EMERGING NEAR PLANET..."
                    transitions.create_hyperspace_transition(screen, SCREEN_WIDTH, SCREEN_HEIGHT, game.round_number, transition_text)
            else:
                transition_text = f"ROUND {game.round_number}"
                transitions.create_hyperspace_transition(screen, SCREEN_WIDTH, SCREEN_HEIGHT, game.round_number, transition_text)
            
            state.ambient_effects.end_round()
            state.ambient_effects.start_round(round_number=game.round_number)
            state.previous_round = game.round_number

            # Update battle music for new round (more intense each round)
            battle_music.set_battle_music_round(game.round_number, immediate=True)
    
        # Check for weather changes and add row effects
        if game.weather_active != state.previous_weather:
            # Clear old weather effects
            state.anim_manager.clear_row_weather()
            
            # Add new weather effects for affected rows
            for row_name, is_active in game.weather_active.items():
                if is_active:
                    target_flag = game.weather_row_targets.get(row_name)
                    weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                    
                    if target_flag in ("player1", "both"):
                        player_row_rect = cfg.PLAYER_ROW_RECTS.get(row_name)
                        if player_row_rect:
                            state.anim_manager.add_row_weather(weather_type, player_row_rect, SCREEN_WIDTH)
                    if target_flag in ("player2", "both"):
                        opponent_row_rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                        if opponent_row_rect:
                            state.anim_manager.add_row_weather(weather_type, opponent_row_rect, SCREEN_WIDTH)
            
            # Handle Clear Weather - show it on all rows for the black hole effect
            if any(game.current_weather_types.get(row) == "Wormhole Stabilization" for row in ["close", "ranged", "siege"]):
                # Show clear weather effect on middle row for dramatic center effect
                middle_row_rect = cfg.PLAYER_ROW_RECTS.get("ranged")  # Use ranged as middle
                if middle_row_rect:
                    state.anim_manager.add_row_weather("Wormhole Stabilization", middle_row_rect, SCREEN_WIDTH)
            
            state.previous_weather = game.weather_active.copy()
    
        # Reset AI ability flag when it becomes player1's turn
        if game.current_player == game.player1:
            state.ai_ability_tried = False

        # AI leader ability - auto-activate when appropriate (e.g., Apophis weather strike)
        # Only try once per turn to avoid spam for leaders without implemented abilities
        if (game.game_state == "playing"
                and game.current_player == game.player2
                and not game.player2.has_passed
                and not state.ai_ability_tried
                and game.can_use_leader_ability(game.player2)):
            state.ai_ability_tried = True  # Only try once per turn
            ability_result = game.activate_leader_ability(game.player2)
            if ability_result:
                ability_name = ability_result.get("ability", game.player2.leader.get('ability', 'Leader Ability'))
                if ability_result.get("requires_ui") and ability_name == "Ancient Knowledge":
                    revealed = ability_result.get("revealed_cards") or []
                    if revealed:
                        chosen_card = max(revealed, key=lambda c: getattr(c, "power", 0))
                        game.catherine_play_chosen_card(game.player2, chosen_card)
                elif ability_result.get("requires_ui") and ability_name == "Eidetic Memory":
                    # AI Jonas Quinn - auto-choose highest power card
                    revealed = ability_result.get("revealed_cards") or []
                    if revealed:
                        chosen_card = max(revealed, key=lambda c: getattr(c, "power", 0))
                        game.jonas_memorize_card(game.player2, chosen_card)
                elif ability_result.get("requires_ui") and ability_name == "System Lord's Cunning":
                    # AI Ba'al - auto-choose highest power card from discard
                    revealed = ability_result.get("revealed_cards") or []
                    if revealed:
                        chosen_card = max(revealed, key=lambda c: getattr(c, "power", 0))
                        game.baal_resurrect_card(game.player2, chosen_card)
                state.anim_manager.add_effect(create_ability_animation(
                    ability_name,
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 3
                ))
                for row_name in ability_result.get("rows", []):
                    weather_target = game.weather_row_targets.get(row_name, "both")
                    weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                    if weather_target in ("player1", "both"):
                        rect = cfg.PLAYER_ROW_RECTS.get(row_name)
                        if rect:
                            state.anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=cfg.ANIM_STARGATE, faction=game.player2_faction))
                            # Add row weather visual effect (meteorites, nebula, etc.)
                            state.anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                    if weather_target in ("player2", "both"):
                        rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                        if rect:
                            state.anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=cfg.ANIM_STARGATE, faction=game.player2_faction))
                            # Add row weather visual effect (meteorites, nebula, etc.)
                            state.anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
    
        # Update animations
        state.anim_manager.update(dt)
    
        # Check if Hathor's ability animation is complete
        if hasattr(game, 'hathor_steal_info') and game.hathor_steal_info:
            # Check if the animation is complete
            animation_complete = True
            for animation in state.anim_manager.animations:
                if isinstance(animation, HathorStealAnimation) and not animation.finished:
                    animation_complete = False
                    break
            
            if animation_complete:
                # Clear the steal info
                game.hathor_steal_info = None
        
        state.ambient_effects.update(dt)
        state.drag_pulse += dt * 0.005
        if state.dragging_card:
            state.drag_pickup_flash = max(0.0, state.drag_pickup_flash - dt / 500.0)
        else:
            state.drag_pickup_flash = max(0.0, state.drag_pickup_flash - dt / 350.0)
            state.drag_velocity *= 0.9
        state.drag_trail_emit_ms = max(0, state.drag_trail_emit_ms - dt)
        for blob in state.drag_trail:
            blob["alpha"] -= dt * 0.35
            blob["width_scale"] += dt * 0.0008
            blob["height_scale"] += dt * 0.0006
        state.drag_trail = [b for b in state.drag_trail if b["alpha"] > 0]
        if state.dragging_card:
            if state.drag_trail_emit_ms <= 0:
                state.drag_trail.append({
                    "pos": state.dragging_card.rect.center,
                    "alpha": 130,
                    "width_scale": 1.0 + min(0.25, abs(state.drag_velocity.x) * 0.04),
                    "height_scale": 1.0 + min(0.2, abs(state.drag_velocity.y) * 0.03),
                    "color": get_row_color(state.dragging_card.row)
                })
                state.drag_trail_emit_ms = 45
    
        # Update card hover scale (instant snap for 1440p performance)
        state.card_hover_scale = state.target_hover_scale
        
        # Update Iris Power effect
        if state.faction_power_effect:
            if not state.faction_power_effect.update(dt):
                state.faction_power_effect = None
        
        # Update Ring Transportation animation
        if state.ring_transport_animation:
            if not state.ring_transport_animation.update(dt):
                # Animation complete
                state.ring_transport_animation = None
                if game.player1.ring_transportation:
                    game.player1.ring_transportation.complete_animation()
        
        # Update Iris Power UI hover states
        mouse_pos = pygame.mouse.get_pos()
        
        # Check if waiting for opponent (LAN mode)
        state.waiting_for_opponent = False
        if LAN_MODE and game.current_player != game.player1 and game.game_state != "game_over":
            state.waiting_for_opponent = True
    
        # Event handling (extracted to event_handler.py)
        handle_events(state, game, screen, dt)

        # Leader ability triggers (at start of player's turn)
        if game.current_player == game.player1 and game.game_state == "playing" and not game.player1.has_passed:
            # Jonas Quinn: See cards drawn by opponent (auto-trigger when opponent draws)
            if game.player1.leader and "Jonas" in game.player1.leader.get('name', ''):
                # Show overlay if opponent has drawn cards (not starting hand)
                if game.opponent_drawn_cards:
                    state.ui_state = UIState.JONAS_PEEK
            
            # Vala: Look at 3 cards, keep 1 (once per round, manual trigger with V key)
            # Ba'al Clone: Clone highest unit (once per round, manual trigger with B key)
            # Thor: Move unit (once per round, manual trigger with T key)
        
        # Simple AI for Player 2 - WITH SMOOTH ANIMATIONS
        # Skip AI animations in LAN mode - opponent is a real human
        if game.current_player == game.player2 and game.game_state == "playing" and not LAN_MODE:
            if not state.ai_turn_in_progress:
                # Start AI turn animation
                state.ai_turn_anim.start_thinking()
                state.ai_turn_in_progress = True
                state.ai_card_to_play = None
                state.ai_row_to_play = None
            
            # Update AI animation
            ai_result = state.ai_turn_anim.update(dt)
            
            if ai_result == "thinking_done":
                # AI has finished thinking, get the decision
                ai_board_before = {row: len(cards) for row, cards in game.player2.board.items()}
    
                # Check if faction power was available before AI decision
                ai_power_available_before = (game.player2.faction_power and
                                             game.player2.faction_power.is_available())
    
                # Get AI decision without executing it yet
                card_to_play, row_to_play = state.ai_controller.choose_move()
    
                # Check if AI used faction power
                ai_power_available_after = (game.player2.faction_power and
                                            game.player2.faction_power.is_available())
                ai_used_faction_power = ai_power_available_before and not ai_power_available_after
    
                if card_to_play:
                    # Store the decision
                    state.ai_card_to_play = card_to_play
                    state.ai_row_to_play = row_to_play
                    # Find card index in hand for animation
                    try:
                        card_index = game.player2.hand.index(card_to_play)
                        state.ai_selected_card_index = card_index
                        state.ai_turn_anim.start_selecting(card_index)
                    except ValueError:
                        # Card not in hand, skip animation
                        state.ai_selected_card_index = None
                        state.ai_turn_anim.finish()
                        state.ai_turn_in_progress = False
                else:
                    state.ai_selected_card_index = None
    
                    # Check if AI used faction power - trigger animation!
                    if ai_used_faction_power:
                        # Create faction power effect animation
                        state.faction_power_effect = FactionPowerEffect(
                            game.player2.faction,
                            SCREEN_WIDTH // 2,
                            SCREEN_HEIGHT // 2,
                            SCREEN_WIDTH,
                            SCREEN_HEIGHT
                        )
                        state.anim_manager.add_effect(state.faction_power_effect)
    
                        # Add history event for AI faction power use
                        game.add_history_event(
                            "faction_power",
                            f"{game.player2.name} used {game.player2.faction_power.name}",
                            "ai"
                        )
    
                        # Add Iris closing animation for Tau'ri Gate Shutdown
                        if game.player2.faction == FACTION_TAURI:
                            from animations import IrisClosingEffect
                            iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                            state.anim_manager.add_effect(iris_anim)
    
                    # AI passes or uses power
                    state.ai_turn_anim.finish()
                    if not game.player2.has_passed:
                        # Only switch turn if AI used power (not pass)
                        # pass_turn() already calls switch_turn() internally
                        game.last_turn_actor = game.player2
                        game.switch_turn()
                    state.ai_turn_in_progress = False
            
            elif ai_result == "selecting_done":
                # Start playing animation
                if state.ai_card_to_play and state.ai_row_to_play:
                    total_cards = len(game.player2.hand)
                    start_center = get_opponent_hand_card_center(total_cards, state.ai_selected_card_index)
                    ability = state.ai_card_to_play.ability or ""
                    target_rects = cfg.PLAYER_ROW_RECTS if (is_spy(state.ai_card_to_play) or state.ai_card_to_play.row == "weather") else cfg.OPPONENT_ROW_RECTS
                    target_rect = target_rects.get(state.ai_row_to_play)
                    if not target_rect:
                        # Fallback to any matching row rect
                        target_rect = cfg.PLAYER_ROW_RECTS.get(state.ai_row_to_play) or cfg.OPPONENT_ROW_RECTS.get(state.ai_row_to_play)
                    end_center = (target_rect.centerx, target_rect.centery) if target_rect else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    if state.ai_card_to_play.image:
                        state.anim_manager.add_effect(AICardPlayAnimation(state.ai_card_to_play.image, start_center, end_center))
                state.ai_turn_anim.start_playing(state.ai_row_to_play)
            
            elif ai_result == "playing_done":
                # Actually play the card
                if state.ai_card_to_play and state.ai_row_to_play:
                    ability = state.ai_card_to_play.ability or ""

                    # Check if player's Iris is active before playing
                    iris_was_active = (hasattr(game.player1, 'iris_defense') and
                                       game.player1.iris_defense.is_active())

                    # Play the card
                    game.play_card(state.ai_card_to_play, state.ai_row_to_play)
                    state.ai_selected_card_index = None

                    # Check if card was blocked by Iris (iris was active, now deactivated)
                    iris_blocked = iris_was_active and not game.player1.iris_defense.is_active()
                    if iris_blocked:
                        # Iris already called switch_turn(); skip animations and resolving
                        from animations import IrisClosingEffect
                        iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                        state.anim_manager.add_effect(iris_anim)
                        state.ai_turn_anim.finish()
                        state.ai_turn_in_progress = False
                    else:
                        # Card was successfully played - show animations
                        if state.ai_row_to_play == 'siege':
                            state.ambient_effects.add_ship(game.player2.faction, state.ai_card_to_play.name, is_player=False)

                        target_rect = cfg.OPPONENT_ROW_RECTS.get(state.ai_row_to_play)
                        effect_x = target_rect.centerx if target_rect else SCREEN_WIDTH // 2
                        effect_y = target_rect.centery if target_rect else SCREEN_HEIGHT // 4

                        weather_visual_applied = False
                        if state.ai_card_to_play.row == "weather":
                            weather_visual_applied = True
                            ability_lower = ability.lower()
                            if "wormhole stabilization" in ability_lower:
                                state.anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                            else:
                                state.anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_CARD_FLIP, faction=game.player2_faction))
                                if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                                    for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                        row_rect = rects.get(state.ai_row_to_play)
                                        if row_rect:
                                            state.anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))

                        # Check for Naquadah Overload
                        if not weather_visual_applied and has_ability(state.ai_card_to_play, Ability.NAQUADAH_OVERLOAD):
                            for player, destroyed_row in game.last_scorch_positions:
                                if player == game.player1:
                                    row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                                else:
                                    row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)
                                if row_rect:
                                    state.anim_manager.add_effect(NaquadahExplosionEffect(
                                        SCREEN_WIDTH // 2,
                                        row_rect.centery,
                                        duration=cfg.ANIM_MAJOR_EFFECT
                                    ))
                            game.last_scorch_positions = []
                        elif not weather_visual_applied and is_hero(state.ai_card_to_play):
                            hero_anim = create_hero_animation(state.ai_card_to_play.name, effect_x, effect_y)
                            state.anim_manager.add_effect(hero_anim)
                            state.anim_manager.add_effect(LegendaryLightningEffect(state.ai_card_to_play))
                        elif not weather_visual_applied:
                            ability_triggered = False

                            # Check for card-specific animations (replicator swarm, etc.)
                            if add_special_card_effect(state.ai_card_to_play, effect_x, effect_y, state.anim_manager, SCREEN_WIDTH, SCREEN_HEIGHT, game=game):
                                ability_triggered = True

                            if not ability_triggered:
                                for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones",
                                                       "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement"]:
                                    if special_ability in ability:
                                        ability_anim = create_ability_animation(ability, effect_x, effect_y)
                                        state.anim_manager.add_effect(ability_anim)
                                        ability_triggered = True
                                        break

                            if not ability_triggered:
                                stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_CARD_FLIP, faction=game.player2_faction)
                                state.anim_manager.add_effect(stargate_effect)

                            if state.ai_card_to_play.row == "special":
                                add_special_card_effect(
                                    state.ai_card_to_play,
                                    effect_x,
                                    effect_y,
                                    state.anim_manager,
                                    SCREEN_WIDTH,
                                    SCREEN_HEIGHT,
                                    game=game
                                )

                        state.ai_turn_anim.start_resolving()
            
            elif ai_result == "resolving_done":
                # Recalculate scores
                game.player1.calculate_score()
                game.player2.calculate_score()
    
                # Check if AI should use Iris Defense (before switching turn)
                if (hasattr(state.ai_controller, 'strategy') and
                    state.ai_controller.strategy.should_use_iris_defense()):
                    # AI activates Iris Defense
                    game.player2.iris_defense.activate()
                    # Trigger Iris closing animation
                    from animations import IrisClosingEffect
                    iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    state.anim_manager.add_effect(iris_anim)
                    # Add history event
                    game.add_history_event(
                        "special",
                        f"{game.player2.name} activated Iris Defense!",
                        "ai",
                        icon="[#]"
                    )
    
                # Finish turn
                state.ai_turn_anim.finish()
                game.switch_turn()
                state.ai_turn_in_progress = False
                state.ai_selected_card_index = None
    
        # LAN opponent turn handling
        elif game.current_player == game.player2 and game.game_state == "playing" and LAN_MODE:
            # Check if faction power was available before polling
            lan_power_available_before = (game.player2.faction_power and
                                          game.player2.faction_power.is_available())
    
            # Poll for network message from opponent
            was_passed = game.player2.has_passed
            card_to_play, row_to_play = state.ai_controller.choose_move()
            
            if not was_passed and game.player2.has_passed:
                # pass_turn() already called switch_turn() internally
                continue
    
            # Check if opponent used faction power
            lan_power_available_after = (game.player2.faction_power and
                                         game.player2.faction_power.is_available())
            if lan_power_available_before and not lan_power_available_after:
                # Opponent used faction power - trigger animation!
                state.faction_power_effect = FactionPowerEffect(
                    game.player2.faction,
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 2,
                    SCREEN_WIDTH,
                    SCREEN_HEIGHT
                )
                state.anim_manager.add_effect(state.faction_power_effect)
    
                # Add Iris closing animation for Tau'ri Gate Shutdown
                if game.player2.faction == FACTION_TAURI:
                    from animations import IrisClosingEffect
                    iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    state.anim_manager.add_effect(iris_anim)
                
                game.last_turn_actor = game.player2
                game.switch_turn()
                continue
    
            if card_to_play and row_to_play:
                # Opponent played a card - process it with animations
                ability = card_to_play.ability or ""
    
                # Play the card
                game.play_card(card_to_play, row_to_play)
    
                # Check if opponent played a siege card for space battle
                if row_to_play == 'siege':
                    state.ambient_effects.add_ship(game.player2.faction, card_to_play.name, is_player=False)
    
                # Trigger visual effect for the play
                target_rect = cfg.OPPONENT_ROW_RECTS.get(row_to_play)
                if is_spy(card_to_play) or card_to_play.row == "weather":
                    target_rect = cfg.PLAYER_ROW_RECTS.get(row_to_play) or target_rect
                effect_x = target_rect.centerx if target_rect else SCREEN_WIDTH // 2
                effect_y = target_rect.centery if target_rect else SCREEN_HEIGHT // 4
                if card_to_play.row == "special":
                    add_special_card_effect(
                        card_to_play,
                        effect_x,
                        effect_y,
                        state.anim_manager,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT,
                        game=game
                    )

                weather_visual_applied = False
                if card_to_play.row == "weather":
                    weather_visual_applied = True
                    ability_lower = ability.lower()
                    if "wormhole stabilization" in ability_lower:
                        state.anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                    else:
                        state.anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_CARD_FLIP, faction=game.player2_faction))
                        if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                            for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                row_rect = rects.get(row_to_play)
                                if row_rect:
                                    state.anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))
    
                # Check for Naquadah Overload
                if not weather_visual_applied and has_ability(card_to_play, Ability.NAQUADAH_OVERLOAD):
                    for player, destroyed_row in game.last_scorch_positions:
                        if player == game.player1:
                            row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                        else:
                            row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)
                        if row_rect:
                            state.anim_manager.add_effect(NaquadahExplosionEffect(
                                SCREEN_WIDTH // 2,
                                row_rect.centery,
                                duration=cfg.ANIM_MAJOR_EFFECT
                            ))
                    game.last_scorch_positions = []
                elif not weather_visual_applied and is_hero(card_to_play):
                    hero_anim = create_hero_animation(card_to_play.name, effect_x, effect_y)
                    state.anim_manager.add_effect(hero_anim)
                    state.anim_manager.add_effect(LegendaryLightningEffect(card_to_play))
                elif not weather_visual_applied:
                    # Check for special ability animations (same as player)
                    ability_triggered = False

                    # Check for card-specific animations (replicator swarm, etc.)
                    if add_special_card_effect(card_to_play, effect_x, effect_y, state.anim_manager, SCREEN_WIDTH, SCREEN_HEIGHT, game=game):
                        ability_triggered = True

                    if not ability_triggered:
                        for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones",
                                               "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement"]:
                            if special_ability in ability:
                                ability_anim = create_ability_animation(ability, effect_x, effect_y)
                                state.anim_manager.add_effect(ability_anim)
                                ability_triggered = True
                                break

                    # Default stargate effect if no special ability
                    if not ability_triggered:
                        stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=cfg.ANIM_CARD_FLIP, faction=game.player2_faction)
                        state.anim_manager.add_effect(stargate_effect)

                # Recalculate scores
                game.player1.calculate_score()
                game.player2.calculate_score()
    
            # Note: If (None, None) returned, either opponent passed/used power (already handled),
            # or no message yet (keep polling next frame)
    
        # Check for score changes and trigger animations
        prev_p1_before = state.prev_p1_score
        prev_p2_before = state.prev_p2_score

        if game.player1.score != state.prev_p1_score or game.player2.score != state.prev_p2_score:
            # Check for row power surges (threshold >= 5)
            _surge_rects = {}
            for rn in ('close', 'ranged', 'siege'):
                pr = cfg.PLAYER_ROW_RECTS.get(rn)
                if pr:
                    _surge_rects[(0, rn)] = pr
                opr = cfg.OPPONENT_ROW_RECTS.get(rn)
                if opr:
                    _surge_rects[(1, rn)] = opr
            state.anim_manager.check_power_surge(game, _surge_rects)

        if game.player1.score != state.prev_p1_score:
            score_x = SCREEN_WIDTH - int(SCREEN_WIDTH * 0.052)
            p1_lead_gain = (prev_p1_before <= prev_p2_before) and (game.player1.score > game.player2.score)
            state.anim_manager.add_score_animation('p1', state.prev_p1_score, game.player1.score,
                                            score_x, SCREEN_HEIGHT // 2 + 50, lead_burst=p1_lead_gain)
            state.prev_p1_score = game.player1.score

        if game.player2.score != state.prev_p2_score:
            score_x = SCREEN_WIDTH - int(SCREEN_WIDTH * 0.052)
            p2_lead_gain = (prev_p2_before <= prev_p1_before) and (game.player2.score > game.player1.score)
            state.anim_manager.add_score_animation('p2', state.prev_p2_score, game.player2.score,
                                            score_x, SCREEN_HEIGHT // 2 - 50, lead_burst=p2_lead_gain)
            state.prev_p2_score = game.player2.score

        # Snapshot row powers for next frame's surge detection
        state.anim_manager.snapshot_row_powers(game)
    
        state.drag_hover_highlight = None
        drag_row_highlights = []
        if state.dragging_card and game.game_state == "playing":
            mouse_pos = pygame.mouse.get_pos()
            hover_alpha = 80
            ability = state.dragging_card.ability or ""
            if state.dragging_card.row == "weather":
                slot_hover = False
                for row_name, slot_rect in WEATHER_SLOT_RECTS.items():
                    slot_color = get_row_color(row_name)
                    drag_row_highlights.append({"rect": slot_rect, "color": slot_color, "alpha": 55})
                    if slot_rect.collidepoint(mouse_pos):
                        state.drag_hover_highlight = {"rect": slot_rect, "color": slot_color, "alpha": 150}
                        slot_hover = True
                hovered_row_name, hovered_rect = get_row_under_position(mouse_pos)
                target_rows = get_weather_target_rows(state.dragging_card, hovered_row_name)
                for row_name in target_rows:
                    color = get_row_color(row_name)
                    player_rect = cfg.PLAYER_ROW_RECTS.get(row_name)
                    opponent_rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                    if player_rect:
                        drag_row_highlights.append({"rect": player_rect, "color": color, "alpha": 70})
                    if opponent_rect:
                        drag_row_highlights.append({"rect": opponent_rect, "color": color, "alpha": 70})
                if not slot_hover and hovered_rect:
                    state.drag_hover_highlight = {"rect": hovered_rect, "color": get_row_color(hovered_row_name or "weather"), "alpha": 120}
            elif state.dragging_card.row == "special" and has_ability(state.dragging_card, Ability.COMMAND_NETWORK):
                for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
                    drag_row_highlights.append({"rect": slot_rect, "color": (255, 215, 0), "alpha": 80})
                    if slot_rect.collidepoint(mouse_pos):
                        state.drag_hover_highlight = {"rect": slot_rect, "color": (255, 215, 0), "alpha": 140}
            elif state.dragging_card.row == "special":
                for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                    for row_name, rect in rects.items():
                        if rect.collidepoint(mouse_pos):
                            state.drag_hover_highlight = {"rect": rect, "color": get_row_color(row_name), "alpha": 100}
                            break
                    if state.drag_hover_highlight:
                        break
            else:
                dragging_is_spy = is_spy(state.dragging_card)
                target_rects = cfg.OPPONENT_ROW_RECTS if dragging_is_spy else cfg.PLAYER_ROW_RECTS
                for row_name, rect in target_rects.items():
                    if rect.collidepoint(mouse_pos):
                        color = (255, 120, 120) if dragging_is_spy else get_row_color(row_name)
                        state.drag_hover_highlight = {"rect": rect, "color": color, "alpha": hover_alpha}
                        break
    
        drag_visual_state = {
            "trail": state.drag_trail,
            "velocity": state.drag_velocity,
            "pickup_boost": state.drag_pickup_flash,
            "pulse": state.drag_pulse
        }
    
        # --- Drawing (extracted to frame_renderer.py) ---
        render_frame(state, game, screen, dt, drag_visual_state)


    battle_music.stop_battle_music()

    # Reset CRT shader panel_rect so it doesn't bleed into the main menu
    gpu = display_manager.gpu_renderer
    if gpu and gpu.enabled:
        crt = gpu.get_effect("crt_hologram")
        if crt:
            crt.set_uniform('panel_rect', (0.0, 0.0, 0.0, 0.0))

    # If restart was requested, signal the outer loop
    if state.restart_requested:
        return "restart"

    return "quit"


def run_game():
    """Entry point that loops on restart instead of recursing."""
    while True:
        result = main()
        if result != "restart":
            break


if __name__ == "__main__":
    run_game()
    if display_manager.gpu_renderer:
        display_manager.gpu_renderer.cleanup()
    pygame.quit()
    sys.exit()
