<template>
  <BaseModal :isOpen="true" @close="$emit('close')">
    <template #title>
      Firma bearbeiten
    </template>

    <div v-if="loading" class="loading">
      Lädt Firmendaten...
    </div>

    <form v-else @submit.prevent="handleSubmit" class="company-form">
      <!-- Name -->
      <div class="form-group">
        <label for="name">Firmenname *</label>
        <BaseInput
          id="name"
          v-model="formData.name"
          placeholder="z.B. Musterfirma GmbH"
          :error="errors.name"
          required
        />
      </div>

      <!-- Adresse -->
      <div class="form-group">
        <label for="address_line1">Straße und Hausnummer *</label>
        <BaseInput
          id="address_line1"
          v-model="formData.address_line1"
          placeholder="z.B. Musterstraße 123"
          :error="errors.address_line1"
          required
        />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="postal_code">PLZ *</label>
          <BaseInput
            id="postal_code"
            v-model="formData.postal_code"
            placeholder="z.B. 12345"
            :error="errors.postal_code"
            required
          />
        </div>

        <div class="form-group flex-2">
          <label for="city">Stadt *</label>
          <BaseInput
            id="city"
            v-model="formData.city"
            placeholder="z.B. Berlin"
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
          :error="errors.country"
          required
        />
      </div>

      <!-- Kontaktdaten -->
      <div class="form-row">
        <div class="form-group">
          <label for="email">E-Mail</label>
          <BaseInput
            id="email"
            v-model="formData.email"
            type="email"
            placeholder="info@firma.de"
            :error="errors.email"
          />
        </div>

        <div class="form-group">
          <label for="phone">Telefon</label>
          <BaseInput
            id="phone"
            v-model="formData.phone"
            type="tel"
            placeholder="+49 123 456789"
            :error="errors.phone"
          />
        </div>
      </div>

      <!-- Steuernummer / USt-ID / Handelsregister -->
      <div class="form-row">
        <div class="form-group">
          <label for="tax_id">Steuernummer *</label>
          <BaseInput
            id="tax_id"
            v-model="formData.tax_id"
            placeholder="z.B. 123/456/78900"
            :error="errors.tax_id"
            required
          />
        </div>

        <div class="form-group">
          <label for="vat_id">USt-IdNr. **</label>
          <BaseInput
            id="vat_id"
            v-model="formData.vat_id"
            placeholder="z.B. DE123456789"
            :error="errors.vat_id"
          />
        </div>
      </div>

      <div class="form-group">
        <label for="commercial_register">Handelsregister **</label>
        <BaseInput
          id="commercial_register"
          v-model="formData.commercial_register"
          placeholder="z.B. HRB 12345, Amtsgericht Berlin"
          :error="errors.commercial_register"
        />
      </div>
      <p class="field-hint" :class="{ 'field-hint--error': errors.non_field_errors }">
        ** Mindestens USt-IdNr. oder Handelsregister muss angegeben werden (ZUGFeRD BR-CO-26).
      </p>
      <p v-if="errors.non_field_errors" class="field-error">{{ errors.non_field_errors }}</p>

      <!-- Bank Details -->
      <div class="form-group">
        <label for="bank_name">Bankname</label>
        <BaseInput
          id="bank_name"
          v-model="formData.bank_name"
          placeholder="z.B. Deutsche Bank"
          :error="errors.bank_name"
        />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="iban">IBAN</label>
          <BaseInput
            id="iban"
            v-model="formData.iban"
            placeholder="z.B. DE89370400440532013000"
            :error="errors.iban"
          />
        </div>

        <div class="form-group">
          <label for="bic">BIC</label>
          <BaseInput
            id="bic"
            v-model="formData.bic"
            placeholder="z.B. COBADEFFXXX"
            :error="errors.bic"
          />
        </div>
      </div>

      <!-- Logo -->
      <div class="form-group">
        <label>Firmenlogo</label>
        <div class="logo-upload">
          <img
            v-if="logoPreview || currentLogoUrl"
            :src="logoPreview || currentLogoUrl"
            alt="Logo-Vorschau"
            class="logo-preview"
          />
          <div class="logo-upload-actions">
            <label class="logo-file-label">
              {{ (logoPreview || currentLogoUrl) ? 'Logo ändern' : 'Logo auswählen' }}
              <input
                type="file"
                accept="image/png,image/jpeg,image/svg+xml"
                class="logo-file-input"
                @change="handleLogoChange"
              />
            </label>
            <BaseButton
              v-if="logoPreview || currentLogoUrl"
              type="button"
              variant="secondary"
              @click="clearLogo"
            >Logo entfernen</BaseButton>
          </div>
          <p class="logo-hint">PNG/JPG/SVG, empfohlen max. 60mm × 20mm</p>
        </div>
      </div>

      <!-- Status -->
      <div class="form-group">
        <label class="checkbox-label">
          <input
            type="checkbox"
            v-model="formData.is_active"
            class="checkbox"
          />
          <span>Firma ist aktiv</span>
        </label>
      </div>

      <!-- Form Actions -->
      <div class="form-actions">
        <BaseButton
          type="button"
          variant="secondary"
          @click="$emit('close')"
        >
          Abbrechen
        </BaseButton>
        <BaseButton
          type="submit"
          variant="primary"
          :loading="saving"
        >
          Änderungen speichern
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import BaseModal from './BaseModal.vue'
import BaseInput from './BaseInput.vue'
import BaseSelect from './BaseSelect.vue'
import BaseButton from './BaseButton.vue'
import { companyService } from '@/api/services/companyService'
import { useToast } from '@/composables/useToast'
import { getErrorMessage } from '@/utils/errorHandling'

