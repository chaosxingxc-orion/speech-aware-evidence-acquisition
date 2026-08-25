"""MODEL-FREE, ZERO-CONTACT **POST-FIX** DISPATCH PROJECTION for A2T stage G1.

Row ``SAEA-SN-MF-A2T-G1-DISPATCH-PROJECTION-POSTFIX`` (model-free-check).

WHY THIS EXISTS, AND WHY IT IS NOT THE PREDECESSOR RE-RUN.
``scripts/a2t_g1_dispatch_projection.py`` sized the THIRD BLEND attempt. It ran
against the ranker as it stood then, projected **0** dispatches, and the flight
matched it exactly -- because the ranker carried the scale defect the owner
ruling of 2026-08-25 (``docs/checks/speech-aware-evidence-acquisition/
2026-08-25-a2t-g1/README.md`` section "CORRECTION") named as an IMPLEMENTATION
DEFECT rather than a finding. The repair landed at commit ``1341c2db``:
``rails.kb_policy._dimension_scales`` divides every ranker dimension by
``max(1.0, sup_d)`` before the weights apply, which is an exact identity
wherever a dimension is already inside its own bound (proved on the sealed
SLURP DEV-1000 store over 674 replayed trajectories, bit-for-bit) and which on
Audio2Tool moves the post-repair prior ceiling ``w_prior * 1.0 = 0.300``
strictly below the admissible floor ``w_cos * tau = 0.325``.

So the fourth BLEND attempt is expected to DISPATCH where the third dispatched
zero, and a dispatch is exactly one Pass-B core contact. The campaign cell now
BINDS HARD: 303 of 400 core contacts are durable, so **97 remain**. This pass
computes the exact count the attempt must be sized against, at zero spend, and
it never raises the campaign cell.

WHAT MAKES THIS AN EXACT COUNT RATHER THAN A PROJECTION.
The predecessor carried one stated limitation: Pass A RE-FLEW the direct decode,
and the program's multi-slot decode-variance channel means a minority of flown
texts do not reproduce byte for byte, so a projection over the M0 texts could
not predict the flown count. **Attempt 4 does not re-fly Pass A.** Attempt 3's
104 Pass-A texts are landed and hash-pinned, and attempt 3 itself proved the
replay admission works (104 of 104 messages digests matched). Attempt 4 replays
them, so the query text of every trajectory is FIXED BEFORE TAKEOFF and this
pass reads exactly those texts. Under a deterministic policy over fixed texts
and fixed vectors the dispatch set is therefore not estimated -- it is the set
the flight will take, and the attempt ceiling is sized on it with a stated
margin for the residual (a Pass-B evidence contact that must be re-sent, or a
trajectory whose evidence contact fails and is retried once).

INPUTS, ALL ALREADY LANDED, NOTHING NEW COMPUTED FROM THE MODEL.
* query texts   -- attempt 3's ``pass-a-direct-outputs.jsonl``, the file pinned
  at ``73e28511...aadc9c`` in that attempt's own mechanical report, every row
  additionally re-verified against its OWN ``direct_response_sha256``;
* query vectors -- attempt 3's durable ``query-vectors.jsonl`` (and its bridge
  table), keyed by text sha256, covering every Pass-A text by construction
  (that attempt's bridge asserted ``coverage_complete``);
* policy        -- the FROZEN v1 cell, byte-identical, through
  ``rails.kb_policy``'s OWN pure functions, never a reimplementation.

ZERO model contacts, ZERO embedding tool contacts, gold never opened.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/a2t_g1_dispatch_projection_postfix.py
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
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

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails import kb_policy as _kb_policy  # noqa: E402
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    FuseKnobs,
    PRIOR_MASS_DIMENSIONS,
    RankWeights,
    _argmax_labels,
    _blend_scores,
    _fused_label_scores,
    _label_identities,
    fuse_supplyfilter_factory,
    multidim_recall,
    rank_wcos_prior_agree_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
    QueryState,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    parse_tool_calls_text,
)

RUN_ID = "SAEA-A2T-G1"
PROJECTION_RUN_ID = "SAEA-SN-MF-A2T-G1-DISPATCH-PROJECTION-POSTFIX"
SPLIT_ID = "A2T-G1-104"
SPLIT_COUNT = 104
SPLIT_IDENTITY_HASH = (
    "f5a030189cf80dcbc52899e2fa5f819bac03874f2ad3f9645fdc60c432a9bf3a"
)
SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-G1-104.json"
SUBSET_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
SNAPSHOT_RELPATH = "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
SNAPSHOT_SHA256 = "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
EMBEDDINGS_RECEIPT_RELPATH = "docs/receipts/knowledge/a2t-kb-size-full-embeddings.json"
LABEL_VOCABULARY_SIZE = 151
EMBEDDER_DIM = 1024
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")

FROZEN_ALPHA = 0.45
FROZEN_TAU = 0.65
FROZEN_TOP_K = 5
FROZEN_FUSE = FuseKnobs(tau=FROZEN_TAU, m=5, c=2, top_l=3)
FROZEN_WEIGHTS = RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)

# The THIRD attempt, whose Pass-A texts attempt 4 replays.
ATTEMPT3_ID = "attempt-20260825T125051Z-a2tg1blend"
ATTEMPT3_REPORT_RELNAME = "arm2-blend-mechanical-report-attempt3.json"
ATTEMPT3_REPORT_SHA256 = (
    "56bf0a7592d2b595da86dab84ad7c0ae8246d1afc150f4cb695f2c9efcc0b520"
)
ATTEMPT3_PASS_A_OUTPUTS_SHA256 = (
    "73e28511f419cd67b1721d829438f8c102e725e01243c9a9f000e00d92aadc9c"
)
ATTEMPT3_BRIDGE_VECTORS_SHA256 = (
    "be63447edd56b97bdc3afa711cda9d40f8dd22b126f2f37bdbee1475b9d088a9"
)

# The repair whose effect this pass measures.
RANKER_FIX_COMMIT = "1341c2db"

OUT_CHECK_DIR = (
    REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-25-a2t-g1"
)

# --- the attempt-4 ceiling arithmetic, stated here so the artifact carries it -
CAMPAIGN_CORE_CELL = 400
CAMPAIGN_AUDIO_CELL = 2000.0
CAMPAIGN_TOOL_CELL = 200
PRIOR_DURABLE_CORE = 303
PRIOR_DURABLE_AUDIO = 1532.409
PRIOR_DURABLE_TOOL = 136
CANARY_CONTACTS = 2
RESEND_CONTACTS = 1
CEILING_MARGIN = 8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def a2t_primary_tool_normalizer(response_text, label_targets):
    """The launcher's own A2T carrier analogue, byte-for-byte."""

    if not isinstance(response_text, str):
        return None
    try:
        calls, parsed = parse_tool_calls_text(response_text)
    except Exception:  # noqa: BLE001
        return None
    if not parsed or not calls:
        return None
    identity = calls[0].name
    if not isinstance(identity, str) or not identity:
        return None
    matches = sorted(
        facet_id for facet_id, target in label_targets.items() if target == identity
    )
    return matches[0] if matches else None


