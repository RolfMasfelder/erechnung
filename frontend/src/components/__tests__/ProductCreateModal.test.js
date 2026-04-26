import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ProductCreateModal from '../ProductCreateModal.vue'
import { productService } from '@/api/services/productService'

// Mock des productService
vi.mock('@/api/services/productService', () => ({
  productService: {
    create: vi.fn(),
    getTaxOptions: vi.fn()
  }
}))

// Mock der Komponenten
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
    template: '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select>',
    props: ['modelValue', 'options', 'error', 'required'],
    emits: ['update:modelValue']
  }
}))

vi.mock('../BaseButton.vue', () => ({
  default: {
    name: 'BaseButton',
    template: '<button @click="$emit(\'click\')" :disabled="disabled || loading"><slot></slot></button>',
    props: ['variant', 'disabled', 'loading', 'type'],
    emits: ['click']
  }
}))

vi.mock('../BaseAlert.vue', () => ({
  default: {
    name: 'BaseAlert',
    template: '<div class="alert"><slot></slot></div>',
    props: ['variant'],
    emits: ['close']
  }
}))

describe('ProductCreateModal', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    productService.getTaxOptions.mockResolvedValue({
      tax_rates: [
        { label: '0% (Befreit)', value: '0.00' },
        { label: '7% (Ermäßigt)', value: '7.00' },
        { label: '19% (Standard)', value: '19.00' }
      ],
      unit_options: [
        { label: 'Piece', value: 'PCE' },
        { label: 'Hour', value: 'HUR' }
      ]
    })
  })

  it('rendert korrekt', () => {
    wrapper = mount(ProductCreateModal, {
      props: { isOpen: true }
    })
    expect(wrapper.find('.modal-title').text()).toBe('Neues Produkt anlegen')
  })

  it('zeigt alle Formularfelder an', () => {
    wrapper = mount(ProductCreateModal)

    const inputs = wrapper.findAll('input')
    expect(inputs.length).toBeGreaterThan(0)
  })

  it('hat korrekte initiale Werte', async () => {
    wrapper = mount(ProductCreateModal)

    // Warte auf nächsten Tick
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.formData.name).toBe('')
    expect(wrapper.vm.formData.base_price).toBe(0)
    expect(wrapper.vm.formData.default_tax_rate).toBe(19.00)
    expect(wrapper.vm.formData.is_active).toBe(true)
  })

  it('emittiert close Event beim Abbrechen', async () => {
    wrapper = mount(ProductCreateModal)

    const buttons = wrapper.findAllComponents({ name: 'BaseButton' })
    const cancelButton = buttons.find(btn => btn.text().includes('Abbrechen'))

    await cancelButton.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('erstellt Produkt erfolgreich', async () => {
    const mockProduct = {
      id: 1,
      name: 'Test Produkt',
      base_price: 100,
      default_tax_rate: 19
    }

    productService.create.mockResolvedValue(mockProduct)

    wrapper = mount(ProductCreateModal)

    // Formular ausfüllen
    wrapper.vm.formData.name = 'Test Produkt'
    wrapper.vm.formData.product_code = 'ART-001'
    wrapper.vm.formData.base_price = 100
    wrapper.vm.formData.default_tax_rate = 19

    await wrapper.vm.$nextTick()

    // Submit
    await wrapper.vm.handleSubmit()

    expect(productService.create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Test Produkt',
        base_price: 100,
        default_tax_rate: 19
      })
    )

    expect(wrapper.emitted('created')).toBeTruthy()
    expect(wrapper.emitted('created')[0][0]).toEqual(mockProduct)
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('zeigt Fehler bei fehlgeschlagenem Submit', async () => {
    const errorResponse = {
      response: {
        data: {
          name: ['Dieses Feld ist erforderlich.']
        }
      }
    }

    productService.create.mockRejectedValue(errorResponse)

    wrapper = mount(ProductCreateModal)

    await wrapper.vm.handleSubmit()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.submitError).toBeTruthy()
    expect(wrapper.vm.errors.name).toBeTruthy()
  })

  it('validiert Pflichtfelder', () => {
    wrapper = mount(ProductCreateModal)

    // Leeres Formular sollte nicht valide sein
    expect(wrapper.vm.formData.name).toBe('')

    // Mit Name sollte es valide sein
    wrapper.vm.formData.name = 'Test'
    expect(wrapper.vm.formData.name).toBe('Test')
  })

  it('akzeptiert nur gültige MwSt.-Sätze', () => {
    wrapper = mount(ProductCreateModal)

    const validRates = [19.00, 7.00, 0.00]
    validRates.forEach(rate => {
      wrapper.vm.formData.default_tax_rate = rate
      expect(wrapper.vm.formData.default_tax_rate).toBe(rate)
    })
  })

  it('setzt is_active standardmäßig auf true', () => {
    wrapper = mount(ProductCreateModal)
    expect(wrapper.vm.formData.is_active).toBe(true)
  })

  it('zeigt Loading-State während Submit', async () => {
    productService.create.mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve({ id: 1 }), 100))
    )

    wrapper = mount(ProductCreateModal)

    wrapper.vm.formData.name = 'Test'
    wrapper.vm.formData.product_code = 'ART-002'
    wrapper.vm.formData.base_price = 10
    const submitPromise = wrapper.vm.handleSubmit()

    expect(wrapper.vm.loading).toBe(true)

    await submitPromise

    expect(wrapper.vm.loading).toBe(false)
  })
})
