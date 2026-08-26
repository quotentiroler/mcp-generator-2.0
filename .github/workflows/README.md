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

### 3. `auto-pr.yml` - Auto PR from develop to main
**NEW** - Runs on: `push` to `develop` branch

Automatically creates a pull request from `develop` to `main` when new commits are pushed. Skips if a PR already exists.

#### Features:
- 🤖 Auto-creates PR from `develop` → `main`
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
| `auto-pr.yml` | Push to `develop` | Auto-create PR from `develop` to `main` |
| `update-version-metadata.yml` | Push to `main` | Update version with commit hash + date |

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
