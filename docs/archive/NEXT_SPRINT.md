# Nächster Sprint - Priorisierte Tasks

**Erstellt:** 2025-12-31
**Status:** � IN ARBEIT
**Branch:** feature/confirmation-dialogs

---

## Übersicht

Basierend auf FRONTEND_BACKLOG.md und TODO.md - priorisiert nach Impact und Aufwand.

| # | Task | Priorität | Aufwand | Impact | Status |
|---|------|-----------|---------|--------|--------|
| 1 | Confirmation Dialogs | 🔴 Hoch | 2-3h | Hoch | ✅ **FERTIG** |
| 2 | Loading States verbessern | 🟡 Mittel | 2-3h | Mittel | ✅ **FERTIG** |
| 3 | Formular-Validierung (Client-Side) | 🟡 Mittel | 3-4h | Hoch | ⚪ **ÜBERSPRUNGEN** |
| 4 | Table Sortierung implementieren | 🟡 Mittel | 1-2h | Mittel | ✅ **FERTIG** |
| 5 | Dashboard Statistiken (Backend + Frontend) | 🟡 Mittel | 3-4h | Hoch | ✅ **FERTIG** |
| 6 | Error Handler für Netzwerk-Probleme | 🟢 Niedrig | 2h | Mittel | ✅ **FERTIG** |
| 7 | Fehlende Form-Komponenten | 🟢 Niedrig | 2-3h | Niedrig | 🔴 Offen |

---

## Task 1: Confirmation Dialogs ✅ FERTIG

**Abgeschlossen:** 2025-12-31

### Implementierung
✅ BaseConfirmDialog.vue erstellt (147 Zeilen)
- 3 Varianten: danger, warning, info
- Icon-Anzeige je nach Variante
- Customizable title, message, button texts
- Event-basiert: @confirm, @cancel

✅ useConfirm Composable erstellt (66 Zeilen)
- Promise-basierte API
- Global singleton pattern
- Auto-reset nach Dialog-Schließung

✅ Integration in Views:
- InvoiceListView.vue - deleteInvoice()
- CustomerListView.vue - deleteCustomer()
- ProductListView.vue - deleteProduct()
- CompanyListView.vue - keine Delete-Funktion vorhanden

✅ Tests:
- BaseConfirmDialog.test.js - 12 Tests ✅
- useConfirm.test.js - 10 Tests ✅
- InvoiceListView.test.js - Delete-Tests angepasst ✅
- CustomerListView.test.js - Delete-Tests angepasst ✅
- **300/300 Unit-Tests bestehen**

✅ Bug-Fixes während Implementation:
- client.test.js: Mock-Responses um config-Property erweitert
- ProductCreateModal.test.js: BaseModal Mock korrigiert
- CustomerCreateModal.test.js: BaseModal Mock korrigiert
- InvoiceListView.test.js: Doppelte useToast Mock entfernt

### Commits
1. `feat: implement confirmation dialogs for delete operations` (9e83d0f)
2. `fix: resolve all unit test issues in confirmation dialogs` (668754d)

### Problem
- Delete-Actions verwenden `confirm()` (Browser-Standard-Dialog)
- Nicht konsistent mit UI-Design
- Keine Customization möglich

### Lösung
**BaseConfirmDialog.vue** erstellen:
```vue
<template>
  <BaseModal :isOpen="isOpen" @close="handleCancel">
    <template #title>{{ title }}</template>
    <p>{{ message }}</p>
    <template #footer>
      <BaseButton variant="secondary" @click="handleCancel">
        Abbrechen
      </BaseButton>
      <BaseButton :variant="variant" @click="handleConfirm">
        {{ confirmText }}
      </BaseButton>
    </template>
  </BaseModal>
</template>
```

**useConfirm Composable:**
```javascript
export function useConfirm() {
  const confirm = (message, options = {}) => {
    return new Promise((resolve) => {
      // Show dialog, resolve with true/false
    })
  }

  return { confirm }
}
```

