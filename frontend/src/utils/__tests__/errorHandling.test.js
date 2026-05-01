import { describe, it, expect, vi } from 'vitest'
import { getErrorMessage, logError } from '../errorHandling'

describe('errorHandling', () => {
  describe('getErrorMessage', () => {
    it('returns network error when no response', () => {
      const error = {}
      expect(getErrorMessage(error)).toBe('Netzwerkfehler - bitte Verbindung prüfen')
    })

    it('returns 401 message', () => {
      const error = { response: { status: 401, data: {} } }
      expect(getErrorMessage(error)).toBe('Nicht autorisiert - bitte erneut anmelden')
    })

    it('returns 403 message', () => {
      const error = { response: { status: 403, data: {} } }
      expect(getErrorMessage(error)).toBe('Zugriff verweigert - keine Berechtigung')
    })

    it('returns 404 message', () => {
      const error = { response: { status: 404, data: {} } }
      expect(getErrorMessage(error)).toBe('Ressource nicht gefunden')
    })

    it('returns 409 message from data.detail', () => {
      const error = { response: { status: 409, data: { detail: 'Already exists' } } }
      expect(getErrorMessage(error)).toBe('Already exists')
    })

    it('returns fallback 409 message when no data.detail', () => {
      const error = { response: { status: 409, data: {} } }
      expect(getErrorMessage(error)).toBe('Konflikt - Ressource existiert bereits')
    })

    it('returns 500 message', () => {
      const error = { response: { status: 500, data: {} } }
      expect(getErrorMessage(error)).toBe('Serverfehler - bitte später erneut versuchen')
    })

    it('returns default message for unknown status', () => {
      const error = { response: { status: 418, data: {} } }
      expect(getErrorMessage(error)).toBe('Ein Fehler ist aufgetreten')
    })

    it('returns custom default message', () => {
      const error = { response: { status: 418, data: {} } }
      expect(getErrorMessage(error, 'Custom error')).toBe('Custom error')
    })

    it('returns data.detail for unknown status', () => {
      const error = { response: { status: 418, data: { detail: 'Custom detail' } } }
      expect(getErrorMessage(error)).toBe('Custom detail')
    })

    it('returns data.message for unknown status when no detail', () => {
      const error = { response: { status: 418, data: { message: 'Custom message' } } }
      expect(getErrorMessage(error)).toBe('Custom message')
    })

    describe('400 validation errors', () => {
      it('formats string data', () => {
        const error = { response: { status: 400, data: 'Invalid request' } }
        expect(getErrorMessage(error)).toBe('Invalid request')
      })

      it('formats data.detail', () => {
        const error = { response: { status: 400, data: { detail: 'Bad request' } } }
        expect(getErrorMessage(error)).toBe('Bad request')
      })

      it('formats field errors', () => {
        const error = { response: { status: 400, data: { email: ['Invalid email'] } } }
        const result = getErrorMessage(error)
        expect(result).toContain('email')
        expect(result).toContain('Invalid email')
      })

      it('formats non_field_errors without field prefix', () => {
        const error = { response: { status: 400, data: { non_field_errors: ['Bad input'] } } }
        const result = getErrorMessage(error)
        expect(result).toContain('Bad input')
        expect(result).not.toContain('non_field_errors')
      })

      it('returns fallback when data does not match any format', () => {
        const error = { response: { status: 400, data: 42 } }
        expect(getErrorMessage(error)).toBe('Ungültige Eingaben')
      })

      it('formats array messages joined by comma', () => {
        const error = { response: { status: 400, data: { name: ['Too short', 'Required'] } } }
        const result = getErrorMessage(error)
        expect(result).toContain('Too short, Required')
      })

      it('formats non-array message strings', () => {
        const error = { response: { status: 400, data: { name: 'Too short' } } }
        const result = getErrorMessage(error)
        expect(result).toContain('Too short')
      })
    })
  })

  describe('logError', () => {
    it('logs error with context', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      logError('MyContext', new Error('Test error'))
      expect(consoleSpy).toHaveBeenCalledWith('[MyContext]', expect.any(Error))
      consoleSpy.mockRestore()
    })

    it('logs response data when present', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const error = { response: { data: { detail: 'err' }, status: 400 } }
      logError('MyContext', error)
      expect(consoleSpy).toHaveBeenCalledWith('Response data:', error.response.data)
      expect(consoleSpy).toHaveBeenCalledWith('Response status:', 400)
      consoleSpy.mockRestore()
    })

    it('does not log response data when no response', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      logError('MyContext', {})
      expect(consoleSpy).toHaveBeenCalledTimes(1)
      consoleSpy.mockRestore()
    })
  })
})
