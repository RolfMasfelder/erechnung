# Next Steps — eRechnung v0.1.4

> Erstellt: 28. April 2026
> Quelle: Analyse `TODO_2026.md` + Codebase-Verifikation
> Ziel: Iterativ abarbeitbare, priorisierte Liste der nächsten Schritte

Stand der Codebase verifiziert:
- ✅ `frontend/src/views/SettingsView.vue` ist 7-Zeilen-Placeholder
- ✅ `frontend/src/api/client.js`: 3× `console.log` (Zeilen 36, 56, 60)
- ✅ Kein GDPdU-Code im Backend vorhanden
- ✅ Keine `ErrorBoundary.vue` Komponente vorhanden

---

## Empfohlene Reihenfolge (in Iterationen)

Die Iterationen sind so geschnitten, dass jede für sich abgeschlossen werden kann
(eigener Branch, eigener Commit, eigener Release möglich) und in 2–8 Stunden machbar ist.

| # | Iteration | Priorität | Aufwand | Risiko |
|---|-----------|-----------|---------|--------|
| 1 | Frontend Quick-Wins (console.log + ErrorBoundary) | HOCH | 2–4h | niedrig |
| 2 | Update-System Pre-Flight-Test | HOCH | 1h | niedrig |
| 3 | Import/Export Architekturentscheidungen | HOCH | 0.5h | niedrig |
| 4 | GDPdU-Export Backend (Service + Tests) | HOCH | 6–10h | mittel |
| 5 | SettingsView Backend (Model + API) | MITTEL | 4–6h | niedrig |
| 6 | SettingsView Frontend (UI + Service) | MITTEL | 4–6h | niedrig |
| 7 | Frontend Offline/Network Error Handling | MITTEL | 1–2h | niedrig |
| 8 | E2E Tests Phase 3 (Stabilisierung) | NIEDRIG | 4–6h | mittel |
| 9 | XRechnung E-Mail-Versand (3.11 Stufe 2) | NIEDRIG | 4–6h | niedrig |
| 10 | Performance-Validierung (Load-Tests) | NIEDRIG | 6–10h | mittel |

**Summe Iteration 1–7 (kurzfristig sinnvoll):** ~19–29h

---

## Iteration 1: Frontend Quick-Wins (2–4h)

**Ziel:** Technische Schulden im Frontend beheben — schneller PR, niedriges Risiko.

### 1.1 Debug-Logs aus Production entfernen
- [x] [frontend/src/api/client.js](frontend/src/api/client.js) — 3× `console.log` umschließen mit `if (import.meta.env.DEV)`
  - Zeile 36: `📡 API Request`
  - Zeile 56: `✅ API Response`
  - Zeile 60: `❌ API Error`
- [x] Workspace nach weiteren `console.log` durchsuchen, die nicht DEV-gated sind
- [x] Prüfen: `frontend/src/services/authService.js` (laut Backlog 3 Stellen — aktuell nicht gefunden, ggf. bereits erledigt)

### 1.2 ErrorBoundary-Komponente
- [x] `frontend/src/components/ErrorBoundary.vue` erstellen
  - Verwendet `onErrorCaptured` Hook
  - Zeigt Fallback-UI mit "Erneut versuchen"-Button
  - Loggt Fehler via existierendem Logger (`frontend/src/utils/logger.js` falls vorhanden)
- [x] In `App.vue` um `<RouterView />` wrappen
- [x] Unit-Test: Fehler in Child-Komponente → Fallback wird angezeigt

### 1.3 Akzeptanzkriterien
- Build (`npm run build`) wirft keine `console.log` mehr in `dist/`
- ErrorBoundary fängt Fehler in mindestens einer View ab (manueller Test)

**Quelle:** TODO_2026.md §3.15
**Branch:** `feat/frontend-quick-wins`

---

## Iteration 2: Update-System Pre-Flight-Test (1h)

**Ziel:** Mock-Test für fehlenden Docker-Daemon im Pre-Flight.

- [x] Test schreiben in `project_root/invoice_app/tests/test_update_preflight.py` (Pfad ggf. anpassen)
- [x] Mock: `subprocess.run('docker', 'info')` wirft `FileNotFoundError`
- [x] Erwartung: Pre-Flight-Check schlägt mit eindeutiger Fehlermeldung fehl

**Quelle:** TODO_2026.md §3.13
**Branch:** `test/update-preflight-mock`

---

## Iteration 3: Import/Export Architekturentscheidungen (0.5h)

**Ziel:** Zwei offene Architekturfragen entscheiden und in ADR/TODO festhalten.

