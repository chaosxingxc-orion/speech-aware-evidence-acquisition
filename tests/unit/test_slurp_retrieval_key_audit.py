"""Unit tests for ``analysis.slurp_retrieval_key_audit`` on a synthetic pool.

No SLURP bytes, no vectors from the data root, no network: every fixture here
is hand-built so the five measurements, the registered-ranker fusion and the
owner's decision table are pinned by construction rather than by a run.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from speech_aware_evidence_acquisition.analysis import slurp_retrieval_key_audit as audit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def dev_row(sample_id, *, population="NEW500", scenario="alarm", intent="alarm_set",
            entities=(), baseline_correct=False, draft="alarm_set"):
    return audit.DevRow(
        sample_id=sample_id,
        population=population,
        scenario=scenario,
        intent=intent,
        entities=tuple(entities),
        baseline_intent_correct=baseline_correct,
        draft_intent=draft,
    ).validate()


def key_row(facet_id, intent, entities=()):
    return audit.KeyRow(facet_id=facet_id, intent=intent, entities=tuple(entities)).validate()


@pytest.fixture
def pool():
    """Four keys in two intents, three DEV rows with known neighbours."""

    keys = (
        key_row("facet:content:1", "alarm_set", (("time", "nine am"),)),
        key_row("facet:content:2", "alarm_set", (("date", "friday"),)),
        key_row("facet:content:3", "email_query", (("person", "ann"),)),
        key_row("facet:content:4", "email_query", (("person", "bob"),)),
    )
    rows = (
        dev_row("s1", entities=(("time", "nine am"),), baseline_correct=False),
        dev_row("s2", population="OLD500", scenario="email", intent="email_query",
                entities=(("person", "ann"), ("person", "zoe")), baseline_correct=True,
                draft="email_query"),
        dev_row("s3", scenario="alarm", intent="alarm_set", entities=(), baseline_correct=True),
    )
    return rows, keys


# ---------------------------------------------------------------------------
# Vector plumbing
# ---------------------------------------------------------------------------


def test_l2_normalise_is_zero_safe():
    matrix = np.array([[3.0, 4.0], [0.0, 0.0]])
    out = audit.l2_normalise(matrix)
    assert np.allclose(out[0], [0.6, 0.8])
    assert np.allclose(out[1], [0.0, 0.0])


def test_cosine_matrix_refuses_mismatched_key_space():
    with pytest.raises(audit.RetrievalKeyAuditError, match="SAME model"):
        audit.cosine_matrix(np.ones((2, 3)), np.ones((4, 5)))


def test_load_vectors_jsonl_round_trip_and_errors(tmp_path):
    path = tmp_path / "v.jsonl"
    path.write_text(
        json.dumps({"id": "a", "vector": [1.0, 0.0]}) + "\n"
        + json.dumps({"id": "b", "vector": [0.0, 1.0]}) + "\n",
        encoding="utf-8",
    )
    ids, matrix = audit.load_vectors_jsonl(path)
    assert ids == ("a", "b")
    assert matrix.shape == (2, 2)

    ragged = tmp_path / "ragged.jsonl"
    ragged.write_text(
        json.dumps({"id": "a", "vector": [1.0]}) + "\n"
        + json.dumps({"id": "b", "vector": [0.0, 1.0]}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(audit.RetrievalKeyAuditError, match="ragged"):
        audit.load_vectors_jsonl(ragged)

    duplicate = tmp_path / "dup.jsonl"
    duplicate.write_text(
        json.dumps({"id": "a", "vector": [1.0]}) + "\n"
        + json.dumps({"id": "a", "vector": [0.0]}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(audit.RetrievalKeyAuditError, match="duplicate"):
        audit.load_vectors_jsonl(duplicate)


def test_align_refuses_a_missing_vector(pool):
    rows, keys = pool
    with pytest.raises(audit.RetrievalKeyAuditError, match="no vector"):
        audit.align_keys(keys, ("facet:content:1",), np.ones((1, 2)))
    with pytest.raises(audit.RetrievalKeyAuditError, match="no query vector"):
        audit.align_queries(rows, ("s1",), np.ones((1, 2)))


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_top_k_orders_by_score_then_index():
    scores = np.array([[0.1, 0.9, 0.9, 0.5]])
    assert audit.top_k_indices(scores, 3).tolist() == [[1, 2, 3]]


def test_top_k_refuses_k_above_the_key_count():
    with pytest.raises(audit.RetrievalKeyAuditError, match="exceeds"):
        audit.top_k_indices(np.zeros((1, 2)), 3)


def test_majority_intent_breaks_ties_by_best_rank():
    assert audit.majority_intent(["b", "a", "a"]) == "a"
    assert audit.majority_intent(["b", "a"]) == "b"
    assert audit.majority_intent(["a"]) == "a"
    with pytest.raises(audit.RetrievalKeyAuditError):
        audit.majority_intent([])


# ---------------------------------------------------------------------------
# The registered-ranker fusion
# ---------------------------------------------------------------------------


def test_fusion_dominance_margin_at_the_registered_weights():
    weights = audit.RankWeights()
    assert weights.w_cos == 0.5 and weights.w_prior == 0.3 and weights.w_agree == 0.2
    # (0.3 + 0.1) / 0.5 = 0.8 raw cosine
    assert audit.fusion_dominance_margin(weights) == pytest.approx(0.8)


def test_rank_weights_come_from_the_registered_policy_config(tmp_path):
    path = tmp_path / "kb-policy.json"
    path.write_text(json.dumps({"rank_weights": {"w_cos": 0.4, "w_prior": 0.4, "w_agree": 0.2}}),
                    encoding="utf-8")
    weights = audit.RankWeights.from_policy_config(path)
    assert (weights.w_cos, weights.w_prior, weights.w_agree) == (0.4, 0.4, 0.2)


def test_fusion_reproduces_the_lock_formula(pool):
    _rows, keys = pool
    weights = audit.RankWeights()
    cosines = np.array([[0.9, 0.1, 0.8, -0.2]])
    scores = audit.fuse_speech_and_state(cosines, [k.intent for k in keys], ["alarm_set"], weights)
    # keys 0,1 agree with the draft: both dimensions recall them, agreement 1.
    assert scores[0, 0] == pytest.approx(0.5 * 0.9 + 0.3 + 0.2)
    assert scores[0, 1] == pytest.approx(0.5 * 0.1 + 0.3 + 0.2)
    # key 2 disagrees: content only, agreement 1/2.
    assert scores[0, 2] == pytest.approx(0.5 * 0.8 + 0.1)
    # key 3 has a non-positive cosine AND disagrees with the draft, so NO dimension
    # recalls it -- exactly the keys the lock's recall stage never returns at all.
    assert scores[0, 3] == pytest.approx(0.0)
    # the 0.8-margin consequence: a much better disagreeing cosine still loses.
    assert scores[0, 1] > scores[0, 2]


def test_fusion_without_a_parsed_draft_ranks_exactly_as_speech_alone(pool):
    _rows, keys = pool
    cosines = np.array([[0.2, 0.9, 0.5, 0.1]])
    scores = audit.fuse_speech_and_state(cosines, [k.intent for k in keys], [None], audit.RankWeights())
    assert audit.top_k_indices(scores, 4).tolist() == audit.top_k_indices(cosines, 4).tolist()


def test_fusion_shape_checks():
    with pytest.raises(audit.RetrievalKeyAuditError, match="2-D"):
        audit.fuse_speech_and_state(np.zeros(3), ["a"], [None], audit.RankWeights())
    with pytest.raises(audit.RetrievalKeyAuditError, match="key_intents"):
        audit.fuse_speech_and_state(np.zeros((1, 2)), ["a"], [None], audit.RankWeights())
    with pytest.raises(audit.RetrievalKeyAuditError, match="draft_intents"):
        audit.fuse_speech_and_state(np.zeros((2, 1)), ["a"], [None], audit.RankWeights())


# ---------------------------------------------------------------------------
# The five measurements
# ---------------------------------------------------------------------------


def test_measure_rows_computes_all_five_quantities(pool):
    rows, keys = pool
    # s1 sees the two alarm keys; s2 sees one email + one alarm; s3 sees two email keys.
    neighbours = np.array([[0, 1], [2, 0], [2, 3]])
    out = audit.measure_rows(rows, keys, neighbours)

    s1, s2, s3 = out
    # 1 intent recall
    assert s1.intent_recall == 1.0 and s2.intent_recall == 1.0 and s3.intent_recall == 0.0
    # 2 vote: s2's neighbours tie 1-1, broken by rank -> the rank-0 email key
    assert s1.vote_intent == "alarm_set" and s2.vote_intent == "email_query"
    assert s3.vote_intent == "email_query"
    assert (s1.vote_correct, s2.vote_correct, s3.vote_correct) == (1.0, 1.0, 0.0)
    # 3 corrective power: s1 saves a wrong baseline, s3 harms a right one, s2 neither
    assert (s1.is_save, s1.is_harm, s1.corrective_net) == (True, False, 1.0)
    assert (s2.is_save, s2.is_harm, s2.corrective_net) == (False, False, 0.0)
    assert (s3.is_save, s3.is_harm, s3.corrective_net) == (False, True, -1.0)
    # 4 filler recall: s1 finds its one slot; s2 finds one of two; s3 has no gold slot
    assert s1.filler_recall == pytest.approx(1.0)
    assert s2.filler_recall == pytest.approx(0.5)
    assert s3.filler_recall is None and s3.gold_filler_count == 0
    # 5 echo: the majority equals the row's own draft label
    assert (s1.echo, s2.echo, s3.echo) == (1.0, 1.0, 0.0)


def test_measure_rows_refuses_a_shape_mismatch(pool):
    rows, keys = pool
    with pytest.raises(audit.RetrievalKeyAuditError, match="n_dev_rows"):
        audit.measure_rows(rows, keys, np.array([[0, 1]]))


def test_summarise_reports_corrective_harm_and_net(pool):
    rows, keys = pool
    out = audit.measure_rows(rows, keys, np.array([[0, 1], [2, 0], [2, 3]]))
    summary = audit.summarise(out)
    assert summary["n"] == 3
    assert summary["baseline_wrong_rows"] == 1 and summary["baseline_right_rows"] == 2
    assert summary["saves"] == 1 and summary["harms"] == 1
    assert summary["corrective_share_of_wrong"] == pytest.approx(100.0)
    assert summary["harm_share_of_right"] == pytest.approx(50.0)
    assert summary["net_rows"] == 0
    assert summary["net_pp"] == pytest.approx(0.0)
    assert summary["filler_rows_scored"] == 2
    assert summary["filler_recall_at_k"] == pytest.approx(75.0)
    assert summary["echo_rate"] == pytest.approx(200.0 / 3.0)


def test_summarise_of_an_empty_population():
    assert audit.summarise([]) == {"n": 0}


def test_scenario_table_is_one_row_per_gold_scenario(pool):
    rows, keys = pool
    out = audit.measure_rows(rows, keys, np.array([[0, 1], [2, 0], [2, 3]]))
    table = audit.scenario_table(out)
    assert [row["scenario"] for row in table] == ["alarm", "email"]
    assert table[0]["n"] == 2 and table[1]["n"] == 1


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def _measurements(pool, neighbours):
    rows, keys = pool
    return audit.measure_rows(rows, keys, np.asarray(neighbours))


def test_absolute_ci_brackets_the_point_estimate(pool):
    out = _measurements(pool, [[0, 1], [2, 0], [2, 3]])
    result = audit.absolute_ci(out, n_replicates=200)
    net = result["corrective_net_pp"]
    assert net["left_mean"] == 0.0
    assert net["delta"] == pytest.approx(audit.summarise(out)["net_pp"])
    assert net["ci_low"] <= net["delta"] <= net["ci_high"]
    assert net["seed"] == audit.BOOTSTRAP_SEED
    assert net["ci_level"] == audit.CI_LEVEL


def test_delta_ci_is_paired_and_signed(pool):
    good = _measurements(pool, [[0, 1], [2, 0], [0, 1]])
    bad = _measurements(pool, [[2, 3], [2, 0], [2, 3]])
    result = audit.delta_ci(bad, good, n_replicates=200)["vote_accuracy_pp"]
    assert result["delta"] > 0.0
    assert result["n"] == 3


def test_delta_ci_refuses_unpaired_rows(pool):
    rows, keys = pool
    left = audit.measure_rows(rows, keys, np.array([[0, 1], [2, 0], [2, 3]]))
    right = audit.measure_rows(rows[:2], keys, np.array([[0, 1], [2, 0]]))
    with pytest.raises(audit.RetrievalKeyAuditError, match="same rows"):
        audit.delta_ci(left, right, n_replicates=50)


# ---------------------------------------------------------------------------
# The owner's decision table
# ---------------------------------------------------------------------------


def _per_set(pool, mapping):
    return {set_id: {5: _measurements(pool, neighbours)} for set_id, neighbours in mapping.items()}


def test_decision_never_lets_a_text_only_set_win(pool):
    # q-gold-text has the best net; it must still be excluded as a candidate.
    per_set = _per_set(pool, {
        "q-gold-text": [[0, 1], [2, 0], [0, 1]],   # saves s1, no harm -> best
        "q-draft": [[2, 3], [2, 0], [0, 1]],
        "q-speech-glap": [[0, 1], [2, 0], [2, 3]],  # save s1, harm s3 -> net 0
    })
    result = audit.decision(per_set)
    assert set(result["eligible_sets"]) == {"q-speech-glap"}
    assert result["winner"] == "q-speech-glap"
    assert "q-gold-text" in result["diagnostic_only"]
    assert "q-draft" in result["diagnostic_only"]
    assert result["gold_text_upper_bound_net_pp"] > result["winner_net_pp"]
    assert result["cross_modal_loss_pp"] == pytest.approx(
        result["gold_text_upper_bound_net_pp"] - result["winner_net_pp"]
    )


def test_decision_closes_the_branch_below_the_gate(pool):
    per_set = _per_set(pool, {
        "q-draft": [[0, 1], [2, 0], [0, 1]],
        "q-speech-glap": [[0, 1], [2, 0], [2, 3]],  # net 0.0 pp
    })
    result = audit.decision(per_set)
    assert result["winner_net_pp"] == pytest.approx(0.0)
    assert result["gate_cleared"] is False
    assert result["verdict"].startswith("CLOSED")
    assert result["gate_net_pp"] == audit.CORRECTIVE_NET_GATE_PP


def test_decision_tie_prefers_speech_alone_over_speech_plus_state(pool):
    same = [[0, 1], [2, 0], [0, 1]]
    per_set = _per_set(pool, {"q-speech-glap+state": same, "q-speech-glap": list(same)})
    result = audit.decision(per_set)
    assert result["winner"] == "q-speech-glap"
    assert result["runner_up"] == "q-speech-glap+state"
    assert result["gate_cleared"] is True


def test_decision_refuses_a_diagnostics_only_audit(pool):
    per_set = _per_set(pool, {"q-draft": [[0, 1], [2, 0], [0, 1]]})
    with pytest.raises(audit.RetrievalKeyAuditError, match="no speech-containing"):
        audit.decision(per_set)


# ---------------------------------------------------------------------------
# Loaders and the decontamination report
# ---------------------------------------------------------------------------


def test_load_dev_rows_and_key_rows(tmp_path):
    dev_path = tmp_path / "dev-rows.jsonl"
    dev_path.write_text(json.dumps({
        "sample_id": "slurp:devel:000011:audio-1", "population": "NEW500", "scenario": "alarm",
        "intent": "alarm_set", "entities": [{"type": "time", "filler": "nine am"}],
        "baseline_intent_correct": 1.0, "draft_intent": "alarm_set",
    }) + "\n", encoding="utf-8")
    rows = audit.load_dev_rows(dev_path)
    assert rows[0].baseline_intent_correct is True
    assert rows[0].entities == (("time", "nine am"),)

    key_path = tmp_path / "train-facets.jsonl"
    key_path.write_text(json.dumps({
        "facet_id": "facet:content:1", "intent": "alarm_set",
        "entities": [{"type": "time", "filler": "nine am"}],
    }) + "\n", encoding="utf-8")
    assert audit.load_key_rows(key_path)[0].facet_id == "facet:content:1"


def test_dev_row_refuses_an_unknown_population():
    with pytest.raises(audit.RetrievalKeyAuditError, match="NEW500 or OLD500"):
        dev_row("s1", population="TEST500")


def test_load_dev_rows_refuses_an_empty_file(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    with pytest.raises(audit.RetrievalKeyAuditError, match="empty"):
        audit.load_dev_rows(path)


def test_decontamination_report_states_the_split_boundaries(pool):
    rows, keys = pool
    query_set = audit.QuerySet(
        query_set_id="q-speech-glap", query_ids=tuple(r.sample_id for r in rows),
        query_vectors=np.ones((3, 2)), key_ids=tuple(k.facet_id for k in keys),
        key_vectors=np.ones((4, 2)), encoder="glap", contains_speech=True,
        fuses_state=False, provenance={},
    )
    report = audit.decontamination_report(rows, keys, [query_set])
    assert report["held_out_test_split"]["loaded"] is False
    assert report["devel_sentence_text"]["written_to_any_artifact"] is False
    assert report["frozen_core_contacts"] == 0
    assert report["key_side"]["split"] == "train"
    assert report["query_sets"][0]["role"] == "candidate"


# ---------------------------------------------------------------------------
# MF-7b: the cross-modal separation and the v2 decision table
# ---------------------------------------------------------------------------


def _engineered_rows(net_by_row, *, echo, population="NEW500"):
    """Rows engineered to a known net corrective power and echo rate."""

    out = []
    for index, net in enumerate(net_by_row):
        is_save = net > 0
        is_harm = net < 0
        out.append(
            audit.RowMeasurement(
                sample_id=f"s{index}", population=population, scenario="alarm",
                intent_recall=1.0, vote_correct=1.0 if is_save else 0.0,
                vote_intent="alarm_set", corrective_net=float(net),
                is_save=is_save, is_harm=is_harm, baseline_correct=not is_save,
                filler_recall=None, gold_filler_count=0,
                echo=1.0 if index < round(echo * len(net_by_row)) else 0.0,
            )
        )
    return tuple(out)


def test_cosine_separation_splits_matched_from_unmatched_pairs(pool):
    rows, keys = pool
    # Query i is the unit vector of its own intent's axis, so a matched pair
    # has cosine 1 and an unmatched one cosine 0 -- separation exactly 1.0.
    axis = {"alarm_set": [1.0, 0.0], "email_query": [0.0, 1.0]}
    query_vectors = np.array([axis[row.intent] for row in rows], dtype=float)
    key_vectors = np.array([axis[key.intent] for key in keys], dtype=float)
    query_set = audit.QuerySet(
        query_set_id="q-speech-lco", query_ids=tuple(r.sample_id for r in rows),
        query_vectors=query_vectors, key_ids=tuple(k.facet_id for k in keys),
        key_vectors=key_vectors, encoder="lco-embedding-omni-3b",
        contains_speech=True, fuses_state=False, provenance={},
    )
    block = audit.cosine_separation(query_set, rows, keys)
    assert block["matched"]["mean"] == pytest.approx(1.0)
    assert block["unmatched"]["mean"] == pytest.approx(0.0)
    assert block["mean_delta"] == pytest.approx(1.0)
    assert block["queries"] == 3
    assert block["keys"] == 4


def test_decision_v2_refuses_a_degenerate_winner_however_high_its_net():
    per_set = {
        # +40 pp but every vote echoes the draft: cannot license KU-S1.
        "q-speech-lco+state": {5: _engineered_rows([1, 1, 1, 1, 0], echo=1.0)},
        # +20 pp and no echo at all: the winner the rule is meant to find.
        "q-speech-lco": {5: _engineered_rows([1, 1, 0, 0, 0], echo=0.0)},
    }
    outcome = audit.decision_v2(
        per_set, ci_low_by_set={"q-speech-lco+state": 30.0, "q-speech-lco": 5.0})
    assert outcome["degenerate_sets"] == ["q-speech-lco+state"]
    assert outcome["winner"] == "q-speech-lco"
    assert outcome["gate_cleared"] is True


def test_decision_v2_needs_both_the_point_estimate_and_the_interval():
    per_set = {"q-speech-nemotron": {5: _engineered_rows([1, 1, 0, 0, 0], echo=0.0)}}
    cleared = audit.decision_v2(per_set, ci_low_by_set={"q-speech-nemotron": 0.4})
    assert cleared["point_estimate_cleared"] is True
    assert cleared["gate_cleared"] is True
    refused = audit.decision_v2(per_set, ci_low_by_set={"q-speech-nemotron": -0.4})
    assert refused["point_estimate_cleared"] is True
    assert refused["interval_cleared"] is False
    assert refused["gate_cleared"] is False
    assert refused["verdict"].startswith("CLOSED")


def test_decision_v2_closes_when_every_speech_set_is_degenerate():
    per_set = {"q-speech-glap+state": {5: _engineered_rows([1, 1, 1, 0, 0], echo=1.0)}}
    outcome = audit.decision_v2(per_set, ci_low_by_set={"q-speech-glap+state": 20.0})
    assert outcome["winner"] is None
    assert outcome["gate_cleared"] is False
    assert outcome["verdict"].startswith("CLOSED")


def test_build_summary_omits_the_paired_block_when_the_reference_is_absent(pool):
    rows, keys = pool
    query_vectors = np.eye(3, 2)
    key_vectors = np.eye(4, 2)
    query_set = audit.QuerySet(
        query_set_id="q-speech-lco", query_ids=tuple(r.sample_id for r in rows),
        query_vectors=query_vectors, key_ids=tuple(k.facet_id for k in keys),
        key_vectors=key_vectors, encoder="lco-embedding-omni-3b",
        contains_speech=True, fuses_state=False, provenance={},
    )
    weights = audit.RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)
    per_set = {
        "q-speech-lco": audit.run_query_set(query_set, rows, keys, weights, k_values=(1,))
    }
    summary = audit.build_summary(
        per_set, {"q-speech-lco": query_set}, weights, decision_k=1,
        baseline_run_id="run", draft_run_id="draft", snapshot_sha256="0" * 64,
        key_npz_sha256="1" * 64, accounting={}, reference="q-draft",
    )
    assert summary["delta_ci90"] == {}


def test_key_space_coherence_separates_a_healthy_tower_from_a_broken_one():
    # Text keys: two tight clusters, one per intent -> a healthy tower.
    key_vectors = np.array(
        [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0], [0.01, 0.99]], dtype=float)
    key_labels = ["alarm_set", "alarm_set", "email_query", "email_query"]
    # Speech queries: interleaved, so every nearest neighbour is the wrong
    # intent -> a tower carrying no intent structure at all.
    query_vectors = np.array(
        [[1.0, 0.0], [0.0, 1.0], [0.99, 0.01], [0.01, 0.99]], dtype=float)
    query_labels = ["alarm_set", "email_query", "email_query", "alarm_set"]
    label_vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float)
    block = audit.key_space_coherence(
        encoder="lco-embedding-omni-3b",
        key_vectors=key_vectors, key_labels=key_labels,
        query_vectors=query_vectors, query_labels=query_labels,
        label_vectors=label_vectors, label_labels=["alarm_set", "email_query"],
    )
    assert block["text_key_space"]["nearest_other_same_label_pp"] == pytest.approx(100.0)
    assert block["speech_query_space"]["nearest_other_same_label_pp"] == pytest.approx(0.0)
    assert block["train_text_to_label"]["nearest_label_accuracy_pp"] == pytest.approx(100.0)
    assert block["train_text_to_label"]["chance_pp"] == pytest.approx(50.0)
