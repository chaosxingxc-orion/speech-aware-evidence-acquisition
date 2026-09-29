"""Actual FlightRuntime phase dispatch reaches the shared native graph."""

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import scorers as _scorers  # noqa: F401
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_outputs,
    _verify_outputs_trace_binding,
)
from speech_aware_evidence_acquisition.core.flight import runtime as flight_module
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core import preparation_fit
from speech_aware_evidence_acquisition.core.base import JudgeVerdict
from speech_aware_evidence_acquisition.core import judges as core_judges
from speech_aware_evidence_acquisition.rails.phase_review import (
    PhaseReviewSpec,
    build_review_for_phase,
)
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

from speech_aware_evidence_acquisition.rails import relisten as rl

from test_e4_relisten_live import (
    REPO_ROOT as RELISTEN_REPO_ROOT,
    _armed_config,
    _arm_relisten_request_gate,
    _two_entity_output,
)
from test_native_episode_runner import _ActualEpisodeHarness
from test_slurp_legal_label_projection_v2 import (
    _PAIRING,
    _PRIOR,
    _FakeIntentProfile,
    _FakeOntology,
    _FakeSchema,
    _gold,
    _official_result,
)
from test_native_episode_runner_grouped_solver import (
    ANSWERS,
    COMMIT,
    DECODING_OVERRIDES,
    _grouped_output,
    _grouped_review_loop_config,
)
from test_role_context_runner import _configure_typed_context
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_rails_runner import _knowledge_snapshot


