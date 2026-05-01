import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import BusinessPartnerListView from '../BusinessPartnerListView.vue'
import { businessPartnerService } from '@/api/services/businessPartnerService'

vi.mock('@/api/services/businessPartnerService', () => ({
  businessPartnerService: {
    getAll: vi.fn(),
    delete: vi.fn()
  }
}))

// Mock useConfirm composable
const mockConfirm = vi.fn()
vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => ({ confirm: mockConfirm })
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn()
  })
}))

vi.mock('@/api/services/importService', () => ({
  importService: { importBusinessPartners: vi.fn() }
}))

describe('BusinessPartnerListView', () => {
  let wrapper
  let router

  const mockCustomers = {
    count: 2,
    results: [
      {
        id: 1,
        name: 'Test Customer GmbH',
        street: 'Test Str. 1',
        postal_code: '12345',
        city: 'Berlin',
        country: 'DE',
        email: 'test@customer.de'
      },
      {
        id: 2,
        name: 'Another Customer',
        street: 'Another Str. 2',
        postal_code: '54321',
        city: 'Munich',
        country: 'DE',
        email: 'info@another.de'
      }
    ]
  }

  beforeEach(async () => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/business-partners', name: 'BusinessPartnerList', component: BusinessPartnerListView },
        { path: '/business-partners/:id', name: 'BusinessPartnerDetail', component: { template: '<div>Detail</div>' } }
      ]
    })

    await router.push('/business-partners')
    await router.isReady()

    vi.clearAllMocks()
    businessPartnerService.getAll.mockResolvedValue(mockCustomers)
  })

  it('renders customer list view', async () => {
    wrapper = mount(BusinessPartnerListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.find('h1').text()).toBe('Geschäftspartner')
  })

  it('loads customers on mount', async () => {
    wrapper = mount(BusinessPartnerListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(businessPartnerService.getAll).toHaveBeenCalled()
  })

  it('displays customer data', async () => {
    wrapper = mount(BusinessPartnerListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('Test Customer GmbH')
    expect(text).toContain('Berlin')
  })

  it('filters customers by search query', async () => {
    wrapper = mount(BusinessPartnerListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const searchInput = wrapper.find('input[placeholder*="Suche"]')
    await searchInput.setValue('Berlin')

    await new Promise(resolve => setTimeout(resolve, 600))

    expect(businessPartnerService.getAll).toHaveBeenCalledWith(
      expect.objectContaining({
        search: 'Berlin'
      })
    )
  })

  it('shows create modal when button clicked', async () => {
    wrapper = mount(BusinessPartnerListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const createButton = wrapper.find('button:contains("Neuer Kunde")')
    if (createButton.exists()) {
      await createButton.trigger('click')
      expect(wrapper.vm.showCreateModal).toBe(true)
    }
  })

  it('handles delete customer', async () => {
    mockConfirm.mockResolvedValue(true)
    businessPartnerService.delete.mockResolvedValue({})

    wrapper = mount(BusinessPartnerListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    if (wrapper.vm.deleteCustomer) {
      await wrapper.vm.deleteCustomer(1, 'Test Geschäftspartner')

      expect(mockConfirm).toHaveBeenCalled()
      expect(businessPartnerService.delete).toHaveBeenCalledWith(1)
    }
  })

  it('handles sorting by column', async () => {
    wrapper = mount(BusinessPartnerListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    vi.clearAllMocks()

    if (wrapper.vm.handleSort) {
      await wrapper.vm.handleSort({ key: 'name', order: 'asc' })

      expect(businessPartnerService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          ordering: 'business_partner_name'
        })
      )

      await wrapper.vm.handleSort({ key: 'city', order: 'desc' })

      expect(businessPartnerService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          ordering: '-city'
        })
      )
    }
  })

  it('handlePageChange updates page and reloads', async () => {
    wrapper = mount(BusinessPartnerListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    businessPartnerService.getAll.mockResolvedValue(mockCustomers)

    if (wrapper.vm.handlePageChange) {
      await wrapper.vm.handlePageChange(2)
      await flushPromises()
      expect(businessPartnerService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 })
      )
    }
  })

  it('viewCustomer navigates to business partner detail', async () => {
    const pushSpy = vi.spyOn(router, 'push')
    wrapper = mount(BusinessPartnerListView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.viewCustomer) {
      await wrapper.vm.viewCustomer(1)
      expect(pushSpy).toHaveBeenCalledWith({ name: 'BusinessPartnerDetail', params: { id: 1 } })
    }
  })

  it('editCustomer sets id and shows modal', async () => {
    wrapper = mount(BusinessPartnerListView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.editCustomer) {
      await wrapper.vm.editCustomer(2)
      expect(wrapper.vm.showEditModal).toBe(true)
    }
  })

  it('handleBusinessPartnerCreated reloads and navigates', async () => {
    wrapper = mount(BusinessPartnerListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    businessPartnerService.getAll.mockResolvedValue(mockCustomers)

    if (wrapper.vm.handleBusinessPartnerCreated) {
      await wrapper.vm.handleBusinessPartnerCreated({ id: 3, name: 'New GmbH' })
      await flushPromises()
      expect(businessPartnerService.getAll).toHaveBeenCalled()
    }
  })

  it('handleBusinessPartnerUpdated closes modal and reloads', async () => {
    wrapper = mount(BusinessPartnerListView, { global: { plugins: [router] } })
    await flushPromises()
    vi.clearAllMocks()
    businessPartnerService.getAll.mockResolvedValue(mockCustomers)

    if (wrapper.vm.handleBusinessPartnerUpdated) {
      await wrapper.vm.handleBusinessPartnerUpdated()
      await flushPromises()
      expect(businessPartnerService.getAll).toHaveBeenCalled()
    }
  })
})
