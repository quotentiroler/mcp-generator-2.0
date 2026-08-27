"""Assembles a per-tag display module from its widget renderers."""

from __future__ import annotations

from ..models import DeleteEndpoint, DisplayEndpoint, FormEndpoint
from .display_fields import (
    STATUS_VARIANTS,
    table_columns_for_fields,
)
from .display_widgets import (
    _render_delete_tool,
    _render_detail_tool,
    _render_form_tool,
    _render_pydantic_model,
    _render_table_tool,
)


def _build_extra_imports(
    *,
    has_forms: bool,
    has_deletes: bool,
    has_nested: bool,
    has_expandable: bool,
    has_tables: bool,
) -> str:
    """Build extra import block based on which features a module needs."""
    blocks: list[str] = []

    # Collect components, actions, and mcp-actions needed
    components: list[str] = []
    actions: list[str] = []
    mcp_actions: list[str] = []

    if has_forms:
        components.extend(["Button", "Form", "If", "Input", "Loader", "Select", "SelectOption"])
        actions.extend(["SetState", "ShowToast"])
        mcp_actions.append("CallTool")

    if has_deletes:
        components.extend(["Button", "Dialog"])
        actions.append("ShowToast")
        mcp_actions.append("CallTool")

    if has_nested:
        components.extend(["Tabs", "Tab"])

    if has_expandable:
        components.append("ExpandableRow")

    if has_tables:
        components.extend(["Button", "If", "Else"])
        actions.extend(["SetInterval", "ToggleState"])
        mcp_actions.append("CallTool")

    # Pydantic imports (forms only)
    if has_forms:
        blocks.append("from typing import Literal")
        blocks.append("from pydantic import BaseModel, Field")

    # Build the try/except import block
    import_lines: list[str] = []
    if components:
        all_components = sorted(set(components))
        import_lines.append(f"    from prefab_ui.components import {', '.join(all_components)}")
    if actions:
        import_lines.append(f"    from prefab_ui.actions import {', '.join(sorted(set(actions)))}")
    if mcp_actions:
        import_lines.append(
            f"    from prefab_ui.actions.mcp import {', '.join(sorted(set(mcp_actions)))}"
        )
    if has_deletes:
        import_lines.append("    from prefab_ui.actions.ui import CloseOverlay")
    if has_forms or has_tables:
        import_lines.append("    from prefab_ui.rx import STATE")

    if import_lines:
        blocks.append("try:")
        blocks.extend(import_lines)
        blocks.append("except ImportError:")
        blocks.append("    pass")

    if not blocks:
        return ""
    return "\n" + "\n".join(blocks) + "\n"


