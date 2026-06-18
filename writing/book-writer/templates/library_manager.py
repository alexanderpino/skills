#!/usr/bin/env python3
"""
library_manager.py — operations on the persistent writer's library.

The library lives at ~/library/ (or wherever LIBRARY_ROOT points) and holds
worlds, characters, and themes that may be reused across projects.

Operations:

    list <type>                      List all items of a type
    show <type> <slug>               Show an item's metadata
    create <type> <slug>             Create a new item (interactive)
    snapshot <type> <slug> <label>   Create a snapshot of current state
    log <type> <slug>                Show changelog
    link <type> <slug> <project>     Record that a project uses this item
    state <type> <slug>              Show current state summary

Usage from skill workflow:
    python3 library_manager.py list worlds
    python3 library_manager.py show worlds iron-galaxy
    python3 library_manager.py create characters elara-hrafnir
    python3 library_manager.py snapshot worlds iron-galaxy "post-iron-fleet"
    python3 library_manager.py link worlds iron-galaxy iron-fleet

This is deliberately simple. The library is markdown + JSON, edited by hand
or by Claude. The script just maintains the metadata sidecars.
"""

import json
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime


LIBRARY_ROOT = Path(os.environ.get('LIBRARY_ROOT', Path.home() / 'library'))


# --- Types and paths -----------------------------------------------------

VALID_TYPES = {'worlds', 'characters', 'themes', 'personas'}

def type_dir(type_name: str) -> Path:
    if type_name not in VALID_TYPES:
        raise ValueError(f"Unknown type {type_name!r}. "
                         f"Valid: {sorted(VALID_TYPES)}")
    return LIBRARY_ROOT / type_name


def item_dir(type_name: str, slug: str) -> Path:
    return type_dir(type_name) / slug


def metadata_path(type_name: str, slug: str) -> Path:
    """JSON metadata sidecar. Different basename per type."""
    basename = {'worlds': 'world', 'characters': 'character',
                'themes': 'theme', 'personas': 'persona'}[type_name]
    return item_dir(type_name, slug) / f"{basename}.json"


def narrative_path(type_name: str, slug: str) -> Path:
    """The main markdown file with the item's description."""
    basename = {'worlds': 'world', 'characters': 'character',
                'themes': 'theme', 'personas': 'persona'}[type_name]
    return item_dir(type_name, slug) / f"{basename}.md"


# --- Metadata operations -------------------------------------------------

def load_metadata(type_name: str, slug: str) -> dict:
    p = metadata_path(type_name, slug)
    if not p.exists():
        raise FileNotFoundError(f"No metadata at {p}")
    return json.loads(p.read_text(encoding='utf-8'))


