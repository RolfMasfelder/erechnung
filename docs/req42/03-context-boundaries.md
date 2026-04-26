# 3. Kontextabgrenzung

## 3.1 Fachlicher Kontext

### Eingehende fachliche Schnittstellen

| Nachbar | Beschreibung |
|---------|--------------|
| Client-Anwendungen | Frontend-Systeme, die e-Rechnungen erstellen möchten |
| ERP-Systeme | Unternehmens-Software mit Rechnungsdaten |
| Buchhaltungssysteme | Finanzsoftware zur Weiterverarbeitung |

### Ausgehende fachliche Schnittstellen

| Nachbar | Beschreibung |
|---------|--------------|
| E-Rechnung-Empfänger | Behörden und Unternehmen, die e-Rechnungen empfangen |
| Archivierungssysteme | Langzeitarchivierung von Rechnungsdokumenten |
| Validierungsservices | Externe Dienste zur Validierung von e-Rechnungen |

## 3.2 Technischer Kontext

### Eingabeschnittstellen

| Kanal | Details |
|-------|---------|
| REST API | JSON-basierte API für CRUD-Operationen |
| Datei-Upload | Upload von Rechnungsdaten (CSV, JSON, XML) |

### Ausgabeschnittstellen

| Kanal | Details |
|-------|---------|
| PDF-Download | ZUGFeRD-konforme PDF/A-3 Dateien |
| XML-Export | Reine XML-Daten (XRechnung) |
| REST API | JSON-Antworten für Abfragen |

### Externe Systeme

| System | Integration |
|--------|-------------|
| PostgreSQL | Datenbankverbindung über TCP/IP |
| SMTP-Server | E-Mail-Versand (optional) |
| S3-Storage | Objektspeicher für Dokumente (optional) |

## 3.3 Abgrenzung

### Im Scope
- Erstellung von ZUGFeRD-konformen Rechnungen
- PDF-Generierung mit XML-Einbettung
- Validierung gegen Standards
- CRUD-Operationen für Rechnungsdaten
- RESTful API

### Außerhalb des Scope
- Komplette ERP-Funktionalität
- Finanzbuchhaltung
- Zahlungsabwicklung
- OCR-Texterkennung
- E-Mail-Client-Funktionalität