### Verwendung in Views:
```javascript
const { confirm } = useConfirm()

const deleteInvoice = async (id) => {
  const confirmed = await confirm(
    'Möchten Sie diese Rechnung wirklich löschen?',
    { variant: 'danger', confirmText: 'Löschen' }
  )
  if (!confirmed) return
  // Delete logic...
}
```

### Dateien (Implementiert)
✅ `frontend/src/components/BaseConfirmDialog.vue` (NEU - 147 Zeilen)
✅ `frontend/src/composables/useConfirm.js` (NEU - 66 Zeilen)
✅ `frontend/src/App.vue` (ANGEPASST - Dialog integriert)
✅ `frontend/src/views/InvoiceListView.vue` (ANGEPASST)
✅ `frontend/src/views/CustomerListView.vue` (ANGEPASST)
✅ `frontend/src/views/ProductListView.vue` (ANGEPASST)
✅ `frontend/src/components/__tests__/BaseConfirmDialog.test.js` (NEU - 12 Tests)
✅ `frontend/src/composables/__tests__/useConfirm.test.js` (NEU - 10 Tests)
✅ `frontend/src/views/__tests__/InvoiceListView.test.js` (ANGEPASST)
✅ `frontend/src/views/__tests__/CustomerListView.test.js` (ANGEPASST)

### Akzeptanzkriterien
✅ BaseConfirmDialog Komponente mit verschiedenen Varianten (danger, warning, info)
✅ useConfirm Composable für einfache Verwendung
✅ Alle `confirm()` Calls in Views ersetzt (3 Views)
✅ Unit Tests für Dialog und Composable (22 neue Tests)
✅ Keyboard Support implementiert (Enter = confirm, Escape = cancel via BaseModal)
✅ Alle 300 Unit-Tests bestehen

**Tatsächlicher Aufwand:** ~3 Stunden

---

## Task 2: Loading States verbessern ✅ FERTIG

**Abgeschlossen:** 2025-12-31

### Implementierung
✅ BaseLoader.vue erstellt (150 Zeilen)
- 3 Modi: spinner, skeleton, overlay
- Spinner für Buttons/inline (sm, md, lg)
- Skeleton-Loader für Tabellen (animiert)
- Overlay für Full-Page Loading
- Props: type, size, rows, rowHeight, overlay, message, inline, loading

✅ Integration in Views:
- InvoiceListView.vue - Skeleton während initialer Load
- CustomerListView.vue - Skeleton während initialer Load
- ProductListView.vue - Skeleton während initialer Load
- CompanyListView.vue - Skeleton während initialer Load

✅ Tests:
- BaseLoader.test.js - 21 Tests ✅
- Spinner Mode (4 Tests)
- Skeleton Mode (5 Tests)
- Overlay Mode (5 Tests)
- Props Validation (3 Tests)
- Accessibility (2 Tests)
- Conditional Rendering (2 Tests)
- **Alle 321 Unit-Tests bestehen**

✅ CSS:
- Skeleton-Box Animation mit gradient
- Dark mode support
- Smooth transitions

### Commits
1. `feat: implement loading states with BaseLoader component` (c06e61f)

### Problem
- Loading-States nur teilweise implementiert
- Keine einheitliche Loading-Komponente
- Skeleton-Loader fehlen

### Lösung
**BaseLoader.vue** erstellen:
```vue
<!-- Spinner für Buttons/kleine Bereiche -->
<BaseLoader size="sm" />

<!-- Skeleton für Tabellen -->
<BaseLoader type="skeleton" rows="5" />

<!-- Full-Page Overlay -->
<BaseLoader overlay />
```

**Skeleton-Loader für Tabellen:**
```vue
<template v-if="loading">
  <tr v-for="i in 5" :key="i">
    <td><div class="skeleton-box"></div></td>
    <td><div class="skeleton-box"></div></td>
  </tr>
</template>
```

### Dateien
- `frontend/src/components/BaseLoader.vue` (NEU)
- `frontend/src/views/*ListView.vue` (ANPASSEN)
- `frontend/src/components/__tests__/BaseLoader.test.js` (NEU)

