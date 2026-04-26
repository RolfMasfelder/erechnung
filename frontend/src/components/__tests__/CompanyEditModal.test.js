import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CompanyEditModal from '../CompanyEditModal.vue'
import { companyService } from '@/api/services/companyService'

vi.mock('@/api/services/companyService', () => ({
  companyService: {
    getById: vi.fn(),
    update: vi.fn()
  }
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    showToast: vi.fn()
  })
}))

describe('CompanyEditModal', () => {
  let wrapper

  const mockCompany = {
    id: 1,
    name: 'Test Company GmbH',
    address_line1: 'Test Str. 1',
    postal_code: '12345',
    city: 'Berlin',
    country: 'DE',
    email: 'test@company.de',
    phone: '+49 123 456789',
    tax_id: '12/345/67890',
    vat_id: 'DE123456789',
    is_active: true
  }

  beforeEach(() => {
    vi.clearAllMocks()
    companyService.getById.mockResolvedValue(mockCompany)
  })

  it('renders the modal', async () => {
    wrapper = mount(CompanyEditModal, {
      props: {
        companyId: 1
      }
    })
    // Check that the component is rendered
    expect(wrapper.exists()).toBe(true)
  })

  it('loads company data on mount', async () => {
    wrapper = mount(CompanyEditModal, {
      props: {
        companyId: 1
      }
    })

    await flushPromises()

    expect(companyService.getById).toHaveBeenCalledWith(1)
    expect(wrapper.vm.formData.name).toBe('Test Company GmbH')
  })

  it('displays loading state while fetching data', async () => {
    let resolvePromise
    const pendingPromise = new Promise(resolve => {
      resolvePromise = resolve
    })
    companyService.getById.mockReturnValue(pendingPromise)

    wrapper = mount(CompanyEditModal, {
      props: {
        companyId: 1
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.find('.loading').exists()).toBe(true)

    resolvePromise(mockCompany)
    await flushPromises()
    expect(wrapper.find('.loading').exists()).toBe(false)
  })

  it('updates company with modified data', async () => {
    const updatedCompany = { ...mockCompany, name: 'Updated Company' }
    companyService.update.mockResolvedValue(updatedCompany)

    wrapper = mount(CompanyEditModal, {
      props: {
        companyId: 1
      }
    })

    await flushPromises()

    await wrapper.find('#name').setValue('Updated Company')

    const form = wrapper.find('form')
    await form.trigger('submit')

    await flushPromises()

    expect(companyService.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        name: 'Updated Company'
      })
    )
  })

  it('validates required fields on submit', async () => {
    wrapper = mount(CompanyEditModal, {
      props: {
        companyId: 1
      }
    })

    await flushPromises()

    await wrapper.find('#name').setValue('')
    await wrapper.find('#address_line1').setValue('')

    const form = wrapper.find('form')
    await form.trigger('submit')

    await wrapper.vm.$nextTick()

    expect(wrapper.vm.errors.name).toBeTruthy()
    expect(wrapper.vm.errors.address_line1).toBeTruthy()
  })

  it('emits updated event on successful update', async () => {
    companyService.update.mockResolvedValue(mockCompany)

    wrapper = mount(CompanyEditModal, {
      props: {
        companyId: 1
      }
    })

    await flushPromises()

    const form = wrapper.find('form')
    await form.trigger('submit')

    await flushPromises()

    expect(wrapper.emitted('updated')).toBeTruthy()
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
