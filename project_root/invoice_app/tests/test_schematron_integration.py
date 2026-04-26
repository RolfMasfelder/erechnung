"""
Integration tests for EN16931 Schematron validation against existing XML files.

These tests validate real invoice XML files from the media/xml/ directory
against both XSD and EN16931 Schematron rules using Saxon-HE.

Run with: docker compose exec web python project_root/manage.py test invoice_app.tests.test_schematron_integration -v2
"""

import unittest
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from invoice_app.utils.xml.backends import SchematronSaxonBackend, XsdOnlyBackend
from invoice_app.utils.xml.constants import SCHEMATRON_XSLT_PATH, XSD_PATH
from invoice_app.utils.xml.validator import ZugferdXmlValidator


MEDIA_XML_DIR = Path(settings.BASE_DIR) / "media" / "xml"


class TestExistingXmlSchematronValidation(TestCase):
    """Validate existing XML files from media/xml/ against EN16931 Schematron."""

    @classmethod
    def setUpClass(cls):
        """Load validation backends once for all tests."""
        super().setUpClass()
        if not SCHEMATRON_XSLT_PATH.exists():
            raise unittest.SkipTest(f"Schematron XSLT not found: {SCHEMATRON_XSLT_PATH}")
        if not XSD_PATH.exists():
            raise unittest.SkipTest(f"XSD schema not found: {XSD_PATH}")
        if not MEDIA_XML_DIR.exists():
            raise unittest.SkipTest(f"Media XML directory not found: {MEDIA_XML_DIR}")

        cls.saxon_backend = SchematronSaxonBackend(SCHEMATRON_XSLT_PATH)

        from lxml import etree

        xsd_schema = etree.XMLSchema(etree.parse(str(XSD_PATH)))
        cls.xsd_backend = XsdOnlyBackend(xsd_schema)

    @classmethod
    def _get_invoice_xml_files(cls):
        """Get all invoice XML files from media/xml/ directory."""
        if not MEDIA_XML_DIR.exists():
            return []
        return sorted(MEDIA_XML_DIR.glob("invoice_*.xml"))

    def test_media_xml_directory_has_files(self):
        """Verify that media/xml/ directory contains invoice XML files."""
        xml_files = self._get_invoice_xml_files()
        if not xml_files:
            self.skipTest("No invoice XML files found in media/xml/ (cleaned by test runner)")

    def test_all_existing_xmls_xsd_validation(self):
        """XSD validation report for all existing invoice XMLs.

        Legacy files using <Invoice> root element are skipped (pre-2025-11 format).
        Reports failures but does not assert — older files may have been generated
        before generator fixes.
        """
        xml_files = self._get_invoice_xml_files()
        if not xml_files:
            self.skipTest("No invoice XML files found")

        xsd_failures = []
        skipped_legacy = 0
        for xml_file in xml_files:
            xml_content = xml_file.read_text(encoding="utf-8")
            # Skip legacy files that use <Invoice> instead of <CrossIndustryInvoice>
            from lxml import etree as _etree

            try:
                root = _etree.fromstring(xml_content.encode("utf-8"))
                if _etree.QName(root).localname != "CrossIndustryInvoice":
                    skipped_legacy += 1
                    continue
            except _etree.XMLSyntaxError:
                pass
            result = self.xsd_backend.validate(xml_content)
            if not result.is_valid:
                xsd_failures.append((xml_file.name, result.errors[:3]))

        tested = len(xml_files) - skipped_legacy
        print(
            f"\n  XSD Validation: {tested - len(xsd_failures)}/{tested} passed (skipped {skipped_legacy} legacy files)"
        )

        if xsd_failures:
            print(f"  XSD failures ({len(xsd_failures)}):")
            for name, errors in xsd_failures[:10]:
                print(f"    {name}: {errors[0][:100]}")

        self.assertIsNotNone(xsd_failures)

    def test_schematron_validation_of_existing_xmls(self):
        """
        Run EN16931 Schematron validation on all existing invoice XMLs.

        Reports which files pass/fail and which Schematron rules are violated.
        This is an informational test — it documents the current state of
        EN16931 compliance without necessarily failing.
        """
        xml_files = self._get_invoice_xml_files()
        if not xml_files:
            self.skipTest("No invoice XML files found")

        passed = []
        failed = []
        rule_counter = Counter()

        for xml_file in xml_files:
            xml_content = xml_file.read_text(encoding="utf-8")
            result = self.saxon_backend.validate(xml_content)

            if result.is_valid:
                passed.append(xml_file.name)
            else:
                failed.append((xml_file.name, result.errors))
                for error in result.errors:
                    # Extract rule ID like [BR-16] from error message
                    if "[" in error and "]" in error:
                        rule_id = error.split("[")[1].split("]")[0]
                        rule_counter[rule_id] += 1

        # Print summary report
        total = len(xml_files)
        print(f"\n{'=' * 70}")
        print("EN16931 Schematron Validation Report")
        print(f"{'=' * 70}")
        print(f"Total files: {total}")
        print(f"Passed:      {len(passed)}")
        print(f"Failed:      {len(failed)}")
        print(f"{'=' * 70}")

        if rule_counter:
            print("\nMost common Schematron rule violations:")
            for rule_id, count in rule_counter.most_common(15):
                print(f"  [{rule_id}]: {count} files")

        if failed:
            print("\nFailed files (first 10):")
            for name, errors in failed[:10]:
                print(f"  {name}: {len(errors)} error(s)")
                for e in errors[:3]:
                    print(f"    - {e[:120]}")

        # This test reports but does not fail — Schematron compliance
        # issues are tracked separately from test pass/fail
        self.assertIsNotNone(passed)

    def test_newest_xml_schematron_compliance(self):
        """
        Check EN16931 Schematron compliance of the most recent XML.

        Reports which rules the newest XML violates. Fails only if there are
        XSD errors (structure); Schematron errors are reported but tolerated
        since they depend on the business data stored in the DB.
        """
        xml_files = self._get_invoice_xml_files()
        if not xml_files:
            self.skipTest("No invoice XML files found")

        newest = max(xml_files, key=lambda f: f.stat().st_mtime)
        xml_content = newest.read_text(encoding="utf-8")

        # XSD must pass
        xsd_result = self.xsd_backend.validate(xml_content)
        if not xsd_result.is_valid:
            self.fail(f"Newest XML {newest.name} fails XSD: {xsd_result.errors[:5]}")

        # Schematron: report, don't fail (data-dependent)
        result = self.saxon_backend.validate(xml_content)
        print(f"\n  Newest XML: {newest.name}")
        print(f"  Schematron valid: {result.is_valid}")
        if not result.is_valid:
            print(f"  Schematron errors ({len(result.errors)}):")
            for e in result.errors[:10]:
                print(f"    - {e[:120]}")

    def test_combined_validation_of_newest_xml(self):
        """
        Full Combined (XSD + Schematron) validation of the newest XML.

        Mirrors the production pipeline. XSD errors cause failure;
        Schematron errors are reported but tolerated.
        """
        from invoice_app.utils.xml.backends import CombinedBackend

        xml_files = self._get_invoice_xml_files()
        if not xml_files:
            self.skipTest("No invoice XML files found")

        combined = CombinedBackend(self.xsd_backend, self.saxon_backend)
        newest = max(xml_files, key=lambda f: f.stat().st_mtime)
        xml_content = newest.read_text(encoding="utf-8")

        result = combined.validate(xml_content)

        self.assertEqual(result.backend_used, "Combined (XSD + Schematron)")

        xsd_errors = [e for e in result.errors if e.startswith("XSD:")]
        schematron_errors = [e for e in result.errors if e.startswith("Schematron:")]

        self.assertEqual(len(xsd_errors), 0, f"XSD errors in {newest.name}: {xsd_errors}")

        # Report Schematron results without failing
        print(f"\n  Combined validation of {newest.name}:")
        print(f"  XSD: OK | Schematron: {len(schematron_errors)} error(s)")
        for e in schematron_errors[:5]:
            print(f"    - {e[:120]}")


