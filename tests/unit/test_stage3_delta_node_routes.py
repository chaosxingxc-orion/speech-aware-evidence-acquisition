"""Stage-3 S3-4s (owner decision 106): the PER-NODE stage3-deltas routes.

Two shapes, one store:

* CANDIDATE-BOUND (Solver cap 8, Reviewer cap 4, Planner cap 4): the
  pre-S3-4s route plus a ``node_target`` filter, so each phase sees only the
  deltas addressed to its own node.
* UNCONDITIONAL (Perception cap 4): the FIRST phase, which produces the
  candidate list and therefore has nothing to bind against. The pre-S3-4s
  ``context_supply`` contract insisted on a LATER supplied phase; this is the
  honest first-phase branch, served through the router's own first-phase
  seed rather than through the per-advance dispatcher.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError,
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_stage3_delta_snapshot_v2,
)
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (
    DEFAULT_STAGE3_DELTA_NODE_CAPS,
    STAGE3_DELTA_CONTEXT_PROVIDER_ID,
    STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID,
    DeltaCandidate,
    Stage3DeltaSupplyError,
    node_target_of_task_target,
    select_stage3_delta_values,
    select_unconditional_stage3_delta_values,
)

from test_candidate_semantic_supply import _store

SHA_A = "a" * 64
SHA_B = "b" * 64
INVENTORY = ("alpha", "beta", "gamma", "delta")


# ---------------------------------------------------------------------------
# The pure selection functions
# ---------------------------------------------------------------------------


def _candidate(value_id, facets, prior, node):
    return DeltaCandidate(
        value_id=value_id,
        associated_facet_ids=tuple(facets),
        prior_score=prior,
        node_target=node,
    )


def test_node_target_of_task_target_reads_v2_and_ignores_v1() -> None:
    assert node_target_of_task_target("solver:slot-contract:alpha") == "solver"
    assert node_target_of_task_target("perception:perception-hint:beta") == "perception"
    # A v1 row names no node and must never be mis-routed into one.
    assert node_target_of_task_target("slot-contract:alpha") is None
    assert node_target_of_task_target(None) is None
    assert node_target_of_task_target("") is None


def test_node_filter_partitions_one_pool_into_disjoint_slices() -> None:
    pool = [
        _candidate("delta:1:aaaaaaaaaaaa", ("alpha",), 0.9, "solver"),
        _candidate("delta:1:bbbbbbbbbbbb", ("alpha",), 0.8, "reviewer"),
        _candidate("delta:1:cccccccccccc", ("alpha",), 0.7, "planner"),
        _candidate("delta:1:dddddddddddd", ("alpha",), 0.6, "perception"),
    ]
    assert select_stage3_delta_values(("alpha",), pool, cap=8, node_target="solver") == (
        "delta:1:aaaaaaaaaaaa",
    )
    assert select_stage3_delta_values(("alpha",), pool, cap=4, node_target="reviewer") == (
        "delta:1:bbbbbbbbbbbb",
    )
    # No filter: the pre-S3-4s behaviour, byte for byte.
    assert len(select_stage3_delta_values(("alpha",), pool, cap=8)) == 4


def test_the_unconditional_selection_has_no_row_dependent_term() -> None:
    pool = [
        _candidate("delta:1:aaaaaaaaaaaa", ("alpha",), 0.5, "perception"),
        _candidate("delta:1:bbbbbbbbbbbb", ("zeta",), 0.9, "perception"),
        _candidate("delta:1:cccccccccccc", ("alpha",), 0.99, "solver"),
    ]
    selected = select_unconditional_stage3_delta_values(pool, cap=4)
    # prior_score descending; the solver row is filtered out; the facets are
    # never consulted.
    assert selected == ("delta:1:bbbbbbbbbbbb", "delta:1:aaaaaaaaaaaa")


def test_the_unconditional_selection_caps_and_tie_breaks_deterministically() -> None:
    pool = [
        _candidate(f"delta:1:{chr(97 + i) * 12}", ("alpha",), 0.5, "perception")
        for i in range(6)
    ]
    selected = select_unconditional_stage3_delta_values(pool, cap=4)
    assert selected == tuple(f"delta:1:{chr(97 + i) * 12}" for i in range(4))


def test_the_registered_node_caps_are_the_spec_s_own() -> None:
    assert DEFAULT_STAGE3_DELTA_NODE_CAPS == {
        "perception": 4, "solver": 8, "reviewer": 4, "planner": 4,
    }


@pytest.mark.parametrize("bad", ["Solver", "review", "", "answering-node"])
def test_an_unknown_node_target_is_refused(bad) -> None:
    pool = [_candidate("delta:1:aaaaaaaaaaaa", ("alpha",), 0.5, "solver")]
    with pytest.raises(Stage3DeltaSupplyError):
        select_stage3_delta_values(("alpha",), pool, cap=4, node_target=bad)


# ---------------------------------------------------------------------------
# The router
# ---------------------------------------------------------------------------


def _program():
    """The locked plan's own phase order and knowledge classes."""

    return PhaseProgram(
        program_id="synthetic-four-node-v1",
        phases=(
            PhaseSpec("perception", "form-candidates", "supplied", None, False),
            PhaseSpec("reviewer", "review-evidence", "supplied", None, False),
            PhaseSpec("planner", "choose-next-action", "supplied", None, False),
            PhaseSpec("solver", "answer", "supplied", None, False),
        ),
        max_contacts=11,
        stop_rule="native-role-episode",
    ).validate()


