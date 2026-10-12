"""Proposer-side meta summary (SkillOpt meta update; spec 1.3, owner dimension 3).

An aggregate table of operator classes per iteration: how many candidates were accepted,
refused or left unflown, and the mean predicted versus measured SLU pp. It is shown to the
proposer only and NEVER shipped to a node: the document carries ``never_shipped: true`` and
:func:`assert_shippable` (which every node-prompt renderer must call on a payload) refuses
it. The table holds numbers and identifiers only; :func:`assert_meta_clean` asserts that no
text-bearing field exists in it.

Measured pp = the state's SLU point delta versus its parent column when present, else
versus lock (the same-flight column the verdict was read on).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from speech_aware_evidence_acquisition.analysis.sealed_credit.archive import (
    assert_no_text_fields, forbidden_key,
)

SCHEMA = "saea-tfrl-proposer-meta-v1"
ROW_KEYS = frozenset({
    "iteration", "operator_class", "n_accepted", "n_refused", "n_unflown",
    "mean_predicted_slu_pp", "mean_measured_slu_pp", "mean_realised_minus_predicted_pp",
})
#: Present only when at least one reread record exists: how many later proposals re-measured a state of this (iteration, class) group.
OPTIONAL_ROW_KEYS = frozenset({"n_rereads"})


class MetaSummaryError(RuntimeError):
    pass


def _measured(state: Mapping[str, Any]) -> float | None:
    credit = state.get("credit")
    if credit is None:
        return None
    block = credit.get("vs_parent") or credit["vs_lock"]
    return float(block["slu"]["point"])


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_meta_summary(states: Iterable[Mapping[str, Any]], arm: str = "typed",
                       rereads: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    states = list(states)
    reread_counts: dict[tuple[int, str], int] = {}
    by_id = {s["state_id"]: s for s in states}
    for r in (rereads or ()):
        held = by_id.get(r["state_id"])
        if held is not None and held["arm"] == arm and held.get("operator_class"):
            key = (held["iteration"], held["operator_class"])
            reread_counts[key] = reread_counts.get(key, 0) + 1
    groups: dict[tuple[int, str], list[Mapping[str, Any]]] = {}
    for s in states:
        if s["arm"] != arm or s["iteration"] < 1:
            continue
        groups.setdefault((s["iteration"], s["operator_class"]), []).append(s)
    rows = []
    for (iteration, operator_class), members in sorted(groups.items()):
        predicted = [float(m["predicted_slu_pp"]) for m in members if m.get("predicted_slu_pp") is not None and m["verdict"] != "unflown"]
        measured = [_measured(m) for m in members if _measured(m) is not None]
        paired = [(float(m["predicted_slu_pp"]), _measured(m)) for m in members
                  if m.get("predicted_slu_pp") is not None and _measured(m) is not None]
        rows.append({
            "iteration": iteration,
            "operator_class": operator_class,
            "n_accepted": sum(m["verdict"] == "accepted" for m in members),
            "n_refused": sum(m["verdict"] == "refused" for m in members),
            "n_unflown": sum(m["verdict"] == "unflown" for m in members),
            "mean_predicted_slu_pp": _mean(predicted),
            "mean_measured_slu_pp": _mean(measured),
            "mean_realised_minus_predicted_pp": _mean([m - p for p, m in paired]),
            **({"n_rereads": reread_counts.get((iteration, operator_class), 0)} if reread_counts else {}),
        })
    document = {"schema": SCHEMA, "never_shipped": True, "arm": arm, "rows": rows}
    assert_meta_clean(document)
    return document


def assert_meta_clean(document: Mapping[str, Any]) -> None:
    """Hard assertion: flagged never-shipped, aggregate rows only, no text-bearing field."""

    if document.get("never_shipped") is not True:
        raise MetaSummaryError("the meta summary must carry never_shipped: true")
    if document.get("schema") != SCHEMA:
        raise MetaSummaryError("not a proposer meta summary")
    if set(document) != {"schema", "never_shipped", "arm", "rows"}:
        raise MetaSummaryError("unexpected top-level field in the meta summary")
    for row in document["rows"]:
        if not ROW_KEYS <= set(row) <= ROW_KEYS | OPTIONAL_ROW_KEYS:
            raise MetaSummaryError(f"meta row must carry exactly {sorted(ROW_KEYS)} (plus optionally {sorted(OPTIONAL_ROW_KEYS)})")
        for key in row:
            if forbidden_key(key):
                raise MetaSummaryError(f"text-bearing field {key!r} in the meta summary")
    try:
        assert_no_text_fields(document)
    except Exception as error:  # ArchiveError -> uniform error type for callers
        raise MetaSummaryError(str(error)) from error


def assert_shippable(payload: Mapping[str, Any]) -> None:
    """Every node-prompt renderer calls this on anything it is about to place in a prompt."""

    if isinstance(payload, Mapping) and (payload.get("never_shipped") is True or payload.get("schema") == SCHEMA):
        raise MetaSummaryError("a never_shipped document may not enter a node prompt")


def render_for_proposer(document: Mapping[str, Any]) -> str:
    """Aggregate table, proposer-only rendering (identifiers and numbers)."""

    assert_meta_clean(document)

    def cell(v: Any) -> str:
        return "-" if v is None else (f"{v:+.2f}" if isinstance(v, float) else str(v))

    header = ["iteration", "operator_class", "n_accepted", "n_refused", "n_unflown",
              "mean_predicted_slu_pp", "mean_measured_slu_pp", "mean_realised_minus_predicted_pp"]
    lines = ["\t".join(header)]
    for row in document["rows"]:
        lines.append("\t".join(cell(row[k]) for k in header))
    return "\n".join(lines) + "\n"


__all__ = [
    "MetaSummaryError", "build_meta_summary", "assert_meta_clean", "assert_shippable",
    "render_for_proposer", "SCHEMA",
]
