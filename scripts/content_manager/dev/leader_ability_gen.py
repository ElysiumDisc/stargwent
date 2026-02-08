"""Developer workflow: Leader ability generator (code stub generator)."""

from ..config import ROOT
from ..ui import print_header, get_input, get_int, confirm, select_from_list
from ..logging_ import log


def leader_ability_generator_workflow():
    """Generate code stubs for new leader abilities."""
    print_header("LEADER ABILITY GENERATOR")

    print("This tool generates code stubs for new leader abilities.")
    print("You'll need to manually add the generated code to game.py\n")

    print("Ability Types:")
    print("  1. Passive Power Bonus (applied during score calculation)")
    print("  2. Once-Per-Game Manual Activation (player clicks button)")
    print("  3. Automatic Trigger (event-based like round start/end)")
    print("  4. Continuous Effect (always active)")
    print("  0. Back")
    print()

    choice = get_input("Select ability type", default="0")

    if choice == "0":
        return

    print()
    leader_name = get_input("Leader Name (e.g., 'Dr. McKay')")
    leader_id = get_input("Leader card_id (e.g., 'tauri_mckay')")
    ability_desc = get_input("Ability Description (what it does)")

    print()

    if choice == "1":
        _generate_passive_bonus_stub(leader_name, leader_id, ability_desc)
    elif choice == "2":
        _generate_manual_activation_stub(leader_name, leader_id, ability_desc)
    elif choice == "3":
        _generate_auto_trigger_stub(leader_name, leader_id, ability_desc)
    elif choice == "4":
        _generate_continuous_effect_stub(leader_name, leader_id, ability_desc)

    log(f"Generated leader ability stub for {leader_name} ({leader_id})")


def _generate_passive_bonus_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for passive power bonus ability."""
    print_header("PASSIVE POWER BONUS STUB")

    target_row = select_from_list("Which row to buff?", ["close", "ranged", "siege", "all rows"])
    bonus = get_int("Power bonus amount", min_val=1, max_val=5, default=2)
    hero_included = confirm("Does the bonus apply to heroes too?", default=False)

    hero_check = "# Note: Applies to heroes too" if hero_included else "if not is_hero(card):"
    indent = "" if hero_included else "    "

    if target_row == "all rows":
        row_code = '''for row_name in ["close", "ranged", "siege"]:
            for card in player.board.get(row_name, []):'''
    else:
        row_code = f'''for card in player.board.get("{target_row}", []):'''

    stub = f'''
# =============================================================================
# ADD TO game.py - In calculate_scores_and_log() method (~line 485)
# Find the section where leader abilities modify power
# =============================================================================

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    {row_code}
        {hero_check}
        {indent}card.displayed_power = getattr(card, 'displayed_power', card.power) + {bonus}
'''

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print("1. Open game.py")
    print("2. Find the calculate_scores_and_log() method (around line 485)")
    print("3. Look for other leader ability checks (search for 'player.leader')")
    print("4. Add this code in the same section")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")


def _generate_manual_activation_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for once-per-game manual activation ability."""
    print_header("MANUAL ACTIVATION STUB")

    stub = f'''
# =============================================================================
# ADD TO game.py - In activate_leader_ability() method (~line 1694)
# =============================================================================

# In the activate_leader_ability method, add this elif clause:

elif "{leader_name}" in leader_name:
    result = self._activate_{leader_id.split('_')[1]}_ability(player)

# =============================================================================
# ADD TO game.py - New method (add after other _activate_* methods ~line 2000)
# =============================================================================

def _activate_{leader_id.split('_')[1]}_ability(self, player):
    """
    {leader_name}: {desc}
    """
    # TODO: Implement ability logic here

    # Example: If ability needs UI selection, return requires_ui
    # return {{
    #     "ability": "{leader_name} Ability",
    #     "revealed_cards": eligible_cards,
    #     "requires_ui": True
    # }}

    # Example: If ability is immediate effect
    self.add_history_event(
        "ability",
        f"{{player.name}} ({leader_name}) activated their ability!",
        self._owner_label(player),
        icon="\\u26a1"
    )

    return {{"ability": "{leader_name} Ability"}}

# =============================================================================
# If ability needs UI interaction, also add a completion method:
# =============================================================================

def {leader_id.split('_')[1]}_complete_ability(self, player, chosen_card):
    """Complete {leader_name}'s ability after UI selection."""
    # TODO: Implement completion logic

    # Mark leader ability as used after successful completion
    self.leader_ability_used[player] = True
    self.calculate_scores_and_log()
    return True
'''

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print("1. Open game.py")
    print("2. Add the elif clause to activate_leader_ability() method (~line 1694)")
    print("3. Add the _activate_*_ability method after similar methods (~line 2000)")
    print("4. If UI interaction needed, add the completion method too")
    print("5. Add UI handling in main.py if requires_ui is True")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")


