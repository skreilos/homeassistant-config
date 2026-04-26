#!/usr/bin/env python3
"""Audit Lovelace entity references against Home Assistant entity registry.

Usage example:
  python3 scripts/audit_lovelace_entities.py \
    --lovelace "/data/home-assistant/.storage/lovelace.dashboard_tedt" \
    --entity-registry "/data/home-assistant/.storage/core.entity_registry" \
    --rename-map "/data/home-assistant/entity_id_rename_map.yaml"
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ENTITY_RE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


@dataclass
class Finding:
    entity_id: str
    path: str
    suggested_replacement: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lovelace", required=True, help="Path to lovelace dashboard storage file")
    parser.add_argument(
        "--entity-registry",
        required=True,
        help="Path to .storage/core.entity_registry",
    )
    parser.add_argument(
        "--rename-map",
        required=False,
        help="Optional path to entity_id_rename_map.yaml for replacement hints",
    )
    parser.add_argument("--json-out", required=False, help="Optional output path for JSON report")
    return parser.parse_args()


def load_entity_registry(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entities = payload.get("data", {}).get("entities", [])
    return {entry.get("entity_id") for entry in entities if entry.get("entity_id")}


def load_rename_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapping = payload.get("entity_id_renames", {})
    if not isinstance(mapping, dict):
        return {}
    return {str(k): str(v) for k, v in mapping.items()}


def walk(node: Any, path: str = "$") -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            next_path = f"{path}.{key}"
            if key in {"entity", "entity_id"} and isinstance(value, str) and ENTITY_RE.match(value):
                refs.append((value, next_path))
            elif key in {"entities"} and isinstance(value, list):
                for idx, item in enumerate(value):
                    item_path = f"{next_path}[{idx}]"
                    if isinstance(item, str) and ENTITY_RE.match(item):
                        refs.append((item, item_path))
                    else:
                        refs.extend(walk(item, item_path))
            else:
                refs.extend(walk(value, next_path))
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            refs.extend(walk(item, f"{path}[{idx}]"))
    return refs


def main() -> int:
    args = parse_args()
    lovelace_path = Path(args.lovelace)
    registry_path = Path(args.entity_registry)
    rename_map_path = Path(args.rename_map) if args.rename_map else None

    lovelace_data = json.loads(lovelace_path.read_text(encoding="utf-8"))
    existing_entities = load_entity_registry(registry_path)
    rename_map = load_rename_map(rename_map_path)

    refs = walk(lovelace_data)
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for entity_id, path in refs:
        if entity_id in existing_entities:
            continue
        key = (entity_id, path)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                entity_id=entity_id,
                path=path,
                suggested_replacement=rename_map.get(entity_id),
            )
        )

    print(f"Scanned references: {len(refs)}")
    print(f"Missing entities: {len(findings)}")
    if findings:
        print("\nMissing references:")
        for item in findings:
            suffix = f" -> suggest: {item.suggested_replacement}" if item.suggested_replacement else ""
            print(f"- {item.entity_id} ({item.path}){suffix}")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.write_text(
            json.dumps(
                {
                    "scanned_references": len(refs),
                    "missing_count": len(findings),
                    "missing": [
                        {
                            "entity_id": item.entity_id,
                            "path": item.path,
                            "suggested_replacement": item.suggested_replacement,
                        }
                        for item in findings
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote JSON report: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
