# Frontend Backlog - Offene Punkte & Verbesserungen

**Erstellt:** 2025-11-11
**Aktualisiert:** 2025-01-22
**Status:** AKTIV
**Priorität:** Nach Kritikalität sortiert

---

## ✅ Kürzlich behoben

### 0a. Login 404 Error - API Pfad-Problem (Teil 1)

**Problem:**

- Login schlug fehl mit "Request failed with status code 404"
- `authService.js` verwendete absolute Pfade mit führendem `/`
- Axios ignoriert `baseURL` wenn Pfad mit `/` beginnt

**Lösung:**

- Alle API-Pfade in `authService.js` von `/auth/token/` zu `auth/token/` geändert
- Betrifft: `login()`, `refreshToken()`, `fetchUserProfile()`

**Commit:** dce5f93
**Status:** ✅ BEHOBEN (2025-11-11)

---

### 0b. URL-Concatenation Problem - baseURL ohne trailing slash

**Problem:**

- Nach Fix von 0a: URLs wurden falsch konkateniert
- `baseURL: '/api'` + `'auth/user/'` = `'/apiauth/user/'` ❌
- Axios fügt kein `/` zwischen baseURL und path ein

**Lösung (Axios Standard-Konvention):**

- **baseURL muss mit `/` enden:** `/api/` ✅
- **Pfade ohne führenden `/`:** `auth/token/` ✅
- Fixed in: `client.js`, `.env.development`, `.env.production`

**Commit:** c872433
**Status:** ✅ BEHOBEN (2025-11-11)

**Lessons Learned:**
> Axios Best Practice: `baseURL: '/api/'` + `'auth/token/'` = `/api/auth/token/` ✅

---

## 🔴 Kritisch (Blocker für Production)

### 1. User-Daten werden nicht geladen ✅ BEHOBEN

**Problem:**

- AppHeader zeigte Fallback-Werte: "Benutzer" / "User"
- `useAuth` Composable lud keine echten User-Daten vom Backend

**Lösung:**

- Backend JWT enthält bereits alle benötigten User-Daten (first_name, last_name, role, permissions)
- Kein separater API-Call notwendig

**Analyse:**

- CustomTokenObtainPairSerializer fügt User-Daten direkt zum Token hinzu
- Frontend kann Daten direkt aus decodedToken auslesen

**Status:** ✅ BEHOBEN (2025-01-22) - Keine Änderung notwendig, funktioniert bereits

---

## 🟡 Wichtig (UX-Verbesserungen)

### 2. Toast-Notifications ✅ IMPLEMENTIERT

**Problem:**

- Erfolgs-/Fehlermeldungen nur in Console oder alert()
- Keine globale Notification für CRUD-Operationen

**Lösung:**

- Toast-Notification-System implementiert
- `ToastContainer` Komponente mit Teleport und Animationen
- `useToast` Composable bereits vorhanden
- Integriert in alle CRUD-Views (Invoice, BusinessPartner, Product, Company)

**Implementation:**

- Success-Toasts für create/update/delete Operationen
- Error-Toasts mit aussagekräftigen Fehlermeldungen
- 25 Unit Tests (alle bestehend)

**Commit:** 669187c
**Status:** ✅ IMPLEMENTIERT (2025-01-22)

---

### 3. Keine Loading-Spinner während API-Calls

**Problem:**

- Dashboard/Listen zeigen keine Loading-States während Datenabruf
- User weiß nicht, ob etwas passiert

**Lösung:**

- Loading-State in Views implementiert (teilweise vorhanden)
- Skeleton-Loader für bessere UX

**Status:** 🟡 TEILWEISE (nur in einigen Views)

---

### 4. Keine Confirmation-Dialogs

**Problem:**

- Delete-Actions haben nur `confirm()` (Standard-Browser-Dialog)
- Nicht konsistent mit UI-Design

**Lösung:**

- BaseConfirmDialog Komponente erstellen
- Composable `useConfirm()`

**Status:** 🔴 OFFEN

---

## 🟢 Nice-to-Have (Verbesserungen)

### 5. Keine Fehlerbehandlung bei Netzwerk-Problemen

