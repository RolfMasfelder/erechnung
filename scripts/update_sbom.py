#!/usr/bin/env python3
"""
Update SBOM.json with current versions from requirements.txt and package-lock.json.

Usage:
    python scripts/update_sbom.py          # Preview changes (dry-run)
    python scripts/update_sbom.py --apply  # Apply changes to SBOM.json

Reads:
  - requirements.txt        (pinned Python versions)
  - frontend/package-lock.json (exact installed npm versions)
  - Dockerfile              (Python base image tag)

Updates:
  - SBOM.json components[].version, bom-ref, purl
  - SBOM.json services[] frontend library versions
  - SBOM.json dependencies[].dependsOn refs
  - metadata timestamp + generation date
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SBOM_PATH = ROOT / "SBOM.json"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
PACKAGE_LOCK_PATH = ROOT / "frontend" / "package-lock.json"
DOCKERFILE_PATH = ROOT / "Dockerfile"


def parse_requirements(path: Path) -> dict[str, str]:
    """Parse requirements.txt → {package_name: version}."""
    versions = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if "==" in line and not line.startswith("#"):
            name, version = line.split("==", 1)
            # Normalize: lowercase, underscores → hyphens
            name = name.lower().replace("_", "-")
            versions[name] = version
    return versions


def parse_package_lock(path: Path) -> dict[str, str]:
    """Parse package-lock.json → {package_name: exact_version}."""
    versions = {}
    if not path.exists():
        return versions
    lock = json.loads(path.read_text())
    for key, info in lock.get("packages", {}).items():
        if key.startswith("node_modules/") and "version" in info:
            pkg_name = key.removeprefix("node_modules/")
            # Only top-level (no nested node_modules)
            if "node_modules/" not in pkg_name:
                versions[pkg_name] = info["version"]
    return versions


def parse_dockerfile_python_image(path: Path) -> str | None:
    """Extract Python base image tag from Dockerfile."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        m = re.match(r"^FROM\s+python:([\S]+)", line, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def normalize_pypi_name(name: str) -> str:
    """Normalize a PyPI package name for lookup."""
    return name.lower().replace("_", "-").replace(" ", "-")


def update_component_version(component: dict, new_version: str, old_bom_ref: str) -> str:
    """Update a component's version, bom-ref, and purl. Returns new bom-ref."""
    old_version = component["version"]
    if old_version == new_version:
        return old_bom_ref

    component["version"] = new_version

    # Update bom-ref: replace version suffix
    new_bom_ref = re.sub(
        r"-[\d][.\d]*$",
        f"-{new_version}",
        old_bom_ref,
    )
    component["bom-ref"] = new_bom_ref

    # Update purl
    if "purl" in component:
        component["purl"] = re.sub(
            r"@[\d][.\d]*$",
            f"@{new_version}",
            component["purl"],
        )

    return new_bom_ref


# Mapping: SBOM purl-name → requirements.txt name (where they differ)
PYPI_NAME_MAP = {
    "django": "django",
    "djangorestframework": "djangorestframework",
    "psycopg2-binary": "psycopg2-binary",
    "celery": "celery",
    "redis": "redis",
    "factur-x": "factur-x",
    "pypdf": "pypdf",
    "weasyprint": "weasyprint",
    "drf-spectacular": "drf-spectacular",
    "lxml": "lxml",
    "xmlschema": "xmlschema",
    "pikepdf": "pikepdf",
    "pillow": "pillow",
    "gunicorn": "gunicorn",
    "whitenoise": "whitenoise",
    "sentry-sdk": "sentry-sdk",
    "django-allauth": "django-allauth",
    "django-axes": "django-axes",
    "django-cors-headers": "django-cors-headers",
    "django-csp": "django-csp",
    "django-redis": "django-redis",
    "djangorestframework-simplejwt": "djangorestframework-simplejwt",
}

# Mapping: SBOM npm name → package-lock.json name
NPM_NAME_MAP = {
    "vue": "vue",
    "vue-router": "vue-router",
    "pinia": "pinia",
    "axios": "axios",
    "vite": "vite",
    "tailwindcss": "tailwindcss",
    "vitest": "vitest",
    "@playwright/test": "@playwright/test",
    "@vue/test-utils": "@vue/test-utils",
}


