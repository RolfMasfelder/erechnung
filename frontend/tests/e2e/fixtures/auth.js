import { test, expect } from '@playwright/test'
import { mockLoginAPI } from './mock-api.js'

/**
 * Login Helper - Authentifizierung für Tests
 * @param {Page} page - Playwright page object
 * @param {string} username - Username (default: 'testuser')
 * @param {string} password - Password (default: 'testpass123')
 * @param {boolean} useMock - Use mock API instead of real backend (default: false)
 */
export async function login(page, username = 'testuser', password = 'testpass123', useMock = false) {
  // Setup mock API only if requested (for unit tests)
  if (useMock) {
    await mockLoginAPI(page.context())
  }

  await page.goto('/login')
  await page.waitForLoadState('networkidle')

  // Formular ausfüllen - verwende Placeholder-basierte Selektoren
  await page.getByPlaceholder('Benutzername eingeben').fill(username)
  await page.getByPlaceholder('Passwort eingeben').fill(password)

  // Submit - verwende Role-basierten Selektor
  await page.getByRole('button', { name: 'Anmelden' }).click()

  // Wait for navigation to complete (login redirects to Dashboard)
  // Increased timeout for slower CI environments
  await page.waitForURL('/', { timeout: 10000 })
  await page.waitForLoadState('networkidle')

  // Check if login was successful by checking localStorage
  const token = await page.evaluate(() => localStorage.getItem('jwt_token'))
  if (!token) {
    // Get any error messages from the page
    const errorMsg = await page.locator('.alert-error, [role="alert"]').textContent().catch(() => 'No error message')
    throw new Error(`Login failed - no JWT token found in localStorage. Error: ${errorMsg}`)
  }
}

/**
 * Logout Helper
 */
export async function logout(page) {
  await page.click('[data-testid="logout-button"]')
  await page.waitForURL('**/login')
}

/**
 * Check if user is authenticated
 * Note: client.js uses 'jwt_token' key for storing access tokens
 */
export async function isAuthenticated(page) {
  const token = await page.evaluate(() => localStorage.getItem('jwt_token'))
  return token !== null
}
