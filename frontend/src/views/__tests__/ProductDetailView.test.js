import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const mockProduct = {
  id: 1,
  name: 'Test Produkt',
  article_number: 'ART-001',
  base_price: '100.00',
  default_tax_rate: '19.00',
  unit: 1,
  is_active: true,
  description: 'Test description'
}

vi.mock('@/api/services/productService', () => ({
  productService: {
    getById: vi.fn(),
    delete: vi.fn()
  }
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '1' } }),
  useRouter: () => ({ push: vi.fn() })
}))

vi.mock('@/components/BaseCard.vue', { default: { template: '<div><slot /></div>' } })
vi.mock('@/components/BaseButton.vue', { default: { template: '<button @click="$emit(\'click\')"><slot /></button>', emits: ['click'] } })
vi.mock('@/components/BaseAlert.vue', { default: { template: '<div />' } })
vi.mock('@/components/ProductEditModal.vue', { default: { template: '<div />' } })

import { productService } from '@/api/services/productService'
import ProductDetailView from '../ProductDetailView.vue'

describe('ProductDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    productService.getById.mockResolvedValue(mockProduct)
  })

  it('loads product on mount', async () => {
    mount(ProductDetailView)
    await flushPromises()
    expect(productService.getById).toHaveBeenCalledWith('1')
  })

  it('handleProductUpdated reloads product', async () => {
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    productService.getById.mockClear()
    await wrapper.vm.handleProductUpdated()
    await flushPromises()
    expect(productService.getById).toHaveBeenCalled()
  })

  it('handleDelete skips when confirm returns false', async () => {
    globalThis.confirm = vi.fn().mockReturnValue(false)
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    await wrapper.vm.handleDelete()
    expect(productService.delete).not.toHaveBeenCalled()
  })

  it('handleDelete deletes and redirects when confirmed', async () => {
    globalThis.confirm = vi.fn().mockReturnValue(true)
    productService.delete.mockResolvedValue({})
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    await wrapper.vm.handleDelete()
    await flushPromises()
    expect(productService.delete).toHaveBeenCalledWith(1)
  })

  it('handleDelete shows alert on delete error', async () => {
    globalThis.confirm = vi.fn().mockReturnValue(true)
    globalThis.alert = vi.fn()
    productService.delete.mockRejectedValue(new Error('In use'))
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    await wrapper.vm.handleDelete()
    await flushPromises()
    expect(globalThis.alert).toHaveBeenCalled()
  })

  it('formatCurrency handles numeric value', async () => {
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    const result = wrapper.vm.formatCurrency(100)
    expect(result).toContain('100')
  })

  it('formatCurrency handles string value with comma', async () => {
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    const result = wrapper.vm.formatCurrency('1.234,56')
    expect(typeof result).toBe('string')
  })

  it('calculateGrossPrice computes net + VAT', async () => {
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    const result = wrapper.vm.calculateGrossPrice({ base_price: '100', default_tax_rate: '19' })
    expect(result).toBeCloseTo(119, 1)
  })

  it('toNumericValue handles NaN string', async () => {
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    const result = wrapper.vm.toNumericValue('not-a-number')
    expect(result).toBe(0)
  })

  it('toNumericValue handles non-finite number', async () => {
    const wrapper = mount(ProductDetailView)
    await flushPromises()
    const result = wrapper.vm.toNumericValue(Infinity)
    expect(result).toBe(0)
  })
})
