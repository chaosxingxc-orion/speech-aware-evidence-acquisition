"""Synthetic verifier-selection read tests; no model, scorer, or real run bytes."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[2] / "scripts" / "analysis" / "slurp_verifier_selection_read.py"
SPEC = importlib.util.spec_from_file_location("slurp_verifier_selection_read", PATH)
read = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = read
SPEC.loader.exec_module(read)


def score(sid, tp, fp, fn, intent=1):
    return {"sample_id": sid, "slu_f1_word_tp": tp/2, "slu_f1_char_tp": tp/2,
            "slu_f1_word_fp": fp/2, "slu_f1_char_fp": fp/2,
            "slu_f1_word_fn": fn/2, "slu_f1_char_fn": fn/2,
            "scenario_action_exact": intent,
            "slu_f1_f1": 0 if 2*tp+fp+fn == 0 else 2*tp/(2*tp+fp+fn)}


def fixture():
    ids = ["slurp:train:u1:a", "slurp:train:u2:a", "slurp:train:u3:a",
           "slurp:train:u4:a", "slurp:train:u5:a"]
    # Last row has a malformed source placeholder at index 4.
    scores = {i: {sid: score(sid, 1, 1, 1) for sid in ids} for i in range(5)}
    for index in range(5):
        scores[index][ids[0]] = score(ids[0], 2 if index == 2 else 0,
                                      0 if index == 2 else 1, 0 if index == 2 else 1)
        scores[index][ids[1]] = score(ids[1], 2 if index == 0 else 1, 0 if index == 0 else 1, 0)
    scores[4][ids[4]] = score(ids[4], 0, 2, 0)
    receipt = {}
    for n, sid in enumerate(ids):
        receipt[sid] = {"sample_id": sid, "permutation": [4,3,2,1,0],
                        "distinct_answers": 1 if n == 2 else 2,
                        "parse_failed": 1 if n == 4 else 0,
                        "parse_ok": 4 if n == 4 else 5}
    verifier = {sid: {"sample_id": sid, "text": '{"chosen_position":3,"reason":"ok"}',
                      "contact_count": 1} for sid in ids}
    verifier[ids[3]]["text"] = '{"chosen_position":9,"reason":"bad"}'
    verifier[ids[4]]["text"] = '{"chosen_position":1,"reason":"malformed source"}'
    strata = {sid: ("alarm" if n < 3 else "audio") for n, sid in enumerate(ids)}
    utterances = {sid: sid for sid in ids}
    medoid = {sid: 0 for sid in ids}
    source_status = {sid: {i: "ok" for i in range(5)} for sid in ids}
    source_status[ids[4]][4] = "malformed"
    return ids, scores, receipt, verifier, strata, utterances, medoid, source_status


def test_all_rows_fallback_and_subsets():
    ids,scores,receipt,verifier,strata,utterances,medoid,source_status=fixture()
    result=read.analyze(ids,scores,receipt,verifier,strata,utterances,medoid,source_status,draws=60)
    assert result["populations"] == {"all":5,"content_distinct":4,"all_parsed":3,
                                     "identical":1,"score_differing":3}
    assert result["choice"]["fallback_count"] == 1
    assert result["choice"]["selected_malformed_source_count"] == 1
    assert result["choice"]["source_index_hist"]["all"]["0"] == 1
    assert result["comparisons"]["all"]["chosen"]["rows"] == 5
    assert result["choice"]["oracle_tie_set_hist"]
    assert "natural_mixture" in result["per_scenario"]
    assert "equal_stratum" in result["per_scenario"]
    assert result["primary"]["benefit_status"] in {"positive_ci95", "not_proven"}


def test_fail_closed_on_missing_or_partial_group():
    ids,scores,receipt,verifier,strata,utterances,medoid,source_status=fixture()
    del verifier[ids[0]]
    with pytest.raises(read.ReadError):
        read.analyze(ids,scores,receipt,verifier,strata,utterances,medoid,source_status,draws=10)
    ids,scores,receipt,verifier,strata,utterances,medoid,source_status=fixture()
    del scores[3][ids[0]]
    with pytest.raises(read.ReadError):
        read.analyze(ids,scores,receipt,verifier,strata,utterances,medoid,source_status,draws=10)


def test_intent_margin_is_explicit_and_not_borrowed():
    ids,scores,receipt,verifier,strata,utterances,medoid,source_status=fixture()
    unresolved=read.analyze(ids,scores,receipt,verifier,strata,utterances,medoid,source_status,draws=20)
    assert unresolved["primary"]["intent_noninferiority"] == "UNRESOLVED"
    resolved=read.analyze(ids,scores,receipt,verifier,strata,utterances,medoid,source_status,
                          draws=20,intent_ni_margin_pp=2.0)
    assert resolved["primary"]["intent_margin_pp"] == 2.0
    with pytest.raises(read.ReadError):
        read.analyze(ids,scores,receipt,verifier,strata,utterances,medoid,source_status,
                     draws=20,intent_ni_margin_pp=-1)


@pytest.mark.parametrize("registered_run", [read.RUN_ID, "SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-V1"])
def test_bound_file_read_and_no_overwrite(tmp_path, registered_run):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.rails.phase_material import (
        balanced_sealed_sample_permutations,
    )
    ids,scores,receipt,verifier,strata,utterances,medoid,source_status=fixture()
    run_dir=tmp_path/"run"
    run_dir.mkdir()
    source_manifest=tmp_path/"source-manifest.json"
    source_manifest.write_text("{}", encoding="utf-8")
    manifest=run_dir/f"{registered_run}.run-manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    roster_path=tmp_path/"roster.json"
    roster_doc={"items":[{"sample_id":sid,"stratum":strata[sid],
                          "utterance_id":utterances[sid]} for sid in ids],
                "split_role":"discovery","split_identity_hash":"synthetic-hash"}
    roster_path.write_text(json.dumps(roster_doc),encoding="utf-8")
    source_rows=[]
    rendered={}
    for sid in ids:
        records=[]
        for index in range(5):
            payload={"scenario":"a","action":str(index if sid!=ids[2] else 0),
                     "entities":[]}
            status=source_status[sid][index]
            record={"sample_index":index,"parse_status":status,
                    "parsed_answer":payload if status=="ok" else None}
            records.append(record)
            rendered[(sid,index)]=read._render_source(record)
        source_rows.append({"sample_id":sid,"solver_group":{"samples":records}})
    permutations=balanced_sealed_sample_permutations(tuple(ids),seed=20260925,count=5)
    material=[]
    for sid in ids:
        row=dict(receipt[sid])
        row["permutation"]=list(permutations[sid])
        row["rendered_sha256"]=[
            __import__("hashlib").sha256(rendered[(sid,index)].encode()).hexdigest()
            for index in row["permutation"]]
        row["distinct_answers"]=len(set(rendered[(sid,i)] for i in range(5)))
        material.append(row)
    receipt_doc={"presentation":{"permutation_rule_id":"balanced-block-v1",
                                 "permutation_seed":20260925,"expected_sample_count":5},
                 "source":{"manifest_sha256":read.sha256_file(source_manifest),
                           "roster_sha256":read.sha256_file(roster_path),
                           "rollout_run_id":"SOURCE","split_identity_hash":"synthetic-hash"},
                 "rows":material}
    receipt_path=tmp_path/"receipt.json"
    receipt_path.write_text(json.dumps(receipt_doc),encoding="utf-8")
    score_root=tmp_path/"scores"
    score_root.mkdir()
    copies={}
    for index in range(5):
        copy_path=score_root/f"sample-{index}.jsonl"
        copy_path.write_text("\n".join(json.dumps({"sample_id":sid,"text":rendered[(sid,index)]})
                                        for sid in ids)+"\n",encoding="utf-8")
        copies[f"sample_{index}"]={"path":str(copy_path),"sha256":read.sha256_file(copy_path)}
        values=[read.extract_official_feedback(scores[index][sid]) for sid in ids]
        score_doc={read.SCORER:{"aggregate":{"identity_check":{"passed":True},
                                             "official":{"slu_f1":read.pooled_f1(values),
                                                         "intent_accuracy":sum(v.intent_exact for v in values)/5}},
                                "per_sample":[scores[index][sid] for sid in ids]}}
        (score_root/f"sample_{index}-{read.SCORER}-scores.json").write_text(
            json.dumps(score_doc),encoding="utf-8")
    (score_root/"render-manifest.json").write_text(
        json.dumps({"samples":5,"copies":copies}),encoding="utf-8")
    (run_dir/f"{registered_run}.generation-manifest.json").write_text(
        json.dumps({"cost":{"calls_used":5,"prompt_tokens_total":100,
                            "completion_tokens_total":20}}),encoding="utf-8")
    source_bundle=SimpleNamespace(
        manifest={"status":"COMPLETED","split":{"role":"discovery"},"run_id":"SOURCE"},
        attempt_state="FINALIZED",split_ids=frozenset(ids),outputs_rows=tuple(source_rows))
    trace_records = {}
    verifier_rows = []
    for n, sid in enumerate(ids):
        request_id = f"flight-{n:04d}"
        row = {key: value for key, value in verifier[sid].items() if key != "contact_count"}
        row["request_id"] = request_id
        verifier_rows.append(row)
        trace_records[f"{request_id}/request"] = {
            "arm": "choice", "payload_sha256": "1" * 64,
            "payload": {"sample_id": sid, "request_id": request_id},
        }
        trace_records[f"{request_id}/response"] = {"text": row["text"]}
    verifier_bundle=SimpleNamespace(
        manifest={"status":"COMPLETED","split":{"role":"discovery"},"run_id":registered_run},
        attempt_state="FINALIZED",split_ids=frozenset(ids),outputs_rows=tuple(verifier_rows),
        trace_records=trace_records)
    def fake_verify(path):
        return source_bundle if Path(path)==source_manifest else verifier_bundle
    kwargs=dict(manifest_path=manifest,source_manifest_path=source_manifest,
                receipt_path=receipt_path,expected_receipt_sha256=read.sha256_file(receipt_path),
                roster_path=roster_path,score_root=score_root,out_root=tmp_path/"report",
                expected_rows=5,draws=20,bundle_verifier=fake_verify)
    if registered_run != read.RUN_ID:
        kwargs["expected_run_id"] = registered_run
    report=read.run(**kwargs)
    assert report["bindings"]["verifier_run_id"] == registered_run
    assert report["rows"]==5
    assert report["choice"]["one_contact_every_row"] is True
    assert report["bindings"]["contact_count_source"] == "verified_model_request_trace"
    assert all("contact_count" not in row for row in verifier_rows)
    assert (tmp_path/"report"/"report.json").exists()
    assert "chosen_position" not in (tmp_path/"report"/"report.md").read_text()
    with pytest.raises(read.ReadError,match="already exists"):
        read.run(**kwargs)
    kwargs["out_root"]=tmp_path/"bad-report"
    kwargs["expected_receipt_sha256"]="0"*64
    with pytest.raises(read.ReadError,match="SHA-256"):
        read.run(**kwargs)
    assert not kwargs["out_root"].exists()
    kwargs["expected_receipt_sha256"] = read.sha256_file(receipt_path)
    verifier_bundle.manifest["status"] = "PARTIAL"
    with pytest.raises(read.ReadError, match="partial"):
        read.run(**kwargs)
    assert not kwargs["out_root"].exists()

    verifier_bundle.manifest["status"] = "COMPLETED"
    kwargs["expected_run_id"] = "WRONG-REGISTERED-RUN"
    with pytest.raises(read.ReadError, match="run ID"):
        read.run(**kwargs)
    assert not kwargs["out_root"].exists()


def test_trace_contact_counts_include_retries_without_mutating_output():
    rows = {"s1": {"sample_id": "s1", "request_id": "b", "text": "answer"}}
    trace = {
        "a/request": {"arm": "choice", "payload_sha256": "1" * 64,
                      "payload": {"sample_id": "s1", "request_id": "a"}},
        "b/request": {"arm": "choice", "payload_sha256": "2" * 64,
                      "payload": {"sample_id": "s1", "request_id": "b"}},
        "b/response": {"text": "answer"},
    }
    enriched = read.bind_contact_counts(rows, trace, calls_used=2)
    assert enriched["s1"]["contact_count"] == 2
    assert "contact_count" not in rows["s1"]


@pytest.mark.parametrize("fault", ["missing_trace", "wrong_sample", "wrong_request",
                                  "wrong_total", "declared_mismatch", "duplicate_request"])
def test_trace_contact_counts_refuse_invalid_bindings(fault):
    rows = {"s1": {"sample_id": "s1", "request_id": "a", "text": "answer"}}
    trace = {
        "a/request": {"arm": "choice", "payload_sha256": "1" * 64,
                      "payload": {"sample_id": "s1", "request_id": "a"}},
        "a/response": {"text": "answer"},
    }
    total = 1
    if fault == "missing_trace":
        del trace["a/request"]
    elif fault == "wrong_sample":
        trace["a/request"]["payload"]["sample_id"] = "other"
    elif fault == "wrong_request":
        rows["s1"]["request_id"] = "other"
    elif fault == "wrong_total":
        total = 2
    elif fault == "declared_mismatch":
        rows["s1"]["contact_count"] = 2
    else:
        trace["b/request"] = trace["a/request"]
    with pytest.raises(read.ReadError):
        read.bind_contact_counts(rows, trace, calls_used=total)
