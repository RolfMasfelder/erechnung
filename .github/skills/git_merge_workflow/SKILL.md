---
name: git_merge_workflow
display_name: Git Merge Workflow
version: 1.0.0
author: Rolf Masfelder
description: Safe merge workflow for two-remote setup (origin + github) to avoid force-pushes
---

# Git Merge Workflow (Two-Remote Setup)

## Problem

This project uses two independent Git remotes:
- `origin` → local mirror (always push)
- `github` → GitHub with Actions and Dependabot (always push)

GitHub's `main` receives Dependabot PR auto-merges independently. If a local feature branch is merged into `main` without pulling from both remotes first, push to one remote will be rejected, requiring a rebase that invalidates commit hashes on the other remote → force-push needed.

## GitHub Branch Protection on `main`

GitHub enforces branch protection rules on `main`:
- **No direct pushes** — `git push github main` is rejected with `GH013: Repository rule violations`
- **Changes must go through a Pull Request** (from `dev` or a feature branch)
- **4 required status checks** must pass before merge
- **No merge commits** in the branch (squash or rebase merge only via PR UI)

**Consequence:** Never run `git push github main` directly. Always create a PR.

## Required Workflow: Merge dev into main

**Always execute these steps in order:**

```bash
# 1. Switch to main and sync from BOTH remotes
git checkout main
git pull origin main
git pull github main    # picks up any Dependabot auto-merges

# 2. Push the source branch (dev) to github if not already up to date
git push github dev

# 3. Create a PR on GitHub: dev → main
# (use mcp_github_create_pull_request or GitHub UI)
# Wait for all CI checks to pass, then merge via PR UI

# 4. After GitHub merges the PR, sync origin:
git pull github main
git push origin main
```

## When This Applies

- Merging `dev` or any feature branch into `main`
- After a CI workflow is green and ready for release
- Before any release tag

## When This Does NOT Apply

- Pushing feature branches to `github` (no branch protection there)
- Pushing anything to `origin` (local mirror — no branch protection)

## Why Both Pulls Are Necessary

Dependabot auto-merges PRs on GitHub's `dev` (since 2026-05-02). These commits don't exist on `origin` or locally. Without `git pull github dev`, the local `dev` diverges from GitHub's `dev`, causing conflicts on the next PR.

## Daily Workflow (Dependabot sync)

Dependabot merges minor/patch updates automatically into `dev` every Monday (or whenever a PR passes CI). To stay in sync:

```bash
# At the start of each working session:
git checkout dev
git pull github dev      # picks up Dependabot auto-merges into dev
git push origin dev      # keep local mirror in sync

# After your own work:
git push origin dev
git push github dev
```

This ensures `dev` never falls behind GitHub and PRs into `main` are always conflict-free.
