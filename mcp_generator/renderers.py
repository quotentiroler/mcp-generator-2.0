"""
Code generation and rendering utilities.

Orchestrates template rendering and code generation for MCP servers,
middleware, and OAuth providers.
"""

import inspect
from pathlib import Path
from typing import Any, get_type_hints

from .models import ModuleSpec, ParameterInfo, ResourceSpec, ToolSpec
from .utils import camel_to_snake, format_parameter_description, sanitize_name


def render_pyproject_template(
    api_metadata, security_config, server_name, total_tools, enable_storage=False
):
    """Render the pyproject.toml template with provided values."""
    template_path = Path(__file__).parent / "templates" / "pyproject_template.toml"
    with open(template_path, encoding="utf-8") as f:
        template = f.read()
    # Remove any non-comment, non-section-header lines at the top (defensive, in case template is changed)

    lines = template.splitlines()
    cleaned_lines = []
    found_section = False
    for line in lines:
        if line.strip() == "" or line.strip().startswith("#"):
            cleaned_lines.append(line)
        elif line.strip().startswith("["):
            cleaned_lines.append(line)
            found_section = True
        elif not found_section:
            # skip accidental junk at the very top (before first section)
            continue
        else:
            cleaned_lines.append(line)
    template = "\n".join(cleaned_lines)

    # Sanitize version to be PEP 440 compliant
    raw_version = str(getattr(api_metadata, "version", "0.1.0"))
    # Replace invalid dots in local version with + (e.g., 1.0.0.abc123 -> 1.0.0+abc123)
    # PEP 440: local version must use + separator, not .
    import re

    # Match pattern: major.minor.patch followed by optional pre-release, then .something
    # Convert the last dot before local version identifier to +
    version_match = re.match(r"^(\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?)\.([\w]+)$", raw_version)
    if version_match:
        # Has invalid dot before local version - fix it
        sanitized_version = f"{version_match.group(1)}+{version_match.group(2)}"
    else:
        # Check for multiple trailing segments with dots (e.g., 1.0.0-alpha.123.abc.def)
        # Replace last occurrence of dot followed by non-numeric with +
        sanitized_version = re.sub(
            r"\.([a-zA-Z]\w*)$",  # Last dot followed by identifier starting with letter
            r"+\1",
            raw_version,
        )

    # Build dependencies list
    dependencies = [
        "fastmcp>=2.2.0,<3.0.0",
        "httpx>=0.23.0",
        "pydantic>=2.0.0,<3.0.0",
        "python-dateutil>=2.8.2",
        "urllib3>=2.0.0,<3.0.0",
        "typing-extensions>=4.7.1",
        "python-jose[cryptography]>=3.3.0,<4.0.0",
        "uvicorn>=0.20.0",
        "anyio>=3.6.0",
        "annotated-types>=0.4.0",
    ]

    # Add cryptography for storage encryption if storage is enabled
    if enable_storage:
        dependencies.append("cryptography>=42.0.0")

    packages = ["servers"]
    if security_config.has_authentication():
        packages.insert(1, "middleware")
    # Render template
    # Clean description: single-line, escape quotes, remove newlines/markdown
    raw_description = getattr(api_metadata, "description", "MCP Server")
    # Remove newlines and excessive whitespace
    clean_description = " ".join(raw_description.split())
    # Escape double quotes
    clean_description = clean_description.replace('"', "'")
    # Truncate if too long (TOML recommends short descriptions)
    if len(clean_description) > 200:
        clean_description = clean_description[:197] + "..."

    # Render dependencies as TOML array: each line is a quoted string ending with a comma
    dependencies_toml = "\n    ".join([f'"{dep}",' for dep in dependencies])
    return (
        template.replace("{{project_name}}", server_name.replace("_", "-").replace(".", "-"))
        .replace("{{version}}", sanitized_version)
        .replace("{{description}}", clean_description)
        .replace("{{dependencies}}", dependencies_toml)
        .replace("{{script_name}}", f"{server_name}-mcp")
        .replace("{{main_module}}", f"{server_name}_mcp_generated")
        .replace("{{entry_point}}", server_name)
        .replace('packages = ["servers"]', f"packages = {packages}")
    )


