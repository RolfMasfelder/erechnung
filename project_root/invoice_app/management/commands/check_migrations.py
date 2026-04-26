"""
Management command: check_migrations

Validates migration health before deployment:
- Checks for unapplied migrations
- Validates all migrations have reverse operations
- Detects common anti-patterns in migration files
- Reports migration status summary
"""

import ast
import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Check migration health: unapplied migrations, reversibility, anti-patterns"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            type=str,
            default="invoice_app",
            help="App label to check (default: invoice_app)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail on warnings (non-zero exit code)",
        )

    def handle(self, *args, **options):
        app_label = options["app"]
        strict = options["strict"]

        self.stdout.write(self.style.MIGRATE_HEADING("Migration Health Check"))
        self.stdout.write("=" * 60)

        errors = []
        warnings = []

        # 1. Check unapplied migrations
        self._check_unapplied(app_label, errors)

        # 2. Check reversibility
        self._check_reversibility(app_label, warnings)

        # 3. Check anti-patterns in migration files
        self._check_anti_patterns(app_label, warnings)

        # 4. Check for pending model changes
        self._check_pending_changes(app_label, warnings)

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 60)

        if errors:
            for err in errors:
                self.stdout.write(self.style.ERROR(f"  ERROR: {err}"))

        if warnings:
            for warn in warnings:
                self.stdout.write(self.style.WARNING(f"  WARNING: {warn}"))

        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS("  All checks passed!"))
        elif not errors:
            self.stdout.write(self.style.SUCCESS(f"  No errors. {len(warnings)} warning(s)."))
        else:
            self.stdout.write(self.style.ERROR(f"  {len(errors)} error(s), {len(warnings)} warning(s)."))

        if errors or (strict and warnings):
            raise SystemExit(1)

    def _check_unapplied(self, app_label, errors):
        """Check for unapplied migrations."""
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("1. Unapplied Migrations"))

        loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        app_migrations = [key for key in loader.migrated_apps if key == app_label]

        if not app_migrations:
            self.stdout.write(f"   No migrations found for '{app_label}'")
            return

        graph = loader.graph
        unapplied = []

        for app, name in loader.graph.leaf_nodes():
            if app != app_label:
                continue
            plan = graph.forwards_plan((app, name))
            for migration_key in plan:
                if migration_key[0] == app_label and migration_key not in applied:
                    unapplied.append(migration_key[1])

        if unapplied:
            for name in unapplied:
                errors.append(f"Unapplied migration: {app_label}.{name}")
                self.stdout.write(self.style.ERROR(f"   [ ] {name}"))
        else:
            # Show applied count
            applied_count = sum(1 for key in applied if key[0] == app_label)
            self.stdout.write(self.style.SUCCESS(f"   All {applied_count} migrations applied ✓"))

    def _check_reversibility(self, app_label, warnings):
        """Check that all RunPython operations have reverse functions."""
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("2. Migration Reversibility"))

        migrations_dir = self._get_migrations_dir(app_label)
        if not migrations_dir:
            self.stdout.write("   Could not find migrations directory")
            return

        issues = 0
        checked = 0

        for filename in sorted(os.listdir(migrations_dir)):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            filepath = os.path.join(migrations_dir, filename)
            checked += 1

            try:
                with open(filepath, encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = node.func
                        # Check for RunPython calls
                        if isinstance(func, ast.Attribute) and func.attr == "RunPython":
                            # RunPython should have at least 2 positional args
                            if len(node.args) < 2:
                                # Check for reverse_code keyword
                                has_reverse = any(kw.arg == "reverse_code" for kw in node.keywords)
                                if not has_reverse:
                                    warnings.append(f"{filename}: RunPython without reverse function")
                                    self.stdout.write(
                                        self.style.WARNING(f"   ⚠ {filename}: RunPython without reverse")
                                    )
                                    issues += 1

            except (SyntaxError, OSError) as e:
                warnings.append(f"{filename}: Could not parse — {e}")

        if issues == 0:
            self.stdout.write(self.style.SUCCESS(f"   All {checked} migrations reversible ✓"))

    def _check_anti_patterns(self, app_label, warnings):
        """Detect common anti-patterns in migration files."""
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("3. Anti-Pattern Detection"))

        migrations_dir = self._get_migrations_dir(app_label)
        if not migrations_dir:
            return

        patterns = [
            (".objects.all()", "Unbounded queryset — use batch processing"),
            ("from invoice_app.models", "Direct model import — use apps.get_model()"),
            ("from invoice_app.services", "Service import in migration — avoid app imports"),
            (".save()", "Individual save() — use bulk_update()"),
        ]

        issues = 0

        for filename in sorted(os.listdir(migrations_dir)):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            filepath = os.path.join(migrations_dir, filename)

            try:
                with open(filepath, encoding="utf-8") as f:
                    lines = f.readlines()

                for lineno, line in enumerate(lines, 1):
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue

                    for pattern, description in patterns:
                        if pattern in line:
                            # Allow .objects.all().delete() in reverse migrations
                            if ".objects.all().delete()" in line:
                                continue
                            # Allow .objects.all() in count-like context
                            if ".objects.all().update(" in line:
                                continue

                            msg = f"{filename}:{lineno}: {description}"
                            warnings.append(msg)
                            self.stdout.write(self.style.WARNING(f"   ⚠ {msg}"))
                            issues += 1

            except OSError:
                pass

        if issues == 0:
            self.stdout.write(self.style.SUCCESS("   No anti-patterns detected ✓"))

    def _check_pending_changes(self, app_label, warnings):
        """Check if models have changes that need a new migration."""
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("4. Pending Model Changes"))

        from io import StringIO

        from django.core.management import call_command

        out = StringIO()

        try:
            call_command(
                "makemigrations",
                app_label,
                "--check",
                "--dry-run",
                stdout=out,
                stderr=out,
            )
            self.stdout.write(self.style.SUCCESS("   No pending model changes ✓"))
        except SystemExit:
            warnings.append(f"Model changes detected — run makemigrations {app_label}")
            self.stdout.write(self.style.WARNING(f"   ⚠ Pending model changes — run: makemigrations {app_label}"))

    def _get_migrations_dir(self, app_label):
        """Get the filesystem path to an app's migrations directory."""
        try:
            app_config = apps.get_app_config(app_label)
            migrations_module = f"{app_config.name}.migrations"
            import importlib

            mod = importlib.import_module(migrations_module)
            return os.path.dirname(mod.__file__)
        except (LookupError, ImportError):
            return None
