"""TDD bug-fix tests — each test targets a verified bug in the codebase.

Written RED-first: these tests expose real bugs that need fixing.
Each class documents the bug, the root cause, and the expected behavior.
"""

import pytest

from mcp_generator.models import ApiMetadata, ModuleSpec, SecurityConfig

# ---------------------------------------------------------------------------
# Bug #2: OpenAPI 3.1 nullable type arrays crash schema parsing
#
# Root cause: _OPENAPI_TYPE_MAP.get(prop_type) where prop_type can be a list
# like ["string", "null"] in OpenAPI 3.1 — raises TypeError: unhashable type
# ---------------------------------------------------------------------------


class TestOpenAPI31NullableTypes:
    """OpenAPI 3.1 uses type: ["string", "null"] for nullable fields."""

    def test_nullable_string_does_not_crash(self) -> None:
        """_parse_schema_fields should handle list-typed properties."""
        from mcp_generator.introspection import _parse_schema_fields

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"], "description": "optional name"},
            },
        }
        # Should not raise TypeError: unhashable type: 'list'
        fields = _parse_schema_fields(schema, {})
        assert len(fields) == 1
        assert fields[0].name == "name"
        assert fields[0].python_type == "str"

    def test_nullable_integer_maps_correctly(self) -> None:
        from mcp_generator.introspection import _parse_schema_fields

        schema = {
            "type": "object",
            "properties": {
                "count": {"type": ["integer", "null"]},
            },
        }
        fields = _parse_schema_fields(schema, {})
        assert fields[0].python_type == "int"

    def test_nullable_boolean_maps_correctly(self) -> None:
        from mcp_generator.introspection import _parse_schema_fields

        schema = {
            "type": "object",
            "properties": {
                "active": {"type": ["boolean", "null"]},
            },
        }
        fields = _parse_schema_fields(schema, {})
        assert fields[0].python_type == "bool"


# ---------------------------------------------------------------------------
# Bug #3: Path-level parameters are ignored for resource endpoints
#
# Root cause: get_resource_endpoints only reads operation-level parameters,
# not path-level parameters defined on the path item object.
# ---------------------------------------------------------------------------


class TestPathLevelParameters:
    """OpenAPI allows parameters at the path item level, shared by all operations."""

    def test_path_level_params_are_included(self, write_spec) -> None:
        from mcp_generator.introspection import get_resource_endpoints

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/pets/{petId}": {
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "get": {
                        "operationId": "getPetById",
                        "tags": ["pet"],
                        "summary": "Get pet by ID",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }
        resources = get_resource_endpoints(write_spec(spec))
        assert "pet" in resources
        pet_resources = resources["pet"]
        assert len(pet_resources) == 1
        assert "petId" in pet_resources[0]["path_params"]

    def test_path_level_query_params_are_included(self, write_spec) -> None:
        from mcp_generator.introspection import get_resource_endpoints

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/items": {
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                            "description": "Max items",
                        }
                    ],
                    "get": {
                        "operationId": "listItems",
                        "tags": ["item"],
                        "summary": "List items",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }
        resources = get_resource_endpoints(write_spec(spec))
        assert "item" in resources
        query_names = [qp["name"] for qp in resources["item"][0]["query_params"]]
        assert "limit" in query_names


# ---------------------------------------------------------------------------
# Bug #4: $ref parameters produce None in generated function signatures
#
# Root cause: If parameter is {"$ref": "..."}, param.get("name") is None
# and this None gets appended to path_params or silently ignored.
# ---------------------------------------------------------------------------


