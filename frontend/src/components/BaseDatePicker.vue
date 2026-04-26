<template>
  <div class="datepicker-group">
    <label v-if="label" :for="pickerId" class="datepicker-label">
      {{ label }}
      <span v-if="required" class="required">*</span>
    </label>

    <div class="datepicker-wrapper">
      <VueDatePicker
        :id="pickerId"
        v-model="internalValue"
        :range="range"
        :multi-calendars="range"
        :enable-time-picker="false"
        :min-date="minDate"
        :max-date="maxDate"
        :disabled="disabled"
        :placeholder="computedPlaceholder"
        :formats="dateFormats"
        :locale="de"
        :clearable="clearable"
        :auto-apply="computedAutoApply"
        :class="pickerClasses"
        :text-input="false"
        :input-class-name="inputClassName"
        @update:model-value="handleUpdate"
        @blur="handleBlur"
        @focus="handleFocus"
        @cleared="handleCleared"
      >
        <template #input-icon>
          <span class="calendar-icon">📅</span>
        </template>

        <template #clear-icon="{ clear }">
          <span class="clear-icon" @click="clear">✕</span>
        </template>
      </VueDatePicker>
    </div>

    <span v-if="error" class="error-message">{{ error }}</span>
    <span v-else-if="hint" class="hint-message">{{ hint }}</span>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { de } from 'date-fns/locale'
import { parseISO, format, isValid } from 'date-fns'

const props = defineProps({
  id: {
    type: String,
    default: null
  },
  modelValue: {
    type: [Date, String, Array],
    default: null
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
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
  },
  range: {
    type: Boolean,
    default: false
  },
  minDate: {
    type: [Date, String],
    default: null
  },
  maxDate: {
    type: [Date, String],
    default: null
  },
  clearable: {
    type: Boolean,
    default: true
  },
  autoApply: {
    type: Boolean,
    default: null
  },
  textInput: {
    type: Boolean,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'blur', 'focus', 'cleared'])

const pickerId = computed(() => props.id || `datepicker-${Math.random().toString(36).substr(2, 9)}`)
const isFocused = ref(false)

// Computed props: autoApply und textInput basierend auf range
const computedAutoApply = computed(() => {
  // Wenn explizit gesetzt, verwenden
  if (props.autoApply !== null) return props.autoApply
  // Für beide Fälle true - Picker schließt automatisch
  // Bei Range: erst nach zweiter Datumsauswahl
  return true
})

const computedTextInput = computed(() => {
  // Wenn explizit gesetzt, verwenden
  if (props.textInput !== null) return props.textInput
  // Für Range: false (zu komplex für manuelle Eingabe)
  // Für Single: true (ermöglicht Tippen)
  return !props.range
})

const computedPlaceholder = computed(() => {
  if (props.placeholder) return props.placeholder
  return props.range ? 'Von - Bis Datum wählen' : 'Datum auswählen'
})

// Formats-Objekt für VueDatePicker v12+
const dateFormats = computed(() => ({
  input: 'dd.MM.yyyy',
  preview: 'dd.MM.yyyy'
}))

// Normalisiert jeden Eingabewert (String, Date, Array) zu einem nativen Date-Objekt.
// VueDatePicker erwartet intern immer Date-Objekte — Strings werden zuverlässig
// via parseISO (date-fns) konvertiert, da new Date('string') browserabhängig ist.
const toDate = (val) => {
  if (!val) return null
  if (Array.isArray(val)) return val.map(toDate)
  if (val instanceof Date) return isValid(val) ? val : null
  if (typeof val === 'string') {
    const parsed = parseISO(val)
    return isValid(parsed) ? parsed : null
  }
  return null
}

// Internal value: immer Date | null (oder Date[] bei Range) — kein String intern
const internalValue = ref(toDate(props.modelValue))

// Watch: externe Änderungen normalisieren
watch(() => props.modelValue, (newValue) => {
  internalValue.value = toDate(newValue)
})

const pickerClasses = computed(() => [
  'datepicker',
  {
    'datepicker-error': props.error,
    'datepicker-focused': isFocused.value,
    'datepicker-disabled': props.disabled
  }
])

const inputClassName = computed(() => {
  const classes = ['datepicker-input']
  if (props.error) classes.push('datepicker-input-error')
  if (props.disabled) classes.push('datepicker-input-disabled')
  return classes.join(' ')
})

const handleUpdate = (value) => {
  // VueDatePicker liefert immer Date-Objekte — direkt übernehmen
  internalValue.value = value

  if (!value) {
    emit('update:modelValue', null)
    return
  }

  // Für Date-Range: Start-Zeit auf 00:00:00, End-Zeit auf 23:59:59 setzen
  if (props.range && Array.isArray(value)) {
    // Nur emittieren wenn beide Daten vorhanden sind
    if (value.length === 2 && value[0] && value[1]) {
      const startDate = new Date(value[0])
      startDate.setHours(0, 0, 0, 0)

      const endDate = new Date(value[1])
      endDate.setHours(23, 59, 59, 999)

      emit('update:modelValue', [startDate, endDate])
    } else {
      // Unvollständige Range nicht emittieren
      console.log('Unvollständige Range-Auswahl, warten auf zweites Datum')
    }
  }
  // Für Einzel-Datum: Als YYYY-MM-DD String emittieren (API-kompatibel)
  // Display-Format (dd.MM.yyyy) ist Sache von VueDatePicker via :formats
  else if (!Array.isArray(value)) {
    if (isValid(value)) {
      emit('update:modelValue', format(value, 'yyyy-MM-dd'))
    } else {
      emit('update:modelValue', null)
    }
  }
  else {
    emit('update:modelValue', value)
  }
}

const handleBlur = () => {
  isFocused.value = false
  emit('blur')
}

const handleFocus = () => {
  isFocused.value = true
  emit('focus')
}

const handleCleared = () => {
  emit('cleared')
  emit('update:modelValue', null)
}
</script>

<style scoped>
.datepicker-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-bottom: 1.2rem;
}

