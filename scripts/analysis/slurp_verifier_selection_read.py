#!/usr/bin/env python3
"""Read a sealed VERIFY-1 choice campaign against sealed ROLL-1 official counts."""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
import hashlib
import json
import math
import os
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from speech_aware_evidence_acquisition.analysis.official_metric_feedback import (
    FeedbackError, OfficialFeedback, extract_official_feedback, frozen_baseline_f1,
    pooled_f1, utility,
)
from speech_aware_evidence_acquisition.rails.artifact_results import (
    ArtifactContentError, parse_slurp_verifier_choice,
)

SCHEMA = "saea-slurp-verifier-selection-read-v1"
SCORER = "slurp-slu-official-projected-v3-train"
RUN_ID = "SAEA-SLURP-STAGE3-VERIFY-1-V1"
SAMPLES = 5
SEED = 20260915
DRAWS = 10000


class ReadError(ValueError):
    """A sealed input, source binding, or analysis declaration is invalid."""


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    try:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReadError(f"invalid JSON input {path}: {error}") from error
    if not isinstance(result, dict):
        raise ReadError(f"JSON input {path} is not an object")
    return result


def exact_ids(ids, mapping, label):
    if not isinstance(mapping, dict) or len(mapping) != len(ids) or set(mapping) != set(ids):
        raise ReadError(f"{label} has missing, extra, or duplicate identities")


def numeric_margin(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReadError("intent own-null margin must be finite and nonnegative")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ReadError("intent own-null margin must be finite and nonnegative")
    return value


def summary(rows):
    if not rows:
        return {"rows": 0, "status": "EMPTY"}
    return {
        "rows": len(rows),
        "slu_f1_pp": 100 * pooled_f1(rows),
        "intent_pp": 100 * sum(row.intent_exact for row in rows) / len(rows),
    }


def paired_ci(arms, ids, utterances, draws, seed):
    """Paired whole-utterance bootstrap, shared draws for all arms."""
    import numpy as np
    clusters = sorted({utterances[sid] for sid in ids})
    if not clusters or isinstance(draws, bool) or not isinstance(draws, int) or draws < 1:
        raise ReadError("bootstrap needs positive draws and at least one cluster")
    members = [[sid for sid in ids if utterances[sid] == key] for key in clusters]
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(clusters), size=(draws, len(clusters)))
    weights = np.zeros((draws, len(clusters)), dtype=np.float64)
    for draw in range(draws):
        weights[draw] = np.bincount(indices[draw], minlength=len(clusters))
    vectors = {}
    for name, arm in arms.items():
        matrix = np.array([
            [sum(arm[sid].tp for sid in group), sum(arm[sid].fp for sid in group),
             sum(arm[sid].fn for sid in group),
             sum(arm[sid].intent_exact for sid in group), len(group)]
            for group in members
        ], dtype=np.float64)
        totals = weights @ matrix
        denominator = 2 * totals[:, 0] + totals[:, 1] + totals[:, 2]
        f1 = np.divide(2 * totals[:, 0], denominator,
                       out=np.zeros(draws), where=denominator > 0)
        vectors[name] = (100 * f1, 100 * totals[:, 3] / totals[:, 4])
    result = {}
    for name in ("mean_single", "sample0", "medoid", "row_f1_oracle", "utility_oracle"):
        delta_slu = vectors["chosen"][0] - vectors[name][0]
        delta_intent = vectors["chosen"][1] - vectors[name][1]
        result[name] = {
            "delta_slu_ci95_pp": [float(np.percentile(delta_slu, 2.5)),
                                  float(np.percentile(delta_slu, 97.5))],
            "delta_intent_ci95_pp": [float(np.percentile(delta_intent, 2.5)),
                                     float(np.percentile(delta_intent, 97.5))],
        }
    return result