def _delta_row(suffix, target, prior, node, kind="slot-contract"):
    return {
        "value_id": f"delta:1:{suffix}",
        "content": f"Synthetic delta statement {suffix}.",
        "associated_facet_ids": [target],
        "node_target": node,
        "source_sample_ids": ["train-1"],
        "provenance_refs": [f"advantage:SAEA-TEST-RUN:row-{suffix}:0:1:0"],
        "task_target": f"{node}:{kind}:{target}",
        "prior_score": prior,
    }


ROWS = (
    _delta_row("aaaaaaaaaaaa", "alpha", 0.90, "solver"),
    _delta_row("bbbbbbbbbbbb", "beta", 0.80, "solver"),
    _delta_row("cccccccccccc", "alpha", 0.70, "reviewer", kind="reviewer-criterion"),
    _delta_row("dddddddddddd", "alpha", 0.60, "planner", kind="planner-rule"),
    _delta_row("eeeeeeeeeeee", "gamma", 0.95, "perception", kind="perception-hint"),
    _delta_row("ffffffffffff", "delta", 0.55, "perception", kind="perception-hint"),
)


def _config(tmp_path, *, context_supply, rows=ROWS):
    snapshot = build_stage3_delta_snapshot_v2(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp",
            source_split_identity_hash=SHA_A,
            permitted_source_sample_ids=("train-1",),
        ),
        rows=rows,
    )
    source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": snapshot.builder_policy_id,
        "source_split_identity_hash": SHA_A,
        "rows": list(rows),
    }
    store = _store(tmp_path, "stage3-deltas", "stage3-deltas", snapshot, source)
    store["context_supply"] = context_supply
    return {"knowledge_stores": {"stage3-deltas": store}}


def _bound(tmp_path, context_supply, rows=ROWS):
    document = _config(tmp_path, context_supply=context_supply, rows=rows)
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    return binding, build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path,
        legal_candidate_ids=INVENTORY,
    )


def _candidate_spec(phase, cap):
    return {
        "provider": STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        "candidate_state_phase": "perception",
        "cap": cap,
        "rank_by": "prior_score",
        "node_target": phase,
    }


def _unconditional_spec(cap=4):
    return {
        "provider": STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID,
        "cap": cap,
        "rank_by": "prior_score",
        "node_target": "perception",
    }


