"""
FastMCP target-version matrix.

Every fact that differs between the FastMCP majors this generator emits for,
so renderers and templates hold no version-specific strings. The 4.x column is
verified against the released fastmcp==4.0.0b3 package, not its upgrade guide:
the transform, auth-provider and event-store paths we emit resolve unchanged,
and fastmcp.experimental.transforms.code_mode survives.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_FASTMCP_TARGET


@dataclass(frozen=True)
class FastMCPTarget:
    """The generation-time contract for one FastMCP major."""

    major: int
    base_pin: str
    pydantic_pin: str
    http_client_module: str
    mcp_error_import: str
    supports_server_sampling: bool
    """``ctx.sample`` exists. Removed in 4.x: no back-channel on 2026-07-28."""

    elicitation_reaches_default_client: bool
    """``ctx.elicit`` reaches a default Client, which negotiates modern on 4.x."""

    tasks_require_extension: bool
    is_prerelease: bool

    def dependency_pin(self, *, enable_apps: bool = False) -> str:
        """The ``fastmcp`` requirement to emit into a generated pyproject."""
        extra = "[apps]" if enable_apps else ""
        return f"fastmcp{extra}{self.base_pin}"

    def render_mcp_error(self, code: str, message: str) -> str:
        """Render an ``McpError`` construction. 4.x rejects the wrapped form."""
        if self.major >= 4:
            return f"McpError(code={code}, message={message})"
        return f"McpError(ErrorData(code={code}, message={message}))"

    @property
    def error_imports(self) -> str:
        """Import lines needed for :meth:`render_mcp_error` to resolve."""
        if self.major >= 4:
            return self.mcp_error_import
        return f"{self.mcp_error_import}\nfrom mcp.types import ErrorData"


# SDK v2 renamed mcp.McpError to MCPError; the fastmcp alias is stable on both.
TARGETS: dict[int, FastMCPTarget] = {
    3: FastMCPTarget(
        major=3,
        base_pin=">=3.2.4,<4.0.0",
        pydantic_pin="pydantic>=2.10.3,<3.0.0",
        http_client_module="httpx",
        mcp_error_import="from mcp import McpError",
        supports_server_sampling=True,
        elicitation_reaches_default_client=True,
        tasks_require_extension=False,
        is_prerelease=False,
    ),
    4: FastMCPTarget(
        major=4,
        base_pin="==4.0.0b3",
        # SDK v2 floors pydantic at 2.12; below it resolution fails outright.
        pydantic_pin="pydantic>=2.12,<3.0.0",
        http_client_module="httpx2",
        mcp_error_import="from fastmcp.exceptions import McpError",
        supports_server_sampling=False,
        elicitation_reaches_default_client=False,
        tasks_require_extension=True,
        is_prerelease=True,
    ),
}

SUPPORTED_TARGETS: tuple[int, ...] = tuple(sorted(TARGETS))


def resolve_target(major: int | None = None) -> FastMCPTarget:
    """Return the target matrix for ``major``, defaulting to the configured one."""
    resolved = DEFAULT_FASTMCP_TARGET if major is None else major
    try:
        return TARGETS[resolved]
    except KeyError:
        supported = ", ".join(str(m) for m in SUPPORTED_TARGETS)
        raise ValueError(
            f"Unsupported FastMCP target major {resolved!r}; supported: {supported}"
        ) from None
