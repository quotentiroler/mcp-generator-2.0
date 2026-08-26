"""Tests for mcp_generator.introspection — tag auto-discovery and spec loading."""

import copy
from collections.abc import Callable
from pathlib import Path

from mcp_generator.introspection import (
    _extract_response_schema,
    _fields_to_coercion_schema,
    _parse_schema_fields,
    _ref_cache,
    _resolve_ref,
    enrich_spec_tags,
    get_body_schemas,
    get_delete_endpoints,
    get_display_endpoints,
    get_form_endpoints,
    get_security_config,
)
from mcp_generator.models import ResponseField
from test.conftest import (
    MINIMAL_OPENAPI_SPEC,
    OPENAPI_SPEC_API_KEY_ONLY,
    OPENAPI_SPEC_WITH_SECURITY,
)

# ---------------------------------------------------------------------------
# enrich_spec_tags
# ---------------------------------------------------------------------------


class TestEnrichSpecTags:
    def test_discovers_undeclared_tag(self) -> None:
        """'user' tag is used on /users but not declared in top-level tags."""
        spec = copy.deepcopy(MINIMAL_OPENAPI_SPEC)
        # Confirm precondition: only 'pet' is declared
        declared = {t["name"] for t in spec["tags"]}
        assert "pet" in declared
        assert "user" not in declared

        discovered = enrich_spec_tags(spec)

        assert "user" in discovered
        tag_names = {t["name"] for t in spec["tags"]}
        assert "user" in tag_names
        assert "pet" in tag_names  # existing tag preserved

    def test_no_duplicates_when_already_declared(self) -> None:
        spec = copy.deepcopy(MINIMAL_OPENAPI_SPEC)
        # Add 'user' to declared tags before enrichment
        spec["tags"].append({"name": "user", "description": "Users"})

        discovered = enrich_spec_tags(spec)

        assert discovered == []  # nothing new
        # Should still have exactly 2 tags
        assert len(spec["tags"]) == 2

    def test_handles_spec_without_tags_key(self) -> None:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/x": {
                    "get": {"tags": ["alpha", "beta"], "responses": {"200": {"description": "OK"}}}
                }
            },
        }
        discovered = enrich_spec_tags(spec)
        assert set(discovered) == {"alpha", "beta"}
        assert "tags" in spec
        assert len(spec["tags"]) == 2

    def test_handles_empty_paths(self) -> None:
        spec = {"openapi": "3.0.3", "info": {"title": "T", "version": "1"}, "paths": {}, "tags": []}
        discovered = enrich_spec_tags(spec)
        assert discovered == []

    def test_handles_operations_without_tags(self) -> None:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {"/x": {"get": {"responses": {"200": {"description": "OK"}}}}},
            "tags": [],
        }
        discovered = enrich_spec_tags(spec)
        assert discovered == []

    def test_multiple_undeclared_across_paths(self) -> None:
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/a": {"get": {"tags": ["alpha"], "responses": {"200": {"description": "OK"}}}},
                "/b": {
                    "post": {"tags": ["beta"], "responses": {"201": {"description": "Created"}}}
                },
                "/c": {
                    "delete": {
                        "tags": ["gamma"],
                        "responses": {"204": {"description": "No Content"}},
                    }
                },
            },
            "tags": [{"name": "alpha", "description": "Already declared"}],
        }
        discovered = enrich_spec_tags(spec)
        assert set(discovered) == {"beta", "gamma"}
        assert len(spec["tags"]) == 3

    def test_idempotent_on_second_call(self) -> None:
        """Calling enrich_spec_tags twice should not add duplicates."""
        spec = copy.deepcopy(MINIMAL_OPENAPI_SPEC)
        enrich_spec_tags(spec)  # first call discovers tags
        second = enrich_spec_tags(spec)
        assert second == []  # nothing new the second time
        assert len(spec["tags"]) == 2  # pet + user


