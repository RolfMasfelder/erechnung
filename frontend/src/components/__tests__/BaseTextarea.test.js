import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseTextarea from '../BaseTextarea.vue'

describe('BaseTextarea', () => {
  it('renders with default props', () => {
    const wrapper = mount(BaseTextarea)

    expect(wrapper.find('textarea').exists()).toBe(true)
    expect(wrapper.find('textarea').attributes('rows')).toBe('4')
  })

  it('renders with label', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        label: 'Description',
        id: 'test-textarea'
      }
    })

    const label = wrapper.find('label')
    expect(label.exists()).toBe(true)
    expect(label.text()).toContain('Description')
    expect(label.attributes('for')).toBe('test-textarea')
  })

  it('shows required indicator when required', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        label: 'Description',
        required: true
      }
    })

    expect(wrapper.find('.required-indicator').exists()).toBe(true)
    expect(wrapper.find('.required-indicator').text()).toBe('*')
  })

  it('emits update:modelValue on input', async () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        modelValue: ''
      }
    })

    const textarea = wrapper.find('textarea')
    await textarea.setValue('New text content')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['New text content'])
  })

  it('displays current modelValue', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        modelValue: 'Initial value'
      }
    })

    expect(wrapper.find('textarea').element.value).toBe('Initial value')
  })

  it('applies custom rows prop', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        rows: 10
      }
    })

    expect(wrapper.find('textarea').attributes('rows')).toBe('10')
  })

  it('shows placeholder text', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        placeholder: 'Enter description'
      }
    })

    expect(wrapper.find('textarea').attributes('placeholder')).toBe('Enter description')
  })

  it('shows error message when error prop is set', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        error: 'This field is required'
      }
    })

    expect(wrapper.find('.base-textarea-error').exists()).toBe(true)
    expect(wrapper.find('.base-textarea-error').text()).toBe('This field is required')
    expect(wrapper.find('textarea').classes()).toContain('base-textarea--error')
  })

  it('shows hint when provided and no error', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        hint: 'Maximum 500 characters'
      }
    })

    expect(wrapper.find('.base-textarea-hint').exists()).toBe(true)
    expect(wrapper.find('.base-textarea-hint').text()).toBe('Maximum 500 characters')
  })

  it('prioritizes error over hint', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        error: 'Error message',
        hint: 'Hint message'
      }
    })

    expect(wrapper.find('.base-textarea-error').exists()).toBe(true)
    expect(wrapper.find('.base-textarea-hint').exists()).toBe(false)
  })

  it('disables textarea when disabled prop is true', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        disabled: true
      }
    })

    const textarea = wrapper.find('textarea')
    expect(textarea.attributes('disabled')).toBeDefined()
    expect(textarea.classes()).toContain('base-textarea--disabled')
  })

  it('emits blur event', async () => {
    const wrapper = mount(BaseTextarea)

    await wrapper.find('textarea').trigger('blur')

    expect(wrapper.emitted('blur')).toBeTruthy()
  })

  it('emits focus event', async () => {
    const wrapper = mount(BaseTextarea)

    await wrapper.find('textarea').trigger('focus')

    expect(wrapper.emitted('focus')).toBeTruthy()
  })

  it('generates unique id when not provided', () => {
    const wrapper1 = mount(BaseTextarea)
    const wrapper2 = mount(BaseTextarea)

    const id1 = wrapper1.find('textarea').attributes('id')
    const id2 = wrapper2.find('textarea').attributes('id')

    expect(id1).toBeTruthy()
    expect(id2).toBeTruthy()
    expect(id1).not.toBe(id2)
  })

  it('uses provided id', () => {
    const wrapper = mount(BaseTextarea, {
      props: {
        id: 'custom-id'
      }
    })

    expect(wrapper.find('textarea').attributes('id')).toBe('custom-id')
  })
})
