#!/usr/bin/env python3
"""Audit Home Assistant entity display names against the project naming standard.

Reads the snapshots produced by ``export_entity_snapshot.py`` and categorizes
all entities into five buckets that drive the friendly-name cleanup:

- A: Helper entities (input_boolean, input_number, input_datetime, scene,
     script, automation, ...) whose user-given ``name`` does not match the
     project naming standard (``<Typ> <Bereich> [<Person>] [<Funktion>]``).
- B: Physical entities (light, switch, sensor, ...) without a user-given
     ``name`` in the entity registry. Display falls back to integration's
     ``original_name``, which is usually technical.
- C: Entities whose ``entity_id`` still contains legacy area tokens.
- D: Entities with a user-given ``name`` that does not start with one of the
     allowed project prefixes (Licht/Schalter/Button/Wecker/Sensor/...).
- E: Entities with both ``name`` and ``original_name`` empty/null. The UI
     shows the raw ``entity_id``.

Outputs:
- inventory/entity_naming_audit.md            (human readable report)
- inventory/entity_naming_audit.json          (machine readable)
- entity_friendly_name_map.template.yaml      (editable map skeleton)

Run from repo root:
    python3 scripts/audit_entity_names.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


HELPER_YAML_FILES: Dict[str, str] = {
    "input_boolean": "input_boolean.yaml",
    "input_number": "input_number.yaml",
    "input_datetime": "input_datetime.yaml",
    "input_select": "input_select.yaml",
    "input_text": "input_text.yaml",
}

HELPER_DOMAINS = {
    "input_boolean",
    "input_number",
    "input_datetime",
    "input_select",
    "input_text",
    "script",
    "automation",
    "scene",
    "timer",
    "counter",
    "schedule",
}

STANDARD_PREFIXES = (
    "Licht",
    "Schalter",
    "Button",
    "Wecker",
    "Routine",
    "Pr\u00e4senz",
    "Benachrichtigung",
    "Szene",
    "Musik",
    "Sound",
    "L\u00fcftung",
    "Energie",
    "Alarm",
    "Sensor",
    "MediaPlayer",
    "Auto",
    "Nachttisch",
    "Bewegung",
    "Multi",
    "Tablet",
    "Kalender",
)

LEGACY_TOKENS = (
    "spielzimmer",
    "kinderschlafzimmer",
    "kinderzimmer",
    "kinderspielzimmer",
    "werktisch",
    "arbeitstisch",
)

DOMAIN_TO_TYP = {
    "light": "Licht",
    "switch": "Schalter",
    "binary_sensor": "Sensor",
    "sensor": "Sensor",
    "button": "Button",
    "media_player": "MediaPlayer",
    "scene": "Szene",
    "automation": "Auto",
    "script": "Routine",
    "input_boolean": "Schalter",
    "input_number": "Wert",
    "input_datetime": "Zeit",
    "input_select": "Auswahl",
    "input_text": "Text",
    "select": "Auswahl",
    "number": "Wert",
    "update": "Update",
}


@dataclass
class Entity:
    entity_id: str
    domain: str
    name: Optional[str]
    original_name: Optional[str]
    area_id: Optional[str]
    area_name: Optional[str]
    device_id: Optional[str]
    device_name: Optional[str]
    has_entity_name: Optional[bool]


@dataclass
class CategoryFinding:
    code: str
    title: str
    description: str
    items: List[Tuple[Entity, Optional[str]]] = field(default_factory=list)


def _strip_quotes(value: str) -> Optional[str]:
    value = value.strip()
    if value == "null":
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value
    return value


def parse_helper_yaml_names(repo_root: Path) -> Dict[str, str]:
    """Return {entity_id: yaml_name} from input_*.yaml repo files.

    HA does not mirror helper YAML `name:` into core.entity_registry, so the
    snapshot would otherwise show null for these. We patch it here.
    """
    names: Dict[str, str] = {}
    for domain, rel_path in HELPER_YAML_FILES.items():
        path = repo_root / rel_path
        if not path.exists():
            continue
        current_object: Optional[str] = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.rstrip()
            if not stripped or stripped.lstrip().startswith("#"):
                continue
            m_obj = re.match(r"^([a-z0-9_]+):\s*$", stripped)
            if m_obj:
                current_object = m_obj.group(1)
                continue
            m_name = re.match(r"^\s+name:\s+(.+?)\s*$", stripped)
            if m_name and current_object:
                value = m_name.group(1).strip().strip('"').strip("'")
                names[f"{domain}.{current_object}"] = value
    return names


def parse_automation_aliases(repo_root: Path) -> Dict[str, str]:
    """Return {automation_id: alias} parsed from automations.yaml."""
    path = repo_root / "automations.yaml"
    if not path.exists():
        return {}
    result: Dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^- id: ", text)[1:]
    for block in blocks:
        first_line, _, rest = block.partition("\n")
        aid_raw = first_line.strip().strip("'").strip('"')
        m_alias = re.search(r"^\s+alias:\s+(.+?)\s*$", rest, re.M)
        if not m_alias:
            continue
        alias = m_alias.group(1).strip().strip('"').strip("'")
        slug = re.sub(r"[^a-z0-9]+", "_", alias.lower()).strip("_")
        result[f"automation.{slug}"] = alias
    return result


def parse_customize_friendly_names(repo_root: Path) -> Dict[str, str]:
    """Return {entity_id: friendly_name} parsed from customize.yaml.

    Used only to bootstrap entity_friendly_name_map.yaml so we never lose the
    hand-curated overrides that customize.yaml held (even though that file is
    not loaded in this repo's configuration.yaml).
    """
    path = repo_root / "customize.yaml"
    if not path.exists():
        return {}
    result: Dict[str, str] = {}
    current_entity: Optional[str] = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        m_obj = re.match(r"^([a-z_]+\.[a-zA-Z0-9_]+):\s*$", stripped)
        if m_obj:
            current_entity = m_obj.group(1)
            continue
        m_name = re.match(r"^\s+friendly_name:\s+(.+?)\s*$", stripped)
        if m_name and current_entity:
            value = m_name.group(1).strip().strip('"').strip("'")
            result[current_entity] = value
    return result


def parse_existing_map(
    path: Path,
) -> Tuple[Dict[str, Optional[str]], List[str], Dict[str, Optional[str]]]:
    """Read an existing entity_friendly_name_map.yaml.

    Returns (entity_value_map, key_order, device_value_map). Values may be
    ``None`` for null/~ entries.
    """
    if not path.exists():
        return {}, [], {}
    values: Dict[str, Optional[str]] = {}
    order: List[str] = []
    devices: Dict[str, Optional[str]] = {}
    in_entities = False
    in_devices = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped_l = raw_line.rstrip()
        if stripped_l.startswith("entities:"):
            in_entities = True
            in_devices = False
            continue
        if stripped_l.startswith("devices:") or stripped_l.startswith("device:"):
            in_entities = False
            inline = stripped_l.split(":", 1)[1].strip()
            in_devices = inline not in {"{}", "[]"}
            continue
        if in_entities:
            m = re.match(r"^  ([a-z_]+\.[a-zA-Z0-9_]+):\s*(.*)$", stripped_l)
            if not m:
                continue
            eid = m.group(1)
            raw_val = m.group(2).strip()
            if raw_val in {"", "~", "null"}:
                values[eid] = None
            else:
                values[eid] = raw_val.strip('"').strip("'")
            if eid not in order:
                order.append(eid)
        elif in_devices:
            md = re.match(r"^  ([A-Za-z0-9_\-:]+):\s*(.*)$", stripped_l)
            if not md:
                continue
            did = md.group(1)
            raw_val = md.group(2).strip()
            if raw_val in {"", "~", "null"}:
                devices[did] = None
            else:
                devices[did] = raw_val.strip('"').strip("'")
    return values, order, devices


def parse_scene_names(repo_root: Path) -> Dict[str, str]:
    """Return {scene.<slug>: name} parsed from scenes.yaml."""
    path = repo_root / "scenes.yaml"
    if not path.exists():
        return {}
    result: Dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^- id: ", text)[1:]
    for block in blocks:
        m_name = re.search(r"^\s+name:\s+(.+?)\s*$", block, re.M)
        if not m_name:
            continue
        name = m_name.group(1).strip().strip('"').strip("'")
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        result[f"scene.{slug}"] = name
    return result


def parse_entities(path: Path) -> List[Entity]:
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^  - entity_id: ", text)[1:]

    entities: List[Entity] = []
    for block in blocks:
        first_line, _, rest = block.partition("\n")
        eid = _strip_quotes(first_line)
        if not eid or "." not in eid:
            continue
        fields: Dict[str, Optional[str]] = {}
        for line in rest.splitlines():
            m = re.match(r"^    ([a-z_]+): (.*)$", line)
            if not m:
                continue
            key, raw = m.group(1), m.group(2)
            fields[key] = _strip_quotes(raw)

        has_entity_name_raw = fields.get("has_entity_name")
        if has_entity_name_raw is None:
            has_entity_name: Optional[bool] = None
        else:
            has_entity_name = has_entity_name_raw.lower() == "true"

        entities.append(
            Entity(
                entity_id=eid,
                domain=eid.split(".", 1)[0],
                name=fields.get("name"),
                original_name=fields.get("original_name"),
                area_id=fields.get("area_id"),
                area_name=fields.get("area_name"),
                device_id=fields.get("device_id"),
                device_name=fields.get("device_name"),
                has_entity_name=has_entity_name,
            )
        )
    return entities


def starts_with_standard_prefix(value: Optional[str]) -> bool:
    if not value:
        return False
    first = value.split()[0] if value.split() else value
    return first.startswith(STANDARD_PREFIXES)


def looks_technical(value: Optional[str], entity_id: str) -> bool:
    """Heuristic: does this display name look like a raw/auto value the user
    would notice as 'wrong' on Lovelace?
    """
    if not value:
        return True
    v = value.strip()
    if not v:
        return True
    if v == entity_id:
        return True
    domain = entity_id.split(".", 1)[0]
    if v.startswith(f"{domain}."):
        return True
    if "." in v and v.replace("_", "").replace(".", "").isalnum() and "_" in v:
        return True
    return False


def suggest_name(entity: Entity) -> Optional[str]:
    """Best-effort suggestion for a friendly name following the project standard.

    Returns ``None`` to indicate the registry override should be removed so HA
    falls back to ``original_name`` + ``device.name_by_user``. This is the
    correct action whenever ``name`` literally equals the ``entity_id`` (a
    previously broken sync).
    """
    if entity.name and entity.name == entity.entity_id:
        return None
    domain = entity.domain
    if entity.name and entity.name.startswith(f"{domain}."):
        return None
    typ = DOMAIN_TO_TYP.get(domain, "Sensor")
    area = entity.area_name or ""
    device = entity.device_name or ""
    base = entity.name or entity.original_name or ""
    base_clean = re.sub(r"\s+", " ", base).strip()
    if base_clean and starts_with_standard_prefix(base_clean):
        return base_clean
    parts = [typ]
    if area and area not in parts:
        parts.append(area)
    if base_clean:
        for token in base_clean.split():
            if token and token not in parts:
                parts.append(token)
    elif device and device not in parts:
        parts.append(device)
    suggestion = " ".join(parts)
    return re.sub(r"\s+", " ", suggestion).strip() or typ


def categorize(entities: Iterable[Entity]) -> Dict[str, CategoryFinding]:
    cats = {
        "A": CategoryFinding(
            code="A",
            title="Helper ohne Standard-Prefix",
            description=(
                "Helper-Entit\u00e4ten, deren angezeigter Name nicht dem Schema "
                "`<Typ> <Bereich> [<Person>] [<Funktion>]` folgt. "
                "Korrektur \u00fcber Repo-YAML (input_*.yaml, scenes.yaml, automations.yaml) "
                "oder zentrale Map."
            ),
        ),
        "B": CategoryFinding(
            code="B",
            title="Physische Entit\u00e4ten ohne Registry-Name",
            description=(
                "Display f\u00e4llt auf `original_name` zur\u00fcck (oft technisch). "
                "Korrektur \u00fcber zentrale Map -> Entity Registry."
            ),
        ),
        "C": CategoryFinding(
            code="C",
            title="Legacy-Tokens im entity_id",
            description=(
                "entity_id enth\u00e4lt `werktisch`, `spielzimmer`, `kinderzimmer`, "
                "`kinderspielzimmer`, `kinderschlafzimmer` oder `arbeitstisch`. "
                "Korrektur \u00fcber `entity_id_rename_map.yaml` + migrate_entity_registry_ids.py."
            ),
        ),
        "D": CategoryFinding(
            code="D",
            title="Technisch wirkender User-Name",
            description=(
                "`name` ist gesetzt, sieht aber technisch aus (entspricht der `entity_id`, "
                "beginnt mit `<domain>.` oder enth\u00e4lt `.`). Solche Namen tauchen oft als "
                "'falsch' auf Lovelace auf. Korrektur \u00fcber zentrale Map."
            ),
        ),
        "E": CategoryFinding(
            code="E",
            title="Kein Name vorhanden",
            description=(
                "Weder `name` noch `original_name` (noch Helper-YAML) gesetzt - die UI zeigt "
                "den blanken `entity_id`. Korrektur \u00fcber zentrale Map oder Helper-YAML."
            ),
        ),
    }
    seen = {code: set() for code in cats}
    for e in entities:
        if any(tok in e.entity_id for tok in LEGACY_TOKENS):
            if e.entity_id not in seen["C"]:
                cats["C"].items.append((e, suggest_name(e)))
                seen["C"].add(e.entity_id)
        display = e.name or e.original_name
        if not display:
            if e.entity_id not in seen["E"]:
                cats["E"].items.append((e, suggest_name(e)))
                seen["E"].add(e.entity_id)
            continue
        if looks_technical(display, e.entity_id):
            if e.domain in HELPER_DOMAINS and e.entity_id not in seen["A"]:
                cats["A"].items.append((e, suggest_name(e)))
                seen["A"].add(e.entity_id)
            elif e.domain not in HELPER_DOMAINS and e.entity_id not in seen["D"]:
                cats["D"].items.append((e, suggest_name(e)))
                seen["D"].add(e.entity_id)
            continue
        if e.domain in HELPER_DOMAINS and not starts_with_standard_prefix(display):
            if e.entity_id not in seen["A"]:
                cats["A"].items.append((e, suggest_name(e)))
                seen["A"].add(e.entity_id)
            continue
        if e.domain not in HELPER_DOMAINS and e.name is None and e.original_name is None:
            if e.entity_id not in seen["B"]:
                cats["B"].items.append((e, suggest_name(e)))
                seen["B"].add(e.entity_id)
    return cats


def write_markdown(path: Path, cats: Dict[str, CategoryFinding], totals: Dict[str, int]) -> None:
    lines: List[str] = []
    lines.append("# Home Assistant Entity Naming Audit")
    lines.append("")
    lines.append(f"- Entit\u00e4ten gescannt: **{totals['total']}**")
    for code in ("A", "B", "C", "D", "E"):
        lines.append(f"- Kategorie {code}: **{len(cats[code].items)}**")
    lines.append("")
    lines.append(
        "Erkl\u00e4rungen und Korrektur-Pfade siehe `entity_friendly_name_map.template.yaml`."
    )
    lines.append("")

    for code in ("A", "B", "C", "D", "E"):
        cat = cats[code]
        lines.append(f"## Kategorie {cat.code} - {cat.title} ({len(cat.items)})")
        lines.append("")
        lines.append(cat.description)
        lines.append("")
        if not cat.items:
            lines.append("- keine")
            lines.append("")
            continue
        for entity, suggestion in sorted(cat.items, key=lambda x: x[0].entity_id):
            current = entity.name or entity.original_name or "<leer>"
            extra = []
            if entity.area_name:
                extra.append(f"area: {entity.area_name}")
            if entity.device_name:
                extra.append(f"device: {entity.device_name}")
            extra_txt = f" ({', '.join(extra)})" if extra else ""
            suggest_txt = "null (reset zu original_name)" if suggestion is None else suggestion
            lines.append(
                f"- `{entity.entity_id}` | current: `{current}`{extra_txt} -> suggest: `{suggest_txt}`"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_production_map(
    path: Path,
    cats: Dict[str, CategoryFinding],
    customize_overrides: Dict[str, str],
    existing_map: Dict[str, Optional[str]],
    existing_devices: Optional[Dict[str, Optional[str]]] = None,
) -> Tuple[int, int]:
    """Write entity_friendly_name_map.yaml.

    Precedence per entity_id:
      1. Value from an existing entity_friendly_name_map.yaml (preserves user edits)
      2. Value from customize.yaml (one-time bootstrap migration)
      3. Audit suggestion (usually null/reset)

    Returns (num_entities_written, num_user_or_customize_values).
    """
    final: Dict[str, Optional[str]] = {}
    sources: Dict[str, str] = {}

    for code in ("A", "B", "C", "D", "E"):
        for entity, suggestion in cats[code].items:
            eid = entity.entity_id
            if eid in final:
                continue
            if eid in existing_map:
                final[eid] = existing_map[eid]
                sources[eid] = "existing"
            elif eid in customize_overrides:
                final[eid] = customize_overrides[eid]
                sources[eid] = "customize"
            else:
                final[eid] = suggestion
                sources[eid] = "audit"

    for eid, val in existing_map.items():
        if eid not in final:
            final[eid] = val
            sources[eid] = "existing"
    for eid, val in customize_overrides.items():
        if eid not in final:
            final[eid] = val
            sources[eid] = "customize"

    lines: List[str] = []
    lines.append("# Friendly-Name-Map (Single Source of Truth)")
    lines.append("#")
    lines.append(
        "# Diese Datei steuert die im Lovelace sichtbaren Anzeigenamen."
    )
    lines.append(
        "# Werte: konkreter String -> setzt `name` in core.entity_registry."
    )
    lines.append(
        "#         ~ oder null    -> l\u00f6scht den Override; HA berechnet den Namen"
    )
    lines.append(
        "#                          aus `original_name` und `device.name_by_user`."
    )
    lines.append("#")
    lines.append(
        "# Generiert/aktualisiert durch scripts/audit_entity_names.py."
    )
    lines.append(
        "# Wende auf dem Server an mit:"
    )
    lines.append(
        "#   sudo python3 scripts/apply_entity_friendly_names.py \\"
    )
    lines.append(
        "#     --registry /data/home-assistant/.storage/core.entity_registry \\"
    )
    lines.append(
        "#     --map entity_friendly_name_map.yaml --apply"
    )
    lines.append("")
    lines.append("entities:")

    sorted_ids = sorted(final.keys())
    for eid in sorted_ids:
        val = final[eid]
        src = sources.get(eid, "audit")
        comment = f"  # source: {src}"
        lines.append(comment)
        if val is None:
            lines.append(f"  {eid}: ~")
        else:
            safe = val.replace('"', '\\"')
            lines.append(f'  {eid}: "{safe}"')

    lines.append("")
    if existing_devices:
        lines.append("devices:")
        for did in sorted(existing_devices.keys()):
            val = existing_devices[did]
            if val is None:
                lines.append(f"  {did}: ~")
            else:
                safe = val.replace('"', '\\"')
                lines.append(f'  {did}: "{safe}"')
    else:
        lines.append("devices: {}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

    customized = sum(1 for s in sources.values() if s in {"existing", "customize"})
    return len(final), customized


def write_template(path: Path, cats: Dict[str, CategoryFinding]) -> None:
    lines: List[str] = []
    lines.append("# Friendly-Name-Map (Single Source of Truth)")
    lines.append("#")
    lines.append("# Bearbeite die Werte unten und committe diese Datei.")
    lines.append("# Wende sie auf dem Server an mit:")
    lines.append("#   sudo python3 scripts/apply_entity_friendly_names.py \\")
    lines.append("#     --registry /data/home-assistant/.storage/core.entity_registry \\")
    lines.append("#     --map entity_friendly_name_map.yaml --apply")
    lines.append("#")
    lines.append("# Nullwerte (~ oder null) entfernen ein bisheriges Registry-Name-Override")
    lines.append("# und reaktivieren `original_name` der Integration.")
    lines.append("")
    lines.append("entities:")
    written: set = set()
    for code in ("A", "B", "C", "D", "E"):
        cat = cats[code]
        if not cat.items:
            continue
        items_for_cat = [
            (e, s) for e, s in cat.items if e.entity_id not in written
        ]
        if not items_for_cat:
            continue
        lines.append(f"  # === Kategorie {cat.code}: {cat.title} ===")
        for entity, suggestion in sorted(items_for_cat, key=lambda x: x[0].entity_id):
            current = entity.name or entity.original_name or ""
            comment_parts = [f"current: \"{current}\""]
            if entity.area_name:
                comment_parts.append(f"area: {entity.area_name}")
            if entity.device_name:
                comment_parts.append(f"device: {entity.device_name}")
            comment = " | ".join(comment_parts)
            lines.append(f"  # {comment}")
            if suggestion is None:
                lines.append(f"  {entity.entity_id}: ~")
            else:
                lines.append(f"  {entity.entity_id}: \"{suggestion}\"")
            written.add(entity.entity_id)
        lines.append("")
    lines.append("devices: {}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    inv = root / "inventory"
    snapshot = inv / "entities_snapshot.yaml"
    if not snapshot.exists():
        print(f"Missing snapshot: {snapshot}. Run export_entity_snapshot.py first.")
        return 2

    entities = parse_entities(snapshot)
    helper_names = parse_helper_yaml_names(root)
    automation_names = parse_automation_aliases(root)
    scene_names = parse_scene_names(root)
    yaml_names: Dict[str, str] = {}
    yaml_names.update(helper_names)
    yaml_names.update(automation_names)
    yaml_names.update(scene_names)
    for e in entities:
        if e.original_name is None and e.name is None and e.entity_id in yaml_names:
            e.original_name = yaml_names[e.entity_id]
    cats = categorize(entities)

    totals = {"total": len(entities)}
    for code in ("A", "B", "C", "D", "E"):
        totals[code] = len(cats[code].items)

    md_path = inv / "entity_naming_audit.md"
    json_path = inv / "entity_naming_audit.json"
    template_path = root / "entity_friendly_name_map.template.yaml"
    map_path = root / "entity_friendly_name_map.yaml"

    customize_overrides = parse_customize_friendly_names(root)
    existing_map, _, existing_devices = parse_existing_map(map_path)

    write_markdown(md_path, cats, totals)
    write_template(template_path, cats)
    map_written, customized = write_production_map(
        map_path,
        cats,
        customize_overrides,
        existing_map,
        existing_devices=existing_devices,
    )

    payload = {
        "summary": totals,
        "categories": {
            code: {
                "title": cats[code].title,
                "description": cats[code].description,
                "items": [
                    {
                        "entity_id": e.entity_id,
                        "domain": e.domain,
                        "name": e.name,
                        "original_name": e.original_name,
                        "area_name": e.area_name,
                        "device_name": e.device_name,
                        "suggestion": s,
                    }
                    for e, s in sorted(cats[code].items, key=lambda x: x[0].entity_id)
                ],
            }
            for code in ("A", "B", "C", "D", "E")
        },
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {template_path}")
    print(f"Wrote {map_path} ({map_written} entries, {customized} curated)")
    print(
        "Summary: "
        + ", ".join(f"{c}={totals[c]}" for c in ("total", "A", "B", "C", "D", "E"))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
