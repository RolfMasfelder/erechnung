# Implementierungsplan: Update-Strategie für eRechnung

**Erstellt:** 17.03.2026
**Basisdokument:** `docs/UPDATE_STRATEGY.md`
**Status:** Abgeschlossen (Phase 1–7 implementiert, 18.03.2026)

---

## Übersicht

Der Plan gliedert die Umsetzung der Update-Strategie (inkl. Integrationstests) in **7 aufeinander aufbauende Phasen**. Jede Phase liefert ein in sich funktionsfähiges Ergebnis und kann unabhängig abgenommen werden.

```
Phase 1: Fundament          ← Voraussetzung für alles Weitere
Phase 2: Docker-Update       ← KMU-Kunden können updaten
Phase 3: Docker-Tests        ← Docker-Updates sind abgesichert
Phase 4: K3s-Update          ← Enterprise-Kunden können updaten
Phase 5: K3s-Tests           ← K3s-Updates sind abgesichert
Phase 6: Edge-Cases & Härte  ← Grenzfälle abgesichert
Phase 7: CI/CD & Doku        ← Vollautomatisierung + Endanwender-Doku
```

**Abhängigkeiten:**

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──┐
                                    ├──→ Phase 6 ──→ Phase 7
Phase 1 ──→ Phase 4 ──→ Phase 5 ──┘
```

Phase 2+3 (Docker) und Phase 4+5 (K3s) können parallel bearbeitet werden.

---

## Phase 1: Fundament — Versionierung, API-Endpoint, Testinfrastruktur

**Ziel:** Alle Voraussetzungen schaffen, auf denen Update-Skripte und Tests aufbauen.

**Liefergegenstände:**

- [x] `/api/version/` Endpoint (Django View)
- [x] `LABEL version=<VERSION>` im Dockerfile
- [x] `CHANGELOG.md` mit v1.0.0
- [x] `docker-compose.update-test.yml` (isolierte Testumgebung)
- [x] Fixture-Sets: `minimal` und `standard`
- [x] Pre-Flight-Check-Modul (als Shell-Library `scripts/lib/preflight.sh`)
- [x] Test-Orchestrierungsskript: Grundgerüst `scripts/run-update-tests.sh`

### Aufgaben

#### 1.1 `/api/version/` Endpoint

**Referenz:** UPDATE_STRATEGY Kap. 11.3

```
Datei: project_root/invoice_app/api/views/version_view.py (neu)
- GET /api/version/ → { "version": "1.0.0", "git_sha": "...", "build_date": "..." }
- Version aus pyproject.toml lesen (importlib.metadata)
- Kein Login erforderlich (öffentlich)
- URL in urls.py registrieren
```

Tests:
- Unit-Test: Endpoint gibt korrekte Version zurück
- Unit-Test: Response-Format ist JSON mit erwarteten Feldern

#### 1.2 Image-Labels im Dockerfile

**Referenz:** UPDATE_STRATEGY Kap. 11.3

```
Datei: Dockerfile
- ARG APP_VERSION=1.0.0
- LABEL org.opencontainers.image.version="${APP_VERSION}"
- docker build --build-arg APP_VERSION=$(python -c "...") .
```

#### 1.3 CHANGELOG.md

**Referenz:** UPDATE_STRATEGY Kap. 7.1

```
Datei: CHANGELOG.md (Projekt-Root)
- Keep a Changelog Format (https://keepachangelog.com)
- Initialer Eintrag [1.0.0] mit allen bisherigen Features
```

#### 1.4 Isolierte Testumgebung

**Referenz:** UPDATE_STRATEGY Kap. 10.2

```
Datei: docker-compose.update-test.yml (neu)
- db-update-test (tmpfs, RAM-Disk)
- redis-update-test (tmpfs)
- web-old (OLD_VERSION)
- web-new (NEW_VERSION, Profile "upgrade-phase")
- Eigenes Netzwerk: update-test
- Eigene Ports (kein Konflikt mit dev/prod)
```

#### 1.5 Fixture-Sets

**Referenz:** UPDATE_STRATEGY Kap. 10.9

```
Datei: test-artifacts/update-tests/fixtures/minimal.json
Datei: test-artifacts/update-tests/fixtures/standard.json
- Exportiert via dumpdata oder generate_test_data
- Versioniert im Repository
```

#### 1.6 Pre-Flight-Check-Library

**Referenz:** UPDATE_STRATEGY Kap. 11.1

```
Datei: scripts/lib/preflight.sh (neu)
Funktionen:
- check_docker_running()
- check_disk_space(min_gb)
- check_compose_file_exists()
- check_current_version()
- check_target_version_exists()
- check_cluster_health()      # K3s
- check_nodes_ready()         # K3s
- acquire_update_lock() / release_update_lock()
```

#### 1.7 Test-Orchestrierung Grundgerüst

**Referenz:** UPDATE_STRATEGY Kap. 10.8.1

```
Datei: scripts/run-update-tests.sh (neu)
- Argument-Parsing: --all, --level N, --test ID, --docker-only, --k3s-only
- Testumgebung Setup/Teardown
- Exit-Codes: 0/1/2
- Log-Verzeichnis: test-artifacts/update-tests/logs/
- Zunächst nur Skelett — Tests werden in späteren Phasen eingefügt
```

### Abnahmekriterien Phase 1

- [x] `curl /api/version/` gibt `{"version": "1.0.0", ...}` zurück
- [x] `docker inspect` zeigt Version-Label
- [x] `CHANGELOG.md` existiert mit v1.0.0 Eintrag
- [x] `docker compose -f docker-compose.update-test.yml up -d` startet isolierte Umgebung
- [x] `scripts/run-update-tests.sh --all` läuft durch (0 Tests, Exit-Code 0)
- [ ] Pre-Flight-Checks erkennen fehlenden Docker-Daemon (Mock-Test)

---

## Phase 2: Docker-Only Update-Skripte

**Ziel:** KMU-Kunden können ihre Docker-Installation mit einem einzigen Befehl updaten und bei Problemen zurückrollen.

**Voraussetzung:** Phase 1 abgeschlossen.

**Liefergegenstände:**

- [x] `scripts/update-docker.sh`
- [x] `scripts/rollback-docker.sh`
- [x] Wartungsseite (HTML) für API-Gateway
- [x] Ebene-1-Tests: S-01 bis S-11 (Docker-spezifisch)

### Aufgaben

#### 2.1 Update-Skript: `scripts/update-docker.sh`

**Referenz:** UPDATE_STRATEGY Kap. 3.3

```
Ablauf:
1. Pre-Flight Checks (scripts/lib/preflight.sh)
2. Backup erzwingen (scripts/backup.sh --all)
3. Backup-SHA256-Verifizierung
4. Alte Images taggen (:pre-update)
5. Neue Images ziehen (docker compose pull) oder bauen (docker compose build)
6. Graceful Shutdown (10s Grace Period)
7. Neustarten: DB/Redis → Init → Web/Celery → Frontend/Gateway
8. Health Check (/api/health/ + /api/version/)
9. Ergebnis-Ausgabe mit Rollback-Hinweis

Optionen:
  --version <TAG>    Bestimmte Version
  --dry-run          Nur prüfen
  --yes              Keine Bestätigungsabfrage
  --local-build      Lokaler Build statt Pull
```

#### 2.2 Rollback-Skript: `scripts/rollback-docker.sh`

**Referenz:** UPDATE_STRATEGY Kap. 6.1

```
Ablauf:
1. Container stoppen
2. :pre-update Images als :latest taggen
3. DB aus Backup wiederherstellen (scripts/restore.sh)
4. Container starten
5. Health Check

Optionen:
  --backup <PFAD>    Bestimmtes Backup (statt Pre-Update)
  --db-only          Nur DB, keine Images
```

#### 2.3 Wartungsseite

**Referenz:** UPDATE_STRATEGY Kap. 3.4

```
Datei: infra/api-gateway/maintenance.html (neu)
- Statische HTML-Seite (kein JS-Framework nötig)
- Deutsche Sprache
- Geschätzte Dauer anzeigen
- Auto-Refresh alle 30s
```

#### 2.4 Skript-Unit-Tests (Ebene 1 — Docker)

**Referenz:** UPDATE_STRATEGY Kap. 10.3, Tests S-01 bis S-11

```
Datei: scripts/tests/test_update_docker.sh (bats-core) oder
Datei: scripts/tests/test_update_docker.py (pytest + subprocess)

Tests:
- S-01: Docker Daemon nicht verfügbar → Exit 1
- S-02: Speicherplatz < 2 GB → Exit 1
- S-03: docker-compose.yml fehlt → Exit 1
- S-04: Gleiche Version → "Bereits auf Version X"
- S-07: Version aus Container lesen → korrekte SemVer
- S-08: Version aus Image-Label lesen → korrekte SemVer
- S-09: :pre-update Tag gesetzt → Image verfügbar
- S-10: backup.sh wird aufgerufen → Exit-Code durchgereicht
- S-11: Backup-Fehler → Update abgebrochen
```

### Abnahmekriterien Phase 2

- [x] `./scripts/update-docker.sh --dry-run` zeigt Plan ohne Änderungen
- [x] `./scripts/update-docker.sh --yes` führt vollständiges Update durch
- [x] `./scripts/rollback-docker.sh` stellt vorherige Version + DB wieder her
- [x] Wartungsseite wird bei gestopptem Backend angezeigt
- [x] Alle S-Tests (Docker) bestehen: `./scripts/run-update-tests.sh --level 1 --docker-only`

---

## Phase 3: Docker-Only Integrationstests

**Ziel:** Docker-Updates sind durch Migrations-, Komponenten- und E2E-Tests vollständig abgesichert.

**Voraussetzung:** Phase 2 abgeschlossen.

**Liefergegenstände:**

- [x] Ebene 2: Migrations-Tests M-01 bis M-23 (17/17 PASS)
- [x] Ebene 3: Docker-Komponententests D-01 bis D-08 (8/8 PASS)
- [x] Ebene 4: Docker E2E-Tests E2E-D-01 bis E2E-D-05 (5/5 PASS)
- [x] Test-Reporting: JUnit XML + HTML Summary

### Aufgaben

#### 3.1 Migrations-Tests (Ebene 2)

**Referenz:** UPDATE_STRATEGY Kap. 10.4

Technisch: Python-basiert (pytest), läuft gegen die Temp-DB aus `docker-compose.update-test.yml`.

```
Test-Strategie:
1. Temp-DB starten (tmpfs)
2. Altes Schema laden (via manage.py migrate invoice_app 000N)
3. Fixtures laden (standard oder edge)
4. Forward-Migration ausführen
5. Schema + Daten inspizieren (pg_dump --schema-only, SQL-Queries)
6. Rollback testen
7. Temp-DB aufräumen

Tests implementieren:
- M-01 bis M-08 (Forward): Schema-Vollständigkeit, Datenintegrität, Performance, Idempotenz
- M-10 bis M-14 (Backward): Rollback-Korrektheit, Transaktionssicherheit, Ping-Pong
- M-20 bis M-23 (Kompatibilität): Alter Code + neues Schema, migrate --plan Prüfung
```

#### 3.2 Docker-Komponententests (Ebene 3)

**Referenz:** UPDATE_STRATEGY Kap. 10.5.1

```
Pro Test: Eigenen Container-Stack hochfahren, Aktion ausführen, verifizieren, aufräumen.

D-01: Happy Path (update-docker.sh end-to-end)
D-02: Backup existiert + ist verifiziert bevor Stop
D-03: Init-Container läuft migrate erfolgreich
D-04: Health Check nach Update OK
D-05: Graceful Shutdown (HTTP-Request während Stop → 200)
D-06: Volume-Persistenz (pg_data intakt nach Restart)
D-07: Static Files refreshed nach collectstatic
D-08: Celery reconnect nach Redis-Restart
```

#### 3.3 Docker E2E-Tests (Ebene 4)

**Referenz:** UPDATE_STRATEGY Kap. 10.6.1

```
E2E-D-01: Standard-Update (v_old → v_new, 5 Rechnungen bleiben)
E2E-D-02: Update + Rollback (simulierter Fehler → rollback → Daten zurück)
E2E-D-03: Multi-Step (v1.0 → v1.1 → v1.2, kumulative Migrationen)
E2E-D-04: Großer Datenbestand (10k Rechnungen, Dauer messen)
E2E-D-05: Update bei laufendem Celery-Task
```

#### 3.4 Test-Reporting

**Referenz:** UPDATE_STRATEGY Kap. 10.10

```
Datei: scripts/lib/test_reporter.sh (oder Python-Modul)
- JUnit XML: test-artifacts/update-tests/junit.xml
- HTML Summary: test-artifacts/update-tests/report.html
- Log pro Testfall: test-artifacts/update-tests/logs/<TEST-ID>.log
- Summary am Ende (Bestanden/Fehlgeschlagen/Dauer)
```

### Abnahmekriterien Phase 3

- [x] `./scripts/run-update-tests.sh --level 2` → alle M-Tests bestanden (17/17)
- [x] `./scripts/run-update-tests.sh --level 3 --docker-only` → alle D-Tests bestanden (8/8)
- [x] `./scripts/run-update-tests.sh --level 4 --docker-only` → alle E2E-D-Tests bestanden (5/5)
- [x] JUnit XML und HTML Report werden generiert
- [x] Gesamtlauf: `./scripts/run-update-tests.sh --all --docker-only` → 40/40 PASS

---

## Phase 4: K3s Rolling Update-Skripte und Manifeste

**Ziel:** Enterprise-Kunden können ihre K3s-Installation mit Zero-Downtime updaten.

**Voraussetzung:** Phase 1 abgeschlossen.

**Liefergegenstände:**

- [x] `scripts/update-k3s.sh` (erweitert bestehendes `k3s-update-images.sh`)
- [x] Rolling-Update-Strategie in allen Deployments
- [x] PodDisruptionBudgets für django-web und api-gateway
- [x] Migrations-Job-Template
- [x] `revisionHistoryLimit: 5` in Deployments
- [x] Ebene-1-Tests: S-05, S-06, S-12 (K3s-spezifisch)

### Aufgaben

#### 4.1 Update-Skript: `scripts/update-k3s.sh`

**Referenz:** UPDATE_STRATEGY Kap. 4.5

```
Erweitert das bestehende k3s-update-images.sh um:
1. Pre-Flight Checks (Cluster-Health, Nodes Ready)
2. Backup (pg_dump aus Postgres-Pod)
3. Migrations-Job deployen + warten
4. Bei Migration-Fehler: ABBRUCH
5. kubectl apply -k (Rolling Update)
6. Rollout-Status überwachen (Timeout 300s)
7. Post-Update Verification
8. Cleanup (alte Jobs, dangling Images)

Optionen:
  --version <TAG>     Bestimmte Version
  --build-only        Nur Images bauen (kein Deploy)
  --dry-run           Nur Plan zeigen
  --skip-backup       Backup überspringen (Testumgebung)
```

#### 4.2 K8s-Manifeste: Rolling Update-Strategie

**Referenz:** UPDATE_STRATEGY Kap. 4.2

```
Dateien:
  infra/k8s/k3s/manifests/50-deploy-django-web.yaml
  infra/k8s/k3s/manifests/52-deploy-celery-worker.yaml
  infra/k8s/k3s/manifests/60-deploy-api-gateway.yaml
  infra/k8s/k3s/manifests/70-deploy-frontend.yaml (falls vorhanden)

Änderungen je Deployment:
  spec.strategy.type: RollingUpdate
  spec.strategy.rollingUpdate.maxSurge: 1
  spec.strategy.rollingUpdate.maxUnavailable: 0
  spec.minReadySeconds: 10
  spec.revisionHistoryLimit: 5

Ausnahme (Recreate):
  infra/k8s/k3s/manifests/30-deploy-postgres.yaml
  infra/k8s/k3s/manifests/32-deploy-redis.yaml (falls vorhanden)
```

#### 4.3 PodDisruptionBudgets

**Referenz:** UPDATE_STRATEGY Kap. 4.4

```
Neue Dateien:
  infra/k8s/k3s/manifests/53-pdb-django-web.yaml
  infra/k8s/k3s/manifests/63-pdb-api-gateway.yaml

Inhalt:
  spec.minAvailable: 1
  selector.matchLabels: app: <service>
```

#### 4.4 Migrations-Job-Template

**Referenz:** UPDATE_STRATEGY Kap. 4.3

```
Neue Datei: infra/k8s/k3s/manifests/41-job-django-migrate-template.yaml
- wait-for-db InitContainer
- manage.py migrate --noinput
- backoffLimit: 3
- activeDeadlineSeconds: 300
- Image-Tag wird per Kustomize überschrieben
```

#### 4.5 Skript-Unit-Tests (Ebene 1 — K3s)

**Referenz:** UPDATE_STRATEGY Kap. 10.3

```
Tests:
- S-05: Cluster nicht erreichbar → Exit 1
- S-06: Node NotReady → Exit 1 + Node-Liste
- S-12: kustomization.yaml newTag korrekt ersetzt
```

### Abnahmekriterien Phase 4

- [x] `./scripts/update-k3s.sh --dry-run` zeigt Update-Plan
- [x] Deployments haben explizite `strategy.rollingUpdate`
- [x] PDBs deployed: `kubectl get pdb -n erechnung`
- [x] Migrations-Job Template einsatzbereit
- [x] `./scripts/run-update-tests.sh --level 1 --k3s-only` → S-05, S-06, S-12 bestanden

---

## Phase 5: K3s Integrationstests

**Ziel:** K3s-Updates sind durch Komponenten- und E2E-Tests abgesichert.

**Voraussetzung:** Phase 4 abgeschlossen.

**Liefergegenstände:**

- [x] K3s-Test-Namespace (`erechnung-update-test`)
- [x] Ebene 3: K3s-Komponententests K-01 bis K-08
- [x] Ebene 4: K3s E2E-Tests E2E-K-01 bis E2E-K-05

### Aufgaben

#### 5.1 K3s-Test-Namespace

**Referenz:** UPDATE_STRATEGY Kap. 10.2

```
Neue Datei: infra/k8s/k3s/test/namespace-update-test.yaml
- Eigener Namespace mit Pod Security Standards
- Eigene PVCs (emptyDir oder tmpfs-backed)
- Eigene ConfigMaps/Secrets mit Test-Credentials
- Cleanup-Script: kubectl delete namespace erechnung-update-test
```

#### 5.2 K3s-Komponententests (Ebene 3)

**Referenz:** UPDATE_STRATEGY Kap. 10.5.2

```
K-01: Rolling Update Happy Path (kein 5xx während Rollout)
K-02: Migrations-Job → completions=1 → dann erst Rollout
K-03: Rollout Status = Available nach Update
K-04: PDB respektiert bei Node Drain
K-05: Readiness Probe blockiert Traffic an startende Pods
K-06: 0% Request-Fehlerrate während Rollout (100 Requests)
K-07: ConfigMap-Änderung → neue Config aktiv
K-08: PVC intakt nach Pod-Restart
```

Implementierung: Shell-Skripte mit kubectl + curl, oder Python mit kubernetes-Client.

#### 5.3 K3s E2E-Tests (Ebene 4)

**Referenz:** UPDATE_STRATEGY Kap. 10.6.2

```
E2E-K-01: Zero-Downtime (Lastgenerator während Update, 0 Fehler)
E2E-K-02: Auto-Rollback bei Health-Fehler (defektes Image → Pods bleiben alt)
E2E-K-03: Manueller Rollback (rollout undo → alte Version aktiv)
E2E-K-04: Migration-Job-Fehler blockiert Rollout
E2E-K-05: Paralleler Traffic (10 Clients, Sessions bleiben valid)
```

Lastgenerator: `hey`, `vegeta`, oder einfaches `curl`-Loop-Skript.

### Abnahmekriterien Phase 5

- [x] Test-Namespace wird automatisch erstellt und bereinigt
- [x] `./scripts/run-update-tests.sh --level 3 --k3s-only` → alle K-Tests bestanden (8/8)
- [x] `./scripts/run-update-tests.sh --level 4 --k3s-only` → alle E2E-K-Tests bestanden (5/5)
- [x] Zero-Downtime verifiziert: 0 fehlgeschlagene Requests in E2E-K-01

---

## Phase 6: Edge-Case-Tests und Härtung

**Ziel:** Grenzfälle und Fehlersituationen sind systematisch abgesichert. Die Testsuite erkennt reale Probleme zuverlässig.

**Voraussetzung:** Phase 3 und Phase 5 abgeschlossen.

**Liefergegenstände:**

- [x] Edge-Case-Tests: EC-01 bis EC-24
- [x] Testsuite-Selbstvalidierung (Negativ-Tests, Mutationstests)
- [x] `stress`- und `edge`-Fixture-Sets

### Aufgaben

#### 6.1 Infrastruktur-Edge-Cases (EC-01 bis EC-07)

**Referenz:** UPDATE_STRATEGY Kap. 10.7.1

```
EC-01: Netzwerk-Abbruch während Image-Pull (iptables-Simulation)
EC-02: Speicherplatz erschöpft (tmpfs mit 100 MB)
EC-03: Kill -9 während Migration (docker kill → Transaktions-Rollback)
EC-04: Paralleles Update (Lock-Mechanismus prüfen)
EC-05: Container-OOM während Migration (Memory-Limit 64M)
EC-06: DNS-Ausfall (K3s: CoreDNS-Pod löschen)
EC-07: Registry nicht erreichbar (K3s: Port 5000 stoppen)
```

#### 6.2 Daten-Edge-Cases (EC-10 bis EC-16)

**Referenz:** UPDATE_STRATEGY Kap. 10.7.2

```
EC-10: Leere DB → Update (kein Division-by-Zero)
EC-11: DB mit manuellen Constraints (Extra-Index)
EC-12: Korruptes Backup (SHA256-Mismatch → Abbruch)
EC-13: Kumulative Migration über mehrere Stufen
EC-14: Sonderzeichen in Media-Dateien
EC-15: Concurrent Write während Migration
EC-16: GoBD-gesperrte Rechnungen unverändert
```

#### 6.3 Versions-Edge-Cases (EC-20 bis EC-24)

**Referenz:** UPDATE_STRATEGY Kap. 10.7.3

```
EC-20: Downgrade-Versuch → Fehlermeldung
EC-21: MAJOR-Sprung ohne Zwischenschritt → Warnung
EC-22: Gleiche Version → No-Op
EC-23: Unbekannte Version → Fehlermeldung
EC-24: pyproject.toml nicht lesbar → Fallback auf Image-Label
```

#### 6.4 Stress- und Edge-Fixtures

**Referenz:** UPDATE_STRATEGY Kap. 10.9

```
Datei: test-artifacts/update-tests/fixtures/stress.json
  → 10.000 Rechnungen, 500 Partner, 2.000 Audit-Einträge

Datei: test-artifacts/update-tests/fixtures/edge.json
  → Sonderzeichen, max. Feldlängen, alle Steuer-Kategorien, GoBD-Locks

Erzeugung: Management Command generate_test_data --preset stress|edge
```

#### 6.5 Testsuite-Selbstvalidierung

**Referenz:** UPDATE_STRATEGY Kap. 10.11

```
Validierungsschritte:
1. Negativ-Test: Absichtlich fehlerhaftes Update → Tests müssen fehlschlagen
2. Mutationstest: Migration-Datei manipulieren (Feld umbenennen) → M-Tests schlagen fehl
3. False-Positive-Check: Korrektes Update → kein Test schlägt fälschlicherweise fehl
4. Performance-Baseline: stress-Fixture auf Referenz-Hardware → Zeitlimits kalibrieren
```

### Abnahmekriterien Phase 6

- [x] `./scripts/run-update-tests.sh --edge-cases` → alle EC-Tests bestanden
- [x] Negativ-Tests: Absichtlich fehlerhaftes Update wird erkannt (kein False Negative)
- [x] Mutationstests: Manipulierte Migration wird erkannt (kein False Negative)
- [x] Stress-Fixtures: Migration mit 10.000 Rechnungen < 60s
- [x] Gesamtlauf: `./scripts/run-update-tests.sh --all` → alle Tests bestanden

---

## Phase 7: CI/CD-Integration und Endanwender-Dokumentation

**Ziel:** Tests laufen automatisch bei jedem Release. Endanwender haben eine verständliche Update-Anleitung.

**Voraussetzung:** Phase 6 abgeschlossen.

**Liefergegenstände:**

- [x] GitHub Actions Workflow: `update-integration-tests.yml`
- [x] Update-Anleitung in `docs/USER_MANUAL.md`
- [x] Database-Schema-Version-Check beim Django-Start
- [x] UPDATE_STRATEGY.md Status auf „Implementiert" setzen

### Aufgaben

#### 7.1 GitHub Actions Workflow

**Referenz:** UPDATE_STRATEGY Kap. 10.8.3

```
Datei: .github/workflows/update-integration-tests.yml
Trigger:
  - Push auf Tags v*.*.*
  - workflow_dispatch (mit old_version + new_version Input)
Jobs:
  - Checkout + Docker Build
  - ./scripts/run-update-tests.sh --all --docker-only
  - Artefakte: JUnit XML + HTML Report + Logs
```

K3s-Tests laufen nicht in GitHub Actions (brauchen echten Cluster), aber werden als required Schritt im `update-k3s.sh` Skript ausgeführt.

#### 7.2 Update-Anleitung im User Manual

**Referenz:** UPDATE_STRATEGY Kap. 11.5

```
Neues Kapitel in docs/USER_MANUAL.md:
- "Installation aktualisieren" (Deutsch)
- Docker-Only: Schritt-für-Schritt mit einem Befehl
- K3s: Schritt-für-Schritt + Voraussetzungen
- Fehlerbehebung: Häufige Probleme + Rollback-Anleitung
- Bildschirmfotos der Wartungsseite
```

#### 7.3 Database-Schema-Version-Check

**Referenz:** UPDATE_STRATEGY Kap. 11.3

```
Datei: project_root/invoice_app/apps.py (ready-Hook)
- Beim Django-Start prüfen: Gibt es unangewandte Migrationen?
- Falls ja: WARNING im Log, nicht Startup blockieren
- Optional: /api/health/ gibt "degraded" zurück wenn Migrationen fehlen
```

#### 7.4 Abschluss

```
- UPDATE_STRATEGY.md: Status → "Implementiert"
- PROGRESS_PROTOCOL.md: Meilenstein dokumentieren
- TODO_2026.md: Update-Strategie als erledigt markieren
```

### Abnahmekriterien Phase 7

- [x] GitHub Actions: Workflow wird bei Tag-Push getriggert und Tests laufen erfolgreich
- [x] User Manual enthält verständliche Update-Anleitung
- [x] Django-Start zeigt Warnung bei fehlenden Migrationen
- [x] Komplett-Durchlauf: Release bauen → Tests → Update → Verifizierung → alles grün

---

## Zusammenfassung: Liefergegenstände je Phase

| Phase | Neue Dateien | Geänderte Dateien | Tests |
|---|---|---|---|
| **1** | version_view.py, CHANGELOG.md, docker-compose.update-test.yml, lib/preflight.sh, run-update-tests.sh, Fixtures | Dockerfile, urls.py | Version-Endpoint Unit-Tests |
| **2** | update-docker.sh, rollback-docker.sh, maintenance.html | — | S-01 bis S-11 |
| **3** | test_migrations.py, test_docker_components.py, test_docker_e2e.py, lib/test_reporter.sh | run-update-tests.sh | M-01–M-23, D-01–D-08, E2E-D-01–05 |
| **4** | update-k3s.sh, 53-pdb-*.yaml, 63-pdb-*.yaml, 41-job-migrate-template.yaml | 50/52/60/70-deploy-*.yaml, kustomization.yaml | S-05, S-06, S-12 |
| **5** | namespace-update-test.yaml, test_k3s_components.sh, test_k3s_e2e.sh | run-update-tests.sh | K-01–K-08, E2E-K-01–05 |
| **6** | test_edge_cases.py, stress.json, edge.json | — | EC-01–EC-24, Mutationstests |
| **7** | update-integration-tests.yml | USER_MANUAL.md, apps.py, UPDATE_STRATEGY.md, TODO_2026.md | CI-Pipeline |

**Gesamtzahl Testfälle: ~85** (12 Skript + 23 Migration + 16 Komponenten + 10 E2E + 24 Edge-Cases)

---

## Reihenfolge-Empfehlung

```
Woche 1-2:  Phase 1 (Fundament)
Woche 3-4:  Phase 2 (Docker-Update-Skripte)
Woche 5-7:  Phase 3 (Docker-Tests)          ← parallel möglich mit Phase 4
Woche 5-6:  Phase 4 (K3s-Update-Skripte)    ← parallel möglich mit Phase 3
Woche 7-9:  Phase 5 (K3s-Tests)
Woche 10-11: Phase 6 (Edge-Cases + Härtung)
Woche 12:   Phase 7 (CI/CD + Doku)
```

Phasen 2+3 (Docker) und 4+5 (K3s) können von verschiedenen Personen parallel bearbeitet werden, da sie nur Phase 1 als gemeinsame Basis haben.
