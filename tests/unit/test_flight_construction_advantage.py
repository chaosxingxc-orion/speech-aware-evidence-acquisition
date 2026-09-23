"""The Stage-3 S3-4s advantage path through ``core.flight.FlightRuntime``.

Before this slice the ``construction-advantage-text`` arm had no path from a
config to a request at all: ``core.flight.runtime._default_construction_material``
knew only the Audio2Tool proposer material, so every ADV-1 cell died at
``check`` with "a construction-proposer flight's baseline fragment must
declare 'construction_proposer_roster_receipt'". What this file proves, end
to end and with ZERO model contacts:

* the per-row instruction is rendered from S3-3's pinned ``pairs.json``, the
  SEALED rollout's own ``solver_group`` custody and the row's own
  construction gold, and every rendered answer is PROVED equal (by sha256)
  to what ``pairs.json`` pinned for that exact sample index;
* a custody drift, a row outside the prepared population and a fragment
  naming a different template are each refused BY NAME, before any contact;
* nothing a receipt may carry holds an utterance, an answer or the gold;
* the resolver seam dispatches on the ARM -- the proposer material is
  reached by the proposer arm and this material by the advantage arm;
* the whole request path (``FlightRuntime.wire_check``) makes exactly one
  text-only payload per row, whose keys equal
  ``ARM_VISIBLE_FIELDS["construction-advantage-text"]``, whose
  ``construction_targets`` are EXACTLY that row's own, and whose
  ``task_instruction`` is that row's own rendered instruction by sha256;
* the response is read at delivery by
  ``rails.stage3_advantage.parse_advantage_statements_v2`` into a per-row
  RECEIPT (legal/illegal counts, node/kind/target labels, digests);
* the E2.4 gate binds the flying cell's split identity to a committed
  ``roster_role == "construction"`` receipt for this arm too.

Every row here is SYNTHETIC. No real SLURP utterance, answer or gold appears
in this repository, which is exactly the constraint the arm exists under.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.contracts.errors import GateClosed
from speech_aware_evidence_acquisition.contracts.gate_exposure import (
    _ExposureAndCarrierMixin,
)
from speech_aware_evidence_acquisition.contracts.plan import ExecutionPlan
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.flight.runtime import (
    NO_CONSTRUCTION_PHASE_SUPPLY_MESSAGE,
    FlightRuntime,
    FlightRuntimeError,
    _default_construction_material,
    arm_shows_construction_targets,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.rails import AudioRef
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient
from speech_aware_evidence_acquisition.rails.stage3_advantage import (
    STAGE3_ADVANTAGE_ARM,
    parse_advantage_statements_v2,
)
from speech_aware_evidence_acquisition.rails.stage3_advantage_material import (
    Stage3AdvantageMaterialError,
    build_advantage_material,
    render_rollout_answer,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter

CARRIER = "slurp"
POLICY = "phase-stage3-advantage-v2"
ROLLOUT_RUN_ID = "SAEA-TEST-STAGE3-ROLLOUT"
ROLLOUT_ATTEMPT_ID = "attempt-test-stage3-rollout"
PAIRS_RELPATH = "analysis/SAEA-TEST-STAGE3-ROLLOUT-SCORE/pairs.json"
TEMPLATE_RELPATH = "probes/slurp_stage3_advantage_v2.txt"
RUN_ID = "SAEA-TEST-STAGE3-ADVANTAGE"

#: Three synthetic rows is enough for every structural claim and keeps the
#: fixture readable; the real cell flies 225.
SAMPLE_IDS = (
    "slurp:train:000001:audio-1",
    "slurp:train:000002:audio-2",
    "slurp:train:000003:audio-3",
)


# ---------------------------------------------------------------------------
# Synthetic sealed rollout + prepared pairs
# ---------------------------------------------------------------------------


def _answer(sample_id: str, index: int) -> dict[str, object]:
    return {
        "scenario": "synthetic",
        "action": f"act{index}",
        "entities": [{"type": "synthetic_slot", "filler": f"{sample_id}-{index}"}],
    }


def _sealed_row(sample_id: str) -> dict[str, object]:
    return {
        "sample_id": sample_id,
        "arm": "speech-feature-query-native-tools",
        "carrier_lock_key": CARRIER,
        "text": render_rollout_answer(_answer(sample_id, 0)),
        "solver_group": {
            "samples": [
                {
                    "sample_index": index,
                    "parse_status": "ok",
                    "parsed_answer": _answer(sample_id, index),
                    "contacts": [{"request_id": f"flight-{index:04d}"}],
                }
                for index in range(3)
            ]
        },
    }


def _trajectory(sample_id: str) -> dict[str, object]:
    return {
        "schema": "saea-stage3-rollout-trajectory-v1",
        "available": True,
        "perception": {
            "candidate_intent_ids": ["synthetic_act0", "synthetic_act1"],
            "candidate_count": 2,
            # One duplicate the first-occurrence-distinct projection folded,
            # so the raw count and the distinct count differ on purpose.
            "raw_candidate_count": 3,
        },
        "delivered": {
            "kind": "accepted",
            "reviewer_verdicts": [{"visit": 0, "token": "ACCEPT", "disposition": "legal"}],
            "planner_actions": [{"action": "ACCEPT", "legal": True, "revision_count": 0}],
            "revision_count": 0,
        },
    }


def _pairs_document(sample_ids=SAMPLE_IDS) -> dict[str, object]:
    rows = []
    pairs = []
    for sample_id in sample_ids:
        best, worst = 0, 2
        rows.append(
            {
                "sample_id": sample_id,
                "best": {
                    "sample_index": best,
                    "response_text_sha256": hashlib.sha256(
                        render_rollout_answer(_answer(sample_id, best)).encode("utf-8")
                    ).hexdigest(),
                },
                "worst": {
                    "sample_index": worst,
                    "response_text_sha256": hashlib.sha256(
                        render_rollout_answer(_answer(sample_id, worst)).encode("utf-8")
                    ).hexdigest(),
                },
            }
        )
        pairs.append(
            {
                "sample_id": sample_id,
                "best_index": best,
                "worst_index": worst,
                "trajectory": _trajectory(sample_id),
            }
        )
    return {
        "schema": "saea-stage3-rollout-score-v1",
        "stage": "pairs",
        "pairs_schema": "saea-stage3-rollout-pairs-v2",
        "run_id": ROLLOUT_RUN_ID,
        "attempt_id": ROLLOUT_ATTEMPT_ID,
        "rows": rows,
        "pairs": pairs,
    }


def _gold_rows(sample_ids=SAMPLE_IDS) -> dict[str, dict[str, object]]:
    return {
        sample_id: {
            "utterance_id": sample_id.rsplit(":", 1)[0],
            "scenario": "synthetic",
            "action": "act0",
            "intent": "synthetic_act0",
            "sentence": "synthetic spoken request",
            "entities": (("synthetic_slot", f"{sample_id}-gold"),),
        }
        for sample_id in sample_ids
    }


def _lay_out_data(tmp_path: Path, *, document=None, sample_ids=SAMPLE_IDS) -> Path:
    data_root = tmp_path / "data"
    sealed = data_root / "runs" / ROLLOUT_RUN_ID / ROLLOUT_ATTEMPT_ID
    sealed.mkdir(parents=True, exist_ok=True)
    (sealed / f"{ROLLOUT_RUN_ID}.outputs.jsonl").write_text(
        "".join(
            json.dumps(_sealed_row(sample_id), sort_keys=True) + "\n"
            for sample_id in sample_ids
        ),
        encoding="utf-8",
    )
    pairs_path = data_root / PAIRS_RELPATH
    pairs_path.parent.mkdir(parents=True, exist_ok=True)
    pairs_path.write_text(
        json.dumps(document if document is not None else _pairs_document(sample_ids)),
        encoding="utf-8",
    )
    return data_root


def _template(repo_root: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "configs" / TEMPLATE_RELPATH
    path = repo_root / "configs" / TEMPLATE_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _values(data_root: Path) -> dict[str, object]:
    pairs_path = data_root / PAIRS_RELPATH
    return {
        "arm": STAGE3_ADVANTAGE_ARM,
        "policy": POLICY,
        "carrier_lock_key": CARRIER,
        "scorers": ["cost"],
        "phase_material": {
            "advantage": {
                "instruction_template": TEMPLATE_RELPATH,
                "instruction_fill": None,
                "response_format_id": "stage3-advantage-statement-v2",
                "predecessor_binding": "none",
            }
        },
        "advantage_pairs": {
            "relpath": PAIRS_RELPATH,
            "sha256": hashlib.sha256(pairs_path.read_bytes()).hexdigest(),
            "rollout_run_id": ROLLOUT_RUN_ID,
            "rollout_attempt_id": ROLLOUT_ATTEMPT_ID,
        },
    }


class _StubSample:
    def __init__(self, sample_id: str) -> None:
        self.sample_id = sample_id


@pytest.fixture()
def gold(monkeypatch):
    rows = _gold_rows()

    def _load(lock, root, sample_ids):
        missing = sorted(set(sample_ids) - set(rows))
        if missing:
            raise AssertionError(f"gold asked for an unprepared row: {missing}")
        return {sample_id: rows[sample_id] for sample_id in sample_ids}

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.slurp."
        "load_slurp_train_construction_rows",
        _load,
    )
    return rows


def _material(tmp_path: Path, *, sample_ids=SAMPLE_IDS, document=None):
    repo_root = tmp_path / "repo"
    _template(repo_root)
    data_root = _lay_out_data(tmp_path, document=document)
    values = _values(data_root)
    return build_advantage_material(
        values,
        lock={},
        data_root=data_root,
        repo_root=repo_root,
        samples=[_StubSample(sample_id) for sample_id in sample_ids],
    )


# ---------------------------------------------------------------------------
# The material: custody equality, refusals, and a text-free receipt
# ---------------------------------------------------------------------------


def test_the_arm_is_construction_visible_off_the_d2_freeze() -> None:
    assert arm_shows_construction_targets(STAGE3_ADVANTAGE_ARM) is True


def test_each_row_renders_the_custodied_best_and_worst_answers(tmp_path, gold) -> None:
    material = _material(tmp_path)
    assert [contact.sample_id for contact in material.contacts] == list(SAMPLE_IDS)
    for contact in material.contacts:
        sample_id = contact.sample_id
        best = render_rollout_answer(_answer(sample_id, 0))
        worst = render_rollout_answer(_answer(sample_id, 2))
        # Byte-for-byte: the custodied answers are IN the instruction, and
        # the sealed row's own delivered text is too.
        assert best in contact.instruction
        assert worst in contact.instruction
        assert _sealed_row(sample_id)["text"] in contact.instruction
        assert f"{sample_id}-gold" in contact.instruction
        assert contact.best_answer_sha256 == hashlib.sha256(
            best.encode("utf-8")
        ).hexdigest()
        assert contact.worst_answer_sha256 == hashlib.sha256(
            worst.encode("utf-8")
        ).hexdigest()
        assert contact.construction_target_ids == (sample_id,)
        assert "{" + "candidate_list" + "}" not in contact.instruction


def test_the_instruction_shows_everything_section_3_requires(tmp_path, gold) -> None:
    """Preregistration section 3: the candidate list in first-occurrence
    distinct order WITH the raw count, ANSWER A and ANSWER B, the delivered
    answer with the Reviewer verdict labels and the Planner route (action
    labels, revision count, delivery kind), and the row's own gold."""

    contact = _material(tmp_path).contacts[0]
    text = contact.instruction
    assert "1. synthetic_act0" in text and "2. synthetic_act1" in text
    assert "(3 candidate(s) proposed; 2 distinct id(s) above" in text
    assert "visit 0: ACCEPT" in text
    assert "1. ACCEPT (legal, revisions so far 0)" in text
    assert "(delivery: accepted; revisions: 0)" in text
    for heading in (
        "PERCEPTION CANDIDATES",
        "ANSWER A",
        "ANSWER B",
        "DELIVERED ANSWER",
        "REVIEWER VERDICTS",
        "PLANNER ROUTE",
        "CORRECT ANSWER",
    ):
        assert heading in text


