# Home Assistant Kontext-Export

Ziel: alle relevanten Daten exportieren, die nicht direkt aus YAML gelesen werden können.

## 1) Auf dem Server exportieren

```bash
cd "/data/home-assistant"
python3 scripts/export_entity_snapshot.py \
  --config-dir "/data/home-assistant" \
  --out "/data/home-assistant/inventory/entities_snapshot.yaml"

python3 scripts/export_ha_context_bundle.py \
  --config-dir "/data/home-assistant" \
  --out-dir "/data/home-assistant/inventory/context_bundle"
```

## 2) In Git committen

```bash
cd "/data/home-assistant"
git add inventory/entities_snapshot.yaml inventory/areas_snapshot.yaml inventory/devices_snapshot.yaml inventory/context_bundle
git commit -m "Update HA snapshots and context bundle."
git push origin main
```

## 3) Lokal nachziehen

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git pull origin main
```

## Enthaltene Zusatzdaten im Context Bundle

- `core.entity_registry.json`
- `core.device_registry.json`
- `core.area_registry.json`
- `core.config_entries.json`
- `core.restore_state.json`
- optional weitere vorhandene Registry-Dateien
