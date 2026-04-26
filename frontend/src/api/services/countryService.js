import apiClient from '../client'

/**
 * Country Service
 * Read-only reference data: ISO countries with EU VAT rates.
 */
export const countryService = {
  /**
   * Returns paginated (or full) list of countries.
   * Pass { page_size: 300 } to fetch all at once.
   */
  async getAll(params = { page_size: 300 }) {
    const response = await apiClient.get('/countries/', { params })
    // Support paginated (DRF) and plain-array responses
    return Array.isArray(response.data) ? response.data : (response.data.results || [])
  },

  async getByCode(code) {
    const response = await apiClient.get(`/countries/${code}/`)
    return response.data
  },

  /**
   * Returns the historically valid tax rates for a country.
   * Optional: pass on_date=YYYY-MM-DD to filter by date.
   */
  async getTaxRates(code, params = {}) {
    const response = await apiClient.get(`/countries/${code}/tax-rates/`, { params })
    return response.data
  }
}
