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

echo "Preparing Debian package for ${PKG_NAME} ${VERSION}..."
mkdir -p "$STAGING_ROOT" "$RELEASE_ROOT"
rm -rf "$PKG_DIR"
mkdir -p "$DATA_DIR" "$BIN_DIR" "$DEBIAN_DIR" "$APPLICATIONS_DIR" "$PIXMAPS_DIR"

python3 - "$ROOT_DIR" "$DATA_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
dst = Path(sys.argv[2]).resolve()

skip_names = {'.git', 'venv', '__pycache__', '.mypy_cache', '.pytest_cache', 'build', 'dist'}
skip_names.add('builds')
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

cat <<'EOF' > "$BIN_DIR/$PKG_NAME"
#!/usr/bin/env bash
set -euo pipefail
GAME_DIR="/usr/share/stargwent"
cd "$GAME_DIR"
exec python3 main.py "$@"
EOF
chmod 755 "$BIN_DIR/$PKG_NAME"

cat <<EOF > "$DEBIAN_DIR/control"
Package: $PKG_NAME
Version: $VERSION
Section: games
Priority: optional
Architecture: all
Maintainer: Stargwent Team
Depends: python3, python3-pygame
Description: Stargate-themed Gwent-style strategy card game built with Pygame.
 Stargwent brings Stargate SG-1 factions, leaders, and abilities into a polished card game experience.
EOF

# Attempt to reuse the game's existing icon for desktop integration
ICON_SOURCE="$DATA_DIR/assets/tauri_oneill.png"
if [[ -f "$ICON_SOURCE" ]]; then
    install -m 644 "$ICON_SOURCE" "$PIXMAPS_DIR/${PKG_NAME}.png"
else
    echo "⚠ Warning: Icon source $ICON_SOURCE not found; desktop entry will reference default icon." >&2
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

OUTPUT="$RELEASE_ROOT/${PKG_NAME}_${VERSION}.deb"
dpkg-deb --build "$PKG_DIR" "$OUTPUT" >/dev/null

echo "Debian package created: $OUTPUT"
