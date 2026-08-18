---
name: github_actions
display_name: GitHub Actions & Workflows
version: 1.0.0
author: Rolf Masfelder
description: Reference for GitHub Actions versions and workflow conventions used in this project
---

# GitHub Actions & Workflows

Use this skill when creating or editing GitHub Actions workflow files (`.github/workflows/*.yml`). When editing an existing workflow, apply these conventions only to the actions and steps you are adding or modifying. Do not upgrade unrelated actions unless explicitly asked.

## Current Action Versions (Stand: April 2026)

Always use these versions when referencing actions. Do NOT use older major versions. If an action is not listed in the version tables below, state that no approved version is on record and ask the user to confirm the version before including it in a workflow.

### Core Actions (GitHub)

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `actions/checkout` | `@v6` | Node 24 | Runner v2.329.0+ required (github-hosted `ubuntu-latest` already meets this; for self-hosted runners, add a comment citing this minimum) |
| `actions/setup-python` | `@v6` | Node 24 | Runner v2.327.1+ required (see above) |
| `actions/setup-node` | `@v6` | Node 24 | Auto-caching since v5+. **Note:** the action's Node runtime (Node 24) is distinct from the project Node version installed for builds (`node-version: '24'`). |
| `actions/upload-artifact` | `@v7` | Node 24 | Breaking: `path` input replaced by `archive`. Use `archive: path/to/files` in generated steps. ESM. |

### Docker Actions

| Action | Version | Node Runtime | Notes |
|--------|---------|-------------|-------|
| `docker/setup-buildx-action` | `@v4` | Node 24 | `install` input removed |
| `docker/build-push-action` | `@v7` | Node 24 | ESM; deprecated env vars removed. Removed: `DOCKER_BUILDKIT` (now always enabled). Do not emit these in generated workflows. |
| `docker/login-action` | `@v4` | Node 24 | |

### Security & Signing

| Action | Version | Notes |
|--------|---------|-------|
| `sigstore/cosign-installer` | `@v4` | Installs Cosign v3 binary. Note: the v3.x installer action only supports Cosign v2 binary — use `@v4` to get Cosign v3. |
| `aquasecurity/trivy-action` | `@v0.36.0` | Uses `v` prefix tags after supply chain attack fix. Always set `with: version: 'vX.Y.Z'` explicitly to pin the Trivy **binary** — the action's own bundled default lags behind the latest Trivy release (check `repos/aquasecurity/trivy/releases/latest` via `gh api` for current binary version). |

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
- Node version: `24`
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
      project_root/ frontend/src/  # project_root/ is the literal Django source directory in this repo
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
| `dependabot-auto-merge.yml` | Auto-merge Dependabot minor/patch PRs | pull_request (dependabot) |
| `e2e-tests.yml` | Playwright E2E in containers | push (frontend paths) |
| `update-integration-tests.yml` | Update migration tests | tag `v*.*.*` |
