#!/usr/bin/env python3
"""a2t_aa_paired_read.py -- the cell A2T-AA read: Audio2Tool's own
request-identical null on the paired 400 (recipe
``a2t-stage3-aa-paired-400-v1-own-null-read``,
``docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1/analysis-recipe-v1.json``).

Cell A2T-AA flew the sealed direct baseline (``a2t-native-role-direct-union4000-v1``)
twice in one chain on one resident Audio2Tool session -- pass A, then pass B --
on ``A2T-PAIRED-400-V1`` (50 rows per tier). This driver executes the recipe's
nine steps:

1. refuse unless both manifests are COMPLETED at 400 rows, both attempts
   FINALIZED, one study commit, one session receipt path, and each manifest's
   split identity hash and ordered id list equal the roster's (not a count);
2. request identity (``request_sha256`` equal, of 400), and -- because
   ``request_sha256`` binds dispatch envelope fields -- a diagnosis from the
   sealed trace's MODEL_REQUEST records: the content digest with the serving
   slot (``decoding_params.id_slot``) and the runtime request id removed, and
   byte identity split by same versus different slot;
3. byte identity (``response_text_sha256`` equal, of 400; every delivered text
   is re-hashed against its recorded digest and dropped), plus the counts of
   rows whose official primary tool and whose official verdicts differ;
4. the sealed per-sample scores of each pass (nothing is re-scored);
5. per-row deltas B minus A; pooled mean delta with a tier-stratified paired
   bootstrap CI95 (seed and draws from the recipe, the row as the resampling
   unit within tier) in the natural-mixture and the equal-tier weighting;
   h_A2T = the CI95 half-width on official tool accuracy;
6. per-tier and per-domain tables (domain from the released tier manifests at
   analysis time), the official (paper-protocol) column beside the repo column
   and the arXiv:2604.22821 Table 3 column beside the tier rows;
7. each pass joined to the sealed direct comparator rows of the same ids
   (identity counts and a paired delta with the same bootstrap), CONTEXT ONLY;
8. throughput per pass (decision 140) from the sealed dispatch receipt, the
   manifest's cost block and the session monitor samples inside each pass's
   contact window;
9. ``per_row.json`` and ``null.json`` under the analysis root.

DESCRIPTIVE. No verdict, no admission, no bar. MODEL-FREE: zero model,
tokenizer, encoder, scorer, server, GPU and network contacts. No query text,
transcript, gold tool, expected call, predicted call or model output is
printed or persisted: ids, tier and domain names, flags, scores, counts and
hashes only. Predicted tool names are compared in memory to derive a flip flag
and are never written.

Usage (WSL, the study venv, literal PYTHONPATH to the tree under test)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$TREE/src \\
    python -B scripts/analysis/a2t_aa_paired_read.py --repo-root $TREE \\
      --data-root $DATA --lock $UMBRELLA/docs/datasets.lock.json \\
      --analysis-root $DATA/analysis/SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

_DRIVER_REPO_ROOT = Path(__file__).resolve().parents[2]

RECIPE_RELPATH = "docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1/analysis-recipe-v1.json"
RECIPE_ID = "a2t-stage3-aa-paired-400-v1-own-null-read"
SCHEMA_PER_ROW = "saea-a2t-own-null-per-row-v1"
SCHEMA_NULL = "saea-a2t-own-null-v1"
EXPECTED_SESSION_ID = "serving-a2t-native-role-base-np3-max2048-v3"

OFFICIAL = "a2t-toolcall-official"
REPO = "a2t-toolcall"
REPO_V2 = "a2t-toolcall-v2"

#: arXiv:2604.22821 Table 3, Qwen3-Omni-30B (tool accuracy, exact match), as pinned in
#: docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-preregistration.md.
PAPER_TABLE_3 = {
    "tier1_direct": (92.4, 92.4),
    "tier2_parametric": (84.6, 15.6),
    "tier3_multi_intent": (74.7, 28.6),
    "tier4_implicit": (33.4, 11.3),
    "tier5_needle": (90.6, 36.0),
    "tier6_correction": (81.5, 24.8),
    "tier7_multiturn": (54.6, 16.3),
    "tier8_intent_blending": (41.7, 12.4),
}

#: per-row metrics: name -> (scorer id, per-sample field).
ROW_METRICS: dict[str, tuple[str, str]] = {
    "official_tool_accuracy": (OFFICIAL, "tool_correct"),
    "official_exact_match": (OFFICIAL, "exact_match"),
    "official_param_f1_macro": (OFFICIAL, "param_f1"),
    "official_parsed": (OFFICIAL, "parsed"),
    "repo_tool_accuracy": (REPO, "tool_accuracy"),
    "repo_exact_match": (REPO, "exact_match"),
    "repo_v2_ordered_tool_accuracy": (REPO_V2, "tool_accuracy"),
    "repo_v2_exact_match": (REPO_V2, "exact_match"),
}
HALF_WIDTH_METRICS = ("official_tool_accuracy", "official_exact_match", "repo_tool_accuracy")


class StopStageError(RuntimeError):
    """A sealed byte does not match what the recipe's step 1 must pin."""


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_outputs(path: Path, label: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for row in iter_jsonl(path):
        sid = row.get("sample_id")
        if not isinstance(sid, str) or not sid:
            raise StopStageError(f"{label}: an outputs row has no usable sample_id")
        if sid in rows:
            raise StopStageError(f"{label}: outputs repeat sample_id {sid!r}")
        text = row.get("text")
        recorded = row.get("response_text_sha256")
        if not isinstance(text, str) or not isinstance(recorded, str):
            raise StopStageError(f"{label}: outputs row {sid!r} lacks text/response_text_sha256")
        recomputed = hashlib.sha256(text.encode("utf-8")).hexdigest()  # the text is dropped here
        rows[sid] = {
            "request_sha256": row.get("request_sha256"),
            "response_text_sha256": recorded,
            "rehash_ok": recomputed == recorded,
        }
    return rows


#: Envelope fields of a MODEL_REQUEST payload that name the dispatch, not the model-visible
#: request: the serving slot the dispatcher assigned and the runtime's request id (plus the
#: per-contact id inside history entries). ``request_sha256`` binds them.
ENVELOPE_FIELDS = ("decoding_params.id_slot", "request_id", "history[].contact_id")


def _canonical_sha(obj: Any) -> str:
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_request_envelopes(trace_path: Path, label: str) -> dict[str, dict]:
    """Per sample: the recorded payload hash, the assigned slot, the request id's digest and a
    content digest with the ENVELOPE_FIELDS removed. Only digests and the slot integer are kept;
    no instruction, history or payload text leaves this function."""

    out: dict[str, dict] = {}
    for record in iter_jsonl(trace_path):
        if record.get("channel") != "MODEL_REQUEST":
            continue
        wrapper = record.get("payload") or {}
        payload = wrapper.get("payload") if isinstance(wrapper, Mapping) else None
        if not isinstance(payload, Mapping):
            continue
        sid = str(payload.get("sample_id"))
        if sid in out:
            raise StopStageError(f"{label}: more than one MODEL_REQUEST for {sid!r}")
        stripped = json.loads(json.dumps(payload))
        slot = (stripped.get("decoding_params") or {}).pop("id_slot", None)
        request_id = stripped.pop("request_id", None)
        for turn in stripped.get("history") or []:
            if isinstance(turn, dict):
                turn.pop("contact_id", None)
        out[sid] = {
            "payload_sha256": wrapper.get("payload_sha256"),
            "id_slot": slot,
            "request_id_sha256": _canonical_sha(request_id),
            "content_sha256_without_envelope": _canonical_sha(stripped),
        }
    return out


def per_sample(scores: Mapping[str, Any], scorer: str) -> dict[str, dict]:
    entry = scores.get(scorer)
    if not isinstance(entry, Mapping) or not isinstance(entry.get("per_sample"), list):
        raise StopStageError(f"sealed scores carry no per_sample block for {scorer!r}")
    return {str(r["sample_id"]): r for r in entry["per_sample"]}


class Arm:
    """One sealed pass: manifest, attempt record, outputs digests, per-sample scores."""

    def __init__(self, data_root: Path, label: str, run_id: str, attempt_id: str) -> None:
        self.label, self.run_id, self.attempt_id = label, run_id, attempt_id
        self.run_dir = data_root / "runs" / run_id / attempt_id
        self.manifest_path = self.run_dir / f"{run_id}.run-manifest.json"
        self.outputs_path = self.run_dir / f"{run_id}.outputs.jsonl"
        self.scores_path = self.run_dir / f"{run_id}.scores.json"
        self.attempt_path = data_root / "attempts" / run_id / f"{attempt_id}.json"
        for required in (self.manifest_path, self.outputs_path, self.scores_path):
            if not required.is_file():
                raise StopStageError(f"{label}: missing sealed file {required}")
        self.manifest = load_json(self.manifest_path)
        self.attempt = load_json(self.attempt_path) if self.attempt_path.is_file() else None
        self.rows = load_outputs(self.outputs_path, label)
        self.scores = load_json(self.scores_path)
        self.hashes = {
            "run_manifest_sha256": digest_file(self.manifest_path),
            "outputs_sha256": digest_file(self.outputs_path),
            "scores_sha256": digest_file(self.scores_path),
        }
        self.tables = {s: per_sample(self.scores, s) for s in (OFFICIAL, REPO, REPO_V2)}
        self.trace_path = self.run_dir / f"{run_id}.trace.jsonl"
        if not self.trace_path.is_file():
            raise StopStageError(f"{label}: missing sealed trace {self.trace_path}")
        self.envelopes = load_request_envelopes(self.trace_path, label)

    def metric(self, sid: str, name: str) -> float:
        scorer, field = ROW_METRICS[name]
        value = self.tables[scorer][sid].get(field)
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        return float(value or 0.0)

    def micro_counts(self, sid: str) -> tuple[int, int, int]:
        r = self.tables[OFFICIAL][sid]
        return (
            int(r.get("param_correct_keys") or 0),
            int(r.get("param_predicted_keys") or 0),
            int(r.get("param_gold_keys") or 0),
        )

    def primary_tool(self, sid: str) -> Any:
        return self.tables[OFFICIAL][sid].get("predicted_tool")


def step1_refusals(a: Arm, b: Arm, roster_ids: Sequence[str], split_identity: str) -> dict:
    findings: list[str] = []
    for arm in (a, b):
        if arm.manifest.get("status") != "COMPLETED":
            findings.append(f"{arm.label}: manifest status {arm.manifest.get('status')!r}")
        if arm.attempt is None or arm.attempt.get("state") != "FINALIZED":
            findings.append(f"{arm.label}: attempt not FINALIZED")
        split = arm.manifest.get("split") or {}
        if split.get("identity_hash") != split_identity:
            findings.append(f"{arm.label}: manifest split identity_hash differs from the roster")
        if list(split.get("ids") or []) != list(roster_ids):
            findings.append(f"{arm.label}: manifest ordered id list differs from the roster")
        if int(split.get("count") or 0) != 400 or len(arm.rows) != 400:
            findings.append(f"{arm.label}: not 400 rows")
        if set(arm.rows) != set(roster_ids):
            findings.append(f"{arm.label}: outputs ids differ from the roster ids")
        if arm.manifest.get("study_repo_dirt") not in ([], None):
            findings.append(f"{arm.label}: sealed with a dirty study tree")
        if (arm.manifest.get("scores") or {}).get("sha256") != arm.hashes["scores_sha256"]:
            findings.append(f"{arm.label}: manifest does not pin the sealed scores bytes")
        bad = [s for s, r in arm.rows.items() if not r["rehash_ok"]]
        if bad:
            findings.append(f"{arm.label}: {len(bad)} delivered texts do not re-hash")
    if a.manifest.get("study_commit") != b.manifest.get("study_commit"):
        findings.append("the two passes carry different study commits")
    pa = (a.manifest.get("session_receipt") or {}).get("path")
    pb = (b.manifest.get("session_receipt") or {}).get("path")
    if pa != pb or not pa or EXPECTED_SESSION_ID not in str(pa):
        findings.append("the two passes do not name one expected session receipt path")
    if findings:
        raise StopStageError("; ".join(findings))
    return {
        "both_completed_400": True,
        "both_attempts_finalized": True,
        "study_commit": a.manifest.get("study_commit"),
        "session_receipt_path": pa,
        "split_identity_hash": split_identity,
        "id_list_check": "manifest split.identity_hash equals the roster's and the ordered id list is equal",
        "delivered_text_rehash_ok": True,
    }


def _f1(c: float, p: float, g: float) -> float:
    prec = c / p if p else 0.0
    rec = c / g if g else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def bootstrap(
    deltas: dict[str, np.ndarray],
    tiers: np.ndarray,
    *,
    seed: int,
    draws: int,
    micro: tuple[np.ndarray, ...],
) -> dict[str, dict]:
    """Tier-stratified paired bootstrap; the row is the resampling unit within tier."""

    rng = np.random.default_rng(seed)
    tier_names = sorted(set(tiers.tolist()))
    tier_index = {t: np.flatnonzero(tiers == t) for t in tier_names}
    names = list(deltas)
    mat = np.stack([deltas[k] for k in names])  # metrics x rows
    nat = np.empty((len(names), draws))
    eq = np.empty((len(names), draws))
    micro_d = np.empty(draws)
    ca, pa, ga, cb, pb, gb = micro
    for i in range(draws):
        picks = [rng.choice(tier_index[t], size=len(tier_index[t]), replace=True) for t in tier_names]
        allp = np.concatenate(picks)
        nat[:, i] = mat[:, allp].mean(axis=1)
        eq[:, i] = np.mean([mat[:, p].mean(axis=1) for p in picks], axis=0)
        micro_d[i] = _f1(cb[allp].sum(), pb[allp].sum(), gb[allp].sum()) - _f1(
            ca[allp].sum(), pa[allp].sum(), ga[allp].sum()
        )

    def block(samples: np.ndarray, point: float) -> dict:
        lo, hi = float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))
        return {
            "mean_delta_pp": 100.0 * point,
            "ci95_pp": [100.0 * lo, 100.0 * hi],
            "ci95_half_width_pp": 100.0 * (hi - lo) / 2.0,
        }

    out: dict[str, dict] = {}
    for j, k in enumerate(names):
        v = deltas[k]
        point_eq = float(np.mean([v[tier_index[t]].mean() for t in tier_names]))
        out[k] = {
            "natural_mixture": block(nat[j], float(v.mean())),
            "equal_tier": block(eq[j], point_eq),
        }
    out["official_param_f1_micro"] = {
        "natural_mixture": block(micro_d, _f1(cb.sum(), pb.sum(), gb.sum()) - _f1(ca.sum(), pa.sum(), ga.sum())),
        "equal_tier": {"note": "micro F1 pools key counts over rows; an equal-tier weighting is not defined for it"},
    }
    return out


