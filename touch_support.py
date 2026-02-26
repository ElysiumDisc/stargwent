"""
Platform detection for web/touch deployment.

Central module used by all other workstreams to determine runtime environment.
"""
import sys

_force_touch = None


def is_web_platform() -> bool:
    """Check if running in browser via Pygbag (Emscripten/WASM)."""
    return sys.platform == "emscripten"


def is_touch_platform() -> bool:
    """Check if touch input should be used (web or forced via desktop testing)."""
    if _force_touch is not None:
        return _force_touch
    return is_web_platform()


def force_touch_mode(enabled: bool) -> None:
    """Force touch mode on/off for desktop testing. Pass None to reset."""
    global _force_touch
    _force_touch = enabled
