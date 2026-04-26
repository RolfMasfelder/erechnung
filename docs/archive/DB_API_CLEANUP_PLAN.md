# Implementierungsplan: DB/API-Bereinigung (Branch: fix/dbapi)

**Erstellt:** 2026-02-21
**Branch:** `fix/dbapi`
**Status:** In Bearbeitung
**Ziel:** openapi.json als Single Source of Truth etablieren; Modelle, Serializer, Views, Dokumentation und Frontend konsistent ausrichten.

---

## Zusammenfassung der durchgeführten Änderungen

| # | Änderung | Status | Dateien |
|---|----------|--------|---------|
| 1 | Branch `fix/dbapi` erstellt | ✅ Fertig | — |
| 2 | Migrationen geprüft — alle aktuell, kein Handlungsbedarf | ✅ Fertig | — |
| 3 | `CompanySerializer`: Explizite Feldliste statt `__all__`, Feld `logo` dokumentiert | ✅ Fertig | `api/serializers.py` |
| 4 | `BusinessPartnerSerializer`: Explizite Feldliste, alle undokumentierten Felder ergänzt | ✅ Fertig | `api/serializers.py` |
| 5 | `ProductSerializer`: Explizite Feldliste, alle undokumentierten Felder ergänzt | ✅ Fertig | `api/serializers.py` |
| 6 | `InvoiceSerializer`: Backward-Compat-Felder **entfernt** (`customer`, `customer_details`, `customer_name`, `invoice_lines`), `invoice_number` als read-only markiert | ✅ Fertig | `api/serializers.py` |
| 7 | `docs/openapi.json` vollständig aus Code regeneriert (142 KB, 33 Endpoints) | ✅ Fertig | `docs/openapi.json` |
| 8 | `swagger_info.py` erstellt → zentrale openapi.Info-Definition | ✅ Fertig | `invoice_project/swagger_info.py` |
| 9 | `settings.py`: `DEFAULT_INFO` gesetzt → `manage.py generate_swagger` ohne Fehler | ✅ Fertig | `invoice_project/settings.py` |
| 10 | `urls.py`: `swagger_info.api_info` verwendet statt inline anonym | ✅ Fertig | `invoice_project/urls.py` |
| 11 | `scripts/regenerate_openapi.sh` erstellt | ✅ Fertig | `scripts/regenerate_openapi.sh` |
| 12 | `docs/API_SPECIFICATION.md` konsolidiert und aktualisiert | ✅ Fertig | `docs/API_SPECIFICATION.md` |
| 13 | `docs/api_documentation.md` gelöscht (veraltet, falsche URL-Basis) | ✅ Fertig | — |

---

## Offene TODOs / Korrekturbedarf

### KRITISCH — Bricht bestehende Funktionalität

#### TODO-001: Frontend — `customer`-Felder aus InvoiceSerializer entfernt

**Priorität:** KRITISCH
**Status:** ✅ ERLEDIGT (Commit aa713e6)

**Implementiert:**
- `InvoiceDetailView.vue`: `invoice.customer_name` → `invoice.business_partner_details?.name`; `invoice.invoice_lines` → `invoice.lines`
- `InvoiceListView.vue`: Bulk-Export und Zell-Rendering auf `business_partner_details` umgestellt
- `DashboardView.vue`: Zell-Rendering und Sort-Funktion auf `business_partner_details` priorisiert
- `InvoiceCreateModal.vue`: `formData.customer` → `formData.business_partner`; `formData.invoice_lines` → `formData.lines`; API-Aufruf angepasst
- `InvoiceEditModal.vue`: alle Referenzen umgestellt; `loadData` liest `invoice.lines` (mit Fallback auf `invoice.invoice_lines`)
- Tests: `InvoiceCreateModal.test.js`, `InvoiceEditModal.test.js`, `InvoiceDetailView.test.js` — Fixtures und Assertions aktualisiert; `createLine`/`createAllowanceCharge` Mocks ergänzt

---

#### TODO-002: Frontend — Dashboard Stats: `customers` → `business_partners`

**Priorität:** ERLEDIGT
**Status:** ✅ DashboardView.vue (Zeile 230) verwendet bereits `statsData.business_partners.active` → kein Handlungsbedarf.
Die alte API_SPECIFICATION.md war falsch dokumentiert. openapi.json und API_SPECIFICATION.md jetzt korrekt.
---

### WICHTIG — Modell/Schema-Inkonsistenzen

#### TODO-003: `Invoice.payment_terms` — Typ-Mismatch

