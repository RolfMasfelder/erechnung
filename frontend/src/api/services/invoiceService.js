import apiClient from '../client'
import {
  invoiceFields,
  invoiceLineFields,
  allowanceChargeFields,
} from '../fieldMappings'

/**
 * Invoice Service
 * Handles all invoice-related API operations.
 *
 * All data that crosses the UI ↔ API boundary is transformed through
 * the explicit field mappings in ../fieldMappings.js.
 * Components work with UI field names only.
 */
export const invoiceService = {
  /**
   * Liste aller Rechnungen mit optionalen Filtern
   * @param {object} params - Query-Parameter (page, search, ordering, filters)
   * @returns {Promise<{count: number, results: Array}>}
   */
  async getAll(params = {}) {
    const response = await apiClient.get('/invoices/', { params })
    const data = response.data
    if (data.results) {
      data.results = data.results.map(mapInvoiceFromApi)
    }
    return data
  },

  /**
   * Einzelne Rechnung abrufen
   * @param {number} id
   * @returns {Promise<object>}
   */
  async getById(id) {
    const response = await apiClient.get(`/invoices/${id}/`)
    return mapInvoiceFromApi(response.data)
  },

  /**
   * Neue Rechnung erstellen
   * @param {object} data - Invoice-Daten (UI field names)
   * @returns {Promise<object>}
   */
  async create(data) {
    const response = await apiClient.post('/invoices/', invoiceFields.toApi(data))
    return mapInvoiceFromApi(response.data)
  },

  /**
   * Rechnung vollständig aktualisieren (PUT)
   * @param {number} id
   * @param {object} data - Vollständige Invoice-Daten (UI field names)
   * @returns {Promise<object>}
   */
  async update(id, data) {
    const response = await apiClient.put(`/invoices/${id}/`, invoiceFields.toApi(data))
    return mapInvoiceFromApi(response.data)
  },

  /**
   * Rechnung teilweise aktualisieren (PATCH)
   * @param {number} id
   * @param {object} data - Teilweise Invoice-Daten (UI field names)
   * @returns {Promise<object>}
   */
  async patch(id, data) {
    const response = await apiClient.patch(`/invoices/${id}/`, invoiceFields.toApi(data))
    return mapInvoiceFromApi(response.data)
  },

  /**
   * Rechnung löschen
   * @param {number} id
   * @returns {Promise<void>}
   */
  async delete(id) {
    await apiClient.delete(`/invoices/${id}/`)
  },

  /**
   * Neue Rechnungsposition anlegen
   * @param {number} invoiceId
   * @param {object} lineData - UI field names (unit_price_net, vat_rate, …)
   * @returns {Promise<object>}
   */
  async createLine(invoiceId, lineData) {
    const response = await apiClient.post('/invoice-lines/', invoiceLineFields.toApi(lineData))
    return invoiceLineFields.fromApi(response.data)
  },

  /**
   * Rechnungsposition aktualisieren
   * @param {number} lineId
   * @param {object} lineData - UI field names
   * @returns {Promise<object>}
   */
  async updateLine(lineId, lineData) {
    const response = await apiClient.patch(`/invoice-lines/${lineId}/`, invoiceLineFields.toApi(lineData))
    return invoiceLineFields.fromApi(response.data)
  },

  /**
   * Rechnungsposition löschen
   * @param {number} lineId
   * @returns {Promise<void>}
   */
  async deleteLine(lineId) {
    await apiClient.delete(`/invoice-lines/${lineId}/`)
  },

  /**
   * Rechnungsweiten Rabatt/Zuschlag anlegen (EN16931 BG-20/BG-21)
   * @param {object} data - UI field names
   * @returns {Promise<object>}
   */
  async createAllowanceCharge(data) {
    const response = await apiClient.post('/invoice-allowance-charges/', allowanceChargeFields.toApi(data))
    return allowanceChargeFields.fromApi(response.data)
  },

  /**
   * Rechnungsweiten Rabatt/Zuschlag aktualisieren
   * @param {number} id
   * @param {object} data - UI field names
   * @returns {Promise<object>}
   */
  async updateAllowanceCharge(id, data) {
    const response = await apiClient.patch(`/invoice-allowance-charges/${id}/`, allowanceChargeFields.toApi(data))
    return allowanceChargeFields.fromApi(response.data)
  },

  /**
   * Rechnungsweiten Rabatt/Zuschlag löschen
   * @param {number} id
   * @returns {Promise<void>}
   */
  async deleteAllowanceCharge(id) {
    await apiClient.delete(`/invoice-allowance-charges/${id}/`)
  },

  /**
   * PDF/A-3 mit ZUGFeRD-XML generieren
   * @param {number} id
   * @param {string} profile - ZUGFeRD-Profil (BASIC, COMFORT, EXTENDED)
   * @returns {Promise<object>} { status, pdf_url, xml_valid, validation_errors }
   */
  async generatePDF(id, profile = 'COMFORT') {
    const response = await apiClient.post(`/invoices/${id}/generate_pdf/?profile=${profile}`)
    return response.data
  },

  /**
   * PDF-Datei herunterladen
   * @param {number} id
   * @returns {Promise<Blob>}
   */
  async downloadPDF(id) {
    const response = await apiClient.get(`/invoices/${id}/download_pdf/`, {
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * XML-Datei herunterladen (ZUGFeRD/Factur-X)
   * @param {number} id
   * @returns {Promise<Blob>}
   */
  async downloadXML(id) {
    const response = await apiClient.get(`/invoices/${id}/download_xml/`, {
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * Standalone XRechnung XML erzeugen (ohne PDF/A-3)
   * @param {number} id
   * @param {string} [profile='XRECHNUNG']
   * @returns {Promise<object>}
   */
  async generateXml(id, profile = 'XRECHNUNG') {
    const response = await apiClient.post(`/invoices/${id}/generate_xml/?profile=${profile}`)
    return response.data
  },

  /**
   * Hybrides PDF mit eingebettetem XML herunterladen
   * @param {number} id
   * @returns {Promise<Blob>}
   */
  async downloadHybridPDF(id) {
    const response = await apiClient.get(`/invoices/${id}/download_hybrid_pdf/`, {
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * Rechnung validieren (Schematron/XSD)
   * @param {number} id
   * @returns {Promise<object>} Validierungsresultat
   */
  async validate(id) {
    const response = await apiClient.post(`/invoices/${id}/validate/`)
    return response.data
  },

  /**
   * Rechnung als bezahlt markieren
   * @param {number} id
   * @param {object} paymentData - z.B. { payment_date, payment_method }
   * @returns {Promise<object>}
   */
  async markAsPaid(id, paymentData = {}) {
    const response = await apiClient.post(`/invoices/${id}/mark_as_paid/`, paymentData)
    return mapInvoiceFromApi(response.data)
  },

  /**
   * Rechnung stornieren
   * @param {number} id
   * @param {string} reason - Stornierungsgrund
   * @returns {Promise<object>}
   */
  async cancel(id, reason = '') {
    const response = await apiClient.post(`/invoices/${id}/cancel/`, { reason })
    return mapInvoiceFromApi(response.data)
  },

  /**
   * Rechnung per E-Mail versenden.
   *
   * Anhänge: PDF/A-3 (mit eingebetteter ZUGFeRD/Factur-X-XML, EN16931).
   * Optional kann die XML zusätzlich als separates Attachment angehängt werden
   * (`attachXml=true`) — nur für reine XRechnung-Workflows nötig.
   *
   * Der Backend-Endpoint transitioniert DRAFT-Rechnungen automatisch nach SENT.
   *
   * @param {number} id - Invoice-ID
   * @param {object} payload
   * @param {string} payload.recipient - E-Mail-Adresse des Empfängers
   * @param {string} [payload.message]  - Optionale persönliche Nachricht
   * @param {boolean} [payload.attachXml=false] - XML zusätzlich separat anhängen
   * @returns {Promise<{message: string, recipient: string, subject: string,
   *   attached_files: string[], sent_at: string}>}
   * @throws {AxiosError} 400 bei ungültiger Eingabe, 503 wenn deaktiviert/SMTP-Fehler
   */
  async sendEmail(id, { recipient, message = '', attachXml = false }) {
    const response = await apiClient.post(`/invoices/${id}/send_email/`, {
      recipient,
      message,
      attach_xml: attachXml,
    })
    return response.data
  },

  /**
   * XRechnung per E-Mail an einen B2G-Empfänger senden.
   * @param {number} id
   * @param {{ recipient?: string, message?: string }} [data]
   * @returns {Promise<object>}
   * @throws {AxiosError} 400 wenn kein GOVERNMENT-Partner oder keine E-Mail
   */
  async sendXRechnung(id, { recipient = '', message = '' } = {}) {
    const response = await apiClient.post(`/invoices/${id}/send_xrechnung/`, {
      recipient,
      message,
    })
    return response.data
  },

  // ── Concurrent Edit Lock ────────────────────────────────────────────────

  /**
   * Bearbeitungs-Lock anfordern.
   * @param {number} id
   * @returns {Promise<{message: string, editing_since: string}>}
   * @throws {AxiosError} HTTP 423 wenn Lock von anderem User gehalten
   */
  async acquireEditLock(id) {
    const response = await apiClient.post(`/invoices/${id}/acquire_edit_lock/`)
    return response.data
  },

  /**
   * Bearbeitungs-Lock freigeben.
   * @param {number} id
   * @returns {Promise<void>}
   */
  async releaseEditLock(id) {
    await apiClient.post(`/invoices/${id}/release_edit_lock/`)
  },

  /**
   * Heartbeat: Bearbeitungs-Lock verlängern (alle 60 s aufrufen).
   * @param {number} id
   * @returns {Promise<void>}
   */
  async refreshEditLock(id) {
    await apiClient.post(`/invoices/${id}/refresh_edit_lock/`)
  },
}

/**
 * Map a full invoice response (including nested lines and allowance_charges)
 * from API field names back to UI field names.
 */
function mapInvoiceFromApi(apiInvoice) {
  const ui = invoiceFields.fromApi(apiInvoice)
  if (Array.isArray(ui.lines)) {
    ui.lines = ui.lines.map(l => invoiceLineFields.fromApi(l))
  }
  if (Array.isArray(ui.allowance_charges)) {
    ui.allowance_charges = ui.allowance_charges.map(ac => allowanceChargeFields.fromApi(ac))
  }
  return ui
}
