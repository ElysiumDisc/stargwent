#!/usr/bin/env python3
"""
Art Assembler — composites finished card images and resizes art assets from raw art.

Takes raw ComfyUI art + card data from cards.py and automatically assembles:
  - Card images: portrait + faction border + row icon + ability icons + power + name + quote
  - Leader portraits: raw art resized to 200x280 (for leaders only)
  - Leader backgrounds: raw art resized to 3840x2160 (for leaders only)
  - Faction backgrounds: raw_art/faction_bg_*.png resized to 3840x2160
  - Lobby background: raw_art/lobby_background.png resized to 3840x2160

Usage:
    python scripts/card_assembler.py                    # All cards with raw art
    python scripts/card_assembler.py tauri_oneill       # Specific cards
    python scripts/card_assembler.py --faction tauri    # Entire faction
    python scripts/card_assembler.py --no-overwrite     # Skip existing
    python scripts/card_assembler.py --dry-run          # Preview only

Asset structure:
    assets/card_assembler/
        borders/          ← Faction border PNGs (200x280, RGBA with transparent portrait cutout)
        row_icons/        ← Row type icons (close.png, ranged.png, siege.png, agile.png)
        ability_icons/    ← Ability icons (Legendary commander.png, etc.)
    raw_art/              ← Drop ComfyUI portrait PNGs here, named by card_id
    raw_art/faction_bg_*  ← Faction backgrounds (resized to 3840x2160)
    raw_art/lobby_background ← Lobby background (resized to 3840x2160)
"""

import argparse
import json
import sys
import types
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required: pip install Pillow")
    sys.exit(1)


# ── Project paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

ASSEMBLER_DIR = PROJECT_ROOT / "assets" / "card_assembler"
BORDERS_DIR = ASSEMBLER_DIR / "borders"
ROW_ICONS_DIR = ASSEMBLER_DIR / "row_icons"
ABILITY_ICONS_DIR = ASSEMBLER_DIR / "ability_icons"

RAW_ART_DIR = PROJECT_ROOT / "raw_art"
OUTPUT_DIR = PROJECT_ROOT / "assets"
QUOTES_FILE = SCRIPT_DIR / "card_quotes.json"

# ── Card dimensions ────────────────────────────────────────────────────────
CARD_W, CARD_H = 200, 280

# ── Leader / background dimensions ────────────────────────────────────────
LEADER_W, LEADER_H = 200, 280         # leader portrait (same as card)
BG_W, BG_H = 3840, 2160              # leader bg, faction bg, lobby bg (4K)

# ── Layout constants ───────────────────────────────────────────────────────
# Measured from actual border PNGs and finished card images (2026-02-15).
# All borders share the same layout; only the faction bar color differs.
#
# Card structure (top to bottom):
#   y=0-22    Top metallic frame (with transparent rounded corners)
#   y=25-192  Portrait art (visible through border's transparent cutout)
#   y=194-210 Name plate (rarity-colored bar, ~16px tall)
#   y=211-213 Dark transition strip
#   y=214-264 Parchment text box (~51px tall)
#   y=265-279 Bottom metallic frame
#
# Left bar structure (top to bottom):
#   x=10-30   Faction-colored strip (~20px wide) within dark frame
#   y=35-60   Ability icon area (top of bar)
#   y=107-132 Gold circle for row icon (center ~y=120)
#   y=200-275 Power number area (bottom of bar)

# Portrait area — fills the entire top section behind the border frame.
# The border's opaque metallic edges overlay on top, so portrait extends
# to card edges. Only the transparent cutout shows the portrait.
PORTRAIT_RECT = (0, 0, 200, 205)

# Row icon — gold circle on the left faction bar, mid-height
# Gold circle: center (21, 119), spans y=107-131 (~25px tall, 20px wide).
# Icon sized to fully cover the gold circle.
ROW_ICON_CENTER = (21, 119)
ROW_ICON_SIZE = 40          # large enough so circular icons fully cover 20x25 gold circle

# Ability icons — stacked in top-left of bar, above row icon
# Top circle on border: center (21, 33), spans y=20-46 (~28px diameter).
# First icon fully covers this circle; subsequent icons stack below without overlap.
ABILITY_X = 21              # center x (centered on faction bar)
ABILITY_Y_START = 30        # first icon center y (covers border circle at y=20-46)
ABILITY_SIZE = 46           # icon diameter — wider, fully covers 28px border circle
ABILITY_SPACING = 50        # vertical gap — clear separation between stacked icons

