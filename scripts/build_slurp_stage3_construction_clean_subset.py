#!/usr/bin/env python3
"""CLI: build R01C, the knowledge-source-free clean subset of the Stage-3
construction roster ``SLURP-STAGE3-CONSTRUCTION-R01``.

Why this exists. Cell ROLL-1 flies the 800-row TRAIN construction roster R01
as its AgentLoop QUERY population, and ``rails.runner
.run_speech_native_agent_loop`` refuses any run whose query samples intersect
the bound knowledge snapshot's own ``source_sample_ids``::

    AgentLoop query samples overlap the TRAIN knowledge source roster: [...]

The bound snapshot is the COMPOSITE of the cell's named stores
(``rails.knowledge_stores._composite`` unions every store's
``source_sample_ids``). Item S3-1k removed the overlap contributed by the
``train-exemplars`` store by re-pointing it at the R01-excluded release
``size-pool-annotated-exemplars-minus-r01``. The two AUTHORED semantic
stores -- ``intent-boundaries-v1`` and ``slot-contracts-v2`` -- cannot be
re-pointed model-free: their cards name R01 recordings in
``source_support.source_sample_ids``, and re-authoring a card is a model
contact. The remaining intersection is therefore removed from the QUERY side
instead: the roster drops every row whose utterance is a knowledge source,
and ROLL-1 flies the clean remainder.

R01C is a PURE SELECTION of R01. No new draw, no new seed, no re-ranking, no
re-encoding: every surviving item is the parent receipt's item verbatim, in
the parent's order. Exclusion is by UTTERANCE, not by recording -- the same
rule ``scripts/build_slurp_stage3_r01_excluded_exemplar_store.py`` applies
from the knowledge side -- so a ``-headset`` sibling is dropped when the
other recording of the same utterance is a knowledge source.

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
encoder, tokenizer, scorer, GPU and network contact (an offline socket guard
is armed before the first input is opened and its attempt count is recorded
in the receipt). No sentence, transcript, scenario, action, intent, entity,
gold or score is read anywhere in this file; only ids, counts, hashes and
media-identity fields already sealed by the parent artifacts are touched.

Artifacts::

    docs/receipts/rosters/slurp-stage3-construction-r01c.json
    configs/dataset/slurp-speech-native-stage3-construction-r01c.json
    $SPEECHRL_DATA_DIR/vectors/slurp-stage3-construction-r01c-v1/
        query-vectors-speech-segments.jsonl        (+ .provenance.json)
        query-vectors-speech-content-v1.jsonl      (+ .provenance.json)

The D1 media supplement is NOT rebuilt: the R01 supplement closes over all
800 parent recordings and is therefore a strict SUPERSET of R01C, which the
media-identity gate accepts (``contracts.gate_media_identity
._d1_media_supplement_records`` verifies the supplement's own integrity and
looks each flown id up in it; it never requires an exact cover). The parent
supplement triple is carried into the R01C view verbatim, and this builder
proves the coverage before writing.

Run in WSL2 (the governed SLURP release lives under ``$SPEECHRL_DATA_DIR``)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_stage3_construction_clean_subset.py
    ... --write     # write every artifact that does not exist yet
    ... --check     # recompute and compare against what is already written
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    CONSTRUCTION_ROSTER_ROLE,
    read_roster,
    verify_roster,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (  # noqa: E402
    load_knowledge_store_binding,
)

CARRIER = "slurp"
RECEIPT_SCHEMA = "saea-roster-receipt-v1"
RUNTIME_VIEW_SCHEMA = "saea-speech-native-runtime-view-v1"
STUDY = "speech-aware-evidence-acquisition"

ROSTER_ID = "SLURP-STAGE3-CONSTRUCTION-R01C"
SPLIT_NAME = "STAGE3-CONSTRUCTION-R01C"
SPLIT_ROLE = "discovery"

PARENT_ROSTER_RELPATH = "docs/receipts/rosters/slurp-stage3-construction-r01.json"
PARENT_VIEW_RELPATH = "configs/dataset/slurp-speech-native-stage3-construction-r01.json"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"
RUNTIME_VIEW_RELPATH = "configs/dataset/slurp-speech-native-stage3-construction-r01c.json"
D1_SUPPLEMENT_RELPATH = "docs/receipts/artifacts/d1-slurp-stage3-construction-r01.json"

#: The ROLL-1 arm cell. The composite BUILD/USE guard is a function of the
#: baseline fragment's ``knowledge_stores`` alone, so the dataset fragment
#: named here cannot move it; the PARENT view is used so this builder stays
#: re-runnable before and after the cell is re-pointed at R01C.
CELL_MODEL_FRAGMENT = (
    "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
)
CELL_DATASET_FRAGMENT = "slurp-speech-native-stage3-construction-r01"
CELL_BASELINE_FRAGMENT = "slurp-native-stage3-rollout-baseline-v1"
CELL_EXPERIMENT_FRAGMENT = "slurp-native-stage3-rollout-r01-v1"

PARENT_VECTOR_DIR = "vectors/slurp-stage3-construction-r01-v1"
VECTOR_DIR = "vectors/slurp-stage3-construction-r01c-v1"
SEGMENTS_NAME = "query-vectors-speech-segments.jsonl"
CONTENT_NAME = "query-vectors-speech-content-v1.jsonl"
PARENT_SEGMENTS_SHA256 = (
    "41b47b3f744a3f18ffcec5cdf76e7116b06da72a63aa566b3d711bdc0adc8ae8"
)
PARENT_CONTENT_SHA256 = (
    "651ddfbbb9e6f29996a000a0f4a16de993a85cfc8e52115e1c66d28760f749cf"
)
SEGMENTS_LEDGER_ROW = "SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1"
CONTENT_LEDGER_ROW = "SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1"
SUBSET_PROVENANCE_SCHEMA = "saea-slurp-query-vectors-subset-provenance-v1"
EXECUTION_PROFILE = "model-free-check"

GENERATOR = "scripts/build_slurp_stage3_construction_clean_subset.py"
AUTHORITY = (
    "coordinator decision 102 (pending owner confirmation): the knowledge-source rows "
    "leave the construction roster and cell ROLL-1 flies the clean subset; "
    "docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md items "
    "S3-1/S3-2; rails.runner.run_speech_native_agent_loop BUILD/USE disjointness rule"
)
SELECTION_RULE = (
    "R01 minus every recording whose utterance is a source of any composed knowledge "
    "store (intent-boundaries-v1, slot-contracts-v2, "
    "size-pool-annotated-exemplars-minus-r01); order preserved"
)


class SubsetError(ValueError):
    """These inputs cannot produce R01C -- fail closed."""


# -- small helpers ---------------------------------------------------------


def canonical_sha256(document: object) -> str:
    """SHA-256 over the canonical JSON every receipt in this study hashes."""

    return hashlib.sha256(
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def committed_json_bytes(document: object) -> bytes:
    """The exact bytes this repository commits a JSON receipt as."""

    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def utterance_of(sample_id: str) -> str:
    """``slurp:train:000049:audio-1434542455`` -> ``slurp:train:000049``."""

    parts = str(sample_id).split(":")
    if len(parts) != 4 or parts[0] != CARRIER:
        raise SubsetError(f"malformed SLURP recording id: {sample_id!r}")
    return ":".join(parts[:3])


# -- the pure selection ----------------------------------------------------


def select_clean_items(
    items: Sequence[Mapping[str, Any]], source_sample_ids: Iterable[str]
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Split a roster's items into ``(kept, excluded)`` by UTTERANCE.

    An item is excluded when ANY recording of its utterance appears in
    ``source_sample_ids`` (the composed knowledge snapshot's own sources), so
    a ``-headset`` sibling of a knowledge source leaves too. Input order is
    preserved in both lists and no item is copied, rewritten or re-ordered.
    """

    blocked = {utterance_of(sample_id) for sample_id in source_sample_ids}
    kept: list[Mapping[str, Any]] = []
    excluded: list[Mapping[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("sample_id"), str):
            raise SubsetError("roster item must be an object carrying a sample_id")
        target = kept if utterance_of(item["sample_id"]) not in blocked else excluded
        target.append(item)
    return kept, excluded


# -- the composed BUILD/USE guard -----------------------------------------


def composite_guard(
    repo_root: Path,
    root: Path,
    *,
    dataset_fragment: str = CELL_DATASET_FRAGMENT,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """``(composite source_sample_ids, a per-store report)`` for cell ROLL-1.

    Exactly the derivation the flight performs: compose the cell's four
    fragments, load the named-store binding, read the composite snapshot the
    binding builds. Never a hand-copied id list.
    """

    composed = compose(
        repo_root,
        CELL_MODEL_FRAGMENT,
        dataset_fragment,
        CELL_BASELINE_FRAGMENT,
        CELL_EXPERIMENT_FRAGMENT,
    )
    binding = load_knowledge_store_binding(composed.values, data_root=root)
    if binding is None:
        raise SubsetError("cell ROLL-1 binds no named knowledge stores")
    stores = {}
    for store_id in binding.store_ids:
        store = binding.store(store_id)
        stores[store_id] = {
            "store_role": store.store_role,
            "release_relpath": store.release_pin["relpath"],
            "release_sha256": store.release_pin["sha256"],
            "snapshot_relpath": store.snapshot_pin["relpath"],
            "snapshot_sha256": store.snapshot_pin["sha256"],
            "source_sample_ids": len(store.snapshot.source_sample_ids),
        }
    report = {
        "composed_from": {
            "model": CELL_MODEL_FRAGMENT,
            "dataset": dataset_fragment,
            "baseline": CELL_BASELINE_FRAGMENT,
            "experiment": CELL_EXPERIMENT_FRAGMENT,
        },
        "derivation": (
            "core.config.compose of the ROLL-1 cell's four fragments, then "
            "rails.knowledge_stores.load_knowledge_store_binding; the guard set is the "
            "composite snapshot's source_sample_ids (the union over composed stores, "
            "rails.knowledge_stores._composite). The dataset fragment cannot move this "
            "set: only knowledge_stores feeds it."
        ),
        "binding_sha256": binding.binding_sha256,
        "composite_snapshot_sha256": binding.composite_snapshot.content_hash(),
        "composite_source_split_identity_hash": (
            binding.composite_snapshot.source_split_identity_hash
        ),
        "composite_source_sample_ids": len(
            binding.composite_snapshot.source_sample_ids
        ),
        "stores": stores,
    }
    return tuple(binding.composite_snapshot.source_sample_ids), report


# -- receipt ---------------------------------------------------------------


def _disjointness_proof(
    parent_receipt: Mapping[str, Any], kept_ids: Sequence[str]
) -> dict[str, Any]:
    """Recompute the parent's disjointness table against R01C's own ids."""

    parent = parent_receipt.get("disjointness_proof")
    if not isinstance(parent, Mapping):
        raise SubsetError("parent roster receipt carries no disjointness proof")
    recordings = set(kept_ids)
    utterances = {utterance_of(sample_id) for sample_id in kept_ids}
    proof: dict[str, Any] = {
        "excluded_utterances_before_the_draw": parent.get(
            "excluded_utterances_before_the_draw", 0
        ),
    }
    for name, entry in sorted(parent.items()):
        if name == "excluded_utterances_before_the_draw":
            continue
        if not isinstance(entry, Mapping):
            continue
        relpath = str(entry["relpath"])
        other = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        # A roster receipt names its rows ``sample_id``; the legacy
        # probe-sample receipt (DEV-1000) names them ``id``. Both are the
        # same carrier-scoped recording id.
        other_ids = [
            str(item.get("sample_id", item.get("id"))) for item in other["items"]
        ]
        proof[name] = {
            "relpath": relpath,
            "items": len(other_ids),
            "shared_recordings": len(recordings & set(other_ids)),
            "shared_utterances": len(
                utterances & {utterance_of(sample_id) for sample_id in other_ids}
            ),
        }
    return proof


def build_receipt(
    parent_receipt: Mapping[str, Any],
    parent_receipt_relpath: str,
    parent_receipt_file_sha256: str,
    kept: Sequence[Mapping[str, Any]],
    excluded: Sequence[Mapping[str, Any]],
    guard_report: Mapping[str, Any],
    guard_ids: Sequence[str],
    d1_note: Mapping[str, Any],
    offline_guard: Mapping[str, Any],
) -> dict[str, Any]:
    kept_ids = [str(item["sample_id"]) for item in kept]
    identity_hash = split_identity_hash(prefixed(CARRIER, kept_ids))
    strata_counts = dict(sorted(Counter(str(item["stratum"]) for item in kept).items()))
    excluded_strata = dict(
        sorted(Counter(str(item["stratum"]) for item in excluded).items())
    )
    residual = set(kept_ids) & set(guard_ids)
    if residual:
        raise SubsetError(
            f"{len(residual)} R01C row(s) are still knowledge sources, e.g. "
            f"{sorted(residual)[:5]}"
        )
    return {
        "schema": RECEIPT_SCHEMA,
        "roster_id": ROSTER_ID,
        "carrier_lock_key": CARRIER,
        "split_role": SPLIT_ROLE,
        "roster_role": CONSTRUCTION_ROSTER_ROLE,
        "seed": parent_receipt["seed"],
        "per_stratum": strata_counts,
        "strata_counts": strata_counts,
        "items": list(kept),
        "excluded_count": len(excluded),
        "split_identity_hash": identity_hash,
        "generator": GENERATOR,
        "authority": AUTHORITY,
        "selection_rule": SELECTION_RULE,
        "draw_method": (
            "No draw. R01C is a pure SELECTION of the parent receipt's frozen items: "
            "every surviving item is the parent's item verbatim, in the parent's order "
            "(ascending sample_id, as core.roster.freeze_roster left it). The seed is "
            "the parent's and is carried for provenance only -- no rng is consulted "
            "anywhere in this build."
        ),
        "parent": {
            "roster_id": parent_receipt["roster_id"],
            "relpath": parent_receipt_relpath,
            "file_sha256": parent_receipt_file_sha256,
            "canonical_sha256": canonical_sha256(parent_receipt),
            "split_identity_hash": parent_receipt["split_identity_hash"],
            "count": len(parent_receipt["items"]),
            "per_stratum": parent_receipt["per_stratum"],
            "strata_counts": parent_receipt["strata_counts"],
            "diversity_report": (
                "not recomputed: the parent's farthest-point diversity statistics are a "
                "property of the DRAW, and a later selection neither preserves nor "
                "invalidates them; read them in the parent receipt"
            ),
            "pool_receipt": parent_receipt["pool_receipt"],
            "vectors": parent_receipt["vectors"],
        },
        "exclusion": {
            "rule": SELECTION_RULE,
            "granularity": (
                "utterance: a recording leaves when ANY recording of its utterance is a "
                "knowledge source, the same rule "
                "scripts/build_slurp_stage3_r01_excluded_exemplar_store.py applies from "
                "the knowledge side"
            ),
            "excluded_recordings": len(excluded),
            "excluded_utterances": len(
                {utterance_of(str(item["sample_id"])) for item in excluded}
            ),
            "excluded_per_stratum": excluded_strata,
            "excluded_sample_ids": sorted(str(item["sample_id"]) for item in excluded),
        },
        "knowledge_source_guard": {
            **dict(guard_report),
            "overlap_with_parent_recordings": len(
                {str(item["sample_id"]) for item in parent_receipt["items"]}
                & set(guard_ids)
            ),
            "overlap_with_r01c_recordings": 0,
            "overlap_with_r01c_utterances": 0,
            "asserted": (
                "set(R01C sample ids) & set(composite source_sample_ids) == set(); the "
                "exact intersection rails.runner.run_speech_native_agent_loop computes "
                "before it dispatches a single row"
            ),
        },
        "d1_supplement": dict(d1_note),
        "disjointness_proof": _disjointness_proof(parent_receipt, kept_ids),
        "offline_guard": dict(offline_guard),
    }


# -- runtime view ----------------------------------------------------------


def _verify_parent_view(view: Mapping[str, Any]) -> None:
    if view.get("schema") != RUNTIME_VIEW_SCHEMA or view.get("study") != STUDY:
        raise SubsetError("parent runtime view identity mismatch")
    unsigned = {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    if view.get("runtime_view_sha256") != canonical_sha256(unsigned):
        raise SubsetError("parent runtime view runtime_view_sha256 mismatch")


def build_runtime_view(
    parent_view: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """The R01C view: the parent's rows for the surviving ids and nothing else.

    The D1 supplement triple is carried VERBATIM -- the parent supplement is a
    superset of R01C and the media-identity gate reads it by id -- so
    ``data.slurp.load_slurp_engineering_gate``'s exact 16-key contract and its
    all-or-nothing supplement rule both still hold.
    """

    _verify_parent_view(parent_view)
    by_id = {str(item["sample_id"]): item for item in parent_view["items"]}
    kept_ids = sorted(str(item["sample_id"]) for item in receipt["items"])
    missing = [sample_id for sample_id in kept_ids if sample_id not in by_id]
    if missing:
        raise SubsetError(
            f"{len(missing)} R01C id(s) are absent from the parent runtime view, e.g. "
            f"{missing[:5]}"
        )
    items = [by_id[sample_id] for sample_id in kept_ids]
    unsigned = {
        "schema": RUNTIME_VIEW_SCHEMA,
        "study": STUDY,
        "status": parent_view["status"],
        "carrier_lock_key": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "seed": parent_view["seed"],
        "split_identity_hash": receipt["split_identity_hash"],
        "source_binding_sha256": canonical_sha256(receipt),
        "d1_media_supplement": parent_view["d1_media_supplement"],
        "d1_media_supplement_sha256": parent_view["d1_media_supplement_sha256"],
        "d1_manifest_sha256": parent_view["d1_manifest_sha256"],
        "count": len(items),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in items), 9
        ),
        "items": items,
    }
    return {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}


# -- vector subsets --------------------------------------------------------


def subset_vector_lines(
    raw: bytes, kept_ids: Sequence[str], *, label: str
) -> tuple[bytes, int]:
    """Keep the parent's own LINE BYTES for the R01C ids, in parent order."""

    wanted = set(kept_ids)
    if len(wanted) != len(kept_ids):
        raise SubsetError("R01C ids repeat")
    seen: set[str] = set()
    kept_lines: list[str] = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        entry_id = str(json.loads(line)["id"])
        if entry_id in seen:
            raise SubsetError(f"{label} repeats id {entry_id!r}")
        seen.add(entry_id)
        if entry_id in wanted:
            kept_lines.append(line)
    absent = wanted - seen
    if absent:
        raise SubsetError(
            f"{label} does not carry {len(absent)} R01C id(s), e.g. {sorted(absent)[:5]}"
        )
    if len(kept_lines) != len(wanted):
        raise SubsetError(f"{label} subset row count disagrees with the R01C roster")
    return ("\n".join(kept_lines) + "\n").encode("utf-8"), len(kept_lines)


def _vector_provenance(
    *,
    parent_relpath: str,
    parent_sha256: str,
    parent_row_count: int,
    output_relpath: str,
    output_sha256: str,
    row_count: int,
    kind: str,
    ledger_row: str,
    roster_relpath: str,
    roster_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": SUBSET_PROVENANCE_SCHEMA,
        "generator": GENERATOR,
        "execution_profile": EXECUTION_PROFILE,
        "contacts": 0,
        "transform": (
            "pure id SELECTION: every kept line is the parent file's own line bytes, "
            "unchanged and in the parent's order; nothing is recomputed, re-encoded, "
            "renormalised or re-ordered, and no model, encoder, tokenizer or network "
            "contact is opened"
        ),
        "parent_relpath": parent_relpath,
        "parent_sha256": parent_sha256,
        "parent_row_count": parent_row_count,
        "parent_kind": kind,
        "parent_exposure_ledger_row": ledger_row,
        "exposure_ledger_row": None,
        "exposure_note": (
            "no new exposure row is owed: these bytes are a subset of the bytes the "
            f"parent row {ledger_row} already sealed, and this selection spends zero "
            "contacts of any kind"
        ),
        "output_relpath": output_relpath,
        "output_kind": kind,
        "row_count": row_count,
        "sha256": output_sha256,
        "roster_relpath": roster_relpath,
        "roster_sha256": roster_sha256,
        "roster_id": ROSTER_ID,
    }


# -- write / check ---------------------------------------------------------


def _emit(path: Path, payload: bytes, *, write: bool, label: str) -> str:
    digest = sha256_bytes(payload)
    if path.exists():
        actual = sha256_file(path)
        state = "IDENTICAL" if actual == digest else "DIFFERS"
        print(
            f"  {label}: exists, {state} "
            f"(on disk {actual[:16]}..., rebuilt {digest[:16]}...)"
        )
        if state == "DIFFERS":
            raise SubsetError(
                f"refusing to overwrite {path}: the rebuilt bytes differ from the "
                "sealed ones"
            )
        return digest
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)
        print(f"  {label}: wrote {path} sha256={digest}")
    else:
        print(f"  {label}: (dry run) would write {path} sha256={digest}")
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write missing artifacts")
    parser.add_argument(
        "--check",
        action="store_true",
        help="recompute and compare only; never write (the default is read-only too)",
    )
    parser.add_argument("--dataset-fragment", default=CELL_DATASET_FRAGMENT)
    args = parser.parse_args(argv)
    write = bool(args.write) and not args.check

    attempts = arm_offline_guard()
    root = data_root()

    parent_roster_path = REPO_ROOT / PARENT_ROSTER_RELPATH
    parent_receipt = read_roster(parent_roster_path)
    parent_view = json.loads(
        (REPO_ROOT / PARENT_VIEW_RELPATH).read_text(encoding="utf-8")
    )

    guard_ids, guard_report = composite_guard(
        REPO_ROOT, root, dataset_fragment=args.dataset_fragment
    )
    kept, excluded = select_clean_items(parent_receipt["items"], guard_ids)
    kept_ids = [str(item["sample_id"]) for item in kept]

    supplement = json.loads(
        (REPO_ROOT / D1_SUPPLEMENT_RELPATH).read_text(encoding="utf-8")
    )
    supplement_ids = {str(entry["id"]) for entry in supplement["manifest"]}
    uncovered = [sample_id for sample_id in kept_ids if sample_id not in supplement_ids]
    if uncovered:
        raise SubsetError(
            f"{len(uncovered)} R01C id(s) are outside the R01 D1 supplement, e.g. "
            f"{uncovered[:5]}"
        )
    d1_note = {
        "relpath": D1_SUPPLEMENT_RELPATH,
        "file_sha256": sha256_file(REPO_ROOT / D1_SUPPLEMENT_RELPATH),
        "supplement_count": int(supplement["count"]),
        "r01c_ids_covered": len(kept_ids),
        "note": (
            "the R01 D1 media supplement is NOT rebuilt for R01C. It closes over all "
            f"{int(supplement['count'])} parent recordings, a strict SUPERSET of R01C's "
            f"{len(kept_ids)}, and contracts.gate_media_identity"
            "._d1_media_supplement_records verifies the supplement's own integrity and "
            "then looks each FLOWN id up in it -- it never requires an exact cover. The "
            "R01C runtime view therefore carries the parent's supplement triple verbatim."
        ),
    }

    receipt = build_receipt(
        parent_receipt,
        PARENT_ROSTER_RELPATH,
        sha256_file(parent_roster_path),
        kept,
        excluded,
        guard_report,
        guard_ids,
        d1_note,
        {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    )
    verify_roster(receipt)
    runtime_view = build_runtime_view(parent_view, receipt)

    print(
        f"parent roster {parent_receipt['roster_id']}: "
        f"{len(parent_receipt['items'])} rows"
    )
    print(
        "composite knowledge source ids: "
        f"{guard_report['composite_source_sample_ids']}"
    )
    for store_id, entry in sorted(guard_report["stores"].items()):
        print(f"  store {store_id}: {entry['source_sample_ids']} source ids")
    print(f"excluded (utterance is a knowledge source): {len(excluded)}")
    print(
        f"{ROSTER_ID}: {len(kept)} rows, "
        f"split identity {receipt['split_identity_hash']}"
    )
    print(f"per-stratum: {json.dumps(receipt['strata_counts'], sort_keys=True)}")
    print(
        "excluded per-stratum: "
        f"{json.dumps(receipt['exclusion']['excluded_per_stratum'], sort_keys=True)}"
    )
    print(
        f"runtime view: count={runtime_view['count']} "
        f"audio_seconds_total={runtime_view['audio_seconds_total']}"
    )
    print(f"runtime_view_sha256={runtime_view['runtime_view_sha256']}")
    print(f"source_binding_sha256={runtime_view['source_binding_sha256']}")

    roster_path = REPO_ROOT / ROSTER_RELPATH
    view_path = REPO_ROOT / RUNTIME_VIEW_RELPATH
    print("artifacts:")
    roster_file_sha256 = _emit(
        roster_path, committed_json_bytes(receipt), write=write, label="roster receipt"
    )
    _emit(
        view_path,
        committed_json_bytes(runtime_view),
        write=write,
        label="dataset fragment",
    )

    for name, parent_sha256, kind, ledger_row in (
        (SEGMENTS_NAME, PARENT_SEGMENTS_SHA256, "sealed-segment-vectors", SEGMENTS_LEDGER_ROW),
        (CONTENT_NAME, PARENT_CONTENT_SHA256, "sealed-vectors", CONTENT_LEDGER_ROW),
    ):
        parent_relpath = f"{PARENT_VECTOR_DIR}/{name}"
        parent_bytes = (root / parent_relpath).read_bytes()
        measured = sha256_bytes(parent_bytes)
        if measured != parent_sha256:
            raise SubsetError(
                f"{parent_relpath} hashes to {measured}, not the pinned {parent_sha256}"
            )
        parent_rows = sum(
            1 for line in parent_bytes.decode("utf-8").splitlines() if line.strip()
        )
        payload, rows = subset_vector_lines(parent_bytes, kept_ids, label=parent_relpath)
        output_relpath = f"{VECTOR_DIR}/{name}"
        digest = _emit(root / output_relpath, payload, write=write, label=output_relpath)
        provenance_relpath = f"{VECTOR_DIR}/{Path(name).stem}.provenance.json"
        provenance = _vector_provenance(
            parent_relpath=parent_relpath,
            parent_sha256=parent_sha256,
            parent_row_count=parent_rows,
            output_relpath=output_relpath,
            output_sha256=digest,
            row_count=rows,
            kind=kind,
            ledger_row=ledger_row,
            roster_relpath=ROSTER_RELPATH,
            roster_sha256=roster_file_sha256,
        )
        _emit(
            root / provenance_relpath,
            committed_json_bytes(provenance),
            write=write,
            label=provenance_relpath,
        )

    print(f"offline guard: {attempts.count} outbound connection attempt(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
