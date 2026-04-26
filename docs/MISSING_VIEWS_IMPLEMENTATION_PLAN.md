# Implementierungsplan: Fehlende Views

**Status:** In Arbeit
**Erstellt:** 2026-02-11
**Grund:** `PHASE_4_COMPLETE.md` markiert Views als fertig, die nur Platzhalter sind

---

## 🔍 Problem-Analyse

### Falsch dokumentierte Views in PHASE_4_COMPLETE.md

1. **CompanyDetailView.vue** ✅ (falsch)
   - Ist nur `<PlaceholderView title="Firmendetails" />`
   - Keine echte Implementierung vorhanden
   - Backend-API `/api/companies/{id}/` existiert

2. **SettingsView.vue** - Nicht in Phase 4 erwähnt
   - Ist nur `<PlaceholderView title="Einstellungen" />`
   - Navigation zeigt "Phase 4"-Hinweis
   - Sollte laut User bereits fertig sein

### Konzept-Klarstellung

Die Umstellung von Customer/Seller auf BusinessPartner:

- **Company** = Rechnungssteller (eigene Firma)
- **BusinessPartner** = Kunden/Lieferanten
- Im Frontend teilweise noch "Customer" genannt (Legacy-Code)
- Backend-APIs:
  - `/api/companies/` - CRUD für Companies ✅
  - `/api/business-partners/` - CRUD für BusinessPartners ✅

---

## 📋 Implementierungsplan

### 1. CompanyDetailView.vue (Priorität: Hoch)

**Ziel:** Vollständige Detailansicht für eine Firma anzeigen

#### Features
- **Firmendaten anzeigen:**
  - Name, Adresse (Straße, PLZ, Stadt, Land)
  - Steuernummer, USt-ID
  - E-Mail, Telefon
  - Bankverbindung (IBAN, BIC, Bankname)
  - Status (Aktiv/Inaktiv)

- **Aktionen:**
  - Bearbeiten (öffnet CompanyEditModal)
  - Löschen (mit Bestätigung)
  - Zurück zur Liste

- **Zusätzliche Informationen:**
  - Erstellungsdatum
  - Letzte Änderung
  - Anzahl verknüpfter Rechnungen (optional)

#### Struktur

```vue
<template>
  <div class="company-detail">
    <div class="page-header">
      <div>
        <BaseButton variant="secondary" @click="goBack">
          ← Zurück
        </BaseButton>
        <h1 class="page-title">{{ company?.name || 'Firma' }}</h1>
      </div>
      <div class="actions">
        <BaseButton variant="primary" @click="editCompany">
          Bearbeiten
        </BaseButton>
        <BaseButton variant="danger" @click="deleteCompany">
          Löschen
        </BaseButton>
      </div>
    </div>

    <BaseLoader v-if="loading" type="skeleton" />

    <template v-else-if="company">
      <!-- Firmendaten Card -->
      <BaseCard>
        <h2 class="section-title">Firmendaten</h2>
        <div class="detail-grid">
          <DetailItem label="Name" :value="company.name" />
          <DetailItem label="Status">
            <StatusBadge :active="company.is_active" />
          </DetailItem>
        </div>
      </BaseCard>

      <!-- Adresse Card -->
      <BaseCard>
        <h2 class="section-title">Adresse</h2>
        <div class="detail-grid">
          <DetailItem label="Straße" :value="company.street" />
          <DetailItem label="PLZ" :value="company.postal_code" />
          <DetailItem label="Stadt" :value="company.city" />
          <DetailItem label="Land" :value="company.country" />
        </div>
      </BaseCard>

      <!-- Kontakt Card -->
      <BaseCard>
        <h2 class="section-title">Kontaktinformationen</h2>
        <div class="detail-grid">
          <DetailItem label="E-Mail" :value="company.email" />
          <DetailItem label="Telefon" :value="company.phone" />
        </div>
      </BaseCard>

      <!-- Steuerdaten Card -->
      <BaseCard>
        <h2 class="section-title">Steuerdaten</h2>
        <div class="detail-grid">
          <DetailItem label="Steuernummer" :value="company.tax_number" />
          <DetailItem label="USt-ID" :value="company.vat_id" />
        </div>
      </BaseCard>

      <!-- Bankverbindung Card -->
      <BaseCard>
        <h2 class="section-title">Bankverbindung</h2>
        <div class="detail-grid">
          <DetailItem label="Bankname" :value="company.bank_name" />
          <DetailItem label="IBAN" :value="company.iban" />
          <DetailItem label="BIC" :value="company.bic" />
        </div>
      </BaseCard>
    </template>

    <!-- Edit Modal -->
    <CompanyEditModal
      v-if="showEditModal"
      :company-id="companyId"
      @close="showEditModal = false"
      @updated="handleCompanyUpdated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { companyService } from '@/api/services/companyService'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseLoader from '@/components/BaseLoader.vue'
import CompanyEditModal from '@/components/CompanyEditModal.vue'
// DetailItem-Component erstellen (siehe unten)

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { confirm } = useConfirm()

const companyId = ref(route.params.id)
const company = ref(null)
const loading = ref(false)
const showEditModal = ref(false)

const loadCompany = async () => {
  loading.value = true
  try {
    company.value = await companyService.getById(companyId.value)
  } catch (error) {
    toast.error('Fehler beim Laden der Firmendaten')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const editCompany = () => {
  showEditModal.value = true
}

const deleteCompany = async () => {
  const confirmed = await confirm({
    title: 'Firma löschen',
    message: 'Möchten Sie diese Firma wirklich löschen?',
    confirmText: 'Löschen',
    cancelText: 'Abbrechen'
  })

  if (confirmed) {
    try {
      await companyService.delete(companyId.value)
      toast.success('Firma gelöscht')
      router.push({ name: 'CompanyList' })
    } catch (error) {
      toast.error('Fehler beim Löschen der Firma')
    }
  }
}

const handleCompanyUpdated = () => {
  showEditModal.value = false
  loadCompany()
  toast.success('Firma aktualisiert')
}

const goBack = () => {
  router.push({ name: 'CompanyList' })
}

onMounted(() => {
  loadCompany()
})
</script>
```

