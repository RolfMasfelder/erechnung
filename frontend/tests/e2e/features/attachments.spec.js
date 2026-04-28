// @ts-check
import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'

/**
 * E2E Tests: Rechnungsbegründende Dokumente (Attachments)
 *
 * Testet die Attachment-Funktionalität in der Rechnungsdetailansicht:
 *   1. Sektion "Rechnungsbegründende Dokumente" sichtbar
 *   2. Upload-Bereich nur bei DRAFT-Rechnungen sichtbar
 *   3. Datei-Upload (PDF) mit Beschreibung und Dokumenttyp
 *   4. Ungültige Dateitypen clientseitig abgelehnt
 *   5. Mehrere Dateien hochladen und einzelne entfernen
 *   6. Anhang in Liste nach Upload sichtbar
 *   7. Download-Button löst Datei-Download aus
 *   8. Löschen-Button mit Bestätigungsdialog (nur DRAFT)
 *   9. Kein Upload/Löschen bei nicht-DRAFT-Rechnungen
 *
 * Prerequisites:
 *   - Backend running (docker compose up -d)
 *   - Test data generated: manage.py generate_test_data --clear --preset standard
 *   - Testdaten enthalten DRAFT- und SENT-Rechnungen
 */

// ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

/**
 * Navigiert zur Detailansicht einer DRAFT-Rechnung.
 * @param {import('@playwright/test').Page} page
 */
async function goToDraftInvoice(page) {
  await page.goto('/invoices')
  await page.waitForLoadState('networkidle')

  const draftRow = page.locator('table tbody tr', { has: page.locator('.status-draft') }).first()
  await expect(draftRow).toBeVisible({ timeout: 10000 })

  // Wait for the attachment API response AND DOM render before capturing counts
  const attachmentResponsePromise = page.waitForResponse(
    res => res.url().includes('/invoice-attachments/') && res.status() === 200,
    { timeout: 10000 }
  )
  await draftRow.locator('a.invoice-link').click()
  await attachmentResponsePromise
  await page.waitForLoadState('networkidle')
}

/**
 * Navigiert zur Detailansicht einer SENT-Rechnung (nicht mehr DRAFT).
 * @param {import('@playwright/test').Page} page
 */
async function goToSentInvoice(page) {
  await page.goto('/invoices')
  await page.waitForLoadState('networkidle')

  const sentRow = page.locator('table tbody tr', { has: page.locator('.status-sent') }).first()
  await expect(sentRow).toBeVisible({ timeout: 10000 })

  const attachmentResponsePromise = page.waitForResponse(
    res => res.url().includes('/invoice-attachments/') && res.status() === 200,
    { timeout: 10000 }
  )
  await sentRow.locator('a.invoice-link').click()
  await attachmentResponsePromise
  await page.waitForLoadState('networkidle')
}

/**
 * Erstellt eine minimale In-Memory-PDF-Datei für Upload-Tests.
 * @returns {{ name: string, mimeType: string, buffer: Buffer }}
 */
function makePdfFile(name = 'Lieferschein.pdf') {
  const content = '%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF'
  return {
    name,
    mimeType: 'application/pdf',
    buffer: Buffer.from(content)
  }
}

// ─── Test Suite ───────────────────────────────────────────────────────────────

