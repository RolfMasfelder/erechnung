# ✅ Checkliste: Update-Workflow mit pip-tools

1. **Aktuelle Umgebung sichern**
   ```bash
   pip freeze > requirements.txt
   ```

2. **Top-Level-Dependencies pflegen**
   - `requirements.in` enthält nur deine Hauptpakete (z. B. `Django`, `psycopg2`, `requests`).

3. **Lockfile erzeugen / aktualisieren**
   ```bash
   pip-compile requirements.in
   ```
   - erstellt/aktualisiert `requirements.txt` mit **eingefrorenen Versionen**.
   - Für Updates:
     ```bash
     pip-compile --upgrade requirements.in
     ```

4. **Neue Test-Umgebung anlegen**
   ```bash
   python -m venv venv-test
   source venv-test/bin/activate
   pip install -r requirements.txt
   ```

5. **Testen**
   - Django starten, Tests laufen lassen, ggf. Datenbank prüfen.

6. **Entscheidung**
   - Läuft alles → alte venv ersetzen (oder `pip-sync` nutzen).
   - Läuft nicht → zurück zum alten `requirements.txt`.
