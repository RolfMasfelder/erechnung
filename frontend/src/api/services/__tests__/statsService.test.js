import { describe, it, expect, vi } from 'vitest'
import { statsService } from '../statsService'
import client from '../../client'

vi.mock('../../client')

describe('statsService', () => {
  describe('getStats', () => {
    it('should fetch dashboard statistics', async () => {
      const mockStats = {
        invoices: {
          total: 150,
          by_status: {
            draft: 10,
            sent: 25,
            paid: 100,
            cancelled: 5,
            overdue: 10
          },
          total_amount: 125000.50,
          paid_amount: 95000.00,
          outstanding_amount: 30000.50
        },
        customers: {
          total: 45,
          active: 42
        },
        products: {
          total: 80,
          active: 75
        },
        companies: {
          total: 3,
          active: 3
        }
      }

      client.get.mockResolvedValue({ data: mockStats })

      const result = await statsService.getStats()

      // client already has /api as baseURL – relative path is /stats/
      expect(client.get).toHaveBeenCalledWith('/stats/')
      expect(result).toEqual(mockStats)
    })

    it('should handle API errors', async () => {
      const error = new Error('Network error')
      client.get.mockRejectedValue(error)

      await expect(statsService.getStats()).rejects.toThrow('Network error')
    })
  })
})
