export function formatCurrency(amount, currency = 'EUR', locale = 'de-DE') {
  if (amount === null || amount === undefined) return ''

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency
  }).format(amount)
}

export function formatNumber(value, decimals = 2, locale = 'de-DE') {
  if (value === null || value === undefined) return ''

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value)
}

export function formatPercentage(value, decimals = 2, locale = 'de-DE') {
  if (value === null || value === undefined) return ''

  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value)
}

export function parseNumber(value) {
  if (!value) return null

  const normalized = value
    .replace(/\./g, '')
    .replace(',', '.')

  const num = parseFloat(normalized)
  return isNaN(num) ? null : num
}
