# REST API Specification

Quick reference for eRechnung Django REST API endpoints.

> **Single Source of Truth:** [`docs/openapi.json`](openapi.json) ist die autoritative API-Vertragsdefinition.
> **Was nicht in openapi.json steht, existiert nicht in der öffentlichen API.**
>
> Nach Änderungen an Modellen/Serialisern/Views openapi.json regenerieren:
>
> ```bash
> cd scripts && ./regenerate_openapi.sh
> ```

## Documentation

- **Swagger UI**: `/api/docs/` (interactive, live)
- **OpenAPI 3.0.3 Schema**: [`docs/openapi.json`](openapi.json)

## Base Configuration

- **Base URL**: `/api/`
- **Authentication**: JWT Bearer Token
- **Content-Type**: `application/json` (Ausnahme: Datei-Upload → `multipart/form-data`)
- **API Version**: v1
- **Last Updated**: 2026-02-21 (auto-generated via drf-yasg)

---

## Authentication Endpoints

### POST `/api/auth/token/`

JWT Access- und Refresh-Token beziehen.

**Request Body:**

```json
{ "username": "string", "password": "string" }
```

**Response (200):**

```json
{
  "access": "string (JWT token)",
  "refresh": "string (JWT token)",
  "user": { "id": "integer", "username": "string", "email": "string", "role": "string" }
}
```

### POST `/api/auth/token/refresh/`

Access-Token mit Refresh-Token erneuern.

**Request Body:** `{ "refresh": "string" }`
**Response (200):** `{ "access": "string" }`

---

## Resource Endpoints — Übersicht

| Method | Path | Aktion |
|--------|------|--------|
| GET | `/api/{resource}/` | Liste (paginiert, filterbar) |
| POST | `/api/{resource}/` | Erstellen |
| GET | `/api/{resource}/{id}/` | Einzeln abrufen |
| PUT | `/api/{resource}/{id}/` | Vollständig ersetzen |
| PATCH | `/api/{resource}/{id}/` | Partiell aktualisieren |
| DELETE | `/api/{resource}/{id}/` | Löschen |

---

## 1. Companies (`/api/companies/`)

**Filter:** `name`, `country`, `tax_id`, `vat_id`, `is_active`
**Suche:** `name`, `tax_id`, `vat_id`, `email`
**Sortierung:** `name`, `created_at`

**Felder:**

```yaml
id:                    integer (read-only)
name:                  string (max 255, required)
legal_name:            string (optional)
tax_id:                string (unique, max 50, required)
vat_id:                string (optional, max 50)
commercial_register:   string (optional)
address_line1:         string (max 255, required)
address_line2:         string (optional)
postal_code:           string (max 20, required)
city:                  string (max 100, required)
state_province:        string (optional)
country:               string (max 100)
phone:                 string (optional)
fax:                   string (optional)
email:                 string (email, optional)
website:               string (URL, optional)
logo:                  file (ImageField, optional, multipart/form-data für Upload)
bank_name:             string (optional)
bank_account:          string (optional)
iban:                  string (max 34, optional)
bic:                   string (max 11, optional)
default_currency:      string (3 chars, default: EUR)
default_payment_terms: integer (days, default: 30)
is_active:             boolean (default: true)
created_at:            datetime (read-only)
updated_at:            datetime (read-only)
```

---

## 2. Business Partners (`/api/business-partners/`)

Kunden und/oder Lieferanten.

**Filter:** `country`, `tax_id`, `vat_id`, `partner_type`, `is_customer`, `is_supplier`, `is_active`
**Suche:** `company_name`, `first_name`, `last_name`, `tax_id`, `vat_id`, `email`
**Sortierung:** `business_partner_name`, `created_at`

**Felder:**

