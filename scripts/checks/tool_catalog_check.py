#!/usr/bin/env python3
"""Model-free proof that the tool catalog is what it claims to be (WAVE W3).

The catalog (``rails/tools.py``) says four things about every tool, and this
check proves each of them against the tree rather than against a comment:

1. **Every manifest is complete.** Each registered manifest re-validates
   through ``ToolManifest.validate`` -- id prefix, 64-hex pin, non-empty typed
   I/O, a legal cost class / axis / scope / ledger row type, and the
   "bytes changed <-> derivation record named" biconditional in both
   directions. A tool whose id disagrees with its registration literal is an
   error, not a warning.

2. **Every pinned hash matches the wrapped function's source.** The manifest's
   ``source_ref`` is imported and ``inspect.getsource`` re-hashed. A wrapper
   whose body drifted from its pin is exactly the failure a "thin wrapper"
   discipline is supposed to make impossible. A wrapper module may declare
   ``ADDITIONAL_PINNED_SOURCES`` for a second dispatched body (the flagged
   -span tool has two); those are verified identically.

3. **No wrapper reaches a framework LLM client, MCP tool or RESTful tool.**
   An AST scan of ``rails/tools.py`` and every module under
   ``rails/tool_wrappers/`` refuses any import of ``openjiuwen`` outside the
   two lazy framework-surface functions, and refuses the forbidden framework
   names anywhere. The adoption memo's red lines (paid API = 0, no cloud, no
   MCP) become a property of the source text.

4. **The system-invoked marker cannot be bypassed.** Every
   ``TOOL_CATALOG.register(...)`` call in ``rails/tools.py`` must take its
   entry from ``build_tool_entry(...)``, which is the one place the marker is
   enforced; a hand-built ``ToolEntry`` slipped into the registry would
   otherwise carry no marker at all.

Plus the committed default and every committed opt-in toolkit table load, resolve, and cover the registered ids.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read.
The package is imported (the catalog is a runtime object), the framework is
not.

Flags: ``--repo-root``, ``--json``.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

PACKAGE_ROOT = "src/speech_aware_evidence_acquisition"
TOOLS_MODULE_RELPATH = f"{PACKAGE_ROOT}/rails/tools.py"
WRAPPERS_DIR_RELPATH = f"{PACKAGE_ROOT}/rails/tool_wrappers"

#: Framework names that must never be imported by the catalog or a wrapper.
#: The LLM client line, MCP in every spelling the package exports, and the
#: RESTful tool (``docs/readiness/2026-08-08-openjiuwen-adoption.md``: the
#: framework's LLM/model clients and anything network-bound are NEVER
#: instantiated; paid API = 0).
FORBIDDEN_FRAMEWORK_NAMES = (
    "MCPTool",
    "McpClient",
    "McpServerConfig",
    "McpToolCard",
    "OpenApiClient",
    "PlaywrightClient",
    "RestfulApi",
    "RestfulApiCard",
    "SseClient",
    "StdioClient",
    "StreamableHttpClient",
)

#: Framework submodules a catalog module may never import at all.
FORBIDDEN_FRAMEWORK_MODULES = (
    "openjiuwen.core.foundation.llm",
    "openjiuwen.core.foundation.tool.mcp",
    "openjiuwen.core.foundation.tool.service_api",
    "openjiuwen.core.common.clients",
)

#: The only two functions allowed to import ``openjiuwen``, and only inside
#: their own bodies (the D2 zero-dependency gate: the module must import with
#: the framework absent).
LAZY_FRAMEWORK_FUNCTIONS = ("to_tool_card", "to_local_function")

#: The one constructor every registration must pass through.
ENTRY_BUILDER = "build_tool_entry"
CATALOG_REGISTRY_VAR = "TOOL_CATALOG"


class ToolCatalogCheckError(RuntimeError):
    """The check itself cannot run: unreadable source, unimportable package."""


def _read(repo_root: Path, relpath: str) -> str:
    try:
        return (repo_root / relpath).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolCatalogCheckError(f"cannot read {relpath}: {exc}") from exc


def _parse(repo_root: Path, relpath: str) -> ast.Module:
    try:
        return ast.parse(_read(repo_root, relpath), filename=relpath)
    except SyntaxError as exc:
        raise ToolCatalogCheckError(f"cannot parse {relpath}: {exc}") from exc


def _catalog_module_relpaths(repo_root: Path) -> list[str]:
    directory = repo_root / WRAPPERS_DIR_RELPATH
    if not directory.is_dir():
        raise ToolCatalogCheckError(f"{WRAPPERS_DIR_RELPATH} does not exist")
    wrappers = sorted(
        f"{WRAPPERS_DIR_RELPATH}/{path.name}"
        for path in directory.iterdir()
        if path.suffix == ".py"
    )
    return [TOOLS_MODULE_RELPATH, *wrappers]


# ---------------------------------------------------------------------------
# 1 + 2. Manifest completeness and the pinned hashes (runtime).
# ---------------------------------------------------------------------------


def check_manifests(tools_module: Any) -> tuple[list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []

    ids = tools_module.catalog_ids()
    if not ids:
        failures.append("the tool catalog is empty")

    for tool_id in ids:
        entry = tools_module.resolve_tool(tool_id)
        manifest = entry.manifest
        row: dict[str, Any] = {"tool_id": tool_id, "complete": False, "pin_ok": False}
        try:
            manifest.validate()
            row["complete"] = True
        except Exception as exc:  # the catalog's own error type
            failures.append(f"{tool_id}: incomplete manifest: {exc}")
        if manifest.tool_id != tool_id:
            failures.append(
                f"{tool_id}: registered under an id its manifest does not carry "
                f"({manifest.tool_id!r})"
            )
        row["source_ref"] = manifest.source_ref
        row["axis"] = manifest.axis
        row["scope"] = manifest.scope
        row["cost_class"] = manifest.cost_class
        row["ledger_row_type"] = manifest.ledger_row_type
        row["changes_bytes"] = manifest.changes_bytes
        try:
            measured = tools_module.source_sha256(manifest.source_ref)
        except Exception as exc:
            failures.append(f"{tool_id}: cannot hash {manifest.source_ref}: {exc}")
        else:
            row["pinned_sha256"] = manifest.pinned_sha256
            row["measured_sha256"] = measured
            if measured == manifest.pinned_sha256:
                row["pin_ok"] = True
            else:
                failures.append(
                    f"{tool_id}: {manifest.source_ref} hashes to {measured}, not the "
                    f"pinned {manifest.pinned_sha256}"
                )
        if manifest.ledger_row_type == "model-contact":
            failures.append(f"{tool_id}: claims a model contact; the core is not a tool")
        rows.append(row)
    return failures, rows


def check_additional_pins(repo_root: Path, tools_module: Any) -> tuple[list[str], list[dict]]:
    """A wrapper module may pin a SECOND dispatched body (a manifest carries
    exactly one ``source_ref``). Verify each declared extra pin."""

    import importlib

    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    for relpath in _catalog_module_relpaths(repo_root):
        if not relpath.startswith(WRAPPERS_DIR_RELPATH):
            continue
        name = relpath[len(f"{PACKAGE_ROOT}/") : -len(".py")].replace("/", ".")
        module = importlib.import_module(f"speech_aware_evidence_acquisition.{name}")
        extra = getattr(module, "ADDITIONAL_PINNED_SOURCES", {})
        for source_ref, pinned in sorted(extra.items()):
            try:
                measured = tools_module.source_sha256(source_ref)
            except Exception as exc:
                failures.append(f"{relpath}: cannot hash {source_ref}: {exc}")
                continue
            rows.append(
                {
                    "module": relpath,
                    "source_ref": source_ref,
                    "pinned_sha256": pinned,
                    "measured_sha256": measured,
                    "pin_ok": measured == pinned,
                }
            )
            if measured != pinned:
                failures.append(
                    f"{relpath}: {source_ref} hashes to {measured}, not the pinned "
                    f"{pinned}"
                )
    return failures, rows


# ---------------------------------------------------------------------------
# 3. No framework LLM client, MCP or RESTful tool; openjiuwen stays lazy.
# ---------------------------------------------------------------------------


def _import_nodes(tree: ast.Module) -> Iterable[tuple[ast.AST, list[str], str]]:
    """Yield ``(node, imported names, module path)`` for every import."""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node, [alias.name.split(".")[-1]], alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            yield node, [alias.name for alias in node.names], module


def _lazy_function_bodies(tree: ast.Module) -> dict[int, str]:
    """Map every statement line inside an allowed lazy function to its name."""

    lines: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name not in LAZY_FRAMEWORK_FUNCTIONS:
                continue
            end = getattr(node, "end_lineno", node.lineno)
            for line in range(node.lineno, end + 1):
                lines[line] = node.name
    return lines


def check_no_framework_clients(repo_root: Path) -> tuple[list[str], list[dict]]:
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    for relpath in _catalog_module_relpaths(repo_root):
        tree = _parse(repo_root, relpath)
        lazy_lines = _lazy_function_bodies(tree)
        framework_imports: list[str] = []
        for node, names, module in _import_nodes(tree):
            for forbidden in FORBIDDEN_FRAMEWORK_MODULES:
                if module == forbidden or module.startswith(forbidden + "."):
                    failures.append(
                        f"{relpath}:{node.lineno}: imports the forbidden framework "
                        f"module {module!r}"
                    )
            for name in names:
                if name in FORBIDDEN_FRAMEWORK_NAMES:
                    failures.append(
                        f"{relpath}:{node.lineno}: imports the forbidden framework "
                        f"name {name!r} (LLM client / MCP / RESTful tool)"
                    )
            if module == "openjiuwen" or module.startswith("openjiuwen."):
                framework_imports.append(f"{module} @ line {node.lineno}")
                owner = lazy_lines.get(node.lineno)
                if owner is None:
                    failures.append(
                        f"{relpath}:{node.lineno}: imports {module!r} outside "
                        f"{LAZY_FRAMEWORK_FUNCTIONS}; the module must import with the "
                        "framework absent (D2 zero-dependency gate)"
                    )
        rows.append({"module": relpath, "framework_imports": framework_imports})
    return failures, rows


# ---------------------------------------------------------------------------
# 4. Every registration passes through the marker-enforcing constructor.
# ---------------------------------------------------------------------------


def check_registrations_enforce_the_marker(repo_root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    registered_ids: list[str] = []
    tree = _parse(repo_root, TOOLS_MODULE_RELPATH)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "register"
            and isinstance(func.value, ast.Name)
            and func.value.id == CATALOG_REGISTRY_VAR
        ):
            continue
        if len(node.args) != 2:
            failures.append(
                f"{TOOLS_MODULE_RELPATH}:{node.lineno}: "
                f"{CATALOG_REGISTRY_VAR}.register takes (id, entry)"
            )
            continue
        first, second = node.args
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            failures.append(
                f"{TOOLS_MODULE_RELPATH}:{node.lineno}: the registered id must be a "
                "string literal so the engineering base check can read it from source"
            )
        else:
            registered_ids.append(first.value)
        builder = second.func if isinstance(second, ast.Call) else None
        if not (isinstance(builder, ast.Name) and builder.id == ENTRY_BUILDER):
            failures.append(
                f"{TOOLS_MODULE_RELPATH}:{node.lineno}: the registered entry must come "
                f"from {ENTRY_BUILDER}(...), which is where system_invoked is enforced"
            )
    if not registered_ids:
        failures.append(f"{TOOLS_MODULE_RELPATH}: no {CATALOG_REGISTRY_VAR} registration found")
    return failures, sorted(registered_ids)


# ---------------------------------------------------------------------------
# 5. The committed toolkit table.
# ---------------------------------------------------------------------------


def _toolkit_relpaths(repo_root: Path, tools_module: Any) -> list[str]:
    """Return the frozen default followed by every committed toolkit JSON."""

    directory = repo_root / "configs" / "toolkit"
    if not directory.is_dir():
        raise ToolCatalogCheckError("configs/toolkit does not exist")
    default_relpath = str(tools_module.TOOLKIT_CONFIG_RELPATH).replace("\\", "/")
    paths = [
        path.relative_to(repo_root).as_posix()
        for path in directory.iterdir()
        if path.is_file() and path.suffix == ".json"
    ]
    optional = sorted(path for path in paths if path != default_relpath)
    return [default_relpath, *optional]


def _toolkit_summary(table: Any, tools_module: Any) -> tuple[dict[str, Any], set[str]]:
    summary: dict[str, Any] = {}
    offered: set[str] = set()
    for task_type in tools_module.TASK_TYPES:
        toolkit = table.for_task(task_type)
        summary[task_type] = {
            role: list(toolkit.tools_for(role)) for role in tools_module.TOOLKIT_ROLES
        }
        for role in tools_module.TOOLKIT_ROLES:
            offered.update(toolkit.tools_for(role))
    return summary, offered


def check_toolkit_tables(
    repo_root: Path, tools_module: Any
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    """Validate the default and every explicitly committed toolkit table.

    The historical default remains a separate summary. Registered tools need
    appear in at least one valid table, allowing a versioned opt-in table to
    add a capability without changing historical defaults.
    """

    failures: list[str] = []
    default_summary: dict[str, Any] = {}
    table_summaries: dict[str, Any] = {}
    offered_by_valid_table: set[str] = set()
    try:
        relpaths = _toolkit_relpaths(repo_root, tools_module)
    except ToolCatalogCheckError as exc:
        return [str(exc)], default_summary, table_summaries

    default_relpath = str(tools_module.TOOLKIT_CONFIG_RELPATH).replace("\\", "/")
    for relpath in relpaths:
        path = repo_root / relpath
        try:
            table = tools_module.load_toolkit_table(path)
            summary, offered = _toolkit_summary(table, tools_module)
        except Exception as exc:
            failures.append(f"toolkit table {relpath} does not load: {exc}")
            continue
        table_summaries[relpath] = {
            "valid": True,
            "task_types": summary,
        }
        offered_by_valid_table.update(offered)
        if relpath == default_relpath:
            default_summary = summary

    unoffered = sorted(set(tools_module.catalog_ids()) - offered_by_valid_table)
    if unoffered:
        failures.append(f"registered but in no valid toolkit: {unoffered}")
    return failures, default_summary, table_summaries


def check_toolkit_table(repo_root: Path, tools_module: Any) -> tuple[list[str], dict]:
    """Backward-compatible default summary over the complete toolkit check."""

    failures, default_summary, _table_summaries = check_toolkit_tables(
        repo_root, tools_module
    )
    return failures, default_summary


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------


def evaluate(repo_root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(repo_root / "src"))
    try:
        from speech_aware_evidence_acquisition.rails import tools as tools_module
    except ImportError as exc:
        raise ToolCatalogCheckError(f"cannot import the tool catalog: {exc}") from exc

    failures: list[str] = []

    manifest_failures, manifest_rows = check_manifests(tools_module)
    failures.extend(manifest_failures)

    extra_failures, extra_rows = check_additional_pins(repo_root, tools_module)
    failures.extend(extra_failures)

    client_failures, module_rows = check_no_framework_clients(repo_root)
    failures.extend(client_failures)

    marker_failures, registered_ids = check_registrations_enforce_the_marker(repo_root)
    failures.extend(marker_failures)

    if registered_ids and sorted(tools_module.catalog_ids()) != registered_ids:
        failures.append(
            "the registration literals in rails/tools.py do not match the catalog: "
            f"{registered_ids} vs {sorted(tools_module.catalog_ids())}"
        )

    toolkit_failures, toolkit_summary, toolkit_tables = check_toolkit_tables(
        repo_root, tools_module
    )
    failures.extend(toolkit_failures)

    return {
        "schema": "saea-tool-catalog-check-v1",
        "repo_root": str(repo_root),
        "tools": manifest_rows,
        "additional_pins": extra_rows,
        "modules": module_rows,
        "registered_ids": registered_ids,
        "toolkits": toolkit_summary,
        "toolkit_tables": toolkit_tables,
        "failures": failures,
        "passed": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = evaluate(args.repo_root.resolve())
    except ToolCatalogCheckError as exc:
        print(f"tool catalog check: FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for failure in data["failures"]:
        print(f"tool catalog check: FAIL: {failure}")
    if data["failures"]:
        print(f"tool catalog check: FAIL ({len(data['failures'])} finding(s))")
        return 1

    print(
        "tool catalog check: PASS "
        f"({len(data['tools'])} tools, {len(data['additional_pins'])} extra pin(s), "
        f"{len(data['modules'])} module(s) clean of framework clients)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
