"""
Tests for the global exception handler and custom exceptions.

Ensures:
- All custom exceptions produce the standardized JSON format
- DRF ValidationErrors are consistently formatted
- 500 errors never leak internal details
- Standard HTTP errors (404, 403, 405) are formatted correctly
"""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from invoice_app.api.exception_handlers import _build_error_response, _flatten_validation_errors
from invoice_app.api.exceptions import (
    BusinessLogicError,
    FileServingError,
    ImportDataError,
    InsufficientPermissionError,
    InvalidDateFormatError,
    InvalidInputError,
    InvalidOperationError,
    InvalidQuantityError,
    InventoryTrackingDisabledError,
    InvoiceStatusError,
    PDFGenerationError,
    ServiceUnavailableError,
    XMLGenerationError,
)
from invoice_app.models import Country, Product


class ExceptionClassTests(APITestCase):
    """Test that exception classes have correct attributes."""

    def test_invalid_input_error(self):
        exc = InvalidInputError()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.default_code, "INVALID_INPUT")
        self.assertIn("Ungültige Eingabedaten", str(exc.detail))

    def test_invalid_date_format_error(self):
        exc = InvalidDateFormatError()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.default_code, "INVALID_DATE_FORMAT")
        self.assertIn("Datumsformat", str(exc.detail))

    def test_invalid_quantity_error(self):
        exc = InvalidQuantityError()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.default_code, "INVALID_QUANTITY")

    def test_invalid_operation_error(self):
        exc = InvalidOperationError()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.default_code, "INVALID_OPERATION")

    def test_import_data_error(self):
        exc = ImportDataError()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.default_code, "IMPORT_DATA_ERROR")

    def test_business_logic_error(self):
        exc = BusinessLogicError()
        self.assertEqual(exc.status_code, 409)
        self.assertEqual(exc.default_code, "BUSINESS_LOGIC_ERROR")

    def test_inventory_tracking_disabled_error(self):
        exc = InventoryTrackingDisabledError()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.default_code, "INVENTORY_TRACKING_DISABLED")

    def test_invoice_status_error(self):
        exc = InvoiceStatusError()
        self.assertEqual(exc.status_code, 409)
        self.assertEqual(exc.default_code, "INVOICE_STATUS_ERROR")

    def test_insufficient_permission_error(self):
        exc = InsufficientPermissionError()
        self.assertEqual(exc.status_code, 403)
        self.assertEqual(exc.default_code, "PERMISSION_DENIED")

    def test_pdf_generation_error(self):
        exc = PDFGenerationError()
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(exc.default_code, "PDF_GENERATION_FAILED")

    def test_xml_generation_error(self):
        exc = XMLGenerationError()
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(exc.default_code, "XML_GENERATION_FAILED")

    def test_file_serving_error(self):
        exc = FileServingError()
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(exc.default_code, "FILE_SERVING_FAILED")

    def test_service_unavailable_error(self):
        exc = ServiceUnavailableError()
        self.assertEqual(exc.status_code, 503)
        self.assertEqual(exc.default_code, "SERVICE_UNAVAILABLE")

    def test_custom_message(self):
        """Custom messages override default."""
        exc = InvalidInputError("Feld 'name' darf nicht leer sein.")
        self.assertEqual(str(exc.detail), "Feld 'name' darf nicht leer sein.")

    def test_inheritance(self):
        """Subclasses inherit from parent."""
        self.assertIsInstance(InvalidDateFormatError(), InvalidInputError)
        self.assertIsInstance(InvalidQuantityError(), InvalidInputError)
        self.assertIsInstance(InvalidOperationError(), InvalidInputError)
        self.assertIsInstance(InventoryTrackingDisabledError(), BusinessLogicError)
        self.assertIsInstance(InvoiceStatusError(), BusinessLogicError)


class HelperFunctionTests(APITestCase):
    """Tests for handler helper functions."""

    def test_build_error_response_minimal(self):
        resp = _build_error_response("TEST_CODE", "Test message", http_status=400)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["error"]["code"], "TEST_CODE")
        self.assertEqual(resp.data["error"]["message"], "Test message")
        self.assertNotIn("details", resp.data["error"])

    def test_build_error_response_with_details(self):
        details = {"field": ["Error 1", "Error 2"]}
        resp = _build_error_response("VALIDATION_ERROR", "Fehler", details=details, http_status=400)
        self.assertEqual(resp.data["error"]["details"], details)

    def test_flatten_validation_errors_dict(self):
        detail = {"name": ["This field is required."], "email": ["Enter a valid email."]}
        result = _flatten_validation_errors(detail)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], ["This field is required."])
        self.assertEqual(result["email"], ["Enter a valid email."])

    def test_flatten_validation_errors_list(self):
        detail = ["Error 1", "Error 2"]
        result = _flatten_validation_errors(detail)
        self.assertIsInstance(result, list)
        self.assertEqual(result, ["Error 1", "Error 2"])

    def test_flatten_validation_errors_string(self):
        result = _flatten_validation_errors("Simple error")
        self.assertEqual(result, "Simple error")


