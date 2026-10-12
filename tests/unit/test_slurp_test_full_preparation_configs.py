"""Preparations 2 and 3 of the SLURP test-full read: the two committed configs.

Owner decisions 99 (2026-09-22) and 107 (2026-09-23). Companion to
``tests/unit/test_slurp_test_full_preprocess_roster.py``, which covers
preparation 1 (the featcache packets).

Covered here:

* ``configs/preparation/slurp-test-full-speech-query-encoding-protocol-v1.json``
  -- the ``saea-speech-query-encoding-protocol-v1`` the step-2b encoder run
  binds, checked through the runtime's OWN loaders
  (``core.speech_preparation_runtime.pinned_json`` / ``confined``,
  ``core.preparation_speech_queries.segment_plan``,
  ``contracts.ExecutionPlan``) rather than against a re-implementation; and
* ``configs/preparation/slurp-test-full-query-alias-v1.json`` -- the step-2c
  dimension-alias TEMPLATE, whose two step-2b digests stay ``PENDING_STEP_2B_*``
  until the roster-agnostic materialiser
  ``scripts/flights/batch/r01_prep23_steps.materialise_alias_config`` binds them.

And, above all, the refusal: the step-2b ExecutionPlan carries split role
``final-report`` and is refused today, because the committed owner-allowance
receipt says ``pending-owner``.

ZERO model, encoder, tokenizer, scorer, GPU and network contacts, and no audio
sample, sentence, gold label, transcript or score is read. ``verify_encoder`` is
the one step of ``run_preparation`` deliberately NOT reproduced here: it
re-hashes the whole frozen Omni-Embed-Nemotron directory, which belongs to the
run itself.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (":" + _existing_pythonpath if _existing_pythonpath else "")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    FINAL_REPORT_SPLIT_ROLE,
    ExecutionPlan,
    ExecutionScopeError,
)
from speech_aware_evidence_acquisition.core import (  # noqa: E402
    speech_preparation_runtime as runtime,
)
from speech_aware_evidence_acquisition.core.preparation_speech_queries import (  # noqa: E402
    segment_plan,
)

RUN = "SAEA-SLURP-TEST-FULL-SPEECH-QUERY-ENCODING-V1"
EXPORT_ROW = "SAEA-SLURP-TEST-FULL-QUERY-VECTOR-EXPORT-V1"
PROTOCOL_RELPATH = (
    "configs/preparation/slurp-test-full-speech-query-encoding-protocol-v1.json"
)
ALIAS_RELPATH = "configs/preparation/slurp-test-full-query-alias-v1.json"
PRECEDENT_PROTOCOL_RELPATH = (
    "configs/preparation/slurp-stage3-construction-r01-speech-query-encoding-protocol-v1.json"
)
DATASET_RELPATH = "configs/dataset/slurp-speech-native-test-full.json"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-test-full-13078-v1.json"
ALLOWANCE_RELPATH = "docs/receipts/owner/2026-09-23-slurp-test-split-allowance-v1.json"
INVENTORY_RELPATH = "coordination/slurp-test-full-speech-query-source-inventory-v1.json"
INVENTORY_SHA256 = "c16ede61a994ef5b2920ab0b9a446203574ee7c731e4c8cae7e5a31e1306ca5f"
SPLIT_IDENTITY = "7247647b8c8b37becd564b7031691565d4e6b09d8e124823054906d36372c95d"
ROSTER_ROWS = 13078
PLANNED_SPEECH_SECONDS = 36912


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


steps = _load("prep23_steps_test_full", "scripts/flights/batch/r01_prep23_steps.py")


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(relpath: str):
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


PROTOCOL = load_json(PROTOCOL_RELPATH)
ALIAS_TEMPLATE = load_json(ALIAS_RELPATH)
PROTOCOL_SHA256 = raw_sha256(REPO / PROTOCOL_RELPATH)
ALLOWANCE = {
    "path": ALLOWANCE_RELPATH,
    "sha256": raw_sha256(REPO / ALLOWANCE_RELPATH),
}


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    root = Path(raw) if raw else None
    return root if root is not None and root.is_dir() else None


requires_data_root = pytest.mark.skipif(
    _data_root() is None, reason="SPEECHRL_DATA_DIR is not materialised on this host"
)


# ---------------------------------------------------------------------------
# The step-2b encoding protocol.
# ---------------------------------------------------------------------------


def test_protocol_carries_the_registered_recipe_constants() -> None:
    assert PROTOCOL["schema"] == "saea-speech-query-encoding-protocol-v1"
    assert PROTOCOL["expected_unique_spans"] == ROSTER_ROWS
    assert PROTOCOL["query_prompt"] == "query: "
    assert PROTOCOL["dimension"] == 2048
    assert PROTOCOL["monitor_interval_seconds"] == 10
    assert PROTOCOL["max_seconds"] == 120.0
    assert PROTOCOL["overlap_seconds"] == 8.0
    assert PROTOCOL["boundary_policy"] == "fixed-stride-complete-final-tail-v1"


def test_cpu_workers_is_eight_and_inside_the_runtime_s_own_bound() -> None:
    """8 is the standing CPU ceiling and the runtime's own upper bound."""

    assert PROTOCOL["cpu_workers"] == 8
    assert type(PROTOCOL["cpu_workers"]) is int
    assert 1 <= PROTOCOL["cpu_workers"] <= 8


