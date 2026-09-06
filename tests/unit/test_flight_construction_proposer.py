"""The proposer path through ``core.flight.FlightRuntime`` (track E3c).

Before this slice the ``construction-proposer-text`` arm had no path from a
config to a request at all: ``FlightRuntime`` issues one contact per roster
sample through ``_dispatch_fixed_policy``, which never supplied
``construction_targets`` (EVO-A1 preregistration section 12 item 9, which
names the missing runner a blocker). What this file proves, end to end and
with ZERO model contacts:

* a proposer "roster" is a committed ``roster_role == "construction"``
  receipt whose items ARE the draws, and ``rails.evolution`` refuses an
  evaluation-role receipt, a tampered one, and one from another carrier;
* one payload per draw, whose keys equal
  ``ARM_VISIBLE_FIELDS["construction-proposer-text"]``, whose
  ``construction_targets`` are EXACTLY that draw's M exemplars in the order
  the seeded draw fixed, and whose request body carries no audio part of any
  kind;
* the E2.4 gate fires on the plan at PREFLIGHT (before a server is started),
  and a gate that cannot receive the arm refuses the flight outright;
* the real ``contracts.gate_exposure`` check refuses an EVALUATION identity
  for this arm.

Every construction row here is SYNTHETIC. No real Audio2Tool query text,
gold call or evaluation identity appears in this repository, which is
exactly the constraint the arm exists under.
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
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
    arm_shows_construction_targets,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.rails import AudioRef, build_payload_binding
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient
from speech_aware_evidence_acquisition.rails.evolution import (
    EvolutionError,
    ProposerDraw,
    build_proposer_material,
    plan_proposer_draws,
    proposer_roster_receipt,
    read_proposer_roster,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter

PROPOSER_ARM = "construction-proposer-text"
CARRIER = "fake-carrier"
TARGET_ID = "castContent"
TOOLS = ("castContent", "playMedia")
#: Two exemplars per tool keeps the fixture small; the M of the real cell is
#: ``rails.evolution.EXEMPLARS_PER_TOOL`` and is a parameter, not a literal.
M = 2


# ---------------------------------------------------------------------------
# Synthetic carrier material
# ---------------------------------------------------------------------------


def _registry_rows() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "tool_id": str(index),
            "tool_name": tool,
            "signature": f"{tool}(deviceId: str)",
            "description": f"Synthetic description for {tool}.",
            "domain": "synthetic_domain",
            "category": "synthetic_category",
            "argument_constraints": "",
            "argument_defaults": "",
        }
        for index, tool in enumerate(TOOLS, start=1)
    )


def _pool() -> dict[str, list[str]]:
    return {
        tool: [f"tier1_direct:{index:06d}" for index in _pool_ids(tool)]
        for tool in TOOLS
    }


def _pool_ids(tool: str) -> range:
    base = 100 if tool == TOOLS[0] else 200
    return range(base, base + 4)


def _exemplar_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for tool in TOOLS:
        for index in _pool_ids(tool):
            sample_id = f"tier1_direct:{index:06d}"
            rows[sample_id] = {
                "query": f"synthetic spoken request {index} for {tool}",
                "gold_call": f"{tool}(deviceId='synthetic-{index}')",
                "tool_name": tool,
            }
    return rows


def _media_facts(sample_id: str) -> dict[str, object]:
    return {
        "media_relpath": _relpath(sample_id),
        "audio_sha256": "0" * 64,
        "audio_seconds": 1.0,
    }


def _relpath(sample_id: str) -> str:
    return f"datasets/{CARRIER}/media/{sample_id.replace(':', '_')}.wav"


def _draws(round_index: int = 1, placebo_slot: int | None = 5):
    return plan_proposer_draws(
        {TARGET_ID: TOOLS},
        _pool(),
        round=round_index,
        proposer_slots=(1, 2),
        placebo_slot=placebo_slot,
        exemplars_per_tool=M,
    )


def _roster(draws=None, *, roster_role_override: str | None = None) -> dict[str, object]:
    draws = draws if draws is not None else _draws()
    receipt = proposer_roster_receipt(
        draws,
        carrier_lock_key=CARRIER,
        roster_id="SYNTH-EVO-PROPOSER-R1",
        media_facts={draw.anchor_sample_id: _media_facts(draw.anchor_sample_id) for draw in draws},
    )
    if roster_role_override is not None:
        receipt = dict(receipt)
        receipt["roster_role"] = roster_role_override
    return receipt


def _material(roster: Mapping[str, object] | None = None):
    return build_proposer_material(
        roster if roster is not None else _roster(),
        registry_rows=_registry_rows(),
        target_tools={TARGET_ID: TOOLS},
        incumbent_overrides={},
        exemplar_rows=_exemplar_rows(),
        carrier_lock_key=CARRIER,
    )


# ---------------------------------------------------------------------------
# rails.evolution: the draws and their receipt
# ---------------------------------------------------------------------------


def test_the_draw_is_a_seeded_ordered_sample_that_differs_per_slot() -> None:
    draws = {(d.target_id, d.k): d for d in _draws(placebo_slot=None)}
    first = draws[(TARGET_ID, 1)].exemplar_ids
    second = draws[(TARGET_ID, 2)].exemplar_ids
    assert len(first) == len(second) == M * len(TOOLS)
    # Same membership is allowed (a pool of exactly M cannot differ), but the
    # ORDER is what the seed fixes and what makes K non-decorative. With a
    # pool of four per tool the two slots differ in membership too.
    assert first != second
    # Deterministic: the same (round, target, k) redraws byte for byte.
    assert _draws(placebo_slot=None)[0].exemplar_ids == first


def test_a_placebo_draw_shows_no_exemplar_and_a_proposer_draw_must() -> None:
    placebo = [d for d in _draws() if d.family == "placebo"]
    assert placebo and all(draw.exemplar_ids == () for draw in placebo)
    with pytest.raises(EvolutionError, match="no exemplars"):
        ProposerDraw(
            round=1,
            target_id=TARGET_ID,
            family="proposer",
            k=1,
            exemplar_ids=(),
            anchor_sample_id="tier1_direct:000100",
        ).validate()
    with pytest.raises(EvolutionError, match="placebo draw carrying"):
        ProposerDraw(
            round=1,
            target_id=TARGET_ID,
            family="placebo",
            k=5,
            exemplar_ids=("tier1_direct:000100",),
            anchor_sample_id="tier1_direct:000100",
        ).validate()


def test_every_draw_claims_a_distinct_anchor() -> None:
    anchors = [draw.anchor_sample_id for draw in _draws()]
    assert len(set(anchors)) == len(anchors)


def test_the_roster_receipt_round_trips_and_refuses_a_tampered_one() -> None:
    draws = _draws()
    receipt = _roster(draws)
    assert receipt["roster_role"] == "construction"
    # The receipt's items are sample-id sorted (``core.roster``'s own
    # convention), so the read order is the receipt's rather than the
    # planner's; every draw survives the round trip unchanged.
    assert sorted(
        read_proposer_roster(receipt, carrier_lock_key=CARRIER),
        key=lambda draw: draw.draw_id,
    ) == sorted(draws, key=lambda draw: draw.draw_id)

    tampered = json.loads(json.dumps(receipt))
    tampered["items"][0]["sample_id"] = "tier1_direct:999999"
    with pytest.raises(EvolutionError, match="not verifiable"):
        read_proposer_roster(tampered)


def test_an_evaluation_role_roster_is_refused_for_this_arm() -> None:
    with pytest.raises(EvolutionError, match="roster_role"):
        read_proposer_roster(_roster(roster_role_override="evaluation"))


def test_another_carriers_roster_is_refused() -> None:
    with pytest.raises(EvolutionError, match="names carrier"):
        read_proposer_roster(_roster(), carrier_lock_key="some-other-carrier")


def test_the_material_renders_one_contact_per_draw_and_binds_their_union() -> None:
    material = _material()
    draws = _draws()
    assert len(material.contacts) == len(draws)
    by_sample = material.by_sample()
    for draw in draws:
        contact = by_sample[draw.anchor_sample_id]
        assert contact.construction_target_ids == (
            draw.exemplar_ids if draw.family == "proposer" else (draw.anchor_sample_id,)
        )
        assert contact.rendered_exemplar_ids == draw.exemplar_ids
        # The instruction is the ONLY place construction text is rendered.
        if draw.family == "proposer":
            assert "gold call:" in contact.instruction
        else:
            assert "gold call:" not in contact.instruction
            assert "placebo" in contact.instruction
    bound = {entry["sample_id"] for entry in material.bound_targets}
    assert bound == {
        sample_id
        for contact in material.contacts
        for sample_id in contact.construction_target_ids
    }
    # A receipt-safe view carries identity and counts, never the text.
    rendered = json.dumps(material.as_json())
    assert "synthetic spoken request" not in rendered


def test_the_material_refuses_a_gold_call_that_names_another_tool() -> None:
    rows = _exemplar_rows()
    # Pick a row a PROPOSER draw actually renders, not a placebo's anchor:
    # the refusal is about the exemplar block's grouping.
    victim = _draws()[0].exemplar_ids[0]
    rows[victim] = dict(rows[victim], gold_call="someOtherTool(deviceId='x')")
    with pytest.raises(EvolutionError, match="gold call opens with"):
        build_proposer_material(
            _roster(),
            registry_rows=_registry_rows(),
            target_tools={TARGET_ID: TOOLS},
            incumbent_overrides={},
            exemplar_rows=rows,
            carrier_lock_key=CARRIER,
        )


def test_the_material_accepts_a_namespaced_gold_call_whose_bare_name_agrees() -> None:
    """A released ``expected_tool_call`` is occasionally namespaced.

    1 of the 274 rows of ``A2T-EVO-EXEMPLARS-V2`` and 3 of fold A's 424 carry
    a head like ``smart_home.setApplianceMode`` while the row's own
    ``tool_name`` column is the bare ``setApplianceMode``. The manifest's
    ``tool_name`` is what the official scorer compares against, so the
    namespace is cosmetic; refusing it would block a whole round over a
    released-data quirk. The gold call is still rendered VERBATIM -- no gold
    is invented or rewritten.
    """

    rows = _exemplar_rows()
    victim = _draws()[0].exemplar_ids[0]
    tool = rows[victim]["tool_name"]
    rows[victim] = dict(
        rows[victim], gold_call=f"smart_home.{rows[victim]['gold_call']}"
    )
    material = build_proposer_material(
        _roster(),
        registry_rows=_registry_rows(),
        target_tools={TARGET_ID: TOOLS},
        incumbent_overrides={},
        exemplar_rows=rows,
        carrier_lock_key=CARRIER,
    )
    rendered = [
        contact.instruction
        for contact in material.contacts
        if victim in contact.rendered_exemplar_ids
    ]
    assert rendered
    assert all(f"smart_home.{tool}(" in text for text in rendered)


# ---------------------------------------------------------------------------
# The real FrozenCoreClient on this arm: narrowing, never widening
# ---------------------------------------------------------------------------


class _ArmAwareGate:
    def __init__(self) -> None:
        self.arms: list[str | None] = []

    def assert_model_touch_allowed(self, plan, *, full_hash=None, diagnostics=None, arm=None):
        self.arms.append(arm)
        return None


class _CapturingTransport:
    def __init__(self) -> None:
        self.payloads: list[dict] = []
        self.bodies: list[bytes] = []

    def __call__(self, request_bytes: bytes) -> bytes:
        self.bodies.append(request_bytes)
        self.payloads.append(json.loads(request_bytes.decode("utf-8")))
        return json.dumps(
            {"text": "ok", "usage": {"prompt_tokens": 3, "completion_tokens": 2}}
        ).encode("utf-8")


def _write_wav(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 16000)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _Sample:
    def __init__(self, sample_id: str, data_root: Path) -> None:
        self.sample_id = sample_id
        relpath = _relpath(sample_id)
        digest = _write_wav(data_root / relpath)
        self.audio_ref = AudioRef(path=relpath, sha256=digest).validate()
        self.audio_seconds = 1.0
        self.media_relpath = relpath


def _real_client(tmp_path: Path, material, *, plan_overrides=None):
    data_root = tmp_path / "data"
    samples = [_Sample(contact.sample_id, data_root) for contact in material.contacts]
    values = dict(
        run_id="SAEA-TEST-EVO-PROPOSER",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=CARRIER,
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-evo-proposer-0001",
    )
    values.update(dict(plan_overrides or {}))
    gate = _ArmAwareGate()
    transport = _CapturingTransport()
    client = FrozenCoreClient(
        plan=ExecutionPlan(**values),
        gate=gate,
        transport=transport,
        run_dir=tmp_path / "run",
        binding=build_payload_binding(
            carrier_lock_key=CARRIER,
            samples=samples,
            data_root=data_root,
            carrier_root=data_root / "datasets" / CARRIER,
        ),
        arm=PROPOSER_ARM,
        construction_targets=[dict(entry) for entry in material.bound_targets],
    )
    return client, gate, transport


def test_each_request_declares_exactly_its_own_draws_exemplars(tmp_path) -> None:
    material = _material()
    client, gate, transport = _real_client(tmp_path, material)
    for contact in material.contacts:
        client.complete(
            (
                {"role": "system", "content": contact.instruction},
                {"role": "user", "content": []},
            ),
            text_only_sample_id=contact.sample_id,
            construction_target_ids=contact.construction_target_ids,
        )
    client.close()

    assert len(transport.payloads) == len(material.contacts)
    assert gate.arms and set(gate.arms) == {PROPOSER_ARM}
    for contact, payload in zip(material.contacts, transport.payloads, strict=True):
        assert set(payload) == set(ARM_VISIBLE_FIELDS[PROPOSER_ARM])
        declared = [entry["sample_id"] for entry in payload["construction_targets"]]
        assert tuple(declared) == contact.construction_target_ids
        assert payload["sample_id"] == contact.sample_id
        assert payload["task_instruction"] == contact.instruction
    for body in transport.bodies:
        text = body.decode("utf-8")
        assert "input_audio" not in text
        assert "input_speech_features" not in text


def test_a_request_can_narrow_the_bound_targets_but_never_widen_them(tmp_path) -> None:
    material = _material()
    client, _gate, transport = _real_client(tmp_path, material)
    contact = material.contacts[0]
    with pytest.raises(Exception, match="not bound at construction"):
        client.complete(
            (
                {"role": "system", "content": contact.instruction},
                {"role": "user", "content": []},
            ),
            text_only_sample_id=contact.sample_id,
            construction_target_ids=("tier1_direct:999999",),
        )
    assert transport.payloads == []
    client.close()


# ---------------------------------------------------------------------------
# The E2.4 gate, on a real receipt tree
# ---------------------------------------------------------------------------


class _RosterProbe(_ExposureAndCarrierMixin):
    """The real gate mixin over a synthetic ``source_root`` -- the same
    ``docs/receipts/rosters`` scan a live flight's gate performs."""

    def __init__(self, source_root: Path) -> None:
        self.source_root = source_root


