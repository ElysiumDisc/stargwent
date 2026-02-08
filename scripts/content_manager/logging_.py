"""Session logging for the content manager."""

import datetime

from .config import BACKUP_DIR, LOG_FILE

_session_log = []
_session_start = None
_backup_folder = None


def get_backup_folder():
    """Return the current session backup folder."""
    return _backup_folder


def log(message: str):
    """Log a message with timestamp."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    _session_log.append(entry)
    print(f"  {message}")


def start_session():
    """Start a new logging session."""
    global _session_start, _backup_folder, _session_log
    _session_start = datetime.datetime.now()
    _session_log = []
    _backup_folder = BACKUP_DIR / _session_start.strftime("%Y-%m-%d_%H%M%S")

    header = f"\n=== CONTENT MANAGER SESSION: {_session_start.strftime('%Y-%m-%d %H:%M:%S')} ==="
    _session_log.append(header)
    log(f"BACKUP FOLDER: {_backup_folder}")


def save_session_log():
    """Save session log to file."""
    if not _session_log:
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write("\n".join(_session_log) + "\n\n")

    print(f"\nSession log saved to: {LOG_FILE}")
