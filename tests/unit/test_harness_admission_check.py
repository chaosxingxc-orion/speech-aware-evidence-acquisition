"""``scripts/checks/harness_admission_check.py``: the admission gate's gate.

The check must PASS on the committed receipt and, more importantly, FAIL on
each defect it exists to catch -- a switch that names no table, a key that
names no entry of its table, an OFF arm that is not the table's null arm, a
``proof`` that names a test nobody wrote, an admitted module that reaches no
default plan, a harmful module armed in one, and a provisionally-admitted
module armed in one before its obligation is met. Every negative control is a
synthetic receipt; the committed one is never mutated.

Loaded via ``importlib.util`` for the reason the other check tests give:
``scripts/`` carries no ``__init__.py`` and is not part of the package.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_PATH = REPO_ROOT / "scripts" / "checks" / "harness_admission_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("harness_admission_check", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hac = _load_module()

PROOF = (
    "tests/unit/test_config_table_module_switches.py"
    "::test_repair_alignment_is_one_key_in_the_judges_table"
)


def _committed() -> dict:
    return json.loads(
        (REPO_ROOT / hac.RECEIPT_RELPATH).read_text(encoding="utf-8")
    )


def _entry(**overrides) -> dict:
    entry = {
        "carrier": "slurp",
        "evidence": {"primary": "a sealed contrast"},
        "module": "a module",
        "row": "SAEA-ROW-1",
        "status": "ADMITTED",
        "switch": {
            "key": "judges.<phase>.judges",
            "off": None,
            "on": ["slurp-legal-label-flag-v1"],
            "proof": PROOF,
            "table": "judges",
        },
    }
    entry.update(overrides)
    return entry


def _receipt(entries, plans=None) -> dict:
    return {
        "default_plans": plans or [],
        "entries": entries,
        "gate": "the design note's section 8 gate",
        "schema": hac.EXPECTED_SCHEMA,
        "status_values": {
            "ADMITTED": "gain",
            "HARMFUL": "a guard fails",
            "NEUTRAL": "no harm, no gain",
            "PENDING": "registered, not decided",
        },
        "switch_rule": "one config key",
    }


def _run(tmp_path, document):
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return hac.evaluate(REPO_ROOT, path)


def _plan(tmp_path, relpath, fragment):
    """Write one default-plan fragment into a synthetic repo root, and seed
    the proof test the switch declaration names, so the plan rules are what
    these cases actually measure."""

    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fragment), encoding="utf-8")
    proof_relpath, _, proof_name = PROOF.partition("::")
    proof = tmp_path / proof_relpath
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(f"def {proof_name}():\n    pass\n", encoding="utf-8")
    return relpath


# ---------------------------------------------------------------------------
# The committed receipt
# ---------------------------------------------------------------------------


def test_the_committed_receipt_passes():
    result = hac.evaluate(REPO_ROOT)
    assert result["failures"] == []
    assert result["passed"] is True


def test_the_committed_receipts_repair_module_is_barred_from_every_plan():
    """Its verdict note fixed the consequence before the verdict was known:
    an UNMET replication obligation means no entry into the default plan.

    Two modules are decided since the 2026-09-08 merge; before it there was
    one, and this case is that one."""

    rows = {row["module"]: row for row in hac.evaluate(REPO_ROOT)["entries"]}
    row = rows["substitution-only repair with the ConEC brief"]
    assert row["blocked"] is True
    assert row["blocked_reason"] == "provisional obligation UNMET"
    assert row["in_default_plans"] == []


def test_the_committed_receipts_scheduler_module_reaches_its_carriers_plan():
    """The other side of the same rule: a NEUTRAL module with no blocking
    obligation must reach a default plan for its own carrier, and the
    dispatcher's verdict admitted it to one."""

    rows = {row["module"]: row for row in hac.evaluate(REPO_ROOT)["entries"]}
    row = rows["cross-call dispatcher (obs_prefetch_depth 1)"]
    assert row["blocked"] is False
    assert row["status"] == "NEUTRAL"
    assert row["table"] == hac.RUN_SWITCH_CLASS
    assert row["switch_key"] == "obs_prefetch_depth"
    assert row["in_default_plans"] == [
        "configs/baseline/e21-buf90-zero-locked-scored4-prefetch1.json"
    ]


def test_the_committed_receipts_switch_names_a_real_table_key_and_a_real_test():
    entry = _committed()["entries"][0]
    assert entry["switch"]["table"] in hac.CONFIG_TABLE_NAMES
    assert hac.resolve_switch_key(entry["switch"]["table"], entry["switch"]["key"]) == "judges"
    relpath, _, name = entry["switch"]["proof"].partition("::")
    assert f"def {name}(" in (REPO_ROOT / relpath).read_text(encoding="utf-8")


def test_the_main_entry_point_returns_zero_on_the_committed_receipt(capsys):
    assert hac.main([]) == 0
    assert "PASS" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Rule 1: the switch resolves in a table
# ---------------------------------------------------------------------------


def test_a_missing_switch_fails(tmp_path):
    entry = _entry()
    del entry["switch"]
    result = _run(tmp_path, _receipt([entry]))
    assert any("missing ['switch']" in failure for failure in result["failures"])


def test_a_switch_naming_no_config_table_fails(tmp_path):
    entry = _entry()
    entry["switch"]["table"] = "modes"
    result = _run(tmp_path, _receipt([entry]))
    assert any("the switch classes are" in failure for failure in result["failures"])


def test_a_key_that_names_no_entry_of_its_table_fails(tmp_path):
    entry = _entry()
    entry["switch"]["key"] = "judges.<phase>.verdicts"
    result = _run(tmp_path, _receipt([entry]))
    assert any("names no entry of the" in failure for failure in result["failures"])


