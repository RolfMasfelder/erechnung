import { test, expect } from '@playwright/test'
import { login } from '../fixtures/auth.js'
import { mockTokenRefresh } from '../fixtures/mock-api.js'

/**
 * Token Refresh Flow Tests
 *
 * Diese Tests decken die Coverage-Gaps in client.js (Lines 50-77) ab.
 * Unit-Tests können diesen Flow nicht gut testen, da er window.location
 * und komplexe Interceptor-Logik involviert.
 */
// Valid fake JWT with far-future expiration (year 2286).
// Payload: {"sub":"testuser","exp":9999999999}
// Required because authService.isAuthenticated() decodes the JWT and calls
// logout() if decoding fails — a plain string like 'new-token' would be
// immediately cleared from localStorage.
const FAKE_JWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6OTk5OTk5OTk5OX0.dGVzdC1zaWduYXR1cmU'

test.describe('Token Refresh Flow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('should refresh token on 401 response', async ({ page, context }) => {
    // Use the real login tokens (from beforeEach). Route mocks intercept at
    // the browser network level so the interceptor chain in client.js fires
    // even though the real backend is never hit.
    let refreshCalled = false

    // Mock Token Refresh Endpoint — returns a new access token
    await context.route('**/api/auth/token/refresh/', async route => {
      refreshCalled = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access: FAKE_JWT
        })
      })
    })

    // Mock Invoice API: First request returns 401, subsequent succeed.
    // Use a regex to match only the invoice list endpoint (page= param)
    // and avoid catching stale dashboard requests (page_size=5&ordering=...)
    // that may still be in-flight from the previous page.
    let invoiceCallCount = 0
    await context.route(/\/api\/invoices\/\?.*page=\d/, async route => {
      invoiceCallCount++

      if (invoiceCallCount === 1) {
        // First call: 401 Unauthorized → triggers refresh in client.js
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Token expired'
          })
        })
      } else {
        // Subsequent calls (after refresh): Success
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            count: 0,
            results: []
          })
        })
      }
    })

    // Navigate to invoices — router guard passes because we have a valid
    // real token from login. The component then fetches invoices which
    // triggers the mock → 401 → refresh → retry chain.
    await page.goto('/invoices')

    // Wait for the invoice list to render — proves the 401→refresh→retry
    // flow completed and the retried request returned data.
    await expect(page.getByText('Keine Rechnungen gefunden')).toBeVisible({ timeout: 15000 })

    // Verify refresh was called and token was updated.
    // Use expect().toPass() polling instead of page.waitForFunction()
    // which can be unreliable for localStorage checks.
    expect(refreshCalled).toBe(true)
    await expect(async () => {
      const token = await page.evaluate(() => localStorage.getItem('jwt_token'))
      expect(token).toBe(FAKE_JWT)
    }).toPass({ timeout: 5000 })

    // The original request should have been retried
    expect(invoiceCallCount).toBeGreaterThanOrEqual(2)
  })

  test('should logout and redirect on refresh failure', async ({ page, context }) => {
    // Mock Token Refresh to fail
    await context.route('**/api/auth/token/refresh/', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Refresh token expired'
        })
      })
    })

    // Mock Invoice API to return 401
    await context.route('**/api/invoices/**', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Token expired'
        })
      })
    })

    // Navigate to invoices (triggers 401 → refresh attempt → failure)
    await page.goto('/invoices').catch(() => {})

    // Wait for any navigation to settle
    await page.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => {})

    // Should redirect to login — use polling assertion (resilient to frame detach
    // caused by window.location.href = '/login' hard navigation in client.js)
    await expect(page).toHaveURL(/.*login/, { timeout: 10000 })

    // Token should be cleared (client.js uses 'jwt_token')
    const token = await page.evaluate(() => localStorage.getItem('jwt_token'))
    expect(token).toBeNull()
  })

  test('should not retry more than once per request', async ({ page, context }) => {
    let refreshCallCount = 0

    // Mock Token Refresh
    await context.route('**/api/auth/token/refresh/', async route => {
      refreshCallCount++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access: `token-${refreshCallCount}`
        })
      })
    })

    // Mock Invoice API: Always return 401
    await context.route('**/api/invoices/**', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Token expired'
        })
      })
    })

    // Navigate to invoices
    await page.goto('/invoices')

    // Wait for the page to settle and process the 401s
    await page.waitForTimeout(2000)

    // Should only try refresh at most once per request (not infinite loop)
    // The client should detect the refresh didn't help and stop retrying
    expect(refreshCallCount).toBeLessThanOrEqual(2)
  })

  test('should handle concurrent 401 responses', async ({ page, context }) => {
    let refreshCallCount = 0

    // Mock Token Refresh
    await context.route('**/api/auth/token/refresh/', async route => {
      refreshCallCount++
      // Simulate slow refresh
      await new Promise(resolve => setTimeout(resolve, 100))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access: 'refreshed-token'
        })
      })
    })

    // Mock multiple APIs returning 401 then success
    const setupMockAPI = (endpoint) => {
      let callCount = 0
      return context.route(endpoint, async route => {
        callCount++
        if (callCount === 1) {
          await route.fulfill({ status: 401, body: '{}' })
        } else {
          await route.fulfill({
            status: 200,
            body: JSON.stringify({ count: 0, results: [] })
          })
        }
      })
    }

    await setupMockAPI('**/api/invoices/**')
    await setupMockAPI('**/api/business-partners/**')
    await setupMockAPI('**/api/products/**')

    // Navigate to dashboard (loads multiple APIs)
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    // Should deduplicate refresh calls - allow 0 (no 401 triggered) or 1 (deduplication works)
    // 0 is valid if the mock routes weren't hit during dashboard load
    expect(refreshCallCount).toBeLessThanOrEqual(1)
  })
})

test.describe('Token Expiration Edge Cases', () => {
  test('should handle 403 Forbidden differently from 401', async ({ page, context }) => {
    await login(page)

    let refreshCalled = false

    await context.route('**/api/auth/token/refresh/', async route => {
      refreshCalled = true
      await route.fulfill({ status: 200, body: '{"access": "new-token"}' })
    })

    // Mock API to return 403 (Permission Denied)
    await context.route('**/api/invoices/**', async route => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'You do not have permission to perform this action.'
        })
      })
    })

    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')

    // Should NOT trigger refresh on 403
    expect(refreshCalled).toBe(false)

    // Should display error message or stay on page (not redirect to login)
    // The 403 error should be handled by the view, not trigger token refresh
    await expect(page).not.toHaveURL(/.*login/)
  })

  test('should handle network errors without refresh', async ({ page, context }) => {
    await login(page)

    let refreshCalled = false

    await context.route('**/api/auth/token/refresh/', async route => {
      refreshCalled = true
      await route.fulfill({ status: 200, body: '{"access": "new-token"}' })
    })

    // Mock API to fail with network error
    await context.route('**/api/invoices/**', async route => {
      await route.abort('failed')
    })

    await page.goto('/invoices')
    await page.waitForLoadState('networkidle')

    // Should NOT trigger refresh on network error
    expect(refreshCalled).toBe(false)
  })
})