# ---------------------------------------------------------------------------
# get_security_config
# ---------------------------------------------------------------------------


class TestGetSecurityConfig:
    def test_reads_header_api_key_scheme(self, write_spec: Callable[..., Path]) -> None:
        """An apiKey scheme keeps its location and header name."""
        config = get_security_config(write_spec(OPENAPI_SPEC_API_KEY_ONLY))
        assert config.schemes["apiKey"] == {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
        }
        assert config.global_security == [{"apiKey": []}]

    def test_api_key_only_spec_has_no_oauth_or_bearer(
        self, write_spec: Callable[..., Path]
    ) -> None:
        """An apiKey scheme must not be mistaken for OAuth2 or bearer."""
        config = get_security_config(write_spec(OPENAPI_SPEC_API_KEY_ONLY))
        assert config.oauth_config is None
        assert config.bearer_format is None

    def test_api_key_only_spec_invents_no_scopes(self, write_spec: Callable[..., Path]) -> None:
        """Global security requiring no scopes yields no scopes."""
        config = get_security_config(write_spec(OPENAPI_SPEC_API_KEY_ONLY))
        assert config.default_scopes == []

    def test_reads_all_scheme_families(self, write_spec: Callable[..., Path]) -> None:
        """bearer, oauth2 and apiKey schemes are read from one spec."""
        config = get_security_config(write_spec(OPENAPI_SPEC_WITH_SECURITY))
        assert set(config.schemes) == {"bearerAuth", "oauth2", "apiKey"}
        assert config.bearer_format == "JWT"
        assert config.oauth_config is not None
        assert config.oauth_config.scheme_name == "oauth2"

    def test_collects_oauth_client_credentials_flow(self, write_spec: Callable[..., Path]) -> None:
        config = get_security_config(write_spec(OPENAPI_SPEC_WITH_SECURITY))
        assert config.oauth_config is not None
        flow = config.oauth_config.flows["clientCredentials"]
        assert flow.token_url == "https://auth.example.com/token"
        assert config.oauth_config.all_scopes == {
            "read": "Read access",
            "write": "Write access",
        }

    def test_default_scopes_come_from_global_security(
        self, write_spec: Callable[..., Path]
    ) -> None:
        """Only scopes the spec actually requires become defaults."""
        config = get_security_config(write_spec(OPENAPI_SPEC_WITH_SECURITY))
        assert config.default_scopes == ["read"]

    def test_reads_extension_auth_metadata(self, write_spec: Callable[..., Path]) -> None:
        spec = copy.deepcopy(OPENAPI_SPEC_API_KEY_ONLY)
        spec["x-jwks-uri"] = "https://auth.example.com/.well-known/jwks.json"
        spec["x-issuer"] = "https://auth.example.com"
        spec["x-audience"] = "key-api"
        config = get_security_config(write_spec(spec))
        assert config.jwks_uri == "https://auth.example.com/.well-known/jwks.json"
        assert config.issuer == "https://auth.example.com"
        assert config.audience == "key-api"

    def test_spec_without_schemes_is_unsecured(self, write_spec: Callable[..., Path]) -> None:
        config = get_security_config(write_spec(MINIMAL_OPENAPI_SPEC))
        assert config.schemes == {}
        assert config.default_scopes == []

    def test_missing_spec_returns_default_config(self, tmp_path: Path) -> None:
        config = get_security_config(tmp_path)
        assert config.schemes == {}
        assert config.oauth_config is None


# ---------------------------------------------------------------------------
# _fields_to_coercion_schema
# ---------------------------------------------------------------------------


