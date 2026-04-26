# 7. Risiken und technische Schulden

## 7.1 Risiken

### R-01: Standardänderungen (HOCH)
**Beschreibung**: ZUGFeRD, XRechnung oder EN 16931 Standards ändern sich
**Wahrscheinlichkeit**: Mittel
**Auswirkung**: Hoch
**Maßnahmen**:
- Modularisierung der Standard-Implementierung
- Versionierung der Generierungslogik
- Monitoring von Standard-Updates
- Flexible XML-Template-Engine

### R-02: Performance bei großem Datenvolumen (MITTEL)
**Beschreibung**: System verlangsamt sich bei vielen Rechnungen
**Wahrscheinlichkeit**: Mittel
**Auswirkung**: Mittel
**Maßnahmen**:
- Datenbankindexierung optimieren
- Caching-Strategie implementieren
- Pagination in API erzwingen
- Performance-Tests in CI

### R-03: Sicherheitslücken (HOCH)
**Beschreibung**: Schwachstellen in Dependencies oder eigenem Code
**Wahrscheinlichkeit**: Mittel
**Auswirkung**: Hoch
**Maßnahmen**:
- Automatische Dependency-Updates (Dependabot)
- Security Scanning in CI
- Regelmäßige Penetrationstests
- Security-Best-Practices befolgen

### R-04: PDF-Generierung inkonsistent (MITTEL)
**Beschreibung**: PDF/A-3 Konformität nicht immer gegeben
**Wahrscheinlichkeit**: Niedrig
**Auswirkung**: Hoch
**Maßnahmen**:
- Automatisierte Validierung generierter PDFs
- Verwendung etablierter Bibliotheken
- Unit-Tests für PDF-Generierung
- Manuelle Stichproben

### R-05: Datenverlust (HOCH)
**Beschreibung**: Verlust von Rechnungsdaten durch Ausfall
**Wahrscheinlichkeit**: Niedrig
**Auswirkung**: Sehr Hoch
**Maßnahmen**:
- Automatisierte Backups (täglich)
- Point-in-Time Recovery
- Backup-Restore-Tests
- Replikation

### R-06: Compliance-Verstöße (HOCH)
**Beschreibung**: Nichteinhaltung von DSGVO oder GoBD
**Wahrscheinlichkeit**: Niedrig
**Auswirkung**: Sehr Hoch
**Maßnahmen**:
- Datenschutz-Folgenabschätzung
- Audit-Logging
- Verschlüsselung sensibler Daten
- Regelmäßige Compliance-Reviews

### R-07: Abhängigkeit von Drittbibliotheken (MITTEL)
**Beschreibung**: Kritische Library wird nicht mehr gewartet
**Wahrscheinlichkeit**: Niedrig
**Auswirkung**: Mittel
**Maßnahmen**:
- Bewertung vor Auswahl (Community, Aktivität)
- Abstraktion von Bibliotheken
- Plan B für kritische Dependencies
- Eigene Forks bei Bedarf

### R-08: Skalierungsprobleme (MITTEL)
**Beschreibung**: System kommt an Lastgrenzen
**Wahrscheinlichkeit**: Mittel
**Auswirkung**: Mittel
**Maßnahmen**:
- Last- und Stresstests
- Horizontale Skalierung vorbereiten
- Monitoring und Alerting
- Capacity Planning

## 7.2 Technische Schulden

### TD-01: Fehlende Migrations-Strategie
**Status**: ✅ Erledigt (04.03.2026)
**Priorität**: Mittel
**Beschreibung**: Keine definierte Strategie für Daten-Migrationen bei Schema-Änderungen
**Auswirkung**: Erschwertes Deployment bei Breaking Changes
**Lösung**: Siehe `docs/MIGRATION_STRATEGY.md`
- Django Migrations systematisch dokumentiert (5 Migrationen katalogisiert)
- Rollback-Strategie mit Matrix und Prozedur definiert
- Zero-Downtime-Migration-Pattern (3-Phasen-Ansatz, Batch-Processing)
- Management Command `check_migrations` für Pre-Deployment-Validierung
- N+1 Anti-Pattern in Migration 0002 behoben (Migration ersetzt)

### TD-02: Unvollständige Fehlerbehandlung
**Status**: Teilweise
**Priorität**: Hoch
**Beschreibung**: Nicht alle Edge Cases in Fehlerbehandlung abgedeckt
**Auswirkung**: Potenzielle 500-Fehler statt aussagekräftiger Meldungen
**Lösungsansatz**:
- Systematisches Error-Mapping definieren
- Globaler Exception Handler
- Fehler-Katalog erstellen

### TD-03: Monitoring-Lücken
**Status**: Offen
**Priorität**: Mittel
**Beschreibung**: Application-Level Monitoring nicht vollständig
**Auswirkung**: Probleme werden zu spät erkannt
**Lösungsansatz**:
- Prometheus/Grafana Integration
- Custom Metrics definieren
- Alerting-Regeln etablieren

### TD-04: Dokumentations-Inkonsistenzen
**Status**: Teilweise
**Priorität**: Niedrig
**Beschreibung**: Code-Kommentare und externe Dokumentation manchmal nicht synchron
**Auswirkung**: Verwirrung bei Entwicklern
**Lösungsansatz**:
- Docs-as-Code Ansatz
- Automatische API-Docs aus Code
- Review-Prozess für Dokumentation

### TD-05: Test-Daten-Management
**Status**: Offen
**Priorität**: Mittel
**Beschreibung**: Keine zentrale Verwaltung von Test-Rechnungsdaten
**Auswirkung**: Inkonsistente Tests, Duplikation
**Lösungsansatz**:
- Fixture-Management System
- Factory-Pattern für Test-Daten
- Realistische Testdaten-Generator

### TD-06: Fehlende API-Rate-Limiting-Granularität
**Status**: Offen
**Priorität**: Niedrig
**Beschreibung**: Rate Limiting nur auf IP-Ebene, nicht per User/API-Key
**Auswirkung**: Unfaires Resource-Sharing, DoS-Anfälligkeit
**Lösungsansatz**:
- Django Rate Limiting erweitern
- Per-User/Token Limitierung
- Differentierte Quotas

### TD-07: Logging-Strategie unvollständig
**Status**: Teilweise
**Priorität**: Mittel
**Beschreibung**: Inkonsistentes Log-Format, fehlende Korrelations-IDs
**Auswirkung**: Schwierige Fehlersuche in verteilten Systemen
**Lösungsansatz**:
- Strukturiertes Logging (JSON)
- Request-IDs durchgängig
- Zentrales Log-Aggregation

## 7.3 Abhängigkeiten und externe Risiken

### Externe Abhängigkeiten
- **Python Ecosystem**: Stabilität von Django, DRF, PDF-Libs
- **PostgreSQL**: Performance und Verfügbarkeit der Datenbank
- **Docker/Container Runtime**: Deployment-Infrastruktur
- **Standard-Organisationen**: Stabilität von ZUGFeRD/XRechnung

### Mitigations
- Regelmäßige Dependency-Updates
- Monitoring von Upstream-Änderungen
- Abstraktions-Layer für kritische Dependencies
- Alternative Lösungen evaluieren
