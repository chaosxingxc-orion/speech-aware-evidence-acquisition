"""E6: the two shipped phase-supply cells --- KU-S1
(``configs/baseline/slurp-phase-blend-cl-v1.json``, a supplied SECOND phase
on the acquire path) and the KU-A1 shape sketch
(``configs/baseline/a2t-phase-dense-hint-v1.json``, a supplied FIRST phase on
the pre-flight seeded path).

Zero model, GPU, network and embedding contacts. The one end-to-end run
drives the REAL ``rails.runner.run_speech_native_agent_loop`` through
``rails.phase_runner.run_continuous_program`` against a recording fake
client, so the acquire transitions actually pass
``assert_knowledge_use_binding`` and ``assert_agent_step_binding`` rather
than being asserted about a mock.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_runner as pr
from speech_aware_evidence_acquisition.rails import phase_supply as ps
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.obs import ObsPacket
from speech_aware_evidence_acquisition.rails.runner import (
    _protected_knowledge_material,
)
from speech_aware_evidence_acquisition.rails.task_adapter import AudioRef, TaskAdapter

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINES = _REPO_ROOT / "configs" / "baseline"
_PROBES = _REPO_ROOT / "configs" / "probes"
_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_PLACEHOLDER = "f" * 64

_SLURP_FRAGMENT = json.loads(
    (_BASELINES / "slurp-phase-blend-cl-v1.json").read_text(encoding="utf-8")
)
_A2T_FRAGMENT = json.loads(
    (_BASELINES / "a2t-phase-dense-hint-v1.json").read_text(encoding="utf-8")
)


# ---------------------------------------------------------------------------
# KU-S1: the shipped fragment
# ---------------------------------------------------------------------------


def test_ku_s1_fragment_declares_the_lock_knobs_on_the_supplied_evidence_phase():
    program = rc.default_phase_program(_SLURP_FRAGMENT["policy"])
    assert program.program_id == "phase-direct-evidence-alpha-blend-v1"
    specs = ps.load_phase_supply_specs(_SLURP_FRAGMENT, program)
    assert set(specs) == {"evidence"}
    spec = specs["evidence"]
    assert spec.provider == "kb-facet-v1"
    assert spec.rank_policy == "saea-rank-wcos-prior-agree-v1"
    assert spec.fuse_policy == "saea-fuse-supplyfilter-v1"
    assert (spec.k, spec.tau, spec.alpha) == (5, 0.65, 0.45)
    assert spec.rank_weights == {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2}
    assert spec.fuse_coverage == {"m": 5, "c": 2, "top_l": 3}
    # The supplied phase is the SECOND one: it rides the acquire transition
    # of the first phase's advance, not a pre-flight seed.
    assert program.phase_names() == ("direct", "evidence")
    assert program.phase("evidence").knowledge == "supplied"


def test_ku_s1_fragment_appends_nothing_per_sample_to_either_control_turn():
    """This is why the cell can bind the FULL snapshot where KU-S1c could
    not: the only text the containment rule reads is two static directives."""

    material = _SLURP_FRAGMENT["phase_material"]
    assert material["direct"]["predecessor_binding"] == "none"
    assert material["evidence"]["predecessor_binding"] == "none"


def test_ku_s1_vector_pins_are_placeholders_that_will_refuse(tmp_path):
    """The fragment ships un-flyable on purpose: both sealed-vector files
    have to be produced under their own tool-contact ledger row first."""

    source = _SLURP_FRAGMENT["phase_supply"]["evidence"]["query_source"]
    assert source["sha256"] == _PLACEHOLDER
    path = tmp_path / "query-vectors.jsonl"
    path.write_text('{"id": "s1", "vectors": {"content": [1.0]}}\n', encoding="utf-8")
    with pytest.raises(ps.PhaseSupplyError, match="hashes to"):
        ps.load_sealed_vectors(
            path, expected_sha256=_PLACEHOLDER, dimensions=("content",)
        )


def _snapshot_path() -> Path | None:
    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_root:
        return None
    path = Path(data_root) / _SLURP_FRAGMENT["knowledge_snapshot_relpath"]
    return path if path.is_file() else None


def _synthetic_full_snapshot() -> KnowledgeSnapshot:
    """A stand-in carrying the exact strings the KU-S1 verdict measured as
    colliding under ``slurp-kb-size-full`` (section 6.2: calendar 57,
    shopping 7, politics 4, change song 2, next episode 2, to do list 2,
    clothing 1, donald trump 1, jane doe 1, new york time 1)."""

    colliding = (
        "calendar",
        "shopping",
        "politics",
        "change song",
        "next episode",
        "to do list",
        "clothing",
        "donald trump",
        "jane doe",
        "new york time",
    )
    return KnowledgeSnapshot(
        snapshot_id="synthetic-size-full-collisions-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:t1",),
        builder_policy_id="test-builder-v1",
        facets=tuple(
            KeyFacet(
                facet_id=f"facet:content:{index}",
                dimension="content",
                representation_kind="text",
                representation=text,
                source_sample_ids=("train:t1",),
            )
            for index, text in enumerate(colliding)
        ),
        values=(
            ValueBundle(
                value_id="value:t1",
                content="a long enough evidence payload for t1",
                associated_facet_ids=("facet:content:0",),
                source_sample_ids=("train:t1",),
                provenance_refs=("train:t1",),
                task_target="calendar/set",
            ),
        ),
    ).validate()


def test_ku_s1_control_turns_pass_containment_against_the_full_snapshot():
    """The measurement the KU-S1 refusal turned on, re-run on this cell's own
    bytes. Uses the REAL snapshot when SPEECHRL_DATA_DIR has it; otherwise a
    synthetic snapshot carrying the verdict's own colliding strings."""

    path = _snapshot_path()
    if path is not None:
        snapshot = KnowledgeSnapshot.from_frozen_json(
            json.loads(path.read_text(encoding="utf-8"))
        )
        measured = snapshot.content_hash()
        assert measured == _SLURP_FRAGMENT["knowledge_snapshot_sha256"]
        assert len(snapshot.values) == 11514
    else:
        snapshot = _synthetic_full_snapshot()
    protected = _protected_knowledge_material(snapshot)
    assert protected
    for phase, entry in _SLURP_FRAGMENT["phase_material"].items():
        relpath = entry["instruction_template"]
        assert relpath.startswith("probes/")
        text = (_PROBES / relpath.split("/", 1)[1]).read_text(encoding="utf-8")
        lowered = text.casefold()
        hits = [material for material in protected if material in lowered]
        assert hits == [], f"phase {phase} control turn collides: {hits[:5]}"


