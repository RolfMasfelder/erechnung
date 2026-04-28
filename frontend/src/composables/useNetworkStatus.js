import { ref } from 'vue'
import { useToast } from './useToast'

/**
 * Composable für Online/Offline Status-Erkennung.
 *
 * Singleton-Pattern: Nutzt modul-globale State + Listener, sodass mehrere
 * Komponenten (App.vue, OfflineBanner.vue, …) denselben `isOnline`-Ref
 * teilen und Toasts nur einmal pro Statuswechsel ausgelöst werden.
 *
 * @returns {{ isOnline: import('vue').Ref<boolean> }}
 */
const isOnline = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)
let initialized = false

function initialize() {
  if (initialized || typeof window === 'undefined') return
  initialized = true

  const { success, warning } = useToast()

  window.addEventListener('online', () => {
    isOnline.value = true
    success('Verbindung wiederhergestellt')
  })

  window.addEventListener('offline', () => {
    isOnline.value = false
    warning('Keine Internetverbindung')
  })
}

export function useNetworkStatus() {
  initialize()
  return { isOnline }
}
