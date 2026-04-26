# BUGFIXES - Bereinigungsplan

**Erstellt:** 23. Januar 2026
**Status:** In Bearbeitung

---

## Übersicht der identifizierten Probleme

| # | Problem | Priorität | Aufwand | Status |
|---|---------|-----------|---------|--------|
| 0 | **Vue.js Frontend fehlt in Kubernetes** | 🔴 Kritisch | Mittel | ✅ Erledigt |
| 1 | Authentifizierung fehlt in der Anwendung | 🔴 Hoch | Mittel | ✅ Erledigt |
| 2 | "Companies" statt "Geschäftspartner" in der UI | 🟡 Mittel | Gering | ✅ Erledigt |
| 3 | Oberfläche auf Englisch statt Deutsch | 🟡 Mittel | Gering | ✅ Erledigt |
| 4 | Keine Daten sichtbar (Test-Daten fehlen) | 🔴 Hoch | Gering | ✅ Erledigt |
| 5 | **Testdaten fehlerhaft / UI zeigt falsche Daten** | 🔴 Hoch | Mittel | ✅ Erledigt |

---

## Bug 0: Vue.js Frontend fehlt in Kubernetes (KRITISCH)

### Problembeschreibung
Das Vue.js Frontend ist in der Kubernetes-Konfiguration **nicht deployed**. Aktuell wird nur das Django Backend mit der REST Framework Browsable API ausgeliefert. Das erklärt:
- Englische Oberfläche → DRF Browsable API (immer Englisch)
- `/login` gibt 404 → Vue-Route existiert nicht in Django
- `/companies/` zeigt API-Daten → DRF API-Endpoint
- Links zu `/admin/` → Django Admin (nicht Vue.js)

### Was Sie aktuell sehen
```
http://192.168.178.80/          → Django REST Framework Browsable API
http://192.168.178.80/invoices/ → DRF API (englisch)
http://192.168.178.80/admin/    → Django Admin Panel
```

### Was Sie sehen sollten
```
http://192.168.178.80/          → Vue.js Dashboard (deutsch)
http://192.168.178.80/login     → Vue.js Login-Seite
http://192.168.178.80/invoices  → Vue.js Rechnungsliste
http://192.168.178.80/api/...   → REST API (nur für Frontend-Calls)
```

### Ursache
In [k8s/kind/k8s-erechnung-local.yaml](k8s/kind/k8s-erechnung-local.yaml) fehlt:
1. **Frontend Deployment** (Vue.js Container)
2. **Frontend Service**
3. **Nginx-Konfiguration** die Frontend und API korrekt routet

Aktuelle Konfiguration:
```
Ingress → api-gateway (nginx) → django-web-service:8000
```

Benötigte Konfiguration:
```
Ingress → api-gateway (nginx)
           ├── /api/*  → django-web-service:8000
           ├── /admin/* → django-web-service:8000
           └── /*      → frontend-service:80 (Vue.js)
```

### Lösungsschritte

```
[✅] 0.1 Frontend Docker-Image für Production gebaut
    - docker build -t erechnung-frontend:local -f frontend/Dockerfile.prod frontend/
    - Image erfolgreich erstellt mit Vite Build + nginx alpine

[✅] 0.2 Kubernetes Manifeste erstellt
    Datei: k8s/kind/k8s-erechnung-local.yaml
    - Frontend Deployment hinzugefügt (2 Replicas, imagePullPolicy: Never)
    - Frontend Service erstellt (ClusterIP auf Port 80)

[✅] 0.3 Nginx ConfigMap angepasst
    - /api/* → Django Backend (django-web-service:8000)
    - /admin/* → Django Admin
    - /static/* → Django Static Files
    - /media/* → Django Media Files
    - /* → Frontend Service (frontend-service:80, Vue.js SPA)

[✅] 0.4 Frontend Image in Remote-kind-Cluster geladen
    - docker save | ssh rolf@192.168.178.80 "docker load && kind load..."
    - Image erfolgreich auf Remote-Server (192.168.178.80) geladen

[✅] 0.5 Kubernetes Deployment aktualisiert
    - kubectl apply -f k8s/kind/k8s-erechnung-local.yaml
    - Frontend Pods gestartet (2/2 Running)
    - API-Gateway mit kubectl rollout restart neu gestartet
    - Neue nginx-Config aktiv

[✅] 0.6 Verifikation
    - http://192.168.178.80/ zeigt Vue.js Frontend (deutsch)
    - SPA-Routing funktioniert
    - API-Calls über /api/* werden korrekt geroutet
```