def analyze(ids, scores, receipt, verifier, strata, utterances, medoid,
            source_status, *, draws=DRAWS, seed=SEED, intent_ni_margin_pp=None,
            expected_rows=None, cost=None):
    """Produce only aggregate tables; every input is aligned by sample identity."""
    ids = tuple(ids)
    if not ids or len(set(ids)) != len(ids):
        raise ReadError("roster identities must be nonempty and unique")
    if expected_rows is not None and len(ids) != expected_rows:
        raise ReadError("roster count disagrees with registration")
    for label, data in (("receipt", receipt), ("verifier", verifier),
                        ("strata", strata), ("utterances", utterances),
                        ("medoid", medoid), ("source_status", source_status)):
        exact_ids(ids, data, label)
    if set(scores) != set(range(SAMPLES)):
        raise ReadError("source sample indices must be exactly 0..4")
    for index in range(SAMPLES):
        exact_ids(ids, scores[index], f"source score {index}")
    margin = numeric_margin(intent_ni_margin_pp)
    source = {index: {} for index in range(SAMPLES)}
    row_f1 = {index: {} for index in range(SAMPLES)}
    for index in range(SAMPLES):
        for sid in ids:
            raw = scores[index][sid]
            try:
                item = extract_official_feedback(raw)
            except FeedbackError as error:
                raise ReadError(f"source score invalid at index {index}: {error}") from error
            if item.sample_id != sid:
                raise ReadError("source score sample identity differs from its binding")
            value = raw.get("slu_f1_f1")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or (
                not math.isfinite(float(value)) or not 0 <= float(value) <= 1
            ):
                raise ReadError("source row SLU-F1 is invalid")
            if abs(pooled_f1([item]) - float(value)) > 1e-6:
                raise ReadError("source row SLU-F1 does not reproduce official counts")
            source[index][sid] = item
            row_f1[index][sid] = float(value)
    for sid in ids:
        record = receipt[sid]
        statuses = source_status[sid]
        if not isinstance(statuses, dict) or set(statuses) != set(range(SAMPLES)):
            raise ReadError("source parse-status group is partial")
        if any(not isinstance(statuses[i], str) or not statuses[i] for i in range(SAMPLES)):
            raise ReadError("source parse status is invalid")
        permutation = record.get("permutation")
        if record.get("sample_id") != sid or not isinstance(permutation, list) or (
            len(permutation) != SAMPLES or
            any(isinstance(i, bool) or not isinstance(i, int) for i in permutation) or
            set(permutation) != set(range(SAMPLES))
        ):
            raise ReadError("receipt source permutation is incomplete")
        if (record.get("parse_ok") != sum(statuses[i] == "ok" for i in range(SAMPLES)) or
            record.get("parse_failed") != sum(statuses[i] != "ok" for i in range(SAMPLES))):
            raise ReadError("receipt parse counts disagree with source")
        distinct = record.get("distinct_answers")
        if isinstance(distinct, bool) or not isinstance(distinct, int) or not 1 <= distinct <= SAMPLES:
            raise ReadError("receipt distinct-answer count is invalid")
        if isinstance(medoid[sid], bool) or medoid[sid] not in range(SAMPLES):
            raise ReadError("medoid index is invalid")
        if not isinstance(strata[sid], str) or not strata[sid]:
            raise ReadError("roster stratum is missing")
        if not isinstance(utterances[sid], str) or not utterances[sid]:
            raise ReadError("roster utterance identity is missing")
        if not isinstance(verifier[sid], dict) or verifier[sid].get("sample_id") != sid:
            raise ReadError("verifier sample identity differs from its binding")

    mean = {
        sid: OfficialFeedback(
            sid, *(sum(getattr(source[i][sid], field) for i in range(SAMPLES)) / SAMPLES
                    for field in ("tp", "fp", "fn", "intent_exact"))
        ) for sid in ids
    }
    f0 = frozen_baseline_f1(list(mean.values()))
    arms = {
        "mean_single": mean,
        "sample0": source[0],
        "medoid": {sid: source[medoid[sid]][sid] for sid in ids},
        "chosen": {}, "row_f1_oracle": {}, "utility_oracle": {},
    }
    subsets = {"all": list(ids), "content_distinct": [], "all_parsed": [],
               "identical": [], "score_differing": []}
    positions, indices, oracle_sets = {}, {}, {}
    fallback, reason_lengths = Counter(), []
    selected_malformed = 0
    contact_hist = Counter()
    for sid in ids:
        record = receipt[sid]
        if record["distinct_answers"] == 1:
            subsets["identical"].append(sid)
        else:
            subsets["content_distinct"].append(sid)
            if record["parse_failed"] == 0:
                subsets["all_parsed"].append(sid)
        values = [row_f1[i][sid] for i in range(SAMPLES)]
        high = max(values)
        oracle_sets[sid] = tuple(i for i, value in enumerate(values) if abs(value - high) <= 1e-12)
        if high - min(values) > 1e-12:
            subsets["score_differing"].append(sid)
        arms["row_f1_oracle"][sid] = source[min(oracle_sets[sid])][sid]
        benefits = [utility(source[i][sid], f0) for i in range(SAMPLES)]
        best = max(benefits)
        utility_index = min(i for i, value in enumerate(benefits) if abs(value - best) <= 1e-12)
        arms["utility_oracle"][sid] = source[utility_index][sid]
        contact_count = verifier[sid].get("contact_count")
        if isinstance(contact_count, bool) or not isinstance(contact_count, int) or contact_count < 0:
            raise ReadError("verifier row contact_count is invalid")
        contact_hist[contact_count] += 1
        raw_text = verifier[sid].get("text")
        try:
            choice = parse_slurp_verifier_choice(
                raw_text, candidate_count=SAMPLES, max_reason_chars=160
            )
            position = choice["chosen_position"]
            index = record["permutation"][position - 1]
            reason_lengths.append(len(choice["reason"]))
        except ArtifactContentError as error:
            position, index = None, 0
            message = str(error)
            reason = ("missing_response" if not isinstance(raw_text, str) or not raw_text.strip()
                      else "invalid_position" if "position" in message
                      else "invalid_reason" if "reason" in message
                      else "invalid_json_or_shape")
            fallback[reason] += 1
        positions[sid], indices[sid] = position, index
        arms["chosen"][sid] = source[index][sid]
        selected_malformed += source_status[sid][index] != "ok"

    comparisons, intervals = {}, {}
    for name, members in subsets.items():
        if not members:
            comparisons[name] = {"rows": 0, "status": "EMPTY"}
            continue
        comparisons[name] = {key: summary([arm[sid] for sid in members])
                             for key, arm in arms.items()}
        intervals[name] = paired_ci(arms, members, utterances, draws, seed)
        chosen = comparisons[name]["chosen"]
        for key in ("mean_single", "sample0", "medoid", "row_f1_oracle", "utility_oracle"):
            row = comparisons[name][key]
            row["delta_chosen_minus_arm_slu_pp"] = chosen["slu_f1_pp"] - row["slu_f1_pp"]
            row["delta_chosen_minus_arm_intent_pp"] = chosen["intent_pp"] - row["intent_pp"]
    position_hist = {
        name: {str(i): sum(positions[sid] == i for sid in members)
               for i in range(1, SAMPLES + 1)} for name, members in subsets.items()
    }
    index_hist = {
        name: {str(i): sum(indices[sid] == i for sid in members)
               for i in range(SAMPLES)} for name, members in subsets.items()
    }
    oracle_agreement = {
        name: {
            "rows": len(members),
            "chosen_in_tie_set": sum(indices[sid] in oracle_sets[sid] for sid in members),
            "random_expected_share": (
                sum(len(oracle_sets[sid]) / SAMPLES for sid in members) / len(members)
                if members else None
            ),
        } for name, members in subsets.items()
    }
    scenarios = {}
    for stratum in sorted(set(strata.values())):
        members = [sid for sid in ids if strata[sid] == stratum]
        scenarios[stratum] = {
            "rows": len(members),
            "chosen": summary([arms["chosen"][sid] for sid in members]),
            "mean_single": summary([mean[sid] for sid in members]),
            "oracle_agreement": sum(indices[sid] in oracle_sets[sid] for sid in members) / len(members),
        }
    equal = {
        key: sum(row[arm][metric] for row in scenarios.values()) / len(scenarios)
        for key, arm, metric in (
            ("chosen_slu_f1_pp", "chosen", "slu_f1_pp"),
            ("mean_single_slu_f1_pp", "mean_single", "slu_f1_pp"),
            ("chosen_intent_pp", "chosen", "intent_pp"),
            ("mean_single_intent_pp", "mean_single", "intent_pp"),
        )
    }
    main_ci = intervals["all"]["mean_single"]
    control = position_hist["identical"]
    count = sum(control.values())
    expected = count / SAMPLES
    chi_square = (sum((value - expected) ** 2 / expected for value in control.values())
                  if expected else None)
    return {
        "schema": SCHEMA, "status": "DESCRIPTIVE", "rows": len(ids),
        "populations": {name: len(members) for name, members in subsets.items()},
        "comparisons": comparisons, "ci95": intervals,
        "choice": {
            "fallback_count": sum(fallback.values()),
            "contact_count_hist": dict(sorted(contact_hist.items())),
            "one_contact_every_row": contact_hist == Counter({1: len(ids)}),
            "fallback_reason_hist": dict(sorted(fallback.items())),
            "fallback_policy": "invalid choice -> sealed source index 0; all rows retained",
            "selected_malformed_source_count": selected_malformed,
            "selected_malformed_source_caveat": (
                "The selected malformed placeholder retains its sealed raw source-sample "
                "score. No answer is repaired or re-scored."
            ),
            "position_hist": position_hist, "source_index_hist": index_hist,
            "oracle_tie_set_hist": dict(sorted(Counter(map(len, oracle_sets.values())).items())),
            "oracle_agreement": oracle_agreement,
            "position_bias_control_chi_square_uniform": chi_square,
            "position_histogram_claim": "descriptive presentation diagnostic only",
            "reason_length": {
                "count": len(reason_lengths),
                "mean": sum(reason_lengths) / len(reason_lengths) if reason_lengths else None,
                "max": max(reason_lengths) if reason_lengths else None,
            },
        },
        "per_scenario": {
            "natural_mixture": {"chosen": comparisons["all"]["chosen"],
                                "mean_single": comparisons["all"]["mean_single"]},
            "equal_stratum": equal, "strata": scenarios,
        },
        "primary": {
            "benefit_status": ("positive_ci95" if main_ci["delta_slu_ci95_pp"][0] > 0
                               else "not_proven"),
            "slu_delta_ci95_pp": main_ci["delta_slu_ci95_pp"],
            "intent_noninferiority": (
                "UNRESOLVED" if margin is None
                else main_ci["delta_intent_ci95_pp"][0] >= -margin
            ),
            "intent_margin_pp": margin, "no_admission_claim": True,
        },
        "frozen_baseline_f0": f0,
        "bootstrap": {"draws": draws, "seed": seed, "cluster": "utterance_id", "paired": True},
        "cost": cost or {},
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0},
    }


