#!/usr/bin/env python3
"""Assign Home Assistant entity areas by entity_id using area names or area IDs.

Usage:
  python3 scripts/migrate_entity_areas.py \
    --config-dir "/data/home-assistant" \
    --map "/data/home-assistant/entity_area_assignment_map.yaml" --apply
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Dict, Tuple


def load_yaml_map(path: Path, root_key: str) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    mapping: Dict[str, str] = {}
    in_section = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == f"{root_key}:":
            in_section = True
            continue
        if not in_section:
            continue
        m = re.match(r"^([a-z0-9_]+\.[a-zA-Z0-9_]+):\s+(.+)$", line)
        if not m:
            raise ValueError(f"Invalid mapping line: {raw}")
        mapping[m.group(1)] = m.group(2).strip().strip('"')
    if not mapping:
        raise ValueError(f"No mappings under {root_key}.")
    return mapping


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", required=True, help="Home Assistant config dir")
    parser.add_argument("--map", required=True, help="Path to entity_area_assignment_map.yaml")
    parser.add_argument("--apply", action="store_true", help="Write changes")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    storage = config_dir / ".storage"
    ent_path = storage / "core.entity_registry"
    area_path = storage / "core.area_registry"

    if not ent_path.exists() or not area_path.exists():
        print("Missing .storage registry files.", file=sys.stderr)
        return 2

    assign = load_yaml_map(Path(args.map), "entity_area_assignments")
    ent = read_json(ent_path)
    area = read_json(area_path)

    areas = area.get("data", {}).get("areas", [])
    area_id_by_name = {a.get("name"): a.get("id") for a in areas if isinstance(a, dict)}
    known_area_ids = {a.get("id") for a in areas if isinstance(a, dict)}

    entities = ent.get("data", {}).get("entities", [])
    ent_by_id = {}
    for e in entities:
        if isinstance(e, dict):
            eid = e.get("entity_id")
            if isinstance(eid, str):
                ent_by_id[eid] = e

    planned: list[Tuple[str, str, str | None]] = []
    for entity_id, area_ref in assign.items():
        # Accept both area names and explicit area IDs for stable automation.
        target_area_id = area_ref if area_ref in known_area_ids else area_id_by_name.get(area_ref)
        if not target_area_id:
            print(f"WARN missing area in registry: {area_ref} (for {entity_id})")
            continue
        entry = ent_by_id.get(entity_id)
        if not entry:
            print(f"WARN missing entity in registry: {entity_id}")
            continue
        before = entry.get("area_id")
        if before != target_area_id:
            planned.append((entity_id, area_ref, before))
            entry["area_id"] = target_area_id

    print(f"Planned area assignments: {len(planned)}")
    for entity_id, area_name, before in planned:
        print(f"- {entity_id}: {before} -> {area_name}")

    if not args.apply:
        print("Dry run only. Use --apply to write changes.")
        return 0

    backup = ent_path.with_suffix(ent_path.suffix + ".areas.bak")
    backup.write_text(ent_path.read_text(encoding="utf-8"), encoding="utf-8")
    ent_path.write_text(json.dumps(ent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Applied changes and created backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
