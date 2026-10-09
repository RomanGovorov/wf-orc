# Advanced Patterns: Git Workflow Patterns

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Merge Conflict Resolution Strategy

Systematic approach to resolving conflicts without losing context or introducing bugs.

```bash
# Prevention: rebase frequently
git fetch origin
git rebase origin/main

# If conflict occurs during rebase:
# 1. Understand the conflict
git status

# 2. Open the conflicted file — look for markers:
# <<<<<<< HEAD             ← origin/main (upstream) side — NOT your branch!
# =======
# >>>>>>> abc1234 (commit)  ← YOUR commit being replayed
# This is INVERTED relative to merge: during `git rebase origin/main`, git
# checks out the upstream as HEAD and replays your commits onto it.

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

# Combined diff against all parents of a merge commit
git diff --cc <file>
```

## Semantic Versioning + Git Tagging

### Manual Tagging

```bash
# Annotated tag (recommended for releases)
git tag -a v1.2.0 -m "feat: user profile feature"
git push origin v1.2.0

# List tags
git tag -l "v1.*"

# Delete tag (local + remote)
git tag -d v1.2.0
git push origin --delete v1.2.0
```

### Semver Rules

```
MAJOR.MINOR.PATCH

MAJOR — breaking changes (feat!:, BREAKING CHANGE:)
MINOR — new features (feat:)
PATCH — bug fixes (fix:, perf:)

Pre-release: v1.0.0-alpha.1, v1.0.0-beta.2, v1.0.0-rc.1
Build metadata: v1.0.0+build.123
```

### Automated Release with semantic-release

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

### GitHub Actions Release Workflow

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
      - uses: actions/setup-node@v5
        with:
          node-version: 22
      - run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Git Hooks (pre-commit + commitlint)

### pre-commit Framework

```yaml
# .pre-commit-config.yaml
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
    rev: ^3.0.0
    hooks:
      - id: prettier
        types_or: [javascript, jsx, ts, tsx, json, yaml, markdown]
```

### Husky + commitlint (Node.js)

```bash
# Install
npm install -D husky @commitlint/cli @commitlint/config-conventional lint-staged eslint-config-prettier

# Initialize husky
npx husky init

# Add commit-msg hook
echo 'npx --no-install -- commitlint --edit ${1}' > .husky/commit-msg
chmod +x .husky/commit-msg

# Add pre-commit hook
cat > .husky/pre-commit << 'EOF'
npm run lint:staged
npm run typecheck
EOF
chmod +x .husky/pre-commit
```

### lint-staged Configuration

```json
{
  "scripts": {
    "lint:staged": "lint-staged",
    "typecheck": "tsc --noEmit"
  },
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

## Cherry-Pick and Hotfix Workflow

### Hotfix Process

```bash
# 1. Create hotfix branch from the release tag
git checkout -b hotfix/fix-payment-timeout v2.3.1

# 2. Make the fix
git commit -m "fix(payment): handle timeout in Stripe webhook"

# 3. Merge hotfix back to main
git checkout main
git merge --no-ff hotfix/fix-payment-timeout

# 4. Cherry-pick the fix to the release branch
git checkout release/2.3
git cherry-pick -x <commit-sha>

# 5. Tag the new release
git tag -a v2.3.2 -m "fix: payment timeout hotfix"
git push origin v2.3.2

# 6. Clean up
git checkout main
git branch -d hotfix/fix-payment-timeout
```

### Cherry-Pick Best Practices

```bash
# Cherry-pick a range of commits
git cherry-pick <sha1>^..<sha3>

# Cherry-pick without committing (review first)
git cherry-pick --no-commit <sha>
git diff --cached
git commit

# Cherry-pick with provenance
git cherry-pick -x <sha>
# Adds "(cherry picked from commit <sha>)" to message

# Resolve conflicts during cherry-pick
git cherry-pick <sha>
# If conflict:
git status
git add <resolved-files>
git cherry-pick --continue
# Or abort:
git cherry-pick --abort
```

## Deep Dive: Rebase vs Merge

### When to Rebase

- Feature branch is behind `main` — rebase to incorporate latest changes
- You want a clean, linear history
- You are the only one working on the branch

### When to Merge

- Multiple people are working on the same branch
- You want to preserve the branch topology
- Creating a merge commit makes the history clearer

### The Golden Rule

**Never rebase a public/shared branch.** Rebasing rewrites history — if others have based work on those commits, their history diverges.

## Edge Cases

### Recovering Lost Commits

```bash
# Find lost commits via reflog
git reflog

# Recover a specific commit
git cherry-pick <sha-from-reflog>

# Or reset to it
git reset --hard <sha-from-reflog>
```

### Detached HEAD State

```bash
# You're in detached HEAD — check out a branch to save work
git log --oneline -5  # find your commit
git checkout -b save-my-work  # create branch from current position
git checkout main
git merge save-my-work
```

### Undoing the Last Commit

```bash
# Keep changes staged
git reset --soft HEAD~1

# Keep changes unstaged
git reset HEAD~1

# Discard all changes (destructive!)
git reset --hard HEAD~1
```

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
