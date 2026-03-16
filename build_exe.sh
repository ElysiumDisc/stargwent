#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# build_exe.sh — Build Windows .exe via PyInstaller
# Run this on Windows (Git Bash / MSYS2) or in a Windows CI runner
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
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "Error: Python 3 is required. Install Python 3.8+ and retry." >&2
    exit 1
fi

# Use python3 if available, otherwise python (Windows default)
PYTHON="python3"
if ! command -v python3 >/dev/null 2>&1; then
    PYTHON="python"
fi

if ! "$PYTHON" -m PyInstaller --version >/dev/null 2>&1; then
    echo "Error: PyInstaller is required. Install with: pip install pyinstaller" >&2
    exit 1
fi

BUILD_ROOT="$ROOT_DIR/builds"
STAGING_ROOT="$BUILD_ROOT/staging"
RELEASE_ROOT="$BUILD_ROOT/releases"
WORK_DIR="$STAGING_ROOT/exe_build"

echo "=== Building Stargwent .exe v${VERSION} ==="
mkdir -p "$STAGING_ROOT" "$RELEASE_ROOT"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

# ── Step 1: Generate .ico icon from PNG ──────────────────────────
echo "[1/5] Generating Windows icon..."
ICON_SOURCE="$ROOT_DIR/assets/tauri_oneill.png"
ICON_ICO="$WORK_DIR/stargwent.ico"

if [[ -f "$ICON_SOURCE" ]]; then
    "$PYTHON" - "$ICON_SOURCE" "$ICON_ICO" <<'PY'
import sys
try:
    from PIL import Image
    img = Image.open(sys.argv[1])
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(sys.argv[2], sizes=sizes)
    print("    Icon generated with Pillow")
except ImportError:
    print("    Warning: Pillow not installed, skipping .ico generation")
    print("    Install with: pip install Pillow")
    sys.exit(1)
PY
    if [[ $? -ne 0 ]]; then
        echo "  Warning: Could not generate .ico — building without custom icon" >&2
        ICON_ICO=""
    fi
else
    echo "  Warning: Icon source not found at $ICON_SOURCE" >&2
    ICON_ICO=""
fi

# ── Step 2: Install dependencies ─────────────────────────────────
echo "[2/5] Checking Python dependencies..."
"$PYTHON" -m pip install --quiet pygame-ce moderngl Pillow 2>/dev/null || true
echo "    Dependencies ready"

# ── Step 3: Run PyInstaller ──────────────────────────────────────
echo "[3/5] Running PyInstaller (this may take a few minutes)..."

ICON_FLAG=""
if [[ -n "$ICON_ICO" && -f "$ICON_ICO" ]]; then
    ICON_FLAG="--icon=$ICON_ICO"
fi

cd "$ROOT_DIR"
"$PYTHON" -m PyInstaller \
    --onedir \
    --name Stargwent \
    --windowed \
    $ICON_FLAG \
    --add-data "assets;assets" \
    --add-data "shaders;shaders" \
    --add-data "docs;docs" \
    --add-data "user_content;user_content" \
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

# ── Step 4: Copy icon into bundle root ───────────────────────────
echo "[4/5] Finalizing bundle..."
BUNDLE_DIR="$WORK_DIR/dist/Stargwent"
if [[ -f "$ICON_SOURCE" ]]; then
    cp "$ICON_SOURCE" "$BUNDLE_DIR/stargwent.png" 2>/dev/null || true
fi

# ── Step 5: Create distributable zip ─────────────────────────────
echo "[5/5] Packaging..."
OUTPUT="$RELEASE_ROOT/Stargwent-${VERSION}-windows-x64.zip"
rm -f "$OUTPUT"

cd "$WORK_DIR/dist"
if command -v zip >/dev/null 2>&1; then
    zip -r -q "$OUTPUT" Stargwent/
elif command -v 7z >/dev/null 2>&1; then
    7z a -tzip "$OUTPUT" Stargwent/ >/dev/null
else
    # Fallback: Python's zipfile
    "$PYTHON" -c "
import zipfile, pathlib, sys
with zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in pathlib.Path('Stargwent').rglob('*'):
        if f.is_file():
            zf.write(f)
" "$OUTPUT"
fi
cd "$ROOT_DIR"

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo ""
echo "=== Build complete ==="
echo "  Package: $OUTPUT"
echo "  Size:    $SIZE"
echo ""
echo "  Extract the zip and run Stargwent/Stargwent.exe"
