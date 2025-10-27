# Contributing to MCP Generator 2.0

Thank you for your interest in contributing to MCP Generator 2.0! This document provides guidelines and instructions for contributing to the project.

## 🎯 Ways to Contribute

- **Report bugs** - Found a bug? Please open an issue
- **Suggest features** - Have an idea? We'd love to hear it
- **Improve documentation** - Help make our docs better
- **Submit code** - Fix bugs or implement features
- **Write tests** - Improve test coverage
- **Share examples** - Show how you're using the generator

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js and npm (for OpenAPI Generator)
- Git

### Development Setup

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/mcp-generator-2.0.git
   cd mcp-generator-2.0
   ```

2. **Add upstream remote**
   ```bash
   # Add the original repository as upstream
   git remote add upstream https://github.com/quotentiroler/mcp-generator-2.0.git
   ```

3. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync --group dev
   
   # Or using pip
   pip install -e ".[dev]"
   ```

4. **Install OpenAPI Generator**
   ```bash
   npm install -g @openapitools/openapi-generator-cli
   ```

5. **Set up pre-commit hooks** (recommended)
   ```bash
   # Configure Git to use the hooks directory
   git config core.hooksPath .githooks
   
   # On Linux/macOS, make hooks executable
   chmod +x .githooks/pre-commit
   ```
   
   This automatically formats code with `ruff` before each commit.

6. **Create a feature branch from develop**
   ```bash
   # Always branch from develop, not main
   git checkout develop
   git checkout -b develop/your-feature-name
   ```

## 🌿 Branching Strategy

We use a **Git Flow** style branching model:

### Branch Structure

- **`main`** - Production-ready code, stable releases only
- **`develop`** - Integration branch for features, always deployable
- **`develop/*`** - Feature branches (e.g., `develop/oauth-support`)

### Workflow

1. **Create feature branch from `develop`**:
   ```bash
   git checkout develop
   git pull upstream develop
   git checkout -b develop/your-feature
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin develop/your-feature
   ```

3. **Create PR to `develop`** (not `main`):
   - Open PR: `develop/your-feature` → `develop`
   - Wait for automated workflows and reviews
   - Address feedback

4. **Automated workflows run**:
   - ✅ Unit tests and linting
   - ✅ Integration tests
   - 🤖 AI-powered diff summary (posted as commit comment)

5. **After merge to `develop`**:
   - 🤖 Auto-PR workflow creates PR: `develop` → `main`
   - Maintainer reviews and merges to `main`
   - Release is created

### Important Notes

- ⚠️ **Never commit directly to `main`**
- ⚠️ **Always create PRs to `develop`**, not `main`
- ✅ Feature branches should be named `develop/*`
- ✅ Keep your branch up to date with `develop`

### Keeping Your Fork Updated

```bash
# Sync your develop branch with upstream
git checkout develop
git pull upstream develop
git push origin develop

# Rebase your feature branch (if needed)
git checkout develop/your-feature
git rebase develop
git push origin develop/your-feature --force-with-lease
```

## 📝 Development Workflow

### Running the Generator

```bash
# Generate from example OpenAPI spec
uv run generate-mcp --file openapi.yaml

# Test the generated output
cd generated_mcp
python swagger_petstore_openapi_mcp_generated.py
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=mcp_generator --cov-report=html

# Run specific test file
uv run pytest test/test_utils.py

# Run with verbose output
uv run pytest -v
```

### Automated Workflows

When you push commits to `develop` or `develop/*` branches, several automated workflows run:

#### 1. **Diff Summary Workflow** (`.github/workflows/diff-summary.yml`)
- 🤖 Automatically generates AI-powered summaries using OpenAI GPT-5 nano
- 💬 Posts summary as a commit comment (visible on commit page)
- 🔀 Smart: Skips merge commits to avoid redundancy
- 💰 Cost-efficient: Truncates large diffs and uses the fastest model

#### 2. **Auto PR Workflow** (`.github/workflows/auto-pr.yml`)
- 🤖 Automatically creates PR from `develop` → `main` when you push to `develop`
- 🔍 Smart: Skips if PR already exists
- 📊 Includes commit count and latest changes
- ✅ Pre-populated with review checklist

#### 3. **Tests Workflow** (`.github/workflows/tests.yml`)
- 🧪 Runs unit tests, linting, and type checking
- 🔍 Validates code quality on every push
- ✅ Must pass before PR can be merged

#### 4. **Integration Tests** (`.github/workflows/test-examples.yml`)
- 🔧 Tests generated MCP servers from example specs
- 🚀 Ensures the generator produces working code

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code with Ruff (done automatically by pre-commit hook)
uv run ruff format .

# Lint code
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Type checking with mypy
uv run mypy mcp_generator/
```

**Pre-commit hooks:**
If you set up the pre-commit hooks (see setup step 5), formatting and linting are automatic.
To bypass when needed: `git commit --no-verify -m "message"`

**Before submitting a PR, ensure:**
- ✅ All tests pass
- ✅ Code is formatted with Ruff (automatic with pre-commit hook)
- ✅ No linting errors
- ✅ Type hints are correct (mypy passes)

## 🎨 Code Style

- Follow **PEP 8** guidelines
- Use **type hints** for all functions
- Write **descriptive variable names**
- Add **docstrings** to all public functions
- Keep functions **focused and small**
- Maximum line length: **100 characters**

### Example:

```python
def generate_server_module(api_var_name: str, api_class: type) -> ModuleSpec:
    """
    Generate a modular MCP server from an API class.
    
    Args:
        api_var_name: Variable name for the API (e.g., 'pet_api')
        api_class: The API class to introspect
        
    Returns:
        ModuleSpec containing the generated code and metadata
    """
    # Implementation
    pass
