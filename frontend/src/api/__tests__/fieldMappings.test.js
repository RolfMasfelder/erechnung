import { describe, it, expect } from 'vitest'
import {
  createFieldMapper,
  invoiceFields,
  invoiceLineFields,
  allowanceChargeFields,
  businessPartnerFields,
  companyFields,
  productFields,
  attachmentFields,
} from '@/api/fieldMappings'

describe('createFieldMapper', () => {
  const mapper = createFieldMapper({
    UI_TO_API: {
      uiName: 'api_name',
      same: 'same',
    },
    UI_ONLY: new Set(['localOnly']),
  })

  describe('toApi', () => {
    it('renames mapped fields', () => {
      const result = mapper.toApi({ uiName: 'hello', same: 42 })
      expect(result).toEqual({ api_name: 'hello', same: 42 })
    })

    it('strips UI_ONLY fields', () => {
      const result = mapper.toApi({ uiName: 'x', localOnly: 'drop me' })
      expect(result.localOnly).toBeUndefined()
      expect(result.api_name).toBe('x')
    })

    it('drops unknown fields not in UI_TO_API', () => {
      const result = mapper.toApi({ uiName: 'x', rogue: 'nope' })
      expect(result.rogue).toBeUndefined()
    })
  })

  describe('fromApi', () => {
    it('renames API fields back to UI names', () => {
      const result = mapper.fromApi({ api_name: 'world', same: 7 })
      expect(result).toEqual({ uiName: 'world', same: 7 })
    })

    it('passes through read-only fields not in mapping', () => {
      const result = mapper.fromApi({ api_name: 'x', id: 1, created_at: '2026-01-01' })
      expect(result.id).toBe(1)
      expect(result.created_at).toBe('2026-01-01')
      expect(result.uiName).toBe('x')
    })
  })

  describe('roundtrip', () => {
    it('survives toApi → fromApi for mapped fields', () => {
      const original = { uiName: 'test', same: 99 }
      const roundtripped = mapper.fromApi(mapper.toApi(original))
      expect(roundtripped.uiName).toBe('test')
      expect(roundtripped.same).toBe(99)
    })
  })
})

describe('invoiceLineFields', () => {
  it('maps unit_price_net → unit_price', () => {
    const api = invoiceLineFields.toApi({ unit_price_net: 100, vat_rate: 19, quantity: 2 })
    expect(api.unit_price).toBe(100)
    expect(api.tax_rate).toBe(19)
    expect(api.quantity).toBe(2)
    // UI names must not leak
    expect(api.unit_price_net).toBeUndefined()
    expect(api.vat_rate).toBeUndefined()
  })

  it('maps unit_price → unit_price_net on response', () => {
    const ui = invoiceLineFields.fromApi({ unit_price: 50, tax_rate: 7, id: 3 })
    expect(ui.unit_price_net).toBe(50)
    expect(ui.vat_rate).toBe(7)
    expect(ui.id).toBe(3)
  })

  it('roundtrips correctly', () => {
    const original = { unit_price_net: 42.5, vat_rate: 19, quantity: 1, invoice: 10 }
    const rt = invoiceLineFields.fromApi(invoiceLineFields.toApi(original))
    expect(rt.unit_price_net).toBe(42.5)
    expect(rt.vat_rate).toBe(19)
    expect(rt.quantity).toBe(1)
  })
})

describe('businessPartnerFields', () => {
  it('maps name → company_name, street → address_line1, tax_number → tax_id', () => {
    const api = businessPartnerFields.toApi({
      name: 'ACME',
      street: 'Hauptstr. 1',
      tax_number: '123',
      city: 'Berlin',
    })
    expect(api.company_name).toBe('ACME')
    expect(api.address_line1).toBe('Hauptstr. 1')
    expect(api.tax_id).toBe('123')
    expect(api.city).toBe('Berlin')
    // UI names stripped
    expect(api.name).toBeUndefined()
    expect(api.street).toBeUndefined()
    expect(api.tax_number).toBeUndefined()
  })

  it('strips UI-only "notes" field', () => {
    const api = businessPartnerFields.toApi({ name: 'X', notes: 'private' })
    expect(api.notes).toBeUndefined()
  })

  it('maps back from API', () => {
    const ui = businessPartnerFields.fromApi({
      id: 1,
      company_name: 'ACME',
      address_line1: 'Hauptstr. 1',
      tax_id: '123',
    })
    expect(ui.name).toBe('ACME')
    expect(ui.street).toBe('Hauptstr. 1')
    expect(ui.tax_number).toBe('123')
    expect(ui.id).toBe(1)
  })
})

describe('companyFields', () => {
  it('passes through all 1:1 fields', () => {
    const data = { name: 'ACME', address_line1: 'Test', city: 'Berlin', tax_id: '42' }
    const api = companyFields.toApi(data)
    expect(api).toEqual(data)
  })

  it('roundtrips correctly', () => {
    const data = { name: 'X', iban: 'DE89', bic: 'COBADEFFXXX' }
    const rt = companyFields.fromApi(companyFields.toApi(data))
    expect(rt.name).toBe('X')
    expect(rt.iban).toBe('DE89')
  })
})

describe('productFields', () => {
  it('passes through all 1:1 fields', () => {
    const data = { name: 'Widget', base_price: '10.00', default_tax_rate: '19.00' }
    const api = productFields.toApi(data)
    expect(api).toEqual(data)
  })
})

describe('invoiceFields', () => {
  it('maps all header fields 1:1', () => {
    const data = { company: 1, issue_date: '2026-03-10', notes: 'test' }
    const api = invoiceFields.toApi(data)
    expect(api.company).toBe(1)
    expect(api.issue_date).toBe('2026-03-10')
    expect(api.notes).toBe('test')
  })
})

describe('allowanceChargeFields', () => {
  it('maps all fields 1:1', () => {
    const data = { invoice: 1, is_charge: false, actual_amount: 10, reason: 'Rabatt' }
    const api = allowanceChargeFields.toApi(data)
    expect(api).toEqual(data)
  })
})

describe('attachmentFields', () => {
  it('maps all fields 1:1', () => {
    const data = { invoice: 1, description: 'Lieferschein', attachment_type: 'delivery_note' }
    const api = attachmentFields.toApi(data)
    expect(api).toEqual(data)
  })
})
