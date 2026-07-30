<template>
  <BaseModal :is-open="true" @close="handleClose">
    <template #title>
      Rechnung bearbeiten
    </template>

    <!-- Lock denied by another user -->
    <div v-if="lockError" class="lock-denied-state">
      <p class="lock-denied-message">
        ⚠️ Diese Rechnung wird gerade von
        <strong>{{ lockError.editing_by }}</strong> bearbeitet
        <span v-if="lockError.editing_since">
          (seit {{ formatLockTime(lockError.editing_since) }})
        </span>.
      </p>
      <p class="lock-denied-hint">Bitte versuchen Sie es später erneut.</p>
    </div>

    <!-- Normal loading / form -->
    <div v-else-if="loading" class="loading-state">
      <p>Lädt Rechnung...</p>
    </div>

    <form v-else-if="!lockError" @submit.prevent="handleSubmit" class="invoice-form">
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

        <div class="form-group">
          <label for="contract_reference">Vertragsreferenz (optional)</label>
          <BaseInput
            id="contract_reference"
            v-model="formData.contract_reference"
            placeholder="z.B. VTR-2026-001"
            :error="errors.contract_reference"
          />
          <small class="form-hint">Vertragsnummer / Rahmenvertrag (BT-12)</small>
        </div>
      </div>

      <!-- Leistungszeitraum (BG-14) -->
      <div class="form-row">
        <div class="form-group">
          <BaseDatePicker
            id="billing_period_start"
            v-model="formData.billing_period_start"
            label="Leistungsbeginn (optional)"
            placeholder="Datum auswählen"
            :error="errors.billing_period_start"
          />
          <small class="form-hint">Beginn des Leistungszeitraums, z.B. 01.04.2026 (BT-73)</small>
        </div>

        <div class="form-group">
          <BaseDatePicker
            id="billing_period_end"
            v-model="formData.billing_period_end"
            label="Leistungsende (optional)"
            placeholder="Datum auswählen"
            :min-date="formData.billing_period_start"
            :error="errors.billing_period_end"
          />
          <small class="form-hint">Ende des Leistungszeitraums, z.B. 30.04.2026 (BT-74)</small>
        </div>
      </div>

      <!-- Lieferadresse BG-15 (BT-75–BT-80) -->
      <div class="form-group">
        <label class="section-toggle">
          <input type="checkbox" v-model="showDeliveryAddress" />
          Abweichende Lieferadresse angeben (BG-15)
        </label>
      </div>
      <template v-if="showDeliveryAddress">
        <div class="form-row">
          <div class="form-group flex-2">
            <BaseInput
              id="delivery_address_line1"
              v-model="formData.delivery_address_line1"
              label="Straße / Hausnummer (BT-75)"
              placeholder="z.B. Musterstraße 1"
            />
          </div>
          <div class="form-group">
            <BaseInput
              id="delivery_address_line2"
              v-model="formData.delivery_address_line2"
              label="Adresszusatz (BT-76)"
              placeholder="z.B. Hinterhaus"
            />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <BaseInput
              id="delivery_postal_code"
              v-model="formData.delivery_postal_code"
              label="PLZ (BT-78)"
              placeholder="z.B. 80331"
            />
          </div>
          <div class="form-group flex-2">
            <BaseInput
              id="delivery_city"
              v-model="formData.delivery_city"
              label="Ort (BT-77)"
              placeholder="z.B. München"
            />
          </div>
          <div class="form-group">
            <BaseInput
              id="delivery_country"
              v-model="formData.delivery_country"
              label="Land ISO (BT-80)"
              placeholder="z.B. DE"
              maxlength="2"
            />
          </div>
        </div>
      </template>

      <!-- Zahlungsempfänger BG-10 (BT-59/BT-60) -->
      <div class="form-group">
        <label class="section-toggle">
          <input type="checkbox" v-model="showPayee" />
          Abweichender Zahlungsempfänger angeben (BG-10)
        </label>
      </div>
      <template v-if="showPayee">
        <div class="form-row">
          <div class="form-group flex-2">
            <BaseInput
              id="payee_name"
              v-model="formData.payee_name"
              label="Name des Zahlungsempfängers (BT-59)"
              placeholder="z.B. Factoring GmbH"
            />
          </div>
          <div class="form-group">
            <BaseInput
              id="payee_id"
              v-model="formData.payee_id"
              label="Kennung (BT-60, optional)"
              placeholder="z.B. Gläubiger-ID"
            />
          </div>
        </div>
      </template>

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
            size="sm"
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
              size="sm"
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

          <!-- Zeilenspezifischer Leistungszeitraum (EN16931 BG-26: BT-134/BT-135) -->
          <div class="form-row" v-if="line.billing_period_start || line.billing_period_end || formData.status === 'draft'">
            <div class="form-group">
              <label :for="`line_billing_start_${index}`">Leistungszeitraum Beginn (BT-134)</label>
              <BaseInput
                :id="`line_billing_start_${index}`"
                v-model="line.billing_period_start"
                type="date"
                :readonly="formData.status !== 'draft'"
              />
            </div>
            <div class="form-group">
              <label :for="`line_billing_end_${index}`">Leistungszeitraum Ende (BT-135)</label>
              <BaseInput
                :id="`line_billing_end_${index}`"
                v-model="line.billing_period_end"
                type="date"
                :min-date="line.billing_period_start"
                :readonly="formData.status !== 'draft'"
              />
            </div>
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
            <div class="form-group" v-if="line.discount_percentage > 0">
              <label :for="`discount_reason_code_${index}`">Rabattcode (BT-140)</label>
              <BaseInput
                :id="`discount_reason_code_${index}`"
                v-model="line.discount_reason_code"
                placeholder="z.B. 95"
                maxlength="10"
                :readonly="formData.status !== 'draft'"
              />
            </div>
          </div>

          <!-- VAT Exemption Reason Code (EN16931 BT-121) -->
          <div class="form-row" v-if="line.vat_rate == 0 || line.vat_exemption_reason_code">
            <div class="form-group flex-2">
              <label :for="`vat_exemption_reason_code_${index}`">VATEX-Code (BT-121)</label>
              <BaseInput
                :id="`vat_exemption_reason_code_${index}`"
                v-model="line.vat_exemption_reason_code"
                placeholder="z.B. VATEX-EU-AE"
                maxlength="20"
                :readonly="formData.status !== 'draft'"
              />
            </div>
          </div>

          <!-- Bruttopreis BG-29 BT-148 (optional) -->
          <div class="form-row">
            <div class="form-group">
              <label :for="`gross_price_${index}`">Bruttopreis vor Rabatt (BT-148, optional)</label>
              <BaseInput
                :id="`gross_price_${index}`"
                v-model.number="line.gross_price"
                type="number"
                step="0.000001"
                min="0"
                placeholder="leer = nur Nettopreis (BT-146)"
                :readonly="formData.status !== 'draft'"
              />
            </div>
          </div>

          <!-- Produktattribute BG-32 (BT-160/BT-161) -->
          <div class="line-attributes-section">
            <div class="section-header">
              <span class="form-label">Attribute (BG-32, optional)</span>
              <BaseButton
                v-if="formData.status === 'draft'"
                type="button"
                variant="secondary"
                size="sm"
                @click="addLineAttribute(index)"
              >
                + Attribut
              </BaseButton>
            </div>
            <p v-if="line.attributes.length === 0" class="ac-empty">
              Keine Produktattribute
            </p>
            <div
              v-for="(attr, attrIdx) in line.attributes"
              :key="attrIdx"
              class="form-row"
            >
              <div class="form-group">
                <label :for="`attr-name-${index}-${attrIdx}`">Name (BT-160)</label>
                <BaseInput
                  :id="`attr-name-${index}-${attrIdx}`"
                  v-model="attr.name"
                  placeholder="z.B. Farbe"
                  :readonly="formData.status !== 'draft'"
                />
              </div>
              <div class="form-group">
                <label :for="`attr-value-${index}-${attrIdx}`">Wert (BT-161)</label>
                <BaseInput
                  :id="`attr-value-${index}-${attrIdx}`"
                  v-model="attr.value"
                  placeholder="z.B. Rot"
                  :readonly="formData.status !== 'draft'"
                />
              </div>
              <div class="form-group" v-if="formData.status === 'draft'">
                <BaseButton
                  type="button"
                  variant="danger"
                  size="sm"
                  @click="removeLineAttribute(index, attrIdx)"
                >
                  Entfernen
                </BaseButton>
              </div>
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
              <label :for="'ac-type-' + acIdx">Typ</label>
              <select :id="'ac-type-' + acIdx" v-model="ac.is_charge" class="base-select" :disabled="formData.status !== 'draft'">
                <option :value="false">Rabatt (–)</option>
                <option :value="true">Zuschlag (+)</option>
              </select>
            </div>
            <div class="form-group">
              <label :for="'ac-amount-' + acIdx">Betrag (Netto)</label>
              <BaseInput
                :id="'ac-amount-' + acIdx"
                v-model.number="ac.actual_amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                :readonly="formData.status !== 'draft'"
              />
            </div>
            <div class="form-group flex-2">
              <label :for="'ac-reason-' + acIdx">Grund</label>
              <BaseInput
                :id="'ac-reason-' + acIdx"
                v-model="ac.reason"
                placeholder="z.B. Skonto, Versandkosten"
                :readonly="formData.status !== 'draft'"
              />
            </div>
            <div class="form-group" v-if="formData.status === 'draft'">
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

      <!-- Anzahlung / Rundung (BT-113 / BT-114) -->
      <div class="form-row">
        <div class="form-group">
          <BaseInput
            id="prepaid_amount"
            v-model.number="formData.prepaid_amount"
            label="Anzahlung (BT-113, optional)"
            type="number"
            step="0.01"
            min="0"
            placeholder="0.00"
          />
          <small class="form-hint">Bereits geleistete Zahlung / Vorauszahlung</small>
        </div>
        <div class="form-group">
          <BaseInput
            id="rounding_amount"
            v-model.number="formData.rounding_amount"
            label="Rundungsbetrag (BT-114, optional)"
            type="number"
            step="0.01"
            placeholder="0.00"
          />
          <small class="form-hint">Kaufmännische Rundungsdifferenz</small>
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
          @click="handleClose"
          :disabled="saving"
        >
          {{ lockError ? 'Schließen' : 'Abbrechen' }}
        </BaseButton>
        <BaseButton
          v-if="!lockError"
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
import { useEditLock } from '@/composables/useEditLock'
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

