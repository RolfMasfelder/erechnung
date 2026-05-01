import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BasePagination from '../BasePagination.vue'

describe('BasePagination', () => {
  const defaultProps = {
    currentPage: 1,
    totalPages: 5,
    total: 50,
    perPage: 10
  }

  describe('rendering', () => {
    it('renders prev and next buttons', () => {
      const wrapper = mount(BasePagination, { props: defaultProps })
      expect(wrapper.find('.pagination-prev').exists()).toBe(true)
      expect(wrapper.find('.pagination-next').exists()).toBe(true)
    })

    it('disables prev button on first page', () => {
      const wrapper = mount(BasePagination, { props: { ...defaultProps, currentPage: 1 } })
      expect(wrapper.find('.pagination-prev').attributes('disabled')).toBeDefined()
    })

    it('disables next button on last page', () => {
      const wrapper = mount(BasePagination, { props: { ...defaultProps, currentPage: 5 } })
      expect(wrapper.find('.pagination-next').attributes('disabled')).toBeDefined()
    })

    it('marks current page as active', () => {
      const wrapper = mount(BasePagination, { props: { ...defaultProps, currentPage: 3 } })
      const activeBtn = wrapper.find('.pagination-active')
      expect(activeBtn.text()).toBe('3')
    })

    it('shows pagination info by default', () => {
      const wrapper = mount(BasePagination, { props: defaultProps })
      expect(wrapper.find('.pagination-info').text()).toContain('1')
      expect(wrapper.find('.pagination-info').text()).toContain('50')
    })

    it('hides pagination info when showInfo=false', () => {
      const wrapper = mount(BasePagination, { props: { ...defaultProps, showInfo: false } })
      expect(wrapper.find('.pagination-info').exists()).toBe(false)
    })
  })

  describe('page range display', () => {
    it('shows all pages when totalPages <= maxVisiblePages', () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 1, totalPages: 4, total: 40, perPage: 10 }
      })
      const pageButtons = wrapper.findAll('.pagination-page')
      expect(pageButtons).toHaveLength(4)
    })

    it('shows ellipsis when pages exceed maxVisiblePages', () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 5, totalPages: 20, total: 200, perPage: 10 }
      })
      const allText = wrapper.findAll('.pagination-page').map(b => b.text())
      expect(allText).toContain('...')
    })

    it('always shows first page in ellipsis mode', () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 10, totalPages: 20, total: 200, perPage: 10 }
      })
      const allText = wrapper.findAll('.pagination-page').map(b => b.text())
      expect(allText[0]).toBe('1')
    })

    it('always shows last page in ellipsis mode', () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 5, totalPages: 20, total: 200, perPage: 10 }
      })
      const allText = wrapper.findAll('.pagination-page').map(b => b.text())
      expect(allText[allText.length - 1]).toBe('20')
    })
  })

  describe('events', () => {
    it('emits update:currentPage when page button clicked', async () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 1, totalPages: 5, total: 50, perPage: 10 }
      })
      const pageButtons = wrapper.findAll('.pagination-page')
      await pageButtons[1].trigger('click') // page 2

      expect(wrapper.emitted('update:currentPage')).toBeTruthy()
      expect(wrapper.emitted('update:currentPage')[0]).toEqual([2])
    })

    it('emits change event when page changes', async () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 1, totalPages: 5, total: 50, perPage: 10 }
      })
      await wrapper.findAll('.pagination-page')[2].trigger('click') // page 3

      expect(wrapper.emitted('change')).toBeTruthy()
      expect(wrapper.emitted('change')[0]).toEqual([3])
    })

    it('emits update:currentPage when next button clicked', async () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 2, totalPages: 5, total: 50, perPage: 10 }
      })
      await wrapper.find('.pagination-next').trigger('click')

      expect(wrapper.emitted('update:currentPage')[0]).toEqual([3])
    })

    it('emits update:currentPage when prev button clicked', async () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 3, totalPages: 5, total: 50, perPage: 10 }
      })
      await wrapper.find('.pagination-prev').trigger('click')

      expect(wrapper.emitted('update:currentPage')[0]).toEqual([2])
    })

    it('does not emit when clicking current page', async () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 2, totalPages: 5, total: 50, perPage: 10 }
      })
      const pageButtons = wrapper.findAll('.pagination-page')
      await pageButtons[1].trigger('click') // page 2 = current

      expect(wrapper.emitted('update:currentPage')).toBeFalsy()
    })

    it('does not emit when clicking ellipsis', async () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 10, totalPages: 20, total: 200, perPage: 10 }
      })
      const ellipsisBtn = wrapper.findAll('.pagination-page').find(b => b.text() === '...')
      if (ellipsisBtn) {
        await ellipsisBtn.trigger('click')
        expect(wrapper.emitted('update:currentPage')).toBeFalsy()
      }
    })
  })

  describe('pagination info range', () => {
    it('calculates correct range for page 1', () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 1, totalPages: 5, total: 50, perPage: 10 }
      })
      expect(wrapper.find('.pagination-info').text()).toContain('1')
      expect(wrapper.find('.pagination-info').text()).toContain('10')
    })

    it('calculates correct range for last partial page', () => {
      const wrapper = mount(BasePagination, {
        props: { currentPage: 3, totalPages: 3, total: 25, perPage: 10 }
      })
      // Page 3: items 21-25
      expect(wrapper.find('.pagination-info').text()).toContain('21')
      expect(wrapper.find('.pagination-info').text()).toContain('25')
    })
  })
})
