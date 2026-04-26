export function isValidEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

export function isValidTaxId(taxId) {
  if (!taxId) return false
  const re = /^\d{10,13}$/
  return re.test(taxId.replace(/[\s-]/g, ''))
}

export function isValidVatId(vatId) {
  if (!vatId) return false
  const re = /^[A-Z]{2}\d{9,12}$/
  return re.test(vatId.replace(/[\s-]/g, ''))
}

export function isValidIBAN(iban) {
  if (!iban) return false

  const normalized = iban.replace(/\s/g, '').toUpperCase()

  if (normalized.length < 15 || normalized.length > 34) {
    return false
  }

  const re = /^[A-Z]{2}\d{2}[A-Z0-9]+$/
  return re.test(normalized)
}

export function isValidBIC(bic) {
  if (!bic) return false

  const normalized = bic.replace(/\s/g, '').toUpperCase()
  const re = /^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/
  return re.test(normalized)
}

export function isValidInvoiceNumber(invoiceNumber) {
  if (!invoiceNumber) return false
  return invoiceNumber.trim().length >= 3
}

export function isValidAmount(amount) {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  return !isNaN(num) && num > 0
}

export function isValidPercentage(percentage) {
  const num = typeof percentage === 'string' ? parseFloat(percentage) : percentage
  return !isNaN(num) && num >= 0 && num <= 100
}
