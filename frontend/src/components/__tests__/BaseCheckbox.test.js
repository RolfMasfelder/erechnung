import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseCheckbox from '../BaseCheckbox.vue'

describe('BaseCheckbox', () => {
  it('renders checkbox input', () => {
    const wrapper = mount(BaseCheckbox)

    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
    expect(wrapper.find('.base-checkbox-checkmark').exists()).toBe(true)
  })

  it('renders label text', () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        label: 'Accept terms'
      }
    })

    expect(wrapper.find('.base-checkbox-text').text()).toBe('Accept terms')
  })

  it('renders slot content instead of label prop', () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        label: 'Fallback'
      },
      slots: {
        default: 'Custom slot content'
      }
    })

    expect(wrapper.find('.base-checkbox-text').text()).toBe('Custom slot content')
  })

  it('emits update:modelValue on change', async () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        modelValue: false
      }
    })

    await wrapper.find('input').setValue(true)

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual([true])
  })

  it('emits change event with checked value', async () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        modelValue: false
      }
    })

    await wrapper.find('input').setValue(true)

    expect(wrapper.emitted('change')).toBeTruthy()
    expect(wrapper.emitted('change')[0]).toEqual([true])
  })

  it('reflects checked state from modelValue', async () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        modelValue: true
      }
    })

    expect(wrapper.find('input').element.checked).toBe(true)

    await wrapper.setProps({ modelValue: false })
    expect(wrapper.find('input').element.checked).toBe(false)
  })

  it('disables checkbox when disabled prop is true', () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        disabled: true
      }
    })

    expect(wrapper.find('input').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.base-checkbox-label').classes()).toContain('base-checkbox-label--disabled')
  })

  it('shows error message when error prop is set', () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        error: 'You must accept the terms'
      }
    })

    expect(wrapper.find('.base-checkbox-error').exists()).toBe(true)
    expect(wrapper.find('.base-checkbox-error').text()).toBe('You must accept the terms')
    expect(wrapper.find('input').classes()).toContain('base-checkbox-input--error')
  })

  it('shows hint when provided and no error', () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        hint: 'This is optional'
      }
    })

    expect(wrapper.find('.base-checkbox-hint').exists()).toBe(true)
    expect(wrapper.find('.base-checkbox-hint').text()).toBe('This is optional')
  })

  it('prioritizes error over hint', () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        error: 'Error message',
        hint: 'Hint message'
      }
    })

    expect(wrapper.find('.base-checkbox-error').exists()).toBe(true)
    expect(wrapper.find('.base-checkbox-hint').exists()).toBe(false)
  })

  it('applies required attribute', () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        required: true
      }
    })

    expect(wrapper.find('input').attributes('required')).toBeDefined()
  })

  it('toggles from false to true', async () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        modelValue: false
      }
    })

    const input = wrapper.find('input')
    input.element.checked = true
    await input.trigger('change')

    expect(wrapper.emitted('update:modelValue')[0]).toEqual([true])
  })

  it('toggles from true to false', async () => {
    const wrapper = mount(BaseCheckbox, {
      props: {
        modelValue: true
      }
    })

    const input = wrapper.find('input')
    input.element.checked = false
    await input.trigger('change')

    expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
  })
})
