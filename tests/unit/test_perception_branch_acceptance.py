"""Acceptance tests AT-P5..AT-P8 for the same-flight Perception-branch instrument (same-flight
instrument phase 2, merge set C, item 8, design docs/superpowers/specs/2026-09-28-same-flight-
instrument-phase2-perception-variants-design.md section 5: "Acceptance tests (unit, fake core)").

AT-P1..AT-P4 are exercised elsewhere, on the SAME fake-core/receipt-validator level this design
section calls for, plus a live real-graph proof beyond what the design requires:

* **AT-P1** (A's Perception request equals the branch-free request) and **AT-P2** (T's wire bytes
  equal A's): ``tests/unit/test_perception_branch_live.py::
  test_a_three_branch_visit_spends_three_contacts_and_delivers_branch_as_own_text`` (live,
  real graph) plus ``tests/unit/test_perception_branch_variants.py::
  test_receipt_validator_accepts_a_twin_whose_request_sha256_differs_from_as`` (receipt-level).
* **AT-P3** (mutating a non-A note leaves every Reviewer/Planner/A-Solver request byte-identical):
  ``tests/unit/test_perception_branch_node.py::test_non_a_notes_never_reach_the_delivered_output``
  (fake core) and ``tests/unit/test_perception_branch_live.py::
  test_non_a_branch_text_never_reaches_the_solvers_own_history`` (live).
* **AT-P4** (ceiling and budget at both levels): ``tests/unit/test_perception_branch_config.py::
  test_perception_branches_compose_and_extend_the_ceiling_level1`` and
  ``test_perception_branches_extend_the_ceiling_level2``.

This file covers the four the coordinator's brief named directly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS_ANALYSIS = _REPO / "scripts" / "analysis"
if str(_SCRIPTS_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ANALYSIS))

import slurp_perception_branch_read as spbr  # noqa: E402

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_outputs, _verify_outputs_trace_binding,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime, FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)

from test_knowledge_stores import _first_phase_config

SAMPLE = "slurp:train:ATP5:0"
ARM = "speech-feature-query-native-tools"
BRANCH_IDS = ("B", "T", "A")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------------------------------------------------------------------------
# AT-P5: a fake sealed run passes verify_bundle, column render, stub scoring
# and the column paired read.
# ---------------------------------------------------------------------------


def _at_p5_fixture():
    """Two fake sealed rows: A's candidates put gold at rank 2, B's put it at rank 1 on one row
    -- a "promoted" row a paired column read should surface."""

    trace: dict[str, object] = {}
    rows: list[dict] = []
    for sample_index, promote in enumerate((True, False)):
        sample_id = f"slurp:train:ATP5:{sample_index}"
        contacts = []
        candidates = {
            "B": ("gold", "other") if promote else ("other", "gold"),
            "T": ("other", "gold"),
            "A": ("other", "gold"),
        }
        for branch_index, branch_id in enumerate(BRANCH_IDS):
            rid = f"request-atp5-{sample_index}-{branch_index}"
            answer = f"note-{branch_id}-{sample_index}"
            contact = {
                "agent_contact_id": f"perception:{sample_index}:{branch_index}",
                "request_id": rid, "request_sha256": _sha(rid),
                "response_sha256": _sha("envelope-" + rid),
                "response_text_sha256": _sha(answer),
            }
            contacts.append(contact)
            trace[rid + "/request"] = {
                "arm": ARM, "payload": {"sample_id": sample_id},
                "payload_sha256": contact["request_sha256"],
            }
            trace[rid + "/response"] = {
                "text": answer, "response_sha256": contact["response_sha256"],
                "response_text_sha256": contact["response_text_sha256"],
            }
        a_contact = contacts[-1]
        branches_receipt = {
            "schema": "saea-perception-branch-arms-v1", "phase_id": "perception",
            "level": 1, "branch_count": 3, "delivered_branch_id": "A",
            "branch_visits": "first", "visit_index": 0,
            "fit_estimate": {
                "slot_tokens": 24576, "completion_ceiling": 512, "base_prompt_tokens": 100,
                "tokens_per_supplied_item": 10, "reserve_tokens": 3072, "prompt_limit_tokens": 20990,
            },
            "branches": [
                {
                    "branch_index": index, "branch_id": branch_id,
                    "deliver": branch_id == "A",
                    "replicate_of": "A" if branch_id == "T" else None,
                    "resolved_knobs": (
                        [{"path": "knowledge_stores.ex.phase_supply.perception.k", "value": 30}]
                        if branch_id == "B" else []
                    ),
                    "release_swap": None, "presentation_id": None,
                    "min_candidates": None, "supplied_value_ids": [], "supplied_count": 0,
                    "max_supplied_items": 5, "contact_id": contact["agent_contact_id"],
                    "request_sha256": contact["request_sha256"],
                    "response_text_sha256": contact["response_text_sha256"],
                    "note_sha256": contact["response_text_sha256"],
                    "note_parse_status": "ok",
                    "candidate_intent_ids": list(candidates[branch_id]),
                    "presentation_skip_reason": None, "contrast_block_sha256": None,
                    "min_candidates_met": None,
                }
                for index, (branch_id, contact) in enumerate(zip(BRANCH_IDS, contacts))
            ],
        }
        row = {
            "request_id": a_contact["request_id"], "sample_id": sample_id,
            "carrier_lock_key": "slurp", "arm": ARM,
            "text": trace[a_contact["request_id"] + "/response"]["text"],
            "admitted": True, "request_sha256": a_contact["request_sha256"],
            "response_sha256": a_contact["response_sha256"],
            "response_text_sha256": a_contact["response_text_sha256"],
            "native_episode_receipt": {
                "role_visits": [{
                    "role_id": "perception", "stage": "perception",
                    "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]},
                }],
                "perception_branches": branches_receipt,
            },
        }
        rows.append(row)
    return rows, trace


def test_at_p5_fake_sealed_run_passes_verify_bundle_render_score_and_paired_read():
    rows, trace = _at_p5_fixture()

    # verify_bundle: each row individually passes _verify_outputs +
    # _verify_outputs_trace_binding (I7v, the Perception path).
    for row in rows:
        verified = _verify_outputs(
            (json.dumps(row) + "\n").encode(), frozenset({row["sample_id"]}), "slurp", ARM,
        )
        _verify_outputs_trace_binding(verified, trace)

    # column render + stub scoring: each branch's own column, scored against a made-up gold id.
    gold_by_sample = {row["sample_id"]: "gold" for row in rows}
    for row in rows:
        for branch_id in BRANCH_IDS:
            column = spbr.render_branch_column(row, branch_id)
            assert "admitted" not in column  # AT-P8's own property, restated here for this column
            scored = spbr.stub_score_column(column, gold_by_sample[row["sample_id"]])
            assert scored["branch_id"] == branch_id

    # column paired read: B beats A on exactly the one promoted row.
    result = spbr.column_paired_read(rows, gold_by_sample, branch_id="B", against="A")
    assert result["n"] == 2
    assert result["point_pp"] == pytest.approx(50.0, abs=0.01)


# ---------------------------------------------------------------------------
# AT-P6: A's router reproduces the prepared seed and a tampered seed is
# refused.
# ---------------------------------------------------------------------------


def test_at_p6_as_router_reproduces_the_prepared_seed(tmp_path):
    """Structurally the same proof as tests/unit/test_perception_branch_seeds.py, restated here
    under its acceptance-test name for auditability."""

    from speech_aware_evidence_acquisition.rails.supply_variants import parse_perception_branches

    store = "intent-boundaries"
    config, _snapshots = _first_phase_config(tmp_path)
    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values=config), _data_root=tmp_path,
        _knowledge_store_binding=load_knowledge_store_binding(config, data_root=tmp_path),
        _knowledge_store_router_options={},
    )
    import types
    runtime._supply_action_router = types.MethodType(FlightRuntime._supply_action_router, runtime)

    group = parse_perception_branches(
        {
            "level": 1,
            "fit_estimate": {
                "slot_tokens": 24576, "completion_ceiling": 512, "base_prompt_tokens": 4000,
                "tokens_per_supplied_item": 100,
            },
            "branches": [
                {
                    "branch_id": "B", "max_supplied_items": 8,
                    "overrides": {f"knowledge_stores.{store}.phase_supply.direct.k": 1},
                },
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
            ],
        },
        first_phase_id="direct", declared_stores=(store, "slot-contracts"),
    )
    program = default_phase_program("phase-direct-only-supplied-v1")
    plan = SimpleNamespace(split_identity_hash="b" * 64)
    binding = {"speech_packet_bindings": {"s1": {"packet_id": "speech/s1", "sha256": "a" * 64}}}
    expected = {"s1": ("intent-boundaries::value:dim-light", "slot-contracts::value:dim-light")}

    seeds, _receipts = FlightRuntime._perception_branch_seeds(
        runtime, program, binding, group, expected, plan,
    )
    assert seeds["A"] == expected

    tampered = {"s1": ("not-the-real-value",)}
    with pytest.raises(FlightRuntimeError, match="different.*first-phase seed"):
        FlightRuntime._perception_branch_seeds(runtime, program, binding, group, tampered, plan)


# ---------------------------------------------------------------------------
# AT-P7: A's level-2 column equals the sealed first Solver visit after the
# normaliser.
# ---------------------------------------------------------------------------


def _at_p7_row(*, a_solver_response_sha256: str, delivered_response_sha256: str) -> dict:
    return {
        "sample_id": "slurp:train:ATP7:0",
        "response_text_sha256": delivered_response_sha256,
        "native_episode_receipt": {"perception_branches": {
            "branches": [
                {
                    "branch_id": "A", "solver_contact_id": "solver:0",
                    "solver_response_text_sha256": a_solver_response_sha256,
                    "candidate_supply_value_ids": ["v1"],
                },
            ],
        }},
    }


def test_at_p7_as_level2_column_equals_the_delivered_response():
    row = _at_p7_row(a_solver_response_sha256=_sha("answer"), delivered_response_sha256=_sha("answer"))
    spbr.assert_a_level2_column_equals_delivery(row)  # does not raise


def test_at_p7_refuses_when_as_level2_column_disagrees_with_delivery():
    row = _at_p7_row(
        a_solver_response_sha256=_sha("answer"), delivered_response_sha256=_sha("different"),
    )
    with pytest.raises(spbr.PerceptionBranchReadError, match="does not equal the sealed row"):
        spbr.assert_a_level2_column_equals_delivery(row)


def test_at_p7_refuses_a_branch_with_no_level2_column():
    row = {
        "sample_id": "slurp:train:ATP7:1", "response_text_sha256": _sha("x"),
        "native_episode_receipt": {"perception_branches": {
            "branches": [{"branch_id": "A"}],
        }},
    }
    with pytest.raises(spbr.PerceptionBranchReadError, match="no level-2 Solver column"):
        spbr.assert_a_level2_column_equals_delivery(row)


# ---------------------------------------------------------------------------
# AT-P8: a column package never emits `admitted`.
# ---------------------------------------------------------------------------


def test_at_p8_a_rendered_column_never_carries_admitted():
    rows, _trace = _at_p5_fixture()
    for row in rows:
        for branch_id in BRANCH_IDS:
            column = spbr.render_branch_column(row, branch_id)
            spbr.assert_column_package_never_admits(column)  # does not raise
            assert "admitted" not in column


def test_at_p8_refuses_a_column_that_was_given_an_admitted_field():
    column = {"sample_id": "s1", "branch_id": "B", "admitted": True}
    with pytest.raises(spbr.PerceptionBranchReadError, match="never carry its own 'admitted'"):
        spbr.assert_column_package_never_admits(column)


def test_at_p8_the_delivered_row_itself_may_carry_admitted():
    """The property is about a COLUMN package, never about the delivered OUTPUT ROW -- I7's own
    admitted field on the sealed row itself is untouched."""

    rows, _trace = _at_p5_fixture()
    assert rows[0]["admitted"] is True
