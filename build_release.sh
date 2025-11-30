#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VERSION="${1:-}"
FORMAT="${2:-all}"

# If no version argument provided, read from README.md badge (single source of truth)
if [[ -z "$VERSION" ]]; then
    VERSION="$(sed -n 's/.*badge\/version-\([0-9.]\+\)-.*/\1/p' "$SCRIPT_DIR/README.md" | head -n1)"
    if [[ -z "$VERSION" ]]; then
        echo "Error: Could not find version in README.md badge" >&2
        echo "Please ensure README.md has: ![Version](https://img.shields.io/badge/version-X.Y.Z-blue)" >&2
        exit 1
    fi
fi

echo "Building Stargwent v${VERSION} releases..."
echo

case "$FORMAT" in
    deb)
        echo "Building Debian package only..."
        "$SCRIPT_DIR/build_deb.sh" "$VERSION"
        ;;
    appimage)
        echo "Building AppImage only..."
        "$SCRIPT_DIR/build_appimage.sh" "$VERSION"
        ;;
    all)
        echo "Building all release formats..."
        "$SCRIPT_DIR/build_deb.sh" "$VERSION"
        echo
        "$SCRIPT_DIR/build_appimage.sh" "$VERSION"
        ;;
    *)
        echo "Error: Unknown format '$FORMAT'" >&2
        echo "Usage: $0 [VERSION] [deb|appimage|all]" >&2
        echo "  VERSION defaults to version from README.md" >&2
        echo "  FORMAT defaults to 'all'" >&2
        exit 1
        ;;
esac

echo
echo "Build complete! Releases are in builds/releases/"
ls -lh "$SCRIPT_DIR/builds/releases/"
