import { describe, it, expect } from 'vitest'
import { formatCurrency, formatNumber, formatPercentage, parseNumber } from '@/utils/formatting'

describe('formatting', () => {
  describe('formatCurrency', () => {
    it('should format currency with default EUR and de-DE locale', () => {
      const result = formatCurrency(1234.56)
      expect(result).toContain('1.234,56')
      expect(result).toContain('€')
    })

    it('should format currency with custom currency', () => {
      const result = formatCurrency(1234.56, 'USD', 'en-US')
      expect(result).toBe('$1,234.56')
    })

    it('should return empty string for null', () => {
      expect(formatCurrency(null)).toBe('')
    })

    it('should return empty string for undefined', () => {
      expect(formatCurrency(undefined)).toBe('')
    })

    it('should format zero', () => {
      const result = formatCurrency(0)
      expect(result).toContain('0,00')
      expect(result).toContain('€')
    })

    it('should format negative amounts', () => {
      const result = formatCurrency(-1234.56)
      expect(result).toContain('-1.234,56')
      expect(result).toContain('€')
    })
  })

  describe('formatNumber', () => {
    it('should format number with default 2 decimals', () => {
      const result = formatNumber(1234.567)
      expect(result).toBe('1.234,57')
    })

    it('should format with custom decimals', () => {
      const result = formatNumber(1234.567, 3)
      expect(result).toBe('1.234,567')
    })

    it('should format with 0 decimals', () => {
      const result = formatNumber(1234.567, 0)
      expect(result).toBe('1.235')
    })

    it('should return empty string for null', () => {
      expect(formatNumber(null)).toBe('')
    })

    it('should format with custom locale', () => {
      const result = formatNumber(1234.56, 2, 'en-US')
      expect(result).toBe('1,234.56')
    })
  })

  describe('formatPercentage', () => {
    it('should format percentage (0.19 = 19%)', () => {
      const result = formatPercentage(0.19)
      expect(result).toContain('19,00')
      expect(result).toContain('%')
    })

    it('should format with custom decimals', () => {
      const result = formatPercentage(0.195, 1)
      expect(result).toContain('19,5')
      expect(result).toContain('%')
    })

    it('should format 100%', () => {
      const result = formatPercentage(1)
      expect(result).toContain('100,00')
      expect(result).toContain('%')
    })

    it('should return empty string for null', () => {
      expect(formatPercentage(null)).toBe('')
    })

    it('should format with custom locale', () => {
      const result = formatPercentage(0.19, 2, 'en-US')
      expect(result).toBe('19.00%')
    })
  })

  describe('parseNumber', () => {
    it('should parse German format (1.234,56)', () => {
      const result = parseNumber('1.234,56')
      expect(result).toBe(1234.56)
    })

    it('should parse without thousand separator', () => {
      const result = parseNumber('1234,56')
      expect(result).toBe(1234.56)
    })

    it('should parse integer', () => {
      const result = parseNumber('1234')
      expect(result).toBe(1234)
    })

    it('should return null for empty string', () => {
      expect(parseNumber('')).toBeNull()
    })

    it('should return null for null', () => {
      expect(parseNumber(null)).toBeNull()
    })

    it('should return null for undefined', () => {
      expect(parseNumber(undefined)).toBeNull()
    })

    it('should return null for invalid input', () => {
      expect(parseNumber('abc')).toBeNull()
    })

    it('should handle negative numbers', () => {
      const result = parseNumber('-1.234,56')
      expect(result).toBe(-1234.56)
    })

    it('should handle decimal-only numbers', () => {
      const result = parseNumber('0,56')
      expect(result).toBe(0.56)
    })
  })
})
