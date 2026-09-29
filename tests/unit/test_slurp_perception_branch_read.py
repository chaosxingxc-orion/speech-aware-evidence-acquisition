"""``scripts/analysis/slurp_perception_branch_read.py`` (same-flight instrument phase 2, merge
set C, item 4): pure, model-free, gold-free-at-import tests of the level-1 read -- gold rank,
paired top1/present bootstrap reads, the twin null bar, the utterance-level read beside it, and
the ledger-reproduction refusal. Every "gold label" here is a synthetic, made-up intent id string
passed directly by the test, never read from a real dataset file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS_ANALYSIS = _REPO / "scripts" / "analysis"
if str(_SCRIPTS_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ANALYSIS))

import slurp_perception_branch_read as spbr  # noqa: E402


def _branches_receipt(candidates_by_branch: dict[str, tuple[str, ...]]) -> dict:
    return {
        "schema": "saea-perception-branch-arms-v1", "phase_id": "perception",
        "level": 1, "delivered_branch_id": "A",
        "branches": [
            {"branch_id": branch_id, "candidate_intent_ids": list(candidates)}
            for branch_id, candidates in candidates_by_branch.items()
        ],
    }


def _row(sample_id: str, candidates_by_branch: dict[str, tuple[str, ...]]) -> dict:
    return {
        "sample_id": sample_id,
        "native_episode_receipt": {"perception_branches": _branches_receipt(candidates_by_branch)},
    }


def test_branch_gold_rank_finds_gold_at_its_position():
    assert spbr.branch_gold_rank(("a", "b", "c"), "b") == 2
    assert spbr.branch_gold_rank(("a", "b", "c"), "a") == 1


def test_branch_gold_rank_is_none_when_gold_is_off_the_list():
    assert spbr.branch_gold_rank(("a", "b"), "z") is None


def test_branch_row_outcome_top1_present_and_rank_agree():
    outcome = spbr.branch_row_outcome(("gold", "other"), "gold")
    assert outcome == {"rank": 1, "present": True, "top1": True}
    outcome = spbr.branch_row_outcome(("other", "gold"), "gold")
    assert outcome == {"rank": 2, "present": True, "top1": False}
    outcome = spbr.branch_row_outcome(("other",), "gold")
    assert outcome == {"rank": None, "present": False, "top1": False}


def test_level1_row_outcomes_covers_every_declared_branch():
    row = _row("s1", {"B": ("x", "gold"), "T": ("gold",), "A": ("gold",)})
    outcomes = spbr.level1_row_outcomes(row, "gold")
    assert outcomes["B"]["rank"] == 2
    assert outcomes["T"]["top1"] is True
    assert outcomes["A"]["top1"] is True


def test_level1_row_outcomes_refuses_a_row_with_no_receipt():
    with pytest.raises(spbr.PerceptionBranchReadError, match="no perception_branches"):
        spbr.level1_row_outcomes({"sample_id": "s1", "native_episode_receipt": {}}, "gold")


def _rows_for_paired_read(n_promoted: int, n_total: int) -> list[dict]:
    """``n_promoted`` rows where B ranks gold 1st and A does not (B beats A); the rest agree."""

    rows = []
    for index in range(n_total):
        sample_id = f"slurp:train:s{index:04d}:0"
        if index < n_promoted:
            rows.append(_row(sample_id, {"B": ("gold", "other"), "T": ("other", "gold"), "A": ("other", "gold")}))
        else:
            rows.append(_row(sample_id, {"B": ("other", "gold"), "T": ("other", "gold"), "A": ("other", "gold")}))
    return rows


def test_paired_top1_read_finds_the_promoted_rows():
    rows = _rows_for_paired_read(n_promoted=20, n_total=100)
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    assert result["n"] == 100
    assert result["discordant"] == 20
    assert result["point_pp"] == pytest.approx(20.0, abs=0.01)
    assert result["ci95"][0] < result["point_pp"] < result["ci95"][1]


def test_paired_top1_read_is_deterministic():
    rows = _rows_for_paired_read(n_promoted=15, n_total=80)
    gold = {row["sample_id"]: "gold" for row in rows}
    first = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    second = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    assert first == second


def test_paired_top1_read_ignores_rows_without_a_gold_label():
    rows = _rows_for_paired_read(n_promoted=5, n_total=10)
    gold = {rows[0]["sample_id"]: "gold"}
    result = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    assert result["n"] == 1


def test_paired_top1_read_refuses_when_nothing_qualifies():
    with pytest.raises(spbr.PerceptionBranchReadError, match="no row"):
        spbr.paired_top1_read([], {}, branch_id="B", against="A")


def test_paired_present_read_uses_the_present_metric():
    rows = [
        _row("s1", {"B": ("gold",), "A": ()}),
        _row("s2", {"B": (), "A": ("gold",)}),
    ]
    gold = {"s1": "gold", "s2": "gold"}
    result = spbr.paired_present_read(rows, gold, branch_id="B", against="A")
    assert result["metric"] == "present"
    # +1 on s1 (B present, A absent), -1 on s2 (B absent, A present): net 0.
    assert result["point_pp"] == pytest.approx(0.0, abs=0.01)


def test_twin_null_bar_is_zero_when_t_and_a_always_agree():
    rows = [_row(f"s{i}", {"T": ("gold",), "A": ("gold",)}) for i in range(30)]
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.twin_null_bar(rows, gold)
    assert result["point_pp"] == pytest.approx(0.0, abs=0.01)
    assert result["abs_point_pp"] == pytest.approx(0.0, abs=0.01)
    assert result["half_width_pp"] >= 0.0


def test_utterance_id_groups_by_the_first_three_segments():
    assert spbr.utterance_id("slurp:train:s1:0") == "slurp:train:s1"
    assert spbr.utterance_id("slurp:train:s1:1") == "slurp:train:s1"
    assert spbr.utterance_id("slurp:train:s2:0") == "slurp:train:s2"


def test_utterance_level_read_clusters_multiple_rows_of_one_utterance():
    # Two rows of the SAME utterance ("s1"), one promoted and one not: averaged to 0.5 before
    # bootstrapping, unlike the row-level read which would see two independent 1.0/0.0 rows.
    rows = [
        _row("slurp:train:s1:0", {"B": ("gold", "other"), "A": ("other", "gold")}),
        _row("slurp:train:s1:1", {"B": ("other", "gold"), "A": ("other", "gold")}),
        _row("slurp:train:s2:0", {"B": ("other", "gold"), "A": ("other", "gold")}),
    ]
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.utterance_level_top1_read(rows, gold, branch_id="B", against="A")
    assert result["clustering"] == "utterance"
    assert result["n"] == 2  # two distinct utterances, not three rows


def test_assert_a_reproduces_ledger_counts_passes_within_tolerance():
    # 60 rank-1, 30 rank-2, 10 rank-3 out of 100 -> 60/30/10 %.
    rows = []
    for index in range(100):
        if index < 60:
            candidates = ("gold", "x", "y")
        elif index < 90:
            candidates = ("x", "gold", "y")
        else:
            candidates = ("x", "y", "gold")
        rows.append(_row(f"s{index}", {"A": candidates}))
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.assert_a_reproduces_ledger_counts(
        rows, gold, expected_rank1_pct=60.0, expected_rank2_pct=30.0, expected_rank3_pct=10.0,
    )
    assert result["total"] == 100
    assert result["observed_pct"][1] == pytest.approx(60.0)


def test_assert_a_reproduces_ledger_counts_refuses_a_drifted_a():
    rows = [_row(f"s{i}", {"A": ("x", "y", "gold")}) for i in range(50)]  # all rank 3
    gold = {row["sample_id"]: "gold" for row in rows}
    with pytest.raises(spbr.PerceptionBranchReadError, match="disagrees with the node ledger"):
        spbr.assert_a_reproduces_ledger_counts(
            rows, gold, expected_rank1_pct=97.57, expected_rank2_pct=26.98, expected_rank3_pct=12.0,
        )


def test_assert_a_reproduces_ledger_counts_refuses_with_no_gold_rows():
    with pytest.raises(spbr.PerceptionBranchReadError, match="no row carried a gold label"):
        spbr.assert_a_reproduces_ledger_counts(
            [], {}, expected_rank1_pct=1.0, expected_rank2_pct=1.0, expected_rank3_pct=1.0,
        )


# ---------------------------------------------------------------------------
# RECIPE MODE (psv_read.sh driver), on a FAKE sealed level-2 run. The recipes are the REAL
# registered ones (P-SV-1's seal-only recipe, P-SV-2's); every sealed byte, gold label, column
# score and paired-read output here is synthetic and written under tmp_path. The two external
# steps (the official column scorer and stage3_paired_read.py) are replaced at the module's own
# subprocess seam; the governed TRAIN gold loader is replaced at its own seam.
# ---------------------------------------------------------------------------

import hashlib  # noqa: E402
import json  # noqa: E402

PSV1_RECIPE = _REPO / "docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/analysis-recipe-v1.json"
PSV2_RECIPE = _REPO / "docs/readiness/2026-09-29-slurp-stage3-psv2-fold-b-v1/analysis-recipe-v1.json"
SCORER = "slurp-slu-official-train"
SPLIT_HASH = "e" * 64
N_ROWS = 24


def _sid(i: int) -> str:
    return f"slurp:train:fake{i // 2:03d}:{i % 2}"


def _gold(i: int) -> str:
    return f"intent_{i % 4}"


def _collapse(values):
    return list(dict.fromkeys(values))


def _item(sid, index, branch_id, raw, *, status="ok", delivering=False, presentation=None,
          skip=None, min_candidates=None):
    listed = [] if status in ("empty", "malformed") else _collapse(raw)
    if status == "ok" and len(listed) != len(raw):
        status = "duplicates-collapsed"
    return {
        "branch_index": index, "branch_id": branch_id, "deliver": delivering,
        "candidate_intent_ids": listed,
        "candidate_intent_ids_raw_count": len(raw), "note_parse_status": status,
        "presentation_id": presentation,
        "contrast_block_sha256": ("c" * 64 if presentation and not skip else None),
        "presentation_skip_reason": skip, "min_candidates": min_candidates,
        "min_candidates_met": (len(listed) >= min_candidates if min_candidates else None),
        "contact_id": f"perception-{branch_id}-{sid}",
        "solver_contact_id": f"solver-{branch_id}-{sid}",
        "solver_response_text_sha256": hashlib.sha256(f"{branch_id}{sid}".encode()).hexdigest(),
    }


def _fake_lists(i: int):
    """(A raw list, B raw list, T raw list, B status, T status, B skip) for row i."""

    gold, other = _gold(i), f"intent_{(i + 1) % 4}"
    a = [gold, other] if i % 3 else [other, gold]
    if i == 1:
        a = [gold, gold, other]  # duplicates-collapsed on the delivering note
    b, b_status, b_skip = [gold, other], "ok", None
    if i == 2:
        b, b_status = [], "empty"
    if i == 3:
        b_skip = "insufficient-pool-support"
    t, t_status = list(a), "ok"
    if i == 5:
        t, t_status = [], "malformed"
    return a, b, t, b_status, t_status, b_skip


def _build_run(tmp_path: Path, recipe_path: Path, *, seal_only: bool, presentation: bool,
               min_candidates: int | None = None):
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    run = recipe["arms"]["arm"]["run_id"]
    attempt = recipe["arms"]["arm"]["attempt_id"]
    treatment = recipe["arms"]["arm"]["branch"]
    order = (treatment, "t-twin", "a-agree")
    data_root = tmp_path / "data"
    run_dir = data_root / "runs" / run / attempt
    run_dir.mkdir(parents=True)
    rows, ledger_results = [], []
    for i in range(N_ROWS):
        sid = _sid(i)
        a, b, t, b_status, t_status, b_skip = _fake_lists(i)
        items = [
            _item(sid, 0, treatment, b, status=b_status,
                  presentation="top2-contrast-v1" if presentation else None,
                  skip=b_skip if presentation else None, min_candidates=min_candidates),
            _item(sid, 1, "t-twin", t, status=t_status),
            _item(sid, 2, "a-agree", a, delivering=True),
        ]
        rows.append({"sample_id": sid, "native_episode_receipt": {"perception_branches": {
            "schema": "saea-perception-branch-arms-v2", "phase_id": "perception", "level": 2,
            "branch_count": 3, "delivered_branch_id": "a-agree", "branches": items}}})
        ledger_results.append({"sample_id": sid, "agent_states": [{
            "state_kind": "phase:perception",
            "content": json.dumps({"candidates": [{"intent_id": x} for x in a]})}]})
    outputs = run_dir / f"{run}.outputs.jsonl"
    outputs.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    manifest = {
        "status": "COMPLETED", "run_id": run,
        "outputs": {"sha256": hashlib.sha256(outputs.read_bytes()).hexdigest()},
        "split": {"count": N_ROWS, "identity_hash": SPLIT_HASH}, "cost": {"calls_used": 0},
    }
    phases = {"phases": [{"results": ledger_results}]}
    if seal_only:
        predecessor = attempt.removesuffix("-seal-only")
        manifest["predecessor_attempt"] = {
            "attempt_id": predecessor,
            "trace_sha256": spbr.RecipePlan.load(recipe_path).predecessor_trace_sha256,
        }
        pred_dir = data_root / "runs" / run / predecessor
        pred_dir.mkdir(parents=True)
        (pred_dir / f"{run}.run-manifest.json").write_text(
            json.dumps({"cost": {"calls_used": 10 * N_ROWS}}), encoding="utf-8")
        (pred_dir / f"{run}.phases.json").write_text(json.dumps(phases), encoding="utf-8")
        # the seal-only attempt's own phases document is a narrowed replay (no agent states)
        (run_dir / f"{run}.phases.json").write_text(
            json.dumps({"seal_only_replay": True, "phases": []}), encoding="utf-8")
    else:
        manifest["cost"] = {"calls_used": 10 * N_ROWS}
        (run_dir / f"{run}.phases.json").write_text(json.dumps(phases), encoding="utf-8")
    (run_dir / f"{run}.run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    roster_rel = "roster.json"
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / roster_rel).write_text(json.dumps({
        "split_identity_hash": SPLIT_HASH, "split_role": "discovery",
        "items": [{"sample_id": _sid(i), "utterance_id": _sid(i).rsplit(":", 1)[0],
                   "stratum": "s"} for i in range(N_ROWS)]}), encoding="utf-8")
    return {"run": run, "attempt": attempt, "order": order, "treatment": treatment,
            "data_root": data_root, "run_dir": run_dir, "repo_root": repo_root,
            "roster": roster_rel, "recipe": recipe_path}


def _correct(branch_id: str, i: int) -> bool:
    if branch_id in ("a-agree", "t-twin"):
        return i % 3 != 0
    return i != 2


class _FakeExternal:
    """The two external steps behind ``spbr._run_subprocess``: the column scorer writes a
    complete score summary and three synthetic per-sample column scores; the paired read writes
    a ``score-contrasts.json`` carrying the numbers the test assigned to its right column."""

    def __init__(self, fake, numbers):
        self.fake, self.numbers, self.calls = fake, numbers, []

    @staticmethod
    def _opt(argv, name):
        return argv[argv.index(name) + 1]

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        if argv[2].endswith("stage3_rollout_score.py"):
            column_dir = Path(self._opt(argv, "--analysis-root"))
            column_dir.mkdir(parents=True, exist_ok=True)
            branches = {}
            for branch_id in self.fake["order"]:
                per_sample = [{"sample_id": _sid(i), "scenario_action_exact": _correct(branch_id, i),
                               "slu_f1_word_tp": 1, "slu_f1_char_tp": 1,
                               "slu_f1_word_fp": 0 if _correct(branch_id, i) else 1,
                               "slu_f1_char_fp": 0, "slu_f1_word_fn": 0, "slu_f1_char_fn": 0}
                              for i in range(N_ROWS)]
                path = column_dir / f"arm-{branch_id}-{SCORER}-scores.json"
                path.write_text(json.dumps({SCORER: {"per_sample": per_sample}}), encoding="utf-8")
                branches[branch_id] = {"copy_sha256": "1" * 64, "scores_sha256": "2" * 64}
            (column_dir / "score-summary.json").write_text(json.dumps({
                "schema": spbr.COLUMN_SCORE_SCHEMA, "stage": "score", "scorer_id": SCORER,
                "source": {"attempt_id": self._opt(argv, "--attempt")},
                "branch_order": list(self.fake["order"]), "branches": branches}), encoding="utf-8")
            return 0
        assert argv[2].endswith("stage3_paired_read.py")
        right = self._opt(argv, "--right-column")
        intent, intent_ci, slu, slu_ci = self.numbers[right]

        def block(delta, ci):
            return {"left_pct": 50.0, "right_pct": 50.0 + delta, "delta_pp": delta,
                    "saves": 3, "harms": 1,
                    "cluster_bootstrap": {"ci95_pp": list(ci),
                                          "ci95_half_width_pp": (ci[1] - ci[0]) / 2}}

        out = Path(self._opt(argv, "--analysis-root"))
        (out / "score-contrasts.json").write_text(json.dumps({
            "n_rows": N_ROWS,
            "per_row": {"scenario_action_exact": block(intent, intent_ci),
                        "slu_f1_f1": block(slu, slu_ci)},
            "pooled_micro": {"slu_f1_micro": block(slu, slu_ci)}}), encoding="utf-8")
        return 0


TWIN_NUMBERS = (0.1, (-0.5, 0.7), 0.2, (-0.8, 1.2))  # intent bar 0.7, SLU bar 1.2
BRANCH_CASES = {
    "NOMINATED": (2.0, (0.5, 3.5), 0.1, (-1.0, 1.2)),
    "BRANCH-LOCAL HARM": (-2.0, (-3.5, -0.5), -0.3, (-1.5, 0.9)),
    "NOT NOMINATED": (0.5, (-0.5, 1.5), 0.1, (-1.0, 1.2)),
    "NOT NOMINATED (guard)": (2.0, (0.5, 3.5), -1.5, (-2.5, -0.5)),
}


def _gold_seam(monkeypatch):
    gold = {_sid(i): _gold(i) for i in range(N_ROWS)}
    monkeypatch.setattr(spbr, "load_train_gold_intents",
                        lambda lock, data_root, ids, workers=None: {s: gold[s] for s in ids})


@pytest.fixture
def psv1_fake(tmp_path, monkeypatch):
    fake = _build_run(tmp_path, PSV1_RECIPE, seal_only=True, presentation=True)
    _gold_seam(monkeypatch)
    return fake


def _recipe_argv(fake, analysis_root, *extra):
    return ["--recipe", str(fake["recipe"]), "--attempt", fake["attempt"], "--roster", fake["roster"],
            "--level", "2", "--analysis-root", str(analysis_root), "--data-root", str(fake["data_root"]),
            "--repo-root", str(fake["repo_root"]), "--lock", "unused.json", *extra]


def _receipt(analysis_root: Path) -> dict:
    return json.loads((analysis_root / spbr.RECEIPT_NAME).read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", sorted(BRANCH_CASES))
def test_psv1_recipe_read_end_to_end_lands_in_every_verdict(psv1_fake, tmp_path, monkeypatch, case):
    fake = psv1_fake
    external = _FakeExternal(fake, {"t-twin": TWIN_NUMBERS, fake["treatment"]: BRANCH_CASES[case]})
    monkeypatch.setattr(spbr, "_run_subprocess", external)
    analysis_root = tmp_path / "read"
    assert spbr.main(_recipe_argv(fake, analysis_root)) == 0
    receipt = _receipt(analysis_root)
    assert receipt["schema"] == "saea-perception-branch-read-v1"
    assert receipt["verdict"]["verdict"] == case.split(" (")[0]
    assert receipt["verdict"]["twin_bar_pp"] == {"intent": 0.7, "slu_f1": 1.2}
    # the registered settings reach both external steps
    score_argv, twin_argv, branch_argv = external.calls
    assert score_argv[score_argv.index("--mode") + 1] == "perception-branches"
    assert score_argv[score_argv.index("--attempt") + 1].endswith("-seal-only")
    assert score_argv[score_argv.index("--scorer-id") + 1] == SCORER
    for argv, right in ((twin_argv, "t-twin"), (branch_argv, fake["treatment"])):
        assert argv[argv.index("--left-column") + 1] == "a-agree"
        assert argv[argv.index("--right-column") + 1] == right
        assert argv[argv.index("--seed") + 1] == "20260929"
        assert argv[argv.index("--draws") + 1] == "10000"
        assert argv[argv.index("--cluster-key") + 1] == "sample_id"
        assert argv[argv.index("--split-identity-hash") + 1] == SPLIT_HASH
        assert argv[argv.index("--recipe-id") + 1] == "slurp-stage3-psv1-fold-b-sealonly-branch-analysis-v1"
    assert receipt["settings"] == {"seed": 20260929, "draws": 10000, "cluster_key": "sample_id",
                                   "scorer_id": SCORER, "level": 2, "ci_level": 0.95}


def test_psv1_recipe_read_tables_custody_and_receipt(psv1_fake, tmp_path, monkeypatch):
    fake = psv1_fake
    monkeypatch.setattr(spbr, "_run_subprocess", _FakeExternal(
        fake, {"t-twin": TWIN_NUMBERS, fake["treatment"]: BRANCH_CASES["NOMINATED"]}))
    analysis_root = tmp_path / "read"
    assert spbr.main(_recipe_argv(fake, analysis_root)) == 0
    receipt = _receipt(analysis_root)
    custody = receipt["custody"]
    assert custody["rows"] == N_ROWS
    assert custody["branch_order"] == ["b-top2contrast", "t-twin", "a-agree"]
    assert custody["branches"]["a-agree"]["note_parse_status"] == {"duplicates-collapsed": 1, "ok": N_ROWS - 1}
    assert custody["branches"]["b-top2contrast"]["note_parse_status"] == {"empty": 1, "ok": N_ROWS - 1}
    # T copies A's raw list, so it also collapses row 1's duplicate
    assert custody["branches"]["t-twin"]["note_parse_status"] == {
        "duplicates-collapsed": 1, "malformed": 1, "ok": N_ROWS - 2}
    assert custody["branches"]["b-top2contrast"]["presentation"] == {
        "rendered": N_ROWS - 1, "skipped:insufficient-pool-support": 1}
    assert custody["extra_contacts"]["per_row"] == 4.0
    assert custody["extra_contacts"]["flight_contacts"]["source"] == "predecessor-run-manifest"
    assert custody["extra_contacts"]["share_of_flight"] == pytest.approx(0.4)
    assert receipt["delivering_note_vs_ledger_parse"]["equal"] == N_ROWS
    assert receipt["delivering_note_vs_ledger_parse"]["raw_duplicate_rows"] == 1
    level1 = receipt["level1"]
    # empty (B) and malformed (T) notes are gold-absent
    assert level1["branches"]["b-top2contrast"]["rank_counts"]["absent"] == 1
    assert level1["branches"]["t-twin"]["rank_counts"]["absent"] == 1
    assert level1["branches"]["a-agree"]["rank_counts"]["absent"] == 0
    assert level1["branches"]["b-top2contrast"]["by_note_parse_status"]["empty"] == {"rows": 1, "present": 0}
    present_b = level1["contrasts"]["present:b-top2contrast-minus-a-agree"]
    assert present_b["n"] == N_ROWS
    assert present_b["delta_pp"] == pytest.approx(-100.0 / N_ROWS, abs=1e-3)
    assert "utterance_level" in present_b
    assert "ranks_internal" not in level1
    # the ledger ranks the raw list: the duplicate row's gold is still rank 1, so no disagreement
    assert level1["delivering_rank_vs_ledger_raw_rank"]["raw_rank_differs_from_collapsed_rank"] == 0
    level2 = receipt["level2"]
    assert set(level2["passes"]) == {"twin-null", "branch"}
    assert level2["scorer_contacts_this_run"] == 3
    conversion_a = level2["conversion_by_gold_rank"]["a-agree"]
    assert conversion_a["1"]["ledger_reference_pct"] == 97.57
    assert conversion_a["1"]["rows"] + conversion_a["2"]["rows"] == N_ROWS
    assert level2["rendered_rows_only"]["rows"] == N_ROWS - 1
    assert level2["rendered_rows_only"]["contrast"]["n"] == N_ROWS - 1
    assert receipt["sealed"]["attempt_id"].endswith("-seal-only")
    assert receipt["gold"]["persisted"] is False
    # hashes and numbers only: no gold label reaches the receipt
    text = (analysis_root / spbr.RECEIPT_NAME).read_text(encoding="utf-8")
    assert all(_gold(i) not in text for i in range(4))


def test_psv1_recipe_read_scoring_is_idempotent_and_rescore_forces(psv1_fake, tmp_path, monkeypatch):
    fake = psv1_fake
    numbers = {"t-twin": TWIN_NUMBERS, fake["treatment"]: BRANCH_CASES["NOMINATED"]}
    first = _FakeExternal(fake, numbers)
    monkeypatch.setattr(spbr, "_run_subprocess", first)
    assert spbr.main(_recipe_argv(fake, tmp_path / "read-1")) == 0
    second = _FakeExternal(fake, numbers)
    monkeypatch.setattr(spbr, "_run_subprocess", second)
    assert spbr.main(_recipe_argv(fake, tmp_path / "read-2")) == 0
    assert [Path(c[2]).name for c in second.calls] == ["stage3_paired_read.py"] * 2
    assert _receipt(tmp_path / "read-2")["level2"]["scorer_contacts_this_run"] == 0
    third = _FakeExternal(fake, numbers)
    monkeypatch.setattr(spbr, "_run_subprocess", third)
    assert spbr.main(_recipe_argv(fake, tmp_path / "read-3", "--rescore")) == 0
    assert Path(third.calls[0][2]).name == "stage3_rollout_score.py"


def test_psv1_recipe_read_refuses_an_existing_receipt_or_pass(psv1_fake, tmp_path, monkeypatch):
    fake = psv1_fake
    monkeypatch.setattr(spbr, "_run_subprocess", _FakeExternal(
        fake, {"t-twin": TWIN_NUMBERS, fake["treatment"]: BRANCH_CASES["NOMINATED"]}))
    analysis_root = tmp_path / "read"
    assert spbr.main(_recipe_argv(fake, analysis_root)) == 0
    assert spbr.main(_recipe_argv(fake, analysis_root)) == 3  # receipt exists
    (analysis_root / spbr.RECEIPT_NAME).unlink()
    assert spbr.main(_recipe_argv(fake, analysis_root)) == 3  # pass directories hold files


def test_psv1_recipe_read_refuses_another_attempt_or_predecessor(psv1_fake, tmp_path):
    fake = psv1_fake
    argv = _recipe_argv(fake, tmp_path / "read")
    argv[argv.index("--attempt") + 1] = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1"
    assert spbr.main(argv) == 3
    manifest_path = fake["run_dir"] / f"{fake['run']}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["predecessor_attempt"]["trace_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(spbr.PerceptionBranchReadError, match="predecessor trace"):
        spbr.SealedRun(fake["data_root"], spbr.RecipePlan.load(fake["recipe"]))


def test_psv1_recipe_read_refuses_when_a_does_not_reproduce_the_ledger_parse(psv1_fake, tmp_path, monkeypatch):
    fake = psv1_fake
    predecessor = fake["attempt"].removesuffix("-seal-only")
    phases_path = fake["data_root"] / "runs" / fake["run"] / predecessor / f"{fake['run']}.phases.json"
    phases = json.loads(phases_path.read_text(encoding="utf-8"))
    phases["phases"][0]["results"][0]["agent_states"][0]["content"] = json.dumps(
        {"candidates": [{"intent_id": "intent_other"}]})
    phases_path.write_text(json.dumps(phases), encoding="utf-8")
    monkeypatch.setattr(spbr, "load_train_gold_intents",
                        lambda *a, **k: pytest.fail("gold must not load before the ledger check"))
    assert spbr.main(_recipe_argv(fake, tmp_path / "read")) == 3


def test_psv1_dry_run_counts_and_touches_no_gold_or_scorer(psv1_fake, tmp_path, monkeypatch, capsys):
    fake = psv1_fake
    monkeypatch.setattr(spbr, "load_train_gold_intents",
                        lambda *a, **k: pytest.fail("the dry run must not load gold"))
    monkeypatch.setattr(spbr, "_run_subprocess",
                        lambda argv: pytest.fail("the dry run must not score or read"))
    monkeypatch.setattr(spbr, "resolve_level2_contacts",
                        lambda sealed, order: {"rows": len(sealed.rows), "unresolved": 0})
    assert spbr.main(_recipe_argv(fake, tmp_path / "read", "--dry-run")) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == "saea-perception-branch-read-dry-run-v1"
    assert report["custody"]["rows"] == N_ROWS
    assert report["delivering_note_vs_ledger_parse"]["equal"] == N_ROWS
    assert report["level2_contacts"] == {"rows": N_ROWS, "unresolved": 0}
    assert report["paired_read_inputs_present"][f"{fake['run']}.generation-manifest.json"] is False
    assert report["stopped_before"] == "gold, scorer and any metric"
    assert not (tmp_path / "read").exists()


def test_psv2_presence_rule_with_min_candidates(tmp_path, monkeypatch):
    fake = _build_run(tmp_path, PSV2_RECIPE, seal_only=False, presentation=False, min_candidates=3)
    _gold_seam(monkeypatch)
    monkeypatch.setattr(spbr, "_run_subprocess", _FakeExternal(
        fake, {"t-twin": TWIN_NUMBERS, fake["treatment"]: BRANCH_CASES["NOMINATED"]}))
    analysis_root = tmp_path / "read"
    assert spbr.main(_recipe_argv(fake, analysis_root)) == 0
    receipt = _receipt(analysis_root)
    assert receipt["recipe"]["rule_kind"] == "presence"
    assert receipt["custody"]["branches"]["b-list3"]["min_candidates_met"] == {"False": N_ROWS}
    assert receipt["level2"]["rendered_rows_only"]["status"] == "NOT_APPLICABLE"
    assert receipt["verdict"]["rule_kind"] == "presence"
    assert receipt["verdict"]["verdict"] == "NOT NOMINATED"  # B loses gold on one row
    assert receipt["delivering_note_vs_ledger_parse"]["phases_sha256"]


def test_decide_presence_nominates_and_declines():
    twin = {"delta_pp": 0.0, "ci95_pp": [-0.4, 0.4], "half_width_pp": 0.4}
    up = {"delta_pp": 2.0, "ci95_pp": [0.8, 3.2], "half_width_pp": 1.2}
    flat = {"delta_pp": 0.3, "ci95_pp": [-0.2, 0.8], "half_width_pp": 0.5}
    assert spbr.decide_presence(twin, up)["verdict"] == "NOMINATED"
    assert spbr.decide_presence(twin, flat)["verdict"] == "NOT NOMINATED"


def test_decide_level2_intent_clauses():
    def contrast(delta, low, high):
        return {"delta_pp": delta, "ci95_pp": [low, high], "half_width_pp": (high - low) / 2}

    twin = {"intent": contrast(0.1, -0.5, 0.7), "slu_f1": contrast(0.2, -0.8, 1.2)}
    small = {"intent": contrast(0.6, 0.1, 1.1), "slu_f1": contrast(0.0, -1.0, 1.0)}
    decided = spbr.decide_level2_intent(twin, small)  # CI above zero but point under the bar
    assert decided["verdict"] == "NOT NOMINATED"
    assert decided["nominate_clauses"]["intent_ci95_lower_above_zero"] is True
    assert decided["nominate_clauses"]["intent_point_exceeds_twin_intent_bar"] is False
    mild_harm = {"intent": contrast(-0.6, -1.1, -0.1), "slu_f1": contrast(0.0, -1.0, 1.0)}
    assert spbr.decide_level2_intent(twin, mild_harm)["verdict"] == "NOT NOMINATED"


def test_v1_receipt_of_a_pre_fix_smoke_reads_with_the_gold_absent_sentinel():
    row = {"sample_id": "s1", "native_episode_receipt": {"perception_branches": {
        "schema": "saea-perception-branch-arms-v1", "phase_id": "perception", "level": 2,
        "delivered_branch_id": "a-agree",
        "branches": [
            {"branch_id": "b-top2contrast", "candidate_intent_ids": ["unparsed"],
             "note_parse_status": "malformed"},
            {"branch_id": "t-twin", "candidate_intent_ids": ["gold", "gold", "x"]},
            {"branch_id": "a-agree", "candidate_intent_ids": ["x", "gold"]},
        ]}}}
    outcomes = spbr.level1_row_outcomes(row, "gold")
    assert outcomes["b-top2contrast"] == {"rank": None, "present": False, "top1": False}
    assert outcomes["t-twin"]["rank"] == 1
    custody = spbr.describe_branches([row], ("b-top2contrast", "t-twin", "a-agree"), "a-agree")
    assert custody["receipt_schema"] == {"saea-perception-branch-arms-v1": 1}
    assert custody["branches"]["t-twin"]["note_parse_status"] == {"ok-v1": 1}
    assert custody["branches"]["t-twin"]["candidate_list_size"] == {"2": 1}
