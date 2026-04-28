import { describe, it, expect, beforeEach, vi } from 'vitest'
import { settingsService } from '../settingsService'
import apiClient from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
  },
}))

describe('settingsService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getMe', () => {
    it('fetches current user settings via /user-settings/me/', async () => {
      apiClient.get.mockResolvedValue({
        data: {
          username: 'alice',
          email: 'alice@example.com',
          language: 'de',
          timezone: 'Europe/Berlin',
          date_format: '%d.%m.%Y',
          email_notifications: true,
          notify_invoice_paid: false,
          notify_invoice_overdue: true,
          default_currency: 'EUR',
          default_payment_terms_days: 14,
        },
      })

      const result = await settingsService.getMe()

      expect(apiClient.get).toHaveBeenCalledWith('/user-settings/me/')
      expect(result.username).toBe('alice')
      expect(result.language).toBe('de')
      expect(result.default_payment_terms_days).toBe(14)
    })
  })

  describe('update', () => {
    it('PUTs full settings payload', async () => {
      apiClient.put.mockResolvedValue({ data: { language: 'fr' } })

      await settingsService.update({ language: 'fr' })

      expect(apiClient.put).toHaveBeenCalledWith(
        '/user-settings/me/',
        expect.objectContaining({ language: 'fr' }),
      )
    })
  })

  describe('patch', () => {
    it('PATCHes a single field', async () => {
      apiClient.patch.mockResolvedValue({
        data: { email_notifications: false },
      })

      const result = await settingsService.patch({ email_notifications: false })

      expect(apiClient.patch).toHaveBeenCalledWith(
        '/user-settings/me/',
        expect.objectContaining({ email_notifications: false }),
      )
      expect(result.email_notifications).toBe(false)
    })
  })

  describe('changePassword', () => {
    it('POSTs snake_case credentials', async () => {
      apiClient.post.mockResolvedValue({ data: { detail: 'ok' } })

      await settingsService.changePassword({
        currentPassword: 'old-pass',
        newPassword: 'new-pass-1234',
      })

      expect(apiClient.post).toHaveBeenCalledWith('/auth/change-password/', {
        current_password: 'old-pass',
        new_password: 'new-pass-1234',
      })
    })
  })

  describe('getSystemInfo', () => {
    it('fetches /system/info/', async () => {
      apiClient.get.mockResolvedValue({
        data: { app_version: '0.1.4', django_version: '5.2' },
      })

      const result = await settingsService.getSystemInfo()

      expect(apiClient.get).toHaveBeenCalledWith('/system/info/')
      expect(result.app_version).toBe('0.1.4')
    })
  })
})
