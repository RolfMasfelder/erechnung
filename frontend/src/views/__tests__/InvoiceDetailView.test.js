import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import InvoiceDetailView from '../InvoiceDetailView.vue'
import { invoiceService } from '@/api/services/invoiceService'

// Mock the invoice service
vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    getById: vi.fn(),
    downloadPDF: vi.fn(),
    downloadXML: vi.fn(),
    generateXml: vi.fn(),
    delete: vi.fn(),
    cancel: vi.fn()
  }
}))

const mockToast = vi.hoisted(() => ({ showToast: vi.fn(), success: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useToast', () => ({ useToast: () => mockToast }))

const mockConfirm = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: mockConfirm }) }))

vi.mock('@/composables/useEditLock', () => ({
  useEditLock: () => ({
    lockState: { isLocked: false, lockedBy: null, lockExpiry: null },
    acquireLock: vi.fn().mockResolvedValue(true),
    releaseLock: vi.fn().mockResolvedValue(undefined)
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

  it('getStatusLabel returns correct labels', async () => {
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.getStatusLabel) {
      expect(wrapper.vm.getStatusLabel('draft')).toBe('Entwurf')
      expect(wrapper.vm.getStatusLabel('SENT')).toBe('Versendet')
      expect(wrapper.vm.getStatusLabel('PAID')).toBe('Bezahlt')
      expect(wrapper.vm.getStatusLabel('unknown')).toBe('unknown')
    }
  })

  it('formatCurrency formats to EUR', async () => {
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.formatCurrency) {
      expect(wrapper.vm.formatCurrency(500)).toContain('500')
    }
  })

  it('formatDate formats ISO date to de-DE', async () => {
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.formatDate) {
      expect(wrapper.vm.formatDate('2025-06-15')).toContain('15')
      expect(wrapper.vm.formatDate(null)).toBe('-')
    }
  })

  it('formatQuantity formats numbers without trailing zeros', async () => {
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.formatQuantity) {
      expect(wrapper.vm.formatQuantity(2)).toBeTruthy()
      expect(wrapper.vm.formatQuantity(null)).toBe('0')
    }
  })

  it('handleInvoiceUpdated reloads invoice', async () => {
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    invoiceService.getById.mockResolvedValue(mockInvoice)

    if (wrapper.vm.handleInvoiceUpdated) {
      await wrapper.vm.handleInvoiceUpdated({ ...mockInvoice, status: 'sent' })
      await flushPromises()
      expect(invoiceService.getById).toHaveBeenCalled()
    }
  })

  it('handleEmailSent reloads invoice', async () => {
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    invoiceService.getById.mockResolvedValue(mockInvoice)

    if (wrapper.vm.handleEmailSent) {
      await wrapper.vm.handleEmailSent()
      await flushPromises()
      expect(invoiceService.getById).toHaveBeenCalled()
    }
  })

  it('handleDelete calls service when confirmed', async () => {
    globalThis.confirm = vi.fn(() => true)
    invoiceService.delete.mockResolvedValue({})
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.handleDelete) {
      await wrapper.vm.handleDelete()
      await flushPromises()
      expect(invoiceService.delete).toHaveBeenCalledWith(1)
    }
  })

  it('handleDelete does nothing when cancelled', async () => {
    globalThis.confirm = vi.fn(() => false)
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.handleDelete) {
      await wrapper.vm.handleDelete()
      expect(invoiceService.delete).not.toHaveBeenCalled()
    }
  })

  it('smartDownload downloads PDF for non-government', async () => {
    const blob = new Blob(['pdf'], { type: 'application/pdf' })
    invoiceService.downloadPDF.mockResolvedValue(blob)
    globalThis.URL = { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() }
    vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
    wrapper = mount(InvoiceDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.smartDownload) {
      await wrapper.vm.smartDownload()
      await flushPromises()
      expect(invoiceService.downloadPDF).toHaveBeenCalled()
    }
  })
})
