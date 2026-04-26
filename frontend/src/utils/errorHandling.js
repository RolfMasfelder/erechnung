export function getErrorMessage(error, defaultMessage = 'Ein Fehler ist aufgetreten') {
  if (!error.response) {
    return 'Netzwerkfehler - bitte Verbindung prüfen'
  }

  const { data, status } = error.response

  switch (status) {
    case 400:
      return formatValidationErrors(data) || 'Ungültige Eingaben'
    case 401:
      return 'Nicht autorisiert - bitte erneut anmelden'
    case 403:
      return 'Zugriff verweigert - keine Berechtigung'
    case 404:
      return 'Ressource nicht gefunden'
    case 409:
      return data.detail || 'Konflikt - Ressource existiert bereits'
    case 500:
      return 'Serverfehler - bitte später erneut versuchen'
    default:
      return data.detail || data.message || defaultMessage
  }
}

function formatValidationErrors(data) {
  if (typeof data === 'string') {
    return data
  }

  if (data.detail) {
    return data.detail
  }

  if (typeof data === 'object') {
    const errors = []
    for (const [field, messages] of Object.entries(data)) {
      const fieldName = field === 'non_field_errors' ? '' : `${field}: `
      const message = Array.isArray(messages) ? messages.join(', ') : messages
      errors.push(`${fieldName}${message}`)
    }
    return errors.join('\n')
  }

  return null
}

export function logError(context, error) {
  console.error(`[${context}]`, error)
  if (error.response) {
    console.error('Response data:', error.response.data)
    console.error('Response status:', error.response.status)
  }
}
