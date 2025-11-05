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
