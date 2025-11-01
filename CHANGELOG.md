# Changelog

All notable changes to MCP Generator 2.0 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0-beta+f9dac73] - 2025-10-29

- ✨ Features (new functionality)
  - None detected

- 🐛 Bug Fixes (fixes to existing functionality)
  - Max: fix: include scripts package in distribution
  - Max: fix: correct path for scripts package location
  - quotentiroler: fix: repair corrupted version extraction in create-release workflow
  - quotentiroler: fix: add __init__.py to scripts package and improve error message

- 📚 Documentation (documentation changes)
  - None detected

- 🔧 Chores & Improvements (maintenance, refactoring, CI/CD)
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - github-actions[bot]: chore: update version metadata with commit 13e8f57 [skip ci]
  - Max: Update
  - Max: update
  - Max: update
  - Max: update
  - Max: update
  - Max: update
  - Max: update
  - Max: update
  - Max: update
  - Max: Update
  - Max: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  - quotentiroler: update
  -  - Staging: Merge develop into staging (9 commits) (#5) (merged commit, skipped)
  -  - Release: 2.0.0-alpha (34 commits) (#21) (merged commit, skipped)

- ⚠️ Breaking Changes (if any)
  - None detected

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/22


### Planned

- Additional authentication schemes support
- GraphQL API support
- Custom template system
- Plugin architecture
- Web UI for configuration


- 🔧 Chores & Improvements: Internal staging workflow updates

Note: No user-facing changes detected beyond update/merge activities.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/24



- 🔧 Chores & Improvements: Internal staging process adjustments (merge from develop into staging)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/27


## [2.0.0-alpha+c53f1ed] - 2025-10-27

### Added

- Initial public release of MCP Generator 2.0
- OpenAPI 3.0+ to FastMCP 2.x server generation
- Modular server architecture with composition pattern
- Complete authentication middleware stack:
  - Bearer token authentication
  - OAuth2 flow support (implicit, authorization code, client credentials, password)
  - JWT validation with JWKS discovery
  - Scope enforcement
- Dual transport support:
  - STDIO mode for local AI clients (Claude Desktop, Cline, Cursor)
  - HTTP mode with SSE for web-based clients
- Comprehensive middleware system:
  - Error handling middleware
  - Authentication middleware
  - Timing middleware
  - Logging middleware
- Event store for resumable SSE streams
- Auto-generated test suites for:
  - Authentication flows
  - Tool validation
- Three CLI commands:
  - `generate-mcp` - Generate MCP servers from OpenAPI specs
  - `run-mcp` - Run registered MCP servers
  - `register-mcp` - Manage server registry
- Complete package files generation:
  - pyproject.toml
  - README.md
  - fastmcp.json for client configuration
- Tool name customization and abbreviation support
- Session management for HTTP transport
- Comprehensive documentation and examples

### Technical Details

- Built on FastMCP 2.x framework
- Uses OpenAPI Generator for Python client generation
- Full Pydantic model support for type safety
- Type hints throughout codebase
- Ruff-formatted code
- Comprehensive test coverage
- Python 3.11+ support

### Dependencies

- fastmcp >= 2.12.0
- httpx >= 0.28.1
- pydantic >= 2.10.3
- pyjwt >= 2.10.0
- cryptography >= 46.0.0
- And more (see pyproject.toml)

---

## How to Use This Changelog

### Types of Changes

- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security vulnerabilities

### Versioning

- **Major version** (X.0.0) - Breaking changes
- **Minor version** (0.X.0) - New features, backwards compatible
- **Patch version** (0.0.X) - Bug fixes, backwards compatible

---

**Note:** This project is under active development. Versions before 1.0.0 may have breaking changes between minor versions.


- 🔧 Chores & Improvements
  - Staging: Merge develop into staging (automated PR)
  - Various internal updates and refinements to prepare staging environment

Note: Commit messages are generic ("update") and do not specify functional changes. Excluded merge commits and trivial commits.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/10



- 🔧 Chores & Improvements
  - Max: update (multiple commits) — minor updates across the codebase.

- 🐛 Bug Fixes
  - Max: fix: include scripts package in distribution
  - Max: fix: correct path for scripts package location

- ✨ Features
  - None detected

- 📚 Documentation
  - None detected

- ⚠️ Breaking Changes
  - None detected

Notes:
- Excluded: merge commits and trivial commits like repeated "update" messages were not listed beyond grouping.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/12



- 🐛 Bug Fixes
  - fix: repair corrupted version extraction in create-release workflow
  - fix: include scripts package in distribution
  - fix: correct path for scripts package location
  - fix: add __init__.py to scripts package and improve error message

- 🔧 Chores & Improvements
  - Max: update (multiple commits)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/14



- 🔧 Chores & Improvements: Auto PR merge from develop to staging (1 commit ahead)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/16



- 🔧 Chores & Improvements
  - Sync staging branch with develop (automated): merged latest changes into staging.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/20

