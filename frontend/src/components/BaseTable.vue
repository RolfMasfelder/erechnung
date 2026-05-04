<template>
  <div class="table-container">
    <div v-if="loading" class="table-loading">
      <div class="spinner-large"></div>
      <p>Lädt Daten...</p>
    </div>

    <div v-else-if="data.length === 0" class="table-empty">
      <p>{{ emptyMessage }}</p>
    </div>

    <table v-else class="table">
      <thead>
        <tr>
          <!-- Checkbox column for selection -->
          <th v-if="selectable" class="th-checkbox">
            <input
              type="checkbox"
              :checked="isAllSelected"
              @change="handleSelectAll"
              aria-label="Alle auswählen"
            />
          </th>
          <th
            v-for="column in columns"
            :key="column.key"
            :class="getHeaderClass(column)"
            @click="column.sortable && handleSort(column.key)"
          >
            <div class="th-content">
              {{ column.label }}
              <span v-if="column.sortable" class="sort-indicator">
                <span v-if="sortKey === column.key">
                  {{ sortOrder === 'asc' ? '▲' : '▼' }}
                </span>
                <span v-else class="sort-default">⇅</span>
              </span>
            </div>
          </th>
          <th v-if="actions || $slots.actions" class="th-actions">Aktionen</th>
        </tr>
      </thead>

      <tbody>
        <tr
          v-for="(row, index) in data"
          :key="getRowKey(row, index)"
          :class="{ 'row-selected': selectable && isRowSelected(row) }"
        >
          <!-- Checkbox cell for selection -->
          <td v-if="selectable" class="td-checkbox">
            <input
              type="checkbox"
              :checked="isRowSelected(row)"
              @change="handleRowSelect(row, index, $event)"
              @click.shift="handleShiftSelect(row, index, $event)"
              :aria-label="`Zeile ${getRowKey(row, index)} auswählen`"
            />
          </td>
          <td v-for="column in columns" :key="column.key">
            <slot
              :name="`cell-${column.key}`"
              :row="row"
              :value="getCellValue(row, column.key)"
            >
              {{ formatCellValue(row, column) }}
            </slot>
          </td>

          <td v-if="actions || $slots.actions" class="td-actions">
            <slot name="actions" :row="row">
              <div class="action-buttons">
                <button
                  v-for="action in actions"
                  :key="action.name"
                  :class="['action-btn', `action-${action.variant || 'secondary'}`]"
                  @click="action.handler(row)"
                >
                  {{ action.label }}
                </button>
              </div>
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  columns: {
    type: Array,
    required: true,
    // Format: [{ key: 'id', label: 'ID', sortable: true, formatter: (value) => value }]
  },
  data: {
    type: Array,
    required: true
  },
  actions: {
    type: Array,
    default: null
    // Format: [{ name: 'edit', label: 'Bearbeiten', variant: 'primary', handler: (row) => {} }]
  },
  loading: {
    type: Boolean,
    default: false
  },
  emptyMessage: {
    type: String,
    default: 'Keine Daten vorhanden'
  },
  rowKey: {
    type: String,
    default: 'id'
  },
  // Selection props
  selectable: {
    type: Boolean,
    default: false
  },
  selectedIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['sort', 'select', 'select-all', 'select-range'])

const sortKey = ref('')
const sortOrder = ref('asc')
const lastSelectedIndex = ref(-1)
const headerCheckboxRef = ref(null)

// Convert selectedIds array to Set for efficient lookups
const selectedIdsSet = computed(() => new Set(props.selectedIds))

// Selection computed properties
const isAllSelected = computed(() => {
  if (props.data.length === 0) return false
  return props.data.every(row => selectedIdsSet.value.has(row[props.rowKey]))
})

const isIndeterminate = computed(() => {
  if (props.data.length === 0) return false
  const selectedCount = props.data.filter(row => selectedIdsSet.value.has(row[props.rowKey])).length
  return selectedCount > 0 && selectedCount < props.data.length
})

// Update indeterminate property directly on checkbox element
watch(() => [isIndeterminate.value, isAllSelected.value], () => {
  nextTick(() => {
    const checkbox = document.querySelector('thead input[type="checkbox"]')
    if (checkbox) {
      checkbox.indeterminate = isIndeterminate.value
    }
  })
}, { immediate: true })

