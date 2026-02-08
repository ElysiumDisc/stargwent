"""Backup and restore functionality."""

import shutil
from pathlib import Path

from .logging_ import get_backup_folder, log


def create_backup(file_path: Path, force: bool = False) -> Path:
    """
    Create a backup of a file before modification.

    Args:
        file_path: The file to backup
        force: If True, overwrite existing backup. If False (default),
               skip if backup already exists in this session.

    Returns:
        Path to the backup file
    """
    backup_folder = get_backup_folder()
    if not backup_folder:
        raise RuntimeError("Session not started - call start_session() first")

    backup_folder.mkdir(parents=True, exist_ok=True)

    backup_path = backup_folder / file_path.name

    # Skip if backup already exists (preserves original state for batch operations)
    if backup_path.exists() and not force:
        log(f"BACKUP EXISTS: {file_path.name} (keeping original)")
        return backup_path

    if file_path.exists():
        shutil.copy2(file_path, backup_path)
        log(f"BACKUP CREATED: {file_path.name} -> {backup_path}")

    return backup_path


def restore_from_backup(file_path: Path):
    """Restore a file from its backup."""
    backup_folder = get_backup_folder()
    if not backup_folder:
        return False

    backup_path = backup_folder / file_path.name
    if backup_path.exists():
        shutil.copy2(backup_path, file_path)
        log(f"RESTORED: {file_path.name} from backup")
        return True
    return False