**Problem:**

- Bei Offline/Timeout keine User-freundliche Fehlermeldung
- Nur Console-Errors

**Lösung:**

- Global Error-Handler in API-Client
- Offline-Detection

**Status:** 🔴 OFFEN

---

### 6. Keine Formular-Validierung (Client-Side)

**Problem:**

- BaseInput/BaseSelect haben keine eingebaute Validierung
- Validierung muss in jeder View manuell implementiert werden

**Lösung:**

- Vuelidate oder VeeValidate Integration
- Wiederverwendbare Validierungs-Composables

**Status:** 🔴 OFFEN

---

### 7. Fehlende Komponenten für Forms

**Problem:**

- Keine BaseTextarea
- Keine BaseCheckbox / BaseRadio
- Keine DatePicker-Integration

**Lösung:**

- Fehlende Basis-Komponenten implementieren
- VueDatePicker für Datumseingaben

**Status:** 🔴 OFFEN

---

### 8. Dashboard zeigt Dummy-Statistiken

**Problem:**

- Stats-Cards zeigen "0" Werte
- Backend hat wahrscheinlich keinen `/api/stats/` Endpoint

**Lösung:**

- Backend-Endpoint für Dashboard-Statistiken
- Frontend: Stats vom Backend laden

**Status:** 🔴 OFFEN

---

### 9. Placeholder-Views für Kunden/Produkte/Firmen

**Problem:**

- BusinessPartnerListView, ProductListView, CompanyListView sind nur Placeholder
- Keine CRUD-Funktionalität

**Lösung:**

- Vollständige List-Views nach Invoice-Muster
- Create/Edit-Forms implementieren

**Status:** 🔴 OFFEN (geplant für Phase 4)

---

### 10. Keine Infinite Scroll / Virtual Scrolling

**Problem:**

- Bei vielen Datensätzen (>100) wird Tabelle langsam
- Keine Virtualisierung

**Lösung:**

- Virtual Scroller für große Listen
- Oder: Server-Side Pagination (bereits vorhanden)

**Status:** 🟢 LOW PRIORITY

---

### 11. Keine Keyboard-Shortcuts

**Problem:**

- Keine Tastatur-Navigation (z.B. Strg+K für Suche)
- Alle Aktionen nur mit Maus

**Lösung:**

- Global Keyboard-Handler
- Shortcuts dokumentieren

**Status:** 🟢 LOW PRIORITY

---

### 12. Fehlende Accessibility-Features

**Problem:**

- Screen-Reader-Support ungetestet
- Keine Skip-Links
- Focus-Management bei Modals

**Lösung:**

- ARIA-Labels überprüfen
- Focus-Trap in Modals
- WCAG 2.1 AA Compliance

**Status:** 🟡 TEILWEISE (Basic ARIA vorhanden)

---

## 🐛 Bugs & Fixes

### 13. BaseTable: Sortierung funktioniert nicht

**Problem:**

- Sort-Event wird emitted, aber nicht verarbeitet
- Listen sortieren nicht nach Klick auf Column-Header

**Lösung:**

- `handleSort()` in Views implementieren
- API-Parameter `ordering=field` / `ordering=-field` nutzen

**Status:** 🔴 OFFEN

---

### 14. BasePagination: Page-Change verzögert

**Problem:**

- Pagination ändert Seite, aber Daten laden nicht sofort
- User sieht alte Daten kurz

**Lösung:**

- Loading-State während Page-Change
- Optimistic UI Update

**Status:** 🟡 MINOR

---

### 15. Router-Transition flackert

**Problem:**

- Fade-Transition zwischen Routes manchmal ruckelig
- Besonders bei langsamen API-Calls

**Lösung:**

- Suspense-Komponente nutzen
- Bessere Transition-Timing

**Status:** 🟢 LOW PRIORITY

---

## 🎨 Design & Styling

### 16. Responsive Design: Mobile-Optimierung

**Problem:**

- Tabellen auf Mobile schwer nutzbar
- Sidebar überlappt Content auf kleinen Screens (teilweise)

**Lösung:**

