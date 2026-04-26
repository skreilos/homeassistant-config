#!/usr/bin/env python3
"""Replace entity_id references across repository files using rename mapping.

Usage:
  python3 scripts/replace_entity_ids_in_repo.py \
    --repo /home/stephanprivat/Dokumente/Development/homeassistant-config \
    --map entity_id_rename_map.yaml --apply
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Dict, Iterable


def load_mapping(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    mapping: Dict[str, str] = {}
    in_section = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "entity_id_renames:":
            in_section = True
            continue
        if not in_section:
            continue
        match = re.match(r"^([a-z0-9_]+\.[a-zA-Z0-9_]+):\s+([a-z0-9_]+\.[a-zA-Z0-9_]+)$", line)
        if not match:
            raise ValueError(f"Invalid mapping line: {raw}")
        mapping[match.group(1)] = match.group(2)
    if not mapping:
        raise ValueError("No entity mappings found in map file.")
    return mapping


def iter_target_files(repo: Path, map_path: Path) -> Iterable[Path]:
    for ext in ("*.yaml", "*.yml", "*.md"):
        for path in repo.rglob(ext):
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            if path.resolve() == map_path.resolve():
                continue
            yield path


def replace_in_file(path: Path, mapping: Dict[str, str]) -> int:
    text = path.read_text(encoding="utf-8")
    updated = text
    replacements = 0
    for old_id in sorted(mapping.keys(), key=len, reverse=True):
        new_id = mapping[old_id]
        count = updated.count(old_id)
        if count:
            updated = updated.replace(old_id, new_id)
            replacements += count
    if replacements:
        path.write_text(updated, encoding="utf-8")
    return replacements


def count_in_file(path: Path, mapping: Dict[str, str]) -> int:
    text = path.read_text(encoding="utf-8")
    return sum(text.count(old_id) for old_id in mapping)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to repo root")
    parser.add_argument("--map", required=True, help="Path to entity_id_rename_map.yaml")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates to files. Without this flag, dry-run only.",
    )
    args = parser.parse_args()

    repo = Path(args.repo)
    map_path = Path(args.map)
    if not repo.exists():
        print(f"Repo path not found: {repo}", file=sys.stderr)
        return 2
    if not map_path.exists():
        print(f"Map file not found: {map_path}", file=sys.stderr)
        return 2

    mapping = load_mapping(map_path)
    files = list(iter_target_files(repo, map_path))
    impacted = []
    total_replacements = 0

    for path in files:
        rel = path.relative_to(repo)
        if args.apply:
            count = replace_in_file(path, mapping)
        else:
            count = count_in_file(path, mapping)
        if count:
            impacted.append((str(rel), count))
            total_replacements += count

    mode = "Applied" if args.apply else "Planned"
    print(f"{mode} replacements: {total_replacements}")
    for rel, count in sorted(impacted):
        print(f"- {rel}: {count}")

    if not args.apply:
        print("Dry run only. Use --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
