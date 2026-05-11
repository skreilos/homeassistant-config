#!/usr/bin/env python3
"""Apply user-given device names to ``.storage/core.device_registry``.

Reads the ``devices:`` section of ``entity_friendly_name_map.yaml`` and patches
``device["name_by_user"]`` accordingly. The device prefix drives the Home
Assistant 2026 friendly-name composition for all child entities that use
``has_entity_name=True``.

Map format::

    devices:
      <device_id>: "Button Zimmer Julian"
      <device_id>: ~          # remove user override, fall back to original name

Usage (server-side, requires sudo to write .storage):

  python3 scripts/apply_device_names.py \
      --devices /data/home-assistant/.storage/core.device_registry \
      --map /data/home-assistant/entity_friendly_name_map.yaml

  sudo python3 scripts/apply_device_names.py \
      --devices /data/home-assistant/.storage/core.device_registry \
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
    device_id: str
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


def load_device_map(path: Path) -> Dict[str, Optional[str]]:
    values: Dict[str, Optional[str]] = {}
    in_devices = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.rstrip()
        line = stripped.strip()
        if not line or line.startswith("#"):
            continue
        if stripped.startswith("devices:"):
            inline = stripped.split("devices:", 1)[1].strip()
            if inline in {"{}", "[]"}:
                in_devices = False
                continue
            in_devices = True
            continue
        if stripped.startswith("entities:"):
            in_devices = False
            continue
        if not in_devices:
            continue
        m = re.match(r"^  ([a-f0-9]{16,}|[A-Za-z0-9_\-:]+):\s*(.*)$", stripped)
        if not m:
            continue
        did = m.group(1)
        raw_val = m.group(2).strip()
        if raw_val in {"", "~", "null", "Null", "NULL"}:
            values[did] = None
        else:
            v = raw_val
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            values[did] = v
    return values


def plan_changes(
    registry: dict, mapping: Dict[str, Optional[str]]
) -> Tuple[List[PlannedChange], int]:
    devices = registry.get("data", {}).get("devices", [])
    if not isinstance(devices, list):
        raise ValueError("Unexpected registry format: data.devices missing or invalid")

    by_id: Dict[str, dict] = {
        entry.get("id"): entry
        for entry in devices
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }

    plan: List[PlannedChange] = []
    not_found = 0
    for did, desired in mapping.items():
        entry = by_id.get(did)
        if entry is None:
            not_found += 1
            continue
        current = entry.get("name_by_user")
        if isinstance(current, str) and current == "":
            current = None
        plan.append(PlannedChange(device_id=did, old=current, new=desired))
    return plan, not_found


def summarize(plan: List[PlannedChange]) -> Dict[str, int]:
    counts = {"set": 0, "update": 0, "clear": 0, "noop": 0}
    for change in plan:
        counts[change.action] += 1
    return counts


def apply_plan(registry: dict, plan: List[PlannedChange]) -> int:
    devices = registry.get("data", {}).get("devices", [])
    by_id = {
        entry.get("id"): entry
        for entry in devices
        if isinstance(entry, dict)
    }
    changed = 0
    for change in plan:
        if change.action == "noop":
            continue
        entry = by_id.get(change.device_id)
        if entry is None:
            continue
        if change.new is None:
            if "name_by_user" in entry:
                entry["name_by_user"] = None
        else:
            entry["name_by_user"] = change.new
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
        "--devices",
        required=True,
        help="Path to .storage/core.device_registry",
    )
    parser.add_argument(
        "--map",
        required=True,
        help="Path to entity_friendly_name_map.yaml (devices: section)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag: dry-run only.",
    )
    args = parser.parse_args()

    registry_path = Path(args.devices)
    map_path = Path(args.map)
    if not registry_path.exists():
        print(f"Devices registry not found: {registry_path}", file=sys.stderr)
        return 2
    if not map_path.exists():
        print(f"Map file not found: {map_path}", file=sys.stderr)
        return 2

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in devices registry: {exc}", file=sys.stderr)
        return 2

    mapping = load_device_map(map_path)
    if not mapping:
        print("No `devices:` entries found in map. Nothing to do.")
        return 0

    plan, not_found = plan_changes(registry, mapping)
    counts = summarize(plan)
    total_changes = counts["set"] + counts["update"] + counts["clear"]

    print(f"Device map entries: {len(mapping)}")
    print(f"Devices not found in registry: {not_found}")
    print(
        "Planned actions: "
        f"set={counts['set']}, update={counts['update']}, clear={counts['clear']}, noop={counts['noop']}"
    )
    for change in [c for c in plan if c.action != "noop"][:50]:
        old = "<none>" if change.old is None else repr(change.old)
        new = "<clear>" if change.new is None else repr(change.new)
        print(f"  [{change.action}] {change.device_id}: {old} -> {new}")
    if total_changes > 50:
        print(f"  ... and {total_changes - 50} more")

    if not args.apply:
        print("Dry run only. Use --apply to write changes.")
        return 0

    changed = apply_plan(registry, plan)
    backup = write_with_backup(registry_path, registry)
    print(f"Applied {changed} changes. Backup written to: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
