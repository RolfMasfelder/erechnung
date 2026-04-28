<template>
  <BaseModal :isOpen="true" @close="$emit('close')" title="Passwort ändern" size="sm">
    <form @submit.prevent="submit" class="password-form">
      <div class="form-row">
        <label for="current_password">Aktuelles Passwort</label>
        <input
          id="current_password"
          v-model="form.currentPassword"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>

      <div class="form-row">
        <label for="new_password">Neues Passwort</label>
        <input
          id="new_password"
          v-model="form.newPassword"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </div>

      <div class="form-row">
        <label for="confirm_password">Neues Passwort bestätigen</label>
        <input
          id="confirm_password"
          v-model="form.confirmPassword"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </div>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </form>

    <template #footer>
      <button type="button" class="btn btn-secondary" @click="$emit('close')">
        Abbrechen
      </button>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="submitting"
        @click="submit"
      >
        {{ submitting ? 'Speichern…' : 'Passwort ändern' }}
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { reactive, ref } from 'vue'
import BaseModal from './BaseModal.vue'
import { settingsService } from '../api/services/settingsService'

const emit = defineEmits(['close', 'changed'])

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  if (form.newPassword !== form.confirmPassword) {
    error.value = 'Die neuen Passwörter stimmen nicht überein.'
    return
  }
  if (form.newPassword.length < 8) {
    error.value = 'Das neue Passwort muss mindestens 8 Zeichen lang sein.'
    return
  }

  submitting.value = true
  try {
    await settingsService.changePassword({
      currentPassword: form.currentPassword,
      newPassword: form.newPassword,
    })
    emit('changed')
    emit('close')
  } catch (err) {
    error.value =
      err?.response?.data?.detail ?? 'Passwortänderung fehlgeschlagen.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.password-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
label {
  font-weight: 600;
  font-size: 0.875rem;
}
input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}
.error {
  color: #b91c1c;
  font-size: 0.875rem;
  margin: 0;
}
.btn {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn-secondary {
  background: #f3f4f6;
  border-color: #d1d5db;
}
.btn-primary {
  background: #2563eb;
  color: white;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
