"""Command-line argument parsing for the content manager."""

import argparse


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Stargwent Content Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dev", action="store_true",
        help="Jump directly to developer menu",
    )
    mode.add_argument(
        "--user", action="store_true",
        help="Jump directly to user/player menu",
    )
    parser.add_argument(
        "--non-interactive", action="store_true",
        help="Use defaults for all prompts (non-interactive mode)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing (show diffs)",
    )
    return parser.parse_args(argv)
