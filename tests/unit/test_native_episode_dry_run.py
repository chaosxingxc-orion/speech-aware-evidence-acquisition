"""The offline dry run of a plan-based native role episode.

Cell CELL-1's generation smoke made four charged Perception contacts on
2026-09-23 and then died at the openJiuwen vertex ``solver_0_input``::

    NativeEpisodeError: native episode node failed: [100054] component
    'solver_0_input' execute 'invoke' error, reason='hypothesis state must
    contain exactly ['candidates', 'sample_id', 'schema', 'semantics']'

Nothing in the ladder could have caught it: ``core.flight.cli check`` never
walks the episode, and every unit test of the stage3-deltas route fed it a
CANONICAL four-key Perception document while a native episode seals the
model's own COMPACT structured-output bytes. This module is the durable
proof that the walk now happens offline, before a flight is queued.

The v2 smoke then spent 12 contacts and died at ``reviewer_0_input`` with
"acquire must introduce at least one new value or facet" -- a defect this
module's first version walked straight past, because it asked only about the
roster's FIRST row, with candidates read off the store's own union of
addressed facets, on the ACCEPT path. All three are now variables, not
assumptions.

Three layers:

* the always-on part -- the helper's own contracts (the graph order it
  derives, the refusals it makes), which need no data root;
* ``test_the_cell_1_smoke_composition_walks_its_whole_episode``, which walks
  the REAL registered smoke cell on the REAL released stores for ONE row with
  canned, schema-valid role answers. It SKIPS where the data root, the
  released stores or the promoted packets are absent, and asserts where they
  are present: the whole graph completes, every node is supplied its own
  stage3-deltas slice, and the delivery is the Solver's sealed draft; and
* the two regressions below it: EVERY row of the smoke roster, answered with
  the Perception candidate ids the retired v2 attempt's own trace recorded,
  and a REVISE verdict that revisits the Solver, the Reviewer and the Planner.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
    DRY_RUN_SCHEMA,
    NATIVE_ROLE_GRAPH_ORDER,
    NativeEpisodeDryRunError,
    compose_dry_run,
    dry_run_native_episode,
    episode_node_order,
    legal_intent_ids,
    store_facet_ids,
)
from speech_aware_evidence_acquisition.rails import AudioRef
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    KNOWLEDGE_VALUE_RENDERING_SCHEMA,
    NativeEpisodeConfig,
    NativeEpisodeRole,
)

from test_phase_supply_repeat_visit import (
    EXEMPLAR_FACET_IDS,
    EXEMPLAR_VALUE_IDS,
    _exemplar_snapshot,
    _prepared_supply,
    _supplied_program,
)
from test_rails_runner import _FakeAdapter, _FakeSample

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_EXPERIMENT = "slurp-native-stage3-delta-cell-smoke-4-v3"
SMOKE_CELL = "slurp-native-stage3-delta-cell-smoke-4-v3"
DELTA_STORE = "stage3-deltas"


# ---------------------------------------------------------------------------
# Contracts that need no data root
# ---------------------------------------------------------------------------


def _episode(*, roles=NATIVE_ROLE_GRAPH_ORDER):
    return NativeEpisodeConfig(
        episode_id="dry-run-order-proof-v1",
        max_revisions=1,
        actions=("ACCEPT", "REVISE", "ACQUIRE"),
        roles=tuple(
            NativeEpisodeRole(
                phase_id=kind, role_kind=kind, max_iterations=1, tool_names=()
            )
            for kind in roles
        ),
        max_contacts=11,
    )


def test_the_walked_order_is_the_graphs_not_the_fragments():
    """The program fragment lists perception, reviewer, planner, solver; the
    GRAPH drafts before it reviews. Walking the fragment's order would put the
    Reviewer in front of the draft it reviews."""

    assert NATIVE_ROLE_GRAPH_ORDER == ("perception", "solver", "reviewer", "planner")
    assert episode_node_order(_episode()) == NATIVE_ROLE_GRAPH_ORDER


def test_an_episode_without_the_four_roles_is_refused_by_name():
    with pytest.raises(NativeEpisodeDryRunError, match="declares no"):
        episode_node_order(_episode(roles=("perception", "solver")))


def test_reading_a_composition_before_composing_it_is_refused():
    class _Runtime:
        pass

    with pytest.raises(NativeEpisodeDryRunError, match="compose_dry_run"):
        legal_intent_ids(_Runtime())


# ---------------------------------------------------------------------------
# The real cell
# ---------------------------------------------------------------------------


def _data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR")
    if not raw:
        return None
    root = Path(raw)
    return root if root.is_dir() else None


def _umbrella_lock() -> Path | None:
    from speech_aware_evidence_acquisition.data.lock import umbrella_lock_path

    # A worktree is NOT in the adjacent-checkout layout, and a worktree is
    # exactly where a fix to these rails is developed and dry-run. The
    # established override name (``scripts/run_enhancement_survey.py``) makes
    # the real-cell walk runnable there instead of silently skipping.
    override = os.environ.get("SAEA_UMBRELLA_LOCK")
    if override:
        path = Path(override)
        return path if path.is_file() else None
    try:
        path = umbrella_lock_path(REPO_ROOT)
    except Exception:  # pragma: no cover - absent umbrella checkout
        return None
    return path if path.is_file() else None


def _canned_answers(runtime) -> dict[str, str]:
    """A fake frozen core: one schema-valid answer per role.

    The Perception answer is the COMPACT document the registered
    ``slurp-intent-hypotheses-v1`` schema defines -- exactly what a flight
    seals -- and names candidates the delta store actually addresses, so the
    candidate-bound routes have something to select.
    """

    legal = set(legal_intent_ids(runtime))
    addressed = [item for item in store_facet_ids(runtime, DELTA_STORE) if item in legal]
    assert addressed, "the released delta store addresses no legal candidate"
    candidates = sorted(addressed)[:3]
    perception = json.dumps(
        {
            "candidates": [
                {
                    "intent_id": intent,
                    "distinction": "Dry-run canned alternative.",
                    "evidence_refs": [],
                    "unresolved_fields": [],
                }
                for intent in candidates
            ]
        },
        separators=(",", ":"),
    )
    return {
        "perception": perception,
        "solver": f"intent: {candidates[0]}\nentities: none",
        "reviewer": "The draft names one legal intent and no unsupported entity.",
        "planner": "ACCEPT",
    }


def _smoke_composition(*, sample_limit: int = 1):
    """``(runtime, binding)`` for the registered smoke cell, or a skip."""

    from speech_aware_evidence_acquisition.core.flight.factory import (
        build_flight_runtime,
    )

    data_root = _data_root()
    lock_path = _umbrella_lock()
    if data_root is None or lock_path is None:
        pytest.skip("the released stores and the umbrella lock are not available here")
    fragment_path = REPO_ROOT / "configs" / "experiment" / f"{SMOKE_EXPERIMENT}.json"
    fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == SMOKE_CELL)

    try:
        runtime = build_flight_runtime(
            REPO_ROOT,
            data_root,
            model=cell["model_fragment"],
            dataset=cell["dataset_fragment"],
            baseline=cell["baseline_fragment"],
            experiment=SMOKE_EXPERIMENT,
            run_id=cell["run_id"],
            attempt_id=cell["attempt_id"],
            runtime_root=Path.home(),
            lock_path=lock_path,
            campaign_active=False,
        )
        binding = compose_dry_run(runtime, sample_limit=sample_limit)
    except Exception as error:  # pragma: no cover - host without the assets
        pytest.skip(f"this host cannot compose the cell offline: {error}")
    return runtime, binding


def _answers_for(candidates, *, revise_on_first_visit=False):
    """A fake frozen core answering with a GIVEN candidate list.

    The Perception answer is the COMPACT document the registered
    ``slurp-intent-hypotheses-v1`` schema defines -- exactly what a flight
    seals. Which intents it names is the whole variable: a node-filtered
    candidate-bound route selects from its OWN slice, and the slices do not
    all address the same intents.
    """

    perception = json.dumps(
        {
            "candidates": [
                {
                    "intent_id": intent,
                    "distinction": "Dry-run canned alternative.",
                    "evidence_refs": [],
                    "unresolved_fields": [],
                }
                for intent in candidates
            ]
        },
        separators=(",", ":"),
    )

    def answer(role: str, visit: int) -> str:
        if role == "perception":
            return perception
        if role == "solver":
            return f"intent: {candidates[0]}\nentities: none"
        if role == "reviewer":
            return "The draft names one legal intent and no unsupported entity."
        if role == "planner":
            return "REVISE" if (revise_on_first_visit and visit == 1) else "ACCEPT"
        raise AssertionError(f"unexpected role {role!r}")

    return answer


def test_the_cell_1_smoke_composition_walks_its_whole_episode():
    """The proof the flight budget paid for twice: walk the registered
    smoke cell's own composition, offline, for one row."""

    _runtime, binding = _smoke_composition(sample_limit=1)
    runtime = _runtime

    assert DELTA_STORE in binding["store_ids"]
    assert episode_node_order(binding["episode"]) == (
        "perception",
        "solver",
        "reviewer",
        "planner",
    )

    result = dry_run_native_episode(
        runtime, answers=_canned_answers(runtime), sample_limit=1
    )

    assert result.schema == DRY_RUN_SCHEMA
    assert tuple(node.phase for node in result.nodes) == (
        "perception",
        "solver",
        "reviewer",
        "planner",
    )
    # The Perception node answered under the compact contract, and what was
    # sealed is what the model said -- the very shape the pre-fix route
    # refused.
    perception = result.nodes[0]
    assert perception.response_format_id == "slurp-intent-hypotheses-v1"
    assert perception.state_kind == "phase:perception"

    # Every node saw its OWN node_target slice of the delta store: the
    # Perception route through the first-phase seed, the other three through
    # their candidate-bound boundary.
    def deltas(value_ids):
        return [item for item in value_ids if item.startswith(f"{DELTA_STORE}::")]

    assert deltas(result.bootstrap_value_ids), "the unconditional route seeded nothing"
    for node in result.nodes[1:]:
        assert deltas(node.supplied_value_ids), f"{node.phase} received no delta"

    # The delivery is the Solver's own sealed draft, not the last node's.
    assert result.delivered_phase == "solver"
    assert result.delivered_sha256

    # The receipt is JSON, so a runbook can keep it beside a launch.
    document = result.as_json()
    assert json.loads(json.dumps(document)) == document
    assert document["supplied_value_counts"]["perception"] >= 1