// Edit lock (ADR-024)
const { lockError, acquireLock, releaseLock } = useEditLock(props.invoiceId)

// State
const loading = ref(true)
const saving = ref(false)
const loadingCustomers = ref(false)
const loadingProducts = ref(false)
const submitError = ref(null)
const originalAcIds = ref([])
const originalLineIds = ref([])
const originalLineAttributeIds = ref({})

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
  contract_reference: '',
  billing_period_start: null,
  billing_period_end: null,
  // BG-15: Delivery address
  delivery_address_line1: '',
  delivery_address_line2: '',
  delivery_city: '',
  delivery_postal_code: '',
  delivery_country: '',
  // BT-113 / BT-114
  prepaid_amount: 0,
  rounding_amount: 0,
  // BG-10: Payee (only set when payee differs from seller)
  payee_name: '',
  payee_id: '',
  status: 'draft',
  notes: '',
  lines: [],
  allowance_charges: []
})

const showDeliveryAddress = ref(false)
const showPayee = ref(false)

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

  if (netAdjustment === 0) {
    return totals
  }
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
    vatAdjustment += netAdjustment * share * (Number.parseFloat(rate) / 100)
  })
  totals.net += netAdjustment
  totals.vat += vatAdjustment
  totals.gross += netAdjustment + vatAdjustment
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
    discount_reason: '',
    discount_reason_code: '',
    vat_exemption_reason_code: '',
    gross_price: null,
    billing_period_start: null,
    billing_period_end: null,
    attributes: []
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
    line.unit_price_net = Number.parseFloat(product.current_price) || 0
    line.vat_rate = Number.parseFloat(product.default_tax_rate) || 19
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

