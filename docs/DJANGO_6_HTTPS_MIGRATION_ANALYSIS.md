# Django 6.0 HTTPS Migration Analysis (Issue #9)

**Datum:** 7. November 2025
**Status:** In Bearbeitung
**Branch:** `feature/issue-9-django-6-https-preparation`

## 🎯 Zusammenfassung

Django 6.0 wird das Standard-Schema für URLs von `http` auf `https` ändern. Diese Analyse dokumentiert die notwendigen Anpassungen und potenzielle Probleme für die eRechnung Django App.

---

## ⚠️ Aktuelle Warning

```
RemovedInDjango60Warning: The default scheme will be changed from 'http' to 'https'
in Django 6.0. Pass the forms.URLField.assume_scheme argument to silence this warning,
or set the FORMS_URLFIELD_ASSUME_HTTPS transitional setting to True to opt into using
'https' as the new default scheme.
```

**Quelle:** `/usr/local/lib/python3.12/site-packages/django/db/models/fields/__init__.py:1142`

---

## 🔍 Betroffene Bereiche

### 1. **URLField in Models**
- **Risiko:** Hoch für externe URLs
- **Betroffene Dateien:**
  - `invoice_app/models/*.py` (falls URLFields vorhanden)

### 2. **URL-Generierung in Views/Templates**
- **Risiko:** Mittel
- **Betroffene Bereiche:**
  - `build_absolute_uri()` Aufrufe
  - Template `{% url %}` Tags mit absoluten URLs
  - API-Responses mit URLs

### 3. **API Gateway & Reverse Proxy**
- **Risiko:** Hoch für Production
- **Betroffene Dateien:**
  - `api-gateway/nginx.conf`
  - `docker-compose.production.yml`

### 4. **Test-Suite**
- **Risiko:** Mittel
- **Impact:** Lokale Tests verwenden HTTP

### 5. **Security Settings**
- **Risiko:** Hoch für Production
- **Betroffene Settings:**
  - `SECURE_PROXY_SSL_HEADER`
  - `SECURE_SSL_REDIRECT`
  - `SESSION_COOKIE_SECURE`
  - `CSRF_COOKIE_SECURE`

---

## 🛠️ Empfohlene Lösungen

### Sofortmaßnahme (Transitional Setting)

**settings.py:**
```python
# Django 6.0 Compatibility: Prepare for HTTPS default scheme
# Set to False to maintain current HTTP behavior for development
# Set to True to opt into HTTPS default (recommended for production)
FORMS_URLFIELD_ASSUME_HTTPS = False  # Development default
```

### Development vs. Production Split

#### **Option A: Environment-basierte Konfiguration (Empfohlen)**

```python
# settings.py
import os

# Django 6.0 HTTPS Preparation
IS_PRODUCTION = os.getenv("DJANGO_ENV", "development") == "production"
FORMS_URLFIELD_ASSUME_HTTPS = IS_PRODUCTION

# Security settings for HTTPS
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 Jahr
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    # Development: Keep HTTP for local testing
    FORMS_URLFIELD_ASSUME_HTTPS = False
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
```

#### **Option B: Separate Settings Files**

```python
# settings_production.py
from invoice_project.settings import *

FORMS_URLFIELD_ASSUME_HTTPS = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## 🚨 Potenzielle Probleme bei lokaler HTTP-Entwicklung

### Problem 1: Cookie-Sicherheit
**Symptom:** Session/CSRF Cookies funktionieren nicht
**Ursache:** `SESSION_COOKIE_SECURE = True` erfordert HTTPS
**Lösung:** Development-Settings mit `False` verwenden

### Problem 2: Redirects
**Symptom:** Endlose Redirect-Loops
**Ursache:** `SECURE_SSL_REDIRECT = True` ohne HTTPS-Proxy
**Lösung:** In Development `False` setzen

### Problem 3: URL-Generierung in Tests
**Symptom:** Tests erwarten `http://`, bekommen aber `https://`
**Ursache:** `build_absolute_uri()` verwendet Request-Schema
**Lösung:** Test-Client mit explizitem Schema konfigurieren