# Power number — inverted triangle at bottom of the left faction bar
# Measured from reference cards: "4" in Asgard Beam Tech spans y=241-258,
# x=14-26, center at (20, 250). Triangle narrows below y=258.
POWER_CENTER = (20, 250)
POWER_FONT_SIZE = 24

# Card name — faction-colored name plate between portrait and text box
# Measured: lighter visible area at y=200 is x=53-168 (116px) for most borders.
# Using x=55-166 with 2px inner margin to keep text on the lighter background.
NAME_Y = 200                # center y of name plate
NAME_X1, NAME_X2 = 55, 166 # horizontal text bounds (visible name plate area)
NAME_FONT_SIZE_MAX = 13
NAME_FONT_SIZE_MIN = 7

# Flavor text — parchment text box at the bottom
# Measured: parchment color at y=215-264, x=15-184
# Usable text area is inset from the left bar (~x=50) to right frame (~x=182)
TEXT_Y = 217                # top of usable text area
TEXT_BOTTOM = 262           # bottom of usable text area
TEXT_X1, TEXT_X2 = 50, 182  # horizontal text bounds
TEXT_FONT_SIZE = 13

# Name plate rectangle — visible colored bar to be recolored by rarity
NAME_PLATE_X1, NAME_PLATE_Y1 = 43, 194
NAME_PLATE_X2, NAME_PLATE_Y2 = 170, 210

# Rarity colors for name plate (matches unlocks.py / create_placeholders.py)
RARITY_COLORS = {
    'common': (200, 200, 200),
    'rare': (100, 150, 255),
    'epic': (200, 100, 255),
    'legendary': (255, 200, 50),
}


# ── Mappings ───────────────────────────────────────────────────────────────
FACTION_BORDER = {
    "Tau'ri": "tauri-border.png",
    "Goa'uld": "goauld-border.png",
    "Jaffa Rebellion": "jaffa-border.png",
    "Lucian Alliance": "lucian-border.png",
    "Asgard": "asgard-border.png",
    "Neutral": "neutral-border.png",
}

FACTION_PREFIX = {
    "tauri": "Tau'ri",
    "goauld": "Goa'uld",
    "jaffa": "Jaffa Rebellion",
    "lucian": "Lucian Alliance",
    "asgard": "Asgard",
    "neutral": "Neutral",
}

ROW_ICON = {
    "close": "close.png",
    "ranged": "ranged.png",
    "siege": "siege.png",
    "agile": "agile.png",
}

ABILITY_ICON = {
    "Legendary Commander": "Legendary commander.png",
    "Tactical Formation": "Tactical formations.png",
    "Gate Reinforcement": "Gate Reinforcement.png",
    "Deep Cover Agent": "Deep Cover Agent.png",
    "Medical Evac": "Medical Evac.png",
    "Command Network": "Command Network.png",
    "Naquadah Overload": "Naquadah Overload.png",
    "Life Force Drain": "Life Force Drain.png",
    "Inspiring Leadership": "Inspiring Leadership.png",
    "Deploy Clones": "Deploy Clones.png",
    "System Lord's Curse": "System Lord's Curse.png",
    "Survival Instinct": "survival instinct.png",
    "Genetic Enhancement": "Genetic Enhancement.png",
}


