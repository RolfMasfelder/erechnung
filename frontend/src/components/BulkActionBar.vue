<template>
  <Transition name="slide-up">
    <div v-if="show" class="bulk-action-bar">
      <div class="bulk-action-content">
        <!-- Selection Info -->
        <div class="selection-info">
          <span class="selection-count">
            <strong>{{ selectionCount }}</strong>
            {{ selectionCount === 1 ? 'Element' : 'Elemente' }} ausgewählt
          </span>

          <button
            v-if="showClearButton"
            type="button"
            class="clear-button"
            @click="handleClear"
          >
            Auswahl aufheben
          </button>
        </div>

        <!-- Action Buttons -->
        <div class="bulk-actions">
          <slot name="actions">
            <!-- Default actions if no slot provided -->
            <BaseButton
              v-if="showExportAction"
              variant="secondary"
              size="sm"
              @click="handleExport"
            >
              <span class="action-icon">📥</span>
              Exportieren
            </BaseButton>

            <BaseButton
              v-for="action in customActions"
              :key="action.key"
              :variant="action.variant || 'secondary'"
              size="sm"
              :disabled="action.disabled"
              @click="handleCustomAction(action)"
            >
              <span v-if="action.icon" class="action-icon">{{ action.icon }}</span>
              {{ action.label }}
            </BaseButton>

            <BaseButton
              v-if="showDeleteAction"
              variant="danger"
              size="sm"
              @click="handleDelete"
            >
              <span class="action-icon">🗑️</span>
              Löschen
            </BaseButton>
          </slot>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import BaseButton from '@/components/BaseButton.vue'

const props = defineProps({
  selectionCount: {
    type: Number,
    required: true
  },
  show: {
    type: Boolean,
    default: true
  },
  showClearButton: {
    type: Boolean,
    default: true
  },
  showDeleteAction: {
    type: Boolean,
    default: true
  },
  showExportAction: {
    type: Boolean,
    default: true
  },
  customActions: {
    type: Array,
    default: () => []
    // Expected format: [{ key: 'archive', label: 'Archivieren', icon: '📁', variant: 'secondary', disabled: false }]
  },
  deleteConfirmMessage: {
    type: String,
    default: 'Möchten Sie die ausgewählten Elemente wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.'
  }
})

const emit = defineEmits([
  'clear',
  'delete',
  'export',
  'action'
])

const handleClear = () => {
  emit('clear')
}

const handleDelete = () => {
  emit('delete')
}

const handleExport = () => {
  emit('export')
}

const handleCustomAction = (action) => {
  emit('action', action.key)
}
</script>

<style scoped>
.bulk-action-bar {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: #1f2937;
  color: #ffffff;
  padding: 0.75rem 1.5rem;
  box-shadow: 0 -4px 6px -1px rgba(0, 0, 0, 0.1), 0 -2px 4px -1px rgba(0, 0, 0, 0.06);
  z-index: 50;
  border-radius: 0.5rem 0.5rem 0 0;
}

.bulk-action-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
  gap: 1rem;
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.selection-count {
  font-size: 0.875rem;
}

.selection-count strong {
  font-size: 1.125rem;
  color: #60a5fa;
}

.clear-button {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: color 0.2s, background-color 0.2s;
}

.clear-button:hover {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.1);
}

.bulk-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.action-icon {
  margin-right: 0.25rem;
}

/* Slide up animation */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .bulk-action-bar {
    padding: 0.75rem 1rem;
  }

  .bulk-action-content {
    flex-direction: column;
    gap: 0.75rem;
  }

  .selection-info {
    width: 100%;
    justify-content: space-between;
  }

  .bulk-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }
}
</style>
