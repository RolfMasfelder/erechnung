// @ts-check
import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'

/**
 * E2E Tests: Gutschrift / Rechnungs-Stornierung (Credit Note)
 *
 * Prerequisites:
 *   - Backend running (docker compose up -d)
 *   - Test data generated: manage.py generate_test_data --clear --preset standard
 *     (creates invoices with SENT/PAID/DRAFT status, user testuser/testpass123)
 */

const INVOICE_DETAIL_URL_PATTERN = /\/api\/invoices\/\d+\/?$/

/**
 * Open the invoice list and apply the status filter so that only invoices
 * with the given status are visible. Required because the list is paginated
 * and SENT invoices may otherwise be off the first page once tests have
 * created credit notes / cancellations during the run.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} label - localized status option ("Versendet", "Bezahlt", ...)
 */
async function filterByStatus(page, label) {
  await page.goto('/invoices')
  await page.waitForLoadState('networkidle')
  await page.locator('select').first().selectOption({ label })
  await page.waitForLoadState('networkidle')
}

/**
 * Locate the first SENT invoice row that is not a credit note.
 * Uses the status filter for stable visibility across paginated results.
 * @param {import('@playwright/test').Page} page
 */
async function firstSentInvoiceRow(page) {
  await filterByStatus(page, 'Versendet')
  const row = page.locator('table tbody tr', {
    has: page.locator('.status-sent'),
    hasNot: page.locator('.type-credit-note'),
  }).first()
  await expect(row).toBeVisible({ timeout: 10000 })
  return row
}

/**
 * Navigate to a SENT invoice detail page.
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<string>} The invoice number
 */
async function goToSentInvoice(page) {
  const sentRow = await firstSentInvoiceRow(page)
  const invoiceNumber = await sentRow.locator('a.invoice-link').textContent() ?? ''
  await sentRow.locator('a.invoice-link').click()
  await page.waitForLoadState('networkidle')
  return invoiceNumber.trim()
}

