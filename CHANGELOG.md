# Changelog

## [3.2.6-alpha+acee146] - 2026-04-25

### Changed

- Dependencies updated

## [3.2.5]P26-04-25

### Changed

- Dependencies updated


- 🔧 Chores & Improvements: CI/CD stability and automation
  - ci: fix auto-pr-to-main race condition by dispatching workflow instead of push trigger
  - chore: update version metadata and sync main/staging after releases
  - ci(promote): simplify to direct push on staging
  - chore: skip changelog/metadata workflows on release commits
  - docs: update CHANGELOG entries for automated PRs

- 🐛 Bug Fixes: UI/display and data handling improvements
  - fix(display): various UI fixes (auto-refresh toggle behavior, resource identifier in delete dialog, indentation fix in table tool, SendMessage prompts handling)
  - fix(display): add SetInterval auto-refresh to table views
  - fix(display): include proper escaping in SendMessage for visibility
  - feat(display): add Dialog, Tabs, ExpandableRow, Loader, If to generated UI (contextual UI improvements)

- ✨ Features: UI enhancements and data tooling
  - feat(display): auto-refresh toggle with persistent state
  - feat(display): add SetInterval auto-refresh to table views
  - feat: schema-aware form data coercion for POST/PUT tools

- 📚 Documentation: changelog updates
  - docs: update CHANGELOG.md for automated PRs and PRs #79/#80/#82/#83

Note: Merge commits and purely metadata updates have been omitted per guidelines.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/85



- 🔧 Chores & Improvements: Sync main into staging after releases and merge develop into staging
- 🐛 Bug Fixes: fix(build) remove duplicate force-include causing PyPI upload rejection
- ⚠️ Breaking Changes: none
- 📚 Documentation: update CHANGELOG.md entries (automated)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/86


## [3.2.4+44a9a2c] - 2026-04-24

### Changed

- Dependencies updated


- 🔧 Chores & Improvements: CI/CD cleanup to push directly to staging; merge and sync processes streamlined; update version metadata and CHANGELOG automation
- 📚 Documentation: CHANGELOG updates for PRs #76, #79
- ⚠️ Breaking Changes: None
- ✨ Features: Auto-refresh UI enhancements (ToggleState, SetInterval), new dialog UI components (Dialog, Tabs, ExpandableRow, Loader, If), enhanced form tools with loading state and coercion
- 🐛 Bug Fixes: Display fixes (resource identifier in delete dialog, proper auto-refresh behavior, indentation fixes, 404/null-safe fixes), SendMessage prompts adjustment, escaping/backslash handling in SendMessage
- 🔧 Chores & Improvements: Code style and lint fixes (ruff), internal cleanup across display module
- 📚 Documentation: CHANGELOG generation updates

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/80



- ✨ Features
  - Display: auto-refresh toggle with persistent state using ToggleState; add SetInterval auto-refresh to table views; include loading state, Submit button behavior, and dynamic result display in SendMessage

- 🐛 Bug Fixes
  - Display: various UI fixes (dialog components, truncation, table indentation, null-safe handling)
  - Display: fix delete confirmation to show resource identifier; proper escaping in SendMessage prompts

- 🔧 Chores & Improvements
  - CI/CD: skip changelog/metadata workflows on release commits; automate version metadata updates and staging promotions
  - Chore: synchronize main into staging; merge develop into staging improvements
  - Docs: automated CHANGELOG updates

- ⚠️ Breaking Changes
  - None identified

Note: Removed update/merge/metadata-only commits per guidance.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/82



- ✨ Features
  - feat(introspection): generic OpenAPI improvements for complex specs, including configurable max_depth for schema display and improved oneOf/anyOf handling

- 🔧 Chores & Improvements
  - CI/CD and staging workflow optimizations around merging main/develop into staging
  - Version metadata updates and automated changelog/documentation workflow adjustments

- ⚠️ Breaking Changes
  - None identified

- 📚 Documentation
  - Documentation updates to CHANGELOG.md for PRs (automated)

Note: Merges, update-only commits, and non-user-facing metadata updates were omitted per guidelines.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/83


## [3.2.3]P26-04-23

### Changed

- Dependencies updated


