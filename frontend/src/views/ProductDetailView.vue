<template>
  <div class="product-detail">
    <div class="page-header">
      <div>
        <router-link to="/products" class="back-link">← Zurück</router-link>
        <h1 class="page-title">{{ product?.name }}</h1>
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
      Lädt Produktdaten...
    </div>

    <div v-else-if="product" class="product-content">
      <!-- Produktdetails -->
      <BaseCard title="Produktinformationen">
        <div class="details-grid">
          <div class="detail-item">
            <span class="detail-label">Produktname:</span>
            <span class="detail-value">{{ product.name }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Status:</span>
            <span :class="['status-badge', product.is_active ? 'active' : 'inactive']">
              {{ product.is_active ? 'Aktiv' : 'Inaktiv' }}
            </span>
          </div>

          <div class="detail-item">
            <span class="detail-label">SKU:</span>
            <span class="detail-value">{{ product.sku || product.product_code || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Kategorie:</span>
            <span class="detail-value">{{ product.category || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Einzelpreis (Netto):</span>
            <span class="detail-value strong">{{ formatCurrency(product.base_price) }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">MwSt.-Satz:</span>
            <span class="detail-value">{{ product.default_tax_rate }}%</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Einzelpreis (Brutto):</span>
            <span class="detail-value">{{ formatCurrency(calculateGrossPrice(product)) }}</span>
          </div>

          <div class="detail-item">
            <span class="detail-label">Einheit:</span>
            <span class="detail-value">{{ formatUnitLabel(product.unit_of_measure) }}</span>
          </div>
        </div>

        <div v-if="product.description" class="description">
          <h3>Beschreibung</h3>
          <p>{{ product.description }}</p>
        </div>
      </BaseCard>

      <!-- Verwendung in Rechnungen (optional, falls Backend unterstützt) -->
      <BaseCard title="Nutzungsstatistik">
        <p class="placeholder">
          Wird in Zukunft die Verwendung des Produkts in Rechnungen anzeigen.
        </p>
      </BaseCard>
    </div>

    <BaseAlert v-else type="error">
      Produkt konnte nicht geladen werden.
    </BaseAlert>

    <!-- Edit Modal -->
    <ProductEditModal
      v-if="showEditModal"
      :product-id="product.id"
      @close="showEditModal = false"
      @updated="handleProductUpdated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { formatUnitLabel } from '@/utils/unitOfMeasure'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseAlert from '@/components/BaseAlert.vue'
import ProductEditModal from '@/components/ProductEditModal.vue'
import { productService } from '@/api/services/productService'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const product = ref(null)
const showEditModal = ref(false)

const loadProduct = async () => {
  loading.value = true
  try {
    const id = route.params.id
    product.value = await productService.getById(id)
  } catch (error) {
    console.error('Failed to load product:', error)
  } finally {
    loading.value = false
  }
}

const toNumericValue = (value) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value === 'string') {
    const normalized = value.replace(/\s/g, '').replace(',', '.')
    const parsed = Number(normalized)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }

  return 0
}

const calculateGrossPrice = (product) => {
  const net = toNumericValue(product.base_price)
  const taxRate = toNumericValue(product.default_tax_rate)
  const vat = net * (taxRate / 100)
  return net + vat
}

const formatCurrency = (value) => {
  const amount = toNumericValue(value)
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR'
  }).format(amount)
}

const handleProductUpdated = () => {
  showEditModal.value = false
  loadProduct()
}

const handleDelete = async () => {
  if (!confirm(`Möchten Sie das Produkt "${product.value.name}" wirklich löschen?`)) {
    return
  }

  try {
    await productService.delete(product.value.id)
    router.push('/products')
  } catch (error) {
    console.error('Fehler beim Löschen des Produkts:', error)
    alert('Produkt konnte nicht gelöscht werden. Möglicherweise wird es noch in Rechnungen verwendet.')
  }
}

onMounted(() => {
  loadProduct()
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

.loading {
  text-align: center;
  padding: 3rem;
  color: #6b7280;
}

.product-content {
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

.detail-value.strong {
  font-size: 1.25rem;
  font-weight: 700;
  color: #3b82f6;
}

.description {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.description h3 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #374151;
}

.description p {
  color: #6b7280;
  line-height: 1.6;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  width: fit-content;
}

.status-badge.active {
  background-color: #d1fae5;
  color: #065f46;
}

.status-badge.inactive {
  background-color: #fee2e2;
  color: #991b1b;
}

.placeholder {
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
