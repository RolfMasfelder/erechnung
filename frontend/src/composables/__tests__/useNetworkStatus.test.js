import { describe, it, expect, vi, beforeEach } from 'vitest'

// Create stable toast mock functions
const mockToast = {
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}

vi.mock('../useToast', () => ({
  useToast: () => mockToast,
}))

// Import AFTER mock is registered. Module-singleton state is set on first import.
const { useNetworkStatus } = await import('../useNetworkStatus')

describe('useNetworkStatus (singleton)', () => {
  beforeEach(() => {
    mockToast.success.mockClear()
    mockToast.warning.mockClear()
  })

  it('returns the same isOnline ref across calls', () => {
    const a = useNetworkStatus()
    const b = useNetworkStatus()
    expect(a.isOnline).toBe(b.isOnline)
  })

  it('initializes with a boolean isOnline value', () => {
    const { isOnline } = useNetworkStatus()
    expect(typeof isOnline.value).toBe('boolean')
  })

  it('updates isOnline and shows warning when offline event fires', () => {
    const { isOnline } = useNetworkStatus()
    window.dispatchEvent(new Event('offline'))
    expect(isOnline.value).toBe(false)
    expect(mockToast.warning).toHaveBeenCalledWith('Keine Internetverbindung')
  })

  it('updates isOnline and shows success when online event fires', () => {
    const { isOnline } = useNetworkStatus()
    window.dispatchEvent(new Event('online'))
    expect(isOnline.value).toBe(true)
    expect(mockToast.success).toHaveBeenCalledWith('Verbindung wiederhergestellt')
  })
})
