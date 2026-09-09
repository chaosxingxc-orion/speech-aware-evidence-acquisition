#!/usr/bin/env python3
"""Stitch the sealed speaker-turn units into the sealed 90-second windows, and
bind the result as DR-1's predecessor snapshot.

Owner Decision 13-J (2026-09-09): the Observe stage uses the SHORT speech to
produce drafts quickly, and the Plan stage hands the model the LONG speech
together with the prior draft and lets it refresh the transcript once. The
short half is already sealed -- ``SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1``
decoded all 5,122 speaker-turn units of the 44 discovery calls -- so DR-1's
pass 1 is READ, exactly as KC-E1f read the comparator's.

What this script produces is the arithmetic between the two grids: each of the
comparator's 1,593 sealed 90-second windows, carrying as its predecessor TEXT
the concatenation of the OBS-E1 units that window owns
(``analysis.e21_unit_draft_stitch``). The row schema is
``core.predecessor_snapshot``'s own, unchanged, so
``reproduction.repair_loop``'s hook binds it with no new loader and no new
verification path.

MODEL-FREE. Zero model, GPU, server, socket, tokenizer, tool, embedder, network
and audio-decode contacts; no reference transcript, ``wer_tags`` sidecar, gold
label or scorer is opened. It reads six sealed files -- two run manifests, two
``outputs.jsonl`` and two ``trace.jsonl`` -- and nothing else.

What it writes
--------------
* ``<data_root>/derived/e21-unit-draft/<run>/<attempt>/window-drafts.json`` --
  1,593 rows carrying the comparator's own window identity and bounds, the
  stitched unit draft, that draft's SHA-256, which units it owns, and the
  units' own sealed completion-token counts. It carries model output, so it
  lives under ``SPEECHRL_DATA_DIR`` where sealed outputs live and NEVER in Git.
* ``docs/receipts/e21-unit-draft-obs-e1-speaker-turn-units-v1.json`` -- the
  committed, CONTENT-FREE binding: paths, sizes and hashes, the six source
  hashes, counts, the ``(window_id, text_sha256)`` chain, the ownership
  distribution and the token distributions the prompt fit projects from. No
  draft character of any kind.
* ``docs/checks/speech-aware-evidence-acquisition/<date>-e21-dr1-unit-draft-stitch/``
  -- the proof, with its own ``MANIFEST.sha256``.

The three proofs, in the order they must hold
----------------------------------------------
1. **Each sealed run rebuilds itself.**
   ``analysis.e21_window_pairing.assert_stitch_reproduces_outputs`` refuses
   unless every recovered call rebuilds its own sealed ``outputs.jsonl``
   hypothesis byte for byte -- run on the comparator AND on the unit run.
2. **Ownership is a monotone partition.**
   ``analysis.e21_unit_draft_stitch.assert_ownership_is_monotone``.
3. **The drafts rebuild OBS-E1's corpus text.** Per call, concatenating the
   per-window drafts equals concatenating the units, which by proof 1 equals
   the sealed OBS-E1 hypothesis. Both links are asserted, and the second is
   asserted AGAINST THE SEALED OUTPUTS FILE directly rather than through the
   first, so the chain is checked end to end.

Usage::

    python scripts/build_e21_unit_draft_snapshot.py [--out <receipt path>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_unit_draft_stitch as stitch,
)
from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_window_pairing as wp,
)
from speech_aware_evidence_acquisition.core.predecessor_snapshot import (  # noqa: E402
    BINDING_SCHEMA,
    SNAPSHOT_SCHEMA,
    window_text_chain_sha256,
)

#: The LONG-window run: it owns the grid DR-1 tiles, and it is the comparator.
WINDOW_RUN_ID = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
WINDOW_ATTEMPT_ID = "attempt-20260904T233816Z-bcd338"
#: The SHORT-unit run: it owns the draft text.
DRAFT_RUN_ID = "SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1"
DRAFT_ATTEMPT_ID = "attempt-20260908T150858Z-c597a8"

CARRIER = "earnings21-original"
SPLIT_IDENTITY_HASH = "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
EXPOSURE_ROW = "SAEA-E21-MF-DR1-PREP-V1"

DEFAULT_RECEIPT = (
    REPO_ROOT / "docs/receipts/e21-unit-draft-obs-e1-speaker-turn-units-v1.json"
)
DEFAULT_CHECK_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-09-e21-dr1-unit-draft-stitch"
)

#: What each sealed run is expected to contain, quoted from its own committed
#: verdict, so this build is checked against a claim rather than against
#: whatever it happens to find. Comparator: the KC-E1f identity anchor and
#: docs/receipts/e21-predecessor-full44-direct-baseline-v2.json. Unit run:
#: docs/readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md sections
#: 1 and 7.
EXPECTED = {
    WINDOW_RUN_ID: {
        "spans": 1593,
        "calls": 44,
        "saturated": 0,
        "completion_tokens": 439532,
        "prompt_tokens": 1935965,
    },
    DRAFT_RUN_ID: {
        "spans": 5122,
        "calls": 44,
        "saturated": 3,
        "completion_tokens": 445342,
        "prompt_tokens": 2255812,
    },
}


def log(message: str) -> None:
    print(
        "[%s] %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message),
        flush=True,
    )


def git(*argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0}

    def percentile(fraction: float) -> float:
        index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
        return ordered[index]

    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": float(statistics.median(ordered)),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "max": ordered[-1],
        "total": sum(ordered),
    }


def read_outputs_text(path: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        sample_id = str(row["sample_id"])
        if sample_id in texts:
            raise SystemExit(f"outputs line {number}: duplicate sample {sample_id!r}")
        texts[sample_id] = str(row["text"])
    return texts


def read_cost_records(path: Path) -> dict[str, dict[str, int]]:
    """``request_id -> {prompt_tokens, completion_tokens}`` from the sealed COST
    channel -- the SERVER's own counts on the flight tokenizer."""

    costs: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("channel") != "COST":
                continue
            record_id = str(record.get("record_id", ""))
            payload = record.get("payload")
            if not isinstance(payload, Mapping) or "/" not in record_id:
                continue
            costs[record_id.split("/", 1)[0]] = {
                "prompt_tokens": int(payload["prompt_tokens"]),
                "completion_tokens": int(payload["completion_tokens"]),
            }
    return costs


