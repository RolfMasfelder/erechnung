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

## Required Workflow: Merge Feature Branch into Main

**Always execute these steps in order:**

```bash
# 1. Switch to main
git checkout main

# 2. Pull from BOTH remotes (order doesn't matter)
git pull origin main
git pull github main

# 3. Merge the feature branch
git merge <feature-branch>

# 4. Push to BOTH remotes
git push origin main
git push github main
```

## When This Applies

- Merging any local branch into `main`
- After completing work on a feature branch
- Before any release

## When This Does NOT Apply

- Pushing feature branches (they only exist locally + remotes, no Dependabot interference)
- Direct commits on `main` (should be rare)

## Why Both Pulls Are Necessary

Dependabot auto-merges PRs on GitHub's `main`. These commits don't exist on `origin` or locally. Without `git pull github main`, the local `main` diverges from GitHub's `main`, causing rejected pushes after merge.
