import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseRadio from '../BaseRadio.vue'

describe('BaseRadio', () => {
  it('renders radio input', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: null
      }
    })

    expect(wrapper.find('input[type="radio"]').exists()).toBe(true)
    expect(wrapper.find('.base-radio-mark').exists()).toBe(true)
  })

  it('renders label text', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        label: 'Option 1',
        modelValue: null
      }
    })

    expect(wrapper.find('.base-radio-text').text()).toBe('Option 1')
  })

  it('renders slot content instead of label prop', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        label: 'Fallback',
        modelValue: null
      },
      slots: {
        default: 'Custom slot content'
      }
    })

    expect(wrapper.find('.base-radio-text').text()).toBe('Custom slot content')
  })

  it('emits update:modelValue with value on change', async () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: null
      }
    })

    await wrapper.find('input').trigger('change')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['option1'])
  })

  it('emits change event with value', async () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: null
      }
    })

    await wrapper.find('input').trigger('change')

    expect(wrapper.emitted('change')).toBeTruthy()
    expect(wrapper.emitted('change')[0]).toEqual(['option1'])
  })

  it('is checked when modelValue matches value', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: 'option1'
      }
    })

    expect(wrapper.find('input').element.checked).toBe(true)
    expect(wrapper.find('.base-radio-label').classes()).toContain('base-radio-label--checked')
  })

  it('is not checked when modelValue does not match value', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: 'option2'
      }
    })

    expect(wrapper.find('input').element.checked).toBe(false)
    expect(wrapper.find('.base-radio-label').classes()).not.toContain('base-radio-label--checked')
  })

  it('disables radio when disabled prop is true', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: null,
        disabled: true
      }
    })

    expect(wrapper.find('input').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.base-radio-label').classes()).toContain('base-radio-label--disabled')
  })

  it('does not emit events when disabled', async () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: null,
        disabled: true
      }
    })

    await wrapper.find('input').trigger('change')

    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
    expect(wrapper.emitted('change')).toBeFalsy()
  })

  it('applies required attribute', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: null,
        required: true
      }
    })

    expect(wrapper.find('input').attributes('required')).toBeDefined()
  })

  it('applies error class when error prop is set', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option1',
        modelValue: null,
        error: 'This option is required'
      }
    })

    expect(wrapper.find('input').classes()).toContain('base-radio-input--error')
  })

  it('works with numeric values', async () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 1,
        modelValue: null
      }
    })

    await wrapper.find('input').trigger('change')

    expect(wrapper.emitted('update:modelValue')[0]).toEqual([1])
  })

  it('works with boolean values', async () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: true,
        modelValue: null
      }
    })

    await wrapper.find('input').trigger('change')

    expect(wrapper.emitted('update:modelValue')[0]).toEqual([true])
  })

  it('has correct name attribute', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'my-radio-group',
        value: 'option1',
        modelValue: null
      }
    })

    expect(wrapper.find('input').attributes('name')).toBe('my-radio-group')
  })

  it('has correct value attribute', () => {
    const wrapper = mount(BaseRadio, {
      props: {
        name: 'test-radio',
        value: 'option-value',
        modelValue: null
      }
    })

    expect(wrapper.find('input').attributes('value')).toBe('option-value')
  })
})
