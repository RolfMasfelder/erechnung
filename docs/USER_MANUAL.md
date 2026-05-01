# Benutzerhandbuch — eRechnung

> Version: 1.0 — 14. März 2026
> Zielgruppe: Anwender:innen und Administrator:innen (ohne Programmierkenntnisse)

---

## Inhalt

1. [Anmeldung](#1-anmeldung)
2. [Übersicht — Dashboard](#2-übersicht--dashboard)
3. [Rechnungen](#3-rechnungen)
4. [Geschäftspartner](#4-geschäftspartner)
5. [Produkte & Artikel](#5-produkte--artikel)
6. [Firmen (eigene Firmen)](#6-firmen-eigene-firmen)
7. [Import & Export](#7-import--export)
8. [Benutzerverwaltung & Rollen (RBAC)](#8-benutzerverwaltung--rollen-rbac)
9. [Django-Admin-Interface](#9-django-admin-interface)
10. [Häufige Fehlermeldungen](#10-häufige-fehlermeldungen)

---

## 1. Anmeldung

Rufen Sie das Frontend auf:

- **Entwicklung:** http://localhost:5173
- **Kubernetes:** http://192.168.178.80

Geben Sie Ihren **Benutzernamen** und Ihr **Passwort** ein und klicken Sie auf _Anmelden_.

Das System verwendet JWT-Tokens. Das Zugriffstoken läuft nach kurzer Zeit ab — die Anwendung erneuert es automatisch im Hintergrund. Bei einer abgelaufenen Sitzung werden Sie zur Anmeldemaske weitergeleitet.

**Erstanmeldung als Administrator:**
Benutzername und Passwort wurden beim Setup mit `createsuperuser` vergeben.

---

## 2. Übersicht — Dashboard

Nach der Anmeldung sehen Sie das Dashboard mit einer Übersicht:

| Kennzahl | Beschreibung |
|----------|--------------|
| Rechnungen gesamt | Alle Rechnungen im System |
| Ausstehend | Rechnungen mit Status SENT oder OVERDUE |
| Bezahlt | Rechnungen mit Status PAID |
| Offener Betrag | Summe unbezahlter Rechnungen (EUR) |
| Geschäftspartner | Aktive Kunden und Lieferanten |
| Produkte | Aktive Artikel im Katalog |

---

## 3. Rechnungen

### 3.1 Rechnungsstatus

Jede Rechnung durchläuft folgende Status-Stufen:

```
DRAFT → SENT → PAID
         ↓
      OVERDUE
         ↓
      CANCELLED
```

| Status | Bedeutung | Bearbeitbar? |
|--------|-----------|--------------|
| **DRAFT** | Entwurf — noch nicht versendet | Ja |
| **SENT** | Versendet / Fällig | Nein (GoBD-Sperre) |
| **PAID** | Bezahlt | Nein (GoBD-Sperre) |
| **OVERDUE** | Überfällig | Nein |
| **CANCELLED** | Storniert | Nein |

> ⚠️ **GoBD:** Sobald eine Rechnung den Status SENT, PAID oder CANCELLED erreicht, wird sie automatisch gesperrt und kann nicht mehr geändert werden. Das ist gesetzlich vorgeschrieben.

### 3.2 Neue Rechnung erstellen

1. Navigieren Sie zu **Rechnungen → Neue Rechnung**
2. Füllen Sie die Pflichtfelder aus:
   - **Rechnungstyp:** OUTGOING (ausgehend) oder INCOMING (eingehend)
   - **Firma:** Ihre eigene Firma (muss vorher angelegt sein)
   - **Geschäftspartner:** Kunde oder Lieferant
   - **Rechnungsdatum** und **Fälligkeitsdatum**
   - **Währung** (Standard: EUR)
   - **Nettobetrag**, **MwSt-Betrag**, **Bruttobetrag**
3. Fügen Sie optional **Rechnungszeilen** hinzu (für ZUGFeRD empfohlen)
4. Klicken Sie auf **Speichern** — die Rechnung wird als DRAFT gespeichert

> Die **Rechnungsnummer** wird automatisch vom System generiert und kann nicht manuell gesetzt werden.

### 3.3 Vorschau und Download

<!-- TODO: Screenshot 30.04.2026 — neue Action-Bar mit Vorschau-Button und Smart-Download-Button (B2B: "PDF herunterladen", B2G: "XML herunterladen") -->

**Vorschau:**
1. Öffnen Sie die Rechnung
2. Klicken Sie auf **Vorschau** — das PDF öffnet sich in einem neuen Browser-Tab

**Herunterladen:**
1. Klicken Sie auf **PDF herunterladen** (B2B) bzw. **XML herunterladen** (B2G/XRechnung)
2. Die Datei wird direkt heruntergeladen

> Das generierte PDF enthält das maschinenlesbare ZUGFeRD-XML eingebettet. Es kann direkt an Kunden versendet und von deren ERP-System automatisch verarbeitet werden.

### 3.4 Rechnung versenden (Status → SENT)

<!-- TODO: Screenshot 30.04.2026 — SendInvoiceModal mit drei Tabs: E-Mail, Datei herunterladen, Peppol (disabled) -->

1. Klicken Sie auf **Versenden** in der Rechnungsdetailansicht
2. Wählen Sie den Versandweg:
   - **E-Mail**: Empfänger-Adresse eingeben und Formular absenden — Status wechselt automatisch auf SENT
   - **Datei herunterladen**: Datei lokal speichern und manuell versenden (B2B → PDF/A-3, B2G → XRechnung XML)
   - **Peppol/Portal**: geplant für eine spätere Version
3. Mit E-Mail-Versand wird die Rechnung GoBD-gesperrt (Status SENT)

### 3.5 Rechnung als bezahlt markieren

1. Öffnen Sie die Rechnung (Status SENT oder OVERDUE)
2. Klicken Sie auf **Als bezahlt markieren**
3. Status wechselt zu PAID — Rechnung ist unwiderruflich gesperrt

### 3.6 Rechnung filtern und suchen

Auf der Rechnungsliste stehen folgende Filter zur Verfügung:

- **Status:** DRAFT / SENT / PAID / OVERDUE / CANCELLED
- **Zeitraum:** Rechnungsdatum von/bis
- **Geschäftspartner**
- **Volltextsuche:** Sucht in Rechnungsnummer, Notizen, Partner-Name

### 3.7 Anhänge hinzufügen

Zu jeder Rechnung können Dateien angehängt werden (z. B. Lieferscheine, Verträge).
Navigieren Sie zum Abschnitt **Anhänge** in der Rechnungsdetailansicht und laden Sie die Datei hoch.

---

## 4. Geschäftspartner

Geschäftspartner können **Kunden**, **Lieferanten** oder beides gleichzeitig sein.

### 4.1 Neuen Geschäftspartner anlegen

1. Navigieren Sie zu **Geschäftspartner → Neu**
2. Wählen Sie **Partnertyp:**
   - `INDIVIDUAL` — Privatperson
   - `BUSINESS` — Unternehmen
   - `GOVERNMENT` — Behörde
   - `NON_PROFIT` — Verein/Stiftung
3. Geben Sie **Firmenname** oder **Vor-/Nachname** ein
4. Pflichtfelder: **Straße**, **PLZ**, **Stadt**
5. Optional aber empfohlen: **Steuernummer**, **USt-ID**, **E-Mail**
6. Klicken Sie auf **Speichern** — die **Partnernummer** wird automatisch vergeben (z. B. `BP-0042`)

### 4.2 Massenimport von Geschäftspartnern

Über **Geschäftspartner → Importieren** können mehrere Partner gleichzeitig importiert werden.
Format: JSON-Array mit den Pflichtfeldern `address_line1`, `postal_code`, `city`.
Option: `skip_duplicates` überspringt bereits vorhandene Einträge.

---

## 5. Produkte & Artikel

Im Produktkatalog verwalten Sie Artikel, die in Rechnungszeilen verwendet werden.

**Produkttypen:** `PHYSICAL` (Ware), `SERVICE` (Dienstleistung), `DIGITAL`, `SUBSCRIPTION`

**Maßeinheiten:** PCE (Stück), HUR (Stunde), DAY (Tag), KGM (kg), LTR (Liter), MON (Monat)

### Lagerbestand

Für physische Produkte mit aktivierter Lagerhaltung (`track_inventory = true`) wird der Bestand automatisch verwaltet. Bei niedrigem Bestand erscheinen Produkte in der Ansicht **Produkte → Niedriger Bestand**.

---

## 6. Firmen (eigene Firmen)

Unter **Firmen** verwalten Sie Ihre eigenen Unternehmen, die als Rechnungsaussteller auftreten.

Pflichtfelder: **Name**, **Steuernummer**, **Straße**, **PLZ**, **Stadt**
Empfohlen: **USt-ID**, **IBAN/BIC** (erscheinen im PDF), **Logo** (erscheint im PDF-Header)

Eine Firma kann als **Standard-Firma** für neue Rechnungen definiert werden.

---

## 7. Import & Export

### Export

Unter **Rechnungen → Exportieren** können Rechnungen exportiert werden:

- Als **CSV** (Tabellenkalkulation)
- Als **JSON** (strukturiert, für Integration)

Berechtigung benötigt: `can_export_data`

### Massenimport

Geschäftspartner und Produkte können per JSON-Datei importiert werden:

- **Geschäftspartner:** `POST /api/business-partners/import/`
- **Produkte:** `POST /api/products/import/`

Berechtigung benötigt: `can_import_data` (Admin-Rolle)

---

## 8. Benutzerverwaltung & Rollen (RBAC)

Das System verwendet rollenbasierte Zugangskontrolle (RBAC).

### Verfügbare Rollen

| Rolle | Typische Funktion | Wichtigste Rechte |
|-------|------------------|-------------------|
| **ADMIN** | Systemadministrator | Alle Rechte, incl. Benutzerverwaltung |
| **MANAGER** | Buchhaltungsleitung | Rechnungen erstellen, versenden, bezahlt markieren; Export |
| **ACCOUNTANT** | Buchhalter/in | Rechnungen erstellen und bearbeiten (DRAFT) |
| **CLERK** | Sachbearbeiter/in | Eingeschränkte Bearbeitungsrechte |
| **AUDITOR** | Prüfer/in | Nur Lesezugriff + Audit-Log-Einsicht |
| **READ_ONLY** | Beobachter | Nur Lesezugriff |

### Benutzer anlegen (Admin)

1. Öffnen Sie das **Django-Admin-Interface:** http://localhost:8000/admin/
2. Navigieren Sie zu **Users → Hinzufügen**
3. Erstellen Sie den Benutzer mit Benutzername und Passwort
4. Navigieren Sie zu **User Roles → Hinzufügen**
5. Wählen Sie den Benutzer und vergeben Sie die gewünschte **Rollenart**
6. Aktivieren Sie die benötigten **Einzelberechtigungen** (Fine-Grained Control)

### Berechtigungsübersicht

| Berechtigung | Admin | Manager | Accountant | Clerk | Auditor | Read Only |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Rechnungen erstellen | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| Rechnungen bearbeiten | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| Rechnungen löschen | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| PDF generieren | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Als bezahlt markieren | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Daten exportieren | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Audit-Log einsehen | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Benutzer verwalten | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Einstellungen ändern | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

⚠️ = abhängig von der individuellen Rollenkonfiguration

### Rechnungsbetrag-Limit

Für jede Rolle kann ein **maximaler Rechnungsbetrag** (`max_invoice_amount`) festgelegt werden. Rechnungen über diesem Betrag können von dieser Rolle nicht erstellt werden.

---

## 9. Django-Admin-Interface

Das Django-Admin-Interface unter http://localhost:8000/admin/ bietet erweiterte Verwaltungsfunktionen, die im Frontend nicht verfügbar sind.

**Zugang:** Nur für Benutzer mit `is_staff = True` oder `is_superuser = True`.

### Verfügbare Admin-Bereiche

| Bereich | Zweck |
|---------|-------|
| **Users** | Benutzer anlegen, Passwörter zurücksetzen |
| **User Roles** | RBAC-Rollen konfigurieren und Benutzer zuweisen |
| **Invoices** | Rechnungen direkt anzeigen/suchen (Notfall-Zugriff) |
| **Business Partners** | Geschäftspartner verwalten |
| **Audit Logs** | GoBD-konformer Audit-Trail einsehen (read-only) |
| **Countries** | Länderdaten und MwSt-Sätze verwalten |

### Passwort zurücksetzen

1. **Django Admin:** http://localhost:8000/admin/auth/user/
2. Benutzer auswählen → **Passwort ändern**

Oder per Kommandozeile (Adminzugriff erforderlich):

```bash
docker compose exec web python project_root/manage.py changepassword <benutzername>
```

### Audit-Log einsehen

Unter **Audit Logs** ist jede Änderung an Rechnungen, Geschäftspartnern und Firmen protokolliert.
Die Logs sind **unveränderbar** (GoBD-Anforderung) und werden **10 Jahre aufbewahrt**.

Jeder Log-Eintrag enthält:

- Zeitstempel (UTC)
- Benutzer (wer hat geändert)
- Aktion (CREATE / UPDATE / DELETE / VIEW)
- Betroffenes Objekt
- Integritäts-Hash (kryptografisch)

---

## 10. Häufige Fehlermeldungen

| Fehlermeldung | Ursache | Lösung |
|---------------|---------|--------|
| **„Keine Berechtigung"** / 403 | Ihre Rolle hat nicht die nötige Berechtigung | Administrator kontaktieren |
| **„Sitzung abgelaufen"** / 401 | JWT-Token abgelaufen | Seite neu laden / erneut anmelden |
| **„Ressource nicht gefunden"** / 404 | Datensatz existiert nicht oder wurde gelöscht | Suche/Filter zurücksetzen |
| **„Dieses Feld darf nicht leer sein"** | Pflichtfeld fehlt | Markierte Felder ausfüllen |
| **„Rechnung kann nicht bearbeitet werden"** | Status ist SENT/PAID/CANCELLED (GoBD-Sperre) | Rechnung ist unveränderbar (gesetzlich) |
| **„PDF-Generierung fehlgeschlagen"** | Pflichtfelder für ZUGFeRD fehlen | Firma und Geschäftspartner vollständig ausfüllen |
| **„Rechnungsnummer bereits vergeben"** | Duplikat-Kontrolle | Automatisch generierte Nummer verwenden |
| **„Betrag überschreitet Limit"** | Rechnungsbetrag-Limit der Rolle überschritten | Manager oder Admin für höheren Betrag beauftragen |

### Support

Bei technischen Problemen:

- **Logs prüfen:** `docker compose logs -f web` (nur Admins mit Serverzegang)
- **Health-Check:** http://localhost:8000/health/detailed/ (erfordert Login)
- **Swagger UI:** http://localhost:8000/api/docs/ (API direkt testen)

---

## 11. Installation aktualisieren

### 11.1 Vorbereitung

Vor jedem Update:

1. **Backup erstellen:** `./scripts/backup.sh` (sichert Datenbank + Mediadateien)
2. **aktuelle Version notieren:** `docker compose exec web python project_root/manage.py version` oder http://localhost:8000/api/version/
3. **Changelog lesen:** Prüfen Sie die Datei `CHANGELOG.md` auf Breaking Changes

### 11.2 Docker-Update (KMU-Installation)

**Ein-Befehl-Update:**

```bash
cd /pfad/zu/erechnung
./scripts/update-docker.sh
```

Das Skript führt automatisch durch:

- Backup der aktuellen Installation
- Download des neuen Images
- Pre-Flight-Checks (Festplatte, Datenbank-Verbindung, etc.)
- Wartungsseite aktivieren
- Datenbank-Migration
- Neustart der Dienste
- Post-Update-Verifizierung

**Manuelles Update (Schritt-für-Schritt):**

```bash
# 1. Backup
./scripts/backup.sh

# 2. Neues Image bauen / herunterladen
docker compose pull    # oder: docker compose build

# 3. Dienste stoppen
docker compose down

# 4. Dienste mit neuem Image starten
docker compose up -d

# 5. Migrationen ausführen
docker compose exec web python project_root/manage.py migrate

# 6. Statische Dateien aktualisieren
docker compose exec web python project_root/manage.py collectstatic --noinput

# 7. Prüfen ob alles läuft
curl http://localhost:8000/health/readiness/
```

### 11.3 Kubernetes-Update (Enterprise-Installation)

```bash
cd /pfad/zu/erechnung
./scripts/update-k3s.sh
```

Das Skript führt ein Rolling-Update durch:

- PodDisruptionBudgets sichern Verfügbarkeit
- Migrations-Job läuft vor dem Rollout
- Neue Pods werden schrittweise gestartet
- Alte Pods werden erst gestoppt wenn neue bereit sind

**Voraussetzungen:**

- `kubectl` konfiguriert und Cluster erreichbar
- Ausreichend Ressourcen für parallele alte + neue Pods

### 11.4 Rollback

Falls nach dem Update Probleme auftreten:

**Docker:**

```bash
./scripts/rollback-docker.sh
```

**Kubernetes:**

```bash
kubectl rollout undo deployment/django-web -n erechnung
kubectl rollout undo deployment/celery-worker -n erechnung
```

### 11.5 Fehlerbehebung

| Problem | Ursache | Lösung |
|---------|---------|--------|
| **„Migrationen fehlgeschlagen"** | Inkompatible Datenbankänderung | Rollback durchführen, CHANGELOG prüfen |
| **Health-Check zeigt „not_ready"** | Migrationen noch nicht angewandt | `docker compose exec web python project_root/manage.py migrate` |
| **Wartungsseite bleibt aktiv** | Update-Skript abgebrochen | Manuell: `docker compose exec web rm /tmp/maintenance.flag` |
| **Container startet nicht** | Fehlende Umgebungsvariable | `docker compose logs web` prüfen, `.env` vergleichen |
| **„Permission denied" bei Backup** | Dateiberechtigungen | `chmod +x scripts/backup.sh scripts/update-docker.sh` |
