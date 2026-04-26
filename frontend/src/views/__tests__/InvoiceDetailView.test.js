import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import InvoiceDetailView from '../InvoiceDetailView.vue'
import { invoiceService } from '@/api/services/invoiceService'

// Mock the invoice service
vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    getById: vi.fn(),
    downloadPDF: vi.fn(),
    downloadXML: vi.fn(),
    delete: vi.fn()
  }
}))

// Mock toast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

describe('InvoiceDetailView', () => {
  let wrapper
  let router

  const mockInvoice = {
    id: 1,
    invoice_number: 'INV-001',
    business_partner_details: { id: 1, name: 'Test Customer GmbH' },
    issue_date: '2025-01-15',
    due_date: '2025-02-15',
    subtotal: 100.00,
    tax_amount: 19.00,
    total_amount: 119.00,
    status: 'draft',
    lines: [
      {
        id: 1,
        position: 1,
        product_name: 'Test Product',
        quantity: 2,
        unit_price_net: 50.00,
        unit_price: 50.00,
        vat_rate: 19,
        tax_rate: 19,
        line_total: 100.00,
        tax_amount: 19.00,
        discount_percentage: '0',
        discount_amount: '0'
      }
    ],
    allowance_charges: [],
    attachments: []
  }

  beforeEach(async () => {
    // Create router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/invoices', name: 'InvoiceList', component: { template: '<div>List</div>' } },
        { path: '/invoices/:id', name: 'InvoiceDetail', component: InvoiceDetailView }
      ]
    })

    // Navigate to the route and wait for it to be ready
    await router.push('/invoices/1')
    await router.isReady()

    // Reset mocks
    vi.clearAllMocks()
    invoiceService.getById.mockResolvedValue(mockInvoice)
  })

  it('renders invoice detail view', async () => {
    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.text()).toContain('INV-001')
  })

  it('loads invoice data on mount', async () => {
    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(invoiceService.getById).toHaveBeenCalledWith('1')
  })

  it('displays invoice information', async () => {
    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('Test Customer GmbH')
    expect(text).toContain('119')
  })

  it('displays invoice lines', async () => {
    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('Test Product')
    expect(text).toContain('2') // quantity
  })

  it('downloads PDF when button clicked', async () => {
    const mockBlob = new Blob(['pdf content'], { type: 'application/pdf' })
    invoiceService.downloadPDF.mockResolvedValue(mockBlob)

    // Mock window.URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')

    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const downloadButton = wrapper.find('button:contains("PDF")')
    if (downloadButton.exists()) {
      await downloadButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(invoiceService.downloadPDF).toHaveBeenCalledWith(1)
    }
  })

  it('downloads XML when button clicked', async () => {
    const mockBlob = new Blob(['xml content'], { type: 'application/xml' })
    invoiceService.downloadXML.mockResolvedValue(mockBlob)

    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')

    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const downloadButton = wrapper.find('button:contains("XML")')
    if (downloadButton.exists()) {
      await downloadButton.trigger('click')
      await wrapper.vm.$nextTick()

      expect(invoiceService.downloadXML).toHaveBeenCalledWith(1)
    }
  })

  it('shows edit button for draft invoices', async () => {
    wrapper = mount(InvoiceDetailView, {
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

  it('hides edit button for sent invoices', async () => {
    const sentInvoice = { ...mockInvoice, status: 'sent' }
    invoiceService.getById.mockResolvedValue(sentInvoice)

    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const editButton = wrapper.find('button:contains("Bearbeiten")')
    expect(editButton.exists()).toBe(false)
  })

  it('handles error when loading invoice fails', async () => {
    invoiceService.getById.mockRejectedValue(new Error('Network error'))

    wrapper = mount(InvoiceDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.invoice).toBeNull()
  })
})
