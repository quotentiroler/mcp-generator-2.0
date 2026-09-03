# Contributing

Thank you for your interest in contributing to MCP Generator 4.x!

## Ways to Contribute

- **Report bugs** — found a bug? Please [open an issue](https://github.com/quotentiroler/mcp-generator-3.x/issues)
- **Suggest features** — have an idea? We'd love to hear it
- **Improve documentation** — help make our docs better
- **Submit code** — fix bugs or implement features
- **Write tests** — improve test coverage
- **Share examples** — show how you're using the generator

## Development Setup

### Prerequisites

- Python 3.11+
- Git

### Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/mcp-generator-3.x.git
cd mcp-generator-3.x

# Add upstream
git remote add upstream https://github.com/quotentiroler/mcp-generator-3.x.git

# Install dev dependencies
uv sync --group dev

# Set up pre-commit hooks
git config core.hooksPath .githooks
```

### Create a Feature Branch

```bash
git checkout develop
git checkout -b develop/your-feature-name
```

## Branching Strategy

We use a **Git Flow** style model:

| Branch | Purpose |
|---|---|
| `main` | Production-ready, stable releases only |
| `develop` | Integration branch, always deployable |
| `develop/*` | Feature branches |

## Development Workflow

```bash
# 1. Make changes
# 2. Run tests
uv run pytest

# 3. Format code
uv run ruff format .

# 4. Lint
uv run ruff check .

# 5. Commit
git commit -m 'feat: add amazing feature'

# 6. Push and open PR against develop
git push origin develop/your-feature-name
```

## Guidelines

- Follow existing code style (Ruff formatting)
- Add tests for new features
- Update documentation as needed
- Keep commits focused and descriptive
- Target the `develop` branch for PRs

## Reporting Bugs

1. Check [existing issues](https://github.com/quotentiroler/mcp-generator-3.x/issues)
2. Include:
    - OpenAPI spec (sanitized/minimal example)
    - Full error message and stack trace
    - Steps to reproduce
    - Expected vs actual behavior
