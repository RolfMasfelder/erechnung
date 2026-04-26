<template>
  <div
    v-if="isOpen"
    ref="overlayRef"
    class="modal-overlay"
    @click.self="handleOverlayClick"
  >
    <div
      class="modal-container"
      :class="sizeClass"
      role="dialog"
      aria-modal="true"
    >
      <div class="modal-header">
        <h2 class="modal-title">
          <slot name="title">{{ title }}</slot>
        </h2>
        <button
          v-if="closable"
          class="modal-close"
          @click="handleClose"
          aria-label="Schließen"
        >
          ✕
        </button>
      </div>

      <div class="modal-body">
        <slot></slot>
      </div>

      <div v-if="$slots.footer" class="modal-footer">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onUnmounted, ref, onMounted } from 'vue'

// Global modal stack to track open modals
if (!window.__modalStack__) {
  window.__modalStack__ = []
  window.__modalIdCounter__ = 0

  // Single global ESC key handler
  window.__modalEscapeHandler__ = (event) => {
    if (event.key === 'Escape' && window.__modalStack__.length > 0) {
      // Get the topmost modal's close function
      const topModal = window.__modalStack__[window.__modalStack__.length - 1]
      if (topModal && topModal.closeHandler) {
        topModal.closeHandler()
      }
    }
  }

  document.addEventListener('keydown', window.__modalEscapeHandler__)
}

const overlayRef = ref(null)
const modalId = ref(null)

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: ''
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg', 'xl', 'full'].includes(value)
  },
  closable: {
    type: Boolean,
    default: true
  },
  closeOnOverlay: {
    type: Boolean,
    default: true
  },
  closeOnEsc: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close', 'update:isOpen'])

const sizeClass = computed(() => `modal-${props.size}`)

const handleClose = () => {
  emit('update:isOpen', false)
  emit('close')
}

const handleOverlayClick = () => {
  if (props.closeOnOverlay) {
    handleClose()
  }
}

watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    // Add to modal stack when opening
    if (!modalId.value) {
      modalId.value = ++window.__modalIdCounter__
    }

    // Remove if already exists (shouldn't happen but safety)
    const existingIndex = window.__modalStack__.findIndex(m => m.id === modalId.value)
    if (existingIndex > -1) {
      window.__modalStack__.splice(existingIndex, 1)
    }

    const modalEntry = {
      id: modalId.value,
      closeHandler: props.closeOnEsc ? handleClose : null,
      closeOnEsc: props.closeOnEsc
    }

    window.__modalStack__.push(modalEntry)
    document.body.style.overflow = 'hidden'
  } else {
    // Remove from modal stack when closing
    const index = window.__modalStack__.findIndex(m => m.id === modalId.value)
    if (index > -1) {
      window.__modalStack__.splice(index, 1)
    }

    // Restore scroll only if no other modals are open
    if (window.__modalStack__.length === 0) {
      document.body.style.overflow = ''
    }
  }
}, { immediate: true })

onMounted(() => {
  // Assign a unique ID when component is mounted
  if (!modalId.value) {
    modalId.value = ++window.__modalIdCounter__
  }
})

onUnmounted(() => {
  // Clean up from modal stack
  if (modalId.value) {
    const index = window.__modalStack__.findIndex(m => m.id === modalId.value)
    if (index > -1) {
      window.__modalStack__.splice(index, 1)
    }
  }

  // Restore scroll only if no other modals are open
  if (window.__modalStack__.length === 0) {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
  animation: fadeIn 0.2s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-container {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.2s ease-in-out;
}

@keyframes slideIn {
  from {
    transform: translateY(-1rem);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-sm {
  width: 100%;
  max-width: 28rem;
}

.modal-md {
  width: 100%;
  max-width: 40rem;
}

.modal-lg {
  width: 100%;
  max-width: 56rem;
}

.modal-xl {
  width: 100%;
  max-width: 72rem;
}

.modal-full {
  width: 95vw;
  height: 95vh;
  max-height: 95vh;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0.25rem;
  line-height: 1;
  transition: color 0.2s;
}

.modal-close:hover {
  color: #111827;
}

.modal-body {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
}
</style>
