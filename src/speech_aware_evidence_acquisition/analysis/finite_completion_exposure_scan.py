"""How often a sealed SLURP arm ever met a finite completion. Answer: never.

Item E13 (2026-09-19), the model-free half. ``native_episode.
finite_completion_policy`` decides what an episode does with a valid,
source-bound completion the frozen core ended before authoritative delivery
(``finish_reason`` ``length`` or ``content_filter``): the parser's default
``"raise"`` aborts the flight, and ``"deliver-latest-or-abstain"`` retains the
row. Arming the key is therefore only NEUTRAL on the sealed record if no
sealed row ever carried such a completion -- otherwise the two arms would have
delivered different bytes and the sealed numbers would not be re-readable.

This scanner measures exactly that, and nothing else, over the sealed trace
files under ``$SPEECHRL_DATA_DIR/runs/``:

* every ``MODEL_RESPONSE`` record's ``usage.completion_tokens``, joined by
  request id to
* every ``MODEL_WIRE_RESPONSE`` record's ``finish_reason`` (the preserved wire
  metadata; ``MODEL_RESPONSE`` itself does not carry it), and to
* every ``USE`` ``.../native-role-contact`` record's ``use_role_id``, which is
  what makes the per-role columns possible.

It reports, per attempt: the contact count, the ``finish_reason`` histogram,
the maximum completion tokens per role, and how many contacts per role reached
448 and exactly 512 tokens (the serving geometry's output cap, and therefore
the token count a ``length`` completion carries on this carrier).

**It never reads, prints or persists a single character of a response's text,
a transcript or a gold label.** The only response fields it opens are the
usage counters, the finish reason and the role id; the preserved base64 wire
body is never decoded.

Scope: read-only under ``SPEECHRL_DATA_DIR``. Zero model, tokenizer, encoder,
scorer, network and GPU contacts.

CLI::

    python -m speech_aware_evidence_acquisition.analysis.finite_completion_exposure_scan \\
        --data-dir "$SPEECHRL_DATA_DIR" --out docs/receipts/<name>.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#: Only runs whose id starts with this are scanned: the SLURP carrier's arms.
DEFAULT_RUN_PREFIX = "SAEA-SLURP-"

#: The manifest status that makes an attempt SEALED. Anything else (an
#: aborted or still-open attempt) is reported, never counted as sealed.
SEALED_STATUS = "COMPLETED"

#: The two ABORTED B7a attempts, scanned as the POSITIVE CONTROL: the recovery
#: arm must show exactly one 512-token Reviewer contact with ``finish_reason``
#: ``length``, which is the flight this item's rule exists to have retained.
DEFAULT_CONTROL_RUNS = (
    "SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1",
    "SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1",
)

#: The completion-token thresholds the tables report. 512 is the serving
#: geometry's ``max_tokens``; 448 (512 - 64) is the "near the cap" band, which
#: is what would make a future ``length`` completion likely rather than freak.
NEAR_CAP_TOKENS = 448
OUTPUT_CAP_TOKENS = 512

#: The finish reasons that make a completion non-authoritative, i.e. the ones
#: ``finite_completion_policy`` decides the fate of.
FINITE_FINISH_REASONS = ("length", "content_filter")

_CHANNEL = re.compile(r'"channel"\s*:\s*"([A-Z_]+)"')
_FINISH_REASON = re.compile(r'"finish_reason"\s*:\s*"([a-z_]+)"')
_WIRE_REQUEST_ID = re.compile(r'"request_id"\s*:\s*"([^"]+)"')
_MAX_TOKENS = re.compile(r'"max_tokens"\s*:\s*(\d+)')
_RECORD_ID = re.compile(r'"record_id"\s*:\s*"([^"]+)"')

#: How far into a ``MODEL_REQUEST`` line ``decoding_params.max_tokens`` can
#: be, and how far from its END ``record_id`` can be. The payload's keys are
#: serialized in sorted order, so ``decoding_params`` is an early leaf of the
#: inner payload and ``record_id`` is the last top-level key; a request line
#: is otherwise tens of kilobytes of history and evidence this scanner NEVER
#: parses, reads or retains.
_REQUEST_HEAD = 600
_RECORD_ID_TAIL = 240

#: How far into a ``MODEL_WIRE_RESPONSE`` line the cheap regexes may look.
#: The payload's keys are serialized in sorted order, so ``finish_reason`` and
#: ``request_id`` both precede the (very large) ``response_b64``; a line that
#: does not yield them in this window falls back to a full parse.
_WIRE_HEAD = 400

#: The role name used when a contact has no ``native-role-contact`` USE
#: record, which is every contact of a non-native (direct) arm.
UNASSIGNED_ROLE = "unassigned"


class FiniteCompletionExposureScanError(RuntimeError):
    """A trace, manifest or data root could not be read."""


def _channel(line: str) -> str | None:
    match = _CHANNEL.search(line, 0, 120)
    return match.group(1) if match else None


def _wire_finish_reason(line: str) -> tuple[str | None, str | None]:
    """``(request id, finish reason)`` of a ``MODEL_WIRE_RESPONSE`` line.

    Read from the line's head without parsing the preserved wire body, which
    is a base64 blob several kilobytes long and is never decoded here.
    """

    finish = _FINISH_REASON.search(line, 0, _WIRE_HEAD)
    request = _WIRE_REQUEST_ID.search(line, 0, _WIRE_HEAD)
    if finish and request:
        return request.group(1), finish.group(1)
    try:
        payload = json.loads(line).get("payload") or {}
    except (json.JSONDecodeError, AttributeError):
        return None, None
    request_id = payload.get("request_id")
    return (
        request_id if isinstance(request_id, str) else None,
        payload.get("finish_reason"),
    )


def scan_trace(path: Path) -> dict[str, Any]:
    """One trace file, reduced to counters. No text of any kind is retained."""

    completion_tokens: dict[str, int | None] = {}
    finish_reasons: dict[str, str | None] = {}
    request_max_tokens: dict[str, int] = {}
    roles: dict[str, str] = {}
    malformed = 0

    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            channel = _channel(line)
            if channel == "MODEL_REQUEST":
                # The configured completion cap only. A request line's
                # history, evidence and audio references are never parsed.
                cap = _MAX_TOKENS.search(line, 0, _REQUEST_HEAD)
                record = _RECORD_ID.search(
                    line, max(0, len(line) - _RECORD_ID_TAIL)
                )
                if cap and record:
                    request_max_tokens[record.group(1).split("/", 1)[0]] = int(
                        cap.group(1)
                    )
            elif channel == "MODEL_RESPONSE":
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                record_id = str(record.get("record_id", ""))
                request_id = record_id.split("/", 1)[0]
                usage = (record.get("payload") or {}).get("usage") or {}
                tokens = usage.get("completion_tokens")
                completion_tokens[request_id] = (
                    tokens if isinstance(tokens, int) else None
                )
            elif channel == "MODEL_WIRE_RESPONSE":
                request_id, finish = _wire_finish_reason(line)
                if request_id is None:
                    malformed += 1
                    continue
                finish_reasons[request_id] = finish
            elif channel == "USE":
                # Cheap reject: the role id lives only on the per-contact USE
                # record, whose record_id ends with this suffix. Every other
                # USE record (tool calls, rejections) is skipped unparsed.
                if "/native-role-contact" not in line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                record_id = str(record.get("record_id", ""))
                if not record_id.endswith("/native-role-contact"):
                    continue
                role = (record.get("payload") or {}).get("use_role_id")
                if isinstance(role, str) and role:
                    roles.setdefault(record_id.split("/", 1)[0], role)

    per_role: dict[str, dict[str, Any]] = {}
    finish_counts: Counter[str] = Counter()
    finite_contacts: list[dict[str, Any]] = []
    for request_id, tokens in sorted(completion_tokens.items()):
        role = roles.get(request_id, UNASSIGNED_ROLE)
        bucket = per_role.setdefault(
            role,
            {
                "contacts": 0,
                "max_completion_tokens": None,
                "at_or_above_near_cap": 0,
                "at_output_cap": 0,
                "at_configured_cap": 0,
                "unknown_configured_cap": 0,
                "unknown_completion_tokens": 0,
                "finish_reason_counts": {},
            },
        )
        bucket["contacts"] += 1
        # A completion is finite exactly when it reached ITS OWN request's
        # cap, which differs by cell (64, 256, 512): the cap is read from
        # the request rather than assumed from the geometry.
        cap = request_max_tokens.get(request_id)
        if cap is None:
            bucket["unknown_configured_cap"] += 1
        elif tokens is not None and tokens >= cap:
            bucket["at_configured_cap"] += 1
        if tokens is None:
            bucket["unknown_completion_tokens"] += 1
        else:
            current = bucket["max_completion_tokens"]
            if current is None or tokens > current:
                bucket["max_completion_tokens"] = tokens
            if tokens >= NEAR_CAP_TOKENS:
                bucket["at_or_above_near_cap"] += 1
            if tokens == OUTPUT_CAP_TOKENS:
                bucket["at_output_cap"] += 1
        finish = finish_reasons.get(request_id)
        label = finish if isinstance(finish, str) else "<no wire record>"
        finish_counts[label] += 1
        bucket["finish_reason_counts"][label] = (
            bucket["finish_reason_counts"].get(label, 0) + 1
        )
        if isinstance(finish, str) and finish in FINITE_FINISH_REASONS:
            finite_contacts.append(
                {
                    "request_id": request_id,
                    "role": role,
                    "finish_reason": finish,
                    "completion_tokens": tokens,
                }
            )

    return {
        "contacts": len(completion_tokens),
        "wire_records": len(finish_reasons),
        "configured_max_tokens": dict(
            sorted(Counter(request_max_tokens.values()).items())
        ),
        "role_labelled_contacts": sum(
            1 for request_id in completion_tokens if request_id in roles
        ),
        "finish_reason_counts": dict(sorted(finish_counts.items())),
        "per_role": {role: per_role[role] for role in sorted(per_role)},
        "finite_contacts": finite_contacts,
        "malformed_records": malformed,
    }


def _manifest_status(attempt: Path) -> tuple[str | None, str | None]:
    """``(status, manifest file name)`` of an attempt directory."""

    manifests = sorted(attempt.glob("*.run-manifest.json"))
    if not manifests:
        return None, None
    try:
        document = json.loads(manifests[0].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FiniteCompletionExposureScanError(
            f"cannot read {manifests[0]}: {error}"
        ) from error
    status = document.get("status") if isinstance(document, dict) else None
    return (status if isinstance(status, str) else None), manifests[0].name


def scan(
    data_dir: Path,
    *,
    run_prefix: str = DEFAULT_RUN_PREFIX,
    control_runs: tuple[str, ...] = DEFAULT_CONTROL_RUNS,
) -> dict[str, Any]:
    runs_root = data_dir / "runs"
    if not runs_root.is_dir():
        raise FiniteCompletionExposureScanError(f"{runs_root} is not a directory")

    sealed: list[dict[str, Any]] = []
    controls: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for run_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        run_id = run_dir.name
        is_control = run_id in control_runs
        if not run_id.startswith(run_prefix) and not is_control:
            continue
        for attempt in sorted(p for p in run_dir.iterdir() if p.is_dir()):
            status, manifest_name = _manifest_status(attempt)
            trace = attempt / f"{run_id}.trace.jsonl"
            row: dict[str, Any] = {
                "run_id": run_id,
                "attempt_id": attempt.name,
                "manifest": manifest_name,
                "manifest_status": status,
                "trace": trace.name if trace.is_file() else None,
            }
            sealed_attempt = status == SEALED_STATUS
            if not trace.is_file():
                row["reason"] = "no trace file"
                skipped.append(row)
                continue
            if not sealed_attempt and not is_control:
                row["reason"] = f"manifest status {status!r} is not {SEALED_STATUS}"
                skipped.append(row)
                continue
            row["trace_bytes"] = trace.stat().st_size
            row.update(scan_trace(trace))
            if sealed_attempt:
                sealed.append(row)
            else:
                row["control"] = True
                controls.append(row)

    def _totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
        counts: Counter[str] = Counter()
        native_counts: Counter[str] = Counter()
        for row in rows:
            counts.update(row["finish_reason_counts"])
            for role, bucket in row["per_role"].items():
                if role != UNASSIGNED_ROLE:
                    native_counts.update(bucket["finish_reason_counts"])

        def _sum(field: str, *, native_only: bool = False) -> int:
            return sum(
                bucket[field]
                for row in rows
                for role, bucket in row["per_role"].items()
                if not native_only or role != UNASSIGNED_ROLE
            )

        return {
            "attempts": len(rows),
            "contacts": sum(row["contacts"] for row in rows),
            "finish_reason_counts": dict(sorted(counts.items())),
            "finite_contacts": sum(len(row["finite_contacts"]) for row in rows),
            "at_output_cap": _sum("at_output_cap"),
            "at_or_above_near_cap": _sum("at_or_above_near_cap"),
            "at_configured_cap": _sum("at_configured_cap"),
            "unknown_configured_cap": _sum("unknown_configured_cap"),
            # The native-episode half: the contacts a native ROLE made,
            # which are the only ones finite_completion_policy governs.
            "native_role_contacts": _sum("contacts", native_only=True),
            "native_finish_reason_counts": dict(sorted(native_counts.items())),
            "native_finite_contacts": sum(
                1
                for row in rows
                for contact in row["finite_contacts"]
                if contact["role"] != UNASSIGNED_ROLE
            ),
            "native_at_configured_cap": _sum(
                "at_configured_cap", native_only=True
            ),
        }

    sealed_totals = _totals(sealed)
    return {
        "schema": "saea-finite-completion-exposure-scan-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir),
        "run_prefix": run_prefix,
        "sealed_status": SEALED_STATUS,
        "near_cap_tokens": NEAR_CAP_TOKENS,
        "output_cap_tokens": OUTPUT_CAP_TOKENS,
        "finite_finish_reasons": list(FINITE_FINISH_REASONS),
        "sealed_attempts": sealed,
        "sealed_totals": sealed_totals,
        "control_attempts": controls,
        "control_totals": _totals(controls),
        "skipped": skipped,
        "zero_finite_completions_on_every_sealed_attempt": (
            sealed_totals["finite_contacts"] == 0
        ),
        "zero_finite_completions_on_every_sealed_native_role_contact": (
            sealed_totals["native_finite_contacts"] == 0
            and sealed_totals["native_at_configured_cap"] == 0
        ),
        "semantics": (
            "Counters only. No response text, transcript or gold label is read, "
            "printed or persisted; the preserved base64 wire body is never "
            "decoded. A contact with no MODEL_WIRE_RESPONSE record is counted "
            "under '<no wire record>' rather than assumed to have stopped "
            "normally."
        ),
        "model_calls": 0,
        "encoder_calls": 0,
        "tokenizer_calls": 0,
        "scorer_invocations": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")),
        help="the data root holding runs/ (defaults to $SPEECHRL_DATA_DIR)",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-prefix", default=DEFAULT_RUN_PREFIX)
    parser.add_argument(
        "--control-run",
        action="append",
        default=None,
        help="an ABORTED run id to scan as a positive control (repeatable)",
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing --out file"
    )
    args = parser.parse_args(argv)

    if not str(args.data_dir):
        parser.error("--data-dir is required when SPEECHRL_DATA_DIR is unset")
    controls = tuple(args.control_run) if args.control_run else DEFAULT_CONTROL_RUNS

    result = scan(
        args.data_dir.resolve(), run_prefix=args.run_prefix, control_runs=controls
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if args.force else "x"
    with args.out.open(mode, encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")

    print(
        json.dumps(
            {
                "sealed_attempts": result["sealed_totals"]["attempts"],
                "sealed_contacts": result["sealed_totals"]["contacts"],
                "sealed_finite_contacts": result["sealed_totals"]["finite_contacts"],
                "sealed_native_role_contacts": result["sealed_totals"][
                    "native_role_contacts"
                ],
                "sealed_native_finite_contacts": result["sealed_totals"][
                    "native_finite_contacts"
                ],
                "control_attempts": result["control_totals"]["attempts"],
                "control_finite_contacts": result["control_totals"]["finite_contacts"],
                "out": str(args.out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