def attempt_directory(root: Path, run_id: str, attempt_id: str) -> Path:
    """The sealed attempt's directory, allowing the run-root placement some
    closures used (`saea-driver run --run-dir` writes where it is pointed)."""

    candidate = root / "runs" / run_id / attempt_id
    if candidate.is_dir():
        return candidate
    alternative = root / "runs" / run_id
    if (alternative / f"{run_id}.run-manifest.json").is_file():
        return alternative
    raise SystemExit(f"no sealed attempt directory at {candidate}")


def load_sealed(root: Path, run_id: str, attempt_id: str) -> dict[str, Any]:
    """One sealed run's spans, texts, costs and hashes, self-proved."""

    attempt_dir = attempt_directory(root, run_id, attempt_id)
    manifest_path = attempt_dir / f"{run_id}.run-manifest.json"
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    for path in (manifest_path, outputs_path, trace_path):
        if not path.is_file():
            raise SystemExit(f"sealed file missing: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest["run_id"]) != run_id:
        raise SystemExit(f"{manifest_path} names a different run")
    if str(manifest["attempt"]["attempt_id"]) != attempt_id:
        raise SystemExit(f"{manifest_path} names a different attempt")
    hashes = {
        "manifest_sha256": sha256_file(manifest_path),
        "outputs_sha256": sha256_file(outputs_path),
        "trace_sha256": sha256_file(trace_path),
    }
    if hashes["outputs_sha256"] != str(manifest["outputs"]["sha256"]):
        raise SystemExit(f"{outputs_path} does not hash to the manifest's own digest")
    if hashes["trace_sha256"] != str(manifest["raw_trace"]["sha256"]):
        raise SystemExit(f"{trace_path} does not hash to the manifest's own digest")

    spans = wp.stitched_windows_from_trace(trace_path)
    texts = read_outputs_text(outputs_path)
    wp.assert_stitch_reproduces_outputs(spans, texts)
    costs = read_cost_records(trace_path)

    total_spans = sum(len(value) for value in spans.values())
    saturated = sum(1 for value in spans.values() for span in value if span.saturated)
    completion = sum(
        int(costs.get(span.request_id, {}).get("completion_tokens") or 0)
        for value in spans.values()
        for span in value
    )
    prompt = sum(
        int(costs.get(span.request_id, {}).get("prompt_tokens") or 0)
        for value in spans.values()
        for span in value
    )
    expected = EXPECTED[run_id]
    measured = {
        "spans": total_spans,
        "calls": len(spans),
        "saturated": saturated,
        "completion_tokens": completion,
        "prompt_tokens": prompt,
    }
    for key, value in expected.items():
        if measured[key] != value:
            raise SystemExit(
                f"{run_id}: measured {key} {measured[key]}, the sealed run records {value}"
            )
    log(
        "%s: %d spans / %d calls / %d saturated / %d completion / %d prompt tokens -- "
        "anchors PASS, stitch rebuilds all %d sealed hypotheses byte for byte"
        % (
            run_id,
            total_spans,
            len(spans),
            saturated,
            completion,
            prompt,
            len(texts),
        )
    )
    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "attempt_dir": attempt_dir,
        "hashes": hashes,
        "spans": spans,
        "texts": texts,
        "costs": costs,
        "measured": measured,
    }


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-run-id", default=WINDOW_RUN_ID)
    parser.add_argument("--window-attempt-id", default=WINDOW_ATTEMPT_ID)
    parser.add_argument("--draft-run-id", default=DRAFT_RUN_ID)
    parser.add_argument("--draft-attempt-id", default=DRAFT_ATTEMPT_ID)
    parser.add_argument("--out", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--check-dir", type=Path, default=DEFAULT_CHECK_DIR)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "TEST-ONLY. A binding receipt records the study commit it was built "
            "at; without this the build refuses a dirty tree rather than naming a "
            "commit that describes different bytes"
        ),
    )
    args = parser.parse_args()

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")

    from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit("the working tree is dirty; a binding names a commit:\n" + dirty)
    study_commit = git("rev-parse", "HEAD")

    root = data_root()
    windows = load_sealed(root, args.window_run_id, args.window_attempt_id)
    drafts_source = load_sealed(root, args.draft_run_id, args.draft_attempt_id)

    # ---- the stitch, proved call by call as it is built --------------------
    drafts = stitch.stitch_corpus(drafts_source["spans"], windows["spans"])
    stitch.assert_window_identity(drafts, windows["spans"])
    for sample_id, call_drafts in drafts.items():
        rebuilt = stitch.stitched_draft_text(call_drafts)
        sealed = drafts_source["texts"][sample_id]
        if rebuilt != sealed:
            raise SystemExit(
                f"sample {sample_id!r}: the per-window drafts do not rebuild the sealed "
                f"OBS-E1 hypothesis ({len(rebuilt)} chars vs {len(sealed)})"
            )
    log(
        "the per-window drafts rebuild all %d sealed OBS-E1 hypotheses byte for byte"
        % len(drafts)
    )

    # ---- rows ---------------------------------------------------------------
    unit_costs = drafts_source["costs"]
    unit_by_id = {
        span.identifier: span
        for value in drafts_source["spans"].values()
        for span in value
    }
    window_costs = windows["costs"]
    window_by_id = {
        span.identifier: span for value in windows["spans"].values() for span in value
    }

    rows: list[dict[str, Any]] = []
    per_call: list[dict[str, Any]] = []
    units_per_window: Counter[int] = Counter()
    empty_windows: list[dict[str, Any]] = []
    owned_units = 0
    for sample_id in sorted(drafts):
        call_drafts = drafts[sample_id]
        call_units = 0
        call_chars = 0
        call_draft_tokens = 0
        call_owned_tokens = 0
        for draft in call_drafts:
            window = window_by_id[draft.window_id]

            def unit_completion(unit_id: str) -> int:
                return int(
                    unit_costs.get(unit_by_id[unit_id].request_id, {}).get(
                        "completion_tokens"
                    )
                    or 0
                )

            # The DRAFT's own cost counts only the units whose text is IN the
            # draft. A saturated unit spent its 1,024-token cap and contributed
            # the empty string (obs_loop's quarantine), so charging its tokens
            # to a prompt fit would inflate three windows by a whole cap.
            draft_completion = sum(
                unit_completion(unit_id)
                for unit_id in draft.unit_ids
                if unit_by_id[unit_id].text
            )
            # The conserved figure, kept beside it so the receipt can prove the
            # partition covers the sealed run's own token total exactly.
            owned_completion = sum(
                unit_completion(unit_id) for unit_id in draft.unit_ids
            )
            rows.append(
                {
                    "window_id": draft.window_id,
                    "sample_id": draft.sample_id,
                    "window_index": draft.window_index,
                    # The COMPARATOR's own request id and bounds: this snapshot
                    # is carried onto the comparator's grid and a DR-1 pass-2
                    # contact tiles exactly it.
                    "request_id": window.request_id,
                    "start_seconds": draft.start_seconds,
                    "end_seconds": draft.end_seconds,
                    "audio_seconds": draft.audio_seconds,
                    "saturated": window.saturated,
                    "text": draft.text,
                    "text_sha256": sha256_text(draft.text),
                    "text_chars": len(draft.text),
                    "text_whitespace_tokens": len(draft.text.split()),
                    # ``completion_tokens`` is the DRAFT's own measured cost:
                    # the sum of the sealed OBS-E1 completion-token counts of
                    # the units whose text is in this window's draft. The
                    # prompt fit projects the pass-2 request from it, so it
                    # must be the draft's cost and not the comparator's.
                    "completion_tokens": draft_completion,
                    "owned_unit_completion_tokens": owned_completion,
                    # ``prompt_tokens`` stays the COMPARATOR's own pass-1
                    # request cost for this window -- the audio-plus-envelope
                    # baseline the fit subtracts its instruction from.
                    "prompt_tokens": window_costs.get(window.request_id, {}).get(
                        "prompt_tokens"
                    ),
                    # Additive, ignored by ``core.predecessor_snapshot``'s
                    # loader, hashed into the artifact: which units this draft
                    # is made of.
                    "draft_unit_ids": list(draft.unit_ids),
                    "draft_units": draft.unit_count,
                    "draft_saturated_units": draft.saturated_units,
                    "draft_run_id": drafts_source["run_id"],
                    "draft_attempt_id": drafts_source["attempt_id"],
                    "stitch_rule": stitch.STITCH_RULE_ID,
                }
            )
            units_per_window[draft.unit_count] += 1
            owned_units += draft.unit_count
            call_units += draft.unit_count
            call_chars += len(draft.text)
            call_draft_tokens += draft_completion
            call_owned_tokens += owned_completion
            if draft.empty:
                empty_windows.append(
                    {
                        "window_id": draft.window_id,
                        "window_seconds": round(draft.audio_seconds, 6),
                        "window_index": draft.window_index,
                        "windows_in_call": len(call_drafts),
                        "is_last_window_of_the_call": draft.window_index
                        == len(call_drafts),
                    }
                )
        per_call.append(
            {
                "sample_id": sample_id,
                "windows": len(call_drafts),
                "units": call_units,
                "draft_chars": call_chars,
                "draft_completion_tokens": call_draft_tokens,
                "owned_unit_completion_tokens": call_owned_tokens,
                "windows_owning_no_unit": sum(1 for d in call_drafts if d.empty),
            }
        )

    if owned_units != EXPECTED[args.draft_run_id]["spans"]:
        raise SystemExit(
            f"ownership covers {owned_units} units, the sealed run has "
            f"{EXPECTED[args.draft_run_id]['spans']}"
        )
    if len(rows) != EXPECTED[args.window_run_id]["spans"]:
        raise SystemExit(
            f"stitched {len(rows)} windows, the comparator has "
            f"{EXPECTED[args.window_run_id]['spans']}"
        )
    draft_completion_total = sum(int(row["completion_tokens"]) for row in rows)
    owned_completion_total = sum(int(row["owned_unit_completion_tokens"]) for row in rows)
    if owned_completion_total != EXPECTED[args.draft_run_id]["completion_tokens"]:
        raise SystemExit(
            f"the owned-unit token sums reach {owned_completion_total}, the unit run "
            f"recorded {EXPECTED[args.draft_run_id]['completion_tokens']}"
        )
    log(
        "ownership PASS: %d units over %d windows, %d window(s) own none, owned-unit "
        "completion tokens conserved at %d (of which %d are in a draft; the %d "
        "difference is the saturated units' quarantined output)"
        % (
            owned_units,
            len(rows),
            len(empty_windows),
            owned_completion_total,
            draft_completion_total,
            owned_completion_total - draft_completion_total,
        )
    )

    # ---- the artifact -------------------------------------------------------
    artifact_relpath = "derived/e21-unit-draft/%s/%s/window-drafts.json" % (
        args.draft_run_id,
        args.draft_attempt_id,
    )
    artifact_path = root / artifact_relpath
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        # The snapshot's OWN identity is the run whose TEXT it carries.
        "run_id": args.draft_run_id,
        "attempt_id": args.draft_attempt_id,
        "carrier_lock_key": CARRIER,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": study_commit,
        "window_grid": {
            "run_id": args.window_run_id,
            "attempt_id": args.window_attempt_id,
            **windows["hashes"],
        },
        "source": drafts_source["hashes"],
        "stitch_rule": stitch.STITCH_RULE_ID,
        "recovery": (
            "analysis.e21_window_pairing.stitched_windows_from_trace on BOTH sealed "
            "runs, each proved by assert_stitch_reproduces_outputs to rebuild its own "
            "sealed hypotheses byte for byte; then "
            "analysis.e21_unit_draft_stitch.stitch_corpus, whose per-window drafts were "
            "proved to rebuild every sealed OBS-E1 hypothesis byte for byte before a "
            "single row was written"
        ),
        "windows": len(rows),
        "calls": len(per_call),
        "rows": rows,
    }
    artifact_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_sha256 = sha256_file(artifact_path)
    artifact_bytes = artifact_path.stat().st_size
    log(
        "wrote %s (%d bytes, sha256 %s)"
        % (artifact_path, artifact_bytes, artifact_sha256[:12])
    )

    # ---- the committed, content-free receipt --------------------------------
    receipt = {
        "schema": BINDING_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.draft_run_id,
        "attempt_id": args.draft_attempt_id,
        "carrier_lock_key": CARRIER,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "exposure_row": EXPOSURE_ROW,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": study_commit,
        "built_by": "scripts/build_e21_unit_draft_snapshot.py",
        "what_it_binds": (
            "the sealed OBS-E1 speaker-turn-unit hypotheses, regrouped onto the sealed "
            "comparator's 1,593 fixed 90-second windows by the majority-overlap "
            "ownership rule saea-e21-unit-draft-majority-overlap-v1. The window "
            "identity and bounds are the COMPARATOR's, because a DR-1 pass-2 contact "
            "tiles the comparator's grid and reproduction.repair_loop matches a cut "
            "window against its bound predecessor's bounds to 1e-6 s"
        ),
        "zero_contact": (
            "no model, GPU, server, socket, tokenizer, tool, embedder, network or "
            "audio-decode contact; six sealed files read (two run manifests, two "
            "outputs.jsonl, two trace.jsonl) and no reference transcript, wer_tags "
            "sidecar, gold label or scorer opened"
        ),
        "content_free": (
            "this receipt carries hashes, counts and distributions only. Not one draft "
            "character is committed: the per-window draft is model output and lives "
            "with the sealed outputs under SPEECHRL_DATA_DIR"
        ),
        "window_grid": {
            "run_id": args.window_run_id,
            "attempt_id": args.window_attempt_id,
            **windows["hashes"],
        },
        "source": drafts_source["hashes"],
        "artifact": {
            "relpath": artifact_relpath,
            "sha256": artifact_sha256,
            "bytes": artifact_bytes,
            "root": "SPEECHRL_DATA_DIR",
        },
        "windows": len(rows),
        "calls": len(per_call),
        "saturated_windows": sum(1 for row in rows if row["saturated"]),
        "window_text_sha256_chain": window_text_chain_sha256(rows),
        "stitch_rule": stitch.STITCH_RULE_ID,
        "identity_anchors": {
            "comparator": {
                "measured": windows["measured"],
                "sealed": EXPECTED[args.window_run_id],
                "check": "PASS",
            },
            "unit_run": {
                "measured": drafts_source["measured"],
                "sealed": EXPECTED[args.draft_run_id],
                "check": "PASS",
            },
            "each_run_rebuilds_its_own_sealed_outputs_byte_for_byte": "PASS",
            "ownership_is_a_monotone_partition_of_the_units": "PASS",
            "drafts_rebuild_the_sealed_obs_e1_hypotheses_byte_for_byte": "PASS",
            "units_owned": owned_units,
            "owned_unit_completion_tokens_conserved": owned_completion_total,
            "draft_completion_tokens": draft_completion_total,
            "quarantined_saturated_unit_tokens": owned_completion_total
            - draft_completion_total,
        },
        "ownership": {
            "units_per_window": {
                str(count): units_per_window[count]
                for count in sorted(units_per_window)
            },
            "windows_owning_no_unit": len(empty_windows),
            "windows_owning_no_unit_detail": empty_windows,
            "why_a_window_may_own_none": (
                "a window shorter than the unit covering it loses every tie. Both cases "
                "here are the last, remainder window of their call, and the corpus loses "
                "nothing: the words spoken there are inside the covering unit's text and "
                "that text is delivered by the preceding window. What a cell does with an "
                "empty draft is its delivery rule's business -- both DR-1 rules refuse it "
                "as empty_predecessor and deliver the empty string"
            ),
        },
        "distributions": {
            "window_draft_chars": distribution([int(r["text_chars"]) for r in rows]),
            "window_draft_whitespace_tokens": distribution(
                [int(r["text_whitespace_tokens"]) for r in rows]
            ),
            "window_draft_completion_tokens": distribution(
                [int(r["completion_tokens"]) for r in rows]
            ),
            "window_owned_unit_completion_tokens": distribution(
                [int(r["owned_unit_completion_tokens"]) for r in rows]
            ),
            "comparator_window_prompt_tokens": distribution(
                [int(r["prompt_tokens"] or 0) for r in rows]
            ),
            "units_per_window": distribution([int(r["draft_units"]) for r in rows]),
            "windows_per_call": distribution([int(c["windows"]) for c in per_call]),
        },
        "why_completion_tokens_matter": (
            "the stitched draft rides in a DR-1 pass-2 request, so the sum of its units' "
            "own completion-token counts IS that request's added text cost, measured by "
            "the flight server on the flight tokenizer. The prompt fit projects the worst "
            "request from this distribution rather than from a characters-per-token "
            "guess, and it states the join residue (one space per unit boundary) it "
            "cannot see"
        ),
        "per_call": per_call,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))

    # ---- the check receipt --------------------------------------------------
    check_dir = Path(args.check_dir)
    check_dir.mkdir(parents=True, exist_ok=True)
    proof = {
        "schema": "saea-e21-dr1-unit-draft-stitch-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": EXPOSURE_ROW,
        "execution_profile": "model-free-check",
        "exposure_row": EXPOSURE_ROW,
        "study_commit": study_commit,
        "study_repo_dirt": dirty,
        "result": "PASS",
        "generated_at": receipt["generated_at"],
        "binding_receipt": {
            "relpath": str(out_path.relative_to(REPO_ROOT).as_posix()),
            "sha256": sha256_file(out_path),
        },
        "identity_anchors": receipt["identity_anchors"],
        "ownership": receipt["ownership"],
        "distributions": receipt["distributions"],
        "authorizes": (
            "nothing. This receipt records an arithmetic regrouping of two sealed runs. "
            "No cell is registered to fly, OBS-E1 stays REJECTED and no verdict moves"
        ),
    }
    (check_dir / "stitch-proof.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_manifest(check_dir)
    log("wrote %s" % (check_dir / "stitch-proof.json"))

    tokens = receipt["distributions"]["window_draft_completion_tokens"]
    log(
        "draft tokens per window: min %d median %.1f p95 %d max %d"
        % (tokens["min"], tokens["median"], tokens["p95"], tokens["max"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
