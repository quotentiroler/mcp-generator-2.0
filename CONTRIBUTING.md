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

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync --group dev
   
   # Or using pip
   pip install -e ".[dev]"
   ```

3. **Install OpenAPI Generator**
   ```bash
   npm install -g @openapitools/openapi-generator-cli
   ```

4. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
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

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code with Ruff
uv run ruff format .

# Lint code
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Type checking with mypy
uv run mypy mcp_generator/
```

**Before submitting a PR, ensure:**
- ✅ All tests pass
- ✅ Code is formatted with Ruff
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
   git checkout main
   git pull upstream main
   git push origin main
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature
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
   git push origin feature/your-feature
   ```
   Then open a PR on GitHub.

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
2. **Maintainer review** provides feedback
3. **Address feedback** and update PR
4. **Approval** once all checks pass
5. **Merge** by maintainer

## 🤝 Community Guidelines

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
