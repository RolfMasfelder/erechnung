---
name: project_structure
display_name: Project Structure & File Organization
version: 1.0.0
author: Rolf Masfelder
description: Rules for organizing files and scripts in the project
---

# Project Structure Rules

## Script Files

**CRITICAL RULE**: All shell scripts and utility scripts MUST be placed in the `scripts/` directory.

### Shell Scripts (*.sh, *.bat)
- **Location**: Always `scripts/` directory
- **Never** create .sh or .bat files in project root
- Examples:
  - `scripts/run_tests_docker.sh`
  - `scripts/run_e2e_container.sh`
  - `scripts/security_audit.sh`

### Utility Python Scripts
Small utility Python scripts (not part of Django app) should also go to `scripts/`:
- Example: `scripts/extract_pdf_xml.py`
- Example: `scripts/scan_directory.py`

### Exceptions
Only scripts that belong to specific components may stay in their directories:
- `api-gateway/*.sh` (component-specific scripts)
- `k8s/kind/*.sh` (Kubernetes setup scripts)
- `project_root/manage.py` (Django management command)

## Root Directory

Keep the project root clean and minimal:
- Configuration files only (.env, docker-compose.yml, pyproject.toml, etc.)
- Documentation files (README.md, TODO.md, etc.)
- Essential build files (Dockerfile, requirements.txt)

**Never create in root:**
- Shell scripts (→ `scripts/`)
- Utility scripts (→ `scripts/`)
- Test files (→ appropriate test directories)
- Temporary files
