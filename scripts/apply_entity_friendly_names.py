#!/usr/bin/env python3
"""Apply friendly-name overrides from ``entity_friendly_name_map.yaml`` to the
Home Assistant entity registry.

For each entry in the map:

- ``entity_id: "Some Name"``  -> sets ``entry["name"]`` in the registry.
- ``entity_id: ~`` (null)     -> removes ``entry["name"]`` so HA falls back to
                                 ``original_name`` + ``device.name_by_user``
                                 (the correct behaviour after a broken sync).

Usage (server-side, requires sudo to write .storage):

  python3 scripts/apply_entity_friendly_names.py \
      --registry /data/home-assistant/.storage/core.entity_registry \
      --map /data/home-assistant/entity_friendly_name_map.yaml

  sudo python3 scripts/apply_entity_friendly_names.py \
      --registry /data/home-assistant/.storage/core.entity_registry \
      --map /data/home-assistant/entity_friendly_name_map.yaml --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class PlannedChange:
    entity_id: str
    old: Optional[str]
    new: Optional[str]

    @property
    def action(self) -> str:
        if self.old == self.new:
            return "noop"
        if self.new is None:
            return "clear"
        if self.old is None:
            return "set"
        return "update"


def load_map(path: Path) -> Dict[str, Optional[str]]:
    """Parse a minimal subset of YAML emitted by audit_entity_names.py.

    Recognised lines (under ``entities:``):
      ``  <entity_id>: ~``
      ``  <entity_id>: null``
      ``  <entity_id>: "<value>"``
      ``  <entity_id>: <value>``

    Lines outside ``entities:`` are ignored.
    """
    values: Dict[str, Optional[str]] = {}
    in_entities = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.rstrip()
        line = stripped.strip()
        if not line or line.startswith("#"):
            continue
        if stripped.startswith("entities:"):
            in_entities = True
            continue
        if stripped.startswith("devices:") or stripped.startswith("device:"):
            in_entities = False
            continue
        if not in_entities:
            continue
        m = re.match(r"^  ([a-z_]+\.[a-zA-Z0-9_]+):\s*(.*)$", stripped)
        if not m:
            continue
        eid = m.group(1)
        raw_val = m.group(2).strip()
        if raw_val in {"", "~", "null", "Null", "NULL"}:
            values[eid] = None
        else:
            stripped_val = raw_val.strip()
            if (stripped_val.startswith('"') and stripped_val.endswith('"')) or (
                stripped_val.startswith("'") and stripped_val.endswith("'")
            ):
                stripped_val = stripped_val[1:-1]
            values[eid] = stripped_val
    if not values:
        raise ValueError(f"No entries parsed from {path}")
    return values


def plan_changes(
    registry: dict, mapping: Dict[str, Optional[str]]
) -> Tuple[List[PlannedChange], int]:
    entities = registry.get("data", {}).get("entities", [])
    if not isinstance(entities, list):
        raise ValueError("Unexpected registry format: data.entities missing or invalid")

    by_id: Dict[str, dict] = {
        entry.get("entity_id"): entry
        for entry in entities
        if isinstance(entry, dict) and isinstance(entry.get("entity_id"), str)
    }

    plan: List[PlannedChange] = []
    not_found = 0
    for eid, desired in mapping.items():
        entry = by_id.get(eid)
        if entry is None:
            not_found += 1
            continue
        current = entry.get("name")
        if isinstance(current, str) and current == "":
            current = None
        plan.append(PlannedChange(entity_id=eid, old=current, new=desired))
    return plan, not_found


def summarize(plan: List[PlannedChange]) -> Dict[str, int]:
    counts = {"set": 0, "update": 0, "clear": 0, "noop": 0}
    for change in plan:
        counts[change.action] += 1
    return counts


def apply_plan(registry: dict, plan: List[PlannedChange]) -> int:
    entities = registry.get("data", {}).get("entities", [])
    by_id = {
        entry.get("entity_id"): entry
        for entry in entities
        if isinstance(entry, dict)
    }
    changed = 0
    for change in plan:
        if change.action == "noop":
            continue
        entry = by_id.get(change.entity_id)
        if entry is None:
            continue
        if change.new is None:
            if "name" in entry:
                entry["name"] = None
        else:
            entry["name"] = change.new
        changed += 1
    return changed


def write_with_backup(registry_path: Path, registry: dict) -> Path:
    suffix = time.strftime("%Y%m%d_%H%M%S")
    backup_path = registry_path.with_suffix(registry_path.suffix + f".bak.{suffix}")
    backup_path.write_text(
        registry_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry", required=True, help="Path to .storage/core.entity_registry"
    )
    parser.add_argument(
        "--map", required=True, help="Path to entity_friendly_name_map.yaml"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag: dry-run only.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on how many changed entries to print in dry-run.",
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

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in registry: {exc}", file=sys.stderr)
        return 2

    mapping = load_map(map_path)
    plan, not_found = plan_changes(registry, mapping)
    counts = summarize(plan)
    total_changes = counts["set"] + counts["update"] + counts["clear"]

    print(f"Map entries: {len(mapping)}")
    print(f"Entities not found in registry (ignored): {not_found}")
    print(
        "Planned actions: "
        f"set={counts['set']}, update={counts['update']}, clear={counts['clear']}, noop={counts['noop']}"
    )

    sample_limit = args.limit if args.limit > 0 else 25
    sample = [c for c in plan if c.action != "noop"][:sample_limit]
    for change in sample:
        old = "<none>" if change.old is None else repr(change.old)
        new = "<clear>" if change.new is None else repr(change.new)
        print(f"  [{change.action}] {change.entity_id}: {old} -> {new}")
    if total_changes > len(sample):
        print(f"  ... and {total_changes - len(sample)} more")

    if not args.apply:
        print("Dry run only. Use --apply to write changes.")
        return 0

    changed = apply_plan(registry, plan)
    backup = write_with_backup(registry_path, registry)
    print(f"Applied {changed} changes. Backup written to: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
