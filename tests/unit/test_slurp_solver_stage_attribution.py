from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.native_episode_source import (
    VerifiedNativeEpisodeSource,
)
from speech_aware_evidence_acquisition.analysis.native_role_responses import (
    NativeRoleResponseSelectionError,
    select_verified_native_role_response,
)
from speech_aware_evidence_acquisition.analysis.slurp_solver_stage_attribution import (
    SlurpSolverStageAttributionError,
    build_slurp_solver_stage_attribution,
)
from speech_aware_evidence_acquisition.analysis import slurp_topn_diagnostics_cli
from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.core.delivery import native_abstention_records
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SlotEntity,
    parse_slu_response,
    score_slu,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _answer(scenario: str, action: str, *entities: tuple[str, str]) -> str:
    return json.dumps(
        {
            "scenario": scenario,
            "action": action,
            "entities": [
                {"type": entity_type, "filler": filler}
                for entity_type, filler in entities
            ],
        },
        sort_keys=True,
    )


def _source(rows: dict[str, list[str]]) -> VerifiedNativeEpisodeSource:
    phase_results = {}
    output_rows = {}
    trace = {}
    sample_ids = tuple(rows)
    for sample_id, visit_responses in rows.items():
        visits = []
        phase_contacts = []
        for visit_number, final_text in enumerate(visit_responses):
            contacts = []
            retry_texts = (
                ("this retry is not a SLURP object", final_text)
                if visit_number == 0 and sample_id.endswith(":save")
                else (final_text,)
            )
            for contact_number, text in enumerate(retry_texts):
                request_id = f"{sample_id}/solver/{visit_number}/{contact_number}"
                agent_contact_id = f"solver-{visit_number}-{contact_number}"
                request_sha256 = _sha(f"request:{request_id}")
                response_sha256 = _sha(f"wire:{request_id}:{text}")
                response_text_sha256 = _sha(text)
                contact = {
                    "agent_contact_id": agent_contact_id,
                    "request_id": request_id,
                    "request_sha256": request_sha256,
                    "response_sha256": response_sha256,
                    "response_text_sha256": response_text_sha256,
                }
                contacts.append(contact)
                trace[f"{request_id}/request"] = {
                    "payload": {
                        "request_id": request_id,
                        "sample_id": sample_id,
                        "decoding_params": {"max_tokens": 64},
                    },
                    "payload_sha256": request_sha256,
                }
                trace[f"{request_id}/response"] = {
                    "text": text,
                    "response_sha256": response_sha256,
                    "response_text_sha256": response_text_sha256,
                    "usage": {"completion_tokens": 8},
                }
                trace[f"{request_id}/native-role-contact"] = {
                    "use_role_id": "solver",
                    "use_agent_contact_id": agent_contact_id,
                    "use_request_sha256": request_sha256,
                    "use_response_sha256": response_sha256,
                    "use_response_text_sha256": response_text_sha256,
                }
                phase_contacts.append(
                    {
                        "plan": {"contact_id": agent_contact_id},
                        "response_sha256": response_text_sha256,
                    }
                )
            visits.append(
                {
                    "role_id": "solver",
                    "stage": "solver",
                    "execution_receipt": {
                        "contacts": contacts,
                        "final_contact": contacts[-1],
                    },
                }
            )
        final_receipt = visits[-1]["execution_receipt"]
        episode = {
            "role_visits": visits,
            "planner_routes": [],
            "accepted_solver_receipt": final_receipt,
        }
        final_text = visit_responses[-1]
        phase_results[sample_id] = {
            "sample_id": sample_id,
            "contacts": phase_contacts,
            "final_response_text": final_text,
            "final_response_sha256": _sha(final_text),
            "native_episode_receipt": episode,
        }
        output_rows[sample_id] = {
            "sample_id": sample_id,
            "text": final_text,
            "native_episode_receipt": episode,
        }

    split_hash = split_identity_hash(prefixed("slurp", sample_ids))
    return VerifiedNativeEpisodeSource(
        bundle=SimpleNamespace(
            trace_records=trace,
            split_ids=frozenset(sample_ids),
            manifest={"status": "COMPLETED"},
        ),
        composed=SimpleNamespace(config_hash="a" * 64, values={"policy": "native-test"}),
        plan=SimpleNamespace(
            carrier_lock_key="slurp",
            split_role="discovery",
            split_identity_hash=split_hash,
            run_id="run-test",
            attempt_id="attempt-test",
            protocol_hash="b" * 64,
        ),
        sample_ids=sample_ids,
        phase_results=phase_results,
        output_rows=output_rows,
        phase_artifact_sha256="c" * 64,
        diagnostics={"sample_count": len(sample_ids)},
    )


