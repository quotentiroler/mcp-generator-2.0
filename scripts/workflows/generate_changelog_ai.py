#!/usr/bin/env python3
"""
Generate AI-powered changelog from AI commit summaries.
Called by update-changelog.yml workflow.
Fetches AI-generated commit comments from GitHub API and summarizes them.
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


def get_commit_summaries_from_github(current_version: str) -> tuple[str, str]:
    """
    Get AI-generated commit comment summaries from GitHub API.

    Returns: (summaries, description)
    - For pre-releases: summaries since last release
    - For stable releases: ALL summaries since last stable release (accumulate pre-releases)
    """
    import json
    import urllib.request

    try:
        # Get all release tags
        result = subprocess.run(
            ["git", "tag", "-l", "v*", "--sort=-version:refname"],
            capture_output=True,
            text=True,
            check=True,
        )

        tags = [tag.strip() for tag in result.stdout.strip().split("\n") if tag.strip()]

        # Determine commit range
        if not tags:
            print("ℹ️  No previous release tags found, using all commits")
            commit_range = "origin/staging"
            description = "all commits"
        else:
            last_tag = tags[0]
            print(f"📌 Last release: {last_tag}")

            # Check if current version is stable
            if is_stable_release(current_version):
                base_version = get_base_version(current_version)
                print(f"🎯 Stable release detected: {base_version}")

                # Find last stable release tag
                last_stable_tag = None
                for tag in tags:
                    tag_version = tag.lstrip("v")
                    if (
                        is_stable_release(tag_version)
                        and get_base_version(tag_version) != base_version
                    ):
                        last_stable_tag = tag
                        break

                if last_stable_tag:
                    print(f"📚 Accumulating changes from {last_stable_tag} (last stable)")
                    commit_range = f"{last_stable_tag}..origin/staging"
                    description = f"accumulated from {last_stable_tag}"
                else:
                    print("📚 No previous stable release, accumulating all commits")
                    commit_range = "origin/staging"
                    description = "accumulated (all commits)"
            else:
                print(f"🔄 Pre-release detected, showing changes since {last_tag}")
                commit_range = f"{last_tag}..origin/staging"
                description = f"since {last_tag}"

        # Get commit SHAs in the range
        result = subprocess.run(
            ["git", "log", commit_range, "--pretty=format:%H"],
            capture_output=True,
            text=True,
            check=True,
        )

        commit_shas = [sha.strip() for sha in result.stdout.strip().split("\n") if sha.strip()]
        print(f"📊 Found {len(commit_shas)} commits in range")

        # Fetch commit comments from GitHub API
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY", "")

        if not token or not repo:
            print("⚠️  No GitHub token/repo, falling back to commit messages")
            result = subprocess.run(
                ["git", "log", commit_range, "--pretty=format:%h - %s"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip(), description

        summaries = []
        for sha in commit_shas:
            try:
                # Fetch commit comments from GitHub API
                url = f"https://api.github.com/repos/{repo}/commits/{sha}/comments"
                req = urllib.request.Request(url)
                req.add_header("Authorization", f"token {token}")
                req.add_header("Accept", "application/vnd.github.v3+json")

                with urllib.request.urlopen(req, timeout=10) as response:
                    comments = json.loads(response.read().decode())

                # Find AI-generated summary comment
                for comment in comments:
                    body = comment.get("body", "")
                    if "AI-Generated Commit Summary" in body or "🤖" in body:
                        # Extract the summary content (remove the header)
                        lines = body.split("\n")
                        summary_lines = []
                        skip_header = True
                        for line in lines:
                            if skip_header and (
                                "##" in line or "---" in line or "Generated by" in line
                            ):
                                continue
                            skip_header = False
                            if line.strip() and not line.startswith("*Generated by"):
                                summary_lines.append(line.strip())

                        if summary_lines:
                            summaries.append(f"{sha[:7]}: " + " ".join(summary_lines))
                            break

            except Exception as e:
                print(f"⚠️  Could not fetch comments for {sha[:7]}: {e}")
                continue

        if not summaries:
            print("⚠️  No AI summaries found, falling back to commit messages")
            result = subprocess.run(
                ["git", "log", commit_range, "--pretty=format:%h - %s"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip(), description

        print(f"✅ Found {len(summaries)} AI-generated commit summaries")
        return "\n".join(summaries), description

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

    # Get commit summaries from GitHub API
    commits, commit_description = get_commit_summaries_from_github(current_version)

    if not commits.strip():
        print(f"ℹ️  No commit summaries found {commit_description}")
        with open("changelog_entry.txt", "w") as f:
            f.write("\n- 🔧 Chores & Improvements: Internal maintenance and updates\n")
        sys.exit(0)

    print(f"📝 Analyzing {len(commits.splitlines())} AI-generated summaries ({commit_description})")

    # Generate summary with OpenAI
    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""Analyze these AI-generated commit summaries and create a high-level changelog entry.

{"This is a STABLE RELEASE - consolidate ALL significant changes from alpha, beta, and rc versions into major themes." if is_stable_release(current_version) else f"This is a pre-release ({current_version}) - summarize changes since the last release."}

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

RULES:
1. Group related summaries together under broader themes
2. Don't list every individual commit - summarize the overall impact
3. Focus on user-facing or developer-relevant changes
4. Skip internal/trivial changes unless they're significant
{"5. For stable releases: Create a cohesive narrative of all improvements across pre-releases" if is_stable_release(current_version) else ""}

If NO meaningful changes, output: "- 🔧 Chores & Improvements: Internal maintenance and updates"

AI Commit Summaries ({commit_description}):
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
