"""Shared fixtures for mcp_generator tests."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from mcp_generator.models import (
    ApiMetadata,
    ModuleSpec,
    OAuthConfig,
    OAuthFlowConfig,
    SecurityConfig,
)

# ---------------------------------------------------------------------------
# Minimal OpenAPI specs
# ---------------------------------------------------------------------------

MINIMAL_OPENAPI_SPEC: dict = {
    "openapi": "3.0.3",
    "info": {"title": "Test API", "version": "1.0.0", "description": "A test API"},
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "tags": ["pet"],
                "summary": "List all pets",
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "operationId": "createPet",
                "tags": ["pet"],
                "summary": "Create a pet",
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/users": {
            "get": {
                "operationId": "listUsers",
                "tags": ["user"],
                "summary": "List users",
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
    "tags": [{"name": "pet", "description": "Pet operations"}],
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "required": ["name", "photoUrls"],
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                    "category": {"$ref": "#/components/schemas/Category"},
                    "photoUrls": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "tags": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Tag"},
                    },
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                    },
                },
            },
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                },
            },
            "Tag": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                },
            },
        }
    },
}

OPENAPI_SPEC_WITH_SECURITY: dict = {
    "openapi": "3.0.3",
    "info": {"title": "Secure API", "version": "2.0.0", "description": "Secured API"},
    "paths": {
        "/items": {
            "get": {
                "operationId": "listItems",
                "tags": ["item"],
                "summary": "List items",
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
    "tags": [{"name": "item", "description": "Item ops"}],
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": "https://auth.example.com/token",
                        "scopes": {"read": "Read access", "write": "Write access"},
                    }
                },
            },
            "apiKey": {"type": "apiKey", "in": "header", "name": "x-api-key"},
        }
    },
    "security": [{"bearerAuth": []}, {"oauth2": ["read"]}],
}

OPENAPI_SPEC_API_KEY_ONLY: dict = {
    "openapi": "3.1.0",
    "info": {"title": "Key API", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/search": {
            "get": {
                "operationId": "search",
                "tags": ["search"],
                "summary": "Search",
                "responses": {"200": {"description": "OK"}},
            }
        }
    },
    "components": {
        "securitySchemes": {"apiKey": {"type": "apiKey", "in": "header", "name": "x-api-key"}}
    },
    "security": [{"apiKey": []}],
}


# ---------------------------------------------------------------------------
# Model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_metadata() -> ApiMetadata:
    return ApiMetadata(
        title="Test API",
        description="A test API for unit tests",
        version="1.0.0",
        contact={"email": "test@example.com"},
        license={"name": "MIT"},
        servers=[{"url": "http://localhost:3001"}],
        external_docs={"url": "https://docs.example.com"},
    )


@pytest.fixture
def api_metadata_no_extras() -> ApiMetadata:
    """ApiMetadata without contact/license/external_docs."""
    return ApiMetadata(title="Bare API", version="0.1.0")


@pytest.fixture
def security_config_none() -> SecurityConfig:
    """SecurityConfig with no auth."""
    return SecurityConfig()


@pytest.fixture
def security_config_bearer() -> SecurityConfig:
    """SecurityConfig with bearer + OAuth2."""
    return SecurityConfig(
        schemes={
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "clientCredentials": {
                        "tokenUrl": "https://auth.example.com/token",
                        "scopes": {"read": "Read access"},
                    }
                },
            },
        },
        global_security=[{"bearerAuth": []}, {"oauth2": ["read"]}],
        oauth_config=OAuthConfig(
            scheme_name="oauth2",
            flows={
                "clientCredentials": OAuthFlowConfig(
                    token_url="https://auth.example.com/token",
                    scopes={"read": "Read access"},
                )
            },
            all_scopes={"read": "Read access"},
        ),
        bearer_format="JWT",
        jwks_uri="https://auth.example.com/.well-known/jwks.json",
        issuer="https://auth.example.com",
        audience="backend-api",
    )


@pytest.fixture
def sample_modules() -> dict[str, ModuleSpec]:
    """Two simple ModuleSpec entries."""
    return {
        "pet": ModuleSpec(
            filename="pet_server.py",
            api_var_name="pet_api",
            api_class_name="PetApi",
            module_name="pet",
            tool_count=3,
            code="# pet server code",
        ),
        "user": ModuleSpec(
            filename="user_server.py",
            api_var_name="user_api",
            api_class_name="UserApi",
            module_name="user",
            tool_count=2,
            code="# user server code",
        ),
    }


@pytest.fixture
def write_spec(tmp_path: Path) -> Callable[..., Path]:
    """Write an OpenAPI spec into a temp dir and return the dir."""

    def _write(spec: dict, filename: str = "openapi.json") -> Path:
        (tmp_path / filename).write_text(json.dumps(spec), encoding="utf-8")
        return tmp_path

    return _write


@pytest.fixture
def tmp_spec_dir(write_spec: Callable[..., Path]) -> Path:
    """Temporary directory containing openapi.json with MINIMAL_OPENAPI_SPEC."""
    return write_spec(MINIMAL_OPENAPI_SPEC)
