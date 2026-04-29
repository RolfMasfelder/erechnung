"""
Tests for the import API endpoints.
"""

import pytest
from django.urls import reverse
from invoice_app.models import BusinessPartner, Country, Product
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an authenticated API client."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(username="testuser", password="testpass123")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def germany():
    """Create or get Germany country fixture."""
    country, _ = Country.objects.get_or_create(
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
            "reduced_vat_rate": 7.00,
        },
    )
    return country


@pytest.fixture
def austria():
    """Create or get Austria country fixture."""
    country, _ = Country.objects.get_or_create(
        code="AT",
        defaults={
            "code_alpha3": "AUT",
            "numeric_code": "040",
            "name": "Austria",
            "name_local": "Österreich",
            "currency_code": "EUR",
            "currency_name": "Euro",
            "currency_symbol": "€",
            "default_language": "de",
            "is_eu_member": True,
            "is_eurozone": True,
            "standard_vat_rate": 20.00,
            "reduced_vat_rate": 10.00,
        },
    )
    return country


@pytest.mark.django_db
class TestBusinessPartnerImport:
    """Tests for business partner import endpoint."""

    def test_import_single_partner_success(self, api_client, germany):
        """Test importing a single business partner."""
        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Test GmbH",
                    "address_line1": "Teststraße 1",
                    "postal_code": "12345",
                    "city": "Berlin",
                    "country_code": "DE",
                    "email": "test@example.com",
                }
            ]
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["imported_count"] == 1
        assert response.data["error_count"] == 0

        # Verify partner was created
        partner = BusinessPartner.objects.get(company_name="Test GmbH")
        assert partner.postal_code == "12345"
        assert partner.city == "Berlin"
        assert partner.country.code == "DE"

    def test_import_multiple_partners(self, api_client, germany, austria):
        """Test importing multiple business partners."""
        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Partner 1 GmbH",
                    "address_line1": "Straße 1",
                    "postal_code": "10001",
                    "city": "Berlin",
                    "country_code": "DE",
                },
                {
                    "company_name": "Partner 2 AG",
                    "address_line1": "Straße 2",
                    "postal_code": "1010",
                    "city": "Wien",
                    "country_code": "AT",
                },
            ]
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["imported_count"] == 2
        assert BusinessPartner.objects.count() == 2

    def test_import_skip_duplicates(self, api_client, germany):
        """Test that duplicates are skipped by default."""
        # Create existing partner
        BusinessPartner.objects.create(
            company_name="Existing GmbH",
            address_line1="Existing Str 1",
            postal_code="12345",
            city="Berlin",
            country=germany,
        )

        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Existing GmbH",
                    "address_line1": "New Address",
                    "postal_code": "12345",
                    "city": "Berlin",
                    "country_code": "DE",
                }
            ],
            "skip_duplicates": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["imported_count"] == 0
        assert response.data["skipped_count"] == 1
        assert BusinessPartner.objects.count() == 1

    def test_import_update_existing(self, api_client, germany):
        """Test updating existing partners."""
        partner = BusinessPartner.objects.create(
            company_name="Update Me GmbH",
            address_line1="Old Street",
            postal_code="11111",
            city="Munich",
            country=germany,
        )

        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Update Me GmbH",
                    "address_line1": "New Street 123",
                    "postal_code": "11111",
                    "city": "Munich",
                    "country_code": "DE",
                    "email": "new@example.com",
                }
            ],
            "update_existing": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["imported_count"] == 1

        partner.refresh_from_db()
        assert partner.address_line1 == "New Street 123"
        assert partner.email == "new@example.com"

    def test_import_validation_error_missing_required(self, api_client, germany):
        """Test validation error for missing required fields."""
        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Incomplete GmbH"
                    # Missing required fields
                }
            ]
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_invalid_country_code(self, api_client):
        """Test validation error for invalid country code."""
        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Invalid Country GmbH",
                    "address_line1": "Test Street",
                    "postal_code": "12345",
                    "city": "Berlin",
                    "country_code": "XX",  # Invalid
                }
            ]
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_empty_rows(self, api_client):
        """Test error for empty rows."""
        url = reverse("api-business-partner-import")
        data = {"rows": []}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_requires_authentication(self, germany):
        """Test that import requires authentication."""
        client = APIClient()
        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {"company_name": "Test GmbH", "address_line1": "Test Street", "postal_code": "12345", "city": "Berlin"}
            ]
        }

        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProductImport:
    """Tests for product import endpoint."""

    def test_import_single_product_success(self, api_client):
        """Test importing a single product."""
        url = reverse("api-product-import")
        data = {"rows": [{"name": "Test Product", "base_price": "99.99", "description": "A test product"}]}

        response = api_client.post(url, data, format="json")

        # Debug: Print response on failure
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["imported_count"] == 1

        product = Product.objects.get(name="Test Product")
        assert float(product.base_price) == 99.99

    def test_import_product_with_code(self, api_client):
        """Test importing product with product code."""
        url = reverse("api-product-import")
        data = {"rows": [{"name": "Coded Product", "product_code": "SKU-12345", "base_price": "49.99"}]}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        product = Product.objects.get(product_code="SKU-12345")
        assert product.name == "Coded Product"

    def test_import_auto_generate_product_code(self, api_client):
        """Test that product code is auto-generated if not provided."""
        url = reverse("api-product-import")
        data = {"rows": [{"name": "Auto Code Product", "base_price": "19.99"}]}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        product = Product.objects.get(name="Auto Code Product")
        assert product.product_code.startswith("P")

    def test_import_multiple_products(self, api_client):
        """Test importing multiple products."""
        url = reverse("api-product-import")
        data = {
            "rows": [
                {"name": "Product 1", "base_price": "10.00"},
                {"name": "Product 2", "base_price": "20.00"},
                {"name": "Product 3", "base_price": "30.00"},
            ]
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["imported_count"] == 3
        assert Product.objects.count() == 3

    def test_import_skip_duplicate_products(self, api_client):
        """Test skipping duplicate products."""
        Product.objects.create(name="Existing Product", base_price=50.00, product_code="EX001")

        url = reverse("api-product-import")
        data = {"rows": [{"name": "Existing Product", "base_price": "60.00"}], "skip_duplicates": True}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["skipped_count"] == 1
        assert Product.objects.count() == 1

    def test_import_update_existing_product(self, api_client):
        """Test updating existing product."""
        product = Product.objects.create(name="Update Product", product_code="UPD001", base_price=100.00)

        url = reverse("api-product-import")
        data = {
            "rows": [
                {
                    "name": "Update Product",
                    "product_code": "UPD001",
                    "base_price": "150.00",
                    "description": "Updated description",
                }
            ],
            "update_existing": True,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        product.refresh_from_db()
        assert float(product.base_price) == 150.00
        assert product.description == "Updated description"

    def test_import_validation_negative_price(self, api_client):
        """Test validation error for negative price."""
        url = reverse("api-product-import")
        data = {"rows": [{"name": "Negative Price", "base_price": "-10.00"}]}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_product_with_all_fields(self, api_client):
        """Test importing product with all optional fields."""
        url = reverse("api-product-import")
        data = {
            "rows": [
                {
                    "name": "Complete Product",
                    "product_code": "COMP001",
                    "base_price": "199.99",
                    "cost_price": "100.00",
                    "description": "Full description",
                    "short_description": "Short desc",
                    "category": "Electronics",
                    "subcategory": "Phones",
                    "brand": "TestBrand",
                    "manufacturer": "TestMfg",
                    "tax_rate": "19.00",  # Maps to default_tax_rate
                    "currency": "EUR",
                    "is_active": True,
                    "is_sellable": True,
                    "track_inventory": True,
                    "stock_quantity": 100,
                    "reorder_level": 10,  # Maps to minimum_stock
                }
            ]
        }

        response = api_client.post(url, data, format="json")

        # Debug: Print response on failure
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")

        assert response.status_code == status.HTTP_201_CREATED
        product = Product.objects.get(product_code="COMP001")
        assert product.category == "Electronics"
        assert float(product.stock_quantity) == 100.0
        assert float(product.minimum_stock) == 10.0
        assert float(product.default_tax_rate) == 19.00


@pytest.mark.django_db
class TestImportAuditLogging:
    """Tests for the hybrid audit log entry written by import endpoints (ADR-025)."""

    def test_business_partner_import_creates_audit_entry(self, api_client, germany):
        from invoice_app.models import AuditLog

        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Audit GmbH",
                    "address_line1": "Auditstr. 1",
                    "postal_code": "10115",
                    "city": "Berlin",
                    "country_code": "DE",
                },
                {
                    "company_name": "Audit AG",
                    "address_line1": "Auditstr. 2",
                    "postal_code": "10117",
                    "city": "Berlin",
                    "country_code": "DE",
                },
            ]
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        entries = AuditLog.objects.filter(action=AuditLog.ActionType.IMPORT).order_by("-timestamp")
        assert entries.count() == 1
        entry = entries.first()
        assert entry.details["object_type"] == "BusinessPartner"
        assert entry.details["row_count"] == 2
        assert entry.details["imported_count"] == 2
        assert entry.details["error_count"] == 0
        assert entry.details["dry_run"] is False
        assert entry.details["format"] == "json"
        assert len(entry.details["source_hash"]) == 64
        assert len(entry.details["imported_ids"]) == 2
        assert entry.severity == AuditLog.Severity.LOW

    def test_product_import_creates_audit_entry(self, api_client):
        from invoice_app.models import AuditLog

        url = reverse("api-product-import")
        data = {"rows": [{"name": "Audit Product", "base_price": "12.34"}]}
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        entry = AuditLog.objects.filter(action=AuditLog.ActionType.IMPORT).get()
        assert entry.details["object_type"] == "Product"
        assert entry.details["imported_count"] == 1
        assert len(entry.details["imported_ids"]) == 1

    def test_audit_entry_records_errors_with_medium_severity(self, api_client, germany):
        """A row that triggers an error must be recorded compactly with raised severity."""
        from invoice_app.models import AuditLog, BusinessPartner

        BusinessPartner.objects.create(
            company_name="Dup GmbH",
            address_line1="Dup 1",
            postal_code="20095",
            city="Hamburg",
            country=germany,
        )

        url = reverse("api-business-partner-import")
        data = {
            "rows": [
                {
                    "company_name": "Dup GmbH",
                    "address_line1": "Dup 1",
                    "postal_code": "20095",
                    "city": "Hamburg",
                    "country_code": "DE",
                }
            ],
            "skip_duplicates": False,
            "update_existing": False,
        }
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_207_MULTI_STATUS

        entry = AuditLog.objects.filter(action=AuditLog.ActionType.IMPORT).get()
        assert entry.details["error_count"] == 1
        assert entry.details["imported_count"] == 0
        assert len(entry.details["errors"]) == 1
        assert entry.severity == AuditLog.Severity.MEDIUM

    def test_audit_source_hash_is_deterministic(self, api_client, germany):
        """Identical payloads must produce identical source_hash values."""
        from invoice_app.models import AuditLog

        rows = [
            {
                "company_name": "Hash GmbH",
                "address_line1": "Hashstr. 1",
                "postal_code": "30159",
                "city": "Hannover",
                "country_code": "DE",
            }
        ]
        url = reverse("api-business-partner-import")
        api_client.post(url, {"rows": rows}, format="json")
        api_client.post(url, {"rows": rows, "skip_duplicates": True}, format="json")

        hashes = list(
            AuditLog.objects.filter(action=AuditLog.ActionType.IMPORT)
            .order_by("timestamp")
            .values_list("details__source_hash", flat=True)
        )
        assert len(hashes) == 2
        assert hashes[0] == hashes[1]
