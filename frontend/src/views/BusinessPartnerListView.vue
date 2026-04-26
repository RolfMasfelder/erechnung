<template>
  <div class="customer-list">
    <div class="page-header">
      <h1 class="page-title">Geschäftspartner</h1>
      <div class="header-actions">
        <ImportButton label="Import" @click="showImportModal = true" />
        <BaseButton variant="primary" @click="showCreateModal = true">
          + Neuer Geschäftspartner
        </BaseButton>
      </div>
    </div>

    <BaseCard>
      <BaseFilterBar
        :filters="filterState.filters.value"
        :pending-search="filterState.pendingSearch.value"
        :is-filtering="filterState.isFiltering.value"
        :has-active-filters="filterState.hasActiveFilters.value"
        :active-filter-count="filterState.activeFilterCount.value"
        :select-filters="selectFilters"
        search-placeholder="Suche nach Name, Stadt, E-Mail..."
        @search="handleSearchInput"
        @search-immediate="handleSearchImmediate"
        @filter-change="handleFilterChange"
        @reset="handleResetFilters"
      />

      <BaseLoader v-if="loading && customers.length === 0" type="skeleton" :rows="5" />

      <BaseTable
        v-else
        :columns="columns"
        :data="customers"
        :loading="loading"
        empty-message="Keine Geschäftspartner gefunden"
        @sort="handleSort"
      >
        <template #cell-name="{ row }">
          <router-link
            :to="{ name: 'BusinessPartnerDetail', params: { id: row.id } }"
            class="customer-link"
          >
            {{ row.name }}
          </router-link>
        </template>

        <template #cell-address="{ row }">
          {{ row.street }}, {{ row.postal_code }} {{ row.city }}
        </template>

        <template #actions="{ row }">
          <div class="action-buttons">
            <BaseButton
              size="sm"
              variant="primary"
              @click="viewCustomer(row.id)"
            >
              Ansehen
            </BaseButton>

            <BaseButton
              size="sm"
              variant="secondary"
              @click="editCustomer(row.id)"
            >
              Bearbeiten
            </BaseButton>

            <BaseButton
              size="sm"
              variant="danger"
              @click="deleteCustomer(row.id, row.name)"
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

    <!-- Create Business Partner Modal -->
    <BusinessPartnerCreateModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleBusinessPartnerCreated"
    />

    <!-- Edit Business Partner Modal -->
    <BusinessPartnerEditModal
      v-if="showEditModal"
      :business-partner-id="selectedBusinessPartnerId"
      @close="showEditModal = false"
      @updated="handleBusinessPartnerUpdated"
    />

    <!-- Import Modal -->
    <ImportModal
      v-if="showImportModal"
      :is-open="showImportModal"
      title="Geschäftspartner importieren"
      :required-fields="['name', 'email', 'country']"
      :optional-fields="['street', 'postal_code', 'city', 'phone', 'tax_id', 'vat_id']"
      @close="showImportModal = false"
      @import="handleImport"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseTable from '@/components/BaseTable.vue'
import BaseButton from '@/components/BaseButton.vue'
import BasePagination from '@/components/BasePagination.vue'
import BaseLoader from '@/components/BaseLoader.vue'
import BaseFilterBar from '@/components/BaseFilterBar.vue'
import ImportButton from '@/components/ImportButton.vue'
import ImportModal from '@/components/ImportModal.vue'
import BusinessPartnerCreateModal from '@/components/BusinessPartnerCreateModal.vue'
import BusinessPartnerEditModal from '@/components/BusinessPartnerEditModal.vue'
import { businessPartnerService } from '@/api/services/businessPartnerService'
import { importService } from '@/api/services/importService'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useFilter } from '@/composables/useFilter'

const router = useRouter()
const toast = useToast()
const { confirm } = useConfirm()
const loading = ref(false)
const customers = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showImportModal = ref(false)
const selectedBusinessPartnerId = ref(null)

// Filter setup with useFilter composable
const filterState = useFilter({
  defaultFilters: {
    search: '',
    country: ''
  },
  debounceMs: 300,
  syncUrl: true,
  onFilterChange: () => {
    pagination.currentPage = 1
    loadCustomers()
  }
})

