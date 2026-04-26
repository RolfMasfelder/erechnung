<script setup>
import { ref } from 'vue'

const message = ref('eRechnung Frontend - Development Mode')
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="max-w-4xl mx-auto">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">
        {{ message }}
      </h1>
      <div class="bg-white shadow-md rounded-lg p-6">
        <h2 class="text-2xl font-semibold mb-4">Willkommen</h2>
        <p class="text-gray-700">
          eRechnung System - Entwicklungsmodus aktiv
        </p>
        <div class="mt-6">
          <p class="text-sm text-gray-500">
            Umgebung: {{ import.meta.env.MODE }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