def render_display_module(
    tag: str,
    endpoints: list[DisplayEndpoint],
    api_var_name: str,
    api_class_name: str,
    form_endpoints: list[FormEndpoint] | None = None,
    delete_endpoints: list[DeleteEndpoint] | None = None,
) -> str:
    """Generate a complete display module file for a tag (e.g. pet_display.py).

    Args:
        tag: The OpenAPI tag (e.g. "pet")
        endpoints: Display endpoints belonging to this tag
        api_var_name: API variable name (e.g. "pet_api")
        api_class_name: API class name (e.g. "PetApi")
        form_endpoints: Optional POST/PUT endpoints for form generation
        delete_endpoints: Optional DELETE endpoints for delete confirmation dialogs
    """
    module_name = tag.title().replace("_", "")

    # Determine which enhanced features are needed by scanning endpoints
    has_nested = False
    has_expandable = False
    has_tables = False
    for ep in endpoints:
        schema = ep.response_schema
        if schema is None:
            continue
        nested = [f for f in schema.fields if f.is_nested_object or f.is_array]
        if nested and schema.is_object:
            has_nested = True
        if schema.is_array:
            has_tables = True
            shown_cols = {c["key"] for c in table_columns_for_fields(schema.fields)}
            extra = any(
                (f.is_nested_object or f.is_array)
                or (not f.is_array and not f.is_nested_object and f.name not in shown_cols)
                for f in schema.fields
            )
            if extra:
                has_expandable = True

    tool_code_blocks = []
    for ep in endpoints:
        schema = ep.response_schema
        if schema is None:
            continue
        if schema.is_array:
            tool_code_blocks.append(_render_table_tool(ep, api_var_name))
        elif schema.is_object:
            tool_code_blocks.append(_render_detail_tool(ep, api_var_name))

    # Generate Pydantic models and form tools
    model_code_blocks = []
    form_tool_blocks = []
    has_forms = False
    if form_endpoints:
        for fe in form_endpoints:
            model_code = _render_pydantic_model(fe)
            if model_code:
                model_code_blocks.append(model_code)
                form_tool_blocks.append(_render_form_tool(fe))
                has_forms = True

    # Generate delete confirmation tools
    delete_tool_blocks = []
    has_deletes = False
    if delete_endpoints:
        for de in delete_endpoints:
            delete_tool_blocks.append(_render_delete_tool(de))
            has_deletes = True

    if not tool_code_blocks and not form_tool_blocks and not delete_tool_blocks:
        return ""

    tools_code = "\n".join(tool_code_blocks)
    models_code = "\n".join(model_code_blocks)
    forms_code = "\n".join(form_tool_blocks)
    deletes_code = "\n".join(delete_tool_blocks)
    variants_repr = repr(STATUS_VARIANTS)

    # Build extra imports based on which features are used
    extra_imports = _build_extra_imports(
        has_forms=has_forms,
        has_deletes=has_deletes,
        has_nested=has_nested,
        has_expandable=has_expandable,
        has_tables=has_tables,
    )

    header = f'''"""
{module_name} Display Tools — API-specific UI views.

Auto-generated from OpenAPI response schemas.
DO NOT EDIT MANUALLY — regenerate using: generate-mcp --enable-apps --generate-ui
"""

import logging
import os
from typing import Any
import sys
from pathlib import Path

from fastmcp import FastMCP

# Add the generated folder to the Python path
generated_path = Path(__file__).parent.parent.parent / "generated_openapi"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

from openapi_py_fetch import ApiClient, ApiException, Configuration
from openapi_client import {api_class_name}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional Prefab imports
# ---------------------------------------------------------------------------
try:
    from prefab_ui.app import PrefabApp
    from prefab_ui.components import (
        Badge,
        Card,
        CardContent,
        Column,
        DataTable,
        DataTableColumn,
        Heading,
        Metric,
        Muted,
        Row,
        Separator,
        Text,
    )
    PREFAB_AVAILABLE = True
except ImportError:
    PREFAB_AVAILABLE = False
{extra_imports}
# Badge variant mapping for status / enum values
_STATUS_VARIANTS = {variants_repr}

mcp = FastMCP("{module_name}Display")
'''

    # The _call_api and _truncate_row helpers use dict comprehension, so avoid f-string
    helper = """
def _call_api(method_name: str, api_instance, **kwargs):
    \"\"\"Call an API method, strip None kwargs, convert result to dict.\"\"\"
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    method = getattr(api_instance, method_name)
    result = method(**filtered)
    if isinstance(result, list):
        return [item.to_dict() if hasattr(item, "to_dict") else item for item in result]
    return result.to_dict() if hasattr(result, "to_dict") else result


def _truncate_row(row: dict, max_len: int = 30) -> dict:
    \"\"\"Truncate long string values for table display.\"\"\"
    return {
        k: (str(v)[:max_len] + "\u2026" if isinstance(v, str) and len(str(v)) > max_len else v)
        for k, v in row.items()
    }

"""

    init_code = f"""
def _get_api():
    \"\"\"Get an API instance using environment-based auth.\"\"\"
    config = Configuration()
    base_url = os.environ.get("API_BASE_URL", "")
    if base_url:
        config.host = base_url
    token = os.environ.get("API_TOKEN", "")
    if token:
        config.access_token = token
    client = ApiClient(config)
    return {api_class_name}(client)

{api_var_name} = _get_api()

# ============================================================================
# Generated display tools
# ============================================================================
"""

    # Assemble: header + helper + init + models + display tools + form tools + delete tools
    parts = [header, helper, init_code]
    if models_code:
        parts.append(
            "\n# ============================================================================\n# Pydantic models for form generation\n# ============================================================================\n"
        )
        parts.append(models_code)
    parts.append(tools_code)
    if forms_code:
        parts.append(
            "\n# ============================================================================\n# Form tools (auto-generated from request body schemas)\n# ============================================================================\n"
        )
        parts.append(forms_code)
    if deletes_code:
        parts.append(
            "\n# ============================================================================\n# Delete confirmation tools\n# ============================================================================\n"
        )
        parts.append(deletes_code)
    return "\n".join(parts) + "\n"
