import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PasswordChangeModal from '../PasswordChangeModal.vue'
import { settingsService } from '@/api/services/settingsService'

vi.mock('@/api/services/settingsService', () => ({
  settingsService: {
    changePassword: vi.fn(),
  },
}))

function fillForm(wrapper, current, next, confirm) {
  return Promise.all([
    wrapper.find('#current_password').setValue(current),
    wrapper.find('#new_password').setValue(next),
    wrapper.find('#confirm_password').setValue(confirm),
  ])
}

describe('PasswordChangeModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all three password fields', () => {
    const wrapper = mount(PasswordChangeModal)
    expect(wrapper.find('#current_password').exists()).toBe(true)
    expect(wrapper.find('#new_password').exists()).toBe(true)
    expect(wrapper.find('#confirm_password').exists()).toBe(true)
  })

  it('shows mismatch error when new and confirm differ', async () => {
    const wrapper = mount(PasswordChangeModal)
    await fillForm(wrapper, 'old-pass', 'new-pass-1234', 'new-pass-XXXX')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.text()).toContain('stimmen nicht überein')
    expect(settingsService.changePassword).not.toHaveBeenCalled()
  })

  it('shows length error when new password is too short', async () => {
    const wrapper = mount(PasswordChangeModal)
    await fillForm(wrapper, 'old-pass', 'short', 'short')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.text()).toContain('mindestens 8 Zeichen')
    expect(settingsService.changePassword).not.toHaveBeenCalled()
  })

  it('calls service and emits changed + close on success', async () => {
    settingsService.changePassword.mockResolvedValue({ detail: 'ok' })
    const wrapper = mount(PasswordChangeModal)

    await fillForm(wrapper, 'old-pass', 'new-pass-1234', 'new-pass-1234')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(settingsService.changePassword).toHaveBeenCalledWith({
      currentPassword: 'old-pass',
      newPassword: 'new-pass-1234',
    })
    expect(wrapper.emitted('changed')).toBeTruthy()
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('shows server error message on failure', async () => {
    settingsService.changePassword.mockRejectedValue({
      response: { data: { detail: 'Aktuelles Passwort falsch.' } },
    })
    const wrapper = mount(PasswordChangeModal)

    await fillForm(wrapper, 'wrong', 'new-pass-1234', 'new-pass-1234')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Aktuelles Passwort falsch.')
    expect(wrapper.emitted('changed')).toBeFalsy()
  })
})
