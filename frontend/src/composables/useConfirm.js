import { ref } from 'vue'

// Global state for the confirmation dialog
const isOpen = ref(false)
const dialogConfig = ref({
  title: '',
  message: '',
  variant: 'danger',
  confirmText: 'Bestätigen',
  cancelText: 'Abbrechen'
})
let resolvePromise = null

export function useConfirm() {
  const confirm = (message, options = {}) => {
    return new Promise((resolve) => {
      // Configure dialog
      dialogConfig.value = {
        title: options.title || 'Bestätigung erforderlich',
        message,
        variant: options.variant || 'danger',
        confirmText: options.confirmText || 'Bestätigen',
        cancelText: options.cancelText || 'Abbrechen'
      }

      // Store resolve function
      resolvePromise = resolve

      // Open dialog
      isOpen.value = true
    })
  }

  const resetConfig = () => {
    dialogConfig.value = {
      title: '',
      message: '',
      variant: 'danger',
      confirmText: 'Bestätigen',
      cancelText: 'Abbrechen'
    }
  }

  const handleConfirm = () => {
    isOpen.value = false
    if (resolvePromise) {
      resolvePromise(true)
      resolvePromise = null
    }
    resetConfig()
  }

  const handleCancel = () => {
    isOpen.value = false
    if (resolvePromise) {
      resolvePromise(false)
      resolvePromise = null
    }
    resetConfig()
  }

  return {
    // State
    isOpen,
    dialogConfig,

    // Methods
    confirm,
    handleConfirm,
    handleCancel
  }
}