def _reference(sample_id: str) -> SlurpRecord:
    return SlurpRecord(
        sample_id=sample_id,
        utterance_id=sample_id,
        split="devel",
        media_relpath=f"{sample_id}.wav",
        audio_seconds=1.0,
        scenario="weather",
        action="query",
        intent="weather_query",
        entities=(SlotEntity("city", "paris"),),
    )


def _saved_row(reference: SlurpRecord, text: str) -> dict[str, object]:
    scenario, action, entities, parsed = parse_slu_response(text)
    row = score_slu(
        gold_scenario=reference.scenario,
        gold_action=reference.action,
        gold_entities=reference.entities,
        predicted_scenario=scenario,
        predicted_action=action,
        predicted_entities=entities,
    ).as_metrics_dict()
    return {"sample_id": reference.sample_id, "parsed": parsed, **row}


@pytest.fixture()
def attribution_fixture():
    save_id = "slurp:devel:save"
    harm_id = "slurp:devel:harm"
    empty_id = "slurp:devel:empty"
    correct = _answer("weather", "query", ("city", "paris"))
    wrong = _answer("calendar", "remove", ("date", "tomorrow"))
    source = _source(
        {
            save_id: [wrong, correct],
            harm_id: [correct, wrong],
            empty_id: [""],
        }
    )
    references = tuple(_reference(sample_id) for sample_id in source.sample_ids)
    official_rows = tuple(
        _saved_row(reference, source.output_rows[reference.sample_id]["text"])
        for reference in references
    )
    return source, references, official_rows


def test_attributes_saves_harms_parse_and_actual_solver_revisions(attribution_fixture):
    source, references, official_rows = attribution_fixture

    report = build_slurp_solver_stage_attribution(
        source,
        reference_records=references,
        official_final_rows=official_rows,
        reference_binding_sha256="d" * 64,
        official_score_result_sha256="e" * 64,
    )

    assert report["aggregate"]["intent_exact"] == {
        "n": 3,
        "draft_correct": 1,
        "final_correct": 1,
        "saves": 1,
        "harms": 1,
        "stable_correct": 0,
        "stable_wrong": 1,
        "unavailable": 0,
        "net": 0,
    }
    assert report["aggregate"]["entity_exact"]["saves"] == 1
    assert report["aggregate"]["entity_exact"]["harms"] == 1
    assert report["aggregate"]["full_exact"]["saves"] == 1
    assert report["aggregate"]["full_exact"]["harms"] == 1
    assert report["aggregate"]["parse"] == {
        "draft_parsed": 2,
        "final_parsed": 2,
        "draft_unparsed": 1,
        "draft_unavailable": 0,
        "final_unparsed": 1,
    }
    assert report["aggregate"]["solver_revision"] == {
        "attempted": 2,
        "not_attempted": 1,
        "completed": 2,
        "not_completed": 1,
        "delivered": 2,
        "not_delivered": 1,
        "delivery_unavailable": 0,
        "response_changed": 2,
    }
    by_id = {row["sample_id"]: row for row in report["samples"]}
    save = by_id["slurp:devel:save"]
    assert save["transitions"] == {
        "intent_exact": "save",
        "entity_exact": "save",
        "full_exact": "save",
    }
    assert save["revision"]["attempted_solver_revision"] is True
    assert save["revision"]["completed_solver_revision"] is True
    assert save["revision"]["delivered_solver_revision"] is True
    assert save["source"]["initial_solver"]["request_id"].endswith("/0/1")
    assert save["source"]["final_delivery"]["request_id"].endswith("/1/0")
    assert "response_text" not in save["source"]["initial_solver"]
    assert report["semantics"]["official_micro_f1_recomputed"] is False


def test_shared_selector_uses_final_retry_and_fails_closed_on_trace_drift():
    sample_id = "slurp:devel:save"
    source = _source(
        {sample_id: [_answer("wrong", "wrong"), _answer("weather", "query")]}
    )

    selection = select_verified_native_role_response(
        source, sample_id=sample_id, role_id="solver", visit_index=0
    )

    assert selection.status == "completed"
    assert selection.contact_index == 1
    assert selection.response_text == _answer("wrong", "wrong")
    assert selection.request_id.endswith("/0/1")
    source.bundle.trace_records[f"{selection.request_id}/response"][
        "response_text_sha256"
    ] = "0" * 64
    with pytest.raises(NativeRoleResponseSelectionError, match="differs from receipt/trace"):
        select_verified_native_role_response(
            source, sample_id=sample_id, role_id="solver", visit_index=0
        )


