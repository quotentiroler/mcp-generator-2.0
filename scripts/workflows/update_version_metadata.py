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


VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$")

CHANNEL_SUFFIX = {"alpha": "-alpha", "beta": "-beta", "stable": ""}


def set_channel(version: str, channel: str) -> str:
    """Pin a version to a release channel.

    The branch decides the channel, so this replaces any existing suffix rather
    than advancing a stage ladder:
        develop -> alpha, test -> beta, main -> stable

    Examples:
        3.2.6-alpha, "beta"   -> 3.2.6-beta
        3.2.6-rc.2, "stable"  -> 3.2.6
        3.2.6, "beta"         -> 3.2.6-beta
    """
    if channel not in CHANNEL_SUFFIX:
        raise ValueError(f"Unknown release channel: {channel}")

    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(f"Unexpected version format: {version}")

    base = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    return f"{base}{CHANNEL_SUFFIX[channel]}"


BUMP_LEVELS = ("patch", "minor", "major")


def bump_semver(version: str, level: str = "patch") -> str:
    """Bump one semver component, keeping whatever channel suffix is present.

        3.2.13-beta, "patch"  -> 3.2.14-beta
        3.2.13-beta, "minor"  -> 3.3.0-beta
        3.2.13-beta, "major"  -> 4.0.0-beta

    A minor or major bump is never inferred. Raising a dependency floor or
    changing generated output is a judgement call, so it is requested
    explicitly via --bump or the Manual Version Bump workflow.
    """
    if level not in BUMP_LEVELS:
        raise ValueError(f"Unknown bump level: {level}; expected one of {BUMP_LEVELS}")

    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(f"Unexpected version format: {version}")

    major, minor, patch = (int(match.group(i)) for i in (1, 2, 3))
    if level == "major":
        major, minor, patch = major + 1, 0, 0
    elif level == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1

    base = f"{major}.{minor}.{patch}"
    prerelease = match.group(4)
    return f"{base}-{prerelease}" if prerelease else base


def bump_within_channel(version: str) -> str:
    """Bump the patch number without leaving the current channel."""
    return bump_semver(version, "patch")


def bump_version(version: str) -> str:
    """
    Bump version according to release stage progression.

    Progression:
        Stable → Alpha:     2.0.0 → 2.0.1-alpha
        Alpha → Beta:       2.0.0-alpha → 2.0.0-beta
        Beta → RC:          2.0.0-beta → 2.0.0-rc
        RC → RC.N:          2.0.0-rc → 2.0.0-rc.1, 2.0.0-rc.1 → 2.0.0-rc.2
        RC.N → Stable:      2.0.0-rc.2 → 2.0.0 (manual)

    Examples:
        2.0.0 → 2.0.1-alpha
        2.0.1 → 2.0.2-alpha
        2.0.0-alpha → 2.0.0-beta
        2.0.0-beta → 2.0.0-rc
        2.0.0-rc → 2.0.0-rc.1
        2.0.0-rc.1 → 2.0.0-rc.2
    """
    # Match: MAJOR.MINOR.PATCH[-prerelease]
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version)

    if not match:
        # Fallback for unexpected format
        print(f"⚠️  Warning: Unexpected version format '{version}', adding .1", file=sys.stderr)
        return f"{version}.1"

    major = match.group(1)
    minor = match.group(2)
    patch = int(match.group(3))
    prerelease = match.group(4)  # None if stable, otherwise "alpha", "beta", "rc", "rc.1", etc.

    if prerelease is None:
        # Stable version → bump patch and add -alpha
        new_patch = patch + 1
        return f"{major}.{minor}.{new_patch}-alpha"

    elif prerelease == "alpha":
        # Alpha → Beta
        return f"{major}.{minor}.{patch}-beta"

    elif prerelease == "beta":
        # Beta → RC
        return f"{major}.{minor}.{patch}-rc"

    elif prerelease == "rc":
        # RC (without number) → RC.1
        return f"{major}.{minor}.{patch}-rc.1"

    elif prerelease.startswith("rc."):
        # RC.N → RC.(N+1)
        rc_match = re.match(r"^rc\.(\d+)$", prerelease)
        if rc_match:
            rc_num = int(rc_match.group(1))
            return f"{major}.{minor}.{patch}-rc.{rc_num + 1}"
        else:
            print(f"⚠️  Warning: Unexpected RC format '{prerelease}'", file=sys.stderr)
            return version

    else:
        # Unknown pre-release format - keep as-is
        print(f"⚠️  Warning: Unknown pre-release format '{prerelease}' - no bump", file=sys.stderr)
        return version


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