```yaml
id:                       integer (read-only)
is_customer:              boolean (default: true)
is_supplier:              boolean (default: false)
partner_type:             string (INDIVIDUAL|BUSINESS|GOVERNMENT|NON_PROFIT)
partner_number:           string (auto-generiert, read-only)
first_name:               string (max 100, optional)
last_name:                string (max 100, optional)
company_name:             string (max 255, optional)
legal_name:               string (max 255, optional)
tax_id:                   string (max 50, optional)
vat_id:                   string (max 50, optional)
commercial_register:      string (max 100, optional)
address_line1:            string (max 255, required)
address_line2:            string (optional)
postal_code:              string (max 20, required)
city:                     string (max 100, required)
state_province:           string (optional)
country:                  integer (FK Country.id) # ⚠️ Country-ID, nicht Name-String
phone:                    string (optional)
fax:                      string (optional)
email:                    string (email, optional)
website:                  string (URL, optional)
payment_terms:            integer (days, default: 30)
credit_limit:             decimal (15,2, optional)
preferred_currency:       string (3 chars, default: EUR)
default_reference_prefix: string (max 20, optional)
contact_person:           string (max 255, optional)
accounting_contact:       string (max 255, optional)
accounting_email:         string (email, optional)
is_active:                boolean (default: true)
created_at:               datetime (read-only)
updated_at:               datetime (read-only)
name:                     string (read-only, Alias für display_name)
display_name:             string (read-only)
role_display:             string (read-only)
```

> ⚠️ `country` ist eine FK-ID (Integer). TODO-007: `/api/countries/` Endpoint fehlt noch.

### POST `/api/business-partners/import/`

Massenimport aus strukturierten Daten.

```json
{
  "rows": [{ "company_name": "...", "address_line1": "...", "postal_code": "...", "city": "...", "country_code": "DE" }],
  "skip_duplicates": true,
  "update_existing": false
}
```

---

## 3. Products (`/api/products/`)

**Filter:** `product_type`, `category`, `subcategory`, `brand`, `tax_category`, `is_active`, `is_sellable`, `track_inventory`
**Suche:** `product_code`, `name`, `description`, `brand`, `manufacturer`
**Sortierung:** `product_code`, `name`, `base_price`, `created_at`

**Felder:**

```yaml
id:                   integer (read-only)
product_code:         string (max 100, unique, required)
name:                 string (max 255, required)
description:          text (optional)
product_type:         string (PHYSICAL|SERVICE|DIGITAL|SUBSCRIPTION)
category:             string (optional)
subcategory:          string (optional)
brand:                string (optional)
manufacturer:         string (optional)
base_price:           decimal (15,2, required)
currency:             string (3 chars, default: EUR)
cost_price:           decimal (15,2, optional)
list_price:           decimal (15,2, optional)
unit_of_measure:      string (PCE|HUR|DAY|KGM|LTR|MON)
weight:               decimal (kg, optional)
dimensions:           string (L×B×H cm, optional)
tax_category:         string (STANDARD|REDUCED|ZERO|EXEMPT|REVERSE_CHARGE)
default_tax_rate:     decimal (6,2, default: 19.00)
tax_code:             string (optional)
track_inventory:      boolean (default: false)
stock_quantity:       decimal (15,3, optional)
minimum_stock:        decimal (15,3, optional)
barcode:              string (optional)
sku:                  string (optional)
tags:                 string (kommagetrennt, optional)
is_active:            boolean (default: true)
is_sellable:          boolean (default: true)
discontinuation_date: date (optional)
created_at:           datetime (read-only)
updated_at:           datetime (read-only)
created_by:           integer (read-only)
current_price:        decimal (read-only, = base_price)
profit_margin:        decimal (read-only, %)
is_in_stock:          boolean (read-only)
needs_restock:        boolean (read-only)
```

### POST `/api/products/{id}/update_stock/`

```json
{ "quantity": "decimal", "operation": "set|add|subtract" }
```

### GET `/api/products/low_stock/`

Produkte unter Mindestbestand.

### GET `/api/products/tax-options/`

Gültige MwSt.-Sätze und Einheiten für die aktive Company.

### POST `/api/products/import/`

