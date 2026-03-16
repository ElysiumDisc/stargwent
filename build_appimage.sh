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

BUILD_ROOT="$ROOT_DIR/builds"
STAGING_ROOT="$BUILD_ROOT/staging"
RELEASE_ROOT="$BUILD_ROOT/releases"
APPDIR="$STAGING_ROOT/${PKG_NAME}.AppDir"

echo "Preparing AppImage for ${PKG_NAME} ${VERSION}..."
mkdir -p "$STAGING_ROOT" "$RELEASE_ROOT"
rm -rf "$APPDIR"
mkdir -p "$APPDIR"

# Download appimagetool if not present
APPIMAGETOOL="$BUILD_ROOT/appimagetool-x86_64.AppImage"
if [[ ! -x "$APPIMAGETOOL" ]]; then
    echo "Downloading appimagetool..."
    wget -q -O "$APPIMAGETOOL" "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
    # Sanity check: downloaded file should be at least 1MB
    if [ $(stat -c%s "$APPIMAGETOOL") -lt 1000000 ]; then
        echo "ERROR: Downloaded appimagetool is suspiciously small"
        exit 1
    fi
fi

# Create AppDir structure
APP_DIR="$APPDIR/usr/share/$PKG_NAME"
mkdir -p "$APP_DIR"
mkdir -p "$APPDIR/usr/bin"

# Copy game files
echo "Copying game files..."
python3 - "$ROOT_DIR" "$APP_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1]).resolve()
dst = Path(sys.argv[2]).resolve()

skip_names = {
    '.git', '.github', '.claude', 'venv', '__pycache__', '.mypy_cache', '.pytest_cache',
    'build', 'dist', 'builds', 'raw_art', 'backup', 'scripts',
    'build_deb.sh', 'build_appimage.sh', 'build_exe.sh', 'build_dmg.sh',
    'build_release.sh', 'build_web.sh', 'metadata.json',
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

# Bundle Python and pygame-ce using python-appimage
PYTHON_APPIMAGE_DIR="$BUILD_ROOT/python-appimage"
PYTHON_VERSION="3.13"

# Check for incomplete download
PYTHON_APPIMAGE="$BUILD_ROOT/python${PYTHON_VERSION}-x86_64.AppImage"
if [[ -f "$PYTHON_APPIMAGE" && ! -s "$PYTHON_APPIMAGE" ]]; then
    echo "Removing incomplete Python AppImage download..."
    rm "$PYTHON_APPIMAGE"
fi

if [[ ! -d "$PYTHON_APPIMAGE_DIR/python" ]]; then
    echo "Setting up Python appimage base..."
    rm -rf "$PYTHON_APPIMAGE_DIR"
    mkdir -p "$PYTHON_APPIMAGE_DIR"

    # Download python-appimage
    if [[ ! -f "$PYTHON_APPIMAGE" ]]; then
        echo "Downloading Python ${PYTHON_VERSION} AppImage..."
        wget -q -O "$PYTHON_APPIMAGE" "https://github.com/niess/python-appimage/releases/download/python3.13/python3.13.9-cp313-cp313-manylinux2014_x86_64.AppImage"
        chmod +x "$PYTHON_APPIMAGE"
        # Sanity check: downloaded file should be at least 10MB
        if [ $(stat -c%s "$PYTHON_APPIMAGE") -lt 10000000 ]; then
            echo "ERROR: Downloaded Python AppImage is suspiciously small"
            exit 1
        fi
    fi

    # Extract Python AppImage
    cd "$PYTHON_APPIMAGE_DIR"
    echo "Extracting Python runtime..."
    "$PYTHON_APPIMAGE" --appimage-extract >/dev/null 2>&1 || { echo "Failed to extract Python AppImage"; exit 1; }
    mv squashfs-root python
    cd "$ROOT_DIR"
fi

# Copy Python runtime to AppDir
echo "Bundling Python runtime..."
cp -r "$PYTHON_APPIMAGE_DIR/python/"* "$APPDIR/"
rm -f "$APPDIR/AppRun"

# Install Python dependencies into the bundled runtime
echo "Installing Python dependencies..."
"$APPDIR/opt/python${PYTHON_VERSION}/bin/python${PYTHON_VERSION}" -m pip install --target="$APPDIR/usr/lib/python3/site-packages" pygame-ce moderngl Pillow >/dev/null 2>&1
echo "    Installed: pygame-ce, moderngl, Pillow"

# Create launcher script
cat <<LAUNCHER > "$APPDIR/AppRun"
#!/bin/bash
SELF=\$(readlink -f "\$0")
HERE=\${SELF%/*}
export PATH="\${HERE}/usr/bin:\${PATH}"
export LD_LIBRARY_PATH="\${HERE}/usr/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export PYTHONPATH="\${HERE}/usr/lib/python3/site-packages\${PYTHONPATH:+:\$PYTHONPATH}"
export PYTHONHOME="\${HERE}/opt/python${PYTHON_VERSION}"

cd "\${HERE}/usr/share/stargwent"
exec "\${HERE}/opt/python${PYTHON_VERSION}/bin/python${PYTHON_VERSION}" main.py "\$@"
LAUNCHER
chmod +x "$APPDIR/AppRun"

# Copy icon
ICON_SOURCE="$APP_DIR/assets/tauri_oneill.png"
if [[ -f "$ICON_SOURCE" ]]; then
    cp "$ICON_SOURCE" "$APPDIR/${PKG_NAME}.png"
    cp "$ICON_SOURCE" "$APPDIR/.DirIcon"
else
    echo "⚠ Warning: Icon not found at $ICON_SOURCE" >&2
fi

# Create desktop file
cat <<EOF > "$APPDIR/${PKG_NAME}.desktop"
[Desktop Entry]
Type=Application
Name=Stargwent
Comment=Stargate-themed tactical card game
Exec=AppRun
Icon=$PKG_NAME
Categories=Game;CardGame;
Terminal=false
Keywords=Stargate;Card;Strategy;Game;
EOF

# Build AppImage
OUTPUT="$RELEASE_ROOT/Stargwent-${VERSION}-linux-x86_64.AppImage"
echo "Building AppImage..."
ARCH=x86_64 "$APPIMAGETOOL" --no-appstream "$APPDIR" "$OUTPUT" >/dev/null 2>&1

echo "AppImage created: $OUTPUT"