def render_fastmcp_template(api_metadata, security_config, modules, total_tools, server_name):
    """Render the fastmcp.json template with provided values."""
    template_path = Path(__file__).parent / "templates" / "fastmcp_template.json"
    with open(template_path, encoding="utf-8") as f:
        template = f.read()
    # Simple replacements for demonstration; expand as needed
    return (
        template.replace("{{composition_strategy}}", "mount")
        .replace("{{resource_prefix_format}}", "path")
        .replace("{{validate_tokens}}", "false")
    )


def generate_tool_for_method(api_var_name: str, method_name: str, method) -> str:
    """Generate MCP tool function for a single API method."""
    # Skip internal methods
    if (
        method_name.startswith("_")
        or "with_http_info" in method_name
        or "without_preload" in method_name
    ):
        return ""

    tool_spec = _build_tool_spec(api_var_name, method_name, method)
    if not tool_spec:
        return ""

    return _render_tool(tool_spec)


def _build_tool_spec(api_var_name: str, method_name: str, method) -> ToolSpec | None:
    """Build tool specification from method introspection."""
    tool_name = sanitize_name(method_name)

    # Get method signature and type hints
    sig = inspect.signature(method)
    try:
        hints = get_type_hints(method)
    except Exception:
        hints = {}

    parameters = []

    for param_name, param in sig.parameters.items():
        if param_name in ["self", "kwargs"]:
            continue

        # Skip internal OpenAPI parameters (FastMCP doesn't allow params starting with _)
        if param_name.startswith("_"):
            continue

        # Get type hint
        param_type = hints.get(param_name, str)

        # Check if this is a Pydantic model parameter
        is_pydantic = hasattr(param_type, "model_fields")

        # Generate enhanced description
        param_desc, example_json = format_parameter_description(param_name, param_type, method)

        # Determine if required (no default value)
        required = param.default == inspect.Parameter.empty

        param_info = ParameterInfo(
            name=param_name,
            type_hint=param_type,
            required=required,
            description=param_desc,
            example_json=example_json,
            is_pydantic=is_pydantic,
            pydantic_class=param_type if is_pydantic else None,
        )
        parameters.append(param_info)

    # Get docstring
    doc = inspect.getdoc(method) or f"Call {method_name}"
    doc_lines = doc.split("\n")
    description = doc_lines[0] if doc_lines else f"Execute {method_name}"

    # Build enhanced docstring
    enhanced_doc = _build_enhanced_docstring(description, parameters, api_var_name, method_name)

    has_pydantic = any(p.is_pydantic for p in parameters)

    return ToolSpec(
        tool_name=tool_name,
        method_name=method_name,
        api_var_name=api_var_name,
        parameters=parameters,
        docstring=enhanced_doc,
        has_pydantic_params=has_pydantic,
    )


def _build_enhanced_docstring(
    description: str, parameters: list[ParameterInfo], api_var_name: str, method_name: str
) -> str:
    """Build enhanced docstring with parameter information."""
    lines = [description, ""]

    if parameters:
        lines.append("Parameters:")
        for param in parameters:
            lines.append(f"    {param.name}: {param.description}")
        lines.append("")

    # Add examples for parameters with JSON schemas
    examples = [(p.name, p.example_json) for p in parameters if p.example_json]
    if examples:
        lines.append("Example JSON for parameters:")
        for param_name, example in examples:
            lines.append(f"  {param_name}:")
            for line in example.split("\n"):
                lines.append(f"    {line}")
        lines.append("")

    lines.append(f"Auto-generated from: {api_var_name}.{method_name}()")

    return "\n    ".join(lines)


