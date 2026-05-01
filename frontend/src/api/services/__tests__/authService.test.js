import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authService } from '../authService'
import apiClient from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

// In-memory localStorage mock for happy-dom compatibility
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { store = {} }
  }
})()
vi.stubGlobal('localStorage', localStorageMock)

// Helper: create a JWT-like token with arbitrary payload
function toBase64Url(str) {
  return btoa(str).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
}
function makeJWT(payload) {
  const header = toBase64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = toBase64Url(JSON.stringify(payload))
  return `${header}.${body}.signature`
}

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('login', () => {
    it('stores tokens and user data on successful login', async () => {
      const futureExp = Math.floor(Date.now() / 1000) + 3600
      const access = makeJWT({ user_id: 1, username: 'alice', exp: futureExp })
      const refresh = 'refresh_token_value'
      apiClient.post.mockResolvedValue({ data: { access, refresh } })

      const result = await authService.login('alice', 'pass')

      expect(apiClient.post).toHaveBeenCalledWith('/auth/token/', { username: 'alice', password: 'pass' })
      expect(localStorage.getItem('jwt_token')).toBe(access)
      expect(localStorage.getItem('refresh_token')).toBe(refresh)
      expect(localStorage.getItem('current_user')).toBeTruthy()
      expect(result.access).toBe(access)
    })

    it('handles login with invalid (non-decodable) access token', async () => {
      apiClient.post.mockResolvedValue({ data: { access: 'invalid.token', refresh: 'ref' } })

      await authService.login('alice', 'pass')

      // Token stored even if not decodable
      expect(localStorage.getItem('jwt_token')).toBe('invalid.token')
      // current_user may not be set if decode failed
    })

    it('throws on login failure', async () => {
      apiClient.post.mockRejectedValue(new Error('Unauthorized'))

      await expect(authService.login('alice', 'wrongpass')).rejects.toThrow('Unauthorized')
    })
  })

  describe('refreshToken', () => {
    it('refreshes token when refresh token exists', async () => {
      localStorage.setItem('refresh_token', 'existing_refresh')
      const newAccess = makeJWT({ user_id: 1, exp: Math.floor(Date.now() / 1000) + 3600 })
      apiClient.post.mockResolvedValue({ data: { access: newAccess } })

      const result = await authService.refreshToken()

      expect(apiClient.post).toHaveBeenCalledWith('/auth/token/refresh/', { refresh: 'existing_refresh' })
      expect(localStorage.getItem('jwt_token')).toBe(newAccess)
      expect(result.access).toBe(newAccess)
    })

    it('throws when no refresh token available', async () => {
      localStorage.removeItem('refresh_token')

      await expect(authService.refreshToken()).rejects.toThrow('No refresh token available')
      expect(apiClient.post).not.toHaveBeenCalled()
    })
  })

  describe('logout', () => {
    it('removes all auth data from localStorage', () => {
      localStorage.setItem('jwt_token', 'token')
      localStorage.setItem('refresh_token', 'refresh')
      localStorage.setItem('current_user', '{"id":1}')

      authService.logout()

      expect(localStorage.getItem('jwt_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(localStorage.getItem('current_user')).toBeNull()
    })
  })

  describe('isAuthenticated', () => {
    it('returns false when no token exists', () => {
      localStorage.removeItem('jwt_token')

      expect(authService.isAuthenticated()).toBe(false)
    })

    it('returns true when token is valid and not expired', () => {
      const futureExp = Math.floor(Date.now() / 1000) + 3600
      const token = makeJWT({ user_id: 1, exp: futureExp })
      localStorage.setItem('jwt_token', token)

      expect(authService.isAuthenticated()).toBe(true)
    })

    it('returns false and logs out when token is expired', () => {
      const pastExp = Math.floor(Date.now() / 1000) - 1
      const token = makeJWT({ user_id: 1, exp: pastExp })
      localStorage.setItem('jwt_token', token)
      localStorage.setItem('refresh_token', 'ref')

      const result = authService.isAuthenticated()

      expect(result).toBe(false)
      expect(localStorage.getItem('jwt_token')).toBeNull()
    })

    it('returns false and logs out when token has no exp claim', () => {
      const token = makeJWT({ user_id: 1 }) // no exp
      localStorage.setItem('jwt_token', token)

      const result = authService.isAuthenticated()

      expect(result).toBe(false)
      expect(localStorage.getItem('jwt_token')).toBeNull()
    })

    it('returns false when token is not decodable', () => {
      localStorage.setItem('jwt_token', 'not.a.valid.jwt')

      const result = authService.isAuthenticated()

      expect(result).toBe(false)
    })
  })

  describe('getCurrentUser', () => {
    it('returns user from localStorage if present', () => {
      const user = { id: 1, username: 'alice' }
      localStorage.setItem('current_user', JSON.stringify(user))

      const result = authService.getCurrentUser()

      expect(result.id).toBe(1)
      expect(result.username).toBe('alice')
    })

    it('extracts user from token when current_user not stored', () => {
      localStorage.removeItem('current_user')
      const futureExp = Math.floor(Date.now() / 1000) + 3600
      const token = makeJWT({ user_id: 2, username: 'bob', exp: futureExp })
      localStorage.setItem('jwt_token', token)

      const result = authService.getCurrentUser()

      expect(result).not.toBeNull()
      expect(result.user_id).toBe(2)
    })

    it('returns null when no user data and no token', () => {
      localStorage.removeItem('current_user')
      localStorage.removeItem('jwt_token')

      expect(authService.getCurrentUser()).toBeNull()
    })

    it('returns null when token is invalid (decode fails)', () => {
      localStorage.removeItem('current_user')
      localStorage.setItem('jwt_token', 'invalid.token')

      const result = authService.getCurrentUser()

      expect(result).toBeNull()
    })
  })
})