### Entscheidungen
- [x] **Async exports via Celery?**
  - Option A: Jetzt integrieren (Phase 4 startet damit)
  - Option B: Später, sobald reale Lastprobleme auftreten
  - Entscheidungskriterien: aktuelle Export-Größen, Nutzerzahl
- [x] **Audit-Log-Granularität bei Import?**
  - Option A: Pro Datensatz (volle Nachvollziehbarkeit, hohes Volumen)
  - Option B: Zusammenfassung pro Import-Job (kompakt, GoBD-grenzwertig)

### Ergebnis dokumentieren
- [x] Falls neuer ADR nötig: `docs/arc42/ADR-018-import-export.md`
- [x] Sonst: Entscheidungen in `TODO_2026.md` §3.14 als Note vermerken

**Quelle:** TODO_2026.md §3.14
**Branch:** `docs/import-export-decisions`

---

## Iteration 4: GDPdU-Export (6–10h)

**Ziel:** Letzte offene GoBD-Anforderung — Export für Finanzbehörden (Betriebsprüfung).

### Hintergrund
GoBD-Locking, Hashing, Audit-Chain und Aufbewahrung sind vollständig (43 Tests in `test_gobd_compliance.py`). Es fehlt nur der GDPdU-Export-Service nach BMF-Schreiben (CSV + index.xml + ZIP).

