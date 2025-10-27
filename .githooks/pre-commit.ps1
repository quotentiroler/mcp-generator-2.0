# Pre-commit hook for Windows PowerShell
# Auto-formats code with ruff before commit

Write-Host "🔍 Running pre-commit checks..." -ForegroundColor Cyan

# Get list of staged Python files
$stagedFiles = git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.py$' }

if (-not $stagedFiles) {
    Write-Host "✅ No Python files to format" -ForegroundColor Green
    exit 0
}

Write-Host "📝 Formatting Python files with ruff..." -ForegroundColor Cyan

# Format staged files
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run ruff format $stagedFiles
} else {
    ruff format $stagedFiles
}

# Run linting
Write-Host "🔍 Running ruff lint..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run ruff check --fix $stagedFiles
} else {
    ruff check --fix $stagedFiles
}

# Add formatted files back to staging
git add $stagedFiles

Write-Host "✅ Pre-commit checks complete" -ForegroundColor Green
exit 0
