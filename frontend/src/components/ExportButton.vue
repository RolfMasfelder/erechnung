<template>
  <div class="export-button-wrapper">
    <BaseButton
      :variant="variant"
      :size="size"
      :disabled="disabled || isExporting"
      @click="showDropdown = !showDropdown"
    >
      <slot>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="export-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        <span>Exportieren</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="dropdown-arrow"
          :class="{ 'dropdown-arrow--open': showDropdown }"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </slot>
    </BaseButton>

    <Transition name="dropdown">
      <div v-if="showDropdown" class="export-dropdown" @click.stop>
        <button class="export-option" @click="handleExport('csv')">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="option-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <span>CSV: Alle Daten</span>
        </button>
        <button class="export-option" @click="handleExport('json')">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="option-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
            />
          </svg>
          <span>JSON: Alle Daten</span>
        </button>
        <div v-if="hasSelection" class="export-divider"></div>
        <button v-if="hasSelection" class="export-option" @click="handleExportSelected('csv')">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="option-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
            />
          </svg>
          <span>CSV: Auswahl ({{ selectionCount }})</span>
        </button>
        <button v-if="hasSelection" class="export-option" @click="handleExportSelected('json')">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="option-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
            />
          </svg>
          <span>JSON: Auswahl ({{ selectionCount }})</span>
        </button>
      </div>
    </Transition>

    <!-- Progress overlay -->
    <div v-if="isExporting" class="export-progress">
      <div class="progress-content">
        <BaseLoader size="sm" />
        <span>{{ exportProgress }}% exportiert...</span>
      </div>
    </div>

    <!-- Error toast -->
    <Transition name="toast">
      <div v-if="exportError" class="export-error">
        <span>{{ exportError }}</span>
        <button class="error-close" @click="resetExport">✕</button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useExport } from '@/composables/useExport'
import BaseButton from './BaseButton.vue'
import BaseLoader from './BaseLoader.vue'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    default: null
  },
  filename: {
    type: String,
    default: 'export'
  },
  selectedIds: {
    type: [Set, Array],
    default: null
  },
  idKey: {
    type: String,
    default: 'id'
  },
  fetchData: {
    type: Function,
    default: null
  },
  variant: {
    type: String,
    default: 'secondary'
  },
  size: {
    type: String,
    default: 'md'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['export', 'error'])

// Local state
const showDropdown = ref(false)

// Use export composable
const {
  isExporting,
  exportProgress,
  exportError,
  exportCSV,
  exportJSON,
  exportSelected,
  resetExport
} = useExport({
  filename: props.filename,
  fetchData: props.fetchData
})

// Computed
const hasSelection = computed(() => {
  if (!props.selectedIds) return false
  if (props.selectedIds instanceof Set) return props.selectedIds.size > 0
  return Array.isArray(props.selectedIds) && props.selectedIds.length > 0
})

const selectionCount = computed(() => {
  if (!props.selectedIds) return 0
  if (props.selectedIds instanceof Set) return props.selectedIds.size
  return props.selectedIds.length
})

// Methods
const handleExport = async (format) => {
  showDropdown.value = false

  let success = false
  if (format === 'csv') {
    success = await exportCSV(props.data, props.columns)
  } else {
    success = await exportJSON(props.data)
  }

  if (success) {
    emit('export', { format, count: props.data.length })
  } else {
    emit('error', exportError.value)
  }
}

const handleExportSelected = async (format) => {
  showDropdown.value = false

  const success = await exportSelected(
    props.data,
    props.selectedIds,
    props.idKey,
    props.columns,
    format
  )

  if (success) {
    emit('export', { format, count: selectionCount.value, selected: true })
  } else {
    emit('error', exportError.value)
  }
}

// Close dropdown on outside click
const handleClickOutside = (event) => {
  if (!event.target.closest('.export-button-wrapper')) {
    showDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.export-button-wrapper {
  position: relative;
  display: inline-block;
}

.export-icon {
  width: 1rem;
  height: 1rem;
  margin-right: 0.5rem;
}

.dropdown-arrow {
  width: 1rem;
  height: 1rem;
  margin-left: 0.5rem;
  transition: transform 0.2s ease;
}

.dropdown-arrow--open {
  transform: rotate(180deg);
}

.export-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.25rem;
  min-width: 12rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  z-index: 50;
  overflow: hidden;
}

.export-option {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  color: #374151;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background-color 0.15s ease;
}

.export-option:hover {
  background-color: #f3f4f6;
}

.option-icon {
  width: 1.125rem;
  height: 1.125rem;
  margin-right: 0.75rem;
  color: #6b7280;
}

.export-divider {
  height: 1px;
  background-color: #e5e7eb;
  margin: 0.25rem 0;
}

/* Progress */
.export-progress {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 0.375rem;
}

.progress-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #4b5563;
}

/* Error */
.export-error {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background-color: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  color: #dc2626;
  white-space: nowrap;
}

.error-close {
  padding: 0.125rem;
  background: none;
  border: none;
  cursor: pointer;
  color: #dc2626;
}

/* Transitions */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-0.25rem);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}
</style>
