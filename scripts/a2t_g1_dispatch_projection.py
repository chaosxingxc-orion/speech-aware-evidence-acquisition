"""MODEL-FREE, ZERO-CONTACT DISPATCH PROJECTION for the A2T stage G1 BLEND arm.

Row ``SAEA-SN-MF-A2T-G1-DISPATCH-PROJECTION`` (model-free-check).

WHY THIS EXISTS. The third BLEND attempt is a TWO-PASS flight and its budget
binds: 196 of the campaign's 400 core contacts are already durable, so only 204
remain, while the two-pass WORST case (2 canary + 104 pass-A direct decodes +
104 pass-B evidence contacts + 1 resend = 211) exceeds it. The launcher's own
fail-closed sizing guard would therefore REFUSE TAKEOFF AT ZERO SPEND. An
attempt ceiling lower than the worst case may only be registered WITH ITS BASIS
STATED, and this pass computes that basis.

WHAT IT COMPUTES. Exactly the registered v1 cell's own dispatch predicate,
through ``rails.kb_policy``'s OWN pure functions (never reimplemented):

    direct_label := a2t primary-tool normalizer over the answer's own call list
    recall       := multidim_recall(snapshot, {"content": q}, facet_vectors, 5)
    rank         := rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
    fusion       := fuse_supplyfilter_factory(FROZEN_FUSE)
    blended      := _blend_scores(_fused_label_scores(...), direct_label, 0.45)
    RETAIN  iff  recall is empty, or fusion selected nothing, or
                 _argmax_labels(blended) == (direct_label,)
    DISPATCH otherwise -- and a dispatch is exactly one pass-B core contact.

ITS INPUT IS ALREADY-LANDED MATERIAL AND NOTHING ELSE. The query text of each
trajectory is the LANDED M0 arm's own direct-decode answer for that sample,
verified one by one against that arm's per-sample ``direct_response_sha256``
records; the query vectors are the ALREADY-EMBEDDED vectors durable on the row
(attempt 2's offline precompute over exactly those texts, plus attempt 2's five
live-embedded divergent texts). ZERO model contacts, ZERO tool contacts, gold
never opened.

ITS ONE STATED LIMITATION. Pass A re-flies the direct decode, and the program's
known multi-slot decode-variance channel means a minority of flown texts will
not reproduce the M0 text byte for byte (attempt 1: 4 of 26; attempt 2: 5 of
58, hit rate 0.9138). Where the text diverges the dispatch decision may differ,
so this is a PROJECTION over the same population under the same policy, not a
prediction of the flown count. The registered ceiling therefore carries a
margin on top of it.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/a2t_g1_dispatch_projection.py
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
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
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    FuseKnobs,
    RankWeights,
    _argmax_labels,
    _blend_scores,
    _fused_label_scores,
    PRIOR_MASS_DIMENSIONS,
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
PROJECTION_RUN_ID = "SAEA-SN-MF-A2T-G1-DISPATCH-PROJECTION"
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

M0_ATTEMPT_ID = "attempt-20260825T100735Z-a2tg1m0"
M0_ARM_REPORT_RELNAME = "arm1-m0-mechanical-report.json"
M0_ARM_REPORT_SHA256 = (
    "7e5e9223c48b1bc457b2b02cb54050d208d717b376326ab5061da8847366ab37"
)
ATTEMPT2_ID = "attempt-20260825T114856Z-a2tg1blend"
ATTEMPT2_PRECOMPUTED_SHA256 = (
    "4fceb9488a5d0245837dfde85cb9d918115d8e6c7f720b2e1e9eccdfeaf46657"
)

OUT_CHECK_DIR = (
    REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-25-a2t-g1"
)


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
    # The QueryState the runtime controller sees is built by
    # ``rails.runner._initial_query_state`` from the promoted speech packet's
    # own descriptor, so this projection binds the identical descriptor rather
    # than a stand-in. Reading a packet header is a local file read: no audio
    # is decoded, no model is loaded and no contact is spent.
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

    # ---- the LANDED M0 direct texts, verified against their own records --
    report_path = OUT_CHECK_DIR / M0_ARM_REPORT_RELNAME
    measured_report = sha256_file(report_path)
    if measured_report != M0_ARM_REPORT_SHA256:
        raise SystemExit("the landed M0 arm report is not the pinned bytes")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("arm_id") != "M0" or report.get("attempt_id") != M0_ATTEMPT_ID:
        raise SystemExit("the pinned M0 report is not the landed M0 attempt")
    m0_run_dir = Path(str(report["run_dir"]))
    mech = json.loads(
        (m0_run_dir / "arm1-m0-mechanical.json").read_text(encoding="utf-8")
    )
    texts: dict[str, str] = {}
    with (m0_run_dir / "arm1-m0-outputs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sample_id = str(row["sample_id"])
            text = row["direct_response_text"]
            if sha256_text(text) != mech.get(sample_id, {}).get("direct_response_sha256"):
                raise SystemExit(
                    "M0 direct text for %r does not hash to its record" % sample_id
                )
            texts[sample_id] = text
    if set(texts) != set(audio_by_sample):
        raise SystemExit("the landed M0 texts do not cover the subset exactly")

    # ---- already-durable query vectors, keyed by text sha ----------------
    a2_dir = root / "runs" / RUN_ID / ATTEMPT2_ID
    precomputed_path = a2_dir / "query-vectors-precomputed.jsonl"
    measured_precomputed = sha256_file(precomputed_path)
    if measured_precomputed != ATTEMPT2_PRECOMPUTED_SHA256:
        raise SystemExit(
            "attempt-2 precomputed query vectors hash to %s, not the landed record %s"
            % (measured_precomputed, ATTEMPT2_PRECOMPUTED_SHA256)
        )
    vectors_by_text_sha: dict[str, tuple[float, ...]] = {}
    vector_source: dict[str, str] = {}
    with precomputed_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = str(record["text_sha256"])
            vectors_by_text_sha[key] = tuple(float(v) for v in record["values"])
            vector_source[key] = "attempt2-offline-precompute"
    landed_path = a2_dir / "query-vectors.jsonl"
    if landed_path.exists():
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
                vector_source[key] = "attempt2-live-embed"

    ranker = rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
    fuser = fuse_supplyfilter_factory(FROZEN_FUSE)
    snapshot_sha = snapshot.content_hash()

    rows: dict[str, dict[str, object]] = {}
    for sample_id in sorted(texts):
        text = texts[sample_id]
        key = sha256_text(text)
        vector = vectors_by_text_sha.get(key)
        if vector is None:
            raise SystemExit(
                "no already-durable query vector for %s; this projection embeds "
                "nothing and must not spend a tool contact" % sample_id
            )
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
            # WHY a trajectory retains is as important as THAT it retains, so
            # the top-m rank window the fuser actually admits over is recorded
            # per sample: the percept-admission gate reads only NON-prior-mass
            # dimensions, so a top-m window occupied entirely by label/prior
            # facets can never admit anything however high the cosines are.
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
            "selected_value_count": len(selected),
            "best_label_count": len(best_labels),
            "dispatch": dispatch,
            "reason": reason,
        }

    dispatch_ids = sorted(s for s, r in rows.items() if r["dispatch"])
    retain_ids = sorted(s for s, r in rows.items() if not r["dispatch"])
    by_tier: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "dispatch": 0})
    for sample_id, row in rows.items():
        entry = by_tier[str(row["tier"])]
        entry["n"] += 1
        entry["dispatch"] += 1 if row["dispatch"] else 0
    dispatch_audio = sum(float(rows[s]["audio_seconds"]) for s in dispatch_ids)
    audio_desc = sorted(audio_by_sample.values(), reverse=True)

    projection = {
        "schema": "saea-a2t-g1-dispatch-projection-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": PROJECTION_RUN_ID,
        "about_run_id": RUN_ID,
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tool": 0, "gold_opened": False},
        "population": {
            "split_id": SPLIT_ID,
            "count": SPLIT_COUNT,
            "subset_receipt_sha256": measured_receipt,
            "split_identity_hash": SPLIT_IDENTITY_HASH,
        },
        "inputs": {
            "query_texts": (
                "the LANDED M0 arm's own per-sample direct-decode answers, each "
                "verified against that arm's direct_response_sha256 record"
            ),
            "m0_attempt_id": M0_ATTEMPT_ID,
            "m0_report_sha256": measured_report,
            "query_vectors": (
                "already-durable embeddings on this row; nothing is embedded here"
            ),
            "attempt2_precomputed_sha256": measured_precomputed,
            "snapshot_sha256": snapshot_sha,
            "content_facet_npz_sha256": measured_npz,
            "policy": (
                "the FROZEN v1 cell (alpha 0.45, tau 0.65, top-k 5, m 5 / c 2 / "
                "top_l 3, rrf 0.5/0.3/0.2) through rails.kb_policy's OWN pure "
                "functions"
            ),
        },
        "projection": {
            "dispatch_count": len(dispatch_ids),
            "retain_count": len(retain_ids),
            "dispatch_rate": round(len(dispatch_ids) / SPLIT_COUNT, 6),
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
        "worst_case_audio_of_largest_n": {
            str(n): round(sum(audio_desc[:n]), 6) for n in (10, 20, 26, 30, 40, 52, 104)
        },
        "limitation": (
            "Pass A re-flies the direct decode. The program's known multi-slot "
            "decode-variance channel means a minority of flown texts will not "
            "reproduce the M0 text byte for byte (attempt 1: 4 of 26; attempt 2: 5 "
            "of 58). Where the text diverges the dispatch decision may differ, so "
            "this is a PROJECTION over the same population under the same policy, "
            "not a prediction of the flown count. The registered attempt ceiling "
            "carries a margin on top of it."
        ),
        "per_sample": {sample_id: rows[sample_id] for sample_id in sorted(rows)},
        "dispatch_sample_ids": dispatch_ids,
    }
    out_path = OUT_CHECK_DIR / "dispatch-projection.json"
    out_path.write_text(
        json.dumps(projection, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "DISPATCH PROJECTION (model-free, zero contacts): %d dispatch / %d retain of %d"
        % (len(dispatch_ids), len(retain_ids), SPLIT_COUNT)
    )
    print("  dispatch rate      : %.4f" % (len(dispatch_ids) / SPLIT_COUNT))
    print("  dispatch audio (s) : %.3f" % dispatch_audio)
    print(
        "  retain==recovered  : %s"
        % projection["projection"]["retain_equals_recovered"]
    )
    print(
        "  no label recovered : %d"
        % projection["projection"]["no_label_recovered_count"]
    )
    for tier, entry in sorted(by_tier.items()):
        print("  %-22s n=%d dispatch=%d" % (tier, entry["n"], entry["dispatch"]))
    print("written: %s" % out_path)
    print("sha256 : %s" % sha256_file(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
