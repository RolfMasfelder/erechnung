#!/usr/bin/env python3
"""
Update SBOM.json and docs/SBOM.md with current versions from requirements.txt and package-lock.json.

Usage:
    python scripts/update_sbom.py          # Preview changes (dry-run)
    python scripts/update_sbom.py --apply  # Apply changes to SBOM.json + docs/SBOM.md

Reads:
  - requirements.txt        (pinned Python versions)
  - frontend/package-lock.json (exact installed npm versions)
  - Dockerfile              (Python base image tag)

Updates:
  - SBOM.json components[].version, bom-ref, purl
  - SBOM.json services[] frontend library versions
  - SBOM.json dependencies[].dependsOn refs
  - SBOM.json metadata timestamp + generation date
  - docs/SBOM.md version table entries + Generated date
"""

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SBOM_PATH = ROOT / "SBOM.json"
SBOM_MD_PATH = ROOT / "docs" / "SBOM.md"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
PACKAGE_LOCK_PATH = ROOT / "frontend" / "package-lock.json"
DOCKERFILE_PATH = ROOT / "Dockerfile"
NODE_DOCKERFILE_PATH = ROOT / "frontend" / "Dockerfile.prod"
PYPROJECT_PATH = ROOT / "pyproject.toml"
LICENSE_PATH = ROOT / "LICENSE"


def parse_pyproject_version(path: Path) -> str | None:
    """Extract version from pyproject.toml."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        m = re.match(r'^version\s*=\s*"([^"]+)"', line)
        if m:
            return m.group(1)
    return None


def parse_license_spdx(path: Path) -> str | None:
    """Derive SPDX license identifier from the first line of LICENSE."""
    if not path.exists():
        return None
    first_line = path.read_text().splitlines()[0].upper()
    if "AFFERO" in first_line and "3" in first_line:
        return "AGPL-3.0-only"
    if "APACHE" in first_line and "2" in first_line:
        return "Apache-2.0"
    if "MIT" in first_line:
        return "MIT"
    if "GPL" in first_line and "3" in first_line:
        return "GPL-3.0-only"
    if "GPL" in first_line and "2" in first_line:
        return "GPL-2.0-only"
    return None


def parse_requirements(path: Path) -> dict[str, str]:
    """Parse requirements.txt → {package_name: version}."""
    versions = {}
    for line in path.read_text().splitlines():
        line = line.strip()  # noqa: PLW2901
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


def parse_dockerfile_node_image(path: Path) -> str | None:
    """Extract Node.js major version from a frontend Dockerfile (e.g. 'node:22-alpine' → '22')."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        m = re.match(r"^FROM\s+node:(\d+)", line, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def normalize_pypi_name(name: str) -> str:
    """Normalize a PyPI package name for lookup."""
    return name.lower().replace("_", "-").replace(" ", "-")


def _get_system_deps(components: list[dict]) -> list[dict]:
    """Extract system package components (those with system:package property)."""
    return [c for c in components if any(p.get("name") == "system:package" for p in c.get("properties", []))]


def _format_system_deps_table(system_deps: list[dict]) -> str:
    """Generate the System Dependencies markdown table from SBOM system components."""
    lines = [
        "| Component | Package Type | License | Purpose |",
        "|-----------|--------------|---------|----------|",
    ]
    for dep in system_deps:
        name = dep.get("name", "")
        lic_list = dep.get("licenses", [])
        if lic_list:
            lic_entry = lic_list[0].get("license", {})
            license_str = lic_entry.get("id") or lic_entry.get("name") or "-"
        else:
            license_str = "-"
        purpose = next(
            (p["value"] for p in dep.get("properties", []) if p.get("name") == "system:purpose"),
            dep.get("description", ""),
        )
        lines.append(f"| {name} | System | {license_str} | {purpose} |")
    return "\n".join(lines)


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

# Mapping: normalized package name → display name used in docs/SBOM.md tables
MD_DISPLAY_NAME: dict[str, str] = {
    # PyPI
    "django": "Django",
    "djangorestframework": "Django REST Framework",
    "gunicorn": "Gunicorn",
    "celery": "Celery",
    "psycopg2-binary": "psycopg2-binary",
    "django-redis": "django-redis",
    "factur-x": "factur-x",
    "reportlab": "ReportLab",
    "pikepdf": "pikepdf",
    "lxml": "lxml",
    "xmlschema": "xmlschema",
    "pillow": "Pillow",
    "pypdf": "pypdf",
    "weasyprint": "WeasyPrint",
    "django-allauth": "django-allauth",
    "django-axes": "django-axes",
    "djangorestframework-simplejwt": "djangorestframework-simplejwt",
    "django-cors-headers": "django-cors-headers",
    "django-csp": "django-csp",
    "sentry-sdk": "Sentry SDK",
    "whitenoise": "WhiteNoise",
    "pytest": "pytest",
    "pytest-django": "pytest-django",
    "coverage": "coverage",
    "black": "black",
    "ruff": "ruff",
    "pylint": "pylint",
    "pre-commit": "pre-commit",
    # npm
    "vue": "Vue.js",
    "vue-router": "Vue Router",
    "pinia": "Pinia",
    "axios": "Axios",
    "vite": "Vite",
    "tailwindcss": "Tailwind CSS",
    "vitest": "Vitest",
    "@playwright/test": "Playwright",
    "@vue/test-utils": "@vue/test-utils",
}

