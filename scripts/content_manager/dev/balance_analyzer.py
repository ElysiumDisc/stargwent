"""Developer workflow: Balance analyzer (power stats)."""

from collections import defaultdict

from ..ui import print_header


def balance_analyzer_workflow():
    """Analyze game balance statistics."""
    print_header("BALANCE ANALYZER")

    try:
        from cards import ALL_CARDS
    except ImportError:
        print("Could not import cards.py")
        return

    faction_stats = defaultdict(lambda: {"count": 0, "total_power": 0, "powers": []})
    row_stats = defaultdict(lambda: {"count": 0, "total_power": 0, "powers": []})
    ability_counts = defaultdict(int)

    for card_id, card in ALL_CARDS.items():
        if card.row in ["special", "weather"]:
            continue

        faction_stats[card.faction]["count"] += 1
        faction_stats[card.faction]["total_power"] += card.power
        faction_stats[card.faction]["powers"].append(card.power)

        row_stats[card.row]["count"] += 1
        row_stats[card.row]["total_power"] += card.power
        row_stats[card.row]["powers"].append(card.power)

        if card.ability:
            for ability in card.ability.split(", "):
                ability_counts[ability.strip()] += 1

    print("\n=== FACTION POWER DISTRIBUTION ===\n")
    print(f"{'Faction':<20} {'Cards':>6} {'Total':>7} {'Avg':>6} {'Min':>5} {'Max':>5}")
    print("-" * 55)

    for faction, stats in sorted(faction_stats.items()):
        if stats["count"] > 0:
            avg = stats["total_power"] / stats["count"]
            min_p = min(stats["powers"])
            max_p = max(stats["powers"])
            print(f"{faction:<20} {stats['count']:>6} {stats['total_power']:>7} {avg:>6.1f} {min_p:>5} {max_p:>5}")

    print("\n=== ROW POWER DISTRIBUTION ===\n")
    print(f"{'Row':<12} {'Cards':>6} {'Total':>7} {'Avg':>6}")
    print("-" * 35)

    for row, stats in sorted(row_stats.items()):
        if stats["count"] > 0:
            avg = stats["total_power"] / stats["count"]
            print(f"{row:<12} {stats['count']:>6} {stats['total_power']:>7} {avg:>6.1f}")

    print("\n=== ABILITY FREQUENCY ===\n")
    print(f"{'Ability':<35} {'Count':>6}")
    print("-" * 45)

    for ability, count in sorted(ability_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"{ability:<35} {count:>6}")

    print("\n=== POTENTIAL OUTLIERS ===\n")

    all_powers = [c.power for c in ALL_CARDS.values() if c.row not in ["special", "weather"]]
    avg_power = sum(all_powers) / len(all_powers) if all_powers else 0

    high_power = [(cid, c) for cid, c in ALL_CARDS.items()
                  if c.power > avg_power + 5 and c.row not in ["special", "weather"]]

    if high_power:
        print("High power cards (5+ above average):")
        for card_id, card in sorted(high_power, key=lambda x: -x[1].power)[:10]:
            print(f"  - {card.name} ({card.faction}): {card.power} power")
