"""Renders MCP resource templates from GET endpoints."""

from typing import Any

from ..models import ParameterInfo, ResourceSpec
from ..utils import camel_to_snake


def generate_resource_for_endpoint(
    api_var_name: str, resource_endpoint: dict[str, Any], method_name: str
) -> ResourceSpec | None:
    """
    Generate MCP resource template specification from OpenAPI GET endpoint.

    Args:
        api_var_name: API instance variable name (e.g., 'pet_api')
        resource_endpoint: Endpoint spec from OpenAPI (path, params, etc.)
        method_name: Python method name from generated client

    Returns:
        ResourceSpec or None if resource generation not suitable
    """
    path = resource_endpoint["path"]
    operation_id = resource_endpoint["operation_id"]
    path_params = resource_endpoint["path_params"]
    query_params_raw = resource_endpoint["query_params"]

    # Convert OpenAPI path to RFC 6570 URI template
    # /pet/{petId} -> pet://{petId}
    # /store/order/{orderId} -> order://{orderId}

    # Extract resource name from path (use last segment or operation_id)
    # Filter out wildcards (*) which are catch-all routes, not meaningful segments
    path_segments = [
        seg for seg in path.split("/") if seg and not seg.startswith("{") and seg != "*"
    ]

    if not path_segments:
        # Path is only parameters (unusual), use operation_id
        resource_name = operation_id.replace("get", "").replace("_", "-").lower()
    else:
        # Use last meaningful segment
        resource_name = path_segments[-1]

    # Keep original for URI scheme (hyphens/dots are valid in URI schemes)
    uri_scheme = resource_name.lower()
    # Sanitize for Python identifier usage (function name)
    resource_name = camel_to_snake(resource_name)
    if not resource_name:
        resource_name = camel_to_snake(operation_id) or "resource"
    # Fallback URI scheme if original was purely non-alphanumeric
    if not uri_scheme or not any(c.isalnum() for c in uri_scheme):
        uri_scheme = resource_name

    # Build URI template
    # Replace /segment/{param} with scheme://segment/{param}
    uri_path = path.lstrip("/")

    # FastMCP requires at least one parameter in URI templates
    # Check if we have path params OR query params
    has_params = bool(path_params or query_params_raw)

    if not has_params:
        # Skip resources with no parameters - FastMCP will reject them
        return None

    # Add query parameters to URI template (RFC 6570 syntax)
    # Required params: use {?param} syntax
    # Optional params: also use {?param} syntax (they're all query params)
    query_param_names = [qp["name"] for qp in query_params_raw]

    if query_param_names:
        query_str = "{?" + ",".join(query_param_names) + "}"
        uri_template = f"{uri_scheme}://{uri_path}{query_str}"
    elif path_params:
        # Has path params but no query params
        uri_template = f"{uri_scheme}://{uri_path}"
    else:
        # No parameters at all - FastMCP will reject
        return None

    # Build query parameter info
    query_params = []
    for qp in query_params_raw:
        schema = qp.get("schema", {})
        param_type = schema.get("type", "string")

        # Map OpenAPI types to Python type hints
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list[str]",
        }

        python_type = type_map.get(param_type, "str")

        query_params.append(
            ParameterInfo(
                name=qp["name"],
                type_hint=python_type,
                required=qp["required"],
                description=qp.get("description", ""),
                example_json=None,
                is_pydantic=False,
                pydantic_class=None,
            )
        )

    description = resource_endpoint.get("summary", "") or resource_endpoint.get("description", "")

    return ResourceSpec(
        resource_name=resource_name,
        uri_template=uri_template,
        method_name=method_name,
        api_var_name=api_var_name,
        path_params=path_params,
        query_params=query_params,
        description=description,
        mime_type="application/json",
    )


def render_resource(spec: ResourceSpec) -> str:
    """Render resource template function code from specification."""

    def _safe_identifier(name: str) -> str:
        """Sanitize a parameter name to a valid Python identifier."""
        safe = name.replace("-", "_").replace(".", "_")
        if safe.isidentifier() and not __import__("keyword").iskeyword(safe):
            return safe
        return f"param_{safe}"

    # Build function parameters (path params + query params)
    func_params = ["ctx: Context"]

    # Map original param names to safe Python identifiers
    path_param_map: dict[str, str] = {}
    for param in spec.path_params:
        safe = _safe_identifier(param)
        path_param_map[param] = safe
        func_params.append(f"{safe}: str")

    # FastMCP requires ALL query parameters to be optional with default values
    query_param_map: dict[str, str] = {}
    for qparam in spec.query_params:
        safe = _safe_identifier(qparam.name)
        query_param_map[qparam.name] = safe
        func_params.append(f"{safe}: {qparam.type_hint} | None = None")

    # Build method call arguments (use original names for API calls)
    call_args_list = []
    for param in spec.path_params:
        safe = path_param_map[param]
        call_args_list.append(f"{param}={safe}" if param == safe else f"{safe}={safe}")
    for qparam in spec.query_params:
        safe = query_param_map[qparam.name]
        call_args_list.append(f"{qparam.name}={safe}" if qparam.name == safe else f"{safe}={safe}")

    call_args = ", ".join(call_args_list) if call_args_list else ""

    # Build docstring
    param_docs = "\n    ".join([f"{path_param_map[p]}: Path parameter" for p in spec.path_params])
    if spec.query_params:
        param_docs += "\n    " + "\n    ".join(
            [f"{qp.name}: {qp.description or 'Query parameter'}" for qp in spec.query_params]
        )

    docstring = f"""{spec.description}

    Parameters:
        {param_docs}

    URI: {spec.uri_template}
    """

    code = f'''
@mcp.resource("{spec.uri_template}")
async def {spec.resource_name}_resource({", ".join(func_params)}) -> str:
    """
{docstring}
    """
    try:
        # Get authenticated API client from context state
        # ctx.get_state() is async
        openapi_client = await ctx.get_state('openapi_client')
        if not openapi_client:
            raise Exception("API client not available. Authentication middleware may not be configured.")
        if not isinstance(openapi_client, ApiClient):
            raise Exception(f"API client is not valid — expected ApiClient, got {{type(openapi_client).__name__}}.")

        apis = _get_api_instances(openapi_client)
        {spec.api_var_name} = apis['{spec.api_var_name}']

        # Call API method
        response = {spec.api_var_name}.{spec.method_name}({call_args})

        # Guard against accidentally-async API clients returning coroutines
        if asyncio.iscoroutine(response):
            response = await response

        # Convert response to JSON string
        if response is None:
            result = "{{}}"
        elif hasattr(response, 'to_dict') and callable(response.to_dict):
            import json
            result = json.dumps(response.to_dict(), indent=2)
        elif isinstance(response, (dict, list)):
            import json
            result = json.dumps(response, indent=2)
        else:
            result = str(response)

        return result

    except Exception as e:
        await ctx.error(f"Error in {spec.resource_name}_resource: {{str(e)}}")
        raise
'''

    return code
