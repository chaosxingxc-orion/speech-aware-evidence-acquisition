#!/usr/bin/env python3
"""CLI: freeze the Audio2Tool PAIRED 400 roster (owner decisions 67 and 71).

Owner decision 67 (2026-09-21): the first Audio2Tool cells -- A2T-NULL first
of all (decision 68) -- read on ONE 400-row subset of the sealed
``A2T-ORG1-UNION-4000``, drawn once and frozen, tier-stratified, receipted
under ``docs/receipts/rosters/``, whose comparator rows are the sealed
union-4000 outputs of the same sample ids. Decision 71 fixes the draw: 50
rows per tier over the eight tiers, one seeded draw at seed 20260921 from the
sample ids of the sealed union-4000, read in natural-mixture and equal-tier
weighting. Decision 76a names the comparator: the sealed direct rows of the
same ids, ``SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1``. Decision 139
(2026-09-27) puts Audio2Tool's own null on the GPU queue.

``A2T-PAIRED-400-V1`` is therefore drawn by :func:`core.roster.freeze_roster`
-- the ONE roster freezer of this repository, whose single-rng stratified
draw rule is stated once in its module docstring -- from the union
flight-roster receipt's own 4,000 items, stratum = tier, per_stratum = 50,
seed 20260921, ``split_role = "discovery"``, ``roster_role = "evaluation"``,
no exclusion and no group key, because the parent population is already the
sealed draw. It is the exact procedure ``scripts/build_a2t_evo_curve_roster.py``
used for the EVO-A1 curve roster at seed 20260906; only the seed, the roster
id and the comparator block differ, and the seed is the owner's.

Three documents are written, all model-free:

* ``docs/receipts/rosters/a2t-paired-400-v1.json`` -- the frozen roster
  receipt (``saea-roster-receipt-v1``), carrying the 400 sample ids, the
  identity hashes, the coverage proof, the four smoke ids and the pin of the
  comparator-rows file beside it;
* ``docs/receipts/rosters/a2t-paired-400-v1.comparator-rows.json`` -- per
  sample id, the SEALED direct comparator's own ``request_sha256`` and
  ``response_text_sha256`` copied out of its sealed ``outputs.jsonl`` (the
  hashes the seal already recorded; the text itself is never opened here),
  plus the comparator's run manifest, outputs, scores and session identities;
* ``docs/checks/speech-aware-evidence-acquisition/2026-09-27-a2t-paired-400-roster/
  flight-roster-receipt.json`` -- the ``saea-a2t-agentloop-flight-roster-
  receipt-v1`` view the Audio2Tool runtime adapter reads
  (``rails.adapters.audio2tool_runtime.build_runtime_adapter``), and
* ``configs/dataset/audio2tool-paired-400.json`` -- the dataset fragment that
  pins it, in exactly the shape ``configs/dataset/audio2tool-evo-curve-400.json``
  already uses.

What this script VERIFIES rather than assumes, all fail-closed:

* the union flight-roster receipt hashes to the value its own committed
  dataset fragment pins, and both of its identity hashes reproduce from its
  items;
* the drawn subset's media facts, MEASURED from the files on disk (wav bytes
  re-hashed, wav headers read for frames and sample rate, tier-7 bound to the
  FIRST user turn exactly as the official protocol serves it), agree to the
  byte and to 1e-6 with what the union receipt already records;
* every drawn sample id already resolves inside ``data.audio2tool``'s frozen
  probe-receipt universe, so NO new probe-sample view is written;
* every drawn sample id already sits inside the D1 identity closure (the base
  ``d1-identity.json`` or the additive ``d1-a2t-org1-union-4000.json``), so NO
  new D1 media supplement is needed;
* every drawn sample id has a promoted speech-feature packet in the sealed
  promotion receipt ``prepared/SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1/promotion.json``
  (the receipt the sealed direct baseline pins), so NO packet preparation is
  needed;
* the sealed comparator's run manifest is COMPLETED at 4,000 rows on the union
  identity, its outputs file hashes to the manifest's pin, and every drawn id
  has exactly one sealed comparator row.

ZERO CONTACTS: wav bytes are hashed and wav container headers are read; no
frozen core, tokenizer, embedder, retriever, scorer, network, GPU or paid
API. No query text, gold tool, expected call, annotation, prior output text
or score is opened; the comparator rows contribute hashes the seal already
recorded; domain is read from the released tier manifests as AGGREGATE
stratum counts only, exactly as the union receipt reads it.

Usage (WSL2, model-free)::

    python -B scripts/build_a2t_paired_400_roster.py            # print only
    python -B scripts/build_a2t_paired_400_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import (  # noqa: E402
    domains_by_sample_id,
    measured_media_facts,
    read_json,
)
from speech_aware_evidence_acquisition.analysis.a2t_evo_rosters import (  # noqa: E402
    covered_by_probe_receipts,
    flight_roster_document,
    gate_identity_hash,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    RosterItem,
    canonical_receipt_bytes,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)

DATE = "2026-09-27"
EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-PAIRED-400-ROSTER-V1"
DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
AUTHORITY = (
    f"{DECISIONS} rows 67, 68, 71, 76a and 139 (the paired 400-row subset of the sealed "
    "union-4000, drawn once at seed 20260921; A2T-NULL first; the sealed direct rows as the "
    f"comparator; the own null on the GPU queue); {INSTRUMENT} rules 3 and 6"
)
SPLIT_NAME = "A2T-PAIRED-400-V1"
SEED = 20260921
PER_TIER = 50
SMOKE_TIERS = ("tier1_direct", "tier2_parametric", "tier5_needle", "tier6_correction")
UNION_RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-a2t-org1-domain-grouped-roster/flight-roster-receipt.json"
)
UNION_FRAGMENT = "configs/dataset/audio2tool-org1-union-4000.json"
UNION_SPLIT_NAME = "A2T-ORG1-UNION-4000"
UNION_ROW_IDS = (
    "SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1",
    "SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1",
    "SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1",
    "SAEA-A2T-ORG1-DOMAIN-GROUPED-V1",
    "SAEA-A2T-NATIVE-SYSTEM-DIRECT-V1",
    "SAEA-A2T-NATIVE-SYSTEM-RECOVERY-DIRECT-V1",
    "SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1",
    "SAEA-A2T-NATIVE-ROLE-DUAL-STORE-UNION4000-V1",
)
CHECK_DIR = REPO_ROOT / (
    f"docs/checks/speech-aware-evidence-acquisition/{DATE}-a2t-paired-400-roster"
)
FLIGHT_RECEIPT_RELPATH = (
    f"docs/checks/speech-aware-evidence-acquisition/{DATE}-a2t-paired-400-roster/"
    "flight-roster-receipt.json"
)
ROSTER_RELPATH = "docs/receipts/rosters/a2t-paired-400-v1.json"
COMPARATOR_RELPATH = "docs/receipts/rosters/a2t-paired-400-v1.comparator-rows.json"
DATASET_RELPATH = "configs/dataset/audio2tool-paired-400.json"
ROSTER_PATH = REPO_ROOT / ROSTER_RELPATH
COMPARATOR_PATH = REPO_ROOT / COMPARATOR_RELPATH
DATASET_PATH = REPO_ROOT / DATASET_RELPATH
PROBES = REPO_ROOT / "docs/receipts/probe-samples"
BASE_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-identity.json"
UNION_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-a2t-org1-union-4000.json"
UNION_D1_RELPATH = "receipts/artifacts/d1-a2t-org1-union-4000.json"
EVO_CURVE_ROSTER = REPO_ROOT / "docs/receipts/rosters/a2t-evo-curve-400-v1.json"
CONSTRUCTION_ROSTER = REPO_ROOT / "docs/receipts/rosters/a2t-construction-800-v1.json"

#: The sealed direct comparator (decision 76a) and the promotion receipt its
#: baseline pins. Both are read under the data root; both were sealed on
#: 2026-09-15 / 2026-09-12 and are named by the committed baseline
#: ``configs/baseline/a2t-native-role-direct-union4000-v1.json``.
COMPARATOR_RUN_ID = "SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1"
COMPARATOR_ATTEMPT_ID = "attempt-a2t-native-role-direct-union4000-generation-v1"
COMPARATOR_BASELINE = "configs/baseline/a2t-native-role-direct-union4000-v1.json"
COMPARATOR_EXPERIMENT = "configs/experiment/a2t-native-role-direct-union4000-v1.json"
UNION_FLIGHT_IDENTITY = "ed8946ddf99f9e898af1c8cb94932c538165cd591c2cff3021321749e52103d6"
SECONDARY_COMPARATORS = (
    ("SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1", "attempt-20260904T172609Z-t1officialpop500"),
    ("SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1", "attempt-20260904T193726Z-t258officialpop1500"),
    ("SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1", "attempt-20260904T211040Z-t3467officialpop2000"),
)

DESIGN = (
    "The PAIRED 400 (owner decisions 67 and 71), roster_role 'evaluation': a 400-row "
    "tier-stratified subset (50 per tier over all eight tiers) of the sealed "
    "A2T-ORG1-UNION-4000, drawn ONCE by core.roster.freeze_roster at seed 20260921. Every "
    "Audio2Tool engineering cell of the current programme -- A2T-NULL (the carrier's own "
    "request-identical null, decision 68, flown first), A2T-NOTOOL, A2T-IDX, A2T-IDXT and "
    "the decision-76a direct-versus-system comparison -- reads on this roster, in both the "
    "natural-mixture and the equal-tier weighting, against the sealed union-4000 outputs of "
    "the same sample ids. The full 4,000 flies only for an admitted form."
)
SELECTION_RULE = (
    "core.roster.freeze_roster over the union receipt's own 4,000 items, stratum = tier, "
    "per_stratum = 50, seed 20260921, one shared rng advanced across strata in ascending "
    "name order; no exclusion and no group key, because the parent population is already "
    "the sealed draw. The seed is owner decision 71's, stated there before this draw."
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_lines(lines: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def _verified_union(repo_root: Path) -> tuple[Mapping[str, object], str]:
    """The union flight-roster receipt, hash-pinned and identity-reproduced."""

    path = repo_root / UNION_RECEIPT
    measured = _sha256_file(path)
    fragment = read_json(repo_root / UNION_FRAGMENT)
    pinned = str(fragment["a2t_calibration_subset_receipt_sha256"])  # type: ignore[index]
    if measured != pinned:
        raise SystemExit(
            f"{UNION_RECEIPT} hashes to {measured}, not the {pinned} its own dataset "
            f"fragment {UNION_FRAGMENT} pins"
        )
    receipt = read_json(path)
    if (
        receipt["schema"] != "saea-a2t-agentloop-flight-roster-receipt-v1"  # type: ignore[index]
        or receipt["carrier"] != AUDIO2TOOL_LOCK_KEY  # type: ignore[index]
        or receipt["split_role"] != "discovery"  # type: ignore[index]
        or receipt["split_name"] != UNION_SPLIT_NAME  # type: ignore[index]
    ):
        raise SystemExit(f"{UNION_RECEIPT} identity is not the sealed union")
    items = receipt["items"]  # type: ignore[index]
    if receipt["count"] != len(items):  # type: ignore[index]
        raise SystemExit(f"{UNION_RECEIPT} count disagrees with its items")
    if _sha256_lines([str(item["key"]) for item in items]) != receipt["split_identity_hash"]:  # type: ignore[index]
        raise SystemExit(f"{UNION_RECEIPT} split_identity_hash does not reproduce")
    flight = split_identity_hash(
        prefixed(AUDIO2TOOL_LOCK_KEY, [str(item["sample_id"]) for item in items])
    )
    if flight != receipt["flight_split_identity_hash"] or flight != UNION_FLIGHT_IDENTITY:  # type: ignore[index]
        raise SystemExit(f"{UNION_RECEIPT} flight_split_identity_hash does not reproduce")
    return receipt, measured


def _coverage(repo_root: Path, ids: Sequence[str]) -> dict[str, object]:
    """The proof that this roster needs NO new probe view and NO new supplement."""

    covered = covered_by_probe_receipts(PROBES, ids)
    covered_ids = {sample for found in covered.values() for sample in found}
    uncovered = sorted(set(ids) - covered_ids)
    base = read_json(BASE_D1)
    base_ids = {
        str(entry["id"])
        for entry in base["carriers"][AUDIO2TOOL_LOCK_KEY]["layers"]["media"]["manifest"]  # type: ignore[index]
    }
    supplement = read_json(UNION_D1)
    supplement_ids = {str(entry["id"]) for entry in supplement["manifest"]}  # type: ignore[index]
    outside = sorted(set(ids) - base_ids - supplement_ids)
    if uncovered:
        raise SystemExit(
            f"{len(uncovered)} drawn ids resolve in no committed probe-sample receipt; "
            "a new additive view would be needed and this script does not write one"
        )
    if outside:
        raise SystemExit(
            f"{len(outside)} drawn ids sit outside the D1 identity closure; a new media "
            "supplement would be needed and this script does not write one"
        )
    return {
        "probe_sample_receipts": {
            stem: len(found) for stem, found in sorted(covered.items())
        },
        "probe_sample_ids_covered": len(covered_ids),
        "probe_sample_ids_uncovered": 0,
        "new_probe_sample_view_required": False,
        "why_no_probe_view": (
            "every drawn id already resolves inside data.audio2tool's frozen-receipt "
            "universe; data.audio2tool._resolve_items refuses a sample id two "
            "probe-sample receipts claim, so an additive view for this roster would "
            "break the loader outright rather than add anything"
        ),
        "d1_base_ids": len(set(ids) & base_ids),
        "d1_union_supplement_ids": len(set(ids) & supplement_ids),
        "d1_ids_outside_the_closure": 0,
        "new_d1_media_supplement_required": False,
        "d1_media_supplement_to_configure": UNION_D1_RELPATH,
        "d1_media_supplement_sha256": _sha256_file(UNION_D1),
        "why_no_new_supplement": (
            "contracts.gate_media_identity accepts exactly one supplement path per run "
            "and verifies only the samples the binding names, so the paired cells "
            "configure the union's own supplement; a subset copy would duplicate "
            "already-bound identities for no gate the union supplement does not "
            "already close"
        ),
    }


def _packet_coverage(root: Path, ids: Sequence[str]) -> dict[str, object]:
    """The proof that every drawn id already holds a promoted speech packet.

    Reads the sealed promotion receipt the committed direct baseline pins by
    absolute path and sha256; a missing packet would mean a CPU preparation
    had to be registered, and this script refuses rather than implying one.
    """

    baseline = read_json(REPO_ROOT / COMPARATOR_BASELINE)
    receipt_path = Path(str(baseline["speech_packet_promotion_receipt"]))  # type: ignore[index]
    pinned = str(baseline["speech_packet_promotion_receipt_sha256"])  # type: ignore[index]
    if not receipt_path.is_file():
        raise SystemExit(f"promotion receipt is missing: {receipt_path}")
    measured = _sha256_file(receipt_path)
    if measured != pinned:
        raise SystemExit(
            f"promotion receipt {receipt_path} hashes to {measured}, not the {pinned} the "
            f"committed baseline {COMPARATOR_BASELINE} pins"
        )
    receipt = read_json(receipt_path)
    from speech_aware_evidence_acquisition.core.flight.runtime import packet_id_for_sample

    registered = {
        str(entry["packet_id"]): str(entry["packet_sha256"])  # type: ignore[index]
        for entry in receipt["packets"]  # type: ignore[index]
    }
    missing = [sample for sample in ids if packet_id_for_sample(sample) not in registered]
    if missing:
        raise SystemExit(
            f"{len(missing)} drawn ids have no promoted packet in {receipt_path}; a packet "
            "preparation would have to be registered and this script does not imply one"
        )
    root_str = str(receipt["feature_root"])  # type: ignore[index]
    return {
        "promotion_receipt": str(receipt_path),
        "promotion_receipt_sha256": measured,
        "promotion_schema": receipt["schema"],  # type: ignore[index]
        "feature_root": root_str,
        "packets_in_receipt": len(registered),
        "drawn_ids_with_a_promoted_packet": len(ids) - len(missing),
        "drawn_ids_without_a_promoted_packet": 0,
        "packet_preparation_required": False,
        "why": (
            "the sealed promotion SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1 (2026-09-12, model-free, "
            "twenty CPU workers over the already-warm legacy cache) promoted every one of the "
            "union-4000 rows into the formal SpeechFeaturePacketV1 tree the committed direct "
            "baseline pins; a strict subset of the union needs nothing promoted"
        ),
    }


def _comparator_rows(root: Path, ids: Sequence[str]) -> tuple[dict[str, object], dict[str, object]]:
    """The sealed direct comparator's identities and its per-row hashes for ``ids``.

    Reads the run manifest (identity and pins), the outputs file (verified
    against the manifest's own sha256) and copies, per drawn sample id, the two
    hashes the seal recorded -- ``request_sha256`` and ``response_text_sha256``.
    The ``text`` field is never read into any output of this script.
    """

    run_dir = root / "runs" / COMPARATOR_RUN_ID / COMPARATOR_ATTEMPT_ID
    manifest_path = run_dir / f"{COMPARATOR_RUN_ID}.run-manifest.json"
    outputs_path = run_dir / f"{COMPARATOR_RUN_ID}.outputs.jsonl"
    scores_path = run_dir / f"{COMPARATOR_RUN_ID}.scores.json"
    attempt_path = root / "attempts" / COMPARATOR_RUN_ID / f"{COMPARATOR_ATTEMPT_ID}.json"
    for path in (manifest_path, outputs_path, scores_path, attempt_path):
        if not path.is_file():
            raise SystemExit(f"sealed comparator file is missing: {path}")
    manifest = read_json(manifest_path)
    attempt = read_json(attempt_path)
    if (
        manifest.get("status") != "COMPLETED"  # type: ignore[union-attr]
        or manifest.get("exposure_run_id") != COMPARATOR_RUN_ID  # type: ignore[union-attr]
        or manifest["attempt"]["attempt_id"] != COMPARATOR_ATTEMPT_ID  # type: ignore[index]
        or manifest["split"]["identity_hash"] != UNION_FLIGHT_IDENTITY  # type: ignore[index]
        or manifest["split"]["count"] != 4000  # type: ignore[index]
        or attempt.get("state") != "FINALIZED"  # type: ignore[union-attr]
    ):
        raise SystemExit("the sealed comparator manifest or attempt is not the sealed direct")
    outputs_sha = _sha256_file(outputs_path)
    if outputs_sha != manifest["outputs"]["sha256"]:  # type: ignore[index]
        raise SystemExit("the comparator outputs file does not hash to its manifest pin")
    scores_sha = _sha256_file(scores_path)
    if scores_sha != manifest["scores"]["sha256"]:  # type: ignore[index]
        raise SystemExit("the comparator scores file does not hash to its manifest pin")
    wanted = set(ids)
    rows: dict[str, dict[str, str]] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            sample_id = str(record["sample_id"])
            if sample_id not in wanted:
                continue
            if sample_id in rows:
                raise SystemExit(f"the comparator holds two rows for {sample_id}")
            rows[sample_id] = {
                "request_sha256": str(record["request_sha256"]),
                "response_text_sha256": str(record["response_text_sha256"]),
                "response_sha256": str(record["response_sha256"]),
            }
    missing = sorted(wanted - set(rows))
    if missing:
        raise SystemExit(f"{len(missing)} drawn ids have no sealed comparator row")
    identity = {
        "run_id": COMPARATOR_RUN_ID,
        "attempt_id": COMPARATOR_ATTEMPT_ID,
        "role": (
            "the sealed direct comparator of owner decision 76a: the direct-only phase "
            "program of the shared controller (phase-direct-only-v1) through FlightRuntime "
            "and the OpenJiuwen executor on all 4,000 union rows, under the official-protocol "
            "compact registry, promoted speech packets, c98304 np3 max2048. Its rows on these "
            "400 ids are the cross-campaign comparator every paired cell is read against; "
            "nothing is re-flown on its side."
        ),
        "baseline_fragment": "a2t-native-role-direct-union4000-v1",
        "experiment_fragment": "a2t-native-role-direct-union4000-v1",
        "config_hash": manifest["config"]["config_hash"],  # type: ignore[index]
        "protocol_hash": manifest["protocol_hash"],  # type: ignore[index]
        "study_commit": manifest.get("study_commit"),  # type: ignore[union-attr]
        "run_manifest": {"relpath": str(manifest_path.relative_to(root)), "sha256": _sha256_file(manifest_path)},
        "outputs": {"relpath": str(outputs_path.relative_to(root)), "sha256": outputs_sha},
        "scores": {"relpath": str(scores_path.relative_to(root)), "sha256": scores_sha},
        "scorers": list(manifest["scorers"]),  # type: ignore[index]
        "session_receipt": dict(manifest["session_receipt"]),  # type: ignore[index]
        "cost": {
            key: manifest["cost"][key]  # type: ignore[index]
            for key in ("calls_used", "audio_seconds_used", "prompt_tokens_total", "completion_tokens_total", "tool_calls")
        },
        "rows_covered": len(rows),
        "secondary_comparators": [
            {
                "run_id": run_id,
                "attempt_id": attempt_id,
                "role": (
                    "the 2026-09-04 official-protocol raw-audio flight that first sealed this "
                    "row (named by the union fragment's own pairing); a different audio path "
                    "and geometry, so reported beside, never a null"
                ),
            }
            for run_id, attempt_id in SECONDARY_COMPARATORS
        ],
    }
    return identity, rows


def _smoke_four(items: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """The four smoke rows: the lexicographically first sample of tiers 1, 2, 5
    and 6 of THIS roster -- the rule the 2026-09-04 calibration smoke and the
    2026-09-05 phase smoke used, applied to the new roster."""

    chosen: list[str] = []
    for tier in SMOKE_TIERS:
        candidates = sorted(str(item["sample_id"]) for item in items if str(item["tier"]) == tier)
        if not candidates:
            raise SystemExit(f"no drawn row in {tier} for the smoke")
        chosen.append(candidates[0])
    seconds = {str(item["sample_id"]): float(item["audio_seconds"]) for item in items}
    return {
        "ids": chosen,
        "rule": (
            "the lexicographically first sample id of tiers 1, 2, 5 and 6 of the paired 400 "
            "-- the four tiers the 2026-09-04 calibration acceptance rule read, the same "
            "selection rule as SAEA-A2T-DIRECT-CALIBRATION-SMOKE-V1 and SAEA-A2T-PHASE-SMOKE-4-V1"
        ),
        "count": len(chosen),
        "audio_seconds_total": round(sum(seconds[sample] for sample in chosen), 6),
        "flight_split_identity_hash": split_identity_hash(prefixed(AUDIO2TOOL_LOCK_KEY, chosen)),
    }


def build(*, repo_root: Path, lock: Mapping[str, object], root: Path) -> dict[str, object]:
    union, union_sha256 = _verified_union(repo_root)
    items = list(union["items"])  # type: ignore[index]
    candidates = [
        RosterItem(
            sample_id=str(item["sample_id"]),
            stratum=str(item["tier"]),
            extra={
                "id": item["id"],
                "key": item["key"],
                "query_idx": item["query_idx"],
                "tier": item["tier"],
            },
        )
        for item in items
    ]
    roster = freeze_roster(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        candidates=candidates,
        per_stratum=PER_TIER,
        seed=SEED,
        split_role="discovery",
        roster_id=SPLIT_NAME,
        roster_role="evaluation",
    )
    ids = [str(item["sample_id"]) for item in roster["items"]]  # type: ignore[index]

    started = time.monotonic()
    media = measured_media_facts(lock, root, ids)
    elapsed = time.monotonic() - started

    parent = {str(item["sample_id"]): item for item in items}
    for sample_id in ids:
        facts = media[sample_id]
        row = parent[sample_id]
        if str(facts["media_relpath"]) != str(row["media_relpath"]):
            raise SystemExit(f"{sample_id}: media_relpath disagrees with the union receipt")
        if str(facts["audio_sha256"]) != str(row["audio_sha256"]):
            raise SystemExit(f"{sample_id}: audio bytes drift against the union receipt")
        if abs(float(facts["audio_seconds"]) - float(row["audio_seconds"])) > 1e-6:
            raise SystemExit(f"{sample_id}: audio duration drift against the union receipt")

    coverage = _coverage(repo_root, ids)
    packets = _packet_coverage(root, ids)
    comparator, comparator_rows = _comparator_rows(root, ids)

    overlap: dict[str, object] = {}
    for label, path in (("a2t-evo-curve-400-v1", EVO_CURVE_ROSTER), ("a2t-construction-800-v1", CONSTRUCTION_ROSTER)):
        if path.is_file():
            other = read_json(path)
            other_ids = {str(item["sample_id"]) for item in other["items"]}  # type: ignore[index]
            overlap[label] = len(set(ids) & other_ids)
    if overlap.get("a2t-construction-800-v1"):
        raise SystemExit("the paired 400 overlaps the construction roster; the union and the construction pool are meant to be disjoint")

    shared = {
        "authority": AUTHORITY,
        "generator": "scripts/build_a2t_paired_400_roster.py",
        "exposure_row": EXPOSURE_ROW_ID,
        "source_roster": UNION_RECEIPT,
        "source_roster_sha256": union_sha256,
        "source_roster_split_name": UNION_SPLIT_NAME,
        "source_roster_count": len(items),
        "source_roster_exposure_rows": list(UNION_ROW_IDS),
        "selection_rule": SELECTION_RULE,
        "seed": SEED,
        "coverage": coverage,
        "packet_coverage": packets,
    }
    flight = flight_roster_document(
        roster,
        media,
        split_name=SPLIT_NAME,
        domains=domains_by_sample_id(lock, root, ids),
        shared={
            **shared,
            "design": DESIGN,
            "strata": "tier (50 per tier, all eight) and domain",
            "strata_basis": (
                "tier is carried per item. Domain is NOT: it is the domain column of each "
                "tier's released manifest, recorded here as aggregate counts exactly as the "
                "union receipt records it, and resolved per sample at ANALYSIS time from the "
                "same manifests. Keeping it out of the item rows keeps this receipt's item "
                "shape identical to the union's and keeps a gold-adjacent label out of the "
                "file the flight entry point reads to build its samples"
            ),
            "pairing": (
                "every one of these 400 rows carries a SEALED direct row from "
                f"{COMPARATOR_RUN_ID} ({COMPARATOR_ATTEMPT_ID}) -- the decision-76a comparator, "
                "same request protocol, same packets, same geometry -- and a sealed "
                "official-protocol raw-audio output from the 2026-09-04 official-population "
                "flights; every paired cell is read against those bytes and nothing is "
                "re-flown on the comparator side"
            ),
            "role": (
                "the roster of every Audio2Tool engineering cell of the current programme, "
                "A2T-NULL first; it decides nothing by itself"
            ),
            "media_measured_seconds": round(elapsed, 3),
        },
    )
    seconds = [float(media[sample]["audio_seconds"]) for sample in ids]
    smoke = _smoke_four(flight["items"])  # type: ignore[arg-type]
    comparator_document = {
        "schema": "saea-a2t-paired-roster-comparator-rows-v1",
        "roster_id": SPLIT_NAME,
        "roster_receipt": ROSTER_RELPATH,
        "flight_split_identity_hash": flight["flight_split_identity_hash"],
        "comparator": comparator,
        "rows": {sample_id: comparator_rows[sample_id] for sample_id in ids},
        "what_a_row_is": (
            "the two hashes the comparator's own seal recorded for this sample id -- the "
            "request bytes and the delivered response text -- copied verbatim from the sealed "
            "outputs.jsonl whose sha256 is pinned above. No text, gold, score or transcript "
            "is written here; a later read joins on sample_id and compares hashes."
        ),
        "contacts": {"model": "none", "network": "none", "scorer": "none", "audio": "none"},
    }
    document = {
        **roster,
        **shared,
        "design": DESIGN,
        "role": "the roster of every current Audio2Tool engineering cell; A2T-NULL first; decides nothing",
        "status": "FROZEN_EVALUATION_ROSTER",
        "sample_selection_rule": (
            "inherited from the union: one wav per row under the paper code's own loader "
            "rule, and on tier 7 the FIRST user turn"
        ),
        "count": len(ids),
        "gate_exposure_identity_hash": gate_identity_hash(roster),
        "flight_split_identity_hash": flight["flight_split_identity_hash"],
        "probe_receipt_split_identity_hash": flight["split_identity_hash"],
        "tier_counts": dict(flight["tier_counts"]),  # type: ignore[arg-type]
        "domain_counts": dict(flight["domain_counts"]),  # type: ignore[arg-type]
        "distinct_query_idx_blocks": len({int(parent[s]["query_idx"]) for s in ids}),
        "overlap_with_sibling_rosters": overlap,
        "audio_seconds_total": round(sum(seconds), 6),
        "audio_seconds_longest_item": round(max(seconds), 6),
        "audio_seconds_shortest_item": round(min(seconds), 6),
        "rows_at_the_654_second_synthesis_defect": sorted(
            sample for sample in ids if float(media[sample]["audio_seconds"]) > 600.0
        ),
        "flight_roster_receipt": FLIGHT_RECEIPT_RELPATH,
        "dataset_fragment": DATASET_RELPATH,
        "comparator_rows": {"relpath": COMPARATOR_RELPATH, "sha256": "FILLED_AT_WRITE"},
        "comparator": {key: comparator[key] for key in ("run_id", "attempt_id", "config_hash", "protocol_hash", "outputs", "run_manifest", "scores")},
        "smoke_four": smoke,
        "exposure": (
            "NO NEW SPEECH IDENTITY. All 400 rows are already-consumed discovery identities of "
            "the Audio2Tool exposure union: contacted on 2026-09-04 under the official protocol "
            "by the three official-population runs, on 2026-09-05 by SAEA-A2T-ORG1-DOMAIN-GROUPED-V1, "
            "on 2026-09-12 by the native-system direct/recovery flights and on 2026-09-15 by the "
            "native-role direct and dual-store flights. Adding this receipt leaves the union's "
            "size unchanged, which the exposure row records"
        ),
        "contacts": {
            "audio": "wav bytes hashed and wav headers read for duration; no decoding",
            "model": "none",
            "network": "none",
            "scorer": "none",
            "comparator": "sealed hashes copied; no output text opened",
        },
    }
    if document["gate_exposure_identity_hash"] != roster["split_identity_hash"]:
        raise SystemExit("the gate's identity hash disagrees with freeze_roster")
    return {
        "roster": document,
        "flight": flight,
        "coverage": coverage,
        "packets": packets,
        "comparator_document": comparator_document,
        "smoke": smoke,
    }


def _write(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"refusing to overwrite an existing receipt: {path}")
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return _sha256_text(text)


def _dataset_fragment(roster: Mapping[str, object], flight: Mapping[str, object], flight_sha256: str) -> dict[str, object]:
    coverage = roster["coverage"]  # type: ignore[index]
    probes = coverage["probe_sample_receipts"]  # type: ignore[index]
    probe_text = ", ".join(f"{count} through {stem}.json" for stem, count in sorted(probes.items(), key=lambda kv: -kv[1]))
    domains = roster["domain_counts"]  # type: ignore[index]
    domain_text = ", ".join(f"{name} {count}" for name, count in sorted(domains.items(), key=lambda kv: -kv[1]))
    long_rows = roster["rows_at_the_654_second_synthesis_defect"]  # type: ignore[index]
    if long_rows:
        long_note = (
            f"The draw inherited {len(long_rows)} of the union's four 654-second synthesis defects "
            f"({', '.join(long_rows)}) and they are KEPT, because the sealed comparator rows this "
            "roster is paired against were produced on exactly these rows and because dodging "
            "them would make the draw a selection rather than a subset. The np3 x 32,768 geometry "
            "of the sealed direct baseline served them once already; the live phase fit re-derives "
            "the worst request before any contact."
        )
    else:
        long_note = (
            "The draw inherited none of the union's four 654-second synthesis defects; the "
            f"longest row is {roster['audio_seconds_longest_item']} s. The live phase fit still "
            "re-derives the worst request before any contact."
        )
    return {
        "carrier_lock_key": AUDIO2TOOL_LOCK_KEY,
        "split_id": SPLIT_NAME,
        "d1_media_supplement": coverage["d1_media_supplement_to_configure"],  # type: ignore[index]
        "d1_media_supplement_sha256": coverage["d1_media_supplement_sha256"],  # type: ignore[index]
        "a2t_calibration_subset_receipt": FLIGHT_RECEIPT_RELPATH,
        "a2t_calibration_subset_receipt_sha256": flight_sha256,
        "a2t_calibration_split_name": SPLIT_NAME,
        "a2t_calibration_split_role": "discovery",
        "a2t_calibration_roster_role": "evaluation",
        "a2t_calibration_split_identity_hash": flight["split_identity_hash"],
        "a2t_calibration_flight_split_identity_hash": flight["flight_split_identity_hash"],
        "a2t_calibration_identity_hash_conventions": (
            "a2t_calibration_split_identity_hash is SHA-256 over the LF-joined sorted roster 'key' "
            "values (audio2tool:<tier>:<id6>) -- the Audio2Tool probe-receipt integrity convention. "
            "a2t_calibration_flight_split_identity_hash is data.splits.split_identity_hash("
            "prefixed('audio2tool', sample_ids)) over audio2tool/<tier>:<id6>, the value "
            "core.flight.FlightRuntime.preflight computes at flight time and the value the frozen "
            f"roster {ROSTER_RELPATH} carries as its own split_identity_hash. Both cover the same 400 rows."
        ),
        "a2t_calibration_count": int(roster["count"]),  # type: ignore[arg-type]
        "a2t_calibration_audio_seconds_total": roster["audio_seconds_total"],
        "a2t_calibration_audio_seconds_longest_item": roster["audio_seconds_longest_item"],
        "a2t_calibration_key_names": (
            "The a2t_calibration_* key names are the flight-family contract "
            "rails.adapters.audio2tool_runtime.build_runtime_adapter reads (RUNTIME_ROSTER_BINDING_FIELDS); "
            "reusing them is what lets this roster fly through the SAME entry point and the SAME "
            "FlightRuntime as every other Audio2Tool direct cell, with no new code path. The keys "
            "name a receipt-scoped roster, not the calibration split."
        ),
        "a2t_calibration_population": (
            "The PAIRED 400 of owner decisions 67 and 71: a 400-row tier-stratified subset (50 per "
            "tier over all eight tiers) of the sealed A2T-ORG1-UNION-4000, drawn ONCE by "
            "core.roster.freeze_roster at seed 20260921 with split_role 'discovery' and roster_role "
            f"'evaluation'. Builder scripts/build_a2t_paired_400_roster.py; frozen receipt {ROSTER_RELPATH}; "
            f"exposure row {EXPOSURE_ROW_ID}. Every Audio2Tool engineering cell of the current programme "
            "(A2T-NULL first, decision 68; then A2T-NOTOOL, A2T-IDX, A2T-IDXT and the decision-76a "
            "direct-versus-system comparison) reads on this roster in both the natural-mixture and the "
            "equal-tier weighting; the full 4,000 flies only for an admitted form."
        ),
        "a2t_calibration_role": (
            "The one roster of the Audio2Tool engineering line. Its first flight is A2T-NULL, the "
            "carrier's own request-identical null (cells A2T-AA pass A and pass B), whose CI95 "
            "half-width becomes the margin every later Audio2Tool interval is read at (decisions 38 "
            "and 68); no Audio2Tool interval is read against zero again."
        ),
        "a2t_calibration_pairing": (
            "Every one of these 400 rows already carries a SEALED direct row from "
            f"{COMPARATOR_RUN_ID} ({COMPARATOR_ATTEMPT_ID}; the decision-76a comparator, same request "
            "protocol, same promoted packets, same c98304 np3 max2048 geometry) and a sealed "
            "official-protocol raw-audio output from SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1, "
            "SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1 and SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1. The "
            f"per-row hashes of the direct comparator are frozen beside the roster in {COMPARATOR_RELPATH}. "
            "Nothing is re-flown on the comparator side: greedy decoding is not bitwise reproducible "
            "across batch shapes on this runtime, which is exactly what A2T-NULL measures."
        ),
        "a2t_calibration_strata": (
            f"tier (50 per tier, all eight) and domain ({domain_text}). Domain is recorded as counts in "
            "the roster receipt and resolved per sample at ANALYSIS time from each tier's released "
            f"manifest, never at request time. {roster['distinct_query_idx_blocks']} distinct query_idx blocks."
        ),
        "a2t_calibration_d1_media_supplement": (
            f"NO NEW SUPPLEMENT. All 400 sample ids are already inside the D1 identity closure: "
            f"{coverage['d1_union_supplement_ids']} through the additive docs/{UNION_D1_RELPATH} and the other "  # type: ignore[index]
            f"{coverage['d1_base_ids']} through the immutable docs/receipts/artifacts/d1-identity.json, which "  # type: ignore[index]
            "contracts.gate_media_identity verifies against and skips. The gate accepts exactly one "
            "supplement path per run and verifies only the samples the binding names, so this fragment "
            "configures the union's own supplement; a subset copy would re-bind identities the union "
            "supplement already binds and close no gate it does not already close."
        ),
        "a2t_calibration_speech_packets": (
            "NO PACKET PREPARATION. Every one of the 400 rows already holds a promoted SpeechFeaturePacketV1 "
            f"in {roster['packet_coverage']['promotion_receipt']} (sha256 {roster['packet_coverage']['promotion_receipt_sha256']}, "  # type: ignore[index]
            f"feature root {roster['packet_coverage']['feature_root']}), the sealed 2026-09-12 promotion "  # type: ignore[index]
            "SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1 that the committed direct baseline pins; the flight's "
            "packet plane is a strict subset of an already-promoted tree and no encoder contact is owed."
        ),
        "a2t_calibration_scoring_identity": (
            f"NO NEW PROBE-SAMPLE RECEIPT. All 400 sample ids already resolve inside data.audio2tool's "
            f"frozen-receipt universe: {probe_text}. A receipt repeating any of them would be refused by "
            "_resolve_items as a duplicate and would break the loader outright."
        ),
        "a2t_calibration_exposure": (
            "Already-consumed discovery identities: every one of these 400 rows was contacted on "
            "2026-09-04 under the official protocol, on 2026-09-05 under ORG-1, on 2026-09-12 by the "
            "native-system flights and on 2026-09-15 by the native-role direct and dual-store flights. "
            "Adding the roster receipt leaves the Audio2Tool exposure union unchanged. This fragment "
            "grants no contact authority; the registered cells' preregistration and the exposure ledger do."
        ),
        "a2t_calibration_no_driver_split_name": (
            "This fragment deliberately declares no split_name key. split_id names the receipt-scoped "
            "split the calibration adapter resolves from the hash-pinned roster receipt above; it is "
            "never resolved through the generic probe-receipt universe."
        ),
        "a2t_calibration_longest_row_note": long_note,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    built = build(repo_root=REPO_ROOT, lock=lock, root=data_root())
    roster = built["roster"]
    flight = built["flight"]
    summary = {
        "split_name": SPLIT_NAME,
        "seed": SEED,
        "count": roster["count"],  # type: ignore[index]
        "strata_counts": roster["strata_counts"],  # type: ignore[index]
        "domain_counts": roster["domain_counts"],  # type: ignore[index]
        "distinct_query_idx_blocks": roster["distinct_query_idx_blocks"],  # type: ignore[index]
        "overlap_with_sibling_rosters": roster["overlap_with_sibling_rosters"],  # type: ignore[index]
        "audio_seconds_total": roster["audio_seconds_total"],  # type: ignore[index]
        "audio_seconds_longest_item": roster["audio_seconds_longest_item"],  # type: ignore[index]
        "rows_at_the_654_second_synthesis_defect": roster["rows_at_the_654_second_synthesis_defect"],  # type: ignore[index]
        "split_identity_hash": roster["split_identity_hash"],  # type: ignore[index]
        "probe_receipt_split_identity_hash": roster["probe_receipt_split_identity_hash"],  # type: ignore[index]
        "smoke_four": built["smoke"],
        "coverage": built["coverage"],
        "packet_coverage": built["packets"],
        "comparator": roster["comparator"],  # type: ignore[index]
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    if args.write:
        comparator_sha = _write(COMPARATOR_PATH, built["comparator_document"])
        roster["comparator_rows"] = {"relpath": COMPARATOR_RELPATH, "sha256": comparator_sha}  # type: ignore[index]
        text = write_roster(roster, ROSTER_PATH)
        flight_sha = _write(CHECK_DIR / "flight-roster-receipt.json", flight)
        dataset_sha = _write(DATASET_PATH, _dataset_fragment(roster, flight, flight_sha))
        summary["written"] = {
            ROSTER_RELPATH: _sha256_text(text),
            COMPARATOR_RELPATH: comparator_sha,
            FLIGHT_RECEIPT_RELPATH: flight_sha,
            DATASET_RELPATH: dataset_sha,
        }
        summary["canonical_bytes_reproduce"] = canonical_receipt_bytes(roster) == text.encode("utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
