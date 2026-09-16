"""Compare analytical byte accounting against actual source-bound rendering."""

import copy
import itertools

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_slot_binding_footprint import audit_footprint
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import _slot
from speech_aware_evidence_acquisition.rails.knowledge_provider import select_candidate_semantic_values


def fixtures():
    rows = []
    for slot, intents in [("date", ("a", "b", "c")), ("place", ("b", "c")), ("person", ("a",))]:
        rows.append({
            "slot_id": slot,
            "intent_bindings": [{"intent_id": intent, "semantic_role": f"Role {intent} for {slot}."}
                                for intent in intents],
            "extraction_cues": ["Retain this global extraction cue."],
            "admissible_formats": ["Preserve the spoken surface form."],
            "missing_behavior": "Do not invent a missing entity.",
            "ambiguity_behavior": "Retain ambiguity.",
            "limitations": ["Bindings are observed, not exhaustive."],
            "source_support": {"source_sample_ids": ["construction-only"], "provenance_refs": ["source"]},
        })
    contents = {f"slot-contract:{row['slot_id']}": _slot(row)[2] for row in rows}
    index = {intent: tuple(sorted(k for k, row in zip(contents, rows, strict=True)
                                  if any(b["intent_id"] == intent for b in row["intent_bindings"])))
             for intent in ("a", "b", "c")}
    return rows, contents, index


def test_complete_ordered_enumeration_agrees_with_actual_rendered_body():
    rows, contents, index = fixtures()
    originals = copy.deepcopy((rows, contents, index))
    report = audit_footprint(source_rows=rows, value_contents=contents, candidate_values=index,
                             candidate_ids=("a", "b", "c"), widths=(1, 2, 3),
                             max_values_per_candidate=1, max_total_values=2)
    by_id = {f"slot-contract:{row['slot_id']}": row for row in rows}
    for measured in report["all_ordered_candidate_sets"]:
        width = measured["distinct_candidate_width"]
        full, projected, count = 0, 0, 0
        for candidates in itertools.permutations(("a", "b", "c"), width):
            selected, _ = select_candidate_semantic_values(
                candidates, index, max_values_per_candidate=1, max_total_values=2)
            for key in selected:
                full += len(contents[key].encode())
                row = copy.deepcopy(by_id[key])
                row["intent_bindings"] = [b for b in row["intent_bindings"] if b["intent_id"] in candidates]
                projected += len(_slot(row)[2].encode())
            count += 1
        assert measured["ordered_sets"] == count
        assert measured["full_body_bytes_sum"] == full
        assert measured["projected_body_bytes_sum"] == projected
    assert (rows, contents, index) == originals


def test_changed_source_or_candidate_mapping_is_refused():
    rows, contents, index = fixtures()
    contents["slot-contract:date"] += " forged"
    with pytest.raises(ValueError, match="source"):
        audit_footprint(source_rows=rows, value_contents=contents, candidate_values=index,
                        candidate_ids=("a", "b", "c"))
    rows, contents, index = fixtures()
    index["a"] = ("slot-contract:place",)
    with pytest.raises(ValueError, match="mapping"):
        audit_footprint(source_rows=rows, value_contents=contents, candidate_values=index,
                        candidate_ids=("a", "b", "c"))


@pytest.mark.parametrize("options", [
    {"widths": (0,)}, {"widths": (4,)}, {"max_values_per_candidate": 0},
    {"max_total_values": True}, {"candidate_ids": ("a", "a")},
])
def test_invalid_enumeration_refuses(options):
    rows, contents, index = fixtures()
    kwargs = dict(source_rows=rows, value_contents=contents, candidate_values=index,
                  candidate_ids=("a", "b", "c"))
    kwargs.update(options)
    with pytest.raises(ValueError):
        audit_footprint(**kwargs)
