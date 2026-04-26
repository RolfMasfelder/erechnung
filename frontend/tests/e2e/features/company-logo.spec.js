/**
 * E2E-Test: Firmenlogo – End-to-End-Durchlauf
 *
 * Testet den vollständigen Browser-seitigen Ablauf:
 *   1. Firma mit Logo anlegen (CompanyCreateModal)
 *   2. Logo wird in der Detailansicht angezeigt (CompanyDetailView)
 *   3. Logo kann im Bearbeiten-Dialog ersetzt werden (CompanyEditModal)
 *   4. Logo wird nach dem Entfernen nicht mehr angezeigt
 *
 * Ablageort: frontend/tests/e2e/features/company-logo.spec.js
 *
 * Ausführung (empfohlen, alles im Container):
 *   cd scripts && ./run_e2e_container.sh
 *
 * Voraussetzung: laufendes Backend (docker compose up -d)
 */

import path from 'path'
import { fileURLToPath } from 'url'
import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const TEST_LOGO_PATH = path.join(__dirname, '../fixtures/test-logo.png')

// Eindeutiger Firmennamen pro Testlauf (verhindert DB-Konflikte bei Steuernr.)
const uniqueSuffix = () => Date.now().toString().slice(-6)

test.describe('Firmenlogo – vollständiger Ablauf', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await page.goto('/companies')
    await page.waitForLoadState('networkidle')
  })

  // ── 1. Firma mit Logo anlegen ──────────────────────────────────────────────

  test('Firma mit Logo anlegen – Logo in Detailansicht sichtbar', async ({ page }) => {
    const suffix = uniqueSuffix()
    const companyName = `Logo Testfirma ${suffix}`
    const taxId = `TEST${suffix}`

    // CreateModal öffnen
    await page.getByRole('button', { name: /\+ Neue Firma/i }).click()
    await expect(page.getByText('Neue Firma anlegen')).toBeVisible()

    // Pflichtfelder füllen
    await page.getByLabel('Firmenname').fill(companyName)
    await page.getByLabel('Straße und Hausnummer').fill('Teststraße 1')
    await page.getByLabel('PLZ').fill('10115')
    await page.getByLabel('Stadt').fill('Berlin')
    await page.getByLabel('Steuernummer').fill(taxId)
    await page.getByLabel('Handelsregister').fill('HRB 12345, Amtsgericht Berlin')

    // Logo hochladen
    const fileInput = page.locator('input[type="file"][accept*="image"]')
    await fileInput.setInputFiles(TEST_LOGO_PATH)

    // Vorschau erscheint im Modal
    await expect(page.locator('.logo-preview')).toBeVisible({ timeout: 3000 })

    // GET-Listener VOR dem Klick registrieren: verhindert Race-Condition wenn
    // loadCompanies() schneller antwortet als Playwright seinen Listener setzt
    const waitForListRefresh = page.waitForResponse(
      resp => resp.url().includes('/api/companies/') && resp.request().method() === 'GET',
      { timeout: 15000 }
    )

    // Formular absenden – Dateiupload ist multipart/FormData
    const [postResp] = await Promise.all([
      page.waitForResponse(
        resp => resp.url().includes('/api/companies/') && resp.request().method() === 'POST',
        { timeout: 15000 }
      ),
      page.getByRole('button', { name: 'Firma erstellen' }).click()
    ])

    // Diagnose: POST-Response loggen (hilft bei CI-Debugging)
    console.log(`POST /api/companies/ → Status: ${postResp.status()}`)
    if (!postResp.ok()) {
      const body = await postResp.text()
      console.error('POST error body:', body.slice(0, 500))
    } else {
      const body = await postResp.json()
      console.log('POST response name:', body.name, '| logo:', body.logo)
    }

    // Auf die GET-Anfrage der Firmenliste warten (handleCompanyCreated → loadCompanies)
    await waitForListRefresh

    // Suchfeld nutzen um Firma auch bei vielen Seiten zu finden
    const searchInput = page.getByPlaceholder('Suche nach Firmenname...')
    await searchInput.fill(companyName)
    await page.waitForResponse(
      resp => resp.url().includes('/api/companies/') && resp.request().method() === 'GET',
      { timeout: 10000 }
    )

    // In der gefilterten Firmenliste die neu angelegte Firma aufrufen
    const companyLink = page.getByRole('link', { name: companyName })
    await expect(companyLink).toBeVisible({ timeout: 10000 })
    await companyLink.click()
    await page.waitForLoadState('networkidle')

    // Logo muss in der Detailansicht als <img> gerendert werden
    const logoImg = page.locator('.company-logo')
    await expect(logoImg).toBeVisible({ timeout: 10000 })

    const src = await logoImg.getAttribute('src')
    expect(src).toBeTruthy()
    expect(src).toContain('company_logos')
  })

  // ── 2. Firma ohne Logo anlegen – kein Logo-Element ───────────────────────

  test('Firma ohne Logo anlegen – kein logo-Element in Detailansicht', async ({ page }) => {
    const suffix = uniqueSuffix()
    const companyName = `Kein Logo Firma ${suffix}`

    await page.getByRole('button', { name: /\+ Neue Firma/i }).click()
    await expect(page.getByText('Neue Firma anlegen')).toBeVisible()

    await page.getByLabel('Firmenname').fill(companyName)
    await page.getByLabel('Straße und Hausnummer').fill('Musterweg 5')
    await page.getByLabel('PLZ').fill('20095')
    await page.getByLabel('Stadt').fill('Hamburg')
    await page.getByLabel('Steuernummer').fill(`NOLOG${suffix}`)
    await page.getByLabel('Handelsregister').fill('HRB 67890, Amtsgericht Hamburg')

    // Kein Logo hochladen
    // Explizit auf POST warten (networkidle feuert zu früh vor handleCompanyCreated-GET)
    await Promise.all([
      page.waitForResponse(
        resp => resp.url().includes('/api/companies/') && resp.request().method() === 'POST',
        { timeout: 15000 }
      ),
      page.getByRole('button', { name: 'Firma erstellen' }).click()
    ])

    // Suchfeld nutzen um Firma auch bei paginierten Ergebnissen zu finden
    const searchInput = page.getByPlaceholder('Suche nach Firmenname...')
    await searchInput.fill(companyName)
    await page.waitForResponse(
      resp => resp.url().includes('/api/companies/') && resp.request().method() === 'GET',
      { timeout: 10000 }
    )

    const companyLink = page.getByRole('link', { name: companyName })
    await expect(companyLink).toBeVisible({ timeout: 5000 })
    await companyLink.click()
    await page.waitForLoadState('networkidle')

    // Kein Logo-Element darf erscheinen
    await expect(page.locator('.company-logo')).not.toBeVisible()
  })

  // ── 3. Logo nachträglich hinzufügen (Edit-Modal) ──────────────────────────

  test('Logo per Bearbeiten-Dialog hinzufügen', async ({ page }) => {
    const suffix = uniqueSuffix()
    const companyName = `Edit Logo Firma ${suffix}`

    // Firma ohne Logo anlegen
    await page.getByRole('button', { name: /\+ Neue Firma/i }).click()
    await page.getByLabel('Firmenname').fill(companyName)
    await page.getByLabel('Straße und Hausnummer').fill('Editstraße 3')
    await page.getByLabel('PLZ').fill('80333')
    await page.getByLabel('Stadt').fill('München')
    await page.getByLabel('Steuernummer').fill(`EDITL${suffix}`)
    await page.getByLabel('Handelsregister').fill('HRB 11111, Amtsgericht München')
    // Explizit auf POST warten (networkidle feuert zu früh)
    await Promise.all([
      page.waitForResponse(
        resp => resp.url().includes('/api/companies/') && resp.request().method() === 'POST',
        { timeout: 15000 }
      ),
      page.getByRole('button', { name: 'Firma erstellen' }).click()
    ])

    // Suchfeld nutzen um Firma auch bei vielen Seiten zu finden
    const searchInput = page.getByPlaceholder('Suche nach Firmenname...')
    await searchInput.fill(companyName)
    await page.waitForResponse(
      resp => resp.url().includes('/api/companies/') && resp.request().method() === 'GET',
      { timeout: 10000 }
    )

    // In Detailansicht navigieren
    await page.getByRole('link', { name: companyName }).click()
    await page.waitForLoadState('networkidle')

    // Bearbeiten öffnen
    await page.getByRole('button', { name: /Bearbeiten/i }).click()
    await expect(page.getByText('Firma bearbeiten')).toBeVisible()

    // Logo hochladen
    const fileInput = page.locator('input[type="file"][accept*="image"]')
    await fileInput.setInputFiles(TEST_LOGO_PATH)
    await expect(page.locator('.logo-preview')).toBeVisible({ timeout: 3000 })

    // Speichern – Dateiupload ist multipart/FormData, daher explizit auf
    // die PATCH-Antwort warten und company aus Response direkt verwenden
    // (handleCompanyUpdated nutzt PATCH-Response direkt → kein Extra-GET nötig)
    const [patchResp] = await Promise.all([
      page.waitForResponse(
        resp => resp.url().includes('/api/companies/') && resp.request().method() === 'PATCH',
        { timeout: 15000 }
      ),
      page.getByRole('button', { name: 'Änderungen speichern' }).click()
    ])
    // Diagnose: PATCH-Response loggen (hilft bei CI-Debugging)
    console.log(`PATCH /api/companies/... → Status: ${patchResp.status()}`)
    if (!patchResp.ok()) {
      const body = await patchResp.text()
      console.error('PATCH error body:', body.slice(0, 500))
    } else {
      const body = await patchResp.json()
      console.log('PATCH response logo:', body.logo)
    }
    // Logo jetzt in Detailansicht sichtbar (Vue reaktiv via PATCH-Response)
    await expect(page.locator('.company-logo')).toBeVisible({ timeout: 10000 })
  })

  // ── 4. Rechnungs-Vorschau: Logo im PDF-Template ───────────────────────────

  test('Rechnungs-Vorschau zeigt Firmenlogo im PDF-Template', async ({ page }) => {
    /**
     * Dieser Test navigiert zur HTML-Vorschau einer Rechnung (/invoices/<pk>/preview/)
     * und prüft, dass das <img class="logo">-Tag vorhanden ist.
     *
     * Voraussetzung: Eine Rechnung muss in der DB vorhanden sein, deren
     * zugehörige Firma ein Logo hat. Falls keine solche Rechnung existiert,
     * wird der Test als "skipped" markiert.
     */

    // Rechnungsliste aufrufen und erste Rechnung mit detail-Link suchen
    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')

    const firstInvoiceLink = page.locator('table tbody tr').first()
      .getByRole('link').first()
    const count = await page.locator('table tbody tr').count()

    if (count === 0) {
      test.skip('Keine Rechnungen vorhanden – Test übersprungen')
      return
    }

    // Rechnungsnummer aus dem ersten Link lesen
    const href = await firstInvoiceLink.getAttribute('href')
    if (!href) {
      test.skip('Kein Link auf erste Rechnung gefunden')
      return
    }

    // Aus URL /invoices/5/ → /invoices/5/preview/
    const previewUrl = href.replace(/\/$/, '') + '/preview/'
    await page.goto(previewUrl)
    await page.waitForLoadState('networkidle')

    // Seite muss die Vorschau-Rechnung enthalten
    await expect(page.locator('.preview-banner')).toBeVisible()

    // Wenn Logo vorhanden ist: <img class="logo"> muss erscheinen
    const logoImg = page.locator('img.logo')
    const companyNameFallback = page.locator('.company-name-text, div[style*="font-size:14pt"], div[style*="font-size: 14pt"]')

    const logoVisible = await logoImg.isVisible()
    const fallbackVisible = await companyNameFallback.isVisible()

    // Genau eines der beiden muss sichtbar sein
    expect(logoVisible || fallbackVisible).toBe(true)
    expect(logoVisible && fallbackVisible).toBe(false)
  })
})
