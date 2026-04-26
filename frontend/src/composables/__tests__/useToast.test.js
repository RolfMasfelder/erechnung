import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useToast } from '../useToast'

describe('useToast', () => {
  let toast

  beforeEach(() => {
    // Get fresh instance for each test
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

  describe('showToast', () => {
    it('should add a toast with unique id', () => {
      toast.showToast('Test message', 'success')

      expect(toast.toasts.value).toHaveLength(1)
      expect(toast.toasts.value[0]).toMatchObject({
        message: 'Test message',
        variant: 'success'
      })
      expect(toast.toasts.value[0].id).toBeDefined()
    })

    it('should add multiple toasts', () => {
      toast.showToast('First message', 'success')
      toast.showToast('Second message', 'danger')

      expect(toast.toasts.value).toHaveLength(2)
      expect(toast.toasts.value[0].message).toBe('First message')
      expect(toast.toasts.value[1].message).toBe('Second message')
    })

    it('should auto-remove toast after timeout', () => {
      toast.showToast('Auto-remove test', 'info', 3000)

      expect(toast.toasts.value.length).toBeGreaterThanOrEqual(1)
      const initialLength = toast.toasts.value.length

      vi.advanceTimersByTime(3000)

      expect(toast.toasts.value.length).toBe(initialLength - 1)
    })

    it('should use default timeout of 5000ms', () => {
      toast.showToast('Default timeout', 'success')

      expect(toast.toasts.value).toHaveLength(1)

      vi.advanceTimersByTime(4999)
      expect(toast.toasts.value).toHaveLength(1)

      vi.advanceTimersByTime(1)
      expect(toast.toasts.value).toHaveLength(0)
    })
  })

  describe('removeToast', () => {
    it('should remove toast by id', () => {
      toast.showToast('First', 'success')
      toast.showToast('Second', 'success')

      const toastId = toast.toasts.value[0].id
      toast.removeToast(toastId)

      expect(toast.toasts.value).toHaveLength(1)
      expect(toast.toasts.value[0].message).toBe('Second')
    })

    it('should handle removing non-existent toast', () => {
      toast.showToast('Test', 'success')

      toast.removeToast('non-existent-id')

      expect(toast.toasts.value).toHaveLength(1)
    })
  })

  describe('convenience methods', () => {
    it('success should create success toast', () => {
      toast.success('Success message')

      expect(toast.toasts.value).toHaveLength(1)
      expect(toast.toasts.value[0]).toMatchObject({
        message: 'Success message',
        variant: 'success'
      })
    })

    it('error should create error toast', () => {
      toast.error('Error message')

      expect(toast.toasts.value).toHaveLength(1)
      expect(toast.toasts.value[0]).toMatchObject({
        message: 'Error message',
        variant: 'danger'
      })
    })

    it('info should create info toast', () => {
      toast.info('Info message')

      expect(toast.toasts.value).toHaveLength(1)
      expect(toast.toasts.value[0]).toMatchObject({
        message: 'Info message',
        variant: 'info'
      })
    })

    it('warning should create warning toast', () => {
      toast.warning('Warning message')

      expect(toast.toasts.value).toHaveLength(1)
      expect(toast.toasts.value[0]).toMatchObject({
        message: 'Warning message',
        variant: 'warning'
      })
    })

    it('convenience methods should accept custom timeout', () => {
      toast.success('Custom timeout', 2000)

      expect(toast.toasts.value).toHaveLength(1)

      vi.advanceTimersByTime(2000)

      expect(toast.toasts.value).toHaveLength(0)
    })
  })

  describe('multiple toasts with timeouts', () => {
    it('should handle multiple toasts with different timeouts', () => {
      toast.showToast('First', 'success', 1000)
      toast.showToast('Second', 'success', 2000)
      toast.showToast('Third', 'success', 3000)

      expect(toast.toasts.value).toHaveLength(3)

      vi.advanceTimersByTime(1000)
      expect(toast.toasts.value).toHaveLength(2)
      expect(toast.toasts.value[0].message).toBe('Second')

      vi.advanceTimersByTime(1000)
      expect(toast.toasts.value).toHaveLength(1)
      expect(toast.toasts.value[0].message).toBe('Third')

      vi.advanceTimersByTime(1000)
      expect(toast.toasts.value).toHaveLength(0)
    })
  })

  describe('shared state', () => {
    it('should share state between multiple instances', () => {
      const toast1 = useToast()
      const toast2 = useToast()

      toast1.success('From instance 1')

      expect(toast2.toasts.value).toHaveLength(1)
      expect(toast2.toasts.value[0].message).toBe('From instance 1')
    })
  })
})