.datepicker-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.required {
  color: #ef4444;
  margin-left: 0.25rem;
}

.datepicker-wrapper {
  position: relative;
}

.error-message {
  font-size: 0.875rem;
  color: #ef4444;
}

.hint-message {
  font-size: 0.875rem;
  color: #6b7280;
}

.calendar-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 0.5rem;
}

.clear-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-right: 0.5rem;
  cursor: pointer;
  color: #9ca3af;
  transition: color 0.2s;
}

.clear-icon:hover {
  color: #ef4444;
}
</style>

<style>
/* Global styles for vue-datepicker to match project design */
.dp__theme_light {
  --dp-background-color: #ffffff;
  --dp-text-color: #111827;
  --dp-hover-color: #f3f4f6;
  --dp-hover-text-color: #111827;
  --dp-hover-icon-color: #374151;
  --dp-primary-color: #3b82f6;
  --dp-primary-disabled-color: #93c5fd;
  --dp-primary-text-color: #ffffff;
  --dp-secondary-color: #e5e7eb;
  --dp-border-color: #d1d5db;
  --dp-menu-border-color: #d1d5db;
  --dp-border-color-hover: #3b82f6;
  --dp-disabled-color: #f3f4f6;
  --dp-disabled-color-text: #9ca3af;
  --dp-scroll-bar-background: #f3f4f6;
  --dp-scroll-bar-color: #9ca3af;
  --dp-success-color: #10b981;
  --dp-success-color-disabled: #6ee7b7;
  --dp-icon-color: #6b7280;
  --dp-danger-color: #ef4444;
  --dp-marker-color: #ef4444;
  --dp-tooltip-color: #374151;
  --dp-input-icon-padding: 36px;
  --dp-highlight-color: rgba(59, 130, 246, 0.1);
  --dp-range-between-dates-background-color: rgba(59, 130, 246, 0.1);
  --dp-range-between-dates-text-color: #111827;
  --dp-range-between-border-color: rgba(59, 130, 246, 0.2);
}

.datepicker-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 1rem;
  color: #111827;
  background-color: #ffffff;
  transition: all 0.2s ease-in-out;
}

.datepicker-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.datepicker-input-error {
  border-color: #ef4444 !important;
}

.datepicker-input-error:focus {
  border-color: #ef4444 !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
}

.datepicker-input-disabled {
  background-color: #f3f4f6 !important;
  cursor: not-allowed !important;
  opacity: 0.6 !important;
}

/* Calendar popup styling */
.dp__menu {
  border-radius: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.dp__cell_inner {
  border-radius: 0.375rem;
}

.dp__range_between {
  border-radius: 0;
}

.dp__range_start {
  border-radius: 0.375rem 0 0 0.375rem;
}

.dp__range_end {
  border-radius: 0 0.375rem 0.375rem 0;
}
</style>
