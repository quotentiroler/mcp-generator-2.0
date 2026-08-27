# GitHub Workflows

This directory contains GitHub Actions workflows for automated CI/CD tasks.

## Workflows

### 1. `tests.yml` - Unit Tests & Linting
Runs on: `push` and `pull_request` to `main` and `develop` branches

- Runs unit tests with pytest
- Performs linting with Ruff
- Type checking with mypy
- Tests on Ubuntu and Windows with Python 3.11

### 2. `test-examples.yml` - Integration Tests
Tests generated MCP servers from example OpenAPI specifications.

### 3. `auto-pr-to-test.yml` - Auto PR from develop to test
Runs on: `push` to `develop` branch

Automatically creates a pull request from `develop` to `test` when new commits are pushed. Skips if a PR already exists. Merging that PR puts the change on the beta channel; `auto-pr-to-main.yml` then opens the release PR from `test` to `main`.

#### Features:
- 🤖 Auto-creates PR from `develop` → `test`
- 🔍 Smart detection: Skips if PR already exists
- 📊 Shows commit count and latest commit info
- 🏷️ Adds labels: `automated`, `release`
- ✅ Includes PR checklist for reviewers
- 📝 Professional PR description

#### Setup:

**Ensure Workflow Permissions**:
- Go to: `Settings` → `Actions` → `General`
- Under "Workflow permissions", ensure:
  - ✅ "Read and write permissions"
  - ✅ "Allow GitHub Actions to create and approve pull requests"

#### PR Template:

The workflow creates PRs with:
- Title: `Release: Merge develop into main (X commits)`
- Commit count and latest commit details
- Pre-populated checklist for reviewers
- Automatic labels (if they exist)

---

## 📋 Workflow Summary

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `tests.yml` | Push/PR to `main`, `develop` | Unit tests, linting, type checking |
| `test-examples.yml` | Push/PR | Integration tests for generated code |
| `auto-pr-to-develop.yml` | Push to `dev/**` | Auto-create PR from feature branch to `develop` |
| `auto-pr-to-test.yml` | Push to `develop` | Auto-create PR from `develop` to `test` |
| `auto-pr-to-main.yml` | Dispatched from `test` | Auto-create release PR from `test` to `main` |
| `update-version-metadata.yml` | Push to `test` | Pin version to the beta channel, add commit hash + date |
| `update-changelog.yml` | PR merged to `test` | Build CHANGELOG entries from commit messages |
| `create-release.yml` | Push to `main`, `test` | Cut the GitHub release, then publish to PyPI |
| `publish.yml` | Called by `create-release.yml` | Build and upload to PyPI (Trusted Publisher OIDC) |

---

## 🚀 Release Channels

The branch decides the channel. Nothing infers it from the version string.

| Branch | Channel | Version | GitHub release | PyPI |
|--------|---------|---------|----------------|------|
| `develop` | integration | unchanged | none | none |
| `test` | beta | `X.Y.Z-beta` | pre-release | `X.Y.ZbN` |
| `main` | stable | `X.Y.Z` | full release | `X.Y.Z` |

`create-release.yml` runs on both release branches and resolves the channel from
`github.ref_name`. It pins the version with
`update_version_metadata.py --channel <channel>`, which is idempotent: on `test`
the version already carries `-beta`, and on `main` the suffix is stripped so the
tag, the changelog heading, the release and the uploaded artifact all agree.

Publishing to PyPI is gated by the `pypi` environment, so a reviewer approves
each upload. Remove the environment's required reviewer to make it unattended.

---

### 4. `update-version-metadata.yml` - Version Metadata Updates
**NEW** - Runs on: `push` to `main` branch

Automatically updates version metadata in CHANGELOG.md and SECURITY.md with commit hash and date.

#### Features:
- 📦 Appends commit hash to version (e.g., `2.0.0-alpha+a1b2c3d`)
- 📅 Updates date in CHANGELOG.md
- 🤖 Auto-commits changes back to main
- 🔍 Skips if no changes needed
- ⏭️ Uses `[skip ci]` to prevent workflow loops

#### What It Does:

Transforms version references like:
```
Before: 2.0.0-alpha (2025-10-25)
After:  2.0.0-alpha+a1b2c3d (2025-10-27)
```

This helps track exactly which commit corresponds to which build.

#### Manual Usage:

```bash
# Update with current commit and date
python scripts/update_version_metadata.py

# Dry run (preview changes)
python scripts/update_version_metadata.py --dry-run

# Specify commit hash manually
python scripts/update_version_metadata.py --commit-hash abc123

# Custom date
python scripts/update_version_metadata.py --date 2025-10-27
```

## Contributing

When adding new workflows:
1. Test locally using `act` if possible
2. Add documentation to this README
3. Use proper caching for dependencies
4. Include error handling and logging
5. Set appropriate permissions in workflow file
