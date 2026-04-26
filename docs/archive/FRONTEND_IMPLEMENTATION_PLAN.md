# Frontend Implementation Plan: Vue.js + Vite in Docker

**Erstellt:** 2025-11-11
**Letzte Aktualisierung:** 2025-11-26
**Status:** PHASE 4 ABGESCHLOSSEN, E2E-TESTS LAUFEN
**Framework:** Vue.js 3 (Composition API)
**Build Tool:** Vite
**Containerization:** Docker + Docker Compose
**Backend API:** Django REST Framework (bereits vollständig implementiert)

---

## Übersicht

Implementierung einer modernen Single-Page Application (SPA) als Frontend für das eRechnung-System. Das Frontend wird in einem separaten Docker-Container laufen und über die REST API mit dem Django-Backend kommunizieren.

### Design-Entscheidungen

1. **Framework-Agnostisch:** Strikte Trennung zwischen UI-Komponenten und API-Client → späterer Wechsel zu React möglich
2. **Docker-First:** Keine Node.js/npm-Installation auf Host-System erforderlich
3. **Hot Reload:** Vite Dev-Server mit Volume-Mounts für lokale Entwicklung
4. **Production-Ready:** Nginx-basiertes Serving der statischen Build-Artefakte
5. **API-Proxy:** Nginx-Routing für `/api/*` → Django-Backend (CORS-vermeidung)

### Architektur-Prinzipien

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                    │
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐  │
│  │   Frontend   │──────│  API Gateway │──────│  Django   │  │
│  │ (Vite/Vue.js)│ HTTP │   (Nginx)    │ HTTP │  Backend  │  │
│  │  Port: 5173  │      │  Port: 80    │      │ Port: 8000│  │
│  └──────────────┘      └──────────────┘      └───────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Container-Setup & Projekt-Initialisierung

**Ziel:** Funktionierende Vue.js + Vite Entwicklungsumgebung in Docker

### 1.1 Dockerfile für Frontend

**Datei:** `frontend/Dockerfile.dev`

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Package-Installation cachen
COPY package*.json ./
RUN npm ci

# Source-Code
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**Datei:** `frontend/Dockerfile.prod`

```dockerfile
# Build-Stage
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production-Stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 1.2 Docker Compose Integration

**Datei:** `docker-compose.frontend.yml`

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: erechnung_frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules  # Prevent overwriting node_modules
    environment:
      - NODE_ENV=development
      - VITE_API_BASE_URL=http://localhost/api
    networks:
      - erechnung-network
    depends_on:
      - web
      - api-gateway

networks:
  erechnung-network:
    external: true
```

### 1.3 Vite + Vue.js Projekt initialisieren

**Ausführung im Container:**

```bash
# Temporärer Container zum Initialisieren
docker run --rm -v $(pwd)/frontend:/app -w /app node:20-alpine sh -c "npm create vite@latest . -- --template vue"

# Dependencies installieren (wird bei docker-compose build automatisch gemacht)
docker-compose -f docker-compose.frontend.yml build
```

### 1.4 Vite-Konfiguration

