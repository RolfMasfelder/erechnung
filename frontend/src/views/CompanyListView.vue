<template>
  <div class="company-list">
    <div class="page-header">
      <div>
        <h1 class="page-title">Firmen</h1>
        <p class="subtitle">Verwaltung aller Firmen im System (Admin)</p>
      </div>
      <BaseButton variant="primary" @click="showCreateModal = true">
        + Neue Firma
      </BaseButton>
    </div>

    <BaseCard>
      <div class="filters">
        <BaseInput
          v-model="filters.search"
          placeholder="Suche nach Firmenname..."
          @input="handleSearch"
        />
      </div>

      <BaseLoader v-if="loading && companies.length === 0" type="skeleton" :rows="5" />

      <BaseTable
        v-else
        :columns="columns"
        :data="companies"
        :loading="loading"
        empty-message="Keine Firmen gefunden"
        @sort="handleSort"
      >
        <template #cell-name="{ row }">
          <router-link
            :to="{ name: 'CompanyDetail', params: { id: row.id } }"
            class="company-link"
          >
            {{ row.name }}
          </router-link>
        </template>

        <template #cell-address="{ row }">
          {{ row.address_line1 }}, {{ row.postal_code }} {{ row.city }}
        </template>

        <template #cell-is_active="{ value }">
          <span :class="['status-badge', value ? 'active' : 'inactive']">
            {{ value ? 'Aktiv' : 'Inaktiv' }}
          </span>
        </template>

        <template #actions="{ row }">
          <div class="action-buttons">
            <BaseButton
              size="sm"
              variant="primary"
              @click="viewCompany(row.id)"
            >
              Ansehen
            </BaseButton>

            <BaseButton
              size="sm"
              variant="secondary"
              @click="editCompany(row.id)"
            >
              Bearbeiten
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

    <!-- Create Company Modal -->
    <CompanyCreateModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleCompanyCreated"
    />

    <!-- Edit Company Modal -->
    <CompanyEditModal
      v-if="showEditModal"
      :company-id="selectedCompanyId"
      @close="showEditModal = false"
      @updated="handleCompanyUpdated"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseTable from '@/components/BaseTable.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseInput from '@/components/BaseInput.vue'
import BasePagination from '@/components/BasePagination.vue'
import BaseLoader from '@/components/BaseLoader.vue'
import CompanyCreateModal from '@/components/CompanyCreateModal.vue'
import CompanyEditModal from '@/components/CompanyEditModal.vue'
import { companyService } from '@/api/services/companyService'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const toast = useToast()
const loading = ref(false)
const companies = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const selectedCompanyId = ref(null)

const filters = reactive({
  search: ''
})

const pagination = reactive({
  currentPage: 1,
  totalPages: 1,
  total: 0,
  perPage: 10,
  sortKey: '',
  sortOrder: 'asc'
})

const columns = [
  { key: 'name', label: 'Firmenname', sortable: true },
  { key: 'address', label: 'Adresse' },
  { key: 'tax_id', label: 'Steuernummer' },
  { key: 'vat_id', label: 'USt-ID' },
  { key: 'is_active', label: 'Status' }
]

let searchTimeout = null

const loadCompanies = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.currentPage,
      page_size: pagination.perPage
    }

    if (filters.search) {
      params.search = filters.search
    }

    if (pagination.sortKey) {
      params.ordering = pagination.sortOrder === 'desc'
        ? `-${pagination.sortKey}`
        : pagination.sortKey
    }

    const response = await companyService.getAll(params)

    companies.value = response.results || []
    pagination.total = response.count || 0
    pagination.totalPages = Math.ceil(pagination.total / pagination.perPage)

  } catch (error) {
    console.error('Failed to load companies:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    pagination.currentPage = 1
    loadCompanies()
  }, 500)
}

const handleSort = ({ key, order }) => {
  pagination.sortKey = key
  pagination.sortOrder = order
  pagination.currentPage = 1
  loadCompanies()
}

const handlePageChange = (page) => {
  pagination.currentPage = page
  loadCompanies()
}

const viewCompany = (id) => {
  router.push({ name: 'CompanyDetail', params: { id } })
}

const editCompany = (id) => {
  selectedCompanyId.value = id
  showEditModal.value = true
}

const handleCompanyCreated = (company) => {
  showCreateModal.value = false
  toast.success('Firma erfolgreich erstellt')
  // Search for the new company so it appears on page 1
  if (company?.name) {
    filters.search = company.name
  }
  pagination.currentPage = 1
  loadCompanies()
}

const handleCompanyUpdated = () => {
  showEditModal.value = false
  toast.success('Firma erfolgreich aktualisiert')
  loadCompanies()
}

onMounted(() => {
  loadCompanies()
})
</script>

<style scoped>
.company-list {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.page-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #111827;
}

.subtitle {
  margin-top: 0.5rem;
  color: #6b7280;
  font-size: 1rem;
}

.filters {
  margin-bottom: 1.5rem;
}

.company-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
}

.company-link:hover {
  text-decoration: underline;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.active {
  background-color: #d1fae5;
  color: #065f46;
}

.status-badge.inactive {
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
