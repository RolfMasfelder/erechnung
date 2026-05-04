<template>
  <div class="invoice-list">
    <div class="page-header">
      <h1 class="page-title">Rechnungen</h1>
      <BaseButton variant="primary" @click="showCreateModal = true">
        + Neue Rechnung
      </BaseButton>
    </div>

    <BaseCard>
      <BaseFilterBar
        :filters="filterState.filters.value"
        :pending-search="filterState.pendingSearch.value"
        :is-filtering="filterState.isFiltering.value"
        :has-active-filters="filterState.hasActiveFilters.value"
        :active-filter-count="filterState.activeFilterCount.value"
        :select-filters="selectFilters"
        :show-date-range="true"
        date-range-key="dateRange"
        date-range-label="Zeitraum"
        search-placeholder="Suche nach Rechnungsnummer, Kunde..."
        @search="handleSearchInput"
        @search-immediate="handleSearchImmediate"
        @filter-change="handleFilterChange"
        @reset="handleResetFilters"
      />

      <BaseLoader v-if="loading && invoices.length === 0" type="skeleton" :rows="5" />

      <BaseTable
        v-else
        :columns="columns"
        :data="invoices"
        :loading="loading"
        :selectable="true"
        :selected-ids="selectedIdsArray"
        empty-message="Keine Rechnungen gefunden"
        @sort="handleSort"
        @select="handleRowSelect"
        @select-all="handleSelectAll"
        @select-range="handleSelectRange"
      >
        <template #cell-invoice_number="{ row }">
          <router-link
            :to="{ name: 'InvoiceDetail', params: { id: row.id } }"
            class="invoice-link"
          >
            <span v-if="row.invoice_type === 'CREDIT_NOTE'" class="type-badge type-credit-note">GS</span>
            <span v-if="row.business_partner_details?.partner_type === 'GOVERNMENT'" class="type-badge type-xrechnung">XR</span>
            {{ row.invoice_number }}
          </router-link>
        </template>

        <template #cell-status="{ value }">
          <span :class="['status-badge', `status-${value?.toLowerCase()}`]">
            {{ getStatusLabel(value) }}
          </span>
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

        <template #cell-total_amount="{ value }">
          {{ formatCurrency(value) }}
        </template>

        <template #cell-issue_date="{ value }">
          {{ formatDate(value) }}
        </template>

        <template #cell-due_date="{ value }">
          {{ formatDate(value) }}
        </template>

        <template #actions="{ row }">
          <div class="action-buttons">
            <BaseButton
              size="sm"
              variant="primary"
              @click="viewInvoice(row.id)"
            >
              Ansehen
            </BaseButton>

            <BaseButton
              size="sm"
              variant="secondary"
              :loading="generatingPdfId === row.id"
              @click="generateAndDownloadPDF(row.id)"
            >
              PDF
            </BaseButton>

            <BaseButton
              v-if="row.status === 'draft'"
              size="sm"
              variant="danger"
              @click="deleteInvoice(row.id)"
            >
              Löschen
            </BaseButton>
          </div>
        </template>
      </BaseTable>

      <BasePagination
        v-if="pagination.totalPages > 1"
        :current-page="pagination.currentPage"
        :total-pages="pagination.totalPages"
        :total="pagination.total"
        :per-page="pagination.perPage"
        @change="handlePageChange"
      />
    </BaseCard>
    <!-- Bulk Action Bar -->
    <BulkActionBar
      :selection-count="bulkSelect.selectionCount.value"
      :show="bulkSelect.hasSelection.value"
      @clear="bulkSelect.clearSelection"
    >
      <template #actions>
        <ExportButton
          :data="invoices"
          :columns="columns"
          :selected-ids="bulkSelect.selectedIds.value"
          filename="rechnungen_export"
          size="sm"
        />
        <BaseButton
          variant="danger"
          size="sm"
          @click="handleBulkDelete"
        >
          <span class="action-icon">🗑️</span>
          Löschen
        </BaseButton>
      </template>
    </BulkActionBar>
    <!-- Create Invoice Modal -->
    <InvoiceCreateModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleInvoiceCreated"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseTable from '@/components/BaseTable.vue'
