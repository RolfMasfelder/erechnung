import { describe, it, expect, beforeEach } from 'vitest'
import { useBulkSelect } from '../useBulkSelect'

describe('useBulkSelect', () => {
  let bulkSelect

  // Test data
  const testItems = [
    { id: 1, name: 'Item 1' },
    { id: 2, name: 'Item 2' },
    { id: 3, name: 'Item 3' },
    { id: 4, name: 'Item 4' },
    { id: 5, name: 'Item 5' }
  ]

  beforeEach(() => {
    bulkSelect = useBulkSelect()
  })

  describe('initial state', () => {
    it('should initialize with empty selection', () => {
      expect(bulkSelect.selectedIds.value.size).toBe(0)
    })

    it('should have selectionCount of 0', () => {
      expect(bulkSelect.selectionCount.value).toBe(0)
    })

    it('should not have any selection', () => {
      expect(bulkSelect.hasSelection.value).toBe(false)
    })

    it('should not be allSelected without items', () => {
      expect(bulkSelect.isAllSelected.value).toBe(false)
    })

    it('should not be indeterminate without items', () => {
      expect(bulkSelect.isIndeterminate.value).toBe(false)
    })
  })

  describe('toggleItem', () => {
    it('should add item to selection when not selected', () => {
      bulkSelect.toggleItem(testItems[0])
      expect(bulkSelect.isSelected(testItems[0])).toBe(true)
      expect(bulkSelect.selectionCount.value).toBe(1)
    })

    it('should remove item from selection when already selected', () => {
      bulkSelect.toggleItem(testItems[0])
      bulkSelect.toggleItem(testItems[0])
      expect(bulkSelect.isSelected(testItems[0])).toBe(false)
      expect(bulkSelect.selectionCount.value).toBe(0)
    })

    it('should handle multiple items', () => {
      bulkSelect.toggleItem(testItems[0])
      bulkSelect.toggleItem(testItems[1])
      bulkSelect.toggleItem(testItems[2])
      expect(bulkSelect.selectionCount.value).toBe(3)
      expect(bulkSelect.isSelected(testItems[0])).toBe(true)
      expect(bulkSelect.isSelected(testItems[1])).toBe(true)
      expect(bulkSelect.isSelected(testItems[2])).toBe(true)
    })

    it('should handle string IDs with custom getItemId', () => {
      const customSelect = useBulkSelect({ getItemId: (item) => item.uuid })
      const item = { uuid: 'abc-123', name: 'Test' }
      customSelect.toggleItem(item)
      expect(customSelect.isSelected(item)).toBe(true)
    })
  })

  describe('selectItem', () => {
    it('should add item to selection', () => {
      bulkSelect.selectItem(testItems[0])
      expect(bulkSelect.isSelected(testItems[0])).toBe(true)
    })

    it('should not duplicate when called twice', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.selectItem(testItems[0])
      expect(bulkSelect.selectionCount.value).toBe(1)
    })
  })

  describe('deselectItem', () => {
    it('should remove item from selection', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.deselectItem(testItems[0])
      expect(bulkSelect.isSelected(testItems[0])).toBe(false)
    })

    it('should do nothing if item not selected', () => {
      bulkSelect.deselectItem(testItems[0])
      expect(bulkSelect.selectionCount.value).toBe(0)
    })
  })

  describe('selectItems', () => {
    it('should select all provided items', () => {
      bulkSelect.selectItems(testItems)
      expect(bulkSelect.selectionCount.value).toBe(5)
      expect(bulkSelect.isSelected(testItems[0])).toBe(true)
      expect(bulkSelect.isSelected(testItems[4])).toBe(true)
    })

    it('should merge with existing selection', () => {
      bulkSelect.selectItem({ id: 10, name: 'Other' })
      bulkSelect.selectItems(testItems.slice(0, 3))
      expect(bulkSelect.selectionCount.value).toBe(4)
    })

    it('should handle empty array', () => {
      bulkSelect.selectItems([])
      expect(bulkSelect.selectionCount.value).toBe(0)
    })
  })

  describe('clearSelection', () => {
    it('should clear all selections', () => {
      bulkSelect.selectItems(testItems)
      bulkSelect.clearSelection()
      expect(bulkSelect.selectionCount.value).toBe(0)
    })

    it('should handle already empty selection', () => {
      bulkSelect.clearSelection()
      expect(bulkSelect.selectionCount.value).toBe(0)
    })
  })

  describe('selectAll and deselectAll', () => {
    beforeEach(() => {
      bulkSelect.updateItems(testItems)
    })

    it('should select all current page items', () => {
      bulkSelect.selectAll()
      expect(bulkSelect.selectionCount.value).toBe(5)
    })

    it('should deselect all current page items', () => {
      bulkSelect.selectAll()
      bulkSelect.deselectAll()
      expect(bulkSelect.selectionCount.value).toBe(0)
    })

    it('should keep selections from other pages when deselecting', () => {
      const otherItem = { id: 100, name: 'Other Page' }
      bulkSelect.selectItem(otherItem)
      bulkSelect.selectAll()
      expect(bulkSelect.selectionCount.value).toBe(6)

      bulkSelect.deselectAll()
      expect(bulkSelect.selectionCount.value).toBe(1)
      expect(bulkSelect.isSelected(otherItem)).toBe(true)
    })
  })

  describe('toggleAll', () => {
    beforeEach(() => {
      bulkSelect.updateItems(testItems)
    })

    it('should select all when none selected', () => {
      bulkSelect.toggleAll()
      expect(bulkSelect.isAllSelected.value).toBe(true)
    })

    it('should deselect all when all selected', () => {
      bulkSelect.selectAll()
      bulkSelect.toggleAll()
      expect(bulkSelect.selectionCount.value).toBe(0)
    })

    it('should select all when some selected (indeterminate)', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.toggleAll()
      expect(bulkSelect.isAllSelected.value).toBe(true)
    })
  })

  describe('selectRange', () => {
    beforeEach(() => {
      bulkSelect.updateItems(testItems)
    })

    it('should select items in range', () => {
      bulkSelect.selectRange(1, 3)
      expect(bulkSelect.selectionCount.value).toBe(3)
      expect(bulkSelect.isSelected(testItems[1])).toBe(true)
      expect(bulkSelect.isSelected(testItems[2])).toBe(true)
      expect(bulkSelect.isSelected(testItems[3])).toBe(true)
    })

    it('should handle reversed range', () => {
      bulkSelect.selectRange(3, 1)
      expect(bulkSelect.selectionCount.value).toBe(3)
    })

    it('should merge with existing selection', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.selectRange(2, 4)
      expect(bulkSelect.selectionCount.value).toBe(4)
    })
  })

  describe('isSelected', () => {
    it('should return true for selected item', () => {
      bulkSelect.selectItem(testItems[0])
      expect(bulkSelect.isSelected(testItems[0])).toBe(true)
    })

    it('should return false for unselected item', () => {
      expect(bulkSelect.isSelected(testItems[0])).toBe(false)
    })
  })

  describe('isAllSelected', () => {
    beforeEach(() => {
      bulkSelect.updateItems(testItems)
    })

    it('should return true when all items are selected', () => {
      bulkSelect.selectAll()
      expect(bulkSelect.isAllSelected.value).toBe(true)
    })

    it('should return false when some items are not selected', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.selectItem(testItems[1])
      expect(bulkSelect.isAllSelected.value).toBe(false)
    })

    it('should return false for empty current items', () => {
      bulkSelect.updateItems([])
      expect(bulkSelect.isAllSelected.value).toBe(false)
    })
  })

  describe('isIndeterminate', () => {
    beforeEach(() => {
      bulkSelect.updateItems(testItems)
    })

    it('should return true when some but not all items are selected', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.selectItem(testItems[1])
      expect(bulkSelect.isIndeterminate.value).toBe(true)
    })

    it('should return false when all items are selected', () => {
      bulkSelect.selectAll()
      expect(bulkSelect.isIndeterminate.value).toBe(false)
    })

    it('should return false when no items are selected', () => {
      expect(bulkSelect.isIndeterminate.value).toBe(false)
    })

    it('should return false for empty current items', () => {
      bulkSelect.updateItems([])
      expect(bulkSelect.isIndeterminate.value).toBe(false)
    })
  })

  describe('selectedIdsArray', () => {
    it('should return array of selected IDs', () => {
      bulkSelect.selectItems(testItems.slice(0, 3))
      const result = bulkSelect.selectedIdsArray.value
      expect(result).toHaveLength(3)
      expect(result).toContain(1)
      expect(result).toContain(2)
      expect(result).toContain(3)
    })

    it('should return empty array when nothing selected', () => {
      expect(bulkSelect.selectedIdsArray.value).toEqual([])
    })
  })

  describe('selectedItems', () => {
    beforeEach(() => {
      bulkSelect.updateItems(testItems)
    })

    it('should return selected items from current page', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.selectItem(testItems[2])
      const selected = bulkSelect.selectedItems.value
      expect(selected).toHaveLength(2)
      expect(selected).toContainEqual(testItems[0])
      expect(selected).toContainEqual(testItems[2])
    })
  })

  describe('selectionCount', () => {
    it('should reactively update when items are added', () => {
      expect(bulkSelect.selectionCount.value).toBe(0)
      bulkSelect.selectItem(testItems[0])
      expect(bulkSelect.selectionCount.value).toBe(1)
      bulkSelect.selectItem(testItems[1])
      expect(bulkSelect.selectionCount.value).toBe(2)
    })

    it('should reactively update when items are removed', () => {
      bulkSelect.selectItems(testItems.slice(0, 3))
      expect(bulkSelect.selectionCount.value).toBe(3)
      bulkSelect.deselectItem(testItems[0])
      expect(bulkSelect.selectionCount.value).toBe(2)
    })
  })

  describe('hasSelection', () => {
    it('should return true when items are selected', () => {
      bulkSelect.selectItem(testItems[0])
      expect(bulkSelect.hasSelection.value).toBe(true)
    })

    it('should return false when nothing is selected', () => {
      expect(bulkSelect.hasSelection.value).toBe(false)
    })
  })

  describe('setItems', () => {
    it('should set current items', () => {
      bulkSelect.setItems(testItems)
      expect(bulkSelect.currentItems.value).toEqual(testItems)
    })

    it('should clear selection by default when items change', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.setItems(testItems)
      expect(bulkSelect.selectionCount.value).toBe(0)
    })
  })

  describe('updateItems', () => {
    it('should update items without clearing selection', () => {
      bulkSelect.selectItem(testItems[0])
      bulkSelect.updateItems(testItems)
      expect(bulkSelect.selectionCount.value).toBe(1)
    })
  })

  describe('persistAcrossPages option', () => {
    it('should keep selection when persistAcrossPages is true', () => {
      const persistSelect = useBulkSelect({ persistAcrossPages: true })
      persistSelect.selectItem(testItems[0])
      persistSelect.setItems(testItems)
      expect(persistSelect.selectionCount.value).toBe(1)
    })
  })

  describe('custom getItemId', () => {
    it('should use custom ID extractor', () => {
      const customSelect = useBulkSelect({
        getItemId: (item) => item.customId
      })
      const items = [
        { customId: 'a', name: 'A' },
        { customId: 'b', name: 'B' }
      ]
      customSelect.selectItem(items[0])
      expect(customSelect.selectedIds.value.has('a')).toBe(true)
    })
  })

  describe('complex scenarios', () => {
    it('should handle mixed operations correctly', () => {
      bulkSelect.updateItems(testItems)

      // Select some
      bulkSelect.selectItems(testItems.slice(0, 3))
      expect(bulkSelect.selectionCount.value).toBe(3)

      // Deselect one
      bulkSelect.deselectItem(testItems[1])
      expect(bulkSelect.selectionCount.value).toBe(2)
      expect(bulkSelect.isSelected(testItems[1])).toBe(false)

      // Toggle one
      bulkSelect.toggleItem(testItems[1])
      expect(bulkSelect.isSelected(testItems[1])).toBe(true)

      // Clear all
      bulkSelect.clearSelection()
      expect(bulkSelect.selectionCount.value).toBe(0)
    })

    it('should handle large number of selections', () => {
      const items = Array.from({ length: 1000 }, (_, i) => ({ id: i, name: `Item ${i}` }))
      bulkSelect.selectItems(items)
      expect(bulkSelect.selectionCount.value).toBe(1000)
      expect(bulkSelect.isSelected(items[500])).toBe(true)
    })
  })
})
