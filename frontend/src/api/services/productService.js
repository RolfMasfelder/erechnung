import apiClient from '../client'
import { productFields } from '../fieldMappings'

/**
 * Product Service
 * Handles product/service catalog management.
 *
 * All data that crosses the UI ↔ API boundary is transformed through
 * the explicit field mappings in ../fieldMappings.js.
 */
export const productService = {
  async getAll(params = {}) {
    const response = await apiClient.get('/products/', { params })
    const data = response.data
    if (data.results) {
      data.results = data.results.map(productFields.fromApi)
    }
    return data
  },

  async getById(id) {
    const response = await apiClient.get(`/products/${id}/`)
    return productFields.fromApi(response.data)
  },

  async create(data) {
    const response = await apiClient.post('/products/', productFields.toApi(data))
    return productFields.fromApi(response.data)
  },

  async update(id, data) {
    const response = await apiClient.put(`/products/${id}/`, productFields.toApi(data))
    return productFields.fromApi(response.data)
  },

  async patch(id, data) {
    const response = await apiClient.patch(`/products/${id}/`, productFields.toApi(data))
    return productFields.fromApi(response.data)
  },

  async getTaxOptions() {
    const response = await apiClient.get('/products/tax-options/')
    return response.data
  },

  async delete(id) {
    await apiClient.delete(`/products/${id}/`)
  }
}
