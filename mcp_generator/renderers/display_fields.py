"""
UI rendering helpers for display tool code generation.

Field/table/tab helpers shared by the display widget renderers.
These functions generate Prefab UI code strings for detail fields, tabs,
expandable rows, and other component patterns.
"""

from __future__ import annotations

from ..models import ResponseField

# ---------------------------------------------------------------------------
# Badge variant mapping for common status/enum patterns
# ---------------------------------------------------------------------------
STATUS_VARIANTS: dict[str, str] = {
    "available": "success",
    "active": "success",
    "enabled": "success",
    "approved": "success",
    "delivered": "success",
    "complete": "success",
    "completed": "success",
    "pending": "warning",
    "processing": "warning",
    "in_progress": "warning",
    "placed": "warning",
    "sold": "error",
    "inactive": "error",
    "disabled": "error",
    "deleted": "error",
    "cancelled": "error",
    "rejected": "error",
    "failed": "error",
}


def table_columns_for_fields(fields: list[ResponseField]) -> list[dict[str, str]]:
    """Select which fields to show as table columns (skip deeply nested, arrays)."""
    columns = []
    for f in fields:
        if f.is_array or f.is_nested_object:
            continue
        label = f.name.replace("_", " ").title()
        columns.append({"key": f.name, "label": label})
    return columns


def find_title_field(fields: list[ResponseField]) -> str | None:
    """Find the best field to use as a display title (name, title, username, etc.)."""
    priority = ["name", "title", "username", "display_name", "label", "email"]
    field_names = {f.name for f in fields}
    for candidate in priority:
        if candidate in field_names:
            return candidate
    return None


def render_detail_fields(fields: list[ResponseField], indent: int = 16) -> str:
    """Generate Prefab code lines for flat fields in a detail card.

    Nested objects and arrays are skipped here — they go into tabs.
    """
    pad = " " * indent
    lines = []
    shown = 0
    for _i, f in enumerate(fields):
        if f.is_array or f.is_nested_object:
            continue
        if shown > 0:
            lines.append(f"{pad}Separator()")

        lines.append(f'{pad}with Row(gap=4, align="center", css_class="py-2"):')
        label = f.name.replace("_", " ").title()
        lines.append(
            f'{pad}    Text("{label}", css_class="font-medium text-muted-foreground w-40 shrink-0")'
        )

        if f.is_enum:
            lines.append(f'{pad}    _val = str(result.get("{f.name}", ""))')
            lines.append(
                f'{pad}    Badge(_val, variant=_STATUS_VARIANTS.get(_val.lower(), "outline"))'
            )
        elif f.python_type == "bool":
            lines.append(f'{pad}    _val = result.get("{f.name}", False)')
            lines.append(
                f'{pad}    Badge("Yes" if _val else "No", variant="success" if _val else "outline")'
            )
        elif f.format in ("date-time", "date"):
            lines.append(
                f'{pad}    Text(str(result.get("{f.name}", "")), css_class="font-medium tabular-nums")'
            )
        else:
            lines.append(f'{pad}    Text(str(result.get("{f.name}", "")), css_class="font-medium")')
        shown += 1

    return "\n".join(lines)


