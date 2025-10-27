# Git Hooks

This directory contains Git hooks for automated code quality checks.

## Pre-commit Hook

Automatically formats Python code with `ruff` before each commit.

### Setup

#### Linux/macOS

```bash
# Configure Git to use this hooks directory
git config core.hooksPath .githooks

# Make the hook executable
chmod +x .githooks/pre-commit
```

#### Windows (PowerShell)

```powershell
# Configure Git to use this hooks directory
git config core.hooksPath .githooks
```

**Note**: Windows will use `pre-commit.ps1` automatically if the `.sh` script fails.

### What it does

1. Detects staged Python files
2. Runs `ruff format` to auto-format code
3. Runs `ruff check --fix` to auto-fix lint issues
4. Re-stages the formatted files
5. Allows the commit to proceed

### Bypass (when needed)

If you need to bypass the hook for a specific commit:

```bash
git commit --no-verify -m "your message"
```

### Troubleshooting

If the hook doesn't run:

1. Verify the hooks path: `git config core.hooksPath`
2. On Linux/macOS, ensure the hook is executable: `ls -la .githooks/pre-commit`
3. Test the hook manually: `.githooks/pre-commit` (Linux/macOS) or `.githooks/pre-commit.ps1` (Windows)
