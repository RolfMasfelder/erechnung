import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

/**
 * Composable for managing filter state with URL synchronization and debouncing.
 *
 * @param {Object} options - Configuration options
 * @param {Object} options.defaultFilters - Default filter values
 * @param {number} options.debounceMs - Debounce delay for search (default: 300ms)
 * @param {boolean} options.syncUrl - Whether to sync filters with URL query params (default: true)
 * @param {Function} options.onFilterChange - Callback when filters change
 * @returns {Object} Filter state and methods
 */
export function useFilter(options = {}) {
  const {
    defaultFilters = {},
    debounceMs = 300,
    syncUrl = true,
    onFilterChange = null
  } = options

  const router = useRouter()
  const route = useRoute()

  // Filter state
  const filters = ref({ ...defaultFilters })
  const pendingSearch = ref('')
  const isFiltering = ref(false)

  // Debounce timer
  let debounceTimer = null

  /**
   * Initialize filters from URL query parameters
   */
  const initFromUrl = () => {
    if (!syncUrl) return

    const query = route.query
    const initialFilters = { ...defaultFilters }

    Object.keys(defaultFilters).forEach(key => {
      if (query[key] !== undefined) {
        // Handle array values (for multi-select filters)
        if (Array.isArray(defaultFilters[key])) {
          initialFilters[key] = Array.isArray(query[key]) ? query[key] : [query[key]]
        }
        // Handle boolean values
        else if (typeof defaultFilters[key] === 'boolean') {
          initialFilters[key] = query[key] === 'true'
        }
        // Handle number values
        else if (typeof defaultFilters[key] === 'number') {
          initialFilters[key] = Number(query[key])
        }
        // Handle date values (ISO string)
        else if (defaultFilters[key] instanceof Date) {
          initialFilters[key] = new Date(query[key])
        }
        // String values
        else {
          initialFilters[key] = query[key]
        }
      }
    })

    filters.value = initialFilters
  }

  /**
   * Format date to YYYY-MM-DD without timezone issues
   */
  const formatDateForUrl = (date) => {
    const d = new Date(date)
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  /**
   * Sync current filters to URL query parameters
   */
  const syncToUrl = () => {
    if (!syncUrl) return

    const query = {}

    Object.entries(filters.value).forEach(([key, value]) => {
      // Only include non-default, non-empty values
      if (value !== defaultFilters[key] && value !== '' && value !== null && value !== undefined) {
        // Handle Date objects
        if (value instanceof Date) {
          query[key] = formatDateForUrl(value)
        }
        // Handle arrays (for date ranges or multi-select)
        else if (Array.isArray(value)) {
          if (value.length > 0) {
            // For date ranges from DatePicker
            if (value[0] instanceof Date) {
              query[key] = value.map(d => formatDateForUrl(d)).join(',')
            } else {
              query[key] = value
            }
          }
        }
        else {
          query[key] = String(value)
        }
      }
    })

    try {
      router.replace({ query }).catch(() => {})
    } catch {
      // Ignore router errors in test environment
    }
  }

  /**
   * Update a single filter value
   */
  const setFilter = (key, value) => {
    filters.value[key] = value
  }

  /**
   * Update multiple filter values at once
   */
  const setFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  /**
   * Handle search input with debouncing
   */
  const handleSearch = (value) => {
    pendingSearch.value = value
    isFiltering.value = true

    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }

    debounceTimer = setTimeout(() => {
      filters.value.search = value
      isFiltering.value = false
    }, debounceMs)
  }

  /**
   * Apply search immediately without debouncing
   */
  const applySearchNow = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    filters.value.search = pendingSearch.value
    isFiltering.value = false
  }

  /**
   * Reset all filters to default values
   */
  const resetFilters = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
    filters.value = { ...defaultFilters }
    pendingSearch.value = ''
    isFiltering.value = false
  }

  /**
   * Check if any filter is active (different from default)
   */
  const hasActiveFilters = computed(() => {
    return Object.keys(defaultFilters).some(key => {
      const current = filters.value[key]
      const defaultVal = defaultFilters[key]

      // Handle arrays
      if (Array.isArray(current) && Array.isArray(defaultVal)) {
        return JSON.stringify(current) !== JSON.stringify(defaultVal)
      }

      // Handle dates
      if (current instanceof Date && defaultVal instanceof Date) {
        return current.getTime() !== defaultVal.getTime()
      }

      return current !== defaultVal
    })
  })

  /**
   * Get count of active filters
   */
  const activeFilterCount = computed(() => {
    return Object.keys(defaultFilters).filter(key => {
      const current = filters.value[key]
      const defaultVal = defaultFilters[key]

      if (current === defaultVal) return false
      if (current === '' || current === null || current === undefined) return false
      if (Array.isArray(current) && current.length === 0) return false

      return true
    }).length
  })

  /**
   * Build query params object for API requests
   */
  const queryParams = computed(() => {
    const params = {}

    Object.entries(filters.value).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        // Handle Date objects
        if (value instanceof Date) {
          params[key] = formatDateForUrl(value)
        }
        // Handle date range arrays - Konvertiere zu Django-Lookup-Syntax
        else if (Array.isArray(value) && value.length === 2 && value[0] instanceof Date) {
          // Für dateRange: Verwende issue_date__gte und issue_date__lte
          // (Backend-kompatibel mit Django FilterSet)
          const fieldName = key === 'dateRange' ? 'issue_date' : key
          params[`${fieldName}__gte`] = formatDateForUrl(value[0])
          params[`${fieldName}__lte`] = formatDateForUrl(value[1])
        }
        // Handle other arrays
        else if (Array.isArray(value) && value.length > 0) {
          params[key] = value.join(',')
        }
        // Regular values
        else if (!Array.isArray(value) || value.length > 0) {
          params[key] = value
        }
      }
    })

    return params
  })

  // Watch for filter changes and sync to URL
  watch(
    filters,
    () => {
      syncToUrl()
      if (onFilterChange) {
        onFilterChange(filters.value)
      }
    },
    { deep: true }
  )

  // Initialize from URL on mount
  onMounted(() => {
    initFromUrl()
  })

  return {
    // State
    filters,
    pendingSearch,
    isFiltering,

    // Computed
    hasActiveFilters,
    activeFilterCount,
    queryParams,

    // Methods
    setFilter,
    setFilters,
    handleSearch,
    applySearchNow,
    resetFilters,
    initFromUrl,
    syncToUrl
  }
}
