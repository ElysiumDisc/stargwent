#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# build_release.sh — Orchestrate all build targets
#
# Usage:
#   ./build_release.sh                     # build targets for current platform
#   ./build_release.sh "" deb              # .deb only
#   ./build_release.sh "" appimage         # AppImage only
#   ./build_release.sh "" exe              # Windows .exe only
#   ./build_release.sh "" dmg              # macOS .dmg only
#   ./build_release.sh "" linux            # .deb + AppImage
#   ./build_release.sh "" all              # all targets for current platform
#   ./build_release.sh 6.5.0 all          # explicit version
# ═══════════════════════════════════════════════════════════════════

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

# Detect platform
PLATFORM="unknown"
case "$(uname -s)" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
esac

echo "=== Stargwent Release Builder v${VERSION} ==="
echo "  Platform: $PLATFORM"
echo "  Target:   $FORMAT"
echo ""

run_deb() {
    if [[ "$PLATFORM" != "linux" ]]; then
        echo "Warning: .deb builds require Linux (current: $PLATFORM)" >&2
        return 1
    fi
    echo "--- Building .deb ---"
    "$SCRIPT_DIR/build_deb.sh" "$VERSION"
    echo ""
}

run_appimage() {
    if [[ "$PLATFORM" != "linux" ]]; then
        echo "Warning: AppImage builds require Linux (current: $PLATFORM)" >&2
        return 1
    fi
    echo "--- Building AppImage ---"
    "$SCRIPT_DIR/build_appimage.sh" "$VERSION"
    echo ""
}

run_exe() {
    if [[ "$PLATFORM" != "windows" ]]; then
        echo "Warning: .exe builds require Windows/MSYS2/Git Bash (current: $PLATFORM)" >&2
        echo "  Tip: Use GitHub Actions with windows-latest for CI builds" >&2
        return 1
    fi
    echo "--- Building .exe ---"
    "$SCRIPT_DIR/build_exe.sh" "$VERSION"
    echo ""
}

run_dmg() {
    if [[ "$PLATFORM" != "macos" ]]; then
        echo "Warning: .dmg builds require macOS (current: $PLATFORM)" >&2
        echo "  Tip: Use GitHub Actions with macos-latest for CI builds" >&2
        return 1
    fi
    echo "--- Building .dmg ---"
    "$SCRIPT_DIR/build_dmg.sh" "$VERSION"
    echo ""
}

case "$FORMAT" in
    deb)      run_deb ;;
    appimage) run_appimage ;;
    exe)      run_exe ;;
    dmg)      run_dmg ;;
    linux)
        run_deb
        run_appimage
        ;;
    all)
        BUILT=0
        case "$PLATFORM" in
            linux)
                run_deb && BUILT=$((BUILT + 1))
                run_appimage && BUILT=$((BUILT + 1))
                ;;
            windows)
                run_exe && BUILT=$((BUILT + 1))
                ;;
            macos)
                run_dmg && BUILT=$((BUILT + 1))
                ;;
        esac
        if [[ $BUILT -eq 0 ]]; then
            echo "Error: No builds succeeded for platform '$PLATFORM'" >&2
            exit 1
        fi
        ;;
    *)
        echo "Error: Unknown format '$FORMAT'" >&2
        echo "" >&2
        echo "Usage: $0 [VERSION] [FORMAT]" >&2
        echo "" >&2
        echo "  VERSION   Version string (default: from README.md badge)" >&2
        echo "" >&2
        echo "  FORMAT    Build target:" >&2
        echo "    deb       Debian .deb package (Linux only)" >&2
        echo "    appimage  AppImage portable binary (Linux only)" >&2
        echo "    exe       Windows .exe via PyInstaller (Windows only)" >&2
        echo "    dmg       macOS .dmg via PyInstaller (macOS only)" >&2
        echo "    linux     Both .deb and AppImage" >&2
        echo "    all       All targets for current platform (default)" >&2
        exit 1
        ;;
esac

echo "=== Build complete! ==="
mkdir -p "$SCRIPT_DIR/builds/releases"
echo ""
ls -lh "$SCRIPT_DIR/builds/releases/" 2>/dev/null || echo "  (no releases found)"