import BaseButton from '@/components/BaseButton.vue'
import BasePagination from '@/components/BasePagination.vue'
import BaseLoader from '@/components/BaseLoader.vue'
import BaseFilterBar from '@/components/BaseFilterBar.vue'
import BulkActionBar from '@/components/BulkActionBar.vue'
import ExportButton from '@/components/ExportButton.vue'
import InvoiceCreateModal from '@/components/InvoiceCreateModal.vue'
import { invoiceService } from '@/api/services/invoiceService'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useFilter } from '@/composables/useFilter'
import { useBulkSelect } from '@/composables/useBulkSelect'

const router = useRouter()
const toast = useToast()
const { confirm } = useConfirm()
const loading = ref(false)
const invoices = ref([])
const showCreateModal = ref(false)
const generatingPdfId = ref(null)

// Bulk selection setup
const bulkSelect = useBulkSelect({
  getItemId: (item) => item.id,
  persistAcrossPages: false
})

// Computed to ensure reactivity - creates new array on every change
const selectedIdsArray = computed(() => {
  return Array.from(bulkSelect.selectedIds.value)
})

// Filter setup with useFilter composable
const filterState = useFilter({
  defaultFilters: {
    search: '',
    status: '',
    dateRange: null
  },
  debounceMs: 300,
  syncUrl: true,
  onFilterChange: () => {
    pagination.currentPage = 1
    loadInvoices()
  }
})

// Select filter configuration for BaseFilterBar
const selectFilters = [
  {
    key: 'status',
    options: [
      { value: '', label: 'Alle Status' },
      { value: 'DRAFT', label: 'Entwurf' },
      { value: 'SENT', label: 'Versendet' },
      { value: 'PAID', label: 'Bezahlt' },
      { value: 'CANCELLED', label: 'Storniert' },
      { value: 'OVERDUE', label: 'Überfällig' }
    ],
    placeholder: 'Status filtern',
    label: ''
  }
]

const pagination = reactive({
  currentPage: 1,
  totalPages: 1,
  total: 0,
  perPage: 10,
  sortKey: '',
  sortOrder: 'asc'
})

const columns = [
  { key: 'invoice_number', label: 'Rechnungsnr.', sortable: true },
  { key: 'customer_name', label: 'Kunde', sortable: true },
  { key: 'issue_date', label: 'Rechnungsdatum', sortable: true },
  { key: 'due_date', label: 'Fälligkeitsdatum', sortable: true },
  { key: 'total_amount', label: 'Gesamtbetrag', sortable: true },
  { key: 'status', label: 'Status', sortable: true }
]

const sortKeyMap = {
  customer_name: 'business_partner__company_name'
}

const getOrderingField = (sortKey) => {
  return sortKeyMap[sortKey] || sortKey
}

const loadInvoices = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.perPage,
      ...filterState.queryParams.value
    }

    if (pagination.sortKey) {
      const orderingField = getOrderingField(pagination.sortKey)
      // Django REST framework ordering: -field für desc, field für asc
      params.ordering = pagination.sortOrder === 'desc'
        ? `-${orderingField}`
        : orderingField
    }

    // Debug: Query-Parameter ausgeben
    if (import.meta.env.DEV) {
      console.log('API Query Parameters:', params)
    }

    const response = await invoiceService.getAll(params)

    invoices.value = response.results || []
    pagination.total = response.count || 0
    pagination.totalPages = Math.ceil(pagination.total / pagination.perPage)

    // Update bulk select with current items (without clearing selection)
    bulkSelect.updateItems(invoices.value)

  } catch (error) {
    console.error('Failed to load invoices:', error)
    toast.error('Fehler beim Laden der Rechnungen')
  } finally {
    loading.value = false
  }
}

const handleSearchInput = (value) => {
  filterState.handleSearch(value)
}

const handleSearchImmediate = () => {
  filterState.applySearchNow()
}

const handleFilterChange = ({ key, value }) => {
  filterState.setFilter(key, value)
}

const handleResetFilters = () => {
  filterState.resetFilters()
}

const handleSort = ({ key, order }) => {
  pagination.sortKey = key
  pagination.sortOrder = order
  pagination.currentPage = 1
  loadInvoices()
}

const handlePageChange = (page) => {
  pagination.currentPage = page
  loadInvoices()
}

