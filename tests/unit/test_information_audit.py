from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import information_audit as ia
from speech_aware_evidence_acquisition.analysis.information_audit_specs import (
    MENTION_FIELD_SEPARATOR,
    CarrierInformationSpec,
    CarrierInformationSpecError,
    EvaluationRoster,
    audio2tool_spec,
    earnings21_conec_spec,
    slurp_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE_SUMMARY = (
    REPO_ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-construction-task-information-audit"
    / "summary.json"
)


def _row(item_id: str, **fields: object) -> dict[str, object]:
    return {"item_id": item_id, **fields}


# ---------------------------------------------------------------------------
# Q1
# ---------------------------------------------------------------------------


def test_field_catalog_sorts_and_validates():
    catalog = ia.field_catalog(
        {"b_field": "runtime-legal-input", "a_field": "forbidden"},
        {"structure_x": "gold-scoring-only"},
    )
    assert list(catalog["fields"]) == ["a_field", "b_field"]
    assert catalog["corpus_structures"] == {"structure_x": "gold-scoring-only"}
    assert set(catalog["legality_classes"]) == {
        "runtime-legal-input",
        "construction-only-knowledge",
        "gold-scoring-only",
        "forbidden",
    }


def test_field_catalog_rejects_unknown_legality():
    with pytest.raises(ia.InformationAuditError):
        ia.field_catalog({"x": "not-a-legality-class"}, {})


# ---------------------------------------------------------------------------
# Q2
# ---------------------------------------------------------------------------


def test_task_information_decomposition_requires_all_four_keys():
    result = ia.task_information_decomposition(
        "slot-slu", {"obs": "a", "org": "b", "supply": "c", "use": "d"}
    )
    assert result == {"task_kind": "slot-slu", "obs": "a", "org": "b", "supply": "c", "use": "d"}
    with pytest.raises(ia.InformationAuditError):
        ia.task_information_decomposition("slot-slu", {"obs": "a", "org": "b", "supply": "c"})


# ---------------------------------------------------------------------------
# Q3
# ---------------------------------------------------------------------------


def test_stratum_histogram_and_population_distribution():
    rows = [_row("1", scenario="alarm"), _row("2", scenario="alarm"), _row("3", scenario="music")]
    counts = ia.stratum_histogram(rows, stratum_of=lambda row: str(row["scenario"]))
    assert counts == {"alarm": 2, "music": 1}
    natural = ia.population_distribution(counts)
    assert natural["total"] == 3
    assert natural["shares"]["alarm"] == pytest.approx(2 / 3)
    assert natural["shares"]["music"] == pytest.approx(1 / 3)


def test_roster_deviation_classifies_equal_stratum_roster():
    natural_shares = {"alarm": 0.90, "music": 0.10}
    # a roster drawn EQUALLY across the two strata is far from natural, close to uniform
    equal_roster = {"alarm": 50, "music": 50}
    result = ia.roster_deviation(natural_shares, equal_roster)
    assert result["classification"] == "near-equal-stratum"
    assert result["total_variation_distance_from_uniform_allocation"] == pytest.approx(0.0)
    assert result["total_variation_distance_from_natural"] == pytest.approx(0.40)


def test_roster_deviation_classifies_natural_mixture_roster():
    natural_shares = {"alarm": 0.90, "music": 0.10}
    natural_roster = {"alarm": 90, "music": 10}
    result = ia.roster_deviation(natural_shares, natural_roster)
    assert result["classification"] == "near-natural-mixture"
    assert result["total_variation_distance_from_natural"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Q4
# ---------------------------------------------------------------------------


def test_label_space_entropy_from_counts_hand_computed():
    # counts = {"a": 3, "b": 1}; p = [0.75, 0.25]
    # entropy = -(0.75*log2(0.75) + 0.25*log2(0.25)) = 0.8112781244591328 bits (hand-computed)
    result = ia.label_space_entropy_from_counts({"a": 3, "b": 1})
    assert result["entropy_bits"] == pytest.approx(0.8112781244591328, abs=1e-9)
    assert result["effective_label_count"] == pytest.approx(2**0.8112781244591328, abs=1e-9)
    assert result["minimum_k_for_mass"] == {
        "0.50": 1,
        "0.80": 2,
        "0.90": 2,
        "0.95": 2,
        "0.99": 2,
        "1.00": 2,
    }
    assert result["top_k_mass"]["1"] == pytest.approx(0.75)


def test_label_space_entropy_uniform_distribution_maximizes_entropy():
    uniform = ia.label_space_entropy_from_counts({"a": 10, "b": 10, "c": 10, "d": 10})
    assert uniform["entropy_bits"] == pytest.approx(2.0, abs=1e-9)
    skewed = ia.label_space_entropy_from_counts({"a": 37, "b": 1, "c": 1, "d": 1})
    assert skewed["entropy_bits"] < uniform["entropy_bits"]


def test_label_field_entropy_over_rows_with_repetition():
    rows = [
        _row("1", labels={"intent": ("play_music",), "entity_type": ("artist_name",)}),
        _row("2", labels={"intent": ("play_music",), "entity_type": ()}),
        _row("3", labels={"intent": ("alarm_set",), "entity_type": ("time",)}),
    ]

    def labels_of(row):
        return row["labels"]

    result = ia.label_field_entropy(rows, labels_of=labels_of, label_fields=("intent", "entity_type"))
    assert result["intent"]["total_occurrences"] == 3
    assert result["entity_type"]["total_occurrences"] == 2


def test_a2t_prototype_headline_numbers_are_the_cited_values():
    """The recovery plan's goal 4 asks for a test that reproduces two
    numbers from the A2T prototype's own summary.json using the generic
    Q4 function, WHEN the prototype's construction rows are reconstructible
    without model contact.

    They are not: `run_audit.py`'s own compact-summary projection
    (`_project_metrics`) keeps only `entropy_bits`, `effective_label_count`,
    `normalized_entropy`, `top_k_mass`, and `minimum_k_for_mass` from the
    full `raw_tool_prior` report -- the per-tool `ranked_tools` occurrence
    list (which alone would let this test rebuild the exact 15,804-call
    multiset and feed it through `label_space_entropy_from_counts`) is
    dropped before the file is written. Reconstructing it would mean
    re-running the A2T construction-loading pipeline, which the recovery
    plan's own goal 4 says NOT to do here. So this test does the honest
    thing: it reads the two headline numbers straight from the already-
    committed, zero-model-contact prototype artifact as a citation-accuracy
    regression guard, and `test_label_space_entropy_from_counts_synthetic_
    matches_prototype_shape` below independently exercises the SAME generic
    function on a synthetic table built to the recovery plan's own escape
    hatch ("otherwise assert on a synthetic table and say so").
    """

    if not PROTOTYPE_SUMMARY.is_file():
        pytest.skip(f"prototype summary not present at {PROTOTYPE_SUMMARY}")
    document = json.loads(PROTOTYPE_SUMMARY.read_text(encoding="utf-8"))
    prior = document["construction"]["raw_tool_prior"]
    assert round(prior["entropy_bits"], 3) == 6.360
    assert prior["minimum_k_for_mass"]["0.90"] == 64


def test_label_space_entropy_from_counts_synthetic_matches_prototype_shape():
    """A synthetic 151-label table (module docstring above explains why a
    real reconstruction is unavailable), calibrated only to roughly the
    prototype's own shape (one dominant head, a long tail), exercised
    through the SAME generic Q4 function the real carriers use."""

    counts = {f"tool_{rank:03d}": max(1, int(2000 / (rank**1.15))) for rank in range(1, 152)}
    result = ia.label_space_entropy_from_counts(counts)
    assert result["label_count"] == 151
    assert result["entropy_bits"] > 0.0
    assert 1 <= result["minimum_k_for_mass"]["0.90"] <= 151
    # coverage is monotone non-decreasing in k
    ranks = sorted(int(k) for k in result["top_k_mass"])
    masses = [result["top_k_mass"][str(k)] for k in ranks]
    assert masses == sorted(masses)


# ---------------------------------------------------------------------------
# Q5, mode A: grouped BM25
# ---------------------------------------------------------------------------


def _bm25_rows() -> list[dict[str, object]]:
    # Two labels, "alpha" and "beta"; deliberately give "alpha" rows text
    # that shares tokens, and "beta" rows different tokens, so retrieval is
    # not degenerate. Twin group_of values must land in the same fold.
    rows = []
    for index in range(12):
        label = "alpha" if index % 2 == 0 else "beta"
        text = f"please {label} action number {index // 2} now" if label == "alpha" else f"turn {label} device {index // 2} off"
        rows.append(_row(f"u{index:02d}", text=text, group=f"block{index // 2}", label=label))
    return rows


def _bm25_callables():
    return dict(
        key_text_of=lambda row: str(row["text"]),
        group_of=lambda row: str(row["group"]),
        labels_of=lambda row: {"label": (str(row["label"]),)},
        stratum_of=lambda row: str(row["label"]),
    )


def test_label_blind_components_group_twins_by_group_of():
    rows = _bm25_rows()
    components = ia.label_blind_components(rows, key_text_of=_bm25_callables()["key_text_of"], group_of=_bm25_callables()["group_of"])
    # every pair sharing group_of must land in the same component (a
    # component may merge multiple group_of blocks via text/token twins,
    # but two rows in the SAME group_of must never split across components)
    by_id = {row["item_id"]: row["group"] for row in rows}
    group_to_component = {}
    for component in components:
        for item_id in component:
            group = by_id[item_id]
            group_to_component.setdefault(group, set()).add(component)
    assert all(len(comps) == 1 for comps in group_to_component.values())


def test_assign_grouped_folds_covers_every_row_exactly_once():
    rows = _bm25_rows()
    callables = _bm25_callables()
    folds = ia.assign_grouped_folds(
        rows, key_text_of=callables["key_text_of"], group_of=callables["group_of"], seed=1, fold_count=3
    )
    assigned = [item_id for fold in folds for item_id in fold]
    assert sorted(assigned) == sorted(row["item_id"] for row in rows)
    assert len(set(assigned)) == len(rows)


def test_assign_grouped_folds_rejects_too_many_folds():
    rows = _bm25_rows()
    callables = _bm25_callables()
    with pytest.raises(ia.InformationAuditError):
        ia.assign_grouped_folds(
            rows, key_text_of=callables["key_text_of"], group_of=callables["group_of"], seed=1, fold_count=100
        )


def test_retrieval_reachability_grouped_bm25_basic_properties():
    rows = _bm25_rows()
    callables = _bm25_callables()
    result = ia.retrieval_reachability_grouped_bm25(
        rows,
        key_text_of=callables["key_text_of"],
        group_of=callables["group_of"],
        labels_of=callables["labels_of"],
        label_fields=("label",),
        stratum_of=callables["stratum_of"],
        seed=7,
        fold_count=3,
        ks=(1, 2),
    )
    assert result["registry_label_count"] == 2
    assert result["scored_unit_count"] == len(rows)
    # coverage@2 must be >= coverage@1 (monotone in k) for a 2-label registry
    assert result["aggregate"]["2"]["full_set_coverage"] >= result["aggregate"]["1"]["full_set_coverage"]
    assert set(result["per_stratum"]) == {"alpha", "beta"}
    for k in ("1", "2"):
        assert result["worst_fold_full_set_coverage"][k] <= result["aggregate"][k]["full_set_coverage"] + 1e-9


# ---------------------------------------------------------------------------
# Q5, mode B: self-supplied membership
# ---------------------------------------------------------------------------


def test_deterministic_derangement_has_no_fixed_point_and_is_deterministic():
    ids = [f"c{i}" for i in range(10)]
    pairing = ia.deterministic_derangement(ids, seed=42)
    assert set(pairing) == set(ids)
    assert set(pairing.values()) == set(ids)
    assert all(key != value for key, value in pairing.items())
    assert ia.deterministic_derangement(ids, seed=42) == pairing  # deterministic
    assert ia.deterministic_derangement(ids, seed=43) != pairing  # seed-sensitive


def test_retrieval_reachability_self_supplied_own_vs_random_other():
    sep = MENTION_FIELD_SEPARATOR
    rows = [
        _row(
            "call_a",
            text="the chief executive officer mentioned acme corporation revenue",
            mentions=(f"ORG{sep}acme corporation",),
        ),
        _row(
            "call_b",
            text="quarterly results for globex industries were strong",
            mentions=(f"ORG{sep}globex industries",),
        ),
        _row(
            "call_c",
            text="no company names appear in this call at all",
            mentions=(f"ORG{sep}acme corporation",),  # NOT present in call_c's own text
        ),
    ]

    def key_text_of(row):
        return str(row["text"])

    def labels_of(row):
        return {"mention": row["mentions"]}

    result = ia.retrieval_reachability_self_supplied(
        rows, key_text_of=key_text_of, labels_of=labels_of, mention_field="mention", mention_separator=sep, seed=3
    )
    assert result["mention_total"] == 3
    per_call = {entry["item_id"]: entry for entry in result["per_call"]}
    assert per_call["call_a"]["own_context_present"] == 1
    assert per_call["call_b"]["own_context_present"] == 1
    assert per_call["call_c"]["own_context_present"] == 0
    assert 0.0 <= result["own_context_reachability"] <= 1.0
    assert 0.0 <= result["random_other_context_reachability"] <= 1.0
    assert "ORG" in result["per_entity_type"]


def test_retrieval_reachability_self_supplied_rejects_malformed_mention():
    def key_text_of(row):
        return "some text"

    def labels_of(row):
        return {"mention": ("no-separator-here",)}

    with pytest.raises(ia.InformationAuditError):
        ia.retrieval_reachability_self_supplied(
            [_row("x")], key_text_of=key_text_of, labels_of=labels_of, mention_field="mention",
            mention_separator=MENTION_FIELD_SEPARATOR, seed=1,
        )


# ---------------------------------------------------------------------------
# Q6
# ---------------------------------------------------------------------------


def test_decontamination_identity_reports_overlap():
    result = ia.decontamination_identity({"a", "b", "c"}, {"c", "d"})
    assert result["identity_overlap_count"] == 1
    assert result["clean"] is False
    result_clean = ia.decontamination_identity({"a", "b"}, {"c", "d"})
    assert result_clean["clean"] is True


def test_near_duplicate_pairs_finds_high_jaccard_pair():
    rows = [
        _row("x1", text="the quick brown fox jumps over the lazy dog today"),
        _row("x2", text="the quick brown fox jumps over the lazy dog today"),  # identical
        _row("x3", text="completely different unrelated sentence about nothing"),
    ]
    result = ia.near_duplicate_pairs(rows, key_text_of=lambda row: str(row["text"]), threshold=0.8)
    assert result["pair_count"] == 1
    assert {result["pairs"][0]["left"], result["pairs"][0]["right"]} == {"x1", "x2"}
    assert result["pairs"][0]["jaccard"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Q7
# ---------------------------------------------------------------------------


def test_external_supplementation_ledger_validates_shape():
    rows = ({"need": "n", "source": "s", "legality": "runtime-legal-input"},)
    result = ia.external_supplementation_ledger(rows)
    assert result["rows"] == [{"need": "n", "source": "s", "legality": "runtime-legal-input"}]
    with pytest.raises(ia.InformationAuditError):
        ia.external_supplementation_ledger(({"need": "n"},))


# ---------------------------------------------------------------------------
# Q8
# ---------------------------------------------------------------------------


def test_minimum_detectable_paired_effect_pp_hand_computed():
    # n=100, historical_discordant_rate=0.20 -> m=20 expected discordant pairs.
    # z_{0.025} = 1.9599639845400545, z_{0.80} = 0.8416212335729143 (standard
    # normal quantiles, hand-looked-up).
    # mde_p = (1.9599639845400545 + 0.8416212335729143) * sqrt(0.25 / 20)
    #       = 2.8015852181129688 * 0.11180339887498949 = 0.31322542...
    # mde_pp = 0.20 * 2 * mde_p * 100 = 12.529017...
    result = ia.minimum_detectable_paired_effect_pp(n=100, historical_discordant_rate=0.20)
    assert result["expected_discordant_pairs"] == pytest.approx(20.0)
    assert result["minimum_detectable_effect_pp"] == pytest.approx(12.529, abs=5e-3)


def test_minimum_detectable_paired_effect_pp_decreases_with_n():
    small = ia.minimum_detectable_paired_effect_pp(n=100, historical_discordant_rate=0.20)
    large = ia.minimum_detectable_paired_effect_pp(n=1000, historical_discordant_rate=0.20)
    assert large["minimum_detectable_effect_pp"] < small["minimum_detectable_effect_pp"]


def test_minimum_detectable_paired_effect_pp_rejects_too_few_expected_discordant_pairs():
    with pytest.raises(ia.InformationAuditError):
        ia.minimum_detectable_paired_effect_pp(n=2, historical_discordant_rate=0.01)


def test_power_table_uses_historical_citations():
    table = ia.power_table(ns={"DEV-500": 500, "DEV-1000": 1000})
    assert set(table["by_n"]) == {"DEV-500", "DEV-1000"}
    for citation in ia.HISTORICAL_DISCORDANCE_CITATIONS:
        assert citation["label"] in table["by_n"]["DEV-500"]


# ---------------------------------------------------------------------------
# Orchestration / CLI refuse-overwrite
# ---------------------------------------------------------------------------


def _synthetic_spec(mode: str) -> CarrierInformationSpec:
    rows = _bm25_rows()

    def construction_loader():
        return rows

    callables = _bm25_callables()
    roster = EvaluationRoster(
        name="synthetic-roster",
        split_role="dev",
        intended_n=12,
        stratum_counts={"alpha": 6, "beta": 6},
        selection_rule_note="synthetic equal-stratum roster for orchestration tests",
        identity_loader=lambda: frozenset({"u00", "u01"}),
    )
    return CarrierInformationSpec(
        carrier_lock_key="synthetic",
        task_kind="synthetic-task",
        strata_key="label",
        label_fields=("label",),
        field_legality={"text": "runtime-legal-input"},
        knowledge_source="synthetic in-memory rows",
        construction_loader=construction_loader,
        evaluation_rosters=(roster,),
        stratum_of=callables["stratum_of"],
        labels_of=callables["labels_of"],
        key_text_of=callables["key_text_of"],
        group_of=callables["group_of"],
        retrieval_mode=mode,
        corpus_structure_legality={},
        obs_org_supply_use={"obs": "o", "org": "r", "supply": "s", "use": "u"},
        external_supplementation=({"need": "n", "source": "s", "legality": "runtime-legal-input"},),
    )


def test_run_information_audit_writes_summary_and_readme(tmp_path):
    spec = _synthetic_spec("grouped_bm25")
    out_dir = tmp_path / "audit"
    result = ia.run_information_audit(spec, out_dir=out_dir, seed=5, ks=(1, 2), folds=3)
    assert (out_dir / "summary.json").is_file()
    assert (out_dir / "README.md").is_file()
    assert result["carrier_lock_key"] == "synthetic"
    on_disk = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert on_disk == result


def test_run_information_audit_refuses_to_overwrite(tmp_path):
    spec = _synthetic_spec("grouped_bm25")
    out_dir = tmp_path / "audit"
    ia.run_information_audit(spec, out_dir=out_dir, seed=5, ks=(1, 2), folds=3)
    with pytest.raises(ia.InformationAuditError):
        ia.run_information_audit(spec, out_dir=out_dir, seed=5, ks=(1, 2), folds=3)


# ---------------------------------------------------------------------------
# Spec builder validation (no real dataset touched -- construction_loader is
# lazy and is never invoked here)
# ---------------------------------------------------------------------------


def test_carrier_information_spec_rejects_missing_obs_org_supply_use_key():
    with pytest.raises(CarrierInformationSpecError):
        CarrierInformationSpec(
            carrier_lock_key="x",
            task_kind="t",
            strata_key="s",
            label_fields=("label",),
            field_legality={"f": "runtime-legal-input"},
            knowledge_source="k",
            construction_loader=lambda: (),
            evaluation_rosters=(
                EvaluationRoster(
                    name="r",
                    split_role="dev",
                    intended_n=1,
                    stratum_counts={"a": 1},
                    selection_rule_note="n",
                    identity_loader=lambda: frozenset(),
                ),
            ),
            stratum_of=lambda row: "a",
            labels_of=lambda row: {},
            key_text_of=lambda row: "",
            group_of=lambda row: "",
            retrieval_mode="grouped_bm25",
            corpus_structure_legality={},
            obs_org_supply_use={"obs": "a", "org": "b", "supply": "c"},  # missing "use"
            external_supplementation=({"need": "n", "source": "s", "legality": "runtime-legal-input"},),
        )


def test_carrier_information_spec_rejects_unknown_retrieval_mode():
    roster = EvaluationRoster(
        name="r",
        split_role="dev",
        intended_n=1,
        stratum_counts={"a": 1},
        selection_rule_note="n",
        identity_loader=lambda: frozenset(),
    )
    with pytest.raises(CarrierInformationSpecError):
        CarrierInformationSpec(
            carrier_lock_key="x",
            task_kind="t",
            strata_key="s",
            label_fields=("label",),
            field_legality={"f": "runtime-legal-input"},
            knowledge_source="k",
            construction_loader=lambda: (),
            evaluation_rosters=(roster,),
            stratum_of=lambda row: "a",
            labels_of=lambda row: {},
            key_text_of=lambda row: "",
            group_of=lambda row: "",
            retrieval_mode="not-a-real-mode",
            corpus_structure_legality={},
            obs_org_supply_use={"obs": "a", "org": "b", "supply": "c", "use": "d"},
            external_supplementation=({"need": "n", "source": "s", "legality": "runtime-legal-input"},),
        )


def test_evaluation_roster_rejects_empty_stratum_counts():
    with pytest.raises(CarrierInformationSpecError):
        EvaluationRoster(
            name="r",
            split_role="dev",
            intended_n=1,
            stratum_counts={},
            selection_rule_note="n",
            identity_loader=lambda: frozenset(),
        )


def test_evaluation_roster_rejects_non_positive_intended_n():
    with pytest.raises(CarrierInformationSpecError):
        EvaluationRoster(
            name="r",
            split_role="dev",
            intended_n=0,
            stratum_counts={"a": 1},
            selection_rule_note="n",
            identity_loader=lambda: frozenset(),
        )


@pytest.mark.parametrize("builder", [audio2tool_spec, slurp_spec, earnings21_conec_spec])
def test_builders_produce_valid_specs_without_touching_real_data(builder, tmp_path):
    """Every builder defers its GOVERNED-DATASET reads (module docstring of
    ``information_audit_specs``): constructing the spec must never call
    ``construction_loader`` or read from the fake ``lock``/``root`` below --
    passing placeholder values for those two must not raise. ``slurp_spec``
    is the one builder that also reads its own already-committed DEV-*
    roster receipts EAGERLY at build time (module docstring), so it alone
    needs the real repository root; the other two builders ignore
    ``repo_root`` entirely until their lazy ``construction_loader`` runs."""

    fake_lock: dict[str, object] = {}
    fake_root = tmp_path / "does-not-exist"
    spec = builder(fake_lock, fake_root, REPO_ROOT)
    assert isinstance(spec, CarrierInformationSpec)
    assert spec.carrier_lock_key
    assert spec.retrieval_mode in {"grouped_bm25", "self_supplied_membership"}
    assert callable(spec.construction_loader)
    assert spec.evaluation_rosters
