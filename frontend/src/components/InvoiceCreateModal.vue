<template>
  <BaseModal :is-open="true" @close="$emit('close')">
    <template #title>
      Neue Rechnung erstellen
    </template>

    <form @submit.prevent="handleSubmit" class="invoice-form">
      <!-- Firma auswählen (falls mehrere) -->
      <div v-if="companies.length > 1" class="form-group">
        <label for="company">Firma *</label>
        <BaseSelect
          id="company"
          v-model="formData.company"
          :options="companies"
          label-key="name"
          value-key="id"
          placeholder="Firma auswählen"
          :error="errors.company"
          required
        />
      </div>

      <!-- Kunde auswählen -->
      <div class="form-group">
        <label for="business_partner">Kunde *</label>
        <BaseSelect
          id="business_partner"
          v-model="formData.business_partner"
          :options="customers"
          label-key="name"
          value-key="id"
          placeholder="Kunde auswählen"
          :error="errors.business_partner"
          :loading="loadingCustomers"
          required
        />
      </div>

      <!-- Rechnungsdatum -->
      <div class="form-row">
        <div class="form-group">
          <BaseDatePicker
            id="issue_date"
            v-model="formData.issue_date"
            label="Rechnungsdatum"
            placeholder="Datum auswählen"
            :error="errors.issue_date"
            required
          />
        </div>

        <!-- Fälligkeitsdatum -->
        <div class="form-group">
          <BaseDatePicker
            id="due_date"
            v-model="formData.due_date"
            label="Fälligkeitsdatum"
            placeholder="Datum auswählen"
            :min-date="formData.issue_date"
            :error="errors.due_date"
            required
          />
        </div>
      </div>

      <!-- Referenzfelder (B2B) -->
      <div class="form-row">
        <div class="form-group">
          <label for="buyer_reference">Ihr Zeichen (optional)</label>
          <BaseInput
            id="buyer_reference"
            v-model="formData.buyer_reference"
            placeholder="z.B. PO-12345"
            :error="errors.buyer_reference"
          />
          <small class="form-hint">Kundenreferenz / Bestellnummer</small>
        </div>

        <div class="form-group">
          <label for="seller_reference">Unser Zeichen (optional)</label>
          <BaseInput
            id="seller_reference"
            v-model="formData.seller_reference"
            placeholder="z.B. PROJ-2026-ABC"
            :error="errors.seller_reference"
          />
          <small class="form-hint">Interne Referenz / Projektnummer</small>
        </div>
      </div>

      <!-- Rechnungspositionen -->
      <div class="invoice-lines-section">
        <div class="section-header">
          <h3>Rechnungspositionen</h3>
          <BaseButton
            type="button"
            variant="secondary"
            size="small"
            @click="addLine"
          >
            + Position hinzufügen
          </BaseButton>
        </div>

        <div
          v-for="(line, index) in formData.lines"
          :key="index"
          class="invoice-line"
        >
          <div class="line-header">
            <h4>Position {{ index + 1 }}</h4>
            <BaseButton
              v-if="formData.lines.length > 1"
              type="button"
              variant="danger"
              size="small"
              @click="removeLine(index)"
            >
              Entfernen
            </BaseButton>
          </div>

          <div class="form-row">
            <!-- Produkt -->
            <div class="form-group flex-2">
              <label :for="`product_${index}`">Produkt *</label>
              <BaseSelect
                :id="`product_${index}`"
                v-model="line.product"
                :options="products"
                label-key="name"
                value-key="id"
                placeholder="Produkt auswählen"
                :error="errors[`lines.${index}.product`]"
                :loading="loadingProducts"
                @change="handleProductChange(index)"
                required
              />
            </div>

            <!-- Menge -->
            <div class="form-group">
              <label :for="`quantity_${index}`">Menge *</label>
              <BaseInput
                :id="`quantity_${index}`"
                v-model.number="line.quantity"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="1.00"
                :error="errors[`lines.${index}.quantity`]"
                @input="calculateLineTotal(index)"
                required
              />
            </div>
          </div>

          <div class="form-row">
            <!-- Einzelpreis Netto -->
            <div class="form-group">
              <label :for="`unit_price_net_${index}`">Einzelpreis (Netto) *</label>
              <BaseInput
                :id="`unit_price_net_${index}`"
                v-model.number="line.unit_price_net"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                :error="errors[`lines.${index}.unit_price_net`]"
                @input="calculateLineTotal(index)"
                required
              />
            </div>

            <!-- MwSt.-Satz -->
            <div class="form-group">
              <label :for="`vat_rate_${index}`">MwSt.-Satz *</label>
              <BaseSelect
                :id="`vat_rate_${index}`"
                v-model.number="line.vat_rate"
                :options="vatRateOptions"
                placeholder="MwSt. auswählen"
                :error="errors[`lines.${index}.vat_rate`]"
                @change="calculateLineTotal(index)"
                required
              />
            </div>

            <!-- Gesamt (berechnet) -->
            <div class="form-group">
              <span class="form-label">Gesamt (Brutto)</span>
              <div class="calculated-value">
                {{ formatCurrency(line.line_total_gross || 0) }}
              </div>
            </div>
          </div>

          <!-- Beschreibung (optional) -->
          <div class="form-group">
            <label :for="`description_${index}`">Beschreibung (optional)</label>
            <BaseInput
              :id="`description_${index}`"
              v-model="line.description"
              placeholder="Zusätzliche Beschreibung"
            />
          </div>

          <!-- Positionsrabatt (EN16931 SpecifiedTradeAllowanceCharge) -->
          <div class="form-row">
            <div class="form-group">
              <label :for="`discount_${index}`">Rabatt %</label>
              <BaseInput
                :id="`discount_${index}`"
                v-model.number="line.discount_percentage"
                type="number"
                step="0.1"
                min="0"
                max="100"
                placeholder="0"
                @input="calculateLineTotal(index)"
              />
            </div>
            <div class="form-group flex-2" v-if="line.discount_percentage > 0">
              <label :for="`discount_reason_${index}`">Rabattgrund</label>
              <BaseInput
                :id="`discount_reason_${index}`"
                v-model="line.discount_reason"
                placeholder="z.B. Mengenrabatt"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Rechnungsrabatte / Zuschläge (Kopfebene EN16931 BG-20/BG-21) -->
      <div class="allowance-charge-section">
        <div class="section-header">
          <h3 class="section-title">Rabatte &amp; Zuschläge (Rechnungsebene)</h3>
          <BaseButton type="button" variant="secondary" size="sm" @click="addAllowanceCharge">
            + Hinzufügen
          </BaseButton>
        </div>
        <p v-if="formData.allowance_charges.length === 0" class="ac-empty">
          Keine rechnungsweiten Rabatte oder Zuschläge
        </p>
        <div
          v-for="(ac, acIdx) in formData.allowance_charges"
          :key="acIdx"
          class="ac-row"
        >
          <div class="form-row">
            <div class="form-group">
              <label>Typ</label>
              <select v-model="ac.is_charge" class="base-select">
                <option :value="false">Rabatt (–)</option>
                <option :value="true">Zuschlag (+)</option>
              </select>
            </div>
            <div class="form-group">
              <label>Betrag (Netto)</label>
              <BaseInput
                v-model.number="ac.actual_amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
              />
            </div>
            <div class="form-group flex-2">
              <label>Grund</label>
              <BaseInput
                v-model="ac.reason"
                placeholder="z.B. Skonto, Versandkosten"
              />
            </div>
            <div class="form-group">
              <label>&nbsp;</label>
              <BaseButton
                type="button"
                variant="danger"
                size="sm"
                @click="removeAllowanceCharge(acIdx)"
              >
                Entfernen
              </BaseButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Zusammenfassung -->
      <div class="invoice-summary">
        <div class="summary-row">
          <span>Netto:</span>
          <span>{{ formatCurrency(calculatedTotals.net) }}</span>
        </div>
        <div class="summary-row">
          <span>MwSt.:</span>
          <span>{{ formatCurrency(calculatedTotals.vat) }}</span>
        </div>
        <div class="summary-row total">
          <span>Gesamt (Brutto):</span>
          <span>{{ formatCurrency(calculatedTotals.gross) }}</span>
        </div>
      </div>

      <!-- Notizen (optional) -->
      <div class="form-group">
        <BaseTextarea
          id="notes"
          v-model="formData.notes"
          label="Notizen (optional)"
          :rows="3"
          placeholder="Interne Notizen"
        />
      </div>

      <!-- Fehlermeldung -->
      <BaseAlert v-if="submitError" variant="danger" @close="submitError = null">
        {{ submitError }}
      </BaseAlert>
    </form>

    <template #footer>
      <div class="modal-actions">
        <BaseButton
          type="button"
          variant="secondary"
          @click="$emit('close')"
          :disabled="loading"
        >
          Abbrechen
        </BaseButton>
        <BaseButton
          type="submit"
          variant="primary"
          @click="handleSubmit"
          :loading="loading"
          :disabled="!isFormValid"
        >
          Rechnung erstellen
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { invoiceService } from '@/api/services/invoiceService'
import { businessPartnerService } from '@/api/services/businessPartnerService'
import { productService } from '@/api/services/productService'
import { companyService } from '@/api/services/companyService'
import BaseModal from './BaseModal.vue'
import BaseInput from './BaseInput.vue'
import BaseSelect from './BaseSelect.vue'
import BaseButton from './BaseButton.vue'
import BaseAlert from './BaseAlert.vue'
import BaseTextarea from './BaseTextarea.vue'
import BaseDatePicker from './BaseDatePicker.vue'

