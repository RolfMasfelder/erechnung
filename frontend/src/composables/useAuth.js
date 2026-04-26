import { ref, computed } from 'vue'
import { authService } from '@/api/services/authService'

const isAuthenticated = ref(authService.isAuthenticated())
const currentUser = ref(authService.getCurrentUser())
const isLoading = ref(false)
const error = ref(null)

export function useAuth() {
  const login = async (username, password) => {
    isLoading.value = true
    error.value = null

    try {
      await authService.login(username, password)
      isAuthenticated.value = true
      // User data is now automatically extracted from JWT in authService
      currentUser.value = authService.getCurrentUser()

      return { success: true }
    } catch (err) {
      error.value = err.response?.data?.message || 'Login fehlgeschlagen'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const logout = () => {
    authService.logout()
    isAuthenticated.value = false
    currentUser.value = null
    error.value = null
  }

  const refreshToken = async () => {
    try {
      await authService.refreshToken()
      // Update current user from refreshed token
      currentUser.value = authService.getCurrentUser()
      return true
    } catch (err) {
      logout()
      return false
    }
  }

  const hasRole = (role) => {
    return computed(() => currentUser.value?.role === role)
  }

  const hasPermission = (permission) => {
    return computed(() => {
      const permissions = currentUser.value?.permissions || []
      return permissions.includes(permission)
    })
  }

  return {
    isAuthenticated: computed(() => isAuthenticated.value),
    currentUser: computed(() => currentUser.value),
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),
    login,
    logout,
    refreshToken,
    hasRole,
    hasPermission
  }
}