class TestRefParameterHandling:
    """$ref parameters should be resolved before extraction."""

    def test_ref_parameter_is_resolved(self, write_spec) -> None:
        from mcp_generator.introspection import get_resource_endpoints

        spec = {
            "openapi": "3.0.3",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/pets/{petId}": {
                    "get": {
                        "operationId": "getPetById",
                        "tags": ["pet"],
                        "summary": "Get pet by ID",
                        "parameters": [{"$ref": "#/components/parameters/PetId"}],
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
            "components": {
                "parameters": {
                    "PetId": {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                }
            },
        }
        resources = get_resource_endpoints(write_spec(spec))
        assert "pet" in resources
        # The resolved parameter name should appear, not None
        assert "petId" in resources["pet"][0]["path_params"]
        assert None not in resources["pet"][0]["path_params"]


# ---------------------------------------------------------------------------
# Bug #5: Swagger 2.0 security definitions are not parsed
#
# Root cause: get_security_config only reads components.securitySchemes
# (OpenAPI 3.x), not securityDefinitions (Swagger 2.0).
# ---------------------------------------------------------------------------


class TestSwagger20SecurityParsing:
    """Swagger 2.0 uses securityDefinitions instead of components.securitySchemes."""

    def test_swagger2_bearer_auth_detected(self, write_spec) -> None:
        from mcp_generator.introspection import get_security_config

        spec = {
            "swagger": "2.0",
            "info": {"title": "Legacy API", "version": "1.0"},
            "host": "api.example.com",
            "basePath": "/v1",
            "securityDefinitions": {
                "Bearer": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                }
            },
            "security": [{"Bearer": []}],
            "paths": {},
        }
        config = get_security_config(write_spec(spec))
        assert config.schemes, "Swagger 2.0 securityDefinitions should be detected"

    def test_swagger2_oauth2_detected(self, write_spec) -> None:
        from mcp_generator.introspection import get_security_config

        spec = {
            "swagger": "2.0",
            "info": {"title": "OAuth API", "version": "1.0"},
            "host": "api.example.com",
            "securityDefinitions": {
                "oauth2": {
                    "type": "oauth2",
                    "flow": "accessCode",
                    "authorizationUrl": "https://auth.example.com/authorize",
                    "tokenUrl": "https://auth.example.com/token",
                    "scopes": {"read": "Read access"},
                }
            },
            "paths": {},
        }
        config = get_security_config(write_spec(spec))
        assert config.schemes, "Swagger 2.0 OAuth2 should be detected"


# ---------------------------------------------------------------------------
# Bug #8: Required-parameter check treats falsy values as missing
#
# Root cause: `_missing = [p for p in _required if not _locals.get(p)]`
# uses truthiness instead of `is None` check.
# Values like 0, False, "" are valid but treated as missing.
# ---------------------------------------------------------------------------


class TestFalsyRequiredParameters:
    """Generated tool code must not treat 0, False, or '' as missing."""

    def test_missing_check_uses_is_none(self) -> None:
        """The generated missing-parameter check should use `is None`, not truthiness."""
        from mcp_generator.models import ParameterInfo, ToolSpec
        from mcp_generator.renderers import _render_tool

        spec = ToolSpec(
            tool_name="test_tool",
            method_name="test_method",
            api_var_name="test_api",
            docstring="Test docstring",
            parameters=[
                ParameterInfo(
                    name="count",
                    type_hint="int",
                    required=True,
                    description="A count",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                ),
            ],
        )
        code = _render_tool(spec)
        # The missing check should use `is None` not truthiness
        # `not _locals.get(p)` treats 0, False, "" as missing
        assert "_locals.get(p) is None" in code, (
            "Required-parameter missing check should use 'is None', not truthiness. "
            f"Found: {[line.strip() for line in code.splitlines() if '_missing' in line]}"
        )


# ---------------------------------------------------------------------------
# Bug #9: Resource parameter names with special chars break generated Python
#
# Root cause: render_resource uses param names directly in function args
# without sanitizing. Names like "sort-by" or "x.filter" cause SyntaxError.
# ---------------------------------------------------------------------------


class TestResourceParameterSanitization:
    """Parameter names with dashes/dots must be sanitized to valid Python identifiers."""

    def test_dash_in_param_name_produces_valid_python(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="items",
            uri_template="items:///items{?sort-by}",
            method_name="list_items",
            api_var_name="item_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="sort-by",
                    type_hint="str",
                    required=False,
                    description="Sort field",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List items",
            mime_type="application/json",
        )
        code = render_resource(spec)
        # The generated code must be valid Python
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated resource code has SyntaxError: {e}\n\nCode:\n{code}")

    def test_dot_in_param_name_produces_valid_python(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="data",
            uri_template="data:///data{?x.filter}",
            method_name="list_data",
            api_var_name="data_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="x.filter",
                    type_hint="str",
                    required=False,
                    description="Filter",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List data",
            mime_type="application/json",
        )
        code = render_resource(spec)
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated resource code has SyntaxError: {e}\n\nCode:\n{code}")

    def test_dash_in_path_param_produces_valid_python(self) -> None:
        from mcp_generator.models import ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="orgs",
            uri_template="orgs:///orgs/{org-id}/members",
            method_name="get_org_members",
            api_var_name="org_api",
            path_params=["org-id"],
            query_params=[],
            description="Get org members",
            mime_type="application/json",
        )
        code = render_resource(spec)
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated resource code has SyntaxError: {e}\n\nCode:\n{code}")


