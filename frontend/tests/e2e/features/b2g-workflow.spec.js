// @ts-check
import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'

/**
 * E2E Tests: B2G-Workflow (Business-to-Government / XRechnung)
 *
 * Testet den vollständigen Workflow:
 *   1. GOVERNMENT-Geschäftspartner mit Leitweg-ID anlegen
 *   2. Leitweg-ID Validierung (Pflichtfeld, Format)
 *   3. Rechnung an GOVERNMENT-Partner erstellen
 *   4. XRechnung-Badge "XR" in der Rechnungsliste
 *   5. XRechnung XML erzeugen Button in Detailansicht
 *
 * Prerequisites:
 *   - Backend running (docker compose up -d)
 *   - Test data generated: manage.py generate_test_data --clear --preset standard
 */

// Valid Leitweg-ID with correct Modulo-97 check digit
const VALID_LEITWEG_ID = '04011000-1234512345-35'

const uniqueSuffix = () => Date.now().toString().slice(-6)

/**
 * Create a GOVERNMENT partner via the UI.
 * @param {import('@playwright/test').Page} page
 * @param {string} name
 * @returns {Promise<void>}
 */
async function createGovernmentPartner(page, name) {
  await page.goto('/business-partners')
  await page.waitForLoadState('networkidle')

  await page.getByRole('button', { name: /Neuer Geschäftspartner|Neuen Geschäftspartner/i }).click()
  await expect(page.getByText('Neuen Geschäftspartner anlegen')).toBeVisible()

  await page.getByLabel('Partnertyp').selectOption('GOVERNMENT')
  await page.getByLabel('Firmenname / Name').fill(name)
  await page.getByLabel('Straße und Hausnummer').fill('Rathausplatz 1')
  await page.getByLabel('PLZ').fill('10115')
  await page.getByLabel('Stadt').fill('Berlin')
  await page.getByLabel('Leitweg-ID').fill(VALID_LEITWEG_ID)

  await page.getByRole('button', { name: 'Geschäftspartner anlegen' }).click()
  await expect(page.getByText('Neuen Geschäftspartner anlegen')).not.toBeVisible({ timeout: 10000 })
  await page.waitForLoadState('networkidle')
}

/**
 * Create an invoice for a given partner via the UI.
 * @param {import('@playwright/test').Page} page
 * @param {string} partnerName
 * @returns {Promise<void>}
 */
async function createInvoiceForPartner(page, partnerName) {
  await page.goto('/invoices')
  await page.waitForLoadState('networkidle')

  await page.getByRole('button', { name: /Neue Rechnung/i }).click()
  await expect(page.getByText('Neue Rechnung erstellen')).toBeVisible()

  // Select the GOVERNMENT partner as customer
  await page.getByLabel('Kunde').selectOption({ label: partnerName })

  // Fill dates
  const today = new Date()
  const issueDate = today.toISOString().split('T')[0]
  const dueDate = new Date(today.getTime() + 30 * 86400000).toISOString().split('T')[0]

  await page.locator('#issue_date input').fill(issueDate)
  await page.locator('#due_date input').fill(dueDate)

  // Fill first line item — select first product
  const productSelect = page.locator('#product_0')
  await productSelect.selectOption({ index: 1 }) // first real product (skip placeholder)

  await page.locator('#quantity_0').fill('1')

  // Submit
  await page.getByRole('button', { name: 'Rechnung erstellen' }).click()
  await expect(page.getByText('Neue Rechnung erstellen')).not.toBeVisible({ timeout: 10000 })
  await page.waitForLoadState('networkidle')
}

