#!/usr/bin/env python3
"""Retitle a prerelease CHANGELOG section as its stable release.

When a version reaches main it stops being a prerelease, so the heading it was
given on the test branch has to follow it:

    ## [3.2.6-beta+a5c3942] - 2026-08-26   ->   ## [3.2.6] - 2026-08-26

The date and separator are preserved via group 1. Note the ``\\g<1>`` in the
replacement: a bare ``\\1`` is read as the octal escape ``\\120`` once the year
follows it, which is what produced headings like ``## [3.2.5]P26-04-25``.

Environment:
    CURRENT_VERSION   version being promoted (a +sha suffix is ignored)
    STABLE_VERSION    version to retitle it to
"""

import os
import re
import sys
from pathlib import Path


def retitle(content: str, current: str, stable: str) -> tuple[str, int]:
    """Rewrite the heading for `current` so it reads as `stable`."""
    pattern = (
        rf"## \[{re.escape(current)}(?:\+[a-f0-9]+)?\]"
        rf"(\s*-\s*\d{{4}}-\d{{2}}-\d{{2}})"
    )
    return re.subn(pattern, rf"## [{stable}]\g<1>", content)


def main() -> None:
    try:
        current = os.environ["CURRENT_VERSION"].split("+")[0]
        stable = os.environ["STABLE_VERSION"]
    except KeyError as exc:
        print(f"Missing environment variable: {exc}", file=sys.stderr)
        sys.exit(1)

    if current == stable:
        print(f"Version is already stable ({stable}); nothing to retitle")
        return

    path = Path("CHANGELOG.md")
    if not path.exists():
        print("No CHANGELOG.md; nothing to retitle")
        return

    content = path.read_text(encoding="utf-8")
    new_content, count = retitle(content, current, stable)

    if count:
        path.write_text(new_content, encoding="utf-8")
        print(f"CHANGELOG heading retitled: {current} -> {stable} ({count})")
    else:
        print(f"No CHANGELOG heading found for {current}; leaving it alone")


if __name__ == "__main__":
    main()
