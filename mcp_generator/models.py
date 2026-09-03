"""
Data models for MCP generator.

Defines structured data classes for API metadata, security configuration,
and module specifications used throughout the generation process.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiMetadata:
    """API metadata extracted from OpenAPI spec."""

    title: str = "Generated API"
    description: str = ""
    version: str = "0.0.1"
    contact: dict[str, str] = field(default_factory=dict)
    license: dict[str, str] = field(default_factory=dict)
    terms_of_service: str | None = None
    servers: list[dict[str, str]] = field(default_factory=list)
    external_docs: dict[str, str] = field(default_factory=dict)
    tags: list[dict[str, Any]] = field(default_factory=list)
    icon_url: str | None = None  # x-logo or x-icon extension
    icon_emoji: str | None = None  # Optional emoji representation

    @property
    def backend_url(self) -> str:
        """Extract backend URL from servers list."""
        if self.servers and len(self.servers) > 0:
            return self.servers[0].get("url", "http://localhost:3001")
        return "http://localhost:3001"

    @property
    def has_relative_server_url(self) -> bool:
        """Check if the backend URL is relative (no scheme/host)."""
        url = self.backend_url
        return not url.startswith("http://") and not url.startswith("https://")


@dataclass
class OAuthFlowConfig:
    """OAuth2 flow configuration."""

    authorization_url: str | None = None
    token_url: str | None = None
    refresh_url: str | None = None
    scopes: dict[str, str] = field(default_factory=dict)


@dataclass
class OAuthConfig:
    """OAuth2 configuration."""

    scheme_name: str
    flows: dict[str, OAuthFlowConfig] = field(default_factory=dict)
    all_scopes: dict[str, str] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    """Security configuration extracted from OpenAPI spec."""

    schemes: dict[str, Any] = field(default_factory=dict)
    global_security: list[dict[str, list[str]]] = field(default_factory=list)
    default_scopes: list[str] = field(default_factory=list)
    oauth_config: OAuthConfig | None = None
    bearer_format: str | None = None
    jwks_uri: str | None = None
    issuer: str | None = None
    audience: str | None = None

    def get_jwks_uri(self, backend_url: str) -> str:
        """Get JWKS URI with fallback."""
        return self.jwks_uri or f"{backend_url}/.well-known/jwks.json"

    def get_issuer(self, backend_url: str) -> str:
        """Get issuer with fallback."""
        return self.issuer or backend_url

    def get_audience(self) -> str:
        """Get audience with fallback."""
        return self.audience or "backend-api"

    def has_authentication(self) -> bool:
        """Check if any authentication is configured."""
        return bool(self.schemes) or bool(self.oauth_config)


@dataclass
class ModuleSpec:
    """Specification for a generated server module."""

    filename: str
    api_var_name: str
    api_class_name: str
    module_name: str
    tool_count: int
    code: str
    resource_count: int = 0  # Number of resource templates in this module
    tag_name: str = ""  # OpenAPI tag name for this module


@dataclass
class ParameterInfo:
    """Information about a function parameter."""

    name: str
    type_hint: Any
    required: bool
    description: str
    example_json: str | None = None
    is_pydantic: bool = False
    pydantic_class: Any = None


@dataclass
class ToolSpec:
    """Specification for a generated MCP tool."""

    tool_name: str
    method_name: str
    api_var_name: str
    parameters: list[ParameterInfo]
    docstring: str
    has_pydantic_params: bool = False
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False
    timeout: int | None = None  # Tool timeout in seconds
    validate_output: bool | None = None  # FastMCP output validation (None = server default)
    body_schema: dict | None = None  # Simplified request body JSON schema for form data coercion


@dataclass
class ResourceSpec:
    """Specification for a generated MCP resource template."""

    resource_name: str
    uri_template: str
    method_name: str
    api_var_name: str
    path_params: list[str]
    query_params: list[ParameterInfo]
    description: str
    mime_type: str = "application/json"


# ---------------------------------------------------------------------------
# Phase 2: Response schema models for generated display tools
# ---------------------------------------------------------------------------


@dataclass
class ResponseField:
    """A single field in an API response schema."""

    name: str
    python_type: str  # e.g. "str", "int", "bool", "float"
    description: str = ""
    is_enum: bool = False
    enum_values: list[str] = field(default_factory=list)
    is_nested_object: bool = False
    is_array: bool = False
    nested_fields: list["ResponseField"] = field(default_factory=list)
    format: str = ""  # OpenAPI format hint (date-time, email, uri, etc.)


@dataclass
class ResponseSchema:
    """Parsed response schema for an API endpoint."""

    fields: list[ResponseField] = field(default_factory=list)
    is_array: bool = False  # top-level is a list of objects
    is_object: bool = False  # top-level is a single object
    schema_name: str = ""  # e.g. "Pet", "Order" (from $ref name)


@dataclass
class DisplayEndpoint:
    """An API endpoint with enough context to generate a display tool."""

    operation_id: str
    path: str
    http_method: str  # always "get" for display tools
    summary: str
    tag: str
    path_params: list[dict[str, Any]]
    query_params: list[dict[str, Any]]
    response_schema: ResponseSchema | None = None


@dataclass
class FormEndpoint:
    """A POST/PUT endpoint with a request body schema for form generation."""

    operation_id: str
    path: str
    http_method: str  # "post" or "put"
    summary: str
    tag: str
    schema_name: str  # e.g. "Pet", "Order"
    fields: list[ResponseField] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    tool_name: str = ""  # Corresponding MCP tool name e.g. "Pet_add_pet"


@dataclass
class DeleteEndpoint:
    """A DELETE endpoint for generating delete confirmation dialogs."""

    operation_id: str
    path: str
    summary: str
    tag: str
    path_params: list[dict[str, Any]]
    tool_name: str = ""  # Corresponding MCP tool name e.g. "Pet_delete_pet"
