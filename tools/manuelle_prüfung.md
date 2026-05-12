# Mustang-CLI — Manuelle Rechnungsprüfung

**Voraussetzung:** Java 11+ auf dem Host (vorhanden: OpenJDK 21)
**JAR + Skript:** dieses `tools/`-Verzeichnis

---

## Verwendung

### 1. Einzelne PDF-Rechnung prüfen

```bash
./tools/validate_invoice_mustang.sh project_root/media/invoices/RE-2026-0042.pdf
```

### 2. Einzelne XML-Datei prüfen (extrahierte Factur-X XML)

```bash
./tools/validate_invoice_mustang.sh /tmp/factur-x.xml
```

### 3. Mehrere Dateien auf einmal

```bash
./tools/validate_invoice_mustang.sh RE-001.pdf RE-002.pdf RE-003.pdf
```

### 4. Alle PDFs in `media/invoices/` prüfen (kein Argument)

```bash
./tools/validate_invoice_mustang.sh
```

### 5. Direktaufruf ohne Skript (maximale Kontrolle)

```bash
java -jar tools/Mustang-CLI-2.22.0.jar --action validate --source RE-2026-0042.pdf
```

---

## Ausgabe verstehen

| Ergebnis  | Bedeutung                                          |
|-----------|----------------------------------------------------|
| `valid`   | Rechnung ist ZUGFeRD/Factur-X konform              |
| `invalid` | Strukturfehler in XML oder PDF/A-Verletzung        |
| Notices   | Hinweise (kein Fehler, im Skript mit `--no-notices` unterdrückt) |

Exit-Code `0` = alle geprüften Dateien gültig, `1` = mindestens eine ungültig.

---

## Weitere JAR-Optionen

```bash
# Hilfe anzeigen
java -jar tools/Mustang-CLI-2.22.0.jar --help

# XML aus PDF extrahieren
java -jar tools/Mustang-CLI-2.22.0.jar --action extract --source RE.pdf --out /tmp/extracted.xml

# Konformitätslevel angeben (EN16931, XRechnung, ...)
java -jar tools/Mustang-CLI-2.22.0.jar --action validate --source RE.pdf --format EN16931
```

---

## Hinweise

- Das JAR und das Skript liegen in `tools/` und sind **nicht** in den Docker-Build eingebunden.
- Ausschließlich für Host-seitige Spot-Checks — kein Bestandteil der Applikationslogik.
- Mustang-Projektseite: <https://www.mustangproject.org>
- Aktuelle JAR-Version: **2.22.0**
