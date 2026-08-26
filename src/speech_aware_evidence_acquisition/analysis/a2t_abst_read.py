"""P-A2T abstention-asymmetry 2x2 offline read suite (pinned,
pre-registered, ``SAEA-PROBE-a2t-abst-44``): ``docs/readiness/
2026-08-19-a2t-abst-preregistration-REGISTERED.md``.

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` (``rails.probes.a2t_abst_flight.run_a2t_abst_flight``'s
own row shape, byte-identical to ``rails.probes.a2t_s2_flight.
A2tS2ArmResult``'s) through the SAME frozen call-parsing primitive every
other consumer of this carrier uses
(``reproduction.toolcall_scoring.parse_tool_calls_text`` -- reused
directly, never re-derived).

NO GOLD IS EVER READ (a structural fact, not merely a discipline): this
probe's metrics are well-formed-abstention / confabulated-call /
parse-failure rates -- a CLASSIFICATION of each response's own SHAPE,
never a correctness judgement against an expected tool call. Unlike every
sibling A2T read suite in this family, :func:`build_a2t_abst_report` never
calls ``data.audio2tool.load_expected_calls`` and never needs a ``lock``/
``root`` parameter at all.

REUSE, NOT RE-DERIVATION: ``analysis.a2t_s2_read.OutputRow``/
``load_attempt_rows``/``load_flight_receipt``/``ClauseResult`` (the SAME
row shape and clause-result primitives Stage-2's own read suite already
built and tested) and ``analysis.bootstrap.paired_cluster_bootstrap`` (the
shared bootstrap primitive) are reused directly rather than re-implemented.

Per-row classification (mission brief, "well-formed-abstention (empty call,
parseable), confabulated-call (emits any tool call), parse-failure"):
``reproduction.toolcall_scoring.parse_tool_calls_text`` fails closed to
``([], False)`` on ANY parse failure (that function's own docstring), so the
predicted-call list is non-empty ONLY when parsing succeeded -- the three
categories are therefore mechanically mutually exclusive and exhaustive
over every response:

- ``parse_failure``: ``not parsed``.
- ``well_formed_abstention``: ``parsed and predicted == []``.
- ``confabulated_call``: ``parsed and predicted != []``.

See :func:`classify_response`.

ENGINEERING-INTERPRETATION NOTES:

1. Harness-defect checks (malformed rows, non-``COMPLETED`` receipt,
   non-empty ``request_failures``, an unexpected cell list (this probe's
   own flight-receipt names its 4 CELLS under ``cells``, with ``arms``
   accepted as an alias, never a Stage-2 arm name; a receipt declaring
   neither key is a defect), a split-identity-hash mismatch, an unknown-cell row, a
   duplicate ``(cell, sample_id)`` pair, a per-cell row count other than
   ``ABST_N`` (11), or the four cells NOT sharing the identical sample-id
   set (the per-sample 4-cell table requires every sample to carry all four
   cells)) are ALL hard, fail-closed refusals (:class:`A2tAbstReadError`)
   raised BEFORE any classification happens -- mirrors ``analysis.
   a2t_s2_read``'s own convention (its module docstring note 1).
2. Verdicts (mission brief: "mechanical, raw-count floors at n=11"):
   evaluated on RAW COUNTS against the registered floors, checked in the
   registered order (ASYMMETRY-CONFIRMED, then ASYMMETRY-REFUTED, else
   INCONCLUSIVE-ABST) -- mutually exclusive by construction (CONFIRMED's
   own ``confabulated_call(TP-S) >= 8/11`` caps ``well_formed_abstention
   (TP-S)`` at <= 3/11, which can never also satisfy REFUTED's own
   ``>= 6/11`` floor).
3. Descriptive bootstrap CI (mission brief: "bootstrap CI published
   descriptively -- n is small by design, this is a bounded mechanism
   probe"): computed for the three verdict-critical rates named in the
   registered clauses (``well_formed_abstention(TW-A)``,
   ``confabulated_call(TP-S)``, ``well_formed_abstention(TP-S)``) via the
   shared ``analysis.bootstrap.paired_cluster_bootstrap`` primitive --
   descriptive only, never gates the mechanical raw-count verdict above.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..reproduction.toolcall_scoring import parse_tool_calls_text
from ..rails.probes.a2t_abst_flight import A2T_ABST_CELLS, ABST_N, TP_S_CELL, TW_A_CELL
from .a2t_s2_read import ClauseResult, OutputRow, load_attempt_rows, load_flight_receipt
from .bootstrap import BootstrapResult, DEFAULT_CI_LEVEL, DEFAULT_N_REPLICATES, DEFAULT_SEED, paired_cluster_bootstrap

REPORT_SCHEMA = "saea-a2t-abst-read-v1"
RUN_ID = "SAEA-PROBE-a2t-abst-44"
DEFAULT_SPLIT_ROLE = "discovery"

# Prereg section 2, quoted verbatim in each clause's own detail text below.
CONFIRMED_ABSTENTION_TW_A_MIN = 8
CONFIRMED_CONFABULATION_TP_S_MIN = 8
REFUTED_ABSTENTION_TP_S_MIN = 6

WELL_FORMED_ABSTENTION = "well_formed_abstention"
CONFABULATED_CALL = "confabulated_call"
PARSE_FAILURE = "parse_failure"


class A2tAbstReadError(RuntimeError):
    """Malformed attempt-dir input or a harness defect the mission's own
    "machine harness checks, fail-closed" requires refusing on -- never
    raised for an ordinary, structurally clean read."""


# ---------------------------------------------------------------------------
# Per-row classification (module docstring): mutually exclusive, exhaustive.
# ---------------------------------------------------------------------------


def classify_response(response_text: str) -> str:
    predicted, parsed = parse_tool_calls_text(response_text)
    if not parsed:
        return PARSE_FAILURE
    if not predicted:
        return WELL_FORMED_ABSTENTION
    return CONFABULATED_CALL


# ---------------------------------------------------------------------------
# Harness-defect checks (note 1: fail-closed refusal, never a soft flag).
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    malformed_row_reasons: Sequence[str],
    flight_receipt: Mapping[str, object] | None,
    rows_by_cell: Mapping[str, Sequence[OutputRow]],
    unknown_cell_rows: Sequence[OutputRow],
    duplicate_pairs: Sequence[tuple[str, str]],
    split_identity_hash: str,
    expected_n: int,
) -> tuple[str, ...]:
    reasons: list[str] = list(malformed_row_reasons)

    if flight_receipt is None:
        reasons.append("flight-receipt.json missing")
    else:
        status = flight_receipt.get("status")
        if status != "COMPLETED":
            reasons.append(
                f"flight-receipt status={status!r} (expected 'COMPLETED'); error={flight_receipt.get('error')!r}"
            )
        failures = flight_receipt.get("request_failures")
        if failures:
            reasons.append(f"flight-receipt request_failures non-empty: {len(failures)} failure(s)")
        # The flight machinery writes the cell list under ``cells``; ``arms``
        # is accepted as an alias so a receipt of either shape is validated
        # rather than silently read as ``None``. Whichever key(s) a receipt
        # declares must agree with the registered cell list, and a receipt
        # declaring neither is itself a defect.
        declared_cells = [(key, flight_receipt[key]) for key in ("cells", "arms") if key in flight_receipt]
        if not declared_cells:
            reasons.append(
                f"flight-receipt declares neither 'cells' nor 'arms'; expected {list(A2T_ABST_CELLS)!r}"
            )
        for key, value in declared_cells:
            if value != list(A2T_ABST_CELLS):
                reasons.append(f"flight-receipt {key}={value!r}, expected {list(A2T_ABST_CELLS)!r}")
        receipt_hash = flight_receipt.get("split_identity_hash")
        if receipt_hash != split_identity_hash:
            reasons.append(
                f"split_identity_hash mismatch: flight-receipt={receipt_hash!r} "
                f"vs. frozen probe receipt={split_identity_hash!r}"
            )

    for row in unknown_cell_rows:
        reasons.append(f"row on unknown cell {row.arm!r} (sample {row.sample_id!r})")
    for pair in duplicate_pairs:
        reasons.append(f"duplicate row for (cell, sample_id)={pair!r}")

    id_sets: dict[str, set] = {}
    for cell in A2T_ABST_CELLS:
        rows = rows_by_cell.get(cell, ())
        got_ids = [row.sample_id for row in rows]
        if len(got_ids) != len(set(got_ids)):
            dupes = sorted({sid for sid in got_ids if got_ids.count(sid) > 1})
            reasons.append(f"cell {cell}: duplicate sample_id row(s) within the cell: {dupes[:5]}")
        if len(rows) != expected_n:
            reasons.append(f"cell {cell}: row count {len(rows)} != expected {expected_n} (n=11 fail-closed check)")
        id_sets[cell] = set(got_ids)

    if len(set(map(frozenset, id_sets.values()))) > 1:
        reasons.append(
            "the four cells do not share the IDENTICAL sample-id set (the per-sample 4-cell table "
            f"requires it): {({cell: sorted(ids) for cell, ids in id_sets.items()})}"
        )

    return tuple(reasons)


# ---------------------------------------------------------------------------
# Per-cell aggregation + the per-sample 4-cell table.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CellAggregate:
    cell: str
    n_samples: int
    well_formed_abstention_count: int
    well_formed_abstention_rate: float
    confabulated_call_count: int
    confabulated_call_rate: float
    parse_failure_count: int
    parse_failure_rate: float


def build_cell_aggregate(cell: str, classifications: Sequence[str]) -> CellAggregate:
    n = len(classifications)
    abst = sum(1 for c in classifications if c == WELL_FORMED_ABSTENTION)
    confab = sum(1 for c in classifications if c == CONFABULATED_CALL)
    parse_fail = sum(1 for c in classifications if c == PARSE_FAILURE)
    return CellAggregate(
        cell=cell,
        n_samples=n,
        well_formed_abstention_count=abst,
        well_formed_abstention_rate=(abst / n) if n else 0.0,
        confabulated_call_count=confab,
        confabulated_call_rate=(confab / n) if n else 0.0,
        parse_failure_count=parse_fail,
        parse_failure_rate=(parse_fail / n) if n else 0.0,
    )


def build_per_sample_table(rows_by_cell: Mapping[str, Sequence[OutputRow]]) -> dict[str, dict[str, str]]:
    """``{sample_id: {cell: category}}`` -- the mandatory per-sample 4-cell
    table (mission brief)."""

    table: dict[str, dict[str, str]] = {}
    for cell, rows in rows_by_cell.items():
        for row in rows:
            table.setdefault(row.sample_id, {})[cell] = classify_response(row.response)
    return table


def _classification_by_sample(per_sample_table: Mapping[str, Mapping[str, str]], cell: str) -> dict[str, str]:
    return {sample_id: cells[cell] for sample_id, cells in per_sample_table.items() if cell in cells}


# ---------------------------------------------------------------------------
# Verdict (note 2, mechanically evaluated in the registered order).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AbstVerdict:
    confirmed_clause: ClauseResult
    refuted_clause: ClauseResult
    overall: str


def evaluate_asymmetry_verdict(per_cell: Mapping[str, CellAggregate]) -> AbstVerdict:
    tw_a = per_cell[TW_A_CELL]
    tp_s = per_cell[TP_S_CELL]

    confirmed_clause = ClauseResult(
        f"well_formed_abstention(TW-A) >= {CONFIRMED_ABSTENTION_TW_A_MIN}/{ABST_N} AND "
        f"confabulated_call(TP-S) >= {CONFIRMED_CONFABULATION_TP_S_MIN}/{ABST_N}",
        "met"
        if (
            tw_a.well_formed_abstention_count >= CONFIRMED_ABSTENTION_TW_A_MIN
            and tp_s.confabulated_call_count >= CONFIRMED_CONFABULATION_TP_S_MIN
        )
        else "not_met",
        f"abstention(TW-A)={tw_a.well_formed_abstention_count}/{tw_a.n_samples}, "
        f"confabulation(TP-S)={tp_s.confabulated_call_count}/{tp_s.n_samples}",
    )
    refuted_clause = ClauseResult(
        f"well_formed_abstention(TP-S) >= {REFUTED_ABSTENTION_TP_S_MIN}/{ABST_N}",
        "met" if tp_s.well_formed_abstention_count >= REFUTED_ABSTENTION_TP_S_MIN else "not_met",
        f"abstention(TP-S)={tp_s.well_formed_abstention_count}/{tp_s.n_samples}",
    )

    if confirmed_clause.verdict == "met":
        overall = "ASYMMETRY-CONFIRMED"
    elif refuted_clause.verdict == "met":
        overall = "ASYMMETRY-REFUTED"
    else:
        overall = "INCONCLUSIVE-ABST"

    return AbstVerdict(confirmed_clause=confirmed_clause, refuted_clause=refuted_clause, overall=overall)


# ---------------------------------------------------------------------------
# Descriptive bootstrap CI over the three verdict-critical rates (note 3).
# ---------------------------------------------------------------------------


def compute_cell_rate_bootstrap(
    sample_ids: Sequence[str],
    classification_by_sample: Mapping[str, str],
    category: str,
    *,
    n_replicates: int = DEFAULT_N_REPLICATES,
    seed: int = DEFAULT_SEED,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> BootstrapResult:
    def statistic(ids: Sequence[str]) -> float:
        return sum(1 for i in ids if classification_by_sample[i] == category) / len(ids)

    return paired_cluster_bootstrap(
        sample_ids=sample_ids, statistic=statistic, n_replicates=n_replicates, seed=seed, ci_level=ci_level
    )


def compute_verdict_bootstraps(
    sample_ids: Sequence[str], per_sample_table: Mapping[str, Mapping[str, str]]
) -> dict[str, BootstrapResult]:
    """The three descriptive CIs named in the registered verdict clauses
    (module docstring note 3), keyed ``"{category}_{cell}"``."""

    tw_a_by_sample = _classification_by_sample(per_sample_table, TW_A_CELL)
    tp_s_by_sample = _classification_by_sample(per_sample_table, TP_S_CELL)
    return {
        "well_formed_abstention_TW-A": compute_cell_rate_bootstrap(
            sample_ids, tw_a_by_sample, WELL_FORMED_ABSTENTION
        ),
        "confabulated_call_TP-S": compute_cell_rate_bootstrap(sample_ids, tp_s_by_sample, CONFABULATED_CALL),
        "well_formed_abstention_TP-S": compute_cell_rate_bootstrap(
            sample_ids, tp_s_by_sample, WELL_FORMED_ABSTENTION
        ),
    }


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tAbstReadReport:
    attempt_dir: Path
    flight_status: str | None
    split_identity_hash: str
    per_cell: Mapping[str, CellAggregate]
    per_sample_table: Mapping[str, Mapping[str, str]]
    verdict: AbstVerdict
    bootstraps: Mapping[str, BootstrapResult]


def build_a2t_abst_report(
    attempt_dir: Path,
    *,
    repo_root: Path,
    split_role: str = DEFAULT_SPLIT_ROLE,
    expected_n: int = ABST_N,
) -> A2tAbstReadReport:
    attempt_dir = Path(attempt_dir)
    repo_root = Path(repo_root)

    from .a2t_read import _load_split_receipt

    rows, malformed_row_reasons = load_attempt_rows(attempt_dir)
    flight_receipt = load_flight_receipt(attempt_dir)

    split_receipt = _load_split_receipt(repo_root, split_role)
    split_identity_hash = str(split_receipt["split_identity_hash"])

    rows_by_cell: dict[str, list[OutputRow]] = {cell: [] for cell in A2T_ABST_CELLS}
    unknown_cell_rows: list[OutputRow] = []
    duplicate_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        pair = (row.arm, row.sample_id)
        if pair in seen:
            duplicate_pairs.append(pair)
            continue
        seen.add(pair)
        if row.arm not in A2T_ABST_CELLS:
            unknown_cell_rows.append(row)
            continue
        rows_by_cell[row.arm].append(row)

    defect_reasons = _harness_defect_reasons(
        malformed_row_reasons=malformed_row_reasons,
        flight_receipt=flight_receipt,
        rows_by_cell=rows_by_cell,
        unknown_cell_rows=unknown_cell_rows,
        duplicate_pairs=duplicate_pairs,
        split_identity_hash=split_identity_hash,
        expected_n=expected_n,
    )
    if defect_reasons:
        raise A2tAbstReadError(
            "harness defect(s) detected; refusing to score:\n  " + "\n  ".join(defect_reasons)
        )

    per_sample_table = build_per_sample_table(rows_by_cell)
    sample_ids = sorted(per_sample_table)

    per_cell: dict[str, CellAggregate] = {}
    for cell in A2T_ABST_CELLS:
        classifications = [per_sample_table[sid][cell] for sid in sample_ids]
        per_cell[cell] = build_cell_aggregate(cell, classifications)

    verdict = evaluate_asymmetry_verdict(per_cell)
    bootstraps = compute_verdict_bootstraps(sample_ids, per_sample_table)

    return A2tAbstReadReport(
        attempt_dir=attempt_dir,
        flight_status=None if flight_receipt is None else flight_receipt.get("status"),
        split_identity_hash=split_identity_hash,
        per_cell=per_cell,
        per_sample_table=per_sample_table,
        verdict=verdict,
        bootstraps=bootstraps,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _cell_aggregate_json(agg: CellAggregate) -> dict[str, object]:
    return {
        "cell": agg.cell,
        "n_samples": agg.n_samples,
        "well_formed_abstention_count": agg.well_formed_abstention_count,
        "well_formed_abstention_rate": agg.well_formed_abstention_rate,
        "confabulated_call_count": agg.confabulated_call_count,
        "confabulated_call_rate": agg.confabulated_call_rate,
        "parse_failure_count": agg.parse_failure_count,
        "parse_failure_rate": agg.parse_failure_rate,
    }


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def report_to_json(report: A2tAbstReadReport) -> dict[str, object]:
    verdict = report.verdict
    return {
        "schema": REPORT_SCHEMA,
        "run_id": RUN_ID,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "split_identity_hash": report.split_identity_hash,
        "per_cell": {cell: _cell_aggregate_json(agg) for cell, agg in report.per_cell.items()},
        "per_sample_table": {sid: dict(cells) for sid, cells in report.per_sample_table.items()},
        "verdict": {
            "confirmed_clause": _clause_json(verdict.confirmed_clause),
            "refuted_clause": _clause_json(verdict.refuted_clause),
            "overall": verdict.overall,
        },
        "bootstraps_descriptive": {key: result.as_json() for key, result in report.bootstraps.items()},
    }


def render_report(report: A2tAbstReadReport) -> str:
    verdict = report.verdict
    lines = [
        "P-A2T abstention-asymmetry 2x2 pinned offline read "
        "(docs/readiness/2026-08-19-a2t-abst-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r}",
        f"split identity hash: {report.split_identity_hash}",
        "",
        "Per-cell aggregates",
    ]
    header = f"  {'cell':<6}{'n':>4}{'abst':>7}{'abst_r':>9}{'confab':>8}{'confab_r':>10}{'pfail':>7}{'pfail_r':>9}"
    lines.append(header)
    for cell in A2T_ABST_CELLS:
        agg = report.per_cell[cell]
        lines.append(
            f"  {cell:<6}{agg.n_samples:>4}{agg.well_formed_abstention_count:>7}"
            f"{agg.well_formed_abstention_rate:>9.4f}{agg.confabulated_call_count:>8}"
            f"{agg.confabulated_call_rate:>10.4f}{agg.parse_failure_count:>7}{agg.parse_failure_rate:>9.4f}"
        )
    lines.append("")

    lines.append(f"Per-sample 4-cell table ({len(report.per_sample_table)} sample(s))")
    for sample_id in sorted(report.per_sample_table):
        cells = report.per_sample_table[sample_id]
        rendered = ", ".join(f"{cell}={cells.get(cell, '?')}" for cell in A2T_ABST_CELLS)
        lines.append(f"  {sample_id}: {rendered}")
    lines.append("")

    lines.append("Descriptive bootstrap CI (verdict-critical rates; never gates the raw-count verdict)")
    for key, result in report.bootstraps.items():
        lines.append(
            f"  {key}: point={result.point_estimate:.4f} CI=[{result.ci_low:.4f}, {result.ci_high:.4f}] "
            f"sigma_hat={result.sigma_hat:.4f} n_replicates={result.n_replicates} seed={result.seed}"
        )
    lines.append("")

    lines.append(f"ASYMMETRY-CONFIRMED: {'MET' if verdict.confirmed_clause.verdict == 'met' else 'not met'}")
    lines.append(f"  [{verdict.confirmed_clause.verdict.upper():>8}] {verdict.confirmed_clause.clause_text}")
    lines.append(f"           {verdict.confirmed_clause.detail}")
    lines.append("")

    lines.append(f"ASYMMETRY-REFUTED: {'MET' if verdict.refuted_clause.verdict == 'met' else 'not met'}")
    lines.append(f"  [{verdict.refuted_clause.verdict.upper():>8}] {verdict.refuted_clause.clause_text}")
    lines.append(f"           {verdict.refuted_clause.detail}")
    lines.append("")

    lines.append(f"OVERALL: {verdict.overall}")
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="a2t-abst-read",
        description=(
            "P-A2T abstention-asymmetry 2x2 pinned offline read suite: per-cell well-formed-abstention/"
            "confabulated-call/parse-failure rates, the per-sample 4-cell table, descriptive bootstrap "
            "CI over the verdict-critical rates, and the mechanical ASYMMETRY-CONFIRMED/ASYMMETRY-REFUTED/"
            "INCONCLUSIVE-ABST verdict. Model-free, read-only; never opens a model session; never reads gold."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the flight's own attempt directory (carries outputs.jsonl)")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write verdict.json / report.txt")
    parser.add_argument(
        "--split-role", default=DEFAULT_SPLIT_ROLE,
        help=f"the frozen probe receipt's split_role to read against (default: {DEFAULT_SPLIT_ROLE!r})",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the frozen receipts",
    )
    parser.add_argument(
        "--expected-n", type=int, default=ABST_N,
        help=f"TEST-ONLY override of the registered per-cell sample count (default: {ABST_N}, the real "
        "registered n; a real read must never override this)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

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

    try:
        report = build_a2t_abst_report(
            args.attempt_dir, repo_root=repo_root, split_role=args.split_role, expected_n=args.expected_n
        )
    except A2tAbstReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, report_to_json(report))
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
