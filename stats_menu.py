import asyncio
import pygame
import os
import math
import display_manager
from deck_persistence import get_persistence
from cards import ALL_CARDS, FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD, FACTION_NEUTRAL
from content_registry import get_all_leaders_for_faction
from animations import get_scale_factor
import board_renderer

# Construct FACTION_LEADERS mapping for easy lookup
FACTION_LEADERS = {
    f: get_all_leaders_for_faction(f)
    for f in [FACTION_TAURI, FACTION_GOAULD, FACTION_JAFFA, FACTION_LUCIAN, FACTION_ASGARD]
}

async def show_confirmation_dialog(surface, text, screen_width, screen_height):
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
    display_manager.gpu_flip()
    
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
        await asyncio.sleep(0)

async def run_stats_menu(screen):
    """Show a stats overlay with tabbed layout: Overview, Factions, Leaders, Records, Draft."""
    screen_width, screen_height = screen.get_size()
    stats = get_persistence().get_stats()

    # Try to load stats menu background image
    stats_bg = None
    stats_bg_path = os.path.join("assets", "stats_menu_bg.png")
    if os.path.exists(stats_bg_path):
        try:
            stats_bg = pygame.image.load(stats_bg_path).convert()
            stats_bg = pygame.transform.scale(stats_bg, (screen_width, screen_height))
        except Exception:
            stats_bg = None

    # Load tab switch sound
    _tab_sound = None
    _tab_snd_path = os.path.join("assets", "audio", "stats_menu_tab.ogg")
    if os.path.exists(_tab_snd_path):
        try:
            _tab_sound = pygame.mixer.Sound(_tab_snd_path)
        except (pygame.error, Exception):
            pass

    def _play_tab_sound():
        if _tab_sound:
            try:
                from game_settings import get_settings as _gs
                _tab_sound.set_volume(_gs().get_effective_sfx_volume())
                _tab_sound.play()
            except (pygame.error, Exception):
                pass

    # Load fallback images for previews
    card_back_img = None
    cb_path = os.path.join("assets", "card_back.png")
    if os.path.exists(cb_path):
        try:
            card_back_img = pygame.image.load(cb_path).convert_alpha()
        except:
            pass

    # Faction color mapping for bars and dots
    faction_bar_colors = {
        "Tau'ri": (100, 150, 255),
        "Goa'uld": (255, 180, 50),
        "Jaffa Rebellion": (200, 150, 100),
        "Lucian Alliance": (200, 80, 200),
        "Asgard": (100, 255, 255),
    }

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
                    if games >= 2:
                        flat.append((pf, of, wins, games, wins / games if games > 0 else 0))
            if flat:
                best = max(flat, key=lambda x: (x[4], x[2]))
                best_matchup = (best[0], best[1], best[2], best[3])
                worst = min(flat, key=lambda x: (x[4], -x[3]))
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
        round_stats = stats.get("round_stats", {})
        ft_games = round_stats.get("first_turn_games", 0)
        ft_wins = round_stats.get("first_turn_wins", 0)
        ft_wr = (ft_wins / ft_games * 100) if ft_games > 0 else 0
        return {
            "total_games": total_games, "total_wins": total_wins, "total_losses": total_losses,
            "streak": streak, "max_streak": stats.get("max_streak", 0), "top_faction": top_faction,
            "ai_games": ai_games, "ai_wins": ai_wins, "lan_games": lan_games, "lan_wins": lan_wins,
            "leader_stats": leader_stats, "top_leader": top_leader,
            "matchups": matchups, "best_matchup": best_matchup, "worst_matchup": worst_matchup,
            "last_results": last_results, "turn_avg": turn_avg, "turn_min": turn_min, "turn_max": turn_max,
            "mull_avg": mull_avg, "abilities": abilities, "top_cards": top_card_list,
            "lan_reliability": lan_rel, "ai_difficulties": ai_difficulties,
            "first_turn_games": ft_games, "first_turn_wins": ft_wins, "first_turn_wr": ft_wr,
        }

    # --- Row builder helpers (shared across tabs) ---
    def add_section(rows, text):
        rows.append({"type": "section", "text": text})
    def add_row(rows, label, value, meta=None):
        rows.append({"type": "row", "label": label, "value": value, "meta": meta})
    def add_bar_row(rows, label, value, pct, bar_color, meta=None):
        rows.append({"type": "bar_row", "label": label, "value": value, "pct": pct, "bar_color": bar_color, "meta": meta})

    # --- Tab builder functions ---
    def build_overview_tab(stats, computed):
        rows = []
        total_games = computed["total_games"]
        total_wins = computed["total_wins"]
        streak = computed["streak"]
        max_streak_val = computed.get("max_streak", 0)
        winrate = (total_wins / total_games * 100) if total_games > 0 else 0
        comebacks = stats.get("round_stats", {}).get("comebacks", 0)
        draft = stats.get("draft_stats", {})
        perfect_draft_runs = draft.get("perfect_runs", 0) if draft else 0

        # Achievements
        achievements = []
        if total_games >= 100:
            achievements.append("* Centurion (100+ games)")
        elif total_games >= 50:
            achievements.append("* Veteran (50+ games)")
        elif total_games >= 10:
            achievements.append("* Recruit (10+ games)")
        best_streak = max(streak, max_streak_val)
        if best_streak >= 10:
            achievements.append("* Unstoppable (10+ win streak)")
        elif best_streak >= 5:
            achievements.append("* On Fire (5+ win streak)")
        if winrate >= 70 and total_games >= 10:
            achievements.append("* Dominator (70%+ WR)")
        matchups_data = stats.get("matchups", {})
        for fname in ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard"]:
            fg = 0
            if fname in matchups_data:
                for opp, rec in matchups_data[fname].items():
                    fg += rec.get("games", 0)
            if fg >= 20:
                achievements.append(f"* {fname} Master (20+ games)")
                break
        if perfect_draft_runs > 0:
            achievements.append("* Perfect Draft (8-0 run)")
        if comebacks >= 5:
            achievements.append("* Comeback King (5+ comebacks)")
        if achievements:
            add_section(rows, "Highlights")
            for ach in achievements:
                rows.append({"type": "achievement", "text": ach})

        # Overall
        add_section(rows, "Overall")
        add_row(rows, "Games Played", str(total_games))
        add_row(rows, "Wins / Losses", f"{total_wins} / {computed['total_losses']}")
        add_row(rows, "Win Rate", f"{winrate:.1f}%")
        add_row(rows, "Current Streak", f"{streak} wins")
        add_row(rows, "Best Streak", f"{max_streak_val} wins")

        # Unlock Progress
        add_section(rows, "Unlock Progress")
        if stats.get("unlock_override_enabled", False):
            add_row(rows, "Leaders Unlocked", "20 / 20 (Unlock All ON)")
            add_row(rows, "Cards Unlocked", "20 / 20 (Unlock All ON)")
        else:
            unlocked_leaders = stats.get("unlocked_leaders", {})
            if isinstance(unlocked_leaders, list):
                leader_count = len(unlocked_leaders)
            else:
                leader_count = sum(len(leaders) for leaders in unlocked_leaders.values())
            unlocked_cards = stats.get("unlocked_cards", [])
            add_row(rows, "Leaders Unlocked", f"{leader_count} / 20")
            add_row(rows, "Cards Unlocked", f"{len(unlocked_cards)} / 20")

        # By Mode
        add_section(rows, "By Mode")
        ai_losses = max(0, computed["ai_games"] - computed["ai_wins"])
        lan_losses = max(0, computed["lan_games"] - computed["lan_wins"])
        ai_wr = (computed["ai_wins"] / computed["ai_games"] * 100) if computed["ai_games"] > 0 else 0
        lan_wr = (computed["lan_wins"] / computed["lan_games"] * 100) if computed["lan_games"] > 0 else 0
        if computed["ai_games"] > 0:
            add_bar_row(rows, "AI Games", f"{computed['ai_wins']}W / {ai_losses}L ({ai_wr:.0f}%)", ai_wr / 100.0, (100, 180, 255))
        else:
            add_row(rows, "AI Games", "No games")
        if computed["lan_games"] > 0:
            add_bar_row(rows, "LAN Games", f"{computed['lan_wins']}W / {lan_losses}L ({lan_wr:.0f}%)", lan_wr / 100.0, (100, 255, 180))
        else:
            add_row(rows, "LAN Games", "No games")

        # First Turn WR
        if computed.get("first_turn_games", 0) > 0:
            add_row(rows, "First Turn WR", f"{computed['first_turn_wins']} / {computed['first_turn_games']} ({computed['first_turn_wr']:.1f}%)")

        # Recent Form
        add_section(rows, "Recent Form")
        last10 = computed.get("last_results", [])
        if last10:
            add_row(rows, "Last 10 Games", "".join(last10))
        else:
            add_row(rows, "Last 10 Games", "No games yet")

        # Game Length
        add_section(rows, "Game Length")
        add_row(rows, "Avg Turns", f"{computed['turn_avg']:.1f}" if computed.get("turn_avg") else "N/A")
        add_row(rows, "Fastest / Longest", f"{computed.get('turn_min','N/A')} / {computed.get('turn_max','N/A')}")

        # Mulligans
        add_section(rows, "Mulligans")
        add_row(rows, "Avg Mulligans", f"{computed['mull_avg']:.1f}" if computed.get("mull_avg") else "N/A")

        # Fun Facts
        add_section(rows, "Fun Facts")
        top_cards_data = stats.get("top_cards", {})
        total_cards_played = sum(r.get("plays", 0) for r in top_cards_data.values()) if top_cards_data else 0
        add_row(rows, "Total Cards Played", str(total_cards_played))
        if total_games > 0:
            add_row(rows, "Cards Per Game", f"{total_cards_played / total_games:.1f}" if total_cards_played else "N/A")
        ab_data = computed.get("abilities", {})
        if ab_data:
            most_ability = max(ab_data.items(), key=lambda kv: kv[1], default=None)
            if most_ability and most_ability[1] > 0:
                add_row(rows, "Most Used Ability", f"{most_ability[0].replace('_', ' ').title()} ({most_ability[1]}x)")
        add_row(rows, "Avg Mulligans/Game", f"{computed['mull_avg']:.1f}" if computed.get("mull_avg") else "N/A")
        if draft and draft.get("runs_started", 0) > 0:
            battles_total = draft.get("battles_won", 0) + draft.get("battles_lost", 0)
            runs_started = draft.get("runs_started", 0)
            if runs_started > 0:
                add_row(rows, "Draft Battles/Run", f"{battles_total / runs_started:.1f}")

        return rows

    def build_factions_tab(stats, computed):
        rows = []
        # Faction Win Rates
        add_section(rows, "Faction Win Rates")
        faction_wins = stats.get("faction_wins", {})
        matchups_raw = stats.get("matchups", {})
        for faction_name in ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard"]:
            wins = faction_wins.get(faction_name, 0)
            games = 0
            if faction_name in matchups_raw:
                for opp, rec in matchups_raw[faction_name].items():
                    games += rec.get("games", 0)
            if games > 0:
                faction_wr = (wins / games) * 100
                bar_color = faction_bar_colors.get(faction_name, (150, 150, 150))
                add_bar_row(rows, faction_name, f"{wins}W / {games - wins}L ({faction_wr:.0f}%)", faction_wr / 100.0, bar_color, meta={"faction": faction_name, "games": games})
            elif wins > 0:
                add_row(rows, faction_name, f"{wins} wins (Games data incomplete)")

        # Matchups
        add_section(rows, "Matchups")
        if computed.get("best_matchup"):
            pf, of, wins, games = computed["best_matchup"]
            add_row(rows, "Best Matchup", f"{pf} vs {of}: {wins}W / {games - wins}L")
        else:
            add_row(rows, "Best Matchup", "No data")
        if computed.get("worst_matchup"):
            pf, of, wins, games = computed["worst_matchup"]
            add_row(rows, "Worst Matchup", f"{pf} vs {of}: {wins}W / {games - wins}L")
        return rows

    def build_leaders_tab(stats, computed):
        rows = []
        # Top Leaders
        add_section(rows, "Top Leaders")
        leader_stats_data = computed.get("leader_stats", {})
        if leader_stats_data:
            sorted_leaders = sorted(leader_stats_data.items(), key=lambda kv: kv[1].get("games", 0), reverse=True)[:5]
            for leader_name, ls in sorted_leaders:
                lg = ls.get("games", 0)
                lw = ls.get("wins", 0)
                if lg == 0:
                    continue
                lr = lw / lg
                leader_meta = None
                for faction_id, leader_list in FACTION_LEADERS.items():
                    for ldata in leader_list:
                        if ldata.get("name") == leader_name:
                            leader_meta = {"leader_id": ldata.get("card_id"), "faction": faction_id, "name": leader_name}
                            break
                    if leader_meta:
                        break
                if not leader_meta:
                    for cid, card in ALL_CARDS.items():
                        if card.name == leader_name:
                            leader_meta = {"leader_id": cid, "faction": card.faction, "name": card.name}
                            break
                add_bar_row(rows, leader_name, f"{lw}W / {lg - lw}L ({lr*100:.0f}%) - {lg} games", lr, (200, 180, 100), meta=leader_meta)
        else:
            add_row(rows, "Top Leaders", "No data")

        # Top Cards
        add_section(rows, "Top Cards")
        if computed.get("top_cards"):
            for name_key, rec in computed["top_cards"]:
                plays = rec.get('plays', 0)
                wins = rec.get('wins', 0)
                rep_id = rec.get('id')
                card_wr = (wins / plays * 100) if plays > 0 else 0
                add_row(rows, name_key, f"{plays} plays ({card_wr:.0f}% WR)", meta={"card_id": rep_id})
        else:
            add_row(rows, "Top Cards", "No data", meta={"card_id": "no_card_data"})

        # Abilities Used
        add_section(rows, "Abilities Used")
        ab = computed.get("abilities", {})
        add_row(rows, "Medical Evac", str(ab.get("medic", 0)))
        add_row(rows, "Ring Transport", str(ab.get("decoy", 0)))
        add_row(rows, "Faction Powers", str(ab.get("faction_power", 0)))
        add_row(rows, "Iris Blocks", str(ab.get("iris_blocks", 0)))
        return rows

    def build_records_tab(stats, computed):
        rows = []
        # Round Breakdown
        add_section(rows, "Round Breakdown")
        round_stats = stats.get("round_stats", {})
        add_row(rows, "Perfect Games (2-0)", str(round_stats.get("sweeps_for", 0)))
        add_row(rows, "Close Wins (2-1)", str(round_stats.get("close_wins", 0)))
        add_row(rows, "Comeback Wins", str(round_stats.get("comebacks", 0)))
        add_row(rows, "Swept (0-2)", str(round_stats.get("sweeps_against", 0)))
        add_row(rows, "Close Losses (1-2)", str(round_stats.get("close_losses", 0)))

        # Score Records (NEW)
        add_section(rows, "Score Records")
        sr = stats.get("score_records", {})
        games_with = sr.get("games_with_scores", 0)
        if games_with > 0:
            avg_score = sr.get("total_score", 0) / games_with
            add_row(rows, "Average Score", f"{avg_score:.1f}")
            highest = sr.get("highest_score")
            if highest is not None:
                leader = sr.get("highest_score_leader", "")
                add_row(rows, "Highest Score", f"{highest}" + (f"  ({leader})" if leader else ""))
            lowest = sr.get("lowest_score")
            if lowest is not None:
                leader = sr.get("lowest_score_leader", "")
                add_row(rows, "Lowest Score", f"{lowest}" + (f"  ({leader})" if leader else ""))
            biggest = sr.get("biggest_margin")
            if biggest is not None:
                leader = sr.get("biggest_margin_leader", "")
                add_row(rows, "Biggest Victory Margin", f"{biggest}" + (f"  ({leader})" if leader else ""))
            closest = sr.get("closest_game")
            if closest is not None:
                leader = sr.get("closest_game_leader", "")
                add_row(rows, "Closest Game", f"{closest}" + (f"  ({leader})" if leader else ""))
        else:
            add_row(rows, "Score Records", "No data yet")

        # LAN Reliability
        add_section(rows, "LAN Reliability")
        lan_rel = stats.get("lan_reliability") or {}
        add_row(rows, "Completed LAN", str(lan_rel.get("completed", 0)))
        add_row(rows, "Disconnects", str(lan_rel.get("disconnects", 0)))
        return rows

    def build_draft_tab(stats, computed):
        rows = []
        add_section(rows, "Draft Mode (Arena)")
        draft = stats.get("draft_stats", {})
        if draft and draft.get("runs_started", 0) > 0:
            runs_started = draft.get("runs_started", 0)
            runs_completed = draft.get("runs_completed", 0)
            add_row(rows, "Runs Started", str(runs_started))
            add_row(rows, "Runs Completed", str(runs_completed))
            battles_won = draft.get("battles_won", 0)
            battles_lost = draft.get("battles_lost", 0)
            total_battles = battles_won + battles_lost
            if total_battles > 0:
                draft_winrate = (battles_won / total_battles) * 100
                add_bar_row(rows, "Battle Record", f"{battles_won}W / {battles_lost}L ({draft_winrate:.1f}%)", draft_winrate / 100.0, (255, 200, 80))
            else:
                add_row(rows, "Battle Record", "No battles yet")
            best_run = draft.get("best_run_wins", 0)
            add_row(rows, "Best Run", f"{best_run} win{'s' if best_run != 1 else ''}")
            perfect_runs = draft.get("perfect_runs", 0)
            if perfect_runs > 0:
                add_row(rows, "Perfect Runs (8 Wins)", str(perfect_runs))
            avg_power = draft.get("avg_deck_power", 0.0)
            highest_power = draft.get("highest_deck_power", 0)
            add_row(rows, "Avg Deck Power", f"{avg_power:.1f}")
            add_row(rows, "Highest Deck Power", str(highest_power))
            total_cards_draft = draft.get("total_cards_drafted", 0)
            if runs_completed > 0:
                avg_cards = total_cards_draft / runs_completed
                add_row(rows, "Avg Cards/Run", f"{avg_cards:.1f}")
            drafted_leaders = draft.get("drafted_leaders", {})
            if drafted_leaders:
                most_leader = max(drafted_leaders.items(), key=lambda x: x[1])
                leader_id = None
                for lid, ldata in ALL_CARDS.items():
                    if ldata.name == most_leader[0]:
                        leader_id = lid
                        break
                add_row(rows, "Favorite Leader", f"{most_leader[0]} ({most_leader[1]}x)", meta={"card_id": leader_id} if leader_id else None)
            drafted_factions = draft.get("drafted_factions", {})
            if drafted_factions:
                most_faction = max(drafted_factions.items(), key=lambda x: x[1])
                add_row(rows, "Favorite Faction", f"{most_faction[0]} ({most_faction[1]}x)")
            most_card = draft.get("most_drafted_card")
            if most_card and most_card in ALL_CARDS:
                card_counts = draft.get("card_draft_counts", {})
                count = card_counts.get(most_card, 0)
                card_name = ALL_CARDS[most_card].name
                add_row(rows, "Favorite Card", f"{card_name} ({count}x)", meta={"card_id": most_card})
        else:
            add_row(rows, "Draft Runs", "Play Draft Mode to see stats!")
        return rows

    # --- Main loop setup ---
    computed = compute(stats)

    panel_width = int(screen_width * 0.7)
    panel_height = int(screen_height * 0.7)
    panel_rect = pygame.Rect(
        (screen_width - panel_width) // 2,
        (screen_height - panel_height) // 2,
        panel_width,
        panel_height
    )

    title_font = pygame.font.SysFont("Arial", 48, bold=True)
    tab_font = pygame.font.SysFont("Arial", 26, bold=True)
    section_font = pygame.font.SysFont("Arial", 32, bold=True)
    label_font = pygame.font.SysFont("Arial", 32, bold=True)
    value_font = pygame.font.SysFont("Arial", 30)
    achievement_font = pygame.font.SysFont("Arial", 26, bold=True)

    back_rect = pygame.Rect(20, 20, 80, 104)
    reset_rect = pygame.Rect(panel_rect.right - 90, panel_rect.bottom - 90, 70, 70)

    def build_conquest_tab(stats, computed):
        rows = []
        add_section(rows, "Galactic Conquest")
        conquest = stats.get("conquest_stats", {})
        if conquest and conquest.get("campaigns_started", 0) > 0:
            # Campaign overview
            started = conquest.get("campaigns_started", 0)
            won = conquest.get("campaigns_won", 0)
            lost = conquest.get("campaigns_lost", 0)
            add_row(rows, "Campaigns", f"{started} started / {won}W / {lost}L")

            # Battle record with win rate bar
            battles_won = conquest.get("battles_won", 0)
            battles_lost = conquest.get("battles_lost", 0)
            total_battles = battles_won + battles_lost
            if total_battles > 0:
                battle_wr = (battles_won / total_battles) * 100
                add_bar_row(rows, "Battle Record",
                            f"{battles_won}W / {battles_lost}L ({battle_wr:.1f}%)",
                            battle_wr / 100.0, (100, 220, 140))

            # Territory
            planets_conquered = conquest.get("planets_conquered", 0)
            add_row(rows, "Planets Conquered", str(planets_conquered))
            homeworlds = conquest.get("homeworlds_captured", 0)
            if homeworlds > 0:
                add_row(rows, "Homeworlds Captured", str(homeworlds))

            # Defense
            defenses_won = conquest.get("defenses_won", 0)
            defenses_lost = conquest.get("defenses_lost", 0)
            if defenses_won + defenses_lost > 0:
                add_row(rows, "Defenses", f"{defenses_won}W / {defenses_lost}L")

            # Speed & progression
            best_turn = conquest.get("best_victory_turn")
            if best_turn:
                add_row(rows, "Fastest Victory", f"Turn {best_turn}")
            best_tier = conquest.get("best_network_tier", 0)
            tier_names = {1: "Outpost", 2: "Regional", 3: "Sector",
                          4: "Quadrant", 5: "Galactic"}
            if best_tier > 0:
                add_row(rows, "Best Network Tier",
                        f"{tier_names.get(best_tier, '?')} (T{best_tier})")

            # Collection & progress
            add_section(rows, "Collection & Progress")
            relics = conquest.get("relics_collected", 0)
            if relics > 0:
                unique_count = len(conquest.get("unique_relics_seen", []))
                add_row(rows, "Relics Collected",
                        f"{relics} total ({unique_count}/17 unique)")
            arcs = conquest.get("arcs_completed", 0)
            if arcs > 0:
                unique_arcs = len(conquest.get("unique_arcs_completed", []))
                add_row(rows, "Story Arcs Completed",
                        f"{arcs} total ({unique_arcs}/6 unique)")
            crises = conquest.get("crises_survived", 0)
            if crises > 0:
                unique_crises = len(conquest.get("unique_crises_seen", []))
                add_row(rows, "Crises Survived",
                        f"{crises} ({unique_crises}/5 types)")
            cards_drafted = conquest.get("cards_drafted", 0)
            if cards_drafted > 0:
                add_row(rows, "Cards Drafted", str(cards_drafted))

            # Diplomacy & economy
            trades = conquest.get("trades_made", 0)
            alliances = conquest.get("alliances_forged", 0)
            betrayals = conquest.get("betrayals", 0)
            if trades + alliances + betrayals > 0:
                add_section(rows, "Diplomacy & Economy")
                if alliances > 0:
                    add_row(rows, "Alliances Forged", str(alliances))
                if trades > 0:
                    add_row(rows, "Trades Made", str(trades))
                if betrayals > 0:
                    add_row(rows, "Betrayals", str(betrayals))

            buildings = conquest.get("buildings_constructed", 0)
            if buildings > 0:
                add_row(rows, "Buildings Constructed", str(buildings))
            naq_earned = conquest.get("naquadah_earned", 0)
            if naq_earned > 0:
                add_row(rows, "Total Naquadah Earned", str(naq_earned))

            # Favorites
            factions_used = conquest.get("conquest_factions_used", {})
            if factions_used:
                fav_faction = max(factions_used, key=factions_used.get)
                add_row(rows, "Favorite Faction",
                        f"{fav_faction} ({factions_used[fav_faction]}x)")
            leaders_used = conquest.get("conquest_leaders_used", {})
            if leaders_used:
                fav_leader = max(leaders_used, key=leaders_used.get)
                add_row(rows, "Favorite Leader",
                        f"{fav_leader} ({leaders_used[fav_leader]}x)")

            # Difficulty wins
            diff_wins = conquest.get("difficulty_wins", {})
            if any(v > 0 for v in diff_wins.values()):
                add_section(rows, "Difficulty Wins")
                for diff in ["easy", "normal", "hard", "insane"]:
                    w = diff_wins.get(diff, 0)
                    if w > 0:
                        add_row(rows, f"  {diff.title()}", str(w))

            # Conquest achievements
            add_section(rows, "Conquest Achievements")
            has_achievement = False
            if won >= 1:
                rows.append({"type": "achievement",
                             "text": "* Galaxy Conqueror (Won a campaign)"})
                has_achievement = True
            if won >= 5:
                rows.append({"type": "achievement",
                             "text": "* Galactic Emperor (Won 5 campaigns)"})
                has_achievement = True
            if best_turn and best_turn <= 15:
                rows.append({"type": "achievement",
                             "text": "* Blitzkrieg (Won in 15 turns or fewer)"})
                has_achievement = True
            if planets_conquered >= 50:
                rows.append({"type": "achievement",
                             "text": "* Planet Hoarder (50+ planets conquered)"})
                has_achievement = True
            if len(conquest.get("unique_arcs_completed", [])) >= 6:
                rows.append({"type": "achievement",
                             "text": "* Loremaster (Completed all 6 story arcs)"})
                has_achievement = True
            if len(conquest.get("unique_relics_seen", [])) >= 17:
                rows.append({"type": "achievement",
                             "text": "* Artifact Hunter (Collected all 17 relics)"})
                has_achievement = True
            if conquest.get("betrayals", 0) >= 1:
                rows.append({"type": "achievement",
                             "text": "* Ba'al's Gambit (Betrayed an ally)"})
                has_achievement = True
            if diff_wins.get("insane", 0) >= 1:
                rows.append({"type": "achievement",
                             "text": "* Ascended (Won on Insane difficulty)"})
                has_achievement = True
            if len(conquest.get("unique_crises_seen", [])) >= 5:
                rows.append({"type": "achievement",
                             "text": "* Crisis Veteran (Survived all 5 crisis types)"})
                has_achievement = True
            if naq_earned >= 1000:
                rows.append({"type": "achievement",
                             "text": "* Naquadah Baron (Earned 1000+ naquadah total)"})
                has_achievement = True
            if not has_achievement:
                add_row(rows, "Achievements", "Keep conquering to unlock!")
        else:
            add_row(rows, "", "Play Galactic Conquest to see stats!")
        return rows

    # Tab state
    TAB_NAMES = ["Overview", "Factions", "Leaders", "Records", "Draft", "Conquest"]
    TAB_KEYS = ["overview", "factions", "leaders", "records", "draft", "conquest"]
    TAB_BUILDERS = [build_overview_tab, build_factions_tab, build_leaders_tab, build_records_tab, build_draft_tab, build_conquest_tab]
    active_tab_idx = 0
    tab_scroll_offsets = {k: 0 for k in TAB_KEYS}

    # Layout constants
    title_height = 50
    tab_bar_y = title_height + 10
    tab_bar_height = 36
    content_top = tab_bar_y + tab_bar_height + 14
    viewport_height = panel_height - content_top - 80  # leave room for hint + reset

    clock = pygame.time.Clock()
    bg_phase = 0
    running = True
    max_scroll = 0
    row_gap = 46
    bar_row_gap = 56
    achievement_gap = 36

    # Pre-compute tab button rects (panel-local coords)
    tab_rects = []
    num_tabs = len(TAB_NAMES)
    tab_total_width = panel_width - 80
    tab_w = tab_total_width // num_tabs
    for i in range(num_tabs):
        tx = 40 + i * tab_w
        tab_rects.append(pygame.Rect(tx, tab_bar_y, tab_w, tab_bar_height))

    while running:
        dt = clock.tick(60)
        await asyncio.sleep(0)
        bg_phase += dt / 1000.0
        current_key = TAB_KEYS[active_tab_idx]
        scroll_offset = tab_scroll_offsets[current_key]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    running = False
                elif event.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - 60)
                elif event.key == pygame.K_DOWN:
                    scroll_offset = min(max_scroll, scroll_offset + 60)
                elif event.key == pygame.K_PAGEUP:
                    scroll_offset = max(0, scroll_offset - 200)
                elif event.key == pygame.K_PAGEDOWN:
                    scroll_offset = min(max_scroll, scroll_offset + 200)
                elif event.key == pygame.K_HOME:
                    scroll_offset = 0
                elif event.key == pygame.K_END:
                    scroll_offset = max_scroll
                elif event.key == pygame.K_TAB:
                    # Cycle tabs
                    tab_scroll_offsets[current_key] = scroll_offset
                    active_tab_idx = (active_tab_idx + 1) % num_tabs
                    current_key = TAB_KEYS[active_tab_idx]
                    scroll_offset = tab_scroll_offsets[current_key]
                    _play_tab_sound()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6):
                    idx = event.key - pygame.K_1
                    if idx < num_tabs:
                        tab_scroll_offsets[current_key] = scroll_offset
                        active_tab_idx = idx
                        current_key = TAB_KEYS[active_tab_idx]
                        scroll_offset = tab_scroll_offsets[current_key]
                        _play_tab_sound()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    try:
                        _sel_path = os.path.join("assets", "audio", "menu_select.ogg")
                        if os.path.exists(_sel_path):
                            _sel_snd = pygame.mixer.Sound(_sel_path)
                            from game_settings import get_settings as _gs
                            _sel_snd.set_volume(_gs().get_effective_sfx_volume())
                            _sel_snd.play()
                    except (pygame.error, Exception):
                        pass
                    running = False
                    continue
                if reset_rect.collidepoint(event.pos):
                    if await show_confirmation_dialog(screen, "Reset all statistics?", screen_width, screen_height):
                        get_persistence().reset_stats()
                        stats = get_persistence().get_stats()
                        computed = compute(stats)
                        tab_scroll_offsets = {k: 0 for k in TAB_KEYS}
                        scroll_offset = 0
                        max_scroll = 0
                    continue
                # Tab clicks (convert to panel-local)
                local_pos = (event.pos[0] - panel_rect.x, event.pos[1] - panel_rect.y)
                tab_clicked = False
                for i, tr in enumerate(tab_rects):
                    if tr.collidepoint(local_pos):
                        tab_scroll_offsets[current_key] = scroll_offset
                        active_tab_idx = i
                        current_key = TAB_KEYS[active_tab_idx]
                        scroll_offset = tab_scroll_offsets[current_key]
                        tab_clicked = True
                        _play_tab_sound()
                        break
                if not tab_clicked and not panel_rect.collidepoint(event.pos):
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                if panel_rect.collidepoint(event.pos):
                    delta = -60 if event.button == 4 else 60
                    scroll_offset = max(0, min(max_scroll, scroll_offset + delta))

        tab_scroll_offsets[current_key] = scroll_offset

        # Draw background
        if stats_bg:
            screen.blit(stats_bg, (0, 0))
        else:
            bg_layer = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            center = (screen_width // 2, screen_height // 2)
            pulse = (math.sin(bg_phase * 2) + 1) * 0.5
            for r in range(120, min(screen_width, screen_height) // 2, 80):
                alpha = max(20, int(80 * (1 - r / (screen_width // 2)) * (0.6 + 0.4 * pulse)))
                pygame.draw.circle(bg_layer, (60, 120, 200, alpha), center, r, width=4)
            for i in range(9):
                angle = bg_phase * 0.8 + i * (2 * math.pi / 9)
                length = min(screen_width, screen_height) // 2
                sx = center[0] + math.cos(angle) * 80
                sy = center[1] + math.sin(angle) * 80
                ex = center[0] + math.cos(angle) * length
                ey = center[1] + math.sin(angle) * length
                pygame.draw.line(bg_layer, (100, 180, 255, 60), (sx, sy), (ex, ey), 2)
            screen.blit(bg_layer, (0, 0))
            dynamic_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            dynamic_overlay.fill((0, 0, 20, 200))
            screen.blit(dynamic_overlay, (0, 0))

        panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel_surf.fill((20, 30, 50, 230))
        pygame.draw.rect(panel_surf, (90, 170, 240), panel_surf.get_rect(), width=3, border_radius=16)

        # Reset button (DHD style)
        reset_local = reset_rect.move(-panel_rect.x, -panel_rect.y)
        reset_center = reset_local.center
        reset_radius = min(reset_local.width, reset_local.height) // 2 - 2
        pygame.draw.circle(panel_surf, (50, 45, 45), reset_center, reset_radius + 8)
        pygame.draw.circle(panel_surf, (70, 60, 60), reset_center, reset_radius + 6)
        pygame.draw.circle(panel_surf, (40, 35, 35), reset_center, reset_radius + 4)
        for i in range(9):
            chev_angle = i * (2 * math.pi / 9) - math.pi / 2
            chev_x = reset_center[0] + math.cos(chev_angle) * (reset_radius + 2)
            chev_y = reset_center[1] + math.sin(chev_angle) * (reset_radius + 2)
            pygame.draw.circle(panel_surf, (120, 60, 20), (int(chev_x), int(chev_y)), 3)
        pulse = 0.7 + 0.3 * math.sin(bg_phase * 3)
        red_glow = int(180 * pulse)
        pygame.draw.circle(panel_surf, (red_glow, 30, 30), reset_center, reset_radius)
        pygame.draw.circle(panel_surf, (min(255, red_glow + 40), 50, 40), reset_center, reset_radius - 4)
        pygame.draw.circle(panel_surf, (min(255, red_glow + 80), 70, 50), reset_center, reset_radius - 8)
        highlight_offset = (-reset_radius // 4, -reset_radius // 4)
        pygame.draw.circle(panel_surf, (255, 150, 120, 100),
                         (reset_center[0] + highlight_offset[0], reset_center[1] + highlight_offset[1]),
                         reset_radius // 3)
        pygame.draw.circle(panel_surf, (100, 40, 40), reset_center, reset_radius, 2)
        reset_text = value_font.render("RESET", True, (255, 220, 200))
        panel_surf.blit(reset_text, reset_text.get_rect(center=reset_center))

        # Title
        title = title_font.render("PLAYER STATS", True, (200, 230, 255))
        panel_surf.blit(title, title.get_rect(center=(panel_rect.width // 2, title_height // 2 + 8)))

        # Tab bar
        mouse_pos = pygame.mouse.get_pos()
        local_mouse = (mouse_pos[0] - panel_rect.x, mouse_pos[1] - panel_rect.y)
        for i, (name, tr) in enumerate(zip(TAB_NAMES, tab_rects)):
            is_active = (i == active_tab_idx)
            is_hovered = tr.collidepoint(local_mouse)
            if is_active:
                bg_color = (60, 90, 140, 255)
            elif is_hovered:
                bg_color = (40, 60, 100, 200)
            else:
                bg_color = (25, 35, 55, 180)
            tab_bg = pygame.Surface((tr.width, tr.height), pygame.SRCALPHA)
            tab_bg.fill(bg_color)
            panel_surf.blit(tab_bg, tr.topleft)
            # Active underline
            if is_active:
                pygame.draw.line(panel_surf, (100, 200, 255), (tr.left + 4, tr.bottom - 2), (tr.right - 4, tr.bottom - 2), 3)
            # Tab text
            text_color = (220, 240, 255) if is_active else (140, 160, 190)
            tab_label = tab_font.render(name, True, text_color)
            panel_surf.blit(tab_label, tab_label.get_rect(center=tr.center))

        # Build rows for active tab
        rows = TAB_BUILDERS[active_tab_idx](stats, computed)

        # Render rows to content surface
        estimated_height = 0
        for r in rows:
            if r["type"] == "bar_row":
                estimated_height += bar_row_gap
            elif r["type"] == "achievement":
                estimated_height += achievement_gap
            elif r["type"] == "section":
                estimated_height += row_gap + 8
            else:
                estimated_height += row_gap
        content_height = max(400, estimated_height + 100)
        content = pygame.Surface((panel_rect.width, content_height), pygame.SRCALPHA)
        y_cursor = 20
        hover_targets = []
        data_row_index = 0

        for entry in rows:
            if entry["type"] == "section":
                if y_cursor > 30:
                    y_cursor += 8
                section = section_font.render(entry["text"], True, (150, 210, 255))
                content.blit(section, (40, y_cursor))
                underline_y = y_cursor + section.get_height() + 2
                underline_width = min(section.get_width() + 40, panel_rect.width - 80)
                for ux in range(underline_width):
                    a = max(0, 255 - int(ux * 255 / underline_width))
                    line_surf = pygame.Surface((1, 2), pygame.SRCALPHA)
                    line_surf.fill((100, 170, 255, a))
                    content.blit(line_surf, (40 + ux, underline_y))
                y_cursor += row_gap + 8
                data_row_index = 0

            elif entry["type"] == "achievement":
                ach_rect = pygame.Rect(40, y_cursor, panel_rect.width - 80, achievement_gap - 4)
                ach_bg = pygame.Surface((ach_rect.width, ach_rect.height), pygame.SRCALPHA)
                ach_bg.fill((80, 70, 20, 60))
                content.blit(ach_bg, ach_rect.topleft)
                ach_text = achievement_font.render(entry["text"], True, (255, 215, 0))
                content.blit(ach_text, (60, y_cursor + 4))
                y_cursor += achievement_gap

            elif entry["type"] == "bar_row":
                if data_row_index % 2 == 1:
                    alt_bg = pygame.Surface((panel_rect.width - 40, bar_row_gap - 4), pygame.SRCALPHA)
                    alt_bg.fill((255, 255, 255, 10))
                    content.blit(alt_bg, (20, y_cursor))
                faction_name = entry.get("meta", {}).get("faction") if entry.get("meta") else None
                label_x = 60
                if faction_name and faction_name in faction_bar_colors:
                    dot_color = faction_bar_colors[faction_name]
                    pygame.draw.circle(content, dot_color, (50, y_cursor + 10), 5)
                    label_x = 62
                lbl = label_font.render(entry["label"], True, (180, 200, 230))
                lbl_rect = lbl.get_rect(topleft=(label_x, y_cursor))
                content.blit(lbl, lbl_rect)
                val = value_font.render(entry["value"], True, (220, 240, 255))
                val_rect = val.get_rect(topright=(panel_rect.width - 60, y_cursor))
                content.blit(val, val_rect)
                bar_y = y_cursor + lbl.get_height() + 4
                bar_width = panel_rect.width - 120
                bar_height = 12
                pygame.draw.rect(content, (40, 50, 70), pygame.Rect(60, bar_y, bar_width, bar_height), border_radius=6)
                fill_width = max(0, int(bar_width * min(1.0, entry["pct"])))
                if fill_width > 0:
                    pygame.draw.rect(content, entry["bar_color"], pygame.Rect(60, bar_y, fill_width, bar_height), border_radius=6)
                meta = entry.get("meta")
                if meta:
                    hover_targets.append({
                        "meta": meta,
                        "rect": pygame.Rect(lbl_rect.left, lbl_rect.top, val_rect.right - lbl_rect.left, lbl_rect.height + bar_height + 4),
                    })
                data_row_index += 1
                y_cursor += bar_row_gap

            else:
                if data_row_index % 2 == 1:
                    alt_bg = pygame.Surface((panel_rect.width - 40, row_gap - 4), pygame.SRCALPHA)
                    alt_bg.fill((255, 255, 255, 10))
                    content.blit(alt_bg, (20, y_cursor))
                lbl = label_font.render(entry["label"], True, (180, 200, 230))
                lbl_rect = lbl.get_rect(topleft=(60, y_cursor))
                content.blit(lbl, lbl_rect)
                if entry["label"] == "Last 10 Games" and entry["value"] != "No games yet":
                    value = entry["value"]
                    x_start = lbl_rect.right + 20
                    char_spacing = 28
                    for ci, ch in enumerate(value):
                        if ch == "W":
                            color = (100, 255, 100)
                        elif ch == "L":
                            color = (255, 100, 100)
                        else:
                            color = (220, 240, 255)
                        ch_surf = value_font.render(ch, True, color)
                        content.blit(ch_surf, (x_start + ci * char_spacing, y_cursor))
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
                data_row_index += 1
                y_cursor += row_gap

        max_scroll = max(0, content_height - viewport_height)
        scroll_offset = max(0, min(max_scroll, scroll_offset))
        tab_scroll_offsets[current_key] = scroll_offset

        view_rect = pygame.Rect(0, scroll_offset, panel_rect.width, viewport_height)
        panel_surf.blit(content, (0, content_top), area=view_rect)

        # Hover previews
        hovered_meta = None
        for ht in hover_targets:
            meta = ht["meta"]
            rect = ht["rect"]
            screen_rect = pygame.Rect(
                panel_rect.x + rect.x,
                panel_rect.y + content_top + rect.y - scroll_offset,
                rect.width,
                rect.height
            )
            if screen_rect.collidepoint(mouse_pos):
                hovered_meta = meta
                break

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
                preview_w = int(img.get_width() * scale)
                preview_h = int(img.get_height() * scale)
                preview = pygame.transform.smoothscale(img, (preview_w, preview_h))
                draw_x = (panel_rect.width - preview_w) // 2
                draw_y = (panel_rect.height - preview_h) // 2
                panel_surf.blit(preview, (draw_x, draw_y))

        hint = value_font.render("Tab / 1-6: switch tabs | Scroll | ESC to go back", True, (170, 190, 210))
        hint_rect = hint.get_rect(center=(panel_rect.width // 2, panel_rect.height - 50))
        panel_surf.blit(hint, hint_rect)

        screen.blit(panel_surf, panel_rect.topleft)

        # DHD back button
        back_rect = board_renderer.draw_dhd_back_button(screen, 20, 20, 80)

        display_manager.gpu_flip()
