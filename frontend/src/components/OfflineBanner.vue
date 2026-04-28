<template>
  <div v-if="!isOnline" class="offline-banner" role="status" aria-live="polite">
    <span class="offline-icon" aria-hidden="true">⚠️</span>
    <span class="offline-text">
      Keine Internetverbindung – Änderungen können derzeit nicht gespeichert werden.
    </span>
  </div>
</template>

<script setup>
import { useNetworkStatus } from '@/composables/useNetworkStatus'

const { isOnline } = useNetworkStatus()
</script>

<style scoped>
.offline-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: #b91c1c;
  color: #fff;
  padding: 0.5rem 1rem;
  text-align: center;
  font-size: 0.875rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}
.offline-icon {
  font-size: 1rem;
}
</style>
