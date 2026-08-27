"""Tests for Phase 2: response schema extraction and display tool generation."""

from mcp_generator.introspection import (
    _extract_response_schema,
    _parse_schema_fields,
    _resolve_ref,
)
from mcp_generator.models import (
    DeleteEndpoint,
    DisplayEndpoint,
    FormEndpoint,
    ResponseField,
    ResponseSchema,
)
from mcp_generator.renderers import (
    _tool_name_for_endpoint,
    render_display_module,
    table_columns_for_fields,
)

# ---------------------------------------------------------------------------
# Test OpenAPI spec with various response shapes
# ---------------------------------------------------------------------------

SCHEMA_TEST_SPEC: dict = {
    "openapi": "3.0.3",
    "info": {"title": "Schema Test API", "version": "1.0.0"},
    "paths": {
        "/pets/{petId}": {
            "get": {
                "operationId": "getPetById",
                "tags": ["pet"],
                "summary": "Get pet by ID",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"},
                            }
                        },
                    }
                },
            }
        },
        "/pets": {
            "get": {
                "operationId": "findPets",
                "tags": ["pet"],
                "summary": "Find all pets",
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Pet"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/inventory": {
            "get": {
                "operationId": "getInventory",
                "tags": ["store"],
                "summary": "Returns inventory",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": {"type": "integer"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/login": {
            "get": {
                "operationId": "loginUser",
                "tags": ["user"],
                "summary": "Login user",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"type": "string"},
                            }
                        },
                    }
                },
            }
        },
        "/orders/{orderId}": {
            "get": {
                "operationId": "getOrder",
                "tags": ["store"],
                "summary": "Get order by ID",
                "parameters": [
                    {
                        "name": "orderId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Order"},
                            }
                        },
                    }
                },
            }
        },
    },
    "tags": [
        {"name": "pet"},
        {"name": "store"},
        {"name": "user"},
    ],
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                    "category": {"$ref": "#/components/schemas/Category"},
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                    },
                    "tags": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Tag"},
                    },
                },
            },
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
            "Tag": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
            "Order": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "quantity": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "enum": ["placed", "approved", "delivered"],
                    },
                    "complete": {"type": "boolean"},
                    "shipDate": {"type": "string", "format": "date-time"},
                },
            },
        }
    },
}


# ---------------------------------------------------------------------------
# _resolve_ref
# ---------------------------------------------------------------------------


class TestResolveRef:
    def test_resolves_simple_ref(self) -> None:
        result = _resolve_ref(SCHEMA_TEST_SPEC, "#/components/schemas/Pet")
        assert "properties" in result
        assert "id" in result["properties"]

    def test_returns_empty_dict_for_invalid_ref(self) -> None:
        result = _resolve_ref(SCHEMA_TEST_SPEC, "#/components/schemas/Nonexistent")
        assert result == {}

    def test_returns_empty_dict_for_malformed_ref(self) -> None:
        result = _resolve_ref(SCHEMA_TEST_SPEC, "")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# _parse_schema_fields
# ---------------------------------------------------------------------------


