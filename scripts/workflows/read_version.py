#!/usr/bin/env python3
"""Print the version from pyproject.toml.

Workflows need the current version in a shell variable. Each one used to inline
its own copy of the same regex inside a heredoc, where the nested quoting is
easy to break. This wraps the parser that already exists in
update_version_metadata.py so there is one implementation.

Usage:
    python scripts/workflows/read_version.py            # 3.2.6-beta
    python scripts/workflows/read_version.py --base     # 3.2.6-beta  (no +sha)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from update_version_metadata import get_version_from_pyproject  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        action="store_true",
        help="Strip the +commit build metadata (3.2.6-beta+a1b2c3d -> 3.2.6-beta)",
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=Path(__file__).parent.parent.parent / "pyproject.toml",
        help="Path to pyproject.toml",
    )
    args = parser.parse_args()

    version = get_version_from_pyproject(args.pyproject)
    print(version.split("+")[0] if args.base else version)


if __name__ == "__main__":
    main()
