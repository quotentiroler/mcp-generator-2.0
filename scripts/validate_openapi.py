#!/usr/bin/env python3
"""
Validate OpenAPI specification for MCP generator compatibility.

This script checks if an OpenAPI spec file is compatible with the MCP generator,
verifying structure, required fields, security schemes, and API operations.

Usage:
    python scripts/validate_openapi.py [--spec PATH] [--strict]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []
        self.stats: dict[str, Any] = {}

    def add_error(self, message: str):
        """Add a validation error (blocks generation)."""
        self.errors.append(message)

    def add_warning(self, message: str):
        """Add a validation warning (generation may work but with issues)."""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Add informational message."""
        self.info.append(message)

    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)

        if self.stats:
            print("\n📈 Statistics:")
            for key, value in self.stats.items():
                print(f"   {key}: {value}")

        if self.info:
            print(f"\n💡 Information ({len(self.info)}):")
            for msg in self.info:
                print(f"   ℹ️  {msg}")

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for msg in self.warnings:
                print(f"   ⚠️  {msg}")

        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for msg in self.errors:
                print(f"   ❌ {msg}")
            print("\n" + "=" * 70)
            print("❌ VALIDATION FAILED")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("✅ VALIDATION PASSED")
            print("=" * 70)


def load_openapi_spec(spec_path: Path) -> dict[str, Any] | None:
    """Load and parse OpenAPI specification."""
    if not spec_path.exists():
        print(f"❌ File not found: {spec_path}")
        return None

    try:
        with open(spec_path, encoding='utf-8') as f:
            spec = json.load(f)
        print(f"✅ Loaded OpenAPI spec: {spec_path}")
        return spec
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None


def validate_basic_structure(spec: dict[str, Any], result: ValidationResult):
    """Validate basic OpenAPI structure."""
    print("\n🔍 Validating basic structure...")

    # Check OpenAPI version
    if 'openapi' not in spec:
        result.add_error("Missing 'openapi' field (required)")
    else:
        version = spec['openapi']
        result.add_info(f"OpenAPI version: {version}")
        if not version.startswith('3.'):
            result.add_warning(f"OpenAPI version {version} may not be fully supported (recommend 3.0.x or 3.1.x)")

    # Check info section
    if 'info' not in spec:
        result.add_error("Missing 'info' section (required)")
    else:
        info = spec['info']
        if 'title' not in info:
            result.add_error("Missing 'info.title' (required)")
        else:
            result.add_info(f"API Title: {info['title']}")

        if 'version' not in info:
            result.add_warning("Missing 'info.version' (recommended)")
        else:
            result.add_info(f"API Version: {info['version']}")

        if 'description' in info:
            result.add_info(f"Has description: {len(info['description'])} chars")

    # Check paths
    if 'paths' not in spec:
        result.add_error("Missing 'paths' section (required)")
    elif not spec['paths']:
        result.add_error("Empty 'paths' section (need at least one endpoint)")


def validate_servers(spec: dict[str, Any], result: ValidationResult):
    """Validate server configuration."""
    print("\n🌐 Validating servers...")

    if 'servers' not in spec or not spec['servers']:
        result.add_warning("No servers defined - backend URL will need to be provided")
        return

    servers = spec['servers']
    result.stats['servers'] = len(servers)

    for i, server in enumerate(servers):
        if 'url' not in server:
            result.add_error(f"Server {i}: missing 'url' field")
        else:
            url = server['url']
            result.add_info(f"Server {i}: {url}")

            # Check if URL looks valid
            if not (url.startswith('http://') or url.startswith('https://') or url.startswith('/')):
                result.add_warning(f"Server {i}: URL may be invalid: {url}")


