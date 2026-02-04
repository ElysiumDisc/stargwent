"""
Interactive rule compendium viewer for Stargwent.
Provides tabbed navigation, faction/leader browsers, searchable ability glossary,
and card filtering backed by docs/rules_menu_spec.md plus generated JSON data.
"""

from __future__ import annotations

import json
import string
from dataclasses import dataclass, field
import math
from pathlib import Path
from textwrap import wrap
from typing import Dict, List, Optional, Tuple

import pygame

SPEC_PATH = Path("docs") / "rules_menu_spec.md"
CARD_JSON = Path("docs") / "card_catalog.json"
LEADER_JSON = Path("docs") / "leader_catalog.json"

TAB_BEHAVIOR = {
    "Tab 1 – Basic Rules": "text",
    "Tab 2 – Turn Structure": "text",
    "Tab 3 – Card Types & Rarity": "text",
    "Tab 4 – Faction Abilities & Powers": "faction",
    "Tab 5 – Leader Cards & Abilities": "leaders",
    "Tab 6 – Unit Abilities (Alphabetical)": "abilities",
    "Tab 7 – Special Cards, Weather, Horns & Combos": "text",
    "Tab 8 – Status Effects & Board Indicators": "text",
    "Tab 9 – Full Card Glossary": "cards",
    "Tab 10 – Faction Lore & Leader Bios": "lore",
}

FACTION_DISPLAY = [
    "Tau'ri",
    "Goa'uld",
    "Jaffa Rebellion",
    "Lucian Alliance",
    "Asgard",
    "Neutral",
]

LEADER_NOTES = {
    "Col. Jack O'Neill": {
        "timing": "Summons a 6-power Jack clone at the start of every round; each clone self-destructs after three of your turns.",
        "synergy": "Use the temporary body to soak weather, horn lanes, or combo with Gate Reinforcement spikes.",
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
        "timing": "Draws 2 cards immediately when you pass a round.",
        "synergy": "Perfect for tempo-pass strategies that bank cards for later rounds.",
    },
    "Jonas Quinn": {
        "timing": "Peeks at the next card your opponent will play.",
        "synergy": "Use intel to time Iris Defense and Command Network counters.",
    },
    "Catherine Langford": {
        "timing": "Once per game: Click portrait to reveal top 3 cards, play one immediately.",
        "synergy": "Save for critical moments when you need specific card types or weather clears.",
    },
    "Apophis": {
        "timing": "Once per game unleashes a random weather hazard respecting immunities.",
        "synergy": "Combine with Hermiod or Asgard Beam artifact for unilateral storms.",
    },
    "Lord Yu": {
        "timing": "When you pass, the opponent's next-round hand is revealed.",
        "synergy": "Pairs with Deep Cover Agents and Sodan scouts for relentless intel.",
    },
    "Sokar": {
        "timing": "All close combat units gain +1 during score calculation.",
        "synergy": "Best with Horus Guard drains and horned frontline pushes.",
    },
    "Ba'al": {
        "timing": "At each round start clones your highest-power unit.",
        "synergy": "Duplicate Legendary ships or huge Ha'tak stacks for inevitability.",
    },
    "Anubis": {
        "timing": "Automatically fires Naquadah Overload at the start of rounds 2 and 3.",
        "synergy": "Preserve Heroes/Survival units so you profit while opponents burn.",
    },
    "Hathor": {
        "timing": "Steals the opponent's lowest-power unit at round start.",
        "synergy": "Disrupts swarm decks and feeds Lucian horn lanes.",
    },
    "Cronus": {
        "timing": "All units gain +1/+2/+3 based on round number.",
        "synergy": "Gate Reinforcement waves scale dramatically across the match.",
    },
    "Teal'c": {
        "timing": "Draw 1 card every time you win a round.",
        "synergy": "Keeps Free Jaffa ahead on cards even in grindy matches.",
    },
    "Bra'tac": {
        "timing": "All Agile cards get +1 power.",
        "synergy": "Encourages flexible row deployments and Ka'lel synergies.",
    },
    "Rak'nor": {
        "timing": "First turn of every round you may play two cards.",
        "synergy": "Explosive openings for Brotherhood or horn setups.",
    },
    "Master Bra'tac": {
        "timing": "All friendly units gain +3 power in round 3.",
        "synergy": "Sandbag earlier rounds and unleash unstoppable final pushes.",
    },
    "Ka'lel": {
        "timing": "First three units each round gain +2 power.",
        "synergy": "Buff spy drops or Gate Reinforcement runs immediately.",
    },
    "Gerak": {
        "timing": "Draw 1 card after every second unit you play.",
        "synergy": "Rewards wide deployments and keeps hand size healthy.",
    },
    "Ishta": {
        "timing": "All Gate Reinforcement units gain +2 power.",
        "synergy": "Turns even 1-power militia into meaningful threats.",
    },
    "Vulkar": {
        "timing": "Spy cards draw 3 instead of 2.",
        "synergy": "Lucian Piracy passive plus Vulkar churns through decks instantly.",
    },
    "Sodan Master": {
        "timing": "Highest-power unit in each row gains +3.",
        "synergy": "Protects tall strategies and punishes weather attempts to shave peaks.",
    },
    "Ba'al Clone": {
        "timing": "All ranged units gain +2 power.",
        "synergy": "Great with snipers and Tok'ra operatives for safe pressure.",
    },
    "Netan": {
        "timing": "Generates a random Neutral card at the start of each round.",
        "synergy": "Smuggling midgame tech keeps opponents guessing.",
    },
    "Vala Mal Doran": {
        "timing": "Once per game look at the top 3 cards of your deck and keep one.",
        "synergy": "Tutor Command Network or Scorch answers on demand.",
    },
    "Anateo": {
        "timing": "Can use Medical Evac once per round without a medic card.",
        "synergy": "Sustain Lucian tempo while looping high-impact units.",
    },
    "Kiva": {
        "timing": "Play two cards on your very first turn of the game.",
        "synergy": "Great for early horn setups or double-spy gambits.",
    },
    "Freyr": {
        "timing": "Your side is completely immune to weather effects.",
        "synergy": "Weaponize hazards guilt-free while enemy lanes crumble.",
    },
    "Loki": {
        "timing": "Every time you play a unit, steal 1 power from the opponent's strongest non-Hero.",
        "synergy": "Snowballs power advantage and punishes tall enemy builds.",
    },
    "Heimdall": {
        "timing": "All Legendary Commanders gain +3 power.",
        "synergy": "Turns every hero into a must-answer finisher.",
    },
    "Thor Supreme Commander": {
        "timing": "Once per round you may move any unit to a different valid row.",
        "synergy": "Dodge weather, re-trigger Tactical Formation, or steal horn lanes.",
    },
    "Hermiod": {
        "timing": "Any weather you play only affects your opponent.",
        "synergy": "Combine with Apophis or Asgard beams for unilateral board control.",
    },
    "Penegal": {
        "timing": "Revives one random unit from discard at the start of rounds 2 and 3.",
        "synergy": "Fuels attrition plans and keeps siege lines staffed.",
    },
    "Aegir": {
        "timing": "All Legendary Commanders gain +2 power.",
        "synergy": "Stacks multiplicatively with Heimdall and Carter bonuses.",
    },
}