def main():
    apply_mode = "--apply" in sys.argv

    if not SBOM_PATH.exists():
        print(f"ERROR: {SBOM_PATH} not found")
        sys.exit(1)
    if not REQUIREMENTS_PATH.exists():
        print(f"ERROR: {REQUIREMENTS_PATH} not found")
        sys.exit(1)

    sbom = json.loads(SBOM_PATH.read_text())
    py_versions = parse_requirements(REQUIREMENTS_PATH)
    npm_versions = parse_package_lock(PACKAGE_LOCK_PATH)
    python_image_tag = parse_dockerfile_python_image(DOCKERFILE_PATH)

    changes = []
    bom_ref_renames = {}  # old_ref → new_ref

    # --- Update Python components ---
    for comp in sbom.get("components", []):
        purl = comp.get("purl", "")
        if purl.startswith("pkg:pypi/"):
            # Extract package name from purl
            pkg_name = purl.split("/")[1].split("@")[0]
            req_name = normalize_pypi_name(pkg_name)
            if req_name in py_versions:
                new_ver = py_versions[req_name]
                old_ver = comp["version"]
                if old_ver != new_ver:
                    old_ref = comp["bom-ref"]
                    new_ref = update_component_version(comp, new_ver, old_ref)
                    bom_ref_renames[old_ref] = new_ref
                    changes.append(f"  Python: {comp['name']} {old_ver} → {new_ver}")

        # Update Python base image
        if comp.get("bom-ref", "").startswith("python-") and python_image_tag:
            old_tag = comp["version"]
            if old_tag != python_image_tag:
                old_ref = comp["bom-ref"]
                comp["version"] = python_image_tag
                comp["description"] = f"Python {python_image_tag.split('-')[0]} on Debian Bookworm (slim)"
                new_ref = f"python-{python_image_tag}"
                comp["bom-ref"] = new_ref
                for prop in comp.get("properties", []):
                    if prop.get("name") == "docker:image":
                        prop["value"] = f"python:{python_image_tag}"
                bom_ref_renames[old_ref] = new_ref
                changes.append(f"  Docker: Python base image {old_tag} → {python_image_tag}")

    # --- Update npm components (in services section) ---
    for svc in sbom.get("services", []):
        if svc.get("type") != "library":
            continue
        npm_name = svc.get("name", "")
        purl = svc.get("purl", "")

        lock_name = NPM_NAME_MAP.get(npm_name)
        if lock_name and lock_name in npm_versions:
            new_ver = npm_versions[lock_name]
            old_ver = svc["version"]
            if old_ver != new_ver:
                old_ref = svc["bom-ref"]
                svc["version"] = new_ver
                # Update bom-ref: name@version
                new_ref = f"{npm_name}@{new_ver}"
                svc["bom-ref"] = new_ref
                if purl:
                    svc["purl"] = re.sub(r"@[\d][.\d]*$", f"@{new_ver}", purl)
                bom_ref_renames[old_ref] = new_ref
                changes.append(f"  npm: {npm_name} {old_ver} → {new_ver}")

    # --- Update dependencies refs ---
    for dep in sbom.get("dependencies", []):
        new_deps = []
        for ref in dep.get("dependsOn", []):
            new_deps.append(bom_ref_renames.get(ref, ref))
        dep["dependsOn"] = new_deps

    # --- Update tool name (always, if still manual) ---
    for tool in sbom["metadata"].get("tools", []):
        if "Manual" in tool.get("name", ""):
            tool["name"] = "Automated SBOM Update (update_sbom.py)"
            changes.append("  Meta: tool name → 'Automated SBOM Update (update_sbom.py)'")

    # --- Only update metadata timestamps if there are real changes ---
    if not changes:
        print("✓ SBOM.json is up to date. No changes needed.")
        return

    # Bump metadata only when real component changes exist
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y-%m-%d")
    sbom["metadata"]["timestamp"] = timestamp

    old_sbom_version = sbom.get("version", 1)
    sbom["version"] = old_sbom_version + 1
    changes.append(f"  Meta: version {old_sbom_version} → {sbom['version']}")
    changes.append(f"  Meta: timestamp → {timestamp}")

    for prop in sbom.get("properties", []):
        if prop.get("name") == "sbom:generation-date":
            prop["value"] = date_str
        if prop.get("name") == "sbom:generation-method":
            prop["value"] = "automated"

    print(f"{'APPLYING' if apply_mode else 'PREVIEW'}: {len(changes)} change(s):")
    for c in changes:
        print(c)

    if apply_mode:
        SBOM_PATH.write_text(json.dumps(sbom, indent=2, ensure_ascii=False) + "\n")
        print(f"\n✓ SBOM.json updated (version {sbom['version']}).")
    else:
        print(f"\nRun with --apply to write changes to {SBOM_PATH.name}")


if __name__ == "__main__":
    main()
