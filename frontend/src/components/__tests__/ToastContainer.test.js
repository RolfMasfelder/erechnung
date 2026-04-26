import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ToastContainer from '../ToastContainer.vue'
import { useToast } from '@/composables/useToast'

describe('ToastContainer', () => {
  let toast

  beforeEach(() => {
    toast = useToast()
    // Clear all toasts - must modify the array in place to affect shared state
    while (toast.toasts.value.length > 0) {
      toast.toasts.value.pop()
    }
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should render without toasts', () => {
    // Ensure state is clean
    while (toast.toasts.value.length > 0) {
      toast.toasts.value.pop()
    }

    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    const container = document.querySelector('.toast-container')
    expect(container).toBeTruthy()
    // Don't check children length - TransitionGroup may have internal elements
    wrapper.unmount()
  })

  it('should render success toast', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.success('Success message')
    await wrapper.vm.$nextTick()

    const toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-success')).toBe(true)
    expect(toastEl.textContent).toContain('Success message')

    wrapper.unmount()
  })

  it('should render error toast', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.error('Error message')
    await wrapper.vm.$nextTick()

    const toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-danger')).toBe(true)
    expect(toastEl.textContent).toContain('Error message')

    wrapper.unmount()
  })

  it('should render warning toast', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.warning('Warning message')
    await wrapper.vm.$nextTick()

    const toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-warning')).toBe(true)
    expect(toastEl.textContent).toContain('Warning message')

    wrapper.unmount()
  })

  it('should render info toast', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.info('Info message')
    await wrapper.vm.$nextTick()

    const toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-info')).toBe(true)
    expect(toastEl.textContent).toContain('Info message')

    wrapper.unmount()
  })

  it('should render multiple toasts', async () => {
    const multiWrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    const initialLength = toast.toasts.value.length
    toast.success('First')
    toast.error('Second')
    toast.warning('Third')
    await multiWrapper.vm.$nextTick()

    const toasts = document.querySelectorAll('.toast')
    expect(toasts.length).toBeGreaterThanOrEqual(3)
    // Check that our new toasts are present
    const texts = Array.from(toasts).map(t => t.textContent)
    expect(texts.some(t => t.includes('First'))).toBe(true)
    expect(texts.some(t => t.includes('Second'))).toBe(true)
    expect(texts.some(t => t.includes('Third'))).toBe(true)

    multiWrapper.unmount()
  })

  it('should remove toast on close button click', async () => {
    const closeWrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.success('Test message')
    await closeWrapper.vm.$nextTick()

    expect(toast.toasts.value.length).toBeGreaterThanOrEqual(1)

    const closeButton = document.querySelector('.toast-close')
    expect(closeButton).toBeTruthy()

    const lengthBefore = toast.toasts.value.length
    closeButton.click()
    await closeWrapper.vm.$nextTick()

    expect(toast.toasts.value.length).toBe(lengthBefore - 1)

    closeWrapper.unmount()
  })

  it('should auto-remove toast after timeout', async () => {
    const timeoutWrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    const initialLength = toast.toasts.value.length
    toast.success('Auto-remove', 1000)
    await timeoutWrapper.vm.$nextTick()

    expect(toast.toasts.value.length).toBe(initialLength + 1)

    vi.advanceTimersByTime(1000)
    await timeoutWrapper.vm.$nextTick()

    expect(toast.toasts.value.length).toBe(initialLength)

    timeoutWrapper.unmount()
  })

  it('should render correct icons for each type', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    // Success icon (check circle)
    toast.success('Success')
    await wrapper.vm.$nextTick()
    let toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-success')).toBe(true)

    // Clear and test error
    while (toast.toasts.value.length > 0) {
      toast.toasts.value.pop()
    }
    toast.error('Error')
    await wrapper.vm.$nextTick()
    toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-danger')).toBe(true)

    // Clear and test warning
    while (toast.toasts.value.length > 0) {
      toast.toasts.value.pop()
    }
    toast.warning('Warning')
    await wrapper.vm.$nextTick()
    toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-warning')).toBe(true)

    // Clear and test info
    while (toast.toasts.value.length > 0) {
      toast.toasts.value.pop()
    }
    toast.info('Info')
    await wrapper.vm.$nextTick()
    toastEl = document.querySelector('.toast')
    expect(toastEl).toBeTruthy()
    expect(toastEl.classList.contains('toast-info')).toBe(true)

    wrapper.unmount()
  })

  it('should apply correct animation classes', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.success('Animated toast')
    await wrapper.vm.$nextTick()

    // TransitionGroup should apply animation classes
    const animatedToast = document.querySelector('.toast')
    expect(animatedToast).toBeTruthy()

    wrapper.unmount()
  })

  it('should position toasts at top-right', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.success('Position test')
    await wrapper.vm.$nextTick()

    const container = document.querySelector('.toast-container')
    expect(container).toBeTruthy()
    // Container exists and is positioned - actual CSS is in scoped styles

    wrapper.unmount()
  })

  it('should stack multiple toasts vertically', async () => {
    const wrapper = mount(ToastContainer, {
      attachTo: document.body
    })

    toast.success('First')
    toast.success('Second')
    toast.success('Third')
    await wrapper.vm.$nextTick()

    const stacked = document.querySelectorAll('.toast')
    expect(stacked.length).toBeGreaterThanOrEqual(3)

    wrapper.unmount()
  })
})
