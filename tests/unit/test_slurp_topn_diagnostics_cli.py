from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli import (
    SlurpTopNAnalysisError,
    _branch_rows,
    _entity_correctness_from_verified_receipt,
    _entity_correctness_from_verified_score_document,
    _raw_aggregate,
    _raw_source_rows,
    _references,
    _observed_width_reports,
    _raw_delivery_diagnostic_report,
    _raw_delivery_reports_by_branch_and_width,
    _select_source_binding,
    _source_rows,
    run_raw_source,
)
from speech_aware_evidence_acquisition.contracts import TraceRecord
from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics import (
    BranchOutcomeRow,
    ReferenceIntentRow,
    SourceCandidateRow,
)
from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical
from speech_aware_evidence_acquisition.core.bundle.raw_contact_source import verify_aborted_contact_source, _transport_response_sha256
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.artifact_results import (
    canonical_sha256,
)


def _state(sample_id: str, candidates: tuple[str, ...]) -> AgentStateArtifact:
    content = json.dumps(
        {
            "schema": "saea-slurp-intent-hypotheses-v1",
            "semantics": "ranked-mutually-exclusive-intent-alternatives",
            "sample_id": sample_id,
            "candidates": [
                {
                    "intent_id": item,
                    "distinction": "synthetic distinction",
                    "evidence_refs": [],
                    "unresolved_fields": [],
                }
                for item in candidates
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return AgentStateArtifact(
        state_id="phase:hypotheses:" + sample_id,
        state_kind="phase:hypotheses",
        content=content,
        source_query_state_sha256="a" * 64,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="phase-intent-hypotheses-only-v1",
        cited_value_ids=(),
    ).validate()


def _source_fixture(tmp_path: Path):
    ids = ("s1", "s2")
    catalog = {
        "schema": "saea-slurp-candidate-contract-catalog-v1",
        "profiles": [{"candidate_id": "a"}, {"candidate_id": "b"}, {"candidate_id": "c"}],
    }
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    catalog_pin = {
        "data_relpath": "catalog.json",
        "sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "source_sha256": canonical_sha256(catalog),
    }
    manifest_path = tmp_path / "source.manifest"
    manifest_path.write_text("synthetic", encoding="utf-8")
    manifest = {
        "status": "COMPLETED",
        "artifact_result": {
            "schema": "saea-artifact-result-binding-v2",
            "role": "slurp-intent-hypotheses",
            "content_contract": {
                "id": "slurp-intent-hypotheses-v1",
                "min_candidates": 3,
                "max_candidates": 3,
                "source_catalog": catalog_pin,
            }
        },
        "artifact_content_source": {"path": str(tmp_path / "artifact-source")},
    }
    (tmp_path / "artifact-source").write_text("", encoding="utf-8")
    bundle = SimpleNamespace(
        manifest=manifest, split_ids=frozenset(ids), attempt_state="FINALIZED"
    )
    states = {sample_id: _state(sample_id, ("a", "b", "c")) for sample_id in ids}
    binding = {
        "manifest": {
            "path": str(manifest_path),
            "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        },
        "candidate_contract_source_sha256": catalog_pin["source_sha256"],
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
        "candidate_count": 3,
    }
    return ids, binding, bundle, states


def test_source_reader_reuses_typed_artifact_and_preserves_order(tmp_path):
    ids, binding, bundle, states = _source_fixture(tmp_path)

    def state_loader(*_args, **_kwargs):
        return states

    rows, _manifest, returned = _source_rows(
        binding, bundle, ids, state_loader=state_loader
    )

    assert tuple(row.sample_id for row in rows) == ids
    assert rows[0].candidate_ids == ("a", "b", "c")
    assert returned is states


def test_branch_reader_requires_common_state_and_delivery_hashes(tmp_path):
    ids, binding, bundle, states = _source_fixture(tmp_path)
    source_path = Path(binding["manifest"]["path"])
    text = '{"scenario":"a","action":"x","entities":[]}'
    delivery_sha = hashlib.sha256(text.encode()).hexdigest()
    branch = SimpleNamespace(
        manifest={"schema": "saea-derived-delivery-v1", "phase_sources": [
            {
                "sample_id": sample_id,
                "predecessor_manifest": {
                    "path": str(source_path), "sha256": binding["manifest"]["sha256"]
                },
                "sealed_state_sha256": states[sample_id].content_hash(),
                "delivered_text_sha256": delivery_sha,
                "refusal_reason": None,
            }
            for sample_id in ids
        ]},
        attempt_state="DERIVED",
        outputs_rows=[
            {"sample_id": sample_id, "text": text, "delivery_text_sha256": delivery_sha}
            for sample_id in ids
        ],
    )

    rows = _branch_rows(
        "joint", branch, source_path, binding["manifest"]["sha256"], states, ids,
        {"s1": True, "s2": False},
    )

    assert rows[0].final_intent_id == "a_x"
    assert rows[0].refused is False
    assert rows[0].entity_correct is True
    assert rows[1].entity_correct is False

    branch.manifest["phase_sources"][1]["sealed_state_sha256"] = "f" * 64
    with pytest.raises(SlurpTopNAnalysisError, match="state binding"):
        _branch_rows(
            "joint", branch, source_path, binding["manifest"]["sha256"], states, ids
        )


def test_branch_reader_exposes_raw_outside_shortlist_flag_for_empty_delivery(tmp_path):
    ids, binding, bundle, states = _source_fixture(tmp_path)
    source_path = Path(binding["manifest"]["path"])
    branch = SimpleNamespace(
        manifest={"schema": "saea-derived-delivery-v1", "phase_sources": [
            {
                "sample_id": sample_id,
                "predecessor_manifest": {
                    "path": str(source_path), "sha256": binding["manifest"]["sha256"]
                },
                "sealed_state_sha256": states[sample_id].content_hash(),
                "delivered_text_sha256": hashlib.sha256(b"").hexdigest(),
                "refusal_reason": "final_intent_outside_shortlist" if sample_id == "s1" else None,
                "delivery_diagnostics": {
                    "final_intent_outside_shortlist": 1 if sample_id == "s1" else 0,
                    "final_authoritative": 0 if sample_id == "s1" else 1,
                },
            }
            for sample_id in ids
        ]},
        attempt_state="DERIVED",
        outputs_rows=[
            {
                "sample_id": sample_id, "text": "",
                "delivery_text_sha256": hashlib.sha256(b"").hexdigest(),
            }
            for sample_id in ids
        ],
    )
    captured = {}
    _branch_rows(
        "joint", branch, source_path, binding["manifest"]["sha256"], states, ids,
        delivery_diagnostics=captured,
    )
    report = _raw_delivery_diagnostic_report(captured, ids)
    assert report["diagnostics_available"] is True
    assert report["flag_row_counts"]["final_intent_outside_shortlist"] == 1
    assert report["refused_count"] == 1
    assert report["refusal_reason_counts"] == {"final_intent_outside_shortlist": 1}


@pytest.mark.parametrize(
    "rows,ids,match",
    [
        ({"s1": []}, ("s1",), "row malformed"),
        ({"s1": {"flags": "bad"}}, ("s1",), "flags malformed"),
        ({"s1": {"flags": {1: 1}}}, ("s1",), "flag key malformed"),
        ({"s1": {"flags": {"outside": -1}}}, ("s1",), "flag value malformed"),
        ({"s1": {"flags": {}, "refusal_reason": 1}}, ("s1",), "refusal reason malformed"),
    ],
)
def test_raw_delivery_report_rejects_malformed_verified_rows(rows, ids, match):
    with pytest.raises(SlurpTopNAnalysisError, match=match):
        _raw_delivery_diagnostic_report(rows, ids)


def test_raw_delivery_report_rejects_duplicate_or_missing_roster():
    row = {"s1": {"flags": {}, "refusal_reason": None}}
    with pytest.raises(SlurpTopNAnalysisError, match="duplicates"):
        _raw_delivery_diagnostic_report(row, ("s1", "s1"))
    with pytest.raises(SlurpTopNAnalysisError, match="roster"):
        _raw_delivery_diagnostic_report(row, ("s1", "s2"))


def test_raw_delivery_reports_are_grouped_by_width_and_missing_flags_stay_unavailable():
    source_rows = (
        SourceCandidateRow("s1", ("a",)),
        SourceCandidateRow("s2", ("a", "b")),
        SourceCandidateRow("s3", ("a", "b", "c")),
    )
    delivery = {
        "hard": {
            "s1": {"flags": {"outside": 0}, "refusal_reason": None},
            "s2": {"flags": None, "refusal_reason": None},
            "s3": {"flags": {"outside": 1}, "refusal_reason": "outside"},
        },
        "joint": {
            "s1": {"flags": {"outside": 1}, "refusal_reason": "outside"},
            "s2": {"flags": {"outside": 0}, "refusal_reason": None},
            "s3": {"flags": {"outside": 0}, "refusal_reason": None},
        },
    }
    reports = _raw_delivery_reports_by_branch_and_width(
        source_rows, delivery, {"s1", "s2", "s3"}
    )
    assert set(reports) == {"1", "2", "3"}
    assert reports["1"]["hard"]["diagnostics_available"] is True
    assert reports["2"]["hard"]["diagnostics_available"] is False
    assert reports["3"]["hard"]["flag_row_counts"]["outside"] == 1
    assert reports["1"]["joint"]["refused_count"] == 1


def test_branch_reader_rejects_malformed_raw_delivery_diagnostics(tmp_path):
    ids, binding, bundle, states = _source_fixture(tmp_path)
    source_path = Path(binding["manifest"]["path"])
    text = '{"scenario":"a","action":"x","entities":[]}'
    delivery_sha = hashlib.sha256(text.encode()).hexdigest()
    branch = SimpleNamespace(
        manifest={"schema": "saea-derived-delivery-v1", "phase_sources": [
            {
                "sample_id": sample_id,
                "predecessor_manifest": {
                    "path": str(source_path), "sha256": binding["manifest"]["sha256"]
                },
                "sealed_state_sha256": states[sample_id].content_hash(),
                "delivered_text_sha256": delivery_sha,
                "refusal_reason": None,
                "delivery_diagnostics": "malformed",
            }
            for sample_id in ids
        ]},
        attempt_state="DERIVED",
        outputs_rows=[
            {"sample_id": sample_id, "text": text, "delivery_text_sha256": delivery_sha}
            for sample_id in ids
        ],
    )
    with pytest.raises(SlurpTopNAnalysisError, match="diagnostics malformed"):
        _branch_rows(
            "joint", branch, source_path, binding["manifest"]["sha256"], states, ids
        )


def test_reference_reader_uses_pinned_split_adapter_and_refuses_foreign_roster(tmp_path):
    ids = ("s1", "s2")
    lock_path = tmp_path / "lock.json"
    lock_path.write_text("{}", encoding="utf-8")
    records = [SimpleNamespace(sample_id=item, intent="a") for item in ids]
    binding = {
        "kind": "slurp-split",
        "split_id": "devel",
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
        "lock": {
            "path": str(lock_path),
            "sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        },
        "data_root": str(tmp_path),
    }

    seen = {}

    def loader(lock, root, split_id, **kwargs):
        seen.update({"lock": lock, "root": root, "split_id": split_id, **kwargs})
        return records

    refs = _references(binding, ids, loader=loader)
    assert [row.intent_id for row in refs] == ["a", "a"]
    assert seen["split_id"] == "devel"

    with pytest.raises(SlurpTopNAnalysisError, match="roster"):
        _references(binding, ("s1", "foreign"), loader=loader)


def test_run_is_config_driven_and_score_gate_precedes_semantic_reads(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli as cli

    ids, source_binding, source_bundle, states = _source_fixture(tmp_path)
    source_path = Path(source_binding["manifest"]["path"])
    text = '{"scenario":"a","action":"x","entities":[]}'
    delivery_sha = hashlib.sha256(text.encode()).hexdigest()
    branch_path = tmp_path / "branch.manifest"
    branch_path.write_text("branch", encoding="utf-8")
    branch_bundle = SimpleNamespace(
        manifest={
            "schema": "saea-derived-delivery-v1",
            "phase_sources": [
                {
                    "sample_id": sample_id,
                    "predecessor_manifest": {
                        "path": str(source_path),
                        "sha256": source_binding["manifest"]["sha256"],
                    },
                    "sealed_state_sha256": states[sample_id].content_hash(),
                    "delivered_text_sha256": delivery_sha,
                    "refusal_reason": None,
                }
                for sample_id in ids
            ],
        },
        attempt_state="DERIVED",
        outputs_rows=[
            {
                "sample_id": sample_id,
                "text": text,
                "delivery_text_sha256": delivery_sha,
            }
            for sample_id in ids
        ],
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text("receipt", encoding="utf-8")
    receipt_pin = {
        "path": str(receipt_path),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "cell_id": "cell",
    }
    roster_pin = {"path": str(tmp_path / "unused"), "sha256": "0" * 64}
    config = {
        "experiment_id": "synthetic",
        "execution_profile": "model-free-check",
        "analysis": {
            "full_roster": roster_pin,
            "roster": roster_pin,
            "metadata": roster_pin,
            "source_diagnostics": {
                "shared_fixed_top3_source": source_binding,
                "reference_source": {
                    "kind": "slurp-split",
                    "split_id": "devel",
                    "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
                    "lock": {"path": str(tmp_path / "lock"), "sha256": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"},
                    "data_root": str(tmp_path),
                },
            },
            "inputs": {
                "joint": {
                    "manifest": {
                        "path": str(branch_path),
                        "sha256": hashlib.sha256(branch_path.read_bytes()).hexdigest(),
                    },
                    "score_receipt": receipt_pin,
                }
            },
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "out.json"
    (tmp_path / "lock").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(cli, "_roster_ids", lambda _value, label: ids if label.endswith("full_roster") else (ids[0],))
    monkeypatch.setattr(
        cli, "_metadata", lambda *_args: {sample_id: {"scenario": "demo"} for sample_id in ids}
    )

    def verifier(path):
        return source_bundle if Path(path) == source_path else branch_bundle

    calls = []

    def score_verifier(_ref, _bundle):
        calls.append("score")
        return {"verified": True}

    def references(*_args, **_kwargs):
        calls.append("references")
        return [SimpleNamespace(sample_id=item, intent="a") for item in ids]

    result = cli.run(
        config_path,
        output,
        bundle_verifier=verifier,
        score_receipt_verifier=score_verifier,
        reference_loader=references,
        state_loader=lambda *_args, **_kwargs: states,
    )

    assert result["populations"] == {"NEW500": 1, "DEV1000": 2, "OLD500": 1}
    assert calls == ["score", "references"]
    assert result["diagnostics"]["DEV1000"]["source"]["topn_included"] == 2
    assert "by_observed_distinct_width" not in result["diagnostics"]["DEV1000"]

    distinct_source = dict(source_binding)
    distinct_source["candidate_count_range"] = [1, 3]
    config["analysis"]["source_diagnostics"] = {
        **config["analysis"]["source_diagnostics"],
        "shared_distinct_source": distinct_source,
    }
    del config["analysis"]["source_diagnostics"]["shared_fixed_top3_source"]
    config_path.write_text(json.dumps(config), encoding="utf-8")
    distinct_result = cli.run(
        config_path,
        tmp_path / "distinct-out.json",
        bundle_verifier=verifier,
        score_receipt_verifier=score_verifier,
        reference_loader=references,
        state_loader=lambda *_args, **_kwargs: states,
    )
    assert distinct_result["source"]["binding_name"] == "shared_distinct_source"
    assert set(distinct_result["diagnostics"]["DEV1000"]["by_observed_distinct_width"]) == {"3"}
    assert distinct_result["diagnostics"]["DEV1000"]["branches"]["joint"][
        "entity_unavailable"
    ] == 2
    assert distinct_result["diagnostics"]["DEV1000"]["raw_delivery_diagnostics"][
        "joint"
    ]["diagnostics_available"] is False
    assert distinct_result["diagnostic_semantics"]["branches.*.out_of_shortlist_attempts"].startswith(
        "delivered_projection_only"
    )


def _raw_trace_fixture(tmp_path: Path, *, finish_reason: str = "stop"):
    ids = ("s1", "s2")
    proposals = {
        "s1": ("a", "a", "b"),
        "s2": ("b", "b", "a"),
    }
    documents = []
    payloads = {}
    for sample_id in ids:
        request_id = f"request-{sample_id}"
        request_payload = {"request_id": request_id, "sample_id": sample_id, "arm": "raw"}
        request = {
            "arm": "raw",
            "payload": request_payload,
            "payload_sha256": hashlib.sha256(canonical(request_payload)).hexdigest(),
        }
        candidate_rows = [
            {
                "intent_id": intent_id,
                "distinction": "synthetic",
                "evidence_refs": [],
                "unresolved_fields": [],
            }
            for intent_id in proposals[sample_id]
        ]
        text = json.dumps({"candidates": candidate_rows}, sort_keys=True, separators=(",", ":"))
        raw_wire = json.dumps(
            {
                "choices": [
                    {"finish_reason": finish_reason, "message": {"content": text}}
                ],
                "usage": {"completion_tokens": 1},
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        response = {
            "response_sha256": "",
            "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "text": text,
            "usage": {"completion_tokens": 1},
        }
        wire = {
            "request_id": request_id,
            "sample_id": sample_id,
            "response_b64": __import__("base64").b64encode(raw_wire).decode("ascii"),
            "response_sha256": hashlib.sha256(raw_wire).hexdigest(),
            "finish_reason": finish_reason,
        }
        response["response_sha256"] = _transport_response_sha256(
            raw_wire,
            expected_text=text,
            expected_usage=response["usage"],
            expected_finish_reason=finish_reason,
        )
        cost = {"request_id": request_id, "calls": 1, "audio_seconds": 1.0}
        for channel, suffix, payload in (
            ("MODEL_REQUEST", "/request", request),
            ("MODEL_RESPONSE", "/response", response),
            ("MODEL_WIRE_RESPONSE", "/wire-response", wire),
            ("COST", "/cost", cost),
        ):
            record_id = request_id + suffix
            TraceRecord(channel, record_id, payload).validate()
            documents.append(
                {
                    "channel": channel,
                    "record_id": record_id,
                    "payload": payload,
                }
            )
            payloads[record_id] = payload
    trace_path = tmp_path / "raw-trace.jsonl"
    trace_path.write_text(
        "".join(json.dumps(document) + "\n" for document in documents), encoding="utf-8"
    )
    return ids, proposals, trace_path


def _raw_kwargs(ids, trace_path):
    return dict(
        expected_ids=ids, legal_intent_ids=frozenset({"a", "b"}),
        max_candidates=3, expected_contacts=len(ids), expected_audio_seconds=float(len(ids)),
        trace_sha256=hashlib.sha256(trace_path.read_bytes()).hexdigest(),
    )


def test_raw_source_rows_preserve_repeated_positions_and_validate_complete_channels(tmp_path):
    ids, proposals, trace_path = _raw_trace_fixture(tmp_path)
    rows = _raw_source_rows(trace_path, **_raw_kwargs(ids, trace_path))
    assert [row.candidate_ids for row in rows] == [proposals["s1"], proposals["s2"]]
    report = _raw_aggregate(
        rows, (ReferenceIntentRow("s1", "a"), ReferenceIntentRow("s2", "a")),
        {"s1": {"scenario": "one"}, "s2": {"scenario": "two"}}, set(ids),
        stratum_field="scenario",
    )
    assert report["rank1_correct_count"] == 1
    assert report["distinct_proposal_coverage_count"] == 2
    assert report["coverage_headroom_count"] == 1
    assert report["by_observed_distinct_width"]["2"]["count"] == 2
    assert report["equal_stratum"]["coverage_headroom"] == 0.5


def test_raw_source_rows_reject_non_normal_stop(tmp_path):
    ids, _, trace_path = _raw_trace_fixture(tmp_path, finish_reason="length")
    with pytest.raises(SlurpTopNAnalysisError, match="did not stop normally"):
        _raw_source_rows(trace_path, **_raw_kwargs(ids, trace_path))


@pytest.mark.parametrize("defect,match", [
    ("missing", "required channels"),
    ("duplicate", "duplicates record_id"),
    ("wire", "wire hash"),
    ("audio", "audio cost"),
    ("illegal", "legal"),
    ("bytes", "hash mismatch"),
])
def test_unsealed_trace_rejects_bound_identity_and_cost_defects(tmp_path, defect, match):
    ids, _, path = _raw_trace_fixture(tmp_path)
    kwargs = _raw_kwargs(ids, path)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    if defect == "missing":
        records = [r for r in records if r["channel"] != "MODEL_WIRE_RESPONSE"]
    elif defect == "duplicate":
        records.append(records[0])
    elif defect == "wire":
        next(r for r in records if r["channel"] == "MODEL_WIRE_RESPONSE")["payload"]["response_sha256"] = "0" * 64
    elif defect == "audio":
        kwargs["expected_audio_seconds"] = 3.0
    elif defect == "illegal":
        kwargs["legal_intent_ids"] = frozenset({"a"})
    elif defect == "bytes":
        records.append(records[0])
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    if defect != "bytes":
        kwargs["trace_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(SlurpTopNAnalysisError, match=match):
        _raw_source_rows(path, **kwargs)


def _raw_entry_fixture(tmp_path):
    ids, _, trace_path = _raw_trace_fixture(tmp_path)
    def pin(path):
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    def save(name, obj):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj))
        return pin(path)
    from speech_aware_evidence_acquisition.reproduction.sampling import split_identity_hash as key_hash
    def roster(name, selected):
        items = [{"id": item, "key": "slurp:" + item} for item in selected]
        return save("docs/receipts/probe-samples/" + name + ".json", {
            "schema": "saea-dev-ladder-v1", "carrier": "slurp", "split_role": "dev",
            "items": items, "split_identity_hash": key_hash([item["key"] for item in items]),
        })
    full, primary = roster("full", ids), roster("primary", ids[:1])
    metadata = save("metadata.json", {"rows": {
        "s1": {"scenario": "one", "speaker": "one"},
        "s2": {"scenario": "two", "speaker": "two"},
    }})
    split_hash = split_identity_hash(prefixed("slurp", ids))
    plan = save("plan.json", {"execution_plan": {
        "run_id": "synthetic", "attempt_id": "synthetic-attempt",
        "carrier_lock_key": "slurp", "split_role": "dev", "split_identity_hash": split_hash,
        "execution_profile": "bounded-discovery-probe", "planned_model_calls": 2,
        "planned_gpu_hours": 1.0, "planned_speech_audio_seconds": 2, "protocol_hash": "1" * 64,
    }})
    attempt = save("attempt.json", {
        "schema": "saea-attempt-v1", "state": "ABORTED", "run_id": "synthetic",
        "attempt_id": "synthetic-attempt", "carrier_lock_key": "slurp",
        "actual": {"calls": 2, "audio_seconds": 2.0},
        "reserved": {"calls": 2, "audio_seconds": 2.0},
    })
    references = {
        "kind": "slurp-split", "split_id": "devel", "split_identity_hash": split_hash,
        "lock": save("lock.json", {}), "data_root": str(tmp_path),
        "allow_heldout": False, "allow_synthetic": False,
    }
    release = save("release.json", {
        "experiment_id": "owner-test", "source_attempt": attempt, "source_trace": pin(trace_path),
        "source_generation_plan": plan, "full_roster": full, "primary_roster": primary,
        "metadata": metadata, "reference_source": references,
    })
    config = {
        "experiment_id": "synthetic-raw", "execution_profile": "model-free-check",
        "analysis": {
            "full_roster": full, "roster": primary, "metadata": metadata,
            "source_diagnostics": {"reference_source": references},
            "raw_source_diagnostics": {
                "source_quality_read_release": {
                    "authorized": True, "release_id": "owner-test", "registration": release,
                },
                "expected_contacts": 2, "max_candidates": 3, "split_identity_hash": split_hash,
                "attempt": attempt, "generation_plan": plan, "raw_trace": pin(trace_path),
                "legal_intent_ids": save("legal.json", {"profiles": [{"candidate_id": "a"}, {"candidate_id": "b"}]}),
                "bootstrap": {"seed": 7, "n_replicates": 100, "ci_level": 0.9, "cluster_field": "speaker"},
            },
        },
    }
    return config


def test_raw_source_entry_uses_real_unsealed_attempt_shape_without_bundle_mock(tmp_path):
    config = _raw_entry_fixture(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    output = tmp_path / "report.json"
    raw = config["analysis"]["raw_source_diagnostics"]
    verified = verify_aborted_contact_source(
        attempt_pin=raw["attempt"],
        trace_pin=raw["raw_trace"],
        generation_plan_pin=raw["generation_plan"],
        expected_sample_ids=("s1", "s2"),
    )
    assert verified.attempt["state"] == "ABORTED"
    assert set(verified.contacts_by_sample_id["s1"]) == {
        "request_id", "request", "response", "wire", "cost"
    }
    with pytest.raises(TypeError):
        verified.trace_records["unexpected"] = {}
    result = run_raw_source(
        config_path, output,
        reference_loader=lambda *_args, **_kwargs: [
            SimpleNamespace(sample_id="s1", intent="a"), SimpleNamespace(sample_id="s2", intent="a"),
        ],
    )
    assert result["source"]["attempt_state"] == "ABORTED"
    assert result["diagnostics"]["NEW500"]["rank1_accuracy"] == 1.0
    assert result["diagnostics"]["OLD500"]["distinct_proposal_coverage"] == 1.0
    assert result["diagnostics"]["DEV1000"]["speaker_ci90_percent"]["coverage_headroom"]["point_estimate"] == 50.0
    assert not list(tmp_path.glob("*manifest*"))
    assert json.loads(output.read_text())["scorer_invocations"] == 0


@pytest.mark.parametrize("defect,match", [
    ("release", "explicit authorized"),
    ("attempt", "ABORTED attempt"),
    ("plan", "differs from source plan"),
])
def test_unsealed_entry_refuses_before_reference_read(tmp_path, defect, match):
    config = _raw_entry_fixture(tmp_path)
    raw = config["analysis"]["raw_source_diagnostics"]
    if defect == "release":
        raw["source_quality_read_release"]["authorized"] = False
    else:
        key = "attempt" if defect == "attempt" else "generation_plan"
        path = Path(raw[key]["path"])
        document = json.loads(path.read_text())
        if defect == "attempt":
            document["state"] = "OPENED"
        else:
            document["execution_plan"]["attempt_id"] = "wrong-attempt"
        path.write_text(json.dumps(document))
        raw[key]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    def no_read(*_args, **_kwargs):
        pytest.fail("references must not be read")
    with pytest.raises(SlurpTopNAnalysisError, match=match):
        run_raw_source(path, tmp_path / "report.json", reference_loader=no_read)


def test_distinct_source_binding_is_selected_without_changing_fixed_default():
    fixed = {"shared_fixed_top3_source": {"candidate_count": 3}}
    assert _select_source_binding(fixed) == (
        "shared_fixed_top3_source", fixed["shared_fixed_top3_source"], False
    )

    distinct = {"shared_distinct_source": {"candidate_count_range": [1, 3]}}
    assert _select_source_binding(distinct) == (
        "shared_distinct_source", distinct["shared_distinct_source"], True
    )

    with pytest.raises(SlurpTopNAnalysisError, match="source binding"):
        _select_source_binding({"shared_distinct_source": {}, "shared_fixed_top3_source": {}})


def test_verified_entity_adapter_uses_exact_counts_and_handles_empty_entities():
    document = {
        "verified": True,
        "scores": {
            "slurp-slu-official": {
                "per_sample": [
                    {"sample_id": "empty", "slot_f1_exact_fp": 0, "slot_f1_exact_fn": 0},
                    {"sample_id": "wrong_entity", "slot_f1_exact_fp": 1, "slot_f1_exact_fn": 0},
                    {"sample_id": "missed_entity", "slot_f1_exact_fp": 0, "slot_f1_exact_fn": 1},
                ]
            }
        },
    }
    assert _entity_correctness_from_verified_score_document(
        document, scorer="slurp-slu-official",
        expected_ids={"empty", "wrong_entity", "missed_entity"}
    ) == {"empty": True, "wrong_entity": False, "missed_entity": False}


def test_verified_entity_adapter_reads_only_hash_pinned_score_result(tmp_path):
    score_path = tmp_path / "score.json"
    score_path.write_text(json.dumps({
        "verified": True,
        "scores": {"slurp-slu-official": {"per_sample": [
            {"sample_id": "s1", "slot_f1_exact_fp": 0, "slot_f1_exact_fn": 0},
        ]}},
    }), encoding="utf-8")
    score_pin = {
        "path": str(score_path),
        "sha256": hashlib.sha256(score_path.read_bytes()).hexdigest(),
    }
    assert _entity_correctness_from_verified_receipt(
        {"score_result": score_pin},
        scorer="slurp-slu-official",
        expected_ids={"s1"},
    ) == {"s1": True}


def test_verified_entity_adapter_refuses_score_roster_mismatch():
    document = {
        "verified": True,
        "scores": {"slurp-slu-official": {"per_sample": [
            {"sample_id": "foreign", "slot_f1_exact_fp": 0, "slot_f1_exact_fn": 0},
        ]}},
    }
    with pytest.raises(SlurpTopNAnalysisError, match="roster"):
        _entity_correctness_from_verified_score_document(
            document, scorer="slurp-slu-official", expected_ids={"s1"}
        )


def test_distinct_candidate_range_accepts_configured_five_and_is_bounded():
    assert _select_source_binding(
        {"shared_distinct_source": {"candidate_count_range": [1, 5]}}
    )[2] is True
    from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli import (
        _source_candidate_width,
    )
    assert _source_candidate_width(
        {"candidate_count_range": [1, 5]}, distinct=True
    ) == 5
    with pytest.raises(SlurpTopNAnalysisError, match="candidate_count_range"):
        _source_candidate_width(
            {"candidate_count_range": [5, 4]}, distinct=True
        )


def test_verified_entity_adapter_leaves_missing_sufficient_counts_unavailable():
    document = {
        "verified": True,
        "scores": {"slurp-slu-official": {"per_sample": [
            {"sample_id": "s1", "slot_f1_exact_f1": 1.0},
        ]}},
    }
    assert _entity_correctness_from_verified_score_document(
        document, scorer="slurp-slu-official", expected_ids={"s1"}
    ) == {"s1": None}


def test_observed_width_reports_cover_configured_widths_and_reject_mismatch():
    source = (
        SourceCandidateRow("s1", ("a",)),
        SourceCandidateRow("s2", ("a", "b")),
        SourceCandidateRow("s3", ("a", "b", "c", "d", "e")),
    )
    refs = tuple(ReferenceIntentRow(sid, "a") for sid in ("s1", "s2", "s3"))
    branches = {"closed_joint": tuple(
        BranchOutcomeRow(sid, "a", False, None) for sid in ("s1", "s2", "s3")
    )}
    reports = _observed_width_reports(source, refs, branches, candidate_width=5)
    assert set(reports) == {"1", "2", "5"}
    assert [
        reports[str(width)]["source"]["sample_count"] for width in (1, 2, 5)
    ] == [1, 1, 1]
    assert reports["2"]["candidate_width"] == 2

    with pytest.raises(SlurpTopNAnalysisError, match="width"):
        _observed_width_reports(
            (SourceCandidateRow("s1", ("a", "b", "c", "d")),),
            (ReferenceIntentRow("s1", "a"),),
            {"closed_joint": (BranchOutcomeRow("s1", "a", False, None),)},
            candidate_width=3,
        )
