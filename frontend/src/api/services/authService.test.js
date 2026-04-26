import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authService } from '@/api/services/authService'
import apiClient from '@/api/client'

// Mock apiClient
vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn()
  }
}))

describe('authService', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should login and store tokens', async () => {
      // Create a mock JWT token with user data
      const mockUserData = { id: 1, username: 'testuser', email: 'test@example.com' }
      // Simple mock JWT: header.payload.signature (we only care about payload)
      const mockJWT = 'header.' + btoa(JSON.stringify(mockUserData)) + '.signature'

      const mockResponse = {
        data: {
          access: mockJWT,
          refresh: 'refresh_token_456'
        }
      }

      apiClient.post.mockResolvedValue(mockResponse)

      const result = await authService.login('testuser', 'password123')

      expect(apiClient.post).toHaveBeenCalledWith('/auth/token/', {
        username: 'testuser',
        password: 'password123'
      })
      expect(localStorage.setItem).toHaveBeenCalledWith('jwt_token', mockJWT)
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'refresh_token_456')
      // current_user is decoded from JWT token
      expect(localStorage.setItem).toHaveBeenCalledWith('current_user', JSON.stringify(mockUserData))
      expect(result).toEqual(mockResponse.data)
    })

    it('should handle login error', async () => {
      const mockError = new Error('Login failed')
      mockError.response = { status: 401 }

      apiClient.post.mockRejectedValue(mockError)

      await expect(authService.login('testuser', 'wrongpass')).rejects.toThrow('Login failed')
      expect(localStorage.setItem).not.toHaveBeenCalled()
    })
  })

  describe('refreshToken', () => {
    it('should refresh access token', async () => {
      localStorage.getItem.mockReturnValue('refresh_token_456')

      const mockResponse = {
        data: { access: 'new_access_token_789' }
      }

      apiClient.post.mockResolvedValue(mockResponse)

      const result = await authService.refreshToken()

      expect(apiClient.post).toHaveBeenCalledWith('/auth/token/refresh/', {
        refresh: 'refresh_token_456'
      })
      expect(localStorage.setItem).toHaveBeenCalledWith('jwt_token', 'new_access_token_789')
      expect(result).toEqual(mockResponse.data)
    })

    it('should throw error if no refresh token available', async () => {
      localStorage.getItem.mockReturnValue(null)

      await expect(authService.refreshToken()).rejects.toThrow('No refresh token available')
      expect(apiClient.post).not.toHaveBeenCalled()
    })
  })

  describe('logout', () => {
    it('should clear all auth data', () => {
      authService.logout()

      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt_token')
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
      expect(localStorage.removeItem).toHaveBeenCalledWith('current_user')
    })
  })

  describe('isAuthenticated', () => {
    it('should return true if token exists', () => {
      // Construct a valid (non-expired) mock JWT token
      const payload = JSON.stringify({ user_id: 1, username: 'testuser', exp: Math.floor(Date.now() / 1000) + 3600 })
      const b64payload = btoa(payload)
      const mockToken = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${b64payload}.mock_signature`
      localStorage.getItem.mockReturnValue(mockToken)

      expect(authService.isAuthenticated()).toBe(true)
      expect(localStorage.getItem).toHaveBeenCalledWith('jwt_token')
    })

    it('should return false if no token exists', () => {
      localStorage.getItem.mockReturnValue(null)

      expect(authService.isAuthenticated()).toBe(false)
    })
  })

  describe('getCurrentUser', () => {
    it('should return parsed user object', () => {
      const user = { id: 1, username: 'testuser' }
      localStorage.getItem.mockReturnValue(JSON.stringify(user))

      const result = authService.getCurrentUser()

      expect(result).toEqual(user)
      expect(localStorage.getItem).toHaveBeenCalledWith('current_user')
    })

    it('should return null if no user data', () => {
      localStorage.getItem.mockReturnValue(null)

      expect(authService.getCurrentUser()).toBeNull()
    })
  })
})
