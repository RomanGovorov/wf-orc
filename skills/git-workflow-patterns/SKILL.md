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

A branching model defines how feature work, releases, and hotfixes flow through a repository.

- **Trunk-Based Development** — all work through `main`; short-lived branches; continuous deployment
- **GitHub Flow** — lightweight; feature branches + pull requests; merge when ready
- **GitFlow** — structured; `develop`, `feature/*`, `release/*`, `hotfix/*` branches; scheduled releases
- **GitLab Flow** — environment-based branches (`staging`, `production`); merge down, not up

### Commit Philosophy

Commits are the atomic unit of change. A well-crafted commit history is a narrative — readable, searchable, and bisectable.

- **Atomic commits** — one logical change per commit
- **Descriptive messages** — imperative mood, present tense, explain *why* not *what*
- **Signed commits** — GPG/SSH signatures for provenance
- **Conventional Commits** — machine-readable format enabling automated changelogs and semver

## Patterns

### 1. Trunk-Based Development

All development flows through `main`. Short-lived feature branches (< 1 day) are merged frequently.

```bash
git checkout main && git pull --rebase origin main
git checkout -b feat/add-search-filter
git add -p                          # stage hunks selectively
git commit -m "feat(search): add date range filter"
git fetch origin && git rebase origin/main
git push -u origin feat/add-search-filter
```

**When to use:** Continuous deployment, small teams (< 10 devs), feature flags available, high test coverage (> 80%).

**Rules:** Feature branches live < 1 day; `main` always deployable; no long-lived branches; feature flags for incomplete work.

### 2. GitHub Flow (Feature Branches + PR)

Simple, opinionated: branch off `main`, commit, open PR, review, merge.

```bash
git checkout main && git pull origin main
git checkout -b feat/TICKET-123-user-profile
git commit -m "feat(profile): add avatar upload endpoint"
git commit -m "feat(profile): add avatar validation (max 5MB, PNG/JPG)"
git fetch origin && git rebase origin/main
git push --force-with-lease origin feat/TICKET-123-user-profile
```

**Merge Strategies:**

| Strategy | When to Use | History |
|---|---|---|
| Squash merge | Small PRs, single-purpose | Clean linear history |
| Rebase merge | Multi-commit PRs with logical chunks | Linear, preserves commits |
| Merge commit | Large PRs, complex feature | Preserves branch topology |

### 3. Conventional Commits (feat/fix/chore + scope + breaking)

Machine-readable commit messages that enable automated changelogs and semantic version bumps.

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
| `style` | — | Formatting (no logic) |
| `refactor` | — | Code restructuring |
| `perf` | PATCH | Performance improvement |
| `test` | — | Adding/updating tests |
| `build` | — | Build system or deps |
| `ci` | — | CI/CD config changes |
| `chore` | — | Maintenance tasks |
| `revert` | PATCH | Reverting a commit |

**Examples:**

```bash
git commit -m "feat(auth): add OAuth2 Google login

Implement Google OAuth2 flow using PKCE. Adds /auth/google/callback
endpoint and stores refresh token in encrypted cookie.

Refs: TICKET-789"

git commit -m "feat(api)!: migrate to v2 response format

BREAKING CHANGE: All API responses now use { data, meta, errors }
envelope format. Clients must update parsers.

Refs: TICKET-800"
```

**commitlint configuration:**

```javascript
// commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor',
      'perf', 'test', 'build', 'ci', 'chore', 'revert',
    ]],
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case']],
    'body-max-line-length': [0],
    'footer-max-line-length': [0],
  },
};
```

### 4. PR/MR Template and Review Checklist

**PR Template (`.github/PULL_REQUEST_TEMPLATE.md`):**

```markdown
## Summary
<!-- One-sentence description -->

## Type
- [ ] feat: New feature
- [ ] fix: Bug fix
- [ ] refactor / docs / test / chore

## Related Issue
Closes #

## Changes
-

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guide
- [ ] Self-review completed
- [ ] No new warnings introduced
- [ ] Documentation updated (if applicable)
```

**Review Checklist:**

| Category | Check |
|---|---|
| Correctness | Does the code do what the PR description says? |
| Correctness | Are edge cases handled? |
| Security | Input validation, auth checks, SQL injection |
| Performance | N+1 queries, unnecessary allocations, missing indexes |
| Readability | Clear naming, appropriate abstractions |
| Tests | Adequate coverage, meaningful assertions |
| Architecture | Consistent with existing patterns |
| Error Handling | Graceful failures, meaningful error messages |

## Key Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Merge commits in feature branches | Creates tangled history | Rebase feature branches onto `main` |
| Committing secrets (`API_KEY`, `.env`) | Security breach | `.gitignore` + pre-commit `detect-private-key` hook |
| Giant "WIP" commits | Impossible to review or bisect | Atomic commits: one logical change per commit |
| `git push --force` on shared branches | Overwrites others' work | `--force-with-lease` on feature branches only |
| Merge conflict resolution without testing | Silent regressions | Run full test suite after resolving conflicts |
| No branch protection rules | Accidental pushes to `main` | Enable branch protection: require PR + status checks |
| Cherry-picking without `-x` | Lost provenance | Always use `git cherry-pick -x <sha>` |
| Long-lived feature branches | Massive merge conflicts | Merge or rebase daily; use feature flags |
| Vague commit messages ("fix", "update") | Useless history | Conventional Commits: `fix(auth): handle expired token` |

## Best Practices

1. **Rebase feature branches, merge to main** — keep branches up-to-date via rebase; merge (or squash-merge) to `main`
2. **One logical change per commit** — makes `git bisect`, `git revert`, and code review straightforward
3. **Never force-push to shared branches** — `main`, `develop`, `release/*` are protected
4. **Sign your commits** — `git config --global commit.gpgsign true` for provenance
5. **Use `.gitignore` aggressively** — never commit build artifacts, IDE settings, secrets
6. **Write imperative commit messages** — "Add feature" not "Added feature"
7. **Protect `main` with branch rules** — require PR reviews, status checks, signed commits
8. **Automate with hooks** — pre-commit for linting, commit-msg for conventional commits
9. **Keep branches short-lived** — merge or rebase at least daily
10. **Document your workflow** — add a `CONTRIBUTING.md` describing conventions
11. **Use `git reflog` for recovery** — lost commits are almost always recoverable
12. **Tag from the integration/release branch** — typically `main` or `release/*`; never from feature branches

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for merge conflict resolution, semantic versioning, Git hooks setup, cherry-pick and hotfix workflows

## See also

> **See also**: `ci-cd-patterns` — CI/CD pipeline implementation, Docker, Terraform, K8s deployment.

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Git | (query "Git") | Advanced merge strategies, rebase workflows |
| Conventional Commits | (query "Conventional Commits") | Specification updates |
| pre-commit | (query "pre-commit framework") | Hook configuration |
