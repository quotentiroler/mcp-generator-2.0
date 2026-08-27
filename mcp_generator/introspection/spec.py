"""Locates, loads and tag-enriches the OpenAPI specification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def enrich_spec_tags(spec: dict[str, Any]) -> list[str]:
    """
    Auto-discover tags from endpoint definitions and add undeclared ones to the
    top-level ``tags`` array.

    The OpenAPI specification allows endpoints to reference tags that are not
    declared in the top-level ``tags`` list.  Some frameworks (e.g. Elysia)
    silently drop tags from the top-level list even though they are used on
    operations.  The openapi-generator-cli and downstream tooling may rely on
    declared tags to generate API classes, so we must ensure every tag in use is
    declared.

    Args:
        spec: Parsed OpenAPI specification (modified **in-place**).

    Returns:
        List of tag names that were auto-discovered and added.
    """
    declared_tags: set[str] = {t["name"] for t in spec.get("tags", [])}

    # Scan all operations for tags that are used but not declared
    discovered: list[str] = []
    for _path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "put", "post", "delete", "patch", "options", "head", "trace"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            for tag in operation.get("tags", []):
                if tag not in declared_tags:
                    spec.setdefault("tags", []).append(
                        {"name": tag, "description": "Auto-discovered from endpoint definitions"}
                    )
                    declared_tags.add(tag)
                    discovered.append(tag)

    return discovered


def _load_openapi_spec(spec_path: Path) -> dict[str, Any] | None:
    """
    Load OpenAPI specification from either JSON or YAML format.

    Args:
        spec_path: Path to the OpenAPI specification file

    Returns:
        Parsed OpenAPI spec as a dictionary, or None if loading fails
    """
    if not spec_path.exists():
        return None

    try:
        # Try loading as JSON first
        with open(spec_path, encoding="utf-8") as f:
            return dict(json.load(f))
    except json.JSONDecodeError:
        # If JSON fails, try YAML
        try:
            import yaml

            with open(spec_path, encoding="utf-8") as f:
                return dict(yaml.safe_load(f))
        except ImportError:
            print("   ⚠️  Could not load YAML file (PyYAML not installed)")
            print("   💡 Install with: pip install pyyaml")
            return None
        except Exception as e:
            print(f"   ⚠️  Could not parse OpenAPI spec as YAML: {e}")
            return None
    except Exception as e:
        print(f"   ⚠️  Could not load OpenAPI spec: {e}")
        return None


def _find_openapi_spec(base_dir: Path | None = None) -> Path | None:
    """Find the OpenAPI specification file (supports both .json and .yaml extensions).

    Args:
        base_dir: Base directory to search for openapi files. Defaults to current working directory.
    """
    if base_dir is None:
        base_dir = Path.cwd()

    # Try openapi.json first (most common)
    json_path = base_dir / "openapi.json"
    if json_path.exists():
        return json_path

    # Try openapi.yaml
    yaml_path = base_dir / "openapi.yaml"
    if yaml_path.exists():
        return yaml_path

    # Try openapi.yml
    yml_path = base_dir / "openapi.yml"
    if yml_path.exists():
        return yml_path

    return None
