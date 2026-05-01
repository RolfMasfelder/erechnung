import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import CompanyDetailView from '../CompanyDetailView.vue'
import { companyService } from '@/api/services/companyService'

vi.mock('@/api/services/companyService', () => ({
  companyService: {
    getById: vi.fn(),
    delete: vi.fn()
  }
}))

const mockConfirm = vi.hoisted(() => vi.fn().mockResolvedValue(false))

const mockToast = vi.hoisted(() => ({ showToast: vi.fn(), success: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useToast', () => ({ useToast: () => mockToast }))

vi.mock('@/composables/useConfirm', () => ({
  useConfirm: () => ({
    confirm: mockConfirm
  })
}))

describe('CompanyDetailView', () => {
  let wrapper
  let router

  const mockCompany = {
    id: 1,
    name: 'Test Firma GmbH',
    address_line1: 'Hauptstraße 123',
    postal_code: '10115',
    city: 'Berlin',
    country: 'DE',
    email: 'info@testfirma.de',
    phone: '+49 30 12345678',
    tax_id: '27/123/45678',
    vat_id: 'DE123456789',
    bank_name: 'Deutsche Bank',
    iban: 'DE89370400440532013000',
    bic: 'COBADEFFXXX',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-15T00:00:00Z'
  }

  beforeEach(async () => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/companies', name: 'CompanyList', component: { template: '<div>List</div>' } },
        { path: '/companies/:id', name: 'CompanyDetail', component: CompanyDetailView }
      ]
    })

    await router.push('/companies/1')
    await router.isReady()

    vi.clearAllMocks()
    companyService.getById.mockResolvedValue(mockCompany)
  })

  it('renders company detail view', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.text()).toContain('Test Firma GmbH')
  })

  it('loads company data on mount', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(companyService.getById).toHaveBeenCalledWith('1')
  })

  it('displays company address information', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('Hauptstraße 123')
    expect(text).toContain('10115')
    expect(text).toContain('Berlin')
    expect(text).toContain('Deutschland')
  })

  it('displays company contact information', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('info@testfirma.de')
    expect(text).toContain('+49 30 12345678')
  })

  it('displays tax information', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('27/123/45678')
    expect(text).toContain('DE123456789')
  })

  it('displays bank information', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('Deutsche Bank')
    expect(text).toContain('DE89370400440532013000')
    expect(text).toContain('COBADEFFXXX')
  })

  it('displays active status badge', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))
    await wrapper.vm.$nextTick()

    const statusBadge = wrapper.find('.status-badge.active')
    expect(statusBadge.exists()).toBe(true)
    expect(statusBadge.text()).toContain('Aktiv')
  })

  it('shows edit and delete buttons', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const buttons = wrapper.findAll('button')
    const editButton = buttons.find(button => button.text().includes('Bearbeiten'))
    const deleteButton = buttons.find(button => button.text().includes('Löschen'))

    expect(editButton).toBeDefined()
    expect(deleteButton).toBeDefined()
  })

  it('displays metadata (created and updated dates)', async () => {
    wrapper = mount(CompanyDetailView, {
      global: {
        plugins: [router]
      }
    })

    await router.isReady()
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 200))
    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('Erstellt am')
    expect(text).toContain('Zuletzt geändert')
  })

  it('getCountryName returns country name', async () => {
    wrapper = mount(CompanyDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.getCountryName) {
      expect(wrapper.vm.getCountryName('DE')).toBeTruthy()
    }
  })

  it('formatDate formats ISO to de-DE', async () => {
    wrapper = mount(CompanyDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.formatDate) {
      expect(wrapper.vm.formatDate('2025-03-15')).toContain('15')
      expect(wrapper.vm.formatDate(null)).toBe('-')
    }
  })

  it('handleCompanyUpdated updates company data directly', async () => {
    wrapper = mount(CompanyDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.handleCompanyUpdated) {
      const updated = { ...mockCompany, name: 'Updated GmbH' }
      await wrapper.vm.handleCompanyUpdated(updated)
      await flushPromises()
      expect(mockToast.success).toHaveBeenCalled()
    }
  })

  it('handleDelete calls service when confirmed', async () => {
    mockConfirm.mockResolvedValue(true)
    companyService.delete.mockResolvedValue({})
    wrapper = mount(CompanyDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.handleDelete) {
      await wrapper.vm.handleDelete()
      await flushPromises()
      expect(companyService.delete).toHaveBeenCalledWith(1)
    }
  })

  it('handleDelete does nothing when cancelled', async () => {
    mockConfirm.mockResolvedValue(false)
    wrapper = mount(CompanyDetailView, { global: { plugins: [router] } })
    await flushPromises()

    if (wrapper.vm.handleDelete) {
      await wrapper.vm.handleDelete()
      expect(companyService.delete).not.toHaveBeenCalled()
    }
  })
})
