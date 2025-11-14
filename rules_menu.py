"""
Interactive rule compendium viewer for Stargwent.
Provides tabbed navigation, faction/leader browsers, searchable ability glossary,
and card filtering backed by docs/rules_menu_spec.md plus generated JSON data.
"""

from __future__ import annotations

import json
import string
from dataclasses import dataclass, field
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
        "timing": "Neutral cards ignore deck restrictions while she is your leader.",
        "synergy": "Enables Tau'ri/Neutral hybrid builds anchored by Atlantis or Destiny.",
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
        self.background = (6, 10, 22)
        self.panel_color = (20, 28, 50)
        self.card_bg = (30, 38, 65)
        self.card_hover = (55, 80, 130)
        self.text_color = (230, 235, 245)
        self.muted_color = (170, 180, 200)
        self.highlight = (120, 190, 255)
        self.warning_color = (255, 120, 120)

        self.title_font = pygame.font.SysFont("Impact, Arial Black, Arial", 64, bold=True)
        self.tab_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.body_font = pygame.font.SysFont("Arial", 22)
        self.small_font = pygame.font.SysFont("Arial", 18)
        self.mono_font = pygame.font.SysFont("Consolas, Menlo, Courier", 18)

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
        self.background_scaled = None
        self._refresh_background()

        # UI state
        self.scroll_offsets: Dict[int, float] = {}
        self.hit_regions: List[Dict] = []
        self.active_input: Optional[Tuple[str, str]] = None
        self.active_faction = FACTION_DISPLAY[0]
        self.leader_faction = FACTION_DISPLAY[0]
        self.leader_category = "base"
        self.ability_search = ""
        self.ability_letter = "All"
        self.card_faction = FACTION_DISPLAY[0]
        self.card_section = "Core Deck"
        self.card_search = ""
        self.card_selected: Optional[Dict] = None
        self.lore_faction = FACTION_DISPLAY[0]
        initial_sections = list(self.card_data.get(self.card_faction, {}).keys())
        if initial_sections:
            self.card_section = initial_sections[0]

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
                current = {"name": name, "Passive": "", "Power": "", "Unique": "", "Strategy": ""}
                factions.append(current)
            elif stripped.startswith("- "):
                key, val = self._split_bullet(stripped[2:].strip())
                if current and key in current:
                    current[key] = val
            elif stripped.startswith("-"):
                # nested entries already handled
                continue
            elif stripped.startswith("  - "):
                label, val = self._split_bullet(stripped[4:].strip())
                if current and label in current:
                    current[label] = val
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
        bg_path = Path("assets") / "rule_menu_bg.png"
        if bg_path.exists():
            try:
                return pygame.image.load(bg_path.as_posix()).convert()
            except pygame.error:
                return None
        return None

    def _refresh_background(self):
        if self.background_image:
            self.background_scaled = pygame.transform.smoothscale(
                self.background_image, (self.width, self.height)
            )
        else:
            self.background_scaled = None

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
        portrait_size = (140, 180)
        for faction in self.leader_data.values():
            for bucket in faction.values():
                for leader in bucket:
                    card_id = leader.get("card_id")
                    if not card_id or card_id in portraits:
                        continue
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
        thumb_size = (80, 120)
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
        if base.get_size() == size:
            return base
        return pygame.transform.smoothscale(base, size)

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

    # ---------- Event Handling ----------

    def resize(self, width: int, height: int):
        self.width = width
        self.height = height
        self._refresh_background()

    def handle_event(self, event) -> Optional[str]:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE) and not self.active_input:
                return "back"
            self._handle_keypress(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            self._handle_scroll(event.y)
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
        elif tab_type == "cards" and field == "search":
            if backspace:
                self.card_search = self.card_search[:-1]
            else:
                self.card_search += text

    def _handle_click(self, pos):
        for hit in reversed(self.hit_regions):
            rect = hit["rect"]
            if rect.collidepoint(pos):
                action = hit["type"]
                if action == "tab":
                    self.active_tab = hit["index"]
                elif action == "faction":
                    self.active_faction = hit["name"]
                elif action == "leader_faction":
                    self.leader_faction = hit["name"]
                elif action == "leader_category":
                    self.leader_category = hit["category"]
                elif action == "ability_letter":
                    self.ability_letter = hit["letter"]
                    self.scroll_offsets[self.active_tab] = 0
                elif action == "card_faction":
                    self.card_faction = hit["name"]
                    sections = list(self.card_data.get(self.card_faction, {}).keys())
                    if sections and self.card_section not in sections:
                        self.card_section = sections[0]
                    self.card_selected = None
                elif action == "card_section":
                    self.card_section = hit["section"]
                    self.card_selected = None
                elif action == "card_entry":
                    self.card_selected = hit["entry"]
                elif action == "lore_faction":
                    self.lore_faction = hit["name"]
                elif action == "input":
                    self.active_input = (hit["tab_type"], hit["field"])
                self.hit_regions.clear()
                return
        # click outside inputs -> clear focus
        self.active_input = None

    def _handle_scroll(self, delta: int):
        tab_title = self.tab_titles[self.active_tab]
        behavior = TAB_BEHAVIOR.get(tab_title, "text")
        if behavior in {"text", "abilities"}:
            self.scroll_offsets[self.active_tab] = max(
                0, self.scroll_offsets.get(self.active_tab, 0) - delta * 30
            )
        elif behavior == "cards":
            self.scroll_offsets[self.active_tab] = max(
                0, self.scroll_offsets.get(self.active_tab, 0) - delta * 40
            )

    # ---------- Drawing ----------

    def draw(self, surface: pygame.Surface):
        if self.background_scaled:
            surface.blit(self.background_scaled, (0, 0))
        else:
            surface.fill(self.background)
        self.hit_regions.clear()
        self._draw_header(surface)
        self._draw_tab_bar(surface)
        tab_title = self.tab_titles[self.active_tab]
        behavior = TAB_BEHAVIOR.get(tab_title, "text")
        if behavior == "faction":
            self._draw_faction_tab(surface)
        elif behavior == "leaders":
            self._draw_leader_tab(surface)
        elif behavior == "abilities":
            self._draw_ability_tab(surface)
        elif behavior == "cards":
            self._draw_card_tab(surface)
        elif behavior == "lore":
            self._draw_lore_tab(surface)
        else:
            self._draw_text_tab(surface, self.general_sections.get(tab_title, {}))

    def _draw_header(self, surface):
        title = self.title_font.render("STARGWENT RULE COMPENDIUM", True, self.text_color)
        surface.blit(title, title.get_rect(midtop=(self.width // 2, 10)))
        subtitle = self.small_font.render("Tab navigation • Click panels for details • ESC to return", True, self.muted_color)
        surface.blit(subtitle, subtitle.get_rect(midtop=(self.width // 2, 70)))

    def _draw_tab_bar(self, surface):
        x = 60
        y = 100
        for idx, title in enumerate(self.tab_titles):
            text = self.tab_font.render(title.replace("Tab ", ""), True, self.text_color)
            padding = 20
            rect = pygame.Rect(x, y, text.get_width() + padding, 36)
            color = self.highlight if idx == self.active_tab else self.panel_color
            pygame.draw.rect(surface, color, rect, border_radius=12)
            surface.blit(text, (rect.x + padding / 2, rect.y + 8))
            self.hit_regions.append({"type": "tab", "index": idx, "rect": rect})
            x += rect.width + 10

    def _draw_text_tab(self, surface, data: Dict):
        panel = pygame.Rect(50, 150, self.width - 100, self.height - 190)
        pygame.draw.rect(surface, self.panel_color, panel, border_radius=18)
        x = panel.x + 24
        y = panel.y + 24 - self.scroll_offsets.get(self.active_tab, 0)
        overview = data.get("overview", [])
        items = data.get("items", [])
        for paragraph in overview:
            y = self._render_wrapped(surface, paragraph, (x, y), panel.width - 48, self.body_font, self.text_color)
            y += 10
        card_width = (panel.width - 72) // 2
        card_height = 120
        cols = 2
        for idx, item in enumerate(items):
            col = idx % cols
            row = idx // cols
            card_x = x + col * (card_width + 24)
            card_y = y + row * (card_height + 16)
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
            pygame.draw.rect(surface, self.card_bg, card_rect, border_radius=12)
            title_text = self.small_font.render(item["title"], True, self.highlight)
            surface.blit(title_text, (card_rect.x + 12, card_rect.y + 8))
            self._render_wrapped(
                surface,
                item["body"],
                (card_rect.x + 12, card_rect.y + 36),
                card_width - 24,
                self.small_font,
                self.text_color,
            )

    def _draw_faction_tab(self, surface):
        panel = pygame.Rect(50, 150, self.width - 100, self.height - 190)
        pygame.draw.rect(surface, self.panel_color, panel, border_radius=18)
        if not self.faction_cards:
            msg = "Faction data missing from rules_menu_spec.md."
            self._render_wrapped(surface, msg, (panel.x + 20, panel.y + 20), panel.width - 40, self.body_font, self.warning_color)
            return
        button_rects = []
        for idx, faction in enumerate(self.faction_cards):
            rect = pygame.Rect(panel.x + 20, panel.y + 20 + idx * 60, 180, 44)
            color = self.highlight if faction["name"] == self.active_faction else self.card_bg
            pygame.draw.rect(surface, color, rect, border_radius=10)
            label = self.small_font.render(faction["name"], True, self.text_color)
            surface.blit(label, (rect.x + 12, rect.y + 10))
            self.hit_regions.append({"type": "faction", "name": faction["name"], "rect": rect})
            button_rects.append(rect)

        active = next((f for f in self.faction_cards if f["name"] == self.active_faction), self.faction_cards[0])
        info_rect = pygame.Rect(panel.x + 220, panel.y + 20, panel.width - 240, panel.height - 40)
        pygame.draw.rect(surface, self.card_bg, info_rect, border_radius=16)

        y = info_rect.y + 20
        for label, key in [("Passive Ability", "Passive"), ("Faction Power", "Power"), ("Unique Mechanics", "Unique"), ("Strategy", "Strategy")]:
            title = self.small_font.render(label, True, self.muted_color)
            surface.blit(title, (info_rect.x + 20, y))
            y = self._render_wrapped(
                surface,
                active.get(key, ""),
                (info_rect.x + 20, y + 20),
                info_rect.width - 40,
                self.body_font,
                self.text_color,
            ) + 16

    def _draw_leader_tab(self, surface):
        panel = pygame.Rect(40, 150, self.width - 80, self.height - 190)
        pygame.draw.rect(surface, self.panel_color, panel, border_radius=18)

        # Faction buttons
        fx = panel.x + 20
        fy = panel.y + 20
        for faction in FACTION_DISPLAY:
            rect = pygame.Rect(fx, fy, 150, 40)
            color = self.highlight if faction == self.leader_faction else self.card_bg
            pygame.draw.rect(surface, color, rect, border_radius=8)
            text = self.small_font.render(faction, True, self.text_color)
            surface.blit(text, (rect.x + 12, rect.y + 10))
            self.hit_regions.append({"type": "leader_faction", "name": faction, "rect": rect})
            fx += rect.width + 10

        # Category toggles
        cat_y = panel.y + 80
        for idx, category in enumerate(["base", "unlockable"]):
            rect = pygame.Rect(panel.x + 20 + idx * 140, cat_y, 130, 32)
            color = self.highlight if self.leader_category == category else self.card_bg
            pygame.draw.rect(surface, color, rect, border_radius=8)
            label = "Base" if category == "base" else "Unlockable"
            text = self.small_font.render(label, True, self.text_color)
            surface.blit(text, (rect.x + 10, rect.y + 8))
            self.hit_regions.append({"type": "leader_category", "category": category, "rect": rect})

        leaders = self.leader_data.get(self.leader_faction, {}).get(self.leader_category, [])
        grid_rect = pygame.Rect(panel.x + 20, panel.y + 120, panel.width - 40, panel.height - 160)
        pygame.draw.rect(surface, self.card_bg, grid_rect, border_radius=12)
        cols = 2
        card_w = (grid_rect.width - 30) // cols
        card_h = 200
        for idx, leader in enumerate(leaders):
            col = idx % cols
            row = idx // cols
            rect = pygame.Rect(grid_rect.x + 10 + col * (card_w + 10), grid_rect.y + 10 + row * (card_h + 10), card_w, card_h)
            pygame.draw.rect(surface, self.panel_color, rect, border_radius=10)
            portrait = self.leader_images.get(leader.get("card_id"))
            if portrait:
                surface.blit(portrait, (rect.x + 10, rect.y + 10))
            title = self.small_font.render(leader["name"], True, self.highlight)
            text_x = rect.x + 10 + (portrait.get_width() + 12 if portrait else 0)
            surface.blit(title, (text_x, rect.y + 12))
            ability = leader.get("ability_desc") or leader.get("ability", "")
            y = self._render_wrapped(surface, ability, (text_x, rect.y + 42), card_w - (text_x - rect.x) - 12, self.small_font, self.text_color)
            notes = LEADER_NOTES.get(leader["name"], {})
            timing = notes.get("timing", "")
            synergy = notes.get("synergy", "")
            self._render_wrapped(surface, f"Timing: {timing}", (text_x, y + 10), card_w - (text_x - rect.x) - 12, self.small_font, self.muted_color)
            self._render_wrapped(surface, f"Synergy: {synergy}", (text_x, y + 46), card_w - (text_x - rect.x) - 12, self.small_font, self.muted_color)

    def _draw_ability_tab(self, surface):
        panel = pygame.Rect(50, 150, self.width - 100, self.height - 190)
        pygame.draw.rect(surface, self.panel_color, panel, border_radius=18)

        search_rect = pygame.Rect(panel.x + 20, panel.y + 20, 260, 32)
        pygame.draw.rect(surface, self.card_bg, search_rect, border_radius=8)
        label = self.small_font.render(f"Search: {self.ability_search}", True, self.text_color)
        surface.blit(label, (search_rect.x + 10, search_rect.y + 7))
        self.hit_regions.append({"type": "input", "tab_type": "abilities", "field": "search", "rect": search_rect})

        # Alphabet filter
        letters = ["All"] + list(string.ascii_uppercase)
        lx = search_rect.right + 20
        ly = panel.y + 20
        for letter in letters:
            rect = pygame.Rect(lx, ly, 32, 32)
            color = self.highlight if self.ability_letter == letter else self.card_bg
            pygame.draw.rect(surface, color, rect, border_radius=6)
            text = self.small_font.render(letter[0], True, self.text_color)
            surface.blit(text, (rect.x + 8, rect.y + 6))
            self.hit_regions.append({"type": "ability_letter", "letter": letter, "rect": rect})
            lx += 36

        list_rect = pygame.Rect(panel.x + 20, panel.y + 70, panel.width - 40, panel.height - 90)
        pygame.draw.rect(surface, self.card_bg, list_rect, border_radius=12)
        filtered = self._filter_abilities()
        total_height = len(filtered) * 130
        view_height = list_rect.height - 20
        max_offset = max(0, total_height - view_height)
        offset = min(self.scroll_offsets.get(self.active_tab, 0), max_offset)
        self.scroll_offsets[self.active_tab] = offset
        clip = surface.get_clip()
        inner_clip = list_rect.inflate(-10, -10)
        surface.set_clip(inner_clip)
        y = list_rect.y + 10 - offset
        for ability in filtered:
            row_rect = pygame.Rect(list_rect.x + 10, y, list_rect.width - 20, 120)
            pygame.draw.rect(surface, self.panel_color, row_rect, border_radius=10)
            title = self.small_font.render(ability["name"], True, self.highlight)
            surface.blit(title, (row_rect.x + 10, row_rect.y + 8))
            self._render_wrapped(surface, f"Effect: {ability['effect']}", (row_rect.x + 10, row_rect.y + 34), row_rect.width - 20, self.small_font, self.text_color)
            self._render_wrapped(surface, f"Timing: {ability['timing']}", (row_rect.x + 10, row_rect.y + 60), row_rect.width - 20, self.small_font, self.muted_color)
            self._render_wrapped(surface, f"Synergy: {ability['synergy']}", (row_rect.x + 10, row_rect.y + 86), row_rect.width - 20, self.small_font, self.muted_color)
            y += 130
        surface.set_clip(clip)

    def _draw_card_tab(self, surface):
        panel = pygame.Rect(30, 150, self.width - 60, self.height - 190)
        pygame.draw.rect(surface, self.panel_color, panel, border_radius=18)

        # Faction selectors
        fx = panel.x + 20
        for faction in FACTION_DISPLAY:
            rect = pygame.Rect(fx, panel.y + 20, 140, 36)
            color = self.highlight if faction == self.card_faction else self.card_bg
            pygame.draw.rect(surface, color, rect, border_radius=8)
            text = self.small_font.render(faction, True, self.text_color)
            surface.blit(text, (rect.x + 10, rect.y + 8))
            self.hit_regions.append({"type": "card_faction", "name": faction, "rect": rect})
            fx += rect.width + 8

        # Section toggle
        sections = list(self.card_data.get(self.card_faction, {}).keys())
        sx = panel.x + 20
        sy = panel.y + 70
        for section in sections:
            rect = pygame.Rect(sx, sy, 200, 30)
            color = self.highlight if section == self.card_section else self.card_bg
            pygame.draw.rect(surface, color, rect, border_radius=8)
            text = self.small_font.render(section, True, self.text_color)
            surface.blit(text, (rect.x + 10, rect.y + 6))
            self.hit_regions.append({"type": "card_section", "section": section, "rect": rect})
            sx += rect.width + 10

        # Search box
        search_rect = pygame.Rect(panel.x + 20, sy + 40, 260, 32)
        pygame.draw.rect(surface, self.card_bg, search_rect, border_radius=8)
        label = self.small_font.render(f"Search: {self.card_search}", True, self.text_color)
        surface.blit(label, (search_rect.x + 10, search_rect.y + 7))
        self.hit_regions.append({"type": "input", "tab_type": "cards", "field": "search", "rect": search_rect})

        list_rect = pygame.Rect(panel.x + 20, search_rect.bottom + 10, 360, panel.height - 150)
        detail_rect = pygame.Rect(list_rect.right + 20, list_rect.y, panel.width - list_rect.width - 60, list_rect.height)
        pygame.draw.rect(surface, self.card_bg, list_rect, border_radius=10)
        pygame.draw.rect(surface, self.card_bg, detail_rect, border_radius=10)

        entries = self.card_data.get(self.card_faction, {}).get(self.card_section, [])
        filtered = [entry for entry in entries if self.card_search.lower() in entry["name"].lower()]
        total_height = len(filtered) * 46
        view_height = list_rect.height - 20
        max_offset = max(0, total_height - view_height)
        offset = min(self.scroll_offsets.get(self.active_tab, 0), max_offset)
        self.scroll_offsets[self.active_tab] = offset
        clip = surface.get_clip()
        surface.set_clip(list_rect.inflate(-8, -8))
        y = list_rect.y + 10 - offset
        for entry in filtered:
            row_rect = pygame.Rect(list_rect.x + 8, y, list_rect.width - 16, 40)
            color = self.highlight if self.card_selected == entry else self.panel_color
            pygame.draw.rect(surface, color, row_rect, border_radius=6)
            card_id = entry.get("card_id")
            art = self._get_card_art(card_id, (32, 48))
            text_x = row_rect.x + 10
            if art:
                surface.blit(art, (row_rect.x + 8, row_rect.y - 4))
                text_x = row_rect.x + 8 + art.get_width() + 10
            text = self.small_font.render(entry["name"], True, self.text_color)
            surface.blit(text, (text_x, row_rect.y + 10))
            self.hit_regions.append({"type": "card_entry", "entry": entry, "rect": row_rect})
            y += 46
        surface.set_clip(clip)

        if self.card_selected:
            card_id = self.card_selected.get("card_id")
            art = self._get_card_art(card_id, (220, 330))
            text_x = detail_rect.x + 10
            text_y = detail_rect.y + 10
            clip = surface.get_clip()
            surface.set_clip(detail_rect.inflate(-8, -8))
            if art:
                surface.blit(art, (detail_rect.x + 10, detail_rect.y + 10))
                text_x = detail_rect.x + 10 + art.get_width() + 20
            self._render_wrapped(
                surface,
                self.card_selected["body"],
                (text_x, text_y),
                detail_rect.width - (text_x - detail_rect.x) - 10,
                self.small_font,
                self.text_color,
            )
            surface.set_clip(clip)
        else:
            text = "Select a card entry to view the full rule text."
            self._render_wrapped(surface, text, (detail_rect.x + 10, detail_rect.y + 10), detail_rect.width - 20, self.small_font, self.muted_color)

    def _draw_lore_tab(self, surface):
        panel = pygame.Rect(50, 150, self.width - 100, self.height - 190)
        pygame.draw.rect(surface, self.panel_color, panel, border_radius=18)
        fx = panel.x + 20
        fy = panel.y + 20
        for faction in FACTION_DISPLAY:
            rect = pygame.Rect(fx, fy, 150, 36)
            color = self.highlight if faction == self.lore_faction else self.card_bg
            pygame.draw.rect(surface, color, rect, border_radius=8)
            text = self.small_font.render(faction, True, self.text_color)
            surface.blit(text, (rect.x + 10, rect.y + 8))
            self.hit_regions.append({"type": "lore_faction", "name": faction, "rect": rect})
            fx += rect.width + 8

        info = self.lore_entries.get(self.lore_faction, {})
        rect = pygame.Rect(panel.x + 20, panel.y + 70, panel.width - 40, panel.height - 100)
        pygame.draw.rect(surface, self.card_bg, rect, border_radius=12)
        y = rect.y + 16
        for key in ["Lore", "Signature Strategy"]:
            title = self.small_font.render(key, True, self.highlight)
            surface.blit(title, (rect.x + 16, y))
            y = self._render_wrapped(surface, info.get(key, "No entry in spec."), (rect.x + 16, y + 22), rect.width - 32, self.body_font, self.text_color) + 16

        leaders = self.leader_data.get(self.lore_faction, {})
        for bucket_name, bucket in leaders.items():
            label = "Base Leaders" if bucket_name == "base" else "Unlockables"
            title = self.small_font.render(label, True, self.muted_color)
            surface.blit(title, (rect.x + 16, y))
            y += 22
            for leader in bucket:
                bio = LEADER_NOTES.get(leader["name"], {}).get("synergy", "See leader tab for details.")
                text = f"- {leader['name']}: {bio}"
                y = self._render_wrapped(surface, text, (rect.x + 32, y), rect.width - 48, self.small_font, self.text_color) + 6

    # ---------- Helper methods ----------

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
    ) -> int:
        x, y = pos
        if not text:
            return y
        for line in wrap(text, max(1, width // max(1, font.size("M")[0]))):
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_linesize()
        return y


def run_rules_menu(screen: pygame.Surface):
    viewer = RulesMenuScreen(screen.get_width(), screen.get_height())
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT):
                    pygame.display.toggle_fullscreen()
                    screen = pygame.display.get_surface()
                    viewer.resize(screen.get_width(), screen.get_height())
                    continue
            result = viewer.handle_event(event)
            if result == "back":
                return None
        viewer.draw(screen)
        pygame.display.flip()
        clock.tick(60)