def validate_security_schemes(spec: dict[str, Any], result: ValidationResult) -> set[str]:
    """Validate security schemes configuration."""
    print("\n🔐 Validating security schemes...")

    security_schemes = {}
    if 'components' in spec and 'securitySchemes' in spec['components']:
        security_schemes = spec['components']['securitySchemes']

    if not security_schemes:
        result.add_warning("No security schemes defined - authentication may not work")
        return set()

    result.stats['security_schemes'] = len(security_schemes)
    scheme_names = set()

    for scheme_name, scheme in security_schemes.items():
        scheme_names.add(scheme_name)
        scheme_type = scheme.get('type', 'unknown')
        result.add_info(f"Security scheme '{scheme_name}': {scheme_type}")

        if scheme_type == 'oauth2':
            if 'flows' not in scheme:
                result.add_error(f"OAuth2 scheme '{scheme_name}': missing 'flows'")
            else:
                flows = scheme['flows']
                result.add_info(f"  OAuth2 flows: {', '.join(flows.keys())}")

                # Check for authorization/token URLs
                for flow_name, flow in flows.items():
                    if flow_name in ['authorizationCode', 'implicit'] and 'authorizationUrl' not in flow:
                        result.add_error(f"  Flow '{flow_name}': missing 'authorizationUrl'")
                    if flow_name in ['authorizationCode', 'password', 'clientCredentials'] and 'tokenUrl' not in flow:
                        result.add_error(f"  Flow '{flow_name}': missing 'tokenUrl'")

                    # Check scopes
                    if 'scopes' in flow:
                        result.add_info(f"  Flow '{flow_name}': {len(flow['scopes'])} scopes defined")

        elif scheme_type == 'http':
            scheme_subtype = scheme.get('scheme', 'unknown')
            result.add_info(f"  HTTP scheme: {scheme_subtype}")
            if scheme_subtype == 'bearer':
                if 'bearerFormat' in scheme:
                    result.add_info(f"  Bearer format: {scheme['bearerFormat']}")

        elif scheme_type == 'apiKey':
            if 'name' not in scheme:
                result.add_error(f"API Key scheme '{scheme_name}': missing 'name'")
            if 'in' not in scheme:
                result.add_error(f"API Key scheme '{scheme_name}': missing 'in'")

    return scheme_names


def validate_paths_and_operations(spec: dict[str, Any], result: ValidationResult, valid_security: set[str]):
    """Validate API paths and operations."""
    print("\n🛣️  Validating paths and operations...")

    if 'paths' not in spec:
        return

    paths = spec['paths']
    result.stats['paths'] = len(paths)

    total_operations = 0
    operations_by_tag: dict[str, int] = {}
    operations_by_method: dict[str, int] = {}

    http_methods = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    for path, path_item in paths.items():
        for method in http_methods:
            if method not in path_item:
                continue

            operation = path_item[method]
            total_operations += 1
            operations_by_method[method.upper()] = operations_by_method.get(method.upper(), 0) + 1

            # Check operationId (important for tool naming)
            if 'operationId' not in operation:
                result.add_warning(f"{method.upper()} {path}: missing 'operationId' (recommended for better tool names)")

            # Check tags (used for module organization)
            if 'tags' in operation and operation['tags']:
                for tag in operation['tags']:
                    operations_by_tag[tag] = operations_by_tag.get(tag, 0) + 1
            else:
                result.add_warning(f"{method.upper()} {path}: no tags (will be in 'default' module)")

            # Check responses
            if 'responses' not in operation or not operation['responses']:
                result.add_warning(f"{method.upper()} {path}: no responses defined")

            # Check security (if global security is defined)
            if 'security' in operation:
                for security_req in operation['security']:
                    for scheme_name in security_req.keys():
                        if scheme_name not in valid_security:
                            result.add_error(f"{method.upper()} {path}: references unknown security scheme '{scheme_name}'")

    result.stats['operations'] = total_operations
    result.stats['operations_by_method'] = operations_by_method
    result.stats['operations_by_tag'] = len(operations_by_tag)

    if total_operations == 0:
        result.add_error("No operations found - need at least one HTTP operation")
    else:
        result.add_info(f"Found {total_operations} operations")
        result.add_info(f"Operations by method: {operations_by_method}")
        result.add_info(f"Tagged modules: {len(operations_by_tag)}")


