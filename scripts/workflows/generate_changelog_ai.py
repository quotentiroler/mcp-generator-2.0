#!/usr/bin/env python3
"""
Generate AI-powered changelog from PR commit messages.
Called by update-changelog.yml workflow.
Only includes commits since the last release tag.
"""

import os
import subprocess
import sys


def filter_meaningful_commits(commits: str) -> str:
    """Filter out generic/useless commits before sending to AI."""
    if not commits:
        return ""

    lines = commits.split("\n")
    filtered = []

    skip_patterns = [
        "update",
        "Update",
        "chore: update version metadata",
        "Merge develop into staging",
        "Merge staging into",
        "Staging: Merge",
        "Release:",
        "[skip ci]",
        "github-actions[bot]",
    ]

    for line in lines:
        # Skip if line matches any skip pattern
        lower_line = line.lower()
        should_skip = False

        # Check if the commit message is ONLY "update" or similar
        if " - update " in lower_line or line.endswith(" - update"):
            should_skip = True

        # Check other skip patterns
        for pattern in skip_patterns:
            if pattern.lower() in lower_line:
                should_skip = True
                break

        if not should_skip:
            filtered.append(line)

    return "\n".join(filtered)


def is_stable_release(version: str) -> bool:
    """Check if version is a stable release (no alpha/beta/rc)."""
    return not any(pre in version.lower() for pre in ["alpha", "beta", "rc"])


def get_base_version(version: str) -> str:
    """Extract base version (e.g., '2.0.0' from '2.0.0-alpha')."""
    # Split on - and + to handle both alpha/beta/rc and metadata
    return version.split("-")[0].split("+")[0]


