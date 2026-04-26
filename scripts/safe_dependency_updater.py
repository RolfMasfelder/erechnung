#!/usr/bin/env python3
"""
Safe Dependency Updater

This script helps you safely update dependencies by:
1. Analyzing compatibility between packages
2. Grouping updates by risk level
3. Testing updates incrementally
4. Creating backup restore points

Usage:
    python safe_dependency_updater.py [options]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class PackageUpdate:
    """Information about a package update."""

    name: str
    current_version: str
    latest_version: str
    risk_level: str  # 'low', 'medium', 'high'
    dependencies: list[str]
    dependents: list[str]
    changelog_url: str = ""
    breaking_changes: list[str] = None

    def __post_init__(self):
        if self.breaking_changes is None:
            self.breaking_changes = []


class SafeDependencyUpdater:
    """Safely update dependencies with compatibility checking."""

    def __init__(self, use_docker: bool = False, dry_run: bool = False):
        self.use_docker = use_docker
        self.dry_run = dry_run
        self.project_root = Path(__file__).parent
        self.requirements_file = self.project_root / "requirements.txt"
        self.backup_dir = self.project_root / "dependency_backups"

        # Core Django ecosystem packages that should be updated together
        self.django_ecosystem = {
            "django",
            "djangorestframework",
            "django-allauth",
            "django-axes",
            "django-cors-headers",
            "django-csp",
            "django-debug-toolbar",
            "django-extensions",
            "django-filter",
            "django-redis",
            "djangorestframework-simplejwt",
            "drf-spectacular",
        }

        # Packages that are usually safe to update independently
        self.safe_packages = {
            "black",
            "coverage",
            "flake8",
            "isort",
            "pre-commit",
            "pylint",
            "pytest",
            "pytest-django",
            "ruff",
            "safety",
            "setuptools",
            "python-dotenv",
            "whitenoise",
            "environs",
            "factory-boy",
        }

        # Packages that require careful testing due to potential breaking changes
        self.risky_packages = {
            "celery",
            "redis",
            "lxml",
            "pillow",
            "reportlab",
            "xmlschema",
            "psycopg2-binary",
            "gunicorn",
            "sentry-sdk",
            "pikepdf",
            "factur-x",
        }

    def run_command(self, cmd: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run command either locally or in Docker container."""
        if self.use_docker:
            docker_cmd = ["docker", "compose", "exec", "web"] + cmd
            return subprocess.run(docker_cmd, capture_output=capture_output, text=True, cwd=self.project_root)
        else:
            return subprocess.run(cmd, capture_output=capture_output, text=True, cwd=self.project_root)

    def create_backup(self) -> Path:
        """Create a backup of current requirements.txt."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"requirements_backup_{timestamp}.txt"

        self.backup_dir.mkdir(exist_ok=True)
        shutil.copy2(self.requirements_file, backup_file)

        print(f"📁 Created backup: {backup_file}")
        return backup_file

    def parse_requirements(self) -> dict[str, str]:
        """Parse requirements.txt and extract current versions."""
        requirements = {}

        with open(self.requirements_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    match = re.match(r"^([a-zA-Z0-9._-]+)([><=!~]+)(.+)$", line)
                    if match:
                        package_name = match.group(1).lower()
                        version = match.group(3)
                        requirements[package_name] = version

        return requirements

    def get_package_info(self, package_name: str) -> dict:
        """Get detailed package information from PyPI."""
        try:
            result = subprocess.run(["pip", "show", package_name, "--verbose"], capture_output=True, text=True)

            info = {}
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        info[key.strip().lower()] = value.strip()

            return info
        except Exception as e:
            print(f"⚠️  Could not get info for {package_name}: {e}")
            return {}

    def analyze_dependencies(self, package_name: str) -> tuple[list[str], list[str]]:
        """Analyze package dependencies and dependents."""
        dependencies = []
        dependents = []

        try:
            # Get dependencies (what this package needs)
            result = self.run_command(["pip", "show", package_name])
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Requires:"):
                        deps = line.split(":", 1)[1].strip()
                        if deps:
                            dependencies = [dep.strip() for dep in deps.split(",")]

            # Get dependents (what needs this package)
            result = self.run_command(["pip", "list", "--format=json"])
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                for pkg in packages:
                    pkg_info = self.get_package_info(pkg["name"])
                    requires = pkg_info.get("requires", "")
                    if package_name in requires.lower():
                        dependents.append(pkg["name"])

        except Exception as e:
            print(f"⚠️  Could not analyze dependencies for {package_name}: {e}")

        return dependencies, dependents

    def assess_risk_level(self, package_name: str, current_version: str, latest_version: str) -> str:
        """Assess the risk level of updating a package."""
        package_name = package_name.lower()

        # Parse version numbers
        def parse_version(version: str) -> tuple[int, ...]:
            return tuple(map(int, re.findall(r"\d+", version)))

        try:
            current_parts = parse_version(current_version)
            latest_parts = parse_version(latest_version)

            # Major version change = high risk
            if current_parts[0] != latest_parts[0]:
                return "high"

            # Minor version change for risky packages = medium risk
            if package_name in self.risky_packages:
                if len(current_parts) >= 2 and len(latest_parts) >= 2:
                    if current_parts[1] != latest_parts[1]:
                        return "medium"

            # Django ecosystem packages require coordination
            if package_name in self.django_ecosystem:
                if len(current_parts) >= 2 and len(latest_parts) >= 2:
                    if current_parts[1] != latest_parts[1]:
                        return "medium"

            # Safe packages are usually low risk
            if package_name in self.safe_packages:
                return "low"

            # Default to medium for unknown packages
            return "medium"

        except ValueError:
            # If we can't parse versions (e.g., malformed version strings), be cautious
            return "high"

    def get_django_compatible_versions(self, target_django_version: str) -> dict[str, str]:
        """Get Django-compatible versions for ecosystem packages."""
        # This is a simplified compatibility matrix
        # In practice, you'd check each package's documentation

        django_major_minor = ".".join(target_django_version.split(".")[:2])

        compatibility_matrix = {
            "5.2": {
                "djangorestframework": "3.16.0",
                "django-allauth": "65.0.0",  # Latest that supports Django 5.2
                "django-cors-headers": "4.7.0",
                "django-debug-toolbar": "6.0.0",
                "django-extensions": "4.1.0",
                "django-filter": "25.1",
                "djangorestframework-simplejwt": "5.5.1",
                "drf-spectacular": "0.29.0",
            },
            "5.1": {
                "djangorestframework": "3.15.2",
                "django-allauth": "0.57.0",
                "django-cors-headers": "4.3.0",
                "django-debug-toolbar": "4.2.0",
                "django-extensions": "3.2.3",
                "django-filter": "23.3",
                "djangorestframework-simplejwt": "5.3.0",
                "drf-spectacular": "0.28.0",
            },
        }

        return compatibility_matrix.get(django_major_minor, {})

    def create_update_plan(self, packages_to_update: dict[str, str]) -> dict[str, list[PackageUpdate]]:
        """Create a phased update plan grouped by risk level."""
        current_requirements = self.parse_requirements()
        update_plan = {"low": [], "medium": [], "high": []}

        for package_name, latest_version in packages_to_update.items():
            current_version = current_requirements.get(package_name, "unknown")

            if current_version == "unknown":
                continue

            risk_level = self.assess_risk_level(package_name, current_version, latest_version)
            dependencies, dependents = self.analyze_dependencies(package_name)

            update_info = PackageUpdate(
                name=package_name,
                current_version=current_version,
                latest_version=latest_version,
                risk_level=risk_level,
                dependencies=dependencies,
                dependents=dependents,
            )

            update_plan[risk_level].append(update_info)

        return update_plan

    def test_requirements(self, requirements_content: str) -> bool:
        """Test if requirements can be installed without conflicts."""
        if self.dry_run:
            print("🧪 DRY RUN: Would test requirements installation")
            return True

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(requirements_content)
            temp_req_file = f.name

        try:
            # Test dependency resolution without actually installing
            cmd = ["pip-compile", "--dry-run", temp_req_file]
            result = self.run_command(cmd)

            success = result.returncode == 0
            if not success:
                print(f"❌ Dependency test failed: {result.stderr}")

            return success

        except Exception as e:
            print(f"⚠️  Could not test requirements: {e}")
            return False
        finally:
            Path(temp_req_file).unlink(missing_ok=True)

    def update_requirements_file(self, updates: list[PackageUpdate]) -> str:
        """Update requirements.txt with new versions."""
        with open(self.requirements_file) as f:
            content = f.read()

        updated_content = content

        for update in updates:
            # Find and replace the package line
            pattern = rf"^{re.escape(update.name)}==.*$"
            replacement = f"{update.name}=={update.latest_version}"
            updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)

        return updated_content

    def apply_updates(self, update_plan: dict[str, list[PackageUpdate]], phase: str) -> bool:
        """Apply updates for a specific phase."""
        updates = update_plan.get(phase, [])

        if not updates:
            print(f"✅ No {phase} risk updates to apply")
            return True

        print(f"\n🔄 Applying {phase} risk updates ({len(updates)} packages):")
        for update in updates:
            print(f"   • {update.name}: {update.current_version} → {update.latest_version}")

        if self.dry_run:
            print("🧪 DRY RUN: Would apply these updates")
            return True

        # Create updated requirements content
        updated_content = self.update_requirements_file(updates)

        # Test the updates
        if not self.test_requirements(updated_content):
            print(f"❌ {phase.title()} risk updates failed testing")
            return False

        # Apply the updates
        with open(self.requirements_file, "w") as f:
            f.write(updated_content)

        # Install the updates
        if self.use_docker:
            install_cmd = ["docker", "compose", "exec", "web", "pip", "install", "-r", "requirements.txt"]
        else:
            install_cmd = ["pip", "install", "-r", "requirements.txt"]

        result = subprocess.run(install_cmd, cwd=self.project_root)

        if result.returncode != 0:
            print(f"❌ Failed to install {phase} risk updates")
            return False

        print(f"✅ {phase.title()} risk updates applied successfully")
        return True

    def run_tests(self) -> bool:
        """Run project tests to verify updates don't break functionality."""
        if self.dry_run:
            print("🧪 DRY RUN: Would run project tests")
            return True

        print("🧪 Running project tests...")

        if self.use_docker:
            test_cmd = ["docker", "compose", "exec", "web", "python", "project_root/manage.py", "test"]
        else:
            test_cmd = ["python", "project_root/manage.py", "test"]

        result = subprocess.run(test_cmd, cwd=self.project_root)

        success = result.returncode == 0
        if success:
            print("✅ All tests passed")
        else:
            print("❌ Tests failed - updates may have broken functionality")

        return success

    def generate_report(self, update_plan: dict[str, list[PackageUpdate]]) -> None:
        """Generate a detailed update report."""
        print("\n" + "=" * 80)
        print("📊 SAFE DEPENDENCY UPDATE PLAN")
        print("=" * 80)

        total_updates = sum(len(updates) for updates in update_plan.values())
        print(f"\n📈 SUMMARY: {total_updates} packages to update")

        for risk_level in ["low", "medium", "high"]:
            updates = update_plan[risk_level]
            if not updates:
                continue

            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}[risk_level]
            print(f"\n{risk_emoji} {risk_level.upper()} RISK UPDATES ({len(updates)}):")

            for update in updates:
                print(f"   • {update.name}: {update.current_version} → {update.latest_version}")
                if update.dependents:
                    print(
                        f"     Affects: {', '.join(update.dependents[:3])}{'...' if len(update.dependents) > 3 else ''}"
                    )

        print("\n💡 RECOMMENDED UPDATE ORDER:")
        print("   1. 🟢 Low risk packages (tools, testing, linting)")
        print("   2. 🟡 Medium risk packages (Django ecosystem, libraries)")
        print("   3. 🔴 High risk packages (core infrastructure, major versions)")

        print("\n⚠️  IMPORTANT NOTES:")
        print("   • Always backup requirements.txt before updating")
        print("   • Test thoroughly after each phase")
        print("   • Update Django ecosystem packages together")
        print("   • Check changelogs for breaking changes")