### Akzeptanzkriterien
- ✅ BaseLoader Komponente mit 3 Modi (spinner, skeleton, overlay)
- ✅ Loading-States in allen ListView konsistent
- ✅ Skeleton-Loader während initialer Datenabruf
- ✅ Spinner bei Button-Actions (z.B. Delete)
- ✅ Unit Tests

**Geschätzter Aufwand:** 2-3 Stunden

---

## Task 3: Formular-Validierung (Client-Side) 🟡 MITTEL

### Problem
- Keine einheitliche Client-Side-Validierung
- Validierung muss in jeder View manuell implementiert werden
- Fehler werden nur von Backend zurückgegeben

### Lösung
**VeeValidate Integration:**
```bash
npm install vee-validate yup
```

**useFormValidation Composable:**
```javascript
import { useForm } from 'vee-validate'
import * as yup from 'yup'

export function useInvoiceForm() {
  const schema = yup.object({
    invoice_number: yup.string().required('Pflichtfeld'),
    invoice_date: yup.date().required('Pflichtfeld'),
    total_gross: yup.number().positive().required()
  })

  const { errors, validate, values } = useForm({ validationSchema: schema })

  return { errors, validate, values }
}
```

**BaseInput mit Validierung:**
```vue
<BaseInput
  v-model="values.invoice_number"
  :error="errors.invoice_number"
  label="Rechnungsnummer"
  required
/>
```

### Dateien
- `package.json` (Dependencies hinzufügen)
- `frontend/src/composables/useFormValidation.js` (NEU)
- `frontend/src/components/BaseInput.vue` (ANPASSEN - error prop)
- `frontend/src/components/BaseSelect.vue` (ANPASSEN - error prop)
- `frontend/src/components/*CreateModal.vue` (ANPASSEN)
- `frontend/src/components/__tests__/useFormValidation.test.js` (NEU)

### Akzeptanzkriterien
- ✅ VeeValidate + Yup integriert
- ✅ useFormValidation Composable für alle Entities
- ✅ BaseInput/BaseSelect zeigen Fehler an
- ✅ Validierung vor Submit
- ✅ Deutsche Fehlermeldungen
- ✅ Unit Tests

**Geschätzter Aufwand:** 3-4 Stunden

---

## Task 3: Formular-Validierung (Client-Side) ⚪ ÜBERSPRUNGEN

**Status:** Manuell ausreichend für aktuelle Use Cases

### Begründung
- Aktuelle manuelle Validierung (required fields, regex) ist funktional
- VeeValidate wäre "overkill" für simple Forms
- Kann später hinzugefügt werden, wenn komplexere Validierung benötigt wird
- Kein kritischer Blocker für MVP

**Geschätzter Aufwand:** 3-4 Stunden (nicht umgesetzt)

---

## Task 4: Table Sortierung implementieren ✅ FERTIG

**Abgeschlossen:** 2025-12-31

### Implementierung
✅ Pagination State erweitert:
- sortKey und sortOrder zu pagination reactive state hinzugefügt
- In allen 4 ListView: InvoiceListView, CustomerListView, ProductListView, CompanyListView

✅ handleSort implementiert:
- Setzt sortKey und sortOrder
- Reset currentPage auf 1 bei neuem Sort
- Ruft loadData() Funktion auf

✅ API ordering Parameter:
- Django REST framework format: `ordering=-field` (desc) oder `ordering=field` (asc)
- Wird nur gesetzt wenn sortKey vorhanden ist

✅ BaseTable UI:
- Hatte bereits visuelle Sort-Icons (▲▼⇅)
- Keine Änderungen nötig - funktionierte out of the box

✅ Tests:
- 2 neue Unit-Tests für Sortierung (InvoiceListView, CustomerListView)
- **Alle 323 Unit-Tests bestehen**

### Commits
1. `feat: implement table sorting with ordering parameter` (5456b67)

### Problem
- BaseTable emittet `sort` Event, aber Views reagieren nicht
- Keine visuelle Anzeige der Sortierrichtung

### Lösung
**BaseTable erweitern:**
```vue
<th @click="handleSort(column.key)">
  {{ column.label }}
  <span v-if="sortKey === column.key">
    {{ sortOrder === 'asc' ? '↑' : '↓' }}
  </span>
</th>
```

