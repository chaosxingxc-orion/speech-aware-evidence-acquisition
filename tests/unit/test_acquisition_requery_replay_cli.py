"""Item E36b: unit tests for the model-free replay CLI
``scripts/analysis/acquisition_requery_replay.py``, on synthetic data only. Loaded by file path
(this script lives under ``scripts/``, not the installed package), exactly as every other
``scripts/analysis`` driver this test tree covers (see e.g. ``test_a2t_g6_result_analysis.py``).
"""

from __future__ import annotations

import collections
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "analysis" / "acquisition_requery_replay.py"


def _module():
    spec = importlib.util.spec_from_file_location("acquisition_requery_replay", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Value:
    def __init__(self, value_id: str, content: str, facet_ids=()):
        self.value_id = value_id
        self.content = content
        self.associated_facet_ids = tuple(facet_ids)


def test_tokenize_is_lowercase_alnum_split_on_non_alnum():
    module = _module()
    assert module._tokenize("Place_Name, Time!") == frozenset({"place", "name", "time"})


def test_build_vocabulary_counts_document_frequency_per_token():
    module = _module()
    values_by_id = {
        "kb:v1": _Value("kb:v1", "alarm_set alarm"),
        "kb:v2": _Value("kb:v2", "calendar_set"),
    }
    value_tokens, document_frequency = module.build_vocabulary(values_by_id)
    assert value_tokens["kb:v1"] == frozenset({"alarm", "set"})
    assert value_tokens["kb:v2"] == frozenset({"calendar", "set"})
    assert document_frequency["set"] == 2
    assert document_frequency["alarm"] == 1
    assert document_frequency["calendar"] == 1


def test_diagnose_row_reports_kept_and_dropped_reasons():
    module = _module()
    values_by_id = {
        "kb:held": _Value("kb:held", "seenword"),
        "kb:v1": _Value("kb:v1", "raretoken commontoken seenword"),
        "kb:v2": _Value("kb:v2", "commontoken"),
        "kb:v3": _Value("kb:v3", "commontoken"),
    }
    value_tokens, document_frequency = module.build_vocabulary(values_by_id)
    total = len(values_by_id)
    excluded = frozenset({"kb:held"})

    diagnosis = module._diagnose_row(
        filters=("ab", "raretoken", "commontoken", "seenword", "ghosttoken"),
        exclude_value_ids=excluded, value_tokens=value_tokens,
        document_frequency=document_frequency, total_values=total,
        min_token_chars=4, max_document_frequency=0.5,
        exclude_visible_tokens=True, k=5,
    )
    # "ab" (2 chars) -> too-short; "commontoken" (df 3 of 4, share 0.75 > 0.5) -> too-common;
    # "seenword" occurs in the excluded (held) value -> visible-in-row; "ghosttoken" occurs in no
    # value -> absent-from-snapshot; only "raretoken" survives.
    assert diagnosis["tokens_dropped_by_reason"] == {
        "too-short": 1, "too-common": 1, "visible-in-row": 1, "absent-from-snapshot": 1,
    }
    assert diagnosis["tokens_kept"] == 1
    assert diagnosis["candidates"] == 1
    assert [value_id for value_id, _score in diagnosis["top"]] == ["kb:v1"]


def test_diagnose_row_returns_empty_when_no_token_survives():
    module = _module()
    values_by_id = {"kb:v1": _Value("kb:v1", "alarm")}
    value_tokens, document_frequency = module.build_vocabulary(values_by_id)
    diagnosis = module._diagnose_row(
        filters=("ab",), exclude_value_ids=frozenset(), value_tokens=value_tokens,
        document_frequency=document_frequency, total_values=1,
        min_token_chars=4, max_document_frequency=1.0,
        exclude_visible_tokens=True, k=5,
    )
    assert diagnosis["tokens_kept"] == 0
    assert diagnosis["candidates"] == 0
    assert diagnosis["top"] == []


def test_iter_acquire_rows_skips_rows_with_no_acquisitions(tmp_path):
    module = _module()
    outputs = tmp_path / "run.outputs.jsonl"
    import json as _json
    with outputs.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(_json.dumps({
            "sample_id": "s1", "native_episode_receipt": {"acquisition": {"acquisitions": []}},
        }) + "\n")
        handle.write(_json.dumps({
            "sample_id": "s2",
            "native_episode_receipt": {
                "acquisition": {"acquisitions": [{"state_filters": ["alarm"]}]},
            },
        }) + "\n")
        handle.write(_json.dumps({"sample_id": "s3"}) + "\n")
    rows = list(module.iter_acquire_rows(outputs))
    assert [sample_id for sample_id, _acqs in rows] == ["s2"]
    assert rows[0][1] == [{"state_filters": ["alarm"]}]


def test_visible_ids_for_unions_every_phase_for_the_sample():
    module = _module()
    supply_values = {
        "perception": {"s1": ["kb:v1", "kb:v2"]},
        "solver": {"s1": ["kb:v2", "kb:v3"], "s2": ["kb:v9"]},
    }
    assert module.visible_ids_for("s1", supply_values) == frozenset({"kb:v1", "kb:v2", "kb:v3"})
    assert module.visible_ids_for("s9", supply_values) == frozenset()


def test_armed_native_episode_values_adds_exactly_the_two_keys():
    module = _module()
    composed_values = {
        "policy": "phase-native-candidates-review-revise-acquire-v1",
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "acquisition": {
                "policy": "saea-acquire-knowledge-requery-v1",
                "budget": {"max_acquisitions_per_row": 1, "contact_budget": 0},
            },
        },
    }
    args = module.Args(
        repo_root=REPO_ROOT, data_root=REPO_ROOT, run_id="r", attempt_id="a",
        experiment="e", cell_id="e", k=5, min_token_chars=4,
        max_document_frequency=0.05, exclude_visible_tokens=True, receipt_out=None,
    )
    armed = module._armed_native_episode_values(composed_values, args)
    acquisition = armed["native_episode"]["acquisition"]
    assert acquisition["budget"] == {
        "max_acquisitions_per_row": 1, "contact_budget": 0, "max_items_per_acquisition": 5,
    }
    assert acquisition["retrieval"] == {
        "policy": module.DEFAULT_RETRIEVAL_POLICY_ID,
        "min_token_chars": 4, "max_document_frequency": 0.05, "exclude_visible_tokens": True,
    }
    # The input mapping is untouched (a defensive deep copy, not a mutation).
    assert "budget" in composed_values["native_episode"]["acquisition"]
    assert "max_items_per_acquisition" not in composed_values["native_episode"]["acquisition"]["budget"]


