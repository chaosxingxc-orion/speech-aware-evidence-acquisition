"""P-A2T Stage-1 A0 baseline offline read suite (pinned, pre-registered).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` / ``flight-receipt.json`` (``rails.runner.
run_rails_experiment``'s zero-supply arm / the flight launcher's own write
shape, see ``docs/checks/speech-aware-evidence-acquisition/
2026-08-18-pa2t-a0-flight/launcher/launch_pa2t_a0.py``) through the SAME
frozen scorer every other consumer of this carrier uses
(``rails.adapters.audio2tool.Audio2ToolAdapter.score``, which itself wraps
``reproduction.toolcall_scoring.score_item`` / ``parse_tool_calls_text`` --
reused directly here, never re-derived).

Purpose (``docs/readiness/2026-08-17-pa2t-preregistration-draft.md`` section
8, item 4): this is Stage 1 of the P-A2T probe family -- a baseline read, NOT
a probe. It carries no branch rules (SUPPLY-CONVERTS/COPY-TRAP/INERT/VOID
have no analog here). Its two deliverables are (a) the REAL tool-acc/EM gap
on the frozen 400-item discovery split, replacing the retired, unsourced
84.6%/15.6% headroom claim (``configs/probes/g0-binding/pa2t-binding.json``
``headroom_extraction.cited_premise_unverified``), and (b) the Stage-2
headroom sample list -- ``{sample ids : tool_accuracy == 1.0 AND
exact_match == 0.0}`` -- that seeds the next probe's registration
(``pa2t-binding.json`` ``headroom_extraction.proposed_selection_rule``).

Sources of truth this module implements EXACTLY (never re-derives on its own
authority):

- ``rails.adapters.audio2tool.Audio2ToolAdapter.score`` for every per-row
  metric (``tool_accuracy``/``exact_match``/``slot_precision``/
  ``slot_recall``/``slot_f1``/``parsed``).
- ``reproduction.toolcall_scoring.parse_tool_calls_text`` for the predicted
  tool-call list an "empty tool-call" row is judged against -- the same
  parser the adapter's own ``score`` calls internally.
- ``data.audio2tool.audio2tool_receipts`` for the frozen split's sample
  universe, using the EXACT same ``f"{tier}:{id:06d}"`` derivation
  ``rails.adapters.audio2tool.Audio2ToolAdapter.load_split`` uses -- never a
  hardcoded sample count, so this suite enforces exact identity with
  whichever receipt it is pointed at rather than a second, driftable
  "400 / 8x50" constant.
- ``rails.runner.ZERO_SUPPLY_ARM`` for the one arm this baseline flies.

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried, because the
mission brief is genuinely underspecified on these exact points -- each is a
documented, reviewable choice, not a silent guess):

1. "empty tool-call rate" (mission brief, replacing the FLOWN ledger note's
   own "17/400 items return an empty tool-call list" observation) is read as
   ``len(parse_tool_calls_text(response_text)[0]) == 0`` -- the predicted
   call list is literally empty -- regardless of the ``parsed`` flag (a
   syntactically valid ``"[]"`` response is still an empty-tool-call row,
   not a parse failure). See :func:`is_empty_tool_call`.
2. Every structural/harness check this module runs (malformed row, duplicate
   sample_id, wrong arm, non-``COMPLETED`` receipt, non-empty
   ``request_failures``, an ``arms`` field other than
   ``[ZERO_SUPPLY_ARM]``, a split-identity-hash mismatch between the flight
   receipt and the frozen probe receipt, missing/extra sample ids against
   the frozen receipt) is a hard, fail-closed REFUSAL
   (:class:`A2tReadError`) raised BEFORE any scoring happens -- never a
   soft flag folded into an emitted report. This baseline read carries no
   branch-rule state machine (unlike ``analysis.pslu_read``'s VOID branch)
   for a defect to fall into, so refusal is the only fail-closed behavior
   available; "machine harness checks, fail-closed" (mission brief) is read
   literally. See :func:`_harness_defect_reasons`.
3. A per-row recheck (recomputed ``Audio2ToolAdapter.score`` vs. the
   ``metrics`` the flight already embedded in ``outputs.jsonl``) is
   INFORMATIONAL, not fatal: every number in the emitted report always comes
   from the fresh recomputation, so a mismatch cannot corrupt the report --
   it is surfaced as a count/list precisely so a reviewer can see whether the
   flight-time scorer and this suite's own scorer ever disagreed, without
   that disagreement blocking the read outright (the harness-defect checks
   above are the fail-closed gate; this is a secondary integrity signal).
   See :func:`_recheck_row`.
4. Exactly one committed probe-sample receipt must declare the requested
   ``split_role`` (fail-closed on zero or more than one) -- this is a
   PINNED single-split read suite (the frozen 400-item discovery split named
   in ``configs/probes/g0-binding/pa2t-a0-flight.json``), not a generic
   multi-receipt aggregator. See :func:`_load_split_receipt`.
5. The split-identity-hash cross-check compares the flight receipt's own
   ``split_identity_hash`` field against the frozen probe receipt's own
   ``split_identity_hash`` field (each independently computed/verified
   elsewhere -- ``core.session``/the launcher for the former,
   ``data.audio2tool._verify_receipt`` for the latter) rather than against a
   hardcoded module constant, so this suite stays testable against any
   synthetic receipt while still catching drift for the real pinned split.
6. Performance note for the flying-later read mission, not fixed here per
   "reuse, never reimplement": ``Audio2ToolAdapter.score`` re-reads and
   re-parses every relevant tier manifest from disk on EVERY call (its own,
   unmodified implementation) -- scoring 400 rows means 400 such reloads.
   This module calls the adapter's own ``score`` method unchanged rather
   than routing around that cost with a second, parallel implementation.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_a2t_read.py``, reusing the shared ``audio2tool_world``
fixture already used by ``tests/unit/test_rails_audio2tool_adapter.py``).
This module is never run against the real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-BASE-a2t-a0-400/``) by the task that wrote
it; a later, separately-registered one-shot read session points
``build_a2t_report``/the CLI at the real COMPLETED attempt
(``attempt-20260818T055500Z-res315`` per the exposure ledger's FLOWN note).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..reproduction.toolcall_scoring import parse_tool_calls_text
from ..rails.adapters.audio2tool import Audio2ToolAdapter, Audio2ToolSample
from ..rails.obs import AudioRef
from ..rails.runner import ZERO_SUPPLY_ARM

REPORT_SCHEMA = "saea-a2t-a0-read-v1"
DEFAULT_SPLIT_ROLE = "discovery"

# Any placeholder is fine: Audio2ToolAdapter.score only ever reads
# sample.sample_id (module docstring point above) -- audio_ref/audio_seconds/
# media_relpath are never touched by scoring, so this suite never needs to
# open a single audio file to read the flight it never opened one to fly.
_PLACEHOLDER_AUDIO_REF = AudioRef(path="unused", sha256="0" * 64).validate()


class A2tReadError(RuntimeError):
    """Malformed attempt-dir input or a harness defect the mission's own
    "machine harness checks, fail-closed" requires refusing on -- never
    raised for an ordinary, structurally clean baseline read."""


# ---------------------------------------------------------------------------
# Loading: outputs.jsonl / flight-receipt.json / the frozen probe receipt.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutputRow:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: Mapping[str, object]

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "OutputRow":
        metrics = document["metrics"]
        consumption = document["consumption"]
        if not isinstance(metrics, Mapping):
            raise ValueError(f"'metrics' must be an object, got {type(metrics).__name__}")
        if not isinstance(consumption, Mapping):
            raise ValueError(f"'consumption' must be an object, got {type(consumption).__name__}")
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            messages=tuple(document["messages"]),
            response_text=str(document["response_text"]),
            metrics=metrics,
            consumption=consumption,
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[tuple[OutputRow, ...], tuple[str, ...]]:
    """``(valid_rows, malformed_row_reasons)``. A malformed row (invalid
    JSON, a missing required key, or a wrong-typed field) is NEVER silently
    dropped and never crashes this loader outright -- it is collected as its
    own harness-defect reason (note 2 above) so the caller can refuse with a
    full, single diagnostic rather than an opaque traceback on line one."""

    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise A2tReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[OutputRow] = []
    malformed: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
            if not isinstance(document, Mapping):
                raise ValueError(f"row must be a JSON object, got {type(document).__name__}")
            row = OutputRow.from_json(document)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            malformed.append(f"outputs.jsonl line {line_no}: malformed row: {error!r}")
            continue
        rows.append(row)
    if not rows and not malformed:
        raise A2tReadError(f"{path}: zero rows")
    return tuple(rows), tuple(malformed)


def load_flight_receipt(attempt_dir: Path) -> Mapping[str, object] | None:
    """The full parsed ``flight-receipt.json``, or ``None`` when the file is
    missing entirely (itself a harness defect: the launcher writes this file
    unconditionally once it starts). A malformed (unparseable) receipt
    raises directly -- unlike a malformed OUTPUT row, there is exactly one
    of these per attempt and no partial-file recovery is meaningful."""

    path = Path(attempt_dir) / "flight-receipt.json"
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise A2tReadError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(document, Mapping):
        raise A2tReadError(f"{path}: must be a JSON object")
    return document


def _load_split_receipt(repo_root: Path, split_role: str) -> Mapping[str, object]:
    """Note 4: exactly one committed probe-sample receipt must declare
    ``split_role`` -- this suite is pinned to one specific frozen split."""

    from ..data.audio2tool import audio2tool_receipts

    receipts = audio2tool_receipts(repo_root)
    matching = [payload for payload in receipts.values() if payload.get("split_role") == split_role]
    if len(matching) != 1:
        raise A2tReadError(
            f"expected exactly one audio2tool probe receipt with split_role={split_role!r}, "
            f"found {len(matching)}"
        )
    return matching[0]


def expected_sample_ids(receipt: Mapping[str, object]) -> tuple[str, ...]:
    """The frozen split's full sample-id universe, sorted -- the EXACT same
    ``f"{tier}:{id:06d}"`` derivation ``Audio2ToolAdapter.load_split`` uses
    (module docstring: never a second, hardcoded count)."""

    ids = {f"{item['tier']}:{int(item['id']):06d}" for item in receipt["items"]}
    return tuple(sorted(ids))


def _tier_of(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


# ---------------------------------------------------------------------------
# Per-row scoring: Audio2ToolAdapter.score reused directly (module docstring).
# ---------------------------------------------------------------------------


def is_empty_tool_call(response_text: str) -> bool:
    """Note 1: the predicted call list is literally empty."""

    predicted, _parsed = parse_tool_calls_text(response_text)
    return len(predicted) == 0


def _numbers_match(a: object, b: object) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-9  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return a == b


_RECHECK_FIELDS: tuple[str, ...] = (
    "tool_accuracy",
    "exact_match",
    "slot_precision",
    "slot_recall",
    "slot_f1",
    "parsed",
)


@dataclass(frozen=True)
class RecheckMismatch:
    sample_id: str
    field: str
    embedded: object
    recomputed: object


def _recheck_row(row: OutputRow, recomputed: Mapping[str, object]) -> tuple[RecheckMismatch, ...]:
    """Note 3: informational only -- never fatal, never trusted over the
    fresh recomputation this module always reports."""

    mismatches: list[RecheckMismatch] = []
    for field in _RECHECK_FIELDS:
        embedded_value = row.metrics.get(field)
        recomputed_value = recomputed[field]
        if field == "parsed":
            if embedded_value != recomputed_value:
                mismatches.append(RecheckMismatch(row.sample_id, field, embedded_value, recomputed_value))
        elif not _numbers_match(embedded_value, recomputed_value):
            mismatches.append(RecheckMismatch(row.sample_id, field, embedded_value, recomputed_value))
    return tuple(mismatches)


@dataclass(frozen=True)
class RowScore:
    row: OutputRow
    tier: str
    metrics: Mapping[str, object]
    empty_tool_call: bool
    recheck_mismatches: tuple[RecheckMismatch, ...]


def score_row(adapter: Audio2ToolAdapter, row: OutputRow) -> RowScore:
    """Reuses ``Audio2ToolAdapter.score`` UNCHANGED (module docstring: reuse,
    never reimplement) -- the sample passed carries only the ``sample_id``
    field that method actually reads."""

    sample = Audio2ToolSample(
        sample_id=row.sample_id,
        audio_ref=_PLACEHOLDER_AUDIO_REF,
        audio_seconds=0.0,
        media_relpath="",
    )
    metrics = adapter.score(sample, row.response_text)
    return RowScore(
        row=row,
        tier=_tier_of(row.sample_id),
        metrics=metrics,
        empty_tool_call=is_empty_tool_call(row.response_text),
        recheck_mismatches=_recheck_row(row, metrics),
    )


# ---------------------------------------------------------------------------
# Harness-defect checks (note 2: fail-closed refusal, never a soft flag).
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    malformed_row_reasons: Sequence[str],
    flight_receipt: Mapping[str, object] | None,
    rows: Sequence[OutputRow],
    expected_ids: Sequence[str],
    split_identity_hash: str,
) -> tuple[str, ...]:
    reasons: list[str] = list(malformed_row_reasons)

    if flight_receipt is None:
        reasons.append("flight-receipt.json missing")
    else:
        status = flight_receipt.get("status")
        if status != "COMPLETED":
            reasons.append(
                f"flight-receipt status={status!r} (expected 'COMPLETED'); "
                f"error={flight_receipt.get('error')!r}"
            )
        failures = flight_receipt.get("request_failures")
        if failures:
            reasons.append(f"flight-receipt request_failures non-empty: {len(failures)} failure(s)")
        arms = flight_receipt.get("arms")
        if arms != [ZERO_SUPPLY_ARM]:
            reasons.append(f"flight-receipt arms={arms!r}, expected [{ZERO_SUPPLY_ARM!r}]")
        receipt_hash = flight_receipt.get("split_identity_hash")
        if receipt_hash != split_identity_hash:
            reasons.append(
                f"split_identity_hash mismatch: flight-receipt={receipt_hash!r} "
                f"vs. frozen probe receipt={split_identity_hash!r}"
            )

    seen: set[str] = set()
    duplicates: list[str] = []
    wrong_arm: list[str] = []
    for row in rows:
        if row.sample_id in seen:
            duplicates.append(row.sample_id)
        seen.add(row.sample_id)
        if row.arm != ZERO_SUPPLY_ARM:
            wrong_arm.append(f"{row.sample_id} (arm={row.arm!r})")
    if duplicates:
        reasons.append(f"{len(duplicates)} duplicate sample_id row(s): {sorted(set(duplicates))[:5]}")
    if wrong_arm:
        reasons.append(f"{len(wrong_arm)} row(s) on an arm other than {ZERO_SUPPLY_ARM!r}: {wrong_arm[:5]}")

    expected_set = set(expected_ids)
    got_set = {row.sample_id for row in rows}
    missing = expected_set - got_set
    extra = got_set - expected_set
    if missing:
        reasons.append(f"missing {len(missing)} sample(s) from the frozen receipt: {sorted(missing)[:5]}")
    if extra:
        reasons.append(f"{len(extra)} sample(s) not in the frozen receipt: {sorted(extra)[:5]}")

    return tuple(reasons)


# ---------------------------------------------------------------------------
# Per-tier / overall aggregation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TierAggregate:
    tier: str
    n_samples: int
    tool_accuracy: float
    exact_match: float
    gap: float
    empty_tool_call_count: int
    empty_tool_call_rate: float


def build_aggregate(label: str, scores: Sequence[RowScore]) -> TierAggregate:
    n = len(scores)
    if n == 0:
        return TierAggregate(label, 0, 0.0, 0.0, 0.0, 0, 0.0)
    tool_accuracy = sum(float(s.metrics["tool_accuracy"]) for s in scores) / n
    exact_match = sum(float(s.metrics["exact_match"]) for s in scores) / n
    empty_count = sum(1 for s in scores if s.empty_tool_call)
    return TierAggregate(
        tier=label,
        n_samples=n,
        tool_accuracy=tool_accuracy,
        exact_match=exact_match,
        gap=tool_accuracy - exact_match,
        empty_tool_call_count=empty_count,
        empty_tool_call_rate=empty_count / n,
    )


def stage2_headroom_ids(scores: Sequence[RowScore]) -> tuple[str, ...]:
    """The Stage-2 headroom list (mission brief / ``pa2t-binding.json``
    ``headroom_extraction.proposed_selection_rule``): samples where tool
    selection was correct but the call was not an exact match."""

    return tuple(
        sorted(
            s.row.sample_id
            for s in scores
            if float(s.metrics["tool_accuracy"]) == 1.0 and float(s.metrics["exact_match"]) == 0.0
        )
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tReadReport:
    attempt_dir: Path
    flight_status: str | None
    split_identity_hash: str
    overall: TierAggregate
    by_tier: Mapping[str, TierAggregate]
    headroom_ids: tuple[str, ...]
    recheck_mismatches: tuple[RecheckMismatch, ...]


def build_a2t_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    split_role: str = DEFAULT_SPLIT_ROLE,
) -> A2tReadReport:
    attempt_dir = Path(attempt_dir)
    repo_root = Path(repo_root)

    rows, malformed_row_reasons = load_attempt_rows(attempt_dir)
    flight_receipt = load_flight_receipt(attempt_dir)
    receipt = _load_split_receipt(repo_root, split_role)
    expected_ids = expected_sample_ids(receipt)
    split_identity_hash = str(receipt["split_identity_hash"])

    defect_reasons = _harness_defect_reasons(
        malformed_row_reasons=malformed_row_reasons,
        flight_receipt=flight_receipt,
        rows=rows,
        expected_ids=expected_ids,
        split_identity_hash=split_identity_hash,
    )
    if defect_reasons:
        raise A2tReadError("harness defect(s) detected; refusing to score:\n  " + "\n  ".join(defect_reasons))

    adapter = Audio2ToolAdapter(lock, root, repo_root=repo_root)
    scores = [score_row(adapter, row) for row in sorted(rows, key=lambda r: r.sample_id)]

    scores_by_tier: dict[str, list[RowScore]] = {}
    for score in scores:
        scores_by_tier.setdefault(score.tier, []).append(score)
    by_tier = {tier: build_aggregate(tier, tier_scores) for tier, tier_scores in sorted(scores_by_tier.items())}
    overall = build_aggregate("overall", scores)

    recheck_mismatches = tuple(m for s in scores for m in s.recheck_mismatches)

    return A2tReadReport(
        attempt_dir=attempt_dir,
        flight_status=None if flight_receipt is None else flight_receipt.get("status"),
        split_identity_hash=split_identity_hash,
        overall=overall,
        by_tier=by_tier,
        headroom_ids=stage2_headroom_ids(scores),
        recheck_mismatches=recheck_mismatches,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _tier_json(aggregate: TierAggregate) -> dict[str, object]:
    return {
        "tier": aggregate.tier,
        "n_samples": aggregate.n_samples,
        "tool_accuracy": aggregate.tool_accuracy,
        "exact_match": aggregate.exact_match,
        "gap": aggregate.gap,
        "empty_tool_call_count": aggregate.empty_tool_call_count,
        "empty_tool_call_rate": aggregate.empty_tool_call_rate,
    }


def report_to_json(report: A2tReadReport) -> dict[str, object]:
    return {
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "split_identity_hash": report.split_identity_hash,
        "overall": _tier_json(report.overall),
        "by_tier": {tier: _tier_json(agg) for tier, agg in report.by_tier.items()},
        "headroom": {
            "note": "Stage-2 headroom list: tool_accuracy == 1.0 AND exact_match == 0.0",
            "count": len(report.headroom_ids),
            "sample_ids": list(report.headroom_ids),
        },
        "recheck_mismatch_count": len(report.recheck_mismatches),
        "recheck_mismatches": [
            {
                "sample_id": m.sample_id,
                "field": m.field,
                "embedded": m.embedded,
                "recomputed": m.recomputed,
            }
            for m in report.recheck_mismatches
        ],
    }


def headroom_to_json(report: A2tReadReport) -> dict[str, object]:
    """Standalone artifact (mission brief: "written as a machine JSON")
    meant to seed the next probe's registration directly, without pulling
    the rest of the read report along with it."""

    return {
        "schema": "saea-a2t-a0-headroom-v1",
        "note": "seeds the Stage-2 supply-probe registration (tool_accuracy == 1.0 AND exact_match == 0.0)",
        "attempt_dir": str(report.attempt_dir),
        "split_identity_hash": report.split_identity_hash,
        "count": len(report.headroom_ids),
        "sample_ids": list(report.headroom_ids),
    }


def render_report(report: A2tReadReport) -> str:
    lines = [
        "P-A2T Stage-1 A0 baseline pinned offline read",
        "=" * 70,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r}",
        f"split identity hash: {report.split_identity_hash}",
        "",
        "REAL tool-acc/EM gap (replaces the retired 84.6%/15.6% headroom claim)",
        f"  overall: n={report.overall.n_samples} tool_acc={report.overall.tool_accuracy:.4f} "
        f"EM={report.overall.exact_match:.4f} gap={report.overall.gap:+.4f}",
        "",
        "Per-tier breakdown",
    ]
    header = f"  {'tier':<24}{'n':>4}{'tool_acc':>10}{'EM':>9}{'gap':>9}{'empty':>7}{'empty_rate':>12}"
    lines.append(header)
    for tier in sorted(report.by_tier):
        agg = report.by_tier[tier]
        lines.append(
            f"  {tier:<24}{agg.n_samples:>4}{agg.tool_accuracy:>10.4f}{agg.exact_match:>9.4f}"
            f"{agg.gap:>9.4f}{agg.empty_tool_call_count:>7}{agg.empty_tool_call_rate:>12.4f}"
        )
    lines.append("")

    lines.append(
        f"overall empty-tool-call rate: {report.overall.empty_tool_call_count}/{report.overall.n_samples} "
        f"({report.overall.empty_tool_call_rate:.4f})"
    )
    lines.append("")

    lines.append(f"Stage-2 headroom list (tool_accuracy==1.0 AND exact_match==0.0): {len(report.headroom_ids)} sample(s)")
    for sample_id in report.headroom_ids[:20]:
        lines.append(f"  {sample_id}")
    if len(report.headroom_ids) > 20:
        lines.append(f"  ... (+{len(report.headroom_ids) - 20} more; full list in headroom.json)")
    lines.append("")

    lines.append(f"recheck mismatches (recomputed vs. flight-embedded metrics, informational only): {len(report.recheck_mismatches)}")
    for mismatch in report.recheck_mismatches[:10]:
        lines.append(
            f"  {mismatch.sample_id}.{mismatch.field}: embedded={mismatch.embedded!r} "
            f"recomputed={mismatch.recomputed!r}"
        )
    if len(report.recheck_mismatches) > 10:
        lines.append(f"  ... (+{len(report.recheck_mismatches) - 10} more)")

    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="a2t-read",
        description=(
            "P-A2T Stage-1 A0 baseline pinned offline read suite: official tool-accuracy/"
            "exact-match per tier and overall, the tool-acc-minus-EM gap, the empty-tool-call "
            "rate, and the Stage-2 headroom sample list. Model-free, read-only; never opens a "
            "model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the flight's own attempt directory (carries outputs.jsonl)")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write verdict.json / report.txt / headroom.json")
    parser.add_argument(
        "--split-role", default=DEFAULT_SPLIT_ROLE,
        help=f"the frozen probe receipt's split_role to read against (default: {DEFAULT_SPLIT_ROLE!r})",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock and the frozen probe receipt",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT

    output_dir = Path(args.output_dir)
    verdict_path = output_dir / "verdict.json"
    if verdict_path.exists():
        print(
            f"REFUSED: {verdict_path} already exists -- this suite refuses to run twice against the same "
            "output dir (one-shot read discipline); choose a fresh --output-dir if a genuinely new read is "
            "intended",
            file=sys.stderr,
        )
        return 1

    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()

    try:
        report = build_a2t_report(
            args.attempt_dir, lock, root, repo_root=repo_root, split_role=args.split_role
        )
    except A2tReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, report_to_json(report))
    write_json_artifact(output_dir / "headroom.json", headroom_to_json(report))
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    print(f"wrote Stage-2 headroom list to {output_dir / 'headroom.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
