# 5. Funktionale Anforderungen

## 5.1 Use Cases

### UC-01: Rechnung erstellen

**Akteur**: Client-Anwendung / Benutzer
**Vorbedingung**: Authentifizierung erfolgreich
**Nachbedingung**: Rechnung ist im System gespeichert

**Hauptszenario**:

1. Client sendet Rechnungsdaten via API
2. System validiert Eingabedaten
3. System erstellt Rechnungsobjekt
4. System speichert Rechnung in Datenbank
5. System gibt Rechnungs-ID zurück

**Alternativszenarien**:

- 2a: Validierung fehlgeschlagen → Fehlermeldung mit Details
- 4a: Datenbankfehler → Rollback und Fehlermeldung

### UC-02: ZUGFeRD-PDF generieren

**Akteur**: Client-Anwendung / Benutzer
**Vorbedingung**: Rechnung existiert im System
**Nachbedingung**: PDF-Datei wurde erstellt

**Hauptszenario**:

1. Client fordert PDF für Rechnungs-ID an
2. System lädt Rechnungsdaten
3. System generiert ZUGFeRD-XML
4. System erstellt PDF/A-3 Dokument
5. System bettet XML in PDF ein
6. System liefert PDF-Datei aus

### UC-03: Rechnung abrufen

**Akteur**: Client-Anwendung / Benutzer
**Vorbedingung**: Authentifizierung erfolgreich
**Nachbedingung**: Rechnungsdaten wurden übermittelt

**Hauptszenario**:

1. Client fordert Rechnung per ID oder Filter an
2. System prüft Zugriffsberechtigung
3. System lädt Rechnungsdaten
4. System gibt JSON-Repräsentation zurück

### UC-04: Rechnung aktualisieren

**Akteur**: Client-Anwendung / Benutzer
**Vorbedingung**: Rechnung existiert, Status erlaubt Änderung
**Nachbedingung**: Rechnung wurde aktualisiert

**Hauptszenario**:

1. Client sendet Änderungen für Rechnungs-ID
2. System validiert Änderungen
3. System prüft Geschäftsregeln (z.B. Status)
4. System aktualisiert Rechnung
5. System gibt aktualisierte Daten zurück

### UC-05: Rechnung validieren

**Akteur**: Client-Anwendung / Benutzer
**Vorbedingung**: Rechnungsdaten liegen vor
**Nachbedingung**: Validierungsergebnis liegt vor

**Hauptszenario**:

1. Client sendet Rechnungsdaten zur Validierung
2. System prüft gegen ZUGFeRD-Schema
3. System prüft Geschäftsregeln
4. System gibt Validierungsergebnis zurück

## 5.2 Funktionale Anforderungen (Katalog)

### FR-01: Rechnungsverwaltung

- **FR-01.01**: System MUSS Rechnungen erstellen können
- **FR-01.02**: System MUSS Rechnungen abrufen können (einzeln und Liste)
- **FR-01.03**: System MUSS Rechnungen aktualisieren können
- **FR-01.04**: System MUSS Rechnungen löschen können (soft delete)
- **FR-01.05**: System MUSS Rechnungen filtern können (Datum, Status, Kunde)
- **FR-01.06**: System MUSS eine fortlaufende, einmalige Rechnungsnummer vergeben (§ 14 Abs. 4 Nr. 4 UStG)
  - Format: `INV-{JJJJ}-{NNNN}` (z.B. `INV-2026-0042`)
  - **Intern**: `sequence_number` (PositiveIntegerField, global fortlaufend, wird beim Jahreswechsel NICHT zurückgesetzt)
  - **Extern**: `invoice_number` (CharField) = Display-String aus `issue_date.year` + `sequence_number`
  - Beide Felder werden bewusst parallel geführt, da Eingangsrechnungen beliebige externe Nummern tragen
  - `sequence_number` ist NULL bei Eingangsrechnungen (externe Lieferantennummern)
  - Vergabe erfolgt atomar über PostgreSQL SEQUENCE (`nextval`), keine Race Conditions
  - Startwert bei Inbetriebnahme einstellbar: `manage.py set_sequence_start <N>` → nächste = N+1
  - Rechnungsnummer ist nach Vergabe unveränderlich (GoBD-konform)

