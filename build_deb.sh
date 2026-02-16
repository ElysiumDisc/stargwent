#!/usr/bin/env bash
set -euo pipefail

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

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Error: dpkg-deb is required to build Debian packages. Install the dpkg tools and retry." >&2
    exit 1
fi

BUILD_ROOT="$ROOT_DIR/builds"
STAGING_ROOT="$BUILD_ROOT/staging"
RELEASE_ROOT="$BUILD_ROOT/releases"
PKG_DIR="$STAGING_ROOT/${PKG_NAME}_${VERSION}"
DATA_DIR="$PKG_DIR/usr/share/$PKG_NAME"
BIN_DIR="$PKG_DIR/usr/bin"
DEBIAN_DIR="$PKG_DIR/DEBIAN"
APPLICATIONS_DIR="$PKG_DIR/usr/share/applications"
PIXMAPS_DIR="$PKG_DIR/usr/share/pixmaps"

echo "=== Building Stargwent .deb v${VERSION} ==="
mkdir -p "$STAGING_ROOT" "$RELEASE_ROOT"
rm -rf "$PKG_DIR"
mkdir -p "$DATA_DIR" "$BIN_DIR" "$DEBIAN_DIR" "$APPLICATIONS_DIR" "$PIXMAPS_DIR"

# ── Copy game files (skip dev/build artifacts) ────────────────
echo "[1/5] Copying game files..."
python3 - "$ROOT_DIR" "$DATA_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
dst = Path(sys.argv[2]).resolve()

skip_names = {
    '.git', 'venv', '__pycache__', '.mypy_cache', '.pytest_cache',
    'build', 'dist', 'builds', 'raw_art', 'backup',
    'build_deb.sh', 'build_appimage.sh', 'build_exe.sh', 'build_dmg.sh', 'build_release.sh',
}
ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '.DS_Store', '*.swp')

for item in src.iterdir():
    if item.name in skip_names:
        continue
    target = dst / item.name
    if item.is_dir():
        shutil.copytree(item, target, dirs_exist_ok=True, ignore=ignore)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
PY

# ── Create bundled venv with all pip dependencies ─────────────
echo "[2/5] Creating bundled Python virtual environment..."
VENV_DIR="$DATA_DIR/.venv"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null 2>&1
"$VENV_DIR/bin/pip" install pygame-ce moderngl Pillow >/dev/null 2>&1
echo "    Installed: pygame-ce, moderngl, Pillow"

# ── Create launcher script ────────────────────────────────────
echo "[3/5] Creating launcher..."
cat <<'EOF' > "$BIN_DIR/$PKG_NAME"
#!/usr/bin/env bash
set -euo pipefail
GAME_DIR="/usr/share/stargwent"
cd "$GAME_DIR"
exec "$GAME_DIR/.venv/bin/python3" main.py "$@"
EOF
chmod 755 "$BIN_DIR/$PKG_NAME"

# ── Control file + desktop entry ──────────────────────────────
echo "[4/5] Writing package metadata..."
cat <<EOF > "$DEBIAN_DIR/control"
Package: $PKG_NAME
Version: $VERSION
Section: games
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.8), libgl1, libsdl2-2.0-0, libsdl2-image-2.0-0, libsdl2-mixer-2.0-0
Description: Stargwent - A Stargate-themed card game
 A strategic card game inspired by Gwent from The Witcher 3,
 set in the Stargate universe. Features 5 factions, 247 cards,
 GPU-accelerated GLSL post-processing (bloom, vignette, distortion),
 LAN multiplayer, draft mode, and a full card unlock system.
 .
 Includes a bundled Python virtual environment with all dependencies.
EOF

# Icon
ICON_SOURCE="$DATA_DIR/assets/tauri_oneill.png"
if [[ -f "$ICON_SOURCE" ]]; then
    install -m 644 "$ICON_SOURCE" "$PIXMAPS_DIR/${PKG_NAME}.png"
else
    echo "  Warning: Icon not found at $ICON_SOURCE" >&2
fi

cat <<EOF > "$APPLICATIONS_DIR/${PKG_NAME}.desktop"
[Desktop Entry]
Type=Application
Name=Stargwent
Comment=Stargate-themed tactical card game
Exec=$PKG_NAME
Icon=$PKG_NAME
Categories=Game;CardGame;
Terminal=false
Keywords=Stargate;Card;Strategy;Game;
EOF

# ── Build .deb ────────────────────────────────────────────────
echo "[5/5] Packaging .deb..."
OUTPUT="$RELEASE_ROOT/Stargwent-${VERSION}-linux-amd64.deb"
dpkg-deb --build --root-owner-group "$PKG_DIR" "$OUTPUT" >/dev/null

SIZE=$(du -h "$OUTPUT" | cut -f1)
echo ""
echo "=== Build complete ==="
echo "  Package: $OUTPUT"
echo "  Size:    $SIZE"
echo ""
echo "  Install:   sudo dpkg -i $OUTPUT"
echo "  Uninstall: sudo dpkg -r $PKG_NAME"
echo "  Run:       stargwent"
