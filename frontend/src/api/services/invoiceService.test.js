import { describe, it, expect, beforeEach, vi } from 'vitest'
import { invoiceService } from '@/api/services/invoiceService'
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

describe('invoiceService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAll', () => {
    it('should fetch all invoices with default params', async () => {
      const mockResponse = {
        data: {
          count: 2,
          results: [
            { id: 1, invoice_number: 'INV-001' },
            { id: 2, invoice_number: 'INV-002' }
          ]
        }
      }

      apiClient.get.mockResolvedValue(mockResponse)

      const result = await invoiceService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/', { params: {} })
      expect(result).toEqual(mockResponse.data)
    })

    it('should fetch invoices with custom params', async () => {
      const params = { page: 2, page_size: 10, status: 'PAID' }
      const mockResponse = { data: { count: 5, results: [] } }

      apiClient.get.mockResolvedValue(mockResponse)

      await invoiceService.getAll(params)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/', { params })
    })
  })

  describe('getById', () => {
    it('should fetch single invoice by id', async () => {
      const mockInvoice = { id: 1, invoice_number: 'INV-001', total_amount: 100.00 }
      apiClient.get.mockResolvedValue({ data: mockInvoice })

      const result = await invoiceService.getById(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/')
      expect(result).toEqual(mockInvoice)
    })
  })

  describe('create', () => {
    it('should create new invoice', async () => {
      const newInvoice = {
        invoice_number: 'INV-003',
        company: 1,
        business_partner: 2,
        total_amount: 200.00
      }
      const mockResponse = { data: { id: 3, ...newInvoice } }

      apiClient.post.mockResolvedValue(mockResponse)

      const result = await invoiceService.create(newInvoice)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/', newInvoice)
      expect(result.id).toBe(3)
      expect(result.company).toBe(1)
    })
  })

  describe('update', () => {
    it('should update invoice (PUT)', async () => {
      const updateData = { invoice_number: 'INV-001-UPDATED' }
      const mockResponse = { data: { id: 1, ...updateData } }

      apiClient.put.mockResolvedValue(mockResponse)

      const result = await invoiceService.update(1, updateData)

      expect(apiClient.put).toHaveBeenCalledWith('/invoices/1/', updateData)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('patch', () => {
    it('should partially update invoice (PATCH)', async () => {
      const patchData = { status: 'PAID' }
      const mockResponse = { data: { id: 1, status: 'PAID' } }

      apiClient.patch.mockResolvedValue(mockResponse)

      const result = await invoiceService.patch(1, patchData)

      expect(apiClient.patch).toHaveBeenCalledWith('/invoices/1/', patchData)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('delete', () => {
    it('should delete invoice', async () => {
      apiClient.delete.mockResolvedValue({})

      await invoiceService.delete(1)

      expect(apiClient.delete).toHaveBeenCalledWith('/invoices/1/')
    })
  })

  describe('downloadPDF', () => {
    it('should download PDF as blob', async () => {
      const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' })
      apiClient.get.mockResolvedValue({ data: mockBlob })

      const result = await invoiceService.downloadPDF(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/download_pdf/', {
        responseType: 'blob'
      })
      expect(result).toEqual(mockBlob)
    })
  })

  describe('downloadXML', () => {
    it('should download XML as blob', async () => {
      const mockBlob = new Blob(['<xml></xml>'], { type: 'application/xml' })
      apiClient.get.mockResolvedValue({ data: mockBlob })

      const result = await invoiceService.downloadXML(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/download_xml/', {
        responseType: 'blob'
      })
      expect(result).toEqual(mockBlob)
    })
  })

  describe('downloadHybridPDF', () => {
    it('should download hybrid PDF as blob', async () => {
      const mockBlob = new Blob(['Hybrid PDF'], { type: 'application/pdf' })
      apiClient.get.mockResolvedValue({ data: mockBlob })

      const result = await invoiceService.downloadHybridPDF(1)

      expect(apiClient.get).toHaveBeenCalledWith('/invoices/1/download_hybrid_pdf/', {
        responseType: 'blob'
      })
      expect(result).toEqual(mockBlob)
    })
  })

  describe('validate', () => {
    it('should validate invoice', async () => {
      const mockValidation = { valid: true, errors: [] }
      apiClient.post.mockResolvedValue({ data: mockValidation })

      const result = await invoiceService.validate(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/validate/')
      expect(result).toEqual(mockValidation)
    })
  })

  describe('markAsPaid', () => {
    it('should mark invoice as paid', async () => {
      const paymentData = { payment_date: '2024-01-15', payment_method: 'BANK_TRANSFER' }
      const mockResponse = { data: { id: 1, status: 'PAID', ...paymentData } }

      apiClient.post.mockResolvedValue(mockResponse)

      const result = await invoiceService.markAsPaid(1, paymentData)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/mark_as_paid/', paymentData)
      expect(result).toEqual(mockResponse.data)
    })

    it('should mark as paid with empty payment data', async () => {
      const mockResponse = { data: { id: 1, status: 'PAID' } }
      apiClient.post.mockResolvedValue(mockResponse)

      await invoiceService.markAsPaid(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/mark_as_paid/', {})
    })
  })

  describe('cancel', () => {
    it('should cancel invoice with reason', async () => {
      const reason = 'Customer requested cancellation'
      const mockResponse = { data: { id: 1, status: 'CANCELLED' } }

      apiClient.post.mockResolvedValue(mockResponse)

      const result = await invoiceService.cancel(1, reason)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/cancel/', { reason })
      expect(result).toEqual(mockResponse.data)
    })

    it('should cancel invoice without reason', async () => {
      const mockResponse = { data: { id: 1, status: 'CANCELLED' } }
      apiClient.post.mockResolvedValue(mockResponse)

      await invoiceService.cancel(1)

      expect(apiClient.post).toHaveBeenCalledWith('/invoices/1/cancel/', { reason: '' })
    })
  })
})
