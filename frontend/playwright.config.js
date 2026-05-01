import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright Configuration für eRechnung Frontend
 * Container-Only Setup mit Docker Compose Integration
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Serial execution — tests share a database; parallel workers cause race conditions. */
  workers: 1,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list']
  ],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL for all tests - Docker Compose Setup */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',

    /* Ignore HTTPS errors for self-signed certs in development */
    ignoreHTTPSErrors: true,

    /* Timeout for each action */
    actionTimeout: 15000,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Viewport für Desktop-Tests
        viewport: { width: 1280, height: 720 }
      },
    },

    // Weitere Browser können installiert werden mit:
    // npx playwright install firefox webkit
    // Dann auskommentieren:
    /*
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1280, height: 720 }
      },
    },

    // Mobile viewports für responsive Tests
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5']
      },
    },
    */

    /* Test against branded browsers - optional
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
    {
      name: 'Google Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    },
    */
  ],

  /* Run your local dev server before starting the tests - NOT USED in Docker setup */
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://127.0.0.1:5173',
  //   reuseExistingServer: !process.env.CI,
  // },

  /* Global timeout for entire test run */
  globalTimeout: process.env.CI ? 1200000 : 1500000, // 20min CI, 25min local

  /* Timeout for each test */
  timeout: 60000, // 1 minute per test

  /* Expect timeout for assertions */
  expect: {
    timeout: 10000
  }
})
