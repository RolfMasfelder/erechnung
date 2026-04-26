# Fehler-Katalog (Error Catalog)

> Einheitliches Fehlerformat für die eRechnung REST API.
> Alle Fehlerantworten folgen diesem Schema:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Benutzerfreundliche Fehlerbeschreibung.",
    "details": { ... }
  }
}
```

- **code**: Maschinenlesbarer Fehlercode (UPPER_SNAKE_CASE)
- **message**: Menschenlesbare Beschreibung (deutsch)
- **details**: Optional — nur bei Validierungsfehlern (Feld → Fehlerliste)

---

## Validierungsfehler (400 Bad Request)

| Code | Beschreibung | Auslöser |
|------|-------------|----------|
| `VALIDATION_ERROR` | DRF-Serializer-Validierung fehlgeschlagen | Ungültige Daten bei POST/PUT/PATCH |
| `INVALID_INPUT` | Allgemeine ungültige Eingabe | Basisklasse für 400-Fehler |
| `INVALID_DATE_FORMAT` | Datumsformat ungültig (erwartet: YYYY-MM-DD) | `on_date` Parameter bei Tax-Rates |
| `INVALID_QUANTITY` | Mengenwert ungültig oder fehlend | `update_stock` ohne/mit ungültiger Menge |
| `INVALID_OPERATION` | Operation nicht erlaubt | `update_stock` mit unbekannter Operation |
| `IMPORT_DATA_ERROR` | Import-Daten ungültig | Bulk-Import mit fehlerhaften Zeilen |

## Geschäftslogik-Fehler

| Code | HTTP | Beschreibung | Auslöser |
|------|------|-------------|----------|
| `BUSINESS_LOGIC_ERROR` | 409 | Allgemeine Geschäftsregelverletzung | Basisklasse |
| `INVENTORY_TRACKING_DISABLED` | 400 | Bestandsverfolgung nicht aktiviert | `update_stock` auf Produkt ohne Tracking |
| `INVOICE_STATUS_ERROR` | 409 | Status erlaubt Aktion nicht | z.B. Rechnung stornieren die bereits bezahlt ist |

## Berechtigungsfehler (403 Forbidden)

| Code | Beschreibung | Auslöser |
|------|-------------|----------|
| `PERMISSION_DENIED` | Keine Berechtigung für die Aktion | `cleanup_expired` ohne `delete_auditlog` Permission |
| `NOT_AUTHENTICATED` | Nicht authentifiziert | Request ohne gültiges JWT-Token |

## Datei-/Generierungsfehler (500 Internal Server Error)

| Code | Beschreibung | Auslöser |
|------|-------------|----------|
| `PDF_GENERATION_FAILED` | PDF-Generierung fehlgeschlagen | `generate_pdf`, `download_pdf` Auto-Generierung |
| `XML_GENERATION_FAILED` | XML-Generierung fehlgeschlagen | `download_xml` Auto-Generierung |
| `FILE_SERVING_FAILED` | Datei konnte nicht bereitgestellt werden | PDF/XML-Datei nicht lesbar |

## Infrastruktur-Fehler

| Code | HTTP | Beschreibung | Auslöser |
|------|------|-------------|----------|
| `SERVICE_UNAVAILABLE` | 503 | Service vorübergehend nicht verfügbar | Datenbank-Fehler bei Dashboard-Statistiken |
| `INTERNAL_SERVER_ERROR` | 500 | Unerwarteter interner Fehler | Unbehandelte Exceptions (ohne Details-Leak) |

## Standard-HTTP-Fehler

| Code | HTTP | Beschreibung |
|------|------|-------------|
| `NOT_FOUND` | 404 | Ressource nicht gefunden |
| `METHOD_NOT_ALLOWED` | 405 | HTTP-Methode nicht erlaubt |
| `NOT_ACCEPTABLE` | 406 | Content-Type nicht akzeptiert |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Medientyp nicht unterstützt |
| `THROTTLED` | 429 | Rate-Limit überschritten |

---

## Implementierung

- **Exception-Klassen**: `invoice_app/api/exceptions.py`
- **Globaler Handler**: `invoice_app/api/exception_handlers.py`
- **Registrierung**: `settings.py` → `REST_FRAMEWORK["EXCEPTION_HANDLER"]`
- **Tests**: `invoice_app/tests/test_exception_handler.py` (32 Tests)

## Sicherheitshinweis

Bei **500-Fehlern** werden **keine internen Details** (Stacktraces, Exception-Messages)
an den Client zurückgegeben. Interne Details werden nur ins Server-Log geschrieben.
