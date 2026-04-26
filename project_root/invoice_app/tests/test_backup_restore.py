"""
Tests for Backup & Restore functionality (Task 1.4).

Tests cover:
- backup_database management command (Django level)
- Backup file creation and integrity
- Metadata generation
- Audit log entry for backups
- Checksum verification
"""

import gzip
import json
import os
import shutil
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from invoice_app.models import AuditLog


class BackupDatabaseCommandTest(TestCase):
    """Test the backup_database management command."""

    def setUp(self):
        self.backup_dir = tempfile.mkdtemp(prefix="erechnung_test_backup_")

    def tearDown(self):
        shutil.rmtree(self.backup_dir, ignore_errors=True)

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_creates_db_file(self, mock_run):
        """Backup command creates a gzipped database dump."""
        # Simulate successful pg_dump
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"-- PostgreSQL database dump\nCREATE TABLE test;\nINSERT INTO test VALUES (1);\n" * 10,
            stderr=b"",
        )

        out = StringIO()
        call_command(
            "backup_database",
            "--db-only",
            "--output",
            self.backup_dir,
            stdout=out,
        )

        # Find the created backup file
        db_files = [f for f in os.listdir(self.backup_dir) if f.startswith("db_") and f.endswith(".sql.gz")]
        self.assertEqual(len(db_files), 1, "Expected exactly one DB backup file")

        db_file = os.path.join(self.backup_dir, db_files[0])
        self.assertTrue(os.path.getsize(db_file) > 0, "Backup file should not be empty")

        # Verify it's valid gzip
        with gzip.open(db_file, "rb") as f:
            content = f.read()
        self.assertIn(b"PostgreSQL database dump", content)

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_creates_checksum(self, mock_run):
        """Backup command creates a SHA256 checksum file."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"-- PostgreSQL database dump\nCREATE TABLE test;\n" * 10,
            stderr=b"",
        )

        call_command(
            "backup_database",
            "--db-only",
            "--output",
            self.backup_dir,
            stdout=StringIO(),
        )

        sha_files = [f for f in os.listdir(self.backup_dir) if f.endswith(".sha256")]
        self.assertEqual(len(sha_files), 1, "Expected exactly one checksum file")

        # Verify checksum format
        sha_path = os.path.join(self.backup_dir, sha_files[0])
        with open(sha_path) as f:
            content = f.read().strip()
        parts = content.split("  ")
        self.assertEqual(len(parts), 2, "Checksum file should have 'hash  filename' format")
        self.assertEqual(len(parts[0]), 64, "SHA256 hash should be 64 chars")

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_creates_audit_log(self, mock_run):
        """Backup creates a GoBD-compliant audit log entry."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"-- PostgreSQL database dump\nCREATE TABLE test;\n" * 10,
            stderr=b"",
        )

        initial_count = AuditLog.objects.filter(action=AuditLog.ActionType.BACKUP).count()

        call_command(
            "backup_database",
            "--db-only",
            "--output",
            self.backup_dir,
            stdout=StringIO(),
        )

        backup_logs = AuditLog.objects.filter(action=AuditLog.ActionType.BACKUP)
        self.assertEqual(
            backup_logs.count(),
            initial_count + 1,
            "Should create one BACKUP audit log entry",
        )

        log_entry = backup_logs.order_by("-timestamp").first()
        self.assertEqual(log_entry.object_type, "database")
        self.assertEqual(log_entry.severity, AuditLog.Severity.MEDIUM)
        self.assertIn("backup_dir", log_entry.new_values)

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_json_output(self, mock_run):
        """Backup with --json flag returns valid JSON."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"-- PostgreSQL database dump\nCREATE TABLE test;\n" * 10,
            stderr=b"",
        )

        out = StringIO()
        err = StringIO()
        call_command(
            "backup_database",
            "--db-only",
            "--json",
            "--output",
            self.backup_dir,
            stdout=out,
            stderr=err,
        )

        # The JSON output may be preceded by progress messages on stderr
        output = out.getvalue().strip()
        # Find the JSON object in the output (starts with {)
        json_start = output.find("{")
        self.assertGreater(json_start, -1, f"No JSON found in output: {output!r}")
        result = json.loads(output[json_start:])
        self.assertTrue(result["success"])
        self.assertIn("database", result)
        self.assertIn("size_bytes", result["database"])
        self.assertIn("checksum", result["database"])
        self.assertEqual(len(result["database"]["checksum"]), 64)

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_fails_on_empty_dump(self, mock_run):
        """Backup fails if pg_dump returns empty output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"",
            stderr=b"",
        )

        with self.assertRaises(CommandError) as ctx:
            call_command(
                "backup_database",
                "--db-only",
                "--output",
                self.backup_dir,
                stdout=StringIO(),
            )
        self.assertIn("suspiciously small", str(ctx.exception))

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_fails_on_pgdump_error(self, mock_run):
        """Backup fails if pg_dump returns non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=b"",
            stderr=b"pg_dump: error: connection refused",
        )

        with self.assertRaises(CommandError) as ctx:
            call_command(
                "backup_database",
                "--db-only",
                "--output",
                self.backup_dir,
                stdout=StringIO(),
            )
        self.assertIn("pg_dump failed", str(ctx.exception))

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_media_with_files(self, mock_run):
        """Backup includes media files when they exist."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"-- PostgreSQL database dump\nCREATE TABLE test;\n" * 10,
            stderr=b"",
        )

        # Create a temporary media directory with test files
        media_dir = os.path.join(self.backup_dir, "media")
        os.makedirs(os.path.join(media_dir, "invoices/pdf"), exist_ok=True)
        with open(os.path.join(media_dir, "invoices/pdf/test.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 test content")

        with override_settings(MEDIA_ROOT=media_dir):
            out = StringIO()
            call_command(
                "backup_database",
                "--output",
                self.backup_dir,
                stdout=out,
            )

        media_files = [f for f in os.listdir(self.backup_dir) if f.startswith("media_") and f.endswith(".tar.gz")]
        self.assertEqual(len(media_files), 1, "Expected one media backup file")

    @patch("invoice_app.management.commands.backup_database.subprocess.run")
    def test_backup_db_only_skips_media(self, mock_run):
        """--db-only flag skips media backup."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"-- PostgreSQL database dump\nCREATE TABLE test;\n" * 10,
            stderr=b"",
        )

        out = StringIO()
        call_command(
            "backup_database",
            "--db-only",
            "--json",
            "--output",
            self.backup_dir,
            stdout=out,
        )

        result = json.loads(out.getvalue())
        self.assertIsNone(result["media"])

        media_files = [f for f in os.listdir(self.backup_dir) if f.startswith("media_")]
        self.assertEqual(len(media_files), 0, "Should not create media backup")


class BackupChecksumVerificationTest(TestCase):
    """Test checksum verification logic."""

    def test_sha256_calculation_is_deterministic(self):
        """Same file content always produces same hash."""
        from invoice_app.management.commands.backup_database import Command

        cmd = Command()
        tmpdir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(tmpdir, "test.bin")
            with open(test_file, "wb") as f:
                f.write(b"deterministic content for hashing")

            hash1 = cmd._sha256(test_file)
            hash2 = cmd._sha256(test_file)

            self.assertEqual(hash1, hash2)
            self.assertEqual(len(hash1), 64)
        finally:
            shutil.rmtree(tmpdir)

    def test_sha256_detects_changes(self):
        """Different content produces different hash."""
        from invoice_app.management.commands.backup_database import Command

        cmd = Command()
        tmpdir = tempfile.mkdtemp()
        try:
            file1 = os.path.join(tmpdir, "file1.bin")
            file2 = os.path.join(tmpdir, "file2.bin")
            with open(file1, "wb") as f:
                f.write(b"content version 1")
            with open(file2, "wb") as f:
                f.write(b"content version 2")

            self.assertNotEqual(cmd._sha256(file1), cmd._sha256(file2))
        finally:
            shutil.rmtree(tmpdir)
