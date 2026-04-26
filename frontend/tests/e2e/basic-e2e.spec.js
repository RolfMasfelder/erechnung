import { test, expect } from '@playwright/test'
import { login } from './fixtures/auth.js'

/**
 * Simple E2E Test - Verify complete flow works
 */
test.describe('Basic E2E Flow', () => {
  test('should login and load invoices', async ({ page }) => {
    // Enable console logging
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('❌ BROWSER ERROR:', msg.text())
      }
    })

    console.log('=== Step 1: Login ===')
    await login(page)

    console.log('=== Step 2: Navigate to invoices ===')
    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')

    // Wait a bit for data to load
    await page.waitForTimeout(2000)

    console.log('=== Step 3: Check for data ===')

// Check if we see the invoice list header (use specific class to avoid ambiguity)
  const pageTitle = page.locator('.page-title')
    await expect(pageTitle).toContainText('Rechnungen')

    // Check if table exists
    const table = page.locator('table')
    await expect(table).toBeVisible()

    // Try to find table rows with a longer timeout
    const rows = page.locator('table tbody tr')
    const rowCount = await rows.count()

    console.log(`Found ${rowCount} table rows`)

    if (rowCount === 0) {
      // Check for "no data" message
      const emptyMsg = page.locator('text=/keine.*rechnungen/i, text=/no.*invoices/i')
      const hasEmptyMsg = await emptyMsg.count() > 0

      if (hasEmptyMsg) {
        console.log('❌ Empty state shown - no invoices found')
        const emptyText = await emptyMsg.textContent()
        console.log('Empty message:', emptyText)
      } else {
        console.log('❌ No rows and no empty message - table not rendering')
      }

      // Take screenshot for debugging
      await page.screenshot({ path: 'test-results/basic-e2e-no-data.png' })
    }

    // Assert we have data
    expect(rowCount).toBeGreaterThan(0)
  })
})
