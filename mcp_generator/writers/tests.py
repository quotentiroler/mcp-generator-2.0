"""Writes the generated test suite and its runner."""

from pathlib import Path


def write_test_files(
    auth_test_code: str | None,
    tool_test_code: str,
    openapi_feature_test_code: str | None,
    http_basic_test_code: str | None,
    performance_test_code: str | None,
    cache_test_code: str | None,
    oauth_persistence_test_code: str | None,
    test_dir: Path,
    resource_test_code: str | None = None,
    transform_test_code: str | None = None,
    multi_auth_test_code: str | None = None,
    server_integration_test_code: str | None = None,
    tool_schema_test_code: str | None = None,
    behavioral_test_code: str | None = None,
    tool_call_test_code: str | None = None,
) -> None:
    """
    Write generated test files to the filesystem.

    Args:
        auth_test_code: Generated authentication flow test code (None if no auth)
        tool_test_code: Generated tool validation test code
        openapi_feature_test_code: Generated OpenAPI feature tests
        http_basic_test_code: Generated HTTP basic E2E tests
        performance_test_code: Generated performance tests
        cache_test_code: Generated cache middleware tests (None if caching not enabled)
        oauth_persistence_test_code: Generated OAuth persistence tests (None if storage not enabled with auth)
        test_dir: Directory to write test files to
        resource_test_code: Generated resource template tests (None if resources not enabled)
        transform_test_code: Generated transform tests (FastMCP 3.1 features)
        multi_auth_test_code: Generated multi-auth tests (FastMCP 3.1 features, None if no auth)
        server_integration_test_code: Generated in-process integration tests
        tool_schema_test_code: Generated tool schema validation tests
        behavioral_test_code: Generated behavioural edge-case tests (expected to fail initially)
        tool_call_test_code: Generated tools/call E2E tests (requires running server)
    """
    test_dir.mkdir(parents=True, exist_ok=True)

    # Write auth flow tests (only if auth is configured)
    if auth_test_code:
        auth_test_file = test_dir / "test_auth_flows_generated.py"
        with open(auth_test_file, "w", encoding="utf-8") as f:
            f.write(auth_test_code)
        print("   ✅ test_auth_flows_generated.py")

    # Write tool tests
    tool_test_file = test_dir / "test_tools_generated.py"
    with open(tool_test_file, "w", encoding="utf-8") as f:
        f.write(tool_test_code)
    print("   ✅ test_tools_generated.py")

    # Write OpenAPI feature tests
    if openapi_feature_test_code:
        feature_test_file = test_dir / "test_e2e_openapi_features_generated.py"
        with open(feature_test_file, "w", encoding="utf-8") as f:
            f.write(openapi_feature_test_code)
        print("   ✅ test_e2e_openapi_features_generated.py")

    # Write HTTP basic E2E tests
    if http_basic_test_code:
        http_basic_file = test_dir / "test_e2e_http_basic_generated.py"
        with open(http_basic_file, "w", encoding="utf-8") as f:
            f.write(http_basic_test_code)
        print("   ✅ test_e2e_http_basic_generated.py")

    # Write performance tests
    if performance_test_code:
        performance_file = test_dir / "test_e2e_performance_generated.py"
        with open(performance_file, "w", encoding="utf-8") as f:
            f.write(performance_test_code)
        print("   ✅ test_e2e_performance_generated.py")

    # Write cache tests
    if cache_test_code:
        cache_file = test_dir / "test_cache_generated.py"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(cache_test_code)
        print("   ✅ test_cache_generated.py")

    # Write OAuth persistence tests
    if oauth_persistence_test_code:
        oauth_file = test_dir / "test_oauth_persistence_generated.py"
        with open(oauth_file, "w", encoding="utf-8") as f:
            f.write(oauth_persistence_test_code)
        print("   ✅ test_oauth_persistence_generated.py")

    # Write resource tests
    if resource_test_code:
        resource_file = test_dir / "test_resources_generated.py"
        with open(resource_file, "w", encoding="utf-8") as f:
            f.write(resource_test_code)
        print("   ✅ test_resources_generated.py")

    # Write transform tests (FastMCP 3.1)
    if transform_test_code:
        transform_file = test_dir / "test_transforms_generated.py"
        with open(transform_file, "w", encoding="utf-8") as f:
            f.write(transform_test_code)
        print("   ✅ test_transforms_generated.py")

    # Write multi-auth tests (FastMCP 3.1)
    if multi_auth_test_code:
        multi_auth_file = test_dir / "test_multi_auth_generated.py"
        with open(multi_auth_file, "w", encoding="utf-8") as f:
            f.write(multi_auth_test_code)
        print("   ✅ test_multi_auth_generated.py")

    # Write server integration tests (in-process, no HTTP needed)
    if server_integration_test_code:
        integration_file = test_dir / "test_server_integration_generated.py"
        with open(integration_file, "w", encoding="utf-8") as f:
            f.write(server_integration_test_code)
        print("   ✅ test_server_integration_generated.py")

    # Write tool schema validation tests
    if tool_schema_test_code:
        schema_file = test_dir / "test_tool_schemas_generated.py"
        with open(schema_file, "w", encoding="utf-8") as f:
            f.write(tool_schema_test_code)
        print("   ✅ test_tool_schemas_generated.py")

    # Write behavioral edge-case tests
    if behavioral_test_code:
        behavioral_file = test_dir / "test_behavioral_generated.py"
        with open(behavioral_file, "w", encoding="utf-8") as f:
            f.write(behavioral_test_code)
        print("   ✅ test_behavioral_generated.py")

    # Write tool call E2E tests (requires running server)
    if tool_call_test_code:
        tool_call_file = test_dir / "test_tool_calls_generated.py"
        with open(tool_call_file, "w", encoding="utf-8") as f:
            f.write(tool_call_test_code)
        print("   ✅ test_tool_calls_generated.py")


def write_test_runner(test_runner_code: str, output_file: Path) -> None:
    """
    Write test runner script to filesystem.

    Args:
        test_runner_code: Generated test runner script code
        output_file: Path to write the test runner script
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(test_runner_code)

    # Make executable on Unix-like systems
    import stat

    current_permissions = output_file.stat().st_mode
    output_file.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"   ✅ {output_file.name}")