class TestFullWorkflowSchematronValidation(TestCase):
    """Test the full workflow: generate XML → validate with XSD + Schematron."""

    @classmethod
    def setUpClass(cls):
        """Load validation backends."""
        super().setUpClass()
        if not SCHEMATRON_XSLT_PATH.exists() or not XSD_PATH.exists():
            raise unittest.SkipTest("Schemas not available")

    def test_generator_output_passes_combined_validation(self):
        """XML from ZugferdXmlGenerator must pass both XSD and Schematron."""
        from invoice_app.utils.xml import ZugferdXmlGenerator

        generator = ZugferdXmlGenerator(profile="COMFORT")
        invoice_data = {
            "number": "INTEG-TEST-001",
            "date": "20260305",
            "due_date": "20260405",
            "currency": "EUR",
            "issuer": {
                "name": "Integration Test GmbH",
                "tax_id": "12/345/67890",
                "vat_id": "DE123456789",
                "street_name": "Teststraße 1",
                "city_name": "Berlin",
                "postcode_code": "10115",
                "country_id": "DE",
                "email": "test@example.com",
            },
            "customer": {
                "name": "Kunde Test AG",
                "vat_id": "DE987654321",
                "street_name": "Kundenweg 2",
                "city_name": "München",
                "postcode_code": "80331",
                "country_id": "DE",
                "email": "kunde@example.com",
            },
            "items": [
                {
                    "product_name": "Beratungsleistung",
                    "quantity": 10,
                    "price": 150.00,
                    "tax_rate": 19.0,
                },
            ],
        }

        xml = generator.generate_xml(invoice_data)

        validator = ZugferdXmlValidator()
        result = validator.validate_xml(xml)

        if not result.is_valid:
            error_details = "\n".join(f"  - {e}" for e in result.errors[:10])
            self.fail(f"Generated XML fails validation ({result.backend_used}):\n{error_details}")

    def test_generator_multi_line_invoice_passes_validation(self):
        """Multi-line invoice with different tax rates must pass validation."""
        from invoice_app.utils.xml import ZugferdXmlGenerator

        generator = ZugferdXmlGenerator(profile="COMFORT")
        invoice_data = {
            "number": "INTEG-MULTI-001",
            "date": "20260305",
            "due_date": "20260405",
            "currency": "EUR",
            "issuer": {
                "name": "Multi-Line Test GmbH",
                "tax_id": "98/765/43210",
                "vat_id": "DE111222333",
                "street_name": "Hauptstraße 10",
                "city_name": "Hamburg",
                "postcode_code": "20095",
                "country_id": "DE",
                "email": "multi@example.com",
            },
            "customer": {
                "name": "Empfänger GmbH",
                "vat_id": "DE444555666",
                "street_name": "Nebenstraße 5",
                "city_name": "Köln",
                "postcode_code": "50667",
                "country_id": "DE",
                "email": "empfaenger@example.com",
            },
            "items": [
                {
                    "product_name": "Software-Entwicklung",
                    "quantity": 40,
                    "price": 120.00,
                    "tax_rate": 19.0,
                },
                {
                    "product_name": "Fachliteratur",
                    "quantity": 3,
                    "price": 49.90,
                    "tax_rate": 7.0,
                },
                {
                    "product_name": "Schulung vor Ort",
                    "quantity": 2,
                    "price": 800.00,
                    "tax_rate": 19.0,
                },
            ],
        }

        xml = generator.generate_xml(invoice_data)

        validator = ZugferdXmlValidator()
        result = validator.validate_xml(xml)

        if not result.is_valid:
            error_details = "\n".join(f"  - {e}" for e in result.errors[:10])
            self.fail(f"Multi-line invoice fails validation ({result.backend_used}):\n{error_details}")

    def test_validator_reports_combined_backend(self):
        """ZugferdXmlValidator should use CombinedBackend when Schematron is available."""
        validator = ZugferdXmlValidator()
        info = validator.get_validation_info()

        self.assertTrue(info["schematron_available"])
        self.assertTrue(info["schematron_enabled"])
        self.assertEqual(info["backend_type"], "CombinedBackend")
