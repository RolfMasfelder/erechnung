<template>
  <div class="select-group">
    <label v-if="label" :for="selectId" class="select-label">
      {{ label }}
      <span v-if="required" class="required">*</span>
    </label>

    <div class="select-wrapper">
      <select
        :id="selectId"
        :value="normalizedValue"
        :disabled="disabled"
        :required="required"
        :class="selectClasses"
        @change="handleChange"
      >
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option
          v-for="option in options"
          :key="getOptionValue(option)"
          :value="getOptionValue(option)"
          :selected="getOptionValue(option) == modelValue"
        >
          {{ getOptionLabel(option) }}
        </option>
      </select>

      <span class="select-arrow">▼</span>
    </div>

    <span v-if="error" class="error-message">{{ error }}</span>
    <span v-else-if="hint" class="hint-message">{{ hint }}</span>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  id: {
    type: String,
    default: null
  },
  modelValue: {
    type: [String, Number, Boolean, null],
    default: null
  },
  options: {
    type: Array,
    required: true
  },
  valueKey: {
    type: String,
    default: 'value'
  },
  labelKey: {
    type: String,
    default: 'label'
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: 'Bitte auswählen...'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  required: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const selectId = computed(() => props.id || `select-${Math.random().toString(36).substr(2, 9)}`)

const selectClasses = computed(() => [
  'select',
  {
    'select-error': props.error,
    'select-disabled': props.disabled
  }
])

const getOptionValue = (option) => {
  if (typeof option === 'object' && option !== null) {
    return option[props.valueKey]
  }
  return option
}

const getOptionLabel = (option) => {
  if (typeof option === 'object' && option !== null) {
    return option[props.labelKey]
  }
  return option
}

// Gibt den exakten Option-Wert zurück, der lose mit modelValue übereinstimmt.
// Löst den Typ-Mismatch zwischen API-Strings ("19.00") und Option-Numbers (19).
const normalizedValue = computed(() => {
  if (!props.options?.length) return props.modelValue ?? ''
  const match = props.options.find(o => getOptionValue(o) == props.modelValue)
  return match != null ? getOptionValue(match) : (props.modelValue ?? '')
})

const handleChange = (event) => {
  const rawValue = event.target.value
  // Den originalen Option-Wert mit korrektem Typ zurückgeben (Number bleibt Number)
  const match = props.options.find(o => String(getOptionValue(o)) === rawValue)
  const value = match != null ? getOptionValue(match) : rawValue
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped>
.select-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-bottom: 1rem;
}

.select-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.required {
  color: #ef4444;
  margin-left: 0.25rem;
}

.select-wrapper {
  position: relative;
}

.select {
  width: 100%;
  padding: 0.5rem 2.5rem 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 1rem;
  background-color: white;
  cursor: pointer;
  appearance: none;
  transition: all 0.2s ease-in-out;
  color: #111827;
}

/* Placeholder styling - grau wenn leer */
.select:invalid,
.select[value=""] {
  color: #9ca3af;
}

.select option {
  color: #111827;
}

.select option[disabled] {
  color: #9ca3af;
}

.select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.select-error {
  border-color: #ef4444;
}

.select-error:focus {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.select-disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
  opacity: 0.6;
}

.select-arrow {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  font-size: 0.75rem;
  color: #6b7280;
}

.error-message {
  font-size: 0.875rem;
  color: #ef4444;
}

.hint-message {
  font-size: 0.875rem;
  color: #6b7280;
}
</style>
