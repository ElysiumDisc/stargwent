"""
Statistics Module for Stargwent

Provides analysis and display utilities for player statistics.
Integrates with deck_persistence.py for data storage.
"""

from typing import Dict, List, Tuple, Optional
from deck_persistence import get_persistence


def get_overall_stats() -> Dict:
    """Get overall player statistics summary.

    Returns:
        Dict with:
        - total_games: Total games played
        - total_wins: Total wins
        - win_rate: Win percentage (0-100)
        - current_streak: Current win streak
        - max_streak: Best win streak
        - ai_stats: AI mode stats
        - lan_stats: LAN mode stats
    """
    persistence = get_persistence()
    stats = persistence.get_stats()

    total_games = stats.get("total_games", 0)
    total_wins = stats.get("total_wins", 0)
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0.0

    ai_games = stats.get("ai_games", 0)
    ai_wins = stats.get("ai_wins", 0)
    ai_win_rate = (ai_wins / ai_games * 100) if ai_games > 0 else 0.0

    lan_games = stats.get("lan_games", 0)
    lan_wins = stats.get("lan_wins", 0)
    lan_win_rate = (lan_wins / lan_games * 100) if lan_games > 0 else 0.0

    return {
        "total_games": total_games,
        "total_wins": total_wins,
        "win_rate": round(win_rate, 1),
        "current_streak": stats.get("consecutive_wins", 0),
        "max_streak": stats.get("max_streak", 0),
        "ai_stats": {
            "games": ai_games,
            "wins": ai_wins,
            "win_rate": round(ai_win_rate, 1)
        },
        "lan_stats": {
            "games": lan_games,
            "wins": lan_wins,
            "win_rate": round(lan_win_rate, 1)
        }
    }


def get_faction_stats() -> Dict[str, Dict]:
    """Get win statistics by faction.

    Returns:
        Dict mapping faction name to:
        - wins: Number of wins with this faction
        - games: Total games with this faction (estimated from wins)
        - win_rate: Win percentage
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    faction_wins = stats.get("faction_wins", {})

    # Note: deck_persistence only tracks wins per faction, not total games
    # We can estimate from matchup data if available
    matchups = stats.get("matchups", {})

    result = {}
    factions = ["Tau'ri", "Goa'uld", "Jaffa Rebellion", "Lucian Alliance", "Asgard"]

    for faction in factions:
        wins = faction_wins.get(faction, 0)

        # Try to get total games from matchups
        games = 0
        if faction in matchups:
            for opponent_data in matchups[faction].values():
                games += opponent_data.get("games", 0)

        if games == 0:
            # Fallback: estimate from wins (assume ~50% win rate if unknown)
            games = wins * 2 if wins > 0 else 0

        win_rate = (wins / games * 100) if games > 0 else 0.0

        result[faction] = {
            "wins": wins,
            "games": games,
            "win_rate": round(win_rate, 1)
        }

    return result


def get_leader_stats() -> List[Dict]:
    """Get win statistics by leader.

    Returns:
        List of dicts sorted by games played (descending):
        - name: Leader name
        - games: Total games
        - wins: Total wins
        - win_rate: Win percentage
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    leader_stats = stats.get("leader_stats", {})

    result = []
    for leader_name, data in leader_stats.items():
        games = data.get("games", 0)
        wins = data.get("wins", 0)
        win_rate = (wins / games * 100) if games > 0 else 0.0

        result.append({
            "name": leader_name,
            "games": games,
            "wins": wins,
            "win_rate": round(win_rate, 1)
        })

    # Sort by games played (most played first)
    result.sort(key=lambda x: x["games"], reverse=True)
    return result


def get_top_cards(limit: int = 10) -> List[Dict]:
    """Get most frequently played cards.

    Args:
        limit: Maximum number of cards to return

    Returns:
        List of dicts sorted by plays (descending):
        - name: Card name
        - card_id: Card ID for lookup
        - plays: Total times played
        - wins: Wins when played
        - win_rate: Win percentage when card was played
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    top_cards = stats.get("top_cards", {})

    result = []
    for card_name, data in top_cards.items():
        plays = data.get("plays", 0)
        wins = data.get("wins", 0)
        win_rate = (wins / plays * 100) if plays > 0 else 0.0

        result.append({
            "name": card_name,
            "card_id": data.get("id", ""),
            "plays": plays,
            "wins": wins,
            "win_rate": round(win_rate, 1)
        })

    # Sort by plays (most played first)
    result.sort(key=lambda x: x["plays"], reverse=True)
    return result[:limit]


def get_matchup_stats() -> Dict[str, Dict[str, Dict]]:
    """Get faction vs faction matchup statistics.

    Returns:
        Nested dict: matchups[player_faction][opponent_faction] = {
            "games": int,
            "wins": int,
            "win_rate": float
        }
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    matchups = stats.get("matchups", {})

    result = {}
    for player_faction, opponents in matchups.items():
        result[player_faction] = {}
        for opponent_faction, data in opponents.items():
            games = data.get("games", 0)
            wins = data.get("wins", 0)
            win_rate = (wins / games * 100) if games > 0 else 0.0

            result[player_faction][opponent_faction] = {
                "games": games,
                "wins": wins,
                "win_rate": round(win_rate, 1)
            }

    return result


