import { ref } from 'vue'

const toasts = ref([])
let idCounter = 0

export function useToast() {
  const showToast = (message, variant = 'info', duration = 5000) => {
    const id = ++idCounter
    const toast = { id, message, variant }

    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  const removeToast = (id) => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  const success = (message, duration) => {
    return showToast(message, 'success', duration)
  }

  const error = (message, duration) => {
    return showToast(message, 'danger', duration)
  }

  const info = (message, duration) => {
    return showToast(message, 'info', duration)
  }

  const warning = (message, duration) => {
    return showToast(message, 'warning', duration)
  }

  return {
    toasts,
    showToast,
    removeToast,
    success,
    error,
    info,
    warning
  }
}
