## E2E Test Problem: Timeout beim Warten auf Frontend

### Problem
Das ursprüngliche Timeout-Problem im Fragment:
```bash
echo "⏳ Waiting for Frontend..."
timeout 60 bash -c 'until docker compose exec -T frontend-e2e python3 -c "import urllib.request; urllib.request.urlopen(\"http://frontend-e2e:5173\")" 2>/dev/null; do echo "Waiting for Frontend..."; sleep 3; done'
```

### Ursachen
1. **Port-Konflikt**: E2E-Frontend wurde automatisch auf Port 5174 gemappt, weil 5173 bereits vom normalen Frontend belegt war
2. **Falsche URL**: Das Script wartete auf `http://frontend-e2e:5173`, aber der Container war auf Port 5174 erreichbar
3. **Host vs. Container**: Ursprünglicher Ansuch versuchte vom Host aus zu prüfen statt im Container

### Lösung ✅

**1. Container-Only Approach**
- Alle Tests laufen NUR im Container
- NICHTS wird auf dem Host installiert (kein Playwright, keine Browser)

**2. Dedicated Scripts**
- `debug_e2e.sh` - Diagnostiziert Frontend-Container-Status
- `wait_for_frontend_e2e.sh` - Wartet auf Vite (Container-intern auf Port 5173)
- `run_e2e_container.sh` - Vollautomatischer Test-Run

**3. Korrekte Port-Konfiguration in docker-compose.e2e.yml**
```yaml
ports:
  - "5174:5173"  # Host:5174 -> Container:5173 (kein Konflikt)
  - "9323:9323"  # Playwright HTML Report
```

**4. Container-interne Checks**
```bash
# Prüft IM Container auf localhost:5173
docker compose -f docker-compose.e2e.yml exec -T frontend-e2e \
  curl -f -s http://localhost:5173
```

### Tests ausführen

**Empfohlen (vollautomatisch):**
```bash
./run_e2e_container.sh
```

**Manuell:**
```bash
# 1. Container starten
docker compose -f docker-compose.e2e.yml up -d frontend-e2e

# 2. Warten bis bereit
./wait_for_frontend_e2e.sh

# 3. Tests ausführen
docker compose -f docker-compose.e2e.yml exec frontend-e2e npm run test:e2e
```

### Ergebnis
✅ Frontend wird korrekt erkannt (intern Port 5173)
✅ Tests laufen erfolgreich im Container
✅ 77+ Tests werden ausgeführt
✅ Kein Port-Konflikt mehr

### Dateien
- [E2E_TESTING.md](E2E_TESTING.md) - Vollständige Dokumentation
- [docker-compose.e2e.yml](docker-compose.e2e.yml) - E2E Container-Setup
- [run_e2e_container.sh](run_e2e_container.sh) - Haupt-Test-Script
- [wait_for_frontend_e2e.sh](wait_for_frontend_e2e.sh) - Health-Check
- [debug_e2e.sh](debug_e2e.sh) - Debugging-Tool