```python
# In Tests
response = self.client.get('/api/endpoint/', secure=False)  # HTTP
response = self.client.get('/api/endpoint/', secure=True)   # HTTPS
```

### Problem 4: API Gateway Header-Forwarding
**Symptom:** Django erkennt HTTPS nicht, obwohl Gateway HTTPS terminiert
**Ursache:** Fehlende `X-Forwarded-Proto` Header
**Lösung:** nginx.conf anpassen

```nginx
# api-gateway/nginx.conf
location / {
    proxy_pass http://web:8000;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
}
```

### Problem 5: Health Endpoints müssen HTTP-kompatibel bleiben
**Symptom:** Load Balancer Health Checks schlagen fehl
**Ursache:** Health Endpoints erfordern HTTPS
**Lösung:** Health Endpoints von SSL-Redirect ausschließen

```python
# views.py
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # Health checks müssen ohne CSRF funktionieren
def health_check(request):
    return JsonResponse({"status": "healthy"})
```

---

## 📋 Änderungen Checkliste

### Phase 1: Transitional Setting (Risikoarm)
- [ ] `FORMS_URLFIELD_ASSUME_HTTPS` Setting hinzufügen
- [ ] Environment-Variable `DJANGO_ENV` einführen
- [ ] `.env.example` aktualisieren
- [ ] Tests ausführen (sicherstellen, dass alles funktioniert)

### Phase 2: Nginx Configuration (Production-relevant)
- [ ] `api-gateway/nginx.conf` prüfen auf `X-Forwarded-Proto`
- [ ] HTTPS-Termination in Gateway konfigurieren
- [ ] Health Endpoint HTTP-Zugriff sicherstellen

### Phase 3: Security Settings (Production-only)
- [ ] Production-spezifische Settings implementieren
- [ ] `docker-compose.production.yml` Environment-Variablen prüfen
- [ ] HSTS-Header aktivieren (nach gründlichem Test)

### Phase 4: Testing
- [ ] Lokale Tests mit HTTP durchführen
- [ ] Production-ähnliche Tests mit HTTPS
- [ ] Health Endpoint Tests (HTTP + HTTPS)
- [ ] API Gateway Integration Tests

### Phase 5: Dokumentation
- [ ] README.md aktualisieren (HTTPS-Konfiguration)
- [ ] CONTRIBUTING.md erweitern (Development HTTPS-Setup optional)
- [ ] DEVELOPMENT_CONTEXT.md aktualisieren

---

## 🔬 Test-Strategie

### Lokale Development (HTTP)
```bash
# .env
DJANGO_ENV=development

# Tests sollten weiterhin funktionieren
docker compose exec web python project_root/manage.py test
```

### Production-Simulation (HTTPS)
```bash
# .env.production
DJANGO_ENV=production

# Mit HTTPS-fähigem Reverse Proxy testen
docker compose -f docker-compose.yml -f docker-compose.production.yml up
```

### Compatibility Tests
```bash
# Alle Warnings anzeigen
docker compose exec web python -W all project_root/manage.py test

# Spezifisch nach Django 6.0 Warnings suchen
docker compose exec web python -W all project_root/manage.py test 2>&1 | grep "RemovedInDjango60"
```

---

## 📖 Weiterführende Ressourcen

- [Django 6.0 Release Notes](https://docs.djangoproject.com/en/stable/releases/6.0/)
- [Django Security Settings](https://docs.djangoproject.com/en/5.1/topics/security/)
- [HTTPS Deployment Checklist](https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/)
- [nginx HTTPS Proxy Configuration](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)

---

## 🎯 Nächste Schritte

1. **Implementierung:** Phase 1 (Transitional Setting) umsetzen
2. **Testing:** Sicherstellen, dass lokale HTTP-Tests weiterhin funktionieren
3. **Review:** nginx.conf auf korrekte Header-Forwarding prüfen
4. **Documentation:** Settings-Dokumentation erweitern
5. **Monitoring:** Nach Django 6.0 Release Migration durchführen

---

**Maintained by:** Development Team
**Last Updated:** 2025-11-07