class TestFieldsToCoercionSchema:
    def test_simple_string_field(self) -> None:
        fields = [ResponseField(name="name", python_type="str")]
        result = _fields_to_coercion_schema(fields)
        assert result == {"name": {"type": "string"}}

    def test_integer_field(self) -> None:
        fields = [ResponseField(name="id", python_type="int")]
        result = _fields_to_coercion_schema(fields)
        assert result == {"id": {"type": "integer"}}

    def test_enum_field(self) -> None:
        fields = [
            ResponseField(name="status", python_type="str", is_enum=True, enum_values=["a", "b"])
        ]
        result = _fields_to_coercion_schema(fields)
        assert result == {"status": {"type": "string", "enum": ["a", "b"]}}

    def test_nested_object(self) -> None:
        fields = [
            ResponseField(
                name="category",
                python_type="dict",
                is_nested_object=True,
                nested_fields=[
                    ResponseField(name="id", python_type="int"),
                    ResponseField(name="name", python_type="str"),
                ],
            )
        ]
        result = _fields_to_coercion_schema(fields)
        assert result == {
            "category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            }
        }

    def test_array_of_strings(self) -> None:
        fields = [ResponseField(name="urls", python_type="list", is_array=True)]
        result = _fields_to_coercion_schema(fields)
        assert result == {"urls": {"type": "array", "items": {"type": "string"}}}

    def test_array_of_objects(self) -> None:
        fields = [
            ResponseField(
                name="tags",
                python_type="list",
                is_array=True,
                nested_fields=[
                    ResponseField(name="id", python_type="int"),
                    ResponseField(name="name", python_type="str"),
                ],
            )
        ]
        result = _fields_to_coercion_schema(fields)
        assert result == {
            "tags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                },
            }
        }


# ---------------------------------------------------------------------------
# get_body_schemas
# ---------------------------------------------------------------------------


class TestGetBodySchemas:
    def test_extracts_pet_body_schema(self, tmp_spec_dir: Path) -> None:
        """get_body_schemas should return a schema for 'create_pet' from MINIMAL_OPENAPI_SPEC."""
        schemas = get_body_schemas(tmp_spec_dir)
        assert "create_pet" in schemas
        pet_schema = schemas["create_pet"]
        assert pet_schema["name"]["type"] == "string"
        assert pet_schema["category"]["type"] == "object"
        assert pet_schema["photoUrls"]["type"] == "array"
        assert pet_schema["tags"]["type"] == "array"
        assert pet_schema["tags"]["items"]["type"] == "object"
        assert pet_schema["status"]["enum"] == ["available", "pending", "sold"]

    def test_returns_empty_for_missing_spec(self, tmp_path: Path) -> None:
        schemas = get_body_schemas(tmp_path)
        assert schemas == {}

    def test_skips_get_endpoints(self, tmp_spec_dir: Path) -> None:
        """GET endpoints should not appear in body schemas."""
        schemas = get_body_schemas(tmp_spec_dir)
        assert "list_pets" not in schemas
        assert "list_users" not in schemas


# ===========================================================================
# Configurable max_depth
# ===========================================================================