def test_a_custody_drift_is_refused_by_name(tmp_path, gold) -> None:
    document = _pairs_document()
    document["rows"][1]["best"]["response_text_sha256"] = "f" * 64
    with pytest.raises(Stage3AdvantageMaterialError, match="renders to"):
        _material(tmp_path, document=document)


def test_a_row_outside_the_prepared_population_is_refused(tmp_path, gold) -> None:
    # pairs.json names only the first two rows; the flight still carries three.
    document = _pairs_document(SAMPLE_IDS[:2])
    with pytest.raises(
        Stage3AdvantageMaterialError, match="not in the disagreeing population"
    ):
        _material(tmp_path, document=document)


def test_a_pairs_digest_mismatch_is_refused(tmp_path, gold) -> None:
    repo_root = tmp_path / "repo"
    _template(repo_root)
    data_root = _lay_out_data(tmp_path)
    values = _values(data_root)
    values["advantage_pairs"] = dict(values["advantage_pairs"], sha256="a" * 64)
    with pytest.raises(Stage3AdvantageMaterialError, match="SHA-256 mismatch"):
        build_advantage_material(
            values,
            lock={},
            data_root=data_root,
            repo_root=repo_root,
            samples=[_StubSample(sample_id) for sample_id in SAMPLE_IDS],
        )


