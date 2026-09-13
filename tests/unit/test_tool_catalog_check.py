"""``scripts/checks/tool_catalog_check.py``: the catalog's own gate (WAVE W3).

The check must PASS on the real tree and, more importantly, FAIL on each
defect it exists to catch -- a drifted pin, a framework LLM/MCP/RESTful
import, an eager ``openjiuwen`` import, a registration that skips the
marker-enforcing constructor, and a non-literal registered id. Every negative
control below is a synthetic source tree; the real one is never mutated.

Loaded via ``importlib.util`` for the reason the engineering-base-check tests
give: ``scripts/`` carries no ``__init__.py`` and is not part of the package.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_PATH = REPO_ROOT / "scripts" / "checks" / "tool_catalog_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tool_catalog_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tcc = _load_module()

PACKAGE_ROOT = "src/speech_aware_evidence_acquisition"


def _synthetic(root: Path, tools_source: str, wrappers: dict[str, str]) -> Path:
    (root / f"{PACKAGE_ROOT}/rails/tool_wrappers").mkdir(parents=True, exist_ok=True)
    (root / f"{PACKAGE_ROOT}/rails/tools.py").write_text(tools_source, encoding="utf-8")
    for name, source in wrappers.items():
        (root / f"{PACKAGE_ROOT}/rails/tool_wrappers/{name}").write_text(
            source, encoding="utf-8"
        )
    return root


_CLEAN_TOOLS = '''
"""Synthetic catalog."""
from ..core.base import Registry

TOOL_CATALOG = Registry("tool")


def build_tool_entry(manifest, body):
    return (manifest, body)


def to_tool_card(tool_id):
    from openjiuwen.core.foundation.tool import ToolCard
    return ToolCard(id=tool_id)


TOOL_CATALOG.register("saea-tool-x-v1", build_tool_entry(None, None))
'''


# ---------------------------------------------------------------------------
# The real tree.
# ---------------------------------------------------------------------------


def test_the_real_catalog_passes():
    data = tcc.evaluate(REPO_ROOT)
    assert data["failures"] == []
    assert data["passed"] is True
    # W3 registered the first eight; WAVE R7 added eighteen rails/a2t_*
    # renderers, OWNER016 added two explicit task actions, and OWNER017 adds
    # the corrective-memory Planner action; OWNER023 adds one cached OBS
    # action; native dispatch adds one live OBS action.
    assert len(data["tools"]) == 31
    assert all(row["complete"] and row["pin_ok"] for row in data["tools"])
    assert all(row["pin_ok"] for row in data["additional_pins"])
    assert data["registered_ids"] == sorted(data["registered_ids"])


def test_the_real_toolkit_summary_names_every_task_type():
    data = tcc.evaluate(REPO_ROOT)
    assert sorted(data["toolkits"]) == ["command", "meeting", "tool-call"]
    for roles in data["toolkits"].values():
        assert sorted(roles) == ["observer", "planner", "reviewer"]


# ---------------------------------------------------------------------------
# Negative controls: the framework red lines.
# ---------------------------------------------------------------------------


def test_a_clean_synthetic_tree_reports_nothing(tmp_path):
    root = _synthetic(tmp_path, _CLEAN_TOOLS, {"__init__.py": "", "a.py": "X = 1\n"})
    failures, rows = tcc.check_no_framework_clients(root)
    assert failures == []
    assert len(rows) == 3


def test_an_mcp_import_fails(tmp_path):
    root = _synthetic(
        tmp_path,
        _CLEAN_TOOLS,
        {
            "__init__.py": "",
            "a.py": "from openjiuwen.core.foundation.tool import MCPTool\n",
        },
    )
    failures, _ = tcc.check_no_framework_clients(root)
    assert any("MCPTool" in failure for failure in failures)


def test_a_restful_tool_import_fails(tmp_path):
    root = _synthetic(
        tmp_path,
        _CLEAN_TOOLS,
        {"__init__.py": "", "a.py": "from openjiuwen.core.foundation.tool import RestfulApi\n"},
    )
    failures, _ = tcc.check_no_framework_clients(root)
    assert any("RestfulApi" in failure for failure in failures)


def test_an_llm_client_module_import_fails(tmp_path):
    root = _synthetic(
        tmp_path,
        _CLEAN_TOOLS,
        {"__init__.py": "", "a.py": "import openjiuwen.core.foundation.llm.base\n"},
    )
    failures, _ = tcc.check_no_framework_clients(root)
    assert any("foundation.llm" in failure for failure in failures)


def test_an_eager_framework_import_fails(tmp_path):
    """The D2 zero-dependency gate: a module-level ``openjiuwen`` import
    would break every environment where the framework is absent."""

    eager = _CLEAN_TOOLS.replace(
        "from ..core.base import Registry",
        "from ..core.base import Registry\nfrom openjiuwen.core.foundation.tool import ToolCard",
    )
    root = _synthetic(tmp_path, eager, {"__init__.py": ""})
    failures, _ = tcc.check_no_framework_clients(root)
    assert any("outside" in failure for failure in failures)


def test_the_lazy_framework_import_inside_to_tool_card_is_allowed(tmp_path):
    root = _synthetic(tmp_path, _CLEAN_TOOLS, {"__init__.py": ""})
    failures, rows = tcc.check_no_framework_clients(root)
    assert failures == []
    tools_row = next(row for row in rows if row["module"].endswith("tools.py"))
    assert tools_row["framework_imports"]


# ---------------------------------------------------------------------------
# Negative controls: the system-invoked marker cannot be bypassed.
# ---------------------------------------------------------------------------


def test_a_registration_that_skips_the_builder_fails(tmp_path):
    bypass = _CLEAN_TOOLS.replace(
        'TOOL_CATALOG.register("saea-tool-x-v1", build_tool_entry(None, None))',
        'TOOL_CATALOG.register("saea-tool-x-v1", ToolEntry(None, None))',
    )
    root = _synthetic(tmp_path, bypass, {"__init__.py": ""})
    failures, ids = tcc.check_registrations_enforce_the_marker(root)
    assert any("build_tool_entry" in failure for failure in failures)
    assert ids == ["saea-tool-x-v1"]


def test_a_non_literal_registered_id_fails(tmp_path):
    dynamic = _CLEAN_TOOLS.replace(
        'TOOL_CATALOG.register("saea-tool-x-v1", build_tool_entry(None, None))',
        "TOOL_CATALOG.register(manifest.tool_id, build_tool_entry(None, None))",
    )
    root = _synthetic(tmp_path, dynamic, {"__init__.py": ""})
    failures, ids = tcc.check_registrations_enforce_the_marker(root)
    assert any("string literal" in failure for failure in failures)
    assert ids == []


def test_a_tree_with_no_registration_fails(tmp_path):
    empty = '"""Nothing registered."""\n'
    root = _synthetic(tmp_path, empty, {"__init__.py": ""})
    failures, ids = tcc.check_registrations_enforce_the_marker(root)
    assert any("no TOOL_CATALOG registration" in failure for failure in failures)
    assert ids == []


def test_the_clean_synthetic_registration_passes(tmp_path):
    root = _synthetic(tmp_path, _CLEAN_TOOLS, {"__init__.py": ""})
    failures, ids = tcc.check_registrations_enforce_the_marker(root)
    assert failures == []
    assert ids == ["saea-tool-x-v1"]


# ---------------------------------------------------------------------------
# Negative control: a drifted pin.
# ---------------------------------------------------------------------------


def test_a_drifted_pin_fails():
    """The check re-hashes each wrapped body; a manifest whose pin no longer
    matches its source is the defect a thin-wrapper discipline exists to make
    impossible."""

    from dataclasses import replace

    from speech_aware_evidence_acquisition.rails import tools

    class _Stale:
        @staticmethod
        def catalog_ids():
            return ["saea-tool-slice-encode-v1"]

        @staticmethod
        def resolve_tool(tool_id):
            entry = tools.resolve_tool(tool_id)
            return type(entry)(
                manifest=replace(entry.manifest, pinned_sha256="0" * 64),
                body=entry.body,
            )

        source_sha256 = staticmethod(tools.source_sha256)

    failures, rows = tcc.check_manifests(_Stale)
    assert any("hashes to" in failure for failure in failures)
    assert rows[0]["pin_ok"] is False


def test_a_missing_wrappers_directory_is_an_error(tmp_path):
    import pytest

    with pytest.raises(tcc.ToolCatalogCheckError):
        tcc.check_no_framework_clients(tmp_path)