### 4.1 Service implementieren
- [x] `invoice_app/services/gdpdu_export_service.py`
  - Methode: `export_period(start_date, end_date) -> bytes` (ZIP-Bytes)
  - CSV-Tabellen: `invoices.csv`, `invoice_lines.csv`, `business_partners.csv`
  - `index.xml` nach GDPdU-DTD ([Beispiel BMF](https://www.bzst.de))
  - Verschlüsselung: NICHT erforderlich (BMF-Spec), aber Hash der ZIP für Audit-Log

### 4.2 API-Endpoint
- [x] `GET /api/gdpdu/export/?start=YYYY-MM-DD&end=YYYY-MM-DD` (Admin-only)
- [x] Response: `application/zip` mit Content-Disposition
- [x] Audit-Log-Eintrag: wer, wann, welcher Zeitraum
- [x] `docs/openapi.json` aktualisieren (Single Source of Truth)

### 4.3 Tests
- [x] `index.xml` entspricht GDPdU-DTD (xmllint validation)
- [x] CSV-Export enthält alle Pflichtfelder
- [x] ZIP-Paket enthält: index.xml + alle CSV + (optional) gindex.xml
- [x] Permission-Test: Nicht-Admin → 403
- [x] Audit-Log wird geschrieben

### 4.4 Akzeptanzkriterien
- Export für 1 Jahr (~1000 Rechnungen) <30s
- ZIP öffnet sich in IDEA (Datev-Prüfsoftware) ohne Fehler

**Quelle:** TODO_2026.md §1.6
**Branch:** `feat/gdpdu-export`

---

## Iteration 5: SettingsView Backend (4–6h)

**Ziel:** Backend-Grundlage für die SettingsView. Frontend in Iteration 6.

### 5.1 UserSettings Model
- [x] `invoice_app/models/user_settings.py`
  - `OneToOneField(User)`
  - Felder: `language` (de/en), `timezone`, `notify_on_invoice_paid`, `default_payment_terms_days`, `default_currency`
- [x] Migration erstellen
- [x] Auto-Erstellung via Signal `post_save` auf User

### 5.2 API-Endpoints
- [x] `GET/PUT/PATCH /api/user-settings/me/` — eigene Settings
- [x] `POST /api/auth/change-password/` — Password ändern
- [x] `GET /api/system/info/` — Version, Build-SHA, DB-Status
- [x] Serializer + ViewSets in `invoice_app/api/`

### 5.3 OpenAPI + Tests
- [x] `docs/openapi.json` aktualisieren — neue Endpoints + Schemas
- [x] Tests: `test_user_settings_api.py`
  - GET liefert eigene Settings
  - PUT speichert Changes
  - Andere User können fremde Settings NICHT lesen (RBAC)
  - Password-Change mit falschem alten Passwort → 400
  - System-Info ist authentifiziert

**Quelle:** TODO_2026.md §2.8
**Branch:** `feat/user-settings-backend`

---

## Iteration 6: SettingsView Frontend (4–6h)

**Ziel:** UI für UserSettings — komplette Ablösung des Placeholders.

### 6.1 Service & Store
- [x] `frontend/src/services/settingsService.js` — REST-Calls
- [x] Field-Mapping in `frontend/src/api/fieldMappings.js` (ACL!)
- [x] Pinia-Store oder Composable

### 6.2 Komponenten
- [x] `SettingsView.vue` — Tabs/Sections:
  - Profil (Sprache, Zeitzone, Notifications)
  - Rechnungs-Defaults (Zahlungsziel, Währung)
  - System-Info (Version, Build-SHA — read-only Karte)
  - Password ändern (Button → Modal)
- [x] `PasswordChangeModal.vue` — Alt + Neu + Bestätigung, Stärke-Indikator

### 6.3 Tests
- [x] Component-Test: SettingsView lädt + speichert
- [x] E2E: User ändert Sprache → wird persistiert + UI-Sprache wechselt

**Quelle:** TODO_2026.md §2.8
**Branch:** `feat/user-settings-frontend`
**Abhängigkeit:** Iteration 5

---

## Iteration 7: Offline/Network-Error-Handling (1–2h)

**Ziel:** User-Feedback bei Netzwerkfehlern statt Console-Errors.

- [x] Global axios interceptor in `client.js`:
  - `error.code === 'ERR_NETWORK'` oder `!navigator.onLine` → Toast "Keine Verbindung — bitte erneut versuchen"
  - Timeout (>30s) → eigene Meldung
- [x] `frontend/src/composables/useNetworkStatus.js` — reaktiver `online`-Status
- [x] Banner in `App.vue` bei `offline === true`

**Quelle:** TODO_2026.md §3.15
**Branch:** `feat/offline-error-handling`

---

## Iteration 8: E2E Tests Phase 3 (4–6h)

**Ziel:** Pass-Rate von 96% → 99%+.

- [x] Auth Error Message Test — Timing-Issue mit `waitForResponse` lösen
- [x] Modal Submission Test — Modal-Close-Selektor reparieren
- [x] DatePicker Tests (6 von 10 fehlerhaft) — Selektoren oder Mock evaluieren
  - Alternative: Custom DatePicker statt Third-Party

**Quelle:** TODO_2026.md §3.12
**Branch:** `test/e2e-stabilization`

---

## Iteration 9: XRechnung E-Mail-Versand (3.11 Stufe 2, 4–6h)

**Ziel:** B2G-Zustellung per E-Mail aus dem System.

- [x] E-Mail-Adresse pro `BusinessPartner` (für GOVERNMENT-Partner)
- [x] Template `xrechnung_email.html` (DE)
- [x] Action: "XRechnung versenden" auf InvoiceDetailView (nur bei GOVERNMENT-Partner)
- [x] Status auf Invoice: `xrechnung_sent_at`, `xrechnung_sent_to`
- [x] Tests: SMTP-Mock, Status-Update

**Quelle:** TODO_2026.md §3.11 Stufe 2
**Branch:** `feat/xrechnung-email`

---

## Iteration 10: Performance-Validierung (6–10h)

**Ziel:** NFR-Validierung gegen die in `req42` definierten Schwellen.

- [x] Load-Test-Tool wählen (k6)
- [x] Szenarien:
  - 100 concurrent User auf `/api/invoices/`
  - 1000 PDF-Generierungen / Stunde
- [ ] Messen: API-Response-Time p90, PDF-Gen p90, DB-Connections, Redis
- [ ] Bericht: `docs/PERFORMANCE_REPORT_v0.1.4.md`
- [ ] Falls Regressionen: Caching-Strategie (Redis) als Folge-Iteration

**Quelle:** TODO_2026.md §3.7
**Branch:** `perf/load-tests`

---

## Nicht eingeplant (bewusst aufgeschoben)

| TODO | Grund |
|------|-------|
| §3.1 Security Phase 3+4 (Vault, WAF, Tracing) | Hoher Aufwand (15–25h+), kein Produktivsystem |
| §3.2 ADRs finalisieren (10–15h) | Wenn Architekturentscheidungen anstehen |
| §3.3 K8s Verfeinerung (10–15h) | HA & Tuning erst bei realer Last |
| §3.5 Webhooks/Signaturen | Kein konkreter Bedarf |
| §3.10 XRechnung Erstellung | ✅ vollständig erledigt (Phase 1–4 alle abgehakt) |
| §3.11 Stufe 3+4 (ZRE-API, Peppol) | Erfordert reale B2G-Anbindung |

---

## Vorschlag für nächste Sprint-Planung

**Sprint A (Quick-Wins, ~6h):** Iterationen 1, 2, 3, 7
**Sprint B (GDPdU, ~6–10h):** Iteration 4 → Release v0.2.0 ("GoBD complete")
**Sprint C (Settings, ~8–12h):** Iterationen 5 + 6 → Release v0.3.0
**Sprint D (Polish, ~4–6h):** Iteration 8

Damit erreichen wir mit ~24–34h Aufwand zwei klar kommunizierbare Releases:
- **v0.2.0** = "GoBD vollständig"
- **v0.3.0** = "User Settings + Frontend Polish"
