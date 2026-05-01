import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseSelect from '../BaseSelect.vue'

describe('BaseSelect', () => {
  const objectOptions = [
    { value: 1, label: 'Option 1' },
    { value: 2, label: 'Option 2' },
    { value: 3, label: 'Option 3' }
  ]

  const stringOptions = ['apple', 'banana', 'cherry']

  it('renders without label when label prop absent', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions } })
    expect(wrapper.find('label').exists()).toBe(false)
  })

  it('renders label when provided', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, label: 'Fruit' } })
    expect(wrapper.find('label').text()).toContain('Fruit')
  })

  it('shows required marker when required=true', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, label: 'Fruit', required: true } })
    expect(wrapper.find('.required').exists()).toBe(true)
  })

  it('hides required marker when required=false', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, label: 'Fruit', required: false } })
    expect(wrapper.find('.required').exists()).toBe(false)
  })

  it('renders placeholder option when provided', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, placeholder: 'Bitte wählen' } })
    expect(wrapper.text()).toContain('Bitte wählen')
  })

  it('always shows default placeholder option', () => {
    // placeholder defaults to 'Bitte auswählen...'
    const wrapper = mount(BaseSelect, { props: { options: stringOptions } })
    const options = wrapper.findAll('option')
    // 3 data options + 1 placeholder
    expect(options.length).toBe(4)
    expect(options[0].text()).toContain('Bitte auswählen')
  })

  it('renders string options (3 data options + default placeholder)', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions } })
    expect(wrapper.findAll('option').length).toBe(4)
  })

  it('renders object options using valueKey/labelKey', () => {
    const wrapper = mount(BaseSelect, { props: { options: objectOptions, modelValue: 1 } })
    const options = wrapper.findAll('option')
    // 3 data options + 1 default placeholder
    expect(options.length).toBe(4)
    expect(options[1].text()).toContain('Option 1')
  })

  it('shows error message when error prop set', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, error: 'Invalid' } })
    expect(wrapper.find('.error-message').text()).toBe('Invalid')
    expect(wrapper.find('.select').classes()).toContain('select-error')
  })

  it('no error message when error absent', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions } })
    expect(wrapper.find('.error-message').exists()).toBe(false)
  })

  it('uses provided id for select', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, id: 'my-select' } })
    expect(wrapper.find('select').attributes('id')).toBe('my-select')
  })

  it('generates random id when no id provided', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions } })
    expect(wrapper.find('select').attributes('id')).toMatch(/^select-/)
  })

  it('applies disabled class when disabled prop set', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, disabled: true } })
    expect(wrapper.find('.select').classes()).toContain('select-disabled')
  })

  it('emits update:modelValue with matched option value on change', async () => {
    const wrapper = mount(BaseSelect, { props: { options: objectOptions, modelValue: null } })
    await wrapper.find('select').setValue('2')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toBe(2)
  })

  it('emits change event on change', async () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions, modelValue: null } })
    await wrapper.find('select').setValue('banana')
    expect(wrapper.emitted('change')).toBeTruthy()
  })

  it('normalizedValue returns modelValue when no options', () => {
    const wrapper = mount(BaseSelect, { props: { options: [], modelValue: 'test' } })
    expect(wrapper.vm.normalizedValue).toBe('test')
  })

  it('normalizedValue returns empty string when modelValue null and no options', () => {
    const wrapper = mount(BaseSelect, { props: { options: [], modelValue: null } })
    expect(wrapper.vm.normalizedValue).toBe('')
  })

  it('normalizedValue matches option by loose equality', () => {
    const wrapper = mount(BaseSelect, { props: { options: objectOptions, modelValue: '1' } })
    // option.value === 1, modelValue === '1', loose equality should match
    expect(wrapper.vm.normalizedValue).toBe(1)
  })

  it('normalizedValue returns modelValue when no match', () => {
    const wrapper = mount(BaseSelect, { props: { options: objectOptions, modelValue: 99 } })
    expect(wrapper.vm.normalizedValue).toBe(99)
  })

  it('emits raw string value when no option match', async () => {
    const wrapper = mount(BaseSelect, { props: { options: objectOptions, modelValue: null } })
    const select = wrapper.find('select')
    // Use a value that doesn't match any option string representation
    Object.defineProperty(select.element, 'value', { writable: true, configurable: true, value: 'custom' })
    await select.trigger('change')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    // value 'custom' doesn't match any option, raw value returned
    expect(typeof emitted[0][0]).toBe('string')
  })

  it('getOptionValue returns primitive for string option', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions } })
    expect(wrapper.vm.getOptionValue('apple')).toBe('apple')
  })

  it('getOptionLabel returns primitive for string option', () => {
    const wrapper = mount(BaseSelect, { props: { options: stringOptions } })
    expect(wrapper.vm.getOptionLabel('apple')).toBe('apple')
  })
})
