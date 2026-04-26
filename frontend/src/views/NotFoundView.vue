<template>
  <div class="not-found">
    <BaseCard>
      <div class="not-found-content">
        <h1 class="error-code">404</h1>
        <h2 class="error-title">Seite nicht gefunden</h2>
        <p class="error-text">
          Die angeforderte Seite existiert nicht oder wurde verschoben.
        </p>
        <div class="error-actions">
          <BaseButton variant="primary" @click="goHome">
            Zur Startseite
          </BaseButton>
          <BaseButton variant="secondary" @click="goBack">
            Zurück
          </BaseButton>
        </div>
      </div>
    </BaseCard>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.not-found {
  max-width: 600px;
  margin: 0 auto;
  padding-top: 5rem;
}

.not-found-content {
  text-align: center;
  padding: 3rem 2rem;
}

.error-code {
  margin: 0 0 1rem 0;
  font-size: 6rem;
  font-weight: 900;
  color: #3b82f6;
  line-height: 1;
}

.error-title {
  margin: 0 0 1rem 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
}

.error-text {
  margin: 0 0 2rem 0;
  color: #6b7280;
}

.error-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}
</style>
