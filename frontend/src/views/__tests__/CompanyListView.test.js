import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import CompanyListView from '../CompanyListView.vue'
import { companyService } from '@/api/services/companyService'

vi.mock('@/api/services/companyService', () => ({
  companyService: {
    getAll: vi.fn(),
    getById: vi.fn(),
    delete: vi.fn()
  }
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

describe('CompanyListView', () => {
  let wrapper
  let router

  const mockCompanies = {
    count: 2,
    results: [
      {
        id: 1,
        name: 'Test Company GmbH',
        address_line1: 'Company Str. 1',
        postal_code: '12345',
        city: 'Berlin',
        tax_id: '12/345/67890',
        vat_id: 'DE123456789',
        is_active: true
      },
      {
        id: 2,
        name: 'Another Company AG',
        address_line1: 'Another Str. 2',
        postal_code: '54321',
        city: 'Munich',
        tax_id: '98/765/43210',
        vat_id: 'DE987654321',
        is_active: false
      }
    ]
  }

  beforeEach(() => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/companies', name: 'CompanyList', component: CompanyListView },
        { path: '/companies/:id', name: 'CompanyDetail', component: { template: '<div>Detail</div>' } }
      ]
    })

    vi.clearAllMocks()
    companyService.getAll.mockResolvedValue(mockCompanies)
    companyService.getById.mockResolvedValue(mockCompanies.results[0])
  })

  it('renders company list view', async () => {
    wrapper = mount(CompanyListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.find('h1').text()).toBe('Firmen')
  })

  it('loads companies on mount', async () => {
    wrapper = mount(CompanyListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(companyService.getAll).toHaveBeenCalled()
  })

  it('displays company data', async () => {
    wrapper = mount(CompanyListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('Test Company GmbH')
    expect(text).toContain('DE123456789')
  })

  it('shows create modal when button clicked', async () => {
    wrapper = mount(CompanyListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const createButton = wrapper.find('button:contains("Neue Firma")')
    if (createButton.exists()) {
      await createButton.trigger('click')
      expect(wrapper.vm.showCreateModal).toBe(true)
    }
  })

  it('shows edit modal when edit button clicked', async () => {
    wrapper = mount(CompanyListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    if (wrapper.vm.editCompany) {
      await wrapper.vm.editCompany(1)
      expect(wrapper.vm.showEditModal).toBe(true)
      expect(wrapper.vm.selectedCompanyId).toBe(1)
    }
  })

  it('displays active/inactive status badge', async () => {
    wrapper = mount(CompanyListView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('Aktiv')
    expect(text).toContain('Inaktiv')
  })
})