# ---------------------------------------------------------------------------
# Bug #10: Resource query param defaults use wrong type
#
# Root cause: `default_val = "None" if "str" in qparam.type_hint else "0"`
# Boolean and list params get default 0 instead of None.
# ---------------------------------------------------------------------------


class TestResourceQueryParamDefaults:
    """All optional query params should default to None, not 0."""

    def test_bool_param_defaults_to_none(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="items",
            uri_template="items:///items{?active}",
            method_name="list_items",
            api_var_name="item_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="active",
                    type_hint="bool",
                    required=False,
                    description="Active filter",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List items",
            mime_type="application/json",
        )
        code = render_resource(spec)
        # Bool params should default to None, not 0
        assert "active: bool | None = None" in code, (
            f"Bool query param should default to None, not 0.\nGenerated:\n{code}"
        )
        assert "active: bool | None = 0" not in code

    def test_int_param_defaults_to_none(self) -> None:
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="items",
            uri_template="items:///items{?limit}",
            method_name="list_items",
            api_var_name="item_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="limit",
                    type_hint="int",
                    required=False,
                    description="Limit results",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List items",
            mime_type="application/json",
        )
        code = render_resource(spec)
        assert "limit: int | None = None" in code, (
            f"Int query param should default to None, not 0.\nGenerated:\n{code}"
        )


# ---------------------------------------------------------------------------
# Bug #11: Unescaped API metadata strings can break generated Python
#
# Root cause: Title/description are interpolated into string literals
# without escaping quotes. E.g. title='Joe\'s API' breaks the f-string.
# ---------------------------------------------------------------------------


class TestMetadataStringEscaping:
    """API titles/descriptions with quotes must not break generated code."""

    def test_title_with_double_quote(self) -> None:
        from mcp_generator.generator import generate_main_composition_server

        meta = ApiMetadata(
            title='My "Cool" API',
            version="1.0.0",
            description="A test API",
            servers=[{"url": "http://localhost:3001"}],
        )
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=1,
                code="",
            ),
        }
        code = generate_main_composition_server(modules, meta, SecurityConfig())
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated server code has SyntaxError with quoted title: {e}")

    def test_description_with_triple_quotes(self) -> None:
        from mcp_generator.generator import generate_main_composition_server

        meta = ApiMetadata(
            title="Test API",
            version="1.0.0",
            description='A description with """triple quotes""" inside',
            servers=[{"url": "http://localhost:3001"}],
        )
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=1,
                code="",
            ),
        }
        code = generate_main_composition_server(modules, meta, SecurityConfig())
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(
                f"Generated server code has SyntaxError with triple-quoted description: {e}"
            )

    def test_title_with_backslash(self) -> None:
        from mcp_generator.generator import generate_main_composition_server

        meta = ApiMetadata(
            title="My API\\v2",
            version="1.0.0",
            servers=[{"url": "http://localhost:3001"}],
        )
        modules = {
            "pet": ModuleSpec(
                filename="pet_server.py",
                api_var_name="pet_api",
                api_class_name="PetApi",
                module_name="pet",
                tool_count=1,
                code="",
            ),
        }
        code = generate_main_composition_server(modules, meta, SecurityConfig())
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated server code has SyntaxError with backslash in title: {e}")


# ===========================================================================
# Round 2 — Additional TDD bug discoveries
# ===========================================================================


