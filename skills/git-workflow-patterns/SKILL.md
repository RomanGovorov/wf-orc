---
name: git-workflow-patterns
description: Git workflow patterns — branching strategies, conventional commits, PR review, merge conflict resolution, release tagging, Git hooks. Use when managing version control, setting up CI triggers, or establishing team conventions.
priority: 5
paths:
  - "**/.husky/**"
  - "**/.pre-commit-config*"
  - "**/commitlint*"
  - "**/.gitconfig"
  - "**/.gitattributes"
  - "**/.gitmodules"
  - "**/CHANGELOG*"
  - "**/.releaserc*"
  - "**/semantic-release*"
---

# Git Workflow Patterns

Complete guide to professional Git workflows — branching strategies, conventional commits, PR review processes, merge conflict resolution, semantic versioning, and Git hooks.

> **See also**: `ci-cd-patterns` — CI/CD pipeline implementation, Docker, Terraform, K8s deployment.

## When to Use This Skill

- When setting up a Git branching strategy for a new project
- When establishing commit message conventions
- When configuring CI/CD pipeline triggers based on branches/tags
- When creating PR/MR review processes and templates
- When resolving complex merge conflicts
- When setting up release tagging and changelog automation
- When configuring pre-commit hooks and commit-msg linters
- When managing hotfix workflows for production incidents

## Core Concepts

### Branching Models

A branching model defines how feature work, releases, and hotfixes flow through a repository. The right model depends on team size, release cadence, and deployment strategy.

- **Trunk-Based Development** — all work flows through `main`; short-lived feature branches; continuous deployment
- **GitHub Flow** — lightweight; feature branches + pull requests; merge when ready
- **GitFlow** — structured; `develop`, `feature/*`, `release/*`, `hotfix/*` branches; suited for scheduled releases
- **GitLab Flow** — environment-based branches (`staging`, `production`); merge down, not up

### Commit Philosophy

Commits are the atomic unit of change. A well-crafted commit history is a narrative — readable, searchable, and bisectable.

- **Atomic commits** — one logical change per commit
- **Descriptive messages** — imperative mood, present tense, explain *why* not *what*
- **Signed commits** — GPG/SSH signatures for provenance
- **Conventional Commits** — machine-readable format enabling automated changelogs and semver

---

## Patterns

### 1. Trunk-Based Development

All development flows through `main`. Short-lived feature branches (< 1 day) are merged frequently. Feature flags control incomplete features.

```bash
# Workflow: branch, work, merge back same day
git checkout main
git pull --rebase origin main
git checkout -b feat/add-search-filter

# Work in small, atomic commits
git add -p                          # stage hunks selectively
git commit -m "feat(search): add date range filter"

# Rebase onto latest main before PR
git fetch origin
git rebase origin/main

# Push and open PR
git push -u origin feat/add-search-filter
```

**When to use:**
- Continuous deployment to production
- Small teams (< 10 developers)
- Feature flag infrastructure available
- High test coverage (> 80%)

**Rules:**
- Feature branches live < 1 day (max 2 days)
- `main` is always deployable
- No long-lived feature branches
- Feature flags for incomplete work

---

### 2. GitHub Flow (Feature Branches + PR)

Simple, opinionated workflow: branch off `main`, commit, open PR, review, merge.

```bash
# 1. Create feature branch from up-to-date main
git checkout main && git pull origin main
git checkout -b feat/TICKET-123-user-profile

# 2. Commit incrementally (atomic commits)
git commit -m "feat(profile): add avatar upload endpoint"
git commit -m "feat(profile): add avatar validation (max 5MB, PNG/JPG)"
git commit -m "test(profile): add avatar upload integration tests"

# 3. Keep branch updated (rebase, not merge)
git fetch origin
git rebase origin/main
# Resolve conflicts if any, then:
git rebase --continue

# 4. Push (force-push with lease after rebase)
git push --force-with-lease origin feat/TICKET-123-user-profile
```

**PR Title Convention:**