Massenimport von Produkten.

---

## 4. Invoices (`/api/invoices/`)

**Filter:** `status`, `invoice_type`, `company`, `business_partner`, `issue_date` (exact/gte/lte), `due_date`
**Suche:** `invoice_number`, `notes`
**Sortierung:** `invoice_number`, `status`, `issue_date`, `due_date`, `total_amount`

**Felder:**

```yaml
id:                       integer (read-only)
invoice_number:           string (read-only, auto: INV-YYYY-NNNN)
invoice_type:             string (INVOICE|CREDIT_NOTE|DEBIT_NOTE|CORRECTED|PARTIAL|FINAL)
invoice_type_display:     string (read-only)
company:                  integer (FK Company)
company_details:          object (read-only, nested)
business_partner:         integer (FK BusinessPartner)
business_partner_details: object (read-only, nested)
issue_date:               date
due_date:                 date
delivery_date:            date (optional)
currency:                 string (3 chars, default: EUR)
subtotal:                 decimal (read-only)
tax_amount:               decimal (read-only)
total_amount:             decimal (read-only)
payment_terms:            string (freier Zahlungstext)
payment_method:           string (optional)
payment_reference:        string (optional)
buyer_reference:          string (max 100, optional, Ihr Zeichen)
seller_reference:         string (max 100, optional, Unser Zeichen)
status:                   string (DRAFT|SENT|PAID|CANCELLED|OVERDUE)
status_display:           string (read-only)
pdf_file:                 string (read-only)
xml_file:                 string (read-only)
notes:                    text (optional)
created_by:               integer (read-only)
created_at:               datetime (read-only)
updated_at:               datetime (read-only)
lines:                    array (InvoiceLine, read-only, nested)
attachments:              array (InvoiceAttachment, read-only, nested)
allowance_charges:        array (InvoiceAllowanceCharge, read-only, nested)
is_paid:                  boolean (read-only)
is_overdue:               boolean (read-only)
```

> ⚠️ **Breaking Change 2026-02-21:** `customer`, `customer_details`, `customer_name`, `invoice_lines` entfernt.
> Verwende: `business_partner`, `business_partner_details`, `lines`.

### POST `/api/invoices/{id}/generate_pdf/`

**Query:** `profile` = `MINIMUM|BASICWL|BASIC|COMFORT|EXTENDED` (default: COMFORT)

**Response:** `{ "status": "...", "pdf_url": "...", "xml_valid": bool, "validation_errors": [] }`

### GET `/api/invoices/{id}/download_pdf/`

PDF herunterladen (auto-generiert wenn fehlend). Response: `application/pdf`

### GET `/api/invoices/{id}/download_xml/`

ZUGFeRD-XML herunterladen (auto-generiert wenn fehlend). Response: `application/xml`

### POST `/api/invoices/{id}/mark_as_paid/`

Rechnung als bezahlt markieren. Response: `{ "message": "Invoice marked as paid" }`

---

## 5. Invoice Lines (`/api/invoice-lines/`)

**Filter:** `invoice` | **Suche:** `description`, `product_code`

**Felder:**

```yaml
id:                  integer (read-only)
invoice:             integer (FK, required)
product:             integer (FK, optional)
product_name:        string (read-only)
description:         string (max 255)
product_code:        string (max 100, optional)
quantity:            decimal (15,3)
unit_price:          decimal (15,6)
effective_unit_price: decimal (read-only)
unit_of_measure:     string (max 20)
tax_rate:            decimal (6,2)
tax_amount:          decimal (read-only)
discount_percentage: decimal (5,2)
discount_amount:     decimal (15,2)
discount_reason:     string (max 255, EN16931 BR-41)
line_subtotal:       decimal (read-only)
line_total:          decimal (read-only)
```

---

## 6. Invoice Allowances/Charges (`/api/invoice-allowance-charges/`)

Header-Level Rabatte/Zuschläge nach EN16931 BG-20/BG-21.

