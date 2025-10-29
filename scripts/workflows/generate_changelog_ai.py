#!/usr/bin/env python3
"""
Generate AI-powered changelog from PR commit messages.
Called by update-changelog.yml workflow.
"""

import os
import sys


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

    # Read the commit messages
    try:
        with open("commit_messages.txt", encoding="utf-8") as f:
            commits = f.read()
    except Exception as e:
        print(f"⚠️  Warning: Could not read commit messages: {e}")
        sys.exit(0)

    if not commits.strip():
        print("ℹ️  No commit messages found")
        with open("changelog_entry.txt", "w") as f:
            f.write(f"\n### 🔄 Changes\n\n- Merged PR #{pr_number}: {pr_title}\n")
        sys.exit(0)

    print(f"📝 Analyzing {len(commits.splitlines())} lines of commit messages")

    # Generate summary with OpenAI
    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""Analyze these commit messages from PR #{pr_number} and create a structured changelog entry.

PR Title: {pr_title}
PR Description: {pr_body[:500] if pr_body else "No description"}

Format the changelog with these categories (only include categories that apply):
- ✨ Features (new functionality)
- 🐛 Bug Fixes (fixes to existing functionality)
- 📚 Documentation (documentation changes)
- 🔧 Chores & Improvements (maintenance, refactoring, CI/CD)
- ⚠️  Breaking Changes (if any)

Use bullet points. Be concise but informative. Focus on what matters to users/developers.
Group related commits together. Skip merge commits and trivial commits (like "update", "fix typo").

Commit Messages:
```
{commits}
```

Changelog Entry:"""

        response = client.responses.create(
            model="gpt-5-nano",
            input=prompt,
            instructions="You are a helpful assistant that creates changelog entries from commit messages. Be concise, use the specified emoji categories, and group related changes together.",
            max_output_tokens=1000,
            reasoning=dict(effort="minimal"),
            text=dict(verbosity="low"),
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