# ---------------------------------------------------------------------------
# The third failure: the rows the canned composition never asked about
# ---------------------------------------------------------------------------

#: The Perception candidate ids the RETIRED v2 smoke actually produced, read
#: off that attempt's own trace (``MODEL_RESPONSE`` records, ids only). Rows 1
#: and 3 completed their episodes; rows 2 and 4 died at the openJiuwen vertex
#: ``reviewer_0_input`` with "acquire must introduce at least one new value or
#: facet", because the Reviewer slice of the released store addresses 30 of
#: the 39 legal intents and neither row's candidates fall in it.
TRACE_CANDIDATES = {
    "slurp:train:000007:audio--1504197557": (
        "audio_volume_up",
        "audio_volume_mute",
        "play_audiobook",
    ),
    "slurp:train:000009:audio-1497557594-headset": (
        "iot_hue_lightchange",
        "iot_hue_lightup",
        "iot_hue_lighton",
    ),
    "slurp:train:000015:audio-1488524781": (
        "audio_volume_up",
        "play_radio",
        "audio_volume_mute",
    ),
    "slurp:train:000023:audio-1490956038": (
        "iot_hue_lightdim",
        "iot_hue_lighton",
        "iot_hue_lightoff",
    ),
}


def test_every_smoke_row_walks_on_the_candidates_the_flight_actually_produced():
    """The regression the v2 smoke paid 12 contacts to discover.

    The canned answers of the test above name candidates read off the store's
    OWN union of addressed facets, so every node's slice had something to
    select and the walk was green on a defect that killed half the roster.
    These are the candidates the flight itself produced. Pre-fix, rows 2 and
    4 raise ``RailsError: acquire must introduce at least one new value or
    facet`` here -- the flight's own error, offline, for nothing. Post-fix,
    all four rows complete, and the nodes whose slice has nothing for the row
    simply take no supply step.
    """

    runtime, _binding = _smoke_composition(sample_limit=4)
    roster = tuple(item.sample_id for item in runtime._samples)
    assert roster == tuple(TRACE_CANDIDATES), roster

    def deltas(value_ids):
        return [item for item in value_ids if item.startswith(f"{DELTA_STORE}::")]

    supplied = {}
    for sample_id, candidates in TRACE_CANDIDATES.items():
        result = dry_run_native_episode(
            runtime,
            answers=_answers_for(candidates),
            sample_id=sample_id,
            sample_limit=4,
        )
        assert tuple(node.phase for node in result.nodes) == NATIVE_ROLE_GRAPH_ORDER
        assert result.delivered_phase == "solver"
        supplied[sample_id] = {
            node.phase: len(deltas(node.supplied_value_ids))
            for node in result.nodes
        }

    # The two rows that completed in the flight are supplied at every node;
    # the two that died supply the Solver and decline Reviewer and Planner.
    rows = list(TRACE_CANDIDATES)
    assert supplied[rows[0]]["reviewer"] == 3
    assert supplied[rows[0]]["planner"] == 1
    assert supplied[rows[1]]["reviewer"] == 0
    assert supplied[rows[1]]["planner"] == 0
    assert supplied[rows[2]]["reviewer"] == 2
    assert supplied[rows[3]]["reviewer"] == 0

    # And the skips are receipted, per node and per row, with their reason.
    router = _binding["phase_binding"].get("supply_for_store")
    audits = router.receipt["delta_supply"]
    declined = {
        (entry["phase"], entry["sample_id"])
        for entry in audits.values()
        if entry["selected"] == 0
    }
    assert ("reviewer", rows[1]) in declined
    assert ("planner", rows[1]) in declined
    assert ("reviewer", rows[3]) in declined
    for entry in audits.values():
        assert entry["node"] == entry["phase"]
        assert entry["store_id"] == DELTA_STORE
        assert entry["reason"]


