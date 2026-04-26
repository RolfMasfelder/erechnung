<template>
  <div class="base-textarea-wrapper">
    <label v-if="label" :for="id" class="base-textarea-label">
      {{ label }}
      <span v-if="required" class="required-indicator">*</span>
    </label>
    <textarea
      :id="id"
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      :disabled="disabled"
      :required="required"
      :class="[
        'base-textarea',
        {
          'base-textarea--error': error,
          'base-textarea--disabled': disabled
        }
      ]"
      @input="handleInput"
      @blur="$emit('blur')"
      @focus="$emit('focus')"
    />
    <p v-if="error" class="base-textarea-error">
      {{ error }}
    </p>
    <p v-else-if="hint" class="base-textarea-hint">
      {{ hint }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  rows: {
    type: Number,
    default: 4
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
  id: {
    type: String,
    default: () => `textarea-${Math.random().toString(36).substr(2, 9)}`
  }
})

const emit = defineEmits(['update:modelValue', 'blur', 'focus'])

const handleInput = (event) => {
  emit('update:modelValue', event.target.value)
}
</script>

<style scoped>
.base-textarea-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.base-textarea-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.required-indicator {
  color: #ef4444;
  margin-left: 0.25rem;
}

.base-textarea {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  color: #1f2937;
  background-color: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
  resize: vertical;
  font-family: inherit;
}

.base-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.base-textarea--error {
  border-color: #ef4444;
}

.base-textarea--error:focus {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.base-textarea--disabled {
  background-color: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

.base-textarea-error {
  font-size: 0.875rem;
  color: #ef4444;
  margin: 0;
}

.base-textarea-hint {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

.base-textarea::placeholder {
  color: #9ca3af;
}
</style>
