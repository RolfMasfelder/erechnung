<template>
  <div class="base-checkbox-wrapper">
    <label
      :class="[
        'base-checkbox-label',
        {
          'base-checkbox-label--disabled': disabled
        }
      ]"
    >
      <input
        type="checkbox"
        :checked="modelValue"
        :disabled="disabled"
        :required="required"
        :class="[
          'base-checkbox-input',
          {
            'base-checkbox-input--error': error
          }
        ]"
        @change="handleChange"
      />
      <span class="base-checkbox-checkmark"></span>
      <span class="base-checkbox-text">
        <slot>{{ label }}</slot>
      </span>
    </label>
    <p v-if="error" class="base-checkbox-error">
      {{ error }}
    </p>
    <p v-else-if="hint" class="base-checkbox-hint">
      {{ hint }}
    </p>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
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
  },
  hint: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const handleChange = (event) => {
  const checked = event.target.checked
  emit('update:modelValue', checked)
  emit('change', checked)
}
</script>

<style scoped>
.base-checkbox-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.base-checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  position: relative;
}

.base-checkbox-label--disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.base-checkbox-input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

.base-checkbox-checkmark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #d1d5db;
  border-radius: 0.25rem;
  background-color: #ffffff;
  transition: all 0.15s ease-in-out;
  flex-shrink: 0;
}

.base-checkbox-input:checked ~ .base-checkbox-checkmark {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

.base-checkbox-input:checked ~ .base-checkbox-checkmark::after {
  content: '';
  display: block;
  width: 0.4rem;
  height: 0.7rem;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.base-checkbox-input:focus ~ .base-checkbox-checkmark {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.base-checkbox-input--error ~ .base-checkbox-checkmark {
  border-color: #ef4444;
}

.base-checkbox-input:disabled ~ .base-checkbox-checkmark {
  background-color: #f3f4f6;
  cursor: not-allowed;
}

.base-checkbox-text {
  margin-left: 0.5rem;
  font-size: 0.875rem;
  color: #374151;
}

.base-checkbox-error {
  font-size: 0.875rem;
  color: #ef4444;
  margin: 0;
  padding-left: 1.75rem;
}

.base-checkbox-hint {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
  padding-left: 1.75rem;
}
</style>
