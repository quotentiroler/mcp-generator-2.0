"""
Code generation and rendering utilities.

Orchestrates template rendering and code generation for MCP servers,
middleware, and OAuth providers.
"""

import inspect
from pathlib import Path
from typing import Any, get_type_hints

from .fastmcp_target import FastMCPTarget, resolve_target
from .models import ModuleSpec, ParameterInfo, ResourceSpec, ToolSpec
from .utils import camel_to_snake, format_parameter_description, sanitize_name


def render_pyproject_template(
    api_metadata: Any,
    security_config: Any,
    server_name: str,
    total_tools: int,
    enable_storage: bool = False,
    enable_apps: bool = False,
    target: FastMCPTarget | None = None,
) -> str:
    """Render the pyproject.toml template with provided values."""
    target = target or resolve_target()
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
        target.dependency_pin(enable_apps=enable_apps),
        "openapi-py-fetch>=0.2.0",
        "httpx>=0.23.0",
        target.pydantic_pin,
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
    if enable_apps:
        packages.append("apps")
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


def render_fastmcp_template(
    api_metadata: Any,
    security_config: Any,
    modules: dict[str, Any],
    total_tools: int,
    server_name: str,
    enable_apps: bool = False,
) -> str:
    """Render the fastmcp.json template with provided values."""
    import json

    template_path = Path(__file__).parent / "templates" / "fastmcp_template.json"
    with open(template_path, encoding="utf-8") as f:
        template = f.read()

    # Build service name from API title
    from .utils import sanitize_server_name

    service_name = sanitize_server_name(api_metadata.title).replace("_", "-")

    # Determine auth settings from security config
    # Only enable JWT validation for bearer schemes or authorizationCode OAuth2 flows
    has_bearer = security_config and security_config.bearer_format
    has_auth_code = (
        security_config
        and security_config.oauth_config
        and "authorizationCode" in security_config.oauth_config.flows
    )
    validate_tokens = "true" if (has_bearer or has_auth_code) else "false"

    rendered = (
        template.replace("{{composition_strategy}}", "mount")
        .replace("{{resource_prefix_format}}", "path")
        .replace("{{validate_tokens}}", validate_tokens)
        .replace("{{service_name}}", f"{service_name}-mcp")
    )

    # Auto-populate oauth_proxy when an authorizationCode flow is detected
    if security_config and security_config.oauth_config:
        auth_code_flow = security_config.oauth_config.flows.get("authorizationCode")
        if auth_code_flow:
            parsed = json.loads(rendered)
            oauth_proxy = parsed["features"]["oauth_proxy"]
            oauth_proxy["enabled"] = True
            if auth_code_flow.authorization_url:
                oauth_proxy["upstream_authorization_endpoint"] = auth_code_flow.authorization_url
            if auth_code_flow.token_url:
                oauth_proxy["upstream_token_endpoint"] = auth_code_flow.token_url
            if auth_code_flow.scopes:
                oauth_proxy["valid_scopes"] = list(auth_code_flow.scopes.keys())
            rendered = json.dumps(parsed, indent=2) + "\n"

    # Auto-enable apps feature when --enable-apps is set
    if enable_apps:
        parsed = json.loads(rendered)
        parsed["features"]["apps"]["enabled"] = True
        rendered = json.dumps(parsed, indent=2) + "\n"

    return rendered


def generate_tool_for_method(
    api_var_name: str,
    method_name: str,
    method: Any,
    tag_name: str = "",
    default_timeout: int | None = 30,
    validate_output: bool | None = None,
    body_schemas: dict[str, dict] | None = None,
    target: FastMCPTarget | None = None,
) -> str:
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

    # Attach request body schema for form data coercion
    if body_schemas and method_name in body_schemas:
        tool_spec.body_schema = body_schemas[method_name]

    # Set tag and timeout from module-level context
    if tag_name:
        tool_spec.tags = [tag_name]
    if default_timeout is not None:
        tool_spec.timeout = default_timeout
    if validate_output is not None:
        tool_spec.validate_output = validate_output

    return _render_tool(tool_spec, target)


