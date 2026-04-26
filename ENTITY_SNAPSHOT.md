# Entity Snapshot Workflow

Ziel: komplette Entity-Liste versionieren, damit Namens-Checks nicht nur auf Automationen basieren.

## 1) Auf dem Server exportieren

```bash
cd "/data/home-assistant"
python3 scripts/export_entity_snapshot.py \
  --config-dir "/data/home-assistant" \
  --out "/data/home-assistant/inventory/entities_snapshot.yaml"
```

## 2) Snapshot committen

```bash
cd "/data/home-assistant"
git add "inventory/entities_snapshot.yaml"
git commit -m "Update Home Assistant entity snapshot."
git push origin main
```

## 3) Für Namensprüfung nutzen

Die Datei `inventory/entities_snapshot.yaml` enthält pro Entity:

- `entity_id`
- `domain`
- `name` / `original_name`
- `area_name`
- `device_name`
- `disabled_by` / `hidden_by`

Damit kann ich beim nächsten Mal repo-weit und vollständig Namenskonsistenz prüfen.

Zusätzlich werden automatisch erzeugt:

- `inventory/areas_snapshot.yaml`
- `inventory/devices_snapshot.yaml`

Damit sind Area- und Device-Daten ebenfalls versioniert und für Konsistenzprüfungen verfügbar.

## Area-Namen automatisch umbenennen

Mapping-Datei:

- `area_rename_map.yaml`

Script:

- `scripts/migrate_area_names.py`

Dry-Run:

```bash
cd "/data/home-assistant"
python3 scripts/migrate_area_names.py \
  --config-dir "/data/home-assistant" \
  --map "/data/home-assistant/area_rename_map.yaml"
```

Apply:

```bash
cd "/data/home-assistant"
sudo python3 scripts/migrate_area_names.py \
  --config-dir "/data/home-assistant" \
  --map "/data/home-assistant/area_rename_map.yaml" \
  --apply
docker restart home-assistant_2026_2_3
```

Danach wieder Snapshot exportieren und committen.
