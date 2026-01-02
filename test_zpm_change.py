import pygame
import os
import sys

# Mock pygame to avoid display issues in headless environment
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1, 1))

from game import Game
from cards import ALL_CARDS, Card

def test_asuran_warship_grants_zpm():
    print("Initializing Game...")
    # Initialize game with dummy callback
    game = Game(None)
    
    player = game.player1
    # Clear hand and board for clean test
    player.hand = []
    player.board = {"close": [], "ranged": [], "siege": []}
    
    # Add Asuran Warship to hand
    print("Adding Asuran Warship to hand...")
    warship = ALL_CARDS["asuran_warship"]
    # We need a fresh instance or copy to avoid modifying the global template if not careful
    # The game usually handles instantiation from templates in deck building, 
    # but here we are grabbing from ALL_CARDS which are Card objects.
    # play_card expects the card object to be in hand.
    player.hand.append(warship)
    
    print(f"Hand before play: {[c.name for c in player.hand]}")
    
    # Ensure it is player's turn
    game.current_player = player
    
    # Play the warship to siege row
    print("Playing Asuran Warship...")
    game.play_card(warship, "siege")
    
    # Check if ZPM was added to hand
    print(f"Hand after play: {[c.name for c in player.hand]}")
    
    zpm_cards = [c for c in player.hand if c.id == "zpm_power"]
    if zpm_cards:
        print("SUCCESS: ZPM card found in hand!")
    else:
        print("FAILURE: ZPM card NOT found in hand!")
        sys.exit(1)
        
    # Now test playing the ZPM card
    zpm = zpm_cards[0]
    print("Playing ZPM card...")
    
    # Ensure it is player's turn AGAIN
    game.current_player = player
    # Reset plays_this_turn to allow another play
    player.plays_this_turn = 0
    
    # ZPM is a special card, row="special"
    game.play_card(zpm, "special")
    
    if player.zpm_active:
        print("SUCCESS: ZPM effect is active!")
    else:
        print("FAILURE: ZPM effect is NOT active!")
        sys.exit(1)

    print("All tests passed.")

if __name__ == "__main__":
    try:
        test_asuran_warship_grants_zpm()
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
