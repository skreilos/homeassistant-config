# Home Assistant Context Bundle

Dieses Verzeichnis enthält exportierte Laufzeit-/Registry-Daten aus `.storage`,
die nicht direkt in YAML-Konfigurationsdateien sichtbar sind.

## Exportiert
- `core.area_registry.json`
- `core.device_registry.json`
- `core.entity_registry.json`
- `core.config_entries.json`
- `core.restore_state.json`

## Nicht gefunden
- `core.floor_registry`
- `core.label_registry`
- `core.group`

## Hinweis
- Tokens/Secrets werden beim Export bestmöglich redigiert.
- Dateien sind Snapshots; bei Änderungen erneut exportieren und committen.