```
feat(scope): brief description [TICKET-123]
fix(scope): brief description [TICKET-456]
```

**Merge Strategies:**

| Strategy | When to Use | History |
|---|---|---|
| Squash merge | Small PRs, single-purpose | Clean linear history |
| Rebase merge | Multi-commit PRs with logical chunks | Linear, preserves commits |
| Merge commit | Large PRs, complex feature | Preserves branch topology |

---

### 3. Conventional Commits (feat/fix/chore + scope + breaking)

Machine-readable commit messages that enable automated changelogs, semantic version bumps, and filtering.

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**

| Type | Semver | Description |
|---|---|---|
| `feat` | MINOR | New feature |
| `fix` | PATCH | Bug fix |
| `docs` | — | Documentation only |
| `style` | — | Formatting, semicolons, etc. (no logic) |
| `refactor` | — | Code restructuring (no feature/fix) |
| `perf` | PATCH | Performance improvement |
| `test` | — | Adding or updating tests |
| `build` | — | Build system or external dependencies |
| `ci` | — | CI/CD configuration changes |
| `chore` | — | Maintenance tasks |
| `revert` | — | Reverting a previous commit |

**Examples:**

```bash
# Feature
git commit -m "feat(auth): add OAuth2 Google login

Implement Google OAuth2 flow using PKCE. Adds /auth/google/callback
endpoint and stores refresh token in encrypted cookie.

Refs: TICKET-789"

# Breaking change
git commit -m "feat(api)!: migrate to v2 response format

BREAKING CHANGE: All API responses now use { data, meta, errors }
envelope format. Clients must update parsers.

Refs: TICKET-800"

# Fix
git commit -m "fix(cart): prevent negative quantity on update

Quantity was not clamped to >= 1 in the update handler, allowing
negative values that broke price calculation.

Fixes: TICKET-801"
```

**commitlint configuration:**

```javascript
// commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat', 'fix', 'docs', 'style', 'refactor',
        'perf', 'test', 'build', 'ci', 'chore', 'revert',
      ],
    ],
    'scope-enum': [
      1,
      'always',
      ['auth', 'api', 'cart', 'profile', 'search', 'core', 'deps'],
    ],
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case']],
    'body-max-line-length': [0],
    'footer-max-line-length': [0],
  },
};
```

---

### 4. PR/MR Template and Review Checklist

A structured PR template ensures consistency and completeness.

**PR Template (`.github/PULL_REQUEST_TEMPLATE.md`):**

```markdown
## Summary
<!-- One-sentence description of what this PR does -->

## Type
- [ ] feat: New feature
- [ ] fix: Bug fix
- [ ] refactor: Code restructuring
- [ ] docs: Documentation
- [ ] test: Tests only
- [ ] chore: Maintenance

## Related Issue
Closes #

## Changes
<!-- Bullet list of changes -->
-
-

## Screenshots / Recordings
<!-- If UI changes, attach before/after -->

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] Edge cases covered

## Checklist
- [ ] Code follows project style guide
- [ ] Self-review completed
- [ ] Comments added for non-obvious logic
- [ ] No new warnings introduced
- [ ] Documentation updated (if applicable)
- [ ] Database migration included (if applicable)
- [ ] Environment variables documented (if new)

## Deployment Notes
<!-- Anything special about deploying this change? -->
```

**Review Checklist (for reviewers):**

| Category | Check |
|---|---|
| Correctness | Does the code do what the PR description says? |
| Correctness | Are edge cases handled? |
| Security | Input validation, auth checks, SQL injection |
| Performance | N+1 queries, unnecessary allocations, missing indexes |
| Readability | Clear naming, appropriate abstractions, comments |
| Tests | Adequate coverage, meaningful assertions |
| Architecture | Consistent with existing patterns |
| Error Handling | Graceful failures, meaningful error messages |

---

### 5. Merge Conflict Resolution Strategy

Systematic approach to resolving conflicts without losing context or introducing bugs.

