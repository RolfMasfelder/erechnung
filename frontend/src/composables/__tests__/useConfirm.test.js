import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useConfirm } from '../useConfirm'

describe('useConfirm', () => {
  beforeEach(() => {
    // Reset state before each test
    const { isOpen } = useConfirm()
    isOpen.value = false
  })

  it('should return reactive state and handlers', () => {
    const { isOpen, dialogConfig, confirm, handleConfirm, handleCancel } = useConfirm()

    expect(isOpen.value).toBe(false)
    expect(dialogConfig.value).toEqual({
      title: '',
      message: '',
      variant: 'danger',
      confirmText: 'Bestätigen',
      cancelText: 'Abbrechen'
    })
    expect(typeof confirm).toBe('function')
    expect(typeof handleConfirm).toBe('function')
    expect(typeof handleCancel).toBe('function')
  })

  it('should open dialog with message when confirm is called', () => {
    const { isOpen, dialogConfig, confirm } = useConfirm()

    confirm('Test message')

    expect(isOpen.value).toBe(true)
    expect(dialogConfig.value.message).toBe('Test message')
  })

  it('should apply custom options when provided', () => {
    const { dialogConfig, confirm } = useConfirm()

    confirm('Test message', {
      title: 'Custom Title',
      variant: 'warning',
      confirmText: 'Yes',
      cancelText: 'No'
    })

    expect(dialogConfig.value.title).toBe('Custom Title')
    expect(dialogConfig.value.variant).toBe('warning')
    expect(dialogConfig.value.confirmText).toBe('Yes')
    expect(dialogConfig.value.cancelText).toBe('No')
  })

  it('should return Promise that resolves to true when confirmed', async () => {
    const { confirm, handleConfirm } = useConfirm()

    const promise = confirm('Test message')
    handleConfirm()

    const result = await promise
    expect(result).toBe(true)
  })

  it('should return Promise that resolves to false when cancelled', async () => {
    const { confirm, handleCancel } = useConfirm()

    const promise = confirm('Test message')
    handleCancel()

    const result = await promise
    expect(result).toBe(false)
  })

  it('should close dialog after confirm', () => {
    const { isOpen, confirm, handleConfirm } = useConfirm()

    confirm('Test message')
    expect(isOpen.value).toBe(true)

    handleConfirm()
    expect(isOpen.value).toBe(false)
  })

  it('should close dialog after cancel', () => {
    const { isOpen, confirm, handleCancel } = useConfirm()

    confirm('Test message')
    expect(isOpen.value).toBe(true)

    handleCancel()
    expect(isOpen.value).toBe(false)
  })

  it('should be singleton across multiple calls', () => {
    const instance1 = useConfirm()
    const instance2 = useConfirm()

    // Both instances should share the same state
    expect(instance1.isOpen).toBe(instance2.isOpen)
    expect(instance1.dialogConfig).toBe(instance2.dialogConfig)
  })

  it('should handle multiple confirm calls sequentially', async () => {
    const { confirm, handleConfirm, handleCancel } = useConfirm()

    const promise1 = confirm('Message 1')
    handleConfirm()
    const result1 = await promise1
    expect(result1).toBe(true)

    const promise2 = confirm('Message 2')
    handleCancel()
    const result2 = await promise2
    expect(result2).toBe(false)
  })

  it('should reset to default config after dialog closes', () => {
    const { dialogConfig, confirm, handleConfirm } = useConfirm()

    confirm('Test', {
      title: 'Custom',
      variant: 'warning',
      confirmText: 'Yes',
      cancelText: 'No'
    })

    handleConfirm()

    // Config should reset to defaults
    expect(dialogConfig.value.title).toBe('')
    expect(dialogConfig.value.variant).toBe('danger')
    expect(dialogConfig.value.confirmText).toBe('Bestätigen')
    expect(dialogConfig.value.cancelText).toBe('Abbrechen')
  })
})
