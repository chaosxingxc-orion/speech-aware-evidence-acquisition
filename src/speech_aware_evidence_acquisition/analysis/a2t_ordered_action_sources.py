"""Project source-bound Audio2Tool rows into ordered action sequences.

The helper performs no file reads and calls no scorer.  Its callers supply an
already selected roster, its tier manifests, saved model outputs, and the two
saved score views.  Only manifest entries named by the roster are passed to
the shared gold expander.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from ..reproduction.toolcall_gold import GoldParseError, expected_tool_calls_for_entry
from ..reproduction.toolcall_scoring import parse_tool_calls_text


class OrderedActionSourceError(ValueError):
    """An ordered-action source row is malformed or contradicts another source."""


def _row_sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise OrderedActionSourceError(f"{label} must be a sequence of rows")
    return value


def _sample_id(row: object, label: str, index: int) -> tuple[str, Mapping[str, object]]:
    if not isinstance(row, Mapping):
        raise OrderedActionSourceError(f"{label}[{index}] must be a row mapping")
    sample_id = row.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id:
        raise OrderedActionSourceError(f"{label}[{index}] lacks a nonempty sample_id")
    return sample_id, row


def _index_rows(value: object, label: str) -> dict[str, Mapping[str, object]]:
    rows = _row_sequence(value, label)
    indexed: dict[str, Mapping[str, object]] = {}
    for index, raw_row in enumerate(rows):
        sample_id, row = _sample_id(raw_row, label, index)
        if sample_id in indexed:
            raise OrderedActionSourceError(
                f"{label} carries duplicate sample_id {sample_id!r}"
            )
        indexed[sample_id] = row
    return indexed


def _roster_index(value: object) -> dict[str, Mapping[str, object]]:
    roster = _index_rows(value, "roster_rows")
    if not roster:
        raise OrderedActionSourceError("roster_rows must not be empty")
    for sample_id, row in roster.items():
        tier = row.get("tier")
        item_id = row.get("id")
        query_idx = row.get("query_idx")
        if not isinstance(tier, str) or not tier:
            raise OrderedActionSourceError(f"roster row {sample_id!r} has an invalid tier")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            raise OrderedActionSourceError(f"roster row {sample_id!r} has an invalid id")
        if (
            isinstance(query_idx, bool)
            or not isinstance(query_idx, int)
            or query_idx < 0
        ):
            raise OrderedActionSourceError(
                f"roster row {sample_id!r} has an invalid query_idx"
            )
        if sample_id != f"{tier}:{item_id:06d}":
            raise OrderedActionSourceError(
                f"roster row {sample_id!r} disagrees with its tier/id association"
            )
    return roster


def _require_exact_ids(
    rows: Mapping[str, object], expected_ids: set[str], label: str
) -> None:
    actual_ids = set(rows)
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise OrderedActionSourceError(
            f"{label} sample IDs differ from roster_rows: missing={missing!r}, extra={extra!r}"
        )


def _selected_manifest_entry(
    entries_by_tier: object,
    *,
    sample_id: str,
    tier: str,
    item_id: int,
    query_idx: int,
) -> Mapping[str, object]:
    if not isinstance(entries_by_tier, Mapping):
        raise OrderedActionSourceError("entries_by_tier must be a tier mapping")
    tier_entries = entries_by_tier.get(tier)
    matches: list[Mapping[str, object]] = []
    if isinstance(tier_entries, Mapping):
        candidate = tier_entries.get(item_id)
        if isinstance(candidate, Mapping):
            matches.append(candidate)
    elif not isinstance(tier_entries, (str, bytes)) and isinstance(
        tier_entries, Sequence
    ):
        matches.extend(
            entry
            for entry in tier_entries
            if isinstance(entry, Mapping) and entry.get("id") == item_id
        )
    else:
        raise OrderedActionSourceError(
            f"entries_by_tier lacks an entry sequence for tier {tier!r}"
        )
    if len(matches) != 1:
        raise OrderedActionSourceError(
            f"manifest selection for roster sample {sample_id!r} found {len(matches)} entries"
        )
    entry = matches[0]
    if entry.get("id") != item_id:
        raise OrderedActionSourceError(
            f"manifest entry for {sample_id!r} disagrees with the roster id"
        )
    if entry.get("query_idx") != query_idx:
        raise OrderedActionSourceError(
            f"manifest entry for {sample_id!r} disagrees with the roster query_idx"
        )
    primary = entry.get("tool_name")
    if (
        not isinstance(primary, str)
        or not primary
        or primary != primary.strip()
    ):
        raise OrderedActionSourceError(
            f"manifest entry for {sample_id!r} has a noncanonical tool_name"
        )
    return entry


def _tier(row: Mapping[str, object], sample_id: str, label: str, expected: str) -> None:
    if row.get("tier") != expected:
        raise OrderedActionSourceError(
            f"{label} row {sample_id!r} tier contradicts roster_rows"
        )


def _official_count(row: Mapping[str, object], sample_id: str, label: str) -> int:
    value = row.get("num_expected_tools")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise OrderedActionSourceError(
            f"{label} row {sample_id!r} has an invalid official expected count"
        )
    return value


def _binary_metric(row: Mapping[str, object], field: str, sample_id: str, label: str) -> float:
    value = row.get(field)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value not in (0, 1)
    ):
        raise OrderedActionSourceError(
            f"{label} row {sample_id!r} field {field!r} must be a binary number"
        )
    return float(value)


def _crosscheck_v2(
    row: Mapping[str, object],
    *,
    sample_id: str,
    label: str,
    parsed: bool,
    expected_names: list[str],
    predicted_names: list[str],
) -> None:
    saved_parsed = row.get("parsed")
    if not isinstance(saved_parsed, bool) or saved_parsed is not parsed:
        raise OrderedActionSourceError(
            f"{label} row {sample_id!r} parsed flag contradicts the shared parser"
        )
    ordered = float(expected_names == predicted_names)
    if _binary_metric(row, "tool_accuracy", sample_id, label) != ordered:
        raise OrderedActionSourceError(
            f"{label} row {sample_id!r} ordered sequence result contradicts the projection"
        )
    multiset = float(Counter(expected_names) == Counter(predicted_names))
    if _binary_metric(row, "tool_accuracy_multiset", sample_id, label) != multiset:
        raise OrderedActionSourceError(
            f"{label} row {sample_id!r} name multiset result contradicts the projection"
        )


def project_ordered_action_sources(
    roster_rows: Sequence[Mapping[str, object]],
    entries_by_tier: Mapping[str, object],
    direct_output_rows: Sequence[Mapping[str, object]],
    system_output_rows: Sequence[Mapping[str, object]],
    direct_official_rows: Sequence[Mapping[str, object]],
    system_official_rows: Sequence[Mapping[str, object]],
    direct_v2_rows: Sequence[Mapping[str, object]],
    system_v2_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Return validated per-sample ordered action source rows.

    ``official_expected_count`` preserves the official scorer's saved count.
    ``expanded_expected_count`` is the number of calls produced by the shared
    manifest gold expander; the two counts intentionally need not be equal.
    """

    roster = _roster_index(roster_rows)
    expected_ids = set(roster)
    sources = {
        "direct_output_rows": _index_rows(direct_output_rows, "direct_output_rows"),
        "system_output_rows": _index_rows(system_output_rows, "system_output_rows"),
        "direct_official_rows": _index_rows(
            direct_official_rows, "direct_official_rows"
        ),
        "system_official_rows": _index_rows(
            system_official_rows, "system_official_rows"
        ),
        "direct_v2_rows": _index_rows(direct_v2_rows, "direct_v2_rows"),
        "system_v2_rows": _index_rows(system_v2_rows, "system_v2_rows"),
    }
    for label, indexed in sources.items():
        _require_exact_ids(indexed, expected_ids, label)

    projected: list[dict[str, object]] = []
    for sample_id in sorted(expected_ids):
        roster_row = roster[sample_id]
        tier = roster_row["tier"]
        item_id = roster_row["id"]
        query_idx = roster_row["query_idx"]
        assert isinstance(tier, str)
        assert isinstance(item_id, int) and not isinstance(item_id, bool)
        assert isinstance(query_idx, int) and not isinstance(query_idx, bool)
        entry = _selected_manifest_entry(
            entries_by_tier,
            sample_id=sample_id,
            tier=tier,
            item_id=item_id,
            query_idx=query_idx,
        )
        try:
            expected_calls = expected_tool_calls_for_entry(entry)
        except GoldParseError as error:
            raise OrderedActionSourceError(
                f"manifest gold for {sample_id!r} cannot be expanded: {error}"
            ) from error
        expected_names = [call.name for call in expected_calls]
        if not expected_names or any(not isinstance(name, str) or not name for name in expected_names):
            raise OrderedActionSourceError(
                f"manifest gold for {sample_id!r} has an invalid tool name"
            )

        direct_output = sources["direct_output_rows"][sample_id]
        system_output = sources["system_output_rows"][sample_id]
        direct_text = direct_output.get("text")
        system_text = system_output.get("text")
        if not isinstance(direct_text, str):
            raise OrderedActionSourceError(
                f"direct_output_rows row {sample_id!r} lacks a text field"
            )
        if not isinstance(system_text, str):
            raise OrderedActionSourceError(
                f"system_output_rows row {sample_id!r} lacks a text field"
            )
        direct_calls, direct_parsed = parse_tool_calls_text(direct_text)
        system_calls, system_parsed = parse_tool_calls_text(system_text)
        direct_names = [call.name for call in direct_calls]
        system_names = [call.name for call in system_calls]

        direct_official = sources["direct_official_rows"][sample_id]
        system_official = sources["system_official_rows"][sample_id]
        direct_v2 = sources["direct_v2_rows"][sample_id]
        system_v2 = sources["system_v2_rows"][sample_id]
        for label, score_row in (
            ("direct_official_rows", direct_official),
            ("system_official_rows", system_official),
            ("direct_v2_rows", direct_v2),
            ("system_v2_rows", system_v2),
        ):
            _tier(score_row, sample_id, label, tier)

        primary_name = expected_names[0]
        for label, official in (
            ("direct_official_rows", direct_official),
            ("system_official_rows", system_official),
        ):
            if official.get("gold_tool") != primary_name:
                raise OrderedActionSourceError(
                    f"{label} row {sample_id!r} gold_tool contradicts expanded gold"
                )
        direct_count = _official_count(
            direct_official, sample_id, "direct_official_rows"
        )
        system_count = _official_count(
            system_official, sample_id, "system_official_rows"
        )
        if direct_count != system_count:
            raise OrderedActionSourceError(
                f"official expected count differs between arms for {sample_id!r}"
            )

        _crosscheck_v2(
            direct_v2,
            sample_id=sample_id,
            label="direct_v2_rows",
            parsed=direct_parsed,
            expected_names=expected_names,
            predicted_names=direct_names,
        )
        _crosscheck_v2(
            system_v2,
            sample_id=sample_id,
            label="system_v2_rows",
            parsed=system_parsed,
            expected_names=expected_names,
            predicted_names=system_names,
        )
        projected.append(
            {
                "sample_id": sample_id,
                "tier": tier,
                "expected_tool_names": expected_names,
                "direct_predicted_tool_names": direct_names,
                "system_predicted_tool_names": system_names,
                "direct_parsed": direct_parsed,
                "system_parsed": system_parsed,
                "official_expected_count": direct_count,
                "expanded_expected_count": len(expected_names),
            }
        )
    return projected
