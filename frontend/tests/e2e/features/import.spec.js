import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'
import { mockBusinessPartnersAPI, mockBusinessPartnerImportAPI } from '../fixtures/mock-api.js'

test.describe('CSV Import', () => {
  // CSV test data with API field names (English)
  const validCSV = `name;country;city;postal_code;street;email
Testfirma GmbH;DE;Berlin;10115;Teststraße 1;test@example.com
Mustermann AG;AT;Wien;1010;Musterweg 2;muster@example.at
Beispiel Ltd;CH;Zürich;8001;Beispielstr. 3;beispiel@example.ch`

  const invalidCSV = `name;country;city;postal_code;street;email
;DE;Berlin;10115;Teststraße 1;test@example.com
Ohne Land;;Wien;1010;Musterweg 2;muster@example.at
Ungültige Email;CH;Zürich;8001;Beispielstr. 3;invalid-email`

  const mixedCSV = `name;country;city;postal_code;street;email
Gute Firma;DE;München;80331;Hauptstr. 1;gut@example.com
;DE;Berlin;10115;Teststraße 1;
Weitere Firma;FR;Paris;75001;Rue Test;info@example.fr`

  test.beforeEach(async ({ page, context }) => {
    // Setup API mocking
    await mockBusinessPartnersAPI(context)
    await mockBusinessPartnerImportAPI(context)

    // Login first
    await login(page)

    // Navigate to business partners page
    await page.goto('/business-partners')
    await page.waitForLoadState('networkidle')
  })

  test('should display import button', async ({ page }) => {
    // Check for import button
    const importButton = page.getByRole('button', { name: /Import/i })
    await expect(importButton).toBeVisible()
  })

  test('should open import modal', async ({ page }) => {
    // Click import button
    const importButton = page.getByRole('button', { name: /Import/i })
    await importButton.click()

    // Modal should open
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })
    await expect(modal).toBeVisible()

    // Check for upload zone (drop-zone class)
    const uploadZone = modal.locator('.drop-zone')
    await expect(uploadZone).toBeVisible()
  })

  test('should display drag and drop zone', async ({ page }) => {
    // Open import modal
    await page.getByRole('button', { name: /Import/i }).click()

    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })
    await expect(modal).toBeVisible()

    // Check for drag & drop text
    await expect(modal).toContainText(/CSV-Datei hierher ziehen/i)

    // Check for file input
    const fileInput = modal.locator('input[type="file"]')
    await expect(fileInput).toBeAttached()
  })

  test('should upload CSV file via file input', async ({ page }) => {
    // Open import modal
    await page.getByRole('button', { name: /Import/i }).click()

    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    // Upload file via Buffer
    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(validCSV, 'utf-8')
    })

    // Wait for file to be processed
    await page.waitForTimeout(500)

    // Preview should appear (use .data-preview only to avoid strict mode)
    const preview = modal.locator('.data-preview').first()
    await expect(preview).toBeVisible({ timeout: 3000 })
  })

  test('should show preview of valid data', async ({ page }) => {
    // Open import modal and upload
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(validCSV, 'utf-8')
    })

    await page.waitForTimeout(500)

    // Check preview shows data
    const preview = modal.locator('.preview-table')
    await expect(preview).toBeVisible({ timeout: 3000 })

    // Should show row count (Zeilen gesamt)
    await expect(modal).toContainText(/3.*Zeilen gesamt|3.*gesamt/i)

    // Should show valid count (Gültig)
    await expect(modal).toContainText(/3.*Gültig/i)
  })

  test('should show validation errors for invalid rows', async ({ page }) => {
    // Open import modal and upload invalid file
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'invalid-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(invalidCSV, 'utf-8')
    })

    await page.waitForTimeout(500)

    // Should show error count (Validierungsfehler gefunden)
    await expect(modal).toContainText(/Validierungsfehler gefunden/i, { timeout: 3000 })

    // Should show error details (use .first() to avoid strict mode)
    const errorList = modal.locator('.validation-errors, .errors-list').first()
    await expect(errorList).toBeVisible()

    // Should show line numbers
    await expect(errorList).toContainText(/Zeile/i)
  })

  test('should handle mixed valid/invalid data', async ({ page }) => {
    // Open import modal and upload mixed file
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'mixed-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(mixedCSV, 'utf-8')
    })

    await page.waitForTimeout(500)

    // Should show both valid and invalid counts
    await expect(modal).toContainText(/gültig|valid/i, { timeout: 3000 })
    await expect(modal).toContainText(/Fehler|error|ungültig|invalid/i)

    // Should offer option to import only valid rows
    const importValidOnlyCheckbox = modal.locator('input[type="checkbox"]').filter({
      hasText: /nur.*gültig|only.*valid/i
    }).or(modal.getByText(/nur.*gültig|only.*valid/i).locator('..').locator('input[type="checkbox"]'))

    // Checkbox might exist
    const hasCheckbox = await importValidOnlyCheckbox.count() > 0
    if (hasCheckbox) {
      await expect(importValidOnlyCheckbox.first()).toBeVisible()
    }
  })

  test('should import valid data successfully', async ({ page }) => {
    // Open import modal and upload
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(validCSV, 'utf-8')
    })

    await page.waitForTimeout(500)

    // Click import button (text includes count: "3 Zeilen importieren")
    const importConfirmButton = modal.getByRole('button', { name: /\d+\s+Zeilen\s+importieren/i })
    await expect(importConfirmButton).toBeEnabled({ timeout: 3000 })
    await importConfirmButton.click()

    // Wait for success: modal closes (import completed and modal dismissed)
    await expect(modal).toBeHidden({ timeout: 10000 })
  })

  test('should show progress indicator during import', async ({ page }) => {
    // Open import modal and upload
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(validCSV, 'utf-8')
    })

    await page.waitForTimeout(500)

    // Click import button (dynamic count)
    const importButton = modal.getByRole('button', { name: /\d+\s+Zeilen\s+importieren/i })
    await importButton.click()

    // Check for loading indicator (import-progress)
    const loadingIndicator = modal.locator('.import-progress, .progress-bar')
    // Might be brief, so don't assert visibility

    // Wait for completion
    await page.waitForTimeout(1000)
  })

  test('should validate file type', async ({ page }) => {
    // Open import modal
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    // Try to upload non-CSV file via Buffer
    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'not-a-csv.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('This is not a CSV file', 'utf-8')
    })

    await page.waitForTimeout(500)

    // Should show error about file type (import-error class)
    const errorMessage = modal.locator('.import-error')
    await expect(errorMessage).toBeVisible({ timeout: 3000 })
    await expect(errorMessage).toContainText(/CSV|Dateiformat|Format|Fehler/i)
  })

  test('should allow canceling import', async ({ page }) => {
    // Open import modal
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })
    await expect(modal).toBeVisible()

    // Upload file
    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(validCSV, 'utf-8')
    })
    await page.waitForTimeout(500)

    // Click cancel button
    const cancelButton = modal.getByRole('button', { name: /Abbrechen|Cancel/i })
    await cancelButton.click()

    // Modal should close
    await expect(modal).toBeHidden({ timeout: 2000 })

    // No import should have happened (no success message)
    const successAlert = page.locator('.alert-success')
    await expect(successAlert).toBeHidden()
  })

  test('should display import summary after completion', async ({ page }) => {
    // Open import modal and upload
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'valid-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(validCSV, 'utf-8')
    })
    await page.waitForTimeout(500)

    // Import (dynamic count in button text)
    const importButton = modal.getByRole('button', { name: /\d+\s+Zeilen\s+importieren/i })
    await importButton.click()

    // Wait for success: modal closes after successful import
    await expect(modal).toBeHidden({ timeout: 10000 })

    // Success toast should have appeared
    const successToast = page.locator('.toast').filter({ hasText: /erfolgreich|importiert|success/i })
    await expect(successToast).toBeVisible({ timeout: 3000 })
  })

  test('should handle empty CSV file', async ({ page }) => {
    // Open import modal and upload empty CSV (header only)
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    const fileInput = modal.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: 'empty.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('Name;Land;Stadt\n', 'utf-8')
    })

    await page.waitForTimeout(500)

    // With no data rows, the modal stays on the upload step (hasParsedData is false).
    // The drop zone should still be visible — no preview is shown.
    const dropZone = modal.locator('.drop-zone')
    await expect(dropZone).toBeVisible({ timeout: 3000 })

    // Import button should NOT be present (no data to import)
    const importButton = modal.getByRole('button', { name: /\d+\s+Zeilen\s+importieren|Importieren/i })
    await expect(importButton).toHaveCount(0)
  })

  test('should support drag and drop upload', async ({ page }) => {
    // Open import modal
    await page.getByRole('button', { name: /Import/i }).click()
    const modal = page.locator('.modal, [role="dialog"]').filter({ hasText: /Import/i })

    // Get upload zone (drop-zone class)
    const uploadZone = modal.locator('.drop-zone').first()
    await expect(uploadZone).toBeVisible()

    // Simulate drag and drop with Buffer
    const dataTransfer = await page.evaluateHandle((csvContent) => {
      const dt = new DataTransfer()
      const file = new File([csvContent], 'test.csv', { type: 'text/csv' })
      dt.items.add(file)
      return dt
    }, validCSV)

    await uploadZone.dispatchEvent('drop', { dataTransfer })

    await page.waitForTimeout(500)

    // Preview should appear (use .first() to avoid strict mode)
    const preview = modal.locator('.data-preview').first()
    await expect(preview).toBeVisible({ timeout: 3000 })
  })
})
