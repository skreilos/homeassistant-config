#!/usr/bin/env python3
"""Batch-rename Home Assistant entity_ids in .storage/core.entity_registry.

Usage:
  python3 scripts/migrate_entity_registry_ids.py \
    --registry /data/home-assistant/.storage/core.entity_registry \
    --map entity_id_rename_map.yaml --apply
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Dict, Tuple


def load_mapping(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    mapping: Dict[str, str] = {}
    inside = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "entity_id_renames:":
            inside = True
            continue
        if not inside:
            continue
        match = re.match(r"^([a-z0-9_]+\.[a-zA-Z0-9_]+):\s+([a-z0-9_]+\.[a-zA-Z0-9_]+)$", line)
        if not match:
            raise ValueError(f"Invalid mapping line: {raw}")
        old_id, new_id = match.group(1), match.group(2)
        mapping[old_id] = new_id
    if not mapping:
        raise ValueError("No entity mappings found in map file.")
    return mapping


def validate_mapping(mapping: Dict[str, str]) -> None:
    for old_id, new_id in mapping.items():
        if old_id == new_id:
            raise ValueError(f"Invalid mapping (same value): {old_id}")


def migrate_registry(registry_path: Path, mapping: Dict[str, str]) -> Tuple[int, dict]:
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    entities = data.get("data", {}).get("entities", [])
    if not isinstance(entities, list):
        raise ValueError("Unexpected registry format: data.entities missing or invalid")

    existing_ids = {entry.get("entity_id") for entry in entities if isinstance(entry, dict)}
    for old_id, new_id in mapping.items():
        if old_id not in existing_ids:
            continue
        mapped_old_ids = set(mapping.keys())
        if new_id in existing_ids and new_id not in mapped_old_ids:
            raise ValueError(
                "Target entity_id already exists and is not being replaced in this mapping: "
                f"{new_id}"
            )

    changed = 0
    for entry in entities:
        if not isinstance(entry, dict):
            continue
        current = entry.get("entity_id")
        if current in mapping:
            entry["entity_id"] = mapping[current]
            changed += 1
    return changed, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, help="Path to core.entity_registry")
    parser.add_argument("--map", required=True, help="Path to entity_id_rename_map.yaml")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes back to registry. Without this flag, dry-run only.",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    map_path = Path(args.map)
    if not registry_path.exists():
        print(f"Registry file not found: {registry_path}", file=sys.stderr)
        return 2
    if not map_path.exists():
        print(f"Map file not found: {map_path}", file=sys.stderr)
        return 2

    mapping = load_mapping(map_path)
    validate_mapping(mapping)

    changed, updated_json = migrate_registry(registry_path, mapping)
    print(f"Planned registry renames: {changed}")
    for old_id, new_id in mapping.items():
        print(f"- {old_id} -> {new_id}")

    if not args.apply:
        print("Dry run only. Use --apply to write changes.")
        return 0

    backup_path = registry_path.with_suffix(registry_path.suffix + ".bak")
    backup_path.write_text(registry_path.read_text(encoding="utf-8"), encoding="utf-8")
    registry_path.write_text(
        json.dumps(updated_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Applied changes and created backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
