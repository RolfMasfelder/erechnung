<template>
  <BaseModal :is-open="true" @close="$emit('close')">
    <template #title>
      Rechnung bearbeiten
    </template>

    <div v-if="loading" class="loading-state">
      <p>Lädt Rechnung...</p>
    </div>

    <form v-else @submit.prevent="handleSubmit" class="invoice-form">
      <!-- Status (nur anzeigen, falls bereits versendet) -->
      <div v-if="formData.status !== 'draft'" class="form-group">
        <span class="form-label">Status</span>
        <div class="readonly-field">
          <span :class="['status-badge', `status-${formData.status}`]">
            {{ getStatusLabel(formData.status) }}
          </span>
          <small class="form-hint">
            Nur Entwürfe können vollständig bearbeitet werden
          </small>
        </div>
      </div>

      <!-- Firma (readonly wenn nicht Entwurf) -->
      <div v-if="companies.length > 1" class="form-group">
        <label for="company">Firma</label>
        <BaseSelect
          v-if="formData.status === 'draft'"
          id="company"
          v-model="formData.company"
          :options="companies"
          label-key="name"
          value-key="id"
          :error="errors.company"
          required
        />
        <div v-else class="readonly-field">
          {{ getCompanyName(formData.company) }}
        </div>
      </div>

      <!-- Kunde (readonly wenn nicht Entwurf) -->
      <div class="form-group">
        <label for="business_partner">Kunde *</label>
        <BaseSelect
          v-if="formData.status === 'draft'"
          id="business_partner"
          v-model="formData.business_partner"
          :options="customers"
          label-key="name"
          value-key="id"
          :error="errors.business_partner"
          :loading="loadingCustomers"
          required
        />
        <div v-else class="readonly-field">
          {{ getCustomerName(formData.business_partner) }}
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

      <!-- Datumfelder -->
      <div class="form-row">
        <div class="form-group">
          <BaseDatePicker
            id="issue_date"
            v-model="formData.issue_date"
            label="Rechnungsdatum"
            placeholder="Datum auswählen"
            :disabled="formData.status !== 'draft'"
            :error="errors.issue_date"
            required
          />
        </div>

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

      <!-- Rechnungspositionen (nur bei Entwurf editierbar) -->
      <div class="invoice-lines-section">
        <div class="section-header">
          <h3>Rechnungspositionen</h3>
          <BaseButton
            v-if="formData.status === 'draft'"
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
          :key="line.id || `new-${index}`"
          class="invoice-line"
        >
          <div class="line-header">
            <h4>Position {{ index + 1 }}</h4>
            <BaseButton
              v-if="formData.status === 'draft' && formData.lines.length > 1"
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
                v-if="formData.status === 'draft'"
                :id="`product_${index}`"
                v-model="line.product"
                :options="products"
                label-key="name"
                value-key="id"
                :error="errors[`lines.${index}.product`]"
                :loading="loadingProducts"
                @change="handleProductChange(index)"
                required
              />
              <div v-else class="readonly-field">
                {{ getProductName(line.product) }}
              </div>
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
                :readonly="formData.status !== 'draft'"
                :error="errors[`lines.${index}.quantity`]"
                @input="calculateLineTotal(index)"
                required
              />
            </div>
          </div>

          <div class="form-row">
            <!-- Einzelpreis -->
            <div class="form-group">
              <label :for="`unit_price_net_${index}`">Einzelpreis (Netto) *</label>
              <BaseInput
                :id="`unit_price_net_${index}`"
                v-model.number="line.unit_price_net"
                type="number"
                step="0.01"
                min="0"
                :readonly="formData.status !== 'draft'"
                :error="errors[`lines.${index}.unit_price_net`]"
                @input="calculateLineTotal(index)"
                required
              />
            </div>

            <!-- MwSt.-Satz -->
            <div class="form-group">
              <label :for="`vat_rate_${index}`">MwSt.-Satz *</label>
              <BaseSelect
                v-if="formData.status === 'draft'"
                :id="`vat_rate_${index}`"
                v-model.number="line.vat_rate"
                :options="vatRateOptions"
                :error="errors[`lines.${index}.vat_rate`]"
                @change="calculateLineTotal(index)"
                required
              />
              <div v-else class="readonly-field">
                {{ line.vat_rate }}%
              </div>
            </div>

            <!-- Gesamt -->
            <div class="form-group">
              <span class="form-label">Gesamt (Brutto)</span>
              <div class="calculated-value">
                {{ formatCurrency(line.line_total_gross || 0) }}
              </div>
            </div>
          </div>

          <!-- Beschreibung -->
          <div class="form-group">
            <label :for="`description_${index}`">Beschreibung</label>
            <BaseInput
              :id="`description_${index}`"
              v-model="line.description"
              :readonly="formData.status !== 'draft'"
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
                :readonly="formData.status !== 'draft'"
                @input="calculateLineTotal(index)"
              />
            </div>
            <div class="form-group flex-2" v-if="line.discount_percentage > 0">
              <label :for="`discount_reason_${index}`">Rabattgrund</label>
              <BaseInput
                :id="`discount_reason_${index}`"
                v-model="line.discount_reason"
                placeholder="z.B. Mengenrabatt"
                :readonly="formData.status !== 'draft'"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Rechnungsrabatte / Zuschläge (Kopfebene EN16931 BG-20/BG-21) -->
      <div class="allowance-charge-section">
        <div class="section-header">
          <h3 class="section-title">Rabatte &amp; Zuschläge (Rechnungsebene)</h3>
          <BaseButton
            v-if="formData.status === 'draft'"
            type="button"
            variant="secondary"
            size="sm"
            @click="addAllowanceCharge"
          >
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
              <select v-model="ac.is_charge" class="base-select" :disabled="formData.status !== 'draft'">
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
                :readonly="formData.status !== 'draft'"
              />
            </div>
            <div class="form-group flex-2">
              <label>Grund</label>
              <BaseInput
                v-model="ac.reason"
                placeholder="z.B. Skonto, Versandkosten"
                :readonly="formData.status !== 'draft'"
              />
            </div>
            <div class="form-group" v-if="formData.status === 'draft'">
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

      <!-- Notizen -->
      <div class="form-group">
        <BaseTextarea
          id="notes"
          v-model="formData.notes"
          label="Notizen"
          :rows="3"
          placeholder="Interne Notizen zur Rechnung"
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
          :disabled="saving"
        >
          Abbrechen
        </BaseButton>
        <BaseButton
          type="submit"
          variant="primary"
          @click="handleSubmit"
          :loading="saving"
          :disabled="!isFormValid"
        >
          Änderungen speichern
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

