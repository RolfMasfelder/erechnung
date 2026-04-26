<template>
  <BaseModal :is-open="true" @close="$emit('close')">
    <template #title>
      Produkt bearbeiten
    </template>

    <div v-if="loading" class="loading-state">
      <p>Lädt Produktdaten...</p>
    </div>

    <form v-else @submit.prevent="handleSubmit" class="product-form">
      <div class="form-group">
        <label for="name">Produktname *</label>
        <BaseInput
          id="name"
          v-model="formData.name"
          :error="errors.name"
          required
        />
      </div>

      <div class="form-group">
        <label for="description">Beschreibung</label>
        <BaseInput
          id="description"
          v-model="formData.description"
          type="textarea"
          rows="3"
          :error="errors.description"
        />
      </div>

      <div class="form-row">
        <div class="form-group">
          <label for="base_price">Einzelpreis (Netto) *</label>
          <BaseInput
            id="base_price"
            v-model.number="formData.base_price"
            type="number"
            step="0.01"
            min="0"
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

      <div class="form-row">
        <div class="form-group">
          <label for="unit_of_measure">Einheit</label>
          <BaseSelect
            id="unit_of_measure"
            v-model="formData.unit_of_measure"
            :options="unitOptions"
            :error="errors.unit_of_measure"
          />
        </div>

        <div class="form-group">
          <label for="sku">Artikelnummer (SKU)</label>
          <BaseInput
            id="sku"
            v-model="formData.sku"
            :error="errors.sku"
          />
        </div>
      </div>

      <div class="form-group">
        <label for="category">Kategorie</label>
        <BaseInput
          id="category"
          v-model="formData.category"
          :error="errors.category"
        />
      </div>

      <div class="form-group">
        <BaseCheckbox
          v-model="formData.is_active"
          label="Produkt ist aktiv"
          hint="Inaktive Produkte können nicht in neuen Rechnungen verwendet werden"
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
import { productService } from '@/api/services/productService'
import { UNIT_OPTIONS } from '@/utils/unitOfMeasure'
import { useToast } from '@/composables/useToast'
import BaseModal from './BaseModal.vue'
import BaseInput from './BaseInput.vue'
import BaseSelect from './BaseSelect.vue'
import BaseButton from './BaseButton.vue'
import BaseAlert from './BaseAlert.vue'
import BaseCheckbox from './BaseCheckbox.vue'

const props = defineProps({
  productId: {
    type: [Number, String],
    required: true
  }
})

const emit = defineEmits(['close', 'updated'])
const toast = useToast()

const loading = ref(true)
const saving = ref(false)
const submitError = ref(null)
const vatRateOptions = ref([])
const unitOptions = ref([])

const formData = reactive({
  name: '',
  description: '',
  base_price: 0,
  default_tax_rate: 19.00,
  unit_of_measure: '',
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
  } catch (error) {
    vatRateOptions.value = [
      { label: '0% (Befreit)', value: 0.00 },
      { label: '7% (Ermäßigt)', value: 7.00 },
      { label: '19% (Standard)', value: 19.00 }
    ]
    unitOptions.value = UNIT_OPTIONS
  }
}

async function loadProduct() {
  loading.value = true
  try {
    const product = await productService.getById(props.productId)
    Object.assign(formData, {
      name: product.name,
      description: product.description || '',
      base_price: parseFloat(product.base_price) || 0,
      default_tax_rate: parseFloat(product.default_tax_rate) || 0,
      unit_of_measure: product.unit_of_measure || '',
      sku: product.sku || '',
      product_code: product.product_code || '',
      category: product.category || '',
      is_active: product.is_active ?? true
    })
  } catch (error) {
    console.error('Fehler beim Laden des Produkts:', error)
    submitError.value = 'Produkt konnte nicht geladen werden'
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  Object.keys(errors).forEach(key => delete errors[key])
  submitError.value = null

  saving.value = true

  try {
    const updated = await productService.patch(props.productId, formData)
    emit('updated', updated)
    emit('close')
  } catch (error) {
    console.error('Fehler beim Aktualisieren des Produkts:', error)

    if (error.response?.data) {
      const serverErrors = error.response.data

      if (serverErrors.detail) {
        submitError.value = serverErrors.detail
      } else if (serverErrors.non_field_errors) {
        submitError.value = serverErrors.non_field_errors.join(', ')
        toast.error(submitError.value)
      } else {
        const errorMessages = []
        Object.keys(serverErrors).forEach(field => {
          errors[field] = Array.isArray(serverErrors[field])
            ? serverErrors[field].join(', ')
            : serverErrors[field]

          errorMessages.push(`${field}: ${errors[field]}`)
        })
        submitError.value = 'Bitte korrigieren Sie die markierten Fehler'
        toast.error(errorMessages.join(' | '))
      }
    } else {
      submitError.value = 'Ein unerwarteter Fehler ist aufgetreten'
      toast.error(submitError.value)
    }
  } finally {
    saving.value = false
  }
}

// Optionen zuerst laden, damit BaseSelect bei onUpdate direkt die richtigen
// Einträge hat und keinen Leerstand zeigt (Race-Condition-Fix).
onMounted(async () => {
  await loadTaxAndUnitOptions()
  await loadProduct()
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
