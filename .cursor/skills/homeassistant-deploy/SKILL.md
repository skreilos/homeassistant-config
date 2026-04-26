---
name: homeassistant-deploy
description: Keep Home Assistant config deployment consistent for this repository. Use when the user mentions home assistant deploy, update, git pull/push, docker restart, config activation, or asks why server has no updates.
---

# Home Assistant Deploy

Use this workflow for this project.

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

## Notes

- HTTPS and SSH remotes are both fine if they reference the same GitHub repo.
- Prefer repo-local git identity on servers (`git config`, not `--global`).
- Keep commands copy/paste friendly and avoid placeholders in final user instructions.