**Views: handleSort implementieren:**
```javascript
const sortKey = ref('')
const sortOrder = ref('asc')

const handleSort = ({ key, order }) => {
  sortKey.value = key
  sortOrder.value = order
  loadInvoices() // Mit ordering=-field Parameter
}
```

### Dateien
- `frontend/src/components/BaseTable.vue` (ANPASSEN)
- `frontend/src/views/InvoiceListView.vue` (ANPASSEN)
- `frontend/src/views/CustomerListView.vue` (ANPASSEN)
- `frontend/src/views/ProductListView.vue` (ANPASSEN)
- `frontend/src/views/CompanyListView.vue` (ANPASSEN)

### Akzeptanzkriterien
- ✅ Sort-Icons (↑↓) in Table-Header
- ✅ Klick auf Column sortiert Liste
- ✅ API-Call mit `ordering` Parameter
- ✅ Toggle zwischen asc/desc
- ✅ Alle ListView unterstützen Sortierung

**Geschätzter Aufwand:** 1-2 Stunden

---

## Task 5: Dashboard Statistiken (Backend + Frontend) ✅ FERTIG

**Abgeschlossen:** 2025-12-31

### Implementierung
✅ Backend - DashboardStatsView API Endpoint:
- RESTful API mit GET method
- Authentication erforderlich (IsAuthenticated)
- Aggregiert Statistiken mit Django ORM (Count, Sum, Q filters)
- Rückgabe: invoices (by_status, total_amount, paid_amount, outstanding_amount), customers (total, active), products (total, active), companies (total, active)

✅ Frontend - statsService:
- Einfacher Service mit getStats() Method
- Verwendet client.get('/api/stats/')
- Gibt Promise mit Stats-Daten zurück

✅ Frontend - DashboardView Integration:
- loadDashboardData() ruft statsService.getStats() auf
- Populates 4 stat cards dynamisch (Gesamt Rechnungen, Offene Rechnungen, Bezahlte Rechnungen, Kunden)
- Loading state während API-Call

✅ Tests:
- Backend: test_stats.py - 5 Tests ✅
  - test_requires_authentication
  - test_returns_empty_stats
  - test_invoice_statistics
  - test_invoice_amounts
  - test_customer_and_product_count
- Frontend: statsService.test.js - 2 Tests ✅
  - getStats success
  - error handling
- Frontend: DashboardView.test.js angepasst - 7 Tests ✅
- **Alle 328 Unit-Tests bestehen (323 frontend + 5 backend stats)**

✅ Bug-Fixes während Implementation:
- Fixed aggregate field name conflict (total_amount → sum_total_amount)
- Fixed Customer model - verwendet company_name statt name property
- Fixed Product model - verwendet base_price und product_code
- Fixed Invoice model - total_amount wird berechnet aus subtotal + tax_amount

### Commits
1. `feat: implement dashboard statistics endpoint and frontend integration` (f5b4dbd)

### Problem
- Dashboard zeigt Dummy-Daten (0 Werte)
- Backend hat keinen `/api/stats/` Endpoint

### Lösung
**Backend: Stats Endpoint erstellen**
```python
# invoice_app/api/views.py
class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = {
            'total_invoices': Invoice.objects.count(),
            'pending_invoices': Invoice.objects.filter(status='pending').count(),
            'total_revenue': Invoice.objects.aggregate(Sum('total_gross'))['total_gross__sum'] or 0,
            'customer_count': Customer.objects.count(),
        }
        return Response(stats)
```

**Frontend: Stats laden**
```javascript
// frontend/src/api/services/statsService.js
export const statsService = {
  async getDashboardStats() {
    const response = await client.get('stats/')
    return response.data
  }
}

// frontend/src/views/DashboardView.vue
const loadStats = async () => {
  stats.value = await statsService.getDashboardStats()
}
```

### Dateien
- `project_root/invoice_app/api/views.py` (ERWEITERN)
- `project_root/invoice_app/api/urls.py` (Route hinzufügen)
- `frontend/src/api/services/statsService.js` (NEU)
- `frontend/src/views/DashboardView.vue` (ANPASSEN)

