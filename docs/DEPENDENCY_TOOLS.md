# Dependency Management Tools

This directory contains two powerful scripts to help you manage Python dependencies and prevent the errors you've been experiencing.

## Scripts Overview

### 1. `simple_requirements_check.py` - Quick Requirements Validation
A focused script that compares your `requirements.txt` with installed packages.

**Features:**
- ✅ Detects missing packages
- ⚠️ Identifies version mismatches
- 📈 Shows outdated packages
- 📦 Lists extra installed packages not in requirements.txt
- 🐳 Docker support

**Usage:**
```bash
# Local environment
python simple_requirements_check.py

# Docker environment
python simple_requirements_check.py --docker
```

### 2. `check_dependencies.py` - Comprehensive Dependency Analysis
A comprehensive tool that analyzes dependencies, security vulnerabilities, and code usage.

**Features:**
- 🔍 Compares requirements.txt with actually imported modules
- 🔒 Security vulnerability scanning with Safety
- 📈 Latest version checking from PyPI
- 📦 Unused dependency detection
- 🐳 Docker support
- 📊 Detailed reporting

**Usage:**
```bash
# Full analysis (local)
python check_dependencies.py

# Full analysis (Docker)
python check_dependencies.py --docker

# Security focus only
python check_dependencies.py --docker --security

# Show update commands
python check_dependencies.py --docker --update

# Find unused dependencies
python check_dependencies.py --docker --unused
```

## Why These Tools Help

### Problem Prevention
The dependency conflicts you experienced (like `ruff-pre-commit==0.12.5` not being found) happen when:
1. Package names change or get deprecated
2. Version constraints conflict between packages
3. Requirements.txt gets out of sync with actual needs

### Solutions Provided
- **Early Detection**: Catch issues before they break CI/CD
- **Version Management**: See what needs updating and what's causing conflicts
- **Security**: Identify vulnerable packages immediately
- **Cleanup**: Remove unused dependencies that can cause conflicts

## Example Output

### Simple Requirements Check
```
📋 Found 40 packages in requirements.txt
📦 Found 129 installed packages

⚠️  VERSION MISMATCHES (2):
   • django: Version mismatch: required 5.1.0, installed 5.1
   • ruff: Package name changed: use 'ruff' instead of 'ruff-pre-commit'

📈 OUTDATED PACKAGES (12):
   • safety: 2.3.5 → 3.6.0
   • django: 5.1.0 → 5.2.4
```

### Comprehensive Analysis
```
🔒 SECURITY VULNERABILITIES:
   ❌ safety (2.3.5):
      • Known security issue - update to 3.6.0+

📦 POTENTIALLY UNUSED DEPENDENCIES:
   ❓ fastapi (0.104.1) - Not found in code imports
   ❓ uvicorn (0.24.0) - Not found in code imports

💡 UPDATE COMMANDS:
   pip install safety==3.6.0
   pip install django==5.2.4
```

## Integration with CI/CD

Add these checks to your development workflow:

### Local Development
```bash
# Before committing
python simple_requirements_check.py --docker

# Weekly dependency health check
python check_dependencies.py --docker --update
```

### Pre-commit Hook
Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: check-requirements
      name: Check requirements.txt
      entry: python simple_requirements_check.py --docker
      language: system
      pass_filenames: false
```

### CI/CD Pipeline
Add to your GitHub Actions workflow:
```yaml
- name: Check Dependencies
  run: |
    python simple_requirements_check.py --docker
    python check_dependencies.py --docker --security
```

## Best Practices

1. **Regular Checks**: Run weekly to catch issues early
2. **Before Updates**: Always check before upgrading packages
3. **Security First**: Use `--security` flag to prioritize vulnerabilities
4. **Clean Requirements**: Remove unused dependencies found by the tool
5. **Version Pinning**: Use exact versions (`==`) for critical packages

## Docker Integration

Both scripts support Docker environments and will automatically:
- Run commands inside your `web` container
- Use the container's Python environment
- Respect your Docker Compose setup

This ensures consistency between local development and production environments.

## Troubleshooting

### Common Issues

**"Safety not found"**:
```bash
# Update requirements.txt with safety==3.6.0
# Rebuild container
docker compose build web --no-cache
```

**"Package not found"**:
- Check if package name changed (e.g., `ruff-pre-commit` → `ruff`)
- Verify package exists on PyPI
- Check for typos in requirements.txt

**"Version conflicts"**:
- Use the comprehensive checker to see dependency trees
- Consider using compatible versions (`>=` instead of `==`)
- Remove conflicting unused packages

## Regular Maintenance

Run this monthly workflow:

1. **Security Check**: `python check_dependencies.py --docker --security`
2. **Update Check**: `python check_dependencies.py --docker --update`
3. **Cleanup**: `python check_dependencies.py --docker --unused`
4. **Validation**: `python simple_requirements_check.py --docker`

This will keep your dependencies secure, up-to-date, and conflict-free!
