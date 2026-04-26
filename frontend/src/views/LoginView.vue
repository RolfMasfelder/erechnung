<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import BaseInput from '@/components/BaseInput.vue'
import BaseButton from '@/components/BaseButton.vue'
import BaseAlert from '@/components/BaseAlert.vue'

const router = useRouter()
const { login } = useAuth()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  if (!username.value || !password.value) {
    error.value = 'Bitte Benutzername und Passwort eingeben'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await login(username.value, password.value)

    // Erfolgreicher Login - zur Startseite navigieren
    await router.push('/')
  } catch (err) {
    console.error('Login failed:', err)

    // Fehlermeldung anzeigen
    if (err.response?.status === 401) {
      error.value = 'Ungültige Anmeldedaten. Bitte überprüfen Sie Benutzername und Passwort.'
    } else if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else if (err.message) {
      error.value = err.message
    } else {
      error.value = 'Login fehlgeschlagen. Bitte versuchen Sie es später erneut.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1 class="login-title">⚡ eRechnung System</h1>
        <p class="login-subtitle">Bitte melden Sie sich an</p>
      </div>

      <BaseAlert
        v-if="error"
        type="error"
        :message="error"
        :closable="true"
        @close="error = ''"
      />

      <form class="login-form" @submit.prevent="handleLogin">
        <BaseInput
          v-model="username"
          label="Benutzername"
          type="text"
          placeholder="Benutzername eingeben"
          required
          :disabled="loading"
        />

        <BaseInput
          v-model="password"
          label="Passwort"
          type="password"
          placeholder="Passwort eingeben"
          required
          :disabled="loading"
        />

        <BaseButton
          type="submit"
          variant="primary"
          size="lg"
          block
          :loading="loading"
        >
          Anmelden
        </BaseButton>
      </form>

      <div class="login-footer">
        <p class="version-info">Version 1.0.0</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
}

.login-container {
  width: 100%;
  max-width: 28rem;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  padding: 2rem;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.875rem;
  font-weight: 700;
  color: #111827;
}

.login-subtitle {
  margin: 0;
  font-size: 0.875rem;
  color: #6b7280;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.login-footer {
  margin-top: 2rem;
  text-align: center;
}

.version-info {
  margin: 0;
  font-size: 0.75rem;
  color: #9ca3af;
}
</style>
