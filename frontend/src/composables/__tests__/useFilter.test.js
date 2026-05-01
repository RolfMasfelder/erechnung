import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useFilter } from '../useFilter'
import { ref, defineComponent } from 'vue'
import { mount } from '@vue/test-utils'

// Mock vue-router
const mockPush = vi.fn()
const mockReplace = vi.fn(() => Promise.resolve())
const mockRoute = ref({ query: {} })

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace
  }),
  useRoute: () => mockRoute.value
}))

describe('useFilter', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockPush.mockClear()
    mockReplace.mockClear()
    mockRoute.value = { query: {} }
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initialization', () => {
    it('initializes with default filters', () => {
      const { filters } = useFilter({
        defaultFilters: {
          search: '',
          status: 'all'
        }
      })

      expect(filters.value.search).toBe('')
      expect(filters.value.status).toBe('all')
    })

    it('initializes with empty object when no defaults provided', () => {
      const { filters } = useFilter()

      expect(filters.value).toEqual({})
    })
  })

  describe('setFilter', () => {
    it('updates a single filter value', () => {
      const { filters, setFilter } = useFilter({
        defaultFilters: { status: 'all', search: '' }
      })

      setFilter('status', 'paid')

      expect(filters.value.status).toBe('paid')
      expect(filters.value.search).toBe('')
    })

    it('can set filter to null', () => {
      const { filters, setFilter } = useFilter({
        defaultFilters: { status: 'active' }
      })

      setFilter('status', null)

      expect(filters.value.status).toBeNull()
    })
  })

  describe('setFilters', () => {
    it('updates multiple filter values at once', () => {
      const { filters, setFilters } = useFilter({
        defaultFilters: { search: '', status: 'all', category: '' }
      })

      setFilters({ status: 'paid', category: 'service' })

      expect(filters.value.status).toBe('paid')
      expect(filters.value.category).toBe('service')
      expect(filters.value.search).toBe('')
    })
  })

  describe('handleSearch with debouncing', () => {
    it('sets pendingSearch immediately', () => {
      const { pendingSearch, handleSearch } = useFilter({
        defaultFilters: { search: '' }
      })

      handleSearch('test query')

      expect(pendingSearch.value).toBe('test query')
    })

    it('sets isFiltering to true during debounce', () => {
      const { isFiltering, handleSearch } = useFilter({
        defaultFilters: { search: '' }
      })

      handleSearch('test')

      expect(isFiltering.value).toBe(true)
    })

    it('updates filters.search after debounce delay', () => {
      const { filters, handleSearch } = useFilter({
        defaultFilters: { search: '' },
        debounceMs: 300
      })

      handleSearch('test query')

      expect(filters.value.search).toBe('')

      vi.advanceTimersByTime(300)

      expect(filters.value.search).toBe('test query')
    })

    it('sets isFiltering to false after debounce', () => {
      const { isFiltering, handleSearch } = useFilter({
        defaultFilters: { search: '' },
        debounceMs: 300
      })

      handleSearch('test')
      expect(isFiltering.value).toBe(true)

      vi.advanceTimersByTime(300)

      expect(isFiltering.value).toBe(false)
    })

    it('cancels previous debounce on new input', () => {
      const { filters, handleSearch } = useFilter({
        defaultFilters: { search: '' },
        debounceMs: 300
      })

      handleSearch('first')
      vi.advanceTimersByTime(100)

      handleSearch('second')
      vi.advanceTimersByTime(100)

      handleSearch('third')
      vi.advanceTimersByTime(300)

      expect(filters.value.search).toBe('third')
    })

    it('respects custom debounce delay', () => {
      const { filters, handleSearch } = useFilter({
        defaultFilters: { search: '' },
        debounceMs: 500
      })

      handleSearch('test')

      vi.advanceTimersByTime(300)
      expect(filters.value.search).toBe('')

      vi.advanceTimersByTime(200)
      expect(filters.value.search).toBe('test')
    })
  })

  describe('applySearchNow', () => {
    it('applies search immediately without waiting for debounce', () => {
      const { filters, pendingSearch, handleSearch, applySearchNow } = useFilter({
        defaultFilters: { search: '' },
        debounceMs: 300
      })

      handleSearch('immediate test')
      expect(filters.value.search).toBe('')

      applySearchNow()

      expect(filters.value.search).toBe('immediate test')
    })

    it('clears pending debounce timer', () => {
      const { filters, handleSearch, applySearchNow } = useFilter({
        defaultFilters: { search: '' },
        debounceMs: 300
      })

      handleSearch('test')
      applySearchNow()

      // Advance time - should not trigger another update
      vi.advanceTimersByTime(300)

      expect(filters.value.search).toBe('test')
    })

    it('sets isFiltering to false', () => {
      const { isFiltering, handleSearch, applySearchNow } = useFilter({
        defaultFilters: { search: '' }
      })

      handleSearch('test')
      expect(isFiltering.value).toBe(true)

      applySearchNow()

      expect(isFiltering.value).toBe(false)
    })
  })

  describe('resetFilters', () => {
    it('resets all filters to default values', () => {
      const { filters, setFilter, resetFilters } = useFilter({
        defaultFilters: { search: '', status: 'all', category: '' }
      })

      setFilter('status', 'paid')
      setFilter('category', 'product')
      setFilter('search', 'test')

      resetFilters()

      expect(filters.value.search).toBe('')
      expect(filters.value.status).toBe('all')
      expect(filters.value.category).toBe('')
    })

    it('clears pending search', () => {
      const { pendingSearch, handleSearch, resetFilters } = useFilter({
        defaultFilters: { search: '' }
      })

      handleSearch('pending')
      expect(pendingSearch.value).toBe('pending')

      resetFilters()

      expect(pendingSearch.value).toBe('')
    })

    it('sets isFiltering to false', () => {
      const { isFiltering, handleSearch, resetFilters } = useFilter({
        defaultFilters: { search: '' }
      })

      handleSearch('test')
      expect(isFiltering.value).toBe(true)

      resetFilters()

      expect(isFiltering.value).toBe(false)
    })

    it('clears pending debounce timer', () => {
      const { filters, handleSearch, resetFilters } = useFilter({
        defaultFilters: { search: '' },
        debounceMs: 300
      })

      handleSearch('test')
      resetFilters()

      vi.advanceTimersByTime(300)

      expect(filters.value.search).toBe('')
    })
  })

  describe('hasActiveFilters', () => {
    it('returns false when all filters are at default', () => {
      const { hasActiveFilters } = useFilter({
        defaultFilters: { search: '', status: 'all' }
      })

      expect(hasActiveFilters.value).toBe(false)
    })

    it('returns true when any filter differs from default', () => {
      const { hasActiveFilters, setFilter } = useFilter({
        defaultFilters: { search: '', status: 'all' }
      })

      setFilter('status', 'paid')

      expect(hasActiveFilters.value).toBe(true)
    })

    it('returns false after reset', () => {
      const { hasActiveFilters, setFilter, resetFilters } = useFilter({
        defaultFilters: { search: '', status: 'all' }
      })

      setFilter('status', 'paid')
      expect(hasActiveFilters.value).toBe(true)

      resetFilters()

      expect(hasActiveFilters.value).toBe(false)
    })
  })

  describe('activeFilterCount', () => {
    it('returns 0 when no filters active', () => {
      const { activeFilterCount } = useFilter({
        defaultFilters: { search: '', status: 'all', category: '' }
      })

      expect(activeFilterCount.value).toBe(0)
    })

    it('counts active filters correctly', () => {
      const { activeFilterCount, setFilter } = useFilter({
        defaultFilters: { search: '', status: 'all', category: '' }
      })

      setFilter('status', 'paid')
      expect(activeFilterCount.value).toBe(1)

      setFilter('category', 'service')
      expect(activeFilterCount.value).toBe(2)
    })

    it('does not count empty string values', () => {
      const { activeFilterCount, setFilter } = useFilter({
        defaultFilters: { search: '', status: '' }
      })

      setFilter('search', '')
      setFilter('status', '')

      expect(activeFilterCount.value).toBe(0)
    })

    it('does not count null values', () => {
      const { activeFilterCount, setFilter } = useFilter({
        defaultFilters: { status: 'all' }
      })

      setFilter('status', null)

      expect(activeFilterCount.value).toBe(0)
    })
  })

  describe('queryParams', () => {
    it('returns object with non-empty filter values', () => {
      const { queryParams, setFilter } = useFilter({
        defaultFilters: { search: '', status: 'all' }
      })

      setFilter('search', 'test')
      setFilter('status', 'paid')

      expect(queryParams.value).toEqual({
        search: 'test',
        status: 'paid'
      })
    })

    it('excludes empty values', () => {
      const { queryParams, setFilter } = useFilter({
        defaultFilters: { search: '', status: '' }
      })

      setFilter('search', 'test')

      expect(queryParams.value).toEqual({ search: 'test' })
      expect(queryParams.value.status).toBeUndefined()
    })

    it('formats Date objects as ISO date strings', () => {
      const { queryParams, setFilter } = useFilter({
        defaultFilters: { date: null }
      })

      setFilter('date', new Date('2026-01-09'))

      expect(queryParams.value.date).toBe('2026-01-09')
    })

    it('formats date range arrays correctly', () => {
      const { queryParams, setFilter } = useFilter({
        defaultFilters: { dateRange: [] }
      })

      setFilter('dateRange', [new Date('2026-01-01'), new Date('2026-01-31')])

      // Backend-Syntax: issue_date__gte / issue_date__lte (Django FilterSet)
      expect(queryParams.value.issue_date__gte).toBe('2026-01-01')
      expect(queryParams.value.issue_date__lte).toBe('2026-01-31')
    })
  })

  describe('onFilterChange callback', () => {
    it('calls callback when filters change', async () => {
      const callback = vi.fn()
      const { setFilter } = useFilter({
        defaultFilters: { status: 'all' },
        onFilterChange: callback
      })

      setFilter('status', 'paid')

      // Wait for watcher to trigger
      await vi.runAllTimersAsync()

      expect(callback).toHaveBeenCalled()
    })
  })

  describe('URL sync disabled', () => {
    it('does not call router.replace when syncUrl is false', () => {
      const { setFilter } = useFilter({
        defaultFilters: { status: 'all' },
        syncUrl: false
      })

      setFilter('status', 'paid')

      expect(mockReplace).not.toHaveBeenCalled()
    })
  })

  describe('initFromUrl with various value types', () => {
    // Helper: mount composable in a Vue component to trigger onMounted
    function mountFilter(options) {
      let result
      const TestComp = defineComponent({
        setup() {
          result = useFilter(options)
          return result
        },
        template: '<div />'
      })
      mount(TestComp)
      return result
    }

    it('reads boolean filter from URL (true)', () => {
      mockRoute.value = { query: { active: 'true' } }
      const { filters } = mountFilter({
        defaultFilters: { active: false },
        syncUrl: true
      })
      expect(filters.value.active).toBe(true)
    })

    it('reads number filter from URL', () => {
      mockRoute.value = { query: { page: '3' } }
      const { filters } = mountFilter({
        defaultFilters: { page: 1 },
        syncUrl: true
      })
      expect(filters.value.page).toBe(3)
    })

    it('reads array filter from URL (single value)', () => {
      mockRoute.value = { query: { tags: 'foo' } }
      const { filters } = mountFilter({
        defaultFilters: { tags: [] },
        syncUrl: true
      })
      expect(Array.isArray(filters.value.tags)).toBe(true)
      expect(filters.value.tags).toContain('foo')
    })

    it('reads array filter from URL (multiple values)', () => {
      mockRoute.value = { query: { tags: ['foo', 'bar'] } }
      const { filters } = mountFilter({
        defaultFilters: { tags: [] },
        syncUrl: true
      })
      expect(filters.value.tags).toEqual(['foo', 'bar'])
    })

    it('reads Date filter from URL', () => {
      mockRoute.value = { query: { createdAt: '2026-06-01' } }
      const { filters } = mountFilter({
        defaultFilters: { createdAt: new Date(0) },
        syncUrl: true
      })
      expect(filters.value.createdAt instanceof Date).toBe(true)
    })

    it('skips unknown query keys', () => {
      mockRoute.value = { query: { unknown: 'x', search: 'hello' } }
      const { filters } = mountFilter({
        defaultFilters: { search: '' },
        syncUrl: true
      })
      expect(filters.value.search).toBe('hello')
      expect(filters.value.unknown).toBeUndefined()
    })
  })

  describe('syncToUrl with Date and Array values', () => {
    it('serializes Date value to URL', async () => {
      const { setFilter } = useFilter({
        defaultFilters: { date: null },
        syncUrl: true
      })
      setFilter('date', new Date('2026-05-15'))
      await vi.runAllTimersAsync()
      expect(mockReplace).toHaveBeenCalled()
      const lastCall = mockReplace.mock.calls[mockReplace.mock.calls.length - 1][0]
      expect(lastCall.query.date).toBe('2026-05-15')
    })

    it('serializes array of non-dates to URL', async () => {
      const { setFilter } = useFilter({
        defaultFilters: { tags: [] },
        syncUrl: true
      })
      setFilter('tags', ['a', 'b'])
      await vi.runAllTimersAsync()
      const lastCall = mockReplace.mock.calls[mockReplace.mock.calls.length - 1][0]
      expect(lastCall.query.tags).toEqual(['a', 'b'])
    })

    it('omits empty array from URL', async () => {
      const { setFilter } = useFilter({
        defaultFilters: { tags: ['x'] },
        syncUrl: true
      })
      setFilter('tags', [])
      await vi.runAllTimersAsync()
      const lastCall = mockReplace.mock.calls[mockReplace.mock.calls.length - 1][0]
      expect(lastCall.query.tags).toBeUndefined()
    })
  })
})
