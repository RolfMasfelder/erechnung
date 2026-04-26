---
name: initial_start
display_name: Initial Start / First Clone Setup
version: 1.0.0
author: Rolf Masfelder
description: Pflichtschritte nach dem ersten Clone oder Umzug in ein neues Verzeichnis (SELinux, Zertifikate, Verzeichnisse, Netzwerk)
---

# Initial Start — Pflichtschritte nach erstem Clone

Diese Schritte sind **einmalig** nach einem frischen Clone oder Verzeichniswechsel nötig.
Werden sie übersprungen, schlagen Services oder Tests fehl.

## 1. PostgreSQL TLS-Zertifikate generieren

Die Zertifikate sind in `.gitignore` und müssen pro Maschine neu erzeugt werden.

```bash
bash scripts/generate-pg-certs.sh infra/postgres/certs
```

Erwartetes Ergebnis: `infra/postgres/certs/` enthält `ca.crt`, `ca.key`, `server.crt`, `server.key`.

## 2. Verzeichnisse mit korrektem Besitzer anlegen

Der Container-User hat UID/GID **1234** (`app_user:app_group`).
Folgende Verzeichnisse müssen existieren und 1234 gehören:

```bash
# logs/ (vom Repo als leeres Verzeichnis vorhanden, aber evtl. root-owned)
sudo chown 1234:1234 logs/

# media/ und incoming_invoices/ existieren nicht im Repo → anlegen
mkdir -p project_root/media project_root/incoming_invoices
sudo chown 1234:1234 project_root/media project_root/incoming_invoices
```

**Auswirkung wenn vergessen:**
- `logs/`: Tests laufen mit `--- Logging error ---` (PermissionError auf `erechnung.log`)
- `media/`: PDF/XML-Download-Tests schlagen mit 500 fehl (`PermissionError: /app/project_root/media`)
- `incoming_invoices/`: `test_file_manager_real_initialization` schlägt mit `PermissionError` fehl

## 3. Docker-Netzwerk zurücksetzen (nach Verzeichniswechsel)

Nach einem Verzeichniswechsel gehört `erechnung-network` noch dem alten Compose-Projekt.
Docker Compose funktioniert trotzdem, gibt aber eine Warnung aus:

```
WARN: a network with name erechnung-network exists but was not created for project "erechnung"
```

Fix (kurze Downtime):

```bash
docker compose down && docker network rm erechnung-network && docker compose up -d
```

Das Netzwerk wird neu mit den korrekten Labels für das aktuelle Projekt angelegt.

## 4. SELinux: Volume-Mounts mit `:z`

Auf SELinux-Systemen (Fedora, RHEL, etc.) müssen alle Bind-Mounts das `:z`-Flag tragen,
sonst schlägt der Container-Start mit `EACCES` (exit 243) fehl.

In `docker-compose.yml` müssen alle `volumes:`-Einträge mit Bind-Mounts so aussehen:

```yaml
- ./project_root:/app/project_root:z
- ./logs:/app/logs:z
- ./frontend:/app:z
- ./frontend/.env.development:/app/.env.development:z
```

**Kein `:z`** bei anonymen Volumes (kein Host-Pfad):
```yaml
- /app/node_modules   # anonym → kein :z
```

## 5. node_modules — anonymes Volume (kein Bind-Mount)

`frontend/node_modules` darf **nicht** als Bind-Mount gemountet werden.
Ein leeres Host-Verzeichnis würde die im Image installierten Pakete überschreiben → exit 127.

Korrekt in `docker-compose.yml`:
```yaml
volumes:
  - ./frontend:/app:z
  - /app/node_modules          # anonym — KEIN ./frontend/node_modules:/app/node_modules
  - ./frontend/.env.development:/app/.env.development:z
```

## Komplette Startsequenz (frischer Clone)

```bash
# 1. TLS-Zertifikate
bash scripts/generate-pg-certs.sh infra/postgres/certs

# 2. Images bauen und Services starten
docker compose build
docker compose up -d

# 3. Verzeichnisse korrigieren (nach erstem Up)
sudo chown 1234:1234 logs/
mkdir -p project_root/media project_root/incoming_invoices
sudo chown 1234:1234 project_root/media project_root/incoming_invoices

# 4. Backend-Tests
bash scripts/run_tests_docker.sh

# 5. Frontend-Tests
docker compose exec frontend npm run test -- --run
```

## Erwartete Testergebnisse (Stand 2026-04)

| Test-Suite | Ergebnis |
|------------|----------|
| Backend (Django) | 730 tests, OK, 5 skipped |
| Frontend (Vitest) | 47 files, 726 tests, all passed |