**Datei:** `frontend/vite.config.js`

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true  // Wichtig für Docker unter Windows/Mac
    },
    proxy: {
      '/api': {
        target: 'http://api-gateway',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild'
  }
})
```

### 1.5 Tests

- [x] Container baut erfolgreich: `docker-compose -f docker-compose.frontend.yml build`
- [x] Dev-Server startet: `docker-compose -f docker-compose.frontend.yml up`
- [x] Hot Reload funktioniert: Datei ändern → Browser aktualisiert automatisch
- [x] Vite-Proxy leitet `/api` Anfragen weiter
- [x] Production-Build erstellt optimierte Artefakte

### 1.6 Dokumentation

- [x] README.md im `frontend/` Verzeichnis mit Entwicklungs-Workflow
- [x] npm Scripts dokumentieren (`dev`, `build`, `preview`)
- [x] Docker-Kommandos für häufige Aufgaben

**Dauer:** 1-2 Tage
**Status:** ✅ ABGESCHLOSSEN
**Ergebnis:** Funktionierende Container-Umgebung mit Vue.js + Vite

---

## Phase 2: API-Client & Authentifizierung ✅

**Ziel:** Saubere Abstraktion der REST API + JWT-Authentifizierung
**Status:** ✅ ABGESCHLOSSEN

### 2.1 Axios-basierter API-Client

**Datei:** `frontend/src/api/client.js`

```javascript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request-Interceptor: JWT-Token hinzufügen
apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('jwt_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Response-Interceptor: 401 → Logout
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

### 2.2 Service-Layer (Framework-agnostisch)

**Datei:** `frontend/src/api/services/authService.js`

```javascript
import apiClient from '../client'

export const authService = {
  async login(username, password) {
    const response = await apiClient.post('/token/', { username, password })
    const { access, refresh } = response.data
    localStorage.setItem('jwt_token', access)
    localStorage.setItem('refresh_token', refresh)
    return response.data
  },

  async refreshToken() {
    const refresh = localStorage.getItem('refresh_token')
    const response = await apiClient.post('/token/refresh/', { refresh })
    localStorage.setItem('jwt_token', response.data.access)
    return response.data
  },

  logout() {
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('refresh_token')
  },

  isAuthenticated() {
    return !!localStorage.getItem('jwt_token')
  }
}
```

**Datei:** `frontend/src/api/services/invoiceService.js`

```javascript
import apiClient from '../client'

export const invoiceService = {
  async getAll(params = {}) {
    const response = await apiClient.get('/invoices/', { params })
    return response.data
  },

  async getById(id) {
    const response = await apiClient.get(`/invoices/${id}/`)
    return response.data
  },

  async create(data) {
    const response = await apiClient.post('/invoices/', data)
    return response.data
  },

  async update(id, data) {
    const response = await apiClient.put(`/invoices/${id}/`, data)
    return response.data
  },

  async delete(id) {
    await apiClient.delete(`/invoices/${id}/`)
  },

  async downloadPDF(id) {
    const response = await apiClient.get(`/invoices/${id}/download_pdf/`, {
      responseType: 'blob'
    })
    return response.data
  },

  async downloadXML(id) {
    const response = await apiClient.get(`/invoices/${id}/download_xml/`, {
      responseType: 'blob'
    })
    return response.data
  }
}
```

**Analog:** `companyService.js`, `customerService.js`, `productService.js`, `attachmentService.js`

### 2.3 Vue.js Composables (State Management)

**Datei:** `frontend/src/composables/useAuth.js`

```javascript
import { ref, computed } from 'vue'
import { authService } from '@/api/services/authService'

const isAuthenticated = ref(authService.isAuthenticated())
const currentUser = ref(null)

export function useAuth() {
  const login = async (username, password) => {
    await authService.login(username, password)
    isAuthenticated.value = true
    // TODO: User-Profil laden
  }

  const logout = () => {
    authService.logout()
    isAuthenticated.value = false
    currentUser.value = null
  }

  return {
    isAuthenticated: computed(() => isAuthenticated.value),
    currentUser: computed(() => currentUser.value),
    login,
    logout
  }
}
```

### 2.4 Tests

**Unit-Tests mit Vitest:**

```javascript
// frontend/src/api/services/__tests__/authService.test.js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authService } from '../authService'
import apiClient from '../../client'

vi.mock('../../client')

describe('authService', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should login and store tokens', async () => {
    apiClient.post.mockResolvedValue({
      data: { access: 'token123', refresh: 'refresh456' }
    })

    await authService.login('user', 'pass')

    expect(localStorage.getItem('jwt_token')).toBe('token123')
    expect(localStorage.getItem('refresh_token')).toBe('refresh456')
  })

  it('should logout and clear tokens', () => {
    localStorage.setItem('jwt_token', 'token123')
    authService.logout()
    expect(localStorage.getItem('jwt_token')).toBeNull()
  })
})
```

**Integration-Tests:**

- [x] Login mit korrekten Credentials → Token erhalten
- [x] Login mit falschen Credentials → 401 Fehler
- [x] API-Call mit Token → 200 OK
- [x] API-Call ohne Token → 401 Unauthorized
- [x] Token-Refresh bei Ablauf

### 2.5 Konfiguration

**Datei:** `frontend/.env.development`

```
VITE_API_BASE_URL=http://localhost/api
```

**Datei:** `frontend/.env.production`

```
VITE_API_BASE_URL=/api
```

**Dauer:** 2-3 Tage
**Status:** ✅ ABGESCHLOSSEN
**Ergebnis:** Wiederverwendbarer API-Client mit JWT-Auth, vollständig getestet

**Implementierte Services:**
- [x] authService (Login, Logout, Token-Refresh, User-Profil)
- [x] invoiceService (CRUD, PDF/XML-Download, Validate, Status)
- [x] companyService (CRUD)
- [x] customerService (CRUD)
- [x] productService (CRUD)
- [x] attachmentService (Upload, Download)

---

## Phase 3: Basis-Komponenten & Routing ✅

**Ziel:** Wiederverwendbare UI-Komponenten + Navigation
**Status:** ✅ ABGESCHLOSSEN

### 3.1 Vue Router Setup

**Installation:**

```bash
docker-compose -f docker-compose.frontend.yml exec frontend npm install vue-router@4
```

**Datei:** `frontend/src/router/index.js`

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import { authService } from '@/api/services/authService'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/invoices',
    name: 'InvoiceList',
    component: () => import('@/views/InvoiceListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/invoices/:id',
    name: 'InvoiceDetail',
    component: () => import('@/views/InvoiceDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/customers',
    name: 'CustomerList',
    component: () => import('@/views/CustomerListView.vue'),
    meta: { requiresAuth: true }
  },
  // ... weitere Routes
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation Guard
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !authService.isAuthenticated()) {
    next('/login')
  } else {
    next()
  }
})

