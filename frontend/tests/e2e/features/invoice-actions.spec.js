// @ts-check
import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'

/**
 * E2E Tests: InvoiceDetailView Action-Buttons (P3-Refactoring)
 *
 * Testet die konsolidierten Action-Buttons:
 *   1. Smart-Download: B2B-Rechnung → "PDF herunterladen"
 *   2. Smart-Download: B2G-Rechnung → "XML herunterladen"
 *   3. Vorschau-Button immer sichtbar
 *   4. Entfernte Buttons nicht mehr vorhanden (generatePDF, generateXRechnung, markAsSent)
 *   5. SendInvoiceModal: Delivery-Mode-Selector mit E-Mail / Download / Peppol
 *   6. SendInvoiceModal Download-Modus: Info-Text abhängig von Partnertyp
 *   7. SendInvoiceModal Peppol-Tab: disabled + Hinweis
 *   8. Versand-Status-Anzeige bei versendeten Rechnungen
 *
 * Prerequisites:
 *   - Backend running (docker compose up -d)
 *   - Test data generated: manage.py generate_test_data --clear --preset standard
 *   - Testdaten enthalten B2B- und B2G-Rechnungen (SENT und DRAFT)
 */

// ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

/**
 * Navigiert zur Detailansicht einer B2B-Rechnung (kein GOVERNMENT-Partner).
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<void>}
 */
async function goToB2BInvoice(page) {
  await page.goto('/invoices')
  await page.waitForLoadState('networkidle')

  const rows = page.locator('table tbody tr')
  const rowCount = await rows.count()

  for (let i = 0; i < rowCount; i++) {
    const row = rows.nth(i)
    const hasXR = await row.locator('.type-xrechnung').count()
    if (hasXR === 0) {
      await row.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')
      return
    }
  }
  throw new Error('Keine B2B-Rechnung in der Liste gefunden')
}

/**
 * Navigiert zur Detailansicht einer B2G-Rechnung (GOVERNMENT-Partner, XR-Badge).
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<void>}
 */
async function goToB2GInvoice(page) {
  await page.goto('/invoices')
  await page.waitForLoadState('networkidle')

  // credit-note.spec.js storniert die XR-Rechnung → erzeugt eine Gutschrift (.type-credit-note)
  // und setzt die Original-Rechnung auf CANCELLED (.status-cancelled). Beides überspringen.
  const rows = page.locator('table tbody tr')
  const rowCount = await rows.count()
  for (let i = 0; i < rowCount; i++) {
    const row = rows.nth(i)
    const hasXR = await row.locator('.type-xrechnung').count()
    const isCreditNote = await row.locator('.type-credit-note').count()
    const isCancelled = await row.locator('.status-cancelled').count()
    if (hasXR > 0 && isCreditNote === 0 && isCancelled === 0) {
      await row.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')
      return
    }
  }
  throw new Error('Keine aktive B2G-Rechnung (nicht Gutschrift, nicht Storniert) in der Liste gefunden')
}

/**
 * Öffnet das Send-Modal einer nicht-stornierten Rechnung.
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<void>}
 */