#### Benötigte Komponenten

**DetailItem.vue** (neu erstellen)
```vue
<template>
  <div class="detail-item">
    <label class="detail-label">{{ label }}</label>
    <div class="detail-value">
      <slot>{{ value || '-' }}</slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: null }
})
</script>

<style scoped>
.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.detail-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
}
.detail-value {
  font-size: 1rem;
  color: #111827;
}
</style>
```

#### Tests erstellen

- `src/views/__tests__/CompanyDetailView.test.js`
- Mock für `companyService.getById()`
- Test: Laden, Bearbeiten, Löschen, Navigation

---

### 2. SettingsView.vue (Priorität: Mittel)

**Ziel:** Systemeinstellungen-Seite mit Konfigurationsoptionen

#### Features

**2.1 Benutzerprofil**
- Name, E-Mail anzeigen
- Passwort ändern (Modal)
- Avatar hochladen (optional)

**2.2 Firmen-Standardeinstellungen**
- Standard-Firma auswählen (Dropdown)
- Standard-MwSt.-Satz
- Standard-Zahlungsbedingungen

**2.3 Rechnungseinstellungen**
- Standard-Rechnungstyp
- Nummerierungsformat
- Standard-Fälligkeitsdauer (Tage)

**2.4 Export/Import-Einstellungen**
- Standard-Export-Format (CSV/Excel)
- Import-Regelsets verwalten

**2.5 System-Informationen**
- Version (Frontend + Backend)
- Letzte Synchronisation
- API-Status

#### Struktur

```vue
<template>
  <div class="settings-view">
    <h1 class="page-title">Einstellungen</h1>

    <!-- Benutzerprofil -->
    <BaseCard>
      <h2 class="section-title">Benutzerprofil</h2>
      <div class="profile-section">
        <div class="profile-info">
          <DetailItem label="Name" :value="user?.username" />
          <DetailItem label="E-Mail" :value="user?.email" />
        </div>
        <div class="profile-actions">
          <BaseButton variant="secondary" @click="showPasswordModal = true">
            Passwort ändern
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <!-- Firmen-Einstellungen -->
    <BaseCard>
      <h2 class="section-title">Firmen-Einstellungen</h2>
      <div class="settings-form">
        <BaseSelect
          v-model="settings.defaultCompany"
          :options="companyOptions"
          label="Standard-Firma"
          @update:model-value="saveSettings"
        />
        <BaseInput
          v-model="settings.defaultVatRate"
          type="number"
          label="Standard-MwSt.-Satz (%)"
          @blur="saveSettings"
        />
      </div>
    </BaseCard>

    <!-- Rechnungseinstellungen -->
    <BaseCard>
      <h2 class="section-title">Rechnungseinstellungen</h2>
      <div class="settings-form">
        <BaseSelect
          v-model="settings.defaultInvoiceType"
          :options="invoiceTypeOptions"
          label="Standard-Rechnungstyp"
          @update:model-value="saveSettings"
        />
        <BaseInput
          v-model="settings.defaultPaymentTerms"
          type="number"
          label="Standard-Zahlungsziel (Tage)"
          @blur="saveSettings"
        />
      </div>
    </BaseCard>

    <!-- System-Info -->
    <BaseCard>
      <h2 class="section-title">System-Informationen</h2>
      <div class="detail-grid">
        <DetailItem label="Frontend-Version" value="1.0.0" />
        <DetailItem label="Backend-Version" :value="systemInfo?.version" />
        <DetailItem label="API-Status">
          <StatusBadge :active="apiStatus.connected" />
        </DetailItem>
      </div>
    </BaseCard>

    <!-- Passwort ändern Modal -->
    <PasswordChangeModal
      v-if="showPasswordModal"
      @close="showPasswordModal = false"
      @success="handlePasswordChanged"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseSelect from '@/components/BaseSelect.vue'
import BaseInput from '@/components/BaseInput.vue'
// DetailItem, PasswordChangeModal erstellen

const authStore = useAuthStore()
const toast = useToast()

const user = ref(authStore.user)
const settings = ref({
  defaultCompany: null,
  defaultVatRate: 19,
  defaultInvoiceType: 'STANDARD',
  defaultPaymentTerms: 30
})
const showPasswordModal = ref(false)
const companyOptions = ref([])
const systemInfo = ref(null)
const apiStatus = ref({ connected: true })

const invoiceTypeOptions = [
  { value: 'STANDARD', label: 'Standardrechnung' },
  { value: 'CREDIT_NOTE', label: 'Gutschrift' },
  { value: 'CANCELLATION', label: 'Stornorechnung' }
]

const loadSettings = async () => {
  // TODO: API-Endpoint für User-Settings erstellen
  // settings.value = await settingsService.get()
}

const saveSettings = async () => {
  try {
    // TODO: API-Endpoint für Settings speichern
    // await settingsService.save(settings.value)
    toast.success('Einstellungen gespeichert')
  } catch (error) {
    toast.error('Fehler beim Speichern der Einstellungen')
  }
}

const handlePasswordChanged = () => {
  showPasswordModal.value = false
  toast.success('Passwort erfolgreich geändert')
}

onMounted(() => {
  loadSettings()
})
</script>
```

