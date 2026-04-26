"""
Django Management Command: backup_database

Creates a database backup and optionally media backup.
Logs the backup event to the GoBD-compliant AuditLog.

Usage:
    python manage.py backup_database
    python manage.py backup_database --db-only
    python manage.py backup_database --output /custom/path
    python manage.py backup_database --retention 30
"""

import gzip
import hashlib
import json
import os
import subprocess
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a backup of the database and media files (GoBD-compliant)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output directory for backup (default: <project>/backups/<date>)",
        )
        parser.add_argument(
            "--db-only",
            action="store_true",
            help="Only backup database, skip media files",
        )
        parser.add_argument(
            "--retention",
            type=int,
            default=30,
            help="Days to keep old backups (0 = keep all, default: 30)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output result as JSON",
        )

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json = options["json"]

        # Determine backup directory
        if options["output"]:
            backup_dir = options["output"]
        else:
            base_dir = os.path.join(settings.BASE_DIR, os.pardir, os.pardir, "backups")
            backup_dir = os.path.join(os.path.abspath(base_dir), datetime.now().strftime("%Y%m%d"))

        os.makedirs(backup_dir, exist_ok=True)

        result = {
            "timestamp": timestamp,
            "backup_dir": backup_dir,
            "database": None,
            "media": None,
            "success": False,
        }

        try:
            # --- Database Backup ---
            db_file = os.path.join(backup_dir, f"db_{timestamp}.sql.gz")
            self._backup_database(db_file)
            result["database"] = {
                "file": db_file,
                "size_bytes": os.path.getsize(db_file),
                "checksum": self._sha256(db_file),
            }

            # --- Media Backup ---
            if not options["db_only"]:
                media_root = getattr(settings, "MEDIA_ROOT", None)
                if media_root and os.path.exists(media_root):
                    media_files = []
                    for _dirpath, _, filenames in os.walk(media_root):
                        media_files.extend(filenames)

                    if media_files:
                        media_file = os.path.join(backup_dir, f"media_{timestamp}.tar.gz")
                        self._backup_media(media_root, media_file)
                        result["media"] = {
                            "file": media_file,
                            "size_bytes": os.path.getsize(media_file),
                            "file_count": len(media_files),
                            "checksum": self._sha256(media_file),
                        }
                    else:
                        result["media"] = {"note": "No media files found"}
                else:
                    result["media"] = {"note": "Media directory does not exist"}

            # --- Audit Log Entry ---
            self._log_audit_event(result)

            result["success"] = True

            if output_json:
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS(f"Backup completed: {backup_dir}"))
                self.stdout.write(
                    f"  Database: {os.path.basename(db_file)} ({result['database']['size_bytes']} bytes)"
                )
                if result["media"] and "file" in result.get("media", {}):
                    self.stdout.write(
                        f"  Media: {os.path.basename(result['media']['file'])} ({result['media']['file_count']} files)"
                    )

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            if output_json:
                self.stdout.write(json.dumps(result, indent=2))
            raise CommandError(f"Backup failed: {e}") from e

    def _backup_database(self, output_path):
        """Create a gzipped pg_dump of the current database."""
        db_settings = settings.DATABASES["default"]

        env = os.environ.copy()
        env["PGPASSWORD"] = db_settings["PASSWORD"]

        cmd = [
            "pg_dump",
            "-h",
            db_settings["HOST"],
            "-p",
            str(db_settings["PORT"]),
            "-U",
            db_settings["USER"],
            "-d",
            db_settings["NAME"],
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
        ]

        self.stderr.write(f"  Running pg_dump for {db_settings['NAME']}...")

        proc = subprocess.run(
            cmd,
            capture_output=True,
            env=env,
            timeout=300,  # 5 minute timeout
            check=False,
        )

        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            raise CommandError(f"pg_dump failed: {stderr}")

        if len(proc.stdout) < 100:
            raise CommandError("pg_dump output is suspiciously small")

        # Compress and write
        with gzip.open(output_path, "wb") as f:
            f.write(proc.stdout)

        # Write checksum
        checksum = self._sha256(output_path)
        with open(f"{output_path}.sha256", "w") as f:
            f.write(f"{checksum}  {os.path.basename(output_path)}\n")

    def _backup_media(self, media_root, output_path):
        """Create a tar.gz of the media directory."""
        import tarfile

        self.stderr.write(f"  Archiving media from {media_root}...")

        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(media_root, arcname="media")

        # Write checksum
        checksum = self._sha256(output_path)
        with open(f"{output_path}.sha256", "w") as f:
            f.write(f"{checksum}  {os.path.basename(output_path)}\n")

    def _sha256(self, filepath):
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _log_audit_event(self, result):
        """Log backup event to AuditLog (GoBD compliance)."""
        try:
            from invoice_app.models.audit import AuditLog

            db_size = result.get("database", {}).get("size_bytes", 0) if result.get("database") else 0
            media_info = result.get("media", {})
            media_count = media_info.get("file_count", 0) if isinstance(media_info, dict) else 0

            AuditLog.objects.create(
                action=AuditLog.ActionType.BACKUP,
                severity=AuditLog.Severity.MEDIUM,
                object_type="database",
                description=(f"Database backup created: DB {db_size} bytes, {media_count} media files"),
                new_values={
                    "backup_dir": result.get("backup_dir", ""),
                    "database_size": db_size,
                    "media_file_count": media_count,
                    "timestamp": result.get("timestamp", ""),
                },
            )
        except Exception as e:
            # Don't fail the backup if audit logging fails
            self.stderr.write(self.style.WARNING(f"Audit log entry failed: {e}"))
