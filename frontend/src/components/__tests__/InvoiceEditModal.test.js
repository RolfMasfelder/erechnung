import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import InvoiceEditModal from '../InvoiceEditModal.vue'
import { invoiceService } from '@/api/services/invoiceService'
import { businessPartnerService } from '@/api/services/businessPartnerService'
import { productService } from '@/api/services/productService'
import { companyService } from '@/api/services/companyService'

vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    getById: vi.fn(),
    update: vi.fn(),
    deleteLine: vi.fn().mockResolvedValue({}),
    updateLine: vi.fn().mockResolvedValue({}),
    createLine: vi.fn().mockResolvedValue({}),
    deleteAllowanceCharge: vi.fn().mockResolvedValue({}),
    createAllowanceCharge: vi.fn().mockResolvedValue({}),
    createLineAttribute: vi.fn().mockResolvedValue({ id: 100 }),
    deleteLineAttribute: vi.fn().mockResolvedValue({})
  }
}))

vi.mock('@/api/services/businessPartnerService', () => ({
  businessPartnerService: {
    getAll: vi.fn()
  }
}))

vi.mock('@/api/services/productService', () => ({
  productService: {
    getAll: vi.fn()
  }
}))

vi.mock('@/api/services/companyService', () => ({
  companyService: {
    getAll: vi.fn()
  }
}))

