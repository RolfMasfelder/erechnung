import { describe, it, expect, beforeEach, vi } from 'vitest'
import { countryService } from '../countryService'
import apiClient from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn()
  }
}))

describe('countryService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getAll', () => {
    it('returns plain array when response is array', async () => {
      const countries = [{ code: 'DE', name: 'Germany' }, { code: 'FR', name: 'France' }]
      apiClient.get.mockResolvedValue({ data: countries })

      const result = await countryService.getAll()

      expect(apiClient.get).toHaveBeenCalledWith('/countries/', { params: { page_size: 300 } })
      expect(result).toEqual(countries)
    })

    it('returns results array from paginated response', async () => {
      const countries = [{ code: 'DE', name: 'Germany' }]
      apiClient.get.mockResolvedValue({ data: { count: 1, results: countries } })

      const result = await countryService.getAll()

      expect(result).toEqual(countries)
    })

    it('returns empty array when paginated response has no results', async () => {
      apiClient.get.mockResolvedValue({ data: {} })

      const result = await countryService.getAll()

      expect(result).toEqual([])
    })

    it('accepts custom params', async () => {
      apiClient.get.mockResolvedValue({ data: [] })

      await countryService.getAll({ page_size: 10, page: 2 })

      expect(apiClient.get).toHaveBeenCalledWith('/countries/', { params: { page_size: 10, page: 2 } })
    })
  })

  describe('getByCode', () => {
    it('fetches country by code', async () => {
      const country = { code: 'DE', name: 'Germany', vat_rate: 19 }
      apiClient.get.mockResolvedValue({ data: country })

      const result = await countryService.getByCode('DE')

      expect(apiClient.get).toHaveBeenCalledWith('/countries/DE/')
      expect(result).toEqual(country)
    })
  })

  describe('getTaxRates', () => {
    it('fetches tax rates for a country', async () => {
      const rates = [{ rate: 19, valid_from: '2007-01-01' }]
      apiClient.get.mockResolvedValue({ data: rates })

      const result = await countryService.getTaxRates('DE')

      expect(apiClient.get).toHaveBeenCalledWith('/countries/DE/tax-rates/', { params: {} })
      expect(result).toEqual(rates)
    })

    it('passes on_date param when provided', async () => {
      apiClient.get.mockResolvedValue({ data: [] })

      await countryService.getTaxRates('DE', { on_date: '2024-01-01' })

      expect(apiClient.get).toHaveBeenCalledWith('/countries/DE/tax-rates/', {
        params: { on_date: '2024-01-01' }
      })
    })
  })
})
