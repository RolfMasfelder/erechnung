import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import BusinessPartnerDetailView from '../BusinessPartnerDetailView.vue'
import { businessPartnerService } from '@/api/services/businessPartnerService'
import { invoiceService } from '@/api/services/invoiceService'

vi.mock('@/api/services/businessPartnerService', () => ({
  businessPartnerService: {
    getById: vi.fn(),
    delete: vi.fn()
  }
}))

vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    getAll: vi.fn()
  }
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

describe('BusinessPartnerDetailView', () => {
  let wrapper
  let router

  const mockCustomer = {
    id: 1,
    name: 'Test Customer GmbH',
    street: 'Test Str. 1',
    postal_code: '12345',
    city: 'Berlin',
    country: 'DE',
    email: 'test@customer.de',
    phone: '+49 123 456789',
    tax_number: '12/345/67890',
    vat_id: 'DE123456789',
    notes: 'Test notes'
  }

  const mockInvoices = {
    count: 1,
    results: [
      {
        id: 1,
        invoice_number: 'INV-001',
        invoice_date: '2025-01-15',
        total_gross: 119.00,
        status: 'PAID'
      }
    ]
  }

  beforeEach(async () => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/business-partners', name: 'BusinessPartnerList', component: { template: '<div>List</div>' } },
        { path: '/business-partners/:id', name: 'BusinessPartnerDetail', component: BusinessPartnerDetailView },
        { path: '/invoices/:id', name: 'InvoiceDetail', component: { template: '<div>Invoice</div>' } }
      ]
    })

    await router.push('/business-partners/1')
    await router.isReady()

    vi.clearAllMocks()
    businessPartnerService.getById.mockResolvedValue(mockCustomer)
    invoiceService.getAll.mockResolvedValue(mockInvoices)
  })

  it('renders customer detail view', async () => {
    wrapper = mount(BusinessPartnerDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.text()).toContain('Test Customer GmbH')
  })

  it('loads customer data on mount', async () => {
    wrapper = mount(BusinessPartnerDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(businessPartnerService.getById).toHaveBeenCalledWith('1')
  })

  it('displays customer contact information', async () => {
    wrapper = mount(BusinessPartnerDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    // Wait for data to load
    await new Promise(resolve => setTimeout(resolve, 200))
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('Test Str. 1')
    expect(text).toContain('12345')
    expect(text).toContain('Berlin')
    expect(text).toContain('test@customer.de')
  })

  it('displays invoice history', async () => {
    wrapper = mount(BusinessPartnerDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 300))
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('INV-001')
    expect(text).toContain('Bezahlt')

    const statusBadge = wrapper.find('.status-badge')
    expect(statusBadge.exists()).toBe(true)
    expect(statusBadge.classes()).toContain('status-paid')
  })

  it('shows edit button', async () => {
    wrapper = mount(BusinessPartnerDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const buttons = wrapper.findAll('button')
    const editButton = buttons.find(button => button.text().includes('Bearbeiten'))
    expect(editButton).toBeDefined()
  })
})
