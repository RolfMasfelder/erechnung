# 6. Qualitätsanforderungen

## 6.1 Qualitätsbaum

```txt
Qualität
├── Funktionalität
│   ├── Konformität (sehr hoch)
│   ├── Korrektheit (sehr hoch)
│   └── Interoperabilität (hoch)
├── Zuverlässigkeit
│   ├── Verfügbarkeit (hoch)
│   ├── Fehlertoleranz (hoch)
│   └── Wiederherstellbarkeit (mittel)
├── Benutzbarkeit
│   ├── Verständlichkeit (hoch)
│   ├── Erlernbarkeit (mittel)
│   └── Bedienbarkeit (hoch)
├── Effizienz
│   ├── Zeitverhalten (mittel)
│   └── Ressourcenverbrauch (mittel)
├── Wartbarkeit
│   ├── Analysierbarkeit (hoch)
│   ├── Änderbarkeit (hoch)
│   ├── Testbarkeit (sehr hoch)
│   └── Modularität (hoch)
└── Sicherheit
    ├── Vertraulichkeit (sehr hoch)
    ├── Integrität (sehr hoch)
    └── Authentizität (hoch)
```

## 6.2 Qualitätsszenarien

### QS-01: Konformität (Funktionalität)

**Szenario**: Ein Benutzer erstellt eine Rechnung im ZUGFeRD COMFORT Profil
**Stimulus**: Generierung einer PDF-Rechnung
**Antwort**: Das System erzeugt ein PDF/A-3 Dokument mit eingebettetem XML
**Metrik**: 100% der Rechnungen müssen Schema-Validierung bestehen

### QS-02: Verfügbarkeit (Zuverlässigkeit)

**Szenario**: Normaler Betrieb unter erwarteter Last
**Stimulus**: API-Anfragen von Clients
**Antwort**: System antwortet innerhalb der SLA
**Metrik**: 99.5% Uptime pro Monat

### QS-03: Performance (Effizienz)

**Szenario**: PDF-Generierung für Standardrechnung
**Stimulus**: API-Request zum PDF-Download
**Antwort**: System generiert und liefert PDF
**Metrik**: < 2 Sekunden Response Time bei 95% der Requests

### QS-04: API-Verständlichkeit (Benutzbarkeit)

**Szenario**: Neuer Entwickler integriert die API
**Stimulus**: Entwickler liest OpenAPI-Dokumentation
**Antwort**: Entwickler kann erste Rechnung erstellen
**Metrik**: < 30 Minuten bis zur ersten erfolgreichen Integration

### QS-05: Authentifizierung (Sicherheit)

**Szenario**: Unautorisierter Zugriff auf API
**Stimulus**: Request ohne gültiges JWT-Token
**Antwort**: System verweigert Zugriff
**Metrik**: 100% der unautorisierten Requests werden abgelehnt

### QS-06: Datenintegrität (Sicherheit)

**Szenario**: SQL-Injection-Versuch
**Stimulus**: Bösartige Eingabe in API-Parameter
**Antwort**: System validiert und bereinigt Eingabe
**Metrik**: 0 erfolgreiche Injection-Angriffe

### QS-07: Testabdeckung (Wartbarkeit)

**Szenario**: Entwickler führt Änderung durch
**Stimulus**: Code-Commit mit neuer Funktionalität
**Antwort**: Automatisierte Tests laufen
**Metrik**: Mindestens 80% Code Coverage

### QS-08: Fehlerbehandlung (Zuverlässigkeit)

**Szenario**: Ungültige Rechnungsdaten werden übermittelt
**Stimulus**: POST-Request mit fehlenden Pflichtfeldern
**Antwort**: System gibt strukturierte Fehlermeldung zurück
**Metrik**: 100% der Validierungsfehler werden mit Details gemeldet

### QS-09: Skalierbarkeit (Effizienz)

**Szenario**: Erhöhte Last während Monatsende
**Stimulus**: 10x normale Request-Rate
**Antwort**: System skaliert horizontal
**Metrik**: Response Time steigt um max. 50%

### QS-10: Wiederherstellbarkeit (Zuverlässigkeit)

**Szenario**: Datenbankausfall
**Stimulus**: PostgreSQL-Container stoppt
**Antwort**: System wird aus Backup wiederhergestellt
**Metrik**: Recovery Time Objective (RTO) < 4 Stunden

## 6.3 Nicht-funktionale Anforderungen

### NFR-01: Performance

- **NFR-01.01**: API-Response Time < 500ms für GET-Requests (90% Percentile)
- **NFR-01.02**: PDF-Generierung < 2s für Standardrechnung
- **NFR-01.03**: System unterstützt mindestens 100 gleichzeitige Benutzer
- **NFR-01.04**: Datenbankabfragen optimiert (< 100ms)

### NFR-02: Skalierbarkeit

- **NFR-02.01**: Horizontale Skalierung möglich (stateless design)
- **NFR-02.02**: System verarbeitet mindestens 1000 Rechnungen/Stunde
- **NFR-02.03**: Datenbankschema unterstützt Partitionierung
- **NFR-02.04**: Kubernetes-kompatibel für automatische Skalierung bei größeren Installationen