class TestConfigurableMaxDepth:
    """max_depth controls how deep schema parsing recurses through $ref chains."""

    @staticmethod
    def _deep_spec() -> dict:
        """Build a spec with 5 levels of nesting: A > B > C > D > E."""
        return {
            "components": {
                "schemas": {
                    "E": {"type": "object", "properties": {"value": {"type": "string"}}},
                    "D": {
                        "type": "object",
                        "properties": {"e": {"$ref": "#/components/schemas/E"}},
                    },
                    "C": {
                        "type": "object",
                        "properties": {"d": {"$ref": "#/components/schemas/D"}},
                    },
                    "B": {
                        "type": "object",
                        "properties": {"c": {"$ref": "#/components/schemas/C"}},
                    },
                    "A": {
                        "type": "object",
                        "properties": {"b": {"$ref": "#/components/schemas/B"}},
                    },
                }
            }
        }

    def test_depth_3_truncates_at_level_3(self) -> None:
        """depth=3: A(0) > b(1) > c(2) > d(3, no children)."""
        spec = self._deep_spec()
        schema = spec["components"]["schemas"]["A"]
        fields = _parse_schema_fields(schema, spec, max_depth=3)
        b = fields[0]
        assert b.name == "b"
        c = b.nested_fields[0]
        assert c.name == "c"
        d = c.nested_fields[0]
        assert d.name == "d"
        assert d.nested_fields == []

    def test_depth_5_reaches_leaf(self) -> None:
        """depth=5: reaches E.value at the bottom of the chain."""
        spec = self._deep_spec()
        schema = spec["components"]["schemas"]["A"]
        fields = _parse_schema_fields(schema, spec, max_depth=5)
        # Walk A > b > c > d > e > value
        node = fields[0]
        for expected in ("b", "c", "d", "e"):
            assert node.name == expected
            assert len(node.nested_fields) > 0, f"{expected} should have children at depth 5"
            node = node.nested_fields[0]
        assert node.name == "value"
        assert node.python_type == "str"

    def test_depth_1_returns_flat_props_only(self) -> None:
        """depth=1: top-level property exists but has no nested children."""
        spec = self._deep_spec()
        schema = spec["components"]["schemas"]["A"]
        fields = _parse_schema_fields(schema, spec, max_depth=1)
        assert len(fields) == 1
        assert fields[0].name == "b"
        assert fields[0].nested_fields == []

    def test_depth_threads_through_extract_response_schema(self) -> None:
        """max_depth parameter on _extract_response_schema reaches _parse_schema_fields."""
        spec = self._deep_spec()
        responses = {
            "200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/A"}}}}
        }
        # depth=5 should produce deep nesting
        result_deep = _extract_response_schema(responses, spec, max_depth=5)
        assert result_deep is not None
        b = result_deep.fields[0]
        assert b.nested_fields[0].nested_fields[0].nested_fields != []

        # depth=2 should truncate earlier
        result_shallow = _extract_response_schema(responses, spec, max_depth=2)
        assert result_shallow is not None
        b2 = result_shallow.fields[0]
        assert b2.nested_fields[0].nested_fields == []

    def test_circular_ref_stops_regardless_of_depth(self) -> None:
        """Circular $refs must stop even with high max_depth."""
        spec = {
            "components": {
                "schemas": {
                    "Node": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                            "child": {"$ref": "#/components/schemas/Node"},
                        },
                    }
                }
            }
        }
        fields = _parse_schema_fields(spec["components"]["schemas"]["Node"], spec, max_depth=100)
        # Should not infinitely recurse — value field should exist
        names = {f.name for f in fields}
        assert "value" in names
        assert "child" in names


# ===========================================================================
# oneOf / anyOf handling — merge all variants
# ===========================================================================


