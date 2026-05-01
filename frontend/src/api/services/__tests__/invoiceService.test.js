import { describe, it, expect, beforeEach, vi } from 'vitest'
import { invoiceService } from '../invoiceService'
import apiClient from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn()
  }
}))

const mockApiInvoice = {
  id: 1,
  invoice_number: 'INV-001',
  invoice_date: '2025-01-15',
  customer: 1,
  company: 1,
  status: 'draft',
  total_net: '100.00',
  total_gross: '119.00',
  lines: [],
  allowance_charges: []
}

describe('invoiceService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAll', () => {
    it('fetches paginated invoices and maps results', async () => {
      apiClient.get.mockResolvedValue({ data: { count: 1, results: [mockApiInvoice] } })

      const result = await invoiceService.getAll({ page: 1 })

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/', { params: { page: 1 } })
      expect(result.count).toBe(1)
      expect(Array.isArray(result.results)).toBe(true)
      expect(result.results[0].id).toBe(1)
    })

    it('returns response without results key as-is', async () => {
      apiClient.get.mockResolvedValue({ data: [mockApiInvoice] })

      const result = await invoiceService.getAll()

      expect(Array.isArray(result)).toBe(true)
    })
  })

  describe('getById', () => {
    it('fetches and maps a single invoice', async () => {
      apiClient.get.mockResolvedValue({ data: mockApiInvoice })

      const result = await invoiceService.getById(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/')
      expect(result.id).toBe(1)
    })
  })

  describe('create', () => {
    it('posts mapped invoice data and returns mapped response', async () => {
      apiClient.post.mockResolvedValue({ data: mockApiInvoice })

      const result = await invoiceService.create({ invoice_number: 'INV-001' })

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/', expect.any(Object))
      expect(result.id).toBe(1)
    })
  })

  describe('update', () => {
    it('puts mapped invoice data', async () => {
      apiClient.put.mockResolvedValue({ data: mockApiInvoice })

      const result = await invoiceService.update(1, { invoice_number: 'INV-001' })

      expect(apiClient.put).toHaveBeenCalledWith('/invoices/1/', expect.any(Object))
      expect(result.id).toBe(1)
    })
  })

  describe('patch', () => {
    it('patches mapped invoice data', async () => {
      apiClient.patch.mockResolvedValue({ data: mockApiInvoice })

      const result = await invoiceService.patch(1, { status: 'sent' })

      expect(apiClient.patch).toHaveBeenCalledWith('/invoices/1/', expect.any(Object))
      expect(result.id).toBe(1)
    })
  })

  describe('delete', () => {
    it('deletes an invoice by id', async () => {
      apiClient.delete.mockResolvedValue({})

      await invoiceService.delete(1)

      expect(apiClient.delete).toHaveBeenCalledWith('/invoices/1/')
    })
  })

  describe('createLine', () => {
    it('creates an invoice line and returns mapped response', async () => {
      apiClient.post.mockResolvedValue({ data: { id: 10, invoice: 1, quantity: '2.00', unit_price_net: '50.00' } })

      const result = await invoiceService.createLine(1, { quantity: 2, unit_price_net: 50 })

      expect(apiClient.post).toHaveBeenCalledWith('/invoice-lines/', expect.any(Object))
      expect(result.id).toBe(10)
    })
  })

  describe('updateLine', () => {
    it('patches an invoice line', async () => {
      apiClient.patch.mockResolvedValue({ data: { id: 10, invoice: 1, quantity: '3.00', unit_price_net: '50.00' } })

      const result = await invoiceService.updateLine(10, { quantity: 3 })

      expect(apiClient.patch).toHaveBeenCalledWith('/invoice-lines/10/', expect.any(Object))
      expect(result.id).toBe(10)
    })
  })

  describe('deleteLine', () => {
    it('deletes an invoice line', async () => {
      apiClient.delete.mockResolvedValue({})

      await invoiceService.deleteLine(10)

      expect(apiClient.delete).toHaveBeenCalledWith('/invoice-lines/10/')
    })
  })

  describe('createAllowanceCharge', () => {
    it('creates an allowance/charge entry', async () => {
      apiClient.post.mockResolvedValue({ data: { id: 20, charge_indicator: true, amount: '10.00' } })

      const result = await invoiceService.createAllowanceCharge({ charge_indicator: true, amount: 10 })

      expect(apiClient.post).toHaveBeenCalledWith('/invoice-allowance-charges/', expect.any(Object))
      expect(result.id).toBe(20)
    })
  })

  describe('updateAllowanceCharge', () => {
    it('patches an allowance/charge entry', async () => {
      apiClient.patch.mockResolvedValue({ data: { id: 20, charge_indicator: false, amount: '5.00' } })

      const result = await invoiceService.updateAllowanceCharge(20, { amount: 5 })

      expect(apiClient.patch).toHaveBeenCalledWith('/invoice-allowance-charges/20/', expect.any(Object))
      expect(result.id).toBe(20)
    })
  })

  describe('deleteAllowanceCharge', () => {
    it('deletes an allowance/charge entry', async () => {
      apiClient.delete.mockResolvedValue({})

      await invoiceService.deleteAllowanceCharge(20)

      expect(apiClient.delete).toHaveBeenCalledWith('/invoice-allowance-charges/20/')
    })
  })

  describe('generatePDF', () => {
    it('posts to generate_pdf with default COMFORT profile', async () => {
      apiClient.post.mockResolvedValue({ data: { status: 'ok', pdf_url: '/pdf/1' } })

      const result = await invoiceService.generatePDF(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/generate_pdf/?profile=COMFORT')
      expect(result.status).toBe('ok')
    })

    it('posts to generate_pdf with custom profile', async () => {
      apiClient.post.mockResolvedValue({ data: { status: 'ok' } })

      await invoiceService.generatePDF(1, 'BASIC')

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/generate_pdf/?profile=BASIC')
    })
  })

  describe('downloadPDF', () => {
    it('fetches PDF as blob', async () => {
      const blob = new Blob(['pdf'], { type: 'application/pdf' })
      apiClient.get.mockResolvedValue({ data: blob })

      const result = await invoiceService.downloadPDF(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/download_pdf/', { responseType: 'blob' })
      expect(result).toBe(blob)
    })
  })

  describe('downloadXML', () => {
    it('fetches XML as blob', async () => {
      const blob = new Blob(['<xml/>'], { type: 'application/xml' })
      apiClient.get.mockResolvedValue({ data: blob })

      const result = await invoiceService.downloadXML(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/download_xml/', { responseType: 'blob' })
      expect(result).toBe(blob)
    })
  })

  describe('generateXml', () => {
    it('posts to generate_xml with default XRECHNUNG profile', async () => {
      apiClient.post.mockResolvedValue({ data: { status: 'ok' } })

      const result = await invoiceService.generateXml(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/generate_xml/?profile=XRECHNUNG')
      expect(result.status).toBe('ok')
    })

    it('posts to generate_xml with custom profile', async () => {
      apiClient.post.mockResolvedValue({ data: { status: 'ok' } })

      await invoiceService.generateXml(1, 'EXTENDED')

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/generate_xml/?profile=EXTENDED')
    })
  })

  describe('downloadHybridPDF', () => {
    it('fetches hybrid PDF as blob', async () => {
      const blob = new Blob(['pdf'], { type: 'application/pdf' })
      apiClient.get.mockResolvedValue({ data: blob })

      const result = await invoiceService.downloadHybridPDF(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/download_hybrid_pdf/', { responseType: 'blob' })
      expect(result).toBe(blob)
    })
  })

  describe('validate', () => {
    it('posts to validate endpoint', async () => {
      apiClient.post.mockResolvedValue({ data: { valid: true, errors: [] } })

      const result = await invoiceService.validate(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/validate/')
      expect(result.valid).toBe(true)
    })
  })

  describe('markAsPaid', () => {
    it('marks invoice as paid with default empty data', async () => {
      apiClient.post.mockResolvedValue({ data: { ...mockApiInvoice, status: 'paid' } })

      const result = await invoiceService.markAsPaid(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/mark_as_paid/', {})
      expect(result.id).toBe(1)
    })

    it('marks invoice as paid with payment data', async () => {
      apiClient.post.mockResolvedValue({ data: { ...mockApiInvoice, status: 'paid' } })

      await invoiceService.markAsPaid(1, { payment_date: '2025-06-01' })

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/mark_as_paid/', { payment_date: '2025-06-01' })
    })
  })

  describe('cancel', () => {
    it('cancels invoice with default empty reason', async () => {
      apiClient.post.mockResolvedValue({ data: { ...mockApiInvoice, status: 'cancelled' } })

      const result = await invoiceService.cancel(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/cancel/', { reason: '' })
      expect(result.id).toBe(1)
    })

    it('cancels invoice with a reason', async () => {
      apiClient.post.mockResolvedValue({ data: { ...mockApiInvoice, status: 'cancelled' } })

      await invoiceService.cancel(1, 'Fehler')

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/cancel/', { reason: 'Fehler' })
    })
  })

  describe('sendEmail', () => {
    it('sends email with required recipient', async () => {
      apiClient.post.mockResolvedValue({ data: { message: 'sent', recipient: 'a@b.com' } })

      const result = await invoiceService.sendEmail(1, { recipient: 'a@b.com' })

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/send_email/', {
        recipient: 'a@b.com',
        message: '',
        attach_xml: false
      })
      expect(result.recipient).toBe('a@b.com')
    })

    it('sends email with message and attachXml flag', async () => {
      apiClient.post.mockResolvedValue({ data: { message: 'sent' } })

      await invoiceService.sendEmail(1, { recipient: 'x@y.de', message: 'Hallo', attachXml: true })

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/send_email/', {
        recipient: 'x@y.de',
        message: 'Hallo',
        attach_xml: true
      })
    })
  })

  describe('acquireEditLock', () => {
    it('acquires edit lock for invoice', async () => {
      apiClient.post.mockResolvedValue({ data: { message: 'Lock acquired', editing_since: '2025-01-01T10:00:00Z' } })

      const result = await invoiceService.acquireEditLock(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/acquire_edit_lock/')
      expect(result.message).toContain('Lock')
    })
  })

  describe('releaseEditLock', () => {
    it('releases edit lock for invoice', async () => {
      apiClient.post.mockResolvedValue({ data: {} })

      await invoiceService.releaseEditLock(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/release_edit_lock/')
    })
  })

  describe('refreshEditLock', () => {
    it('refreshes edit lock for invoice', async () => {
      apiClient.post.mockResolvedValue({ data: {} })

      await invoiceService.refreshEditLock(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/refresh_edit_lock/')
    })
  })

  describe('mapInvoiceFromApi (via getById)', () => {
    it('maps nested lines and allowance_charges', async () => {
      const apiData = {
        ...mockApiInvoice,
        lines: [{ id: 1, invoice: 1, quantity: '2.00', unit_price_net: '50.00', vat_rate: '19.00', description: 'Item' }],
        allowance_charges: [{ id: 1, charge_indicator: true, amount: '5.00', reason: 'Shipping' }]
      }
      apiClient.get.mockResolvedValue({ data: apiData })

      const result = await invoiceService.getById(1)

      expect(Array.isArray(result.lines)).toBe(true)
      expect(Array.isArray(result.allowance_charges)).toBe(true)
    })
  })
})
