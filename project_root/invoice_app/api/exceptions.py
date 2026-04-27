"""
Custom API Exceptions — eRechnung

Einheitliche Fehlerklassen für konsistente API-Antworten.
Alle Exceptions werden vom globalen Exception Handler (exception_handlers.py)
in ein standardisiertes JSON-Format umgewandelt:

    {
        "error": {
            "code": "INVOICE_NOT_FOUND",
            "message": "Rechnung nicht gefunden.",
            "details": { ... }        # optional
        }
    }

Fehler-Katalog:
    Siehe docs/ERROR_CATALOG.md für vollständige Referenz.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


# ─── Validation ─────────────────────────────────────────────────────────────


class InvalidInputError(APIException):
    """Ungültige Eingabedaten (z.B. falsches Format, fehlende Pflichtfelder)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Ungültige Eingabedaten."
    default_code = "INVALID_INPUT"


class InvalidDateFormatError(InvalidInputError):
    """Ungültiges Datumsformat."""

    default_detail = "Ungültiges Datumsformat. Erwartet: YYYY-MM-DD."
    default_code = "INVALID_DATE_FORMAT"


class InvalidQuantityError(InvalidInputError):
    """Ungültiger Mengenwert."""

    default_detail = "Ungültiger Mengenwert."
    default_code = "INVALID_QUANTITY"


class InvalidOperationError(InvalidInputError):
    """Ungültige Operation."""

    default_detail = "Ungültige Operation."
    default_code = "INVALID_OPERATION"


class ImportDataError(InvalidInputError):
    """Fehler beim Datenimport."""

    default_detail = "Import-Daten ungültig."
    default_code = "IMPORT_DATA_ERROR"


# ─── Business Logic ─────────────────────────────────────────────────────────


class BusinessLogicError(APIException):
    """Verletzung einer Geschäftsregel."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Geschäftsregel verletzt."
    default_code = "BUSINESS_LOGIC_ERROR"


class InventoryTrackingDisabledError(BusinessLogicError):
    """Bestandsverfolgung nicht aktiviert."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Bestandsverfolgung ist für dieses Produkt nicht aktiviert."
    default_code = "INVENTORY_TRACKING_DISABLED"


class InvoiceStatusError(BusinessLogicError):
    """Ungültiger Rechnungsstatus für die angeforderte Aktion."""

    default_detail = "Aktion für den aktuellen Rechnungsstatus nicht erlaubt."
    default_code = "INVOICE_STATUS_ERROR"


class GoBDViolationError(BusinessLogicError):
    """Verletzung einer GoBD-Anforderung (z.B. gesperrtes Dokument ändern)."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "GoBD-Verletzung: Gesperrte Dokumente können nicht geändert werden."
    default_code = "GOBD_VIOLATION"


class EditLockError(APIException):
    """Rechnung wird gerade von einem anderen Benutzer bearbeitet (Pessimistic Edit Lock)."""

    status_code = 423  # HTTP 423 Locked (RFC 4918)
    default_detail = "Diese Rechnung wird gerade von einem anderen Benutzer bearbeitet."
    default_code = "EDIT_LOCKED"


# ─── Permissions ────────────────────────────────────────────────────────────


class InsufficientPermissionError(APIException):
    """Fehlende Berechtigung für die Aktion."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Keine Berechtigung für diese Aktion."
    default_code = "PERMISSION_DENIED"


# ─── PDF / XML Generation ──────────────────────────────────────────────────


class PDFGenerationError(APIException):
    """Fehler bei der PDF-Generierung."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "PDF-Generierung fehlgeschlagen."
    default_code = "PDF_GENERATION_FAILED"


class XMLGenerationError(APIException):
    """Fehler bei der XML-Generierung."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "XML-Generierung fehlgeschlagen."
    default_code = "XML_GENERATION_FAILED"


class FileServingError(APIException):
    """Fehler beim Bereitstellen einer Datei."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Datei konnte nicht bereitgestellt werden."
    default_code = "FILE_SERVING_FAILED"


# ─── Database / Infrastructure ──────────────────────────────────────────────


class ServiceUnavailableError(APIException):
    """Infrastruktur- oder Datenbankfehler."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service vorübergehend nicht verfügbar."
    default_code = "SERVICE_UNAVAILABLE"
