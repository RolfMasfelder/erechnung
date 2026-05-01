import { describe, it, expect } from 'vitest'
import { UNIT_OPTIONS, formatUnitLabel } from '../unitOfMeasure'

describe('unitOfMeasure', () => {
  describe('UNIT_OPTIONS', () => {
    it('exports an array of options', () => {
      expect(Array.isArray(UNIT_OPTIONS)).toBe(true)
      expect(UNIT_OPTIONS.length).toBeGreaterThan(0)
    })

    it('each option has value and label', () => {
      for (const opt of UNIT_OPTIONS) {
        expect(opt).toHaveProperty('value')
        expect(opt).toHaveProperty('label')
      }
    })
  })

  describe('formatUnitLabel', () => {
    it('returns label for known id', () => {
      expect(formatUnitLabel(1)).toBe('Stück')
      expect(formatUnitLabel(2)).toBe('Stunde')
      expect(formatUnitLabel(6)).toBe('Monat')
    })

    it('returns string id for unknown id', () => {
      expect(formatUnitLabel(99)).toBe('99')
    })

    it('returns "-" for null', () => {
      expect(formatUnitLabel(null)).toBe('-')
    })

    it('returns "-" for undefined', () => {
      expect(formatUnitLabel(undefined)).toBe('-')
    })

    it('returns "-" for empty string', () => {
      expect(formatUnitLabel('')).toBe('-')
    })
  })
})