@pytest.mark.parametrize("max_revisions", (0, 1))
@pytest.mark.parametrize(
    ("history_scope", "typed_context"),
    (
        pytest.param(None, False, id="default"),
        pytest.param("latest-solver-and-local-tools", False, id="history-scope"),
        pytest.param(None, True, id="typed-role-context"),
    ),
)
def test_flight_config_dispatches_actual_roles_and_preserves_solver_custody(
    tmp_path,
    monkeypatch,
    max_revisions,
    history_scope,
    typed_context,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=2,
        max_revisions=max_revisions,
        max_contacts=4 + 3 * max_revisions,
        planner_actions=(("ACCEPT",) if max_revisions == 0 else ("REVISE", "ACCEPT")),
        arm="speech-feature-query",
    )
    typed_expected = _configure_typed_context(harness) if typed_context else None
    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": max_revisions,
            "actions": dict(
                zip(("accept", "revise", "acquire"), harness.config.actions)
            ),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                }
                for role in harness.config.roles
            },
        },
        "native_contact_fit": {
            "run_id": "SAEA-NATIVE-DISPATCH-FIT",
            "attempt_id": "attempt-native-dispatch-fit",
            "contact_cap": 8 * harness.config.max_contacts,
        },
    }
    if history_scope is not None:
        values["native_episode"]["roles"]["reviewer"]["history_scope"] = history_scope
    if typed_context:
        values["native_episode"]["role_context"] = json.loads(
            harness.config.role_context_json
        )
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    judge_id = core_judges.EARNINGS_NUMERIC_FORMAT_JUDGE_V1
    review = build_review_for_phase(
        {
            role.phase_id: PhaseReviewSpec(phase=role.phase_id, judges=(judge_id,))
            for role in harness.config.roles
        },
        judges={
            judge_id: lambda draft, material, state: JudgeVerdict(
                judge_id, "v1", score=0.5
            ),
        },
    )
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
        "review_for_phase": review,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None

    def capacity_identity_only(request):
        harness.request_gate(request)
        capacity_identity_only.receipts.append({"capacity_verified": False})

    capacity_identity_only.receipts = []
    factories = []

    def fit_factory(actual_runtime, actual_program, actual_plan):
        factories.append((actual_runtime, actual_program, actual_plan))
        return capacity_identity_only

    monkeypatch.setattr(
        flight_module, "default_phase_program", lambda _policy: harness.program
    )
    monkeypatch.setattr(preparation_fit, "build_native_contact_fit_gate", fit_factory)
    try:
        rows, contacts, kind, dispatch, _phases = runtime._dispatch_phase_program(
            harness.client,
            harness.plan,
            harness.program.program_id,
        )
    finally:
        closed = harness.close()

    assert factories == [(runtime, harness.program, harness.plan)]
    assert contacts == closed["request_count"] == 2 * harness.config.max_contacts
    assert kind == "phase-program"
    assert dispatch["dispatch"] == "phase-program-continuous"
    assert dispatch["contacts_per_sample_ceiling"] == harness.config.max_contacts
    assert dispatch["native_episode"]["episode_id"] == harness.config.episode_id
    if typed_context:
        assert dispatch["native_episode"]["role_context"] == json.loads(
            harness.config.role_context_json
        )
    else:
        assert "role_context" not in dispatch["native_episode"]
    receipt_roles = {row["role_kind"]: row for row in dispatch["native_episode"]["roles"]}
    if history_scope is None:
        assert all("history_scope" not in row for row in receipt_roles.values())
    else:
        assert receipt_roles["reviewer"]["history_scope"] == history_scope
        assert all("history_scope" not in receipt_roles[role] for role in ("perception", "solver", "planner"))
        for key, prepared in harness.prepared.items():
            if key[1] == "reviewer":
                assert "perception-analysis:" not in json.dumps(prepared["rendered"])
    assert len(dispatch["native_contact_fit_receipts"]) == contacts
    expected_final = (
        typed_expected["revised_draft" if max_revisions else "first_draft"]
        if typed_expected is not None
        else None
    )
    assert [row["final_response_text"] for row in rows] == (
        [expected_final, expected_final]
        if typed_context
        else [
            f"solver-answer:s1:visit:{max_revisions + 1}",
            f"solver-answer:s2:visit:{max_revisions + 1}",
        ]
    )
    for row in rows:
        receipt = row["native_episode_receipt"]
        accepted = receipt["accepted_solver_receipt"]["final_contact"]
        assert ":solver:" in accepted["agent_contact_id"]
        assert receipt["planner_routes"][-1]["action"] == "ACCEPT"

    assert harness.trace.records == []  # FlightRuntime flushed its one-shot buffer.
    trace_rows = [
        json.loads(line)
        for line in (harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl")
        .read_text()
        .splitlines()
    ]
    judgments = [
        row["payload"]
        for row in trace_rows
        if row["channel"] == "USE" and "use_phase_judgments" in row["payload"]
    ]
    assert len(judgments) == contacts
    assert len({row["use_source_request_id"] for row in judgments}) == contacts

    runtime._output_rows = rows
    canonical = runtime._canonical_output_rows(harness.client)
    for row in canonical:
        if typed_context:
            assert row["text"] == expected_final
        else:
            assert row["text"].startswith("solver-answer:")
        assert (
            hashlib.sha256(row["text"].encode()).hexdigest()
            == row["response_text_sha256"]
        )
        accepted = row["native_episode_receipt"]["accepted_solver_receipt"][
            "final_contact"
        ]
        assert row["request_id"] == accepted["request_id"]
        latest = [t for t in harness.client.timings if t.sample_id == row["sample_id"]][
            -1
        ]
        assert (
            row["request_id"] != latest.request_id
        )  # Planner cannot become the source.

    altered = copy.deepcopy(rows)
    altered[0]["native_episode_receipt"]["accepted_solver_receipt"]["final_contact"][
        "response_sha256"
    ] = "0" * 64
    runtime._output_rows = altered
    with pytest.raises(FlightRuntimeError, match="accepted runtime result"):
        runtime._canonical_output_rows(harness.client)


@pytest.mark.parametrize("max_revisions", (0, 1))
def test_canonical_outputs_accept_an_opted_in_terminal_solver_delivery(
    tmp_path, monkeypatch, max_revisions
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=max_revisions,
        max_contacts=4 + 3 * max_revisions,
        planner_actions=("ACCEPT",) if max_revisions == 0 else ("REVISE", "ACCEPT"),
        arm="speech-feature-query",
    )
    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": max_revisions,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                }
                for role in harness.config.roles
            },
        },
        "native_contact_fit": {
            "run_id": "SAEA-NATIVE-TERMINAL-FIT",
            "attempt_id": "attempt-native-terminal-fit",
            "contact_cap": 4 + 3 * max_revisions,
        },
    }
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
        "review_for_phase": None,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None
    monkeypatch.setattr(flight_module, "default_phase_program", lambda _policy: harness.program)
    def terminal_capacity_gate(request):
        harness.request_gate(request)
        terminal_capacity_gate.receipts.append({"capacity_verified": False})

    terminal_capacity_gate.receipts = []
    monkeypatch.setattr(
        preparation_fit, "build_native_contact_fit_gate", lambda *_args: terminal_capacity_gate
    )
    try:
        rows, *_ = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id
        )
    finally:
        harness.close()

    terminal_receipt = copy.deepcopy(rows[0]["native_episode_receipt"])
    terminal_receipt.pop("accepted_solver_receipt")
    terminal_receipt["terminal_solver_receipt"] = copy.deepcopy([
        visit["execution_receipt"]
        for visit in terminal_receipt["role_visits"]
        if visit["stage"] == "solver"
    ][-1])
    terminal_receipt["planner_routes"][-1]["action"] = "REVISE"
    terminal_receipt["terminal_disposition"] = {
        "reason": "revision_limit",
        "planner_action": "REVISE",
        "revision_count": max_revisions,
        "planner_accepted": False,
    }
    values["native_episode"]["exhaustion_policy"] = "deliver-latest-solver"
    row = {**rows[0], "native_episode_receipt": terminal_receipt}
    runtime._output_rows = [row]
    runtime._phase_summaries = (
        SimpleNamespace(results=(SimpleNamespace(
            sample_id=row["sample_id"],
            final_response_text=row["final_response_text"],
            native_episode_receipt=terminal_receipt,
        ),)),
    )

    canonical = runtime._canonical_output_rows(harness.client)

    terminal = terminal_receipt["terminal_solver_receipt"]["final_contact"]
    assert canonical[0]["request_id"] == terminal["request_id"]
    assert canonical[0]["text"] == row["final_response_text"]

    terminal_receipt["terminal_disposition"]["planner_action"] = "UNREGISTERED"
    terminal_receipt["planner_routes"][-1]["action"] = "UNREGISTERED"
    with pytest.raises(FlightRuntimeError, match="configured revise/acquire action"):
        runtime._canonical_output_rows(harness.client)


    if max_revisions:
        terminal_receipt["terminal_disposition"]["planner_action"] = "REFRESH_CANDIDATES"
        terminal_receipt["planner_routes"][-1]["action"] = "REFRESH_CANDIDATES"
        with pytest.raises(FlightRuntimeError, match="configured revise/acquire action"):
            runtime._canonical_output_rows(harness.client)
        values["native_episode"]["candidate_refresh"] = {
            "action": "REFRESH_CANDIDATES", "max_refreshes": 1,
        }
        refreshed_terminal = runtime._canonical_output_rows(harness.client)
        assert refreshed_terminal[0]["request_id"] == terminal["request_id"]
        assert refreshed_terminal[0]["text"] == row["final_response_text"]