test.describe('Gutschrift / Stornierung', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      if (msg.type() === 'error') console.log('❌ BROWSER ERROR:', msg.text())
    })
    await login(page)
  })

  test.describe('Storno-Button Sichtbarkeit', () => {
    test('Stornieren-Button ist bei SENT-Rechnung sichtbar', async ({ page }) => {
      const sentRow = await firstSentInvoiceRow(page)
      await sentRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      // Cancel button should be visible
      const cancelButton = page.getByRole('button', { name: /Stornieren/i })
      await expect(cancelButton).toBeVisible({ timeout: 5000 })
    })

    test('Stornieren-Button ist bei PAID-Rechnung sichtbar', async ({ page }) => {
      await filterByStatus(page, 'Bezahlt')
      const paidRow = page.locator('table tbody tr', {
        has: page.locator('.status-paid'),
        hasNot: page.locator('.type-credit-note'),
      }).first()
      await expect(paidRow).toBeVisible({ timeout: 10000 })

      await paidRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      const cancelButton = page.getByRole('button', { name: /Stornieren/i })
      await expect(cancelButton).toBeVisible({ timeout: 5000 })
    })

    test('Stornieren-Button ist bei DRAFT-Rechnung NICHT sichtbar', async ({ page }) => {
      await filterByStatus(page, 'Entwurf')
      const draftRow = page.locator('table tbody tr', {
        has: page.locator('.status-draft'),
      }).first()
      await expect(draftRow).toBeVisible({ timeout: 10000 })

      await draftRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      const cancelButton = page.getByRole('button', { name: /Stornieren/i })
      await expect(cancelButton).not.toBeVisible()
    })
  })

  test.describe('Storno-Dialog', () => {
    test('Dialog öffnet und schließt mit Abbrechen', async ({ page }) => {
      await goToSentInvoice(page)

      // Open dialog
      await page.getByRole('button', { name: /Stornieren/i }).click()

      // Dialog should be visible
      const dialog = page.locator('.cancel-dialog')
      await expect(dialog).toBeVisible()
      await expect(dialog.locator('h2')).toContainText('Rechnung stornieren')

      // Close via "Abbrechen" button
      await dialog.getByRole('button', { name: 'Abbrechen' }).click()
      await expect(dialog).not.toBeVisible()
    })

    test('Dialog schließt bei Klick auf Overlay', async ({ page }) => {
      await goToSentInvoice(page)

      await page.getByRole('button', { name: /Stornieren/i }).click()

      const dialog = page.locator('.cancel-dialog')
      await expect(dialog).toBeVisible()

      // Click on overlay (outside the dialog content) using the overlay locator
      // Using @click.self on .modal-overlay requires clicking the overlay element directly
      await page.locator('.modal-overlay').click({ position: { x: 10, y: 10 } })
      await expect(dialog).not.toBeVisible()
    })

    test('Stornieren-Button ist ohne Stornogrund deaktiviert', async ({ page }) => {
      await goToSentInvoice(page)

      await page.getByRole('button', { name: /Stornieren/i }).click()

      const dialog = page.locator('.cancel-dialog')
      await expect(dialog).toBeVisible()

      // The confirm button inside the dialog should be disabled
      const confirmButton = dialog.getByRole('button', { name: 'Stornieren' })
      await expect(confirmButton).toBeDisabled()

      // Textarea should be empty
      const reasonInput = page.locator('#cancelReason')
      await expect(reasonInput).toBeVisible()
      await expect(reasonInput).toHaveValue('')
    })

    test('Stornieren-Button wird nach Eingabe des Grunds aktiv', async ({ page }) => {
      await goToSentInvoice(page)

      await page.getByRole('button', { name: /Stornieren/i }).click()

      const dialog = page.locator('.cancel-dialog')
      const confirmButton = dialog.getByRole('button', { name: 'Stornieren' })
      const reasonInput = page.locator('#cancelReason')

      // Initially disabled
      await expect(confirmButton).toBeDisabled()

      // Type a reason
      await reasonInput.fill('E2E Test: Fehlerhafter Rechnungsbetrag')

      // Now enabled
      await expect(confirmButton).toBeEnabled()
    })

    test('Nur Leerzeichen reichen nicht als Stornogrund', async ({ page }) => {
      await goToSentInvoice(page)

      await page.getByRole('button', { name: /Stornieren/i }).click()

      const dialog = page.locator('.cancel-dialog')
      const confirmButton = dialog.getByRole('button', { name: 'Stornieren' })
      const reasonInput = page.locator('#cancelReason')

      // Fill with whitespace only
      await reasonInput.fill('   ')
      await expect(confirmButton).toBeDisabled()
    })
  })

  test.describe.serial('Storno-Workflow (End-to-End)', () => {
    test('Rechnung stornieren erzeugt Gutschrift und navigiert dorthin', async ({ page }) => {
      // Navigate to a SENT invoice (filter list to keep them on page 1)
      const sentRow = await firstSentInvoiceRow(page)
      const originalNumber = (await sentRow.locator('a.invoice-link').textContent() ?? '').trim()
      console.log(`Storniere Rechnung: ${originalNumber}`)

      await sentRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      // Open cancel dialog
      await page.getByRole('button', { name: /Stornieren/i }).click()
      const dialog = page.locator('.cancel-dialog')
      await expect(dialog).toBeVisible()

      // Fill reason and confirm
      await page.locator('#cancelReason').fill('E2E Test: Stornierung wegen fehlerhafter Angaben')

      // Set up listener for the detail page GET BEFORE triggering cancel
      const detailResponsePromise = page.waitForResponse(
        resp => INVOICE_DETAIL_URL_PATTERN.test(resp.url()) && resp.request().method() === 'GET' && resp.status() === 200,
        { timeout: 15000 }
      )

      // Wait for cancel API response
      const [cancelResp] = await Promise.all([
        page.waitForResponse(
          resp => resp.url().includes('/cancel/') && resp.request().method() === 'POST',
          { timeout: 15000 }
        ),
        dialog.getByRole('button', { name: 'Stornieren' }).click()
      ])

      console.log(`POST /cancel/ → Status: ${cancelResp.status()}`)
      expect(cancelResp.ok()).toBeTruthy()

      const cancelData = await cancelResp.json()
      console.log(`Gutschrift erstellt: ${cancelData.credit_note_number} (ID: ${cancelData.credit_note_id})`)

      // Wait for navigation and credit note data to load
      await detailResponsePromise
      await page.waitForLoadState('networkidle')

      // Verify we're on the credit note page
      const pageTitle = page.locator('.page-title')
      await expect(pageTitle).toContainText(cancelData.credit_note_number, { timeout: 10000 })

      // Credit note should show "Gutschrift" badge
      const typeBadge = page.locator('.page-title .type-badge.type-credit-note')
      await expect(typeBadge).toBeVisible()
      await expect(typeBadge).toContainText('Gutschrift')

      // Credit note number should have GS- prefix
      expect(cancelData.credit_note_number).toMatch(/^GS-/)
    })

    test('Gutschrift zeigt Querverweis zur Originalrechnung', async ({ page }) => {
      // First, find a SENT invoice and cancel it (if not already done)
      await filterByStatus(page, 'Versendet')
      const sentRow = page.locator('table tbody tr', {
        has: page.locator('.status-sent'),
        hasNot: page.locator('.type-credit-note'),
      }).first()
      // If no SENT invoices left (all cancelled by previous test), skip
      const sentCount = await sentRow.count()
      if (sentCount === 0) {
        test.skip()
        return
      }

      const originalNumber = (await sentRow.locator('a.invoice-link').textContent() ?? '').trim()
      await sentRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      // Cancel it
      await page.getByRole('button', { name: /Stornieren/i }).click()
      await page.locator('#cancelReason').fill('E2E Test: Querverweis-Prüfung')

      // Set up listener for the detail page GET BEFORE triggering cancel
      const detailResponsePromise = page.waitForResponse(
        resp => INVOICE_DETAIL_URL_PATTERN.test(resp.url()) && resp.request().method() === 'GET' && resp.status() === 200,
        { timeout: 15000 }
      )

      await Promise.all([
        page.waitForResponse(
          resp => resp.url().includes('/cancel/') && resp.request().method() === 'POST',
          { timeout: 15000 }
        ),
        page.locator('.cancel-dialog').getByRole('button', { name: 'Stornieren' }).click()
      ])

      // Wait for navigation and credit note data to load
      await detailResponsePromise
      await page.waitForLoadState('networkidle')

      // On the credit note page: verify "Storno zu:" cross-link
      const stornoRef = page.locator('.detail-item', { hasText: 'Storno zu:' })
      await expect(stornoRef).toBeVisible({ timeout: 10000 })
      const crossLink = stornoRef.locator('a.cross-link')
      await expect(crossLink).toContainText(originalNumber)

      // Navigate back to the original invoice via the cross-link
      await crossLink.click()
      await page.waitForLoadState('networkidle')

      // Original invoice should show "Storniert durch:" cross-link
      const cancelledByRef = page.locator('.detail-item', { hasText: 'Storniert durch:' })
      await expect(cancelledByRef).toBeVisible({ timeout: 10000 })
      const reverseLink = cancelledByRef.locator('a.cross-link')
      await expect(reverseLink).toBeVisible()
    })

    test('Stornieren-Button verschwindet nach Stornierung', async ({ page }) => {
      await filterByStatus(page, 'Versendet')
      const sentRow = page.locator('table tbody tr', {
        has: page.locator('.status-sent'),
        hasNot: page.locator('.type-credit-note'),
      }).first()
      const sentCount = await sentRow.count()
      if (sentCount === 0) {
        test.skip()
        return
      }

      await sentRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      // Cancel the invoice
      await page.getByRole('button', { name: /Stornieren/i }).click()
      await page.locator('#cancelReason').fill('E2E Test: Button-Sichtbarkeit nach Storno')

      // Set up listener for the detail page GET BEFORE triggering cancel
      const detailResponsePromise = page.waitForResponse(
        resp => INVOICE_DETAIL_URL_PATTERN.test(resp.url()) && resp.request().method() === 'GET' && resp.status() === 200,
        { timeout: 15000 }
      )

      await Promise.all([
        page.waitForResponse(
          resp => resp.url().includes('/cancel/') && resp.request().method() === 'POST',
          { timeout: 15000 }
        ),
        page.locator('.cancel-dialog').getByRole('button', { name: 'Stornieren' }).click()
      ])

      // Wait for navigation and credit note data to load
      await detailResponsePromise
      await page.waitForLoadState('networkidle')

      // On the credit note page: cancel button should NOT be visible (credit notes can't be cancelled)
      const cancelButton = page.getByRole('button', { name: /Stornieren/i })
      await expect(cancelButton).not.toBeVisible()
    })
  })

  test.describe('Gutschrift in Listenansicht', () => {
    test('Gutschrift-Badge "GS" wird in der Rechnungsliste angezeigt', async ({ page }) => {
      // Check if credit notes already exist (created by other tests)
      await page.goto('/invoices')
      await page.waitForLoadState('networkidle')

      const searchInput = page.getByPlaceholder(/Suche/i)
      await searchInput.fill('GS-')
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(500)

      const existingBadge = page.locator('.type-badge.type-credit-note')
      const existingCount = await existingBadge.count()

      if (existingCount === 0) {
        // No credit notes yet — create one by cancelling a SENT invoice
        await searchInput.clear()
        await page.waitForLoadState('networkidle')

        const sentRow = page.locator('table tbody tr', { has: page.locator('.status-sent') }).first()
        const sentCount = await sentRow.count()

        if (sentCount > 0) {
          await sentRow.locator('a.invoice-link').click()
          await page.waitForLoadState('networkidle')

          const cancelButton = page.getByRole('button', { name: /Stornieren/i })
          if (await cancelButton.isVisible()) {
            await cancelButton.click()
            await page.locator('#cancelReason').fill('E2E Test: Badge-Prüfung in Liste')

            await Promise.all([
              page.waitForResponse(
                resp => resp.url().includes('/cancel/') && resp.request().method() === 'POST',
                { timeout: 15000 }
              ),
              page.locator('.cancel-dialog').getByRole('button', { name: 'Stornieren' }).click()
            ])

            await page.waitForLoadState('networkidle')
          }
        }

        // Go back to list and search for credit notes
        await page.goto('/invoices')
        await page.waitForLoadState('networkidle')
        await page.getByPlaceholder(/Suche/i).fill('GS-')
        await page.waitForLoadState('networkidle')
        await page.waitForTimeout(500)
      }

      // Should find at least one credit note with GS badge
      const gsBadge = page.locator('.type-badge.type-credit-note')
      await expect(gsBadge.first()).toBeVisible({ timeout: 10000 })
      await expect(gsBadge.first()).toContainText('GS')
    })
  })
})