### FR-02: ZUGFeRD-Konformität

- **FR-02.01**: System MUSS ZUGFeRD 2.x unterstützen
- **FR-02.02**: System MUSS Profile BASIC, COMFORT, EXTENDED unterstützen
- **FR-02.03**: System MUSS XRechnung-Format unterstützen
- **FR-02.04**: System MUSS EN 16931 konforme Daten erzeugen
- **FR-02.05**: System MUSS XML gegen XSD-Schema validieren

### FR-03: PDF-Generierung

- **FR-03.01**: System MUSS PDF/A-3 konforme Dokumente erzeugen
- **FR-03.02**: System MUSS XML als Anhang einbetten
- **FR-03.03**: System MUSS konfigurierbare Layouts unterstützen
- **FR-03.04**: System MUSS Logo-Integration ermöglichen
- **FR-03.05**: System MUSS mehrsprachige Rechnungen unterstützen

### FR-04: API-Funktionalität

- **FR-04.01**: System MUSS RESTful API bereitstellen
- **FR-04.02**: System MUSS JSON als Datenformat verwenden
- **FR-04.03**: System MUSS OpenAPI-Dokumentation bereitstellen
- **FR-04.04**: System MUSS API-Versionierung unterstützen
- **FR-04.05**: System MUSS Pagination für Listen implementieren

### FR-05: Authentifizierung & Autorisierung

- **FR-05.01**: System MUSS JWT-basierte Authentifizierung bieten
- **FR-05.02**: System MUSS Benutzer-Registrierung ermöglichen
- **FR-05.03**: System MUSS Rollen-basierte Zugriffskontrolle implementieren
- **FR-05.04**: System MUSS Token-Refresh unterstützen
- **FR-05.05**: System MUSS Passwort-Reset-Funktion bieten

### FR-06: Datenvalidierung

- **FR-06.01**: System MUSS Eingabedaten gegen Schema validieren
- **FR-06.02**: System MUSS Pflichtfelder prüfen
- **FR-06.03**: System MUSS Datentypen validieren
- **FR-06.04**: System MUSS Geschäftsregeln durchsetzen
- **FR-06.05**: System MUSS aussagekräftige Fehlermeldungen liefern

## 5.3 User Stories

### Epic: Rechnungserstellung

- **US-01**: Als Benutzer möchte ich eine Rechnung mit Kundendaten und Positionen erstellen können
- **US-02**: Als Benutzer möchte ich eine Vorlage für wiederkehrende Rechnungen verwenden können
- **US-03**: Als Benutzer möchte ich Rechnungspositionen mit Artikelnummern verknüpfen können

### Epic: PDF-Export

- **US-04**: Als Benutzer möchte ich eine ZUGFeRD-konforme PDF-Rechnung herunterladen können
- **US-05**: Als Benutzer möchte ich das Layout meiner Rechnung anpassen können
- **US-06**: Als Benutzer möchte ich mein Firmenlogo in die Rechnung einfügen können

### Epic: Validierung

- **US-07**: Als Benutzer möchte ich vor dem Versand prüfen können, ob meine Rechnung konform ist
- **US-08**: Als Benutzer möchte ich detaillierte Validierungsfehler angezeigt bekommen
- **US-09**: Als Benutzer möchte ich verschiedene ZUGFeRD-Profile testen können

### Epic: Integration

- **US-10**: Als Entwickler möchte ich die API in mein ERP-System integrieren können
- **US-11**: Als Entwickler möchte ich Batch-Import von Rechnungen durchführen können
- **US-12**: Als Entwickler möchte ich Webhooks für Rechnungs-Events nutzen können