### Akzeptanzkriterien
- ✅ Backend Stats-Endpoint mit echten Daten
- ✅ Frontend lädt und zeigt Stats an
- ✅ Loading-State während Datenabruf
- ✅ Error-Handling wenn Stats nicht laden
- ✅ Unit Tests (Backend + Frontend)

**Geschätzter Aufwand:** 3-4 Stunden

---

## Task 6: Error Handler für Netzwerk-Probleme ✅ FERTIG

**Abgeschlossen:** 2025-12-31

### Implementierung
✅ Response Interceptor in client.js:
- Erkennt Netzwerkfehler (!error.response)
- Erkennt Timeouts (ECONNABORTED code)
- Erkennt Server-Fehler (status >= 500)
- Zeigt benutzerfreundliche Toast-Nachrichten an
- Unterscheidet zwischen Client-Fehlern (4xx - kein Toast) und Server-Fehlern

✅ useNetworkStatus Composable erstellt:
- Überwacht navigator.onLine Status
- Hört auf 'online' und 'offline' Events
- Zeigt automatisch Toast bei Verbindungsänderungen
- Cleanup in onUnmounted für Event Listeners

✅ Integration in App.vue:
- useNetworkStatus wird global initialisiert
- Überwacht Verbindungsstatus während gesamter App-Laufzeit

✅ Tests:
- useNetworkStatus.test.js - 7 Tests ✅
  - Initial online/offline status
  - Status updates on events
  - Toast notifications
  - Event listener cleanup
- client.test.js - 5 neue Tests ✅
  - Network failure toast
  - Timeout error toast
  - 500 server error toast
  - 503 service unavailable toast
  - No toast for 404 errors
- **Alle 338 Unit-Tests bestehen**

✅ Mock-Fixes:
- Stabile Toast-Mock-Instanz für konsistentes Verhalten
- Export mockToast für Test-Nutzung
- Vermeidung von Factory-Function-Problemen

### Commits
1. `feat: implement error handler for network problems with offline detection` (a12d9eb)

### Problem
- Bei Offline/Timeout keine User-freundliche Fehlermeldung
- Nur Console-Errors

### Lösung
**Global Error Interceptor:**
```javascript
// frontend/src/api/client.js
client.interceptors.response.use(
  response => response,
  error => {
    if (!error.response) {
      // Network error (offline, timeout, etc.)
      toast.error('Netzwerkfehler. Bitte prüfen Sie Ihre Internetverbindung.')
    } else if (error.code === 'ECONNABORTED') {
      toast.error('Zeitüberschreitung. Der Server antwortet nicht.')
    } else if (error.response.status >= 500) {
      toast.error('Serverfehler. Bitte versuchen Sie es später erneut.')
    }
    return Promise.reject(error)
  }
)
```

**Offline Detection:**
```javascript
// frontend/src/composables/useNetworkStatus.js
export function useNetworkStatus() {
  const isOnline = ref(navigator.onLine)

  window.addEventListener('online', () => {
    isOnline.value = true
    toast.success('Verbindung wiederhergestellt')
  })

  window.addEventListener('offline', () => {
    isOnline.value = false
    toast.warning('Keine Internetverbindung')
  })

  return { isOnline }
}
```

### Dateien
- `frontend/src/api/client.js` (ANGEPASST - Response Interceptor erweitert)
- `frontend/src/composables/useNetworkStatus.js` (NEU - 37 Zeilen)
- `frontend/src/App.vue` (ANGEPASST - useNetworkStatus eingebunden)
- `frontend/src/composables/__tests__/useNetworkStatus.test.js` (NEU - 7 Tests)
- `frontend/src/api/__tests__/client.test.js` (ANGEPASST - 5 neue Tests)

### Akzeptanzkriterien
- ✅ Toast bei Netzwerkfehlern
- ✅ Toast bei Timeouts
- ✅ Toast bei Server-Fehlern (5xx)
- ✅ Offline-Detection mit Browser-Events
- ✅ Reconnect-Notification
- ✅ Unit Tests (12 neue Tests insgesamt)

**Geschätzter Aufwand:** 2 Stunden (tatsächlich ~2h)