const emit = defineEmits(['close', 'created'])

// State
const loading = ref(false)
const loadingCustomers = ref(false)
const loadingProducts = ref(false)
const submitError = ref(null)

const customers = ref([])
const products = ref([])
const companies = ref([])

const formData = reactive({
  company: null,
  business_partner: null,
  issue_date: new Date().toISOString().split('T')[0],
  due_date: calculateDefaultDueDate(),
  buyer_reference: '',
  seller_reference: '',
  notes: '',
  lines: [
    createEmptyLine()
  ],
  allowance_charges: []
})

const errors = reactive({})

// MwSt.-Sätze (Standard für Deutschland)
const vatRateOptions = [
  { label: '19% (Standard)', value: 19 },
  { label: '7% (Ermäßigt)', value: 7 },
  { label: '0% (Befreit)', value: 0 }
]

// Berechnete Werte
const calculatedTotals = computed(() => {
  const totals = { net: 0, vat: 0, gross: 0 }

  formData.lines.forEach(line => {
    if (line.quantity && line.unit_price_net && line.vat_rate !== null) {
      const baseNet = line.quantity * line.unit_price_net
      const discount = baseNet * ((line.discount_percentage || 0) / 100)
      const net = baseNet - discount
      const vat = net * (line.vat_rate / 100)
      totals.net += net
      totals.vat += vat
      totals.gross += net + vat
    }
  })

  // Kopfebene Rabatte/Zuschläge
  formData.allowance_charges.forEach(ac => {
    const amount = ac.actual_amount || 0
    const vat = amount * ((ac.tax_rate || 0) / 100)
    if (ac.is_charge) {
      totals.net += amount
      totals.vat += vat
      totals.gross += amount + vat
    } else {
      totals.net -= amount
      totals.vat -= vat
      totals.gross -= amount + vat
    }
  })

  return totals
})

