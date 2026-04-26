<template>
  <BaseModal :is-open="true" @close="$emit('close')">
    <template #title>
      Neues Produkt anlegen
    </template>

    <form @submit.prevent="handleSubmit" class="product-form">
      <!-- Produktname -->
      <div class="form-group">
        <label for="name">Produktname *</label>
        <BaseInput
          id="name"
          v-model="formData.name"
          placeholder="z.B. Beratungsleistung"
          :error="errors.name"
          required
        />
      </div>

      <!-- Beschreibung -->
      <div class="form-group">
        <label for="description">Beschreibung</label>
        <BaseInput
          id="description"
          v-model="formData.description"
          type="textarea"
          rows="3"
          placeholder="Detaillierte Produktbeschreibung"
          :error="errors.description"
        />
      </div>

      <!-- Preis und MwSt. -->
      <div class="form-row">
        <div class="form-group">
          <label for="base_price">Einzelpreis (Netto) *</label>
          <BaseInput
            id="base_price"
            v-model.number="formData.base_price"
            type="number"
            step="0.01"
            min="0"
            placeholder="0.00"
            :error="errors.base_price"
            required
          />
        </div>

        <div class="form-group">
          <label for="default_tax_rate">MwSt.-Satz *</label>
          <BaseSelect
            id="default_tax_rate"
            v-model.number="formData.default_tax_rate"
            :options="vatRateOptions"
            :error="errors.default_tax_rate"
            required
          />
        </div>
      </div>

      <!-- Einheit und Artikelnummer -->
      <div class="form-row">
        <div class="form-group">
          <label for="unit_of_measure">Einheit *</label>
          <BaseSelect
            id="unit_of_measure"
            v-model="formData.unit_of_measure"
            :options="unitOptions"
            :error="errors.unit_of_measure"
            required
          />
        </div>

        <div class="form-group">
          <label for="sku">Artikelnummer (SKU)</label>
          <BaseInput
            id="sku"
            v-model="formData.sku"
            placeholder="z.B. ART-12345"
            :error="errors.sku"
          />
        </div>
      </div>

      <!-- Produktcode und Kategorie -->
      <div class="form-row">
        <div class="form-group">
          <label for="product_code">Produktcode *</label>
          <BaseInput
            id="product_code"
            v-model="formData.product_code"
            placeholder="z.B. ART-12345"
            :error="errors.product_code"
            required
          />
        </div>

        <div class="form-group">
          <label for="category">Kategorie</label>
          <BaseInput
            id="category"
            v-model="formData.category"
            placeholder="z.B. Dienstleistung, Hardware, Software"
            :error="errors.category"
          />
        </div>
      </div>

      <!-- Aktiv-Status -->
      <div class="form-group">
        <BaseCheckbox
          v-model="formData.is_active"
          label="Produkt ist aktiv"
          hint="Inaktive Produkte können nicht in neuen Rechnungen verwendet werden"
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
        >
          Produkt anlegen
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { productService } from '@/api/services/productService'
import { UNIT_OPTIONS } from '@/utils/unitOfMeasure'
import BaseModal from './BaseModal.vue'
import BaseInput from './BaseInput.vue'
import BaseSelect from './BaseSelect.vue'
import BaseButton from './BaseButton.vue'
import BaseAlert from './BaseAlert.vue'
import BaseCheckbox from './BaseCheckbox.vue'

const emit = defineEmits(['close', 'created'])

const loading = ref(false)
const submitError = ref(null)
const vatRateOptions = ref([])
const unitOptions = ref([])

const formData = reactive({
  name: '',
  description: '',
  base_price: 0,
  default_tax_rate: 19.00,
  unit_of_measure: 1,
  sku: '',
  product_code: '',
  category: '',
  is_active: true
})

const errors = reactive({})

async function loadTaxAndUnitOptions() {
  try {
    const data = await productService.getTaxOptions()
    vatRateOptions.value = (data.tax_rates || []).map(option => ({
      label: option.label,
      value: Number(option.value)
    }))
    // API-Werte werden ignoriert – wir nutzen die zentrale deutsche Übersetzungstabelle
    unitOptions.value = UNIT_OPTIONS

    if (vatRateOptions.value.length > 0 && !vatRateOptions.value.some(option => option.value === formData.default_tax_rate)) {
      formData.default_tax_rate = vatRateOptions.value[0].value
    }

    if (unitOptions.value.length > 0 && !unitOptions.value.some(option => option.value === formData.unit_of_measure)) {
      formData.unit_of_measure = unitOptions.value[0].value
    }
  } catch (error) {
    vatRateOptions.value = [
      { label: '0% (Befreit)', value: 0.00 },
      { label: '7% (Ermäßigt)', value: 7.00 },
      { label: '19% (Standard)', value: 19.00 }
    ]
    unitOptions.value = UNIT_OPTIONS
  }
}

async function handleSubmit() {
  Object.keys(errors).forEach(key => delete errors[key])
  submitError.value = null

  // Client-seitige Pflichtfeld-Validierung
  let hasClientErrors = false
  if (!formData.product_code || !formData.product_code.trim()) {
    errors.product_code = 'Produktcode ist ein Pflichtfeld.'
    hasClientErrors = true
  }
  if (!formData.name || !formData.name.trim()) {
    errors.name = 'Produktname ist ein Pflichtfeld.'
    hasClientErrors = true
  }
  if (formData.base_price === null || formData.base_price === '' || formData.base_price < 0) {
    errors.base_price = 'Einzelpreis ist ein Pflichtfeld.'
    hasClientErrors = true
  }
  if (hasClientErrors) {
    submitError.value = 'Bitte korrigieren Sie die markierten Fehler.'
    return
  }

  loading.value = true

  try {
    const created = await productService.create(formData)
    emit('created', created)
    emit('close')
  } catch (error) {
    console.error('Fehler beim Anlegen des Produkts:', error)

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
    loading.value = false
  }
}

onMounted(() => {
  loadTaxAndUnitOptions()
})
</script>

<style scoped>
.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.product-form {
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

.form-hint {
  color: #6b7280;
  font-size: 0.875rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 1.25rem;
  height: 1.25rem;
  cursor: pointer;
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