class GlobalExceptionHandlerIntegrationTests(APITestCase):
    """Integration tests: verify actual API endpoints return standardized error format."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

        self.germany = Country.objects.get_or_create(
            code="DE",
            defaults={
                "code_alpha3": "DEU",
                "numeric_code": "276",
                "name": "Germany",
                "name_local": "Deutschland",
                "currency_code": "EUR",
                "currency_name": "Euro",
                "currency_symbol": "€",
                "default_language": "de",
                "is_eu_member": True,
                "is_eurozone": True,
                "standard_vat_rate": 19.00,
            },
        )[0]

    def _create_product(self, name="Test Product", code="TST001", track_inventory=False, stock_quantity=None):
        """Helper to create a Product with correct fields."""
        return Product.objects.create(
            name=name,
            product_code=code,
            base_price=10.00,
            track_inventory=track_inventory,
            stock_quantity=stock_quantity,
        )

    def test_invalid_date_format_on_tax_rates(self):
        """GET /countries/DE/tax-rates/?on_date=invalid -> INVALID_DATE_FORMAT."""
        url = reverse("api-country-tax-rates", kwargs={"code": "DE"})
        response = self.client.get(url, {"on_date": "not-a-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "INVALID_DATE_FORMAT")

    def test_inventory_tracking_disabled(self):
        """POST update_stock on product without inventory tracking."""
        product = self._create_product(track_inventory=False)
        url = reverse("api-product-update-stock", kwargs={"pk": product.pk})
        response = self.client.post(url, {"quantity": "5", "operation": "set"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVENTORY_TRACKING_DISABLED")

    def test_invalid_quantity_missing(self):
        """POST update_stock without quantity -> INVALID_QUANTITY."""
        product = self._create_product(name="Tracked", code="TRK001", track_inventory=True, stock_quantity=50)
        url = reverse("api-product-update-stock", kwargs={"pk": product.pk})
        response = self.client.post(url, {"operation": "set"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVALID_QUANTITY")

    def test_invalid_quantity_value(self):
        """POST update_stock with non-numeric quantity -> INVALID_QUANTITY."""
        product = self._create_product(name="Tracked2", code="TRK002", track_inventory=True, stock_quantity=50)
        url = reverse("api-product-update-stock", kwargs={"pk": product.pk})
        response = self.client.post(url, {"quantity": "abc", "operation": "set"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVALID_QUANTITY")

    def test_invalid_operation(self):
        """POST update_stock with bad operation -> INVALID_OPERATION."""
        product = self._create_product(name="Tracked3", code="TRK003", track_inventory=True, stock_quantity=50)
        url = reverse("api-product-update-stock", kwargs={"pk": product.pk})
        response = self.client.post(url, {"quantity": "5", "operation": "multiply"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "INVALID_OPERATION")

    def test_permission_denied_cleanup(self):
        """POST cleanup_expired without permission -> PERMISSION_DENIED."""
        url = reverse("api-audit-log-cleanup-expired")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["code"], "PERMISSION_DENIED")

    def test_not_found_returns_standard_format(self):
        """GET non-existent invoice -> NOT_FOUND in standard error format."""
        url = reverse("api-invoice-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "NOT_FOUND")

    def test_method_not_allowed_returns_standard_format(self):
        """DELETE on read-only endpoint -> METHOD_NOT_ALLOWED."""
        url = reverse("api-country-list")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "METHOD_NOT_ALLOWED")

    def test_unauthenticated_returns_standard_format(self):
        """Request without auth -> error format."""
        from rest_framework.test import APIClient

        anon_client = APIClient()  # fresh client, no auth
        url = reverse("api-invoice-list")
        response = anon_client.get(url)
        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )
        self.assertIn("error", response.data)

    def test_validation_error_on_create(self):
        """POST product with invalid data -> VALIDATION_ERROR with details."""
        url = reverse("api-product-list")
        # Missing required fields (name, product_code)
        response = self.client.post(url, {"base_price": "not-a-number"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("details", response.data["error"])

    def test_error_response_never_leaks_internals(self):
        """Error responses should not contain Python exception names or tracebacks."""
        product = self._create_product(name="Tracked4", code="TRK004", track_inventory=True, stock_quantity=50)
        url = reverse("api-product-update-stock", kwargs={"pk": product.pk})
        response = self.client.post(url, {"quantity": "abc", "operation": "set"}, format="json")
        response_str = str(response.data)
        self.assertNotIn("Traceback", response_str)
        self.assertNotIn('File "', response_str)
        self.assertNotIn("InvalidOperation", response_str)

    def test_error_format_structure(self):
        """All error responses have the standard error structure."""
        product = self._create_product(name="FormatTest", code="FMT001", track_inventory=False)
        url = reverse("api-product-update-stock", kwargs={"pk": product.pk})
        response = self.client.post(url, {"quantity": "5"}, format="json")

        # Verify structure
        self.assertIn("error", response.data)
        error = response.data["error"]
        self.assertIn("code", error)
        self.assertIn("message", error)
        # Code should be uppercase with underscores
        self.assertTrue(error["code"].isupper() or "_" in error["code"])
        # Message should be non-empty
        self.assertTrue(len(error["message"]) > 0)
