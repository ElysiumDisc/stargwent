"""
Deck Persistence System for StarGwent
Handles saving/loading player deck customizations and unlock progress
"""
import json
import os
from typing import Dict, List, Optional
from content_registry import iter_unlockable_leader_ids
from save_paths import get_deck_save_path, get_unlock_save_path, ensure_migration

# Ensure legacy saves are migrated to XDG directory on first access
ensure_migration()

# File paths for save data (using XDG Base Directory paths)
DECK_SAVE_FILE = get_deck_save_path()
UNLOCK_SAVE_FILE = get_unlock_save_path()

class DeckPersistence:
    """Manages persistent deck storage across game sessions"""

    # Card ID migrations: old_id -> new_id
    # When cards are renamed or split into multiple copies, add mappings here
    CARD_ID_MIGRATIONS = {
        "goauld_alkesh": "goauld_alkesh_1",  # Split into _1, _2, _3 for Gate Reinforcement
    }

    def __init__(self):
        self.deck_data = self.load_decks()
        self.unlock_data = self.load_unlocks()

    def _migrate_card_ids(self, deck_data: Dict) -> tuple:
        """Migrate old card IDs to new ones. Returns (data, was_migrated)."""
        migrated = False
        # Import ALL_CARDS for validation (fail gracefully if unavailable)
        try:
            from cards import ALL_CARDS
        except ImportError:
            ALL_CARDS = None

        for faction, faction_data in deck_data.items():
            if isinstance(faction_data, dict) and "cards" in faction_data:
                new_cards = []
                for card_id in faction_data["cards"]:
                    if card_id in self.CARD_ID_MIGRATIONS:
                        new_id = self.CARD_ID_MIGRATIONS[card_id]
                        # Validate target ID exists before migrating
                        if ALL_CARDS is None or new_id in ALL_CARDS:
                            new_cards.append(new_id)
                            print(f"  Migrated card ID: {card_id} -> {new_id}")
                            migrated = True
                        else:
                            # Target doesn't exist, keep original
                            new_cards.append(card_id)
                    else:
                        new_cards.append(card_id)
                faction_data["cards"] = new_cards
        if migrated:
            print("✓ Card ID migration complete")
        return deck_data, migrated

    def load_decks(self) -> Dict:
        """Load saved deck configurations"""
        if os.path.exists(DECK_SAVE_FILE):
            try:
                with open(DECK_SAVE_FILE, 'r') as f:
                    data = json.load(f)
                    # Apply migrations for renamed/split cards
                    data, was_migrated = self._migrate_card_ids(data)
                    # Save migrated data so it only migrates once
                    if was_migrated:
                        with open(DECK_SAVE_FILE, 'w') as fw:
                            json.dump(data, fw, indent=2)
                        print(f"✓ Migrated deck data saved to {DECK_SAVE_FILE}")
                    return data
            except Exception as e:
                print(f"Error loading deck data: {e}")
                return self._get_default_deck_data()
        return self._get_default_deck_data()
    
    def load_unlocks(self) -> Dict:
        """Load unlock progress"""
        if os.path.exists(UNLOCK_SAVE_FILE):
            try:
                with open(UNLOCK_SAVE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading unlock data: {e}")
                return self._get_default_unlock_data()
        return self._get_default_unlock_data()
    
    def save_decks(self):
        """Save current deck configurations"""
        try:
            with open(DECK_SAVE_FILE, 'w') as f:
                json.dump(self.deck_data, f, indent=2)
            print(f"✓ Decks saved to {DECK_SAVE_FILE}")
        except Exception as e:
            print(f"Error saving deck data: {e}")
    
    def save_unlocks(self):
        """Save unlock progress"""
        try:
            with open(UNLOCK_SAVE_FILE, 'w') as f:
                json.dump(self.unlock_data, f, indent=2)
            print(f"✓ Unlocks saved to {UNLOCK_SAVE_FILE}")
        except Exception as e:
            print(f"Error saving unlock data: {e}")
    
    def _get_default_deck_data(self) -> Dict:
        """Default deck configuration"""
        return {
            "Tau'ri": {
                "leader": "tauri_oneill",  # Default leader
                "cards": []  # Empty = use default faction deck
            },
            "Goa'uld": {
                "leader": "goauld_apophis",
                "cards": []
            },
            "Jaffa Rebellion": {
                "leader": "jaffa_tealc",
                "cards": []
            },
            "Lucian Alliance": {
                "leader": "lucian_vulkar",
                "cards": []
            },
            "Asgard": {
                "leader": "asgard_freyr",
                "cards": []
            }
        }
    
    def _get_default_unlock_data(self) -> Dict:
        """Default unlock progress"""
        return {
            "unlocked_cards": [],
            "unlocked_leaders": [],
            "consecutive_wins": 0,
            "total_wins": 0,
            "total_games": 0,
            "faction_wins": {
                "Tau'ri": 0,
                "Goa'uld": 0,
                "Jaffa Rebellion": 0,
                "Lucian Alliance": 0,
                "Asgard": 0
            },
            # Draft Mode Stats
            "draft_stats": {
                "runs_started": 0,
                "runs_completed": 0,
                "battles_won": 0,
                "battles_lost": 0,
                "best_run_wins": 0,
                "perfect_runs": 0,
                "total_cards_drafted": 0,
                "drafted_leaders": {},  # leader_id: count
                "drafted_factions": {},  # faction: count
                "avg_deck_power": 0.0,
                "highest_deck_power": 0,
                "most_drafted_card": None,
                "card_draft_counts": {}  # card_id: count
            },
            "active_draft_run": None,  # Stores current run state if active
            # User Content Stats (custom cards/leaders/factions created by players)
            "user_content_stats": {
                "games_with_user_cards": 0,
                "games_with_user_leaders": 0,
                "games_with_user_factions": 0,
                "user_cards_played": {},  # card_id: times_played
                "user_leaders_used": {},  # leader_id: times_used
                "user_factions_used": {},  # faction: times_used
            }
        }
    
    def get_active_draft_run(self) -> Optional[Dict]:
        """Get the currently active draft run if one exists."""
        return self.unlock_data.get("active_draft_run")

    def save_active_draft_run(self, run_data: Dict):
        """Save the state of the active draft run."""
        self.unlock_data["active_draft_run"] = run_data
        self.save_unlocks()
        print(f"✓ Active draft run saved (Wins: {run_data.get('wins', 0)})")

    def clear_active_draft_run(self):
        """Clear the active draft run (game over or completed)."""
        self.unlock_data["active_draft_run"] = None
        self.save_unlocks()

    
    def get_deck(self, faction: str) -> Dict:
        """Get deck configuration for a faction"""
        if faction in self.deck_data:
            return self.deck_data[faction]
        return {"leader": "", "cards": []}
    
    def set_deck(self, faction: str, leader_id: str, card_ids: List[str]):
        """Set deck configuration for a faction"""
        self.deck_data[faction] = {
            "leader": leader_id,
            "cards": card_ids
        }
        self.save_decks()
        print(f"✓ Deck saved for {faction}: {len(card_ids)} cards, Leader: {leader_id}")
    
    def get_leader(self, faction: str) -> str:
        """Get selected leader for faction"""
        if faction in self.deck_data:
            return self.deck_data[faction].get("leader", "")
        return ""
    
    def set_leader(self, faction: str, leader_id: str):
        """Set leader for faction"""
        if faction not in self.deck_data:
            self.deck_data[faction] = {"leader": leader_id, "cards": []}
        else:
            self.deck_data[faction]["leader"] = leader_id
        self.save_decks()
        print(f"✓ Leader set for {faction}: {leader_id}")
    
    def is_leader_unlocked(self, leader_id: str) -> bool:
        """Check if a leader is unlocked"""
        return leader_id in self.unlock_data.get("unlocked_leaders", [])
    
    def is_card_unlocked(self, card_id: str) -> bool:
        """Check if a card is unlocked"""
        return card_id in self.unlock_data.get("unlocked_cards", [])
    
    def unlock_leader(self, leader_id: str):
        """Unlock a leader"""
        if leader_id not in self.unlock_data.get("unlocked_leaders", []):
            self.unlock_data.setdefault("unlocked_leaders", []).append(leader_id)
            self.save_unlocks()
            print(f"✓ Leader unlocked: {leader_id}")
    
    def unlock_card(self, card_id: str):
        """Unlock a card"""
        if card_id not in self.unlock_data.get("unlocked_cards", []):
            self.unlock_data.setdefault("unlocked_cards", []).append(card_id)
            self.save_unlocks()
            print(f"✓ Card unlocked: {card_id}")
    
    def record_game_result(self, won: bool, faction: str, mode: str = "ai"):
        """Record game result and update stats (mode: ai or lan)."""
        self.unlock_data["total_games"] = self.unlock_data.get("total_games", 0) + 1
        mode_key = "ai" if mode not in ("ai", "lan") else mode
        games_key = f"{mode_key}_games"
        wins_key = f"{mode_key}_wins"
        self.unlock_data[games_key] = self.unlock_data.get(games_key, 0) + 1
        
        if won:
            self.unlock_data["total_wins"] = self.unlock_data.get("total_wins", 0) + 1
            self.unlock_data["consecutive_wins"] = self.unlock_data.get("consecutive_wins", 0) + 1
            self.unlock_data[wins_key] = self.unlock_data.get(wins_key, 0) + 1
            
            # Track faction-specific wins
            faction_wins = self.unlock_data.setdefault("faction_wins", {})
            faction_wins[faction] = faction_wins.get(faction, 0) + 1
            
            print(f"✓ Win recorded! Consecutive wins: {self.unlock_data['consecutive_wins']}")
        else:
            self.unlock_data["consecutive_wins"] = 0
            print("✗ Loss recorded. Win streak reset.")
        
        # Track max streak
        current_streak = self.unlock_data.get("consecutive_wins", 0)
        max_streak = self.unlock_data.get("max_streak", 0)
        if current_streak > max_streak:
            self.unlock_data["max_streak"] = current_streak

        self.save_unlocks()

    def record_user_content_usage(self, deck_ids: List[str], leader_id: str, faction: str):
        """
        Track user content usage in games.

        Checks deck for user-created cards, leaders, and factions and
        updates the stats accordingly. Call this when starting a game.
        """
        try:
            from user_content_loader import is_user_card, is_user_leader, is_user_faction
        except ImportError:
            return  # No user content loader available

        stats = self.unlock_data.setdefault("user_content_stats", {
            "games_with_user_cards": 0,
            "games_with_user_leaders": 0,
            "games_with_user_factions": 0,
            "user_cards_played": {},
            "user_leaders_used": {},
            "user_factions_used": {},
        })

        # Check for user cards in deck
        user_cards = [cid for cid in deck_ids if is_user_card(cid)]
        if user_cards:
            stats["games_with_user_cards"] = stats.get("games_with_user_cards", 0) + 1
            for card_id in user_cards:
                stats.setdefault("user_cards_played", {})[card_id] = \
                    stats.get("user_cards_played", {}).get(card_id, 0) + 1

        # Check for user leader
        if is_user_leader(leader_id):
            stats["games_with_user_leaders"] = stats.get("games_with_user_leaders", 0) + 1
            stats.setdefault("user_leaders_used", {})[leader_id] = \
                stats.get("user_leaders_used", {}).get(leader_id, 0) + 1

        # Check for user faction
        if is_user_faction(faction):
            stats["games_with_user_factions"] = stats.get("games_with_user_factions", 0) + 1
            stats.setdefault("user_factions_used", {})[faction] = \
                stats.get("user_factions_used", {}).get(faction, 0) + 1

        self.save_unlocks()

    def get_user_content_stats(self) -> Dict:
        """Get user content statistics for the stats menu."""
        return self.unlock_data.get("user_content_stats", {
            "games_with_user_cards": 0,
            "games_with_user_leaders": 0,
            "games_with_user_factions": 0,
            "user_cards_played": {},
            "user_leaders_used": {},
            "user_factions_used": {},
        })
    
    def get_consecutive_wins(self) -> int:
        """Get current win streak"""
        return self.unlock_data.get("consecutive_wins", 0)
    
    def get_stats(self) -> Dict:
        """Get player statistics"""
        return {
            "total_games": self.unlock_data.get("total_games", 0),
            "total_wins": self.unlock_data.get("total_wins", 0),
            "ai_games": self.unlock_data.get("ai_games", 0),
            "ai_wins": self.unlock_data.get("ai_wins", 0),
            "lan_games": self.unlock_data.get("lan_games", 0),
            "lan_wins": self.unlock_data.get("lan_wins", 0),
            "consecutive_wins": self.unlock_data.get("consecutive_wins", 0),
            "max_streak": self.unlock_data.get("max_streak", 0),
            "faction_wins": self.unlock_data.get("faction_wins", {}),
            "unlocked_leaders": self.unlock_data.get("unlocked_leaders", []),
            "unlocked_cards": self.unlock_data.get("unlocked_cards", []),
            "leader_stats": self.unlock_data.get("leader_stats", {}),
            "matchups": self.unlock_data.get("matchups", {}),
            "last_results": self.unlock_data.get("last_results", []),
            "turn_stats": self.unlock_data.get("turn_stats", {}),
            "mulligans": self.unlock_data.get("mulligans", {}),
            "ability_usage": self.unlock_data.get("ability_usage", {}),
            "top_cards": self.unlock_data.get("top_cards", {}),
            "lan_reliability": self.unlock_data.get("lan_reliability", {}),
            "draft_stats": self.unlock_data.get("draft_stats", {}),
            "round_stats": self.unlock_data.get("round_stats", {}),
            "unlock_override_enabled": self.unlock_data.get("unlock_override_enabled", False),
        }

    def reset_stats(self):
        """Reset tracked stats (games, wins, streak, faction wins)."""
        self.unlock_data["total_games"] = 0
        self.unlock_data["total_wins"] = 0
        self.unlock_data["consecutive_wins"] = 0
        self.unlock_data["max_streak"] = 0
        self.unlock_data["faction_wins"] = {}
        self.unlock_data["ai_games"] = 0
        self.unlock_data["ai_wins"] = 0
        self.unlock_data["lan_games"] = 0
        self.unlock_data["lan_wins"] = 0
        self.unlock_data["leader_stats"] = {}
        self.unlock_data["matchups"] = {}
        self.unlock_data["last_results"] = []
        self.unlock_data["turn_stats"] = {}
        self.unlock_data["mulligans"] = {}
        self.unlock_data["ability_usage"] = {}
        self.unlock_data["top_cards"] = {}
        self.unlock_data["lan_reliability"] = {}
        self.unlock_data["round_stats"] = {
            "sweeps_for": 0,
            "sweeps_against": 0,
            "close_wins": 0,
            "close_losses": 0,
            "comebacks": 0,
            "first_turn_games": 0,
            "first_turn_wins": 0,
        }
        self.unlock_data["draft_stats"] = {
            "runs_started": 0,
            "runs_completed": 0,
            "battles_won": 0,
            "battles_lost": 0,
            "best_run_wins": 0,
            "perfect_runs": 0,
            "total_cards_drafted": 0,
            "drafted_leaders": {},
            "drafted_factions": {},
            "avg_deck_power": 0.0,
            "highest_deck_power": 0,
            "most_drafted_card": None,
            "card_draft_counts": {}
        }
        self.save_unlocks()

    def record_game_summary(self, summary: Dict):
        """Record rich game summary for advanced stats."""
        print(f"[persistence] Recording summary for leader: {summary.get('leader')}")
        # Leader stats
        leader_name = summary.get("leader") or "Unknown"
        leader_stats = self.unlock_data.setdefault("leader_stats", {})
        leader_entry = leader_stats.setdefault(leader_name, {"games": 0, "wins": 0})
        leader_entry["games"] += 1
        if summary.get("won"):
            leader_entry["wins"] += 1

        # Matchups
        pf = summary.get("player_faction", "Unknown")
        of = summary.get("opponent_faction", "Unknown")
        matchups = self.unlock_data.setdefault("matchups", {})
        pf_map = matchups.setdefault(pf, {})
        pair = pf_map.setdefault(of, {"games": 0, "wins": 0})
        pair["games"] += 1
        if summary.get("won"):
            pair["wins"] += 1

        # Max streak already tracked elsewhere; store last results for form
        last_results = self.unlock_data.setdefault("last_results", [])
        last_results.append("W" if summary.get("won") else "L")
        self.unlock_data["last_results"] = last_results[-10:]

        # Turn stats - ensure all keys exist even if dict was previously empty
        turn_stats = self.unlock_data.setdefault("turn_stats", {})
        turn_stats.setdefault("total", 0)
        turn_stats.setdefault("games", 0)
        turn_stats.setdefault("min", None)
        turn_stats.setdefault("max", None)
        turn_stats.setdefault("history", [])
        turns = summary.get("turns")
        if isinstance(turns, int):
            turn_stats["total"] += turns
            turn_stats["games"] += 1
            turn_stats["min"] = turns if turn_stats["min"] is None else min(turn_stats["min"], turns)
            turn_stats["max"] = turns if turn_stats["max"] is None else max(turn_stats["max"], turns)
            turn_stats["history"].append(turns)
            turn_stats["history"] = turn_stats["history"][-50:]

        # Mulligans - ensure all keys exist
        mull_data = self.unlock_data.setdefault("mulligans", {})
        mull_data.setdefault("total", 0)
        mull_data.setdefault("games", 0)
        mulls = summary.get("mulligans")
        if isinstance(mulls, int):
            mull_data["total"] += mulls
            mull_data["games"] += 1

        # Ability usage
        abilities = self.unlock_data.setdefault("ability_usage", {})
        print(f"[persistence] Recording abilities from summary: {summary.get('abilities', {})}")
        for key in ("medic", "decoy", "faction_power", "iris_blocks"):
            abilities[key] = abilities.get(key, 0) + int(summary.get("abilities", {}).get(key, 0))

        # Top cards - group by name so identical units (Recruit 1, 2, 3) count together
        top_cards = self.unlock_data.setdefault("top_cards", {})
        from cards import ALL_CARDS
        cards_played = summary.get("cards_played", [])
        print(f"[persistence] Recording {len(cards_played)} cards played")
        for cid in cards_played:
            if not cid:
                continue
            # Group by name
            card_name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            entry = top_cards.setdefault(card_name, {"plays": 0, "wins": 0, "id": cid})
            entry["plays"] += 1
            # Update ID to a valid one if the current one is somehow missing from ALL_CARDS
            if card_name not in ALL_CARDS and cid in ALL_CARDS:
                 entry["id"] = cid
                 
            if summary.get("won"):
                entry["wins"] += 1

        # Mode details
        if summary.get("mode") == "lan":
            lan_reliability = self.unlock_data.setdefault("lan_reliability", {})
            lan_reliability.setdefault("completed", 0)
            lan_reliability.setdefault("disconnects", 0)
            if summary.get("lan_completed"):
                lan_reliability["completed"] += 1
            if summary.get("lan_disconnect"):
                lan_reliability["disconnects"] += 1

        # Round breakdown stats (2-0 sweeps vs 2-1 close games, comebacks)
        round_stats = self.unlock_data.setdefault("round_stats", {})
        round_stats.setdefault("sweeps_for", 0)
        round_stats.setdefault("sweeps_against", 0)
        round_stats.setdefault("close_wins", 0)
        round_stats.setdefault("close_losses", 0)
        round_stats.setdefault("comebacks", 0)
        round_stats.setdefault("first_turn_games", 0)
        round_stats.setdefault("first_turn_wins", 0)
        
        player_rounds = summary.get("player_rounds_won", 0)
        opponent_rounds = summary.get("opponent_rounds_won", 0)
        won = summary.get("won", False)
        lost_round_1 = summary.get("lost_round_1", False)
        went_first = summary.get("went_first", False)
        
        if won:
            if opponent_rounds == 0:
                round_stats["sweeps_for"] += 1
            else:
                round_stats["close_wins"] += 1
            if lost_round_1:
                round_stats["comebacks"] += 1
        else:
            if player_rounds == 0:
                round_stats["sweeps_against"] += 1
            else:
                round_stats["close_losses"] += 1
        
        # First turn tracking
        if went_first is not None:
            round_stats["first_turn_games"] += 1
            if went_first and won:
                round_stats["first_turn_wins"] += 1

        # AI difficulty split
        self.save_unlocks()

    def record_draft_start(self):
        """Record that a draft run has started."""
        draft_stats = self.unlock_data.setdefault("draft_stats", {})
        draft_stats["runs_started"] = draft_stats.get("runs_started", 0) + 1
        self.save_unlocks()

    def record_draft_completion(self, leader_id: str, leader_name: str, faction: str,
                               cards: list, deck_power: int, won: bool, final_wins: int = 0):
        """
        Record draft run completion with full details.

        Args:
            leader_id: ID of drafted leader
            leader_name: Name of drafted leader
            faction: Leader's faction
            cards: List of drafted cards
            deck_power: Total power of drafted deck
            won: Whether the draft battle was won
            final_wins: Total wins in the run (if completed)
        """
        draft_stats = self.unlock_data.setdefault("draft_stats", {})

        # Capture old state for average calculation
        old_runs = draft_stats.get("runs_completed", 0)
        old_avg = draft_stats.get("avg_deck_power", 0.0)

        # Completion count
        draft_stats["runs_completed"] = old_runs + 1

        # Win/loss
        if won:
            draft_stats["battles_won"] = draft_stats.get("battles_won", 0) + 1
        else:
            draft_stats["battles_lost"] = draft_stats.get("battles_lost", 0) + 1

        # Best Run & Perfect Runs
        if final_wins > 0:
            if final_wins > draft_stats.get("best_run_wins", 0):
                draft_stats["best_run_wins"] = final_wins
            
            if final_wins >= 8:
                draft_stats["perfect_runs"] = draft_stats.get("perfect_runs", 0) + 1

        # Cards drafted
        draft_stats["total_cards_drafted"] = draft_stats.get("total_cards_drafted", 0) + len(cards)

        # Leader tracking
        drafted_leaders = draft_stats.setdefault("drafted_leaders", {})
        drafted_leaders[leader_name] = drafted_leaders.get(leader_name, 0) + 1

        # Faction tracking
        drafted_factions = draft_stats.setdefault("drafted_factions", {})
        drafted_factions[faction] = drafted_factions.get(faction, 0) + 1

        # Deck power tracking
        new_total_power = (old_avg * old_runs) + deck_power
        draft_stats["avg_deck_power"] = new_total_power / draft_stats["runs_completed"]

        if deck_power > draft_stats.get("highest_deck_power", 0):
            draft_stats["highest_deck_power"] = deck_power

        # Card draft counts
        card_counts = draft_stats.setdefault("card_draft_counts", {})
        for card in cards:
            card_id = card.id if hasattr(card, 'id') else str(card)
            card_counts[card_id] = card_counts.get(card_id, 0) + 1

        # Find most drafted card
        if card_counts:
            most_drafted = max(card_counts.items(), key=lambda x: x[1])
            draft_stats["most_drafted_card"] = most_drafted[0]

        self.save_unlocks()
        print(f"✓ Draft run recorded: {leader_name} ({'Win' if won else 'Loss'}), Deck Power: {deck_power}")

# Global instance
_persistence = None

def get_persistence() -> DeckPersistence:
    """Get global persistence instance"""
    global _persistence
    if _persistence is None:
        _persistence = DeckPersistence()
    return _persistence

def save_player_deck(faction: str, leader_id: str, card_ids: List[str]):
    """Save player's deck configuration"""
    persistence = get_persistence()
    persistence.set_deck(faction, leader_id, card_ids)

def load_player_deck(faction: str) -> Dict:
    """Load player's deck configuration"""
    persistence = get_persistence()
    return persistence.get_deck(faction)

def save_leader_choice(faction: str, leader_id: str):
    """Save player's leader choice"""
    persistence = get_persistence()
    persistence.set_leader(faction, leader_id)

def load_leader_choice(faction: str) -> str:
    """Load player's leader choice"""
    persistence = get_persistence()
    return persistence.get_leader(faction)

def record_victory(faction: str, mode: str = "ai"):
    """Record a victory"""
    persistence = get_persistence()
    persistence.record_game_result(True, faction, mode=mode)

def record_defeat(faction: str, mode: str = "ai"):
    """Record a defeat"""
    persistence = get_persistence()
    persistence.record_game_result(False, faction, mode=mode)

def check_leader_unlock() -> Optional[str]:
    """Check if player unlocked a new leader (3 consecutive wins)"""
    persistence = get_persistence()
    wins = persistence.get_consecutive_wins()

    if wins >= 3 and wins % 3 == 0:  # Every 3 wins
        # Return a random locked leader
        all_unlockable = [
            leader_id for leader_id in iter_unlockable_leader_ids()
            if not persistence.is_leader_unlocked(leader_id)
        ]

        if all_unlockable:
            import random
            unlocked_leader = random.choice(all_unlockable)
            persistence.unlock_leader(unlocked_leader)
            return unlocked_leader

    return None


# ============================================================================
# DECK EXPORT/IMPORT (JSON Format)
# ============================================================================

def export_deck_json(faction: str, filepath: str) -> bool:
    """Export a deck to a shareable JSON file.

    Args:
        faction: Faction name (e.g., "Tau'ri", "Goa'uld")
        filepath: Path to save the JSON file

    Returns:
        True if export successful, False otherwise

    JSON Format:
    {
        "version": "1.0",
        "faction": "Tau'ri",
        "leader": "tauri_oneill",
        "cards": ["tauri_carter", "tauri_jackson", ...]
    }
    """
    persistence = get_persistence()
    deck_data = persistence.get_deck(faction)

    if not deck_data:
        print(f"[deck-export] No deck found for faction: {faction}")
        return False

    export_data = {
        "version": "1.0",
        "faction": faction,
        "leader": deck_data.get("leader", ""),
        "cards": deck_data.get("cards", [])
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"[deck-export] Deck exported to {filepath}")
        return True
    except (IOError, OSError) as e:
        print(f"[deck-export] Failed to export deck: {e}")
        return False


def import_deck_json(filepath: str) -> Optional[Dict]:
    """Import a deck from a JSON file.

    Args:
        filepath: Path to the JSON file

    Returns:
        Dict with deck data if successful:
        {
            "faction": str,
            "leader": str,
            "cards": List[str]
        }
        Or None if import failed

    Note: This does NOT automatically save the deck.
    Call save_player_deck() to persist the imported deck.
    """
    if not os.path.exists(filepath):
        print(f"[deck-import] File not found: {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate required fields
        if not isinstance(data, dict):
            print("[deck-import] Invalid JSON format: expected object")
            return None

        faction = data.get("faction")
        leader = data.get("leader", "")
        cards = data.get("cards", [])

        if not faction:
            print("[deck-import] Missing required field: faction")
            return None

        if not isinstance(cards, list):
            print("[deck-import] Invalid cards field: expected array")
            return None

        # Validate cards exist in card database
        from cards import ALL_CARDS
        valid_cards = []
        invalid_cards = []

        for card_id in cards:
            if card_id in ALL_CARDS:
                valid_cards.append(card_id)
            else:
                invalid_cards.append(card_id)

        if invalid_cards:
            print(f"[deck-import] Warning: {len(invalid_cards)} unknown cards skipped: {invalid_cards[:5]}...")

        result = {
            "faction": faction,
            "leader": leader,
            "cards": valid_cards
        }

        print(f"[deck-import] Loaded deck: {faction}, leader={leader}, {len(valid_cards)} cards")
        return result

    except json.JSONDecodeError as e:
        print(f"[deck-import] Invalid JSON: {e}")
        return None
    except (IOError, OSError) as e:
        print(f"[deck-import] Failed to read file: {e}")
        return None


def import_and_save_deck(filepath: str) -> bool:
    """Import a deck from JSON and save it to persistence.

    Args:
        filepath: Path to the JSON file

    Returns:
        True if import and save successful, False otherwise
    """
    deck_data = import_deck_json(filepath)
    if not deck_data:
        return False

    faction = deck_data["faction"]
    leader = deck_data["leader"]
    cards = deck_data["cards"]

    save_player_deck(faction, leader, cards)
    print(f"[deck-import] Deck saved for {faction}")
    return True


def get_deck_summary(faction: str) -> Dict:
    """Get a summary of a deck for display/export preview.

    Args:
        faction: Faction name

    Returns:
        Dict with deck statistics:
        {
            "faction": str,
            "leader": str,
            "card_count": int,
            "total_power": int,
            "unit_counts": {"close": n, "ranged": n, "siege": n},
            "special_count": int,
            "weather_count": int
        }
    """
    from cards import ALL_CARDS

    persistence = get_persistence()
    deck_data = persistence.get_deck(faction)

    if not deck_data or not deck_data.get("cards"):
        return {
            "faction": faction,
            "leader": deck_data.get("leader", "") if deck_data else "",
            "card_count": 0,
            "total_power": 0,
            "unit_counts": {"close": 0, "ranged": 0, "siege": 0},
            "special_count": 0,
            "weather_count": 0
        }

    cards = deck_data["cards"]
    total_power = 0
    unit_counts = {"close": 0, "ranged": 0, "siege": 0}
    special_count = 0
    weather_count = 0

    for card_id in cards:
        if card_id not in ALL_CARDS:
            continue
        card = ALL_CARDS[card_id]
        total_power += card.power

        if card.row == "special":
            special_count += 1
        elif card.row == "weather":
            weather_count += 1
        elif card.row == "agile":
            # Agile cards count towards both close and ranged
            unit_counts["close"] += 0.5
            unit_counts["ranged"] += 0.5
        elif card.row in unit_counts:
            unit_counts[card.row] += 1

    return {
        "faction": faction,
        "leader": deck_data.get("leader", ""),
        "card_count": len(cards),
        "total_power": total_power,
        "unit_counts": {k: int(v) for k, v in unit_counts.items()},
        "special_count": special_count,
        "weather_count": weather_count
    }
