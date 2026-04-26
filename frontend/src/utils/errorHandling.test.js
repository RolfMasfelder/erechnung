import { describe, it, expect } from 'vitest'
import { getErrorMessage } from '@/utils/errorHandling'

describe('errorHandling', () => {
  describe('getErrorMessage', () => {
    it('should return network error message when no response', () => {
      const error = { message: 'Network Error' }

      const result = getErrorMessage(error)

      expect(result).toBe('Netzwerkfehler - bitte Verbindung prüfen')
    })

    it('should handle 400 validation errors', () => {
      const error = {
        response: {
          status: 400,
          data: {
            email: ['This field is required.'],
            password: ['Password too short.']
          }
        }
      }

      const result = getErrorMessage(error)

      expect(result).toContain('email: This field is required.')
      expect(result).toContain('password: Password too short.')
    })

    it('should handle 401 unauthorized', () => {
      const error = {
        response: {
          status: 401,
          data: { detail: 'Invalid credentials' }
        }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('Nicht autorisiert - bitte erneut anmelden')
    })

    it('should handle 403 forbidden', () => {
      const error = {
        response: { status: 403, data: {} }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('Zugriff verweigert - keine Berechtigung')
    })

    it('should handle 404 not found', () => {
      const error = {
        response: { status: 404, data: {} }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('Ressource nicht gefunden')
    })

    it('should handle 409 conflict', () => {
      const error = {
        response: {
          status: 409,
          data: { detail: 'Invoice already exists' }
        }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('Invoice already exists')
    })

    it('should handle 500 server error', () => {
      const error = {
        response: { status: 500, data: {} }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('Serverfehler - bitte später erneut versuchen')
    })

    it('should use default message for unknown errors', () => {
      const error = {
        response: { status: 418, data: {} }
      }

      const result = getErrorMessage(error, 'Custom default')

      expect(result).toBe('Custom default')
    })

    it('should extract detail from response', () => {
      const error = {
        response: {
          status: 418,
          data: { detail: 'I am a teapot' }
        }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('I am a teapot')
    })

    it('should extract message from response', () => {
      const error = {
        response: {
          status: 418,
          data: { message: 'Custom error message' }
        }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('Custom error message')
    })

    it('should handle string error data', () => {
      const error = {
        response: {
          status: 400,
          data: 'Invalid data format'
        }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('Invalid data format')
    })

    it('should handle non_field_errors', () => {
      const error = {
        response: {
          status: 400,
          data: {
            non_field_errors: ['This combination already exists']
          }
        }
      }

      const result = getErrorMessage(error)

      expect(result).toBe('This combination already exists')
    })
  })
})
