import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true  // Wichtig für Docker unter Windows/Mac
    }
    // Kein Proxy - direkter HTTPS-Zugriff auf API-Gateway
    // CORS wird vom API-Gateway gehandhabt
  },
  optimizeDeps: {
    include: ['@vuepic/vue-datepicker']
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild'
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: './src/test/setup.js',
    // E2E-Tests ausschließen - diese laufen via Playwright (npx playwright test)
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/tests/e2e/**'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.spec.js',
        '**/*.test.js'
      ]
    }
  }
})
