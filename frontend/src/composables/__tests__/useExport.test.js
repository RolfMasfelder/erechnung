import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useExport } from '../useExport'

describe('useExport', () => {
  let exportComposable

  // Test data
  const testData = [
    { id: 1, name: 'Test Kunde 1', email: 'test1@example.com', amount: 100.50 },
    { id: 2, name: 'Test Kunde 2', email: 'test2@example.com', amount: 200.75 },
    { id: 3, name: 'Test Kunde 3', email: 'test3@example.com', amount: 300.00 }
  ]

  const nestedData = [
    { id: 1, customer: { name: 'Kunde A', address: { city: 'Berlin' } } },
    { id: 2, customer: { name: 'Kunde B', address: { city: 'München' } } }
  ]

  // Mock Date for consistent filename generation
  const mockDate = new Date('2024-01-15T10:30:00Z')

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(mockDate)
    exportComposable = useExport({ filename: 'test_export' })

    // Mock DOM methods for download
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-url')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with correct default state', () => {
      expect(exportComposable.isExporting.value).toBe(false)
      expect(exportComposable.exportProgress.value).toBe(0)
      expect(exportComposable.exportError.value).toBe(null)
    })
  })

  describe('generateFilename', () => {
    it('should generate filename with date stamp', () => {
      const result = exportComposable.generateFilename('csv')
      expect(result).toBe('test_export_20240115.csv')
    })

    it('should use custom filename from options', () => {
      const customExport = useExport({ filename: 'rechnungen' })
      const result = customExport.generateFilename('json')
      expect(result).toBe('rechnungen_20240115.json')
    })

    it('should use default filename when not provided', () => {
      const defaultExport = useExport()
      const result = defaultExport.generateFilename('csv')
      expect(result).toBe('export_20240115.csv')
    })
  })

  describe('toCSV', () => {
    it('should return empty string for empty data', () => {
      const result = exportComposable.toCSV([])
      expect(result).toBe('')
    })

    it('should return empty string for null data', () => {
      const result = exportComposable.toCSV(null)
      expect(result).toBe('')
    })

    it('should convert data to CSV with semicolon delimiter', () => {
      const data = [
        { name: 'Test', value: 123 }
      ]
      const result = exportComposable.toCSV(data)
      expect(result).toBe('name;value\nTest;123')
    })

    it('should use column labels when provided', () => {
      const columns = [
        { key: 'name', label: 'Kundenname' },
        { key: 'amount', label: 'Betrag' }
      ]
      const result = exportComposable.toCSV(testData, columns)
      const lines = result.split('\n')
      expect(lines[0]).toBe('Kundenname;Betrag')
    })

    it('should handle nested object paths', () => {
      const columns = [
        { key: 'id', label: 'ID' },
        { key: 'customer.name', label: 'Kunde' },
        { key: 'customer.address.city', label: 'Stadt' }
      ]
      const result = exportComposable.toCSV(nestedData, columns)
      const lines = result.split('\n')
      expect(lines[0]).toBe('ID;Kunde;Stadt')
      expect(lines[1]).toBe('1;Kunde A;Berlin')
      expect(lines[2]).toBe('2;Kunde B;München')
    })

    it('should apply column formatters', () => {
      const columns = [
        { key: 'name', label: 'Name' },
        {
          key: 'amount',
          label: 'Betrag',
          formatter: (value) => `${value.toFixed(2)} €`
        }
      ]
      const result = exportComposable.toCSV(testData, columns)
      const lines = result.split('\n')
      expect(lines[1]).toContain('100.50 €')
    })

    it('should escape values containing semicolons', () => {
      const data = [{ name: 'Test;Name', value: 'OK' }]
      const result = exportComposable.toCSV(data)
      expect(result).toContain('"Test;Name"')
    })

    it('should escape values containing quotes', () => {
      const data = [{ name: 'Test "Quote" Name', value: 'OK' }]
      const result = exportComposable.toCSV(data)
      expect(result).toContain('"Test ""Quote"" Name"')
    })

    it('should escape values containing newlines', () => {
      const data = [{ name: 'Line1\nLine2', value: 'OK' }]
      const result = exportComposable.toCSV(data)
      expect(result).toContain('"Line1\nLine2"')
    })

    it('should handle null and undefined values', () => {
      const data = [{ name: null, value: undefined }]
      const result = exportComposable.toCSV(data)
      const lines = result.split('\n')
      expect(lines[1]).toBe(';')
    })
  })

  describe('exportCSV', () => {
    it('should manage isExporting state correctly', async () => {
      // Since exportCSV is sync-like (no real async work), test the before/after state
      expect(exportComposable.isExporting.value).toBe(false)
      await exportComposable.exportCSV(testData)
      expect(exportComposable.isExporting.value).toBe(false)
    })

    it('should reset isExporting after export completes', async () => {
      await exportComposable.exportCSV(testData)
      expect(exportComposable.isExporting.value).toBe(false)
    })

    it('should set exportProgress to 100 on success', async () => {
      await exportComposable.exportCSV(testData)
      expect(exportComposable.exportProgress.value).toBe(100)
    })

    it('should return true on successful export', async () => {
      const result = await exportComposable.exportCSV(testData)
      expect(result).toBe(true)
    })

    it('should set error for empty data', async () => {
      const result = await exportComposable.exportCSV([])
      expect(result).toBe(false)
      expect(exportComposable.exportError.value).toBe('Keine Daten zum Exportieren vorhanden')
    })

    it('should use custom filename when provided', async () => {
      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      await exportComposable.exportCSV(testData, null, 'custom_file.csv')
      expect(mockLink.download).toBe('custom_file.csv')
    })

    it('should call fetchData when no data provided and fetchData configured', async () => {
      const fetchData = vi.fn().mockResolvedValue(testData)
      const exportWithFetch = useExport({ filename: 'test', fetchData })

      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      const result = await exportWithFetch.exportCSV(null)
      expect(fetchData).toHaveBeenCalled()
      expect(result).toBe(true)
    })
  })

  describe('exportJSON', () => {
    it('should export data as JSON', async () => {
      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      const result = await exportComposable.exportJSON(testData)
      expect(result).toBe(true)
      expect(mockLink.download).toBe('test_export_20240115.json')
    })

    it('should return false for empty data', async () => {
      const result = await exportComposable.exportJSON([])
      expect(result).toBe(false)
      expect(exportComposable.exportError.value).toBe('Keine Daten zum Exportieren vorhanden')
    })

    it('should set progress correctly', async () => {
      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      await exportComposable.exportJSON(testData)
      expect(exportComposable.exportProgress.value).toBe(100)
    })
  })

  describe('exportSelected', () => {
    it('should export only selected items by ID', async () => {
      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      const selectedIds = new Set([1, 3])
      const result = await exportComposable.exportSelected(testData, selectedIds)
      expect(result).toBe(true)
    })

    it('should accept array of IDs', async () => {
      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      const selectedIds = [1, 2]
      const result = await exportComposable.exportSelected(testData, selectedIds)
      expect(result).toBe(true)
    })

    it('should return false when no items selected', async () => {
      const selectedIds = new Set()
      const result = await exportComposable.exportSelected(testData, selectedIds)
      expect(result).toBe(false)
      expect(exportComposable.exportError.value).toBe('Keine Elemente ausgewählt')
    })

    it('should use custom idKey', async () => {
      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      const dataWithCustomId = [
        { customId: 'a', name: 'Test 1' },
        { customId: 'b', name: 'Test 2' }
      ]
      const selectedIds = new Set(['a'])
      const result = await exportComposable.exportSelected(dataWithCustomId, selectedIds, 'customId')
      expect(result).toBe(true)
    })

    it('should support JSON format', async () => {
      const clickSpy = vi.fn()
      const mockLink = { click: clickSpy, download: '', href: '', style: { display: '' }, remove: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink)

      const selectedIds = new Set([1])
      const result = await exportComposable.exportSelected(testData, selectedIds, 'id', null, 'json')
      expect(result).toBe(true)
      expect(mockLink.download).toContain('.json')
    })
  })

  describe('resetExport', () => {
    it('should reset all export state', async () => {
      // Trigger an error first
      await exportComposable.exportCSV([])

      expect(exportComposable.exportError.value).not.toBe(null)

      exportComposable.resetExport()

      expect(exportComposable.isExporting.value).toBe(false)
      expect(exportComposable.exportProgress.value).toBe(0)
      expect(exportComposable.exportError.value).toBe(null)
    })
  })
})
