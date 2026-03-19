"""
STARGWENT - GALACTIC CONQUEST - Relic / Artifact System

Stargate-themed relics with permanent passive effects for the campaign run.
Relics are acquired by conquering homeworlds, completing story arcs, or events.
"""

from dataclasses import dataclass


@dataclass
class Relic:
    """A collectible artifact with a passive campaign effect."""
    id: str
    name: str
    description: str
    icon_char: str        # Unicode character for HUD display
    category: str         # "combat" | "economy" | "exploration"


# All available relics
RELICS = {
    # === Combat Relics ===
    "staff_of_ra": Relic(
        id="staff_of_ra",
        name="Staff of Ra",
        description="+1 power to all Goa'uld cards in your deck",
        icon_char="\u2694",  # crossed swords
        category="combat",
    ),
    "thors_hammer": Relic(
        id="thors_hammer",
        name="Thor's Hammer",
        description="+2 power to all Hero cards",
        icon_char="\u2692",  # hammer and pick
        category="combat",
    ),
    "kull_armor": Relic(
        id="kull_armor",
        name="Kull Armor",
        description="-1 power to all enemy cards (min 1)",
        icon_char="\u26E8",  # shield
        category="combat",
    ),
    "iris_shield": Relic(
        id="iris_shield",
        name="Iris Shield",
        description="Block the first Spy card played against you",
        icon_char="\u25CE",  # bullseye
        category="combat",
    ),
    "ancient_zpm": Relic(
        id="ancient_zpm",
        name="Ancient ZPM",
        description="+1 starting card in all battles",
        icon_char="\u26A1",  # lightning
        category="combat",
    ),
    "ori_prior_staff": Relic(
        id="ori_prior_staff",
        name="Ori Prior Staff",
        description="Weather effects deal minimum 3 power reduction (not 1)",
        icon_char="\u2721",  # star
        category="combat",
    ),
    "sarcophagus": Relic(
        id="sarcophagus",
        name="Sarcophagus",
        description="Revive: +1 random card from your discard after each round",
        icon_char="\u2625",  # ankh
        category="combat",
    ),

    # === Economy Relics ===
    "asgard_core": Relic(
        id="asgard_core",
        name="Asgard Core",
        description="+20 bonus Naquadah per victory",
        icon_char="\u2B50",  # star
        category="economy",
    ),
    "naquadah_reactor": Relic(
        id="naquadah_reactor",
        name="Naquadah Reactor",
        description="+10 Naquadah per turn (passive income)",
        icon_char="\u2622",  # radioactive
        category="economy",
    ),

    # === Exploration Relics ===
    "ring_platform": Relic(
        id="ring_platform",
        name="Ring Platform",
        description="Attack planets 2 hops away (not just adjacent)",
        icon_char="\u25EF",  # large circle
        category="exploration",
    ),
    "replicator_nanites": Relic(
        id="replicator_nanites",
        name="Replicator Nanites",
        description="20% chance to duplicate chosen reward card",
        icon_char="\u2234",  # therefore (dots)
        category="exploration",
    ),
    "alteran_database": Relic(
        id="alteran_database",
        name="Alteran Database",
        description="+1 card choice on all reward screens",
        icon_char="\u2261",  # triple bar
        category="exploration",
    ),
    "quantum_mirror": Relic(
        id="quantum_mirror",
        name="Quantum Mirror",
        description="See enemy hand size during battles",
        icon_char="\u2B2F",  # mirror
        category="exploration",
    ),
    "teltak_transport": Relic(
        id="teltak_transport",
        name="Tel'tak Transport",
        description="See defender power total before attacking",
        icon_char="\u2708",  # airplane
        category="exploration",
    ),
    "jaffa_tretonin": Relic(
        id="jaffa_tretonin",
        name="Jaffa Tretonin",
        description="Weather can't reduce your cards below 3 power",
        icon_char="\u2695",  # caduceus
        category="combat",
    ),
    "ancient_repository": Relic(
        id="ancient_repository",
        name="Ancient Repository",
        description="+30 naq/turn if you control Atlantis",
        icon_char="\u2261",  # triple bar
        category="economy",
    ),
    "asgard_time_machine": Relic(
        id="asgard_time_machine",
        name="Asgard Time Machine",
        description="Once per campaign: undo last planet loss",
        icon_char="\u231B",  # hourglass
        category="exploration",
    ),
    "flames_of_celestis": Relic(
        id="flames_of_celestis",
        name="Flames of Celestis",
        description="+2 power to first card played each round",
        icon_char="\U0001F525",  # fire
        category="combat",
    ),
}


# Guaranteed relic per conquered homeworld
HOMEWORLD_RELICS = {
    "Goa'uld": "sarcophagus",
    "Tau'ri": "iris_shield",
    "Jaffa Rebellion": "kull_armor",
    "Lucian Alliance": "naquadah_reactor",
    "Asgard": "asgard_core",
}


def get_relic(relic_id):
    """Get a Relic by ID, or None if not found."""
    return RELICS.get(relic_id)


def get_homeworld_relic(faction):
    """Get the relic ID awarded for conquering a faction's homeworld."""
    return HOMEWORLD_RELICS.get(faction)