**Priorität:** WICHTIG
**Status:** ✅ ERLEDIGT (Migration 0011)
**Entscheidung:** Option B — `PositiveIntegerField(default=30, null=True)` (Tage)
**Migration:** `0011_invoice_payment_terms_integer.py` mit Daten-Migration (Text → Int)

---

#### TODO-004: `BusinessPartner.country` — FK statt String

**Priorität:** WICHTIG
**Status:** ✅ ERLEDIGT
**Entscheidung:** ForeignKey beibehalten. `country`-Feld liefert Country-PK (`code`, ISO alpha-2, z. B. `"DE"`).

**Implementiert:**

- `/api/countries/` readonly endpoint registriert
- `/api/countries/{code}/` Detailansicht
- `/api/countries/{code}/tax-rates/` Steuersätze
- Frontend nutzt Country-Code aus diesem Endpoint für Dropdowns

**TODO:** Frontend-Formulare für Business Partner müssen Country-Dropdown aus `/api/countries/` befüllen.

**Status:** ✅ ERLEDIGT (Commit b93bd19)
- `countryService.js` erstellt (`/api/countries/` mit Fallback auf statische Liste)
- `businessPartnerService` in Index exportiert
- `BusinessPartnerCreateModal.vue` &amp; `BusinessPartnerEditModal.vue` laden Länder dynamisch beim Mount
- Tests aktualisiert (Mock für `countryService.getAll`)

---

#### TODO-005: `Product.product_type` — Choices-Abweichung von alter Spec

**Priorität:** WICHTIG
**Bereich:** Frontend, Daten
**Problem:** Alte API_SPECIFICATION nannte `GOODS/SERVICE`, Modell hat `PHYSICAL/SERVICE/DIGITAL/SUBSCRIPTION`.
**Ist-Zustand im Code:** `PHYSICAL/SERVICE/DIGITAL/SUBSCRIPTION` (korrekt)
**Aktion:** ✅ N/A — Kein Frontend-Dropdown für `product_type` vorhanden; wird erst bei Implementierung der Produktverwaltung relevant.

---

#### TODO-006: `AuditLog.severity` — Choices-Abweichung

**Priorität:** MITTEL
**Bereich:** Dokumentation, Frontend
**Problem:** Modell hat `LOW/MEDIUM/HIGH/CRITICAL`, alte Spec nannte `INFO/WARNING/ERROR/CRITICAL`.
**Ist-Zustand im Code:** `LOW/MEDIUM/HIGH/CRITICAL` (korrekt, openapi.json aktuell)
**Aktion:** ✅ N/A — Kein Audit-Log-Filter im Frontend vorhanden; wird relevant wenn AuditLog-Ansicht implementiert wird.

---

### ERGÄNZUNGEN — Fehlende Endpoints

#### TODO-007: `/api/countries/` Endpoint fehlt

**Priorität:** WICHTIG
**Status:** ✅ ERLEDIGT
**Implementiert:**

- `CountrySerializer` und `CountryTaxRateSerializer` in `api/serializers.py`
- `CountryViewSet(ReadOnlyModelViewSet)` in `api/rest_views.py`
- Registriert in `api/urls.py`: `router.register(r"countries", CountryViewSet, basename="api-country")`
- `lookup_field = "code"` (ISO alpha-2, z. B. `DE`, nicht Integer-PK)

---

#### TODO-008: `/api/countries/{id}/tax-rates/` oder `/api/tax-rates/?country=DE`

**Priorität:** MITTEL
**Status:** ✅ ERLEDIGT
**Implementiert:** `GET /api/countries/{code}/tax-rates/` als `@action(detail=True)` auf `CountryViewSet`.

Optionaler Query-Parameter `?on_date=YYYY-MM-DD` gibt nur die zum Datum gültigen Steuersätze zurück (via `CountryTaxRate.get_effective_rates()`).

---

### DOKUMENTATION

#### TODO-009: openapi.json nach jeder Schnittstellen-Änderung regenerieren

**Priorität:** PROZESS
**Bereich:** Entwicklungs-Workflow
**Aktion:** Als Regel im Entwicklungsprozess etablieren:
```bash
cd scripts && ./regenerate_openapi.sh
git add docs/openapi.json
```
Sinnvoll als pre-commit-hook oder CI/CD-Check.

---

#### TODO-010: InvoiceLine — `discount_reason` in openapi.json prüfen

**Priorität:** NIEDRIG
**Bereich:** Dokumentation
**Status:** Feld ist im Modell und Serializer vorhanden, prüfen ob in generiertem openapi.json korrekt erscheint. ✅ (Sollte durch Regenerierung behoben sein)

---

### BACKEND-SCHNITTSTELLE

