export function formatDate(isoDate, locale = 'de-DE') {
  if (!isoDate) return ''

  const date = new Date(isoDate)
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date)
}

export function formatDateTime(isoDate, locale = 'de-DE') {
  if (!isoDate) return ''

  const date = new Date(isoDate)
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

export function toISODate(date) {
  if (!date) return ''

  const d = date instanceof Date ? date : new Date(date)
  return d.toISOString().split('T')[0]
}