def get_commits_for_changelog(current_version: str) -> tuple[str, str]:
    """
    Get commit messages for changelog.

    Returns: (commits, description)
    - For pre-releases: commits since last release
    - For stable releases: ALL commits since last stable release (accumulate pre-releases)
    """
    try:
        # Get all release tags
        result = subprocess.run(
            ["git", "tag", "-l", "v*", "--sort=-version:refname"],
            capture_output=True,
            text=True,
            check=True,
        )

        tags = [tag.strip() for tag in result.stdout.strip().split("\n") if tag.strip()]

        if not tags:
            print("ℹ️  No previous release tags found, using all commits")
            result = subprocess.run(
                ["git", "log", "origin/staging", "--pretty=format:%h - %s (%an)"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout, "all commits"

        last_tag = tags[0]
        print(f"📌 Last release: {last_tag}")

        # Check if current version is stable
        if is_stable_release(current_version):
            # For stable release, find last stable release of same major.minor
            base_version = get_base_version(current_version)
            print(f"🎯 Stable release detected: {base_version}")

            # Find last stable release tag
            last_stable_tag = None
            for tag in tags:
                tag_version = tag.lstrip("v")
                if is_stable_release(tag_version) and get_base_version(tag_version) != base_version:
                    last_stable_tag = tag
                    break

            if last_stable_tag:
                print(f"📚 Accumulating changes from {last_stable_tag} (last stable)")
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        f"{last_stable_tag}..origin/staging",
                        "--pretty=format:%h - %s (%an)",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.stdout.strip(), f"accumulated from {last_stable_tag}"
            else:
                # No previous stable, get all commits
                print("📚 No previous stable release, accumulating all commits")
                result = subprocess.run(
                    ["git", "log", "origin/staging", "--pretty=format:%h - %s (%an)"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.stdout.strip(), "accumulated (all commits)"
        else:
            # For pre-release, only show changes since last release
            print(f"🔄 Pre-release detected, showing changes since {last_tag}")
            result = subprocess.run(
                ["git", "log", f"{last_tag}..origin/staging", "--pretty=format:%h - %s (%an)"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip(), f"since {last_tag}"

    except Exception as e:
        print(f"⚠️  Error getting commits: {e}")
        return "", "error"


def main():
    # Check if API key is available
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set, skipping AI generation")
        sys.exit(0)

    try:
        from openai import OpenAI
    except ImportError:
        print("⚠️  Warning: openai package not available, skipping AI generation")
        sys.exit(0)

    # Read environment variables from GitHub Actions
    pr_number = os.environ.get("PR_NUMBER", "unknown")
    pr_title = os.environ.get("PR_TITLE", "")
    pr_body = os.environ.get("PR_BODY", "")
    pr_url = os.environ.get("PR_URL", "")

    # Get current version from pyproject.toml
    try:
        import re

        with open("pyproject.toml", encoding="utf-8") as f:
            content = f.read()
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        current_version = match.group(1) if match else "unknown"
        print(f"📦 Current version: {current_version}")
    except Exception as e:
        print(f"⚠️  Could not read version from pyproject.toml: {e}")
        current_version = "unknown"

    # Get commits based on release type
    commits, commit_description = get_commits_for_changelog(current_version)

    # Filter out meaningless commits BEFORE sending to AI
    print(f"📊 Total commits: {len(commits.splitlines())}")
    commits = filter_meaningful_commits(commits)
    print(f"📝 Meaningful commits after filtering: {len(commits.splitlines())}")

    if not commits.strip():
        print(f"ℹ️  No meaningful commits {commit_description}")
        with open("changelog_entry.txt", "w") as f:
            f.write("\n- � Chores & Improvements: Internal maintenance and updates\n")
        sys.exit(0)

    # Generate summary with OpenAI
    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""Analyze these commit messages and create a professional changelog entry.

{"This is a STABLE RELEASE - accumulate ALL significant changes from alpha, beta, and rc versions." if is_stable_release(current_version) else f"This is a pre-release ({current_version}) - show ONLY changes since the last release."}

PR Title: {pr_title}
PR Description: {pr_body[:500] if pr_body else "No description"}

Format the changelog with these categories (only include categories that apply):
- ✨ Features (new functionality)
- 🐛 Bug Fixes (fixes to existing functionality)
- 📚 Documentation (documentation changes)
- 🔧 Chores & Improvements (maintenance, refactoring, CI/CD)
- ⚠️  Breaking Changes (if any)

CRITICAL FILTERING RULES - MUST FOLLOW:
1. **COMPLETELY SKIP** commits with only "update", "Update", or similar generic messages
2. **COMPLETELY SKIP** "chore: update version metadata" commits
3. **COMPLETELY SKIP** merge commits (e.g., "Merge develop into staging", "Staging: Merge", "Release: ")
4. **ONLY INCLUDE** commits with meaningful descriptions (e.g., "fix: add __init__.py", "feat: smart changelog")
5. Group duplicate/similar changes into single bullets
6. Be extremely concise - users don't care about internal commits
{"7. For stable releases: Summarize major themes, not individual commits" if is_stable_release(current_version) else ""}

**If there are NO meaningful commits** (only "update", metadata, or merge commits):
Output exactly: "- 🔧 Chores & Improvements: Internal maintenance and updates"

**Example of what NOT to include:**
- "update" (skip)
- "Update" (skip)  
- "chore: update version metadata with commit abc123 [skip ci]" (skip)
- "Staging: Merge develop into staging" (skip)
- "Release: 2.0.0-alpha (34 commits)" (skip)

**Example of what TO include:**
- "fix: add __init__.py to scripts package" (include as "Fixed scripts package distribution")
- "feat: smart changelog generation" (include as "Added intelligent changelog generation")

Commit Messages ({commit_description}):
```
{commits}
```

Generate a clean, professional changelog entry:"""

        response = client.responses.create(
            model="gpt-5-nano",
            input=prompt,
            instructions="You are a helpful assistant that creates changelog entries from commit messages. Be concise, use the specified emoji categories, and group related changes together.",
            max_output_tokens=1000,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
        )

        if response.output_text:
            changelog = response.output_text.strip()

            # Ensure it starts with a newline and category
            if not changelog.startswith("\n"):
                changelog = "\n" + changelog

            # Add PR reference
            changelog += f"\n\n**Full Changelog**: {pr_url}\n"

            with open("changelog_entry.txt", "w", encoding="utf-8") as f:
                f.write(changelog)

            print("✅ Generated AI-powered changelog entry")
            print(changelog)
        else:
            print("⚠️  No output from OpenAI, skipping")
            sys.exit(0)

    except Exception as e:
        print(f"⚠️  Error generating AI summary: {e}")
        print("   Skipping AI generation")
        sys.exit(0)


if __name__ == "__main__":
    main()
