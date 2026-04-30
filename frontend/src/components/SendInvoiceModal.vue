<template>
  <BaseModal :isOpen="true" size="md" @close="$emit('close')">
    <template #title>
      📤 Rechnung {{ invoice?.invoice_number }} versenden
    </template>

    <!-- Delivery mode selector -->
    <div class="delivery-modes">
      <button
        type="button"
        :class="['mode-btn', { active: deliveryMode === 'email' }]"
        @click="deliveryMode = 'email'"
      >
        📧 E-Mail
      </button>
      <button
        type="button"
        :class="['mode-btn', { active: deliveryMode === 'download' }]"
        @click="deliveryMode = 'download'"
      >
        📥 Datei herunterladen
      </button>
      <button
        type="button"
        class="mode-btn"
        disabled
        title="Kommt in einer späteren Version"
      >
        🔗 Peppol/Portal
      </button>
    </div>

    <!-- E-Mail mode -->
    <form v-if="deliveryMode === 'email'" class="send-form" @submit.prevent="submit">
      <BaseAlert v-if="error" type="error">{{ error }}</BaseAlert>

      <BaseAlert v-if="alreadySent" type="info">
        Diese Rechnung wurde bereits am
        <strong>{{ formatDateTime(invoice.last_emailed_at) }}</strong>
        an
        <strong>{{ invoice.last_email_recipient }}</strong>
        versendet. Erneuter Versand ist möglich.
      </BaseAlert>

      <div class="form-row">
        <label for="send-recipient">Empfänger-E-Mail-Adresse *</label>
        <input
          id="send-recipient"
          v-model.trim="form.recipient"
          type="email"
          required
          autocomplete="email"
          :placeholder="recipientPlaceholder"
        />
        <small v-if="suggestedFromPartner" class="hint">
          Vorausgefüllt aus den Stammdaten des Geschäftspartners.
        </small>
      </div>

      <div class="form-row">
        <label for="send-message">Persönliche Nachricht (optional)</label>
        <textarea
          id="send-message"
          v-model="form.message"
          rows="4"
          placeholder="z. B. „Anbei die Rechnung für die im April erbrachten Leistungen.“"
        />
      </div>

      <details class="advanced">
        <summary>Erweiterte Optionen</summary>
        <label class="checkbox">
          <input v-model="form.attachXml" type="checkbox" />
          XML zusätzlich als separates Attachment anhängen
          <small>
            Nur für reine XRechnung-Workflows nötig — die XML ist bereits
            EN16931-konform im PDF/A-3 eingebettet.
          </small>
        </label>
      </details>

      <BaseAlert v-if="!emailEnabled" type="warning">
        E-Mail-Versand ist auf diesem Server deaktiviert
        (<code>INVOICE_EMAIL_ENABLED=false</code>). Bitte den Administrator
        kontaktieren.
      </BaseAlert>
    </form>

    <!-- Download mode -->
    <div v-else-if="deliveryMode === 'download'" class="send-form">
      <BaseAlert type="info">
        <strong v-if="isGovernment">XRechnung (XML)</strong>
        <strong v-else>PDF/A-3 (ZUGFeRD)</strong>
        wird heruntergeladen.
        <span v-if="isGovernment">
          Optimiert für B2G/Behörden-Workflows (XRechnung EN16931-konform).
        </span>
        <span v-else>
          Enthält eingebettete ZUGFeRD-XML (EN16931-konform, Factur-X).
        </span>
      </BaseAlert>
      <BaseAlert v-if="downloadError" type="error">{{ downloadError }}</BaseAlert>
    </div>

    <!-- Peppol mode -->
    <div v-else class="send-form">
      <BaseAlert type="warning">
        Peppol/Portal-Zustellung ist noch nicht verfügbar.
        Diese Funktion wird in einer späteren Version implementiert.
      </BaseAlert>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">
        Abbrechen
      </BaseButton>
      <!-- Email mode -->
      <BaseButton
        v-if="deliveryMode === 'email'"
        variant="primary"
        :loading="submitting"
        :disabled="submitting || !form.recipient"
        @click="submit"
      >
        📤 Jetzt versenden
      </BaseButton>
      <!-- Download mode -->
      <BaseButton
        v-else-if="deliveryMode === 'download'"
        variant="secondary"
        :loading="downloading"
        @click="handleDownload"
      >
        📥 {{ isGovernment ? 'XML herunterladen' : 'PDF herunterladen' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'
import BaseAlert from './BaseAlert.vue'
import { invoiceService } from '@/api/services/invoiceService'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  invoice: { type: Object, required: true },
})
const emit = defineEmits(['close', 'sent'])
const toast = useToast()

