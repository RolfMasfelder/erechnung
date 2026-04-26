<template>
  <BaseModal :is-open="true" @close="$emit('close')">
    <template #title>
      Geschäftspartner bearbeiten
    </template>

    <div v-if="loading" class="loading-state">
      <p>Lädt Geschäftspartnerdaten...</p>
    </div>

    <form v-else @submit.prevent="handleSubmit" class="customer-form">
      <!-- Partnertyp -->
      <div class="form-group">
        <label for="partner_type">Partnertyp *</label>
        <BaseSelect
          id="partner_type"
          v-model="formData.partner_type"
          :options="partnerTypeOptions"
          :error="errors.partner_type"
          required
        />
      </div>

      <!-- Gleiche Formularfelder wie BusinessPartnerCreateModal -->
      <div class="form-group">
        <label for="name">Firmenname / Name *</label>
        <BaseInput
          id="name"
          v-model="formData.name"
          :error="errors.name"
          required
        />
      </div>

      <div class="form-group">
        <label for="street">Straße und Hausnummer *</label>
        <BaseInput
          id="street"
          v-model="formData.street"
          :error="errors.street"
          required
        />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="postal_code">PLZ *</label>
          <BaseInput
            id="postal_code"
            v-model="formData.postal_code"
            :error="errors.postal_code"
            required
          />
        </div>

        <div class="form-group flex-2">
          <label for="city">Stadt *</label>
          <BaseInput
            id="city"
            v-model="formData.city"
            :error="errors.city"
            required
          />
        </div>
      </div>

      <div class="form-group">
        <label for="country">Land *</label>
        <BaseSelect
          id="country"
          v-model="formData.country"
          :options="countryOptions"
          :loading="loadingCountries"
          :error="errors.country"
          required
        />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="email">E-Mail</label>
          <BaseInput
            id="email"
            v-model="formData.email"
            type="email"
            :error="errors.email"
          />
        </div>

        <div class="form-group">
          <label for="phone">Telefon</label>
          <BaseInput
            id="phone"
            v-model="formData.phone"
            type="tel"
            :error="errors.phone"
          />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="tax_number">Steuernummer</label>
          <BaseInput
            id="tax_number"
            v-model="formData.tax_number"
            :error="errors.tax_number"
          />
        </div>

        <div class="form-group">
          <label for="vat_id">USt-ID</label>
          <BaseInput
            id="vat_id"
            v-model="formData.vat_id"
            :error="errors.vat_id"
          />
        </div>
      </div>

      <!-- Leitweg-ID (nur bei GOVERNMENT) -->
      <div v-if="formData.partner_type === 'GOVERNMENT'" class="form-group">
        <label for="leitweg_id">Leitweg-ID *</label>
        <BaseInput
          id="leitweg_id"
          v-model="formData.leitweg_id"
          placeholder="z.B. 04011000-1234512345-06"
          :error="errors.leitweg_id"
          required
        />
        <small class="field-hint">Pflichtfeld für öffentliche Auftraggeber (XRechnung)</small>
      </div>

      <div class="form-group">
        <BaseTextarea
          id="notes"
          v-model="formData.notes"
          label="Notizen"
          :rows="3"
          placeholder="Zusätzliche Informationen zum Geschäftspartner"
        />
      </div>

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
        >
          Änderungen speichern
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { businessPartnerService } from '@/api/services/businessPartnerService'
import { countryService } from '@/api/services/countryService'
import BaseModal from './BaseModal.vue'
import BaseInput from './BaseInput.vue'
import BaseSelect from './BaseSelect.vue'
import BaseButton from './BaseButton.vue'
import BaseAlert from './BaseAlert.vue'
import BaseTextarea from './BaseTextarea.vue'

const props = defineProps({
  businessPartnerId: {
    type: [Number, String],
    required: true
  }
})

const emit = defineEmits(['close', 'updated'])

const loading = ref(true)
const saving = ref(false)
const loadingCountries = ref(false)
const submitError = ref(null)

const formData = reactive({
  partner_type: 'BUSINESS',
  name: '',
  street: '',
  postal_code: '',
  city: '',
  country: 'DE',
  email: '',
  phone: '',
  tax_number: '',
  vat_id: '',
  leitweg_id: '',
  notes: ''
})

const partnerTypeOptions = ref([
  { value: 'BUSINESS', label: 'Unternehmen' },
  { value: 'INDIVIDUAL', label: 'Privatperson' },
  { value: 'GOVERNMENT', label: 'Öffentlicher Auftraggeber' },
  { value: 'NON_PROFIT', label: 'Gemeinnützig' },
])

const errors = reactive({})

// Fallback-Liste (wird durch API-Daten ersetzt)
const countryOptions = ref([
  { value: 'DE', label: 'Deutschland' },
  { value: 'AT', label: 'Österreich' },
  { value: 'CH', label: 'Schweiz' },
  { value: 'FR', label: 'Frankreich' },
  { value: 'NL', label: 'Niederlande' },
  { value: 'BE', label: 'Belgien' },
  { value: 'PL', label: 'Polen' },
  { value: 'CZ', label: 'Tschechien' }
])

async function loadCountries() {
  loadingCountries.value = true
  try {
    const countries = await countryService.getAll()
    if (countries.length > 0) {
      countryOptions.value = countries.map(c => ({ value: c.code, label: c.name }))
    }
  } catch (error) {
    console.warn('Länderliste konnte nicht geladen werden, verwende Fallback-Liste', error)
  } finally {
    loadingCountries.value = false
  }
}

async function loadCustomer() {
  loading.value = true
  try {
    const customer = await businessPartnerService.getById(props.businessPartnerId)
    Object.assign(formData, {
      partner_type: customer.partner_type || 'BUSINESS',
      name: customer.name,
      street: customer.street,
      postal_code: customer.postal_code,
      city: customer.city,
      country: customer.country || 'DE',
      email: customer.email || '',
      phone: customer.phone || '',
      tax_number: customer.tax_number || '',
      vat_id: customer.vat_id || '',
      leitweg_id: customer.leitweg_id || '',
      notes: customer.notes || ''
    })
  } catch (error) {
    console.error('Fehler beim Laden des Geschäftspartner:', error)
    submitError.value = 'Geschäftspartner konnte nicht geladen werden'
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  Object.keys(errors).forEach(key => delete errors[key])
  submitError.value = null

  saving.value = true

  try {
    const updated = await businessPartnerService.update(props.businessPartnerId, formData)
    emit('updated', updated)
    emit('close')
  } catch (error) {
    console.error('Fehler beim Aktualisieren des Geschäftspartner:', error)

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

// Länderliste zuerst laden, damit das Land-Select sofort korrekt vorselektiert
// wird wenn loadCustomer() das Formular sichtbar macht (Race-Condition-Fix).
onMounted(async () => {
  await loadCountries()
  await loadCustomer()
})
</script>

<style scoped>
.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.loading-state {
  padding: 2rem;
  text-align: center;
}

.customer-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #374151;
}

.field-hint {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: -0.25rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
}

.form-row .flex-2 {
  grid-column: span 1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
