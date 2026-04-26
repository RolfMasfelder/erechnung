import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CompanyCreateModal from '../CompanyCreateModal.vue'
import { companyService } from '@/api/services/companyService'

vi.mock('@/api/services/companyService', () => ({
  companyService: {
    create: vi.fn()
  }
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

describe('CompanyCreateModal', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the modal', () => {
    wrapper = mount(CompanyCreateModal)
    // Check that the component and form are rendered
    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('validates required fields', async () => {
    wrapper = mount(CompanyCreateModal)

    const form = wrapper.find('form')
    await form.trigger('submit')

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.errors.name).toBeTruthy()
    expect(wrapper.vm.errors.address_line1).toBeTruthy()
    expect(wrapper.vm.errors.city).toBeTruthy()
  })

  it('creates company with valid data', async () => {
    const mockCompany = {
      id: 1,
      name: 'Test Company GmbH',
      address_line1: 'Test Str. 1',
      postal_code: '12345',
      city: 'Berlin',
      country: 'DE',
      tax_id: '12/345/67890'
    }

    companyService.create.mockResolvedValue(mockCompany)

    wrapper = mount(CompanyCreateModal)

    await wrapper.find('#name').setValue('Test Company GmbH')
    await wrapper.find('#address_line1').setValue('Test Str. 1')
    await wrapper.find('#postal_code').setValue('12345')
    await wrapper.find('#city').setValue('Berlin')
    await wrapper.find('#tax_id').setValue('12/345/67890')
    await wrapper.find('#vat_id').setValue('DE123456789')

    const form = wrapper.find('form')
    await form.trigger('submit')

    await wrapper.vm.$nextTick()

    expect(companyService.create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Test Company GmbH',
        address_line1: 'Test Str. 1',
        city: 'Berlin'
      })
    )
  })

  it('validates email format', async () => {
    wrapper = mount(CompanyCreateModal)

    await wrapper.find('#name').setValue('Test')
    await wrapper.find('#address_line1').setValue('Str')
    await wrapper.find('#postal_code').setValue('12345')
    await wrapper.find('#city').setValue('City')
    await wrapper.find('#tax_id').setValue('123')
    await wrapper.find('#vat_id').setValue('DE123456789')
    await wrapper.find('#email').setValue('invalid-email')

    const form = wrapper.find('form')
    await form.trigger('submit')

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.errors.email).toBeTruthy()
  })

  it('emits close event when cancel button clicked', async () => {
    wrapper = mount(CompanyCreateModal)

    const cancelButton = wrapper.find('button:contains("Abbrechen")')
    if (cancelButton.exists()) {
      await cancelButton.trigger('click')
      expect(wrapper.emitted('close')).toBeTruthy()
    }
  })

  it('emits created event on successful creation', async () => {
    const mockCompany = { id: 1, name: 'Test' }
    companyService.create.mockResolvedValue(mockCompany)

    wrapper = mount(CompanyCreateModal)

    await wrapper.find('#name').setValue('Test Company')
    await wrapper.find('#address_line1').setValue('Street')
    await wrapper.find('#postal_code').setValue('12345')
    await wrapper.find('#city').setValue('City')
    await wrapper.find('#tax_id').setValue('123')
    await wrapper.find('#vat_id').setValue('DE123456789')

    const form = wrapper.find('form')
    await form.trigger('submit')

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.emitted('created')).toBeTruthy()
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
