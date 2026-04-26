import { describe, it, expect, beforeEach, vi } from 'vitest'
import { companyService } from '../companyService'
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

describe('companyService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAll', () => {
    it('should fetch all companies', async () => {
      const mockResponse = {
        data: {
          count: 2,
          results: [
            { id: 1, name: 'Company A' },
            { id: 2, name: 'Company B' }
          ]
        }
      }

      apiClient.get.mockResolvedValue(mockResponse)

      const result = await companyService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/companies/', { params: {} })
      expect(result).toEqual(mockResponse.data)
    })

    it('should pass query parameters', async () => {
      const mockResponse = { data: { count: 0, results: [] } }
      apiClient.get.mockResolvedValue(mockResponse)

      await companyService.getAll({ search: 'test', page: 2 })

      expect(apiClient.get).toHaveBeenCalledWith('/companies/', {
        params: { search: 'test', page: 2 }
      })
    })
  })

  describe('getById', () => {
    it('should fetch a company by id', async () => {
      const mockCompany = { id: 1, name: 'Test Company' }
      apiClient.get.mockResolvedValue({ data: mockCompany })

      const result = await companyService.getById(1)

      expect(apiClient.get).toHaveBeenCalledWith('/companies/1/')
      expect(result).toEqual(mockCompany)
    })
  })

  describe('create', () => {
    it('should create a new company', async () => {
      const newCompany = { name: 'New Company', address_line1: 'Test St.' }
      const mockResponse = { data: { id: 1, ...newCompany } }
      apiClient.post.mockResolvedValue(mockResponse)

      const result = await companyService.create(newCompany)

      expect(apiClient.post).toHaveBeenCalledWith('/companies/', newCompany)
      expect(result.name).toBe('New Company')
    })
  })

  describe('update', () => {
    it('should update an existing company', async () => {
      const updatedCompany = { name: 'Updated Company' }
      const mockResponse = { data: { id: 1, ...updatedCompany } }
      apiClient.put.mockResolvedValue(mockResponse)

      const result = await companyService.update(1, updatedCompany)

      expect(apiClient.put).toHaveBeenCalledWith('/companies/1/', updatedCompany)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('delete', () => {
    it('should delete a company', async () => {
      apiClient.delete.mockResolvedValue({})

      await companyService.delete(1)

      expect(apiClient.delete).toHaveBeenCalledWith('/companies/1/')
    })
  })

  describe('patch', () => {
    it('should send a PATCH request', async () => {
      const patchData = { name: 'Patched Name' }
      const mockResponse = { data: { id: 1, ...patchData } }
      apiClient.patch.mockResolvedValue(mockResponse)

      const result = await companyService.patch(1, patchData)

      expect(apiClient.patch).toHaveBeenCalledWith('/companies/1/', patchData)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('Logo-Upload via FormData', () => {
    it('create: sendet FormData wenn Logo-Datei vorhanden ist', async () => {
      const mockFile = new File(['png-data'], 'logo.png', { type: 'image/png' })
      const formData = new FormData()
      formData.append('name', 'Logo Firma')
      formData.append('tax_id', 'TAX123')
      formData.append('logo', mockFile)

      const mockResponse = {
        data: { id: 5, name: 'Logo Firma', logo: '/media/company_logos/logo.png' }
      }
      apiClient.post.mockResolvedValue(mockResponse)

      const result = await companyService.create(formData)

      expect(apiClient.post).toHaveBeenCalledWith('/companies/', formData)
      expect(result.logo).toContain('logo.png')
    })

    it('patch: sendet FormData mit Logo-Datei zum Ersetzen', async () => {
      const mockFile = new File(['png-data'], 'new-logo.png', { type: 'image/png' })
      const formData = new FormData()
      formData.append('logo', mockFile)

      const mockResponse = {
        data: { id: 1, logo: '/media/company_logos/new-logo.png' }
      }
      apiClient.patch.mockResolvedValue(mockResponse)

      const result = await companyService.patch(1, formData)

      expect(apiClient.patch).toHaveBeenCalledWith('/companies/1/', formData)
      expect(result.logo).toContain('new-logo.png')
    })

    it('patch: sendet leeren logo-String zum Entfernen des Logos', async () => {
      const formData = new FormData()
      formData.append('logo', '')

      const mockResponse = { data: { id: 1, logo: null } }
      apiClient.patch.mockResolvedValue(mockResponse)

      const result = await companyService.patch(1, formData)

      expect(apiClient.patch).toHaveBeenCalledWith('/companies/1/', formData)
      expect(result.logo).toBeNull()
    })
  })
})
