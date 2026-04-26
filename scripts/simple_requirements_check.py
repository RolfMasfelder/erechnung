#!/usr/bin/env python3
"""
Simple Requirements Checker

This script compares your requirements.txt with actually installed packages
and checks for version mismatches and outdated packages.

Usage:
    python simple_requirements_check.py [--docker]
"""

import argparse
import json
import re
import subprocess
from pathlib import Path


def run_command(cmd, use_docker=False):
    """Run command either locally or in Docker container."""
    if use_docker:
        docker_cmd = ["docker", "compose", "exec", "web"] + cmd
        return subprocess.run(docker_cmd, capture_output=True, text=True)
    else:
        return subprocess.run(cmd, capture_output=True, text=True)


def parse_requirements(requirements_file):
    """Parse requirements.txt file."""
    requirements = {}

    if not requirements_file.exists():
        print(f"❌ Requirements file not found: {requirements_file}")
        return requirements

    with open(requirements_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                # Handle different version specifiers (==, >=, >, etc.)
                match = re.match(r"^([a-zA-Z0-9._-]+)([><=!~]+)(.+)$", line)
                if match:
                    package_name = match.group(1).lower()
                    operator = match.group(2)
                    version = match.group(3)
                    requirements[package_name] = {
                        "version": version,
                        "operator": operator,
                        "line": line_num,
                        "raw": line,
                    }
                else:
                    # Package without version specifier
                    package_name = line.lower()
                    requirements[package_name] = {"version": "any", "operator": "", "line": line_num, "raw": line}

    return requirements


def get_installed_packages(use_docker=False):
    """Get currently installed packages."""
    try:
        result = run_command(["pip", "list", "--format=json"], use_docker)
        if result.returncode == 0:
            packages = json.loads(result.stdout)
            return {pkg["name"].lower(): pkg["version"] for pkg in packages}
        else:
            print(f"⚠️  Failed to get installed packages: {result.stderr}")
    except Exception as e:
        print(f"⚠️  Error getting installed packages: {e}")

    return {}


def get_outdated_packages(use_docker=False):
    """Get list of outdated packages."""
    try:
        result = run_command(["pip", "list", "--outdated", "--format=json"], use_docker)
        if result.returncode == 0:
            outdated = json.loads(result.stdout)
            return {pkg["name"].lower(): pkg["latest_version"] for pkg in outdated}
        else:
            print(f"⚠️  Failed to check outdated packages: {result.stderr}")
    except Exception as e:
        print(f"⚠️  Error checking outdated packages: {e}")

    return {}


def compare_versions(required_version, installed_version, operator):
    """Compare version strings."""
    if operator == "==" and required_version != installed_version:
        return f"Version mismatch: required {required_version}, installed {installed_version}"
    elif operator in [">=", ">"] and required_version > installed_version:
        return f"Version too old: required {operator}{required_version}, installed {installed_version}"
    return None


def main():
    parser = argparse.ArgumentParser(description="Check requirements.txt against installed packages")
    parser.add_argument("--docker", action="store_true", help="Run checks in Docker container")
    args = parser.parse_args()

    print("🔍 Simple Requirements Checker")
    print("=" * 50)

    # Get requirements from file
    requirements_file = Path("requirements.txt")
    requirements = parse_requirements(requirements_file)
    print(f"📋 Found {len(requirements)} packages in requirements.txt")

    # Get installed packages
    installed = get_installed_packages(args.docker)
    print(f"📦 Found {len(installed)} installed packages")

    # Get outdated packages
    outdated = get_outdated_packages(args.docker)
    print(f"📈 Found {len(outdated)} outdated packages")

    print("\n" + "=" * 50)
    print("📊 ANALYSIS RESULTS")
    print("=" * 50)

    # Check each requirement
    missing_packages = []
    version_mismatches = []
    outdated_in_requirements = []

    for package_name, req_info in requirements.items():
        if package_name not in installed:
            missing_packages.append((package_name, req_info))
        else:
            installed_version = installed[package_name]
            required_version = req_info["version"]
            operator = req_info["operator"]

            # Check version mismatch
            if operator and required_version != "any":
                mismatch = compare_versions(required_version, installed_version, operator)
                if mismatch:
                    version_mismatches.append((package_name, req_info, installed_version, mismatch))

            # Check if package is outdated
            if package_name in outdated:
                latest_version = outdated[package_name]
                outdated_in_requirements.append((package_name, installed_version, latest_version))

    # Check for extra installed packages
    extra_packages = []
    for package_name in installed:
        if package_name not in requirements:
            # Skip common system packages
            system_packages = {"pip", "setuptools", "wheel", "distribute"}
            if package_name not in system_packages:
                extra_packages.append(package_name)

    # Print results
    print("\n🔍 SUMMARY:")
    print(f"   Missing packages: {len(missing_packages)}")
    print(f"   Version mismatches: {len(version_mismatches)}")
    print(f"   Outdated packages: {len(outdated_in_requirements)}")
    print(f"   Extra packages: {len(extra_packages)}")

    if missing_packages:
        print(f"\n❌ MISSING PACKAGES ({len(missing_packages)}):")
        for package_name, req_info in missing_packages:
            print(f"   • {package_name} (line {req_info['line']}: {req_info['raw']})")
        print(f"\n   💡 Install with: pip install {' '.join(pkg[0] for pkg in missing_packages)}")

    if version_mismatches:
        print(f"\n⚠️  VERSION MISMATCHES ({len(version_mismatches)}):")
        for package_name, req_info, _, mismatch in version_mismatches:
            print(f"   • {package_name}: {mismatch}")
            print(f"     Line {req_info['line']}: {req_info['raw']}")

    if outdated_in_requirements:
        print(f"\n📈 OUTDATED PACKAGES ({len(outdated_in_requirements)}):")
        for package_name, current_version, latest_version in outdated_in_requirements:
            print(f"   • {package_name}: {current_version} → {latest_version}")

    if extra_packages:
        print(f"\n📦 EXTRA INSTALLED PACKAGES ({len(extra_packages)}):")
        print("   (These are installed but not in requirements.txt)")
        for package_name in sorted(extra_packages):
            version = installed[package_name]
            print(f"   • {package_name}=={version}")

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if missing_packages:
        print(f"   1. 📥 Install {len(missing_packages)} missing packages")
    if version_mismatches:
        print(f"   2. 🔄 Fix {len(version_mismatches)} version mismatches")
    if outdated_in_requirements:
        print(f"   3. 📈 Consider updating {len(outdated_in_requirements)} outdated packages")
    if extra_packages:
        print(f"   4. 📝 Consider adding {len(extra_packages)} extra packages to requirements.txt")

    if not any([missing_packages, version_mismatches, outdated_in_requirements]):
        print("   ✅ All packages are correctly installed and up to date!")

    print("\n🔧 USEFUL COMMANDS:")
    if args.docker:
        print("   # Install missing packages:")
        print("   docker compose exec web pip install <package_name>")
        print("   # Update all packages:")
        print("   docker compose exec web pip install -r requirements.txt --upgrade")
        print("   # Check what would be updated:")
        print("   docker compose exec web pip list --outdated")
    else:
        print("   # Install missing packages:")
        print("   pip install <package_name>")
        print("   # Update all packages:")
        print("   pip install -r requirements.txt --upgrade")
        print("   # Check what would be updated:")
        print("   pip list --outdated")


if __name__ == "__main__":
    main()