def test_shared_selector_reports_missing_and_finite_without_substituting_text():
    source = _source({"slurp:devel:only": [_answer("weather", "query")]})
    missing = select_verified_native_role_response(
        source, sample_id="slurp:devel:only", role_id="reviewer"
    )
    assert missing.status == "missing"
    assert missing.response_text is None

    finite_source = copy.deepcopy(source)
    sample_id = finite_source.sample_ids[0]
    episode = finite_source.phase_results[sample_id]["native_episode_receipt"]
    visit = episode["role_visits"].pop()
    episode.pop("accepted_solver_receipt")
    episode["interrupted_role"] = visit
    episode["terminal_disposition"] = {
        "reason": "finite_completion",
        "finish_reason": "length",
        "role_id": "solver",
        "stage": "solver",
        "revision_count": 0,
        "planner_accepted": False,
        "rejected_contact": visit["execution_receipt"]["final_contact"],
    }
    episode["abstention_receipt"] = {
        "source_contact": visit["execution_receipt"]["final_contact"]
    }
    finite = select_verified_native_role_response(
        finite_source, sample_id=sample_id, role_id="solver"
    )
    assert finite.status == "finite"
    assert finite.visit_index is None
    assert finite.response_text == _answer("weather", "query")


@pytest.mark.parametrize("which", ("reference", "official", "source"))
def test_exact_full_roster_is_required(attribution_fixture, which):
    source, references, official_rows = attribution_fixture
    if which == "reference":
        references = references[:-1]
    elif which == "official":
        official_rows = official_rows[::-1]
    else:
        source = replace(source, output_rows=dict(list(source.output_rows.items())[:-1]))
    with pytest.raises(SlurpSolverStageAttributionError, match="exact ordered roster"):
        build_slurp_solver_stage_attribution(
            source,
            reference_records=references,
            official_final_rows=official_rows,
            reference_binding_sha256="d" * 64,
            official_score_result_sha256="e" * 64,
        )


def test_saved_final_fields_must_match_deterministic_final_parse(attribution_fixture):
    source, references, official_rows = attribution_fixture
    official_rows = list(copy.deepcopy(official_rows))
    official_rows[0]["scenario_action_exact"] = 0.0
    with pytest.raises(SlurpSolverStageAttributionError, match="saved final score"):
        build_slurp_solver_stage_attribution(
            source,
            reference_records=references,
            official_final_rows=official_rows,
            reference_binding_sha256="d" * 64,
            official_score_result_sha256="e" * 64,
        )


def test_existing_verified_reference_join_exposes_full_offline_records(
    tmp_path, monkeypatch
):
    ids = ("slurp:devel:two", "slurp:devel:one")
    records = tuple(_reference(sample_id) for sample_id in reversed(ids))
    lock_path = tmp_path / "datasets.lock.json"
    lock_path.write_text("{}", encoding="utf-8")
    lock_sha256 = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    monkeypatch.setattr(slurp_topn_diagnostics_cli, "load_lock", lambda _path: {})

    loaded = slurp_topn_diagnostics_cli.load_verified_slurp_reference_records(
        {
            "kind": "slurp-split",
            "split_id": "devel",
            "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
            "loaded_split_identity_hash": split_identity_hash(
                prefixed("slurp", tuple(record.sample_id for record in records))
            ),
            "lock": {"path": str(lock_path), "sha256": lock_sha256},
            "data_root": str(tmp_path),
        },
        ids,
        loader=lambda *_args, **_kwargs: records,
    )

    assert tuple(record.sample_id for record in loaded) == ids
    assert loaded[0].entities == (SlotEntity("city", "paris"),)


