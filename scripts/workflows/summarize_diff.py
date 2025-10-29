#!/usr/bin/env python3
"""
Generate concise summaries of git diffs using OpenAI Responses API.

This script analyzes git diffs and creates human-readable summaries
of changes made in commits using GPT-5 nano. Large diffs are truncated to stay within token limits
while maintaining context.

Usage:
    python scripts/summarize_diff.py [--base-ref BASE] [--head-ref HEAD]

Environment Variables:
    OPENAI_API_KEY: Required - Your OpenAI API key
"""

import argparse
import os
import subprocess
import sys

# Maximum characters per file's diff before truncation
MAX_CHARS_PER_FILE = 1000


def get_git_diff(base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> str:
    """Get git diff between two references."""
    try:
        result = subprocess.run(
            ["git", "diff", base_ref, head_ref],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting git diff: {e}", file=sys.stderr)
        print(f"   stdout: {e.stdout}", file=sys.stderr)
        print(f"   stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def truncate_file_diff(diff_section: str, max_chars: int = MAX_CHARS_PER_FILE) -> str:
    """
    Truncate a single file's diff if it's too large.

    Keeps the file header (diff --git, ---, +++, @@) and truncates the content.
    """
    if len(diff_section) <= max_chars:
        return diff_section

    lines = diff_section.split("\n")

    # Keep all header lines (metadata and hunk headers)
    header_lines = []
    content_lines = []

    for line in lines:
        if (
            line.startswith("diff --git")
            or line.startswith("index ")
            or line.startswith("---")
            or line.startswith("+++")
            or line.startswith("@@")
        ):
            header_lines.append(line)
        else:
            content_lines.append(line)

    # Calculate space available for content
    header_text = "\n".join(header_lines)
    available_chars = max_chars - len(header_text) - 100  # Reserve space for truncation message

    if available_chars < 100:
        # If header is too large, just show truncation message
        return header_text + "\n... [diff too large, truncated]"

    # Truncate content and add message
    content_text = "\n".join(content_lines)
    if len(content_text) > available_chars:
        truncated_chars = len(content_text) - available_chars
        content_text = (
            content_text[:available_chars] + f"\n... [truncated {truncated_chars} more chars]"
        )

    return header_text + "\n" + content_text


def truncate_diff(diff: str, max_chars_per_file: int = MAX_CHARS_PER_FILE) -> str:
    """
    Truncate diff by processing each file separately.

    Each file's diff is truncated to max_chars_per_file characters.
    """
    if not diff.strip():
        return diff

    # Split into file sections
    file_sections = []
    current_section = []

    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            if current_section:
                file_sections.append("\n".join(current_section))
            current_section = [line]
        else:
            current_section.append(line)

    # Add the last section
    if current_section:
        file_sections.append("\n".join(current_section))

    # Process each file section
    truncated_sections = []
    for section in file_sections:
        truncated_section = truncate_file_diff(section, max_chars_per_file)
        truncated_sections.append(truncated_section)

    return "\n\n".join(truncated_sections)


def summarize_with_openai(diff: str, api_key: str) -> str:
    """Generate a concise summary of the diff using OpenAI Responses API with GPT-5 nano."""
    try:
        # Import here to avoid requiring openai if not using this feature
        from openai import OpenAI
    except ImportError:
        return "Error: openai package not installed. Install with: pip install openai"

    if not diff.strip():
        return "No changes detected in this commit."

    client = OpenAI(api_key=api_key)

    prompt = f"""Analyze this git diff and provide a CONCISE summary (2-4 sentences max).

Focus ONLY on:
- What changed (be specific but brief)
- Why it matters

Be direct and technical. No fluff.

Git Diff:
```
{diff}
```

Summary:"""

    try:
        response = client.responses.create(
            model="gpt-5-nano",
            input=prompt,
            instructions="You are a technical assistant that creates ultra-concise diff summaries. Maximum 4 sentences. Be direct and specific.",
            max_output_tokens=200,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
        )

        if response.output_text:
            return response.output_text.strip()

        return "Unable to generate summary (no output text)."

    except Exception as e:
        return f"Unable to generate AI summary: {str(e)}"


def get_commit_info(ref: str = "HEAD") -> dict[str, str]:
    """Get commit information."""
    try:
        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "--short", ref],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = hash_result.stdout.strip()

        # Get commit message
        msg_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", ref],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_message = msg_result.stdout.strip()

        # Get author
        author_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%an", ref],
            capture_output=True,
            text=True,
            check=True,
        )
        author = author_result.stdout.strip()

        return {
            "hash": commit_hash,
            "message": commit_message,
            "author": author,
        }
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Could not get commit info: {e}", file=sys.stderr)
        return {
            "hash": "unknown",
            "message": "unknown",
            "author": "unknown",
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate concise summaries of git diffs using OpenAI API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summarize latest commit
  python scripts/summarize_diff.py

  # Summarize changes between two refs
  python scripts/summarize_diff.py --base-ref main --head-ref develop

  # Summarize changes in current branch vs main
  python scripts/summarize_diff.py --base-ref origin/main --head-ref HEAD

Environment Variables:
  OPENAI_API_KEY: Required - Your OpenAI API key
        """,
    )

    parser.add_argument(
        "--base-ref",
        type=str,
        default="HEAD~1",
        help="Base reference for diff (default: HEAD~1)",
    )

    parser.add_argument(
        "--head-ref",
        type=str,
        default="HEAD",
        help="Head reference for diff (default: HEAD)",
    )

    parser.add_argument(
        "--max-chars",
        type=int,
        default=MAX_CHARS_PER_FILE,
        help=f"Maximum characters per file's diff before truncation (default: {MAX_CHARS_PER_FILE})",
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    print("📊 Analyzing git diff...", file=sys.stderr)
    print(f"   Base: {args.base_ref}", file=sys.stderr)
    print(f"   Head: {args.head_ref}", file=sys.stderr)
    print(file=sys.stderr)

    # Get commit info for context
    commit_info = get_commit_info(args.head_ref)

    # Get diff
    diff = get_git_diff(args.base_ref, args.head_ref)

    if not diff.strip():
        print("ℹ️  No changes detected between the specified references.", file=sys.stderr)
        return

    # Truncate if needed
    original_size = len(diff)
    diff = truncate_diff(diff, args.max_chars)
    truncated_size = len(diff)

    if truncated_size < original_size:
        print(f"📉 Diff truncated: {original_size} → {truncated_size} chars", file=sys.stderr)
        print(file=sys.stderr)

    # Generate summary
    print("🤖 Generating summary with OpenAI GPT-5 nano...", file=sys.stderr)
    print(file=sys.stderr)

    summary = summarize_with_openai(diff, api_key)

    # Print results to stdout (for commit message) - CONCISE FORMAT
    print(f"Diff Summary: {summary}")
    print()
    print(f"Commit: {commit_info['hash']} by {commit_info['author']}")
    if truncated_size < original_size:
        print(f"(Diff truncated: {original_size} → {truncated_size} chars)")


if __name__ == "__main__":
    main()
