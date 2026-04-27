# ADR 024: Pessimistisches Bearbeitungs-Lock für konkurrierende Zugriffe

## Status

Accepted — 27. April 2026

**Implementierungsstand:** Vollständig umgesetzt in `Invoice`-Modell, `InvoiceViewSet`, Serializer und Migrations `0011_add_edit_lock_fields`.

## Kontext

Das System ist für mehrere gleichzeitig arbeitende Benutzer ausgelegt. Mehrere Mitarbeiter können dieselbe Aufgabe haben (z.B. „DRAFT-Rechnungen bearbeiten"). Ohne Koordinationsmechanismus würden sie sich auf denselben Datensatz stürzen — entweder mit stiller Last-Write-Wins-Überschreibung oder mit HTTP 409-Fehlern (Optimistic Locking), die den Benutzer zur manuellen Konfliktlösung zwingen.

## Entscheidung

**Pessimistisches Bearbeitungs-Lock auf Anwendungsebene** (Checkout/Checkin-Muster):

- Beim Öffnen eines Datensatzes zum Bearbeiten ruft das Frontend `POST /invoices/{id}/acquire_edit_lock/` auf.
- Der erste Aufrufer erhält den Lock (`editing_by`, `editing_since` werden gesetzt).
- Alle weiteren Aufrufer erhalten `HTTP 423 Locked` mit dem Namen des aktuellen Lock-Inhabers.
- Solange das Formular offen ist, sendet das Frontend alle 60 Sekunden einen Heartbeat (`POST .../refresh_edit_lock/`), um den Lock zu verlängern.
- Beim Speichern oder Abbrechen ruft das Frontend `POST .../release_edit_lock/` auf.
- Locks laufen automatisch nach `INVOICE_EDIT_LOCK_TIMEOUT_MINUTES` (Standard: 30 Min.) ab, falls der Benutzer den Browser schließt oder die Session abbricht.
- `PATCH`/`PUT`-Anfragen ohne vorherigen Lock prüfen ebenfalls auf fremden Lock und liefern ggf. `HTTP 423`.

## Warum nicht Optimistic Locking (If-Match / ETag)?

Optimistic Locking erkennt Konflikte erst beim Speichern. In einem Mehrbenutzer-System, in dem viele Mitarbeiter dieselben Aufgaben bearbeiten, würden sich alle auf denselben ältesten DRAFT-Datensatz stürzen — nur einer hat Erfolg, alle anderen bekommen 409. Benutzer müssten sich außerhalb der Anwendung absprechen. Das ist keine gute UX.

## Warum kein neuer Status „In Arbeit"?

Der `Invoice`-Lifecycle-Status (`DRAFT → SENT → PAID → CANCELLED`) ist GoBD-relevant und unveränderbar nach Übergang. Dieser Status beschreibt den **Dokumentenstatus**, nicht den **Bearbeitungsstatus**. Ein transientes UI-Lock-Flag gehört semantisch nicht in das Status-Modell:
- Bei Serverabsturz soll der Lock weg sein, nicht im Audit-Log stehen.
- Lock-Timeout kann konfiguriert werden ohne Einfluss auf GoBD-Compliance.

## Implementierungsdetails

### Modell-Felder (Invoice)

| Feld | Typ | Beschreibung |
|---|---|---|
| `editing_by` | FK → User (nullable) | Benutzer der aktuell den Lock hält |
| `editing_since` | DateTimeField (nullable) | Zeitpunkt der Lock-Übernahme |

### Konfiguration

```
INVOICE_EDIT_LOCK_TIMEOUT_MINUTES=30  # Default, via Umgebungsvariable konfigurierbar
```

### API-Endpunkte

| Methode | URL | Beschreibung |
|---|---|---|
| `POST` | `/invoices/{id}/acquire_edit_lock/` | Lock anfordern (200 OK oder 423 Locked) |
| `POST` | `/invoices/{id}/release_edit_lock/` | Lock freigeben |
| `POST` | `/invoices/{id}/refresh_edit_lock/` | Heartbeat — Lock verlängern |
| `PATCH`/`PUT` | `/invoices/{id}/` | Prüft auf fremden Lock → 423 falls gesperrt |

### Fehlerformat bei 423

```json
{
  "error": {
    "code": "EDIT_LOCKED",
    "message": "Diese Rechnung wird gerade von einem anderen Benutzer bearbeitet.",
    "details": {
      "editing_by": "Max Mustermann",
      "editing_since": "2026-04-27T14:30:00Z"
    }
  }
}
```

### Atomare Lock-Übernahme

`acquire_edit_lock()` verwendet `select_for_update()` innerhalb einer DB-Transaktion, um Race Conditions bei gleichzeitiger Lock-Übernahme durch mehrere HTTP-Requests zu verhindern. Dies ist der einzige legitime Einsatz von `select_for_update()` im System — innerhalb eines einzelnen Requests, nicht über HTTP-Session-Grenzen hinweg.

## Konsequenzen

### Positiv

- Benutzer sieht sofort, wer gerade an einem Datensatz arbeitet — keine nachträglichen Konflikte.
- Kein stilles Überschreiben von Änderungen (Last-Write-Wins).
- Lock-Timeout schützt gegen hängende Locks bei Browserabsturz.
- Supervisor kann Lock administrativ freigeben (via Force-Release).

### Einschränkungen

- Frontend muss Lock-Lifecycle (acquire/heartbeat/release) aktiv verwalten.
- Bei sehr langen Bearbeitungszeiten > Timeout-Dauer muss der Heartbeat laufen.
- Kein Lock-Schutz für GoBD-gesperrte Rechnungen nötig (unveränderbar durch `GoBDViolationError`).

## Anwendungsbereich

Dieses Muster gilt für **alle Entitäten im System, bei denen gleichzeitige Bearbeitung durch mehrere Benutzer zu Konflikten führen kann**. Aktuell: `Invoice`. Zukünftig: `BusinessPartner`, `Company`, `Product` sobald Mehrbenutzer-Konflikte dort relevant werden. Für neue Entitäten ist dasselbe Muster (`editing_by` + `editing_since` + Lock-Endpunkte + Timeout) zu verwenden — siehe `docs/arc42/08-cross-cutting-concepts.md`, Abschnitt „Concurrent Access".