const props = defineProps({
  companyId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['close', 'updated'])
const toast = useToast()

const loading = ref(false)
const saving = ref(false)
const errors = reactive({})
const selectedLogoFile = ref(null)
const logoPreview = ref(null)   // blob URL for newly selected file
const currentLogoUrl = ref('')  // URL from API for existing logo
const logoCleared = ref(false)

const handleLogoChange = (event) => {
  const file = event.target.files[0]
  if (!file) return
  selectedLogoFile.value = file
  logoPreview.value = URL.createObjectURL(file)
  logoCleared.value = false
}

const clearLogo = () => {
  selectedLogoFile.value = null
  logoPreview.value = null
  currentLogoUrl.value = ''
  logoCleared.value = true
}

const formData = reactive({
  name: '',
  address_line1: '',
  postal_code: '',
  city: '',
  country: 'DE',
  email: '',
  phone: '',
  tax_id: '',
  vat_id: '',
  commercial_register: '',
  bank_name: '',
  iban: '',
  bic: '',
  is_active: true
})

const countryOptions = [
  { value: 'DE', label: 'Deutschland' },
  { value: 'AT', label: 'Österreich' },
  { value: 'CH', label: 'Schweiz' },
  { value: 'FR', label: 'Frankreich' },
  { value: 'NL', label: 'Niederlande' },
  { value: 'BE', label: 'Belgien' },
  { value: 'LU', label: 'Luxemburg' },
  { value: 'IT', label: 'Italien' },
  { value: 'ES', label: 'Spanien' },
  { value: 'PL', label: 'Polen' }
]

const loadCompany = async () => {
  loading.value = true
  try {
    const company = await companyService.getById(props.companyId)

    // Populate form data
    Object.keys(formData).forEach(key => {
      if (company[key] !== undefined) {
        formData[key] = company[key]
      }
    })

    // Normalize country: may be stored as full name ("Deutschland") instead of code ("DE")
    const countryMatch = countryOptions.find(
      o => o.value === company.country || o.label === company.country
    )
    if (countryMatch) {
      formData.country = countryMatch.value
    }

    currentLogoUrl.value = company.logo || ''
  } catch (error) {
    console.error('Error loading company:', error)
    const errorMsg = getErrorMessage(error, 'Fehler beim Laden der Firmendaten')
    toast.error(errorMsg)
    emit('close')
  } finally {
    loading.value = false
  }
}

const validateForm = () => {
  Object.keys(errors).forEach(key => delete errors[key])
  let isValid = true

  if (!formData.name?.trim()) {
    errors.name = 'Firmenname ist erforderlich'
    isValid = false
  }

  if (!formData.address_line1?.trim()) {
    errors.address_line1 = 'Straße ist erforderlich'
    isValid = false
  }

  if (!formData.postal_code?.trim()) {
    errors.postal_code = 'PLZ ist erforderlich'
    isValid = false
  }

  if (!formData.city?.trim()) {
    errors.city = 'Stadt ist erforderlich'
    isValid = false
  }

  if (!formData.country) {
    errors.country = 'Land ist erforderlich'
    isValid = false
  }

  if (!formData.tax_id?.trim()) {
    errors.tax_id = 'Steuernummer ist erforderlich'
    isValid = false
  }

  if (!formData.vat_id?.trim() && !formData.commercial_register?.trim()) {
    errors.non_field_errors = 'Mindestens USt-IdNr. oder Handelsregister muss angegeben werden (ZUGFeRD BR-CO-26)'
    isValid = false
  }

  if (formData.email && !isValidEmail(formData.email)) {
    errors.email = 'Ungültige E-Mail-Adresse'
    isValid = false
  }

  return isValid
}

const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }

  saving.value = true

  try {
    let payload
    if (selectedLogoFile.value || logoCleared.value) {
      // Use multipart/form-data to send optional file change
      payload = new FormData()
      Object.entries(formData).forEach(([key, value]) => {
        if (value !== null && value !== undefined) payload.append(key, value)
      })
      if (selectedLogoFile.value) {
        payload.append('logo', selectedLogoFile.value)
      } else {
        payload.append('logo', '')  // clear the logo
      }
      const company = await companyService.patch(props.companyId, payload)
      emit('updated', company)
    } else {
      const company = await companyService.update(props.companyId, formData)
      emit('updated', company)
    }
    emit('close')
  } catch (error) {
    console.error('Error updating company:', error)

    if (error.response?.data) {
      // Handle validation errors from backend
      Object.keys(error.response.data).forEach(key => {
        if (Array.isArray(error.response.data[key])) {
          errors[key] = error.response.data[key][0]
        } else {
          errors[key] = error.response.data[key]
        }
      })
    }

    const errorMsg = getErrorMessage(error, 'Fehler beim Aktualisieren der Firma')
    toast.error(errorMsg, 8000)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadCompany()
})
</script>

<style scoped>
.company-form {
  max-width: 600px;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.loading {
  padding: 2rem;
  text-align: center;
  color: #6b7280;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-row .flex-2 {
  grid-column: span 1;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox {
  width: 1.25rem;
  height: 1.25rem;
  cursor: pointer;
}

.logo-upload {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.logo-preview {
  max-height: 60px;
  max-width: 180px;
  object-fit: contain;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  padding: 4px;
  background: #f9fafb;
}

.logo-upload-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logo-file-label {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.logo-file-label:hover {
  background: #e5e7eb;
}

.logo-file-input {
  display: none;
}

.logo-hint {
  font-size: 0.75rem;
  color: #9ca3af;
}

.field-hint {
  font-size: 0.75rem;
  color: #9ca3af;
  margin-top: 0.25rem;
  margin-bottom: 0;
}

.field-hint--error {
  color: #ef4444;
}

.field-error {
  font-size: 0.8rem;
  color: #ef4444;
  margin-top: 0.25rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column-reverse;
  }
}
</style>
