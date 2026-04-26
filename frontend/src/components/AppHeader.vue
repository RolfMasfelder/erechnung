<template>
  <header class="app-header">
    <div class="header-left">
      <button
        class="menu-toggle"
        @click="$emit('toggle-sidebar')"
        aria-label="Toggle Sidebar"
      >
        ☰
      </button>

      <h1 class="app-title">
        <span class="title-icon">⚡</span>
        eRechnung System
      </h1>
    </div>

    <nav class="header-right">
      <div class="user-info">
        <span class="user-name">{{ displayName }}</span>
        <span class="user-role">{{ displayRole }}</span>
      </div>

      <BaseButton
        variant="secondary"
        size="sm"
        @click="handleLogout"
      >
        Abmelden
      </BaseButton>
    </nav>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { useRouter } from 'vue-router'
import BaseButton from './BaseButton.vue'

defineEmits(['toggle-sidebar'])

const { currentUser, logout } = useAuth()
const router = useRouter()

// Display name: First + Last name, oder Username als Fallback
const displayName = computed(() => {
  if (!currentUser.value) return 'Benutzer'

  const { first_name, last_name, username } = currentUser.value
  if (first_name && last_name) {
    return `${first_name} ${last_name}`
  }
  return username || 'Benutzer'
})

// Display role: Name from role object, or fallback to role type
const displayRole = computed(() => {
  if (!currentUser.value) return 'User'

  const { role, is_superuser } = currentUser.value

  if (is_superuser) return 'Administrator'
  if (role && role.name) return role.name
  if (role && role.role_type) return role.role_type

  return 'User'
})

const handleLogout = async () => {
  logout()
  await router.push('/login')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.menu-toggle {
  display: none;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #374151;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 0.375rem;
  transition: background-color 0.2s;
}

.menu-toggle:hover {
  background-color: #f3f4f6;
}

.app-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #111827;
}

.title-icon {
  font-size: 1.5rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
}

.user-role {
  font-size: 0.75rem;
  color: #6b7280;
}

@media (max-width: 768px) {
  .app-header {
    padding: 1rem;
  }

  .menu-toggle {
    display: block;
  }

  .user-info {
    display: none;
  }
}
</style>
