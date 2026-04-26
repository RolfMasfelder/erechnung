import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useNetworkStatus } from '../useNetworkStatus'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

// Create stable toast mock functions
const mockToast = {
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
  info: vi.fn()
}

vi.mock('../useToast', () => ({
  useToast: () => mockToast
}))

// Export mockToast for use in tests
export { mockToast }

describe('useNetworkStatus', () => {
  let component
  let wrapper

  beforeEach(() => {
    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true
    })

    // Create test component that uses the composable
    component = defineComponent({
      setup() {
        const { isOnline } = useNetworkStatus()
        return { isOnline }
      },
      render() {
        return h('div', this.isOnline ? 'online' : 'offline')
      }
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  it('initializes with current online status', () => {
    wrapper = mount(component)
    expect(wrapper.vm.isOnline).toBe(true)
    expect(wrapper.text()).toBe('online')
  })

  it('initializes as offline when navigator is offline', () => {
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: false
    })

    wrapper = mount(component)
    expect(wrapper.vm.isOnline).toBe(false)
    expect(wrapper.text()).toBe('offline')
  })

  it('updates status when going online', async () => {
    wrapper = mount(component)

    // Simulate going online
    const onlineEvent = new Event('online')
    window.dispatchEvent(onlineEvent)

    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isOnline).toBe(true)
  })

  it('updates status when going offline', async () => {
    wrapper = mount(component)

    // Simulate going offline
    const offlineEvent = new Event('offline')
    window.dispatchEvent(offlineEvent)

    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isOnline).toBe(false)
  })

  it('shows success toast when connection is restored', async () => {
    wrapper = mount(component)

    // Simulate going online
    const onlineEvent = new Event('online')
    window.dispatchEvent(onlineEvent)

    await wrapper.vm.$nextTick()
    expect(mockToast.success).toHaveBeenCalledWith('Verbindung wiederhergestellt')
  })

  it('shows warning toast when connection is lost', async () => {
    wrapper = mount(component)

    // Simulate going offline
    const offlineEvent = new Event('offline')
    window.dispatchEvent(offlineEvent)

    await wrapper.vm.$nextTick()
    expect(mockToast.warning).toHaveBeenCalledWith('Keine Internetverbindung')
  })

  it('removes event listeners on unmount', () => {
    const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')

    wrapper = mount(component)
    wrapper.unmount()

    expect(removeEventListenerSpy).toHaveBeenCalledWith('online', expect.any(Function))
    expect(removeEventListenerSpy).toHaveBeenCalledWith('offline', expect.any(Function))

    removeEventListenerSpy.mockRestore()
  })
})