- Mobile: Card-Layout statt Tabelle
- Bessere Breakpoint-Definitionen

**Status:** 🟡 TEILWEISE (Basic Responsive vorhanden)

---

### 17. Dark Mode fehlt

**Problem:**

- Nur Light Theme verfügbar
- Keine Theme-Toggle

**Lösung:**

- CSS-Variablen für Farben
- `useTheme()` Composable
- LocalStorage-Persistierung

**Status:** 🟢 LOW PRIORITY (Future Enhancement)

---

### 18. Keine Animationen/Transitions

**Problem:**

- UI fühlt sich statisch an
- Keine Micro-Interactions

**Lösung:**

- Subtile Animations hinzufügen
- Loading-Skeletons statt Spinner

**Status:** 🟢 LOW PRIORITY

---

## 📦 Code-Qualität & Testing

### 19. Keine Component-Tests

**Problem:**

- Basis-Komponenten haben keine Unit-Tests
- Regression-Gefahr bei Änderungen

**Lösung:**

- Vitest Tests für alle Base-Komponenten
- Test-Coverage >80%

**Status:** 🔴 OFFEN (geplant)

---

### 20. Keine E2E-Tests

**Problem:**

- User-Flows ungetestet
- Login → Dashboard → Invoice-Create manuell

**Lösung:**

- Playwright E2E-Tests
- CI/CD Integration

**Status:** 🔴 OFFEN (geplant)

---

### 21. Keine Error-Boundaries

**Problem:**

- Vue-Komponenten-Fehler crashen gesamte App
- Keine Fallback-UI

**Lösung:**

- Error-Boundary-Komponente
- Sentry-Integration für Error-Tracking

**Status:** 🔴 OFFEN

---

## 🔧 Technische Schulden

### 22. Debug-Logs in Production

**Problem:**

- `console.log()` in authService und apiClient
- Performance-Impact

**Lösung:**

- Nur in Development loggen: `if (import.meta.env.DEV)`
- Oder: Logging-Library mit Levels

**Status:** 🟡 TODO (vor Production)

---

### 23. Hardcoded Container-Name im Vite-Proxy

**Problem:**

- `target: 'https://erechnung-api-gateway-1'`
- Nicht portabel für andere Environments

**Lösung:**

- Environment-Variable: `VITE_PROXY_TARGET`
- Oder: Service-Alias im Docker-Network

**Status:** 🟡 TODO (vor Multi-Environment-Deployment)

---

### 24. Keine Code-Splitting-Strategie

**Problem:**

- Alle Komponenten in einem Bundle
- Initiale Load-Zeit könnte optimiert werden

**Lösung:**

- Route-basiertes Code-Splitting (bereits teilweise via Lazy-Loading)
- Component-Lazy-Loading für große Komponenten

**Status:** 🟢 LOW PRIORITY (bereits Lazy-Routes)

---

## 📋 Nächste Schritte (Priorisierung)

### Sprint 1: Kritische Fixes

1. ✅ User-Daten laden (#1)
2. ✅ Toast-Notifications (#2)
3. ✅ Confirmation-Dialogs (#4)

### Sprint 2: Forms & Validierung

4. ✅ Client-Side-Validierung (#6)
5. ✅ Fehlende Form-Komponenten (#7)
6. ✅ BusinessPartner/Product/Company CRUD (#9)

### Sprint 3: Testing & Qualität

7. ✅ Component-Tests (#19)
8. ✅ E2E-Tests (#20)
9. ✅ Error-Boundaries (#21)

### Sprint 4: Polish & Production

10. ✅ Debug-Logs entfernen (#22)
11. ✅ Accessibility-Review (#12)
12. ✅ Performance-Optimierung

---

## 🏷️ Labels

- 🔴 **OFFEN** - Noch nicht begonnen
- 🟡 **TEILWEISE** - In Arbeit oder teilweise implementiert
- 🟢 **LOW PRIORITY** - Nice-to-Have, nicht kritisch
- ✅ **ERLEDIGT** - Abgeschlossen

---

**Zuletzt aktualisiert:** 2025-11-11 15:00 Uhr
