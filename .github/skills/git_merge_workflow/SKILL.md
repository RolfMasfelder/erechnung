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
- **Only merge commits** allowed (no squash, no rebase)

**Consequence:** Never run `git push github main` directly. Always create a PR.

## Required Workflow: Merge dev into main

> **Use this workflow ONLY when you intend to release dev → main via PR.**
> Do NOT use this workflow just to sync with Dependabot — use the Daily Workflow instead.

**Always execute these steps in order:**

```bash
# 0. Verify all refs are in sync before starting.
#    Run the for-each-ref command below. If any SHA mismatches exist between
#    local, origin/main, and github/main, pull from both remotes and resolve
#    conflicts before proceeding.
git for-each-ref --format='%(refname:short) %(objectname:short)' refs/heads/main refs/heads/dev refs/remotes/origin/main refs/remotes/origin/dev refs/remotes/github/main refs/remotes/github/dev

# 1. Switch to main and sync from BOTH remotes
git checkout main
git pull origin main
git pull github main    # picks up any Dependabot auto-merges
# If either pull results in a merge conflict: stop, resolve conflicts manually,
# commit the merge, then re-run step 0 to confirm sync before continuing.

# 2. Push the source branch (dev) to github if not already up to date
git push github dev

# 3. Create a PR on GitHub: dev → main
# Use mcp_github_mcp_se_create_pull_request or the GitHub UI.
# If PR creation fails because a PR already exists for dev → main, locate and use the existing PR.
# If PR creation fails because dev and main are already identical (no diff), skip steps 3–4 and go to step 5.
#
# If CI checks fail:
#   (a) Do NOT merge the PR.
#   (b) Push a fix commit to dev on github (git push github dev).
#   (c) The existing open PR will pick up the new commit automatically.
#   (d) Wait for CI to pass again before merging.
#
# Merge the PR using the GitHub UI or mcp_github_mcp_se_merge_pull_request.
# Do NOT proceed to step 4 until `git ls-remote github refs/heads/main` shows the new merge commit.
# Wait for user confirmation or poll until the merge commit appears.

# 4. After GitHub merges the PR: sync main, then merge back into dev
git pull github main
git push origin main    # keep local mirror in sync
# If git push origin main is rejected: run `git pull origin main` to inspect the divergence.
# If origin/main has commits not on github/main, merge origin/main into local main, then re-push.
# Do not force-push.

# 5. Merge main back into dev to stay in sync
# main may have Dependabot auto-merge commits that dev doesn't have yet.
# Without this step, the next PR from dev → main will include unrelated Dependabot commits.
git checkout dev
git pull github main    # fetch github/main; git pull merges it into current branch (dev)
git push origin dev
git push github dev
```

## When This Applies

- Merging `dev` or any feature branch into `main`
- After a CI workflow is green and ready for release
- Before any release tag

For feature branches other than `dev`: substitute the feature branch name wherever `dev` appears in the Required Workflow. Step 5 (merge main back into dev) should also be performed on the feature branch to keep it current. The Daily Workflow applies to `dev` only.

## When This Does NOT Apply

- Pushing feature branches to `github` (no branch protection there)
- Pushing anything to `origin` (local mirror — no branch protection)

## Why Both Pulls Are Necessary

Dependabot auto-merges PRs into GitHub's `main` (since 2026-05-12). These commits don't exist on `origin` or locally. Without `git pull github main`, the local `main` diverges from GitHub's `main`, and merging `dev` into `main` will be rejected or cause conflicts.

## Daily Workflow (Dependabot sync)

> **Use this workflow ONLY at the start of a session or after a Dependabot merge, when no PR to main is being created.**
> If you intend to merge dev → main via PR, use the Required Workflow above instead.

Dependabot merges minor/patch updates automatically into `main` every Monday (or whenever a PR passes CI). To stay in sync:

```bash
# At the start of each working session:
git checkout dev
git pull github dev      # picks up any direct changes to dev on GitHub
git fetch github main    # fetch github/main without merging into dev
git merge github/main    # explicitly merge fetched github/main into dev
git push origin dev
git push github dev

# After your own work:
git push origin dev
git push github dev
```

This ensures `dev` never falls behind `main` and PRs into `main` are always conflict-free.

Check SHA on all repos (local, origin, github) before merging to confirm they are in sync. If you see a mismatch, do not merge until you have pulled from both remotes and resolved any conflicts.

```bash
git for-each-ref --format='%(refname:short) %(objectname:short)' refs/heads/main refs/heads/dev refs/remotes/origin/main refs/remotes/origin/dev refs/remotes/github/main refs/remotes/github/dev
```
