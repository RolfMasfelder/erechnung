---
name: git-merge-workflow
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
# commit the merge. Then push the resolved main to both remotes
# (`git push origin main` and — since github/main is protected — open a PR if needed,
# or confirm with the user). Re-run step 0 to confirm all SHAs match before continuing.

# 2. Push the source branch (dev) to github if not already up to date
git push github dev
# If git push github dev is rejected (non-fast-forward): run `git pull github dev`
# to inspect the divergence. If the remote commits are safe to integrate,
# merge them (`git merge github/dev`), then re-push. Do not force-push.
# If the remote state is unexpected, stop and ask the user before proceeding.
```

**Step 3 — Create and merge PR:**

3a. Attempt PR creation (`mcp_github_mcp_se_create_pull_request` or the GitHub UI).
  - If a PR already exists for dev → main: use the existing PR ID.
  - If dev == main (no diff): skip to step 5.

3b. Wait for all 4 CI checks to pass.
  - If any check fails: push a fix to dev (`git push github dev`), then return to 3b.

3c. Merge the PR only after CI is green (GitHub UI or `mcp_github_mcp_se_merge_pull_request`).

3d. Poll `git ls-remote github refs/heads/main` every 30 seconds for up to 5 minutes. If the merge commit does not appear within 5 minutes, stop and ask the user to confirm the merge completed before continuing.

```bash
# 4. After GitHub merges the PR: sync main, then merge back into dev
git pull github main
git push origin main    # keep local mirror in sync
# If git push origin main is rejected: run `git pull origin main` to inspect the divergence.
# If origin/main has commits not on github/main, this indicates an unexpected divergence.
# Do not merge or force-push. Stop and ask the user to inspect origin/main manually
# before proceeding, as pushing those commits to github/main would require a PR.

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

For feature branches other than `dev`: substitute the feature branch name wherever `dev` appears in the Required Workflow. The Daily Workflow applies to `dev` only.

### Feature Branch Notes

Feature branches are not protected on GitHub. The same 4 required status checks still apply to the PR into main. After merging a feature branch PR, perform step 5 on both the feature branch and on dev: merge main into dev so dev stays current. Then delete the feature branch if it is no longer needed (`git push github --delete <feature-branch>` and `git push origin --delete <feature-branch>`).

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
