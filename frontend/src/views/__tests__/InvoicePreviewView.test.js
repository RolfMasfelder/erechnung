import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const mockInvoice = {
  id: 1,
  invoice_number: 'RE-2026-001',
  issue_date: '2026-01-09',
  due_date: '2026-02-09',
  status: 'draft',
  total_net: '100.00',
  total_tax: '19.00',
  total_gross: '119.00',
  notes: '',
  company_details: { name: 'My Company GmbH', logo: null },
  customer: { name: 'Customer A', street: 'Str. 1', city: 'Berlin', zip: '10115' },
  lines: [
    { id: 1, description: 'Service', quantity: '1', unit_price: '100.00', line_total: '100.00' }
  ]
}

vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    getById: vi.fn()
  }
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '1' } }),
  RouterLink: { template: '<a><slot /></a>' }
}))

import { invoiceService } from '@/api/services/invoiceService'
import InvoicePreviewView from '../InvoicePreviewView.vue'

describe('InvoicePreviewView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    invoiceService.getById.mockResolvedValue(mockInvoice)
  })

  it('renders preview banner', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.find('.preview-banner').exists()).toBe(true)
  })

  it('shows loading initially', () => {
    invoiceService.getById.mockReturnValue(new Promise(() => {}))
    const wrapper = mount(InvoicePreviewView)
    expect(wrapper.find('.preview-loading').exists()).toBe(true)
  })

  it('shows invoice content after load', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.find('.invoice-document').exists()).toBe(true)
  })

  it('shows error message on load failure', async () => {
    invoiceService.getById.mockRejectedValue(new Error('Not found'))
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.find('.preview-error').exists()).toBe(true)
  })

  it('computes company name from company_details', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.companyName).toBe('My Company GmbH')
  })

  it('computes empty company name when no invoice', async () => {
    invoiceService.getById.mockResolvedValue({ ...mockInvoice, company_details: null })
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.companyName).toBe('')
  })

  it('computes logo as null when not set', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.companyLogo).toBeNull()
  })

  it('computes logo when set', async () => {
    invoiceService.getById.mockResolvedValue({
      ...mockInvoice,
      company_details: { name: 'X', logo: 'http://example.com/logo.png' }
    })
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.companyLogo).toBe('http://example.com/logo.png')
  })

  it('formatDate returns empty string for null', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.formatDate(null)).toBe('')
  })

  it('formatDate returns empty string for undefined', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.formatDate(undefined)).toBe('')
  })

  it('formatDate formats valid date', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    const result = wrapper.vm.formatDate('2026-01-09')
    expect(typeof result).toBe('string')
    expect(result).toContain('09')
  })

  it('formatCurrency returns dash for null', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.formatCurrency(null)).toBe('–')
  })

  it('formatCurrency returns dash for undefined', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.formatCurrency(undefined)).toBe('–')
  })

  it('formatCurrency formats valid number', async () => {
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    const result = wrapper.vm.formatCurrency('100.00')
    expect(result).toContain('100')
  })

  it('uses generic error message when error has no message', async () => {
    invoiceService.getById.mockRejectedValue({})
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.vm.error).toBe('Unbekannter Fehler')
  })

  it('renders product_name when description is absent', async () => {
    invoiceService.getById.mockResolvedValue({
      ...mockInvoice,
      items: [
        { id: 2, description: '', product_name: 'Widget', quantity: '2', unit_price: '50.00', line_total: '100.00' }
      ]
    })
    const wrapper = mount(InvoicePreviewView)
    await flushPromises()
    expect(wrapper.html()).toContain('Widget')
  })
})
