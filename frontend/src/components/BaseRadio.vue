<template>
  <label
    :class="[
      'base-radio-label',
      {
        'base-radio-label--disabled': disabled,
        'base-radio-label--checked': isChecked
      }
    ]"
  >
    <input
      type="radio"
      :name="name"
      :value="value"
      :checked="isChecked"
      :disabled="disabled"
      :required="required"
      :class="[
        'base-radio-input',
        {
          'base-radio-input--error': error
        }
      ]"
      @change="handleChange"
    />
    <span class="base-radio-mark"></span>
    <span class="base-radio-text">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean],
    default: null
  },
  value: {
    type: [String, Number, Boolean],
    required: true
  },
  name: {
    type: String,
    required: true
  },
  label: {
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
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const isChecked = computed(() => props.modelValue === props.value)

const handleChange = (event) => {
  if (!props.disabled) {
    emit('update:modelValue', props.value)
    emit('change', props.value)
  }
}
</script>

<style scoped>
.base-radio-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  position: relative;
  padding: 0.5rem;
  border-radius: 0.375rem;
  transition: background-color 0.15s ease-in-out;
}

.base-radio-label:hover:not(.base-radio-label--disabled) {
  background-color: #f9fafb;
}

.base-radio-label--checked {
  background-color: #eff6ff;
}

.base-radio-label--disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.base-radio-input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

.base-radio-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #d1d5db;
  border-radius: 50%;
  background-color: #ffffff;
  transition: all 0.15s ease-in-out;
  flex-shrink: 0;
}

.base-radio-input:checked ~ .base-radio-mark {
  border-color: #3b82f6;
}

.base-radio-input:checked ~ .base-radio-mark::after {
  content: '';
  display: block;
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
  background-color: #3b82f6;
}

.base-radio-input:focus ~ .base-radio-mark {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.base-radio-input--error ~ .base-radio-mark {
  border-color: #ef4444;
}

.base-radio-input:disabled ~ .base-radio-mark {
  background-color: #f3f4f6;
  cursor: not-allowed;
}

.base-radio-text {
  margin-left: 0.5rem;
  font-size: 0.875rem;
  color: #374151;
  font-weight: 500;
}
</style>
