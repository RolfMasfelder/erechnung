"""
Tests for DSGVO/GDPR Implementation (Task 3.6).

Tests cover:
- Data Classification registry and utility functions
- DataSubjectRequest model and lifecycle
- ProcessingActivity model (Art. 30)
- PrivacyImpactAssessment model (Art. 35)
- ConsentRecord model (Art. 7)
- GDPRService: data collection, anonymization, DSR processing
- GDPR API endpoints (admin-only access)
- Management command (gdpr_check)
"""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from invoice_app.models import BusinessPartner, Country
from invoice_app.models.gdpr import (
    DATA_CLASSIFICATION_REGISTRY,
    ConsentRecord,
    DataClassification,
    DataSubjectRequest,
    PrivacyImpactAssessment,
    ProcessingActivity,
    get_classification,
    get_unclassified_fields,
)
from invoice_app.services.gdpr_service import GDPRService


User = get_user_model()


class GDPRTestMixin:
    """Shared test setup for GDPR tests."""

    @classmethod
    def setUpTestData(cls):
        cls.country_de, _ = Country.objects.get_or_create(
            code="DE",
            defaults={
                "name": "Germany",
                "is_eu_member": True,
                "standard_vat_rate": Decimal("19.00"),
            },
        )
        cls.admin_user = User.objects.create_superuser(
            username="gdpr_admin",
            email="admin@example.com",
            password="testpass123!",
        )
        cls.regular_user = User.objects.create_user(
            username="gdpr_user",
            email="user@example.com",
            password="testpass123!",
            first_name="Max",
            last_name="Mustermann",
        )
        cls.partner = BusinessPartner.objects.create(
            partner_number="BP-GDPR-001",
            company_name="Test Partner GmbH",
            first_name="Erika",
            last_name="Musterfrau",
            email="erika@testpartner.de",
            phone="+49 123 456789",
            fax="+49 123 456780",
            contact_person="Erika Musterfrau",
            accounting_contact="Buchhaltung",
            accounting_email="buchhaltung@testpartner.de",
            address_line1="Teststraße 42",
            postal_code="10115",
            city="Berlin",
            country=cls.country_de,
        )


# ── Data Classification Tests ──────────────────────────────────────────────


class DataClassificationTests(TestCase):
    """Tests for the data classification registry."""

    def test_classification_choices(self):
        """All classification levels exist."""
        self.assertEqual(len(DataClassification.choices), 4)
        labels = [c[0] for c in DataClassification.choices]
        self.assertIn("public", labels)
        self.assertIn("restricted", labels)

    def test_registry_has_entries(self):
        """Registry contains classified fields."""
        self.assertGreater(len(DATA_CLASSIFICATION_REGISTRY), 20)

    def test_get_classification_known_field(self):
        """get_classification returns correct level for known field."""
        result = get_classification("BusinessPartner", "email")
        self.assertEqual(result, DataClassification.CONFIDENTIAL)

    def test_get_classification_restricted(self):
        """Tax ID classified as restricted."""
        result = get_classification("BusinessPartner", "tax_id")
        self.assertEqual(result, DataClassification.RESTRICTED)

    def test_get_classification_unknown_field(self):
        """Unknown fields return None."""
        result = get_classification("BusinessPartner", "nonexistent_field")
        self.assertIsNone(result)

    def test_get_unclassified_fields(self):
        """Returns list of unclassified fields (may be empty or not)."""
        result = get_unclassified_fields()
        self.assertIsInstance(result, list)


# ── DataSubjectRequest Model Tests ─────────────────────────────────────────


