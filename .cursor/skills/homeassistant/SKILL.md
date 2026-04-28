---
name: homeassistant
description: Keep Home Assistant config changes consistent for this repository, including deployment, exports, audits, and naming standards. Use when the user mentions home assistant deploy, update, git pull/push, docker restart, entity naming, automation alias naming, exports, or asks why server has no updates.
---

# Home Assistant Config

Use this workflow for this project.

## Naming standard (use for all new changes)

Use these patterns consistently:

- Automation alias: `<Typ> <Bereich> [<Person>] [<Funktion>]`
- Entity friendly name: `<Typ> <Bereich> [<Person>] [<Funktion>]`
- Trigger IDs inside one automation should follow the same area/person token as that automation.

Project examples:

- `Button Zimmer Julian`
- `Button Zimmer Julian Nachttisch`
- `Button Zimmer Julian Schreibtisch`
- `Licht Zimmer Julian`
- `Nachttisch Zimmer Julian`
- `Licht Zimmer Joshua`

Normalization rules:

- Keep order fixed (`Typ` -> `Bereich` -> optional `Person` -> optional function).
- Prefer `Zimmer Julian` / `Zimmer Joshua` over older room labels.
- Do not rename technical `entity_id` values unless the user explicitly asks for entity migration.

### Automation naming concept (mandatory)

Use these `Typ` prefixes:

- `Licht` for light automations
- `Schalter` for switch/power automations
- `Button` for physical button/remotes
- `Wecker` for wake-up routines
- `Routine` for household routines
- `Präsenz` for presence/occupancy
- `Benachrichtigung` for notifications
- `Szene` for scene selectors
- `Musik` / `Sound` for audio behavior
- `Lüftung` for fan/dehumidifier logic
- `Energie` for tariff/cost logic
- `Alarm` for security/all-off actions

Rules:

1. Use German names.
2. Avoid separators like `-`, `_`, `V2`, `II`, `Everyday`.
3. Keep aliases concise and human-readable.
4. Do not include technical IDs in aliases.

## Setup

- Local repo: `/home/stephanprivat/Dokumente/Development/homeassistant-config`
- Server repo: `/data/home-assistant`
- Container: `home-assistant`
- Branch: `main`
- Local HA access: `http://10.0.0.2:8123`
- External HA URL (Cloudflare): `https://home.the-force.ch/dashboard-tedt?homescreen=1`

## Response style for this skill

When the user asks for deploy help, always provide:

1. Exact commands, in execution order.
2. Which host runs each command (local vs server).
3. A short "verify" step with expected outcome.
4. A fallback path if one command fails.

## Default execution mode for this project

If the user requests ongoing implementation work in this Home Assistant repo, default to:

1. Apply the requested config/code changes.
2. Run a quick sanity check on touched files.
3. Commit immediately.
4. Push immediately to `main`.
5. Return the commit hash and required server pull/restart commands.

Only skip commit/push if the user explicitly says not to commit yet.

### Deploy handshake override (mandatory)

After any commit+push in this project, return **only** this server step first:

- `cd "/data/home-assistant"`
- `git pull origin main`

Then wait for user confirmation that config check passed.
Only after explicit user confirmation, provide restart commands.

When the user asks for `commit` + `push` (or equivalent):

1. First provide a short summary of commit hash + push result.
2. Immediately after the summary, provide only:
   - `cd "/data/home-assistant"`
   - `git pull origin main`
3. Do not include restart in the same response.
4. Wait for user confirmation that config validation passed, then provide restart/export steps.
5. If compose/image changes are part of the commit, use `docker compose pull && docker compose up -d` only after confirmation.
6. After restart/export is complete, provide local sync command:
   - `cd "/home/stephanprivat/Dokumente/Development/homeassistant-config" && git pull origin main`

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
docker restart home-assistant
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
   - `docker inspect home-assistant`
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
   - `docker restart home-assistant`
5. Retest external URL and local URL.

Verification commands:

