import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BulkActionBar from '../BulkActionBar.vue'
import BaseButton from '../BaseButton.vue'

describe('BulkActionBar', () => {
  const createWrapper = (props = {}, slots = {}) => {
    return mount(BulkActionBar, {
      props: {
        selectionCount: 0,
        ...props
      },
      slots: {
        ...slots
      },
      global: {
        components: {
          BaseButton
        },
        stubs: {
          Transition: false
        }
      }
    })
  }

  describe('visibility', () => {
    it('should not render when show is false', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: false })
      expect(wrapper.find('.bulk-action-bar').exists()).toBe(false)
    })

    it('should render when show is true and selectionCount is greater than 0', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true })
      expect(wrapper.find('.bulk-action-bar').exists()).toBe(true)
    })

    it('should render with multiple selections', () => {
      const wrapper = createWrapper({ selectionCount: 42, show: true })
      expect(wrapper.find('.bulk-action-bar').exists()).toBe(true)
    })
  })

  describe('selection count display', () => {
    it('should display singular text for 1 selection', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true })
      expect(wrapper.text()).toContain('1')
      expect(wrapper.text()).toContain('Element ausgewählt')
    })

    it('should display plural text for multiple selections', () => {
      const wrapper = createWrapper({ selectionCount: 5, show: true })
      expect(wrapper.text()).toContain('5')
      expect(wrapper.text()).toContain('Elemente ausgewählt')
    })

    it('should update display when count changes', async () => {
      const wrapper = createWrapper({ selectionCount: 3, show: true })
      expect(wrapper.text()).toContain('3')
      expect(wrapper.text()).toContain('Elemente')

      await wrapper.setProps({ selectionCount: 1 })
      expect(wrapper.text()).toContain('1')
      expect(wrapper.text()).toContain('Element ausgewählt')
    })
  })

  describe('clear button', () => {
    it('should render clear button when showClearButton is true', () => {
      const wrapper = createWrapper({ selectionCount: 2, show: true, showClearButton: true })
      const clearBtn = wrapper.find('.clear-button')
      expect(clearBtn.exists()).toBe(true)
      expect(clearBtn.text()).toContain('Auswahl aufheben')
    })

    it('should not render clear button when showClearButton is false', () => {
      const wrapper = createWrapper({ selectionCount: 2, show: true, showClearButton: false })
      const clearBtn = wrapper.find('.clear-button')
      expect(clearBtn.exists()).toBe(false)
    })

    it('should emit clear event when clicked', async () => {
      const wrapper = createWrapper({ selectionCount: 2, show: true, showClearButton: true })
      const clearBtn = wrapper.find('.clear-button')
      await clearBtn.trigger('click')
      expect(wrapper.emitted('clear')).toBeTruthy()
      expect(wrapper.emitted('clear')).toHaveLength(1)
    })
  })

  describe('export button', () => {
    it('should render export button when showExportAction is true', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showExportAction: true })
      expect(wrapper.text()).toContain('Exportieren')
    })

    it('should hide export button when showExportAction is false', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showExportAction: false })
      expect(wrapper.text()).not.toContain('Exportieren')
    })

    it('should emit export event when clicked', async () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showExportAction: true })
      const buttons = wrapper.findAllComponents(BaseButton)
      const exportBtn = buttons.find(b => b.text().includes('Exportieren'))
      expect(exportBtn).toBeTruthy()
      await exportBtn.trigger('click')
      expect(wrapper.emitted('export')).toBeTruthy()
    })
  })

  describe('delete button', () => {
    it('should render delete button when showDeleteAction is true', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showDeleteAction: true })
      expect(wrapper.text()).toContain('Löschen')
    })

    it('should hide delete button when showDeleteAction is false', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showDeleteAction: false })
      expect(wrapper.text()).not.toContain('Löschen')
    })

    it('should emit delete event when clicked', async () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showDeleteAction: true })
      const buttons = wrapper.findAllComponents(BaseButton)
      const deleteBtn = buttons.find(b => b.text().includes('Löschen'))
      expect(deleteBtn).toBeTruthy()
      await deleteBtn.trigger('click')
      expect(wrapper.emitted('delete')).toBeTruthy()
    })
  })

  describe('custom actions', () => {
    it('should render custom actions', () => {
      const wrapper = createWrapper({
        selectionCount: 1,
        show: true,
        customActions: [
          { key: 'archive', label: 'Archivieren', icon: '📁' }
        ]
      })
      expect(wrapper.text()).toContain('Archivieren')
    })

    it('should emit action event with key when custom action clicked', async () => {
      const wrapper = createWrapper({
        selectionCount: 1,
        show: true,
        customActions: [
          { key: 'archive', label: 'Archivieren' }
        ]
      })
      const buttons = wrapper.findAllComponents(BaseButton)
      const archiveBtn = buttons.find(b => b.text().includes('Archivieren'))
      await archiveBtn.trigger('click')
      expect(wrapper.emitted('action')).toBeTruthy()
      expect(wrapper.emitted('action')[0]).toEqual(['archive'])
    })
  })

  describe('custom actions slot', () => {
    it('should render content in actions slot', () => {
      const wrapper = createWrapper(
        { selectionCount: 1, show: true },
        { actions: '<button class="custom-action">Custom</button>' }
      )
      const customBtn = wrapper.find('button.custom-action')
      expect(customBtn.exists()).toBe(true)
    })
  })

  describe('styling', () => {
    it('should have correct base classes', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true })
      const bar = wrapper.find('.bulk-action-bar')
      expect(bar.classes()).toContain('bulk-action-bar')
    })

    it('should have selection info section', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true })
      expect(wrapper.find('.selection-info').exists()).toBe(true)
    })

    it('should have actions section', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true })
      expect(wrapper.find('.bulk-actions').exists()).toBe(true)
    })
  })

  describe('accessibility', () => {
    it('should use semantic button elements', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true })
      const buttons = wrapper.findAll('button')
      expect(buttons.length).toBeGreaterThan(0)
    })
  })

  describe('transition behavior', () => {
    it('should have transition wrapper', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true })
      // Transition is present - content should be rendered
      expect(wrapper.find('.bulk-action-bar').exists()).toBe(true)
    })
  })

  describe('props validation', () => {
    it('should accept selectionCount as number', () => {
      const wrapper = createWrapper({ selectionCount: 100, show: true })
      expect(wrapper.text()).toContain('100')
    })

    it('should accept showExportAction prop', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showExportAction: true })
      expect(wrapper.text()).toContain('Exportieren')
    })

    it('should accept showDeleteAction prop', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showDeleteAction: true })
      expect(wrapper.text()).toContain('Löschen')
    })

    it('should accept showClearButton prop', () => {
      const wrapper = createWrapper({ selectionCount: 1, show: true, showClearButton: true })
      expect(wrapper.find('.clear-button').exists()).toBe(true)
    })
  })
})