**Filter:** `invoice`, `is_charge` | **Suche:** `reason`, `reason_code`

**Felder:**

```yaml
id:                  integer (read-only)
invoice:             integer (FK, required)
is_charge:           boolean (false=Rabatt, true=Zuschlag)
actual_amount:       decimal (15,2, min 0.01)
calculation_percent: decimal (7,4, optional)
basis_amount:        decimal (15,2, optional)
reason_code:         string (UNTDID 5189/7161, optional)
reason:              string (max 255, optional)
sort_order:          integer (default: 0)
```

---

## 7. Invoice Attachments (`/api/invoice-attachments/`)

**Filter:** `invoice` | **Suche:** `description` | **Upload:** `multipart/form-data`

**Felder:** `id`, `invoice`, `file`, `description`, `uploaded_at`

---

## 8. Audit Logs (`/api/audit-logs/`)

**Read-only.** Permission: `view_auditlog`.

**Filter:** `action`, `severity`, `object_type`, `is_compliance_relevant`, `is_security_event`, `username`

**Severity-Werte:** `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

**Action-Werte:** `CREATE`, `READ`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, `LOGIN_FAILED`, `ACCESS_DENIED`, `EXPORT`, `IMPORT`, `GENERATE_PDF`, `SEND_EMAIL`, `BACKUP`, `RESTORE`, `CONFIG_CHANGE`, `SECURITY_EVENT`

**Custom Actions:**
- `GET /api/audit-logs/security_events/` — letzte 100 Security-Events
- `GET /api/audit-logs/compliance_events/` — letzte 100 Compliance-Events
- `POST /api/audit-logs/cleanup_expired/` — abgelaufene Einträge löschen (`delete_auditlog` Permission)

---

## 9. Statistics (`/api/stats/`)

```json
{
  "invoices": { "total": 0, "by_status": {}, "total_amount": 0, "paid_amount": 0, "outstanding_amount": 0 },
  "business_partners": { "total": 0, "active": 0 },
  "products": { "total": 0, "active": 0 },
  "companies": { "total": 0, "active": 0 }
}
```

---

## Health Endpoints

| Endpoint | Auth | Zweck |
|----------|------|-------|
| `GET /health/` | Keine | Load-Balancer |
| `GET /health/detailed/` | JWT | Service-Status |
| `GET /health/readiness/` | Keine | K8s Readiness-Probe |

---

## Gemeinsame Features

**Pagination:** `?page=1&page_size=100` | **Filter:** `?status=PAID&issue_date__gte=2026-01-01` | **Suche:** `?search=text` | **Sortierung:** `?ordering=-issue_date`

**Errors:** Standard HTTP-Codes, JSON-Body mit `detail` oder Feld-Fehlern.

---

## Wichtige Hinweise

1. JWT-Auth für alle `/api/*` Endpoints (außer Auth-Endpoints)
2. `business_partner.country` ist FK-ID (Integer) — kein Name-String
3. Datei-Uploads: `multipart/form-data`
4. Rechnungssummen werden vom Backend berechnet — nie manuell setzen
5. `invoice_number` ist read-only — wird vom Backend generiert
6. openapi.json nach jeder API-Änderung regenerieren: `cd scripts && ./regenerate_openapi.sh`

---

## Nutzungsbeispiele (curl)

Alle Beispiele gegen `http://localhost:8000`. Token-Variable einmalig setzen:

```bash
export TOKEN="<access_token>"
```

---

### 1. Authentifizierung — Token beziehen

```bash
curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "geheim"}' | python3 -m json.tool
```

**Antwort (200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "ADMIN"
  }
}
```

Token speichern:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "geheim"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")
```

---

### 2. Token erneuern

```bash
curl -s -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

---

### 3. Rechnungen auflisten

```bash
# Alle Rechnungen (paginiert)
curl -s http://localhost:8000/api/invoices/ \
  -H "Authorization: Bearer $TOKEN"

# Gefiltert: nur bezahlte Rechnungen, neueste zuerst
curl -s "http://localhost:8000/api/invoices/?status=PAID&ordering=-issue_date&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# Volltextsuche
curl -s "http://localhost:8000/api/invoices/?search=Mustermann" \
  -H "Authorization: Bearer $TOKEN"
```

**Antwort (200):**
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/invoices/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "invoice_number": "INV-2026-0001",
      "invoice_type": "OUTGOING",
      "status": "DRAFT",
      "issue_date": "2026-03-14",
      "due_date": "2026-04-13",
      "currency": "EUR",
      "subtotal": "1000.00",
      "tax_amount": "190.00",
      "total_amount": "1190.00",
      "is_paid": false,
      "is_overdue": false
    }
  ]
}
```

---

### 4. Rechnung erstellen

```bash
curl -s -X POST http://localhost:8000/api/invoices/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_type": "OUTGOING",
    "company": 1,
    "business_partner": 3,
    "issue_date": "2026-03-14",
    "due_date": "2026-04-13",
    "currency": "EUR",
    "subtotal": "1000.00",
    "tax_amount": "190.00",
    "total_amount": "1190.00",
    "payment_terms": 30,
    "status": "DRAFT"
  }'
```

**Antwort (201):**
```json
{
  "id": 5,
  "invoice_number": "INV-2026-0005",
  "status": "DRAFT",
  "pdf_file": null,
  "xml_file": null,
  "created_at": "2026-03-14T10:00:00Z"
}
```

---

### 5. PDF generieren (ZUGFeRD/Factur-X)

```bash
curl -s -X POST http://localhost:8000/api/invoices/5/generate_pdf/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Antwort (200):**
```json
{
  "id": 5,
  "pdf_file": "/media/invoices/INV-2026-0005.pdf",
  "xml_file": "/media/invoices/INV-2026-0005.xml"
}
```

---

### 6. PDF herunterladen

```bash
curl -s http://localhost:8000/api/invoices/5/download_pdf/ \
  -H "Authorization: Bearer $TOKEN" \
  --output INV-2026-0005.pdf
```

Die Antwort ist eine Binary-Datei (`application/pdf`). Der generierte PDF enthält eingebettetes ZUGFeRD-XML (Factur-X EN 16931 Comfort).

---

### 7. XML herunterladen

```bash
curl -s http://localhost:8000/api/invoices/5/download_xml/ \
  -H "Authorization: Bearer $TOKEN" \
  --output INV-2026-0005.xml
```

---

### 8. Rechnung als bezahlt markieren

```bash
curl -s -X POST http://localhost:8000/api/invoices/5/mark_as_paid/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

---

### 9. Geschäftspartner anlegen

```bash
curl -s -X POST http://localhost:8000/api/business-partners/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_customer": true,
    "is_supplier": false,
    "partner_type": "BUSINESS",
    "company_name": "Musterfirma GmbH",
    "tax_id": "12345/67890",
    "vat_id": "DE123456789",
    "address_line1": "Musterstraße 1",
    "postal_code": "80331",
    "city": "München",
    "country": "DE",
    "email": "info@musterfirma.de",
    "payment_terms": 30
  }'
```

**Antwort (201):**
```json
{
  "id": 10,
  "partner_number": "BP-0010",
  "name": "Musterfirma GmbH",
  "role_display": "Kunde",
  "is_active": true,
  "created_at": "2026-03-14T10:00:00Z"
}
```

---

### 10. Fehler-Response (Beispiel)

Bei Validierungsfehlern antwortet die API einheitlich:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dieses Feld darf nicht leer sein.",
    "details": {
      "address_line1": ["Dieses Feld darf nicht leer sein."],
      "postal_code": ["Dieses Feld ist erforderlich."]
    }
  }
}
```

Weitere Fehlercodes: `NOT_FOUND` (404), `PERMISSION_DENIED` (403), `NOT_AUTHENTICATED` (401).
