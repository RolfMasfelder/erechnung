<template>
  <div
    v-if="show"
    class="alert"
    :class="alertClasses"
    role="alert"
  >
    <div class="alert-icon">{{ icon }}</div>

    <div class="alert-content">
      <h4 v-if="title" class="alert-title">{{ title }}</h4>
      <div class="alert-message">
        <slot>{{ message }}</slot>
      </div>
    </div>

    <button
      v-if="closable"
      class="alert-close"
      @click="handleClose"
      aria-label="Schließen"
    >
      ✕
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'info',
    validator: (value) => ['success', 'info', 'warning', 'error'].includes(value)
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  },
  closable: {
    type: Boolean,
    default: true
  },
  autoDismiss: {
    type: Number,
    default: 0 // 0 = no auto-dismiss, otherwise milliseconds
  }
})

const emit = defineEmits(['close'])

const show = ref(true)

const alertClasses = computed(() => [`alert-${props.type}`])

const icon = computed(() => {
  const icons = {
    success: '✓',
    info: 'ℹ',
    warning: '⚠',
    error: '✕'
  }
  return icons[props.type] || 'ℹ'
})

const handleClose = () => {
  show.value = false
  emit('close')
}

let autoDismissTimer = null

watch(() => props.autoDismiss, (value) => {
  if (value > 0) {
    autoDismissTimer = setTimeout(() => {
      handleClose()
    }, value)
  }
}, { immediate: true })

// Cleanup
const cleanup = () => {
  if (autoDismissTimer) {
    clearTimeout(autoDismissTimer)
  }
}

// Vue 3 onUnmounted equivalent
import { onUnmounted } from 'vue'
onUnmounted(cleanup)
</script>

<style scoped>
.alert {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.375rem;
  border-width: 1px;
  border-style: solid;
  margin-bottom: 1rem;
  animation: slideDown 0.3s ease-in-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-0.5rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.alert-icon {
  flex-shrink: 0;
  font-size: 1.25rem;
  font-weight: bold;
}

.alert-content {
  flex: 1;
}

.alert-title {
  margin: 0 0 0.25rem 0;
  font-size: 0.875rem;
  font-weight: 600;
}

.alert-message {
  font-size: 0.875rem;
  line-height: 1.5;
}

.alert-close {
  flex-shrink: 0;
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.alert-close:hover {
  opacity: 1;
}

/* Success */
.alert-success {
  background-color: #d1fae5;
  border-color: #10b981;
  color: #065f46;
}

.alert-success .alert-icon {
  color: #10b981;
}

/* Info */
.alert-info {
  background-color: #dbeafe;
  border-color: #3b82f6;
  color: #1e40af;
}

.alert-info .alert-icon {
  color: #3b82f6;
}

/* Warning */
.alert-warning {
  background-color: #fef3c7;
  border-color: #f59e0b;
  color: #92400e;
}

.alert-warning .alert-icon {
  color: #f59e0b;
}

/* Error */
.alert-error {
  background-color: #fee2e2;
  border-color: #ef4444;
  color: #991b1b;
}

.alert-error .alert-icon {
  color: #ef4444;
}
</style>