class TestOneOfAnyOfHandling:
    """oneOf/anyOf should merge properties from all variants, not just pick the first."""

    @staticmethod
    def _polymorphic_spec() -> dict:
        return {
            "components": {
                "schemas": {
                    "StringValue": {
                        "type": "object",
                        "properties": {"valueString": {"type": "string"}},
                    },
                    "QuantityValue": {
                        "type": "object",
                        "properties": {
                            "valueQuantity": {"type": "number"},
                            "unit": {"type": "string"},
                        },
                    },
                    "CodeableValue": {
                        "type": "object",
                        "properties": {"valueCode": {"type": "string"}},
                    },
                }
            }
        }

    def test_oneof_merges_all_variant_properties(self) -> None:
        """oneOf with 3 $ref variants exposes all 4 unique properties."""
        spec = self._polymorphic_spec()
        schema = {
            "oneOf": [
                {"$ref": "#/components/schemas/StringValue"},
                {"$ref": "#/components/schemas/QuantityValue"},
                {"$ref": "#/components/schemas/CodeableValue"},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        names = {f.name for f in fields}
        assert names == {"valueString", "valueQuantity", "unit", "valueCode"}

    def test_anyof_merges_all_variant_properties(self) -> None:
        """anyOf with 2 $ref variants exposes all 3 properties."""
        spec = self._polymorphic_spec()
        schema = {
            "anyOf": [
                {"$ref": "#/components/schemas/StringValue"},
                {"$ref": "#/components/schemas/QuantityValue"},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        names = {f.name for f in fields}
        assert names == {"valueString", "valueQuantity", "unit"}

    def test_oneof_inline_schemas_merged(self) -> None:
        """oneOf with inline object schemas merges all properties."""
        spec: dict = {"components": {"schemas": {}}}
        schema = {
            "oneOf": [
                {"type": "object", "properties": {"alpha": {"type": "string"}}},
                {"type": "object", "properties": {"beta": {"type": "integer"}}},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        names = {f.name for f in fields}
        assert names == {"alpha", "beta"}

    def test_oneof_overlapping_properties_last_wins(self) -> None:
        """When variants share a property name, last variant's definition wins."""
        spec: dict = {"components": {"schemas": {}}}
        schema = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"status": {"type": "string", "description": "from variant A"}},
                },
                {
                    "type": "object",
                    "properties": {"status": {"type": "integer", "description": "from variant B"}},
                },
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        # Should have exactly one 'status' field (merged/overwritten)
        assert len(fields) == 1
        assert fields[0].name == "status"
        assert fields[0].python_type == "int"  # last variant wins

    def test_oneof_nested_inside_property(self) -> None:
        """oneOf inside a property (not at schema root) should also merge."""
        spec: dict = {
            "components": {
                "schemas": {
                    "Observation": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "value": {
                                "oneOf": [
                                    {
                                        "type": "object",
                                        "properties": {"valueString": {"type": "string"}},
                                    },
                                    {
                                        "type": "object",
                                        "properties": {"valueNumber": {"type": "number"}},
                                    },
                                ]
                            },
                        },
                    }
                }
            }
        }
        fields = _parse_schema_fields(spec["components"]["schemas"]["Observation"], spec)
        names = {f.name for f in fields}
        assert "id" in names
        assert "value" in names
        # The value field should have merged nested fields from both oneOf variants
        value_field = next(f for f in fields if f.name == "value")
        nested_names = {f.name for f in value_field.nested_fields}
        assert "valueString" in nested_names
        assert "valueNumber" in nested_names

    def test_allof_still_merges(self) -> None:
        """allOf must still work after the oneOf/anyOf refactor."""
        spec = self._polymorphic_spec()
        schema = {
            "allOf": [
                {"$ref": "#/components/schemas/StringValue"},
                {"$ref": "#/components/schemas/QuantityValue"},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        names = {f.name for f in fields}
        assert names == {"valueString", "valueQuantity", "unit"}

    def test_oneof_preserves_field_types(self) -> None:
        """Merged fields must retain their correct python_type from each variant."""
        spec = self._polymorphic_spec()
        schema = {
            "oneOf": [
                {"$ref": "#/components/schemas/StringValue"},
                {"$ref": "#/components/schemas/QuantityValue"},
            ]
        }
        fields = _parse_schema_fields(schema, spec)
        by_name = {f.name: f for f in fields}
        assert by_name["valueString"].python_type == "str"
        assert by_name["valueQuantity"].python_type == "float"
        assert by_name["unit"].python_type == "str"


# ===========================================================================
# $ref caching
# ===========================================================================


class TestRefCaching:
    """$ref resolution uses a module-level cache for performance."""

    def test_resolve_ref_returns_correct_schema(self) -> None:
        spec = {
            "components": {
                "schemas": {"Pet": {"type": "object", "properties": {"name": {"type": "string"}}}}
            }
        }
        result = _resolve_ref(spec, "#/components/schemas/Pet")
        assert result["type"] == "object"
        assert "name" in result["properties"]

    def test_resolve_ref_cached_returns_same_object(self) -> None:
        """Cached result must be the exact same object (identity check)."""
        spec = {
            "components": {
                "schemas": {"Dog": {"type": "object", "properties": {"breed": {"type": "string"}}}}
            }
        }
        r1 = _resolve_ref(spec, "#/components/schemas/Dog")
        r2 = _resolve_ref(spec, "#/components/schemas/Dog")
        assert r1 is r2  # identity, not just equality

    def test_cache_key_includes_spec_identity(self) -> None:
        """Different spec dicts with same ref must not share cached results."""
        spec_a = {
            "components": {
                "schemas": {"X": {"type": "object", "properties": {"a": {"type": "string"}}}}
            }
        }
        spec_b = {
            "components": {
                "schemas": {"X": {"type": "object", "properties": {"b": {"type": "integer"}}}}
            }
        }
        result_a = _resolve_ref(spec_a, "#/components/schemas/X")
        result_b = _resolve_ref(spec_b, "#/components/schemas/X")
        assert "a" in result_a["properties"]
        assert "b" in result_b["properties"]
        assert result_a is not result_b

    def test_cache_populated_after_resolve(self) -> None:
        """The _ref_cache dict must contain entries after resolution."""
        spec = {
            "components": {
                "schemas": {"Cat": {"type": "object", "properties": {"color": {"type": "string"}}}}
            }
        }
        ref = "#/components/schemas/Cat"
        _resolve_ref(spec, ref)
        cache_key = (id(spec), ref)
        assert cache_key in _ref_cache
        assert _ref_cache[cache_key]["type"] == "object"

    def test_missing_ref_returns_empty_dict(self) -> None:
        """Non-existent $ref should return {} and cache the empty result."""
        spec: dict = {"components": {"schemas": {}}}
        result = _resolve_ref(spec, "#/components/schemas/NonExistent")
        assert result == {}


# ===========================================================================
# FHIR content type matching
# ===========================================================================


class TestFhirContentType:
    """Response extraction supports FHIR and standard JSON content types."""

    def test_fhir_json_content_type(self) -> None:
        """application/fhir+json should be matched for response schema extraction."""
        spec: dict = {"components": {"schemas": {}}}
        responses = {
            "200": {
                "content": {
                    "application/fhir+json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "resourceType": {"type": "string"},
                            },
                        }
                    }
                }
            }
        }
        result = _extract_response_schema(responses, spec)
        assert result is not None
        names = {f.name for f in result.fields}
        assert names == {"id", "resourceType"}

    def test_standard_json_still_works(self) -> None:
        """application/json continues to work."""
        spec: dict = {"components": {"schemas": {}}}
        responses = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        }
                    }
                }
            }
        }
        result = _extract_response_schema(responses, spec)
        assert result is not None
        assert result.fields[0].name == "name"

    def test_json_preferred_over_fhir_when_both_present(self) -> None:
        """When both application/json and application/fhir+json exist, json wins."""
        spec: dict = {"components": {"schemas": {}}}
        responses = {
            "200": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"from_json": {"type": "string"}},
                        }
                    },
                    "application/fhir+json": {
                        "schema": {
                            "type": "object",
                            "properties": {"from_fhir": {"type": "string"}},
                        }
                    },
                }
            }
        }
        result = _extract_response_schema(responses, spec)
        assert result is not None
        names = {f.name for f in result.fields}
        assert "from_json" in names

    def test_fhir_json_with_array_response(self) -> None:
        """FHIR Bundle-style array responses should parse correctly."""
        spec: dict = {"components": {"schemas": {}}}
        responses = {
            "200": {
                "content": {
                    "application/fhir+json": {
                        "schema": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "resourceType": {"type": "string"},
                                    "id": {"type": "string"},
                                },
                            },
                        }
                    }
                }
            }
        }
        result = _extract_response_schema(responses, spec)
        assert result is not None
        assert result.is_array is True
        names = {f.name for f in result.fields}
        assert names == {"resourceType", "id"}

    def test_wildcard_fallback_still_works(self) -> None:
        """*/* content type should still be matched as last resort."""
        spec: dict = {"components": {"schemas": {}}}
        responses = {
            "200": {
                "content": {
                    "*/*": {
                        "schema": {
                            "type": "object",
                            "properties": {"data": {"type": "string"}},
                        }
                    }
                }
            }
        }
        result = _extract_response_schema(responses, spec)
        assert result is not None
        assert result.fields[0].name == "data"


