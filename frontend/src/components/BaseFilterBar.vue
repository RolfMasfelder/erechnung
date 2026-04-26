<template>
  <div :class="['filter-bar', { 'filter-bar-collapsed': isCollapsed }]">
    <!-- Mobile Toggle Button -->
    <button
      v-if="collapsible"
      class="filter-toggle"
      type="button"
      @click="toggleCollapse"
    >
      <span class="filter-toggle-icon">{{ isCollapsed ? '▼' : '▲' }}</span>
      <span class="filter-toggle-text">
        Filter {{ hasActiveFilters ? `(${activeFilterCount})` : '' }}
      </span>
    </button>

    <div v-show="!isCollapsed || !collapsible" class="filter-bar-content">
      <!-- Search Field -->
      <div v-if="showSearch" class="filter-item filter-search">
        <BaseInput
          :model-value="pendingSearch"
          :placeholder="searchPlaceholder"
          type="text"
          @update:model-value="handleSearchInput"
          @keyup.enter="applySearchNow"
        >
          <template #prefix>
            <span class="search-icon">🔍</span>
          </template>
        </BaseInput>
        <span v-if="isFiltering" class="filter-indicator">...</span>
      </div>

      <!-- Status/Category Dropdown Filters -->
      <div
        v-for="filter in selectFilters"
        :key="filter.key"
        class="filter-item"
      >
        <BaseSelect
          :model-value="filters[filter.key]"
          :options="filter.options"
          :placeholder="filter.placeholder"
          :label="filter.label"
          @update:model-value="(value) => setFilter(filter.key, value)"
        />
      </div>

      <!-- Date Range Filter -->
      <div v-if="showDateRange" class="filter-item filter-date-range">
        <BaseDatePicker
          :model-value="filters[dateRangeKey]"
          :label="dateRangeLabel"
          :placeholder="dateRangePlaceholder"
          range
          :min-date="dateRangeMin"
          :max-date="dateRangeMax"
          @update:model-value="(value) => setFilter(dateRangeKey, value)"
        />
      </div>

      <!-- Custom Filter Slot -->
      <slot name="filters" :filters="filters" :setFilter="setFilter" />

      <!-- Reset Button -->
      <div v-if="showReset && hasActiveFilters" class="filter-reset">
        <BaseButton
          variant="secondary"
          size="sm"
          @click="handleReset"
        >
          <span class="reset-icon">✕</span>
          Filter zurücksetzen
        </BaseButton>
      </div>
    </div>

    <!-- Active Filters Summary (when collapsed) -->
    <div v-if="isCollapsed && hasActiveFilters" class="filter-summary">
      <span class="filter-summary-text">
        {{ activeFilterCount }} Filter aktiv
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, toRefs } from 'vue'
import BaseInput from '@/components/BaseInput.vue'
import BaseSelect from '@/components/BaseSelect.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseDatePicker from '@/components/BaseDatePicker.vue'

const props = defineProps({
  // Filter state from useFilter composable
  filters: {
    type: Object,
    required: true
  },
  pendingSearch: {
    type: String,
    default: ''
  },
  isFiltering: {
    type: Boolean,
    default: false
  },
  hasActiveFilters: {
    type: Boolean,
    default: false
  },
  activeFilterCount: {
    type: Number,
    default: 0
  },

  // Search configuration
  showSearch: {
    type: Boolean,
    default: true
  },
  searchPlaceholder: {
    type: String,
    default: 'Suchen...'
  },

  // Select filters configuration
  selectFilters: {
    type: Array,
    default: () => []
    // Expected format: [{ key: 'status', options: [...], placeholder: '...', label: '...' }]
  },

  // Date range configuration
  showDateRange: {
    type: Boolean,
    default: false
  },
  dateRangeKey: {
    type: String,
    default: 'dateRange'
  },
  dateRangeLabel: {
    type: String,
    default: 'Zeitraum'
  },
  dateRangePlaceholder: {
    type: String,
    default: 'Datum auswählen'
  },
  dateRangeMin: {
    type: Date,
    default: null
  },
  dateRangeMax: {
    type: Date,
    default: null
  },

  // Reset button
  showReset: {
    type: Boolean,
    default: true
  },

  // Collapsible on mobile
  collapsible: {
    type: Boolean,
    default: true
  },
  initialCollapsed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'search',
  'search-immediate',
  'filter-change',
  'reset'
])

// Collapse state for mobile
const isCollapsed = ref(props.initialCollapsed)

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// Methods (delegated to parent via events)
const handleSearchInput = (value) => {
  emit('search', value)
}

const applySearchNow = () => {
  emit('search-immediate')
}

const setFilter = (key, value) => {
  emit('filter-change', { key, value })
}

const handleReset = () => {
  emit('reset')
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background-color: #f9fafb;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.filter-bar-content {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-end;
}

.filter-item {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
}

.filter-search {
  flex: 2;
  min-width: 250px;
  max-width: 400px;
  position: relative;
}

.filter-date-range {
  min-width: 280px;
}

.filter-reset {
  flex: 0 0 auto;
  min-width: auto;
  max-width: none;
  align-self: flex-start;
}

.filter-indicator {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #6b7280;
  font-size: 0.875rem;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.search-icon {
  margin-right: 0.5rem;
}

.reset-icon {
  margin-right: 0.25rem;
}

/* Mobile Toggle */
.filter-toggle {
  display: none;
  width: 100%;
  padding: 0.75rem 1rem;
  background-color: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  text-align: left;
  transition: background-color 0.2s;
}

.filter-toggle:hover {
  background-color: #f3f4f6;
}

.filter-toggle-icon {
  margin-right: 0.5rem;
}

.filter-summary {
  padding: 0.5rem 0;
  font-size: 0.875rem;
  color: #6b7280;
}

.filter-summary-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Responsive: Show toggle on mobile */
@media (max-width: 768px) {
  .filter-toggle {
    display: flex;
    align-items: center;
  }

  .filter-bar-collapsed .filter-bar-content {
    display: none;
  }

  .filter-bar-content {
    flex-direction: column;
  }

  .filter-item {
    min-width: 100%;
    max-width: 100%;
  }

  .filter-search {
    min-width: 100%;
    max-width: 100%;
  }

  .filter-date-range {
    min-width: 100%;
  }
}
</style>
