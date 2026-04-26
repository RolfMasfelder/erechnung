<template>
  <BaseModal
    :is-open="isOpen"
    :title="title"
    size="lg"
    @close="handleClose"
    @update:is-open="$emit('update:isOpen', $event)"
  >
    <!-- Step 1: File Upload -->
    <div v-if="!hasParsedData" class="import-upload">
      <div
        class="drop-zone"
        :class="{ 'drop-zone--active': isDragging, 'drop-zone--error': importError }"
        @dragenter.prevent="isDragging = true"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <div class="drop-zone__icon">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-12 w-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        </div>
        <p class="drop-zone__text">
          CSV-Datei hierher ziehen oder
          <label class="drop-zone__link">
            <span>durchsuchen</span>
            <input
              ref="fileInput"
              type="file"
              accept=".csv,text/csv,application/vnd.ms-excel"
              class="sr-only"
              @change="handleFileSelect"
            />
          </label>
        </p>
        <p class="drop-zone__hint">Unterstützte Formate: CSV (Semikolon oder Komma getrennt)</p>
      </div>

      <div v-if="importError" class="import-error">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
            clip-rule="evenodd"
          />
        </svg>
        <span>{{ importError }}</span>
      </div>

      <div v-if="isParsing" class="import-loading">
        <BaseLoader size="sm" />
        <span>Datei wird analysiert...</span>
      </div>
    </div>

    <!-- Step 2: Preview & Validation -->
    <div v-else class="import-preview">
      <div class="import-summary">
        <div class="summary-item summary-item--file">
          <span class="summary-label">Datei:</span>
          <span class="summary-value">{{ fileName }}</span>
          <button class="summary-action" @click="resetImport">
            Andere Datei wählen
          </button>
        </div>
        <div class="summary-stats">
          <div class="stat stat--total">
            <span class="stat-value">{{ parsedData.length }}</span>
            <span class="stat-label">Zeilen gesamt</span>
          </div>
          <div class="stat stat--valid">
            <span class="stat-value">{{ validRows.length }}</span>
            <span class="stat-label">Gültig</span>
          </div>
          <div v-if="invalidRows.length > 0" class="stat stat--invalid">
            <span class="stat-value">{{ invalidRows.length }}</span>
            <span class="stat-label">Fehlerhaft</span>
          </div>
        </div>
      </div>

      <!-- Validation Errors -->
      <div v-if="hasErrors" class="validation-errors">
        <div class="errors-header">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          <span>{{ validationErrors.length }} Validierungsfehler gefunden</span>
        </div>
        <div class="errors-list">
          <div
            v-for="(error, index) in displayedErrors"
            :key="index"
            class="error-item"
          >
            <span class="error-row">Zeile {{ error.row }}:</span>
            <span class="error-field" v-if="error.field">{{ error.field }}</span>
            <span class="error-message">{{ error.message }}</span>
          </div>
          <button
            v-if="validationErrors.length > maxDisplayedErrors"
            class="errors-toggle"
            @click="showAllErrors = !showAllErrors"
          >
            {{ showAllErrors ? 'Weniger anzeigen' : `+ ${validationErrors.length - maxDisplayedErrors} weitere Fehler` }}
          </button>
        </div>
      </div>

      <!-- Data Preview -->
      <div class="data-preview">
        <h4 class="preview-title">Datenvorschau</h4>
        <div class="preview-table-container">
          <table class="preview-table">
            <thead>
              <tr>
                <th class="preview-th">Zeile</th>
                <th
                  v-for="header in parsedHeaders"
                  :key="header"
                  class="preview-th"
                >
                  {{ header }}
                  <span v-if="isRequiredField(header)" class="required-marker">*</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in previewRows"
                :key="row._rowIndex"
                :class="{ 'row--invalid': isRowInvalid(row._rowIndex) }"
              >
                <td class="preview-td preview-td--row-num">{{ row._rowIndex }}</td>
                <td
                  v-for="header in parsedHeaders"
                  :key="header"
                  class="preview-td"
                  :class="{ 'cell--error': hasFieldError(row._rowIndex, header) }"
                >
                  {{ row[header] || '-' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="parsedData.length > maxPreviewRows" class="preview-note">
          Zeigt {{ maxPreviewRows }} von {{ parsedData.length }} Zeilen
        </p>
      </div>

      <!-- Import Progress -->
      <div v-if="isImporting" class="import-progress">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: `${importProgress}%` }"
          ></div>
        </div>
        <span class="progress-text">{{ importProgress }}% importiert...</span>
      </div>
    </div>

    <template #footer>
      <div class="import-footer">
        <BaseButton variant="secondary" @click="handleClose">
          Abbrechen
        </BaseButton>
        <div v-if="hasParsedData" class="import-actions">
          <BaseButton
            v-if="hasErrors && validRows.length > 0"
            variant="warning"
            :disabled="isImporting"
            @click="handleImport(true)"
          >
            Nur gültige Zeilen importieren ({{ validRows.length }})
          </BaseButton>
          <BaseButton
            variant="primary"
            :disabled="isImporting || (hasErrors && validRows.length === 0)"
            @click="handleImport(false)"
          >
            <template v-if="!hasErrors">
              {{ parsedData.length }} Zeilen importieren
            </template>
            <template v-else-if="validRows.length === 0">
              Keine gültigen Daten
            </template>
            <template v-else>
              Alle importieren ({{ parsedData.length }})
            </template>
          </BaseButton>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useImport } from '@/composables/useImport'
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'
import BaseLoader from './BaseLoader.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: 'Daten importieren'
  },
  requiredFields: {
    type: Array,
    default: () => []
  },
  fieldValidators: {
    type: Object,
    default: () => ({})
  },
  onImport: {
    type: Function,
    required: true
  }
})

