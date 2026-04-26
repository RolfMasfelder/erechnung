import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import DashboardView from '../DashboardView.vue'
import { invoiceService } from '@/api/services/invoiceService'
import { statsService } from '@/api/services/statsService'

vi.mock('@/api/services/invoiceService', () => ({
  invoiceService: {
    getAll: vi.fn()
  }
}))

vi.mock('@/api/services/statsService', () => ({
  statsService: {
    getStats: vi.fn()
  }
}))

describe('DashboardView', () => {
  let wrapper
  let router

  const mockStats = {
    invoices: {
      total: 42,
      by_status: {
        draft: 5,
        sent: 8,
        paid: 25,
        cancelled: 2,
        overdue: 2
      },
      total_amount: 12450.00,
      paid_amount: 7350.00,
      outstanding_amount: 5100.00
    },
    business_partners: { total: 15, active: 15 },
    products: { total: 30, active: 28 },
    companies: { total: 2, active: 2 }
  }

  const mockRecentInvoices = {
    count: 10,
    results: [
      {
        id: 1,
        invoice_number: 'INV-001',
        customer_name: 'Test Customer',
        customer_details: { id: 101, name: 'Test Customer' },
        issue_date: '2025-01-15',
        total_amount: 238.00,
        status: 'PAID'
      },
      {
        id: 2,
        invoice_number: 'INV-002',
        customer_name: 'Another Customer',
        customer_details: { id: 102, name: 'Another Customer' },
        issue_date: '2025-01-20',
        total_amount: 119.00,
        status: 'SENT'
      }
    ]
  }

  beforeEach(async () => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'Dashboard', component: DashboardView },
        { path: '/invoices', name: 'InvoiceList', component: { template: '<div>Invoices</div>' } },
        { path: '/invoices/:id', name: 'InvoiceDetail', component: { template: '<div>Detail</div>' } },
        { path: '/business-partners/:id', name: 'BusinessPartnerDetail', component: { template: '<div>Partner</div>' } }
      ]
    })

    await router.push('/')
    await router.isReady()

    vi.clearAllMocks()
    statsService.getStats.mockResolvedValue(mockStats)
    invoiceService.getAll.mockResolvedValue(mockRecentInvoices)
  })

  it('renders dashboard view', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    expect(wrapper.find('h1').text()).toBe('Dashboard')
  })

  it('loads recent invoices on mount', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    expect(statsService.getStats).toHaveBeenCalled()
    expect(invoiceService.getAll).toHaveBeenCalledWith(
      expect.objectContaining({
        page_size: 5
      })
    )
  })

  it('displays statistics from API', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('42') // Total invoices
    expect(text).toContain('15') // Total customers (active)
    expect(text).toContain('25') // Paid invoices
    expect(text).toContain('10') // Open invoices (sent + overdue = 8 + 2)
  })

  it('displays statistics cards', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('Gesamt Rechnungen')
    expect(text).toContain('Offene Rechnungen')
    expect(text).toContain('Bezahlte Rechnungen')
  })

  it('displays recent invoices table', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const text = wrapper.text()
    expect(text).toContain('INV-001')
    expect(text).toContain('Test Customer')
    expect(text).toContain('Bezahlt')
    expect(text).toContain('Versendet')

    const statusBadges = wrapper.findAll('.status-badge')
    expect(statusBadges.some(badge => badge.classes().includes('status-paid'))).toBe(true)
    expect(statusBadges.some(badge => badge.classes().includes('status-sent'))).toBe(true)
  })

  it('sorts recent invoices when clicking sortable header', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const getFirstInvoiceNumber = () => {
      const firstRow = wrapper.findAll('tbody tr')[0]
      if (!firstRow) return ''
      const invoiceLink = firstRow.find('.invoice-link')
      return invoiceLink.exists() ? invoiceLink.text() : firstRow.text()
    }

    expect(getFirstInvoiceNumber()).toContain('INV-001')

    const invoiceHeader = wrapper.findAll('th').find(th => th.text().includes('Rechnungsnr.'))
    expect(invoiceHeader).toBeTruthy()

    await invoiceHeader.trigger('click')
    await wrapper.vm.$nextTick()
    expect(getFirstInvoiceNumber()).toContain('INV-001')

    await invoiceHeader.trigger('click')
    await wrapper.vm.$nextTick()
    expect(getFirstInvoiceNumber()).toContain('INV-002')
  })

  it('sorts amount column numerically in both directions', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    const getFirstInvoiceNumber = () => {
      const firstRow = wrapper.findAll('tbody tr')[0]
      if (!firstRow) return ''
      const invoiceLink = firstRow.find('.invoice-link')
      return invoiceLink.exists() ? invoiceLink.text() : firstRow.text()
    }

    const amountHeader = wrapper.findAll('th').find(th => th.text().includes('Betrag'))
    expect(amountHeader).toBeTruthy()

    await amountHeader.trigger('click')
    await wrapper.vm.$nextTick()
    expect(getFirstInvoiceNumber()).toContain('INV-002')

    await amountHeader.trigger('click')
    await wrapper.vm.$nextTick()
    expect(getFirstInvoiceNumber()).toContain('INV-001')
  })

  it('displays quick actions', async () => {
    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()

    const text = wrapper.text()
    expect(text).toContain('Neue Rechnung')
    expect(text).toContain('Neuer Geschäftspartner')
    expect(text).toContain('Neues Produkt')
  })

  it('navigates to invoice detail when clicking details button', async () => {
    const push = vi.spyOn(router, 'push')

    wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    if (wrapper.vm.viewInvoice) {
      await wrapper.vm.viewInvoice(1)
      expect(push).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'InvoiceDetail',
          params: { id: 1 }
        })
      )
    }
  })
})
