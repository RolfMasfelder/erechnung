<template>
  <div class="company-detail">
    <div class="page-header">
      <div>
        <router-link to="/companies" class="back-link">← Zurück</router-link>
        <h1 class="page-title">{{ company?.name }}</h1>
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
      Lädt Firmendaten...
    </div>

    <div v-else-if="company" class="company-content">
      <!-- Firmendaten -->
      <BaseCard title="Firmendaten">
        <div v-if="company.logo" class="company-logo-wrapper">
          <img :src="company.logo" alt="Firmenlogo" class="company-logo" />
        </div>
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Firmenname:</span>
            <span class="detail-value">{{ company.name }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Status:</span>
            <span :class="['status-badge', company.is_active ? 'active' : 'inactive']">
              {{ company.is_active ? 'Aktiv' : 'Inaktiv' }}
            </span>
          </div>
        </div>
      </BaseCard>

      <!-- Adresse -->
      <BaseCard title="Adresse">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Straße:</span>
            <span class="detail-value">{{ company.address_line1 || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">PLZ:</span>
            <span class="detail-value">{{ company.postal_code || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Stadt:</span>
            <span class="detail-value">{{ company.city || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Land:</span>
            <span class="detail-value">{{ getCountryName(company.country) || '-' }}</span>
          </div>
        </div>
      </BaseCard>

      <!-- Kontaktinformationen -->
      <BaseCard title="Kontaktinformationen">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">E-Mail:</span>
            <span class="detail-value">
              <a v-if="company.email" :href="`mailto:${company.email}`">
                {{ company.email }}
              </a>
              <span v-else class="empty">-</span>
            </span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Telefon:</span>
            <span class="detail-value">
              <a v-if="company.phone" :href="`tel:${company.phone}`">
                {{ company.phone }}
              </a>
              <span v-else class="empty">-</span>
            </span>
          </div>
        </div>
      </BaseCard>

      <!-- Steuerdaten -->
      <BaseCard title="Steuerdaten">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Steuernummer:</span>
            <span class="detail-value">{{ company.tax_id || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">USt-ID:</span>
            <span class="detail-value">{{ company.vat_id || '-' }}</span>
          </div>
        </div>
      </BaseCard>

      <!-- Bankverbindung -->
      <BaseCard title="Bankverbindung">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Bankname:</span>
            <span class="detail-value">{{ company.bank_name || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">IBAN:</span>
            <span class="detail-value">{{ company.iban || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">BIC:</span>
            <span class="detail-value">{{ company.bic || '-' }}</span>
          </div>
        </div>
      </BaseCard>

      <!-- Metadaten -->
      <BaseCard title="Metadaten">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Erstellt am:</span>
            <span class="detail-value">{{ formatDate(company.created_at) }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Zuletzt geändert:</span>
            <span class="detail-value">{{ formatDate(company.updated_at) }}</span>
          </div>
        </div>
      </BaseCard>
    </div>

    <BaseAlert v-else type="error">
      Firma konnte nicht geladen werden.
    </BaseAlert>

    <!-- Edit Modal -->
    <CompanyEditModal
      v-if="showEditModal && company"
      :company-id="company.id"
      @close="showEditModal = false"
      @updated="handleCompanyUpdated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseAlert from '@/components/BaseAlert.vue'
import CompanyEditModal from '@/components/CompanyEditModal.vue'
import { companyService } from '@/api/services/companyService'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { confirm } = useConfirm()
const loading = ref(false)
const company = ref(null)
const showEditModal = ref(false)

const countryNames = {
  DE: 'Deutschland',
  AT: 'Österreich',
  CH: 'Schweiz',
  FR: 'Frankreich',
  NL: 'Niederlande',
  BE: 'Belgien',
  LU: 'Luxemburg',
  IT: 'Italien',
  ES: 'Spanien',
  PL: 'Polen'
}

const loadCompany = async () => {
  loading.value = true
  try {
    const id = route.params.id
    company.value = await companyService.getById(id)
  } catch (error) {
    console.error('Failed to load company:', error)
    toast.error('Fehler beim Laden der Firmendaten')
  } finally {
    loading.value = false
  }
}

const getCountryName = (countryCode) => {
  return countryNames[countryCode] || countryCode
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const handleCompanyUpdated = (updatedCompany) => {
  showEditModal.value = false
  if (updatedCompany) {
    // Use the data returned by the PATCH response directly – no extra GET needed
    company.value = updatedCompany
  } else {
    loadCompany()
  }
  toast.success('Firma aktualisiert')
}

const handleDelete = async () => {
  const confirmed = await confirm({
    title: 'Firma löschen',
    message: `Möchten Sie die Firma "${company.value.name}" wirklich löschen?`,
    confirmText: 'Löschen',
    cancelText: 'Abbrechen',
    type: 'danger'
  })

  if (!confirmed) {
    return
  }

  try {
    await companyService.delete(company.value.id)
    toast.success('Firma gelöscht')
    router.push('/companies')
  } catch (error) {
    console.error('Failed to delete company:', error)
    toast.error('Fehler beim Löschen der Firma. Möglicherweise sind noch Rechnungen mit dieser Firma verknüpft.')
  }
}

onMounted(() => {
  loadCompany()
})
</script>

<style scoped>
.company-detail {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.back-link {
  display: inline-block;
  color: #3b82f6;
  text-decoration: none;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.back-link:hover {
  text-decoration: underline;
}

.page-title {
  margin: 0;
  font-size: 1.875rem;
  font-weight: 700;
  color: #111827;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #6b7280;
}

.company-content {
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
  font-weight: 500;
  color: #6b7280;
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

.empty {
  color: #9ca3af;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-badge.active {
  background-color: #dcfce7;
  color: #166534;
}

.status-badge.inactive {
  background-color: #f3f4f6;
  color: #6b7280;
}

.company-logo-wrapper {
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.company-logo {
  max-height: 60px;
  max-width: 200px;
  object-fit: contain;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .actions {
    width: 100%;
    justify-content: stretch;
  }

  .actions button {
    flex: 1;
  }

  .details-grid {
    grid-template-columns: 1fr;
  }
}
</style>