BASE_FRAME_SIZE = (3840, 2160)
GATE_CENTER = (1887, 1005)
GATE_RADIUS = 455
LEFT_PANEL_RECTS = {
    "upper": (216, 466, 559, 360),
    "lower": (216, 865, 559, 360),
    "stack": (216, 1268, 441, 640),
}
RIGHT_STACK_RECTS = [
    (3231, 520, 332, 170),
    (3231, 730, 332, 170),
    (3231, 940, 332, 170),
    (3231, 1150, 332, 170),
    (3231, 1360, 332, 170),
    (3231, 1570, 332, 170),
]
STATUS_BAR_RECT = (1200, 1800, 1400, 285)
CHEVRON_POLYGONS = [
    [
        (1178, 929),
        (1180, 915),
        (1201, 783),
        (1202, 779),
        (1203, 778),
        (1204, 778),
        (1217, 784),
        (1221, 786),
        (1292, 823),
        (1318, 837),
        (1326, 842),
        (1329, 845),
        (1329, 847),
        (1327, 860),
        (1320, 902),
        (1319, 907),
        (1318, 909),
        (1316, 911),
        (1312, 912),
        (1296, 915),
    ],
    [
        (2441, 843),
        (2445, 840),
        (2455, 834),
        (2464, 829),
        (2475, 823),
        (2553, 781),
        (2563, 776),
        (2564, 776),
        (2565, 777),
        (2566, 780),
        (2569, 795),
        (2591, 922),
        (2592, 929),
        (2592, 930),
        (2591, 931),
        (2586, 931),
        (2553, 926),
        (2474, 914),
        (2461, 912),
        (2456, 911),
    ],
    [
        (2371, 1322),
        (2372, 1319),
        (2373, 1317),
        (2379, 1307),
        (2384, 1299),
        (2396, 1280),
        (2406, 1265),
        (2407, 1264),
        (2410, 1264),
        (2480, 1281),
        (2544, 1297),
        (2544, 1299),
        (2542, 1303),
        (2539, 1308),
        (2469, 1420),
        (2462, 1430),
        (2460, 1430),
        (2457, 1427),
        (2449, 1418),
        (2410, 1371),
    ],
    [
        (1356, 522),
        (1357, 520),
        (1366, 512),
        (1468, 429),
        (1473, 425),
        (1476, 423),
        (1477, 423),
        (1478, 424),
        (1481, 430),
        (1498, 475),
        (1521, 536),
        (1524, 544),
        (1527, 553),
        (1527, 555),
        (1526, 557),
        (1525, 558),
        (1513, 568),
        (1484, 592),
        (1479, 596),
        (1477, 597),
    ],
    [
        (1814, 293),
        (1821, 292),
        (1962, 292),
        (1971, 293),
        (1972, 294),
        (1968, 307),
        (1953, 352),
        (1933, 411),
        (1929, 422),
        (1927, 426),
        (1925, 428),
        (1860, 428),
        (1858, 426),
        (1857, 424),
        (1852, 410),
        (1845, 390),
        (1844, 387),
        (1818, 308),
        (1815, 298),
        (1814, 294),
    ],
    [
        (2241, 552),
        (2242, 549),
        (2246, 539),
        (2273, 473),
        (2292, 427),
        (2293, 425),
        (2295, 423),
        (2297, 424),
        (2303, 429),
        (2399, 512),
        (2409, 521),
        (2413, 525),
        (2409, 529),
        (2406, 531),
        (2297, 596),
        (2295, 597),
        (2292, 598),
        (2291, 598),
        (2287, 595),
        (2281, 590),
    ],
    [
        (1233, 1287),
        (1234, 1286),
        (1238, 1285),
        (1276, 1278),
        (1287, 1276),
        (1370, 1261),
        (1371, 1261),
        (1373, 1263),
        (1375, 1266),
        (1380, 1275),
        (1386, 1286),
        (1401, 1314),
        (1404, 1320),
        (1404, 1322),
        (1401, 1326),
        (1320, 1412),
        (1308, 1424),
        (1306, 1424),
        (1304, 1421),
        (1299, 1412),
    ],
]
SCANLINE_SPACING = 6

# Chevron tab assignments - thematic groupings with labels
# Each chevron controls related content sections
CHEVRON_CONFIG = [
    {"label": "RULES", "tabs": [0, 1]},      # Tab 1: Basic Rules, Tab 2: Turn Structure
    {"label": "CARDS", "tabs": [2, 8]},      # Tab 3: Card Types, Tab 9: Card Glossary
    {"label": "FACTIONS", "tabs": [3, 9]},   # Tab 4: Faction Abilities, Tab 10: Faction Lore
    {"label": "LEADERS", "tabs": [4]},       # Tab 5: Leader Cards & Abilities
    {"label": "ABILITIES", "tabs": [5]},     # Tab 6: Unit Abilities
    {"label": "SPECIAL", "tabs": [6]},       # Tab 7: Special Cards, Weather, Horns
    {"label": "STATUS", "tabs": [7]},        # Tab 8: Status Effects
]


@dataclass
class SpecNode:
    title: str
    level: int
    content: List[str] = field(default_factory=list)
    children: List["SpecNode"] = field(default_factory=list)


class SpecParser:
    """Parses markdown into a tree of headings and content."""

    def __init__(self, text: str):
        self.root = SpecNode("root", 0)
        self._parse(text.splitlines())

    def _parse(self, lines: List[str]):
        stack = [self.root]
        for raw in lines:
            if not raw.strip():
                stack[-1].content.append("")
                continue
            stripped = raw.lstrip()
            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                title = stripped[level:].strip()
                node = SpecNode(title, level)
                while stack and stack[-1].level >= level:
                    stack.pop()
                stack[-1].children.append(node)
                stack.append(node)
            else:
                stack[-1].content.append(raw.rstrip("\n"))

    def find_tabs(self) -> List[SpecNode]:
        tabs: List[SpecNode] = []

        def visit(node: SpecNode):
            if node.title in TAB_BEHAVIOR and node is not self.root:
                tabs.append(node)
            for child in node.children:
                visit(child)

        for child in self.root.children:
            visit(child)
        return tabs