def _jsonl(path):
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReadError(f"invalid JSONL input {path}: {error}") from error


def _render_source(record):
    if record.get("parse_status") != "ok":
        payload = None
    else:
        payload = record.get("parsed_answer")
        if not isinstance(payload, dict):
            raise ReadError("parsed source sample has no structured answer")
    if payload is None:
        body = {"scenario": "", "action": "", "entities": []}
    else:
        entities = payload.get("entities", [])
        if not isinstance(entities, list):
            raise ReadError("source answer entities are not a list")
        body = {
            "scenario": payload.get("scenario", ""),
            "action": payload.get("action", ""),
            "entities": [{"type": entity["type"], "filler": entity["filler"]}
                         for entity in entities],
        }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def bind_contact_counts(rows, trace_records, *, calls_used):
    """Derive per-row contacts from verified single-phase request traces.

    Include unsuccessful attempts and retries; preserve sealed output bytes.
    This verifier has no tool-derived or stitched request roots.
    """
    if not isinstance(trace_records, Mapping):
        raise ReadError("verifier trace records are unavailable")
    if isinstance(calls_used, bool) or not isinstance(calls_used, int) or calls_used < 0:
        raise ReadError("verifier generation cost is invalid")
    contacts = Counter()
    requests = {}
    for record_id, envelope in trace_records.items():
        if not record_id.endswith("/request"):
            continue
        payload = envelope.get("payload")
        if (not isinstance(envelope.get("arm"), str) or
                not isinstance(payload, Mapping)):
            raise ReadError("verifier request trace lacks a model envelope")
        request_id = record_id[:-len("/request")]
        sid = payload.get("sample_id")
        if sid not in rows or payload.get("request_id") != request_id:
            raise ReadError("verifier request trace identity differs from the roster")
        if request_id in requests:
            raise ReadError("duplicate verifier request trace identity")
        requests[request_id] = sid
        contacts[sid] += 1
    if sum(contacts.values()) != calls_used:
        raise ReadError("verifier trace contacts disagree with generation cost")
    enriched = {}
    for sid, row in rows.items():
        request_id = row.get("request_id")
        if requests.get(request_id) != sid:
            raise ReadError("verifier output lacks its own model request")
        if f"{request_id}/response" not in trace_records:
            raise ReadError("verifier output lacks its own model response")
        if "contact_count" in row and (
                isinstance(row["contact_count"], bool)
                or not isinstance(row["contact_count"], int)
                or row["contact_count"] != contacts[sid]):
            raise ReadError("verifier declared contact count disagrees with trace")
        enriched[sid] = dict(row, contact_count=contacts[sid])
    return enriched


