<template>
  <div class="invoice-preview-page">
    <!-- Preview Banner -->
    <div class="preview-banner">
      <span class="preview-banner-icon">👁</span>
      Vorschau – Diese Ansicht entspricht dem PDF-Ausdruck
      <router-link :to="{ name: 'InvoiceDetail', params: { id: route.params.id } }" class="preview-back-link">
        ← Zurück zur Rechnung
      </router-link>
    </div>

    <div v-if="loading" class="preview-loading">Lade Rechnungsvorschau…</div>

    <div v-else-if="error" class="preview-error">
      Fehler beim Laden der Rechnung: {{ error }}
    </div>

    <div v-else-if="invoice" class="invoice-document">
      <!-- Sender / Company Header -->
      <div class="invoice-header">
        <div class="company-block">
          <!-- Logo wenn vorhanden -->
          <img
            v-if="companyLogo"
            :src="companyLogo"
            alt="Firmenlogo"
            class="logo"
          />
          <!-- Fallback: Firmenname als Text -->
          <div
            v-else
            class="company-name-text"
            style="font-size:14pt; font-weight:bold;"
          >{{ companyName || '–' }}</div>

          <div class="company-address">
            <div v-if="company.address_line1">{{ company.address_line1 }}</div>
            <div v-if="company.postal_code || company.city">
              {{ company.postal_code }} {{ company.city }}
            </div>
            <div v-if="company.country">{{ company.country }}</div>
          </div>
        </div>

        <div class="invoice-meta">
          <h1 class="invoice-title">Rechnung</h1>
          <table class="invoice-meta-table">
            <tbody>
              <tr>
                <td>Rechnungsnummer:</td>
                <td><strong>{{ invoice.invoice_number }}</strong></td>
              </tr>
              <tr>
                <td>Rechnungsdatum:</td>
                <td>{{ formatDate(invoice.issue_date) }}</td>
              </tr>
              <tr v-if="invoice.due_date">
                <td>Fälligkeitsdatum:</td>
                <td>{{ formatDate(invoice.due_date) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Empfänger -->
      <div v-if="invoice.recipient_name" class="recipient-block">
        <div class="recipient-label">An:</div>
        <div class="recipient-name">{{ invoice.recipient_name }}</div>
        <div v-if="invoice.recipient_address">{{ invoice.recipient_address }}</div>
      </div>

      <!-- Rechnungspositionen -->
      <table class="invoice-items-table" v-if="invoice.items?.length">
        <thead>
          <tr>
            <th>Beschreibung</th>
            <th class="text-right">Menge</th>
            <th class="text-right">Einzelpreis</th>
            <th class="text-right">Gesamt</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in invoice.items" :key="item.id">
            <td>{{ item.description || item.product_name }}</td>
            <td class="text-right">{{ item.quantity }}</td>
            <td class="text-right">{{ formatCurrency(item.unit_price_net) }}</td>
            <td class="text-right">{{ formatCurrency(item.line_total) }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="total-row">
            <td colspan="3">Nettobetrag</td>
            <td class="text-right">{{ formatCurrency(invoice.net_total) }}</td>
          </tr>
          <tr>
            <td colspan="3">MwSt. ({{ invoice.tax_rate ? invoice.tax_rate + '%' : '' }})</td>
            <td class="text-right">{{ formatCurrency(invoice.tax_amount) }}</td>
          </tr>
          <tr class="grand-total-row">
            <td colspan="3"><strong>Gesamtbetrag</strong></td>
            <td class="text-right"><strong>{{ formatCurrency(invoice.total_amount) }}</strong></td>
          </tr>
        </tfoot>
      </table>

      <!-- Fußnote -->
      <div v-if="company.iban || company.bank_name" class="invoice-footer">
        <div v-if="company.bank_name">Bank: {{ company.bank_name }}</div>
        <div v-if="company.iban">IBAN: {{ company.iban }}</div>
        <div v-if="company.bic">BIC: {{ company.bic }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { invoiceService } from '@/api/services/invoiceService'

const route = useRoute()
const invoice = ref(null)
const loading = ref(true)
const error = ref(null)

const company = computed(() => invoice.value?.company_details || {})
const companyName = computed(() => company.value?.name || '')
const companyLogo = computed(() => company.value?.logo || null)

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const formatCurrency = (val) => {
  if (val === null || val === undefined) return '–'
  return Number(val).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })
}

onMounted(async () => {
  try {
    invoice.value = await invoiceService.getById(route.params.id)
  } catch (e) {
    error.value = e.message || 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.invoice-preview-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 1rem;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  color: #111;
}

/* Preview Banner */
.preview-banner {
  background: #fef9c3;
  border: 1px solid #fde047;
  border-radius: 0.375rem;
  padding: 0.5rem 1rem;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #713f12;
}
.preview-banner-icon {
  font-size: 1rem;
}
.preview-back-link {
  margin-left: auto;
  color: #1d4ed8;
  text-decoration: none;
}
.preview-back-link:hover {
  text-decoration: underline;
}

.preview-loading,
.preview-error {
  padding: 2rem;
  text-align: center;
  color: #6b7280;
}
.preview-error {
  color: #dc2626;
}

/* Invoice Document */
.invoice-document {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 2.5rem;
}

.invoice-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  gap: 2rem;
}

.company-block {
  flex: 1;
}

.logo {
  max-height: 60px;
  max-width: 200px;
  object-fit: contain;
  margin-bottom: 0.5rem;
  display: block;
}

.company-address {
  font-size: 0.875rem;
  color: #4b5563;
  margin-top: 0.5rem;
  line-height: 1.5;
}

.invoice-meta {
  text-align: right;
}

.invoice-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #111827;
}

.invoice-meta-table {
  font-size: 0.9rem;
  border-collapse: collapse;
}
.invoice-meta-table td {
  padding: 0.2rem 0.5rem;
}
.invoice-meta-table td:first-child {
  color: #6b7280;
  text-align: right;
}

.recipient-block {
  margin-bottom: 2rem;
  font-size: 0.95rem;
}
.recipient-label {
  font-size: 0.8rem;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}
.recipient-name {
  font-weight: 600;
}

.invoice-items-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}
.invoice-items-table th {
  border-bottom: 2px solid #e5e7eb;
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
}
.invoice-items-table td {
  border-bottom: 1px solid #f3f4f6;
  padding: 0.5rem 0.75rem;
}
.text-right {
  text-align: right;
}

.total-row td,
.grand-total-row td {
  padding-top: 0.75rem;
}
.grand-total-row td {
  font-size: 1.05rem;
  border-top: 2px solid #111827;
}

.invoice-footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
  font-size: 0.8rem;
  color: #6b7280;
}
</style>
