import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import InvoiceAttachments from '../InvoiceAttachments.vue'
import { attachmentService } from '@/api/services/attachmentService'
import { useToast } from '@/composables/useToast'

vi.mock('@/api/services/attachmentService', () => ({
  attachmentService: {
    getByInvoice: vi.fn(),
    upload: vi.fn(),
    download: vi.fn(),
    delete: vi.fn()
  }
}))

const mockToast = { success: vi.fn(), error: vi.fn() }
vi.mock('@/composables/useToast', () => ({
  useToast: () => mockToast
}))

const mockAttachments = [
  {
    id: 1,
    description: 'Lieferschein',
    original_filename: 'lieferschein.pdf',
    attachment_type: 'delivery_note',
    mime_type: 'application/pdf',
    uploaded_at: '2024-03-01T10:00:00Z',
    file: '/media/att/lieferschein.pdf'
  },
  {
    id: 2,
    description: 'Beleg',
    original_filename: null,
    attachment_type: 'supporting_document',
    mime_type: 'image/png',
    uploaded_at: '2024-03-02T12:00:00Z',
    file: '/media/att/beleg.png'
  }
]

function mountComponent(isDraft = false) {
  return mount(InvoiceAttachments, {
    props: { invoiceId: 1, isDraft },
    global: {
      stubs: { BaseCard: false, BaseButton: false }
    }
  })
}