// Watch selectedIds changes and force update of checkboxes
watch(() => props.selectedIds, () => {
  nextTick(() => {
    // Force update of all body checkboxes
    const checkboxes = document.querySelectorAll('tbody input[type="checkbox"]')
    checkboxes.forEach((checkbox, index) => {
      if (props.data[index]) {
        const row = props.data[index]
        const shouldBeChecked = selectedIdsSet.value.has(row[props.rowKey])
        if (checkbox.checked !== shouldBeChecked) {
          checkbox.checked = shouldBeChecked
        }
      }
    })
  })
}, { deep: true })

const isRowSelected = (row) => {
  return selectedIdsSet.value.has(row[props.rowKey])
}

// Selection handlers
const handleSelectAll = (event) => {
  const ids = props.data.map(row => row[props.rowKey])
  emit('select-all', { ids, selected: event.target.checked })
}

const handleRowSelect = (row, index, event) => {
  // Update last selected index for shift-click range selection
  if (!event.shiftKey) {
    lastSelectedIndex.value = index
  }
  emit('select', { id: row[props.rowKey], selected: event.target.checked })
}

const handleShiftSelect = (row, index, event) => {
  if (event.shiftKey && lastSelectedIndex.value !== -1) {
    event.preventDefault()
    const startIndex = Math.min(lastSelectedIndex.value, index)
    const endIndex = Math.max(lastSelectedIndex.value, index)
    const ids = props.data.slice(startIndex, endIndex + 1).map(r => r[props.rowKey])
    emit('select-range', { ids })
  }
  lastSelectedIndex.value = index
}

const getHeaderClass = (column) => {
  return {
    'th-sortable': column.sortable,
    'th-sorted': sortKey.value === column.key
  }
}

const handleSort = (key) => {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }

  emit('sort', { key: sortKey.value, order: sortOrder.value })
}

const getRowKey = (row, index) => {
  return row[props.rowKey] || index
}

const getCellValue = (row, key) => {
  return key.split('.').reduce((obj, k) => obj?.[k], row)
}

const formatCellValue = (row, column) => {
  const value = getCellValue(row, column.key)

  if (column.formatter && typeof column.formatter === 'function') {
    return column.formatter(value, row)
  }

  return value ?? '-'
}
</script>

<style scoped>
.table-container {
  width: 100%;
  overflow-x: auto;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.table-loading,
.table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  color: #6b7280;
}

.spinner-large {
  width: 3rem;
  height: 3rem;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background-color: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
}

th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  white-space: nowrap;
}

.th-sortable {
  cursor: pointer;
  user-select: none;
}

.th-sortable:hover {
  background-color: #f3f4f6;
}

.th-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sort-indicator {
  display: inline-flex;
  align-items: center;
  font-size: 0.75rem;
  color: #3b82f6;
}

.sort-default {
  color: #9ca3af;
}

.th-actions {
  text-align: right;
  width: 1%;
}

tbody tr {
  border-bottom: 1px solid #e5e7eb;
}

tbody tr:hover {
  background-color: #f9fafb;
}

tbody tr:last-child {
  border-bottom: none;
}

td {
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: #1f2937;
}

.td-actions {
  text-align: right;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.action-btn {
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-primary {
  background-color: #3b82f6;
  color: white;
}

.action-primary:hover {
  background-color: #2563eb;
}

.action-secondary {
  background-color: #6b7280;
  color: white;
}

.action-secondary:hover {
  background-color: #4b5563;
}

.action-danger {
  background-color: #ef4444;
  color: white;
}

.action-danger:hover {
  background-color: #dc2626;
}

/* Selection styles */
.th-checkbox,
.td-checkbox {
  width: 3rem;
  text-align: center;
  padding: 0.75rem 0.5rem;
}

.th-checkbox input,
.td-checkbox input {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
  accent-color: #3b82f6;
}

.row-selected {
  background-color: #eff6ff !important;
}

.row-selected:hover {
  background-color: #dbeafe !important;
}
</style>