def test_a_fragment_naming_another_template_is_refused(tmp_path, gold) -> None:
    repo_root = tmp_path / "repo"
    _template(repo_root)
    data_root = _lay_out_data(tmp_path)
    values = _values(data_root)
    values["phase_material"]["advantage"]["instruction_template"] = "probes/other.txt"
    with pytest.raises(Stage3AdvantageMaterialError, match="not the pinned"):
        build_advantage_material(
            values,
            lock={},
            data_root=data_root,
            repo_root=repo_root,
            samples=[_StubSample(sample_id) for sample_id in SAMPLE_IDS],
        )


def test_no_receipt_carries_an_utterance_an_answer_or_the_gold(tmp_path, gold) -> None:
    material = _material(tmp_path)
    rendered = json.dumps(material.as_json(), sort_keys=True)
    assert "synthetic spoken request" not in rendered
    for sample_id in SAMPLE_IDS:
        assert f"{sample_id}-gold" not in rendered
        assert render_rollout_answer(_answer(sample_id, 0)) not in rendered
    # What a receipt DOES carry: identity, counts and digests.
    first = material.contacts[0].as_json()
    assert set(first) >= {
        "sample_id",
        "best_sample_index",
        "worst_sample_index",
        "best_answer_sha256",
        "worst_answer_sha256",
        "delivered_answer_sha256",
        "gold_sha256",
        "prompt_sha256",
        "prompt_characters",
    }


