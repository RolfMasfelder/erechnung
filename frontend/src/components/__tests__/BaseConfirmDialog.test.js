import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseConfirmDialog from '../BaseConfirmDialog.vue'
import BaseModal from '../BaseModal.vue'
import BaseButton from '../BaseButton.vue'

// Mock child components
vi.mock('../BaseModal.vue', () => ({
  default: {
    name: 'BaseModal',
    template: `
      <div v-if="isOpen" class="base-modal">
        <div class="modal-header"><slot name="title" /></div>
        <div class="modal-body"><slot /></div>
        <div class="modal-footer"><slot name="footer" /></div>
      </div>
    `,
    props: ['isOpen'],
    emits: ['close']
  }
}))

vi.mock('../BaseButton.vue', () => ({
  default: {
    name: 'BaseButton',
    template: '<button @click="$emit(\'click\')" :class="variant"><slot /></button>',
    props: ['variant'],
    emits: ['click']
  }
}))

describe('BaseConfirmDialog', () => {
  it('should render when isOpen is true', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message'
      }
    })

    expect(wrapper.find('.base-modal').exists()).toBe(true)
    expect(wrapper.text()).toContain('Test message')
  })

  it('should not render when isOpen is false', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: false,
        message: 'Test message'
      }
    })

    expect(wrapper.find('.base-modal').exists()).toBe(false)
  })

  it('should display custom title', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        title: 'Custom Title',
        message: 'Test message'
      }
    })

    expect(wrapper.text()).toContain('Custom Title')
  })

  it('should display default title when not provided', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message'
      }
    })

    expect(wrapper.text()).toContain('Bestätigung erforderlich')
  })

  it('should display custom confirm and cancel text', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message',
        confirmText: 'Ja, löschen',
        cancelText: 'Nein, abbrechen'
      }
    })

    expect(wrapper.text()).toContain('Ja, löschen')
    expect(wrapper.text()).toContain('Nein, abbrechen')
  })

  it('should emit confirm event when confirm button clicked', async () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message'
      }
    })

    const buttons = wrapper.findAllComponents({ name: 'BaseButton' })
    const confirmButton = buttons[1] // Second button is confirm
    await confirmButton.trigger('click')

    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('should emit cancel event when cancel button clicked', async () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message'
      }
    })

    const buttons = wrapper.findAllComponents({ name: 'BaseButton' })
    const cancelButton = buttons[0] // First button is cancel
    await cancelButton.trigger('click')

    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('should apply danger variant by default', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message'
      }
    })

    expect(wrapper.find('.icon-danger').exists()).toBe(true)
  })

  it('should apply warning variant when specified', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message',
        variant: 'warning'
      }
    })

    expect(wrapper.find('.icon-warning').exists()).toBe(true)
  })

  it('should apply info variant when specified', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message',
        variant: 'info'
      }
    })

    expect(wrapper.find('.icon-info').exists()).toBe(true)
  })

  it('should pass variant to confirm button', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message',
        variant: 'danger'
      }
    })

    const buttons = wrapper.findAllComponents({ name: 'BaseButton' })
    const confirmButton = buttons[1]
    expect(confirmButton.props('variant')).toBe('danger')
  })

  it('should pass secondary variant to cancel button', () => {
    const wrapper = mount(BaseConfirmDialog, {
      props: {
        isOpen: true,
        message: 'Test message'
      }
    })

    const buttons = wrapper.findAllComponents({ name: 'BaseButton' })
    const cancelButton = buttons[0]
    expect(cancelButton.props('variant')).toBe('secondary')
  })
})
