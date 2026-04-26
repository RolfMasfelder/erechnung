# Playwright E2E Testing für eRechnung Frontend

## Übersicht

Playwright End-to-End Tests für das Vue.js Frontend mit Container-Only Setup.

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions Runner                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Docker Compose Network                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │   Frontend   │  │ API Gateway  │  │   Django    │ │ │
│  │  │   (Vite)     │  │   (Nginx)    │  │   Backend   │ │ │
│  │  │ localhost:   │  │ localhost:   │  │             │ │ │
│  │  │   5173       │◄─┤   443        │◄─┤   8000      │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  │         ▲                                              │ │
│  │         │ HTTP Requests                                │ │
│  │  ┌──────┴──────────┐                                   │ │
│  │  │   Playwright    │                                   │ │
│  │  │   Container     │                                   │ │
│  │  │  (Chromium/FF)  │                                   │ │
│  │  └─────────────────┘                                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Playwright im Frontend-Container installieren

```bash
# In den Frontend-Container wechseln
docker-compose exec frontend sh

# Playwright installieren
npm install -D @playwright/test

# Browser-Binaries installieren (Chromium, Firefox, WebKit)
npx playwright install --with-deps chromium firefox
```

### 2. Dockerfile erweitern (für CI/CD)

Die `frontend/Dockerfile.dev` ist bereits playwright-ready, da sie auf Node Alpine basiert.
Für CI/CD wird ein separates Dockerfile für Tests verwendet (siehe unten).

## Projekt-Struktur

```
frontend/
├── tests/
│   ├── unit/                    # Existing Vitest tests
│   ├── e2e/                     # NEW: Playwright E2E tests
│   │   ├── auth/
│   │   │   ├── login.spec.js
│   │   │   └── token-refresh.spec.js
│   │   ├── invoices/
│   │   │   ├── invoice-list.spec.js
│   │   │   ├── invoice-create.spec.js
│   │   │   ├── invoice-edit.spec.js
│   │   │   └── invoice-download.spec.js
│   │   ├── customers/
│   │   │   ├── customer-crud.spec.js
│   │   │   └── customer-detail.spec.js
│   │   ├── products/
│   │   │   └── product-crud.spec.js
│   │   ├── components/
│   │   │   ├── modals.spec.js
│   │   │   └── pagination.spec.js
│   │   └── fixtures/
│   │       ├── users.json
│   │       ├── invoices.json
│   │       └── mock-api.js
├── playwright.config.js         # Playwright config
├── package.json                 # Extended with e2e scripts
└── .env.test                    # Test environment variables
```

## Verwendung

### Lokal (im Container)

```bash
# Alle Tests ausführen
docker-compose exec frontend npm run test:e2e

# Tests mit UI (headed mode)
docker-compose exec frontend npm run test:e2e:headed

# Einzelnen Test ausführen
docker-compose exec frontend npx playwright test tests/e2e/auth/login.spec.js

# Debug-Mode
docker-compose exec frontend npx playwright test --debug

# Report öffnen
docker-compose exec frontend npx playwright show-report
```

### CI/CD (GitHub Actions)

Die Tests laufen automatisch bei:
- **Push** auf `feature/*` branches
- **Pull Requests** nach `main` oder `develop`

Siehe `.github/workflows/e2e-tests.yml` für Details.

## Test-Patterns

### 1. Authentication Helper

```javascript
// tests/e2e/fixtures/auth.js
export async function login(page, username = 'admin', password = 'admin123') {
  await page.goto('/login')
  await page.fill('input[name="username"]', username)
  await page.fill('input[name="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/dashboard')
}
```

### 2. API Mocking

```javascript
// tests/e2e/fixtures/mock-api.js
export async function mockInvoiceListAPI(context, invoices = []) {
  await context.route('**/api/invoices/**', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: invoices.length,
        results: invoices
      })
    })
  })
}
```

### 3. Page Object Model (Optional)

```javascript
// tests/e2e/pages/InvoiceListPage.js
export class InvoiceListPage {
  constructor(page) {
    this.page = page
    this.createButton = page.locator('[data-testid="create-invoice"]')
    this.searchInput = page.locator('input[placeholder*="Suche"]')
  }

  async goto() {
    await this.page.goto('/invoices')
  }

  async search(query) {
    await this.searchInput.fill(query)
    await this.page.waitForTimeout(600) // Debounce
  }

  async clickCreate() {
    await this.createButton.click()
  }
}
```

## Best Practices

### 1. Test-IDs verwenden

```vue
<!-- InvoiceListView.vue -->
<button data-testid="create-invoice" @click="showCreateModal = true">
  Neue Rechnung
</button>
```

```javascript
// Test
await page.click('[data-testid="create-invoice"]')
```

### 2. Warten auf API-Responses

```javascript
// Warten auf spezifische API-Calls
await page.waitForResponse(response =>
  response.url().includes('/api/invoices/') && response.status() === 200
)
```

### 3. Screenshots bei Fehlern

```javascript
test('invoice creation', async ({ page }) => {
  try {
    // ... test code
  } catch (error) {
    await page.screenshot({ path: 'debug-invoice-create.png', fullPage: true })
    throw error
  }
})
```

### 4. Parallele Tests vermeiden (Shared State)

```javascript
// playwright.config.js
workers: 1 // In CI: Sequenziell ausführen wegen Datenbank-State
```

## Environment Variables

### `.env.test`

```env
VITE_API_BASE_URL=https://api-gateway/api
PLAYWRIGHT_BASE_URL=https://frontend:5173
NODE_TLS_REJECT_UNAUTHORIZED=0  # Self-signed certs
```

## Troubleshooting

### Problem: "Browser not found"

```bash
# Browser neu installieren
docker-compose exec frontend npx playwright install chromium
```

### Problem: "Connection refused"

```bash
# Sicherstellen, dass alle Services laufen
docker-compose ps

# Frontend muss erreichbar sein
curl -k https://localhost:5173
```

### Problem: "Timeout waiting for selector"

```javascript
// Explizites Warten verwenden
await page.waitForSelector('[data-testid="invoice-list"]', { timeout: 30000 })
```

### Problem: "Self-signed certificate"

```javascript
// In playwright.config.js bereits konfiguriert:
ignoreHTTPSErrors: true
```

## Performance-Tipps

1. **Parallele Execution deaktivieren** in CI (Datenbank-Konflikte)
2. **Selektive Tests** bei PR-Reviews (nur geänderte Features)
3. **Browser cachen** in GitHub Actions (siehe Workflow)
4. **API-Mocking** wo möglich (schneller als echte Requests)

## Metriken

Nach vollständigem Setup erwartete Werte:
- **Test-Abdeckung:** ~15-20 E2E-Tests
- **Ausführungszeit:** ~3-5 Minuten (lokal), ~5-8 Minuten (CI)
- **Flaky-Rate:** <5% (durch Auto-Waiting)

## Weiterführende Dokumentation

- [Playwright Docs](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Docker Guide](https://playwright.dev/docs/docker)
