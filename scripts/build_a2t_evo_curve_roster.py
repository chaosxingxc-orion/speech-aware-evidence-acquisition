#!/usr/bin/env python3
"""CLI: freeze the EVO-A1 CURVE roster (MODEL-FREE, identity and media only).

Exposure row ``SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1``; authority
``docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md``
section 7, closed by the coordinator on 2026-09-06 as **Option A**.

``A2T-EVO-CURVE-400-V1`` is a 400-row, tier-stratified (50 per tier) SUBSET of
the sealed union ``A2T-ORG1-UNION-4000``, drawn ONCE by
:func:`core.roster.freeze_roster` at seed 20260906 with ``split_role
= "discovery"`` and ``roster_role = "evaluation"``. It is read once per round
by the round's incumbent and decides nothing; because it is a strict subset of
the final read's population, the curve and the evaluation delta are measured on
one distribution and the generalization gap is not confounded by a population
change.

No new speech identity: every one of the 400 rows was contacted on 2026-09-04
under the official protocol and again on 2026-09-05 under ORG-1, and each
carries a sealed official-protocol output the curve read is paired against.

What this script VERIFIES rather than assumes, all fail-closed:

* the union flight-roster receipt hashes to the value its own committed dataset
  fragment pins, and both of its identity hashes reproduce from its items;
* the drawn subset's media facts, MEASURED from the files on disk by
  ``analysis.a2t_evo_capacity.measured_media_facts`` (wav bytes re-hashed, wav
  headers read for frames and sample rate, tier-7 bound to the FIRST user turn
  exactly as the official protocol serves it), agree to the byte and to 1e-6
  with what the union receipt already records;
* every drawn sample id already resolves inside ``data.audio2tool``'s frozen
  probe-receipt universe, so NO new probe-sample view may be written -- one
  that repeated an id would be refused by the loader as a duplicate;
* every drawn sample id already sits inside the D1 identity closure, in the
  base ``d1-identity.json`` or in the additive ``d1-a2t-org1-union-4000.json``
  supplement, so NO new D1 media supplement is needed either.

ZERO CONTACTS: wav bytes are hashed and wav container headers are read for
frame count and sample rate; no decoding beyond the header. No frozen core,
tokenizer, embedder, retriever, scorer, network, GPU or paid API. No query
text, gold tool, expected call, annotation, prior output or score is opened;
domain is read from the released tier manifests as AGGREGATE stratum counts
only, exactly as the union receipt reads it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1"
AUTHORITY = (
    "docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md"
)
SPLIT_NAME = "A2T-EVO-CURVE-400-V1"
SEED = 20260906
PER_TIER = 50
UNION_RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-a2t-org1-domain-grouped-roster/flight-roster-receipt.json"
)
UNION_FRAGMENT = "configs/dataset/audio2tool-org1-union-4000.json"
UNION_ROW_IDS = (
    "SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1",
    "SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1",
    "SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1",
    "SAEA-A2T-ORG1-DOMAIN-GROUPED-V1",
)
CHECK_DIR = REPO_ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-curve-roster"
)
ROSTER_PATH = REPO_ROOT / "docs/receipts/rosters/a2t-evo-curve-400-v1.json"
PROBES = REPO_ROOT / "docs/receipts/probe-samples"
BASE_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-identity.json"
UNION_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-a2t-org1-union-4000.json"

DESIGN = (
    "EVO-A1 curve roster, roster_role 'evaluation': a 400-row tier-stratified subset "
    "(50 per tier) of the sealed A2T-ORG1-UNION-4000, drawn once by core.roster"
    ".freeze_roster at seed 20260906. It is read once per round by that round's "
    "incumbent and DECIDES NOTHING -- no gate, no selection and no acceptance reads "
    "it. Its virtue is that it is a strict SUBSET of the final read's population, so "
    "the curve and the evaluation delta sit on one distribution."
)
SELECTION_RULE = (
    "core.roster.freeze_roster over the union receipt's own 4,000 items, stratum = "
    "tier, per_stratum = 50, seed 20260906, one shared rng advanced across strata in "
    "ascending name order; no exclusion and no group key, because the parent "
    "population is already the sealed draw"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        or receipt["split_name"] != "A2T-ORG1-UNION-4000"  # type: ignore[index]
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
    if flight != receipt["flight_split_identity_hash"]:  # type: ignore[index]
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
        "d1_media_supplement_to_configure": "receipts/artifacts/d1-a2t-org1-union-4000.json",
        "d1_media_supplement_sha256": _sha256_file(UNION_D1),
        "why_no_new_supplement": (
            "contracts.gate_media_identity accepts exactly one supplement path per run "
            "and verifies only the samples the binding names, so the curve cell "
            "configures the union's own supplement; a subset copy would duplicate "
            "3xx already-bound identities for no gate the union supplement does not "
            "already close"
        ),
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

    # The measured facts must equal what the union receipt already records, or
    # the D1 supplement the curve cell configures does not describe these bytes.
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
    shared = {
        "authority": AUTHORITY,
        "generator": "scripts/build_a2t_evo_curve_roster.py",
        "exposure_row": EXPOSURE_ROW_ID,
        "source_roster": UNION_RECEIPT,
        "source_roster_sha256": union_sha256,
        "source_roster_split_name": "A2T-ORG1-UNION-4000",
        "source_roster_count": len(items),
        "source_roster_exposure_rows": list(UNION_ROW_IDS),
        "selection_rule": SELECTION_RULE,
        "seed": SEED,
        "coverage": coverage,
    }
    flight = flight_roster_document(
        roster,
        media,
        split_name=SPLIT_NAME,
        domains=domains_by_sample_id(lock, root, ids),
        shared={
            **shared,
            "design": DESIGN,
            "pairing": (
                "every one of these 400 rows carries a sealed official-protocol output "
                "under the compact registry from the three 2026-09-04 official-population "
                "flights; the curve read is paired against those bytes and nothing is "
                "re-flown on the baseline side"
            ),
            "role": (
                "the evolution curve: one read per round by that round's post-decision "
                "incumbent. It decides nothing"
            ),
            "media_measured_seconds": round(elapsed, 3),
        },
    )
    seconds = [float(media[sample]["audio_seconds"]) for sample in ids]
    document = {
        **roster,
        **shared,
        "design": DESIGN,
        "role": "the evolution curve; read once per round, decides nothing",
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
        "audio_seconds_total": round(sum(seconds), 6),
        "audio_seconds_longest_item": round(max(seconds), 6),
        "audio_seconds_shortest_item": round(min(seconds), 6),
        "flight_roster_receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-06-a2t-evo-curve-roster/flight-roster-receipt.json"
        ),
        "exposure": (
            "NO NEW SPEECH IDENTITY. All 400 rows are already-consumed discovery "
            "identities of the Audio2Tool exposure union: contacted on 2026-09-04 under "
            "the official protocol by the three official-population runs and again on "
            "2026-09-05 by SAEA-A2T-ORG1-DOMAIN-GROUPED-V1. Adding this receipt leaves "
            "the union's size unchanged, which the exposure row records"
        ),
        "contacts": {
            "audio": "wav bytes hashed and wav headers read for duration; no decoding",
            "model": "none",
            "network": "none",
            "scorer": "none",
        },
    }
    if document["gate_exposure_identity_hash"] != roster["split_identity_hash"]:
        raise SystemExit("the gate's identity hash disagrees with freeze_roster")
    return {"roster": document, "flight": flight, "coverage": coverage}


def _write(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f"refusing to overwrite an existing receipt: {path}")
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        "count": roster["count"],  # type: ignore[index]
        "strata_counts": roster["strata_counts"],  # type: ignore[index]
        "domain_counts": roster["domain_counts"],  # type: ignore[index]
        "distinct_query_idx_blocks": roster["distinct_query_idx_blocks"],  # type: ignore[index]
        "audio_seconds_total": roster["audio_seconds_total"],  # type: ignore[index]
        "audio_seconds_longest_item": roster["audio_seconds_longest_item"],  # type: ignore[index]
        "split_identity_hash": roster["split_identity_hash"],  # type: ignore[index]
        "probe_receipt_split_identity_hash": roster["probe_receipt_split_identity_hash"],  # type: ignore[index]
        "coverage": built["coverage"],
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    if args.write:
        text = write_roster(roster, ROSTER_PATH)
        summary["roster_receipt"] = str(ROSTER_PATH.relative_to(REPO_ROOT))
        summary["roster_receipt_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        summary["flight_roster_receipt_sha256"] = _write(
            CHECK_DIR / "flight-roster-receipt.json", flight
        )
        summary["canonical_bytes_reproduce"] = canonical_receipt_bytes(roster) == text.encode(
            "utf-8"
        )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
