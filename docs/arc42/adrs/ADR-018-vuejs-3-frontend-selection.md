# ADR 018: Vue.js 3 Framework Selection for Frontend SPA

## Status

Accepted (November 2025)

## Date

2025-11-10

## Context

Following ADR-009 (Frontend Architecture and API-First Approach), we decided on an API-first architecture with independent frontend applications. Now we need to select a specific JavaScript framework for the Single Page Application (SPA) implementation.

### Requirements

1. **Modern Framework**: Must support Composition API and reactive programming
2. **Ecosystem**: Rich ecosystem with routing, state management, and UI libraries
3. **Performance**: Fast initial load and runtime performance
4. **Developer Experience**: Good tooling, TypeScript support, hot module replacement
5. **Bundle Size**: Small production bundle size
6. **Learning Curve**: Reasonable learning curve for team
7. **Community**: Active community and long-term support

### Framework Candidates

1. **Vue.js 3**: Progressive framework with Composition API
2. **React 18**: Library with extensive ecosystem
3. **Angular 17**: Full-featured framework with TypeScript
4. **Svelte 4**: Compiler-based framework with reactive programming

## Decision

**We choose Vue.js 3 (version 3.5.24) for the eRechnung frontend SPA.**

### Technology Stack

**Core Framework:**

- Vue.js 3.5.24 with Composition API
- Vue Router 4.6.3 for client-side routing
- Pinia 3.0.4 for state management

**Build Tooling:**

- Vite 7.2.2 for fast development builds and HMR
- Vitest 4.0.8 for unit testing

**Styling:**

- Tailwind CSS 4.1.17 for utility-first CSS

**HTTP Client:**

- Axios 1.13.2 with JWT interceptors

**Testing:**

- Vitest + @vue/test-utils for unit tests
- Playwright for E2E tests (see ADR-019)

## Rationale

### Why Vue.js 3?

**1. Composition API Excellence:**

```javascript
// Clean, reusable composables for business logic
export function useAuth() {
  const authStore = useAuthStore()
  const router = useRouter()

  const login = async (credentials) => {
    await authStore.login(credentials)
    router.push('/')
  }

  return { login, isAuthenticated: computed(() => authStore.isAuthenticated) }
}
```

**2. Excellent Performance:**

- Small bundle size: ~30KB runtime (gzipped)
- Virtual DOM with compiler optimizations
- Automatic static tree hoisting
- Fast SSR support (future-ready for SEO)

**3. Developer Experience:**

- Single File Components (SFC) with `<script setup>` syntax
- Excellent TypeScript support
- Vite integration for instant HMR
- Vue DevTools for debugging

**4. Ecosystem Maturity:**

- Pinia for intuitive state management
- Vue Router for declarative routing
- Rich UI component libraries (Headless UI, Radix Vue)
- Extensive community plugins

**5. Progressive Enhancement:**

- Can be incrementally adopted
- Works well with Django templates if needed
- Easy migration path from Vue 2

**6. Real-World Success:**

- Used by Alibaba, Xiaomi, Nintendo, GitLab
- Proven at scale (millions of users)
- Long-term support from core team

### Why Not React?

- Larger ecosystem but steeper learning curve
- JSX syntax requires mental context switching
- useState/useEffect hooks more complex than Vue's reactivity
- Larger bundle size (~45KB react + react-dom)

### Why Not Angular?

- Too heavyweight for our needs (full framework with RxJS)
- Steeper learning curve with TypeScript requirements
- Larger bundle size and slower initial load
- Over-engineering for invoice management app

### Why Not Svelte?

- Excellent but smaller ecosystem
- Fewer enterprise-ready UI libraries
- Less mature state management solutions
- Smaller talent pool for hiring

## Implementation Details

### Project Structure

```txt
frontend/
├── src/
│   ├── api/           # API client and services
│   ├── assets/        # Static assets
│   ├── components/    # Reusable UI components
│   │   ├── base/      # Base components (Button, Input, etc.)
│   │   └── features/  # Feature-specific components
│   ├── composables/   # Vue composables (useAuth, useInvoices, etc.)
│   ├── router/        # Vue Router configuration
│   ├── stores/        # Pinia stores
│   ├── views/         # Page components
│   ├── App.vue        # Root component
│   └── main.js        # Application entry point
├── tests/
│   ├── unit/          # Vitest unit tests
│   └── e2e/           # Playwright E2E tests
├── index.html
├── vite.config.js
└── package.json
```

### Key Patterns

**Composables for Logic Reuse:**

```javascript
// composables/useInvoices.js
export function useInvoices() {
  const invoices = ref([])
  const loading = ref(false)

  const fetchInvoices = async (filters) => {
    loading.value = true
    invoices.value = await invoiceService.list(filters)
    loading.value = false
  }

  return { invoices, loading, fetchInvoices }
}
```

**Pinia Stores for Global State:**

```javascript
// stores/auth.js
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token'))
  const isAuthenticated = computed(() => !!token.value)

  const login = async (credentials) => {
    const response = await authService.login(credentials)
    token.value = response.access
    localStorage.setItem('token', response.access)
  }

  return { token, isAuthenticated, login }
})
```

## Consequences

### Positive

- **Fast Development**: Vite HMR enables instant feedback
- **Clean Code**: Composition API promotes code reuse
- **Small Bundle**: Fast initial page load (<300KB gzipped)
- **Good DX**: Excellent tooling and debugging experience
- **Future-Proof**: Active development with regular updates

### Negative

- **Learning Curve**: Team needs to learn Vue.js 3 patterns
- **Ecosystem Lock-in**: Committed to Vue.js ecosystem
- **Migration Effort**: Django templates need to be replaced

### Neutral

- **No SSR Initially**: Client-side rendering only (can add SSR later with Nuxt)
- **API Dependency**: Requires robust REST API (already planned)

## Alternatives Considered

1. **Keep Django Templates**: Rejected due to limited interactivity and modern UX requirements
2. **React 18**: Considered but Vue.js offered better DX and smaller footprint
3. **Alpine.js**: Too limited for complex SPA requirements

## Related Decisions

- ADR-009: Frontend Architecture and API-First Approach (parent decision)
- ADR-019: Playwright for E2E Testing (testing strategy)
- ADR-005: JWT Authentication (authentication mechanism used in frontend)

## Milestones

- **Phase 1** (November 2025): Project setup with Vite, Vue Router, Pinia
- **Phase 2** (November 2025): API client with JWT interceptors
- **Phase 3** (November 2025): Base UI components
- **Phase 4** (November 2025): CRUD views with modals (144 tests, 94.4% pass-rate)
- **Phase 5** (December 2025): UI/UX enhancements (381 tests, +101 new)
- **Phase 6** (January 2026): Advanced features (filtering, bulk ops, export/import)

## References

- Vue.js 3 Documentation: <https://vuejs.org/>
- Composition API RFC: <https://github.com/vuejs/rfcs/blob/master/active-rfcs/0013-composition-api.md>
- Vite Documentation: <https://vitejs.dev/>
- Pinia Documentation: <https://pinia.vuejs.org/>