describe('InvoiceAttachments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.URL = { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() }
    globalThis.confirm = vi.fn(() => true)
    attachmentService.getByInvoice.mockResolvedValue(mockAttachments)
  })

  describe('loading', () => {
    it('calls getByInvoice on mount', async () => {
      mountComponent()
      await flushPromises()

      expect(attachmentService.getByInvoice).toHaveBeenCalledWith(1)
    })

    it('shows attachment list after loading', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.html()).toContain('lieferschein.pdf')
    })

    it('shows placeholder when no attachments', async () => {
      attachmentService.getByInvoice.mockResolvedValue([])
      const wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.html()).toContain('Keine Anhänge')
    })

    it('handles paginated response (results array)', async () => {
      attachmentService.getByInvoice.mockResolvedValue({ results: mockAttachments })
      const wrapper = mountComponent()
      await flushPromises()

      expect(wrapper.html()).toContain('lieferschein.pdf')
    })
  })

  describe('upload area', () => {
    it('shows upload area when isDraft=true', async () => {
      const wrapper = mountComponent(true)
      await flushPromises()

      expect(wrapper.find('.upload-area').exists()).toBe(true)
    })

    it('hides upload area when isDraft=false', async () => {
      const wrapper = mountComponent(false)
      await flushPromises()

      expect(wrapper.find('.upload-area').exists()).toBe(false)
    })
  })

  describe('file validation and pending uploads', () => {
    it('adds valid file to pending list on file select', async () => {
      const wrapper = mountComponent(true)
      await flushPromises()

      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      const input = wrapper.find('input[type="file"]')
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')

      expect(wrapper.find('.pending-uploads').exists()).toBe(true)
      expect(wrapper.html()).toContain('test.pdf')
    })

    it('shows error for file exceeding 10 MB', async () => {
      const wrapper = mountComponent(true)
      await flushPromises()

      const bigFile = new File([new ArrayBuffer(11 * 1024 * 1024)], 'huge.pdf', { type: 'application/pdf' })
      const input = wrapper.find('input[type="file"]')
      Object.defineProperty(input.element, 'files', { value: [bigFile] })
      await input.trigger('change')

      expect(mockToast.error).toHaveBeenCalledWith(expect.stringContaining('zu groß'))
    })

    it('shows error for disallowed file type', async () => {
      const wrapper = mountComponent(true)
      await flushPromises()

      const file = new File(['content'], 'script.exe', { type: 'application/octet-stream' })
      const input = wrapper.find('input[type="file"]')
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')

      expect(mockToast.error).toHaveBeenCalledWith(expect.stringContaining('nicht erlaubten'))
    })

    it('removes pending file when remove button clicked', async () => {
      const wrapper = mountComponent(true)
      await flushPromises()

      const file = new File(['x'], 'remove-me.pdf', { type: 'application/pdf' })
      const input = wrapper.find('input[type="file"]')
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')

      await wrapper.find('.remove-btn').trigger('click')

      expect(wrapper.find('.pending-uploads').exists()).toBe(false)
    })
  })

  describe('uploadAll', () => {
    it('uploads all pending files and reloads list', async () => {
      attachmentService.upload.mockResolvedValue({ id: 99, description: 'test.pdf' })
      const wrapper = mountComponent(true)
      await flushPromises()

      const file = new File(['x'], 'upload.pdf', { type: 'application/pdf' })
      const input = wrapper.find('input[type="file"]')
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')

      await wrapper.findAll('button').find(b => b.text().includes('Hochladen')).trigger('click')
      await flushPromises()

      expect(attachmentService.upload).toHaveBeenCalledWith(
        1, file, expect.objectContaining({ description: 'upload', attachment_type: 'supporting_document' }), expect.any(Function)
      )
      expect(mockToast.success).toHaveBeenCalled()
    })

    it('shows error toast when upload fails', async () => {
      attachmentService.upload.mockRejectedValue(new Error('Server error'))
      const wrapper = mountComponent(true)
      await flushPromises()

      const file = new File(['x'], 'fail.pdf', { type: 'application/pdf' })
      const input = wrapper.find('input[type="file"]')
      Object.defineProperty(input.element, 'files', { value: [file] })
      await input.trigger('change')

      await wrapper.findAll('button').find(b => b.text().includes('Hochladen')).trigger('click')
      await flushPromises()

      expect(mockToast.error).toHaveBeenCalledWith(expect.stringContaining('fail.pdf'))
    })
  })

  describe('download', () => {
    it('downloads attachment when download button clicked', async () => {
      const blob = new Blob(['pdf'], { type: 'application/pdf' })
      attachmentService.download.mockResolvedValue(blob)
      const appendSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => {})
      const wrapper = mountComponent()
      await flushPromises()

      const dlBtn = wrapper.findAll('.action-btn')[0]
      await dlBtn.trigger('click')
      await flushPromises()

      expect(attachmentService.download).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }))
      appendSpy.mockRestore()
    })

    it('shows error toast when download fails', async () => {
      attachmentService.download.mockRejectedValue(new Error('Download failed'))
      const wrapper = mountComponent()
      await flushPromises()

      await wrapper.findAll('.action-btn')[0].trigger('click')
      await flushPromises()

      expect(mockToast.error).toHaveBeenCalledWith(expect.stringContaining('Herunterladen'))
    })
  })

  describe('delete', () => {
    it('deletes attachment after confirm', async () => {
      attachmentService.delete.mockResolvedValue({})
      const wrapper = mountComponent(true)
      await flushPromises()

      const deleteBtn = wrapper.findAll('.action-btn.danger')[0]
      await deleteBtn.trigger('click')
      await flushPromises()

      expect(attachmentService.delete).toHaveBeenCalledWith(1)
      expect(mockToast.success).toHaveBeenCalledWith('Anhang gelöscht')
    })

    it('does not delete when confirm returns false', async () => {
      globalThis.confirm = vi.fn(() => false)
      const wrapper = mountComponent(true)
      await flushPromises()

      await wrapper.findAll('.action-btn.danger')[0].trigger('click')

      expect(attachmentService.delete).not.toHaveBeenCalled()
    })
  })

  describe('getIcon helper', () => {
    it('shows PDF icon for PDF mime type', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      // First attachment is PDF
      const firstItem = wrapper.findAll('.attachment-icon')[0]
      expect(firstItem.text()).toBe('📕')
    })

    it('shows image icon for image mime type', async () => {
      const wrapper = mountComponent()
      await flushPromises()

      // Second attachment is PNG
      const secondItem = wrapper.findAll('.attachment-icon')[1]
      expect(secondItem.text()).toBe('🖼️')
    })
  })
})
