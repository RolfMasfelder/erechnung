# E2E Testing Guide

## Übersicht

Die E2E-Tests laufen **ausschließlich in Docker-Containern**. Es wird **nichts auf dem Host installiert**.

## Architektur

```
┌─────────────────────────────────────────────────────────┐
│ E2E Test Container (mcr.microsoft.com/playwright)      │
│                                                         │
│  ├── Vite Dev Server (Port 5173 intern)                │
│  ├── Playwright + Chromium/Firefox/WebKit              │
│  └── Tests unter /app/tests/e2e/                       │
└─────────────────────────────────────────────────────────┘
           │                     │
           ├─ Port 5174 (Host)  │ Port 9323 (Reports)
           │                     │
           ▼                     ▼
    Vite Frontend         HTML Test Reports
```

## Port-Mapping

| Service | Container-Port | Host-Port | Verwendung |
|---------|---------------|-----------|------------|
| Vite Dev Server | 5173 | 5174 | Frontend für Tests |
| Playwright Report | 9323 | 9323 | HTML-Reports |

**Wichtig:** Normales Frontend läuft auf `localhost:5173`, E2E-Frontend auf `localhost:5174`

## Quick Start

### 1. Vollautomatischer Test-Run (EMPFOHLEN)

```bash
./run_e2e_container.sh
```

Dieser Befehl:
- Startet Backend (falls nötig)
- Startet E2E-Frontend-Container
- Wartet bis Vite bereit ist
- Führt alle Playwright-Tests aus
- Zeigt Ergebnis an

### 2. Manueller Workflow

```bash
# 1. Setup (einmalig nach Code-Änderungen)
./setup_e2e.sh

# 2. Frontend-Container starten
docker compose -f docker-compose.e2e.yml up -d frontend-e2e

# 3. Warten bis bereit
./wait_for_frontend_e2e.sh

# 4. Tests ausführen
docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e

# 5. Cleanup
docker compose -f docker-compose.e2e.yml down
```

## Test-Kommandos (im Container)

```bash
# Alle Tests
docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e

# Spezifische Tests
docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e tests/e2e/auth/

# Mit UI (headed mode)
docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e:headed

# HTML-Report anzeigen
docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e:report
# Oder: http://localhost:9323
```

## Debugging

### Status prüfen

```bash
./debug_e2e.sh
```

Zeigt:
- Container-Status
- Port-Bindings
- Vite-Server-Status (intern)
- Netzwerk-Konfiguration
- Letzte 30 Log-Zeilen

### Live-Logs verfolgen

```bash
docker compose -f docker-compose.e2e.yml logs -f frontend-e2e
```

### Shell im Container

```bash
docker compose -f docker-compose.e2e.yml exec frontend-e2e bash

# Im Container dann:
npm run dev          # Vite manuell starten
curl http://localhost:5173  # Vite testen
npx playwright test --help  # Playwright-Optionen
```

### Häufige Probleme

#### Problem: "Container not running"

```bash
docker compose -f docker-compose.e2e.yml up -d frontend-e2e
```

#### Problem: "Vite not responding"

```bash
# Logs prüfen
docker compose -f docker-compose.e2e.yml logs frontend-e2e

# Container neu starten
docker compose -f docker-compose.e2e.yml restart frontend-e2e

# Kompletter Rebuild
docker compose -f docker-compose.e2e.yml down
docker compose -f docker-compose.e2e.yml build --no-cache frontend-e2e
docker compose -f docker-compose.e2e.yml up -d frontend-e2e
```

#### Problem: Port-Konflikt

Normales Frontend und E2E-Frontend können gleichzeitig laufen:
- Normales Frontend: `http://localhost:5173`
- E2E-Frontend: `http://localhost:5174`

Wenn Port-Probleme auftreten:
```bash
# Welcher Container nutzt welchen Port?
docker ps | grep "5173\|5174"
```

## Test-Struktur

```
frontend/tests/e2e/
├── auth/
│   ├── login.spec.js           # Authentifizierung
│   └── token-refresh.spec.js   # Token-Erneuerung
├── components/
│   ├── modals.spec.js          # Modal-Interaktionen
│   └── pagination.spec.js      # Pagination
├── features/
│   ├── bulk-operations.spec.js # Bulk-Delete/Select
│   ├── datepicker.spec.js      # DatePicker
│   ├── export.spec.js          # CSV-Export
│   ├── filters.spec.js         # Filter-Funktionen
│   └── import.spec.js          # CSV-Import
└── basic-e2e.spec.js           # Smoke-Tests
```

## CI/CD Integration

Die E2E-Tests können in GitHub Actions ausgeführt werden:

```yaml
- name: Run E2E Tests
  run: ./run_e2e_container.sh
```

## Best Practices

1. **Tests isoliert halten**: Jeder Test sollte unabhängig laufen können
2. **Fixtures nutzen**: Testdaten über `tests/e2e/fixtures/*.ts`
3. **Page Objects**: Wiederverwendbare Selektoren in `tests/e2e/pages/*.ts`
4. **Cleanup**: Tests sollten nach sich aufräumen (Löschen von Test-Daten)

## Referenzen

- [Playwright Docs](https://playwright.dev/docs/intro)
- [Vite Testing](https://vitejs.dev/guide/api-javascript.html#createserver)
- [Docker Compose Docs](https://docs.docker.com/compose/)
