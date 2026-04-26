# Dependency Update Test-Plan

**Branch:** `test-dependencies` (basierend auf PR "chore: update Python dependencies")
**Datum:** 7. November 2025

## 📦 Updates im PR

Insgesamt **24 Package-Updates**:

### Major/Minor Updates (kritischer):
- `astroid`: 3.3.11 → **4.0.1** ⚠️ (Major Update)
- `isort`: 6.1.0 → **7.0.0** ⚠️ (Major Update)

### Patch Updates (weniger kritisch):
- `charset-normalizer`: 3.4.3 → 3.4.4
- `coverage`: 7.10.7 → 7.11.0
- `django-allauth`: 65.12.0 → 65.12.1
- `faker`: 37.8.0 → 37.12.0
- `filelock`: 3.19.1 → 3.20.0
- `idna`: 3.10 → 3.11
- `iniconfig`: 2.1.0 → 2.3.0
- `msgpack`: 1.1.1 → 1.1.2
- ... und weitere

## ✅ Test-Checkliste

### 1. Build & Installation
- [ ] Docker-Build erfolgreich
- [ ] Alle Packages installierbar
- [ ] Keine Dependency-Konflikte

### 2. Tests
```bash
# Alle Tests ausführen
docker compose exec web python project_root/manage.py test invoice_app.tests

# Erwartung: Gleiche Anzahl bestehender Tests wie auf main
# - 242 Tests sollten bestehen
# - 10 bekannte Fehler (PDF-bezogen, nicht dependencies-related)
```

### 3. Linting (wegen isort 7.0.0 Major Update)
```bash
# Pre-commit hooks testen
git commit --allow-empty -m "test: verify linting with new isort"

# Erwartung: Keine neuen Linting-Fehler
```

### 4. Import-Tests (wegen astroid 4.0.1 Major Update)
```bash
# Django Check
docker compose exec web python project_root/manage.py check

# Python Import Tests
docker compose exec web python -c "
from invoice_app.models import Invoice, Company, Customer
from invoice_app.services import InvoiceService
from invoice_app.api.rest_views import InvoiceViewSet
print('✅ All imports successful')
"
```

### 5. Development Workflow
```bash
# Shell funktioniert
docker compose exec web python project_root/manage.py shell

# Migrations funktionieren
docker compose exec web python project_root/manage.py showmigrations

# Swagger UI funktioniert
# Öffne: http://localhost:8000/api/docs/
```

### 6. Kritische Features
- [ ] PDF-Generierung (reportlab, pypdf)
- [ ] XML-Validierung (lxml, Schematron)
- [ ] API-Endpoints (DRF, drf-yasg)
- [ ] JWT-Auth (djangorestframework-simplejwt)
- [ ] Celery-Tasks

## 🚨 Bekannte Risiken

### astroid 4.0.1 (pylint-Abhängigkeit)
**Risiko:** Linting-Regeln könnten sich ändern
**Mitigation:** Pre-commit hooks testen

### isort 7.0.0
**Risiko:** Import-Sortierung könnte sich ändern
**Mitigation:**
- Prüfen ob `.isort.cfg` / `pyproject.toml` angepasst werden muss
- Pre-commit hooks testen

## ✅ Erfolgs-Kriterien

1. **Docker-Build:** Erfolgreich ohne Errors
2. **Tests:** Gleiche Test-Ergebnisse wie main (242 passed, 10 known errors)
3. **Linting:** Keine neuen Warnungen/Fehler
4. **Django Check:** Keine System-Check-Fehler
5. **API:** Swagger UI lädt erfolgreich
6. **Development:** Shell, Migrations, Commands funktionieren

## 🔄 Rollback-Plan

Falls Probleme auftreten:

```bash
# 1. Zurück zu main
git checkout main

# 2. Container mit alten Dependencies neu bauen
docker compose down
docker compose build --no-cache
docker compose up -d

# 3. Test-Branch löschen
git branch -D test-dependencies

# 4. PR auf GitHub mit Kommentar ablehnen
```

## 📝 Nach erfolgreichem Test

```bash
# 1. Zurück zu main
git checkout main

# 2. PR auf GitHub mergen
# (via GitHub Web-Interface)

# 3. Aktualisierte main pullen
git pull github main

# 4. Container neu bauen mit neuen Dependencies
docker compose down
docker compose build --no-cache
docker compose up -d

# 5. Test-Branch aufräumen
git branch -D test-dependencies
```

---

**Maintained by:** Development Team
**Status:** ⏳ In Bearbeitung
