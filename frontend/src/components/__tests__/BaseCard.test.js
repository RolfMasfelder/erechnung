import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseCard from '../BaseCard.vue'

describe('BaseCard', () => {
  it('renders default slot content', () => {
    const wrapper = mount(BaseCard, { slots: { default: '<p>Body content</p>' } })
    expect(wrapper.find('.card-body').text()).toContain('Body content')
  })

  it('shows header when title prop set', () => {
    const wrapper = mount(BaseCard, { props: { title: 'My Card' } })
    expect(wrapper.find('.card-header').exists()).toBe(true)
    expect(wrapper.find('.card-title').text()).toBe('My Card')
  })

  it('does not show header when no title and no header slot', () => {
    const wrapper = mount(BaseCard)
    expect(wrapper.find('.card-header').exists()).toBe(false)
  })

  it('shows header when header slot provided', () => {
    const wrapper = mount(BaseCard, { slots: { header: '<span>Custom Header</span>' } })
    expect(wrapper.find('.card-header').exists()).toBe(true)
    expect(wrapper.find('.card-header').text()).toContain('Custom Header')
  })

  it('shows footer when footer slot provided', () => {
    const wrapper = mount(BaseCard, { slots: { footer: '<button>Save</button>' } })
    expect(wrapper.find('.card-footer').exists()).toBe(true)
  })

  it('does not show footer when no footer slot', () => {
    const wrapper = mount(BaseCard)
    expect(wrapper.find('.card-footer').exists()).toBe(false)
  })

  it('applies shadow class by default', () => {
    const wrapper = mount(BaseCard)
    expect(wrapper.find('.card').classes()).toContain('card-shadow')
  })

  it('does not apply shadow class when shadow=false', () => {
    const wrapper = mount(BaseCard, { props: { shadow: false } })
    expect(wrapper.find('.card').classes()).not.toContain('card-shadow')
  })

  it('applies hover class when hover=true', () => {
    const wrapper = mount(BaseCard, { props: { hover: true } })
    expect(wrapper.find('.card').classes()).toContain('card-hover')
  })

  it('does not apply hover class by default', () => {
    const wrapper = mount(BaseCard)
    expect(wrapper.find('.card').classes()).not.toContain('card-hover')
  })

  it('applies correct padding class', () => {
    const wrapper = mount(BaseCard, { props: { padding: 'lg' } })
    expect(wrapper.find('.card').classes()).toContain('card-padding-lg')
  })

  it('uses md padding by default', () => {
    const wrapper = mount(BaseCard)
    expect(wrapper.find('.card').classes()).toContain('card-padding-md')
  })
})
