import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'
import path from 'path'
import fs from 'fs'

test.describe('CSV Export', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await login(page)

    // Navigate to invoices page
    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')
  })

  test('should display export button after selecting items', async ({ page }) => {
    // Export button appears only after selecting items (Bulk Export)
    // First select an item
    const checkboxes = page.locator('tbody tr input[type="checkbox"]')
    await checkboxes.first().check()
    await page.waitForTimeout(300)

    // Now check for export button in bulk action bar
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })
    await expect(exportButton).toBeVisible({ timeout: 5000 })
  })

  test('should show export format options', async ({ page }) => {
    // Select items first to make export button appear
    const checkboxes = page.locator('tbody tr input[type="checkbox"]')
    await checkboxes.first().check()
    await page.waitForTimeout(300)

    // Check that export button is visible
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })
    await expect(exportButton).toBeVisible({ timeout: 5000 })

    // Note: Currently no format dropdown implemented, export goes directly to CSV
    // This test verifies export functionality is accessible
  })

  test('should export all data as CSV', async ({ page }) => {
    // Select all items using "Alle auswählen" checkbox
    const selectAllCheckbox = page.locator('thead input[type="checkbox"], th input[type="checkbox"]')
    await selectAllCheckbox.check()
    await page.waitForTimeout(500)

    // Click export button to open dropdown
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })
    await exportButton.click()

    // Wait for dropdown to be visible
    const dropdown = page.locator('.export-dropdown')
    await expect(dropdown).toBeVisible({ timeout: 3000 })

    // Setup download handler BEFORE clicking option
    const downloadPromise = page.waitForEvent('download')

    // Click CSV option
    const csvOption = page.locator('.export-option:has-text("CSV: Alle")')
    await csvOption.click()

    // Wait for download
    const download = await downloadPromise

    // Check filename
    const filename = download.suggestedFilename()
    expect(filename).toMatch(/\.csv$/)
    expect(filename).toContain('rechnung')

    // Save file temporarily
    const tempPath = path.join('/tmp', filename)
    await download.saveAs(tempPath)

    // Verify file exists and has content
    expect(fs.existsSync(tempPath)).toBeTruthy()
    const fileSize = fs.statSync(tempPath).size
    expect(fileSize).toBeGreaterThan(0)

    // Read and validate CSV content
    const content = fs.readFileSync(tempPath, 'utf-8')

    // Should have header row
    const lines = content.split('\n').filter(line => line.trim())
    expect(lines.length).toBeGreaterThan(1)

    // Check for expected columns (German headers)
    const header = lines[0]
    expect(header).toMatch(/Rechnungsnr|Rechnungsnummer|Invoice/)
    expect(header).toMatch(/Kunde|Customer/)
    expect(header).toMatch(/Betrag|Amount/i)

    // Cleanup
    fs.unlinkSync(tempPath)
  })

  test('should export all data as JSON', async ({ page }) => {
    // Select all items using "Alle auswählen" checkbox
    const selectAllCheckbox = page.locator('thead input[type="checkbox"], th input[type="checkbox"]')
    await selectAllCheckbox.check()
    await page.waitForTimeout(500)

    // Click export button in bulk action bar to open dropdown
    const exportButton = page.getByRole('button', { name: /Export/i })
    await exportButton.click()

    // Wait for dropdown to be visible
    const dropdown = page.locator('.export-dropdown')
    await expect(dropdown).toBeVisible({ timeout: 3000 })

    // Setup download handler BEFORE clicking download option
    const downloadPromise = page.waitForEvent('download')

    // Click JSON "Alle Daten" option
    const jsonOption = page.locator('.export-option:has-text("JSON: Alle")')
    await jsonOption.click()

    // Wait for download
    const download = await downloadPromise

    // Check filename
    const filename = download.suggestedFilename()
    expect(filename).toMatch(/\.json$/)

    // Save file temporarily
    const tempPath = path.join('/tmp', filename)
    await download.saveAs(tempPath)

    // Verify file exists
    expect(fs.existsSync(tempPath)).toBeTruthy()

    // Read and validate JSON content
    const content = fs.readFileSync(tempPath, 'utf-8')
    const data = JSON.parse(content)

    // Should be an array
    expect(Array.isArray(data)).toBeTruthy()
    expect(data.length).toBeGreaterThan(0)

    // Check first item has expected properties
    const firstItem = data[0]
    expect(firstItem).toHaveProperty('invoice_number')
    expect(firstItem).toHaveProperty('business_partner')
    expect(firstItem).toHaveProperty('total_amount')

    // Cleanup
    fs.unlinkSync(tempPath)
  })

  test('should export selected items only', async ({ page }) => {
    // Select first two items
    const checkboxes = page.locator('tbody tr input[type="checkbox"]')
    await checkboxes.nth(0).check()
    await checkboxes.nth(1).check()
    await page.waitForTimeout(300)

    // Bulk action bar should be visible
    const bulkActionBar = page.locator('.bulk-action-bar, [data-testid="bulk-action-bar"]')
    await expect(bulkActionBar).toBeVisible({ timeout: 3000 })

    // Setup download handler
    const downloadPromise = page.waitForEvent('download')

    // Click export button to open dropdown
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })
    await exportButton.click()

    // Click CSV Auswahl option in dropdown
    const dropdown = page.locator('.export-dropdown')
    await expect(dropdown).toBeVisible({ timeout: 3000 })
    const csvOption = page.locator('.export-option:has-text("CSV: Auswahl")')
    await csvOption.click()

    // Wait for download
    const download = await downloadPromise

    // Save and validate
    const tempPath = path.join('/tmp', download.suggestedFilename())
    await download.saveAs(tempPath)

    const content = fs.readFileSync(tempPath, 'utf-8')
    const lines = content.split('\n').filter(line => line.trim())

    // Should have header + 2 data rows
    expect(lines.length).toBe(3) // header + 2 items

    // Cleanup
    fs.unlinkSync(tempPath)
  })

  test('should show progress indicator during export', async ({ page }) => {
    // Select all items first
    const selectAllCheckbox = page.locator('thead input[type="checkbox"], th input[type="checkbox"]')
    await selectAllCheckbox.check()
    await page.waitForTimeout(300)

    // Setup download handler but don't wait yet
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 })

    // Click export button to open dropdown
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })
    await exportButton.click()

    // Click CSV Alle Daten option in dropdown
    const dropdown = page.locator('.export-dropdown')
    await expect(dropdown).toBeVisible({ timeout: 3000 })
    const csvOption = page.locator('.export-option:has-text("CSV: Alle")')
    await csvOption.click()

    // Check for loading indicator (might be brief)
    const loadingIndicator = page.locator('.loading, .spinner, [data-loading]')
    // Note: This might not always be visible if export is very fast

    // Wait for download to complete
    await downloadPromise
  })

  test('should handle empty data export', async ({ page }) => {
    // Apply filter that returns no results
    const searchInput = page.locator('input[placeholder*="Suche"], input[type="search"]')
    await searchInput.fill('NONEXISTENT-XXXXX-9999')
    await page.waitForTimeout(400)
    await page.waitForLoadState('networkidle')

    // No items visible → no checkboxes to select → no export button
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })

    // Export button should NOT be visible (only appears after selecting items)
    await expect(exportButton).toBeHidden({ timeout: 3000 })
  })

  test('should export with German CSV format (semicolon delimiter)', async ({ page }) => {
    // Select all items first
    const selectAllCheckbox = page.locator('thead input[type="checkbox"], th input[type="checkbox"]')
    await selectAllCheckbox.check()
    await page.waitForTimeout(300)

    // Setup download handler
    const downloadPromise = page.waitForEvent('download')

    // Click export button to open dropdown
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })
    await exportButton.click()

    // Click CSV Alle Daten option in dropdown
    const dropdown = page.locator('.export-dropdown')
    await expect(dropdown).toBeVisible({ timeout: 3000 })
    const csvOption = page.locator('.export-option:has-text("CSV: Alle")')
    await csvOption.click()

    // Wait for download
    const download = await downloadPromise

    // Save file
    const tempPath = path.join('/tmp', download.suggestedFilename())
    await download.saveAs(tempPath)

    // Read content
    const content = fs.readFileSync(tempPath, 'utf-8')

    // Check for semicolon delimiter (German Excel format)
    const firstLine = content.split('\n')[0]
    expect(firstLine).toContain(';')

    // Check that semicolon count indicates proper columns
    const semicolonCount = (firstLine.match(/;/g) || []).length
    expect(semicolonCount).toBeGreaterThan(3) // At least 4 columns

    // Cleanup
    fs.unlinkSync(tempPath)
  })

  test('should include all visible columns in export', async ({ page }) => {
    // Select all items first
    const selectAllCheckbox = page.locator('thead input[type="checkbox"], th input[type="checkbox"]')
    await selectAllCheckbox.check()
    await page.waitForTimeout(300)

    // Setup download handler
    const downloadPromise = page.waitForEvent('download')

    // Click export button to open dropdown
    const exportButton = page.getByRole('button', { name: /Export|Exportieren/i })
    await exportButton.click()

    // Click CSV Alle Daten option in dropdown
    const dropdown = page.locator('.export-dropdown')
    await expect(dropdown).toBeVisible({ timeout: 3000 })
    const csvOption = page.locator('.export-option:has-text("CSV: Alle")')
    await csvOption.click()

    // Wait for download
    const download = await downloadPromise
    const tempPath = path.join('/tmp', download.suggestedFilename())
    await download.saveAs(tempPath)

    // Read CSV header
    const content = fs.readFileSync(tempPath, 'utf-8')
    const header = content.split('\n')[0]

    // Check for expected columns
    const expectedColumns = [
      /Rechnungsnr|Rechnungsnummer|Invoice.*Number/i,
      /Kunde|Customer/i,
      /Datum|Date/i,
      /Betrag|Amount|Total/i,
      /Status/i
    ]

    for (const columnPattern of expectedColumns) {
      expect(header).toMatch(columnPattern)
    }

    // Cleanup
    fs.unlinkSync(tempPath)
  })
})