def _land_roster(root: Path, receipt: Mapping[str, object], name: str) -> str:
    path = root / "docs" / "receipts" / "rosters" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    return str(receipt["split_identity_hash"])


def _plan_for(identity_hash: str, *, split_role: str = "discovery") -> ExecutionPlan:
    return ExecutionPlan(
        run_id="SAEA-TEST-EVO-PROPOSER",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=CARRIER,
        split_role=split_role,
        split_identity_hash=identity_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-evo-proposer-0001",
    )


def test_the_gate_opens_on_the_proposer_rosters_own_identity(tmp_path) -> None:
    identity = _land_roster(tmp_path, _roster(), "synth-evo-proposer-r1")
    probe = _RosterProbe(tmp_path)
    probe._require_construction_role_for_visible_targets(_plan_for(identity), PROPOSER_ARM)


def test_the_gate_refuses_an_evaluation_identity_for_this_arm(tmp_path) -> None:
    identity = _land_roster(
        tmp_path, _roster(roster_role_override="evaluation"), "synth-evo-eval"
    )
    probe = _RosterProbe(tmp_path)
    with pytest.raises(GateClosed, match="roster_role='construction'"):
        probe._require_construction_role_for_visible_targets(_plan_for(identity), PROPOSER_ARM)


def test_the_gate_refuses_a_non_discovery_split_role_for_this_arm(tmp_path) -> None:
    identity = _land_roster(tmp_path, _roster(), "synth-evo-proposer-r1")
    probe = _RosterProbe(tmp_path)
    with pytest.raises(GateClosed, match="only on a discovery split"):
        probe._require_construction_role_for_visible_targets(
            _plan_for(identity, split_role="test"), PROPOSER_ARM
        )