### FR-07: Frontend-Funktionalität (Vue.js SPA) ✨ NEU

- **FR-07.01**: System MUSS moderne Single Page Application bereitstellen
- **FR-07.02**: System MUSS responsive Design für Mobile/Tablet/Desktop bieten
- **FR-07.03**: System MUSS Echtzeit-Dashboard mit Statistiken anzeigen
- **FR-07.04**: System MUSS Confirmation Dialogs für kritische Aktionen zeigen
- **FR-07.05**: System MUSS Loading States und Error Handling implementieren
- **FR-07.06**: System MUSS Toast Notifications für User Feedback bereitstellen
- **FR-07.07**: System MUSS Offline-Erkennung und Netzwerkfehler-Behandlung bieten

### FR-08: Advanced Features ✨ NEU

- **FR-08.01**: System MUSS Advanced Filtering mit URL-Persistenz unterstützen
- **FR-08.02**: System MUSS Bulk Operations (Multi-Select, Bulk Delete) ermöglichen
- **FR-08.03**: System MUSS CSV Export mit deutscher Formatierung bieten
- **FR-08.04**: System MUSS CSV/JSON Import mit Validierung unterstützen
- **FR-08.05**: System MUSS Table Sorting für alle Listen-Ansichten ermöglichen
- **FR-08.06**: System MUSS DatePicker für Datumsauswahl integrieren

### FR-09: Background Processing ✨ NEU

- **FR-09.01**: System MUSS asynchrone Task-Verarbeitung mit Celery unterstützen
- **FR-09.02**: System MUSS Redis als Message Broker und Cache verwenden
- **FR-09.03**: System MUSS Background-Jobs für zeitintensive Operationen nutzen
- **FR-09.04**: System MUSS Task-Status-Tracking ermöglichen

### FR-10: API Gateway und Rate Limiting ✨ NEU

- **FR-10.01**: System MUSS nginx API Gateway als Reverse Proxy bereitstellen
- **FR-10.02**: System MUSS Rate Limiting pro IP-Adresse implementieren
- **FR-10.03**: System MUSS Security Headers (HSTS, CSP, X-Frame-Options) setzen
- **FR-10.04**: System MUSS API-Versionierung über Gateway unterstützen
- **FR-10.05**: System MUSS CORS-Konfiguration zentral verwalten

### FR-11: Health Monitoring ✨ NEU

- **FR-11.01**: System MUSS drei-stufige Health Endpoints bereitstellen
  - `/health/` - Simple Health Check
  - `/health/detailed/` - Detailed Health mit DB/Redis Status
  - `/health/readiness/` - Readiness Probe für Orchestration
- **FR-11.02**: System MUSS Komponenten-Status (PostgreSQL, Redis) überprüfen
- **FR-11.03**: System MUSS JSON-formatierte Health-Antworten liefern

### Epic: Frontend UI/UX ✨ NEU

- **US-13**: Als Benutzer möchte ich eine moderne, intuitive Oberfläche nutzen
- **US-14**: Als Benutzer möchte ich Echtzeit-Statistiken auf einem Dashboard sehen
- **US-15**: Als Benutzer möchte ich mehrere Items gleichzeitig bearbeiten können (Bulk)
- **US-16**: Als Benutzer möchte ich Rechnungen nach verschiedenen Kriterien filtern können
- **US-17**: Als Benutzer möchte ich Rechnungslisten als CSV exportieren können
- **US-18**: Als Benutzer möchte ich Rechnungen aus CSV/JSON Dateien importieren können

### Epic: Testing & Quality Assurance ✨ NEU

- **US-19**: Als Entwickler möchte ich E2E Tests mit Playwright ausführen können
- **US-20**: Als Entwickler möchte ich Unit Tests für Frontend-Komponenten haben
- **US-21**: Als Entwickler möchte ich automatisierte CI/CD Tests in GitHub Actions nutzen