const emit = defineEmits(['update:isOpen', 'close', 'success'])

// Configuration
const maxPreviewRows = 10
const maxDisplayedErrors = 5

// Local state
const isDragging = ref(false)
const showAllErrors = ref(false)
const fileInput = ref(null)

// Use import composable
const {
  isParsing,
  isImporting,
  importProgress,
  importError,
  parsedData,
  parsedHeaders,
  validationErrors,
  fileName,
  hasParsedData,
  hasErrors,
  validRows,
  invalidRows,
  parseFile,
  executeImport,
  resetImport
} = useImport({
  requiredFields: props.requiredFields,
  fieldValidators: props.fieldValidators,
  onImport: props.onImport
})

// Computed
const displayedErrors = computed(() => {
  if (showAllErrors.value) {
    return validationErrors.value
  }
  return validationErrors.value.slice(0, maxDisplayedErrors)
})

const previewRows = computed(() => {
  return parsedData.value.slice(0, maxPreviewRows)
})

// Methods
const isRequiredField = (header) => {
  return props.requiredFields.includes(header)
}

const isRowInvalid = (rowIndex) => {
  return validationErrors.value.some((e) => e.row === rowIndex)
}

const hasFieldError = (rowIndex, field) => {
  return validationErrors.value.some((e) => e.row === rowIndex && e.field === field)
}

const handleFileSelect = async (event) => {
  const file = event.target.files?.[0]
  if (file) {
    await parseFile(file)
  }
}

const handleDrop = async (event) => {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    await parseFile(file)
  }
}

const handleImport = async (skipErrors = false) => {
  const result = await executeImport(skipErrors)
  if (result) {
    emit('success', result)
    handleClose()
  }
}

const handleClose = () => {
  resetImport()
  showAllErrors.value = false
  emit('update:isOpen', false)
  emit('close')
}

// Reset when modal closes
watch(() => props.isOpen, (newValue) => {
  if (!newValue) {
    resetImport()
    showAllErrors.value = false
  }
})
</script>

<style scoped>
.import-upload {
  padding: 1rem;
}

