import apiClient from '../client'

/**
 * Authentication Service
 * Handles login, logout, token refresh, and auth state
 */

/**
 * Dekodiert JWT Token (Base64) ohne Verification
 * @param {string} token
 * @returns {object} Decoded payload
 */
function decodeJWT(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (error) {
    console.error('Failed to decode JWT:', error)
    return null
  }
}

export const authService = {
  /**
   * Login mit Username und Password
   * @param {string} username
   * @param {string} password
   * @returns {Promise<{access: string, refresh: string}>}
   */
  async login(username, password) {
    if (import.meta.env.DEV) {
      console.log('🔐 Login attempt:', { username, endpoint: '/auth/token/' })
    }

    const response = await apiClient.post('/auth/token/', {
      username,
      password
    })

    if (import.meta.env.DEV) {
      console.log('✅ Login successful:', response.data)
    }

    const { access, refresh } = response.data

    // Tokens speichern
    localStorage.setItem('jwt_token', access)
    localStorage.setItem('refresh_token', refresh)

    // User-Daten aus JWT Token extrahieren
    const userData = decodeJWT(access)
    if (userData) {
      if (import.meta.env.DEV) {
        console.log('👤 Decoded user data:', userData)
      }
      localStorage.setItem('current_user', JSON.stringify(userData))
    }

    return response.data
  },

  /**
   * Refresh Access Token
   * @returns {Promise<{access: string}>}
   */
  async refreshToken() {
    const refresh = localStorage.getItem('refresh_token')

    if (!refresh) {
      throw new Error('No refresh token available')
    }

    const response = await apiClient.post('/auth/token/refresh/', { refresh })
    const { access } = response.data

    localStorage.setItem('jwt_token', access)
    return response.data
  },

  /**
   * Logout - Entfernt alle Auth-Daten
   */
  logout() {
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('current_user')
  },

  /**
   * Prüft ob User authentifiziert ist (mit Token-Ablauf-Validierung)
   * @returns {boolean}
   */
  isAuthenticated() {
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      return false
    }

    // Token dekodieren und Ablaufzeit prüfen
    const decoded = decodeJWT(token)
    if (!decoded || !decoded.exp) {
      // Ungültiges Token → entfernen
      this.logout()
      return false
    }

    // Prüfe ob Token abgelaufen ist (exp ist in Sekunden, Date.now() in ms)
    const currentTime = Date.now() / 1000
    if (decoded.exp < currentTime) {
      console.warn('🔒 Token expired, logging out')
      this.logout()
      return false
    }

    return true
  },

  /**
   * Gibt aktuellen User zurück (aus localStorage oder JWT)
   * @returns {object|null}
   */
  getCurrentUser() {
    const userJson = localStorage.getItem('current_user')
    if (userJson) {
      return JSON.parse(userJson)
    }

    // Fallback: Versuche User aus Token zu extrahieren
    const token = localStorage.getItem('jwt_token')
    if (token) {
      const userData = decodeJWT(token)
      if (userData) {
        localStorage.setItem('current_user', JSON.stringify(userData))
        return userData
      }
    }

    return null
  }
}