def validate_schemas(spec: dict[str, Any], result: ValidationResult):
    """Validate schema definitions."""
    print("\n📦 Validating schemas...")

    schemas = {}
    if 'components' in spec and 'schemas' in spec['components']:
        schemas = spec['components']['schemas']

    if not schemas:
        result.add_warning("No schemas defined in components - may have issues with request/response types")
        return

    result.stats['schemas'] = len(schemas)
    result.add_info(f"Found {len(schemas)} schema definitions")

    # Count schemas by type
    schema_types: dict[str, int] = {}
    for schema_name, schema in schemas.items():
        schema_type = schema.get('type', 'object')
        schema_types[schema_type] = schema_types.get(schema_type, 0) + 1

    result.add_info(f"Schema types: {schema_types}")


def validate_for_generator(spec: dict[str, Any], result: ValidationResult, strict: bool = False):
    """Validate specific requirements for MCP generator."""
    print("\n🔧 Validating MCP generator compatibility...")

    # Check if we can extract backend URL
    backend_url = None
    if 'servers' in spec and spec['servers']:
        backend_url = spec['servers'][0].get('url')

    if not backend_url:
        if strict:
            result.add_error("Cannot determine backend URL - no servers defined")
        else:
            result.add_warning("Cannot determine backend URL - will use default")
    else:
        result.add_info(f"Backend URL will be: {backend_url}")

    # Check for operations (will become tools)
    if 'paths' in spec:
        has_operations = any(
            any(method in path_item for method in ['get', 'post', 'put', 'patch', 'delete'])
            for path_item in spec['paths'].values()
        )
        if not has_operations:
            result.add_error("No HTTP operations found - cannot generate tools")

    # Check if we can extract JWT config (if OAuth2 is used)
    if 'components' in spec and 'securitySchemes' in spec['components']:
        oauth_schemes = [
            scheme for scheme in spec['components']['securitySchemes'].values()
            if scheme.get('type') == 'oauth2'
        ]
        if oauth_schemes:
            result.add_info("OAuth2 detected - JWT configuration will be extracted")

            # Check for OIDC discovery URL
            has_oidc = any(
                'openIdConnectUrl' in scheme
                for scheme in spec['components']['securitySchemes'].values()
                if scheme.get('type') == 'openIdConnect'
            )
            if has_oidc:
                result.add_info("OpenID Connect detected - JWKS discovery available")


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(
        description="Validate OpenAPI specification for MCP generator compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate default openapi.json
  python scripts/validate_openapi.py
  
  # Validate specific file
  python scripts/validate_openapi.py --spec path/to/openapi.json
  
  # Strict validation (treat warnings as errors)
  python scripts/validate_openapi.py --strict
        """
    )

    script_dir = Path(__file__).parent
    project_dir = script_dir.parent

    parser.add_argument(
        "--spec",
        type=Path,
        default=project_dir / "openapi.json",
        help="Path to OpenAPI specification file (default: openapi.json)"
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (stricter validation)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🔍 OpenAPI Specification Validator")
    print("=" * 70)
    print(f"\nValidating: {args.spec}")
    if args.strict:
        print("Mode: STRICT (warnings treated as errors)")

    # Load spec
    spec = load_openapi_spec(args.spec)
    if spec is None:
        return 1

    # Run validations
    result = ValidationResult()

    validate_basic_structure(spec, result)
    validate_servers(spec, result)
    valid_security = validate_security_schemes(spec, result)
    validate_paths_and_operations(spec, result, valid_security)
    validate_schemas(spec, result)
    validate_for_generator(spec, result, strict=args.strict)

    # Print summary
    result.print_summary()

    # Determine exit code
    if not result.is_valid():
        return 1
    elif args.strict and result.warnings:
        print("\n⚠️  STRICT MODE: Validation failed due to warnings")
        return 1
    else:
        print("\n✅ OpenAPI spec is compatible with MCP generator")
        return 0


if __name__ == "__main__":
    sys.exit(main())
