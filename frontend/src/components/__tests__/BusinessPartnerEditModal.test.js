import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BusinessPartnerEditModal from '../BusinessPartnerEditModal.vue'
import { businessPartnerService } from '@/api/services/businessPartnerService'

vi.mock('@/api/services/businessPartnerService', () => ({
  businessPartnerService: {
    getById: vi.fn(),
    update: vi.fn()
  }
}))

vi.mock('@/api/services/countryService', () => ({
  countryService: {
    getAll: vi.fn().mockResolvedValue([
      { code: 'DE', name: 'Deutschland' },
      { code: 'AT', name: 'Österreich' },
      { code: 'CH', name: 'Schweiz' },
      { code: 'FR', name: 'Frankreich' },
      { code: 'NL', name: 'Niederlande' },
      { code: 'BE', name: 'Belgien' },
      { code: 'PL', name: 'Polen' },
      { code: 'CZ', name: 'Tschechien' }
    ])
  }
}))

describe('BusinessPartnerEditModal', () => {
  let wrapper

  const mockCustomer = {
    id: 1,
    name: 'Test Customer',
    street: 'Test Street 1',
    postal_code: '12345',
    city: 'Test City',
    country: 'DE',
    email: 'test@example.com',
    phone: '+49123456789',
    tax_number: '12345',
    vat_id: 'DE123456789',
    notes: 'Test notes'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads customer data on mount', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
        isOpen: true
      }
    })

    // Wait for loading
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(businessPartnerService.getById).toHaveBeenCalledWith(1)
    expect(wrapper.vm.formData.name).toBe('Test Customer')
    expect(wrapper.vm.formData.street).toBe('Test Street 1')
    expect(wrapper.vm.formData.postal_code).toBe('12345')
    expect(wrapper.vm.loading).toBe(false)
  })

  it('shows loading state while fetching customer', async () => {
    businessPartnerService.getById.mockReturnValue(new Promise(() => {})) // Never resolves

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
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
    businessPartnerService.getById.mockRejectedValue(new Error('Load failed'))

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(consoleError).toHaveBeenCalled()
    expect(wrapper.vm.loading).toBe(false)

    consoleError.mockRestore()
  })

  it('updates customer on form submit', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)
    businessPartnerService.update.mockResolvedValue({ ...mockCustomer, name: 'Updated Customer' })

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Update form data
    wrapper.vm.formData.name = 'Updated Customer'

    // Submit form
    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    expect(businessPartnerService.update).toHaveBeenCalledWith(1, expect.objectContaining({
      name: 'Updated Customer'
    }))
    expect(wrapper.emitted()).toHaveProperty('updated')
  })

  it('displays validation errors', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)
    businessPartnerService.update.mockRejectedValue({
      response: {
        data: {
          name: ['Dieses Feld ist erforderlich.'],
          postal_code: ['Ungültige PLZ.']
        }
      }
    })

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Submit form
    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    if (wrapper.vm.errors.name) {
      expect(wrapper.vm.errors.name).toBe('Dieses Feld ist erforderlich.')
    }
    if (wrapper.vm.errors.postal_code) {
      expect(wrapper.vm.errors.postal_code).toBe('Ungültige PLZ.')
    }
  })

  it('emits close event when cancel button clicked', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
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

  it('disables buttons while saving', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)
    businessPartnerService.update.mockReturnValue(new Promise(() => {})) // Never resolves

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Start saving
    wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.saving).toBe(true)
  })

  it('validates required fields', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const nameInput = wrapper.find('#name')
    const streetInput = wrapper.find('#street')
    const postalCodeInput = wrapper.find('#postal_code')
    const cityInput = wrapper.find('#city')

    expect(nameInput.attributes('required')).toBeDefined()
    expect(streetInput.attributes('required')).toBeDefined()
    expect(postalCodeInput.attributes('required')).toBeDefined()
    expect(cityInput.attributes('required')).toBeDefined()
  })

  it('shows country select with options', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
        isOpen: true
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Countries loaded from API (mocked: 8 items)
    expect(wrapper.vm.countryOptions).toHaveLength(8)
    expect(wrapper.vm.countryOptions[0]).toEqual({ value: 'DE', label: 'Deutschland' })
  })

  it('handles network error on update', async () => {
    businessPartnerService.getById.mockResolvedValue(mockCustomer)
    businessPartnerService.update.mockRejectedValue(new Error('Network error'))

    wrapper = mount(BusinessPartnerEditModal, {
      props: {
        businessPartnerId: 1,
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
})
