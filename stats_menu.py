import pygame
import os
import math
from deck_persistence import get_persistence
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL
from content_registry import get_all_leaders_for_faction
from animations import get_scale_factor

# Construct FACTION_LEADERS mapping for easy lookup
FACTION_LEADERS = {
    f: get_all_leaders_for_faction(f)
    for f in [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD]
}

def show_confirmation_dialog(surface, text, screen_width, screen_height):
    """Show a simple Yes/No confirmation dialog."""
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    
    dialog_width, dialog_height = 400, 200
    dialog_rect = pygame.Rect(
        (screen_width - dialog_width) // 2,
        (screen_height - dialog_height) // 2,
        dialog_width,
        dialog_height
    )
    
    # Dialog Box
    pygame.draw.rect(overlay, (30, 40, 60), dialog_rect, border_radius=12)
    pygame.draw.rect(overlay, (100, 150, 200), dialog_rect, width=2, border_radius=12)
    
    font = pygame.font.SysFont("Arial", 28, bold=True)
    text_surf = font.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(screen_width // 2, dialog_rect.top + 60))
    overlay.blit(text_surf, text_rect)
    
    # Buttons
    btn_font = pygame.font.SysFont("Arial", 24, bold=True)
    
    yes_rect = pygame.Rect(dialog_rect.left + 50, dialog_rect.bottom - 70, 100, 40)
    no_rect = pygame.Rect(dialog_rect.right - 150, dialog_rect.bottom - 70, 100, 40)
    
    # Draw initial buttons
    pygame.draw.rect(overlay, (40, 100, 40), yes_rect, border_radius=6)
    yes_text = btn_font.render("YES", True, (200, 255, 200))
    overlay.blit(yes_text, yes_text.get_rect(center=yes_rect.center))
    
    pygame.draw.rect(overlay, (100, 40, 40), no_rect, border_radius=6)
    no_text = btn_font.render("NO", True, (255, 200, 200))
    overlay.blit(no_text, no_text.get_rect(center=no_rect.center))
    
    surface.blit(overlay, (0, 0))
    pygame.display.flip()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_RETURN:
                    return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if yes_rect.collidepoint(event.pos):
                    return True
                if no_rect.collidepoint(event.pos):
                    return False
                if not dialog_rect.collidepoint(event.pos):
                    return False # Click outside closes
        
        # Keep UI responsive if needed, but blocking is fine for dialog
        pygame.time.wait(10)

def run_stats_menu(screen):
    """Show a stats overlay with win/loss and faction usage."""
    screen_width, screen_height = screen.get_size()
    stats = get_persistence().get_stats()

    # Try to load stats menu background image
    stats_bg = None
    stats_bg_path = os.path.join("assets", "stats_menu_bg.png")
    if os.path.exists(stats_bg_path):
        try:
            stats_bg = pygame.image.load(stats_bg_path).convert()
            stats_bg = pygame.transform.scale(stats_bg, (screen_width, screen_height))
            print(f"✓ Loaded stats menu background from {stats_bg_path}")
        except Exception as e:
            print(f"Warning: Could not load stats background: {e}")
            stats_bg = None
    else:
        print(f"Stats menu background not found at {stats_bg_path}, using animated background")

    # Load fallback images for previews
    card_back_img = None
    cb_path = os.path.join("assets", "card_back.png")
    if os.path.exists(cb_path):
        try:
            card_back_img = pygame.image.load(cb_path).convert_alpha()
        except:
            pass
            
    faction_bgs = {}
    for f in [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD]:
        f_key = f.lower().replace("'", "").replace(" ", "_")
        f_path = os.path.join("assets", f"faction_bg_{f_key}.png")
        if os.path.exists(f_path):
            try:
                faction_bgs[f] = pygame.image.load(f_path).convert_alpha()
            except:
                pass

    def compute(stats):
        total_games = stats.get("total_games", 0)
        total_wins = stats.get("total_wins", 0)
        total_losses = max(0, total_games - total_wins)
        streak = stats.get("consecutive_wins", 0)
        faction_wins = stats.get("faction_wins", {})
        top_faction = max(faction_wins.items(), key=lambda kv: kv[1])[0] if faction_wins else None
        ai_games = stats.get("ai_games", 0)
        ai_wins = stats.get("ai_wins", 0)
        lan_games = stats.get("lan_games", 0)
        lan_wins = stats.get("lan_wins", 0)
        leader_stats = stats.get("leader_stats", {})
        matchups = stats.get("matchups", {})
        last_results = stats.get("last_results", [])
        turn_stats = stats.get("turn_stats", {})
        mulligans = stats.get("mulligans", {})
        abilities = stats.get("ability_usage", {})
        top_cards = stats.get("top_cards", {})
        lan_rel = stats.get("lan_reliability", {})
        ai_difficulties = stats.get("ai_difficulty", {})
        top_leader = max(leader_stats.items(), key=lambda kv: kv[1].get("games", 0))[0] if leader_stats else None
        best_matchup = None
        worst_matchup = None
        if matchups:
            flat = []
            for pf, opps in matchups.items():
                for of, rec in opps.items():
                    games = rec.get("games", 0)
                    wins = rec.get("wins", 0)
                    if games >= 2:  # Only count matchups with 2+ games
                        flat.append((pf, of, wins, games, wins / games if games > 0 else 0))
            if flat:
                # Best matchup = highest win rate
                best = max(flat, key=lambda x: (x[4], x[2]))  # Sort by win rate, then total wins
                best_matchup = (best[0], best[1], best[2], best[3])
                # Worst matchup = lowest win rate
                worst = min(flat, key=lambda x: (x[4], -x[3]))  # Sort by win rate, then most games (for significance)
                worst_matchup = (worst[0], worst[1], worst[2], worst[3])
        turn_avg = 0
        turn_min = turn_stats.get("min")
        turn_max = turn_stats.get("max")
        if turn_stats.get("games", 0) > 0:
            turn_avg = turn_stats.get("total", 0) / max(1, turn_stats.get("games", 1))
        mull_avg = 0
        if mulligans.get("games", 0) > 0:
            mull_avg = mulligans.get("total", 0) / max(1, mulligans.get("games", 1))
        top_card_list = sorted(top_cards.items(), key=lambda kv: kv[1].get("plays", 0), reverse=True)[:3] if top_cards else []
        
        # New first turn stats
        round_stats = stats.get("round_stats", {})
        ft_games = round_stats.get("first_turn_games", 0)
        ft_wins = round_stats.get("first_turn_wins", 0)
        ft_wr = (ft_wins / ft_games * 100) if ft_games > 0 else 0
        
        return {
            "total_games": total_games,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "streak": streak,
            "max_streak": stats.get("max_streak", 0),
            "top_faction": top_faction,
            "ai_games": ai_games,
            "ai_wins": ai_wins,
            "lan_games": lan_games,
            "lan_wins": lan_wins,
            "leader_stats": leader_stats,
            "top_leader": top_leader,
            "matchups": matchups,
            "best_matchup": best_matchup,
            "worst_matchup": worst_matchup,
            "last_results": last_results,
            "turn_avg": turn_avg,
            "turn_min": turn_min,
            "turn_max": turn_max,
            "mull_avg": mull_avg,
            "abilities": abilities,
            "top_cards": top_card_list,
            "lan_reliability": lan_rel,
            "ai_difficulties": ai_difficulties,
            "first_turn_games": ft_games,
            "first_turn_wins": ft_wins,
            "first_turn_wr": ft_wr,
        }

    computed = compute(stats)

    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    panel_width = int(screen_width * 0.7)
    panel_height = int(screen_height * 0.7)
    panel_rect = pygame.Rect(
        (screen_width - panel_width) // 2,
        (screen_height - panel_height) // 2,
        panel_width,
        panel_height
    )

    title_font = pygame.font.SysFont("Arial", 68, bold=True)
    section_font = pygame.font.SysFont("Arial", 32, bold=True)
    label_font = pygame.font.SysFont("Arial", 32, bold=True)
    value_font = pygame.font.SysFont("Arial", 30)

    # Buttons
    back_rect = pygame.Rect(panel_rect.x + 28, panel_rect.y + 22, 140, 48)
    # Reset button is circular DHD style - make it square for proper circle
    reset_rect = pygame.Rect(panel_rect.right - 90, panel_rect.bottom - 90, 70, 70)

    clock = pygame.time.Clock()
    bg_phase = 0
    running = True
    scroll_offset = 0
    max_scroll = 0
    content_top = 120
    viewport_height = panel_height - 200
    
    # Pre-render button font
    button_font = pygame.font.SysFont("Arial", 28, bold=True)

    while running:
        dt = clock.tick(60)
        bg_phase += dt / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    running = False
                    continue
                if reset_rect.collidepoint(event.pos):
                    if show_confirmation_dialog(screen, "Reset all statistics?", screen_width, screen_height):
                        get_persistence().reset_stats()
                        stats = get_persistence().get_stats()
                        computed = compute(stats)
                        scroll_offset = 0
                        max_scroll = 0
                    continue
                # Click anywhere else closes
                if not panel_rect.collidepoint(event.pos):
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                if panel_rect.collidepoint(event.pos):
                    delta = -60 if event.button == 4 else 60
                    scroll_offset = max(0, min(max_scroll, scroll_offset + delta))

        # Draw background - use image if available, otherwise animated background
        if stats_bg:
            # Use static background image
            screen.blit(stats_bg, (0, 0))
        else:
            # Fallback to animated Stargate background layer
            bg_layer = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            center = (screen_width // 2, screen_height // 2)
            pulse = (math.sin(bg_phase * 2) + 1) * 0.5
            for r in range(120, min(screen_width, screen_height) // 2, 80):
                alpha = max(20, int(80 * (1 - r / (screen_width // 2)) * (0.6 + 0.4 * pulse)))
                pygame.draw.circle(bg_layer, (60, 120, 200, alpha), center, r, width=4)
            # Rotating chevron rays
            for i in range(9):
                angle = bg_phase * 0.8 + i * (2 * math.pi / 9)
                length = min(screen_width, screen_height) // 2
                sx = center[0] + math.cos(angle) * 80
                sy = center[1] + math.sin(angle) * 80
                ex = center[0] + math.cos(angle) * length
                ey = center[1] + math.sin(angle) * length
                pygame.draw.line(bg_layer, (100, 180, 255, 60), (sx, sy), (ex, ey), 2)

            screen.blit(bg_layer, (0, 0))

            # Dark overlay to keep readability
            dynamic_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            dynamic_overlay.fill((0, 0, 20, 200))
            screen.blit(dynamic_overlay, (0, 0))

        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 30, 50, 230))
        pygame.draw.rect(panel_surf, (90, 170, 240), panel_surf.get_rect(), width=3, border_radius=16)

        # Back button
        pygame.draw.rect(panel_surf, (30, 45, 70), back_rect.move(-panel_rect.x, -panel_rect.y), border_radius=8)
        pygame.draw.rect(panel_surf, (90, 170, 240), back_rect.move(-panel_rect.x, -panel_rect.y), width=2, border_radius=8)
        back_text = button_font.render("← Back", True, (210, 230, 255))
        back_text_rect = back_text.get_rect(center=back_rect.move(-panel_rect.x, -panel_rect.y).center)
        panel_surf.blit(back_text, back_text_rect)

        # Reset button - Red DHD Stargate style
        reset_local = reset_rect.move(-panel_rect.x, -panel_rect.y)
        reset_center = reset_local.center
        reset_radius = min(reset_local.width, reset_local.height) // 2 - 2
        
        # DHD outer ring (dark metallic)
        pygame.draw.circle(panel_surf, (50, 45, 45), reset_center, reset_radius + 8)
        pygame.draw.circle(panel_surf, (70, 60, 60), reset_center, reset_radius + 6)
        pygame.draw.circle(panel_surf, (40, 35, 35), reset_center, reset_radius + 4)
        
        # Draw 9 mini chevrons around the ring
        for i in range(9):
            chev_angle = i * (2 * math.pi / 9) - math.pi / 2
            chev_x = reset_center[0] + math.cos(chev_angle) * (reset_radius + 2)
            chev_y = reset_center[1] + math.sin(chev_angle) * (reset_radius + 2)
            # Dim orange chevron dots
            pygame.draw.circle(panel_surf, (120, 60, 20), (int(chev_x), int(chev_y)), 3)
        
        # Red glowing center (pulsing effect)
        pulse = 0.7 + 0.3 * math.sin(bg_phase * 3)
        red_glow = int(180 * pulse)
        pygame.draw.circle(panel_surf, (red_glow, 30, 30), reset_center, reset_radius)
        pygame.draw.circle(panel_surf, (min(255, red_glow + 40), 50, 40), reset_center, reset_radius - 4)
        pygame.draw.circle(panel_surf, (min(255, red_glow + 80), 70, 50), reset_center, reset_radius - 8)
        
        # Inner highlight (top-left light reflection)
        highlight_offset = (-reset_radius // 4, -reset_radius // 4)
        pygame.draw.circle(panel_surf, (255, 150, 120, 100), 
                         (reset_center[0] + highlight_offset[0], reset_center[1] + highlight_offset[1]), 
                         reset_radius // 3)
        
        # Border ring
        pygame.draw.circle(panel_surf, (100, 40, 40), reset_center, reset_radius, 2)
        
        # Reset text
        reset_text = value_font.render("RESET", True, (255, 220, 200))
        reset_text_rect = reset_text.get_rect(center=reset_center)
        panel_surf.blit(reset_text, reset_text_rect)

        # Title
        title = title_font.render("PLAYER STATS", True, (200, 230, 255))
        title_rect = title.get_rect(center=(panel_rect.width // 2, 60))
        panel_surf.blit(title, title_rect)

        # Build rows for scrollable content
        row_gap = 46
        rows = []
        def add_section(text):
            rows.append({"type": "section", "text": text})
        def add_row(label, value, meta=None):
            rows.append({"type": "row", "label": label, "value": value, "meta": meta})

        # Overall
        add_section("Overall")
        winrate = (computed["total_wins"] / computed["total_games"] * 100) if computed["total_games"] > 0 else 0
        add_row("Games Played", str(computed["total_games"]))
        add_row("Wins / Losses", f"{computed['total_wins']} / {computed['total_losses']}")
        add_row("Win Rate", f"{winrate:.1f}%")
        add_row("Current Streak", f"{computed['streak']} wins")
        add_row("Best Streak", f"{computed['max_streak']} wins")

        # Unlock Progress
        add_section("Unlock Progress")
        unlocked_leaders = stats.get("unlocked_leaders", [])
        unlocked_cards = stats.get("unlocked_cards", [])
        add_row("Leaders Unlocked", f"{len(unlocked_leaders)} / 20")
        add_row("Cards Unlocked", f"{len(unlocked_cards)} / 20")

        # Faction Win Rates
        add_section("Faction Win Rates")
        faction_wins = stats.get("faction_wins", {})
        for faction_name in ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard"]:
            wins = faction_wins.get(faction_name, 0)
            # Calculate games played with this faction from matchups
            matchups = stats.get("matchups", {})
            games = 0
            if faction_name in matchups:
                for opp, rec in matchups[faction_name].items():
                    games += rec.get("games", 0)
            
            # Show games played
            if games > 0:
                faction_wr = (wins / games) * 100
                add_row(faction_name, f"{wins}W / {games - wins}L ({faction_wr:.0f}%)", meta={"games": games})
            elif wins > 0:
                add_row(faction_name, f"{wins} wins (Games data incomplete)")
            else:
                 # Optional: hide if no games, or show 0
                 pass

        # By Mode
        add_section("By Mode")
        ai_losses = max(0, computed["ai_games"] - computed["ai_wins"])
        lan_losses = max(0, computed["lan_games"] - computed["lan_wins"])
        ai_wr = (computed["ai_wins"] / computed["ai_games"] * 100) if computed["ai_games"] > 0 else 0
        lan_wr = (computed["lan_wins"] / computed["lan_games"] * 100) if computed["lan_games"] > 0 else 0
        add_row("AI Games", f"{computed['ai_wins']}W / {ai_losses}L ({ai_wr:.0f}%)" if computed["ai_games"] > 0 else "No games")
        add_row("LAN Games", f"{computed['lan_wins']}W / {lan_losses}L ({lan_wr:.0f}%)" if computed["lan_games"] > 0 else "No games")
        
        # New: First Turn Advantage
        if computed.get("first_turn_games", 0) > 0:
            add_row("First Turn WR", f"{computed['first_turn_wins']} / {computed['first_turn_games']} ({computed['first_turn_wr']:.1f}%)")

        # Round Breakdown
        add_section("Round Breakdown")
        round_stats = stats.get("round_stats", {})
        sweeps = round_stats.get("sweeps_for", 0)
        close_wins = round_stats.get("close_wins", 0)
        comebacks = round_stats.get("comebacks", 0)
        sweeps_against = round_stats.get("sweeps_against", 0)
        close_losses = round_stats.get("close_losses", 0)
        add_row("Perfect Games (2-0)", str(sweeps))
        add_row("Close Wins (2-1)", str(close_wins))
        add_row("Comeback Wins", str(comebacks))
        add_row("Swept (0-2)", str(sweeps_against))
        add_row("Close Losses (1-2)", str(close_losses))

        # Leaders
        add_section("Leaders")
        top_leader = computed.get("top_leader") or "No data"
        leader_meta = None
        leader_wr_text = ""
        if computed.get("top_leader"):
            # FACTION_LEADERS values are lists of leader dicts
            for faction_id, leader_list in FACTION_LEADERS.items():
                for ldata in leader_list:
                    if ldata.get("name") == computed["top_leader"]:
                        leader_meta = {"leader_id": ldata.get("card_id"), "faction": faction_id, "name": ldata.get("name")}
                        break
                if leader_meta:
                    break
            
            # Fallback: Search ALL_CARDS if registry match failed (defensive coding)
            if not leader_meta:
                for cid, card in ALL_CARDS.items():
                    if card.name == computed["top_leader"]:
                        leader_meta = {
                            "leader_id": cid, 
                            "faction": card.faction, 
                            "name": card.name
                        }
                        break

            # Get leader win rate
            leader_stats = computed.get("leader_stats", {})
            if computed["top_leader"] in leader_stats:
                ls = leader_stats[computed["top_leader"]]
                lg = ls.get("games", 0)
                lw = ls.get("wins", 0)
                if lg > 0:
                    leader_wr_text = f" ({lw}/{lg} = {lw/lg*100:.0f}%)"
        add_row("Most Played Leader", top_leader + leader_wr_text, meta=leader_meta)

        # Matchups
        add_section("Matchups")
        if computed.get("best_matchup"):
            pf, of, wins, games = computed["best_matchup"]
            add_row("Best Matchup", f"{pf} vs {of}: {wins}W / {games - wins}L")
        else:
            add_row("Best Matchup", "No data")
        # Add worst matchup
        if computed.get("worst_matchup"):
            pf, of, wins, games = computed["worst_matchup"]
            add_row("Worst Matchup", f"{pf} vs {of}: {wins}W / {games - wins}L")

        # Form - Visual W/L display
        add_section("Recent Form")
        last10 = computed.get("last_results", [])
        if last10:
            add_row("Last 10 Games", "".join(last10)) # logic handled in rendering
        else:
            add_row("Last 10 Games", "No games yet")

        # Game length
        add_section("Game Length")
        add_row("Avg Turns", f"{computed['turn_avg']:.1f}" if computed.get("turn_avg") else "N/A")
        add_row("Fastest / Longest", f"{computed.get('turn_min','N/A')} / {computed.get('turn_max','N/A')}")

        # Mulligans
        add_section("Mulligans")
        add_row("Avg Mulligans", f"{computed['mull_avg']:.1f}" if computed.get("mull_avg") else "N/A")

        # Abilities
        add_section("Abilities Used")
        ab = computed.get("abilities", {})
        add_row("Medical Evac", str(ab.get("medic", 0)))
        add_row("Ring Transport", str(ab.get("decoy", 0)))
        add_row("Faction Powers", str(ab.get("faction_power", 0)))
        add_row("Iris Blocks", str(ab.get("iris_blocks", 0)))

        # Top cards
        add_section("Top Cards")
        if computed.get("top_cards"):
            for name_key, rec in computed["top_cards"]:
                # name_key is now the card name
                plays = rec.get('plays', 0)
                wins = rec.get('wins', 0)
                # Use the representative ID stored during recording for the hover preview
                rep_id = rec.get('id')
                card_wr = (wins / plays * 100) if plays > 0 else 0
                add_row(name_key, f"{plays} plays ({card_wr:.0f}% WR)", meta={"card_id": rep_id})
        else:
            add_row("Top Cards", "No data", meta={"card_id": "no_card_data"})

        # LAN reliability
        add_section("LAN Reliability")
        lan_rel = computed.get("lan_reliability") or {}
        add_row("Completed LAN", str(lan_rel.get("completed", 0)))
        add_row("Disconnects", str(lan_rel.get("disconnects", 0)))

        # Draft Mode (Arena)
        add_section("Draft Mode (Arena)")
        draft = stats.get("draft_stats", {})
        if draft and draft.get("runs_started", 0) > 0:
            # Draft run stats
            runs_started = draft.get("runs_started", 0)
            runs_completed = draft.get("runs_completed", 0)
            add_row("Runs Started", str(runs_started))
            add_row("Runs Completed", str(runs_completed))

            # Win/loss record
            battles_won = draft.get("battles_won", 0)
            battles_lost = draft.get("battles_lost", 0)
            total_battles = battles_won + battles_lost
            if total_battles > 0:
                draft_winrate = (battles_won / total_battles) * 100
                add_row("Battle Record", f"{battles_won}W / {battles_lost}L ({draft_winrate:.1f}%)")
            else:
                add_row("Battle Record", "No battles yet")

            # Best run
            best_run = draft.get("best_run_wins", 0)
            add_row("Best Run", f"{best_run} win{'s' if best_run != 1 else ''}")

            # Deck stats
            total_cards = draft.get("total_cards_drafted", 0)
            if runs_completed > 0:
                avg_cards = total_cards / runs_completed
                add_row("Avg Cards/Run", f"{avg_cards:.1f}")

            avg_power = draft.get("avg_deck_power", 0.0)
            highest_power = draft.get("highest_deck_power", 0)
            add_row("Avg Deck Power", f"{avg_power:.1f}")
            add_row("Highest Deck Power", str(highest_power))

            # Most drafted leader (with hover preview)
            drafted_leaders = draft.get("drafted_leaders", {})
            if drafted_leaders:
                most_leader = max(drafted_leaders.items(), key=lambda x: x[1])
                # Find leader_id for hover preview
                leader_id = None
                for lid, ldata in ALL_CARDS.items():
                    if ldata.name == most_leader[0]:
                        leader_id = lid
                        break
                add_row("Favorite Leader", f"{most_leader[0]} ({most_leader[1]}x)", meta={"card_id": leader_id} if leader_id else None)

            # Most drafted faction
            drafted_factions = draft.get("drafted_factions", {})
            if drafted_factions:
                most_faction = max(drafted_factions.items(), key=lambda x: x[1])
                add_row("Favorite Faction", f"{most_faction[0]} ({most_faction[1]}x)")

            # Most drafted card
            most_card = draft.get("most_drafted_card")
            if most_card and most_card in ALL_CARDS:
                card_counts = draft.get("card_draft_counts", {})
                count = card_counts.get(most_card, 0)
                card_name = ALL_CARDS[most_card].name
                add_row("Favorite Card", f"{card_name} ({count}x)", meta={"card_id": most_card})
        else:
            add_row("Draft Runs", "Play Draft Mode to see stats!")

        # Build content surface
        content_height = max(800, len(rows) * row_gap + 200)
        content = pygame.Surface((panel_rect.width, content_height), pygame.SRCALPHA)
        y_cursor = 20
        hover_targets = []
        for entry in rows:
            if entry["type"] == "section":
                section = section_font.render(entry["text"], True, (150, 210, 255))
                content.blit(section, (40, y_cursor))
            else:
                lbl = label_font.render(entry["label"], True, (180, 200, 230))
                lbl_rect = lbl.get_rect(topleft=(60, y_cursor))
                content.blit(lbl, lbl_rect)
                
                # Special rendering for "Last 10 Games"
                if entry["label"] == "Last 10 Games" and entry["value"] != "No games yet":
                    value = entry["value"]
                    x_start = lbl_rect.right + 20
                    # Render each character with spacing
                    char_spacing = 28  # Increased spacing for better readability
                    for i, ch in enumerate(value):
                        if ch == "W":
                            color = (100, 255, 100) # Green
                        elif ch == "L":
                            color = (255, 100, 100) # Red
                        else:
                            color = (220, 240, 255)
                        
                        ch_surf = value_font.render(ch, True, color)
                        content.blit(ch_surf, (x_start + i * char_spacing, y_cursor))
                        
                    val_rect = pygame.Rect(x_start, y_cursor, len(value)*char_spacing, ch_surf.get_height())
                else:
                    val = value_font.render(entry["value"], True, (220, 240, 255))
                    val_rect = val.get_rect(topright=(panel_rect.width - 60, y_cursor))
                    content.blit(val, val_rect)

                meta = entry.get("meta")
                if meta:
                    hover_targets.append({
                        "meta": meta,
                        "rect": pygame.Rect(lbl_rect.left, lbl_rect.top, val_rect.right - lbl_rect.left, lbl_rect.height),
                    })
            y_cursor += row_gap

        max_scroll = max(0, content_height - viewport_height)
        scroll_offset = max(0, min(max_scroll, scroll_offset))

        view_rect = pygame.Rect(0, scroll_offset, panel_rect.width, viewport_height)
        panel_surf.blit(content, (0, content_top), area=view_rect)

        # Hover previews for leader/card rows
        mouse_pos = pygame.mouse.get_pos()
        faction_colors = {
            FACTION_TAURI: (100, 180, 255),
            FACTION_GOAULD: (220, 180, 80),
            FACTION_JAFFA: (140, 90, 60),
            FACTION_LUCIAN: (150, 200, 120),
            FACTION_ASGARD: (180, 220, 255),
            FACTION_NEUTRAL: (200, 200, 200),
        }
        # Hover preview - show in center of panel
        hovered_meta = None
        for ht in hover_targets:
            meta = ht["meta"]
            rect = ht["rect"]
            # Convert to screen rect for hover detection
            screen_rect = pygame.Rect(
                panel_rect.x + rect.x,
                panel_rect.y + content_top + rect.y - scroll_offset,
                rect.width,
                rect.height
            )
            if screen_rect.collidepoint(mouse_pos):
                hovered_meta = meta
                break

        # Draw centered preview if hovering - just the PNG, no fluff
        if hovered_meta:
            scale = get_scale_factor(screen_height)
            img = None
            
            if hovered_meta.get("card_id"):
                card_id = hovered_meta["card_id"]
                card = ALL_CARDS.get(card_id)
                img = card.image if card and card.image else card_back_img
            elif hovered_meta.get("leader_id"):
                leader_id = hovered_meta.get("leader_id")
                leader_card = ALL_CARDS.get(leader_id)
                img = leader_card.image if leader_card and leader_card.image else card_back_img
            
            if img:
                # Scale PNG to native resolution * screen scale factor
                preview_w = int(img.get_width() * scale)
                preview_h = int(img.get_height() * scale)
                preview = pygame.transform.smoothscale(img, (preview_w, preview_h))
                
                # Center in panel
                draw_x = (panel_rect.width - preview_w) // 2
                draw_y = (panel_rect.height - preview_h) // 2
                panel_surf.blit(preview, (draw_x, draw_y))

        hint = value_font.render("Scroll / ESC / Enter to go back", True, (170, 190, 210))
        hint_rect = hint.get_rect(center=(panel_rect.width // 2, panel_rect.height - 50))
        panel_surf.blit(hint, hint_rect)

        screen.blit(panel_surf, panel_rect.topleft)
        pygame.display.flip()
