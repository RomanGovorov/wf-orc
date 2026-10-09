# Code Examples: Git Workflow Patterns

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Conventional Commits

Standard commit message format for automated changelogs and semantic versioning.

```bash
# Format: <type>[optional scope]: <description>
#
# Types:
# - feat: new feature
# - fix: bug fix
# - docs: documentation only
# - style: formatting, no code logic change
# - refactor: code change that neither fixes a bug nor adds a feature
# - perf: performance improvement
# - test: adding or updating tests
# - chore: maintenance tasks (dependencies, CI config, etc.)
# - build: changes to build system or dependencies
# - ci: CI/CD configuration changes
# - revert: revert a previous commit

# Examples:
git commit -m "feat(auth): add OAuth2 login with Google"
git commit -m "fix(api): handle null pointer in user endpoint"
git commit -m "docs(readme): update installation instructions"
git commit -m "refactor(database): extract query builder into separate module"
git commit -m "perf(cache): implement LRU eviction policy"
git commit -m "test(user-service): add integration tests for registration flow"
git commit -m "chore(deps): upgrade lodash to 4.17.21"

# Breaking changes (major version bump):
git commit -m "feat(api)!: change user endpoint response format

BREAKING CHANGE: The /api/v1/users endpoint now returns a paginated response
instead of an array. Clients must update to handle the new format:
{ users: [...], total: number, page: number }"

# Multi-line commit message:
git commit -m "feat(payment): integrate Stripe payment gateway

- Add Stripe SDK dependency
- Implement PaymentService with createPaymentIntent method
- Add webhook handler for payment.success and payment.failed events
- Create Payment model with status tracking
- Add unit tests for payment flow

Closes #234"
```

## Example 2: Feature Branch Workflow

Complete workflow for developing a feature from branch creation to merge.

```bash
# 1. Start from latest main
git checkout main
git pull origin main

# 2. Create feature branch with descriptive name
git checkout -b feat/user-authentication

# 3. Work on the feature — make atomic commits
git add src/auth/login.ts
git commit -m "feat(auth): add login form component"

git add src/auth/auth.service.ts
git commit -m "feat(auth): implement JWT token generation"

git add tests/auth.test.ts
git commit -m "test(auth): add unit tests for authentication service"

# 4. Keep branch up-to-date with main (rebase frequently)
git fetch origin
git rebase origin/main

# If conflicts occur:
# - Resolve conflicts in affected files
# - git add <resolved-files>
# - git rebase --continue

# 5. Push branch to remote
git push -u origin feat/user-authentication

# 6. Create Pull Request (GitHub CLI)
gh pr create --title "feat(auth): add user authentication" \
             --body "## Changes
- Add login/logout functionality
- Implement JWT-based session management
- Add refresh token rotation
- Include comprehensive test coverage

## Testing
- [x] Unit tests pass
- [x] Integration tests pass
- [x] Manual testing completed

Closes #123"

# 7. After PR approval — merge (squash and merge recommended)
gh pr merge --squash --delete-branch

# Or merge locally:
git checkout main
git merge --squash feat/user-authentication
git commit -m "feat(auth): add user authentication (#123)"
git push origin main
git branch -d feat/user-authentication
```

## Example 3: Git Hook (pre-commit)

Pre-commit hook to run linting and formatting before allowing commits.

```bash
#!/bin/sh
# .husky/pre-commit (Husky) or .git/hooks/pre-commit (manual)
#
# This hook runs before each commit to ensure code quality.
# Exit with non-zero status to abort the commit.

set -e

echo "🔍 Running pre-commit checks..."

# 1. Run linter on staged files
echo "📝 Running ESLint..."
npm run lint

# 2. Run formatter
echo "🎨 Running Prettier..."
npm run format:check

# 3. Run type checker (TypeScript)
echo "🔧 Running TypeScript compiler..."
npm run typecheck

# 4. Run unit tests (fast tests only)
echo "🧪 Running unit tests..."
npm run test:unit

# 5. Check for secrets (using git-secrets or gitleaks)
echo "🔐 Checking for secrets..."
if command -v gitleaks &> /dev/null; then
    gitleaks protect --staged
fi

echo "✅ All pre-commit checks passed!"
```

**Setup with Husky (recommended):**

```bash
# Install Husky
npm install -D husky

# Initialize Husky
npx husky init

# Create pre-commit hook
echo "npm run lint && npm run test:unit" > .husky/pre-commit

# Make it executable
chmod +x .husky/pre-commit

# Commit the hook (it will run for all team members)
git add .husky/pre-commit
git commit -m "chore: add pre-commit hook for linting and tests"
```