def _build_tool_spec(api_var_name: str, method_name: str, method: Any) -> ToolSpec | None:
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

    # Detect deprecated status from method docstring or annotations
    is_deprecated = False
    if doc and ("deprecated" in doc.lower()):
        is_deprecated = True
    if hasattr(method, "__deprecated__"):
        is_deprecated = True

    return ToolSpec(
        tool_name=tool_name,
        method_name=method_name,
        api_var_name=api_var_name,
        parameters=parameters,
        docstring=enhanced_doc,
        has_pydantic_params=has_pydantic,
        deprecated=is_deprecated,
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


def _build_missing_params_block(
    spec: ToolSpec, target: FastMCPTarget, required_literal: str
) -> str:
    """Render the missing-required-parameter handling for the target.

    On FastMCP 3.x the server asks the client for the values via ``ctx.elicit``.
    FastMCP 4 gates elicitation to handshake-era connections, and a default
    ``Client`` negotiates the modern era, so the tool reports what it needs and
    lets the caller supply it — the guard shape that works on both eras.
    """
    detect = f"""        _required = [{required_literal}]
        _locals = locals()
        _missing = [p for p in _required if _locals.get(p) is None]"""

    if target.elicitation_reaches_default_client:
        return f"""        # --- Elicitation: ask user for missing required parameters ---
{detect}
        if _missing:
            try:
                _elicit_msg = f"Missing required parameter(s) for {spec.tool_name}: {{', '.join(_missing)}}. Please provide values."
                _elicit_resp = await ctx.elicit(_elicit_msg, response_type=str)
                if hasattr(_elicit_resp, "action") and _elicit_resp.action != "accept":
                    return {{"error": "User declined to provide required parameters"}}
            except Exception:
                pass  # Elicitation not supported by client — continue with what we have"""

    return f"""        # --- Guard: report missing required parameters to the caller ---
{detect}
        if _missing:
            await ctx.info(f"{spec.tool_name} needs: {{', '.join(_missing)}}")
            return {{
                "error": "missing_required_parameters",
                "missing": _missing,
                "message": f"Provide required parameter(s) for {spec.tool_name}: {{', '.join(_missing)}}.",
            }}"""


def _build_api_error_block(spec: ToolSpec, target: FastMCPTarget) -> str:
    """Render the ApiException branch for the target.

    FastMCP 3.x asks the caller's model for a remediation hint via ``ctx.sample``.
    Server-initiated sampling is removed in FastMCP 4 with no replacement, so the
    error is raised on its own.
    """
    if not target.supports_server_sampling:
        return '        raise Exception(f"API Error: {{error_msg}} (status: {{e.status}})")'

    return """        # --- Sampling: ask LLM to suggest a fix for API errors ---
        try:
            _sample_result = await ctx.sample(
                f"The API call '{tool_name}' failed with: {{error_msg}} (status {{e.status}}). "
                f"Suggest what the user should do to fix this.",
                system_prompt="You are a helpful API debugging assistant. Be concise.",
                max_tokens=200,
            )
            _suggestion = _sample_result.result if hasattr(_sample_result, 'result') else str(_sample_result)
            raise Exception(f"API Error: {{error_msg}} (status: {{e.status}})\\\\n💡 Suggestion: {{_suggestion}}")
        except Exception as _sample_err:
            if "API Error:" in str(_sample_err):
                raise
            raise Exception(f"API Error: {{error_msg}} (status: {{e.status}})")""".replace(
        "{tool_name}", spec.tool_name
    )


def _render_tool(spec: ToolSpec, target: FastMCPTarget | None = None) -> str:
    """Render tool function code from specification."""
    target = target or resolve_target()
    # Build function signature
    func_params = ["ctx: Context"]
    # Detect body parameters (request body for POST/PUT) to support Form.from_model()
    body_param = next((p for p in spec.parameters if p.name == "body"), None)
    has_body = body_param is not None

    for param in spec.parameters:
        if param.name == "body" and has_body:
            # Make body optional so Form.from_model() can submit via data instead
            func_params.append(f"{param.name}: str | None = None")
        elif param.required:
            func_params.append(f"{param.name}: str")
        else:
            func_params.append(f"{param.name}: str | None = None")

    # Add 'data' parameter for Form.from_model() integration
    # When a prefab Form submits via CallTool, it sends {"data": {field: value, ...}}
    if has_body:
        func_params.append("data: str | dict | None = None")

    # Build parameter conversion code for Pydantic models
    param_conversion_code = ""
    pydantic_params = [p for p in spec.parameters if p.is_pydantic]

    # Add data → body conversion for Form.from_model() support
    if has_body:
        if spec.body_schema:
            schema_literal = repr(spec.body_schema)
            param_conversion_code += f"""
        # Form / CallTool sends field values under 'data' key — coerce flat
        # form data into the nested structure the API expects.
        if data and not body:
            import json as _json
            _body_schema = {schema_literal}
            body = _json.dumps(_coerce_form_data(data, _body_schema)) if isinstance(data, dict) else data
"""
        else:
            param_conversion_code += """
        # Form.from_model() sends field values under 'data' key via CallTool
        if data and not body:
            import json as _json
            body = _json.dumps(data) if isinstance(data, dict) else data
"""

    if pydantic_params:
        for param in pydantic_params:
            model_class_name = param.pydantic_class.__name__
            param_conversion_code += f"""
        # Convert JSON string to Pydantic model
        try:
            import json
            {param.name}_data = json.loads({param.name}) if isinstance({param.name}, str) else {param.name}
            {param.name}_obj = {model_class_name}(**{param.name}_data)
        except Exception as e:
            raise _ParameterValidationError(f"Invalid JSON parameter '{param.name}': {{str(e)}}") from e
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
        model_imports = f"\n        from openapi_client.models import {', '.join(set(model_names))}"

    # Build @mcp.tool() decorator with optional kwargs
    tool_decorator_kwargs = []
    if spec.tags:
        tags_str = ", ".join([f'"{t}"' for t in spec.tags])
        tool_decorator_kwargs.append(f"tags=[{tags_str}]")
    if spec.timeout is not None:
        tool_decorator_kwargs.append(f"timeout={spec.timeout}")
    if spec.deprecated:
        tool_decorator_kwargs.append('version="deprecated"')
    if spec.validate_output is not None:
        tool_decorator_kwargs.append(f"validate_output={spec.validate_output}")

    if tool_decorator_kwargs:
        decorator = f"@mcp.tool({', '.join(tool_decorator_kwargs)})"
    else:
        decorator = "@mcp.tool"

    # Build list of required parameter names for elicitation
    # When body has a data alternative (Form.from_model), body is not strictly required
    required_param_names = [
        p.name for p in spec.parameters if p.required and not (p.name == "body" and has_body)
    ]
    required_params_literal = ", ".join([f'"{n}"' for n in required_param_names])

    missing_params_block = _build_missing_params_block(spec, target, required_params_literal)
    api_error_block = _build_api_error_block(spec, target)

    code = f'''
{decorator}
async def {spec.tool_name}({", ".join(func_params)}) -> dict[str, Any]:
    """
    {spec.docstring}
    """
    try:
        # Report progress: starting
        await ctx.report_progress(0, 3, "Validating parameters...")

{missing_params_block}

        # Log tool execution start
        await ctx.info(f"Executing {spec.tool_name}...")

        # Get authenticated API client from context state (set by middleware)
        # FastMCP 3.x: ctx.get_state() is now async
        openapi_client = await ctx.get_state('openapi_client')
        if not openapi_client:
            raise Exception("API client not available. Authentication middleware may not be configured.")
        if not hasattr(openapi_client, 'configuration'):
            raise Exception(f"API client is not valid — expected ApiClient, got {{type(openapi_client).__name__}}.")

        apis = _get_api_instances(openapi_client)
        {spec.api_var_name} = apis['{spec.api_var_name}']{model_imports}{param_conversion_code}

        # Report progress: calling API
        await ctx.report_progress(1, 3, "Calling API...")
        await ctx.debug(f"Calling API: {spec.method_name}")
        response = {spec.api_var_name}.{spec.method_name}({call_args})

        # Guard against accidentally-async API clients returning coroutines
        if asyncio.iscoroutine(response):
            response = await response

        # Convert response to dict - handle various response types
        if response is None:
            result = None
        elif hasattr(response, 'to_dict') and callable(response.to_dict):
            # Pydantic model with to_dict method
            try:
                result = response.to_dict()
            except Exception:
                result = str(response)
        elif isinstance(response, list):
            # List of items - convert each if possible
            result = []
            for item in response:
                if hasattr(item, 'to_dict') and callable(item.to_dict):
                    try:
                        result.append(item.to_dict())
                    except Exception:
                        result.append(str(item))
                else:
                    result.append(item)
        elif isinstance(response, tuple):
            # Tuple response (some APIs return tuples)
            result = list(response) if response else []
        elif isinstance(response, bytes):
            # Binary response - decode to string
            result = response.decode('utf-8', errors='replace')
        elif isinstance(response, (dict, str, int, float, bool)):
            # Primitive types or already a dict
            result = response
        elif hasattr(response, '__next__') or hasattr(response, '__aiter__'):
            # Generator or async iterator - materialise to list
            items = list(response) if hasattr(response, '__next__') else response
            result = []
            for item in items:
                if hasattr(item, 'to_dict') and callable(item.to_dict):
                    try:
                        result.append(item.to_dict())
                    except Exception:
                        result.append(str(item))
                else:
                    result.append(item)
        elif hasattr(response, 'isoformat') and callable(response.isoformat):
            # datetime/date/time objects — convert to ISO format string
            result = response.isoformat()
        else:
            # Fallback: try to convert to dict or use as-is
            try:
                result = dict(response) if hasattr(response, '__dict__') else response
            except Exception:
                result = str(response)

        # Report progress: processing response
        await ctx.report_progress(2, 3, "Processing response...")

        # Log successful completion
        await ctx.info(f"✅ {spec.tool_name} completed successfully")
        await ctx.report_progress(3, 3, "Done")
        return {{"result": result}}

    except _ParameterValidationError as e:
        await ctx.error(f"Parameter error in {spec.tool_name}: {{str(e)}}")
        raise Exception(str(e))
    except ApiException as e:
        error_msg = _format_api_error(e)
        await ctx.error(f"API error in {spec.tool_name}: {{error_msg}}")
{api_error_block}
    except ConnectionError as e:
        await ctx.error(f"Connection error in {spec.tool_name}: {{str(e)}}")
        raise Exception(f"Connection error: could not reach the API backend. {{str(e)}}")
    except TimeoutError as e:
        await ctx.error(f"Timeout error in {spec.tool_name}: {{str(e)}}")
        raise Exception(f"Timeout error: the API request timed out. {{str(e)}}")
    except Exception as e:
        await ctx.error(f"Unexpected error in {spec.tool_name}: {{str(e)}}")
        raise Exception(f"Unexpected error in {spec.tool_name}: {{str(e)}}")

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
        # FastMCP 3.x: ctx.get_state() is now async
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


def generate_server_module(
    api_var_name: str,
    api_class: Any,
    resource_endpoints: list[dict[str, Any]] | None = None,
    validate_output: bool | None = None,
    exclude_methods: set[str] | None = None,
    body_schemas: dict[str, dict] | None = None,
    target: FastMCPTarget | None = None,
) -> ModuleSpec:
    """Generate a single server module for one API class.

    Args:
        api_var_name: API instance variable name (e.g., 'pet_api')
        api_class: API class from generated OpenAPI client
        resource_endpoints: Optional list of GET endpoints to generate as resources
        validate_output: FastMCP 3.1 validate_output flag (None = server default)
        exclude_methods: Method names already generated by earlier modules (first-tag-wins dedup).
            Any method in this set is skipped, and newly generated methods are added to it.
        body_schemas: Mapping of method_name → simplified body schema for form data coercion.
    """
    api_class_name = api_class.__name__
    module_name = api_var_name.replace("_api", "").title().replace("_", "")

    # Header
    code = f'''"""
{module_name} MCP Server Module.

Auto-generated from {api_class_name}.
DO NOT EDIT MANUALLY - regenerate using: python src/mcp_generator.py
"""

import asyncio
import logging
from pathlib import Path
from typing import Any
import sys

from fastmcp import FastMCP, Context

# Add the generated folder to the Python path so we can import openapi_client
generated_path = Path(__file__).parent.parent.parent / "generated_openapi"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

from openapi_py_fetch import ApiClient, ApiException
from openapi_client import {api_class_name}

logger = logging.getLogger(__name__)

# Create FastMCP 3.x Server for this module
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


class _ParameterValidationError(Exception):
    """Raised when a tool parameter cannot be parsed from JSON."""
    pass

'''

    # Embed _coerce_form_data helper when any method in this module has a body schema
    # The helper reshapes flat form key-value pairs into the nested structure the API expects.
    _module_methods = {
        n for n in dir(api_class) if not n.startswith("_") and callable(getattr(api_class, n, None))
    }
    _has_coercible = body_schemas and any(m in body_schemas for m in _module_methods)
    if _has_coercible:
        code += '''
def _coerce_form_data(data: dict, schema: dict) -> dict:
    """Coerce flat form data into the nested structure the API expects.

    Form UIs send flat key-value string pairs, but REST APIs often require
    nested objects, typed arrays, integers, etc.  This function reshapes each
    field according to the body schema extracted from the OpenAPI spec at
    generation time.
    """
    import json as _json

    coerced: dict = {}
    for key, value in data.items():
        field_schema = schema.get(key)
        if field_schema is None:
            coerced[key] = value
            continue

        field_type = field_schema.get("type", "string")

        if field_type == "array":
            items_schema = field_schema.get("items", {})
            items_type = items_schema.get("type", "string")
            if isinstance(value, list):
                coerced[key] = value
            elif isinstance(value, str):
                try:
                    parsed = _json.loads(value)
                    coerced[key] = parsed if isinstance(parsed, list) else [parsed]
                except (ValueError, _json.JSONDecodeError):
                    parts = [v.strip() for v in value.split(",") if v.strip()]
                    if items_type == "object":
                        # Wrap each plain string into an object keyed by the first string property
                        item_props = items_schema.get("properties", {})
                        name_key = next(
                            (pk for pk, pv in item_props.items() if pv.get("type") == "string"),
                            "name",
                        )
                        coerced[key] = [{name_key: p} for p in parts]
                    else:
                        coerced[key] = parts
            else:
                coerced[key] = [value]

        elif field_type == "object":
            props = field_schema.get("properties", {})
            if isinstance(value, dict):
                coerced[key] = value
            elif isinstance(value, str):
                try:
                    parsed = _json.loads(value)
                    coerced[key] = parsed
                except (ValueError, _json.JSONDecodeError):
                    # Wrap plain string into an object using the first string property
                    name_key = next(
                        (pk for pk, pv in props.items() if pv.get("type") == "string"),
                        "name",
                    )
                    coerced[key] = {name_key: value}
            else:
                coerced[key] = value

        elif field_type == "integer":
            try:
                coerced[key] = int(value)
            except (ValueError, TypeError):
                coerced[key] = value

        elif field_type == "number":
            try:
                coerced[key] = float(value)
            except (ValueError, TypeError):
                coerced[key] = value

        elif field_type == "boolean":
            if isinstance(value, str):
                coerced[key] = value.lower() in ("true", "1", "yes")
            else:
                coerced[key] = bool(value)

        else:
            coerced[key] = value

    return coerced

'''

    code += """
# Generated tool functions
# ============================================================================

"""

    # Generate tools for this API
    # Derive tag name from api_var_name (e.g., 'pet_api' -> 'pet')
    tag_name = api_var_name.replace("_api", "")
    tool_count = 0
    for method_name in dir(api_class):
        if method_name.startswith("_"):
            continue

        method = getattr(api_class, method_name)
        if not callable(method):
            continue

        # First-tag-wins dedup: skip methods already generated by an earlier module
        if exclude_methods is not None and method_name in exclude_methods:
            continue

        tool_code = generate_tool_for_method(
            api_var_name,
            method_name,
            method,
            tag_name=tag_name,
            validate_output=validate_output,
            body_schemas=body_schemas,
            target=target,
        )
        if tool_code:
            code += tool_code
            tool_count += 1
            # Record this method so later modules skip it
            if exclude_methods is not None:
                exclude_methods.add(method_name)

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
        tag_name=tag_name,
    )
