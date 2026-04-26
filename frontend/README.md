# eRechnung Frontend

Vue.js 3 Frontend für das eRechnung ZUGFeRD Invoice Management System.

## Tech Stack

- **Vue.js**: 3.5.24
- **Vite**: 7.2.2
- **Vue Router**: 4.6.3
- **Pinia**: 3.0.4 (State Management)
- **Axios**: 1.13.2
- **Tailwind CSS**: 4.1.17
- **Vitest**: 4.0.8 (Testing)
- **Node**: 25.1.0 (Alpine)

## Development

### Mit Docker (empfohlen)

```bash
# Backend + API-Gateway starten (falls nicht schon läuft)
docker-compose up -d

# Frontend mit API-Gateway starten
docker-compose -f docker-compose.frontend.yml up

# Browser öffnen
http://localhost:5173
```

**Wichtig:** Das Frontend verbindet sich direkt via HTTPS zum API-Gateway (`https://localhost/api`).
Beim ersten Zugriff muss das selbst-signierte Zertifikat im Browser akzeptiert werden:

1. Öffne `https://localhost/api/health/` im Browser
2. Akzeptiere das Sicherheits-Risiko (selbst-signiertes Zertifikat)
3. Danach funktionieren API-Calls vom Frontend

### Lokal (ohne Docker)

```bash
cd frontend

# Dependencies installieren
npm install

# Dev-Server starten
npm run dev

# Tests ausführen
npm run test

# Production Build
npm run build
```

## Projekt-Struktur

```
frontend/
├── src/
│   ├── api/           # API Client & Services
│   ├── components/    # Vue Komponenten
│   ├── composables/   # Vue Composables
│   ├── router/        # Vue Router
│   ├── stores/        # Pinia Stores
│   ├── views/         # Page Components
│   ├── App.vue
│   ├── main.js
│   └── style.css
├── public/            # Statische Assets
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

## Verfügbare npm Scripts

- `npm run dev` - Dev-Server mit Hot Reload
- `npm run build` - Production Build
- `npm run preview` - Preview Production Build
- `npm run test` - Unit Tests mit Vitest
- `npm run test:ui` - Vitest UI
- `npm run test:coverage` - Coverage Report

## API-Verbindung

Das Frontend verbindet sich **direkt via HTTPS** zum API-Gateway - kein Vite-Proxy.
Dies entspricht dem Production-Setup (K8s Ingress).

| Environment | API URL |
|-------------|---------|
| Development | `https://localhost/api` (direkt zum API-Gateway) |
| Production  | `/api` (relativ, via K8s Ingress) |

### Zertifikat im Browser akzeptieren

Da in der Entwicklung selbst-signierte Zertifikate verwendet werden:

```bash
# Einmalig: CA-Zertifikat im System installieren (optional)
# Linux:
sudo cp api-gateway/certs/ca.crt /usr/local/share/ca-certificates/erechnung-dev-ca.crt
sudo update-ca-certificates

# Oder: Im Browser https://localhost/health aufrufen und Zertifikat akzeptieren
```

## Deployment

Production Build wird in einem Nginx-Container bereitgestellt (siehe `Dockerfile.prod`).
