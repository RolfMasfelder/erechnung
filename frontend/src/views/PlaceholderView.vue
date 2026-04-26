<template>
  <div class="placeholder-view">
    <BaseCard>
      <div class="placeholder-content">
        <h1 class="placeholder-title">{{ title }}</h1>
        <p class="placeholder-text">
          Diese Seite wird in Phase 4 implementiert.
        </p>
        <BaseButton variant="primary" @click="goBack">
          Zurück
        </BaseButton>
      </div>
    </BaseCard>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'

defineProps({
  title: {
    type: String,
    default: 'Seite in Entwicklung'
  }
})

const router = useRouter()

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.placeholder-view {
  max-width: 600px;
  margin: 0 auto;
  padding-top: 3rem;
}

.placeholder-content {
  text-align: center;
  padding: 3rem 2rem;
}

.placeholder-title {
  margin: 0 0 1rem 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
}

.placeholder-text {
  margin: 0 0 2rem 0;
  color: #6b7280;
}
</style>