def get_round_breakdown() -> Dict:
    """Get round-level statistics.

    Returns:
        Dict with:
        - sweeps_for: 2-0 wins
        - sweeps_against: 0-2 losses
        - close_wins: 2-1 wins
        - close_losses: 1-2 losses
        - comebacks: Wins after losing round 1
        - first_turn_advantage: Win rate when going first
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    round_stats = stats.get("round_stats", {})

    first_turn_games = round_stats.get("first_turn_games", 0)
    first_turn_wins = round_stats.get("first_turn_wins", 0)
    first_turn_win_rate = (first_turn_wins / first_turn_games * 100) if first_turn_games > 0 else 0.0

    return {
        "sweeps_for": round_stats.get("sweeps_for", 0),
        "sweeps_against": round_stats.get("sweeps_against", 0),
        "close_wins": round_stats.get("close_wins", 0),
        "close_losses": round_stats.get("close_losses", 0),
        "comebacks": round_stats.get("comebacks", 0),
        "first_turn_games": first_turn_games,
        "first_turn_wins": first_turn_wins,
        "first_turn_advantage": round(first_turn_win_rate, 1)
    }


def get_ability_usage() -> Dict:
    """Get ability usage statistics.

    Returns:
        Dict with counts for each tracked ability type
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    return stats.get("ability_usage", {
        "medic": 0,
        "decoy": 0,
        "faction_power": 0,
        "iris_blocks": 0
    })


def get_turn_stats() -> Dict:
    """Get turn count statistics.

    Returns:
        Dict with:
        - avg_turns: Average turns per game
        - min_turns: Fewest turns in a game
        - max_turns: Most turns in a game
        - total_turns: Total turns across all games
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    turn_stats = stats.get("turn_stats", {})

    total = turn_stats.get("total", 0)
    games = turn_stats.get("games", 0)
    avg = (total / games) if games > 0 else 0.0

    return {
        "avg_turns": round(avg, 1),
        "min_turns": turn_stats.get("min"),
        "max_turns": turn_stats.get("max"),
        "total_turns": total,
        "games_tracked": games
    }


def get_recent_form() -> Tuple[str, int]:
    """Get recent win/loss form.

    Returns:
        Tuple of (form_string, win_count)
        - form_string: Last 10 results as "WLWWLWWWWW"
        - win_count: Wins in last 10 games
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    last_results = stats.get("last_results", [])

    form_string = "".join(last_results[-10:]) if last_results else ""
    win_count = form_string.count("W")

    return (form_string, win_count)


def get_draft_stats() -> Dict:
    """Get draft mode statistics.

    Returns:
        Dict with draft-specific stats
    """
    persistence = get_persistence()
    stats = persistence.get_stats()
    draft_stats = stats.get("draft_stats", {})

    runs_completed = draft_stats.get("runs_completed", 0)
    battles_won = draft_stats.get("battles_won", 0)
    battles_lost = draft_stats.get("battles_lost", 0)
    total_battles = battles_won + battles_lost
    battle_win_rate = (battles_won / total_battles * 100) if total_battles > 0 else 0.0

    return {
        "runs_started": draft_stats.get("runs_started", 0),
        "runs_completed": runs_completed,
        "battles_won": battles_won,
        "battles_lost": battles_lost,
        "battle_win_rate": round(battle_win_rate, 1),
        "best_run_wins": draft_stats.get("best_run_wins", 0),
        "perfect_runs": draft_stats.get("perfect_runs", 0),
        "total_cards_drafted": draft_stats.get("total_cards_drafted", 0),
        "avg_deck_power": round(draft_stats.get("avg_deck_power", 0), 1),
        "highest_deck_power": draft_stats.get("highest_deck_power", 0),
        "most_drafted_card": draft_stats.get("most_drafted_card"),
        "favorite_leaders": _get_top_n(draft_stats.get("drafted_leaders", {}), 3),
        "favorite_factions": _get_top_n(draft_stats.get("drafted_factions", {}), 3)
    }


def _get_top_n(counts_dict: Dict, n: int) -> List[Tuple[str, int]]:
    """Get top N items from a counts dictionary."""
    sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:n]


def format_stats_summary() -> str:
    """Format a text summary of all statistics.

    Returns:
        Multi-line string suitable for display
    """
    overall = get_overall_stats()
    faction = get_faction_stats()
    round_breakdown = get_round_breakdown()
    form_str, form_wins = get_recent_form()

    lines = [
        "=== STARGWENT STATISTICS ===",
        "",
        f"Total Games: {overall['total_games']}",
        f"Total Wins:  {overall['total_wins']} ({overall['win_rate']}%)",
        f"Win Streak:  {overall['current_streak']} (Best: {overall['max_streak']})",
        "",
        "--- Mode Breakdown ---",
        f"AI:  {overall['ai_stats']['wins']}/{overall['ai_stats']['games']} ({overall['ai_stats']['win_rate']}%)",
        f"LAN: {overall['lan_stats']['wins']}/{overall['lan_stats']['games']} ({overall['lan_stats']['win_rate']}%)",
        "",
        "--- Faction Performance ---",
    ]

    for fname, fdata in faction.items():
        if fdata["games"] > 0:
            lines.append(f"  {fname}: {fdata['wins']}/{fdata['games']} ({fdata['win_rate']}%)")

    lines.extend([
        "",
        "--- Round Breakdown ---",
        f"2-0 Sweeps: {round_breakdown['sweeps_for']}",
        f"0-2 Swept:  {round_breakdown['sweeps_against']}",
        f"2-1 Close:  {round_breakdown['close_wins']}",
        f"1-2 Close:  {round_breakdown['close_losses']}",
        f"Comebacks:  {round_breakdown['comebacks']}",
        "",
        f"Recent Form: {form_str} ({form_wins}/10)",
    ])

    return "\n".join(lines)
