#!/usr/bin/env python3
"""Compute the next release version from the git tags.

The version is no longer stored in pyproject.toml. hatch-vcs derives it from
the tag, so the tag is the single source of truth and a tag can never disagree
with the version it ships — which is exactly how v4.0.0-beta twice ended up
pointing at content that said something else.

Channels:
    stable  vX.Y.Z      cut on main
    beta    vX.Y.ZbN    cut on test, N increasing within one base version

The bump level stays explicit, matching the policy already stated in
update_version_metadata.bump_semver: patch is the default, and minor or major
must be asked for, via --bump or a `Release-Bump:` trailer on the merge commit.

Usage:
    next_version.py --channel stable
    next_version.py --channel beta --bump minor
    next_version.py --channel beta --tags "v4.0.1 v4.0.2b1"   # for tests
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from update_version_metadata import BUMP_LEVELS, bump_semver  # noqa: E402

STABLE_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
BETA_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)b(\d+)$")
TRAILER_RE = re.compile(r"^Release-Bump:\s*(patch|minor|major)\s*$", re.M | re.I)


def read_tags() -> list[str]:
    """Every tag in the repository, newest first is not assumed."""
    out = subprocess.run(
        ["git", "tag", "--list"], capture_output=True, text=True, check=True
    ).stdout
    return [t.strip() for t in out.splitlines() if t.strip()]


def latest_stable(tags: list[str]) -> str:
    """Highest vX.Y.Z tag, or 0.0.0 when the repo has never released."""
    versions = [tuple(int(g) for g in m.groups()) for m in (STABLE_RE.match(t) for t in tags) if m]
    if not versions:
        return "0.0.0"
    return ".".join(str(n) for n in max(versions))


def bump_from_trailer(message: str) -> str | None:
    """The level named by a `Release-Bump:` trailer, if the commit carries one."""
    match = TRAILER_RE.search(message or "")
    return match.group(1).lower() if match else None


def next_beta(tags: list[str], base: str) -> str:
    """The next unused vX.Y.ZbN for this base, so PyPI never sees a reuse."""
    prefix = tuple(int(p) for p in base.split("."))
    used = [
        int(m.group(4))
        for m in (BETA_RE.match(t) for t in tags)
        if m and tuple(int(m.group(i)) for i in (1, 2, 3)) == prefix
    ]
    return f"{base}b{max(used) + 1 if used else 1}"


def resolve(channel: str, tags: list[str], level: str) -> str:
    """The version this channel should publish next."""
    base = bump_semver(latest_stable(tags), level)
    if channel == "stable":
        return base
    if channel == "beta":
        return next_beta(tags, base)
    raise ValueError(f"Unknown channel: {channel}; expected 'stable' or 'beta'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True, choices=("stable", "beta"))
    parser.add_argument("--bump", choices=BUMP_LEVELS, default=None)
    parser.add_argument("--message", default="", help="Commit message to read a trailer from")
    parser.add_argument("--tags", default=None, help="Space-separated tags instead of git")
    parser.add_argument("--print-tag", action="store_true", help="Print v-prefixed tag name")
    args = parser.parse_args()

    tags = args.tags.split() if args.tags is not None else read_tags()
    level = args.bump or bump_from_trailer(args.message) or "patch"
    version = resolve(args.channel, tags, level)
    print(f"v{version}" if args.print_tag else version)


if __name__ == "__main__":
    main()
