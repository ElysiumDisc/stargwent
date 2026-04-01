"""UI drawing for the space shooter — infinite survival mode."""

import pygame
import math

from .entities import PowerUp
from .upgrades import UPGRADES, EVOLUTIONS, RARITY_COLORS

# Font cache to avoid per-frame SysFont allocation
_font_cache = {}


def _get_cached_font(size, bold=False):
    """Return a cached pygame SysFont."""
    key = (size, bold)
    font = _font_cache.get(key)
    if font is None:
        font = pygame.font.SysFont("Arial", size, bold=bold)
        _font_cache[key] = font
    return font


def draw_ui(game, surface):
    """Draw game UI overlay (all screen-space, no camera)."""
    # Survival timer (centered, large)
    mins = int(game.survival_seconds) // 60
    secs = int(game.survival_seconds) % 60
    timer_text = game.ui_font.render(f"{mins:02d}:{secs:02d}", True, (255, 200, 100))
    surface.blit(timer_text, (game.screen_width // 2 - timer_text.get_width() // 2, 80))

    # Difficulty tier label
    tier_label = game.spawner.get_difficulty_label()
    tier_color = _get_tier_color(tier_label)
    tier_text = game.small_font.render(tier_label, True, tier_color)
    surface.blit(tier_text, (game.screen_width // 2 - tier_text.get_width() // 2, 115))

    # Enemies alive count
    enemies_text = game.small_font.render(f"Enemies: {len(game.ai_ships)}", True, (255, 100, 100))
    surface.blit(enemies_text, (game.screen_width // 2 - enemies_text.get_width() // 2, 140))

    # Score display (top-left)
    score_text = game.ui_font.render(f"SCORE: {game.score:,}", True, (255, 215, 0))
    surface.blit(score_text, (20, 20))

    # Score breakdown hint
    score_hint = game.small_font.render(f"Enemies: {game.enemies_defeated} | Asteroids: {game.asteroids_destroyed}", True, (180, 180, 180))
    surface.blit(score_hint, (20, 55))

    # Kill counter (top-right area)
    kill_text = game.small_font.render(f"Kills: {game.total_kills}", True, (255, 200, 100))
    surface.blit(kill_text, (game.screen_width - kill_text.get_width() - 20, 80))

    # Kill streak & combo display
    if game.kill_streak >= 3:
        tier = getattr(game, 'kill_streak_tier', 0)
        mult = getattr(game, 'kill_streak_mult', 1.0)
        tier_colors = {0: (255, 100, 50), 1: (255, 255, 255), 2: (80, 140, 255),
                       3: (180, 80, 255), 4: (255, 200, 50)}
        streak_color = tier_colors.get(tier, (255, 100, 50))
        pulse = 1.0 + math.sin(pygame.time.get_ticks() * 0.01) * 0.15
        streak_size = int(32 * pulse) + tier * 2
        streak_font = _get_cached_font(streak_size, bold=True)
        label = f"STREAK x{game.kill_streak}!"
        if mult > 1.0:
            label += f" ({mult:.1f}x DMG)"
        streak_surf = streak_font.render(label, True, streak_color)
        sx = game.screen_width - streak_surf.get_width() - 20
        # Glow ring for tier 3+ (purple/gold)
        if tier >= 3:
            glow_r = streak_surf.get_width() // 2 + 10
            glow_surf = pygame.Surface((glow_r * 2, streak_surf.get_height() + 20), pygame.SRCALPHA)
            glow_alpha = int(60 + 30 * math.sin(pygame.time.get_ticks() * 0.008))
            pygame.draw.ellipse(glow_surf, (*streak_color[:3], glow_alpha),
                              (0, 0, glow_r * 2, streak_surf.get_height() + 20))
            surface.blit(glow_surf, (sx + streak_surf.get_width() // 2 - glow_r, 100))
        surface.blit(streak_surf, (sx, 110))

    # XP bar (below health/shield bars area, left side)
    xp_bar_x = 20
    xp_bar_y = 80
    xp_bar_w = 200
    xp_bar_h = 12
    level_text = game.small_font.render(f"Lv.{game.level}", True, (100, 255, 100))
    surface.blit(level_text, (xp_bar_x, xp_bar_y))
    bar_x = xp_bar_x + level_text.get_width() + 8
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, xp_bar_y + 2, xp_bar_w, xp_bar_h))
    xp_pct = game.xp / max(game.xp_to_next, 1)
    pygame.draw.rect(surface, (100, 255, 100), (bar_x, xp_bar_y + 2, int(xp_bar_w * xp_pct), xp_bar_h))
    pygame.draw.rect(surface, (150, 255, 150), (bar_x, xp_bar_y + 2, xp_bar_w, xp_bar_h), 1)

    # Active power-ups indicator (top-right)
    if game.active_powerups:
        powerup_y = 150 if game.kill_streak >= 3 else 110
        for ptype, remaining in game.active_powerups.items():
            if remaining > 0:
                props = PowerUp.TYPES.get(ptype, {})
                name = props.get("name", ptype)
                duration = props.get("duration", 1)
                pct = remaining / max(duration, 1)

                box_width = 150
                box_height = 30
                box_x = game.screen_width - box_width - 20

                pygame.draw.rect(surface, (30, 30, 50),
                               (box_x, powerup_y, box_width, box_height), border_radius=5)
                bar_width = int((box_width - 10) * pct)
                color = props.get("color", (100, 200, 255))
                pygame.draw.rect(surface, color,
                               (box_x + 5, powerup_y + 5, bar_width, box_height - 10), border_radius=3)
                text = game.small_font.render(name, True, (255, 255, 255))
                surface.blit(text, (box_x + 10, powerup_y + 5))

                powerup_y += box_height + 5

    # Active upgrades display (bottom of screen, colored icon squares)
    if game.upgrades:
        icon_size = 28
        icon_spacing = 34
        active_upgrades = [(name, count) for name, count in game.upgrades.items() if count > 0]
        # Also show evolutions
        for evo_name in game.evolutions:
            if evo_name in EVOLUTIONS:
                active_upgrades.append((evo_name, "E"))
        total_icons_w = len(active_upgrades) * icon_spacing
        icon_x = (game.screen_width - total_icons_w) // 2
        icon_y = game.screen_height - 65

        # Semi-transparent background strip
        if active_upgrades:
            strip_rect = pygame.Rect(icon_x - 5, icon_y - 3, total_icons_w + 10, icon_size + 14)
            strip_surf = pygame.Surface((strip_rect.width, strip_rect.height), pygame.SRCALPHA)
            strip_surf.fill((0, 0, 0, 100))
            surface.blit(strip_surf, strip_rect.topleft)

        mouse_pos = pygame.mouse.get_pos()
        for name, count in active_upgrades:
            is_evolution = name in EVOLUTIONS
            if is_evolution:
                evo_info = EVOLUTIONS[name]
                info = {"icon": "E", "color": (255, 215, 0), "name": evo_info["name"]}
            else:
                info = UPGRADES.get(name, {})
            color = info.get("color", (200, 200, 200))

            # Draw colored square
            sq_rect = pygame.Rect(icon_x, icon_y, icon_size, icon_size)
            pygame.draw.rect(surface, color, sq_rect, border_radius=4)
            if is_evolution:
                # Gold border for evolutions
                pygame.draw.rect(surface, (255, 215, 0), sq_rect, 2, border_radius=4)
            else:
                pygame.draw.rect(surface, (255, 255, 255), sq_rect, 1, border_radius=4)

            # Icon text
            icon_text = info.get("icon", "?")
            icon_surf = game.tiny_font.render(icon_text, True, (0, 0, 0))
            surface.blit(icon_surf, (icon_x + (icon_size - icon_surf.get_width()) // 2,
                                     icon_y + (icon_size - icon_surf.get_height()) // 2))

            # Stack count
            if not is_evolution:
                count_surf = game.count_font.render(str(count), True, (255, 255, 255))
                surface.blit(count_surf, (icon_x + icon_size - 6, icon_y + icon_size - 8))

            # Hover tooltip
            if sq_rect.collidepoint(mouse_pos):
                tooltip_text = info.get('name', name)
                if not is_evolution:
                    tooltip_text += f" x{count}"
                tooltip_surf = game.small_font.render(tooltip_text, True, (255, 255, 255))
                tt_bg = pygame.Surface((tooltip_surf.get_width() + 10, tooltip_surf.get_height() + 6), pygame.SRCALPHA)
                tt_bg.fill((0, 0, 0, 180))
                surface.blit(tt_bg, (icon_x - 5, icon_y - 28))
                surface.blit(tooltip_surf, (icon_x, icon_y - 25))

            icon_x += icon_spacing

    # Player faction label
    player_label = game.ui_font.render(game.player_faction.upper(), True, game.player_ship.laser_color)
    surface.blit(player_label, (50, game.screen_height - 90))

    # Thruster boost energy bar
    boost_x = 50
    boost_y = game.screen_height - 62
    boost_bar_w = 140
    boost_bar_h = 6
    ship = game.player_ship
    boost_pct = ship.thruster_boost_energy / ship.thruster_boost_max
    boost_label_color = (255, 200, 100) if ship.thruster_boost_active else (120, 120, 150)
    boost_label = game.tiny_font.render("[SHIFT] BOOST", True, boost_label_color)
    surface.blit(boost_label, (boost_x, boost_y - 14))
    pygame.draw.rect(surface, (30, 30, 50), (boost_x, boost_y, boost_bar_w, boost_bar_h))
    bar_color = (255, 200, 50) if ship.thruster_boost_active else (100, 180, 255)
    pygame.draw.rect(surface, bar_color, (boost_x, boost_y, int(boost_bar_w * boost_pct), boost_bar_h))
    pygame.draw.rect(surface, (150, 150, 180), (boost_x, boost_y, boost_bar_w, boost_bar_h), 1)

    # Wormhole cooldown indicator
    wh_x = 50
    wh_y = game.screen_height - 130
    if game.wormhole_active:
        wh_label = game.small_font.render("[Q] WORMHOLE  IN TRANSIT", True, (100, 180, 255))
        surface.blit(wh_label, (wh_x, wh_y))
    elif game.wormhole_cooldown > 0:
        cd_pct = game.wormhole_cooldown / game.wormhole_max_cooldown
        bar_w = 140
        bar_h = 10
        cd_secs = game.wormhole_cooldown / 60.0
        wh_label = game.small_font.render(f"[Q] WORMHOLE  {cd_secs:.1f}s", True, (120, 120, 150))
        surface.blit(wh_label, (wh_x, wh_y))
        pygame.draw.rect(surface, (40, 40, 60), (wh_x, wh_y + 25, bar_w, bar_h))
        fill_w = int(bar_w * (1.0 - cd_pct))
        pygame.draw.rect(surface, (80, 140, 255), (wh_x, wh_y + 25, fill_w, bar_h))
        pygame.draw.rect(surface, (100, 160, 255), (wh_x, wh_y + 25, bar_w, bar_h), 1)
    else:
        wh_label = game.small_font.render("[Q] WORMHOLE  READY", True, (100, 200, 255))
        surface.blit(wh_label, (wh_x, wh_y))

    # Secondary fire cooldown indicator
    sec_x = 50
    sec_y = wh_y - 40
    ship = game.player_ship
    if ship.secondary_type:
        sec_names = {
            "railgun": "RAILGUN",
            "staff_barrage": "STAFF BARRAGE",
            "ion_pulse": "ION PULSE",
            "war_cry": "WAR CRY",
            "scatter_mines": "SCATTER MINES",
        }
        sec_name = sec_names.get(ship.secondary_type, "SPECIAL")
        if ship.secondary_buff_timer > 0:
            # Active buff — show duration
            buff_secs = ship.secondary_buff_timer / 60.0
            sec_label = game.small_font.render(
                f"[E] {sec_name}  ACTIVE {buff_secs:.1f}s", True, (255, 200, 100))
            surface.blit(sec_label, (sec_x, sec_y))
        elif ship.secondary_cooldown > 0:
            cd_pct = ship.secondary_cooldown / ship.secondary_fire_rate
            bar_w = 140
            bar_h = 10
            cd_secs = ship.secondary_cooldown / 60.0
            sec_label = game.small_font.render(
                f"[E] {sec_name}  {cd_secs:.1f}s", True, (120, 120, 150))
            surface.blit(sec_label, (sec_x, sec_y))
            pygame.draw.rect(surface, (40, 40, 60), (sec_x, sec_y + 25, bar_w, bar_h))
            fill_w = int(bar_w * (1.0 - cd_pct))
            pygame.draw.rect(surface, ship.laser_color, (sec_x, sec_y + 25, fill_w, bar_h))
            pygame.draw.rect(surface, (150, 150, 180), (sec_x, sec_y + 25, bar_w, bar_h), 1)
        else:
            sec_label = game.small_font.render(
                f"[E] {sec_name}  READY", True, ship.laser_color)
            surface.blit(sec_label, (sec_x, sec_y))

    # Controls hint (hidden on touch platforms — virtual joystick is shown instead)
    from touch_support import is_touch_platform
    if not is_touch_platform():
        controls = game.small_font.render(
            "WASD: Move  |  SHIFT: Boost  |  E: Special  |  Q: Wormhole  |  ESC: Exit",
            True, (150, 150, 150))
        surface.blit(controls, (game.screen_width // 2 - controls.get_width() // 2, game.screen_height - 30))

    # Mini-radar (bottom-right corner)
    _draw_mini_radar(game, surface)

    # Game over screen
    if game.game_over:
        _draw_game_over(game, surface)


def _get_tier_color(label):
    """Get color for difficulty tier label."""
    colors = {
        "Calm": (100, 200, 100),
        "Warming Up": (150, 220, 100),
        "Skirmish": (200, 200, 100),
        "Engaged": (255, 200, 50),
        "Contested": (255, 150, 50),
        "Intense": (255, 100, 50),
        "Dangerous": (255, 60, 60),
        "Overwhelming": (255, 30, 30),
        "Apocalypse": (255, 0, 0),
        "Beyond": (200, 0, 255),
    }
    return colors.get(label, (200, 200, 200))


def _draw_mini_radar(game, surface):
    """Draw mini-radar with wider world view and camera viewport outlined."""
    radar_w = 150
    radar_h = 110
    radar_x = game.screen_width - radar_w - 15
    radar_y = game.screen_height - radar_h - 40

    # Semi-transparent background
    radar_surf = pygame.Surface((radar_w, radar_h), pygame.SRCALPHA)
    radar_surf.fill((0, 0, 0, 120))
    pygame.draw.rect(radar_surf, (80, 80, 120, 150), (0, 0, radar_w, radar_h), 1)

    # Radar covers a wider area around camera
    radar_world_w = 3000  # World units visible on radar
    radar_world_h = 2200
    cam_x = game.camera.x
    cam_y = game.camera.y

    # Scale factors
    sx = radar_w / radar_world_w
    sy = radar_h / radar_world_h

    def to_radar(wx, wy):
        rx = int((wx - cam_x + radar_world_w / 2) * sx)
        ry = int((wy - cam_y + radar_world_h / 2) * sy)
        return max(1, min(radar_w - 1, rx)), max(1, min(radar_h - 1, ry))

    # Draw camera viewport rectangle
    vp_x1 = int((radar_world_w / 2 - game.screen_width / 2) * sx)
    vp_y1 = int((radar_world_h / 2 - game.screen_height / 2) * sy)
    vp_w = int(game.screen_width * sx)
    vp_h = int(game.screen_height * sy)
    pygame.draw.rect(radar_surf, (60, 60, 100, 100), (vp_x1, vp_y1, vp_w, vp_h), 1)

    # Player (green dot)
    px, py = to_radar(game.player_ship.x + game.player_ship.width // 2, game.player_ship.y)
    pygame.draw.circle(radar_surf, (0, 255, 0), (px, py), 3)

    # Enemies (red dots)
    for enemy in game.ai_ships:
        ex, ey = to_radar(enemy.x + enemy.width // 2, enemy.y)
        color = (255, 215, 0) if getattr(enemy, 'is_boss', False) else (255, 50, 50)
        size = 3 if getattr(enemy, 'is_boss', False) else 2
        pygame.draw.circle(radar_surf, color, (ex, ey), size)

    # Asteroids (orange dots)
    for asteroid in game.asteroids:
        ax, ay = to_radar(asteroid.x, asteroid.y)
        pygame.draw.circle(radar_surf, (255, 165, 0), (ax, ay), 1)

    # Power-ups (blue dots)
    for powerup in game.powerups:
        ppx, ppy = to_radar(powerup.x, powerup.y)
        pygame.draw.circle(radar_surf, (100, 200, 255), (ppx, ppy), 2)

    surface.blit(radar_surf, (radar_x, radar_y))


def _draw_game_over(game, surface):
    """Draw game over screen — survival mode (always ends in death)."""
    overlay = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surface.blit(overlay, (0, 0))

    result_text = "DEFEAT"
    result_color = (255, 50, 50)

    mins = int(game.survival_seconds) // 60
    secs = int(game.survival_seconds) % 60
    sub_text = f"Survived {mins:02d}:{secs:02d} | {game.enemies_defeated} enemies defeated | Level {game.level}"

    result_surf = game.title_font.render(result_text, True, result_color)
    sub_surf = game.ui_font.render(sub_text, True, (200, 200, 200))

    score_surf = game.title_font.render(f"SCORE: {game.score:,}", True, (255, 215, 0))

    rank_text = ""
    if hasattr(game, 'final_rank') and game.final_rank > 0:
        if game.final_rank == 1:
            rank_text = "SESSION BEST!"
        else:
            rank_text = f"Session Rank #{game.final_rank}"
        games_played = len(game.session_scores)
        if games_played > 1:
            rank_text += f"  ({games_played} games this session)"
    rank_surf = game.ui_font.render(rank_text, True, (100, 255, 100)) if rank_text else None

    # Show evolutions earned
    evo_text = ""
    if game.evolutions:
        evo_names = [EVOLUTIONS[e]["name"] for e in game.evolutions if e in EVOLUTIONS]
        if evo_names:
            evo_text = "Evolutions: " + ", ".join(evo_names)
    evo_surf = game.small_font.render(evo_text, True, (255, 215, 0)) if evo_text else None

    restart_surf = game.ui_font.render("Press R to play again or ESC to exit", True, (150, 150, 150))

    y_offset = game.screen_height // 2 - 140
    surface.blit(result_surf, (game.screen_width // 2 - result_surf.get_width() // 2, y_offset))
    y_offset += 70
    surface.blit(score_surf, (game.screen_width // 2 - score_surf.get_width() // 2, y_offset))
    y_offset += 60
    if rank_surf:
        surface.blit(rank_surf, (game.screen_width // 2 - rank_surf.get_width() // 2, y_offset))
        y_offset += 40
    surface.blit(sub_surf, (game.screen_width // 2 - sub_surf.get_width() // 2, y_offset))
    y_offset += 40
    if evo_surf:
        surface.blit(evo_surf, (game.screen_width // 2 - evo_surf.get_width() // 2, y_offset))
        y_offset += 40
    y_offset += 10
    surface.blit(restart_surf, (game.screen_width // 2 - restart_surf.get_width() // 2, y_offset))


def draw_level_up_screen(game, surface):
    """Draw the level-up upgrade selection overlay with enhanced cards."""
    time_tick = pygame.time.get_ticks()

    # Dark overlay
    overlay = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surface.blit(overlay, (0, 0))

    # "LEVEL UP!" text with pulse (use fixed font, scale for pulse effect)
    if not hasattr(draw_level_up_screen, '_title_font'):
        draw_level_up_screen._title_font = pygame.font.SysFont("Arial", 64, bold=True)
        draw_level_up_screen._title_surf = draw_level_up_screen._title_font.render("LEVEL UP!", True, (255, 215, 0))
    pulse = 1.0 + math.sin(time_tick * 0.005) * 0.1
    base_surf = draw_level_up_screen._title_surf
    w = int(base_surf.get_width() * pulse)
    h = int(base_surf.get_height() * pulse)
    title = pygame.transform.smoothscale(base_surf, (w, h))
    surface.blit(title, (game.screen_width // 2 - title.get_width() // 2, 80))

    subtitle = game.ui_font.render(f"Level {game.level} - Choose an upgrade:", True, (200, 200, 200))
    surface.blit(subtitle, (game.screen_width // 2 - subtitle.get_width() // 2, 150))

    # Draw 3 upgrade cards
    card_w, card_h = 220, 300
    spacing = 40
    total_w = len(game.level_up_choices) * card_w + (len(game.level_up_choices) - 1) * spacing
    start_x = (game.screen_width - total_w) // 2
    card_y = (game.screen_height - card_h) // 2

    game._level_up_card_rects = []
    mouse_pos = pygame.mouse.get_pos()

    for i, upgrade_name in enumerate(game.level_up_choices):
        is_evolution = upgrade_name in EVOLUTIONS
        if is_evolution:
            evo_info = EVOLUTIONS[upgrade_name]
            info = {
                "name": evo_info["name"],
                "desc": evo_info["desc"],
                "icon": "E",
                "color": (255, 215, 0),
                "max": 1,
                "rarity": "legendary",
            }
            current_stacks = 0
        else:
            info = UPGRADES[upgrade_name]
            current_stacks = game.upgrades.get(upgrade_name, 0)

        x = start_x + i * (card_w + spacing)
        rect = pygame.Rect(x, card_y, card_w, card_h)
        game._level_up_card_rects.append(rect)

        hovered = rect.collidepoint(mouse_pos)
        rarity = info.get("rarity", "common")
        rarity_color = RARITY_COLORS.get(rarity, (200, 200, 200))

        # Card background with gradient effect
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        for row in range(card_h):
            t = row / card_h
            r = int(info["color"][0] * (1 - t) * 0.3 + 30 * t)
            g = int(info["color"][1] * (1 - t) * 0.3 + 30 * t)
            b = int(info["color"][2] * (1 - t) * 0.3 + 30 * t)
            if hovered:
                r = min(255, r + 20)
                g = min(255, g + 20)
                b = min(255, b + 20)
            pygame.draw.line(card_surf, (r, g, b, 220), (0, row), (card_w, row))
        surface.blit(card_surf, (x, card_y))

        # Animated pulsing border with rarity color
        border_pulse = abs(math.sin(time_tick * 0.004 + i * 0.5))
        border_alpha = int(150 + border_pulse * 105) if hovered else int(80 + border_pulse * 80)
        border_w = 3 if hovered else 2
        border_surf = pygame.Surface((card_w + 4, card_h + 4), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*rarity_color, border_alpha), (0, 0, card_w + 4, card_h + 4), border_w, border_radius=12)
        surface.blit(border_surf, (x - 2, card_y - 2))

        # Glow on hover
        if hovered:
            glow = pygame.Surface((card_w + 30, card_h + 30), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*rarity_color, 40), (0, 0, card_w + 30, card_h + 30), border_radius=15)
            surface.blit(glow, (x - 15, card_y - 15))

        # Evolution banner
        if is_evolution:
            evo_banner = game.card_name_font.render("EVOLUTION", True, (255, 215, 0))
            surface.blit(evo_banner, (x + card_w // 2 - evo_banner.get_width() // 2, card_y + 5))
        else:
            # Rarity label
            rarity_surf = game.count_font.render(rarity.upper(), True, rarity_color)
            surface.blit(rarity_surf, (x + card_w // 2 - rarity_surf.get_width() // 2, card_y + 8))

        # Key shortcut indicator
        key_text = game.card_key_font.render(f"[{i + 1}]", True, (180, 180, 180))
        surface.blit(key_text, (x + card_w // 2 - key_text.get_width() // 2, card_y + 24))

        # Icon
        icon_surf = game.card_icon_font.render(info["icon"], True, info["color"])
        surface.blit(icon_surf, (x + card_w // 2 - icon_surf.get_width() // 2, card_y + 50))

        # Name
        name_surf = game.card_name_font.render(info["name"], True, (255, 255, 255))
        surface.blit(name_surf, (x + card_w // 2 - name_surf.get_width() // 2, card_y + 105))

        # Description (multi-line)
        desc_lines = info["desc"].split("\n")
        for j, line in enumerate(desc_lines):
            desc_surf = game.card_desc_font.render(line, True, (180, 180, 180))
            surface.blit(desc_surf, (x + card_w // 2 - desc_surf.get_width() // 2, card_y + 135 + j * 20))

        # Evolution: show prereqs
        if is_evolution:
            prereq_text = " + ".join(UPGRADES.get(p, {}).get("name", p) for p in evo_info["prereqs"])
            prereq_surf = game.card_desc_font.render(prereq_text, True, (255, 200, 100))
            surface.blit(prereq_surf, (x + card_w // 2 - prereq_surf.get_width() // 2, card_y + 200))
        else:
            # Stats preview on hover
            if hovered:
                preview = _get_upgrade_preview(game, upgrade_name, current_stacks)
                if preview:
                    preview_surf = game.card_desc_font.render(preview, True, (100, 255, 100))
                    surface.blit(preview_surf, (x + card_w // 2 - preview_surf.get_width() // 2, card_y + 200))

            # Stack indicator
            stack_y = card_y + card_h - 55
            stack_text = f"{current_stacks}/{info['max']}"
            stack_surf = game.card_stack_font.render(stack_text, True, (150, 150, 150))
            surface.blit(stack_surf, (x + card_w // 2 - stack_surf.get_width() // 2, stack_y))

            # Stack pips
            pip_y = stack_y + 25
            pip_total = info["max"]
            pip_w = min(16, (card_w - 40) // max(pip_total, 1))
            pip_start = x + (card_w - pip_total * pip_w) // 2
            for p in range(pip_total):
                pip_color = info["color"] if p < current_stacks else (60, 60, 80)
                if p == current_stacks:
                    pip_color = (255, 255, 255)
                pygame.draw.rect(surface, pip_color,
                                (pip_start + p * pip_w + 1, pip_y, pip_w - 2, 8), border_radius=2)


def _get_upgrade_preview(game, upgrade_name, current_stacks):
    """Return a stats preview string for hover."""
    ship = game.player_ship
    if upgrade_name == "naquadah_plating":
        return f"HP: {int(ship.max_health)} -> {int(ship.max_health + 20)}"
    elif upgrade_name == "sublight_engines":
        return f"Speed: {ship.speed} -> {ship.speed + 1}"
    elif upgrade_name == "shield_harmonics":
        return f"Shields: {int(ship.max_shields)} -> {int(ship.max_shields + 20)}"
    elif upgrade_name == "rapid_capacitors":
        new_rate = max(5, int(ship.fire_rate * 0.9))
        return f"Fire rate: {ship.fire_rate} -> {new_rate}"
    elif upgrade_name == "magnet_field":
        cur = 30 + game.upgrades.get("magnet_field", 0) * 40 + game.upgrades.get("tractor_beam", 0) * 15
        return f"Range: {cur} -> {cur + 40}"
    elif upgrade_name == "critical_strike":
        cur_chance = current_stacks * 10
        return f"Crit: {cur_chance}% -> {cur_chance + 10}%"
    elif upgrade_name == "evasion_matrix":
        cur_dodge = current_stacks * 8
        return f"Dodge: {cur_dodge}% -> {cur_dodge + 8}%"
    return None