def _render_tool(spec: ToolSpec) -> str:
    """Render tool function code from specification."""
    # Build function signature
    func_params = ["ctx: Context"]
    for param in spec.parameters:
        if param.required:
            func_params.append(f"{param.name}: str")
        else:
            func_params.append(f"{param.name}: str | None = None")

    # Build parameter conversion code for Pydantic models
    param_conversion_code = ""
    pydantic_params = [p for p in spec.parameters if p.is_pydantic]

    if pydantic_params:
        for param in pydantic_params:
            model_class_name = param.pydantic_class.__name__
            param_conversion_code += f"""
        # Convert JSON string to Pydantic model
        import json
        {param.name}_data = json.loads({param.name}) if isinstance({param.name}, str) else {param.name}
        {param.name}_obj = {model_class_name}(**{param.name}_data)
"""

    # Build method call arguments - use converted objects for Pydantic params
    call_args_list = []
    for param in spec.parameters:
        if param.is_pydantic:
            call_args_list.append(f"{param.name}={param.name}_obj")
        else:
            call_args_list.append(f"{param.name}={param.name}")
    call_args = ", ".join(call_args_list)

    # Import Pydantic model classes
    model_imports = ""
    if pydantic_params:
        model_names = [p.pydantic_class.__name__ for p in pydantic_params]
        model_imports = f"\n        from generated_openapi.openapi_client.models import {', '.join(set(model_names))}"

    code = f'''
@mcp.tool
async def {spec.tool_name}({", ".join(func_params)}) -> dict[str, Any]:
    """
    {spec.docstring}
    """
    try:
        # Log tool execution start
        await ctx.info(f"Executing {spec.tool_name}...")

        # Get authenticated API client from context state (set by middleware)
        openapi_client = ctx.get_state('openapi_client')
        if not openapi_client:
            raise Exception("API client not available. Authentication middleware may not be configured.")

        apis = _get_api_instances(openapi_client)
        {spec.api_var_name} = apis['{spec.api_var_name}']{model_imports}{param_conversion_code}

        # Log API call
        await ctx.debug(f"Calling API: {spec.method_name}")
        response = {spec.api_var_name}.{spec.method_name}({call_args})

        # Convert response to dict - handle various response types
        if response is None:
            result = None
        elif hasattr(response, 'to_dict') and callable(response.to_dict):
            # Pydantic model with to_dict method
            result = response.to_dict()
        elif isinstance(response, list):
            # List of items - convert each if possible
            result = []
            for item in response:
                if hasattr(item, 'to_dict') and callable(item.to_dict):
                    result.append(item.to_dict())
                else:
                    result.append(item)
        elif isinstance(response, tuple):
            # Tuple response (some APIs return tuples)
            result = list(response) if response else []
        elif isinstance(response, (dict, str, int, float, bool)):
            # Primitive types or already a dict
            result = response
        else:
            # Fallback: try to convert to dict or use as-is
            try:
                result = dict(response) if hasattr(response, '__dict__') else response
            except:
                result = str(response)

        # Log successful completion
        await ctx.info(f"✅ {spec.tool_name} completed successfully")
        return {{"result": result}}

    except ApiException as e:
        error_msg = _format_api_error(e)
        await ctx.error(f"API error in {spec.tool_name}: {{error_msg}}")
        raise Exception(f"API Error: {{error_msg}} (status: {{e.status}})")
    except Exception as e:
        await ctx.error(f"Unexpected error in {spec.tool_name}: {{str(e)}}")
        raise Exception(f"Unexpected error: {{str(e)}}")
'''

    return code


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
    path_segments = [seg for seg in path.split("/") if seg and not seg.startswith("{")]

    if not path_segments:
        # Path is only parameters (unusual), use operation_id
        resource_name = operation_id.replace("get", "").replace("_", "-").lower()
    else:
        # Use last meaningful segment
        resource_name = path_segments[-1]

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
        uri_template = f"{resource_name}://{uri_path}{query_str}"
    elif path_params:
        # Has path params but no query params
        uri_template = f"{resource_name}://{uri_path}"
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

    # Build function parameters (path params + query params)
    func_params = ["ctx: Context"]

    for param in spec.path_params:
        func_params.append(f"{param}: str")

    # FastMCP requires ALL query parameters to be optional with default values
    for qparam in spec.query_params:
        # All query params must have defaults for FastMCP resource templates
        default_val = "None" if "str" in qparam.type_hint else "0"
        func_params.append(f"{qparam.name}: {qparam.type_hint} | None = {default_val}")

    # Build method call arguments
    call_args_list = []
    for param in spec.path_params:
        call_args_list.append(f"{param}={param}")
    for qparam in spec.query_params:
        call_args_list.append(f"{qparam.name}={qparam.name}")

    call_args = ", ".join(call_args_list) if call_args_list else ""

    # Build docstring
    param_docs = "\n    ".join([f"{p}: Path parameter" for p in spec.path_params])
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
        openapi_client = ctx.get_state('openapi_client')
        if not openapi_client:
            raise Exception("API client not available. Authentication middleware may not be configured.")

        apis = _get_api_instances(openapi_client)
        {spec.api_var_name} = apis['{spec.api_var_name}']

        # Call API method
        response = {spec.api_var_name}.{spec.method_name}({call_args})

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