### Workaround: Frontend lokal starten

Bis das Kubernetes-Deployment gefixt ist, können Sie das Frontend lokal starten:

**Option A: Mit Docker Compose (Port 5173)**
```bash
# Netzwerk muss existieren
docker network create erechnung_django_app_erechnung-network 2>/dev/null || true

# Frontend starten
docker-compose -f docker-compose.frontend.yml up frontend
```
→ Zugriff: http://localhost:5173

**Option B: Direkt mit npm (Port 5173)**
```bash
cd frontend
npm install
npm run dev
```
→ Zugriff: http://localhost:5173

**Hinweis:** Das Frontend muss auf die richtige API-URL zeigen:
- Für lokales Backend: `VITE_API_BASE_URL=http://localhost:8000/api`
- Für K8s Backend: `VITE_API_BASE_URL=http://192.168.178.80/api`

### Betroffene Dateien
- `k8s/kind/k8s-erechnung-local.yaml` (Deployment + Service hinzufügen)
- `k8s/kind/ingress.yaml` (Routing anpassen)
- `frontend/Dockerfile.prod` (bereits vorhanden)

---

## Bug 1: Authentifizierung fehlt in der Anwendung

### Problembeschreibung
Die Anwendung zeigt die Home-Page ohne vorherige Anmeldung an. Obwohl JWT-Authentifizierung implementiert ist, funktioniert der Auth-Guard nicht korrekt.

### Ursachenanalyse

**Ist-Zustand:**
- [frontend/src/router/index.js](frontend/src/router/index.js): Navigation Guard prüft `authService.isAuthenticated()`
- [frontend/src/api/services/authService.js](frontend/src/api/services/authService.js): Prüft nur `localStorage.getItem('jwt_token')`
- [project_root/invoice_app/api/rest_views.py](project_root/invoice_app/api/rest_views.py): API-Views haben `permission_classes = [IsAuthenticated]`
- Login-View existiert unter [frontend/src/views/LoginView.vue](frontend/src/views/LoginView.vue)

**Mögliche Ursachen:**
1. **Router Guard funktioniert nicht** - Die `isAuthenticated()` Prüfung könnte fehlschlagen
2. **Falsche Route-Konfiguration** - Dashboard wird ohne Auth-Check geladen
3. **Token bleibt nach Logout bestehen** - LocalStorage wird nicht korrekt gelöscht

### Lösungsschritte

```
[✅] 1.1 Debugging: Router-Guard in Browser-Console prüfen
    - Öffne Browser DevTools → Console
    - Navigiere zur App und prüfe ob Guard-Logik aufgerufen wird
    - Prüfe localStorage auf vorhandene Tokens

[✅] 1.2 Router-Guard verstärken
    Datei: frontend/src/router/index.js
    - Token-Validierung hinzugefügt (nicht nur Existenz prüfen)
    - JWT-Ablaufzeit wird geprüft
    - Debug-Logging für Entwicklung hinzugefügt

[✅] 1.3 AuthService erweitern
    Datei: frontend/src/api/services/authService.js
    - isAuthenticated() prüft jetzt Token-Ablauf (exp-Claim)
    - Abgelaufene Tokens werden automatisch gelöscht
    - Logout wird automatisch bei abgelaufenen Tokens ausgeführt

[✅] 1.4 Test-User verifizieren
    - In Kubernetes: django-init Job erstellt admin/admin User
    - create_test_data Command erstellt testuser/testpass123
```

### Betroffene Dateien
- `frontend/src/router/index.js`
- `frontend/src/api/services/authService.js`
- `frontend/src/composables/useAuth.js`

---

## Bug 2: "Companies" statt "Geschäftspartner" in der UI