# ── Load card data (mock pygame to avoid dependency) ───────────────────────
def load_cards():
    """Import ALL_CARDS, UNLOCKABLE_CARDS, and leader IDs with pygame mocked out.

    Returns (ALL_CARDS, rarity_map, leader_ids) where:
      - rarity_map: {card_id: rarity_str} from explicit rarity in unlocks.py
      - leader_ids: set of card_ids that are leaders (from content_registry.py)
    """

    class _MockSurface:
        def __init__(self, *a, **k):
            pass
        def fill(self, *a, **k):
            pass

    class _MockRect:
        def __init__(self, *a, **k):
            pass

    mock_pg = types.ModuleType("pygame")
    mock_pg.Surface = _MockSurface
    mock_pg.Rect = _MockRect
    mock_pg.SRCALPHA = 0
    mock_pg.init = lambda *a, **k: None
    # display_manager calls pygame.key.set_repeat at module level
    mock_key = types.ModuleType("pygame.key")
    mock_key.set_repeat = lambda *a, **k: None
    mock_pg.key = mock_key
    sys.modules["pygame.key"] = mock_key
    # unlocks.py uses pygame.font inside class __init__ (not at module level)
    mock_font = types.ModuleType("pygame.font")
    mock_font.SysFont = lambda *a, **k: None
    mock_pg.font = mock_font
    sys.modules["pygame.font"] = mock_font

    prev = sys.modules.get("pygame")
    sys.modules["pygame"] = mock_pg

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from cards import ALL_CARDS
    from unlocks import UNLOCKABLE_CARDS
    from content_registry import BASE_FACTION_LEADERS, UNLOCKABLE_LEADERS

    # Build rarity lookup from explicit rarity fields only
    rarity_map = {}
    for card_id, data in UNLOCKABLE_CARDS.items():
        if "rarity" in data:
            rarity_map[card_id] = data["rarity"]

    # Collect all leader card_ids
    leader_ids = set()
    for faction_leaders in BASE_FACTION_LEADERS.values():
        for leader in faction_leaders:
            leader_ids.add(leader["card_id"])
    for faction_leaders in UNLOCKABLE_LEADERS.values():
        for leader in faction_leaders:
            leader_ids.add(leader["card_id"])

    if prev is not None:
        sys.modules["pygame"] = prev
    else:
        del sys.modules["pygame"]
    sys.modules.pop("pygame.font", None)

    return ALL_CARDS, rarity_map, leader_ids


# ── Font loading ───────────────────────────────────────────────────────────
_font_cache = {}


def get_font(size):
    """Get a TrueType font, searching project assets then system paths."""
    if size in _font_cache:
        return _font_cache[size]

    candidates = [
        PROJECT_ROOT / "assets" / "font.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
    ]
    # Try pygame bundled font from venv
    for pyver in ["3.13", "3.12", "3.11", "3.10"]:
        candidates.append(
            PROJECT_ROOT / "venv" / "lib" / f"python{pyver}"
            / "site-packages" / "pygame" / "freesansbold.ttf"
        )

    for path in candidates:
        if path.exists():
            try:
                font = ImageFont.truetype(str(path), size)
                _font_cache[size] = font
                return font
            except (OSError, IOError):
                continue

    # Last resort: Pillow default bitmap font (won't respect size)
    print(f"  [WARN] No TrueType font found, using Pillow default")
    font = ImageFont.load_default()
    _font_cache[size] = font
    return font


# ── Image utilities ────────────────────────────────────────────────────────
# Placeholder images from create_placeholders.py are small solid-color
# rectangles (~2-5KB). Real card art with photo composites are 20KB+.
PLACEHOLDER_SIZE_THRESHOLD = 15_000  # bytes


def has_raw_art(card_id):
    """Check if raw portrait art exists for a card."""
    return any(
        (RAW_ART_DIR / f"{card_id}{ext}").exists()
        for ext in (".png", ".jpg", ".jpeg", ".webp")
    )


def is_real_art(card_id):
    """Check if the existing asset is real art (not a placeholder)."""
    asset_path = OUTPUT_DIR / f"{card_id}.png"
    if not asset_path.exists():
        return False
    return asset_path.stat().st_size > PLACEHOLDER_SIZE_THRESHOLD


def card_status(card_id):
    """Classify a card: 'done', 'ready', or 'needs_art'."""
    if is_real_art(card_id):
        return "done"
    if has_raw_art(card_id):
        return "ready"
    return "needs_art"


REPORT_FILE = PROJECT_ROOT / "card_status.txt"


