"""
STARGWENT - GALACTIC CONQUEST - Narrative Arcs (Story Chains)

Three story chains that track planet conquest sequences and award relics/bonuses.
Each arc requires conquering specific planets in any order.
"""

from dataclasses import dataclass, field


@dataclass
class NarrativeArc:
    """A story chain tracking a sequence of planet conquests."""
    id: str
    name: str
    description: str
    required_planets: list          # planet names that must be conquered
    rewards: dict                   # {"type": ..., "value": ...}
    completion_message: str


# All narrative arcs
NARRATIVE_ARCS = {
    "path_of_the_ancients": NarrativeArc(
        id="path_of_the_ancients",
        name="Path of the Ancients",
        description="Follow the trail of the Ancients through their forgotten outposts.",
        required_planets=["Heliopolis", "Kheb", "Atlantis"],
        rewards={"type": "relic", "value": "ancient_zpm"},
        completion_message="The Ancient ZPM hums to life! Unlimited power flows through the Stargate network.",
    ),
    "fall_of_the_system_lords": NarrativeArc(
        id="fall_of_the_system_lords",
        name="Fall of the System Lords",
        description="Dismantle the Goa'uld empire from their darkest strongholds.",
        required_planets=["Tartarus", "Netu", "Hasara"],
        rewards={"type": "naquadah_and_purge", "value": 150},
        completion_message="The System Lords are broken! Their empire crumbles. +150 Naquadah, 3 weak cards removed.",
    ),
    "jaffa_liberation": NarrativeArc(
        id="jaffa_liberation",
        name="Jaffa Liberation",
        description="Free the Jaffa people from millennia of servitude.",
        required_planets=["Dakara", "Hak'tyl", "Chulak"],
        rewards={"type": "relic_and_naquadah", "value": {"relic": "staff_of_ra", "naquadah": 100}},
        completion_message="The Jaffa are free! Teal'c would be proud. Staff of Ra + 100 Naquadah.",
    ),
}


def check_arc_progress(campaign_state, planet_name):
    """Check and update narrative arc progress after conquering a planet.

    Args:
        campaign_state: CampaignState instance
        planet_name: Name of the just-conquered planet

    Returns:
        List of (arc, step_number, total_steps, is_complete) tuples for arcs that advanced.
    """
    results = []
    progress = campaign_state.narrative_progress

    for arc_id, arc in NARRATIVE_ARCS.items():
        if planet_name not in arc.required_planets:
            continue

        # Initialize progress if needed
        if arc_id not in progress:
            progress[arc_id] = []

        # Already completed this arc
        if len(progress[arc_id]) >= len(arc.required_planets):
            continue

        # Add planet if not already tracked
        if planet_name not in progress[arc_id]:
            progress[arc_id].append(planet_name)

        step = len(progress[arc_id])
        total = len(arc.required_planets)
        is_complete = (step >= total)

        results.append((arc, step, total, is_complete))

    return results


def apply_arc_rewards(campaign_state, arc):
    """Apply the rewards for completing a narrative arc.

    Args:
        campaign_state: CampaignState instance
        arc: NarrativeArc that was completed
    """
    rewards = arc.rewards

    if rewards["type"] == "relic":
        relic_id = rewards["value"]
        if not campaign_state.has_relic(relic_id):
            campaign_state.add_relic(relic_id)

    elif rewards["type"] == "naquadah_and_purge":
        campaign_state.add_naquadah(rewards["value"])
        # Remove 3 weakest cards
        from cards import ALL_CARDS
        deck_power = [(cid, getattr(ALL_CARDS.get(cid), 'power', 0) or 0)
                      for cid in campaign_state.current_deck]
        deck_power.sort(key=lambda x: x[1])
        for cid, _ in deck_power[:3]:
            if len(campaign_state.current_deck) > 10:
                campaign_state.remove_card(cid)

    elif rewards["type"] == "relic_and_naquadah":
        relic_id = rewards["value"]["relic"]
        naq = rewards["value"]["naquadah"]
        if not campaign_state.has_relic(relic_id):
            campaign_state.add_relic(relic_id)
        campaign_state.add_naquadah(naq)


def get_arc_progress_display(campaign_state):
    """Get display data for all arcs (for Run Info screen).

    Returns:
        List of (arc_name, progress_str, is_complete) tuples.
    """
    display = []
    progress = campaign_state.narrative_progress

    for arc_id, arc in NARRATIVE_ARCS.items():
        completed_planets = progress.get(arc_id, [])
        step = len(completed_planets)
        total = len(arc.required_planets)
        is_complete = (step >= total)

        planets_str = " > ".join(
            f"[{p}]" if p in completed_planets else p
            for p in arc.required_planets
        )
        progress_str = f"{step}/{total}: {planets_str}"
        display.append((arc.name, progress_str, is_complete))

    return display
