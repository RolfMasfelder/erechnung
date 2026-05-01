import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseInput from '../BaseInput.vue'

describe('BaseInput', () => {
  it('renders input element', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('shows label when label prop is set', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', label: 'My Label' } })
    expect(wrapper.find('label').text()).toContain('My Label')
  })

  it('hides label when label prop is empty', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    expect(wrapper.find('label').exists()).toBe(false)
  })

  it('shows required star when required is true', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', label: 'Name', required: true } })
    expect(wrapper.find('.required').exists()).toBe(true)
  })

  it('hides required star when required is false', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', label: 'Name', required: false } })
    expect(wrapper.find('.required').exists()).toBe(false)
  })

  it('shows error message when error is set', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', error: 'Required field' } })
    expect(wrapper.find('.error-message').text()).toBe('Required field')
    expect(wrapper.find('.error-icon').exists()).toBe(true)
  })

  it('hides error message when error is empty', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    expect(wrapper.find('.error-message').exists()).toBe(false)
  })

  it('shows hint when hint is set and no error', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', hint: 'Some hint' } })
    expect(wrapper.find('.hint-message').text()).toBe('Some hint')
  })

  it('hides hint when error is also set', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', hint: 'hint', error: 'err' } })
    expect(wrapper.find('.hint-message').exists()).toBe(false)
  })

  it('uses provided id', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', id: 'my-id', label: 'L' } })
    expect(wrapper.find('input').attributes('id')).toBe('my-id')
    expect(wrapper.find('label').attributes('for')).toBe('my-id')
  })

  it('generates random id when no id provided', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    const id = wrapper.find('input').attributes('id')
    expect(id).toMatch(/^input-/)
  })

  it('emits update:modelValue on input', async () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    await wrapper.find('input').setValue('hello')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
  })

  it('emits blur on blur', async () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    await wrapper.find('input').trigger('blur')
    expect(wrapper.emitted('blur')).toBeTruthy()
  })

  it('emits focus on focus', async () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    await wrapper.find('input').trigger('focus')
    expect(wrapper.emitted('focus')).toBeTruthy()
  })

  it('applies disabled class when disabled', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', disabled: true } })
    expect(wrapper.find('input').classes()).toContain('input-disabled')
  })

  it('applies error class when error is set', () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '', error: 'err' } })
    expect(wrapper.find('input').classes()).toContain('input-error')
  })

  it('applies focused class on focus', async () => {
    const wrapper = mount(BaseInput, { props: { modelValue: '' } })
    await wrapper.find('input').trigger('focus')
    expect(wrapper.find('input').classes()).toContain('input-focused')
  })
})
