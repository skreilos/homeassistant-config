---
name: homeassistant-config
description: Keep Home Assistant config changes consistent for this repository, including deployment and naming standards. Use when the user mentions home assistant deploy, update, git pull/push, docker restart, entity naming, automation alias naming, or asks why server has no updates.
---

# Home Assistant Config

Use this workflow for this project.

## Naming standard (use for all new changes)

Use these patterns consistently:

- Automation alias: `<Typ> <Zimmer> <Person> [<Funktion>]`
- Entity friendly name: `<Typ> <Zimmer> <Person> [<Funktion>]`
- Trigger IDs inside one automation should follow the same room/person token as that automation.

Project examples:

- `Button Zimmer Julian`
- `Button Zimmer Julian Nachttisch`
- `Button Zimmer Julian Schreibtisch`
- `Licht Zimmer Julian`
- `Nachttisch Zimmer Julian`
- `Licht Zimmer Joshua`

Normalization rules:

- Keep order fixed (`Typ` -> `Zimmer` -> `Person` -> optional function).
- Prefer `Zimmer Julian` / `Zimmer Joshua` over older room labels.
- Do not rename technical `entity_id` values unless the user explicitly asks for entity migration.

## Setup

- Local repo: `/home/stephanprivat/Dokumente/Development/homeassistant-config`
- Server repo: `/data/home-assistant`
- Container: `home-assistant_2026_2_3`
- Branch: `main`
- Local HA access: `http://10.0.0.2:8123`
- External HA URL (Cloudflare): `https://home.the-force.ch/dashboard-tedt?homescreen=1`

## Response style for this skill

When the user asks for deploy help, always provide:

1. Exact commands, in execution order.
2. Which host runs each command (local vs server).
3. A short "verify" step with expected outcome.
4. A fallback path if one command fails.

Use German by default when the user writes in German.

## Standard deploy flow (copy/paste ready)

### A) Local machine: prepare, commit, push

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git status --short
git add .
git commit -m "Describe change briefly"
git push origin main
```

### B) Server: pull latest config

```bash
cd "/data/home-assistant"
git pull origin main
```

### C) Server: activate config in Docker

```bash
docker restart home-assistant_2026_2_3
```

## Verification checklist

Run and compare the top commit on both sides:

```bash
# local
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git log -1 --oneline

# server
cd "/data/home-assistant"
git log -1 --oneline
```

Expected: same commit hash on local `main` and server `main`.

## If `git pull` shows no updates

Run this checklist in order:

1. Confirm local push was executed:
   - `cd "/home/stephanprivat/Dokumente/Development/homeassistant-config" && git push origin main`
2. Compare local/server commit:
   - `git log -1 --oneline` (both sides)
3. Confirm both remotes point to the same repo:
   - `git remote -v` (both sides)
4. Confirm server path is the active config repo:
   - `cd "/data/home-assistant" && pwd`
5. Retry pull:
   - `git pull origin main`

## If commit fails (author identity unknown)

Set repo-local identity on the machine where commit is created:

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git config user.name "Stephan"
git config user.email "mail@kreilos.ch"
```

Then retry commit.

## If push fails (SSH auth)

Check SSH auth quickly:

```bash
ssh -T git@github.com
```

