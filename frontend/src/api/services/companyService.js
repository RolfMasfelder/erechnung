import apiClient from '../client'
import { companyFields } from '../fieldMappings'

/**
 * Company Service
 * Handles company (issuer) management.
 *
 * All data that crosses the UI ↔ API boundary is transformed through
 * the explicit field mappings in ../fieldMappings.js.
 *
 * FormData payloads (file uploads) are passed through directly because
 * Object.entries() cannot iterate FormData — the modals already build
 * FormData with the correct API field names.
 */

function toPayload(data) {
  return data instanceof FormData ? data : companyFields.toApi(data)
}

export const companyService = {
  async getAll(params = {}) {
    const response = await apiClient.get('/companies/', { params })
    const data = response.data
    if (data.results) {
      data.results = data.results.map(companyFields.fromApi)
    }
    return data
  },

  async getById(id) {
    const response = await apiClient.get(`/companies/${id}/`)
    return companyFields.fromApi(response.data)
  },

  async create(data) {
    const response = await apiClient.post('/companies/', toPayload(data))
    return companyFields.fromApi(response.data)
  },

  async update(id, data) {
    const response = await apiClient.put(`/companies/${id}/`, toPayload(data))
    return companyFields.fromApi(response.data)
  },

  async patch(id, data) {
    const response = await apiClient.patch(`/companies/${id}/`, toPayload(data))
    return companyFields.fromApi(response.data)
  },

  async delete(id) {
    await apiClient.delete(`/companies/${id}/`)
  }
}