class DataSubjectRequestModelTests(GDPRTestMixin, TestCase):
    """Tests for DataSubjectRequest model."""

    def test_create_dsr(self):
        """Can create a basic DSR."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="erika@testpartner.de",
            subject_name="Erika Musterfrau",
            subject_type="partner",
            deadline=timezone.now().date() + timedelta(days=30),
        )
        self.assertEqual(dsr.status, DataSubjectRequest.RequestStatus.RECEIVED)
        self.assertIn("DSR-", str(dsr))

    def test_auto_deadline(self):
        """Deadline auto-set to 30 days if not provided."""
        dsr = DataSubjectRequest(
            request_type=DataSubjectRequest.RequestType.ERASURE,
            subject_email="test@example.com",
            subject_name="Test Person",
            subject_type="partner",
        )
        dsr.save()
        expected = (timezone.now() + timedelta(days=30)).date()
        self.assertEqual(dsr.deadline, expected)

    def test_is_overdue(self):
        """Overdue detection works."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="test@example.com",
            subject_name="Test",
            subject_type="partner",
            deadline=timezone.now().date() - timedelta(days=1),
        )
        self.assertTrue(dsr.is_overdue)

    def test_not_overdue_when_completed(self):
        """Completed DSR is never overdue."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="test@example.com",
            subject_name="Test",
            subject_type="partner",
            status=DataSubjectRequest.RequestStatus.COMPLETED,
            deadline=timezone.now().date() - timedelta(days=1),
        )
        self.assertFalse(dsr.is_overdue)

    def test_days_remaining(self):
        """Days remaining calculation."""
        future = timezone.now().date() + timedelta(days=10)
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="test@example.com",
            subject_name="Test",
            subject_type="partner",
            deadline=future,
        )
        self.assertEqual(dsr.days_remaining, 10)

    def test_days_remaining_none_when_completed(self):
        """Completed DSR returns None for days_remaining."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="test@example.com",
            subject_name="Test",
            subject_type="partner",
            status=DataSubjectRequest.RequestStatus.COMPLETED,
            deadline=timezone.now().date() + timedelta(days=5),
        )
        self.assertIsNone(dsr.days_remaining)


# ── ProcessingActivity Model Tests ─────────────────────────────────────────


class ProcessingActivityModelTests(TestCase):
    """Tests for ProcessingActivity model."""

    def test_create_processing_activity(self):
        """Can create a processing activity."""
        pa = ProcessingActivity.objects.create(
            name="Rechnungserstellung",
            purpose="Erstellung und Versand von Rechnungen",
            legal_basis=ProcessingActivity.LegalBasis.CONTRACT,
            data_subjects="Kunden, Geschäftspartner",
            data_categories="Name, Adresse, E-Mail, Steuernummer",
            retention_period="10 Jahre (GoBD)",
        )
        self.assertEqual(str(pa), "Rechnungserstellung")
        self.assertTrue(pa.is_active)


# ── PrivacyImpactAssessment Model Tests ────────────────────────────────────


class PIAModelTests(TestCase):
    """Tests for PrivacyImpactAssessment model."""

    def test_create_pia(self):
        """Can create a PIA."""
        pia = PrivacyImpactAssessment.objects.create(
            feature_name="E-Rechnung Import",
            description="Import von ZUGFeRD/XRechnung PDFs",
            data_types="Rechnungsdaten, Geschäftspartner-PII",
            risk_level=PrivacyImpactAssessment.RiskLevel.MEDIUM,
            risk_description="Verarbeitung personenbezogener Rechnungsdaten",
            mitigation_measures="Verschlüsselung, Zugriffskontrolle, Audit-Logging",
        )
        self.assertIn("Mittel", str(pia))
        self.assertEqual(pia.status, PrivacyImpactAssessment.AssessmentStatus.DRAFT)


# ── ConsentRecord Model Tests ──────────────────────────────────────────────


class ConsentRecordModelTests(GDPRTestMixin, TestCase):
    """Tests for ConsentRecord model."""

    def test_grant_consent(self):
        """Can grant consent."""
        consent = ConsentRecord.objects.create(
            user=self.regular_user,
            purpose=ConsentRecord.ConsentPurpose.ANALYTICS,
        )
        consent.grant(ip_address="192.168.1.1")
        consent.refresh_from_db()
        self.assertTrue(consent.granted)
        self.assertIsNotNone(consent.granted_at)
        self.assertEqual(consent.ip_address, "192.168.1.1")

    def test_revoke_consent(self):
        """Can revoke consent."""
        consent = ConsentRecord.objects.create(
            user=self.regular_user,
            purpose=ConsentRecord.ConsentPurpose.NEWSLETTER,
            granted=True,
            granted_at=timezone.now(),
        )
        consent.revoke()
        consent.refresh_from_db()
        self.assertFalse(consent.granted)
        self.assertIsNotNone(consent.revoked_at)

    def test_unique_user_purpose(self):
        """Only one consent per user + purpose."""
        ConsentRecord.objects.create(user=self.regular_user, purpose=ConsentRecord.ConsentPurpose.ANALYTICS)
        with self.assertRaises(IntegrityError):
            ConsentRecord.objects.create(user=self.regular_user, purpose=ConsentRecord.ConsentPurpose.ANALYTICS)


# ── GDPRService Tests ──────────────────────────────────────────────────────


