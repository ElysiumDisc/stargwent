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
            }
        }
    
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
            "faction_wins": self.unlock_data.get("faction_wins", {}),
            "unlocked_leaders": len(self.unlock_data.get("unlocked_leaders", [])),
            "unlocked_cards": len(self.unlock_data.get("unlocked_cards", []))
        }

    def reset_stats(self):
        """Reset tracked stats (games, wins, streak, faction wins)."""
        self.unlock_data["total_games"] = 0
        self.unlock_data["total_wins"] = 0
        self.unlock_data["consecutive_wins"] = 0
        self.unlock_data["faction_wins"] = {}
        self.unlock_data["ai_games"] = 0
        self.unlock_data["ai_wins"] = 0
        self.unlock_data["lan_games"] = 0
        self.unlock_data["lan_wins"] = 0
        self.save_unlocks()

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
