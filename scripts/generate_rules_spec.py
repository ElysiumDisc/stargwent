"""
Generate the comprehensive Rule Menu specification for Stargwent.
Aggregates data from cards.py, content_registry.py, unlocks.py, and README-driven lore.
"""

from __future__ import annotations

import ast
import datetime
import json
from collections import defaultdict
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
CARD_CATALOG_PATH = ROOT / "docs" / "card_catalog.json"
LEADER_CATALOG_PATH = ROOT / "docs" / "leader_catalog.json"
UNLOCKS_PATH = ROOT / "unlocks.py"
SPEC_PATH = ROOT / "docs" / "rules_menu_spec.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def parse_assign_dict(module_src: str, name: str):
    tree = ast.parse(module_src)
    target_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    target_node = node.value
                    break
        if target_node:
            break
    if target_node is None:
        raise ValueError(f"Could not find assignment for {name}")

    def node_to_value(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Dict):
            return {
                node_to_value(k): node_to_value(v)
                for k, v in zip(node.keys, node.values)
            }
        if isinstance(node, ast.List):
            return [node_to_value(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(node_to_value(item) for item in node.elts)
        return ast.unparse(node)

    return node_to_value(target_node)


def build_combo_lookup():
    combos = [
        {
            "name": "SG-1 United",
            "members": [
                "Col. Jack O'Neill",
                "Dr. Samantha Carter",
                "Dr. Daniel Jackson",
                "V. Teal'c",
            ],
            "bonus": "+5 power to each member when all four are on board",
            "description": "Classic SG-1 lineup rallies for a massive spike once the full team is deployed.",
        },
        {
            "name": "Tok'ra Alliance",
            "members": ["Dr. Samantha Carter", "Tok'ra Operative"],
            "bonus": "+3 power to both units",
            "description": "Joint Tau'ri and Tok'ra operations amplify Carter's tactical planning.",
        },
        {
            "name": "System Lords Summit",
            "members": ["Apophis", "Yu the Great", "Sokar"],
            "bonus": "+4 power to each System Lord",
            "description": "A temporary truce between rival Goa'uld unleashes terrifying authority.",
        },
    ]
    lookup = defaultdict(list)
    for combo in combos:
        for member in combo["members"]:
            lookup[member].append(combo)
    return combos, lookup


def build_ability_info():
    return {
        "Legendary Commander": {
            "effect": "Hero unit immune to weather, Command Network doubling, Naquadah Overload, Medical Evac targeting, and most status effects.",
            "timing": "Passive as long as the unit stays on the board.",
            "synergy": "Ideal anchor for horns, benefits from Heimdall and Aegir buffs, and ignores Lucian self-damage from Unstable Naquadah.",
        },
        "Tactical Formation": {
            "effect": "Identical copies in the same row multiply their base power by the number of copies (applies after weather adjustments).",
            "timing": "Re-evaluated every score calculation while at least two copies remain in the row.",
            "synergy": "Best with Gate Reinforcement units and horn slots; Ka'lel boosts can push tight-bond spikes even higher.",
        },
        "Gate Reinforcement": {
            "effect": "When played, immediately pulls every copy of the unit from hand and deck into the same row.",
            "timing": "Triggers the moment the original card resolves on the battlefield.",
            "synergy": "Thins the deck, supercharges Tactical Formation groups, and feeds Ishta's leader buff while exposing you to Scorch if you over-stack.",
        },
        "Life Force Drain": {
            "effect": "After Gate Reinforcement finishes spawning copies, steals 1 base power from a random enemy unit per copy (minimum 1).",
            "timing": "Automatically after muster resolves.",
            "synergy": "Pairs with System Lord's Curse for swing turns; works best when opponents keep midrange units vulnerable.",
        },
        "System Lord's Curse": {
            "effect": "After a Gate Reinforcement wave lands, reduces every opposing card in the mirrored row by 1 power (minimum 1).",
            "timing": "Immediately after muster resolves.",
            "synergy": "Amplifies Scorch setups and punishes enemy row stacking, especially when combined with Naquadah Overload.",
        },
        "Deep Cover Agent": {
            "effect": "Placed on the opponent's side as a spy; draws 2 cards (3 if Lucian Piracy passive or Vulkar leader is active).",
            "timing": "Draw happens as soon as the spy enters the opponent's row.",
            "synergy": "Fuel for combo pieces, activates Lucian Piracy bonus, and can bait weather on the enemy board.",
        },
        "Medical Evac": {
            "effect": "Opens the medic UI so you can choose any non-Hero unit from your discard pile and replay it instantly.",
            "timing": "Triggered on play; selection pauses the game until resolved.",
            "synergy": "Loop key engines, recover horn targets after Scorch, and extend Gate Reinforcement waves.",
        },
        "Deploy Clones": {
            "effect": "Spawns two Shield Maiden tokens (2 power each) into the same row.",
            "timing": "Instantly, right after the source unit resolves.",
            "synergy": "Adds bodies for Tactical Formation math and Brotherhood stacking; protects against weather attrition.",
        },
        "Activate Combat Protocol": {
            "effect": "Summons a single 5-power Asgard Avenger token to the chosen row.",
            "timing": "Immediate on-play effect.",
            "synergy": "Guarantees board presence for Command Network turns and provides expendable fodder for Iris trades.",
        },
        "Genetic Enhancement": {
            "effect": "Finds the weakest non-Hero in each friendly row and upgrades it to an 8-power berserker, granting Survival Instinct if missing.",
            "timing": "Triggers instantly after play resolves.",
            "synergy": "Great with low-power token floods and ensures resilience versus weather lanes.",
        },
        "Survival Instinct": {
            "effect": "Whenever weather hits its row, the unit ignores the 1-power cap and instead gains +2 power over its base.",
            "timing": "Passive; evaluated each time weather would normally reduce power.",
            "synergy": "Turns enemy hazards into buffs and combos with Hermiod/Freyr weather control to weaponize storms.",
        },
        "Inspiring Leadership": {
            "effect": "Boosts adjacent friendly units that are not Legendary by +1 power each time scores are recalculated.",
            "timing": "Continuous aura along the row.",
            "synergy": "Place between high-value engines or Gate Reinforcement stacks to double-dip on adjacency bonuses.",
        },
        "Command Network": {
            "effect": "Acts as Commander's Horn: doubles the displayed power of every non-Hero in the targeted row for the rest of the round.",
            "timing": "Applied immediately and persists until round end; only one horn per row.",
            "synergy": "Pairs with Tactical Formation and Brotherhood; remember horn slots occupy visible HUD panels for clarity.",
        },
        "Naquadah Overload": {
            "effect": "Scorch effect that destroys the highest-power non-Hero units on the battlefield (both sides if tied). Merlin variants only hit the opponent.",
            "timing": "Resolves instantly on play.",
            "synergy": "Best after baiting out Legendary commanders; combos with System Lord's Curse to soften specific rows beforehand.",
        },
        "Ring Transport": {
            "effect": "Interactive special that highlights all valid units and returns any selected non-Hero to your hand.",
            "timing": "Selection UI triggers on play; effect resolves once the player confirms.",
            "synergy": "Recycle deploy abilities, protect engines from Scorch, and trigger on-play effects multiple times.",
        },
        "Ice Planet Hazard": {
            "effect": "Close-combat weather that reduces non-Heroes to 1 power on affected sides.",
            "timing": "Stays until cleared; respects Freyr/Hermiod shields.",
            "synergy": "Lock down melee swarms and set up Brotherhood denial.",
        },
        "Nebula Interference": {
            "effect": "Ranged-row weather with the standard 1-power rule.",
            "timing": "Persistent until cleared.",
            "synergy": "Shuts down archers and spy spam while Survival Instinct units profit.",
        },
        "Asteroid Storm": {
            "effect": "Siege-row weather applying the 1-power cap.",
            "timing": "Persistent until cleared.",
            "synergy": "Counter starship piles and Apophis raid triggers; combine with Gate Shutdown for wipe turns.",
        },
        "Electromagnetic Pulse": {
            "effect": "Targetable weather: choose any row and apply the 1-power rule.",
            "timing": "Takes effect immediately and lasts until cleared.",
            "synergy": "Flexible answer to horned rows; Hermiod leader causes EMP to hit opponents only.",
        },
        "Wormhole Stabilization": {
            "effect": "Clears every active weather, removes hazard icons, and restores normal power.",
            "timing": "Instant cure.",
            "synergy": "Resets the board before committing horn turns or Survival Instinct units.",
        },
        "Prometheus Draw Protocol": {
            "effect": "Every Prometheus-class card draws 1 card for its owner upon being played.",
            "timing": "Draw happens immediately after deployment.",
            "synergy": "Encourages repeated deployment via Ring Transport and Medical Evac loops.",
        },
        "Mothership Logistics": {
            "effect": "Any card with \"Mothership\" in its name draws 2 cards for its owner when played.",
            "timing": "Instant draw.",
            "synergy": "Refuels siege strategies and helps refill after Naquadah Overload self-damage.",
        },
        "Remove all Goa'uld": {
            "effect": "Thor's Hammer effect: purges every Goa'uld faction unit from both boards.",
            "timing": "Instant global cleanse.",
            "synergy": "Reset stubborn hero piles and open lanes for Tau'ri pushes.",
        },
        "Double all your siege": {
            "effect": "Zero Point Module doubles the displayed power of all your siege units for the rest of the round.",
            "timing": "Applies immediately to existing siege rows.",
            "synergy": "Combine with horns or Cronus leader to spike absurd totals.",
        },
        "Reveal opponent's hand": {
            "effect": "Communication Stones or Sodan recon reveal every card in the enemy hand until the round ends.",
            "timing": "Instant; stays visible for the round.",
            "synergy": "Informs Deep Cover Agent placement and Lord Yu turn planning.",
        },
        "Draw 1 card when played": {
            "effect": "Self-explanatory cantrip on deploy.",
            "timing": "Immediate draw.",
            "synergy": "Keeps your hand full for Gate Reinforcement combos and faction passives.",
        },
        "Draw 2 cards when played": {
            "effect": "Automatic double draw upon deployment.",
            "timing": "Immediate.",
            "synergy": "Massive refill for siege engines; best with Lucian piracy because spies still draw extra.",
        },
        "When played: Look at opponent's hand": {
            "effect": "Recon ping that exposes opponent cards for the round.",
            "timing": "Instant reveal when the card resolves.",
            "synergy": "Pairs with Lord Yu or Communication Device to keep intel flooding.",
        },
        "Naquadah Overload: Destroy lowest enemy unit": {
            "effect": "Ancient Drone variant that targets the lowest-power enemy instead of the highest.",
            "timing": "Immediate strike.",
            "synergy": "Pick off engines hiding behind big tanks; works even through horned rows.",
        },
    }


DEFAULT_ABILITY = {
    "effect": "No keyword ability; relies on raw stats and row placement.",
    "timing": "Always active.",
    "synergy": "Ideal horn targets or filler for Tactical Formation groups.",
}

ROW_LABELS = {
    "close": "Close Combat",
    "ranged": "Ranged",
    "siege": "Siege",
    "agile": "Agile (close or ranged)",
    "special": "Special",
    "weather": "Weather",
}

ROW_TYPE_LABEL = {
    "close": "unit",
    "ranged": "unit",
    "siege": "unit",
    "agile": "unit",
    "special": "special",
    "weather": "weather",
}
SPECIAL_NAME_ABILITIES = [
    (lambda name: "Prometheus" in name, "Prometheus Draw Protocol"),
    (lambda name: "Mothership" in name, "Mothership Logistics"),
]

FACTION_ORDER = [
    "Tau'ri",
    "Goa'uld",
    "Jaffa Rebellion",
    "Lucian Alliance",
    "Asgard",
    "Neutral",
]


def build_leader_notes():
    return {
        "Col. Jack O'Neill": {
            "timing": "Draws 1 extra card at the start of rounds 2 and 3 (stacks with Tau'ri Resourcefulness).",
            "synergy": "Ensures SG-1 combo consistency and keeps Iris Defense fueled.",
        },
        "Gen. George Hammond": {
            "timing": "First unit you play each round gains a permanent +3 tag.",
            "synergy": "Lead with tanky Gate Reinforcement units for commanding board states.",
        },
        "Dr. Samantha Carter": {
            "timing": "Applies +2 to every siege unit you control during score calculation.",
            "synergy": "Stacks with Zero Point Module and Command Network pushes.",
        },
        "Gen. Landry": {
            "timing": "Each friendly unit that survives a round gains +1 cumulative base power.",
            "synergy": "Rewards patient play and Medical Evac loops.",
        },
        "Dr. McKay": {
            "timing": "Draw 2 cards immediately when you pass a round.",
            "synergy": "Ideal for tactics where you slam tempo then bank cards for later rounds.",
        },
        "Jonas Quinn": {
            "timing": "Peeks at the next card your opponent will play.",
            "synergy": "Use intel to time Iris Defense and Command Network counters.",
        },
        "Catherine Langford": {
            "timing": "Neutral cards ignore deck restrictions while she is your leader.",
            "synergy": "Allows hybrid Tau'ri/Neutral builds with Atlantis and Destiny.",
        },
        "Apophis": {
            "timing": "Once per game, unleashes a random weather hazard that honors all immunity rules.",
            "synergy": "Combine with Asgard Beam artifact or Hermiod to skew hazards in your favor.",
        },
        "Lord Yu": {
            "timing": "When you pass, the opponent's next-round hand is revealed until the round ends.",
            "synergy": "Pairs with Deep Cover Agents and Sodan scouts for relentless intel.",
        },
        "Sokar": {
            "timing": "All of your Close Combat units gain +1 during score calculation.",
            "synergy": "Best with Horus Guard life-drain packages and horns.",
        },
        "Ba'al": {
            "timing": "At the start of each round copies your highest-power unit.",
            "synergy": "Clone Legendary ships or buffed Ha'tak stacks for unstoppable boards.",
        },
        "Anubis": {
            "timing": "Automatically fires Naquadah Overload at the start of rounds 2 and 3.",
            "synergy": "Plan to preserve Heroes and Survival Instinct cards for those rounds.",
        },
        "Hathor": {
            "timing": "At round start steals the opponent's lowest-power unit from their board.",
            "synergy": "Destabilizes swarm strategies and feeds Lucian horn lanes.",
        },
        "Cronus": {
            "timing": "All your units gain +1/+2/+3 based on the round number.",
            "synergy": "Works wonders with Gate Reinforcement floods that span multiple rounds.",
        },
        "Teal'c": {
            "timing": "Draw 1 card each time you win a round.",
            "synergy": "Keeps Free Jaffa ahead in cards even while trading resources.",
        },
        "Bra'tac": {
            "timing": "All Agile cards get +1 power.",
            "synergy": "Encourages flexible row deployment and works with Ka'lel buffs.",
        },
        "Rak'nor": {
            "timing": "On the first turn of every round you may play two cards instead of one.",
            "synergy": "Explosive openings with Brotherhood stacks or Gate Reinforcement.",
        },
        "Master Bra'tac": {
            "timing": "All friendly units gain +3 power in round 3.",
            "synergy": "Sandbag to the final round for unstoppable finishing pushes.",
        },
        "Ka'lel": {
            "timing": "The first three units you play each round get +2 power.",
            "synergy": "Buffs tactical swarms and synergizes with Deep Cover Agents you reclaim.",
        },
        "Gerak": {
            "timing": "Draw 1 card after every second unit you play.",
            "synergy": "Rewards wide deployments; maintain tempo while refilling hand.",
        },
        "Ishta": {
            "timing": "All Gate Reinforcement units gain +2 power.",
            "synergy": "Makes even 1-power militia into legitimate threats once mustered.",
        },
        "Vulkar": {
            "timing": "Spy cards draw 3 instead of 2.",
            "synergy": "Lucian Piracy passive plus Vulkar lets you churn through decks instantly.",
        },
        "Sodan Master": {
            "timing": "Boosts the highest-power unit in each row by +3.",
            "synergy": "Protects tall strategies and punishes weather attempts to shave peaks.",
        },
        "Ba'al Clone": {
            "timing": "All Ranged units gain +2 power.",
            "synergy": "Pairs with Lucian snipers and Tok'ra Operatives for safe pressure.",
        },
        "Netan": {
            "timing": "Generates a random Neutral card at the start of each round.",
            "synergy": "Pushes smuggler themes and lets you access Ancient tech midgame.",
        },
        "Vala Mal Doran": {
            "timing": "Once per game look at the top 3 cards of your deck and keep one.",
            "synergy": "Cherry-pick Command Network or Scorch answers when needed.",
        },
        "Anateo": {
            "timing": "Can use Medical Evac once per round without playing a medic card.",
            "synergy": "Sustain Lucian tempo and loop high-impact units safely.",
        },
        "Kiva": {
            "timing": "Play two cards on your very first turn of the game.",
            "synergy": "Great for early horn setups or double-spy gambits.",
        },
        "Freyr": {
            "timing": "Your side is completely immune to weather effects.",
            "synergy": "Lets you weaponize hazards with no downside and shrink enemy lanes.",
        },
        "Loki": {
            "timing": "Every time you play a unit, steal 1 power from the opponent's strongest non-Hero and give it to a random friendly unit.",
            "synergy": "Snowballs power advantage and punishes tall enemy builds.",
        },
        "Heimdall": {
            "timing": "All Legendary Commanders gain +3 power.",
            "synergy": "Turns every hero into a must-answer finisher, especially SG-1 or Asgard heavy ships.",
        },
        "Thor Supreme Commander": {
            "timing": "Once per round you may move any unit to a different valid row.",
            "synergy": "Dodge weather, re-trigger Tactical Formation, or steal horned rows.",
        },
        "Hermiod": {
            "timing": "Any weather you play only affects your opponent.",
            "synergy": "Combine with Apophis or Asgard beams for unilateral board control.",
        },
        "Penegal": {
            "timing": "Revives one random unit from your discard pile at the start of rounds 2 and 3.",
            "synergy": "Fuels attrition plans and ensures you never run out of hulls.",
        },
        "Aegir": {
            "timing": "All Legendary Commanders gain +2 power.",
            "synergy": "Stacks multiplicatively with Heimdall and Carter for unstoppable hero lines.",
        },
    }
LEADER_BIOS = {
    "Col. Jack O'Neill": "Career special forces officer who leads SG-1 with sarcasm and bravery; excels at turning sparse intel into decisive plays.",
    "Gen. George Hammond": "Commanding officer of the SGC whose steady leadership keeps Earth safe; focuses on disciplined deployments.",
    "Dr. Samantha Carter": "Brilliant astrophysicist and combat pilot; engineers siege solutions and tech synergies.",
    "Gen. Landry": "SGC successor after Hammond; a pragmatic strategist who values attrition victories.",
    "Dr. McKay": "Arrogant yet brilliant scientist from Atlantis, obsessed with optimizing resources.",
    "Jonas Quinn": "Kelownan diplomat turned SG-1 member with prophetic insight and encyclopedic recall.",
    "Catherine Langford": "Archaeologist who kept the Stargate program alive for decades; favors cross-faction diplomacy.",
    "Apophis": "Iconic System Lord who terrorized the galaxy through fear and ritual; masters battlefield chaos.",
    "Lord Yu": "Ancient strategist whose rigid honor code hides ruthless calculation.",
    "Sokar": "Goa'uld warlord obsessed with overwhelming front-line force and demonic theatrics.",
    "Ba'al": "Cunning clone-happy System Lord renowned for schemes within schemes.",
    "Anubis": "Half-ascended tyrant wielding forbidden Ancient tech to erase opposition.",
    "Hathor": "Seductive Goa'uld queen who manipulates foes with chemical and psychological warfare.",
    "Cronus": "Ancient System Lord who embodies disciplined militarism and slow inevitability.",
    "Teal'c": "Defector from the Goa'uld ranks and champion of the Free Jaffa; a paragon of honor.",
    "Bra'tac": "Veteran master-at-arms who mentored generations of warriors.",
    "Rak'nor": "Young commander who specializes in daring first strikes for the rebellion.",
    "Master Bra'tac": "Elder statesman of the Jaffa, orchestrating final stands with unwavering resolve.",
    "Ka'lel": "Hak'tyl warrior-poet whose battlefield speeches ignite allies.",
    "Gerak": "Political operator balancing loyalty and ambition within the Free Jaffa Nation.",
    "Ishta": "Leader of the Hak'tyl resistance, specializing in precise infiltrations.",
    "Vulkar": "Lucian Alliance spymaster who monetizes every battlefield secret.",
    "Sodan Master": "Leader of the cloaked Sodan sect, blending honor with guerrilla tactics.",
    "Ba'al Clone": "One of the countless Ba'al duplicates still chasing power in the underworld.",
    "Netan": "Crime lord who treats battlefields as trade routes to be exploited.",
    "Vala Mal Doran": "Former thief turned SG-1 ally who gambles big and usually wins.",
    "Anateo": "Lucian commander obsessed with black-market tech and battlefield triage.",
    "Kiva": "Brutal alliance general who believes shock-and-awe is the only diplomacy.",
    "Freyr": "Asgard High Councilor guarding the Protected Planets Treaty with incorruptible focus.",
    "Loki": "Renegade Asgard geneticist whose curiosity often borders on treason.",
    "Heimdall": "Asgard scientist overseeing genetic research to save his species.",
    "Thor Supreme Commander": "Defender of Earth and voice of the Asgard Fleet; master tactician with endless resolve.",
    "Hermiod": "Stoic Asgard engineer assigned to Tau'ri ships, famous for dry commentary.",
    "Penegal": "High Council member in charge of Asgard defense logistics.",
    "Aegir": "Fleet commander who orchestrated countless Asgard naval victories.",
}

FACTION_LORE = {
    "Tau'ri": {
        "lore": "Earth's SGC forces blend human ingenuity with reverse-engineered technology, relying on flexible combined-arms tactics and SG-1 heroics.",
        "strategies": "Lean on balanced rows, SG-1 alliances, and reliable medic loops to outlast opponents. Iris Defense and DHD recursion make them resilient.",
    },
    "Goa'uld": {
        "lore": "System Lords rule through fear, fielding relentless waves of Jaffa legions, Ha'tak fleets, and sinister weather manipulation.",
        "strategies": "Stack Gate Reinforcement cohorts, weaponize Naquadah Overload, and leverage Sarcophagus revival to grind foes down.",
    },
    "Jaffa Rebellion": {
        "lore": "Former slaves turned freedom fighters who rely on Brotherhood cohesion and tactical discipline.",
        "strategies": "Use Brotherhood buffs, Agile flexibility, and leadership bursts in round 3 to overwhelm larger armies.",
    },
    "Lucian Alliance": {
        "lore": "Pirates, smugglers, and mercenaries profiting from chaos across the galaxy.",
        "strategies": "Spam spies for card advantage, abuse Medical Evac mobility, and hijack neutral tech to surprise opponents.",
    },
    "Asgard": {
        "lore": "Ancient protectors wielding holograms, cloning vats, and superior battleships.",
        "strategies": "Control the board with weather immunity, clone swarms, and precise shield tricks while powering up Legendary commanders.",
    },
    "Neutral": {
        "lore": "Ancient technology, Ori zealotry, Wraith bio-ships, and other forces any faction can recruit.",
        "strategies": "Slot into any deck to cover weaknesses—be it Scorch insurance, horn bait, or extra Legendary anchors.",
    },
}

def lookup_ability_info(raw: str, ability_info: dict) -> dict:
    if not raw:
        return DEFAULT_ABILITY
    info = ability_info.get(raw)
    if info:
        return info
    for key, data in ability_info.items():
        if key and key in raw:
            return data
    return {
        "effect": f"See in-game tooltip for {raw}.",
        "timing": "Refer to ability description.",
        "synergy": "Use with faction tools that amplify this keyword.",
    }


def card_extra_abilities(name: str) -> list[str]:
    extras = []
    for predicate, ability in SPECIAL_NAME_ABILITIES:
        if predicate(name):
            extras.append(ability)
    return extras


def format_card_entry(card: dict, ability_info: dict, combo_lookup: dict, source: str) -> str:
    ability_field = card.get("ability") or ""
    ability_names = [part.strip() for part in ability_field.split(",") if part.strip()]
    ability_names.extend([extra for extra in card_extra_abilities(card["name"]) if extra not in ability_names])
    if not ability_names:
        ability_names = [""]

    effect_bits = []
    timing_bits = []
    synergy_bits = []
    for ability_name in ability_names:
        info = lookup_ability_info(ability_name, ability_info) if ability_name else DEFAULT_ABILITY
        label = ability_name or "Baseline"
        effect_bits.append(f"{label}: {info['effect']}")
        timing_bits.append(info["timing"])
        synergy_bits.append(info["synergy"])

    combos = combo_lookup.get(card["name"], [])
    combo_note = ""
    if combos:
        bundle = ", ".join(f"{c['name']} ({c['bonus']})" for c in combos)
        combo_note = f" Combo hooks: {bundle}."

    row_label = ROW_LABELS.get(card["row"], card["row"])
    card_type = ROW_TYPE_LABEL.get(card["row"], "unit")
    rarity = card.get("rarity")
    rarity_text = f" | Rarity: {rarity.title()}" if rarity else ""
    desc = card.get("description")
    desc_text = f" {desc}" if desc else ""
    stats = f"Power {card['power']} | {row_label} {card_type}{rarity_text}"
    entry = f"- **{card['name']}** ({stats}) — {ability_field or 'No keyword ability.'}{desc_text}"
    entry += f" Effects: {' '.join(effect_bits)}"
    entry += f" Timing: {' '.join(timing_bits)}"
    entry += f" Synergy: {' '.join(synergy_bits)}{combo_note}"
    entry += f" [Source: {source}; ID: {card['card_id']}]."
    return entry


def format_leader_entry(faction: str, leader: dict, tier: str, notes: dict) -> str:
    name = leader["name"]
    ability = leader.get("ability_desc") or leader.get("ability")
    extra = notes.get(name, {})
    timing = extra.get("timing", "See ability description.")
    synergy = extra.get("synergy", "Synergizes with core faction mechanics.")
    return f"- **{name}** ({tier}, {faction}) — {ability}. Timing: {timing} Synergy: {synergy}."


def format_leader_bio(name: str, faction: str, notes: dict) -> str:
    bio = LEADER_BIOS.get(name, "Lore TBD.")
    hook = notes.get(name, {}).get("synergy", "Compliments faction gameplan.")
    return f"- **{name}** ({faction}) — {bio} Playstyle tip: {hook}"

def build_spec() -> str:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    combos, combo_lookup = build_combo_lookup()
    ability_info = build_ability_info()
    leader_notes = build_leader_notes()

    card_catalog = load_json(CARD_CATALOG_PATH)
    leader_catalog = load_json(LEADER_CATALOG_PATH)
    unlock_data = parse_assign_dict(UNLOCKS_PATH.read_text(), "UNLOCKABLE_CARDS")

    unlock_entries = []
    for card_id, data in unlock_data.items():
        unlock_entries.append({
            "card_id": card_id,
            "name": data["name"],
            "faction": data["faction"],
            "power": data["power"],
            "row": data["row"],
            "ability": data.get("ability"),
            "rarity": data.get("rarity"),
            "description": data.get("description"),
        })
    unlock_by_faction = defaultdict(list)
    for card in unlock_entries:
        unlock_by_faction[card["faction"]].append(card)
    for items in unlock_by_faction.values():
        items.sort(key=lambda c: (-c["power"], c["name"]))

    parts: list[str] = []
    parts.append(f"# Stargwent Rule Menu UI Specification\n\nGenerated on {now} using cards.py, content_registry.py, unlocks.py, game.py, and README.md. Covers {sum(len(v) for v in card_catalog.values())} core cards + {len(unlock_entries)} unlockables + 35 leaders.")

    parts.append(dedent(
        """
        ## UI Overview
        - Accessible from the Main Menu via the new `RULE MENU` option; loads instantly without blocking gameplay assets.
        - Layout: 10-tab horizontal ribbon (Basic Rules → Lore) anchored to the top 120px of the viewport. Active tab glows faction blue with a Stargate chevron indicator.
        - Left rail (420px) hosts search, filters, and a collapsible outline for the current tab. Right content panel scrolls independently.
        - Inputs: Mouse wheel/trackpad scroll vertical content; Q/E or LB/RB cycle tabs; Arrow/Page keys scroll; `F` focuses the search box on tabs with lists; `ESC` backs out to Main Menu.
        - Scroll Feedback: Persistent scrollbar plus “Page X/Y” breadcrumb for long chapters (Card Glossary and Lore tabs paginate by faction subsections).
        - Content uses a responsive grid: three columns on desktop, collapsing to a single column under 1600px width.
        """
    ))

    parts.append(dedent(
        """
        ## Tab Directory & Behaviors
        1. Basic Rules – onboarding, objectives, deck requirements, controls, DHD/Iris primer.
        2. Turn Structure – mulligan timing, action economy, scoring, pass/round logic.
        3. Card Types & Rarity – rows, specials, weather, hero tags, rarity color codes.
        4. Faction Abilities – passive traits, once-per-game Faction Powers, unique mechanics.
        5. Leader Cards & Abilities – mechanical reference for all 35 leaders (base + unlock).
        6. Unit Abilities A–Z – glossary of every keyword from Tactical Formation to Wormhole Stabilization.
        7. Special Cards – detailed behavior for weather, Command Network, Naquadah Overload, artifacts, combo systems.
        8. Status Effects – explanation of weather slots, horn slots, hand reveals, Ka'lel/Hammond flags, DHD state, Iris readiness.
        9. Full Card Glossary – exhaustive card list per faction plus unlockables with stats/effects/synergy.
        10. Faction Lore & Leader Bios – narrative flavor, strategic archetypes, and biographies.
        """
    ))

    parts.append(dedent(
        """
        ## Tab 1 – Basic Rules
        **Layout:** Two-column grid: left column covers Objective, Setup, and Turn Basics; right column highlights Deck Building, Progression, and Controls. Sticky infographic at top depicts the 3-round win condition.

        - **Objective:** Win 2 of 3 rounds by ending a round with more total power. Ties award both players a round win.
        - **Setup:** 10-card starting hand, 2–5 card mulligan, random coin flip determines first player. Deck size 20–40 with at least 15 units; faction decks may include Neutral plus unlocked tech. Custom decks saved in `player_decks.json`.
        - **Resource Systems:** No mana—power is entirely card-driven. Iris Defense is a one-shot shield that destroys the opponent's next card; Dial Home Device (DHD) retrieves one random non-Hero unit per round from discard if unused.
        - **Progression:** Winning any match unlocks one of three random cards (weighted to your faction/Neutral). Three consecutive wins unlock one of three faction leaders. Unlock state stored in `player_unlocks.json`.
        - **Controls Recap:** Drag/drop to play, right-click to inspect, SPACE to trigger Faction Power (once per game), ESC to pause, D to view discard, mouse wheel to scroll panels.
        - **Battlefield Cues:** Weather slots on the left show hazards affecting rows; horn slots highlight Command Network placement; discard, artifact, and history panels remain clickable from this tab to reinforce UI literacy.
        """
    ))

    parts.append(dedent(
        """
        ## Tab 2 – Turn Structure
        **Layout:** Timeline ribbon illustrating phases (Mulligan → Round Start → Player Turns → Pass → Round End → Victory). Below the ribbon, expandable accordions explain each phase in detail with clarifications for leader overrides.

        - **Mulligan:** Redraw 2–5 cards before round 1; AI mulligans 2–4 automatically. Deck shuffles after mulligan resolves.
        - **Round Start:** Draw 2 cards at the beginning of rounds 2 and 3. Tau'ri Resourcefulness and Jack O'Neill add one more draw here. DHD and Iris reset availability.
        - **Player Turn:** Default action economy is 1 card per turn. Rak'nor may play two cards on his first turn each round; Ka'lel buffs the first three units per round; Gerak draws after every second unit. If the opponent's Iris is active, your first card is destroyed on contact.
        - **Playing Cards:** Validate row (Agile cards can enter close or ranged). Weather cards target rows directly; specials like Command Network and Ring Transport open contextual UI. Deep Cover Agents auto-place on the opponent's board and immediately draw cards.
        - **Leader Triggers:** Hammond and Ka'lel mark boosts as cards resolve; Loki siphons power from the strongest enemy each time you deploy; Lord Yu flags opponent hand reveal for the following round; McKay draws when you pass.
        - **Pass & Round End:** Press the DHD to pass. Once both players pass, scores lock, round winner recorded, board wipes to discard, horns/weather cleared, leader boost flags removed. Master Bra'tac, Cronus, and Anubis have round-based effects that trigger here.
        - **Victory:** First to 2 round wins claims the match. Unlock checks fire from `deck_persistence.py` immediately afterward.
        """
    ))

    parts.append(dedent(
        """
        ## Tab 3 – Card Types & Rarity
        **Layout:** Icon grid showcasing each card frame (Close/Ranged/Siege/Agile/Weather/Special) alongside rarity swatches. Includes tooltip callouts for Legendary commanders and token cards.

        - **Unit Rows:** Close (melee), Ranged, Siege, and Agile (may occupy close or ranged). Agile cards inherit row bonuses from whichever lane they occupy when scores are evaluated.
        - **Special Cards:** One-shot effects such as Command Network (horn), Naquadah Overload (Scorch), Medical Evac (revive), Ring Transport (recall). They occupy the special row in decks and resolve immediately.
        - **Weather Cards:** Ice Planet Hazard (close), Nebula Interference (ranged), Asteroid Storm (siege), Electromagnetic Pulse (any row). Wormhole Stabilization clears all hazards. Weather reduces non-Hero units to 1 power unless they have Survival Instinct; Hermiod and Freyr modify targeting.
        - **Legendary Commanders:** Immune to most removal, cannot be doubled by horns, ignore weather/scorch, and power leader synergy (Heimdall/Aegir). Identified by golden frames.
        - **Tokens:** Shield Maidens (2 power) and Asgard Avengers (5 power) spawned by Deploy Clones/Activate Combat Protocol inherit faction tags but are not part of your deck list.
        - **Rarity Palette:** Commons (silver), Rare (blue), Epic (purple), Legendary (gold). Base decks mostly common/rare, while unlockables include epics and legendaries like Atlantis City or Dakara Superweapon.
        """
    ))

    parts.append(dedent(
        """
        ## Tab 4 – Faction Abilities & Powers
        **Layout:** Five accordion cards (one per faction) showing Passive Ability, Faction Power, Unique Mechanics, and an Example Strategy vignette. Icons for once-per-game powers sit beside descriptions to mirror in-game HUD placement.
        """
    ))

    faction_details = {
        "Tau'ri": {
            "passive": "Resourcefulness – draw 1 extra card at the start of rounds 2 and 3.",
            "power": "The Gate Shutdown – destroy the highest-power enemy unit in each row (once per game).",
            "unique": "Tau'ri Iris Defense (one-shot shield) and Dial Home Device recursion every round.",
        },
        "Goa'uld": {
            "passive": "System Lord's Command – non-Hero units gain +1 when you control any Hero.",
            "power": "Sarcophagus Revival – revive two random non-Hero units from your discard pile.",
            "unique": "Goa'uld Ring Transportation (return a close unit to hand once per round) and Apophis weather decree.",
        },
        "Jaffa Rebellion": {
            "passive": "Brotherhood – each unit gains +1 per other unit in its row (max +3).",
            "power": "Rebel Alliance Aid – draw 3 cards, then discard 3 random cards (once per game).",
            "unique": "Hak'tyl leadership trackers for Ka'lel/Gerak and strong Agile presence.",
        },
        "Lucian Alliance": {
            "passive": "Piracy – first spy each round draws 3 cards instead of 2.",
            "power": "Unstable Naquadah – deal 5 damage to every non-Hero unit (both sides).",
            "unique": "Black-market Medical Evac (Anateo), smuggling random Neutral cards (Netan), heavy spy economy.",
        },
        "Asgard": {
            "passive": "Superior Shielding – immune to the first enemy weather each round.",
            "power": "Holographic Decoy – swap the opponent's close and ranged rows once per game.",
            "unique": "Clone vats (Deploy Clones), Genetic Enhancement, beam transports, weather immunity stacks with Freyr/Hermiod.",
        },
        "Neutral": {
            "passive": "Varies – see card entries.",
            "power": "N/A",
            "unique": "Neutral tech is accessible to all factions via unlocks and Langford's ability.",
        },
    }

    for faction in FACTION_ORDER:
        if faction not in faction_details:
            continue
        data = faction_details[faction]
        strategy = FACTION_LORE.get(faction, {}).get("strategies", "")
        parts.append(f"- **{faction}**\n  - Passive: {data['passive']}\n  - Faction Power: {data['power']}\n  - Unique Mechanics: {data['unique']}\n  - Example Strategy: {strategy}")
    parts.append(dedent(
        """
        ## Tab 5 – Leader Cards & Abilities
        **Layout:** Sub-tabs for each faction (Tau'ri → Asgard). Each sub-tab splits leaders into Base and Unlockable columns with portrait thumbnails, ability text, timing clarifications, and synergy callouts. Hovering a leader highlights related cards in the glossary.
        """
    ))

    for faction in FACTION_ORDER:
        if faction not in leader_catalog:
            continue
        parts.append(f"### {faction} Leaders")
        base_leaders = leader_catalog[faction].get("base", [])
        unlockable_leaders = leader_catalog[faction].get("unlockable", [])
        if base_leaders:
            parts.append("**Base Roster**")
            for leader in base_leaders:
                parts.append(format_leader_entry(faction, leader, "Base", leader_notes))
        if unlockable_leaders:
            parts.append("**Unlockable Roster**")
            for leader in unlockable_leaders:
                parts.append(format_leader_entry(faction, leader, "Unlockable", leader_notes))

    parts.append(dedent(
        """
        ## Tab 6 – Unit Abilities (Alphabetical)
        **Layout:** Searchable list with alphabet chips (A–Z). Selecting an ability filters the card glossary simultaneously. Each row shows Effect, Timing, Synergy columns backed directly by code logic.
        """
    ))

    for ability_name in sorted(ability_info):
        info = ability_info[ability_name]
        parts.append(f"- **{ability_name}** – Effect: {info['effect']} Timing: {info['timing']} Synergy: {info['synergy']}")
    parts.append("- **Baseline** – Effect: No keyword ability; rely on stats. Timing: Always on. Synergy: Perfect horn/buff fodder.")

    parts.append(dedent(
        """
        ## Tab 7 – Special Cards, Weather, Horns & Combos
        **Layout:** Carousel of card vignettes (Command Network, Naquadah Overload, Wormhole Stabilization, weather hazards, artifacts). Each slide includes iconography, targeting rules, and UI prompts. Secondary panel lists Alliance Combos and Artifact behaviors.

        - **Command Network (Horn):** Drag onto any row to double non-Hero power there. Horn slot indicator glows blue for player, red for AI.
        - **Naquadah Overload (Scorch variants):** Default version nukes the highest-power non-Hero units globally; Merlin's Weapon targets opponents only; Ancient Drone variant hits the lowest-power enemy.
        - **Ring Transport:** Opens target selector; blue outline = friendly, red = enemy. Returning an enemy unit places it in your hand for future turns.
        - **Medical Evac:** Highlights all non-Hero cards in discard; click to revive into its native row (Agile defaults to Close).
        - **Weather Cards:** Drag hazard onto desired row; affected sides indicated in the weather panel text (Player, Opponent, Both). Wormhole Stabilization clears all hazards and plays a black-hole animation.
        - **Artifacts:**
          - Ancient Control Chair – +2 to all friendly Neutral units in play.
          - Communication Stones – draws 1 card whenever the opponent passes.
          - Asgard Beam Array – lowers Scorch threshold to 8 power (handled inside Naquadah Overload logic).
        - **Alliance Combos:**
        """
    ))

    for combo in combos:
        summary = f"  - **{combo['name']}** – Members: {', '.join(combo['members'])}. Bonus: {combo['bonus']}. {combo['description']}"
        parts.append(summary)

    parts.append(dedent(
        """
        - **Apophis Weather Decree:** Leader ability duplicates a random weather card (Ice Planet, Nebula, Asteroid, or EMP) and applies it to both sides while respecting Freyr/Hermiod rules.
        - **Ring Transportation (Goa'uld mechanic):** Once per round you may target a friendly close-combat unit and beam it back to your hand; animation lasts 4 seconds with five concentric rings.
        """
    ))

    parts.append(dedent(
        """
        ## Tab 8 – Status Effects & Board Indicators
        **Layout:** HUD mock-up labeling every persistent indicator. Each effect entry explains its icon, duration, clearing condition, and related buttons/hotkeys.

        - **Weather Slots:** Three panels on the left display the card art, owner icon, and which side(s) are affected. Clicking shows tooltip from this spec.
        - **Command Horn Slots:** Mirrored on the right; glowing rim indicates whether the horn doubles player or opponent. Destroy horn by Scorching or clearing the row.
        - **Iris Defense:** Tau'ri DHD button pulses blue when available, gray when spent. Text clarifies it destroys the opponent's next played card automatically.
        - **Dial Home Device:** Once per round, glows amber when ready. Hover tooltip shows whether a valid discard target exists.
        - **Faction Power Meter:** Golden border = ready, gray = spent. Hotkey reminder (SPACE) shown below.
        - **Hand Reveal:** Eye icon over a leader portrait signals the opponent's hand is exposed (Lord Yu, Communication Device, Sodan recon). Fades at round end.
        - **Leader Flags:** Small glyphs track Ka'lel (+2 queued), Hammond (+3 on first unit), Cronus round number. Clearing a round wipes the glyph.
        - **Spy Indicator:** Deep Cover Agents gain a purple spy icon and are listed under opponent control in history logs despite being yours.
        - **Alliance Combo Tracker:** When a combo is one card away, HUD chips light up to encourage completion; completing a combo adds a temporary badge to card frames.
        """
    ))

    parts.append(dedent(
        """
        ## Tab 9 – Full Card Glossary
        **Layout:** Mega-tab with faction filter chips across the top and a persistent search box (supports name, ability, row, or ID queries). Each faction page shows Core Deck cards first, then Unlockables, each in collapsible sections. Entries reference this spec so hovering them elsewhere can deep-link into the glossary.
        """
    ))

    for faction in FACTION_ORDER:
        core_cards = card_catalog.get(faction)
        unlock_cards = unlock_by_faction.get(faction)
        if not core_cards and not unlock_cards:
            continue
        parts.append(f"### {faction}")
        if core_cards:
            parts.append("**Core Deck**")
            for card in core_cards:
                parts.append(format_card_entry(card, ability_info, combo_lookup, "Core Deck"))
        if unlock_cards:
            parts.append("**Unlockable Collection**")
            for card in unlock_cards:
                parts.append(format_card_entry(card, ability_info, combo_lookup, "Unlockable"))

    parts.append(dedent(
        """
        ## Tab 10 – Faction Lore & Leader Bios
        **Layout:** Storybook presentation with faction splash art followed by expandable leader dossiers. Each dossier includes biography, notable episodes, and a recommended strategy tip derived from ability notes.
        """
    ))

    for faction in FACTION_ORDER:
        if faction not in FACTION_LORE:
            continue
        parts.append(f"### {faction}")
        parts.append(f"- Lore: {FACTION_LORE[faction]['lore']}")
        parts.append(f"- Signature Strategy: {FACTION_LORE[faction]['strategies']}")
        leaders = leader_catalog.get(faction, {})
        leader_lines = []
        for bucket in ("base", "unlockable"):
            for leader in leaders.get(bucket, []):
                leader_lines.append(format_leader_bio(leader["name"], faction, leader_notes))
        if leader_lines:
            parts.append("- Leader Bios:")
            parts.extend([f"  {line}" for line in leader_lines])

    return "\n".join(parts) + "\n"

def main():
    spec_text = build_spec()
    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPEC_PATH.write_text(spec_text)
    print(f"Wrote {SPEC_PATH.relative_to(ROOT)} ({len(spec_text)} characters)")


if __name__ == "__main__":
    main()