### NFR-03: Verfügbarkeit

- **NFR-03.01**: 99.5% Uptime (außer geplante Wartungsfenster)
- **NFR-03.02**: Graceful Degradation bei Teilausfällen
- **NFR-03.03**: Health-Check-Endpoints für Monitoring

### NFR-04: Sicherheit

- **NFR-04.01**: Alle Kommunikation über HTTPS/TLS 1.3
- **NFR-04.02**: Passwörter mit bcrypt gehashed (min. 12 Runden)
- **NFR-04.03**: JWT-Tokens mit 15 Minuten Gültigkeit
- **NFR-04.04**: Rate Limiting: max. 100 Requests/Minute pro IP
- **NFR-04.05**: SQL-Injection-Schutz durch ORM

### NFR-05: Wartbarkeit

- **NFR-05.01**: Code Coverage mindestens 80%
- **NFR-05.02**: Alle öffentlichen APIs dokumentiert
- **NFR-05.03**: Logging auf mindestens INFO-Level
- **NFR-05.04**: Modularität: max. 500 Zeilen pro Modul

### NFR-06: Portabilität

- **NFR-06.01**: Docker-basiertes Deployment
- **NFR-06.02**: Kubernetes-Manifeste für größere Installationen
- **NFR-06.03**: Keine OS-spezifischen Dependencies
- **NFR-06.04**: Konfiguration über Environment Variables
- **NFR-06.05**: Health-Check und Readiness-Probes für Kubernetes

### NFR-07: Konformität

- **NFR-07.01**: ZUGFeRD 2.3 Konformität
- **NFR-07.02**: XRechnung 3.0 Konformität
- **NFR-07.03**: PDF/A-3 Standard-Konformität
- **NFR-07.04**: EN 16931 Konformität
- **NFR-07.05**: DSGVO-Konformität

### NFR-08: Benutzerfreundlichkeit

- **NFR-08.01**: OpenAPI 3.0 Spezifikation
- **NFR-08.02**: Konsistente Fehlerformat (RFC 7807)
- **NFR-08.03**: Beispiele für alle API-Endpoints
- **NFR-08.04**: Deutsche und englische Fehlermeldungen

### NFR-09: Kompatibilität

- **NFR-09.01**: Unterstützung gängiger Browser für Swagger UI
- **NFR-09.02**: REST API Level 2 (Richardson Maturity Model)
- **NFR-09.03**: JSON Schema Validation

### NFR-10: Frontend Performance ✨ NEU

- **NFR-10.01**: First Contentful Paint (FCP) < 1.5s
- **NFR-10.02**: Time to Interactive (TTI) < 3s
- **NFR-10.03**: Bundle Size (gzipped) < 300KB initial load
- **NFR-10.04**: Vue.js 3 mit Composition API für optimale Performance
- **NFR-10.05**: Vite Build System für schnelle Development-Builds

### NFR-11: Test Coverage ✨ NEU

- **NFR-11.01**: Backend Unit Tests: mindestens 80% Coverage (aktuell: 263 Tests)
- **NFR-11.02**: Frontend Unit Tests: mindestens 80% Coverage (aktuell: 381 Tests)
- **NFR-11.03**: E2E Tests: mindestens 90% Pass-Rate (aktuell: 96% mit Playwright)
- **NFR-11.04**: CI/CD Pipeline mit automatisierten Tests in GitHub Actions
- **NFR-11.05**: Test-Isolation: Keine Abhängigkeiten zwischen Tests

### NFR-12: Kubernetes Enterprise Deployment ✨ NEU

- **NFR-12.01**: Multi-Node Cluster Support (1 Control-Plane + 2+ Worker)
- **NFR-12.02**: LoadBalancer Integration (MetalLB für Bare-Metal)
- **NFR-12.03**: Ingress Controller mit TLS/HTTPS (nginx)
- **NFR-12.04**: Network Policies für Zero-Trust Segmentierung
- **NFR-12.05**: Pod Security Standards (baseline/restricted)
- **NFR-12.06**: CNI Provider für Network Policies (Calico)
- **NFR-12.07**: Persistent Storage mit PVC (PostgreSQL, Redis)
- **NFR-12.08**: InitContainer für DB Migrations (django-init Job)

### NFR-13: Container Registry ✨ NEU

- **NFR-13.01**: Lokale HTTPS Docker Registry für Offline-Deployments
- **NFR-13.02**: Image Pull von lokaler Registry < 20s (PostgreSQL)
- **NFR-13.03**: containerd Mirror Configuration auf allen Kubernetes Nodes
- **NFR-13.04**: Alle Application + Infrastructure Images lokal verfügbar
- **NFR-13.05**: Registry mit TLS-Zertifikaten (self-signed für Development)

### NFR-14: Developer Experience ✨ NEU

- **NFR-14.01**: Docker-First Development (alle Commands via docker compose)
- **NFR-14.02**: Hot-Reload für Frontend (Vite HMR)
- **NFR-14.03**: Lokale E2E Tests in isoliertem Container
- **NFR-14.04**: Vollständige API-Dokumentation mit OpenAPI/Swagger
- **NFR-14.05**: Strukturierte Projekt-Dokumentation (arc42 + req42)