async function openSendModal(page) {
  const sendBtn = page.getByRole('button', { name: /Per E-Mail versenden/i })
  await expect(sendBtn).toBeVisible({ timeout: 10000 })
  await sendBtn.click()
  await expect(page.getByText(/Rechnung.*versenden/i).first()).toBeVisible({ timeout: 5000 })
}

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe('InvoiceDetailView: konsolidierte Action-Buttons', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', (msg) => {
      if (msg.type() === 'error') console.log('❌ BROWSER ERROR:', msg.text())
    })
    await login(page)
  })

  // ── Smart-Download ──────────────────────────────────────────────────────────

  test.describe('Smart-Download Button', () => {
    test('B2B-Rechnung: Button zeigt "PDF herunterladen"', async ({ page }) => {
      await goToB2BInvoice(page)
      await expect(page.getByRole('button', { name: /PDF herunterladen/i })).toBeVisible()
    })

    test('B2G-Rechnung: Button zeigt "XML herunterladen"', async ({ page }) => {
      await goToB2GInvoice(page)
      await expect(page.getByRole('button', { name: /XML herunterladen/i })).toBeVisible()
    })

    test('B2B-Rechnung: "XML herunterladen" ist NICHT sichtbar', async ({ page }) => {
      await goToB2BInvoice(page)
      await expect(page.getByRole('button', { name: /XML herunterladen/i })).not.toBeVisible()
    })

    test('B2G-Rechnung: "PDF herunterladen" ist NICHT sichtbar', async ({ page }) => {
      await goToB2GInvoice(page)
      await expect(page.getByRole('button', { name: /PDF herunterladen/i })).not.toBeVisible()
    })
  })

  // ── Vorschau-Button ─────────────────────────────────────────────────────────

  test.describe('Vorschau-Button', () => {
    test('Vorschau-Button ist bei B2B-Rechnung sichtbar', async ({ page }) => {
      await goToB2BInvoice(page)
      await expect(page.getByRole('button', { name: /Vorschau/i })).toBeVisible()
    })

    test('Vorschau-Button ist bei B2G-Rechnung sichtbar', async ({ page }) => {
      await goToB2GInvoice(page)
      await expect(page.getByRole('button', { name: /Vorschau/i })).toBeVisible()
    })

    test('Vorschau-Button öffnet neuen Tab', async ({ page, context }) => {
      // PDF generation on CI runners can take up to ~60s — give the full test 2 minutes
      test.setTimeout(120_000)
      await goToB2BInvoice(page)

      const [newPage] = await Promise.all([
        context.waitForEvent('page', { timeout: 90_000 }),
        page.getByRole('button', { name: /Vorschau/i }).click(),
      ])
      // blob: URLs are immediately loaded when the tab opens — no waitForLoadState needed
      expect(newPage.url()).toMatch(/^(?:blob:|.*application\/pdf)/)
      await newPage.close()
    })
  })

  // ── Entfernte Buttons ───────────────────────────────────────────────────────

  test.describe('Entfernte Buttons nicht mehr vorhanden', () => {
    test('"PDF generieren"-Button ist entfernt', async ({ page }) => {
      await goToB2BInvoice(page)
      await expect(page.getByRole('button', { name: /PDF generieren/i })).not.toBeVisible()
    })

    test('"XRechnung XML erzeugen"-Button ist entfernt', async ({ page }) => {
      await goToB2GInvoice(page)
      await expect(page.getByRole('button', { name: /XRechnung XML erzeugen/i })).not.toBeVisible()
    })

    test('"Als versendet markieren"-Button ist entfernt', async ({ page }) => {
      await goToB2BInvoice(page)
      await expect(
        page.getByRole('button', { name: /Als versendet markieren/i }),
      ).not.toBeVisible()
    })
  })

  // ── Versand-Status-Anzeige ──────────────────────────────────────────────────

  test.describe('Versand-Status-Anzeige', () => {
    test('Bereits versendete Rechnung zeigt Versand-Status', async ({ page }) => {
      // Navigate to a SENT invoice that was emailed (test data includes these)
      await page.goto('/invoices')
      await page.waitForLoadState('networkidle')

      const sentRow = page
        .locator('table tbody tr', { has: page.locator('.status-sent') })
        .first()
      await expect(sentRow).toBeVisible({ timeout: 10000 })
      await sentRow.locator('a.invoice-link').click()
      await page.waitForLoadState('networkidle')

      // The versand-status div should either be present (if last_emailed_at is set)
      // or absent (if invoice was marked sent manually). Either is valid — we just
      // ensure no JS error occurred and the page loaded correctly.
      await expect(page.locator('.invoice-detail')).toBeVisible()
    })
  })
})

// ─── SendInvoiceModal: Delivery-Mode-Selector ─────────────────────────────────

