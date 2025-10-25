#!/usr/bin/env python3
"""
Test script for MCP Generator examples.

This script:
1. Regenerates all examples
2. Runs their test suites
3. Reports results

Usage:
    python scripts/test_examples.py
    python scripts/test_examples.py --example petstore
    python scripts/test_examples.py --skip-generation
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        # Set console to UTF-8 mode on Windows
        os.system('chcp 65001 > nul 2>&1')
        # Reconfigure stdout/stderr encoding if available (Python 3.7+)
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass  # Not available or failed, continue anyway


# Examples to test (relative to project root)
EXAMPLES = [
    "examples/petstore",
    "examples/minimal",
]


def run_command(cmd: list[str], cwd: Path, description: str) -> tuple[bool, str]:
    """Run a command and return success status and output.

    Args:
        cmd: Command and arguments to run
        cwd: Working directory
        description: Human-readable description of the command

    Returns:
        Tuple of (success: bool, output: str)
    """
    print(f"\n{'='*80}")
    print(f"▶ {description}")
    print(f"  Working directory: {cwd}")
    print(f"  Command: {' '.join(cmd)}")
    print('='*80)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace problematic characters
            timeout=300  # 5 minute timeout
        )

        # Always print output for visibility
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        success = result.returncode == 0

        if success:
            print(f"✅ {description} - SUCCESS")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")

        return success, result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT (exceeded 5 minutes)")
        return False, "Command timed out"
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False, str(e)


def clean_example(example_dir: Path) -> bool:
    """Clean generated files from an example.

    Args:
        example_dir: Path to example directory

    Returns:
        True if cleaning succeeded
    """
    print(f"\n🧹 Cleaning {example_dir.name}...")

    # Directories to remove
    dirs_to_remove = [
        example_dir / "generated_mcp",
        example_dir / "generated_openapi",
        example_dir / "test",
    ]

    for dir_path in dirs_to_remove:
        if dir_path.exists():
            import shutil
            try:
                shutil.rmtree(dir_path)
                print(f"  ✓ Removed {dir_path.relative_to(example_dir)}")
            except Exception as e:
                print(f"  ⚠ Failed to remove {dir_path}: {e}")
                return False

    # Files to remove
    files_to_remove = [
        example_dir / "openapitools.json",
    ]

    for file_path in files_to_remove:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"  ✓ Removed {file_path.relative_to(example_dir)}")
            except Exception as e:
                print(f"  ⚠ Failed to remove {file_path}: {e}")

    print(f"✅ Cleaned {example_dir.name}")
    return True


def regenerate_example(example_dir: Path) -> bool:
    """Regenerate an example's MCP server.

    Args:
        example_dir: Path to example directory

    Returns:
        True if regeneration succeeded
    """
    # Check if openapi spec exists
    openapi_files = list(example_dir.glob("openapi.*"))
    if not openapi_files:
        print(f"⚠ No OpenAPI spec found in {example_dir}")
        return False

    # Step 1: Generate MCP server
    if (example_dir / "openapi.json").exists():
        cmd = ["uv", "run", "generate-mcp"]
    elif (example_dir / "openapi.yaml").exists():
        cmd = ["uv", "run", "generate-mcp"]
    else:
        cmd = ["uv", "run", "generate-mcp"]

    success, _ = run_command(
        cmd,
        example_dir,
        f"Generating MCP server for {example_dir.name}"
    )

    if not success:
        return False

    # Step 2: Register MCP server
    # Note: register-mcp writes to user config files, skip in CI
    # success, _ = run_command(
    #     ["uv", "run", "register-mcp"],
    #     example_dir / "generated_mcp",
    #     f"Registering MCP server for {example_dir.name}"
    # )

    return success


def run_example_tests(example_dir: Path) -> bool:
    """Run an example's test suite.

    Args:
        example_dir: Path to example directory

    Returns:
        True if tests passed
    """
    test_runner = example_dir / "test" / "run_tests.py"

    if not test_runner.exists():
        print(f"⚠ No test runner found at {test_runner}")
        return False

    success, _ = run_command(
        ["uv", "run", "python", str(test_runner)],
        example_dir,
        f"Running tests for {example_dir.name}"
    )

    return success


def test_example(example_path: str, skip_generation: bool = False) -> bool:
    """Test a single example.

    Args:
        example_path: Relative path to example directory
        skip_generation: If True, skip regeneration step

    Returns:
        True if all steps succeeded
    """
    project_root = Path(__file__).parent.parent
    example_dir = project_root / example_path

    if not example_dir.exists():
        print(f"❌ Example directory not found: {example_dir}")
        return False

    print(f"\n{'#'*80}")
    print(f"# Testing Example: {example_dir.name}")
    print(f"{'#'*80}")

    # Step 1: Clean
    if not skip_generation:
        if not clean_example(example_dir):
            print(f"❌ Failed to clean {example_dir.name}")
            return False

    # Step 2: Regenerate
    if not skip_generation:
        if not regenerate_example(example_dir):
            print(f"❌ Failed to regenerate {example_dir.name}")
            return False
    else:
        print(f"\n⏭️  Skipping regeneration for {example_dir.name}")

    # Step 3: Run tests
    if not run_example_tests(example_dir):
        print(f"❌ Tests failed for {example_dir.name}")
        return False

    print(f"\n✅ All steps completed successfully for {example_dir.name}")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test MCP Generator examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all examples
  python scripts/test_examples.py

  # Test specific example
  python scripts/test_examples.py --example petstore

  # Skip regeneration (just run tests)
  python scripts/test_examples.py --skip-generation
        """
    )

    parser.add_argument(
        "--example",
        help="Test only specific example (e.g., 'petstore', 'minimal')",
        type=str
    )

    parser.add_argument(
        "--skip-generation",
        help="Skip cleaning and regeneration, just run tests",
        action="store_true"
    )

    args = parser.parse_args()

    # Determine which examples to test
    if args.example:
        # Find matching example
        examples_to_test = [e for e in EXAMPLES if args.example in e]
        if not examples_to_test:
            print(f"❌ No example found matching '{args.example}'")
            print("\nAvailable examples:")
            for ex in EXAMPLES:
                print(f"  - {Path(ex).name}")
            return 1
    else:
        examples_to_test = EXAMPLES

    print(f"""
+==============================================================================+
|                    MCP Generator - Example Test Suite                      |
+==============================================================================+

Testing {len(examples_to_test)} example(s):
""")
    for ex in examples_to_test:
        print(f"  • {Path(ex).name}")

    if args.skip_generation:
        print("\n⚠️  Skipping regeneration (--skip-generation)")

    # Test each example
    results = {}
    for example_path in examples_to_test:
        example_name = Path(example_path).name
        results[example_name] = test_example(example_path, args.skip_generation)

    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print('='*80)

    passed = sum(1 for success in results.values() if success)
    failed = len(results) - passed

    for example_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {example_name:20s} {status}")

    print(f"\nTotal: {passed}/{len(results)} passed")

    if failed > 0:
        print(f"\n❌ {failed} example(s) failed")
        return 1
    else:
        print("\n✅ All examples passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
