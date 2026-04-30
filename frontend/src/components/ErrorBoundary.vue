<script setup>
import { ref, onErrorCaptured } from 'vue'

defineProps({
  fallbackTitle: {
    type: String,
    default: 'Etwas ist schiefgelaufen'
  },
  fallbackMessage: {
    type: String,
    default: 'Es ist ein unerwarteter Fehler aufgetreten. Bitte versuchen Sie es erneut.'
  }
})

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((err) => {
  hasError.value = true
  errorMessage.value = err?.message || String(err)

  if (import.meta.env.DEV) {
    console.error('🛑 ErrorBoundary caught:', err)
  }

  // Prevent the error from propagating further so the whole app does not crash.
  return false
})

function reset() {
  hasError.value = false
  errorMessage.value = ''
}
</script>

<template>
  <div v-if="hasError" class="error-boundary" role="alert">
    <div class="error-boundary__card">
      <h2 class="error-boundary__title">{{ fallbackTitle }}</h2>
      <p class="error-boundary__message">{{ fallbackMessage }}</p>
      <pre v-if="$attrs.showDetails !== false && errorMessage" class="error-boundary__details">{{ errorMessage }}</pre>
      <div class="error-boundary__actions">
        <button type="button" class="error-boundary__button" @click="reset">
          Erneut versuchen
        </button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  min-height: 50vh;
}

.error-boundary__card {
  max-width: 32rem;
  padding: 2rem;
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.error-boundary__title {
  margin: 0 0 0.75rem;
  color: #b91c1c;
  font-size: 1.25rem;
  font-weight: 600;
}

.error-boundary__message {
  margin: 0 0 1rem;
  color: #374151;
}

.error-boundary__details {
  margin: 0 0 1rem;
  padding: 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.375rem;
  color: #7f1d1d;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.error-boundary__actions {
  display: flex;
  justify-content: flex-end;
}

.error-boundary__button {
  padding: 0.5rem 1rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 0.375rem;
  font-weight: 500;
  cursor: pointer;
}

.error-boundary__button:hover {
  background: #1d4ed8;
}
</style>
