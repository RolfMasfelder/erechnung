import apiClient from '../client'
import { attachmentFields } from '../fieldMappings'

/**
 * Attachment Service
 * Handles file attachments (rechnungsbegründende Dokumente) for invoices.
 * Backend endpoint: /api/invoice-attachments/
 *
 * All data that crosses the UI ↔ API boundary is transformed through
 * the explicit field mappings in ../fieldMappings.js.
 * Note: upload() uses FormData, so field renaming happens on append keys.
 */
export const attachmentService = {
  async getByInvoice(invoiceId) {
    const response = await apiClient.get('/invoice-attachments/', {
      params: { invoice: invoiceId, page_size: 1000 }
    })
    const data = response.data
    if (Array.isArray(data)) {
      return data.map(attachmentFields.fromApi)
    }
    if (data.results) {
      data.results = data.results.map(attachmentFields.fromApi)
    }
    return data
  },

  async getById(id) {
    const response = await apiClient.get(`/invoice-attachments/${id}/`)
    return attachmentFields.fromApi(response.data)
  },

  async upload(invoiceId, file, metadata, onProgress) {
    const meta = metadata || {}
    // Build UI object then convert to API field names
    const uiData = {
      invoice: invoiceId,
      file,
      description: meta.description || file.name,
      attachment_type: meta.attachment_type,
    }
    const apiData = attachmentFields.toApi(uiData)

    const formData = new FormData()
    for (const [key, value] of Object.entries(apiData)) {
      if (value != null) formData.append(key, value)
    }

    const response = await apiClient.post('/invoice-attachments/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress
        ? (e) => onProgress(Math.round((e.loaded * 100) / e.total))
        : undefined
    })
    return attachmentFields.fromApi(response.data)
  },

  async download(attachment) {
    const response = await apiClient.get(attachment.file, {
      responseType: 'blob',
      baseURL: ''
    })
    return response.data
  },

  async delete(id) {
    await apiClient.delete(`/invoice-attachments/${id}/`)
  }
}
