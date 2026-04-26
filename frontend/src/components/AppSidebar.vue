<template>
  <aside
    class="app-sidebar"
    :class="{ 'sidebar-open': isOpen }"
  >
    <div class="sidebar-overlay" @click="$emit('close')"></div>

    <nav class="sidebar-content">
      <div class="nav-section">
        <h3 class="nav-section-title">Hauptmenü</h3>

        <router-link
          to="/"
          class="nav-link"
          active-class="nav-link-active"
          exact
        >
          <span class="nav-icon">📊</span>
          <span class="nav-text">Dashboard</span>
        </router-link>
      </div>

      <div class="nav-section">
        <h3 class="nav-section-title">Rechnungswesen</h3>

        <router-link
          to="/invoices"
          class="nav-link"
          active-class="nav-link-active"
        >
          <span class="nav-icon">📄</span>
          <span class="nav-text">Rechnungen</span>
        </router-link>

        <router-link
          to="/business-partners"
          class="nav-link"
          active-class="nav-link-active"
        >
          <span class="nav-icon">👥</span>
          <span class="nav-text">Geschäftspartner</span>
        </router-link>

        <router-link
          to="/products"
          class="nav-link"
          active-class="nav-link-active"
        >
          <span class="nav-icon">📦</span>
          <span class="nav-text">Produkte</span>
        </router-link>
      </div>

      <div class="nav-section">
        <h3 class="nav-section-title">Verwaltung</h3>

        <router-link
          to="/companies"
          class="nav-link"
          active-class="nav-link-active"
        >
          <span class="nav-icon">🏢</span>
          <span class="nav-text">Firmen</span>
        </router-link>

        <router-link
          to="/settings"
          class="nav-link"
          active-class="nav-link-active"
        >
          <span class="nav-icon">⚙️</span>
          <span class="nav-text">Einstellungen</span>
        </router-link>
      </div>
    </nav>
  </aside>
</template>

<script setup>
defineProps({
  isOpen: {
    type: Boolean,
    default: true
  }
})

defineEmits(['close'])
</script>

<style scoped>
.app-sidebar {
  position: relative;
  width: 16rem;
  background: white;
  border-right: 1px solid #e5e7eb;
  transition: transform 0.3s ease-in-out;
}

.sidebar-overlay {
  display: none;
}

.sidebar-content {
  height: 100%;
  overflow-y: auto;
  padding: 1.5rem 0;
}

.nav-section {
  margin-bottom: 1.5rem;
}

.nav-section-title {
  padding: 0 1.5rem;
  margin: 0 0 0.5rem 0;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #9ca3af;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.5rem;
  color: #374151;
  text-decoration: none;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-link:hover {
  background-color: #f9fafb;
  color: #111827;
}

.nav-link-active {
  background-color: #eff6ff;
  color: #3b82f6;
  border-left-color: #3b82f6;
  font-weight: 600;
}

.nav-icon {
  font-size: 1.25rem;
}

.nav-text {
  font-size: 0.875rem;
}

/* Mobile Styles */
@media (max-width: 768px) {
  .app-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 200;
    transform: translateX(-100%);
  }

  .sidebar-open {
    transform: translateX(0);
  }

  .sidebar-open .sidebar-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: -1;
  }
}
</style>
