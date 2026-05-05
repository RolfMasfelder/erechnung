<template>
  <div class="invoice-detail">
    <div class="page-header">
      <div class="page-header-top">
        <div>
          <router-link to="/invoices" class="back-link">← Zurück</router-link>
          <h1 class="page-title">
            <span v-if="invoice?.invoice_type === 'CREDIT_NOTE'" class="type-badge type-credit-note">Gutschrift</span>
            {{ invoice?.invoice_number }}
          </h1>
        </div>

      <div class="actions">
        <BaseButton
          v-if="invoice?.status?.toUpperCase() === 'DRAFT'"
          variant="primary"
          @click="showEditModal = true"
        >
          ✏️ Bearbeiten
        </BaseButton>
        <BaseButton
          variant="secondary"
          :loading="downloading"
          :title="smartDownloadTooltip"
          @click="smartDownload"
        >
          📥 {{ smartDownloadLabel }}
        </BaseButton>
        <BaseButton
          variant="secondary"
          title="PDF im Browser öffnen (Vorschau)"
          @click="previewPDF"
        >
          👁 Vorschau
        </BaseButton>
        <BaseButton
          v-if="canSendEmail"
          variant="primary"
          @click="showSendModal = true"
        >
          📤 Per E-Mail versenden
        </BaseButton>
        <BaseButton
          v-if="canSendEmail && isGovernment"
          variant="primary"
          :loading="sendingXRechnung"
          @click="handleSendXRechnung"
        >
          🏛️ XRechnung versenden
        </BaseButton>
        <BaseButton
          v-if="invoice?.status?.toUpperCase() === 'DRAFT'"
          variant="danger"
          @click="handleDelete"
        >
          🗑️ Löschen
        </BaseButton>
        <BaseButton
          v-if="canCancel"
          variant="danger"
          @click="showCancelDialog = true"
        >
          ❌ Stornieren
        </BaseButton>
      </div>
      </div><!-- end page-header-top -->
      <div v-if="invoice?.last_emailed_at" class="versand-status">
        📧 Zuletzt versendet: {{ formatDateTime(invoice.last_emailed_at) }}
        <span v-if="invoice.last_email_recipient"> an <strong>{{ invoice.last_email_recipient }}</strong></span>
      </div>
      <div v-if="invoice?.xrechnung_sent_at" class="versand-status">
        🏛️ XRechnung versendet: {{ formatDateTime(invoice.xrechnung_sent_at) }}
        <span v-if="invoice.xrechnung_sent_to"> an <strong>{{ invoice.xrechnung_sent_to }}</strong></span>
      </div>
    </div><!-- end page-header -->

    <div v-if="loading" class="loading">
      Lädt Rechnung...
    </div>

    <div v-else-if="invoice" class="invoice-content">
      <!-- Edit-Lock: Banner when locked by someone else -->
      <div
        v-if="invoice.editing_by_display"
        class="edit-lock-banner"
      >
        ✏️ Wird gerade bearbeitet von
        <strong>{{ invoice.editing_by_display }}</strong>
        <span v-if="invoice.editing_since">
          (seit {{ formatTime(invoice.editing_since) }})
        </span>.
      </div>
      <BaseCard title="Rechnungsdetails">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Rechnungsnummer:</span>
            <span class="detail-value">{{ invoice.invoice_number }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Status:</span>
            <span :class="['status-badge', `status-${invoice.status?.toLowerCase()}`]">
              {{ getStatusLabel(invoice.status) }}
            </span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Kunde:</span>
            <span class="detail-value">{{ invoice.business_partner_details?.name }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Rechnungsdatum:</span>
            <span class="detail-value">{{ formatDate(invoice.issue_date) }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Fälligkeitsdatum:</span>
            <span class="detail-value">{{ formatDate(invoice.due_date) }}</span>
          </div>

          <div v-if="invoice.buyer_reference" class="detail-item">
            <span class="detail-label">Ihr Zeichen:</span>
            <span class="detail-value">{{ invoice.buyer_reference }}</span>
          </div>

          <div v-if="invoice.seller_reference" class="detail-item">
            <span class="detail-label">Unser Zeichen:</span>
            <span class="detail-value">{{ invoice.seller_reference }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Gesamtbetrag:</span>
            <span class="detail-value strong">{{ formatCurrency(invoice.total_amount) }}</span>
          </div>

          <!-- Cross-links: Storno-Referenzen -->
          <div v-if="invoice.cancelled_by_number" class="detail-item">
            <span class="detail-label">Storniert durch:</span>
            <router-link
              :to="{ name: 'InvoiceDetail', params: { id: invoice.cancelled_by_id } }"
              class="cross-link"
            >
              {{ invoice.cancelled_by_number }}
            </router-link>
          </div>

          <div v-if="invoice.cancels_invoice_number" class="detail-item">
            <span class="detail-label">Storno zu:</span>
            <router-link
              :to="{ name: 'InvoiceDetail', params: { id: invoice.cancels_invoice_id } }"
              class="cross-link"
            >
              {{ invoice.cancels_invoice_number }}
            </router-link>
          </div>
        </div>
      </BaseCard>

      <BaseCard title="Positionen">
        <BaseTable
          v-if="invoice.lines && invoice.lines.length > 0"
          :columns="lineColumns"
          :data="invoice.lines"
        >
          <template #cell-quantity="{ value }">
            {{ formatQuantity(value) }}
          </template>
          <template #cell-unit_price_net="{ value }">
            {{ formatCurrency(value) }}
          </template>
          <template #cell-discount_percentage="{ value }">
            {{ parseFloat(value) > 0 ? parseFloat(value).toLocaleString('de-DE', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + ' %' : '-' }}
          </template>
          <template #cell-discount_amount="{ value }">
            {{ parseFloat(value) > 0 ? formatCurrency(value) : '-' }}
          </template>
          <template #cell-vat_rate="{ value }">
            {{ value }}%
          </template>
          <template #cell-line_total="{ row }">
            {{ formatCurrency(parseFloat(row.line_total) + parseFloat(row.tax_amount)) }}
          </template>
        </BaseTable>
        <p v-else class="placeholder">Keine Positionen vorhanden.</p>

        <!-- Zusammenfassung -->
        <div v-if="invoice.lines && invoice.lines.length > 0" class="summary">
          <!-- Ohne Rechnungsebene-Korrekturen: einfache Anzeige -->
          <div v-if="!hasHeaderAdjustments" class="summary-row">
            <span>Netto:</span>
            <span>{{ formatCurrency(invoice.subtotal) }}</span>
          </div>

          <!-- Mit Rechnungsebene-Korrekturen: Positionen → Rabatte/Zuschläge → Netto nach Abzügen -->
          <template v-if="hasHeaderAdjustments">
            <div class="summary-row">
              <span>Positionen (Netto):</span>
              <span>{{ formatCurrency(linesSubtotal) }}</span>
            </div>

            <!-- Rechnungsebene-Rabatte -->
            <div
              v-for="ac in headerAllowances"
              :key="'allow-' + ac.id"
              class="summary-row allowance-row"
            >
              <span>Rabatt ({{ ac.reason || 'Rechnungsebene' }}):</span>
              <span class="negative">-{{ formatCurrency(ac.actual_amount) }}</span>
            </div>

            <!-- Rechnungsebene-Zuschläge -->
            <div
              v-for="ac in headerCharges"
              :key="'charge-' + ac.id"
              class="summary-row charge-row"
            >
              <span>Zuschlag ({{ ac.reason || 'Rechnungsebene' }}):</span>
              <span>+{{ formatCurrency(ac.actual_amount) }}</span>
            </div>

            <div class="summary-row subtotal-adjusted-row">
              <span>Netto nach Abzügen:</span>
              <span>{{ formatCurrency(netAfterAdjustments) }}</span>
            </div>
          </template>

          <div class="summary-row">
            <span>MwSt.:</span>
            <span>{{ formatCurrency(correctedTaxAmount) }}</span>
          </div>
          <div class="summary-row total">
            <span>Gesamt (Brutto):</span>
            <span>{{ formatCurrency(correctedGrandTotal) }}</span>
          </div>
        </div>
      </BaseCard>

      <!-- Notizen -->
      <BaseCard v-if="invoice.notes" title="Notizen">
        <div class="notes-content">
          <template v-for="(line, idx) in invoice.notes.split('\n')" :key="idx">
            <p v-if="line.startsWith('⚠️')" class="note-warning">{{ line }}</p>
            <p v-else>{{ line }}</p>
          </template>
        </div>
      </BaseCard>

      <!-- Rechnungsbegründende Dokumente -->
      <InvoiceAttachments
        :invoice-id="invoice.id"
        :is-draft="invoice.status?.toUpperCase() === 'DRAFT'"
      />
    </div>

    <BaseAlert v-else type="error">
      Rechnung konnte nicht geladen werden.
    </BaseAlert>

    <!-- Edit Modal -->
    <InvoiceEditModal
      v-if="showEditModal"
      :invoice-id="invoice.id"
      @close="showEditModal = false"
      @updated="handleInvoiceUpdated"
    />

    <!-- Send-Email Modal -->
    <SendInvoiceModal
      v-if="showSendModal && invoice"
      :invoice="invoice"
      @close="showSendModal = false"
      @sent="handleEmailSent"
    />

    <!-- Cancel Confirmation Dialog -->
    <div v-if="showCancelDialog" class="modal-overlay" @click.self="showCancelDialog = false">
      <div class="modal-content cancel-dialog">
        <h2>Rechnung stornieren</h2>
        <p>
          Möchten Sie die Rechnung <strong>{{ invoice?.invoice_number }}</strong> wirklich stornieren?
          Es wird eine Gutschrift (Stornorechnung) erstellt.
        </p>
        <div class="form-group">
          <label for="cancelReason">Stornogrund (Pflicht):</label>
          <textarea
            id="cancelReason"
            v-model="cancelReason"
            rows="3"
            placeholder="Bitte geben Sie den Grund für die Stornierung an..."
            class="cancel-reason-input"
          />
        </div>
        <div class="dialog-actions">
          <BaseButton variant="secondary" @click="showCancelDialog = false">
            Abbrechen
          </BaseButton>
          <BaseButton
            variant="danger"
            :disabled="!cancelReason.trim()"
            :loading="cancelling"
            @click="handleCancel"
          >
            Stornieren
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseAlert from '@/components/BaseAlert.vue'
import BaseTable from '@/components/BaseTable.vue'
import InvoiceEditModal from '@/components/InvoiceEditModal.vue'
import InvoiceAttachments from '@/components/InvoiceAttachments.vue'
import SendInvoiceModal from '@/components/SendInvoiceModal.vue'
import { invoiceService } from '@/api/services/invoiceService'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const loading = ref(false)
const downloading = ref(false)
const sendingXRechnung = ref(false)
const invoice = ref(null)
const showEditModal = ref(false)
const showSendModal = ref(false)
const showCancelDialog = ref(false)
const cancelReason = ref('')
const cancelling = ref(false)

// Smart-Download: B2G → XRechnung XML, sonst → PDF
const isGovernment = computed(
  () => invoice.value?.business_partner_details?.partner_type === 'GOVERNMENT'
)

const smartDownloadLabel = computed(() =>
  isGovernment.value ? 'XML herunterladen' : 'PDF herunterladen'
)

const smartDownloadTooltip = computed(() =>
  isGovernment.value
    ? 'XRechnung (XML) generieren und herunterladen (B2G)'
    : 'PDF/A-3 mit eingebetteter ZUGFeRD-XML herunterladen'
)

// Cancel button visible only for SENT or PAID invoices (not credit notes)
const canCancel = computed(() => {
  if (!invoice.value) return false
  const s = invoice.value.status?.toUpperCase()
  return (s === 'SENT' || s === 'PAID') && invoice.value.invoice_type !== 'CREDIT_NOTE'
})

// Send-Email is allowed in any non-cancelled state (DRAFT auto-transitions to SENT).
const canSendEmail = computed(() => {
  if (!invoice.value) return false
  const s = invoice.value.status?.toUpperCase()
  return s !== 'CANCELLED' && invoice.value.invoice_type !== 'CREDIT_NOTE'
})

// Prüfen ob mindestens eine Position einen Rabatt hat
const hasDiscounts = computed(() => {
  if (!invoice.value?.lines) return false
  return invoice.value.lines.some(
    (line) => Number.parseFloat(line.discount_percentage) > 0 || Number.parseFloat(line.discount_amount) > 0
  )
})

// Rechnungsebene-Rabatte und -Zuschläge
const hasHeaderAdjustments = computed(() => {
  return (invoice.value?.allowance_charges || []).length > 0
})

const headerAllowances = computed(() =>
  (invoice.value?.allowance_charges || []).filter((ac) => !ac.is_charge),
)

const headerCharges = computed(() =>
  (invoice.value?.allowance_charges || []).filter((ac) => ac.is_charge),
)

const totalHeaderAllowances = computed(() =>
  headerAllowances.value.reduce((sum, ac) => sum + Number.parseFloat(ac.actual_amount), 0),
)

const totalHeaderCharges = computed(() =>
  headerCharges.value.reduce((sum, ac) => sum + Number.parseFloat(ac.actual_amount), 0),
)

// Zeilensumme (Netto, vor Rechnungsebene-Korrekturen)
// = invoice.subtotal (= Steuerbasis) + Allowances - Charges
const linesSubtotal = computed(() => {
  return (
    (Number.parseFloat(invoice.value?.subtotal) || 0) +
    totalHeaderAllowances.value -
    totalHeaderCharges.value
  )
})

// Nach Modell-Fix: invoice.subtotal = Steuerbasis (bereits korrekt),
// invoice.tax_amount und invoice.total_amount werden vom Modell korrekt berechnet.
// Die folgenden Werte kommen direkt aus dem Modell (kein Frontend-Recompute nötig).
const netAfterAdjustments = computed(() => Number.parseFloat(invoice.value?.subtotal) || 0)
const correctedTaxAmount = computed(() => Number.parseFloat(invoice.value?.tax_amount) || 0)
const correctedGrandTotal = computed(() => Number.parseFloat(invoice.value?.total_amount) || 0)

const lineColumns = computed(() => {
  const cols = [
    { key: 'id', label: 'Pos.' },
    { key: 'product_name', label: 'Produkt' },
    { key: 'description', label: 'Beschreibung' },
    { key: 'quantity', label: 'Menge' },
    { key: 'unit_price_net', label: 'Einzelpreis (Netto)' },
  ]
  if (hasDiscounts.value) {
    cols.push(
      { key: 'discount_percentage', label: 'Rabatt %' },
      { key: 'discount_amount', label: 'Rabattbetrag' },
    )
  }
  cols.push(
    { key: 'vat_rate', label: 'MwSt.' },
    { key: 'line_total', label: 'Gesamt (Brutto)' },
  )
  return cols
})

const loadInvoice = async () => {
  loading.value = true
  try {
    const id = route.params.id
    invoice.value = await invoiceService.getById(id)
  } catch (error) {
    console.error('Failed to load invoice:', error)
  } finally {
    loading.value = false
  }
}

const smartDownload = async () => {
  downloading.value = true
  try {
    let blob, filename
    if (isGovernment.value) {
      await invoiceService.generateXml(route.params.id)
      blob = await invoiceService.downloadXML(route.params.id)
      filename = `invoice-${invoice.value.invoice_number}.xml`
      toast.success('XRechnung XML erfolgreich heruntergeladen')
    } else {
      blob = await invoiceService.downloadPDF(route.params.id)
      filename = `invoice-${invoice.value.invoice_number}.pdf`
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
  } catch (err) {
    const detail = err?.response?.data?.detail ?? 'Fehler beim Herunterladen'
    toast.error(detail)
  } finally {
    downloading.value = false
  }
}

const previewPDF = async () => {
  try {
    const blob = await invoiceService.downloadPDF(route.params.id)
    const url = globalThis.URL.createObjectURL(blob)
    globalThis.open(url, '_blank')
    // Revoke after browser has loaded the PDF
    setTimeout(() => globalThis.URL.revokeObjectURL(url), 60000)
  } catch (err) {
    const detail = err?.response?.data?.detail ?? 'Fehler beim Laden der PDF-Vorschau'
    toast.error(detail)
  }
}

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

const getStatusLabel = (status) => {
  const labels = {
    'DRAFT': 'Entwurf',
    'SENT': 'Versendet',
    'PAID': 'Bezahlt',
    'CANCELLED': 'Storniert',
    'OVERDUE': 'Überfällig',
    // Legacy lowercase support
    'draft': 'Entwurf',
    'sent': 'Versendet',
    'paid': 'Bezahlt',
    'cancelled': 'Storniert',
    'overdue': 'Überfällig'
  }
  return labels[status] || status
}

const formatCurrency = (value) => {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR'
  }).format(value || 0)
}

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const formatQuantity = (value) => {
  if (!value) return '0'
  // Convert to number and format without unnecessary decimals
  const num = Number.parseFloat(value)
  return new Intl.NumberFormat('de-DE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(num)
}

const handleInvoiceUpdated = (updated) => {
  showEditModal.value = false
  // Rechnung neu laden
  loadInvoice()
  // console.log('Rechnung aktualisiert:', updated)
}

const handleEmailSent = () => {
  showSendModal.value = false
  // Rechnung neu laden, damit last_emailed_at und ggf. neuer Status (DRAFT→SENT) angezeigt werden.
  loadInvoice()
}

const handleSendXRechnung = async () => {
  if (!invoice.value) return
  const partner = invoice.value.business_partner_details ?? {}
  const recipient = partner.email ?? ''
  if (!recipient) {
    alert('Kein E-Mail-Empfänger: Bitte eine E-Mail-Adresse am Geschäftspartner hinterlegen.')
    return
  }
  sendingXRechnung.value = true
  try {
    await invoiceService.sendXRechnung(invoice.value.id, { recipient })
    await loadInvoice()
  } catch (err) {
    const msg = err?.response?.data?.detail ?? err?.response?.data?.error ?? 'Fehler beim Versenden der XRechnung.'
    alert(msg)
  } finally {
    sendingXRechnung.value = false
  }
}

const handleDelete = async () => {
  if (!confirm(`Möchten Sie die Rechnung ${invoice.value.invoice_number} wirklich löschen?`)) {
    return
  }

  try {
    await invoiceService.delete(invoice.value.id)
    // Zurück zur Liste navigieren
    router.push('/invoices')
  } catch (error) {
    console.error('Fehler beim Löschen der Rechnung:', error)
    alert('Rechnung konnte nicht gelöscht werden')
  }
}

const handleCancel = async () => {
  cancelling.value = true
  try {
    const result = await invoiceService.cancel(invoice.value.id, cancelReason.value.trim())
    showCancelDialog.value = false
    cancelReason.value = ''
    toast.success(`Rechnung storniert. Gutschrift ${result.credit_note_number} erstellt.`)
    // Navigate to the new credit note
    router.push({ name: 'InvoiceDetail', params: { id: result.credit_note_id } })
  } catch (error) {
    console.error('Fehler beim Stornieren:', error)
    toast.error(error.response?.data?.detail || 'Rechnung konnte nicht storniert werden.')
  } finally {
    cancelling.value = false
  }
}

onMounted(() => {
  loadInvoice()
})

// Reload when navigating between invoices (same route, different ID)
watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    loadInvoice()
  }
})

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
/* Edit-Lock Banner */
.edit-lock-banner {
  padding: 0.75rem 1rem;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 0.375rem;
  color: #92400e;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  position: sticky;
  top: 0;
  z-index: 10;
  background: white;
  padding: 0.75rem 0 0.75rem;
}

.page-header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.back-link {
  display: inline-block;
  color: #3b82f6;
  text-decoration: none;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.back-link:hover {
  text-decoration: underline;
}

.page-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
}

.actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.versand-status {
  font-size: 0.8rem;
  color: #6b7280;
  text-align: right;
  padding-right: 0.25rem;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #6b7280;
}

.invoice-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.detail-value {
  font-size: 1rem;
  color: #111827;
}

.detail-value.strong {
  font-size: 1.25rem;
  font-weight: 700;
  color: #3b82f6;
}

.placeholder {
  text-align: center;
  color: #6b7280;
  padding: 2rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  width: fit-content;
}

.status-draft {
  background-color: #f3f4f6;
  color: #374151;
}

.status-sent {
  background-color: #dbeafe;
  color: #1e40af;
}

.status-paid {
  background-color: #d1fae5;
  color: #065f46;
}

.status-cancelled {
  background-color: #fee2e2;
  color: #991b1b;
}

.status-overdue {
  background-color: #fef3c7;
  color: #92400e;
}

.summary {
  margin-top: 2rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: 1rem;
}

.summary-row.total {
  border-top: 2px solid #d1d5db;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
}

.summary-row.allowance-row {
  color: #b91c1c;
  font-size: 0.95rem;
}

.summary-row.charge-row {
  color: #15803d;
  font-size: 0.95rem;
}

.summary-row.subtotal-adjusted-row {
  border-top: 1px dashed #d1d5db;
  padding-top: 0.5rem;
  font-weight: 600;
}

.negative {
  color: #b91c1c;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 1rem;
  }

  .actions {
    flex-wrap: wrap;
  }
}

.notes-content p {
  margin: 0.25rem 0;
}

.note-warning {
  color: #92400e;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
  padding: 0.5rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

/* Credit note type badge */
.type-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 0.5rem;
  vertical-align: middle;
}

.type-credit-note {
  background-color: #fce7f3;
  color: #9d174d;
}

/* Cross-link to related invoices */
.cross-link {
  color: #3b82f6;
  font-weight: 600;
  text-decoration: none;
}

.cross-link:hover {
  text-decoration: underline;
}

/* Cancel dialog */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content.cancel-dialog {
  background: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  max-width: 480px;
  width: 90%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.cancel-dialog h2 {
  margin: 0 0 0.75rem;
  font-size: 1.25rem;
  color: #991b1b;
}

.cancel-dialog p {
  margin: 0 0 1rem;
  color: #374151;
  line-height: 1.5;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 600;
  font-size: 0.875rem;
  color: #374151;
}

.cancel-reason-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  resize: vertical;
  font-family: inherit;
}

.cancel-reason-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>