**Setup with pre-commit (Python):**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run against all files (initial setup)
pre-commit run --all-files
```

## Example 4: Commit Message Linter (commitlint)

Enforce conventional commit format automatically.

```javascript
// commitlint.config.js
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Type must be one of these
    'type-enum': [
      2,
      'always',
      [
        'feat',     // New feature
        'fix',      // Bug fix
        'docs',     // Documentation
        'style',    // Formatting, no logic change
        'refactor', // Code refactor
        'perf',     // Performance improvement
        'test',     // Tests
        'build',    // Build system or dependencies
        'ci',       // CI/CD config
        'chore',    // Other maintenance
        'revert',   // Revert commit
      ],
    ],
    // Scope must be lowercase
    'scope-case': [2, 'always', 'lower-case'],
    // Subject must not end with period
    'subject-full-stop': [2, 'never', '.'],
    // Subject must be lowercase (except first letter)
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    // Header max length
    'header-max-length': [2, 'always', 100],
    // Body line max length
    'body-max-line-length': [2, 'always', 200],
  ],
};
```

```bash
# Install commitlint
npm install -D @commitlint/{cli,config-conventional}

# Create commitlint hook
echo "npx --no -- commitlint --edit \${1}" > .husky/commit-msg
chmod +x .husky/commit-msg

# Test it
git commit -m "bad commit message"  # ❌ Will fail
git commit -m "feat: add new feature"  # ✅ Will pass
```

## Example 5: Semantic Release

Automated versioning and changelog generation based on commit messages.

```yaml
# .releaserc.yaml (semantic-release configuration)
branches:
  - main
  - name: develop
    prerelease: alpha

plugins:
  # Analyze commits for version bump
  - - "@semantic-release/commit-analyzer"
    - preset: conventionalcommits
      releaseRules:
        - type: feat
          release: minor
        - type: fix
          release: patch
        - type: perf
          release: patch
        - type: docs
          release: false
        - breaking: true
          release: major

  # Generate release notes
  - - "@semantic-release/release-notes-generator"
    - preset: conventionalcommits
      presetConfig:
        types:
          - type: feat
            section: "✨ Features"
          - type: fix
            section: "🐛 Bug Fixes"
          - type: perf
            section: "⚡ Performance Improvements"
          - type: docs
            section: "📚 Documentation"
          - type: chore
            section: "🔧 Maintenance"

  # Update changelog
  - - "@semantic-release/changelog"
    - changelogFile: CHANGELOG.md

  # Update package.json version
  - - "@semantic-release/npm"
    - npmPublish: false

  # Create GitHub release
  - - "@semantic-release/github"
    - assets:
        - path: dist/**/*.js
          label: "Distribution files"

  # Create Git tag
  - - "@semantic-release/git"
    - assets:
        - CHANGELOG.md
        - package.json
        - package-lock.json
      message: "chore(release): ${nextRelease.version} [skip ci]

${nextRelease.notes}"
```

```bash
# Install semantic-release
npm install -D semantic-release @semantic-release/{git,github,changelog,commit-analyzer,release-notes-generator}

# Run release (typically in CI)
npx semantic-release

# This will:
# 1. Analyze commits since last release
# 2. Determine next version (major/minor/patch)
# 3. Generate release notes
# 4. Update CHANGELOG.md
# 5. Create Git tag (e.g., v1.2.3)
# 6. Push tag to remote
# 7. Create GitHub release with notes
```

## Example 6: Hotfix Workflow

Emergency fix for production issues.

```bash
# 1. Create hotfix branch from main (production)
git checkout main
git pull origin main
git checkout -b hotfix/critical-auth-bug

# 2. Fix the issue
# ... make changes ...
git add src/auth/validator.ts
git commit -m "fix(auth): resolve token validation bypass

Critical security issue where expired tokens were accepted.
Added proper expiration check in validateToken method.

Fixes #456"

# 3. Test the fix
npm test
npm run test:e2e

# 4. Create PR to main
gh pr create --title "hotfix: critical auth bug fix" \
             --body "**CRITICAL FIX**

This resolves a security vulnerability in token validation.

## Impact
- Severity: Critical
- Affected versions: 1.0.0 - 1.2.3
- Fix: Added expiration timestamp check

## Testing
- [x] Unit tests added
- [x] Manual verification completed
- [x] Security review completed"

# 5. After merge — tag the release
git checkout main
git pull origin main
git tag -a v1.2.4 -m "v1.2.4 - Critical auth fix"
git push origin main --tags

# 6. Merge hotfix back to develop (if using GitFlow)
git checkout develop
git merge main
git push origin develop
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
