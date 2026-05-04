/**
 * k6 Load Test: Invoice List API
 *
 * Tests GET /api/invoices/ under load (100 concurrent virtual users).
 * Validates response time and error rate thresholds.
 *
 * Usage:
 *   k6 run scripts/k6/load-test-invoices.js
 *
 * Environment variables:
 *   BASE_URL   - API base URL (default: http://localhost:8000)
 *   API_TOKEN  - Bearer token for authentication
 */

import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const errorRate = new Rate('errors')
const invoiceListDuration = new Trend('invoice_list_duration')

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // ramp up to 20 VUs
    { duration: '1m',  target: 100 },  // ramp up to 100 VUs
    { duration: '2m',  target: 100 },  // hold at 100 VUs
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    // 95th percentile under 500 ms
    http_req_duration: ['p(95)<500'],
    // Error rate below 1%
    errors: ['rate<0.01'],
    // Invoice list specifically under 800 ms (DB query + serialization)
    invoice_list_duration: ['p(95)<800'],
  },
}

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'
const API_TOKEN = __ENV.API_TOKEN || ''

const params = {
  headers: {
    Authorization: `Bearer ${API_TOKEN}`,
    'Content-Type': 'application/json',
  },
}

export default function () {
  // GET /api/invoices/ — paginated list
  const listRes = http.get(`${BASE_URL}/api/invoices/?page=1&page_size=25`, params)
  invoiceListDuration.add(listRes.timings.duration)

  const listOk = check(listRes, {
    'invoice list status 200': (r) => r.status === 200,
    'invoice list has results': (r) => {
      try {
        const body = JSON.parse(r.body)
        return body.results !== undefined
      } catch {
        return false
      }
    },
    'invoice list response time < 800ms': (r) => r.timings.duration < 800,
  })
  errorRate.add(!listOk)

  // GET /api/invoices/?status=SENT — filtered query (tests DB index usage)
  const filteredRes = http.get(`${BASE_URL}/api/invoices/?status=SENT&page_size=10`, params)
  const filteredOk = check(filteredRes, {
    'filtered invoice list status 200': (r) => r.status === 200,
    'filtered response time < 500ms': (r) => r.timings.duration < 500,
  })
  errorRate.add(!filteredOk)

  sleep(1)
}
