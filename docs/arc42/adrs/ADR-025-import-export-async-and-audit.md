# ADR 025: Import/Export — Async Strategy & Audit Granularity

## Status

Accepted — 28. April 2026

## Kontext

Der Import/Export-Workflow für Rechnungen, Geschäftspartner und Produkte ist in den Phasen 1–3 implementiert (CSV/JSON, Validation, Dry-Run). Phase 4 sollte ursprünglich asynchrone Exports und vollständiges Audit-Logging einführen. Vor der Umsetzung waren zwei Architekturentscheidungen offen, die in `TODO_2026.md` §3.14 dokumentiert waren.

## Entscheidungen

### 1. Async Exports (Celery): vorerst nicht integrieren — synchron bleiben

**Begründung:**

- Es gibt aktuell keine bekannten Lastprobleme; das System läuft nicht produktiv.
- Bisher beobachtete Export-Größen (≤ wenige Tausend Rechnungen) sind innerhalb der HTTP-Timeout-Grenzen (`gunicorn` 120s, nginx 300s) verarbeitbar.
- Celery-Integration bringt Komplexität: zusätzlicher Worker-Prozess, Result-Backend, Monitoring, Healthcheck, Image-Größe, Deployment-Dependency in Docker und K3s. Das lohnt sich erst bei realer Notwendigkeit.
- **Trigger für Re-Evaluation:** Sobald ein Export im Schnitt > 30 s dauert oder Browser-Timeouts auftreten, wird Celery nachgerüstet (eigene Iteration). Zwischen-Schritt wäre auch ein synchroner Streaming-Response, der weniger Komplexität bringt als Celery.

**YAGNI-Prinzip:** Implementiere Async erst, wenn synchron nachweislich nicht mehr ausreicht.

### 2. Audit-Log-Granularität bei Import: Hybrid (Job + zusammengefasste Record-IDs)

**Begründung:**

Die zwei diskutierten Optionen waren:

- A) **Pro Datensatz** ein Audit-Eintrag — vollständig nachvollziehbar, aber für Imports mit >1000 Records erzeugt das ein Vielfaches an Log-Volumen.
- B) **Nur eine Zusammenfassung** pro Job — kompakt, aber GoBD-grenzwertig (welche genauen Datensätze wurden importiert?).

**Gewählt: Hybrid (Mittelweg, GoBD-konform):**

- **Ein** `AuditLog`-Eintrag pro Import-Job mit:
  - User, Zeitstempel, Quelldatei (Hash), Format, Dry-Run-Flag
  - Aggregat: `created_count`, `updated_count`, `skipped_count`, `failed_count`
  - Liste der **IDs** (nicht volle Payloads) der erstellten/aktualisierten Records — als JSON-Array im `details`-Feld
  - Bei Fehler-Records: ID + Fehlerursache (kompakt)
- **Keine** zusätzlichen pro-Record Audit-Einträge im Import-Service. Pro-Record-Änderungen werden weiterhin durch das bestehende generelle Modell-Audit-Log (Save-Hook) erfasst, das jedem `INSERT/UPDATE` automatisch folgt.

Damit gilt:

- GoBD-Nachvollziehbarkeit: Welche Records wurden in welchem Job angefasst? → Job-Eintrag mit ID-Liste.
- Welche genauen Feldwerte wurden geschrieben? → reguläres Modell-Audit-Log.
- Log-Volumen: 1 Eintrag pro Import-Job statt N Einträge.

## Konsequenzen

- Phase 4 wird nicht implementiert wie ursprünglich geplant. Stattdessen: Audit-Hybrid jetzt umsetzen, Async-Exports erst nach realem Lastnachweis.
- `TODO_2026.md` §3.14 wird geschlossen.
- Folge-Iteration für den Audit-Hybrid (eigene Aufgabe, nicht Teil dieses ADR): Erweiterung von `ImportService.import_records()` um einen aggregierten Audit-Eintrag mit ID-Liste. **Umgesetzt am 29.04.2026** in `BusinessPartnerImportView` und `ProductImportView` (`_log_import_audit()` Helper in `rest_views.py`); 4 neue Tests in `test_import.py::TestImportAuditLogging`.

## Re-Evaluation

Bei eines der folgenden Trigger neue Iteration / ADR:

- Synchrone Exports überschreiten regelmäßig 30 s.
- Audit-Log-Volumen wird zum Performance-Problem (unwahrscheinlich beim Hybrid).
- Compliance-Audit fordert pro-Record-Granularität explizit.
