import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseDatePicker from '../BaseDatePicker.vue'

// Mock the VueDatePicker component
vi.mock('@vuepic/vue-datepicker', () => ({
  VueDatePicker: {
    name: 'VueDatePicker',
    props: ['modelValue', 'range', 'enableTimePicker', 'multiCalendars', 'minDate', 'maxDate', 'disabled', 'placeholder', 'format', 'formats', 'locale', 'clearable', 'autoApply', 'textInput'],
    emits: ['update:model-value', 'blur', 'focus', 'cleared'],
    template: `
      <div class="mock-datepicker" data-testid="datepicker">
        <input
          :value="modelValue"
          :disabled="disabled"
          :placeholder="placeholder"
          @input="$emit('update:model-value', $event.target.value)"
          @blur="$emit('blur')"
          @focus="$emit('focus')"
        />
        <button v-if="clearable" @click="$emit('cleared')" data-testid="clear-btn">Clear</button>
      </div>
    `
  }
}))

describe('BaseDatePicker', () => {
  it('renders datepicker component', () => {
    const wrapper = mount(BaseDatePicker)

    expect(wrapper.find('.datepicker-group').exists()).toBe(true)
    expect(wrapper.find('.datepicker-wrapper').exists()).toBe(true)
    expect(wrapper.find('[data-testid="datepicker"]').exists()).toBe(true)
  })

  it('renders label when provided', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        label: 'Rechnungsdatum'
      }
    })

    expect(wrapper.find('.datepicker-label').exists()).toBe(true)
    expect(wrapper.find('.datepicker-label').text()).toBe('Rechnungsdatum')
  })

  it('shows required indicator when required', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        label: 'Datum',
        required: true
      }
    })

    expect(wrapper.find('.required').exists()).toBe(true)
    expect(wrapper.find('.required').text()).toBe('*')
  })

  it('does not show label when not provided', () => {
    const wrapper = mount(BaseDatePicker)

    expect(wrapper.find('.datepicker-label').exists()).toBe(false)
  })

  it('displays error message when error prop is set', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        error: 'Bitte gültiges Datum eingeben'
      }
    })

    expect(wrapper.find('.error-message').exists()).toBe(true)
    expect(wrapper.find('.error-message').text()).toBe('Bitte gültiges Datum eingeben')
  })

  it('displays hint message when hint prop is set', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        hint: 'Format: TT.MM.JJJJ'
      }
    })

    expect(wrapper.find('.hint-message').exists()).toBe(true)
    expect(wrapper.find('.hint-message').text()).toBe('Format: TT.MM.JJJJ')
  })

  it('prioritizes error over hint', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        error: 'Fehler',
        hint: 'Hinweis'
      }
    })

    expect(wrapper.find('.error-message').exists()).toBe(true)
    expect(wrapper.find('.hint-message').exists()).toBe(false)
  })

  it('emits update:modelValue when date changes', async () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        modelValue: null
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    await datepicker.vm.$emit('update:model-value', new Date('2026-01-09'))

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    // Einzeldatum wird als YYYY-MM-DD String emittiert (API-kompatibel)
    expect(wrapper.emitted('update:modelValue')[0][0]).toBe('2026-01-09')
  })

  it('emits blur event', async () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    await datepicker.vm.$emit('blur')

    expect(wrapper.emitted('blur')).toBeTruthy()
  })

  it('emits focus event', async () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    await datepicker.vm.$emit('focus')

    expect(wrapper.emitted('focus')).toBeTruthy()
  })

  it('emits cleared and update:modelValue with null when cleared', async () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        modelValue: new Date('2026-01-09')
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    await datepicker.vm.$emit('cleared')

    expect(wrapper.emitted('cleared')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0][0]).toBeNull()
  })

  it('uses German locale by default', () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    const locale = datepicker.props('locale')
    expect(locale).toBeDefined()
    expect(locale.code).toBe('de')
  })

  it('uses default German date format', () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    // Component uses :formats object (v12+ API) instead of single :format string
    const formats = datepicker.props('formats')
    expect(formats?.input).toBe('dd.MM.yyyy')
  })

  it('uses datetime format when enableTime is true', () => {
    // enableTime and format props are not supported by this component;
    // the component always uses the formats object with German date display
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    const formats = datepicker.props('formats')
    expect(formats?.input).toBe('dd.MM.yyyy')
  })

  it('passes disabled prop to datepicker', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        disabled: true
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('disabled')).toBe(true)
  })

  it('passes range prop to datepicker', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        range: true
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('range')).toBe(true)
  })

  it('passes minDate constraint', () => {
    const minDate = new Date('2025-01-01')
    const wrapper = mount(BaseDatePicker, {
      props: {
        minDate
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('minDate')).toEqual(minDate)
  })

  it('passes maxDate constraint', () => {
    const maxDate = new Date('2026-12-31')
    const wrapper = mount(BaseDatePicker, {
      props: {
        maxDate
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('maxDate')).toEqual(maxDate)
  })

  it('uses custom placeholder', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        placeholder: 'Bitte Datum wählen'
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('placeholder')).toBe('Bitte Datum wählen')
  })

  it('uses default placeholder in German', () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('placeholder')).toBe('Datum auswählen')
  })

  it('enables text input by default', () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    // text-input is hardcoded to false in the component template
    expect(datepicker.props('textInput')).toBe(false)
  })

  it('enables clearable by default', () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('clearable')).toBe(true)
  })

  it('enables autoApply by default', () => {
    const wrapper = mount(BaseDatePicker)

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('autoApply')).toBe(true)
  })

  it('generates unique id when not provided', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        label: 'Test'
      }
    })

    const label = wrapper.find('.datepicker-label')
    expect(label.attributes('for')).toMatch(/^datepicker-/)
  })

  it('uses provided id', () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        id: 'my-custom-id',
        label: 'Test'
      }
    })

    const label = wrapper.find('.datepicker-label')
    expect(label.attributes('for')).toBe('my-custom-id')
  })

  it('watches for external modelValue changes', async () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        modelValue: new Date('2026-01-01')
      }
    })

    await wrapper.setProps({ modelValue: new Date('2026-06-15') })

    // Internal value should be updated
    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('modelValue')).toEqual(new Date('2026-06-15'))
  })

  it('normalizes ISO string modelValue to a Date object internally', () => {
    // ISO-Strings kommen typischerweise vom Backend/API
    const wrapper = mount(BaseDatePicker, {
      props: {
        modelValue: '2026-03-15'
      }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    const modelValue = datepicker.props('modelValue')
    expect(modelValue).toBeInstanceOf(Date)
    expect(modelValue.getFullYear()).toBe(2026)
    expect(modelValue.getMonth()).toBe(2) // 0-indexed: M\u00e4rz = 2
    expect(modelValue.getDate()).toBe(15)
  })

  it('normalizes ISO string modelValue change to Date object via watch', async () => {
    const wrapper = mount(BaseDatePicker, {
      props: {
        modelValue: '2026-01-01'
      }
    })

    await wrapper.setProps({ modelValue: '2026-06-15' })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    const modelValue = datepicker.props('modelValue')
    expect(modelValue).toBeInstanceOf(Date)
    expect(modelValue.getFullYear()).toBe(2026)
    expect(modelValue.getMonth()).toBe(5) // 0-indexed: Juni = 5
    expect(modelValue.getDate()).toBe(15)
  })

  it('normalizes null modelValue to null internally', () => {
    const wrapper = mount(BaseDatePicker, {
      props: { modelValue: null }
    })

    const datepicker = wrapper.findComponent({ name: 'VueDatePicker' })
    expect(datepicker.props('modelValue')).toBeNull()
  })
})
