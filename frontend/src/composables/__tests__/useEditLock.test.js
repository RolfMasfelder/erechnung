import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useEditLock } from '../useEditLock'
import { invoiceService } from '@/api/services/invoiceService'

vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    acquireEditLock: vi.fn(),
    releaseEditLock: vi.fn(),
    refreshEditLock: vi.fn()
  }
}))

// Helper component to test the composable inside a Vue lifecycle
function makeComponent(invoiceId) {
  return defineComponent({
    setup() {
      return useEditLock(invoiceId)
    },
    template: '<div />'
  })
}

describe('useEditLock', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('starts with lockHeld=false and lockError=null', () => {
      const wrapper = mount(makeComponent(1))
      expect(wrapper.vm.lockHeld).toBe(false)
      expect(wrapper.vm.lockError).toBeNull()
    })
  })

  describe('acquireLock', () => {
    it('sets lockHeld=true on success', async () => {
      invoiceService.acquireEditLock.mockResolvedValue({})
      const wrapper = mount(makeComponent(1))

      const result = await wrapper.vm.acquireLock()

      expect(result).toBe(true)
      expect(wrapper.vm.lockHeld).toBe(true)
      expect(invoiceService.acquireEditLock).toHaveBeenCalledWith(1)
    })

    it('returns false and sets lockError on 423', async () => {
      invoiceService.acquireEditLock.mockRejectedValue({
        response: {
          status: 423,
          data: { editing_by: 'max', editing_since: '2024-01-01T10:00:00Z' }
        }
      })
      const wrapper = mount(makeComponent(2))

      const result = await wrapper.vm.acquireLock()

      expect(result).toBe(false)
      expect(wrapper.vm.lockHeld).toBe(false)
      expect(wrapper.vm.lockError).toBeTruthy()
    })

    it('returns false on other errors', async () => {
      invoiceService.acquireEditLock.mockRejectedValue(new Error('Network error'))
      const wrapper = mount(makeComponent(1))

      const result = await wrapper.vm.acquireLock()

      expect(result).toBe(false)
      expect(wrapper.vm.lockHeld).toBe(false)
    })

    it('normalises lockError from nested error.details shape', async () => {
      invoiceService.acquireEditLock.mockRejectedValue({
        response: {
          status: 423,
          data: { error: { details: { editing_by: 'lisa', editing_since: '2024-01-01T12:00:00Z' } } }
        }
      })
      const wrapper = mount(makeComponent(1))

      await wrapper.vm.acquireLock()

      expect(wrapper.vm.lockError.editing_by).toBe('lisa')
    })
  })

  describe('releaseLock', () => {
    it('releases lock and calls service', async () => {
      invoiceService.acquireEditLock.mockResolvedValue({})
      invoiceService.releaseEditLock.mockResolvedValue({})
      const wrapper = mount(makeComponent(1))

      await wrapper.vm.acquireLock()
      await wrapper.vm.releaseLock()

      expect(wrapper.vm.lockHeld).toBe(false)
      expect(invoiceService.releaseEditLock).toHaveBeenCalledWith(1)
    })

    it('does not call service when lock is not held', async () => {
      const wrapper = mount(makeComponent(1))

      await wrapper.vm.releaseLock()

      expect(invoiceService.releaseEditLock).not.toHaveBeenCalled()
    })

    it('silently ignores release errors', async () => {
      invoiceService.acquireEditLock.mockResolvedValue({})
      invoiceService.releaseEditLock.mockRejectedValue(new Error('Release failed'))
      const wrapper = mount(makeComponent(1))

      await wrapper.vm.acquireLock()
      await expect(wrapper.vm.releaseLock()).resolves.toBeUndefined()
    })
  })

  describe('heartbeat', () => {
    it('calls refreshEditLock after 60 seconds', async () => {
      invoiceService.acquireEditLock.mockResolvedValue({})
      invoiceService.refreshEditLock.mockResolvedValue({})
      const wrapper = mount(makeComponent(1))

      await wrapper.vm.acquireLock()
      vi.advanceTimersByTime(60_000)
      await nextTick()

      expect(invoiceService.refreshEditLock).toHaveBeenCalledWith(1)
    })

    it('sets lockHeld=false when heartbeat receives 423', async () => {
      invoiceService.acquireEditLock.mockResolvedValue({})
      invoiceService.refreshEditLock.mockRejectedValue({
        response: { status: 423 }
      })
      const wrapper = mount(makeComponent(1))

      await wrapper.vm.acquireLock()
      vi.advanceTimersByTime(60_000)
      await nextTick()
      await nextTick()

      expect(wrapper.vm.lockHeld).toBe(false)
    })
  })

  describe('onUnmounted', () => {
    it('releases lock when component unmounts', async () => {
      invoiceService.acquireEditLock.mockResolvedValue({})
      invoiceService.releaseEditLock.mockResolvedValue({})
      const wrapper = mount(makeComponent(1))

      await wrapper.vm.acquireLock()
      wrapper.unmount()
      await nextTick()

      expect(invoiceService.releaseEditLock).toHaveBeenCalled()
    })
  })
})