def test_protocol_recipe_matches_the_r01_precedent_field_for_field() -> None:
    """Only the roster-bound fields and cpu_workers may differ."""

    precedent = load_json(PRECEDENT_PROTOCOL_RELPATH)
    assert set(PROTOCOL) == set(precedent)
    roster_bound = {
        "cache_relpath",
        "cpu_workers",
        "expected_unique_spans",
        "isolation",
        "output_relpath",
        "query_rows_relpath",
        "roster_sha256",
        "sources",
    }
    for key in set(PROTOCOL) - roster_bound:
        assert PROTOCOL[key] == precedent[key], key
    for key in roster_bound:
        assert PROTOCOL[key] != precedent[key], key


def test_protocol_roster_hash_is_the_committed_roster_receipt() -> None:
    roster_sha256 = raw_sha256(REPO / ROSTER_RELPATH)
    assert PROTOCOL["roster_sha256"] == roster_sha256
    assert PROTOCOL["sources"]["derived_from"]["roster_receipt"] == {
        "path": ROSTER_RELPATH,
        "sha256": roster_sha256,
    }
    receipt = load_json(ROSTER_RELPATH)
    assert receipt["roster_id"] == "SLURP-TEST-FULL-13078-V1"
    assert receipt["split_role"] == FINAL_REPORT_SPLIT_ROLE
    assert len(receipt["items"]) == PROTOCOL["expected_unique_spans"] == ROSTER_ROWS


def test_protocol_runtime_view_pin_is_the_committed_dataset_fragment() -> None:
    view = load_json(DATASET_RELPATH)
    pinned = PROTOCOL["sources"]["derived_from"]["runtime_view"]
    assert pinned["path"] == DATASET_RELPATH
    assert pinned["raw_sha256"] == raw_sha256(REPO / DATASET_RELPATH)
    assert pinned["canonical_runtime_view_sha256"] == view["runtime_view_sha256"]
    assert view["split_identity_hash"] == SPLIT_IDENTITY
    assert view["count"] == ROSTER_ROWS


def test_protocol_sources_pin_the_step_2a_inventory_not_the_runtime_view() -> None:
    sources = PROTOCOL["sources"]
    assert sources["schema"] == "saea-speech-query-source-inventory-v1"
    assert sources["sha256"] == INVENTORY_SHA256
    assert sources["path"].endswith("/" + INVENTORY_RELPATH)
    assert sources["path"].startswith("${SAEA_DATA_ROOT}/")  # data-root placeholder (owner rulings 289 B / 290 B)