def test_a_key_that_does_not_start_with_its_table_fails(tmp_path):
    entry = _entry()
    entry["switch"]["key"] = "phase_review.<phase>.judges"
    result = _run(tmp_path, _receipt([entry]))
    assert any("does not start with its table" in failure for failure in result["failures"])


def test_an_off_arm_that_is_not_the_tables_null_arm_fails(tmp_path):
    entry = _entry()
    entry["switch"]["off"] = []
    result = _run(tmp_path, _receipt([entry]))
    assert any("third cell identity" in failure for failure in result["failures"])


def test_an_on_arm_that_is_the_null_arm_fails(tmp_path):
    entry = _entry()
    entry["switch"]["on"] = None
    result = _run(tmp_path, _receipt([entry]))
    assert any("must arm something" in failure for failure in result["failures"])


def test_a_proof_naming_a_test_nobody_wrote_fails(tmp_path):
    entry = _entry()
    entry["switch"]["proof"] = (
        "tests/unit/test_config_table_module_switches.py::test_wishful_thinking"
    )
    result = _run(tmp_path, _receipt([entry]))
    assert any("does not define" in failure for failure in result["failures"])


def test_a_proof_naming_a_file_that_does_not_exist_fails(tmp_path):
    entry = _entry()
    entry["switch"]["proof"] = "tests/unit/test_nothing.py::test_x"
    result = _run(tmp_path, _receipt([entry]))
    assert any("which does not exist" in failure for failure in result["failures"])


def test_a_proof_that_is_not_a_node_id_fails(tmp_path):
    entry = _entry()
    entry["switch"]["proof"] = "somebody checked it"
    result = _run(tmp_path, _receipt([entry]))
    assert any("node id" in failure for failure in result["failures"])


# ---------------------------------------------------------------------------
# Rule 2: an admitted or neutral module reaches a default plan
# ---------------------------------------------------------------------------


def test_an_admitted_module_with_no_default_plan_fails(tmp_path):
    result = _run(tmp_path, _receipt([_entry()]))
    assert any("no default plan for" in failure for failure in result["failures"])


def test_an_admitted_module_armed_in_a_default_plan_passes(tmp_path):
    relpath = _plan(
        tmp_path,
        "configs/baseline/plan.json",
        {"policy": "phase-direct-only-v1", "judges": {"direct": {"judges": ["x"]}}},
    )
    result = hac.evaluate(
        tmp_path,
        _write(tmp_path, _receipt([_entry()], [{"carrier": "slurp", "config": relpath}])),
    )
    assert result["failures"] == []
    assert result["entries"][0]["in_default_plans"] == [relpath]


def test_a_plan_that_declares_the_tables_null_arm_does_not_arm_the_module(tmp_path):
    relpath = _plan(tmp_path, "configs/baseline/plan.json", {"judges": None})
    result = hac.evaluate(
        tmp_path,
        _write(tmp_path, _receipt([_entry()], [{"carrier": "slurp", "config": relpath}])),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_plan_for_another_carrier_does_not_count(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt([_entry()], [{"carrier": "earnings21-original", "config": relpath}]),
        ),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_pending_module_is_neither_required_nor_barred(tmp_path):
    result = _run(tmp_path, _receipt([_entry(status="PENDING")]))
    assert result["failures"] == []


def test_a_default_plan_naming_a_missing_file_fails(tmp_path):
    result = _run(
        tmp_path,
        _receipt([_entry(status="PENDING")], [{"carrier": "slurp", "config": "configs/x.json"}]),
    )
    assert any("does not exist" in failure for failure in result["failures"])


# ---------------------------------------------------------------------------
# Rule 3: a harmful or unmet-provisional module never enters a plan
# ---------------------------------------------------------------------------


def test_a_harmful_module_armed_in_a_default_plan_fails(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt(
                [_entry(status="HARMFUL")], [{"carrier": "slurp", "config": relpath}]
            ),
        ),
    )
    assert any("status HARMFUL, but it is armed" in failure for failure in result["failures"])


def test_a_harmful_module_absent_from_every_plan_passes(tmp_path):
    result = _run(tmp_path, _receipt([_entry(status="HARMFUL")]))
    assert result["failures"] == []


def test_a_provisionally_admitted_module_armed_in_a_plan_fails(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt(
                [_entry(provisional={"state": "UNMET", "reason": "one sample"})],
                [{"carrier": "slurp", "config": relpath}],
            ),
        ),
    )
    assert any(
        "provisional obligation UNMET, but it is armed" in failure
        for failure in result["failures"]
    )


def test_a_met_provisional_obligation_stops_blocking(tmp_path):
    relpath = _plan(
        tmp_path, "configs/baseline/plan.json", {"judges": {"direct": {"judges": ["x"]}}}
    )
    result = hac.evaluate(
        tmp_path,
        _write(
            tmp_path,
            _receipt(
                [_entry(provisional={"state": "MET", "reason": "replicated"})],
                [{"carrier": "slurp", "config": relpath}],
            ),
        ),
    )
    assert result["failures"] == []
    assert result["entries"][0]["blocked"] is False


# ---------------------------------------------------------------------------
# Receipt shape
# ---------------------------------------------------------------------------


def test_an_old_schema_fails(tmp_path):
    document = _receipt([_entry(status="PENDING")])
    document["schema"] = "saea-harness-admission-v1"
    result = _run(tmp_path, document)
    assert any("expected" in failure for failure in result["failures"])


def test_a_missing_top_level_key_fails(tmp_path):
    document = _receipt([_entry(status="PENDING")])
    del document["switch_rule"]
    result = _run(tmp_path, document)
    assert any("missing top-level key(s)" in failure for failure in result["failures"])


