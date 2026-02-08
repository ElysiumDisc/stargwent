# Stargwent User Content

This folder contains user-created content for Stargwent. You can create custom cards,
leaders, and factions using ONLY existing game mechanics and abilities.

## Directory Structure

```
user_content/
├── enabled.json          # Tracks which content is enabled
├── cards/                # Custom card definitions
│   └── {card_id}/
│       ├── card.json     # Card definition
│       └── card.png      # Card artwork (200x280 recommended)
├── leaders/              # Custom leader definitions
│   └── {leader_id}/
│       ├── leader.json   # Leader definition
│       ├── portrait.png  # Leader portrait (200x280)
│       └── background.png # Leader background (optional)
├── factions/             # Custom faction definitions
│   └── {faction_name}/
│       ├── faction.json  # Faction definition
│       ├── cards/        # Faction's cards
│       ├── leaders/      # Faction's leaders
│       └── faction_bg.png # Faction background (optional)
└── packs/                # Imported content packs
    └── {pack_name}/
        ├── manifest.json # Pack metadata
        └── ...           # Pack content
```

## Creating Content

Use the Content Manager CLI tool to create content:
```bash
python scripts/content_manager.py --user    # Jump directly to user menu
python scripts/content_manager.py           # Or select "User / Player" from role menu
```

User menu options:
- **1. Save Manager** - Backup/restore player saves
- **2. Deck Import/Export** - Share decks via JSON or text
- **3. Create Custom Card** - Step-by-step card creation wizard
- **4. Create Custom Leader** - Step-by-step leader creation wizard
- **5. Create Custom Faction** - Create a complete faction
- **6. Import Content Pack** - Install a .zip content pack
- **7. Export Content Pack** - Package your content as .zip
- **8. Manage User Content** - Enable, disable, or delete content
- **9. Validate User Content** - Check for errors

All user content can be freely enabled, disabled, or completely deleted at any time
without affecting the base game.

## Important Rules

1. **Existing Abilities Only**: You can ONLY use abilities from the game's `Ability` enum.
   You cannot create new game mechanics or abilities.

2. **Valid Rows**: Cards must use one of: `close`, `ranged`, `siege`, `agile`, `special`, `weather`

3. **Valid Rarities**: `common`, `rare`, `epic`, `legendary`

4. **Power Range**: Card power must be 0-20

5. **Faction Passives/Powers**: Must be based on existing faction mechanics

## Card JSON Schema

```json
{
  "card_id": "user_my_card",
  "name": "My Custom Card",
  "faction": "Tau'ri",
  "power": 5,
  "row": "ranged",
  "ability": "Deep Cover Agent",
  "is_unlockable": false,
  "rarity": "common",
  "description": "A custom card I created",
  "author": "YourName"
}
```

## Leader JSON Schema

```json
{
  "card_id": "user_my_leader",
  "name": "My Custom Leader",
  "faction": "Tau'ri",
  "ability": "Custom Ability Name",
  "ability_desc": "Draw 1 card when you pass",
  "ability_type": "DRAW_ON_PASS",
  "ability_params": {"draw_count": 1},
  "is_base": true,
  "author": "YourName"
}
```

## Faction JSON Schema

```json
{
  "name": "My Faction",
  "constant": "FACTION_MYFACTION",
  "primary_color": [100, 150, 200],
  "secondary_color": [80, 120, 160],
  "glow_color": [120, 180, 240],
  "passive_name": "My Passive",
  "passive_type": "EXTRA_DRAW",
  "passive_params": {"count": 1, "rounds": [2, 3]},
  "passive_desc": "Draw 1 extra card at rounds 2 and 3",
  "power_name": "My Power",
  "power_type": "REVIVE_UNITS",
  "power_params": {"count": 2},
  "power_desc": "Revive 2 random units from discard",
  "author": "YourName"
}
```

## Sharing Content

To share your content:
1. Use **Export Content Pack** to create a .zip file
2. Share the .zip file with other players
3. They can use **Import Content Pack** to install it

## Troubleshooting

Run **Validate User Content** to check for:
- Missing image files
- Invalid ability names
- Duplicate card IDs
- Schema validation errors

If content doesn't appear in-game:
1. Check `enabled.json` to ensure content is enabled
2. Restart the game after adding new content
3. Run validation to check for errors
