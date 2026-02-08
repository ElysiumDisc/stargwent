#!/usr/bin/env python3
"""
Stargwent Content Manager
=========================

A CLI tool for managing Stargwent content, with separate modes for
developers and players.

Usage:
    python scripts/content_manager.py
    python scripts/content_manager.py --dev       # Jump to developer menu
    python scripts/content_manager.py --user      # Jump to user menu
    python scripts/content_manager.py --dry-run   # Preview changes only
    python scripts/content_manager.py --non-interactive  # Use defaults

=== DEVELOPER MODE ===
Modifies game source code directly (cards.py, abilities.py, etc.)
  1. Add Card       5. Placeholders     9. Balance Analyzer
  2. Add Leader     6. Documentation   10. Batch Import
  3. Add Faction    7. Asset Checker   11. Leader Ability Gen
  4. Edit Ability   8. Audio Manager   12. Card Rename/Delete

=== USER MODE ===
Creates content in user_content/ using existing abilities only.
All user content can be freely enabled, disabled, or deleted.
  1. Save Manager       5. Create Faction
  2. Deck Import/Export 6. Import Content Pack
  3. Create Card        7. Export Content Pack
  4. Create Leader      8. Manage User Content
                        9. Validate Content
"""

from content_manager import main

if __name__ == "__main__":
    main()
