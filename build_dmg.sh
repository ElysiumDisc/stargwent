#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# build_dmg.sh — Build macOS .dmg via PyInstaller
# Run this on macOS (requires Xcode command-line tools)
# ═══════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

PKG_NAME="stargwent"
VERSION="${1:-}"

# If no version argument provided, read from README.md badge (single source of truth)
if [[ -z "$VERSION" ]]; then
    VERSION="$(sed -n 's/.*badge\/version-\([0-9.]\+\)-.*/\1/p' "$ROOT_DIR/README.md" | head -n1)"
    if [[ -z "$VERSION" ]]; then
        echo "Error: Could not find version in README.md badge" >&2
        echo "Please ensure README.md has: ![Version](https://img.shields.io/badge/version-X.Y.Z-blue)" >&2
        exit 1
    fi
fi

# ── Check prerequisites ──────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is required. Install Python 3.8+ and retry." >&2
    exit 1
fi

if ! python3 -m PyInstaller --version >/dev/null 2>&1; then
    echo "Error: PyInstaller is required. Install with: pip install pyinstaller" >&2
    exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
    echo "Error: hdiutil not found. This script must be run on macOS." >&2
    exit 1
fi

BUILD_ROOT="$ROOT_DIR/builds"
STAGING_ROOT="$BUILD_ROOT/staging"
RELEASE_ROOT="$BUILD_ROOT/releases"
WORK_DIR="$STAGING_ROOT/dmg_build"

echo "=== Building Stargwent .dmg v${VERSION} ==="
mkdir -p "$STAGING_ROOT" "$RELEASE_ROOT"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

# ── Step 1: Generate .icns icon from PNG ─────────────────────────
echo "[1/5] Generating macOS icon..."
ICON_SOURCE="$ROOT_DIR/assets/tauri_oneill.png"
ICON_ICNS="$WORK_DIR/stargwent.icns"
ICONSET_DIR="$WORK_DIR/stargwent.iconset"

if [[ -f "$ICON_SOURCE" ]]; then
    mkdir -p "$ICONSET_DIR"

    # Try sips (macOS built-in) first, fall back to Pillow
    if command -v sips >/dev/null 2>&1; then
        for SIZE in 16 32 64 128 256 512; do
            sips -z $SIZE $SIZE "$ICON_SOURCE" --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}.png" >/dev/null 2>&1
        done
        # Retina variants
        for SIZE in 16 32 128 256; do
            DOUBLE=$((SIZE * 2))
            sips -z $DOUBLE $DOUBLE "$ICON_SOURCE" --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}@2x.png" >/dev/null 2>&1
        done
        iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS" 2>/dev/null || true
        echo "    Icon generated with sips/iconutil"
    else
        python3 - "$ICON_SOURCE" "$ICONSET_DIR" <<'PY'
import sys
try:
    from PIL import Image
    img = Image.open(sys.argv[1])
    iconset = sys.argv[2]
    for size in [16, 32, 64, 128, 256, 512]:
        resized = img.resize((size, size), Image.LANCZOS)
        resized.save(f"{iconset}/icon_{size}x{size}.png")
    for size in [16, 32, 128, 256]:
        double = size * 2
        resized = img.resize((double, double), Image.LANCZOS)
        resized.save(f"{iconset}/icon_{size}x{size}@2x.png")
except ImportError:
    print("    Warning: Pillow not installed for icon generation")
    sys.exit(1)
PY
        if command -v iconutil >/dev/null 2>&1; then
            iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS" 2>/dev/null || true
            echo "    Icon generated with Pillow/iconutil"
        fi
    fi

    if [[ ! -f "$ICON_ICNS" ]]; then
        echo "  Warning: Could not generate .icns — building without custom icon" >&2
        ICON_ICNS=""
    fi
else
    echo "  Warning: Icon source not found at $ICON_SOURCE" >&2
    ICON_ICNS=""
fi

# ── Step 2: Install dependencies ─────────────────────────────────
echo "[2/5] Checking Python dependencies..."
python3 -m pip install --quiet pygame-ce moderngl Pillow 2>/dev/null || true
echo "    Dependencies ready"

# ── Step 3: Run PyInstaller ──────────────────────────────────────
echo "[3/5] Running PyInstaller (this may take a few minutes)..."

ICON_FLAG=""
if [[ -n "$ICON_ICNS" && -f "$ICON_ICNS" ]]; then
    ICON_FLAG="--icon=$ICON_ICNS"
fi

cd "$ROOT_DIR"
python3 -m PyInstaller \
    --onedir \
    --name Stargwent \
    --windowed \
    $ICON_FLAG \
    --add-data "assets:assets" \
    --add-data "shaders:shaders" \
    --add-data "docs:docs" \
    --add-data "user_content:user_content" \
    --hidden-import moderngl \
    --hidden-import glcontext \
    --hidden-import PIL \
    --hidden-import PIL._imaging \
    --hidden-import PIL.ImageDraw \
    --distpath "$WORK_DIR/dist" \
    --workpath "$WORK_DIR/work" \
    --specpath "$WORK_DIR" \
    --noconfirm \
    main.py

echo "    PyInstaller bundle created"

# ── Step 4: Verify .app bundle ───────────────────────────────────
echo "[4/5] Verifying .app bundle..."
APP_BUNDLE="$WORK_DIR/dist/Stargwent.app"
if [[ ! -d "$APP_BUNDLE" ]]; then
    # PyInstaller --onedir on macOS with --windowed creates a .app
    # If it didn't, the bundle is in dist/Stargwent/ as a folder
    BUNDLE_DIR="$WORK_DIR/dist/Stargwent"
    if [[ -d "$BUNDLE_DIR" ]]; then
        echo "    Bundle found at $BUNDLE_DIR (folder mode)"
        APP_BUNDLE=""
    else
        echo "Error: PyInstaller did not produce expected output" >&2
        exit 1
    fi
fi

# ── Step 5: Create .dmg ─────────────────────────────────────────
echo "[5/5] Creating .dmg..."
OUTPUT="$RELEASE_ROOT/Stargwent-${VERSION}-macos.dmg"
rm -f "$OUTPUT"

if [[ -n "$APP_BUNDLE" && -d "$APP_BUNDLE" ]]; then
    # .app bundle — create dmg from it
    hdiutil create \
        -volname "Stargwent" \
        -srcfolder "$APP_BUNDLE" \
        -ov -format UDZO \
        "$OUTPUT" >/dev/null
else
    # Folder bundle — create dmg from dist/Stargwent/
    hdiutil create \
        -volname "Stargwent" \
        -srcfolder "$WORK_DIR/dist/Stargwent" \
        -ov -format UDZO \
        "$OUTPUT" >/dev/null
fi

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo ""
echo "=== Build complete ==="
echo "  Package: $OUTPUT"
echo "  Size:    $SIZE"
echo ""
echo "  Install: Open the .dmg and drag Stargwent to Applications"
echo "  Run:     Open Stargwent from Applications or Launchpad"
