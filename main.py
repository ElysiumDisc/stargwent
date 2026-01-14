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
    ReplicatorCrawlEffect,
    GoauldSymbioteAnimation,
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


def _draw_card_details(target_surface, card, rect):
    """Render card overlays (power pips and row icon)."""
    if card.row not in ["special", "weather"]:
        # Determine color based on buffs/debuffs
        if card.displayed_power > card.power:
            text_color = (100, 255, 100) # Green for buff
        elif card.displayed_power < card.power:
            text_color = (255, 100, 100) # Red for curse/damage
        else:
            text_color = cfg.WHITE # Default

        power_text = cfg.POWER_FONT.render(str(card.displayed_power), True, text_color)
        power_rect = power_text.get_rect(
            center=(rect.x + rect.width / 2, rect.y + rect.height - 20)
        )
        pygame.draw.rect(
            target_surface,
            (0, 0, 0, 150),
            power_rect.inflate(4, 4)
        )
        target_surface.blit(power_text, power_rect)


def _draw_drag_trail(surface, trail_entries):
    """Draw motion silhouettes that follow the dragged card."""
    if not trail_entries:
        return

    for blob in trail_entries:
        alpha = int(blob.get("alpha", 0))
        if alpha <= 0:
            continue

        width_scale = blob.get("width_scale", 1.0)
        height_scale = blob.get("height_scale", 1.0)
        width = max(4, int(CARD_WIDTH * width_scale))
        height = max(4, int(CARD_HEIGHT * height_scale))
        tint = blob.get("color", (180, 200, 255))
        trail_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        pygame.draw.rect(
            trail_surface,
            (tint[0], tint[1], tint[2], alpha),
            trail_surface.get_rect(),
            border_radius=18
        )
        pygame.draw.rect(
            trail_surface,
            (255, 255, 255, min(alpha, 140)),
            trail_surface.get_rect().inflate(-12, -12),
            border_radius=14
        )

        pos = blob.get("pos", (0, 0))
        surface.blit(
            trail_surface,
            (int(pos[0] - width // 2), int(pos[1] - height // 2))
        )


def add_special_card_effect(card, effect_x, effect_y, anim_manager, screen_width, screen_height):
    """Trigger unique animations for special cards matching lore/logic."""
    name_lower = (card.name or "").lower()
    ability_lower = (card.ability or "").lower()
    card_id = getattr(card, 'card_id', '') or ''

    if "thor" in name_lower or "remove all goa'uld" in ability_lower:
        anim_manager.add_effect(ThorsHammerPurgeEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "zero point module" in name_lower or "zpm" in name_lower or "double all your siege" in ability_lower:
        anim_manager.add_effect(ZPMSurgeEffect(effect_x, effect_y))
        return True
    if "communication device" in name_lower or "reveal opponent's hand" in ability_lower:
        anim_manager.add_effect(CommunicationRevealEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "merlin" in name_lower or "anti-ori" in name_lower:
        anim_manager.add_effect(MerlinAntiOriEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "dakara" in name_lower:
        anim_manager.add_effect(DakaraShockwaveEffect(effect_x, effect_y, screen_width, screen_height))
        return True
    if "naquadah" in name_lower or "overload" in ability_lower:
        anim_manager.add_effect(NaquadahExplosionEffect(effect_x, effect_y, duration=1500))
        return True
    if "replicator swarm" in name_lower:
        anim_manager.add_effect(ReplicatorCrawlEffect(screen_width, screen_height))
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
        "expires_at": pygame.time.get_ticks() + 5000,
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
    """
    Main game loop, but initialized with a specific LAN context.
    """
    # Set global LAN context
    global LAN_MODE, LAN_CONTEXT
    LAN_MODE = True
    LAN_CONTEXT = context
    
    # Initialize unlock system (needed for DeckManager)
    from unlocks import CardUnlockSystem
    unlock_system = CardUnlockSystem()
    
    # Initialize game with LAN context decks/leaders
    # Local player is player1, Remote player is player2
    player1_deck = [ALL_CARDS[cid] for cid in context.local.deck_ids if cid in ALL_CARDS]
    player2_deck = [ALL_CARDS[cid] for cid in context.remote.deck_ids if cid in ALL_CARDS]
    
    # Find leader cards
    from deck_builder import FACTION_LEADERS
    def find_leader(faction, leader_id):
        # Check base leaders
        for leader in FACTION_LEADERS.get(faction, []):
            if leader.get("card_id") == leader_id:
                return leader
        # Check unlockable leaders
        from content_registry import UNLOCKABLE_LEADERS
        if faction in UNLOCKABLE_LEADERS:
            for leader in UNLOCKABLE_LEADERS[faction]:
                if leader.get("card_id") == leader_id:
                    return leader
        # Fallback
        return FACTION_LEADERS.get(faction, [{}])[0]

    player1_leader = find_leader(context.local.faction, context.local.leader_id)
    player2_leader = find_leader(context.remote.faction, context.remote.leader_id)
    
    game = Game(
        player1_faction=context.local.faction,
        player1_deck=player1_deck,
        player1_leader=player1_leader,
        player2_faction=context.remote.faction,
        player2_deck=player2_deck,
        player2_leader=player2_leader,
        seed=context.seed
    )
    
    # Initialize Network Controller for player 2
    from lan_opponent import NetworkController, NetworkPlayerProxy
    network_controller = NetworkController(game, game.player2, context.session, context.role)
    network_proxy = NetworkPlayerProxy(context.session, context.role)
    
    # Assign controller to game logic variables used in main loop
    # We need to inject this into the main game loop scope
    # Ideally main() should be refactored to accept these, but for now we'll hijack the globals/locals
    # Actually, run_game_loop() is what we want to call, passing these.
    
    # Since main.py is a script, we'll reuse the logic by calling a shared loop function
    # But main() is currently monolithic.
    # We will run a modified version of the game loop here.
    
    # ... ACTUALLY, main() is huge. duplicating it is bad.
    # Refactoring main() into run_game_loop() is the right way, but risky for this task.
    # Instead, I will call the internal loop logic if I can expose it.
    
    # Let's look at how I can inject this.
    # The easiest way without huge refactor is to set global variables that main() checks?
    # No, main() creates its own Game object.
    
    # I will rename `main()` to `run_game_loop(game_instance=None, network_ctrl=None)` 
    # and have `main` call `run_game_loop()`.
    
    # But wait, I can't easily rename main() in one go if it's 5000 lines.
    # I will define run_game_with_context to essentially COPY the necessary setup and then run the loop.
    # OR, I can implement `run_game_loop` by extracting the while loop from `main`.
    
    # Given the constraints, I will assume `main.py` has a `main()` function that does everything.
    # I will implement `run_game_with_context` by modifying `main` to accept arguments.
    pass

def main(external_game=None, external_network=None):
    # ... existing main code ...
    # When creating game:
    if external_game:
        game = external_game
        ai_controller = external_network # This will be the network controller
    else:
        # ... existing game creation ...
        pass


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
    
    # Update global LAN context if needed (for chat panel etc)
    if menu_action == 'lan_game':
        # game_setup doesn't set global LAN_MODE/CONTEXT in main.py, we do it here
        if isinstance(ai_controller, NetworkController):
            LAN_MODE = True
            # We assume context is valid if we have a controller

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
    if game.player1.faction in FACTION_POWERS_FACTORY and not game.player1.faction_power:
        game.player1.faction_power = FACTION_POWERS_FACTORY[game.player1.faction]

    if game.player2.faction in FACTION_POWERS_FACTORY and not game.player2.faction_power:
        # Create separate instance for AI
        game.player2.faction_power = type(FACTION_POWERS_FACTORY[game.player2.faction])()

    game.start_game()

    # === MULLIGAN PHASE (Separate screen before main game) ===
    mulligan_selected = []
    mulligan_clock = pygame.time.Clock()
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

        pygame.display.flip()

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
            pygame.display.flip()

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
            on_message=push_chat_to_history
        )
        
        lan_chat_panel.add_message("System", f"Connected as {LAN_CONTEXT.role}. Type 'T' to chat!")

    selected_card = None
    dragging_card = None
    drag_offset = (0, 0)
    drag_target_x = 0
    drag_target_y = 0
    drag_velocity = Vector2()
    drag_trail = []
    drag_trail_emit_ms = 0
    drag_pickup_flash = 0.0
    drag_pulse = 0.0
    drag_hover_highlight = None
    card_hover_scale = 1.0
    target_hover_scale = 1.0
    hovered_card = None
    keyboard_hand_cursor = -1  # -1 means no keyboard selection, 0+ is index in hand
    keyboard_row_cursor = 0    # For selecting target row when playing a card
    keyboard_mode_active = False  # True when using keyboard to play cards
    keyboard_button_cursor = -1  # -1 = none, 0 = pass, 1 = faction power
    mulligan_selected = []
    mulligan_local_done = False
    mulligan_remote_done = not LAN_MODE
    inspected_card = None
    inspected_leader = None
    player_leader_rect = None
    ai_leader_rect = None
    player_ability_rect = None
    ai_ability_rect = None
    
    # UI State Machine Initialization
    ui_state = UIState.PLAYING
    
    # State Data Holders
    medic_card_played = None
    decoy_card_played = None
    ring_transport_animation = None
    ring_transport_selection = False
    ring_transport_button_rect = None
    decoy_drag_target = None
    decoy_valid_targets = []
    iris_button_rect = None
    previous_round = game.round_number
    previous_weather = {"close": False, "ranged": False, "siege": False}
    
    # Discard pile viewer data
    discard_scroll = 0
    discard_rect = None
    
    # Leader ability selection data
    vala_cards_to_choose = []
    catherine_cards_to_choose = []
    thor_selected_unit = None
    pending_leader_choice = None
    
    # History/column state
    history_scroll_offset = 0
    history_scroll_limit = 0
    history_manual_scroll = False
    history_entry_hitboxes = []
    history_panel_rect = None
    player_faction_button_rect = None
    player_ability_ready = False
    ai_ability_ready = False
    ai_faction_button_rect = None
    player_special_button_rect = None
    player_special_button_kind = None
    ai_special_button_rect = None
    ai_special_button_kind = None
    button_info_popup = None

    # Pass buttons (command bar + HUD)
    hud_pass_button_size = max(80, int(SCREEN_HEIGHT * 0.04))
    HUD_PASS_BUTTON_RECT = pygame.Rect(
        HUD_LEFT + (HUD_WIDTH - hud_pass_button_size) // 2,
        cfg.pct_y(0.94) - hud_pass_button_size // 2,
        hud_pass_button_size,
        hud_pass_button_size
    )
    
    faction_power_effect = None
    
    # Debug overlay toggle (F3 key)
    debug_overlay_enabled = False
    
    clock = pygame.time.Clock()
    
    # AI Turn Animation System
    from animations import AITurnAnimation
    ai_turn_anim = AITurnAnimation(SCREEN_WIDTH, SCREEN_HEIGHT)
    ai_turn_in_progress = False
    ai_card_to_play = None
    ai_row_to_play = None
    ai_selected_card_index = None

    running = True
    fullscreen = display_manager.FULLSCREEN

    while running:
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
            main(lan_game_data=rematch_data)
            return
        if getattr(game, 'main_menu_requested', False):
            battle_music.stop_battle_music()
            main()  # Return to main menu
            return

        sync_fullscreen_from_surface()
        # CRITICAL: Update screen reference every frame (gets recreated on fullscreen toggle)
        screen = display_manager.screen
        dt = clock.tick(144)
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
        if lan_chat_panel:
            lan_chat_panel.poll_session()

        # Check for LAN disconnect
        if LAN_MODE and LAN_CONTEXT:
            if not LAN_CONTEXT.session.is_connected():
                # Show disconnect message
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                screen.blit(overlay, (0, 0))

                font_large = pygame.font.SysFont("Arial", 60, bold=True)
                font_small = pygame.font.SysFont("Arial", 30)

                text1 = font_large.render("CONNECTION LOST", True, (255, 100, 100))
                text2 = font_small.render("Your opponent has disconnected", True, (200, 200, 200))
                text3 = font_small.render("Press any key to return to menu", True, (150, 150, 150))

                screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, SCREEN_HEIGHT // 2 - 80))
                screen.blit(text2, (SCREEN_WIDTH // 2 - text2.get_width() // 2, SCREEN_HEIGHT // 2))
                screen.blit(text3, (SCREEN_WIDTH // 2 - text3.get_width() // 2, SCREEN_HEIGHT // 2 + 60))

                pygame.display.flip()

                waiting = True
                while waiting:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                            waiting = False

                LAN_CONTEXT.session.close()
                battle_music.stop_battle_music()
                main()
                return

        # Handle remote mulligan selections in LAN mode
        if LAN_MODE and LAN_CONTEXT and game.game_state == "mulligan" and not mulligan_remote_done:
            mulligan_timeout = 30000
            mulligan_start_time = pygame.time.get_ticks()
            max_iterations = 1000
            iteration_count = 0

            while iteration_count < max_iterations:
                if pygame.time.get_ticks() - mulligan_start_time > mulligan_timeout:
                    print("WARNING: Mulligan timeout reached, proceeding without remote mulligan")
                    mulligan_remote_done = True
                    break

                iteration_count += 1
                msg = LAN_CONTEXT.session.receive()
                if not msg:
                    break
                try:
                    parsed = parse_message(msg)
                except ValueError:
                    continue

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
                    mulligan_remote_done = True
                    continue

                LAN_CONTEXT.session.inbox.put(parsed)
                break


        if getattr(game, "history_dirty", False):
            if not history_manual_scroll:
                history_scroll_offset = 0
            game.history_dirty = False
        history_entry_hitboxes = []
        player_ability_ready = not game.leader_ability_used.get(game.player1, False)
        ai_ability_ready = not game.leader_ability_used.get(game.player2, False)
        
        # Check for round changes and reset space battle WITH COOL TRANSITION
        if game.round_number != previous_round:
            # Step 1: Cards sweep off the board (before showing winner)
            if previous_round >= 1:
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
            
            ambient_effects.end_round()
            ambient_effects.start_round(round_number=game.round_number)
            previous_round = game.round_number

            # Update battle music for new round (more intense each round)
            battle_music.set_battle_music_round(game.round_number, immediate=True)
    
        # Check for weather changes and add row effects
        if game.weather_active != previous_weather:
            # Clear old weather effects
            anim_manager.clear_row_weather()
            
            # Add new weather effects for affected rows
            for row_name, is_active in game.weather_active.items():
                if is_active:
                    target_flag = game.weather_row_targets.get(row_name)
                    weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                    
                    if target_flag in ("player1", "both"):
                        player_row_rect = cfg.PLAYER_ROW_RECTS.get(row_name)
                        if player_row_rect:
                            anim_manager.add_row_weather(weather_type, player_row_rect, SCREEN_WIDTH)
                    if target_flag in ("player2", "both"):
                        opponent_row_rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                        if opponent_row_rect:
                            anim_manager.add_row_weather(weather_type, opponent_row_rect, SCREEN_WIDTH)
            
            # Handle Clear Weather - show it on all rows for the black hole effect
            if any(game.current_weather_types.get(row) == "Wormhole Stabilization" for row in ["close", "ranged", "siege"]):
                # Show clear weather effect on middle row for dramatic center effect
                middle_row_rect = cfg.PLAYER_ROW_RECTS.get("ranged")  # Use ranged as middle
                if middle_row_rect:
                    anim_manager.add_row_weather("Wormhole Stabilization", middle_row_rect, SCREEN_WIDTH)
            
            previous_weather = game.weather_active.copy()
    
        # AI leader ability - auto-activate when appropriate (e.g., Apophis weather strike)
        if (game.game_state == "playing"
                and game.current_player == game.player2
                and not game.player2.has_passed):
            ability_result = game.activate_leader_ability(game.player2)
            if ability_result:
                ability_name = ability_result.get("ability", game.player2.leader.get('ability', 'Leader Ability'))
                if ability_result.get("requires_ui") and ability_name == "Ancient Knowledge":
                    revealed = ability_result.get("revealed_cards") or []
                    if revealed:
                        chosen_card = max(revealed, key=lambda c: getattr(c, "power", 0))
                        game.catherine_play_chosen_card(game.player2, chosen_card)
                anim_manager.add_effect(create_ability_animation(
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
                            anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                            # Add row weather visual effect (meteorites, nebula, etc.)
                            anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                    if weather_target in ("player2", "both"):
                        rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                        if rect:
                            anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                            # Add row weather visual effect (meteorites, nebula, etc.)
                            anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
    
        # Update animations
        anim_manager.update(dt)
    
        # Check if Hathor's ability animation is complete
        if hasattr(game, 'hathor_steal_info') and game.hathor_steal_info:
            # Check if the animation is complete
            animation_complete = True
            for animation in anim_manager.animations:
                if isinstance(animation, HathorStealAnimation) and not animation.finished:
                    animation_complete = False
                    break
            
            if animation_complete:
                # Clear the steal info
                game.hathor_steal_info = None
        
        ambient_effects.update(dt)
        drag_pulse += dt * 0.005
        if dragging_card:
            drag_pickup_flash = max(0.0, drag_pickup_flash - dt / 500.0)
        else:
            drag_pickup_flash = max(0.0, drag_pickup_flash - dt / 350.0)
            drag_velocity *= 0.9
        drag_trail_emit_ms = max(0, drag_trail_emit_ms - dt)
        for blob in drag_trail[:]:
            blob["alpha"] -= dt * 0.35
            blob["width_scale"] += dt * 0.0008
            blob["height_scale"] += dt * 0.0006
            if blob["alpha"] <= 0:
                drag_trail.remove(blob)
        if dragging_card:
            if drag_trail_emit_ms <= 0:
                drag_trail.append({
                    "pos": dragging_card.rect.center,
                    "alpha": 130,
                    "width_scale": 1.0 + min(0.25, abs(drag_velocity.x) * 0.04),
                    "height_scale": 1.0 + min(0.2, abs(drag_velocity.y) * 0.03),
                    "color": get_row_color(dragging_card.row)
                })
                drag_trail_emit_ms = 45
    
        # Update card hover scale (instant snap for 1440p performance)
        card_hover_scale = target_hover_scale
        
        # Update Iris Power effect
        if faction_power_effect:
            if not faction_power_effect.update(dt):
                faction_power_effect = None
        
        # Update Ring Transportation animation
        if ring_transport_animation:
            if not ring_transport_animation.update(dt):
                # Animation complete
                ring_transport_animation = None
                if game.player1.ring_transportation:
                    game.player1.ring_transportation.complete_animation()
        
        # Update Iris Power UI hover states
        mouse_pos = pygame.mouse.get_pos()
        
        # Check if waiting for opponent (LAN mode)
        waiting_for_opponent = False
        if LAN_MODE and game.current_player != game.player1 and not game.game_over:
            waiting_for_opponent = True
    
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Handle chat input in LAN mode FIRST (takes priority except for ESC and F11)
                if lan_chat_panel and lan_chat_panel.active and event.key not in (pygame.K_ESCAPE, pygame.K_F11, pygame.K_F3):
                    lan_chat_panel.handle_event(event)
                    continue  # Skip other key handlers when typing in chat

                # F3 - Toggle debug overlay (zone boundaries + FPS counter)
                if event.key == pygame.K_F3:
                    # Toggle debug/FPS
                    DEBUG_MODE = not DEBUG_MODE
                    get_settings().set_show_fps(DEBUG_MODE)
                    print(f"Debug Mode: {DEBUG_MODE}")

                # Debug: Print all key presses
                elif event.key == pygame.K_F11:
                    print(f"🔑 DEBUG: F11 key detected (keycode: {event.key})")

                # ESC to toggle pause menu or close overlays
                if event.key == pygame.K_ESCAPE:
                    if inspected_card or inspected_leader:
                        inspected_card = None
                        inspected_leader = None
                    elif ui_state == UIState.DISCARD_VIEW:
                        ui_state = UIState.PLAYING
                        discard_scroll = 0
                    elif ui_state == UIState.JONAS_PEEK:
                        ui_state = UIState.PLAYING
                        # Clear the tracked cards after viewing
                        game.opponent_drawn_cards = []
                    elif ui_state == UIState.LAN_CHAT:
                        ui_state = UIState.PLAYING
                    elif game.game_state == "playing":
                        if ui_state == UIState.PAUSED:
                            ui_state = UIState.PLAYING
                        else:
                            ui_state = UIState.PAUSED
                
                # Toggle fullscreen with F11
                elif event.key == pygame.K_F11:
                    print(f"🔑 Fullscreen toggle requested. Current state: {display_manager.FULLSCREEN}")
                    toggle_fullscreen_mode()
                    fullscreen = display_manager.FULLSCREEN
                    
                    # Recalculate UI button positions for new resolution
                    hud_pass_button_size = max(80, int(SCREEN_HEIGHT * 0.04))
                    HUD_PASS_BUTTON_RECT = pygame.Rect(
                        HUD_LEFT + (HUD_WIDTH - hud_pass_button_size) // 2,
                        pct_y(0.94) - hud_pass_button_size // 2,
                        hud_pass_button_size,
                        hud_pass_button_size
                    )
                    cfg.MULLIGAN_BUTTON_RECT = pygame.Rect(
                        SCREEN_WIDTH - int(300 * SCALE_FACTOR),
                        SCREEN_HEIGHT - int(160 * SCALE_FACTOR),
                        int(200 * SCALE_FACTOR),
                        int(50 * SCALE_FACTOR)
                    )
                    
                    mode_label = "ON" if fullscreen else "OFF"
                    print(f"✓ Fullscreen: {mode_label} - Resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
                    print(f"  Scale Factor: {SCALE_FACTOR:.2f}")
                
                # F key = Play keyboard-selected or hovered card to its default row
                elif event.key == pygame.K_f:
                    if game.game_state == "playing" and game.current_player == game.player1 and ui_state == UIState.PLAYING:
                        # Get card to play: keyboard-selected or hovered
                        card_to_play = None
                        if keyboard_mode_active and keyboard_hand_cursor >= 0 and keyboard_hand_cursor < len(game.player1.hand):
                            card_to_play = game.player1.hand[keyboard_hand_cursor]
                        elif hovered_card and hovered_card in game.player1.hand:
                            card_to_play = hovered_card

                        if card_to_play:
                            # Determine default row
                            if card_to_play.row in ("close", "ranged", "siege"):
                                target_row = card_to_play.row
                            elif card_to_play.row == "agile":
                                target_row = "close"  # Default agile to close
                            elif card_to_play.row == "weather":
                                target_row = "close"  # Default weather to close row
                            elif card_to_play.row == "special":
                                # Special cards need specific handling
                                if "Ring Transport" in (card_to_play.ability or ""):
                                    target_row = None  # Skip - needs drag
                                elif "Wormhole Stabilization" in (card_to_play.ability or ""):
                                    target_row = "weather"
                                elif "Command Network" in (card_to_play.ability or ""):
                                    target_row = "close"  # Default horn to close
                                else:
                                    target_row = "special"
                            else:
                                target_row = card_to_play.row

                            if target_row:
                                game.play_card(card_to_play, target_row)
                                row_rect = cfg.PLAYER_ROW_RECTS.get(target_row)
                                if row_rect:
                                    anim_manager.add_effect(StargateActivationEffect(row_rect.centerx, row_rect.centery, duration=800))
                                if network_proxy:
                                    network_proxy.send_play_card(card_to_play.id, target_row)
                                # Reset keyboard cursor
                                keyboard_hand_cursor = min(keyboard_hand_cursor, len(game.player1.hand) - 1)
                                if len(game.player1.hand) == 0:
                                    keyboard_hand_cursor = -1
                                    keyboard_mode_active = False
                                hovered_card = None

                # G key = Activate Faction Power
                elif event.key == pygame.K_g:
                    if game.game_state == "playing" and game.current_player == game.player1:
                        if game.player1.faction_power and game.player1.faction_power.is_available():
                            if game.player1.faction_power.activate(game, game.player1):
                                faction_power_effect = FactionPowerEffect(
                                    game.player1.faction,
                                    SCREEN_WIDTH // 2,
                                    SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH,
                                    SCREEN_HEIGHT
                                )
                                game.add_history_event(
                                    "faction_power",
                                    f"{game.player1.name} used {game.player1.faction_power.name}",
                                    "player"
                                )
                                if network_proxy:
                                    network_proxy.send_faction_power(game.player1.faction_power.name)
                                game.player1.calculate_score()
                                game.player2.calculate_score()
                                print(f"✓ Faction Power activated: {game.player1.faction_power.name}")
                
                # T key = Toggle LAN Chat Input
                elif event.key == pygame.K_t:
                    if lan_chat_panel and not lan_chat_panel.active:
                        lan_chat_panel.active = True
                        continue
                    elif lan_chat_panel and lan_chat_panel.active:
                         pass

                # Arrow keys for keyboard card navigation
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and game.game_state == "playing" and game.current_player == game.player1 and ui_state == UIState.PLAYING:
                    hand_size = len(game.player1.hand)
                    if hand_size > 0:
                        keyboard_mode_active = True
                        keyboard_button_cursor = -1  # Reset button cursor when selecting cards
                        if keyboard_hand_cursor < 0:
                            keyboard_hand_cursor = 0
                        elif event.key == pygame.K_LEFT:
                            keyboard_hand_cursor = (keyboard_hand_cursor - 1) % hand_size
                        else:
                            keyboard_hand_cursor = (keyboard_hand_cursor + 1) % hand_size
                        # Update hovered_card to show the keyboard-selected card
                        if 0 <= keyboard_hand_cursor < hand_size:
                            hovered_card = game.player1.hand[keyboard_hand_cursor]

                # Tab key = Cycle through action buttons (Pass, Faction Power)
                elif event.key == pygame.K_TAB and game.game_state == "playing" and game.current_player == game.player1 and ui_state == UIState.PLAYING:
                    # Deactivate card selection mode, switch to button mode
                    keyboard_mode_active = False
                    keyboard_hand_cursor = -1
                    hovered_card = None
                    # Cycle: -1 -> 0 (pass) -> 1 (faction power) -> -1
                    keyboard_button_cursor = (keyboard_button_cursor + 1) % 3 - 1  # -1, 0, 1, -1...
                    if keyboard_button_cursor == -1:
                        keyboard_button_cursor = 0  # Start at pass button

                # UP/DOWN to select target row when a card is selected via keyboard
                elif event.key in (pygame.K_UP, pygame.K_DOWN) and game.game_state == "playing" and game.current_player == game.player1 and ui_state == UIState.PLAYING:
                    if keyboard_mode_active and keyboard_hand_cursor >= 0 and keyboard_hand_cursor < len(game.player1.hand):
                        card = game.player1.hand[keyboard_hand_cursor]
                        # Determine valid rows for this card
                        if card.row == "close":
                            valid_rows = ["close"]
                        elif card.row == "ranged":
                            valid_rows = ["ranged"]
                        elif card.row == "siege":
                            valid_rows = ["siege"]
                        elif card.row == "agile":
                            valid_rows = ["close", "ranged"]
                        elif card.row == "weather":
                            valid_rows = ["close", "ranged", "siege"]
                        elif card.row == "special":
                            valid_rows = ["close", "ranged", "siege"]  # For horn effects
                        else:
                            valid_rows = ["close", "ranged", "siege"]

                        if len(valid_rows) > 1:
                            if event.key == pygame.K_UP:
                                keyboard_row_cursor = (keyboard_row_cursor - 1) % len(valid_rows)
                            else:
                                keyboard_row_cursor = (keyboard_row_cursor + 1) % len(valid_rows)
                    elif keyboard_button_cursor >= 0:
                        # Cycle between pass (0) and faction power (1)
                        keyboard_button_cursor = 1 - keyboard_button_cursor

                # SPACEBAR or ENTER = Play card via keyboard or close overlays
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    # Skip if chat is active (RETURN opens chat)
                    if lan_chat_panel and not lan_chat_panel.active and event.key == pygame.K_RETURN:
                        lan_chat_panel.active = True
                        continue

                    if inspected_card or inspected_leader:
                        # Close preview
                        inspected_card = None
                        inspected_leader = None
                    elif ui_state in (UIState.DISCARD_VIEW, UIState.JONAS_PEEK):
                        # Close overlays
                        if ui_state == UIState.JONAS_PEEK:
                            game.opponent_drawn_cards = []
                        ui_state = UIState.PLAYING
                        discard_scroll = 0
                    elif keyboard_button_cursor >= 0 and game.game_state == "playing" and game.current_player == game.player1:
                        # Activate keyboard-selected button
                        if keyboard_button_cursor == 0:
                            # Pass button
                            game.pass_turn()
                            if network_proxy:
                                network_proxy.send_pass()
                            keyboard_button_cursor = -1
                        elif keyboard_button_cursor == 1:
                            # Faction power button
                            if game.player1.faction_power and game.player1.faction_power.is_available():
                                if game.player1.faction_power.activate(game, game.player1):
                                    faction_power_effect = FactionPowerEffect(
                                        game.player1.faction,
                                        SCREEN_WIDTH // 2,
                                        SCREEN_HEIGHT // 2,
                                        SCREEN_WIDTH,
                                        SCREEN_HEIGHT
                                    )
                                    game.add_history_event(
                                        "faction_power",
                                        f"{game.player1.name} used {game.player1.faction_power.name}",
                                        "player"
                                    )
                                    if network_proxy:
                                        network_proxy.send_faction_power(game.player1.faction_power.name)
                                    game.player1.calculate_score()
                                    game.player2.calculate_score()
                            keyboard_button_cursor = -1
                    elif keyboard_mode_active and keyboard_hand_cursor >= 0 and game.game_state == "playing" and game.current_player == game.player1:
                        # Play the keyboard-selected card
                        if keyboard_hand_cursor < len(game.player1.hand):
                            card = game.player1.hand[keyboard_hand_cursor]

                            # Determine target row
                            if card.row == "close":
                                target_row = "close"
                            elif card.row == "ranged":
                                target_row = "ranged"
                            elif card.row == "siege":
                                target_row = "siege"
                            elif card.row == "agile":
                                valid_rows = ["close", "ranged"]
                                target_row = valid_rows[keyboard_row_cursor % len(valid_rows)]
                            elif card.row == "weather":
                                valid_rows = ["close", "ranged", "siege"]
                                target_row = valid_rows[keyboard_row_cursor % len(valid_rows)]
                            elif card.row == "special":
                                if "Command Network" in (card.ability or ""):
                                    valid_rows = ["close", "ranged", "siege"]
                                    target_row = valid_rows[keyboard_row_cursor % len(valid_rows)]
                                elif "Wormhole Stabilization" in (card.ability or ""):
                                    target_row = "weather"
                                elif "Ring Transport" in (card.ability or ""):
                                    target_row = None
                                else:
                                    target_row = "special"
                            else:
                                target_row = card.row

                            if target_row:
                                game.play_card(card, target_row)
                                row_rect = cfg.PLAYER_ROW_RECTS.get(target_row)
                                if row_rect:
                                    anim_manager.add_effect(StargateActivationEffect(row_rect.centerx, row_rect.centery, duration=800))
                                if network_proxy:
                                    network_proxy.send_play_card(card.id, target_row)
                                keyboard_hand_cursor = min(keyboard_hand_cursor, len(game.player1.hand) - 1)
                                if len(game.player1.hand) == 0:
                                    keyboard_hand_cursor = -1
                                    keyboard_mode_active = False
                                keyboard_row_cursor = 0
                                hovered_card = None
                    elif hovered_card and game.game_state == "playing":
                        # Preview hovered card with spacebar
                        inspected_card = hovered_card
                    elif selected_card and game.game_state == "playing":
                        # Preview selected card (legacy behavior)
                        inspected_card = selected_card

                # Keyboard navigation for mulligan phase
                if game.game_state == "mulligan" and not mulligan_local_done:
                    hand_size = len(game.player1.hand)
                    if hand_size > 0:
                        # LEFT/RIGHT to navigate cards
                        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                            keyboard_mode_active = True
                            if keyboard_hand_cursor < 0:
                                keyboard_hand_cursor = 0
                            elif event.key == pygame.K_LEFT:
                                keyboard_hand_cursor = (keyboard_hand_cursor - 1) % hand_size
                            else:
                                keyboard_hand_cursor = (keyboard_hand_cursor + 1) % hand_size
                            if 0 <= keyboard_hand_cursor < hand_size:
                                hovered_card = game.player1.hand[keyboard_hand_cursor]

                        # SPACE to toggle selection
                        elif event.key == pygame.K_SPACE and keyboard_hand_cursor >= 0 and keyboard_hand_cursor < hand_size:
                            card = game.player1.hand[keyboard_hand_cursor]
                            if card in mulligan_selected:
                                mulligan_selected.remove(card)
                            elif len(mulligan_selected) < 5:
                                mulligan_selected.append(card)

                        # ENTER to confirm mulligan
                        elif event.key == pygame.K_RETURN:
                            if 2 <= len(mulligan_selected) <= 5:
                                selected_indices = [i for i, card in enumerate(game.player1.hand) if card in mulligan_selected]
                                game.mulligan(game.player1, mulligan_selected)
                                game.player_mulligan_count = len(selected_indices)
                                mulligan_local_done = True
                                mulligan_selected = []
                                keyboard_hand_cursor = -1
                                keyboard_mode_active = False

                                if network_proxy:
                                    network_proxy.send_mulligan(selected_indices)
                                else:
                                    from ai_opponent import AIStrategy
                                    ai_strategy = AIStrategy(game, game.player2)
                                    ai_cards = ai_strategy.decide_mulligan()
                                    game.mulligan(game.player2, ai_cards)

                # Game over screen - R to restart
                if game.game_state == "game_over":
                    if event.key == pygame.K_r and not LAN_MODE:
                        battle_music.stop_battle_music()
                        main()
                        return
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        # Handle game over screen button clicks
                        # Calculate button positions (same as in drawing section)
                        button_width = 200
                        button_height = 50
                        button_spacing = 20
                        y_offset = 0  # This would need to match the actual y_offset from drawing
                        start_y = SCREEN_HEIGHT // 2 + y_offset + 30

                        # Check if draft mode to determine which buttons to use
                        if hasattr(game, 'is_draft_match') and game.is_draft_match:
                            # Check draft mode conditions
                            persistence = get_persistence()
                            active_run_data = persistence.get_active_draft_run()
                            player_won = (game.winner == game.player1)

                            if active_run_data:
                                current_wins = active_run_data.get('wins', 0)
                                if not (player_won and current_wins < DraftRun.MAX_WINS):  # Only show buttons if not continuing automatically
                                    # Define draft mode game over buttons
                                    rematch_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                                    main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                                    quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                                    mouse_pos = pygame.mouse.get_pos()
                                    if rematch_button.collidepoint(mouse_pos):
                                        battle_music.stop_battle_music()
                                        main()
                                        return
                                    elif main_menu_button.collidepoint(mouse_pos):
                                        battle_music.stop_battle_music()
                                        return  # This will exit the current main() call and return to the menu
                                    elif quit_button.collidepoint(mouse_pos):
                                        pygame.quit()
                                        sys.exit()
                            else:
                                # No active draft run - show regular game over buttons
                                rematch_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                                main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                                quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                                mouse_pos = pygame.mouse.get_pos()
                                if rematch_button.collidepoint(mouse_pos):
                                    battle_music.stop_battle_music()
                                    main()
                                    return
                                elif main_menu_button.collidepoint(mouse_pos):
                                    battle_music.stop_battle_music()
                                    return  # This will exit the current main() call and return to the menu
                                elif quit_button.collidepoint(mouse_pos):
                                    pygame.quit()
                                    sys.exit()
                        else:
                            # Regular game - show game over buttons
                            rematch_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                            main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                            quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                            mouse_pos = pygame.mouse.get_pos()
                            if rematch_button.collidepoint(mouse_pos):
                                battle_music.stop_battle_music()
                                main()
                                return
                            elif main_menu_button.collidepoint(mouse_pos):
                                battle_music.stop_battle_music()
                                return  # This will exit the current main() call and return to the menu
                            elif quit_button.collidepoint(mouse_pos):
                                pygame.quit()
                                sys.exit()
                    elif event.key == pygame.K_p and LAN_MODE:
                        # Play again in LAN mode - go back to deck selection while staying connected
                        if network_proxy and network_proxy.session.is_connected():
                            # Send play again message to peer
                            network_proxy.session.send("play_again", {"request": True})
                            battle_music.stop_battle_music()
                            # Return to LAN menu with existing session for rematch
                            from lan_menu import run_lan_rematch
                            result = run_lan_rematch(screen, network_proxy.session, network_proxy.role)
                            if result:
                                # Both players ready - run deck selection and start new game
                                from lan_game import run_lan_setup
                                from unlocks import CardUnlockSystem
                                import main as main_module
                                unlock_system = CardUnlockSystem()
                                new_context = run_lan_setup(screen, unlock_system, result["session"], result["role"])
                                if new_context:
                                    # Set global LAN context via module and restart game
                                    main_module.LAN_MODE = True
                                    main_module.LAN_CONTEXT = new_context
                                    main()
                            return
                    elif event.key == pygame.K_ESCAPE:
                        if LAN_MODE and network_proxy:
                            network_proxy.session.close()
                        running = False
                    elif event.key == pygame.K_RETURN and getattr(game, 'draft_victory', False):
                        # Launch space shooter easter egg with ship selection!
                        from space_shooter import run_space_shooter
                        run_space_shooter(screen)  # Shows ship selection screen
            elif event.type == pygame.MOUSEWHEEL:
                if history_panel_rect and history_panel_rect.collidepoint(pygame.mouse.get_pos()):
                    history_scroll_offset = max(0, min(history_scroll_limit, history_scroll_offset - event.y * cfg.HISTORY_ENTRY_HEIGHT))
                    history_manual_scroll = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # LAN: Block game interactions if waiting for opponent
                # Allow Right Click (3) for inspection and UI clicks if paused/chatting
                if waiting_for_opponent and ui_state not in (UIState.PAUSED, UIState.LAN_CHAT) and event.button != 3:
                    continue
    
                if event.button in (4, 5):
                    if history_panel_rect and history_panel_rect.collidepoint(event.pos):
                        delta = cfg.HISTORY_ENTRY_HEIGHT if event.button == 4 else -cfg.HISTORY_ENTRY_HEIGHT
                        history_scroll_offset = max(0, min(history_scroll_limit, history_scroll_offset - delta))
                        history_manual_scroll = True
                    continue
                if event.button == 1:
                    button_info_popup = None
                if game.current_player == game.player1:
                    # Handle leader ability click
                    if player_ability_rect and player_ability_rect.collidepoint(event.pos):
                        # If the leader is Hathor, handle her ability specifically
                        if game.player1.leader and "Hathor" in game.player1.leader.get('name', ''):
                            if game.trigger_hathor_ability(game.player1):
                                # Start the animation
                                steal_info = game.hathor_steal_info
                                if steal_info:
                                    # Calculate start and end positions
                                    start_pos = (
                                        steal_info['card'].rect.centerx,
                                        steal_info['card'].rect.centery
                                    )
                                    
                                    # Find the target row position
                                    target_row = steal_info['to_player'].hathor_ability_pending['target_row']
                                    target_row_rect = cfg.PLAYER_ROW_RECTS[target_row]
                                    end_pos = (
                                        target_row_rect.centerx,
                                        target_row_rect.centery
                                    )
                                    
                                    # Create and start the animation
                                    animation = HathorStealAnimation(
                                        steal_info['card'],
                                        start_pos,
                                        end_pos,
                                        on_finish=lambda: game.switch_turn()
                                    )
                                    anim_manager.add_animation(animation)
                                    steal_info["animation_started"] = True
                                    if network_proxy:
                                        network_proxy.send_leader_ability(
                                            "Hathor Steal",
                                            {
                                                "from_row": steal_info.get("from_row"),
                                                "from_index": steal_info.get("from_index"),
                                                "target_row": steal_info.get("target_row"),
                                                "card_id": steal_info.get("card_id"),
                                            }
                                        )
                            # After attempting Hathor's ability, don't process any other click logic for this event
                            continue
                        else:
                            # For any other leader, use the generic activation
                            result = game.activate_leader_ability(game.player1)
                            if result:
                                if result.get("requires_ui"):
                                    ability_name = result.get("ability", "")
                                    if ability_name == "Ancient Knowledge":
                                        # Catherine Langford
                                        ui_state = UIState.CATHERINE_SELECT
                                        catherine_cards_to_choose = result.get("revealed_cards", [])
                                    elif ability_name in ["Eidetic Memory", "System Lord's Cunning"]:
                                        # Jonas Quinn or Ba'al
                                        pending_leader_choice = result
                                        ui_state = UIState.LEADER_CHOICE_SELECT
                                elif result.get("rows"):
                                    # Weather ability (Apophis) - show weather visual effects
                                    ability_name = result.get("ability", "Weather Decree")
                                    if network_proxy:
                                        network_proxy.send_leader_ability(
                                            ability_name,
                                            {"rows": result.get("rows", [])}
                                        )
                                    anim_manager.add_effect(create_ability_animation(
                                        ability_name,
                                        SCREEN_WIDTH // 2,
                                        SCREEN_HEIGHT // 3
                                    ))
                                    for row_name in result.get("rows", []):
                                        weather_target = game.weather_row_targets.get(row_name, "both")
                                        weather_type = game.current_weather_types.get(row_name, "Ice Storm")
                                        if weather_target in ("player1", "both"):
                                            rect = cfg.PLAYER_ROW_RECTS.get(row_name)
                                            if rect:
                                                anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                                                anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                                        if weather_target in ("player2", "both"):
                                            rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                                            if rect:
                                                anim_manager.add_effect(StargateActivationEffect(rect.centerx, rect.centery, duration=800))
                                                anim_manager.add_row_weather(weather_type, rect, SCREEN_WIDTH)
                                else:
                                    if network_proxy:
                                        ability_name = result.get("ability", game.player1.leader.get("name", "leader_ability"))
                                        network_proxy.send_leader_ability(ability_name, {})
                # RIGHT CLICK = Card Preview/Zoom or Discard Pile View
                if event.button == 3:  # Right click
                    button_info_popup = None
                    popup_targets = []
                    if player_ability_rect:
                        popup_targets.append(("ability", game.player1, player_ability_rect, None))
                    if ai_ability_rect:
                        popup_targets.append(("ability", game.player2, ai_ability_rect, None))
                    if player_faction_button_rect:
                        popup_targets.append(("faction", game.player1, player_faction_button_rect, None))
                    if ai_faction_button_rect:
                        popup_targets.append(("faction", game.player2, ai_faction_button_rect, None))
                    if player_special_button_rect and player_special_button_kind:
                        popup_targets.append(("special", game.player1, player_special_button_rect, player_special_button_kind))
                    if ai_special_button_rect and ai_special_button_kind:
                        popup_targets.append(("special", game.player2, ai_special_button_rect, ai_special_button_kind))
    
                    popup_triggered = False
                    for kind, owner, rect, special_kind in popup_targets:
                        if rect and rect.collidepoint(event.pos):
                            new_popup = build_button_info_popup(kind, owner, rect, special_kind)
                            if new_popup:
                                button_info_popup = new_popup
                            popup_triggered = True
                            break
                    if popup_triggered:
                        continue
    
                    history_clicked = False
                    for entry, rect in history_entry_hitboxes:
                        if rect.collidepoint(event.pos):
                            history_clicked = True
                            if getattr(entry, "card_ref", None):
                                inspected_card = entry.card_ref
                                selected_card = None
                            break
                    if history_clicked:
                        continue
                    # Check if right-clicking discard pile to view it
                    if discard_rect and discard_rect.collidepoint(event.pos) and ui_state != UIState.DISCARD_VIEW:
                        ui_state = UIState.DISCARD_VIEW
                        discard_scroll = 0
                        continue
                    
                    # Check if right-clicking a card in the discard viewer to inspect it
                    if ui_state == UIState.DISCARD_VIEW:
                        card_clicked = False
                        for card in game.player1.discard_pile:
                            if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                inspected_card = card
                                selected_card = None
                                card_clicked = True
                                break
                        
                        # If clicked on a card, don't close the viewer
                        if card_clicked:
                            continue
                        
                        # Otherwise close the discard viewer
                        ui_state = UIState.PLAYING
                        discard_scroll = 0
                        continue
                    
                    # Close any existing previews
                    if inspected_card or inspected_leader:
                        inspected_card = None
                        inspected_leader = None
                    else:
                        # Check if clicking on a card in hand
                        for card in game.player1.hand:
                            if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                inspected_card = card
                                selected_card = None
                                break
                        
                        # Check if clicking on board cards (both player and opponent)
                        if not inspected_card:
                            for player_obj in [game.player1, game.player2]:
                                for row_name, cards in player_obj.board.items():
                                    for card in cards:
                                        if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                            inspected_card = card
                                            selected_card = None
                                            break
                                    if inspected_card:
                                        break
                                if inspected_card:
                                    break
                        
                        # Check if clicking on leader portraits
                        if not inspected_card:
                            if player_leader_rect and player_leader_rect.collidepoint(event.pos):
                                inspected_leader = game.player1
                            elif ai_leader_rect and ai_leader_rect.collidepoint(event.pos):
                                inspected_leader = game.player2
                    continue
                
                # LEFT CLICK = Select/Activate
                if event.button != 1:  # Only handle left click below
                    continue
                
                # Click discard pile to view it
                if discard_rect and discard_rect.collidepoint(event.pos) and ui_state != UIState.DISCARD_VIEW:
                    ui_state = UIState.DISCARD_VIEW
                    discard_scroll = 0
                
                # Close discard viewer with click
                if ui_state == UIState.DISCARD_VIEW and event.button == 1:
                    ui_state = UIState.PLAYING
                
                # Handle discard scroll with mouse wheel
                if ui_state == UIState.DISCARD_VIEW and event.button in [4, 5]:
                    if event.button == 4:  # Scroll up
                        discard_scroll = min(0, discard_scroll + 50)
                    else:  # Scroll down
                        discard_scroll -= 50
                
                # Handle medic selection mode
                if ui_state == UIState.MEDIC_SELECT:
                    # Check if clicking on a card in the medic selection overlay
                    # This will be handled after drawing
                    pass
                
                # Check if clicking Faction Power button (player only)
                if (game.game_state == "playing"
                        and game.current_player == game.player1
                        and player_faction_button_rect
                        and player_faction_button_rect.collidepoint(event.pos)):
                    if game.player1.faction_power and game.player1.faction_power.is_available():
                        if game.player1.faction_power.activate(game, game.player1):
                            faction_power_effect = FactionPowerEffect(
                                game.player1.faction,
                                SCREEN_WIDTH // 2,
                                SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT
                            )
                            game.add_history_event(
                                "faction_power",
                                f"{game.player1.name} used {game.player1.faction_power.name}",
                                "player"
                            )
                            # Send over network in LAN mode
                            if network_proxy:
                                network_proxy.send_faction_power(game.player1.faction_power.name)
                            # Track ability usage
                            game.ability_usage["faction_power"] = game.ability_usage.get("faction_power", 0) + 1
                            game.player1.calculate_score()
                            game.player2.calculate_score()
                    continue
                
                # Check if clicking on leader portraits (for inspection)
                if player_leader_rect and player_leader_rect.collidepoint(event.pos):
                    inspected_leader = game.player1
                    inspected_card = None
                    selected_card = None
                    continue
                elif ai_leader_rect and ai_leader_rect.collidepoint(event.pos):
                    inspected_leader = game.player2
                    inspected_card = None
                    selected_card = None
                    continue
                
                # Check if clicking on opponent cards (for inspection)
                if not inspected_card and not inspected_leader:
                    for row_name, cards in game.player2.board.items():
                        for card in cards:
                            if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                inspected_card = card
                                selected_card = None
                                break
                        if inspected_card:
                            break
                
                # Close inspection overlays if clicking
                if inspected_card or inspected_leader:
                    inspected_card = None
                    inspected_leader = None
                    continue
                
                # Mulligan phase
                if game.game_state == "mulligan":
                    if mulligan_local_done:
                        continue
    
                    # Select cards to mulligan (max 2)
                    for card in game.player1.hand:
                        if card.rect.collidepoint(event.pos):
                            if card in mulligan_selected:
                                mulligan_selected.remove(card)
                            elif len(mulligan_selected) < 5:  # Max 5 cards
                                mulligan_selected.append(card)
                            break
                    
                    # Confirm mulligan
                    if cfg.MULLIGAN_BUTTON_RECT.collidepoint(event.pos):
                        # Enforce 2-5 card limit
                        if len(mulligan_selected) < 2:
                            # Show error message
                            print("Must select at least 2 cards for mulligan!")
                            continue
                        elif len(mulligan_selected) > 5:
                            # Show error message
                            print("Cannot mulligan more than 5 cards!")
                            continue
                        selected_indices = [i for i, card in enumerate(game.player1.hand) if card in mulligan_selected]
                        game.mulligan(game.player1, mulligan_selected)
                        game.player_mulligan_count = len(selected_indices)
                        mulligan_local_done = True
                        mulligan_selected = []
    
                        if network_proxy:
                            network_proxy.send_mulligan(selected_indices)
                        else:
                            # Single-player: Use AI strategy for mulligan
                            from ai_opponent import AIStrategy
                            ai_strategy = AIStrategy(game, game.player2)
                            ai_cards = ai_strategy.decide_mulligan()
                            game.mulligan(game.player2, ai_cards)
                            mulligan_remote_done = True
                            # Don't end mulligan here - let the main loop handle it

                # Playing phase - START DRAG
                elif game.game_state == "playing":
                    if game.current_player == game.player1 and not game.player1.has_passed:
                        # Check if clicking on pass buttons
                        pass_clicked = False
                        if HUD_PASS_BUTTON_RECT and HUD_PASS_BUTTON_RECT.collidepoint(event.pos):
                            selected_card = None
                            dragging_card = None
                            drag_velocity = Vector2()
                            drag_pickup_flash = 0.0
                            anim_manager.add_effect(StargateActivationEffect(HUD_PASS_BUTTON_RECT.centerx,
                                                                             HUD_PASS_BUTTON_RECT.centery,
                                                                             duration=800))
                            game.pass_turn()
    
                            # Send network action if in LAN mode
                            if network_proxy:
                                network_proxy.send_pass()
    
                            pass_clicked = True
                        if pass_clicked:
                            continue
                        # Iris button click (Tau'ri only)
                        elif iris_button_rect and iris_button_rect.collidepoint(event.pos):
                            if game.player1.iris_defense.is_available():
                                game.player1.iris_defense.activate()
                                # Trigger Iris closing animation at center of screen
                                from animations import IrisClosingEffect
                                iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                                anim_manager.add_effect(iris_anim)
                        # Ring Transportation button click (Goa'uld only)
                        elif ring_transport_button_rect and ring_transport_button_rect.collidepoint(event.pos):
                            if game.player1.ring_transportation and game.player1.ring_transportation.can_use():
                                # Enter card selection mode - next card clicked will be transported
                                ui_state = UIState.RING_TRANSPORT_SELECT
                        else:
                            # Ring Transport selection mode - clicking a card on player's board
                            if ui_state == UIState.RING_TRANSPORT_SELECT:
                                # Check if clicking on player's CLOSE COMBAT cards only
                                card_clicked = False
                                row_cards = game.player1.board.get("close", [])
                                for card in row_cards:
                                    if hasattr(card, 'rect') and card.rect.collidepoint(event.pos):
                                        # Start ring transportation animation
                                        from power import RingTransportAnimation
                                        
                                        start_pos = (card.rect.centerx, card.rect.centery)
                                        # End position = center of hand area
                                        end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - HAND_Y_OFFSET // 2)
                                        
                                        ring_transport_animation = RingTransportAnimation(
                                            card, start_pos, end_pos, SCREEN_WIDTH, SCREEN_HEIGHT
                                        )
                                        
                                        # Remove card from board and add to hand
                                        game.player1.board["close"].remove(card)
                                        game.player1.hand.append(card)
                                        
                                        # Mark ability as used
                                        game.player1.ring_transportation.use(card)
                                        
                                        # Recalculate scores
                                        game.player1.calculate_score()
                                        game.player2.calculate_score()
                                        
                                        ui_state = UIState.PLAYING
                                        card_clicked = True
                                        break
                                
                                if card_clicked:
                                    continue
                            
                            # Check if clicking on a card in hand
                            for card in game.player1.hand:
                                if card.rect.collidepoint(event.pos):
                                    # Check if clicking the same special card again (confirmation)
                                    if card.row == "special" and selected_card == card:
                                        # Second click = confirm and play
                                        # Check if this is a decoy card
                                        if "Ring Transport" in (card.ability or ""):
                                            # This card is played by dragging and dropping, so do nothing on a double-click.
                                            pass
                                        else:
                                            # Check if this is Wormhole Stabilization (Clear Weather)
                                            if "Wormhole Stabilization" in (card.ability or ""):
                                                black_hole_anim = ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                                                anim_manager.add_effect(black_hole_anim)
                                            game.play_card(card, card.row)
                                        selected_card = None
                                        dragging_card = None
                                        drag_velocity = Vector2()
                                        drag_pickup_flash = 0.0
                                        break
                                    
                                    # First click or different card - Select it
                                    selected_card = card
                                    
                                    if card.row == "special":
                                        # All Special cards can now be dragged
                                        dragging_card = card
                                        drag_offset = (card.rect.x - event.pos[0], card.rect.y - event.pos[1])
                                        drag_velocity = Vector2()
                                        drag_trail.clear()
                                        drag_trail_emit_ms = 0
                                        drag_pickup_flash = 1.0
                                        drag_pulse = 0.0
                                        # Get valid decoy targets for Ring Transport
                                        if "Ring Transport" in (card.ability or ""):
                                            decoy_valid_targets = []
                                            valid_cards = game.get_decoy_valid_cards()
                                            for valid_card in valid_cards:
                                                if hasattr(valid_card, 'rect'):
                                                    decoy_valid_targets.append((valid_card, valid_card.rect.copy()))
                                    else:
                                        # Start dragging unit cards
                                        dragging_card = card
                                        drag_offset = (card.rect.x - event.pos[0], card.rect.y - event.pos[1])
                                        drag_velocity = Vector2()
                                        drag_trail.clear()
                                        drag_trail_emit_ms = 0
                                        drag_pickup_flash = 1.0
                                        drag_pulse = 0.0
                                        # Get valid decoy targets for Ring Transport on unit cards (e.g., Puddle Jumper)
                                        if "Ring Transport" in (card.ability or ""):
                                            decoy_valid_targets = []
                                            valid_cards = game.get_decoy_valid_cards()
                                            for valid_card in valid_cards:
                                                if hasattr(valid_card, 'rect'):
                                                    decoy_valid_targets.append((valid_card, valid_card.rect.copy()))
                                    
                                    break
            
            elif event.type == pygame.MOUSEBUTTONUP:
                # Drop card
                if dragging_card and game.game_state == "playing":
                    played = False
                    is_spy = "Deep Cover Agent" in (dragging_card.ability or "")
                    ability_text = dragging_card.ability or ""
                    ability_lower = ability_text.lower()
                    
                    # Weather and special cards can target any row
                    if dragging_card.row in ["weather", "special"]:
                        if dragging_card.row == "weather":
                            target_row = None
                            drop_rect = None
                            # First, allow dropping onto dedicated weather slots
                            for row_name, slot_rect in WEATHER_SLOT_RECTS.items():
                                if slot_rect.collidepoint(event.pos):
                                    target_row = row_name
                                    drop_rect = slot_rect
                                    break
                            # Fallback to full row targets if player drags over the battlefield
                            if target_row is None:
                                for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                    for row_name, rect in rects.items():
                                        if rect.collidepoint(event.pos):
                                            target_row = row_name
                                            drop_rect = rect
                                            break
                                    if target_row:
                                        break
                            if target_row:
                                played = True
                                if "wormhole stabilization" in ability_lower:
                                    anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                                else:
                                    effect_x = drop_rect.centerx
                                    effect_y = drop_rect.centery
                                    anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=800))
                                    if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                                        for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                            row_rect = rects.get(target_row)
                                            if row_rect:
                                                anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))
                                game.play_card(dragging_card, target_row)
    
                                # Send network action if in LAN mode
                                if network_proxy:
                                    network_proxy.send_play_card(dragging_card.id, target_row)
                        else:
                            if "Command Network" in ability_text:
                                for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
                                    if slot_rect.collidepoint(event.pos):
                                        game.play_card(dragging_card, row_name)
                                        played = True
                                        effect_x = slot_rect.centerx
                                        effect_y = slot_rect.centery
                                        anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=800))
                                        break
                            elif "Ring Transport" in ability_text:
                                # Ring Transport - check if dropped on a valid card
                                if decoy_drag_target:
                                    if game.play_ring_transport(dragging_card, decoy_drag_target):
                                        # Show ring transport animation with golden rings
                                        from power import RingTransportAnimation
                                        start_pos = (decoy_drag_target.rect.centerx, decoy_drag_target.rect.centery)
                                        # End position is player's hand area
                                        end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
                                        ring_transport_animation = RingTransportAnimation(
                                            decoy_drag_target, start_pos, end_pos,
                                            SCREEN_WIDTH, SCREEN_HEIGHT
                                        )
                                        game.player1.calculate_score()
                                        game.player2.calculate_score()
                                        game.switch_turn()
                                        played = True
                                    decoy_valid_targets = []
                                    decoy_drag_target = None
                            else:
                                for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                    for row_name, rect in rects.items():
                                        if rect.collidepoint(event.pos):
                                            game.play_card(dragging_card, row_name)
                                            played = True
                                            
                                            effect_x = rect.centerx
                                            effect_y = rect.centery
                                            
                                            # Check for Naquadah Overload explosions
                                            if "Naquadah Overload" in ability_text:
                                                # Create blue explosions ONLY on rows where cards were destroyed
                                                for player, destroyed_row in game.last_scorch_positions:
                                                    # Determine which row rect to use
                                                    if player == game.player1:
                                                        row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                                                    else:
                                                        row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)
                                                    
                                                    if row_rect:
                                                        anim_manager.add_effect(NaquadahExplosionEffect(
                                                            SCREEN_WIDTH // 2,
                                                            row_rect.centery,
                                                            duration=1500
                                                        ))
                                                game.last_scorch_positions = []
                                            
                                            # Trigger other special visuals
                                            if not add_special_card_effect(dragging_card, effect_x, effect_y, anim_manager, SCREEN_WIDTH, SCREEN_HEIGHT):
                                                stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=800)
                                                anim_manager.add_effect(stargate_effect)
                                            break
                                    if played:
                                        break
                    else:
                        # Regular unit cards
                        target_rows = cfg.OPPONENT_ROW_RECTS if is_spy else cfg.PLAYER_ROW_RECTS
                        
                        # Check which row the card was dropped on
                        for row_name, rect in target_rows.items():
                            if rect.collidepoint(event.pos):
                                if dragging_card.row == row_name or (dragging_card.row == "agile" and row_name in ["close", "ranged"]):
                                    
                                    # Check if this is a Ring Transport unit (e.g., Puddle Jumper) dropped on a valid target
                                    if "Ring Transport" in (dragging_card.ability or "") and decoy_drag_target:
                                        if game.play_ring_transport(dragging_card, decoy_drag_target):
                                            # Show ring transport animation with golden rings
                                            from power import RingTransportAnimation
                                            start_pos = (decoy_drag_target.rect.centerx, decoy_drag_target.rect.centery)
                                            # End position is player's hand area
                                            end_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)
                                            ring_transport_animation = RingTransportAnimation(
                                                decoy_drag_target, start_pos, end_pos,
                                                SCREEN_WIDTH, SCREEN_HEIGHT
                                            )
                                            game.player1.calculate_score()
                                            game.player2.calculate_score()
                                            game.switch_turn()
                                            played = True
                                        decoy_valid_targets = []
                                        decoy_drag_target = None
                                        break
                                    
                                    # Calculate insertion index (Mid-Card Insertion)
                                    target_player = game.player2 if is_spy else game.player1
                                    row_cards = target_player.board[row_name]
                                    insert_index = len(row_cards)
                                    
                                    # Find drop position relative to existing cards (Dynamic Slot Logic)
                                    if row_cards:
                                        mouse_x = event.pos[0]
                                        for i, card in enumerate(row_cards):
                                            if hasattr(card, 'rect'):
                                                # Use center of card as threshold for insertion
                                                if mouse_x < card.rect.centerx:
                                                    insert_index = i
                                                    break
                                    
                                    # --- NEW: Check card for specific animations ---
                                    if "Naquadah Overload" in (dragging_card.ability or ""):
                                        # Naquadah Overload: Play card first, then show explosions on affected rows
                                        game.play_card(dragging_card, row_name, index=insert_index)
                                        
                                        # Create blue explosions ONLY on rows where cards were destroyed
                                        for player, destroyed_row in game.last_scorch_positions:
                                            # Determine which row rect to use
                                            if player == game.player1:
                                                row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                                            else:
                                                row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)
                                            
                                            if row_rect:
                                                anim_manager.add_effect(NaquadahExplosionEffect(
                                                    SCREEN_WIDTH // 2,
                                                    row_rect.centery,
                                                    duration=1500
                                                ))
                                        
                                        # Clear the positions for next time
                                        game.last_scorch_positions = []
                                        played = True
                                    elif "Legendary Commander" in (dragging_card.ability or ""):
                                        # Legendary Commander card - use unique hero animation
                                        effect_x = rect.centerx
                                        effect_y = rect.centery
                                        hero_anim = create_hero_animation(dragging_card.name, effect_x, effect_y)
                                        anim_manager.add_effect(hero_anim)
                                        anim_manager.add_effect(LegendaryLightningEffect(dragging_card))
                                    else:
                                        # Check for special abilities
                                        effect_x = rect.centerx
                                        effect_y = rect.centery
                                        
                                        ability = dragging_card.ability or ""
                                        ability_triggered = False
                                        
                                        # Check for special ability animations
                                        for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones", 
                                                               "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement",
                                                               "Look at opponent's hand"]:
                                            if special_ability in ability:
                                                ability_anim = create_ability_animation(ability, effect_x, effect_y)
                                                anim_manager.add_effect(ability_anim)
                                                ability_triggered = True
                                                break
                                        
                                        # Default stargate effect if no special ability
                                        if not ability_triggered:
                                            anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y))
    
                                    # Special card unique visuals
                                    if dragging_card.row == "special":
                                        add_special_card_effect(
                                            dragging_card,
                                            effect_x,
                                            effect_y,
                                            anim_manager,
                                            SCREEN_WIDTH,
                                            SCREEN_HEIGHT
                                        )
                                    
                                    # Add ship to space battle if siege card is PLAYED
                                    if dragging_card.row == "siege":
                                        ambient_effects.add_ship(game.player1.faction, dragging_card.name, is_player=True)
                                    
                                    # Check if this is a medic card
                                    if "Medical Evac" in (dragging_card.ability or ""):
                                        valid_medic_cards = game.get_medic_valid_cards(game.player1)
                                        if valid_medic_cards:
                                            # Enter medic selection mode
                                            ui_state = UIState.MEDIC_SELECT
                                            medic_card_played = dragging_card
                                            game.play_card(dragging_card, row_name, index=insert_index)
                                        else:
                                            # No cards to revive, play normally
                                            game.play_card(dragging_card, row_name, index=insert_index)
                                    else:
                                        game.play_card(dragging_card, row_name, index=insert_index)
                                    
                                    # Add special card effects for unit cards too
                                    effect_x = rect.centerx
                                    effect_y = rect.centery
                                    if not add_special_card_effect(dragging_card, effect_x, effect_y, anim_manager, SCREEN_WIDTH, SCREEN_HEIGHT):
                                        # Default stargate effect if no special effect
                                        anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=800))
                                    
                                    played = True
                                    break
                    
                    # Reset drag state
                    if not played:
                        selected_card = None
                    dragging_card = None
                    drag_velocity = Vector2()
                    drag_pickup_flash = 0.0
                    decoy_valid_targets = []
                    decoy_drag_target = None
            
            elif event.type == pygame.MOUSEMOTION:
                # Reset keyboard mode when mouse is used significantly
                rel_x, rel_y = getattr(event, "rel", (0, 0))
                if abs(rel_x) > 5 or abs(rel_y) > 5:
                    if keyboard_mode_active:
                        keyboard_mode_active = False
                        keyboard_hand_cursor = -1

                # Update dragging position with smooth easing
                if dragging_card:
                    drag_target_x = event.pos[0] + drag_offset[0]
                    drag_target_y = event.pos[1] + drag_offset[1]
                    # Apply easing for smooth follow
                    easing_factor = 0.25  # Lower = smoother but more lag
                    dragging_card.rect.x += (drag_target_x - dragging_card.rect.x) * easing_factor
                    dragging_card.rect.y += (drag_target_y - dragging_card.rect.y) * easing_factor
                    rel_x, rel_y = getattr(event, "rel", (0, 0))
                    drag_velocity.x = drag_velocity.x * 0.7 + rel_x * 0.3
                    drag_velocity.y = drag_velocity.y * 0.7 + rel_y * 0.3
                    
                    # Update Ring Transport decoy target detection
                    if "Ring Transport" in (dragging_card.ability or ""):
                        decoy_drag_target = None
                        mouse_pos = event.pos
                        for card, rect in decoy_valid_targets:
                            if rect.collidepoint(mouse_pos):
                                decoy_drag_target = card
                                break
                else:
                    drag_velocity *= 0.85
                    decoy_drag_target = None
                
                # Check for card hover in hand (for scale effect)
                if not dragging_card and game.game_state in ("playing", "mulligan"):
                    mouse_pos = event.pos
                    new_hovered = None
                    for card in game.player1.hand:
                        if hasattr(card, 'rect') and card.rect.collidepoint(mouse_pos):
                            new_hovered = card
                            break
                    if new_hovered != hovered_card:
                        hovered_card = new_hovered
                        target_hover_scale = 1.08 if hovered_card else 1.0
        
        # Leader ability triggers (at start of player's turn)
        if game.current_player == game.player1 and game.game_state == "playing" and not game.player1.has_passed:
            # Jonas Quinn: See cards drawn by opponent (auto-trigger when opponent draws)
            if game.player1.leader and "Jonas" in game.player1.leader.get('name', ''):
                # Show overlay if opponent has drawn cards (not starting hand)
                if game.opponent_drawn_cards:
                    ui_state = UIState.JONAS_PEEK
            
            # Vala: Look at 3 cards, keep 1 (once per round, manual trigger with V key)
            # Ba'al Clone: Clone highest unit (once per round, manual trigger with B key)
            # Thor: Move unit (once per round, manual trigger with T key)
        
        # Simple AI for Player 2 - WITH SMOOTH ANIMATIONS
        # Skip AI animations in LAN mode - opponent is a real human
        if game.current_player == game.player2 and game.game_state == "playing" and not LAN_MODE:
            if not ai_turn_in_progress:
                # Start AI turn animation
                ai_turn_anim.start_thinking()
                ai_turn_in_progress = True
                ai_card_to_play = None
                ai_row_to_play = None
            
            # Update AI animation
            ai_result = ai_turn_anim.update(dt)
            
            if ai_result == "thinking_done":
                # AI has finished thinking, get the decision
                ai_board_before = {row: len(cards) for row, cards in game.player2.board.items()}
    
                # Check if faction power was available before AI decision
                ai_power_available_before = (game.player2.faction_power and
                                             game.player2.faction_power.is_available())
    
                # Get AI decision without executing it yet
                card_to_play, row_to_play = ai_controller.choose_move()
    
                # Check if AI used faction power
                ai_power_available_after = (game.player2.faction_power and
                                            game.player2.faction_power.is_available())
                ai_used_faction_power = ai_power_available_before and not ai_power_available_after
    
                if card_to_play:
                    # Store the decision
                    ai_card_to_play = card_to_play
                    ai_row_to_play = row_to_play
                    # Find card index in hand for animation
                    try:
                        card_index = game.player2.hand.index(card_to_play)
                        ai_selected_card_index = card_index
                        ai_turn_anim.start_selecting(card_index)
                    except ValueError:
                        # Card not in hand, skip animation
                        ai_selected_card_index = None
                        ai_turn_anim.finish()
                        ai_turn_in_progress = False
                else:
                    ai_selected_card_index = None
    
                    # Check if AI used faction power - trigger animation!
                    if ai_used_faction_power:
                        # Create faction power effect animation
                        faction_power_effect = FactionPowerEffect(
                            game.player2.faction,
                            SCREEN_WIDTH // 2,
                            SCREEN_HEIGHT // 2,
                            SCREEN_WIDTH,
                            SCREEN_HEIGHT
                        )
                        anim_manager.add_effect(faction_power_effect)
    
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
                            anim_manager.add_effect(iris_anim)
    
                    # AI passes or uses power
                    ai_turn_anim.finish()
                    game.last_turn_actor = game.player2
                    game.switch_turn()
                    ai_turn_in_progress = False
            
            elif ai_result == "selecting_done":
                # Start playing animation
                if ai_card_to_play and ai_row_to_play:
                    total_cards = len(game.player2.hand)
                    start_center = get_opponent_hand_card_center(total_cards, ai_selected_card_index)
                    ability = ai_card_to_play.ability or ""
                    target_rects = cfg.PLAYER_ROW_RECTS if ("Deep Cover Agent" in ability or ai_card_to_play.row == "weather") else cfg.OPPONENT_ROW_RECTS
                    target_rect = target_rects.get(ai_row_to_play)
                    if not target_rect:
                        # Fallback to any matching row rect
                        target_rect = cfg.PLAYER_ROW_RECTS.get(ai_row_to_play) or cfg.OPPONENT_ROW_RECTS.get(ai_row_to_play)
                    end_center = (target_rect.centerx, target_rect.centery) if target_rect else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    if ai_card_to_play.image:
                        anim_manager.add_effect(AICardPlayAnimation(ai_card_to_play.image, start_center, end_center))
                ai_turn_anim.start_playing(ai_row_to_play)
            
            elif ai_result == "playing_done":
                # Actually play the card
                if ai_card_to_play and ai_row_to_play:
                    ability = ai_card_to_play.ability or ""
                    
                    # Play the card
                    game.play_card(ai_card_to_play, ai_row_to_play)
                    ai_selected_card_index = None
                    
                    # Check if AI played a siege card for space battle
                    if ai_row_to_play == 'siege':
                        ambient_effects.add_ship(game.player2.faction, ai_card_to_play.name, is_player=False)
                    
                    # Trigger visual effect for the play
                    target_rect = cfg.OPPONENT_ROW_RECTS.get(ai_row_to_play)
                    effect_x = target_rect.centerx if target_rect else SCREEN_WIDTH // 2
                    effect_y = target_rect.centery if target_rect else SCREEN_HEIGHT // 4
    
                    weather_visual_applied = False
                    if ai_card_to_play.row == "weather":
                        weather_visual_applied = True
                        ability_lower = ability.lower()
                        if "wormhole stabilization" in ability_lower:
                            anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                        else:
                            anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=500))
                            if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                                for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                    row_rect = rects.get(ai_row_to_play)
                                    if row_rect:
                                        anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))
    
                    # Check for Naquadah Overload
                    if not weather_visual_applied and "Naquadah Overload" in ability:
                        # Create blue explosions ONLY on rows where cards were destroyed
                        for player, destroyed_row in game.last_scorch_positions:
                            if player == game.player1:
                                row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                            else:
                                row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)
                            
                            if row_rect:
                                anim_manager.add_effect(NaquadahExplosionEffect(
                                    SCREEN_WIDTH // 2,
                                    row_rect.centery,
                                    duration=1500
                                ))
                        game.last_scorch_positions = []
                    elif not weather_visual_applied and "Legendary Commander" in ability:
                        hero_anim = create_hero_animation(ai_card_to_play.name, effect_x, effect_y)
                        anim_manager.add_effect(hero_anim)
                        anim_manager.add_effect(LegendaryLightningEffect(ai_card_to_play))
                    elif not weather_visual_applied:
                        # Check for special ability animations (same as player)
                        ability_triggered = False
                        for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones",
                                               "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement"]:
                            if special_ability in ability:
                                ability_anim = create_ability_animation(ability, effect_x, effect_y)
                                anim_manager.add_effect(ability_anim)
                                ability_triggered = True
                                break
    
                        # Default stargate effect if no special ability
                        if not ability_triggered:
                            stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=500)
                            anim_manager.add_effect(stargate_effect)
    
                        # Special card unique visuals
                        if ai_card_to_play.row == "special":
                            add_special_card_effect(
                                ai_card_to_play,
                                effect_x,
                                effect_y,
                                anim_manager,
                                SCREEN_WIDTH,
                                SCREEN_HEIGHT
                            )
                
                ai_turn_anim.start_resolving()
            
            elif ai_result == "resolving_done":
                # Recalculate scores
                game.player1.calculate_score()
                game.player2.calculate_score()
    
                # Check if AI should use Iris Defense (before switching turn)
                if (hasattr(ai_controller, 'strategy') and
                    ai_controller.strategy.should_use_iris_defense()):
                    # AI activates Iris Defense
                    game.player2.iris_defense.activate()
                    # Trigger Iris closing animation
                    from animations import IrisClosingEffect
                    iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    anim_manager.add_effect(iris_anim)
                    # Add history event
                    game.add_history_event(
                        "special",
                        f"{game.player2.name} activated Iris Defense!",
                        "ai",
                        icon="[#]"
                    )
    
                # Finish turn
                ai_turn_anim.finish()
                game.switch_turn()
                ai_turn_in_progress = False
                ai_selected_card_index = None
    
        # LAN opponent turn handling
        elif game.current_player == game.player2 and game.game_state == "playing" and LAN_MODE:
            # Check if faction power was available before polling
            lan_power_available_before = (game.player2.faction_power and
                                          game.player2.faction_power.is_available())
    
            # Poll for network message from opponent
            was_passed = game.player2.has_passed
            card_to_play, row_to_play = ai_controller.choose_move()
            
            if not was_passed and game.player2.has_passed:
                game.switch_turn()
                continue
    
            # Check if opponent used faction power
            lan_power_available_after = (game.player2.faction_power and
                                         game.player2.faction_power.is_available())
            if lan_power_available_before and not lan_power_available_after:
                # Opponent used faction power - trigger animation!
                faction_power_effect = FactionPowerEffect(
                    game.player2.faction,
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 2,
                    SCREEN_WIDTH,
                    SCREEN_HEIGHT
                )
                anim_manager.add_effect(faction_power_effect)
    
                # Add Iris closing animation for Tau'ri Gate Shutdown
                if game.player2.faction == FACTION_TAURI:
                    from animations import IrisClosingEffect
                    iris_anim = IrisClosingEffect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    anim_manager.add_effect(iris_anim)
                
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
                    ambient_effects.add_ship(game.player2.faction, card_to_play.name, is_player=False)
    
                # Trigger visual effect for the play
                target_rect = cfg.OPPONENT_ROW_RECTS.get(row_to_play)
                if "Deep Cover Agent" in ability or card_to_play.row == "weather":
                    target_rect = cfg.PLAYER_ROW_RECTS.get(row_to_play) or target_rect
                effect_x = target_rect.centerx if target_rect else SCREEN_WIDTH // 2
                effect_y = target_rect.centery if target_rect else SCREEN_HEIGHT // 4
                if card_to_play.row == "special":
                    add_special_card_effect(
                        card_to_play,
                        effect_x,
                        effect_y,
                        anim_manager,
                        SCREEN_WIDTH,
                        SCREEN_HEIGHT
                    )
    
                weather_visual_applied = False
                if card_to_play.row == "weather":
                    weather_visual_applied = True
                    ability_lower = ability.lower()
                    if "wormhole stabilization" in ability_lower:
                        anim_manager.add_effect(ClearWeatherBlackHole(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                    else:
                        anim_manager.add_effect(StargateActivationEffect(effect_x, effect_y, duration=500))
                        if "asteroid storm" in ability_lower or "micrometeorite" in ability_lower:
                            for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                                row_rect = rects.get(row_to_play)
                                if row_rect:
                                    anim_manager.add_effect(MeteorShowerImpactEffect(row_rect))
    
                # Check for Naquadah Overload
                if not weather_visual_applied and "Naquadah Overload" in ability:
                    for player, destroyed_row in game.last_scorch_positions:
                        if player == game.player1:
                            row_rect = cfg.PLAYER_ROW_RECTS.get(destroyed_row)
                        else:
                            row_rect = cfg.OPPONENT_ROW_RECTS.get(destroyed_row)
                        if row_rect:
                            anim_manager.add_effect(NaquadahExplosionEffect(
                                SCREEN_WIDTH // 2,
                                row_rect.centery,
                                duration=1500
                            ))
                    game.last_scorch_positions = []
                elif not weather_visual_applied and "Legendary Commander" in ability:
                    hero_anim = create_hero_animation(card_to_play.name, effect_x, effect_y)
                    anim_manager.add_effect(hero_anim)
                    anim_manager.add_effect(LegendaryLightningEffect(card_to_play))
                elif not weather_visual_applied:
                    # Check for special ability animations (same as player)
                    ability_triggered = False
                    for special_ability in ["Inspiring Leadership", "Vampire", "Crone", "Deploy Clones",
                                           "Activate Combat Protocol", "Survival Instinct", "Genetic Enhancement"]:
                        if special_ability in ability:
                            ability_anim = create_ability_animation(ability, effect_x, effect_y)
                            anim_manager.add_effect(ability_anim)
                            ability_triggered = True
                            break
    
                    # Default stargate effect if no special ability
                    if not ability_triggered:
                        stargate_effect = StargateActivationEffect(effect_x, effect_y, duration=500)
                        anim_manager.add_effect(stargate_effect)
    
                # Recalculate scores
                game.player1.calculate_score()
                game.player2.calculate_score()
    
            # Note: If (None, None) returned, either opponent passed/used power (already handled),
            # or no message yet (keep polling next frame)
    
        # Check for score changes and trigger animations
        prev_p1_before = prev_p1_score
        prev_p2_before = prev_p2_score
    
        if game.player1.score != prev_p1_score:
            score_x = SCREEN_WIDTH - int(SCREEN_WIDTH * 0.052)
            p1_lead_gain = (prev_p1_before <= prev_p2_before) and (game.player1.score > game.player2.score)
            anim_manager.add_score_animation('p1', prev_p1_score, game.player1.score, 
                                            score_x, SCREEN_HEIGHT // 2 + 50, lead_burst=p1_lead_gain)
            prev_p1_score = game.player1.score
        
        if game.player2.score != prev_p2_score:
            score_x = SCREEN_WIDTH - int(SCREEN_WIDTH * 0.052)
            p2_lead_gain = (prev_p2_before <= prev_p1_before) and (game.player2.score > game.player1.score)
            anim_manager.add_score_animation('p2', prev_p2_score, game.player2.score,
                                            score_x, SCREEN_HEIGHT // 2 - 50, lead_burst=p2_lead_gain)
            prev_p2_score = game.player2.score
    
        drag_hover_highlight = None
        drag_row_highlights = []
        if dragging_card and game.game_state == "playing":
            mouse_pos = pygame.mouse.get_pos()
            hover_alpha = 80
            ability = dragging_card.ability or ""
            if dragging_card.row == "weather":
                slot_hover = False
                for row_name, slot_rect in WEATHER_SLOT_RECTS.items():
                    slot_color = get_row_color(row_name)
                    drag_row_highlights.append({"rect": slot_rect, "color": slot_color, "alpha": 55})
                    if slot_rect.collidepoint(mouse_pos):
                        drag_hover_highlight = {"rect": slot_rect, "color": slot_color, "alpha": 150}
                        slot_hover = True
                hovered_row_name, hovered_rect = get_row_under_position(mouse_pos)
                target_rows = get_weather_target_rows(dragging_card, hovered_row_name)
                for row_name in target_rows:
                    color = get_row_color(row_name)
                    player_rect = cfg.PLAYER_ROW_RECTS.get(row_name)
                    opponent_rect = cfg.OPPONENT_ROW_RECTS.get(row_name)
                    if player_rect:
                        drag_row_highlights.append({"rect": player_rect, "color": color, "alpha": 70})
                    if opponent_rect:
                        drag_row_highlights.append({"rect": opponent_rect, "color": color, "alpha": 70})
                if not slot_hover and hovered_rect:
                    drag_hover_highlight = {"rect": hovered_rect, "color": get_row_color(hovered_row_name or "weather"), "alpha": 120}
            elif dragging_card.row == "special" and "Command Network" in ability:
                for row_name, slot_rect in PLAYER_HORN_SLOT_RECTS.items():
                    drag_row_highlights.append({"rect": slot_rect, "color": (255, 215, 0), "alpha": 80})
                    if slot_rect.collidepoint(mouse_pos):
                        drag_hover_highlight = {"rect": slot_rect, "color": (255, 215, 0), "alpha": 140}
            elif dragging_card.row == "special":
                for rects in (cfg.PLAYER_ROW_RECTS, cfg.OPPONENT_ROW_RECTS):
                    for row_name, rect in rects.items():
                        if rect.collidepoint(mouse_pos):
                            drag_hover_highlight = {"rect": rect, "color": get_row_color(row_name), "alpha": 100}
                            break
                    if drag_hover_highlight:
                        break
            else:
                is_spy = "Deep Cover Agent" in ability
                target_rects = cfg.OPPONENT_ROW_RECTS if is_spy else cfg.PLAYER_ROW_RECTS
                for row_name, rect in target_rects.items():
                    if rect.collidepoint(mouse_pos):
                        color = (255, 120, 120) if is_spy else get_row_color(row_name)
                        drag_hover_highlight = {"rect": rect, "color": color, "alpha": hover_alpha}
                        break
    
        drag_visual_state = {
            "trail": drag_trail,
            "velocity": drag_velocity,
            "pickup_boost": drag_pickup_flash,
            "pulse": drag_pulse
        }
    
        # --- Drawing ---
        # Use mulligan background during mulligan phase, otherwise board background
        if game.game_state == "mulligan":
            screen.blit(assets["mulligan_bg"], (0, 0))
        else:
            screen.blit(assets["board"], (0, 0))
        
        separator_color = (100, 150, 200, 150)
        separator_width = 3
        glow_color = (150, 200, 255, 80)
        x_start = PLAYFIELD_LEFT
        x_end = PLAYFIELD_LEFT + PLAYFIELD_WIDTH
    
        for row_rect in list(cfg.OPPONENT_ROW_RECTS.values()) + list(cfg.PLAYER_ROW_RECTS.values()):
            y_pos = row_rect.bottom
            if row_rect in cfg.OPPONENT_ROW_RECTS.values():
                y_pos += 8
    
            pygame.draw.line(screen, glow_color, (x_start, y_pos - 2), (x_end, y_pos - 2), 1)
            pygame.draw.line(screen, glow_color, (x_start, y_pos - 1), (x_end, y_pos - 1), 1)
            pygame.draw.line(screen, separator_color, (x_start, y_pos), (x_end, y_pos), separator_width)
            pygame.draw.line(screen, glow_color, (x_start, y_pos + separator_width), (x_end, y_pos + separator_width), 1)
            pygame.draw.line(screen, glow_color, (x_start, y_pos + separator_width + 1), (x_end, y_pos + separator_width + 1), 1)
        
        # Draw ambient background effects
        ambient_effects.draw(screen)
        
        if game.game_state == "mulligan":
            # Draw mulligan UI (hand and button only, no text)
            draw_hand(
                screen,
                game.player1,
                None,
                mulligan_selected,
                dragging_card=None,
                hovered_card=hovered_card,
                hover_scale=card_hover_scale
            )
            board_renderer.draw_mulligan_button(screen, mulligan_selected)
            history_panel_rect = None
        elif game.game_state == "game_over":
            # Draw game over screen
            game_over_text = cfg.SCORE_FONT.render("GAME OVER", True, cfg.WHITE)
            screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
            
            if game.winner:
                winner_text = cfg.SCORE_FONT.render(f"{game.winner.name} WINS!", True, (100, 255, 100))
                screen.blit(winner_text, (SCREEN_WIDTH // 2 - winner_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
                
                # Record game result and show rewards
                if not hasattr(game, 'reward_shown'):
                    game.reward_shown = True
                    
                    # Record win/loss using persistence system
                    player_won = (game.winner == game.player1)
    
                    # Update Draft Run Progress
                    if hasattr(game, 'is_draft_match') and game.is_draft_match:
                        persistence = get_persistence()
                        # Update the active run
                        active_run_data = persistence.get_active_draft_run()
                        if active_run_data:
                            current_wins = active_run_data.get('wins', 0)
                            
                            if player_won:
                                current_wins += 1
                                active_run_data['wins'] = current_wins
                                
                                # Check milestones
                                msg_list = []
                                
                                if current_wins >= DraftRun.MAX_WINS: # 8 Wins
                                    msg_list.append("DRAFT CHAMPION! 8 WINS!")
                                    msg_list.append("You have conquered the galaxy!")
                                    game.draft_victory = True
                                    persistence.clear_active_draft_run()
                                    # Record stats for completed run
                                    leader_name = player_leader.get('name', 'Unknown')
                                    leader_id = player_leader.get('card_id', '')
                                    deck_power = sum(card.power for card in player_deck)
                                    persistence.record_draft_completion(
                                        leader_id=leader_id,
                                        leader_name=leader_name,
                                        faction=game.player1_faction,
                                        cards=player_deck,
                                        deck_power=deck_power,
                                        won=True,
                                        final_wins=current_wins
                                    )
                                else:
                                    # Continue Run
                                    if current_wins == DraftRun.MILESTONE_REDRAFT_LEADER: # 5 Wins
                                        active_run_data['phase'] = "redraft_leader"
                                        msg_list.append("Milestone Reached: Leader Redraft Available!")
                                    elif current_wins == DraftRun.MILESTONE_REDRAFT_CARDS: # 3 Wins
                                        active_run_data['phase'] = "redraft_cards_select"
                                        msg_list.append("Milestone Reached: Card Redraft Available!")
                                    else:
                                        # Ensure we go back to review/battle ready
                                        active_run_data['phase'] = "review"
                                    
                                    persistence.save_active_draft_run(active_run_data)
                                    msg_list.append(f"Draft Run Progress: {current_wins}/{DraftRun.MAX_WINS} Wins")
                                
                                game.draft_messages = msg_list
                                
                            else:
                                # Defeat - End Run
                                persistence.clear_active_draft_run()
                                game.draft_messages = ["Draft Run Ended", f"Final Result: {current_wins} Wins"]
                                # Record stats
                                leader_name = player_leader.get('name', 'Unknown')
                                leader_id = player_leader.get('card_id', '')
                                deck_power = sum(card.power for card in player_deck)
                                persistence.record_draft_completion(
                                    leader_id=leader_id,
                                    leader_name=leader_name,
                                    faction=game.player1_faction,
                                    cards=player_deck,
                                    deck_power=deck_power,
                                    won=False,
                                    final_wins=current_wins
                                )
                        else:
                             # Fallback if no run data found (legacy/error)
                            persistence.record_draft_completion(
                                leader_id=player_leader.get('card_id', ''),
                                leader_name=player_leader.get('name', 'Unknown'),
                                faction=game.player1_faction,
                                cards=player_deck,
                                deck_power=sum(c.power for c in player_deck),
                                won=player_won
                            )
    
                    mode_label = "lan" if LAN_MODE else "ai"
    
                    # Record rich stats summary once per game (BEFORE blocking UI)
                    try:
                        # Extract leader names robustly
                        leader_obj = game.player1.leader
                        if isinstance(leader_obj, dict):
                            leader_name = leader_obj.get('name', 'Unknown')
                        elif isinstance(leader_obj, str):
                            leader_name = leader_obj # Use ID if name unavailable
                        else:
                            leader_name = str(leader_obj) if leader_obj else 'Unknown'
    
                        opp_leader_obj = game.player2.leader
                        if isinstance(opp_leader_obj, dict):
                            opponent_leader = opp_leader_obj.get('name', 'Unknown')
                        else:
                            opponent_leader = str(opp_leader_obj) if opp_leader_obj else 'Unknown'
    
                        # Check if player lost round 1 (for comeback tracking)
                        round_history = getattr(game, "round_history", [])
                        lost_round_1 = len(round_history) > 0 and round_history[0].get("winner") == "player2"
                        # Check who went first
                        went_first = getattr(game, "player_went_first", None)
                        
                        summary = {
                            "won": player_won,
                            "player_faction": game.player1_faction,
                            "opponent_faction": game.player2_faction,
                            "leader": leader_name,
                            "opponent_leader": opponent_leader,
                            "turns": getattr(game, "turn_count", 0),
                            "mulligans": getattr(game, "player_mulligan_count", 0),
                            "abilities": getattr(game, "ability_usage", {}),
                            "cards_played": getattr(game, "cards_played_ids", []),
                            "mode": mode_label,
                            "lan_completed": LAN_MODE,
                            "lan_disconnect": False,
                            "ai_difficulty": "hard" if not LAN_MODE else None,
                            "player_rounds_won": game.player1.rounds_won,
                            "opponent_rounds_won": game.player2.rounds_won,
                            "lost_round_1": lost_round_1,
                            "went_first": went_first,
                        }
                        print(f"[stats] Recording summary: won={player_won}, leader={leader_name}")
                        print(f"[stats] cards_played={len(summary['cards_played'])}, abilities={summary['abilities']}")
                        get_persistence().record_game_summary(summary)
                        print("[stats] Summary recorded successfully")
                    except Exception as exc:
                        print(f"[stats] Unable to record summary: {exc}")
                        import traceback
                        traceback.print_exc()
    
                    if player_won:
                        record_victory(game.player1_faction, mode_label)
    
                        # FIRST: Check for leader unlock (every 3 consecutive wins)
                        persistence = get_persistence()
                        consecutive_wins = persistence.get_consecutive_wins()

                        if consecutive_wins > 0 and consecutive_wins % 3 == 0:
                            # Show leader reward screen - unless unlock all is enabled
                            if not unlock_system.is_unlock_override_enabled():
                                unlocked_leader = show_leader_reward_screen(screen, unlock_system, game.player1_faction)
                                if unlocked_leader:
                                    leader_name = unlocked_leader.get('name', 'Unknown Leader')
                                    game.unlock_message = cfg.UI_FONT.render(f"NEW LEADER UNLOCKED: {leader_name}!", True, (255, 215, 0))
                                    game.streak_message = cfg.UI_FONT.render(f"3 Win Streak! Leader unlocked!", True, (255, 150, 50))
                        
                        # SECOND: Show card reward screen (every win) - unless unlock all is enabled
                        unlock_system.record_game_result(True)
                        # Only show reward screen if unlock all is not enabled
                        if not unlock_system.is_unlock_override_enabled():
                            unlocked_card = show_card_reward_screen(screen, unlock_system, faction=game.player1_faction)
                            if unlocked_card:
                                # Add unlocked card to player's deck
                                persistence = get_persistence()
                                persistence.unlock_card(unlocked_card)
                                current_deck = persistence.get_deck(game.player1_faction)
                                current_cards = current_deck.get("cards", [])
                                if unlocked_card not in current_cards:
                                    current_cards.append(unlocked_card)
                                    persistence.set_deck(game.player1_faction, current_deck.get("leader", ""), current_cards)
                                    print(f"✓ Card {unlocked_card} added to {game.player1_faction} deck")

                                card_msg = cfg.UI_FONT.render(f"Unlocked: {UNLOCKABLE_CARDS[unlocked_card]['name']}!", True, (255, 215, 0))
                                if hasattr(game, 'unlock_message'):
                                    game.unlock_message2 = card_msg
                                else:
                                    game.unlock_message = card_msg
                        
                        # Show win streak progress
                        if not hasattr(game, 'streak_message'):
                            persistence = get_persistence()
                            streak = persistence.get_consecutive_wins()
                            if streak > 0:
                                remaining = 3 - (streak % 3)
                                if remaining == 3:
                                    remaining = 0  # Just got a leader unlock
                                game.streak_message = cfg.UI_FONT.render(f"Win Streak: {streak}! ({remaining} more for leader unlock)", True, (100, 255, 100))
                    else:
                        record_defeat(game.player1_faction, mode_label)
                        unlock_system.record_game_result(False)
            
            score_text = cfg.UI_FONT.render(f"Final Score: {game.player1.name} {game.player1.rounds_won} - {game.player2.rounds_won} {game.player2.name}", True, cfg.WHITE)
            screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2))
            
            # Show unlock messages if exist
            y_offset = 30
            if hasattr(game, 'unlock_message'):
                screen.blit(game.unlock_message, (SCREEN_WIDTH // 2 - game.unlock_message.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset))
                y_offset += 35
            if hasattr(game, 'unlock_message2'):
                screen.blit(game.unlock_message2, (SCREEN_WIDTH // 2 - game.unlock_message2.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset))
                y_offset += 35
            if hasattr(game, 'streak_message'):
                screen.blit(game.streak_message, (SCREEN_WIDTH // 2 - game.streak_message.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset))
                y_offset += 35
            
            if hasattr(game, 'draft_messages'):
                for msg in game.draft_messages:
                    if isinstance(msg, str):
                        msg_surf = cfg.UI_FONT.render(msg, True, (255, 200, 100))
                    else:
                        msg_surf = msg
                    screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset))
                    y_offset += 35
    
            if getattr(game, 'draft_victory', False):
                egg_font = pygame.font.SysFont("Arial", 48, bold=True)
                egg_text = egg_font.render("EASTER EGG UNLOCKED!", True, (255, 0, 255))
                sub_text = cfg.UI_FONT.render("Press ENTER to play STARGATE SPACE BATTLE!", True, (200, 100, 255))
                
                screen.blit(egg_text, (SCREEN_WIDTH // 2 - egg_text.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset + 20))
                screen.blit(sub_text, (SCREEN_WIDTH // 2 - sub_text.get_width() // 2, SCREEN_HEIGHT // 2 + y_offset + 70))
                y_offset += 100
            
            # Show different options based on game mode
            if hasattr(game, 'is_draft_match') and game.is_draft_match:
                # In draft mode, check if we should continue automatically
                persistence = get_persistence()
                active_run_data = persistence.get_active_draft_run()

                # Check if player won
                player_won = (game.winner == game.player1)

                if active_run_data:
                    current_wins = active_run_data.get('wins', 0)
                    if player_won and current_wins < DraftRun.MAX_WINS:  # Player won and still in draft run
                        # Show draft progress and options
                        scale = display_manager.SCALE_FACTOR
                        button_width = int(250 * scale)
                        button_height = int(55 * scale)
                        button_spacing = int(15 * scale)
                        start_y = SCREEN_HEIGHT // 2 + y_offset + int(40 * scale)
                        mouse_pos = pygame.mouse.get_pos()

                        # Progress message
                        progress_text = cfg.UI_FONT.render(f"Draft Progress: {current_wins}/{DraftRun.MAX_WINS} Wins", True, (100, 255, 100))
                        screen.blit(progress_text, (SCREEN_WIDTH // 2 - progress_text.get_width() // 2, start_y - int(50 * scale)))

                        # Define buttons
                        continue_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                        save_exit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                        quit_draft_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                        # Draw Stargwent-styled buttons
                        draw_stargwent_button(screen, continue_button, "CONTINUE DRAFT", mouse_pos,
                                              base_color=(40, 60, 40), hover_color=(60, 90, 60),
                                              border_color=(80, 180, 80), hover_border=(100, 255, 100))
                        draw_stargwent_button(screen, save_exit_button, "SAVE & EXIT", mouse_pos,
                                              base_color=(50, 50, 70), hover_color=(70, 70, 100),
                                              border_color=(100, 100, 180), hover_border=(150, 150, 255))
                        draw_stargwent_button(screen, quit_draft_button, "ABANDON DRAFT", mouse_pos,
                                              base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                              border_color=(180, 80, 80), hover_border=(255, 100, 100))

                        # Handle button clicks
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if continue_button.collidepoint(mouse_pos):
                                # Continue to next draft game
                                battle_music.stop_battle_music()
                                main()  # Restart the game for the next draft battle
                                return
                            elif save_exit_button.collidepoint(mouse_pos):
                                # Save is automatic - just exit to main menu
                                battle_music.stop_battle_music()
                                game.main_menu_requested = True
                            elif quit_draft_button.collidepoint(mouse_pos):
                                # Abandon draft run
                                persistence.clear_active_draft_run()
                                battle_music.stop_battle_music()
                                game.main_menu_requested = True
                    else:
                        # Draft completed (either won all rounds or lost) - show game over options
                        scale = display_manager.SCALE_FACTOR
                        button_width = int(250 * scale)
                        button_height = int(55 * scale)
                        button_spacing = int(20 * scale)
                        start_y = SCREEN_HEIGHT // 2 + y_offset + int(40 * scale)
                        mouse_pos = pygame.mouse.get_pos()

                        # Define buttons - different for draft mode end
                        new_draft_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                        main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                        quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                        # Draw Stargwent-styled buttons
                        draw_stargwent_button(screen, new_draft_button, "NEW DRAFT", mouse_pos,
                                              base_color=(40, 60, 40), hover_color=(60, 90, 60),
                                              border_color=(80, 180, 80), hover_border=(100, 255, 100))
                        draw_stargwent_button(screen, main_menu_button, "MAIN MENU", mouse_pos)
                        draw_stargwent_button(screen, quit_button, "QUIT", mouse_pos,
                                              base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                              border_color=(180, 80, 80), hover_border=(255, 100, 100))

                        # Handle button clicks
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if new_draft_button.collidepoint(mouse_pos):
                                game.main_menu_requested = True  # Return to menu to start new draft
                            elif main_menu_button.collidepoint(mouse_pos):
                                game.main_menu_requested = True
                            elif quit_button.collidepoint(mouse_pos):
                                pygame.quit()
                                sys.exit()
                else:
                    # No active draft run - show regular game over options
                    scale = display_manager.SCALE_FACTOR
                    button_width = int(250 * scale)
                    button_height = int(55 * scale)
                    button_spacing = int(20 * scale)
                    start_y = SCREEN_HEIGHT // 2 + y_offset + int(40 * scale)
                    mouse_pos = pygame.mouse.get_pos()

                    # Define buttons
                    rematch_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                    main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                    quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                    # Draw Stargwent-styled buttons
                    draw_stargwent_button(screen, rematch_button, "REMATCH", mouse_pos)
                    draw_stargwent_button(screen, main_menu_button, "MAIN MENU", mouse_pos)
                    draw_stargwent_button(screen, quit_button, "QUIT", mouse_pos,
                                          base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                          border_color=(180, 80, 80), hover_border=(255, 100, 100))

                    # Handle button clicks
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if rematch_button.collidepoint(mouse_pos):
                            game.restart_requested = True
                        elif main_menu_button.collidepoint(mouse_pos):
                            game.main_menu_requested = True
                        elif quit_button.collidepoint(mouse_pos):
                            pygame.quit()
                            sys.exit()

            else:
                # Regular game - show game over options with Stargwent styling
                scale = display_manager.SCALE_FACTOR
                button_width = int(250 * scale)
                button_height = int(55 * scale)
                button_spacing = int(20 * scale)
                start_y = SCREEN_HEIGHT // 2 + y_offset + int(40 * scale)
                mouse_pos = pygame.mouse.get_pos()

                # Define buttons
                rematch_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y, button_width, button_height)
                main_menu_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + button_height + button_spacing, button_width, button_height)
                quit_button = pygame.Rect(SCREEN_WIDTH // 2 - button_width // 2, start_y + 2 * (button_height + button_spacing), button_width, button_height)

                # Draw Stargwent-styled buttons
                draw_stargwent_button(screen, rematch_button, "REMATCH", mouse_pos)
                draw_stargwent_button(screen, main_menu_button, "MAIN MENU", mouse_pos)
                draw_stargwent_button(screen, quit_button, "QUIT", mouse_pos,
                                      base_color=(70, 40, 40), hover_color=(100, 50, 50),
                                      border_color=(180, 80, 80), hover_border=(255, 100, 100))

                # Handle button clicks
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if rematch_button.collidepoint(mouse_pos):
                        game.restart_requested = True
                    elif main_menu_button.collidepoint(mouse_pos):
                        game.main_menu_requested = True
                    elif quit_button.collidepoint(mouse_pos):
                        pygame.quit()
                        sys.exit()
            history_panel_rect = None
        if ui_state != UIState.LEADER_MATCHUP and game.game_state != "game_over":
            board_renderer.draw_board(screen, game, selected_card, dragging_card=dragging_card,
                       drag_hover_highlight=drag_hover_highlight,
                       drag_row_highlights=None)  # Add logic for drag row highlights if needed
            board_renderer.draw_scores(screen, game, anim_manager, render_static=False)
            
            # Draw row scores using render_engine (special specialized boxes)
    
            # Auto-start Hathor steal animation (LAN/AI) if pending and not started yet
            steal_info = getattr(game, "hathor_steal_info", None)
            if steal_info and not steal_info.get("animation_started"):
                card = steal_info.get("card")
                target_row = steal_info.get("target_row", "close")
                if card and hasattr(card, "rect"):
                    start_pos = (card.rect.centerx, card.rect.centery)
                    target_rect = cfg.PLAYER_ROW_RECTS.get(target_row) or cfg.OPPONENT_ROW_RECTS.get(target_row)
                    end_pos = (target_rect.centerx, target_rect.centery) if target_rect else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    h_anim = HathorStealAnimation(
                        card,
                        start_pos,
                        end_pos,
                        on_finish=lambda: game.switch_turn()
                    )
                    anim_manager.add_animation(h_anim)
                    steal_info["animation_started"] = True
    
            # 1. Sidebar Positioning (No More Percentages)
            panel_width = 220 # Narrower panel to fit next to scores
            history_rect = pygame.Rect(
                cfg.SIDEBAR_X + 260,
                pct_y(0.12),
                panel_width,
                pct_y(0.80) - pct_y(0.12)
            )
            history_panel_rect = history_rect
    
            # 2. Draw Score Boxes (Anchored to Sidebar start + padding)
            draw_row_score_boxes(screen, game)

            # Always show game history in the HUD panel
            history_entry_hitboxes, history_scroll_limit = draw_history_panel(
                screen,
                game,
                history_rect,
                history_scroll_offset,
                pygame.mouse.get_pos()
            )
    
            # Round and Turn indicator in HUD (horizontal layout)
            round_font = pygame.font.SysFont("Arial", max(24, int(26 * SCALE_FACTOR)), bold=True)
            round_text = round_font.render(f"Round {game.round_number}", True, cfg.WHITE)
            turn_color = (120, 255, 160) if game.current_player == game.player1 else (255, 140, 140)
            turn_text = round_font.render("YOUR TURN" if game.current_player == game.player1 else "ENEMY TURN", True, turn_color)
            # Draw on same line: "Round X - YOUR TURN"
            hud_text_x = HUD_LEFT + int(HUD_WIDTH * 0.05)
            hud_text_y = pct_y(0.04)
            screen.blit(round_text, (hud_text_x, hud_text_y))
            screen.blit(turn_text, (hud_text_x, hud_text_y + round_text.get_height() + 4))
    
            command_bar_surface = pygame.Surface((SCREEN_WIDTH, COMMAND_BAR_HEIGHT), pygame.SRCALPHA)
            command_bar_surface.fill((10, 20, 35, 200))
            pygame.draw.line(command_bar_surface, (80, 120, 180), (0, 0), (SCREEN_WIDTH, 0), 2)
            screen.blit(command_bar_surface, (0, COMMAND_BAR_Y))
    
            board_renderer.draw_pass_button(screen, game, HUD_PASS_BUTTON_RECT)

            # Draw keyboard highlight for Pass button
            if keyboard_button_cursor == 0 and game.current_player == game.player1:
                highlight_rect = HUD_PASS_BUTTON_RECT.inflate(12, 12)
                pygame.draw.rect(screen, (255, 255, 100), highlight_rect, width=3, border_radius=highlight_rect.width // 2)
    
            draw_hand(
                screen,
                game.player1,
                selected_card,
                dragging_card=dragging_card,
                hovered_card=hovered_card,
                hover_scale=card_hover_scale,
                drag_visuals=drag_visual_state
            )
            draw_opponent_hand(screen, game.player2)

            # Draw keyboard navigation hint when active
            if game.current_player == game.player1 and ui_state == UIState.PLAYING:
                hint_font = pygame.font.SysFont("Arial", max(18, int(20 * SCALE_FACTOR)))
                hint_text = None

                if keyboard_mode_active and keyboard_hand_cursor >= 0:
                    if keyboard_hand_cursor < len(game.player1.hand):
                        card = game.player1.hand[keyboard_hand_cursor]
                        if card.row in ("agile", "weather", "special"):
                            hint_text = "←/→: Card | ↑/↓: Row | F: Play | TAB: Buttons"
                        else:
                            hint_text = "←/→: Card | F: Play | SPACE: Preview | TAB: Buttons"
                elif keyboard_button_cursor >= 0:
                    btn_name = "PASS" if keyboard_button_cursor == 0 else "FACTION POWER"
                    hint_text = f"↑/↓: Switch | SPACE: {btn_name} | ←/→: Cards"

                if hint_text:
                    hint_surf = hint_font.render(hint_text, True, (180, 200, 220))
                    hint_x = (SCREEN_WIDTH - hint_surf.get_width()) // 2
                    hint_y = COMMAND_BAR_Y - hint_surf.get_height() - 8
                    hint_bg = pygame.Surface((hint_surf.get_width() + 16, hint_surf.get_height() + 8), pygame.SRCALPHA)
                    hint_bg.fill((20, 30, 50, 180))
                    screen.blit(hint_bg, (hint_x - 8, hint_y - 4))
                    screen.blit(hint_surf, (hint_x, hint_y))
    
            mouse_pos = pygame.mouse.get_pos()
            ai_area = LEADER_TOP_RECT.copy()
            player_area = LEADER_BOTTOM_RECT.copy()
            ai_stack = draw_leader_column(
                screen,
                game.player2,
                ai_area,
                ability_ready=ai_ability_ready,
                faction_power_ready=bool(game.player2.faction_power and game.player2.faction_power.is_available()),
                hover_pos=mouse_pos
            )
            player_stack = draw_leader_column(
                screen,
                game.player1,
                player_area,
                ability_ready=player_ability_ready,
                faction_power_ready=bool(game.player1.faction_power and game.player1.faction_power.is_available()),
                hover_pos=mouse_pos
            )
    
            ai_leader_rect = ai_stack["leader_rect"]
            ai_ability_rect = ai_stack["ability_rect"]
            ai_faction_button_rect = ai_stack["faction_rect"]
            ai_special_button_rect = ai_stack.get("special_rect")
            ai_special_button_kind = ai_stack.get("special_kind")
            player_leader_rect = player_stack["leader_rect"]
            player_ability_rect = player_stack["ability_rect"]
            player_faction_button_rect = player_stack["faction_rect"]
            player_special_button_rect = player_stack.get("special_rect")
            player_special_button_kind = player_stack.get("special_kind")
            discard_rect = player_stack.get("discard_rect") or discard_rect
    
            iris_button_rect = player_special_button_rect if player_special_button_kind == "iris" else None
            ring_transport_button_rect = player_special_button_rect if player_special_button_kind == "rings" else None

            # Draw keyboard highlight for Faction Power button
            if keyboard_button_cursor == 1 and game.current_player == game.player1 and player_faction_button_rect:
                highlight_rect = player_faction_button_rect.inflate(8, 8)
                pygame.draw.rect(screen, (255, 255, 100), highlight_rect, width=3, border_radius=8)
    
            if ai_turn_in_progress:
                total_cards = len(game.player2.hand)
                if total_cards > 0:
                    card_spacing = int(CARD_WIDTH * 0.125)
                    positions, _ = _compute_hand_positions(total_cards, CARD_WIDTH, card_spacing)
                    left_edge = positions[0]
                    right_edge = positions[-1] + CARD_WIDTH
                    opponent_hand_area = pygame.Rect(left_edge, opponent_hand_area_y,
                                                     right_edge - left_edge, CARD_HEIGHT)
                    ai_turn_anim.draw(screen, cfg.UI_FONT, opponent_hand_area)
        
        # Draw animations and effects on top of everything (but not during game_over)
        if game.game_state != "game_over":
            anim_manager.draw_effects(screen)
            anim_manager.draw_weather(screen)
        
        # Draw Iris Power effect (full-screen cinematic) - not during game_over
        if faction_power_effect and game.game_state != "game_over":
            faction_power_effect.draw(screen)

        # Draw Ring Transportation animation - not during game_over
        if ring_transport_animation and game.game_state != "game_over":
            ring_transport_animation.draw(screen)
        
        # Draw visual feedback for ring transport selection mode (not during game_over)
        if ring_transport_selection and game.game_state != "game_over":
            # Dim the screen slightly
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0, 0))
            
            # Draw instruction text
            hint_font = pygame.font.Font(None, 48)
            hint_text = hint_font.render("Click a CLOSE COMBAT unit to return to hand", True, (255, 200, 100))
            hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
            
            # Draw text shadow
            shadow_text = hint_font.render("Click a CLOSE COMBAT unit to return to hand", True, (0, 0, 0))
            screen.blit(shadow_text, (hint_rect.x + 3, hint_rect.y + 3))
            screen.blit(hint_text, hint_rect)
            
            # Highlight ONLY close combat cards on board with golden glow
            row_cards = game.player1.board.get("close", [])
            for card in row_cards:
                if hasattr(card, 'rect'):
                    # Golden glow around selectable cards
                    glow_surf = pygame.Surface((card.rect.width + 20, card.rect.height + 20), pygame.SRCALPHA)
                    glow_alpha = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.005))
                    pygame.draw.rect(glow_surf, (255, 200, 100, glow_alpha), glow_surf.get_rect(), border_radius=10)
                    screen.blit(glow_surf, (card.rect.x - 10, card.rect.y - 10))
        
        # Draw visual feedback when dragging Ring Transport over valid targets
        if dragging_card and "Ring Transport" in (dragging_card.ability or ""):
            # Highlight valid targets
            for card, rect in decoy_valid_targets:
                # Golden glow around valid cards
                glow_surf = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
                glow_alpha = int(100 + 80 * math.sin(pygame.time.get_ticks() * 0.008))
                pygame.draw.rect(glow_surf, (100, 200, 255, glow_alpha), glow_surf.get_rect(), border_radius=8)
                screen.blit(glow_surf, (rect.x - 10, rect.y - 10))
            
            # Draw laser beam to hovered target
            if decoy_drag_target and hasattr(decoy_drag_target, 'rect'):
                # Animated laser beam from dragged card to target
                beam_start = (dragging_card.rect.centerx, dragging_card.rect.centery)
                beam_end = (decoy_drag_target.rect.centerx, decoy_drag_target.rect.centery)
                
                # Pulsing beam effect
                pulse = math.sin(pygame.time.get_ticks() * 0.01) * 0.3 + 0.7
                beam_color = (int(150 * pulse), int(220 * pulse), int(255 * pulse))
                beam_width = int(4 + 2 * math.sin(pygame.time.get_ticks() * 0.01))
                
                # Draw main beam
                pygame.draw.line(screen, beam_color, beam_start, beam_end, beam_width)
                
                # Draw glow along the beam
                glow_surf = pygame.Surface((abs(beam_end[0] - beam_start[0]) + 40, 
                                           abs(beam_end[1] - beam_start[1]) + 40), pygame.SRCALPHA)
                glow_start = (20, 20) if beam_start[0] < beam_end[0] else (glow_surf.get_width() - 20, 20)
                glow_end = (glow_surf.get_width() - 20, glow_surf.get_height() - 20) if beam_start[0] < beam_end[0] else (20, glow_surf.get_height() - 20)
                pygame.draw.line(glow_surf, (*beam_color, int(100 * pulse)), glow_start, glow_end, beam_width + 6)
                screen.blit(glow_surf, (min(beam_start[0], beam_end[0]) - 20, min(beam_start[1], beam_end[1]) - 20))
                
                # Draw glowing circle at target
                target_glow_size = int(20 + 10 * math.sin(pygame.time.get_ticks() * 0.015))
                target_glow = pygame.Surface((target_glow_size * 2, target_glow_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(target_glow, (*beam_color, int(150 * pulse)), 
                                 (target_glow_size, target_glow_size), target_glow_size)
                screen.blit(target_glow, (decoy_drag_target.rect.centerx - target_glow_size, 
                                         decoy_drag_target.rect.centery - target_glow_size))
        
        # Draw card inspection overlay (on top of EVERYTHING)
        if inspected_card:
            selection_overlays.draw_card_inspection_overlay(screen, inspected_card, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        if inspected_leader:
            selection_overlays.draw_leader_inspection_overlay(screen, inspected_leader, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Medical Evac selection overlay
        medic_card_rects = []
        if ui_state == UIState.MEDIC_SELECT:
            medic_valid_cards = game.get_medic_valid_cards(game.player1)
            if not medic_valid_cards:
                # No valid targets (discard pile empty) — exit selection and end turn cleanly
                ui_state = UIState.PLAYING
                medic_card_played = None
                game.add_history_event(
                    "ability",
                    f"{game.player1.name}'s medic had no targets to revive",
                    "player",
                    icon="+"
                )
                game.player1.calculate_score()
                game.player2.calculate_score()
                game.last_turn_actor = game.player1
                game.switch_turn()
            else:
                medic_card_rects = selection_overlays.draw_medic_selection_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
                
                # Handle clicks on medic cards
                mouse_pos = pygame.mouse.get_pos()
                mouse_clicked = pygame.mouse.get_pressed()[0]
                
                if mouse_clicked:
                    for card, rect in medic_card_rects:
                        if rect.collidepoint(mouse_pos):
                            # Player selected this card to revive
                            game.trigger_medic(game.player1, card)
                            game.player1.calculate_score()
                            game.player2.calculate_score()
                            game.last_turn_actor = game.player1
                            game.switch_turn()
                            if network_proxy:
                                network_proxy.send_medic_choice(card.id)
                            ui_state = UIState.PLAYING
                            medic_card_played = None
                            pygame.time.wait(200)  # Small delay to prevent double-click
                            break
        
        # Ring Transport selection overlay
        decoy_card_rects = []
        if ui_state == UIState.DECOY_SELECT:
            decoy_card_rects = selection_overlays.draw_decoy_selection_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            # Handle clicks on decoy cards
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = pygame.mouse.get_pressed()[0]
            
            if mouse_clicked:
                for card, rect in decoy_card_rects:
                    if rect.collidepoint(mouse_pos):
                        # Player selected this card to return to hand
                        if game.apply_decoy(card):
                            game.player1.calculate_score()
                            game.player2.calculate_score()
                            game.last_turn_actor = game.player1
                            game.switch_turn()
                            if network_proxy:
                                network_proxy.send_decoy_choice(card.id)
                            ui_state = UIState.PLAYING
                            decoy_card_played = None
                            pygame.time.wait(200)  # Small delay to prevent double-click
                        break
        
        # Jonas Quinn peek overlay
        if ui_state == UIState.JONAS_PEEK:
            selection_overlays.draw_jonas_peek_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
    
            # Handle click to close
            if pygame.mouse.get_pressed()[0]:
                ui_state = UIState.PLAYING
                # Clear the tracked cards after viewing
                game.opponent_drawn_cards = []
                pygame.time.wait(200)
        
        # Ba'al Clone selection overlay
        baal_card_rects = []
        if ui_state == UIState.BAAL_CLONE_SELECT:
            baal_card_rects = selection_overlays.draw_baal_clone_overlay(screen, game, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in baal_card_rects:
                    if rect.collidepoint(mouse_pos):
                        # Clone this card - create proper independent copy
                        import copy
                        from cards import load_card_image
                        cloned_card = copy.copy(card)
                        # Create a new rect for the clone (avoid sharing the same rect object)
                        cloned_card.rect = pygame.Rect(0, 0, cfg.CARD_WIDTH, cfg.CARD_HEIGHT)
                        # ALWAYS load image fresh for cloned card to ensure it displays correctly
                        load_card_image(cloned_card)
                        # Clear animation flags
                        cloned_card.in_transit = False
                        # Find which row the original is in
                        for row_name, row_cards in game.player1.board.items():
                            if card in row_cards:
                                game.player1.board[row_name].append(cloned_card)
                                break
                        game.player1.calculate_score()
                        ui_state = UIState.PLAYING
                        pygame.time.wait(200)
                        break
        
        # Vala selection overlay
        vala_card_rects = []
        if ui_state == UIState.VALA_SELECT:
            vala_card_rects = selection_overlays.draw_vala_selection_overlay(screen, vala_cards_to_choose, SCREEN_WIDTH, SCREEN_HEIGHT)
            
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in vala_card_rects:
                    if rect.collidepoint(mouse_pos):
                        # Add chosen card to hand
                        game.player1.hand.append(card)
                        # Return unchosen cards to deck
                        for c in vala_cards_to_choose:
                            if c != card:
                                game.player1.deck.append(c)
                        game.rng.shuffle(game.player1.deck)
                        ui_state = UIState.PLAYING
                        vala_cards_to_choose = []
                        pygame.time.wait(200)
                        break
    
        # Catherine Langford selection overlay
        catherine_card_rects = []
        if ui_state == UIState.CATHERINE_SELECT:
            catherine_card_rects = selection_overlays.draw_catherine_selection_overlay(screen, catherine_cards_to_choose, SCREEN_WIDTH, SCREEN_HEIGHT)
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in catherine_card_rects:
                    if rect.collidepoint(mouse_pos):
                        revealed_ids = [c.id for c in catherine_cards_to_choose]
                        game.catherine_play_chosen_card(game.player1, card)
                        if network_proxy:
                            network_proxy.send_leader_ability(
                                "Ancient Knowledge",
                                {"choice_id": card.id, "revealed_ids": revealed_ids}
                            )
                        ui_state = UIState.PLAYING
                        catherine_cards_to_choose = []
                        pygame.time.wait(200)
                        break
    
        # Generic leader choice overlay (Jonas Quinn, Ba'al, etc.)
        leader_choice_rects = []
        if pending_leader_choice:
            # Sync state if needed
            if ui_state != UIState.LEADER_CHOICE_SELECT:
                ui_state = UIState.LEADER_CHOICE_SELECT
                
            leader_choice_rects = selection_overlays.draw_leader_choice_overlay(screen, pending_leader_choice, SCREEN_WIDTH, SCREEN_HEIGHT)
            mouse_pos = pygame.mouse.get_pos()
            if pygame.mouse.get_pressed()[0]:
                for card, rect in leader_choice_rects:
                    if rect.collidepoint(mouse_pos):
                        ability_name = pending_leader_choice.get("ability", "")
                        if ability_name == "Eidetic Memory":
                            game.jonas_memorize_card(game.player1, card)
                            if network_proxy:
                                network_proxy.send_leader_ability(
                                    "Eidetic Memory",
                                    {"card_id": card.id}
                                )
                        elif ability_name == "System Lord's Cunning":
                            game.baal_resurrect_card(game.player1, card)
                            if network_proxy:
                                network_proxy.send_leader_ability(
                                    "System Lord's Cunning",
                                    {"choice_id": card.id}
                                )
                        pending_leader_choice = None
                        ui_state = UIState.PLAYING
                        pygame.time.wait(200)
                        break
    
        # Thor move mode - simple visual indicator
        if ui_state == UIState.THOR_MOVE_SELECT:
            # Draw indicator
            indicator_font = pygame.font.Font(None, 48)
            indicator_text = indicator_font.render("THOR: Click a unit to move, then click destination row", True, (50, 200, 150))
            indicator_rect = indicator_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
            
            # Semi-transparent background
            bg_surf = pygame.Surface((indicator_rect.width + 40, indicator_rect.height + 20), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 180))
            screen.blit(bg_surf, (indicator_rect.x - 20, indicator_rect.y - 10))
            screen.blit(indicator_text, indicator_rect)
            
            # Handle clicks
            if pygame.mouse.get_pressed()[0]:
                mouse_pos = pygame.mouse.get_pos()
                
                if not thor_selected_unit:
                    # First click: select unit
                    for row_cards in game.player1.board.values():
                        for card in row_cards:
                            if hasattr(card, 'rect') and card.rect.collidepoint(mouse_pos):
                                thor_selected_unit = card
                                pygame.time.wait(200)
                                break
                        if thor_selected_unit:
                            break
                else:
                    # Second click: select destination row
                    for row_name, rect in cfg.PLAYER_ROW_RECTS.items():
                        if rect.collidepoint(mouse_pos):
                            # Move the unit
                            for source_row, row_cards in game.player1.board.items():
                                if thor_selected_unit in row_cards:
                                    row_cards.remove(thor_selected_unit)
                                    game.player1.board[row_name].append(thor_selected_unit)
                                    game.player1.calculate_score()
                                    ui_state = UIState.PLAYING
                                    thor_selected_unit = None
                                    pygame.time.wait(200)
                                    break
                            break
        
        # Discard pile viewer overlay
        if ui_state == UIState.DISCARD_VIEW:
            selection_overlays.draw_discard_viewer(screen, game.player1.discard_pile, SCREEN_WIDTH, SCREEN_HEIGHT, discard_scroll)
    
        # Context popup for leader column buttons
        if button_info_popup and ui_state != UIState.PAUSED and not inspected_card and not inspected_leader:
            expires_at = button_info_popup.get("expires_at")
            if expires_at and pygame.time.get_ticks() > expires_at:
                button_info_popup = None
            else:
                draw_button_info_popup(screen, button_info_popup)
        
        # Pause menu overlay
        if ui_state == UIState.PAUSED:
            # Semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            # Pause menu
            menu_width = 500
            menu_height = 480
            menu_x = (SCREEN_WIDTH - menu_width) // 2
            menu_y = (SCREEN_HEIGHT - menu_height) // 2

            # Menu background
            pygame.draw.rect(screen, (30, 30, 40), (menu_x, menu_y, menu_width, menu_height), border_radius=15)
            pygame.draw.rect(screen, (100, 150, 200), (menu_x, menu_y, menu_width, menu_height), 5, border_radius=15)

            # Title
            pause_font = pygame.font.SysFont("Arial", 56, bold=True)
            title_text = pause_font.render("PAUSED", True, (200, 200, 200))
            title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, menu_y + 70))
            screen.blit(title_text, title_rect)

            # Buttons
            button_font = pygame.font.SysFont("Arial", 32, bold=True)
            button_width = 350
            button_height = 55
            button_x = (SCREEN_WIDTH - button_width) // 2
            button_spacing = 70
            mouse_pos = pygame.mouse.get_pos()

            # Resume button
            resume_button = pygame.Rect(button_x, menu_y + 140, button_width, button_height)
            resume_hover = resume_button.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (70, 200, 70) if resume_hover else (50, 160, 50), resume_button, border_radius=10)
            pygame.draw.rect(screen, (100, 255, 100) if resume_hover else (80, 180, 80), resume_button, 2, border_radius=10)
            resume_text = button_font.render("RESUME", True, (255, 255, 255))
            resume_rect = resume_text.get_rect(center=resume_button.center)
            screen.blit(resume_text, resume_rect)

            # Options button
            options_button = pygame.Rect(button_x, menu_y + 140 + button_spacing, button_width, button_height)
            options_hover = options_button.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (80, 140, 200) if options_hover else (60, 100, 160), options_button, border_radius=10)
            pygame.draw.rect(screen, (120, 180, 255) if options_hover else (80, 140, 200), options_button, 2, border_radius=10)
            options_text = button_font.render("OPTIONS", True, (255, 255, 255))
            options_rect = options_text.get_rect(center=options_button.center)
            screen.blit(options_text, options_rect)

            # Main Menu button
            main_menu_button = pygame.Rect(button_x, menu_y + 140 + button_spacing * 2, button_width, button_height)
            main_menu_hover = main_menu_button.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (200, 160, 60) if main_menu_hover else (160, 120, 40), main_menu_button, border_radius=10)
            pygame.draw.rect(screen, (255, 200, 100) if main_menu_hover else (180, 140, 60), main_menu_button, 2, border_radius=10)
            menu_text = button_font.render("MAIN MENU", True, (255, 255, 255))
            menu_rect = menu_text.get_rect(center=main_menu_button.center)
            screen.blit(menu_text, menu_rect)

            # Quit button
            quit_button = pygame.Rect(button_x, menu_y + 140 + button_spacing * 3, button_width, button_height)
            quit_hover = quit_button.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (200, 70, 70) if quit_hover else (160, 50, 50), quit_button, border_radius=10)
            pygame.draw.rect(screen, (255, 100, 100) if quit_hover else (180, 70, 70), quit_button, 2, border_radius=10)
            quit_text = button_font.render("QUIT GAME", True, (255, 255, 255))
            quit_rect = quit_text.get_rect(center=quit_button.center)
            screen.blit(quit_text, quit_rect)

            # Hint text
            hint_font = pygame.font.SysFont("Arial", 18)
            hint_text = hint_font.render("Press ESC to resume | F11 for fullscreen", True, (140, 140, 160))
            hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, menu_y + menu_height - 25))
            screen.blit(hint_text, hint_rect)

            # Handle pause menu clicks
            if event and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if resume_button.collidepoint(event.pos):
                    ui_state = UIState.PLAYING
                elif options_button.collidepoint(event.pos):
                    # Open settings menu
                    from game_settings import run_settings_menu
                    run_settings_menu(screen)
                elif main_menu_button.collidepoint(event.pos):
                    battle_music.stop_battle_music()
                    main()
                    return
                elif quit_button.collidepoint(event.pos):
                    battle_music.stop_battle_music()
                    pygame.quit()
                    sys.exit()
    
        # LAN: Waiting for Opponent Overlay
        if LAN_MODE and game.current_player != game.player1 and not game.game_over and ui_state == UIState.PLAYING:
            # Draw transparent overlay
            wait_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            wait_overlay.fill((0, 0, 0, 100)) # Darken slightly
            screen.blit(wait_overlay, (0, 0))
            
            # Draw Text
            wait_font = pygame.font.SysFont("Arial", 48, bold=True)
            wait_text = wait_font.render("WAITING FOR OPPONENT...", True, (255, 255, 255))
            wait_rect = wait_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            
            # Draw text background
            pygame.draw.rect(screen, (0, 0, 0, 150), wait_rect.inflate(40, 20), border_radius=10)
            screen.blit(wait_text, wait_rect)
    
        # Debug overlay: FPS counter and performance stats (v4.3.1)
        if DEBUG_MODE:
            current_fps = clock.get_fps()
            # FPS counter (top-left corner)
            fps_text = cfg.UI_FONT.render(f"FPS: {current_fps:.1f}", True, (0, 255, 0))
            fps_bg = pygame.Surface((fps_text.get_width() + 10, fps_text.get_height() + 6), pygame.SRCALPHA)
            fps_bg.fill((0, 0, 0, 180))
            screen.blit(fps_bg, (8, 8))
            screen.blit(fps_text, (13, 11))

        pygame.display.flip()
    
    battle_music.stop_battle_music()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