test.describe('Attachments: Rechnungsbegründende Dokumente', () => {
  // Serial mode: tests share the same DRAFT invoice and must not run in parallel
  // to avoid race conditions when counting attachment-items.
  test.describe.configure({ mode: 'serial' })

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      if (msg.type() === 'error') console.log('❌ BROWSER ERROR:', msg.text())
    })
    await login(page)
  })

  // ── 1. Sektion sichtbar ────────────────────────────────────────────────────

  test.describe('Sektion "Rechnungsbegründende Dokumente"', () => {
    test('Sektion ist in DRAFT-Rechnungsdetail sichtbar', async ({ page }) => {
      await goToDraftInvoice(page)

      await expect(page.getByText('Rechnungsbegründende Dokumente')).toBeVisible()
    })

    test('Leerer Zustand zeigt Hinweistext "Keine Anhänge vorhanden"', async ({ page }) => {
      await goToDraftInvoice(page)

      // If no attachments exist yet, placeholder text should be visible
      const attachmentList = page.locator('.attachment-list')
      const placeholder = page.getByText('Keine Anhänge vorhanden.')
      const hasItems = await attachmentList.count()

      if (hasItems === 0) {
        await expect(placeholder).toBeVisible()
      }
      // If attachments already exist (other tests ran first), list is shown instead
    })

    test('Upload-Bereich enthält Hinweis zu erlaubten Dateitypen', async ({ page }) => {
      await goToDraftInvoice(page)

      await expect(
        page.getByText(/PDF, PNG, JPEG, CSV, XLSX/i)
      ).toBeVisible()
      await expect(page.getByText(/max\. 10 MB/i)).toBeVisible()
    })
  })

  // ── 2. Upload-Bereich DRAFT vs. nicht-DRAFT ────────────────────────────────

  test.describe('Upload-Bereich: Sichtbarkeit nach Rechnungsstatus', () => {
    test('Upload-Bereich ist bei DRAFT-Rechnung sichtbar', async ({ page }) => {
      await goToDraftInvoice(page)

      const uploadArea = page.locator('.upload-area')
      await expect(uploadArea).toBeVisible()
    })

    test('Upload-Bereich fehlt bei SENT-Rechnung (schreibgeschützt)', async ({ page }) => {
      await goToSentInvoice(page)

      const uploadArea = page.locator('.upload-area')
      await expect(uploadArea).not.toBeVisible()
    })

    test('Löschen-Button fehlt bei SENT-Rechnung', async ({ page }) => {
      await goToSentInvoice(page)

      const deleteButtons = page.locator('button[title="Löschen"]')
      await expect(deleteButtons).toHaveCount(0)
    })
  })

  // ── 3. Datei-Upload ────────────────────────────────────────────────────────

  test.describe('Datei-Upload', () => {
    test('PDF-Datei auswählen zeigt Dateiname und Upload-Button', async ({ page }) => {
      await goToDraftInvoice(page)

      const pdf = makePdfFile('Testlieferschein.pdf')
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })

      // Pending area shows the filename
      await expect(page.locator('.pending-file-name').filter({ hasText: 'Testlieferschein.pdf' })).toBeVisible()

      // Upload button is visible
      await expect(page.getByRole('button', { name: /Hochladen/i })).toBeVisible()
    })

    test('Beschreibung und Dokumenttyp können vor dem Upload geändert werden', async ({ page }) => {
      await goToDraftInvoice(page)

      const pdf = makePdfFile('Zeitaufstellung.pdf')
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })

      await expect(page.locator('.pending-file')).toBeVisible()

      // Change description
      const descInput = page.locator('.pending-file input[placeholder*="Lieferschein"]')
      await descInput.clear()
      await descInput.fill('Stundenliste April 2026')
      await expect(descInput).toHaveValue('Stundenliste April 2026')

      // Change type to "Zeitaufstellung"
      const typeSelect = page.locator('.pending-file select')
      await typeSelect.selectOption('timesheet')
      await expect(typeSelect).toHaveValue('timesheet')
    })

    test('Pending-Upload kann via Abbrechen-Button zurückgesetzt werden', async ({ page }) => {
      await goToDraftInvoice(page)

      const pdf = makePdfFile('ZumAbbrechen.pdf')
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })

      await expect(page.locator('.pending-file')).toBeVisible()

      // Cancel removes pending list
      await page.getByRole('button', { name: 'Abbrechen' }).click()

      await expect(page.locator('.pending-file')).not.toBeVisible()
      await expect(page.getByRole('button', { name: /Hochladen/i })).not.toBeVisible()
    })

    test('Einzelne Datei aus Pending-Liste kann mit ✕ entfernt werden', async ({ page }) => {
      await goToDraftInvoice(page)

      const pdf1 = makePdfFile('Datei1.pdf')
      const pdf2 = makePdfFile('Datei2.pdf')
      const fileInput = page.locator('.upload-area input[type="file"]')

      // Upload two files at once
      await fileInput.setInputFiles([
        { name: pdf1.name, mimeType: pdf1.mimeType, buffer: pdf1.buffer },
        { name: pdf2.name, mimeType: pdf2.mimeType, buffer: pdf2.buffer }
      ])

      await expect(page.locator('.pending-file')).toHaveCount(2)

      // Remove first file via ✕ button
      await page.locator('.pending-file').first().locator('.remove-btn').click()

      await expect(page.locator('.pending-file')).toHaveCount(1)
      // The remaining file should be Datei2
      await expect(page.locator('.pending-file-name').filter({ hasText: 'Datei2.pdf' })).toBeVisible()
    })

    test('PDF-Upload erscheint in Attachment-Liste', async ({ page }) => {
      await goToDraftInvoice(page)

      // Count existing attachments before upload
      const existingCount = await page.locator('.attachment-item').count()

      const pdf = makePdfFile(`Beleg_${Date.now()}.pdf`)
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })

      await expect(page.locator('.pending-file')).toBeVisible()

      // Trigger upload
      await page.getByRole('button', { name: /Hochladen/i }).click()

      // Wait for the specific filename to appear in list (robust against loadAttachments race)
      await expect(page.locator('.pending-uploads')).not.toBeAttached({ timeout: 30000 })
      await expect(
        page.locator('.attachment-name').filter({ hasText: pdf.name })
      ).toBeVisible({ timeout: 30000 })

      // Attachment list grows by 1
      const newCount = await page.locator('.attachment-item').count()
      expect(newCount).toBe(existingCount + 1)
    })

    test('Mehrere Dateien gleichzeitig hochladen erscheinen in Liste', async ({ page }) => {
      await goToDraftInvoice(page)

      const existingCount = await page.locator('.attachment-item').count()

      const suffix = Date.now()
      const pdf1 = makePdfFile(`Multi_A_${suffix}.pdf`)
      const pdf2 = makePdfFile(`Multi_B_${suffix}.pdf`)
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles([
        { name: pdf1.name, mimeType: pdf1.mimeType, buffer: pdf1.buffer },
        { name: pdf2.name, mimeType: pdf2.mimeType, buffer: pdf2.buffer }
      ])

      // Button shows count
      await expect(page.getByRole('button', { name: '2 Dateien hochladen' })).toBeVisible()

      await page.getByRole('button', { name: '2 Dateien hochladen' }).click()
      await expect(page.locator('.pending-uploads')).not.toBeAttached({ timeout: 30000 })

      // Wait for both files to appear by name (robust against sequential upload race)
      await expect(page.locator('.attachment-name').filter({ hasText: pdf1.name })).toBeVisible({ timeout: 30000 })
      await expect(page.locator('.attachment-name').filter({ hasText: pdf2.name })).toBeVisible({ timeout: 30000 })

      const newCount = await page.locator('.attachment-item').count()
      expect(newCount).toBe(existingCount + 2)
    })
  })

  // ── 4. Ungültige Dateien ───────────────────────────────────────────────────

  test.describe('Clientseitige Datei-Validierung', () => {
    test('Datei mit verbotenem Typ (.exe) wird abgelehnt', async ({ page }) => {
      await goToDraftInvoice(page)

      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: 'virus.exe',
        mimeType: 'application/octet-stream',
        buffer: Buffer.from('MZ - fake exe')
      })

      // No pending file added — toast error or input unchanged
      await expect(page.locator('.pending-file')).not.toBeVisible()
    })

    test('Datei mit verbotenem Typ (.js) wird abgelehnt', async ({ page }) => {
      await goToDraftInvoice(page)

      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: 'script.js',
        mimeType: 'application/javascript',
        buffer: Buffer.from('alert("xss")')
      })

      await expect(page.locator('.pending-file')).not.toBeVisible()
    })
  })

  // ── 5. Download ────────────────────────────────────────────────────────────

  test.describe('Attachment herunterladen', () => {
    test('Herunterladen-Button löst Download aus', async ({ page }) => {
      await goToDraftInvoice(page)

      // Upload a file first so there's something to download
      const pdf = makePdfFile(`Download_Test_${Date.now()}.pdf`)
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })
      await page.getByRole('button', { name: /Hochladen/i }).click()
      await expect(page.locator('.pending-uploads')).not.toBeAttached({ timeout: 30000 })
      await page.waitForLoadState('networkidle')

      // Find the just-uploaded attachment
      const attachment = page.locator('.attachment-item', { hasText: pdf.name }).first()
      await expect(attachment).toBeVisible()

      // Click download and capture download event
      const downloadPromise = page.waitForEvent('download', { timeout: 10000 })
      await attachment.locator('button[title="Herunterladen"]').click()
      const download = await downloadPromise

      // Filename matches what we uploaded
      expect(download.suggestedFilename()).toBe(pdf.name)
    })
  })

  // ── 6. Löschen ────────────────────────────────────────────────────────────

  test.describe('Attachment löschen', () => {
    test('Löschen-Button erscheint bei DRAFT-Rechnung', async ({ page }) => {
      await goToDraftInvoice(page)

      // Upload a file so there is something deletable
      const pdf = makePdfFile(`ZumLoeschen_${Date.now()}.pdf`)
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })
      await page.getByRole('button', { name: /Hochladen/i }).click()
      await expect(page.locator('.pending-uploads')).not.toBeAttached({ timeout: 30000 })
      await page.waitForLoadState('networkidle')

      // Delete button should be visible for the uploaded attachment
      const attachment = page.locator('.attachment-item', { hasText: pdf.name }).first()
      await expect(attachment.locator('button[title="Löschen"]')).toBeVisible()
    })

    test('Bestätigungsdialog erscheint beim Löschen', async ({ page }) => {
      await goToDraftInvoice(page)

      // Upload a file
      const pdf = makePdfFile(`ConfirmDelete_${Date.now()}.pdf`)
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })
      await page.getByRole('button', { name: /Hochladen/i }).click()
      await expect(page.locator('.pending-uploads')).not.toBeAttached({ timeout: 30000 })

      const attachment = page.locator('.attachment-item', { hasText: pdf.name }).first()
      await expect(attachment).toBeVisible({ timeout: 10000 }) // Ensure upload is reflected before counting
      const countBefore = await page.locator('.attachment-item').count()

      // Click delete — browser confirm dialog should appear
      page.once('dialog', async dialog => {
        expect(dialog.type()).toBe('confirm')
        expect(dialog.message()).toContain(pdf.name)
        await dialog.dismiss() // Cancel → no deletion
      })
      await attachment.locator('button[title="Löschen"]').click()

      // Dismissed → attachment still in list
      await expect(attachment).toBeVisible()
      expect(await page.locator('.attachment-item').count()).toBe(countBefore)
    })

    test('Bestätigen des Dialogs löscht den Anhang aus der Liste', async ({ page }) => {
      await goToDraftInvoice(page)

      const pdf = makePdfFile(`DeleteConfirm_${Date.now()}.pdf`)
      const fileInput = page.locator('.upload-area input[type="file"]')

      await fileInput.setInputFiles({
        name: pdf.name,
        mimeType: pdf.mimeType,
        buffer: pdf.buffer
      })
      await page.getByRole('button', { name: /Hochladen/i }).click()
      await expect(page.locator('.pending-uploads')).not.toBeAttached({ timeout: 30000 })
      await page.waitForLoadState('networkidle')

      const attachment = page.locator('.attachment-item', { hasText: pdf.name }).first()
      await expect(attachment).toBeVisible()
      const countBefore = await page.locator('.attachment-item').count()

      // Accept the confirm dialog → delete proceeds
      page.once('dialog', async dialog => {
        await dialog.accept()
      })
      await attachment.locator('button[title="Löschen"]').click()

      // Attachment removed from list
      await expect(attachment).not.toBeVisible({ timeout: 10000 })
      const countAfter = await page.locator('.attachment-item').count()
      expect(countAfter).toBe(countBefore - 1)
    })
  })
})
