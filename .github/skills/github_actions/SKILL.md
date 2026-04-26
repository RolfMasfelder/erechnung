---
name: github_actions
display_name: GitHub Actions & Workflows
version: 1.0.0
author: Rolf Masfelder
description: Reference for GitHub Actions versions and workflow conventions used in this project
---

# GitHub Actions & Workflows

Use this skill when creating or editing GitHub Actions workflow files (`.github/workflows/*.yml`).

## Current Action Versions (Stand: April 2026)

Always use these versions when referencing actions. Do NOT use older major versions.

### Core Actions (GitHub)

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `actions/checkout` | `@v6` | Node 24 | Requires runner v2.329.0+ |
| `actions/setup-python` | `@v6` | Node 24 | Requires runner v2.327.1+ |
| `actions/setup-node` | `@v6` | Node 24 | Auto-caching since v5+ |
| `actions/upload-artifact` | `@v7` | Node 24 | Breaking: new `archive` param, ESM |

### Docker Actions

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `docker/setup-buildx-action` | `@v4` | Node 24 | `install` input removed |
| `docker/build-push-action` | `@v7` | Node 24 | ESM; deprecated env vars removed |
| `docker/login-action` | `@v4` | Node 24 | |

### Security & Signing

| Action | Version | Notes |
|--------|---------|-------|
| `sigstore/cosign-installer` | `@v4` | Installs Cosign v3; v3.x installer only supports Cosign v2 |
| `aquasecurity/trivy-action` | `@v0.35.0` | Uses `v` prefix tags after supply chain attack fix |

### Dependency & PR Management

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `peter-evans/create-pull-request` | `@v8` | Node 24 | |
| `dependabot/fetch-metadata` | `@v3` | Node 24 | |

### Infrastructure

| Action | Version | Notes |
|--------|---------|-------|
| `azure/k8s-set-context` | `@v4` | Node 20 (v4.0.2 latest) |

## Archived / DO NOT USE

| Action | Status | Replacement |
|--------|--------|-------------|
| `semgrep/semgrep-action` | **Archived** (April 2024) | `pip install semgrep && semgrep scan` |

## Project Conventions

### Workflow Files
- Location: `.github/workflows/`
- Python version: `3.13`
- Node version: `22`
- Runner: `ubuntu-latest`

### Security Scanning (SAST)
Semgrep runs as direct CLI, not as a GitHub Action:
```yaml
- name: Run Semgrep SAST analysis
  run: |
    pip install semgrep
    semgrep scan \
      --config p/python \
      --config p/django \
      --config p/javascript \
      --config p/owasp-top-ten \
      --error \
      --exclude='*/migrations/*' \
      --exclude='*/tests/*' \
      project_root/ frontend/src/
```

### Docker Build Convention
- Platform: `linux/amd64` only (no ARM64)
- Registry: `ghcr.io/rolfmasfelder/`
- Images signed with Cosign keyless signing
- Build cache: `type=gha`

### Existing Workflows

| File | Purpose | Trigger |
|------|---------|---------|
| `ci-cd.yml` | Lint → Test → Security Scan | push/PR on main, develop |
| `docker.yml` | Docker build, publish, sign | tag `v*`, weekly, PR |
| `deploy.yml` | K8s deployment via kustomize | tag `v*` |
| `dependencies.yml` | pip-compile + npm update with auto-PR | weekly Monday 6 AM |
| `e2e-tests.yml` | Playwright E2E in containers | push (frontend paths) |
| `update-integration-tests.yml` | Update migration tests | tag `v*.*.*` |
| `dependabot-auto-merge.yml` | Auto-merge minor/patch Dependabot PRs | PR events |
