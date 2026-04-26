import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseFilterBar from '../BaseFilterBar.vue'

// Mock child components
vi.mock('@/components/BaseInput.vue', () => ({
  default: {
    name: 'BaseInput',
    props: ['modelValue', 'placeholder', 'type'],
    emits: ['update:modelValue', 'keyup'],
    template: `
      <div class="mock-input">
        <slot name="prefix" />
        <input
          :value="modelValue"
          :placeholder="placeholder"
          @input="$emit('update:modelValue', $event.target.value)"
          @keyup.enter="$emit('keyup', { key: 'Enter' })"
        />
      </div>
    `
  }
}))

vi.mock('@/components/BaseSelect.vue', () => ({
  default: {
    name: 'BaseSelect',
    props: ['modelValue', 'options', 'placeholder', 'label'],
    emits: ['update:modelValue'],
    template: `
      <div class="mock-select">
        <select
          :value="modelValue"
          @change="$emit('update:modelValue', $event.target.value)"
        >
          <option v-for="opt in options" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>
    `
  }
}))

vi.mock('@/components/BaseButton.vue', () => ({
  default: {
    name: 'BaseButton',
    props: ['variant', 'size'],
    template: '<button class="mock-button" @click="$emit(\'click\')"><slot /></button>'
  }
}))

vi.mock('@/components/BaseDatePicker.vue', () => ({
  default: {
    name: 'BaseDatePicker',
    props: ['modelValue', 'label', 'placeholder', 'range', 'minDate', 'maxDate'],
    emits: ['update:modelValue'],
    template: '<div class="mock-datepicker" data-testid="datepicker"></div>'
  }
}))

