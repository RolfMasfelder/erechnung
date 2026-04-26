<template>
  <nav class="pagination" aria-label="Pagination">
    <button
      class="pagination-btn pagination-prev"
      :disabled="currentPage <= 1"
      @click="handlePageChange(currentPage - 1)"
      aria-label="Vorherige Seite"
    >
      ‹ Zurück
    </button>

    <div class="pagination-pages">
      <button
        v-for="page in visiblePages"
        :key="page"
        :class="['pagination-page', { 'pagination-active': page === currentPage }]"
        :disabled="page === '...'"
        @click="page !== '...' && handlePageChange(page)"
      >
        {{ page }}
      </button>
    </div>

    <button
      class="pagination-btn pagination-next"
      :disabled="currentPage >= totalPages"
      @click="handlePageChange(currentPage + 1)"
      aria-label="Nächste Seite"
    >
      Weiter ›
    </button>
  </nav>

  <div v-if="showInfo" class="pagination-info">
    Zeige {{ rangeStart }} bis {{ rangeEnd }} von {{ total }} Einträgen
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: {
    type: Number,
    required: true
  },
  totalPages: {
    type: Number,
    required: true
  },
  total: {
    type: Number,
    default: 0
  },
  perPage: {
    type: Number,
    default: 10
  },
  maxVisiblePages: {
    type: Number,
    default: 5
  },
  showInfo: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:currentPage', 'change'])

const visiblePages = computed(() => {
  const pages = []
  const { currentPage, totalPages, maxVisiblePages } = props

  if (totalPages <= maxVisiblePages) {
    // Show all pages
    for (let i = 1; i <= totalPages; i++) {
      pages.push(i)
    }
  } else {
    // Show subset with ellipsis
    const half = Math.floor(maxVisiblePages / 2)
    let start = currentPage - half
    let end = currentPage + half

    if (start < 1) {
      start = 1
      end = maxVisiblePages
    }

    if (end > totalPages) {
      end = totalPages
      start = totalPages - maxVisiblePages + 1
    }

    if (start > 1) {
      pages.push(1)
      if (start > 2) pages.push('...')
    }

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (end < totalPages) {
      if (end < totalPages - 1) pages.push('...')
      pages.push(totalPages)
    }
  }

  return pages
})

const rangeStart = computed(() => {
  return (props.currentPage - 1) * props.perPage + 1
})

const rangeEnd = computed(() => {
  const end = props.currentPage * props.perPage
  return end > props.total ? props.total : end
})

const handlePageChange = (page) => {
  if (page >= 1 && page <= props.totalPages && page !== props.currentPage) {
    emit('update:currentPage', page)
    emit('change', page)
  }
}
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 1.5rem 0;
}

.pagination-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  background: white;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  gap: 0.25rem;
}

.pagination-page {
  min-width: 2.5rem;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  background: white;
  color: #374151;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-page:hover:not(:disabled):not(.pagination-active) {
  background-color: #f9fafb;
  border-color: #9ca3af;
}

.pagination-page:disabled {
  cursor: default;
  border-color: transparent;
}

.pagination-active {
  background-color: #3b82f6;
  border-color: #3b82f6;
  color: white;
  font-weight: 600;
}

.pagination-info {
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
  margin-top: 0.5rem;
}
</style>