If needed, verify remote:

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git remote -v
```

SSH remote format should be:

`git@github.com:skreilos/homeassistant-config.git`

## If restart succeeds but behavior is unchanged

1. Confirm server actually received latest commit (`git log -1 --oneline`).
2. Confirm running container name:
   - `docker ps --format '{{.Names}}' | rg home-assistant`
3. Confirm container `/config` mount points to `/data/home-assistant`:
   - `docker inspect home-assistant_2026_2_3`
4. Restart again after successful pull.

## Optional Home Assistant CLI path

If this installation provides the HA CLI:

```bash
ha core check
ha core restart
```

## Cloudflare 403 troubleshooting (this setup)

Symptom:

- External URL returns `403 Forbidden`.
- Local IP access `10.0.0.2` works.

Likely cause in this project:

- In `configuration.yaml`, `http.trusted_proxies` is currently limited and may not include Cloudflare proxy IP ranges.

Action order:

1. Keep `use_x_forwarded_for: true`.
2. Add Cloudflare proxy CIDRs to `http.trusted_proxies` in `configuration.yaml`.
3. Ensure Cloudflare SSL mode is `Full (strict)` and origin cert/path is valid.
4. Restart Home Assistant container:
   - `docker restart home-assistant_2026_2_3`
5. Retest external URL and local URL.

Verification commands:

```bash
cd "/data/home-assistant"
rg "http:|use_x_forwarded_for|trusted_proxies" configuration.yaml
docker logs --tail=200 home-assistant_2026_2_3
```

Expected:

- No repeated proxy/auth related warnings in HA logs.
- External URL responds without `403`.

## Automated entity_id migration (no manual UI renaming)

Use the mapping file:

- `entity_id_rename_map.yaml`

Use scripts:

- `scripts/migrate_entity_registry_ids.py` (updates `/config/.storage/core.entity_registry`)
- `scripts/replace_entity_ids_in_repo.py` (updates YAML/MD references in this git repo)

Recommended run order:

1. Dry run in repo:
   - `python3 scripts/replace_entity_ids_in_repo.py --repo "/home/stephanprivat/Dokumente/Development/homeassistant-config" --map "entity_id_rename_map.yaml"`
2. Dry run on server registry:
   - `python3 scripts/migrate_entity_registry_ids.py --registry "/data/home-assistant/.storage/core.entity_registry" --map "/data/home-assistant/entity_id_rename_map.yaml"`
3. Apply in repo:
   - `python3 scripts/replace_entity_ids_in_repo.py --repo "/home/stephanprivat/Dokumente/Development/homeassistant-config" --map "entity_id_rename_map.yaml" --apply`
4. Apply in server registry:
   - `python3 scripts/migrate_entity_registry_ids.py --registry "/data/home-assistant/.storage/core.entity_registry" --map "/data/home-assistant/entity_id_rename_map.yaml" --apply`
5. Restart Home Assistant:
   - `docker restart home-assistant_2026_2_3`

## Full entity inventory export (for complete naming audits)

To avoid naming checks based only on automation references, export full entity registry snapshot on the server:

```bash
cd "/data/home-assistant"
python3 scripts/export_entity_snapshot.py \
  --config-dir "/data/home-assistant" \
  --out "/data/home-assistant/inventory/entities_snapshot.yaml"
```

Commit `inventory/entities_snapshot.yaml` to git. Use this file as the source of truth for future naming consistency checks.
The export also writes:

- `inventory/areas_snapshot.yaml`
- `inventory/devices_snapshot.yaml`

Use all three files as source of truth for naming and assignment audits.

## Full HA context export (beyond YAML)

When runtime/integration state is needed, export context bundle from `.storage`:

```bash
cd "/data/home-assistant"
python3 scripts/export_ha_context_bundle.py \
  --config-dir "/data/home-assistant" \
  --out-dir "/data/home-assistant/inventory/context_bundle"
```

Then commit:

```bash
git add inventory/context_bundle
git commit -m "Update HA context bundle."
git push origin main
```

This gives the agent visibility into non-YAML registry/runtime metadata.

## Consistency audit command

Run after snapshot/context export:

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
python3 scripts/audit_ha_consistency.py
```

Outputs:

- `inventory/consistency_audit.json`
- `inventory/consistency_audit.md`

Use the markdown report as primary checklist for cleanup priorities.

## Category B consistency pass (safe mode)

For diagnostics entities (battery/LQI/RSSI), keep `entity_id` stable and improve naming/areas:

- Friendly names in `customize.yaml`
- Area assignment map in `entity_area_assignment_map.yaml`
- Server script: `scripts/migrate_entity_areas.py`

Run order:

1. Dry run:
   - `python3 scripts/migrate_entity_areas.py --config-dir "/data/home-assistant" --map "/data/home-assistant/entity_area_assignment_map.yaml"`
