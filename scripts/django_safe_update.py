#!/usr/bin/env python3
"""
Django-Safe Dependency Update Guide

This script provides a practical approach to safely updating your 37 outdated packages
by grouping them according to compatibility and risk levels.

Usage:
    python django_safe_update.py [--apply-phase PHASE] [--docker]
"""

import argparse
import re
from datetime import datetime
from pathlib import Path


class DjangoSafeUpdater:
    """Safe update strategy for Django eRechnung project."""

    def __init__(self):
        self.requirements_file = Path("requirements.txt")

        # Define update phases based on your current packages
        self.update_phases = {
            "phase1_tools": {
                "description": "🟢 Development Tools & Testing (Safest)",
                "packages": {
                    "black": "25.1.0",  # Already latest
                    "coverage": "7.10.1",
                    "flake8": "7.3.0",
                    "isort": "6.0.1",
                    "pre-commit": "4.2.0",
                    "pylint": "3.3.7",
                    "pytest": "8.4.1",
                    "pytest-django": "4.11.1",
                    "ruff": "0.12.7",
                    "safety": "3.6.0",  # Already latest
                    "setuptools": "80.9.0",
                    "factory-boy": "3.3.3",
                },
                "risk": "LOW",
                "notes": "These are development tools that rarely break functionality.",
            },
            "phase2_utilities": {
                "description": "🟡 Utility Libraries (Medium Risk)",
                "packages": {
                    "python-dotenv": "1.1.1",
                    "environs": "14.2.0",
                    "whitenoise": "6.9.0",
                    "uritemplate": "4.2.0",
                    "dj-database-url": "3.0.1",
                    "sentry-sdk": "2.34.1",
                },
                "risk": "MEDIUM",
                "notes": "Configuration and utility packages. Test thoroughly.",
            },
            "phase3_django_ecosystem": {
                "description": "🟡 Django Ecosystem (Coordinated Update)",
                "packages": {
                    # Keep Django at 5.1.x for stability - 5.2.4 is major jump
                    "django": "5.1.5",  # Latest 5.1.x instead of 5.2.4
                    "djangorestframework": "3.16.0",
                    "django-debug-toolbar": "6.0.0",
                    "django-extensions": "4.1.0",
                    "django-filter": "25.1",
                    "django-redis": "6.0.0",
                    "djangorestframework-simplejwt": "5.5.1",
                    "drf-yasg": "1.21.10",
                    "django-cors-headers": "4.7.0",
                    "django-csp": "4.0",
                },
                "risk": "MEDIUM",
                "notes": "Update Django ecosystem together. Test all Django features!",
            },
            "phase4_authentication": {
                "description": "🔴 Authentication (High Risk)",
                "packages": {
                    # django-allauth: MAJOR version jump from 0.57.0 to 65.x is BREAKING
                    "django-allauth": "0.64.0",  # Safer incremental update
                    "django-axes": "8.0.0",
                },
                "risk": "HIGH",
                "notes": "Authentication changes can break user login! Test extensively.",
            },
            "phase5_infrastructure": {
                "description": "🔴 Infrastructure & Processing (Highest Risk)",
                "packages": {
                    "celery": "5.5.3",
                    "redis": "6.2.0",
                    "gunicorn": "23.0.0",
                    "psycopg2-binary": "2.9.10",  # Keep stable - already good version
                },
                "risk": "HIGH",
                "notes": "Core infrastructure. Update in staging first!",
            },
            "phase6_file_processing": {
                "description": "🔴 PDF/XML Processing (Critical for eRechnung)",
                "packages": {
                    "lxml": "6.0.0",  # Major version jump!
                    "pillow": "11.3.0",
                    "reportlab": "4.4.3",
                    "pikepdf": "9.10.2",
                    "xmlschema": "4.1.0",  # Major version jump!
                    # factur-x: 2.0.0 to 3.8 is MAJOR - likely breaking
                    "factur-x": "2.8.0",  # Safer incremental update
                },
                "risk": "CRITICAL",
                "notes": "These handle your core eRechnung XML/PDF generation. Test invoice generation thoroughly!",
            },
        }

        # Packages to AVOID updating (known breaking changes)
        self.avoid_updates = {
            "django": "5.2.4",  # Too big a jump from 5.1.0
            "django-allauth": "65.10.0",  # MAJOR breaking changes
            "factur-x": "3.8",  # Likely breaking for ZUGFeRD XML
            "lxml": "6.0.0",  # Major version - test carefully first
            "xmlschema": "4.1.0",  # Major version - may break XML validation
        }

    def create_backup(self):
        """Create timestamped backup of requirements.txt."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = Path(f"requirements_backup_{timestamp}.txt")

        with open(self.requirements_file) as f:
            content = f.read()

        with open(backup_file, "w") as f:
            f.write(content)

        print(f"📁 Backup created: {backup_file}")
        return backup_file

    def show_update_plan(self):
        """Show the complete update plan."""
        print("=" * 80)
        print("🚀 DJANGO eRechnung SAFE UPDATE PLAN")
        print("=" * 80)

        print("\n📋 STRATEGY: Phased Updates with Testing Between Each Phase")
        print("\n⚠️  CRITICAL WARNINGS:")
        print("   • Django 5.1.0 → 5.2.4 is a MAJOR jump - using 5.1.5 instead")
        print("   • django-allauth 0.57.0 → 65.x has BREAKING CHANGES - using 0.64.0")
        print("   • factur-x 2.0.0 → 3.8 may break ZUGFeRD XML - using 2.8.0")
        print("   • Always test invoice generation after XML/PDF library updates")

        total_packages = sum(len(phase["packages"]) for phase in self.update_phases.values())
        print(f"\n📊 TOTAL: {total_packages} packages to update across 6 phases")

        for _phase_name, phase_info in self.update_phases.items():
            risk_color = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "🚨"}
            color = risk_color.get(phase_info["risk"], "⚪")

            print(f"\n{color} {phase_info['description']}")
            print(f"   Risk Level: {phase_info['risk']}")
            print(f"   Packages: {len(phase_info['packages'])}")
            print(f"   Notes: {phase_info['notes']}")

            for package, version in phase_info["packages"].items():
                print(f"      • {package}: → {version}")

    def apply_phase(self, phase_name):
        """Apply updates for a specific phase."""
        if phase_name not in self.update_phases:
            print(f"❌ Unknown phase: {phase_name}")
            print(f"Available phases: {list(self.update_phases.keys())}")
            return False

        phase_info = self.update_phases[phase_name]
        packages = phase_info["packages"]

        print(f"\n🔄 Applying {phase_info['description']}")
        print(f"📦 Updating {len(packages)} packages...")

        # Read current requirements
        with open(self.requirements_file) as f:
            content = f.read()

        updated_content = content

        # Update each package
        for package, new_version in packages.items():
            pattern = rf"^{re.escape(package)}==.*$"
            replacement = f"{package}=={new_version}"
            updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
            print(f"   ✅ {package} → {new_version}")

        # Write updated requirements
        with open(self.requirements_file, "w") as f:
            f.write(updated_content)

        print("\n💡 NEXT STEPS:")
        print("   1. Install updates: docker compose exec web pip install -r requirements.txt")
        print("   2. Run automated tests: ./run_tests_docker.sh")
        print("   3. Verify specific test results based on risk level:")

        if phase_info["risk"] == "LOW":
            print("      • All 87+ tests should pass (dev tools rarely break functionality)")
        elif phase_info["risk"] == "MEDIUM" and "django" in [pkg.lower() for pkg in packages.keys()]:
            print("      • Focus on Django core tests: models, API, CRUD operations")
            print("      • Verify RBAC functionality still works")
        elif phase_info["risk"] in ["HIGH", "CRITICAL"]:
            print("      • Critical: All authentication tests must pass (RBAC, UserRole, UserProfile)")
            print("      • Critical: All PDF/XML generation tests must pass (InvoiceService, ZUGFeRD)")
            print("      • Critical: Integration tests for complete eRechnung workflow")

        print("   4. If ALL tests pass, proceed to next phase")
        print("   5. If ANY test fails, restore from backup and investigate")

        return True

    def generate_commands(self):
        """Generate Docker commands for each phase."""
        print("\n" + "=" * 80)
        print("📝 PHASE-BY-PHASE COMMANDS")
        print("=" * 80)

        for i, (phase_name, phase_info) in enumerate(self.update_phases.items(), 1):
            print(f"\n--- PHASE {i}: {phase_info['description']} ---")
            print("# Create backup (before first phase only)")
            if i == 1:
                print("cp requirements.txt requirements_backup_$(date +%Y%m%d_%H%M%S).txt")

            print(f"\n# Apply phase {i} updates")
            print(f"python django_safe_update.py --apply-phase {phase_name}")

            print("\n# Install updated packages")
            print("docker compose exec web pip install -r requirements.txt")

            print("\n# Run comprehensive automated test suite (87+ tests)")
            print("./run_tests_docker.sh")

            if phase_info["risk"] in ["HIGH", "CRITICAL"]:
                print(f"\n# For {phase_info['risk']} risk: Verify critical test categories")
                print("# Ensure these specific test groups ALL pass:")
                if "auth" in phase_name or "django" in phase_name:
                    print("# - RBAC and authentication tests (UserRole, UserProfile)")
                if "file_processing" in phase_name or "django" in phase_name:
                    print("# - PDF/XML generation tests (InvoiceService, ZUGFeRD)")
                    print("# - Integration tests for complete eRechnung workflow")

            print("\n# SUCCESS CRITERIA: ALL 87+ tests must pass")
            print("# If ANY test fails, restore backup:")
            print("# cp requirements_backup_TIMESTAMP.txt requirements.txt")
            print("# docker compose exec web pip install -r requirements.txt")


def main():
    parser = argparse.ArgumentParser(description="Django-safe dependency updater")
    parser.add_argument("--apply-phase", help="Apply updates for specific phase")
    parser.add_argument("--show-commands", action="store_true", help="Show all commands")
    parser.add_argument("--backup-only", action="store_true", help="Create backup only")

    args = parser.parse_args()

    updater = DjangoSafeUpdater()

    if args.backup_only:
        updater.create_backup()
        return

    if args.show_commands:
        updater.generate_commands()
        return

    if args.apply_phase:
        updater.create_backup()
        success = updater.apply_phase(args.apply_phase)
        if not success:
            return 1
    else:
        updater.show_update_plan()
        print("\n💡 TO GET STARTED:")
        print("   python django_safe_update.py --apply-phase phase1_tools")
        print("   python django_safe_update.py --show-commands  # See all commands")


if __name__ == "__main__":
    main()
