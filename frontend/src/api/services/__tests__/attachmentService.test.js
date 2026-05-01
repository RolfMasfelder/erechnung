import { describe, it, expect, beforeEach, vi } from 'vitest'
import { attachmentService } from '../attachmentService'
import apiClient from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

describe('attachmentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getByInvoice', () => {
    it('returns mapped array when response is plain array', async () => {
      const raw = [{ id: 1, invoice: 5, description: 'Test', attachment_type: 'PDF', file: '/files/a.pdf' }]
      apiClient.get.mockResolvedValue({ data: raw })

      const result = await attachmentService.getByInvoice(5)

      expect(apiClient.get).toHaveBeenCalledWith('/invoice-attachments/', {
        params: { invoice: 5, page_size: 1000 }
      })
      expect(Array.isArray(result)).toBe(true)
      expect(result[0].id).toBe(1)
    })

    it('returns mapped results when response is paginated', async () => {
      const data = {
        count: 1,
        results: [{ id: 2, invoice: 5, description: 'Doc', attachment_type: 'XML', file: '/files/b.xml' }]
      }
      apiClient.get.mockResolvedValue({ data })

      const result = await attachmentService.getByInvoice(5)

      expect(result.results).toHaveLength(1)
      expect(result.results[0].id).toBe(2)
    })
  })

  describe('getById', () => {
    it('fetches and maps a single attachment', async () => {
      apiClient.get.mockResolvedValue({
        data: { id: 3, invoice: 1, description: 'Single', attachment_type: 'PDF', file: '/files/c.pdf' }
      })

      const result = await attachmentService.getById(3)

      expect(apiClient.get).toHaveBeenCalledWith('/invoice-attachments/3/')
      expect(result.id).toBe(3)
    })
  })

  describe('upload', () => {
    it('posts FormData and returns mapped attachment', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      apiClient.post.mockResolvedValue({
        data: { id: 10, invoice: 5, description: 'test.pdf', attachment_type: 'PDF', file: '/files/test.pdf' }
      })

      const result = await attachmentService.upload(5, mockFile, { description: 'Meine Datei', attachment_type: 'PDF' })

      expect(apiClient.post).toHaveBeenCalledWith(
        '/invoice-attachments/',
        expect.any(FormData),
        expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
      )
      expect(result.id).toBe(10)
    })

    it('uses file.name as description when metadata is empty', async () => {
      const mockFile = new File(['content'], 'auto.pdf', { type: 'application/pdf' })
      apiClient.post.mockResolvedValue({
        data: { id: 11, invoice: 5, description: 'auto.pdf', attachment_type: null, file: '/files/auto.pdf' }
      })

      await attachmentService.upload(5, mockFile)

      const formDataArg = apiClient.post.mock.calls[0][1]
      expect(formDataArg.get('description')).toBe('auto.pdf')
    })

    it('calls onProgress callback during upload', async () => {
      const mockFile = new File(['x'], 'p.pdf')
      apiClient.post.mockImplementation(async (_url, _data, config) => {
        config.onUploadProgress({ loaded: 50, total: 100 })
        return { data: { id: 12, invoice: 1, description: 'p.pdf', attachment_type: null, file: '/f.pdf' } }
      })

      const onProgress = vi.fn()
      await attachmentService.upload(1, mockFile, {}, onProgress)

      expect(onProgress).toHaveBeenCalledWith(50)
    })
  })

  describe('download', () => {
    it('fetches blob with empty baseURL', async () => {
      const blob = new Blob(['pdf content'], { type: 'application/pdf' })
      apiClient.get.mockResolvedValue({ data: blob })

      const result = await attachmentService.download({ file: '/media/files/test.pdf' })

      expect(apiClient.get).toHaveBeenCalledWith(
        '/media/files/test.pdf',
        { responseType: 'blob', baseURL: '' }
      )
      expect(result).toBe(blob)
    })
  })

  describe('delete', () => {
    it('sends DELETE request for given id', async () => {
      apiClient.delete.mockResolvedValue({})

      await attachmentService.delete(7)

      expect(apiClient.delete).toHaveBeenCalledWith('/invoice-attachments/7/')
    })
  })
})