ALL_ROUTES = {
    "perception": _unconditional_spec(),
    "reviewer": _candidate_spec("reviewer", 4),
    "planner": _candidate_spec("planner", 4),
    "solver": _candidate_spec("solver", 8),
}


def _perception_state(sample_id, intents):
    content = json.dumps(
        {
            "schema": "saea-slurp-intent-hypotheses-v1",
            "semantics": "ranked-mutually-exclusive-intent-alternatives",
            "sample_id": sample_id,
            "candidates": [
                {
                    "intent_id": intent,
                    "distinction": f"Evidence for {intent}.",
                    "evidence_refs": ["speech"],
                    "unresolved_fields": [],
                }
                for intent in intents
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return AgentStateArtifact(
        state_id=f"perception:{sample_id}",
        state_kind="phase:perception",
        content=content,
        source_query_state_sha256=SHA_B,
        source_response_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        producer_policy_id="synthetic-four-node-v1",
        cited_value_ids=(),
    ).validate()


def _context(binding, artifact, sample_id="s1"):
    query = QueryState(
        query_id=f"query:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id=f"packet:{sample_id}",
        speech_packet_sha256=SHA_B,
        use_split_identity_hash=SHA_A,
        query_source="speech_features",
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256=binding.binding_sha256,
        catalog_facet_ids=tuple(f.facet_id for f in binding.composite_snapshot.facets),
        catalog_value_ids=tuple(v.value_id for v in binding.composite_snapshot.values),
        query_state=query,
        task_contract="synthetic full legal label and type inventory",
        agent_states=(artifact,),
        prior_response_sha256s=(),
        contact_index=1,
    )


def _selected(supply):
    return tuple(supply.fusion_decision.selected_value_ids)


def test_each_candidate_bound_phase_sees_only_its_own_node_s_deltas(tmp_path):
    binding, router = _bound(tmp_path, ALL_ROUTES)
    context = _context(binding, _perception_state("s1", ("alpha", "beta")))
    solver = _selected(router.automatic_for_phase("solver", context))
    reviewer = _selected(router.automatic_for_phase("reviewer", context))
    planner = _selected(router.automatic_for_phase("planner", context))
    assert solver == (
        "stage3-deltas::delta:1:aaaaaaaaaaaa", "stage3-deltas::delta:1:bbbbbbbbbbbb",
    )
    assert reviewer == ("stage3-deltas::delta:1:cccccccccccc",)
    assert planner == ("stage3-deltas::delta:1:dddddddddddd",)
    assert not set(solver) & set(reviewer) & set(planner)


def test_a_candidate_bound_phase_still_binds_to_the_rows_own_candidates(tmp_path):
    binding, router = _bound(tmp_path, ALL_ROUTES)
    only_beta = _context(binding, _perception_state("s1", ("beta",)))
    assert _selected(router.automatic_for_phase("solver", only_beta)) == (
        "stage3-deltas::delta:1:bbbbbbbbbbbb",
    )
    # beta has no reviewer delta at all -> nothing supplied, no error.
    assert router.automatic_for_phase("reviewer", only_beta).fusion_decision.selected_value_ids == ()


def test_the_perception_route_is_served_by_the_first_phase_seed(tmp_path):
    binding, router = _bound(tmp_path, ALL_ROUTES)
    assert hasattr(router, "unconditional_first_phase")
    seeds = router.unconditional_first_phase(
        speech_packet_bindings={"s1": {}, "s2": {}}
    )
    assert set(seeds) == {"perception"}
    # Row-independent: every row of the split receives the same list, ranked
    # by prior_score, the solver/reviewer/planner rows filtered out.
    expected = (
        "stage3-deltas::delta:1:eeeeeeeeeeee",
        "stage3-deltas::delta:1:ffffffffffff",
    )
    assert seeds["perception"] == {"s1": expected, "s2": expected}
    # bootstrap_first_phase composes the same list itself.
    _facets, values = router.bootstrap_first_phase(
        speech_packet_bindings={"s1": {}, "s2": {}}, split_identity_hash=SHA_A,
    )
    assert values == {"s1": expected, "s2": expected}


def test_the_perception_route_is_receipted_with_its_selection(tmp_path):
    _binding, router = _bound(tmp_path, ALL_ROUTES)
    entry = router.receipt["stores"]["stage3-deltas"]
    assert entry["context_supply"] == ["perception", "planner", "reviewer", "solver"]
    unconditional = entry["unconditional_context_supply"]
    assert unconditional["phase"] == "perception"
    assert unconditional["node_target"] == "perception"
    assert unconditional["cap"] == 4
    assert unconditional["selected_value_ids"] == [
        "delta:1:eeeeeeeeeeee", "delta:1:ffffffffffff",
    ]


def test_a_store_with_only_the_unconditional_route_is_admitted(tmp_path):
    binding, router = _bound(tmp_path, {"perception": _unconditional_spec()})
    assert hasattr(router, "unconditional_first_phase")
    assert router.receipt["stores"]["stage3-deltas"]["context_supply"] == ["perception"]


@pytest.mark.parametrize(
    "spec",
    [
        # candidate_state_phase is refused: this route cannot honour a per-row
        # binding, so a spec asking for one is a configuration error.
        {**_unconditional_spec(), "candidate_state_phase": "perception"},
        {**_unconditional_spec(), "rank_by": "cosine"},
        {**_unconditional_spec(), "cap": 0},
        {**_unconditional_spec(), "node_target": "solver"},
        {k: v for k, v in _unconditional_spec().items() if k != "node_target"},
    ],
)
def test_the_unconditional_spec_is_validated_fail_closed(tmp_path, spec):
    with pytest.raises(KnowledgeStoreError):
        _bound(tmp_path, {"perception": spec})


def test_the_unconditional_provider_is_refused_on_a_later_phase(tmp_path):
    with pytest.raises(KnowledgeStoreError):
        _bound(tmp_path, {"solver": _unconditional_spec()})


def test_the_candidate_bound_provider_is_still_refused_on_the_first_phase(tmp_path):
    with pytest.raises(KnowledgeStoreError):
        _bound(tmp_path, {"perception": _candidate_spec("perception", 4)})


def test_a_pre_s3_4s_spec_without_node_target_still_validates_and_routes(tmp_path):
    """The pre-S3-4s shape is unchanged: no ``node_target``, no filter."""

    spec = {
        "provider": STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        "candidate_state_phase": "perception",
        "cap": 8,
        "rank_by": "prior_score",
    }
    binding, router = _bound(tmp_path, {"solver": spec})
    context = _context(binding, _perception_state("s1", ("alpha",)))
    assert _selected(router.automatic_for_phase("solver", context)) == (
        "stage3-deltas::delta:1:aaaaaaaaaaaa",
        "stage3-deltas::delta:1:cccccccccccc",
        "stage3-deltas::delta:1:dddddddddddd",
    )
    assert not hasattr(router, "unconditional_first_phase")
# ---------------------------------------------------------------------------
# Seeding the route EXACTLY ONCE (2026-09-23)
#
# The route reaches the first phase through two seeds, and cell CELL-1's
# generation smoke was refused before its first contact because both of them
# carried it: ``prepare_phase_supply`` derives the pinned artifact THROUGH
# ``FlightRuntime._phase_supply_seeds`` (item E16), which for a store-routed
# cell means through ``bootstrap_first_phase``, which composes the route
# itself -- and the dispatch merge then appended it a second time.
# ---------------------------------------------------------------------------


UNCONDITIONAL_IDS = (
    "stage3-deltas::delta:1:eeeeeeeeeeee",
    "stage3-deltas::delta:1:ffffffffffff",
)


def _seed_runtime(tmp_path, binding, router):
    """A ``FlightRuntime`` bound to the REAL router for the model-free
    first-phase seed path only: no client, no adapter, no attempt, no gate.
    """

    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )

    frozen = b"synthetic frozen preparation source"
    (tmp_path / "frozen-source.json").write_bytes(frozen)
    values = {
        # The locked plan's own policy: its phase order is _program()'s.
        "policy": "phase-native-candidates-review-revise-v1",
        "preparation_source_receipts": [
            {
                "root": "repository",
                "relpath": "frozen-source.json",
                "sha256": hashlib.sha256(frozen).hexdigest(),
            }
        ],
    }
    runtime = object.__new__(FlightRuntime)
    runtime._data_root = tmp_path
    runtime._repo_root = tmp_path
    runtime._composed = SimpleNamespace(values=values, config_hash="c" * 64)
    runtime._prepare = lambda: (values, "slurp", "TRAIN", SHA_B)
    spec = SimpleNamespace(
        as_json=lambda: {"phase": "perception"}, phase="perception"
    )
    phase_binding = {
        "knowledge_snapshot": binding.composite_snapshot,
        "speech_packet_bindings": {
            "s1": {"packet_id": "speech/s1", "sha256": SHA_A},
            "s2": {"packet_id": "speech/s2", "sha256": SHA_B},
        },
        "supply_specs": {"perception": spec},
        "supply_for_store": router,
    }
    runtime._phase_program_material = phase_binding
    runtime._default_phase_program_binding = lambda program, client: phase_binding
    return runtime, phase_binding, default_phase_program(values["policy"])


def test_the_route_is_seeded_once_from_scratch_and_once_from_a_prepared_artifact(
    tmp_path,
):
    from types import SimpleNamespace

    binding, router = _bound(tmp_path, ALL_ROUTES)
    runtime, phase_binding, program = _seed_runtime(tmp_path, binding, router)
    specs = phase_binding["supply_specs"]
    plan = SimpleNamespace(split_identity_hash=SHA_B)

    # (b) Computed from scratch: bootstrap_first_phase composes the route and
    # the merge adds nothing on top of it.
    live = runtime._phase_supply_seeds(program, phase_binding, specs, plan)
    assert live == (
        {},
        {"perception": {"s1": UNCONDITIONAL_IDS, "s2": UNCONDITIONAL_IDS}},
    )

    # (a) From the pinned artifact, which was produced by that same seed and
    # therefore ALREADY carries the route.
    artifact = runtime.prepare_phase_supply(tmp_path / "prepared-seed.json")
    published = json.loads(
        (tmp_path / "prepared-seed.json").read_text(encoding="utf-8")
    )
    assert published["output"]["values"]["perception"]["s1"] == list(
        UNCONDITIONAL_IDS
    )
    runtime._composed.values["prepared_phase_supply"] = {
        "relpath": "prepared-seed.json",
        "sha256": artifact["sha256"],
    }
    prepared = runtime._phase_supply_seeds(program, phase_binding, specs, plan)
    assert prepared == live
    for row in prepared[1]["perception"].values():
        assert [row.count(value_id) for value_id in UNCONDITIONAL_IDS] == [1, 1]


def _seam_binding(route, rows=("s1",)):
    from types import SimpleNamespace

    def seam(*, speech_packet_bindings, **_ignored):
        return {
            "perception": {
                sample_id: route for sample_id in sorted(speech_packet_bindings)
            }
        }

    return {
        "supply_for_store": SimpleNamespace(unconditional_first_phase=seam),
        "speech_packet_bindings": {sample_id: {} for sample_id in rows},
    }


def test_an_artifact_seed_already_carrying_the_route_keeps_every_id_once():
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        _merge_unconditional_first_phase,
    )

    route = ("store::d1", "store::d2")
    seeded = ("retrieval::v1", "retrieval::v2") + route
    facets, values = _merge_unconditional_first_phase(
        {"perception": {"s1": ("retrieval::f1",)}},
        {"perception": {"s1": seeded}},
        _seam_binding(route),
        "perception",
        seeded_from_artifact=True,
    )
    assert facets == {"perception": {"s1": ("retrieval::f1",)}}
    assert values == {"perception": {"s1": seeded}}


def test_an_artifact_seed_prepared_before_the_route_existed_still_gets_it():
    """The case the seam was written for: an artifact frozen over a store
    that did not yet declare an unconditional route."""

    from speech_aware_evidence_acquisition.core.flight.runtime import (
        _merge_unconditional_first_phase,
    )

    route = ("store::d1", "store::d2")
    _facets, values = _merge_unconditional_first_phase(
        {},
        {"perception": {"s1": ("retrieval::v1",)}},
        _seam_binding(route),
        "perception",
        seeded_from_artifact=True,
    )
    assert values == {"perception": {"s1": ("retrieval::v1",) + route}}


@pytest.mark.parametrize(
    "seeded",
    [
        # A partial overlap is not a composition of this route.
        ("retrieval::v1", "store::d1"),
        # The route's ids, but not as the tail this producer writes.
        ("store::d1", "store::d2", "retrieval::v1"),
    ],
)
def test_a_genuine_duplicate_still_refuses_an_artifact_seed(seeded):
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntimeError,
        _merge_unconditional_first_phase,
    )

    with pytest.raises(FlightRuntimeError, match="repeats a seeded value id"):
        _merge_unconditional_first_phase(
            {},
            {"perception": {"s1": seeded}},
            _seam_binding(("store::d1", "store::d2")),
            "perception",
            seeded_from_artifact=True,
        )


