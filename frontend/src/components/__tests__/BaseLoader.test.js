import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseLoader from '@/components/BaseLoader.vue'

describe('BaseLoader', () => {
  describe('Spinner Mode', () => {
    it('renders spinner by default', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'spinner' }
      })

      expect(wrapper.find('.animate-spin').exists()).toBe(true)
      expect(wrapper.find('[role="status"]').exists()).toBe(true)
    })

    it('renders spinner with different sizes', () => {
      const sizes = ['sm', 'md', 'lg']

      sizes.forEach(size => {
        const wrapper = mount(BaseLoader, {
          props: { type: 'spinner', size }
        })

        const spinner = wrapper.find('.animate-spin')
        expect(spinner.exists()).toBe(true)
      })
    })

    it('renders inline spinner', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'spinner', inline: true }
      })

      expect(wrapper.find('.inline-flex').exists()).toBe(true)
    })

    it('hides when loading is false', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'spinner', loading: false }
      })

      expect(wrapper.find('.animate-spin').exists()).toBe(false)
    })
  })

  describe('Skeleton Mode', () => {
    it('renders skeleton boxes', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'skeleton', rows: 3 }
      })

      const skeletons = wrapper.findAll('.skeleton-box')
      expect(skeletons).toHaveLength(3)
    })

    it('renders correct number of rows', () => {
      const testCases = [1, 5, 10]

      testCases.forEach(rows => {
        const wrapper = mount(BaseLoader, {
          props: { type: 'skeleton', rows }
        })

        const skeletons = wrapper.findAll('.skeleton-box')
        expect(skeletons).toHaveLength(rows)
      })
    })

    it('applies custom row height', () => {
      const customHeight = '5rem'
      const wrapper = mount(BaseLoader, {
        props: { type: 'skeleton', rows: 3, rowHeight: customHeight }
      })

      const skeleton = wrapper.find('.skeleton-box')
      expect(skeleton.attributes('style')).toContain(`height: ${customHeight}`)
    })

    it('uses default row height when not specified', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'skeleton', rows: 3 }
      })

      const skeleton = wrapper.find('.skeleton-box')
      expect(skeleton.attributes('style')).toContain('height: 3rem')
    })

    it('hides skeleton when loading is false', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'skeleton', loading: false }
      })

      expect(wrapper.find('.skeleton-box').exists()).toBe(false)
    })
  })

  describe('Overlay Mode', () => {
    it('renders overlay with spinner', () => {
      const wrapper = mount(BaseLoader, {
        props: { overlay: true }
      })

      expect(wrapper.find('.fixed.inset-0').exists()).toBe(true)
      expect(wrapper.find('.bg-gray-900\\/50').exists()).toBe(true)
      expect(wrapper.find('.animate-spin').exists()).toBe(true)
    })

    it('shows message when provided', () => {
      const message = 'Bitte warten...'
      const wrapper = mount(BaseLoader, {
        props: { overlay: true, message }
      })

      expect(wrapper.text()).toContain(message)
    })

    it('does not show message when not provided', () => {
      const wrapper = mount(BaseLoader, {
        props: { overlay: true }
      })

      expect(wrapper.find('p').exists()).toBe(false)
    })

    it('hides overlay when loading is false', () => {
      const wrapper = mount(BaseLoader, {
        props: { overlay: true, loading: false }
      })

      expect(wrapper.find('.fixed.inset-0').exists()).toBe(false)
    })

    it('uses correct size for overlay spinner', () => {
      const sizes = ['sm', 'md', 'lg']

      sizes.forEach(size => {
        const wrapper = mount(BaseLoader, {
          props: { overlay: true, size }
        })

        expect(wrapper.find('.animate-spin').exists()).toBe(true)
      })
    })
  })

  describe('Props Validation', () => {
    it('validates type prop', () => {
      const { type } = BaseLoader.props
      expect(type.validator('spinner')).toBe(true)
      expect(type.validator('skeleton')).toBe(true)
      expect(type.validator('invalid')).toBe(false)
    })

    it('validates size prop', () => {
      const { size } = BaseLoader.props
      expect(size.validator('sm')).toBe(true)
      expect(size.validator('md')).toBe(true)
      expect(size.validator('lg')).toBe(true)
      expect(size.validator('xl')).toBe(false)
    })

    it('has correct default values', () => {
      const wrapper = mount(BaseLoader)

      expect(wrapper.vm.$props.type).toBe('spinner')
      expect(wrapper.vm.$props.size).toBe('md')
      expect(wrapper.vm.$props.rows).toBe(5)
      expect(wrapper.vm.$props.rowHeight).toBe('3rem')
      expect(wrapper.vm.$props.overlay).toBe(false)
      expect(wrapper.vm.$props.inline).toBe(false)
      expect(wrapper.vm.$props.loading).toBe(true)
    })
  })

  describe('Accessibility', () => {
    it('has correct ARIA attributes for spinner', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'spinner' }
      })

      const spinner = wrapper.find('[role="status"]')
      expect(spinner.exists()).toBe(true)
      expect(spinner.attributes('aria-label')).toBe('Lädt...')
    })

    it('has screen reader text', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'spinner' }
      })

      const srText = wrapper.find('.sr-only')
      expect(srText.exists()).toBe(true)
      expect(srText.text()).toBe('Lädt...')
    })
  })

  describe('Conditional Rendering', () => {
    it('only renders one loader type at a time', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'spinner', overlay: false }
      })

      expect(wrapper.find('.animate-spin').exists()).toBe(true)
      expect(wrapper.find('.skeleton-box').exists()).toBe(false)
      expect(wrapper.find('.fixed.inset-0').exists()).toBe(false)
    })

    it('overlay takes precedence when enabled', () => {
      const wrapper = mount(BaseLoader, {
        props: { type: 'skeleton', overlay: true }
      })

      expect(wrapper.find('.fixed.inset-0').exists()).toBe(true)
      expect(wrapper.find('.skeleton-box').exists()).toBe(false)
    })
  })
})
