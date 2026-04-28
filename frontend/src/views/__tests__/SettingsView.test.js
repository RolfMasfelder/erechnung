import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SettingsView from '../SettingsView.vue'
import { settingsService } from '@/api/services/settingsService'

vi.mock('@/api/services/settingsService', () => ({
  settingsService: {
    getMe: vi.fn(),
    patch: vi.fn(),
    update: vi.fn(),
    changePassword: vi.fn(),
    getSystemInfo: vi.fn(),
  },
}))

const mockSettings = {
  username: 'alice',
  email: 'alice@example.com',
  language: 'de',
  timezone: 'Europe/Berlin',
  date_format: '%d.%m.%Y',
  email_notifications: true,
  notify_invoice_paid: true,
  notify_invoice_overdue: false,
  default_currency: 'EUR',
  default_payment_terms_days: 14,
}

describe('SettingsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    settingsService.getMe.mockResolvedValue({ ...mockSettings })
    settingsService.getSystemInfo.mockResolvedValue({
      app_version: '0.1.4',
      django_version: '5.2',
      python_version: '3.13',
      debug: false,
    })
  })

  it('loads user settings on mount', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()
    expect(settingsService.getMe).toHaveBeenCalled()
    expect(wrapper.find('#language').element.value).toBe('de')
  })

  it('renders all four tabs', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs).toHaveLength(4)
    expect(tabs[0].text()).toBe('Profil')
    expect(tabs[1].text()).toContain('Defaults')
    expect(tabs[2].text()).toBe('Passwort')
    expect(tabs[3].text()).toBe('System-Info')
  })

  it('switches to defaults tab and shows currency field', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()
    await wrapper.findAll('[role="tab"]')[1].trigger('click')
    expect(wrapper.find('#default_currency').exists()).toBe(true)
    expect(wrapper.find('#default_currency').element.value).toBe('EUR')
  })

  it('saves profile changes via patch', async () => {
    settingsService.patch.mockResolvedValue({ ...mockSettings, language: 'en' })
    const wrapper = mount(SettingsView)
    await flushPromises()

    await wrapper.find('#language').setValue('en')
    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()

    expect(settingsService.patch).toHaveBeenCalled()
    const payload = settingsService.patch.mock.calls[0][0]
    expect(payload.language).toBe('en')
  })

  it('shows 404 hint when profile is missing', async () => {
    settingsService.getMe.mockRejectedValue({ response: { status: 404 } })
    const wrapper = mount(SettingsView)
    await flushPromises()
    expect(wrapper.text()).toContain('noch kein Profil')
  })

  it('opens password modal from password tab', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()
    await wrapper.findAll('[role="tab"]')[2].trigger('click')
    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()
    // The PasswordChangeModal renders BaseModal with role=dialog
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    expect(wrapper.html()).toContain('Aktuelles Passwort')
  })

  it('loads system info on mount and displays version', async () => {
    const wrapper = mount(SettingsView)
    await flushPromises()
    await wrapper.findAll('[role="tab"]')[3].trigger('click')
    expect(wrapper.text()).toContain('0.1.4')
  })
})
