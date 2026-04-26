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

## Standard deploy flow

1. Validate local git state:
   - `git status --short`
   - `git log -1 --oneline`
2. Commit local changes if needed.
3. Push from local:
   - `git push origin main`
4. Pull on server:
   - `cd "/data/home-assistant" && git pull origin main`
5. Activate in Docker:
   - `docker restart home-assistant_2026_2_3`

## If `git pull` shows no updates

Run this checklist in order:

1. Compare top commit local vs server (`git log -1 --oneline`).
2. Verify both repos point to the same remote (`git remote -v`).
3. Confirm local push happened (`git push origin main`).
4. Confirm server path is correct repo (`cd "/data/home-assistant"`).
5. Retry `git pull origin main`.

## Quick verification after deploy

- `cd "/data/home-assistant" && git log -1 --oneline`
- Confirm commit hash matches local `main`.

## Notes

- HTTPS and SSH remotes are both fine if they reference the same GitHub repo.
- Missing local git author identity blocks commits; set repo-local `user.name` and `user.email` if needed.