test.describe('B2G-Workflow (XRechnung)', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      if (msg.type() === 'error') console.log('❌ BROWSER ERROR:', msg.text())
    })
    await login(page)
  })

  test.describe('GOVERNMENT-Partner anlegen', () => {
    test('Leitweg-ID Feld erscheint bei Partnertyp "Öffentlicher Auftraggeber"', async ({ page }) => {
      await page.goto('/business-partners')
      await page.waitForLoadState('networkidle')

      await page.getByRole('button', { name: /Neuer Geschäftspartner|Neuen Geschäftspartner/i }).click()
      await expect(page.getByText('Neuen Geschäftspartner anlegen')).toBeVisible()

      // Leitweg-ID should NOT be visible for BUSINESS type (default)
      await expect(page.getByLabel('Leitweg-ID')).not.toBeVisible()

      // Switch to GOVERNMENT
      await page.getByLabel('Partnertyp').selectOption('GOVERNMENT')

      // Leitweg-ID should now be visible
      await expect(page.getByLabel('Leitweg-ID')).toBeVisible()
      await expect(page.getByText('Pflichtfeld für öffentliche Auftraggeber')).toBeVisible()
    })

    test('Leitweg-ID Feld verschwindet bei Wechsel zurück zu Unternehmen', async ({ page }) => {
      await page.goto('/business-partners')
      await page.waitForLoadState('networkidle')

      await page.getByRole('button', { name: /Neuer Geschäftspartner|Neuen Geschäftspartner/i }).click()
      await expect(page.getByText('Neuen Geschäftspartner anlegen')).toBeVisible()

      // Switch to GOVERNMENT → Leitweg-ID visible
      await page.getByLabel('Partnertyp').selectOption('GOVERNMENT')
      await expect(page.getByLabel('Leitweg-ID')).toBeVisible()

      // Switch back to BUSINESS → Leitweg-ID hidden
      await page.getByLabel('Partnertyp').selectOption('BUSINESS')
      await expect(page.getByLabel('Leitweg-ID')).not.toBeVisible()
    })

    test('GOVERNMENT-Partner mit gültiger Leitweg-ID anlegen', async ({ page }) => {
      const suffix = uniqueSuffix()
      const partnerName = `Stadtverwaltung Test ${suffix}`

      await createGovernmentPartner(page, partnerName)

      // Verify partner was created (detail view shows heading)
      await expect(page.getByRole('heading', { name: partnerName })).toBeVisible()
    })

    test('GOVERNMENT-Partner ohne Leitweg-ID wird abgelehnt', async ({ page }) => {
      const suffix = uniqueSuffix()

      await page.goto('/business-partners')
      await page.waitForLoadState('networkidle')

      await page.getByRole('button', { name: /Neuer Geschäftspartner|Neuen Geschäftspartner/i }).click()

      // Select GOVERNMENT type
      await page.getByLabel('Partnertyp').selectOption('GOVERNMENT')

      // Fill required fields but skip Leitweg-ID
      await page.getByLabel('Firmenname / Name').fill(`Amt ohne LeitwegID ${suffix}`)
      await page.getByLabel('Straße und Hausnummer').fill('Amtsweg 5')
      await page.getByLabel('PLZ').fill('10117')
      await page.getByLabel('Stadt').fill('Berlin')

      // Submit without Leitweg-ID
      await page.getByRole('button', { name: 'Geschäftspartner anlegen' }).click()

      // Modal should stay open — form submission blocked by required field
      await expect(page.getByText('Neuen Geschäftspartner anlegen')).toBeVisible()
      // Leitweg-ID input should have required validation state
      const leitwegInput = page.getByLabel('Leitweg-ID')
      await expect(leitwegInput).toBeVisible()
      await expect(leitwegInput).toHaveValue('')
    })
  })

  test.describe('XRechnung in Rechnungsliste und Detailansicht', () => {
    test('XRechnung-Badge "XR" und XML-Button bei GOVERNMENT-Rechnung', async ({ page }) => {
      const suffix = uniqueSuffix()
      const partnerName = `B2G Testamt ${suffix}`

      // Step 1: Create GOVERNMENT partner via UI
      await createGovernmentPartner(page, partnerName)

      // Step 2: Create invoice for GOVERNMENT partner via UI
      await createInvoiceForPartner(page, partnerName)

      // Step 3: Verify XR badge in invoice list
      await page.goto('/invoices')
      await page.waitForLoadState('networkidle')

      const xrBadge = page.locator('.type-badge.type-xrechnung')
      await expect(xrBadge.first()).toBeVisible({ timeout: 10000 })
      await expect(xrBadge.first()).toHaveText('XR')

      // Step 4: Click on the XR invoice to go to detail view
      const xrRow = page.locator('table tbody tr', { has: page.locator('.type-xrechnung') }).first()
      await xrRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      // Step 5: XRechnung XML button should be visible
      await expect(page.getByRole('button', { name: /XRechnung XML/i })).toBeVisible()
    })

    test('XRechnung XML Button ist bei normaler Rechnung NICHT sichtbar', async ({ page }) => {
      // Navigate to invoices list - pick a regular (non-GOVERNMENT) invoice
      await page.goto('/invoices')
      await page.waitForLoadState('networkidle')

      // Find an invoice without XR badge
      const rows = page.locator('table tbody tr')
      const rowCount = await rows.count()

      let regularInvoiceFound = false
      for (let i = 0; i < rowCount; i++) {
        const row = rows.nth(i)
        const hasXR = await row.locator('.type-xrechnung').count()
        if (hasXR === 0) {
          // Click on this regular invoice
          await row.locator('a.invoice-link').click()
          await page.waitForLoadState('networkidle')
          regularInvoiceFound = true
          break
        }
      }

      expect(regularInvoiceFound).toBeTruthy()

      // XRechnung XML button should NOT be visible
      await expect(page.getByRole('button', { name: /XRechnung XML/i })).not.toBeVisible()
      // Regular XML download should still be visible
      await expect(page.getByRole('button', { name: /XML herunterladen/i })).toBeVisible()
    })
  })
})