#### Benötigte Backend-Endpunkte (TODO)

1. **UserSettings API:**
   ```
   GET /api/user-settings/
   PUT /api/user-settings/
   PATCH /api/user-settings/
   ```

2. **Password Change API:**
   ```
   POST /api/auth/change-password/
   ```

3. **System Info API:**
   ```
   GET /api/system/info/
   ```

#### Benötigte Komponenten

- **PasswordChangeModal.vue** (neu)
- **StatusBadge.vue** (neu oder aus BaseAlert ableiten)

---

## 📝 Aufgabenliste

### Phase 1: CompanyDetailView ✅ Bereit zur Implementierung

- [ ] `CompanyDetailView.vue` erstellen
- [ ] `DetailItem.vue` Component erstellen
- [ ] `StatusBadge.vue` Component erstellen (oder bestehende nutzen)
- [ ] CompanyDetailView-Tests schreiben
- [ ] Router-Route testen
- [ ] PHASE_4_COMPLETE.md korrigieren

### Phase 2: SettingsView (Backend-Dependency)

- [ ] Backend: UserSettings Model erstellen
- [ ] Backend: UserSettings API-Endpoints implementieren
- [ ] Backend: Password-Change-Endpoint erweitern
- [ ] Backend: System-Info-Endpoint erstellen
- [ ] Frontend: `SettingsView.vue` implementieren
- [ ] Frontend: `PasswordChangeModal.vue` erstellen
- [ ] Frontend: `settingsService.js` erstellen
- [ ] Tests schreiben

### Phase 3: Dokumentation

- [ ] `PHASE_4_COMPLETE.md` korrigieren
- [ ] API_SPECIFICATION.md erweitern (UserSettings)
- [ ] PROGRESS_PROTOCOL.md aktualisieren

---

## 🔄 Migration: Customer → BusinessPartner

**Status:** Teilweise migriert

### Noch zu bereinigen:

1. **Frontend-Bezeichnungen:**
   - `CustomerListView` → Nutzt BusinessPartner-API ✅
   - `CustomerDetailView` → Nutzt BusinessPartner-API ✅
   - Variablennamen `customer` in `businessPartner` umbenennen (optional)

2. **API-Service:**
   - `customerService.js` prüfen, ob es `/business-partners/` nutzt
   - Eventuell in `businessPartnerService.js` umbenennen

3. **Router:**
   - Route-Namen prüfen (`CustomerList` vs. `BusinessPartnerList`)

---

## 📊 Aufwand-Schätzung

| Task | Aufwand | Priorität |
|------|---------|-----------|
| CompanyDetailView + Tests | 2h | Hoch |
| DetailItem.vue | 0.5h | Hoch |
| StatusBadge.vue | 0.5h | Mittel |
| Backend: UserSettings Model + API | 3h | Mittel |
| SettingsView.vue | 2h | Mittel |
| PasswordChangeModal.vue | 1h | Mittel |
| Tests für Settings | 1h | Mittel |
| Dokumentation aktualisieren | 1h | Niedrig |
| **Gesamt** | **11h** | |

---

## 🚀 Nächste Schritte

1. **Sofort umsetzbar (ohne Backend-Änderungen):**
   - CompanyDetailView.vue implementieren
   - DetailItem.vue Component erstellen
   - Tests schreiben
   - PHASE_4_COMPLETE.md korrigieren

2. **Backend-Abhängig:**
   - UserSettings-API implementieren
   - SettingsView.vue implementieren

3. **Optional (Refactoring):**
   - Customer → BusinessPartner Bezeichnungen bereinigen
   - customerService → businessPartnerService umbenennen

---

**Erstellt:** 2026-02-11
**Letzte Aktualisierung:** 2026-02-11
**Status:** 🟡 Implementierung ausstehend
