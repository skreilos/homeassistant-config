#!/usr/bin/env python3
"""Export a broad Home Assistant context bundle from .storage.

This captures runtime/registry metadata that is not directly represented in
YAML config files, so it can be versioned in git for audit/debug purposes.

Usage:
  python3 scripts/export_ha_context_bundle.py \
    --config-dir "/data/home-assistant" \
    --out-dir "/data/home-assistant/inventory/context_bundle"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


EXPORT_FILES = [
    "core.area_registry",
    "core.device_registry",
    "core.entity_registry",
    "core.config_entries",
    "core.restore_state",
    "core.floor_registry",
    "core.label_registry",
    "core.group",
]


def scrub_json(value: Any) -> Any:
    """Redact obvious secrets/tokens while keeping useful structure."""
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            key = k.lower()
            if any(s in key for s in ["token", "access_token", "refresh_token", "password", "secret", "api_key"]):
                out[k] = "***REDACTED***"
            else:
                out[k] = scrub_json(v)
        return out
    if isinstance(value, list):
        return [scrub_json(x) for x in value]
    return value


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_index(path: Path, exported: List[str], missing: List[str]) -> None:
    lines = [
        "# Home Assistant Context Bundle",
        "",
        "Dieses Verzeichnis enthält exportierte Laufzeit-/Registry-Daten aus `.storage`,",
        "die nicht direkt in YAML-Konfigurationsdateien sichtbar sind.",
        "",
        "## Exportiert",
    ]
    lines.extend([f"- `{name}.json`" for name in exported] or ["- _keine_"])
    lines.append("")
    lines.append("## Nicht gefunden")
    lines.extend([f"- `{name}`" for name in missing] or ["- _keine_"])
    lines.append("")
    lines.append("## Hinweis")
    lines.append("- Tokens/Secrets werden beim Export bestmöglich redigiert.")
    lines.append("- Dateien sind Snapshots; bei Änderungen erneut exportieren und committen.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", required=True, help="Home Assistant config directory")
    parser.add_argument("--out-dir", required=True, help="Target directory for bundle exports")
    args = parser.parse_args()

    config_dir = Path(args.config_dir)
    storage_dir = config_dir / ".storage"
    out_dir = Path(args.out_dir)

    exported: List[str] = []
    missing: List[str] = []

    for name in EXPORT_FILES:
        src = storage_dir / name
        if not src.exists():
            missing.append(name)
            continue
        payload = scrub_json(read_json(src))
        dst = out_dir / f"{name}.json"
        write_json(dst, payload)
        exported.append(name)

    write_index(out_dir / "README.md", exported, missing)
    print(f"Exported {len(exported)} files to {out_dir}")
    if missing:
        print(f"Missing {len(missing)} optional files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
