#!/usr/bin/env python3
"""Assemble the committed flight receipt for the Earnings-21 entity-repair cell.

Reads only the run's own sealed artifacts, the committed predecessor binding and
the attached session's monitor. No model, GPU, tool, network or audio contact.

THE DELIVERY-INTEGRITY GUARD RUNS FIRST, AND IT ABORTS THE READ.
``docs/readiness/2026-09-07-e21-kc-e1f-brief-repair-pass-v1-preregistration.md``
section 5 makes it one guard of five and section 8 item 7 makes it the step
before any number is looked at. For EVERY window the delivered raw text must
carry the identical whitespace-token count as the sealed predecessor, and then:

* a REFUSED window must deliver the predecessor BYTE FOR BYTE and must record
  zero applied substitutions;
* a DELIVERED window must be byte-identical at every token position the repair
  did not substitute -- so its differing positions equal that window's own
  recorded ``obs_repair_substituted_tokens`` -- and must record substitutions if
  and only if a position actually moved.

The refusal branch is checked FIRST and that ordering is load-bearing:
``core.repair_alignment._refuse`` is handed ``substituted_tokens`` on the
``substituted_fraction_above_ceiling`` path, so a refusal can carry a non-zero
WOULD-BE count while having applied nothing at all. Comparing that count against
the delivered bytes is a category error, and getting the order backwards flags a
correct refusal as a violation (it did, on 4 of this cell's 1,593 windows,
before the order was fixed).

It is a construction check verified from the sealed trace, not a statistical
one; a single failing window makes this script exit non-zero and write nothing,
because a delivered hypothesis whose token count moved is exactly the defect the
mechanism exists to make impossible.

BOTH CELLS OF THE FRAGMENT USE THIS BUILDER. ``cell_id`` selects which one is
being written; the twin ``E21-ku-e1fc-placebo-repair`` additionally takes its
sibling's sealed attempt so the per-window prompt-token match the prompt fit
asserted (+7 tokens on every window, the constant ``[evidence <id>] `` header
residual) is re-measured on the FLIGHT's own requests rather than assumed.

The ``kc_e1f`` column of ``delivered_vs_comparator_operations`` is the v1
schema's own-cell column, named for the experiment fragment
``e21-kc-e1f-repair-44-v1``; in the twin's receipt it carries the twin's numbers.
It is deliberately not renamed, so the pair's two receipts stay comparable field
for field.

usage:
  python scripts/e21_kc_e1f_flight_receipt.py <attempt_dir> <run_id> <t0> <t1>
      <session_id> <out.json> [cell_id] [paired_run_id] [paired_attempt_dir]
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.core.predecessor_snapshot import (  # noqa: E402
    load_predecessor_binding,
)
from speech_aware_evidence_acquisition.core.repair_alignment import (  # noqa: E402
    REFUSAL_REASONS,
    REJECTION_CLASSES,
)
from speech_aware_evidence_acquisition.core.session.serving import (  # noqa: E402
    summarize_monitor_file,
)

DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)
BINDING_RELPATH = "receipts/e21-predecessor-full44-direct-baseline-v2.json"
BINDING_SHA256 = "26f1d9ccd4a4f9d7aa27559f57b98ee9f8928ee2378883470eeb13145f77a72a"
SLOT_TOKENS = 9216
MAX_TOKENS = 1024

#: The sealed comparator's own published numbers, quoted from the
#: preregistration's ``comparator`` block. Never recomputed here.
COMPARATOR = {
    "corpus_wer_percent": 8.2,
    "conec_person_entity_wer_percent": 22.489,
    "conec_org_entity_wer_percent": 17.213,
    "numeric_value_accuracy_percent": 90.73,
    "negation_critical_error_rate_percent": 0.0278,
    "substitutions": 13098,
    "deletions": 5701,
    "insertions": 10700,
    "reference_words": 359765,
    "prompt_tokens_total": 1935965,
    "completion_tokens_total": 439532,
    "gpu_hours": 0.9734,
    "windows_per_minute": 16.38,
    "saturated_slice_count": 0,
}
#: The treatment cell's own committed flight numbers, quoted from
#: ``docs/checks/.../2026-09-07-e21-kc-e1f-repair-44-v1/flight/flight-receipt.json``
#: and its exposure row. Emitted only in the TWIN's receipt, and quoted rather
#: than recomputed. It is a reference column, never a contrast: the paired
#: intervals belong to the verdict.
KC_E1F = {
    "attempt_id": "attempt-20260908T040832Z-ecda9c",
    "corpus_wer_percent": 8.154,
    "conec_person_entity_wer_percent": 18.752,
    "conec_org_entity_wer_percent": 16.502,
    "numeric_value_accuracy_percent": 90.744,
    "negation_critical_error_rate_percent": 0.0275,
    "substitutions": 12936,
    "deletions": 5700,
    "insertions": 10701,
    "reference_words": 359765,
    "prompt_tokens_total": 3550695,
    "completion_tokens_total": 434219,
    "gpu_hours": 1.1093,
    "windows_per_minute": 15.295,
    "saturated_slice_count": 3,
    "windows_changed": 1064,
    "windows_refused": 82,
    "accepted_substitutions": 2427,
    "substituted_tokens_applied": 2545,
}
KC_E1 = {
    "prompt_tokens_total": 2907274,
    "completion_tokens_total": 423115,
    "gpu_hours": 0.9948,
    "windows_per_minute": 16.244,
    "saturated_slice_count": 2,
    "corpus_wer_percent": 8.736,
    "conec_person_entity_wer_percent": 18.341,
    "conec_org_entity_wer_percent": 17.992,
    "numeric_value_accuracy_percent": 90.189,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _operation_table(aggregates):
    """The delivered hypothesis's own S / D / I against the sealed comparator's.

    The delivery is substitution-only in RAW whitespace-token space by
    construction; the Whisper normalizer is not a per-token map, so a
    substituted surface form can normalize to a different number of words and
    the NORMALIZED deletion/insertion counts can move by that delta alone
    (preregistration section 5.1). This block publishes the deltas; attributing
    each one to the substitution that caused it is the verdict's work, not this
    receipt's.
    """

    wer = aggregates.get("asr-wer-whisper")
    if not isinstance(wer, dict):
        return None
    rows = {}
    for name in ("substitutions", "deletions", "insertions", "reference_words"):
        mine = wer.get(name)
        theirs = COMPARATOR.get(name)
        rows[name] = {
            "kc_e1f": mine,
            "comparator": theirs,
            "delta": (mine - theirs) if isinstance(mine, int) and isinstance(theirs, int) else None,
        }
    rows["note"] = (
        "raw-space delivery is substitution-only; these are NORMALIZED counts, so a "
        "deletion or insertion delta is a normalization delta of a substituted span "
        "until the verdict attributes it. A move that cannot be attributed to a "
        "substituted span is a defect report, not a result"
    )
    return rows


def _window_prompt_tokens(trace_path):
    """window_id -> the flight server's own prompt-token count for that window.

    Joins the COST record to the OBS record through the shared record-id base,
    which is the request id. Used only for the twin's token match against the
    treatment cell: the prompt fit asserted +7 tokens per rendered line, and this
    re-measures the same quantity on the requests that actually flew.
    """

    prompt_by_request = {}
    window_by_request = {}
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        payload = record.get("payload") or {}
        base = str(record.get("record_id", "")).split("/", 1)[0]
        if record.get("channel") == "COST" and payload.get("prompt_tokens") is not None:
            prompt_by_request[base] = int(payload["prompt_tokens"])
        elif record.get("channel") == "OBS" and "obs_repair" in payload:
            window_by_request[base] = str(
                payload.get("obs_repair_predecessor_window_id", "")
            )
    return {
        window: prompt_by_request[request]
        for request, window in window_by_request.items()
        if request in prompt_by_request
    }


def _token_match(mine, paired_run_id, paired_trace):
    """The twin's per-window prompt-token delta against its sibling cell.

    A DESCRIPTIVE match, not a contrast: the two cells fly the identical audio,
    the identical predecessor and the identical instruction, so every token of
    difference is the brief's own rendering. The prompt fit measured exactly +7
    on all 1,593 windows before either cell flew; this reports what the flight
    itself carried, including any window where the two disagree.
    """

    theirs = _window_prompt_tokens(paired_trace)
    deltas = {
        window: value - theirs[window] for window, value in mine.items() if window in theirs
    }
    if not deltas:
        return {"paired_run_id": paired_run_id, "windows_matched": 0}
    ordered = sorted(deltas.values())
    histogram = Counter(ordered)
    return {
        "paired_run_id": paired_run_id,
        "paired_trace": str(paired_trace),
        "windows_this_cell": len(mine),
        "windows_paired_cell": len(theirs),
        "windows_matched": len(deltas),
        "windows_unmatched": sorted(set(mine) - set(theirs))[:20],
        "delta_min": ordered[0],
        "delta_median": statistics.median(ordered),
        "delta_max": ordered[-1],
        "delta_histogram": {str(key): count for key, count in sorted(histogram.items())},
        "constant_delta": ordered[0] if ordered[0] == ordered[-1] else None,
        "prompt_fit_expected_delta": 7,
        "matches_the_prompt_fit": ordered[0] == ordered[-1] == 7,
        "basis": (
            "each cell's own COST record joined to its OBS record through the shared "
            "request id, so the count is the flight server's own, on the flight "
            "tokenizer, including the identical speech tokens of the identical audio"
        ),
    }


def quantile(values, fraction):
    if not values:
        return None
    return values[min(len(values) - 1, int(fraction * (len(values) - 1)))]


def main() -> int:
    attempt_dir = Path(sys.argv[1])
    run_id = sys.argv[2]
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    session_id = sys.argv[5]
    out = Path(sys.argv[6])
    cell_id = sys.argv[7] if len(sys.argv) > 7 else "E21-kc-e1f-brief-repair"
    paired_run_id = sys.argv[8] if len(sys.argv) > 8 else None
    paired_attempt_dir = Path(sys.argv[9]) if len(sys.argv) > 9 else None
    session_dir = DATA_ROOT / "serving" / session_id

    manifest_path = attempt_dir / f"{run_id}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan_path = attempt_dir / f"{run_id}.plan.json"
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    scores_path = attempt_dir / f"{run_id}.scores.json"

    snapshot = load_predecessor_binding(
        REPO / "docs" / BINDING_RELPATH, DATA_ROOT, expected_receipt_sha256=BINDING_SHA256
    )

    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    prompt_tokens_by_request: dict[str, int] = {}
    per_call_windows: dict[str, int] = {}
    obs_by_request: dict[str, dict] = {}
    request_sample: dict[str, str] = {}
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        payload = record.get("payload") or {}
        channel = record.get("channel")
        base = str(record.get("record_id", "")).split("/", 1)[0]
        if channel == "COST":
            if payload.get("prompt_tokens") is not None:
                prompt_tokens.append(int(payload["prompt_tokens"]))
                prompt_tokens_by_request[base] = int(payload["prompt_tokens"])
            if payload.get("completion_tokens") is not None:
                completion_tokens.append(int(payload["completion_tokens"]))
        elif channel == "MODEL_REQUEST" and not payload.get("stitch"):
            inner = payload.get("payload")
            if isinstance(inner, dict):
                sample_id = str(inner["sample_id"])
                per_call_windows[sample_id] = per_call_windows.get(sample_id, 0) + 1
                request_sample[str(inner["request_id"])] = sample_id
        elif channel == "OBS" and "obs_repair" in payload:
            obs_by_request[base] = payload

    # ------------------------------------------------------------------
    # THE DELIVERY-INTEGRITY GUARD. It aborts the read.
    # ------------------------------------------------------------------
    violations: list[dict] = []
    ledger = {
        "windows": 0,
        "windows_changed": 0,
        "windows_delivered_unchanged_without_refusal": 0,
        "windows_refused": 0,
        "accepted_substitutions": 0,
        "substituted_tokens_applied": 0,
        "substituted_tokens_refused_would_be": 0,
        "refusals_by_reason": {name: 0 for name in REFUSAL_REASONS},
        "rejected_opcodes": {name: 0 for name in REJECTION_CLASSES},
        "pass2_saturated": 0,
        "pass2_skipped": 0,
    }
    substituted_positions_total = 0
    anchor_ratios: list[float] = []
    per_call_substitutions: Counter[str] = Counter()
    for request_id, record in sorted(obs_by_request.items()):
        window_id = str(record.get("obs_repair_predecessor_window_id", ""))
        predecessor = snapshot.windows.get(window_id)
        delivered = str(record.get("obs_delivered_text", ""))
        if predecessor is None:
            violations.append(
                {
                    "request_id": request_id,
                    "window_id": window_id,
                    "reason": "window is not in the sealed binding",
                }
            )
            continue
        pass1_tokens = predecessor.text.split()
        delivered_tokens = delivered.split()
        recorded = int(record.get("obs_repair_substituted_tokens", 0) or 0)
        substitutions = int(record.get("obs_repair_substitutions", 0) or 0)
        refused = bool(record.get("obs_repair_refused"))
        if len(delivered_tokens) != len(pass1_tokens):
            violations.append(
                {
                    "request_id": request_id,
                    "window_id": window_id,
                    "reason": "delivered token count moved",
                    "predecessor_tokens": len(pass1_tokens),
                    "delivered_tokens": len(delivered_tokens),
                }
            )
            continue
        if refused:
            if delivered != predecessor.text:
                violations.append(
                    {
                        "request_id": request_id,
                        "window_id": window_id,
                        "reason": "a refused window did not deliver the predecessor byte "
                        "for byte",
                    }
                )
                continue
            if substitutions:
                violations.append(
                    {
                        "request_id": request_id,
                        "window_id": window_id,
                        "reason": "a refused window recorded applied substitutions",
                        "substitutions": substitutions,
                    }
                )
                continue
            ledger["substituted_tokens_refused_would_be"] += recorded
        else:
            differing = [
                index
                for index, (left, right) in enumerate(zip(pass1_tokens, delivered_tokens))
                if left != right
            ]
            if len(differing) != recorded:
                violations.append(
                    {
                        "request_id": request_id,
                        "window_id": window_id,
                        "reason": "differing token positions do not equal the recorded "
                        "substituted-token count",
                        "differing_positions": len(differing),
                        "recorded_substituted_tokens": recorded,
                    }
                )
                continue
            if bool(differing) != bool(substitutions):
                violations.append(
                    {
                        "request_id": request_id,
                        "window_id": window_id,
                        "reason": "differing positions and applied substitutions disagree "
                        "on whether anything moved",
                        "differing_positions": len(differing),
                        "substitutions": substitutions,
                    }
                )
                continue
            substituted_positions_total += len(differing)
            ledger["substituted_tokens_applied"] += recorded
            ledger["accepted_substitutions"] += substitutions
            if substitutions:
                ledger["windows_changed"] += 1
                per_call_substitutions[request_sample.get(request_id, "?")] += substitutions
            else:
                ledger["windows_delivered_unchanged_without_refusal"] += 1

        ledger["windows"] += 1
        if refused:
            ledger["windows_refused"] += 1
            reason = record.get("obs_repair_refusal_reason")
            if reason in ledger["refusals_by_reason"]:
                ledger["refusals_by_reason"][reason] += 1
            else:
                violations.append(
                    {
                        "request_id": request_id,
                        "window_id": window_id,
                        "reason": "unknown refusal reason %r" % (reason,),
                    }
                )
        for name, count in dict(record.get("obs_repair_rejected", {})).items():
            if name in ledger["rejected_opcodes"]:
                ledger["rejected_opcodes"][name] += int(count)
        ledger["pass2_saturated"] += int(bool(record.get("obs_repair_pass2_saturated")))
        ledger["pass2_skipped"] += int(bool(record.get("obs_repair_pass2_skipped")))
        pred_tokens = int(record.get("obs_repair_predecessor_tokens", 0) or 0)
        anchor = int(record.get("obs_repair_anchor_tokens", 0) or 0)
        if pred_tokens:
            anchor_ratios.append(anchor / pred_tokens)

    if violations:
        sys.stderr.write(
            "DELIVERY-INTEGRITY GUARD FAILED on %d window(s); the read is aborted and no "
            "receipt is written.\n%s\n"
            % (len(violations), json.dumps(violations[:20], indent=1, sort_keys=True))
        )
        return 2

    cost = manifest["cost"]
    monitor = summarize_monitor_file(
        session_dir / "monitor.jsonl", from_epoch=t0, to_epoch=t1
    )
    prompt_tokens.sort()
    completion_tokens.sort()
    anchor_ratios.sort()
    wall = t1 - t0
    windows = sum(per_call_windows.values())
    scores = (
        json.loads(scores_path.read_text(encoding="utf-8"))
        if scores_path.is_file()
        else {}
    )
    aggregates = {
        name: value.get("aggregate")
        for name, value in scores.items()
        if isinstance(value, dict) and "aggregate" in value
    }

    my_window_prompt_tokens = {
        str(obs_by_request[request].get("obs_repair_predecessor_window_id", "")): value
        for request, value in prompt_tokens_by_request.items()
        if request in obs_by_request
    }
    token_match = (
        _token_match(
            my_window_prompt_tokens,
            paired_run_id,
            paired_attempt_dir / f"{paired_run_id}.trace.jsonl",
        )
        if paired_run_id and paired_attempt_dir
        else None
    )

    receipt = {
        "schema": "saea-e21-kc-e1f-flight-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "cell_id": cell_id,
        "exposure_run_id": run_id,
        "attempt_id": (
            manifest["attempt"]["attempt_id"]
            if isinstance(manifest.get("attempt"), dict)
            else manifest.get("attempt")
        ),
        "status": manifest["status"],
        "study_commit": manifest["study_commit"],
        "study_repo_dirt": manifest["study_repo_dirt"],
        "decides_nothing": (
            "This receipt reports ONE cell's flight. The comparator contrast, the other "
            "cell of the pair, the paired intervals and the preregistration's section 5 "
            "decision rule are separate acts under their own rows."
        ),
        "config_hash": (
            manifest["config"]["config_hash"]
            if isinstance(manifest.get("config"), dict)
            else None
        ),
        "protocol_hash": manifest["protocol_hash"],
        "split": manifest["split"],
        "plan": json.loads(plan_path.read_text(encoding="utf-8")),
        "scorers": manifest.get("scorers"),
        "legality": manifest.get("legality"),
        "predecessor_binding": {
            "relpath": BINDING_RELPATH,
            "sha256": BINDING_SHA256,
            "run_id": snapshot.run_id,
            "windows": snapshot.window_count,
        },
        "delivery_integrity": {
            "guard": (
                "for every window the delivered raw text carries the identical "
                "whitespace-token count as the sealed predecessor; a REFUSED window "
                "delivers the predecessor byte for byte and records zero applied "
                "substitutions; a DELIVERED window is byte-identical at every token "
                "position the repair did not substitute, so its differing positions "
                "equal that window's own recorded obs_repair_substituted_tokens, and it "
                "records substitutions if and only if a position moved. The refusal "
                "branch is checked FIRST: a substituted_fraction_above_ceiling refusal "
                "carries a WOULD-BE substituted-token count while applying nothing"
            ),
            "windows_checked": ledger["windows"],
            "violations": 0,
            "result": "PASS",
            "differing_token_positions_total": substituted_positions_total,
            "aborts_the_read": True,
        },
        "repair_ledger": ledger,
        "anchor_ratio": {
            "count": len(anchor_ratios),
            "min": anchor_ratios[0] if anchor_ratios else None,
            "median": statistics.median(anchor_ratios) if anchor_ratios else None,
            "max": anchor_ratios[-1] if anchor_ratios else None,
            "floor": 0.60,
        },
        "substitutions_per_call": dict(sorted(per_call_substitutions.items())),
        "windows": {
            "calls": len(per_call_windows),
            "windows": windows,
            "per_call": dict(sorted(per_call_windows.items())),
        },
        "tokens": {
            "prompt_total": sum(prompt_tokens),
            "completion_total": sum(completion_tokens),
            "prompt_min": prompt_tokens[0] if prompt_tokens else None,
            "prompt_median": quantile(prompt_tokens, 0.5),
            "prompt_max": prompt_tokens[-1] if prompt_tokens else None,
            "completion_min": completion_tokens[0] if completion_tokens else None,
            "completion_median": quantile(completion_tokens, 0.5),
            "completion_max": completion_tokens[-1] if completion_tokens else None,
            "slot_tokens": SLOT_TOKENS,
            "max_tokens": MAX_TOKENS,
            "worst_realized_request_tokens": (
                prompt_tokens[-1] + MAX_TOKENS if prompt_tokens else None
            ),
            "worst_realized_margin_factor": (
                round(SLOT_TOKENS / (prompt_tokens[-1] + MAX_TOKENS), 4)
                if prompt_tokens
                else None
            ),
            "comparator_prompt_total": COMPARATOR["prompt_tokens_total"],
            "comparator_completion_total": COMPARATOR["completion_tokens_total"],
            "kc_e1_prompt_total": KC_E1["prompt_tokens_total"],
            "kc_e1_completion_total": KC_E1["completion_tokens_total"],
        },
        "cost": {
            "calls_used": cost["calls_used"],
            "audio_seconds_used": cost["audio_seconds_used"],
            "gpu_seconds": cost["gpu_seconds"],
            "gpu_hours": round(cost["gpu_seconds"] / 3600.0, 4),
            "cpu_seconds": cost.get("cpu_seconds"),
            "latency_seconds_total": cost.get("latency_seconds_total"),
            "peak_vram_mib": cost.get("peak_vram_mib"),
            "gate_setup_seconds": cost.get("gate_setup_seconds"),
            "prompt_tokens_total": cost.get("prompt_tokens_total"),
            "completion_tokens_total": cost.get("completion_tokens_total"),
            "registered_calls": 1750,
            "registered_speech_audio_seconds": 150000,
            "registered_gpu_hours": 1.2,
            "registered_gpu_hours_basis": (
                "the preregistration's section 6 figure, KC-E1's realized 0.9948 GPU-h at "
                "SIX slots times 1.2. This cell flies at FOUR slots under the owner's own "
                "GPU-order delegation, which does the same total work with less batching, "
                "so the sampler figure is reported against that ceiling under both "
                "conventions rather than blended or hidden"
            ),
            "comparator_gpu_hours": COMPARATOR["gpu_hours"],
            "kc_e1_gpu_hours": KC_E1["gpu_hours"],
            "monitor_wall_hours": round(wall / 3600.0, 4),
        },
        "throughput": {
            "run_wall_seconds": round(wall, 1),
            "run_wall_minutes": round(wall / 60.0, 2),
            "windows_per_minute": round(windows / (wall / 60.0), 3) if wall else None,
            "realized_realtime_factor": (
                round(cost["audio_seconds_used"] / cost["gpu_seconds"], 2)
                if cost.get("gpu_seconds")
                else None
            ),
            "realtime_factor_convention": (
                "metered cut audio seconds divided by the manifest's own nvidia-smi "
                "busy-time seconds -- the convention the KC-E1 and tail2s receipts use"
            ),
            "comparator_windows_per_minute": COMPARATOR["windows_per_minute"],
            "kc_e1_windows_per_minute": KC_E1["windows_per_minute"],
            "slot_count_note": (
                "KC-E1 and the comparator flew at -np 6; this cell flies at -np 4, so a "
                "windows-per-minute comparison against them carries a serving change as "
                "well as a protocol one"
            ),
        },
        "serving": {
            "mode": "attached-serving-session",
            "session_id": session_id,
            "flight_started_a_server": False,
            "flight_stopped_a_server": False,
            "geometry": {
                "server_c": 36864,
                "server_np": 4,
                "slots": 4,
                "slot_tokens": SLOT_TOKENS,
            },
            "session_receipt": {
                "path": str(session_dir / "session-receipt.json"),
                "sha256": sha256(session_dir / "session-receipt.json"),
            },
            "monitor_summary": monitor,
            "monitor_summary_basis": (
                "core.session.serving.summarize_monitor_file over the attempt's own run "
                f"wall window {int(t0)}-{int(t1)}; core.driver.run_experiment_bundled "
                "writes no session-attach receipt (that is core.flight.FlightRuntime's "
                "artifact and this carrier's 90-second OBS tiling does not go through "
                "it), so head and tail idle count as parked against this flight rather "
                "than being hidden"
            ),
        },
        "saturation": {
            "saturated_slice_count": cost.get("saturated_slice_count"),
            "saturated_sample_ids": cost.get("saturated_sample_ids"),
            "skipped_slice_count": cost.get("skipped_slice_count"),
            "skipped_sample_ids": cost.get("skipped_sample_ids"),
            "pass2_saturated_windows": ledger["pass2_saturated"],
            "pass2_skipped_windows": ledger["pass2_skipped"],
            "comparator_saturated_slice_count": COMPARATOR["saturated_slice_count"],
            "kc_e1_saturated_slice_count": KC_E1["saturated_slice_count"],
            "rule": (
                "a saturated or skipped pass-2 decode reaches core.repair_alignment as the "
                "empty string and is refused as empty_response, so it delivers pass 1 and "
                "can never contribute an empty span the way KC-E1's two saturated windows "
                "did"
            ),
        },
        "scores_aggregates": aggregates,
        "delivered_vs_comparator_operations": _operation_table(aggregates),
        "comparator_published": COMPARATOR,
        "kc_e1_published": KC_E1,
        **(
            {"kc_e1f_published": KC_E1F}
            if cell_id != "E21-kc-e1f-brief-repair"
            else {}
        ),
        **({"token_match": token_match} if token_match else {}),
        "artifacts": {
            "manifest": str(manifest_path),
            "manifest_sha256": sha256(manifest_path),
            "outputs": str(outputs_path),
            "outputs_sha256": sha256(outputs_path),
            "trace": str(trace_path),
            "trace_sha256": sha256(trace_path),
            "plan": str(plan_path),
            "plan_sha256": sha256(plan_path),
            **(
                {"scores": str(scores_path), "scores_sha256": sha256(scores_path)}
                if scores_path.is_file()
                else {}
            ),
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "delivery_integrity": receipt["delivery_integrity"]["result"],
                "windows": windows,
                "calls": len(per_call_windows),
                "windows_changed": ledger["windows_changed"],
                "accepted_substitutions": ledger["accepted_substitutions"],
                "refusals": ledger["refusals_by_reason"],
                "gpu_hours": receipt["cost"]["gpu_hours"],
                "windows_per_minute": receipt["throughput"]["windows_per_minute"],
                "parked_fraction": monitor.get("parked_fraction"),
                "out": str(out),
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