// Delivery mode: 'email' | 'download' | 'peppol'
const deliveryMode = ref('email')

const isGovernment = computed(
  () => props.invoice?.business_partner_details?.partner_type === 'GOVERNMENT'
)

// Pre-fill recipient from business_partner.email if available
const partnerEmail =
  props.invoice?.business_partner_details?.email ||
  props.invoice?.last_email_recipient ||
  ''

const form = reactive({
  recipient: partnerEmail,
  message: '',
  attachXml: false,
})

const suggestedFromPartner = computed(
  () =>
    !!props.invoice?.business_partner_details?.email &&
    form.recipient === props.invoice.business_partner_details.email,
)

const recipientPlaceholder = computed(() => 'kunde@example.com')

const alreadySent = computed(() => !!props.invoice?.last_emailed_at)

// Optimistic — backend will return 503 if disabled. No /system/info field yet.
const emailEnabled = ref(true)

const submitting = ref(false)
const error = ref('')
const downloading = ref(false)
const downloadError = ref('')

function formatDateTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function handleDownload() {
  downloadError.value = ''
  downloading.value = true
  try {
    let blob, filename
    if (isGovernment.value) {
      await invoiceService.generateXml(props.invoice.id)
      blob = await invoiceService.downloadXML(props.invoice.id)
      filename = `invoice-${props.invoice.invoice_number}.xml`
      toast.success('XRechnung XML erfolgreich heruntergeladen')
    } else {
      blob = await invoiceService.downloadPDF(props.invoice.id)
      filename = `invoice-${props.invoice.invoice_number}.pdf`
      toast.success('PDF erfolgreich heruntergeladen')
    }
    const url = globalThis.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    globalThis.URL.revokeObjectURL(url)
    a.remove()
    emit('close')
  } catch (err) {
    const detail =
      err?.response?.data?.detail || err?.message || 'Fehler beim Herunterladen'
    downloadError.value = detail
  } finally {
    downloading.value = false
  }
}

async function submit() {
  error.value = ''
  if (!form.recipient) {
    error.value = 'Bitte eine Empfänger-E-Mail-Adresse angeben.'
    return
  }
  submitting.value = true
  try {
    const result = await invoiceService.sendEmail(props.invoice.id, {
      recipient: form.recipient,
      message: form.message,
      attachXml: form.attachXml,
    })
    toast.success(`Rechnung an ${result.recipient} versendet.`)
    emit('sent', result)
    emit('close')
  } catch (err) {
    const status = err?.response?.status
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.error?.message ||
      err?.message ||
      'Unbekannter Fehler beim Versand.'
    if (status === 503) {
      emailEnabled.value = false
      error.value = `E-Mail-Versand nicht verfügbar: ${detail}`
    } else if (status === 400) {
      error.value = `Ungültige Eingabe: ${detail}`
    } else {
      error.value = detail
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.delivery-modes {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}
.mode-btn {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  background: #f9fafb;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  transition: background 0.15s, border-color 0.15s;
}
.mode-btn:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #3b82f6;
}
.mode-btn.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}
.mode-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.send-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.form-row label {
  font-weight: 600;
  font-size: 0.9rem;
}
.form-row input,
.form-row textarea {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: inherit;
}
.form-row .hint {
  color: #666;
  font-size: 0.8rem;
}
.advanced {
  border-top: 1px solid #eee;
  padding-top: 0.5rem;
}
.advanced summary {
  cursor: pointer;
  font-weight: 600;
  user-select: none;
}
.checkbox {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.5rem;
  cursor: pointer;
}
.checkbox small {
  margin-left: 1.5rem;
  color: #666;
  font-size: 0.8rem;
}
</style>
