import { ref, computed } from 'vue'
import { invoiceService } from '@/api/services/invoiceService'

export function useInvoices() {
  const invoices = ref([])
  const currentInvoice = ref(null)
  const isLoading = ref(false)
  const error = ref(null)
  const pagination = ref({
    count: 0,
    page: 1,
    pageSize: 20
  })

  const fetchInvoices = async (params = {}) => {
    isLoading.value = true
    error.value = null

    try {
      const data = await invoiceService.getAll({
        page: pagination.value.page,
        page_size: pagination.value.pageSize,
        ...params
      })

      invoices.value = data.results
      pagination.value.count = data.count

      return data
    } catch (err) {
      error.value = err.response?.data?.message || 'Laden der Rechnungen fehlgeschlagen'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchInvoice = async (id) => {
    isLoading.value = true
    error.value = null

    try {
      const invoice = await invoiceService.getById(id)
      currentInvoice.value = invoice
      return invoice
    } catch (err) {
      error.value = err.response?.data?.message || 'Laden der Rechnung fehlgeschlagen'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const createInvoice = async (data) => {
    isLoading.value = true
    error.value = null

    try {
      const invoice = await invoiceService.create(data)
      invoices.value.unshift(invoice)
      return invoice
    } catch (err) {
      error.value = err.response?.data?.message || 'Erstellen der Rechnung fehlgeschlagen'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const updateInvoice = async (id, data, partial = false) => {
    isLoading.value = true
    error.value = null

    try {
      const invoice = partial
        ? await invoiceService.patch(id, data)
        : await invoiceService.update(id, data)

      const index = invoices.value.findIndex(inv => inv.id === id)
      if (index !== -1) {
        invoices.value[index] = invoice
      }

      if (currentInvoice.value?.id === id) {
        currentInvoice.value = invoice
      }

      return invoice
    } catch (err) {
      error.value = err.response?.data?.message || 'Aktualisieren der Rechnung fehlgeschlagen'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const deleteInvoice = async (id) => {
    isLoading.value = true
    error.value = null

    try {
      await invoiceService.delete(id)
      invoices.value = invoices.value.filter(inv => inv.id !== id)

      if (currentInvoice.value?.id === id) {
        currentInvoice.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.message || 'Löschen der Rechnung fehlgeschlagen'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  const downloadPDF = async (id, filename) => {
    try {
      const blob = await invoiceService.downloadPDF(id)
      downloadBlob(blob, filename || `invoice_${id}.pdf`)
    } catch (err) {
      error.value = err.response?.data?.message || 'Download fehlgeschlagen'
      throw err
    }
  }

  const downloadXML = async (id, filename) => {
    try {
      const blob = await invoiceService.downloadXML(id)
      downloadBlob(blob, filename || `invoice_${id}.xml`)
    } catch (err) {
      error.value = err.response?.data?.message || 'Download fehlgeschlagen'
      throw err
    }
  }

  const downloadHybridPDF = async (id, filename) => {
    try {
      const blob = await invoiceService.downloadHybridPDF(id)
      downloadBlob(blob, filename || `invoice_${id}_hybrid.pdf`)
    } catch (err) {
      error.value = err.response?.data?.message || 'Download fehlgeschlagen'
      throw err
    }
  }

  const nextPage = async () => {
    if (pagination.value.page * pagination.value.pageSize < pagination.value.count) {
      pagination.value.page++
      await fetchInvoices()
    }
  }

  const previousPage = async () => {
    if (pagination.value.page > 1) {
      pagination.value.page--
      await fetchInvoices()
    }
  }

  const goToPage = async (page) => {
    pagination.value.page = page
    await fetchInvoices()
  }

  return {
    invoices: computed(() => invoices.value),
    currentInvoice: computed(() => currentInvoice.value),
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),
    pagination: computed(() => pagination.value),
    fetchInvoices,
    fetchInvoice,
    createInvoice,
    updateInvoice,
    deleteInvoice,
    downloadPDF,
    downloadXML,
    downloadHybridPDF,
    nextPage,
    previousPage,
    goToPage
  }
}
