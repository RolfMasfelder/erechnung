import apiClient from '../client'
import { userSettingsFields } from '../fieldMappings'

/**
 * User Settings Service.
 *
 * Wraps the /api/user-settings/me/, /api/auth/change-password/ and
 * /api/system/info/ endpoints. All fields crossing the UI ↔ API boundary
 * pass through ../fieldMappings.js (ACL).
 */

export const settingsService = {
  /** Fetch the current user's preferences. */
  async getMe() {
    const response = await apiClient.get('/user-settings/me/')
    return userSettingsFields.fromApi(response.data)
  },

  /** Replace all preference fields. */
  async update(data) {
    const response = await apiClient.put(
      '/user-settings/me/',
      userSettingsFields.toApi(data),
    )
    return userSettingsFields.fromApi(response.data)
  },

  /** Update individual preference fields. */
  async patch(data) {
    const response = await apiClient.patch(
      '/user-settings/me/',
      userSettingsFields.toApi(data),
    )
    return userSettingsFields.fromApi(response.data)
  },

  /** Change the current user's password. */
  async changePassword({ currentPassword, newPassword }) {
    const response = await apiClient.post('/auth/change-password/', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return response.data
  },

  /** Public-ish system info (version, runtime). */
  async getSystemInfo() {
    const response = await apiClient.get('/system/info/')
    return response.data
  },
}
