"""Stage-3 S3-4 proof obligations (docs/superpowers/specs/2026-09-22-stage3-
tfrl-base-loop-engineering.md section S3-4 "Proof obligations"): the
``construction-advantage-text`` arm gates exactly like the proposer arm, its
rendered material never reaches a receipt, the closed-form parser never
raises, and the phase program loads.

Every fixture below is synthetic: no real SLURP utterance text, gold or
model output appears anywhere in this file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts.errors import GateClosed
from speech_aware_evidence_acquisition.contracts.gate_exposure import (
    CONSTRUCTION_ROSTER_ROLE,
    ROSTER_RECEIPT_SCHEMA,
    _ExposureAndCarrierMixin,
)
from speech_aware_evidence_acquisition.contracts.identifiers import (
    CONSTRUCTION_VISIBLE_ARMS,
    CONSTRUCTION_VISIBLE_FIELD,
)
from speech_aware_evidence_acquisition.contracts.plan import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import AGENT_CONTROLLERS, RESPONSE_FORMATS
from speech_aware_evidence_acquisition.core.flight.runtime import arm_shows_construction_targets
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.rails import controllers as _controllers  # noqa: F401
from speech_aware_evidence_acquisition.rails.stage3_advantage import (
    STAGE3_ADVANTAGE_ARM,
    STAGE3_ADVANTAGE_PROGRAM_ID,
    STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID,
    LEGAL_DELTA_KINDS,
    AdvantagePair,
    AdvantagePairSample,
    Stage3AdvantageError,
    build_advantage_instruction_for_row,
    load_advantage_pairs,
    parse_advantage_statement,
    render_advantage_instruction,
    stage3_advantage_response_format_v1,
)

CARRIER = "slurp"
TEMPLATE = "ANSWER A:\n{best_answer}\nANSWER B:\n{worst_answer}\nGOLD:\n{gold}\n"


# ---------------------------------------------------------------------------
# Registration: the arm is text-only and gated exactly like the proposer arm.
# ---------------------------------------------------------------------------


def test_arm_is_registered_beside_the_proposer_arm_with_the_same_field_shape() -> None:
    assert STAGE3_ADVANTAGE_ARM in ARM_VISIBLE_FIELDS
    assert STAGE3_ADVANTAGE_ARM in CONSTRUCTION_VISIBLE_ARMS
    proposer_fields = set(ARM_VISIBLE_FIELDS["construction-proposer-text"])
    advantage_fields = set(ARM_VISIBLE_FIELDS[STAGE3_ADVANTAGE_ARM])
    assert advantage_fields == proposer_fields
    bare_core_fields = set(ARM_VISIBLE_FIELDS["bare-core"])
    assert advantage_fields == bare_core_fields | {CONSTRUCTION_VISIBLE_FIELD}


def test_arm_shows_construction_targets_true_for_the_new_arm() -> None:
    assert arm_shows_construction_targets(STAGE3_ADVANTAGE_ARM) is True
    assert arm_shows_construction_targets("bare-core") is False


# ---------------------------------------------------------------------------
# The E2.4/E37-style gate, on a real receipt tree (no fakes).
# ---------------------------------------------------------------------------


class _RosterProbe(_ExposureAndCarrierMixin):
    def __init__(self, source_root: Path) -> None:
        self.source_root = source_root


def _synthetic_roster(
    sample_ids: tuple[str, ...],
    *,
    roster_role: str = CONSTRUCTION_ROSTER_ROLE,
    split_role: str = "discovery",
) -> dict[str, object]:
    ids = [f"{CARRIER}/{sample_id}" for sample_id in sample_ids]
    split_identity_hash = hashlib.sha256(
        "\n".join(sorted(ids)).encode("utf-8")
    ).hexdigest()
    return {
        "schema": ROSTER_RECEIPT_SCHEMA,
        "carrier_lock_key": CARRIER,
        "roster_role": roster_role,
        "split_role": split_role,
        "split_identity_hash": split_identity_hash,
        "items": [{"sample_id": sample_id} for sample_id in sample_ids],
    }


def _land_roster(root: Path, receipt: dict[str, object], name: str) -> str:
    path = root / "docs" / "receipts" / "rosters" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    return str(receipt["split_identity_hash"])


def _plan_for(identity_hash: str, *, split_role: str = "discovery") -> ExecutionPlan:
    return ExecutionPlan(
        run_id="SAEA-TEST-STAGE3-ADVANTAGE",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=CARRIER,
        split_role=split_role,
        split_identity_hash=identity_hash,
        planned_model_calls=10,
        planned_gpu_hours=0.3,
        planned_speech_audio_seconds=0,
        protocol_hash="b" * 64,
        attempt_id="attempt-stage3-advantage-0001",
    )


def test_gate_opens_on_a_committed_construction_roster(tmp_path) -> None:
    identity = _land_roster(
        tmp_path, _synthetic_roster(("synthetic-row-1", "synthetic-row-2")), "synth-construction-r01"
    )
    probe = _RosterProbe(tmp_path)
    probe._require_construction_role_for_visible_targets(_plan_for(identity), STAGE3_ADVANTAGE_ARM)


def test_gate_refuses_a_non_construction_roster(tmp_path) -> None:
    identity = _land_roster(
        tmp_path,
        _synthetic_roster(("synthetic-row-1",), roster_role="evaluation"),
        "synth-evaluation",
    )
    probe = _RosterProbe(tmp_path)
    with pytest.raises(GateClosed, match="roster_role='construction'"):
        probe._require_construction_role_for_visible_targets(_plan_for(identity), STAGE3_ADVANTAGE_ARM)


def test_gate_refuses_when_no_roster_is_committed_at_all(tmp_path) -> None:
    probe = _RosterProbe(tmp_path)
    with pytest.raises(GateClosed, match="model touch refused"):
        probe._require_construction_role_for_visible_targets(
            _plan_for("f" * 64), STAGE3_ADVANTAGE_ARM
        )


def test_gate_refuses_a_non_discovery_split_role(tmp_path) -> None:
    identity = _land_roster(tmp_path, _synthetic_roster(("synthetic-row-1",)), "synth-construction-r01")
    probe = _RosterProbe(tmp_path)
    with pytest.raises(GateClosed, match="only on a discovery split"):
        probe._require_construction_role_for_visible_targets(
            _plan_for(identity, split_role="test"), STAGE3_ADVANTAGE_ARM
        )


# ---------------------------------------------------------------------------
# The phase program and response format registrations.
# ---------------------------------------------------------------------------


def test_phase_program_loads_with_one_phase_and_one_contact() -> None:
    program = AGENT_CONTROLLERS  # import side effect only; resolve via controllers below
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

    loaded = default_phase_program(STAGE3_ADVANTAGE_PROGRAM_ID)
    assert loaded.program_id == STAGE3_ADVANTAGE_PROGRAM_ID
    assert loaded.phase_names() == ("advantage",)
    assert loaded.max_contacts == 1
    assert loaded.stop_rule == "always-run-full-program"
    assert loaded.phase("advantage").response_format_id == STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID
    assert loaded.phase("advantage").knowledge == "none"
    assert STAGE3_ADVANTAGE_PROGRAM_ID in AGENT_CONTROLLERS.names()


def test_response_format_registered_and_matches_the_legal_kind_enum() -> None:
    assert STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID in RESPONSE_FORMATS.names()
    resolved = RESPONSE_FORMATS.resolve(STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID)
    schema = resolved({}, Path("."))
    kind_enum = schema["json_schema"]["schema"]["properties"]["delta_kind"]["enum"]
    assert set(kind_enum) == set(LEGAL_DELTA_KINDS)
    # The module-level function is the same one the registry holds.
    assert resolved is stage3_advantage_response_format_v1


# ---------------------------------------------------------------------------
# The closed-form parser: never raises, retains, marks illegal.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", list(LEGAL_DELTA_KINDS))
def test_parser_accepts_every_legal_kind(kind: str) -> None:
    text = f"DELTA-KIND: {kind}\nTARGET: synthetic_target\nSTATEMENT: A short synthetic statement.\n"
    result = parse_advantage_statement(text)
    assert result.legal is True
    assert result.delta_kind == kind
    assert result.target == "synthetic_target"
    assert result.illegal_reasons == ()


def test_parser_marks_an_illegal_kind_but_retains_every_field() -> None:
    text = "DELTA-KIND: not-a-real-kind\nTARGET: synthetic_target\nSTATEMENT: A statement.\n"
    result = parse_advantage_statement(text)
    assert result.legal is False
    assert "illegal delta-kind" in result.illegal_reasons[0]
    assert result.delta_kind == "not-a-real-kind"
    assert result.statement == "A statement."


def test_parser_enforces_the_forty_word_boundary() -> None:
    exactly_forty = " ".join(["word"] * 40)
    forty_one = " ".join(["word"] * 41)
    legal = parse_advantage_statement(
        f"DELTA-KIND: exemplar-note\nTARGET: t\nSTATEMENT: {exactly_forty}\n"
    )
    illegal = parse_advantage_statement(
        f"DELTA-KIND: exemplar-note\nTARGET: t\nSTATEMENT: {forty_one}\n"
    )
    assert legal.legal is True
    assert illegal.legal is False
    assert any("exceeds 40 words" in reason for reason in illegal.illegal_reasons)


def test_parser_handles_missing_keys_without_raising() -> None:
    result = parse_advantage_statement("DELTA-KIND: exemplar-note\n")
    assert result.legal is False
    assert "missing keys" in result.illegal_reasons[0]
    assert "TARGET" in result.illegal_reasons[0]
    assert "STATEMENT" in result.illegal_reasons[0]


def test_parser_handles_non_string_input_without_raising() -> None:
    result = parse_advantage_statement(None)  # type: ignore[arg-type]
    assert result.legal is False
    assert result.delta_kind == "" and result.target == "" and result.statement == ""


def test_parser_keeps_the_first_occurrence_of_a_repeated_key() -> None:
    text = (
        "DELTA-KIND: intent-boundary\nDELTA-KIND: slot-contract\n"
        "TARGET: t\nSTATEMENT: One sentence.\n"
    )
    result = parse_advantage_statement(text)
    assert result.delta_kind == "intent-boundary"


def test_parser_statement_value_may_contain_a_colon() -> None:
    text = "DELTA-KIND: exemplar-note\nTARGET: t\nSTATEMENT: It used a ratio of 3:1 correctly.\n"
    result = parse_advantage_statement(text)
    assert result.legal is True
    assert result.statement == "It used a ratio of 3:1 correctly."


def test_parser_extra_surrounding_lines_are_ignored() -> None:
    text = (
        "Some preamble the model was not asked for.\n"
        "DELTA-KIND: slot-contract\nTARGET: t\nSTATEMENT: One sentence.\n"
        "Trailing text too.\n"
    )
    result = parse_advantage_statement(text)
    assert result.legal is True


# ---------------------------------------------------------------------------
# Rendered material and parsed statements never reach a receipt.
# ---------------------------------------------------------------------------


def test_statement_receipt_never_carries_the_statement_text() -> None:
    secret = "SYNTHETIC_STATEMENT_MARKER_should_never_leak_into_a_receipt"
    result = parse_advantage_statement(
        f"DELTA-KIND: exemplar-note\nTARGET: t\nSTATEMENT: {secret}\n"
    )
    receipt_bytes = json.dumps(result.receipt())
    assert secret not in receipt_bytes
    assert result.statement_sha256() == hashlib.sha256(secret.encode("utf-8")).hexdigest()


def test_rendered_instruction_is_never_returned_by_any_receipt_helper(tmp_path) -> None:
    secret_best = "SYNTHETIC_BEST_ANSWER_MARKER"
    secret_worst = "SYNTHETIC_WORST_ANSWER_MARKER"
    secret_gold = "SYNTHETIC_GOLD_MARKER"
    pair = AdvantagePair(
        sample_id="synthetic-row-1",
        best=AdvantagePairSample(sample_index=0, response_text_sha256="a" * 64),
        worst=AdvantagePairSample(sample_index=1, response_text_sha256="b" * 64),
    )
    instruction = build_advantage_instruction_for_row(
        TEMPLATE,
        pair,
        best_answer_text=secret_best,
        worst_answer_text=secret_worst,
        gold_text=secret_gold,
    )
    assert secret_best in instruction and secret_worst in instruction and secret_gold in instruction
    pairs_document = {
        "rows": [
            {
                "sample_id": pair.sample_id,
                "best": {"sample_index": 0, "response_text_sha256": "a" * 64},
                "worst": {"sample_index": 1, "response_text_sha256": "b" * 64},
            }
        ]
    }
    pairs_path = tmp_path / "pairs.json"
    pairs_path.write_text(json.dumps(pairs_document), encoding="utf-8", newline="\n")
    pairs = load_advantage_pairs(pairs_path, repo_root=tmp_path)
    receipt_bytes = json.dumps(pairs.receipt())
    for secret in (secret_best, secret_worst, secret_gold):
        assert secret not in receipt_bytes


def test_render_advantage_instruction_requires_every_placeholder() -> None:
    with pytest.raises(Stage3AdvantageError, match="missing placeholder"):
        render_advantage_instruction(
            "no placeholders here", best_answer_text="a", worst_answer_text="b", gold_text="c"
        )


# ---------------------------------------------------------------------------
# pairs.json loading.
# ---------------------------------------------------------------------------


def _write_pairs(tmp_path: Path, *, rollout_run_id: str | None = "SAEA-TEST-ROLLOUT-R1") -> Path:
    document: dict[str, object] = {
        "rows": [
            {
                "sample_id": "synthetic-row-1",
                "best": {"sample_index": 2, "response_text_sha256": "a" * 64},
                "worst": {"sample_index": 4, "response_text_sha256": "b" * 64},
            },
            {
                "sample_id": "synthetic-row-2",
                "best": {"sample_index": 0, "response_text_sha256": "c" * 64},
                "worst": {"sample_index": 3, "response_text_sha256": "d" * 64},
            },
        ]
    }
    if rollout_run_id is not None:
        document["rollout_run_id"] = rollout_run_id
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    return path


def test_load_advantage_pairs_happy_path(tmp_path) -> None:
    path = _write_pairs(tmp_path)
    pairs = load_advantage_pairs(
        path, repo_root=tmp_path, expected_rollout_run_id="SAEA-TEST-ROLLOUT-R1"
    )
    assert len(pairs.pairs) == 2
    by_sample = pairs.by_sample()
    assert by_sample["synthetic-row-1"].best.sample_index == 2
    assert pairs.rollout_run_id == "SAEA-TEST-ROLLOUT-R1"


def test_load_advantage_pairs_refuses_sha256_mismatch(tmp_path) -> None:
    path = _write_pairs(tmp_path)
    with pytest.raises(Stage3AdvantageError, match="SHA-256 mismatch"):
        load_advantage_pairs(path, repo_root=tmp_path, expected_sha256="0" * 64)


def test_load_advantage_pairs_refuses_rollout_run_id_mismatch(tmp_path) -> None:
    path = _write_pairs(tmp_path, rollout_run_id="SAEA-TEST-ROLLOUT-R1")
    with pytest.raises(Stage3AdvantageError, match="rollout_run_id disagrees"):
        load_advantage_pairs(
            path, repo_root=tmp_path, expected_rollout_run_id="SAEA-TEST-ROLLOUT-R2"
        )


def test_load_advantage_pairs_refuses_a_duplicate_sample_id(tmp_path) -> None:
    document = {
        "rows": [
            {
                "sample_id": "synthetic-row-1",
                "best": {"sample_index": 0, "response_text_sha256": "a" * 64},
                "worst": {"sample_index": 1, "response_text_sha256": "b" * 64},
            },
            {
                "sample_id": "synthetic-row-1",
                "best": {"sample_index": 0, "response_text_sha256": "a" * 64},
                "worst": {"sample_index": 1, "response_text_sha256": "b" * 64},
            },
        ]
    }
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    with pytest.raises(Stage3AdvantageError, match="duplicate sample_id"):
        load_advantage_pairs(path, repo_root=tmp_path)


def test_load_advantage_pairs_refuses_a_malformed_row(tmp_path) -> None:
    document = {"rows": [{"sample_id": "synthetic-row-1"}]}
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    with pytest.raises(Stage3AdvantageError, match="missing"):
        load_advantage_pairs(path, repo_root=tmp_path)


def test_load_advantage_pairs_refuses_an_empty_rows_array(tmp_path) -> None:
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps({"rows": []}), encoding="utf-8", newline="\n")
    with pytest.raises(Stage3AdvantageError, match="non-empty array"):
        load_advantage_pairs(path, repo_root=tmp_path)