# ---------------------------------------------------------------------------
# FlightRuntime: the dispatch, the gate forwarding and the wire check
# ---------------------------------------------------------------------------


class _ProposerAdapter(TaskAdapter):
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
        return "adapter instruction that a proposer flight must NOT send"

    def gold(self, sample):  # pragma: no cover -- a proposer row is never scored
        raise AssertionError("a proposer flight must never resolve gold through the adapter")

    def score_response(self, gold, response):  # pragma: no cover
        raise AssertionError("a proposer flight must never score a row")


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _repo(tmp_path: Path, run_id: str) -> Path:
    repo_root = tmp_path / "repo"
    for relpath, document in (
        (
            "configs/model/m.json",
            {
                "model_lock_key": "fake-lock",
                "transport": "fake",
                "decoding_params": {"id_slot": 0, "temperature": 0},
            },
        ),
        ("configs/dataset/d.json", {"carrier_lock_key": CARRIER, "split_id": "fake-split"}),
        (
            "configs/baseline/b.json",
            {"arm": PROPOSER_ARM, "policy": "fixed", "scorers": ["cost"]},
        ),
        (
            "configs/experiment/e.json",
            {
                "execution_plan": {
                    "execution_profile": "bounded-discovery-probe",
                    "split_role": "discovery",
                    "planned_model_calls": 10,
                    "planned_gpu_hours": 1.0,
                    # NOT zero, and this is a finding rather than a fixture choice:
                    # ``core.model.FrozenCoreAdapter`` charges the payload's
                    # ``audio_seconds`` against the plan even for a text-only
                    # request that sends no audio part, so a proposer run id
                    # registered at 0 speech seconds dies at its first contact.
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
        "| run/experiment id | consumed |\n| --- | --- |\n" f"| {run_id} | no |\n",
        encoding="utf-8",
    )
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "test snapshot")
    return repo_root


def _runtime(tmp_path: Path, *, gate=None, material=None, **overrides) -> FlightRuntime:
    run_id = "SAEA-TEST-EVO-PROPOSER"
    repo_root = _repo(tmp_path, run_id)
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    material = material if material is not None else _material()
    _ProposerAdapter.samples = tuple(
        _Sample(contact.sample_id, data_root) for contact in material.contacts
    )
    kwargs: dict[str, object] = {
        "client_factory": FrozenCoreClient,
        "carrier_root_resolver": lambda lock, key, root: Path(root) / "datasets" / key,
        "construction_material_resolver": lambda values, **_kw: material,
    }
    kwargs.update(overrides)
    return FlightRuntime(
        repo_root,
        data_root,
        model="m",
        dataset="d",
        baseline="b",
        experiment="e",
        run_id=run_id,
        attempt_id="attempt-001",
        runtime_root=tmp_path / "runtime",
        adapter_factory=lambda lock, root: _ProposerAdapter(lock, root),
        gate_factory=lambda *a, **kw: (gate if gate is not None else _ArmAwareGate()),
        lock={},
        **kwargs,
    )


def test_the_arm_is_recognised_off_the_d2_freeze() -> None:
    assert arm_shows_construction_targets(PROPOSER_ARM) is True
    assert arm_shows_construction_targets("bare-core") is False


def test_preflight_fires_the_e24_gate_with_the_arm(tmp_path) -> None:
    gate = _ArmAwareGate()
    runtime = _runtime(tmp_path, gate=gate)
    runtime.preflight()
    assert gate.arms == [PROPOSER_ARM]


def test_a_gate_that_cannot_receive_the_arm_refuses_the_flight(tmp_path) -> None:
    class _BlindGate:
        def assert_model_touch_allowed(self, plan, **_kwargs):
            return None

    runtime = _runtime(tmp_path, gate=_BlindGate())
    with pytest.raises(FlightRuntimeError, match="cannot receive the arm"):
        runtime.preflight()


def test_the_wire_check_proves_one_payload_per_draw_with_its_own_exemplars(
    tmp_path,
) -> None:
    material = _material()
    runtime = _runtime(tmp_path, material=material)
    receipt = runtime.wire_check(seal_and_score=False)

    assert receipt["model_contacts"] == 0
    assert receipt["arm"] == PROPOSER_ARM
    assert receipt["construction_proposer_arm"] is True
    assert receipt["policy_kind"] == "direct-construction-proposer"
    assert receipt["payload_keys"] == sorted(ARM_VISIBLE_FIELDS[PROPOSER_ARM])
    assert receipt["contact_count"] == len(material.contacts)
    assert len(receipt["request_body_sha256"]) == len(material.contacts)
    draws = {record["draw_id"]: record for record in receipt["construction_draws"]}
    assert len(draws) == len(material.contacts)
    # Identity and counts only: no construction text reaches the receipt.
    assert "synthetic spoken request" not in json.dumps(receipt)


def test_the_wire_check_refuses_a_request_that_declares_other_targets(tmp_path) -> None:
    material = _material()

    class _WidenedClient(FrozenCoreClient):
        def complete(self, messages, **kwargs):
            # Narrowing is legal; declaring the whole bound union on every
            # request is not what the draw showed, and the check must say so.
            kwargs.pop("construction_target_ids", None)
            return super().complete(messages, **kwargs)

    runtime = _runtime(tmp_path, material=material, client_factory=_WidenedClient)
    with pytest.raises(FlightRuntimeError, match="declares construction targets"):
        runtime.wire_check(seal_and_score=False)


def test_the_prompt_budget_fits_the_proposer_instruction_not_the_adapters(
    tmp_path,
) -> None:
    material = _material()
    seen: list[bytes] = []

    def _counter(payload: bytes) -> int:
        seen.append(payload)
        return 16

    runtime = _runtime(tmp_path, material=material, token_counter=_counter)
    receipt = runtime.preflight()
    assert receipt["prompt_budget"]
    joined = b"".join(seen).decode("utf-8")
    assert "adapter instruction that a proposer flight must NOT send" not in joined
    widest = max(material.contacts, key=lambda contact: len(contact.instruction))
    assert widest.instruction[:40] in joined
