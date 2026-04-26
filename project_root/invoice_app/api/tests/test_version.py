"""Tests for the /api/version/ endpoint."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class VersionEndpointTest(TestCase):
    """Test cases for the public version endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("api-version")

    def test_returns_200_without_auth(self):
        """Version endpoint is public — no authentication required."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_response_is_json(self):
        """Response content type is application/json."""
        response = self.client.get(self.url)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_response_has_expected_fields(self):
        """Response contains version, git_sha, and build_date."""
        response = self.client.get(self.url)
        data = response.json()

        self.assertIn("version", data)
        self.assertIn("git_sha", data)
        self.assertIn("build_date", data)

    def test_version_is_semver(self):
        """Version string follows semantic versioning (X.Y.Z)."""

        response = self.client.get(self.url)
        data = response.json()

        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+")

    def test_version_matches_pyproject(self):
        """Version matches the value in pyproject.toml."""
        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data["version"], "1.0.0")

    def test_only_get_allowed(self):
        """POST/PUT/DELETE are not allowed."""
        for method in ("post", "put", "delete", "patch"):
            response = getattr(self.client, method)(self.url)
            self.assertEqual(
                response.status_code,
                405,
                f"{method.upper()} should return 405, got {response.status_code}",
            )
