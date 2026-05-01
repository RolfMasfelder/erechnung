import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import BaseModal from '../BaseModal.vue'

describe('BaseModal', () => {
  afterEach(() => {
    // Reset modal stack and body style after each test
    window.__modalStack__ = []
    document.body.style.overflow = ''
    vi.restoreAllMocks()
  })

  describe('rendering', () => {
    it('does not render when isOpen is false', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: false, title: 'Test Modal' }
      })
      expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    })

    it('renders when isOpen is true', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Test Modal' }
      })
      expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('Test Modal')
    })

    it('renders default slot content', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' },
        slots: { default: '<p class="content">Modal Body</p>' }
      })
      expect(wrapper.find('.content').exists()).toBe(true)
      expect(wrapper.text()).toContain('Modal Body')
    })

    it('renders footer slot when provided', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' },
        slots: { footer: '<button class="footer-btn">OK</button>' }
      })
      expect(wrapper.find('.modal-footer').exists()).toBe(true)
      expect(wrapper.find('.footer-btn').exists()).toBe(true)
    })

    it('does not render footer when no footer slot', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' }
      })
      expect(wrapper.find('.modal-footer').exists()).toBe(false)
    })

    it('renders close button when closable=true (default)', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' }
      })
      expect(wrapper.find('.modal-close').exists()).toBe(true)
    })

    it('does not render close button when closable=false', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal', closable: false }
      })
      expect(wrapper.find('.modal-close').exists()).toBe(false)
    })
  })

  describe('size classes', () => {
    it.each(['sm', 'md', 'lg', 'xl', 'full'])('applies modal-%s class for size=%s', (size) => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal', size }
      })
      expect(wrapper.find('.modal-container').classes()).toContain(`modal-${size}`)
    })
  })

  describe('close behavior', () => {
    it('emits close and update:isOpen when close button clicked', async () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' }
      })
      await wrapper.find('.modal-close').trigger('click')
      expect(wrapper.emitted('close')).toBeTruthy()
      expect(wrapper.emitted('update:isOpen')?.[0]).toEqual([false])
    })

    it('emits close when overlay clicked and closeOnOverlay=true (default)', async () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal', closeOnOverlay: true }
      })
      await wrapper.find('.modal-overlay').trigger('click')
      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('does not emit close when overlay clicked and closeOnOverlay=false', async () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal', closeOnOverlay: false }
      })
      await wrapper.find('.modal-overlay').trigger('click')
      expect(wrapper.emitted('close')).toBeFalsy()
    })
  })

  describe('modal stack management', () => {
    it('adds modal to stack when opened', async () => {
      window.__modalStack__ = []
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' }
      })
      await flushPromises()
      expect(window.__modalStack__.length).toBeGreaterThan(0)
      wrapper.unmount()
    })

    it('removes modal from stack on unmount', async () => {
      window.__modalStack__ = []
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' }
      })
      await flushPromises()
      const countBefore = window.__modalStack__.length
      wrapper.unmount()
      expect(window.__modalStack__.length).toBeLessThan(countBefore)
    })

    it('restores body overflow when last modal closes', async () => {
      window.__modalStack__ = []
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal' }
      })
      await flushPromises()
      expect(document.body.style.overflow).toBe('hidden')
      await wrapper.setProps({ isOpen: false })
      await flushPromises()
      expect(document.body.style.overflow).toBe('')
      wrapper.unmount()
    })

    it('does not restore overflow when another modal is still open', async () => {
      window.__modalStack__ = []
      const wrapper1 = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal 1' }
      })
      const wrapper2 = mount(BaseModal, {
        props: { isOpen: true, title: 'Modal 2' }
      })
      await flushPromises()

      await wrapper1.setProps({ isOpen: false })
      await flushPromises()
      // wrapper2 is still open, so overflow should still be hidden
      expect(document.body.style.overflow).toBe('hidden')

      wrapper1.unmount()
      wrapper2.unmount()
    })
  })

  describe('title slot', () => {
    it('renders title slot content instead of title prop', () => {
      const wrapper = mount(BaseModal, {
        props: { isOpen: true, title: 'Prop Title' },
        slots: { title: '<span class="custom-title">Custom Title</span>' }
      })
      expect(wrapper.find('.custom-title').exists()).toBe(true)
    })
  })
})