def test_a_revise_verdict_revisits_three_nodes_without_acquiring_twice():
    """The other way a route introduces nothing: the cumulative value set.

    A per-node selection is a pure function of (phase, sample), so the second
    visit of the Solver, the Reviewer and the Planner is handed ids the
    episode already holds. The walk performs the runner's own
    ``restrict_repeat_visit_supply`` step, so this is the flight's behaviour
    and not an approximation of it.
    """

    runtime, _binding = _smoke_composition(sample_limit=4)
    sample_id, candidates = next(iter(TRACE_CANDIDATES.items()))
    result = dry_run_native_episode(
        runtime,
        answers=_answers_for(candidates, revise_on_first_visit=True),
        sample_id=sample_id,
        sample_limit=4,
        node_order=NATIVE_ROLE_GRAPH_ORDER + ("solver", "reviewer", "planner"),
    )

    walked = tuple((node.phase, node.visit) for node in result.nodes)
    assert walked == (
        ("perception", 1),
        ("solver", 1),
        ("reviewer", 1),
        ("planner", 1),
        ("solver", 2),
        ("reviewer", 2),
        ("planner", 2),
    )
    first_visits = {node.phase: node for node in result.nodes[:4]}
    assert first_visits["solver"].supplied_value_ids
    assert first_visits["reviewer"].supplied_value_ids
    # Every second visit acquires nothing: the values it would have been
    # given are already on the accumulated QueryState.
    for node in result.nodes[4:]:
        assert node.supplied_value_ids == (), node.phase