MONTHS_DE = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def sync_sbom_md(  # noqa: PLR0912, PLR0913
    py_versions: dict[str, str],
    npm_versions: dict[str, str],
    python_image_tag: str | None,
    node_major: str | None,
    project_version: str | None,
    project_license: str | None,
    apply_mode: bool,
    now: datetime,
    system_deps: list[dict] | None = None,
) -> list[str]:
    """Sync docs/SBOM.md tables to the current package versions.

    Compares SBOM.md against py_versions + npm_versions directly,
    so it stays correct even when SBOM.json itself needs no update.
    """
    if not SBOM_MD_PATH.exists():
        return []

    # Merge all current versions into one lookup
    current: dict[str, str] = {**py_versions, **npm_versions}

    content = SBOM_MD_PATH.read_text()
    md_changes = []

    # Sync project version
    if project_version:
        m = re.search(r"(\*\*Version:\*\* )([\d.]+)", content)
        if m and m.group(2) != project_version:
            content = re.sub(r"(\*\*Version:\*\* )[\d.]+", r"\g<1>" + project_version, content)
            md_changes.append(f"  SBOM.md: Version {m.group(2)} → {project_version}")

    # Sync project license
    if project_license:
        m = re.search(r"(\*\*License:\*\* )(\S+)", content)
        if m and m.group(2) != project_license:
            content = re.sub(r"(\*\*License:\*\* )\S+", r"\g<1>" + project_license, content)
            md_changes.append(f"  SBOM.md: License {m.group(2)} → {project_license}")

    for pkg_name, md_name in MD_DISPLAY_NAME.items():
        new_ver = current.get(pkg_name)
        if not new_ver:
            continue
        pattern = r"(\| " + re.escape(md_name) + r" \| )(\S+)( \| )"
        m = re.search(pattern, content)
        if m and m.group(2) != new_ver:
            old_ver = m.group(2)
            content = re.sub(pattern, r"\g<1>" + new_ver + r"\3", content)
            md_changes.append(f"  SBOM.md: {md_name} {old_ver} → {new_ver}")

    # Sync Python base image version in the Runtime Environment section
    if python_image_tag:
        py_ver_match = re.match(r"^([\d.]+)", python_image_tag)
        if py_ver_match:
            py_ver = py_ver_match.group(1)
            m = re.search(r"(\*\*Backend:\*\* Python )([\d.]+)", content)
            if m and m.group(2) != py_ver:
                content = re.sub(
                    r"(\*\*Backend:\*\* Python )[\d.]+",
                    r"\g<1>" + py_ver,
                    content,
                )
                md_changes.append(f"  SBOM.md: Python runtime {m.group(2)} → {py_ver}")
    # Sync Node.js major version
    if node_major:
        m = re.search(r"(\*\*Frontend:\*\* Node\.js )(\d+)", content)
        if m and m.group(2) != node_major:
            content = re.sub(
                r"(\*\*Frontend:\*\* Node\.js )\d+",
                r"\g<1>" + node_major,
                content,
            )
            md_changes.append(f"  SBOM.md: Node.js {m.group(2)} \u2192 {node_major}")
    # Sync System Dependencies table from SBOM.json system components
    if system_deps:
        new_table = _format_system_deps_table(system_deps)
        sys_dep_pattern = r"### System Dependencies\n(?:\|[^\n]+\n)+"
        new_section = f"### System Dependencies\n{new_table}\n"
        new_content = re.sub(sys_dep_pattern, new_section, content)
        if new_content != content:
            content = new_content
            md_changes.append("  SBOM.md: System Dependencies table updated")

    if not md_changes:
        return []

    date_str = f"{now.day}. {MONTHS_DE[now.month - 1]} {now.year}"
    content = re.sub(r"\*\*Generated:\*\* .+", f"**Generated:** {date_str}", content)
    content = re.sub(
        r"\*\*Generation Method:\*\* .+",
        "**Generation Method:** Automated (update_sbom.py)",
        content,
    )
    md_changes.append(f"  SBOM.md: Generated → {date_str}")

    if apply_mode:
        SBOM_MD_PATH.write_text(content)

    return md_changes


def main():  # noqa: PLR0912, PLR0915
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
    node_major = parse_dockerfile_node_image(NODE_DOCKERFILE_PATH)
    project_version = parse_pyproject_version(PYPROJECT_PATH)
    project_license = parse_license_spdx(LICENSE_PATH)

    changes = []
    bom_ref_renames: dict[str, str] = {}  # old_ref → new_ref

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

    now = datetime.now(UTC)

    # Sync docs/SBOM.md independently — works even when SBOM.json is already current
    system_deps = _get_system_deps(sbom.get("components", []))
    md_changes = sync_sbom_md(
        py_versions,
        npm_versions,
        python_image_tag,
        node_major,
        project_version,
        project_license,
        apply_mode,
        now,
        system_deps=system_deps,
    )

    if not changes and not md_changes:
        print("✓ SBOM.json and docs/SBOM.md are up to date. No changes needed.")
        return

    # Bump SBOM.json metadata only when its own components changed
    if changes:
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

    all_changes = changes + md_changes
    print(f"{'APPLYING' if apply_mode else 'PREVIEW'}: {len(all_changes)} change(s):")
    for c in all_changes:
        print(c)

    if apply_mode:
        if changes:
            SBOM_PATH.write_text(json.dumps(sbom, indent=2, ensure_ascii=False) + "\n")
        targets = ([SBOM_PATH.name] if changes else []) + (["docs/SBOM.md"] if md_changes else [])
        print(f"\n✓ Updated: {' + '.join(targets)}.")
    else:
        targets = ([SBOM_PATH.name] if changes else []) + (["docs/SBOM.md"] if md_changes else [])
        print(f"\nRun with --apply to write changes to {' and '.join(targets)}")


if __name__ == "__main__":
    main()
