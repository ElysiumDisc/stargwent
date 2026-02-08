"""User interaction helpers for terminal UI."""

import os
import sys
from typing import List, Optional, Tuple

from .color import cyan, bold

# Global non-interactive flag, set by CLI
NON_INTERACTIVE = False


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """Print a formatted header."""
    width = 50
    print()
    print(cyan("=" * width))
    print(f"  {bold(title)}")
    print(cyan("=" * width))
    print()


def print_box(lines: List[str], width: int = 48):
    """Print text in a box."""
    print("+" + "-" * width + "+")
    for line in lines:
        print(f"| {line:<{width-2}} |")
    print("+" + "-" * width + "+")


def confirm(prompt: str, default: bool = True) -> bool:
    """Ask for yes/no confirmation."""
    if NON_INTERACTIVE:
        return default

    suffix = "[Y/n]" if default else "[y/N]"
    response = input(f"{prompt} {suffix}: ").strip().lower()

    if not response:
        return default
    return response in ("y", "yes")


def get_input(prompt: str, default: str = None, validator=None) -> str:
    """Get validated input from user."""
    while True:
        if default:
            if NON_INTERACTIVE:
                return default
            response = input(f"{prompt} [{default}]: ").strip()
            if not response:
                response = default
        else:
            if NON_INTERACTIVE:
                raise RuntimeError(f"Non-interactive mode: no default for '{prompt}'")
            response = input(f"{prompt}: ").strip()

        if validator:
            error = validator(response)
            if error:
                print(f"  Invalid: {error}")
                if NON_INTERACTIVE:
                    raise RuntimeError(f"Validation failed: {error}")
                continue

        return response


def get_int(prompt: str, min_val: int = None, max_val: int = None, default: int = None) -> int:
    """Get an integer from user."""
    while True:
        if default is not None:
            if NON_INTERACTIVE:
                return default
            response = input(f"{prompt} [{default}]: ").strip()
            if not response:
                return default
        else:
            if NON_INTERACTIVE:
                raise RuntimeError(f"Non-interactive mode: no default for '{prompt}'")
            response = input(f"{prompt}: ").strip()

        try:
            value = int(response)
            if min_val is not None and value < min_val:
                print(f"  Must be at least {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"  Must be at most {max_val}")
                continue
            return value
        except ValueError:
            print("  Please enter a number")


def get_rgb(prompt: str, default: Tuple[int, int, int] = None) -> Tuple[int, int, int]:
    """Get RGB color tuple from user."""
    while True:
        if default:
            if NON_INTERACTIVE:
                return default
            default_str = f"{default[0]},{default[1]},{default[2]}"
            response = input(f"{prompt} (R,G,B) [{default_str}]: ").strip()
            if not response:
                return default
        else:
            if NON_INTERACTIVE:
                raise RuntimeError(f"Non-interactive mode: no default for '{prompt}'")
            response = input(f"{prompt} (R,G,B): ").strip()

        try:
            parts = [int(x.strip()) for x in response.split(",")]
            if len(parts) != 3:
                print("  Enter three values separated by commas (e.g., 100,150,200)")
                continue
            if not all(0 <= x <= 255 for x in parts):
                print("  Each value must be 0-255")
                continue
            return tuple(parts)
        except ValueError:
            print("  Enter three numbers separated by commas (e.g., 100,150,200)")


def select_from_list(prompt: str, options: List[str], allow_custom: bool = False) -> str:
    """Let user select from a list of options."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    if allow_custom:
        print(f"  {len(options) + 1}. (Other - enter custom)")

    if NON_INTERACTIVE:
        return options[0]

    while True:
        response = input("Choice: ").strip()
        try:
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return options[idx]
            if allow_custom and idx == len(options):
                return input("Enter custom value: ").strip()
        except ValueError:
            pass
        print("  Invalid choice")


def progress_bar(current: int, total: int, prefix: str = "", width: int = 30):
    """Display a progress bar in the terminal."""
    if total == 0:
        return
    fraction = current / total
    filled = int(width * fraction)
    bar = "#" * filled + "-" * (width - filled)
    pct = int(fraction * 100)
    end = "\n" if current == total else "\r"
    print(f"  {prefix} [{bar}] {pct}% ({current}/{total})", end=end, flush=True)
