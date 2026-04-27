import { ref, onUnmounted } from 'vue'
import { invoiceService } from '@/api/services/invoiceService'

const HEARTBEAT_INTERVAL_MS = 60_000

/**
 * Manages the pessimistic edit lock lifecycle for an invoice.
 *
 * Pattern (ADR-024 / arc42 §8.9):
 *   1. Call acquireLock() when opening the edit form.
 *   2. Heartbeats run automatically every 60 s while the lock is held.
 *   3. Lock is released automatically on component unmount (browser close / navigation).
 *   4. Call releaseLock() explicitly after a successful save.
 *
 * @param {number|string} invoiceId
 * @returns {{ lockHeld: Ref<boolean>, lockError: Ref<{editing_by:string,editing_since:string}|null>, acquireLock: Function, releaseLock: Function }}
 */
export function useEditLock(invoiceId) {
  /** @type {import('vue').Ref<boolean>} */
  const lockHeld = ref(false)

  /**
   * Set when acquire fails with 423.
   * @type {import('vue').Ref<{editing_by:string, editing_since:string}|null>}
   */
  const lockError = ref(null)

  /** @type {ReturnType<typeof setInterval>|null} */
  let heartbeatTimer = null

  /**
   * Request the edit lock. Returns true on success, false if held by another user.
   * @returns {Promise<boolean>}
   */
  async function acquireLock() {
    lockError.value = null
    try {
      await invoiceService.acquireEditLock(invoiceId)
      lockHeld.value = true
      _startHeartbeat()
      return true
    } catch (err) {
      if (err.response?.status === 423) {
        // Normalise both possible response shapes (DRF nested error vs. flat details)
        const body = err.response.data
        lockError.value = body?.error?.details ?? body?.details ?? body ?? null
      }
      return false
    }
  }

  /**
   * Release the edit lock. Best-effort — server auto-expires after timeout anyway.
   * @returns {Promise<void>}
   */
  async function releaseLock() {
    _stopHeartbeat()
    if (!lockHeld.value) return
    lockHeld.value = false
    try {
      await invoiceService.releaseEditLock(invoiceId)
    } catch (releaseError) {
      // best-effort — server auto-expires locks after INVOICE_EDIT_LOCK_TIMEOUT_MINUTES
      console.debug('Edit lock release failed (non-critical):', releaseError?.message)
    }
  }

  function _startHeartbeat() {
    _stopHeartbeat()
    heartbeatTimer = setInterval(async () => {
      if (!lockHeld.value) return
      try {
        await invoiceService.refreshEditLock(invoiceId)
      } catch (err) {
        if (err.response?.status === 423) {
          // Lock was force-released by a supervisor; stop heartbeat silently
          lockHeld.value = false
          _stopHeartbeat()
        }
      }
    }, HEARTBEAT_INTERVAL_MS)
  }

  function _stopHeartbeat() {
    if (heartbeatTimer !== null) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  onUnmounted(() => {
    releaseLock()
  })

  return { lockHeld, lockError, acquireLock, releaseLock }
}