- 🔧 Chores & Improvements: CI/CD stabilization for staging workflow auto-updates, PR title/body synchronization, and automated metadata handling
- ⚠️ Breaking Changes: None
- 🐛 Bug Fixes: Fix ci workflow to update PR titles/bodies on new pushes; ensure PRs target main correctly
- 📚 Documentation: Update CHANGELOG references for automated PRs (internal docs updates)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/72



- 🔧 Chores & Improvements: CI/CD tidy-up and automated staging sync
  - fix(ci): auto-sync main back to staging after release
  - fix(ci): auto-pr-to-main updates existing PR title/body on new pushes
  - Staging: Merge develop into staging (various commits) to prevent divergence
  - chore: merge main into staging after PR #71 merge [automated]
  - 618f688: fix(ci): auto-pr-to-main updates existing PR title/body on new pushes
  - 5870dd5: Staging: Merge develop into staging (25 commits)
  - 7445647: chore: merge main into staging to resolve branch divergence
  - 3563b52, 7a0695f: fix(ci): promote workflow uses PR instead of direct push to main
  - ed81e1e, 201121c: fix(ci): replace [skip ci] with [automated] in bot commits to prevent release skip
  - a720e6b, 4499c79: feat(ci): add Promote to Stable Release workflow
  - 38...: various automated changelog and metadata updates

- 🐛 Bug Fixes: CI/testing and tooling improvements
  - fix(tests): rewrite SSE parser to handle multi-line events and large responses
  - fix(tests): escape newline in template f-string assertion
  - fix(tests): increase httpx timeout and improve SSE error diagnostics
  - fix: show_form CallTool missing arguments and input_type binding
  - fix: warn when OpenAPI spec has relative server URL
  - fix: filter wildcard catch-all paths from resource URI schemes
  - fix: separate URI scheme from Python identifier in resource generation
  - fix: sanitize resource names from path segments for valid Python identifiers
  - fix: sanitize special chars in camel_to_snake for valid Python identifiers
  - fix: 5 more TDD-verified bugs — display params, camel_to_snake, response refs, version normalization
  - fix: 8 TDD-verified bugs — nullable types, path params, Swagger 2.0 auth, falsy checks, param sanitization, query defaults, metadata escaping
  - fix: SSE parser skips notifications before result in tools/call tests
  - fix: resolve all Ruff lint and format errors for CI

- 📚 Documentation: CHANGELOG updates automated
  - docs: update CHANGELOG.md for PR #70, #64, #63, #72 (automated)
  - docs: update install instructions for PyPI (pip install mcp-generator)

- ✨ Features: CI/test tooling enhancements
  - feat(ci): add Promote to Stable Release workflow
  - feat: add real tools/call E2E test template
  - feat: generate Form.from_model() tools from POST/PUT request body schemas
  - refactor: replace generate_client.py with openapi-py-fetch dependency

- ⚠️ Breaking Changes
  - None detected in this release

- 🔧 Chores & Improvements: Misc maintenance
  - style: fix ruff formatting in cli.py
  - 82fd7c8: style: fix ruff formatting in cli.py
  - 8b248a3: chore: update version metadata with commit 7445647
  - 0e41d4d: chore: update version metadata with commit 8048bcb

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/74


## [3.2.2] - 2026-04-22

### Changed

- Dependencies updated


- 🔧 Chores & Improvements: Staging merge and CI/workflow updates
  - Merge develop into staging (staging prep)
  - Add PyPI publish workflow and related metadata
  - Update PyPI metadata (classifiers, keywords, urls)
  - Update contact information

- 📚 Documentation: Update changelog reference for PR #63

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/64


- 🔧 Chores & Improvements: Internal staging merge and CI/CD housekeeping

Notes:
- Skipped metadata and merge commits per guidelines
- No user-facing feature or bug fixes detected in meaningful commits since last release

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/67



- 🔧 Chores & Improvements: Internal updates and maintenance

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/70


## [3.2.1] - 2026-04-20

