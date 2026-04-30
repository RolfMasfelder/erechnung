import axios from 'axios'
import { useToast } from '@/composables/useToast'

/**
 * Axios-basierter API-Client mit JWT-Authentifizierung
 * Framework-agnostisch für spätere Migration zu React oder anderen Frameworks
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000 // 30 Sekunden Timeout
})

// Toast instance für Error-Handling
const { error: showError } = useToast()

/**
 * Request-Interceptor: JWT-Token zu allen Requests hinzufügen
 */
apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('jwt_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Bei FormData Content-Type entfernen, damit Browser/Axios ihn
    // automatisch mit dem korrekten multipart-Boundary setzt
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }

    // Debug-Log (DEV only)
    if (import.meta.env.DEV) {
      console.log('📡 API Request:', {
        method: config.method?.toUpperCase(),
        url: config.url,
        baseURL: config.baseURL,
        fullURL: `${config.baseURL}${config.url}`
      })
    }

    return config
  },
  error => {
    return Promise.reject(error)
  }
)

/**
 * Response-Interceptor: 401 Fehler behandeln (automatischer Logout)
 * + Netzwerkfehler und Server-Errors mit user-freundlichen Meldungen
 */
apiClient.interceptors.response.use(
  response => {
    if (import.meta.env.DEV) {
      console.log('✅ API Response:', response.status, response.config.url)
    }
    return response
  },
  async error => {
    if (import.meta.env.DEV) {
      console.log('❌ API Error:', error.response?.status, error.config?.url, error.message)
    }
    const originalRequest = error.config

    // Netzwerkfehler (kein Response vom Server - Offline, Timeout, DNS, etc.)
    if (!error.response) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        showError('Zeitüberschreitung. Der Server antwortet nicht.')
      } else {
        showError('Netzwerkfehler. Bitte prüfen Sie Ihre Internetverbindung.')
      }
      return Promise.reject(error)
    }

    // Server-Fehler (5xx)
    if (error.response.status >= 500) {
      showError('Serverfehler. Bitte versuchen Sie es später erneut.')
      return Promise.reject(error)
    }

    // Ignoriere 401 bei Login-Requests (damit Error-Handling im LoginView funktioniert)
    if (originalRequest.url?.includes('/auth/token/') && !originalRequest.url?.includes('/refresh')) {
      return Promise.reject(error)
    }

    // Bei 401 Fehler (Unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Versuche Token zu refreshen
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/token/refresh/`,
            { refresh: refreshToken }
          )

          const { access } = response.data
          localStorage.setItem('jwt_token', access)

          // Ursprünglichen Request mit neuem Token wiederholen
          originalRequest.headers.Authorization = `Bearer ${access}`
          return apiClient(originalRequest)
        } catch (refreshError) {
          // Refresh fehlgeschlagen → Logout
          localStorage.removeItem('jwt_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      } else {
        // Kein Refresh-Token → Logout
        localStorage.removeItem('jwt_token')
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