class RulesMenuScreen:
    """Interactive HUD for browsing the Stargwent rulebook."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.bg_color = (2, 5, 12)
        self.text_color = (192, 255, 249)
        self.muted_color = (90, 150, 170)
        self.accent_color = (72, 220, 255)
        self.deep_accent = (0, 160, 210)
        self.chevron_color = (255, 90, 90)
        self.warning_color = (255, 120, 120)
        self.shadow_color = (5, 20, 35)
        base_title = pygame.font.SysFont("BankGothic Md BT, Orbitron, Eurostile, Arial", 48)
        base_body = pygame.font.SysFont("Eurostile, Orbitron, Arial", 24)
        base_small = pygame.font.SysFont("Eurostile, Orbitron, Arial", 18)
        base_mono = pygame.font.SysFont("Consolas, Menlo, Courier", 18)
        self.title_font = base_title
        self.body_font = base_body
        self.small_font = base_small
        self.mono_font = base_mono

        self.spec = self._load_spec()
        self.tabs = self.spec.find_tabs()
        if not self.tabs:
            fallback = SpecNode("Rule Menu", 1, ["Specification missing. Run scripts/generate_rules_spec.py."])
            self.tabs = [fallback]
            TAB_BEHAVIOR.setdefault("Rule Menu", "text")
        self.tab_titles = [tab.title for tab in self.tabs]
        self.active_tab = 0

        self.card_data = self._parse_card_entries()
        self.faction_cards = self._parse_faction_cards()
        self.ability_entries = self._parse_abilities()
        self.general_sections = self._build_general_sections()
        self.lore_entries = self._parse_lore_entries()
        self.leader_data = self._load_leader_data()
        self.leader_images = self._load_leader_portraits()
        self.card_images = self._load_card_images()
        self.background_image = self._load_background()
        self.background_scaled: Optional[pygame.Surface] = None

        # Dynamic HUD geometry (filled in by _refresh_layout)
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.left_panels: Dict[str, pygame.Rect] = {}
        self.right_slots: List[pygame.Rect] = []
        self.bottom_status_rect = pygame.Rect(0, 0, 0, 0)
        self.viewport_rect = pygame.Rect(0, 0, 0, 0)
        self.viewport_mask: Optional[pygame.Surface] = None
        self.scanline_surface: Optional[pygame.Surface] = None
        self.chevron_slots: List[Dict] = []

        # UI state
        self.scroll_offsets: Dict[int, float] = {}
        self.hit_regions: List[Dict] = []
        self.active_input: Optional[Tuple[str, str]] = None
        self.active_faction = FACTION_DISPLAY[0]
        self.leader_faction = FACTION_DISPLAY[0]
        self.leader_category = "base"
        self.leader_selected: Optional[Dict] = None
        self.leader_page_offset = 0
        self.ability_search = ""
        self.ability_letter = "All"
        self.card_faction = FACTION_DISPLAY[0]
        self.card_section = "Core Deck"
        self.card_search = ""
        self.card_selected: Optional[Dict] = None
        self.card_list_offset = 0
        self.lore_faction = FACTION_DISPLAY[0]
        self.status_message = "IDLE"
        
        # Navigation
        self.should_exit = False
        self.back_button_rect = pygame.Rect(0, 0, 0, 0)
        
        initial_sections = list(self.card_data.get(self.card_faction, {}).keys())
        if initial_sections:
            self.card_section = initial_sections[0]
        self._refresh_layout()

    # ---------- Data parsing ----------

    def _load_spec(self) -> SpecParser:
        if SPEC_PATH.exists():
            return SpecParser(SPEC_PATH.read_text(encoding="utf-8"))
        placeholder = "## Tab 1 – Basic Rules\n- Spec file missing. Run scripts/generate_rules_spec.py."
        return SpecParser(placeholder)

    def _build_general_sections(self) -> Dict[str, Dict]:
        sections = {}
        for tab in self.tabs:
            behavior = TAB_BEHAVIOR.get(tab.title, "text")
            if behavior == "text":
                overview, items = self._parse_text_tab(tab)
                sections[tab.title] = {"overview": overview, "items": items}
        return sections

    def _parse_text_tab(self, node: SpecNode) -> Tuple[List[str], List[Dict[str, str]]]:
        overview: List[str] = []
        items: List[Dict[str, str]] = []
        for line in node.content:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                entry = stripped[2:].strip()
                title, body = self._split_bullet(entry)
                items.append({"title": title, "body": body})
            elif not stripped.startswith("#"):
                overview.append(stripped.replace("**", ""))
        # include child sections as additional cards
        for child in node.children:
            text = " ".join(t.strip() for t in child.content if t.strip())
            if text:
                items.append({"title": child.title.replace("###", "").strip(), "body": text})
        return overview, items

    def _parse_faction_cards(self) -> List[Dict[str, str]]:
        tab = self._get_tab("Tab 4 – Faction Abilities & Powers")
        factions: List[Dict[str, str]] = []
        current: Optional[Dict[str, str]] = None
        for raw in tab.content:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("- **") and stripped.endswith("**"):
                name = stripped[4:-2]
                current = {"name": name, "Passive": "", "Power": "", "Unique": "", "Strategy": "", "Strategy Tips": ""}
                factions.append(current)
            elif stripped.startswith("- "):
                key, val = self._split_bullet(stripped[2:].strip())
                # Map various key formats to our expected fields
                if current:
                    if key in current:
                        current[key] = val
                    elif key == "Faction Power":
                        current["Power"] = val
                    elif key == "Unique Mechanics":
                        current["Unique"] = val
                    elif key == "Strategy Tips":
                        current["Strategy Tips"] = val
                    elif key == "Example Strategy":
                        current["Strategy"] = val
            elif stripped.startswith("-"):
                # nested entries already handled
                continue
            elif stripped.startswith("  - "):
                label, val = self._split_bullet(stripped[4:].strip())
                if current:
                    if label in current:
                        current[label] = val
                    elif label == "Faction Power":
                        current["Power"] = val
                    elif label == "Unique Mechanics":
                        current["Unique"] = val
                    elif label == "Strategy Tips":
                        current["Strategy Tips"] = val
        return factions

    def _parse_abilities(self) -> List[Dict[str, str]]:
        tab = self._get_tab("Tab 6 – Unit Abilities (Alphabetical)")
        abilities: List[Dict[str, str]] = []
        for line in tab.content:
            stripped = line.strip()
            if stripped.startswith("- **"):
                name_end = stripped.find("**", 3)
                name = stripped[4:name_end]
                remainder = stripped[name_end + 2:].strip(" –")
                parts = remainder.split("Timing:")
                effect_part = parts[0].strip()
                timing_part = ""
                synergy_part = ""
                if len(parts) > 1:
                    timing_and_synergy = parts[1].split("Synergy:")
                    timing_part = timing_and_synergy[0].strip()
                    if len(timing_and_synergy) > 1:
                        synergy_part = timing_and_synergy[1].strip()
                abilities.append(
                    {
                        "name": name,
                        "effect": effect_part.replace("Effects:", "").strip(),
                        "timing": timing_part,
                        "synergy": synergy_part,
                    }
                )
        return abilities

    def _parse_card_entries(self) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        tab = self._get_tab("Tab 9 – Full Card Glossary")
        entries: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        for faction_node in tab.children:
            faction = faction_node.title.replace("###", "").strip()
            entries[faction] = {}
            current_section = None
            for line in faction_node.content:
                stripped = line.strip()
                if stripped.startswith("**") and stripped.endswith("**"):
                    section = stripped.strip("*")
                    entries[faction][section] = []
                    current_section = section
                elif stripped.startswith("- **") and current_section:
                    name_end = stripped.find("**", 3)
                    name = stripped[4:name_end]
                    body = stripped[name_end + 2 :].strip(" —")
                    card_id = self._extract_card_id(body)
                    entries[faction][current_section].append({"name": name, "body": body, "card_id": card_id})
        return entries

    def _load_background(self) -> Optional[pygame.Surface]:
        # Try specific rule menu bg first
        bg_path = Path("assets") / "rule_menu_bg.png"
        if bg_path.exists():
            try:
                return pygame.image.load(bg_path.as_posix()).convert()
            except pygame.error:
                pass
        
        # Fallback to deck building bg (common asset)
        bg_path = Path("assets") / "deck_building_bg.png"
        if bg_path.exists():
            try:
                return pygame.image.load(bg_path.as_posix()).convert()
            except pygame.error:
                pass
                
        return None

    def _extract_card_id(self, text: str) -> str:
        marker = "ID:"
        if marker not in text:
            return ""
        tail = text.split(marker)[-1]
        tail = tail.split("]")[0]
        return tail.strip().strip(".")

    def _parse_lore_entries(self) -> Dict[str, Dict[str, str]]:
        tab = self._get_tab("Tab 10 – Faction Lore & Leader Bios")
        lore: Dict[str, Dict[str, str]] = {}
        
        # The faction entries are children of Tab 10 (### Tau'ri, ### Goa'uld, etc.)
        for child in tab.children:
            faction_name = child.title.strip()
            current = lore.setdefault(faction_name, {})
            
            # Parse the content lines for this faction
            for raw in child.content:
                stripped = raw.strip()
                if stripped.startswith("- ") and current is not None:
                    key, val = self._split_bullet(stripped[2:].strip())
                    current[key.rstrip(":")] = val
        
        # Also check direct content of tab (for backwards compatibility)
        current = None
        for raw in tab.content:
            stripped = raw.strip()
            if stripped.startswith("### "):
                name = stripped.replace("###", "").strip()
                current = lore.setdefault(name, {})
            elif stripped.startswith("- ") and current is not None:
                key, val = self._split_bullet(stripped[2:].strip())
                current[key.rstrip(":")] = val
        return lore

    def _load_leader_data(self) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        if not LEADER_JSON.exists():
            return {}
        raw = json.loads(LEADER_JSON.read_text())
        data: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        for fac_key, payload in raw.items():
            pretty = self._pretty_faction_name(fac_key)
            data[pretty] = {
                "base": payload.get("base", []),
                "unlockable": payload.get("unlockable", []),
            }
        return data

    def _load_leader_portraits(self) -> Dict[str, pygame.Surface]:
        portraits: Dict[str, pygame.Surface] = {}
        portrait_size = (280, 360)  # Higher res for better scaling
        for faction in self.leader_data.values():
            for bucket in faction.values():
                for leader in bucket:
                    card_id = leader.get("card_id")
                    if not card_id or card_id in portraits:
                        continue
                    
                    # Prioritize specific leader portrait if it exists
                    leader_variant = f"{card_id}_leader"
                    if (Path("assets") / f"{leader_variant}.png").exists():
                        img = self._try_load_asset(leader_variant, portrait_size)
                    else:
                        img = self._try_load_asset(card_id, portrait_size)
                        
                    portraits[card_id] = img
        return portraits

    def _try_load_asset(self, card_id: str, size: Tuple[int, int]) -> pygame.Surface:
        path = Path("assets") / f"{card_id}.png"
        if path.exists():
            try:
                img = pygame.image.load(path.as_posix()).convert_alpha()
                return pygame.transform.smoothscale(img, size)
            except pygame.error:
                pass
        placeholder = pygame.Surface(size, pygame.SRCALPHA)
        placeholder.fill(self._hash_color(card_id))
        label = self.small_font.render(card_id.replace("_", " ")[:14], True, self.text_color)
        placeholder.blit(label, (8, size[1] // 2 - label.get_height() // 2))
        return placeholder

    def _hash_color(self, key: str) -> Tuple[int, int, int]:
        base = sum(ord(c) for c in key)
        return ((base * 37) % 128 + 80, (base * 17) % 128 + 80, (base * 53) % 128 + 80)

    def _load_card_images(self) -> Dict[str, pygame.Surface]:
        images: Dict[str, pygame.Surface] = {}
        thumb_size = (200, 280)  # Higher res for better scaling
        for faction_sections in self.card_data.values():
            for entries in faction_sections.values():
                for entry in entries:
                    card_id = entry.get("card_id")
                    if not card_id or card_id in images:
                        continue
                    images[card_id] = self._try_load_asset(card_id, thumb_size)
        return images

    def _get_card_art(self, card_id: Optional[str], size: Tuple[int, int]) -> Optional[pygame.Surface]:
        if not card_id:
            return None
        base = self.card_images.get(card_id)
        if not base:
            return None
        base_w, base_h = base.get_size()
        max_w, max_h = size
        if max_w <= 0 or max_h <= 0:
            return base
        scale = min(max_w / base_w, max_h / base_h)
        new_size = (max(1, int(base_w * scale)), max(1, int(base_h * scale)))
        if new_size == base.get_size():
            return base
        return pygame.transform.smoothscale(base, new_size)

    # ---------- Utility parsing helpers ----------

    def _pretty_faction_name(self, fac_key: str) -> str:
        mapping = {
            "FACTION_TAURI": "Tau'ri",
            "FACTION_GOAULD": "Goa'uld",
            "FACTION_JAFFA": "Jaffa Rebellion",
            "FACTION_LUCIAN": "Lucian Alliance",
            "FACTION_ASGARD": "Asgard",
        }
        return mapping.get(fac_key, fac_key)

    def _split_bullet(self, text: str) -> Tuple[str, str]:
        if text.startswith("**"):
            end = text.find("**", 2)
            title = text[2:end]
            remainder = text[end + 2 :].lstrip(":–- ").strip()
            return title, remainder
        parts = text.split(":", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return text, ""

    def _get_tab(self, title: str) -> SpecNode:
        for tab in self.tabs:
            if tab.title == title:
                return tab
        return SpecNode(title, 0)

    # ---------- Layout Helpers ----------

    def _refresh_layout(self):
        # Calculate uniform scale (preserve aspect ratio) with letterboxing
        self.scale_x = self.width / BASE_FRAME_SIZE[0]
        self.scale_y = self.height / BASE_FRAME_SIZE[1]
        self.scale = min(self.scale_x, self.scale_y)  # Use minimum to fit without stretching

        # Calculate centering offsets for letterboxing
        scaled_width = BASE_FRAME_SIZE[0] * self.scale
        scaled_height = BASE_FRAME_SIZE[1] * self.scale
        self.offset_x = (self.width - scaled_width) / 2
        self.offset_y = (self.height - scaled_height) / 2

        # Scale background with uniform scaling and center it
        if self.background_image:
            new_w = int(BASE_FRAME_SIZE[0] * self.scale)
            new_h = int(BASE_FRAME_SIZE[1] * self.scale)
            scaled = pygame.transform.smoothscale(self.background_image, (new_w, new_h))

            # Create full-screen surface and center the scaled background
            self.background_scaled = pygame.Surface((self.width, self.height))
            self.background_scaled.fill(self.bg_color)
            self.background_scaled.blit(scaled, (int(self.offset_x), int(self.offset_y)))
            self.background_scaled.set_colorkey((0, 0, 0))
        else:
            self.background_scaled = None
        self._init_fonts()
        # All panels use uniform scaling to align with background frame
        self.left_panels = {name: self._scale_rect(rect) for name, rect in LEFT_PANEL_RECTS.items()}
        self.right_slots = [self._scale_rect(rect) for rect in RIGHT_STACK_RECTS]
        self.bottom_status_rect = self._scale_rect(STATUS_BAR_RECT)
        # Gate-centered elements use uniform scaling with offset
        center = self._scale_point(GATE_CENTER)
        radius = max(60, int(self.scale * GATE_RADIUS))
        self.viewport_rect = pygame.Rect(
            int(center[0] - radius),
            int(center[1] - radius),
            radius * 2,
            radius * 2,
        )

        # Position back button in bottom left (uniform scaling to align with frame)
        self.back_button_rect = self._scale_rect((100, 2000, 350, 100))
        
        self._rebuild_viewport_mask()
        self._rebuild_scanlines()
        self._build_chevron_slots()
        self._sync_leader_selection()
        self._ensure_card_selection()

    def _init_fonts(self):
        # Use average of scale_x/scale_y for fonts (screen-relative, not letterboxed)
        screen_scale = (self.scale_x + self.scale_y) * 0.5
        base = max(0.65, min(screen_scale * 1.4, 2.4))
        self.title_font = pygame.font.SysFont(
            "BankGothic Md BT, Orbitron, Eurostile, Arial", max(32, int(46 * base))
        )
        self.body_font = pygame.font.SysFont("Eurostile, Orbitron, Arial", max(18, int(24 * base)))
        self.small_font = pygame.font.SysFont("Eurostile, Orbitron, Arial", max(14, int(18 * base)))
        self.mono_font = pygame.font.SysFont("Consolas, Menlo, Courier", max(14, int(18 * base)))

    def _scale_point(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Scale a point for gate-centered elements (uses uniform scale + offset)."""
        return (point[0] * self.scale + self.offset_x,
                point[1] * self.scale + self.offset_y)

    def _scale_rect(self, rect_data: Tuple[int, int, int, int]) -> pygame.Rect:
        """Scale a rect for gate-centered elements (uses uniform scale + offset)."""
        x, y, w, h = rect_data
        return pygame.Rect(
            int(x * self.scale + self.offset_x),
            int(y * self.scale + self.offset_y),
            max(4, int(w * self.scale)),
            max(4, int(h * self.scale)),
        )

    def _scale_polygon(self, polygon: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Scale a polygon for gate-centered elements (uses uniform scale + offset)."""
        return [(int(px * self.scale + self.offset_x), int(py * self.scale + self.offset_y)) for px, py in polygon]

    def _rebuild_viewport_mask(self):
        size = (self.viewport_rect.width, self.viewport_rect.height)
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (size[0] // 2, size[1] // 2), size[0] // 2)
        self.viewport_mask = mask

    def _rebuild_scanlines(self):
        size = (self.viewport_rect.width, self.viewport_rect.height)
        pattern = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(0, size[1], SCANLINE_SPACING):
            pygame.draw.line(pattern, (0, 120, 180, 40), (0, y), (size[0], y))
        self.scanline_surface = pattern

    def _build_chevron_slots(self):
        center = self._scale_point(GATE_CENTER)
        slots = []
        for poly in CHEVRON_POLYGONS:
            scaled = self._scale_polygon(poly)
            cx = sum(pt[0] for pt in scaled) / len(scaled)
            cy = sum(pt[1] for pt in scaled) / len(scaled)
            angle = math.degrees(math.atan2(cy - center[1], cx - center[0])) % 360
            slots.append((angle, {"polygon": scaled, "tabs": [], "current_index": 0, "label": ""}))
        slots.sort(key=lambda entry: entry[0])
        ordered = [payload for _, payload in slots]

        # Apply thematic chevron config
        for idx, config in enumerate(CHEVRON_CONFIG):
            if idx < len(ordered):
                ordered[idx]["tabs"] = config["tabs"]
                ordered[idx]["label"] = config["label"]

        self.chevron_slots = ordered
        self._sync_chevron_state()

    def _sync_chevron_state(self):
        for slot in self.chevron_slots:
            slot["current_index"] = 0
            if self.active_tab in slot["tabs"]:
                slot["current_index"] = slot["tabs"].index(self.active_tab)

    def _sync_leader_selection(self):
        leaders = self.leader_data.get(self.leader_faction, {}).get(self.leader_category, [])
        self.leader_page_offset = 0
        self.leader_selected = leaders[0] if leaders else None

    def _ensure_card_selection(self):
        entries = self.card_data.get(self.card_faction, {}).get(self.card_section, [])
        filtered = [entry for entry in entries if self.card_search.lower() in entry["name"].lower()]
        if not filtered:
            self.card_selected = None
            self.card_list_offset = 0
            return
        self.card_list_offset = min(self.card_list_offset, max(0, len(filtered) - 1))
        if not self.card_selected or self.card_selected not in filtered:
            self.card_selected = filtered[0]

    def _set_active_tab(self, index: int):
        index = max(0, min(len(self.tab_titles) - 1, index))
        if index == self.active_tab:
            return
        self.active_tab = index
        self.scroll_offsets.setdefault(index, 0)
        self._sync_chevron_state()
        self._set_status(self.tab_titles[index])

    def _activate_chevron(self, slot_index: int):
        if slot_index < 0 or slot_index >= len(self.chevron_slots):
            return
        slot = self.chevron_slots[slot_index]
        if not slot["tabs"]:
            return
        next_index = (slot["current_index"] + 1) % len(slot["tabs"])
        slot["current_index"] = next_index
        self._set_active_tab(slot["tabs"][next_index])

    def _set_status(self, text: str):
        self.status_message = text

    def _point_in_polygon(self, pos: Tuple[int, int], polygon: List[Tuple[int, int]]) -> bool:
        x, y = pos
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersects = ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-6) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside

    # ---------- Event Handling ----------

    def resize(self, width: int, height: int):
        self.width = width
        self.height = height
        self._refresh_layout()

    def handle_event(self, event) -> Optional[str]:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE) and not self.active_input:
                return "back"
            self._handle_keypress(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            self._handle_scroll(event.y)
        
        if self.should_exit:
            return "back"
        return None

    def _handle_keypress(self, event):
        if not self.active_input:
            if event.key == pygame.K_r:
                self.__init__(self.width, self.height)  # reload spec + data
            return
        tab_type, field = self.active_input
        if event.key == pygame.K_RETURN:
            self.active_input = None
            return
        if event.key == pygame.K_ESCAPE:
            self.active_input = None
            return
        if event.key == pygame.K_BACKSPACE:
            self._modify_input(tab_type, field, backspace=True)
            return
        if event.unicode:
            self._modify_input(tab_type, field, text=event.unicode)

    def _modify_input(self, tab_type: str, field: str, text: str = "", backspace: bool = False):
        if tab_type == "abilities" and field == "search":
            if backspace:
                self.ability_search = self.ability_search[:-1]
            else:
                self.ability_search += text
            self.scroll_offsets[self.active_tab] = 0
        elif tab_type == "cards" and field == "search":
            if backspace:
                self.card_search = self.card_search[:-1]
            else:
                self.card_search += text
            self.card_list_offset = 0
            self._ensure_card_selection()

    def _handle_click(self, pos):
        for hit in reversed(self.hit_regions):
            polygon = hit.get("polygon")
            rect = hit.get("rect")
            if polygon and self._point_in_polygon(pos, polygon):
                self._process_hit(hit)
                return
            if rect and rect.collidepoint(pos):
                self._process_hit(hit)
                return
        self.active_input = None

    def _process_hit(self, hit: Dict):
        action = hit["type"]
        if action == "exit":
            self.should_exit = True
        elif action == "chevron":
            self._activate_chevron(hit["slot"])
        elif action == "faction":
            self.active_faction = hit["name"]
            self.scroll_offsets[self.active_tab] = 0
            self._set_status(f"{self.active_faction} directives active")
        elif action == "leader_faction":
            self.leader_faction = hit["name"]
            self._sync_leader_selection()
            self._set_status(f"Leader roster: {self.leader_faction}")
        elif action == "leader_category":
            self.leader_category = hit["category"]
            self._sync_leader_selection()
            label = "Base" if hit["category"] == "base" else "Unlockable"
            self._set_status(f"{self.leader_faction} {label} Leaders")
        elif action == "leader_select":
            self.leader_selected = hit["entry"]
            self._set_status(f"Leader locked: {self.leader_selected['name']}")
        elif action == "leader_scroll":
            leaders = self.leader_data.get(self.leader_faction, {}).get(self.leader_category, [])
            if leaders:
                max_offset = max(0, len(leaders) - len(self.right_slots))
                self.leader_page_offset = max(0, min(max_offset, self.leader_page_offset + hit["delta"]))
        elif action == "ability_letter":
            self.ability_letter = hit["letter"]
            self.scroll_offsets[self.active_tab] = 0
        elif action == "card_faction":
            self.card_faction = hit["name"]
            sections = list(self.card_data.get(self.card_faction, {}).keys())
            if sections and self.card_section not in sections:
                self.card_section = sections[0]
            self.card_list_offset = 0
            self._ensure_card_selection()
            self._set_status(f"{self.card_faction} deck manifest")
        elif action == "card_section":
            self.card_section = hit["section"]
            self.card_list_offset = 0
            self._ensure_card_selection()
        elif action == "card_entry":
            self.card_selected = hit["entry"]
            self._set_status(f"Card ready: {self.card_selected['name']}")
        elif action == "card_scroll":
            entries = self.card_data.get(self.card_faction, {}).get(self.card_section, [])
            filtered = [entry for entry in entries if self.card_search.lower() in entry["name"].lower()]
            max_offset = max(0, len(filtered) - hit.get("page", 1))
            self.card_list_offset = max(0, min(max_offset, self.card_list_offset + hit["delta"]))
        elif action == "lore_faction":
            self.lore_faction = hit["name"]
        elif action == "input":
            self.active_input = (hit["tab_type"], hit["field"])
        self.hit_regions.clear()

    def _handle_scroll(self, delta: int):
        tab_title = self.tab_titles[self.active_tab]
        behavior = TAB_BEHAVIOR.get(tab_title, "text")
        # Smoother scroll steps for better reading experience
        step = 25 if behavior in {"text", "abilities", "lore"} else 35
        if behavior in {"text", "abilities", "lore", "faction"}:
            self.scroll_offsets[self.active_tab] = max(
                0, self.scroll_offsets.get(self.active_tab, 0) - delta * step
            )
        elif behavior == "cards":
            self.scroll_offsets[self.active_tab] = max(
                0, self.scroll_offsets.get(self.active_tab, 0) - delta * 30
            )

    # ---------- Drawing ----------

    def draw(self, surface: pygame.Surface):
        surface.fill(self.bg_color)
        # Draw background FIRST so it's behind all UI elements
        if self.background_scaled:
            surface.blit(self.background_scaled, (0, 0))
        self.hit_regions.clear()
        self._draw_soft_grid(surface)
        tab_title = self.tab_titles[self.active_tab]
        behavior = TAB_BEHAVIOR.get(tab_title, "text")
        self._draw_header(surface)
        self._draw_left_controls(surface, behavior)
        self._draw_right_controls(surface, behavior)
        self._draw_viewport(surface, behavior)
        self._draw_status_bar(surface)
        self._draw_chevrons(surface)
        self._draw_back_button(surface)

    def _draw_back_button(self, surface: pygame.Surface):
        rect = self.back_button_rect
        # Use mouse pos for hover effect (if available via external update, otherwise static)
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        
        color = self.accent_color if hovered else self.deep_accent
        bg_color = (20, 40, 60) if hovered else (10, 20, 30)
        
        # Draw button background
        pygame.draw.rect(surface, bg_color, rect, border_radius=8)
        pygame.draw.rect(surface, color, rect, 2, border_radius=8)
        
        # Draw text
        text = self.body_font.render("MAIN MENU", True, self.text_color)
        text_rect = text.get_rect(center=rect.center)
        surface.blit(text, text_rect)
        
        # Register hit region
        self.hit_regions.append({"type": "exit", "rect": rect})


    def _draw_soft_grid(self, surface: pygame.Surface):
        spacing = max(80, int(140 * self.scale))
        glow = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, spacing):
            pygame.draw.line(glow, (0, 60, 120, 25), (0, y), (self.width, y))
        for x in range(0, self.width, spacing):
            pygame.draw.line(glow, (0, 60, 120, 25), (x, 0), (x, self.height))
        surface.blit(glow, (0, 0))

    def _draw_header(self, surface: pygame.Surface):
        tab_title = self.tab_titles[self.active_tab]
        title = self.title_font.render("STARGWENT RULE COMPENDIUM", True, self.accent_color)
        surface.blit(title, title.get_rect(center=(self.width // 2, int(70 * self.scale_y) + 30)))
        subtitle = self.small_font.render(f"{tab_title} — scroll inner gate for data", True, self.muted_color)
        surface.blit(subtitle, subtitle.get_rect(center=(self.width // 2, int(70 * self.scale_y) + 70)))

    def _draw_left_controls(self, surface: pygame.Surface, behavior: str):
        upper = self.left_panels.get("upper")
        lower = self.left_panels.get("lower")
        stack = self.left_panels.get("stack")
        if behavior == "faction":
            if upper:
                self._panel_label(surface, upper, "Factions")
                self._draw_menu(surface, upper, [f["name"] for f in self.faction_cards], self.active_faction, "faction")
            if lower:
                self._draw_panel_hint(surface, lower, "Scroll gate to read passive, power, and tactics.")
        elif behavior == "leaders":
            if upper:
                self._panel_label(surface, upper, "Leader Faction")
                self._draw_menu(surface, upper, FACTION_DISPLAY, self.leader_faction, "leader_faction")
            if lower:
                self._panel_label(surface, lower, "Roster Tier")
                toggles = [("Base", "base"), ("Unlock", "unlockable")]
                self._draw_toggle_buttons(surface, lower, toggles, self.leader_category, "leader_category")
        elif behavior == "abilities":
            if upper:
                self._panel_label(surface, upper, "Ability Search")
                self._draw_search_box(surface, upper, self.ability_search or "type to filter", "abilities")
            if lower:
                self._panel_label(surface, lower, "Alphabet Filter")
                self._draw_letter_grid(surface, lower)
        elif behavior == "cards":
            if upper:
                self._panel_label(surface, upper, "Card Faction")
                self._draw_menu(surface, upper, FACTION_DISPLAY, self.card_faction, "card_faction")
            if lower:
                self._panel_label(surface, lower, "Deck Section")
                sections = list(self.card_data.get(self.card_faction, {}).keys())
                self._draw_toggle_buttons(surface, lower, [(s, s) for s in sections], self.card_section, "card_section")
            if stack:
                self._panel_label(surface, stack, "Card Manifest")
                self._draw_card_list_panel(surface, stack)
        elif behavior == "lore":
            if upper:
                self._panel_label(surface, upper, "Faction Selection")
                self._draw_menu(surface, upper, FACTION_DISPLAY, self.lore_faction, "lore_faction")
            if lower:
                self._draw_panel_hint(surface, lower, "Gate viewport shows lore + signature strategy.")
        else:
            if upper:
                self._draw_panel_hint(surface, upper, "Chevron ring now controls tabs. Use scroll for long entries.")
            if lower:
                self._draw_panel_hint(surface, lower, "Left panels host filters + references for each tab.")

    def _draw_right_controls(self, surface: pygame.Surface, behavior: str):
        if behavior == "leaders":
            self._draw_leader_thumbnails(surface)
        elif behavior == "cards":
            self._draw_card_art_panel(surface)
        elif behavior == "abilities":
            if self.right_slots:
                hint_rect = self.right_slots[0]
                self._panel_label(surface, hint_rect, "Diagnostics")
                self._draw_panel_hint(surface, hint_rect, "Use letter grid or search field to filter abilities.")

    def _draw_viewport(self, surface: pygame.Surface, behavior: str):
        viewport = pygame.Surface(self.viewport_rect.size, pygame.SRCALPHA)
        tab_title = self.tab_titles[self.active_tab]
        if behavior == "faction":
            self._draw_faction_content(viewport)
        elif behavior == "leaders":
            self._draw_leader_content(viewport)
        elif behavior == "abilities":
            self._draw_ability_content(viewport)
        elif behavior == "cards":
            self._draw_card_content(viewport)
        elif behavior == "lore":
            self._draw_lore_content(viewport)
        else:
            self._draw_text_content(viewport, self.general_sections.get(tab_title, {}))
        if self.viewport_mask:
            viewport.blit(self.viewport_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if self.scanline_surface:
            viewport.blit(self.scanline_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        previous_clip = surface.get_clip()
        surface.set_clip(self.viewport_rect)
        surface.blit(viewport, self.viewport_rect.topleft)
        surface.set_clip(previous_clip)

    def _draw_status_bar(self, surface: pygame.Surface):
        rect = self.bottom_status_rect
        pygame.draw.rect(surface, self.accent_color, rect, 2)
        tab_label = self.small_font.render(self.tab_titles[self.active_tab], True, self.text_color)
        status_label = self.small_font.render(self.status_message, True, self.text_color)
        surface.blit(tab_label, (rect.x + 18, rect.y + 12))
        surface.blit(status_label, (rect.x + 18, rect.y + 18 + tab_label.get_height()))

    def _draw_chevrons(self, surface: pygame.Surface):
        layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        for idx, slot in enumerate(self.chevron_slots):
            polygon = slot["polygon"]
            active_tab = slot["tabs"][slot["current_index"]] if slot["tabs"] else None
            active = active_tab == self.active_tab
            fill_alpha = 110 if active else 40
            stroke_color = self.chevron_color if active else (120, 40, 40)
            pygame.draw.polygon(layer, (*stroke_color, fill_alpha), polygon)
            pygame.draw.polygon(layer, (*stroke_color, 200), polygon, 2)
            self.hit_regions.append({"type": "chevron", "slot": idx, "polygon": polygon})
        surface.blit(layer, (0, 0))

    def _draw_text_content(self, view: pygame.Surface, data: Dict):
        column_x, column_width, top, area_height = self._viewport_safe_area(view)
        offset = self.scroll_offsets.get(self.active_tab, 0)
        y = top + 10 - offset
        content_height = 0
        overview = data.get("overview", [])
        for paragraph in overview:
            start_y = y
            y = self._render_wrapped(
                view,
                paragraph,
                (column_x + column_width // 2, y),
                column_width,
                self.body_font,
                self.text_color,
                align_center=True,
            ) + 28  # Increased paragraph spacing for better readability
            content_height += y - start_y
        for item in data.get("items", []):
            start_y = y
            # Calculate dynamic height based on text content
            title_height = self.small_font.get_linesize() + 14  # title + padding
            body_text = item["body"]
            body_width = column_width - 32
            max_chars = max(1, body_width // max(1, self.small_font.size("M")[0]))
            wrapped_lines = wrap(body_text, max_chars) if body_text else []
            body_height = len(wrapped_lines) * self.small_font.get_linesize()
            # Total height: title area (48px) + body + bottom padding (20px)
            item_height = max(80, 48 + body_height + 20)

            card_rect = pygame.Rect(column_x, y, column_width, item_height)
            pygame.draw.rect(view, self.accent_color, card_rect, 2)
            title = self.small_font.render(item["title"], True, self.accent_color)
            view.blit(title, (card_rect.x + 16, card_rect.y + 14))
            self._render_wrapped(
                view,
                item["body"],
                (card_rect.x + card_rect.width // 2, card_rect.y + 48),
                card_rect.width - 32,
                self.small_font,
                self.text_color,
                align_center=True,
            )
            y += item_height + 20  # item height + gap between items
            content_height += y - start_y
        self._update_scroll_limit(content_height, area_height)

    def _draw_faction_content(self, view: pygame.Surface):
        active = next((f for f in self.faction_cards if f["name"] == self.active_faction), None)
        if not active:
            self._render_wrapped(view, "No faction data.", (40, 60), view.get_width() - 80, self.body_font, self.warning_color)
            return
        column_x, column_width, top, area_height = self._viewport_safe_area(view)
        offset = self.scroll_offsets.get(self.active_tab, 0)
        y = top + 10 - offset
        content_height = 0
        
        # Display faction fields - include Strategy Tips if available
        faction_fields = [
            ("Passive Ability", "Passive"),
            ("Faction Power", "Power"),
            ("Unique Mechanics", "Unique"),
            ("Strategy Tips", "Strategy Tips"),
        ]
        
        for label, key in faction_fields:
            entry_text = active.get(key, "")
            if not entry_text:
                continue
                
            heading = self.small_font.render(label.upper(), True, self.muted_color)
            view.blit(heading, (column_x, y))
            start_y = y
            y = self._render_wrapped(
                view,
                entry_text,
                (column_x + column_width // 2, y + 26),
                column_width,
                self.body_font,
                self.text_color,
                align_center=True,
            ) + 30
            content_height += y - start_y
        self._update_scroll_limit(content_height, area_height)

    def _draw_leader_content(self, view: pygame.Surface):
        leader = self.leader_selected
        if not leader:
            self._render_wrapped(view, "No leader unlocked in this category.", (40, 60), view.get_width() - 80, self.body_font, self.warning_color)
            return
        column_x, column_width, top, area_height = self._viewport_safe_area(view)
        offset = self.scroll_offsets.get(self.active_tab, 0)
        y = top + 10 - offset
        content_height = 0
        title = self.body_font.render(leader["name"], True, self.accent_color)
        view.blit(title, (column_x, y))
        y += title.get_height() + 12
        content_height += title.get_height() + 12
        ability = leader.get("ability_desc") or leader.get("ability", "")
        start_y = y
        y = self._render_wrapped(
            view,
            ability,
            (column_x + column_width // 2, y),
            column_width,
            self.body_font,
            self.text_color,
            align_center=True,
        ) + 20
        content_height += y - start_y
        notes = LEADER_NOTES.get(leader["name"], {})
        for label in ("timing", "synergy"):
            if notes.get(label):
                heading = self.small_font.render(label.capitalize(), True, self.muted_color)
                view.blit(heading, (column_x, y))
                start_y = y
                y = self._render_wrapped(
                    view,
                    notes[label],
                    (column_x + column_width // 2, y + 20),
                    column_width,
                    self.small_font,
                    self.text_color,
                    align_center=True,
                ) + 16
                content_height += y - start_y
        self._update_scroll_limit(content_height, area_height)

    def _draw_ability_content(self, view: pygame.Surface):
        abilities = self._filter_abilities()
        column_x, column_width, top, area_height = self._viewport_safe_area(view)
        offset = self.scroll_offsets.get(self.active_tab, 0)
        y = top + 10 - offset
        content_height = 0
        for ability in abilities:
            # Start of this ability card
            card_start_y = y

            # Draw name
            name = self.small_font.render(ability["name"], True, self.accent_color)
            view.blit(name, (column_x + 16, y + 10))

            center_x = column_x + column_width // 2
            current_y = y + 36

            # Render Effect (returns Y after rendering)
            current_y = self._render_wrapped(
                view,
                f"Effect: {ability['effect']}",
                (center_x, current_y),
                column_width - 32,
                self.small_font,
                self.text_color,
                align_center=True,
            )
            current_y += 6  # Small gap

            # Render Timing
            current_y = self._render_wrapped(
                view,
                f"Timing: {ability['timing']}",
                (center_x, current_y),
                column_width - 32,
                self.small_font,
                self.muted_color,
                align_center=True,
            )
            current_y += 6  # Small gap

            # Render Synergy
            current_y = self._render_wrapped(
                view,
                f"Synergy: {ability['synergy']}",
                (center_x, current_y),
                column_width - 32,
                self.small_font,
                self.muted_color,
                align_center=True,
            )
            current_y += 12  # Bottom padding

            # Calculate actual card height based on rendered content
            actual_height = current_y - card_start_y
            min_height = 120  # Minimum card height
            card_height = max(min_height, actual_height)

            # Draw border around the actual content
            card_rect = pygame.Rect(column_x, card_start_y, column_width, card_height)
            pygame.draw.rect(view, self.deep_accent, card_rect, 2)

            # Move to next card with proper spacing
            y = card_start_y + card_height + 20  # 20px gap between cards
            content_height += card_height + 20
        self._update_scroll_limit(content_height, area_height)

    def _draw_card_content(self, view: pygame.Surface):
        if not self.card_selected:
            self._render_wrapped(view, "Select a card from the left manifest.", (40, 60), view.get_width() - 80, self.body_font, self.muted_color)
            return
        card = self.card_selected
        column_x, column_width, top, area_height = self._viewport_safe_area(view)
        offset = self.scroll_offsets.get(self.active_tab, 0)
        y = top + 10 - offset
        content_height = 0
        title = self.body_font.render(card["name"], True, self.accent_color)
        view.blit(title, (column_x + column_width // 2 - title.get_width() // 2, y))
        y += title.get_height() + 6
        content_height += title.get_height() + 6
        meta = self.small_font.render(f"Section: {self.card_section}  |  Faction: {self.card_faction}", True, self.muted_color)
        view.blit(meta, (column_x + column_width // 2 - meta.get_width() // 2, y))
        y += meta.get_height() + 14
        content_height += meta.get_height() + 14
        start_y = y
        y = self._render_wrapped(
            view,
            card["body"],
            (column_x + column_width // 2, y),
            column_width,
            self.body_font,
            self.text_color,
            align_center=True,
        )
        content_height += y - start_y
        self._update_scroll_limit(content_height, area_height)

    def _draw_lore_content(self, view: pygame.Surface):
        info = self.lore_entries.get(self.lore_faction, {})
        column_x, column_width, top, area_height = self._viewport_safe_area(view)
        offset = self.scroll_offsets.get(self.active_tab, 0)
        y = top + 10 - offset
        content_height = 0
        
        # Display all lore fields in order
        lore_fields = ["Lore", "Signature Strategy", "Key Synergies", "Iconic Quote"]
        
        for label in lore_fields:
            entry_text = info.get(label, "")
            if not entry_text:
                continue
                
            # Special styling for Iconic Quote
            if label == "Iconic Quote":
                heading = self.small_font.render("ICONIC QUOTE", True, self.accent_color)
            else:
                heading = self.small_font.render(label.upper(), True, self.muted_color)
            
            view.blit(heading, (column_x + column_width // 2 - heading.get_width() // 2, y))
            start_y = y
            
            # Use italic-style color for quotes
            text_color = self.accent_color if label == "Iconic Quote" else self.text_color
            
            y = self._render_wrapped(
                view,
                entry_text,
                (column_x + column_width // 2, y + 24),
                column_width,
                self.body_font,
                text_color,
                align_center=True,
            ) + 36  # Extra spacing between sections for better readability
            content_height += y - start_y
        self._update_scroll_limit(content_height, area_height)

    def _viewport_safe_area(self, view: pygame.Surface) -> Tuple[int, int, int, int]:
        width = view.get_width()
        radius = width // 2
        # Increased margins for cleaner look inside the portal
        margin = max(60, int(radius * 0.38))
        column_width = max(200, width - margin * 2)
        column_x = (width - column_width) // 2
        available_height = width - margin * 2
        return column_x, column_width, margin, available_height

    def _update_scroll_limit(self, content_height: float, area_height: float):
        offset = self.scroll_offsets.get(self.active_tab, 0)
        max_offset = max(0, content_height - area_height)
        self.scroll_offsets[self.active_tab] = max(0, min(max_offset, offset))

    def _panel_label(self, surface: pygame.Surface, rect: pygame.Rect, text: str):
        if not rect:
            return
        label = self.small_font.render(text.upper(), True, self.accent_color)
        surface.blit(label, (rect.x, rect.y - label.get_height() - 6))

    def _draw_panel_hint(self, surface: pygame.Surface, rect: pygame.Rect, text: str):
        if not rect:
            return
        hint_rect = pygame.Rect(rect.x + 10, rect.y + 10, rect.width - 20, rect.height - 20)
        pygame.draw.rect(surface, self.deep_accent, hint_rect, 1)
        self._render_wrapped(surface, text, (hint_rect.x + 8, hint_rect.y + 8), hint_rect.width - 16, self.small_font, self.muted_color)

    def _draw_menu(self, surface: pygame.Surface, rect: pygame.Rect, items: List[str], active: str, action_type: str):
        if not rect:
            return
        y = rect.y + 16
        for item in items:
            item_rect = pygame.Rect(rect.x + 10, y, rect.width - 20, self.small_font.get_linesize() + 8)
            selected = item == active
            color = self.accent_color if selected else self.deep_accent
            pygame.draw.rect(surface, color, item_rect, 2)
            text = self.small_font.render(item, True, self.text_color if selected else self.muted_color)
            surface.blit(text, (item_rect.x + 8, item_rect.y + 2))
            self.hit_regions.append({"type": action_type, "name": item, "rect": item_rect})
            y += item_rect.height + 10

    def _draw_toggle_buttons(self, surface: pygame.Surface, rect: pygame.Rect, options: List[Tuple[str, str]], active_value: str, action_type: str):
        if not rect:
            return
        button_width = max(120, rect.width // max(1, len(options)) - 10)
        x = rect.x + 10
        for label, value in options:
            button = pygame.Rect(x, rect.y + 16, button_width, 32)
            selected = value == active_value
            color = self.accent_color if selected else self.deep_accent
            pygame.draw.rect(surface, color, button, 2)
            text = self.small_font.render(label, True, self.text_color if selected else self.muted_color)
            surface.blit(text, (button.x + 10, button.y + 6))
            payload = {"type": action_type, "rect": button}
            if action_type == "leader_category":
                payload["category"] = value
            elif action_type == "card_section":
                payload["section"] = value
            else:
                payload["value"] = value
            self.hit_regions.append(payload)
            x += button_width + 12

    def _draw_search_box(self, surface: pygame.Surface, rect: pygame.Rect, value: str, tab_type: str):
        box = pygame.Rect(rect.x + 10, rect.y + 16, rect.width - 20, 36)
        pygame.draw.rect(surface, self.accent_color, box, 2)
        text = self.small_font.render(value, True, self.text_color)
        surface.blit(text, (box.x + 10, box.y + 6))
        self.hit_regions.append({"type": "input", "tab_type": tab_type, "field": "search", "rect": box})

    def _draw_letter_grid(self, surface: pygame.Surface, rect: pygame.Rect):
        letters = ["All"] + list(string.ascii_uppercase)
        cols = max(6, rect.width // 40)
        x = rect.x + 10
        y = rect.y + 16
        for idx, letter in enumerate(letters):
            cell = pygame.Rect(x, y, 34, 28)
            active = self.ability_letter == letter
            color = self.accent_color if active else self.deep_accent
            pygame.draw.rect(surface, color, cell, 2)
            text = self.small_font.render(letter[0], True, self.text_color if active else self.muted_color)
            surface.blit(text, (cell.x + 8, cell.y + 4))
            self.hit_regions.append({"type": "ability_letter", "letter": letter, "rect": cell})
            x += 38
            if (idx + 1) % cols == 0:
                x = rect.x + 10
                y += 32

    def _draw_card_list_panel(self, surface: pygame.Surface, rect: pygame.Rect):
        entries = self.card_data.get(self.card_faction, {}).get(self.card_section, [])
        filtered = [entry for entry in entries if self.card_search.lower() in entry["name"].lower()]
        row_height = self.small_font.get_linesize() + 10
        visible_count = max(1, (rect.height - 80) // row_height)
        max_offset = max(0, len(filtered) - visible_count)
        self.card_list_offset = max(0, min(max_offset, self.card_list_offset))
        start = self.card_list_offset
        display = filtered[start : start + visible_count]
        y = rect.y + 20
        for entry in display:
            row = pygame.Rect(rect.x + 10, y, rect.width - 20, row_height)
            selected = entry is self.card_selected
            color = self.accent_color if selected else self.deep_accent
            pygame.draw.rect(surface, color, row, 2)
            text = self.small_font.render(entry["name"], True, self.text_color if selected else self.muted_color)
            surface.blit(text, (row.x + 8, row.y + 2))
            self.hit_regions.append({"type": "card_entry", "entry": entry, "rect": row})
            y += row_height + 6
        if start > 0:
            up = pygame.Rect(rect.right - 40, rect.y + 16, 24, 20)
            pygame.draw.polygon(surface, self.accent_color, [(up.centerx, up.y), (up.left, up.bottom), (up.right, up.bottom)], 2)
            self.hit_regions.append({"type": "card_scroll", "delta": -1, "page": visible_count, "rect": up})
        if start + visible_count < len(filtered):
            down = pygame.Rect(rect.right - 40, rect.bottom - 36, 24, 20)
            pygame.draw.polygon(surface, self.accent_color, [(down.left, down.y), (down.right, down.y), (down.centerx, down.bottom)], 2)
            self.hit_regions.append({"type": "card_scroll", "delta": 1, "page": visible_count, "rect": down})

    def _draw_leader_thumbnails(self, surface: pygame.Surface):
        if not self.right_slots:
            return
        leaders = self.leader_data.get(self.leader_faction, {}).get(self.leader_category, [])
        slots = self.right_slots
        visible = leaders[self.leader_page_offset : self.leader_page_offset + len(slots)]
        for idx, slot in enumerate(slots):
            pygame.draw.rect(surface, self.deep_accent, slot, 2)
            if idx >= len(visible):
                continue
            leader = visible[idx]
            portrait = self.leader_images.get(leader.get("card_id"))
            # Reserve space for name at bottom (scaled)
            name_height = self.small_font.get_linesize() + 8
            if portrait:
                # Fill the slot with portrait, leaving small padding and name space
                max_w = max(20, slot.width - 8)
                max_h = max(20, slot.height - name_height - 8)
                pw, ph = portrait.get_size()
                scale = min(max_w / pw, max_h / ph)
                new_size = (max(1, int(pw * scale)), max(1, int(ph * scale)))
                img = pygame.transform.smoothscale(portrait, new_size)
                img_rect = img.get_rect(midtop=(slot.centerx, slot.y + 4))
                surface.blit(img, img_rect)
            name = self.small_font.render(leader["name"], True, self.text_color)
            surface.blit(name, (slot.x + 4, slot.bottom - name.get_height() - 4))
            self.hit_regions.append({"type": "leader_select", "entry": leader, "rect": slot})
        if leaders:
            max_offset = max(0, len(leaders) - len(slots))
            if self.leader_page_offset > 0:
                up = pygame.Rect(slots[0].centerx - 12, slots[0].y - 30, 24, 18)
                pygame.draw.polygon(surface, self.accent_color, [(up.centerx, up.y), (up.left, up.bottom), (up.right, up.bottom)], 2)
                self.hit_regions.append({"type": "leader_scroll", "delta": -1, "rect": up})
            if self.leader_page_offset < max_offset:
                down = pygame.Rect(slots[-1].centerx - 12, slots[-1].bottom + 12, 24, 18)
                pygame.draw.polygon(surface, self.accent_color, [(down.left, down.y), (down.right, down.y), (down.centerx, down.bottom)], 2)
                self.hit_regions.append({"type": "leader_scroll", "delta": 1, "rect": down})

    def _draw_card_art_panel(self, surface: pygame.Surface):
        if not self.card_selected or not self.right_slots:
            return
        art_slot = self.right_slots[0]
        pygame.draw.rect(surface, self.deep_accent, art_slot, 2)
        # Fill the slot with card art, leaving small padding
        art = self._get_card_art(self.card_selected.get("card_id"), (art_slot.width - 8, art_slot.height - 8))
        if art:
            art_pos = art.get_rect(center=art_slot.center)
            surface.blit(art, art_pos.topleft)
        text_slot = self.right_slots[1] if len(self.right_slots) > 1 else None
        if text_slot:
            pygame.draw.rect(surface, self.deep_accent, text_slot, 2)
            lines = [
                f"ID: {self.card_selected.get('card_id') or 'unknown'}",
                f"Section: {self.card_section}",
                f"Faction: {self.card_faction}",
            ]
            y = text_slot.y + 4
            for line in lines:
                y = self._render_wrapped(surface, line, (text_slot.x + 4, y), text_slot.width - 8, self.small_font, self.text_color) + 2

    def _filter_abilities(self) -> List[Dict[str, str]]:
        results = self.ability_entries
        if self.ability_letter != "All":
            results = [a for a in results if a["name"].upper().startswith(self.ability_letter)]
        if self.ability_search:
            results = [a for a in results if self.ability_search.lower() in a["name"].lower()]
        return results

    def _render_wrapped(
        self,
        surface: pygame.Surface,
        text: str,
        pos: Tuple[int, int],
        width: int,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        align_center: bool = False,
    ) -> int:
        x, y = pos
        if not text:
            return y
        max_chars = max(1, width // max(1, font.size("M")[0]))
        for line in wrap(text, max_chars):
            rendered = font.render(line, True, color)
            if align_center:
                line_x = x - rendered.get_width() // 2
            else:
                line_x = x
            surface.blit(rendered, (line_x, y))
            y += font.get_linesize()
        return y


def run_rules_menu(screen: pygame.Surface, toggle_fullscreen_callback=None):
    viewer = RulesMenuScreen(screen.get_width(), screen.get_height())
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    if toggle_fullscreen_callback:
                        toggle_fullscreen_callback()
                    else:
                        import display_manager; display_manager.toggle_fullscreen_mode()
                    screen = pygame.display.get_surface()
                    viewer.resize(screen.get_width(), screen.get_height())
                    continue
            result = viewer.handle_event(event)
            if result == "back":
                return None
        viewer.draw(screen)
        pygame.display.flip()
        clock.tick(60)