function addLineAttribute(lineIndex) {
  formData.lines[lineIndex].attributes.push({ name: '', value: '' })
}

function removeLineAttribute(lineIndex, attrIndex) {
  formData.lines[lineIndex].attributes.splice(attrIndex, 1)
}

async function handleClose() {
  await releaseLock()
  emit('close')
}

function formatLockTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
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
      contract_reference: invoice.contract_reference || '',
      billing_period_start: invoice.billing_period_start || null,
      billing_period_end: invoice.billing_period_end || null,
      delivery_address_line1: invoice.delivery_address_line1 || '',
      delivery_address_line2: invoice.delivery_address_line2 || '',
      delivery_city: invoice.delivery_city || '',
      delivery_postal_code: invoice.delivery_postal_code || '',
      delivery_country: invoice.delivery_country || '',
      prepaid_amount: Number.parseFloat(invoice.prepaid_amount) || 0,
      rounding_amount: Number.parseFloat(invoice.rounding_amount) || 0,
      payee_name: invoice.payee_name || '',
      payee_id: invoice.payee_id || '',
      status: invoice.status,
      notes: invoice.notes || '',
    })
    showDeliveryAddress.value = !!(invoice.delivery_address_line1 || invoice.delivery_city || invoice.delivery_country)
    showPayee.value = !!(invoice.payee_name || invoice.payee_id)
    Object.assign(formData, {
      lines: (invoice.lines || invoice.invoice_lines || []).map(line => ({
        id: line.id,
        product: line.product,
        quantity: Number.parseFloat(line.quantity) || 1,
        unit_price_net: Number.parseFloat(line.unit_price_net) || 0,
        vat_rate: Number.parseFloat(line.vat_rate) ?? 19,
        description: line.description || '',
        line_total_gross: Number.parseFloat(line.line_total) || 0,
        discount_percentage: Number.parseFloat(line.discount_percentage || 0),
        discount_reason: line.discount_reason || '',
        discount_reason_code: line.discount_reason_code || '',
        vat_exemption_reason_code: line.vat_exemption_reason_code || '',
        gross_price: line.gross_price == null ? null : Number.parseFloat(line.gross_price),
        billing_period_start: line.billing_period_start || null,
        billing_period_end: line.billing_period_end || null,
        attributes: (line.attributes || []).map(a => ({ id: a.id, name: a.name || '', value: a.value || '' }))
      })),
      allowance_charges: (invoice.allowance_charges || []).map(ac => ({
        id: ac.id,
        is_charge: ac.is_charge,
        actual_amount: Number.parseFloat(ac.actual_amount),
        reason: ac.reason || '',
        reason_code: ac.reason_code || ''
      }))
    })

    // Merke IDs der bestehenden Rabatte/Zuschläge und Positionen für späteres Löschen
    originalAcIds.value = (invoice.allowance_charges || []).map(ac => ac.id)
    originalLineIds.value = (invoice.lines || []).map(l => l.id)
    originalLineAttributeIds.value = {}
    ;(invoice.lines || []).forEach(line => {
      originalLineAttributeIds.value[line.id] = (line.attributes || []).map(a => a.id)
    })

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

    if (import.meta.env.DEV) {
      console.log('Geladene Daten (Edit):', {
        customers: customers.value.length,
        products: products.value.length,
        companies: companies.value.length
      })
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
      contract_reference: formData.contract_reference,
      billing_period_start: formData.billing_period_start || null,
      billing_period_end: formData.billing_period_end || null,
      delivery_address_line1: formData.delivery_address_line1 || '',
      delivery_address_line2: formData.delivery_address_line2 || '',
      delivery_city: formData.delivery_city || '',
      delivery_postal_code: formData.delivery_postal_code || '',
      delivery_country: formData.delivery_country || '',
      prepaid_amount: formData.prepaid_amount || 0,
      rounding_amount: formData.rounding_amount || 0,
      payee_name: showPayee.value ? (formData.payee_name || '') : '',
      payee_id: showPayee.value ? (formData.payee_id || '') : '',
      notes: formData.notes,
      // lines ist im InvoiceSerializer read_only – werden separat via /invoice-lines/ verwaltet
    }

    const updated = await invoiceService.update(props.invoiceId, updateData)

    // Positionen aktualisieren (InvoiceSerializer.lines ist read_only → eigene Requests)
    if (formData.status === 'draft') {
      const currentLineIds = new Set(formData.lines.filter(l => l.id).map(l => l.id))
      const removedLineIds = originalLineIds.value.filter(id => !currentLineIds.has(id))

      // Gelöschte Positionen entfernen
      await Promise.all(removedLineIds.map(id => invoiceService.deleteLine(id)))

      // Bestehende updaten, neue anlegen
      await Promise.all(formData.lines.map(async line => {
        const linePayload = {
          invoice: props.invoiceId,
          product: line.product,
          quantity: line.quantity,
          unit_price_net: line.unit_price_net,
          vat_rate: line.vat_rate,
          description: line.description || '',
          discount_percentage: line.discount_percentage || 0,
          discount_reason: line.discount_reason || '',
          discount_reason_code: line.discount_reason_code || '',
          vat_exemption_reason_code: line.vat_exemption_reason_code || '',
          gross_price: line.gross_price ? Number.parseFloat(line.gross_price) : null,
          billing_period_start: line.billing_period_start || null,
          billing_period_end: line.billing_period_end || null
        }
        let resultLine
        if (line.id) {
          await invoiceService.updateLine(line.id, linePayload)
        } else {
          resultLine = await invoiceService.createLine(props.invoiceId, linePayload)
          line.id = resultLine.id
        }

        // Produktattribute (BG-32): bestehende löschen, aktuelle neu anlegen
        const existingAttrIds = originalLineAttributeIds.value[line.id] || []
        await Promise.all(existingAttrIds.map(attrId => invoiceService.deleteLineAttribute(attrId)))
        const validAttributes = (line.attributes || []).filter(a => a.name?.trim() && a.value?.trim())
        const createdAttrs = await Promise.all(validAttributes.map((attr, attrIdx) =>
          invoiceService.createLineAttribute({
            invoice_line: line.id,
            name: attr.name,
            value: attr.value,
            sort_order: attrIdx
          })
        ))
        originalLineAttributeIds.value[line.id] = createdAttrs.map(a => a.id)
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
    await releaseLock()
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
  acquireLock()
})
</script>

<style scoped>
/* Edit-Lock: Blocked-by-other-user state */
.lock-denied-state {
  padding: 2rem 1.5rem;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.lock-denied-message {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  color: #92400e;
}

.lock-denied-hint {
  margin: 0;
  font-size: 0.875rem;
  color: #78350f;
}

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

.line-attributes-section {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #d1d5db;
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