def build_status_report(all_cards):
    """Build per-faction status report. Returns (report_string, totals_dict, faction_needs)."""
    from datetime import datetime

    lines = []
    lines.append(f"Stargwent Card Art Status — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    # Group by faction
    factions = {}
    for cid, card in all_cards.items():
        factions.setdefault(card.faction, []).append(cid)

    faction_order = [
        "Tau'ri", "Goa'uld", "Jaffa Rebellion",
        "Lucian Alliance", "Asgard", "Neutral",
    ]

    totals = {"done": 0, "ready": 0, "needs_art": 0}
    faction_needs = {}  # faction -> count needing art

    lines.append(f"\n{'Faction':<20s} {'Done':>6s} {'Ready':>6s} {'Need':>6s} {'Total':>6s}")
    lines.append("-" * 50)

    all_factions = faction_order + [f for f in factions if f not in faction_order]

    for faction in all_factions:
        cards = factions.get(faction, [])
        if not cards:
            continue
        counts = {"done": 0, "ready": 0, "needs_art": 0}
        for cid in cards:
            status = card_status(cid)
            counts[status] += 1
            totals[status] += 1

        if counts["needs_art"] > 0:
            faction_needs[faction] = counts["needs_art"]

        lines.append(
            f"  {faction:<18s} {counts['done']:>6d} {counts['ready']:>6d} "
            f"{counts['needs_art']:>6d} {len(cards):>6d}"
        )

    total = sum(totals.values())
    lines.append("-" * 50)
    lines.append(
        f"  {'TOTAL':<18s} {totals['done']:>6d} {totals['ready']:>6d} "
        f"{totals['needs_art']:>6d} {total:>6d}"
    )

    pct = (totals["done"] / total * 100) if total else 0
    lines.append(f"\nProgress: {totals['done']}/{total} cards done ({pct:.0f}%)")

    # Summary sentence
    if totals["needs_art"] > 0:
        need_parts = [f"{count} {name}" for name, count in faction_needs.items()]
        lines.append(f"{totals['needs_art']} cards still need art: {', '.join(need_parts)}")
    else:
        lines.append("All cards have real art!")

    # Ready to assemble
    ready = [cid for cid in all_cards if card_status(cid) == "ready"]
    if ready:
        lines.append(f"\nReady to assemble ({len(ready)}):")
        for cid in ready:
            c = all_cards[cid]
            lines.append(f"  {cid:40s} {c.name}")

    # Cards needing art (grouped by faction)
    if totals["needs_art"] > 0:
        lines.append(f"\nCards needing art ({totals['needs_art']}):")
        for faction in all_factions:
            cards = factions.get(faction, [])
            need = [cid for cid in cards if card_status(cid) == "needs_art"]
            if not need:
                continue
            lines.append(f"\n  [{faction}] ({len(need)} cards)")
            for cid in need:
                c = all_cards[cid]
                lines.append(f"    {cid:40s} {c.name}")

    return "\n".join(lines)


def print_status_report(all_cards, write_file=False):
    """Print status report and optionally write to card_status.txt."""
    report = build_status_report(all_cards)
    print(report)

    if write_file:
        REPORT_FILE.write_text(report)
        print(f"\nReport written to: {REPORT_FILE}")


def detect_portrait_area(border_img):
    """Find the portrait cutout in a border PNG.

    Note: These borders have transparent pixels scattered throughout
    (rounded corners, edge feathering) so simple bounding-box detection
    of all transparent pixels gives the wrong result. We always use the
    measured PORTRAIT_RECT constants instead.
    """
    # The borders have transparency at corners and edges, not just the
    # portrait cutout, so auto-detection is unreliable. Return None to
    # fall back to the carefully measured PORTRAIT_RECT constants.
    return None


def center_crop_resize(img, target_w, target_h):
    """Center-crop to match target aspect ratio, then resize with LANCZOS."""
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # Source is wider — crop sides
        new_w = int(src_h * target_ratio)
        offset = (src_w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, src_h))
    elif src_ratio < target_ratio:
        # Source is taller — crop top/bottom
        new_h = int(src_w / target_ratio)
        offset = (src_h - new_h) // 2
        img = img.crop((0, offset, src_w, offset + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def crop_transparent_padding(img):
    """Crop transparent padding from an RGBA image."""
    bbox = img.getbbox()  # bounding box of non-zero alpha pixels
    if bbox:
        return img.crop(bbox)
    return img


def scale_icon(icon_img, target_size):
    """Scale an icon to fit within target_size, preserving aspect ratio."""
    icon_img.thumbnail((target_size, target_size), Image.LANCZOS)
    return icon_img


def paste_centered(canvas, icon, center_x, center_y):
    """Paste an RGBA icon centered at the given point."""
    x = center_x - icon.width // 2
    y = center_y - icon.height // 2
    canvas.paste(icon, (x, y), icon if icon.mode == "RGBA" else None)


def wrap_text(text, font, max_width):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_name(name, max_width, size_max, size_min=4):
    """Shrink font to fit name in max_width; truncate with '...' as last resort.

    Returns (display_text, font).
    """
    for size in range(size_max, size_min - 1, -1):
        font = get_font(size)
        bbox = font.getbbox(name)
        if (bbox[2] - bbox[0]) <= max_width:
            return name, font

    # Still too wide at min size — truncate with ellipsis
    font = get_font(size_min)
    for end in range(len(name) - 1, 0, -1):
        truncated = name[:end].rstrip() + "..."
        bbox = font.getbbox(truncated)
        if (bbox[2] - bbox[0]) <= max_width:
            return truncated, font
    return "...", font


def fit_quote(quote, max_width, max_height, size_max, size_min=5):
    """Shrink font until word-wrapped quote fits within max_width x max_height.

    Returns (lines, font, line_height) or ([], None, 0) if empty.
    """
    for size in range(size_max, size_min - 1, -1):
        font = get_font(size)
        lines = wrap_text(quote, font, max_width)
        sample_bbox = font.getbbox("Ay")
        line_h = sample_bbox[3] - sample_bbox[1] + 2
        total_h = line_h * len(lines)
        if total_h <= max_height:
            return lines, font, line_h

    # At min size still overflows — keep lines that fit, truncate last with '...'
    font = get_font(size_min)
    lines = wrap_text(quote, font, max_width)
    sample_bbox = font.getbbox("Ay")
    line_h = sample_bbox[3] - sample_bbox[1] + 2
    max_lines = max(1, max_height // line_h)
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        for end in range(len(last), 0, -1):
            truncated = last[:end].rstrip() + "..."
            bbox = font.getbbox(truncated)
            if (bbox[2] - bbox[0]) <= max_width:
                lines[max_lines - 1] = truncated
                break
        lines = lines[:max_lines]
    return lines, font, line_h


# ── Main assembly pipeline ─────────────────────────────────────────────────
def assemble_card(card, quotes, border_cache, icon_cache, rarity_map=None):
    """
    Assemble a single finished card image.

    Pipeline:
      1. Load raw portrait art
      2. Crop/resize to fit portrait cutout in border
      3. Paste portrait onto canvas
      4. Alpha-composite faction border on top
      5. Scale & paste row icon into golden circle
      6. Scale & paste ability icon(s) (stacked if multiple)
      7. Render power number in inverted triangle
      7b. Draw rarity-colored name plate overlay (explicit rarity from unlocks.py only)
      8. Render card name on name plate (auto-sized)
      9. Render flavor text in text box (word-wrapped)

    Returns (Image, warnings_list) or (None, errors_list).
    """
    warnings = []
    card_id = card.id

    # 1. Load raw portrait art
    raw_path = None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = RAW_ART_DIR / f"{card_id}{ext}"
        if candidate.exists():
            raw_path = candidate
            break

    if raw_path is None:
        return None, [f"No raw art found: {card_id}"]

    portrait = Image.open(raw_path).convert("RGBA")

    # 2. Load faction border
    border_file = FACTION_BORDER.get(card.faction, "neutral-border.png")
    if card.faction not in FACTION_BORDER:
        warnings.append(f"Unknown faction '{card.faction}', using neutral border")

    border = border_cache.get(border_file)
    if border is None:
        border_path = BORDERS_DIR / border_file
        if border_path.exists():
            border = Image.open(border_path).convert("RGBA")
            if border.size != (CARD_W, CARD_H):
                border = border.resize((CARD_W, CARD_H), Image.LANCZOS)
            border_cache[border_file] = border
        else:
            warnings.append(f"Border not found: {border_file} — assembling without border")
            border = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
            border_cache[border_file] = border

    # 3. Detect portrait area from border transparency (or use defaults)
    portrait_rect = detect_portrait_area(border)
    if portrait_rect is None:
        portrait_rect = PORTRAIT_RECT

    px1, py1, px2, py2 = portrait_rect
    pw, ph = px2 - px1, py2 - py1

    # 4. Create canvas, paste portrait, overlay border
    canvas = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 255))
    fitted_portrait = portrait.resize((pw, ph), Image.LANCZOS)
    canvas.paste(fitted_portrait, (px1, py1))
    canvas = Image.alpha_composite(canvas, border)

    # 5. Row icon
    if card.row in ROW_ICON:
        icon_key = ("row", card.row)
        icon = icon_cache.get(icon_key)
        if icon is None:
            icon_path = ROW_ICONS_DIR / ROW_ICON[card.row]
            if icon_path.exists():
                icon = Image.open(icon_path).convert("RGBA")
                # Crop transparent padding, then force square to fill gold circle
                icon = crop_transparent_padding(icon)
                icon = icon.resize((ROW_ICON_SIZE, ROW_ICON_SIZE), Image.LANCZOS)
                icon_cache[icon_key] = icon
            else:
                warnings.append(f"Row icon not found: {ROW_ICON[card.row]}")
                icon = False  # sentinel
                icon_cache[icon_key] = icon
        if icon and icon is not False:
            paste_centered(canvas, icon, *ROW_ICON_CENTER)

    # 6. Ability icons (stacked vertically)
    if card.ability:
        abilities = [a.strip() for a in card.ability.split(",")]
        y_pos = ABILITY_Y_START
        for ability_name in abilities:
            icon_file = ABILITY_ICON.get(ability_name)
            if not icon_file:
                continue  # No icon for this ability — skip gracefully

            icon_key = ("ability", ability_name)
            icon = icon_cache.get(icon_key)
            if icon is None:
                icon_path = ABILITY_ICONS_DIR / icon_file
                if icon_path.exists():
                    icon = Image.open(icon_path).convert("RGBA")
                    # Crop padding, force square to fill the ability slot
                    icon = crop_transparent_padding(icon)
                    icon = icon.resize((ABILITY_SIZE, ABILITY_SIZE), Image.LANCZOS)
                    icon_cache[icon_key] = icon
                else:
                    warnings.append(f"Ability icon not found: {icon_file}")
                    icon = False
                    icon_cache[icon_key] = icon

            if icon and icon is not False:
                paste_centered(canvas, icon, ABILITY_X, y_pos)
                y_pos += ABILITY_SPACING

    # 7. Power number
    draw = ImageDraw.Draw(canvas)
    if card.power > 0 or card.row not in ("special", "weather"):
        power_font = get_font(POWER_FONT_SIZE)
        power_text = str(card.power)
        bbox = power_font.getbbox(power_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        # Account for bbox origin offset to truly center the glyph
        px = POWER_CENTER[0] - tw // 2 - bbox[0]
        py = POWER_CENTER[1] - th // 2 - bbox[1]
        draw.text((px, py), power_text, fill=(0, 0, 0, 255), font=power_font)

    # 7b. Rarity-colored name plate overlay (only for cards with explicit rarity)
    explicit_rarity = (rarity_map or {}).get(card.id)
    if explicit_rarity and explicit_rarity in RARITY_COLORS:
        rarity_color = RARITY_COLORS[explicit_rarity]
        draw.rectangle(
            [NAME_PLATE_X1, NAME_PLATE_Y1, NAME_PLATE_X2, NAME_PLATE_Y2],
            fill=(*rarity_color, 255),
        )

    # 8. Card name (auto-sized to fit name plate, ellipsis if still too long)
    name_w = NAME_X2 - NAME_X1
    display_name, name_font = fit_name(card.name, name_w, NAME_FONT_SIZE_MAX)
    bbox = name_font.getbbox(display_name)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    nx = NAME_X1 + (name_w - tw) // 2 - bbox[0]
    ny = NAME_Y - th // 2 - bbox[1]
    draw.text((nx, ny), display_name, fill=(0, 0, 0, 255), font=name_font)

    # 9. Flavor text (auto-sized to fit text box, ellipsis if still too long)
    quote = quotes.get(card_id, "")
    if quote:
        text_w = TEXT_X2 - TEXT_X1
        text_h = TEXT_BOTTOM - TEXT_Y
        lines, text_font, line_h = fit_quote(quote, text_w, text_h, TEXT_FONT_SIZE)

        # Center the block vertically within the text box
        total_h = line_h * len(lines)
        ty = TEXT_Y + (text_h - total_h) // 2
        for line in lines:
            bbox = text_font.getbbox(line)
            tw = bbox[2] - bbox[0]
            tx = TEXT_X1 + (text_w - tw) // 2
            draw.text((tx, ty), line, fill=(0, 0, 0, 255), font=text_font)
            ty += line_h

    return canvas, warnings


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    global RAW_ART_DIR, OUTPUT_DIR

    parser = argparse.ArgumentParser(
        description="Assemble finished card images from raw portrait art",
        epilog=(
            "Asset folders:\n"
            f"  Borders:       {BORDERS_DIR}/\n"
            f"  Row icons:     {ROW_ICONS_DIR}/\n"
            f"  Ability icons: {ABILITY_ICONS_DIR}/\n"
            f"  Raw art:       {RAW_ART_DIR}/\n"
            f"  Output:        {OUTPUT_DIR}/\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "card_ids", nargs="*",
        help="Specific card IDs to assemble (default: all with raw art)",
    )
    parser.add_argument(
        "--faction", type=str,
        help="Assemble all cards of a faction (tauri/goauld/jaffa/lucian/asgard/neutral)",
    )
    parser.add_argument(
        "--no-overwrite", action="store_true",
        help="Skip cards that already have finished assets",
    )
    parser.add_argument(
        "--input", type=Path, default=None,
        help=f"Raw portrait art directory (default: {RAW_ART_DIR})",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be assembled without writing files",
    )
    parser.add_argument(
        "--list-missing", action="store_true",
        help="List all cards that have no raw art yet",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show per-faction breakdown: done / ready to assemble / needs art",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Write status report to card_status.txt (implies --status)",
    )
    args = parser.parse_args()

    if args.input:
        RAW_ART_DIR = args.input
    if args.output:
        OUTPUT_DIR = args.output

    # Load card data
    print("Loading card data...")
    all_cards, rarity_map, leader_ids = load_cards()
    print(f"  {len(all_cards)} cards in database")
    print(f"  {len(rarity_map)} cards with explicit rarity")
    print(f"  {len(leader_ids)} leaders")

    # Load quotes
    quotes = {}
    if QUOTES_FILE.exists():
        with open(QUOTES_FILE) as f:
            quotes = json.load(f)
        print(f"  {len(quotes)} card quotes loaded")

    # --status / --report mode
    if args.status or args.report:
        print_status_report(all_cards, write_file=args.report)
        return

    # --list-missing mode
    if args.list_missing:
        missing = [cid for cid in all_cards if not has_raw_art(cid)]
        print(f"\nCards without raw art ({len(missing)}/{len(all_cards)}):")
        for cid in missing:
            c = all_cards[cid]
            print(f"  {cid:40s} {c.name} ({c.faction})")
        return

    # Determine which cards to assemble
    if args.card_ids:
        target_ids = args.card_ids
    elif args.faction:
        faction_name = FACTION_PREFIX.get(args.faction.lower())
        if not faction_name:
            print(f"Unknown faction: {args.faction}")
            print(f"Valid: {', '.join(FACTION_PREFIX.keys())}")
            sys.exit(1)
        target_ids = [
            cid for cid, c in all_cards.items()
            if c.faction == faction_name
        ]
        print(f"Faction '{faction_name}': {len(target_ids)} cards")
    else:
        # All cards that have raw art
        target_ids = [cid for cid in all_cards if has_raw_art(cid)]
        print(f"Found raw art for {len(target_ids)} cards")

    if not target_ids:
        print("\nNo cards to assemble.")
        print(f"Drop raw portrait PNGs (named by card_id) into:\n  {RAW_ART_DIR}/")
        return

    # Verify assembler assets exist
    border_ok = any(BORDERS_DIR.glob("*.png"))
    if not border_ok:
        print(f"\n[WARN] No border PNGs found in {BORDERS_DIR}/")
        print("  Cards will be assembled without borders.")
        print("  Drop faction border PNGs here:")
        for name in FACTION_BORDER.values():
            print(f"    {BORDERS_DIR / name}")
        print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Assembly loop
    border_cache = {}
    icon_cache = {}
    assembled = 0
    skipped = 0
    errors = 0

    for card_id in target_ids:
        card = all_cards.get(card_id)
        if card is None:
            print(f"  [SKIP] Unknown card ID: {card_id}")
            errors += 1
            continue

        output_path = OUTPUT_DIR / f"{card_id}.png"
        if args.no_overwrite and output_path.exists():
            skipped += 1
            continue

        if args.dry_run:
            print(f"  [DRY] {card_id} — {card.name} ({card.faction}, {card.row}, {card.power})")
            if card_id in leader_ids:
                if has_raw_art(f"{card_id}_leader"):
                    print(f"  [DRY] {card_id}_leader.png (leader portrait)")
                if has_raw_art(f"leader_bg_{card_id}"):
                    print(f"  [DRY] leader_bg_{card_id}.png (leader background)")
            assembled += 1
            continue

        result, warnings = assemble_card(card, quotes, border_cache, icon_cache, rarity_map)

        for w in warnings:
            print(f"  [WARN] {card_id}: {w}")

        if result is None:
            errors += 1
            continue

        result.save(output_path, "PNG")
        assembled += 1
        print(f"  [OK] {card_id} -> {output_path.name}")

        # Leader extras: each has its OWN separate raw art file
        if card_id in leader_ids:
            # Leader portrait: raw_art/{card_id}_leader.{ext} -> assets/{card_id}_leader.png
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                leader_raw = RAW_ART_DIR / f"{card_id}_leader{ext}"
                if leader_raw.exists():
                    leader_path = OUTPUT_DIR / f"{card_id}_leader.png"
                    if not (args.no_overwrite and leader_path.exists()):
                        leader_img = Image.open(leader_raw).convert("RGBA")
                        leader_img = leader_img.resize((LEADER_W, LEADER_H), Image.LANCZOS)
                        leader_img.save(leader_path, "PNG")
                        print(f"  [OK] {leader_raw.name} -> {leader_path.name} (leader portrait)")
                    break

            # Leader background: raw_art/leader_bg_{card_id}.{ext} -> assets/leader_bg_{card_id}.png
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                bg_raw = RAW_ART_DIR / f"leader_bg_{card_id}{ext}"
                if bg_raw.exists():
                    bg_path = OUTPUT_DIR / f"leader_bg_{card_id}.png"
                    if not (args.no_overwrite and bg_path.exists()):
                        bg_img = Image.open(bg_raw).convert("RGBA")
                        bg_img = bg_img.resize((BG_W, BG_H), Image.LANCZOS)
                        bg_img.save(bg_path, "PNG")
                        print(f"  [OK] {bg_raw.name} -> {bg_path.name} (leader background)")
                    break

    print(f"\nCards: {assembled} assembled, {skipped} skipped, {errors} errors")

    # ── Background art assembly ───────────────────────────────────────────
    bg_count = 0

    # Faction backgrounds: raw_art/faction_bg_*.{ext} -> assets/faction_bg_*.png
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        for raw_bg in RAW_ART_DIR.glob(f"faction_bg_*{ext}"):
            stem = raw_bg.stem  # e.g. "faction_bg_tauri"
            out_path = OUTPUT_DIR / f"{stem}.png"
            if args.no_overwrite and out_path.exists():
                continue
            if args.dry_run:
                print(f"  [DRY] {stem}.png (faction background)")
            else:
                bg_img = Image.open(raw_bg).convert("RGBA")
                bg_img = bg_img.resize((BG_W, BG_H), Image.LANCZOS)
                bg_img.save(out_path, "PNG")
                print(f"  [OK] {raw_bg.name} -> {out_path.name} (faction background)")
            bg_count += 1

    # Lobby background: raw_art/lobby_background.{ext} -> assets/lobby_background.png
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        lobby_raw = RAW_ART_DIR / f"lobby_background{ext}"
        if lobby_raw.exists():
            out_path = OUTPUT_DIR / "lobby_background.png"
            if args.no_overwrite and out_path.exists():
                break
            if args.dry_run:
                print(f"  [DRY] lobby_background.png")
            else:
                bg_img = Image.open(lobby_raw).convert("RGBA")
                bg_img = bg_img.resize((BG_W, BG_H), Image.LANCZOS)
                bg_img.save(out_path, "PNG")
                print(f"  [OK] {lobby_raw.name} -> lobby_background.png")
            bg_count += 1
            break

    if bg_count:
        print(f"Backgrounds: {bg_count} processed")


if __name__ == "__main__":
    main()