```bash
# Prevention: rebase frequently
git fetch origin
git rebase origin/main

# If conflict occurs during rebase:
# 1. Understand the conflict
git status
# Shows which files have conflicts

# 2. Open the conflicted file — look for markers:
# <<<<<<< HEAD (your branch)
# =======
# >>>>>>> origin/main (incoming)

# 3. Resolve: keep both, keep one, or merge manually
# 4. Stage and continue
git add <resolved-file>
git rebase --continue

# If it gets too messy — abort and start fresh
git rebase --abort
```

**Resolution Strategies:**

| Scenario | Strategy |
|---|---|
| Both sides changed same logic | Understand intent, pick the more correct version |
| Refactor vs. new feature | Apply refactor first, then adapt new code |
| Auto-generated files | Regenerate after resolving source conflicts |
| Lock files (package-lock.json) | Accept either side, then regenerate (`npm install`) |
| Migration files | Keep both (they should be independent) |

**Tools:**

```bash
# Use merge tool for visual resolution
git mergetool --tool=vimdiff

# Configure default merge tool
git config --global merge.tool vscode
git config --global mergetool.vscode.cmd 'code --wait $MERGED'

# Three-way diff (base, ours, theirs)
git diff --cc <file>
```

---

### 6. Semantic Versioning + Git Tagging

Automate version bumps and changelogs from conventional commits.

```bash
# Manual tagging
git tag -a v1.2.0 -m "feat: user profile feature"
git push origin v1.2.0

# Lightweight tag (not recommended for releases)
git tag v1.2.0-rc.1

# List tags
git tag -l "v1.*"

# Delete tag (local + remote)
git tag -d v1.2.0
git push origin --delete v1.2.0
```

**Semver Rules:**

```
MAJOR.MINOR.PATCH

MAJOR — breaking changes (feat!:, BREAKING CHANGE:)
MINOR — new features (feat:)
PATCH — bug fixes (fix:, perf:)

Pre-release: v1.0.0-alpha.1, v1.0.0-beta.2, v1.0.0-rc.1
Build metadata: v1.0.0+build.123
```

**Automated Release with `semantic-release`:**

```javascript
// .releaserc.js
module.exports = {
  branches: [
    'main',
    { name: 'beta', prerelease: true },
    { name: 'alpha', prerelease: true },
  ],
  plugins: [
    '@semantic-release/commit-analyzer',
    '@semantic-release/release-notes-generator',
    '@semantic-release/changelog',
    ['@semantic-release/npm', { npmPublish: false }],
    '@semantic-release/git',
    '@semantic-release/github',
  ],
};
```

**GitHub Actions release workflow:**

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    branches: [main]

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

### 7. Git Hooks (pre-commit + commitlint)

Enforce code quality and commit conventions before code enters the repository.

**pre-commit framework (`.pre-commit-config.yaml`):**

```yaml
repos:
  # Python — Ruff linting + formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.1
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # General — trailing whitespace, end-of-file, etc.
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: detect-private-key

  # TypeScript — ESLint + Prettier
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.17.0
    hooks:
      - id: eslint
        files: \.[jt]sx?$
        types: [file]
        additional_dependencies:
          - eslint@9.17.0
          - "@typescript-eslint/eslint-plugin"
          - "@typescript-eslint/parser"

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks:
      - id: prettier
        types_or: [javascript, jsx, ts, tsx, json, yaml, markdown]
```

**Husky + commitlint (Node.js projects):**

```bash
# Install
npm install -D husky @commitlint/cli @commitlint/config-conventional

# Initialize husky
npx husky init

# Add commit-msg hook
echo 'npx --no -- commitlint --edit ${1}' > .husky/commit-msg
chmod +x .husky/commit-msg

# Add pre-commit hook
cat > .husky/pre-commit << 'EOF'
npm run lint:staged
npm run typecheck
EOF
chmod +x .husky/pre-commit
```

**lint-staged configuration (`package.json`):**

```json
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{js,json,md,yml}": [
      "prettier --write"
    ]
  }
}
```