def main():
    parser = argparse.ArgumentParser(description="Safely update Python dependencies")
    parser.add_argument("--docker", action="store_true", help="Use Docker environment")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--phase", choices=["low", "medium", "high", "all"], help="Apply specific risk level updates")
    parser.add_argument("--plan-only", action="store_true", help="Only show update plan without applying")

    args = parser.parse_args()

    updater = SafeDependencyUpdater(use_docker=args.docker, dry_run=args.dry_run)

    print("🔍 Analyzing dependencies for safe updates...")

    # Get outdated packages
    try:
        result = updater.run_command(["pip", "list", "--outdated", "--format=json"])
        if result.returncode == 0:
            outdated_packages = json.loads(result.stdout)
            packages_to_update = {pkg["name"].lower(): pkg["latest_version"] for pkg in outdated_packages}
        else:
            print("❌ Could not get outdated packages list")
            return 1
    except Exception as e:
        print(f"❌ Error getting outdated packages: {e}")
        return 1

    if not packages_to_update:
        print("✅ All packages are up to date!")
        return 0

    # Create update plan
    update_plan = updater.create_update_plan(packages_to_update)

    # Generate report
    updater.generate_report(update_plan)

    if args.plan_only:
        return 0

    # Create backup
    if not args.dry_run:
        updater.create_backup()

    # Apply updates by phase
    if args.phase == "all":
        phases = ["low", "medium", "high"]
    elif args.phase:
        phases = [args.phase]
    else:
        # Interactive mode - ask user which phases to apply
        phases = []
        for risk_level in ["low", "medium", "high"]:
            if update_plan[risk_level]:
                response = input(f"\nApply {risk_level} risk updates? [y/N]: ")
                if response.lower().startswith("y"):
                    phases.append(risk_level)

    # Apply selected phases
    for phase in phases:
        if not updater.apply_updates(update_plan, phase):
            print(f"❌ Failed to apply {phase} risk updates. Stopping.")
            return 1

        # Run tests after each phase
        if not updater.run_tests():
            print(f"❌ Tests failed after {phase} risk updates. Consider rolling back.")
            return 1

        if phase != phases[-1]:  # Not the last phase
            input(f"\n✅ {phase.title()} risk updates completed. Press Enter to continue to next phase...")

    print("\n🎉 Dependency updates completed successfully!")
    print("📝 Don't forget to commit the updated requirements.txt")

    return 0


if __name__ == "__main__":
    sys.exit(main())