const isFormValid = computed(() => {
  return (
    formData.business_partner &&
    formData.issue_date &&
    formData.due_date &&
    formData.lines.length > 0 &&
    formData.lines.every(line =>
      line.product &&
      line.quantity > 0 &&
      line.unit_price_net >= 0 &&
      line.vat_rate !== null
    )
  )
})

// Methoden
function createEmptyLine() {
  return {
    product: null,
    quantity: 1,
    unit_price_net: 0,
    vat_rate: 19,
    description: '',
    line_total_gross: 0,
    discount_percentage: 0,
    discount_reason: ''
  }
}

function calculateDefaultDueDate() {
  const date = new Date()
  date.setDate(date.getDate() + 14) // 14 Tage Zahlungsziel
  return date.toISOString().split('T')[0]
}

function addLine() {
  formData.lines.push(createEmptyLine())
}

function removeLine(index) {
  formData.lines.splice(index, 1)
}

function handleProductChange(index) {
  const line = formData.lines[index]
  // Loser Vergleich nötig: BaseSelect emittiert String (DOM), p.id ist Number (API)
  const product = products.value.find(p => p.id == line.product)

  if (product) {
    line.unit_price_net = parseFloat(product.current_price) || 0
    line.vat_rate = parseFloat(product.default_tax_rate) || 19
    line.description = product.description || ''
    calculateLineTotal(index)
  }
}

function calculateLineTotal(index) {
  const line = formData.lines[index]

  if (line.quantity && line.unit_price_net !== null && line.vat_rate !== null) {
    const baseNet = line.quantity * line.unit_price_net
    const discount = baseNet * ((line.discount_percentage || 0) / 100)
    const net = baseNet - discount
    const vat = net * (line.vat_rate / 100)
    line.line_total_gross = net + vat
  } else {
    line.line_total_gross = 0
  }
}

function createEmptyAllowanceCharge() {
  return { is_charge: false, actual_amount: 0, reason: '', reason_code: '' }
}

function addAllowanceCharge() {
  formData.allowance_charges.push(createEmptyAllowanceCharge())
}

function removeAllowanceCharge(index) {
  formData.allowance_charges.splice(index, 1)
}

function formatCurrency(value) {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR'
  }).format(value)
}

