import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ProductListView from '../ProductListView.vue'
import { productService } from '@/api/services/productService'

vi.mock('@/api/services/productService', () => ({
  productService: {
    getAll: vi.fn(),
    delete: vi.fn()
  }
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

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
})