def generate_server_module(
    api_var_name: str, api_class, resource_endpoints: list[dict[str, Any]] | None = None
) -> ModuleSpec:
    """Generate a single server module for one API class.

    Args:
        api_var_name: API instance variable name (e.g., 'pet_api')
        api_class: API class from generated OpenAPI client
        resource_endpoints: Optional list of GET endpoints to generate as resources
    """
    api_class_name = api_class.__name__
    module_name = api_var_name.replace("_api", "").title().replace("_", "")

    # Header
    code = f'''"""
{module_name} MCP Server Module.

Auto-generated from {api_class_name}.
DO NOT EDIT MANUALLY - regenerate using: python src/mcp_generator.py
"""

import logging
from pathlib import Path
from typing import Any
import sys

from fastmcp import FastMCP, Context

# Add the generated folder to the Python path so we can importopenapi_client
generated_path = Path(__file__).parent.parent.parent / "generated_openapi"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

from openapi_client import (
    ApiClient,
    ApiException,
    {api_class_name},
)

logger = logging.getLogger(__name__)

# Create FastMCP 2.x Server for this module
mcp = FastMCP("{module_name}")


def _format_api_error(e: ApiException) -> str:
    """Format API exception into user-friendly error message."""
    if e.status == 401:
        return "Authentication required. User token invalid or missing."
    elif e.status == 403:
        return "Permission denied. Your role does not allow this action."
    elif e.status == 404:
        return "Resource not found."
    elif e.status == 500:
        return "Backend server error."
    else:
        return f"API error (status {{e.status}}): {{e.reason}}"


def _get_api_instances(openapi_client: ApiClient) -> dict:
    """Create API instances with the given client."""
    return {{
        '{api_var_name}': {api_class_name}(openapi_client)
    }}


# Generated tool functions
# ============================================================================

'''

    # Generate tools for this API
    tool_count = 0
    for method_name in dir(api_class):
        if method_name.startswith("_"):
            continue

        method = getattr(api_class, method_name)
        if not callable(method):
            continue

        tool_code = generate_tool_for_method(api_var_name, method_name, method)
        if tool_code:
            code += tool_code
            tool_count += 1

    # Generate resource templates if requested
    resource_count = 0
    if resource_endpoints:
        code += """

# Generated resource templates
# ============================================================================

"""
        for endpoint in resource_endpoints:
            operation_id = endpoint["operation_id"]
            # Convert camelCase operation_id to snake_case method name
            # getPetById -> get_pet_by_id
            method_name = camel_to_snake(operation_id)

            if not hasattr(api_class, method_name):
                continue

            resource_spec = generate_resource_for_endpoint(api_var_name, endpoint, method_name)

            if resource_spec:
                resource_code = render_resource(resource_spec)
                code += resource_code
                resource_count += 1

    # Footer
    code += f"""

# Generated {tool_count} tools and {resource_count} resources for {api_class_name}
"""

    filename = f"{api_var_name.replace('_api', '')}_server.py"

    return ModuleSpec(
        filename=filename,
        api_var_name=api_var_name,
        api_class_name=api_class_name,
        module_name=module_name,
        tool_count=tool_count,
        code=code,
        resource_count=resource_count,
    )