### Problembeschreibung
Das Datenmodell wurde von "Companies" auf "BusinessPartner" umgestellt, aber die Oberfläche zeigt weiterhin "Companies" an.

### Ursachenanalyse

**Ist-Zustand:**
- [frontend/src/components/AppSidebar.vue](frontend/src/components/AppSidebar.vue#L54-L63): Zeigt "Firmen" unter Verwaltung
- [frontend/src/views/CompanyListView.vue](frontend/src/views/CompanyListView.vue): Verwendet `/companies/` API-Endpoint
- [frontend/src/api/services/companyService.js](frontend/src/api/services/companyService.js): Nutzt `/companies/` Endpoint
- Backend hat separaten `BusinessPartnerViewSet` mit `/business-partners/` Endpoint

**Konzeptuelles Problem:**
Es gibt im Backend ZWEI verschiedene Entitäten:
1. **Company** - Die eigene Firma des Users (Rechnungsaussteller)
2. **BusinessPartner** - Kunden/Lieferanten (Rechnungsempfänger)

Die Frontend-Sidebar hat "Kunden" unter Rechnungswesen, nutzt aber CustomerListView (nicht BusinessPartnerListView).

### Lösungsschritte

```
[✅] 2.1 Klärung: Was soll "Companies" werden?
    → Backend hat /companies/ (eigene Firmen) UND /business-partners/ (Kunden/Lieferanten)
    → Frontend nutzte fälschlicherweise /customers/ (existiert nicht!)

[✅] 2.2 Sidebar-Terminologie anpassen
    - Sidebar zeigt korrekt "Kunden" (Deutsch)
    - Route /customers zeigt CustomerListView an

[✅] 2.3 API-Service korrigiert
    Datei: frontend/src/api/services/customerService.js
    - Alle Endpoints von /customers/ zu /business-partners/ geändert
    - Kommentar hinzugefügt dass Backend /business-partners/ nutzt

[✅] 2.4 Views verwenden korrekten Endpoint
    - CustomerListView.vue nutzt jetzt korrekten /business-partners/ Endpoint
    - CompanyListView.vue nutzt /companies/ für eigene Firmen (Admin-Bereich)
```

### Empfehlung
**Option B** scheint korrekt zu sein:
- "Firmen" (Companies) = Admin-Bereich für eigene Firmendaten
- "Kunden" = BusinessPartner (Rechnungsempfänger)

Die Labels sind bereits auf Deutsch ("Firmen", "Kunden"), aber die Route-Namen und API-Endpoints sind auf Englisch, was korrekt ist.

→ **Prüfen ob "Kunden"-View die richtige API nutzt (`/business-partners/` oder `/customers/`)**

### Betroffene Dateien
- `frontend/src/components/AppSidebar.vue`
- `frontend/src/views/CompanyListView.vue`
- `frontend/src/views/CustomerListView.vue`
- `frontend/src/api/services/companyService.js`
- `frontend/src/api/services/customerService.js`
- `frontend/src/router/index.js`

---

## Bug 3: Oberfläche auf Englisch statt Deutsch

### Problembeschreibung
Die Anwendung zeigt englische Texte an, obwohl sie auf Deutsch sein sollte.

### Ursachenanalyse

**Ist-Zustand:**
Nach Analyse der Codebase sind die **meisten UI-Texte bereits auf Deutsch**:
- [frontend/src/views/LoginView.vue](frontend/src/views/LoginView.vue): "Bitte melden Sie sich an", "Anmelden"
- [frontend/src/components/AppSidebar.vue](frontend/src/components/AppSidebar.vue): "Dashboard", "Rechnungen", "Kunden", "Produkte", "Firmen", "Einstellungen"
- [frontend/src/views/CompanyListView.vue](frontend/src/views/CompanyListView.vue#L5-L6): "Firmen", "Verwaltung aller Firmen im System"

**Was noch englisch sein könnte:**
1. Browser-Titel (document.title)
2. Error-Messages von API
3. Validierungsmeldungen
4. Datum-/Zahlenformate (bereits auf `de-DE` gesetzt)

### Lösungsschritte

```
[✅] 3.1 Englische Texte identifizieren
    - HomeView.vue hatte "Welcome" statt "Willkommen"

[✅] 3.2 Identifizierte Texte übersetzen
    - "Welcome" → "Willkommen"
    - "Vue 3 + Vite... Setup erfolgreich" → "eRechnung System - Entwicklungsmodus aktiv"
    - "Node:" → "Umgebung:"

[✅] 3.3 HomeView.vue geprüft
    Datei: frontend/src/views/HomeView.vue
    - Alle Texte auf Deutsch geändert
    - Wird als Fallback-Route genutzt

[ ] 3.4 Optional: i18n-System für Mehrsprachigkeit vorbereiten
    - NICHT jetzt implementieren
    - Nur als TODO dokumentieren für später
```

### Konkret zu ändernde Texte (bekannt)

| Datei | Aktuell | Neu |
|-------|---------|-----|
| `HomeView.vue` | "Welcome" | "Willkommen" |
| `HomeView.vue` | "Vue 3 + Vite + Tailwind CSS + Pinia Setup erfolgreich!" | (ggf. entfernen, da Dev-Placeholder) |

### Betroffene Dateien
- `frontend/src/views/HomeView.vue` (bekannt)
- Weitere nach Analyse

---

## Bug 4: Keine Daten sichtbar

### Problembeschreibung
Die Anwendung zeigt keine Daten an. Es ist unklar, ob:
- Test-Daten fehlen in der Datenbank
- Der User nicht authentifiziert ist und daher keine Daten abrufen kann
- Die API-Anfragen fehlschlagen

### Ursachenanalyse

**Kubernetes Setup prüfen:**
1. [k8s/kind/k8s-erechnung-local.yaml#L219-L239](k8s/kind/k8s-erechnung-local.yaml#L219-L239): `django-init` Job erstellt nur:
   - Superuser: `admin` / `admin`
   - Test-User: `testuser` / `testpass123`
   - **KEINE Testdaten** (keine Fixtures geladen!)

2. API erfordert `IsAuthenticated` Permission auf allen ViewSets

**Wahrscheinlichste Ursache:**
→ User ist nicht eingeloggt → API gibt 401 Unauthorized → Frontend zeigt leere Listen

### Lösungsschritte

```
[✅] 4.1 Browser DevTools öffnen → Network Tab
    - Nicht notwendig - direkter Fix implementiert

[✅] 4.2 Kubernetes: django-init Job erweitert
    Datei: k8s/kind/k8s-erechnung-local.yaml
    - Verwendet jetzt existierenden Management Command: create_test_data
    - Erstellt admin User: admin/admin
    - Command erstellt testuser/testpass123 und umfassende Testdaten

[✅] 4.3 create_test_data Command wird aufgerufen
    - Erstellt Countries (Deutschland mit MwSt-Sätzen)
    - Erstellt Company (Musterfirma GmbH)
    - Erstellt BusinessPartners (Kunden)
    - Erstellt Products (Beratung, Lizenzen, Support)
    - Erstellt Invoices mit InvoiceItems (Draft, Sent, Overdue)

[ ] 4.4 Optional: Fixtures erstellen für Production
    - Aktuell werden Testdaten bei jedem Deployment erstellt
    - Für Production: Fixtures nur einmalig laden
```

### Fixtures erstellen (empfohlen)

```bash
# Im Container:
python project_root/manage.py dumpdata invoice_app.businesspartner --indent 2 > fixtures/test_businesspartners.json
python project_root/manage.py dumpdata invoice_app.product --indent 2 > fixtures/test_products.json
python project_root/manage.py dumpdata invoice_app.invoice --indent 2 > fixtures/test_invoices.json
```

**Oder in django-init Job hinzufügen:**
```yaml
python project_root/manage.py shell << 'EOF'
from invoice_app.models import BusinessPartner, Product, Country

# Beispiel-Kunde erstellen
de = Country.objects.get_or_create(code='DE', defaults={'name': 'Deutschland', 'vat_rate': 19.0})[0]
BusinessPartner.objects.get_or_create(
    company_name='Musterfirma GmbH',
    defaults={
        'partner_type': 'company',
        'is_customer': True,
        'address_line1': 'Musterstraße 1',
        'postal_code': '12345',
        'city': 'Berlin',
        'country': de
    }
)
print("✓ Testdaten erstellt")
EOF
```

### Betroffene Dateien
- `k8s/kind/k8s-erechnung-local.yaml`
- `project_root/invoice_app/fixtures/` (neue Dateien)

---

## Priorisierte Reihenfolge

### Phase 1: Kritische Funktionalität (sofort)
1. **Bug 1** - Authentifizierung prüfen und reparieren
2. **Bug 4** - Testdaten erstellen (hängt von Bug 1 ab)

### Phase 2: UI-Korrekturen (danach)
3. **Bug 2** - Companies/Geschäftspartner Terminologie klären
4. **Bug 3** - Verbleibende englische Texte übersetzen

---

## Bug 5: Testdaten fehlerhaft / UI zeigt falsche Daten

### Problembeschreibung
Nach erfolgreichem Login und Ausführung von `create_test_data` werden Daten angezeigt, aber mit mehreren Fehlern:

1. **Dashboard zeigt überall "0"**
   - "Keine Rechnungen" obwohl 20 Rechnungen existieren
   - "Keine Kunden" obwohl 10 Kunden existieren
   - Statistiken zeigen keine Daten

2. **Rechnungsliste: Kein Kundenbezug**
   - Rechnungen werden angezeigt
   - Aber ohne zugeordneten Kunden
   - Feld für Kundenname ist leer

3. **Kundenliste: Falsche/Fehlende Daten**
   - Kunden haben keinen Namen (Feld leer)
   - "Adresse" zeigt z.B. ", Dresden" (Komma am Anfang)
   - "Stadt" zeigt korrekt "Dresden"
   - Feldmapping scheint durcheinander zu sein

### Ursachenanalyse

**Mögliche Ursachen:**

1. **Backend: Testdaten-Generierung fehlerhaft**
   - `create_test_data.py` erstellt BusinessPartner ohne `name`-Feld?
   - Nur `company_name` gesetzt, aber Frontend erwartet `name`?
   - Adressfelder falsch befüllt

2. **Backend: Serializer-Mapping fehlerhaft**
   - BusinessPartnerSerializer mappt Felder falsch
   - `name` wird nicht aus `company_name` oder Kombination von `first_name`/`last_name` generiert
   - Invoice Serializer included keinen BusinessPartner

3. **Frontend: Falsche Feld-Referenzen**
   - CustomerListView erwartet `row.name`, aber Backend sendet `company_name`
   - Dashboard-API-Calls gehen an falsche Endpoints
   - InvoiceListView zeigt `customer` nicht korrekt an

### Lösungsschritte

```
[✅] 5.1 Backend: BusinessPartner-Daten geprüft
    - BusinessPartner hat @property "name" die company_name ODER first_name + last_name zurückgibt
    - Feld war nicht im Serializer exponiert

[✅] 5.2 Backend: Serializer erweitert
    - BusinessPartnerSerializer: name, display_name, role_display als ReadOnlyField hinzugefügt
    - InvoiceSerializer: customer_name und invoice_lines Felder hinzugefügt

[✅] 5.3 Backend: Dashboard Stats korrigiert
    - DashboardStatsView: Status-Filter von lowercase auf UPPERCASE geändert (DB speichert DRAFT, nicht draft)
    - Statistiken werden nun korrekt gezählt

[✅] 5.4 Frontend: Feldnamen korrigiert
    - Dashboard: statsData.customers → statsData.business_partners
    - CustomerListView: row.street → row.address_line1
    - CustomerDetailView: address_line1 und address_line2 korrekt angezeigt

[✅] 5.5 Frontend: Datumsformatierung standardisiert
    - Alle Views nutzen formatDate mit expliziten Optionen {day: '2-digit', month: '2-digit', year: 'numeric'}
    - Deutsches Format: DD.MM.YYYY (z.B. 23.01.2026)

[✅] 5.6 Frontend: Kundennamen in Rechnungen
    - InvoiceListView und DashboardView zeigen customer_name korrekt an
    - Clickable router-links für Navigation zu Kundendetails

[✅] 5.7 Frontend: Rechnungsdetails korrigiert
    - Status wird lowercase konvertiert für Label-Lookup (DRAFT → draft)
    - Kundenname wird korrekt angezeigt (customer_name aus Serializer)
    - Positionen-Tabelle zeigt invoice_lines korrekt an
    - Spalten angepasst: unit_price, tax_rate, line_total (statt _net/_gross Suffixe)

[✅] 5.8 Frontend: Positionen-Berechnung korrigiert
    - Menge formatiert ohne Tausendertrennzeichen (3 statt 3.000)
    - Brutto-Betrag wird berechnet: line_total (Netto) + tax_amount (MwSt)
    - Zusammenfassung nutzt korrekte API-Felder: subtotal, tax_amount, total_amount

[✅] 5.9 Frontend: Datumsformat in Kundendetails
    - Template-Slot für due_date mit deutscher Formatierung hinzugefügt
```

**Hinweis zum Preismodell:**
Das Backend speichert in `line_total` den **Netto-Betrag** (nach Rabatt, vor Steuer). Die MwSt wird separat in `tax_amount` gespeichert. Das Frontend berechnet für die Anzeige: Brutto = line_total + tax_amount.

### Betroffene Dateien
- Backend: `project_root/invoice_app/management/commands/create_test_data.py`
- Backend: `project_root/invoice_app/api/serializers.py`
- Backend: `project_root/invoice_app/models/business_partner.py`
- Frontend: `frontend/src/views/DashboardView.vue`
- Frontend: `frontend/src/views/CustomerListView.vue`
- Frontend: `frontend/src/views/InvoiceListView.vue`

---

## Nächste Schritte

1. **Im Browser prüfen:**
   - URL aufrufen
   - DevTools öffnen (F12)
   - Zur Login-Seite navigiert? → Wenn nein, Bug 1 bestätigt
   - Network-Tab: API-Calls mit 401? → Wenn ja, nicht authentifiziert

2. **Login testen:**
   - `/login` aufrufen
   - Credentials: `admin` / `admin` eingeben
   - Funktioniert Login? → Wenn ja, Bug 1 ist anderes Problem

3. **Nach Login:**
   - Dashboard prüfen
   - Daten sichtbar? → Wenn nein, Testdaten fehlen (Bug 4)

---

## Changelog

| Datum | Änderung |
|-------|----------|
| 2026-01-23 | Initialer Bugfix-Plan erstellt |
| 2026-01-23 | **Bugs 1-4 implementiert und getestet** |
| 2026-01-23 | Bug 1: JWT Token-Ablauf-Validierung in authService und Router-Guard |
| 2026-01-23 | Bug 2: customerService korrigiert auf /business-partners/ Endpoint |
| 2026-01-23 | Bug 3: HomeView.vue auf Deutsch übersetzt |
| 2026-01-23 | Bug 4: django-init Job nutzt create_test_data Command |
| 2026-01-23 | **Bug 5: Vollständig behoben** - Dashboard-Stats, Serializer-Felder, Datumsformatierung, Positionen-Anzeige |
| 2026-01-23 | Bug 5.1-5.3: Backend Serializer erweitert (name, customer_name, invoice_lines, status-Filter) |
| 2026-01-23 | Bug 5.4-5.6: Frontend Feldnamen korrigiert, Datumsformat standardisiert, Navigation hinzugefügt |
| 2026-01-23 | Bug 5.7-5.9: Rechnungsdetails komplett überarbeitet (Status, Positionen, Berechnungen, Formatierung) |
| 2026-01-23 | **Bug 0: Erfolgreich abgeschlossen** - Vue.js Frontend läuft in Kubernetes auf http://192.168.178.80 |
| 2026-01-23 | Bug 0: Frontend-Image gebaut, via SSH in Remote-kind-Cluster geladen, Deployment aktualisiert |
| 2026-01-23 | **Alle 6 Bugs (0-5) erfolgreich behoben!** |
