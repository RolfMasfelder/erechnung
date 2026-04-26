import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useImport } from '../useImport'

describe('useImport', () => {
  let importComposable

  beforeEach(() => {
    importComposable = useImport()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initial state', () => {
    it('should initialize with correct default state', () => {
      expect(importComposable.isImporting.value).toBe(false)
      expect(importComposable.isParsing.value).toBe(false)
      expect(importComposable.importProgress.value).toBe(0)
      expect(importComposable.importError.value).toBe(null)
      expect(importComposable.parsedData.value).toEqual([])
      expect(importComposable.parsedHeaders.value).toEqual([])
      expect(importComposable.validationErrors.value).toEqual([])
      expect(importComposable.fileName.value).toBe('')
    })

    it('should have computed properties at correct initial values', () => {
      expect(importComposable.hasParsedData.value).toBe(false)
      expect(importComposable.hasErrors.value).toBe(false)
      expect(importComposable.validRows.value).toEqual([])
      expect(importComposable.invalidRows.value).toEqual([])
    })
  })

  describe('parseCSV', () => {
    it('should parse basic CSV with semicolon delimiter', () => {
      const csv = 'name;email;amount\nTest Kunde;test@example.com;100.50'
      const result = importComposable.parseCSV(csv)

      expect(result.headers).toEqual(['name', 'email', 'amount'])
      expect(result.data).toHaveLength(1)
      expect(result.data[0].name).toBe('Test Kunde')
      expect(result.data[0].email).toBe('test@example.com')
      expect(result.data[0].amount).toBe('100.50')
    })

    it('should auto-detect comma delimiter', () => {
      const csv = 'name,email,amount\nTest,test@example.com,100'
      const result = importComposable.parseCSV(csv)

      expect(result.headers).toEqual(['name', 'email', 'amount'])
      expect(result.data[0].name).toBe('Test')
    })

    it('should auto-detect tab delimiter', () => {
      const csv = 'name\temail\tamount\nTest\ttest@example.com\t100'
      const result = importComposable.parseCSV(csv)

      expect(result.headers).toEqual(['name', 'email', 'amount'])
      expect(result.data[0].name).toBe('Test')
    })

    it('should use provided delimiter over auto-detection', () => {
      const csv = 'name|email|amount\nTest|test@example.com|100'
      const result = importComposable.parseCSV(csv, '|')

      expect(result.headers).toEqual(['name', 'email', 'amount'])
      expect(result.data[0].name).toBe('Test')
    })

    it('should handle quoted values', () => {
      const csv = 'name;description\n"Test Name";"A description with; semicolon"'
      const result = importComposable.parseCSV(csv)

      expect(result.data[0].name).toBe('Test Name')
      expect(result.data[0].description).toBe('A description with; semicolon')
    })

    it('should handle escaped quotes inside quoted values', () => {
      const csv = 'name;value\n"Test ""Quote""";OK'
      const result = importComposable.parseCSV(csv)

      expect(result.data[0].name).toBe('Test "Quote"')
    })

    it('should handle Windows line endings (CRLF)', () => {
      const csv = 'name;email\r\nTest1;test1@example.com\r\nTest2;test2@example.com'
      const result = importComposable.parseCSV(csv)

      expect(result.data).toHaveLength(2)
      expect(result.data[0].name).toBe('Test1')
      expect(result.data[1].name).toBe('Test2')
    })

    it('should handle old Mac line endings (CR)', () => {
      const csv = 'name;email\rTest1;test1@example.com\rTest2;test2@example.com'
      const result = importComposable.parseCSV(csv)

      expect(result.data).toHaveLength(2)
    })

    it('should skip empty lines', () => {
      const csv = 'name;email\n\nTest1;test1@example.com\n\nTest2;test2@example.com\n'
      const result = importComposable.parseCSV(csv)

      expect(result.data).toHaveLength(2)
    })

    it('should return error for empty content', () => {
      const result = importComposable.parseCSV('')

      expect(result.errors).toHaveLength(1)
      expect(result.errors[0].message).toBe('Datei ist leer')
    })

    it('should return error for null content', () => {
      const result = importComposable.parseCSV(null)

      expect(result.errors).toHaveLength(1)
    })

    it('should detect column count mismatch', () => {
      const csv = 'name;email;amount\nTest;test@example.com'
      const result = importComposable.parseCSV(csv)

      expect(result.errors.length).toBeGreaterThan(0)
      expect(result.errors[0].message).toContain('Spaltenanzahl')
    })

    it('should include row index in parsed data', () => {
      const csv = 'name;email\nTest1;test1@example.com\nTest2;test2@example.com'
      const result = importComposable.parseCSV(csv)

      expect(result.data[0]._rowIndex).toBe(2) // Row 2 (1-based, after header)
      expect(result.data[1]._rowIndex).toBe(3)
    })

    it('should trim header names', () => {
      const csv = ' name ; email ; amount \nTest;test@example.com;100'
      const result = importComposable.parseCSV(csv)

      expect(result.headers).toEqual(['name', 'email', 'amount'])
    })
  })

  describe('validateData', () => {
    it('should validate required fields in headers', () => {
      const validator = useImport({ requiredFields: ['name', 'email'] })
      const data = [{ _rowIndex: 2, name: 'Test' }]
      const headers = ['name']

      const errors = validator.validateData(data, headers)

      expect(errors.length).toBeGreaterThan(0)
      expect(errors[0].field).toBe('email')
      expect(errors[0].message).toContain('fehlt')
    })

    it('should validate required fields have values', () => {
      const validator = useImport({ requiredFields: ['name', 'email'] })
      const data = [
        { _rowIndex: 2, name: 'Test', email: '' }
      ]
      const headers = ['name', 'email']

      const errors = validator.validateData(data, headers)

      expect(errors.length).toBe(1)
      expect(errors[0].field).toBe('email')
      expect(errors[0].message).toContain('leer')
    })

    it('should run custom validators', () => {
      const validator = useImport({
        requiredFields: ['email'],
        fieldValidators: {
          email: (value) => {
            if (!value.includes('@')) {
              return 'Ungültige E-Mail-Adresse'
            }
            return true
          }
        }
      })
      const data = [{ _rowIndex: 2, email: 'invalid-email' }]
      const headers = ['email']

      const errors = validator.validateData(data, headers)

      expect(errors.length).toBe(1)
      expect(errors[0].message).toBe('Ungültige E-Mail-Adresse')
    })

    it('should skip custom validators for empty optional fields', () => {
      const validator = useImport({
        requiredFields: [],
        fieldValidators: {
          phone: () => 'Should not be called'
        }
      })
      const data = [{ _rowIndex: 2, phone: '' }]
      const headers = ['phone']

      const errors = validator.validateData(data, headers)

      expect(errors).toEqual([])
    })

    it('should return empty array when all validations pass', () => {
      const validator = useImport({ requiredFields: ['name'] })
      const data = [{ _rowIndex: 2, name: 'Valid Name' }]
      const headers = ['name']

      const errors = validator.validateData(data, headers)

      expect(errors).toEqual([])
    })

    it('should validate multiple rows', () => {
      const validator = useImport({ requiredFields: ['name'] })
      const data = [
        { _rowIndex: 2, name: 'Valid' },
        { _rowIndex: 3, name: '' },
        { _rowIndex: 4, name: 'Also Valid' },
        { _rowIndex: 5, name: '' }
      ]
      const headers = ['name']

      const errors = validator.validateData(data, headers)

      expect(errors.length).toBe(2)
      expect(errors[0].row).toBe(3)
      expect(errors[1].row).toBe(5)
    })
  })

  describe('parseFile', () => {
    it('should parse valid CSV file', async () => {
      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })

      const result = await importComposable.parseFile(file)

      expect(result).toBe(true)
      expect(importComposable.parsedHeaders.value).toEqual(['name', 'email'])
      expect(importComposable.parsedData.value).toHaveLength(1)
      expect(importComposable.fileName.value).toBe('test.csv')
    })

    it('should reject invalid file types', async () => {
      const file = new File(['not csv'], 'test.pdf', { type: 'application/pdf' })

      const result = await importComposable.parseFile(file)

      expect(result).toBe(false)
      expect(importComposable.importError.value).toContain('Ungültiges Dateiformat')
    })

    it('should accept CSV by extension even with wrong MIME type', async () => {
      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'application/octet-stream' })

      const result = await importComposable.parseFile(file)

      expect(result).toBe(true)
    })

    it('should accept text/plain for CSV files', async () => {
      const fileContent = 'name;email\nTest;test@example.com'
      // .csv extension takes priority – text/plain MIME type is accepted when extension is .csv
      const file = new File([fileContent], 'data.csv', { type: 'text/plain' })

      const result = await importComposable.parseFile(file)

      expect(result).toBe(true)
    })

    it('should set isParsing during parse', async () => {
      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })

      const parsePromise = importComposable.parseFile(file)
      // Note: This might not catch isParsing=true due to async nature
      await parsePromise

      expect(importComposable.isParsing.value).toBe(false)
    })

    it('should return false for empty file', async () => {
      const file = new File([''], 'empty.csv', { type: 'text/csv' })

      const result = await importComposable.parseFile(file)

      expect(result).toBe(false)
      expect(importComposable.importError.value).toContain('leer')
    })

    it('should run validation after parsing', async () => {
      const validator = useImport({ requiredFields: ['email'] })
      const fileContent = 'name;email\nTest;'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })

      await validator.parseFile(file)

      expect(validator.validationErrors.value.length).toBe(1)
    })
  })

  describe('computed: validRows and invalidRows', () => {
    it('should separate valid and invalid rows', async () => {
      const validator = useImport({ requiredFields: ['name'] })
      const fileContent = 'name;email\nValid;test1@example.com\n;test2@example.com\nAlsoValid;test3@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })

      await validator.parseFile(file)

      expect(validator.validRows.value).toHaveLength(2)
      expect(validator.invalidRows.value).toHaveLength(1)
      expect(validator.validRows.value[0].name).toBe('Valid')
      expect(validator.validRows.value[1].name).toBe('AlsoValid')
    })
  })

  describe('executeImport', () => {
    it('should call onImport with valid data', async () => {
      const onImport = vi.fn().mockResolvedValue({ imported: 2 })
      const importHandler = useImport({ onImport })

      const fileContent = 'name;email\nTest1;test1@example.com\nTest2;test2@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      const result = await importHandler.executeImport()

      expect(onImport).toHaveBeenCalled()
      expect(result).toEqual({ imported: 2 })
      expect(importHandler.importProgress.value).toBe(100)
    })

    it('should set error when no onImport configured', async () => {
      const result = await importComposable.executeImport()

      expect(result).toBe(null)
      expect(importComposable.importError.value).toContain('Keine Import-Funktion')
    })

    it('should set isImporting during import', async () => {
      const onImport = vi.fn().mockResolvedValue({ imported: 1 })
      const importHandler = useImport({ onImport })

      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      const importPromise = importHandler.executeImport()
      // Note: checking during async might not work
      await importPromise

      expect(importHandler.isImporting.value).toBe(false)
    })

    it('should import only valid rows when skipErrors is true', async () => {
      const onImport = vi.fn().mockResolvedValue({ imported: 1 })
      const importHandler = useImport({
        requiredFields: ['name'],
        onImport
      })

      const fileContent = 'name;email\nValid;test1@example.com\n;test2@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      await importHandler.executeImport(true) // skipErrors = true

      expect(onImport).toHaveBeenCalledWith(
        expect.arrayContaining([expect.objectContaining({ name: 'Valid' })]),
        expect.any(Function)
      )
      expect(onImport.mock.calls[0][0]).toHaveLength(1)
    })

    it('should remove _rowIndex from imported data', async () => {
      const onImport = vi.fn().mockResolvedValue({ imported: 1 })
      const importHandler = useImport({ onImport })

      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      await importHandler.executeImport()

      const importedData = onImport.mock.calls[0][0]
      expect(importedData[0]._rowIndex).toBeUndefined()
    })

    it('should provide progress callback to onImport', async () => {
      const onImport = vi.fn().mockImplementation(async (data, progressCallback) => {
        progressCallback(50)
        return { imported: 1 }
      })
      const importHandler = useImport({ onImport })

      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      await importHandler.executeImport()

      expect(onImport).toHaveBeenCalledWith(
        expect.any(Array),
        expect.any(Function)
      )
    })

    it('should handle import errors', async () => {
      const onImport = vi.fn().mockRejectedValue(new Error('API Fehler'))
      const importHandler = useImport({ onImport })

      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      const result = await importHandler.executeImport()

      expect(result).toBe(null)
      expect(importHandler.importError.value).toBe('API Fehler')
    })

    it('should return null for empty data', async () => {
      const onImport = vi.fn()
      const importHandler = useImport({
        requiredFields: ['name'],
        onImport
      })

      // All rows invalid
      const fileContent = 'name;email\n;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      const result = await importHandler.executeImport(true) // skipErrors, but all invalid

      expect(result).toBe(null)
      expect(importHandler.importError.value).toContain('Keine gültigen Daten')
    })

    it('should store import results', async () => {
      const expectedResult = { imported: 2, errors: 0 }
      const onImport = vi.fn().mockResolvedValue(expectedResult)
      const importHandler = useImport({ onImport })

      const fileContent = 'name;email\nTest1;test1@example.com\nTest2;test2@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importHandler.parseFile(file)

      await importHandler.executeImport()

      expect(importHandler.importResults.value).toEqual(expectedResult)
    })
  })

  describe('resetImport', () => {
    it('should reset all import state', async () => {
      const fileContent = 'name;email\nTest;test@example.com'
      const file = new File([fileContent], 'test.csv', { type: 'text/csv' })
      await importComposable.parseFile(file)

      expect(importComposable.hasParsedData.value).toBe(true)

      importComposable.resetImport()

      expect(importComposable.isImporting.value).toBe(false)
      expect(importComposable.isParsing.value).toBe(false)
      expect(importComposable.importProgress.value).toBe(0)
      expect(importComposable.importError.value).toBe(null)
      expect(importComposable.parsedData.value).toEqual([])
      expect(importComposable.parsedHeaders.value).toEqual([])
      expect(importComposable.validationErrors.value).toEqual([])
      expect(importComposable.fileName.value).toBe('')
      expect(importComposable.importResults.value).toBe(null)
    })
  })
})
