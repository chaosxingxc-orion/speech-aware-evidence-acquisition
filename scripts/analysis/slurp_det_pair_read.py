#!/usr/bin/env python3
"""slurp_det_pair_read.py -- the cell DET read: per-row byte identity of the
delivered answer between two request-identical passes of the locked plan.

Cell DET (``docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1/``)
flies the locked v2.0 plan twice in one chain -- pass A, then pass B -- on the
first 50 rows of TRAIN Fold A, on a single-slot, prompt-cache-off serving
geometry. This driver answers the one question the cell asks: on how many of
the 50 rows are the two delivered answers the SAME BYTES?

Stages (``--stage stop|read|all``):

  stop   verify both attempts are FINALIZED, both manifests COMPLETED and
         sealed with a clean study tree, both manifests bind the roster's
         split identity, both outputs files carry exactly the roster's ids,
         and every outputs row's delivered ``text`` re-hashes to its recorded
         ``response_text_sha256`` (so "byte identity" below is literally over
         the delivered bytes). Refuses loudly on any mismatch; writes
         ``stop.json``.
  read   per row: the two delivered digests and whether they are equal; when
         the sealed official per-sample scores exist, each pass's
         ``slu_f1_f1`` and ``scenario_action_exact`` and their paired delta;
         when the per-sample rows carry the scorer's ``parsed`` prediction,
         whether the (scenario, action) pair and the entity SET differ. Pooled
         paired deltas with a CI95 by row bootstrap (seed 20260915, 10,000
         draws). Writes ``per_row.json`` and ``summary.json``.

DESCRIPTIVE. There is no verdict, no admission and no comparator: the cell is
its own control. The registered decision rule is a routing rule, not a claim:
50 of 50 identical rows means the between-flight offset is an artefact of
batch composition and cache state and the 200-row floor re-estimate is worth
flying; anything less means the offset is intrinsic to the model's numerics on
this hardware. A 50-row cell cannot support a floor re-estimate.

MODEL-FREE. Zero model, tokenizer, encoder, scorer, server, GPU and network
contacts: every byte it reads is already sealed, and it opens each file
read-only. No utterance text, transcript, gold label, delivered filler or
model output is ever printed or persisted: ``per_row.json`` and
``summary.json`` carry ids, stratum names, digests, flags, scores and counts
only. The delivered text is read into memory ONLY to re-hash it against its
recorded digest and is discarded.

Usage (from WSL, the study venv)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=... \\
    python -B scripts/analysis/slurp_det_pair_read.py --stage all \\
      --left-run SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1 \\
      --left-attempt attempt-slurp-native-stage3-det-np1-fold-a-50-a-generation-v1 \\
      --right-run SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1 \\
      --right-attempt attempt-slurp-native-stage3-det-np1-fold-a-50-b-generation-v1 \\
      --roster docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json \\
      --repo-root $REPO --data-root $DATA --analysis-root $DATA/analysis/<read id>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

_DRIVER_REPO_ROOT = Path(__file__).resolve().parents[2]

SCHEMA_STOP = "saea-slurp-det-pair-read-stop-v1"
SCHEMA_PER_ROW = "saea-slurp-det-pair-read-per-row-v1"
SCHEMA_SUMMARY = "saea-slurp-det-pair-read-summary-v1"
RECIPE_ID = "slurp-stage3-det-np1-fold-a-50-pair-read-v1"

DEFAULT_SCORER = "slurp-slu-official-train"
DEFAULT_SEED = 20260915
DEFAULT_DRAWS = 10000

#: Context reported beside the number, never a comparator and never a gate.
REPORTED_BESIDE = {
    "roll_aa_within_flight_np4": {
        "byte_identical_rows": 183,
        "rows": 200,
        "share": 0.915,
        "intent_flips": 0,
        "entity_set_flips": 15,
        "source": "docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md",
        "what": (
            "two greedy passes of one Solver visit INSIDE one flight, np4 x 24,576 with the "
            "prompt cache on"
        ),
    },
    "cross_flight_np4": {
        "raw_output_disagreement_share_about": 0.28,
        "intent_disagreement_share_about": 0.05,
        "var1_plan_vs_planr_slu_pp": 1.87,
        "var1_plan_vs_planr_ci95_pp": [0.41, 3.36],
        "var1_plan_vs_planr_intent_pp": -1.28,
        "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2b",
        "what": (
            "two request-identical FLIGHTS of the locked plan, np4 x 24,576 with the prompt "
            "cache on; the between-flight offset this cell tests"
        ),
    },
    "note": (
        "CONTEXT ONLY. The within-flight and cross-flight np4 numbers were measured on other "
        "rosters at other n; the comparison the programme wants is qualitative: does the "
        "delivered answer repeat byte for byte when batch composition and cache state are "
        "removed?"
    ),
}

#: Owner decision 140 (2026-09-26): the np1 cache-off test is authorised as a cheap
#: test, but ADOPTION of any geometry is decided on THROUGHPUT, because future rounds
#: need massive sampling. The resident np4 geometry's reference throughput is cell
#: ROLL-2's sealed arm: 8,996 contacts and 81,435,827 prompt tokens between
#: 16:00:01Z and 18:22:39Z (8,558 s). Both DET passes report the same two numbers
#: from their own sealed dispatch window so the trade is one table.
ROLL_2_NP4_REFERENCE = {
    "run_id": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1",
    "geometry": "np4 x 24,576, prompt cache on (the resident geometry)",
    "contacts": 8996,
    "prompt_tokens": 81435827,
    "arm_window_utc": ["16:00:01Z", "18:22:39Z"],
    "wall_seconds": 8558,
    "contacts_per_minute": round(8996 / (8558 / 60.0), 2),
    "prompt_tokens_per_second": round(81435827 / 8558.0, 1),
    "window_definition": (
        "the arm's wall window as the coordinator recorded it (first to last contact of the "
        "arm); the DET passes use the sealed dispatch contact_window of each attempt, which is "
        "the same interval measured by the runtime's own clock and excludes model load"
    ),
}


def _throughput(arm: "Arm") -> dict[str, Any]:
    """Contacts per minute and prompt tokens per second from the SEALED dispatch
    window (``flight-receipts.json``: ``wall_seconds`` / ``contact_window`` /
    ``contact_count``) and the sealed generation manifest's cost block
    (``prompt_tokens_total``, ``completion_tokens_total``, ``calls_used``)."""

    receipts_path = arm.run_dir / "flight-receipts.json"
    generation_path = arm.run_dir / f"{arm.run_id}.generation-manifest.json"
    out: dict[str, Any] = {
        "run_id": arm.run_id,
        "flight_receipts_present": receipts_path.is_file(),
        "generation_manifest_present": generation_path.is_file(),
    }
    dispatch: Mapping[str, Any] | None = None
    if receipts_path.is_file():
        document = load_json(receipts_path)
        stages = document.get("stages") if isinstance(document, Mapping) else None
        candidates = list(stages.values()) if isinstance(stages, Mapping) else (
            document if isinstance(document, list) else []
        )
        for payload in candidates:
            if isinstance(payload, Mapping) and "wall_seconds" in payload and "contact_window" in payload:
                dispatch = payload
                break
    cost: Mapping[str, Any] = {}
    if generation_path.is_file():
        generation = load_json(generation_path)
        cost = generation.get("cost") or {} if isinstance(generation, Mapping) else {}
    if dispatch is not None:
        wall = float(dispatch.get("wall_seconds") or 0.0)
        contacts = dispatch.get("contact_count")
        out.update({
            "wall_seconds": wall,
            "contact_window": dispatch.get("contact_window"),
            "contact_count": contacts,
            "serving_slots": dispatch.get("serving_slots"),
            "occupancy_slots": dispatch.get("occupancy_slots"),
            "runtime_contacts_per_second": dispatch.get("contacts_per_second"),
        })
        prompt_tokens = cost.get("prompt_tokens_total")
        out["prompt_tokens_total"] = prompt_tokens
        out["completion_tokens_total"] = cost.get("completion_tokens_total")
        out["calls_used"] = cost.get("calls_used")
        if wall > 0 and isinstance(contacts, (int, float)):
            out["contacts_per_minute"] = round(float(contacts) / (wall / 60.0), 2)
        if wall > 0 and isinstance(prompt_tokens, (int, float)):
            out["prompt_tokens_per_second"] = round(float(prompt_tokens) / wall, 1)
    return out


class StopStageError(RuntimeError):
    """A sealed byte does not match what the stop stage must pin."""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


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


@dataclass(frozen=True)
class Arm:
    label: str
    run_id: str
    attempt_id: str
    run_dir: Path
    attempt_record: dict
    manifest: dict
    manifest_sha256: str
    scores: dict | None
    scores_sha256: str | None
    outputs_path: Path
    outputs_sha256: str
    rows: dict[str, dict]  # sample_id -> {response_text_sha256, text_sha256_recomputed}


def load_arm(data_root: Path, label: str, run_id: str, attempt_id: str) -> Arm:
    run_dir = data_root / "runs" / run_id / attempt_id
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    scores_path = run_dir / f"{run_id}.scores.json"
    attempt_path = data_root / "attempts" / run_id / f"{attempt_id}.json"
    for required in (manifest_path, outputs_path, attempt_path):
        if not required.is_file():
            raise StopStageError(f"{label}: missing required sealed file {required}")
    rows: dict[str, dict] = {}
    for row in iter_jsonl(outputs_path):
        sid = row.get("sample_id")
        if not isinstance(sid, str) or not sid:
            raise StopStageError(f"{label}: an outputs row has no usable sample_id")
        if sid in rows:
            raise StopStageError(f"{label}: outputs repeat sample_id {sid!r}")
        recorded = row.get("response_text_sha256")
        text = row.get("text")
        if not isinstance(recorded, str) or not isinstance(text, str):
            raise StopStageError(
                f"{label}: outputs row {sid!r} carries no text/response_text_sha256 pair"
            )
        # The text is hashed and dropped; it is never kept, printed or written.
        recomputed = hashlib.sha256(text.encode("utf-8")).hexdigest()
        rows[sid] = {
            "response_text_sha256": recorded,
            "text_sha256_recomputed": recomputed,
            "text_bytes": len(text.encode("utf-8")),
        }
    return Arm(
        label=label,
        run_id=run_id,
        attempt_id=attempt_id,
        run_dir=run_dir,
        attempt_record=load_json(attempt_path),
        manifest=load_json(manifest_path),
        manifest_sha256=digest_file(manifest_path),
        scores=load_json(scores_path) if scores_path.is_file() else None,
        scores_sha256=digest_file(scores_path) if scores_path.is_file() else None,
        outputs_path=outputs_path,
        outputs_sha256=digest_file(outputs_path),
        rows=rows,
    )


@dataclass(frozen=True)
class Roster:
    relpath: str
    sha256: str
    ids: tuple[str, ...]
    carrier_lock_key: str
    split_identity_hash: str
    stratum_of: dict[str, str]


def load_roster(repo_root: Path, relpath: str) -> Roster:
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from speech_aware_evidence_acquisition.core.roster import verify_roster  # noqa: PLC0415

    path = repo_root / relpath
    if not path.is_file():
        raise StopStageError(f"roster not found at {path}")
    document = load_json(path)
    measured = verify_roster(document)
    ids = tuple(str(item["sample_id"]) for item in document["items"])
    return Roster(
        relpath=relpath,
        sha256=digest_file(path),
        ids=ids,
        carrier_lock_key=str(document["carrier_lock_key"]),
        split_identity_hash=measured,
        stratum_of={str(item["sample_id"]): str(item.get("stratum")) for item in document["items"]},
    )


# --------------------------------------------------------------------------
# stop
# --------------------------------------------------------------------------


def stage_stop(left: Arm, right: Arm, roster: Roster, *, expected_session_id: str | None) -> dict:
    findings: list[str] = []
    for arm in (left, right):
        if arm.attempt_record.get("state") != "FINALIZED":
            findings.append(f"{arm.label}: attempt state is {arm.attempt_record.get('state')!r}")
        if arm.manifest.get("status") != "COMPLETED":
            findings.append(f"{arm.label}: manifest status is {arm.manifest.get('status')!r}")
        if arm.manifest.get("study_repo_dirt") not in ([], None):
            findings.append(f"{arm.label}: manifest sealed with a dirty study tree")
        split = arm.manifest.get("split") or {}
        if split.get("identity_hash") != roster.split_identity_hash:
            findings.append(f"{arm.label}: manifest split identity_hash does not match the roster")
        if set(arm.rows) != set(roster.ids):
            missing = sorted(set(roster.ids) - set(arm.rows))[:5]
            extra = sorted(set(arm.rows) - set(roster.ids))[:5]
            findings.append(
                f"{arm.label}: outputs ids do not equal the roster ids (missing {missing}, extra {extra})"
            )
        bad_hash = [
            sid for sid, row in arm.rows.items()
            if row["response_text_sha256"] != row["text_sha256_recomputed"]
        ]
        if bad_hash:
            findings.append(
                f"{arm.label}: {len(bad_hash)} outputs row(s) whose text does not re-hash to its "
                f"recorded response_text_sha256 (first: {bad_hash[:3]})"
            )
        if arm.scores is not None:
            pin = arm.manifest.get("scores") or {}
            if pin.get("sha256") not in (None, arm.scores_sha256):
                findings.append(f"{arm.label}: manifest does not pin the sealed score bytes")
    if expected_session_id is not None:
        for arm in (left, right):
            named = json.dumps(arm.manifest, sort_keys=True)
            if expected_session_id not in named:
                findings.append(
                    f"{arm.label}: manifest does not name the expected serving session "
                    f"{expected_session_id!r}"
                )
    same_commit = left.manifest.get("study_commit") == right.manifest.get("study_commit")
    if findings:
        raise StopStageError("; ".join(findings))
    return {
        "schema": SCHEMA_STOP,
        "recipe_id": RECIPE_ID,
        "roster": {
            "relpath": roster.relpath,
            "sha256": roster.sha256,
            "rows": len(roster.ids),
            "split_identity_hash": roster.split_identity_hash,
        },
        "arms": {
            arm.label: {
                "run_id": arm.run_id,
                "attempt_id": arm.attempt_id,
                "manifest_sha256": arm.manifest_sha256,
                "outputs_sha256": arm.outputs_sha256,
                "scores_sha256": arm.scores_sha256,
                "study_commit": arm.manifest.get("study_commit"),
                "config_hash": arm.manifest.get("config_hash")
                or (arm.manifest.get("plan") or {}).get("config_hash"),
                "rows": len(arm.rows),
                "delivered_text_rehash_ok": True,
            }
            for arm in (left, right)
        },
        "same_study_commit": same_commit,
        "expected_session_id": expected_session_id,
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0},
    }


# --------------------------------------------------------------------------
# read
# --------------------------------------------------------------------------


def _per_sample(arm: Arm, scorer_id: str) -> dict[str, dict] | None:
    if arm.scores is None:
        return None
    entry = arm.scores.get(scorer_id)
    if not isinstance(entry, dict) or not isinstance(entry.get("per_sample"), list):
        return None
    table: dict[str, dict] = {}
    for row in entry["per_sample"]:
        sid = row.get("sample_id")
        if isinstance(sid, str) and sid:
            table[sid] = row
    return table


def _entity_key(parsed: Any) -> tuple | None:
    if not isinstance(parsed, Mapping):
        return None
    entities = parsed.get("entities")
    if not isinstance(entities, list):
        return None
    return tuple(sorted(
        (str(e.get("type", "")).strip().lower(), " ".join(str(e.get("filler", "")).split()).lower())
        for e in entities if isinstance(e, Mapping)
    ))


def _intent_key(parsed: Any) -> tuple | None:
    if not isinstance(parsed, Mapping):
        return None
    if "scenario" not in parsed or "action" not in parsed:
        return None
    return (str(parsed.get("scenario")), str(parsed.get("action")))


def _bootstrap_block(values: Sequence[float], *, seed: int, draws: int) -> dict:
    n = len(values)
    if n == 0:
        return {"n": 0}
    rng = random.Random(seed)
    means = []
    for _ in range(draws):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(0.025 * draws)]
    hi = means[max(int(0.975 * draws) - 1, 0)]
    return {
        "n": n,
        "mean_pp": 100.0 * sum(values) / n,
        "sd_pp": 100.0 * (statistics.pstdev(values) if n > 1 else 0.0),
        "ci95_pp": [100.0 * lo, 100.0 * hi],
        "ci95_half_width_pp": 100.0 * (hi - lo) / 2.0,
        "draws": draws,
        "seed": seed,
        "unit": "row (paired: both passes of a row move together)",
    }


def stage_read(
    left: Arm, right: Arm, roster: Roster, *, scorer_id: str, seed: int, draws: int
) -> tuple[dict, dict]:
    left_scores = _per_sample(left, scorer_id)
    right_scores = _per_sample(right, scorer_id)
    scored = left_scores is not None and right_scores is not None
    records: list[dict] = []
    for sid in roster.ids:
        a, b = left.rows[sid], right.rows[sid]
        record: dict[str, Any] = {
            "sample_id": sid,
            "stratum": roster.stratum_of.get(sid),
            "left_response_text_sha256": a["response_text_sha256"],
            "right_response_text_sha256": b["response_text_sha256"],
            "byte_identical": a["response_text_sha256"] == b["response_text_sha256"],
            "left_text_bytes": a["text_bytes"],
            "right_text_bytes": b["text_bytes"],
        }
        if scored:
            la, lb = left_scores.get(sid), right_scores.get(sid)
            if la is None or lb is None:
                raise StopStageError(f"per-sample score row missing for {sid!r}")
            slu_a, slu_b = float(la.get("slu_f1_f1", 0.0)), float(lb.get("slu_f1_f1", 0.0))
            int_a, int_b = bool(la.get("scenario_action_exact")), bool(lb.get("scenario_action_exact"))
            record.update({
                "left_slu_f1_f1": slu_a, "right_slu_f1_f1": slu_b,
                "left_scenario_action_exact": int_a, "right_scenario_action_exact": int_b,
                "delta_slu_f1_f1": slu_b - slu_a,
                "delta_scenario_action_exact": int(int_b) - int(int_a),
            })
            ia, ib = _intent_key(la.get("parsed")), _intent_key(lb.get("parsed"))
            ea, eb = _entity_key(la.get("parsed")), _entity_key(lb.get("parsed"))
            record["intent_flip"] = None if ia is None or ib is None else (ia != ib)
            record["entity_set_flip"] = None if ea is None or eb is None else (ea != eb)
        records.append(record)

    n = len(records)
    identical = sum(1 for r in records if r["byte_identical"])

    def share(key: str) -> dict:
        known = [r[key] for r in records if r.get(key) is not None]
        return {
            "count": sum(1 for v in known if v),
            "denominator": len(known),
            "share": (sum(1 for v in known if v) / len(known)) if known else None,
            "unknown": n - len(known),
        }

    strata: dict[str, list[dict]] = {}
    for r in records:
        strata.setdefault(str(r["stratum"]), []).append(r)
    per_stratum = {
        k: {
            "rows": len(v),
            "byte_identical": sum(1 for r in v if r["byte_identical"]),
            **({
                "mean_delta_slu_pp": 100.0 * sum(r["delta_slu_f1_f1"] for r in v) / len(v),
                "mean_delta_intent_pp": 100.0 * sum(r["delta_scenario_action_exact"] for r in v) / len(v),
            } if scored else {}),
        }
        for k, v in sorted(strata.items())
    }
    summary: dict[str, Any] = {
        "schema": SCHEMA_SUMMARY,
        "recipe_id": RECIPE_ID,
        "left": {"run_id": left.run_id, "attempt_id": left.attempt_id, "outputs_sha256": left.outputs_sha256},
        "right": {"run_id": right.run_id, "attempt_id": right.attempt_id, "outputs_sha256": right.outputs_sha256},
        "roster": {"relpath": roster.relpath, "sha256": roster.sha256, "rows": n,
                   "split_identity_hash": roster.split_identity_hash},
        "byte_identical_delivered_answer": {
            "count": identical,
            "rows": n,
            "share": identical / n if n else None,
            "all_identical": identical == n and n > 0,
            "non_identical_sample_ids": [r["sample_id"] for r in records if not r["byte_identical"]],
        },
        "scored": scored,
        "scorer_id": scorer_id if scored else None,
        "per_stratum": per_stratum,
        "reported_beside": REPORTED_BESIDE,
        "throughput": {
            "decision_140": (
                "the np1 cache-off test is authorised as a cheap test; ADOPTION of any geometry "
                "is decided on throughput, because future rounds need massive sampling. This "
                "cell decides a determinism question and INFORMS a throughput one; the "
                "coordinator will not adopt np1 for sampling-heavy work on determinism alone."
            ),
            "pass_a_np1_nocache": _throughput(left),
            "pass_b_np1_nocache": _throughput(right),
            "roll_2_np4_reference": ROLL_2_NP4_REFERENCE,
            "table": [
                {
                    "geometry": "np1 x 24,576, prompt cache off (pass A)",
                    "contacts_per_minute": _throughput(left).get("contacts_per_minute"),
                    "prompt_tokens_per_second": _throughput(left).get("prompt_tokens_per_second"),
                },
                {
                    "geometry": "np1 x 24,576, prompt cache off (pass B)",
                    "contacts_per_minute": _throughput(right).get("contacts_per_minute"),
                    "prompt_tokens_per_second": _throughput(right).get("prompt_tokens_per_second"),
                },
                {
                    "geometry": ROLL_2_NP4_REFERENCE["geometry"] + " (ROLL-2 sealed arm)",
                    "contacts_per_minute": ROLL_2_NP4_REFERENCE["contacts_per_minute"],
                    "prompt_tokens_per_second": ROLL_2_NP4_REFERENCE["prompt_tokens_per_second"],
                },
            ],
        },
        "routing_rule": (
            f"{identical} of {n} rows byte-identical. "
            + (
                "ALL rows repeat: the between-flight offset is an artefact of batch composition "
                "and cache state on the np4 geometry; the coordinator scales this probe to 200 "
                "rows for a floor re-estimate (a separate registration)."
                if identical == n and n > 0 else
                "NOT all rows repeat: single-slot, cache-off serving does not make the flight "
                "reproducible; the offset is intrinsic to the model's numerics on this hardware "
                "and the programme stops hoping for a cheaper instrument along this axis."
            )
            + " A 50-row cell cannot support a floor re-estimate; it decides only whether the "
            "200-row re-estimate is worth flying."
        ),
        "claim_boundary": (
            "DESCRIPTIVE. No superiority, generalisation, admission, component-causal or "
            "confirmatory claim; development rows (owner decisions 28 and 86); the pooled "
            "SLU-F1 and intent differences below are reported as numbers, never read against "
            "a bar."
        ),
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0},
    }
    if scored:
        summary["intent_flip"] = share("intent_flip")
        summary["entity_set_flip"] = share("entity_set_flip")
        summary["scenario_action_exact_disagreement"] = {
            "count": sum(1 for r in records if r["delta_scenario_action_exact"] != 0),
            "rows": n,
        }
        summary["paired_delta_slu_f1_f1"] = _bootstrap_block(
            [r["delta_slu_f1_f1"] for r in records], seed=seed, draws=draws
        )
        summary["paired_delta_scenario_action_exact"] = _bootstrap_block(
            [float(r["delta_scenario_action_exact"]) for r in records], seed=seed, draws=draws
        )
    per_row = {"schema": SCHEMA_PER_ROW, "recipe_id": RECIPE_ID, "rows": records}
    return per_row, summary


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--stage", choices=("stop", "read", "all"), default="all")
    parser.add_argument("--left-run", required=True)
    parser.add_argument("--left-attempt", required=True)
    parser.add_argument("--left-label", default="pass-a")
    parser.add_argument("--right-run", required=True)
    parser.add_argument("--right-attempt", required=True)
    parser.add_argument("--right-label", default="pass-b")
    parser.add_argument("--roster", required=True, help="roster receipt relpath under --repo-root")
    parser.add_argument("--repo-root", default=str(_DRIVER_REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--analysis-root", required=True)
    parser.add_argument("--scorer-id", default=DEFAULT_SCORER)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--expected-session-id", default=None)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    analysis_root = Path(args.analysis_root)
    roster = load_roster(repo_root, args.roster)
    left = load_arm(data_root, args.left_label, args.left_run, args.left_attempt)
    right = load_arm(data_root, args.right_label, args.right_run, args.right_attempt)

    stop = stage_stop(left, right, roster, expected_session_id=args.expected_session_id)
    written = {"stop.json": write_json(analysis_root / "stop.json", stop)}
    if args.stage in ("read", "all"):
        per_row, summary = stage_read(
            left, right, roster, scorer_id=args.scorer_id, seed=args.seed, draws=args.draws
        )
        written["per_row.json"] = write_json(analysis_root / "per_row.json", per_row)
        written["summary.json"] = write_json(analysis_root / "summary.json", summary)
        print(json.dumps({k: v for k, v in summary.items() if k not in ("per_stratum",)},
                         indent=2, sort_keys=True))
    print(json.dumps({"written": written, "analysis_root": str(analysis_root)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StopStageError as error:
        print(f"slurp_det_pair_read: STOP: {error}", file=sys.stderr)
        raise SystemExit(2) from None