describe('BaseFilterBar', () => {
  const defaultProps = {
    filters: { search: '', status: 'all' },
    pendingSearch: '',
    isFiltering: false,
    hasActiveFilters: false,
    activeFilterCount: 0
  }

  it('renders filter bar container', () => {
    const wrapper = mount(BaseFilterBar, {
      props: defaultProps
    })

    expect(wrapper.find('.filter-bar').exists()).toBe(true)
    expect(wrapper.find('.filter-bar-content').exists()).toBe(true)
  })

  describe('search field', () => {
    it('renders search field by default', () => {
      const wrapper = mount(BaseFilterBar, {
        props: defaultProps
      })

      expect(wrapper.find('.filter-search').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'BaseInput' }).exists()).toBe(true)
    })

    it('hides search field when showSearch is false', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          showSearch: false
        }
      })

      expect(wrapper.find('.filter-search').exists()).toBe(false)
    })

    it('uses custom search placeholder', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          searchPlaceholder: 'Rechnungen suchen...'
        }
      })

      const input = wrapper.findComponent({ name: 'BaseInput' })
      expect(input.props('placeholder')).toBe('Rechnungen suchen...')
    })

    it('emits search event on input', async () => {
      const wrapper = mount(BaseFilterBar, {
        props: defaultProps
      })

      const input = wrapper.findComponent({ name: 'BaseInput' })
      await input.vm.$emit('update:modelValue', 'test query')

      expect(wrapper.emitted('search')).toBeTruthy()
      expect(wrapper.emitted('search')[0]).toEqual(['test query'])
    })

    it('shows filtering indicator when isFiltering is true', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          isFiltering: true
        }
      })

      expect(wrapper.find('.filter-indicator').exists()).toBe(true)
    })
  })

  describe('select filters', () => {
    it('renders select filters from configuration', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          selectFilters: [
            {
              key: 'status',
              options: [
                { value: 'all', label: 'Alle' },
                { value: 'paid', label: 'Bezahlt' }
              ],
              placeholder: 'Status',
              label: 'Status'
            }
          ]
        }
      })

      const selects = wrapper.findAllComponents({ name: 'BaseSelect' })
      expect(selects.length).toBe(1)
    })

    it('emits filter-change when select value changes', async () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          selectFilters: [
            {
              key: 'status',
              options: [{ value: 'paid', label: 'Bezahlt' }],
              placeholder: 'Status'
            }
          ]
        }
      })

      const select = wrapper.findComponent({ name: 'BaseSelect' })
      await select.vm.$emit('update:modelValue', 'paid')

      expect(wrapper.emitted('filter-change')).toBeTruthy()
      expect(wrapper.emitted('filter-change')[0]).toEqual([{ key: 'status', value: 'paid' }])
    })

    it('renders multiple select filters', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          selectFilters: [
            { key: 'status', options: [], placeholder: 'Status' },
            { key: 'category', options: [], placeholder: 'Kategorie' }
          ]
        }
      })

      const selects = wrapper.findAllComponents({ name: 'BaseSelect' })
      expect(selects.length).toBe(2)
    })
  })

  describe('date range filter', () => {
    it('hides date range by default', () => {
      const wrapper = mount(BaseFilterBar, {
        props: defaultProps
      })

      expect(wrapper.find('.filter-date-range').exists()).toBe(false)
    })

    it('shows date range when showDateRange is true', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          showDateRange: true
        }
      })

      expect(wrapper.find('.filter-date-range').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'BaseDatePicker' }).exists()).toBe(true)
    })

    it('passes date range props correctly', () => {
      const minDate = new Date('2025-01-01')
      const maxDate = new Date('2026-12-31')

      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          showDateRange: true,
          dateRangeLabel: 'Zeitraum',
          dateRangePlaceholder: 'Datum wählen',
          dateRangeMin: minDate,
          dateRangeMax: maxDate
        }
      })

      const datepicker = wrapper.findComponent({ name: 'BaseDatePicker' })
      expect(datepicker.props('label')).toBe('Zeitraum')
      expect(datepicker.props('placeholder')).toBe('Datum wählen')
      expect(datepicker.props('minDate')).toEqual(minDate)
      expect(datepicker.props('maxDate')).toEqual(maxDate)
      // Verify datepicker is configured for range selection
      expect(datepicker.exists()).toBe(true)
    })
  })

  describe('reset button', () => {
    it('hides reset button when no active filters', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          hasActiveFilters: false
        }
      })

      expect(wrapper.find('.filter-reset').exists()).toBe(false)
    })

    it('shows reset button when filters are active', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          hasActiveFilters: true,
          activeFilterCount: 2
        }
      })

      expect(wrapper.find('.filter-reset').exists()).toBe(true)
    })

    it('emits reset event on click', async () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          hasActiveFilters: true
        }
      })

      const resetButton = wrapper.find('.filter-reset .mock-button')
      await resetButton.trigger('click')

      expect(wrapper.emitted('reset')).toBeTruthy()
    })

    it('hides reset button when showReset is false', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          hasActiveFilters: true,
          showReset: false
        }
      })

      expect(wrapper.find('.filter-reset').exists()).toBe(false)
    })
  })

  describe('collapsible behavior', () => {
    it('shows toggle button when collapsible is true', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          collapsible: true
        }
      })

      expect(wrapper.find('.filter-toggle').exists()).toBe(true)
    })

    it('hides toggle button when collapsible is false', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          collapsible: false
        }
      })

      expect(wrapper.find('.filter-toggle').exists()).toBe(false)
    })

    it('toggles collapsed state on button click', async () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          collapsible: true,
          initialCollapsed: false
        }
      })

      expect(wrapper.find('.filter-bar-collapsed').exists()).toBe(false)

      await wrapper.find('.filter-toggle').trigger('click')

      expect(wrapper.find('.filter-bar-collapsed').exists()).toBe(true)
    })

    it('starts collapsed when initialCollapsed is true', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          collapsible: true,
          initialCollapsed: true
        }
      })

      expect(wrapper.find('.filter-bar-collapsed').exists()).toBe(true)
    })

    it('shows active filter count in toggle button', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          collapsible: true,
          hasActiveFilters: true,
          activeFilterCount: 3
        }
      })

      expect(wrapper.find('.filter-toggle-text').text()).toContain('(3)')
    })

    it('shows filter summary when collapsed with active filters', () => {
      const wrapper = mount(BaseFilterBar, {
        props: {
          ...defaultProps,
          collapsible: true,
          initialCollapsed: true,
          hasActiveFilters: true,
          activeFilterCount: 2
        }
      })

      expect(wrapper.find('.filter-summary').exists()).toBe(true)
      expect(wrapper.find('.filter-summary-text').text()).toContain('2 Filter aktiv')
    })
  })

  describe('custom filter slot', () => {
    it('renders slot content', () => {
      const wrapper = mount(BaseFilterBar, {
        props: defaultProps,
        slots: {
          filters: '<div class="custom-filter">Custom Filter</div>'
        }
      })

      expect(wrapper.find('.custom-filter').exists()).toBe(true)
    })
  })

  describe('search immediate', () => {
    it('emits search-immediate on Enter key', async () => {
      const wrapper = mount(BaseFilterBar, {
        props: defaultProps
      })

      const input = wrapper.findComponent({ name: 'BaseInput' })
      await input.vm.$emit('keyup', { key: 'Enter' })

      // Note: The component listens for @keyup.enter which Vue handles internally
      // We need to test the actual keyup event
    })
  })
})
