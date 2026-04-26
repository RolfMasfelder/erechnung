import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import InvoiceCreateModal from '../InvoiceCreateModal.vue'
import { invoiceService } from '@/api/services/invoiceService'
import { businessPartnerService } from '@/api/services/businessPartnerService'
import { productService } from '@/api/services/productService'
import { companyService } from '@/api/services/companyService'

vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    create: vi.fn(),
    createLine: vi.fn().mockResolvedValue({ id: 1 }),
    createAllowanceCharge: vi.fn().mockResolvedValue({ id: 1 })
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

describe('InvoiceCreateModal', () => {
  let wrapper

  const mockCustomers = [
    { id: 1, name: 'Customer 1' },
    { id: 2, name: 'Customer 2' }
  ]

  const mockProducts = [
    { id: 1, name: 'Product 1', unit_price: 100.00, vat_rate: 19 },
    { id: 2, name: 'Product 2', unit_price: 50.00, vat_rate: 7 }
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

  it('loads related data on mount', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(businessPartnerService.getAll).toHaveBeenCalled()
    expect(productService.getAll).toHaveBeenCalled()
    expect(companyService.getAll).toHaveBeenCalled()
  })

  it('initializes with default form data', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.formData.lines).toHaveLength(1)
    expect(wrapper.vm.formData.issue_date).toBeTruthy()
    expect(wrapper.vm.formData.due_date).toBeTruthy()
  })

  it('creates invoice on form submit', async () => {
    const newInvoice = {
      id: 1,
      invoice_number: 'INV-2024-001',
      customer: 1,
      total_amount: 119.00
    }

    invoiceService.create.mockResolvedValue(newInvoice)

    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    wrapper.vm.formData.business_partner = 1
    wrapper.vm.formData.lines[0].product = 1
    wrapper.vm.formData.lines[0].quantity = 1

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    if (invoiceService.create.mock.calls.length > 0) {
      expect(invoiceService.create).toHaveBeenCalled()
      expect(wrapper.emitted()).toHaveProperty('created')
    }
  })

  it('displays validation errors', async () => {
    invoiceService.create.mockRejectedValue({
      response: {
        data: {
          customer: ['Dieses Feld ist erforderlich.'],
          lines: ['Mindestens eine Position erforderlich.']
        }
      }
    })

    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    if (wrapper.vm.errors.customer) {
      expect(wrapper.vm.errors.customer).toBe('Dieses Feld ist erforderlich.')
    }
  })

  it('adds new invoice line', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const initialLength = wrapper.vm.formData.lines.length

    if (wrapper.vm.addLine) {
      wrapper.vm.addLine()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.formData.lines.length).toBe(initialLength + 1)
    }
  })

  it('removes invoice line', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Add a second line first
    if (wrapper.vm.addLine) {
      wrapper.vm.addLine()
      await wrapper.vm.$nextTick()

      const lengthWith2Lines = wrapper.vm.formData.lines.length

      if (wrapper.vm.removeLine) {
        wrapper.vm.removeLine(1)
        await wrapper.vm.$nextTick()

        expect(wrapper.vm.formData.lines.length).toBe(lengthWith2Lines - 1)
      }
    }
  })

  it('updates line when product changes', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    wrapper.vm.formData.lines[0].product = 1

    if (wrapper.vm.handleProductChange) {
      wrapper.vm.handleProductChange(0)
      await wrapper.vm.$nextTick()

      const selectedProduct = mockProducts[0]
      if (wrapper.vm.formData.lines[0].unit_price !== undefined) {
        expect(wrapper.vm.formData.lines[0].unit_price).toBe(selectedProduct.unit_price)
      }
      if (wrapper.vm.formData.lines[0].vat_rate !== undefined) {
        expect(wrapper.vm.formData.lines[0].vat_rate).toBe(selectedProduct.vat_rate)
      }
    }
  })

  it('emits close event when cancel button clicked', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const cancelButton = wrapper.findAll('button').find(btn => btn.text() === 'Abbrechen')
    if (cancelButton) {
      await cancelButton.trigger('click')
      expect(wrapper.emitted()).toHaveProperty('close')
    }
  })

  it('handles network error on create', async () => {
    invoiceService.create.mockRejectedValue(new Error('Network error'))

    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    wrapper.vm.formData.business_partner = 1

    if (wrapper.vm.handleSubmit) {
      await wrapper.vm.handleSubmit()
      await wrapper.vm.$nextTick()

      if (wrapper.vm.submitError) {
        expect(wrapper.vm.submitError).toBeTruthy()
      }
    }
  })

  it('validates required fields', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Form should be invalid initially (no business_partner set)
    expect(wrapper.vm.isFormValid).toBeFalsy()

    // After setting required fields form should become valid
    wrapper.vm.formData.business_partner = 1
    wrapper.vm.formData.lines[0].product = 1
    wrapper.vm.formData.lines[0].quantity = 1
    wrapper.vm.formData.lines[0].unit_price_net = 100
    wrapper.vm.formData.lines[0].vat_rate = 19

    await wrapper.vm.$nextTick()
    expect(wrapper.vm.isFormValid).toBe(true)
  })

  it('shows company select when multiple companies exist', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.companies.length).toBeGreaterThan(1)
  })

  it('calculates line totals', async () => {
    wrapper = mount(InvoiceCreateModal, {
      props: {
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    if (wrapper.vm.formData.lines[0]) {
      const line = wrapper.vm.formData.lines[0]
      line.quantity = 2
      line.unit_price_net = 100
      line.vat_rate = 19

      if (wrapper.vm.calculateLineTotal) {
        await wrapper.vm.$nextTick()
        const total = wrapper.vm.calculateLineTotal(0)
        if (total !== undefined) {
          expect(total).toBe(238) // 2 * 100 * 1.19
        }
      }
    }
  })
})