def test_grouped_solver_seals_a_row_the_bundle_verifier_accepts(tmp_path, monkeypatch):
    """E2d (SLURP v2 base program M2): what ``_canonical_output_rows`` seals
    for a samples-N Solver visit, and that ``core.bundle`` accepts it.

    Cell B2 v3's four-row smoke generated every contact and then failed AT THE
    SEAL: the pre-E2d runner bound a grouped row's ``response_text_sha256`` to
    the LAST RAW sample's response text while ``text`` carried the COMMIT
    policy's aggregate, so I7 ("the text was mutated after the model response
    was recorded") refused it. Both halves of the repair are proved here on
    one real dispatch: the sealed row now hashes the DELIVERED bytes and
    records the commit parameters, and the bundle verifier re-derives those
    bytes from the row's own recorded samples (I7g), whose response hashes it
    pins to this run's own trace records.
    """

    samples = 3
    max_contacts = 1 + samples + 1 + 1  # perception + group + reviewer + planner
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=max_contacts,
        planner_actions=("ACCEPT",),
        arm="speech-feature-query",
    )
    harness.config = _grouped_review_loop_config(
        max_contacts=max_contacts,
        samples=samples,
        decoding_overrides=DECODING_OVERRIDES,
        commit=COMMIT,
    )
    harness._output = _grouped_output
    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": 0,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                    **(
                        {
                            "samples": role.samples,
                            "decoding_overrides": dict(role.decoding_overrides),
                            "commit": dict(role.commit),
                        }
                        if role.role_kind == "solver"
                        else {}
                    ),
                }
                for role in harness.config.roles
            },
        },
        "native_contact_fit": {
            "run_id": "SAEA-NATIVE-GROUPED-SEAL-FIT",
            "attempt_id": "attempt-native-grouped-seal-fit",
            "contact_cap": 8 * max_contacts,
        },
    }
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None

    def capacity_identity_only(request):
        harness.request_gate(request)
        capacity_identity_only.receipts.append({"capacity_verified": False})

    capacity_identity_only.receipts = []
    monkeypatch.setattr(
        flight_module, "default_phase_program", lambda _policy: harness.program
    )
    monkeypatch.setattr(
        preparation_fit,
        "build_native_contact_fit_gate",
        lambda *_args: capacity_identity_only,
    )
    try:
        rows, contacts, _kind, _dispatch, _phases = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id,
        )
    finally:
        harness.close()

    assert contacts == max_contacts
    runtime._output_rows = rows
    canonical = runtime._canonical_output_rows(harness.client)
    assert len(canonical) == 1
    row = canonical[0]

    group = row["solver_group"]
    # (1) The receipt now records the parameters the policy was applied with,
    # so a post-seal reader can re-run the exact commit this visit made.
    assert group["commit_policy_id"] == COMMIT["policy"]
    assert group["commit_params"] == {
        "min_support": COMMIT["min_support"],
        "similarity_threshold": COMMIT["similarity_threshold"],
    }
    assert [record["sample_index"] for record in group["samples"]] == list(range(samples))

    # (2) The delivered text equals NO raw sample's text -- the fact that broke
    # the old seal -- and the row's own hash now describes those delivered
    # bytes, not the last raw contact's.
    raw_texts = [json.dumps(answer, ensure_ascii=False, sort_keys=True) for answer in ANSWERS]
    assert row["text"] not in raw_texts
    assert hashlib.sha256(row["text"].encode()).hexdigest() == row["response_text_sha256"]
    last_contact = group["samples"][-1]["contacts"][-1]
    assert row["response_text_sha256"] != last_contact["response_text_sha256"]
    # ...while the row's transport identity is still that one real contact.
    assert row["request_id"] == last_contact["request_id"]
    assert row["response_sha256"] == last_contact["response_sha256"]

    # (3) The bundle verifier accepts it, against this run's own trace.
    trace_records = {}
    for line in (
        (harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        document = json.loads(line)
        trace_records[document["record_id"]] = document["payload"]
    raw = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    verified = _verify_outputs(
        raw, frozenset({row["sample_id"]}), row["carrier_lock_key"], row["arm"],
    )
    _verify_outputs_trace_binding(verified, trace_records)

    # ...and refuses the same row once its delivered text is rewritten, with
    # its own hash recomputed so that I7 alone would not notice.
    forged = dict(row)
    forged["text"] = row["text"] + " "
    forged["response_text_sha256"] = hashlib.sha256(forged["text"].encode()).hexdigest()
    forged_raw = (json.dumps(forged, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    with pytest.raises(BundleError, match="I7g"):
        _verify_outputs(
            forged_raw, frozenset({row["sample_id"]}), row["carrier_lock_key"], row["arm"],
        )


# ---------------------------------------------------------------------------
# E8c: one malformed Planner token is a row, not a campaign.
# ---------------------------------------------------------------------------

E8C_ACCEPT_ID = "slurp:devel:000001:rec-a"
E8C_ILLEGAL_ID = "slurp:devel:000002:rec-b"
#: The six-letter token the sealed B7a anchor trace actually carried.
E8C_ILLEGAL_TOKEN = "REJECT"
E8C_DRAFTS = {
    E8C_ACCEPT_ID: json.dumps(
        {
            "scenario": "recommendation",
            "action": "locations",
            "entities": [{"type": "place_name", "filler": "berlin"}],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ),
    E8C_ILLEGAL_ID: json.dumps(
        {
            "scenario": "alarm",
            "action": "set",
            "entities": [{"type": "time", "filler": "seven"}],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ),
}


def test_an_illegal_planner_token_seals_its_row_and_the_campaign_continues(
    tmp_path, monkeypatch
):
    """E8c.  Cell B7a's 1,080-row arm aborted at 618 rows because ONE Planner
    response was the token ``REJECT`` instead of ``ACCEPT``/``REVISE``: the
    harness raised, and the whole campaign died with it.

    Here the same token arrives on the second sample of a real two-row
    dispatch.  The row is RETAINED: its committed draft is delivered
    unchanged, its receipt carries the ``planner_action_illegal`` count and
    the token's sha256 (never the token beyond 32 characters), the campaign
    runs the row to its seal and keeps its contact accounting, the bundle
    verifier accepts the sealed row, and the registered SLURP official scorer
    scores it exactly like the accepted row beside it.
    """

    max_contacts = 7  # perception + (solver, reviewer, planner) * 2
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=2,
        max_revisions=1,
        max_contacts=max_contacts,
        planner_actions=("ACCEPT", "ACCEPT"),
        arm="speech-feature-query",
        sample_ids=(E8C_ACCEPT_ID, E8C_ILLEGAL_ID),
    )

    def output(key):
        sample_id, phase, visit, _turn = key
        if phase == "solver":
            return E8C_DRAFTS[sample_id]
        if phase == "planner":
            return "ACCEPT" if sample_id == E8C_ACCEPT_ID else E8C_ILLEGAL_TOKEN
        return f"{phase}-analysis:{sample_id}:visit:{visit}"

    harness._output = output
    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": 1,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                }
                for role in harness.config.roles
            },
        },
        "native_contact_fit": {
            "run_id": "SAEA-NATIVE-ILLEGAL-PLANNER-FIT",
            "attempt_id": "attempt-native-illegal-planner-fit",
            "contact_cap": 8 * max_contacts,
        },
    }
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None

    def capacity_identity_only(request):
        harness.request_gate(request)
        capacity_identity_only.receipts.append({"capacity_verified": False})

    capacity_identity_only.receipts = []
    monkeypatch.setattr(
        flight_module, "default_phase_program", lambda _policy: harness.program
    )
    monkeypatch.setattr(
        preparation_fit,
        "build_native_contact_fit_gate",
        lambda *_args: capacity_identity_only,
    )
    try:
        rows, contacts, _kind, _dispatch, _phases = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id,
        )
    finally:
        closed = harness.close()

    # (1) The campaign ran BOTH rows, and neither row spent a revision.
    assert contacts == closed["request_count"] == 8  # 4 contacts each, no revision
    by_id = {row["sample_id"]: row for row in rows}
    assert set(by_id) == {E8C_ACCEPT_ID, E8C_ILLEGAL_ID}

    accepted_receipt = by_id[E8C_ACCEPT_ID]["native_episode_receipt"]
    assert accepted_receipt["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "ACCEPT"}
    ]
    assert "planner_action_illegal" not in accepted_receipt

    # (2) The illegal row's own disposition, with the token's sha256 and no
    # more than 32 characters of the token itself.
    digest = hashlib.sha256(E8C_ILLEGAL_TOKEN.encode("utf-8")).hexdigest()
    illegal_receipt = by_id[E8C_ILLEGAL_ID]["native_episode_receipt"]
    assert illegal_receipt["planner_routes"] == [
        {
            "role_visit_index": 3,
            "revision_count": 0,
            "action": E8C_ILLEGAL_TOKEN,
            "legal": False,
            "disposition": "planner_action_illegal",
            "action_sha256": digest,
            "action_chars": len(E8C_ILLEGAL_TOKEN),
        }
    ]
    assert illegal_receipt["planner_action_illegal"] == {
        "schema": "saea-native-planner-action-illegal-v1",
        "count": 1,
        "action_sha256": [digest],
    }
    # It still sealed through the ordinary explicit acceptance...
    assert ":solver:" in illegal_receipt["accepted_solver_receipt"]["final_contact"][
        "agent_contact_id"
    ]
    assert "terminal_disposition" not in illegal_receipt
    # ...and delivered the committed draft, unchanged.
    assert by_id[E8C_ILLEGAL_ID]["final_response_text"] == E8C_DRAFTS[E8C_ILLEGAL_ID]

    # (3) The seal is an ordinary row: same shape as the accepted one.
    runtime._output_rows = rows
    canonical = {row["sample_id"]: row for row in runtime._canonical_output_rows(harness.client)}
    assert set(canonical[E8C_ILLEGAL_ID]) == set(canonical[E8C_ACCEPT_ID])
    for sample_id, row in canonical.items():
        assert row["text"] == E8C_DRAFTS[sample_id]
        assert hashlib.sha256(row["text"].encode()).hexdigest() == row["response_text_sha256"]

    # (4) The bundle verifier accepts the sealed rows, against this run's trace.
    trace_records = {}
    for line in (
        (harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        document = json.loads(line)
        trace_records[document["record_id"]] = document["payload"]
    ordered = [canonical[E8C_ACCEPT_ID], canonical[E8C_ILLEGAL_ID]]
    raw = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered
    ).encode("utf-8")
    verified = _verify_outputs(
        raw,
        frozenset(canonical),
        ordered[0]["carrier_lock_key"],
        ordered[0]["arm"],
    )
    _verify_outputs_trace_binding(verified, trace_records)

    # (5) The registered SLURP official scorer scores the illegal row exactly
    # like any other: its DELIVERED text is the draft, so it reaches the
    # official prediction file and the per-sample table with no special case.
    gold = [
        _gold(E8C_ACCEPT_ID, "recommendation", "locations", (SlotEntity("place_name", "berlin"),)),
        _gold(E8C_ILLEGAL_ID, "alarm", "set", (SlotEntity("time", "seven"),)),
    ]
    monkeypatch.setattr(
        soe,
        "load_slurp_split",
        lambda lock, root, split_id, *, allow_heldout=False, allow_synthetic=False: gold,
    )
    monkeypatch.setattr(soe, "load_slurp_ontology", lambda lock, root: _FakeOntology(_PAIRING))
    monkeypatch.setattr(
        soe,
        "load_slurp_intent_slot_schema",
        lambda lock, root: _FakeSchema(
            {intent: _FakeIntentProfile(n) for intent, n in _PRIOR.items()}
        ),
    )
    monkeypatch.setattr(soe, "official_evaluator_root", lambda root: Path("unused"))
    captured: dict[str, object] = {}

    def _fake_run(gold_path, pred_path, *, evaluator_root, python_executable=None, average="micro"):
        captured["predictions"] = [
            json.loads(line)
            for line in Path(pred_path).read_text(encoding="utf-8").split("\n")
            if line.strip()
        ]
        return _official_result()

    monkeypatch.setattr(soe, "run_official_evaluate", _fake_run)
    outputs_path = tmp_path / "e8c.outputs.jsonl"
    outputs_path.write_bytes(raw)

    scored = SCORERS.resolve("slurp-slu-official-projected-v2")(outputs_path, {}, tmp_path)

    predictions = {row["file"]: row for row in captured["predictions"]}
    assert set(predictions) == {E8C_ACCEPT_ID, E8C_ILLEGAL_ID}
    assert (predictions[E8C_ILLEGAL_ID]["scenario"], predictions[E8C_ILLEGAL_ID]["action"]) == (
        "alarm",
        "set",
    )
    assert predictions[E8C_ILLEGAL_ID]["entities"] == [{"type": "time", "filler": "seven"}]
    per_sample = {row["sample_id"]: row for row in scored["per_sample"]}
    assert set(per_sample) == {E8C_ACCEPT_ID, E8C_ILLEGAL_ID}
    assert per_sample[E8C_ILLEGAL_ID]["scenario_action_exact"] == 1.0
    assert per_sample[E8C_ILLEGAL_ID]["projected"] is False


# ---------------------------------------------------------------------------
# E4 (owner decision 185): the identity-bound last mile -- the row's sealed
# ``saea-relisten-v1`` receipt (``AgentLoopResult.relisten``) survives BOTH
# outputs-row writers into the persisted outputs row, and the bundle
# verifier's I7l invariant accepts it against this run's own real trace.
# ---------------------------------------------------------------------------


def test_relisten_reaches_the_sealed_row_and_the_bundle_verifier_accepts(
    tmp_path, monkeypatch
):
    """Structurally ``test_grouped_solver_seals_a_row_the_bundle_verifier_
    accepts``'s own twin, for E4 instead of E2d: driven through the REAL
    ``FlightRuntime._dispatch_phase_program`` dispatch (never a hand-built
    row), so both outputs-row writers
    (``_rows_from_phase_summaries`` then ``_canonical_output_rows``) and the
    I7l bundle invariant are proved on one real sealed row, not three
    separate synthetic ones.
    """

    max_slots_per_row = 2
    max_contacts = 2 + rl.relisten_extra_ceiling(max_slots_per_row)
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0,
        max_contacts=max_contacts, planner_actions=(),
    )
    harness.config = _armed_config(max_slots_per_row=max_slots_per_row)
    harness.repo_root = RELISTEN_REPO_ROOT
    sample_id = harness.samples[0].sample_id
    harness._output = _two_entity_output(sample_id)
    _arm_relisten_request_gate(harness)

    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": 0,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                }
                for role in harness.config.roles
            },
            "relisten": json.loads(harness.config.relisten_json),
        },
        "native_contact_fit": {
            "run_id": "SAEA-NATIVE-RELISTEN-SEAL-FIT",
            "attempt_id": "attempt-native-relisten-seal-fit",
            "contact_cap": max_contacts,
        },
    }
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._repo_root = RELISTEN_REPO_ROOT
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
        "review_for_phase": None,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None
    monkeypatch.setattr(
        flight_module, "default_phase_program", lambda _policy: harness.program
    )

    def capacity_identity_only(request):
        harness.request_gate(request)
        capacity_identity_only.receipts.append({"capacity_verified": False})

    capacity_identity_only.receipts = []
    monkeypatch.setattr(
        preparation_fit,
        "build_native_contact_fit_gate",
        lambda *_args: capacity_identity_only,
    )
    try:
        rows, contacts, _kind, dispatch, _phases = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id,
        )
    finally:
        harness.close()

    # E4-1 registration fix: a relisten contact is dispatched OUTSIDE the
    # ACCEPT/REVISE/ACQUIRE graph (design section 6) and is never added to
    # ``result.contacts`` / ``native_episode_receipt.role_visits`` -- that is
    # unchanged. What IS fixed is every DERIVED count that used to read
    # ``result.contacts`` alone as "every contact this row spent": the
    # aggregate ``contacts`` this call returns, the row's own
    # ``contact_count`` field (checked below) and the flight's own
    # ``contacts_per_sample_observed`` budget accounting (also checked below)
    # now all include the row's own relisten spend (``FlightRuntime.
    # _result_contact_count``), so none of them undercounts a relisten-armed
    # row against its own ``contacts_per_sample_ceiling`` any more.
    assert contacts == max_contacts
    # Writer #1 (_rows_from_phase_summaries): the receipt is already on the
    # row this call returns.
    assert len(rows) == 1
    receipt = rows[0].get("relisten")
    assert receipt is not None
    assert receipt["schema"] == rl.RELISTEN_RECEIPT_SCHEMA
    assert receipt["triggered_count"] == 2
    assert receipt["contacts_used"] == 4
    # The row's own contact_count now counts the relisten spend too (E4-1
    # registration finding: 0/120 rows counted it before this fix).
    assert rows[0]["contact_count"] == max_contacts

    # The flight's own budget-accounting receipt: the per-sample "observed"
    # count the dispatch reports now matches this row's own real spend.
    observed = {row["sample_id"]: row["contacts"] for row in dispatch["contacts_per_sample_observed"]}
    assert observed == {sample_id: max_contacts}

    # Writer #2 (_canonical_output_rows): the SAME receipt survives, byte for
    # byte, into the row that actually gets sealed as outputs.jsonl.
    runtime._output_rows = rows
    canonical = runtime._canonical_output_rows(harness.client)
    assert len(canonical) == 1
    row = canonical[0]
    assert row["relisten"] == receipt
    # Shadow delivery: the delivered answer is never mutated by this stage.
    assert row["text"] == rows[0]["final_response_text"]

    # I7l: the bundle verifier's own trace-binding invariant accepts the
    # sealed row against this run's own real trace.
    trace_records = {}
    for line in (
        (harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ):
        document = json.loads(line)
        trace_records[document["record_id"]] = document["payload"]
    # The row's own relisten spend actually happened, as real, traced
    # contacts: 2 base (Perception, Solver) + 4 relisten (2 blind + 2
    # confirm) -- exactly ``max_contacts``, no slack, no overflow.
    assert sum(1 for record_id in trace_records if record_id.endswith("/request")) == max_contacts
    raw = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    verified = _verify_outputs(
        raw, frozenset({row["sample_id"]}), row["carrier_lock_key"], row["arm"],
    )
    _verify_outputs_trace_binding(verified, trace_records)

    # ...and refuses the same row once an accepted entity's blind value hash
    # is forged, with I7 alone (the row's own text/hash agreement) untouched.
    forged = copy.deepcopy(row)
    forged["relisten"]["entities"][0]["blind"]["value_sha256"] = "0" * 64
    forged_raw = (json.dumps(forged, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    verified_forged = _verify_outputs(
        forged_raw, frozenset({row["sample_id"]}), row["carrier_lock_key"], row["arm"],
    )
    with pytest.raises(BundleError, match="I7l"):
        _verify_outputs_trace_binding(verified_forged, trace_records)


def test_config_without_relisten_leaves_the_canonical_row_byte_identical(
    tmp_path, monkeypatch
):
    """Item 1's own regression guard on BOTH writers: an unarmed config's
    dispatch never adds a ``relisten`` key anywhere along the row's path --
    exactly what a config written before E4 already produced."""

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=2, planner_actions=(),
    )
    from test_native_episode_runner import _review_off_config

    harness.config = _review_off_config(max_contacts=2)
    sample_id = harness.samples[0].sample_id

    def output(key):
        _sample_id, phase, visit, _turn = key
        return (
            _two_entity_output(sample_id)(key)
            if phase == "solver"
            else f"{phase}-analysis:{_sample_id}:visit:{visit}"
        )

    harness._output = output

    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": 0,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                }
                for role in harness.config.roles
            },
        },
        "native_contact_fit": {
            "run_id": "SAEA-NATIVE-NO-RELISTEN-FIT",
            "attempt_id": "attempt-native-no-relisten-fit",
            "contact_cap": 2,
        },
    }
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._repo_root = RELISTEN_REPO_ROOT
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
        "review_for_phase": None,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None
    monkeypatch.setattr(
        flight_module, "default_phase_program", lambda _policy: harness.program
    )

    def capacity_identity_only(request):
        harness.request_gate(request)
        capacity_identity_only.receipts.append({"capacity_verified": False})

    capacity_identity_only.receipts = []
    monkeypatch.setattr(
        preparation_fit,
        "build_native_contact_fit_gate",
        lambda *_args: capacity_identity_only,
    )
    try:
        rows, contacts, _kind, _dispatch, _phases = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id,
        )
    finally:
        harness.close()

    assert contacts == 2
    assert "relisten" not in rows[0]
    runtime._output_rows = rows
    canonical = runtime._canonical_output_rows(harness.client)
    assert "relisten" not in canonical[0]
