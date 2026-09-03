"""Renders MCP tool functions from introspected client methods."""

import inspect
from typing import Any, get_type_hints

from ..fastmcp_target import FastMCPTarget, resolve_target
from ..models import ParameterInfo, ToolSpec
from ..utils import format_parameter_description, sanitize_name


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
    """Render missing-parameter handling: elicit on 3.x, guard response on 4.x."""
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
    """Render the ApiException branch. 4.x has no ctx.sample to ask for a hint.

    Single braces on purpose: the caller interpolates this block into its own
    f-string, and a value substituted into an f-string is not re-scanned for
    brace escapes. Doubling them here would emit literal "{error_msg}" into the
    generated server instead of the error text.
    """
    if not target.supports_server_sampling:
        return '        raise Exception(f"API Error: {error_msg} (status: {e.status})")'

    return """        # --- Sampling: ask LLM to suggest a fix for API errors ---
        try:
            _sample_result = await ctx.sample(
                f"The API call '{tool_name}' failed with: {error_msg} (status {e.status}). "
                f"Suggest what the user should do to fix this.",
                system_prompt="You are a helpful API debugging assistant. Be concise.",
                max_tokens=200,
            )
            _suggestion = _sample_result.result if hasattr(_sample_result, 'result') else str(_sample_result)
            raise Exception(f"API Error: {error_msg} (status: {e.status})\\n💡 Suggestion: {_suggestion}")
        except Exception as _sample_err:
            if "API Error:" in str(_sample_err):
                raise
            raise Exception(f"API Error: {error_msg} (status: {e.status})")""".replace(
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
        # ctx.get_state() is async
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
