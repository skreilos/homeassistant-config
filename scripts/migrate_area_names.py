#!/usr/bin/env python3
"""Rename Home Assistant area names in .storage/core.area_registry.

Supports mapping by area_id OR current area name.

Usage:
  python3 scripts/migrate_area_names.py \
    --config-dir "/data/home-assistant" \
    --map "/data/home-assistant/area_rename_map.yaml"

  sudo python3 scripts/migrate_area_names.py \
    --config-dir "/data/home-assistant" \
    --map "/data/home-assistant/area_rename_map.yaml" \
    --apply
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Dict


def load_mapping(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    mapping: Dict[str, str] = {}
    in_section = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "area_name_renames:":
            in_section = True
            continue
        if not in_section:
            continue
        m = re.match(r"^([a-z0-9_]+):\s+(.+)$", line)
        if not m:
            raise ValueError(f"Invalid mapping line: {raw}")
        mapping[m.group(1)] = m.group(2).strip().strip('"')
    if not mapping:
        raise ValueError("No mappings found under area_name_renames.")
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", required=True, help="Home Assistant config dir")
    parser.add_argument("--map", required=True, help="Path to area_rename_map.yaml")
    parser.add_argument("--apply", action="store_true", help="Write changes")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    map_path = Path(args.map)
    area_path = config_dir / ".storage" / "core.area_registry"

    if not map_path.exists():
        print(f"Map file not found: {map_path}", file=sys.stderr)
        return 2
    if not area_path.exists():
        print(f"Area registry not found: {area_path}", file=sys.stderr)
        return 2

    mapping = load_mapping(map_path)
    area_json = json.loads(area_path.read_text(encoding="utf-8"))
    areas = area_json.get("data", {}).get("areas", [])
    if not isinstance(areas, list):
        print("Invalid area registry format.", file=sys.stderr)
        return 2

    planned = []
    for area in areas:
        if not isinstance(area, dict):
            continue
        area_id = area.get("id")
        current_name = area.get("name")
        if not isinstance(area_id, str) or not isinstance(current_name, str):
            continue

        new_name = None
        if area_id in mapping:
            new_name = mapping[area_id]
        elif current_name in mapping:
            new_name = mapping[current_name]

        if new_name and new_name != current_name:
            planned.append((area_id, current_name, new_name))
            area["name"] = new_name

    print(f"Planned area renames: {len(planned)}")
    for area_id, current_name, new_name in planned:
        print(f"- {area_id}: {current_name} -> {new_name}")

    if not args.apply:
        print("Dry run only. Use --apply to write changes.")
        return 0

    backup_path = area_path.with_suffix(area_path.suffix + ".names.bak")
    backup_path.write_text(area_path.read_text(encoding="utf-8"), encoding="utf-8")
    area_path.write_text(json.dumps(area_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Applied changes and created backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
