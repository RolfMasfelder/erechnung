<template>
  <div class="invoice-detail">
    <div class="page-header">
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
          variant="primary"
          :loading="generatingPdf"
          @click="generatePDF"
        >
          ⚡ PDF generieren
        </BaseButton>
        <BaseButton variant="secondary" :disabled="generatingPdf" @click="downloadPDF">
          📥 PDF herunterladen
        </BaseButton>
        <BaseButton variant="secondary" @click="downloadXML">
          📥 XML herunterladen
        </BaseButton>
        <BaseButton
          v-if="invoice?.business_partner_details?.partner_type === 'GOVERNMENT'"
          variant="secondary"
          :loading="generatingXml"
          @click="generateXRechnung"
        >
          🏛️ XRechnung XML erzeugen
        </BaseButton>
        <BaseButton
          v-if="invoice?.status?.toUpperCase() === 'DRAFT'"
          variant="success"
          :loading="markingAsSent"
          @click="handleMarkAsSent"
        >
          ✉️ Als versendet markieren
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
    </div>

    <div v-if="loading" class="loading">
      Lädt Rechnung...
    </div>

    <div v-else-if="invoice" class="invoice-content">
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
import { invoiceService } from '@/api/services/invoiceService'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const loading = ref(false)
const generatingPdf = ref(false)
const generatingXml = ref(false)
const markingAsSent = ref(false)
const invoice = ref(null)
const showEditModal = ref(false)
const showCancelDialog = ref(false)
const cancelReason = ref('')
const cancelling = ref(false)

// Cancel button visible only for SENT or PAID invoices (not credit notes)
const canCancel = computed(() => {
  if (!invoice.value) return false
  const s = invoice.value.status?.toUpperCase()
  return (s === 'SENT' || s === 'PAID') && invoice.value.invoice_type !== 'CREDIT_NOTE'
})

// Prüfen ob mindestens eine Position einen Rabatt hat
const hasDiscounts = computed(() => {
  if (!invoice.value?.lines) return false
  return invoice.value.lines.some(
    (line) => parseFloat(line.discount_percentage) > 0 || parseFloat(line.discount_amount) > 0
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
  headerAllowances.value.reduce((sum, ac) => sum + parseFloat(ac.actual_amount), 0),
)

const totalHeaderCharges = computed(() =>
  headerCharges.value.reduce((sum, ac) => sum + parseFloat(ac.actual_amount), 0),
)

// Zeilensumme (Netto, vor Rechnungsebene-Korrekturen)
// = invoice.subtotal (= Steuerbasis) + Allowances - Charges
const linesSubtotal = computed(() => {
  return (
    (parseFloat(invoice.value?.subtotal) || 0) +
    totalHeaderAllowances.value -
    totalHeaderCharges.value
  )
})

// Nach Modell-Fix: invoice.subtotal = Steuerbasis (bereits korrekt),
// invoice.tax_amount und invoice.total_amount werden vom Modell korrekt berechnet.
// Die folgenden Werte kommen direkt aus dem Modell (kein Frontend-Recompute nötig).
const netAfterAdjustments = computed(() => parseFloat(invoice.value?.subtotal) || 0)
const correctedTaxAmount = computed(() => parseFloat(invoice.value?.tax_amount) || 0)
const correctedGrandTotal = computed(() => parseFloat(invoice.value?.total_amount) || 0)

const lineColumns = computed(() => {
  const cols = [
    { key: 'id', label: 'Pos.' },
    { key: 'product_name', label: 'Produkt' },
    { key: 'description', label: 'Beschreibung' },
    { key: 'quantity', label: 'Menge' },
    { key: 'unit_price_net', label: 'Einzelpreis (Netto)' },
  ]
  if (hasDiscounts.value) {
    cols.push({ key: 'discount_percentage', label: 'Rabatt %' })
    cols.push({ key: 'discount_amount', label: 'Rabattbetrag' })
  }
  cols.push({ key: 'vat_rate', label: 'MwSt.' })
  cols.push({ key: 'line_total', label: 'Gesamt (Brutto)' })
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

const handleMarkAsSent = async () => {
  if (!confirm('Rechnung als versendet markieren? Danach kann sie nicht mehr bearbeitet werden (GoBD).')) return
  markingAsSent.value = true
  try {
    await invoiceService.markAsSent(route.params.id)
    toast.success('Rechnung als versendet markiert und gesperrt.')
    await loadInvoice()
  } catch (error) {
    const detail = error.response?.data?.detail ?? 'Fehler beim Statuswechsel'
    toast.error(detail)
  } finally {
    markingAsSent.value = false
  }
}

const generatePDF = async () => {
  generatingPdf.value = true
  try {
    const result = await invoiceService.generatePDF(route.params.id)
    if (result.xml_valid) {
      toast.success('PDF/A-3 erfolgreich generiert')
    } else {
      toast.warning('PDF generiert, aber XML-Validierung mit Warnungen')
    }
    await loadInvoice()
  } catch (error) {
    console.error('Failed to generate PDF:', error)
    toast.error('Fehler bei der PDF-Generierung')
  } finally {
    generatingPdf.value = false
  }
}

const downloadPDF = async () => {
  try {
    const blob = await invoiceService.downloadPDF(route.params.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `invoice-${invoice.value.invoice_number}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    toast.success('PDF erfolgreich heruntergeladen')
  } catch (error) {
    console.error('Failed to download PDF:', error)
    toast.error('Fehler beim Herunterladen des PDFs')
  }
}

const downloadXML = async () => {
  try {
    const blob = await invoiceService.downloadXML(route.params.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `invoice-${invoice.value.invoice_number}.xml`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('Failed to download XML:', error)
  }
}

const generateXRechnung = async () => {
  generatingXml.value = true
  try {
    await invoiceService.generateXml(route.params.id)
    toast.success('XRechnung XML erfolgreich erzeugt')
    // Auto-download the generated XML
    await downloadXML()
  } catch (error) {
    console.error('Failed to generate XRechnung XML:', error)
    const detail = error.response?.data?.detail ?? 'Fehler beim Erzeugen der XRechnung'
    toast.error(detail)
  } finally {
    generatingXml.value = false
  }
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
  const num = parseFloat(value)
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
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
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