def paired_block(left: Arm, right: Arm, ids: Sequence[str], tiers: np.ndarray, *, seed: int, draws: int) -> dict:
    deltas = {
        k: np.array([right.metric(s, k) - left.metric(s, k) for s in ids], dtype=float) for k in ROW_METRICS
    }
    ca, pa, ga = (np.array(x, dtype=float) for x in zip(*(left.micro_counts(s) for s in ids)))
    cb, pb, gb = (np.array(x, dtype=float) for x in zip(*(right.micro_counts(s) for s in ids)))
    return bootstrap(deltas, tiers, seed=seed, draws=draws, micro=(ca, pa, ga, cb, pb, gb))


def level(arm: Arm, ids: Sequence[str]) -> dict:
    out = {k: 100.0 * float(np.mean([arm.metric(s, k) for s in ids])) for k in ROW_METRICS}
    counts = [arm.micro_counts(s) for s in ids]
    out["official_param_f1_micro"] = 100.0 * _f1(
        sum(c[0] for c in counts), sum(c[1] for c in counts), sum(c[2] for c in counts)
    )
    return out


def throughput(arm: Arm, monitor_path: Path) -> dict:
    receipts = load_json(arm.run_dir / "flight-receipts.json")
    rp = receipts["stages"]["run_phases"]
    window = rp["contact_window"]
    wall = float(window["to"]) - float(window["from"])
    cost = arm.manifest.get("cost") or {}
    contacts = int(rp["contact_count"])
    prompt = int(cost.get("prompt_tokens_total") or 0)
    completion = int(cost.get("completion_tokens_total") or 0)
    out: dict[str, Any] = {
        "contact_count": contacts,
        "contact_window_epoch": window,
        "generation_wall_seconds": round(wall, 3),
        "contacts_per_minute": round(contacts / (wall / 60.0), 2) if wall > 0 else None,
        "prompt_tokens_total": prompt,
        "completion_tokens_total": completion,
        "prompt_tokens_per_contact": round(prompt / contacts, 1) if contacts else None,
        "completion_tokens_per_contact": round(completion / contacts, 2) if contacts else None,
        "prompt_tokens_per_second": round(prompt / wall, 1) if wall > 0 else None,
        "runtime_contacts_per_second": rp.get("contacts_per_second"),
        "slot_occupancy": rp.get("slot_occupancy"),
        "serving_slots": rp.get("serving_slots"),
        "rows_answered_as_text": (rp.get("response_arrival") or {}).get("rows_answered_as_text"),
        "native_episode_dispositions": rp.get("native_episode_dispositions"),
    }
    if monitor_path.is_file():
        samples = [
            r for r in iter_jsonl(monitor_path)
            if float(window["from"]) <= float(r.get("sampled_at", 0)) <= float(window["to"])
        ]
        powers = [float(r["gpu"]["power_watts"]) for r in samples if r.get("gpu")]
        utils = [float(r["gpu"]["utilization_percent"]) for r in samples if r.get("gpu")]
        active = 0.0
        for prev, cur in zip(samples, samples[1:]):
            busy = ((prev.get("slots") or {}).get("busy") or 0) > 0
            if busy or float((prev.get("gpu") or {}).get("utilization_percent") or 0) >= 5.0:
                active += float(cur["sampled_at"]) - float(prev["sampled_at"])
        out["session_monitor_in_window"] = {
            "monitor_path": str(monitor_path),
            "samples": len(samples),
            "active_seconds_approx": round(active, 1),
            "mean_power_watts": round(float(np.mean(powers)), 2) if powers else None,
            "peak_power_watts": max(powers) if powers else None,
            "mean_utilization_percent": round(float(np.mean(utils)), 2) if utils else None,
            "definition": (
                "monitor samples whose sampled_at falls inside the pass's sealed contact window; "
                "an interval counts as active when the sample opening it shows a busy slot or "
                "utilization >= 5 %"
            ),
        }
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--repo-root", default=str(_DRIVER_REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock", required=True, help="the umbrella docs/datasets.lock.json")
    parser.add_argument("--analysis-root", required=True)
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    data = Path(args.data_root).resolve()
    recipe = load_json(repo / RECIPE_RELPATH)
    if recipe.get("recipe_id") != RECIPE_ID:
        raise StopStageError("recipe id mismatch")
    seed = int(recipe["interval"]["seed"])
    draws = int(recipe["interval"]["draws"])
    roster_doc = load_json(repo / recipe["roster"]["relpath"])
    roster_ids = [str(i["sample_id"]) for i in roster_doc["items"]]
    tier_of = {str(i["sample_id"]): str(i["tier"]) for i in roster_doc["items"]}
    split_identity = recipe["roster"]["split_identity_hash"]
    comp_rows = load_json(repo / recipe["roster"]["comparator_rows"])["rows"]

    arms = recipe["arms"]
    a = Arm(data, "pass_a", arms["pass_a"]["run_id"], arms["pass_a"]["attempt_id"])
    b = Arm(data, "pass_b", arms["pass_b"]["run_id"], arms["pass_b"]["attempt_id"])
    comp = arms["sealed_direct_comparator"]
    d = Arm(data, "direct", comp["run_id"], comp["attempt_id"])
    if (
        d.hashes["outputs_sha256"] != comp["outputs"]["sha256"]
        or d.hashes["scores_sha256"] != comp["scores"]["sha256"]
        or d.hashes["run_manifest_sha256"] != comp["run_manifest"]["sha256"]
    ):
        raise StopStageError("sealed direct comparator bytes differ from the recipe's pins")

    stop = step1_refusals(a, b, roster_ids, split_identity)

    if str(repo / "src") not in sys.path:
        sys.path.insert(0, str(repo / "src"))
    from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import (  # noqa: PLC0415
        domains_by_sample_id,
    )
    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    domain_of = domains_by_sample_id(load_lock(Path(args.lock)), data, roster_ids)

    ids = roster_ids
    tiers = np.array([tier_of[s] for s in ids])
    records: list[dict] = []
    for sid in ids:
        ra, rb = a.rows[sid], b.rows[sid]
        records.append({
            "sample_id": sid,
            "tier": tier_of[sid],
            "domain": domain_of[sid],
            "a_request_sha256": ra["request_sha256"],
            "b_request_sha256": rb["request_sha256"],
            "a_response_text_sha256": ra["response_text_sha256"],
            "b_response_text_sha256": rb["response_text_sha256"],
            "request_identical": ra["request_sha256"] == rb["request_sha256"],
            "request_content_identical_without_envelope": (
                a.envelopes[sid]["content_sha256_without_envelope"]
                == b.envelopes[sid]["content_sha256_without_envelope"]
            ),
            "a_id_slot": a.envelopes[sid]["id_slot"],
            "b_id_slot": b.envelopes[sid]["id_slot"],
            "same_slot": a.envelopes[sid]["id_slot"] == b.envelopes[sid]["id_slot"],
            "request_id_differs": a.envelopes[sid]["request_id_sha256"] != b.envelopes[sid]["request_id_sha256"],
            "trace_payload_hash_matches_outputs": (
                a.envelopes[sid]["payload_sha256"] == ra["request_sha256"]
                and b.envelopes[sid]["payload_sha256"] == rb["request_sha256"]
            ),
            "byte_identical": ra["response_text_sha256"] == rb["response_text_sha256"],
            "primary_tool_differs": a.primary_tool(sid) != b.primary_tool(sid),
            "official_tool_verdict_differs": a.metric(sid, "official_tool_accuracy")
            != b.metric(sid, "official_tool_accuracy"),
            "official_exact_verdict_differs": a.metric(sid, "official_exact_match")
            != b.metric(sid, "official_exact_match"),
            "request_content_identical_to_direct_without_envelope": {
                "a": a.envelopes[sid]["content_sha256_without_envelope"]
                == d.envelopes[sid]["content_sha256_without_envelope"],
                "b": b.envelopes[sid]["content_sha256_without_envelope"]
                == d.envelopes[sid]["content_sha256_without_envelope"],
            },
            "request_identical_to_direct": {
                "a": ra["request_sha256"] == comp_rows[sid]["request_sha256"],
                "b": rb["request_sha256"] == comp_rows[sid]["request_sha256"],
            },
            "byte_identical_to_direct": {
                "a": ra["response_text_sha256"] == comp_rows[sid]["response_text_sha256"],
                "b": rb["response_text_sha256"] == comp_rows[sid]["response_text_sha256"],
            },
            "a": {k: a.metric(sid, k) for k in ROW_METRICS},
            "b": {k: b.metric(sid, k) for k in ROW_METRICS},
            "direct": {k: d.metric(sid, k) for k in ROW_METRICS},
            "delta_b_minus_a": {k: b.metric(sid, k) - a.metric(sid, k) for k in ROW_METRICS},
        })

    n = len(records)
    req_ident = sum(r["request_identical"] for r in records)
    byte_ident = sum(r["byte_identical"] for r in records)
    pair = paired_block(a, b, ids, tiers, seed=seed, draws=draws)

    def table(key: str, groups: dict[str, list[str]]) -> dict:
        out = {}
        for g, sids in sorted(groups.items()):
            la, lb, ld = level(a, sids), level(b, sids), level(d, sids)
            row: dict[str, Any] = {
                "rows": len(sids),
                "byte_identical": sum(1 for r in records if r[key] == g and r["byte_identical"]),
                "pass_a": la,
                "pass_b": lb,
                "direct_sealed": ld,
                "delta_b_minus_a_pp": {k: lb[k] - la[k] for k in la},
            }
            if key == "tier" and g in PAPER_TABLE_3:
                row["paper_table3_tool_accuracy"], row["paper_table3_exact_match"] = PAPER_TABLE_3[g]
            out[g] = row
        return out

    by_tier: dict[str, list[str]] = {}
    by_domain: dict[str, list[str]] = {}
    for r in records:
        by_tier.setdefault(r["tier"], []).append(r["sample_id"])
        by_domain.setdefault(r["domain"], []).append(r["sample_id"])

    monitor = Path(str((a.manifest.get("session_receipt") or {}).get("path", ""))).parent / "monitor.jsonl"
    null: dict[str, Any] = {
        "schema": SCHEMA_NULL,
        "recipe_id": RECIPE_ID,
        "recipe_relpath": RECIPE_RELPATH,
        "recipe_sha256": digest_file(repo / RECIPE_RELPATH),
        "interval": {"draws": draws, "seed": seed, "level": "CI95", "stratification": "tier"},
        "run_ids": {"pass_a": a.run_id, "pass_b": b.run_id, "direct": d.run_id},
        "sealed_hashes": {"pass_a": a.hashes, "pass_b": b.hashes, "direct": d.hashes},
        "step1_refusals": stop,
        "step2_request_identity": {
            "identical": req_ident,
            "rows": n,
            "request_identical_pair": req_ident == n,
            "rule": (
                "recipe step 2: the pair is read as request-identical only at 400 of 400; any other count "
                "is reported as the finding and the null is NOT registered from it"
            ),
            "diagnosis": {
                "envelope_fields_removed": list(ENVELOPE_FIELDS),
                "content_identical_without_envelope": sum(
                    r["request_content_identical_without_envelope"] for r in records
                ),
                "rows_differing_only_in_envelope": sum(
                    (not r["request_identical"]) and r["request_content_identical_without_envelope"]
                    for r in records
                ),
                "same_slot_rows": sum(r["same_slot"] for r in records),
                "request_id_differs_rows": sum(r["request_id_differs"] for r in records),
                "trace_payload_hash_matches_outputs_rows": sum(
                    r["trace_payload_hash_matches_outputs"] for r in records
                ),
                "byte_identical_given_same_slot": [
                    sum(r["byte_identical"] for r in records if r["same_slot"]),
                    sum(r["same_slot"] for r in records),
                ],
                "byte_identical_given_different_slot": [
                    sum(r["byte_identical"] for r in records if not r["same_slot"]),
                    sum(not r["same_slot"] for r in records),
                ],
                "source": "the MODEL_REQUEST records of each pass's sealed trace.jsonl, digests only",
            },
        },
        "step3_byte_identity": {
            "identical": byte_ident,
            "rows": n,
            "primary_tool_differs": sum(r["primary_tool_differs"] for r in records),
            "official_tool_verdict_differs": sum(r["official_tool_verdict_differs"] for r in records),
            "official_exact_verdict_differs": sum(r["official_exact_verdict_differs"] for r in records),
            "non_identical_sample_ids": [r["sample_id"] for r in records if not r["byte_identical"]],
        },
        "step4_levels": {
            "pass_a": level(a, ids),
            "pass_b": level(b, ids),
            "direct_sealed_same_ids": level(d, ids),
        },
        "step5_paired_b_minus_a": pair,
        "h_A2T": {
            "natural_mixture_pp": {k: pair[k]["natural_mixture"]["ci95_half_width_pp"] for k in HALF_WIDTH_METRICS},
            "equal_tier_pp": {k: pair[k]["equal_tier"]["ci95_half_width_pp"] for k in HALF_WIDTH_METRICS},
            "registered_names": {
                "h_A2T": "official_tool_accuracy",
                "h_A2T_em": "official_exact_match",
                "h_A2T_repo": "repo_tool_accuracy",
            },
            "null_registered_by_recipe_letter": req_ident == n,
            "note": (
                "valid at n = 400 on A2T-PAIRED-400-V1 under the c98304 np3 x 32,768 max2048 geometry with the "
                "sealed direct baseline's request form; with 50 rows in every tier the two weightings coincide "
                "in the point estimate"
            ),
        },
        "step6_per_tier": table("tier", by_tier),
        "step6_per_domain": table("domain", by_domain),
        "step7_comparator_context": {
            "what": "CONTEXT ONLY, never a gate: each pass joined to the sealed direct rows of the same ids",
            "request_content_identical_to_direct_without_envelope": {
                "pass_a": sum(r["request_content_identical_to_direct_without_envelope"]["a"] for r in records),
                "pass_b": sum(r["request_content_identical_to_direct_without_envelope"]["b"] for r in records),
            },
            "request_identical_to_direct": {
                "pass_a": sum(r["request_identical_to_direct"]["a"] for r in records),
                "pass_b": sum(r["request_identical_to_direct"]["b"] for r in records),
            },
            "byte_identical_to_direct": {
                "pass_a": sum(r["byte_identical_to_direct"]["a"] for r in records),
                "pass_b": sum(r["byte_identical_to_direct"]["b"] for r in records),
            },
            "paired_pass_a_minus_direct": paired_block(d, a, ids, tiers, seed=seed, draws=draws),
            "paired_pass_b_minus_direct": paired_block(d, b, ids, tiers, seed=seed, draws=draws),
        },
        "step8_throughput": {"pass_a": throughput(a, monitor), "pass_b": throughput(b, monitor)},
        "claim_boundary": recipe["claim_boundary"],
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0, "gpu": 0, "network": 0},
        "privacy": recipe["privacy"],
    }
    per_row = {"schema": SCHEMA_PER_ROW, "recipe_id": RECIPE_ID, "rows": records}
    root = Path(args.analysis_root)
    written = {
        "per_row.json": write_json(root / "per_row.json", per_row),
        "null.json": write_json(root / "null.json", null),
    }
    print(json.dumps({"written": written, "analysis_root": str(root)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StopStageError as error:
        print(f"a2t_aa_paired_read: STOP: {error}", file=sys.stderr)
        raise SystemExit(2) from None
