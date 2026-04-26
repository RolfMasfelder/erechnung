import { ref } from 'vue'

/**
 * Composable for exporting data to various formats (CSV, JSON).
 *
 * @param {Object} options - Configuration options
 * @param {string} options.filename - Base filename for exports (default: 'export')
 * @param {Function} options.fetchData - Optional function to fetch data when none provided
 * @returns {Object} Export state and methods
 */
export function useExport(options = {}) {
  const { filename = 'export', fetchData = null } = options

  // State
  const isExporting = ref(false)
  const exportProgress = ref(0)
  const exportError = ref(null)

  /**
   * Generate filename with date stamp
   */
  const generateFilename = (extension) => {
    const date = new Date()
    const dateStr = date.toISOString().slice(0, 10).replaceAll('-', '')
    return `${filename}_${dateStr}.${extension}`
  }

  /**
   * Get value from nested object path
   */
  const getNestedValue = (obj, path) => {
    return path.split('.').reduce((current, key) => current?.[key], obj)
  }

  /**
   * Escape CSV value if necessary
   */
  const escapeCSVValue = (value) => {
    if (value === null || value === undefined) {
      return ''
    }

    const stringValue = String(value)

    // Check if escaping is needed (contains semicolon, quotes, or newlines)
    if (
      stringValue.includes(';') ||
      stringValue.includes('"') ||
      stringValue.includes('\n') ||
      stringValue.includes('\r')
    ) {
      // Escape quotes by doubling them
      const escaped = stringValue.replaceAll('"', '""')
      return `"${escaped}"`
    }

    return stringValue
  }

  /**
   * Convert data array to CSV string
   * Uses semicolon as delimiter (German Excel standard)
   */
  const toCSV = (data, columns = null) => {
    if (!data || data.length === 0) {
      return ''
    }

    // Determine columns to export
    const exportColumns = columns || Object.keys(data[0]).map((key) => ({
      key,
      label: key
    }))

    // Build header row
    const headerRow = exportColumns.map((col) => col.label).join(';')

    // Build data rows
    const dataRows = data.map((row) => {
      return exportColumns
        .map((col) => {
          let value = getNestedValue(row, col.key)

          // Apply formatter if provided
          if (col.formatter && typeof col.formatter === 'function') {
            value = col.formatter(value, row)
          }

          return escapeCSVValue(value)
        })
        .join(';')
    })

    return [headerRow, ...dataRows].join('\n')
  }

  /**
   * Trigger file download
   */
  const triggerDownload = (content, mimeType, downloadFilename) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = downloadFilename
    link.style.display = 'none'

    document.body.appendChild(link)
    link.click()
    link.remove()

    URL.revokeObjectURL(url)
  }

  /**
   * Export data as CSV file
   */
  const exportCSV = async (data, columns = null, customFilename = null) => {
    isExporting.value = true
    exportError.value = null
    exportProgress.value = 0

    try {
      let exportData = data

      // Fetch data if not provided and fetchData is configured
      if ((!exportData || exportData.length === 0) && fetchData) {
        exportProgress.value = 20
        exportData = await fetchData()
      }

      if (!exportData || exportData.length === 0) {
        exportError.value = 'Keine Daten zum Exportieren vorhanden'
        return false
      }

      exportProgress.value = 50

      const csvContent = toCSV(exportData, columns)
      const downloadFilename = customFilename || generateFilename('csv')

      exportProgress.value = 80

      triggerDownload(csvContent, 'text/csv;charset=utf-8', downloadFilename)

      exportProgress.value = 100
      return true
    } catch (error) {
      exportError.value = error.message || 'Export fehlgeschlagen'
      return false
    } finally {
      isExporting.value = false
    }
  }

  /**
   * Export data as JSON file
   */
  const exportJSON = async (data, customFilename = null) => {
    isExporting.value = true
    exportError.value = null
    exportProgress.value = 0

    try {
      let exportData = data

      // Fetch data if not provided and fetchData is configured
      if ((!exportData || exportData.length === 0) && fetchData) {
        exportProgress.value = 20
        exportData = await fetchData()
      }

      if (!exportData || exportData.length === 0) {
        exportError.value = 'Keine Daten zum Exportieren vorhanden'
        return false
      }

      exportProgress.value = 50

      const jsonContent = JSON.stringify(exportData, null, 2)
      const downloadFilename = customFilename || generateFilename('json')

      exportProgress.value = 80

      triggerDownload(jsonContent, 'application/json', downloadFilename)

      exportProgress.value = 100
      return true
    } catch (error) {
      exportError.value = error.message || 'Export fehlgeschlagen'
      return false
    } finally {
      isExporting.value = false
    }
  }

  /**
   * Export selected items only
   */
  const exportSelected = async (
    allData,
    selectedIds,
    idKey = 'id',
    columns = null,
    format = 'csv'
  ) => {
    // Convert to Set if array
    const idsSet = selectedIds instanceof Set ? selectedIds : new Set(selectedIds)

    if (idsSet.size === 0) {
      exportError.value = 'Keine Elemente ausgewählt'
      return false
    }

    // Filter data to selected items
    const selectedData = allData.filter((item) => idsSet.has(item[idKey]))

    if (selectedData.length === 0) {
      exportError.value = 'Keine Elemente ausgewählt'
      return false
    }

    // Export in requested format
    if (format === 'json') {
      return exportJSON(selectedData)
    }

    return exportCSV(selectedData, columns)
  }

  /**
   * Reset export state
   */
  const resetExport = () => {
    isExporting.value = false
    exportProgress.value = 0
    exportError.value = null
  }

  return {
    // State
    isExporting,
    exportProgress,
    exportError,

    // Methods
    generateFilename,
    toCSV,
    exportCSV,
    exportJSON,
    exportSelected,
    resetExport
  }
}
