<template>
  <div class="dashboard">
    <h1 class="page-title">Dashboard</h1>

    <div class="stats-grid">
      <BaseCard
        v-for="stat in stats"
        :key="stat.title"
        :title="stat.title"
        hover
      >
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </BaseCard>
    </div>

    <div class="dashboard-grid">
      <BaseCard title="Letzte Rechnungen" class="recent-invoices">
        <BaseTable
          v-if="!loading"
          :columns="invoiceColumns"
          :data="sortedRecentInvoices"
          :loading="loading"
          empty-message="Keine Rechnungen vorhanden"
          @sort="handleSort"
        >
          <template #cell-status="{ value }">
            <span :class="['status-badge', `status-${value?.toLowerCase()}`]">
              {{ getStatusLabel(value) }}
            </span>
          </template>

          <template #cell-invoice_number="{ row }">
            <router-link
              :to="{ name: 'InvoiceDetail', params: { id: row.id } }"
              class="invoice-link"
            >
              {{ row.invoice_number }}
            </router-link>
          </template>

          <template #cell-customer_name="{ row }">
            <router-link
              v-if="row.business_partner_details?.id || row.customer_details?.id"
              :to="{ name: 'BusinessPartnerDetail', params: { id: row.business_partner_details?.id || row.customer_details?.id } }"
              class="customer-link"
            >
              {{ row.business_partner_details?.name || row.customer_details?.name }}
            </router-link>
            <span v-else>-</span>
          </template>

          <template #cell-due_date="{ value }">
            {{ formatDate(value) }}
          </template>

          <template #cell-total_amount="{ value }">
            {{ formatCurrency(value) }}
          </template>

          <template #actions="{ row }">
            <BaseButton
              size="sm"
              variant="primary"
              @click="viewInvoice(row.id)"
            >
              Details
            </BaseButton>
          </template>
        </BaseTable>

        <div class="card-footer">
          <router-link to="/invoices" class="view-all-link">
            Alle Rechnungen anzeigen →
          </router-link>
        </div>
      </BaseCard>

      <BaseCard title="Schnellaktionen">
        <div class="quick-actions">
          <BaseButton
            variant="primary"
            block
            @click="createInvoice"
          >
            📄 Neue Rechnung
          </BaseButton>

          <BaseButton
            variant="secondary"
            block
            @click="createBusinessPartner"
          >
            👥 Neuer Geschäftspartner
          </BaseButton>

          <BaseButton
            variant="secondary"
            block
            @click="createProduct"
          >
            📦 Neues Produkt
          </BaseButton>
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseTable from '@/components/BaseTable.vue'
import BaseButton from '@/components/BaseButton.vue'
import { invoiceService } from '@/api/services/invoiceService'
import { statsService } from '@/api/services/statsService'

const router = useRouter()
const loading = ref(false)
const recentInvoices = ref([])
const tableSort = ref({ key: '', order: 'asc' })

const stats = ref([
  { title: 'Gesamt Rechnungen', value: '0', label: 'Im System' },
  { title: 'Offene Rechnungen', value: '0', label: 'Unbezahlt' },
  { title: 'Bezahlte Rechnungen', value: '0', label: 'Abgeschlossen' },
  { title: 'Kunden', value: '0', label: 'Aktiv' }
])

const invoiceColumns = [
  { key: 'invoice_number', label: 'Rechnungsnr.', sortable: true },
  { key: 'customer_name', label: 'Kunde', sortable: true },
  { key: 'due_date', label: 'Fällig am', sortable: true },
  { key: 'total_amount', label: 'Betrag', sortable: true },
  { key: 'status', label: 'Status', sortable: true }
]

const parseNumericValue = (value) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value === 'string') {
    const normalized = value
      .replace(/\s/g, '')
      .replace(/\./g, '')
      .replace(',', '.')

    const parsed = Number(normalized)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }

  return null
}

const getSortableValue = (invoice, key) => {
  if (key === 'customer_name') {
    return (
      invoice.business_partner_details?.name
      || invoice.customer_details?.name
      || ''
    )
  }

  if (key === 'total_amount') {
    return parseNumericValue(invoice.total_amount) ?? 0
  }

  if (key === 'due_date') {
    return invoice.due_date ? new Date(invoice.due_date).getTime() : 0
  }

  return invoice[key] ?? ''
}

const sortedRecentInvoices = computed(() => {
  if (!tableSort.value.key) {
    return recentInvoices.value
  }

  const sorted = [...recentInvoices.value].sort((a, b) => {
    const aValue = getSortableValue(a, tableSort.value.key)
    const bValue = getSortableValue(b, tableSort.value.key)

    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return aValue - bValue
    }

    return String(aValue).localeCompare(String(bValue), 'de', { sensitivity: 'base' })
  })

  return tableSort.value.order === 'desc' ? sorted.reverse() : sorted
})

const handleSort = ({ key, order }) => {
  tableSort.value = { key, order }
}

const loadDashboardData = async () => {
  loading.value = true
  try {
    // Load statistics from API
    const statsData = await statsService.getStats()

    // Update stats with real data
    stats.value = [
      {
        title: 'Gesamt Rechnungen',
        value: statsData.invoices.total.toString(),
        label: 'Im System'
      },
      {
        title: 'Offene Rechnungen',
        value: (statsData.invoices.by_status.sent + statsData.invoices.by_status.overdue).toString(),
        label: 'Unbezahlt'
      },
      {
        title: 'Bezahlte Rechnungen',
        value: statsData.invoices.by_status.paid.toString(),
        label: 'Abgeschlossen'
      },
      {
        title: 'Geschäftspartner',
        value: statsData.business_partners.active.toString(),
        label: 'Aktiv'
      }
    ]

    // Load recent invoices (limit 5)
    const response = await invoiceService.getAll({ page_size: 5, ordering: '-created_at' })
    recentInvoices.value = response.results || []

  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    loading.value = false
  }
}

const getStatusLabel = (status) => {
  const labels = {
    'DRAFT': 'Entwurf',
    'SENT': 'Versendet',
    'PAID': 'Bezahlt',
    'CANCELLED': 'Storniert',
    'OVERDUE': 'Überfällig',
    'draft': 'Entwurf',
    'sent': 'Versendet',
    'paid': 'Bezahlt',
    'cancelled': 'Storniert',
    'overdue': 'Überfällig'
  }
  return labels[status] || status
}

const formatCurrency = (value) => {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR'
  }).format(value || 0)
}

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const viewInvoice = (id) => {
  router.push({ name: 'InvoiceDetail', params: { id } })
}

const createInvoice = () => {
  router.push('/invoices?action=create')
}

const createBusinessPartner = () => {
  router.push('/business-partners?action=create')
}

const createProduct = () => {
  router.push('/products?action=create')
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
}

.page-title {
  margin: 0 0 2rem 0;
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-content {
  text-align: center;
  padding: 1rem 0;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #3b82f6;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

.recent-invoices {
  grid-column: 1;
}

.card-footer {
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
  text-align: center;
}

.view-all-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
}

.view-all-link:hover {
  text-decoration: underline;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-draft {
  background-color: #f3f4f6;
  color: #374151;
}

.status-sent {
  background-color: #dbeafe;
  color: #1e40af;
}

.status-paid {
  background-color: #d1fae5;
  color: #065f46;
}

.status-cancelled {
  background-color: #fee2e2;
  color: #991b1b;
}

.status-overdue {
  background-color: #fef3c7;
  color: #92400e;
}

.customer-link,
.invoice-link {
  color: #2563eb;
  text-decoration: none;
  transition: color 0.2s;
}

.customer-link:hover,
.invoice-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
