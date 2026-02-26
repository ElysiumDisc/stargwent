#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# build_web.sh — Build & test Pygbag web version, auto-cleanup junk
#
# Usage:
#   ./build_web.sh          # local dev server (localhost:8000)
#   ./build_web.sh --build  # headless build only (for CI)
# ═══════════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-}"

cleanup_pygbag() {
    echo ""
    echo "═══ Cleaning up Pygbag artifacts ═══"

    # Remove re-encoded audio files (*-pygbag.ogg, *-pygbag.mp3, etc.)
    local count
    count=$(find "$SCRIPT_DIR" -name "*-pygbag.*" -type f | wc -l)
    if [[ "$count" -gt 0 ]]; then
        find "$SCRIPT_DIR" -name "*-pygbag.*" -type f -delete
        echo "  Deleted $count re-encoded audio files"
    fi

    # Remove build cache
    if [[ -d "$SCRIPT_DIR/build/web-cache" ]]; then
        rm -rf "$SCRIPT_DIR/build/web-cache"
        echo "  Deleted build/web-cache/"
    fi

    # Remove generated build output (keep our PWA source files)
    local generated=(
        "$SCRIPT_DIR/build/version.txt"
        "$SCRIPT_DIR/build/web/favicon.png"
        "$SCRIPT_DIR/build/web/index.html"
    )
    for f in "${generated[@]}"; do
        [[ -f "$f" ]] && rm -f "$f"
    done

    # Remove large bundle files
    find "$SCRIPT_DIR/build/web" -maxdepth 1 \( -name "*.apk" -o -name "*.tar.gz" \) -type f -delete 2>/dev/null || true

    echo "  Cleanup complete — only PWA source files remain in build/web/"
}

# Always clean up on exit (Ctrl+C, error, or normal exit)
trap cleanup_pygbag EXIT

# Check pygbag is installed
if ! command -v pygbag &>/dev/null; then
    echo "Error: pygbag not installed. Run: pip install pygbag" >&2
    exit 1
fi

echo "═══ Building Stargwent for Web (Pygbag) ═══"
echo ""

if [[ "$MODE" == "--build" ]]; then
    pygbag --build "$SCRIPT_DIR/main.py"
else
    echo "Starting dev server at http://localhost:8000"
    echo "Press Ctrl+C to stop"
    echo ""
    pygbag "$SCRIPT_DIR/main.py"
fi
