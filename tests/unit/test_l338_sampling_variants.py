"""Decision 338: the SAMPLING column -- branch axes ``perception_samples`` / ``solver_samples``.

Layers (model-free): 1. the parser and seed derivation; 2. the loader and the ceiling; 3. the v6 receipt.
"""

from __future__ import annotations

import copy
import hashlib

import pytest

from speech_aware_evidence_acquisition.rails import commit_policies as cp
from speech_aware_evidence_acquisition.rails import perception_merge_policies as mp
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6,
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    SAMPLING_VARIANT_KINDS,
    PerceptionBranchError,
    derive_sample_seeds,
    parse_perception_sampling_variants,
    perception_branch_ceiling,
    perception_branch_receipt,
    perception_branch_record,
    perception_samples_record,
    sampling_extra_contacts,
    solver_samples_record,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

FIT = {"slot_tokens": 24576, "completion_ceiling": 4096, "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
DECODING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
L1 = {
    "n": 5, "decoding": DECODING,
    "commit": {
        "policy": "saea-commit-first-support-v1", "min_support": 2, "similarity_threshold": 0.8,
        "n1_min": 0.2, "empty_votes_min": 3,
    },
}
L2 = {"k": 4, "decoding": DECODING, "merge_policy": "saea-perception-candidate-union-v1", "cap": 3}


def _block(*, arms=None, twin=True):
    rows = arms if arms is not None else [
        {"arm_id": "l1-support", "solver_samples": copy.deepcopy(L1)},
        {"arm_id": "l2-union", "perception_samples": copy.deepcopy(L2)},
    ]
    rows = list(rows)
    if twin:
        rows.append({"arm_id": "aa", "replicate_of": "lock"})
    rows.append({"arm_id": "lock", "deliver": True})
    return {"node": "perception", "arms": rows, "max_supplied_items": 4, "fit_estimate": dict(FIT)}


def _group(**kwargs):
    return parse_perception_sampling_variants(_block(**kwargs), phase_id="perception")


# ---------------------------------------------------------------------------
# 1. parser, seeds, refusals
# ---------------------------------------------------------------------------


def test_the_parser_builds_a_level_two_sampling_group():
    group = _group()
    assert group.level == 2 and group.is_sampling and not group.is_thinking and not group.is_template
    assert group.renders_unvaried_evidence
    assert group.branch_ids == ("l1-support", "l2-union", "aa", "lock")
    assert group.delivering_branch.perception_samples is None and group.delivering_branch.solver_samples is None
    assert group.twin_branch.solver_samples is None
    l1, l2 = group.branch("l1-support"), group.branch("l2-union")
    assert l1.solver_samples.n == 5 and l1.solver_samples.seed_offsets == (1, 2, 3, 4)
    assert l1.solver_samples.n1_min == 0.2 and l1.solver_samples.empty_votes_min == 3
    assert l2.perception_samples.k == 4 and l2.perception_samples.seed_offsets == (1, 2, 3)
    assert l2.perception_samples.merge_policy == mp.CANDIDATE_UNION_V1 and l2.perception_samples.cap == 3
    # 3 + 4 extra samples beyond the level-2 base term.
    assert sampling_extra_contacts(group) == 4 + 3
    assert l1.as_json()["solver_samples"]["commit"]["policy"] == cp.FIRST_SUPPORT_V1


def test_both_nodes_may_share_one_branch():
    both = [{"arm_id": "both", "perception_samples": copy.deepcopy(L2), "solver_samples": copy.deepcopy(L1)}]
    group = _group(arms=both)
    assert sampling_extra_contacts(group) == 3 + 4
    assert group.branch("both").perception_samples is not None and group.branch("both").solver_samples is not None


def test_seed_derivation_is_lock_seed_plus_offset_with_greedy_sample_zero():
    assert derive_sample_seeds(20260913, (1, 2, 3, 4)) == (20260913, 20260914, 20260915, 20260916, 20260917)
    custom = copy.deepcopy(L2)
    custom["seed_offsets"] = [7, 11, 13]
    axis = _group(arms=[{"arm_id": "x", "perception_samples": custom}]).branch("x").perception_samples
    assert axis.seed_offsets == (7, 11, 13)
    assert derive_sample_seeds(100, axis.seed_offsets) == (100, 107, 111, 113)
    with pytest.raises(PerceptionBranchError):
        derive_sample_seeds(-1, (1,))
    with pytest.raises(PerceptionBranchError):
        derive_sample_seeds(True, (1,))


def _mut(axis, fn):
    block = _block()
    fn(block["arms"][0 if axis == "solver" else 1][f"{axis}_samples"])
    return block


@pytest.mark.parametrize("axis, fn, message", [
    ("solver", lambda a: a["decoding"].update(presence_penalty=0.5), "sets only"),
    ("solver", lambda a: a["decoding"].update(seed=1), "request seed"),
    ("solver", lambda a: a["decoding"].update(max_tokens=10), "completion cap"),
    ("solver", lambda a: a.__setitem__("decoding", {"top_p": 0.9}), "positive temperature"),
    ("solver", lambda a: a["decoding"].update(temperature=0), "outside|positive temperature"),
    ("solver", lambda a: a["decoding"].update(top_p=0), "outside"),
    ("solver", lambda a: a.__setitem__("n", 1), "from 2 to 8"),
    ("solver", lambda a: a.__setitem__("n", 9), "from 2 to 8"),
    ("solver", lambda a: a.__setitem__("greedy_first", False), "greedy_first must be true"),
    ("solver", lambda a: a.__setitem__("seed_offsets", [1, 2, 3]), "4 distinct integers"),
    ("solver", lambda a: a.__setitem__("seed_offsets", [1, 1, 2, 3]), "distinct"),
    ("solver", lambda a: a.__setitem__("seed_offsets", [0, 1, 2, 3]), "from 1 to"),
    ("solver", lambda a: a["commit"].__setitem__("policy", "no-such-policy"), "commit.policy is invalid"),
    ("solver", lambda a: a["commit"].__setitem__("min_support", 6), "min_support"),
    ("solver", lambda a: a["commit"].__setitem__("similarity_threshold", 0), "similarity_threshold"),
    ("solver", lambda a: a["commit"].pop("empty_votes_min"), "half a gate"),
    ("solver", lambda a: a["commit"].__setitem__("n1_min", 1.5), "n1_min"),
    ("solver", lambda a: a["commit"].__setitem__("empty_votes_min", 5), "empty_votes_min"),
    ("solver", lambda a: a["commit"].__setitem__("policy", "saea-commit-plurality-support-v1"), "takes no gate"),
    ("solver", lambda a: a.update(extra=1), "must be an object"),
    ("solver", lambda a: a.pop("commit"), "must be an object"),
    ("perception", lambda a: a.__setitem__("k", 1), "from 2 to 4"),
    ("perception", lambda a: a.__setitem__("k", 5), "from 2 to 4"),
    ("perception", lambda a: a.__setitem__("merge_policy", "no-such-merge"), "merge_policy is invalid"),
    ("perception", lambda a: a.__setitem__("cap", 0), "cap"),
    ("perception", lambda a: a["decoding"].update(presence_penalty=0.1), "sets only"),
    ("perception", lambda a: a.pop("merge_policy"), "must be an object"),
])
def test_axis_refusals_by_name(axis, fn, message):
    with pytest.raises(PerceptionBranchError, match=message):
        parse_perception_sampling_variants(_mut(axis, fn), phase_id="perception")


@pytest.mark.parametrize("mutate, message", [
    (lambda b: b["arms"][0].update(thinking_policy={"solver": {"enable_thinking": False}}), "unknown keys"),
    (lambda b: b["arms"][0].update(instruction_template={"relpath": "x", "sha256": "0" * 64}), "unknown keys"),
    (lambda b: b["arms"][0].update(overrides={"k": 3}), "unknown keys"),
    (lambda b: b["arms"][0].update(decoding={"temperature": 0.5}), "unknown keys"),
    (lambda b: b["arms"][0].pop("solver_samples"), "must declare perception_samples"),
    (lambda b: b["arms"][-1].update(solver_samples=copy.deepcopy(L1)), "no sampling axis"),
    (lambda b: b["arms"][-2].update(perception_samples=copy.deepcopy(L2)), "no sampling axis"),
    (lambda b: b["arms"].__setitem__(1, {"arm_id": "dup", "solver_samples": copy.deepcopy(b["arms"][0]["solver_samples"])}), "same axes"),
    (lambda b: b.__setitem__("arms", [b["arms"][-1], *b["arms"][:-1]]), "LAST arm"),
    (lambda b: b["arms"][1].__setitem__("arm_id", "l1-support"), "distinct"),
    (lambda b: b.__setitem__("node", "solver"), "'perception' role"),
    (lambda b: b["arms"][-2].__setitem__("replicate_of", "l1-support"), "not the delivering arm"),
    (lambda b: b.update(extra=1), "exactly"),
])
def test_group_refusals_by_name(mutate, message):
    block = _block()
    mutate(block)
    with pytest.raises(PerceptionBranchError, match=message):
        parse_perception_sampling_variants(block, phase_id="perception")


def test_the_twin_is_required_and_the_candidate_count_is_bounded():
    with pytest.raises(PerceptionBranchError, match="exactly one twin"):
        _group(twin=False)
    many = [
        {"arm_id": f"a{i}", "solver_samples": {**copy.deepcopy(L1), "n": 2 + (i % 7), "decoding": {"temperature": 0.1 * (i + 1)}}}
        for i in range(7)
    ]
    with pytest.raises(PerceptionBranchError, match="between 1 and 6"):
        _group(arms=many)


def test_a_fit_overrun_is_refused():
    block = _block()
    block["fit_estimate"]["base_prompt_tokens"] = 23000
    with pytest.raises(PerceptionBranchError, match="exceeds"):
        parse_perception_sampling_variants(block, phase_id="perception")


def test_kind_names_mirror_the_effect_floor_gate():
    import stage3_effect_floor_check as gate

    assert tuple(SAMPLING_VARIANT_KINDS) == gate.SAMPLING_VARIANT_KINDS
    assert set(SAMPLING_VARIANT_KINDS) <= set(gate.VARIANT_KINDS)


# ---------------------------------------------------------------------------
# 2. the loader and the ceiling
# ---------------------------------------------------------------------------


def _values(block=None, *, carrier="slurp"):
    from test_review_off_capacity import values

    v = copy.deepcopy(values(False))
    v["policy"] = "phase-native-module-v1-c10"
    v["phase_material"] = {"perception": {"instruction_template": "probes/slurp_native_role_perception_v2.txt"}}
    v["native_episode"]["roles"]["perception"]["sampling_variants"] = block if block is not None else _block()
    v["carrier_lock_key"] = carrier
    return v


def _program(ceiling):
    from test_native_episode_config import program

    return program(ceiling=ceiling)


def test_the_loader_parses_the_group_and_adds_the_sampling_contacts_to_the_ceiling():
    group = _group()
    base = perception_branch_ceiling(base_ceiling=2, branch_count=group.branch_count, level=2)
    ceiling = base + sampling_extra_contacts(group)
    config = load_native_episode_config(_values(), _program(ceiling))
    assert config.max_contacts == ceiling
    assert config.perception_branch_group.is_sampling and config.supply_variant_group is None
    with pytest.raises(ValueError, match="program contact ceiling must equal"):
        load_native_episode_config(_values(), _program(base))


def test_the_loader_refuses_by_name():
    # cap must equal the Solver's own max_candidates (3)
    wrong = _block()
    wrong["arms"][1]["perception_samples"]["cap"] = 4
    with pytest.raises(ValueError, match="candidate_supply.max_candidates"):
        load_native_episode_config(_values(wrong), _program(20))
    with pytest.raises(ValueError, match="candidate_supply.max_candidates"):
        load_native_episode_config(_values(carrier=None) if False else _values(carrier="not-a-carrier"), _program(20))
    bad = _block()
    bad["arms"][0]["solver_samples"]["n"] = 1
    with pytest.raises(ValueError, match="sampling_variants is invalid"):
        load_native_episode_config(_values(bad), _program(20))
    for other in ("branches", "template_variants", "thinking_variants", "decoding_variants", "supply_variants"):
        v = _values()
        v["native_episode"]["roles"]["perception"][other] = {"x": 1}
        with pytest.raises(ValueError):
            load_native_episode_config(v, _program(20))
    # a Solver row may not declare the key
    v = _values()
    v["native_episode"]["roles"]["solver"]["sampling_variants"] = _block()
    with pytest.raises(ValueError):
        load_native_episode_config(v, _program(20))


def test_the_v4g_refusal_stays_scoped_to_the_role_wide_grouped_visit():
    # The delivering branch carries no sampling axis, so a deliver_normaliser is not refused by this column; the existing
    # refusal still names ``roles.solver.samples >= 2`` only.
    group = _group()
    assert group.delivering_branch.solver_samples is None and group.delivering_branch.perception_samples is None
    assert all(not b.deliver for b in group.branches if b.solver_samples is not None)


# ---------------------------------------------------------------------------
# 3. the v6 receipt
# ---------------------------------------------------------------------------

LOCK_SEED = 20260913


def _hash(label):
    return hashlib.sha256(label.encode()).hexdigest()


def _perception_samples(axis, branch_id, lists):
    samples = []
    for i, ids in enumerate(lists):
        samples.append({
            "contact_id": f"{branch_id}-p{i}", "request_sha256": _hash(f"rq{branch_id}{i}"),
            "response_text_sha256": _hash(f"rs{branch_id}{i}"), "note_parse_status": "ok" if ids else "empty",
            "candidate_intent_ids": list(ids),
        })
    outcome = mp.merge_candidate_union_v1(lists, cap=axis.cap)
    return perception_samples_record(axis, lock_seed=LOCK_SEED, samples=samples, outcome=outcome)


def _solver_samples(axis, branch_id):
    def ans(*e):
        return cp.ParsedSlurpAnswer("alarm", "set", tuple(SlotEntity(t, f) for t, f in e))

    answers = [ans(("time", "7 am")), ans(("time", "7 am")), ans(), ans(), ans()]
    votes = [cp.SolverSampleVote(i, a) for i, a in enumerate(answers)]
    outcome = cp.commit_first_support_v1(
        votes, min_support=axis.min_support, similarity_threshold=axis.similarity_threshold,
        n1=0.5, n1_min=axis.n1_min, empty_votes_min=axis.empty_votes_min,
    )
    samples = [
        {"contact_id": f"{branch_id}-s{i}", "request_sha256": _hash(f"srq{i}"),
         "response_text_sha256": _hash(f"srs{i}"), "parse_status": "ok"}
        for i in range(axis.n)
    ]
    return solver_samples_record(axis, lock_seed=LOCK_SEED, samples=samples, outcome=outcome)


def _rows(group, *, mutate=None):
    rows = []
    for index, branch in enumerate(group.branches):
        digest = _hash(f"note-{index}")
        sampling = None
        if branch.is_b:
            sampling = {
                "perception_samples": None if branch.perception_samples is None else _perception_samples(
                    branch.perception_samples, branch.branch_id, [["a", "b"], ["a", "c"], ["c", "d"], ["a"]],
                ),
                "solver_samples": None if branch.solver_samples is None else _solver_samples(
                    branch.solver_samples, branch.branch_id,
                ),
            }
            if mutate is not None:
                sampling = mutate(sampling)
        rows.append(perception_branch_record(
            branch=branch, branch_index=index, contact_id=f"c{index}", request_sha256=digest,
            response_text_sha256=digest, note_sha256=digest, note_parse_status="malformed",
            candidate_intent_ids=(), supplied_value_ids=(), solver_contact_id=f"s{index}",
            solver_request_sha256=digest, solver_response_text_sha256=digest, candidate_supply_value_ids=(),
            sampling_group=True, sampling=sampling,
        ))
    return rows


def _validate(group, block):
    validate_perception_branch_receipt(
        block, branch_ids=list(group.branch_ids), delivered_branch_id="lock", twin_branch_id="aa",
        phase_id="perception", level=2,
    )


def test_a_v6_receipt_records_streams_seeds_support_and_merge():
    group = _group()
    rows = _rows(group)
    block = perception_branch_receipt(group=group, phase_id="perception", records=rows)
    assert block["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6 == "saea-perception-branch-arms-v6"
    _validate(group, block)
    l1, l2 = rows[0]["sampling"]["solver_samples"], rows[1]["sampling"]["perception_samples"]
    assert l1["seeds"] == [LOCK_SEED + i for i in range(5)] and l1["samples"][0]["override"] is None
    assert l1["samples"][1]["override"] == DECODING and l1["samples"][3]["seed"] == LOCK_SEED + 3
    assert l1["outcome"]["gate"]["status"] == "fired" and l1["outcome"]["delivered_entity_count"] == 0
    assert l2["merged_candidate_ids"] == ["a", "b", "c"] and l2["appended_candidate_ids"] == ["c"]
    assert {r["intent_id"]: r["support"] for r in l2["support_counts"]}["a"] == 3
    assert rows[1]["sampling"]["solver_samples"] is None
    assert rows[2]["sampling"] is None and rows[3]["sampling"] is None


@pytest.mark.parametrize("edit, message", [
    (lambda s: s["solver_samples"]["samples"][1].__setitem__("seed", 5), "derived seed"),
    (lambda s: s["solver_samples"]["samples"][0].__setitem__("override", dict(DECODING)), "greedy"),
    (lambda s: s["solver_samples"].__setitem__("greedy_first", False), "greedy_first"),
    (lambda s: s["solver_samples"]["samples"].pop(), "exactly 5 samples"),
    (lambda s: s["solver_samples"]["commit"].pop("policy"), "commit must carry"),
    (lambda s: s["solver_samples"]["decoding"].update(presence_penalty=0.2), "decoding must be"),
    (lambda s: s["solver_samples"]["seeds"].__setitem__(1, 0), "lock seed followed"),
    (lambda s: s.__setitem__("solver_samples", None), "at least one sampling axis"),
    (lambda s: s.update(extra=1), "exactly"),
])
def test_a_malformed_solver_sampling_record_is_refused(edit, message):
    group = _group()

    def mutate(sampling):
        edit(sampling)
        return sampling

    with pytest.raises(PerceptionBranchError, match=message):
        _rows(group, mutate=lambda s: mutate(s) if s["solver_samples"] is not None else s)


def test_a_malformed_perception_sampling_record_is_refused_by_the_validator():
    group = _group()
    block = perception_branch_receipt(group=group, phase_id="perception", records=_rows(group))
    bad = copy.deepcopy(block)
    bad["branches"][1]["sampling"]["perception_samples"]["merged_candidate_ids"] = ["c", "a", "b"]
    with pytest.raises(ValueError, match="start with sample 0"):
        _validate(group, bad)
    bad = copy.deepcopy(block)
    bad["branches"][1]["sampling"]["perception_samples"]["merged_candidate_ids"] = ["a", "b", "c", "d"]
    with pytest.raises(ValueError, match="within the cap"):
        _validate(group, bad)
    bad = copy.deepcopy(block)
    bad["branches"][3]["sampling"] = copy.deepcopy(block["branches"][0]["sampling"])        # the delivering branch
    with pytest.raises(ValueError, match="no sampling axis"):
        _validate(group, bad)
    bad = copy.deepcopy(block)
    bad["branches"][2]["sampling"] = copy.deepcopy(block["branches"][0]["sampling"])        # the twin
    with pytest.raises(ValueError, match="no sampling axis"):
        _validate(group, bad)
    bad = copy.deepcopy(block)
    bad["branches"][0]["sampling"] = None                                                   # a candidate with no axis
    with pytest.raises(ValueError, match="sampling branch row"):
        _validate(group, bad)
    bad = copy.deepcopy(block)
    bad["branches"][0]["thinking_policy"] = {"solver": {"enable_thinking": False}}
    with pytest.raises(ValueError, match="invalid shape"):
        _validate(group, bad)


def test_the_record_refuses_a_sampling_value_that_disagrees_with_the_declared_axes():
    group = _group()
    l1 = group.branch("l1-support")
    digest = _hash("x")
    common = dict(
        branch=l1, branch_index=0, contact_id="c", request_sha256=digest, response_text_sha256=digest, note_sha256=digest,
        note_parse_status="malformed", candidate_intent_ids=(), supplied_value_ids=(),
    )
    with pytest.raises(PerceptionBranchError, match="not the sampling"):
        perception_branch_record(**common)
    rows = _rows(group)
    wrong = copy.deepcopy(rows[0]["sampling"])
    wrong["solver_samples"]["n"] = 4
    with pytest.raises(PerceptionBranchError):
        perception_branch_record(**common, sampling_group=True, sampling=wrong)
    wrong = copy.deepcopy(rows[0]["sampling"])
    wrong["solver_samples"]["commit"]["min_support"] = 3
    with pytest.raises(PerceptionBranchError, match="differs from the commit"):
        perception_branch_record(**common, sampling_group=True, sampling=wrong)


def test_older_schemas_do_not_accept_a_sampling_field_and_v6_rows_are_not_template_or_thinking():
    group = _group()
    with pytest.raises(PerceptionBranchError, match="one shape"):
        perception_branch_record(
            branch=group.branch("aa"), branch_index=2, contact_id="c", request_sha256=_hash("a"),
            response_text_sha256=_hash("a"), note_sha256=_hash("a"), note_parse_status="malformed",
            candidate_intent_ids=(), supplied_value_ids=(), sampling_group=True, thinking_group=True,
        )
    block = perception_branch_receipt(group=group, phase_id="perception", records=_rows(group))
    v5 = copy.deepcopy(block)
    v5["schema"] = "saea-perception-branch-arms-v5"
    with pytest.raises(ValueError):
        _validate(group, v5)
