"""Safe file modification with validation and rollback."""

import sys
import json
import difflib
from pathlib import Path

from .config import ROOT
from .backup import create_backup, restore_from_backup
from .logging_ import log
from .color import green, red, yellow


# Global dry-run flag, set by CLI
DRY_RUN = False


def safe_modify_file(file_path: Path, modifier_fn, description: str) -> bool:
    """
    Safely modify a file with full validation.

    1. Creates backup before modification
    2. Applies modifier function
    3. Validates Python syntax (for .py files)
    4. Tests import works (for .py files)
    5. Rolls back on any failure

    In dry-run mode, shows a unified diff without writing.
    """
    # Read original content
    original = file_path.read_text() if file_path.exists() else ""

    try:
        # Apply modification
        modified = modifier_fn(original)

        # Validate Python syntax
        if file_path.suffix == ".py":
            compile(modified, str(file_path), "exec")

        # Dry-run: show diff and return
        if DRY_RUN:
            _show_diff(file_path, original, modified, description)
            return True

        # Create backup
        create_backup(file_path)

        # Write changes
        file_path.write_text(modified)

        # Verify import works for Python files
        if file_path.suffix == ".py":
            module_name = file_path.stem
            # Don't test import for script files
            if file_path.parent == ROOT:
                try:
                    # Clear from sys.modules to force reimport
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    __import__(module_name)
                except Exception as e:
                    raise RuntimeError(f"Import test failed: {e}")

        log(f"MODIFIED: {file_path.name} - {description}")
        return True

    except Exception as e:
        if not DRY_RUN:
            # ROLLBACK
            file_path.write_text(original)
            log(f"ERROR: {e}")
            log(f"ROLLED BACK: {file_path.name}")
        print(f"\n  {red('[ERROR]')} {e}")
        if not DRY_RUN:
            print(f"  Changes rolled back - game is safe!")
        return False


def safe_modify_json(file_path: Path, modifier_fn, description: str) -> bool:
    """Safely modify a JSON file."""
    try:
        if file_path.exists():
            data = json.loads(file_path.read_text())
        else:
            data = {}

        modified_data = modifier_fn(data)

        if DRY_RUN:
            original_text = json.dumps(data, indent=2)
            modified_text = json.dumps(modified_data, indent=2)
            _show_diff(file_path, original_text, modified_text, description)
            return True

        create_backup(file_path)
        file_path.write_text(json.dumps(modified_data, indent=2))
        log(f"MODIFIED: {file_path.name} - {description}")
        return True

    except Exception as e:
        if not DRY_RUN:
            restore_from_backup(file_path)
        log(f"ERROR: {e}")
        print(f"\n  {red('[ERROR]')} {e}")
        return False


def _show_diff(file_path: Path, original: str, modified: str, description: str):
    """Show a unified diff for dry-run mode."""
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=f"a/{file_path.name}",
        tofile=f"b/{file_path.name}",
        n=3,
    )
    diff_text = "".join(diff)
    if diff_text:
        print(f"\n  {yellow('[DRY-RUN]')} {description}")
        print(f"  {file_path.name}:")
        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                print(f"  {green(line)}")
            elif line.startswith("-") and not line.startswith("---"):
                print(f"  {red(line)}")
            else:
                print(f"  {line}")
    else:
        print(f"  {yellow('[DRY-RUN]')} {description} - no changes")
