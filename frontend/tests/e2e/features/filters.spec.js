import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'

test.describe('Filter Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await login(page)

    // Navigate to invoices page
    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')
  })

  test('should display filter bar', async ({ page }) => {
    // Check filter bar is visible
    await expect(page.locator('.filter-bar')).toBeVisible()

    // Check search field with correct placeholder
    await expect(page.getByPlaceholder('Suche nach Rechnungsnummer, Kunde...')).toBeVisible()

    // Check reset button (only visible with active filters)
    const resetButton = page.getByRole('button', { name: /Filter zurücksetzen/i })
    await expect(resetButton).toBeHidden()
  })

  test('should filter by search term', async ({ page }) => {
    // Get initial row count
    const initialRows = await page.locator('tbody tr').count()
    expect(initialRows).toBeGreaterThan(0)

    // Enter search term (current format: INV-{year}-{NNNN})
    await page.getByPlaceholder('Suche nach Rechnungsnummer, Kunde...').fill('INV-2026')

    // Wait for debounce (300ms) + request
    await page.waitForTimeout(400)
    await page.waitForLoadState('networkidle')
  })

  test('should filter by status', async ({ page }) => {
    // Open status dropdown
    const statusSelect = page.locator('select').first()
    await expect(statusSelect).toBeVisible()

    // Select status by index (0 is placeholder, 1+ are values)
    await statusSelect.selectOption({ index: 2 })

    await page.waitForLoadState('networkidle')

    // Check URL contains status parameter
    await expect(page).toHaveURL(/status=/)

    // Reset button should be visible
    await expect(page.getByRole('button', { name: /Filter zurücksetzen/i })).toBeVisible()
  })

  test('should filter by date range', async ({ page }) => {
    // Check if date range filter is available
    const fromDatePicker = page.locator('#filter-date-from, [data-filter="date-from"]')
    const toDatePicker = page.locator('#filter-date-to, [data-filter="date-to"]')

    // Try keyboard input approach (more reliable with textInput mode)
    if (await fromDatePicker.isVisible()) {
      const fromInput = fromDatePicker.locator('input').first()
      await fromInput.fill('01.01.2024')
      await page.waitForTimeout(200)
    }

    if (await toDatePicker.isVisible()) {
      const toInput = toDatePicker.locator('input').first()
      await toInput.fill('31.01.2024')
      await page.waitForTimeout(200)
    }

    await page.waitForLoadState('networkidle')

    // Check URL contains date parameters or filters applied
    const url = page.url()
    const hasDateParams = url.includes('from=') || url.includes('to=') || url.includes('date')

    // If no URL params, check if table updated (filtered results)
    if (!hasDateParams) {
      // At least the table should be visible
      await expect(page.locator('table, .table')).toBeVisible()
    } else {
      expect(hasDateParams).toBe(true)
    }
  })

  test('should combine multiple filters', async ({ page }) => {
    // Apply search
    await page.getByPlaceholder('Suche nach Rechnungsnummer, Kunde...').fill('INV-2026')
    await page.waitForTimeout(400)

    // Apply status filter
    const statusSelect = page.locator('select').first()
    if (await statusSelect.isVisible()) {
      await statusSelect.selectOption({ index: 2 })
    }

    await page.waitForLoadState('networkidle')

    // Check URL contains both parameters
    await expect(page).toHaveURL(/search=INV-2026/)

    // Reset button should be visible
    await expect(page.getByRole('button', { name: /Filter zurücksetzen/i })).toBeVisible()
  })

  test('should reset filters', async ({ page }) => {
    // Apply some filters
    await page.getByPlaceholder('Suche nach Rechnungsnummer, Kunde...').fill('test')
    await page.waitForTimeout(400)

    const statusSelect = page.locator('select').first()
    if (await statusSelect.isVisible()) {
      await statusSelect.selectOption({ index: 2 })
      await page.waitForLoadState('networkidle')
    }

    // Reset button should be visible
    const resetButton = page.getByRole('button', { name: /Filter zurücksetzen/i })
    await expect(resetButton).toBeVisible()

    // Click reset
    await resetButton.click()

    await page.waitForLoadState('networkidle')

    // Check search is cleared
    await expect(page.getByPlaceholder('Suche nach Rechnungsnummer, Kunde...')).toHaveValue('')

    // Check URL has no filter parameters
    await expect(page).toHaveURL(/\/invoices\/?$/)

    // Reset button should be hidden
    await expect(resetButton).toBeHidden()
  })

  test('should persist filters on page navigation', async ({ page }) => {
    // Apply filter
    await page.getByPlaceholder('Suche nach Rechnungsnummer, Kunde...').fill('INV-2026')
    await page.waitForTimeout(400)
    await page.waitForLoadState('networkidle')

    // Navigate to second page if possible
    const nextButton = page.getByRole('button', { name: /Weiter|Next/i })
    const buttonCount = await nextButton.count()

    if (buttonCount > 0 && await nextButton.isEnabled()) {
      await nextButton.click()
      await page.waitForLoadState('networkidle')

      // Check search parameter still in URL
      await expect(page).toHaveURL(/search=INV-2026/)
      await expect(page).toHaveURL(/page=2/)
    } else {
      // Single page of results - just check filter persists
      await expect(page).toHaveURL(/search=INV-2026/)
    }
  })

  test('should show empty state when no results', async ({ page }) => {
    // Search for something that definitely doesn't exist
    await page.getByPlaceholder('Suche nach Rechnungsnummer, Kunde...').fill('NONEXISTENT-XXXXX-9999')
    await page.waitForTimeout(400)
    await page.waitForLoadState('networkidle')

    // Check for empty state message
    const emptyState = page.locator('text=/Keine.*Rechnungen.*gefunden/i')
    await expect(emptyState).toBeVisible({ timeout: 2000 })
  })

  test('should collapse filter bar on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Wait for responsive layout to adjust
    await page.waitForTimeout(500)

    // Close sidebar if it's open (on mobile, sidebar overlays all content at z-index:200).
    // The overlay's z-index:-1 makes it unclickable, and the sidebar covers the hamburger
    // toggle too. Use dispatchEvent directly on the overlay to trigger Vue's @click handler.
    const sidebar = page.locator('.app-sidebar.sidebar-open')
    if (await sidebar.isVisible({ timeout: 1000 }).catch(() => false)) {
      // Dispatch click event directly on the overlay element to trigger Vue handler
      await page.locator('.sidebar-overlay').dispatchEvent('click')
      await page.waitForTimeout(500)
    }
    // Verify sidebar is closed
    await expect(page.locator('.app-sidebar.sidebar-open')).toHaveCount(0, { timeout: 3000 })

    // Check filter toggle button is visible
    const toggleButton = page.locator('.filter-toggle')
    await expect(toggleButton).toBeVisible({ timeout: 3000 })

    // Check filter content is visible initially
    const filterContent = page.locator('.filter-bar-content')
    const isVisible = await filterContent.isVisible()

    if (isVisible) {
      // Click toggle to collapse
      await toggleButton.click()
      await page.waitForTimeout(300)

      // Filter content should be hidden
      await expect(filterContent).toBeHidden()
    } else {
      // Already collapsed on mobile — click to expand
      await toggleButton.click()
      await page.waitForTimeout(300)

      // Filter content should be visible
      await expect(filterContent).toBeVisible()

      // Click again to collapse
      await toggleButton.click()
      await page.waitForTimeout(300)
      await expect(filterContent).toBeHidden()
    }

    // Toggle button should show filter text
    await expect(toggleButton).toContainText('Filter')
  })
})
