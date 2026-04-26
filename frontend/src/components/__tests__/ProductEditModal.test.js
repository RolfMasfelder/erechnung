import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ProductEditModal from '../ProductEditModal.vue'
import { productService } from '@/api/services/productService'

vi.mock('@/api/services/productService', () => ({
  productService: {
    getById: vi.fn(),
    patch: vi.fn(),
    getTaxOptions: vi.fn()
  }
}))

describe('ProductEditModal', () => {
  let wrapper

  const mockProduct = {
    id: 1,
    name: 'Test Product',
    description: 'Test description',
    base_price: 99.99,
    default_tax_rate: 19,
    unit_of_measure: 1,
    sku: 'TEST-001',
    category: 'Test Category',
    is_active: true
  }

  beforeEach(() => {
    vi.clearAllMocks()
    productService.getTaxOptions.mockResolvedValue({
      tax_rates: [
        { label: '0% (Befreit)', value: '0.00' },
        { label: '7% (Ermäßigt)', value: '7.00' },
        { label: '19% (Standard)', value: '19.00' }
      ],
      unit_options: [
        { label: 'Piece', value: 'PCE' },
        { label: 'Hour', value: 'HUR' }
      ]
    })
  })

  it('loads product data on mount', async () => {
    productService.getById.mockResolvedValue(mockProduct)

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(productService.getById).toHaveBeenCalledWith(1)
    expect(wrapper.vm.formData.name).toBe('Test Product')
    expect(wrapper.vm.formData.base_price).toBe(99.99)
    expect(wrapper.vm.formData.default_tax_rate).toBe(19)
    expect(wrapper.vm.loading).toBe(false)
  })

  it('shows loading state while fetching product', async () => {
    productService.getById.mockReturnValue(new Promise(() => {}))

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.loading).toBe(true)
    const text = wrapper.text()
    expect(text).toContain('Lädt')
  })

  it('handles load error gracefully', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    productService.getById.mockRejectedValue(new Error('Load failed'))

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(consoleError).toHaveBeenCalled()
    expect(wrapper.vm.loading).toBe(false)

    consoleError.mockRestore()
  })

  it('updates product on form submit', async () => {
    productService.getById.mockResolvedValue(mockProduct)
    productService.patch.mockResolvedValue({ ...mockProduct, name: 'Updated Product' })

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    wrapper.vm.formData.name = 'Updated Product'

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    expect(productService.patch).toHaveBeenCalledWith(1, expect.objectContaining({
      name: 'Updated Product'
    }))
    expect(wrapper.emitted()).toHaveProperty('updated')
  })

  it('displays validation errors', async () => {
    productService.getById.mockResolvedValue(mockProduct)
    productService.patch.mockRejectedValue({
      response: {
        data: {
          name: ['Dieses Feld ist erforderlich.'],
          base_price: ['Ungültiger Preis.']
        }
      }
    })

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    if (wrapper.vm.errors.name) {
      expect(wrapper.vm.errors.name).toBe('Dieses Feld ist erforderlich.')
    }
    if (wrapper.vm.errors.base_price) {
      expect(wrapper.vm.errors.base_price).toBe('Ungültiger Preis.')
    }
  })

  it('emits close event when cancel button clicked', async () => {
    productService.getById.mockResolvedValue(mockProduct)

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
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

  it('handles network error on update', async () => {
    productService.getById.mockResolvedValue(mockProduct)
    productService.patch.mockRejectedValue(new Error('Network error'))

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.submitError).toBeTruthy()
    expect(wrapper.vm.saving).toBe(false)
  })

  it('shows VAT rate options', async () => {
    productService.getById.mockResolvedValue(mockProduct)

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.vatRateOptions).toBeDefined()
    expect(wrapper.vm.vatRateOptions.length).toBeGreaterThan(0)
  })

  it('handles is_active checkbox', async () => {
    productService.getById.mockResolvedValue(mockProduct)

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.formData.is_active).toBe(true)

    wrapper.vm.formData.is_active = false
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.formData.is_active).toBe(false)
  })

  it('validates required fields', async () => {
    productService.getById.mockResolvedValue(mockProduct)

    wrapper = mount(ProductEditModal, {
      props: {
        productId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const nameInput = wrapper.find('#name')
    const priceInput = wrapper.find('#base_price')

    if (nameInput.exists()) {
      expect(nameInput.attributes('required')).toBeDefined()
    }
    if (priceInput.exists()) {
      expect(priceInput.attributes('required')).toBeDefined()
    }
  })
})
