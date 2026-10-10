"""SCR TF-0 offline learner on SYNTHETIC pools: model-free and data-free.

A seeded generator builds a Fold-B-like roster (an N1-like context feature, an independent noise feature, a lock column of ten
count columns per row and counterfactual action columns). The cores under test are the pure functions of
``scripts/analysis/slurp_scr_offline_learner.py``; the real-data loaders only feed them.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import slurp_scr_offline_learner as L  # noqa: E402

N = 600
FEATS = ("n1_share", "noise")


def _lock_matrix(rng, gold_empty):
    """Ten count columns per row: a false fill on 60 % of empty-gold rows; 75 % of non-empty rows exact."""
    base = np.zeros((len(gold_empty), 10))
    base_empty = np.zeros((len(gold_empty), 10))
    for k, ge in enumerate(gold_empty):
        base[k, 9] = base_empty[k, 9] = 1.0
        if ge:
            if rng.random() < 0.6:
                base[k, [1, 4, 7]] = 2.0
        else:
            if rng.random() < 0.75:
                base[k, [0, 3, 6]] = 3.0
            else:
                base[k, [0, 3, 6]] = 1.0
                base[k, [1, 4, 7]] = 1.0
                base[k, [2, 5, 8]] = 2.0
            base_empty[k, [2, 5, 8]] = 3.0
    return base, base_empty


def _world(seed=3, *, planted=True, n=N):
    """``planted``: the ``empty`` action helps exactly where the N1-like feature is high (empty-gold rows concentrate there);
    ``r1-c3`` is a harmful action (it breaks exact rows)."""
    rng = np.random.default_rng(seed)
    ids = [f"slurp:train:{i}:a" for i in range(n)]
    utt = [f"slurp:train:{i}" for i in range(n)]
    f = rng.random(n)
    p_empty = np.where(f > 0.5, 0.92, 0.12) if planted else np.full(n, 0.35)
    gold_empty = rng.random(n) < p_empty
    base, base_empty = _lock_matrix(rng, gold_empty)
    harmful = base.copy()
    for k in range(n):
        if not gold_empty[k] and rng.random() < 0.5:
            harmful[k, [1, 4, 7]] += 1.0
            harmful[k, [0, 3, 6]] = np.maximum(harmful[k, [0, 3, 6]] - 1.0, 0.0)
    twin = base.copy()
    sigs = {s: {"n1_share": float(f[k]), "noise": float(rng.random())} for k, s in enumerate(ids)}
    scenario = [("alarm", "music", "lists")[k % 3] for k in range(n)]
    deltas = {L.EMPTY: base_empty - base, "r1-c3": harmful - base}
    ind = {L.EMPTY: L.indicators(base, base_empty, base, base_empty, gold_empty),
           "r1-c3": L.indicators(base, harmful, base, harmful, gold_empty)}
    view = L.make_view(ids=ids, utt=utt, scenario=scenario, gold_empty=gold_empty, base=base, twin=twin, deltas=deltas,
                       ind=ind)
    return view, sigs


def _params(**kw):
    p = {"max_depth": 3, "min_leaf": 40, "margin_pp_per_row": 0.0033, "shrink": 0.0, "intent_weight": 0.0,
         "learners": ["tree", "logistic"], "feature_variants": {"pre": FEATS}, "draws": 300, "seed": 11}
    p.update(kw)
    return p


def _boot(view, draws=300):
    return L.DRV.Bootstrap(view["ids"], dict(zip(view["ids"], view["utt"])), draws=draws, seed=20260915)


# ---------------------------------------------------------------------------


def test_the_linearised_gain_is_the_first_order_pooled_delta_and_additive_across_rows():
    view, _ = _world()
    base, delta = view["base"], view["deltas"][L.EMPTY]
    g = L.linear_gain(base, delta)
    # the linearisation is close to the exact change for a small share of swapped rows (first order)
    few = np.zeros(N, dtype=bool)
    few[::25] = True
    swapped = base.copy()
    swapped[few] += delta[few]
    exact = L.DRV.pooled(swapped)["slu_f1_pp"] - L.DRV.pooled(base)["slu_f1_pp"]
    assert abs(g[few].sum() - exact) < 0.1 * max(abs(exact), 0.5)
    # one row: first-order accuracy
    k = int(np.argmax(np.abs(g)))
    one = base.copy()
    one[k] += delta[k]
    exact_one = L.DRV.pooled(one)["slu_f1_pp"] - L.DRV.pooled(base)["slu_f1_pp"]
    assert g[k] == pytest.approx(exact_one, abs=1e-3)
    # a row whose counts do not change gains nothing; the gain is linear in the delta
    assert np.all(L.linear_gain(base, np.zeros_like(delta)) == 0)
    assert np.allclose(L.linear_gain(base, 2 * delta), 2 * g)


def test_a_tree_recovers_a_planted_threshold_and_respects_depth_and_leaf_floor():
    rng = np.random.default_rng(1)
    X = rng.random((500, 3))
    y = np.where(X[:, 1] > 0.6, 1.0, -0.5) + rng.normal(0, 0.05, 500)
    tree = L.fit_tree(X, y, ["a", "b", "c"], max_depth=3, min_leaf=50)
    assert tree["feature"] == "b" and tree["threshold"] == pytest.approx(0.6, abs=0.05)
    leaves = L.tree_leaves(tree)
    assert all(leaf["n"] >= 50 for leaf in leaves) and sum(leaf["n"] for leaf in leaves) == 500
    assert max(len(leaf["rule"]) for leaf in leaves) <= 3
    low = L.tree_leaf(tree, {"a": 0.5, "b": 0.2, "c": 0.5})["value"]
    high = L.tree_leaf(tree, {"a": 0.5, "b": 0.9, "c": 0.5})["value"]
    assert low == pytest.approx(-0.5, abs=0.05) and high == pytest.approx(1.0, abs=0.05)
    deep = L.fit_tree(X, y, ["a", "b", "c"], max_depth=1, min_leaf=50)
    assert len(L.tree_leaves(deep)) == 2


def test_a_tree_does_not_split_below_twice_the_leaf_floor_and_shrink_pulls_toward_zero():
    X = np.arange(80, dtype=float).reshape(-1, 1)
    y = np.where(X[:, 0] > 40, 1.0, 0.0)
    tree = L.fit_tree(X, y, ["a"], max_depth=3, min_leaf=50)
    assert "leaf" in tree and tree["n"] == 80
    shrunk = L.fit_tree(X, y + 2.0, ["a"], max_depth=3, min_leaf=50, shrink=80.0)
    assert 0 < shrunk["value"] < float((y + 2.0).mean())


def test_tree_predict_and_leaf_ids_agree_with_tree_leaf():
    rng = np.random.default_rng(2)
    X = rng.random((300, 2))
    y = np.where(X[:, 0] > 0.4, 2.0, 0.0)
    names = ["u", "v"]
    tree = L.fit_tree(X, y, names, max_depth=2, min_leaf=30)
    pred = L.tree_predict(tree, X, names)
    ids = L.tree_leaf_ids(tree, X, names)
    for i in range(0, 300, 17):
        leaf = L.tree_leaf(tree, dict(zip(names, X[i])))
        assert leaf["value"] == pred[i] and leaf["leaf"] == ids[i]


def test_cross_fitting_never_scores_a_row_with_a_model_that_saw_it():
    rng = np.random.default_rng(5)
    X = rng.random((400, 2))
    halves = np.array([i % 2 for i in range(400)])
    y = np.where(X[:, 0] > 0.5, 1.0, 0.0) + rng.normal(0, 0.1, 400)
    learner = L.Learner("tree", ["a", "b"], max_depth=2, min_leaf=40)
    base = L.crossfit(X, {"act": y}, halves, learner)["act"]
    # rewrite the half-1 targets: half-1 predictions must NOT move (they come from the half-0 model), half-0 must
    y2 = y.copy()
    y2[halves == 1] = -y2[halves == 1] + 5.0
    again = L.crossfit(X, {"act": y2}, halves, learner)["act"]
    assert np.array_equal(base[halves == 1], again[halves == 1])
    assert not np.array_equal(base[halves == 0], again[halves == 0])
    # the logistic decomposition obeys the same rule
    lg = L.Learner("logistic", ["a", "b"])
    b2 = L.crossfit(X, {"act": y}, halves, lg)["act"]
    a2 = L.crossfit(X, {"act": y2}, halves, lg)["act"]
    assert np.array_equal(b2[halves == 1], a2[halves == 1])


def test_choose_routes_to_the_best_action_only_above_the_margin_and_ties_go_to_the_earlier_action():
    pred = {"a": np.array([0.5, 0.0, 0.2, 0.2]), "b": np.array([0.1, 0.3, 0.2, 0.001])}
    out = L.choose(pred, [L.NOOP, "a", "b"], 0.05)
    assert list(out) == ["a", "b", "a", "a"]
    out = L.choose(pred, [L.NOOP, "a", "b"], 0.25)
    assert list(out) == ["a", "b", L.NOOP, L.NOOP]
    assert list(L.choose(pred, [L.NOOP], 0.0)) == [L.NOOP] * 4


def test_the_post_solver_empty_action_moves_no_intent_and_the_routed_column_is_the_lock_plus_chosen_deltas():
    view, _ = _world()
    assert np.all(view["deltas"][L.EMPTY][:, 9] == 0)
    choice = np.array([L.EMPTY if k % 3 == 0 else L.NOOP for k in range(N)], dtype=object)
    routed = L.routed_matrix(view, choice)
    assert np.array_equal(routed[choice == L.NOOP], view["base"][choice == L.NOOP])
    assert np.array_equal(routed[choice == L.EMPTY], (view["base"] + view["deltas"][L.EMPTY])[choice == L.EMPTY])
    r = L.evaluate_choice(view, choice, _boot(view))
    assert r["intent_rows_moved"] == 0 and r["delta_intent_pp"] == 0.0
    assert r["rows_routed"] == int((choice == L.EMPTY).sum()) and r["routed_rows_by_action"] == {L.EMPTY: 200}
    assert r["ci95_vs_lock_slu_pp"][0] <= r["delta_vs_lock_slu_pp"] <= r["ci95_vs_lock_slu_pp"][1]


def test_evaluate_choice_exchange_arithmetic_counts_false_fills_and_exact_rows_from_the_credit_indicators():
    view, _ = _world()
    everywhere = np.array([L.EMPTY] * N, dtype=object)
    r = L.evaluate_choice(view, everywhere, _boot(view), detail=True)
    ge = view["gold_empty"]
    ff_expected = int(((L.pred_items(view["base"]) > 0) & ge).sum())
    lost_expected = int((L.is_exact(view["base"]) & ~ge).sum())
    assert r["exchange"]["false_fills_removed_net"] == ff_expected
    assert r["exchange"]["nonempty_exact_lost"] == lost_expected and r["exchange"]["nonempty_exact_gained"] == 0
    assert r["exchange"]["predicted_pp_false_fill_x0.033_plus_nonempty_exact_x0.070"] == pytest.approx(
        0.033 * ff_expected - 0.070 * lost_expected, abs=1e-3)
    assert set(r["per_scenario"]) == {"alarm", "music", "lists"}
    assert sum(v["rows"] for v in r["per_scenario"].values()) == N
    assert r["empty_vs_non_empty"]["empty_gold"]["rows"] + r["empty_vs_non_empty"]["non_empty_gold"]["rows"] == N
    assert r["empty_vs_non_empty"]["empty_gold"]["false_fills_removed_net"] == ff_expected
    assert r["empty_vs_non_empty"]["non_empty_gold"]["exact_lost"] == lost_expected
    assert r["equal_stratum"]["natural_mixture_delta_slu_pp"] == r["delta_vs_lock_slu_pp"]


def test_stratum_weights_give_every_scenario_the_same_total_weight():
    w = L.stratum_weights(["a"] * 6 + ["b"] * 3 + ["c"] * 1)
    assert w.sum() == pytest.approx(10.0)
    assert w[:6].sum() == pytest.approx(w[6:9].sum()) == pytest.approx(w[9:].sum())


def test_a_planted_context_effect_is_recovered_by_the_cross_fitted_router_and_the_harmful_action_is_not_chosen():
    view, sigs = _world(planted=True)
    boot = _boot(view)
    params = _params()
    fill = L.fill_values(sigs, view["ids"], FEATS)
    res = L.analyse(view, sigs, params, boot, fill=fill, groups_available={"pre": True},
                    actions=(L.NOOP, "r1-c3", L.EMPTY), headline=("tree", "pre"))
    head = res["variants"]["tree|pre"]["subsets"]["default"]
    assert head["delta_vs_lock_slu_pp"] > 0.5 and head["ci95_vs_lock_slu_pp"][0] > 0
    assert head["routed_rows_by_action"].get(L.EMPTY, 0) > 100 and "r1-c3" not in head["routed_rows_by_action"]
    assert head["intent_rows_moved"] == 0
    # the 'post' subset has only the empty action; the template subset only the harmful one (nothing routed)
    assert res["variants"]["tree|pre"]["subsets"]["post_solver_only"]["delta_vs_lock_slu_pp"] > 0.5
    templ = res["variants"]["tree|pre"]["subsets"]["solver_template_only"]
    assert templ["rows_routed"] == 0 and templ["delta_vs_lock_slu_pp"] == 0.0
    # the logistic variant is reported beside the tree
    assert "logistic|pre" in res["variants"]
    assert res["_choice"]["default"].shape == (N,)


def test_without_any_planted_context_effect_the_router_does_not_claim_a_gain():
    view, sigs = _world(seed=9, planted=False)
    boot = _boot(view)
    fill = L.fill_values(sigs, view["ids"], FEATS)
    res = L.analyse(view, sigs, _params(margin_pp_per_row=0.01), boot, fill=fill, groups_available={"pre": True},
                    actions=(L.NOOP, "r1-c3", L.EMPTY), headline=("tree", "pre"))
    head = res["variants"]["tree|pre"]["subsets"]["default"]
    assert head["ci95_vs_lock_slu_pp"][0] <= 0.0 or head["delta_vs_lock_slu_pp"] <= 0.0


def test_unavailable_feature_group_is_reported_not_silently_dropped():
    view, sigs = _world()
    boot = _boot(view)
    params = _params(feature_variants={"pre": FEATS, "pre+p1tag": FEATS + ("p1_tag_ok",)})
    fill = L.fill_values(sigs, view["ids"], FEATS + ("p1_tag_ok",))
    res = L.analyse(view, sigs, params, boot, fill=fill, groups_available={"pre": True, "pre+p1tag": False},
                    actions=(L.NOOP, L.EMPTY), headline=("tree", "pre"))
    assert res["variants"]["tree|pre+p1tag"] == {"unavailable": True}
    assert fill["p1_tag_ok"] == 0.0


def test_the_pinned_routing_table_is_executable_from_the_signature_alone_and_survives_json():
    view, sigs = _world(planted=True)
    params = _params()
    fill = L.fill_values(sigs, view["ids"], FEATS)
    boot = _boot(view)
    res = L.analyse(view, sigs, params, boot, fill=fill, groups_available={"pre": True},
                    actions=(L.NOOP, "r1-c3", L.EMPTY), headline=("tree", "pre"))
    oof = res["_oof"]
    table = L.build_routing_table(view, sigs, params, fill=fill, features=list(FEATS), actions=[L.NOOP, "r1-c3", L.EMPTY],
                                  oof=oof, groups="pre")
    choice = table.pop("_choice")
    loaded = json.loads(json.dumps(L.jsonable(table)))
    for i, s in enumerate(view["ids"]):
        assert L.route_row(loaded, sigs[s]) == choice[i]
    assert table["in_sample_routed_rows"] == int((choice != L.NOOP).sum()) > 0
    assert sum(c["n"] for c in table["cells"]) == N
    assert all(set(c["cell"]) == set(table["action_order"]) for c in table["cells"])
    # a missing feature takes its pinned fill value
    row = {"n1_share": None, "noise": None}
    assert L.route_row(loaded, row) == L.route_row(loaded, {"n1_share": fill["n1_share"], "noise": fill["noise"]})


def test_the_rendered_table_text_carries_no_row_text_and_names_every_feature(tmp_path):
    view, sigs = _world(planted=True)
    feats = ("n1_share", "audio_seconds")
    for s in view["ids"]:
        sigs[s]["audio_seconds"] = 3.0
    params = _params()
    fill = L.fill_values(sigs, view["ids"], feats)
    table = L.build_routing_table(view, sigs, params, fill=fill, features=list(feats), actions=[L.NOOP, L.EMPTY], oof=None,
                                  groups="pre")
    table.pop("_choice")
    text = L.render_table_md(table, {"rows": N, "pool_roster": "synthetic roster"})
    for f in feats:
        assert f"`{f}`" in text
    assert "Routing cells" in text and "Decision procedure" in text


def test_leave_one_pool_out_scores_the_other_pool_with_its_own_lock_and_columns():
    view, sigs = _world(planted=True, seed=4)
    other, other_sigs = _world(planted=True, seed=4)  # the same rows seen through a second flight
    params = _params(learners=["tree"])
    fill = L.fill_values(sigs, view["ids"], FEATS)
    Xp, _ = L.design_matrix(sigs, view["ids"], FEATS, fill)
    Xq, _ = L.design_matrix(other_sigs, view["ids"], FEATS, fill)
    out = L.lopo(view, Xp, other, Xq, {"empty": L.EMPTY}, {"empty": L.EMPTY}, params, _boot(other), FEATS)
    assert out["families"] == ["empty"]
    assert out["delta_vs_lock_slu_pp"] > 0.3 and out["intent_rows_moved"] == 0
    # pools over different rows are refused
    shifted = dict(other, ids=[s + "x" for s in other["ids"]])
    with pytest.raises(L.ScrError, match="same rows"):
        L.lopo(view, Xp, shifted, Xq, {"empty": L.EMPTY}, {"empty": L.EMPTY}, params, _boot(other), FEATS)


def test_the_signature_takes_no_gold_and_is_computed_from_receipts_and_pinned_tables_only():
    assert "gold" not in " ".join(inspect.signature(L.row_signature).parameters)
    table = {"intent_n": {"alarm_set": 10, "general_quirky": 10}, "intent_with_entities": {"alarm_set": 9, "general_quirky": 1}}
    pool = {"values": {f"e{k}": {"intent": "alarm_set" if k < 6 else "general_quirky", "n_entities": 0 if k % 2 else 2}
                       for k in range(20)}}
    phase = {"boundary": [], "ex_ids": [f"e{k}" for k in range(20)], "ex_scores": [0.9, 0.5, 0.4],
             "note": {"ids": ["alarm_set", "general_quirky"], "unresolved": [2, 0], "slot_named": [1, 0],
                      "evidence_refs": [3, 0], "distinction_tokens": [11, 4]}}
    sig = L.row_signature(phase, {"audio_seconds": 4.5}, pool, table, {"headset": True, "audio_seconds": 9.0})
    assert sig["n1_share"] == 0.5 and sig["rate_rank1"] == 0.9 and sig["candidates"] == 2.0
    assert sig["audio_seconds"] == 4.5 and sig["headset"] == 1.0 and sig["top1_cosine"] == 0.9
    assert sig["distinction_tokens_rank1"] == 11.0 and sig["unresolved_rank1"] == 2.0 and sig["evidence_refs_rank1"] == 3.0
    assert sig["rate_vote"] == 0.1 or sig["rate_vote"] == 0.9
    assert 0.0 <= sig["n1_same_intent"] <= 1.0
    # no note -> the note features are None, the supply features remain
    none = L.row_signature(dict(phase, note=None), {}, pool, table, None)
    assert none["rate_rank1"] is None and none["candidates"] is None and none["headset"] is None
    assert none["audio_seconds"] is None and none["n1_share"] == 0.5
    # every documented feature of every group is defined in the doc table
    assert all(f in L.FEATURE_DOC for group in L.FEATURE_GROUPS.values() for f in group)
    assert set(sig) == set(L.FEATURE_GROUPS["pre"])


def test_the_verdict_action_empties_the_lock_row_only_where_the_aggressive_arm_answered_empty():
    rng = np.random.default_rng(6)
    ge = rng.random(120) < 0.4
    lock, lock_empty = _lock_matrix(rng, ge)
    c3 = lock.copy()
    c3[:30, 6:9] = 0.0           # the aggressive arm answers empty on the first 30 rows
    pool = {"v4g": {"lock": lock, "aa": lock, "r1-c3": c3}, "v3": {"lock": lock, "aa": lock, "r1-c3": c3},
            "v4g_empty": {"lock": lock_empty}, "v3_empty": {"lock": lock_empty}}
    info = L.CATALOG["empty-if-c3-i1"]
    delta, ind = L.pool_action("empty-if-c3-i1", info, pool, ge)
    fired = L.pred_items(c3) == 0
    assert np.array_equal(delta[fired], (lock_empty - lock)[fired])
    assert np.all(delta[~fired] == 0)
    assert np.all(delta[:, 9] == 0)
    d_plain, _ = L.pool_action("r1-c3", L.CATALOG["r1-c3"], pool, ge)
    assert np.array_equal(d_plain, c3 - lock)
    d_empty, _ = L.pool_action(L.EMPTY, L.CATALOG[L.EMPTY], pool, ge)
    assert np.array_equal(d_empty, lock_empty - lock)


def test_catalog_subsets_and_action_parsing():
    assert L.DEFAULT_ACTIONS == (L.NOOP, "r1-c3", "r1-i2-c3", "r1-c5", "r1-i2-c4", L.EMPTY)
    sub = L.subsets_of(L.DEFAULT_ACTIONS)
    assert sub["default"] == list(L.DEFAULT_ACTIONS)
    assert sub["solver_template_only"] == [L.NOOP, "r1-c3", "r1-i2-c3", "r1-c5", "r1-i2-c4"]
    assert sub["post_solver_only"] == [L.NOOP, L.EMPTY]
    assert "empty-if-c3-i1" in sub["default_plus_verdict"] and "empty-if-c3-i2" in sub["post_solver_plus_verdict"]
    assert set(L.CATALOG["r6-p1"]) >= {"kind", "pool", "arm", "family"} and L.CATALOG["r6-p1"]["pool"] == "r6"
    assert L.parse_actions("r1-c3,empty") == (L.NOOP, "r1-c3", L.EMPTY)
    with pytest.raises(SystemExit):
        L.parse_actions("r1-c9")


def test_outputs_are_write_once_and_a_contact_counter_must_stay_zero(tmp_path):
    d = tmp_path / "analysis"
    L.refuse_overwrite(d)
    d.mkdir()
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        L.refuse_overwrite(d)
    L.assert_zero_contacts({"contacts": dict(L.CONTACTS)})
    with pytest.raises(L.ScrError):
        L.assert_zero_contacts({"contacts": dict(L.CONTACTS, model=1)})
    assert set(L.CONTACTS) == {"model", "server", "tokenizer", "encoder", "embedder", "scorer_subprocess", "network",
                               "gpu", "paid_api"}


def test_default_margin_is_a_tenth_of_the_false_fill_exchange_rate_and_the_floor_margin_stays_in_the_sensitivity():
    class A:
        max_depth, min_leaf, margin_pp_per_row, shrink, intent_weight, draws, seed = 3, 60, None, 0.0, 0.0, 10, 1
    p = L.default_params(A)
    assert p["margin_pp_per_row"] == pytest.approx(0.0033)
    view, sigs = _world()
    fill = L.fill_values(sigs, view["ids"], FEATS)
    out = L.margin_sensitivity(view, sigs, _params(), _boot(view), fill=fill, actions=(L.NOOP, L.EMPTY),
                               headline=("tree", "pre"))
    assert any("floor/min_leaf" in k for k in out) and any(k.startswith("zero") for k in out)
    # a bigger margin never routes more rows
    routed = [v["rows_routed"] for v in out.values()]
    import re
    by_margin = sorted(zip([float(re.search(r"\(([0-9.]+) pp/row\)$", k).group(1)) for k in out], routed))
    assert all(a[1] >= b[1] for a, b in zip(by_margin, by_margin[1:]))


def test_oracle_picks_the_best_realised_action_per_row_and_never_loses_to_the_lock():
    view, _ = _world()
    boot = _boot(view)
    block = L.oracle_block(view, (L.NOOP, "r1-c3", L.EMPTY), boot)
    assert block["default"]["delta_vs_lock_slu_pp"] >= block["post_solver_only"]["delta_vs_lock_slu_pp"] >= 0.0
    assert block["default"]["delta_intent_pp"] == 0.0 or block["default"]["delta_intent_pp"] > -1e-9
    # the noise-only ceiling: a twin identical to the lock has nothing to select
    assert block["noise_only_twin_best_of_lock_and_aa"]["rows_routed"] == 0