def test_the_resolver_seam_dispatches_on_the_arm(tmp_path, gold) -> None:
    repo_root = tmp_path / "repo"
    _template(repo_root)
    data_root = _lay_out_data(tmp_path)
    values = _values(data_root)
    material = _default_construction_material(
        values,
        lock={},
        data_root=data_root,
        repo_root=repo_root,
        samples=[_StubSample(sample_id) for sample_id in SAMPLE_IDS],
    )
    assert [contact.sample_id for contact in material.contacts] == list(SAMPLE_IDS)
    # The proposer arm still reaches the proposer material, whose own refusal
    # is the one it always had.
    with pytest.raises(FlightRuntimeError, match="construction_proposer_roster_receipt"):
        _default_construction_material(
            dict(values, arm="construction-proposer-text"),
            lock={},
            data_root=data_root,
            repo_root=repo_root,
            samples=[_StubSample(sample_id) for sample_id in SAMPLE_IDS],
        )


# ---------------------------------------------------------------------------
# The E2.4 gate on this arm
# ---------------------------------------------------------------------------


class _RosterProbe(_ExposureAndCarrierMixin):
    def __init__(self, source_root: Path) -> None:
        self.source_root = source_root


def _roster_identity() -> str:
    """The identity the gate recomputes from the receipt's own items."""

    ids = sorted(f"{CARRIER}/{sample_id}" for sample_id in SAMPLE_IDS)
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def _construction_roster() -> dict[str, object]:
    return {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "SYNTH-STAGE3-ADVANTAGE",
        "carrier_lock_key": CARRIER,
        "roster_role": "construction",
        "split_role": "discovery",
        "split_identity_hash": _roster_identity(),
        "items": [{"sample_id": sample_id} for sample_id in SAMPLE_IDS],
    }


def _land(root: Path, receipt: Mapping[str, object], name: str) -> None:
    path = root / "docs" / "receipts" / "rosters" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")


def _plan_for(identity_hash: str, *, split_role: str = "discovery") -> ExecutionPlan:
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=CARRIER,
        split_role=split_role,
        split_identity_hash=identity_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-stage3-advantage-0001",
    )


