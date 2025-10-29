#!/usr/bin/env python3
"""
Update version metadata in CHANGELOG.md and SECURITY.md with commit hash and date.

This script runs on the main branch to append the commit hash to the version
and add the current date. Auto-bumps the version if a GitHub release already exists.

Usage:
    python scripts/update_version_metadata.py
    python scripts/update_version_metadata.py --commit-hash abc123
    python scripts/update_version_metadata.py --dry-run
    python scripts/update_version_metadata.py --github-token TOKEN

The script will:
1. Read the current version from pyproject.toml
2. Check if a GitHub release exists for this version
3. Auto-bump version if release exists (2.0.0 → 2.0.1, 2.0.0-alpha → 2.0.1-alpha)
4. Get the current commit hash (short form)
5. Get the current date
6. Update CHANGELOG.md with version+hash and date
7. Update SECURITY.md with version+hash
8. Update pyproject.toml with bumped version (if bumped)

Example:
    Version: 2.0.0-alpha (release exists)
    Auto-bump: 2.0.1-alpha
    Commit: a1b2c3d
    Date: 2025-10-27

    Result: 2.0.1-alpha+a1b2c3d (2025-10-27)
"""

import argparse
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def get_git_commit_hash(short: bool = True) -> str:
    """Get the current git commit hash."""
    try:
        cmd = ["git", "rev-parse", "--short" if short else "", "HEAD"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting commit hash: {e}", file=sys.stderr)
        sys.exit(1)


def check_github_release_exists(
    repo_owner: str, repo_name: str, version: str, github_token: str | None = None
) -> bool:
    """Check if a GitHub release exists for the given version."""
    try:
        # GitHub API endpoint
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/tags/v{version}"

        # Prepare headers
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        # Make request
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise

        return False

    except Exception as e:
        print(f"⚠️  Warning: Could not check GitHub releases: {e}", file=sys.stderr)
        print("   Continuing without version bump...", file=sys.stderr)
        return False


def bump_version(version: str) -> str:
    """
    Bump the patch version number (third digit).

    Examples:
        2.0.0 → 2.0.1
        2.0.1 → 2.0.2
        2.0.0-alpha → 2.0.1-alpha
        2.0.5-beta → 2.0.6-beta
        1.2.3-rc.1 → 1.2.4-rc.1
    """
    # Match semantic version with optional pre-release suffix
    # Pattern: MAJOR.MINOR.PATCH[-prerelease]
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", version)

    if match:
        major = match.group(1)
        minor = match.group(2)
        patch = int(match.group(3))
        suffix = match.group(4)  # Everything after patch (e.g., "-alpha", "-beta.1")

        # Increment patch version
        new_patch = patch + 1
        return f"{major}.{minor}.{new_patch}{suffix}"

    # Fallback: If version doesn't match expected format, just add .1
    print(f"⚠️  Warning: Unexpected version format '{version}', adding .1", file=sys.stderr)
    return f"{version}.1"


def get_version_from_pyproject(pyproject_path: Path) -> str:
    """Extract version from pyproject.toml."""
    try:
        with open(pyproject_path, encoding="utf-8") as f:
            content = f.read()

        # Find version line
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if match:
            return match.group(1)

        print("❌ Could not find version in pyproject.toml", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ File not found: {pyproject_path}", file=sys.stderr)
        sys.exit(1)


def update_changelog(
    changelog_path: Path,
    version: str,
    commit_hash: str,
    date_str: str,
    dry_run: bool = False,
) -> bool:
    """Update CHANGELOG.md with version+hash and date."""
    try:
        with open(changelog_path, encoding="utf-8") as f:
            content = f.read()

        version_with_hash = f"{version}+{commit_hash}"

        # Pattern to match: ## [2.0.0-alpha] - 2025-10-25
        # or: ## [2.0.0-alpha+abc123] - 2025-10-25
        pattern = rf"\[{re.escape(version)}(?:\+[a-f0-9]+)?\]\s*-\s*\d{{4}}-\d{{2}}-\d{{2}}"
        replacement = f"[{version_with_hash}] - {date_str}"

        if not re.search(pattern, content):
            print(f"⚠️  Version {version} not found in CHANGELOG.md", file=sys.stderr)
            return False

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            print("ℹ️  CHANGELOG.md already up to date")
            return True

        if dry_run:
            print("🔍 DRY RUN - Would update CHANGELOG.md:")
            print(f"   {version} → {version_with_hash}")
            print(f"   Date: {date_str}")
            return True

        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Updated CHANGELOG.md: {version_with_hash} ({date_str})")
        return True

    except FileNotFoundError:
        print(f"❌ File not found: {changelog_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error updating CHANGELOG.md: {e}", file=sys.stderr)
        return False


def update_security(
    security_path: Path,
    version: str,
    commit_hash: str,
    dry_run: bool = False,
) -> bool:
    """Update SECURITY.md with version+hash."""
    try:
        with open(security_path, encoding="utf-8") as f:
            content = f.read()

        version_with_hash = f"{version}+{commit_hash}"

        # Pattern to match version in the table
        # | 2.0.0-alpha   | :white_check_mark: | Pre-release |
        # or | 2.0.0-alpha+abc123 | :white_check_mark: | Pre-release |
        pattern = rf"\|\s*{re.escape(version)}(?:\+[a-f0-9]+)?\s*\|"
        replacement = f"| {version_with_hash}   |"

        if not re.search(pattern, content):
            print(f"⚠️  Version {version} not found in SECURITY.md", file=sys.stderr)
            return False

        new_content = re.sub(pattern, replacement, content)

        if new_content == content:
            print("ℹ️  SECURITY.md already up to date")
            return True

        if dry_run:
            print("🔍 DRY RUN - Would update SECURITY.md:")
            print(f"   {version} → {version_with_hash}")
            return True

        with open(security_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Updated SECURITY.md: {version_with_hash}")
        return True

    except FileNotFoundError:
        print(f"❌ File not found: {security_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error updating SECURITY.md: {e}", file=sys.stderr)
        return False


def update_pyproject_version(
    pyproject_path: Path,
    new_version: str,
    dry_run: bool = False,
) -> bool:
    """Update version in pyproject.toml."""
    try:
        with open(pyproject_path, encoding="utf-8") as f:
            content = f.read()

        # Pattern to match version line
        pattern = r'^(version\s*=\s*["\'])([^"\']+)(["\'])'

        def replace_version(match):
            return f"{match.group(1)}{new_version}{match.group(3)}"

        new_content = re.sub(pattern, replace_version, content, flags=re.MULTILINE)

        if new_content == content:
            print("ℹ️  pyproject.toml already up to date")
            return True

        if dry_run:
            print("🔍 DRY RUN - Would update pyproject.toml:")
            print(f"   version → {new_version}")
            return True

        with open(pyproject_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Updated pyproject.toml: {new_version}")
        return True

    except FileNotFoundError:
        print(f"❌ File not found: {pyproject_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error updating pyproject.toml: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update version metadata with commit hash and date",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update with current commit and date
  python scripts/update_version_metadata.py

  # Specify commit hash manually
  python scripts/update_version_metadata.py --commit-hash abc123

  # Dry run (show what would be changed)
  python scripts/update_version_metadata.py --dry-run

  # Specify custom date
  python scripts/update_version_metadata.py --date 2025-10-27
        """,
    )

    parser.add_argument(
        "--commit-hash",
        type=str,
        help="Commit hash to use (default: current HEAD)",
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Date to use in YYYY-MM-DD format (default: today)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without actually changing files",
    )

    parser.add_argument(
        "--github-token",
        type=str,
        help="GitHub token for API access (default: GITHUB_TOKEN env var)",
    )

    args = parser.parse_args()

    # Get root directory (script is in scripts/workflows/, so go up 3 levels)
    root_dir = Path(__file__).parent.parent.parent

    # Get commit hash
    if args.commit_hash:
        commit_hash = args.commit_hash
        print(f"📌 Using provided commit hash: {commit_hash}")
    else:
        commit_hash = get_git_commit_hash(short=True)
        print(f"📌 Current commit hash: {commit_hash}")

    # Get date
    if args.date:
        date_str = args.date
        print(f"📅 Using provided date: {date_str}")
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        print(f"📅 Current date: {date_str}")

    # Get version from pyproject.toml
    pyproject_path = root_dir / "pyproject.toml"
    version = get_version_from_pyproject(pyproject_path)
    print(f"📦 Current version: {version}")

    # Check if release exists and bump version if needed
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN")
    repo_owner = "quotentiroler"
    repo_name = "mcp-generator-2.0"

    release_exists = check_github_release_exists(repo_owner, repo_name, version, github_token)

    if release_exists:
        original_version = version
        version = bump_version(version)
        print(f"🔄 Release v{original_version} exists - bumping to {version}")
        version_was_bumped = True
    else:
        print(f"ℹ️  No release found for v{version} - keeping version as-is")
        version_was_bumped = False

    print()

    # Update files
    changelog_path = root_dir / "CHANGELOG.md"
    security_path = root_dir / "SECURITY.md"

    changelog_success = update_changelog(
        changelog_path, version, commit_hash, date_str, args.dry_run
    )
    security_success = update_security(security_path, version, commit_hash, args.dry_run)

    # Update pyproject.toml only if version was bumped
    pyproject_success = True
    if version_was_bumped:
        pyproject_success = update_pyproject_version(pyproject_path, version, args.dry_run)

    print()

    if changelog_success and security_success and pyproject_success:
        print("=" * 70)
        print("✅ VERSION METADATA UPDATE COMPLETE")
        print("=" * 70)
        print(f"Version: {version}+{commit_hash}")
        print(f"Date: {date_str}")
        if args.dry_run:
            print()
            print("⚠️  This was a DRY RUN - no files were actually changed")
        print("=" * 70)
        sys.exit(0)
    else:
        print("=" * 70)
        print("❌ VERSION METADATA UPDATE FAILED")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
