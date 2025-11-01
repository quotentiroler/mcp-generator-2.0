#!/usr/bin/env python3
"""
Generate AI-powered changelog from AI commit summaries.
Called by update-changelog.yml workflow.
Only includes commits since the last release tag.
"""

import os
import subprocess
import sys


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

    if not commits.strip():
        print(f"ℹ️  No new commits {commit_description}")
        with open("changelog_entry.txt", "w") as f:
            f.write("\n- 🔧 Chores & Improvements: Internal maintenance and updates\n")
        sys.exit(0)

    print(f"📝 Analyzing {len(commits.splitlines())} commit messages ({commit_description})")

    # Generate summary with OpenAI
    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""Analyze these commit messages from recent changes and create a concise changelog entry.

{"This is a STABLE RELEASE - accumulate ALL significant changes from alpha, beta, and rc versions." if is_stable_release(current_version) else f"This is a pre-release ({current_version}) - show ONLY changes since the last release."}

PR Title: {pr_title}
PR Description: {pr_body[:500] if pr_body else "No description"}

Each line below is an AI-generated summary of a commit's changes.
Your task: Create a concise, high-level changelog by grouping related changes.

Format the changelog with these categories (only include categories that apply):
- ✨ Features (new functionality)
- 🐛 Bug Fixes (fixes to existing functionality)
- 📚 Documentation (documentation changes)
- 🔧 Chores & Improvements (maintenance, refactoring, CI/CD)
- ⚠️  Breaking Changes (if any)

IMPORTANT RULES:
1. Skip ALL "update" commits unless they have meaningful context
2. Skip merge commits (e.g., "Merge develop into staging")
3. Skip metadata commits (e.g., "chore: update version metadata")
4. Group duplicate/similar fixes together
5. Be concise - combine related changes into single bullets
6. Focus on user-facing or developer-relevant changes only
{"7. For stable releases: Group and summarize all major features/fixes from pre-releases" if is_stable_release(current_version) else ""}

If NO meaningful changes are found (only "update" commits), output:
"- 🔧 Chores & Improvements: Internal updates and maintenance"

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
