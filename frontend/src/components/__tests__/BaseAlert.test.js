import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseAlert from '../BaseAlert.vue'

describe('BaseAlert', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders when show is true (default)', () => {
    const wrapper = mount(BaseAlert, { props: { message: 'Test' } })
    expect(wrapper.find('.alert').exists()).toBe(true)
  })

  it('renders correct icon for success type', () => {
    const wrapper = mount(BaseAlert, { props: { type: 'success', message: 'OK' } })
    expect(wrapper.find('.alert-icon').text()).toBe('✓')
  })

  it('renders correct icon for warning type', () => {
    const wrapper = mount(BaseAlert, { props: { type: 'warning', message: 'Warn' } })
    expect(wrapper.find('.alert-icon').text()).toBe('⚠')
  })

  it('renders correct icon for error type', () => {
    const wrapper = mount(BaseAlert, { props: { type: 'error', message: 'Err' } })
    expect(wrapper.find('.alert-icon').text()).toBe('✕')
  })

  it('renders correct icon for info type (default)', () => {
    const wrapper = mount(BaseAlert, { props: { message: 'Info' } })
    expect(wrapper.find('.alert-icon').text()).toBe('ℹ')
  })

  it('shows title when provided', () => {
    const wrapper = mount(BaseAlert, { props: { title: 'My Title', message: 'body' } })
    expect(wrapper.find('.alert-title').text()).toBe('My Title')
  })

  it('hides title when not provided', () => {
    const wrapper = mount(BaseAlert, { props: { message: 'body' } })
    expect(wrapper.find('.alert-title').exists()).toBe(false)
  })

  it('shows close button when closable is true (default)', () => {
    const wrapper = mount(BaseAlert, { props: { message: 'x' } })
    expect(wrapper.find('.alert-close').exists()).toBe(true)
  })

  it('hides close button when closable is false', () => {
    const wrapper = mount(BaseAlert, { props: { message: 'x', closable: false } })
    expect(wrapper.find('.alert-close').exists()).toBe(false)
  })

  it('hides alert and emits close on close button click', async () => {
    const wrapper = mount(BaseAlert, { props: { message: 'x' } })
    await wrapper.find('.alert-close').trigger('click')
    expect(wrapper.find('.alert').exists()).toBe(false)
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('applies alert-success class for success type', () => {
    const wrapper = mount(BaseAlert, { props: { type: 'success', message: 'OK' } })
    expect(wrapper.find('.alert').classes()).toContain('alert-success')
  })

  it('applies alert-error class for error type', () => {
    const wrapper = mount(BaseAlert, { props: { type: 'error', message: 'Err' } })
    expect(wrapper.find('.alert').classes()).toContain('alert-error')
  })

  it('auto-dismisses after autoDismiss ms', async () => {
    const wrapper = mount(BaseAlert, { props: { message: 'x', autoDismiss: 3000 } })
    expect(wrapper.find('.alert').exists()).toBe(true)
    vi.advanceTimersByTime(3000)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.alert').exists()).toBe(false)
  })

  it('does not auto-dismiss when autoDismiss is 0', async () => {
    const wrapper = mount(BaseAlert, { props: { message: 'x', autoDismiss: 0 } })
    vi.advanceTimersByTime(10000)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.alert').exists()).toBe(true)
  })

  it('renders slot content', () => {
    const wrapper = mount(BaseAlert, {
      props: { message: 'fallback' },
      slots: { default: '<span class="custom">custom content</span>' }
    })
    expect(wrapper.find('.custom').exists()).toBe(true)
  })
})
