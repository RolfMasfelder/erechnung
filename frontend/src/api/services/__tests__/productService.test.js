import { describe, it, expect, beforeEach, vi } from 'vitest'
import { productService } from '../productService'
import apiClient from '@/api/client'

// Mock des API-Clients
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

describe('productService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAll', () => {
    it('ruft alle Produkte ab', async () => {
      const mockResponse = {
        data: {
          count: 2,
          results: [
            { id: 1, name: 'Produkt 1', unit_price: 100 },
            { id: 2, name: 'Produkt 2', unit_price: 200 }
          ]
        }
      }

      apiClient.get.mockResolvedValue(mockResponse)

      const result = await productService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/products/', { params: {} })
      expect(result).toEqual(mockResponse.data)
      expect(result.results).toHaveLength(2)
    })

    it('übergibt Query-Parameter korrekt', async () => {
      const mockResponse = { data: { results: [] } }
      apiClient.get.mockResolvedValue(mockResponse)

      await productService.getAll({
        search: 'Test',
        is_active: 'true',
        page: 2
      })

      expect(apiClient.get).toHaveBeenCalledWith('/products/', {
        params: {
          search: 'Test',
          is_active: 'true',
          page: 2
        }
      })
    })
  })

  describe('getById', () => {
    it('ruft einzelnes Produkt ab', async () => {
      const mockProduct = {
        id: 1,
        name: 'Test Produkt',
        unit_price: 99.99,
        vat_rate: 19
      }

      apiClient.get.mockResolvedValue({ data: mockProduct })

      const result = await productService.getById(1)

      expect(apiClient.get).toHaveBeenCalledWith('/products/1/')
      expect(result).toEqual(mockProduct)
    })
  })

  describe('create', () => {
    it('erstellt neues Produkt', async () => {
      const newProduct = {
        name: 'Neues Produkt',
        base_price: 150,
        default_tax_rate: 19,
        is_active: true
      }

      const mockResponse = { data: { id: 3, ...newProduct } }
      apiClient.post.mockResolvedValue(mockResponse)

      const result = await productService.create(newProduct)

      expect(apiClient.post).toHaveBeenCalledWith('/products/', newProduct)
      expect(result.id).toBe(3)
      expect(result.name).toBe('Neues Produkt')
    })
  })

  describe('update', () => {
    it('aktualisiert bestehendes Produkt', async () => {
      const updatedData = {
        name: 'Aktualisiertes Produkt',
        base_price: 175
      }

      const mockResponse = { data: { id: 1, ...updatedData } }
      apiClient.put.mockResolvedValue(mockResponse)

      const result = await productService.update(1, updatedData)

      expect(apiClient.put).toHaveBeenCalledWith('/products/1/', updatedData)
      expect(result.name).toBe('Aktualisiertes Produkt')
    })
  })

  describe('delete', () => {
    it('löscht Produkt', async () => {
      apiClient.delete.mockResolvedValue({ data: null })

      await productService.delete(1)

      expect(apiClient.delete).toHaveBeenCalledWith('/products/1/')
    })
  })

  describe('Fehlerbehandlung', () => {
    it('wirft Fehler bei fehlgeschlagenem Request', async () => {
      const error = new Error('Network Error')
      apiClient.get.mockRejectedValue(error)

      await expect(productService.getAll()).rejects.toThrow('Network Error')
    })

    it('behandelt 404-Fehler korrekt', async () => {
      const error = {
        response: {
          status: 404,
          data: { detail: 'Nicht gefunden' }
        }
      }
      apiClient.get.mockRejectedValue(error)

      await expect(productService.getById(999)).rejects.toMatchObject({
        response: { status: 404 }
      })
    })
  })
})
