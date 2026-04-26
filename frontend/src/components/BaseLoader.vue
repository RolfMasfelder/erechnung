<template>
  <!-- Overlay Loader (Full Page) -->
  <div v-if="overlay && isVisible" class="fixed inset-0 bg-gray-900/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg p-6 shadow-xl">
      <SpinnerLoader :size="size" />
      <p v-if="message" class="mt-4 text-gray-700 text-center">{{ message }}</p>
    </div>
  </div>

  <!-- Skeleton Loader -->
  <div v-else-if="type === 'skeleton' && isVisible" class="space-y-3">
    <div v-for="i in rows" :key="i" class="skeleton-box" :style="{ height: rowHeight }"></div>
  </div>

  <!-- Inline Spinner -->
  <SpinnerLoader v-else-if="type === 'spinner' && isVisible" :size="size" :inline="inline" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // Type of loader: 'spinner', 'skeleton'
  type: {
    type: String,
    default: 'spinner',
    validator: (value) => ['spinner', 'skeleton'].includes(value)
  },
  // Size for spinner: 'sm', 'md', 'lg'
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  // Number of skeleton rows
  rows: {
    type: Number,
    default: 5
  },
  // Height of each skeleton row
  rowHeight: {
    type: String,
    default: '3rem'
  },
  // Show as full-page overlay
  overlay: {
    type: Boolean,
    default: false
  },
  // Message to show with overlay loader
  message: {
    type: String,
    default: ''
  },
  // Display inline (for buttons etc.)
  inline: {
    type: Boolean,
    default: false
  },
  // Control visibility
  loading: {
    type: Boolean,
    default: true
  }
})

const isVisible = computed(() => props.loading)
</script>

<script>
// SpinnerLoader Sub-Component
import { h } from 'vue'

const SpinnerLoader = {
  props: {
    size: {
      type: String,
      default: 'md',
      validator: (value) => ['sm', 'md', 'lg'].includes(value)
    },
    inline: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const sizeClasses = {
      sm: 'h-4 w-4 border-2',
      md: 'h-8 w-8 border-2',
      lg: 'h-12 w-12 border-3'
    }

    const containerClass = props.inline
      ? 'inline-flex items-center justify-center'
      : 'flex items-center justify-center p-4'

    return () => h('div', { class: containerClass }, [
      h('div', {
        class: `${sizeClasses[props.size]} border-gray-300 border-t-primary rounded-full animate-spin`,
        role: 'status',
        'aria-label': 'Lädt...'
      }, [
        h('span', { class: 'sr-only' }, 'Lädt...')
      ])
    ])
  }
}

export { SpinnerLoader }
</script>

<style scoped>
/* Skeleton Box Animation */
.skeleton-box {
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
  border-radius: 0.375rem;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .skeleton-box {
    background: linear-gradient(
      90deg,
      #2d2d2d 25%,
      #3d3d3d 50%,
      #2d2d2d 75%
    );
    background-size: 200% 100%;
  }
}
</style>