def test_a_seed_computed_from_scratch_keeps_the_strict_overlap_refusal():
    """Only an artifact seed may already carry the route. Every other seed
    keeps the pre-fix rule, under which any overlap at all refuses."""

    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntimeError,
        _merge_unconditional_first_phase,
    )

    route = ("store::d1", "store::d2")
    with pytest.raises(FlightRuntimeError, match="repeats a seeded value id"):
        _merge_unconditional_first_phase(
            {}, {"perception": {"s1": route}}, _seam_binding(route), "perception"
        )


def test_check_refuses_a_pinned_supply_that_cannot_compose(tmp_path):
    """``core.flight.cli check`` verified a pinned artifact's IDENTITY and
    never composed it, which is exactly the gap CELL-1's smoke fell through:
    the artifact was current, and the seed it produced was refused at
    dispatch. ``verify_prepared_artifacts`` now composes it too."""

    from speech_aware_evidence_acquisition.core.flight.cli import (
        prepared_artifact_blockers,
    )

    binding, router = _bound(tmp_path, ALL_ROUTES)
    runtime, _phase_binding, _program = _seed_runtime(tmp_path, binding, router)
    artifact = runtime.prepare_phase_supply(tmp_path / "prepared-seed.json")
    runtime._composed.values["prepared_phase_supply"] = {
        "relpath": "prepared-seed.json",
        "sha256": artifact["sha256"],
    }
    (report,) = runtime.verify_prepared_artifacts()
    assert (report["key"], report["identity_ok"], report["seed_ok"]) == (
        "prepared_phase_supply", True, True,
    )
    assert prepared_artifact_blockers(
        {"prepared_artifacts_ok": True, "prepared_artifacts": [report]}
    ) == []

    # A route overlapping the seeded values without being their tail is a
    # genuine duplicate. The artifact's identity still holds, so only the
    # composition can catch it -- and it must, before an attempt is opened.
    runtime._prepared_artifact_reports = None
    router.unconditional_first_phase = lambda *, speech_packet_bindings, **_k: {
        "perception": {
            sample_id: (UNCONDITIONAL_IDS[0],)
            for sample_id in sorted(speech_packet_bindings)
        }
    }
    (broken,) = runtime.verify_prepared_artifacts()
    assert broken["identity_ok"] is True
    assert broken["seed_ok"] is False
    assert "repeats a seeded value id" in broken["reason"]
    assert prepared_artifact_blockers(
        {"prepared_artifacts_ok": False, "prepared_artifacts": [broken]}
    ) == [
        "prepared artifact does not compose into a first-phase seed: "
        f"prepared_phase_supply ({broken['relpath']}): {broken['reason']}"
    ]