def test_finite_delivery_retains_last_completed_solver_without_fake_revision():
    sample_id = "slurp:devel:finite"
    correct = _answer("weather", "query", ("city", "paris"))
    source = _source({sample_id: [correct]})
    episode = source.phase_results[sample_id]["native_episode_receipt"]
    solver_receipt = episode.pop("accepted_solver_receipt")
    request_id = f"{sample_id}/reviewer/interrupted"
    contact = {
        "agent_contact_id": "reviewer-interrupted",
        "request_id": request_id,
        "request_sha256": _sha(f"request:{request_id}"),
        "response_sha256": _sha(f"wire:{request_id}:partial"),
        "response_text_sha256": _sha("partial"),
    }
    source.bundle.trace_records[f"{request_id}/request"] = {
        "payload": {"request_id": request_id, "sample_id": sample_id},
        "payload_sha256": contact["request_sha256"],
    }
    source.bundle.trace_records[f"{request_id}/response"] = {
        "text": "partial",
        "response_sha256": contact["response_sha256"],
        "response_text_sha256": contact["response_text_sha256"],
    }
    source.bundle.trace_records[f"{request_id}/native-role-contact"] = {
        "use_role_id": "reviewer",
        "use_agent_contact_id": contact["agent_contact_id"],
        "use_request_sha256": contact["request_sha256"],
        "use_response_sha256": contact["response_sha256"],
        "use_response_text_sha256": contact["response_text_sha256"],
    }
    source.phase_results[sample_id]["contacts"].append(
        {
            "plan": {"contact_id": contact["agent_contact_id"]},
            "response_sha256": contact["response_text_sha256"],
        }
    )
    episode["terminal_solver_receipt"] = solver_receipt
    episode["interrupted_role"] = {
        "role_id": "reviewer",
        "stage": "review",
        "execution_receipt": {"contacts": [contact], "final_contact": contact},
    }
    episode["terminal_disposition"] = {
        "reason": "finite_completion",
        "finish_reason": "length",
        "role_id": "reviewer",
        "stage": "review",
        "revision_count": 0,
        "planner_accepted": False,
        "rejected_contact": contact,
    }
    reference = _reference(sample_id)

    report = build_slurp_solver_stage_attribution(
        source,
        reference_records=(reference,),
        official_final_rows=(_saved_row(reference, correct),),
        reference_binding_sha256="d" * 64,
        official_score_result_sha256="e" * 64,
    )

    row = report["samples"][0]
    assert row["source"]["final_delivery"]["delivery_kind"] == "finite"
    assert row["revision"] == {
        "solver_attempt_count": 1,
        "completed_solver_visits": 1,
        "attempted_solver_revision": False,
        "completed_solver_revision": False,
        "delivered_solver_revision": False,
        "response_changed": False,
    }


def test_pre_solver_finite_abstention_keeps_full_row_with_unavailable_draft():
    sample_id = "slurp:devel:abstain"
    source = _source({sample_id: [_answer("weather", "query")]})
    episode = source.phase_results[sample_id]["native_episode_receipt"]
    interrupted = episode["role_visits"].pop()
    rejected = interrupted["execution_receipt"]["final_contact"]
    episode.pop("accepted_solver_receipt")
    episode["interrupted_role"] = interrupted
    episode["terminal_disposition"] = {
        "reason": "finite_completion",
        "finish_reason": "length",
        "role_id": "solver",
        "stage": "solver",
        "revision_count": 0,
        "planner_accepted": False,
        "rejected_contact": rejected,
    }
    episode["abstention_receipt"] = {"source_contact": rejected}
    derived_id, request_document, response_document = native_abstention_records(
        sample_id=sample_id,
        source_contact=rejected,
        finish_reason="length",
    )
    source.phase_results[sample_id]["final_response_text"] = ""
    source.phase_results[sample_id]["final_response_sha256"] = _sha("")
    source.output_rows[sample_id].update(
        text="",
        request_id=derived_id,
        request_sha256=request_document["payload_sha256"],
        response_sha256=response_document["response_sha256"],
        response_text_sha256=response_document["response_text_sha256"],
    )
    reference = _reference(sample_id)

    report = build_slurp_solver_stage_attribution(
        source,
        reference_records=(reference,),
        official_final_rows=(_saved_row(reference, ""),),
        reference_binding_sha256="d" * 64,
        official_score_result_sha256="e" * 64,
    )

    row = report["samples"][0]
    assert row["source"]["initial_solver"] == {"status": "missing"}
    assert row["source"]["final_delivery"]["delivery_kind"] == "abstention"
    assert row["transitions"] == {
        "intent_exact": "unavailable",
        "entity_exact": "unavailable",
        "full_exact": "unavailable",
    }
    assert row["revision"]["attempted_solver_revision"] is False
    assert row["revision"]["completed_solver_revision"] is False
    assert row["revision"]["delivered_solver_revision"] is None


