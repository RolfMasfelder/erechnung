/**
 * Stats API Service
 * Handles dashboard statistics API calls
 */
import client from '../client'

export const statsService = {
  /**
   * Get dashboard statistics
   * @returns {Promise<Object>} Statistics data
   */
  async getStats() {
    const response = await client.get('/stats/')
    return response.data
  }
}
