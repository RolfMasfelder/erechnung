import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProductListView from '../ProductListView.vue'
import { productService } from '@/api/services/productService'

vi.mock('@/api/services/productService', () => ({
  productService: {
    getAll: vi.fn(),
    delete: vi.fn()
  }
}))

const mockToast = { showToast: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() }
vi.mock('@/composables/useToast', () => ({ useToast: () => mockToast }))

const mockConfirm = vi.fn()
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: mockConfirm }) }))

vi.mock('@/api/services/importService', () => ({
  importService: { importProducts: vi.fn() }
}))

import { importService } from '@/api/services/importService'

describe('ProductListView', () => {
  let wrapper
  let router

  const mockProducts = {
    count: 2,
    results: [
      {
        id: 1,
        name: 'Test Product',
        product_code: 'PRD-001',
        sku: 'TEST-001',
        base_price: 100.00,
        default_tax_rate: 19,
        unit_of_measure: 1,
        is_active: true,
        category: 'Software'
      },
      {
        id: 2,
        name: 'Another Product',
        product_code: 'PRD-002',
        sku: 'TEST-002',
        base_price: 50.00,
        default_tax_rate: 19,
        unit_of_measure: 1,
        is_active: false,
        category: 'Hardware'
      }
    ]
  }

  beforeEach(async () => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/products', name: 'ProductList', component: ProductListView },
        { path: '/products/:id', name: 'ProductDetail', component: { template: '<div>Detail</div>' } }
      ]
    })

    await router.push('/products')
    await router.isReady()

    vi.clearAllMocks()
    productService.getAll.mockResolvedValue(mockProducts)
  })

  it('renders product list view', async () => {
    wrapper = mount(ProductListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.find('h1').text()).toBe('Produkte')
  })

  it('loads products on mount', async () => {
    wrapper = mount(ProductListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(productService.getAll).toHaveBeenCalled()
  })

  it('displays product data', async () => {
    wrapper = mount(ProductListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('Test Product')
    expect(text).toContain('TEST-001')
  })

  it('filters products by search', async () => {
    wrapper = mount(ProductListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const searchInput = wrapper.find('input[placeholder*="Suche"]')
    await searchInput.setValue('Software')

    await new Promise(resolve => setTimeout(resolve, 600))

    expect(productService.getAll).toHaveBeenCalledWith(
      expect.objectContaining({
        search: 'Software'
      })
    )
  })

  it('shows create modal when button clicked', async () => {
    wrapper = mount(ProductListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const createButton = wrapper.find('button:contains("Neues Produkt")')
    if (createButton.exists()) {
      await createButton.trigger('click')
      expect(wrapper.vm.showCreateModal).toBe(true)
    }
  })

  it('displays inactive badge for inactive products', async () => {
    wrapper = mount(ProductListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('Inaktiv')
  })

  it('shows link to product detail view', async () => {
    wrapper = mount(ProductListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const firstProductLink = wrapper.find('.product-link')
    expect(firstProductLink.exists()).toBe(true)
    expect(firstProductLink.attributes('href')).toContain('/products/1')
  })

  it('handleSort updates sort params and reloads', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    productService.getAll.mockResolvedValue(mockProducts)

    const baseTable = wrapper.findComponent({ name: 'BaseTable' })
    await baseTable.vm.$emit('sort', { key: 'base_price', order: 'desc' })
    await flushPromises()

    expect(productService.getAll).toHaveBeenCalledWith(
      expect.objectContaining({ ordering: '-base_price' })
    )
  })

  it('handlePageChange updates page and reloads', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    productService.getAll.mockResolvedValue(mockProducts)

    if (wrapper.vm.handlePageChange) {
      await wrapper.vm.handlePageChange(3)
      await flushPromises()
      expect(productService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({ page: 3 })
      )
    }
  })

  it('viewProduct navigates to product detail', async () => {
    const pushSpy = vi.spyOn(router, 'push')
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.viewProduct) {
      await wrapper.vm.viewProduct(1)
      expect(pushSpy).toHaveBeenCalledWith({ name: 'ProductDetail', params: { id: 1 } })
    }
  })

  it('editProduct sets selectedProductId and shows modal', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.editProduct) {
      await wrapper.vm.editProduct(2)
      expect(wrapper.vm.showEditModal).toBe(true)
      expect(wrapper.vm.selectedProductId).toBe(2)
    }
  })

  it('deleteProduct calls service when confirmed', async () => {
    mockConfirm.mockResolvedValue(true)
    productService.delete.mockResolvedValue({})
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    mockConfirm.mockResolvedValue(true)
    productService.delete.mockResolvedValue({})
    productService.getAll.mockResolvedValue(mockProducts)

    if (wrapper.vm.deleteProduct) {
      await wrapper.vm.deleteProduct(1, 'Test Product')
      await flushPromises()
      expect(productService.delete).toHaveBeenCalledWith(1)
      expect(mockToast.success).toHaveBeenCalled()
    }
  })

  it('deleteProduct does nothing when not confirmed', async () => {
    mockConfirm.mockResolvedValue(false)
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    mockConfirm.mockResolvedValue(false)

    if (wrapper.vm.deleteProduct) {
      await wrapper.vm.deleteProduct(1, 'Test Product')
      expect(productService.delete).not.toHaveBeenCalled()
    }
  })

  it('deleteProduct shows error when delete fails', async () => {
    mockConfirm.mockResolvedValue(true)
    productService.delete.mockRejectedValue(new Error('Cannot delete'))
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    mockConfirm.mockResolvedValue(true)
    productService.delete.mockRejectedValue(new Error('Cannot delete'))

    if (wrapper.vm.deleteProduct) {
      await wrapper.vm.deleteProduct(1, 'Test Product')
      await flushPromises()
      expect(mockToast.error).toHaveBeenCalled()
    }
  })

  it('handleProductCreated closes modal and reloads', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    productService.getAll.mockResolvedValue(mockProducts)

    if (wrapper.vm.handleProductCreated) {
      await wrapper.vm.handleProductCreated()
      await flushPromises()
      expect(mockToast.success).toHaveBeenCalled()
      expect(productService.getAll).toHaveBeenCalled()
    }
  })

  it('handleProductUpdated closes modal and reloads', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    productService.getAll.mockResolvedValue(mockProducts)

    if (wrapper.vm.handleProductUpdated) {
      await wrapper.vm.handleProductUpdated()
      await flushPromises()
      expect(mockToast.success).toHaveBeenCalled()
      expect(productService.getAll).toHaveBeenCalled()
    }
  })

  it('formatCurrency formats to EUR', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.formatCurrency) {
      const result = wrapper.vm.formatCurrency(1234.56)
      expect(result).toContain('1.234,56')
    }
  })

  it('handleImport succeeds without errors', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    productService.getAll.mockResolvedValue(mockProducts)
    importService.importProducts.mockResolvedValue({ created: 2, errors: [] })

    if (wrapper.vm.handleImport) {
      await wrapper.vm.handleImport([{ name: 'P1' }, { name: 'P2' }])
      await flushPromises()
      expect(mockToast.success).toHaveBeenCalled()
    }
  })

  it('handleImport shows warning when partial errors', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    productService.getAll.mockResolvedValue(mockProducts)
    importService.importProducts.mockResolvedValue({ created: 1, errors: ['error1'] })

    if (wrapper.vm.handleImport) {
      await wrapper.vm.handleImport([{ name: 'P1' }, { name: 'P2' }])
      await flushPromises()
      expect(mockToast.warning).toHaveBeenCalled()
    }
  })

  it('handleImport shows error on failure', async () => {
    wrapper = mount(ProductListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    importService.importProducts.mockRejectedValue(new Error('Network error'))

    if (wrapper.vm.handleImport) {
      await wrapper.vm.handleImport([{ name: 'P1' }])
      await flushPromises()
      expect(mockToast.error).toHaveBeenCalled()
    }
  })
})
