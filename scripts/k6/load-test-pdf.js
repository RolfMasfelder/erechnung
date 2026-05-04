/**
 * k6 Load Test: PDF/XML Generation
 *
 * Tests on-demand PDF and XRechnung XML generation under concurrent load.
 * Validates generation time and error rate for the download endpoints.
 *
 * Usage:
 *   k6 run scripts/k6/load-test-pdf.js
 *
 * Prerequisites:
 *   - At least one SENT invoice must exist in the target environment.
 *   - Set INVOICE_IDS to a comma-separated list of invoice IDs, e.g.
 *     k6 run -e INVOICE_IDS="1,2,3,4,5" scripts/k6/load-test-pdf.js
 *
 * Environment variables:
 *   BASE_URL    - API base URL (default: http://localhost:8000)
 *   API_TOKEN   - Bearer token for authentication
 *   INVOICE_IDS - Comma-separated invoice IDs to test against (default: "1")
 */

import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const errorRate = new Rate('errors')
const pdfDuration = new Trend('pdf_generation_duration')
const xmlDuration = new Trend('xml_generation_duration')

export const options = {
  stages: [
    { duration: '20s', target: 10 },   // ramp up — PDF generation is CPU-intensive
    { duration: '1m',  target: 30 },   // hold at 30 VUs (realistic concurrent PDF requests)
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    // PDF generation: p(95) under 3 seconds (weasyprint + ZUGFeRD embedding)
    pdf_generation_duration: ['p(95)<3000'],
    // XML generation: p(95) under 1 second
    xml_generation_duration: ['p(95)<1000'],
    // Overall error rate below 1%
    errors: ['rate<0.01'],
  },
}

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'
const API_TOKEN = __ENV.API_TOKEN || ''
const INVOICE_IDS = (__ENV.INVOICE_IDS || '1').split(',').map((id) => parseInt(id, 10))

const params = {
  headers: {
    Authorization: `Bearer ${API_TOKEN}`,
    'Content-Type': 'application/json',
  },
}

/**
 * Pick a random invoice ID from the configured list.
 * @returns {number}
 */
function randomInvoiceId() {
  return INVOICE_IDS[Math.floor(Math.random() * INVOICE_IDS.length)]
}

export default function () {
  const invoiceId = randomInvoiceId()

  // PDF download (triggers on-demand generation if not cached)
  const pdfRes = http.get(`${BASE_URL}/api/invoices/${invoiceId}/download_pdf/`, params)
  pdfDuration.add(pdfRes.timings.duration)

  const pdfOk = check(pdfRes, {
    'PDF download status 200': (r) => r.status === 200,
    'PDF content-type is PDF': (r) =>
      (r.headers['Content-Type'] || '').includes('application/pdf'),
    'PDF response time < 3s': (r) => r.timings.duration < 3000,
  })
  errorRate.add(!pdfOk)

  sleep(0.5)

  // XRechnung XML download
  const xmlRes = http.get(`${BASE_URL}/api/invoices/${invoiceId}/download_xml/`, params)
  xmlDuration.add(xmlRes.timings.duration)

  const xmlOk = check(xmlRes, {
    'XML download status 200': (r) => r.status === 200,
    'XML content-type is XML': (r) =>
      (r.headers['Content-Type'] || '').includes('xml'),
    'XML response time < 1s': (r) => r.timings.duration < 1000,
  })
  errorRate.add(!xmlOk)

  sleep(1)
}