def test_protocol_artifact_paths_are_confined_and_name_this_roster(tmp_path: Path) -> None:
    keys = ("output_relpath", "query_rows_relpath", "cache_relpath")
    resolved = {key: runtime.confined(tmp_path, PROTOCOL[key]) for key in keys}
    assert len(set(resolved.values())) == len(keys)
    assert PROTOCOL["output_relpath"] == "prepared/%s/index.json" % RUN
    assert PROTOCOL["query_rows_relpath"] == "prepared/%s/queries.jsonl" % RUN
    assert PROTOCOL["cache_relpath"] == "prepared/slurp-test-full-speech-query-span-cache-v1"
    for path in resolved.values():
        assert path.is_relative_to(tmp_path.resolve())


PROSE_KEYS = frozenset(
    {"answer_authority", "built_by", "contact_policy", "how_to_fill", "isolation",
     "registration_note"}
)


def _binding_values(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key not in PROSE_KEYS:
                yield from _binding_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _binding_values(item)
    else:
        yield node


def test_no_other_roster_name_leaks_into_a_binding_field() -> None:
    for label, document in ((PROTOCOL_RELPATH, PROTOCOL), (ALIAS_RELPATH, ALIAS_TEMPLATE)):
        text = " ".join(str(value) for value in _binding_values(document))
        for foreign in (
            "DEV2000", "DEV-2000", "dev2000", "FOLD-A", "fold-a", "DEV-1000",
            "STAGE3-CONSTRUCTION-R01", "stage3-construction-r01",
        ):
            assert foreign not in text, (label, foreign)
        assert "test-full" in text.lower()


# ---------------------------------------------------------------------------
# The refusal.
# ---------------------------------------------------------------------------


def _step_2b_plan(**overrides) -> ExecutionPlan:
    fields = {
        "attempt_id": "encode-v1",
        "carrier_lock_key": "slurp",
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 2.0,
        "planned_model_calls": ROSTER_ROWS,
        "planned_speech_audio_seconds": PLANNED_SPEECH_SECONDS,
        "protocol_hash": PROTOCOL_SHA256,
        "run_id": RUN,
        "split_identity_hash": SPLIT_IDENTITY,
        "split_role": FINAL_REPORT_SPLIT_ROLE,
        "owner_allowance": ALLOWANCE,
    }
    fields.update(overrides)
    return ExecutionPlan(**fields)


def test_the_step_2b_plan_is_refused_today() -> None:
    """``core.speech_preparation_runtime.run_preparation`` builds exactly this
    plan and validates it before its first contact."""

    with pytest.raises(ExecutionScopeError) as error:
        _step_2b_plan().validate()
    message = str(error.value)
    assert "status is 'pending-owner', not 'authorised'" in message
    assert ALLOWANCE_RELPATH in message


def test_the_step_2b_plan_without_an_allowance_is_refused_for_that_reason() -> None:
    with pytest.raises(ExecutionScopeError) as error:
        _step_2b_plan(owner_allowance=None).validate()
    assert "no owner_allowance was declared" in str(error.value)


def test_the_committed_allowance_names_this_run_as_a_preparation() -> None:
    document = load_json(ALLOWANCE_RELPATH)
    assert RUN in document["preparation_run_ids"]
    assert EXPORT_ROW in document["preparation_run_ids"]
    assert RUN in document["permitted_run_ids"]
    assert EXPORT_ROW in document["permitted_run_ids"]
    assert document["split"]["split_identity_hash"] == SPLIT_IDENTITY
    assert document["run_ids"][EXPORT_ROW]["expected_contacts"] == 0


def test_the_plan_numbers_match_the_protocol_and_the_roster() -> None:
    plan_fields = _step_2b_plan()
    assert plan_fields.planned_model_calls == PROTOCOL["expected_unique_spans"]
    view = load_json(DATASET_RELPATH)
    assert plan_fields.planned_speech_audio_seconds >= float(view["audio_seconds_total"])
    assert plan_fields.planned_speech_audio_seconds == PLANNED_SPEECH_SECONDS


# ---------------------------------------------------------------------------
# The inventory, through the runtime's own loaders.
# ---------------------------------------------------------------------------


@requires_data_root
def test_protocol_bindings_load_through_the_runtime_loaders() -> None:
    data_root = _data_root()
    assert data_root is not None
    previous = Path.cwd()
    os.chdir(REPO)
    try:
        protocol = runtime.pinned_json({"path": PROTOCOL_RELPATH, "sha256": PROTOCOL_SHA256})
        sources = runtime.pinned_json(protocol["sources"])
        encoder = runtime.pinned_json(protocol["encoder"])
    finally:
        os.chdir(previous)
    assert sources["roster_sha256"] == protocol["roster_sha256"]
    assert sources["schema"] == "saea-speech-query-source-inventory-v1"
    assert sources["count"] == ROSTER_ROWS
    assert sources["split_identity_hash"] == SPLIT_IDENTITY
    assert encoder["schema"] == "saea-pinned-speech-query-encoder-inventory-v1"


@requires_data_root
def test_the_inventory_reproduces_the_expected_span_count_and_audio_budget() -> None:
    """The exact arithmetic ``run_preparation`` runs before the first contact."""

    data_root = _data_root()
    assert data_root is not None
    sources = json.loads((data_root / INVENTORY_RELPATH).read_text(encoding="utf-8"))
    rows = sources["rows"]
    identity = hashlib.sha256(
        "\n".join(sorted("slurp/%s" % row["id"] for row in rows)).encode("utf-8")
    ).hexdigest()
    assert identity == SPLIT_IDENTITY
    spans = {
        (
            row["audio_sha256"],
            row["source_frames"],
            row["source_sample_rate_hz"],
            span["start_frame"],
            span["end_frame"],
        )
        for row in rows
        for span in segment_plan(
            row["source_frames"],
            row["source_sample_rate_hz"],
            max_seconds=PROTOCOL["max_seconds"],
            overlap_seconds=PROTOCOL["overlap_seconds"],
        )
    }
    audio_seconds = sum((end - start) / rate for _sha, _frames, rate, start, end in spans)
    assert len(spans) == PROTOCOL["expected_unique_spans"] == ROSTER_ROWS
    assert audio_seconds <= PLANNED_SPEECH_SECONDS


# ---------------------------------------------------------------------------
# The step-2c dimension-alias template.
# ---------------------------------------------------------------------------


def test_alias_template_is_the_contract_field_set_plus_the_how_to_fill_note() -> None:
    assert set(ALIAS_TEMPLATE) == steps.ALIAS_CONFIG_FIELDS | {"how_to_fill"}
    assert isinstance(ALIAS_TEMPLATE["how_to_fill"], str)
    assert "PENDING_STEP_2B_QUERIES_SHA256" in ALIAS_TEMPLATE["how_to_fill"]
    assert "PENDING_STEP_2B_RECEIPT_SHA256" in ALIAS_TEMPLATE["how_to_fill"]


def test_alias_template_pending_markers_sit_exactly_where_step_2b_output_lands() -> None:
    assert ALIAS_TEMPLATE["source"]["sha256"] == "PENDING_STEP_2B_QUERIES_SHA256"
    assert ALIAS_TEMPLATE["source_receipts"][0]["sha256"] == "PENDING_STEP_2B_RECEIPT_SHA256"
    text = json.dumps(ALIAS_TEMPLATE)
    assert text.count("PENDING_STEP_2B_QUERIES_SHA256") == 2  # the field and the note
    assert text.count("PENDING_STEP_2B_RECEIPT_SHA256") == 2


def test_alias_template_cross_references_the_protocol_and_the_committed_receipts() -> None:
    assert ALIAS_TEMPLATE["schema"] == "saea-sealed-segment-vector-dimension-alias-v1"
    assert ALIAS_TEMPLATE["expected_rows"] == PROTOCOL["expected_unique_spans"]
    assert ALIAS_TEMPLATE["vector_width"] == PROTOCOL["dimension"]
    assert ALIAS_TEMPLATE["source"]["relpath"] == PROTOCOL["query_rows_relpath"]
    assert ALIAS_TEMPLATE["source"]["kind"] == "sealed-segment-vectors"
    assert ALIAS_TEMPLATE["source"]["dimension"] == "content"
    assert ALIAS_TEMPLATE["target_dimension"] == "intent-boundary"
    assert ALIAS_TEMPLATE["output_relpath"] == (
        "vectors/slurp-test-full-v1/query-vectors-speech-segments.jsonl"
    )
    assert ALIAS_TEMPLATE["receipt_relpath"] == (
        "prepared/SAEA-SLURP-TEST-FULL-ALIAS-V1/query-dimension-alias.json"
    )
    receipts = ALIAS_TEMPLATE["source_receipts"]
    assert receipts[0]["relpath"] == "preparation-runs/%s/encode-v1/receipt.json" % RUN
    assert receipts[0]["root"] == "data"
    assert receipts[1] == {
        "relpath": DATASET_RELPATH,
        "root": "repository",
        "sha256": raw_sha256(REPO / DATASET_RELPATH),
    }
    assert receipts[2] == {
        "relpath": ROSTER_RELPATH,
        "root": "repository",
        "sha256": raw_sha256(REPO / ROSTER_RELPATH),
    }


def test_materialising_the_template_yields_exactly_the_contract_field_set() -> None:
    """The roster-agnostic R01 materialiser is reused verbatim, not forked."""

    config = steps.materialise_alias_config(
        ALIAS_TEMPLATE, queries_sha256="a" * 64, receipt_sha256="b" * 64
    )
    assert set(config) == steps.ALIAS_CONFIG_FIELDS
    assert config["source"]["sha256"] == "a" * 64
    assert config["source_receipts"][0]["sha256"] == "b" * 64
    assert "PENDING_" not in json.dumps(config)
    # The committed bytes stay a template.
    assert ALIAS_TEMPLATE["source"]["sha256"] == "PENDING_STEP_2B_QUERIES_SHA256"


def test_the_three_draft_rows_are_registered_exactly_once_and_unconsumed() -> None:
    """DRAFT rows: written before any contact, never ``consumed = yes``.

    ``contracts.gate_exposure._require_exposure_preregistration`` refuses a run
    id registered more than once and refuses a consumed row outright, so both
    properties are load-bearing, not decoration.
    """

    from speech_aware_evidence_acquisition.contracts import (  # noqa: PLC0415
        _parse_ledger_tables,
    )

    rows = _parse_ledger_tables(
        (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    )
    expected = {
        "SAEA-SN-TEST-FULL-PREPROCESS": ("bounded-discovery-probe", "13078", "36912", "1.0"),
        RUN: ("bounded-discovery-probe", "13078", "36912", "4.0"),
        EXPORT_ROW: ("model-free-check", "0", "0", "0"),
    }
    for run_id, (profile, calls, seconds, gpu_hours) in expected.items():
        matched = [row for row in rows if row.get("run/experiment id") == run_id]
        assert len(matched) == 1, run_id
        row = matched[0]
        assert row["execution profile"] == profile
        assert row["split role"] == FINAL_REPORT_SPLIT_ROLE
        assert row["split identity hash"] == SPLIT_IDENTITY
        assert row["consumed"].strip().lower() == "no"
        assert (row["calls"], row["speech audio seconds"], row["gpu hours"]) == (
            calls,
            seconds,
            gpu_hours,
        )
        assert "DRAFT" in row["notes"]
        assert "owner allowance + root countersignature pending" in row["scope"]


def test_the_plan_note_is_committed_and_names_every_run_id() -> None:
    note = (
        REPO / "docs/readiness/2026-09-23-slurp-test-full-preparations-v1.md"
    ).read_text(encoding="utf-8")
    for run_id in ("SAEA-SN-TEST-FULL-PREPROCESS", RUN, EXPORT_ROW):
        assert run_id in note
    for run_id in (
        "SAEA-SLURP-TEST-FULL-LOCKED-SYSTEM-V1",
        "SAEA-SLURP-TEST-FULL-DIRECT-V1",
    ):
        assert run_id in note
    assert "13,078" in note and "2,974" in note
    assert "36,911.9388125" in note


def test_the_content_derivative_step_reuses_the_generic_r01_cli() -> None:
    """Preparation 3 registers no new tool: it is R01's step 3 on this roster."""

    script = REPO / "scripts/build_slurp_query_content_derivative.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    for flag in ("--source-relpath", "--source-sha256", "--out-dir", "--out-name", "--ledger-row"):
        assert flag in text