def test_a_duplicate_candidate_row_walks_instead_of_killing_the_flight():
    """The 2026-09-23 ARM abort, offline.

    The CELL-1 ARM spent 304 metered contacts and died at row ~75 of 1,080
    with ``candidate intent_ids must be unique and ordered``, raised inside
    the stage3-deltas candidate-bound route. Two of its 75 Perception answers
    named ONE legal intent three times; the sealed PLAN arm carries 25 such
    rows in 1,080 (2.3 %) -- including one of those two, sample
    ``slurp:train:000544:audio-1501158529`` -- and completed every one of
    them, because its only other reader of that state, the slot-contracts
    candidate supply, declares the bounded first-occurrence projection.

    Pre-fix this walk raised ``KnowledgeStoreError: candidate intent_ids must
    be unique and ordered`` on both duplicate shapes. Post-fix all four shapes
    complete the whole graph, the duplicates project to their first
    occurrences, and the projection is receipted per node and per row.
    """

    runtime, binding = _smoke_composition(sample_limit=4)
    roster = tuple(item.sample_id for item in runtime._samples)
    legal = set(legal_intent_ids(runtime))
    addressed = sorted(
        item for item in store_facet_ids(runtime, DELTA_STORE) if item in legal
    )
    assert len(addressed) >= 3, addressed
    first, second, third = addressed[:3]

    # One row per shape: a router memoises its per-row selection by
    # (phase, sample, query-state hash), so two shapes cannot share a row.
    shapes = {
        # exactly the shape the ARM died on, and the PLAN arm's own n=3/d=1
        "duplicate-all-the-same": (first, first, first),
        # the PLAN arm's other duplicate shape, n=3 distinct=2
        "duplicate-one-repeat": (first, second, first),
        # "ordered" in the refusal text is not an ordering constraint
        "out-of-order-descending": tuple(sorted((first, second, third), reverse=True)),
        "clean-control": (first, second, third),
    }

    for (shape, candidates), sample_id in zip(shapes.items(), roster):
        result = dry_run_native_episode(
            runtime,
            answers=_answers_for(candidates),
            sample_id=sample_id,
            sample_limit=4,
        )
        assert tuple(node.phase for node in result.nodes) == NATIVE_ROLE_GRAPH_ORDER, shape
        assert result.delivered_phase == "solver", shape

    router = binding["phase_binding"].get("supply_for_store")
    projections = router.receipt["delta_candidate_projection"]
    # Only the two duplicate rows are recorded, and every node that read them.
    recorded = {entry["sample_id"] for entry in projections.values()}
    assert recorded == {roster[0], roster[1]}, recorded
    by_row = {
        entry["sample_id"]: (entry["raw_positions"], entry["retained_positions"])
        for entry in projections.values()
    }
    assert by_row[roster[0]] == (3, 1)
    assert by_row[roster[1]] == (3, 2)
    for entry in projections.values():
        assert entry["store_id"] == DELTA_STORE
        assert entry["node"] == entry["phase"]
        assert entry["projection_policy_id"]
        assert entry["original_text_sha256"] != entry["projected_content_sha256"]


