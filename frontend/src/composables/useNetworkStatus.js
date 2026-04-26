import { ref, onMounted, onUnmounted } from 'vue'
import { useToast } from './useToast'

/**
 * Composable für Online/Offline Status-Erkennung
 * Zeigt automatisch Toasts bei Verbindungsänderungen
 *
 * @returns {Object} { isOnline: Ref<boolean> }
 */
export function useNetworkStatus() {
  const isOnline = ref(navigator.onLine)
  const { success, warning } = useToast()

  const handleOnline = () => {
    isOnline.value = true
    success('Verbindung wiederhergestellt')
  }

  const handleOffline = () => {
    isOnline.value = false
    warning('Keine Internetverbindung')
  }

  onMounted(() => {
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
  })

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  })

  return {
    isOnline
  }
}