def test_two_entries_deciding_one_module_and_carrier_fail(tmp_path):
    result = _run(
        tmp_path,
        _receipt([_entry(status="PENDING"), _entry(status="PENDING")]),
    )
    assert any("a second entry decides" in failure for failure in result["failures"])


def test_an_unknown_status_fails(tmp_path):
    result = _run(tmp_path, _receipt([_entry(status="PROBABLY-FINE")]))
    assert any("is not one of" in failure for failure in result["failures"])


def test_an_unreadable_receipt_raises(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("{not json", encoding="utf-8")
    try:
        hac.evaluate(REPO_ROOT, path)
    except hac.HarnessAdmissionCheckError as error:
        assert "cannot read" in str(error)
    else:  # pragma: no cover - the check must refuse
        raise AssertionError("an unreadable receipt must raise")


def test_the_committed_receipt_is_not_mutated_by_any_of_this():
    assert _committed() == copy.deepcopy(_committed())
    assert _committed()["schema"] == hac.EXPECTED_SCHEMA


def _write(root: Path, document: dict) -> Path:
    path = root / "receipt.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Rule 4: the run switch class -- one config key, no table, no request moved
#
# Added 2026-09-08 on the merge of WAVE W4 into master, where the v2 schema
# met the cross-call dispatcher: a scheduler is one config key and has no
# per-phase table entry, because the four tables are per-phase and it is
# per-run. Every case below runs against a SYNTHETIC repo root, so the
# committed receipt is never mutated and the falsifier bytes are the case's
# own.
# ---------------------------------------------------------------------------

RUN_PROOF = (
    "tests/unit/test_config_table_module_switches.py"
    "::test_the_cross_call_dispatcher_is_one_run_level_key"
)


def _falsifier_receipt(tmp_path, relpath="docs/checks/dispatch", digest=None):
    """A receipt directory with a MANIFEST the check can re-hash. Pass
    ``digest`` to seed one that does not verify."""

    directory = tmp_path / relpath
    directory.mkdir(parents=True, exist_ok=True)
    body = b"1,593 of 1,593 slices byte-identical\n"
    (directory / "README.md").write_bytes(body)
    listed = digest or hashlib.sha256(body).hexdigest()
    (directory / "MANIFEST.sha256").write_text(
        f"{listed} *README.md\n", encoding="utf-8"
    )
    return relpath


def _run_entry(tmp_path, receipt_relpath="docs/checks/dispatch", **switch_overrides):
    switch = {
        "falsifier": {"kind": "request-bytes-identical", "receipt": receipt_relpath},
        "key": "obs_prefetch_depth",
        "off": 0,
        "on": 1,
        "proof": RUN_PROOF,
        "table": "run",
    }
    switch.update(switch_overrides)
    proof_relpath, _, proof_name = RUN_PROOF.partition("::")
    proof = tmp_path / proof_relpath
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(f"def {proof_name}():\n    pass\n", encoding="utf-8")
    return _entry(
        carrier="earnings21-original",
        module="a scheduler",
        status="NEUTRAL",
        switch=switch,
    )


def _run_plan(tmp_path, fragment=None):
    relpath = "configs/baseline/plan.json"
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"obs_prefetch_depth": 1} if fragment is None else fragment),
        encoding="utf-8",
    )
    return relpath


def _evaluate(tmp_path, document):
    return hac.evaluate(tmp_path, _write(tmp_path, document))


def test_a_run_class_switch_with_a_verifying_falsifier_and_a_plan_passes(tmp_path):
    _falsifier_receipt(tmp_path)
    plan = _run_plan(tmp_path)
    result = _evaluate(
        tmp_path,
        _receipt(
            [_run_entry(tmp_path)],
            [{"carrier": "earnings21-original", "config": plan}],
        ),
    )
    assert result["failures"] == []
    assert result["entries"][0]["table"] == "run"
    assert result["entries"][0]["switch_key"] == "obs_prefetch_depth"
    assert result["entries"][0]["in_default_plans"] == [plan]


def test_a_run_key_outside_the_closed_allowlist_fails(tmp_path):
    _falsifier_receipt(tmp_path)
    result = _evaluate(
        tmp_path, _receipt([_run_entry(tmp_path, key="obs_batch_slices")])
    )
    assert any("closed allowlist" in failure for failure in result["failures"])


def test_a_dotted_run_key_fails(tmp_path):
    _falsifier_receipt(tmp_path)
    result = _evaluate(
        tmp_path, _receipt([_run_entry(tmp_path, key="run.obs_prefetch_depth")])
    )
    assert any("is dotted" in failure for failure in result["failures"])


def test_a_run_entry_without_a_falsifier_fails(tmp_path):
    _falsifier_receipt(tmp_path)
    entry = _run_entry(tmp_path)
    del entry["switch"]["falsifier"]
    result = _evaluate(tmp_path, _receipt([entry]))
    assert any(
        "owes a falsifier proving it changed no request byte" in failure
        for failure in result["failures"]
    )


def test_a_run_falsifier_of_another_kind_fails(tmp_path):
    _falsifier_receipt(tmp_path)
    entry = _run_entry(tmp_path)
    entry["switch"]["falsifier"]["kind"] = "somebody looked at it"
    result = _evaluate(tmp_path, _receipt([entry]))
    assert any("accepts only" in failure for failure in result["failures"])


def test_a_run_falsifier_naming_no_receipt_directory_fails(tmp_path):
    result = _evaluate(
        tmp_path,
        _receipt([_run_entry(tmp_path, receipt_relpath="docs/checks/nothing-here")]),
    )
    assert any(
        "not a directory in this repository" in failure
        for failure in result["failures"]
    )