- ✨ Features
  - 🔧 feat: add A2A agent generation and OpenAPI Overlay support
  - 🔧 feat: MCP Apps Phase 1 — curated display tools + GenerativeUI wiring
  - 🔧 feat: MCP Apps Phase 2 + bump to v3.2.0
  - 🔧 feat: MCP Apps + v3.2.0 — interactive UI display tools, docs refresh
  - 🔧 feat: add show_metrics, show_timeline, show_progress display tools

- 🐛 Bug Fixes
  - 🐛 fix: display renderers use Configuration instead of missing get_api_client
  - 🐛 fix: guard against None API results in detail display tools
  - 🐛 fix: snake_case param names in display tool API calls
  - 🐛 fix: comparison tool picks name/title/label key for card heading
  - 🐛 fix: resolve ruff lint errors and sort imports in __init__.py
  - 🐛 fix: resolve 77 mypy type errors across 18 files
  - 🐛 fix: use rows= kwarg for DataTable (not data=)
  - 🐛 fix: correct prefab-ui imports in display_tools template

- 📚 Documentation
  - 📚 docs: update CHANGELOG.md for PR #59
  - 📚 docs: rename MCP Generator 3.1 -> 3.x across README and CLI
  - 📚 docs: update competitive analysis — add new competitors, refresh star counts, add feature rows
  - 📚 docs: add MCP Apps (interactive UI display tools) to README

- 🔧 Chores & Improvements
  - 🔧 style: apply ruff formatting to new files
  - 🔧 style: sort imports in __init__.py
  - 🔧 fix: resolve ruff lint errors in a2a, overlay, and test files
  - 🔧 refactor: derive __version__ from pyproject.toml via importlib.metadata
  - 🔧 chore: bump version to 3.2.1
  - 🔧 clean: general cleanup
  - 🔧 fix: correct actively maintained status for openapi-mcp-codegen

- ⚠️ Breaking Changes
  - None detected for this release.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/61



- ✨ Features
  - feat: add A2A agent generation and OpenAPI Overlay support
  - feat: MCP Apps Phase 1 — curated display tools + GenerativeUI wiring
  - feat: MCP Apps Phase 2 + bump to v3.2.0 (also supports interactive UI display tools)

- 🐛 Bug Fixes
  - fix: guard against None API results in detail display tools
  - fix: display renderers use Configuration instead of missing get_api_client
  - fix: sort imports in __init__.py (stdlib before relative)
  - fix: resolve ruff lint errors across multiple files (formatting/imports)
  - fix: ruff 8-file format
  - fix: resolve all 77 mypy type errors across 18 files

- 📚 Documentation
  - docs: update CHANGELOG.md for PRs #59 and #61
  - docs: add MCP Apps (interactive UI display tools) to README
  - docs: rename MCP Generator 3.1 -> 3.x across README and CLI
  - docs: update competitive analysis — new competitors, refreshed data

- 🔧 Chores & Improvements
  - chore: add PyPI metadata (classifiers, keywords, urls)
  - chore: add PyPI publish workflow (Trusted Publishers) and fix pyproject urls
  - chore: bump version to 3.2.1
  - refactor: derive __version__ from pyproject.toml via importlib.metadata
  - style: apply ruff formatting to new files
  - clean and misc fixes for project hygiene

- ⚠️ Breaking Changes
  - (none)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/63


## [3.2.0] - 2026-04-20

- ✨ Features: MCP Apps Phase 1 — interactive UI display tools (show_table, show_detail, show_chart, show_form, show_comparison, show_metrics, show_timeline, show_progress) with Prefab UI rendering and JSON fallback; Phase 2 planned with --generate-ui to create API-specific tools from OpenAPI schemas
- 📚 Documentation: Branding/docs refresh accompanying MCP Apps release

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/59


All notable changes to MCP Generator 3.x will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.1-rc.1+23e773c] - 2026-03-27

### Changed

- Dependencies updated


- ✨ Features
  - feat: Auto-populate FastMCP.json auth config from OpenAPI security schemes
  - feat: FastMCP 3.1 features — RateLimiting, OAuthProxy, progress/elicitation/sampling, SSRF protection
  - feat: Behavioral edge-case generated test template
  - feat: Advanced generated test templates for agent-driven iteration
  - feat: Wire FastMCP 3.1 features + comprehensive test coverage

