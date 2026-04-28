<template>
  <div class="settings-view">
    <h1>Einstellungen</h1>

    <div class="tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        role="tab"
        :aria-selected="activeTab === tab.id"
        :class="['tab', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="loading">Lade Einstellungen…</div>
    <div v-else-if="loadError" class="error" role="alert">{{ loadError }}</div>

    <!-- Profil -->
    <section v-else-if="activeTab === 'profile'" class="panel" role="tabpanel">
      <div class="row">
        <label>Benutzername</label>
        <input :value="settings.username" disabled />
      </div>
      <div class="row">
        <label>E-Mail</label>
        <input :value="settings.email" disabled />
      </div>
      <div class="row">
        <label for="language">Sprache</label>
        <select id="language" v-model="settings.language">
          <option value="en">English</option>
          <option value="de">Deutsch</option>
          <option value="fr">Français</option>
          <option value="es">Español</option>
        </select>
      </div>
      <div class="row">
        <label for="timezone">Zeitzone</label>
        <input id="timezone" v-model="settings.timezone" />
      </div>
      <div class="row">
        <label for="date_format">Datumsformat</label>
        <select id="date_format" v-model="settings.date_format">
          <option value="%Y-%m-%d">YYYY-MM-DD</option>
          <option value="%d.%m.%Y">DD.MM.YYYY</option>
          <option value="%m/%d/%Y">MM/DD/YYYY</option>
          <option value="%d/%m/%Y">DD/MM/YYYY</option>
        </select>
      </div>
      <SaveBar :saving="saving" :status="saveStatus" @save="save" />
    </section>

    <!-- Defaults / Benachrichtigungen -->
    <section v-else-if="activeTab === 'defaults'" class="panel" role="tabpanel">
      <fieldset>
        <legend>Rechnungs-Defaults</legend>
        <div class="row">
          <label for="default_currency">Standard-Währung</label>
          <input
            id="default_currency"
            v-model="settings.default_currency"
            maxlength="3"
          />
        </div>
        <div class="row">
          <label for="default_payment_terms_days">Zahlungsziel (Tage)</label>
          <input
            id="default_payment_terms_days"
            v-model.number="settings.default_payment_terms_days"
            type="number"
            min="0"
          />
        </div>
      </fieldset>

      <fieldset>
        <legend>E-Mail-Benachrichtigungen</legend>
        <label class="checkbox">
          <input v-model="settings.email_notifications" type="checkbox" />
          E-Mail-Benachrichtigungen aktivieren
        </label>
        <label class="checkbox">
          <input
            v-model="settings.notify_invoice_paid"
            type="checkbox"
            :disabled="!settings.email_notifications"
          />
          Bei bezahlter Rechnung benachrichtigen
        </label>
        <label class="checkbox">
          <input
            v-model="settings.notify_invoice_overdue"
            type="checkbox"
            :disabled="!settings.email_notifications"
          />
          Bei überfälliger Rechnung benachrichtigen
        </label>
      </fieldset>
      <SaveBar :saving="saving" :status="saveStatus" @save="save" />
    </section>

    <!-- Passwort -->
    <section v-else-if="activeTab === 'password'" class="panel" role="tabpanel">
      <p>
        Aus Sicherheitsgründen erfolgt die Passwortänderung in einem separaten
        Dialog.
      </p>
      <button type="button" class="btn btn-primary" @click="showPasswordModal = true">
        Passwort ändern…
      </button>
      <p v-if="passwordChangedToast" class="success" role="status">
        Passwort wurde erfolgreich geändert.
      </p>
    </section>

    <!-- System -->
    <section v-else-if="activeTab === 'system'" class="panel" role="tabpanel">
      <div v-if="systemInfo" class="system-info">
        <div class="row"><label>Anwendungs-Version</label><code>{{ systemInfo.app_version }}</code></div>
        <div class="row"><label>Django-Version</label><code>{{ systemInfo.django_version }}</code></div>
        <div class="row"><label>Python-Version</label><code>{{ systemInfo.python_version }}</code></div>
        <div class="row"><label>Debug</label><code>{{ systemInfo.debug }}</code></div>
      </div>
      <button type="button" class="btn btn-secondary" @click="loadSystemInfo">
        Aktualisieren
      </button>
    </section>

    <PasswordChangeModal
      v-if="showPasswordModal"
      @close="showPasswordModal = false"
      @changed="onPasswordChanged"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, h } from 'vue'
