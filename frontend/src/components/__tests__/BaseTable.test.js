import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseTable from '../BaseTable.vue'

describe('BaseTable', () => {
  const defaultColumns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Name' },
    { key: 'status', label: 'Status' }
  ]

  const defaultData = [
    { id: 1, name: 'Item 1', status: 'active' },
    { id: 2, name: 'Item 2', status: 'inactive' },
    { id: 3, name: 'Item 3', status: 'active' }
  ]

  const createWrapper = (props = {}) => {
    return mount(BaseTable, {
      props: {
        columns: defaultColumns,
        data: defaultData,
        ...props
      }
    })
  }

  describe('basic rendering', () => {
    it('should render table with columns', () => {
      const wrapper = createWrapper()
      const headers = wrapper.findAll('th')
      expect(headers.length).toBe(3)
      expect(headers[0].text()).toBe('ID')
      expect(headers[1].text()).toBe('Name')
    })

    it('should render table with data rows', () => {
      const wrapper = createWrapper()
      const rows = wrapper.findAll('tbody tr')
      expect(rows.length).toBe(3)
    })

    it('should show empty message when no data', () => {
      const wrapper = createWrapper({ data: [] })
      expect(wrapper.text()).toContain('Keine Daten vorhanden')
    })

    it('should show custom empty message', () => {
      const wrapper = createWrapper({ data: [], emptyMessage: 'Keine Einträge' })
      expect(wrapper.text()).toContain('Keine Einträge')
    })

    it('should show loading state', () => {
      const wrapper = createWrapper({ loading: true })
      expect(wrapper.find('.table-loading').exists()).toBe(true)
      expect(wrapper.text()).toContain('Lädt Daten...')
    })
  })

  describe('sorting', () => {
    it('should render sort indicator on sortable columns', () => {
      const sortableColumns = [
        { key: 'id', label: 'ID', sortable: true },
        { key: 'name', label: 'Name', sortable: true }
      ]
      const wrapper = createWrapper({ columns: sortableColumns })
      expect(wrapper.find('.th-sortable').exists()).toBe(true)
    })

    it('should emit sort event when sortable column clicked', async () => {
      const sortableColumns = [
        { key: 'id', label: 'ID', sortable: true }
      ]
      const wrapper = createWrapper({ columns: sortableColumns })
      await wrapper.find('.th-sortable').trigger('click')
      expect(wrapper.emitted('sort')).toBeTruthy()
      expect(wrapper.emitted('sort')[0][0]).toEqual({ key: 'id', order: 'asc' })
    })

    it('should toggle sort order on repeated click', async () => {
      const sortableColumns = [
        { key: 'id', label: 'ID', sortable: true }
      ]
      const wrapper = createWrapper({ columns: sortableColumns })
      await wrapper.find('.th-sortable').trigger('click')
      await wrapper.find('.th-sortable').trigger('click')
      expect(wrapper.emitted('sort')[1][0]).toEqual({ key: 'id', order: 'desc' })
    })
  })

  describe('cell formatting', () => {
    it('should apply formatter function to cell', () => {
      const columns = [
        { key: 'status', label: 'Status', formatter: (val) => val.toUpperCase() }
      ]
      const wrapper = createWrapper({ columns })
      expect(wrapper.text()).toContain('ACTIVE')
    })

    it('should display dash for null/undefined values', () => {
      const data = [{ id: 1, name: null }]
      const columns = [
        { key: 'id', label: 'ID' },
        { key: 'name', label: 'Name' }
      ]
      const wrapper = createWrapper({ columns, data })
      const cells = wrapper.findAll('td')
      expect(cells[1].text()).toBe('-')
    })

    it('should handle nested key paths', () => {
      const data = [{ id: 1, user: { name: 'John' } }]
      const columns = [
        { key: 'user.name', label: 'User Name' }
      ]
      const wrapper = createWrapper({ columns, data })
      expect(wrapper.text()).toContain('John')
    })
  })

  describe('actions', () => {
    it('should render action column when actions provided', () => {
      const actions = [
        { name: 'edit', label: 'Edit', handler: vi.fn() }
      ]
      const wrapper = createWrapper({ actions })
      expect(wrapper.find('.th-actions').exists()).toBe(true)
      expect(wrapper.text()).toContain('Aktionen')
    })

    it('should call action handler when clicked', async () => {
      const handler = vi.fn()
      const actions = [
        { name: 'edit', label: 'Edit', handler }
      ]
      const wrapper = createWrapper({ actions })
      await wrapper.find('.action-btn').trigger('click')
      expect(handler).toHaveBeenCalledWith(defaultData[0])
    })

    it('should render action with correct variant class', () => {
      const actions = [
        { name: 'delete', label: 'Delete', variant: 'danger', handler: vi.fn() }
      ]
      const wrapper = createWrapper({ actions })
      expect(wrapper.find('.action-danger').exists()).toBe(true)
    })
  })

  describe('selection functionality', () => {
    it('should not render checkbox column when selectable is false', () => {
      const wrapper = createWrapper({ selectable: false })
      expect(wrapper.find('.th-checkbox').exists()).toBe(false)
    })

    it('should render checkbox column when selectable is true', () => {
      const wrapper = createWrapper({ selectable: true })
      expect(wrapper.find('.th-checkbox').exists()).toBe(true)
    })

    it('should render checkbox in each row when selectable', () => {
      const wrapper = createWrapper({ selectable: true })
      const rowCheckboxes = wrapper.findAll('.td-checkbox input[type="checkbox"]')
      expect(rowCheckboxes.length).toBe(3)
    })

    it('should render header checkbox when selectable', () => {
      const wrapper = createWrapper({ selectable: true })
      const headerCheckbox = wrapper.find('.th-checkbox input[type="checkbox"]')
      expect(headerCheckbox.exists()).toBe(true)
    })

    it('should mark row as selected when id is in selectedIds', () => {
      const selectedIds = new Set([1, 2])
      const wrapper = createWrapper({ selectable: true, selectedIds })
      const selectedRows = wrapper.findAll('.row-selected')
      expect(selectedRows.length).toBe(2)
    })

    it('should check row checkbox when id is in selectedIds', () => {
      const selectedIds = new Set([1])
      const wrapper = createWrapper({ selectable: true, selectedIds })
      const checkboxes = wrapper.findAll('.td-checkbox input[type="checkbox"]')
      expect(checkboxes[0].element.checked).toBe(true)
      expect(checkboxes[1].element.checked).toBe(false)
    })

    it('should emit select event when row checkbox clicked', async () => {
      const wrapper = createWrapper({ selectable: true })
      const checkbox = wrapper.findAll('.td-checkbox input[type="checkbox"]')[0]
      await checkbox.setValue(true)
      expect(wrapper.emitted('select')).toBeTruthy()
      expect(wrapper.emitted('select')[0][0]).toEqual({ id: 1, selected: true })
    })

    it('should emit select-all event when header checkbox clicked', async () => {
      const wrapper = createWrapper({ selectable: true })
      const headerCheckbox = wrapper.find('.th-checkbox input[type="checkbox"]')
      await headerCheckbox.setValue(true)
      expect(wrapper.emitted('select-all')).toBeTruthy()
      expect(wrapper.emitted('select-all')[0][0]).toEqual({
        ids: [1, 2, 3],
        selected: true
      })
    })

    it('should show header checkbox as checked when all selected', () => {
      const selectedIds = new Set([1, 2, 3])
      const wrapper = createWrapper({ selectable: true, selectedIds })
      const headerCheckbox = wrapper.find('.th-checkbox input[type="checkbox"]')
      expect(headerCheckbox.element.checked).toBe(true)
    })

    it('should show header checkbox as indeterminate when some selected', async () => {
      const selectedIds = new Set([1, 2])
      const wrapper = createWrapper({ selectable: true, selectedIds })
      const headerCheckbox = wrapper.find('.th-checkbox input[type="checkbox"]')
      // Note: indeterminate is not a reactive prop, it's set programmatically
      // We check the computed property is calculating correctly
      expect(wrapper.vm.isIndeterminate).toBe(true)
    })

    it('should have aria-label on row checkboxes', () => {
      const wrapper = createWrapper({ selectable: true })
      const checkbox = wrapper.find('.td-checkbox input[type="checkbox"]')
      expect(checkbox.attributes('aria-label')).toContain('Zeile')
    })

    it('should have aria-label on header checkbox', () => {
      const wrapper = createWrapper({ selectable: true })
      const checkbox = wrapper.find('.th-checkbox input[type="checkbox"]')
      expect(checkbox.attributes('aria-label')).toBe('Alle auswählen')
    })
  })

  describe('row key', () => {
    it('should use id as default row key', () => {
      const wrapper = createWrapper({ selectable: true })
      const selectedIds = new Set([1])
      wrapper.setProps({ selectedIds })
      // Default rowKey is 'id'
      expect(wrapper.props('rowKey')).toBe('id')
    })

    it('should use custom rowKey for selection', () => {
      const data = [
        { uuid: 'a', name: 'Item A' },
        { uuid: 'b', name: 'Item B' }
      ]
      const selectedIds = new Set(['a'])
      const wrapper = createWrapper({
        data,
        rowKey: 'uuid',
        selectable: true,
        selectedIds
      })
      const selectedRows = wrapper.findAll('.row-selected')
      expect(selectedRows.length).toBe(1)
    })
  })

  describe('cell slots', () => {
    it('should render custom cell content via slot', () => {
      const wrapper = mount(BaseTable, {
        props: {
          columns: [{ key: 'status', label: 'Status' }],
          data: [{ status: 'active' }]
        },
        slots: {
          'cell-status': '<span class="custom-status">{{ params.value }}</span>'
        }
      })
      expect(wrapper.find('.custom-status').exists()).toBe(true)
    })
  })

  describe('styling', () => {
    it('should apply row-selected class to selected rows', () => {
      const selectedIds = new Set([2])
      const wrapper = createWrapper({ selectable: true, selectedIds })
      const rows = wrapper.findAll('tbody tr')
      expect(rows[0].classes()).not.toContain('row-selected')
      expect(rows[1].classes()).toContain('row-selected')
    })

    it('should have checkbox column with correct styling class', () => {
      const wrapper = createWrapper({ selectable: true })
      expect(wrapper.find('.th-checkbox').exists()).toBe(true)
      expect(wrapper.find('.td-checkbox').exists()).toBe(true)
    })
  })
})