---

## ✅ Task 7: Fehlende Form-Komponenten 🟢 NIEDRIG

### Status: ABGESCHLOSSEN ✅

### Implementierung
✅ BaseTextarea Komponente erstellt:
- Props: modelValue, label, placeholder, rows (default 4), disabled, required, error, hint, id
- Auto-generierte eindeutige ID via Math.random() wenn nicht angegeben
- Error/Hint Priorisierung (Error überlagert Hint)
- Label mit required Indikator (*)
- Disabled State Styling
- Focus shadow effect

✅ BaseCheckbox Komponente erstellt:
- Props: modelValue (Boolean), label, disabled, required, error, hint
- Custom Checkmark-Styling mit CSS ::after Pseudo-Element
- Label-Slot für flexiblen Content
- Checked State mit blauem Hintergrund (#3b82f6)
- Checkmark-Animation bei checked
- Error/Hint Display unterhalb Checkbox

✅ BaseRadio Komponente erstellt:
- Props: modelValue (String/Number/Boolean), value (required), name (required), label, disabled, required, error
- Computed isChecked für visuelle Checked-State-Anzeige
- Radio-Mark mit ::after Pseudo-Element (Dot)
- Hover State (#f9fafb), Checked State (#eff6ff)
- Unterstützt String, Number und Boolean Values

✅ Modal-Integrationen (6 Dateien angepasst):
- CustomerEditModal.vue: BaseTextarea für Notizen-Feld
- CustomerCreateModal.vue: BaseTextarea für Notizen-Feld
- InvoiceCreateModal.vue: BaseTextarea für Notizen-Feld
- InvoiceEditModal.vue: BaseTextarea für Notizen-Feld
- ProductEditModal.vue: BaseCheckbox für is_active Toggle
- ProductCreateModal.vue: BaseCheckbox für is_active Toggle

✅ Tests:
- BaseTextarea.test.js - 15 Tests ✅
  - Default props, label, required indicator
  - modelValue emission and display
  - Custom rows prop, placeholder
  - Error/hint display and prioritization
  - Disabled state
  - Blur/Focus events
  - Unique ID generation
- BaseCheckbox.test.js - 13 Tests ✅
  - Rendering, label, slot content
  - update:modelValue and change events
  - Checked state reflection
  - Disabled state
  - Error/hint display
  - Toggle behavior
- BaseRadio.test.js - 15 Tests ✅
  - Radio input/mark rendering
  - Label and slot content
  - update:modelValue with value
  - Checked state when modelValue matches value
  - Disabled state prevents events
  - Numeric and boolean value support
  - Name and value attributes
- **Alle 381 Unit-Tests bestehen (338 bestehende + 43 neue)**

### Commits
1. `feat: implement missing form components (BaseTextarea, BaseCheckbox, BaseRadio)` (d656bf3)

### Problem
- Keine BaseTextarea (BaseInput unterstützt kein type="textarea")
- Keine BaseCheckbox / BaseRadio
- Native HTML-Elemente inkonsistent gestyled
- Keine DatePicker-Integration (für späteren Sprint)

### Lösung
**BaseTextarea.vue (150 Zeilen):**
```vue
<template>
  <div class="base-textarea">
    <label v-if="label" :for="textareaId" class="base-textarea__label">
      {{ label }}
      <span v-if="required" class="base-textarea__required">*</span>
    </label>
    <textarea
      :id="textareaId"
      :value="modelValue"
      @input="handleInput"
      @blur="$emit('blur', $event)"
      @focus="$emit('focus', $event)"
      :placeholder="placeholder"
      :rows="rows"
      :disabled="disabled"
      :required="required"
      :class="{
        'base-textarea--error': error,
        'base-textarea--disabled': disabled
      }"
    />
    <p v-if="error" class="base-textarea__error">{{ error }}</p>
    <p v-else-if="hint" class="base-textarea__hint">{{ hint }}</p>
  </div>
</template>
```

**BaseCheckbox.vue (140 Zeilen):**
```vue
<template>
  <div class="base-checkbox">
    <label class="base-checkbox__wrapper">
      <input
        type="checkbox"
        :checked="modelValue"
        @change="handleChange"
        :disabled="disabled"
        :required="required"
        class="base-checkbox__input"
      />
      <span class="base-checkbox__mark"></span>
      <span v-if="label || $slots.default" class="base-checkbox__label">
        <slot>{{ label }}</slot>
      </span>
    </label>
    <p v-if="error" class="base-checkbox__error">{{ error }}</p>
    <p v-else-if="hint" class="base-checkbox__hint">{{ hint }}</p>
  </div>
</template>
```

**BaseRadio.vue (130 Zeilen):**
```vue
<template>
  <div class="base-radio">
    <label class="base-radio__wrapper">
      <input
        type="radio"
        :checked="isChecked"
        :value="value"
        :name="name"
        @change="handleChange"
        :disabled="disabled"
        :required="required"
        class="base-radio__input"
      />
      <span class="base-radio__mark"></span>
      <span v-if="label || $slots.default" class="base-radio__label">
        <slot>{{ label }}</slot>
      </span>
    </label>
    <p v-if="error" class="base-radio__error">{{ error }}</p>
  </div>
</template>
```

### Dateien
- `frontend/src/components/BaseTextarea.vue` (NEU - 150 Zeilen)
- `frontend/src/components/BaseCheckbox.vue` (NEU - 140 Zeilen)
- `frontend/src/components/BaseRadio.vue` (NEU - 130 Zeilen)
- `frontend/src/components/__tests__/BaseTextarea.test.js` (NEU - 15 Tests)
- `frontend/src/components/__tests__/BaseCheckbox.test.js` (NEU - 13 Tests)
- `frontend/src/components/__tests__/BaseRadio.test.js` (NEU - 15 Tests)
- `frontend/src/components/CustomerEditModal.vue` (ANGEPASST)
- `frontend/src/components/CustomerCreateModal.vue` (ANGEPASST)
- `frontend/src/components/InvoiceCreateModal.vue` (ANGEPASST)
- `frontend/src/components/InvoiceEditModal.vue` (ANGEPASST)
- `frontend/src/components/ProductEditModal.vue` (ANGEPASST)
- `frontend/src/components/ProductCreateModal.vue` (ANGEPASST)

### Akzeptanzkriterien
- ✅ BaseTextarea mit label, error, hint, rows, disabled
- ✅ BaseCheckbox mit custom styling und checkmark animation
- ✅ BaseRadio mit checked state und radio mark
- ✅ v-model Support für alle Komponenten
- ✅ Error/Disabled States
- ✅ 43 Unit Tests (alle bestanden)
- ✅ Integration in 6 bestehende Modals
- ⚪ BaseDatePicker (verschoben auf späteren Sprint)

**Geschätzter Aufwand:** 2-3 Stunden (tatsächlich ~2.5h)

---

## Empfohlene Reihenfolge

### Sprint 1 (Priorität)
1. **Confirmation Dialogs** (2-3h) - Sofort nützlich, häufig benötigt
2. **Table Sortierung** (1-2h) - Schneller Win, verbessert UX
3. **Loading States** (2-3h) - Polishing, bessere Wahrnehmung

**Gesamt:** 5-8 Stunden

### Sprint 2 (Erweitert)
4. **Formular-Validierung** (3-4h) - Verhindert fehlerhafte Submissions
5. **Dashboard Statistiken** (3-4h) - Backend + Frontend, hoher Impact

**Gesamt:** 6-8 Stunden

### Sprint 3 (Nice-to-Have)
6. **Error Handler** (2h) - Robustheit
7. **Form-Komponenten** (2-3h) - Vervollständigt Component Library

**Gesamt:** 4-5 Stunden

---

## Weitere Aufgaben (nicht priorisiert)

Aus TODO.md:
- [ ] Deployment-Dokumentation aktualisieren
- [ ] Performance-Optimierung (Code Splitting, Lazy Loading)
- [ ] Internationalisierung (i18n)
- [ ] Backup & Recovery Tests
- [ ] Security Audit
- [ ] GDPR Compliance Review

Diese können in späteren Sprints behandelt werden.