# ---------------------------------------------------------------------------
# Cell RANKVIS (owner decision 171): the dry run honours
# native_episode.knowledge_value_rendering exactly as rails.runner does.
#
# The dry run never renders a request's text (it only hashes the phase's
# static instruction), so the one place a retrieval-rank reorder is visible
# here is DryRunNode.supplied_value_ids -- the named store's selected value
# ids in the order a flight would acquire and later render them, "retrieval
# rank 1", "retrieval rank 2", ... in that same order. These proofs are
# synthetic (a two-node perception -> solver walk with a stand-in supply,
# not any registered cell) and model-free: no utterance, gold or model text.
# ---------------------------------------------------------------------------

_RANKVIS_STORE = "train-exemplars"

_RANKVIS_RENDERING = {
    "schema": KNOWLEDGE_VALUE_RENDERING_SCHEMA,
    "order": "retrieval-rank",
    "rank_visible": True,
    "stores": [_RANKVIS_STORE],
}

_RANKVIS_ANSWERS = {"perception": "PERCEPTION ANSWER", "solver": "SOLVER ANSWER"}


def _rankvis_material_for_phase(phase_name, context, _sealed_states):
    return PhaseMaterial(
        instruction=f"Synthetic instruction for {phase_name}.",
        response_format=None,
        contact_id=f"dry-run-rankvis-test:{phase_name}:{context.sample_id}",
        purpose="assistant",
    ).validate()


def _rankvis_ranked_supply(snapshot):
    # _prepared_supply with facet b ranked above facet a, so a retrieval-rank
    # reorder visibly moves the odd-indexed exemplars in front of the even
    # ones (mirrors test_knowledge_value_rendering.py's own _ranked_supply).
    from speech_aware_evidence_acquisition.rails.knowledge import RankedFacet

    inner = _prepared_supply(snapshot)

    def supply_for_phase(phase_name, context):
        supply = inner(phase_name, context)
        if supply is None:
            return None
        rank = replace(
            supply.rank_result,
            candidates=(
                RankedFacet(facet_id=EXEMPLAR_FACET_IDS[1], score=0.9),
                RankedFacet(facet_id=EXEMPLAR_FACET_IDS[0], score=0.5),
            ),
        ).validate()
        decision = replace(
            supply.fusion_decision, rank_result_sha256=rank.content_hash()
        ).validate()
        return replace(supply, rank_result=rank, fusion_decision=decision).validate()

    return supply_for_phase


