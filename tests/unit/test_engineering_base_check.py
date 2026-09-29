"""``scripts/checks/engineering_base_check.py``: the ratchet guard against
engineering-base regrowth (study ``CLAUDE.md`` "Engineering base and
experiment rules (owner, 2026-09-03)").

The check is a standalone, stdlib-only script (it must also run under native
Windows Python -- no torch/numpy stack), so it is loaded here via
``importlib.util`` rather than a package import: ``scripts/`` carries no
``__init__.py`` and is not part of the distributed package.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_PATH = REPO_ROOT / "scripts" / "checks" / "engineering_base_check.py"
BASELINE_PATH = REPO_ROOT / "scripts" / "checks" / "engineering_base_baseline.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("engineering_base_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ebc = _load_module()


# ---------------------------------------------------------------------------
# Synthetic mini-repo fixture
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_synthetic_repo(root: Path) -> None:
    """A minimal tree exercising every ratcheted rule at once:

    * ``rails/probes/x.py`` -- R1 offender regardless of content.
    * ``configs/baseline/fake.json`` -- a ``policy`` / ``evidence_source`` /
      ``scorers`` entry that cannot resolve (no canonical ``core.base``
      population file exists in this synthetic repo, so every string value
      is unregistered by construction).
    * ``docs/checks/foo/launcher/`` -- R4 offender. Carries a placeholder
      file (not ``.py``) so it survives a real ``git add -A`` too --
      ``git`` never tracks an empty directory, so an empty ``mkdir`` alone
      would silently vanish from a ``--write-baseline`` capture.
    """

    _write(root / "src/speech_aware_evidence_acquisition/rails/probes/__init__.py", "")
    _write(
        root / "src/speech_aware_evidence_acquisition/rails/probes/x.py",
        '"""A synthetic probe module (no adapter/controller classes here)."""\n',
    )
    _write(
        root / "configs/baseline/fake.json",
        json.dumps(
            {
                "arm": "synthetic",
                "policy": "unknown-policy",
                "evidence_source": "unknown-evidence",
                "scorers": ["unknown-scorer"],
            },
            indent=2,
        ),
    )
    _write(root / "docs/checks/foo/launcher/note.txt", "placeholder\n")


_EXPECTED_OFFENDERS = {
    "probe_modules": [
        "src/speech_aware_evidence_acquisition/rails/probes/x.py",
    ],
    "adapter_subclasses_outside_adapters": [],
    "controller_classes_outside_controllers": [],
    "launcher_dirs": [
        "docs/checks/foo/launcher",
    ],
    "unregistered_config_values": [
        "configs/baseline/fake.json::evidence_source=unknown-evidence",
        "configs/baseline/fake.json::policy=unknown-policy",
        "configs/baseline/fake.json::scorers[0]=unknown-scorer",
    ],
}


def _run(tmp_path: Path, baseline_path: Path, capsys, *, extra_args: list[str] | None = None):
    exit_code = ebc.main(
        [
            "--repo-root",
            str(tmp_path),
            "--baseline",
            str(baseline_path),
            "--json",
            *(extra_args or []),
        ]
    )
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    return exit_code, report


# ---------------------------------------------------------------------------
# 1. Empty baseline -> FAIL with the exact offender strings.
# ---------------------------------------------------------------------------


def test_empty_baseline_fails_with_exact_offenders(tmp_path, capsys):
    _make_synthetic_repo(tmp_path)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"rules": {}}), encoding="utf-8")

    exit_code, report = _run(tmp_path, baseline_path, capsys)

    assert exit_code == 1
    assert report["passed"] is False
    expected_new = {
        "probe_modules: src/speech_aware_evidence_acquisition/rails/probes/x.py",
        "unregistered_config_values: configs/baseline/fake.json::policy=unknown-policy",
        "unregistered_config_values: configs/baseline/fake.json::evidence_source=unknown-evidence",
        "unregistered_config_values: configs/baseline/fake.json::scorers[0]=unknown-scorer",
        "launcher_dirs: docs/checks/foo/launcher",
    }
    assert set(report["new_offenders"]) == expected_new
    assert report["obsolete_baseline_entries"] == []


# ---------------------------------------------------------------------------
# 2. Baseline containing them -> PASS.
# ---------------------------------------------------------------------------


def test_baseline_with_known_offenders_passes(tmp_path, capsys):
    _make_synthetic_repo(tmp_path)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps({"rules": _EXPECTED_OFFENDERS}), encoding="utf-8"
    )

    exit_code, report = _run(tmp_path, baseline_path, capsys)

    assert exit_code == 0
    assert report["passed"] is True
    assert report["new_offenders"] == []
    assert report["obsolete_baseline_entries"] == []


# ---------------------------------------------------------------------------
# 3. A baseline entry that no longer exists -> PASS with a warning.
# ---------------------------------------------------------------------------


def test_obsolete_baseline_entry_warns_but_passes(tmp_path, capsys):
    _make_synthetic_repo(tmp_path)
    rules = {k: list(v) for k, v in _EXPECTED_OFFENDERS.items()}
    rules["probe_modules"].append(
        "src/speech_aware_evidence_acquisition/rails/probes/gone.py"
    )
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"rules": rules}), encoding="utf-8")

    exit_code, report = _run(tmp_path, baseline_path, capsys)

    assert exit_code == 0
    assert report["passed"] is True
    assert report["new_offenders"] == []
    assert report["obsolete_baseline_entries"] == [
        "probe_modules: src/speech_aware_evidence_acquisition/rails/probes/gone.py"
    ]

    # Non-JSON mode prints the WARN line and still exits 0.
    exit_code_text = ebc.main(
        ["--repo-root", str(tmp_path), "--baseline", str(baseline_path)]
    )
    captured = capsys.readouterr()
    assert exit_code_text == 0
    assert (
        "engineering base check: WARN: obsolete baseline entry: probe_modules: "
        "src/speech_aware_evidence_acquisition/rails/probes/gone.py" in captured.out
    )
    assert "engineering base check: PASS" in captured.out


# ---------------------------------------------------------------------------
# 4. R6 (adapter line budget) is never ratcheted: FAIL outright on any
#    offender, baseline or not.
# ---------------------------------------------------------------------------


def test_adapter_line_budget_fails_outright_even_with_full_baseline(tmp_path, capsys):
    _make_synthetic_repo(tmp_path)
    big_content = "\n".join(f"# line {i}" for i in range(300)) + "\n"
    _write(
        tmp_path / "src/speech_aware_evidence_acquisition/rails/adapters/big.py",
        big_content,
    )
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps({"rules": _EXPECTED_OFFENDERS}), encoding="utf-8"
    )

    exit_code, report = _run(tmp_path, baseline_path, capsys)

    assert exit_code == 1
    assert report["passed"] is False
    offenders = report["rules"]["adapter_line_budget"]["offenders"]
    assert offenders == [
        "src/speech_aware_evidence_acquisition/rails/adapters/big.py: 300 lines (limit 260)"
    ]
    assert report["rules"]["adapter_line_budget"]["ratcheted"] is False
    assert (
        "adapter_line_budget: "
        "src/speech_aware_evidence_acquisition/rails/adapters/big.py: 300 lines (limit 260)"
        in report["new_offenders"]
    )


# ---------------------------------------------------------------------------
# 5. --write-baseline reads ONLY the committed tree, never the live one.
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def test_write_baseline_reads_only_the_committed_tree(tmp_path, capsys):
    _make_synthetic_repo(tmp_path)
    try:
        _git(tmp_path, "init", "-q")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        pytest.skip(f"git unavailable in this environment: {exc}")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "synthetic snapshot")

    # An UNCOMMITTED extra probe module must NOT leak into the baseline.
    _write(
        tmp_path / "src/speech_aware_evidence_acquisition/rails/probes/uncommitted.py",
        '"""Not part of HEAD -- must not appear in a committed-tree baseline."""\n',
    )

    baseline_path = tmp_path / "baseline.json"
    exit_code = ebc.main(
        [
            "--repo-root",
            str(tmp_path),
            "--baseline",
            str(baseline_path),
            "--write-baseline",
        ]
    )
    capsys.readouterr()
    assert exit_code == 0

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    head = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert baseline["schema"] == "engineering-base-baseline-v1"
    assert baseline["captured_at_commit"] == head
    assert len(head) == 40
    assert baseline["rules"] == _EXPECTED_OFFENDERS
    assert "adapter_line_budget" not in baseline["rules"]


# ---------------------------------------------------------------------------
# 6. Regex extraction (used everywhere, native Windows included) must agree
#    with what the package actually registers when it IS importable (this
#    repository's own WSL venv) -- study CLAUDE.md "Environment".
# ---------------------------------------------------------------------------


def test_regex_extraction_agrees_with_package_import():
    try:
        from speech_aware_evidence_acquisition.core import base as core_base
        from speech_aware_evidence_acquisition.core import evidence as _core_evidence  # noqa: F401
        from speech_aware_evidence_acquisition.core import policies as _core_policies  # noqa: F401
        from speech_aware_evidence_acquisition.core import scorers as _core_scorers  # noqa: F401
        from speech_aware_evidence_acquisition.rails import kb_policy as _kb_policy  # noqa: F401
        from speech_aware_evidence_acquisition.rails import (
            knowledge_build as _knowledge_build,  # noqa: F401
        )

        # Slice C4a (commit a80eef79) added rails/controllers.py to the
        # check's own CANONICAL_REGISTRY_FILES -- it registers the four
        # phase-program ids into AGENT_CONTROLLERS at import time -- but not
        # to this agreement test's import list, so the regex side saw four
        # ids the import side had never loaded and the two could not agree.
        # Every canonical registry file the check scans must be imported
        # here, or this test compares a full scan against a partial import.
        from speech_aware_evidence_acquisition.rails import (
            controllers as _controllers,  # noqa: F401
        )

        # E6 (2026-09-06): core.base.KNOWLEDGE_PROVIDERS is populated from
        # rails/knowledge_provider.py, now a canonical registration site, so
        # the same rule applies to it.
        from speech_aware_evidence_acquisition.rails import (
            knowledge_provider as _knowledge_provider,  # noqa: F401
        )

        # WAVE W3 (2026-09-08): rails/tools.py is a canonical registration
        # site for TOOL_CATALOG, so the same rule applies to it. The registry
        # object lives in rails.tools rather than core.base (that module's own
        # docstring says why), so it is read from there below.
        from speech_aware_evidence_acquisition.rails import tools as _tools
        from speech_aware_evidence_acquisition.rails import phase_planner as _planner  # noqa: F401
        # Owner decisions 195/196 (2026-09-29): rails/consumption_module.py is
        # the canonical registration site of core.base.CONSUMPTION_MODULES.
        from speech_aware_evidence_acquisition.rails import (
            consumption_module as _consumption_module,  # noqa: F401
        )
        from speech_aware_evidence_acquisition.core.model import (
            native_evidence_projection as _native_evidence_projection,  # noqa: F401
            native_slot_binding_view as _native_slot_binding_view,  # noqa: F401
        )
    except ImportError as exc:
        pytest.skip(f"package not importable in this environment: {exc}")

    reader = ebc.LiveTreeReader(REPO_ROOT)
    regex_registered = ebc.build_registered_names(reader)

    import_registered = {
        "POLICIES": set(core_base.POLICIES.names()),
        "NATIVE_EVIDENCE_PROJECTIONS": set(core_base.NATIVE_EVIDENCE_PROJECTIONS.names()),
        "EVIDENCE_SOURCES": set(core_base.EVIDENCE_SOURCES.names()),
        "SCORERS": set(core_base.SCORERS.names()),
        "AGENT_CONTROLLERS": set(core_base.AGENT_CONTROLLERS.names()),
        "KNOWLEDGE_RANKERS": set(core_base.KNOWLEDGE_RANKERS.names()),
        "KNOWLEDGE_FUSERS": set(core_base.KNOWLEDGE_FUSERS.names()),
        "KNOWLEDGE_BUILDERS": set(core_base.KNOWLEDGE_BUILDERS.names()),
        # E1 (2026-09-05): the phase-program response formats, registered
        # from the same canonical rails/controllers.py file.
        "RESPONSE_FORMATS": set(core_base.RESPONSE_FORMATS.names()),
        # E6 (2026-09-06): the knowledge providers a baseline fragment's
        # phase_supply.provider resolves against.
        "KNOWLEDGE_PROVIDERS": set(core_base.KNOWLEDGE_PROVIDERS.names()),
        # E22 cell (b) (2026-09-06): the per-sample decoding_params.max_tokens
        # rules, registered from the same canonical core/policies.py file.
        "MAX_TOKENS_POLICIES": set(core_base.MAX_TOKENS_POLICIES.names()),
        # Owner Decision 11-B change #1 (2026-09-08): the Reviewer's judges,
        # registered from the same canonical core/policies.py file. Empty
        # until the first judge lands, and the agreement still has to hold --
        # a registry the regex side knows about and the import side does not
        # is exactly the drift this test exists to catch.
        "JUDGES": set(core_base.JUDGES.names()),
        "PHASE_PLANNERS": set(core_base.PHASE_PLANNERS.names()),
        # Stage-3 iteration 3 (2026-09-24): the row-level supply-application
        # policies a stage3-deltas ``context_supply.<node>.scenario_gate.policy``
        # resolves against, registered from the same canonical
        # rails/knowledge_provider.py file as the delta provider ids.
        "STAGE3_SUPPLY_GATE_POLICIES": set(core_base.STAGE3_SUPPLY_GATE_POLICIES.names()),
        # WAVE W3 (2026-09-08): the pinned, system-invoked tool catalog a
        # ``tools`` list in configs/ resolves against.
        "TOOL_CATALOG": set(_tools.TOOL_CATALOG.names()),
        # Owner decisions 195/196 (2026-09-29): the evidence-consumption
        # module a native_episode.consumption_module.module_id resolves in.
        "CONSUMPTION_MODULES": set(core_base.CONSUMPTION_MODULES.names()),
    }

    assert regex_registered == import_registered


def test_a_per_sample_max_tokens_policy_id_must_resolve(tmp_path):
    """E22 cell (b) (2026-09-06): ``decoding_params.max_tokens`` may be a
    per-sample RULE OBJECT, and its ``policy`` id resolves in
    ``core.base.MAX_TOKENS_POLICIES`` like every other component id a config
    declares.

    Matched by PATH rather than by bare key name, which this test pins: the
    top-level ``"policy": "fixed"`` of an arm program is still checked against
    ``POLICIES`` and is NOT dragged into the max-tokens registry, and a plain
    integer ``max_tokens`` declares no id at all.
    """

    _write(
        tmp_path / "configs/model/known.json",
        json.dumps(
            {
                "decoding_params": {
                    "max_tokens": {"policy": "duration-proportional-v1", "alpha": 1.5}
                }
            }
        ),
    )
    _write(
        tmp_path / "configs/model/unknown.json",
        json.dumps({"decoding_params": {"max_tokens": {"policy": "cap-by-vibes"}}}),
    )
    _write(
        tmp_path / "configs/model/plain.json",
        json.dumps({"decoding_params": {"temperature": 0, "max_tokens": 1024}}),
    )
    _write(
        tmp_path / "configs/baseline/arm.json",
        json.dumps({"arm": "a", "policy": "fixed", "scorers": []}),
    )

    registered = {var: set() for var in ebc.ALL_REGISTRY_VARS}
    registered["MAX_TOKENS_POLICIES"] = {"duration-proportional-v1"}
    registered["POLICIES"] = {"fixed"}
    offenders, keys_found = ebc.rule_unregistered_config_values(
        ebc.LiveTreeReader(tmp_path), registered
    )

    assert offenders == [
        "configs/model/unknown.json::decoding_params.max_tokens.policy=cap-by-vibes"
    ]
    assert "decoding_params.max_tokens.policy" in keys_found
    assert "policy" in keys_found


# --- WAVE W3 (tool catalog, 2026-09-08) ------------------------------------


def test_a_toolkit_tools_list_must_resolve_in_the_tool_catalog(tmp_path):
    """Every ``tools`` LIST anywhere under ``configs/`` names catalog ids and
    must resolve in ``rails.tools.TOOL_CATALOG``.

    Two things this test pins beside the happy path. The scan covers ALL of
    ``configs/``, not just the baseline/experiment fragment dirs, because a
    toolkit table is neither. And a ``tools`` OBJECT is skipped: the
    Audio2Tool construction targets under ``configs/knowledge/`` already carry
    one, whose keys are the carrier's own 152 function names -- task payload,
    not catalog ids -- and turning that into an offender would be checking the
    wrong object.
    """

    _write(
        tmp_path / "configs/toolkit/task-toolkits-v1.json",
        json.dumps(
            {
                "toolkits": {
                    "meeting": {
                        "observer": {"tools": ["saea-tool-known-v1"]},
                        "reviewer": {"tools": ["saea-tool-unknown-v1"]},
                    }
                }
            }
        ),
    )
    _write(
        tmp_path / "configs/knowledge/a2t/targets.json",
        json.dumps({"targets": [{"tools": {"getLightState": {"note": "payload"}}}]}),
    )

    registered = {var: set() for var in ebc.ALL_REGISTRY_VARS}
    registered["TOOL_CATALOG"] = {"saea-tool-known-v1"}
    offenders, keys_found = ebc.rule_unregistered_tool_ids(
        ebc.LiveTreeReader(tmp_path), registered
    )

    assert offenders == [
        "configs/toolkit/task-toolkits-v1.json::"
        "toolkits.meeting.reviewer.tools[0]=saea-tool-unknown-v1"
    ]
    assert keys_found == ["tools"]


def test_a_non_string_tool_entry_is_an_offender(tmp_path):
    _write(
        tmp_path / "configs/toolkit/broken.json",
        json.dumps({"toolkits": {"command": {"observer": {"tools": [7]}}}}),
    )
    registered = {var: set() for var in ebc.ALL_REGISTRY_VARS}
    offenders, _ = ebc.rule_unregistered_tool_ids(ebc.LiveTreeReader(tmp_path), registered)
    assert offenders == [
        "configs/toolkit/broken.json::toolkits.command.observer.tools[0]=7"
    ]


# --- end WAVE W3 -----------------------------------------------------------


# ---------------------------------------------------------------------------
# 7. The real check against the real repo with the committed baseline must
#    PASS or only WARN; a FAIL is tolerated only insofar as every offending
#    path is explained by a currently-uncommitted edit (other agents are
#    concurrently editing this working tree -- expected, per this slice's
#    own hard rules).
# ---------------------------------------------------------------------------


def _offender_path(offender: str) -> str:
    """The leading repo-relative path out of an offender string, whichever
    of the two separators (``"::"`` for R1-R5, ``": "`` for R6's
    ``"<path>: <n> lines (limit ...)"``) appears first."""

    cut = len(offender)
    for sep in ("::", ": "):
        idx = offender.find(sep)
        if idx != -1:
            cut = min(cut, idx)
    return offender[:cut]


def _explained_by_dirty_tree(offending_path: str, dirty_paths: set[str]) -> bool:
    if offending_path in dirty_paths:
        return True
    prefix = offending_path.rstrip("/") + "/"
    if any(dirty.startswith(prefix) for dirty in dirty_paths):
        return True
    return any(offending_path.startswith(dirty.rstrip("/") + "/") for dirty in dirty_paths)


def test_real_repo_passes_or_warns_only_given_committed_baseline(capsys):
    if not BASELINE_PATH.exists():
        pytest.fail(f"committed baseline missing: {BASELINE_PATH}")

    exit_code = ebc.main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--baseline",
            str(BASELINE_PATH),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    if report["passed"]:
        assert exit_code == 0
        return

    status = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    dirty_paths: set[str] = set()
    for line in status.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        dirty_paths.add(path.strip('"'))

    unexplained = sorted(
        item
        for item in report["new_offenders"]
        if not _explained_by_dirty_tree(_offender_path(item.split(": ", 1)[-1]), dirty_paths)
    )
    assert not unexplained, (
        "engineering base check FAILed on paths not explained by concurrent "
        f"uncommitted edits: {unexplained}; dirty paths were {sorted(dirty_paths)}"
    )


# ---------------------------------------------------------------------------
# The ``judges`` rule (owner Decision 11-B change #1, 2026-09-08): every
# judge id a config declares must resolve in ``core.base.JUDGES``, at any
# depth -- today under a baseline fragment's ``phase_review`` block.
# ---------------------------------------------------------------------------


def _make_judges_repo(root: Path, *, judge_ids: list[str], registered: list[str]) -> None:
    """A synthetic tree whose ONLY offender source is the ``judges`` rule."""

    registrations = "\n".join(
        f'JUDGES.register("{judge_id}", object())' for judge_id in registered
    )
    _write(
        root / "src/speech_aware_evidence_acquisition/core/policies.py",
        f'"""Synthetic canonical registration site."""\n{registrations}\n',
    )
    _write(
        root / "configs/baseline/reviewed.json",
        json.dumps(
            {
                "arm": "synthetic",
                "phase_review": {"draft": {"judges": judge_ids, "on_flag": "record"}},
            },
            indent=2,
        ),
    )


def test_judges_key_is_checked_at_any_depth_against_the_judges_registry(tmp_path, capsys):
    _make_judges_repo(tmp_path, judge_ids=["known-judge", "ghost-judge"], registered=["known-judge"])
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"rules": {}}), encoding="utf-8")

    exit_code, report = _run(tmp_path, baseline_path, capsys)

    assert exit_code == 1
    assert report["new_offenders"] == [
        "unregistered_config_values: "
        "configs/baseline/reviewed.json::phase_review.draft.judges[1]=ghost-judge"
    ]
    assert "judges" in report["config_keys_found"]
    assert report["registered_names"]["JUDGES"] == ["known-judge"]


def test_a_fully_registered_judges_list_is_not_an_offender(tmp_path, capsys):
    _make_judges_repo(
        tmp_path, judge_ids=["known-judge"], registered=["known-judge", "spare-judge"]
    )
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"rules": {}}), encoding="utf-8")

    exit_code, report = _run(tmp_path, baseline_path, capsys)

    assert exit_code == 0
    assert report["passed"] is True


def test_subclass_detector_resolves_aliases_transitive_imports_and_unrelated_names(tmp_path):
    """Subclass detection follows imports while keeping same-named locals isolated."""

    _write(tmp_path / "src/speech_aware_evidence_acquisition/rails/task_adapter.py", "class TaskAdapter: pass\n")
    _write(tmp_path / "src/speech_aware_evidence_acquisition/rails/controllers.py", "class EvidenceAgentController: pass\n")
    _write(tmp_path / "src/speech_aware_evidence_acquisition/rails/adapters/base.py", "from ..task_adapter import TaskAdapter as AdapterBase\nclass SharedAdapter(AdapterBase): pass\n")
    _write(tmp_path / "scripts/ordinary.py", "from speech_aware_evidence_acquisition.rails.adapters.base import SharedAdapter as SA\nclass ScriptAdapter(SA): pass\nclass TaskAdapter: pass\nclass Unrelated(TaskAdapter): pass\n")
    _write(tmp_path / "scripts/controller_child.py", "from speech_aware_evidence_acquisition.rails.controllers import EvidenceAgentController as EAC\nclass Child(EAC): pass\n")

    reader = ebc.LiveTreeReader(tmp_path)
    assert ebc.find_subclasses(reader, "speech_aware_evidence_acquisition.rails.task_adapter", "TaskAdapter") == [
        "scripts/ordinary.py::ScriptAdapter",
        "src/speech_aware_evidence_acquisition/rails/adapters/base.py::SharedAdapter",
    ]
    assert ebc.find_subclasses(reader, "speech_aware_evidence_acquisition.rails.controllers", "EvidenceAgentController") == [
        "scripts/controller_child.py::Child",
    ]


def test_subclass_detector_reports_allowed_class_exported_to_script(tmp_path):
    _write(tmp_path / "src/speech_aware_evidence_acquisition/rails/task_adapter.py", "class TaskAdapter: pass\n")
    _write(tmp_path / "src/speech_aware_evidence_acquisition/rails/adapters/allowed.py", "from ..task_adapter import TaskAdapter\nclass AllowedAdapter(TaskAdapter): pass\n")
    _write(tmp_path / "flights/run.py", "from speech_aware_evidence_acquisition.rails.adapters.allowed import AllowedAdapter\nclass FlightAdapter(AllowedAdapter): pass\n")

    reader = ebc.LiveTreeReader(tmp_path)
    assert ebc.find_subclasses(reader, "speech_aware_evidence_acquisition.rails.task_adapter", "TaskAdapter") == [
        "flights/run.py::FlightAdapter",
        "src/speech_aware_evidence_acquisition/rails/adapters/allowed.py::AllowedAdapter",
    ]



def test_nested_planner_policy_resolves_only_in_shared_registry(tmp_path, capsys):
    _write(
        tmp_path / "src/speech_aware_evidence_acquisition/rails/phase_planner.py",
        'PHASE_PLANNERS.register("continue-on-flag-v1", rule)\n',
    )
    config = tmp_path / "configs/baseline/reviewed.json"
    _write(config, json.dumps({
        "nested": {"phase_planner": {"draft": {
            "planner_policy_id": "continue-on-flag-v1",
        }}},
    }))
    baseline = tmp_path / "baseline.json"
    _write(baseline, json.dumps({"rules": {}}))
    code, report = _run(tmp_path, baseline, capsys)
    assert code == 0
    assert report["passed"]
    document = json.loads(config.read_text())
    document["nested"]["phase_planner"]["draft"]["planner_policy_id"] = "private-copy"
    _write(config, json.dumps(document))
    code, report = _run(tmp_path, baseline, capsys)
    assert code == 1
    assert any("planner_policy_id=private-copy" in item for item in report["new_offenders"])
