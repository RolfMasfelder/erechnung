import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ImportModal from '../ImportModal.vue'

// Mock child components
vi.mock('../BaseModal.vue', () => ({
  default: {
    name: 'BaseModal',
    template: `
      <div v-if="isOpen" class="mock-modal">
        <slot></slot>
        <div class="mock-footer"><slot name="footer"></slot></div>
      </div>
    `,
    props: ['isOpen', 'title', 'size'],
    emits: ['close', 'update:isOpen']
  }
}))

vi.mock('../BaseButton.vue', () => ({
  default: {
    name: 'BaseButton',
    template: '<button :class="variant" :disabled="disabled"><slot></slot></button>',
    props: ['variant', 'disabled']
  }
}))

vi.mock('../BaseLoader.vue', () => ({
  default: {
    name: 'BaseLoader',
    template: '<div class="mock-loader"></div>',
    props: ['size']
  }
}))

describe('ImportModal', () => {
  const defaultProps = {
    isOpen: true,
    title: 'Test Import',
    requiredFields: ['name'],
    fieldValidators: {},
    onImport: vi.fn().mockResolvedValue({ imported: 1 })
  }

  const createWrapper = (props = {}) => {
    return mount(ImportModal, {
      props: { ...defaultProps, ...props }
    })
  }

  const createCsvFile = (content) => {
    return new File([content], 'test.csv', { type: 'text/csv' })
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('should render modal when isOpen is true', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.mock-modal').exists()).toBe(true)
    })

    it('should not render modal when isOpen is false', () => {
      const wrapper = createWrapper({ isOpen: false })
      expect(wrapper.find('.mock-modal').exists()).toBe(false)
    })

    it('should show drop zone initially', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.drop-zone').exists()).toBe(true)
    })

    it('should not show preview initially', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.import-preview').exists()).toBe(false)
    })
  })

  describe('drop zone', () => {
    it('should have file input', () => {
      const wrapper = createWrapper()
      const input = wrapper.find('input[type="file"]')
      expect(input.exists()).toBe(true)
      expect(input.attributes('accept')).toContain('.csv')
    })

    it('should show active state on dragenter', async () => {
      const wrapper = createWrapper()
      const dropZone = wrapper.find('.drop-zone')

      await dropZone.trigger('dragenter')
      expect(wrapper.find('.drop-zone--active').exists()).toBe(true)
    })

    it('should remove active state on dragleave', async () => {
      const wrapper = createWrapper()
      const dropZone = wrapper.find('.drop-zone')

      await dropZone.trigger('dragenter')
      await dropZone.trigger('dragleave')
      expect(wrapper.find('.drop-zone--active').exists()).toBe(false)
    })
  })

  describe('file parsing', () => {
    it('should parse CSV file on selection', async () => {
      const wrapper = createWrapper()
      const input = wrapper.find('input[type="file"]')

      const file = createCsvFile('name;email\nTest;test@example.com')

      // Simulate file selection
      Object.defineProperty(input.element, 'files', {
        value: [file]
      })
      await input.trigger('change')
      await nextTick()

      // Should switch to preview
      expect(wrapper.find('.import-preview').exists()).toBe(true)
    })

    it('should show error for empty file', async () => {
      const wrapper = createWrapper()
      const input = wrapper.find('input[type="file"]')

      const file = createCsvFile('')

      Object.defineProperty(input.element, 'files', {
        value: [file]
      })
      await input.trigger('change')
      await nextTick()

      expect(wrapper.find('.import-error').exists()).toBe(true)
    })
  })

  describe('preview', () => {
    const parseValidFile = async (wrapper, content = 'name;email\nTest;test@example.com') => {
      const input = wrapper.find('input[type="file"]')
      const file = createCsvFile(content)
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')
      await nextTick()
    }

    it('should show file name after parsing', async () => {
      const wrapper = createWrapper()
      await parseValidFile(wrapper)

      expect(wrapper.text()).toContain('test.csv')
    })

    it('should show row counts', async () => {
      const wrapper = createWrapper()
      await parseValidFile(wrapper, 'name;email\nTest1;a@b.com\nTest2;c@d.com')

      const stats = wrapper.find('.summary-stats')
      expect(stats.text()).toContain('2')
    })

    it('should show validation errors when present', async () => {
      const wrapper = createWrapper({ requiredFields: ['name', 'email'] })
      await parseValidFile(wrapper, 'name;email\nTest;')

      expect(wrapper.find('.validation-errors').exists()).toBe(true)
    })

    it('should show data preview table', async () => {
      const wrapper = createWrapper()
      await parseValidFile(wrapper)

      expect(wrapper.find('.preview-table').exists()).toBe(true)
    })

    it('should mark required fields in header', async () => {
      const wrapper = createWrapper({ requiredFields: ['name'] })
      await parseValidFile(wrapper)

      expect(wrapper.find('.required-marker').exists()).toBe(true)
    })
  })

  describe('import execution', () => {
    const parseValidFile = async (wrapper, content = 'name;email\nTest;test@example.com') => {
      const input = wrapper.find('input[type="file"]')
      const file = createCsvFile(content)
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')
      await nextTick()
    }

    it('should call onImport when import button clicked', async () => {
      const onImport = vi.fn().mockResolvedValue({ imported: 1 })
      const wrapper = createWrapper({ onImport })
      await parseValidFile(wrapper)

      const importButton = wrapper.findAll('button').find((b) => b.text().includes('importieren'))
      await importButton?.trigger('click')
      await nextTick()

      expect(onImport).toHaveBeenCalled()
    })

    it('should emit success event on successful import', async () => {
      const onImport = vi.fn().mockResolvedValue({ imported: 1 })
      const wrapper = createWrapper({ onImport })
      await parseValidFile(wrapper)

      const importButton = wrapper.findAll('button').find((b) => b.text().includes('importieren'))
      await importButton?.trigger('click')
      await nextTick()

      expect(wrapper.emitted('success')).toBeTruthy()
    })
  })

  describe('modal actions', () => {
    it('should emit close on cancel', async () => {
      const wrapper = createWrapper()

      const cancelButton = wrapper.findAll('button').find((b) => b.text() === 'Abbrechen')
      await cancelButton?.trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('should reset state on close', async () => {
      const wrapper = createWrapper()

      // Parse a file first
      const input = wrapper.find('input[type="file"]')
      const file = createCsvFile('name;email\nTest;test@example.com')
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')
      await nextTick()

      expect(wrapper.find('.import-preview').exists()).toBe(true)

      // Close
      const cancelButton = wrapper.findAll('button').find((b) => b.text() === 'Abbrechen')
      await cancelButton?.trigger('click')

      // Reopen
      await wrapper.setProps({ isOpen: false })
      await wrapper.setProps({ isOpen: true })
      await nextTick()

      // Should show upload zone again
      expect(wrapper.find('.drop-zone').exists()).toBe(true)
    })
  })
})