.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 0.5rem;
  padding: 3rem 2rem;
  text-align: center;
  transition: all 0.2s ease;
  background-color: #fafafa;
}

.drop-zone--active {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.drop-zone--error {
  border-color: #ef4444;
  background-color: #fef2f2;
}

.drop-zone__icon {
  color: #9ca3af;
  margin-bottom: 1rem;
  display: flex;
  justify-content: center;
}

.drop-zone__icon svg {
  width: 3rem;
  height: 3rem;
}

.drop-zone__text {
  color: #4b5563;
  margin-bottom: 0.5rem;
}

.drop-zone__link {
  color: #3b82f6;
  cursor: pointer;
  text-decoration: underline;
}

.drop-zone__link:hover {
  color: #2563eb;
}

.drop-zone__hint {
  font-size: 0.875rem;
  color: #9ca3af;
}

.import-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.75rem;
  background-color: #fef2f2;
  border-radius: 0.375rem;
  color: #dc2626;
}

.import-error svg {
  flex-shrink: 0;
}

.import-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
  color: #6b7280;
}

/* Preview */
.import-preview {
  padding: 1rem;
}

.import-summary {
  margin-bottom: 1.5rem;
}

.summary-item--file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.summary-label {
  color: #6b7280;
}

.summary-value {
  font-weight: 500;
  color: #111827;
}

.summary-action {
  color: #3b82f6;
  font-size: 0.875rem;
  background: none;
  border: none;
  cursor: pointer;
  text-decoration: underline;
}

.summary-action:hover {
  color: #2563eb;
}

.summary-stats {
  display: flex;
  gap: 1.5rem;
}

.stat {
  text-align: center;
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  background-color: #f3f4f6;
}

.stat--valid {
  background-color: #d1fae5;
}

.stat--invalid {
  background-color: #fee2e2;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
}

.stat--valid .stat-value {
  color: #059669;
}

.stat--invalid .stat-value {
  color: #dc2626;
}

.stat-label {
  font-size: 0.75rem;
  color: #6b7280;
}

/* Validation Errors */
.validation-errors {
  margin-bottom: 1.5rem;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  background-color: #fef2f2;
}

.errors-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #fecaca;
  font-weight: 500;
  color: #dc2626;
}

.errors-header svg {
  flex-shrink: 0;
}

.errors-list {
  padding: 0.75rem 1rem;
}

.error-item {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.875rem;
}

.error-row {
  font-weight: 500;
  color: #991b1b;
}

.error-field {
  color: #6b7280;
}

.error-field::after {
  content: ':';
}

.error-message {
  color: #dc2626;
}

.errors-toggle {
  margin-top: 0.5rem;
  color: #3b82f6;
  font-size: 0.875rem;
  background: none;
  border: none;
  cursor: pointer;
}

.errors-toggle:hover {
  text-decoration: underline;
}

/* Data Preview */
.data-preview {
  margin-bottom: 1rem;
}

.preview-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.75rem;
}

.preview-table-container {
  overflow-x: auto;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
}

.preview-table {
  width: 100%;
  font-size: 0.75rem;
  border-collapse: collapse;
}

.preview-th {
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-weight: 500;
  background-color: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
}

.required-marker {
  color: #ef4444;
  margin-left: 0.125rem;
}

.preview-td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e5e7eb;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-td--row-num {
  font-weight: 500;
  color: #6b7280;
  background-color: #f9fafb;
}

.row--invalid {
  background-color: #fef2f2;
}

.cell--error {
  background-color: #fee2e2;
  color: #dc2626;
}

.preview-note {
  font-size: 0.75rem;
  color: #9ca3af;
  margin-top: 0.5rem;
  text-align: center;
}

/* Import Progress */
.import-progress {
  margin-top: 1rem;
}

.progress-bar {
  height: 0.5rem;
  background-color: #e5e7eb;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.3s ease;
}

.progress-text {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #6b7280;
  text-align: center;
}

/* Footer */
.import-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.import-actions {
  display: flex;
  gap: 0.75rem;
}
</style>
