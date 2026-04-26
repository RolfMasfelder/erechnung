<template>
  <BaseModal :isOpen="isOpen" @close="handleCancel">
    <template #title>{{ title }}</template>

    <div class="confirm-dialog-content">
      <div class="confirm-dialog-icon">
        <svg
          v-if="variant === 'danger'"
          class="icon icon-danger"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <svg
          v-else-if="variant === 'warning'"
          class="icon icon-warning"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <svg
          v-else
          class="icon icon-info"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>

      <p class="confirm-dialog-message">{{ message }}</p>
    </div>

    <template #footer>
      <BaseButton variant="secondary" @click="handleCancel">
        {{ cancelText }}
      </BaseButton>
      <BaseButton :variant="variant" @click="handleConfirm">
        {{ confirmText }}
      </BaseButton>
    </template>
  </BaseModal>
</template>

<script setup>
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'

defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Bestätigung erforderlich'
  },
  message: {
    type: String,
    required: true
  },
  variant: {
    type: String,
    default: 'danger',
    validator: (value) => ['danger', 'warning', 'info'].includes(value)
  },
  confirmText: {
    type: String,
    default: 'Bestätigen'
  },
  cancelText: {
    type: String,
    default: 'Abbrechen'
  }
})

const emit = defineEmits(['confirm', 'cancel'])

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<style scoped>
.confirm-dialog-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 0;
}

.confirm-dialog-icon {
  flex-shrink: 0;
}

.icon {
  width: 3rem;
  height: 3rem;
}

.icon-danger {
  color: rgb(220, 38, 38);
}

.icon-warning {
  color: rgb(234, 179, 8);
}

.icon-info {
  color: rgb(59, 130, 246);
}

.confirm-dialog-message {
  flex: 1;
  color: rgb(55, 65, 81);
  font-size: 0.9375rem;
  line-height: 1.5;
  margin: 0;
  padding-top: 0.5rem;
}
</style>
