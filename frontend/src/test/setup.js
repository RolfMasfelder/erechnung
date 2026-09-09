/**
 * Vitest Setup File
 * Wird vor allen Tests ausgeführt
 */

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

// happy-dom (vitest 5) exposes localStorage as getter-only, so define via property descriptor
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true,
  configurable: true
})

// Mock window.location
delete window.location
window.location = { href: '' }

// Cleanup nach jedem Test
afterEach(() => {
  vi.clearAllMocks()
  localStorageMock.getItem.mockClear()
  localStorageMock.setItem.mockClear()
  localStorageMock.removeItem.mockClear()
  localStorageMock.clear.mockClear()
})