def main() -> int:
    root = data_root()
    load_lock(umbrella_lock_path())

    # ---- the repair must be LIVE, asserted rather than assumed -----------
    if not hasattr(_kb_policy, "_dimension_scales"):
        raise SystemExit(
            "rails.kb_policy carries no _dimension_scales: this pass exists to "
            "measure the landed repair %s and refuses to run against the "
            "pre-repair ranker" % RANKER_FIX_COMMIT
        )
    kb_policy_sha = sha256_file(
        REPO / "src" / "speech_aware_evidence_acquisition" / "rails" / "kb_policy.py"
    )

    # ---- subset receipt (the population this projection is about) --------
    receipt_path = REPO / SUBSET_RECEIPT_RELPATH
    measured_receipt = sha256_file(receipt_path)
    if measured_receipt != SUBSET_RECEIPT_SHA256:
        raise SystemExit("subset receipt hashes to %s, not the pin" % measured_receipt)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt["split_name"] != SPLIT_ID or receipt["count"] != SPLIT_COUNT:
        raise SystemExit("subset receipt identity drifted")
    audio_by_sample = {
        item["sample_id"]: float(item["audio_seconds"]) for item in receipt["items"]
    }
    packet_by_sample: dict[str, dict[str, str]] = {}
    for item in receipt["items"]:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        if packet.audio_sha256 != item["audio_sha256"]:
            raise SystemExit(
                "packet %s carries a different audio sha256" % item["packet_id"]
            )
        packet_by_sample[item["sample_id"]] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }

    # ---- knowledge snapshot + content-facet vectors ----------------------
    snapshot_path = root / SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise SystemExit("A2T knowledge snapshot content hash mismatch")
    label_targets = dict(_label_identities(snapshot))
    if len(label_targets) != LABEL_VOCABULARY_SIZE:
        raise SystemExit("A2T label vocabulary size drifted")
    values_by_id = {value.value_id: value for value in snapshot.values}

    emb_receipt = json.loads(
        (REPO / EMBEDDINGS_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    facet_block = emb_receipt["vectors"]["content_facets"]
    facet_npz_path = snapshot_path.parent / facet_block["file"]
    measured_npz = sha256_file(facet_npz_path)
    if measured_npz != facet_block["sha256"]:
        raise SystemExit("content-facet npz hash mismatch vs the landed receipt")
    npz = np.load(facet_npz_path)
    facet_ids = [str(v) for v in npz["ids"]]
    facet_matrix = npz["vectors"]
    if facet_matrix.shape != (len(facet_ids), EMBEDDER_DIM):
        raise SystemExit("unexpected facet vector shape %r" % (facet_matrix.shape,))
    facet_vector_table = {
        facet_id: {"content": tuple(facet_matrix[index].tolist())}
        for index, facet_id in enumerate(facet_ids)
    }

    # ---- attempt 3's LANDED PASS-A texts, the exact texts attempt 4 replays
    report_path = OUT_CHECK_DIR / ATTEMPT3_REPORT_RELNAME
    measured_report = sha256_file(report_path)
    if measured_report != ATTEMPT3_REPORT_SHA256:
        raise SystemExit(
            "the landed attempt-3 report hashes to %s, not the pin" % measured_report
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("arm_id") != "BLEND" or report.get("attempt_id") != ATTEMPT3_ID:
        raise SystemExit("the pinned report is not the landed attempt-3 BLEND arm")
    a3_dir = Path(str(report["run_dir"]))
    if a3_dir.name != ATTEMPT3_ID:
        raise SystemExit("the pinned report names an unexpected run dir")

    pass_a_path = a3_dir / "pass-a-direct-outputs.jsonl"
    measured_pass_a = sha256_file(pass_a_path)
    if measured_pass_a != ATTEMPT3_PASS_A_OUTPUTS_SHA256:
        raise SystemExit(
            "attempt-3 Pass-A outputs hash to %s, not the record %s"
            % (measured_pass_a, ATTEMPT3_PASS_A_OUTPUTS_SHA256)
        )
    texts: dict[str, str] = {}
    pass_a_message_digests: dict[str, str] = {}
    with pass_a_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("pass") != "A":
                raise SystemExit("an attempt-3 Pass-A row is not a Pass-A row")
            sample_id = str(row["sample_id"])
            text = row["direct_response_text"]
            if sha256_text(text) != row["direct_response_sha256"]:
                raise SystemExit(
                    "Pass-A text for %r does not hash to its own record" % sample_id
                )
            texts[sample_id] = text
            pass_a_message_digests[sample_id] = str(row["messages_sha256"])
    if set(texts) != set(audio_by_sample):
        raise SystemExit("the landed Pass-A texts do not cover the subset exactly")

    # ---- attempt 3's durable query-vector tables, keyed by text sha ------
    vectors_by_text_sha: dict[str, tuple[float, ...]] = {}
    vector_source: dict[str, str] = {}
    landed_path = a3_dir / "query-vectors.jsonl"
    measured_landed = sha256_file(landed_path)
    with landed_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = str(record["text_sha256"])
            if key in vectors_by_text_sha:
                continue
            vectors_by_text_sha[key] = tuple(float(v) for v in record["values"])
            vector_source[key] = str(record.get("source", "attempt3-durable-table"))
    bridge_path = a3_dir / "query-vectors-bridge.jsonl"
    measured_bridge = sha256_file(bridge_path)
    if measured_bridge != ATTEMPT3_BRIDGE_VECTORS_SHA256:
        raise SystemExit(
            "attempt-3 bridge vectors hash to %s, not the record" % measured_bridge
        )
    with bridge_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = str(record["text_sha256"])
            if key in vectors_by_text_sha:
                continue
            vectors_by_text_sha[key] = tuple(float(v) for v in record["values"])
            vector_source[key] = "attempt3-offline-bridge"

    ranker = rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
    fuser = fuse_supplyfilter_factory(FROZEN_FUSE)
    snapshot_sha = snapshot.content_hash()

    rows: dict[str, dict[str, object]] = {}
    missing_vector: list[str] = []
    for sample_id in sorted(texts):
        text = texts[sample_id]
        key = sha256_text(text)
        vector = vectors_by_text_sha.get(key)
        if vector is None:
            missing_vector.append(sample_id)
            continue
        direct_label = a2t_primary_tool_normalizer(text, label_targets)
        query_state = QueryState(
            query_id="%s:%s:step0" % (RUN_ID, sample_id),
            query_sample_id=sample_id,
            speech_packet_id=packet_by_sample[sample_id]["packet_id"],
            speech_packet_sha256=packet_by_sample[sample_id]["sha256"],
            use_split_identity_hash=SPLIT_IDENTITY_HASH,
        )
        reason: str
        selected: tuple[str, ...] = ()
        best_labels: tuple[str, ...] = ()
        recall_scores = multidim_recall(
            snapshot,
            {"content": vector},
            lambda facet_id: facet_vector_table.get(facet_id, {}),
            FROZEN_TOP_K,
        )
        top_m_kinds: tuple[str, ...] = ()
        content_in_top_m = 0
        best_content_cosine = None
        if not recall_scores:
            dispatch = False
            reason = "recall empty"
        else:
            rank_result = ranker(
                snapshot_sha256=snapshot_sha,
                query_state=query_state,
                recall_scores=recall_scores,
            )
            fusion_decision = fuser(
                snapshot=snapshot,
                snapshot_sha256=snapshot_sha,
                query_state=query_state,
                rank_result=rank_result,
                recall_scores=recall_scores,
            )
            selected = tuple(fusion_decision.selected_value_ids)
            top_m = tuple(c.facet_id for c in rank_result.candidates[: FROZEN_FUSE.m])
            top_m_kinds = tuple(fid.split(":")[1] if ":" in fid else fid for fid in top_m)
            content_in_top_m = sum(1 for kind in top_m_kinds if kind == "content")
            best_content_cosine = max(
                (
                    score
                    for dims in recall_scores.values()
                    for dim, score in dims.items()
                    if dim not in PRIOR_MASS_DIMENSIONS
                ),
                default=None,
            )
            if not selected:
                dispatch = False
                reason = "fusion selected nothing"
            else:
                fused = _fused_label_scores(
                    label_targets, values_by_id, selected, rank_result
                )
                blended = _blend_scores(label_targets, fused, direct_label, FROZEN_ALPHA)
                best_labels = _argmax_labels(blended)
                if best_labels == (direct_label,):
                    dispatch = False
                    reason = "direct label uniquely wins the blend (retain-primary)"
                else:
                    dispatch = True
                    reason = (
                        "no label recovered from the direct answer"
                        if direct_label is None
                        else "the blend argmax is not uniquely the direct label"
                    )
        rows[sample_id] = {
            "tier": sample_id.split(":")[0],
            "top_m_facet_kinds": list(top_m_kinds),
            "content_facets_in_top_m": content_in_top_m,
            "best_content_cosine": (
                round(best_content_cosine, 6) if best_content_cosine is not None else None
            ),
            "audio_seconds": audio_by_sample[sample_id],
            "direct_label_recovered": direct_label is not None,
            "direct_label_facet_id": direct_label,
            "query_vector_source": vector_source[key],
            "pass_a_messages_sha256": pass_a_message_digests[sample_id],
            "selected_value_count": len(selected),
            "selected_value_ids": list(selected),
            "best_label_count": len(best_labels),
            "dispatch": dispatch,
            "reason": reason,
        }
    if missing_vector:
        raise SystemExit(
            "no already-durable query vector for %d samples (%r); this pass embeds "
            "nothing and must not spend a tool contact"
            % (len(missing_vector), missing_vector[:5])
        )

    dispatch_ids = sorted(s for s, r in rows.items() if r["dispatch"])
    retain_ids = sorted(s for s, r in rows.items() if not r["dispatch"])
    by_tier: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "dispatch": 0})
    for sample_id, row in rows.items():
        entry = by_tier[str(row["tier"])]
        entry["n"] += 1
        entry["dispatch"] += 1 if row["dispatch"] else 0
    dispatch_audio = sum(float(rows[s]["audio_seconds"]) for s in dispatch_ids)
    audio_desc = sorted(audio_by_sample.values(), reverse=True)
    supplied_counts = Counter(int(row["selected_value_count"]) for row in rows.values())

    # ---- the attempt-4 ceiling this pass exists to compute ---------------
    projected_dispatch = len(dispatch_ids)
    pass_b_ceiling = projected_dispatch + CEILING_MARGIN
    attempt_ceiling = CANARY_CONTACTS + pass_b_ceiling + RESEND_CONTACTS
    core_remaining = CAMPAIGN_CORE_CELL - PRIOR_DURABLE_CORE
    audio_remaining = CAMPAIGN_AUDIO_CELL - PRIOR_DURABLE_AUDIO
    # Worst-case Pass-B metered audio: the ``pass_b_ceiling`` LARGEST sample
    # durations in the subset, so the audio guard is conservative whichever
    # samples actually dispatch.
    pass_b_worst_audio = sum(audio_desc[:pass_b_ceiling])
    canary_audio = sum(audio_desc[:1]) * 2
    resend_audio = audio_desc[0]
    attempt_worst_audio = canary_audio + pass_b_worst_audio + resend_audio
    fits = attempt_ceiling <= core_remaining and attempt_worst_audio <= audio_remaining

    projection = {
        "schema": "saea-a2t-g1-dispatch-projection-v2-postfix",
        "study": "speech-aware-evidence-acquisition",
        "run_id": PROJECTION_RUN_ID,
        "about_run_id": RUN_ID,
        "about_attempt": "the FOURTH BLEND attempt, the first flight after the ranker scale defect was repaired",
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tool": 0, "gold_opened": False},
        "ranker_repair": {
            "commit": RANKER_FIX_COMMIT,
            "kb_policy_sha256": kb_policy_sha,
            "rule": "every ranker dimension divided by max(1.0, sup_d) over the recalled candidate set before the weights apply",
            "structural_guarantee_under_the_locked_knobs": (
                "w_prior * 1.0 = 0.300 is strictly below w_cos * tau = 0.325, so "
                "every percept-admissible content facet outranks every prior-mass "
                "facet on any carrier by construction"
            ),
            "identity_on_the_locked_slurp_cell": (
                "proved on the sealed DEV-1000 store over 674 replayed "
                "trajectories, exact float equality"
            ),
        },
        "population": {
            "split_id": SPLIT_ID,
            "count": SPLIT_COUNT,
            "subset_receipt_sha256": measured_receipt,
            "split_identity_hash": SPLIT_IDENTITY_HASH,
        },
        "inputs": {
            "query_texts": (
                "attempt 3's LANDED Pass-A direct-decode texts -- the exact texts "
                "attempt 4 REPLAYS rather than re-flies, so the dispatch set here "
                "is the set the flight takes, not an estimate of it"
            ),
            "attempt3_id": ATTEMPT3_ID,
            "attempt3_report_sha256": measured_report,
            "attempt3_pass_a_outputs_sha256": measured_pass_a,
            "attempt3_query_vectors_sha256": measured_landed,
            "attempt3_bridge_vectors_sha256": measured_bridge,
            "distinct_query_vectors_available": len(vectors_by_text_sha),
            "snapshot_sha256": snapshot_sha,
            "content_facet_npz_sha256": measured_npz,
            "policy": (
                "the FROZEN v1 cell (alpha 0.45, tau 0.65, top-k 5, m 5 / c 2 / "
                "top_l 3, rrf 0.5/0.3/0.2) through rails.kb_policy's OWN pure "
                "functions, with the 1341c2db repair live"
            ),
        },
        "projection": {
            "dispatch_count": projected_dispatch,
            "retain_count": len(retain_ids),
            "dispatch_rate": round(projected_dispatch / SPLIT_COUNT, 6),
            "dispatch_audio_seconds": round(dispatch_audio, 6),
            "by_tier": {tier: dict(entry) for tier, entry in sorted(by_tier.items())},
            "retain_equals_recovered": all(
                (not row["dispatch"]) == bool(row["direct_label_recovered"])
                for row in rows.values()
            ),
            "no_label_recovered_count": sum(
                1 for row in rows.values() if not row["direct_label_recovered"]
            ),
            "trajectories_with_zero_content_facets_in_top_m": sum(
                1 for row in rows.values() if row["content_facets_in_top_m"] == 0
            ),
            "trajectories_with_a_content_facet_in_top_m": sum(
                1 for row in rows.values() if row["content_facets_in_top_m"] > 0
            ),
            "supplied_value_count_distribution": {
                str(k): supplied_counts[k] for k in sorted(supplied_counts)
            },
            "best_content_cosine_distribution": {
                "min": min(
                    (
                        row["best_content_cosine"]
                        for row in rows.values()
                        if row["best_content_cosine"] is not None
                    ),
                    default=None,
                ),
                "max": max(
                    (
                        row["best_content_cosine"]
                        for row in rows.values()
                        if row["best_content_cosine"] is not None
                    ),
                    default=None,
                ),
                "at_or_above_tau": sum(
                    1
                    for row in rows.values()
                    if row["best_content_cosine"] is not None
                    and row["best_content_cosine"] >= FROZEN_TAU
                ),
            },
        },
        "attempt4_ceiling": {
            "basis": (
                "Pass A is REPLAYED from attempt 3's hash-pinned landed texts at "
                "ZERO core contacts, so the only contacts attempt 4 can spend are "
                "the canary, one Pass-B evidence contact per DISPATCHING "
                "trajectory, and the identical-prompt resend"
            ),
            "canary_contacts": CANARY_CONTACTS,
            "pass_a_contacts": 0,
            "projected_dispatch": projected_dispatch,
            "margin": CEILING_MARGIN,
            "pass_b_contact_ceiling": pass_b_ceiling,
            "resend_contacts": RESEND_CONTACTS,
            "attempt_core_ceiling": attempt_ceiling,
            "campaign_core_cell": CAMPAIGN_CORE_CELL,
            "prior_durable_core": PRIOR_DURABLE_CORE,
            "core_remaining": core_remaining,
            "attempt_worst_case_audio_seconds": round(attempt_worst_audio, 6),
            "pass_b_worst_audio_seconds": round(pass_b_worst_audio, 6),
            "campaign_audio_cell": CAMPAIGN_AUDIO_CELL,
            "prior_durable_audio_seconds": PRIOR_DURABLE_AUDIO,
            "audio_remaining_seconds": round(audio_remaining, 6),
            "prior_durable_tool_contacts": PRIOR_DURABLE_TOOL,
            "campaign_tool_cell": CAMPAIGN_TOOL_CELL,
            "projected_tool_contacts": 0,
            "why_zero_tool_contacts": (
                "every Pass-A text is already covered by attempt 3's durable "
                "query-vector table, so the offline bridge has nothing to embed "
                "and the sidecar never needs to be spawned"
            ),
            "fits_remaining_cell": fits,
        },
        "margin_rationale": (
            "The dispatch set is EXACT under a deterministic policy over fixed "
            "texts and fixed vectors, so the margin is not there for the policy. "
            "It covers only serving-side residuals: an evidence contact that has "
            "to be re-sent, or a trajectory whose evidence decode fails once and "
            "is retried. It is deliberately small because the cell binds."
        ),
        "worst_case_audio_of_largest_n": {
            str(n): round(sum(audio_desc[:n]), 6)
            for n in (1, 5, 10, 15, 20, 23, 26, 30, 104)
        },
        "per_sample": {sample_id: rows[sample_id] for sample_id in sorted(rows)},
        "dispatch_sample_ids": dispatch_ids,
    }
    out_path = OUT_CHECK_DIR / "dispatch-projection-postfix.json"
    out_path.write_text(
        json.dumps(projection, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "POST-FIX DISPATCH PROJECTION (model-free, zero contacts): %d dispatch / %d "
        "retain of %d" % (projected_dispatch, len(retain_ids), SPLIT_COUNT)
    )
    print("  dispatch rate      : %.4f" % (projected_dispatch / SPLIT_COUNT))
    print("  dispatch audio (s) : %.3f" % dispatch_audio)
    print("  retain==recovered  : %s" % projection["projection"]["retain_equals_recovered"])
    print("  no label recovered : %d" % projection["projection"]["no_label_recovered_count"])
    print(
        "  content in top-m   : %d of %d"
        % (
            projection["projection"]["trajectories_with_a_content_facet_in_top_m"],
            SPLIT_COUNT,
        )
    )
    print(
        "  supplied-value dist: %s"
        % (projection["projection"]["supplied_value_count_distribution"],)
    )
    for tier, entry in sorted(by_tier.items()):
        print("  %-22s n=%d dispatch=%d" % (tier, entry["n"], entry["dispatch"]))
    print("")
    print("ATTEMPT-4 CEILING ARITHMETIC")
    print(
        "  %d canary + 0 pass-A (REPLAYED) + %d pass-B (%d dispatch + %d margin) + %d "
        "resend = %d"
        % (
            CANARY_CONTACTS,
            pass_b_ceiling,
            projected_dispatch,
            CEILING_MARGIN,
            RESEND_CONTACTS,
            attempt_ceiling,
        )
    )
    print("  core remaining     : %d of %d" % (core_remaining, CAMPAIGN_CORE_CELL))
    print(
        "  worst-case audio   : %.3f s against %.3f s remaining"
        % (attempt_worst_audio, audio_remaining)
    )
    print("  FITS               : %s" % fits)
    print("written: %s" % out_path)
    print("sha256 : %s" % sha256_file(out_path))
    return 0 if fits else 3


if __name__ == "__main__":
    raise SystemExit(main())