def save_metadata(type_name: str, slug: str, data: dict) -> None:
    p = metadata_path(type_name, slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    data['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                 encoding='utf-8')


# --- Commands ------------------------------------------------------------

def cmd_list(type_name: str) -> None:
    """List all items of a type."""
    d = type_dir(type_name)
    if not d.exists():
        print(f"No items in {type_name}.")
        return
    items = sorted(p.name for p in d.iterdir() if p.is_dir())
    if not items:
        print(f"No items in {type_name}.")
        return
    print(f"{type_name.capitalize()} in library:")
    for slug in items:
        try:
            md = load_metadata(type_name, slug)
            name = md.get('name', slug)
            summary = md.get('current_state_summary', '').strip()
            tags = md.get('tags', [])
            tag_str = f" [{', '.join(tags)}]" if tags else ''
            print(f"  {slug}{tag_str}")
            print(f"    {name}")
            if summary:
                # First line only for compact listing.
                first_line = summary.split('\n')[0][:80]
                print(f"    {first_line}")
        except FileNotFoundError:
            print(f"  {slug}  (no metadata)")


def cmd_show(type_name: str, slug: str) -> None:
    """Show full metadata for an item."""
    md = load_metadata(type_name, slug)
    print(json.dumps(md, indent=2, ensure_ascii=False))


def cmd_create(type_name: str, slug: str, name: str = None,
               summary: str = '') -> None:
    """Create a new library item with empty narrative file and basic metadata."""
    if metadata_path(type_name, slug).exists():
        print(f"Already exists: {type_name}/{slug}", file=sys.stderr)
        sys.exit(1)

    d = item_dir(type_name, slug)
    d.mkdir(parents=True, exist_ok=True)
    (d / 'snapshots').mkdir(exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    md = {
        'id': slug,
        'name': name or slug,
        'type': type_name.rstrip('s'),  # singular
        'created': today,
        'last_updated': today,
        'current_state_summary': summary,
        'snapshots': [],
        'used_in': [],
        'tags': []
    }
    save_metadata(type_name, slug, md)

    # Empty narrative file.
    narrative_path(type_name, slug).write_text(
        f"# {name or slug}\n\n", encoding='utf-8'
    )

    # Empty changelog.
    (d / 'changelog.md').write_text(
        f"# Changelog — {name or slug}\n\n"
        f"## {today} — created\n\nInitial creation of library entry.\n",
        encoding='utf-8'
    )

    print(f"Created {type_name}/{slug}")


def cmd_snapshot(type_name: str, slug: str, label: str) -> None:
    """Snapshot the current state of an item.

    Copies the narrative .md file into snapshots/ with a date-prefixed name,
    and adds a snapshot entry to the metadata.
    """
    md = load_metadata(type_name, slug)
    today = datetime.now().strftime('%Y-%m-%d')

    # Slugify label for filename: lowercase, replace non-word chars with -.
    slug_label = ''.join(c if c.isalnum() else '-' for c in label.lower())
    slug_label = '-'.join(p for p in slug_label.split('-') if p)
    snap_filename = f"{today}_{slug_label}.md"
    snap_path = item_dir(type_name, slug) / 'snapshots' / snap_filename

    src = narrative_path(type_name, slug)
    if not src.exists():
        print(f"Source narrative does not exist: {src}", file=sys.stderr)
        sys.exit(1)

    shutil.copy2(src, snap_path)

    md.setdefault('snapshots', []).append({
        'id': slug_label,
        'date': today,
        'label': label,
        'file': f"snapshots/{snap_filename}"
    })
    save_metadata(type_name, slug, md)

    # Append to changelog.
    changelog = item_dir(type_name, slug) / 'changelog.md'
    with changelog.open('a', encoding='utf-8') as f:
        f.write(f"\n## {today} — snapshot: {label}\n\n"
                f"State captured to `{snap_path.relative_to(item_dir(type_name, slug))}`.\n")

    print(f"Snapshot {snap_filename} created for {type_name}/{slug}")


def cmd_log(type_name: str, slug: str) -> None:
    """Print the item's changelog."""
    changelog = item_dir(type_name, slug) / 'changelog.md'
    if not changelog.exists():
        print(f"No changelog at {changelog}", file=sys.stderr)
        sys.exit(1)
    print(changelog.read_text(encoding='utf-8'))


def cmd_link(type_name: str, slug: str, project: str,
             snapshot_id: str = None) -> None:
    """Record that a project is using this library item."""
    md = load_metadata(type_name, slug)
    today = datetime.now().strftime('%Y-%m-%d')

    used_in = md.setdefault('used_in', [])

    # Avoid duplicates: update existing entry if same project.
    existing = next((u for u in used_in if u.get('project') == project), None)
    if existing:
        existing['last_used'] = today
        if snapshot_id:
            existing['as_of_snapshot'] = snapshot_id
    else:
        entry = {
            'project': project,
            'first_used': today,
            'last_used': today
        }
        if snapshot_id:
            entry['as_of_snapshot'] = snapshot_id
        used_in.append(entry)

    save_metadata(type_name, slug, md)
    print(f"Linked {type_name}/{slug} -> project {project}")


def cmd_state(type_name: str, slug: str) -> None:
    """Print the current_state_summary."""
    md = load_metadata(type_name, slug)
    print(md.get('current_state_summary', '').strip() or '(no summary)')


# --- CLI dispatcher ------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        if cmd == 'list' and len(args) == 1:
            cmd_list(args[0])
        elif cmd == 'show' and len(args) == 2:
            cmd_show(args[0], args[1])
        elif cmd == 'create' and len(args) >= 2:
            name = args[2] if len(args) >= 3 else None
            summary = args[3] if len(args) >= 4 else ''
            cmd_create(args[0], args[1], name, summary)
        elif cmd == 'snapshot' and len(args) == 3:
            cmd_snapshot(args[0], args[1], args[2])
        elif cmd == 'log' and len(args) == 2:
            cmd_log(args[0], args[1])
        elif cmd == 'link' and len(args) >= 3:
            snap_id = args[3] if len(args) >= 4 else None
            cmd_link(args[0], args[1], args[2], snap_id)
        elif cmd == 'state' and len(args) == 2:
            cmd_state(args[0], args[1])
        else:
            print(f"Unknown command or wrong args: {cmd} {args}",
                  file=sys.stderr)
            print(__doc__)
            sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