def _generate_auto_trigger_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for automatic trigger ability."""
    print_header("AUTOMATIC TRIGGER STUB")

    trigger = select_from_list("When does this trigger?", [
        "round_start",
        "round_end",
        "turn_start",
        "turn_end",
        "card_played",
        "card_destroyed",
        "pass_turn"
    ])

    stub = f'''
# =============================================================================
# ADD TO game.py - Find the appropriate trigger location
# =============================================================================
'''

    trigger_stubs = {
        "round_start": f'''
# In start_round() method (~line 200), add:

# {leader_name} Leader Ability: {desc}
for player in [self.player1, self.player2]:
    if player.leader and "{leader_name}" in player.leader.get('name', ''):
        # TODO: Implement round start effect
        self.add_history_event(
            "ability",
            f"{{player.name}} ({leader_name})'s ability triggered!",
            self._owner_label(player),
            icon="\\u26a1"
        )
''',
        "round_end": f'''
# In end_round() method (~line 350), add:

# {leader_name} Leader Ability: {desc}
for player in [self.player1, self.player2]:
    if player.leader and "{leader_name}" in player.leader.get('name', ''):
        # TODO: Implement round end effect
        self.add_history_event(
            "ability",
            f"{{player.name}} ({leader_name})'s ability triggered!",
            self._owner_label(player),
            icon="\\u26a1"
        )
''',
        "card_played": f'''
# In play_card() method (~line 500), after card is placed, add:

# {leader_name} Leader Ability: {desc}
if self.current_player.leader and "{leader_name}" in self.current_player.leader.get('name', ''):
    # TODO: Implement card played effect
    # card variable contains the card that was just played
    self.add_history_event(
        "ability",
        f"{{self.current_player.name}} ({leader_name})'s ability triggered!",
        self._owner_label(self.current_player),
        icon="\\u26a1"
    )
''',
        "pass_turn": f'''
# In pass_turn() method, add:

# {leader_name} Leader Ability: {desc}
if self.current_player.leader and "{leader_name}" in self.current_player.leader.get('name', ''):
    # TODO: Implement pass turn effect
    self.add_history_event(
        "ability",
        f"{{self.current_player.name}} ({leader_name})'s ability triggered on pass!",
        self._owner_label(self.current_player),
        icon="\\u26a1"
    )
''',
    }

    stub += trigger_stubs.get(trigger, f'''
# Find the appropriate trigger point for: {trigger}
# {leader_name} Leader Ability: {desc}

if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # TODO: Implement {trigger} effect
    self.add_history_event(
        "ability",
        f"{{player.name}} ({leader_name})'s ability triggered!",
        self._owner_label(player),
        icon="\\u26a1"
    )
''')

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print(f"1. Open game.py")
    print(f"2. Find the {trigger} trigger location")
    print("3. Add the code at the appropriate point")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")


def _generate_continuous_effect_stub(leader_name: str, leader_id: str, desc: str):
    """Generate code stub for continuous effect ability."""
    print_header("CONTINUOUS EFFECT STUB")

    effect_type = select_from_list("What type of continuous effect?", [
        "weather_immunity",
        "power_modifier",
        "draw_modifier",
        "custom"
    ])

    stub = f'''
# =============================================================================
# CONTINUOUS EFFECT: {leader_name} - {desc}
# =============================================================================
'''

    effect_stubs = {
        "weather_immunity": f'''
# In apply_weather_effect() method, add check at the start:

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # Skip weather effect for this player
    return []  # Or modify the effect as needed
''',
        "power_modifier": f'''
# In calculate_scores_and_log() method (~line 485), add:

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    for row_name in ["close", "ranged", "siege"]:
        for card in player.board.get(row_name, []):
            # TODO: Apply continuous power modifier
            # Example: card.displayed_power += 1
            pass
''',
        "draw_modifier": f'''
# In draw_card() method, add:

# {leader_name} Leader Ability: {desc}
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # TODO: Modify draw behavior
    # Example: Draw extra card
    # self._draw_single_card(player)
    pass
''',
        "custom": f'''
# {leader_name} Leader Ability: {desc}
#
# IMPLEMENTATION NOTES:
# - Continuous effects should be checked wherever they apply
# - Common locations:
#   - calculate_scores_and_log() for power modifiers
#   - apply_weather_effect() for weather immunity
#   - draw_card() for draw modifiers
#   - play_card() for card play effects
#
# Add checks like:
if player.leader and "{leader_name}" in player.leader.get('name', ''):
    # TODO: Implement continuous effect
    pass
''',
    }

    stub += effect_stubs.get(effect_type, effect_stubs["custom"])

    print(stub)
    print("=" * 70)
    print()
    print("INSTRUCTIONS:")
    print("1. Open game.py")
    print("2. Find the appropriate method(s) based on effect type")
    print("3. Add the check wherever the effect should apply")
    print()

    if confirm("Save this stub to a file?", default=True):
        stub_file = ROOT / "scripts" / f"leader_stub_{leader_id}.py"
        stub_file.write_text(stub)
        print(f"\n[OK] Stub saved to: {stub_file}")
