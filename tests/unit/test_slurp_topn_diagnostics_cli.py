from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli import (
    SlurpTopNAnalysisError,
    _branch_rows,
    _raw_aggregate,
    _raw_source_rows,
    _transport_response_sha256,
    _references,
    _source_rows,
    run_raw_source,
)
from speech_aware_evidence_acquisition.contracts import TraceRecord
from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics import ReferenceIntentRow
from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical
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
        "joint", branch, source_path, binding["manifest"]["sha256"], states, ids
    )

    assert rows[0].final_intent_id == "a_x"
    assert rows[0].refused is False

    branch.manifest["phase_sources"][1]["sealed_state_sha256"] = "f" * 64
    with pytest.raises(SlurpTopNAnalysisError, match="state binding"):
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
    hashes = {
        document["record_id"]: TraceRecord(
            document["channel"], document["record_id"], document["payload"]
        ).content_hash()
        for document in documents
    }
    trace_path = tmp_path / "raw-trace.jsonl"
    trace_path.write_text(
        "\n".join(json.dumps(document, sort_keys=True, separators=(",", ":")) for document in documents)
        + "\n",
        encoding="utf-8",
    )
    trace_manifest_path = tmp_path / "trace-manifest.json"
    trace_manifest_path.write_text(
        json.dumps({"records": hashes}, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "aborted.manifest.json"
    manifest = {
        "status": "ABORTED",
        "split": {
            "identity_hash": split_identity_hash(prefixed("slurp", ids)),
            "ids": list(ids),
        },
        "raw_trace": {
            "path": str(trace_path),
            "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
        },
        "trace_manifest": {
            "path": str(trace_manifest_path),
            "sha256": hashlib.sha256(trace_manifest_path.read_bytes()).hexdigest(),
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    bundle = __import__("types").SimpleNamespace(
        manifest=manifest,
        manifest_path=manifest_path,
        split_ids=frozenset(ids),
        attempt_state="ABORTED",
        trace_records=payloads,
    )
    return ids, proposals, trace_path, trace_manifest_path, manifest_path, bundle


def test_raw_source_rows_preserve_repeated_positions_and_validate_complete_channels(tmp_path):
    ids, proposals, trace_path, trace_manifest_path, _manifest_path, bundle = _raw_trace_fixture(tmp_path)

    rows = _raw_source_rows(
        trace_path,
        trace_manifest_path,
        bundle,
        expected_ids=ids,
        legal_intent_ids=frozenset({"a", "b"}),
        max_candidates=3,
        expected_contacts=2,
    )

    assert [row.candidate_ids for row in rows] == [proposals["s1"], proposals["s2"]]
    report = _raw_aggregate(
        rows,
        (ReferenceIntentRow("s1", "a"), ReferenceIntentRow("s2", "a")),
        {"s1": {"scenario": "one"}, "s2": {"scenario": "two"}},
        set(ids),
        stratum_field="scenario",
    )
    assert report["rank1_correct_count"] == 1
    assert report["distinct_proposal_coverage_count"] == 2
    assert report["by_observed_distinct_width"]["2"]["count"] == 2


def test_raw_source_rows_reject_non_normal_stop(tmp_path):
    ids, _proposals, trace_path, trace_manifest_path, _manifest_path, bundle = _raw_trace_fixture(
        tmp_path, finish_reason="length"
    )

    with pytest.raises(SlurpTopNAnalysisError, match="did not stop normally"):
        _raw_source_rows(
            trace_path,
            trace_manifest_path,
            bundle,
            expected_ids=ids,
            legal_intent_ids=frozenset({"a", "b"}),
            max_candidates=3,
            expected_contacts=2,
        )


def test_raw_source_entry_point_requires_release_and_reports_pinned_populations(tmp_path, monkeypatch):
    ids, _proposals, trace_path, trace_manifest_path, manifest_path, bundle = _raw_trace_fixture(tmp_path)
    lock_path = tmp_path / "lock.json"
    lock_path.write_text("{}", encoding="utf-8")
    legal_path = tmp_path / "legal.json"
    legal_path.write_text(json.dumps({"intent_ids": ["a", "b"]}), encoding="utf-8")
    legal_pin = {
        "path": str(legal_path),
        "sha256": hashlib.sha256(legal_path.read_bytes()).hexdigest(),
    }
    manifest_pin = {
        "path": str(manifest_path),
        "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    trace_pin = {
        "path": str(trace_path),
        "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
    }
    trace_manifest_pin = {
        "path": str(trace_manifest_path),
        "sha256": hashlib.sha256(trace_manifest_path.read_bytes()).hexdigest(),
    }
    config = {
        "experiment_id": "synthetic-raw",
        "execution_profile": "model-free-check",
        "analysis": {
            "full_roster": {"path": "full", "sha256": "0" * 64},
            "roster": {"path": "primary", "sha256": "0" * 64},
            "metadata": {"path": "metadata", "sha256": "0" * 64},
            "stratum_field": "scenario",
            "source_diagnostics": {
                "reference_source": {
                    "kind": "slurp-split",
                    "split_id": "synthetic",
                    "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
                    "lock": {
                        "path": str(lock_path),
                        "sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                    },
                    "data_root": str(tmp_path),
                }
            },
            "raw_source_diagnostics": {
                "source_quality_read_release": {"authorized": True, "release_id": "owner-test"},
                "expected_contacts": 2,
                "max_candidates": 3,
                "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
                "manifest": manifest_pin,
                "raw_trace": trace_pin,
                "trace_manifest": trace_manifest_pin,
                "legal_intent_ids": legal_pin,
            },
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    output = tmp_path / "report.json"

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli._roster_ids",
        lambda _value, label: ids if label.endswith("full_roster") else ("s1",),
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli._metadata",
        lambda *_args: {"s1": {"scenario": "one"}, "s2": {"scenario": "two"}},
    )
    result = run_raw_source(
        config_path,
        output,
        bundle_verifier=lambda _path: bundle,
        reference_loader=lambda *_args, **_kwargs: [
            __import__("types").SimpleNamespace(sample_id="s1", intent="a"),
            __import__("types").SimpleNamespace(sample_id="s2", intent="a"),
        ],
    )

    assert result["source"]["attempt_state"] == "ABORTED"
    assert result["diagnostics"]["NEW500"]["rank1_accuracy"] == 1.0
    assert result["diagnostics"]["OLD500"]["distinct_proposal_coverage"] == 1.0
    assert json.loads(output.read_text())["scorer_invocations"] == 0