---

### 8. Cherry-Pick and Hotfix Workflow

Apply specific commits to other branches — critical for production hotfixes.

```bash
# Hotfix workflow
# 1. Create hotfix branch from the release tag
git checkout -b hotfix/fix-payment-timeout v2.3.1

# 2. Make the fix
git commit -m "fix(payment): handle timeout in Stripe webhook"

# 3. Merge hotfix back to main (for next release)
git checkout main
git merge --no-ff hotfix/fix-payment-timeout

# 4. Cherry-pick the fix to the release branch
git checkout release/2.3
git cherry-pick <commit-sha>

# 5. Tag the new release
git tag -a v2.3.2 -m "fix: payment timeout hotfix"
git push origin v2.3.2

# 6. Clean up
git branch -d hotfix/fix-payment-timeout
```

**Cherry-pick best practices:**

```bash
# Cherry-pick a range of commits
git cherry-pick <sha1>^..<sha3>

# Cherry-pick without committing (review first)
git cherry-pick --no-commit <sha>
git diff --cached
git commit

# Cherry-pick with preserved author and timestamp
git cherry-pick -x <sha>
# Adds "(cherry picked from commit <sha>)" to message

# Resolve cherry-pick conflicts
git cherry-pick <sha>
# If conflict:
git status
# Edit conflicted files
git add <resolved-files>
git cherry-pick --continue
# Or abort:
git cherry-pick --abort
```

---

## Best Practices

1. **Rebase feature branches, merge to main** — keep feature branches up-to-date via rebase; use merge (or squash-merge) when integrating to `main`
2. **One logical change per commit** — makes `git bisect`, `git revert`, and code review straightforward
3. **Never force-push to shared branches** — `main`, `develop`, `release/*` are protected; force-push only to personal feature branches
4. **Sign your commits** — `git config --global commit.gpgsign true` for provenance verification
5. **Use `.gitignore` aggressively** — never commit build artifacts, IDE settings, secrets, or OS-specific files
6. **Write imperative commit messages** — "Add feature" not "Added feature" — mirrors `git merge` output
7. **Protect `main` with branch rules** — require PR reviews, status checks, and signed commits
8. **Automate with hooks** — pre-commit for linting, commit-msg for conventional commits, pre-push for tests
9. **Keep branches short-lived** — stale branches accumulate conflicts; merge or rebase at least daily
10. **Document your workflow** — add a `CONTRIBUTING.md` that describes branching, commit, and PR conventions
11. **Use `git reflog` for recovery** — lost commits are almost always recoverable via `git reflog`
12. **Tag releases from `main`** — never tag from feature branches; tags should be immutable

---

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Merge commits in feature branches | Creates tangled history | Rebase feature branches onto `main` |
| Committing secrets (`API_KEY`, `.env`) | Security breach, even after removal | `.gitignore` + pre-commit `detect-private-key` hook |
| Giant "WIP" commits | Impossible to review or bisect | Atomic commits: one logical change per commit |
| Ignoring `.gitignore` | Bloated repo, IDE noise in diffs | Start every project with a proper `.gitignore` |
| `git push --force` on shared branches | Overwrites others' work | `--force-with-lease` on feature branches only |
| Merge conflict resolution without testing | Silent regressions | Run full test suite after resolving conflicts |
| No branch protection rules | Accidental pushes to `main` | Enable branch protection: require PR + status checks |
| Cherry-picking without `-x` | Lost provenance — can't trace origin | Always use `git cherry-pick -x <sha>` |
| Long-lived feature branches | Massive merge conflicts, stale code | Merge or rebase daily; use feature flags |
| Vague commit messages ("fix", "update") | Useless history, hard to search | Conventional Commits: `fix(auth): handle expired token` |

---

## Context7 Integration

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Git | (query "Git") | Advanced merge strategies, rebase workflows |
| Conventional Commits | (query "Conventional Commits") | Specification updates |
| pre-commit | (query "pre-commit framework") | Hook configuration |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs`.