def test_the_gate_binds_the_flying_cells_identity_to_a_construction_roster(
    tmp_path,
) -> None:
    identity = _roster_identity()
    _land(tmp_path, _construction_roster(), "synth-stage3-advantage")
    probe = _RosterProbe(tmp_path)
    probe._require_construction_role_for_visible_targets(
        _plan_for(identity), STAGE3_ADVANTAGE_ARM
    )
    with pytest.raises(GateClosed, match="roster_role='construction'"):
        probe._require_construction_role_for_visible_targets(
            _plan_for("d" * 64), STAGE3_ADVANTAGE_ARM
        )
    with pytest.raises(GateClosed, match="only on a discovery split"):
        probe._require_construction_role_for_visible_targets(
            _plan_for(identity, split_role="test"), STAGE3_ADVANTAGE_ARM
        )


# ---------------------------------------------------------------------------
# FlightRuntime: the dispatch and the whole request path
# ---------------------------------------------------------------------------


def _relpath(sample_id: str) -> str:
    return f"datasets/{CARRIER}/media/{sample_id.replace(':', '_')}.wav"


def _write_wav(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 16000)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _RuntimeSample:
    def __init__(self, sample_id: str, data_root: Path) -> None:
        self.sample_id = sample_id
        relpath = _relpath(sample_id)
        digest = _write_wav(data_root / relpath)
        self.audio_ref = AudioRef(path=relpath, sha256=digest).validate()
        self.audio_seconds = 1.0
        self.media_relpath = relpath


class _AdvantageAdapter(TaskAdapter):
    SERVING_SLOTS = 1
    SERVING_SLOT_TOKENS = 32768
    SERVING_MAX_TOKENS = 256

    samples: tuple = ()

    def __init__(self, lock, root) -> None:
        self._lock = lock
        self._root = Path(root)

    def load_split(self, split_id: str):
        return type(self).samples

    def build_task_contract(self, sample, obs) -> str:
        return "contract"

    def instruction(self, sample) -> str:
        return "adapter instruction that an advantage flight must NOT send"

    def gold(self, sample):  # pragma: no cover -- never scored
        raise AssertionError("an advantage flight must never resolve gold here")

    def score_response(self, gold, response):  # pragma: no cover
        raise AssertionError("an advantage flight must never score a row")


class _ArmAwareGate:
    def __init__(self) -> None:
        self.arms: list[str | None] = []

    def assert_model_touch_allowed(
        self, plan, *, full_hash=None, diagnostics=None, arm=None
    ):
        self.arms.append(arm)
        return None


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    _template(repo_root)
    for relpath, document in (
        (
            "configs/model/m.json",
            {
                "model_lock_key": "fake-lock",
                "transport": "fake",
                "decoding_params": {"id_slot": 0, "temperature": 0},
            },
        ),
        (
            "configs/dataset/d.json",
            {"carrier_lock_key": CARRIER, "split_id": "fake-split"},
        ),
        (
            "configs/baseline/b.json",
            {
                "arm": STAGE3_ADVANTAGE_ARM,
                "policy": POLICY,
                "scorers": ["cost"],
                "phase_material": {
                    "advantage": {
                        "instruction_template": TEMPLATE_RELPATH,
                        "instruction_fill": None,
                        "response_format_id": "stage3-advantage-statement-v2",
                        "predecessor_binding": "none",
                    }
                },
            },
        ),
        (
            "configs/experiment/e.json",
            {
                "execution_plan": {
                    "execution_profile": "bounded-discovery-probe",
                    "split_role": "discovery",
                    "planned_model_calls": 10,
                    "planned_gpu_hours": 1.0,
                    "planned_speech_audio_seconds": 100,
                }
            },
        ),
    ):
        path = repo_root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")
    ledger = repo_root / "docs" / "exposure-ledger.md"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        "| run/experiment id | consumed |\n| --- | --- |\n" f"| {RUN_ID} | no |\n",
        encoding="utf-8",
    )
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "test snapshot")
    return repo_root


_ADVANTAGE_RESPONSE = (
    "NODE: solver\n"
    "DELTA-KIND: slot-contract\n"
    "TARGET: synthetic_act0\n"
    "STATEMENT: Keep the synthetic slot filler verbatim.\n"
)


