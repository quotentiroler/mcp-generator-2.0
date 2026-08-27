"""Every FastMCP symbol the generator emits must be reachable somewhere.

Generated servers import FastMCP behind `try: ... except ImportError: X = None`
so an older FastMCP degrades instead of crashing. That also means a symbol which
has MOVED degrades silently: the feature is still advertised in fastmcp.json, the
config test still passes, and the middleware is quietly None at runtime.

ResponseLimitingMiddleware moved from `middleware.rate_limiting` into its own
`middleware.response_limiting` module in FastMCP 3.2, and response limiting
stopped being applied without anything failing.

A symbol is checked against every module the generator imports it from, because
some are deliberate version-fallback chains (3.2 path first, 3.1 path second) and
only need to resolve once. Symbols behind an uninstalled optional extra, such as
GenerativeUI needing fastmcp[apps], are skipped rather than failed.
"""

import importlib
import re
from collections import defaultdict
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_DIR = PROJECT_ROOT / "mcp_generator"

IMPORT_RE = re.compile(r"^\s*from\s+(fastmcp[\w.]*)\s+import\s+(.+?)\s*$", re.MULTILINE)

# An optional-extra guard raises ImportError with install instructions rather
# than simply being absent.
OPTIONAL_EXTRA_HINTS = ("install with", "requires", "pip install")


def _symbols(clause: str) -> list[str]:
    """Names from an import clause, dropping any `as` alias."""
    names = []
    for part in clause.strip().strip("()").split(","):
        part = part.strip()
        if part and part != "*":
            names.append(part.split(" as ")[0].strip())
    return names


def _collect() -> dict[str, set[str]]:
    """Map each emitted symbol to every module it is imported from."""
    by_symbol: dict[str, set[str]] = defaultdict(set)
    for path in sorted(SOURCE_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for module, clause in IMPORT_RE.findall(text):
            if clause.rstrip().endswith("\\") or clause.count("(") != clause.count(")"):
                continue
            for name in _symbols(clause):
                by_symbol[name].add(module)
    return dict(by_symbol)


EMITTED = _collect()
CASES = sorted((sym, tuple(sorted(mods))) for sym, mods in EMITTED.items())


def test_emitted_imports_were_found():
    """Guard the collector — an empty result would make every case vacuous."""
    assert len(CASES) > 10, f"only found {len(CASES)} fastmcp imports"


@pytest.mark.parametrize(("symbol", "modules"), CASES, ids=[c[0] for c in CASES])
def test_emitted_symbol_is_reachable(symbol: str, modules: tuple[str, ...]):
    """The symbol must resolve from at least one module the generator imports it from."""
    optional_extra: str | None = None
    tried: list[str] = []

    for module in modules:
        try:
            loaded = importlib.import_module(module)
        except ImportError as exc:
            message = str(exc).lower()
            if any(hint in message for hint in OPTIONAL_EXTRA_HINTS):
                optional_extra = f"{module}: {exc}"
            tried.append(f"{module} ({type(exc).__name__})")
            continue

        if hasattr(loaded, symbol):
            return
        tried.append(f"{module} (no attribute {symbol})")

    if optional_extra:
        pytest.skip(f"{symbol} needs an optional FastMCP extra - {optional_extra}")

    pytest.fail(
        f"{symbol} is not reachable from any module the generator imports it from. "
        f"It may have moved between FastMCP versions. Tried: {', '.join(tried)}"
    )


def test_response_limiting_middleware_is_reachable():
    """The regression that motivated this file."""
    from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware

    assert ResponseLimitingMiddleware is not None
