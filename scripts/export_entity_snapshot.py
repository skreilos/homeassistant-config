#!/usr/bin/env python3
"""Export Home Assistant entity snapshot from .storage registries.

Creates a git-friendly YAML file with all known entities, including area/device
resolution where available.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_registry_map(entries: List[Dict[str, Any]], key: str, value: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in entries:
        k = item.get(key)
        v = item.get(value)
        if isinstance(k, str) and isinstance(v, str):
            result[k] = v
    return result


def yaml_quote(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def dump_yaml_entities(rows: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("generated_by: export_entity_snapshot.py")
    lines.append("entities:")
    for row in rows:
        lines.append(f'  - entity_id: {yaml_quote(row["entity_id"])}')
        lines.append(f'    domain: {yaml_quote(row["domain"])}')
        lines.append(f'    platform: {yaml_quote(row.get("platform"))}')
        lines.append(f'    name: {yaml_quote(row.get("name"))}')
        lines.append(f'    original_name: {yaml_quote(row.get("original_name"))}')
        lines.append(f'    area_id: {yaml_quote(row.get("area_id"))}')
        lines.append(f'    area_name: {yaml_quote(row.get("area_name"))}')
        lines.append(f'    device_id: {yaml_quote(row.get("device_id"))}')
        lines.append(f'    device_name: {yaml_quote(row.get("device_name"))}')
        lines.append(f'    disabled_by: {yaml_quote(row.get("disabled_by"))}')
        lines.append(f'    hidden_by: {yaml_quote(row.get("hidden_by"))}')
        lines.append(f'    has_entity_name: {yaml_quote(row.get("has_entity_name"))}')
        lines.append(f'    original_icon: {yaml_quote(row.get("original_icon"))}')
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        required=True,
        help="Path to Home Assistant config dir (contains .storage).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output YAML path for entity snapshot.",
    )
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    storage_dir = config_dir / ".storage"

    entity_registry = read_json(storage_dir / "core.entity_registry")
    device_registry = read_json(storage_dir / "core.device_registry")
    area_registry = read_json(storage_dir / "core.area_registry")

    entities = entity_registry.get("data", {}).get("entities", [])
    devices = device_registry.get("data", {}).get("devices", [])
    areas = area_registry.get("data", {}).get("areas", [])

    device_name_by_id = parse_registry_map(devices, "id", "name_by_user")
    # fallback to default name if no user-defined name
    for item in devices:
        did = item.get("id")
        if not isinstance(did, str):
            continue
        if did not in device_name_by_id:
            name = item.get("name")
            if isinstance(name, str):
                device_name_by_id[did] = name

    area_name_by_id = parse_registry_map(areas, "id", "name")

    rows: List[Dict[str, Any]] = []
    for entry in entities:
        if not isinstance(entry, dict):
            continue
        entity_id = entry.get("entity_id")
        if not isinstance(entity_id, str) or "." not in entity_id:
            continue
        domain = entity_id.split(".", 1)[0]
        area_id: Optional[str] = entry.get("area_id")
        device_id: Optional[str] = entry.get("device_id")
        row = {
            "entity_id": entity_id,
            "domain": domain,
            "platform": entry.get("platform"),
            "name": entry.get("name"),
            "original_name": entry.get("original_name"),
            "area_id": area_id,
            "area_name": area_name_by_id.get(area_id) if area_id else None,
            "device_id": device_id,
            "device_name": device_name_by_id.get(device_id) if device_id else None,
            "disabled_by": entry.get("disabled_by"),
            "hidden_by": entry.get("hidden_by"),
            "has_entity_name": entry.get("has_entity_name"),
            "original_icon": entry.get("original_icon"),
        }
        rows.append(row)

    rows.sort(key=lambda x: x["entity_id"])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dump_yaml_entities(rows), encoding="utf-8")
    print(f"Exported {len(rows)} entities -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
