"""Writes server modules, middleware, apps and display packages."""

from pathlib import Path

from ..config import TEMPLATES_DIR
from ..models import ModuleSpec


def write_server_modules(modules: dict[str, ModuleSpec], output_dir: Path) -> None:
    """Write server modules to the filesystem."""
    output_dir.mkdir(exist_ok=True, parents=True)

    # Write each server module
    for module_spec in modules.values():
        output_file = output_dir / module_spec.filename
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(module_spec.code)
        print(f"   ✅ {module_spec.filename}")

    # Generate __init__.py for servers package
    imports = []
    exports = []

    for module_spec in modules.values():
        module_name = module_spec.filename.replace(".py", "")
        server_var = f"{module_name.replace('_server', '')}_mcp"
        imports.append(f"from .{module_name} import mcp as {server_var}")
        exports.append(f'    "{server_var}",')

    init_content = '"""Servers package for modular MCP servers."""\n'
    init_content += "\n".join(imports) + "\n\n"
    init_content += "__all__ = [\n"
    init_content += "\n".join(exports) + "\n"
    init_content += "]\n"

    init_file = output_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(init_content)
    print("   ✅ __init__.py")


def write_middleware_files(
    middleware_code: str, oauth_code: str, event_store_code: str, output_dir: Path
) -> None:
    """Write middleware files to the filesystem."""
    output_dir.mkdir(exist_ok=True, parents=True)

    # Write authentication middleware
    auth_file = output_dir / "authentication.py"
    with open(auth_file, "w", encoding="utf-8") as f:
        f.write(middleware_code)
    print("   ✅ authentication.py")

    # Write OAuth provider
    oauth_file = output_dir / "oauth_provider.py"
    with open(oauth_file, "w", encoding="utf-8") as f:
        f.write(oauth_code)
    print("   ✅ oauth_provider.py")

    # Write event store
    event_store_file = output_dir / "event_store.py"
    with open(event_store_file, "w", encoding="utf-8") as f:
        f.write(event_store_code)
    print("   ✅ event_store.py")

    # Create __init__.py for middleware package
    init_file = output_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""Middleware package for MCP server."""\n')
        f.write(
            "from .authentication import ApiClientContextMiddleware, JWTAuthenticationBackend, AuthenticatedIdentity\n"
        )
        f.write(
            "from .oauth_provider import build_authentication_stack, create_remote_auth_provider, create_jwt_verifier, RequireScopesMiddleware, create_multi_auth_verifier\n"
        )
        f.write("from .event_store import InMemoryEventStore\n")
        f.write("\n__all__ = [\n")
        f.write('    "ApiClientContextMiddleware",\n')
        f.write('    "JWTAuthenticationBackend",\n')
        f.write('    "AuthenticatedIdentity",\n')
        f.write('    "build_authentication_stack",\n')
        f.write('    "create_remote_auth_provider",\n')
        f.write('    "create_jwt_verifier",\n')
        f.write('    "create_multi_auth_verifier",\n')
        f.write('    "RequireScopesMiddleware",\n')
        f.write('    "InMemoryEventStore",\n')
        f.write("]\n")


def write_main_server(code: str, output_file: Path) -> None:
    """Write main composition server to filesystem."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"✅ Generated main server: {output_file}")


def write_apps_package(output_dir: Path) -> None:
    """Write MCP Apps package (curated display tools) to the filesystem."""
    import shutil

    apps_dir = output_dir / "apps"
    apps_dir.mkdir(exist_ok=True, parents=True)

    # Copy display_tools.py template
    template_path = TEMPLATES_DIR / "display_tools.py"
    dest_path = apps_dir / "display_tools.py"
    shutil.copy2(template_path, dest_path)
    print(
        "   ✅ apps/display_tools.py (show_table, show_detail, show_chart, show_form, show_comparison)"
    )

    # Create __init__.py for apps package
    init_file = apps_dir / "__init__.py"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write('"""MCP Apps package — curated display tools and UI providers."""\n')
        f.write("from .display_tools import mcp as display_tools_mcp\n\n")
        f.write("__all__ = [\n")
        f.write('    "display_tools_mcp",\n')
        f.write("]\n")
    print("   ✅ apps/__init__.py")


def write_display_modules(display_modules: dict[str, str], apps_dir: Path) -> None:
    """Write API-specific display tool modules (e.g. pet_display.py, store_display.py).

    Also updates apps/__init__.py to export the new display modules.
    """
    apps_dir.mkdir(exist_ok=True, parents=True)

    written = []
    for tag, code in display_modules.items():
        filename = f"{tag}_display.py"
        dest = apps_dir / filename
        dest.write_text(code, encoding="utf-8")
        written.append((tag, filename))
        print(f"   ✅ apps/{filename}")

    # Update __init__.py to include display modules
    if written:
        init_file = apps_dir / "__init__.py"
        init_content = init_file.read_text(encoding="utf-8") if init_file.exists() else ""

        new_imports = []
        new_all_entries = []
        for tag, filename in written:
            module = filename.replace(".py", "")
            var_name = f"{tag}_display_mcp"
            import_line = f"from .{module} import mcp as {var_name}"
            if import_line not in init_content:
                new_imports.append(import_line)
                new_all_entries.append(f'    "{var_name}",')

        if new_imports:
            lines = init_content.rstrip().split("\n")
            all_start = None
            all_end = None
            for i, line in enumerate(lines):
                if "__all__" in line:
                    all_start = i
                if all_start is not None and line.strip() == "]":
                    all_end = i
                    break

            if all_start is not None and all_end is not None:
                for imp in new_imports:
                    lines.insert(all_start, imp)
                    all_start += 1
                    all_end += 1
                for entry in new_all_entries:
                    lines.insert(all_end, entry)
                    all_end += 1
            else:
                lines.extend(new_imports)

            init_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"   ✅ apps/__init__.py (updated with {len(written)} display modules)")
