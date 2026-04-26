<template>
  <div class="customer-detail">
    <div class="page-header">
      <div>
        <router-link to="/business-partners" class="back-link">← Zurück</router-link>
        <h1 class="page-title">{{ customer?.name }}</h1>
      </div>

      <div class="actions">
        <BaseButton variant="primary" @click="showEditModal = true">
          ✏️ Bearbeiten
        </BaseButton>
        <BaseButton variant="danger" @click="handleDelete">
          🗑️ Löschen
        </BaseButton>
      </div>
    </div>

    <div v-if="loading" class="loading">
      Lädt Geschäftspartnerdaten...
    </div>

    <div v-else-if="customer" class="customer-content">
      <!-- Kontaktdaten -->
      <BaseCard title="Kontaktdaten">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Firmenname / Name:</span>
            <span class="detail-value">{{ customer.name }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Adresse:</span>
            <span class="detail-value">
              {{ customer.street }}<br>
              <span v-if="customer.address_line2">{{ customer.address_line2 }}<br></span>
              {{ customer.postal_code }} {{ customer.city }}<br>
              {{ getCountryName(customer.country) }}
            </span>
          </div>

          <div class="detail-item">
            <span class="detail-label">E-Mail:</span>
            <span class="detail-value">
              <a v-if="customer.email" :href="`mailto:${customer.email}`">
                {{ customer.email }}
              </a>
              <span v-else class="empty">-</span>
            </span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Telefon:</span>
            <span class="detail-value">
              <a v-if="customer.phone" :href="`tel:${customer.phone}`">
                {{ customer.phone }}
              </a>
              <span v-else class="empty">-</span>
            </span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Steuernummer:</span>
            <span class="detail-value">{{ customer.tax_number || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">USt-ID:</span>
            <span class="detail-value">{{ customer.vat_id || '-' }}</span>
          </div>

          <div v-if="customer.partner_type === 'GOVERNMENT'" class="detail-item">
            <span class="detail-label">Leitweg-ID:</span>
            <span class="detail-value">{{ customer.leitweg_id || '-' }}</span>
          </div>
        </div>
      </BaseCard>

      <!-- Notizen -->
      <BaseCard v-if="customer.notes" title="Notizen">
        <p>{{ customer.notes }}</p>
      </BaseCard>

      <!-- Rechnungshistorie -->
      <BaseCard title="Rechnungshistorie">
        <div v-if="loadingInvoices" class="loading-invoices">
          Lädt Rechnungen...
        </div>

        <div v-else-if="invoices.length > 0">
          <BaseTable
            :columns="invoiceColumns"
            :data="invoices"
          >
            <template #cell-invoice_number="{ row }">
              <router-link
                :to="{ name: 'InvoiceDetail', params: { id: row.id } }"
                class="invoice-link"
              >
                {{ row.invoice_number }}
              </router-link>
            </template>

            <template #cell-status="{ value }">
              <span :class="['status-badge', `status-${value?.toLowerCase()}`]">
                {{ getStatusLabel(value) }}
              </span>
            </template>

            <template #cell-total_amount="{ value }">
              {{ formatCurrency(value) }}
            </template>

            <template #cell-issue_date="{ value }">
              {{ formatDate(value) }}
            </template>

            <template #cell-due_date="{ value }">
              {{ formatDate(value) }}
            </template>
          </BaseTable>

          <!-- Statistik -->
          <div class="invoice-stats">
            <div class="stat-item">
              <span class="stat-label">Anzahl Rechnungen:</span>
              <span class="stat-value">{{ invoiceStats.total }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Gesamtumsatz:</span>
              <span class="stat-value">{{ formatCurrency(invoiceStats.totalAmount) }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Offene Rechnungen:</span>
              <span class="stat-value">{{ invoiceStats.openCount }}</span>
            </div>
          </div>
        </div>

        <p v-else class="empty-message">
          Noch keine Rechnungen für diesen Geschäftspartner vorhanden.
        </p>
      </BaseCard>
    </div>

    <BaseAlert v-else type="error">
      Geschäftspartner konnte nicht geladen werden.
    </BaseAlert>

    <!-- Edit Modal -->
    <BusinessPartnerEditModal
      v-if="showEditModal"
      :business-partner-id="customer.id"
      @close="showEditModal = false"
      @updated="handleBusinessPartnerUpdated"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseAlert from '@/components/BaseAlert.vue'
import BaseTable from '@/components/BaseTable.vue'
import BusinessPartnerEditModal from '@/components/BusinessPartnerEditModal.vue'
import { businessPartnerService } from '@/api/services/businessPartnerService'
import { invoiceService } from '@/api/services/invoiceService'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const loadingInvoices = ref(false)
const customer = ref(null)
const invoices = ref([])
const showEditModal = ref(false)

const invoiceColumns = [
  { key: 'invoice_number', label: 'Rechnungsnr.' },
  { key: 'issue_date', label: 'Datum' },
  { key: 'due_date', label: 'Fällig am' },
  { key: 'total_amount', label: 'Betrag' },
  { key: 'status', label: 'Status' }
]

const countryNames = {
  'DE': 'Deutschland',
  'AT': 'Österreich',
  'CH': 'Schweiz',
  'FR': 'Frankreich',
  'NL': 'Niederlande',
  'BE': 'Belgien',
  'PL': 'Polen',
  'CZ': 'Tschechien'
}

const invoiceStats = computed(() => {
  const stats = {
    total: invoices.value.length,
    totalAmount: 0,
    openCount: 0
  }

  invoices.value.forEach(invoice => {
    stats.totalAmount += invoice.total_amount || 0
    const normalizedStatus = invoice.status?.toLowerCase()
    if (normalizedStatus === 'sent' || normalizedStatus === 'overdue') {
      stats.openCount++
    }
  })

  return stats
})

const loadCustomer = async () => {
  loading.value = true
  try {
    const id = route.params.id
    customer.value = await businessPartnerService.getById(id)
  } catch (error) {
    console.error('Failed to load customer:', error)
  } finally {
    loading.value = false
  }
}

const loadInvoices = async () => {
  loadingInvoices.value = true
  try {
    const id = route.params.id
    // API-Aufruf mit Customer-Filter
    const response = await invoiceService.getAll({
      customer: id,
      page_size: 100 // Alle Rechnungen des Geschäftspartner laden
    })
    invoices.value = response.results || []
  } catch (error) {
    console.error('Failed to load invoices:', error)
  } finally {
    loadingInvoices.value = false
  }
}

const getCountryName = (code) => {
  return countryNames[code] || code
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

const handleBusinessPartnerUpdated = () => {
  showEditModal.value = false
  loadCustomer()
}

const handleDelete = async () => {
  if (!confirm(`Möchten Sie den Geschäftspartner "${customer.value.name}" wirklich löschen?`)) {
    return
  }

  try {
    await businessPartnerService.delete(customer.value.id)
    router.push('/business-partners')
  } catch (error) {
    console.error('Fehler beim Löschen des Geschäftspartner:', error)
    alert('Geschäftspartner konnte nicht gelöscht werden. Möglicherweise sind noch Rechnungen mit diesem Geschäftspartner verknüpft.')
  }
}

onMounted(() => {
  loadCustomer()
  loadInvoices()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.back-link {
  display: inline-block;
  color: #3b82f6;
  text-decoration: none;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.back-link:hover {
  text-decoration: underline;
}

.page-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
}

.actions {
  display: flex;
  gap: 0.75rem;
}

.loading,
.loading-invoices {
  text-align: center;
  padding: 3rem;
  color: #6b7280;
}

.customer-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.detail-value {
  font-size: 1rem;
  color: #111827;
}

.detail-value a {
  color: #3b82f6;
  text-decoration: none;
}

.detail-value a:hover {
  text-decoration: underline;
}

.detail-value .empty {
  color: #9ca3af;
}

.invoice-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
}

.invoice-link:hover {
  text-decoration: underline;
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

.invoice-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #111827;
}

.empty-message {
  text-align: center;
  color: #6b7280;
  padding: 2rem;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 1rem;
  }

  .actions {
    flex-wrap: wrap;
  }
}
</style>