```

## 🐛 Reporting Bugs

When reporting bugs, please include:

1. **Clear title** - Describe the issue concisely
2. **Description** - What happened vs. what you expected
3. **Steps to reproduce** - Detailed steps to reproduce the issue
4. **OpenAPI spec** - A minimal example (sanitized if needed)
5. **Error messages** - Full error output and stack traces
6. **Environment**:
   - OS and version
   - Python version
   - MCP Generator version
   - OpenAPI Generator version

**Use the bug report template** when creating an issue.

## 💡 Suggesting Features

When suggesting features:

1. **Check existing issues** - Maybe it's already suggested
2. **Describe the use case** - Why is this feature needed?
3. **Provide examples** - Show how it would work
4. **Consider alternatives** - Are there other ways to solve this?

**Use the feature request template** when creating an issue.

## 🔧 Submitting Pull Requests

### PR Guidelines

1. **Create an issue first** - Discuss major changes before implementing
2. **Keep PRs focused** - One feature/fix per PR
3. **Write tests** - Add tests for new features
4. **Update documentation** - Update README or docs as needed
5. **Follow the template** - Use the PR template provided

### PR Process

1. **Update your fork**
   ```bash
   git checkout develop
   git pull upstream develop
   git push origin develop
   ```

2. **Create a feature branch from develop**
   ```bash
   git checkout -b develop/your-feature
   ```

3. **Make your changes**
   - Write code
   - Add tests
   - Update docs

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add support for custom templates"
   ```

   **Commit message format:**
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test additions/changes
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks

5. **Push and create PR**
   ```bash
   git push origin develop/your-feature
   ```
   Then open a PR on GitHub targeting the **`develop`** branch (not `main`).

6. **Automated workflows will run**:
   - ✅ Tests, linting, type checking
   - 🤖 AI-generated diff summary (on commit comment)
   - Wait for all checks to pass

7. **Address review feedback**:
   ```bash
   # Make changes
   git add .
   git commit -m "fix: address review feedback"
   git push origin develop/your-feature
   ```

8. **After merge**:
   - Your changes are in `develop`
   - Auto-PR workflow creates PR to `main`
   - Maintainer reviews and merges to `main` for release

### PR Checklist

Before submitting, ensure:

- [ ] Code follows project style guidelines
- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`ruff format`)
- [ ] No linting errors (`ruff check`)
- [ ] Type checking passes (`mypy`)
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] PR description explains the changes

## 🧪 Writing Tests

We use `pytest` for testing. Tests should:

- **Be isolated** - Don't depend on other tests
- **Be fast** - Use mocks for external calls
- **Be clear** - Test one thing at a time
- **Have good names** - Describe what they test

### Test Structure

```python
def test_generate_server_module_creates_valid_code():
    """Test that server module generation produces valid Python code."""
    # Arrange
    api_class = MockApiClass()
    
    # Act
    result = generate_server_module("pet_api", api_class)
    
    # Assert
    assert result.tool_count > 0
    assert "def " in result.code
    assert result.filename.endswith("_server.py")
```

## 📚 Documentation

Good documentation is crucial:

- **README.md** - Keep the main README updated
- **Docstrings** - Document all public APIs
- **Comments** - Explain complex logic
- **Examples** - Provide usage examples
- **CHANGELOG.md** - Update for significant changes

## 🔍 Code Review Process

All submissions require review:

1. **Automated checks** run (tests, linting, type checking)
2. **AI diff summary** generated (helps reviewers understand changes)
3. **Maintainer review** provides feedback
4. **Address feedback** and update PR
5. **Approval** once all checks pass
6. **Merge to `develop`** by maintainer
7. **Auto-PR created** from `develop` to `main`
8. **Release** after `main` merge

### What Reviewers Look For

- ✅ Code quality and style
- ✅ Test coverage
- ✅ Documentation updates
- ✅ Breaking changes noted
- ✅ Performance implications
- ✅ Security considerations

## � AI-Powered Workflows

We use AI to enhance the development experience:

### Commit Summaries

Every commit to `develop` or `develop/*` branches automatically gets an AI-generated summary:

- **Model**: OpenAI GPT-5 nano (fastest, most cost-efficient)
- **Posted as**: Commit comment (visible on commit page)
- **Content**: Concise summary of what changed and why it matters
- **Smart truncation**: Large diffs are intelligently truncated to stay within token limits

**Example summary:**
```markdown
## 🤖 AI-Generated Commit Summary

**Changes**:
- Added OAuth2 authentication middleware generation
- Implemented JWT validation with JWKS support
- Updated templates to include security schemes

**Impact**:
- Breaking Change: Updated authentication config structure
- New feature: Scope enforcement middleware
```

### Viewing Summaries

1. Go to your commit on GitHub
2. Scroll to the comments section
3. See the AI-generated summary

**Note**: Merge commits are automatically skipped to avoid redundant summaries.

## �🤝 Community Guidelines

- **Be respectful** - Treat everyone with respect
- **Be constructive** - Provide helpful feedback
- **Be patient** - Maintainers are often volunteers
- **Be collaborative** - Work together towards solutions

See our [Code of Conduct](CODE_OF_CONDUCT.md) for details.

## 📞 Getting Help

- **Discord/Slack** - [Coming soon]
- **GitHub Discussions** - For questions and discussions
- **GitHub Issues** - For bugs and features
- **Email** - maxivities@gmail.com

## 🎓 Learning Resources

New to contributing? Check out:

- [First Contributions Guide](https://github.com/firstcontributions/first-contributions)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Writing Good Commit Messages](https://chris.beams.io/posts/git-commit/)

## 📄 License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

---

**Thank you for contributing to MCP Generator 2.0!** 🎉

Your contributions help make this tool better for everyone in the MCP community.