export default router
```

### 3.2 Basis-Komponenten (Framework-agnostisch vorbereitet)

**Datei:** `frontend/src/components/BaseButton.vue`

```vue
<template>
  <button
    :type="type"
    :class="buttonClasses"
    :disabled="disabled || loading"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="spinner"></span>
    <slot v-else></slot>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: 'button' },
  variant: { type: String, default: 'primary' }, // primary, secondary, danger
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['click'])

const buttonClasses = computed(() => ({
  'btn': true,
  [`btn-${props.variant}`]: true,
  'btn-loading': props.loading
}))
</script>

<style scoped>
.btn {
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s;
}
.btn-primary { background-color: #007bff; color: white; }
.btn-secondary { background-color: #6c757d; color: white; }
.btn-danger { background-color: #dc3545; color: white; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spinner { /* Spinner-Animation */ }
</style>
```

**Weitere Basis-Komponenten:**

- `BaseInput.vue` - Formular-Eingabefelder
- `BaseSelect.vue` - Dropdown-Auswahl
- `BaseTable.vue` - Datentabellen mit Sortierung/Pagination
- `BaseModal.vue` - Modale Dialoge
- `BaseCard.vue` - Container-Komponente
- `BaseAlert.vue` - Benachrichtigungen/Fehlermeldungen
- `BasePagination.vue` - Seitennavigation

### 3.3 Layout-Komponenten

**Datei:** `frontend/src/components/AppLayout.vue`

```vue
<template>
  <div class="app-layout">
    <AppHeader />
    <div class="app-content">
      <AppSidebar />
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
</script>
```

**Datei:** `frontend/src/components/AppHeader.vue`

```vue
<template>
  <header class="app-header">
    <h1>eRechnung System</h1>
    <nav>
      <span>{{ currentUser?.username }}</span>
      <BaseButton variant="secondary" @click="handleLogout">
        Abmelden
      </BaseButton>
    </nav>
  </header>
</template>

<script setup>
import { useAuth } from '@/composables/useAuth'
import { useRouter } from 'vue-router'
import BaseButton from './BaseButton.vue'

const { currentUser, logout } = useAuth()
const router = useRouter()

const handleLogout = () => {
  logout()
  router.push('/login')
}
</script>
```

**Datei:** `frontend/src/components/AppSidebar.vue`

```vue
<template>
  <aside class="app-sidebar">
    <nav>
      <router-link to="/">Dashboard</router-link>
      <router-link to="/invoices">Rechnungen</router-link>
      <router-link to="/customers">Kunden</router-link>
      <router-link to="/products">Produkte</router-link>
      <router-link to="/companies">Firmen</router-link>
    </nav>
  </aside>
</template>
```

### 3.4 Tests

**Component-Tests mit Vitest + Vue Test Utils:**

```javascript
// frontend/src/components/__tests__/BaseButton.test.js
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseButton from '../BaseButton.vue'

describe('BaseButton', () => {
  it('renders slot content', () => {
    const wrapper = mount(BaseButton, {
      slots: { default: 'Click me' }
    })
    expect(wrapper.text()).toContain('Click me')
  })

  it('emits click event', async () => {
    const wrapper = mount(BaseButton)
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('is disabled when loading', () => {
    const wrapper = mount(BaseButton, {
      props: { loading: true }
    })
    expect(wrapper.find('button').element.disabled).toBe(true)
  })
})
```

**E2E-Tests mit Playwright:**

```javascript
// frontend/e2e/navigation.spec.js
import { test, expect } from '@playwright/test'

test('navigates to invoice list', async ({ page }) => {
  await page.goto('http://localhost:5173/login')

  // Login
  await page.fill('[name="username"]', 'testuser')
  await page.fill('[name="password"]', 'testpass')
  await page.click('button[type="submit"]')

  // Navigate
  await page.click('text=Rechnungen')
  await expect(page).toHaveURL(/\/invoices/)
  await expect(page.locator('h1')).toContainText('Rechnungen')
})
```

**Test-Checkliste:**

- [x] Alle Basis-Komponenten rendern korrekt
- [x] Router-Navigation funktioniert
- [x] Auth-Guard blockiert unauthentifizierte Zugriffe
- [x] Logout leitet zu Login-Seite um
- [x] Responsive Design (Mobile/Tablet/Desktop)

**Dauer:** 3-4 Tage
**Ergebnis:** ✅ Vollständiges UI-Framework mit Navigation und wiederverwendbaren Komponenten

---

## Phase 4: Feature-Views (Rechnungen, Kunden, Produkte) ✅ ABGESCHLOSSEN

**Ziel:** Vollständige CRUD-Funktionalität für alle Hauptentitäten

### 4.1 Invoice List View

**Datei:** `frontend/src/views/InvoiceListView.vue`

```vue
<template>
  <div class="invoice-list">
    <h1>Rechnungen</h1>

    <div class="controls">
      <BaseInput
        v-model="searchQuery"
        placeholder="Suche..."
        @input="handleSearch"
      />
      <BaseButton @click="showCreateModal = true">
        Neue Rechnung
      </BaseButton>
    </div>

    <BaseTable
      :columns="columns"
      :data="invoices"
      :loading="loading"
      @row-click="handleRowClick"
      @sort="handleSort"
    />

    <BasePagination
      :current-page="currentPage"
      :total-pages="totalPages"
      @page-change="handlePageChange"
    />

    <InvoiceCreateModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleInvoiceCreated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { invoiceService } from '@/api/services/invoiceService'
import BaseTable from '@/components/BaseTable.vue'
import BaseInput from '@/components/BaseInput.vue'
import BaseButton from '@/components/BaseButton.vue'
import BasePagination from '@/components/BasePagination.vue'
import InvoiceCreateModal from '@/components/InvoiceCreateModal.vue'

const router = useRouter()
const invoices = ref([])
const loading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const searchQuery = ref('')
const showCreateModal = ref(false)

const columns = [
  { key: 'invoice_number', label: 'Rechnungsnummer', sortable: true },
  { key: 'customer_name', label: 'Kunde', sortable: true },
  { key: 'invoice_date', label: 'Datum', sortable: true },
  { key: 'total_gross', label: 'Betrag', sortable: true, format: 'currency' },
  { key: 'status', label: 'Status', sortable: true }
]

const fetchInvoices = async (params = {}) => {
  loading.value = true
  try {
    const response = await invoiceService.getAll({
      page: currentPage.value,
      search: searchQuery.value,
      ...params
    })
    invoices.value = response.results
    totalPages.value = Math.ceil(response.count / 20)
  } catch (error) {
    console.error('Fehler beim Laden der Rechnungen:', error)
  } finally {
    loading.value = false
  }
}

const handleRowClick = (invoice) => {
  router.push(`/invoices/${invoice.id}`)
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchInvoices()
}

const handleSearch = () => {
  currentPage.value = 1
  fetchInvoices()
}

const handleSort = ({ column, direction }) => {
  const ordering = direction === 'asc' ? column : `-${column}`
  fetchInvoices({ ordering })
}

const handleInvoiceCreated = () => {
  showCreateModal.value = false
  fetchInvoices()
}

onMounted(() => {
  fetchInvoices()
})
</script>
```

### 4.2 Invoice Detail View

**Datei:** `frontend/src/views/InvoiceDetailView.vue`

```vue
<template>
  <div v-if="invoice" class="invoice-detail">
    <div class="header">
      <h1>Rechnung {{ invoice.invoice_number }}</h1>
      <div class="actions">
        <BaseButton @click="downloadPDF">PDF herunterladen</BaseButton>
        <BaseButton @click="downloadXML">XML herunterladen</BaseButton>
        <BaseButton variant="secondary" @click="editInvoice">Bearbeiten</BaseButton>
        <BaseButton variant="danger" @click="deleteInvoice">Löschen</BaseButton>
      </div>
    </div>

    <BaseCard>
      <h2>Rechnungsinformationen</h2>
      <dl class="info-grid">
        <dt>Rechnungsnummer:</dt>
        <dd>{{ invoice.invoice_number }}</dd>

        <dt>Kunde:</dt>
        <dd>{{ invoice.customer_name }}</dd>

        <dt>Datum:</dt>
        <dd>{{ formatDate(invoice.invoice_date) }}</dd>

        <dt>Fälligkeitsdatum:</dt>
        <dd>{{ formatDate(invoice.due_date) }}</dd>

        <dt>Netto:</dt>
        <dd>{{ formatCurrency(invoice.total_net) }}</dd>

        <dt>MwSt.:</dt>
        <dd>{{ formatCurrency(invoice.total_vat) }}</dd>

        <dt>Brutto:</dt>
        <dd class="total">{{ formatCurrency(invoice.total_gross) }}</dd>
      </dl>
    </BaseCard>

    <BaseCard>
      <h2>Rechnungspositionen</h2>
      <BaseTable
        :columns="lineColumns"
        :data="invoice.invoice_lines"
      />
    </BaseCard>

    <BaseCard v-if="invoice.attachments?.length">
      <h2>Anhänge</h2>
      <ul>
        <li v-for="attachment in invoice.attachments" :key="attachment.id">
          <a :href="attachment.file_url" target="_blank">
            {{ attachment.file_name }}
          </a>
        </li>
      </ul>
    </BaseCard>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { invoiceService } from '@/api/services/invoiceService'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseTable from '@/components/BaseTable.vue'

const route = useRoute()
const router = useRouter()
const invoice = ref(null)

const lineColumns = [
  { key: 'position', label: 'Pos.' },
  { key: 'product_name', label: 'Produkt' },
  { key: 'quantity', label: 'Menge' },
  { key: 'unit_price_net', label: 'Einzelpreis', format: 'currency' },
  { key: 'vat_rate', label: 'MwSt.', format: 'percentage' },
  { key: 'line_total_gross', label: 'Gesamt', format: 'currency' }
]

const fetchInvoice = async () => {
  const id = route.params.id
  invoice.value = await invoiceService.getById(id)
}

const downloadPDF = async () => {
  const blob = await invoiceService.downloadPDF(invoice.value.id)
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${invoice.value.invoice_number}.pdf`
  a.click()
}

const downloadXML = async () => {
  const blob = await invoiceService.downloadXML(invoice.value.id)
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${invoice.value.invoice_number}.xml`
  a.click()
}

const editInvoice = () => {
  // TODO: Edit-Modal oder separate Edit-View
}

const deleteInvoice = async () => {
  if (confirm('Rechnung wirklich löschen?')) {
    await invoiceService.delete(invoice.value.id)
    router.push('/invoices')
  }
}

const formatDate = (date) => new Date(date).toLocaleDateString('de-DE')
const formatCurrency = (value) => new Intl.NumberFormat('de-DE', {
  style: 'currency',
  currency: 'EUR'
}).format(value)

onMounted(() => {
  fetchInvoice()
})
</script>
```

### 4.3 Weitere Views (analog)

- **CustomerListView.vue** - Kundenliste mit Suche/Filter
- **CustomerDetailView.vue** - Kundendetails mit Rechnungshistorie
- **ProductListView.vue** - Produktliste mit Kategorien
- **ProductDetailView.vue** - Produktdetails
- **CompanyListView.vue** - Firmenliste (Admin)
- **DashboardView.vue** - Übersicht mit Statistiken

### 4.4 Formular-Komponenten

**Datei:** `frontend/src/components/InvoiceCreateModal.vue`

```vue
<template>
  <BaseModal @close="$emit('close')">
    <h2>Neue Rechnung erstellen</h2>

    <form @submit.prevent="handleSubmit">
      <BaseSelect
        v-model="formData.customer"
        label="Kunde"
        :options="customers"
        option-label="name"
        option-value="id"
        required
      />

      <BaseInput
        v-model="formData.invoice_date"
        label="Rechnungsdatum"
        type="date"
        required
      />

      <BaseInput
        v-model="formData.due_date"
        label="Fälligkeitsdatum"
        type="date"
        required
      />

      <!-- Invoice Lines -->
      <div v-for="(line, index) in formData.invoice_lines" :key="index">
        <h3>Position {{ index + 1 }}</h3>
        <BaseSelect
          v-model="line.product"
          label="Produkt"
          :options="products"
          option-label="name"
          option-value="id"
        />
        <BaseInput
          v-model.number="line.quantity"
          label="Menge"
          type="number"
          step="0.01"
        />
        <BaseButton
          variant="danger"
          @click="removeLine(index)"
        >
          Entfernen
        </BaseButton>
      </div>

      <BaseButton type="button" @click="addLine">
        Position hinzufügen
      </BaseButton>

      <div class="form-actions">
        <BaseButton type="submit" :loading="loading">
          Speichern
        </BaseButton>
        <BaseButton
          type="button"
          variant="secondary"
          @click="$emit('close')"
        >
          Abbrechen
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { invoiceService } from '@/api/services/invoiceService'
import { customerService } from '@/api/services/customerService'
import { productService } from '@/api/services/productService'
import BaseModal from './BaseModal.vue'
import BaseInput from './BaseInput.vue'
import BaseSelect from './BaseSelect.vue'
import BaseButton from './BaseButton.vue'

const emit = defineEmits(['close', 'created'])

const loading = ref(false)
const customers = ref([])
const products = ref([])
const formData = ref({
  customer: null,
  invoice_date: new Date().toISOString().split('T')[0],
  due_date: null,
  invoice_lines: [
    { product: null, quantity: 1 }
  ]
})

const handleSubmit = async () => {
  loading.value = true
  try {
    await invoiceService.create(formData.value)
    emit('created')
  } catch (error) {
    console.error('Fehler beim Erstellen der Rechnung:', error)
    alert('Fehler beim Erstellen der Rechnung')
  } finally {
    loading.value = false
  }
}

const addLine = () => {
  formData.value.invoice_lines.push({ product: null, quantity: 1 })
}

const removeLine = (index) => {
  formData.value.invoice_lines.splice(index, 1)
}

onMounted(async () => {
  customers.value = (await customerService.getAll()).results
  products.value = (await productService.getAll()).results
})
</script>
```

### 4.5 Tests

**Feature-Tests:**

- [x] Rechnungsliste lädt Daten vom Backend
- [x] Suche filtert Rechnungen
- [x] Pagination funktioniert
- [x] Rechnungsdetails anzeigen
- [x] PDF/XML-Download funktioniert
- [x] Neue Rechnung erstellen
- [x] Rechnung bearbeiten (wenn implementiert)
- [x] Rechnung löschen (mit Bestätigung)
- [x] Analog für Kunden, Produkte, Firmen

**E2E-Tests:**

```javascript
// frontend/e2e/invoice.spec.js
import { test, expect } from '@playwright/test'

test('creates new invoice', async ({ page }) => {
  await page.goto('http://localhost:5173/invoices')

  await page.click('text=Neue Rechnung')
  await page.selectOption('[name="customer"]', { label: 'Testkunde GmbH' })
  await page.fill('[name="invoice_date"]', '2025-11-11')
  await page.fill('[name="due_date"]', '2025-12-11')

  // Erste Position
  await page.selectOption('[name="product_0"]', { label: 'Testprodukt' })
  await page.fill('[name="quantity_0"]', '5')

  await page.click('button:has-text("Speichern")')

  await expect(page.locator('.alert-success')).toContainText('Rechnung erstellt')
})
```

**Dauer:** 5-7 Tage
**Ergebnis:** Vollständige CRUD-Funktionalität für alle Hauptentitäten

---

## Phase 5: Styling & UX-Optimierung

**Ziel:** Professionelles Design und optimale Benutzererfahrung

### 5.1 CSS-Framework-Entscheidung

**Option A: Tailwind CSS** (empfohlen für Vite + Vue.js)

```bash
docker-compose -f docker-compose.frontend.yml exec frontend npm install -D tailwindcss postcss autoprefixer
docker-compose -f docker-compose.frontend.yml exec frontend npx tailwindcss init -p
```

**Datei:** `frontend/tailwind.config.js`

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#007bff',
        secondary: '#6c757d',
        success: '#28a745',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#17a2b8'
      }
    },
  },
  plugins: [],
}
```

**Option B: Bootstrap 5** (falls bevorzugt)

```bash
docker-compose -f docker-compose.frontend.yml exec frontend npm install bootstrap@5
```

### 5.2 Globale Styles

**Datei:** `frontend/src/assets/styles/main.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-primary: #007bff;
  --color-secondary: #6c757d;
  --color-success: #28a745;
  --color-danger: #dc3545;
  --color-warning: #ffc107;
  --color-info: #17a2b8;

  --font-family-base: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-size-base: 16px;
  --line-height-base: 1.5;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-family-base);
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  color: #333;
  background-color: #f5f5f5;
}

/* Layout */
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  background: var(--color-primary);
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-content {
  display: flex;
  flex: 1;
}

.app-sidebar {
  width: 250px;
  background: white;
  border-right: 1px solid #ddd;
  padding: 1rem;
}

.main-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

/* Responsive */
@media (max-width: 768px) {
  .app-content {
    flex-direction: column;
  }

  .app-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #ddd;
  }
}
```

### 5.3 UX-Features

**Loading States:**

```vue
<template>
  <div v-if="loading" class="loading-spinner">
    <div class="spinner"></div>
    <p>Lädt...</p>
  </div>
  <div v-else>
    <!-- Content -->
  </div>
</template>
```

**Error Handling:**

```vue
<template>
  <BaseAlert
    v-if="error"
    variant="danger"
    @close="error = null"
  >
    {{ error.message }}
  </BaseAlert>
</template>

<script setup>
import { ref } from 'vue'

const error = ref(null)

const handleError = (err) => {
  error.value = {
    message: err.response?.data?.detail || 'Ein Fehler ist aufgetreten'
  }
}
</script>
```

**Toast Notifications:**

```javascript
// frontend/src/composables/useToast.js
import { ref } from 'vue'

const toasts = ref([])

export function useToast() {
  const showToast = (message, variant = 'info') => {
    const id = Date.now()
    toasts.value.push({ id, message, variant })

    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 5000)
  }

  return {
    toasts,
    showToast,
    success: (msg) => showToast(msg, 'success'),
    error: (msg) => showToast(msg, 'danger'),
    info: (msg) => showToast(msg, 'info')
  }
}
```

### 5.4 Accessibility (A11y)

- [x] Alle Formularfelder haben `<label>`
- [x] Buttons haben aussagekräftige Texte (kein "Klick hier")
- [x] Fokus-Indikatoren sichtbar
- [x] ARIA-Attribute für komplexe Komponenten
- [x] Keyboard-Navigation funktioniert
- [x] Farbkontrast WCAG AA konform

### 5.5 Performance-Optimierung

**Code-Splitting:**

```javascript
// Lazy Loading von Routes
const routes = [
  {
    path: '/invoices',
    component: () => import('@/views/InvoiceListView.vue')
  }
]
```

**Virtuelles Scrolling für große Listen:**

```bash
docker-compose -f docker-compose.frontend.yml exec frontend npm install vue-virtual-scroller
```

**Bildoptimierung:**

- WebP-Format verwenden
- Lazy Loading mit `loading="lazy"`
- Responsive Images mit `srcset`

### 5.6 Tests

- [x] Responsive Design auf allen Breakpoints (manuell getestet, dokumentiert in Protocol)
- [ ] Lighthouse-Score > 90 (Performance, Accessibility, Best Practices)
- [ ] Cross-Browser-Kompatibilität (Chrome, Firefox, Safari, Edge)
- [ ] Dark Mode (optional)

**Dauer:** 3-4 Tage
**Ergebnis:** Professionelles, benutzerfreundliches Frontend

---

## Phase 6: Production-Deployment & CI/CD

**Ziel:** Automatisiertes Deployment mit optimierten Builds

### 6.1 Production Docker Setup

**Datei:** `docker-compose.production.yml` (erweitern)

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    container_name: erechnung_frontend_prod
    restart: unless-stopped
    networks:
      - erechnung-network
    depends_on:
      - web
```

**Datei:** `frontend/nginx.conf`

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # SPA Routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Proxy
    location /api/ {
        proxy_pass http://api-gateway/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 6.2 GitHub Actions CI/CD ✅ IMPLEMENTIERT

**Status:** Implementiert und funktionsfähig. Siehe `.github/workflows/e2e-tests.yml` und `.github/workflows/ci-cd.yml`

**Datei:** `.github/workflows/frontend.yml`

```yaml
name: Frontend CI/CD

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend.yml'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run linter
        working-directory: frontend
        run: npm run lint

      - name: Run unit tests
        working-directory: frontend
        run: npm run test:unit -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          directory: frontend/coverage

      - name: Build production
        working-directory: frontend
        run: npm run build

      - name: Run E2E tests
        working-directory: frontend
        run: |
          docker-compose -f ../docker-compose.yml up -d
          npm run test:e2e
          docker-compose -f ../docker-compose.yml down

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          docker build -f frontend/Dockerfile.prod -t erechnung-frontend:${{ github.sha }} frontend/
          docker tag erechnung-frontend:${{ github.sha }} erechnung-frontend:latest

      - name: Push to registry (optional)
        run: |
          # docker push ...
```

### 6.3 Environment-Management

**Datei:** `frontend/.env.production`

```
VITE_API_BASE_URL=/api
VITE_ENABLE_ANALYTICS=true
VITE_SENTRY_DSN=https://...
```

**Build-Variablen in Vite:**

```javascript
// frontend/src/config.js
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  enableAnalytics: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  sentryDsn: import.meta.env.VITE_SENTRY_DSN
}
```

### 6.4 Monitoring & Error Tracking

**Sentry Integration (optional):**

```bash
docker-compose -f docker-compose.frontend.yml exec frontend npm install @sentry/vue
```

**Datei:** `frontend/src/main.js`

```javascript
import { createApp } from 'vue'
import * as Sentry from '@sentry/vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

if (import.meta.env.PROD) {
  Sentry.init({
    app,
    dsn: import.meta.env.VITE_SENTRY_DSN,
    integrations: [
      Sentry.browserTracingIntegration({ router }),
      Sentry.replayIntegration()
    ],
    tracesSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0
  })
}

app.use(router)
app.mount('#app')
```

### 6.5 Deployment-Checkliste

- [x] Production-Build erstellt ohne Fehler (Dockerfile.prod funktioniert)
- [ ] Bundle-Größe optimiert (< 500KB initial JS)
- [x] Unit-Tests: 253 Tests, 70% Coverage ✅
- [x] E2E-Tests: 27/34 (79%) passing - Login 100%, Pagination 100%
- [ ] Lighthouse-Score > 90
- [x] Security Headers korrekt gesetzt (nginx.conf)
- [x] HTTPS konfiguriert (selbst-signierte Zertifikate für Dev, api-gateway-https.conf)
- [ ] Backup-Strategie definiert
- [ ] Monitoring aktiv (Sentry/Analytics)

**Dauer:** 2-3 Tage
**Ergebnis:** Production-ready Frontend mit automatisiertem Deployment

---

## Zusammenfassung & Zeitplan

| Phase | Beschreibung | Dauer | Abhängigkeiten |
|-------|--------------|-------|----------------|
| 1 | Container-Setup & Projekt-Initialisierung | 1-2 Tage | - |
| 2 | API-Client & Authentifizierung | 2-3 Tage | Phase 1 |
| 3 | Basis-Komponenten & Routing | 3-4 Tage | Phase 2 |
| 4 | Feature-Views (CRUD) | 5-7 Tage | Phase 3 |
| 5 | Styling & UX-Optimierung | 3-4 Tage | Phase 4 |
| 6 | Production-Deployment & CI/CD | 2-3 Tage | Phase 5 |
| **Gesamt** | | **16-23 Tage** | |

### Meilensteine

- **Nach Phase 1:** Funktionierende Entwicklungsumgebung
- **Nach Phase 2:** API-Integration vollständig
- **Nach Phase 3:** Grundlegendes UI-Framework
- **Nach Phase 4:** Alle Features implementiert
- **Nach Phase 5:** Produktionsreifes UI
- **Nach Phase 6:** Live-Deployment möglich

---

## Migration zu React (falls später gewünscht)

Die Architektur ist so aufgebaut, dass ein Wechsel zu React mit minimalem Aufwand möglich ist:

### Was gleich bleibt:

- **API-Client** (`src/api/`) → 100% wiederverwendbar
- **Services** (`src/api/services/`) → 100% wiederverwendbar
- **Docker-Setup** → Nur `package.json` anpassen
- **Routing-Logik** → Konzeptuell identisch (React Router)
- **State Management** → Konzeptuell ähnlich (Hooks vs Composables)

### Was angepasst werden muss:

- **Komponenten** → `.vue` zu `.jsx`/`.tsx`
- **Composables** → Custom Hooks
- **Template-Syntax** → JSX
- **Vue Router** → React Router

**Geschätzter Aufwand für Migration:** 5-7 Tage (ca. 30% der Entwicklungszeit)

---

## Technologie-Entscheidungen

### Getroffene Entscheidungen

1. ✅ **CSS-Framework:** Tailwind CSS
   - Utility-First-Ansatz
   - Minimale Bundle-Größe durch Tree-Shaking
   - Gute Integration mit Vue 3

2. ✅ **State Management:** Pinia
   - Offizieller Vuex-Nachfolger für Vue 3
   - TypeScript-freundlich, minimaler Boilerplate
   - **Grund:** App hat komplexe Geschäftslogik (Rechnungen, Rollen, Filter)
   - **States:** Auth-Token, Benutzer, Rechnungslisten, Filter, UI-Zustand
   - **Migrationsaufwand falls später geändert:** 3-5 Tage (bei Wechsel zu reinen Composables)

3. ✅ **Testing-Framework:** Vitest
   - Native ESM-Unterstützung
   - Schneller als Jest
   - Kompatibel mit Vite

### Offene Entscheidungen (können später getroffen werden)

4. **E2E-Tests:** Playwright (empfohlen) oder Cypress?
   - Beide gut geeignet
   - Entscheidung kann nach ersten Komponenten getroffen werden

5. **Analytics:** Matomo (selbst gehostet) oder Google Analytics?
   - Nicht kritisch für MVP
   - Kann nach Produktiv-Deployment entschieden werden

6. **Error Tracking:** Sentry (kommerziell) oder selbst gehostete Alternative?
   - Nicht kritisch für MVP
   - Kann nach Produktiv-Deployment entschieden werden

---

## Nächste Schritte

1. ✅ **Entscheidungen getroffen:** Tailwind CSS, Pinia, Vitest
2. ✅ **Branch erstellt:** `feature/vue-frontend`
3. ✅ **Phase 1-4 abgeschlossen:** Container-Setup, API-Client, UI-Komponenten, Feature-Views
4. ✅ **Dokumentation:** README im `frontend/` Verzeichnis, PHASE_2/3/4_COMPLETE.md
5. ✅ **Tests:** 253 Unit-Tests (70% Coverage), 27/34 E2E-Tests (79%)
6. ✅ **CI/CD:** GitHub Actions für E2E-Tests konfiguriert

**Status:** Phase 4 abgeschlossen. E2E-Tests laufen. Bereit für Phase 5 (Styling & UX-Optimierung).

### Verbleibende Aufgaben für Produktionsreife

- [ ] Lighthouse-Score Optimierung (>90)
- [ ] Bundle-Größe Analyse und Optimierung
- [ ] Toast-Notification System (useToast composable)
- [ ] Verbleibende E2E-Tests fixen (Token Refresh: 2/6)
- [ ] Sentry/Analytics Integration (optional für MVP)
