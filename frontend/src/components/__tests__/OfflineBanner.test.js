import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

const { default: OfflineBanner } = await import('../OfflineBanner.vue')

function setOnline(value) {
  Object.defineProperty(navigator, 'onLine', {
    configurable: true,
    get: () => value,
  })
}

describe('OfflineBanner', () => {
  let wrapper

  beforeEach(() => {
    setOnline(true)
  })

  afterEach(() => {
    if (wrapper) wrapper.unmount()
    // Reset back to online so other tests start clean
    window.dispatchEvent(new Event('online'))
  })

  it('does not render the banner when online', () => {
    window.dispatchEvent(new Event('online'))
    wrapper = mount(OfflineBanner)
    expect(wrapper.find('.offline-banner').exists()).toBe(false)
  })

  it('renders the banner with the offline message when offline', async () => {
    wrapper = mount(OfflineBanner)
    window.dispatchEvent(new Event('offline'))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.offline-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('Keine Internetverbindung')
  })

  it('hides the banner when connection is restored', async () => {
    wrapper = mount(OfflineBanner)
    window.dispatchEvent(new Event('offline'))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.offline-banner').exists()).toBe(true)

    window.dispatchEvent(new Event('online'))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.offline-banner').exists()).toBe(false)
  })
})
