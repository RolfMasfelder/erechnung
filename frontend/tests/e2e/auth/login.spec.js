import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'
import { mockLoginAPI } from '../fixtures/mock-api.js'

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page, context }) => {
    // Don't use API mocking for auth tests - test against real backend
    // Clear storage before each test
    await page.context().clearCookies()
    await page.goto('/login')
  })

  test('should display login form', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('eRechnung System')
    await expect(page.getByPlaceholder('Benutzername eingeben')).toBeVisible()
    await expect(page.getByPlaceholder('Passwort eingeben')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Anmelden' })).toBeVisible()
  })

  test('should login successfully with valid credentials', async ({ page }) => {
    // Fill form with real test user credentials
    await page.getByPlaceholder('Benutzername eingeben').fill('testuser')
    await page.getByPlaceholder('Passwort eingeben').fill('testpass123')

    // Submit
    await page.getByRole('button', { name: 'Anmelden' }).click()

    // Should redirect to dashboard (root route) - increased timeout for CI
    await page.waitForURL('/', { timeout: 8000 })
    // Wait for dashboard to load
    await page.waitForSelector('.page-title', { timeout: 5000 })
    await expect(page.locator('.page-title')).toContainText('Dashboard')
  })

  test('should show error with invalid credentials', async ({ page }) => {
    await page.getByPlaceholder('Benutzername eingeben').fill('invalid')
    await page.getByPlaceholder('Passwort eingeben').fill('wrongpass')

    await page.getByRole('button', { name: 'Anmelden' }).click()

    // Should stay on login page
    await expect(page).toHaveURL(/.*login/)

    // Should show error message - BaseAlert uses .alert class
    await expect(page.locator('.alert').first()).toBeVisible({ timeout: 10000 })
    // Accept both specific error messages and generic HTTP error messages
    await expect(page.locator('.alert')).toContainText(/Ungültige|fehlgeschlagen|credentials|400|failed/i)
  })

  test('should logout successfully', async ({ page }) => {
    // Login first
    await login(page)

    // Click logout button ("Abmelden" in AppHeader)
    await page.getByRole('button', { name: /Abmelden/i }).click()

    // Should redirect to login (increased timeout for slower CI)
    await page.waitForURL('**/login', { timeout: 10000 })
    await expect(page).toHaveURL(/.*login/)
  })

  test('should redirect to login when accessing protected route', async ({ page }) => {
    // Try to access invoices without login
    await page.goto('/invoices')

    // Should redirect to login
    await page.waitForURL(/.*login/)
    await expect(page).toHaveURL(/.*login/)
  })

  test('should redirect to originally requested page after login', async ({ page }) => {
    // Try to access invoices without login
    await page.goto('/invoices')

    // Should redirect to login with redirect parameter
    await page.waitForURL(/.*login/, { timeout: 5000 })
    await page.waitForLoadState('networkidle')

    // Login with real test user
    await page.getByPlaceholder('Benutzername eingeben').fill('testuser')
    await page.getByPlaceholder('Passwort eingeben').fill('testpass123')
    await page.getByRole('button', { name: 'Anmelden' }).click()

    // Should redirect to originally requested page - increased timeout for CI
    await page.waitForURL('**/invoices', { timeout: 15000 })
    await expect(page).toHaveURL(/.*invoices/)
  })
})