```bash
cd "/data/home-assistant"
rg "http:|use_x_forwarded_for|trusted_proxies" configuration.yaml
docker logs --tail=200 home-assistant
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
   - `docker restart home-assistant`

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

## Lovelace dashboard entity audit (critical for "unknown entities")

When cards show `Unbekannt` / inactive entities, audit the live Lovelace storage file against the active entity registry:

```bash
cd "/data/home-assistant"
python3 scripts/audit_lovelace_entities.py \
  --lovelace "/data/home-assistant/.storage/lovelace.dashboard_tedt" \
  --entity-registry "/data/home-assistant/.storage/core.entity_registry" \
  --rename-map "/data/home-assistant/entity_id_rename_map.yaml" \
  --json-out "/data/home-assistant/inventory/lovelace_entity_audit.json"
```

Interpretation:

- Lines with `-> suggest:` are safe rename-map replacements.
- Lines without suggestion are usually truly missing/deleted devices and must be replaced or removed manually.

Before any `.storage` Lovelace edit:

```bash
cd "/data/home-assistant/.storage"
sudo cp lovelace.dashboard_tedt "lovelace.dashboard_tedt.bak_$(date +%F_%H%M%S)"
```

Important grep note:

- `grep lovelace*` also matches `.bak` files.  
  Validate active file only with:

```bash
grep -niE "pattern" "/data/home-assistant/.storage/lovelace.dashboard_tedt"
```

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
   - `docker restart home-assistant`
4. Re-export snapshot:
   - `python3 scripts/export_entity_snapshot.py --config-dir "/data/home-assistant" --out "/data/home-assistant/inventory/entities_snapshot.yaml"`

## Notes

- HTTPS and SSH remotes are both fine if they reference the same GitHub repo.
- Prefer repo-local git identity on servers (`git config`, not `--global`).
- Keep commands copy/paste friendly and avoid placeholders in final user instructions.

## Docker Compose update workflow (Home Assistant)

Use this project file:

- `/data/home-assistant/docker-compose.yml`

Recommended container name:

- `home-assistant` (stable, no version in name)

### Regular update (already on compose)

1. Update image tag in `docker-compose.yml` (in git).
2. Push changes from local.
3. On server:

```bash
cd "/data/home-assistant"
git pull origin main
docker compose pull
docker compose up -d
```

### First-time migration from manual `docker run` to compose

If compose fails with name conflict, remove old manually created container first:

```bash
cd "/data/home-assistant"
docker stop home-assistant_2026_2_3
docker rm home-assistant_2026_2_3
docker compose pull
docker compose up -d
```

### Optional cleanup of old docker images

Safe periodic cleanup:

```bash
docker image prune -a
```

Stronger cleanup (includes stopped containers/networks/cache):

```bash
docker system prune -a
```

Do not use `--volumes` unless user explicitly asks.

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
docker restart home-assistant
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

### Permission denied for `.storage/lovelace.dashboard_tedt`

Cause: `.storage` file not writable as normal user.
Fix: edit with `sudo` and keep timestamped backup before write.

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

### Developer Tools "Services" missing

In newer HA versions, "Services" is now "Actions" (`Aktionen`).
Use `action:` syntax instead of `service:` in manual test calls.

### `select.select_option` rejects lowercase values

Some entities use case-sensitive option names.
Example valid values:

- `Off`
- `On`
- `Toggle`
- `PreviousValue`

If `on` fails, retry with `On`.

### `MAC_NO_ACK` when setting ZHA start-up options

Cause: Zigbee device did not acknowledge command (often lamp has no power because Shelly is off, or weak mesh).

Recovery order:

1. Turn Shelly output on.
2. Wait 2-3 seconds.
3. Retry action.
4. If still failing: ZHA "Reconfigure", then retry.

### Shelly-controlled room lights flash to 100% before dimming

If Shelly physically powers Zigbee bulbs, automation dimming can only run after power-on.
To reduce initial flash, configure bulb startup attributes on the bulb entities:

- `select.*_start_up_behavior` (use valid option names like `On` or `PreviousValue`)
- `number.*_start_up_current_level`
- optionally `number.*_on_off_transition_time`

This behavior cannot be fully solved in automation alone when bulbs are power-cycled by Shelly.