// Select filter configuration for BaseFilterBar
const selectFilters = [
  {
    key: 'country',
    options: [
      { value: '', label: 'Alle Länder' },
      { value: 'DE', label: 'Deutschland' },
      { value: 'AT', label: 'Österreich' },
      { value: 'CH', label: 'Schweiz' },
      { value: 'FR', label: 'Frankreich' },
      { value: 'NL', label: 'Niederlande' },
      { value: 'BE', label: 'Belgien' },
      { value: 'PL', label: 'Polen' },
      { value: 'CZ', label: 'Tschechien' }
    ],
    placeholder: 'Land filtern',
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
  { key: 'name', label: 'Name', sortable: true },
  { key: 'address', label: 'Adresse' },
  { key: 'city', label: 'Stadt', sortable: true },
  { key: 'country', label: 'Land', sortable: true },
  { key: 'email', label: 'E-Mail' },
  { key: 'phone', label: 'Telefon' }
]

const sortKeyMap = {
  name: 'business_partner_name'
}

const getOrderingField = (sortKey) => {
  return sortKeyMap[sortKey] || sortKey
}

const loadCustomers = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.perPage,
      ...filterState.queryParams.value
    }

    if (pagination.sortKey) {
      const orderingField = getOrderingField(pagination.sortKey)
      params.ordering = pagination.sortOrder === 'desc'
        ? `-${orderingField}`
        : orderingField
    }

    const response = await businessPartnerService.getAll(params)

    customers.value = response.results || []
    pagination.total = response.count || 0
    pagination.totalPages = Math.ceil(pagination.total / pagination.perPage)

  } catch (error) {
    console.error('Failed to load customers:', error)
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
  loadCustomers()
}

const handlePageChange = (page) => {
  pagination.currentPage = page
  loadCustomers()
}

const viewCustomer = (id) => {
  router.push({ name: 'BusinessPartnerDetail', params: { id } })
}

const editCustomer = (id) => {
  selectedBusinessPartnerId.value = id
  showEditModal.value = true
}

const deleteCustomer = async (id, name) => {
  const confirmed = await confirm(
    `Möchten Sie den Geschäftspartner "${name}" wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.`,
    {
      title: 'Geschäftspartner löschen',
      variant: 'danger',
      confirmText: 'Löschen'
    }
  )

  if (!confirmed) return

  try {
    await businessPartnerService.delete(id)
    toast.success('Geschäftspartner erfolgreich gelöscht')
    loadCustomers()
  } catch (error) {
    console.error('Failed to delete customer:', error)
    toast.error('Geschäftspartner konnte nicht gelöscht werden. Möglicherweise sind noch Rechnungen mit diesem Geschäftspartner verknüpft.')
  }
}

const handleBusinessPartnerCreated = (customer) => {
  showCreateModal.value = false
  // console.log('Geschäftspartner erstellt:', customer)
  toast.success('Geschäftspartner erfolgreich erstellt')
  loadCustomers()
  // Optional: Zur Detail-Ansicht navigieren
  if (customer?.id) {
    router.push({ name: 'BusinessPartnerDetail', params: { id: customer.id } })
  }
}

const handleBusinessPartnerUpdated = () => {
  showEditModal.value = false
  toast.success('Geschäftspartner erfolgreich aktualisiert')
  loadCustomers()
}

const handleImport = async (validatedData) => {
  try {
    const result = await importService.importBusinessPartners(validatedData)

    showImportModal.value = false

    if (result.errors && result.errors.length > 0) {
      toast.warning(`${result.created} von ${validatedData.length} Geschäftspartner importiert. ${result.errors.length} Fehler aufgetreten.`)
    } else {
      toast.success(`${result.created} Geschäftspartner erfolgreich importiert`)
    }

    loadCustomers()
  } catch (error) {
    console.error('Import failed:', error)
    toast.error('Import fehlgeschlagen: ' + (error.message || 'Unbekannter Fehler'))
  }
}

onMounted(() => {
  loadCustomers()
})
</script>

<style scoped>
.customer-list {
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

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.customer-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
}

.customer-link:hover {
  text-decoration: underline;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
  }
}
</style>
