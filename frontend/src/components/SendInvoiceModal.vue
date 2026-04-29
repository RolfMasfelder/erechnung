<template>
  <BaseModal :isOpen="true" size="md" @close="$emit('close')">
    <template #title>
      📤 Rechnung {{ invoice?.invoice_number }} versenden
    </template>

    <form class="send-form" @submit.prevent="submit">
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

    <template #footer>
      <BaseButton variant="secondary" @click="$emit('close')">
        Abbrechen
      </BaseButton>
      <BaseButton
        variant="primary"
        :loading="submitting"
        :disabled="submitting || !form.recipient"
        @click="submit"
      >
        📤 Jetzt versenden
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
