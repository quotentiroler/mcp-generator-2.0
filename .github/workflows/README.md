# GitHub Workflow### 3. `diff-summary.yml` - AI-Powered Diff Summaries
**NEW** - Runs on: `push` to `develop` and `develop/**` branches

Automatically generates concise summaries of code changes using OpenAI's GPT-5 nano model via the Responses API.

**Note**: Automatically skips merge commits (e.g., when merging `develop/*` branches into `develop`) to avoid redundant summaries.

#### Features:
- 🤖 Uses GPT-5 nano (fastest, most cost-efficient GPT-5 model)
- 📊 Analyzes git diffs between commits
- 💬 Posts summary as **commit comment** (visible on commit page)
- 🔀 **Smart skip**: Automatically skips merge commits
- 💾 Uploads summary as artifact (30-day retention)
- 🔒 Truncates large diffs (500 chars per file version)
- ⚡ Caches dependencies for faster runsctory contains GitHub Actions workflows for automated CI/CD tasks.

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

### 4. `diff-summary.yml` - AI-Powered Diff Summaries
**NEW** - Runs on: `push` to `develop` and `develop/**` branches

Automatically generates concise summaries of code changes using OpenAI's GPT-5 nano model via the Responses API.

#### Features:
- 🤖 Uses GPT-5 nano (fastest, most cost-efficient GPT-5 model)
- 📊 Analyzes git diffs between commits
- � Posts summary as **commit comment** (visible on commit page)
- 💾 Uploads summary as artifact (30-day retention)
- 🔒 Truncates large diffs (500 chars per file version)
- ⚡ Caches dependencies for faster runs

#### Setup:

1. **Add OpenAI API Key to Repository Secrets**:
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key

2. **Ensure Workflow Permissions**:
   - Go to: `Settings` → `Actions` → `General`
   - Under "Workflow permissions", ensure:
     - ✅ "Read and write permissions" (needed to post commit comments)

#### Manual Usage:

You can also run the diff summarization script locally:

```bash
# Install OpenAI package
uv pip install --system openai

# Set your API key
export OPENAI_API_KEY="your-api-key-here"  # Linux/macOS
set OPENAI_API_KEY=your-api-key-here      # Windows CMD
$env:OPENAI_API_KEY="your-api-key-here"   # Windows PowerShell

# Summarize latest commit
python scripts/summarize_diff.py

# Summarize changes between branches
python scripts/summarize_diff.py --base-ref main --head-ref develop

# Summarize with custom truncation
python scripts/summarize_diff.py --max-chars 1000
```

#### Cost Optimization:

- Uses **GPT-5 nano** - the most cost-efficient GPT-5 model
- Truncates large diffs to stay within token limits
- Max 500 output tokens per summary
- Caches pip dependencies for faster subsequent runs
- **Skips merge commits** automatically to avoid unnecessary API calls

#### Merge Commit Behavior:

The workflow automatically detects and skips merge commits (commits with 2+ parents). This means:

- ✅ Regular commits on `develop/*` branches → **AI summary generated**
- ✅ Direct commits to `develop` branch → **AI summary generated**
- ❌ Merge commits (e.g., merging `develop/feature` into `develop`) → **Skipped**

This prevents redundant summaries when feature branches are merged, since the individual commits in the branch already have their own summaries.

#### Example Output:

On the commit page, you'll see a comment like:

```markdown
## 🤖 AI-Generated Commit Summary

======================================================================
📝 COMMIT SUMMARY
======================================================================

**Commit**: a1b2c3d
**Author**: Max Nussbaumer
**Message**: Add OAuth2 support to generator

**AI Summary**:
- Added OAuth2 authentication middleware generation
- Implemented JWT validation with JWKS support
- Updated templates to include security schemes
- **Breaking Change**: Updated authentication config structure
- Added comprehensive tests for auth flows

======================================================================

---
*Generated by OpenAI GPT-5 nano based on code changes*
```

---

## 📋 Workflow Summary

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `tests.yml` | Push/PR to `main`, `develop` | Unit tests, linting, type checking |
| `test-examples.yml` | Push/PR | Integration tests for generated code |
| `auto-pr.yml` | Push to `develop` | Auto-create PR from `develop` to `main` |
| `diff-summary.yml` | Push to `develop`, `develop/**` | AI-generated commit summaries |
| `update-version-metadata.yml` | Push to `main` | Update version with commit hash + date |

---

### 5. `update-version-metadata.yml` - Version Metadata Updates
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

## Troubleshooting

### Diff Summary Workflow Issues:

**Error: "OPENAI_API_KEY not set"**
- Ensure the secret is added to repository settings
- Check the secret name is exactly `OPENAI_API_KEY`

**Error: "openai package not installed"**
- The workflow should install it automatically
- Check the "Install dependencies" step in workflow logs

**Commit comment not posted**
- Verify workflow has write permissions for contents
- Check `Settings` → `Actions` → `General` → `Workflow permissions`
- Ensure "Read and write permissions" is selected

**Rate limit errors**
- Consider increasing the cache duration
- Reduce frequency by limiting to specific branches
- Use OpenAI's tier limits appropriately

## Contributing

When adding new workflows:
1. Test locally using `act` if possible
2. Add documentation to this README
3. Use proper caching for dependencies
4. Include error handling and logging
5. Set appropriate permissions in workflow file
