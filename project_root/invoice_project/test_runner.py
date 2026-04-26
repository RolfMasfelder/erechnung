"""
Custom test runner that cleans up test artifacts before each run.

Removes generated XML files from media/xml/ that accumulate during tests
and pollute integration test results (e.g. test_schematron_integration).

This runner is ONLY invoked by `manage.py test` — never in production.
"""

from pathlib import Path

from django.conf import settings
from django.test.runner import DiscoverRunner


class ERehnungTestRunner(DiscoverRunner):
    """Test runner with pre-run cleanup of test artifacts."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._clean_media_xml()
        self._disable_ssl_redirect()

    def _disable_ssl_redirect(self):
        """Disable SECURE_SSL_REDIRECT during tests.

        In production (DJANGO_ENV=production), SSL redirect is enabled.
        The Django test client uses HTTP, so SSL redirect causes 301 on every request.
        """
        settings.SECURE_SSL_REDIRECT = False

    def _clean_media_xml(self):
        """Remove generated invoice XMLs from media/xml/ before tests."""
        media_xml = Path(settings.BASE_DIR) / "media" / "xml"
        if not media_xml.exists():
            return

        removed = 0
        for xml_file in media_xml.glob("invoice_*.xml"):
            xml_file.unlink()
            removed += 1

        if removed:
            print(f"\n  Cleaned up {removed} invoice XML files from {media_xml}/")