async function loadData() {
  try {
    loadingCustomers.value = true
    loadingProducts.value = true

    const [customersResponse, productsResponse, companiesResponse] = await Promise.all([
      businessPartnerService.getAll({ page_size: 1000 }),
      productService.getAll({ page_size: 1000 }),
      companyService.getAll()
    ])

    // Prüfe Response-Struktur und extrahiere Daten korrekt
    customers.value = Array.isArray(customersResponse)
      ? customersResponse
      : (customersResponse.results || [])

    products.value = Array.isArray(productsResponse)
      ? productsResponse
      : (productsResponse.results || [])

    companies.value = Array.isArray(companiesResponse)
      ? companiesResponse
      : (companiesResponse.results || [])

    if (import.meta.env.DEV) {
      console.log('Geladene Daten:', {
        customers: customers.value.length,
        products: products.value.length,
        companies: companies.value.length
      })
    }

    // Wenn nur eine Firma vorhanden ist, automatisch auswählen
    if (companies.value.length === 1) {
      formData.company = companies.value[0].id
    }

    // Warnung bei leeren Daten
    if (customers.value.length === 0) {
      console.warn('Keine Kunden gefunden!')
    }
    if (products.value.length === 0) {
      console.warn('Keine Produkte gefunden!')
    }
  } catch (error) {
    console.error('Fehler beim Laden der Daten:', error)
    submitError.value = 'Fehler beim Laden der Formulardaten'
  } finally {
    loadingCustomers.value = false
    loadingProducts.value = false
  }
}

async function handleSubmit() {
  // Validierung zurücksetzen
  Object.keys(errors).forEach(key => delete errors[key])
  submitError.value = null

  if (!isFormValid.value) {
    submitError.value = 'Bitte füllen Sie alle Pflichtfelder aus'
    return
  }

  loading.value = true

  try {
    // Daten für API vorbereiten
    const invoiceData = {
      company: formData.company || companies.value[0]?.id,
      business_partner: formData.business_partner,
      issue_date: formData.issue_date,
      due_date: formData.due_date,
      buyer_reference: formData.buyer_reference || '',
      seller_reference: formData.seller_reference || '',
      notes: formData.notes,
    }

    const created = await invoiceService.create(invoiceData)

    // Positionen separat anlegen (Serializer unterstützt kein nested write)
    const linePromises = formData.lines
      .filter(line => line.product && line.quantity > 0)
      .map(line => invoiceService.createLine(created.id, {
        invoice: created.id,
        product: line.product,
        quantity: line.quantity,
        unit_price_net: line.unit_price_net,
        vat_rate: line.vat_rate,
        description: line.description || '',
        discount_percentage: line.discount_percentage || 0,
        discount_reason: line.discount_reason || ''
      }))
    await Promise.all(linePromises)

    // Kopfebene Rabatte/Zuschläge anlegen
    const acPromises = formData.allowance_charges
      .filter(ac => ac.actual_amount > 0)
      .map(ac => invoiceService.createAllowanceCharge({
        invoice: created.id,
        is_charge: ac.is_charge,
        actual_amount: ac.actual_amount,
        reason: ac.reason || (ac.is_charge ? 'Zuschlag' : 'Rabatt'),
        reason_code: ac.reason_code || '',
        tax_rate: ac.tax_rate,
        sort_order: 0
      }))
    await Promise.all(acPromises)

    emit('created', created)
    emit('close')
  } catch (error) {
    console.error('Fehler beim Erstellen der Rechnung:', error)

    if (error.response?.data) {
      // Validierungsfehler vom Backend
      const serverErrors = error.response.data

      // Allgemeine Fehlermeldung
      if (serverErrors.detail) {
        submitError.value = serverErrors.detail
      } else if (serverErrors.non_field_errors) {
        submitError.value = serverErrors.non_field_errors.join(', ')
      } else {
        // Feldspezifische Fehler
        Object.keys(serverErrors).forEach(field => {
          errors[field] = Array.isArray(serverErrors[field])
            ? serverErrors[field].join(', ')
            : serverErrors[field]
        })
        submitError.value = 'Bitte korrigieren Sie die markierten Fehler'
      }
    } else {
      submitError.value = 'Ein unerwarteter Fehler ist aufgetreten'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.invoice-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label,
.form-group .form-label {
  font-weight: 500;
  color: #374151;
}

.form-hint {
  color: #6b7280;
  font-size: 0.875rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-row .flex-2 {
  grid-column: span 2;
}

.invoice-lines-section {
  border-top: 2px solid #e5e7eb;
  padding-top: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.invoice-line {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1rem;
}

.line-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.line-header h4 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: #1f2937;
}

.calculated-value {
  padding: 0.5rem 0.75rem;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-weight: 600;
  color: #1f2937;
}

.invoice-summary {
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-top: 1rem;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: 1rem;
}

.summary-row.total {
  border-top: 2px solid #9ca3af;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1f2937;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.allowance-charge-section {
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
}

.allowance-charge-section .section-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
  color: #374151;
}

.ac-empty {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0.5rem 0 0;
}

.ac-row {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e5e7eb;
}

.base-select {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  background: #fff;
  font-size: 0.875rem;
  color: #1f2937;
  cursor: pointer;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .form-row .flex-2 {
    grid-column: span 1;
  }
}
</style>