import { settingsService } from '../api/services/settingsService'
import PasswordChangeModal from '../components/PasswordChangeModal.vue'

const tabs = [
  { id: 'profile', label: 'Profil' },
  { id: 'defaults', label: 'Defaults & Benachrichtigungen' },
  { id: 'password', label: 'Passwort' },
  { id: 'system', label: 'System-Info' },
]
const activeTab = ref('profile')

const settings = reactive({
  username: '',
  email: '',
  language: 'en',
  timezone: 'UTC',
  date_format: '%Y-%m-%d',
  email_notifications: true,
  notify_invoice_paid: true,
  notify_invoice_overdue: true,
  default_currency: 'EUR',
  default_payment_terms_days: 30,
})

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const saveStatus = ref('')
const systemInfo = ref(null)
const showPasswordModal = ref(false)
const passwordChangedToast = ref(false)

const SaveBar = {
  props: ['saving', 'status'],
  emits: ['save'],
  setup(props, { emit }) {
    return () =>
      h('div', { class: 'save-bar' }, [
        h(
          'button',
          {
            type: 'button',
            class: 'btn btn-primary',
            disabled: props.saving,
            onClick: () => emit('save'),
          },
          props.saving ? 'Speichere…' : 'Speichern',
        ),
        props.status
          ? h('span', { class: 'save-status', role: 'status' }, props.status)
          : null,
      ])
  },
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await settingsService.getMe()
    Object.assign(settings, data)
  } catch (err) {
    loadError.value =
      err?.response?.status === 404
        ? 'Für diesen Benutzer wurde noch kein Profil angelegt. Bitte den Administrator kontaktieren.'
        : 'Einstellungen konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function loadSystemInfo() {
  try {
    systemInfo.value = await settingsService.getSystemInfo()
  } catch {
    systemInfo.value = null
  }
}

async function save() {
  saving.value = true
  saveStatus.value = ''
  try {
    const data = await settingsService.patch({
      language: settings.language,
      timezone: settings.timezone,
      date_format: settings.date_format,
      email_notifications: settings.email_notifications,
      notify_invoice_paid: settings.notify_invoice_paid,
      notify_invoice_overdue: settings.notify_invoice_overdue,
      default_currency: settings.default_currency,
      default_payment_terms_days: settings.default_payment_terms_days,
    })
    Object.assign(settings, data)
    saveStatus.value = 'Gespeichert.'
  } catch {
    saveStatus.value = 'Speichern fehlgeschlagen.'
  } finally {
    saving.value = false
  }
}

function onPasswordChanged() {
  passwordChangedToast.value = true
  setTimeout(() => (passwordChangedToast.value = false), 4000)
}

onMounted(() => {
  load()
  loadSystemInfo()
})
</script>

<style scoped>
.settings-view {
  padding: 1.5rem;
  max-width: 800px;
}
h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
}
.tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 1.25rem;
}
.tab {
  padding: 0.5rem 1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  font-size: 0.875rem;
}
.tab.active {
  border-bottom-color: #2563eb;
  font-weight: 600;
}
.panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
fieldset {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
legend {
  font-weight: 600;
  font-size: 0.875rem;
  padding: 0 0.5rem;
}
.row {
  display: grid;
  grid-template-columns: 220px 1fr;
  align-items: center;
  gap: 0.75rem;
}
label {
  font-weight: 500;
  font-size: 0.875rem;
}
input,
select {
  padding: 0.4rem 0.6rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}
input:disabled {
  background: #f9fafb;
  color: #6b7280;
}
.checkbox {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-weight: 500;
  font-size: 0.875rem;
}
.btn {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn-primary {
  background: #2563eb;
  color: white;
}
.btn-secondary {
  background: #f3f4f6;
  border-color: #d1d5db;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.save-bar {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-top: 0.5rem;
}
.save-status {
  font-size: 0.875rem;
  color: #15803d;
}
.error {
  color: #b91c1c;
  font-size: 0.875rem;
}
.success {
  color: #15803d;
  font-size: 0.875rem;
}
.system-info code {
  background: #f3f4f6;
  padding: 0.1rem 0.4rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}
.loading {
  font-size: 0.875rem;
  color: #6b7280;
}
</style>
