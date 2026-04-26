# Home Assistant Update Ablauf

Diese Checkliste beschreibt den Standardablauf fuer dieses Setup:

- Lokales Repo: `/home/stephanprivat/Dokumente/Development/homeassistant-config`
- Server-Repo: `/data/home-assistant`
- Container: `home-assistant_2026_2_3`

## 1) Lokal aendern und committen

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git status
git add .
git commit -m "Kurzbeschreibung der Aenderung"
```

## 2) Lokal nach GitHub pushen

```bash
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git push origin main
```

## 3) Auf dem Server pullen

```bash
cd "/data/home-assistant"
git pull origin main
```

## 4) Home Assistant Container neu starten

```bash
docker restart home-assistant_2026_2_3
```

## 5) Schnellkontrolle

```bash
cd "/data/home-assistant"
git log -1 --oneline
```

Der oberste Commit auf dem Server sollte mit dem lokalen Stand uebereinstimmen.

## Fehlerbild: `git pull` bringt keine Updates

Typische Ursachen:

1. Lokal wurde noch nicht gepusht (`git push` fehlt).
2. Falsches Verzeichnis auf dem Server (nicht das gemountete `/config`-Repo).
3. Falscher Branch.

Schnell pruefen:

```bash
# lokal
cd "/home/stephanprivat/Dokumente/Development/homeassistant-config"
git log -1 --oneline
git remote -v

# server
cd "/data/home-assistant"
git log -1 --oneline
git remote -v
```

## Optional: Home Assistant Konfiguration validieren

Wenn die HA-CLI verfuegbar ist:

```bash
ha core check
ha core restart
```