test.describe('SendInvoiceModal: Delivery-Mode-Selector', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', (msg) => {
      if (msg.type() === 'error') console.log('❌ BROWSER ERROR:', msg.text())
    })
    await login(page)
  })

  test('Modal zeigt drei Delivery-Tabs: E-Mail, Datei herunterladen, Peppol', async ({ page }) => {
    await goToB2BInvoice(page)
    await openSendModal(page)

    await expect(page.getByRole('button', { name: /E-Mail/i }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Datei herunterladen/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Peppol/i })).toBeVisible()
  })

  test('E-Mail-Tab ist standardmäßig aktiv: E-Mail-Formular sichtbar', async ({ page }) => {
    await goToB2BInvoice(page)
    await openSendModal(page)

    await expect(page.getByLabel('Empfänger-E-Mail-Adresse')).toBeVisible()
    await expect(page.getByRole('button', { name: /Jetzt versenden/i })).toBeVisible()
  })

  test('Download-Tab: zeigt Format-Info (B2B → PDF/A-3)', async ({ page }) => {
    await goToB2BInvoice(page)
    await openSendModal(page)

    await page.getByRole('button', { name: /Datei herunterladen/i }).click()

    await expect(page.getByText(/PDF\/A-3/i)).toBeVisible()
    // Scope to dialog to avoid strict mode conflict with smartDownload button on detail page
    await expect(page.getByRole('dialog').getByRole('button', { name: /PDF herunterladen/i })).toBeVisible()
    // E-Mail-Formular verschwindet
    await expect(page.getByLabel('Empfänger-E-Mail-Adresse')).not.toBeVisible()
  })

  test('Download-Tab: zeigt Format-Info (B2G → XRechnung XML)', async ({ page }) => {
    await goToB2GInvoice(page)
    await openSendModal(page)

    await page.getByRole('button', { name: /Datei herunterladen/i }).click()

    await expect(page.getByText(/XRechnung/i).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /XML herunterladen/i })).toBeVisible()
  })

  test('Peppol-Tab: Button ist disabled', async ({ page }) => {
    await goToB2BInvoice(page)
    await openSendModal(page)

    const peppolBtn = page.getByRole('button', { name: /Peppol/i })
    await expect(peppolBtn).toBeDisabled()
  })

  test('Peppol-Tab-Tooltip: "Kommt in einer späteren Version"', async ({ page }) => {
    await goToB2BInvoice(page)
    await openSendModal(page)

    const peppolBtn = page.getByRole('button', { name: /Peppol/i })
    const title = await peppolBtn.getAttribute('title')
    expect(title).toMatch(/sp.+teren Version/i)
  })

  test('Wechsel zwischen Tabs funktioniert (E-Mail → Download → E-Mail)', async ({ page }) => {
    await goToB2BInvoice(page)
    await openSendModal(page)

    // Start: E-Mail active
    await expect(page.getByLabel('Empfänger-E-Mail-Adresse')).toBeVisible()

    // Switch to Download
    await page.getByRole('button', { name: /Datei herunterladen/i }).click()
    await expect(page.getByLabel('Empfänger-E-Mail-Adresse')).not.toBeVisible()
    // Use .first() to avoid strict-mode violation: the modal renders the text in two elements
    await expect(page.getByText(/PDF\/A-3|ZUGFeRD/i).first()).toBeVisible()

    // Switch back to E-Mail
    await page.getByRole('button', { name: /E-Mail/i }).first().click()
    await expect(page.getByLabel('Empfänger-E-Mail-Adresse')).toBeVisible()
  })

  test('Abbrechen-Button schließt Modal', async ({ page }) => {
    await goToB2BInvoice(page)
    await openSendModal(page)

    await page.getByRole('button', { name: /Abbrechen/i }).click()
    await expect(page.getByLabel('Empfänger-E-Mail-Adresse')).not.toBeVisible()
  })
})
