#!/usr/bin/env python3
"""Build KC-E2's two model-free knowledge artifacts, deterministically.

1. ``configs/knowledge/e22-brief-v1/derangement-v1.json`` -- the form twin's
   CALL PAIRING. ``core.metadata_brief.select_twin_partners`` is the rule: for
   each roster call, the closest-measuring unused Earnings-22 call OUTSIDE the
   roster whose ticker, country, UN region and dialect family all differ from the
   arm's, matched by the SYMMETRIC padder. Measured here on WHITESPACE tokens,
   because this builder is model-free; ``scripts/e22_kc_e2_prompt_fit.py``
   re-verifies every pair on the FLIGHT tokenizer, writes the real pad plan and
   rewrites this artifact if any pair fails there. The roster receipt and the
   metadata table it was derived from are hash-pinned in the document, so a later
   roster change cannot silently re-pair the control.

2. ``docs/receipts/artifacts/e22-dev1500-clip-call-map.json`` -- the clip -> call
   map the whole cell is paired and clustered by: 1,500 published ESB clips over
   ten calls, with each call's own metadata-row digest beside it.

**Why 2 is a receipt and NOT a ``saea-d1-evidence-supplement-v1``**, stated here
because the KC-E2 brief asked for one and the gate cannot accept one:

* ``contracts.gate.FrozenCoreGate.__post_init__`` allows AT MOST ONE supplement
  per gate, media or evidence, never both -- and this cell's dataset fragment
  MUST carry the ``d1_media_supplement`` that brings the ``@ts2`` clips into D1's
  closure at all. An evidence supplement would displace it.
* ``gate_evidence_identity._d1_evidence_supplement_manifest`` requires the
  supplement's ``ids_sha256`` to EQUAL the carrier's own default evidence layer's
  sample universe. Earnings-22 has no evidence layer at all
  (``data.carriers.EARNINGS22_ORIGINAL.evidence is None``), and a 1,500-clip id
  set could never equal a 125-call one even if it had.

Both are structural, not incidental, which is why the brief's evidence records
carry ``carrier_bound=False`` and pin the table's bytes in the composed config
instead. This receipt is the pairing artifact, not an identity claim.

Zero contacts of every kind: two committed JSON reads, one metadata-table read
under ``SPEECHRL_DATA_DIR``, one hasher, two JSON writers. No model, tokenizer,
network, GPU or audio contact; no reference, transcript or annotation byte is
opened. Both outputs are byte-deterministic -- no timestamp, no commit id -- so a
rebuild reproduces the same sha256 and the fragments' pins never have to move.

Usage (WSL2)::

    python scripts/build_e22_brief_knowledge.py            # print, write nothing
    python scripts/build_e22_brief_knowledge.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.class_lists import (  # noqa: E402
    whitespace_token_count,
)
from speech_aware_evidence_acquisition.core.metadata_brief import (  # noqa: E402
    DERANGEMENT_SCHEMA,
    DISTINCT_TWIN_FIELDS,
    brief_terms,
    call_source_slice,
    metadata_header_and_rows,
    render_brief,
    select_twin_partners,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402

STUDY_SLUG = "speech-aware-evidence-acquisition"
CARRIER_LOCK_KEY = "earnings22-original"
CLIP_CALL_MAP_SCHEMA = "saea-e22-dev1500-clip-call-map-v1"

ROSTER_RELPATH = "docs/receipts/rosters/e22-dev-esb-1500-tail2s-v1.json"
METADATA_RELPATH = "datasets/earnings21-22/earnings22/metadata.csv"

DERANGEMENT_OUT = REPO_ROOT / "configs/knowledge/e22-brief-v1/derangement-v1.json"
CLIP_CALL_MAP_OUT = REPO_ROOT / "docs/receipts/artifacts/e22-dev1500-clip-call-map.json"


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    roster_path = REPO_ROOT / ROSTER_RELPATH
    roster_blob = roster_path.read_bytes()
    roster = json.loads(roster_blob.decode("utf-8"))
    if str(roster.get("carrier_lock_key")) != CARRIER_LOCK_KEY:
        raise SystemExit(f"{ROSTER_RELPATH} does not name {CARRIER_LOCK_KEY}")
    items = list(roster["items"])

    metadata_path = Path(root) / METADATA_RELPATH
    metadata_blob = metadata_path.read_bytes()
    metadata_sha256 = sha256_bytes(metadata_blob)
    metadata_text = metadata_blob.decode("utf-8")
    _, table_rows = metadata_header_and_rows(metadata_text)

    clip_call: dict[str, str] = {}
    for item in items:
        sample_id = str(item["sample_id"])
        stratum = str(item["stratum"])
        # The stratum IS the call. Derived independently from the id and checked
        # against it, so a roster whose stratum disagreed with its own ids would
        # stop this build rather than silently define the pairing twice.
        derived = sample_id.split("@", 1)[0].split("-", 1)[0]
        if derived != stratum:
            raise SystemExit(
                f"roster item {sample_id!r} carries stratum {stratum!r} but its id names "
                f"call {derived!r}"
            )
        if sample_id in clip_call:
            raise SystemExit(f"roster repeats clip {sample_id!r}")
        clip_call[sample_id] = stratum
    calls = sorted(set(clip_call.values()))
    missing = [call for call in calls if call not in table_rows]
    if missing:
        raise SystemExit(f"the metadata table has no row for call(s) {missing}")

    per_call = {call: sorted(k for k, v in clip_call.items() if v == call) for call in calls}
    row_digests = {
        call: sha256_bytes(call_source_slice(metadata_text, call).encode("utf-8"))
        for call in sorted(table_rows)
    }
    slices_by_call = {call: call_source_slice(metadata_text, call) for call in table_rows}
    briefs_by_call = {call: render_brief(text) for call, text in slices_by_call.items()}
    terms_by_call = {call: brief_terms(text) for call, text in slices_by_call.items()}
    # Measured on WHITESPACE tokens here, deliberately: this builder is
    # model-free and the flight tokenizer needs a resident server. The pairing
    # is a hash-pinned DEFAULT that scripts/e22_kc_e2_prompt_fit.py re-verifies
    # -- and, if a call fails on flight tokens, re-selects and rewrites -- before
    # the twin can fly. The document records which counter chose it.
    derangement, pad_repeats = select_twin_partners(
        briefs_by_call=briefs_by_call,
        roster_calls=calls,
        candidate_calls=sorted(table_rows),
        token_counter=whitespace_token_count,
        terms_by_call=terms_by_call,
    )

    ids_sha256 = sha256_bytes("\n".join(sorted(clip_call)).encode("utf-8"))
    map_sha256 = sha256_bytes(
        "\n".join(f"{clip},{clip_call[clip]}" for clip in sorted(clip_call)).encode("utf-8")
    )

    derangement_doc: dict[str, Any] = {
        "schema": DERANGEMENT_SCHEMA,
        "study": STUDY_SLUG,
        "carrier_lock_key": CARRIER_LOCK_KEY,
        "rule": (
            "core.metadata_brief.select_twin_partners: for each roster call in sorted "
            "order, the unused Earnings-22 call OUTSIDE the roster whose brief already "
            "measures CLOSEST to the arm's and whose ticker, country, UN region and "
            "major dialect family all DIFFER from the arm's, taking the first the "
            "symmetric padder accepts. Deterministic, injective and fixed-point-free, "
            "so no clip ever receives its own call's brief and no twin restates its "
            "arm's facts. Drawn from outside the roster because a partner inside it "
            "could state a fact that is true of another roster call; matched by the "
            "SYMMETRIC padder because a real brief can be longer than the one it twins "
            "-- the two Oceania calls render the corpus's shortest briefs and nothing "
            "that states different facts fits inside them."
        ),
        "selection_counter": "whitespace_token_count",
        "distinct_twin_fields": list(DISTINCT_TWIN_FIELDS),
        "twin_terms": {call: dict(terms_by_call[derangement[call]]) for call in calls},
        "whitespace_pad_repeats": {
            call: {"arm": pad_repeats[call][0], "twin": pad_repeats[call][1]}
            for call in calls
        },
        "verified_on_flight_tokenizer": False,
        "verification_step": (
            "scripts/e22_kc_e2_prompt_fit.py re-measures every pair on the flight "
            "tokenizer and, if any call's twin exceeds its arm at any prefix there, "
            "re-selects and rewrites this artifact before the pad plan is built."
        ),
        "calls": calls,
        "derangement": {call: derangement[call] for call in calls},
        "source_row_sha256": {call: row_digests[call] for call in calls},
        "twin_row_sha256": {call: row_digests[derangement[call]] for call in calls},
        "metadata_relpath": METADATA_RELPATH,
        "metadata_sha256": metadata_sha256,
        "roster_receipt": ROSTER_RELPATH,
        "roster_receipt_sha256": sha256_bytes(roster_blob),
        "split_identity_hash": str(roster["split_identity_hash"]),
        "what_this_is": (
            "the pinned call pairing core.evidence's e22-metadata-brief-deranged and "
            "-deranged-token-matched sources read to decide WHICH call's brief twins "
            "each clip. Pinned by path and sha256 in the twin's baseline fragment, so "
            "its exact contents land in params_hash and the derivation registry "
            "re-derives the twin from the same bytes on every gated run."
        ),
    }

    clip_call_doc: dict[str, Any] = {
        "schema": CLIP_CALL_MAP_SCHEMA,
        "study": STUDY_SLUG,
        "carrier_lock_key": CARRIER_LOCK_KEY,
        "roster_receipt": ROSTER_RELPATH,
        "roster_receipt_sha256": sha256_bytes(roster_blob),
        "roster_id": str(roster["roster_id"]),
        "split_role": str(roster["split_role"]),
        "split_identity_hash": str(roster["split_identity_hash"]),
        "count": len(clip_call),
        "calls": calls,
        "clips_per_call": {call: len(per_call[call]) for call in calls},
        "ids_sha256": ids_sha256,
        "map_sha256": map_sha256,
        "metadata_relpath": METADATA_RELPATH,
        "metadata_sha256": metadata_sha256,
        "call_row_sha256": {call: row_digests[call] for call in calls},
        "clip_call_map": {clip: clip_call[clip] for clip in sorted(clip_call)},
        "pairing_unit": (
            "the published ESB clip (1,500 of them). The bootstrap CLUSTER is the call "
            "(10 of them). Recovered from a clip id by splitting on '@' and then on the "
            "first '-', the same convention data.variant_ids.published_sample_key and "
            "reproduction.esb_reference.published_segment_key already fix."
        ),
        "why_not_a_d1_evidence_supplement": (
            "TWO structural refusals, not an omission. (1) contracts.gate.FrozenCoreGate "
            "allows at most ONE supplement per gate, media or evidence, and this cell's "
            "dataset fragment must carry the d1_media_supplement that brings the @ts2 "
            "clips into D1's closure at all. (2) gate_evidence_identity requires an "
            "evidence supplement's ids_sha256 to equal the carrier's own default "
            "evidence layer's sample universe, and earnings22-original declares no "
            "evidence layer (data.carriers.EARNINGS22_ORIGINAL.evidence is None); a "
            "1,500-clip id set could not equal a 125-call one in any case. The brief's "
            "evidence records therefore carry carrier_bound=False and the composed "
            "config pins the metadata table's bytes directly. This file is the pairing "
            "artifact and makes no identity claim."
        ),
    }
    return derangement_doc, clip_call_doc


def _write(path: Path, document: Mapping[str, Any]) -> str:
    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return sha256_bytes(payload.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.data_root) if args.data_root is not None else Path(data_root())
    derangement_doc, clip_call_doc = build(root)

    summary = {
        "calls": derangement_doc["calls"],
        "derangement": derangement_doc["derangement"],
        "clips": clip_call_doc["count"],
        "clips_per_call": clip_call_doc["clips_per_call"],
        "metadata_sha256": clip_call_doc["metadata_sha256"],
        "split_identity_hash": clip_call_doc["split_identity_hash"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not args.write:
        return 0
    summary["derangement_artifact_sha256"] = _write(DERANGEMENT_OUT, derangement_doc)
    summary["clip_call_map_sha256"] = _write(CLIP_CALL_MAP_OUT, clip_call_doc)
    print(
        json.dumps(
            {
                "derangement_artifact": str(DERANGEMENT_OUT.relative_to(REPO_ROOT)),
                "derangement_artifact_sha256": summary["derangement_artifact_sha256"],
                "clip_call_map": str(CLIP_CALL_MAP_OUT.relative_to(REPO_ROOT)),
                "clip_call_map_sha256": summary["clip_call_map_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