def _rankvis_runtime(*, rendering=None, supply_factory=_prepared_supply):
    # A minimal, synthetic runtime for dry_run_native_episode: its own
    # _dry_run_binding is set directly, so compose_dry_run (and the
    # FlightRuntime machinery it needs) never runs.
    sample = _FakeSample(
        sample_id="s1", audio_ref=AudioRef(path="a.wav", sha256="a" * 64), audio_seconds=2.0,
    )
    snapshot = _exemplar_snapshot()
    program = _supplied_program(max_contacts=5)
    episode = NativeEpisodeConfig(
        episode_id="dry-run-rankvis-v1",
        max_revisions=1,
        actions=("ACCEPT", "REVISE", "ACQUIRE"),
        roles=(
            NativeEpisodeRole(phase_id="perception", role_kind="perception", max_iterations=1, tool_names=()),
            NativeEpisodeRole(phase_id="solver", role_kind="solver", max_iterations=1, tool_names=()),
        ),
        max_contacts=5,
    )
    if rendering is not None:
        episode = replace(episode, knowledge_value_rendering_json=json.dumps(rendering))

    runtime = SimpleNamespace()
    runtime._samples = (sample,)
    runtime._adapter = _FakeAdapter(samples=(sample,))
    runtime._plan = SimpleNamespace(run_id="dry-run-rankvis-test", split_identity_hash="a" * 64)
    runtime._composed = SimpleNamespace(values={})
    runtime._phase_supply_seeds = lambda *args, **kwargs: ({}, {})
    runtime._dry_run_binding = {
        "values": {},
        "policy": "dry-run-rankvis-test",
        "program": program,
        "episode": episode,
        "phase_binding": {
            "material_for_phase": _rankvis_material_for_phase,
            "supply_for_phase": supply_factory(snapshot),
            "knowledge_snapshot": snapshot,
            "speech_packet_bindings": {"s1": {"packet_id": "a.wav", "sha256": "a" * 64}},
        },
        "store_ids": (_RANKVIS_STORE,),
        "supply_variant_for_phase": None,
    }
    return runtime


def _rankvis_walk(*, rendering, supply_factory):
    runtime = _rankvis_runtime(rendering=rendering, supply_factory=supply_factory)
    return dry_run_native_episode(
        runtime, answers=_RANKVIS_ANSWERS, sample_id="s1", sample_limit=1,
        node_order=("perception", "solver"),
    )


def test_dry_run_without_the_key_supplies_todays_order():
    # OFF (no key): the solver node's supplied ids are the supply's own
    # order, untouched -- the pre-RANKVIS behaviour, byte for byte.
    result = _rankvis_walk(rendering=None, supply_factory=_prepared_supply)
    solver_node = next(node for node in result.nodes if node.phase == "solver")
    assert solver_node.supplied_value_ids == EXEMPLAR_VALUE_IDS


def test_dry_run_armed_with_retrieval_rank_shows_the_rank_order():
    # ON (retrieval-rank): the solver node's supplied ids are re-ordered by
    # retrieval rank -- facet b's (odd-indexed) exemplars first, in the exact
    # order a rank-visible render would number "retrieval rank 1",
    # "retrieval rank 2", ... -- the same reorder rails.runner applies at a
    # flight's own supply step, reached here through the SAME function.
    result = _rankvis_walk(rendering=_RANKVIS_RENDERING, supply_factory=_rankvis_ranked_supply)
    solver_node = next(node for node in result.nodes if node.phase == "solver")
    expected_order = EXEMPLAR_VALUE_IDS[1::2] + EXEMPLAR_VALUE_IDS[0::2]
    assert solver_node.supplied_value_ids == expected_order
    assert set(solver_node.supplied_value_ids) == set(EXEMPLAR_VALUE_IDS)


def test_dry_run_the_key_changes_only_the_reordered_store():
    # Without the key the render is byte-identical to today's; with it, only
    # the reordered store's own supplied ids (and the counts derived from
    # them) move -- every other field of the walked receipt, including the
    # perception node and the solver node's instruction hash, is unchanged.
    off = _rankvis_walk(rendering=None, supply_factory=_prepared_supply).as_json()
    on = _rankvis_walk(
        rendering=_RANKVIS_RENDERING, supply_factory=_rankvis_ranked_supply
    ).as_json()
    off_nodes = {node["phase"]: node for node in off["nodes"]}
    on_nodes = {node["phase"]: node for node in on["nodes"]}
    assert off_nodes["perception"] == on_nodes["perception"]
    assert off_nodes["solver"]["supplied_value_ids"] != on_nodes["solver"]["supplied_value_ids"]
    for key in off_nodes["solver"]:
        if key == "supplied_value_ids":
            continue
        assert off_nodes["solver"][key] == on_nodes["solver"][key], key
    # Same items, different order: a reorder, never an addition or a drop.
    assert off["supplied_value_counts"] == on["supplied_value_counts"]
