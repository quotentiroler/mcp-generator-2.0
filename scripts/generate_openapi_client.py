#!/usr/bin/env python3
"""
Generate Python API client from OpenAPI specification using OpenAPI Generator.

This script automates the generation of the Python API client that the MCP server
uses to communicate with the backend API.

Usage:
    python scripts/generate_openapi_client.py [--openapi-spec PATH] [--output-dir PATH]

Requirements:
    - OpenAPI Generator CLI installed (via npm or standalone)
    - OpenAPI specification file (openapi.json)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def setup_utf8_console():
    """Configure UTF-8 encoding for console output (fixes emoji display on Windows)."""
    if sys.platform == 'win32':
        # Set console to UTF-8 mode on Windows
        try:
            os.system('chcp 65001 > nul 2>&1')
        except:
            pass
        # Reconfigure stdout encoding if available
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8') # type: ignore
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8') # type: ignore
        except (AttributeError, OSError):
            pass


def check_openapi_generator():
    """Check if OpenAPI Generator CLI is available."""
    # On Windows, we need to use shell=True or call via cmd
    import platform
    is_windows = platform.system() == "Windows"

    try:
        # Try npx first (from openapitools.json config)
        cmd = ["npx", "@openapitools/openapi-generator-cli", "version"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            shell=is_windows
        )
        if result.returncode == 0:
            print(f"✅ OpenAPI Generator found (via npx): {result.stdout.strip()}")
            return "npx"
    except FileNotFoundError:
        pass

    try:
        # Try standalone openapi-generator-cli
        cmd = ["openapi-generator-cli", "version"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            shell=is_windows
        )
        if result.returncode == 0:
            print(f"✅ OpenAPI Generator found (standalone): {result.stdout.strip()}")
            return "standalone"
    except FileNotFoundError:
        pass

    print("❌ OpenAPI Generator CLI not found!")
    print("\nInstall options:")
    print("  1. Via npm: npm install -g @openapitools/openapi-generator-cli")
    print("  2. Via npm (local): npm install @openapitools/openapi-generator-cli")
    print("  3. Standalone: https://openapi-generator.tech/docs/installation")
    return None


def load_config(config_path: Path) -> dict:
    """Load OpenAPI Generator configuration."""
    if not config_path.exists():
        print(f"⚠️  Config file not found: {config_path}")
        print("Using default configuration")
        return {}

    with open(config_path) as f:
        config = json.load(f)

    print(f"✅ Loaded config from: {config_path}")
    return config


def generate_client(
    openapi_spec: Path,
    output_dir: Path,
    config_path: Path,
    generator_type: str
) -> bool:
    """Generate Python API client using OpenAPI Generator."""

    if not openapi_spec.exists():
        print(f"❌ OpenAPI spec not found: {openapi_spec}")
        return False

    print("\n📋 Input:")
    print(f"   OpenAPI spec: {openapi_spec}")
    print(f"   Output dir:   {output_dir}")
    print(f"   Config:       {config_path}")

    # Build command
    base_cmd = [
        "npx", "@openapitools/openapi-generator-cli", "generate"
    ] if generator_type == "npx" else [
        "openapi-generator-cli", "generate"
    ]

    cmd = base_cmd + [
        "-i", str(openapi_spec),
        "-g", "python",
        "-o", str(output_dir),
    ]

    # Add config if it exists
    if config_path.exists():
        cmd.extend(["-c", str(config_path)])

    # Add additional options (only ones not in config)
    cmd.extend([
        "--skip-validate-spec",  # Skip validation for faster generation
    ])

    print("\n🚀 Running OpenAPI Generator...")
    print(f"   Command: {' '.join(cmd)}")

    # Check if we're on Windows
    import platform
    is_windows = platform.system() == "Windows"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            shell=is_windows  # Use shell on Windows to find npx/commands in PATH
        )

        if result.returncode != 0:
            print("\n❌ Generation failed!")
            print(f"\nSTDERR:\n{result.stderr}")
            print(f"\nSTDOUT:\n{result.stdout}")
            return False

        print("\n✅ Client generated successfully!")

        # Print summary
        if output_dir.exists():
            api_dir = output_dir / "openapi_client"
            if api_dir.exists():
                api_files = list((api_dir / "api").glob("*.py")) if (api_dir / "api").exists() else []
                model_files = list((api_dir / "models").glob("*.py")) if (api_dir / "models").exists() else []

                print("\n📊 Generated:")
                print(f"   APIs:   {len(api_files)} files")
                print(f"   Models: {len(model_files)} files")
                print(f"   Output: {output_dir}")

        return True

    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        return False


def clean_output_dir(output_dir: Path):
    """Clean the output directory before generation."""
    if output_dir.exists():
        print(f"\n🧹 Cleaning existing output directory: {output_dir}")

        # Remove only generated content, keep __pycache__ out of git
        items_to_remove = [
            "openapi_client",
            "docs",
            "test",
            ".openapi-generator",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "test-requirements.txt",
            "tox.ini",
            "git_push.sh",
            ".gitignore",
            ".gitlab-ci.yml",
            ".travis.yml",
            "README.md",
        ]

        for item_name in items_to_remove:
            item_path = output_dir / item_name
            if item_path.exists():
                if item_path.is_file():
                    item_path.unlink()
                elif item_path.is_dir():
                    shutil.rmtree(item_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Python API client from OpenAPI specification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with defaults
  python scripts/generate_openapi_client.py
  
  # Specify custom OpenAPI spec
  python scripts/generate_openapi_client.py --openapi-spec path/to/openapi.json
  
  # Specify custom output directory
  python scripts/generate_openapi_client.py --output-dir my-client
  
  # Don't clean before generating
  python scripts/generate_openapi_client.py --no-clean
        """
    )

    # Use current working directory instead of script location
    # This allows the script to work correctly when called from different directories
    project_dir = Path.cwd()

    # Find OpenAPI spec (check for .json, .yaml, or .yml)
    default_spec = None
    for ext in ['openapi.json', 'openapi.yaml', 'openapi.yml']:
        spec_path = project_dir / ext
        if spec_path.exists():
            default_spec = spec_path
            break

    if not default_spec:
        default_spec = project_dir / "openapi.json"  # Fallback default

    parser.add_argument(
        "--openapi-spec",
        type=Path,
        default=default_spec,
        help="Path to OpenAPI specification file (default: openapi.json/yaml)"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_dir / "generated_openapi",
        help="Output directory for generated client (default: generated_openapi/)"
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=project_dir / "openapi-generator-config.json",
        help="Path to OpenAPI Generator config file"
    )

    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Don't clean output directory before generation"
    )

    args = parser.parse_args()

    # Setup UTF-8 console for emoji support on Windows
    setup_utf8_console()

    print("=" * 70)
    print("🔧 Python API Client Generator")
    print("=" * 70)

    # Check for OpenAPI Generator
    generator_type = check_openapi_generator()
    if not generator_type:
        return 1

    # Load configuration
    config = load_config(args.config)

    # Clean output directory if requested
    if not args.no_clean:
        clean_output_dir(args.output_dir)

    # Generate client
    success = generate_client(
        args.openapi_spec,
        args.output_dir,
        args.config,
        generator_type
    )

    if success:
        print("\n" + "=" * 70)
        print("✅ API Client generation complete!")
        print("=" * 70)
        print("\nNext steps:")
        print(f"  1. Review generated code in: {args.output_dir}")
        print(f"  2. Install the client: pip install -e {args.output_dir}")
        print("  3. Import in code: from openapi_client import ApiClient, Configuration")
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌ API Client generation failed!")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