- 🐛 Bug Fixes
  - fix: only enable validate_tokens for bearer/authorizationCode schemes
  - fix: first-tag-wins dedup for multi-tag operations
  - fix: use camel_to_snake for expected tool tags in test_server_integration template
  - fix: lowercase expected tag in test_server_integration template
  - fix: exclude behavioral tests from default CI run; fix MockContext.report_progress signature
  - fix: fix sys.path setup in generated test templates for correct module resolution
  - fix: centralize server name sanitization to prevent invalid Python identifiers
  - fix: escape newline in sampling error template to prevent SyntaxError
  - fix: resolve all Ruff lint errors (import sort, unused vars, bare except, f-strings)

- 📚 Documentation
  - docs: update CHANGELOG.md for PRs and version updates

- 🔧 Chores & Improvements
  - chore: update version metadata and related commit housekeeping
  - chore: ruff formatting and lint improvements across files
  - chore: update proxy-openapi/json references to reflect latest beta/stable
  - chore: sync main into develop and staging branches during release process
  - chore: update repo references, paths, and docs for stable release
  - chore: remove stale tests and adjust tracking

- ⚠️ Breaking Changes
  - none detected

- 🔧 Chores & Improvements (internal)
  - internal updates and maintenance

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/57


## [3.1.1-rc+2b7ece3] - 2026-03-26

### Changed

- Dependencies updated


- ✨ Features: FastMCP 3.1 features — RateLimiting, OAuthProxy, progress/elicitation/sampling, SSRF protection
  - Add RateLimitingMiddleware (token-bucket) with configurable max_rps, burst, global_limit
  - Add OAuthProxy for bridging non-DCR IdPs (Auth0, Okta, Azure AD) to MCP auth
  - Add ctx.report_progress() calls

- 🔧 Chores & Improvements: Code quality and test/template enhancements
  - Various tests/templates and code quality improvements (camel_to_snake updates, tag handling, sys.path setup, server name sanitization, Ruff lint fixes, formatting)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/54



- ✨ Features: Auto-populate fastmcp.json auth config from OpenAPI security schemes
  - Enable oauth_proxy with upstream URLs and valid_scopes for OAuth2 authorizationCode
  - Enable validate_tokens for bearer auth schemes

- 🔧 Chores & Improvements: Minor formatting fixes in tests (ruff)

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/55


## [3.1.1-beta+d025b9d] - 2026-03-12

### Changed

- Dependencies updated


- ✨ Features: None
- 🐛 Bug Fixes: None
- 📚 Documentation: None
- 🔧 Chores & Improvements:
  - Sync main into develop and prepare staging (pre-release 3.1.1-beta)
  - Resolve merge conflicts and keep 3.1.1-alpha version
  - Update changelog formatting for version bumps
  - Update version metadata
- ⚠️ Breaking Changes: None

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/47



- 🔧 Chores & Improvements: CI/CD and internal maintenance
- 🐛 Bug Fixes: Corrected repo name for release check (mcp-generator-2.0 vs mcp-generator-3.x)
- 📚 Documentation: Update CHANGELOG references and PR notes
- ⚠️ Breaking Changes: None detected

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/49



- 🔧 Chores & Improvements: Sync version bumps and metadata after staging merge; ensure develop remains ahead of staging
- 🐛 Bug Fixes: Fix version bump propagation to develop and correct repo name for release checks
- 📚 Documentation: Update CHANGELOG.md references for previous PRs
- ⚠️ Breaking Changes: None detected for this pre-release

Notes:
- Includes: bump to 3.1.1-beta, sync back to develop, prevent revert of version bumps on merges, and changelog diff improvements.

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/50



- ✨ Features
  - FastMCP 3.1 features wired, including tags, timeout, version, parameters, and FunctionTool
  - Behavioral test templates: added edge-case test template and advanced agent-driven iteration templates

- 🐛 Bug Fixes
  - Generated code improvements based on behavioral test failures (ParameterValidationError, duck-type validation, isoformat datetime, coroutine guard, expanded exception handling)

- 📚 Documentation
  - Documentation updates: stale version refs, repo URLs, and paths across MD files

- 🔧 Chores & Improvements
  - Behavioral test template improvements and expanded test coverage
  - Code style/lint fixes for formatting and ruff violations

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/52