def test_armed_native_episode_values_refuses_a_cell_with_no_acquisition():
    module = _module()
    args = module.Args(
        repo_root=REPO_ROOT, data_root=REPO_ROOT, run_id="r", attempt_id="a",
        experiment="e", cell_id="e", k=5, min_token_chars=4,
        max_document_frequency=0.05, exclude_visible_tokens=True, receipt_out=None,
    )
    try:
        module._armed_native_episode_values({"native_episode": {}}, args)
    except module.ReplayError:
        pass
    else:  # pragma: no cover - the assertion below fails loudly if this path is taken
        raise AssertionError("expected ReplayError")


def test_store_mix_aggregation_over_synthetic_rows():
    """A whole-pipeline slice on synthetic in-memory data: two rows, a tiny snapshot of two
    stores, the diagnostic scorer producing a store mix that matches a hand count."""

    module = _module()
    values_by_id = {
        "store-a::v1": _Value("store-a::v1", "alarm_set alarm", ("store-a::facet1",)),
        "store-b::v1": _Value("store-b::v1", "calendar_set calendar", ("store-b::facet1",)),
    }
    value_tokens, document_frequency = module.build_vocabulary(values_by_id)
    total = len(values_by_id)

    class _Binding:
        store_ids = ("store-a", "store-b")

    diagnosis_a = module._diagnose_row(
        filters=("alarm",), exclude_value_ids=frozenset(), value_tokens=value_tokens,
        document_frequency=document_frequency, total_values=total,
        min_token_chars=1, max_document_frequency=1.0, exclude_visible_tokens=True, k=5,
    )
    diagnosis_b = module._diagnose_row(
        filters=("calendar",), exclude_value_ids=frozenset(), value_tokens=value_tokens,
        document_frequency=document_frequency, total_values=total,
        min_token_chars=1, max_document_frequency=1.0, exclude_visible_tokens=True, k=5,
    )
    stores = collections.Counter()
    for diagnosis in (diagnosis_a, diagnosis_b):
        for value_id, _score in diagnosis["top"]:
            stores[module.store_of(_Binding(), value_id)] += 1
    assert dict(stores) == {"store-a": 1, "store-b": 1}