def test_ku_s1_control_turn_bytes_are_pinned_by_the_probe_manifest():
    manifest = json.loads((_PROBES / "manifest.json").read_text(encoding="utf-8"))
    probe = manifest["probes"]["SLURP-CONSUMPTION-KU-S1"]
    templates = probe["arms"]["direct_evidence"]
    assert templates == ["slurp_phase_direct.txt", "slurp_phase_evidence.txt"]
    for name in templates:
        digest = hashlib.sha256((_PROBES / name).read_bytes()).hexdigest()
        assert manifest["templates"][name]["sha256"] == digest


# ---------------------------------------------------------------------------
# KU-S1: a fake two-phase run through the real agent loop
# ---------------------------------------------------------------------------


def _cell_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="ku-s1-cell-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:u1", "train:u2"),
        builder_policy_id="test-builder-v1",
        facets=(
            KeyFacet("facet:content:u1", "content", "text", "red apple", ("train:u1",)),
            KeyFacet("facet:content:u2", "content", "text", "green leaf", ("train:u2",)),
            KeyFacet("facet:label:red", "label", "text", "red", ("train:u1",)),
            KeyFacet("facet:label:green", "label", "text", "green", ("train:u2",)),
        ),
        values=(
            ValueBundle(
                value_id="value:u1",
                content="a long enough evidence payload for u1",
                associated_facet_ids=("facet:content:u1", "facet:label:red"),
                source_sample_ids=("train:u1",),
                # SLURP-shaped intent identity ("scenario_action"): the
                # registered default normalizer joins the response's own
                # parsed fields that way, so the alpha head can only match a
                # task_target of this shape.
                provenance_refs=("train:u1",),
                task_target="red_query",
                prior_score=0.7,
            ),
            ValueBundle(
                value_id="value:u2",
                content="a long enough evidence payload for u2",
                associated_facet_ids=("facet:content:u2", "facet:label:green"),
                source_sample_ids=("train:u2",),
                provenance_refs=("train:u2",),
                task_target="green_query",
                prior_score=0.3,
            ),
        ),
    ).validate()


