import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

// A child whose render throws when shouldThrow is true.
const ThrowingChild = defineComponent({
  name: 'ThrowingChild',
  props: {
    shouldThrow: {
      type: Boolean,
      default: true
    }
  },
  render() {
    if (this.shouldThrow) {
      throw new Error('Simulated child failure')
    }
    return h('div', { class: 'child-ok' }, 'OK')
  }
})

describe('ErrorBoundary', () => {
  it('renders the slot content when no error occurs', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: () => h(ThrowingChild, { shouldThrow: false })
      }
    })

    expect(wrapper.find('.child-ok').exists()).toBe(true)
    expect(wrapper.find('.error-boundary').exists()).toBe(false)
  })

  it('catches errors from child components and shows fallback UI', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: () => h(ThrowingChild, { shouldThrow: true })
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.find('.error-boundary').exists()).toBe(true)
    expect(wrapper.find('.error-boundary__title').text()).toContain('schiefgelaufen')
    expect(wrapper.text()).toContain('Simulated child failure')

    errorSpy.mockRestore()
  })

  it('uses custom fallback title and message via props', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mount(ErrorBoundary, {
      props: {
        fallbackTitle: 'Eigener Titel',
        fallbackMessage: 'Eigene Nachricht'
      },
      slots: {
        default: () => h(ThrowingChild, { shouldThrow: true })
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Eigener Titel')
    expect(wrapper.text()).toContain('Eigene Nachricht')

    errorSpy.mockRestore()
  })

  it('resets to slot content when reset button is clicked', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const shouldThrow = ref(true)
    const wrapper = mount(ErrorBoundary, {
      slots: {
        default: () => h(ThrowingChild, { shouldThrow: shouldThrow.value })
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.find('.error-boundary').exists()).toBe(true)

    // Stop the child from throwing before resetting the boundary.
    shouldThrow.value = false
    await wrapper.find('.error-boundary__button').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.error-boundary').exists()).toBe(false)
    expect(wrapper.find('.child-ok').exists()).toBe(true)

    errorSpy.mockRestore()
  })
})