#### TODO-011: `InvoiceAllowanceChargeViewSet` — Frontend-Integration prüfen

**Priorität:** MITTEL
**Status:** ✅ MODELL ERWEITERT (Frontend-Integration noch ausstehend)

**Implementiert (Backend):**

- `InvoiceAllowanceCharge.invoice_line` FK (nullable, Migration 0012) für Positionsebene
- `invoice_line is null` → Rechnungsebene (header-level, EN16931 ApplicableHeaderTradeSettlement)
- `invoice_line is set` → Positionsebene (line-level, EN16931 SpecifiedLineTradeSettlement)
- `InvoiceLine.recalculate()` berechnungs-Methode für line-level A/Cs
- `Invoice.recalculate_totals()` filtert jetzt `invoice_line__isnull=True` für header-level
- `InvoiceSerializer.allowance_charges` zeigt nur header-level A/Cs
- `InvoiceLineSerializer.allowance_charges` zeigt line-level A/Cs für jede Position

**API:**

- `POST /api/invoice-allowance-charges/` mit `invoice_line=null` → Rechnungsebene
- `POST /api/invoice-allowance-charges/` mit `invoice_line=123` → Positionsebene
- `is_line_level` Feld (read-only) im Serializer für einfache Unterscheidung

**Ausstehend:** Frontend-UI für Positionsebene-Rabatte/-Zuschläge implementieren.

---

#### TODO-012: Import-Endpoints — Frontend-Integration prüfen

**Priorität:** NIEDRIG
**Status:** ✅ ERLEDIGT
`importService.importCustomers()` genutzt in `BusinessPartnerListView.vue`; `importService.importProducts()` in `ProductListView.vue`. Endpoints sind in `openapi.json` dokumentiert.

---

#### TODO-013: `Invoice.invoice_number` als read-only im Serializer

**Priorität:** NIEDRIG
**Status:** ✅ ERLEDIGT
`InvoiceCreateModal.vue` behandelt `invoice_number` korrekt als optionales Feld (kein `required`, sendet `undefined` wenn leer, nicht in `isFormValid` geprüft).

---

### QUALITÄT / TECHNISCHE SCHULDEN

#### TODO-014: `BusinessPartnerSerializer.display_name` und `name` — Redundanz

**Priorität:** NIEDRIG
**Status:** ✅ ERLEDIGT
`display_name` aus `BusinessPartnerSerializer` entfernt. Nur noch `name` (read-only Property, identischer Wert) wird exponiert.

---

#### TODO-015: `CompanySerializer` — `logo`-Feld — Upload-Handling Frontend

**Priorität:** MITTEL
**Status:** ✅ ERLEDIGT
`CompanyEditModal.vue` verwendet `FormData` / multipart für Logo-Upload (wenn Datei gewählt oder gelöscht), JSON für reine Textfelder.

---

## Regenerierung von openapi.json

Nach **jeder** Änderung an Modellen, Serialisern oder Views:

```bash
cd scripts && ./regenerate_openapi.sh
# dann committen:
git add docs/openapi.json
git commit -m "docs: regenerate openapi.json"
```

Alternativ direkt:
```bash
docker compose exec web python project_root/manage.py generate_swagger docs/openapi.json -f json -o
```

---

## Entscheidungslog

| Datum | Entscheidung | Begründung |
|-------|-------------|------------|
| 2026-02-21 | openapi.json via drf_yasg automatisch generieren | Verhindert Drift zwischen Code und Dokumentation |
| 2026-02-21 | Backward-Compat-Felder des InvoiceSerializers entfernt | User: "Abwärtskompatibilität wird NICHT benötigt" |
| 2026-02-21 | `payment_terms` als TextField belassen | Keine Migration; Typ-Klärung als eigenes TODO |
| 2026-02-21 | `api_documentation.md` gelöscht | Komplett veraltet, falsche URL-Basis, falsche Ressourcennamen |
| 2026-02-21 | `API_SPECIFICATION.md` als primäre Referenz | Menschenlesbare Zusammenfassung von openapi.json |
| 2026-02-21 | `Invoice.payment_terms` → PositiveIntegerField(days) | Option B gewählt; Daten-Migration 0011 (Text→Int) |
| 2026-02-21 | `CountryViewSet` mit `lookup_field="code"` | ISO alpha-2 Code als URL-Parameter statt Integer-PK |
| 2026-02-21 | `InvoiceAllowanceCharge.invoice_line` FK (nullable) | Rabatte/Zuschläge auf Positions- UND Rechnungsebene (EN16931) |
| 2026-02-21 | `display_name` aus BusinessPartnerSerializer entfernt | Redundanz: `name` ist identisch |
