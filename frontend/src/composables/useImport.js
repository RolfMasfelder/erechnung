import { ref, computed } from 'vue'

/**
 * Composable for importing data from CSV files.
 *
 * @param {Object} options - Configuration options
 * @param {Array<string>} options.requiredFields - Fields that must be present and non-empty
 * @param {Object} options.fieldValidators - Custom validators per field { fieldName: (value) => true | 'error message' }
 * @param {Function} options.onImport - Function to call with valid data for actual import
 * @returns {Object} Import state and methods
 */
export function useImport(options = {}) {
  const {
    requiredFields = [],
    fieldValidators = {},
    onImport = null
  } = options

  // State
  const isImporting = ref(false)
  const isParsing = ref(false)
  const importProgress = ref(0)
  const importError = ref(null)
  const parsedData = ref([])
  const parsedHeaders = ref([])
  const validationErrors = ref([])
  const fileName = ref('')
  const importResults = ref(null)

  // Computed
  const hasParsedData = computed(() => parsedData.value.length > 0)
  const hasErrors = computed(() => validationErrors.value.length > 0)

  const validRows = computed(() => {
    const errorRowIndices = new Set(validationErrors.value.map((e) => e.row))
    return parsedData.value.filter((row) => !errorRowIndices.has(row._rowIndex))
  })

  const invalidRows = computed(() => {
    const errorRowIndices = new Set(validationErrors.value.map((e) => e.row))
    return parsedData.value.filter((row) => errorRowIndices.has(row._rowIndex))
  })

  /**
   * Auto-detect delimiter from first line
   */
  const detectDelimiter = (firstLine) => {
    const delimiters = [';', ',', '\t', '|']
    let maxCount = 0
    let detected = ';'

    for (const delimiter of delimiters) {
      const count = (firstLine.match(new RegExp(delimiter.replace(/[|\\]/g, '\\$&'), 'g')) || []).length
      if (count > maxCount) {
        maxCount = count
        detected = delimiter
      }
    }

    return detected
  }

  /**
   * Parse a single CSV line, handling quoted values
   */
  const parseCSVLine = (line, delimiter) => {
    const values = []
    let current = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i++) {
      const char = line[i]
      const nextChar = line[i + 1]

      if (inQuotes) {
        if (char === '"') {
          if (nextChar === '"') {
            // Escaped quote
            current += '"'
            i++
          } else {
            // End of quoted value
            inQuotes = false
          }
        } else {
          current += char
        }
      } else {
        if (char === '"') {
          inQuotes = true
        } else if (char === delimiter) {
          values.push(current)
          current = ''
        } else {
          current += char
        }
      }
    }

    // Add last value
    values.push(current)

    return values
  }

  /**
   * Parse CSV content string
   */
  const parseCSV = (content, delimiter = null) => {
    const result = {
      headers: [],
      data: [],
      errors: []
    }

    if (!content || content.trim() === '') {
      result.errors.push({
        row: 0,
        message: 'Datei ist leer'
      })
      return result
    }

    // Normalize line endings
    const normalizedContent = content.replaceAll('\r\n', '\n').replaceAll('\r', '\n')

    // Split into lines and filter empty
    const lines = normalizedContent.split('\n').filter((line) => line.trim() !== '')

    if (lines.length === 0) {
      result.errors.push({
        row: 0,
        message: 'Keine Daten gefunden'
      })
      return result
    }

    // Detect or use provided delimiter
    const usedDelimiter = delimiter || detectDelimiter(lines[0])

    // Parse header
    result.headers = parseCSVLine(lines[0], usedDelimiter).map((h) => h.trim())
    const expectedColumns = result.headers.length

    // Parse data rows
    for (let i = 1; i < lines.length; i++) {
      const values = parseCSVLine(lines[i], usedDelimiter)
      const rowIndex = i + 1 // 1-based, accounting for header

      if (values.length !== expectedColumns) {
        result.errors.push({
          row: rowIndex,
          message: `Spaltenanzahl stimmt nicht überein (erwartet: ${expectedColumns}, gefunden: ${values.length})`
        })
      }

      const rowData = { _rowIndex: rowIndex }
      result.headers.forEach((header, idx) => {
        rowData[header] = values[idx] !== undefined ? values[idx] : ''
      })

      result.data.push(rowData)
    }

    return result
  }

  /**
   * Validate parsed data
   */
  const validateData = (data, headers) => {
    const errors = []

    // Check required fields exist in headers
    for (const field of requiredFields) {
      if (!headers.includes(field)) {
        errors.push({
          row: 0,
          field,
          message: `Pflichtfeld "${field}" fehlt in den Spalten`
        })
      }
    }

    // If required fields missing in headers, don't validate rows
    if (errors.length > 0) {
      return errors
    }

    // Validate each row
    for (const row of data) {
      // Check required fields have values
      for (const field of requiredFields) {
        const value = row[field]
        if (value === undefined || value === null || value === '') {
          errors.push({
            row: row._rowIndex,
            field,
            message: `Pflichtfeld "${field}" ist leer`
          })
        }
      }

      // Run custom validators
      for (const [field, validator] of Object.entries(fieldValidators)) {
        const value = row[field]

        // Skip validation for empty optional fields
        if ((value === undefined || value === null || value === '') && !requiredFields.includes(field)) {
          continue
        }

        const result = validator(value, row)
        if (result !== true) {
          errors.push({
            row: row._rowIndex,
            field,
            message: result
          })
        }
      }
    }

    return errors
  }

  /**
   * Parse a file object
   */
  const parseFile = async (file) => {
    isParsing.value = true
    importError.value = null
    validationErrors.value = []
    parsedData.value = []
    parsedHeaders.value = []

    try {
      // Check file type
      const validTypes = ['text/csv', 'application/vnd.ms-excel']
      const hasValidExtension = file.name?.toLowerCase().endsWith('.csv')

      // File must have .csv extension OR valid MIME type (but not text/plain without .csv)
      const isValidFile = hasValidExtension || (
        validTypes.includes(file.type) && file.type !== 'text/plain'
      )

      if (!isValidFile) {
        importError.value = 'Ungültiges Dateiformat. Bitte eine CSV-Datei wählen.'
        return false
      }

      fileName.value = file.name || ''

      // Read file content
      const content = await file.text()

      if (!content || content.trim() === '') {
        importError.value = 'Die Datei ist leer'
        return false
      }

      // Parse CSV
      const result = parseCSV(content)

      if (result.errors.length > 0 && result.data.length === 0) {
        importError.value = result.errors[0].message
        return false
      }

      parsedHeaders.value = result.headers
      parsedData.value = result.data

      // Run validation
      const errors = validateData(result.data, result.headers)
      validationErrors.value = errors

      return true
    } catch (error) {
      importError.value = error.message || 'Fehler beim Lesen der Datei'
      return false
    } finally {
      isParsing.value = false
    }
  }

  /**
   * Execute the actual import
   */
  const executeImport = async (skipErrors = false) => {
    if (!onImport) {
      importError.value = 'Keine Import-Funktion konfiguriert'
      return null
    }

    isImporting.value = true
    importProgress.value = 0
    importError.value = null

    try {
      // Get data to import
      const dataToImport = skipErrors ? validRows.value : parsedData.value

      if (dataToImport.length === 0) {
        importError.value = 'Keine gültigen Daten zum Importieren'
        return null
      }

      // Remove internal _rowIndex before import
      const cleanData = dataToImport.map((row) => {
        const { _rowIndex, ...cleanRow } = row
        return cleanRow
      })

      // Execute import with progress callback
      const progressCallback = (progress) => {
        importProgress.value = progress
      }

      const result = await onImport(cleanData, progressCallback)

      importProgress.value = 100
      importResults.value = result

      return result
    } catch (error) {
      importError.value = error.message || 'Import fehlgeschlagen'
      return null
    } finally {
      isImporting.value = false
    }
  }

  /**
   * Reset all import state
   */
  const resetImport = () => {
    isImporting.value = false
    isParsing.value = false
    importProgress.value = 0
    importError.value = null
    parsedData.value = []
    parsedHeaders.value = []
    validationErrors.value = []
    fileName.value = ''
    importResults.value = null
  }

  return {
    // State
    isImporting,
    isParsing,
    importProgress,
    importError,
    parsedData,
    parsedHeaders,
    validationErrors,
    fileName,
    importResults,

    // Computed
    hasParsedData,
    hasErrors,
    validRows,
    invalidRows,

    // Methods
    parseCSV,
    validateData,
    parseFile,
    executeImport,
    resetImport
  }
}
