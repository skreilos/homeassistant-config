#!/usr/bin/env python3
"""Synchronize Home Assistant entity display names with technical entity_ids.

By default this script updates `name` in `.storage/core.entity_registry`
so the UI display name equals the full technical `entity_id`.

Usage:
  python3 scripts/sync_entity_display_names.py \
    --registry /data/home-assistant/.storage/core.entity_registry

  python3 scripts/sync_entity_display_names.py \
    --registry /data/home-assistant/.storage/core.entity_registry \
    --domains light,switch,binary_sensor --apply
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable


def parse_domains(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    domains = {part.strip() for part in raw.split(",") if part.strip()}
    return domains or None


def iter_entities(data: dict) -> Iterable[dict]:
    entities = data.get("data", {}).get("entities", [])
    if not isinstance(entities, list):
        raise ValueError("Unexpected registry format: data.entities missing or invalid")
    for entry in entities:
        if isinstance(entry, dict):
            yield entry


def should_process(entity_id: str, allowed_domains: set[str] | None) -> bool:
    if "." not in entity_id:
        return False
    domain = entity_id.split(".", 1)[0]
    if allowed_domains is None:
        return True
    return domain in allowed_domains


def sync_display_names(registry: dict, allowed_domains: set[str] | None) -> tuple[int, list[str]]:
    changed = 0
    touched: list[str] = []

    for entry in iter_entities(registry):
        entity_id = entry.get("entity_id")
        if not isinstance(entity_id, str):
            continue
        if not should_process(entity_id, allowed_domains):
            continue

        current_name = entry.get("name")
        if current_name == entity_id:
            continue

        entry["name"] = entity_id
        changed += 1
        touched.append(entity_id)

    return changed, touched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, help="Path to .storage/core.entity_registry")
    parser.add_argument(
        "--domains",
        help="Optional comma-separated domains to limit changes (e.g. light,switch)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag: dry-run only.",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry file not found: {registry_path}", file=sys.stderr)
        return 2

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in registry: {exc}", file=sys.stderr)
        return 2

    allowed_domains = parse_domains(args.domains)
    changed, touched = sync_display_names(registry, allowed_domains)

    mode = "Planned" if not args.apply else "Applied"
    print(f"{mode} display-name sync updates: {changed}")
    for entity_id in touched:
        print(f"- {entity_id}")

    if not args.apply:
        print("Dry run only. Use --apply to write changes.")
        return 0

    backup_path = registry_path.with_suffix(registry_path.suffix + ".bak")
    backup_path.write_text(registry_path.read_text(encoding="utf-8"), encoding="utf-8")
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Applied changes and created backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