def render_detail_tabs(fields: list[ResponseField], indent: int = 8) -> str:
    """Generate Tabs section for nested objects and arrays in a detail view.

    Returns empty string if there are no nested/array fields to tabify.
    """
    nested = [f for f in fields if (f.is_nested_object and f.nested_fields) or f.is_array]
    if not nested:
        return ""

    pad = " " * indent
    lines = []
    lines.append(f'{pad}with Tabs(variant="line"):')

    for f in nested:
        label = f.name.replace("_", " ").title()
        lines.append(f'{pad}    with Tab("{label}"):')

        if f.is_array:
            lines.append(f'{pad}        _items = result.get("{f.name}") or []')
            lines.append(f"{pad}        if _items:")
            lines.append(f'{pad}            Badge(f"{{len(_items)}} items", variant="outline")')
            if f.nested_fields:
                cols = table_columns_for_fields(f.nested_fields)
                col_lines = []
                for c in cols[:5]:
                    col_lines.append(
                        f'{pad}                DataTableColumn(key="{c["key"]}", header="{c["label"]}", sortable=True),'
                    )
                cols_code = "\n".join(col_lines)
                lines.append(f"{pad}            DataTable(")
                lines.append(f"{pad}                rows=_items,")
                lines.append(f"{pad}                columns=[")
                lines.append(cols_code)
                lines.append(f"{pad}                ],")
                lines.append(f"{pad}                search=True,")
                lines.append(f"{pad}            )")
            else:
                lines.append(f"{pad}            for _item in _items:")
                lines.append(f"{pad}                Text(str(_item))")
            lines.append(f"{pad}        else:")
            lines.append(f'{pad}            Muted("No items")')

        elif f.is_nested_object and f.nested_fields:
            sub_val = f'(result.get("{f.name}") or {{}})'
            lines.append(f"{pad}        with Card():")
            lines.append(f'{pad}            with CardContent(css_class="py-4"):')
            sub_shown = 0
            for nf in f.nested_fields:
                if nf.is_array or nf.is_nested_object:
                    continue
                if sub_shown > 0:
                    lines.append(f"{pad}                Separator()")
                nlabel = nf.name.replace("_", " ").title()
                lines.append(
                    f'{pad}                with Row(gap=4, align="center", css_class="py-2"):'
                )
                lines.append(
                    f'{pad}                    Text("{nlabel}", css_class="font-medium text-muted-foreground w-40 shrink-0")'
                )
                lines.append(
                    f'{pad}                    Text(str(({sub_val}).get("{nf.name}", "")), css_class="font-medium")'
                )
                sub_shown += 1

    return "\n".join(lines)


def render_expandable_detail(
    fields: list[ResponseField],
    shown_columns: set[str],
    indent: int = 8,
) -> str:
    """Generate the detail component code for ExpandableRow."""
    pad = " " * indent
    lines = []

    # Show hidden flat fields
    for f in fields:
        if f.is_array or f.is_nested_object:
            continue
        if f.name in shown_columns:
            continue
        label = f.name.replace("_", " ").title()
        lines.append(f'{pad}with Row(gap=4, align="center"):')
        lines.append(
            f'{pad}    Text("{label}", css_class="font-medium text-muted-foreground w-32")'
        )
        if f.is_enum:
            lines.append(f'{pad}    _val = str(row.get("{f.name}", ""))')
            lines.append(
                f'{pad}    Badge(_val, variant=_STATUS_VARIANTS.get(_val.lower(), "outline"))'
            )
        else:
            lines.append(f'{pad}    Text(str(row.get("{f.name}", "")), css_class="font-medium")')

    # Show nested objects
    for f in fields:
        if not f.is_nested_object or not f.nested_fields:
            continue
        label = f.name.replace("_", " ").title()
        lines.append(f'{pad}Muted("{label}")')
        sub_val = f'(row.get("{f.name}") or {{}})'
        for nf in f.nested_fields:
            if nf.is_array or nf.is_nested_object:
                continue
            nlabel = nf.name.replace("_", " ").title()
            lines.append(f'{pad}with Row(gap=4, align="center"):')
            lines.append(
                f'{pad}    Text("{nlabel}", css_class="font-medium text-muted-foreground w-32")'
            )
            lines.append(
                f'{pad}    Text(str(({sub_val}).get("{nf.name}", "")), css_class="font-medium")'
            )

    # Show array fields as counts/badges
    for f in fields:
        if not f.is_array:
            continue
        label = f.name.replace("_", " ").title()
        lines.append(f'{pad}with Row(gap=4, align="center"):')
        lines.append(
            f'{pad}    Text("{label}", css_class="font-medium text-muted-foreground w-32")'
        )
        lines.append(f'{pad}    _arr = row.get("{f.name}") or []')
        lines.append(f'{pad}    Badge(f"{{len(_arr)}} items", variant="outline")')

    if not lines:
        lines.append(f'{pad}Muted("No additional details")')

    return "\n".join(lines)
