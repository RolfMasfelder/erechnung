import { describe, it, expect, beforeEach, vi } from 'vitest'
import { businessPartnerService, toApi, fromApi } from '../businessPartnerService'
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

describe('businessPartnerService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('toApi', () => {
    it('should map UI field names to API field names', () => {
      const uiData = {
        name: 'Test GmbH',
        street: 'Musterstraße 1',
        tax_number: '12345',
        postal_code: '10115',
        city: 'Berlin',
        country: 'DE',
        vat_id: 'DE123',
        email: 'test@example.com',
        notes: 'Some notes'
      }
      const apiData = toApi(uiData)
      expect(apiData.company_name).toBe('Test GmbH')
      expect(apiData.address_line1).toBe('Musterstraße 1')
      expect(apiData.tax_id).toBe('12345')
      expect(apiData.postal_code).toBe('10115')
      expect(apiData.city).toBe('Berlin')
      // UI-only fields should be stripped
      expect(apiData.notes).toBeUndefined()
      // Original UI names should not be present
      expect(apiData.name).toBeUndefined()
      expect(apiData.street).toBeUndefined()
      expect(apiData.tax_number).toBeUndefined()
    })
  })

  describe('fromApi', () => {
    it('should map API field names to UI field names', () => {
      const apiData = {
        id: 1,
        company_name: 'Test GmbH',
        address_line1: 'Musterstraße 1',
        tax_id: '12345',
        postal_code: '10115',
        city: 'Berlin'
      }
      const uiData = fromApi(apiData)
      expect(uiData.name).toBe('Test GmbH')
      expect(uiData.street).toBe('Musterstraße 1')
      expect(uiData.tax_number).toBe('12345')
      expect(uiData.id).toBe(1)
      expect(uiData.postal_code).toBe('10115')
    })

    it('should roundtrip correctly', () => {
      const original = { name: 'X', street: 'Y', tax_number: 'Z', city: 'W' }
      const roundtripped = fromApi(toApi(original))
      expect(roundtripped.name).toBe('X')
      expect(roundtripped.street).toBe('Y')
      expect(roundtripped.tax_number).toBe('Z')
      expect(roundtripped.city).toBe('W')
    })
  })

  describe('getAll', () => {
    it('should fetch all customers with mapped fields', async () => {
      const mockResponse = {
        data: {
          count: 2,
          results: [
            { id: 1, company_name: 'Customer A', address_line1: 'Street A' },
            { id: 2, company_name: 'Customer B', address_line1: 'Street B' }
          ]
        }
      }

      apiClient.get.mockResolvedValue(mockResponse)

      const result = await businessPartnerService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/business-partners/', { params: {} })
      expect(result.results[0].name).toBe('Customer A')
      expect(result.results[0].street).toBe('Street A')
      expect(result.results[1].name).toBe('Customer B')
    })

    it('should pass query parameters', async () => {
      const mockResponse = { data: { count: 0, results: [] } }
      apiClient.get.mockResolvedValue(mockResponse)

      await businessPartnerService.getAll({ search: 'test', page: 2 })

      expect(apiClient.get).toHaveBeenCalledWith('/business-partners/', {
        params: { search: 'test', page: 2 }
      })
    })

    it('handles non-paginated array response', async () => {
      const mockResponse = { data: [{ id: 1, company_name: 'Customer A' }] }
      apiClient.get.mockResolvedValue(mockResponse)

      const result = await businessPartnerService.getAll()

      expect(Array.isArray(result)).toBe(true)
    })
  })

  describe('getById', () => {
    it('should fetch a customer by id with mapped fields', async () => {
      const apiCustomer = { id: 1, company_name: 'Test Customer', address_line1: 'Test St. 1', tax_id: '999' }
      apiClient.get.mockResolvedValue({ data: apiCustomer })

      const result = await businessPartnerService.getById(1)

      expect(apiClient.get).toHaveBeenCalledWith('/business-partners/1/')
      expect(result.name).toBe('Test Customer')
      expect(result.street).toBe('Test St. 1')
      expect(result.tax_number).toBe('999')
    })
  })

  describe('create', () => {
    it('should send mapped fields to API', async () => {
      const uiData = { name: 'New Customer', street: 'New St. 1', email: 'test@example.com' }
      const mockResponse = { data: { id: 1, company_name: 'New Customer', address_line1: 'New St. 1', email: 'test@example.com' } }
      apiClient.post.mockResolvedValue(mockResponse)

      const result = await businessPartnerService.create(uiData)

      expect(apiClient.post).toHaveBeenCalledWith('/business-partners/',
        expect.objectContaining({
          company_name: 'New Customer',
          address_line1: 'New St. 1',
          email: 'test@example.com'
        })
      )
      expect(result.name).toBe('New Customer')
      expect(result.street).toBe('New St. 1')
    })
  })

  describe('update', () => {
    it('should send mapped fields to API', async () => {
      const uiData = { name: 'Updated Customer', street: 'Updated St.' }
      const mockResponse = { data: { id: 1, company_name: 'Updated Customer', address_line1: 'Updated St.' } }
      apiClient.put.mockResolvedValue(mockResponse)

      const result = await businessPartnerService.update(1, uiData)

      expect(apiClient.put).toHaveBeenCalledWith('/business-partners/1/',
        expect.objectContaining({
          company_name: 'Updated Customer',
          address_line1: 'Updated St.'
        })
      )
      expect(result.name).toBe('Updated Customer')
    })
  })

  describe('delete', () => {
    it('should delete a customer', async () => {
      apiClient.delete.mockResolvedValue({})

      await businessPartnerService.delete(1)

      expect(apiClient.delete).toHaveBeenCalledWith('/business-partners/1/')
    })
  })

  describe('patch', () => {
    it('patches business partner data', async () => {
      const uiData = { name: 'Patched GmbH' }
      const mockResponse = { data: { id: 1, company_name: 'Patched GmbH' } }
      apiClient.patch.mockResolvedValue(mockResponse)

      const result = await businessPartnerService.patch(1, uiData)

      expect(apiClient.patch).toHaveBeenCalledWith('/business-partners/1/', expect.any(Object))
      expect(result.name).toBe('Patched GmbH')
    })
  })
})
