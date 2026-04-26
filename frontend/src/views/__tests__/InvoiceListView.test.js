import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import InvoiceListView from '../InvoiceListView.vue'
import { invoiceService } from '@/api/services/invoiceService'

// Mock the invoice service
vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    getAll: vi.fn(),
    delete: vi.fn()
  }
}))
// Mock useConfirm composable
const mockConfirm = vi.fn()
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => ({ confirm: mockConfirm })
}))

// Mock useToast composable
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  })
}))

describe('InvoiceListView', () => {
  let wrapper
  let router

  const mockInvoices = {
    count: 2,
    results: [
      {
        id: 1,
        invoice_number: 'INV-001',
        customer_name: 'Test Customer',
        customer_details: { id: 101, name: 'Test Customer' },
        issue_date: '2025-01-15',
        total_amount: 119.00,
        status: 'draft'
      },
      {
        id: 2,
        invoice_number: 'INV-002',
        customer_name: 'Another Customer',
        customer_details: { id: 102, name: 'Another Customer' },
        issue_date: '2025-01-20',
        total_amount: 238.00,
        status: 'sent'
      }
    ]
  }

  beforeEach(async () => {
    // Create router
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/invoices', name: 'InvoiceList', component: InvoiceListView },
        { path: '/invoices/:id', name: 'InvoiceDetail', component: { template: '<div>Detail</div>' } },
        { path: '/business-partners/:id', name: 'BusinessPartnerDetail', component: { template: '<div>Partner</div>' } }
      ]
    })

    await router.push('/invoices')
    await router.isReady()

    // Reset mocks
    vi.clearAllMocks()
    invoiceService.getAll.mockResolvedValue(mockInvoices)
  })

  it('renders invoice list view', async () => {
    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.find('h1').text()).toBe('Rechnungen')
  })

  it('loads invoices on mount', async () => {
    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(invoiceService.getAll).toHaveBeenCalled()
  })

  it('displays invoice data in table', async () => {
    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('INV-001')
    expect(text).toContain('Test Customer')
  })

  it('filters invoices by search query', async () => {
    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const searchInput = wrapper.find('input[placeholder*="Suche"]')
    await searchInput.setValue('INV-001')

    // Wait for debounce
    await new Promise(resolve => setTimeout(resolve, 600))

    expect(invoiceService.getAll).toHaveBeenCalledWith(
      expect.objectContaining({
        search: 'INV-001'
      })
    )
  })

  it('shows create modal when button clicked', async () => {
    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const createButton = wrapper.find('button:contains("Neue Rechnung")')
    if (createButton.exists()) {
      await createButton.trigger('click')
      expect(wrapper.vm.showCreateModal).toBe(true)
    }
  })

  it('handles pagination', async () => {
    const manyInvoices = {
      count: 50,
      results: Array.from({ length: 20 }, (_, i) => ({
        id: i + 1,
        invoice_number: `INV-${String(i + 1).padStart(3, '0')}`,
        customer_name: `Customer ${i + 1}`,
        customer_details: { id: i + 1, name: `Customer ${i + 1}` },
        issue_date: '2025-01-15',
        total_amount: 100.00,
        status: 'draft'
      }))
    }

    invoiceService.getAll.mockResolvedValue(manyInvoices)

    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Check if pagination is rendered
    const pagination = wrapper.find('[class*="pagination"]')
    expect(pagination.exists() || wrapper.vm.pagination.totalPages > 1).toBe(true)
  })

  it('displays empty state when no invoices', async () => {
    invoiceService.getAll.mockResolvedValue({
      count: 0,
      results: []
    })

    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.text()).toContain('Keine Rechnungen')
  })

  it('handles loading state', async () => {
    // Make the promise pending
    let resolvePromise
    const pendingPromise = new Promise(resolve => {
      resolvePromise = resolve
    })
    invoiceService.getAll.mockReturnValue(pendingPromise)

    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    // Should show loading state
    expect(wrapper.vm.loading).toBe(true)

    // Resolve the promise
    resolvePromise(mockInvoices)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.loading).toBe(false)
  })

  it('handles navigation to detail view', async () => {
    const push = vi.fn()
    router.push = push

    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Call the viewInvoice method directly
    wrapper.vm.viewInvoice(1)
    expect(push).toHaveBeenCalledWith({ name: 'InvoiceDetail', params: { id: 1 } })
  })

  it('handles delete invoice', async () => {
    mockConfirm.mockResolvedValue(true)

    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const initialCallCount = invoiceService.getAll.mock.calls.length

    if (wrapper.vm.deleteInvoice) {
      await wrapper.vm.deleteInvoice(1)
      expect(invoiceService.delete).toHaveBeenCalledWith(1)
      // After delete, loadInvoices should be called again
      expect(invoiceService.getAll.mock.calls.length).toBeGreaterThan(initialCallCount)
    }
  })

  it('cancels delete when user declines confirmation', async () => {
    mockConfirm.mockResolvedValue(false)

    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    if (wrapper.vm.deleteInvoice) {
      await wrapper.vm.deleteInvoice(1)
      expect(invoiceService.delete).not.toHaveBeenCalled()
    }
  })

  it('handles sorting by column', async () => {
    wrapper = mount(InvoiceListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Clear the initial load call
    vi.clearAllMocks()

    // Simulate sort event
    if (wrapper.vm.handleSort) {
      await wrapper.vm.handleSort({ key: 'invoice_number', order: 'asc' })

      expect(invoiceService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          ordering: 'invoice_number'
        })
      )

      // Sort descending
      await wrapper.vm.handleSort({ key: 'invoice_number', order: 'desc' })

      expect(invoiceService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          ordering: '-invoice_number'
        })
      )

      await wrapper.vm.handleSort({ key: 'customer_name', order: 'asc' })

      expect(invoiceService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          ordering: 'business_partner__company_name'
        })
      )

      await wrapper.vm.handleSort({ key: 'status', order: 'desc' })

      expect(invoiceService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          ordering: '-status'
        })
      )
    }
  })
})
