#!/usr/bin/env python3
"""Audit Home Assistant config consistency using exported snapshots.

Checks:
- Naming convention drift in entity IDs
- Missing references in active YAML config files
- Legacy area names
- Stale customize keys

Outputs:
- inventory/consistency_audit.json
- inventory/consistency_audit.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


ENTITY_TOKEN_RE = re.compile(
    r"\b(?:light|switch|sensor|binary_sensor|media_player|input_boolean|input_select|scene|automation|cover|person|number|select|button|update|script)\.[a-zA-Z0-9_]+\b"
)

SERVICE_LIKE = {
    "light.turn_on",
    "light.turn_off",
    "light.toggle",
    "switch.toggle",
    "switch.turn_on",
    "switch.turn_off",
    "scene.turn_on",
    "script.turn_on",
    "script.turn_off",
    "media_player.media_play",
    "media_player.media_stop",
    "media_player.media_pause",
    "media_player.media_play_pause",
    "media_player.select_source",
    "media_player.play_media",
    "media_player.join",
    "media_player.unjoin",
    "media_player.volume_set",
    "media_player.volume_up",
    "media_player.volume_down",
    "media_player.shuffle_set",
    "input_select.select_next",
    "input_select.select_previous",
    "input_select.select_option",
    "input_boolean.turn_on",
    "input_boolean.turn_off",
    "input_boolean.toggle",
    "automation.turn_on",
    "automation.turn_off",
    "cover.open_cover",
    "cover.close_cover",
}

ACTIVE_CONFIG_FILES = [
    "configuration.yaml",
    "automations.yaml",
    "scenes.yaml",
    "customize.yaml",
    "input_boolean.yaml",
]

LEGACY_TOKENS = [
    "spielzimmer",
    "kinderschlafzimmer",
    "kinderzimmer",
    "kinderspielzimmer",
    "werktisch",
    "arbeitstisch",
]


def parse_snapshot_entity_ids(path: Path) -> Set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r'entity_id: "([a-z0-9_]+\.[a-zA-Z0-9_]+)"', text))


def parse_area_names(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8")
    return re.findall(r'name: "([^"]+)"', text)


def parse_automation_entities(path: Path) -> Set[str]:
    txt = path.read_text(encoding="utf-8")
    aliases = re.findall(r"^\s*alias:\s*(.+)$", txt, re.M)
    entities = set()
    for alias in aliases:
        slug = re.sub(r"[^a-z0-9]+", "_", alias.lower()).strip("_")
        entities.add(f"automation.{slug}")
    return entities


def collect_missing_references(root: Path, existing: Set[str], automations: Set[str]) -> List[Tuple[str, int, str]]:
    misses: List[Tuple[str, int, str]] = []
    for rel in ACTIVE_CONFIG_FILES:
        p = root / rel
        if not p.exists():
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            # Ignore include lines like `input_boolean: !include input_boolean.yaml`
            if "!include " in line:
                continue
            for tok in ENTITY_TOKEN_RE.findall(line):
                if tok in SERVICE_LIKE:
                    continue
                if tok.startswith("automation."):
                    if tok not in existing and tok not in automations:
                        misses.append((rel, i, tok))
                elif tok not in existing:
                    misses.append((rel, i, tok))
    dedup = []
    seen = set()
    for rel, ln, tok in misses:
        key = (rel, tok)
        if key in seen:
            continue
        seen.add(key)
        dedup.append((rel, ln, tok))
    return dedup


def legacy_entity_ids(existing: Set[str]) -> List[str]:
    return sorted([e for e in existing if any(tok in e for tok in LEGACY_TOKENS)])


def likely_stale_customize_keys(root: Path, existing: Set[str]) -> List[str]:
    p = root / "customize.yaml"
    if not p.exists():
        return []
    keys = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if re.match(r"^[a-z0-9_]+\.[a-zA-Z0-9_]+:\s*$", line.strip()):
            keys.append(line.strip().rstrip(":"))
    return sorted([k for k in keys if k not in existing])


def build_recommendations(missing_refs: List[Tuple[str, int, str]], stale_customize: List[str], area_names: List[str]) -> List[str]:
    recs = []
    if missing_refs:
        recs.append(
            "Fix missing entity references in active files (`automations.yaml`, `scenes.yaml`, `customize.yaml`)."
        )
    if stale_customize:
        recs.append(
            "Update `customize.yaml` keys to current entity IDs from `inventory/entities_snapshot.yaml`."
        )
    dup_julian = [n for n in area_names if n == "Zimmer Julian"]
    if len(dup_julian) > 1:
        recs.append("Consider consolidating duplicate area names (`Zimmer Julian`) into one canonical area.")
    recs.append("Run export scripts after each device/rename change and commit snapshots.")
    return recs


def write_markdown(path: Path, data: Dict) -> None:
    lines: List[str] = []
    lines.append("# Home Assistant Consistency Audit")
    lines.append("")
    lines.append(f"- Entities in snapshot: **{data['summary']['entity_count']}**")
    lines.append(f"- Missing references in active config: **{data['summary']['missing_reference_count']}**")
    lines.append(f"- Legacy entity IDs remaining: **{data['summary']['legacy_entity_id_count']}**")
    lines.append(f"- Stale customize keys: **{data['summary']['stale_customize_count']}**")
    lines.append("")

    lines.append("## Priority Findings")
    for rec in data["recommendations"]:
        lines.append(f"- {rec}")
    lines.append("")

    lines.append("## Missing References (Active Config)")
    for rel, ln, tok in data["missing_references"][:120]:
        lines.append(f"- `{tok}` in `{rel}`")
    if not data["missing_references"]:
        lines.append("- none")
    lines.append("")

    lines.append("## Stale Customize Keys")
    for key in data["stale_customize_keys"]:
        lines.append(f"- `{key}`")
    if not data["stale_customize_keys"]:
        lines.append("- none")
    lines.append("")

    lines.append("## Legacy Entity IDs (Remaining)")
    for eid in data["legacy_entity_ids"][:120]:
        lines.append(f"- `{eid}`")
    if not data["legacy_entity_ids"]:
        lines.append("- none")
    lines.append("")

    lines.append("## Areas")
    for name in data["area_names"]:
        lines.append(f"- `{name}`")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    inv = root / "inventory"
    inv.mkdir(parents=True, exist_ok=True)

    entities_path = inv / "entities_snapshot.yaml"
    areas_path = inv / "areas_snapshot.yaml"
    if not entities_path.exists() or not areas_path.exists():
        raise SystemExit("Missing snapshot files in inventory/. Run export scripts first.")

    existing = parse_snapshot_entity_ids(entities_path)
    area_names = parse_area_names(areas_path)
    automations = parse_automation_entities(root / "automations.yaml")

    missing = collect_missing_references(root, existing, automations)
    legacy = legacy_entity_ids(existing)
    stale_customize = likely_stale_customize_keys(root, existing)
    recommendations = build_recommendations(missing, stale_customize, area_names)

    data = {
        "summary": {
            "entity_count": len(existing),
            "missing_reference_count": len(missing),
            "legacy_entity_id_count": len(legacy),
            "stale_customize_count": len(stale_customize),
        },
        "missing_references": missing,
        "legacy_entity_ids": legacy,
        "stale_customize_keys": stale_customize,
        "area_names": area_names,
        "recommendations": recommendations,
    }

    json_path = inv / "consistency_audit.json"
    md_path = inv / "consistency_audit.md"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(md_path, data)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(
        f"Summary: missing_refs={len(missing)}, stale_customize={len(stale_customize)}, legacy_ids={len(legacy)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