const props = defineProps({
  invoiceId: {
    type: [Number, String],
    required: true
  }
})

const emit = defineEmits(['close', 'updated'])

// State
const loading = ref(true)
const saving = ref(false)
const loadingCustomers = ref(false)
const loadingProducts = ref(false)
const submitError = ref(null)
const originalAcIds = ref([])
const originalLineIds = ref([])

const customers = ref([])
const products = ref([])
const companies = ref([])

const formData = reactive({
  company: null,
  business_partner: null,
  issue_date: '',
  due_date: '',
  buyer_reference: '',
  seller_reference: '',
  status: 'draft',
  notes: '',
  lines: [],
  allowance_charges: []
})

const errors = reactive({})

const vatRateOptions = [
  { label: '19% (Standard)', value: 19 },
  { label: '7% (Ermäßigt)', value: 7 },
  { label: '0% (Befreit)', value: 0 }
]

// Berechnete Werte
const calculatedTotals = computed(() => {
  const totals = { net: 0, vat: 0, gross: 0 }

  formData.lines.forEach(line => {
    if (line.quantity && line.unit_price_net !== null && line.vat_rate !== null) {
      const baseNet = line.quantity * line.unit_price_net
      const discount = baseNet * ((line.discount_percentage || 0) / 100)
      const net = baseNet - discount
      const vat = net * (line.vat_rate / 100)
      totals.net += net
      totals.vat += vat
      totals.gross += net + vat
    }
  })

  // Kopfebene Rabatte/Zuschläge: proportionale Verteilung auf MwSt.-Gruppen
  // (gleicher Algorithmus wie der XML-Generator – BR-S-08 / BR-CO-5)
  const acCharges = (formData.allowance_charges || []).filter(ac => ac.is_charge)
  const acAllowances = (formData.allowance_charges || []).filter(ac => !ac.is_charge)
  const chargesTotal = acCharges.reduce((s, ac) => s + (ac.actual_amount || 0), 0)
  const allowancesTotal = acAllowances.reduce((s, ac) => s + (ac.actual_amount || 0), 0)
  const netAdjustment = chargesTotal - allowancesTotal  // positiv = Zuschlag

  if (netAdjustment !== 0) {
    // Nettosumme aller Positionen als Basis für proportionale MwSt.-Verteilung
    const totalLineNet = totals.net
    // VAT-Gruppen aus den Positionen aufbauen
    const vatGroups = {}
    formData.lines.forEach(line => {
      if (line.quantity && line.unit_price_net !== null && line.vat_rate !== null) {
        const baseNet = line.quantity * line.unit_price_net
        const discount = baseNet * ((line.discount_percentage || 0) / 100)
        const lineNet = baseNet - discount
        const rate = line.vat_rate
        vatGroups[rate] = (vatGroups[rate] || 0) + lineNet
      }
    })
    // Proportionale MwSt.-Korrektur
    let vatAdjustment = 0
    Object.entries(vatGroups).forEach(([rate, groupNet]) => {
      const share = totalLineNet > 0 ? groupNet / totalLineNet : 0
      vatAdjustment += netAdjustment * share * (parseFloat(rate) / 100)
    })
    totals.net += netAdjustment
    totals.vat += vatAdjustment
    totals.gross += netAdjustment + vatAdjustment
  } else {
    totals.net += netAdjustment
    totals.gross += netAdjustment
  }

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
    if (!line.description) {
      line.description = product.description || ''
    }
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

function getStatusLabel(status) {
  const labels = {
    'draft': 'Entwurf',
    'sent': 'Versendet',
    'paid': 'Bezahlt',
    'cancelled': 'Storniert',
    'overdue': 'Überfällig'
  }
  return labels[status] || status
}

function getCompanyName(id) {
  return companies.value.find(c => c.id == id)?.name || ''
}

function getCustomerName(id) {
  return customers.value.find(c => c.id == id)?.name || ''
}

function getProductName(id) {
  return products.value.find(p => p.id == id)?.name || ''
}

async function loadData() {
  try {
    loading.value = true
    loadingCustomers.value = true
    loadingProducts.value = true

    // Rechnung laden
    const invoice = await invoiceService.getById(props.invoiceId)

    // Formulardaten setzen
    Object.assign(formData, {
      company: invoice.company,
      business_partner: invoice.business_partner,
      issue_date: invoice.issue_date,
      due_date: invoice.due_date,
      buyer_reference: invoice.buyer_reference || '',
      seller_reference: invoice.seller_reference || '',
      status: invoice.status,
      notes: invoice.notes || '',
      lines: (invoice.lines || invoice.invoice_lines || []).map(line => ({
        id: line.id,
        product: line.product,
        quantity: parseFloat(line.quantity) || 1,
        unit_price_net: parseFloat(line.unit_price_net) || 0,
        vat_rate: parseFloat(line.vat_rate) ?? 19,
        description: line.description || '',
        line_total_gross: parseFloat(line.line_total) || 0,
        discount_percentage: parseFloat(line.discount_percentage || 0),
        discount_reason: line.discount_reason || ''
      })),
      allowance_charges: (invoice.allowance_charges || []).map(ac => ({
        id: ac.id,
        is_charge: ac.is_charge,
        actual_amount: parseFloat(ac.actual_amount),
        reason: ac.reason || '',
        reason_code: ac.reason_code || ''
      }))
    })

    // Merke IDs der bestehenden Rabatte/Zuschläge und Positionen für späteres Löschen
    originalAcIds.value = (invoice.allowance_charges || []).map(ac => ac.id)
    originalLineIds.value = (invoice.lines || []).map(l => l.id)

    // Zusatzdaten laden
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

    console.log('Geladene Daten (Edit):', {
      customers: customers.value.length,
      products: products.value.length,
      companies: companies.value.length
    })

    // Warnung bei leeren Daten
    if (customers.value.length === 0) {
      console.warn('Keine Kunden gefunden!')
    }
    if (products.value.length === 0) {
      console.warn('Keine Produkte gefunden!')
    }

  } catch (error) {
    console.error('Fehler beim Laden der Daten:', error)
    submitError.value = 'Fehler beim Laden der Rechnung'
  } finally {
    loading.value = false
    loadingCustomers.value = false
    loadingProducts.value = false
  }
}

async function handleSubmit() {
  Object.keys(errors).forEach(key => delete errors[key])
  submitError.value = null

  if (!isFormValid.value) {
    submitError.value = 'Bitte füllen Sie alle Pflichtfelder aus'
    return
  }

  saving.value = true

  try {
    const updateData = {
      company: formData.company,
      business_partner: formData.business_partner,
      issue_date: formData.issue_date,
      due_date: formData.due_date,
      buyer_reference: formData.buyer_reference,
      seller_reference: formData.seller_reference,
      notes: formData.notes,
      // lines ist im InvoiceSerializer read_only – werden separat via /invoice-lines/ verwaltet
    }

    const updated = await invoiceService.update(props.invoiceId, updateData)

    // Positionen aktualisieren (InvoiceSerializer.lines ist read_only → eigene Requests)
    if (formData.status === 'draft') {
      const currentLineIds = formData.lines.filter(l => l.id).map(l => l.id)
      const removedLineIds = originalLineIds.value.filter(id => !currentLineIds.includes(id))

      // Gelöschte Positionen entfernen
      await Promise.all(removedLineIds.map(id => invoiceService.deleteLine(id)))

      // Bestehende updaten, neue anlegen
      await Promise.all(formData.lines.map(line => {
        const linePayload = {
          invoice: props.invoiceId,
          product: line.product,
          quantity: line.quantity,
          unit_price_net: line.unit_price_net,
          vat_rate: line.vat_rate,
          description: line.description || '',
          discount_percentage: line.discount_percentage || 0,
          discount_reason: line.discount_reason || ''
        }
        if (line.id) {
          return invoiceService.updateLine(line.id, linePayload)
        } else {
          return invoiceService.createLine(props.invoiceId, linePayload)
        }
      }))
      originalLineIds.value = formData.lines.filter(l => l.id).map(l => l.id)
    }

    // Kopfebene Rabatte/Zuschläge: alte löschen, neue anlegen
    if (formData.status === 'draft') {
      await Promise.all(originalAcIds.value.map(id => invoiceService.deleteAllowanceCharge(id)))
      originalAcIds.value = []
      const acPromises = formData.allowance_charges
        .filter(ac => ac.actual_amount > 0)
        .map(ac => invoiceService.createAllowanceCharge({
          invoice: props.invoiceId,
          is_charge: ac.is_charge,
          actual_amount: ac.actual_amount,
          reason: ac.reason || (ac.is_charge ? 'Zuschlag' : 'Rabatt'),
          reason_code: ac.reason_code || '',
          sort_order: 0
        }))
      await Promise.all(acPromises)
    }

    emit('updated', updated)
    emit('close')
  } catch (error) {
    console.error('Fehler beim Aktualisieren der Rechnung:', error)

    if (error.response?.data) {
      const serverErrors = error.response.data

      if (serverErrors.detail) {
        submitError.value = serverErrors.detail
      } else if (serverErrors.non_field_errors) {
        submitError.value = serverErrors.non_field_errors.join(', ')
      } else {
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
    saving.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* Gleiche Styles wie InvoiceCreateModal */
.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.loading-state {
  padding: 2rem;
  text-align: center;
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

.readonly-field {
  padding: 0.5rem 0.75rem;
  background: #f9fafb;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  color: #6b7280;
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

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
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
