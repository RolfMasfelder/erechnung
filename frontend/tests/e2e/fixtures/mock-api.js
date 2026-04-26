/**
 * Mock API Helpers für Playwright Tests
 * Ermöglicht API-Response-Stubbing ohne echtes Backend
 */

/**
 * Mock Invoice List API
 */
export async function mockInvoiceListAPI(context, invoices = [], totalCount = null) {
  await context.route('**/api/invoices/**', async route => {
    const url = new URL(route.request().url())
    const page = parseInt(url.searchParams.get('page') || '1')
    const pageSize = parseInt(url.searchParams.get('page_size') || '10')

    const start = (page - 1) * pageSize
    const end = start + pageSize
    const paginatedInvoices = invoices.slice(start, end)

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: totalCount || invoices.length,
        next: end < invoices.length ? `?page=${page + 1}` : null,
        previous: page > 1 ? `?page=${page - 1}` : null,
        results: paginatedInvoices
      })
    })
  })
}

/**
 * Mock Single Invoice API
 */
export async function mockInvoiceDetailAPI(context, invoice) {
  await context.route(`**/api/invoices/${invoice.id}/`, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(invoice)
    })
  })
}

/**
 * Mock Business Partner List API
 */
export async function mockBusinessPartnerListAPI(context, businessPartners = []) {
  await context.route('**/api/business-partners/**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: businessPartners.length,
        results: businessPartners
      })
    })
  })
}

/**
 * Mock Business Partner Import API
 */
export async function mockBusinessPartnerImportAPI(context, successCount = 3, errors = []) {
  await context.route('**/api/business-partners/import/', async route => {
    // Only intercept POST requests
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        created: successCount,
        updated: 0,
        errors: errors
      })
    })
  })
}

/**
 * Mock Product List API
 */
export async function mockProductListAPI(context, products = []) {
  await context.route('**/api/products/**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: products.length,
        results: products
      })
    })
  })
}

/**
 * Mock Company List API
 */
export async function mockCompanyListAPI(context, companies = []) {
  await context.route('**/api/companies/**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: companies.length,
        results: companies
      })
    })
  })
}

/**
 * Mock Error Response
 */
export async function mockAPIError(context, endpoint, status = 500, errorData = {}) {
  await context.route(endpoint, async route => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: errorData.detail || 'Ein Fehler ist aufgetreten',
        ...errorData
      })
    })
  })
}

/**
 * Mock File Download (PDF/XML)
 */
export async function mockFileDownload(context, endpoint, filename, contentType = 'application/pdf') {
  await context.route(endpoint, async route => {
    await route.fulfill({
      status: 200,
      contentType,
      headers: {
        'Content-Disposition': `attachment; filename="${filename}"`
      },
      body: Buffer.from('Mock file content')
    })
  })
}

/**
 * Mock Login API
 */
export async function mockLoginAPI(context, credentials = { username: 'admin', password: 'admin123' }) {
  await context.route('**/api/auth/token/', async route => {
    let postData
    try {
      postData = route.request().postDataJSON()
    } catch (e) {
      // Fallback if JSON parsing fails
      postData = {}
    }

    // Check credentials
    if (postData && postData.username === credentials.username && postData.password === credentials.password) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access: 'mock-access-token-' + Date.now(),
          refresh: 'mock-refresh-token-' + Date.now(),
          user: {
            id: 1,
            username: credentials.username,
            email: `${credentials.username}@example.com`,
            first_name: 'Test',
            last_name: 'User'
          }
        })
      })
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Ungültige Anmeldedaten'
        })
      })
    }
  })
}

/**
 * Mock Token Refresh
 */
export async function mockTokenRefresh(context, newAccessToken = 'new-token-123') {
  await context.route('**/api/auth/token/refresh/', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access: newAccessToken
      })
    })
  })
}

/**
 * Wait for specific API call
 */
export async function waitForAPI(page, urlPattern, options = {}) {
  return page.waitForResponse(
    response => response.url().includes(urlPattern) &&
                response.status() === (options.status || 200),
    { timeout: options.timeout || 30000 }
  )
}

// Alias exports for convenience
export const mockInvoicesAPI = mockInvoiceListAPI
export const mockBusinessPartnersAPI = mockBusinessPartnerListAPI