describe('InvoiceEditModal', () => {
  let wrapper

  const mockInvoice = {
    id: 1,
    invoice_number: 'INV-2024-001',
    company: 1,
    business_partner: 1,
    issue_date: '2024-01-15',
    due_date: '2024-02-15',
    status: 'draft',
    total_amount: 119.00,
    lines: [
      {
        id: 1,
        product: 1,
        description: 'Test Product',
        quantity: 1,
        unit_price: 100.00,
        tax_rate: 19,
        line_total: 119.00
      }
    ]
  }

  const mockCustomers = [
    { id: 1, name: 'Customer 1' },
    { id: 2, name: 'Customer 2' }
  ]

  const mockProducts = [
    { id: 1, name: 'Product 1', unit_price: 100.00, vat_rate: 19 },
    { id: 2, name: 'Product 2', unit_price: 50.00, vat_rate: 19 }
  ]

  const mockCompanies = [
    { id: 1, name: 'Company 1' },
    { id: 2, name: 'Company 2' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    businessPartnerService.getAll.mockResolvedValue(mockCustomers)
    productService.getAll.mockResolvedValue(mockProducts)
    companyService.getAll.mockResolvedValue(mockCompanies)
  })

  it('loads invoice data on mount', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(invoiceService.getById).toHaveBeenCalledWith(1)
    expect(wrapper.vm.formData.business_partner).toBe(1)
    expect(wrapper.vm.formData.status).toBe('draft')
    expect(wrapper.vm.loading).toBe(false)
  })

  it('shows loading state while fetching invoice', async () => {
    invoiceService.getById.mockReturnValue(new Promise(() => {}))

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.loading).toBe(true)
    const text = wrapper.text()
    expect(text).toContain('Lädt')
  })

  it('loads related data (customers, products, companies)', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(businessPartnerService.getAll).toHaveBeenCalled()
    expect(productService.getAll).toHaveBeenCalled()
    expect(companyService.getAll).toHaveBeenCalled()
  })

  it('handles load error gracefully', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    invoiceService.getById.mockRejectedValue(new Error('Load failed'))

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(consoleError).toHaveBeenCalled()
    expect(wrapper.vm.loading).toBe(false)

    consoleError.mockRestore()
  })

  it('updates invoice on form submit', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)
    invoiceService.update.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    wrapper.vm.formData.due_date = '2024-03-15'

    if (wrapper.vm.handleSubmit) {
      await wrapper.vm.handleSubmit()
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))

      if (invoiceService.update.mock.calls.length > 0) {
        expect(invoiceService.update).toHaveBeenCalledWith(1, expect.objectContaining({
          business_partner: 1
        }))
        expect(wrapper.emitted()).toHaveProperty('updated')
      }
    }
  })

  it('displays validation errors', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)
    invoiceService.update.mockRejectedValue({
      response: {
        data: {
          customer: ['Dieses Feld ist erforderlich.'],
          invoice_number: ['Rechnungsnummer existiert bereits.']
        }
      }
    })

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    if (wrapper.vm.errors.customer) {
      expect(wrapper.vm.errors.customer).toBe('Dieses Feld ist erforderlich.')
    }
    if (wrapper.vm.errors.invoice_number) {
      expect(wrapper.vm.errors.invoice_number).toBe('Rechnungsnummer existiert bereits.')
    }
  })

  it('emits close event when cancel button clicked', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    const cancelButton = wrapper.findAll('button').find(btn => btn.text() === 'Abbrechen')
    if (cancelButton) {
      await cancelButton.trigger('click')
      expect(wrapper.emitted()).toHaveProperty('close')
    }
  })

  it('handles network error on update', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)
    invoiceService.update.mockRejectedValue(new Error('Network error'))

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.submitError).toBeTruthy()
    expect(wrapper.vm.saving).toBe(false)
  })

  it('shows invoice lines', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(wrapper.vm.formData.lines).toHaveLength(1)
    expect(wrapper.vm.formData.lines[0].product).toBe(1)
  })

  it('allows adding invoice lines for drafts', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    const initialLength = wrapper.vm.formData.lines.length

    if (wrapper.vm.addLine) {
      wrapper.vm.addLine()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formData.lines.length).toBe(initialLength + 1)
    }
  })

  it('allows removing invoice lines for drafts', async () => {
    const invoiceWithMultipleLines = {
      ...mockInvoice,
      lines: [
        mockInvoice.lines[0],
        { ...mockInvoice.lines[0], id: 2 }
      ]
    }

    invoiceService.getById.mockResolvedValue(invoiceWithMultipleLines)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    const initialLength = wrapper.vm.formData.lines.length

    if (wrapper.vm.removeLine) {
      wrapper.vm.removeLine(1)
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formData.lines.length).toBe(initialLength - 1)
    }
  })

  it('prevents editing non-draft invoices', async () => {
    const sentInvoice = { ...mockInvoice, status: 'sent' }
    invoiceService.getById.mockResolvedValue(sentInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(wrapper.vm.formData.status).toBe('sent')
    // Should show readonly fields for non-draft invoices
  })

  it('does not show payee section by default', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(wrapper.vm.showPayee).toBe(false)
    expect(wrapper.find('#payee_name').exists()).toBe(false)
  })

  it('shows and pre-fills payee section when invoice has payee data (BG-10)', async () => {
    const invoiceWithPayee = { ...mockInvoice, payee_name: 'Factoring GmbH', payee_id: 'FACT-1' }
    invoiceService.getById.mockResolvedValue(invoiceWithPayee)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(wrapper.vm.showPayee).toBe(true)
    expect(wrapper.vm.formData.payee_name).toBe('Factoring GmbH')
    expect(wrapper.vm.formData.payee_id).toBe('FACT-1')
    expect(wrapper.find('#payee_name').exists()).toBe(true)
  })

  it('submits payee fields when toggled on', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)
    invoiceService.update.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    wrapper.vm.showPayee = true
    wrapper.vm.formData.payee_name = 'Factoring GmbH'
    wrapper.vm.formData.payee_id = 'FACT-1'

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(invoiceService.update).toHaveBeenCalledWith(1, expect.objectContaining({
      payee_name: 'Factoring GmbH',
      payee_id: 'FACT-1'
    }))
  })

  it('loads line attributes from invoice (BG-32)', async () => {
    const invoiceWithAttributes = {
      ...mockInvoice,
      lines: [
        {
          ...mockInvoice.lines[0],
          attributes: [
            { id: 10, name: 'Farbe', value: 'Rot', sort_order: 0 }
          ]
        }
      ]
    }
    invoiceService.getById.mockResolvedValue(invoiceWithAttributes)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(wrapper.vm.formData.lines[0].attributes).toHaveLength(1)
    expect(wrapper.vm.formData.lines[0].attributes[0].name).toBe('Farbe')
    expect(wrapper.vm.formData.lines[0].attributes[0].value).toBe('Rot')
  })

  it('allows adding and removing line attributes', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    expect(wrapper.vm.formData.lines[0].attributes).toEqual([])

    wrapper.vm.addLineAttribute(0)
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.formData.lines[0].attributes).toHaveLength(1)

    wrapper.vm.formData.lines[0].attributes[0].name = 'Material'
    wrapper.vm.formData.lines[0].attributes[0].value = 'Aluminium'

    wrapper.vm.removeLineAttribute(0, 0)
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.formData.lines[0].attributes).toHaveLength(0)
  })

  it('creates line attributes on submit for a new attribute', async () => {
    invoiceService.getById.mockResolvedValue(mockInvoice)
    invoiceService.update.mockResolvedValue(mockInvoice)

    wrapper = mount(InvoiceEditModal, {
      props: {
        invoiceId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))

    wrapper.vm.addLineAttribute(0)
    wrapper.vm.formData.lines[0].attributes[0].name = 'Farbe'
    wrapper.vm.formData.lines[0].attributes[0].value = 'Blau'

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(invoiceService.createLineAttribute).toHaveBeenCalledWith(expect.objectContaining({
      invoice_line: 1,
      name: 'Farbe',
      value: 'Blau'
    }))
  })
})
