import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the API client
vi.mock('../../client', () => ({
  default: {
    post: vi.fn()
  }
}))

import apiClient from '../../client'
import { importService } from '../importService'

describe('importService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('importBusinessPartners', () => {
    it('should call API with correct endpoint and data', async () => {
      const mockResponse = {
        data: {
          success: true,
          imported_count: 2,
          skipped_count: 0,
          error_count: 0,
          errors: [],
          imported_ids: [1, 2]
        }
      }
      apiClient.post.mockResolvedValue(mockResponse)

      const rows = [
        { company_name: 'Test GmbH', address_line1: 'Test Street', postal_code: '12345', city: 'Berlin' },
        { company_name: 'Other AG', address_line1: 'Other Street', postal_code: '54321', city: 'Munich' }
      ]

      const result = await importService.importBusinessPartners(rows)

      expect(apiClient.post).toHaveBeenCalledWith('/business-partners/import/', {
        rows,
        skip_duplicates: true,
        update_existing: false
      })
      expect(result.success).toBe(true)
      expect(result.imported_count).toBe(2)
    })

    it('should pass custom options', async () => {
      const mockResponse = { data: { success: true, imported_count: 1 } }
      apiClient.post.mockResolvedValue(mockResponse)

      const rows = [{ company_name: 'Test' }]
      await importService.importBusinessPartners(rows, {
        skipDuplicates: false,
        updateExisting: true
      })

      expect(apiClient.post).toHaveBeenCalledWith('/business-partners/import/', {
        rows,
        skip_duplicates: false,
        update_existing: true
      })
    })
  })

  describe('importProducts', () => {
    it('should call API with correct endpoint', async () => {
      const mockResponse = {
        data: {
          success: true,
          imported_count: 1,
          errors: []
        }
      }
      apiClient.post.mockResolvedValue(mockResponse)

      const rows = [{ name: 'Test Product', base_price: '99.99' }]

      const result = await importService.importProducts(rows)

      expect(apiClient.post).toHaveBeenCalledWith('/products/import/', {
        rows,
        skip_duplicates: true,
        update_existing: false
      })
      expect(result.success).toBe(true)
    })
  })

  describe('mapBusinessPartnerHeaders', () => {
    it('should map German headers to API field names', () => {
      const headers = ['Firmenname', 'Straße', 'PLZ', 'Ort', 'Land', 'USt-IdNr.', 'E-Mail']

      const mapped = importService.mapBusinessPartnerHeaders(headers)

      expect(mapped).toEqual([
        'company_name',
        'address_line1',
        'postal_code',
        'city',
        'country_code',
        'vat_id',
        'email'
      ])
    })

    it('should convert unknown headers to snake_case', () => {
      const headers = ['Custom Field', 'Another One']

      const mapped = importService.mapBusinessPartnerHeaders(headers)

      expect(mapped).toEqual(['custom_field', 'another_one'])
    })
  })

  describe('mapProductHeaders', () => {
    it('should map German product headers', () => {
      const headers = ['Produktname', 'Artikelnummer', 'Grundpreis', 'Kategorie', 'MwSt-Satz']

      const mapped = importService.mapProductHeaders(headers)

      expect(mapped).toEqual([
        'name',
        'product_code',
        'base_price',
        'category',
        'tax_rate'
      ])
    })
  })

  describe('transformBusinessPartnerData', () => {
    it('should transform data with mapped headers', () => {
      const data = [
        { 'Firmenname': 'Test GmbH', 'PLZ': '12345', 'Aktiv': 'ja' }
      ]
      const headers = ['Firmenname', 'PLZ', 'Aktiv']

      const transformed = importService.transformBusinessPartnerData(data, headers)

      expect(transformed[0].company_name).toBe('Test GmbH')
      expect(transformed[0].postal_code).toBe('12345')
      expect(transformed[0].is_active).toBe(true)
    })

    it('should handle boolean values', () => {
      const data = [
        { 'Aktiv': 'ja' },
        { 'Aktiv': '1' },
        { 'Aktiv': 'true' },
        { 'Aktiv': 'nein' },
        { 'Aktiv': '0' },
        { 'Aktiv': 'false' }
      ]
      const headers = ['Aktiv']

      const transformed = importService.transformBusinessPartnerData(data, headers)

      expect(transformed[0].is_active).toBe(true)
      expect(transformed[1].is_active).toBe(true)
      expect(transformed[2].is_active).toBe(true)
      expect(transformed[3].is_active).toBe(false)
      expect(transformed[4].is_active).toBe(false)
      expect(transformed[5].is_active).toBe(false)
    })
  })

  describe('transformProductData', () => {
    it('should transform product data', () => {
      const data = [
        { 'Produktname': 'Widget', 'Grundpreis': '29,99', 'Bestand': '100' }
      ]
      const headers = ['Produktname', 'Grundpreis', 'Bestand']

      const transformed = importService.transformProductData(data, headers)

      expect(transformed[0].name).toBe('Widget')
      expect(transformed[0].base_price).toBe(29.99)
      expect(transformed[0].stock_quantity).toBe(100)
    })

    it('should handle German decimal format', () => {
      const data = [
        { 'Grundpreis': '1.234,56' }
      ]
      const headers = ['Grundpreis']

      const transformed = importService.transformProductData(data, headers)

      expect(transformed[0].base_price).toBe(1234.56)
    })
  })

  describe('parseBoolean', () => {
    it('should parse various true values', () => {
      expect(importService.parseBoolean('true')).toBe(true)
      expect(importService.parseBoolean('1')).toBe(true)
      expect(importService.parseBoolean('ja')).toBe(true)
      expect(importService.parseBoolean('yes')).toBe(true)
      expect(importService.parseBoolean('x')).toBe(true)
      expect(importService.parseBoolean('aktiv')).toBe(true)
      expect(importService.parseBoolean('active')).toBe(true)
      expect(importService.parseBoolean(true)).toBe(true)
    })

    it('should parse various false values', () => {
      expect(importService.parseBoolean('false')).toBe(false)
      expect(importService.parseBoolean('0')).toBe(false)
      expect(importService.parseBoolean('nein')).toBe(false)
      expect(importService.parseBoolean('')).toBe(false)
      expect(importService.parseBoolean(false)).toBe(false)
    })

    it('should parse non-string truthy/falsy', () => {
      expect(importService.parseBoolean(1)).toBe(true)
      expect(importService.parseBoolean(0)).toBe(false)
      expect(importService.parseBoolean(null)).toBe(false)
    })
  })

  describe('parseGermanDecimal', () => {
    it('returns null for null/empty', () => {
      expect(importService.parseGermanDecimal(null)).toBeNull()
      expect(importService.parseGermanDecimal('')).toBeNull()
    })

    it('parses German decimal string', () => {
      expect(importService.parseGermanDecimal('1.234,56')).toBeCloseTo(1234.56)
    })

    it('parses plain number value (not string)', () => {
      expect(importService.parseGermanDecimal(99.99)).toBe(99.99)
    })

    it('parses non-string number-like value', () => {
      expect(importService.parseGermanDecimal(42)).toBe(42)
    })
  })

  describe('transformBusinessPartnerData with numeric fields', () => {
    it('should parse payment_terms as integer', () => {
      const data = [{ 'Zahlungsziel': '14' }]
      const headers = ['Zahlungsziel']
      const result = importService.transformBusinessPartnerData(data, headers)
      expect(result[0].payment_terms).toBe(14)
    })

    it('should default payment_terms to 30 when invalid', () => {
      const data = [{ 'Zahlungsziel': 'abc' }]
      const headers = ['Zahlungsziel']
      const result = importService.transformBusinessPartnerData(data, headers)
      expect(result[0].payment_terms).toBe(30)
    })

    it('should parse credit_limit as decimal', () => {
      const data = [{ 'Kreditlimit': '5.000,00' }]
      const headers = ['Kreditlimit']
      const result = importService.transformBusinessPartnerData(data, headers)
      expect(result[0].credit_limit).toBeCloseTo(5000)
    })
  })

  describe('transformProductData with bool/numeric fields', () => {
    it('should parse is_sellable and track_inventory booleans', () => {
      const data = [{ 'Verkäuflich': 'ja', 'Lager verfolgen': '0' }]
      const headers = ['Verkäuflich', 'Lager verfolgen']
      const result = importService.transformProductData(data, headers)
      expect(result[0].is_sellable).toBe(true)
      expect(result[0].track_inventory).toBe(false)
    })

    it('should parse reorder_level as integer', () => {
      const data = [{ 'Meldebestand': '5' }]
      const headers = ['Meldebestand']
      const result = importService.transformProductData(data, headers)
      expect(result[0].reorder_level).toBe(5)
    })

    it('should parse cost_price and tax_rate as decimal', () => {
      const data = [{ 'EK-Preis': '19,00', 'MwSt-Satz': '19,0' }]
      const headers = ['EK-Preis', 'MwSt-Satz']
      const result = importService.transformProductData(data, headers)
      expect(result[0].cost_price).toBeCloseTo(19)
      expect(result[0].tax_rate).toBeCloseTo(19)
    })
  })
})