def create_changelog_section(
    changelog_path: Path,
    version: str,
    date_str: str,
    dry_run: bool = False,
) -> bool:
    """Create a new section in CHANGELOG.md for the bumped version."""
    try:
        with open(changelog_path, encoding="utf-8") as f:
            content = f.read()

        # Check if section already exists
        pattern = rf"## \[{re.escape(version)}(?:\+[a-f0-9]+)?\]"
        if re.search(pattern, content):
            print(f"ℹ️  Changelog section for {version} already exists")
            return True

        # Find the first ## [ section and insert before it
        match = re.search(r"(## \[)", content)
        if not match:
            print("⚠️  Could not find existing version section in CHANGELOG.md", file=sys.stderr)
            return False

        # Create new section
        new_section = f"""## [{version}] - {date_str}

### Changed

- Dependencies updated

"""

        insert_pos = match.start()
        new_content = content[:insert_pos] + new_section + content[insert_pos:]

        if dry_run:
            print("🔍 DRY RUN - Would create new CHANGELOG.md section:")
            print(f"   ## [{version}] - {date_str}")
            return True

        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Created CHANGELOG.md section: [{version}] - {date_str}")
        return True

    except FileNotFoundError:
        print(f"❌ File not found: {changelog_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error creating CHANGELOG.md section: {e}", file=sys.stderr)
        return False


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
            print("   Skipping - version entry will be added by changelog workflow")
            return True  # Not an error, just skip

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
            print("   Skipping - version entry will be added manually")
            return True  # Not an error, just skip

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
        "--bump",
        type=str,
        choices=list(BUMP_LEVELS),
        help="Bump this semver component before applying the channel",
    )

    parser.add_argument(
        "--set-version",
        type=str,
        help="Set an exact base version (X.Y.Z), overriding --bump",
    )

    parser.add_argument(
        "--channel",
        type=str,
        choices=["alpha", "beta", "stable"],
        help="Pin the version to a release channel instead of advancing the stage ladder",
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

    version_on_disk = version

    if args.set_version:
        if not re.fullmatch(r"\d+\.\d+\.\d+", args.set_version):
            print(f"❌ --set-version must be X.Y.Z, got {args.set_version!r}", file=sys.stderr)
            sys.exit(1)
        print(f"📌 Version set explicitly: {version} -> {args.set_version}")
        version = args.set_version
    elif args.bump:
        bumped = bump_semver(version, args.bump)
        print(f"⬆️  {args.bump} bump: {version} -> {bumped}")
        version = bumped

    if args.channel:
        pinned = set_channel(version, args.channel)
        if pinned != version:
            print(f"🎯 Channel '{args.channel}': {version} -> {pinned}")
        version = pinned

    # Check if release exists and bump version if needed
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN")
    repo_owner = "quotentiroler"
    repo_name = "mcp-generator-3.x"

    release_exists = check_github_release_exists(repo_owner, repo_name, version, github_token)

    if release_exists:
        original_version = version
        version = bump_within_channel(version) if args.channel else bump_version(version)
        print(f"🔄 Release v{original_version} exists - bumping to {version}")
        version_was_bumped = True
    else:
        print(f"ℹ️  No release found for v{version} - keeping version as-is")
        version_was_bumped = False

    print()

    # Update files
    changelog_path = root_dir / "CHANGELOG.md"
    security_path = root_dir / "SECURITY.md"

    # Create new changelog section if version was bumped
    if version_was_bumped:
        create_changelog_section(changelog_path, version, date_str, args.dry_run)

    changelog_success = update_changelog(
        changelog_path, version, commit_hash, date_str, args.dry_run
    )
    security_success = update_security(security_path, version, commit_hash, args.dry_run)

    # Write pyproject.toml whenever the version actually moved. A channel pin
    # (3.2.7-beta -> 3.2.7) changes it without being a bump, and skipping the
    # write there left main tagged stable while pyproject still said -beta.
    pyproject_success = True
    if version != version_on_disk:
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