def load_bound_inputs(
    *, manifest_path, source_manifest_path, receipt_path, expected_receipt_sha256,
    roster_path, score_root, scorer_id=SCORER, expected_rows=625, bundle_verifier=None,
    expected_run_id=RUN_ID,
):
    """Verify both bundles and every source/score/receipt identity before analysis."""
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.rails.phase_material import (
        balanced_sealed_sample_permutations,
    )
    import importlib.util
    aggregation_path = ROOT / "scripts" / "analysis" / "slurp_sample_aggregation_offline_read.py"
    spec = importlib.util.spec_from_file_location("slurp_sample_aggregation_offline_read", aggregation_path)
    aggregation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aggregation)
    build_arms = aggregation.build_arms

    if not isinstance(expected_run_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", expected_run_id) is None:
        raise ReadError("expected verifier run ID must be a plain identity")
    verifier = bundle_verifier or verify_bundle
    manifest_path = Path(manifest_path)
    source_manifest_path = Path(source_manifest_path)
    receipt_path = Path(receipt_path)
    roster_path = Path(roster_path)
    score_root = Path(score_root)
    if sha256_file(receipt_path) != expected_receipt_sha256:
        raise ReadError("permutation receipt SHA-256 differs from the registered input")
    receipt_doc = read_json(receipt_path)
    if receipt_doc.get("presentation", {}).get("permutation_rule_id") != "balanced-block-v1":
        raise ReadError("permutation receipt rule is not balanced-block-v1")
    presentation = receipt_doc["presentation"]
    if presentation.get("expected_sample_count") != SAMPLES:
        raise ReadError("permutation receipt sample count is not five")
    source_meta = receipt_doc.get("source")
    if not isinstance(source_meta, dict):
        raise ReadError("permutation receipt lacks source binding")
    if source_meta.get("manifest_sha256") != sha256_file(source_manifest_path):
        raise ReadError("source manifest SHA-256 differs from permutation receipt")
    if source_meta.get("roster_sha256") != sha256_file(roster_path):
        raise ReadError("roster SHA-256 differs from permutation receipt")
    source_bundle = verifier(source_manifest_path)
    chosen_bundle = verifier(manifest_path)
    for name, bundle in (("source", source_bundle), ("verifier", chosen_bundle)):
        if bundle.manifest.get("status") != "COMPLETED" or bundle.attempt_state != "FINALIZED":
            raise ReadError(f"{name} bundle is absent, partial, or not FINALIZED")
        if bundle.manifest.get("split", {}).get("role") != "discovery":
            raise ReadError(f"{name} bundle is not a discovery split")
    if source_bundle.manifest.get("run_id") != source_meta.get("rollout_run_id"):
        raise ReadError("source run ID differs from permutation receipt")
    if chosen_bundle.manifest.get("run_id") != expected_run_id:
        raise ReadError("verifier run ID differs from the registered expected identity")
    roster_doc = read_json(roster_path)
    items = roster_doc.get("items")
    if not isinstance(items, list) or len(items) != expected_rows:
        raise ReadError("roster row count differs from registration")
    ids = [item.get("sample_id") for item in items]
    if (any(not isinstance(sid, str) or not sid.startswith("slurp:train:") for sid in ids)
            or len(set(ids)) != len(ids)):
        raise ReadError("roster sample identities are not unique SLURP TRAIN ids")
    if (roster_doc.get("split_role") != "discovery" or
            roster_doc.get("split_identity_hash") != source_meta.get("split_identity_hash")):
        raise ReadError("roster split binding differs from permutation receipt")
    if set(source_bundle.split_ids) != set(ids) or set(chosen_bundle.split_ids) != set(ids):
        raise ReadError("bundle split identities differ from roster")
    source_rows = {row["sample_id"]: row for row in source_bundle.outputs_rows}
    chosen_rows = {row["sample_id"]: row for row in chosen_bundle.outputs_rows}
    exact_ids(ids, source_rows, "source bundle")
    exact_ids(ids, chosen_rows, "verifier bundle")
    receipt_rows = receipt_doc.get("rows")
    if not isinstance(receipt_rows, list) or len(receipt_rows) != len(ids):
        raise ReadError("permutation receipt is partial")
    receipt = {row.get("sample_id"): row for row in receipt_rows}
    exact_ids(ids, receipt, "permutation receipt")
    balanced = balanced_sealed_sample_permutations(
        tuple(source_rows), seed=presentation["permutation_seed"], count=SAMPLES
    )
    scores = {}
    score_hashes = {}
    render_manifest = read_json(score_root / "render-manifest.json")
    if render_manifest.get("samples") != SAMPLES:
        raise ReadError("source render manifest has wrong sample count")
    source_status = {}
    sealed = {}
    rendered_by_index = {}
    for sid in ids:
        group = source_rows[sid].get("solver_group")
        records = group.get("samples") if isinstance(group, dict) else None
        if not isinstance(records, list) or len(records) != SAMPLES:
            raise ReadError("source solver group is absent or partial")
        by_index = {record.get("sample_index"): record for record in records}
        if set(by_index) != set(range(SAMPLES)):
            raise ReadError("source solver group indices are incomplete")
        source_status[sid] = {i: by_index[i].get("parse_status") for i in range(SAMPLES)}
        sealed[sid] = {"samples": records}
        permutation = receipt[sid].get("permutation")
        if permutation != list(balanced[sid]):
            raise ReadError("committed permutation differs from balanced source assignment")
        expected_hashes = receipt[sid].get("rendered_sha256")
        hashes = [
            hashlib.sha256(_render_source(by_index[index]).encode("utf-8")).hexdigest()
            for index in permutation
        ]
        if hashes != expected_hashes:
            raise ReadError("committed rendered source hashes disagree with source group")
        rendered_by_index[sid] = {
            index: _render_source(by_index[index]) for index in range(SAMPLES)
        }
    for index in range(SAMPLES):
        entry = render_manifest.get("copies", {}).get(f"sample_{index}")
        if not isinstance(entry, dict):
            raise ReadError("source render manifest is missing a copy")
        copy_path = Path(entry.get("path", ""))
        if not copy_path.is_absolute():
            copy_path = score_root / copy_path
        if copy_path.resolve().parent != score_root.resolve():
            raise ReadError("source rendered copy lies outside the score root")
        if sha256_file(copy_path) != entry.get("sha256"):
            raise ReadError("source rendered copy hash mismatch")
        copied = _jsonl(copy_path)
        if len(copied) != len(ids):
            raise ReadError("source rendered copy has wrong row count")
        copy_rows = {row.get("sample_id"): row.get("text") for row in copied}
        exact_ids(ids, copy_rows, "source rendered copy")
        if any(copy_rows[sid] != rendered_by_index[sid][index] for sid in ids):
            raise ReadError("source rendered copy differs from sealed source group")
        score_path = score_root / f"sample_{index}-{scorer_id}-scores.json"
        score_hashes[str(index)] = sha256_file(score_path)
        score_doc = read_json(score_path)
        entry = score_doc.get(scorer_id)
        if not isinstance(entry, dict) or not entry.get("aggregate", {}).get(
            "identity_check", {}
        ).get("passed"):
            raise ReadError("source official score identity check is absent or failed")
        raw_scores = entry.get("per_sample")
        if not isinstance(raw_scores, list) or len(raw_scores) != len(ids):
            raise ReadError("source per-sample official scores are partial")
        scores[index] = {row.get("sample_id"): row for row in raw_scores}
        exact_ids(ids, scores[index], "source official scores")
        values = [extract_official_feedback(scores[index][sid]) for sid in ids]
        official = entry["aggregate"].get("official", {})
        if (abs(pooled_f1(values) - float(official.get("slu_f1", -1))) > 1e-6 or
            abs(sum(v.intent_exact for v in values)/len(values) -
                float(official.get("intent_accuracy", -1))) > 1e-6):
            raise ReadError("source official aggregate does not reproduce from sealed counts")
    medoid = build_arms(
        sealed, ids, SAMPLES, support_levels=(), threshold=0.8
    )["selection"]["R1-medoid"]
    strata = {item["sample_id"]: item.get("stratum") for item in items}
    utterances = {item["sample_id"]: item.get("utterance_id") for item in items}
    generation = read_json(
        manifest_path.parent / f"{expected_run_id}.generation-manifest.json"
    )
    cost = generation.get("cost")
    if not isinstance(cost, dict) or isinstance(cost.get("calls_used"), bool) or (
        not isinstance(cost.get("calls_used"), int)
        or cost["calls_used"] < 0
    ):
        raise ReadError("verifier generation cost is missing")
    chosen_rows = bind_contact_counts(
        chosen_rows, chosen_bundle.trace_records, calls_used=cost["calls_used"]
    )
    cost = {
        "calls_used": cost["calls_used"],
        "contacts_per_row": cost["calls_used"] / len(ids),
        "one_contact_per_row": cost["calls_used"] == len(ids),
        "prompt_tokens_total": cost.get("prompt_tokens_total"),
        "completion_tokens_total": cost.get("completion_tokens_total"),
    }
    flight_path = manifest_path.parent / "flight-receipts.json"
    if flight_path.exists():
        flight = read_json(flight_path)
        active = flight.get("stages", {}).get("seal", {}).get(
            "serving_monitor_summary", {}
        ).get("active_seconds")
        if isinstance(active, (int, float)) and not isinstance(active, bool):
            cost["gpu_active_hours"] = active / 3600
    bindings = {
        "verifier_run_id": expected_run_id,
        "contact_count_source": "verified_model_request_trace",
        "verifier_manifest_sha256": sha256_file(manifest_path),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "permutation_receipt_sha256": sha256_file(receipt_path),
        "roster_sha256": sha256_file(roster_path),
        "score_root": str(score_root),
        "render_manifest_sha256": sha256_file(score_root / "render-manifest.json"),
        "source_score_file_sha256": score_hashes,
        "scorer_id": scorer_id,
        "permutation_rule": "balanced-block-v1",
    }
    return ids, scores, receipt, chosen_rows, strata, utterances, medoid, source_status, cost, bindings


def run(*, manifest_path, source_manifest_path, receipt_path, expected_receipt_sha256,
        roster_path, score_root, out_root, scorer_id=SCORER,
        intent_ni_margin_pp=None, draws=DRAWS, seed=SEED, expected_rows=625,
        bundle_verifier=None, expected_run_id=RUN_ID):
    """Read and validate before creating the new analysis directory."""
    out_root = Path(out_root)
    if out_root.exists():
        raise ReadError(f"analysis output already exists: {out_root}")
    loaded = load_bound_inputs(
        manifest_path=manifest_path, source_manifest_path=source_manifest_path,
        receipt_path=receipt_path, expected_receipt_sha256=expected_receipt_sha256,
        roster_path=roster_path, score_root=score_root, scorer_id=scorer_id,
        expected_rows=expected_rows, bundle_verifier=bundle_verifier,
        expected_run_id=expected_run_id,
    )
    ids, scores, receipt, chosen, strata, utterances, medoid, source_status, cost, bindings = loaded
    report = analyze(
        ids, scores, receipt, chosen, strata, utterances, medoid, source_status,
        draws=draws, seed=seed, intent_ni_margin_pp=intent_ni_margin_pp,
        expected_rows=expected_rows, cost=cost,
    )
    report["bindings"] = bindings
    out_root.mkdir(parents=True, exist_ok=False)
    with (out_root / "report.json").open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, sort_keys=True, indent=2, ensure_ascii=True)
        stream.write("\n")
    all_rows = report["comparisons"]["all"]
    lines = [
        "# VERIFY-1 sealed selection read", "",
        "Status: DESCRIPTIVE. TRAIN construction data; no admission or test claim.", "",
        f"Rows: {report['rows']}; fallback choices: {report['choice']['fallback_count']}; "
        f"selected malformed source placeholders: {report['choice']['selected_malformed_source_count']}.",
        "", "| Population | n | chosen SLU-F1 | mean-single SLU-F1 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, count in report["populations"].items():
        cell = report["comparisons"][name]
        if count:
            lines.append(f"| {name} | {count} | {cell['chosen']['slu_f1_pp']:.2f} | "
                         f"{cell['mean_single']['slu_f1_pp']:.2f} |")
    lines += ["", f"Primary CI95 chosen minus mean-single: "
              f"{report['primary']['slu_delta_ci95_pp']}.",
              "Position histograms are descriptive presentation diagnostics only.",
              "The row-F1 oracle is label metric-limited; malformed source placeholders "
              "retain their sealed raw source score.", ""]
    (out_root / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "source-manifest", "receipt", "expected-receipt-sha256",
                 "roster", "source-score-root", "out-root"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    parser.add_argument("--scorer-id", default=SCORER)
    parser.add_argument("--expected-run-id", default=RUN_ID)
    parser.add_argument("--intent-ni-margin-pp", type=float)
    parser.add_argument("--draws", type=int, default=DRAWS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root) if args.data_root else None
    def location(value, base):
        path = Path(value)
        if path.is_absolute():
            return path
        if base is None:
            parser.error("--data-root is required for relative data paths")
        return base / path
    try:
        report = run(
            manifest_path=location(args.manifest, data_root),
            source_manifest_path=location(args.source_manifest, data_root),
            receipt_path=location(args.receipt, repo_root),
            expected_receipt_sha256=args.expected_receipt_sha256,
            roster_path=location(args.roster, repo_root),
            score_root=location(args.source_score_root, data_root),
            out_root=location(args.out_root, data_root), scorer_id=args.scorer_id,
            intent_ni_margin_pp=args.intent_ni_margin_pp,
            draws=args.draws, seed=args.seed, expected_run_id=args.expected_run_id,
        )
    except (ReadError, FeedbackError, OSError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    print(f"DESCRIPTIVE: {report['rows']} sealed selections; report written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
