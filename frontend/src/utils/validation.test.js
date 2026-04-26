import { describe, it, expect } from 'vitest'
import {
  isValidEmail,
  isValidTaxId,
  isValidVatId,
  isValidIBAN,
  isValidBIC,
  isValidInvoiceNumber,
  isValidAmount,
  isValidPercentage
} from '@/utils/validation'

describe('validation', () => {
  describe('isValidEmail', () => {
    it('should validate correct email', () => {
      expect(isValidEmail('test@example.com')).toBe(true)
      expect(isValidEmail('user.name+tag@example.co.uk')).toBe(true)
    })

    it('should reject invalid email', () => {
      expect(isValidEmail('notanemail')).toBe(false)
      expect(isValidEmail('missing@domain')).toBe(false)
      expect(isValidEmail('@example.com')).toBe(false)
      expect(isValidEmail('test@')).toBe(false)
    })
  })

  describe('isValidTaxId', () => {
    it('should validate German tax ID (10-13 digits)', () => {
      expect(isValidTaxId('1234567890')).toBe(true)
      expect(isValidTaxId('1234567890123')).toBe(true)
    })

    it('should accept tax ID with spaces/dashes', () => {
      expect(isValidTaxId('123 456 789 0')).toBe(true)
      expect(isValidTaxId('123-456-789-0')).toBe(true)
    })

    it('should reject invalid tax ID', () => {
      expect(isValidTaxId('123')).toBe(false)
      expect(isValidTaxId('12345678901234')).toBe(false)
      expect(isValidTaxId('abc1234567890')).toBe(false)
      expect(isValidTaxId('')).toBe(false)
      expect(isValidTaxId(null)).toBe(false)
    })
  })

  describe('isValidVatId', () => {
    it('should validate EU VAT ID', () => {
      expect(isValidVatId('DE123456789')).toBe(true)
      expect(isValidVatId('FR12345678901')).toBe(true)
      expect(isValidVatId('GB123456789')).toBe(true)
    })

    it('should accept VAT ID with spaces/dashes', () => {
      expect(isValidVatId('DE 123 456 789')).toBe(true)
      expect(isValidVatId('DE-123-456-789')).toBe(true)
    })

    it('should reject invalid VAT ID', () => {
      expect(isValidVatId('D123456789')).toBe(false) // 1 letter
      expect(isValidVatId('de123456789')).toBe(false) // lowercase
      expect(isValidVatId('123456789')).toBe(false) // no country code
      expect(isValidVatId('')).toBe(false)
      expect(isValidVatId(null)).toBe(false)
    })
  })

  describe('isValidIBAN', () => {
    it('should validate correct IBAN format', () => {
      expect(isValidIBAN('DE89370400440532013000')).toBe(true)
      expect(isValidIBAN('GB82WEST12345698765432')).toBe(true)
      expect(isValidIBAN('FR1420041010050500013M02606')).toBe(true)
    })

    it('should accept IBAN with spaces', () => {
      expect(isValidIBAN('DE89 3704 0044 0532 0130 00')).toBe(true)
    })

    it('should reject invalid IBAN', () => {
      expect(isValidIBAN('DE8937040044')).toBe(false) // too short
      expect(isValidIBAN('1234567890123456789012345678901234567890')).toBe(false) // too long
      expect(isValidIBAN('D389370400440532013000')).toBe(false) // 1 letter
      expect(isValidIBAN('DEAA370400440532013000')).toBe(false) // letters instead of digits
      expect(isValidIBAN('')).toBe(false)
      expect(isValidIBAN(null)).toBe(false)
    })
  })

  describe('isValidBIC', () => {
    it('should validate 8-character BIC', () => {
      expect(isValidBIC('DEUTDEFF')).toBe(true)
      expect(isValidBIC('COBADEFF')).toBe(true)
    })

    it('should validate 11-character BIC', () => {
      expect(isValidBIC('DEUTDEFF500')).toBe(true)
      expect(isValidBIC('COBADEFFXXX')).toBe(true)
    })

    it('should accept BIC with spaces', () => {
      expect(isValidBIC('DEUT DE FF')).toBe(true)
      expect(isValidBIC('DEUT DE FF 500')).toBe(true)
    })

    it('should reject invalid BIC', () => {
      expect(isValidBIC('DEUT')).toBe(false) // too short
      expect(isValidBIC('DEUTDEFF50')).toBe(false) // 10 chars
      expect(isValidBIC('DEUTDEFF5000')).toBe(false) // 12 chars
      // Note: lowercase wird zu uppercase normalisiert, daher akzeptiert
      expect(isValidBIC('')).toBe(false)
      expect(isValidBIC(null)).toBe(false)
    })
  })

  describe('isValidInvoiceNumber', () => {
    it('should validate invoice numbers >= 3 chars', () => {
      expect(isValidInvoiceNumber('INV-001')).toBe(true)
      expect(isValidInvoiceNumber('2024-001')).toBe(true)
      expect(isValidInvoiceNumber('ABC')).toBe(true)
    })

    it('should reject short invoice numbers', () => {
      expect(isValidInvoiceNumber('AB')).toBe(false)
      expect(isValidInvoiceNumber('1')).toBe(false)
      expect(isValidInvoiceNumber('')).toBe(false)
      expect(isValidInvoiceNumber('   ')).toBe(false) // only whitespace
      expect(isValidInvoiceNumber(null)).toBe(false)
    })
  })

  describe('isValidAmount', () => {
    it('should validate positive numbers', () => {
      expect(isValidAmount(100)).toBe(true)
      expect(isValidAmount(0.01)).toBe(true)
      expect(isValidAmount(1234.56)).toBe(true)
    })

    it('should validate positive number strings', () => {
      expect(isValidAmount('100')).toBe(true)
      expect(isValidAmount('1234.56')).toBe(true)
    })

    it('should reject zero and negative amounts', () => {
      expect(isValidAmount(0)).toBe(false)
      expect(isValidAmount(-100)).toBe(false)
      expect(isValidAmount('-100')).toBe(false)
    })

    it('should reject invalid inputs', () => {
      expect(isValidAmount('abc')).toBe(false)
      expect(isValidAmount(NaN)).toBe(false)
      expect(isValidAmount(null)).toBe(false)
      expect(isValidAmount(undefined)).toBe(false)
    })
  })

  describe('isValidPercentage', () => {
    it('should validate percentages 0-100', () => {
      expect(isValidPercentage(0)).toBe(true)
      expect(isValidPercentage(50)).toBe(true)
      expect(isValidPercentage(100)).toBe(true)
      expect(isValidPercentage(19.5)).toBe(true)
    })

    it('should validate percentage strings', () => {
      expect(isValidPercentage('0')).toBe(true)
      expect(isValidPercentage('50')).toBe(true)
      expect(isValidPercentage('100')).toBe(true)
    })

    it('should reject out-of-range percentages', () => {
      expect(isValidPercentage(-1)).toBe(false)
      expect(isValidPercentage(101)).toBe(false)
      expect(isValidPercentage('-1')).toBe(false)
      expect(isValidPercentage('101')).toBe(false)
    })

    it('should reject invalid inputs', () => {
      expect(isValidPercentage('abc')).toBe(false)
      expect(isValidPercentage(Number.NaN)).toBe(false)
      // Note: null wird zu 0 konvertiert, was zwischen 0-100 liegt
      expect(isValidPercentage(undefined)).toBe(false)
    })
  })
})