@dataclass(frozen=True)
class _Sample:
    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


@dataclass
class _Adapter(TaskAdapter):
    samples: tuple[_Sample, ...]
    events: list[str] = field(default_factory=list)

    SERVING_SLOTS = 1
    SERVING_SLOT_TOKENS = 4096
    SERVING_MAX_TOKENS = 64

    def load_split(self, split_id):
        return self.samples if split_id == "all" else ()

    def build_task_contract(self, sample, obs: ObsPacket) -> str:
        return "answer the spoken command"

    def assemble_prompt(self, sample, supply):
        return (
            {"role": "system", "content": "fake closed-list system message"},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "media_relpath": sample.audio_ref.path}
                ],
            },
        )

    def score(self, sample, response):
        return {"response_length": len(response)}


class _RecordingClient:
    def __init__(self):
        self.calls: list[dict] = []

    def complete(self, messages, **options):
        self.calls.append({"messages": tuple(messages), "options": dict(options)})
        return json.dumps({"scenario": "red", "action": "query"})


def _write_vectors(path: Path, rows) -> str:
    text = "".join(
        json.dumps({"id": entry_id, "vectors": vectors}, sort_keys=True) + "\n"
        for entry_id, vectors in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cell_values(tmp_path: Path, sample_ids) -> dict:
    query_digest = _write_vectors(
        tmp_path / "v" / "q.jsonl",
        [(sample_id, {"content": [1.0, 0.0]}) for sample_id in sample_ids],
    )
    facet_digest = _write_vectors(
        tmp_path / "v" / "f.jsonl",
        [
            ("facet:content:u1", {"content": [1.0, 0.0]}),
            ("facet:content:u2", {"content": [0.0, 1.0]}),
        ],
    )

    def source(relpath, digest, signal):
        return {
            "kind": ps.SEALED_VECTORS_KIND,
            "relpath": relpath,
            "sha256": digest,
            "tool_contact_ledger_row": "TEST-EMB-0001",
            "embedded_signal": signal,
        }

    declared = json.loads(json.dumps(_SLURP_FRAGMENT["phase_supply"]))
    # The QUERY side must declare a speech-carrying modality (owner rule
    # 2026-09-06); the KEY side is unconstrained knowledge text.
    declared["evidence"]["query_source"] = source(
        "v/q.jsonl", query_digest, "speech+state: the test's own synthetic vectors"
    )
    declared["evidence"]["facet_source"] = source(
        "v/f.jsonl", facet_digest, "the test's own synthetic facet vectors"
    )
    # The alpha head is exercised by its own test below; this run proves the
    # acquire path, so it must not retain the direct answer.
    declared["evidence"].pop("alpha")
    return {"phase_supply": declared}


def test_ku_s1_shaped_two_phase_run_seals_one_row_per_sample_with_acquire(tmp_path):
    sample_ids = ("dev:s1", "dev:s2")
    snapshot = _cell_snapshot()
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    supply_for_phase = ps.build_supply_for_phase(
        ps.load_phase_supply_specs(_cell_values(tmp_path, sample_ids), program),
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
    )
    adapter = _Adapter(
        samples=tuple(
            _Sample(
                sample_id=sample_id,
                audio_ref=AudioRef(path=f"{sample_id}.wav", sha256=_SHA_A),
                audio_seconds=2.0,
            )
            for sample_id in sample_ids
        )
    )
    client = _RecordingClient()
    plan = ExecutionPlan(
        run_id="SAEA-E-TEST-ku-s1-shape",
        execution_profile="model-free-check",
        carrier_lock_key="rails-fake",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash(_PLACEHOLDER, "bare-core", _SHA_A),
        attempt_id="attempt-ku-s1-shape-0001",
    )

    def material_for_phase(name, context, sealed_states):
        return PhaseMaterial(
            instruction=f"static directive for {name}",
            response_format=None,
            contact_id=f"{program.program_id}:{name}:{context.sample_id}",
            purpose=program.phase(name).purpose,
        ).validate()

    summary = pr.run_continuous_program(
        program=program,
        adapter=adapter,
        plan=plan,
        data_root=tmp_path,
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings={
            sample_id: {"packet_id": f"speech/{sample_id}", "sha256": _SHA_C}
            for sample_id in sample_ids
        },
        trace_sink=TraceBuffer(plan.run_id),
        decoding_params={},
        material_for_phase=material_for_phase,
        supply_for_phase=supply_for_phase,
        agent_executor_id="reference-trajectory-v1",
        slot_count=1,
        queue_depth=1,
    )

    # ONE sealed row per sample, carrying the evidence phase's response.
    assert len(summary.results) == len(sample_ids)
    assert {result.sample_id for result in summary.results} == set(sample_ids)
    for result in summary.results:
        assert len(result.contacts) == 2
        kinds = [transition.action_kind for transition in result.transitions]
        assert kinds == ["acquire", "stop"]
        acquire = result.transitions[0]
        assert acquire.new_value_ids == ("value:u1",)
        assert acquire.new_agent_state_ids == (f"direct:{result.sample_id}",)
        assert result.final_query_state.retrieved_value_ids == ("value:u1",)
        wave = result.waves[0]
        assert wave.rank_result is not None
        assert wave.fusion_decision is not None

    # The supply reached the model as a TYPED content block, and the control
    # turns are byte-identical between the unsupplied and supplied phases.
    supplied = [
        part
        for call in client.calls
        for part in call["messages"][1]["content"]
        if part.get("knowledge_role") is not None
    ]
    assert len(supplied) == len(sample_ids)
    for part in supplied:
        assert part["knowledge_role"] == "value"
        assert part["evidence_id"] == "value:u1"
        assert part["source_uri"].startswith("knowledge-snapshot://")
        assert part["text"] == "a long enough evidence payload for u1"
    instructions = {call["options"]["contact_instruction"] for call in client.calls}
    assert instructions == {"static directive for direct", "static directive for evidence"}
    for call in client.calls:
        assert "evidence payload" not in call["options"]["contact_instruction"]


def test_ku_s1_alpha_head_retains_the_direct_answer_when_it_uniquely_wins(tmp_path):
    """``alpha`` is live: the fragment's 0.45 reproduces
    ``KbAlphaBlendController``'s retain-primary shortcut on the base."""

    snapshot = _cell_snapshot()
    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    values = _cell_values(tmp_path, ("dev:s1",))
    values["phase_supply"]["evidence"]["alpha"] = 0.45
    supply_for_phase = ps.build_supply_for_phase(
        ps.load_phase_supply_specs(values, program),
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
    )
    adapter = _Adapter(
        samples=(
            _Sample(
                sample_id="dev:s1",
                audio_ref=AudioRef(path="dev-s1.wav", sha256=_SHA_A),
                audio_seconds=2.0,
            ),
        )
    )
    client = _RecordingClient()
    plan = ExecutionPlan(
        run_id="SAEA-E-TEST-ku-s1-alpha",
        execution_profile="model-free-check",
        carrier_lock_key="rails-fake",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash(_PLACEHOLDER, "bare-core", _SHA_A),
        attempt_id="attempt-ku-s1-alpha-0001",
    )

    def material_for_phase(name, context, sealed_states):
        return PhaseMaterial(
            instruction=f"static directive for {name}",
            response_format=None,
            contact_id=f"{program.program_id}:{name}:{context.sample_id}",
            purpose=program.phase(name).purpose,
        ).validate()

    summary = pr.run_continuous_program(
        program=program,
        adapter=adapter,
        plan=plan,
        data_root=tmp_path,
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings={
            "dev:s1": {"packet_id": "speech/dev:s1", "sha256": _SHA_C}
        },
        trace_sink=TraceBuffer(plan.run_id),
        decoding_params={},
        material_for_phase=material_for_phase,
        supply_for_phase=supply_for_phase,
        agent_executor_id="reference-trajectory-v1",
        slot_count=1,
        queue_depth=1,
    )
    (result,) = summary.results
    # The direct answer's label ("red") is the unique blend winner, so the
    # evidence contact is never spent: ONE contact, one stop, no acquire.
    assert len(result.contacts) == 1
    assert [t.action_kind for t in result.transitions] == ["stop"]
    assert len(client.calls) == 1


def test_run_continuous_program_refuses_a_barrier_program():
    program = rc.default_phase_program("phase-select-then-fill-v1")
    assert any(phase.barrier for phase in program.phases)
    with pytest.raises(pr.PhaseRunnerError, match="barrier"):
        pr.run_continuous_program(
            program=program,
            adapter=_Adapter(samples=()),
            plan=None,
            data_root=Path("."),
            core_client=None,
            split_id="all",
            knowledge_snapshot=None,
            speech_packet_bindings={"s1": {"packet_id": "p", "sha256": _SHA_A}},
            trace_sink=None,
            decoding_params={},
            material_for_phase=lambda *args: None,
        )


# ---------------------------------------------------------------------------
# KU-A1: the shape sketch
# ---------------------------------------------------------------------------


def test_ku_a1_fragment_supplies_the_first_phase_of_a_one_phase_program():
    program = rc.default_phase_program(_A2T_FRAGMENT["policy"])
    assert program.phase_names() == ("direct",)
    declared = _A2T_FRAGMENT["phase_supply"]
    assert set(declared) == {"direct"}
    assert declared["direct"]["provider"] == "dense-centroid-v1"
    assert declared["direct"]["k"] == 8
    # The one-phase program's own phase declares knowledge "none", which is
    # exactly the refusal a supplied phase has to clear -- the sketch is
    # therefore honest about being un-flyable until that program declares a
    # supplied phase.
    with pytest.raises(ps.PhaseSupplyError, match="knowledge='none'"):
        ps.load_phase_supply_specs(_A2T_FRAGMENT, program)


def test_ku_a1_shape_passes_preflight_on_a_supplied_one_phase_program(tmp_path):
    """The same preflight, with a fake provider and no embeddings: a
    one-phase program whose single phase declares ``knowledge: "supplied"``
    resolves the fragment's spec, and the selection is decided BEFORE the
    flight rather than by an acquire transition."""

    program = rc.PhaseProgram(
        program_id="a2t-phase-dense-hint-shape-v1",
        phases=(
            rc.PhaseSpec(
                name="direct",
                purpose="direct-decode",
                knowledge="supplied",
                response_format_id=None,
                barrier=False,
            ),
        ),
        max_contacts=1,
        stop_rule="always-run-full-program",
    ).validate()
    snapshot = _cell_snapshot()
    digest = _write_vectors(
        tmp_path / "v" / "q.jsonl", [("dev:s1", {"content": [1.0, 0.0]})]
    )
    declared = json.loads(json.dumps(_A2T_FRAGMENT["phase_supply"]))
    declared["direct"]["query_source"] = {
        "kind": ps.SEALED_VECTORS_KIND,
        "relpath": "v/q.jsonl",
        "sha256": digest,
        "tool_contact_ledger_row": "TEST-EMB-0002",
        "embedded_signal": "speech: the test's own synthetic audio-keyed vectors",
    }
    specs = ps.load_phase_supply_specs({"phase_supply": declared}, program)
    assert specs["direct"].k == 8

    from speech_aware_evidence_acquisition.rails.knowledge import (
        FusionDecision,
        RankedFacet,
        RankResult,
    )

    class _FakeDenseProvider:
        """Stands in for a built ``DenseCentroidProvider``: KU-A1's real one
        needs a ``ToolTierSemanticIndex`` this seam cannot derive from a
        ``KnowledgeSnapshot``, which is why
        ``bind_phase_supply_providers`` exists."""

        def __init__(self):
            self.seen: list[str] = []

        def candidates(self, query, *, k):
            self.state = query["query_state"]
            self.seen.append(self.state.query_id)
            self.rank_result = RankResult(
                snapshot_sha256=snapshot.content_hash(),
                query_state_sha256=self.state.content_hash(),
                ranking_policy_id="fake-dense-rank-v1",
                candidates=(RankedFacet(facet_id="facet:content:u1", score=1.0),),
            ).validate()
            return "ranking"

        def fuse(self, rankings, *, k, policy_id):
            return FusionDecision(
                snapshot_sha256=snapshot.content_hash(),
                query_state_sha256=self.state.content_hash(),
                rank_result_sha256=self.rank_result.content_hash(),
                fusion_policy_id=policy_id,
                supporting_facet_ids=("facet:content:u1",),
                selected_value_ids=("value:u1",),
            ).validate()

        def last_rank_result(self):
            return self.rank_result

    provider = _FakeDenseProvider()
    supply_for_phase = ps.build_supply_for_phase(
        specs,
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        data_root=tmp_path,
        provider_for_phase=lambda phase: provider,
        seed_phases=("direct",),
    )
    facets, values = ps.build_bootstrap_selection(
        specs["direct"],
        provider=provider,
        query_vectors_by_sample=supply_for_phase.query_tables["direct"],
        speech_packet_bindings={
            "dev:s1": {"packet_id": "speech/dev:s1", "sha256": _SHA_C}
        },
        split_identity_hash=_SHA_A,
    )
    assert values == {"dev:s1": ("value:u1",)}
    assert facets == {}
    assert provider.seen == [f"{ps.SEED_QUERY_ID_PREFIX}:direct:dev:s1"]
    # A seeded phase never answers the runtime callable: its values already
    # rode the initial QueryState.
    assert supply_for_phase("direct", None) is None


def test_ku_a1_sketch_records_that_mf_6_gates_it():
    assert "MF-6" in _A2T_FRAGMENT["gated_by_mf_6"]
    assert "0.85" in _A2T_FRAGMENT["gated_by_mf_6"]


# ---------------------------------------------------------------------------
# Owner rule, 2026-09-06, at the FlightRuntime preflight
# ---------------------------------------------------------------------------


def _legality_stub(values):
    """``FlightRuntime._assert_phase_supply_is_legal_for`` called unbound on
    a stub carrying only the composed baseline values it reads -- no repo, no
    data root, no snapshot, no contact."""

    return SimpleNamespace(_composed=SimpleNamespace(values=values))


def _query_source(signal):
    return {
        "kind": ps.SEALED_VECTORS_KIND,
        "relpath": "v/q.jsonl",
        "sha256": _SHA_A,
        "tool_contact_ledger_row": "TEST-EMB-0003",
        "embedded_signal": signal,
    }


@pytest.mark.parametrize(
    "signal",
    [
        "speech: the row's own 90 s speech packet, embedded by the pinned tool "
        "embedder before takeoff",
        "speech+state: that packet fused with the row's own phase-1 draft answer",
    ],
)
def test_flight_preflight_accepts_a_speech_carrying_query_source(signal):
    values = {"phase_supply": {"evidence": {"query_source": _query_source(signal)}}}
    FlightRuntime._assert_phase_supply_is_legal_for(
        _legality_stub(values), "phase-direct-evidence-alpha-blend-v1"
    )


def test_flight_preflight_refuses_a_text_only_query_source():
    """Owner rule 2026-09-06. The refusal fires on the RAW fragment, before
    the phase program is resolved and before any vector file is opened."""

    values = {
        "phase_supply": {
            "evidence": {
                "query_source": _query_source(
                    "the sealed closed-list response text of each row"
                )
            }
        }
    }
    with pytest.raises(FlightRuntimeError, match="must DECLARE the query signal"):
        FlightRuntime._assert_phase_supply_is_legal_for(
            _legality_stub(values), "phase-direct-evidence-alpha-blend-v1"
        )


def test_flight_preflight_still_refuses_phase_supply_on_a_fixed_policy():
    """The pre-existing E6 refusal is unchanged by the new rule."""

    values = {
        "phase_supply": {
            "evidence": {"query_source": _query_source("speech: anything")}
        }
    }
    with pytest.raises(FlightRuntimeError, match="policy is 'fixed'"):
        FlightRuntime._assert_phase_supply_is_legal_for(_legality_stub(values), "fixed")


def test_shipped_query_sources_declare_a_speech_modality():
    """Both shipped fragments' QUERY sources declare a modality in the fixed
    vocabulary; neither KEY source is required to."""

    for fragment, phase in ((_SLURP_FRAGMENT, "evidence"), (_A2T_FRAGMENT, "direct")):
        source = fragment["phase_supply"][phase]["query_source"]
        modality = ps.query_signal_modality(source, field="query_source")
        assert modality in ps.QUERY_SIGNAL_MODALITIES
    facet = _SLURP_FRAGMENT["phase_supply"]["evidence"]["facet_source"]
    assert not facet["embedded_signal"].startswith(tuple(ps.QUERY_SIGNAL_MODALITIES))