class GDPRServiceDataCollectionTests(GDPRTestMixin, TestCase):
    """Tests for GDPRService data collection (Art. 15)."""

    def test_collect_partner_data(self):
        """Collect all PII for a partner DSR."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="erika@testpartner.de",
            subject_name="Erika Musterfrau",
            subject_type="partner",
            deadline=timezone.now().date() + timedelta(days=30),
        )
        data = GDPRService.collect_subject_data(dsr)
        self.assertIn("business_partner", data)
        self.assertEqual(len(data["business_partner"]), 1)
        self.assertEqual(data["business_partner"][0]["first_name"], "Erika")

    def test_collect_user_data(self):
        """Collect all PII for a user DSR."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="user@example.com",
            subject_name="Max Mustermann",
            subject_type="user",
            deadline=timezone.now().date() + timedelta(days=30),
        )
        data = GDPRService.collect_subject_data(dsr)
        self.assertIn("user_account", data)
        self.assertEqual(len(data["user_account"]), 1)
        self.assertEqual(data["user_account"][0]["first_name"], "Max")

    def test_export_json(self):
        """Export data as JSON string."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.PORTABILITY,
            subject_email="erika@testpartner.de",
            subject_name="Erika Musterfrau",
            subject_type="partner",
            deadline=timezone.now().date() + timedelta(days=30),
        )
        json_str = GDPRService.export_subject_data_json(dsr)
        self.assertIn("Erika", json_str)
        self.assertIn("business_partner", json_str)


class GDPRServiceAnonymizationTests(GDPRTestMixin, TestCase):
    """Tests for GDPRService anonymization (Art. 17, GoBD-compliant)."""

    def test_anonymize_partner(self):
        """Partner PII is replaced with anonymized placeholder."""
        GDPRService.anonymize_partner(self.partner.pk, performed_by=self.admin_user)
        self.partner.refresh_from_db()
        self.assertIn("Anonymisiert", self.partner.first_name)
        self.assertEqual(self.partner.email, "")
        self.assertEqual(self.partner.phone, "")
        self.assertFalse(self.partner.is_active)
        # Partner record preserved (GoBD)
        self.assertIsNotNone(self.partner.pk)

    def test_anonymize_user(self):
        """User PII is replaced, account deactivated."""
        GDPRService.anonymize_user(self.regular_user.pk, performed_by=self.admin_user)
        self.regular_user.refresh_from_db()
        self.assertIn("anon_", self.regular_user.username)
        self.assertEqual(self.regular_user.email, "")
        self.assertFalse(self.regular_user.is_active)
        self.assertFalse(self.regular_user.has_usable_password())


class GDPRServiceDSRProcessingTests(GDPRTestMixin, TestCase):
    """Tests for full DSR processing workflow."""

    def test_process_access_request(self):
        """Access request collects data and completes."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="erika@testpartner.de",
            subject_name="Erika Musterfrau",
            subject_type="partner",
            deadline=timezone.now().date() + timedelta(days=30),
        )
        result = GDPRService.process_dsr(dsr.pk, performed_by=self.admin_user)
        self.assertEqual(result.status, DataSubjectRequest.RequestStatus.COMPLETED)
        self.assertIn("business_partner", result.result_data)

    def test_process_erasure_request(self):
        """Erasure request anonymizes partner data."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ERASURE,
            subject_email="erika@testpartner.de",
            subject_name="Erika Musterfrau",
            subject_type="partner",
            related_partner=self.partner,
            deadline=timezone.now().date() + timedelta(days=30),
        )
        result = GDPRService.process_dsr(dsr.pk, performed_by=self.admin_user)
        self.assertEqual(result.status, DataSubjectRequest.RequestStatus.COMPLETED)
        self.partner.refresh_from_db()
        self.assertIn("Anonymisiert", self.partner.first_name)

    def test_process_restriction_request(self):
        """Restriction request deactivates partner."""
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.RESTRICTION,
            subject_email="erika@testpartner.de",
            subject_name="Erika Musterfrau",
            subject_type="partner",
            deadline=timezone.now().date() + timedelta(days=30),
        )
        result = GDPRService.process_dsr(dsr.pk, performed_by=self.admin_user)
        self.assertEqual(result.status, DataSubjectRequest.RequestStatus.COMPLETED)
        self.partner.refresh_from_db()
        self.assertFalse(self.partner.is_active)

    def test_process_completed_dsr_rejected(self):
        """Cannot re-process a completed DSR via API."""
        DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="test@example.com",
            subject_name="Test",
            subject_type="partner",
            status=DataSubjectRequest.RequestStatus.COMPLETED,
            deadline=timezone.now().date() + timedelta(days=30),
        )
        # The API-level check is in the ViewSet, not the service
        # Service-level: processing a completed DSR again is tested via API below

    def test_deadline_monitoring(self):
        """Overdue and upcoming deadline queries work."""
        DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="overdue@example.com",
            subject_name="Overdue",
            subject_type="partner",
            deadline=timezone.now().date() - timedelta(days=5),
        )
        DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="upcoming@example.com",
            subject_name="Upcoming",
            subject_type="partner",
            deadline=timezone.now().date() + timedelta(days=3),
        )
        overdue = GDPRService.get_overdue_requests()
        upcoming = GDPRService.get_upcoming_deadlines(days=7)
        self.assertEqual(overdue.count(), 1)
        self.assertEqual(overdue.first().subject_name, "Overdue")
        self.assertGreaterEqual(upcoming.count(), 1)


# ── API Endpoint Tests ─────────────────────────────────────────────────────


class GDPRAPITests(GDPRTestMixin, TestCase):
    """Tests for GDPR REST API endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_dsr_list_requires_admin(self):
        """Non-admin users cannot access DSR list."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/gdpr/requests/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dsr_list_admin_access(self):
        """Admin can list DSRs."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/gdpr/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dsr_create(self):
        """Admin can create a DSR."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            "/api/gdpr/requests/",
            {
                "request_type": "access",
                "subject_email": "erika@testpartner.de",
                "subject_name": "Erika Musterfrau",
                "subject_type": "partner",
                "deadline": (timezone.now().date() + timedelta(days=30)).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_dsr_process_action(self):
        """Admin can process a DSR via /process/ action."""
        self.client.force_authenticate(user=self.admin_user)
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="erika@testpartner.de",
            subject_name="Erika Musterfrau",
            subject_type="partner",
            deadline=timezone.now().date() + timedelta(days=30),
        )
        response = self.client.post(f"/api/gdpr/requests/{dsr.pk}/process/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "completed")

    def test_dsr_process_completed_rejected(self):
        """Cannot process already completed DSR."""
        self.client.force_authenticate(user=self.admin_user)
        dsr = DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="test@example.com",
            subject_name="Test",
            subject_type="partner",
            status=DataSubjectRequest.RequestStatus.COMPLETED,
            deadline=timezone.now().date() + timedelta(days=30),
        )
        response = self.client.post(f"/api/gdpr/requests/{dsr.pk}/process/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dsr_deadlines_action(self):
        """Deadlines endpoint returns overdue/upcoming."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/gdpr/requests/deadlines/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_processing_activity_crud(self):
        """Admin can CRUD processing activities."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            "/api/gdpr/processing-activities/",
            {
                "name": "Rechnungserstellung",
                "purpose": "Erstellung von Rechnungen",
                "legal_basis": "contract",
                "data_subjects": "Kunden",
                "data_categories": "Name, Adresse",
                "retention_period": "10 Jahre",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_pia_crud(self):
        """Admin can CRUD privacy impact assessments."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            "/api/gdpr/impact-assessments/",
            {
                "feature_name": "Test Feature",
                "description": "Test",
                "data_types": "Name",
                "risk_level": "low",
                "risk_description": "Niedrig",
                "mitigation_measures": "Verschlüsselung",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_consent_requires_admin(self):
        """Non-admin users cannot access consent records."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/gdpr/consent-records/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ── Management Command Tests ──────────────────────────────────────────────


class GDPRManagementCommandTests(GDPRTestMixin, TestCase):
    """Tests for the gdpr_check management command."""

    def test_gdpr_check_runs(self):
        """Management command runs without errors."""
        out = StringIO()
        call_command("gdpr_check", stdout=out)
        output = out.getvalue()
        self.assertIn("DSGVO-Statusbericht", output)

    def test_gdpr_check_json(self):
        """JSON output works."""
        out = StringIO()
        call_command("gdpr_check", json=True, stdout=out)
        output = out.getvalue()
        self.assertIn("dsr_summary", output)

    def test_gdpr_check_deadlines(self):
        """Deadlines sub-command works."""
        out = StringIO()
        call_command("gdpr_check", deadlines=True, stdout=out)
        output = out.getvalue()
        self.assertIn("DSGVO-Fristen", output)

    def test_gdpr_check_classification(self):
        """Classification sub-command works."""
        out = StringIO()
        call_command("gdpr_check", classification=True, stdout=out)
        output = out.getvalue()
        self.assertIn("Datenklassifizierung", output)

    def test_gdpr_check_overdue_exits_1(self):
        """Command exits with code 1 when overdue DSRs exist."""
        DataSubjectRequest.objects.create(
            request_type=DataSubjectRequest.RequestType.ACCESS,
            subject_email="overdue@example.com",
            subject_name="Overdue Test",
            subject_type="partner",
            deadline=timezone.now().date() - timedelta(days=5),
        )
        out = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            call_command("gdpr_check", stdout=out)
        self.assertEqual(ctx.exception.code, 1)
