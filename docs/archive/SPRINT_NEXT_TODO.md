# Sprint TODO: Frontend Priority Tasks

**Erstellt:** 2025-12-24
**Priorität:** Kritisch / Wichtig
**Status:** In Arbeit
**Branch:** `sprint_next`

---

## Fortschritt

| Task | Status | Branch | PR | Abgeschlossen |
|------|--------|--------|----|--------------|
| **Task 5** | ✅ Erledigt | `fix/frontend-test-fixes` | [#14](https://github.com/RolfMasfelder/eRechnung_Django_App/pull/14) | 2025-12-24 |
| **Task 1** | 🔄 In Arbeit | `sprint_next` | - | - |
| **Task 2** | ⏳ Geplant | `sprint_next` | - | - |

---

## Übersicht

Dieser Plan adressiert drei priorisierte Tasks aus der Analyse vom 24. Dezember 2025:

| # | Task | Priorität | Geschätzte Zeit | Status |
|---|------|-----------|-----------------|--------|
| 1 | User-Daten im Frontend laden | 🔴 Kritisch | 1-2h | 🔄 In Arbeit |
| 2 | Toast Notification System | 🔴 Kritisch | 2-3h | ⏳ Geplant |
| 5 | Frontend Test-Fixes | 🟡 Wichtig | 2-4h | ✅ Erledigt

---

## Task 1: User-Daten im Frontend laden

### Problem
- AppHeader zeigt Fallback-Werte: "Benutzer" / "User"
- JWT-Token enthält nur grundlegende Claims (user_id, username, exp)
- Vollständige User-Daten (first_name, last_name, role, permissions) fehlen

### Ist-Zustand

**authService.js** - JWT-Decoding implementiert:
```javascript
// User-Daten werden aus JWT Token extrahiert (Zeile 48-53)
const userData = decodeJWT(access)
if (userData) {
  localStorage.setItem('current_user', JSON.stringify(userData))
}
```

**useAuth.js** - getCurrentUser() wird aufgerufen:
```javascript
// Nach Login (Zeile 17-18)
currentUser.value = authService.getCurrentUser()
```

**AppHeader.vue** - Computed Properties nutzen currentUser:
```javascript
// displayName prüft first_name, last_name, username
// displayRole prüft role, is_superuser
```

### Ursachenanalyse
Das JWT-Token enthält standardmäßig nur:
- `user_id`
- `username`
- `exp` (Expiration)

Fehlend im Token oder via API:
- `first_name`, `last_name`
- `role` (mit name, role_type, permissions)
- `is_superuser`

### Implementierungsschritte

#### Schritt 1.1: Backend - JWT Claims erweitern (Option A - bevorzugt)
**Datei:** `project_root/invoice_app/api/views.py` oder separate `jwt.py`

```python
# Custom JWT Token Serializer mit erweiterten Claims
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Erweiterte Claims hinzufügen
        token['username'] = user.username
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['email'] = user.email
        token['is_superuser'] = user.is_superuser

        # UserProfile/Role Daten
        try:
            profile = user.profile
            token['role'] = {
                'name': profile.role.name,
                'role_type': profile.role.role_type,
            }
        except:
            token['role'] = None

        return token
```

- [ ] CustomTokenObtainPairSerializer implementieren
- [ ] In `urls.py` konfigurieren für `/auth/token/`
- [ ] Unit-Test für erweiterte Claims schreiben

#### Schritt 1.2: Alternative - User Profile API Endpoint (Option B)
**Falls JWT-Erweiterung nicht gewünscht:**

- [ ] Prüfen ob `/api/auth/user/` Endpoint existiert
- [ ] Falls ja: `fetchUserProfile()` nach Login aufrufen
- [ ] Falls nein: Endpoint implementieren der UserProfile mit Role zurückgibt

```javascript
// In authService.js - fetchUserProfile hinzufügen/aktivieren
async fetchUserProfile() {
  const response = await apiClient.get('/auth/user/')
  localStorage.setItem('current_user', JSON.stringify(response.data))
  return response.data
}
```

#### Schritt 1.3: Frontend - Nach Login User-Daten laden
**Datei:** `frontend/src/composables/useAuth.js`

```javascript
// In login() Funktion nach erfolgreichem Token-Erhalt:
const login = async (username, password) => {
  // ... bestehender Code ...

  await authService.login(username, password)
  isAuthenticated.value = true

  // NEU: Explizit User-Profil laden falls nicht im JWT
  // await authService.fetchUserProfile()

  currentUser.value = authService.getCurrentUser()
  return { success: true }
}
```

- [ ] Login-Flow testen mit vollständigen User-Daten
- [ ] AppHeader zeigt korrekten Namen und Rolle

### Akzeptanzkriterien
- [ ] Nach Login zeigt AppHeader den echten Benutzernamen
- [ ] Nach Login zeigt AppHeader die korrekte Rolle (Admin/Manager/etc.)
- [ ] Nach Page-Refresh bleiben User-Daten erhalten
- [ ] Logout löscht alle User-Daten

---

## Task 2: Toast Notification System

### Problem
- Erfolgs-/Fehlermeldungen nur in Console oder lokaler BaseAlert
- Keine globale Benachrichtigung für CRUD-Operationen
- Inkonsistente UX über verschiedene Views

### Implementierungsschritte

#### Schritt 2.1: Toast Composable erstellen
**Neue Datei:** `frontend/src/composables/useToast.js`

```javascript
import { ref } from 'vue'

const toasts = ref([])
let toastId = 0

export function useToast() {
  const add = (message, type = 'info', duration = 5000) => {
    const id = ++toastId
    toasts.value.push({ id, message, type, duration })

    if (duration > 0) {
      setTimeout(() => remove(id), duration)
    }

    return id
  }

  const remove = (id) => {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  const success = (message, duration) => add(message, 'success', duration)
  const error = (message, duration) => add(message, 'error', duration)
  const warning = (message, duration) => add(message, 'warning', duration)
  const info = (message, duration) => add(message, 'info', duration)

  return {
    toasts,
    add,
    remove,
    success,
    error,
    warning,
    info
  }
}
```

- [ ] `useToast.js` Composable erstellen
- [ ] Export in `composables/index.js` hinzufügen

#### Schritt 2.2: Toast Container Komponente
**Neue Datei:** `frontend/src/components/ToastContainer.vue`

```vue
<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', `toast-${toast.type}`]"
        >
          <span class="toast-icon">{{ icons[toast.type] }}</span>
          <span class="toast-message">{{ toast.message }}</span>
          <button @click="remove(toast.id)" class="toast-close">×</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '@/composables/useToast'

const { toasts, remove } = useToast()

const icons = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ'
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 400px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background: white;
}

.toast-success { border-left: 4px solid #10b981; }
.toast-error { border-left: 4px solid #ef4444; }
.toast-warning { border-left: 4px solid #f59e0b; }
.toast-info { border-left: 4px solid #3b82f6; }

.toast-close {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  opacity: 0.5;
}

/* Transition Animations */
.toast-enter-active { animation: slideIn 0.3s ease-out; }
.toast-leave-active { animation: slideOut 0.3s ease-in; }

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes slideOut {
  from { transform: translateX(0); opacity: 1; }
  to { transform: translateX(100%); opacity: 0; }
}
</style>
```

- [ ] `ToastContainer.vue` Komponente erstellen
- [ ] Tailwind-kompatible Styles oder eigene CSS

#### Schritt 2.3: ToastContainer in App einbinden
**Datei:** `frontend/src/App.vue`

```vue
<template>
  <RouterView />
  <ToastContainer />
</template>

<script setup>
import ToastContainer from '@/components/ToastContainer.vue'
</script>
```

- [ ] ToastContainer in App.vue importieren
- [ ] Prüfen dass Teleport korrekt funktioniert

#### Schritt 2.4: Toast in CRUD-Operationen integrieren
**Beispiel:** `frontend/src/views/InvoiceListView.vue`

```javascript
import { useToast } from '@/composables/useToast'

const toast = useToast()

const deleteInvoice = async (id) => {
  try {
    await invoiceService.delete(id)
    toast.success('Rechnung erfolgreich gelöscht')
    await loadInvoices()
  } catch (err) {
    toast.error('Fehler beim Löschen: ' + err.message)
  }
}
```

- [ ] Toast in InvoiceListView integrieren
- [ ] Toast in CompanyListView integrieren
- [ ] Toast in CustomerListView integrieren
- [ ] Toast in ProductListView integrieren
- [ ] Toast bei Create/Edit Modals integrieren

#### Schritt 2.5: Tests für Toast System
**Neue Datei:** `frontend/src/components/__tests__/ToastContainer.spec.js`

- [ ] Unit-Test für useToast Composable
- [ ] Unit-Test für ToastContainer Komponente
- [ ] Integration-Test für Toast bei CRUD-Operation

### Akzeptanzkriterien
- [ ] Nach erfolgreicher CRUD-Operation erscheint grüner Toast
- [ ] Bei Fehlern erscheint roter Toast mit Fehlermeldung
- [ ] Toasts verschwinden automatisch nach 5 Sekunden
- [ ] Toasts können manuell geschlossen werden
- [ ] Mehrere Toasts können gleichzeitig angezeigt werden

---

## Task 5: Frontend Test-Fixes ✅ ANALYSIERT (2025-12-24)

### Test-Ergebnis (aktuell)

| Status | Anzahl |
|--------|--------|
| **Bestanden** | 248 |
| **Fehlgeschlagen** | 5 Unit-Tests + 4 E2E-Suiten |
| **Gesamt** | 253 Tests |

**Hinweis:** Es sind 253 Tests statt der erwarteten 144 - die Zahl hat sich erhöht!

---

### Identifizierte Failures

#### Problem A: E2E Tests werden von Vitest ausgeführt (4 Suiten)

**Betroffene Dateien:**
- `tests/e2e/auth/login.spec.js`
- `tests/e2e/auth/token-refresh.spec.js`
- `tests/e2e/components/modals.spec.js`
- `tests/e2e/components/pagination.spec.js`

**Fehler:**
```
Error: Playwright Test did not expect test.describe() to be called here.
```

**Ursache:** Playwright E2E-Tests im `tests/e2e/` Verzeichnis werden fälschlicherweise von Vitest mitgeladen.

**Lösung:**
- [ ] `vitest.config.js` anpassen: E2E-Tests ausschließen
```javascript
// In vitest.config.js
export default defineConfig({
  test: {
    exclude: [
      '**/node_modules/**',
      '**/tests/e2e/**'  // E2E-Tests von Vitest ausschließen
    ]
  }
})
```
- [ ] Alternativ: E2E-Tests in separaten Ordner `e2e/` (außerhalb von `tests/`) verschieben

---

#### Problem B: client.test.js - Response Mock unvollständig (3 Tests)

**Betroffene Tests:**
- `returns response unchanged on success`
- `passes through successful responses with data`
- `passes through 204 No Content responses`

**Fehler:**
```javascript
// client.js:45
console.log('✅ API Response:', response.status, response.config.url)
// TypeError: Cannot read properties of undefined (reading 'url')
```

**Ursache:** Test-Mocks übergeben `response.config` nicht korrekt.

**Lösung:**
- [ ] `src/api/__tests__/client.test.js` - Mock-Responses mit `config` Objekt erweitern:
```javascript
// Vorher (unvollständig):
const mockResponse = { status: 200, data: {} }

// Nachher (vollständig):
const mockResponse = {
  status: 200,
  data: {},
  config: { url: '/api/test/' }  // <-- Hinzufügen!
}
```

---

#### Problem C: CustomerCreateModal.test.js - Selector nicht gefunden (1 Test)

**Betroffener Test:** `rendert korrekt`

**Fehler:**
```
Error: Cannot call text on an empty DOMWrapper.
wrapper.find('.modal-title').text()
```

**Ursache:** Modal ist initial nicht geöffnet, daher existiert `.modal-title` nicht im DOM.

**Lösung:**
- [ ] `src/components/__tests__/CustomerCreateModal.test.js` - Modal mit `isOpen=true` mounten:
```javascript
// Vorher:
wrapper = mount(CustomerCreateModal)

// Nachher:
wrapper = mount(CustomerCreateModal, {
  props: { isOpen: true }
})
```

---

#### Problem D: ProductCreateModal.test.js - Selector nicht gefunden (1 Test)

**Betroffener Test:** `rendert korrekt`

**Fehler:** Identisch mit Problem C

**Lösung:**
- [ ] `src/components/__tests__/ProductCreateModal.test.js` - Modal mit `isOpen=true` mounten

---

### Zusätzliche Warnings (nicht blockierend)

| Warning | Betroffene Tests | Lösung |
|---------|------------------|--------|
| `Invalid prop: size` | InvoiceCreateModal, InvoiceEditModal | `size="small"` → `size="sm"` |
| `Invalid prop: type` | BaseInput in Modals | `type` Prop-Validator erweitern oder Props anpassen |
| `No match found for location with path ""` | ListView Tests | Router-Mock mit Default-Route |

---

### Implementierungsschritte

#### Schritt 5.1: Vitest Config - E2E ausschließen
**Datei:** `frontend/vitest.config.js`

```javascript
export default defineConfig({
  test: {
    environment: 'jsdom',
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/tests/e2e/**'  // Playwright E2E Tests ausschließen
    ],
    include: ['src/**/*.{test,spec}.{js,ts}']
  }
})
```

- [ ] Config anpassen
- [ ] Verifizieren: `npm test` zeigt keine E2E-Tests mehr

#### Schritt 5.2: client.test.js - Response Mocks fixen
**Datei:** `frontend/src/api/__tests__/client.test.js`

- [ ] Zeile ~228: `config: { url: '/test' }` zu Mock hinzufügen
- [ ] Zeile ~239: dto.
- [ ] Zeile ~250: dto.

#### Schritt 5.3: CustomerCreateModal.test.js - Props fixen
**Datei:** `frontend/src/components/__tests__/CustomerCreateModal.test.js`

- [ ] Zeile ~65-66: `mount(CustomerCreateModal, { props: { isOpen: true } })`

#### Schritt 5.4: ProductCreateModal.test.js - Props fixen
**Datei:** `frontend/src/components/__tests__/ProductCreateModal.test.js`

- [ ] Zeile ~65-67: `mount(ProductCreateModal, { props: { isOpen: true } })`

#### Schritt 5.5: Tests erneut ausführen

```bash
docker-compose -f docker-compose.frontend.yml exec frontend npm test -- --run
```

- [x] Alle 253 Tests grün
- [x] 100% Pass-Rate erreicht

---

### Akzeptanzkriterien
- [x] `npm test` zeigt 0 Failures
- [x] E2E-Tests laufen separat via `npx playwright test`
- [x] Keine Test-Warnings für Props
- [x] CI/CD Pipeline läuft ohne Test-Failures

### ✅ Task 5 Abgeschlossen (2025-12-24)
- Alle 5 Test-Failures behoben
- 253/253 Tests bestanden
- PR #14 erstellt: https://github.com/RolfMasfelder/eRechnung_Django_App/pull/14

---

## 🔄 Nächste Schritte (Branch: sprint_next)

### Priorität 1: Task 1 - User-Daten im Frontend laden
**Geschätzte Zeit:** 1-2h
**Schritte:**
1. Backend: JWT Claims erweitern ODER User-API Endpoint bereitstellen
2. Frontend: User-Daten nach Login laden
3. Tests schreiben
4. AppHeader Validierung

### Priorität 2: Task 2 - Toast Notification System
**Geschätzte Zeit:** 2-3h
**Schritte:**
1. useToast Composable erstellen
2. ToastContainer Komponente
3. In CRUD-Views integrieren
4. Tests schreiben

---

## Checkliste für Abschluss

### Vor Merge
- [x] Alle Unit-Tests grün (Task 5)
- [ ] E2E Tests (falls relevant) grün
- [ ] Code-Review durchgeführt
- [ ] Keine neuen Linter-Warnings

### Dokumentation
- [x] SPRINT_NEXT_TODO.md aktualisiert
- [ ] FRONTEND_BACKLOG.md aktualisieren (Tasks als erledigt markieren)
- [ ] TODO.md aktualisieren (Phase 5 Progress)
- [ ] PROGRESS_PROTOCOL.md mit Milestone-Eintrag

### Git Workflow
```bash
# Feature-Branch erstellen (ERLEDIGT für Task 5)
git checkout -b fix/frontend-test-fixes  ✅

# Nächster Branch für Tasks 1+2
git checkout main
git pull origin main
git checkout -b sprint_next

# Nach Implementierung
git add .
git commit -m "feat(frontend): user data loading and toast system"

# Push zu beiden Remotes
git push origin sprint_next
git push github feat/frontend-priority-tasks
```

---

## Referenzen

- [FRONTEND_BACKLOG.md](./FRONTEND_BACKLOG.md) - Vollständige Backlog-Liste
- [TODO.md](../TODO.md) - Projekt-weite Aufgaben
- [frontend/README.md](../frontend/README.md) - Frontend-Dokumentation
