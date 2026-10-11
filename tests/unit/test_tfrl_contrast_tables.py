"""E-T3: the contrast tables (``scripts/analysis/tfrl_contrast_tables.py``) and the cross-fitted delivery fitter
(``scripts/analysis/tfrl_delivery_fit.py``), proved on synthetic rows.

What is proved: counts-only output; the ``<3`` suppression; a sha-stable re-run; the forbidden-key self-check;
the four-way value-in-supply split; the item-credit sign counters; the deterministic half split, threshold
choice and family rules of the fitter.  Zero model, tokenizer, encoder, network and GPU contacts; no
``SPEECHRL_DATA_DIR`` read.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_ANALYSIS = REPO / "scripts" / "analysis"
if str(_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS))

import tfrl_contrast_tables as T  # noqa: E402
import tfrl_delivery_fit as F  # noqa: E402

# ---------------------------------------------------------------------------
# suppression and primitives


def test_cell_suppresses_one_and_two_but_not_zero_or_three() -> None:
    assert [T.cell(n) for n in (0, 1, 2, 3, 40)] == [0, "<3", "<3", 3, 40]


def test_rate_is_withheld_below_the_floor() -> None:
    assert T.rate_pct(1, 2) is None
    assert T.rate_pct(1, 4) == 25.0


def test_percentile_is_nearest_rank_and_dist_withholds_small_groups() -> None:
    assert T.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.50) == 5
    assert T.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.99) == 10
    assert T.dist([4.0, 5.0]) == {"n": "<3", "mean": None, "p50": None, "p99": None}
    assert T.dist([1, 2, 3, None]) == {"n": 3, "mean": 2.0, "p50": 2, "p99": 3}


@pytest.mark.parametrize(
    "rank,length,expected",
    [(1, 3, "1"), (3, 3, "3"), (4, 6, "4-5"), (5, 6, "4-5"), (8, 9, "6-10"), (12, 20, "11+"),
     (None, 3, "off-list"), (None, 0, "no-shortlist")],
)
def test_rank_bin(rank, length, expected) -> None:
    assert T.rank_bin(rank, length) == expected


def test_gold_rank_is_one_based() -> None:
    assert T.gold_rank(["a_x", "b_y", "c_z"], "b_y") == 2
    assert T.gold_rank(["a_x"], "q_q") is None


# ---------------------------------------------------------------------------
# value-in-supply split


def _state(value="oslo", typ="place_name", printed=frozenset(), card=False, store=frozenset(),
           store_cards=False, train=frozenset(), own="u1"):
    return T.supply_state(value, typ, set(printed), card, set(store), store_cards, frozenset(train), own)


def test_supply_state_is_a_four_way_partition_in_priority_order() -> None:
    assert _state(printed={("place_name", "oslo")}) == "in_supply"
    assert _state(printed={("city", "oslo")}) == "in_supply"          # E2: under another type
    assert _state(card=True) == "in_supply"                          # E3
    assert _state(store={"oslo"}) == "in_store_not_delivered"
    assert _state(store_cards=True) == "in_store_not_delivered"
    assert _state(train={"u2"}) == "in_train_not_in_store"
    assert _state(train={"u1"}) == "nowhere"                          # only the row's own utterance
    assert _state() == "nowhere"
    assert _state(store={"oslo"}, train={"u2"}) == "in_store_not_delivered"


# ---------------------------------------------------------------------------
# tables


def _items():
    items = []
    for _ in range(5):
        items.append({"class": "MISSING", "type": "date", "scenario": "calendar", "state": "in_supply"})
    for _ in range(2):
        items.append({"class": "MISSING", "type": "date", "scenario": "calendar", "state": "nowhere"})
    items.append({"class": "SPURIOUS", "type": "person", "scenario": "email", "state": "nowhere"})
    return items


def test_failure_cube_counts_partition_the_total_and_suppress_small_cells() -> None:
    cube = T.failure_cube(_items())
    assert cube["columns"][:3] == ["class", "slot_type", "scenario"]
    by = {(r[0], r[1], r[2]): r[3:] for r in cube["rows"]}
    # in_supply 5, in_store 0, in_train 0, nowhere 2 -> "<3", total 7
    assert by[("MISSING", "date", "calendar")] == [5, 0, 0, "<3", 7]
    assert by[("SPURIOUS", "person", "email")] == [0, 0, 0, "<3", "<3"]
    assert cube["marginals"]["class_x_state"]["MISSING"]["in_supply"] == 5
    assert cube["marginals"]["class_x_scenario"]["SPURIOUS"] == {"email": "<3"}


def test_failure_cube_rows_follow_the_class_order() -> None:
    items = [{"class": "FORMAT", "type": "a", "scenario": "s", "state": "nowhere"},
             {"class": "SPURIOUS", "type": "a", "scenario": "s", "state": "nowhere"}]
    classes = [r[0] for r in T.failure_cube(items)["rows"]]
    assert classes == ["SPURIOUS", "FORMAT"]


def test_empty_gold_table() -> None:
    rows = [{"scenario": "play", "gold_empty": True, "filled": i < 2, "spurious": ["genre"] if i < 2 else []}
            for i in range(4)]
    rows += [{"scenario": "play", "gold_empty": False, "filled": True, "spurious": ["artist"]}]
    table = T.empty_gold_table(rows)
    p = table["per_scenario"]["play"]
    assert p["empty_gold_rows"] == 4 and p["false_fill_rows"] == "<3"
    assert p["false_fill_rate_pct"] == 50.0
    assert table["spurious_types_by_scenario"]["play"] == {"genre": "<3"}
    assert table["spurious_types_all_rows_by_scenario"]["play"] == {"artist": "<3", "genre": "<3"}


def test_intent_table_histogram_covers_wrong_rows_only() -> None:
    rows = [{"scenario": "alarm", "intent_ok": True, "shortlist_len": 3, "rank": 1} for _ in range(5)]
    rows += [{"scenario": "alarm", "intent_ok": False, "shortlist_len": 3, "rank": 2} for _ in range(3)]
    rows += [{"scenario": "alarm", "intent_ok": False, "shortlist_len": 3, "rank": None} for _ in range(4)]
    table = T.intent_table(rows)
    p = table["per_scenario"]["alarm"]
    assert p["rows"] == 12 and p["intent_wrong_rows"] == 7
    assert p["gold_on_shortlist_rows"] == 8
    assert p["wrong_rank_histogram"]["2"] == 3 and p["wrong_rank_histogram"]["off-list"] == 4
    assert p["wrong_rank_histogram"]["1"] == 0
    assert set(p["wrong_rank_histogram"]) == set(T.RANK_BINS)


def test_structure_table_uses_nearest_rank_percentiles() -> None:
    rows = [{"scenario": "s", "exemplars": 20, "cards": c, "prompt_tokens": 1000 + c} for c in range(1, 11)]
    block = T.structure_table(rows)["overall"]
    assert block["cards"]["p50"] == 5 and block["cards"]["p99"] == 10
    assert block["supplied_tokens"]["p50"] == 1005
    none_tokens = T.structure_table([dict(r, prompt_tokens=None) for r in rows])["overall"]
    assert none_tokens["supplied_tokens"]["mean"] is None


def test_item_credit_counts_signs_against_the_lock_column() -> None:
    rendered = {f"r{i}": {"ace:i1:aaa"} for i in range(6)}
    rendered["r6"] = {"ace:i1:bbb"}
    column = {f"r{i}": 1.0 for i in range(7)}
    lock = {"r0": 0.5, "r1": 0.5, "r2": 0.5, "r3": 1.0, "r4": 1.0, "r5": 1.5, "r6": 0.0}
    table = T.item_credit_table(["ace:i1:bbb", "ace:i1:aaa"], rendered, column, lock)
    a = next(i for i in table["items"] if i["item_id"] == "ace:i1:aaa")
    assert a == {"item_id": "ace:i1:aaa", "rendered_rows": 6, "helpful": 3, "harmful": "<3", "neutral": "<3"}
    assert [i["item_id"] for i in table["items"]] == ["ace:i1:aaa", "ace:i1:bbb"]


def test_playbook_item_ids_are_read_from_snapshot_or_items(tmp_path: Path) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps({"values": [{"value_id": "value:ace-playbook::ace:i1:aaa", "content": "x"}]}))
    assert T.load_playbook_item_ids(snap) == ["ace:i1:aaa"]
    items = tmp_path / "items.json"
    items.write_text(json.dumps({"items": [{"item_id": "ace:i1:bbb"}, {"item_id": "ace:i1:aaa"}]}))
    assert T.load_playbook_item_ids(items) == ["ace:i1:aaa", "ace:i1:bbb"]
    empty = tmp_path / "empty.json"
    empty.write_text("{}")
    with pytest.raises(T.TablesError):
        T.load_playbook_item_ids(empty)


def test_rendered_item_ids_match_prefixed_value_ids() -> None:
    row = {"solver_ids": ["value:ace-playbook::ace:i1:aaa", "value:other::z"], "ex_rendered": [], "contracts": []}
    assert T.rendered_item_ids(row, {"ace:i1:aaa", "ace:i1:bbb"}) == {"ace:i1:aaa"}


# ---------------------------------------------------------------------------
# artefact discipline


def _document():
    return {
        "schema": T.SCHEMA,
        "table_a": T.failure_cube(_items()),
        "table_f": {"columns": T.REFUSED_COLUMNS, "rows": []},
        "table_g": {"playbook_release": None, "items": []},
    }


def test_finalize_is_sha_stable_and_ignores_its_own_field() -> None:
    first = T.finalize(_document())
    second = T.finalize(copy.deepcopy(_document()))
    assert first == second
    assert len(first["tables_sha256"]) == 64
    assert T.finalize(first)["tables_sha256"] == first["tables_sha256"]
    changed = _document()
    changed["table_a"]["rows"][0][3] = 99
    assert T.finalize(changed)["tables_sha256"] != first["tables_sha256"]


def test_the_artefact_is_json_of_counts_only() -> None:
    parsed = json.loads(json.dumps(T.finalize(_document()), sort_keys=True))
    leaves = []

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        else:
            leaves.append(node)

    walk(parsed)
    assert all(isinstance(x, (int, float, str, type(None), bool)) for x in leaves)
    assert max(len(x) for x in leaves if isinstance(x, str)) <= T.MAX_STRING


@pytest.mark.parametrize("key", ["text", "Transcript", "gold", "value_text", "utterance", "answer"])
def test_forbidden_keys_fail_the_self_check(key) -> None:
    doc = _document()
    doc["table_a"]["marginals"][key] = 1
    with pytest.raises(T.TablesError, match="forbidden key"):
        T.finalize(doc)


def test_an_overlong_string_fails_the_self_check() -> None:
    doc = _document()
    doc["table_a"]["rows"].append(["x" * 201])
    with pytest.raises(T.TablesError, match="longer"):
        T.finalize(doc)


def test_table_f_is_an_empty_buffer_with_the_driver_columns() -> None:
    assert T.REFUSED_COLUMNS == ["candidate_id", "operator_class", "predicted_pp", "measured_pp", "verdict"]


def test_exchange_table_copies_without_recomputing() -> None:
    pool = {"split": "devel", "rows": 1000,
            "analytic_rates": {"remove_1_spurious_entity_pp": 0.0282},
            "node_rates": {"per_raw_exact_row_pp": 0.0567, "note": "long prose"},
            "empirical_rates": {k: {"mean_pp": 0.1, "n": 5, "median_pp": 9.9} for k in T.EXCHANGE_EMPIRICAL_KEYS}}
    report = {"pools": {name: pool for name in T.EXCHANGE_POOLS}}
    table = T.exchange_table(report, "f" * 64)
    a2 = table["pools"]["a2"]
    assert a2["analytic_rates_pp"] == {"remove_1_spurious_entity_pp": 0.0282}
    assert a2["node_rates"] == {"per_raw_exact_row_pp": 0.0567}
    assert a2["empirical_rates_pp"]["remove_one_spurious_entity"] == {"mean_pp": 0.1, "n": 5}
    assert table["source_sha256"] == "f" * 64


# ---------------------------------------------------------------------------
# the cross-fitted delivery fitter


def test_halves_are_deterministic_disjoint_and_cover_the_clusters() -> None:
    clusters = [f"u{i}" for i in range(11)] * 2
    a1, b1 = F.utterance_halves(clusters)
    a2, b2 = F.utterance_halves(list(reversed(clusters)))
    assert (a1, b1) == (a2, b2)
    assert not (a1 & b1) and (a1 | b1) == set(clusters)
    assert len(a1) == 6 and len(b1) == 5
    assert F.utterance_halves(clusters, seed=1) != (a1, b1)


def test_choose_threshold_breaks_ties_by_fewer_edits_then_smaller_t() -> None:
    grid = (0.05, 0.10, 0.20)
    assert F.choose_threshold(grid, {0.05: 1.0, 0.10: 1.0, 0.20: 0.5}, {0.05: 9, 0.10: 4, 0.20: 1}) == 0.10
    assert F.choose_threshold(grid, {0.05: 1.0, 0.10: 1.0, 0.20: 0.5}, {0.05: 4, 0.10: 4, 0.20: 1}) == 0.05
    assert F.choose_threshold(grid, {0.05: 0.0, 0.10: 0.0, 0.20: 0.0}, {0.05: 0, 0.10: 0, 0.20: 0}) == 0.05


def test_pooled_slu_is_micro_f1_over_word_plus_char() -> None:
    np = pytest.importorskip("numpy")
    m = np.zeros((2, 10))
    m[0, :6] = [1, 0, 0, 1, 0, 0]
    m[1, :6] = [0, 1, 1, 0, 1, 1]
    assert F.pooled_slu(m) == pytest.approx(50.0)  # tp 2, fp 2, fn 2 -> 2*2 / (2*2 + 2 + 2)


class _Stats:
    intent_n = {"alarm_set": 200, "tiny_x": 10}
    intent_with_entities = {"alarm_set": 4, "tiny_x": 0}

    def type_share(self, intent, typ):
        return {("alarm_set", "time"): 0.9, ("alarm_set", "place"): 0.004, ("tiny_x", "place"): 0.0}.get(
            (intent, typ), 0.0)

    article_table = {"date|the": {"included": 1, "excluded": 40}, "date|a": {"included": 5, "excluded": 5},
                     "time|my": {"included": 0, "excluded": 3}}


class _Ent:
    def __init__(self, type, filler):
        self.type, self.filler = type, filler

    def __eq__(self, other):
        return (self.type, self.filler) == (other.type, other.filler)


def _env():
    def wilson(successes, n, z):
        p = successes / n
        centre = p + z * z / (2 * n)
        half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
        return (centre + half) / (1 + z * z / n)

    return {"SlotEntity": lambda type, filler: _Ent(type, filler), "fold": str.lower,
            "wilson_upper_bound": wilson, "z": 1.96, "strip_cache": {}}


def test_article_strip_set_needs_opportunities_and_a_low_included_share() -> None:
    assert F.article_strip_set(_Stats.article_table, 0.10) == {("date", "the")}
    assert F.article_strip_set(_Stats.article_table, 0.60) == {("date", "the"), ("date", "a")}


def test_family_ee_drops_all_only_when_the_wilson_bound_is_below_t_and_never_fills() -> None:
    pairs = [(0, _Ent("time", "7"))]
    assert F.apply_family("ee", 0.10, list(pairs), "alarm_set", _Stats(), _env()) == []
    assert F.apply_family("ee", 0.02, list(pairs), "alarm_set", _Stats(), _env()) == pairs
    assert F.apply_family("ee", 0.10, list(pairs), None, _Stats(), _env()) == pairs
    assert F.apply_family("ee", 0.10, [], "alarm_set", _Stats(), _env()) == []


def test_family_ti_is_guarded_by_pool_size() -> None:
    pairs = [(0, _Ent("time", "7")), (1, _Ent("place", "x"))]
    out = F.apply_family("ti", 0.01, list(pairs), "alarm_set", _Stats(), _env())
    assert [i for i, _ in out] == [0]
    assert F.apply_family("ti", 0.01, list(pairs), "tiny_x", _Stats(), _env()) == pairs  # < 100 exemplars


def test_family_article_strips_a_leading_determiner() -> None:
    pairs = [(0, _Ent("date", "The fifth of may")), (1, _Ent("date", "the"))]
    out = F.apply_family("article", 0.10, list(pairs), "x_y", _Stats(), _env())
    assert out[0][1].filler == "fifth of may" and out[1][1].filler == "the"


def test_unknown_family_is_refused() -> None:
    with pytest.raises(F.FitError):
        F.apply_family("nope", 0.1, [(0, _Ent("a", "b"))], "x", _Stats(), _env())


def test_the_fit_report_seal_is_stable_and_text_free() -> None:
    doc = {"schema": F.SCHEMA, "family": "ee", "refused": True, "rule_table": None}
    sealed = F.seal(dict(doc), "report_sha256")
    assert sealed == F.seal(dict(sealed), "report_sha256")
    with pytest.raises(F.FitError):
        F.seal({"answer": 1}, "report_sha256")


def test_every_family_grid_contains_its_v4g_point() -> None:
    assert 0.10 in F.GRIDS["ee"] and 0.01 in F.GRIDS["ti"] and 0.10 in F.GRIDS["article"]


def test_family_oclock_strips_a_trailing_oclock_token_from_a_time_filler_only() -> None:
    pairs = [(0, _Ent("time", "seven o'clock")), (1, _Ent("time", "7 OClock")), (2, _Ent("time", "oclock")),
             (3, _Ent("date", "five o'clock")), (4, _Ent("time", "half past"))]
    out = F.apply_family("oclock", 1.0, list(pairs), "alarm_set", _Stats(), _env())
    assert [e.filler for _i, e in out] == ["seven", "7", "oclock", "five o'clock", "half past"]


def test_family_oclock_honours_the_candidates_intent_and_type_scope() -> None:
    pairs = [(0, _Ent("time", "seven o'clock"))]
    env = _env()
    env["intents"] = ("alarm_query", "alarm_set")
    assert F.apply_family("oclock", 1.0, list(pairs), "alarm_set", _Stats(), env)[0][1].filler == "seven"
    assert F.apply_family("oclock", 1.0, list(pairs), "calendar_set", _Stats(), env) == pairs
    assert F.apply_family("oclock", 1.0, list(pairs), None, _Stats(), env) == pairs
    env2 = _env()
    env2["types"] = ("date",)
    assert F.apply_family("oclock", 1.0, list(pairs), "alarm_set", _Stats(), env2) == pairs


def test_oclock_has_no_threshold_one_nominal_grid_point() -> None:
    assert F.GRIDS["oclock"] == (1.0,) and "oclock" in F.FAMILIES
