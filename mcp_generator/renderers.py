"""
Code generation and rendering utilities.

Orchestrates template rendering and code generation for MCP servers,
middleware, and OAuth providers.
"""

import inspect
from pathlib import Path
from typing import get_type_hints

from .models import ModuleSpec, ParameterInfo, ToolSpec
from .utils import format_parameter_description, sanitize_name


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
        .replace("{{version}}", str(getattr(api_metadata, "version", "0.1.0")))
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


def generate_server_module(api_var_name: str, api_class) -> ModuleSpec:
    """Generate a single server module for one API class."""
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

    # Footer
    code += f"""

# Generated {tool_count} tools for {api_class_name}
"""

    filename = f"{api_var_name.replace('_api', '')}_server.py"

    return ModuleSpec(
        filename=filename,
        api_var_name=api_var_name,
        api_class_name=api_class_name,
        module_name=module_name,
        tool_count=tool_count,
        code=code,
    )