def _runtime(tmp_path: Path, gold_rows) -> tuple[FlightRuntime, object]:
    repo_root = _repo(tmp_path)
    data_root = _lay_out_data(tmp_path)
    values = _values(data_root)
    material = build_advantage_material(
        values,
        lock={},
        data_root=data_root,
        repo_root=repo_root,
        samples=[_StubSample(sample_id) for sample_id in SAMPLE_IDS],
    )
    _AdvantageAdapter.samples = tuple(
        _RuntimeSample(sample_id, data_root) for sample_id in SAMPLE_IDS
    )
    runtime = FlightRuntime(
        repo_root,
        data_root,
        model="m",
        dataset="d",
        baseline="b",
        experiment="e",
        run_id=RUN_ID,
        attempt_id="attempt-001",
        runtime_root=tmp_path / "runtime",
        adapter_factory=lambda lock, root: _AdvantageAdapter(lock, root),
        gate_factory=lambda *a, **kw: _ArmAwareGate(),
        client_factory=FrozenCoreClient,
        carrier_root_resolver=lambda lock, key, root: Path(root) / "datasets" / key,
        construction_material_resolver=lambda values, **_kw: material,
        lock={},
    )
    return runtime, material


def test_the_prompt_budget_fits_the_advantage_instruction(tmp_path, gold) -> None:
    runtime, material = _runtime(tmp_path, gold)
    receipt = runtime.preflight()
    assert receipt["prompt_budget"]
    assert receipt["prompt_budget"][0]["phase"] == "advantage"


def test_the_wire_check_proves_one_text_only_payload_per_row(tmp_path, gold) -> None:
    runtime, material = _runtime(tmp_path, gold)
    receipt = runtime.wire_check(
        seal_and_score=False, response_text=_ADVANTAGE_RESPONSE
    )

    assert receipt["model_contacts"] == 0
    assert receipt["arm"] == STAGE3_ADVANTAGE_ARM
    assert receipt["construction_proposer_arm"] is True
    assert receipt["policy_kind"] == "direct-construction-advantage"
    assert receipt["payload_keys"] == sorted(ARM_VISIBLE_FIELDS[STAGE3_ADVANTAGE_ARM])
    assert receipt["contact_count"] == len(SAMPLE_IDS)
    draws = {record["draw_id"]: record for record in receipt["construction_draws"]}
    assert len(draws) == len(SAMPLE_IDS)
    rendered = json.dumps(receipt, sort_keys=True, default=str)
    assert "synthetic spoken request" not in rendered
    for sample_id in SAMPLE_IDS:
        assert f"{sample_id}-gold" not in rendered


def test_the_response_is_parsed_at_delivery_into_a_text_free_receipt(
    tmp_path, gold
) -> None:
    runtime, material = _runtime(tmp_path, gold)
    runtime.wire_check(seal_and_score=False, response_text=_ADVANTAGE_RESPONSE)
    rows = runtime._output_rows
    assert len(rows) == len(SAMPLE_IDS)
    expected = parse_advantage_statements_v2(_ADVANTAGE_RESPONSE).receipt()
    for row in rows:
        statements = row["advantage_statements"]
        assert statements == expected
        assert statements["legal"] is True
        assert statements["legal_block_count"] == 1
        assert statements["blocks"][0]["node"] == "solver"
        assert statements["blocks"][0]["delta_kind"] == "slot-contract"
        # The statement TEXT never enters the receipt.
        assert "Keep the synthetic slot filler verbatim." not in json.dumps(
            statements, sort_keys=True
        )


def test_the_sealed_row_keeps_the_delivery_read(tmp_path, gold) -> None:
    runtime, material = _runtime(tmp_path, gold)
    runtime.wire_check(seal_and_score=False, response_text=_ADVANTAGE_RESPONSE)
    sealed = runtime._canonical_output_rows(runtime._client)
    assert len(sealed) == len(SAMPLE_IDS)
    expected = parse_advantage_statements_v2(_ADVANTAGE_RESPONSE).receipt()
    for row in sealed:
        assert row["advantage_statements"] == expected
        assert row["arm"] == STAGE3_ADVANTAGE_ARM
        assert row["text"] == _ADVANTAGE_RESPONSE


