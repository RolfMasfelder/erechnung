<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import ToastContainer from '@/components/ToastContainer.vue'
import BaseConfirmDialog from '@/components/BaseConfirmDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useNetworkStatus } from '@/composables/useNetworkStatus'

const route = useRoute()
const { isOpen, dialogConfig, handleConfirm, handleCancel } = useConfirm()

// Initialize network status monitoring
useNetworkStatus()

// Routes that should not use the main layout (e.g., Login)
const publicRoutes = ['Login', 'NotFound']
const useLayout = computed(() => !publicRoutes.includes(route.name))
</script>

<template>
  <div id="app">
    <AppLayout v-if="useLayout">
      <router-view />
    </AppLayout>
    <router-view v-else />

    <!-- Global Toast Notifications -->
    <ToastContainer />

    <!-- Global Confirmation Dialog -->
    <BaseConfirmDialog
      :isOpen="isOpen"
      :title="dialogConfig.title"
      :message="dialogConfig.message"
      :variant="dialogConfig.variant"
      :confirmText="dialogConfig.confirmText"
      :cancelText="dialogConfig.cancelText"
      @confirm="handleConfirm"
      @cancel="handleCancel"
    />
  </div>
</template>

<style>
/* Global styles */
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
}
</style>
