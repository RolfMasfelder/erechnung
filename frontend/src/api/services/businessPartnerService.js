import apiClient from '../client'
import { businessPartnerFields } from '../fieldMappings'

/**
 * Re-export mapping functions for backward compatibility.
 * The authoritative field definitions live in ../fieldMappings.js.
 */
export const toApi  = businessPartnerFields.toApi
export const fromApi = businessPartnerFields.fromApi

/**
 * Business Partner Service
 * Handles business partner management (customers and suppliers)
 * Note: Backend uses /business-partners/ endpoint
 */
export const businessPartnerService = {
  async getAll(params = {}) {
    const response = await apiClient.get('/business-partners/', { params })
    const data = response.data
    if (data.results) {
      data.results = data.results.map(fromApi)
    }
    return data
  },

  async getById(id) {
    const response = await apiClient.get(`/business-partners/${id}/`)
    return fromApi(response.data)
  },

  async create(data) {
    const response = await apiClient.post('/business-partners/', toApi(data))
    return fromApi(response.data)
  },

  async update(id, data) {
    const response = await apiClient.put(`/business-partners/${id}/`, toApi(data))
    return fromApi(response.data)
  },

  async patch(id, data) {
    const response = await apiClient.patch(`/business-partners/${id}/`, toApi(data))
    return fromApi(response.data)
  },

  async delete(id) {
    await apiClient.delete(`/business-partners/${id}/`)
  }
}
