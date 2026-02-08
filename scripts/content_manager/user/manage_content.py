"""User workflow: Manage (enable/disable/delete/validate) user content."""

import shutil
from collections import defaultdict

from ..config import USER_CONTENT_DIR
from ..ui import print_header, get_input, get_int, confirm
from ..color import green, red, yellow
from ..logging_ import log


def user_manage_content():
    """Manage (enable/disable) user content."""
    while True:
        print_header("MANAGE USER CONTENT")

        try:
            from user_content_loader import get_loader
            loader = get_loader()
            content = loader.list_content()
        except Exception as e:
            print(f"[ERROR] Cannot load user content: {e}")
            return

        total = sum(len(v) for v in content.values())
        if total == 0:
            print("No user content found.")
            print("\nUse the Create Custom Card/Leader/Faction options to create content,")
            print("or Import Content Pack to add content from other players.")
            return

        # Display content
        idx = 1
        content_map = {}

        for content_type, items in content.items():
            if items:
                print(f"\n  === {content_type.upper()} ===")
                for item in items:
                    status = green("[x]") if item.get("enabled", True) else "[ ]"
                    print(f"  {status} {idx}. {item['name']} ({item['id']}) by {item.get('author', 'Unknown')}")
                    content_map[idx] = (content_type[:-1], item['id'], item.get('enabled', True))  # Remove 's' from type
                    idx += 1

        print("\n  Actions:")
        print("  E. Enable/disable content (enter number)")
        print("  R. Refresh list")
        print("  D. Delete content")
        print("  0. Back")
        print()

        choice = get_input("Choice", default="0")

        if choice == "0":
            break
        elif choice.upper() == "R":
            continue
        elif choice.upper() == "E":
            num = get_int("Enter content number to toggle", min_val=1, max_val=len(content_map))
            content_type, content_id, is_enabled = content_map[num]
            if is_enabled:
                loader.disable_content(content_type, content_id)
                print(f"[OK] Disabled {content_id}")
            else:
                loader.enable_content(content_type, content_id)
                print(f"[OK] Enabled {content_id}")
        elif choice.upper() == "D":
            num = get_int("Enter content number to delete", min_val=1, max_val=len(content_map))
            content_type, content_id, _ = content_map[num]
            if confirm(f"Delete {content_id}? This cannot be undone!", default=False):
                # Delete the content directory
                if content_type == "card":
                    path = USER_CONTENT_DIR / "cards" / content_id.replace("user_", "")
                elif content_type == "leader":
                    path = USER_CONTENT_DIR / "leaders" / content_id.replace("user_", "")
                elif content_type == "faction":
                    path = USER_CONTENT_DIR / "factions" / content_id.lower().replace(" ", "_")
                elif content_type == "pack":
                    path = USER_CONTENT_DIR / "packs" / content_id.lower().replace(" ", "_")
                else:
                    path = None

                if path and path.exists():
                    shutil.rmtree(path)
                    log(f"Deleted user content: {content_id}")
                    print(f"[OK] Deleted {content_id}")
                else:
                    print(f"[ERROR] Content not found at {path}")
        else:
            # Try to parse as number for quick toggle
            try:
                num = int(choice)
                if num in content_map:
                    content_type, content_id, is_enabled = content_map[num]
                    if is_enabled:
                        loader.disable_content(content_type, content_id)
                        print(f"[OK] Disabled {content_id}")
                    else:
                        loader.enable_content(content_type, content_id)
                        print(f"[OK] Enabled {content_id}")
            except ValueError:
                pass

        input("\nPress Enter to continue...")


def user_validate_content():
    """Validate all user content for errors."""
    print_header("VALIDATE USER CONTENT")

    try:
        from user_content_loader import get_loader
        loader = get_loader()
        errors = loader.validate_all()
    except Exception as e:
        print(f"[ERROR] Cannot validate: {e}")
        return

    if not errors:
        print(green("[OK] All user content is valid!"))
        return

    print(f"Found {len(errors)} validation errors:\n")

    # Group by content
    by_content = defaultdict(list)
    for error in errors:
        key = f"{error.content_type}:{error.content_id}"
        by_content[key].append(error)

    for key, errs in by_content.items():
        content_type, content_id = key.split(":", 1)
        print(f"\n  {content_type.upper()}: {content_id}")
        for err in errs:
            if "Missing" in err.message or "placeholder" in err.message.lower():
                severity = yellow("[WARNING]")
            else:
                severity = red("[ERROR]")
            print(f"    {severity} {err.field}: {err.message}")

    # Summary
    error_count = len([e for e in errors if "Missing" not in e.message])
    warning_count = len(errors) - error_count

    print(f"\n=== SUMMARY ===")
    print(f"  Errors: {error_count}")
    print(f"  Warnings: {warning_count}")

    if error_count > 0:
        print("\n  Fix errors to ensure content loads correctly.")
    else:
        print("\n  Warnings are non-critical - content will still load.")
