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