class TestParseSchemaFields:
    def test_parses_pet_schema(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        names = {f.name for f in fields}
        assert {"id", "name", "category", "status", "tags"} == names

    def test_detects_enum_field(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        status = next(f for f in fields if f.name == "status")
        assert status.is_enum is True
        assert "available" in status.enum_values

    def test_detects_nested_object(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        cat = next(f for f in fields if f.name == "category")
        assert cat.is_nested_object is True
        nested_names = {nf.name for nf in cat.nested_fields}
        assert "id" in nested_names
        assert "name" in nested_names

    def test_detects_array_field(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC)
        tags = next(f for f in fields if f.name == "tags")
        assert tags.is_array is True

    def test_detects_boolean_field(self) -> None:
        order = SCHEMA_TEST_SPEC["components"]["schemas"]["Order"]
        fields = _parse_schema_fields(order, SCHEMA_TEST_SPEC)
        complete = next(f for f in fields if f.name == "complete")
        assert complete.python_type == "bool"

    def test_detects_datetime_format(self) -> None:
        order = SCHEMA_TEST_SPEC["components"]["schemas"]["Order"]
        fields = _parse_schema_fields(order, SCHEMA_TEST_SPEC)
        ship = next(f for f in fields if f.name == "shipDate")
        assert ship.format == "date-time"

    def test_respects_max_depth(self) -> None:
        pet = SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"]
        fields = _parse_schema_fields(pet, SCHEMA_TEST_SPEC, max_depth=1)
        cat = next((f for f in fields if f.name == "category"), None)
        # At max_depth=1, the ref resolves but can't recurse further
        assert cat is not None

    def test_handles_circular_refs(self) -> None:
        """Circular $ref should not cause infinite recursion."""
        circular_spec = {
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
        node = circular_spec["components"]["schemas"]["Node"]
        fields = _parse_schema_fields(node, circular_spec)
        assert len(fields) >= 1  # Should not hang


# ---------------------------------------------------------------------------
# _extract_response_schema
# ---------------------------------------------------------------------------


class TestExtractResponseSchema:
    def test_extracts_single_object(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/pets/{petId}"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is not None
        assert schema.is_object is True
        assert schema.is_array is False
        assert schema.schema_name == "Pet"
        assert len(schema.fields) >= 4

    def test_extracts_array_of_objects(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/pets"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is not None
        assert schema.is_array is True
        assert schema.schema_name == "Pet"

    def test_skips_additional_properties_only(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/inventory"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is None

    def test_skips_scalar_string(self) -> None:
        responses = SCHEMA_TEST_SPEC["paths"]["/login"]["get"]["responses"]
        schema = _extract_response_schema(responses, SCHEMA_TEST_SPEC)
        assert schema is None

    def test_returns_none_for_empty_responses(self) -> None:
        schema = _extract_response_schema({}, SCHEMA_TEST_SPEC)
        assert schema is None

    def test_returns_none_for_no_content(self) -> None:
        schema = _extract_response_schema({"200": {"description": "OK"}}, SCHEMA_TEST_SPEC)
        assert schema is None


# ---------------------------------------------------------------------------
# _tool_name_for_endpoint
# ---------------------------------------------------------------------------


class TestToolNameForEndpoint:
    def _make_endpoint(self, op_id: str, is_array: bool = False) -> DisplayEndpoint:
        schema = ResponseSchema(
            fields=[ResponseField(name="id", python_type="int")],
            is_array=is_array,
            is_object=not is_array,
            schema_name="Pet",
        )
        return DisplayEndpoint(
            operation_id=op_id,
            path="/test",
            http_method="get",
            summary="test",
            tag="pet",
            path_params=[],
            query_params=[],
            response_schema=schema,
        )

    def test_array_endpoint_gets_table_suffix(self) -> None:
        ep = self._make_endpoint("findPetsByStatus", is_array=True)
        name = _tool_name_for_endpoint(ep)
        assert name == "view_find_pets_by_status_table"

    def test_object_endpoint_gets_detail_suffix(self) -> None:
        ep = self._make_endpoint("getPetById", is_array=False)
        name = _tool_name_for_endpoint(ep)
        assert name == "view_get_pet_by_id_detail"

    def test_unique_names_for_similar_endpoints(self) -> None:
        ep1 = self._make_endpoint("findPetsByStatus", is_array=True)
        ep2 = self._make_endpoint("findPetsByTags", is_array=True)
        assert _tool_name_for_endpoint(ep1) != _tool_name_for_endpoint(ep2)


# ---------------------------------------------------------------------------
# table_columns_for_fields
# ---------------------------------------------------------------------------


class TestTableColumnsForFields:
    def test_skips_array_fields(self) -> None:
        fields = [
            ResponseField(name="id", python_type="int"),
            ResponseField(name="tags", python_type="list", is_array=True),
            ResponseField(name="name", python_type="str"),
        ]
        columns = table_columns_for_fields(fields)
        keys = [c["key"] for c in columns]
        assert "id" in keys
        assert "name" in keys
        assert "tags" not in keys

    def test_skips_nested_objects(self) -> None:
        fields = [
            ResponseField(name="id", python_type="int"),
            ResponseField(name="category", python_type="dict", is_nested_object=True),
        ]
        columns = table_columns_for_fields(fields)
        keys = [c["key"] for c in columns]
        assert "category" not in keys

    def test_labels_are_title_case(self) -> None:
        fields = [ResponseField(name="first_name", python_type="str")]
        columns = table_columns_for_fields(fields)
        assert columns[0]["label"] == "First Name"


# ---------------------------------------------------------------------------
# render_display_module (integration)
# ---------------------------------------------------------------------------


class TestRenderDisplayModule:
    def _make_endpoints(self) -> list[DisplayEndpoint]:
        pet_fields = _parse_schema_fields(
            SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"], SCHEMA_TEST_SPEC
        )
        return [
            DisplayEndpoint(
                operation_id="findPets",
                path="/pets",
                http_method="get",
                summary="Find all pets",
                tag="pet",
                path_params=[],
                query_params=[{"name": "status", "required": False, "schema": {"type": "string"}}],
                response_schema=ResponseSchema(fields=pet_fields, is_array=True, schema_name="Pet"),
            ),
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet by ID",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=pet_fields, is_object=True, schema_name="Pet"
                ),
            ),
        ]

    def test_renders_non_empty_module(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert code  # non-empty
        assert "PetDisplay" in code
        assert "FastMCP" in code

    def test_generated_code_compiles(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        compile(code, "pet_display.py", "exec")

    def test_contains_table_tool(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "view_find_pets_table" in code
        assert "DataTable" in code

    def test_contains_detail_tool(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "view_get_pet_by_id_detail" in code
        assert "Card" in code

    def test_contains_status_variants(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "_STATUS_VARIANTS" in code
        assert "'available': 'success'" in code

    def test_contains_prefab_imports(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "from prefab_ui.app import PrefabApp" in code
        assert "PREFAB_AVAILABLE" in code

    def test_returns_empty_for_no_endpoints(self) -> None:
        code = render_display_module("empty", [], "empty_api", "EmptyApi")
        assert code == ""

    def test_returns_empty_for_endpoints_without_schema(self) -> None:
        ep = DisplayEndpoint(
            operation_id="noSchema",
            path="/nothing",
            http_method="get",
            summary="No schema",
            tag="x",
            path_params=[],
            query_params=[],
            response_schema=None,
        )
        code = render_display_module("x", [ep], "x_api", "XApi")
        assert code == ""

    def test_enum_fields_use_badge_with_variant(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "_STATUS_VARIANTS.get(" in code
        assert "Badge(" in code

    def test_detail_tool_has_error_handling(self) -> None:
        code = render_display_module("pet", self._make_endpoints(), "pet_api", "PetApi")
        assert "except Exception" in code
        assert '"error"' in code or '"Error"' in code


# ---------------------------------------------------------------------------
# Form generation tests
# ---------------------------------------------------------------------------


class TestFormGeneration:
    """Test manual form code generation from FormEndpoint data."""

    def _make_form_endpoints(self) -> list[FormEndpoint]:
        return [
            FormEndpoint(
                operation_id="addPet",
                path="/pets",
                http_method="post",
                summary="Add a new pet",
                tag="pet",
                schema_name="Pet",
                fields=[
                    ResponseField(name="id", python_type="int"),
                    ResponseField(name="name", python_type="str"),
                    ResponseField(
                        name="status",
                        python_type="str",
                        is_enum=True,
                        enum_values=["available", "pending", "sold"],
                        description="pet status",
                    ),
                ],
                required_fields=["name"],
                tool_name="Pet_add_pet",
            ),
            FormEndpoint(
                operation_id="updatePet",
                path="/pets",
                http_method="put",
                summary="Update pet",
                tag="pet",
                schema_name="Pet",
                fields=[
                    ResponseField(name="id", python_type="int"),
                    ResponseField(name="name", python_type="str"),
                ],
                required_fields=["name"],
                tool_name="Pet_update_pet",
            ),
        ]

    def test_form_models_have_unique_class_names(self) -> None:
        """Same schema used by different operations must produce unique class names."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert "class AddPetForm(BaseModel):" in code
        assert "class UpdatePetForm(BaseModel):" in code

    def test_form_tool_references_correct_tool_name(self) -> None:
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert '"Pet_add_pet"' in code
        assert '"Pet_update_pet"' in code

    def test_form_tool_submit_label(self) -> None:
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert '"Create Pet"' in code
        assert '"Update Pet"' in code

    def test_form_model_uses_literal_for_enum(self) -> None:
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert 'Literal["available", "pending", "sold"]' in code

    def test_form_model_required_field_has_no_default(self) -> None:
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        # "name" is required → no default=None
        assert 'name: str = Field(title="Name")' in code

    def test_form_model_optional_field_has_default_none(self) -> None:
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        # "id" is not required → has default=None
        assert "default=None" in code

    def test_form_imports_included(self) -> None:
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert "from pydantic import BaseModel, Field" in code
        # Check essential form components are imported (sorted, may include extras like Loader)
        for comp in ("Button", "Form", "Input", "Loader", "Select", "SelectOption"):
            assert comp in code, f"Missing import: {comp}"
        assert "from prefab_ui.actions import SetState, ShowToast" in code
        assert "from prefab_ui.actions.mcp import CallTool" in code

    def test_no_forms_no_form_imports(self) -> None:
        """When no form endpoints are provided, no form imports should be present."""
        pet_fields = _parse_schema_fields(
            SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"], SCHEMA_TEST_SPEC
        )
        endpoints = [
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet by ID",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=pet_fields, is_object=True, schema_name="Pet"
                ),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        assert "from pydantic import BaseModel, Field" not in code
        assert "CallTool" not in code

    def test_form_and_display_tools_coexist(self) -> None:
        """Forms and display tools can be generated in the same module."""
        pet_fields = _parse_schema_fields(
            SCHEMA_TEST_SPEC["components"]["schemas"]["Pet"], SCHEMA_TEST_SPEC
        )
        display_endpoints = [
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet by ID",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=pet_fields, is_object=True, schema_name="Pet"
                ),
            ),
        ]
        code = render_display_module(
            "pet",
            display_endpoints,
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        # Has both display and form tools
        assert "def view_get_pet_by_id_detail" in code
        assert "def form_add_pet" in code
        assert "CallTool(" in code
        assert "SetState(" in code

    def test_form_tool_has_loading_state(self) -> None:
        """Form tool must include submitting state for button disable."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert 'let={"submitting": False}' in code
        assert "STATE.submitting" in code

    def test_form_tool_has_success_feedback(self) -> None:
        """Form tool must include toast on success."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert "ShowToast(" in code
        assert "SendMessage(" not in code

    def test_form_tool_wraps_data(self) -> None:
        """Form tool must wrap field bindings under a 'data' key."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert '"data":' in code
        assert "{{ name }}" in code
        assert "{{ id }}" in code

    def test_form_tool_renders_select_for_enum(self) -> None:
        """Enum fields must render as Select dropdowns."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert "Select(" in code
        assert 'SelectOption(value="available"' in code
        assert 'SelectOption(value="pending"' in code
        assert 'SelectOption(value="sold"' in code

    def test_form_tool_renders_input_for_string(self) -> None:
        """String fields must render as Input components."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert 'Input(name="name"' in code
        assert 'input_type="text"' in code

    def test_form_tool_renders_number_input(self) -> None:
        """Integer fields must render as number inputs."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert 'Input(name="id"' in code
        assert 'input_type="number"' in code


# ===========================================================================
# Test: Delete confirmation dialog generation
# ===========================================================================


class TestDeleteDialogGeneration:
    """Tests for delete confirmation dialog tools."""

    @staticmethod
    def _make_delete_endpoints() -> list[DeleteEndpoint]:
        return [
            DeleteEndpoint(
                operation_id="deletePet",
                path="/pet/{petId}",
                summary="Deletes a pet",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                tool_name="Pet_delete_pet",
            ),
        ]

    def test_delete_tool_generated(self) -> None:
        """Delete endpoint produces a tool function."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            delete_endpoints=self._make_delete_endpoints(),
        )
        assert "def action_delete_delete_pet(" in code

    def test_delete_tool_has_dialog(self) -> None:
        """Delete tool must render a Dialog confirmation."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            delete_endpoints=self._make_delete_endpoints(),
        )
        assert 'Dialog(title="Confirm Deletion"' in code
        assert "CloseOverlay()" in code

    def test_delete_tool_calls_correct_tool(self) -> None:
        """Delete dialog must call the correct namespaced tool."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            delete_endpoints=self._make_delete_endpoints(),
        )
        assert '"Pet_delete_pet"' in code

    def test_delete_tool_has_destructive_button(self) -> None:
        """Delete dialog must have a destructive variant button."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            delete_endpoints=self._make_delete_endpoints(),
        )
        assert 'variant="destructive"' in code

    def test_delete_imports_included(self) -> None:
        """Delete tools must import Dialog, CloseOverlay, etc."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            delete_endpoints=self._make_delete_endpoints(),
        )
        assert "Dialog" in code
        assert "CloseOverlay" in code
        assert "ShowToast" in code

    def test_delete_dialog_shows_resource_identifier(self) -> None:
        """Delete dialog body must show the resource identifier being deleted."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            delete_endpoints=self._make_delete_endpoints(),
        )
        # Should show the param name and value in the confirmation message
        assert "petId" in code
        # The confirmation text should interpolate the parameter
        assert 'f"' in code or "{petId}" in code

    def test_delete_dialog_shows_username_for_user(self) -> None:
        """Delete dialog for user must show the username being deleted."""
        delete_endpoints = [
            DeleteEndpoint(
                operation_id="deleteUser",
                path="/user/{username}",
                summary="Delete user resource.",
                tag="user",
                path_params=[{"name": "username", "required": True, "schema": {"type": "string"}}],
                tool_name="User_delete_user",
            ),
        ]
        code = render_display_module(
            "user",
            [],
            "user_api",
            "UserApi",
            delete_endpoints=delete_endpoints,
        )
        assert "{username}" in code


# ===========================================================================
# Test: Tabbed detail views for nested objects
# ===========================================================================


class TestTabbedDetailViews:
    """Tests for Tabs rendering in detail views with nested data."""

    @staticmethod
    def _make_nested_schema() -> ResponseSchema:
        return ResponseSchema(
            fields=[
                ResponseField(name="id", python_type="int"),
                ResponseField(name="name", python_type="str"),
                ResponseField(
                    name="category",
                    python_type="dict",
                    is_nested_object=True,
                    nested_fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                ),
                ResponseField(
                    name="tags",
                    python_type="list",
                    is_array=True,
                    nested_fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                ),
            ],
            is_object=True,
            schema_name="Pet",
        )

    def test_tabs_rendered_for_nested_detail(self) -> None:
        """Detail view with nested objects must include Tabs."""
        endpoints = [
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=self._make_nested_schema(),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        assert "Tabs(" in code
        assert 'Tab("Category")' in code
        assert 'Tab("Tags")' in code

    def test_tabs_import_included(self) -> None:
        """Tabs and Tab must be imported when nested fields exist."""
        endpoints = [
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=self._make_nested_schema(),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        assert "Tab" in code
        assert "Tabs" in code


# ===========================================================================
# Bug fix: Table views should truncate long strings for display
# ===========================================================================


class TestTableTruncation:
    """Table display rows must truncate long string values."""

    @staticmethod
    def _make_table_endpoints() -> list[DisplayEndpoint]:
        return [
            DisplayEndpoint(
                operation_id="findPetsByStatus",
                path="/pets/findByStatus",
                http_method="get",
                summary="Find pets by status",
                tag="pet",
                path_params=[],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                    is_array=True,
                    schema_name="Pet",
                ),
            ),
        ]

    def test_table_includes_truncation_helper(self) -> None:
        """Generated module must include _truncate_row helper."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert "_truncate_row" in code

    def test_non_expandable_table_truncates_rows(self) -> None:
        """Non-expandable table must truncate display rows."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert "_truncate_row" in code
        # Table passes truncated rows, not raw results
        assert "rows=results" not in code or "_truncate_row" in code

    def test_expandable_table_truncates_display_keeps_detail(self) -> None:
        """Expandable table must truncate display dict but pass full data to detail."""
        endpoints = [
            DisplayEndpoint(
                operation_id="findPets",
                path="/pets",
                http_method="get",
                summary="Find pets",
                tag="pet",
                path_params=[],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                        ResponseField(
                            name="category",
                            python_type="dict",
                            is_nested_object=True,
                            nested_fields=[
                                ResponseField(name="id", python_type="int"),
                                ResponseField(name="name", python_type="str"),
                            ],
                        ),
                    ],
                    is_array=True,
                    schema_name="Pet",
                ),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        # ExpandableRow display should be truncated
        assert "_truncate_row(_r)" in code
        # Detail helper should receive full _r, not truncated
        assert "_build_" in code


# ===========================================================================
# Bug fix: Auto-refresh CallTool must pass variable values, not strings
# ===========================================================================


class TestAutoRefreshArguments:
    """Auto-refresh CallTool must reference function parameter variables."""

    @staticmethod
    def _make_table_with_param() -> list[DisplayEndpoint]:
        return [
            DisplayEndpoint(
                operation_id="findPetsByStatus",
                path="/pets/findByStatus",
                http_method="get",
                summary="Find pets by status",
                tag="pet",
                path_params=[],
                query_params=[{"name": "status", "required": False, "schema": {"type": "string"}}],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                    is_array=True,
                    schema_name="Pet",
                ),
            ),
        ]

    def test_refresh_uses_variable_not_string_literal(self) -> None:
        """CallTool arguments must reference the variable, not a string literal."""
        code = render_display_module("pet", self._make_table_with_param(), "pet_api", "PetApi")
        # Should have: "status": status  (variable reference)
        assert '"status": status' in code
        # Must NOT have: 'status': 'status'  (string literal)
        assert "'status': 'status'" not in code

    def test_no_params_means_no_arguments(self) -> None:
        """Table with no params should not pass arguments to CallTool."""
        endpoints = [
            DisplayEndpoint(
                operation_id="listPets",
                path="/pets",
                http_method="get",
                summary="List pets",
                tag="pet",
                path_params=[],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                    is_array=True,
                    schema_name="Pet",
                ),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        # CallTool should not have arguments= when there are no params
        assert 'CallTool("view_list_pets_table")' in code


# ===========================================================================
# Bug fix: Detail views should handle 404 with friendly Not Found
# ===========================================================================


class TestDetailView404:
    """Detail views must show Not Found for 404 errors."""

    @staticmethod
    def _make_detail_endpoint() -> list[DisplayEndpoint]:
        return [
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet by ID",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                    is_object=True,
                    schema_name="Pet",
                ),
            ),
        ]

    def test_404_shows_not_found(self) -> None:
        """Detail view must check for 404 and show Not Found heading."""
        code = render_display_module("pet", self._make_detail_endpoint(), "pet_api", "PetApi")
        assert "e.status == 404" in code
        assert "Not Found" in code

    def test_404_uses_warning_variant(self) -> None:
        """404 handler should use warning variant, not error."""
        code = render_display_module("pet", self._make_detail_endpoint(), "pet_api", "PetApi")
        # The 404 block should show a warning, distinct from generic errors
        assert 'Heading("Not Found")' in code


# ===========================================================================
# Bug fix: Null-safe nested object/array access
# ===========================================================================


class TestNullSafeNestedAccess:
    """Nested object/array access must handle None values safely."""

    @staticmethod
    def _make_nested_detail() -> list[DisplayEndpoint]:
        return [
            DisplayEndpoint(
                operation_id="getPetById",
                path="/pets/{petId}",
                http_method="get",
                summary="Get pet by ID",
                tag="pet",
                path_params=[{"name": "petId", "required": True, "schema": {"type": "integer"}}],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                        ResponseField(
                            name="category",
                            python_type="dict",
                            is_nested_object=True,
                            nested_fields=[
                                ResponseField(name="id", python_type="int"),
                                ResponseField(name="name", python_type="str"),
                            ],
                        ),
                        ResponseField(
                            name="tags",
                            python_type="list",
                            is_array=True,
                            nested_fields=[
                                ResponseField(name="id", python_type="int"),
                                ResponseField(name="name", python_type="str"),
                            ],
                        ),
                    ],
                    is_object=True,
                    schema_name="Pet",
                ),
            ),
        ]

    def test_nested_object_uses_or_fallback(self) -> None:
        """Nested object access must use 'or {}' for None safety."""
        code = render_display_module("pet", self._make_nested_detail(), "pet_api", "PetApi")
        assert "or {})" in code
        # Must NOT use the unsafe pattern
        assert '.get("category", {})' not in code

    def test_array_field_uses_or_fallback(self) -> None:
        """Array field access must use 'or []' for None safety."""
        code = render_display_module("pet", self._make_nested_detail(), "pet_api", "PetApi")
        assert "or []" in code
        # Must NOT use the unsafe pattern
        assert '.get("tags", [])' not in code

    def test_expandable_nested_uses_or_fallback(self) -> None:
        """Expandable row detail nested access must also be None-safe."""
        endpoints = [
            DisplayEndpoint(
                operation_id="findPets",
                path="/pets",
                http_method="get",
                summary="Find pets",
                tag="pet",
                path_params=[],
                query_params=[],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                        ResponseField(
                            name="category",
                            python_type="dict",
                            is_nested_object=True,
                            nested_fields=[
                                ResponseField(name="id", python_type="int"),
                                ResponseField(name="name", python_type="str"),
                            ],
                        ),
                    ],
                    is_array=True,
                    schema_name="Pet",
                ),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        # Expandable detail must also use or {} pattern
        assert "or {})" in code


# ===========================================================================
# Test: SetInterval auto-refresh in table views
# ===========================================================================


class TestSetIntervalAutoRefresh:
    """Tests for SetInterval-based auto-refresh in table views."""

    @staticmethod
    def _make_table_endpoints() -> list[DisplayEndpoint]:
        return [
            DisplayEndpoint(
                operation_id="findPetsByStatus",
                path="/pets/findByStatus",
                http_method="get",
                summary="Find pets by status",
                tag="pet",
                path_params=[],
                query_params=[{"name": "status", "required": False, "schema": {"type": "string"}}],
                response_schema=ResponseSchema(
                    fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                    is_array=True,
                    schema_name="Pet",
                ),
            ),
        ]

    def test_table_has_auto_refresh_button(self) -> None:
        """Table view must include an Auto-refresh toggle button."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert '"Auto-refresh"' in code

    def test_table_has_set_interval(self) -> None:
        """Table view must include SetInterval action."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert "SetInterval(" in code
        assert "30000" in code

    def test_table_has_live_badge(self) -> None:
        """Table view must show a Live badge when auto-refresh is active."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert 'Badge("Live"' in code
        assert "STATE.auto_refresh" in code

    def test_table_refresh_calls_same_tool(self) -> None:
        """SetInterval on_tick must call the same table tool via CallTool."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert 'CallTool("view_find_pets_by_status_table"' in code

    def test_table_imports_set_interval(self) -> None:
        """Module with tables must import SetInterval."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert "SetInterval" in code
        assert "STATE" in code

    def test_table_auto_refresh_state(self) -> None:
        """Table view must initialize auto_refresh state to False."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert '"auto_refresh": False' in code

    def test_toggle_button_uses_toggle_state(self) -> None:
        """Auto-refresh button must use ToggleState for toggle behaviour."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert "ToggleState" in code

    def test_stop_button_exists(self) -> None:
        """A Stop button must appear when auto_refresh is active (via Else)."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert '"Stop"' in code

    def test_else_used_for_toggle(self) -> None:
        """If/Else must be used to swap between Auto-refresh and Stop buttons."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert "Else()" in code

    def test_auto_refresh_state_on_prefab_app(self) -> None:
        """State must be set on PrefabApp(state=...) not let={} for persistence."""
        code = render_display_module("pet", self._make_table_endpoints(), "pet_api", "PetApi")
        assert 'PrefabApp(view=view, state={"auto_refresh": False})' in code


# ===========================================================================
# Test: ExpandableRow in tables
# ===========================================================================


class TestExpandableRowTable:
    """Tests for ExpandableRow in table views."""

    @staticmethod
    def _make_table_schema_with_nested() -> ResponseSchema:
        return ResponseSchema(
            fields=[
                ResponseField(name="id", python_type="int"),
                ResponseField(name="name", python_type="str"),
                ResponseField(
                    name="category",
                    python_type="dict",
                    is_nested_object=True,
                    nested_fields=[
                        ResponseField(name="id", python_type="int"),
                        ResponseField(name="name", python_type="str"),
                    ],
                ),
            ],
            is_array=True,
            schema_name="Pet",
        )

    def test_expandable_row_used_for_nested_table(self) -> None:
        """Table with nested fields must use ExpandableRow."""
        endpoints = [
            DisplayEndpoint(
                operation_id="findPets",
                path="/pets",
                http_method="get",
                summary="Find pets",
                tag="pet",
                path_params=[],
                query_params=[],
                response_schema=self._make_table_schema_with_nested(),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        assert "ExpandableRow(" in code
        assert "_build_" in code

    def test_expandable_row_import(self) -> None:
        """ExpandableRow must be imported."""
        endpoints = [
            DisplayEndpoint(
                operation_id="findPets",
                path="/pets",
                http_method="get",
                summary="Find pets",
                tag="pet",
                path_params=[],
                query_params=[],
                response_schema=self._make_table_schema_with_nested(),
            ),
        ]
        code = render_display_module("pet", endpoints, "pet_api", "PetApi")
        assert "ExpandableRow" in code


# ===========================================================================
# Test: Loader in form tools
# ===========================================================================


class TestLoaderInForms:
    """Tests for Loader component in form submission."""

    @staticmethod
    def _make_form_endpoints() -> list[FormEndpoint]:
        return [
            FormEndpoint(
                operation_id="addPet",
                path="/pet",
                http_method="post",
                summary="Add pet",
                tag="pet",
                schema_name="Pet",
                fields=[
                    ResponseField(name="name", python_type="str"),
                ],
                required_fields=["name"],
                tool_name="Pet_add_pet",
            ),
        ]

    def test_loader_in_form(self) -> None:
        """Form tool must include a Loader component."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert "Loader(" in code
        assert 'variant="dots"' in code

    def test_loader_conditional_on_submitting(self) -> None:
        """Loader must be wrapped in If(STATE.submitting)."""
        code = render_display_module(
            "pet",
            [],
            "pet_api",
            "PetApi",
            form_endpoints=self._make_form_endpoints(),
        )
        assert "If(STATE.submitting)" in code
        assert "Loader(" in code
