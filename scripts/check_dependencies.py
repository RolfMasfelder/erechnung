#!/usr/bin/env python3
"""
Dependency Analysis Script for Django eRechnung Project

This script helps analyze and maintain Python dependencies by:
1. Comparing requirements.txt with actually imported modules
2. Checking for outdated packages and security vulnerabilities
3. Identifying unused dependencies
4. Suggesting version updates

Usage:
    python check_dependencies.py [options]

Options:
    --docker    Run analysis inside Docker container
    --update    Show update commands for outdated packages
    --security  Focus on security vulnerabilities only
    --unused    Find potentially unused dependencies
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# Django setup for standalone script
def setup_django():
    """Setup Django environment for standalone script."""
    sys.path.insert(0, "project_root")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoice_project.settings")
    import django

    django.setup()


@dataclass
class PackageInfo:
    """Information about a Python package."""

    name: str
    current_version: str
    latest_version: str = ""
    used_in_code: bool = False
    security_issues: list[str] = field(default_factory=list)
    update_available: bool = False
    import_names: set[str] = field(default_factory=set)

    def __post_init__(self):
        self.update_available = self.current_version != self.latest_version if self.latest_version else False


class DependencyChecker:
    """Main class for dependency analysis."""

    def __init__(self, use_docker: bool = False):
        self.use_docker = use_docker
        self.project_root = Path(__file__).parent.parent  # Go up one level from scripts/
        self.requirements_file = self.project_root / "requirements.txt"
        self.packages: dict[str, PackageInfo] = {}
        self.code_imports: set[str] = set()

        # Common package name mappings (pip name -> import name)
        self.package_mappings = {
            "django-allauth": "allauth",
            "django-axes": "axes",
            "django-cors-headers": "corsheaders",
            "django-csp": "csp",
            "django-debug-toolbar": "debug_toolbar",
            "django-extensions": "django_extensions",
            "django-filter": "django_filters",
            "django-redis": "django_redis",
            "djangorestframework": "rest_framework",
            "djangorestframework-simplejwt": "rest_framework_simplejwt",
            "drf-spectacular": "drf_spectacular",
            "factory-boy": "factory",
            "factur-x": "facturx",
            "pillow": "PIL",
            "psycopg2-binary": "psycopg2",
            "python-dotenv": "dotenv",
            "dj-database-url": "dj_database_url",
        }

    def run_command(self, cmd: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run command either locally or in Docker container."""
        if self.use_docker:
            docker_cmd = ["docker", "compose", "exec", "web"] + cmd
            return subprocess.run(docker_cmd, capture_output=capture_output, text=True, cwd=self.project_root)
        else:
            return subprocess.run(cmd, capture_output=capture_output, text=True, cwd=self.project_root)

    def parse_requirements(self) -> dict[str, str]:
        """Parse requirements.txt and extract package names with versions."""
        requirements = {}

        if not self.requirements_file.exists():
            print(f"❌ Requirements file not found: {self.requirements_file}")
            return requirements

        with open(self.requirements_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Handle different version specifiers
                    match = re.match(r"^([a-zA-Z0-9._-]+)([><=!]+)(.+)$", line)
                    if match:
                        package_name = match.group(1).lower()
                        version = match.group(3)
                        requirements[package_name] = version
                    else:
                        # Package without version specifier
                        package_name = line.lower()
                        requirements[package_name] = "unknown"

        return requirements

    def get_installed_packages(self) -> dict[str, str]:
        """Get currently installed packages and their versions."""
        try:
            result = self.run_command(["pip", "list", "--format=json"])
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                return {pkg["name"].lower(): pkg["version"] for pkg in packages}
        except Exception as e:
            print(f"⚠️  Could not get installed packages: {e}")

        return {}

    def get_latest_versions(self, package_names: list[str]) -> dict[str, str]:
        """Get latest available versions for packages from PyPI."""
        latest_versions = {}

        print("🔍 Checking latest versions from PyPI...")
        for i, package in enumerate(package_names):
            try:
                print(f"   [{i + 1}/{len(package_names)}] {package}", end=" ... ", flush=True)
                result = self.run_command(["pip", "index", "versions", package])

                if result.returncode == 0:
                    # Parse pip index output
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if "Available versions:" in line:
                            versions = line.split("Available versions:")[1].strip()
                            if versions:
                                # Get the first (latest) version
                                latest_version = versions.split(",")[0].strip()
                                latest_versions[package] = latest_version
                                print(f"✅ {latest_version}")
                                break
                    else:
                        print("❓ No version info")
                else:
                    print("❌ Failed")
            except Exception as e:
                print(f"❌ Error: {e}")

        return latest_versions

    def scan_code_imports(self) -> set[str]:
        """Scan Python files for import statements."""
        imports = set()
        python_files = []

        # Scan project_root directory
        project_dir = self.project_root / "project_root"
        if project_dir.exists():
            python_files.extend(project_dir.rglob("*.py"))

        print(f"🔍 Scanning {len(python_files)} Python files for imports...")

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Find import statements
                import_patterns = [
                    r"^import\s+([a-zA-Z0-9._]+)",
                    r"^from\s+([a-zA-Z0-9._]+)\s+import",
                ]

                for pattern in import_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        # Get top-level module name
                        top_level = match.split(".")[0]
                        imports.add(top_level)
            except Exception as e:
                print(f"⚠️  Could not read {py_file}: {e}")

        return imports

    def _format_vulnerability_info(self, vuln: dict) -> str:
        """Format vulnerability information for display."""
        advisory = vuln.get("id", "Security vulnerability found")
        description = vuln.get("description", "")
        fix_versions = vuln.get("fix_versions", [])

        vuln_info = advisory
        if fix_versions:
            vuln_info += f" (fix available in: {', '.join(fix_versions[:3])})"
        if description:
            short_desc = description[:100] + "..." if len(description) > 100 else description
            vuln_info += f" - {short_desc}"

        return vuln_info

    def _parse_pip_audit_json(self, audit_data: dict) -> dict[str, list[str]]:
        """Parse pip-audit JSON output and extract vulnerability information."""
        vulnerabilities = {}
        dependencies = audit_data.get("dependencies", [])

        for dep in dependencies:
            package = dep.get("name", "").lower()
            vulns = dep.get("vulns", [])
            if vulns:
                vulnerabilities[package] = [self._format_vulnerability_info(vuln) for vuln in vulns]

        return vulnerabilities

    def check_security_vulnerabilities(self) -> dict[str, list[str]]:
        """Check for security vulnerabilities using pip-audit."""
        vulnerabilities = {}

        try:
            print("🔒 Checking for security vulnerabilities...")
            if self.use_docker:
                result = self.run_command(["/home/appuser/.local/bin/pip-audit", "--format", "json"])
            else:
                result = self.run_command(["pip-audit", "--format", "json"])

            # pip-audit returns exit code 1 when vulnerabilities are found, but still provides valid JSON
            if result.returncode in [0, 1] and result.stdout.strip():
                try:
                    audit_data = json.loads(result.stdout)
                    vulnerabilities = self._parse_pip_audit_json(audit_data)

                    # Count total vulnerabilities
                    total_vulns = sum(len(vulns) for vulns in vulnerabilities.values())

                    if result.returncode == 1:
                        print(f"🚨 Found {total_vulns} security vulnerabilities in {len(vulnerabilities)} packages")
                    else:
                        print("✅ No known security vulnerabilities found")

                except json.JSONDecodeError:
                    if "No known vulnerabilities found" not in result.stdout:
                        print("⚠️  Could not parse pip-audit output as JSON")
                        print(f"Raw output: {result.stdout[:200]}...")
            else:
                print(f"⚠️  pip-audit failed (exit code {result.returncode}): {result.stderr}")
        except Exception as e:
            print(f"⚠️  Could not run pip-audit: {e}")

        return vulnerabilities

    def find_unused_dependencies(self, requirements: dict[str, str], code_imports: set[str]) -> set[str]:
        """Find potentially unused dependencies."""
        unused = set()

        for package_name in requirements.keys():
            # Check direct import name
            if package_name not in code_imports:
                # Check mapped import name
                mapped_name = self.package_mappings.get(package_name, package_name)
                if mapped_name not in code_imports:
                    # Check if it's a commonly used package that might be imported differently
                    potential_imports = {
                        package_name.replace("-", "_"),
                        package_name.replace("_", "-"),
                        package_name.split("-")[0] if "-" in package_name else package_name,
                    }

                    if not any(imp in code_imports for imp in potential_imports):
                        unused.add(package_name)

        # Remove some packages that are commonly used indirectly
        indirect_packages = {
            "gunicorn",
            "psycopg2-binary",
            "whitenoise",
            "setuptools",
            "coverage",
            "pytest",
            "pytest-django",
            "factory-boy",
            "pre-commit",
            "black",
            "ruff",
            "flake8",
            "isort",
            "pylint",
            "pip-audit",
        }

        unused = unused - indirect_packages
        return unused

    def analyze_dependencies(self, check_security: bool = True, check_unused: bool = True) -> None:
        """Main analysis function."""
        print("🔍 Starting dependency analysis...\n")

        # Parse requirements.txt
        requirements = self.parse_requirements()
        print(f"📋 Found {len(requirements)} packages in requirements.txt")

        # Get installed packages
        installed = self.get_installed_packages()
        print(f"📦 Found {len(installed)} installed packages")

        # Get latest versions
        latest_versions = self.get_latest_versions(list(requirements.keys()))

        # Scan code for imports
        if check_unused:
            self.code_imports = self.scan_code_imports()
            print(f"📄 Found {len(self.code_imports)} unique imports in code")

        # Check security vulnerabilities
        vulnerabilities = {}
        if check_security:
            vulnerabilities = self.check_security_vulnerabilities()

        # Build package info
        for package_name, _req_version in requirements.items():
            installed_version = installed.get(package_name, "Not installed")
            latest_version = latest_versions.get(package_name, "Unknown")

            # Check if package is used in code
            used_in_code = False
            if check_unused:
                import_name = self.package_mappings.get(package_name, package_name)
                used_in_code = (
                    package_name in self.code_imports
                    or import_name in self.code_imports
                    or any(imp.startswith(package_name) for imp in self.code_imports)
                )

            self.packages[package_name] = PackageInfo(
                name=package_name,
                current_version=installed_version,
                latest_version=latest_version,
                used_in_code=used_in_code,
                security_issues=vulnerabilities.get(package_name, []),
            )

    def generate_report(
        self, show_updates: bool = False, security_only: bool = False, unused_only: bool = False
    ) -> None:
        """Generate and display the analysis report."""
        print("\n" + "=" * 80)
        print("📊 DEPENDENCY ANALYSIS REPORT")
        print("=" * 80)

        if security_only:
            self._print_security_report()
        elif unused_only:
            self._print_unused_report()
        else:
            self._print_full_report(show_updates)

    def _print_security_report(self) -> None:
        """Print security vulnerabilities report."""
        print("\n🔒 SECURITY VULNERABILITIES:")
        security_issues = {name: pkg for name, pkg in self.packages.items() if pkg.security_issues}

        if security_issues:
            for name, pkg in security_issues.items():
                print(f"\n❌ {name} ({pkg.current_version}):")
                for issue in pkg.security_issues:
                    print(f"   • {issue}")
        else:
            print("✅ No known security vulnerabilities found!")

    def _print_unused_report(self) -> None:
        """Print unused dependencies report."""
        print("\n📦 POTENTIALLY UNUSED DEPENDENCIES:")
        unused = [name for name, pkg in self.packages.items() if not pkg.used_in_code]

        if unused:
            for name in sorted(unused):
                pkg = self.packages[name]
                print(f"❓ {name} ({pkg.current_version}) - Not found in code imports")
        else:
            print("✅ All dependencies appear to be used!")

    def _print_full_report(self, show_updates: bool) -> None:
        """Print full analysis report."""
        # Summary
        total = len(self.packages)
        outdated = sum(1 for pkg in self.packages.values() if pkg.update_available)
        vulnerable = sum(1 for pkg in self.packages.values() if pkg.security_issues)
        unused = sum(1 for pkg in self.packages.values() if not pkg.used_in_code)

        print("\n📊 SUMMARY:")
        print(f"   Total packages: {total}")
        print(f"   Outdated: {outdated}")
        print(f"   With security issues: {vulnerable}")
        print(f"   Potentially unused: {unused}")

        # Outdated packages
        if show_updates:
            outdated_packages = {name: pkg for name, pkg in self.packages.items() if pkg.update_available}
            if outdated_packages:
                print(f"\n📈 OUTDATED PACKAGES ({len(outdated_packages)}):")
                for name, pkg in sorted(outdated_packages.items()):
                    print(f"   {name}: {pkg.current_version} → {pkg.latest_version}")

                print("\n💡 UPDATE COMMANDS:")
                print("   # Update individual packages:")
                for name, pkg in sorted(outdated_packages.items()):
                    print(f"   pip install {name}=={pkg.latest_version}")

                print("\n   # Or update requirements.txt and run:")
                print("   pip install -r requirements.txt --upgrade")

        # Security issues
        self._print_security_report()

        # Unused dependencies
        self._print_unused_report()

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if vulnerable > 0:
            print(f"   1. 🔒 Fix {vulnerable} security vulnerabilities immediately")
        if outdated > 0:
            print(f"   2. 📈 Consider updating {outdated} outdated packages")
        if unused > 0:
            print(f"   3. 🧹 Review {unused} potentially unused dependencies")
        print("   4. 🔄 Run this script regularly to maintain dependency health")


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Analyze Python dependencies for Django eRechnung project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python check_dependencies.py                    # Full analysis
    python check_dependencies.py --docker           # Run in Docker container
    python check_dependencies.py --security         # Security issues only
    python check_dependencies.py --unused           # Unused dependencies only
    python check_dependencies.py --update           # Show update commands
        """,
    )

    parser.add_argument("--docker", action="store_true", help="Run analysis inside Docker container")
    parser.add_argument("--update", action="store_true", help="Show update commands for outdated packages")
    parser.add_argument("--security", action="store_true", help="Focus on security vulnerabilities only")
    parser.add_argument("--unused", action="store_true", help="Find potentially unused dependencies")

    args = parser.parse_args()

    # Initialize checker
    checker = DependencyChecker(use_docker=args.docker)

    try:
        # Run analysis
        checker.analyze_dependencies(check_security=not args.unused, check_unused=not args.security)

        # Generate report
        checker.generate_report(show_updates=args.update, security_only=args.security, unused_only=args.unused)

    except KeyboardInterrupt:
        print("\n\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
