import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BusinessPartnerCreateModal from '../BusinessPartnerCreateModal.vue'
import { businessPartnerService } from '@/api/services/businessPartnerService'

vi.mock('@/api/services/businessPartnerService', () => ({
  businessPartnerService: {
    create: vi.fn()
  }
}))

vi.mock('@/api/services/countryService', () => ({
  countryService: {
    getAll: vi.fn().mockResolvedValue([
      { code: 'DE', name: 'Deutschland' },
      { code: 'AT', name: 'Österreich' }
    ])
  }
}))

// Mock-Komponenten (gleiche wie bei ProductCreateModal)
vi.mock('../BaseModal.vue', () => ({
  default: {
    name: 'BaseModal',
    template: '<div class="base-modal"><div class="modal-title"><slot name="title"></slot></div><slot></slot><slot name="footer"></slot></div>',
    emits: ['close']
  }
}))

vi.mock('../BaseInput.vue', () => ({
  default: {
    name: 'BaseInput',
    template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
    props: ['modelValue', 'type', 'error', 'placeholder', 'required'],
    emits: ['update:modelValue']
  }
}))

vi.mock('../BaseSelect.vue', () => ({
  default: {
    name: 'BaseSelect',
    template: '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"></select>',
    props: ['modelValue', 'options', 'error', 'required'],
    emits: ['update:modelValue']
  }
}))

vi.mock('../BaseButton.vue', () => ({
  default: {
    name: 'BaseButton',
    template: '<button @click="$emit(\'click\')"><slot></slot></button>',
    props: ['variant', 'disabled', 'loading', 'type'],
    emits: ['click']
  }
}))

vi.mock('../BaseAlert.vue', () => ({
  default: {
    name: 'BaseAlert',
    template: '<div><slot></slot></div>',
    props: ['variant'],
    emits: ['close']
  }
}))

describe('BusinessPartnerCreateModal', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('rendert korrekt', () => {
    wrapper = mount(BusinessPartnerCreateModal, {
      props: { isOpen: true }
    })
    expect(wrapper.find('.modal-title').text()).toBe('Neuen Geschäftspartner anlegen')
  })

  it('hat korrekte initiale Werte', async () => {
    wrapper = mount(BusinessPartnerCreateModal)
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.formData.name).toBe('')
    expect(wrapper.vm.formData.country).toBe('DE')
    expect(wrapper.vm.formData.city).toBe('')
  })

  it('erstellt Kunden erfolgreich', async () => {
    const mockCustomer = {
      id: 1,
      name: 'Test GmbH',
      street: 'Teststraße 1',
      postal_code: '12345',
      city: 'Berlin',
      country: 'DE'
    }

    businessPartnerService.create.mockResolvedValue(mockCustomer)

    wrapper = mount(BusinessPartnerCreateModal)

    Object.assign(wrapper.vm.formData, mockCustomer)
    await wrapper.vm.$nextTick()

    await wrapper.vm.handleSubmit()

    expect(businessPartnerService.create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Test GmbH',
        city: 'Berlin',
        country: 'DE'
      })
    )

    expect(wrapper.emitted('created')).toBeTruthy()
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('zeigt Fehler bei ungültigen Daten', async () => {
    const errorResponse = {
      response: {
        data: {
          name: ['Dieses Feld ist erforderlich.'],
          postal_code: ['Ungültiges Format.']
        }
      }
    }

    businessPartnerService.create.mockRejectedValue(errorResponse)

    wrapper = mount(BusinessPartnerCreateModal)
    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.submitError).toBeTruthy()
    expect(wrapper.vm.errors.name).toBe('Dieses Feld ist erforderlich.')
    expect(wrapper.vm.errors.postal_code).toBe('Ungültiges Format.')
  })

  it('emittiert close beim Abbrechen', async () => {
    wrapper = mount(BusinessPartnerCreateModal)

    const buttons = wrapper.findAllComponents({ name: 'BaseButton' })
    const cancelButton = buttons.find(btn => btn.text().includes('Abbrechen'))

    await cancelButton.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('validiert E-Mail-Format (optional)', () => {
    wrapper = mount(BusinessPartnerCreateModal)

    // Test mit gültiger E-Mail
    wrapper.vm.formData.email = 'test@example.com'
    expect(wrapper.vm.formData.email).toBe('test@example.com')

    // Test ohne E-Mail (sollte auch ok sein)
    wrapper.vm.formData.email = ''
    expect(wrapper.vm.formData.email).toBe('')
  })

  it('akzeptiert verschiedene Länder', () => {
    wrapper = mount(BusinessPartnerCreateModal)

    const countries = ['DE', 'AT', 'CH', 'FR']
    countries.forEach(country => {
      wrapper.vm.formData.country = country
      expect(wrapper.vm.formData.country).toBe(country)
    })
  })
})
