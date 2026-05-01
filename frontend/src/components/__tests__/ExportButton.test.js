import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import ExportButton from '../ExportButton.vue'

// Mock useExport composable with reactive refs
const mockExportCSV = vi.fn().mockResolvedValue(true)
const mockExportJSON = vi.fn().mockResolvedValue(true)
const mockExportSelected = vi.fn().mockResolvedValue(true)
const mockResetExport = vi.fn()

vi.mock('@/composables/useExport', () => ({
  useExport: () => ({
    isExporting: ref(false),
    exportProgress: ref(0),
    exportError: ref(null),
    exportCSV: mockExportCSV,
    exportJSON: mockExportJSON,
    exportSelected: mockExportSelected,
    resetExport: mockResetExport
  })
}))

// Mock child components
vi.mock('../BaseButton.vue', () => ({
  default: {
    name: 'BaseButton',
    template: '<button :class="variant" :disabled="disabled" @click="$emit(\'click\')"><slot></slot></button>',
    props: ['variant', 'size', 'disabled']
  }
}))

vi.mock('../BaseLoader.vue', () => ({
  default: {
    name: 'BaseLoader',
    template: '<div class="mock-loader"></div>',
    props: ['size']
  }
}))

describe('ExportButton', () => {
  const testData = [
    { id: 1, name: 'Test 1', email: 'test1@example.com' },
    { id: 2, name: 'Test 2', email: 'test2@example.com' },
    { id: 3, name: 'Test 3', email: 'test3@example.com' }
  ]

  const defaultProps = {
    data: testData,
    filename: 'test_export'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  const createWrapper = (props = {}) => {
    return mount(ExportButton, {
      props: { ...defaultProps, ...props },
      global: {
        stubs: {
          Transition: false
        }
      }
    })
  }

  describe('rendering', () => {
    it('should render export button', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('button').exists()).toBe(true)
    })

    it('should show "Exportieren" text by default', () => {
      const wrapper = createWrapper()
      expect(wrapper.text()).toContain('Exportieren')
    })

    it('should not show dropdown initially', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.export-dropdown').exists()).toBe(false)
    })
  })

  describe('dropdown toggle', () => {
    it('should have showDropdown initially false', () => {
      const wrapper = createWrapper()
      expect(wrapper.vm.showDropdown).toBe(false)
    })
  })

  describe('selection count', () => {
    it('should compute hasSelection correctly for Set', () => {
      const wrapper = createWrapper({
        selectedIds: new Set([1, 2])
      })
      expect(wrapper.vm.hasSelection).toBe(true)
      expect(wrapper.vm.selectionCount).toBe(2)
    })

    it('should compute hasSelection correctly for Array', () => {
      const wrapper = createWrapper({
        selectedIds: [1, 3]
      })
      expect(wrapper.vm.hasSelection).toBe(true)
      expect(wrapper.vm.selectionCount).toBe(2)
    })

    it('should return false for empty selection', () => {
      const wrapper = createWrapper({
        selectedIds: new Set()
      })
      expect(wrapper.vm.hasSelection).toBe(false)
      expect(wrapper.vm.selectionCount).toBe(0)
    })

    it('should return false for null selection', () => {
      const wrapper = createWrapper({
        selectedIds: null
      })
      expect(wrapper.vm.hasSelection).toBe(false)
      expect(wrapper.vm.selectionCount).toBe(0)
    })
  })

  describe('disabled state', () => {
    it('should disable button when disabled prop is true', () => {
      const wrapper = createWrapper({ disabled: true })
      expect(wrapper.find('button').attributes('disabled')).toBeDefined()
    })
  })

  describe('export methods', () => {
    it('should call handleExport method for CSV', async () => {
      const wrapper = createWrapper()

      // Manually call the method
      await wrapper.vm.handleExport('csv')
      await flushPromises()

      expect(mockExportCSV).toHaveBeenCalledWith(testData, null)
    })

    it('should call handleExport method for JSON', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.handleExport('json')
      await flushPromises()

      expect(mockExportJSON).toHaveBeenCalledWith(testData)
    })

    it('should call handleExportSelected method', async () => {
      const selectedIds = new Set([1])
      const wrapper = createWrapper({ selectedIds })

      await wrapper.vm.handleExportSelected('csv')
      await flushPromises()

      expect(mockExportSelected).toHaveBeenCalled()
    })

    it('should emit export event on successful CSV export', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.handleExport('csv')
      await flushPromises()

      expect(wrapper.emitted('export')).toBeTruthy()
      expect(wrapper.emitted('export')[0][0]).toEqual({
        format: 'csv',
        count: 3
      })
    })

    it('should emit export event on successful JSON export', async () => {
      const wrapper = createWrapper()

      await wrapper.vm.handleExport('json')
      await flushPromises()

      expect(wrapper.emitted('export')).toBeTruthy()
      expect(wrapper.emitted('export')[0][0]).toEqual({
        format: 'json',
        count: 3
      })
    })

    it('should emit export event for selected items', async () => {
      const wrapper = createWrapper({
        selectedIds: new Set([1])
      })

      await wrapper.vm.handleExportSelected('csv')
      await flushPromises()

      expect(wrapper.emitted('export')).toBeTruthy()
      expect(wrapper.emitted('export')[0][0]).toEqual({
        format: 'csv',
        count: 1,
        selected: true
      })
    })

    it('should use custom columns when provided', async () => {
      const columns = [{ key: 'name', label: 'Kundenname' }]
      const wrapper = createWrapper({ columns })

      await wrapper.vm.handleExport('csv')
      await flushPromises()

      expect(mockExportCSV).toHaveBeenCalledWith(testData, columns)
    })

    it('should emit error event when CSV export fails', async () => {
      mockExportCSV.mockResolvedValueOnce(false)
      const wrapper = createWrapper()

      await wrapper.vm.handleExport('csv')
      await flushPromises()

      expect(wrapper.emitted('error')).toBeTruthy()
    })

    it('should emit error event when JSON export fails', async () => {
      mockExportJSON.mockResolvedValueOnce(false)
      const wrapper = createWrapper()

      await wrapper.vm.handleExport('json')
      await flushPromises()

      expect(wrapper.emitted('error')).toBeTruthy()
    })

    it('should emit error event when exportSelected fails', async () => {
      mockExportSelected.mockResolvedValueOnce(false)
      const wrapper = createWrapper({ selectedIds: new Set([1]) })

      await wrapper.vm.handleExportSelected('csv')
      await flushPromises()

      expect(wrapper.emitted('error')).toBeTruthy()
    })

    it('should emit export for JSON selected items', async () => {
      const wrapper = createWrapper({ selectedIds: [1, 2] })

      await wrapper.vm.handleExportSelected('json')
      await flushPromises()

      expect(wrapper.emitted('export')).toBeTruthy()
      expect(wrapper.emitted('export')[0][0]).toEqual({
        format: 'json',
        count: 2,
        selected: true
      })
    })
  })

  describe('handleClickOutside', () => {
    it('closes dropdown when clicking outside .export-button-wrapper', () => {
      const wrapper = createWrapper()
      wrapper.vm.showDropdown = true

      const event = {
        target: {
          closest: vi.fn().mockReturnValue(null)
        }
      }
      wrapper.vm.handleClickOutside(event)
      expect(wrapper.vm.showDropdown).toBe(false)
    })

    it('keeps dropdown open when clicking inside .export-button-wrapper', () => {
      const wrapper = createWrapper()
      wrapper.vm.showDropdown = true

      const event = {
        target: {
          closest: vi.fn().mockReturnValue(document.createElement('div'))
        }
      }
      wrapper.vm.handleClickOutside(event)
      expect(wrapper.vm.showDropdown).toBe(true)
    })
  })

  describe('selectionCount edge cases', () => {
    it('should return 0 for empty array', () => {
      const wrapper = createWrapper({ selectedIds: [] })
      expect(wrapper.vm.selectionCount).toBe(0)
      expect(wrapper.vm.hasSelection).toBe(false)
    })

    it('should return false for non-Set non-Array selectedIds', () => {
      const wrapper = createWrapper({ selectedIds: null })
      expect(wrapper.vm.hasSelection).toBe(false)
    })
  })
})
