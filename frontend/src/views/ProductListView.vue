<template>
  <div class="product-list">
    <div class="page-header">
      <h1 class="page-title">Produkte</h1>
      <div class="header-actions">
        <ImportButton label="Import" @click="showImportModal = true" />
        <BaseButton variant="primary" @click="showCreateModal = true">
          + Neues Produkt
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
        search-placeholder="Suche nach Name, SKU, Kategorie..."
        @search="handleSearchInput"
        @search-immediate="handleSearchImmediate"
        @filter-change="handleFilterChange"
        @reset="handleResetFilters"
      />

      <BaseLoader v-if="loading && products.length === 0" type="skeleton" :rows="5" />

      <BaseTable
        v-else
        :columns="columns"
        :data="products"
        :loading="loading"
        empty-message="Keine Produkte gefunden"
        @sort="handleSort"
      >
        <template #cell-name="{ row }">
          <div class="product-name">
            <router-link
              :to="{ name: 'ProductDetail', params: { id: row.id } }"
              class="name product-link"
            >
              {{ row.name }}
            </router-link>
            <span v-if="!row.is_active" class="inactive-badge">Inaktiv</span>
          </div>
        </template>

        <template #cell-product_code="{ row }">
          {{ row.sku || row.product_code || '-' }}
        </template>

        <template #cell-base_price="{ value }">
          {{ formatCurrency(value) }}
        </template>

        <template #cell-default_tax_rate="{ value }">
          {{ value }}%
        </template>

        <template #actions="{ row }">
          <div class="action-buttons">
            <BaseButton
              size="sm"
              variant="primary"
              @click="viewProduct(row.id)"
            >
              Ansehen
            </BaseButton>

            <BaseButton
              size="sm"
              variant="secondary"
              @click="editProduct(row.id)"
            >
              Bearbeiten
            </BaseButton>

            <BaseButton
              size="sm"
              variant="danger"
              @click="deleteProduct(row.id, row.name)"
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

    <!-- Create Product Modal -->
    <ProductCreateModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleProductCreated"
    />

    <!-- Edit Product Modal -->
    <ProductEditModal
      v-if="showEditModal"
      :product-id="selectedProductId"
      @close="showEditModal = false"
      @updated="handleProductUpdated"
    />

    <!-- Import Modal -->
    <ImportModal
      v-if="showImportModal"
      :is-open="showImportModal"
      title="Produkte importieren"
      :required-fields="['name', 'price']"
      :optional-fields="['description', 'sku', 'product_code', 'unit_of_measure', 'default_tax_rate', 'is_active']"
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
import ProductCreateModal from '@/components/ProductCreateModal.vue'
import ProductEditModal from '@/components/ProductEditModal.vue'
import { productService } from '@/api/services/productService'
import { importService } from '@/api/services/importService'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useFilter } from '@/composables/useFilter'

const toast = useToast()
const { confirm } = useConfirm()
const router = useRouter()
const loading = ref(false)
const products = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showImportModal = ref(false)
const selectedProductId = ref(null)

// Filter setup with useFilter composable
const filterState = useFilter({
  defaultFilters: {
    search: '',
    is_active: ''
  },
  debounceMs: 300,
  syncUrl: true,
  onFilterChange: () => {
    pagination.currentPage = 1
    loadProducts()
  }
})

// Select filter configuration for BaseFilterBar
const selectFilters = [
  {
    key: 'is_active',
    options: [
      { value: '', label: 'Alle Status' },
      { value: 'true', label: 'Nur aktive' },
      { value: 'false', label: 'Nur inaktive' }
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
  { key: 'name', label: 'Produktname', sortable: true },
  { key: 'product_code', label: 'SKU/Code', sortable: true },
  { key: 'category', label: 'Kategorie', sortable: true },
  { key: 'base_price', label: 'Preis (Netto)', sortable: true },
  { key: 'default_tax_rate', label: 'MwSt.', sortable: true },
  { key: 'unit_of_measure', label: 'Einheit' }
]

const loadProducts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.perPage,
      ...filterState.queryParams.value
    }

    if (pagination.sortKey) {
      params.ordering = pagination.sortOrder === 'desc'
        ? `-${pagination.sortKey}`
        : pagination.sortKey
    }

    const response = await productService.getAll(params)

    products.value = response.results || []
    pagination.total = response.count || 0
    pagination.totalPages = Math.ceil(pagination.total / pagination.perPage)

  } catch (error) {
    console.error('Failed to load products:', error)
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
  loadProducts()
}

const handlePageChange = (page) => {
  pagination.currentPage = page
  loadProducts()
}

const viewProduct = (id) => {
  router.push({ name: 'ProductDetail', params: { id } })
}

const editProduct = (id) => {
  selectedProductId.value = id
  showEditModal.value = true
}

const deleteProduct = async (id, name) => {
  const confirmed = await confirm(
    `Möchten Sie das Produkt "${name}" wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.`,
    {
      title: 'Produkt löschen',
      variant: 'danger',
      confirmText: 'Löschen'
    }
  )

  if (!confirmed) return

  try {
    await productService.delete(id)
    toast.success('Produkt erfolgreich gelöscht')
    loadProducts()
  } catch (error) {
    console.error('Failed to delete product:', error)
    toast.error('Produkt konnte nicht gelöscht werden. Möglicherweise wird es noch in Rechnungen verwendet.')
  }
}

const handleProductCreated = () => {
  showCreateModal.value = false
  toast.success('Produkt erfolgreich erstellt')
  loadProducts()
}

const handleProductUpdated = () => {
  showEditModal.value = false
  toast.success('Produkt erfolgreich aktualisiert')
  loadProducts()
}

const handleImport = async (validatedData) => {
  try {
    const result = await importService.importProducts(validatedData)

    showImportModal.value = false

    if (result.errors && result.errors.length > 0) {
      toast.warning(`${result.created} von ${validatedData.length} Produkten importiert. ${result.errors.length} Fehler aufgetreten.`)
    } else {
      toast.success(`${result.created} Produkte erfolgreich importiert`)
    }

    loadProducts()
  } catch (error) {
    console.error('Import failed:', error)
    toast.error('Import fehlgeschlagen: ' + (error.message || 'Unbekannter Fehler'))
  }
}

const formatCurrency = (value) => {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR'
  }).format(value || 0)
}

onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
.product-list {
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

.product-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.product-name .name {
  font-weight: 600;
}

.product-link {
  color: #2563eb;
  text-decoration: none;
}

.product-link:hover {
  text-decoration: underline;
}

.inactive-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  background-color: #fee2e2;
  color: #991b1b;
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