def test_truncated_later_solver_is_attempted_but_not_completed_or_delivered():
    sample_id = "slurp:devel:truncated-revision"
    correct = _answer("weather", "query", ("city", "paris"))
    wrong = _answer("calendar", "remove", ("date", "tomorrow"))
    source = _source({sample_id: [correct, wrong]})
    episode = source.phase_results[sample_id]["native_episode_receipt"]
    interrupted = episode["role_visits"].pop()
    rejected = interrupted["execution_receipt"]["final_contact"]
    episode.pop("accepted_solver_receipt")
    episode["terminal_solver_receipt"] = episode["role_visits"][0][
        "execution_receipt"
    ]
    episode["interrupted_role"] = interrupted
    episode["terminal_disposition"] = {
        "reason": "finite_completion",
        "finish_reason": "length",
        "role_id": "solver",
        "stage": "solver",
        "revision_count": 1,
        "planner_accepted": False,
        "rejected_contact": rejected,
    }
    source.phase_results[sample_id]["final_response_text"] = correct
    source.phase_results[sample_id]["final_response_sha256"] = _sha(correct)
    source.output_rows[sample_id]["text"] = correct
    reference = _reference(sample_id)

    report = build_slurp_solver_stage_attribution(
        source,
        reference_records=(reference,),
        official_final_rows=(_saved_row(reference, correct),),
        reference_binding_sha256="d" * 64,
        official_score_result_sha256="e" * 64,
    )

    row = report["samples"][0]
    assert row["source"]["final_delivery"]["delivery_kind"] == "finite"
    assert row["revision"] == {
        "solver_attempt_count": 2,
        "completed_solver_visits": 1,
        "attempted_solver_revision": True,
        "completed_solver_revision": False,
        "delivered_solver_revision": False,
        "response_changed": False,
    }


@pytest.mark.parametrize(
    ("references", "official"),
    [((object(),), ({"sample_id": "slurp:devel:only"},)),
     ((_reference("slurp:devel:only"),), ("not-a-row",))],
)
def test_malformed_roster_members_raise_attribution_error(references, official):
    source = _source({"slurp:devel:only": [""]})
    with pytest.raises(SlurpSolverStageAttributionError, match="exact ordered roster"):
        build_slurp_solver_stage_attribution(
            source,
            reference_records=references,
            official_final_rows=official,
            reference_binding_sha256="d" * 64,
            official_score_result_sha256="e" * 64,
        )


def _normalised_source(monkeypatch):
    from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
    from speech_aware_evidence_acquisition.rails.delivery_normalisers import SlurpProjectionV3DeliveryNormaliser
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import legal_intent_inventory
    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: legal_intent_inventory({"weather": ("query",)}))
    sid = "slurp:devel:normalised"
    raw = _answer("weather", "query", ("city", "PARIS"))
    result = SlurpProjectionV3DeliveryNormaliser()(raw)
    assert result.text != raw
    source = _source({sid: [raw]})
    phase = source.phase_results[sid]
    phase["native_episode_receipt"]["deliver_normaliser"] = dict(result.receipt)
    phase["final_response_text"] = result.text
    phase["final_response_sha256"] = _sha(result.text)
    source.output_rows[sid].update(text=result.text, carrier_lock_key="slurp")
    return source, _reference(sid)


def test_registered_postprocessing_has_separate_custody_and_effect(monkeypatch):
    source, ref = _normalised_source(monkeypatch)
    report = build_slurp_solver_stage_attribution(
        source, reference_records=[ref],
        official_final_rows=[_saved_row(ref, source.output_rows[ref.sample_id]["text"])],
        reference_binding_sha256="d" * 64, official_score_result_sha256="e" * 64,
    )
    row = report["samples"][0]
    assert row["revision"]["completed_solver_revision"] is False
    assert row["metrics"]["pre_delivery"]["entity_exact"] == 0
    assert row["metrics"]["final"]["entity_exact"] == 1
    assert row["postprocessing_transitions"]["entity_exact"] == "save"
    assert row["source"]["final_delivery"]["normalisation"]["normaliser_id"] == "saea-deliver-normalise-v3"


@pytest.mark.parametrize("mutation", ["missing", "input", "output", "carrier", "rule", "text"])
def test_postprocessing_does_not_relax_custody(monkeypatch, mutation):
    source, ref = _normalised_source(monkeypatch)
    episode = source.phase_results[ref.sample_id]["native_episode_receipt"]
    block = episode["deliver_normaliser"]
    if mutation == "missing":
        del episode["deliver_normaliser"]
    elif mutation == "text":
        source.output_rows[ref.sample_id]["text"] = _answer("weather", "query")
    else:
        field = {"input": "input_sha256", "output": "output_sha256", "carrier": "carrier_lock_key", "rule": "normaliser_id"}[mutation]
        block[field] = "0" * 64
    with pytest.raises(SlurpSolverStageAttributionError):
        build_slurp_solver_stage_attribution(
            source, reference_records=[ref],
            official_final_rows=[_saved_row(ref, source.output_rows[ref.sample_id]["text"])],
            reference_binding_sha256="d" * 64, official_score_result_sha256="e" * 64,
        )
