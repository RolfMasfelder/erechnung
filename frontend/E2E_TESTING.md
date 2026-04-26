# E2E Testing mit Playwright

## Setup

### Option 1: Playwright Image (Empfohlen für E2E-Tests)

**Image:** `mcr.microsoft.com/playwright:v1.56.1-noble` (Ubuntu 24.04 LTS)
**Größe:** ~2.86 GB
**Enthält:** Chromium, Firefox, WebKit + alle System-Dependencies

```bash
# 1. Backend-Services starten
docker-compose up -d

# 2. E2E Frontend Container bauen
docker-compose -f docker-compose.e2e.yml build frontend-e2e

# 3. E2E Frontend starten
docker-compose -f docker-compose.e2e.yml up frontend-e2e

# 4. Tests ausführen (in separatem Terminal)
docker-compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e

# 5. Aufräumen
docker-compose -f docker-compose.e2e.yml down
```

### Option 2: Alpine Image (Nur für Development)

**Image:** `node:alpine`
**Größe:** ~319 MB
**Problem:** Keine Browser-Support, benötigt manuelle Installation

```bash
# Aktuelles Setup (ohne E2E-Tests)
docker-compose -f docker-compose.frontend.yml up
```

## Reproduzierbarkeit

Alle Abhängigkeiten werden automatisch aus `package.json` + `package-lock.json` installiert:

```json
{
  "devDependencies": {
    "@playwright/test": "^1.56.1"
  }
}
```

Der `package-lock.json` garantiert **exakt dieselben Versionen** bei jedem Build.

## Browser-Verfügbarkeit

### Playwright Image
- ✅ **Chromium 141.0.7390.37** (vorinstalliert)
- ✅ **Firefox 137.0** (vorinstalliert)
- ✅ **WebKit 18.4** (vorinstalliert)

### Alpine Image
- ❌ **Chromium** - Manuelle Installation erforderlich (Alpine apk)
- ❌ **Firefox/WebKit** - Nicht verfügbar für musl libc

## Image-Größen-Vergleich

| Image | Basis | Größe | Browser | E2E-Tests |
|-------|-------|-------|---------|-----------|
| `node:alpine` | Alpine Linux 3.22 | 319 MB | ❌ | ❌ |
| `mcr.microsoft.com/playwright:v1.56.1-noble` | Ubuntu 24.04 LTS | 2.86 GB | ✅ | ✅ |

## Empfehlung

**Development**: Alpine Image (klein, schnell)
**E2E-Tests**: Playwright Image (vollständig, zuverlässig)
**CI/CD**: Playwright Image (garantierte Browser-Kompatibilität)

## Weitere Infos

- [Playwright Docker Dokumentation](https://playwright.dev/docs/docker)
- [Microsoft Playwright Images](https://mcr.microsoft.com/en-us/product/playwright/about)
