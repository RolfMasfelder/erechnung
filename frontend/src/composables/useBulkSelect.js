import { ref, computed } from 'vue'

/**
 * Composable for managing bulk selection state in tables.
 *
 * @param {Object} options - Configuration options
 * @param {Function} options.getItemId - Function to extract ID from item (default: item => item.id)
 * @param {boolean} options.persistAcrossPages - Whether to keep selection when changing pages (default: false)
 * @returns {Object} Selection state and methods
 */
export function useBulkSelect(options = {}) {
  const {
    getItemId = (item) => item.id,
    persistAcrossPages = false
  } = options

  // Set of selected item IDs
  const selectedIds = ref(new Set())

  // Reference to current page items for "select all" functionality
  const currentItems = ref([])

  /**
   * Check if an item is selected
   */
  const isSelected = (item) => {
    const id = getItemId(item)
    return selectedIds.value.has(id)
  }

  /**
   * Toggle selection of a single item
   */
  const toggleItem = (item) => {
    const id = getItemId(item)
    const newSet = new Set(selectedIds.value)

    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }

    selectedIds.value = newSet
  }

  /**
   * Select a single item
   */
  const selectItem = (item) => {
    const id = getItemId(item)
    if (!selectedIds.value.has(id)) {
      const newSet = new Set(selectedIds.value)
      newSet.add(id)
      selectedIds.value = newSet
    }
  }

  /**
   * Deselect a single item
   */
  const deselectItem = (item) => {
    const id = getItemId(item)
    if (selectedIds.value.has(id)) {
      const newSet = new Set(selectedIds.value)
      newSet.delete(id)
      selectedIds.value = newSet
    }
  }

  /**
   * Select multiple items at once
   */
  const selectItems = (items) => {
    const newSet = new Set(selectedIds.value)
    items.forEach(item => {
      newSet.add(getItemId(item))
    })
    selectedIds.value = newSet
  }

  /**
   * Select all items on current page
   */
  const selectAll = () => {
    selectItems(currentItems.value)
  }

  /**
   * Deselect all items on current page
   */
  const deselectAll = () => {
    const currentIds = new Set(currentItems.value.map(getItemId))
    const newSet = new Set(selectedIds.value)

    currentIds.forEach(id => {
      newSet.delete(id)
    })

    selectedIds.value = newSet
  }

  /**
   * Clear all selections (across all pages)
   */
  const clearSelection = () => {
    selectedIds.value = new Set()
  }

  /**
   * Toggle all items on current page
   */
  const toggleAll = () => {
    if (isAllSelected.value) {
      deselectAll()
    } else {
      selectAll()
    }
  }

  /**
   * Handle shift+click for range selection
   * @param {Object} item - The clicked item
   * @param {number} index - Index of clicked item in currentItems
   * @param {number} lastIndex - Index of last clicked item
   */
  const selectRange = (startIndex, endIndex) => {
    const start = Math.min(startIndex, endIndex)
    const end = Math.max(startIndex, endIndex)

    const itemsInRange = currentItems.value.slice(start, end + 1)
    selectItems(itemsInRange)
  }

  /**
   * Set current page items (call when data changes)
   */
  const setItems = (items) => {
    currentItems.value = items

    // Clear selection when items change if not persisting
    if (!persistAcrossPages) {
      clearSelection()
    }
  }

  /**
   * Update items without clearing selection
   */
  const updateItems = (items) => {
    currentItems.value = items
  }

  /**
   * Get array of selected IDs
   */
  const selectedIdsArray = computed(() => {
    return Array.from(selectedIds.value)
  })

  /**
   * Get selected items from current page
   */
  const selectedItems = computed(() => {
    return currentItems.value.filter(item => isSelected(item))
  })

  /**
   * Count of selected items
   */
  const selectionCount = computed(() => {
    return selectedIds.value.size
  })

  /**
   * Check if any items are selected
   */
  const hasSelection = computed(() => {
    return selectedIds.value.size > 0
  })

  /**
   * Check if all current page items are selected
   */
  const isAllSelected = computed(() => {
    if (currentItems.value.length === 0) return false

    return currentItems.value.every(item => isSelected(item))
  })

  /**
   * Check if some (but not all) current page items are selected
   */
  const isIndeterminate = computed(() => {
    if (currentItems.value.length === 0) return false

    const selectedCount = currentItems.value.filter(item => isSelected(item)).length
    return selectedCount > 0 && selectedCount < currentItems.value.length
  })

  /**
   * Count of selected items on current page
   */
  const currentPageSelectionCount = computed(() => {
    return currentItems.value.filter(item => isSelected(item)).length
  })

  return {
    // State
    selectedIds,
    currentItems,

    // Computed
    selectedIdsArray,
    selectedItems,
    selectionCount,
    hasSelection,
    isAllSelected,
    isIndeterminate,
    currentPageSelectionCount,

    // Methods
    isSelected,
    toggleItem,
    selectItem,
    deselectItem,
    selectItems,
    selectAll,
    deselectAll,
    clearSelection,
    toggleAll,
    selectRange,
    setItems,
    updateItems
  }
}
