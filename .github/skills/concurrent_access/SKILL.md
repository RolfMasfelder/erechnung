---
name: concurrent_access
display_name: Concurrent Access — Pessimistisches Edit-Lock
version: 1.0.0
author: Rolf Masfelder
description: >
  Zugriffsmuster für parallele Bearbeitungszugriffe mehrerer Benutzer auf denselben Datensatz.
  USE FOR: neue Entitäten die bearbeitet werden können; Fragen zu Locks, 423-Fehler, Heartbeats;
  Race Conditions; Parallelzugriff-Bugs.
---

# Concurrent Access — Pessimistisches Edit-Lock

## Entscheidung (ADR-024)

Das System verwendet **Pessimistisches Application-Level Locking** (Checkout/Checkin).
Kein Optimistic Locking. Kein Status-Feld "In Arbeit".

Dokumentiert in:
- `docs/arc42/adrs/ADR-024-pessimistic-edit-locking.md` — Entscheidung + Rationale
- `docs/arc42/08-cross-cutting-concepts.md` Abschnitt 8.9 — verbindliches Muster

## Pflichtschritte bei neuer Entität

### 1. Backend: Model-Felder

```python
editing_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name="editing_<entity>s",
    verbose_name=_("In Bearbeitung von"),
)
editing_since = models.DateTimeField(_("In Bearbeitung seit"), null=True, blank=True)
```

Index auf `editing_since` hinzufügen.

### 2. Backend: Hilfsmethoden im Model

Drei Methoden kopieren/anpassen von `Invoice`:
- `is_edit_locked_by_other(user)` — prüft Fremdlock + Timeout
- `acquire_edit_lock(user)` — atomar mit `select_for_update()` in `transaction.atomic()`
- `release_edit_lock(user)` — gibt Lock frei, nur durch Inhaber

Timeout kommt aus `settings.INVOICE_EDIT_LOCK_TIMEOUT_MINUTES` (30 Min. Default).
Für weitere Entitäten eigene Setting-Variable anlegen: `<ENTITY>_EDIT_LOCK_TIMEOUT_MINUTES`.

### 3. Backend: Exception

`EditLockError` aus `invoice_app.api.exceptions` ist bereits vorhanden und wiederverwendbar.

### 4. Backend: ViewSet

```python
def perform_update(self, serializer):
    instance = serializer.instance
    if instance.is_edit_locked_by_other(self.request.user):
        holder = instance.editing_by
        raise EditLockError(detail={
            "editing_by": holder.get_full_name() or holder.username,
            "editing_since": instance.editing_since.isoformat(),
        })
    serializer.save()

@action(detail=True, methods=["post"], url_path="acquire_edit_lock")
def acquire_edit_lock(self, request, pk=None): ...

@action(detail=True, methods=["post"], url_path="release_edit_lock")
def release_edit_lock(self, request, pk=None): ...

@action(detail=True, methods=["post"], url_path="refresh_edit_lock")
def refresh_edit_lock(self, request, pk=None): ...
```

Für Vorlage: `InvoiceViewSet` in `project_root/invoice_app/api/rest_views.py`.

### 5. Backend: Serializer

`editing_by_display` (SerializerMethodField, gibt `full_name` oder `username` zurück) und
`editing_since` zu `fields` und `read_only_fields` hinzufügen.

### 6. Backend: Migration

`makemigrations <app> --name add_edit_lock_fields` ausführen (Docker).

### 7. Frontend: fieldMappings.js

```js
editing_by_display: 'editing_by_display',  // read-only
editing_since:      'editing_since',        // read-only
```

### 8. Frontend: Service

Drei Methoden analog zu `invoiceService.acquireEditLock/releaseEditLock/refreshEditLock`.

### 9. Frontend: useEditLock Composable

Wiederverwendbares Composable `frontend/src/composables/useEditLock.js` nutzen.
Parameter: `(invoiceId, serviceRef)` — `serviceRef` ist der jeweilige Service.

### 10. Frontend: View / Modal

- **DetailView**: Lock-Banner anzeigen wenn `entity.editing_by_display` gesetzt
- **EditModal**: `useEditLock` einbinden, Lock bei `onMounted` acquiren, 423 als Fehlerzustand zeigen

## Fehlerformat (HTTP 423)

```json
{
  "error": {
    "code": "EDIT_LOCKED",
    "message": "...",
    "details": { "editing_by": "Max Mustermann", "editing_since": "2026-04-27T14:30:00Z" }
  }
}
```

## Konfiguration

```
INVOICE_EDIT_LOCK_TIMEOUT_MINUTES=30
```

## Abgrenzung

| Lock | Zweck | Mechanismus |
|---|---|---|
| `editing_by/editing_since` | Parallele Bearbeitung | Application-Level, temporär, Heartbeat |
| `is_locked` | GoBD-Unveränderbarkeit | Permanent nach SENT/PAID/CANCELLED |
