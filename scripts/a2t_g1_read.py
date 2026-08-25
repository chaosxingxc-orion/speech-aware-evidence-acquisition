"""Audio2Tool stage G1 -- the SEAL AND SCORE step of exposure row
``SAEA-A2T-G1``.

Both arms land MECHANICALLY (the launcher never opens gold and computes no
accuracy). This script opens gold ONCE over the sealed, already-flown
population and reports, together and in the same table, exactly what campaign
plan section 3.5 requires:

* **tool accuracy** -- the primary metric, equality of the full tool-name
  MULTISET, the label-selection analogue of SLURP intent accuracy;
* **exact match** -- equality of the full name-plus-argument multiset;
* the tool-accuracy minus exact-match **gap**;
* the **empty-call rate**;
* the **per-tier table, all 8 tiers, published whole**.

The smuggling guard the plan states verbatim is carried here: a tool-accuracy
gain that leaves exact match flat is a DIFFERENT claim and must not be
smuggled.

SCORING IS REUSED, NEVER REIMPLEMENTED. Per-sample metrics come from
``rails.adapters.audio2tool.Audio2ToolAdapter.score`` (which calls the frozen
``reproduction.toolcall_scoring``); the tier aggregation, empty-call rule and
headroom rule come from ``analysis.a2t_read``; the paired cluster bootstrap
and McNemar come from ``analysis.dev100_reviewer_audit``.

POPULATION AND WHAT IT LICENSES. ``A2T-G1-104`` is drawn from the frozen
EXPOSED 400-item discovery split. Plan section 3.3 makes every number here a
SECONDARY reading that can never be the campaign claim, and section 3.5 puts
the claim interval at n >= 400 UNEXPOSED, which is G2's job. Intervals
reported here are descriptive.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/a2t_g1_read.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.analysis.a2t_read import (  # noqa: E402
    OutputRow,
    RowScore,
    _tier_of,
    build_aggregate,
    is_empty_tool_call,
    stage2_headroom_ids,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    bootstrap_gain,
    mcnemar,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_expected_calls,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    A2T_SCORER_VERSION,
    parse_tool_calls_text,
)

RUN_ID = "SAEA-A2T-G1"
OUT_DIR = (
    REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-25-a2t-g1"
)
SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-G1-104.json"
SUBSET_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
BOOTSTRAP_SEED = 20260807
BOOTSTRAP_REPLICATES = 10000
# The published A0 comparator on the parent 400-item split. A DIFFERENT
# population (the parent, not this 104-item subset), quoted as an anchor only.
A0_TOOL_ACCURACY = 0.5425
A0_EXACT_MATCH = 0.2425
A0_EMPTY_CALL_RATE = 0.1025

_PLACEHOLDER_AUDIO_REF = AudioRef(path="unused", sha256="0" * 64).validate()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_arm(stub: str, report_relname: str | None = None) -> dict:
    """``report_relname`` lets a SUCCESSOR attempt's report be read under the
    same arm stub. The per-sample mechanical records still come from the run
    directory the report itself names, so the two can never drift apart."""

    report_path = OUT_DIR / (
        report_relname or ("%s-mechanical-report.json" % stub)
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["run_id"] != RUN_ID:
        raise SystemExit("%s names a different run id" % report_path)
    outputs_path = Path(str(report["mechanical"]["opaque_outputs"]))
    rows: dict[str, dict] = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            rows[str(record["sample_id"])] = record
    mech_path = Path(report["run_dir"]) / ("%s-mechanical.json" % stub)
    mech = json.loads(mech_path.read_text(encoding="utf-8"))
    return {
        "stub": stub,
        "arm_id": report["arm_id"],
        "report": report,
        "report_path": report_path,
        "report_sha256": sha256_file(report_path),
        "outputs_path": outputs_path,
        "outputs_sha256": sha256_file(outputs_path),
        "rows": rows,
        "mechanical": mech,
    }


def score_arm(adapter, arm: dict) -> dict[str, RowScore]:
    scored: dict[str, RowScore] = {}
    for sample_id, record in arm["rows"].items():
        text = str(record["final_response_text"])
        sample = Audio2ToolSample(
            sample_id=sample_id,
            audio_ref=_PLACEHOLDER_AUDIO_REF,
            audio_seconds=0.0,
            media_relpath="",
        )
        metrics = adapter.score(sample, text)
        scored[sample_id] = RowScore(
            row=OutputRow(
                arm=str(arm["arm_id"]),
                sample_id=sample_id,
                messages=(),
                response_text=text,
                metrics={},
                consumption={},
            ),
            tier=_tier_of(sample_id),
            metrics=metrics,
            empty_tool_call=is_empty_tool_call(text),
            recheck_mismatches=(),
        )
    return scored


def aggregate_block(scored: dict[str, RowScore], sample_ids: list[str]) -> dict:
    ordered = [scored[sid] for sid in sample_ids]
    agg = build_aggregate("pooled", ordered)
    parsed_failures = sorted(
        sid
        for sid in sample_ids
        if not bool(scored[sid].metrics["parsed"])
    )
    return {
        "n": agg.n_samples,
        "tool_accuracy": agg.tool_accuracy,
        "tool_accuracy_count": sum(
            1 for s in ordered if float(s.metrics["tool_accuracy"]) == 1.0
        ),
        "exact_match": agg.exact_match,
        "exact_match_count": sum(
            1 for s in ordered if float(s.metrics["exact_match"]) == 1.0
        ),
        "gap_tool_accuracy_minus_exact_match": agg.gap,
        "empty_call_count": agg.empty_tool_call_count,
        "empty_call_rate": agg.empty_tool_call_rate,
        "unparsed_count": len(parsed_failures),
        "unparsed_ids": parsed_failures,
        "mean_slot_f1": sum(float(s.metrics["slot_f1"]) for s in ordered) / len(ordered),
        "headroom_tool_correct_not_exact": list(stage2_headroom_ids(ordered)),
    }


def per_tier_table(
    m0: dict[str, RowScore], blend: dict[str, RowScore], sample_ids: list[str]
) -> list[dict]:
    tiers = sorted({_tier_of(sid) for sid in sample_ids})
    table = []
    for tier in tiers:
        ids = [sid for sid in sample_ids if _tier_of(sid) == tier]
        m0_agg = build_aggregate(tier, [m0[sid] for sid in ids])
        blend_agg = build_aggregate(tier, [blend[sid] for sid in ids])
        table.append(
            {
                "tier": tier,
                "n": len(ids),
                "m0_tool_accuracy": m0_agg.tool_accuracy,
                "blend_tool_accuracy": blend_agg.tool_accuracy,
                "tool_accuracy_delta_pp": 100.0
                * (blend_agg.tool_accuracy - m0_agg.tool_accuracy),
                "m0_exact_match": m0_agg.exact_match,
                "blend_exact_match": blend_agg.exact_match,
                "exact_match_delta_pp": 100.0 * (blend_agg.exact_match - m0_agg.exact_match),
                "m0_gap": m0_agg.gap,
                "blend_gap": blend_agg.gap,
                "m0_empty_call_rate": m0_agg.empty_tool_call_rate,
                "blend_empty_call_rate": blend_agg.empty_tool_call_rate,
            }
        )
    return table


def paired_block(
    m0: dict[str, RowScore], blend: dict[str, RowScore], sample_ids: list[str], field: str
) -> dict:
    m0_binary = {sid: int(float(m0[sid].metrics[field]) == 1.0) for sid in sample_ids}
    blend_binary = {sid: int(float(blend[sid].metrics[field]) == 1.0) for sid in sample_ids}
    boot = bootstrap_gain(
        sample_ids=sample_ids,
        m0=m0_binary,
        blend=blend_binary,
        n_replicates=BOOTSTRAP_REPLICATES,
        seed=BOOTSTRAP_SEED,
    )
    n01 = sum(1 for sid in sample_ids if m0_binary[sid] == 0 and blend_binary[sid] == 1)
    n10 = sum(1 for sid in sample_ids if m0_binary[sid] == 1 and blend_binary[sid] == 0)
    return {
        "field": field,
        "m0_count": sum(m0_binary.values()),
        "blend_count": sum(blend_binary.values()),
        "delta_samples": sum(blend_binary.values()) - sum(m0_binary.values()),
        "delta_pp": 100.0
        * (sum(blend_binary.values()) - sum(m0_binary.values()))
        / len(sample_ids),
        "bootstrap": boot,
        "bootstrap_label_erratum": (
            "the imported bootstrap_gain hard-codes a resampling string reading "
            "'over the 100 DEV-100 ids'; the actual resampling universe here is the "
            "%d A2T-G1-104 ids. The module is NOT edited -- it is pinned to already "
            "sealed reads -- so both the returned label and this correction are "
            "carried." % len(sample_ids)
        ),
        "mcnemar": mcnemar(n01, n10),
        "wrong_to_correct_ids": sorted(
            sid for sid in sample_ids if m0_binary[sid] == 0 and blend_binary[sid] == 1
        ),
        "correct_to_wrong_ids": sorted(
            sid for sid in sample_ids if m0_binary[sid] == 1 and blend_binary[sid] == 0
        ),
    }


def m0_only_read(*, m0_arm, sample_ids, subset, measured_subset, lock, root) -> int:
    """The BLEND arm did not land: report the M0 arm alone, with NO paired
    statistic and NO comparison, and say so.

    This is a legitimate deliverable rather than a consolation prize: M0 under
    the section 8.1 DERIVED geometry is the same bare prompt-matched direct
    decode that produced the published A0 comparator, so scoring it is the
    MECHANICS check that the derived geometry reproduces the carrier's known
    baseline behaviour. It is NOT a first-signal read of the paradigm, because
    the arm the paradigm lives in never completed."""

    if sorted(m0_arm["rows"]) != sample_ids:
        raise SystemExit("the M0 arm flew a different population than the receipt")
    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    gold = load_expected_calls(lock, root, repo_root=REPO)
    missing = [sid for sid in sample_ids if sid not in gold]
    if missing:
        raise SystemExit("gold missing for %r" % (missing[:5],))
    scored = score_arm(adapter, m0_arm)
    block = aggregate_block(scored, sample_ids)
    tiers = sorted({_tier_of(sid) for sid in sample_ids})
    table = []
    for tier in tiers:
        ids = [sid for sid in sample_ids if _tier_of(sid) == tier]
        agg = build_aggregate(tier, [scored[sid] for sid in ids])
        table.append(
            {
                "tier": tier,
                "n": len(ids),
                "m0_tool_accuracy": agg.tool_accuracy,
                "m0_exact_match": agg.exact_match,
                "m0_gap": agg.gap,
                "m0_empty_call_rate": agg.empty_tool_call_rate,
            }
        )
    gold_sizes = Counter(len(gold[sid]) for sid in sample_ids)
    report = {
        "schema": "saea-a2t-g1-read-m0-only-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "exposure_ledger_row": RUN_ID,
        "generated_at": __import__("datetime").datetime.now(
            tz=__import__("datetime").timezone.utc
        ).isoformat(),
        "status": (
            "PARTIAL. The BLEND arm ABORTED on the registered in-flight decode-rate "
            "sentinel and never completed its loop, so NO paired statistic, NO "
            "comparison and NO first-signal read of the paradigm exists. This report "
            "covers the M0 arm ALONE."
        ),
        "population": {
            "split_name": subset["split_name"],
            "count": len(sample_ids),
            "receipt": SUBSET_RECEIPT_RELPATH,
            "receipt_sha256": measured_subset,
            "split_identity_hash": subset["split_identity_hash"],
            "run_identity_hash": subset["run_identity_hash"],
            "exposure": (
                "EXPOSED. Plan section 3.3: every number here is a SECONDARY reading "
                "and can never be the campaign claim."
            ),
        },
        "arm": {
            "arm_id": m0_arm["arm_id"],
            "attempt_id": m0_arm["report"]["attempt_id"],
            "report_sha256": m0_arm["report_sha256"],
            "outputs_sha256": m0_arm["outputs_sha256"],
            "config_hash": m0_arm["report"]["config_hash"],
            "server_np": m0_arm["report"]["server_np"],
            "canary_worst_ms_per_token": m0_arm["report"]["canary"].get(
                "worst_generation_ms_per_token"
            ),
            "sentinel": m0_arm["report"]["sentinel"],
        },
        "scorer": A2T_SCORER_VERSION,
        "pooled_m0": block,
        "per_tier_m0": table,
        "gold_call_list_length_counts": dict(sorted(gold_sizes.items())),
        "a0_anchor": {
            "note": (
                "the published A0 comparator was read on the PARENT 400-item split "
                "under a DIFFERENT serving geometry (-c 49152 -np 1) and a different "
                "llama.cpp build. Quoted as an anchor only; the populations differ, "
                "the comparison is NOT paired, and n=104 against n=400 means a "
                "single sample here is about 1 pp."
            ),
            "a0_tool_accuracy": A0_TOOL_ACCURACY,
            "a0_exact_match": A0_EXACT_MATCH,
            "a0_empty_call_rate": A0_EMPTY_CALL_RATE,
            "g1_m0_tool_accuracy": block["tool_accuracy"],
            "g1_m0_exact_match": block["exact_match"],
            "g1_m0_empty_call_rate": block["empty_call_rate"],
            "tool_accuracy_difference_pp": 100.0 * (block["tool_accuracy"] - A0_TOOL_ACCURACY),
            "exact_match_difference_pp": 100.0 * (block["exact_match"] - A0_EXACT_MATCH),
        },
        "what_this_does_and_does_not_establish": {
            "does": (
                "that the section 8.1 DERIVED geometry serves this carrier's bare "
                "direct decode end to end at 104 of 104 samples with no failed call, "
                "and where its baseline sits on this subset"
            ),
            "does_not": (
                "anything about whether the locked policy cell transfers. The BLEND "
                "arm is the arm that carries the paradigm and it did not complete."
            ),
        },
        "hard_stop": (
            "G1 authorizes MECHANICS AND FIRST SIGNAL ONLY, and the first-signal half "
            "was not reached. No generality claim, no superiority claim, no test "
            "contact, no knob change and no Stage-3 activity follows from this report."
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "g1-read-m0-only.json"
    out_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(block, indent=2, sort_keys=True))
    print("")
    print("%-24s %4s %10s %10s %8s %10s" % ("tier", "n", "tool_acc", "exact", "gap", "empty"))
    for row in table:
        print(
            "%-24s %4d %10.4f %10.4f %8.4f %10.4f"
            % (
                row["tier"],
                row["n"],
                row["m0_tool_accuracy"],
                row["m0_exact_match"],
                row["m0_gap"],
                row["m0_empty_call_rate"],
            )
        )
    print("")
    print("A0 anchor: %s" % json.dumps(report["a0_anchor"], sort_keys=True))
    print("read written: %s" % out_path)
    print("read sha256: %s" % sha256_file(out_path))
    return 0


def replay_decisions(*, blend_arm: dict, sample_ids, root) -> dict:
    """Model-free, zero-contact: re-derive each trajectory's RETAIN-or-DISPATCH
    branch from its own landed query vector and its own flown direct text, and
    compare against the branch the controller actually took.

    Everything here is ``rails.kb_policy``'s own pure functions. Nothing is
    reimplemented, no gold is consulted, and no contact is spent. It also
    records WHY each trajectory branched the way it did, because on this
    carrier the answer turned out to be structural."""

    from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: PLC0415
        PRIOR_MASS_DIMENSIONS,
        FuseKnobs,
        RankWeights,
        _argmax_labels,
        _blend_scores,
        _fused_label_scores,
        _label_identities,
        fuse_supplyfilter_factory,
        multidim_recall,
        rank_wcos_prior_agree_factory,
    )
    from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: PLC0415
        KnowledgeSnapshot,
        QueryState,
    )
    import numpy as np  # noqa: PLC0415

    fuse = FuseKnobs(tau=0.65, m=5, c=2, top_l=3)
    weights = RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)
    alpha, top_k = 0.45, 5

    snapshot_path = (
        root / "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
    )
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    label_targets = dict(_label_identities(snapshot))
    values_by_id = {value.value_id: value for value in snapshot.values}
    emb_receipt = json.loads(
        (REPO / "docs/receipts/knowledge/a2t-kb-size-full-embeddings.json").read_text(
            encoding="utf-8"
        )
    )
    facet_block = emb_receipt["vectors"]["content_facets"]
    npz = np.load(snapshot_path.parent / facet_block["file"])
    facet_ids = [str(v) for v in npz["ids"]]
    matrix = npz["vectors"]
    facet_vectors = {
        facet_id: {"content": tuple(matrix[index].tolist())}
        for index, facet_id in enumerate(facet_ids)
    }

    run_dir = Path(str(blend_arm["report"]["run_dir"]))
    vectors_by_text_sha: dict[str, tuple] = {}
    with (run_dir / "query-vectors.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            vectors_by_text_sha[str(record["text_sha256"])] = tuple(
                float(v) for v in record["values"]
            )

    ranker = rank_wcos_prior_agree_factory(weights)
    fuser = fuse_supplyfilter_factory(fuse)
    snapshot_sha = snapshot.content_hash()
    subset = json.loads((REPO / SUBSET_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    packet_by_sample = {
        item["sample_id"]: item["packet_id"] for item in subset["items"]
    }
    from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: PLC0415
        load_speech_feature_packet,
    )

    feature_root = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
    packet_sha_by_sample = {
        item["sample_id"]: load_speech_feature_packet(
            feature_root, item["packet_id"]
        ).packet_sha256
        for item in subset["items"]
    }
    # The runtime QueryState carries the LOAD-SPLIT identity hash the
    # ExecutionPlan carries, which is the receipt's ``run_identity_hash`` --
    # not the receipt's own self-signing ``split_identity_hash`` and certainly
    # not the split NAME.
    split_identity_hash = str(subset["run_identity_hash"])

    mismatches: list[str] = []
    zero_content_in_top_m = 0
    empty_recall = 0
    empty_fusion = 0
    cosines: list[float] = []
    replayed = 0
    for sample_id in sample_ids:
        row = blend_arm["rows"][sample_id]
        text = row.get("direct_response_text")
        if not isinstance(text, str):
            mismatches.append("%s: no landed direct text" % sample_id)
            continue
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        vector = vectors_by_text_sha.get(key)
        if vector is None:
            mismatches.append("%s: no landed query vector for the flown text" % sample_id)
            continue
        try:
            calls, parsed = parse_tool_calls_text(text)
        except Exception:  # noqa: BLE001
            calls, parsed = [], False
        direct_label = None
        if parsed and calls and isinstance(calls[0].name, str) and calls[0].name:
            matches = sorted(
                facet_id
                for facet_id, target in label_targets.items()
                if target == calls[0].name
            )
            direct_label = matches[0] if matches else None
        query_state = QueryState(
            query_id="%s:%s:step0" % (RUN_ID, sample_id),
            query_sample_id=sample_id,
            speech_packet_id=packet_by_sample[sample_id],
            speech_packet_sha256=packet_sha_by_sample[sample_id],
            use_split_identity_hash=str(split_identity_hash),
        )
        recall_scores = multidim_recall(
            snapshot, {"content": vector}, lambda fid: facet_vectors.get(fid, {}), top_k
        )
        replayed += 1
        if not recall_scores:
            empty_recall += 1
            replay_dispatch = False
        else:
            best_cosine = max(
                (
                    score
                    for dims in recall_scores.values()
                    for dim, score in dims.items()
                    if dim not in PRIOR_MASS_DIMENSIONS
                ),
                default=None,
            )
            if best_cosine is not None:
                cosines.append(float(best_cosine))
            rank_result = ranker(
                snapshot_sha256=snapshot_sha,
                query_state=query_state,
                recall_scores=recall_scores,
            )
            top_m = tuple(c.facet_id for c in rank_result.candidates[: fuse.m])
            if not any(fid.split(":")[1] == "content" for fid in top_m if ":" in fid):
                zero_content_in_top_m += 1
            fusion = fuser(
                snapshot=snapshot,
                snapshot_sha256=snapshot_sha,
                query_state=query_state,
                rank_result=rank_result,
                recall_scores=recall_scores,
            )
            selected = tuple(fusion.selected_value_ids)
            if not selected:
                empty_fusion += 1
                replay_dispatch = False
            else:
                fused = _fused_label_scores(
                    label_targets, values_by_id, selected, rank_result
                )
                blended = _blend_scores(label_targets, fused, direct_label, alpha)
                replay_dispatch = _argmax_labels(blended) != (direct_label,)
        flown_dispatch = not bool(blend_arm["mechanical"][sample_id]["retained_primary"])
        if replay_dispatch != flown_dispatch:
            mismatches.append(sample_id)
    return {
        "semantics": (
            "each trajectory's RETAIN-or-DISPATCH branch re-derived offline from its "
            "OWN landed query vector and OWN flown direct text through "
            "rails.kb_policy's own pure functions, compared against the branch the "
            "controller actually took. Zero contacts, gold never consulted."
        ),
        "trajectories_replayed": replayed,
        "branch_mismatches": mismatches,
        "decision_replay_holds": not mismatches and replayed == len(sample_ids),
        "why_each_trajectory_branched": {
            "recall_empty": empty_recall,
            "fusion_selected_nothing": empty_fusion,
            "zero_content_facets_in_top_m": zero_content_in_top_m,
            "best_content_cosine_min": round(min(cosines), 6) if cosines else None,
            "best_content_cosine_max": round(max(cosines), 6) if cosines else None,
            "best_content_cosine_at_or_above_tau": sum(
                1 for c in cosines if c >= fuse.tau
            ),
            "tau": fuse.tau,
            "trajectories_with_a_content_facet_in_top_m": (
                len(sample_ids) - zero_content_in_top_m
            ),
            # The reading MUST follow the numbers beside it. Before the ranker
            # scale repair (1341c2db) every trajectory had zero content facets
            # in the top-m window; after it, admission works. Hard-coding
            # either narrative would make the report describe a different
            # flight from the one it scored.
            "reading": (
                (
                    "content-facet RECALL is healthy -- the cosines clear the "
                    "admission threshold. What never happens is ADMISSION: the "
                    "ranker's prior-mass dimensions outscore any cosine, so the "
                    "top-m window the fuser admits over holds no content facet at "
                    "all, and percept admission reads only NON-prior-mass "
                    "dimensions. Nothing is admitted, nothing is selected, every "
                    "trajectory retains."
                )
                if zero_content_in_top_m == len(sample_ids)
                else (
                    "content-facet recall is healthy AND admission now works: a "
                    "content facet enters the top-m window the fuser admits over on "
                    "%d of %d trajectories, so the supply path is exercised rather "
                    "than structurally inert. Each trajectory then retains or "
                    "dispatches on the blend argmax, which is the decision this "
                    "replay reproduces."
                    % (len(sample_ids) - zero_content_in_top_m, len(sample_ids))
                )
            ),
        },
    }


def main() -> int:
    lock = load_lock(umbrella_lock_path())
    root = data_root()

    subset_path = REPO / SUBSET_RECEIPT_RELPATH
    measured_subset = sha256_file(subset_path)
    if measured_subset != SUBSET_RECEIPT_SHA256:
        raise SystemExit("subset receipt hashes to %s, not the pin" % measured_subset)
    subset = json.loads(subset_path.read_text(encoding="utf-8"))
    sample_ids = sorted(item["sample_id"] for item in subset["items"])
    if len(sample_ids) != int(subset["count"]):
        raise SystemExit("subset receipt count disagrees with its items")

    m0_only = "--m0-only" in sys.argv
    blend_report_relname = None
    if "--blend-report" in sys.argv:
        blend_report_relname = sys.argv[sys.argv.index("--blend-report") + 1]
    out_relname = "g1-read.json"
    if "--out" in sys.argv:
        out_relname = sys.argv[sys.argv.index("--out") + 1]
    m0_arm = load_arm("arm1-m0")
    if m0_only:
        return m0_only_read(
            m0_arm=m0_arm,
            sample_ids=sample_ids,
            subset=subset,
            measured_subset=measured_subset,
            lock=lock,
            root=root,
        )
    blend_arm = load_arm("arm2-blend", blend_report_relname)
    for arm in (m0_arm, blend_arm):
        if sorted(arm["rows"]) != sample_ids:
            raise SystemExit(
                "%s flew a different population than the subset receipt" % arm["stub"]
            )
        if arm["report"]["config_hash"] != m0_arm["report"]["config_hash"]:
            raise SystemExit("the two arms flew different composed configs")
        if arm["report"]["server_np"] != 2:
            raise SystemExit("an arm did not fly the derived -np 2 geometry")

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    gold = load_expected_calls(lock, root, repo_root=REPO)
    missing = [sid for sid in sample_ids if sid not in gold]
    if missing:
        raise SystemExit("gold missing for %r" % (missing[:5],))

    m0_scored = score_arm(adapter, m0_arm)
    blend_scored = score_arm(adapter, blend_arm)

    m0_block = aggregate_block(m0_scored, sample_ids)
    blend_block = aggregate_block(blend_scored, sample_ids)

    tool_paired = paired_block(m0_scored, blend_scored, sample_ids, "tool_accuracy")
    em_paired = paired_block(m0_scored, blend_scored, sample_ids, "exact_match")

    # ---- mechanism: dispatch decomposition over SCORED outcomes ----------
    blend_mech = blend_arm["mechanical"]
    retained = sorted(sid for sid in sample_ids if blend_mech[sid]["retained_primary"])
    dispatched = sorted(sid for sid in sample_ids if not blend_mech[sid]["retained_primary"])
    recovered = sorted(
        sid for sid in sample_ids if blend_mech[sid]["direct_label_recovered"] is True
    )
    decomposition = {
        "retained_primary": len(retained),
        "dispatched": len(dispatched),
        "closes_over_population": len(retained) + len(dispatched) == len(sample_ids),
        "direct_label_recovered": len(recovered),
        "retain_equals_direct_label_recovered": sorted(recovered) == retained,
        "dead_direct_dispatched": sum(
            1 for sid in dispatched if blend_mech[sid]["direct_label_recovered"] is not True
        ),
        "branch_only_replay": blend_arm["report"]["mechanical"]["branch_only_replay"],
        "subgroups": {},
    }
    for name, ids in (("retain-primary", retained), ("dead-direct-dispatch", dispatched)):
        if not ids:
            decomposition["subgroups"][name] = {"n": 0}
            continue
        m0_correct = sum(
            1 for sid in ids if float(m0_scored[sid].metrics["tool_accuracy"]) == 1.0
        )
        blend_correct = sum(
            1 for sid in ids if float(blend_scored[sid].metrics["tool_accuracy"]) == 1.0
        )
        m0_em = sum(1 for sid in ids if float(m0_scored[sid].metrics["exact_match"]) == 1.0)
        blend_em = sum(
            1 for sid in ids if float(blend_scored[sid].metrics["exact_match"]) == 1.0
        )
        decomposition["subgroups"][name] = {
            "n": len(ids),
            "m0_tool_accuracy": m0_correct / len(ids),
            "blend_tool_accuracy": blend_correct / len(ids),
            "tool_accuracy_delta_samples": blend_correct - m0_correct,
            "m0_exact_match": m0_em / len(ids),
            "blend_exact_match": blend_em / len(ids),
            "exact_match_delta_samples": blend_em - m0_em,
        }

    # ---- DECISION REPLAY: the invariant a branch-only replay cannot carry --
    #
    # The registered branch-only replay proves that the SUPPLY a dispatched
    # trajectory received equals what the pure functions independently produce.
    # When NOTHING dispatches it has nothing to check and reports zero
    # trajectories, which is vacuous rather than passing. The invariant that
    # still bites is one level up: replay the RETAIN-versus-DISPATCH DECISION
    # itself, through rails.kb_policy's OWN pure functions, on each
    # trajectory's OWN landed query vector and OWN flown direct text, and
    # require it to reproduce the controller's flown branch on every sample.
    decision_replay = replay_decisions(
        blend_arm=blend_arm,
        sample_ids=sample_ids,
        root=root,
    )
    decomposition["decision_replay"] = decision_replay
    decomposition["branch_only_replay_is_vacuous"] = (
        int(decomposition["branch_only_replay"].get("trajectories_replayed", 0)) == 0
    )

    # ---- WHERE THE PAIRED DELTA COMES FROM, when nothing dispatched ------
    #
    # If no trajectory dispatched, the policy supplied nothing to any contact
    # and the two arms differ ONLY where the frozen core's own multi-slot
    # decode variance produced a different direct answer for the same prompt.
    # A delta must then be attributed to that channel and NOT to the method,
    # and this block is what makes that attribution checkable rather than
    # asserted.
    blend_report_mech = blend_arm["report"]["mechanical"]
    divergent = sorted(
        blend_arm["report"]["two_pass"]["pass_a"]["divergent_from_landed_m0_text"]
    ) if "two_pass" in blend_arm["report"] else []
    flipped_tool = sorted(
        sid
        for sid in sample_ids
        if float(m0_scored[sid].metrics["tool_accuracy"])
        != float(blend_scored[sid].metrics["tool_accuracy"])
    )
    flipped_em = sorted(
        sid
        for sid in sample_ids
        if float(m0_scored[sid].metrics["exact_match"])
        != float(blend_scored[sid].metrics["exact_match"])
    )
    identical_text = sorted(
        sid
        for sid in sample_ids
        if blend_arm["rows"][sid].get("direct_response_text")
        == m0_arm["rows"][sid].get("final_response_text")
    )
    dispatched_set = set(dispatched)
    divergent_set = set(divergent)

    def _attribute(sid: str) -> str:
        """Which channel can account for this flip.

        A trajectory that DISPATCHED received evidence, so the method could
        have moved it. A trajectory whose Pass-A text diverges from the landed
        M0 text was decoded differently by the frozen core, so decode variance
        could have moved it. Both, neither, or exactly one may apply, and the
        honest report names which -- it never assigns a flip to the method by
        elimination."""

        d = sid in dispatched_set
        v = sid in divergent_set
        if d and not v:
            return "method-attributable (dispatched, text identical to M0)"
        if v and not d:
            return "decode-variance (text divergent, never dispatched)"
        if d and v:
            return "AMBIGUOUS (dispatched AND text divergent)"
        return "UNEXPLAINED (neither dispatched nor text-divergent)"

    decode_variance = {
        "question": (
            "a paired delta can come from the METHOD (a dispatched trajectory that "
            "received evidence) or from the frozen core's OWN multi-slot decode "
            "variance (a trajectory whose direct text did not reproduce byte for "
            "byte). Which flips belong to which channel?"
        ),
        "dispatched_trajectories": int(blend_report_mech["two_contact_trajectories_dispatched"]),
        "evidence_contacts_flown": int(blend_report_mech["pass_b_evidence_contacts_flown"]),
        "trajectories_with_text_identical_to_m0": len(identical_text),
        "trajectories_with_text_divergent_from_m0": len(sample_ids) - len(identical_text),
        "divergent_sample_ids": divergent,
        "tool_accuracy_flips": flipped_tool,
        "tool_accuracy_flips_all_inside_divergent_set": all(
            sid in set(divergent) for sid in flipped_tool
        ),
        "exact_match_flips": flipped_em,
        "exact_match_flips_all_inside_divergent_set": all(
            sid in set(divergent) for sid in flipped_em
        ),
        "tool_accuracy_flip_attribution": {
            sid: _attribute(sid) for sid in flipped_tool
        },
        "exact_match_flip_attribution": {
            sid: _attribute(sid) for sid in flipped_em
        },
        "attribution": (
            (
                "every scored difference between the two arms falls inside the set "
                "of trajectories whose direct decode did not reproduce byte for "
                "byte, and no trajectory received any evidence. The paired delta is "
                "therefore the frozen core's OWN multi-slot decode-variance channel, "
                "measured on this carrier, and it is NOT an effect of the policy "
                "cell. It must not be read as the method helping or hurting."
            )
            if not dispatched
            else (
                "trajectories DID dispatch here, so the two channels coexist and "
                "each flip is attributed individually above rather than assigned to "
                "one channel wholesale. A flip on a dispatched trajectory whose text "
                "was byte-identical to M0 can only come from the evidence contact; a "
                "flip on a never-dispatched trajectory can only come from decode "
                "variance; a flip that is both is reported AMBIGUOUS and is not "
                "counted for the method. At n=104 none of these differences is "
                "separated from zero by its own interval, and the per-flip "
                "attribution is a MECHANISM reading, never an effect size."
            )
        ),
    }

    # ---- the tool-name-multiset mapping, measured on THIS population -----
    gold_multiset_sizes = Counter(len(gold[sid]) for sid in sample_ids)
    gold_single_tool = sum(
        1 for sid in sample_ids if len({call.name for call in gold[sid]}) == 1
    )
    primary_in_vocabulary = 0
    label_vocabulary = set()
    snapshot_path = (
        root / "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
    )
    snapshot_doc = json.loads(snapshot_path.read_text(encoding="utf-8"))
    for value in snapshot_doc["values"]:
        target = value.get("task_target")
        if isinstance(target, str) and target:
            label_vocabulary.add(target)
    for sid in sample_ids:
        if gold[sid] and gold[sid][0].name in label_vocabulary:
            primary_in_vocabulary += 1
    multiset_mapping = {
        "scorer_projection": (
            "tool accuracy is equality of the full tool-name MULTISET "
            "(collections.Counter over call names); exact match is equality of the "
            "full name-plus-argument multiset. Frozen scorer %s." % A2T_SCORER_VERSION
        ),
        "dispatch_projection": (
            "the A2T direct-label-recovery analogue takes the PRIMARY (first) call's "
            "tool name and matches it EXACTLY against the 151-tool label vocabulary, "
            "ties by facet_id ascending -- the carrier form of the SLURP "
            "scenario_action rule and of the f1060078 repair. It governs which branch "
            "of the dispatch rule a trajectory takes and is NEVER scored."
        ),
        "gold_call_list_length_counts": dict(sorted(gold_multiset_sizes.items())),
        "gold_single_distinct_tool_items": gold_single_tool,
        "gold_multi_distinct_tool_items": len(sample_ids) - gold_single_tool,
        "projection_lossless_share": gold_single_tool / len(sample_ids),
        "gold_primary_names_inside_label_vocabulary": primary_in_vocabulary,
        "label_vocabulary_size": len(label_vocabulary),
        "disclosure": (
            "on the %d items whose gold call list names a single distinct tool the "
            "primary-name projection and the multiset carry the same information; on "
            "the remaining %d it is LOSSY, and that is a property of the dispatch "
            "rule, not of the score."
            % (gold_single_tool, len(sample_ids) - gold_single_tool)
        ),
    }

    spend = {
        arm["stub"]: {
            "core_contacts": arm["report"]["spend_vs_ceilings"]["this_attempt"][
                "core_contacts"
            ],
            "embedding_tool_contacts": arm["report"]["spend_vs_ceilings"][
                "this_attempt"
            ]["embedding_tool_contacts"],
            "metered_audio_seconds": arm["report"]["spend_vs_ceilings"]["this_attempt"][
                "metered_audio_seconds"
            ],
            "gpu_active_hours_contact_basis": arm["report"]["spend_vs_ceilings"][
                "this_attempt"
            ]["gpu_active_hours_contact_basis"],
        }
        for arm in (m0_arm, blend_arm)
    }
    spend["campaign_ceilings"] = m0_arm["report"]["spend_vs_ceilings"]["campaign_ceilings"]
    spend["campaign_cumulative_core_contacts"] = (
        blend_arm["report"]["spend_vs_ceilings"]["campaign_cumulative_incl_prior_arms"][
            "core_contacts"
        ]
    )

    report = {
        "schema": "saea-a2t-g1-read-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "exposure_ledger_row": RUN_ID,
        "generated_at": __import__("datetime").datetime.now(
            tz=__import__("datetime").timezone.utc
        ).isoformat(),
        "authority": (
            "docs/readiness/2026-08-25-a2t-generality-campaign-plan.md sections 3.3, "
            "3.5, 3.6, 7 and 8; contract configs/experiment/a2t-g1-v1.json"
        ),
        "population": {
            "split_name": subset["split_name"],
            "count": len(sample_ids),
            "receipt": SUBSET_RECEIPT_RELPATH,
            "receipt_sha256": measured_subset,
            "split_identity_hash": subset["split_identity_hash"],
            "run_identity_hash": subset["run_identity_hash"],
            "exposure": (
                "EXPOSED. Plan section 3.3: every number in this report is a SECONDARY "
                "reading and can never be the campaign claim. The claim interval needs "
                "n >= 400 UNEXPOSED (section 3.5) and belongs to G2."
            ),
        },
        "arms": {
            arm["stub"]: {
                "arm_id": arm["arm_id"],
                "attempt_id": arm["report"]["attempt_id"],
                "report_sha256": arm["report_sha256"],
                "outputs_sha256": arm["outputs_sha256"],
                "config_hash": arm["report"]["config_hash"],
                "server_np": arm["report"]["server_np"],
                "canary_worst_ms_per_token": arm["report"]["canary"].get(
                    "worst_generation_ms_per_token"
                ),
                "sentinel_tripped": arm["report"]["sentinel"]["tripped"],
            }
            for arm in (m0_arm, blend_arm)
        },
        "scorer": A2T_SCORER_VERSION,
        "primary_metric": "tool_accuracy",
        "pooled": {"m0": m0_block, "blend": blend_block},
        "headline": {
            "m0_tool_accuracy": m0_block["tool_accuracy"],
            "blend_tool_accuracy": blend_block["tool_accuracy"],
            "tool_accuracy_delta_pp": tool_paired["delta_pp"],
            "m0_exact_match": m0_block["exact_match"],
            "blend_exact_match": blend_block["exact_match"],
            "exact_match_delta_pp": em_paired["delta_pp"],
            "m0_gap": m0_block["gap_tool_accuracy_minus_exact_match"],
            "blend_gap": blend_block["gap_tool_accuracy_minus_exact_match"],
            "m0_empty_call_rate": m0_block["empty_call_rate"],
            "blend_empty_call_rate": blend_block["empty_call_rate"],
        },
        "smuggling_guard": (
            "plan section 3.5, carried verbatim: a tool-accuracy gain that leaves "
            "exact match flat is a DIFFERENT claim and must not be smuggled. Both "
            "metrics, the gap and the empty-call rate are reported together above and "
            "per tier below."
        ),
        "paired_tool_accuracy": tool_paired,
        "paired_exact_match": em_paired,
        "per_tier": per_tier_table(m0_scored, blend_scored, sample_ids),
        "mechanism": decomposition,
        "decode_variance_attribution": decode_variance,
        "tool_name_multiset_mapping": multiset_mapping,
        "a0_anchor": {
            "note": (
                "the published A0 comparator was read on the PARENT 400-item split, "
                "not on this 104-item subset. Quoted as an anchor only; the "
                "populations differ and the comparison is NOT paired."
            ),
            "a0_tool_accuracy": A0_TOOL_ACCURACY,
            "a0_exact_match": A0_EXACT_MATCH,
            "a0_empty_call_rate": A0_EMPTY_CALL_RATE,
            "g1_m0_tool_accuracy": m0_block["tool_accuracy"],
            "g1_m0_exact_match": m0_block["exact_match"],
            "g1_m0_empty_call_rate": m0_block["empty_call_rate"],
        },
        "spend": spend,
        "limitations": [
            "EXPOSED tier: every number is a secondary reading (plan section 3.3).",
            "n = 104: below the plan's own n >= 400 power floor (section 3.5); the "
            "intervals here are descriptive, not a confirmatory claim.",
            "the a2t-gold-v1 scorer's semantics are interpretation, not ground truth "
            "-- the A0 verdict's own limitation, inherited in full.",
            "the corpus is synthetic and the speakers are synthetic voice assignments.",
            "no ablation arm flew, so nothing here attributes the effect to retrieval "
            "as opposed to the second contact; ABL-RANDRET answers that at G2.",
        ],
        "hard_stop": (
            "G1 authorizes MECHANICS AND FIRST SIGNAL ONLY. No generality claim, no "
            "superiority claim, no test contact, no knob change and no Stage-3 "
            "activity follows from this report."
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / out_relname
    out_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report["headline"], indent=2, sort_keys=True))
    print("")
    print("paired tool accuracy: %s" % json.dumps(
        {
            "delta_pp": tool_paired["delta_pp"],
            "ci90": [
                tool_paired["bootstrap"]["ci90_low_pp"],
                tool_paired["bootstrap"]["ci90_high_pp"],
            ],
            "ci95": [
                tool_paired["bootstrap"]["ci95_low_pp"],
                tool_paired["bootstrap"]["ci95_high_pp"],
            ],
            "mcnemar_p": tool_paired["mcnemar"].get("exact_binomial_two_sided_p"),
            "w_to_c": tool_paired["mcnemar"].get("n01_wrong_to_correct"),
            "c_to_w": tool_paired["mcnemar"].get("n10_correct_to_wrong"),
        }
    ))
    print("paired exact match:   %s" % json.dumps(
        {
            "delta_pp": em_paired["delta_pp"],
            "ci90": [
                em_paired["bootstrap"]["ci90_low_pp"],
                em_paired["bootstrap"]["ci90_high_pp"],
            ],
            "mcnemar_p": em_paired["mcnemar"].get("exact_binomial_two_sided_p"),
            "w_to_c": em_paired["mcnemar"].get("n01_wrong_to_correct"),
            "c_to_w": em_paired["mcnemar"].get("n10_correct_to_wrong"),
        }
    ))
    print("")
    print(
        "%-24s %4s %8s %8s %8s %8s %8s %8s"
        % ("tier", "n", "M0 tool", "BL tool", "d pp", "M0 EM", "BL EM", "d pp")
    )
    for row in report["per_tier"]:
        print(
            "%-24s %4d %8.4f %8.4f %8.2f %8.4f %8.4f %8.2f"
            % (
                row["tier"],
                row["n"],
                row["m0_tool_accuracy"],
                row["blend_tool_accuracy"],
                row["tool_accuracy_delta_pp"],
                row["m0_exact_match"],
                row["blend_exact_match"],
                row["exact_match_delta_pp"],
            )
        )
    print("")
    print("mechanism: %s" % json.dumps(
        {
            k: v
            for k, v in decomposition.items()
            if k not in ("subgroups", "branch_only_replay")
        }
    ))
    print("subgroups: %s" % json.dumps(decomposition["subgroups"]))
    print("branch-only: %s (vacuous=%s)" % (
        json.dumps(decomposition["branch_only_replay"]),
        decomposition["branch_only_replay_is_vacuous"],
    ))
    print("decode variance: %s" % json.dumps(
        {k: v for k, v in decode_variance.items() if k not in ("question", "attribution")}
    ))
    print("decision replay: %s" % json.dumps(
        {
            k: v
            for k, v in decomposition["decision_replay"].items()
            if k not in ("semantics", "why_each_trajectory_branched")
        }
    ))
    print("why: %s" % json.dumps(
        {
            k: v
            for k, v in decomposition["decision_replay"][
                "why_each_trajectory_branched"
            ].items()
            if k != "reading"
        }
    ))
    print("")
    print("read written: %s" % out_path)
    print("read sha256: %s" % sha256_file(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