// Bulk selection handlers
const handleRowSelect = ({ id, selected }) => {
  const item = invoices.value.find(inv => inv.id === id)
  if (item) {
    if (selected) {
      bulkSelect.selectItem(item)
    } else {
      bulkSelect.deselectItem(item)
    }
  }
}

const handleSelectAll = ({ ids, selected }) => {
  if (selected) {
    const items = invoices.value.filter(inv => ids.includes(inv.id))
    bulkSelect.selectItems(items)
  } else {
    // Use deselectAll to clear current page selection
    bulkSelect.deselectAll()
  }
}

const handleSelectRange = ({ ids }) => {
  const items = invoices.value.filter(inv => ids.includes(inv.id))
  bulkSelect.selectItems(items)
}

const handleBulkDelete = async () => {
  const count = bulkSelect.selectionCount.value
  const confirmed = await confirm(
    `Möchten Sie wirklich ${count} ${count === 1 ? 'Rechnung' : 'Rechnungen'} löschen? Diese Aktion kann nicht rückgängig gemacht werden.`,
    {
      title: 'Rechnungen löschen',
      variant: 'danger',
      confirmText: 'Löschen'
    }
  )

  if (!confirmed) return

  try {
    const selectedIds = Array.from(bulkSelect.selectedIds.value)
    await Promise.all(selectedIds.map(id => invoiceService.delete(id)))

    toast.success(`${count} ${count === 1 ? 'Rechnung' : 'Rechnungen'} gelöscht`)
    bulkSelect.clearSelection()
    loadInvoices()
  } catch (error) {
    console.error('Bulk delete failed:', error)
    toast.error('Fehler beim Löschen')
  }
}

const viewInvoice = (id) => {
  router.push({ name: 'InvoiceDetail', params: { id } })
}

const generateAndDownloadPDF = async (id) => {
  generatingPdfId.value = id
  try {
    // Generate PDF first, then download
    await invoiceService.generatePDF(id)
    const blob = await invoiceService.downloadPDF(id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `invoice-${id}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    toast.success('PDF erfolgreich generiert und heruntergeladen')
  } catch (error) {
    console.error('Failed to generate/download PDF:', error)
    toast.error('Fehler bei der PDF-Generierung')
  } finally {
    generatingPdfId.value = null
  }
}

const deleteInvoice = async (id) => {
  const confirmed = await confirm(
    'Möchten Sie diese Rechnung wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.',
    {
      title: 'Rechnung löschen',
      variant: 'danger',
      confirmText: 'Löschen'
    }
  )

  if (!confirmed) return

  try {
    await invoiceService.delete(id)
    toast.success('Rechnung erfolgreich gelöscht')
    loadInvoices()
  } catch (error) {
    console.error('Failed to delete invoice:', error)
    toast.error('Fehler beim Löschen der Rechnung')
  }
}

const handleInvoiceCreated = (invoice) => {
  showCreateModal.value = false
  toast.success('Rechnung erfolgreich erstellt')
  // Liste neu laden
  loadInvoices()
  // Optional: Zur Detail-Ansicht navigieren
  if (invoice?.id) {
    router.push({ name: 'InvoiceDetail', params: { id: invoice.id } })
  }
}

const getStatusLabel = (status) => {
  const labels = {
    'DRAFT': 'Entwurf',
    'SENT': 'Versendet',
    'PAID': 'Bezahlt',
    'CANCELLED': 'Storniert',
    'OVERDUE': 'Überfällig',
    // Legacy lowercase support (falls Backend noch alte Werte hat)
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

onMounted(() => {
  loadInvoices()
})
</script>

<style scoped>
.invoice-list {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
}

.invoice-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
}

.invoice-link:hover {
  text-decoration: underline;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
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

.customer-link {
  color: #2563eb;
  text-decoration: none;
  transition: color 0.2s;
}

.customer-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.status-overdue {
  background-color: #fef3c7;
  color: #92400e;
}

.type-badge {
  display: inline-block;
  padding: 0.1rem 0.35rem;
  border-radius: 0.2rem;
  font-size: 0.65rem;
  font-weight: 700;
  margin-right: 0.25rem;
  vertical-align: middle;
}

.type-credit-note {
  background-color: #fce7f3;
  color: #9d174d;
}

.type-xrechnung {
  background-color: #dbeafe;
  color: #1e40af;
}

@media (max-width: 768px) {
  .filters {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