def test_the_construction_draws_seal_the_per_row_identities(tmp_path, gold) -> None:
    runtime, material = _runtime(tmp_path, gold)
    receipt = runtime.wire_check(
        seal_and_score=False, response_text=_ADVANTAGE_RESPONSE
    )
    draws = {record["sample_id"]: record for record in receipt["construction_draws"]}
    assert set(draws) == set(SAMPLE_IDS)
    for sample_id, record in draws.items():
        contact = material.by_sample()[sample_id]
        assert record["best_sample_index"] == 0
        assert record["worst_sample_index"] == 2
        assert record["best_answer_sha256"] == contact.best_answer_sha256
        assert record["worst_answer_sha256"] == contact.worst_answer_sha256
        assert record["gold_sha256"] == contact.gold_sha256
        assert record["prompt_sha256"] == contact.prompt_sha256
        assert record["candidate_intent_ids"] == ["synthetic_act0", "synthetic_act1"]
        assert record["reviewer_verdict_dispositions"] == ["ACCEPT"]
        assert record["planner_actions"] == ["ACCEPT"]
        assert record["delivered_kind"] == "accepted"


def test_the_dispatch_declares_the_program_and_its_single_phase(tmp_path, gold) -> None:
    runtime, material = _runtime(tmp_path, gold)
    receipt = runtime.wire_check(
        seal_and_score=False, response_text=_ADVANTAGE_RESPONSE
    )
    assert receipt["dispatch"]["program_id"] == POLICY
    assert receipt["dispatch"]["phase_names"] == ["advantage"]
    material_receipt = receipt["phase_material"]
    assert material_receipt["instruction_is_per_row"] is True
    phase = material_receipt["phases"][0]
    assert phase["spec"]["response_format_id"] == "stage3-advantage-statement-v2"
    assert phase["response_format_sha256"]


# ---------------------------------------------------------------------------
# Item E42: the prepared-phase-supply question this arm answers with "none"
#
# The offline preparation path (``core.flight.repin`` -> ``prepare-supply``)
# used to walk the SPEECH phase-program binding for every non-fixed policy and
# died on "phase programs require an explicit feature or raw speech arm" --
# true of a speech cell, meaningless for an arm whose whole dispatch is
# ``_dispatch_fixed_policy``. These prove the honest answer, and that it stays
# scoped to exactly this shape.
# ---------------------------------------------------------------------------


def test_the_advantage_cell_reports_no_prepared_phase_supply(tmp_path, gold) -> None:
    runtime, _material = _runtime(tmp_path, gold)

    assert (
        runtime._prepared_phase_supply_absent_reason()
        == NO_CONSTRUCTION_PHASE_SUPPLY_MESSAGE
    )
    with pytest.raises(PreparationError) as identity_error:
        runtime.phase_supply_artifact_identity()
    assert str(identity_error.value) == NO_CONSTRUCTION_PHASE_SUPPLY_MESSAGE

    target = tmp_path / "prepared" / "phase-supply-v1.json"
    with pytest.raises(PreparationError) as prepare_error:
        runtime.prepare_phase_supply(target)
    assert str(prepare_error.value) == NO_CONSTRUCTION_PHASE_SUPPLY_MESSAGE
    assert not target.exists()


@pytest.mark.parametrize(
    "key, value",
    [
        ("knowledge_stores", {"slot-contracts": {"view": "v1"}}),
        ("phase_supply", {"advantage": {"provider": "kb-facet-v1"}}),
        ("prepared_phase_supply", {"relpath": "prepared/x.json", "sha256": "a" * 64}),
        ("prepared_phase_recall", {"advantage": {"relpath": "prepared/r.json", "sha256": "b" * 64}}),
    ],
)
def test_a_construction_cell_that_declares_supply_is_refused_by_name(
    tmp_path, gold, key, value
) -> None:
    runtime, _material = _runtime(tmp_path, gold)
    baseline = runtime._repo_root / "configs" / "baseline" / "b.json"
    document = json.loads(baseline.read_text(encoding="utf-8"))
    document[key] = value
    baseline.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(FlightRuntimeError) as error:
        runtime.phase_supply_artifact_identity()
    message = str(error.value)
    assert key in message
    assert "undefined" in message


def test_a_speech_arm_is_untouched_by_the_construction_answer(tmp_path, gold) -> None:
    """The guard reads the ARM, not the policy: a speech cell keeps its own
    (unchanged) phase-supply derivation, refusals included."""
    runtime, _material = _runtime(tmp_path, gold)
    baseline = runtime._repo_root / "configs" / "baseline" / "b.json"
    document = json.loads(baseline.read_text(encoding="utf-8"))
    document["arm"] = "speech-feature-query-native-tools"
    baseline.write_text(json.dumps(document), encoding="utf-8")

    assert runtime._prepared_phase_supply_absent_reason() is None
