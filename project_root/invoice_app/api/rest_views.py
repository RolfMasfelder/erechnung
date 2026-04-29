"""
REST API views for the invoice_app.
"""

import hashlib
import json
import logging  # noqa: I001
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import DatabaseError, IntegrityError, OperationalError, models
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, NullIf
from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from invoice_app.models import (
    AuditLog,
    BusinessPartner,
    Company,
    ConsentRecord,
    Country,
    CountryTaxRate,
    DataSubjectRequest,
    Invoice,
    InvoiceAllowanceCharge,
    InvoiceAttachment,
    InvoiceLine,
    PrivacyImpactAssessment,
    ProcessingActivity,
    Product,
)
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import (
    EditLockError,
    FileServingError,
    InsufficientPermissionError,
    InvalidDateFormatError,
    InvalidOperationError,
    InvalidQuantityError,
    InventoryTrackingDisabledError,
    PDFGenerationError,
    ServiceUnavailableError,
    XMLGenerationError,
)
from .serializers import (
    AuditLogSerializer,
    BusinessPartnerImportSerializer,
    BusinessPartnerSerializer,
    CompanySerializer,
    ConsentRecordSerializer,
    CountrySerializer,
    CountryTaxRateSerializer,
    DataSubjectRequestSerializer,
    ImportResultSerializer,
    InvoiceAllowanceChargeSerializer,
    InvoiceAttachmentSerializer,
    InvoiceLineSerializer,
    InvoiceSerializer,
    PrivacyImpactAssessmentSerializer,
    ProcessingActivitySerializer,
    ProductImportSerializer,
    ProductSerializer,
)

logger = logging.getLogger(__name__)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing companies.
    """

    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["name", "country", "tax_id", "vat_id", "is_active"]
    search_fields = ["name", "tax_id", "vat_id", "email"]
    ordering_fields = ["name", "created_at"]


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for countries (read-only reference data).

    Provides ISO country data including VAT rates, currency, and language.
    Used as reference for BusinessPartner.country (ForeignKey).
    """

    queryset = Country.objects.filter(is_active=True).order_by("name")
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "name_local", "code", "currency_code"]
    ordering_fields = ["name", "code"]
    lookup_field = "code"

    @action(detail=True, methods=["get"], url_path="tax-rates")
    def tax_rates(self, request, code=None):
        """
        Return all historically valid VAT rates for a country.

        Returns active rates ordered by valid_from descending.
        Use the `on_date` query parameter (YYYY-MM-DD) to filter effective
        rates for a specific date.
        """
        country = self.get_object()
        on_date_str = request.query_params.get("on_date")
        if on_date_str:
            from datetime import date

            try:
                on_date = date.fromisoformat(on_date_str)
                tax_rates = CountryTaxRate.get_effective_rates(country=country, on_date=on_date)
            except ValueError:
                raise InvalidDateFormatError() from None
        else:
            tax_rates = CountryTaxRate.objects.filter(country=country).order_by("-valid_from", "rate_type")
        serializer = CountryTaxRateSerializer(tax_rates, many=True)
        return Response(serializer.data)


class BusinessPartnerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing business partners (customers and suppliers).
    """

    queryset = BusinessPartner.objects.all()
    serializer_class = BusinessPartnerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["country", "tax_id", "vat_id", "partner_type", "is_customer", "is_supplier", "is_active"]
    search_fields = ["company_name", "first_name", "last_name", "tax_id", "vat_id", "email"]
    ordering_fields = ["business_partner_name", "created_at"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                business_partner_name=Coalesce(
                    NullIf("company_name", models.Value("")),
                    NullIf("last_name", models.Value("")),
                    NullIf("first_name", models.Value("")),
                    models.Value(""),
                )
            )
        )


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing products.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "product_type",
        "category",
        "subcategory",
        "brand",
        "tax_category",
        "is_active",
        "is_sellable",
        "track_inventory",
    ]
    search_fields = ["product_code", "name", "description", "brand", "manufacturer"]
    ordering_fields = ["product_code", "name", "base_price", "created_at"]

    @action(detail=False, methods=["get"], url_path="tax-options")
    def tax_options(self, request):
        """Return legal VAT rates for active company country and selectable product units."""
        active_company = Company.objects.filter(is_active=True).order_by("id").first()

        country = None
        if active_company:
            country_input = (active_company.country or "").strip()
            country = (
                Country.objects.filter(code__iexact=country_input).first()
                or Country.objects.filter(name__iexact=country_input).first()
                or Country.objects.filter(name_local__iexact=country_input).first()
            )

        today = timezone.now().date()
        effective_rates = []
        if country:
            effective_rates = sorted(
                CountryTaxRate.get_effective_rates(country=country, on_date=today),
                key=lambda rate_obj: (rate_obj.rate, rate_obj.rate_type),
            )

        seen_rates = set()
        tax_rate_options = [
            {
                "value": str(rate_obj.rate),
                "label": f"{rate_obj.rate}% ({rate_obj.get_rate_type_display()})",
                "rate_type": rate_obj.rate_type,
                "valid_from": rate_obj.valid_from,
                "valid_to": rate_obj.valid_to,
            }
            for rate_obj in effective_rates
            if (str(rate_obj.rate) not in seen_rates and not seen_rates.add(str(rate_obj.rate)))
        ]

        unit_options = [{"value": value, "label": label} for value, label in Product.UnitOfMeasure.choices]

        return Response(
            {
                "country_code": country.code if country else None,
                "country_name": country.name if country else None,
                "valid_on": today,
                "tax_rates": tax_rate_options,
                "unit_options": unit_options,
            }
        )

    @extend_schema(
        description="Update stock quantity for a product",
        request=inline_serializer(
            name="UpdateStockRequest",
            fields={
                "quantity": serializers.DecimalField(max_digits=10, decimal_places=2, help_text="New stock quantity"),
                "operation": serializers.ChoiceField(
                    choices=["set", "add", "subtract"], help_text="Stock operation type"
                ),
            },
        ),
        responses={200: ProductSerializer},
    )
    @action(detail=True, methods=["post"])
    def update_stock(self, request, pk=None):
        """Update stock quantity for a product."""
        product = self.get_object()

        if not product.track_inventory:
            raise InventoryTrackingDisabledError()

        quantity = request.data.get("quantity")
        operation = request.data.get("operation", "set")

        if quantity is None:
            raise InvalidQuantityError("Menge ist erforderlich.")

        try:
            quantity = Decimal(str(quantity))
        except (ValueError, TypeError, InvalidOperation):
            raise InvalidQuantityError() from None

        if operation == "set":
            product.stock_quantity = quantity
        elif operation == "add":
            product.stock_quantity = (product.stock_quantity or 0) + quantity
        elif operation == "subtract":
            current_stock = product.stock_quantity or 0
            product.stock_quantity = max(0, current_stock - quantity)
        else:
            raise InvalidOperationError("Ungültige Operation. Verwenden Sie 'set', 'add' oder 'subtract'.")

        product.save()
        serializer = self.get_serializer(product)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Get products with low stock levels."""
        low_stock_products = self.queryset.filter(
            track_inventory=True, stock_quantity__lte=models.F("minimum_stock")
        ).exclude(minimum_stock__isnull=True)

        serializer = self.get_serializer(low_stock_products, many=True)
        return Response(serializer.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing audit logs (read-only).
    """

    queryset = AuditLog.objects.all().select_related("user")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["action", "severity", "object_type", "is_compliance_relevant", "is_security_event", "username"]
    search_fields = ["username", "description", "object_repr", "ip_address"]
    ordering_fields = ["timestamp", "action", "severity"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()

        # Only users with explicit permission can view audit logs
        if not self.request.user.has_perm("invoice_app.view_auditlog"):
            return queryset.none()

        return queryset

    @action(detail=False, methods=["get"])
    def security_events(self, request):
        """Get recent security events."""
        security_logs = self.get_queryset().filter(is_security_event=True)[:100]
        serializer = self.get_serializer(security_logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def compliance_events(self, request):
        """Get recent compliance-relevant events."""
        compliance_logs = self.get_queryset().filter(is_compliance_relevant=True)[:100]
        serializer = self.get_serializer(compliance_logs, many=True)
        return Response(serializer.data)

    @extend_schema(
        description="Clean up expired audit log entries",
        responses={
            200: inline_serializer(
                name="CleanupExpiredResponse",
                fields={
                    "deleted_count": serializers.IntegerField(help_text="Number of deleted entries"),
                    "message": serializers.CharField(help_text="Result message"),
                },
            ),
        },
    )
    @action(detail=False, methods=["post"])
    def cleanup_expired(self, request):
        """Clean up expired audit log entries."""
        if not request.user.has_perm("invoice_app.delete_auditlog"):
            raise InsufficientPermissionError()

        deleted_count = AuditLog.cleanup_expired()
        return Response(
            {"deleted_count": deleted_count, "message": f"Cleaned up {deleted_count} expired audit log entries"}
        )


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing invoices.
    """

    queryset = Invoice.objects.all().select_related("company", "business_partner", "created_by")
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Support date range filtering with __gte and __lte lookups
    filterset_fields = {
        "status": ["exact"],
        "invoice_type": ["exact"],
        "company": ["exact"],
        "business_partner": ["exact"],
        "issue_date": ["exact", "gte", "lte"],
        "due_date": ["exact", "gte", "lte"],
    }
    search_fields = ["invoice_number", "notes"]
    ordering_fields = [
        "invoice_number",
        "status",
        "business_partner__company_name",
        "issue_date",
        "due_date",
        "total_amount",
    ]

    def perform_update(self, serializer):
        """Block PATCH/PUT if the invoice is locked by a different user."""
        instance = serializer.instance
        if instance.is_edit_locked_by_other(self.request.user):
            holder = instance.editing_by
            raise EditLockError(
                detail={
                    "editing_by": holder.get_full_name() or holder.username,
                    "editing_since": instance.editing_since.isoformat() if instance.editing_since else None,
                }
            )
        serializer.save()

    @extend_schema(
        description="Acquire the edit lock for this invoice. Returns 423 if already locked by another user.",
        responses={
            200: inline_serializer(
                name="AcquireEditLockResponse",
                fields={"message": serializers.CharField(), "editing_since": serializers.DateTimeField()},
            ),
            423: OpenApiResponse(description="Invoice is currently being edited by another user"),
        },
    )
    @action(detail=True, methods=["post"], url_path="acquire_edit_lock")
    def acquire_edit_lock(self, request, pk=None):
        """Acquire the pessimistic edit lock. Must be called before opening the edit form."""
        invoice = self.get_object()
        success, holder = invoice.acquire_edit_lock(request.user)
        if not success:
            raise EditLockError(
                detail={
                    "editing_by": holder.get_full_name() or holder.username,
                    "editing_since": invoice.editing_since.isoformat() if invoice.editing_since else None,
                }
            )
        return Response(
            {"message": "Bearbeitungssperre gesetzt.", "editing_since": invoice.editing_since},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description="Release the edit lock held by the current user.",
        responses={
            200: inline_serializer(name="ReleaseEditLockResponse", fields={"message": serializers.CharField()})
        },
    )
    @action(detail=True, methods=["post"], url_path="release_edit_lock")
    def release_edit_lock(self, request, pk=None):
        """Release the edit lock. No-op if the current user does not hold the lock."""
        invoice = self.get_object()
        invoice.release_edit_lock(request.user)
        return Response({"message": "Bearbeitungssperre freigegeben."}, status=status.HTTP_200_OK)

    @extend_schema(
        description="Refresh (extend) the edit lock held by the current user. Call every ~60 s as a heartbeat.",
        responses={
            200: inline_serializer(
                name="RefreshEditLockResponse",
                fields={"message": serializers.CharField(), "editing_since": serializers.DateTimeField()},
            ),
            423: OpenApiResponse(description="Lock is held by another user — cannot refresh"),
        },
    )
    @action(detail=True, methods=["post"], url_path="refresh_edit_lock")
    def refresh_edit_lock(self, request, pk=None):
        """Heartbeat: extend the edit lock for another timeout period."""
        invoice = self.get_object()
        success, holder = invoice.acquire_edit_lock(request.user)
        if not success:
            raise EditLockError(
                detail={
                    "editing_by": holder.get_full_name() or holder.username,
                    "editing_since": invoice.editing_since.isoformat() if invoice.editing_since else None,
                }
            )
        return Response(
            {"message": "Bearbeitungssperre verl\u00e4ngert.", "editing_since": invoice.editing_since},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description="Generate and download PDF for the invoice",
        parameters=[
            OpenApiParameter(
                name="profile",
                location=OpenApiParameter.QUERY,
                description="ZUGFeRD/Factur-X profile to use (BASIC, COMFORT, EXTENDED, or XRECHNUNG)",
                type=str,
                default="BASIC",
                required=False,
            ),
        ],
        responses={200: OpenApiResponse(description="PDF generation result")},
    )
    @action(detail=True, methods=["post"])
    def generate_pdf(self, request, pk=None):
        """
        Generate a PDF/A-3 with ZUGFeRD/Factur-X XML for the invoice.

        When ENABLE_ASYNC_PDF is True, the generation is offloaded to a Celery
        worker and the response includes a task_id for polling.
        Otherwise, the PDF is generated synchronously.
        """
        invoice = self.get_object()

        # Get ZUGFeRD profile from query parameters
        zugferd_profile = request.query_params.get("profile", "COMFORT").upper()
        if zugferd_profile not in ["MINIMUM", "BASICWL", "BASIC", "COMFORT", "EXTENDED", "XRECHNUNG"]:
            zugferd_profile = "COMFORT"

        # Async mode: offload to Celery worker (Issue #4)
        if settings.ENABLE_ASYNC_PDF:
            from invoice_app.tasks import generate_invoice_pdf_task

            task = generate_invoice_pdf_task.delay(invoice.pk, zugferd_profile)
            return Response(
                {
                    "status": "PDF generation started",
                    "task_id": task.id,
                    "async": True,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Sync mode (default)
        try:
            from invoice_app.services.invoice_service import InvoiceService

            invoice_service = InvoiceService()
            result = invoice_service.generate_invoice_files(invoice, zugferd_profile)
            pdf_url = request.build_absolute_uri(settings.MEDIA_URL + str(invoice.pdf_file))

            return Response(
                {
                    "status": "PDF generated successfully",
                    "pdf_url": pdf_url,
                    "xml_valid": result["is_valid"],
                    "validation_errors": result["validation_errors"] if not result["is_valid"] else [],
                    "async": False,
                },
                status=status.HTTP_200_OK,
            )

        except (OSError, ValueError) as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            raise PDFGenerationError() from None

    @extend_schema(
        description="Mark the invoice as paid",
        responses={
            200: inline_serializer(
                name="MarkAsPaidResponse",
                fields={"message": serializers.CharField()},
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def mark_as_paid(self, request, pk=None):
        """
        Mark the invoice as paid.
        """
        invoice = self.get_object()
        invoice.status = Invoice.InvoiceStatus.PAID
        invoice.save()

        return Response({"message": "Invoice marked as paid"}, status=status.HTTP_200_OK)

    @extend_schema(
        description="Mark the invoice as sent (DRAFT → SENT). GoBD: auto-locks the invoice.",
        responses={
            200: inline_serializer(
                name="MarkAsSentResponse",
                fields={"message": serializers.CharField()},
            ),
            409: OpenApiResponse(description="Invoice is not in DRAFT status"),
        },
    )
    @action(detail=True, methods=["post"], url_path="mark_as_sent")
    def mark_as_sent(self, request, pk=None):
        """
        Mark the invoice as sent. Transitions DRAFT → SENT and auto-locks (GoBD).
        """
        invoice = self.get_object()
        if invoice.status != Invoice.InvoiceStatus.DRAFT:
            return Response(
                {"detail": "Nur Rechnungen im Entwurfsstatus können als versendet markiert werden."},
                status=status.HTTP_409_CONFLICT,
            )
        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.save()
        return Response(
            {"message": f"Rechnung {invoice.invoice_number} als versendet markiert."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description="Download PDF file for the invoice. Auto-generates if missing.",
        responses={
            (200, "application/pdf"): OpenApiResponse(description="PDF file"),
            404: OpenApiResponse(description="PDF not found"),
            500: OpenApiResponse(description="Server error"),
        },
    )
    @action(detail=True, methods=["get"], url_path="download_pdf")
    def download_pdf(self, request, pk=None):
        """
        Download the PDF file for an invoice.
        Automatically generates the PDF if it doesn't exist.
        """
        invoice = self.get_object()

        # Check if PDF file exists
        if not invoice.pdf_file or not invoice.pdf_file.storage.exists(invoice.pdf_file.name):
            # Auto-generate if missing
            try:
                from invoice_app.services.invoice_service import InvoiceService

                invoice_service = InvoiceService()
                result = invoice_service.generate_invoice_files(invoice, zugferd_profile="COMFORT")
                logger.info(f"Auto-generated PDF for invoice {invoice.id}: {result['pdf_path']}")
            except (OSError, ValueError) as e:
                logger.error(f"Failed to generate PDF for invoice {invoice.id}: {str(e)}")
                raise PDFGenerationError() from None

        # Serve the file
        try:
            pdf_path = invoice.pdf_file.path
            f = open(pdf_path, "rb")  # noqa: SIM115
            response = FileResponse(
                f,
                content_type="application/pdf",
                as_attachment=True,
                filename=f"invoice_{invoice.invoice_number}.pdf",
            )
            return response
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Failed to serve PDF for invoice {invoice.id}: {str(e)}")
            raise FileServingError() from None

    @extend_schema(
        description="Download ZUGFeRD/Factur-X XML file for the invoice. Auto-generates if missing.",
        responses={
            (200, "application/xml"): OpenApiResponse(description="XML file"),
            404: OpenApiResponse(description="XML not found"),
            500: OpenApiResponse(description="Server error"),
        },
    )
    @action(detail=True, methods=["get"], url_path="download_xml")
    def download_xml(self, request, pk=None):
        """
        Download the ZUGFeRD/Factur-X XML file for an invoice.
        Automatically generates the XML if it doesn't exist.
        """
        invoice = self.get_object()

        # Check if XML file exists
        if not invoice.xml_file or not invoice.xml_file.storage.exists(invoice.xml_file.name):
            # Auto-generate if missing
            try:
                from invoice_app.services.invoice_service import InvoiceService

                invoice_service = InvoiceService()
                result = invoice_service.generate_invoice_files(invoice, zugferd_profile="COMFORT")
                logger.info(f"Auto-generated XML for invoice {invoice.id}: {result['xml_path']}")
            except (OSError, ValueError) as e:
                logger.error(f"Failed to generate XML for invoice {invoice.id}: {str(e)}")
                raise XMLGenerationError() from None

        # Serve the file
        try:
            xml_path = invoice.xml_file.path
            f = open(xml_path, "rb")  # noqa: SIM115
            response = FileResponse(
                f,
                content_type="application/xml",
                as_attachment=True,
                filename=f"invoice_{invoice.invoice_number}.xml",
            )
            return response
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Failed to serve XML for invoice {invoice.id}: {str(e)}")
            raise FileServingError() from None

    @extend_schema(
        description="Generate standalone XRechnung XML (without PDF/A-3 embedding) for B2G invoices",
        parameters=[
            OpenApiParameter(
                name="profile",
                location=OpenApiParameter.QUERY,
                description="XML profile to use (default: XRECHNUNG for B2G)",
                type=str,
                default="XRECHNUNG",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(description="XML generation result"),
            400: OpenApiResponse(description="Validation error (e.g., missing BT-10)"),
        },
    )
    @action(detail=True, methods=["post"], url_path="generate_xml")
    def generate_xml(self, request, pk=None):
        """
        Generate standalone XRechnung XML for B2G invoices.

        Produces a pure CII XML file without PDF/A-3 embedding.
        Ideal for government invoices that require XML-only submission.
        """
        invoice = self.get_object()
        profile = request.query_params.get("profile", "XRECHNUNG").upper()
        if profile not in ["MINIMUM", "BASICWL", "BASIC", "COMFORT", "EXTENDED", "XRECHNUNG"]:
            profile = "XRECHNUNG"

        try:
            from invoice_app.services.invoice_service import InvoiceService

            invoice_service = InvoiceService()
            result = invoice_service.generate_xml_only(invoice, zugferd_profile=profile)

            return Response(
                {
                    "status": "XML generated successfully",
                    "xml_valid": result["is_valid"],
                    "validation_errors": result["validation_errors"] if not result["is_valid"] else [],
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"status": "error", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except OSError as e:
            logger.error(f"Failed to generate XML: {str(e)}")
            raise XMLGenerationError() from None

    @extend_schema(
        description="Rechnung stornieren (GoBD-konform: erstellt Stornorechnung statt Löschung)",
        request=inline_serializer(
            name="CancelInvoiceRequest",
            fields={"reason": serializers.CharField(required=False, default="")},
        ),
        responses={
            200: inline_serializer(
                name="CancelInvoiceResponse",
                fields={
                    "message": serializers.CharField(),
                    "credit_note_id": serializers.IntegerField(),
                    "credit_note_number": serializers.CharField(),
                },
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        GoBD-konforme Stornierung: Erstellt eine Stornorechnung (Credit Note).
        """
        invoice = self.get_object()
        reason = request.data.get("reason", "")
        credit_note = invoice.cancel(user=request.user, reason=reason)

        return Response(
            {
                "message": f"Rechnung {invoice.invoice_number} storniert.",
                "credit_note_id": credit_note.id,
                "credit_note_number": credit_note.invoice_number,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        description=(
            "Rechnung per E-Mail versenden. PDF/A-3 wird immer angehängt und "
            "enthält die ZUGFeRD/Factur-X XML bereits eingebettet (EN16931-konform). "
            "Über attach_xml=true kann die XML zusätzlich als separates Attachment "
            "verschickt werden (nur für reine XRechnung-Workflows empfohlen). "
            "Erfordert eine konfigurierte SMTP-Verbindung; "
            "schlägt fehl, wenn INVOICE_EMAIL_ENABLED=False."
        ),
        request=inline_serializer(
            name="SendInvoiceEmailRequest",
            fields={
                "recipient": serializers.EmailField(required=True),
                "message": serializers.CharField(required=False, allow_blank=True, default=""),
                # Default False: PDF/A-3 already embeds the ZUGFeRD/Factur-X XML.
                # Setting to True ships the XML as a separate attachment too
                # (use only for pure XRechnung workflows).
                "attach_xml": serializers.BooleanField(required=False, default=False),
            },
        ),
        responses={
            200: inline_serializer(
                name="SendInvoiceEmailResponse",
                fields={
                    "message": serializers.CharField(),
                    "recipient": serializers.EmailField(),
                    "subject": serializers.CharField(),
                    "attached_files": serializers.ListField(child=serializers.CharField()),
                    "sent_at": serializers.DateTimeField(),
                },
            ),
            400: OpenApiResponse(description="Ungültige Eingabe (z. B. fehlender Empfänger)"),
            503: OpenApiResponse(description="E-Mail-Versand deaktiviert oder SMTP-Fehler"),
        },
    )
    @action(detail=True, methods=["post"], url_path="send_email")
    def send_email(self, request, pk=None):
        """Send the invoice (PDF + optional XML) to a recipient via SMTP."""
        from invoice_app.services.email_service import (
            EmailDeliveryError,
            EmailDisabledError,
            InvoiceEmailService,
        )

        invoice = self.get_object()
        recipient = (request.data.get("recipient") or "").strip()
        message = request.data.get("message") or ""
        # PDF/A-3 already embeds the structured XML — separate attachment is opt-in.
        attach_xml = bool(request.data.get("attach_xml", False))

        if not recipient:
            return Response(
                {"detail": "Empfänger-E-Mail-Adresse ist erforderlich."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # DRAFT auto-transition: sending an invoice marks it as SENT (GoBD-locks it).
        if invoice.status == Invoice.InvoiceStatus.DRAFT:
            invoice.status = Invoice.InvoiceStatus.SENT
            invoice.save()
            invoice.refresh_from_db()

        try:
            result = InvoiceEmailService().send_invoice(
                invoice,
                recipient,
                message=message,
                attach_xml=attach_xml,
                request=request,
                user=request.user,
            )
        except EmailDisabledError as exc:
            logger.warning("Email sending disabled for invoice %s: %s", invoice.id, exc)
            return Response(
                {"detail": "E-Mail-Versand ist derzeit nicht verfügbar."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except EmailDeliveryError as exc:
            logger.error("SMTP delivery failed for invoice %s: %s", invoice.id, exc)
            return Response(
                {"detail": "E-Mail-Versand fehlgeschlagen. Bitte später erneut versuchen."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValueError as exc:
            logger.warning("Invalid email send request for invoice %s: %s", invoice.id, exc)
            return Response(
                {"detail": "Ungültige Anfrageparameter für den E-Mail-Versand."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"Rechnung {invoice.invoice_number} per E-Mail versendet.",
                "recipient": result.recipient,
                "subject": result.subject,
                "attached_files": result.attached_filenames,
                "sent_at": result.sent_at,
            },
            status=status.HTTP_200_OK,
        )


class InvoiceLineViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing invoice lines.
    """

    queryset = InvoiceLine.objects.all().select_related("invoice")
    serializer_class = InvoiceLineSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["invoice"]
    search_fields = ["description", "product_code"]


class InvoiceAttachmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing invoice attachments.
    """

    queryset = InvoiceAttachment.objects.all().select_related("invoice")
    serializer_class = InvoiceAttachmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["invoice"]
    search_fields = ["description"]


class InvoiceAllowanceChargeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing invoice-level allowances and charges (EN16931 BG-20/BG-21).
    Each create/update/delete automatically recalculates invoice totals and
    invalidates the cached PDF (model-level, via InvoiceAllowanceCharge.save/delete).
    """

    queryset = InvoiceAllowanceCharge.objects.all().select_related("invoice")
    serializer_class = InvoiceAllowanceChargeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["invoice", "is_charge"]
    search_fields = ["reason", "reason_code"]


class DashboardStatsView(APIView):
    """
    API endpoint for dashboard statistics.
    Returns aggregated data for invoices, customers, products.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Get dashboard statistics including invoice counts, totals, and overviews",
        responses={
            200: OpenApiResponse(
                description="Statistics data",
                examples=[
                    OpenApiExample(
                        "Dashboard Stats",
                        value={
                            "invoices": {
                                "total": 150,
                                "by_status": {
                                    "draft": 10,
                                    "sent": 25,
                                    "paid": 100,
                                    "cancelled": 5,
                                    "overdue": 10,
                                },
                                "total_amount": 125000.50,
                                "paid_amount": 95000.00,
                                "outstanding_amount": 30000.50,
                            },
                            "customers": {"total": 45, "active": 42},
                            "products": {"total": 80, "active": 75},
                            "companies": {"total": 3, "active": 3},
                        },
                    ),
                ],
            ),
        },
    )
    def get(self, request):
        """Get dashboard statistics."""
        try:
            # Invoice statistics
            invoice_stats = Invoice.objects.aggregate(
                total=Count("id"),
                sum_total_amount=Sum("total_amount"),
                draft_count=Count("id", filter=Q(status="DRAFT")),
                sent_count=Count("id", filter=Q(status="SENT")),
                paid_count=Count("id", filter=Q(status="PAID")),
                cancelled_count=Count("id", filter=Q(status="CANCELLED")),
                overdue_count=Count("id", filter=Q(status="OVERDUE")),
                sum_paid_amount=Sum("total_amount", filter=Q(status="PAID")),
            )

            # Calculate outstanding amount (sent + overdue invoices)
            outstanding = Invoice.objects.filter(status__in=["SENT", "OVERDUE"]).aggregate(
                sum_amount=Sum("total_amount")
            )

            # Business partner statistics (customers/suppliers)
            partner_stats = BusinessPartner.objects.aggregate(
                total=Count("id"),
                active=Count("id", filter=Q(is_active=True)),
            )

            # Product statistics
            product_stats = Product.objects.aggregate(
                total=Count("id"),
                active=Count("id", filter=Q(is_active=True)),
            )

            # Company statistics
            company_stats = Company.objects.aggregate(
                total=Count("id"),
                active=Count("id", filter=Q(is_active=True)),
            )

            return Response(
                {
                    "invoices": {
                        "total": invoice_stats["total"] or 0,
                        "by_status": {
                            "draft": invoice_stats["draft_count"] or 0,
                            "sent": invoice_stats["sent_count"] or 0,
                            "paid": invoice_stats["paid_count"] or 0,
                            "cancelled": invoice_stats["cancelled_count"] or 0,
                            "overdue": invoice_stats["overdue_count"] or 0,
                        },
                        "total_amount": float(invoice_stats["sum_total_amount"] or 0),
                        "paid_amount": float(invoice_stats["sum_paid_amount"] or 0),
                        "outstanding_amount": float(outstanding["sum_amount"] or 0),
                    },
                    "business_partners": {
                        "total": partner_stats["total"] or 0,
                        "active": partner_stats["active"] or 0,
                    },
                    "products": {
                        "total": product_stats["total"] or 0,
                        "active": product_stats["active"] or 0,
                    },
                    "companies": {
                        "total": company_stats["total"] or 0,
                        "active": company_stats["active"] or 0,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except (OperationalError, DatabaseError) as e:
            logger.error(f"Error fetching dashboard stats: {str(e)}")
            raise ServiceUnavailableError("Dashboard-Statistiken konnten nicht abgerufen werden.") from None


def _hash_import_payload(rows):
    """
    Compute a deterministic SHA-256 hash of the imported rows.

    Used as a stable identifier of the source data for audit logging
    (ADR-025 — Hybrid audit). Keys are sorted so re-ordering does not
    change the hash; values are coerced via ``default=str`` to handle
    Decimals/dates emitted by DRF.
    """
    canonical = json.dumps(rows, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _log_import_audit(*, request, object_type, rows, result):
    """
    Write a single aggregated audit entry for a bulk import job (ADR-025).

    One ``AuditLog`` entry per import job containing:

    - User, timestamp, source-data hash, format, dry-run flag
    - Aggregated counts (created/updated/skipped/failed)
    - List of IDs of imported records (no full payloads — those are
      captured by the regular per-model audit hooks)
    - Compact list of row-level errors (row index + message)
    """
    payload_hash = _hash_import_payload(rows)
    error_count = result.get("error_count", 0)
    severity = AuditLog.Severity.MEDIUM if error_count else AuditLog.Severity.LOW

    AuditLog.log_action(
        action=AuditLog.ActionType.IMPORT,
        user=request.user,
        request=request,
        description=f"Bulk-Import: {object_type} ({len(rows)} Zeilen)",
        details={
            "object_type": object_type,
            "format": "json",
            "dry_run": False,
            "source_hash": payload_hash,
            "row_count": len(rows),
            "imported_count": result.get("imported_count", 0),
            "skipped_count": result.get("skipped_count", 0),
            "error_count": error_count,
            "imported_ids": result.get("imported_ids", []),
            "errors": result.get("errors", []),
        },
        severity=severity,
    )


class BusinessPartnerImportView(APIView):
    """
    API endpoint for bulk importing business partners (customers/suppliers).

    POST /api/v1/business-partners/import/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Import business partners from CSV data",
        request=BusinessPartnerImportSerializer,
        responses={
            201: ImportResultSerializer,
            400: OpenApiResponse(description="Validation errors"),
        },
    )
    def post(self, request):
        """Import business partners from validated CSV data."""
        from invoice_app.models import Country

        serializer = BusinessPartnerImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rows = serializer.validated_data["rows"]
        skip_duplicates = serializer.validated_data.get("skip_duplicates", True)
        update_existing = serializer.validated_data.get("update_existing", False)

        imported_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        imported_ids = []

        for idx, row_data in enumerate(rows, start=1):
            try:
                # Resolve country from code
                country_code = row_data.pop("country_code", "DE")
                country = None
                if country_code:
                    country = Country.objects.filter(code=country_code.upper()).first()

                # Check for duplicate by company_name + postal_code
                existing = BusinessPartner.objects.filter(
                    company_name=row_data["company_name"],
                    postal_code=row_data["postal_code"],
                ).first()

                if existing:
                    if update_existing:
                        # Update existing record
                        for key, value in row_data.items():
                            if value:  # Only update non-empty values
                                setattr(existing, key, value)
                        if country:
                            existing.country = country
                        existing.save()
                        imported_ids.append(existing.id)
                        imported_count += 1
                    elif skip_duplicates:
                        skipped_count += 1
                    else:
                        errors.append(
                            {
                                "row": idx,
                                "field": "company_name",
                                "message": f"Geschäftspartner '{row_data['company_name']}' existiert bereits",
                            }
                        )
                        error_count += 1
                else:
                    # Create new record
                    partner = BusinessPartner.objects.create(
                        country=country,
                        **row_data,
                    )
                    imported_ids.append(partner.id)
                    imported_count += 1

            except (IntegrityError, OperationalError, KeyError, ValueError) as e:
                errors.append(
                    {
                        "row": idx,
                        "message": str(e),
                    }
                )
                error_count += 1

        result = {
            "success": error_count == 0,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "errors": errors,
            "imported_ids": imported_ids,
        }

        _log_import_audit(
            request=request,
            object_type="BusinessPartner",
            rows=rows,
            result=result,
        )

        result_status = status.HTTP_201_CREATED if error_count == 0 else status.HTTP_207_MULTI_STATUS
        return Response(result, status=result_status)


class ProductImportView(APIView):
    """
    API endpoint for bulk importing products.

    POST /api/v1/products/import/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Import products from CSV data",
        request=ProductImportSerializer,
        responses={
            201: ImportResultSerializer,
            400: OpenApiResponse(description="Validation errors"),
        },
    )
    def post(self, request):
        """Import products from validated CSV data."""
        serializer = ProductImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rows = serializer.validated_data["rows"]
        skip_duplicates = serializer.validated_data.get("skip_duplicates", True)
        update_existing = serializer.validated_data.get("update_existing", False)

        imported_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        imported_ids = []

        for idx, row_data in enumerate(rows, start=1):
            try:
                # Check for duplicate by product_code or name
                product_code = row_data.get("product_code", "")
                name = row_data["name"]

                existing = None
                if product_code:
                    existing = Product.objects.filter(product_code=product_code).first()
                if not existing:
                    existing = Product.objects.filter(name=name).first()

                if existing:
                    if update_existing:
                        # Update existing record
                        for key, value in row_data.items():
                            if value is not None and value != "":
                                setattr(existing, key, value)
                        existing.save()
                        imported_ids.append(existing.id)
                        imported_count += 1
                    elif skip_duplicates:
                        skipped_count += 1
                    else:
                        errors.append(
                            {
                                "row": idx,
                                "field": "name",
                                "message": f"Produkt '{name}' existiert bereits",
                            }
                        )
                        error_count += 1
                else:
                    # Generate product_code if not provided
                    if not product_code:
                        # Simple auto-generation: P + 5 digits
                        last_product = Product.objects.order_by("-id").first()
                        next_id = (last_product.id + 1) if last_product else 1
                        row_data["product_code"] = f"P{next_id:05d}"

                    # Create new record
                    product = Product.objects.create(**row_data)
                    imported_ids.append(product.id)
                    imported_count += 1

            except (IntegrityError, OperationalError, KeyError, ValueError) as e:
                errors.append(
                    {
                        "row": idx,
                        "message": str(e),
                    }
                )
                error_count += 1

        result = {
            "success": error_count == 0,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "errors": errors,
            "imported_ids": imported_ids,
        }

        _log_import_audit(
            request=request,
            object_type="Product",
            rows=rows,
            result=result,
        )

        result_status = status.HTTP_201_CREATED if error_count == 0 else status.HTTP_207_MULTI_STATUS
        return Response(result, status=result_status)


# ─── GoBD Compliance Reporting ──────────────────────────────────────────────


class ComplianceReportView(APIView):
    """
    GoBD Compliance Report — Integritätsbericht für Betriebsprüfungen.

    Nur für Administratoren zugänglich.
    GET /api/compliance/integrity-report/
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        description="GoBD Integritätsbericht: Prüft Rechnungs-Hashes und Audit-Log-Kette",
        responses={
            200: OpenApiResponse(description="Integritätsbericht als JSON"),
        },
    )
    def get(self, request):
        from invoice_app.services.integrity_service import IntegrityService

        report = IntegrityService.generate_integrity_report()

        AuditLog.log_action(
            action=AuditLog.ActionType.SECURITY_EVENT,
            user=request.user,
            request=request,
            description="GoBD-Integritätsbericht erstellt",
            details={"status": report["status"]},
            severity=AuditLog.Severity.MEDIUM,
        )

        return Response(report, status=status.HTTP_200_OK)


class RetentionSummaryView(APIView):
    """
    Aufbewahrungsfristen-Übersicht.

    GET /api/compliance/retention-summary/
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        description="Übersicht der Aufbewahrungsfristen für Rechnungen und Audit-Log",
        responses={
            200: OpenApiResponse(description="Retention-Statistiken"),
        },
    )
    def get(self, request):
        from invoice_app.services.integrity_service import IntegrityService

        summary = IntegrityService.get_retention_summary()
        return Response(summary, status=status.HTTP_200_OK)


# ── GDPR / DSGVO Views ────────────────────────────────────────────────────


class DataSubjectRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for GDPR Data Subject Requests.
    Admin-only: create, list, process DSRs.
    """

    queryset = DataSubjectRequest.objects.all()
    serializer_class = DataSubjectRequestSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["request_type", "status", "subject_type"]
    search_fields = ["subject_name", "subject_email"]
    ordering_fields = ["created_at", "deadline", "status"]
    ordering = ["-created_at"]

    @extend_schema(
        description="Betroffenenanfrage verarbeiten (Auskunft, Löschung, etc.)",
        responses={200: DataSubjectRequestSerializer},
    )
    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        """Process a DSR (collect data, anonymize, etc.)."""
        from invoice_app.services.gdpr_service import GDPRService

        dsr = self.get_object()

        if dsr.status in (
            DataSubjectRequest.RequestStatus.COMPLETED,
            DataSubjectRequest.RequestStatus.REJECTED,
        ):
            return Response(
                {"detail": "Diese Anfrage wurde bereits abgeschlossen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dsr = GDPRService.process_dsr(dsr.pk, performed_by=request.user)
        serializer = self.get_serializer(dsr)
        return Response(serializer.data)

    @extend_schema(
        description="Überfällige und bald fällige Betroffenenanfragen",
        responses={200: DataSubjectRequestSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def deadlines(self, request):
        """List overdue and upcoming DSR deadlines."""
        from invoice_app.services.gdpr_service import GDPRService

        overdue = GDPRService.get_overdue_requests()
        upcoming = GDPRService.get_upcoming_deadlines(days=7)
        combined = (overdue | upcoming).distinct().order_by("deadline")
        serializer = self.get_serializer(combined, many=True)
        return Response(serializer.data)


class ProcessingActivityViewSet(viewsets.ModelViewSet):
    """
    API endpoint for the Processing Activities Register (Art. 30).
    """

    queryset = ProcessingActivity.objects.all()
    serializer_class = ProcessingActivitySerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "purpose"]
    ordering = ["name"]


class PrivacyImpactAssessmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Privacy Impact Assessments (Art. 35).
    """

    queryset = PrivacyImpactAssessment.objects.all()
    serializer_class = PrivacyImpactAssessmentSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["risk_level", "status"]
    ordering = ["-created_at"]


class ConsentRecordViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Consent Records (Art. 7).
    """

    queryset = ConsentRecord.objects.all()
    serializer_class = ConsentRecordSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["purpose", "granted"]
    search_fields = ["user__username", "user__email"]