# ---------------------------------------------------------------------------
# Bug #12: get_display_endpoints ignores path-level and $ref parameters
#
# Root cause: Same pattern as Bug #3/#4 — only reads get_op.get("parameters")
# but not path_item.get("parameters"). Also doesn't resolve $ref params.
# ---------------------------------------------------------------------------


class TestDisplayEndpointPathParams:
    """get_display_endpoints must merge path-level and $ref params."""

    def test_path_level_params_included_in_display(self, write_spec) -> None:
        """Path-level parameters must appear in display endpoint params."""
        from mcp_generator.introspection import get_display_endpoints

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/items/{itemId}": {
                    "parameters": [
                        {
                            "name": "itemId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "get": {
                        "operationId": "getItem",
                        "tags": ["items"],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    },
                }
            },
        }
        result = get_display_endpoints(write_spec(spec))
        endpoints = result.get("items", [])
        assert len(endpoints) == 1, f"Expected 1 display endpoint, got {len(endpoints)}"
        param_names = [p["name"] for p in endpoints[0].path_params]
        assert "itemId" in param_names, (
            f"Path-level param 'itemId' missing from display endpoint. Got: {param_names}"
        )

    def test_ref_params_resolved_in_display(self, write_spec) -> None:
        """$ref parameters must be resolved in display endpoint extraction."""
        from mcp_generator.introspection import get_display_endpoints

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "components": {
                "parameters": {
                    "ItemId": {
                        "name": "itemId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                }
            },
            "paths": {
                "/items/{itemId}": {
                    "get": {
                        "operationId": "getItem",
                        "tags": ["items"],
                        "parameters": [
                            {"$ref": "#/components/parameters/ItemId"},
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    },
                }
            },
        }
        result = get_display_endpoints(write_spec(spec))
        endpoints = result.get("items", [])
        assert len(endpoints) == 1
        param_names = [p["name"] for p in endpoints[0].path_params]
        assert "itemId" in param_names, (
            f"$ref param 'itemId' missing from display endpoint. Got: {param_names}"
        )


# ---------------------------------------------------------------------------
# Bug #13: Stale set comprehension in get_resource_endpoints (dead code)
#
# Root cause: After Bug #3/#4 fix, line ~403 has an orphan set comprehension:
#   {p.get("name") for p in get_op.get("parameters", []) if "name" in p}
# It evaluates but the result is never assigned — pure dead code / linter warning.
# ---------------------------------------------------------------------------


class TestNoStaleSetComprehension:
    """get_resource_endpoints should not have dead-code expressions."""

    def test_no_orphan_set_comprehension(self) -> None:
        """Source code must not contain orphan set comprehensions."""
        import ast
        import inspect

        from mcp_generator.introspection import get_resource_endpoints

        source = inspect.getsource(get_resource_endpoints)
        tree = ast.parse(source)

        orphan_sets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.SetComp):
                orphan_sets.append(ast.get_source_segment(source, node) or f"line {node.lineno}")

        assert not orphan_sets, f"Found orphan set comprehension(s) — dead code: {orphan_sets}"


# ---------------------------------------------------------------------------
# Bug #14: camel_to_snake fails on consecutive uppercase letters
#
# Root cause: regex r"([a-z0-9])([A-Z])" only inserts _ between lower→upper
# transitions. "HTMLParser" → "htmlparser" instead of "html_parser".
# "APIClient" → "apiclient" instead of "api_client".
# ---------------------------------------------------------------------------


class TestCamelToSnakeConsecutiveUppercase:
    """camel_to_snake must handle consecutive uppercase letters (acronyms)."""

    def test_acronym_followed_by_word(self) -> None:
        from mcp_generator.utils import camel_to_snake

        assert camel_to_snake("HTMLParser") == "html_parser", (
            f"Expected 'html_parser', got '{camel_to_snake('HTMLParser')}'"
        )

    def test_acronym_api(self) -> None:
        from mcp_generator.utils import camel_to_snake

        assert camel_to_snake("APIClient") == "api_client", (
            f"Expected 'api_client', got '{camel_to_snake('APIClient')}'"
        )

    def test_mid_string_acronym(self) -> None:
        from mcp_generator.utils import camel_to_snake

        assert camel_to_snake("getHTTPResponse") == "get_http_response", (
            f"Expected 'get_http_response', got '{camel_to_snake('getHTTPResponse')}'"
        )

    def test_simple_camel_still_works(self) -> None:
        """Ensure normal CamelCase still converts correctly."""
        from mcp_generator.utils import camel_to_snake

        assert camel_to_snake("PetApi") == "pet_api"
        assert camel_to_snake("StoreApi") == "store_api"


# ---------------------------------------------------------------------------
# Bug #16: Response-level $ref not resolved in _extract_response_schema
#
# Root cause: _extract_response_schema receives raw response objects. If a
# response uses $ref (e.g. {"$ref": "#/components/responses/Success"}), the
# function tries .get("content") on the ref object which returns None.
# The $ref must be resolved first.
# ---------------------------------------------------------------------------


class TestResponseRefResolution:
    """_extract_response_schema must resolve $ref in response objects."""

    def test_ref_response_schema_extracted(self) -> None:
        from mcp_generator.introspection import _extract_response_schema

        spec = {
            "components": {
                "responses": {
                    "PetResponse": {
                        "description": "A pet",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
                }
            }
        }
        responses = {"200": {"$ref": "#/components/responses/PetResponse"}}
        result = _extract_response_schema(responses, spec)
        assert result is not None, (
            "_extract_response_schema returned None for $ref response — ref not resolved"
        )
        assert len(result.fields) >= 2, f"Expected at least 2 fields, got {len(result.fields)}"


# ---------------------------------------------------------------------------
# Bug #17: normalize_version misses simple pre-release tags
#
# Root cause: regex r"^(\d+\.\d+\.\d+)-([a-z]+)\.(.+)$" requires a dot
# after the prerelease name (e.g. "alpha.123"). But simple prerelease
# tags like "1.0.0-alpha" or "2.0.0-beta" have no dot — they don't match
# and are returned as-is, which is not PEP 440 compliant.
# ---------------------------------------------------------------------------


class TestNormalizeVersionSimplePrerelease:
    """normalize_version must handle pre-release tags without local parts."""

    def test_simple_alpha(self) -> None:
        from mcp_generator.utils import normalize_version

        result = normalize_version("1.0.0-alpha")
        assert result != "1.0.0-alpha", (
            f"'1.0.0-alpha' is not PEP 440 — should be normalized. Got: {result}"
        )
        # PEP 440 alpha: 1.0.0a0
        assert "a" in result.lower(), f"Expected PEP 440 alpha marker in '{result}'"

    def test_simple_beta(self) -> None:
        from mcp_generator.utils import normalize_version

        result = normalize_version("2.0.0-beta")
        assert result != "2.0.0-beta", (
            f"'2.0.0-beta' is not PEP 440 — should be normalized. Got: {result}"
        )

    def test_simple_rc(self) -> None:
        from mcp_generator.utils import normalize_version

        result = normalize_version("3.0.0-rc")
        assert result != "3.0.0-rc", (
            f"'3.0.0-rc' is not PEP 440 — should be normalized. Got: {result}"
        )

    def test_existing_format_still_works(self) -> None:
        """Ensure the existing format with local part still converts."""
        from mcp_generator.utils import normalize_version

        result = normalize_version("0.0.1-alpha.202510200205.3df5db6a")
        assert "a0+" in result, f"Existing format broke. Got: {result}"


# ===========================================================================
# Round 3 — CI failure: special chars in operation IDs
# ===========================================================================


# ---------------------------------------------------------------------------
# Bug #18: camel_to_snake doesn't strip non-identifier characters
#
# Root cause: Operation IDs like "getAppsByApp*" or "getDocs-api" contain
# special characters (* - etc.) that are not valid in Python identifiers.
# camel_to_snake only handles CamelCase→snake_case but doesn't sanitize
# these chars. The generated test functions have names like
# "test_call_get_apps_by_app*" which is a SyntaxError.
# This caused CI failure in "Test Examples" workflow (proxy-smart).
# ---------------------------------------------------------------------------


class TestCamelToSnakeSpecialChars:
    """camel_to_snake must produce valid Python identifiers."""

    def test_asterisk_removed(self) -> None:
        from mcp_generator.utils import camel_to_snake

        result = camel_to_snake("getAppsByApp*")
        assert result.isidentifier(), (
            f"'{result}' is not a valid Python identifier (from 'getAppsByApp*')"
        )
        assert "*" not in result

    def test_hyphen_replaced(self) -> None:
        from mcp_generator.utils import camel_to_snake

        result = camel_to_snake("getDocs-api")
        assert result.isidentifier(), (
            f"'{result}' is not a valid Python identifier (from 'getDocs-api')"
        )
        assert "-" not in result

    def test_multiple_special_chars(self) -> None:
        from mcp_generator.utils import camel_to_snake

        result = camel_to_snake("postFhir-serversByServer_idMtlsCertificates")
        assert result.isidentifier(), f"'{result}' is not a valid Python identifier"

    def test_leading_digit_after_strip(self) -> None:
        """If stripping leaves a digit at the start, it must still be valid."""
        from mcp_generator.utils import camel_to_snake

        result = camel_to_snake("123BadName")
        assert result.isidentifier(), f"'{result}' should be a valid Python identifier"


# ---------------------------------------------------------------------------
# Bug #19: Resource names from path segments not sanitized for Python
#
# Root cause: generate_resource_for_endpoint uses the raw last path segment
# as resource_name (e.g. "group-doors" from "/admin/group-doors").
# render_resource then emits "async def group-doors_resource(...)" which is
# a SyntaxError. The resource_name must be a valid Python identifier.
# This caused CI failure: proxy-smart server wouldn't start.
# ---------------------------------------------------------------------------


class TestResourceNameSanitization:
    """Resource names derived from path segments must be valid Python identifiers."""

    def test_hyphenated_path_segment(self) -> None:
        from mcp_generator.renderers import generate_resource_for_endpoint

        endpoint = {
            "path": "/admin/group-doors",
            "operation_id": "getGroupDoors",
            "path_params": [],
            "query_params": [
                {
                    "name": "limit",
                    "required": False,
                    "schema": {"type": "integer"},
                    "description": "",
                },
            ],
            "summary": "List group doors",
            "description": "List group doors",
            "responses": {},
            "tags": ["admin"],
        }
        spec = generate_resource_for_endpoint("admin_api", endpoint, "get_group_doors")
        assert spec is not None
        assert spec.resource_name.isidentifier(), (
            f"resource_name '{spec.resource_name}' is not a valid Python identifier"
        )

    def test_dotted_path_segment(self) -> None:
        from mcp_generator.renderers import generate_resource_for_endpoint

        endpoint = {
            "path": "/api/v2.0/items/{id}",
            "operation_id": "getItem",
            "path_params": ["id"],
            "query_params": [],
            "summary": "Get item",
            "description": "",
            "responses": {},
            "tags": ["items"],
        }
        spec = generate_resource_for_endpoint("items_api", endpoint, "get_item")
        assert spec is not None
        assert spec.resource_name.isidentifier(), (
            f"resource_name '{spec.resource_name}' is not a valid Python identifier"
        )

    def test_resource_function_compiles(self) -> None:
        """The full rendered resource code must be valid Python syntax."""
        from mcp_generator.models import ParameterInfo, ResourceSpec
        from mcp_generator.renderers import render_resource

        spec = ResourceSpec(
            resource_name="group_doors",
            uri_template="group-doors:///admin/group-doors{?limit}",
            method_name="get_group_doors",
            api_var_name="admin_api",
            path_params=[],
            query_params=[
                ParameterInfo(
                    name="limit",
                    type_hint="int",
                    required=False,
                    description="",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                )
            ],
            description="List group doors",
        )
        code = render_resource(spec)
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Rendered resource code has SyntaxError: {e}")


# ---------------------------------------------------------------------------
# Bug #20: Wildcard catch-all paths produce empty URI scheme
#
# Root cause: Paths like /apps/{app}/* have '*' as the last non-parameter
# segment. camel_to_snake("*") → "" because all chars are non-alphanumeric.
# This produces a URI template like "://apps/{app}/*" with an empty scheme,
# which fails URI scheme validation.
#
# Fix: Filter out '*' wildcards from path_segments; add fallback for
# invalid uri_scheme.
# ---------------------------------------------------------------------------


class TestWildcardPathResourceGeneration:
    """Wildcard catch-all routes must not produce empty URI schemes."""

    def test_wildcard_filtered_from_path_segments(self) -> None:
        """Path like /apps/{app}/* should use 'apps' not '*' as resource name."""
        from mcp_generator.renderers import generate_resource_for_endpoint

        endpoint = {
            "path": "/apps/{app}/*",
            "operation_id": "getAppFiles",
            "summary": "Get app files",
            "description": "Get files for an app",
            "path_params": [{"name": "app", "python_type": "str", "description": "App ID"}],
            "query_params": [],
        }
        result = generate_resource_for_endpoint("apps_api", endpoint, "get_app_files")
        assert result is not None
        # URI scheme should be 'apps', not '*' or empty
        assert result.uri_template.startswith("apps://"), (
            f"Expected 'apps://' scheme, got: {result.uri_template}"
        )
        # Function name should be valid Python identifier
        assert result.resource_name.isidentifier(), (
            f"resource_name should be valid identifier, got: {result.resource_name}"
        )

    def test_pure_wildcard_path_falls_back_to_operation_id(self) -> None:
        """Path like /{id}/* should fall back to operation_id for naming."""
        from mcp_generator.renderers import generate_resource_for_endpoint

        endpoint = {
            "path": "/{id}/*",
            "operation_id": "getCatchAll",
            "summary": "Catch-all",
            "description": "Catch all",
            "path_params": [{"name": "id", "python_type": "str", "description": "ID"}],
            "query_params": [],
        }
        result = generate_resource_for_endpoint("default_api", endpoint, "get_catch_all")
        assert result is not None
        # Should not have empty scheme
        scheme = result.uri_template.split("://")[0]
        assert scheme, f"URI scheme should not be empty, got: {result.uri_template}"
        assert any(c.isalnum() for c in scheme), (
            f"URI scheme must contain alphanumeric chars, got: '{scheme}'"
        )


# ---------------------------------------------------------------------------
# Rendered error blocks must interpolate, not print their own placeholders
#
# Root cause: _build_api_error_block returns a plain string that the caller
# interpolates into its own f-string. A value substituted into an f-string is
# not re-scanned for brace escapes, so `{{error_msg}}` survived verbatim and the
# generated server printed "API Error: {error_msg}" instead of the error.
# ---------------------------------------------------------------------------


class TestRenderedErrorBlocksInterpolate:
    """Generated exception messages must carry real values, not placeholders."""

    @staticmethod
    def _render() -> str:
        from mcp_generator.models import ParameterInfo, ToolSpec
        from mcp_generator.renderers import _render_tool

        spec = ToolSpec(
            tool_name="test_tool",
            method_name="test_method",
            api_var_name="test_api",
            docstring="Test docstring",
            parameters=[
                ParameterInfo(
                    name="count",
                    type_hint="int",
                    required=True,
                    description="A count",
                    example_json=None,
                    is_pydantic=False,
                    pydantic_class=None,
                ),
            ],
        )
        return _render_tool(spec)

    def test_no_doubled_placeholders_survive(self) -> None:
        code = self._render()
        offenders = [
            line.strip()
            for line in code.splitlines()
            if "{{error_msg}}" in line or "{{e.status}}" in line or "{{_suggestion}}" in line
        ]
        assert not offenders, (
            "Generated code still contains doubled placeholders, which print as "
            f"literal text instead of interpolating: {offenders}"
        )

    def test_error_message_interpolates_the_error(self) -> None:
        code = self._render()
        assert "{error_msg}" in code, "generated error message should interpolate error_msg"

    def test_rendered_tool_is_valid_python(self) -> None:
        """Escaping mistakes tend to surface as an unterminated string."""
        import ast
        import textwrap

        ast.parse(textwrap.dedent(self._render()))