# ===========================================================================
# Spec passthrough — overlay-enhanced specs reach endpoint extraction
# ===========================================================================

_PASSTHROUGH_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "tags": [{"name": "items"}],
    "paths": {
        "/items": {
            "get": {
                "operationId": "listItems",
                "tags": ["items"],
                "summary": "List items",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "Search query",
                    }
                ],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    },
                                }
                            }
                        }
                    }
                },
            },
            "post": {
                "operationId": "createItem",
                "tags": ["items"],
                "summary": "Create item",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "price": {"type": "number"},
                                },
                                "required": ["name"],
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/items/{itemId}": {
            "delete": {
                "operationId": "deleteItem",
                "tags": ["items"],
                "summary": "Delete item",
                "parameters": [
                    {"name": "itemId", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {"204": {"description": "Deleted"}},
            }
        },
    },
    "components": {"schemas": {}},
}


class TestSpecPassthrough:
    """When spec= is provided, endpoint functions must use it instead of reading from disk."""

    def test_display_endpoints_from_spec_dict(self) -> None:
        """get_display_endpoints(spec=...) should parse endpoints without disk I/O."""
        result = get_display_endpoints(spec=_PASSTHROUGH_SPEC)
        assert "items" in result
        ep = result["items"][0]
        assert ep.operation_id == "listItems"
        assert ep.response_schema is not None
        names = {f.name for f in ep.response_schema.fields}
        assert names == {"id", "name"}

    def test_form_endpoints_from_spec_dict(self) -> None:
        """get_form_endpoints(spec=...) should parse POST/PUT bodies without disk I/O."""
        result = get_form_endpoints(spec=_PASSTHROUGH_SPEC)
        assert "items" in result
        ep = result["items"][0]
        assert ep.operation_id == "createItem"
        field_names = {f.name for f in ep.fields}
        assert "name" in field_names
        assert "price" in field_names

    def test_delete_endpoints_from_spec_dict(self) -> None:
        """get_delete_endpoints(spec=...) should find DELETE ops without disk I/O."""
        result = get_delete_endpoints(spec=_PASSTHROUGH_SPEC)
        assert "items" in result
        ep = result["items"][0]
        assert ep.operation_id == "deleteItem"
        assert any(p["name"] == "itemId" for p in ep.path_params)

    def test_overlay_enhanced_spec_used_over_disk(self, write_spec: Callable[..., Path]) -> None:
        """When spec= is provided, the disk file (if different) must be ignored."""

        # Write a DIFFERENT spec to disk
        disk_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Disk", "version": "1.0.0"},
            "paths": {
                "/other": {
                    "get": {
                        "operationId": "listOther",
                        "tags": ["other"],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"x": {"type": "string"}},
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            },
            "components": {"schemas": {}},
        }
        # Pass the in-memory spec — should get "items", NOT "other"
        result = get_display_endpoints(write_spec(disk_spec), spec=_PASSTHROUGH_SPEC)
        assert "items" in result
        assert "other" not in result

    def test_display_query_params_include_description(self) -> None:
        """Query param descriptions from spec should flow through to endpoints."""
        result = get_display_endpoints(spec=_PASSTHROUGH_SPEC)
        ep = result["items"][0]
        q_param = next(p for p in ep.query_params if p["name"] == "q")
        assert q_param["description"] == "Search query"