def test_a_run_falsifier_whose_manifest_does_not_verify_fails(tmp_path):
    """A named receipt whose bytes moved proves nothing, so the check
    re-hashes the manifest instead of believing the path."""

    _falsifier_receipt(tmp_path, digest="0" * 64)
    result = _evaluate(tmp_path, _receipt([_run_entry(tmp_path)]))
    assert any(
        "does not match its listed sha256" in failure for failure in result["failures"]
    )


def test_a_run_off_arm_that_is_not_the_null_arm_fails(tmp_path):
    _falsifier_receipt(tmp_path)
    result = _evaluate(tmp_path, _receipt([_run_entry(tmp_path, off=1)]))
    assert any("third cell identity" in failure for failure in result["failures"])


def test_a_plan_that_leaves_the_run_key_at_its_default_does_not_arm_it(tmp_path):
    _falsifier_receipt(tmp_path)
    plan = _run_plan(tmp_path, {"obs_prefetch_depth": 0})
    result = _evaluate(
        tmp_path,
        _receipt(
            [_run_entry(tmp_path)],
            [{"carrier": "earnings21-original", "config": plan}],
        ),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_harmful_run_module_armed_in_a_plan_fails(tmp_path):
    _falsifier_receipt(tmp_path)
    plan = _run_plan(tmp_path)
    entry = _run_entry(tmp_path)
    entry["status"] = "HARMFUL"
    result = _evaluate(
        tmp_path,
        _receipt([entry], [{"carrier": "earnings21-original", "config": plan}]),
    )
    assert any("status HARMFUL" in failure for failure in result["failures"])


def test_switch_classes_naming_a_class_the_check_cannot_enforce_fails(tmp_path):
    document = _receipt([_entry()])
    document["switch_classes"] = ["judges", "vibes"]
    result = _run(tmp_path, document)
    assert any("'switch_classes' is" in failure for failure in result["failures"])


def test_the_committed_receipt_declares_the_switch_classes_this_check_knows():
    assert _committed()["switch_classes"] == list(hac.SWITCH_CLASS_NAMES)


# ---------------------------------------------------------------------------
# Rule 5: the episode switch class -- one dotted path under native_episode,
# on a closed allowlist, whose OFF arm is that key's own null form.
#
# Added by Fable E6 (2026-09-16, harness-admission v3) for the SLURP v2 base
# program's M0 (review-loop off) and M2 (grouped-Solver sampling). Every case
# below runs against a SYNTHETIC receipt, so the committed one (which carries
# no 'episode' entry yet -- no B0/B2 cell has been decided) is never mutated.
# ---------------------------------------------------------------------------

EPISODE_PROOF = (
    "tests/unit/test_config_table_module_switches.py"
    "::test_grouped_solver_sampling_is_one_native_episode_roles_solver_key"
)


def _episode_entry(tmp_path, **switch_overrides):
    switch = {
        "key": "native_episode.roles.solver",
        "off": None,
        "on": {
            "samples": 5,
            "decoding_overrides": {"temperature": 0.7, "seed_offset": 0},
            "commit": {
                "policy": "saea-commit-plurality-support-v1",
                "min_support": 3,
                "similarity_threshold": 0.8,
            },
        },
        "proof": EPISODE_PROOF,
        "table": "episode",
    }
    switch.update(switch_overrides)
    proof_relpath, _, proof_name = EPISODE_PROOF.partition("::")
    proof = tmp_path / proof_relpath
    proof.parent.mkdir(parents=True, exist_ok=True)
    if not proof.exists():
        proof.write_text(f"def {proof_name}():\n    pass\n", encoding="utf-8")
    return _entry(module="grouped Solver sampling", status="NEUTRAL", switch=switch)


def _episode_plan(tmp_path, fragment=None, relpath="configs/baseline/episode-plan.json"):
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    default = {
        "native_episode": {
            "roles": {"solver": {"phase_id": "solver", "max_iterations": 1, "samples": 5}}
        }
    }
    path.write_text(json.dumps(fragment if fragment is not None else default), encoding="utf-8")
    return relpath


def test_an_episode_class_switch_with_an_arming_plan_passes(tmp_path):
    plan = _episode_plan(tmp_path)
    result = _evaluate(
        tmp_path,
        _receipt([_episode_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert result["failures"] == []
    assert result["entries"][0]["table"] == "episode"
    assert result["entries"][0]["switch_key"] == "native_episode.roles.solver"
    assert result["entries"][0]["in_default_plans"] == [plan]


def test_a_plan_leaving_the_episode_key_at_its_default_does_not_arm_it(tmp_path):
    plan = _episode_plan(
        tmp_path,
        {"native_episode": {"roles": {"solver": {"phase_id": "solver", "max_iterations": 1}}}},
    )
    result = _evaluate(
        tmp_path,
        _receipt([_episode_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_an_episode_key_outside_the_closed_allowlist_fails(tmp_path):
    result = _evaluate(
        tmp_path,
        _receipt([_episode_entry(tmp_path, key="native_episode.roles.reviewer")]),
    )
    assert any("not admitted" in failure for failure in result["failures"])


def test_an_episode_key_not_under_native_episode_fails(tmp_path):
    result = _evaluate(tmp_path, _receipt([_episode_entry(tmp_path, key="roles.solver")]))
    assert any("does not start with" in failure for failure in result["failures"])


def test_an_episode_off_arm_that_is_not_the_keys_null_form_fails(tmp_path):
    result = _evaluate(
        tmp_path, _receipt([_episode_entry(tmp_path, off={"samples": 3})])
    )
    assert any("own null form" in failure for failure in result["failures"])


def test_an_episode_on_arm_that_is_the_null_arm_fails(tmp_path):
    result = _evaluate(tmp_path, _receipt([_episode_entry(tmp_path, on=None)]))
    assert any("must arm something" in failure for failure in result["failures"])


def test_a_harmful_episode_module_armed_in_a_plan_fails(tmp_path):
    plan = _episode_plan(tmp_path)
    entry = _episode_entry(tmp_path)
    entry["status"] = "HARMFUL"
    result = _evaluate(
        tmp_path, _receipt([entry], [{"carrier": "slurp", "config": plan}])
    )
    assert any("status HARMFUL" in failure for failure in result["failures"])


def test_the_review_loop_marker_arms_and_disarms_through_the_same_class(tmp_path):
    """The allowlist's other key, proved through the same machinery: 'on'
    arms it, 'off' does not."""

    entry = _episode_entry(tmp_path, key="native_episode.review_loop", off="off", on="on")
    plan_on = _episode_plan(
        tmp_path, {"native_episode": {"review_loop": "on"}}, "configs/baseline/rl-on.json"
    )
    result_on = _evaluate(
        tmp_path, _receipt([entry], [{"carrier": "slurp", "config": plan_on}])
    )
    assert result_on["failures"] == []
    assert result_on["entries"][0]["in_default_plans"] == [plan_on]

    plan_off = _episode_plan(
        tmp_path, {"native_episode": {"review_loop": "off"}}, "configs/baseline/rl-off.json"
    )
    result_off = _evaluate(
        tmp_path, _receipt([entry], [{"carrier": "slurp", "config": plan_off}])
    )
    assert any("no default plan for" in failure for failure in result_off["failures"])


# ---------------------------------------------------------------------------
# Rule 6: the stores switch class -- knowledge_stores.<store_id>, whose OFF
# arm is the named store's absence.
#
# Added alongside rule 5 for the SLURP v2 base program's M1 (exemplar-
# grounded Solver, the train-exemplars store). Every case below runs against
# a SYNTHETIC receipt.
# ---------------------------------------------------------------------------

STORES_PROOF = (
    "tests/unit/test_config_table_module_switches.py"
    "::test_exemplar_supply_store_is_the_only_key_moved_on_the_committed_fragments"
)


def _stores_entry(tmp_path, **switch_overrides):
    switch = {
        "key": "knowledge_stores.train-exemplars",
        "off": None,
        "on": {"store_role": "train-exemplars"},
        "proof": STORES_PROOF,
        "table": "stores",
    }
    switch.update(switch_overrides)
    proof_relpath, _, proof_name = STORES_PROOF.partition("::")
    proof = tmp_path / proof_relpath
    proof.parent.mkdir(parents=True, exist_ok=True)
    if not proof.exists():
        proof.write_text(f"def {proof_name}():\n    pass\n", encoding="utf-8")
    return _entry(module="exemplar-grounded Solver", status="NEUTRAL", switch=switch)


def _stores_plan(tmp_path, fragment=None, relpath="configs/baseline/stores-plan.json"):
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    default = {"knowledge_stores": {"train-exemplars": {"store_role": "train-exemplars"}}}
    path.write_text(json.dumps(fragment if fragment is not None else default), encoding="utf-8")
    return relpath


def test_a_stores_class_switch_with_an_arming_plan_passes(tmp_path):
    plan = _stores_plan(tmp_path)
    result = _evaluate(
        tmp_path,
        _receipt([_stores_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert result["failures"] == []
    assert result["entries"][0]["table"] == "stores"
    assert result["entries"][0]["switch_key"] == "knowledge_stores.train-exemplars"
    assert result["entries"][0]["in_default_plans"] == [plan]


def test_a_plan_without_the_named_store_does_not_arm_it(tmp_path):
    plan = _stores_plan(tmp_path, {"knowledge_stores": {}})
    result = _evaluate(
        tmp_path,
        _receipt([_stores_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_stores_key_with_the_wrong_shape_fails(tmp_path):
    result = _evaluate(tmp_path, _receipt([_stores_entry(tmp_path, key="knowledge_stores")]))
    assert any("must be" in failure for failure in result["failures"])


def test_a_stores_off_arm_that_is_not_null_fails(tmp_path):
    result = _evaluate(tmp_path, _receipt([_stores_entry(tmp_path, off={})]))
    assert any("must be null" in failure for failure in result["failures"])


def test_a_stores_on_arm_that_is_the_null_arm_fails(tmp_path):
    result = _evaluate(tmp_path, _receipt([_stores_entry(tmp_path, on=None)]))
    assert any("must arm something" in failure for failure in result["failures"])


def test_a_harmful_stores_module_armed_in_a_plan_fails(tmp_path):
    plan = _stores_plan(tmp_path)
    entry = _stores_entry(tmp_path)
    entry["status"] = "HARMFUL"
    result = _evaluate(
        tmp_path, _receipt([entry], [{"carrier": "slurp", "config": plan}])
    )
    assert any("status HARMFUL" in failure for failure in result["failures"])


# ---------------------------------------------------------------------------
# Regression: the v3 bump changed only the schema/switch_classes fields --
# every existing admission entry still validates unchanged.
# ---------------------------------------------------------------------------


def test_the_v3_schema_still_validates_every_existing_entry():
    assert _committed()["schema"] == "saea-harness-admission-v3"
    assert set(_committed()["switch_classes"]) == {
        "judges", "knowledge_views", "observe", "toolkits", "run", "episode", "stores",
        "phase_tools", "module",
    }
    result = hac.evaluate(REPO_ROOT)
    assert result["failures"] == []
    assert result["passed"] is True
    # Every committed entry validates -- read as a count OF THE RECEIPT rather
    # than as a literal, because this test is about the schema validating what
    # is committed, and a literal turns every later admission into a failure
    # here (the SLURP review-loop entry of 2026-09-17 made the old literal 4
    # wrong without anything being wrong).
    assert len(result["entries"]) == len(_committed()["entries"])


# ---------------------------------------------------------------------------
# Rule 6, the class's SECOND arm form: the store RE-PIN (E9, 2026-09-17).
#
# Cell B4b's module M4b re-pins a store the comparator ALREADY carries --
# knowledge_stores.slot-contracts, from slot-contracts-v1 to slot-contracts-v2
# -- so its OFF arm is the incumbent's pins, not the store's absence, and the
# null form cannot express it. These cases fix what the extension accepts and,
# more importantly, what it still refuses: an undeclared re-pin, a re-pin that
# pins the same bytes twice, an arm that moves more than the two pin leaves,
# and a repo-relative pin whose file is missing or whose bytes moved. Every
# case runs against a SYNTHETIC receipt; the committed one carries no re-pin
# entry (the M4b row is not written here) and is never mutated.
# ---------------------------------------------------------------------------

REPIN_PROOF = (
    "tests/unit/test_config_table_module_switches.py"
    "::test_the_stores_repin_form_is_one_key"
)

#: The two arms exactly as the committed fragments pin them: the sealed anchor
#: configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json and
#: cell B4b's configs/baseline/slurp-native-anchor-slot-store-v2-train-fold-a-v2.json.
#: Both relpaths are SPEECHRL_DATA_DIR paths, so this model-free check reads
#: neither and both are checked for shape alone.
V1_PINS = {
    "release": {
        "relpath": "knowledge/slurp/semantic/slot-contracts-v1/release.json",
        "sha256": "8a29c48bfc5aed2eb27ce38073252d3fc608c9102aa8b8095a072667289b4f3e",
    },
    "snapshot": {
        "relpath": "knowledge/slurp/semantic/slot-contracts-v1/snapshot.json",
        "sha256": "11c246e4b815a4f966e8cf8785f06b70515755eca71658862c6f98e9914044e6",
    },
}
V2_PINS = {
    "release": {
        "relpath": "knowledge/slurp/semantic/slot-contracts-v2/release.json",
        "sha256": "f8e42d4ff1b220f45b26397340149566544cf5b13d7453fbc46a2b5c3400d11b",
    },
    "snapshot": {
        "relpath": "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json",
        "sha256": "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec",
    },
}


def _repin_entry(tmp_path, **switch_overrides):
    switch = {
        "form": "repin",
        "key": "knowledge_stores.slot-contracts",
        "off": copy.deepcopy(V1_PINS),
        "on": copy.deepcopy(V2_PINS),
        "proof": REPIN_PROOF,
        "table": "stores",
    }
    switch.update(switch_overrides)
    proof_relpath, _, proof_name = REPIN_PROOF.partition("::")
    proof = tmp_path / proof_relpath
    proof.parent.mkdir(parents=True, exist_ok=True)
    if not proof.exists():
        proof.write_text(f"def {proof_name}():\n    pass\n", encoding="utf-8")
    return _entry(
        module="date/time slot-contract revision (slot store v2)",
        status="ADMITTED",
        switch=switch,
    )


def _repin_plan(tmp_path, pins=None, relpath="configs/baseline/repin-plan.json"):
    """A default-plan fragment pinning the slot-contracts store at ``pins``
    (the v2 pins by default), beside a second store that never moves. ``pins``
    of ``None`` writes a plan that carries no slot-contracts store at all."""

    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    stores = {"intent-boundaries": {"store_role": "intent-boundaries"}}
    if pins is not None:
        stores["slot-contracts"] = {
            "store_role": "slot-contracts",
            "candidate_supply": {"solver": {"provider": "slurp-candidate-semantic-v1"}},
            **copy.deepcopy(pins),
        }
    path.write_text(json.dumps({"knowledge_stores": stores}), encoding="utf-8")
    return relpath


def test_a_stores_repin_switch_with_an_arming_plan_passes(tmp_path):
    plan = _repin_plan(tmp_path, V2_PINS)
    result = _evaluate(
        tmp_path,
        _receipt([_repin_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert result["failures"] == []
    assert result["entries"][0]["table"] == "stores"
    assert result["entries"][0]["switch_form"] == "repin"
    assert result["entries"][0]["switch_key"] == "knowledge_stores.slot-contracts"
    assert result["entries"][0]["in_default_plans"] == [plan]


def test_a_plan_carrying_the_repin_off_pins_does_not_arm_the_module(tmp_path):
    """The whole reason plan arming needed the ON arm: the store IS present
    and is NOT the null arm, and the module is still off."""

    plan = _repin_plan(tmp_path, V1_PINS)
    result = _evaluate(
        tmp_path,
        _receipt([_repin_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_plan_without_the_re_pinned_store_does_not_arm_the_module(tmp_path):
    plan = _repin_plan(tmp_path, None)
    result = _evaluate(
        tmp_path,
        _receipt([_repin_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert any("no default plan for" in failure for failure in result["failures"])


def test_a_stores_repin_entry_whose_off_equals_on_fails(tmp_path):
    plan = _repin_plan(tmp_path, V2_PINS)
    result = _evaluate(
        tmp_path,
        _receipt(
            [_repin_entry(tmp_path, off=copy.deepcopy(V2_PINS))],
            [{"carrier": "slurp", "config": plan}],
        ),
    )
    assert any("switches nothing at all" in failure for failure in result["failures"])


def test_a_stores_repin_entry_without_the_form_marker_fails(tmp_path):
    """The form is declared, never inferred: the same two arms without
    ``form: 'repin'`` are read in the null form and refused there."""

    entry = _repin_entry(tmp_path)
    del entry["switch"]["form"]
    result = _evaluate(tmp_path, _receipt([entry]))
    assert any("must be null" in failure for failure in result["failures"])
    assert any("'repin'" in failure for failure in result["failures"])


def test_an_unknown_stores_switch_form_fails(tmp_path):
    result = _evaluate(tmp_path, _receipt([_repin_entry(tmp_path, form="rebase")]))
    assert any("one of two" in failure for failure in result["failures"])


def test_a_stores_repin_arm_that_is_not_the_two_pins_fails(tmp_path):
    result = _evaluate(
        tmp_path,
        _receipt(
            [
                _repin_entry(
                    tmp_path,
                    on={**copy.deepcopy(V2_PINS), "store_role": "slot-contracts"},
                )
            ]
        ),
    )
    assert any("exactly ['release', 'snapshot']" in failure for failure in result["failures"])


def test_a_stores_repin_arm_missing_a_pin_fails(tmp_path):
    result = _evaluate(
        tmp_path, _receipt([_repin_entry(tmp_path, off={"release": V1_PINS["release"]})])
    )
    assert any("must carry exactly" in failure for failure in result["failures"])


def test_a_repo_relative_store_pin_whose_bytes_moved_fails(tmp_path):
    """A pin that DOES resolve in this repository is re-hashed here, because a
    pin whose file moved is not a pin."""

    relpath = "knowledge/slurp/semantic/slot-contracts-v2/release.json"
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    result = _evaluate(tmp_path, _receipt([_repin_entry(tmp_path)]))
    assert any("hash to" in failure for failure in result["failures"])

    # The same pins, at the bytes they actually name, pass. Both leaves have
    # to be written now: the directory exists, so the snapshot is a
    # repo-relative pin as well.
    snapshot = tmp_path / "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
    snapshot.write_text('{"values": []}', encoding="utf-8")
    on = copy.deepcopy(V2_PINS)
    on["release"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    on["snapshot"]["sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    plan = _repin_plan(tmp_path, on)
    result = _evaluate(
        tmp_path,
        _receipt(
            [_repin_entry(tmp_path, on=on)], [{"carrier": "slurp", "config": plan}]
        ),
    )
    assert result["failures"] == []


def test_a_repo_relative_store_pin_whose_file_is_missing_fails(tmp_path):
    """The case in between, fail-closed: the directory is in this repository
    and the file is not."""

    (tmp_path / "knowledge/slurp/semantic/slot-contracts-v2").mkdir(parents=True)
    result = _evaluate(tmp_path, _receipt([_repin_entry(tmp_path)]))
    assert any("must name a file that exists" in failure for failure in result["failures"])


def test_a_harmful_stores_repin_module_armed_in_a_plan_fails(tmp_path):
    plan = _repin_plan(tmp_path, V2_PINS)
    entry = _repin_entry(tmp_path)
    entry["status"] = "HARMFUL"
    result = _evaluate(
        tmp_path, _receipt([entry], [{"carrier": "slurp", "config": plan}])
    )
    assert any("status HARMFUL" in failure for failure in result["failures"])


def test_the_stores_null_form_still_validates_exactly_as_before(tmp_path):
    """The extension adds a second form; it does not loosen the first. An
    entry that declares no form is read under the null rule unchanged, and its
    plan arming is still "the named store is present and not null"."""

    plan = _stores_plan(tmp_path)
    result = _evaluate(
        tmp_path,
        _receipt([_stores_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert result["failures"] == []
    assert result["entries"][0]["switch_form"] is None
    assert result["entries"][0]["in_default_plans"] == [plan]

    # ... and an OFF arm that is not the store's absence is still refused when
    # the entry does not declare the re-pin form.
    refused = _evaluate(
        tmp_path, _receipt([_stores_entry(tmp_path, off={"store_role": "x"})])
    )
    assert any("must be null" in failure for failure in refused["failures"])


# ---------------------------------------------------------------------------
# Rule 7: the phase_tools switch class -- one role's toolkit -- and the
# RETIRED status. Added 2026-09-20 by item E25 for cell B1-notool, whose
# module WITHDRAWS the Reviewer's task-contract tool: ON is the toolkit the
# comparator carried, OFF is its null arm, the plan carries OFF. Every case
# runs against a SYNTHETIC repo root; the committed receipt is never mutated.
# ---------------------------------------------------------------------------

PHASE_TOOLS_PROOF = (
    "tests/unit/test_config_table_module_switches.py"
    "::test_the_reviewer_toolkit_withdrawal_is_one_phase_tools_key"
)

REVIEWER_TOOLKIT = {
    "reviewer": {
        "allowed_tools": ["saea-tool-task-contract-v1"],
        "knowledge_views": ["text"],
        "mode": "native-tools",
        "source_authority_role": "reviewer",
    }
}


def _phase_tools_entry(tmp_path, status="RETIRED", **switch_overrides):
    switch = {
        "key": "phase_tools.reviewer",
        "off": None,
        "on": REVIEWER_TOOLKIT,
        "proof": PHASE_TOOLS_PROOF,
        "table": "phase_tools",
    }
    switch.update(switch_overrides)
    proof_relpath, _, proof_name = PHASE_TOOLS_PROOF.partition("::")
    proof = tmp_path / proof_relpath
    proof.parent.mkdir(parents=True, exist_ok=True)
    if not proof.exists():
        proof.write_text(f"def {proof_name}():\n    pass\n", encoding="utf-8")
    return _entry(module="the Reviewer's task-contract toolkit", status=status, switch=switch)


def _phase_tools_plan(tmp_path, fragment, relpath="configs/baseline/phase-tools-plan.json"):
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fragment), encoding="utf-8")
    return relpath


def _retired_receipt(entries, plans):
    document = _receipt(entries, plans)
    document["status_values"]["RETIRED"] = "the ON arm was withdrawn; the plan carries OFF"
    return document


def test_a_retired_toolkit_whose_plan_carries_the_off_arm_passes(tmp_path):
    plan = _phase_tools_plan(tmp_path, {"arm": "speech-feature-query-native-tools"})
    result = _evaluate(
        tmp_path,
        _retired_receipt([_phase_tools_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert result["failures"] == []
    row = result["entries"][0]
    assert row["table"] == "phase_tools"
    assert row["switch_key"] == "phase_tools.reviewer"
    assert row["blocked"] is True
    assert "RETIRED" in row["blocked_reason"]
    assert row["in_default_plans"] == []


def test_a_plan_with_an_empty_or_null_role_mapping_carries_the_off_arm(tmp_path):
    for phase_tools in (None, {}, {"reviewer": None}, {"reviewer": {}}):
        plan = _phase_tools_plan(tmp_path, {"phase_tools": phase_tools})
        result = _evaluate(
            tmp_path,
            _retired_receipt(
                [_phase_tools_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]
            ),
        )
        assert result["failures"] == [], phase_tools


def test_a_retired_toolkit_still_armed_in_a_plan_fails(tmp_path):
    plan = _phase_tools_plan(tmp_path, {"phase_tools": REVIEWER_TOOLKIT})
    result = _evaluate(
        tmp_path,
        _retired_receipt([_phase_tools_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert any(
        "status RETIRED" in failure and "armed in default plan(s)" in failure
        for failure in result["failures"]
    )


def test_a_retired_toolkit_with_no_plan_for_its_carrier_fails(tmp_path):
    plan = _phase_tools_plan(tmp_path, {"phase_tools": None})
    result = _evaluate(
        tmp_path,
        _retired_receipt(
            [_phase_tools_entry(tmp_path)], [{"carrier": "earnings21-original", "config": plan}]
        ),
    )
    assert any("no default plan exists for 'slurp'" in failure for failure in result["failures"])


def test_a_plan_arming_a_different_role_does_not_arm_the_retired_one(tmp_path):
    plan = _phase_tools_plan(
        tmp_path, {"phase_tools": {"planner": REVIEWER_TOOLKIT["reviewer"]}}
    )
    result = _evaluate(
        tmp_path,
        _retired_receipt([_phase_tools_entry(tmp_path)], [{"carrier": "slurp", "config": plan}]),
    )
    assert result["failures"] == []


def test_a_new_toolkit_admitted_the_ordinary_way_must_reach_a_plan(tmp_path):
    armed = _phase_tools_plan(tmp_path, {"phase_tools": REVIEWER_TOOLKIT})
    result = _evaluate(
        tmp_path,
        _receipt(
            [_phase_tools_entry(tmp_path, status="ADMITTED")],
            [{"carrier": "slurp", "config": armed}],
        ),
    )
    assert result["failures"] == []
    assert result["entries"][0]["in_default_plans"] == [armed]
    unarmed = _phase_tools_plan(tmp_path, {"phase_tools": None}, "configs/baseline/off.json")
    result = _evaluate(
        tmp_path,
        _receipt(
            [_phase_tools_entry(tmp_path, status="ADMITTED")],
            [{"carrier": "slurp", "config": unarmed}],
        ),
    )
    assert any("no default plan for 'slurp' arms" in failure for failure in result["failures"])


def test_a_phase_tools_key_with_the_wrong_shape_fails(tmp_path):
    plan = _phase_tools_plan(tmp_path, {"phase_tools": None})
    for key in ("phase_tools", "phase_tools.<phase>", "toolkits.reviewer", "phase_tools.reviewer.mode"):
        result = _evaluate(
            tmp_path,
            _retired_receipt(
                [_phase_tools_entry(tmp_path, key=key)], [{"carrier": "slurp", "config": plan}]
            ),
        )
        assert any(".switch.key:" in failure for failure in result["failures"]), key


def test_a_phase_tools_off_arm_that_is_not_null_fails(tmp_path):
    plan = _phase_tools_plan(tmp_path, {"phase_tools": None})
    result = _evaluate(
        tmp_path,
        _retired_receipt(
            [_phase_tools_entry(tmp_path, off=REVIEWER_TOOLKIT)],
            [{"carrier": "slurp", "config": plan}],
        ),
    )
    assert any(".switch.off is" in failure for failure in result["failures"])


def test_a_phase_tools_on_arm_that_is_the_null_arm_fails(tmp_path):
    plan = _phase_tools_plan(tmp_path, {"phase_tools": None})
    for on in (None, {}):
        result = _evaluate(
            tmp_path,
            _retired_receipt(
                [_phase_tools_entry(tmp_path, on=on)], [{"carrier": "slurp", "config": plan}]
            ),
        )
        assert any(".switch.on is" in failure for failure in result["failures"]), on


def test_status_values_naming_a_status_the_check_cannot_enforce_fails(tmp_path):
    document = _receipt([_entry()], [])
    document["status_values"]["VIBES"] = "unenforced"
    result = _evaluate(tmp_path, document)
    assert any("'status_values' names ['VIBES']" in failure for failure in result["failures"])


def test_the_committed_receipt_retires_the_reviewer_toolkit_out_of_every_plan():
    """The B1-notool row: RETIRED, blocked, and the SLURP plan carries no
    phase_tools mapping at all."""

    result = hac.evaluate(REPO_ROOT)
    rows = [row for row in result["entries"] if row["switch_key"] == "phase_tools.reviewer"]
    assert len(rows) == 1
    assert rows[0]["status"] == "RETIRED"
    assert rows[0]["blocked"] is True
    assert rows[0]["in_default_plans"] == []
    plan = next(
        plan for plan in _committed()["default_plans"] if plan["carrier"] == "slurp"
    )
    fragment = json.loads((REPO_ROOT / plan["config"]).read_text(encoding="utf-8"))
    assert "phase_tools" not in fragment