## [3.1.0] - 2026-03-06

### Added

- **FastMCP 3.1 Features** — Full support for FastMCP 3.0/3.1 features:
  - **Tool Tags** — Automatic per-module tag grouping (`@mcp.tool(tags=["pet"])`)
  - **Tool Timeouts** — Configurable per-tool timeout (default 30s)
  - **SearchTools Transform** — BM25 text search over tool catalog (opt-in)
  - **CodeMode Transform** — Experimental meta-tool execution (opt-in)
  - **ResponseLimitingMiddleware** — UTF-8-safe truncation of oversized responses (1MB default)
  - **PingMiddleware** — HTTP keepalive for long-lived connections
  - **MultiAuth** — Compose multiple token verifiers (JWT + OAuth2, etc.)
  - **Component Versioning** — Deprecated endpoints annotated automatically
  - **Dynamic Visibility** — Per-session component toggling via scopes
  - **OpenTelemetry** — Tracing with MCP semantic conventions (Console/OTLP export)
  - **validate_output** — FastMCP output validation support

- **Enhanced CI** — Comprehensive test improvements:
  - Enabled unit tests (99 tests, was previously TODO)
  - Added Python 3.12 to test matrix
  - Added coverage reporting with Codecov
  - New `fastmcp-features` CI job for targeted feature tests
  - FastMCP 3.1 verification in example integration tests

- **Documentation** — Updated docs for all new features:
  - New `features` section in configuration guide
  - OpenTelemetry and middleware documentation
  - Transforms (SearchTools, CodeMode) guide
  - MultiAuth and dynamic visibility documentation

### Changed

- **fastmcp.json Template** — Expanded with full `features` section
- **pyproject.toml** — Added `[telemetry]` optional dependency group
- **Generated README** — Lists all FastMCP 3.1 features


- ✨ Features
  - No new user-facing features identified

- 🐛 Bug Fixes
  - fix: add Accept header to bearer token auth test to prevent 406 response
  - fix: sanitize version strings to be PEP 440 compliant
  - fix: handle concurrent changelog updates with pull-rebase
  - debug: add path debugging and -rs flag to show skip reasons
  - debug: add import error details to oauth test skip reason
  - fix: prevent sys.exit during pytest collection in oauth tests

- 🔧 Chores & Improvements
  - chore: update version metadata with commit 6094e01
  - ci: regenerate uv.lock when version is bumped in pyproject.toml
  - chore: update version metadata with commit c26698a
  - update: various internal updates and maintenance lines (aggregate)
  - chore: update version metadata with commit f09e716
  - update: internal updates and maintenance

- 📚 Documentation
  - docs: update CHANGELOG.md for PR #44
  - docs: update CHANGELOG.md for PR #42

- ⚠️ Breaking Changes
  - None detected

- 🔧 CI/CD
  - Merge-related and staging PRs (omitted per guidelines)
  - Updates related to versioning and test infrastructure improvements

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-3.x/pull/45


## [2.0.0-rc.1+6094e01] - 2025-11-05

- ✨ Features: Storage functionality (merged dev/storage changes)
- 🔧 Chores & Improvements: Update version metadata
- 🔧 Chores & Improvements: Concurrent changelog updates and path debugging enhancements
- 🐛 Bug Fixes: Prevent sys.exit during pytest collection in oauth tests
- ⚠️ Breaking Changes: None detected
- 📚 Documentation: None detected

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/42



- 🔧 Chores & Improvements: Maintenance and CI updates (internal updates, version metadata, and debug/testing enhancements)

- 🐛 Bug Fixes: 
  - fix: add Accept header to bearer token auth test to prevent 406 response
  - fix: sanitize version strings to be PEP 440 compliant
  - fix: handle concurrent changelog updates with pull-rebase
  - fix: add fastmcp and cryptography to dev dependencies
  - fix: prevent sys.exit during pytest collection in oauth tests

- 🔧 Chores & Improvements: Misc internal test/debug improvements and skip reason details

- ⚠️ Breaking Changes: None detected

**Full Changelog**: https://github.com/quotentiroler/mcp-generator-2.0/pull/44


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

- Initial public release of MCP Generator 3.x
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

