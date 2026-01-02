"""
Deck Persistence System for StarGwent
Handles saving/loading player deck customizations and unlock progress
"""
import json
import os
from typing import Dict, List, Optional
from content_registry import iter_unlockable_leader_ids

# File paths for save data
DECK_SAVE_FILE = "player_decks.json"
UNLOCK_SAVE_FILE = "player_unlocks.json"

class DeckPersistence:
    """Manages persistent deck storage across game sessions"""
    
    def __init__(self):
        self.deck_data = self.load_decks()
        self.unlock_data = self.load_unlocks()
    
    def load_decks(self) -> Dict:
        """Load saved deck configurations"""
        if os.path.exists(DECK_SAVE_FILE):
            try:
                with open(DECK_SAVE_FILE, 'r') as f:
                    return json.load(f)
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
                "total_cards_drafted": 0,
                "drafted_leaders": {},  # leader_id: count
                "drafted_factions": {},  # faction: count
                "avg_deck_power": 0.0,
                "highest_deck_power": 0,
                "most_drafted_card": None,
                "card_draft_counts": {}  # card_id: count
            },
            "active_draft_run": None  # Stores current run state if active
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
                               cards: list, deck_power: int, won: bool):
        """
        Record draft run completion with full details.

        Args:
            leader_id: ID of drafted leader
            leader_name: Name of drafted leader
            faction: Leader's faction
            cards: List of drafted cards
            deck_power: Total power of drafted deck
            won: Whether the draft battle was won
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
            # For now, best run is just 1 (could expand for multi-battle runs later)
            if draft_stats.get("best_run_wins", 0) < 1:
                draft_stats["best_run_wins"] = 1
        else:
            draft_stats["battles_lost"] = draft_stats.get("battles_lost", 0) + 1

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