2. Apply:
   - `sudo python3 scripts/migrate_entity_areas.py --config-dir "/data/home-assistant" --map "/data/home-assistant/entity_area_assignment_map.yaml" --apply`
3. Restart:
   - `docker restart home-assistant_2026_2_3`
4. Re-export snapshot:
   - `python3 scripts/export_entity_snapshot.py --config-dir "/data/home-assistant" --out "/data/home-assistant/inventory/entities_snapshot.yaml"`

## Notes

- HTTPS and SSH remotes are both fine if they reference the same GitHub repo.
- Prefer repo-local git identity on servers (`git config`, not `--global`).
- Keep commands copy/paste friendly and avoid placeholders in final user instructions.

## Full operational runbook (this project)

Use this exact sequence whenever naming/entity consistency work is done.

### 1) Local prepare and push

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git status
git add .
git commit -m "Describe config/naming update."
git push origin main
```

### 2) Server sync

```bash
cd "/data/home-assistant"
git pull origin main
```

### 3) Category A (entity_id migration) on server

Dry run:

```bash
python3 scripts/migrate_entity_registry_ids.py \
  --registry "/data/home-assistant/.storage/core.entity_registry" \
  --map "/data/home-assistant/entity_id_rename_map.yaml"
```

Apply:

```bash
sudo python3 scripts/migrate_entity_registry_ids.py \
  --registry "/data/home-assistant/.storage/core.entity_registry" \
  --map "/data/home-assistant/entity_id_rename_map.yaml" \
  --apply
```

### 4) Category B (diagnostics naming/area consistency) on server

Dry run:

```bash
python3 scripts/migrate_entity_areas.py \
  --config-dir "/data/home-assistant" \
  --map "/data/home-assistant/entity_area_assignment_map.yaml"
```

Apply:

```bash
sudo python3 scripts/migrate_entity_areas.py \
  --config-dir "/data/home-assistant" \
  --map "/data/home-assistant/entity_area_assignment_map.yaml" \
  --apply
```

### 5) Restart Home Assistant

```bash
docker restart home-assistant_2026_2_3
```

### 6) Export full inventory snapshots

```bash
python3 scripts/export_entity_snapshot.py \
  --config-dir "/data/home-assistant" \
  --out "/data/home-assistant/inventory/entities_snapshot.yaml"
```

Expected output files:

- `inventory/entities_snapshot.yaml`
- `inventory/areas_snapshot.yaml`
- `inventory/devices_snapshot.yaml`

### 7) Server commit and push snapshots

```bash
git add inventory/entities_snapshot.yaml inventory/areas_snapshot.yaml inventory/devices_snapshot.yaml
git commit -m "Update entity/area/device snapshots after migration."
git push origin main
```

### 8) Local pull after server push

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git pull origin main
```

## Validation checks

### A migration success

- Compare `inventory/entity_rename_plan.md` against `inventory/entities_snapshot.yaml`.
- For each `old -> new`, `new` exists and `old` no longer exists.

### B migration success

- Every key in `entity_area_assignment_map.yaml` has non-null `area_name` in `inventory/entities_snapshot.yaml`.

### Legacy token check

No legacy entity IDs should remain with these tokens:

- `spielzimmer`
- `kinderschlafzimmer`
- `kinderzimmer`
- `kinderspielzimmer`
- `werktisch`
- `arbeitstisch`

## Known pitfalls and fixes

### Permission denied for `.storage/core.entity_registry`

Cause: file owned by `root:root`.
Fix: run migration scripts with `sudo` on server.

### Missing area in registry

Cause: mapping uses area display name that does not exist in `core.area_registry`.
Fix: prefer stable area IDs in `entity_area_assignment_map.yaml` (for example `julian`).

### Area names still legacy

Use area name migration mapping and script:

- `area_rename_map.yaml`
- `scripts/migrate_area_names.py`

Run dry run first, then apply with `sudo`, restart HA, and re-export snapshots.

### `rg` not available on server

Use:

```bash
grep -E "pattern" inventory/entities_snapshot.yaml
```
